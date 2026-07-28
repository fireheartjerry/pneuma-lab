"""Canonical, fail-closed artifact IO for the resampling-null study."""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import mimetypes
from pathlib import Path, PurePosixPath
from typing import Any, Literal, cast

from jsonschema import Draft202012Validator

from pneuma_lab import schemas as pneuma_schemas
from pneuma_lab.foundation.artifacts import (
    canonical_json_bytes,
    write_atomic_bytes,
    write_atomic_json,
    write_atomic_jsonl,
)

from .types import ArtifactRef


SCHEMA_BY_KIND = {
    "resampling_study_manifest": "resampling-study-manifest.schema.json",
    "resampling_prefix_schedule": "resampling-prefix-schedule.schema.json",
    "resampling_prefix_receipt": "resampling-prefix-receipt.schema.json",
    "resampling_assignment_ledger": "resampling-assignment-ledger.schema.json",
    "resampling_packet_index": "resampling-packet-index.schema.json",
    "resampling_task_block": "resampling-task-block.schema.json",
    "resampling_blinded_projection": "resampling-blinded-projection.schema.json",
    "resampling_analysis_freeze": "resampling-analysis-freeze.schema.json",
    "resampling_analysis": "resampling-analysis.schema.json",
    "resampling_power_report": "resampling-power-report.schema.json",
    "resampling_unblind_receipt": "resampling-unblind-receipt.schema.json",
    "resampling_artifact_root": "resampling-artifact-root.schema.json",
}

_SCIENTIFIC_REF_KEYS = frozenset(
    {"role", "relative_path", "sha256", "byte_count", "media_type"}
)
_SINGLETON_KINDS = frozenset(
    {
        "resampling_study_manifest",
        "resampling_prefix_schedule",
        "resampling_prefix_receipt",
        "resampling_assignment_ledger",
        "resampling_blinded_projection",
        "resampling_analysis_freeze",
        "resampling_analysis",
        "resampling_unblind_receipt",
    }
)
_OPERATIONAL_TOP_LEVEL = frozenset({"operational"})
_RECEIPT_NAME = "p0-core-receipt.json"


class RecordValidationError(ValueError):
    """Raised when a scientific record or its artifact closure is invalid."""


def _plain_json(value: object, *, path: str = "$") -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise RecordValidationError(f"{path}: JSON object keys must be strings")
            result[key] = _plain_json(nested, path=f"{path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [
            _plain_json(nested, path=f"{path}[{index}]")
            for index, nested in enumerate(value)
        ]
    if isinstance(value, float) and not math.isfinite(value):
        raise RecordValidationError(f"{path}: non-finite number")
    return value


def canonical_digest(value: Mapping[str, object]) -> str:
    """Return the stable compact-JSON SHA-256 for one mapping."""

    return hashlib.sha256(
        canonical_json_bytes(dict(value), indent=None)
    ).hexdigest()


def _validation_error_key(error: Any) -> tuple[tuple[str, ...], str]:
    return tuple(str(part) for part in error.absolute_path), error.message


def _semantic_unique(
    values: object,
    field: str,
    *,
    key: str,
) -> None:
    if not isinstance(values, list):
        return
    observed: list[object] = []
    for item in values:
        if isinstance(item, Mapping):
            observed.append(item.get(key))
    if len(observed) != len(set(observed)):
        raise RecordValidationError(f"{field} must have unique {key} values")


def _validate_semantics(value: dict[str, object]) -> None:
    kind = cast(str, value["record_kind"])
    payload = cast(dict[str, object], value["payload"])
    if kind == "resampling_prefix_schedule":
        tasks = cast(list[object], payload["tasks"])
        task_ids: list[object] = []
        for index, item in enumerate(tasks):
            if not isinstance(item, Mapping):
                continue
            task = item.get("task")
            if isinstance(task, Mapping):
                task_ids.append(task.get("task_id"))
                groups = task.get("sensitivity_groups")
                _semantic_unique(
                    groups,
                    f"payload.tasks[{index}].task.sensitivity_groups",
                    key="kind",
                )
            slots = item.get("slots")
            for slot_key in ("slot_id", "seed", "execution_order"):
                _semantic_unique(
                    slots,
                    f"payload.tasks[{index}].slots",
                    key=slot_key,
                )
        if len(task_ids) != len(set(task_ids)):
            raise RecordValidationError("payload.tasks must have unique task_id values")
    elif kind == "resampling_prefix_receipt":
        _semantic_unique(
            payload["task_receipts"],
            "payload.task_receipts",
            key="task_id",
        )
    elif kind == "resampling_assignment_ledger":
        _semantic_unique(payload["assignments"], "payload.assignments", key="task_id")
        _semantic_unique(
            payload["allocation_receipts"],
            "payload.allocation_receipts",
            key="task_id",
        )
        for assignment in cast(list[object], payload["assignments"]):
            if not isinstance(assignment, Mapping):
                continue
            if assignment.get("task_id") == assignment.get("donor_task_id"):
                raise RecordValidationError(
                    "assignment task_id and donor_task_id must differ"
                )
            if assignment.get("task_lineage") == assignment.get("donor_lineage"):
                raise RecordValidationError(
                    "assignment task and donor lineages must differ"
                )
            slot_arms = assignment.get("slot_arms")
            if isinstance(slot_arms, list):
                slot_ids = [
                    item[0]
                    for item in slot_arms
                    if isinstance(item, list) and len(item) == 2
                ]
                arms = [
                    item[1]
                    for item in slot_arms
                    if isinstance(item, list) and len(item) == 2
                ]
                if len(slot_ids) != len(set(slot_ids)):
                    raise RecordValidationError(
                        "assignment slot_arms must have unique slot IDs"
                    )
                if sorted(arms) != ["NONE", "REAL", "RESAMPLE", "SHAM"]:
                    raise RecordValidationError(
                        "assignment slot_arms must contain every arm exactly once"
                    )
    elif kind == "resampling_packet_index":
        entries = payload.get("entries")
        _semantic_unique(entries, "payload.entries", key="task_id")
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, Mapping) or "real_ref" not in entry:
                    continue
                if entry.get("task_id") == entry.get("donor_task_id"):
                    raise RecordValidationError(
                        "packet pair task_id and donor_task_id must differ"
                    )
                if entry.get("real_token_count") != entry.get("sham_token_count"):
                    raise RecordValidationError(
                        "packet pair real/sham token counts must match"
                    )
                if entry.get("rewrite_expected") != entry.get("rewrite_completed"):
                    raise RecordValidationError(
                        "packet pair identifier rewrites must be complete"
                    )
    elif kind == "resampling_task_block":
        _semantic_unique(
            payload["sensitivity_groups"],
            "payload.sensitivity_groups",
            key="kind",
        )
        _semantic_unique(
            payload["slot_outcomes"],
            "payload.slot_outcomes",
            key="opaque_arm_id",
        )
        outcomes = cast(list[Mapping[str, object]], payload["slot_outcomes"])
        for outcome in outcomes:
            if (
                outcome.get("task_id") != payload["task_id"]
                or outcome.get("benchmark") != payload["benchmark"]
            ):
                raise RecordValidationError(
                    "slot outcome task/benchmark must match its task block"
                )
            if (
                outcome.get("infrastructure_failure") is True
                and outcome.get("success") != 0
            ):
                raise RecordValidationError(
                    "infrastructure-failure outcomes must have success == 0"
                )
        attempts = payload.get("attempts")
        if isinstance(attempts, list):
            indices = [
                attempt.get("attempt_index")
                for attempt in attempts
                if isinstance(attempt, Mapping)
            ]
            if indices != list(range(len(indices))):
                raise RecordValidationError(
                    "payload.attempts must be chronological from attempt 0"
                )
            selected = payload.get("selected_attempt_index")
            if selected not in indices:
                raise RecordValidationError(
                    "selected_attempt_index must identify an embedded attempt"
                )
            selected_attempt = attempts[cast(int, selected)]
            if (
                not isinstance(selected_attempt, Mapping)
                or selected_attempt.get("complete") is not True
            ):
                raise RecordValidationError("selected attempt must be complete")
        if payload.get("triggered") is False:
            no_trigger_outcomes = cast(
                list[dict[str, object]],
                payload["slot_outcomes"],
            )
            copied_fields = (
                "success",
                "prefix_success",
                "partial_reward",
                "infrastructure_failure",
                "counters",
                "artifact_ref",
            )
            signatures = [
                tuple(
                    json.dumps(outcome.get(field), sort_keys=True)
                    for field in copied_fields
                )
                for outcome in no_trigger_outcomes
            ]
            if len(set(signatures)) != 1:
                raise RecordValidationError(
                    "no-trigger slot_outcomes must be four copied Y_0 outcomes"
                )
    elif kind == "resampling_blinded_projection":
        _semantic_unique(payload["task_block_refs"], "task_block_refs", key="relative_path")
        _semantic_unique(payload["rows"], "rows", key="task_id")
        rows = cast(list[object], payload["rows"])
        if len(rows) != cast(int, payload["expected_task_count"]):
            raise RecordValidationError(
                "expected_task_count must equal the number of rows"
            )
        if len(cast(list[object], payload["task_block_refs"])) != len(rows):
            raise RecordValidationError(
                "task_block_refs and rows must have equal coverage"
            )
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            slots = row.get("slots")
            if isinstance(slots, list):
                labels = [
                    slot.get("label")
                    for slot in slots
                    if isinstance(slot, Mapping)
                ]
                if labels != ["A", "B", "C", "D"]:
                    raise RecordValidationError(
                        "blinded slots must be ordered A, B, C, D"
                    )
    elif kind == "resampling_artifact_root":
        entries = cast(list[dict[str, object]], payload["entries"])
        paths = [cast(str, entry["relative_path"]) for entry in entries]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise RecordValidationError(
                "artifact-root entries must have unique sorted relative paths"
            )
        if _RECEIPT_NAME in paths:
            raise RecordValidationError("artifact root must exclude its own receipt")
        required = cast(list[str], payload["required_document_kinds"])
        if required != sorted(required):
            raise RecordValidationError(
                "required_document_kinds must be sorted"
            )
    elif kind == "resampling_power_report":
        stage = payload["stage"]
        if stage == "selection":
            selected = cast(list[object], payload["selected_cells"])
            if (
                payload["selection_count"] != len(selected)
                or cast(int, payload["candidate_count"]) < len(selected)
            ):
                raise RecordValidationError(
                    "power selection counts do not match selected_cells"
                )
        elif (
            stage == "validation"
            and payload["phase"] == "full_multiplier_fallback"
        ):
            cells = cast(list[object], payload["complete_cell_ids"])
            if (
                payload["expected_cell_count"] != len(cells)
                or payload["observed_cell_count"] != len(cells)
            ):
                raise RecordValidationError(
                    "full-multiplier validation must cover every declared cell"
                )


def validate_record(value: Mapping[str, object]) -> dict[str, object]:
    """Validate and return a detached plain-JSON scientific record."""

    if not isinstance(value, Mapping):
        raise RecordValidationError("record must be a mapping")
    plain = _plain_json(value)
    if not isinstance(plain, dict):
        raise RecordValidationError("record must be a JSON object")
    record_kind = plain.get("record_kind")
    if not isinstance(record_kind, str) or record_kind not in SCHEMA_BY_KIND:
        raise RecordValidationError(f"unknown record_kind: {record_kind!r}")
    schema = pneuma_schemas.load_schema(SCHEMA_BY_KIND[record_kind])
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(plain), key=_validation_error_key)
    if errors:
        rendered: list[str] = []
        for error in errors:
            location = "$"
            if error.absolute_path:
                location += "".join(f"[{part!r}]" for part in error.absolute_path)
            rendered.append(f"{location}: {error.message}")
        raise RecordValidationError("; ".join(rendered))
    # The frozen value type applies path-normalization checks that are awkward
    # to express portably in ECMA-262 regular expressions.
    tuple(_walk_artifact_refs(plain))
    _validate_semantics(plain)
    return cast(dict[str, object], plain)


def _reject_constant(value: str) -> object:
    raise RecordValidationError(f"non-finite JSON constant {value!r}")


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RecordValidationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _load_json_bytes(payload: bytes, *, source: Path) -> object:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise RecordValidationError(f"{source}: UTF-8 BOM is forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except RecordValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecordValidationError(f"{source}: invalid UTF-8 JSON: {exc}") from exc


def load_record(path: Path) -> dict[str, object]:
    """Load strict UTF-8 JSON and validate it as one registered record."""

    source = Path(path)
    try:
        payload = source.read_bytes()
    except OSError as exc:
        raise RecordValidationError(f"cannot read record {source}: {exc}") from exc
    value = _load_json_bytes(payload, source=source)
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{source}: record must be a JSON object")
    return validate_record(cast(Mapping[str, object], value))


def _run_root(run_root: Path) -> Path:
    root = Path(run_root).resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    return root


def _resolve_inside(
    path: Path,
    run_root: Path,
    *,
    require_exists: bool,
) -> tuple[Path, str]:
    root = _run_root(run_root)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=require_exists)
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise RecordValidationError(
            f"artifact path escapes run_root: {path}"
        ) from exc
    if relative == Path("."):
        raise RecordValidationError("artifact path must name a file below run_root")
    relative_path = PurePosixPath(*relative.parts).as_posix()
    return resolved, relative_path


def _manifest_records(run_root: Path) -> list[tuple[Path, dict[str, object]]]:
    root = _run_root(run_root)
    found: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(root.rglob("*.json")):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in (
            _OPERATIONAL_TOP_LEVEL | {"sources"}
        ):
            continue
        try:
            raw = _load_json_bytes(path.read_bytes(), source=path)
        except (OSError, RecordValidationError):
            continue
        if (
            isinstance(raw, Mapping)
            and raw.get("record_kind") == "resampling_study_manifest"
        ):
            found.append((path, validate_record(cast(Mapping[str, object], raw))))
    return found


def _require_manifest_ancestry(
    record: Mapping[str, object],
    *,
    run_root: Path,
) -> None:
    manifests = _manifest_records(run_root)
    if len(manifests) != 1:
        raise RecordValidationError(
            "exactly one study manifest must exist before scientific descendants"
        )
    manifest = manifests[0][1]
    for field in ("study_id", "frozen_created_at", "provenance"):
        if record.get(field) != manifest.get(field):
            raise RecordValidationError(
                f"scientific descendant {field} does not match study manifest"
            )


def _artifact_ref_for_path(path: Path, run_root: Path, role: str, media_type: str) -> ArtifactRef:
    resolved, relative_path = _resolve_inside(path, run_root, require_exists=True)
    payload = resolved.read_bytes()
    return ArtifactRef(
        role=role,
        relative_path=relative_path,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type=media_type,
    )


def _prepare_destination(path: Path, run_root: Path) -> tuple[Path, str]:
    target, relative_path = _resolve_inside(path, run_root, require_exists=False)
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    rebound, rebound_relative = _resolve_inside(
        target,
        run_root,
        require_exists=False,
    )
    if rebound != target or rebound_relative != relative_path:
        raise RecordValidationError("artifact destination ancestry changed")
    return target, relative_path


def write_record(
    path: Path,
    value: Mapping[str, object],
    *,
    run_root: Path,
    role: str,
) -> ArtifactRef:
    """Validate completely, publish atomically without overwrite, and reference."""

    validated = validate_record(value)
    if validated["record_kind"] != "resampling_study_manifest":
        _require_manifest_ancestry(validated, run_root=run_root)
    target, _relative = _prepare_destination(path, run_root)
    write_atomic_json(target, validated)
    return _artifact_ref_for_path(target, run_root, role, "application/json")


def write_jsonl_artifact(
    path: Path,
    rows: Iterable[Mapping[str, object]],
    *,
    run_root: Path,
    role: str,
) -> ArtifactRef:
    """Materialize, validate, and atomically publish one immutable JSONL blob."""

    materialized: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise RecordValidationError(f"JSONL row {index} must be a mapping")
        plain = _plain_json(row, path=f"$[{index - 1}]")
        if not isinstance(plain, dict):
            raise RecordValidationError(f"JSONL row {index} must be a JSON object")
        materialized.append(cast(dict[str, object], plain))
    # Prove every row serializes before a destination is created.
    for row in materialized:
        canonical_json_bytes(row, indent=None)
    target, _relative = _prepare_destination(path, run_root)
    write_atomic_jsonl(target, materialized)
    return _artifact_ref_for_path(
        target,
        run_root,
        role,
        "application/x-ndjson",
    )


def _normalized_source_name(path: Path) -> str:
    name = Path(path).name
    normalized = PurePosixPath(name).as_posix()
    if not normalized or normalized in {".", ".."} or "/" in normalized:
        raise ValueError(f"invalid source name: {path}")
    return normalized


def _media_type(path: Path) -> str:
    suffix = path.suffix.casefold()
    overrides = {
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
        ".md": "text/markdown",
        ".py": "text/x-python",
        ".txt": "text/plain",
    }
    if suffix in overrides:
        return overrides[suffix]
    guessed, _encoding = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _required_kind_list(value: object) -> list[str]:
    candidate = value
    if isinstance(candidate, Mapping):
        candidate = candidate.get("required_document_kinds")
    if not isinstance(candidate, list) or not candidate:
        raise RecordValidationError(
            "required-document-kinds source must contain a non-empty JSON array"
        )
    if not all(isinstance(kind, str) for kind in candidate):
        raise RecordValidationError("required document kinds must be strings")
    kinds = cast(list[str], candidate)
    if (
        kinds != sorted(kinds)
        or len(kinds) != len(set(kinds))
        or "resampling_artifact_root" in kinds
        or any(kind not in SCHEMA_BY_KIND for kind in kinds)
    ):
        raise RecordValidationError(
            "required document kinds must be sorted, unique upstream kinds"
        )
    return kinds


@dataclass(frozen=True, slots=True)
class _SourceCopy:
    source: Path
    payload: bytes
    destination: Path
    ref: ArtifactRef


def _plan_source_copy(
    source: Path,
    *,
    run_root: Path,
    subtree: str,
    role: str,
) -> _SourceCopy:
    source_path = Path(source).resolve(strict=True)
    if not source_path.is_file():
        raise ValueError(f"source must be a file: {source}")
    payload = source_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    name = _normalized_source_name(source_path)
    relative = PurePosixPath("sources", subtree, f"{digest}-{name}").as_posix()
    destination, checked_relative = _resolve_inside(
        Path(run_root) / Path(relative),
        run_root,
        require_exists=False,
    )
    if checked_relative != relative:
        raise RecordValidationError("source destination path was not canonical")
    ref = ArtifactRef(
        role=role,
        relative_path=relative,
        sha256=digest,
        byte_count=len(payload),
        media_type=_media_type(source_path),
    )
    return _SourceCopy(source_path, payload, destination, ref)


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return cast(dict[str, object], asdict(ref))


