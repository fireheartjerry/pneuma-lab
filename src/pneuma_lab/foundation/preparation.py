"""Deterministic, zero-weight preparation for local foundation training."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat as stat_module

from pneuma_lab import dataset_readiness
from pneuma_lab.converters import openhands_sampled_training as openhands_converter
from pneuma_lab.foundation.artifacts import (
    ArtifactPublicationError,
    bind_artifact_publication,
    write_atomic_bytes,
    write_atomic_json,
)
from pneuma_lab.foundation.contamination import build_contamination_receipt
from pneuma_lab.foundation.data import (
    ACTIVE_DATASET_GROUPS,
    DataAuthorizationError,
    _validate_output_path,
    build_content_addressed_shard,
    build_diversity_inventory,
    deduplicate_examples,
)
from pneuma_lab.foundation.eval_identities import (
    EVAL_METADATA_FIELDS,
    IdentityRecord,
    _metadata_rows,
    build_eval_identity_index,
    identity_from_foundation_record,
    load_required_eval_identities,
)
from pneuma_lab.foundation.records import (
    FoundationRecordError,
    GradientEligibility,
    LaneDisposition,
    TerminalRole,
    render_foundation_record,
    validate_foundation_record,
)
from pneuma_lab.foundation.specs import MODEL_SPECS
from pneuma_lab.foundation.suite import (
    build_suite_completeness_report,
    evaluation_identity_scope,
    load_suite_policy,
    open_authorized_payload,
    validate_suite_policy,
)


STAGE_TOKEN_CEILINGS = {
    "100k": 100_000,
    "500k": 500_000,
    "1m": 1_000_000,
    "2m": 2_000_000,
    "8m": 8_000_000,
    "16m": 16_000_000,
    "32m": 32_000_000,
}

_REGISTRY_RELATIVE_PATH = Path(
    "docs/data/training-readiness/dataset-registry.json"
)
_SUITE_RELATIVE_PATH = Path(
    "docs/data/training-readiness/pneuma-foundation-v0-suite.json"
)
_LICENSE_RELATIVE_PATH = Path(
    "docs/data/license-receipts/"
    "swe-gym-openhands-sampled.local-research.json"
)
_TRACE_RELATIVE_PATH = Path(
    "processed/swe-gym/openhands-sampled/pneuma_traces.jsonl"
)
_ADAPTER_REPORT_RELATIVE_PATH = Path(
    "processed/swe-gym/openhands-sampled/adapter_report.json"
)
_LICENSE_RECEIPT = {
    "receipt_kind": "dataset_license_posture",
    "receipt_schema_version": "0.1.0",
    "dataset_id": "swe-gym-openhands-sampled",
    "artifact_card_license_declared": False,
    "upstream_code_license": "Apache-2.0",
    "mirror_directory_license_observed": "MIT",
    "decision": "local_research_candidate_no_redistribution",
    "cloud_redistribution_allowed": False,
    "requires_exact_operator_authorization": True,
    "sources": [
        "https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories",
        "https://github.com/SWE-Gym/SWE-Gym",
        "https://huggingface.co/datasets/neulab/agent-data-collection/blob/main/"
        "swe-gym_openhands_sampled_trajectories/LICENSE",
    ],
}


@dataclass(frozen=True)
class PreparationRequest:
    stage: str
    repo_root: Path
    data_root: Path
    tokenizer_snapshot: Path
    output_root: Path
    seed: int = 20260713
    dry_run: bool = False


@dataclass(frozen=True)
class PreparationResult:
    preparation_manifest_path: Path
    suite_report_path: Path
    license_receipt_path: Path
    source_presence_receipt_path: Path
    source_integrity_receipt_path: Path
    shard_path: Path
    shard_manifest_path: Path
    split_receipt_path: Path
    contamination_receipt_path: Path
    diversity_receipt_path: Path
    selection_receipt_path: Path


class _DigestingBinaryStream:
    def __init__(self, stream) -> None:
        self._stream = stream
        self._digest = hashlib.sha256()

    @property
    def hexdigest(self) -> str:
        return self._digest.hexdigest()

    def __iter__(self):
        for chunk in self._stream:
            if not isinstance(chunk, bytes):
                raise ValueError("authorized payload stream must yield bytes")
            self._digest.update(chunk)
            yield chunk

    def read(self, size: int = -1) -> bytes:
        chunk = self._stream.read(size)
        if not isinstance(chunk, bytes):
            raise ValueError("authorized payload stream must yield bytes")
        self._digest.update(chunk)
        return chunk


def _strict_json_bytes(payload: bytes, *, label: str) -> dict:
    def reject_duplicate_members(pairs):
        value = {}
        for name, member in pairs:
            if name in value:
                raise ValueError(f"{label} has duplicate JSON member: {name}")
            value[name] = member
        return value

    def reject_constant(constant: str):
        raise ValueError(f"{label} has non-finite JSON constant: {constant}")

    try:
        value = json.loads(
            payload,
            object_pairs_hook=reject_duplicate_members,
            parse_constant=reject_constant,
        )
    except ValueError:
        raise
    except (json.JSONDecodeError, RecursionError, UnicodeError) as exc:
        raise ValueError(f"{label} must be strict JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _load_strict_json(path: Path, *, label: str) -> tuple[dict, bytes]:
    try:
        payload = Path(path).read_bytes()
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError(f"{label} cannot be read") from exc
    return _strict_json_bytes(payload, label=label), payload


def _load_tokenizer(snapshot: Path):
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise ValueError("transformers is required to load the pinned tokenizer") from exc
    return AutoTokenizer.from_pretrained(
        str(snapshot),
        local_files_only=True,
        trust_remote_code=False,
    )


def _validate_tokenizer_snapshot(path: Path) -> Path:
    snapshot = Path(path)
    try:
        metadata = snapshot.lstat()
    except (OSError, TypeError, ValueError) as exc:
        raise ValueError("tokenizer snapshot must exist locally") from exc
    if not stat_module.S_ISDIR(metadata.st_mode) or snapshot.is_symlink():
        raise ValueError("tokenizer snapshot must be a physical directory")
    for member in snapshot.rglob("*"):
        try:
            member_metadata = member.lstat()
        except OSError as exc:
            raise ValueError("tokenizer snapshot metadata cannot be inspected") from exc
        if stat_module.S_ISLNK(member_metadata.st_mode):
            raise ValueError("tokenizer snapshot must not contain symbolic links")
    return snapshot


def _stream_snapshot(stream, relative_path: Path, digest: str) -> dict:
    metadata = os.fstat(stream.fileno())
    return {
        "relative_path": relative_path.as_posix(),
        "size": metadata.st_size,
        "mtime_ns": metadata.st_mtime_ns,
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "sha256": digest,
    }


def _read_authorized_value(
    policy: Mapping,
    *,
    stage: str,
    family: str,
    lane_id: str | None,
    data_root: Path,
    relative_path: Path,
    parser,
):
    path = Path(data_root) / relative_path
    with open_authorized_payload(
        policy,
        stage=stage,
        family=family,
        lane_id=lane_id,
        data_root=data_root,
        path=path,
    ) as stream:
        before = os.fstat(stream.fileno())
        digesting = _DigestingBinaryStream(stream)
        value = parser(digesting)
        after = os.fstat(stream.fileno())
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            raise ValueError("authorized payload changed while it was being parsed")
        snapshot = _stream_snapshot(stream, relative_path, digesting.hexdigest)
    return value, snapshot


def _hash_authorized_source(
    policy: Mapping,
    *,
    stage: str,
    family: str,
    lane_id: str | None,
    data_root: Path,
    relative_path: Path,
) -> dict:
    def consume(stream) -> None:
        while stream.read(1024 * 1024):
            pass

    _, snapshot = _read_authorized_value(
        policy,
        stage=stage,
        family=family,
        lane_id=lane_id,
        data_root=data_root,
        relative_path=relative_path,
        parser=consume,
    )
    return snapshot


def _issue_suffix(source_id: str) -> str | None:
    match = re.search(r"(?:^|[-_#/])([0-9]+)$", source_id)
    return match.group(1) if match is not None else None


def _identities_from_rows(family: str, rows: Iterable[Mapping]) -> tuple[IdentityRecord, ...]:
    return tuple(
        IdentityRecord(
            family=family,
            lane_id=family,
            repo=row["repo"],
            issue_or_pr=_issue_suffix(row["source_id"]),
            task_id=row["source_id"],
            base_commit=row["base_commit"],
            patch_sha256=None,
            test_patch_sha256=None,
            fuzzy_text_sha256=None,
        )
        for row in rows
    )


def _canonical_json_bytes(value: Mapping) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _pretty_json_bytes(value: Mapping) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _conversion_bundle(traces: tuple[dict, ...], adapter_report: Mapping) -> dict:
    examples = openhands_converter.convert_traces(
        traces,
        adapter_report_ref="verified-stream:adapter_report.json",
        manifest_ref="full/hash_manifest.json",
    )
    openhands_converter.validate_training_examples(examples)
    examples_bytes = b"".join(_canonical_json_bytes(example) for example in examples)
    invalid_bytes = b""
    output_hashes = {
        "examples_jsonl_sha256": hashlib.sha256(examples_bytes).hexdigest(),
        "invalid_examples_jsonl_sha256": hashlib.sha256(invalid_bytes).hexdigest(),
    }
    report = openhands_converter.build_conversion_report(
        mode=openhands_converter.FULL_MODE,
        input_path="verified-stream:pneuma_traces.jsonl",
        adapter_report_path="verified-stream:adapter_report.json",
        adapter_report=dict(adapter_report),
        limit=None,
        traces_read=len(traces),
        agent_steps=sum(
            int(trace["trajectory"]["num_agent_steps"]) for trace in traces
        ),
        examples=examples,
        invalid_records=[],
        output_hashes=output_hashes,
    )
    if not report["count_reconciliation"]["reconciled"]:
        raise ValueError("trace counts do not reconcile with the adapter report")
    report_bytes = _canonical_json_bytes(report)
    manifest = openhands_converter.build_hash_manifest(
        mode=openhands_converter.FULL_MODE,
        examples_text=examples_bytes.decode("utf-8"),
        invalid_text="",
        report_text=report_bytes.decode("utf-8"),
        limit=None,
        input_path="verified-stream:pneuma_traces.jsonl",
        adapter_report_path="verified-stream:adapter_report.json",
    )
    manifest["hashes"]["hash_manifest_json_sha256"] = hashlib.sha256(
        _canonical_json_bytes(manifest)
    ).hexdigest()
    manifest_bytes = _canonical_json_bytes(manifest)
    return {
        "examples": examples,
        "examples.jsonl": examples_bytes,
        "invalid_examples.jsonl": invalid_bytes,
        "conversion_report.json": report_bytes,
        "hash_manifest.json": manifest_bytes,
    }


def _regular_generated_bytes(path: Path) -> bytes | None:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError("generated conversion artifact cannot be inspected") from exc
    if stat_module.S_ISLNK(metadata.st_mode) or not stat_module.S_ISREG(
        metadata.st_mode
    ):
        raise ValueError("generated conversion artifact must be a physical regular file")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError("generated conversion artifact cannot be read") from exc


def _conversion_is_complete(output_root: Path, bundle: Mapping) -> bool:
    for name in (
        "examples.jsonl",
        "invalid_examples.jsonl",
        "conversion_report.json",
        "hash_manifest.json",
    ):
        if _regular_generated_bytes(output_root / name) != bundle[name]:
            return False
    return True


def _split_assignments(examples: Iterable[Mapping]) -> tuple[dict, ...]:
    assignments = []
    repository_splits: dict[str, str] = {}
    for example in examples:
        split_group = example.get("split_group")
        if not isinstance(split_group, Mapping):
            raise ValueError("converted example split_group must be a mapping")
        repo = split_group.get("repo")
        if not isinstance(repo, str) or not repo.strip():
            raise ValueError("converted example repository must be a nonempty string")
        split_id = deterministic_split(repo)
        canonical_repo = repo.casefold()
        previous = repository_splits.setdefault(canonical_repo, split_id)
        if previous != split_id:
            raise ValueError("one repository cannot be assigned to multiple splits")
        assignments.append(
            {
                "record_source_id": example.get("example_id"),
                "repo": repo,
                "split_id": split_id,
                "quarantine_id": None,
            }
        )
    return tuple(assignments)


def _render_records(
    examples: Iterable[Mapping],
    assignments: Iterable[Mapping],
    *,
    tokenizer,
    source_receipt_hashes: tuple[str, ...],
) -> tuple[dict, ...]:
    disposition = LaneDisposition(
        terminal_role=TerminalRole.TRAIN,
        gradient_eligibility=GradientEligibility.FIRST_STAGE,
        license_disposition="local_research_candidate_no_redistribution",
        privacy_disposition="redaction_verified",
        dual_use_disposition="not_flagged",
        oracle_disposition="target_only",
    )
    records = []
    for example, assignment in zip(examples, assignments, strict=True):
        record = render_foundation_record(
            example,
            lane_disposition=disposition,
            split_assignment=assignment,
            tokenizer=tokenizer,
            tokenizer_revision=MODEL_SPECS["2b"].revision,
            source_receipt_hashes=source_receipt_hashes,
        )
        prompt_tokens = len(
            tokenizer.encode(
                record["rendered"]["prompt_text"],
                add_special_tokens=False,
            )
        )
        target_tokens = len(
            tokenizer.encode(
                record["rendered"]["target_text"],
                add_special_tokens=False,
            )
        )
        if record["tokenization"] != {
            "tokenizer_id": MODEL_SPECS["2b"].model_id,
            "tokenizer_revision": MODEL_SPECS["2b"].revision,
            "prompt_tokens": prompt_tokens,
            "target_tokens": target_tokens,
            "total_tokens": prompt_tokens + target_tokens,
        }:
            raise ValueError("foundation record tokenizer recount does not match")
        records.append(record)
    unique, _duplicates = deduplicate_examples(records)
    return tuple(unique)


def _planned_shard_paths(
    records: Iterable[Mapping],
    output_root: Path,
) -> tuple[Path, Path]:
    payload = b"".join(_canonical_json_bytes(record) for record in records)
    digest = hashlib.sha256(payload).hexdigest()
    shard_root = output_root / "shards"
    return (
        shard_root / f"{digest}.jsonl",
        shard_root / f"{digest}.manifest.json",
    )


def _result_paths(
    output_root: Path,
    shard_path: Path,
    shard_manifest_path: Path,
) -> PreparationResult:
    return PreparationResult(
        preparation_manifest_path=output_root / "preparation_manifest.json",
        suite_report_path=output_root / "suite_report.json",
        license_receipt_path=output_root / "license_receipt.json",
        source_presence_receipt_path=output_root / "source_presence_receipt.json",
        source_integrity_receipt_path=output_root / "source_integrity_receipt.json",
        shard_path=shard_path,
        shard_manifest_path=shard_manifest_path,
        split_receipt_path=output_root / "split_receipt.json",
        contamination_receipt_path=output_root / "contamination_receipt.json",
        diversity_receipt_path=output_root / "diversity_receipt.json",
        selection_receipt_path=output_root / "selection_receipt.json",
    )


def deterministic_split(repo: str) -> str:
    if not isinstance(repo, str) or not repo.strip():
        raise ValueError("repository must be a nonempty string")
    bucket = int(
        hashlib.sha256(repo.casefold().encode("utf-8")).hexdigest()[:8],
        16,
    ) % 100
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "validation"
    return "held_out"


def _validated_selection_record(record, *, index: int) -> dict:
    if not isinstance(record, Mapping):
        raise ValueError(f"foundation record {index} must be a mapping")
    try:
        validate_foundation_record(record)
    except FoundationRecordError as exc:
        raise ValueError(f"foundation record {index} schema is invalid: {exc}") from exc
    tokenization = record.get("tokenization")
    if not isinstance(tokenization, Mapping):
        raise ValueError(f"foundation record {index} tokenization is invalid")
    token_values = tuple(
        tokenization.get(field)
        for field in ("prompt_tokens", "target_tokens", "total_tokens")
    )
    if any(type(value) is not int or value <= 0 for value in token_values):
        raise ValueError(f"foundation record {index} token counts must be positive")
    if token_values[0] + token_values[1] != token_values[2]:
        raise ValueError(f"foundation record {index} token total is inconsistent")
    labels = (record.get("observations") or {}).get("labels")
    if not isinstance(labels, Mapping) or type(labels.get("resolved")) is not bool:
        raise ValueError(f"foundation record {index} resolved labels are missing")
    return dict(record)


def select_complete_records(
    records: Iterable[Mapping],
    token_ceiling: int,
) -> tuple[dict, ...]:
    if type(token_ceiling) is not int or token_ceiling <= 0:
        raise ValueError("token ceiling must be a positive integer")
    values = tuple(
        _validated_selection_record(record, index=index)
        for index, record in enumerate(records)
    )
    record_ids = [record["record_id"] for record in values]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("foundation records contain a duplicate record_id")
    train = sorted(
        (
            record
            for record in values
            if (
                record["split"]["split_id"] == "train"
                and record["disposition"]["terminal_role"] == "train"
                and record["disposition"]["gradient_eligibility"]
                in {"first_stage", "later"}
            )
        ),
        key=lambda record: record["record_id"],
    )
    anchors = []
    for label in (True, False):
        anchor = next(
            (
                record
                for record in train
                if record["observations"]["labels"]["resolved"] is label
            ),
            None,
        )
        if anchor is None:
            raise ValueError("train records must include resolved and unresolved labels")
        anchors.append(anchor)
    selected_ids = {record["record_id"] for record in anchors}
    total_tokens = sum(
        record["tokenization"]["total_tokens"] for record in anchors
    )
    if total_tokens > token_ceiling:
        raise ValueError("resolved/unresolved anchors exceed the token ceiling")
    for record in train:
        if record["record_id"] in selected_ids:
            continue
        record_tokens = record["tokenization"]["total_tokens"]
        if total_tokens + record_tokens <= token_ceiling:
            selected_ids.add(record["record_id"])
            total_tokens += record_tokens
    return tuple(record for record in train if record["record_id"] in selected_ids)


def prepare_stage(request: PreparationRequest) -> PreparationResult:
    if not isinstance(request, PreparationRequest):
        raise ValueError("preparation request must be a PreparationRequest")
    if request.stage not in STAGE_TOKEN_CEILINGS:
        raise ValueError(f"unknown foundation preparation stage: {request.stage!r}")
    if type(request.seed) is not int:
        raise ValueError("preparation seed must be an integer")
    if type(request.dry_run) is not bool:
        raise ValueError("dry_run must be a bool")
    repo_root = Path(request.repo_root)
    data_root = Path(request.data_root)
    output_root = Path(request.output_root)
    for label, path in (
        ("repository root", repo_root),
        ("protected data root", data_root),
        ("preparation output root", output_root),
    ):
        if not path.is_absolute():
            raise ValueError(f"{label} must be absolute")
    try:
        _validate_output_path(
            repo_root=repo_root,
            output_root=output_root,
            data_root=data_root,
        )
        conversion_root = (
            repo_root / "build/training_examples/openhands-sampled/full"
        )
        _validate_output_path(
            repo_root=repo_root,
            output_root=conversion_root,
            data_root=data_root,
        )
    except DataAuthorizationError as exc:
        raise ValueError(f"preparation output policy failed: {exc}") from exc

    registry, _registry_bytes = _load_strict_json(
        repo_root / _REGISTRY_RELATIVE_PATH,
        label="canonical dataset registry",
    )
    registry_findings = dataset_readiness.validate_registry(
        registry,
        root=repo_root,
    )
    if registry_findings:
        raise ValueError(
            "canonical dataset registry is invalid: "
            + "; ".join(registry_findings)
        )
    suite_policy = load_suite_policy(repo_root / _SUITE_RELATIVE_PATH)
    validate_suite_policy(suite_policy, registry)
    suite_report = build_suite_completeness_report(suite_policy, data_root)
    families = suite_report.get("families")
    if (
        not isinstance(families, list)
        or [item.get("family") for item in families]
        != list(ACTIVE_DATASET_GROUPS)
        or not all(item.get("exists") is True for item in families)
    ):
        raise ValueError("all ten governed dataset families must be present")
    license_receipt, license_bytes = _load_strict_json(
        repo_root / _LICENSE_RELATIVE_PATH,
        label="committed OpenHands license receipt",
    )
    if license_receipt != _LICENSE_RECEIPT:
        raise ValueError("committed OpenHands license receipt posture is invalid")
    tokenizer_snapshot = _validate_tokenizer_snapshot(request.tokenizer_snapshot)
    tokenizer = _load_tokenizer(tokenizer_snapshot)

    source_before = []
    traces, trace_snapshot = _read_authorized_value(
        suite_policy,
        stage=request.stage,
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=data_root,
        relative_path=_TRACE_RELATIVE_PATH,
        parser=openhands_converter.parse_verified_trace_stream,
    )
    source_before.append(trace_snapshot)
    adapter_report, report_snapshot = _read_authorized_value(
        suite_policy,
        stage=request.stage,
        family="swe-gym",
        lane_id="swe-gym-openhands-sampled",
        data_root=data_root,
        relative_path=_ADAPTER_REPORT_RELATIVE_PATH,
        parser=openhands_converter.parse_verified_adapter_report_stream,
    )
    source_before.append(report_snapshot)
    if adapter_report.get("traces_file_sha256") != trace_snapshot["sha256"]:
        raise ValueError("verified trace digest does not match the adapter report")

    required_families, _blocked_families = evaluation_identity_scope(suite_policy)
    eval_relative_paths = {}
    planned_eval_identities = []
    for family in required_families:
        relative_path = Path(f"processed/{family}/normalized_metadata.jsonl")
        rows, snapshot = _read_authorized_value(
            suite_policy,
            stage=request.stage,
            family=family,
            lane_id=None,
            data_root=data_root,
            relative_path=relative_path,
            parser=lambda stream: _metadata_rows(
                stream,
                allow_unretained_fields=True,
            ),
        )
        source_before.append(snapshot)
        eval_relative_paths[family] = relative_path
        identities = _identities_from_rows(family, rows)
        if not identities:
            raise ValueError(
                f"required evaluation identity family is empty: {family}"
            )
        planned_eval_identities.extend(identities)
    source_before = sorted(source_before, key=lambda item: item["relative_path"])

    bundle = _conversion_bundle(tuple(traces), adapter_report)
    receipt_hashes = tuple(
        sorted(
            (
                hashlib.sha256(bundle["conversion_report.json"]).hexdigest(),
                hashlib.sha256(bundle["hash_manifest.json"]).hexdigest(),
                hashlib.sha256(license_bytes).hexdigest(),
            )
        )
    )
    assignments = _split_assignments(bundle["examples"])
    records = _render_records(
        bundle["examples"],
        assignments,
        tokenizer=tokenizer,
        source_receipt_hashes=receipt_hashes,
    )
    selected = select_complete_records(
        records,
        token_ceiling=STAGE_TOKEN_CEILINGS[request.stage],
    )
    contamination_receipt = build_contamination_receipt(
        (identity_from_foundation_record(record) for record in selected),
        planned_eval_identities,
        suite_policy=suite_policy,
    )
    if (
        contamination_receipt["evaluation_coverage_complete"] is not True
        or contamination_receipt["finding_count"] != 0
        or contamination_receipt["repo_issue_disjoint"] is not True
    ):
        raise ValueError("foundation selection is contaminated or eval coverage is incomplete")
    diversity_receipt = {
        "manifest_kind": "pneuma_foundation_diversity_receipt",
        "manifest_schema_version": "0.1.0",
        **build_diversity_inventory(selected),
    }
    selected_tokens = sum(
        record["tokenization"]["total_tokens"] for record in selected
    )
    tokenizer_recount_total = sum(
        len(
            tokenizer.encode(
                record["rendered"]["prompt_text"],
                add_special_tokens=False,
            )
        )
        + len(
            tokenizer.encode(
                record["rendered"]["target_text"],
                add_special_tokens=False,
            )
        )
        for record in selected
    )
    if selected_tokens != tokenizer_recount_total:
        raise ValueError("aggregate tokenizer recount does not match selected records")
    selection_receipt = {
        "manifest_kind": "pneuma_foundation_selection_receipt",
        "manifest_schema_version": "0.1.0",
        "stage": request.stage,
        "seed": request.seed,
        "token_ceiling": STAGE_TOKEN_CEILINGS[request.stage],
        "candidate_record_count": len(records),
        "selected_record_count": len(selected),
        "selected_record_ids": [record["record_id"] for record in selected],
        "selected_token_count": selected_tokens,
        "tokenizer_recount_total": tokenizer_recount_total,
        "resolved_count": sum(
            record["observations"]["labels"]["resolved"] is True
            for record in selected
        ),
        "unresolved_count": sum(
            record["observations"]["labels"]["resolved"] is False
            for record in selected
        ),
        "persisted_training_weight": 0.0,
    }
    split_receipt = {
        "manifest_kind": "pneuma_foundation_repo_grouped_split_receipt",
        "manifest_schema_version": "0.1.0",
        "algorithm": "sha256(repo.casefold())[:8] mod 100",
        "thresholds": {"train": 80, "validation": 90, "held_out": 100},
        "assignments": list(assignments),
        "repository_grouped": True,
    }
    source_presence_receipt = {
        "manifest_kind": "pneuma_foundation_source_presence_receipt",
        "manifest_schema_version": "0.1.0",
        "inspection": "filesystem_metadata_only",
        "all_ten_present": True,
        "families": families,
    }

    def source_after_snapshot() -> list[dict]:
        source_specs = [
            (
                "swe-gym",
                "swe-gym-openhands-sampled",
                _TRACE_RELATIVE_PATH,
            ),
            (
                "swe-gym",
                "swe-gym-openhands-sampled",
                _ADAPTER_REPORT_RELATIVE_PATH,
            ),
            *(
                (family, None, eval_relative_paths[family])
                for family in required_families
            ),
        ]
        values = [
            _hash_authorized_source(
                suite_policy,
                stage=request.stage,
                family=family,
                lane_id=lane_id,
                data_root=data_root,
                relative_path=relative_path,
            )
            for family, lane_id, relative_path in source_specs
        ]
        return sorted(values, key=lambda item: item["relative_path"])

    planned_shard_path, planned_shard_manifest_path = _planned_shard_paths(
        selected,
        output_root,
    )
    planned_result = _result_paths(
        output_root,
        planned_shard_path,
        planned_shard_manifest_path,
    )
    if request.dry_run:
        if source_before != source_after_snapshot():
            raise ValueError(
                "protected source metadata or hashes changed during dry-run planning"
            )
        return planned_result

    if not _conversion_is_complete(conversion_root, bundle):
        openhands_converter.run_verified_stream_conversion(
            traces,
            adapter_report,
            repo_root=repo_root,
            data_root=data_root,
            output_root=conversion_root,
        )
    if not _conversion_is_complete(conversion_root, bundle):
        raise ValueError("published conversion is not byte-identical to the plan")

    eval_index_paths = {}
    for family in required_families:
        output_path = output_root / "eval-identities" / f"{family}.jsonl"
        build_eval_identity_index(
            suite_policy,
            family=family,
            repo_root=repo_root,
            data_root=data_root,
            source_path=data_root / eval_relative_paths[family],
            output_path=output_path,
            allowed_fields=EVAL_METADATA_FIELDS,
        )
        eval_index_paths[family] = output_path
    operational_eval_identities = load_required_eval_identities(
        eval_index_paths,
        suite_policy=suite_policy,
    )
    operational_contamination = build_contamination_receipt(
        (identity_from_foundation_record(record) for record in selected),
        operational_eval_identities,
        suite_policy=suite_policy,
    )
    if operational_contamination != contamination_receipt:
        raise ValueError("operational evaluation identity indexes changed the plan")

    shard_result = build_content_addressed_shard(
        selected,
        repo_root=repo_root,
        output_root=output_root / "shards",
        data_root=data_root,
    )
    result = _result_paths(
        output_root,
        shard_result.shard_path,
        shard_result.manifest_path,
    )
    if (
        result.shard_path != planned_result.shard_path
        or result.shard_manifest_path != planned_result.shard_manifest_path
        or shard_result.example_count != len(selected)
    ):
        raise ValueError("content-addressed shard differs from the validated plan")

    source_after = source_after_snapshot()
    if source_before != source_after:
        raise ValueError("protected source metadata or hashes changed during preparation")
    source_integrity_receipt = {
        "manifest_kind": "pneuma_foundation_source_integrity_receipt",
        "manifest_schema_version": "0.1.0",
        "before": source_before,
        "after": source_after,
        "unchanged": True,
    }
    receipt_payloads = {
        "suite_report.json": _pretty_json_bytes(suite_report),
        "license_receipt.json": license_bytes,
        "source_presence_receipt.json": _pretty_json_bytes(
            source_presence_receipt
        ),
        "source_integrity_receipt.json": _pretty_json_bytes(
            source_integrity_receipt
        ),
        "split_receipt.json": _pretty_json_bytes(split_receipt),
        "contamination_receipt.json": _pretty_json_bytes(
            contamination_receipt
        ),
        "diversity_receipt.json": _pretty_json_bytes(diversity_receipt),
        "selection_receipt.json": _pretty_json_bytes(selection_receipt),
    }
    manifest = {
        "manifest_kind": "pneuma_foundation_preparation_manifest",
        "manifest_schema_version": "0.1.0",
        "stage": request.stage,
        "seed": request.seed,
        "dry_run": False,
        "dataset_suite": "all_ten_governed_groups",
        "gradient_lane": "swe-gym-openhands-sampled",
        "training_authorized": False,
        "persisted_training_weight": 0.0,
        "source_receipt_hashes": list(receipt_hashes),
        "receipt_sha256": {
            name: hashlib.sha256(payload).hexdigest()
            for name, payload in sorted(receipt_payloads.items())
        },
        "shard": {
            "artifact": result.shard_path.name,
            "sha256": shard_result.sha256,
            "example_count": shard_result.example_count,
            "manifest_artifact": result.shard_manifest_path.name,
        },
        "gates": {
            "all_ten_present": True,
            "eval_coverage_complete": True,
            "contamination_findings": 0,
            "source_unchanged": True,
            "tokenizer_recount_matches": True,
        },
    }
    try:
        with bind_artifact_publication(
            output_root,
            anchor_root=repo_root,
            allowed_root=repo_root / "build",
            forbidden_roots=(data_root,),
        ) as publication:
            write_atomic_json(
                result.preparation_manifest_path,
                manifest,
                publication=publication,
            )
            write_atomic_json(
                result.suite_report_path,
                suite_report,
                publication=publication,
            )
            write_atomic_bytes(
                result.license_receipt_path,
                license_bytes,
                publication=publication,
            )
            write_atomic_json(
                result.source_presence_receipt_path,
                source_presence_receipt,
                publication=publication,
            )
            write_atomic_json(
                result.source_integrity_receipt_path,
                source_integrity_receipt,
                publication=publication,
            )
            write_atomic_json(
                result.split_receipt_path,
                split_receipt,
                publication=publication,
            )
            write_atomic_json(
                result.contamination_receipt_path,
                contamination_receipt,
                publication=publication,
            )
            write_atomic_json(
                result.diversity_receipt_path,
                diversity_receipt,
                publication=publication,
            )
            write_atomic_json(
                result.selection_receipt_path,
                selection_receipt,
                publication=publication,
            )
    except ArtifactPublicationError as exc:
        raise ValueError(f"preparation receipt publication failed: {exc}") from exc
    return result


__all__ = [
    "STAGE_TOKEN_CEILINGS",
    "PreparationRequest",
    "PreparationResult",
    "deterministic_split",
    "prepare_stage",
    "select_complete_records",
]
