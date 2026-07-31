"""Immutable pre-outcome analysis inputs for the resampling study."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path

from pneuma_lab.foundation.artifacts import write_atomic_bytes

from .artifacts import _load_direct_scientific_parent, _read_ref, _resolve_inside, write_record
from .errors import RecordValidationError
from .types import ArtifactRef


@dataclass(frozen=True, slots=True)
class CurrentAnalysisInputs:
    """Caller-owned bytes which must still equal the analysis freeze."""

    source_paths: Mapping[str, Path]
    config_path: Path
    projection_schema_path: Path
    packet_index_ref: ArtifactRef


def snapshot_sources(
    run_root: Path,
    sources: Mapping[str, Path],
    *,
    relative_paths: Mapping[str, str] | None = None,
) -> dict[str, ArtifactRef]:
    """Copy exact external bytes into the immutable generic source namespace."""

    root = Path(run_root).resolve(strict=True)
    if not root.is_dir() or not sources:
        raise ValueError("run root and sources must be non-empty")
    result: dict[str, ArtifactRef] = {}
    observed_sources: set[Path] = set()
    observed_outputs: set[str] = set()
    for name, source in sources.items():
        if type(name) is not str or not name or not isinstance(source, Path):
            raise ValueError("source names and paths must be valid")
        resolved = source.resolve(strict=True)
        if not resolved.is_file():
            raise ValueError("source must identify a regular file")
        if resolved in observed_sources:
            raise ValueError("duplicate source is not permitted")
        try:
            resolved.relative_to(root)
        except ValueError:
            pass
        else:
            raise ValueError("source must remain outside the run root")
        payload = resolved.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        relative = (
            relative_paths[name]
            if relative_paths is not None and name in relative_paths
            else f"sources/analysis-freeze/{digest}-{resolved.name}"
        )
        target, normalized = _resolve_inside(Path(relative), root, require_exists=False)
        if not normalized.startswith("sources/analysis-freeze/"):
            raise ValueError("snapshot must remain inside the generic source path")
        if normalized in observed_outputs:
            raise ValueError("duplicate snapshot destination is not permitted")
        if target.exists():
            if target.read_bytes() != payload:
                raise FileExistsError(target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            write_atomic_bytes(target, payload)
        observed_sources.add(resolved)
        observed_outputs.add(normalized)
        result[name] = ArtifactRef(
            role="analysis_source",
            relative_path=normalized,
            sha256=digest,
            byte_count=len(payload),
            media_type="application/octet-stream",
        )
    return result


def freeze_analysis(
    *,
    run_root: Path,
    destination: Path,
    study_id: str,
    frozen_created_at: str,
    provenance: Mapping[str, str],
    source_paths: Mapping[str, Path],
    config_path: Path,
    projection_schema_path: Path,
    packet_index_ref: ArtifactRef,
) -> ArtifactRef:
    """Seal source bytes and bind them to one already-sealed packet index."""

    if type(packet_index_ref) is not ArtifactRef:
        raise TypeError("packet index reference must be exact")
    packet_index = _load_direct_scientific_parent(
        {
            "role": packet_index_ref.role,
            "relative_path": packet_index_ref.relative_path,
            "sha256": packet_index_ref.sha256,
            "byte_count": packet_index_ref.byte_count,
            "media_type": packet_index_ref.media_type,
        },
        run_root=run_root,
        field="packet_index_ref",
        expected_kind="resampling_packet_index",
        expected_stage="sealed",
    )
    if packet_index.value["study_id"] != study_id:
        raise RecordValidationError("sealed packet index has another study")
    all_sources = dict(source_paths)
    if {"config", "projection_schema"} & set(all_sources):
        raise ValueError("source names collide with reserved freeze inputs")
    all_sources["config"] = config_path
    all_sources["projection_schema"] = projection_schema_path
    snapshots = snapshot_sources(run_root, all_sources)
    record = {
        "record_kind": "resampling_analysis_freeze",
        "schema_version": "0.2.0",
        "study_id": study_id,
        "frozen_created_at": frozen_created_at,
        "provenance": dict(provenance),
        "payload": {
            "source_refs": [
                {
                    "name": name,
                    "ref": {
                        "role": ref.role,
                        "relative_path": ref.relative_path,
                        "sha256": ref.sha256,
                        "byte_count": ref.byte_count,
                        "media_type": ref.media_type,
                    },
                }
                for name, ref in sorted(snapshots.items())
                if name not in {"config", "projection_schema"}
            ],
            "config_ref": {"role": snapshots["config"].role, "relative_path": snapshots["config"].relative_path, "sha256": snapshots["config"].sha256, "byte_count": snapshots["config"].byte_count, "media_type": snapshots["config"].media_type},
            "projection_schema_ref": {"role": snapshots["projection_schema"].role, "relative_path": snapshots["projection_schema"].relative_path, "sha256": snapshots["projection_schema"].sha256, "byte_count": snapshots["projection_schema"].byte_count, "media_type": snapshots["projection_schema"].media_type},
            "packet_index_ref": {"role": packet_index_ref.role, "relative_path": packet_index_ref.relative_path, "sha256": packet_index_ref.sha256, "byte_count": packet_index_ref.byte_count, "media_type": packet_index_ref.media_type},
        },
    }
    return write_record(destination, record, run_root=run_root, role="analysis_freeze")


def verify_analysis_freeze(
    freeze_ref: ArtifactRef, *, run_root: Path, source_paths: Mapping[str, Path],
    config_path: Path, projection_schema_path: Path, packet_index_ref: ArtifactRef,
) -> None:
    """Fail closed when any copied input or sealed packet parent has drifted."""
    freeze = _load_direct_scientific_parent(
        {"role": freeze_ref.role, "relative_path": freeze_ref.relative_path, "sha256": freeze_ref.sha256, "byte_count": freeze_ref.byte_count, "media_type": freeze_ref.media_type},
        run_root=run_root, field="freeze_ref", expected_kind="resampling_analysis_freeze",
    )
    payload = freeze.value["payload"]
    assert isinstance(payload, Mapping)
    if payload.get("packet_index_ref") != {"role": packet_index_ref.role, "relative_path": packet_index_ref.relative_path, "sha256": packet_index_ref.sha256, "byte_count": packet_index_ref.byte_count, "media_type": packet_index_ref.media_type}:
        raise RecordValidationError("analysis freeze packet index differs")
    _load_direct_scientific_parent(payload["packet_index_ref"], run_root=run_root, field="packet_index_ref", expected_kind="resampling_packet_index", expected_stage="sealed")
    inputs = dict(source_paths)
    if {"config", "projection_schema"} & set(inputs):
        raise ValueError("source names collide with reserved freeze inputs")
    bindings = payload["source_refs"]
    if not isinstance(bindings, list):
        raise RecordValidationError("analysis freeze named input bindings are malformed")
    frozen_by_name: dict[str, Mapping[str, object]] = {}
    for binding in bindings:
        if (
            not isinstance(binding, Mapping)
            or type(binding.get("name")) is not str
            or not isinstance(binding.get("ref"), Mapping)
            or binding["name"] in frozen_by_name
        ):
            raise RecordValidationError("analysis freeze named input bindings are malformed")
        frozen_by_name[binding["name"]] = binding["ref"]
    if set(frozen_by_name) != set(inputs):
        raise RecordValidationError("analysis freeze named input set differs")
    for name, path in inputs.items():
        ref = frozen_by_name[name]
        _, frozen_bytes = _read_ref(ArtifactRef(**dict(ref)), run_root=run_root)
        if Path(path).read_bytes() != frozen_bytes:
            raise RecordValidationError(
                f"analysis freeze named input {name!r} differs"
            )
    for label, path, ref in (
        ("config", config_path, payload["config_ref"]),
        ("projection schema", projection_schema_path, payload["projection_schema_ref"]),
    ):
        if not isinstance(ref, Mapping):
            raise RecordValidationError(f"analysis freeze {label} ref is malformed")
        _, frozen_bytes = _read_ref(ArtifactRef(**dict(ref)), run_root=run_root)
        if Path(path).read_bytes() != frozen_bytes:
            raise RecordValidationError(f"analysis freeze {label} differs")


def verify_current_analysis_inputs(
    freeze_ref: ArtifactRef, *, run_root: Path, inputs: CurrentAnalysisInputs,
) -> None:
    """Require the exact caller-current inputs, not merely stored snapshots."""
    if type(inputs) is not CurrentAnalysisInputs:
        raise TypeError("unblind requires exact CurrentAnalysisInputs")
    verify_analysis_freeze(
        freeze_ref,
        run_root=run_root,
        source_paths=inputs.source_paths,
        config_path=inputs.config_path,
        projection_schema_path=inputs.projection_schema_path,
        packet_index_ref=inputs.packet_index_ref,
    )


def verify_frozen_analysis_inputs(freeze_ref: ArtifactRef, *, run_root: Path) -> None:
    """Verify every immutable CurrentAnalysisInputs snapshot before unblinding."""
    freeze = _load_direct_scientific_parent(
        {"role": freeze_ref.role, "relative_path": freeze_ref.relative_path, "sha256": freeze_ref.sha256, "byte_count": freeze_ref.byte_count, "media_type": freeze_ref.media_type},
        run_root=run_root, field="freeze_ref", expected_kind="resampling_analysis_freeze",
    )
    payload = freeze.value["payload"]
    assert isinstance(payload, Mapping)
    bindings = payload["source_refs"]
    if not isinstance(bindings, list):
        raise RecordValidationError("analysis freeze named input bindings are malformed")
    refs: list[object] = []
    for binding in bindings:
        if not isinstance(binding, Mapping) or not isinstance(binding.get("ref"), Mapping):
            raise RecordValidationError("analysis freeze named input bindings are malformed")
        refs.append(binding["ref"])
    refs.extend([payload["config_ref"], payload["projection_schema_ref"]])
    for index, value in enumerate(refs):
        if not isinstance(value, Mapping):
            raise RecordValidationError("frozen analysis input ref is malformed")
        ref = ArtifactRef(**dict(value))
        if not ref.relative_path.startswith("sources/analysis-freeze/"):
            raise RecordValidationError("CurrentAnalysisInputs must remain in immutable source namespace")
        _read_ref(ref, run_root=run_root)
