"""Contract tests for resampling-null schemas and canonical artifact IO."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
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
FROZEN_UPSTREAM_KINDS = tuple(
    sorted(kind for kind in KINDS if kind != "resampling_artifact_root")
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
            "required_document_kinds": list(FROZEN_UPSTREAM_KINDS),
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


@pytest.mark.parametrize(
    "required_kinds",
    [
        [],
        ["resampling_study_manifest"],
        [*FROZEN_UPSTREAM_KINDS, "resampling_artifact_root"],
        [
            *FROZEN_UPSTREAM_KINDS,
            FROZEN_UPSTREAM_KINDS[-1],
        ],
    ],
)
def test_artifact_root_schema_requires_exact_frozen_upstream_kinds(
    required_kinds: list[str],
) -> None:
    value = _record(
        "resampling_artifact_root",
        _minimal_payload("resampling_artifact_root"),
    )
    value["payload"]["required_document_kinds"] = required_kinds  # type: ignore[index]
    with pytest.raises(RecordValidationError, match="required_document_kinds"):
        validate_record(value)


@pytest.mark.parametrize(
    "nonfinite",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        pytest.param(
            __import__("numpy").float32("nan"),
            id="numpy-float32-nan",
        ),
        pytest.param(
            __import__("numpy").float64("inf"),
            id="numpy-float64-infinity",
        ),
    ],
)
def test_non_builtin_nonfinite_numbers_fail_closed(nonfinite: object) -> None:
    value = _record(
        "resampling_analysis",
        _minimal_payload("resampling_analysis"),
    )
    value["payload"]["result"]["continuation"] = nonfinite  # type: ignore[index]
    with pytest.raises(RecordValidationError, match="non-finite"):
        validate_record(value)


@pytest.mark.parametrize(
    "number",
    [
        Decimal("0.5"),
        pytest.param(__import__("numpy").float32(0.5), id="numpy-float32"),
        pytest.param(__import__("numpy").int64(1), id="numpy-int64"),
    ],
)
def test_non_builtin_finite_numbers_are_not_plain_json(number: object) -> None:
    value = _record(
        "resampling_analysis",
        _minimal_payload("resampling_analysis"),
    )
    value["payload"]["result"]["continuation"] = number  # type: ignore[index]
    with pytest.raises(RecordValidationError, match="plain JSON number"):
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
    del full_validation["approximation_receipt"]
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


def _write_test_record(
    root: Path,
    relative_path: str,
    kind: str,
    payload: dict[str, object],
) -> dict[str, object]:
    return _artifact_mapping(
        write_record(
            root / relative_path,
            _record(kind, payload),
            run_root=root,
            role=kind,
        )
    )


def _cell_result(cell_id: str) -> dict[str, object]:
    return {
        "cell_id": cell_id,
        "alternative_pass_count": 16_000,
        "alternative_trial_count": 20_000,
        "null_pass_count": 1_000,
        "null_trial_count": 20_000,
    }


def _build_full_study(
    root: Path,
    *,
    variant: str | None = None,
    fallback: bool = False,
    omit_kind: str | None = None,
) -> dict[str, object]:
    root.mkdir()

    def raw(name: str, value: object) -> dict[str, object]:
        payload = (
            value
            if isinstance(value, bytes)
            else json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        )
        return _write_blob(root, f"raw/{name}", payload)

    raws = {
        "tasks": raw("tasks.json", {"tasks": [{"task_id": "task-1"}]}),
        "roster": raw("roster.json", {"tasks": [{"task_id": "task-1"}]}),
        "assignment": raw("assignment.py", b"assignment"),
        "provider": raw("provider.json", {"lane": "lane-a"}),
        "tokenizer": raw("tokenizer.json", {"name": "tokenizer"}),
        "template": raw("template.json", {"name": "template"}),
        "policy": raw("policy.json", {"name": "policy"}),
        "pads": raw("pads.json", {"units": []}),
        "revision": raw("revision.md", b"revision"),
        "required": raw("required.json", list(FROZEN_UPSTREAM_KINDS)),
        "shared": raw("shared.bin", b"shared"),
        "analysis_config": raw("analysis-config.json", {"alpha": 0.05}),
        "projection_schema": raw("projection-schema.json", {"version": 1}),
        "power_grid": raw(
            "power-grid.json",
            {"cells": [{"cell_id": f"cell-{index}"} for index in range(5)]},
        ),
        "topology": raw("topology.json", {"cpu_count": 1}),
        "power_config": raw("power-config.json", {"datasets": 20_000}),
        "numeric_fixture": raw("numeric-fixture.json", {"digest": SHA_A}),
        "alternate": raw("alternate.bin", b"alternate"),
    }

    manifest_payload = {
        "task_registry_ref": raws["tasks"],
        "roster_ref": raws["roster"],
        "assignment_program_ref": raws["assignment"],
        "provider_lane_plan_ref": raws["provider"],
        "tokenizer_ref": raws["tokenizer"],
        "packet_template_ref": raws["template"],
        "packet_policy_ref": raws["policy"],
        "pad_unit_set_ref": raws["pads"],
        "source_revision_refs": [raws["revision"]],
        "seed_commitment_sha256": SHA_A,
        "required_document_kinds_ref": raws["required"],
    }
    manifest_ref = _write_test_record(
        root,
        "study-manifest.json",
        "resampling_study_manifest",
        manifest_payload,
    )

    schedule_payload = _minimal_payload("resampling_prefix_schedule")
    schedule_payload["manifest_ref"] = manifest_ref
    schedule_payload["assignment_program_ref"] = (
        raws["alternate"]
        if variant == "schedule-assignment-program"
        else raws["assignment"]
    )
    schedule_payload["provider_lane_plan_ref"] = (
        raws["alternate"]
        if variant == "schedule-provider-lane"
        else raws["provider"]
    )
    schedule_ref = _write_test_record(
        root,
        "prefix-schedule.json",
        "resampling_prefix_schedule",
        schedule_payload,
    )

    prefix_schedule_sha = cast(str, schedule_ref["sha256"])
    if variant == "prefix-schedule-hash":
        prefix_schedule_sha = SHA_A
    verifier_schedule_sha = cast(str, schedule_ref["sha256"])
    if variant == "prefix-verifier-schedule-hash":
        verifier_schedule_sha = SHA_A
    prefix_task_receipt = {
        "task_id": "task-1",
        "schedule_sha256": prefix_schedule_sha,
        "snapshot_ref": raws["shared"],
        "visible_context_ref": (
            {**raws["shared"], "role": "frankenstein"}
            if variant == "conflicting-ref"
            else raws["shared"]
        ),
        "visible_sha256": SHA_A,
        "token_ids_sha256": SHA_B,
        "pending_tool_calls": [],
        "trigger_reason": "no_intervention_opportunity",
        "y0_grade": {
            "success": 0,
            "partial_reward": 0.0,
            "infrastructure_failure": False,
            "artifact_ref": raws["shared"],
        },
        "verifier_receipt": {
            "task_id": "task-1",
            "schedule_sha256": verifier_schedule_sha,
            "snapshot_ref": raws["shared"],
            "verifier_artifact_ref": raws["shared"],
            "finding_count": 0,
        },
        "counters": {
            "generated_tokens": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "call_seeds": [],
        "provider_cost_ref": (
            _ref(
                "raw/missing.bin",
                byte_count=3,
                media_type="application/octet-stream",
            )
            if variant == "dangling-ref"
            else raws["shared"]
        ),
    }
    prefix_ref = _write_test_record(
        root,
        "prefix-receipt.json",
        "resampling_prefix_receipt",
        {
            "schedule_ref": schedule_ref,
            "task_receipts": [prefix_task_receipt],
        },
    )

    assignment_schedule_sha = cast(str, schedule_ref["sha256"])
    if variant == "assignment-schedule-hash":
        assignment_schedule_sha = SHA_A
    assignment_prefix_sha = cast(str, prefix_ref["sha256"])
    if variant == "assignment-prefix-hash":
        assignment_prefix_sha = SHA_A
    assignment_payload = {
        "schedule_ref": schedule_ref,
        "prefix_index_ref": prefix_ref,
        "assignment_mode": "uniform_12",
        "assignments": [
            {
                "task_id": "task-1",
                "task_lineage": "repo-1",
                "donor_task_id": "task-donor",
                "donor_lineage": "repo-donor",
                "slot_arms": [
                    ["slot-0", "REAL"],
                    ["slot-1", "SHAM"],
                    ["slot-2", "NONE"],
                    ["slot-3", "RESAMPLE"],
                ],
                "schedule_sha256": assignment_schedule_sha,
                "prefix_index_sha256": assignment_prefix_sha,
            }
        ],
        "allocation_receipts": [
            {
                "task_id": "task-1",
                "treatment_allocation_index": 0,
                "no_packet_orientation_bit": 0,
                "slot_capabilities": [
                    [f"slot-{index}", hashlib.sha256(f"cap-{index}".encode()).hexdigest()]
                    for index in range(4)
                ],
            }
        ],
    }
    assignment_ref = _write_test_record(
        root,
        "assignment-ledger.json",
        "resampling_assignment_ledger",
        assignment_payload,
    )

    candidate_payload = {
        "stage": "candidate",
        "assignment_ref": assignment_ref,
        "prefix_index_ref": prefix_ref,
        "tokenizer_ref": (
            raws["alternate"]
            if variant == "packet-tokenizer"
            else raws["tokenizer"]
        ),
        "packet_template_ref": raws["template"],
        "packet_policy_ref": raws["policy"],
        "pad_unit_set_ref": raws["pads"],
        "entries": [
            {
                "task_id": "task-1",
                "prefix_index_sha256": cast(str, prefix_ref["sha256"]),
                "trigger_reason": "no_intervention_opportunity",
            }
        ],
    }
    candidate_ref = _write_test_record(
        root,
        "packet-candidate.json",
        "resampling_packet_index",
        candidate_payload,
    )
    sealed_payload = {
        "stage": "sealed",
        "candidate_ref": candidate_ref,
        "assignment_ref": assignment_ref,
        "prefix_index_ref": prefix_ref,
        "tokenizer_ref": candidate_payload["tokenizer_ref"],
        "packet_template_ref": raws["template"],
        "packet_policy_ref": (
            raws["alternate"]
            if variant == "sealed-packet-policy"
            else raws["policy"]
        ),
        "pad_unit_set_ref": raws["pads"],
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
    sealed_ref = _write_test_record(
        root,
        "packet-sealed.json",
        "resampling_packet_index",
        sealed_payload,
    )

    freeze_ref = _write_test_record(
        root,
        "analysis-freeze.json",
        "resampling_analysis_freeze",
        {
            "source_refs": [raws["shared"]],
            "config_ref": raws["analysis_config"],
            "projection_schema_ref": raws["projection_schema"],
            "packet_index_ref": sealed_ref,
        },
    )
    task_parent_refs = {
        "schedule_ref": schedule_ref,
        "prefix_index_ref": prefix_ref,
        "assignment_ref": assignment_ref,
        "packet_index_ref": sealed_ref,
        "analysis_freeze_ref": freeze_ref,
    }
    task_payload = _no_trigger_task_block_payload(task_parent_refs)
    for outcome in cast(list[dict[str, object]], task_payload["slot_outcomes"]):
        outcome["artifact_ref"] = raws["shared"]
    task_ref = _write_test_record(
        root,
        "task-1.json",
        "resampling_task_block",
        task_payload,
    )
    if variant == "extra-task":
        extra_payload = deepcopy(task_payload)
        extra_payload["task_id"] = "task-2"
        for outcome in cast(
            list[dict[str, object]],
            extra_payload["slot_outcomes"],
        ):
            outcome["task_id"] = "task-2"
        _write_test_record(
            root,
            "task-2.json",
            "resampling_task_block",
            extra_payload,
        )

    projection_payload = {
        "schedule_ref": schedule_ref,
        "analysis_freeze_ref": freeze_ref,
        "task_block_refs": [task_ref],
        "rows": [
            {
                "task_id": "task-1",
                "benchmark": "swe",
                "stratum": "python",
                "lineage": "repo-1",
                "sensitivity_groups": [
                    {"kind": "language", "value": "python"}
                ],
                "prefix_success": 0,
                "triggered": False,
                "slots": [
                    {
                        "label": label,
                        "slot_id": f"slot-{index}",
                        "outcome": deepcopy(task_payload["slot_outcomes"][index]),  # type: ignore[index]
                    }
                    for index, label in enumerate(("A", "B", "C", "D"))
                ],
                "pipeline_valid": True,
                "validity_codes": [],
            }
        ],
        "expected_task_count": 1,
        "complete": True,
    }
    projection_ref = _write_test_record(
        root,
        "projection.json",
        "resampling_blinded_projection",
        projection_payload,
    )
    unblind_ref = _write_test_record(
        root,
        "unblind.json",
        "resampling_unblind_receipt",
        {
            "projection_ref": projection_ref,
            "assignment_ledger_ref": assignment_ref,
            "analysis_freeze_ref": freeze_ref,
            "expected_task_count": 1,
            "permit_hmac_sha256": SHA_A,
        },
    )
    if omit_kind != "resampling_analysis":
        _write_test_record(
            root,
            "analysis.json",
            "resampling_analysis",
            {
                "analysis_freeze_ref": freeze_ref,
                "projection_ref": projection_ref,
                "unblind_receipt_ref": unblind_ref,
                "config_ref": (
                    raws["alternate"]
                    if variant == "analysis-config"
                    else raws["analysis_config"]
                ),
                "row_count": 1,
                "result": _analysis_result(),
                "numeric_receipt": {"finite": True},
            },
        )

    common_power = {
        "roster_ref": raws["roster"],
        "grid_ref": raws["power_grid"],
        "topology_ref": raws["topology"],
        "config_ref": raws["power_config"],
        "numeric_fixture_ref": raws["numeric_fixture"],
        "numeric_contract": _numeric_contract(),
    }

    def bind_power(
        payload: dict[str, object],
        *,
        phase: str = "gaussian_approximation",
    ) -> None:
        payload.update(deepcopy(common_power))
        payload["phase"] = phase

    gaussian_screen = _power_payload("screen")
    bind_power(gaussian_screen)
    gaussian_screen["cell_count"] = 5
    screen_ref = _write_test_record(
        root,
        "power/gaussian-screen.json",
        "resampling_power_report",
        gaussian_screen,
    )
    gaussian_shard_refs: list[dict[str, object]] = []
    gaussian_shard_payloads: list[dict[str, object]] = []
    partitions = [
        ["cell-0", "cell-1", "cell-2"],
        ["cell-3", "cell-4"],
    ]
    if variant == "power-cell-gap":
        partitions[1] = ["cell-3"]
    elif variant == "power-cell-overlap":
        partitions[1] = ["cell-2", "cell-3", "cell-4"]
    for shard_position in range(2):
        shard_payload = _power_payload("shard", shard_index=shard_position)
        bind_power(shard_payload)
        shard_payload["parent_refs"] = [screen_ref]
        shard_payload["cell_results"] = [
            _cell_result(cell_id) for cell_id in partitions[shard_position]
        ]
        if variant == "power-shard-gap" and shard_position == 1:
            shard_payload["shard_index"] = 2
            shard_payload["shard_count"] = 3
        elif variant == "power-shard-count" and shard_position == 1:
            shard_payload["shard_count"] = 3
        if variant == "power-shard-parent" and shard_position == 1:
            shard_payload["parent_refs"] = [raws["alternate"]]
        gaussian_shard_payloads.append(shard_payload)
        gaussian_shard_refs.append(
            _write_test_record(
                root,
                f"power/gaussian-shard-{shard_position}.json",
                "resampling_power_report",
                shard_payload,
            )
        )
    selection_payload = _power_payload("selection")
    bind_power(selection_payload)
    selection_payload["parent_refs"] = [screen_ref, *gaussian_shard_refs]
    if variant == "power-selection-parent":
        selection_payload["parent_refs"] = [screen_ref, gaussian_shard_refs[0]]
    selection_ref = _write_test_record(
        root,
        "power/gaussian-selection.json",
        "resampling_power_report",
        selection_payload,
    )
    gaussian_validation = _power_payload("validation")
    bind_power(gaussian_validation)
    gaussian_validation["parent_refs"] = [
        screen_ref,
        *gaussian_shard_refs,
        selection_ref,
    ]
    if fallback:
        gaussian_validation["approximation_receipt"] = {
            "max_absolute_gate_pass_rate_difference": 0.02,
            "gaussian_tier_decision": "C160",
            "full_multiplier_tier_decision": "C120",
            "tier_decision_unchanged": False,
            "passed": False,
        }
    if variant == "power-validation-parent":
        gaussian_validation["parent_refs"] = [
            screen_ref,
            *gaussian_shard_refs,
        ]
    if variant == "power-common-grid":
        gaussian_validation["grid_ref"] = raws["alternate"]
    gaussian_validation_ref = _write_test_record(
        root,
        "power/gaussian-validation.json",
        "resampling_power_report",
        gaussian_validation,
    )

    attempt_refs = [
        screen_ref,
        *gaussian_shard_refs,
        selection_ref,
        gaussian_validation_ref,
    ]
    selected_phase = "gaussian_approximation"
    selected_generation = 0
    finalization: dict[str, object] = {
        "kind": "completed_chain",
        "selected_phase": "gaussian_approximation",
        "selected_generation": 0,
        "selected_screen_ref": screen_ref,
        "selected_shard_refs": (
            [gaussian_shard_refs[0]]
            if variant == "power-finalization-shard-gap"
            else gaussian_shard_refs
        ),
        "selected_selection_ref": selection_ref,
        "selected_validation_ref": gaussian_validation_ref,
    }

    if fallback:
        fallback_trigger = gaussian_validation_ref
        if variant == "fallback-trigger-screen":
            fallback_trigger = screen_ref
        full_screen = _power_payload("screen")
        bind_power(full_screen, phase="full_multiplier_fallback")
        full_screen["cell_count"] = 5
        full_screen["parent_refs"] = [fallback_trigger]
        full_screen_ref = _write_test_record(
            root,
            "power/full-screen.json",
            "resampling_power_report",
            full_screen,
        )
        full_shard_refs: list[dict[str, object]] = []
        for shard_index, cell_ids in enumerate(partitions):
            shard_payload = _power_payload("shard", shard_index=shard_index)
            bind_power(shard_payload, phase="full_multiplier_fallback")
            shard_payload["parent_refs"] = [full_screen_ref]
            shard_payload["cell_results"] = [
                _cell_result(cell_id) for cell_id in cell_ids
            ]
            full_shard_refs.append(
                _write_test_record(
                    root,
                    f"power/full-shard-{shard_index}.json",
                    "resampling_power_report",
                    shard_payload,
                )
            )
        full_validation = _power_payload("validation")
        bind_power(full_validation, phase="full_multiplier_fallback")
        for field in (
            "selected_cells",
            "interval_receipts",
            "validation_dataset_count",
            "approximation_receipt",
        ):
            del full_validation[field]
        full_validation.update(
            parent_refs=[
                fallback_trigger,
                full_screen_ref,
                *full_shard_refs,
            ],
            fallback_trigger_ref=fallback_trigger,
            complete_cell_ids=[f"cell-{index}" for index in range(5)],
            expected_cell_count=5,
            observed_cell_count=5,
            raw_counts_ref=raws["shared"],
            numeric_receipt_ref=raws["numeric_fixture"],
            selected_tier=None,
            decision="CONDITIONAL_ONLY",
        )
        full_validation_ref = _write_test_record(
            root,
            "power/full-validation.json",
            "resampling_power_report",
            full_validation,
        )
        attempt_refs.extend(
            [full_screen_ref, *full_shard_refs, full_validation_ref]
        )
        selected_phase = "full_multiplier_fallback"
        finalization = {
            "kind": "completed_chain",
            "selected_phase": selected_phase,
            "selected_generation": 0,
            "fallback_trigger_ref": fallback_trigger,
            "selected_screen_ref": full_screen_ref,
            "selected_shard_refs": full_shard_refs,
            "full_grid_validation_ref": full_validation_ref,
        }

    final_payload = _power_payload("final")
    bind_power(final_payload, phase=selected_phase)
    final_payload["generation"] = selected_generation
    final_payload["parent_refs"] = attempt_refs
    final_payload["all_attempt_refs"] = attempt_refs
    final_payload["finalization"] = finalization
    _write_test_record(
        root,
        "power/final.json",
        "resampling_power_report",
        final_payload,
    )
    if variant == "duplicate-power-shard":
        duplicate = deepcopy(gaussian_shard_payloads[1])
        _write_test_record(
            root,
            "power/gaussian-shard-duplicate.json",
            "resampling_power_report",
            duplicate,
        )
    return {
        "raws": raws,
        "task_parent_refs": task_parent_refs,
        "manifest_ref": manifest_ref,
    }


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
            approximation_receipt={
                "max_absolute_gate_pass_rate_difference": 0.01,
                "gaussian_tier_decision": "C160",
                "full_multiplier_tier_decision": "C160",
                "tier_decision_unchanged": True,
                "passed": True,
            },
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_absolute_gate_pass_rate_difference", 0.0100001),
        ("full_multiplier_tier_decision", "C120"),
        ("tier_decision_unchanged", False),
        ("passed", False),
    ],
)
def test_gaussian_validation_receipt_enforces_frozen_acceptance_gate(
    field: str,
    value: object,
) -> None:
    payload = _power_payload("validation")
    validate_record(_record("resampling_power_report", payload))
    payload["approximation_receipt"][field] = value  # type: ignore[index]
    with pytest.raises(RecordValidationError, match="(?i)approximation"):
        validate_record(_record("resampling_power_report", payload))


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
        json.dumps(FROZEN_UPSTREAM_KINDS),
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
    built = _build_full_study(root)
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    root_record = load_record(root / receipt.relative_path)
    paths = [entry["relative_path"] for entry in root_record["payload"]["entries"]]  # type: ignore[index]
    assert paths == sorted(paths)
    assert "p0-core-receipt.json" not in paths
    assert "raw/shared.bin" in paths
    verify_artifact_root(
        root / "p0-core-receipt.json",
        root,
        required_document_kinds=FROZEN_UPSTREAM_KINDS,
    )
    shared_ref = built["raws"]["shared"]  # type: ignore[index]
    (root / cast(str, shared_ref["relative_path"])).write_bytes(b"changed")
    with pytest.raises(RecordValidationError):
        verify_artifact_root(
            root / "p0-core-receipt.json",
            root,
            required_document_kinds=FROZEN_UPSTREAM_KINDS,
        )


@pytest.mark.parametrize(
    ("variant", "message"),
    [
        ("dangling-ref", "dangling"),
        ("conflicting-ref", "conflicting"),
    ],
)
def test_artifact_root_rejects_dangling_and_conflicting_refs(
    tmp_path: Path,
    variant: str,
    message: str,
) -> None:
    root = tmp_path / variant
    _build_full_study(root, variant=variant)
    with pytest.raises(RecordValidationError, match=message):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
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
    payload["terminal_slot_receipts"] = deepcopy(terminal_receipts)
    payload["execution_receipts"] = [
        {
            "source_receipt_sha256": canonical_digest(terminal_receipts[index]),
            "source_kind": "graded_unscored",
            "grade_receipt": {
                "success": 0,
                "partial_reward": 0.0,
                "infrastructure_failure": False,
                "artifact_ref": _ref(f"grades/{index}.json"),
            },
            "outcome": deepcopy(payload["slot_outcomes"][index]),  # type: ignore[index]
        }
        for index in range(4)
    ]
    return payload


@pytest.mark.parametrize(
    "mutation",
    [
        "selected-terminal",
        "source-digest",
        "execution-outcome",
        "slot-identity",
    ],
)
def test_triggered_task_block_rejects_frankenstein_causal_chains(
    mutation: str,
) -> None:
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
    payload = _triggered_task_block_payload(refs)
    validate_record(_record("resampling_task_block", payload))

    if mutation == "selected-terminal":
        payload["attempts"][0]["terminal_receipts"][0][  # type: ignore[index]
            "pre_injection_visible_sha256"
        ] = SHA_B
    elif mutation == "source-digest":
        payload["execution_receipts"][0]["source_receipt_sha256"] = SHA_A  # type: ignore[index]
    elif mutation == "execution-outcome":
        payload["execution_receipts"][0]["outcome"]["success"] = 1  # type: ignore[index]
    else:
        payload["terminal_slot_receipts"][0][  # type: ignore[index]
            "opaque_capability_id"
        ] = "opaque-frankenstein"

    with pytest.raises(RecordValidationError, match="(?i)(causal|receipt|outcome|slot)"):
        validate_record(_record("resampling_task_block", payload))


def _outage_task_block_payload(
    refs: dict[str, dict[str, object]],
) -> dict[str, object]:
    payload = _triggered_task_block_payload(refs)
    second_attempt = deepcopy(payload["attempts"][0])  # type: ignore[index]
    second_attempt["attempt_index"] = 1
    second_attempt["attempt_ref"] = _ref("attempts/attempt-1.json")
    first_attempt = deepcopy(payload["attempts"][0])  # type: ignore[index]
    first_attempt["terminal_receipts"] = first_attempt["terminal_receipts"][:2]
    first_attempt["complete"] = False
    payload["attempts"] = [first_attempt, second_attempt]
    payload["selected_attempt_index"] = 1
    payload["terminal_slot_receipts"] = deepcopy(
        second_attempt["terminal_receipts"]
    )
    payload["execution_receipts"] = [
        {
            **deepcopy(receipt),
            "source_receipt_sha256": canonical_digest(
                second_attempt["terminal_receipts"][index]
            ),
        }
        for index, receipt in enumerate(payload["execution_receipts"])  # type: ignore[arg-type]
    ]
    payload["outage_receipt"] = {
        "task_id": "task-1",
        "provider_event_ref": _ref("events/provider-outage.json"),
        "first_attempt": deepcopy(first_attempt),
        "detected_before_endpoint_readable": True,
        "work_order_sha256s": deepcopy(first_attempt["work_order_sha256s"]),
        "rerun_index": 1,
    }
    return payload


@pytest.mark.parametrize(
    "mutation",
    [
        "first-attempt",
        "work-orders",
        "task-id",
        "first-attempt-slot",
        "first-attempt-capability",
        "rerun-work-orders",
    ],
)
def test_outage_receipt_is_bound_to_the_actual_first_attempt(
    mutation: str,
) -> None:
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
    payload = _outage_task_block_payload(refs)
    validate_record(_record("resampling_task_block", payload))
    outage = payload["outage_receipt"]  # type: ignore[assignment]
    if mutation == "first-attempt":
        outage["first_attempt"]["terminal_receipts"] = []  # type: ignore[index]
    elif mutation == "work-orders":
        outage["work_order_sha256s"][0] = SHA_A  # type: ignore[index]
    elif mutation == "task-id":
        outage["task_id"] = "task-frankenstein"  # type: ignore[index]
    elif mutation == "first-attempt-slot":
        payload["attempts"][0]["terminal_receipts"][0]["slot_id"] = "slot-x"  # type: ignore[index]
        outage["first_attempt"] = deepcopy(payload["attempts"][0])  # type: ignore[index]
    elif mutation == "first-attempt-capability":
        payload["attempts"][0]["terminal_receipts"][0][  # type: ignore[index]
            "opaque_capability_id"
        ] = "opaque-x"
        outage["first_attempt"] = deepcopy(payload["attempts"][0])  # type: ignore[index]
    else:
        payload["attempts"][0]["work_order_sha256s"][0] = SHA_A  # type: ignore[index]
        outage["first_attempt"] = deepcopy(payload["attempts"][0])  # type: ignore[index]
        outage["work_order_sha256s"] = deepcopy(  # type: ignore[index]
            payload["attempts"][0]["work_order_sha256s"]  # type: ignore[index]
        )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(outage|attempt|slot|work.order)",
    ):
        validate_record(_record("resampling_task_block", payload))


def test_artifact_root_requires_exact_roster_unique_task_blocks(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    _build_full_study(root)
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()

    (root / receipt.relative_path).unlink()
    other = tmp_path / "extra-task"
    _build_full_study(other, variant="extra-task")
    with pytest.raises(RecordValidationError, match="cover the roster"):
        seal_artifact_root(
            other,
            FROZEN_UPSTREAM_KINDS,
            other / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_artifact_root_document_coverage_and_power_identities(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing"
    _build_full_study(
        missing_root,
        omit_kind="resampling_analysis",
    )
    with pytest.raises(RecordValidationError, match="missing"):
        seal_artifact_root(
            missing_root,
            FROZEN_UPSTREAM_KINDS,
            missing_root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )

    root = tmp_path / "valid"
    _build_full_study(root)
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()

    duplicate_root = tmp_path / "duplicate"
    _build_full_study(duplicate_root, variant="duplicate-power-shard")
    with pytest.raises(RecordValidationError, match="duplicate|zero-based"):
        seal_artifact_root(
            duplicate_root,
            FROZEN_UPSTREAM_KINDS,
            duplicate_root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


@pytest.mark.parametrize(
    "variant",
    [
        "schedule-assignment-program",
        "schedule-provider-lane",
        "prefix-schedule-hash",
        "prefix-verifier-schedule-hash",
        "assignment-schedule-hash",
        "assignment-prefix-hash",
        "packet-tokenizer",
        "sealed-packet-policy",
        "analysis-config",
        "power-common-grid",
    ],
)
def test_artifact_root_rejects_frankenstein_scientific_ancestry(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / variant
    _build_full_study(root, variant=variant)
    with pytest.raises(RecordValidationError, match="(?i)(ancestry|ref|hash|source)"):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


@pytest.mark.parametrize(
    "variant",
    [
        "power-shard-parent",
        "power-shard-gap",
        "power-shard-count",
        "power-cell-gap",
        "power-cell-overlap",
        "power-selection-parent",
        "power-validation-parent",
        "power-finalization-shard-gap",
    ],
)
def test_power_chain_rejects_incomplete_or_frankenstein_topology(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / variant
    _build_full_study(root, variant=variant)
    with pytest.raises(
        RecordValidationError,
        match="(?i)(power|parent|shard|cell|coverage)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_full_multiplier_fallback_requires_terminal_failed_gaussian_validation(
    tmp_path: Path,
) -> None:
    valid_root = tmp_path / "fallback-valid"
    _build_full_study(valid_root, fallback=True)
    receipt = seal_artifact_root(
        valid_root,
        FROZEN_UPSTREAM_KINDS,
        valid_root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (valid_root / receipt.relative_path).is_file()

    invalid_root = tmp_path / "fallback-screen-trigger"
    _build_full_study(
        invalid_root,
        variant="fallback-trigger-screen",
        fallback=True,
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(fallback|Gaussian|validation)",
    ):
        seal_artifact_root(
            invalid_root,
            FROZEN_UPSTREAM_KINDS,
            invalid_root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )
