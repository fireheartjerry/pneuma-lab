"""Task-8-only timing lower-bound no-go contract."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null import timing_no_go
from pneuma_lab.resampling_null.timing_no_go import (
    TimingNoGoBindings,
    create_timing_no_go,
    verify_timing_no_go,
)
from pneuma_lab.resampling_null.types import ArtifactRef
from pneuma_lab.schemas import load_schema


def _write_json(root: Path, relative_path: str, value: object) -> bytes:
    payload = canonical_json_bytes(value, indent=None)
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return payload


def _ref(
    root: Path,
    relative_path: str,
    value: object,
    *,
    role: str,
    media_type: str = "application/json",
) -> ArtifactRef:
    payload = _write_json(root, relative_path, value)
    return ArtifactRef(
        role=role,
        relative_path=relative_path,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type=media_type,
    )


def _mapping(ref: ArtifactRef) -> dict[str, object]:
    return {
        "role": ref.role,
        "relative_path": ref.relative_path,
        "sha256": ref.sha256,
        "byte_count": ref.byte_count,
        "media_type": ref.media_type,
    }


def _fixture(
    tmp_path: Path,
    *,
    elapsed_lower_bound_seconds: int = 7200,
    host_identity_sha256: str | None = None,
    p0_values: list[float] | None = None,
):
    host_identity = (
        timing_no_go._current_host_identity_sha256()
        if host_identity_sha256 is None
        else host_identity_sha256
    )
    topology_ref = _ref(
        tmp_path,
        "sources/power-screen-topology/topology.json",
        {
            "contract_id": "p0-power-screen-topology-v1",
            "schema_version": "1",
            "shard_partitioning": "contiguous-frozen-cell-range-v1",
        },
        role="power_screen_topology",
    )
    grid_ref = _ref(
        tmp_path,
        "sources/power-grid/grid.json",
        {
            "schema_version": "1",
            "screen_datasets_per_cell": 200,
            "datasets_per_cell": 20000,
            "max_projected_wall_seconds": 43200,
            "p0_values": [0.1, 0.4, 0.7] if p0_values is None else p0_values,
            "trigger_rates": [0.6, 0.75, 0.9],
            "latent_rhos": [0.0, 0.4, 0.8],
        },
        role="power_grid",
    )
    manifest_ref = _ref(
        tmp_path,
        "study-manifest.json",
        {
            "schema_version": "0.1.0",
            "record_kind": "resampling_study_manifest",
            "payload": {
                "power_grid_ref": _mapping(grid_ref),
                "power_screen_topology_ref": _mapping(topology_ref),
            },
        },
        role="study_manifest",
    )
    authority_ref = _ref(
        tmp_path,
        "power/power-authority.json",
        {
            "schema_version": "1",
            "authority_kind": "synthetic_validation",
            "manifest_ref": _mapping(manifest_ref),
        },
        role="power_authority",
        media_type="application/vnd.pneuma.power-authority+json",
    )
    run_identity = timing_no_go._run_root_identity(tmp_path.resolve())
    started_ns = 1_000_000_000
    observed_ns = started_ns + elapsed_lower_bound_seconds * 1_000_000_000
    evidence_ref = _ref(
        tmp_path,
        "timing-evidence/task10-authorized-termination.json",
        {
            "contract_id": "task10-p0-timing-termination-evidence-v1",
            "execution_owner": "task_10_canonical_timing_rerun",
            "machinery_owner": "task_8_timing_admission",
            "run_root_identity_sha256": run_identity,
            "host_identity_sha256": host_identity,
            "clock": {
                "source": "time.monotonic_ns",
                "started_monotonic_ns": started_ns,
                "observed_monotonic_ns": observed_ns,
                "elapsed_lower_bound_seconds": elapsed_lower_bound_seconds,
                "semantics": "conservative_lower_bound",
            },
            "termination": {
                "authorization": "user_explicit",
                "event_id": "EJ-20260730-0217",
                "signal": "SIGTERM",
                "exit_status": "clean",
                "probe_status": "terminated_incomplete",
            },
        },
        role="timing_termination_evidence",
    )
    bindings = TimingNoGoBindings(
        study_manifest_ref=manifest_ref,
        power_authority_ref=authority_ref,
        power_grid_ref=grid_ref,
        power_screen_topology_ref=topology_ref,
        termination_evidence_ref=evidence_ref,
        run_root_identity_sha256=run_identity,
        host_identity_sha256=host_identity,
    )
    return bindings


def test_schema_is_closed_and_not_a_power_report() -> None:
    schema = load_schema("resampling-timing-no-go.schema.json")
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["record_kind"]["const"] == "resampling_timing_no_go"
    payload = schema["properties"]["payload"]
    assert payload["properties"]["outcome"]["const"] == "timing_infeasible_lower_bound"
    assert "stage" not in payload["properties"]
    assert "parent_refs" not in payload["properties"]
    for subschema in payload["properties"]["claims"]["properties"].values():
        assert subschema == {"const": False}


def test_create_and_verify_host_specific_lower_bound(tmp_path: Path) -> None:
    path = create_timing_no_go(_fixture(tmp_path), run_root=tmp_path)
    record = verify_timing_no_go(path, run_root=tmp_path)

    assert path.relative_to(tmp_path).as_posix() == (
        "timing-admission/task8-timing-no-go.json"
    )
    assert record["record_kind"] == "resampling_timing_no_go"
    payload = record["payload"]
    assert payload["outcome"] == "timing_infeasible_lower_bound"
    assert payload["projection"] == {
        "formula": "ceil(elapsed_lower_bound_seconds * production_datasets_per_cell / screen_datasets_per_cell)",
        "cell_count": 2916,
        "shard_count": 64,
        "screen_datasets_per_cell": 200,
        "production_datasets_per_cell": 20000,
        "multiplier": 100,
        "max_projected_wall_seconds": 43200,
        "admissible_probe_threshold_seconds": 432,
        "elapsed_lower_bound_seconds": 7200,
        "projected_wall_seconds_lower_bound": 720000,
    }
    assert set(payload["claims"].values()) == {False}
    assert payload["execution_provenance"] == {
        "execution_owner": "task_10_canonical_timing_rerun",
        "machinery_owner": "task_8_timing_admission",
        "promotes_task_10_completion": False,
        "promotes_task_8_scientific_completion": False,
    }


def test_threshold_equality_is_not_a_no_go(tmp_path: Path) -> None:
    with pytest.raises(RecordValidationError, match="strictly exceed"):
        create_timing_no_go(
            _fixture(tmp_path, elapsed_lower_bound_seconds=432),
            run_root=tmp_path,
        )


def test_creation_is_exclusive(tmp_path: Path) -> None:
    bindings = _fixture(tmp_path)
    create_timing_no_go(bindings, run_root=tmp_path)
    with pytest.raises(FileExistsError):
        create_timing_no_go(bindings, run_root=tmp_path)


@pytest.mark.parametrize(
    "relative_path,value",
    [
        (
            "power/screen.json",
            {"record_kind": "resampling_power_report", "payload": {"stage": "screen"}},
        ),
        (
            "power-timing-verifications/receipt.json",
            {"contract_id": "p0-production-timing-verification-v1"},
        ),
        (
            "power/shard-0.json",
            {"record_kind": "resampling_power_report", "payload": {"stage": "shard"}},
        ),
        (
            "power/final.json",
            {"record_kind": "resampling_power_report", "payload": {"stage": "final"}},
        ),
        (
            "prefix-schedule.json",
            {"record_kind": "resampling_prefix_schedule"},
        ),
    ],
)
def test_verification_rejects_a_later_forbidden_descendant(
    tmp_path: Path, relative_path: str, value: object
) -> None:
    path = create_timing_no_go(_fixture(tmp_path), run_root=tmp_path)
    _write_json(tmp_path, relative_path, value)
    with pytest.raises(RecordValidationError, match="forbidden descendant"):
        verify_timing_no_go(path, run_root=tmp_path)


def test_verification_rejects_noncanonical_or_promoted_record(tmp_path: Path) -> None:
    path = create_timing_no_go(_fixture(tmp_path), run_root=tmp_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["payload"]["claims"]["scientific_result"] = True
    path.write_text(json.dumps(record, indent=2))
    with pytest.raises(RecordValidationError, match="canonical|claim"):
        verify_timing_no_go(path, run_root=tmp_path)


def test_creation_rejects_missing_or_drifting_binding(tmp_path: Path) -> None:
    bindings = _fixture(tmp_path)
    drifted = replace(
        bindings,
        power_grid_ref=replace(bindings.power_grid_ref, sha256="0" * 64),
    )
    with pytest.raises(RecordValidationError, match="digest|binding"):
        create_timing_no_go(drifted, run_root=tmp_path)


def test_creation_rejects_power_authority_media_type_drift(tmp_path: Path) -> None:
    bindings = _fixture(tmp_path)
    with pytest.raises(RecordValidationError, match="media type"):
        replace(
            bindings,
            power_authority_ref=replace(
                bindings.power_authority_ref, media_type="application/json"
            ),
        )


def test_verification_rejects_malformed_file_at_forbidden_path(
    tmp_path: Path,
) -> None:
    path = create_timing_no_go(_fixture(tmp_path), run_root=tmp_path)
    (tmp_path / "power/screen.json").write_bytes(b"not-json\n")
    with pytest.raises(RecordValidationError, match="forbidden descendant"):
        verify_timing_no_go(path, run_root=tmp_path)


def test_creation_rejects_parent_symlink_escape(tmp_path: Path) -> None:
    bindings = _fixture(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (tmp_path / "timing-admission").symlink_to(outside, target_is_directory=True)
    with pytest.raises(
        RecordValidationError, match="canonical directory|safely|forbidden descendant"
    ):
        create_timing_no_go(bindings, run_root=tmp_path)
    assert not (outside / "task8-timing-no-go.json").exists()


def test_projection_uses_unbounded_exact_integer_arithmetic(tmp_path: Path) -> None:
    elapsed = 10**400
    path = create_timing_no_go(
        _fixture(tmp_path, elapsed_lower_bound_seconds=elapsed),
        run_root=tmp_path,
    )
    record = verify_timing_no_go(path, run_root=tmp_path)
    assert record["payload"]["projection"]["projected_wall_seconds_lower_bound"] == (
        elapsed * 100
    )


def test_creation_derives_2916_cells_from_the_frozen_grid(tmp_path: Path) -> None:
    with pytest.raises(RecordValidationError, match="2916|grid"):
        create_timing_no_go(
            _fixture(tmp_path, p0_values=[0.1, 0.4]),
            run_root=tmp_path,
        )


def test_creation_rejects_consistently_relabelled_host(tmp_path: Path) -> None:
    actual = timing_no_go._current_host_identity_sha256()
    relabelled = "0" * 64 if actual != "0" * 64 else "1" * 64
    with pytest.raises(RecordValidationError, match="current host"):
        create_timing_no_go(
            _fixture(tmp_path, host_identity_sha256=relabelled),
            run_root=tmp_path,
        )


def test_run_identity_binds_filesystem_object_not_only_path(tmp_path: Path) -> None:
    bindings = _fixture(tmp_path)
    path_only = hashlib.sha256(str(tmp_path.resolve()).encode("utf-8")).hexdigest()
    assert bindings.run_root_identity_sha256 != path_only


def test_verification_rejects_non_json_descendant_namespace(tmp_path: Path) -> None:
    path = create_timing_no_go(_fixture(tmp_path), run_root=tmp_path)
    target = tmp_path / "analysis/result.bin"
    target.parent.mkdir()
    target.write_bytes(b"descendant")
    with pytest.raises(RecordValidationError, match="forbidden descendant"):
        verify_timing_no_go(path, run_root=tmp_path)
