"""Public loading boundary for digest-bound scientific records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import cast

from .artifacts import _read_ref, validate_record
from .authority_refs import (
    decode_artifact_ref,
    load_json_bytes,
)
from .errors import RecordValidationError
from .prefix_contracts import SCIENTIFIC_PARENT_KIND


_SCIENTIFIC_PATH_BY_ROLE: Mapping[str, str] = MappingProxyType({
    "resampling_prefix_schedule": "prefix-schedule.json",
    "study_manifest": "study-manifest.json",
})

if set(_SCIENTIFIC_PATH_BY_ROLE) != set(SCIENTIFIC_PARENT_KIND):
    raise RuntimeError("scientific role/path registry coverage drifted")


@dataclass(frozen=True, slots=True)
class ScientificRecord:
    path: Path
    relative_path: str
    value: dict[str, object]
    sha256: str
    byte_count: int


def load_scientific_parent(
    value: object,
    *,
    run_root: Path,
    field: str,
    expected_kind: str,
    expected_stage: str | None = None,
) -> ScientificRecord:
    """Load and validate one direct scientific parent by exact ArtifactRef."""

    ref = decode_artifact_ref(value, field=field)
    expected_roles = tuple(
        role
        for role, record_kind in SCIENTIFIC_PARENT_KIND.items()
        if record_kind == expected_kind
    )
    if len(expected_roles) != 1:
        raise RecordValidationError(
            f"{field} has no unique registered scientific role for {expected_kind}"
        )
    expected_role = expected_roles[0]
    if ref.role != expected_role:
        raise RecordValidationError(
            f"{field} scientific role must be {expected_role}"
        )
    if ref.media_type != "application/json":
        raise RecordValidationError(
            f"{field} must reference application/json"
        )
    expected_path = _SCIENTIFIC_PATH_BY_ROLE[expected_role]
    if ref.relative_path != expected_path:
        raise RecordValidationError(
            f"{field} scientific path must be {expected_path}"
        )
    root = Path(run_root).resolve(strict=True)
    path, raw = _read_ref(ref, run_root=root)
    decoded = load_json_bytes(raw, source=path)
    if not isinstance(decoded, Mapping):
        raise RecordValidationError(
            f"{field} must reference a JSON object"
        )
    validated = validate_record(cast(Mapping[str, object], decoded))
    if validated["record_kind"] != expected_kind:
        raise RecordValidationError(
            f"{field} must reference {expected_kind}, "
            f"got {validated['record_kind']}"
        )
    payload = cast(Mapping[str, object], validated["payload"])
    if expected_stage is not None and payload.get("stage") != expected_stage:
        raise RecordValidationError(
            f"{field} must reference {expected_kind} "
            f"stage {expected_stage!r}"
        )
    return ScientificRecord(
        path=path,
        relative_path=ref.relative_path,
        value=validated,
        sha256=ref.sha256,
        byte_count=ref.byte_count,
    )


__all__ = ("ScientificRecord", "load_scientific_parent")