def seal_study_manifest(
    study_source: Path,
    tasks_source: Path,
    roster_source: Path,
    assignment_program_source: Path,
    provider_lane_plan_source: Path,
    tokenizer_source: Path,
    packet_template_source: Path,
    packet_policy_source: Path,
    pad_unit_set_source: Path,
    source_revision_sources: Sequence[Path],
    required_document_kinds_source: Path,
    *,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Copy every external input and seal the first scientific record."""

    root = _run_root(run_root)
    existing_scientific = _scientific_documents(
        root,
        excluded={Path(out)},
    )
    if existing_scientific:
        raise FileExistsError(
            "study manifest must be the first scientific record in run_root"
        )
    if not source_revision_sources:
        raise ValueError("source_revision_sources must be non-empty")
    revision_names = [
        _normalized_source_name(path) for path in source_revision_sources
    ]
    if revision_names != sorted(revision_names):
        raise ValueError("source_revision_sources must be sorted by normalized source name")
    if len(revision_names) != len(set(revision_names)):
        raise ValueError("source_revision_sources must have unique normalized names")
    required_path = Path(required_document_kinds_source).resolve(strict=True)
    _required_kind_list(
        _load_json_bytes(required_path.read_bytes(), source=required_path)
    )

    source_path = Path(study_source).resolve(strict=True)
    template_raw = _load_json_bytes(source_path.read_bytes(), source=source_path)
    if not isinstance(template_raw, Mapping):
        raise RecordValidationError("study template must be a JSON object")
    template = cast(dict[str, object], _plain_json(template_raw))
    expected_top = {
        "record_kind",
        "schema_version",
        "study_id",
        "frozen_created_at",
        "provenance",
        "payload",
    }
    if set(template) != expected_top:
        raise RecordValidationError(
            "study template must contain exactly the scientific envelope fields"
        )
    if template.get("record_kind") != "resampling_study_manifest":
        raise RecordValidationError("study template has wrong record_kind")
    template_payload = template.get("payload")
    if (
        not isinstance(template_payload, Mapping)
        or set(template_payload) != {"seed_commitment_sha256"}
    ):
        raise RecordValidationError(
            "study template payload must contain only seed_commitment_sha256"
        )

    fixed_inputs = (
        (tasks_source, "task-registry", "task_registry"),
        (roster_source, "roster", "roster"),
        (assignment_program_source, "assignment-program", "assignment_program"),
        (provider_lane_plan_source, "provider-lane-plan", "provider_lane_plan"),
        (tokenizer_source, "tokenizer", "tokenizer"),
        (packet_template_source, "packet-template", "packet_template"),
        (packet_policy_source, "packet-policy", "packet_policy"),
        (pad_unit_set_source, "pad-unit-set", "pad_unit_set"),
        (
            required_document_kinds_source,
            "required-document-kinds",
            "required_document_kinds",
        ),
    )
    copies = [
        _plan_source_copy(
            source,
            run_root=root,
            subtree=subtree,
            role=role,
        )
        for source, subtree, role in fixed_inputs
    ]
    revision_copies = [
        _plan_source_copy(
            revision,
            run_root=root,
            subtree="revisions",
            role="source_revision",
        )
        for revision in source_revision_sources
    ]
    all_copies = copies + revision_copies
    destinations = [copy.destination for copy in all_copies]
    if len(destinations) != len(set(destinations)):
        raise RecordValidationError("source copies have conflicting destinations")
    for destination in destinations:
        if destination.exists():
            raise FileExistsError(destination)

    by_role = {copy.ref.role: copy.ref for copy in copies}
    final_payload: dict[str, object] = {
        "task_registry_ref": _ref_mapping(by_role["task_registry"]),
        "roster_ref": _ref_mapping(by_role["roster"]),
        "assignment_program_ref": _ref_mapping(by_role["assignment_program"]),
        "provider_lane_plan_ref": _ref_mapping(by_role["provider_lane_plan"]),
        "tokenizer_ref": _ref_mapping(by_role["tokenizer"]),
        "packet_template_ref": _ref_mapping(by_role["packet_template"]),
        "packet_policy_ref": _ref_mapping(by_role["packet_policy"]),
        "pad_unit_set_ref": _ref_mapping(by_role["pad_unit_set"]),
        "source_revision_refs": [
            _ref_mapping(copy.ref) for copy in revision_copies
        ],
        "seed_commitment_sha256": template_payload["seed_commitment_sha256"],
        "required_document_kinds_ref": _ref_mapping(
            by_role["required_document_kinds"]
        ),
    }
    final = dict(template)
    final["payload"] = final_payload
    validated = validate_record(final)
    out_target, _relative = _prepare_destination(out, root)

    for copy in all_copies:
        copy.destination.parent.mkdir(parents=True, exist_ok=True)
        write_atomic_bytes(copy.destination, copy.payload)
    return write_record(
        out_target,
        validated,
        run_root=root,
        role="study_manifest",
    )


def verify_digest_link(
    child: Mapping[str, object],
    field: str,
    parent: Mapping[str, object],
) -> None:
    """Verify a naked digest or ArtifactRef field against canonical parent bytes."""

    if field in child:
        link = child[field]
    else:
        payload = child.get("payload")
        if not isinstance(payload, Mapping) or field not in payload:
            raise RecordValidationError(f"missing digest link field {field!r}")
        link = payload[field]
    if isinstance(link, Mapping):
        claimed = link.get("sha256")
    else:
        claimed = link
    expected = canonical_digest(parent)
    if claimed != expected:
        raise RecordValidationError(
            f"{field} digest mismatch: expected {expected}, got {claimed!r}"
        )


@dataclass(frozen=True, slots=True)
class ArtifactEntry:
    relative_path: str
    sha256: str
    byte_count: int
    entry_kind: Literal["scientific_record", "referenced_blob"]
    document_kind: str | None
    role: str
    media_type: str


@dataclass(frozen=True, slots=True)
class _ScientificDocument:
    path: Path
    relative_path: str
    value: dict[str, object]
    sha256: str
    byte_count: int


def _is_operational(relative: Path) -> bool:
    return bool(relative.parts and relative.parts[0] in _OPERATIONAL_TOP_LEVEL)


def _scientific_documents(
    run_root: Path,
    *,
    excluded: Collection[Path],
) -> dict[str, _ScientificDocument]:
    root = _run_root(run_root)
    excluded_resolved = {Path(path).resolve(strict=False) for path in excluded}
    documents: dict[str, _ScientificDocument] = {}
    for path in sorted(root.rglob("*.json")):
        resolved = path.resolve(strict=True)
        if resolved in excluded_resolved:
            continue
        relative = resolved.relative_to(root)
        if _is_operational(relative) or (
            relative.parts and relative.parts[0] == "sources"
        ):
            continue
        payload = resolved.read_bytes()
        try:
            raw = _load_json_bytes(payload, source=resolved)
        except RecordValidationError:
            continue
        if not isinstance(raw, Mapping):
            continue
        kind = raw.get("record_kind")
        if not isinstance(kind, str):
            continue
        if kind == "resampling_artifact_root":
            raise RecordValidationError(
                f"nested or pre-existing artifact root: {relative.as_posix()}"
            )
        if kind not in SCHEMA_BY_KIND:
            if kind.startswith("resampling_"):
                raise RecordValidationError(
                    f"raw file presented as scientific record: {relative.as_posix()}"
                )
            continue
        validated = validate_record(cast(Mapping[str, object], raw))
        relative_path = PurePosixPath(*relative.parts).as_posix()
        documents[relative_path] = _ScientificDocument(
            path=resolved,
            relative_path=relative_path,
            value=validated,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
        )
    return documents


def _walk_artifact_refs(value: object) -> Iterable[ArtifactRef]:
    if isinstance(value, Mapping):
        if frozenset(value) == _SCIENTIFIC_REF_KEYS:
            try:
                yield ArtifactRef(
                    role=cast(str, value["role"]),
                    relative_path=cast(str, value["relative_path"]),
                    sha256=cast(str, value["sha256"]),
                    byte_count=cast(int, value["byte_count"]),
                    media_type=cast(str, value["media_type"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise RecordValidationError(f"malformed ArtifactRef: {exc}") from exc
            return
        for nested in value.values():
            yield from _walk_artifact_refs(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_artifact_refs(nested)


def _read_ref(
    ref: ArtifactRef,
    *,
    run_root: Path,
) -> tuple[Path, bytes]:
    parts = PurePosixPath(ref.relative_path).parts
    if parts and parts[0] in _OPERATIONAL_TOP_LEVEL:
        raise RecordValidationError(
            "operational artifacts cannot enter the scientific closure"
        )
    try:
        path, relative = _resolve_inside(
            Path(ref.relative_path),
            run_root,
            require_exists=True,
        )
    except (FileNotFoundError, RecordValidationError) as exc:
        raise RecordValidationError(
            f"dangling artifact_ref {ref.relative_path!r}"
        ) from exc
    if relative != ref.relative_path or not path.is_file():
        raise RecordValidationError(
            f"artifact_ref is not a canonical file: {ref.relative_path!r}"
        )
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != ref.sha256 or len(payload) != ref.byte_count:
        raise RecordValidationError(
            f"artifact_ref bytes mismatch: {ref.relative_path!r}"
        )
    return path, payload


def _extract_task_ids(value: object) -> set[str] | None:
    if isinstance(value, list):
        task_ids: list[str] = []
        for item in value:
            if isinstance(item, str) and item:
                task_ids.append(item)
            elif isinstance(item, Mapping):
                candidate = item.get("task_id")
                if not isinstance(candidate, str):
                    nested = item.get("task")
                    if isinstance(nested, Mapping):
                        candidate = nested.get("task_id")
                if isinstance(candidate, str) and candidate:
                    task_ids.append(candidate)
                else:
                    return None
            else:
                return None
        if len(task_ids) != len(set(task_ids)):
            raise RecordValidationError("roster contains duplicate task_id values")
        return set(task_ids)
    if isinstance(value, Mapping):
        for key in ("tasks", "task_ids", "roster"):
            if key in value:
                extracted = _extract_task_ids(value[key])
                if extracted is not None:
                    return extracted
        payload = value.get("payload")
        if isinstance(payload, (Mapping, list)):
            return _extract_task_ids(payload)
    return None


def _manifest_roster_task_ids(
    manifest: _ScientificDocument,
    *,
    run_root: Path,
) -> set[str]:
    payload = cast(Mapping[str, object], manifest.value["payload"])
    for key in ("roster_ref", "task_registry_ref"):
        ref_value = payload.get(key)
        if not isinstance(ref_value, Mapping):
            continue
        ref = ArtifactRef(**cast(dict[str, Any], dict(ref_value)))
        path, raw = _read_ref(ref, run_root=run_root)
        try:
            decoded = _load_json_bytes(raw, source=path)
        except RecordValidationError:
            continue
        extracted = _extract_task_ids(decoded)
        if extracted is not None:
            return extracted
    raise RecordValidationError("manifest roster does not expose a task roster")


def _validate_kind_identities(
    documents: Mapping[str, _ScientificDocument],
    *,
    required_document_kinds: set[str],
    run_root: Path,
) -> None:
    by_kind: dict[str, list[_ScientificDocument]] = {}
    for document in documents.values():
        kind = cast(str, document.value["record_kind"])
        by_kind.setdefault(kind, []).append(document)
    observed_kinds = set(by_kind)
    missing = required_document_kinds - observed_kinds
    extra = observed_kinds - required_document_kinds
    if missing:
        raise RecordValidationError(
            f"missing required document kinds: {sorted(missing)}"
        )
    if extra:
        raise RecordValidationError(
            f"extra scientific document kinds: {sorted(extra)}"
        )
    for kind in _SINGLETON_KINDS:
        if kind in by_kind and len(by_kind[kind]) != 1:
            raise RecordValidationError(f"{kind} must be singleton")

    packet_documents = by_kind.get("resampling_packet_index", [])
    if packet_documents:
        stages = [
            cast(Mapping[str, object], document.value["payload"])["stage"]
            for document in packet_documents
        ]
        if Counter(stages) != Counter({"candidate": 1, "sealed": 1}):
            raise RecordValidationError(
                "packet-index identities require one candidate and one sealed"
            )
        candidate = next(
            document
            for document in packet_documents
            if cast(Mapping[str, object], document.value["payload"])["stage"]
            == "candidate"
        )
        sealed = next(
            document
            for document in packet_documents
            if cast(Mapping[str, object], document.value["payload"])["stage"]
            == "sealed"
        )
        candidate_ref = cast(
            Mapping[str, object],
            cast(Mapping[str, object], sealed.value["payload"])["candidate_ref"],
        )
        if (
            candidate_ref.get("relative_path") != candidate.relative_path
            or candidate_ref.get("sha256") != candidate.sha256
        ):
            raise RecordValidationError(
                "sealed packet index does not parent the unique candidate"
            )

    task_documents = by_kind.get("resampling_task_block", [])
    if task_documents:
        task_ids = [
            cast(
                str,
                cast(Mapping[str, object], document.value["payload"])["task_id"],
            )
            for document in task_documents
        ]
        if len(task_ids) != len(set(task_ids)):
            raise RecordValidationError("duplicate task-block task_id identity")
        manifest_documents = by_kind.get("resampling_study_manifest", [])
        if len(manifest_documents) != 1:
            raise RecordValidationError(
                "task-block coverage requires the singleton study manifest"
            )
        roster_task_ids = _manifest_roster_task_ids(
            manifest_documents[0],
            run_root=run_root,
        )
        if set(task_ids) != roster_task_ids:
            raise RecordValidationError(
                "task-block task_id identities do not exactly cover the roster"
            )

    power_documents = by_kind.get("resampling_power_report", [])
    if power_documents:
        _validate_power_identities(power_documents)
    _validate_scientific_ancestry(by_kind)


def _require_ref_matches(
    value: object,
    expected: _ScientificDocument,
    *,
    field: str,
) -> None:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    if (
        value.get("relative_path") != expected.relative_path
        or value.get("sha256") != expected.sha256
        or value.get("byte_count") != expected.byte_count
        or value.get("media_type") != "application/json"
    ):
        raise RecordValidationError(
            f"{field} does not identify the exact {expected.value['record_kind']} parent"
        )


def _singleton_document(
    by_kind: Mapping[str, list[_ScientificDocument]],
    kind: str,
) -> _ScientificDocument | None:
    documents = by_kind.get(kind, [])
    if not documents:
        return None
    if len(documents) != 1:
        raise RecordValidationError(f"{kind} must be singleton")
    return documents[0]


def _validate_scientific_ancestry(
    by_kind: Mapping[str, list[_ScientificDocument]],
) -> None:
    manifest = _singleton_document(by_kind, "resampling_study_manifest")
    schedule = _singleton_document(by_kind, "resampling_prefix_schedule")
    prefix = _singleton_document(by_kind, "resampling_prefix_receipt")
    assignment = _singleton_document(by_kind, "resampling_assignment_ledger")
    projection = _singleton_document(by_kind, "resampling_blinded_projection")
    freeze = _singleton_document(by_kind, "resampling_analysis_freeze")
    analysis = _singleton_document(by_kind, "resampling_analysis")
    unblind = _singleton_document(by_kind, "resampling_unblind_receipt")

    if schedule is not None and manifest is not None:
        _require_ref_matches(
            _power_payload(schedule)["manifest_ref"],
            manifest,
            field="prefix schedule manifest_ref",
        )
    if prefix is not None and schedule is not None:
        _require_ref_matches(
            _power_payload(prefix)["schedule_ref"],
            schedule,
            field="prefix receipt schedule_ref",
        )
    if assignment is not None:
        assignment_payload = _power_payload(assignment)
        if schedule is not None:
            _require_ref_matches(
                assignment_payload["schedule_ref"],
                schedule,
                field="assignment schedule_ref",
            )
        if prefix is not None:
            _require_ref_matches(
                assignment_payload["prefix_index_ref"],
                prefix,
                field="assignment prefix_index_ref",
            )

    packet_documents = by_kind.get("resampling_packet_index", [])
    candidate = next(
        (
            document
            for document in packet_documents
            if _power_payload(document).get("stage") == "candidate"
        ),
        None,
    )
    sealed = next(
        (
            document
            for document in packet_documents
            if _power_payload(document).get("stage") == "sealed"
        ),
        None,
    )
    for packet in packet_documents:
        packet_payload = _power_payload(packet)
        if assignment is not None:
            _require_ref_matches(
                packet_payload["assignment_ref"],
                assignment,
                field="packet assignment_ref",
            )
        if prefix is not None:
            _require_ref_matches(
                packet_payload["prefix_index_ref"],
                prefix,
                field="packet prefix_index_ref",
            )
    if sealed is not None and candidate is not None:
        _require_ref_matches(
            _power_payload(sealed)["candidate_ref"],
            candidate,
            field="sealed packet candidate_ref",
        )
    if freeze is not None and sealed is not None:
        _require_ref_matches(
            _power_payload(freeze)["packet_index_ref"],
            sealed,
            field="analysis freeze packet_index_ref",
        )

    task_documents = by_kind.get("resampling_task_block", [])
    for task in task_documents:
        task_payload = _power_payload(task)
        for field, parent in (
            ("schedule_ref", schedule),
            ("prefix_index_ref", prefix),
            ("assignment_ref", assignment),
            ("packet_index_ref", sealed),
            ("analysis_freeze_ref", freeze),
        ):
            if parent is not None:
                _require_ref_matches(
                    task_payload[field],
                    parent,
                    field=f"task block {field}",
                )

    if projection is not None:
        projection_payload = _power_payload(projection)
        if schedule is not None:
            _require_ref_matches(
                projection_payload["schedule_ref"],
                schedule,
                field="projection schedule_ref",
            )
        if freeze is not None:
            _require_ref_matches(
                projection_payload["analysis_freeze_ref"],
                freeze,
                field="projection analysis_freeze_ref",
            )
        expected_task_paths = {document.relative_path for document in task_documents}
        projected_task_paths = {
            ref.relative_path
            for ref in _walk_artifact_refs(projection_payload["task_block_refs"])
        }
        if expected_task_paths != projected_task_paths:
            raise RecordValidationError(
                "projection task_block_refs do not exactly cover task blocks"
            )

    if unblind is not None:
        unblind_payload = _power_payload(unblind)
        for field, parent in (
            ("projection_ref", projection),
            ("assignment_ledger_ref", assignment),
            ("analysis_freeze_ref", freeze),
        ):
            if parent is not None:
                _require_ref_matches(
                    unblind_payload[field],
                    parent,
                    field=f"unblind {field}",
                )
    if analysis is not None:
        analysis_payload = _power_payload(analysis)
        for field, parent in (
            ("analysis_freeze_ref", freeze),
            ("projection_ref", projection),
            ("unblind_receipt_ref", unblind),
        ):
            if parent is not None:
                _require_ref_matches(
                    analysis_payload[field],
                    parent,
                    field=f"analysis {field}",
                )


def _power_payload(document: _ScientificDocument) -> Mapping[str, object]:
    return cast(Mapping[str, object], document.value["payload"])


def _artifact_paths(value: object) -> set[str]:
    return {ref.relative_path for ref in _walk_artifact_refs(value)}


def _validate_power_identities(
    documents: Sequence[_ScientificDocument],
) -> None:
    by_authority: dict[str, list[_ScientificDocument]] = {}
    for document in documents:
        payload = _power_payload(document)
        authority = cast(str, payload["decision_authority"])
        by_authority.setdefault(authority, []).append(document)
    for authority, authority_documents in by_authority.items():
        nonfinal: list[_ScientificDocument] = []
        finals: list[_ScientificDocument] = []
        identities: set[tuple[object, ...]] = set()
        for document in authority_documents:
            payload = _power_payload(document)
            stage = cast(str, payload["stage"])
            if stage == "final":
                finals.append(document)
                continue
            identity = (
                authority,
                payload["phase"],
                payload["generation"],
                stage,
                payload.get("shard_index") if stage == "shard" else None,
            )
            if identity in identities:
                raise RecordValidationError(
                    f"duplicate power attempt identity: {identity!r}"
                )
            identities.add(identity)
            nonfinal.append(document)
        if len(finals) != 1:
            raise RecordValidationError(
                f"power authority {authority!r} requires exactly one final"
            )
        final_payload = _power_payload(finals[0])
        attempted_paths = {
            document.relative_path for document in nonfinal
        }
        all_attempt_paths = {
            ref.relative_path
            for ref in _walk_artifact_refs(final_payload["all_attempt_refs"])
        }
        if attempted_paths != all_attempt_paths:
            raise RecordValidationError(
                "final all_attempt_refs must parent every immutable power attempt"
            )
        parent_paths = {
            ref.relative_path
            for ref in _walk_artifact_refs(final_payload["parent_refs"])
        }
        if parent_paths != attempted_paths:
            raise RecordValidationError(
                "final parent_refs must parent every immutable power attempt"
            )
        finalization = cast(Mapping[str, object], final_payload["finalization"])
        if finalization["kind"] == "completed_chain":
            phase = finalization["selected_phase"]
            generation = finalization["selected_generation"]
            document_by_path = {
                document.relative_path: document for document in nonfinal
            }

            def selected_document(
                ref_value: object,
                *,
                expected_stage: str,
                field: str,
            ) -> _ScientificDocument:
                refs = tuple(_walk_artifact_refs(ref_value))
                if len(refs) != 1:
                    raise RecordValidationError(
                        f"power finalization {field} must be one ArtifactRef"
                    )
                document = document_by_path.get(refs[0].relative_path)
                if document is None:
                    raise RecordValidationError(
                        f"power finalization {field} is not an attempted report"
                    )
                payload = _power_payload(document)
                if (
                    payload["stage"] != expected_stage
                    or payload["phase"] != phase
                    or payload["generation"] != generation
                ):
                    raise RecordValidationError(
                        f"power finalization {field} has wrong stage, phase, or generation"
                    )
                return document

            selected_document(
                finalization["selected_screen_ref"],
                expected_stage="screen",
                field="selected_screen_ref",
            )
            shard_refs = tuple(
                _walk_artifact_refs(finalization["selected_shard_refs"])
            )
            if not shard_refs:
                raise RecordValidationError("selected power chain lacks a shard")
            for index, shard_ref in enumerate(shard_refs):
                selected_document(
                    _ref_mapping(shard_ref),
                    expected_stage="shard",
                    field=f"selected_shard_refs[{index}]",
                )
            if phase == "gaussian_approximation":
                selection_document = selected_document(
                    finalization["selected_selection_ref"],
                    expected_stage="selection",
                    field="selected_selection_ref",
                )
                validation_document = selected_document(
                    finalization["selected_validation_ref"],
                    expected_stage="validation",
                    field="selected_validation_ref",
                )
                selection_payload = _power_payload(selection_document)
                selected_cells = cast(
                    list[object],
                    selection_payload["selected_cells"],
                )
                if (
                    len(selected_cells) != 5
                    or selection_payload["selection_count"] != 5
                ):
                    raise RecordValidationError(
                        "Gaussian completed chain requires the frozen worst five cells"
                    )
                validation_payload = _power_payload(validation_document)
                if validation_payload["selected_cells"] != selected_cells:
                    raise RecordValidationError(
                        "Gaussian validation cells differ from the frozen selection"
                    )
                interval_cells = {
                    receipt.get("cell_id")
                    for receipt in cast(
                        list[Mapping[str, object]],
                        validation_payload["interval_receipts"],
                    )
                }
                if interval_cells != set(selected_cells):
                    raise RecordValidationError(
                        "Gaussian validation intervals do not cover the worst five"
                    )
            else:
                validation_document = selected_document(
                    finalization["full_grid_validation_ref"],
                    expected_stage="validation",
                    field="full_grid_validation_ref",
                )
                fallback_refs = tuple(
                    _walk_artifact_refs(finalization["fallback_trigger_ref"])
                )
                if len(fallback_refs) != 1:
                    raise RecordValidationError(
                        "fallback_trigger_ref must be one ArtifactRef"
                    )
                fallback = document_by_path.get(fallback_refs[0].relative_path)
                if (
                    fallback is None
                    or _power_payload(fallback)["phase"]
                    != "gaussian_approximation"
                ):
                    raise RecordValidationError(
                        "full-multiplier chain must parent a failed Gaussian trigger"
                    )
                validation_payload = _power_payload(validation_document)
                validation_fallback = cast(
                    Mapping[str, object],
                    validation_payload["fallback_trigger_ref"],
                )
                if (
                    validation_fallback.get("relative_path")
                    != fallback.relative_path
                    or validation_fallback.get("sha256") != fallback.sha256
                ):
                    raise RecordValidationError(
                        "full-grid validation uses a different fallback trigger"
                    )
        else:
            terminal_ref = cast(
                Mapping[str, object],
                finalization["terminal_attempt_ref"],
            )
            terminal_path = cast(str, terminal_ref["relative_path"])
            terminal = next(
                (
                    document
                    for document in nonfinal
                    if document.relative_path == terminal_path
                ),
                None,
            )
            if terminal is None:
                raise RecordValidationError(
                    "feasibility no-go terminal attempt is not in all_attempt_refs"
                )
            terminal_payload = _power_payload(terminal)
            if terminal_payload["stage"] != finalization["terminal_stage"]:
                raise RecordValidationError(
                    "feasibility no-go terminal_stage does not match its attempt"
                )
            phase = terminal_payload["phase"]
            generation = terminal_payload["generation"]
        if (
            final_payload["phase"] != phase
            or final_payload["generation"] != generation
        ):
            raise RecordValidationError(
                "final phase/generation must name its selected or terminal attempt"
            )


def _entry_mapping(entry: ArtifactEntry) -> dict[str, object]:
    return cast(dict[str, object], asdict(entry))


def _artifact_entries(
    run_root: Path,
    required_document_kinds: Collection[str],
    *,
    excluded: Collection[Path],
) -> list[ArtifactEntry]:
    required = list(required_document_kinds)
    if (
        len(required) != len(set(required))
        or "resampling_artifact_root" in required
        or any(kind not in SCHEMA_BY_KIND for kind in required)
    ):
        raise RecordValidationError("required_document_kinds is invalid")
    documents = _scientific_documents(run_root, excluded=excluded)
    _validate_kind_identities(
        documents,
        required_document_kinds=set(required),
        run_root=run_root,
    )
    if not documents:
        raise RecordValidationError("scientific artifact closure is empty")
    manifests = [
        document
        for document in documents.values()
        if document.value["record_kind"] == "resampling_study_manifest"
    ]
    if len(manifests) != 1:
        raise RecordValidationError("artifact closure requires one study manifest")
    manifest_value = manifests[0].value
    for document in documents.values():
        for field in ("study_id", "frozen_created_at", "provenance"):
            if document.value[field] != manifest_value[field]:
                raise RecordValidationError(
                    f"{document.relative_path}: {field} differs from manifest"
                )
    manifest_payload = cast(Mapping[str, object], manifest_value["payload"])
    required_ref = ArtifactRef(
        **cast(
            dict[str, Any],
            dict(cast(Mapping[str, object], manifest_payload["required_document_kinds_ref"])),
        )
    )
    required_path, required_bytes = _read_ref(required_ref, run_root=run_root)
    frozen_required = _required_kind_list(
        _load_json_bytes(required_bytes, source=required_path)
    )
    if frozen_required != sorted(required):
        raise RecordValidationError(
            "required_document_kinds differ from the manifest-bound source"
        )

    refs_by_path: dict[str, ArtifactRef] = {}
    for document in documents.values():
        for ref in _walk_artifact_refs(document.value):
            previous = refs_by_path.get(ref.relative_path)
            if previous is not None and previous != ref:
                raise RecordValidationError(
                    f"conflicting artifact_ref metadata for {ref.relative_path!r}"
                )
            refs_by_path[ref.relative_path] = ref
            _read_ref(ref, run_root=run_root)

    entries_by_path: dict[str, ArtifactEntry] = {}
    for relative_path, document in documents.items():
        incoming = refs_by_path.get(relative_path)
        if incoming is not None:
            if (
                incoming.sha256 != document.sha256
                or incoming.byte_count != document.byte_count
                or incoming.media_type != "application/json"
            ):
                raise RecordValidationError(
                    f"scientific record ref mismatch: {relative_path!r}"
                )
            role = incoming.role
        else:
            role = cast(str, document.value["record_kind"])
        entries_by_path[relative_path] = ArtifactEntry(
            relative_path=relative_path,
            sha256=document.sha256,
            byte_count=document.byte_count,
            entry_kind="scientific_record",
            document_kind=cast(str, document.value["record_kind"]),
            role=role,
            media_type="application/json",
        )

    for relative_path, ref in refs_by_path.items():
        if relative_path in documents:
            continue
        _path, payload = _read_ref(ref, run_root=run_root)
        entries_by_path[relative_path] = ArtifactEntry(
            relative_path=relative_path,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
            entry_kind="referenced_blob",
            document_kind=None,
            role=ref.role,
            media_type=ref.media_type,
        )
    return [entries_by_path[path] for path in sorted(entries_by_path)]


def _normalize_required_kinds(
    required_document_kinds: Collection[str],
) -> list[str]:
    required = list(required_document_kinds)
    if (
        not required
        or len(required) != len(set(required))
        or "resampling_artifact_root" in required
        or any(kind not in SCHEMA_BY_KIND for kind in required)
    ):
        raise RecordValidationError(
            "required_document_kinds must be non-empty, unique upstream kinds"
        )
    return sorted(required)


def _entries_digest(entries: Sequence[ArtifactEntry]) -> str:
    payload = [_entry_mapping(entry) for entry in entries]
    return hashlib.sha256(canonical_json_bytes(payload, indent=None)).hexdigest()


def seal_artifact_root(
    run_root: Path,
    required_document_kinds: Collection[str],
    out: Path,
    *,
    study_id: str,
    frozen_created_at: str,
    provenance: Mapping[str, str],
) -> ArtifactRef:
    """Seal the complete sorted recursive scientific artifact closure."""

    root = _run_root(run_root)
    expected_out = root / _RECEIPT_NAME
    resolved_out, _relative = _resolve_inside(out, root, require_exists=False)
    if resolved_out != expected_out:
        raise RecordValidationError(
            f"artifact-root output must be exactly {expected_out}"
        )
    if expected_out.exists():
        raise FileExistsError(expected_out)
    required = _normalize_required_kinds(required_document_kinds)
    entries = _artifact_entries(
        root,
        required,
        excluded={expected_out},
    )
    provenance_copy = cast(dict[str, object], _plain_json(provenance))
    record: dict[str, object] = {
        "record_kind": "resampling_artifact_root",
        "schema_version": "0.1.0",
        "study_id": study_id,
        "frozen_created_at": frozen_created_at,
        "provenance": provenance_copy,
        "payload": {
            "code_sha256": provenance_copy.get("code_sha256"),
            "design_sha256": provenance_copy.get("design_sha256"),
            "entries": [_entry_mapping(entry) for entry in entries],
            "root_sha256": _entries_digest(entries),
            "required_document_kinds": required,
        },
    }
    return write_record(
        expected_out,
        record,
        run_root=root,
        role="artifact_root",
    )


def verify_artifact_root(
    receipt_path: Path,
    run_root: Path,
    *,
    required_document_kinds: Collection[str],
) -> None:
    """Recompute and verify an immutable artifact-root receipt."""

    root = _run_root(run_root)
    receipt, _relative = _resolve_inside(
        receipt_path,
        root,
        require_exists=True,
    )
    if receipt != root / _RECEIPT_NAME:
        raise RecordValidationError(
            f"artifact-root receipt must be exactly {root / _RECEIPT_NAME}"
        )
    record = load_record(receipt)
    if record["record_kind"] != "resampling_artifact_root":
        raise RecordValidationError("receipt is not a resampling artifact root")
    payload = cast(Mapping[str, object], record["payload"])
    required = _normalize_required_kinds(required_document_kinds)
    if payload["required_document_kinds"] != required:
        raise RecordValidationError("required_document_kinds differ from receipt")
    provenance = cast(Mapping[str, object], record["provenance"])
    if (
        payload["code_sha256"] != provenance["code_sha256"]
        or payload["design_sha256"] != provenance["design_sha256"]
    ):
        raise RecordValidationError("artifact-root provenance is inconsistent")
    actual_entries = _artifact_entries(
        root,
        required,
        excluded={receipt},
    )
    manifest_entries = [
        entry
        for entry in actual_entries
        if entry.document_kind == "resampling_study_manifest"
    ]
    if len(manifest_entries) != 1:
        raise RecordValidationError("artifact root lacks its singleton manifest")
    manifest = load_record(root / Path(manifest_entries[0].relative_path))
    for field in ("study_id", "frozen_created_at", "provenance"):
        if record[field] != manifest[field]:
            raise RecordValidationError(
                f"artifact-root {field} differs from study manifest"
            )
    actual_payload = [_entry_mapping(entry) for entry in actual_entries]
    if payload["entries"] != actual_payload:
        raise RecordValidationError("artifact-root entries do not match current closure")
    if payload["root_sha256"] != _entries_digest(actual_entries):
        raise RecordValidationError("artifact-root digest mismatch")


__all__ = [
    "SCHEMA_BY_KIND",
    "RecordValidationError",
    "ArtifactEntry",
    "canonical_digest",
    "validate_record",
    "load_record",
    "write_record",
    "write_jsonl_artifact",
    "seal_study_manifest",
    "verify_digest_link",
    "seal_artifact_root",
    "verify_artifact_root",
]
