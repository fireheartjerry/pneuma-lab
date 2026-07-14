"""Exact, handle-bound authorization for one local foundation stage."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack, contextmanager
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import subprocess
from types import MappingProxyType
from typing import Any, Iterator
from typing import TYPE_CHECKING
import unicodedata

from jsonschema import Draft202012Validator, FormatChecker

from pneuma_lab.foundation.artifacts import (
    ArtifactPublicationError,
    BoundArtifactRead,
    BoundArtifactReadHandle,
    bind_artifact_publication,
    write_atomic_json,
)
from pneuma_lab.foundation.data import (
    ACTIVE_DATASET_GROUPS,
    build_diversity_inventory,
)
from pneuma_lab.foundation.records import (
    EffectiveTrainingRecord,
    FoundationRecordError,
    validate_foundation_record,
)
from pneuma_lab.foundation.specs import MODEL_SPECS
from pneuma_lab.schemas import load_schema

if TYPE_CHECKING:
    from pneuma_lab.foundation.preparation import PreparationResult


APPROVAL_PHRASE_PREFIX = "I APPROVE THIS EXACT PNEUMA FOUNDATION SCOPE"
_AUTHORIZED_LANE_WEIGHTS = {"swe-gym-openhands-sampled": 1.0}
_STAGE_TOKEN_CEILINGS = {
    "100k": 100_000,
    "500k": 500_000,
    "1m": 1_000_000,
    "2m": 2_000_000,
    "8m": 8_000_000,
    "16m": 16_000_000,
    "32m": 32_000_000,
}
_ARTIFACT_FIELDS = {
    "preparation_manifest": "preparation_manifest_path",
    "suite_report": "suite_report_path",
    "license_receipt": "license_receipt_path",
    "source_presence_receipt": "source_presence_receipt_path",
    "source_integrity_receipt": "source_integrity_receipt_path",
    "shard": "shard_path",
    "shard_manifest": "shard_manifest_path",
    "split_receipt": "split_receipt_path",
    "contamination_receipt": "contamination_receipt_path",
    "diversity_receipt": "diversity_receipt_path",
    "selection_receipt": "selection_receipt_path",
}
_RECEIPT_FILENAMES = {
    "suite_report": "suite_report.json",
    "license_receipt": "license_receipt.json",
    "source_presence_receipt": "source_presence_receipt.json",
    "source_integrity_receipt": "source_integrity_receipt.json",
    "split_receipt": "split_receipt.json",
    "contamination_receipt": "contamination_receipt.json",
    "diversity_receipt": "diversity_receipt.json",
    "selection_receipt": "selection_receipt.json",
}
_LOCAL_PROFILE = {
    "profile": "wsl2_local_nf4",
    "quantization": "nf4_double_quant",
    "core_dtype": "bf16",
    "projection_dtype": "bf16",
    "gradient_checkpointing": True,
    "sequence_length": 512,
    "microbatch_size": 1,
    "gradient_accumulation": 32,
    "data_loader_workers": 8,
    "max_ram_gb": 24.0,
    "max_vram_gb": 7.5,
}
_BUDGET = {
    "paid_compute_usd": 0,
    "paid_compute_ceiling_usd": 0,
    "cloud_jobs_used": 0,
    "cloud_jobs_ceiling": 0,
    "cloud_lifetime_cap_usd": 45,
}
_SOURCE_POLICY = {
    "root": "C:\\pneuma-data",
    "write_allowed": False,
    "private_cloud_transfer": False,
}
_OUTPUT_ROOT = "build/foundation/runs/"
_PROTECTED_DATA_ROOT = Path(r"C:\pneuma-data")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_UTC_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)


class FoundationAuthorizationError(ValueError):
    """Raised before model allocation when an authorization binding fails."""


@dataclass(frozen=True)
class VerifiedFoundationAuthorization:
    model_key: str
    token_ceiling: int
    shard_path: Path
    shard_manifest_path: Path
    output_root: Path
    authorized_lane_weights: Mapping
    scope_digest: str
    manifest: Mapping


@dataclass
class _HeldArtifact:
    path: Path
    handle: BoundArtifactReadHandle
    read: BoundArtifactRead


def _semantic_key(key: str) -> str:
    return unicodedata.normalize("NFKC", key).casefold()


def _validated_json_value(value: Any, *, path: str = "scope") -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise FoundationAuthorizationError(
                f"{path} JSON number must be finite"
            )
        return value
    if isinstance(value, list):
        return [
            _validated_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        result = {}
        semantic_keys: set[str] = set()
        for key, item in value.items():
            if not isinstance(key, str):
                raise FoundationAuthorizationError(
                    f"{path} JSON object key must be a string"
                )
            semantic = _semantic_key(key)
            if semantic in semantic_keys:
                raise FoundationAuthorizationError(
                    f"{path} contains duplicate semantic key aliases"
                )
            semantic_keys.add(semantic)
            result[key] = _validated_json_value(item, path=f"{path}.{key}")
        return result
    raise FoundationAuthorizationError(
        f"{path} is not JSON-safe: {type(value).__name__}"
    )


def _reject_constant(value: str) -> None:
    raise FoundationAuthorizationError(f"JSON number must be finite: {value}")


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    semantic_keys: set[str] = set()
    for key, value in pairs:
        if key in result:
            raise FoundationAuthorizationError(f"duplicate JSON member: {key}")
        semantic = _semantic_key(key)
        if semantic in semantic_keys:
            raise FoundationAuthorizationError(
                f"duplicate semantic JSON member alias: {key}"
            )
        semantic_keys.add(semantic)
        result[key] = value
    return result


def _strict_json_bytes(payload: bytes, *, label: str) -> dict:
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, FoundationAuthorizationError) as exc:
        raise FoundationAuthorizationError(f"cannot load strict JSON {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise FoundationAuthorizationError(f"expected JSON object: {label}")
    return value


def _strict_jsonl_records(payload: bytes, *, label: str) -> tuple[dict, ...]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FoundationAuthorizationError(
            f"cannot decode strict JSONL {label}: {exc}"
        ) from exc
    if not text or not text.endswith("\n"):
        raise FoundationAuthorizationError(
            f"{label} must be nonempty newline-terminated JSONL"
        )
    records = []
    for index, line in enumerate(text.splitlines(), start=1):
        if not line:
            raise FoundationAuthorizationError(
                f"{label} contains a blank line at {index}"
            )
        records.append(
            _strict_json_bytes(line.encode("utf-8"), label=f"{label} line {index}")
        )
    return tuple(records)


def _is_exact_positive_zero(value: Any) -> bool:
    return (
        type(value) is float
        and value == 0.0
        and math.copysign(1.0, value) > 0
    )


def _require_digest(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_PATTERN.fullmatch(value):
        raise FoundationAuthorizationError(f"{label} must be a SHA-256 digest")
    return value


def _coherence_error(detail: str) -> FoundationAuthorizationError:
    return FoundationAuthorizationError(
        f"foundation authorization artifact coherence failed: {detail}"
    )


def authorization_scope_digest(scope: Mapping) -> str:
    """Return the strict canonical digest of an immutable authorization scope."""

    canonical = _validated_json_value(scope)
    payload = json.dumps(
        canonical,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _absolute_lexical(path: Path) -> Path:
    candidate = Path(path)
    if ".." in candidate.parts:
        raise FoundationAuthorizationError("authorization path contains parent traversal")
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    return Path(os.path.abspath(candidate))


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _repo_relative(path: Path, *, repo_root: Path) -> str:
    root = _absolute_lexical(repo_root)
    candidate = _absolute_lexical(path)
    build_root = root / "build"
    if not _inside(candidate, build_root) or candidate == build_root:
        raise FoundationAuthorizationError(
            "authorization artifacts must be physical files under repository build/"
        )
    return candidate.relative_to(root).as_posix()


def _path_from_binding(binding: Mapping, *, repo_root: Path) -> Path:
    relative = binding.get("path")
    if (
        not isinstance(relative, str)
        or not relative.startswith("build/")
        or "\\" in relative
        or ".." in Path(relative).parts
    ):
        raise FoundationAuthorizationError("artifact binding path is not canonical")
    path = _absolute_lexical(Path(repo_root) / Path(relative))
    if _repo_relative(path, repo_root=repo_root) != relative:
        raise FoundationAuthorizationError("artifact binding path is not canonical")
    return path


@contextmanager
def _hold_artifacts(
    paths: Mapping[str, Path],
    *,
    repo_root: Path,
) -> Iterator[dict[str, _HeldArtifact]]:
    root = _absolute_lexical(repo_root)
    build_root = root / "build"
    held: dict[str, _HeldArtifact] = {}
    forbidden_roots = (
        (_PROTECTED_DATA_ROOT,)
        if _PROTECTED_DATA_ROOT.is_absolute()
        else ()
    )
    try:
        with ExitStack() as stack:
            for name, raw_path in paths.items():
                path = _absolute_lexical(raw_path)
                _repo_relative(path, repo_root=root)
                publication = stack.enter_context(
                    bind_artifact_publication(
                        path.parent,
                        anchor_root=root,
                        allowed_root=build_root,
                        forbidden_roots=forbidden_roots,
                    )
                )
                handle = stack.enter_context(publication.hold_read(path))
                held[name] = _HeldArtifact(
                    path=path,
                    handle=handle,
                    read=handle.read_bytes(),
                )
            yield held
    except FoundationAuthorizationError:
        raise
    except (ArtifactPublicationError, OSError, RuntimeError, TypeError, ValueError) as exc:
        raise FoundationAuthorizationError(f"artifact binding failed: {exc}") from exc


def _revalidate_held(held: Mapping[str, _HeldArtifact]) -> None:
    for item in held.values():
        item.handle.revalidate(item.read)


def artifact_binding(path: Path, repo_root: Path) -> dict:
    """Bind one artifact from a single no-follow handle read."""

    with _hold_artifacts({"artifact": Path(path)}, repo_root=repo_root) as held:
        item = held["artifact"]
        _revalidate_held(held)
        return {
            "path": _repo_relative(item.path, repo_root=repo_root),
            "sha256": item.read.sha256,
            "size": item.read.size,
        }


def _git(repo_root: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise FoundationAuthorizationError(f"cannot inspect git state: {exc}") from exc
    return completed.stdout.strip()


def current_clean_code_commit(repo_root: Path) -> str:
    """Return HEAD only when the repository has no tracked or untracked changes."""

    root = _absolute_lexical(repo_root)
    commit = _git(root, "rev-parse", "HEAD")
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise FoundationAuthorizationError("current git commit is not a full SHA-1")
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise FoundationAuthorizationError("foundation authorization requires a clean git checkout")
    return commit


def _validate_commit_binding(repo_root: Path, code_commit: str) -> None:
    if not isinstance(code_commit, str) or not _COMMIT_PATTERN.fullmatch(code_commit):
        raise FoundationAuthorizationError("code_commit must be a full lowercase git SHA-1")
    current = current_clean_code_commit(repo_root)
    if not hmac.compare_digest(current, code_commit):
        raise FoundationAuthorizationError("code_commit differs from the current clean checkout")


def _validate_manifest(manifest: Mapping) -> None:
    validator = Draft202012Validator(
        load_schema("foundation-training-authorization.schema.json"),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(dict(manifest)), key=lambda error: list(error.path))
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise FoundationAuthorizationError(f"authorization schema invalid: {detail}")


def _candidate_path(preparation: Any, *, repo_root: Path, stage: str) -> Path:
    expected = _absolute_lexical(
        Path(repo_root) / f"build/foundation/authorizations/candidates/{stage}.json"
    )
    actual = _absolute_lexical(preparation.authorization_candidate_path)
    if actual != expected:
        raise FoundationAuthorizationError("authorization candidate path is not exact")
    return actual


def _artifact_paths_from_preparation(preparation: Any) -> dict[str, Path]:
    try:
        return {
            name: Path(getattr(preparation, field))
            for name, field in _ARTIFACT_FIELDS.items()
        }
    except (AttributeError, TypeError) as exc:
        raise FoundationAuthorizationError("preparation result is incomplete") from exc


def _validate_exact_preparation_paths(paths: Mapping[str, Path]) -> None:
    preparation_root = _absolute_lexical(paths["preparation_manifest"].parent)
    expected_direct = {
        "preparation_manifest": "preparation_manifest.json",
        "suite_report": "suite_report.json",
        "license_receipt": "license_receipt.json",
        "source_presence_receipt": "source_presence_receipt.json",
        "source_integrity_receipt": "source_integrity_receipt.json",
        "split_receipt": "split_receipt.json",
        "contamination_receipt": "contamination_receipt.json",
        "diversity_receipt": "diversity_receipt.json",
        "selection_receipt": "selection_receipt.json",
    }
    for name, filename in expected_direct.items():
        if _absolute_lexical(paths[name]) != preparation_root / filename:
            raise FoundationAuthorizationError(
                f"preparation {name} path is not exact"
            )
    shard_root = preparation_root / "shards"
    if (
        _absolute_lexical(paths["shard"].parent) != shard_root
        or _absolute_lexical(paths["shard_manifest"].parent) != shard_root
    ):
        raise FoundationAuthorizationError(
            "preparation shard paths are not exact"
        )
    normalized = tuple(_absolute_lexical(path) for path in paths.values())
    if len(normalized) != len(set(normalized)):
        raise FoundationAuthorizationError(
            "preparation artifact paths must be distinct"
        )


def _validate_preparation_coherence_unchecked(
    scope: Mapping,
    bound_payloads: Mapping[str, BoundArtifactRead],
) -> None:
    """Prove all held preparation artifacts describe one exact local run."""

    if set(bound_payloads) != set(_ARTIFACT_FIELDS):
        raise _coherence_error("bound artifact set is incomplete")
    bindings = scope.get("artifacts")
    if not isinstance(bindings, Mapping) or set(bindings) != set(bound_payloads):
        raise _coherence_error("scope artifact bindings are incomplete")
    for name, read in bound_payloads.items():
        binding = bindings[name]
        if (
            not isinstance(binding, Mapping)
            or binding.get("sha256") != read.sha256
            or binding.get("size") != read.size
        ):
            raise _coherence_error(f"scope binding differs from held {name}")

    parsed = {
        name: _strict_json_bytes(read.payload, label=name.replace("_", " "))
        for name, read in bound_payloads.items()
        if name != "shard"
    }
    records = _strict_jsonl_records(
        bound_payloads["shard"].payload,
        label="foundation shard",
    )
    preparation = parsed["preparation_manifest"]
    model = scope.get("model")
    if not isinstance(model, Mapping) or model.get("key") not in MODEL_SPECS:
        raise _coherence_error("scope model key is not pinned")
    spec = MODEL_SPECS[model["key"]]
    if spec.key != "2b":
        raise _coherence_error(
            "the first local preparation authorizes only the exact 2b model"
        )
    expected_model = {
        "key": spec.key,
        "model_id": spec.model_id,
        "revision": spec.revision,
        "tokenizer_id": spec.model_id,
        "tokenizer_revision": spec.revision,
    }
    if dict(model) != expected_model:
        raise _coherence_error("scope model and tokenizer pin changed")
    stage = scope.get("stage")
    if stage not in _STAGE_TOKEN_CEILINGS:
        raise _coherence_error("scope stage is unknown")
    token_ceiling = _STAGE_TOKEN_CEILINGS[stage]
    if scope.get("token_ceiling") != token_ceiling:
        raise _coherence_error("scope stage and token ceiling differ")
    if (
        preparation.get("manifest_kind")
        != "pneuma_foundation_preparation_manifest"
        or preparation.get("manifest_schema_version") != "0.1.0"
        or preparation.get("stage") != stage
        or preparation.get("token_ceiling") != token_ceiling
        or preparation.get("dry_run") is not False
        or preparation.get("dataset_suite") != "all_ten_governed_groups"
        or preparation.get("gradient_lane")
        != "swe-gym-openhands-sampled"
        or preparation.get("training_authorized") is not False
        or not _is_exact_positive_zero(
            preparation.get("persisted_training_weight")
        )
    ):
        raise _coherence_error("preparation scope fields are not exact")

    tokenizer = preparation.get("tokenizer_snapshot")
    if not isinstance(tokenizer, Mapping) or tokenizer.get("model_id") != spec.model_id:
        raise _coherence_error("preparation tokenizer model differs from scope")
    if tokenizer.get("revision") != spec.revision:
        raise _coherence_error("preparation tokenizer revision differs from scope")
    tokenizer_receipt_digest = _require_digest(
        tokenizer.get("receipt_sha256"),
        label="tokenizer receipt",
    )
    tokenizer_snapshot_digest = _require_digest(
        tokenizer.get("snapshot_sha256"),
        label="tokenizer snapshot",
    )

    receipt_digests = preparation.get("receipt_sha256")
    expected_receipt_names = set(_RECEIPT_FILENAMES.values())
    if not isinstance(receipt_digests, Mapping) or set(receipt_digests) != expected_receipt_names:
        raise _coherence_error("preparation receipt digest map is not exact")
    for binding_name, filename in _RECEIPT_FILENAMES.items():
        expected = _require_digest(
            receipt_digests[filename],
            label=f"{filename} receipt binding",
        )
        if not hmac.compare_digest(expected, bound_payloads[binding_name].sha256):
            raise _coherence_error(f"{filename} digest differs from held bytes")

    generated = preparation.get("generated_artifact_sha256")
    if not isinstance(generated, Mapping) or set(generated) != {
        "conversion",
        "eval_identities",
    }:
        raise _coherence_error("generated artifact digest groups are incomplete")
    conversion = generated["conversion"]
    if not isinstance(conversion, Mapping) or set(conversion) != {
        "examples.jsonl",
        "invalid_examples.jsonl",
        "conversion_report.json",
        "hash_manifest.json",
    }:
        raise _coherence_error("generated conversion digest map is incomplete")
    for name, digest in conversion.items():
        _require_digest(digest, label=f"generated conversion {name}")
    eval_digests = generated["eval_identities"]
    if not isinstance(eval_digests, Mapping) or not eval_digests:
        raise _coherence_error("generated evaluation identity digests are empty")
    for family, digest in eval_digests.items():
        if not isinstance(family, str) or not family:
            raise _coherence_error("generated evaluation family is invalid")
        _require_digest(digest, label=f"generated evaluation identity {family}")

    source_receipt_hashes = preparation.get("source_receipt_hashes")
    if (
        not isinstance(source_receipt_hashes, list)
        or source_receipt_hashes != sorted(set(source_receipt_hashes))
    ):
        raise _coherence_error("preparation source receipt hashes are not canonical")
    for digest in source_receipt_hashes:
        _require_digest(digest, label="preparation source receipt")
    required_source_digests = {
        bound_payloads["license_receipt"].sha256,
        tokenizer_receipt_digest,
        tokenizer_snapshot_digest,
        conversion["conversion_report.json"],
        conversion["hash_manifest.json"],
    }
    if not required_source_digests.issubset(source_receipt_hashes):
        raise _coherence_error("generated and tokenizer sources lack receipts")

    record_ids = []
    for record in records:
        try:
            validate_foundation_record(record)
        except FoundationRecordError as exc:
            raise _coherence_error(f"shard record is invalid: {exc}") from exc
        source = record.get("source")
        disposition = record.get("disposition")
        split = record.get("split")
        rendered = record.get("rendered")
        forecasts = record.get("forecast_targets")
        tokenization = record.get("tokenization")
        if (
            not _is_exact_positive_zero(record.get("training_weight"))
            or not isinstance(source, Mapping)
            or source.get("dataset_family") != "swe-gym"
            or source.get("lane_id") != "swe-gym-openhands-sampled"
            or source.get("receipt_hashes") != source_receipt_hashes
            or not isinstance(disposition, Mapping)
            or disposition.get("terminal_role") != "train"
            or disposition.get("gradient_eligibility") != "first_stage"
            or not isinstance(split, Mapping)
            or split.get("split_id") != "train"
            or not isinstance(rendered, Mapping)
            or not isinstance(rendered.get("target_text"), str)
            or not rendered["target_text"].strip()
            or not isinstance(tokenization, Mapping)
            or tokenization.get("tokenizer_id") != spec.model_id
            or tokenization.get("tokenizer_revision") != spec.revision
            or tokenization.get("total_tokens")
            != tokenization.get("prompt_tokens", -1)
            + tokenization.get("target_tokens", -1)
            or not isinstance(forecasts, Mapping)
            or not any(
                isinstance(target, Mapping)
                and target.get("applicable") is True
                and target.get("provenance") == "observed_outcome"
                for target in forecasts.values()
            )
        ):
            raise _coherence_error("shard record is outside the exact gradient lane")
        record_ids.append(record["record_id"])
    if len(record_ids) != len(set(record_ids)):
        raise _coherence_error("shard record IDs are not unique")

    shard_digest = bound_payloads["shard"].sha256
    shard_entry = preparation.get("shard")
    shard_manifest = parsed["shard_manifest"]
    expected_inventory = build_diversity_inventory(records)
    if (
        not isinstance(shard_entry, Mapping)
        or shard_entry.get("artifact") != f"{shard_digest}.jsonl"
        or shard_entry.get("sha256") != shard_digest
        or shard_entry.get("example_count") != len(records)
        or shard_entry.get("manifest_artifact")
        != f"{shard_digest}.manifest.json"
        or shard_manifest.get("manifest_kind") != "pneuma_foundation_shard"
        or shard_manifest.get("schema_version") != "0.1.0"
        or shard_manifest.get("sha256") != shard_digest
        or shard_manifest.get("example_count") != len(records)
        or shard_manifest.get("duplicate_example_ids") != []
        or shard_manifest.get("inventory") != expected_inventory
        or shard_manifest.get("source_policy")
        != "read_only_external_corpus"
        or shard_manifest.get("token_ceiling") != token_ceiling
        or expected_inventory["token_count"] > token_ceiling
    ):
        raise _coherence_error("shard bytes, manifest, and preparation differ")

    gates = preparation.get("gates")
    if gates != {
        "all_ten_present": True,
        "eval_coverage_complete": True,
        "contamination_findings": 0,
        "source_unchanged": True,
        "tokenizer_recount_matches": True,
    }:
        raise _coherence_error("preparation gates are not exact")

    suite = parsed["suite_report"]
    suite_families = suite.get("families")
    suite_first_stage = suite.get("first_stage")
    if (
        suite.get("manifest_kind") != "pneuma_foundation_suite_report"
        or suite.get("manifest_schema_version") != "0.1.0"
        or not isinstance(suite_first_stage, Mapping)
        or suite_first_stage.get("stage") != stage
        or suite_first_stage.get("authorized_lane_candidates")
        != ["swe-gym-openhands-sampled"]
        or not isinstance(suite_families, list)
        or [item.get("family") for item in suite_families]
        != list(ACTIVE_DATASET_GROUPS)
        or any(item.get("exists") is not True for item in suite_families)
    ):
        raise _coherence_error("suite receipt does not prove all-ten presence")

    license_receipt = parsed["license_receipt"]
    if (
        license_receipt.get("receipt_kind") != "dataset_license_posture"
        or license_receipt.get("receipt_schema_version") != "0.1.0"
        or license_receipt.get("dataset_id") != "swe-gym-openhands-sampled"
        or license_receipt.get("decision")
        != "local_research_candidate_no_redistribution"
        or license_receipt.get("cloud_redistribution_allowed") is not False
        or license_receipt.get("requires_exact_operator_authorization")
        is not True
    ):
        raise _coherence_error("license receipt does not permit exact local research")

    source_presence = parsed["source_presence_receipt"]
    if (
        source_presence.get("manifest_kind")
        != "pneuma_foundation_source_presence_receipt"
        or source_presence.get("manifest_schema_version") != "0.1.0"
        or source_presence.get("all_ten_present") is not True
        or source_presence.get("before") != source_presence.get("after")
        or not isinstance(source_presence.get("before"), Mapping)
        or source_presence["before"].get("complete") is not True
        or source_presence.get("families")
        != source_presence["after"].get("families")
        or source_presence.get("lanes")
        != source_presence["after"].get("lanes")
    ):
        raise _coherence_error("source presence receipt contradicts all-ten gate")

    source_integrity = parsed["source_integrity_receipt"]
    if (
        source_integrity.get("manifest_kind")
        != "pneuma_foundation_source_integrity_receipt"
        or source_integrity.get("manifest_schema_version") != "0.1.0"
        or source_integrity.get("unchanged") is not True
        or source_integrity.get("before") != source_integrity.get("after")
        or source_integrity.get("all_ten_before")
        != source_integrity.get("all_ten_after")
        or not isinstance(source_integrity.get("all_ten_before"), Mapping)
        or source_integrity["all_ten_before"].get("complete") is not True
        or source_integrity.get("tokenizer_snapshot") != tokenizer
    ):
        raise _coherence_error("source integrity receipt contradicts source gate")

    contamination = parsed["contamination_receipt"]
    required_eval_families = contamination.get("required_evaluation_families")
    if (
        contamination.get("manifest_kind")
        != "pneuma_foundation_contamination_receipt"
        or contamination.get("manifest_schema_version") != "0.1.0"
        or contamination.get("training_identity_count") != len(records)
        or contamination.get("evaluation_coverage_complete") is not True
        or contamination.get("finding_count") != 0
        or contamination.get("findings") != []
        or contamination.get("repo_issue_disjoint") is not True
        or not isinstance(required_eval_families, list)
        or set(required_eval_families) != set(eval_digests)
    ):
        raise _coherence_error("contamination receipt contradicts disjointness gates")

    diversity = parsed["diversity_receipt"]
    if (
        diversity.get("manifest_kind")
        != "pneuma_foundation_diversity_receipt"
        or diversity.get("manifest_schema_version") != "0.1.0"
        or {
            key: value
            for key, value in diversity.items()
            if key not in {"manifest_kind", "manifest_schema_version"}
        }
        != expected_inventory
    ):
        raise _coherence_error("diversity receipt differs from shard inventory")

    selection = parsed["selection_receipt"]
    total_tokens = sum(record["tokenization"]["total_tokens"] for record in records)
    resolved_count = sum(
        record["observations"]["labels"]["resolved"] is True
        for record in records
    )
    if (
        selection.get("manifest_kind")
        != "pneuma_foundation_selection_receipt"
        or selection.get("manifest_schema_version") != "0.1.0"
        or selection.get("stage") != stage
        or selection.get("token_ceiling") != token_ceiling
        or selection.get("selected_record_count") != len(records)
        or type(selection.get("candidate_record_count")) is not int
        or selection["candidate_record_count"] < len(records)
        or selection.get("selected_record_ids") != record_ids
        or selection.get("selected_token_count") != total_tokens
        or selection.get("tokenizer_recount_total") != total_tokens
        or selection.get("resolved_count") != resolved_count
        or selection.get("unresolved_count") != len(records) - resolved_count
        or not _is_exact_positive_zero(
            selection.get("persisted_training_weight")
        )
    ):
        raise _coherence_error("selection receipt differs from shard records")

    split = parsed["split_receipt"]
    canonical_sets = split.get("canonical_repository_sets")
    if (
        split.get("manifest_kind")
        != "pneuma_foundation_repo_grouped_split_receipt"
        or split.get("manifest_schema_version") != "0.1.0"
        or split.get("repository_grouped") is not True
        or not isinstance(split.get("assignments"), list)
        or not isinstance(canonical_sets, Mapping)
        or set(canonical_sets) != {"train", "validation", "held_out"}
    ):
        raise _coherence_error("split receipt is incomplete")
    normalized_sets = {
        name: set(values) if isinstance(values, list) else None
        for name, values in canonical_sets.items()
    }
    if any(values is None for values in normalized_sets.values()) or any(
        normalized_sets[left] & normalized_sets[right]
        for index, left in enumerate(normalized_sets)
        for right in tuple(normalized_sets)[index + 1 :]
    ):
        raise _coherence_error("split receipt repository sets overlap")


def _validate_preparation_coherence(
    scope: Mapping,
    bound_payloads: Mapping[str, BoundArtifactRead],
) -> None:
    """Fail closed around the shared held-byte semantic validator."""

    try:
        _validate_preparation_coherence_unchecked(scope, bound_payloads)
    except FoundationAuthorizationError:
        raise
    except (
        AttributeError,
        KeyError,
        OverflowError,
        TypeError,
        ValueError,
    ) as exc:
        raise _coherence_error(f"malformed cross-artifact value: {exc}") from exc


def build_authorization_candidate(
    preparation: PreparationResult,
    *,
    repo_root: Path,
    code_commit: str,
    model_key: str = "2b",
) -> Path:
    """Build a nonauthorizing exact-scope candidate after preparation stabilizes."""

    root = _absolute_lexical(repo_root)
    _validate_commit_binding(root, code_commit)
    if model_key not in ("2b", "4b"):
        raise FoundationAuthorizationError("only pinned 2b or 4b models may be authorized")
    spec = MODEL_SPECS[model_key]
    artifact_paths = _artifact_paths_from_preparation(preparation)
    _validate_exact_preparation_paths(artifact_paths)
    with _hold_artifacts(artifact_paths, repo_root=root) as held:
        preparation_manifest = _strict_json_bytes(
            held["preparation_manifest"].read.payload,
            label="preparation manifest",
        )
        selection_receipt = _strict_json_bytes(
            held["selection_receipt"].read.payload,
            label="selection receipt",
        )
        stage = preparation_manifest.get("stage")
        if stage not in _STAGE_TOKEN_CEILINGS:
            raise FoundationAuthorizationError("preparation stage is not authorized")
        token_ceiling = _STAGE_TOKEN_CEILINGS[stage]
        if (
            preparation_manifest.get("training_authorized") is not False
            or preparation_manifest.get("persisted_training_weight") != 0.0
            or preparation_manifest.get("dry_run") is not False
            or preparation_manifest.get("token_ceiling") != token_ceiling
        ):
            raise FoundationAuthorizationError("preparation manifest is not a zero-weight final plan")
        if (
            selection_receipt.get("stage") != stage
            or selection_receipt.get("token_ceiling") != token_ceiling
        ):
            raise FoundationAuthorizationError("selection receipt ceiling differs from preparation")
        shard_entry = preparation_manifest.get("shard")
        if (
            not isinstance(shard_entry, Mapping)
            or shard_entry.get("artifact") != artifact_paths["shard"].name
            or shard_entry.get("manifest_artifact")
            != artifact_paths["shard_manifest"].name
        ):
            raise FoundationAuthorizationError(
                "preparation manifest shard paths are not exact"
            )
        candidate_path = _candidate_path(preparation, repo_root=root, stage=stage)
        bindings = {
            name: {
                "path": _repo_relative(item.path, repo_root=root),
                "sha256": item.read.sha256,
                "size": item.read.size,
            }
            for name, item in held.items()
        }
        scope = {
            "model": {
                "key": spec.key,
                "model_id": spec.model_id,
                "revision": spec.revision,
                "tokenizer_id": spec.model_id,
                "tokenizer_revision": spec.revision,
            },
            "stage": stage,
            "token_ceiling": token_ceiling,
            "local_profile": copy.deepcopy(_LOCAL_PROFILE),
            "learning_rates": [0.00005, 0.0001, 0.0002],
            "code_commit": code_commit,
            "artifacts": bindings,
            "authorized_lane_weights": copy.deepcopy(_AUTHORIZED_LANE_WEIGHTS),
            "source_data_policy": copy.deepcopy(_SOURCE_POLICY),
            "output_root": _OUTPUT_ROOT,
            "budget": copy.deepcopy(_BUDGET),
        }
        _validate_preparation_coherence(
            scope,
            {name: item.read for name, item in held.items()},
        )
        digest = authorization_scope_digest(scope)
        candidate = {
            "manifest_kind": "pneuma_foundation_training_authorization",
            "manifest_schema_version": "0.2.0",
            "authorization_status": "candidate",
            "scope": scope,
            "scope_digest": digest,
            "operator_approval": None,
        }
        _validate_manifest(candidate)
        try:
            with bind_artifact_publication(
                candidate_path.parent,
                anchor_root=root,
                allowed_root=root / "build",
                forbidden_roots=(
                    (_PROTECTED_DATA_ROOT,)
                    if _PROTECTED_DATA_ROOT.is_absolute()
                    else ()
                ),
            ) as publication:
                write_atomic_json(candidate_path, candidate, publication=publication)
                _revalidate_held(held)
        except (ArtifactPublicationError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise FoundationAuthorizationError(
                f"authorization candidate publication failed: {exc}"
            ) from exc
    return candidate_path


def required_approval_phrase(candidate: Mapping) -> str:
    """Return the exact phrase for a validated nonauthorizing candidate."""

    if not isinstance(candidate, Mapping):
        raise FoundationAuthorizationError("approval phrase requires a candidate mapping")
    _validate_manifest(candidate)
    if candidate.get("authorization_status") != "candidate":
        raise FoundationAuthorizationError("approval phrase requires candidate status")
    scope = candidate.get("scope")
    digest = candidate.get("scope_digest")
    computed = authorization_scope_digest(scope)
    if not isinstance(digest, str) or not hmac.compare_digest(digest, computed):
        raise FoundationAuthorizationError("candidate scope digest does not match")
    return f"{APPROVAL_PHRASE_PREFIX} {digest}"


def _repo_from_authorization_path(path: Path) -> Path:
    candidate = _absolute_lexical(path)
    for parent in candidate.parents:
        if parent.name == "build":
            return parent.parent
    raise FoundationAuthorizationError("authorization path is outside a repository build tree")


def _require_exact_authorization_path(path: Path, *, repo_root: Path, status: str, stage: str) -> Path:
    folder = "candidates" if status == "candidate" else "final"
    expected = _absolute_lexical(
        repo_root / f"build/foundation/authorizations/{folder}/{stage}.json"
    )
    actual = _absolute_lexical(path)
    if actual != expected:
        raise FoundationAuthorizationError(f"{status} authorization path is not exact")
    return actual


def _validated_utc_timestamp(value: str) -> str:
    if not isinstance(value, str) or not _UTC_PATTERN.fullmatch(value):
        raise FoundationAuthorizationError("approved_at must be a strict UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value.removesuffix("Z") + "+00:00")
    except ValueError as exc:
        raise FoundationAuthorizationError("approved_at is not a valid UTC timestamp") from exc
    if parsed.tzinfo != timezone.utc:
        raise FoundationAuthorizationError("approved_at must be UTC")
    return value


def finalize_authorization(
    candidate_path: Path,
    supplied_scope_digest: str,
    supplied_approval_phrase: str,
    operator_id: str,
    approved_at: str,
    output_path: Path,
) -> Path:
    """Convert one unchanged candidate into a separately published final authorization."""

    repo_root = _repo_from_authorization_path(candidate_path)
    candidate_path = _absolute_lexical(candidate_path)
    with _hold_artifacts({"candidate": candidate_path}, repo_root=repo_root) as held:
        candidate = _strict_json_bytes(
            held["candidate"].read.payload,
            label="authorization candidate",
        )
        _validate_manifest(candidate)
        if candidate.get("authorization_status") != "candidate":
            raise FoundationAuthorizationError("only a candidate may be finalized")
        scope = candidate["scope"]
        stage = scope["stage"]
        _require_exact_authorization_path(
            candidate_path,
            repo_root=repo_root,
            status="candidate",
            stage=stage,
        )
        output_path = _require_exact_authorization_path(
            output_path,
            repo_root=repo_root,
            status="authorized",
            stage=stage,
        )
        digest = candidate["scope_digest"]
        computed = authorization_scope_digest(scope)
        if not hmac.compare_digest(digest, computed):
            raise FoundationAuthorizationError("candidate scope digest does not match")
        if not isinstance(supplied_scope_digest, str) or not hmac.compare_digest(
            supplied_scope_digest,
            digest,
        ):
            raise FoundationAuthorizationError("supplied scope digest does not match")
        expected_phrase = f"{APPROVAL_PHRASE_PREFIX} {digest}"
        if not isinstance(supplied_approval_phrase, str) or not hmac.compare_digest(
            supplied_approval_phrase,
            expected_phrase,
        ):
            raise FoundationAuthorizationError("supplied approval phrase does not match")
        if (
            not isinstance(operator_id, str)
            or not operator_id.strip()
            or operator_id != operator_id.strip()
        ):
            raise FoundationAuthorizationError("operator_id must be a nonempty exact string")
        approved_at = _validated_utc_timestamp(approved_at)
        final = {
            "manifest_kind": candidate["manifest_kind"],
            "manifest_schema_version": candidate["manifest_schema_version"],
            "authorization_status": "authorized",
            "scope": copy.deepcopy(scope),
            "scope_digest": digest,
            "operator_approval": {
                "operator_id": operator_id,
                "approved_at": approved_at,
                "scope_digest": digest,
                "approval_phrase_sha256": hashlib.sha256(
                    supplied_approval_phrase.encode("utf-8")
                ).hexdigest(),
            },
        }
        _validate_manifest(final)
        try:
            with bind_artifact_publication(
                output_path.parent,
                anchor_root=repo_root,
                allowed_root=repo_root / "build",
                forbidden_roots=(
                    (_PROTECTED_DATA_ROOT,)
                    if _PROTECTED_DATA_ROOT.is_absolute()
                    else ()
                ),
            ) as publication:
                write_atomic_json(output_path, final, publication=publication)
                _revalidate_held(held)
        except (ArtifactPublicationError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise FoundationAuthorizationError(
                f"final authorization publication failed: {exc}"
            ) from exc
    return output_path


def _assert_exact_scope(scope: Mapping, *, repo_root: Path) -> None:
    model = scope.get("model")
    if not isinstance(model, Mapping) or model.get("key") not in ("2b", "4b"):
        raise FoundationAuthorizationError("authorization model key is not permitted")
    spec = MODEL_SPECS[model["key"]]
    if dict(model) != {
        "key": spec.key,
        "model_id": spec.model_id,
        "revision": spec.revision,
        "tokenizer_id": spec.model_id,
        "tokenizer_revision": spec.revision,
    }:
        raise FoundationAuthorizationError("authorization does not match the model/tokenizer pin")
    stage = scope.get("stage")
    if stage not in _STAGE_TOKEN_CEILINGS:
        raise FoundationAuthorizationError("authorization stage is unknown")
    if scope.get("token_ceiling") != _STAGE_TOKEN_CEILINGS[stage]:
        raise FoundationAuthorizationError("authorization stage and ceiling differ")
    if scope.get("local_profile") != _LOCAL_PROFILE:
        raise FoundationAuthorizationError("authorization is not the exact local profile")
    if scope.get("learning_rates") != [0.00005, 0.0001, 0.0002]:
        raise FoundationAuthorizationError("authorization learning-rate scope changed")
    if scope.get("authorized_lane_weights") != _AUTHORIZED_LANE_WEIGHTS:
        raise FoundationAuthorizationError("authorization lane-weight map changed")
    if scope.get("source_data_policy") != _SOURCE_POLICY:
        raise FoundationAuthorizationError("protected source policy changed")
    if scope.get("output_root") != _OUTPUT_ROOT:
        raise FoundationAuthorizationError("authorization output root changed")
    if scope.get("budget") != _BUDGET:
        raise FoundationAuthorizationError("authorization budget must remain zero-paid local")
    _validate_commit_binding(repo_root, scope.get("code_commit"))


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    return value


def verify_foundation_authorization(
    authorization_path: Path,
    *,
    repo_root: Path,
    registry_path: Path | None = None,
) -> VerifiedFoundationAuthorization:
    """Verify one exact final authorization and every held artifact before use."""

    del registry_path
    root = _absolute_lexical(repo_root)
    path = _absolute_lexical(authorization_path)
    pending_template = _absolute_lexical(
        root
        / "docs/data/training-authorizations/"
        "pneuma-foundation-v0.pending.json"
    )
    if path == pending_template:
        raise FoundationAuthorizationError("foundation training is not authorized")
    try:
        with _hold_artifacts({"authorization": path}, repo_root=root) as authorization_held:
            manifest = _strict_json_bytes(
                authorization_held["authorization"].read.payload,
                label="foundation authorization",
            )
            _validate_manifest(manifest)
            status = manifest.get("authorization_status")
            if status != "authorized":
                raise FoundationAuthorizationError("foundation training is not authorized")
            scope = manifest["scope"]
            stage = scope["stage"]
            _require_exact_authorization_path(
                path,
                repo_root=root,
                status="authorized",
                stage=stage,
            )
            digest = manifest["scope_digest"]
            computed = authorization_scope_digest(scope)
            approval = manifest["operator_approval"]
            if not hmac.compare_digest(digest, computed):
                raise FoundationAuthorizationError("authorization scope digest does not match")
            if not hmac.compare_digest(approval["scope_digest"], digest):
                raise FoundationAuthorizationError("operator scope digest does not match")
            phrase = f"{APPROVAL_PHRASE_PREFIX} {digest}"
            phrase_sha256 = hashlib.sha256(phrase.encode("utf-8")).hexdigest()
            if not hmac.compare_digest(
                approval["approval_phrase_sha256"],
                phrase_sha256,
            ):
                raise FoundationAuthorizationError("operator approval phrase hash changed")
            if (
                not isinstance(approval["operator_id"], str)
                or not approval["operator_id"].strip()
                or approval["operator_id"] != approval["operator_id"].strip()
            ):
                raise FoundationAuthorizationError("operator approval is invalid")
            _validated_utc_timestamp(approval["approved_at"])
            _assert_exact_scope(scope, repo_root=root)
            bindings = scope["artifacts"]
            if set(bindings) != set(_ARTIFACT_FIELDS):
                raise FoundationAuthorizationError("authorization artifact set is incomplete")
            paths = {
                name: _path_from_binding(binding, repo_root=root)
                for name, binding in bindings.items()
            }
            _validate_exact_preparation_paths(paths)
            with _hold_artifacts(paths, repo_root=root) as artifact_held:
                for name, item in artifact_held.items():
                    binding = bindings[name]
                    if (
                        not hmac.compare_digest(item.read.sha256, binding["sha256"])
                        or item.read.size != binding["size"]
                    ):
                        raise FoundationAuthorizationError(
                            f"authorized artifact digest or size changed: {name}"
                        )
                _validate_preparation_coherence(
                    scope,
                    {
                        name: item.read
                        for name, item in artifact_held.items()
                    },
                )
                _revalidate_held(artifact_held)
                _revalidate_held(authorization_held)
                frozen_manifest = _deep_freeze(copy.deepcopy(manifest))
                return VerifiedFoundationAuthorization(
                    model_key=scope["model"]["key"],
                    token_ceiling=scope["token_ceiling"],
                    shard_path=paths["shard"],
                    shard_manifest_path=paths["shard_manifest"],
                    output_root=root / Path(scope["output_root"]),
                    authorized_lane_weights=_deep_freeze(
                        copy.deepcopy(scope["authorized_lane_weights"])
                    ),
                    scope_digest=digest,
                    manifest=frozen_manifest,
                )
    except FoundationAuthorizationError:
        raise
    except (ArtifactPublicationError, OSError, RuntimeError, TypeError, ValueError) as exc:
        raise FoundationAuthorizationError(f"authorization verification failed: {exc}") from exc


def apply_verified_authorization(
    record: Mapping,
    authorization: VerifiedFoundationAuthorization,
) -> EffectiveTrainingRecord:
    """Apply one in-memory lane weight without mutating the persisted record."""

    if not isinstance(authorization, VerifiedFoundationAuthorization):
        raise FoundationAuthorizationError("a verified foundation authorization is required")
    if not isinstance(record, Mapping):
        raise FoundationAuthorizationError("foundation record must be a mapping")
    weight = record.get("training_weight")
    if (
        type(weight) is not float
        or weight != 0.0
        or math.copysign(1.0, weight) < 0
    ):
        raise FoundationAuthorizationError("persisted training weight must be exactly +0.0")
    try:
        validate_foundation_record(record)
    except FoundationRecordError as exc:
        raise FoundationAuthorizationError(f"foundation record is invalid: {exc}") from exc
    source = record.get("source")
    lane = source.get("lane_id") if isinstance(source, Mapping) else None
    if lane not in authorization.authorized_lane_weights:
        raise FoundationAuthorizationError("foundation record lane is not exactly authorized")
    if lane != "swe-gym-openhands-sampled" or source.get("dataset_family") != "swe-gym":
        raise FoundationAuthorizationError("foundation record lane is outside the exact scope")
    disposition = record.get("disposition")
    if (
        not isinstance(disposition, Mapping)
        or disposition.get("terminal_role") != "train"
        or disposition.get("gradient_eligibility") != "first_stage"
    ):
        raise FoundationAuthorizationError("foundation record is not eligible for this lane")
    rendered = record.get("rendered")
    target_text = rendered.get("target_text") if isinstance(rendered, Mapping) else None
    if not isinstance(target_text, str) or not target_text.strip():
        raise FoundationAuthorizationError("foundation record target text must be nonempty")
    forecasts = record.get("forecast_targets")
    applicable = (
        isinstance(forecasts, Mapping)
        and any(
            isinstance(target, Mapping)
            and target.get("applicable") is True
            and target.get("provenance") == "observed_outcome"
            and isinstance(target.get("value"), (int, float))
            and not isinstance(target.get("value"), bool)
            and math.isfinite(target["value"])
            for target in forecasts.values()
        )
    )
    if not applicable:
        raise FoundationAuthorizationError(
            "foundation record needs an applicable outcome-derived forecast"
        )
    effective_weight = authorization.authorized_lane_weights[lane]
    if type(effective_weight) is not float or effective_weight <= 0 or not math.isfinite(effective_weight):
        raise FoundationAuthorizationError("authorized effective weight is invalid")
    return EffectiveTrainingRecord(record=record, effective_weight=effective_weight)


__all__ = [
    "APPROVAL_PHRASE_PREFIX",
    "FoundationAuthorizationError",
    "VerifiedFoundationAuthorization",
    "apply_verified_authorization",
    "artifact_binding",
    "authorization_scope_digest",
    "build_authorization_candidate",
    "current_clean_code_commit",
    "finalize_authorization",
    "required_approval_phrase",
    "verify_foundation_authorization",
]
