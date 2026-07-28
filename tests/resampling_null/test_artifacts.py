"""Contract tests for resampling-null schemas and canonical artifact IO."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab import schemas as pls
from pneuma_lab.resampling_null.artifacts import (
    SCHEMA_BY_KIND,
    RecordValidationError,
    canonical_digest,
    load_record,
    seal_artifact_root,
    seal_study_manifest,
    validate_record,
    verify_artifact_root,
    verify_digest_link,
    write_jsonl_artifact,
    write_record,
)


KINDS = (
    "resampling_study_manifest",
    "resampling_prefix_schedule",
    "resampling_prefix_receipt",
    "resampling_assignment_ledger",
    "resampling_packet_index",
    "resampling_task_block",
    "resampling_blinded_projection",
    "resampling_analysis_freeze",
    "resampling_analysis",
    "resampling_power_report",
    "resampling_unblind_receipt",
    "resampling_artifact_root",
)
SHA_A = "a" * 64
SHA_B = "b" * 64
FROZEN = "2026-07-28T12:00:00Z"


def _ref(
    path: str,
    *,
    role: str = "source",
    sha256: str = SHA_A,
    byte_count: int = 1,
    media_type: str = "application/json",
) -> dict[str, object]:
    return {
        "role": role,
        "relative_path": path,
        "sha256": sha256,
        "byte_count": byte_count,
        "media_type": media_type,
    }


def _record(kind: str, payload: dict[str, object]) -> dict[str, object]:
    return {
        "record_kind": kind,
        "schema_version": "0.1.0",
        "study_id": "study-1",
        "frozen_created_at": FROZEN,
        "provenance": {
            "design_sha256": SHA_A,
            "code_sha256": SHA_B,
        },
        "payload": payload,
    }


def _minimal_payload(kind: str) -> dict[str, object]:
    refs = {
        name: _ref(f"parents/{name}.json", role=name)
        for name in (
            "manifest_ref",
            "schedule_ref",
            "prefix_index_ref",
            "assignment_ref",
            "candidate_ref",
            "tokenizer_ref",
            "packet_template_ref",
            "packet_policy_ref",
            "pad_unit_set_ref",
            "analysis_freeze_ref",
            "projection_ref",
            "unblind_receipt_ref",
            "config_ref",
            "projection_schema_ref",
            "packet_index_ref",
            "assignment_ledger_ref",
            "roster_ref",
            "grid_ref",
        )
    }
    payloads: dict[str, dict[str, object]] = {
        "resampling_study_manifest": {
            "task_registry_ref": _ref("sources/tasks.json"),
            "roster_ref": _ref("sources/roster.json"),
            "assignment_program_ref": _ref("sources/assignment.py"),
            "provider_lane_plan_ref": _ref("sources/provider.json"),
            "tokenizer_ref": _ref("sources/tokenizer.json"),
            "packet_template_ref": _ref("sources/template.json"),
            "packet_policy_ref": _ref("sources/policy.json"),
            "pad_unit_set_ref": _ref("sources/pads.json"),
            "source_revision_refs": [_ref("sources/revisions/design.md")],
            "seed_commitment_sha256": SHA_A,
            "required_document_kinds_ref": _ref("sources/required.json"),
        },
        "resampling_prefix_schedule": {
            "manifest_ref": refs["manifest_ref"],
            "assignment_program_ref": refs["assignment_ref"],
            "provider_lane_plan_ref": _ref("parents/provider.json"),
            "study_seed": 7,
            "tasks": [
                {
                    "task": {
                        "task_id": "task-1",
                        "benchmark": "swe",
                        "stratum": "python",
                        "lineage": "repo-1",
                        "sensitivity_groups": [
                            {"kind": "language", "value": "python"}
                        ],
                    },
                    "prefix_seed": 11,
                    "slots": [
                        {
                            "slot_id": f"slot-{index}",
                            "seed": 20 + index,
                            "execution_order": index,
                            "hardware_lane": index,
                        }
                        for index in range(4)
                    ],
                    "provider_lane": "lane-a",
                }
            ],
        },
        "resampling_prefix_receipt": {
            "schedule_ref": refs["schedule_ref"],
            "task_receipts": [],
        },
        "resampling_assignment_ledger": {
            "schedule_ref": refs["schedule_ref"],
            "prefix_index_ref": refs["prefix_index_ref"],
            "assignment_mode": "uniform_12",
            "assignments": [],
            "allocation_receipts": [],
        },
        "resampling_packet_index": {
            "stage": "candidate",
            "assignment_ref": refs["assignment_ref"],
            "prefix_index_ref": refs["prefix_index_ref"],
            "tokenizer_ref": refs["tokenizer_ref"],
            "packet_template_ref": refs["packet_template_ref"],
            "packet_policy_ref": refs["packet_policy_ref"],
            "pad_unit_set_ref": refs["pad_unit_set_ref"],
            "entries": [],
        },
        "resampling_task_block": _no_trigger_task_block_payload(refs),
        "resampling_blinded_projection": {
            "schedule_ref": refs["schedule_ref"],
            "analysis_freeze_ref": refs["analysis_freeze_ref"],
            "task_block_refs": [],
            "rows": [],
            "expected_task_count": 0,
            "complete": True,
        },
        "resampling_analysis_freeze": {
            "source_refs": [_ref("sources/data.json")],
            "config_ref": refs["config_ref"],
            "projection_schema_ref": refs["projection_schema_ref"],
            "packet_index_ref": refs["packet_index_ref"],
        },
        "resampling_analysis": {
            "analysis_freeze_ref": refs["analysis_freeze_ref"],
            "projection_ref": refs["projection_ref"],
            "unblind_receipt_ref": refs["unblind_receipt_ref"],
            "config_ref": refs["config_ref"],
            "row_count": 0,
            "result": _analysis_result(),
            "numeric_receipt": {"finite": True},
        },
        "resampling_power_report": {
            "stage": "screen",
            "decision_authority": "synthetic_validation",
            "phase": "gaussian_approximation",
            "generation": 0,
            "roster_ref": refs["roster_ref"],
            "grid_ref": refs["grid_ref"],
            "parent_refs": [],
            "topology_ref": _ref("parents/topology.json"),
            "config_ref": refs["config_ref"],
            "numeric_fixture_ref": _ref("parents/numeric-fixture.json"),
            "numeric_contract": _numeric_contract(),
            "projected_wall_seconds": 1,
            "cell_count": 1,
            "dataset_count": 200,
        },
        "resampling_unblind_receipt": {
            "projection_ref": refs["projection_ref"],
            "assignment_ledger_ref": refs["assignment_ledger_ref"],
            "analysis_freeze_ref": refs["analysis_freeze_ref"],
            "expected_task_count": 0,
            "permit_hmac_sha256": SHA_A,
        },
        "resampling_artifact_root": {
            "code_sha256": SHA_B,
            "design_sha256": SHA_A,
            "entries": [],
            "root_sha256": SHA_A,
            "required_document_kinds": [],
        },
    }
    return payloads[kind]


def _outcome(slot: int) -> dict[str, object]:
    return {
        "task_id": "task-1",
        "benchmark": "swe",
        "opaque_arm_id": f"opaque-{slot}",
        "success": 0,
        "prefix_success": 0,
        "partial_reward": 0.0,
        "infrastructure_failure": False,
        "counters": {
            "generated_tokens": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "artifact_ref": _ref(f"grades/slot-{slot}.json", role="grade"),
    }


def _no_trigger_task_block_payload(
    refs: dict[str, dict[str, object]],
) -> dict[str, object]:
    outcomes = [_outcome(index) for index in range(4)]
    for outcome in outcomes:
        outcome["artifact_ref"] = _ref("grades/y0.json", role="grade")
    return {
        "task_id": "task-1",
        "benchmark": "swe",
        "stratum": "python",
        "sensitivity_groups": [{"kind": "language", "value": "python"}],
        "triggered": False,
        "prefix_success": 0,
        "slot_outcomes": outcomes,
        "schedule_ref": refs["schedule_ref"],
        "prefix_index_ref": refs["prefix_index_ref"],
        "assignment_ref": refs["assignment_ref"],
        "packet_index_ref": refs["packet_index_ref"],
        "analysis_freeze_ref": refs["analysis_freeze_ref"],
        "attempts": None,
        "selected_attempt_index": None,
        "terminal_slot_receipts": None,
        "execution_receipts": None,
        "outage_receipt": None,
        "validity_event_refs": [],
        "pipeline_valid": True,
        "validity_codes": [],
    }


def _analysis_result() -> dict[str, object]:
    randomization = {
        "statistic": 0.0,
        "p_value": 1.0,
        "mode": "enumerated_exact",
        "support_size": 1,
        "draws": None,
        "monte_carlo_se": None,
    }
    contrast = {
        "estimate": 0.0,
        "standard_error": 0.0,
        "simultaneous_lower": 0.0,
        "simultaneous_upper": 0.0,
        "randomization": randomization,
    }
    bounds = {
        "family_name": "co_primary",
        "contrast_names": ["content", "excess"],
        "estimates": [0.0, 0.0],
        "standard_errors": [0.0, 0.0],
        "lowers": [0.0, 0.0],
        "uppers": [0.0, 0.0],
        "critical_value": 1.0,
        "method": "task_cluster_rademacher_max_t",
        "draws": 1,
        "seed": 1,
        "quantile_order_1_based": 1,
    }
    secondary_bounds = deepcopy(bounds)
    secondary_bounds["family_name"] = "secondary_three"
    secondary_bounds["contrast_names"] = ["sham_packet", "continuation", "total"]
    for name in ("estimates", "standard_errors", "lowers", "uppers"):
        secondary_bounds[name] = [0.0, 0.0, 0.0]
    return {
        "content": contrast,
        "excess": contrast,
        "sham_packet": contrast,
        "continuation": 0.0,
        "total": 0.0,
        "null": 0.0,
        "omnibus_sharp": randomization,
        "primary_bounds": bounds,
        "secondary_family": {
            "contrast_names": ["sham_packet", "continuation", "total"],
            "raw_one_sided_p": [1.0, 1.0, 1.0],
            "holm_adjusted_p": [1.0, 1.0, 1.0],
            "bounds": secondary_bounds,
        },
        "resolution": {
            "q0": 0.0,
            "r95": 0.0,
            "discordant_task_count": 0,
            "mode": "equal_roster_exact_binomial",
        },
        "differential_failure_gap": 0.0,
        "benchmark_estimates": [],
        "leave_one_out": [],
        "gates": [],
        "verdict": "UNRESOLVED_RESAMPLING",
        "reasons": ["empty fixture"],
    }


def _write_blob(root: Path, relative_path: str, value: bytes) -> dict[str, object]:
    path = root / Path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return _ref(
        relative_path,
        sha256=hashlib.sha256(value).hexdigest(),
        byte_count=len(value),
        media_type="application/octet-stream",
    )


def _artifact_mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], asdict(value))


def _replace_artifact_refs(value: object, replacement: dict[str, object]) -> None:
    if isinstance(value, dict):
        if set(value) == {
            "role",
            "relative_path",
            "sha256",
            "byte_count",
            "media_type",
        }:
            copied = deepcopy(replacement)
            value.clear()
            value.update(copied)
            return
        for nested in value.values():
            _replace_artifact_refs(nested, replacement)
    elif isinstance(value, list):
        for nested in value:
            _replace_artifact_refs(nested, replacement)


def test_registry_and_schema_metadata_are_closed() -> None:
    assert tuple(SCHEMA_BY_KIND) == KINDS
    assert tuple(pls.RESAMPLING_SCHEMA_FILES) == tuple(SCHEMA_BY_KIND.values())
    for kind, filename in SCHEMA_BY_KIND.items():
        schema = pls.load_schema(filename)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["x-pneuma-schema-kind"] == "resampling-study"
        assert schema["x-pneuma-version"] == "0.1.0"
        assert schema["additionalProperties"] is False
        Draft202012Validator.check_schema(schema)
        assert validate_record(_record(kind, _minimal_payload(kind)))


@pytest.mark.parametrize("bad_kind", ["unknown", "", "RESAMPLING_STUDY_MANIFEST"])
def test_unknown_record_kinds_fail_closed(bad_kind: str) -> None:
    value = _record("resampling_study_manifest", _minimal_payload("resampling_study_manifest"))
    value["record_kind"] = bad_kind
    with pytest.raises(RecordValidationError, match="record_kind"):
        validate_record(value)


def test_unknown_properties_and_malformed_digests_fail_closed() -> None:
    value = _record("resampling_study_manifest", _minimal_payload("resampling_study_manifest"))
    value["surprise"] = True
    with pytest.raises(RecordValidationError):
        validate_record(value)
    del value["surprise"]
    value["provenance"]["code_sha256"] = "A" * 64  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(value)


def test_duplicate_keys_nan_and_bom_fail_closed(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"record_kind":"x","record_kind":"y"}',
        encoding="utf-8",
    )
    with pytest.raises(RecordValidationError, match="duplicate"):
        load_record(duplicate)
    nonfinite = tmp_path / "nan.json"
    nonfinite.write_text('{"value":NaN}', encoding="utf-8")
    with pytest.raises(RecordValidationError, match="non-finite"):
        load_record(nonfinite)
    bom = tmp_path / "bom.json"
    bom.write_bytes(b"\xef\xbb\xbf{}")
    with pytest.raises(RecordValidationError, match="BOM"):
        load_record(bom)


def test_packet_and_power_stage_payloads_are_discriminated() -> None:
    packet = _record("resampling_packet_index", _minimal_payload("resampling_packet_index"))
    packet["payload"]["stage"] = "draft"  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(packet)
    packet = _record("resampling_packet_index", _minimal_payload("resampling_packet_index"))
    packet["payload"]["candidate_ref"] = _ref("candidate.json")  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(packet)
    candidate_payload = _minimal_payload("resampling_packet_index")
    sealed_payload = {
        "stage": "sealed",
        "candidate_ref": _ref("packet-candidate.json"),
        **{
            key: candidate_payload[key]
            for key in (
                "assignment_ref",
                "prefix_index_ref",
                "tokenizer_ref",
                "packet_template_ref",
                "packet_policy_ref",
                "pad_unit_set_ref",
            )
        },
        "audit_gates": {
            "roster_complete": True,
            "ancestry_valid": True,
            "token_parity": True,
            "schema_parity": True,
            "field_parity": True,
            "severity_parity": True,
            "rewrites_complete": True,
            "identifier_collision_free": True,
            "artifact_bytes_verified": True,
        },
    }
    validate_record(_record("resampling_packet_index", sealed_payload))

    for stage in ("screen", "shard", "selection", "validation", "final"):
        power = _record(
            "resampling_power_report",
            _power_payload(stage, shard_index=0),
        )
        validate_record(power)
    power = _record("resampling_power_report", _power_payload("screen"))
    power["payload"]["stage"] = "adhoc"  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(power)

    completed = _power_payload("final")
    attempts = completed["all_attempt_refs"]
    completed["parent_refs"] = attempts
    completed["finalization"] = {
        "kind": "completed_chain",
        "selected_phase": "gaussian_approximation",
        "selected_generation": 0,
        "selected_screen_ref": attempts[0],  # type: ignore[index]
        "selected_shard_refs": [attempts[1]],  # type: ignore[index]
        "selected_selection_ref": attempts[2],  # type: ignore[index]
        "selected_validation_ref": attempts[3],  # type: ignore[index]
    }
    validate_record(_record("resampling_power_report", completed))
    full_validation = _power_payload("validation")
    full_validation["phase"] = "full_multiplier_fallback"
    del full_validation["selected_cells"]
    del full_validation["interval_receipts"]
    del full_validation["validation_dataset_count"]
    full_validation.update(
        fallback_trigger_ref=_ref("power/gaussian-trigger.json"),
        complete_cell_ids=["cell-1"],
        expected_cell_count=1,
        observed_cell_count=1,
        raw_counts_ref=_ref("power/raw-counts.json"),
        numeric_receipt_ref=_ref("power/numeric.json"),
        selected_tier=None,
        decision="CONDITIONAL_ONLY",
    )
    validate_record(_record("resampling_power_report", full_validation))
    full_completed = _power_payload("final")
    full_completed["phase"] = "full_multiplier_fallback"
    full_completed["generation"] = 1
    full_completed["parent_refs"] = full_completed["all_attempt_refs"]
    full_completed["finalization"] = {
        "kind": "completed_chain",
        "selected_phase": "full_multiplier_fallback",
        "selected_generation": 1,
        "fallback_trigger_ref": _ref("power/gaussian-trigger.json"),
        "selected_screen_ref": _ref("power/full-screen.json"),
        "selected_shard_refs": [_ref("power/full-shard.json")],
        "full_grid_validation_ref": _ref("power/full-validation.json"),
    }
    validate_record(_record("resampling_power_report", full_completed))
    no_go = _power_payload("final")
    no_go["finalization"]["selected_validation_ref"] = _ref("fabricated.json")  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(_record("resampling_power_report", no_go))


def _numeric_contract() -> dict[str, object]:
    return {
        "numpy_version": "2.0.0",
        "gauss_hermite_order": 96,
        "gauss_legendre_order": 128,
        "probability_tolerance": 1e-10,
        "gaussian_root_tolerance": 1e-10,
        "gaussian_root_max_iterations": 200,
        "clopper_pearson_tolerance": 1e-12,
        "clopper_pearson_max_iterations": 200,
    }


def _power_payload(stage: str, *, shard_index: int | None = None) -> dict[str, object]:
    parent_refs = [] if stage == "screen" else [_ref("parents/power-parent.json")]
    base: dict[str, object] = {
        "stage": stage,
        "decision_authority": "synthetic_validation",
        "phase": "gaussian_approximation",
        "generation": 0,
        "roster_ref": _ref("parents/roster.json", role="roster"),
        "grid_ref": _ref("parents/grid.json", role="grid"),
        "parent_refs": parent_refs,
        "topology_ref": _ref("parents/topology.json", role="topology"),
        "config_ref": _ref("parents/power-config.json", role="power_config"),
        "numeric_fixture_ref": _ref(
            "parents/numeric-fixture.json",
            role="numeric_fixture",
        ),
        "numeric_contract": _numeric_contract(),
    }
    if stage == "screen":
        base.update(projected_wall_seconds=1, cell_count=1, dataset_count=200)
    elif stage == "shard":
        base.update(
            shard_index=0 if shard_index is None else shard_index,
            shard_count=2,
            cell_results=[],
            dataset_count=20_000,
        )
    elif stage == "selection":
        cells = [f"cell-{index}" for index in range(5)]
        base.update(
            selected_cells=cells,
            candidate_count=5,
            selection_count=5,
        )
    elif stage == "validation":
        cells = [f"cell-{index}" for index in range(5)]
        base.update(
            selected_cells=cells,
            interval_receipts=[
                {
                    "cell_id": cell,
                    "alternative_power_lower": 0.8,
                    "null_false_positive_upper": 0.05,
                }
                for cell in cells
            ],
            validation_dataset_count=2_000,
        )
    elif stage == "final":
        attempt_refs = [
            _ref(f"power/attempt-{index}.json", role="power_attempt")
            for index in range(4)
        ]
        base.update(
            all_attempt_refs=attempt_refs,
            finalization={
                "kind": "feasibility_no_go",
                "terminal_attempt_ref": attempt_refs[0],
                "terminal_stage": "screen",
                "reason": "gaussian_screen_exhausted",
            },
        )
    return base


def _bind_power_sources(
    payload: dict[str, object],
    source_ref: dict[str, object],
) -> None:
    for key in (
        "roster_ref",
        "grid_ref",
        "topology_ref",
        "config_ref",
        "numeric_fixture_ref",
    ):
        payload[key] = source_ref


def test_canonical_digest_ignores_mapping_insertion_order() -> None:
    left = {"b": {"y": 2, "x": 1}, "a": [3, 4]}
    right = {"a": [3, 4], "b": {"x": 1, "y": 2}}
    assert canonical_digest(left) == canonical_digest(right)


def test_nested_parent_change_invalidates_digest_link() -> None:
    parent = {"payload": {"outcomes": [{"success": 0}]}}
    child = {"parent_sha256": canonical_digest(parent)}
    verify_digest_link(child, "parent_sha256", parent)
    parent["payload"]["outcomes"][0]["success"] = 1  # type: ignore[index]
    with pytest.raises(RecordValidationError, match="parent_sha256"):
        verify_digest_link(child, "parent_sha256", parent)


def test_writes_refuse_overwrite_and_publish_nothing_on_serialization_failure(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    manifest_path = root / "manifest.json"
    manifest = _record(
        "resampling_study_manifest",
        _minimal_payload("resampling_study_manifest"),
    )
    ref = write_record(
        manifest_path,
        manifest,
        run_root=root,
        role="study_manifest",
    )
    assert ref.relative_path == "manifest.json"
    with pytest.raises(FileExistsError):
        write_record(manifest_path, manifest, run_root=root, role="study_manifest")

    bad_json = root / "bad.json"
    bad = deepcopy(manifest)
    bad["payload"]["bad"] = object()  # type: ignore[index]
    with pytest.raises((RecordValidationError, TypeError)):
        write_record(bad_json, bad, run_root=root, role="bad")
    assert not bad_json.exists()

    bad_jsonl = root / "bad.jsonl"
    with pytest.raises((RecordValidationError, TypeError, ValueError)):
        write_jsonl_artifact(
            bad_jsonl,
            [{"ok": 1}, {"bad": math.nan}],
            run_root=root,
            role="rows",
        )
    assert not bad_jsonl.exists()


def test_scientific_descendant_requires_study_manifest(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    schedule = _record(
        "resampling_prefix_schedule",
        _minimal_payload("resampling_prefix_schedule"),
    )
    with pytest.raises(RecordValidationError, match="study manifest"):
        write_record(root / "schedule.json", schedule, run_root=root, role="schedule")


def test_study_manifest_seal_copies_all_sources_without_reading_clock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external = tmp_path / "external"
    external.mkdir()
    sources: dict[str, Path] = {}
    for name in (
        "tasks",
        "roster",
        "assignment",
        "provider",
        "tokenizer",
        "template",
        "policy",
        "pads",
        "required",
        "revision-a",
        "revision-b",
    ):
        source = external / f"{name}.json"
        source.write_text(json.dumps({"name": name}), encoding="utf-8")
        sources[name] = source
    sources["required"].write_text(
        json.dumps(["resampling_study_manifest"]),
        encoding="utf-8",
    )
    study = external / "study.json"
    study.write_text(
        json.dumps(
            _record(
                "resampling_study_manifest",
                {"seed_commitment_sha256": SHA_A},
            )
        ),
        encoding="utf-8",
    )
    run_root = tmp_path / "run"
    run_root.mkdir()

    import time

    monkeypatch.setattr(time, "time", lambda: (_ for _ in ()).throw(AssertionError("clock")))
    manifest_ref = seal_study_manifest(
        study,
        sources["tasks"],
        sources["roster"],
        sources["assignment"],
        sources["provider"],
        sources["tokenizer"],
        sources["template"],
        sources["policy"],
        sources["pads"],
        [sources["revision-a"], sources["revision-b"]],
        sources["required"],
        run_root=run_root,
        out=run_root / "study-manifest.json",
    )
    manifest = load_record(run_root / manifest_ref.relative_path)
    payload = manifest["payload"]
    for key in (
        "task_registry_ref",
        "roster_ref",
        "assignment_program_ref",
        "provider_lane_plan_ref",
        "tokenizer_ref",
        "packet_template_ref",
        "packet_policy_ref",
        "pad_unit_set_ref",
        "required_document_kinds_ref",
    ):
        assert (run_root / payload[key]["relative_path"]).is_file()  # type: ignore[index]
    assert len(payload["source_revision_refs"]) == 2  # type: ignore[arg-type]
    assert manifest["frozen_created_at"] == FROZEN


def test_source_revisions_must_be_nonempty_and_sorted(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(["resampling_study_manifest"]),
        encoding="utf-8",
    )
    study = tmp_path / "study.json"
    study.write_text(
        json.dumps(
            _record(
                "resampling_study_manifest",
                {"seed_commitment_sha256": SHA_A},
            )
        ),
        encoding="utf-8",
    )
    root = tmp_path / "run"
    root.mkdir()
    args = [study] + [source] * 8
    with pytest.raises(ValueError, match="non-empty"):
        seal_study_manifest(
            *args,
            [],
            source,
            run_root=root,
            out=root / "study-manifest.json",
        )
    z = tmp_path / "z.json"
    a = tmp_path / "a.json"
    z.write_text("{}", encoding="utf-8")
    a.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="sorted"):
        seal_study_manifest(
            *args,
            [z, a],
            source,
            run_root=root,
            out=root / "study-manifest.json",
        )


def test_artifact_root_follows_raw_refs_and_detects_byte_changes(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    raw_ref = _write_blob(root, "raw/snapshot.bin", b"snapshot")
    required_ref = _write_blob(
        root,
        "raw/required.json",
        json.dumps(["resampling_study_manifest"]).encode(),
    )
    manifest = _record(
        "resampling_study_manifest",
        _minimal_payload("resampling_study_manifest"),
    )
    for key in tuple(manifest["payload"]):  # type: ignore[arg-type]
        if key.endswith("_ref"):
            manifest["payload"][key] = raw_ref  # type: ignore[index]
    manifest["payload"]["required_document_kinds_ref"] = required_ref  # type: ignore[index]
    manifest["payload"]["source_revision_refs"] = [raw_ref]  # type: ignore[index]
    write_record(root / "manifest.json", manifest, run_root=root, role="manifest")
    receipt = seal_artifact_root(
        root,
        ["resampling_study_manifest"],
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    root_record = load_record(root / receipt.relative_path)
    paths = [entry["relative_path"] for entry in root_record["payload"]["entries"]]  # type: ignore[index]
    assert paths == sorted(paths)
    assert "p0-core-receipt.json" not in paths
    assert "raw/snapshot.bin" in paths
    verify_artifact_root(
        root / "p0-core-receipt.json",
        root,
        required_document_kinds=["resampling_study_manifest"],
    )
    (root / "raw/snapshot.bin").write_bytes(b"changed")
    with pytest.raises(RecordValidationError):
        verify_artifact_root(
            root / "p0-core-receipt.json",
            root,
            required_document_kinds=["resampling_study_manifest"],
        )


def test_artifact_root_rejects_dangling_and_conflicting_refs(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    manifest = _record(
        "resampling_study_manifest",
        _minimal_payload("resampling_study_manifest"),
    )
    valid_ref = _write_blob(root, "raw/valid.bin", b"valid")
    required_ref = _write_blob(
        root,
        "raw/required.json",
        json.dumps(["resampling_study_manifest"]).encode(),
    )
    for key in tuple(manifest["payload"]):  # type: ignore[arg-type]
        if key.endswith("_ref"):
            manifest["payload"][key] = valid_ref  # type: ignore[index]
    manifest["payload"]["required_document_kinds_ref"] = required_ref  # type: ignore[index]
    manifest["payload"]["source_revision_refs"] = [  # type: ignore[index]
        _ref("raw/missing.bin", byte_count=3, media_type="application/octet-stream")
    ]
    write_record(root / "manifest.json", manifest, run_root=root, role="manifest")
    with pytest.raises(RecordValidationError, match="dangling"):
        seal_artifact_root(
            root,
            ["resampling_study_manifest"],
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )

    (root / "raw").mkdir(exist_ok=True)
    (root / "raw/missing.bin").write_bytes(b"x")
    shared = _write_blob(root, "raw/shared.bin", b"shared")
    manifest["payload"]["source_revision_refs"] = [  # type: ignore[index]
        shared,
        {**shared, "role": "different"},
    ]
    (root / "manifest.json").unlink()
    write_record(root / "manifest.json", manifest, run_root=root, role="manifest")
    with pytest.raises(RecordValidationError, match="conflicting"):
        seal_artifact_root(
            root,
            ["resampling_study_manifest"],
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_task_block_triggered_and_no_trigger_arms_are_closed() -> None:
    refs = {
        name: _ref(f"parents/{name}.json", role=name)
        for name in (
            "schedule_ref",
            "prefix_index_ref",
            "assignment_ref",
            "packet_index_ref",
            "analysis_freeze_ref",
        )
    }
    no_trigger = _record(
        "resampling_task_block",
        _no_trigger_task_block_payload(refs),
    )
    validate_record(no_trigger)
    no_trigger["payload"]["attempts"] = []  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(no_trigger)

    triggered = _record(
        "resampling_task_block",
        _triggered_task_block_payload(refs),
    )
    validate_record(triggered)
    triggered["payload"]["terminal_slot_receipts"] = None  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(triggered)


def _triggered_task_block_payload(
    refs: dict[str, dict[str, object]],
) -> dict[str, object]:
    payload = _no_trigger_task_block_payload(refs)
    payload["triggered"] = True
    terminal_receipts = [
        {
            "slot_id": f"slot-{index}",
            "opaque_capability_id": f"opaque-{index}",
            "pre_injection_visible_sha256": SHA_A,
            "pre_injection_token_ids_sha256": SHA_B,
            "final_snapshot_ref": _ref(f"snapshots/{index}.bin"),
            "counters": {
                "generated_tokens": 1,
                "model_calls": 1,
                "tool_calls": 0,
                "wall_clock_ms": 1,
            },
            "call_seeds": [
                {
                    "subject_role": "primary_subject",
                    "call_index": 0,
                    "seed": index,
                }
            ],
            "failure_kind": "none",
            "provider_cost_ref": _ref(f"costs/{index}.json"),
            "endpoint_readable": False,
        }
        for index in range(4)
    ]
    payload["attempts"] = [
        {
            "attempt_index": 0,
            "attempt_ref": _ref("attempts/attempt-0.json"),
            "work_order_sha256s": [
                hashlib.sha256(f"work-{index}".encode()).hexdigest()
                for index in range(4)
            ],
            "terminal_receipts": terminal_receipts,
            "complete": True,
            "endpoint_readable": False,
        }
    ]
    payload["selected_attempt_index"] = 0
    payload["terminal_slot_receipts"] = terminal_receipts
    payload["execution_receipts"] = [
        {
            "source_receipt_sha256": SHA_A,
            "source_kind": "graded_unscored",
            "grade_receipt": {
                "success": 0,
                "partial_reward": 0.0,
                "infrastructure_failure": False,
                "artifact_ref": _ref(f"grades/{index}.json"),
            },
            "outcome": _outcome(index),
        }
        for index in range(4)
    ]
    return payload


def test_artifact_root_requires_exact_roster_unique_task_blocks(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    shared = _write_blob(root, "raw/shared.json", b"{}")
    roster = _write_blob(
        root,
        "raw/roster.json",
        json.dumps({"tasks": [{"task_id": "task-1"}]}).encode(),
    )
    required = _write_blob(
        root,
        "raw/required.json",
        json.dumps(
            ["resampling_study_manifest", "resampling_task_block"]
        ).encode(),
    )
    manifest = _record(
        "resampling_study_manifest",
        _minimal_payload("resampling_study_manifest"),
    )
    _replace_artifact_refs(manifest["payload"], shared)
    manifest["payload"]["roster_ref"] = roster  # type: ignore[index]
    manifest["payload"]["required_document_kinds_ref"] = required  # type: ignore[index]
    write_record(root / "manifest.json", manifest, run_root=root, role="manifest")

    parent_refs = {
        name: shared
        for name in (
            "schedule_ref",
            "prefix_index_ref",
            "assignment_ref",
            "packet_index_ref",
            "analysis_freeze_ref",
        )
    }
    task_payload = _no_trigger_task_block_payload(parent_refs)
    _replace_artifact_refs(task_payload, shared)
    write_record(
        root / "task-1.json",
        _record("resampling_task_block", task_payload),
        run_root=root,
        role="task_block",
    )
    receipt = seal_artifact_root(
        root,
        ["resampling_study_manifest", "resampling_task_block"],
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()

    (root / receipt.relative_path).unlink()
    extra_payload = deepcopy(task_payload)
    extra_payload["task_id"] = "task-2"
    for outcome in extra_payload["slot_outcomes"]:
        outcome["task_id"] = "task-2"
    write_record(
        root / "task-2.json",
        _record("resampling_task_block", extra_payload),
        run_root=root,
        role="task_block",
    )
    with pytest.raises(RecordValidationError, match="cover the roster"):
        seal_artifact_root(
            root,
            ["resampling_study_manifest", "resampling_task_block"],
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_artifact_root_document_coverage_and_power_identities(tmp_path: Path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    manifest = _record(
        "resampling_study_manifest",
        _minimal_payload("resampling_study_manifest"),
    )
    # Make every manifest ref resolve to one shared raw blob.
    raw = _write_blob(root, "raw/shared.json", b"{}")
    required_ref = _write_blob(
        root,
        "raw/required.json",
        json.dumps(
            ["resampling_power_report", "resampling_study_manifest"]
        ).encode(),
    )
    for key, value in list(manifest["payload"].items()):  # type: ignore[union-attr]
        if key.endswith("_ref"):
            manifest["payload"][key] = raw  # type: ignore[index]
        elif key == "source_revision_refs":
            manifest["payload"][key] = [raw]  # type: ignore[index]
    manifest["payload"]["required_document_kinds_ref"] = required_ref  # type: ignore[index]
    write_record(root / "manifest.json", manifest, run_root=root, role="manifest")
    with pytest.raises(RecordValidationError, match="missing"):
        seal_artifact_root(
            root,
            ["resampling_study_manifest", "resampling_power_report"],
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )

    screen_payload = _power_payload("screen")
    _bind_power_sources(screen_payload, raw)
    screen_ref = _artifact_mapping(
        write_record(
            root / "power-screen.json",
            _record("resampling_power_report", screen_payload),
            run_root=root,
            role="power_screen",
        )
    )
    retry_screen_payload = _power_payload("screen")
    retry_screen_payload["generation"] = 1
    _bind_power_sources(retry_screen_payload, raw)
    retry_screen_ref = _artifact_mapping(
        write_record(
            root / "power-screen-generation-1.json",
            _record("resampling_power_report", retry_screen_payload),
            run_root=root,
            role="power_screen",
        )
    )
    shard_refs: list[dict[str, object]] = []
    for shard_index in (0, 1):
        shard_payload = _power_payload("shard", shard_index=shard_index)
        _bind_power_sources(shard_payload, raw)
        shard_payload["parent_refs"] = [screen_ref]
        shard_refs.append(
            _artifact_mapping(
                write_record(
                    root / f"power-shard-{shard_index}.json",
                    _record("resampling_power_report", shard_payload),
                    run_root=root,
                    role="power_shard",
                )
            )
        )
    selection_payload = _power_payload("selection")
    _bind_power_sources(selection_payload, raw)
    selection_payload["parent_refs"] = [screen_ref, *shard_refs]
    selection_ref = _artifact_mapping(
        write_record(
            root / "power-selection.json",
            _record("resampling_power_report", selection_payload),
            run_root=root,
            role="power_selection",
        )
    )
    validation_payload = _power_payload("validation")
    _bind_power_sources(validation_payload, raw)
    validation_payload["parent_refs"] = [
        screen_ref,
        *shard_refs,
        selection_ref,
    ]
    validation_ref = _artifact_mapping(
        write_record(
            root / "power-validation.json",
            _record("resampling_power_report", validation_payload),
            run_root=root,
            role="power_validation",
        )
    )
    all_attempt_refs = [
        screen_ref,
        retry_screen_ref,
        *shard_refs,
        selection_ref,
        validation_ref,
    ]
    final_payload = _power_payload("final")
    _bind_power_sources(final_payload, raw)
    final_payload["parent_refs"] = all_attempt_refs
    final_payload["all_attempt_refs"] = all_attempt_refs
    final_payload["finalization"] = {
        "kind": "completed_chain",
        "selected_phase": "gaussian_approximation",
        "selected_generation": 0,
        "selected_screen_ref": screen_ref,
        "selected_shard_refs": shard_refs,
        "selected_selection_ref": selection_ref,
        "selected_validation_ref": validation_ref,
    }
    write_record(
        root / "power-final.json",
        _record("resampling_power_report", final_payload),
        run_root=root,
        role="power_final",
    )
    receipt = seal_artifact_root(
        root,
        ["resampling_study_manifest", "resampling_power_report"],
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()

    (root / "p0-core-receipt.json").unlink()
    duplicate_payload = _power_payload("shard", shard_index=1)
    _bind_power_sources(duplicate_payload, raw)
    duplicate_payload["parent_refs"] = [screen_ref]
    write_record(
        root / "power-shard-duplicate.json",
        _record("resampling_power_report", duplicate_payload),
        run_root=root,
        role="power_shard",
    )
    with pytest.raises(RecordValidationError, match="duplicate"):
        seal_artifact_root(
            root,
            ["resampling_study_manifest", "resampling_power_report"],
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )
