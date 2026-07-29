"""Contract tests for resampling-null schemas and canonical artifact IO."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, cast
import unicodedata

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab import schemas as pls
from pneuma_lab.resampling_null.artifacts import (
    SCHEMA_BY_KIND,
    RecordValidationError,
    canonical_digest,
    canonical_json_bytes,
    load_record,
    seal_artifact_root,
    seal_study_manifest,
    validate_record,
    verify_artifact_root,
    verify_digest_link,
    write_jsonl_artifact,
    write_record,
)
from pneuma_lab.resampling_null.assignment import (
    BytesField,
    U64Field,
    commitment_sha256,
    require_schedulable_power_final,
)
from pneuma_lab.resampling_null.branch_assignment import seal_branch_assignment
from pneuma_lab.resampling_null.execution_authority import (
    load_prefix_execution_authority,
)
from pneuma_lab.resampling_null.packets import (
    IdentifierAtom,
    IdentifierKind,
    NoInterventionPacketMarker,
    PacketInvalid,
    SyntheticPacketArtifactStore,
    audit_and_seal_packet_index,
    build_packet_pair,
    derive_packet_rewrite_artifacts,
    normalize_synthetic_packet_findings,
    write_packet_candidate,
)
from pneuma_lab.resampling_null.assignment_verification import (
    _require_assignment_publication,
    require_assignment_reconstruction,
    require_confirmation_assignment,
    verify_synthetic_assignment_graph,
)
from pneuma_lab.resampling_null.schedule import seal_prefix_schedule
from pneuma_lab.resampling_null.secrets import AssignmentSecretStore
from pneuma_lab.resampling_null.storage import (
    ConfirmationStorageLease,
    LocalTestStorageLease,
    claim_local_test_storage,
    _publish_local_test_scientific,
)
from pneuma_lab.resampling_null.types import ArtifactRef, CallContractCaps
from tests.resampling_null.provider_authority_fixture import (
    ProviderAuthorityFixture,
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


def _minimal_prefix_task_receipt() -> dict[str, object]:
    def controller_ref(role: str) -> dict[str, object]:
        return _ref(
            f"controller-artifacts/{role}/{SHA_A}",
            role=role,
            media_type=(
                "application/octet-stream"
                if role in {"grade_evidence", "verifier_evidence"}
                else "application/json"
            ),
        )

    return {
        "task_id": "task-1",
        "schedule_sha256": SHA_A,
        "prefix_caps": {
            "generated_tokens": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "snapshot_ref": controller_ref("composite_snapshot"),
        "visible_context_ref": controller_ref("visible_context"),
        "visible_sha256": SHA_A,
        "token_ids_ref": controller_ref("token_ids"),
        "token_ids_sha256": SHA_A,
        "branch_pending_calls": [],
        "terminal_unexecuted_remainder": [],
        "trigger_reason": "no_intervention_opportunity",
        "terminal_failure_kind": "none",
        "y0_grade": {
            "success": 0,
            "partial_reward": 0.0,
            "infrastructure_failure": False,
            "artifact_ref": controller_ref("grade_evidence"),
        },
        "grade_execution_receipt_ref": controller_ref("grade_evidence_receipt"),
        "verifier_receipt": {
            "task_id": "task-1",
            "schedule_sha256": SHA_A,
            "snapshot_ref": controller_ref("composite_snapshot"),
            "verifier_artifact_ref": controller_ref("verifier_evidence"),
            "finding_count": 0,
        },
        "verifier_execution_receipt_ref": controller_ref("verifier_evidence_receipt"),
        "counters": {
            "generated_tokens": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "simulator_counters": {
            "generated_tokens": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "call_seeds": [],
        "provider_attempts_ref": controller_ref("provider_attempt_ledger"),
        "boundary_ledger_ref": controller_ref("tool_boundary_ledger"),
        "provider_cost_ref": controller_ref("provider_cost_closure"),
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
            "eligibility_manifest_ref": None,
            "roster_ceremony_policy_ref": None,
            "assignment_program_ref": _ref("sources/assignment.py"),
            "provider_lane_plan_ref": _ref("sources/provider.json"),
            "storage_policy_contract_ref": _ref("sources/storage-policy.json"),
            "power_grid_ref": _ref("sources/power-grid.json"),
            "power_screen_topology_ref": _ref("sources/power-screen-topology.json"),
            "tokenizer_ref": _ref("sources/tokenizer.json"),
            "packet_template_ref": _ref("sources/template.json"),
            "packet_policy_ref": _ref("sources/policy.json"),
            "pad_unit_set_ref": _ref("sources/pads.json"),
            "source_revision_refs": [_ref("sources/revisions/design.md")],
            "commitment_scheme": "resampling-null-key-ceremony-v1",
            "roster_local_nonce_commitment_sha256": SHA_A,
            "schedule_seed_commitment_sha256": SHA_A,
            "assignment_master_key_commitment_sha256": SHA_A,
            "required_document_kinds_ref": _ref("sources/required.json"),
        },
        "resampling_prefix_schedule": {
            "manifest_ref": refs["manifest_ref"],
            "power_final_ref": _ref("parents/power-final.json", role="power_final"),
            "schedule_authority": "synthetic_validation",
            "selected_tier": None,
            "selected_membership_sha256": SHA_A,
            "schedule_seed": 7,
            "tasks": [
                {
                    "task": {
                        "task_id": "task-1",
                        "benchmark": "swe",
                        "stratum": "python",
                        "lineage": "repo-1",
                        "sensitivity_groups": [{"kind": "language", "value": "python"}],
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
            "task_receipts": [_minimal_prefix_task_receipt()],
        },
        "resampling_assignment_ledger": _t3_s02_no_trigger_assignment_payload(),
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
        "resampling_power_report": _power_payload("screen"),
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
    return cast(dict[str, object], asdict(cast(Any, value)))


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


def _t3_s02_manifest_payload() -> dict[str, object]:
    return deepcopy(_minimal_payload("resampling_study_manifest"))


def _t3_s02_schedule_payload() -> dict[str, object]:
    return deepcopy(_minimal_payload("resampling_prefix_schedule"))


def _t3_s02_no_trigger_assignment_payload() -> dict[str, object]:
    matching_program_ref = _ref(
        "sources/assignment-program.json",
        role="matching_program",
    )
    return {
        "manifest_ref": _ref("parents/manifest.json", role="manifest"),
        "schedule_ref": _ref("parents/schedule.json", role="schedule"),
        "prefix_index_ref": _ref("parents/prefix-index.json", role="prefix_index"),
        "matching_program_ref": matching_program_ref,
        "assignment_master_key_commitment_sha256": SHA_A,
        "assignment_prefix_view_sha256": SHA_B,
        "assignment_mode": "synthetic_derangement",
        "matching_proof_refs": [],
        "assignments": [
            {
                "task_id": "task-1",
                "task_lineage": "repo-1",
                "donor_match_kind": "not_applicable_no_trigger",
                "donor_task_id": None,
                "donor_lineage": None,
                "slot_arms": [
                    ["slot-0", "REAL"],
                    ["slot-1", "SHAM"],
                    ["slot-2", "NONE"],
                    ["slot-3", "RESAMPLE"],
                ],
                "schedule_sha256": SHA_A,
                "prefix_index_sha256": SHA_B,
            }
        ],
        "allocation_receipts": [
            {
                "task_id": "task-1",
                "slot_ids_by_ordinal": [
                    "slot-0",
                    "slot-1",
                    "slot-2",
                    "slot-3",
                ],
                "treatment_allocation_index": 0,
                "allocation_rejection_counter": 0,
                "no_packet_orientation_bit": 0,
                "orientation_rejection_counter": 0,
                "slot_capabilities": [
                    [
                        f"slot-{index}",
                        hashlib.sha256(f"cap-{index}".encode()).hexdigest(),
                    ]
                    for index in range(4)
                ],
            }
        ],
        "donor_match_receipts": [
            {
                "kind": "not_applicable_no_trigger",
                "task_id": "task-1",
                "trigger_reason": "no_intervention_opportunity",
                "assignment_prefix_view_sha256": SHA_B,
            }
        ],
    }


def _t3_s02_matched_assignment_payload() -> dict[str, object]:
    payload = _t3_s02_no_trigger_assignment_payload()
    proof_ref = _ref(
        f"blobs/matching/proof/{SHA_A}.json",
        role="matching_proof",
    )
    assignment = cast(
        list[dict[str, object]],
        payload["assignments"],
    )[0]
    assignment.update(
        {
            "donor_match_kind": "matched",
            "donor_task_id": "task-2",
            "donor_lineage": "repo-2",
        }
    )
    payload["matching_proof_refs"] = [proof_ref]
    payload["donor_match_receipts"] = [
        {
            "kind": "matched",
            "task_id": "task-1",
            "donor_task_id": "task-2",
            "task_lineage": "repo-1",
            "donor_lineage": "repo-2",
            "assignment_mode": "synthetic_derangement",
            "matching_algorithm": "synthetic_cyclic_offset_v1",
            "stratum_key": ["swe", "python"],
            "assignment_prefix_view_sha256": SHA_B,
            "candidates": [
                {
                    "donor_task_id": "task-2",
                    "donor_lineage": "repo-2",
                    "primary_cost": [0, 0, 0],
                    "fallback_code": None,
                    "tie_hmac_sha256": SHA_A,
                }
            ],
            "chosen_primary_cost": [0, 0, 0],
            "matching_proof_ref": proof_ref,
        }
    ]
    return payload


def test_t3_s02_manifest_uses_three_named_ceremony_commitments() -> None:
    payload = _t3_s02_manifest_payload()
    assert validate_record(_record("resampling_study_manifest", payload))

    legacy = deepcopy(payload)
    del legacy["commitment_scheme"]
    del legacy["roster_local_nonce_commitment_sha256"]
    del legacy["schedule_seed_commitment_sha256"]
    del legacy["assignment_master_key_commitment_sha256"]
    legacy["seed_commitment_sha256"] = SHA_A
    with pytest.raises(RecordValidationError):
        validate_record(_record("resampling_study_manifest", legacy))

    for field in (
        "roster_local_nonce_commitment_sha256",
        "schedule_seed_commitment_sha256",
        "assignment_master_key_commitment_sha256",
    ):
        missing = deepcopy(payload)
        del missing[field]
        with pytest.raises(RecordValidationError, match=field):
            validate_record(_record("resampling_study_manifest", missing))


def test_t3_s02_manifest_conditional_refs_are_paired() -> None:
    payload = _t3_s02_manifest_payload()
    payload["eligibility_manifest_ref"] = _ref("sources/eligibility.json")
    payload["roster_ceremony_policy_ref"] = _ref("sources/roster-ceremony-policy.json")
    assert validate_record(_record("resampling_study_manifest", payload))

    for field in (
        "eligibility_manifest_ref",
        "roster_ceremony_policy_ref",
    ):
        unpaired = deepcopy(payload)
        unpaired[field] = None
        with pytest.raises(RecordValidationError, match=field):
            validate_record(_record("resampling_study_manifest", unpaired))


def test_t3_s02_schedule_loads_assignment_inputs_only_via_manifest() -> None:
    payload = _t3_s02_schedule_payload()
    assert validate_record(_record("resampling_prefix_schedule", payload))

    empty = deepcopy(payload)
    empty["tasks"] = []
    with pytest.raises(RecordValidationError, match="tasks"):
        validate_record(_record("resampling_prefix_schedule", empty))

    for forbidden in ("assignment_program_ref", "provider_lane_plan_ref"):
        contaminated = deepcopy(payload)
        contaminated[forbidden] = _ref(f"forbidden/{forbidden}.json")
        with pytest.raises(RecordValidationError):
            validate_record(_record("resampling_prefix_schedule", contaminated))


def test_t3_s02_prefix_receipts_are_nonempty() -> None:
    payload = _minimal_payload("resampling_prefix_receipt")
    payload["task_receipts"] = []
    with pytest.raises(RecordValidationError, match="task_receipts"):
        validate_record(_record("resampling_prefix_receipt", payload))


@pytest.mark.parametrize(
    "variant",
    [
        "both_queues",
        "branch_timeout",
        "duplicate_role_index",
        "nonconsecutive_role_index",
        "unequal_walls",
        "simulator_tools",
        "adverse_nonzero_y0",
        "wrong_snapshot_role",
        "verifier_ancestry",
        "duplicate_queue_call_id",
    ],
)
def test_t5_s02b_prefix_semantics_fail_closed(variant: str) -> None:
    payload = _minimal_payload("resampling_prefix_receipt")
    receipt = cast(list[dict[str, object]], payload["task_receipts"])[0]
    if variant == "both_queues":
        call = {
            "call_id": "call-1",
            "name": "read",
            "canonical_arguments_json": "{}\n",
        }
        receipt["branch_pending_calls"] = [call]
        receipt["terminal_unexecuted_remainder"] = [call]
    elif variant == "branch_timeout":
        receipt["trigger_reason"] = "first_eligible_mutation"
        receipt["terminal_failure_kind"] = "timeout"
    elif variant == "duplicate_role_index":
        receipt["call_seeds"] = [
            {"subject_role": "primary_subject", "call_index": 0, "seed": 1},
            {"subject_role": "primary_subject", "call_index": 0, "seed": 2},
        ]
    elif variant == "nonconsecutive_role_index":
        receipt["call_seeds"] = [
            {"subject_role": "primary_subject", "call_index": 1, "seed": 1},
        ]
    elif variant == "unequal_walls":
        receipt["simulator_counters"]["wall_clock_ms"] = 1  # type: ignore[index]
    elif variant == "simulator_tools":
        receipt["simulator_counters"]["tool_calls"] = 1  # type: ignore[index]
    elif variant == "adverse_nonzero_y0":
        receipt["terminal_failure_kind"] = "timeout"
        receipt["y0_grade"]["success"] = 1  # type: ignore[index]
    elif variant == "verifier_ancestry":
        receipt["verifier_receipt"]["task_id"] = "other-task"  # type: ignore[index]
    elif variant == "duplicate_queue_call_id":
        call = {
            "call_id": "call-1",
            "name": "read",
            "canonical_arguments_json": "{}\n",
        }
        receipt["branch_pending_calls"] = [call, {**call, "name": "write"}]
        receipt["trigger_reason"] = "first_eligible_mutation"
    else:
        receipt["snapshot_ref"]["role"] = "wrong"  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(_record("resampling_prefix_receipt", payload))


@pytest.mark.parametrize(
    "variant",
    [
        "noncanonical_tool_arguments",
        "successful_infrastructure_failure",
        "task_schedule_drift",
        "verifier_schedule_drift",
    ],
)
def test_t5_s02b_prefix_runtime_records_and_schedule_are_exact(variant: str) -> None:
    payload = _minimal_payload("resampling_prefix_receipt")
    receipt = cast(list[dict[str, object]], payload["task_receipts"])[0]
    if variant == "noncanonical_tool_arguments":
        receipt["branch_pending_calls"] = [
            {
                "call_id": "call-1",
                "name": "read",
                "canonical_arguments_json": "not-json",
            }
        ]
        receipt["trigger_reason"] = "first_eligible_mutation"
    elif variant == "successful_infrastructure_failure":
        grade = cast(dict[str, object], receipt["y0_grade"])
        grade["success"] = 1
        grade["infrastructure_failure"] = True
    elif variant == "task_schedule_drift":
        receipt["schedule_sha256"] = SHA_B
        verifier = cast(dict[str, object], receipt["verifier_receipt"])
        verifier["schedule_sha256"] = SHA_B
    else:
        verifier = cast(dict[str, object], receipt["verifier_receipt"])
        verifier["schedule_sha256"] = SHA_B
    with pytest.raises(RecordValidationError):
        validate_record(_record("resampling_prefix_receipt", payload))


@pytest.mark.parametrize("surface", ["schema", "custom"])
def test_t5_s02b_prefix_media_type_rejects_whitespace(surface: str) -> None:
    record = _record(
        "resampling_prefix_receipt",
        _minimal_payload("resampling_prefix_receipt"),
    )
    receipt = cast(list[dict[str, object]], record["payload"]["task_receipts"])[0]  # type: ignore[index]
    snapshot_ref = cast(dict[str, object], receipt["snapshot_ref"])
    snapshot_ref["media_type"] = " application/json"
    if surface == "schema":
        schema = pls.load_schema("resampling-prefix-receipt.schema.json")
        errors = list(Draft202012Validator(schema).iter_errors(record))
        assert errors
    else:
        with pytest.raises(RecordValidationError):
            validate_record(record)


def test_t3_s02_assignment_accepts_closed_no_trigger_arm() -> None:
    payload = _t3_s02_no_trigger_assignment_payload()
    assert validate_record(_record("resampling_assignment_ledger", payload))

    assignment = cast(list[dict[str, object]], payload["assignments"])[0]
    assignment["donor_task_id"] = "task-2"
    with pytest.raises(RecordValidationError):
        validate_record(_record("resampling_assignment_ledger", payload))


@pytest.mark.parametrize(
    "field",
    ["assignments", "allocation_receipts", "donor_match_receipts"],
)
def test_t3_s02_assignment_arrays_are_nonempty(field: str) -> None:
    payload = _t3_s02_no_trigger_assignment_payload()
    payload[field] = []
    with pytest.raises(RecordValidationError, match=field):
        validate_record(_record("resampling_assignment_ledger", payload))


def test_t3_s02_assignment_matching_proofs_are_conditional_and_unique() -> None:
    payload = _t3_s02_matched_assignment_payload()
    assert validate_record(_record("resampling_assignment_ledger", payload))

    no_proof = deepcopy(payload)
    no_proof["matching_proof_refs"] = []
    with pytest.raises(RecordValidationError, match="matching_proof"):
        validate_record(_record("resampling_assignment_ledger", no_proof))

    duplicated = deepcopy(payload)
    duplicated["matching_proof_refs"] *= 2  # type: ignore[operator]
    with pytest.raises(RecordValidationError, match="matching_proof"):
        validate_record(_record("resampling_assignment_ledger", duplicated))

    wrong_algorithm = deepcopy(payload)
    donor_receipt = cast(
        list[dict[str, object]],
        wrong_algorithm["donor_match_receipts"],
    )[0]
    donor_receipt["matching_algorithm"] = "exact_constrained_min_cost_v1"
    with pytest.raises(RecordValidationError, match="matching_algorithm"):
        validate_record(_record("resampling_assignment_ledger", wrong_algorithm))


def test_t3_s02_stratum_key_is_an_ordered_tuple_not_a_set() -> None:
    payload = _t3_s02_matched_assignment_payload()
    donor_receipt = cast(
        list[dict[str, object]],
        payload["donor_match_receipts"],
    )[0]
    donor_receipt["stratum_key"] = ["python", "python"]
    assert validate_record(_record("resampling_assignment_ledger", payload))


def test_t3_s02_assignment_arrays_share_one_task_order() -> None:
    payload = _t3_s02_no_trigger_assignment_payload()
    assignment = deepcopy(cast(list[dict[str, object]], payload["assignments"])[0])
    assignment.update(
        {
            "task_id": "task-2",
            "task_lineage": "repo-2",
            "slot_arms": [
                [f"task-2-slot-{index}", arm]
                for index, arm in enumerate(("REAL", "SHAM", "NONE", "RESAMPLE"))
            ],
        }
    )
    cast(list[dict[str, object]], payload["assignments"]).append(assignment)

    allocation = deepcopy(
        cast(list[dict[str, object]], payload["allocation_receipts"])[0]
    )
    allocation["task_id"] = "task-2"
    allocation["slot_ids_by_ordinal"] = [f"task-2-slot-{index}" for index in range(4)]
    allocation["slot_capabilities"] = [
        [
            f"task-2-slot-{index}",
            hashlib.sha256(f"task-2-cap-{index}".encode()).hexdigest(),
        ]
        for index in range(4)
    ]
    cast(
        list[dict[str, object]],
        payload["allocation_receipts"],
    ).append(allocation)

    donor_receipt = deepcopy(
        cast(list[dict[str, object]], payload["donor_match_receipts"])[0]
    )
    donor_receipt["task_id"] = "task-2"
    cast(
        list[dict[str, object]],
        payload["donor_match_receipts"],
    ).append(donor_receipt)
    assert validate_record(_record("resampling_assignment_ledger", payload))

    reordered = deepcopy(payload)
    cast(
        list[dict[str, object]],
        reordered["donor_match_receipts"],
    ).reverse()
    with pytest.raises(RecordValidationError, match="order"):
        validate_record(_record("resampling_assignment_ledger", reordered))


def test_t3_s02_matched_candidate_rows_are_nonempty() -> None:
    payload = _t3_s02_matched_assignment_payload()
    donor_receipt = cast(
        list[dict[str, object]],
        payload["donor_match_receipts"],
    )[0]
    donor_receipt["candidates"] = []
    with pytest.raises(RecordValidationError, match="candidates"):
        validate_record(_record("resampling_assignment_ledger", payload))


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
    value = _record(
        "resampling_study_manifest", _minimal_payload("resampling_study_manifest")
    )
    value["record_kind"] = bad_kind
    with pytest.raises(RecordValidationError, match="record_kind"):
        validate_record(value)


def test_unknown_properties_and_malformed_digests_fail_closed() -> None:
    value = _record(
        "resampling_study_manifest", _minimal_payload("resampling_study_manifest")
    )
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
    packet = _record(
        "resampling_packet_index", _minimal_payload("resampling_packet_index")
    )
    packet["payload"]["stage"] = "draft"  # type: ignore[index]
    with pytest.raises(RecordValidationError):
        validate_record(packet)
    packet = _record(
        "resampling_packet_index", _minimal_payload("resampling_packet_index")
    )
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
        "selected_kernel_id": "power-final-gaussian-v1",
        "selected_shard_count": 2,
        "selected_screen_ref": attempts[0],  # type: ignore[index]
        "selected_shard_refs": [attempts[1]],  # type: ignore[index]
        "selected_selection_ref": attempts[2],  # type: ignore[index]
        "selected_validation_ref": attempts[3],  # type: ignore[index]
        "selected_tier": None,
        "decision": "CONDITIONAL_ONLY",
    }
    validate_record(_record("resampling_power_report", completed))
    full_validation = _power_payload(
        "validation",
        phase="full_multiplier_fallback",
    )
    validate_record(_record("resampling_power_report", full_validation))
    full_completed = _power_payload(
        "final",
        phase="full_multiplier_fallback",
    )
    full_completed["generation"] = 1
    full_completed["parent_refs"] = full_completed["all_attempt_refs"]
    full_completed["finalization"] = {
        "kind": "completed_chain",
        "selected_phase": "full_multiplier_fallback",
        "selected_generation": 1,
        "selected_kernel_id": "power-final-full-multiplier-v1",
        "selected_shard_count": 2,
        "fallback_trigger_ref": _ref("power/gaussian-trigger.json"),
        "selected_screen_ref": _ref("power/full-screen.json"),
        "selected_shard_refs": [_ref("power/full-shard.json")],
        "full_grid_validation_ref": _ref("power/full-validation.json"),
        "selected_tier": None,
        "decision": "CONDITIONAL_ONLY",
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


def _replace_test_record(
    root: Path,
    relative_path: str,
    mutate_payload: Callable[[dict[str, object]], None],
) -> dict[str, object]:
    path = root / relative_path
    record = load_record(path)
    payload = cast(dict[str, object], record["payload"])
    mutate_payload(payload)
    kind = cast(str, record["record_kind"])
    path.unlink()
    return _artifact_mapping(
        write_record(
            path,
            record,
            run_root=root,
            role=kind,
        )
    )


def _force_replace_test_record(
    root: Path,
    relative_path: str,
    mutate_payload: Callable[[dict[str, object]], None],
) -> dict[str, object]:
    path = root / relative_path
    record = load_record(path)
    payload = cast(dict[str, object], record["payload"])
    mutate_payload(payload)
    validated = validate_record(record)
    encoded = canonical_json_bytes(validated, indent=2)
    path.write_bytes(encoded)
    return _ref(
        relative_path,
        role=cast(str, record["record_kind"]),
        sha256=hashlib.sha256(encoded).hexdigest(),
        byte_count=len(encoded),
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
    no_go_stage: str | None = None,
    no_go_mutation: str | None = None,
    no_go_reason: str | None = None,
    packet_pair: bool = False,
    decision_authority: str = "synthetic_validation",
    verdict_mutation: str | None = None,
    failed_second_task: bool = False,
    earlier_power_partial: bool = False,
    later_power_partial: bool = False,
    full_gate_failure: bool = False,
    retry_after_terminal: str | None = None,
    completed_power_consumer_fixture: bool = False,
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
        subtree = "sources" if completed_power_consumer_fixture else "raw"
        return _write_blob(root, f"{subtree}/{name}", payload)

    def controller_raw(role: str, label: str | None = None) -> dict[str, object]:
        media_types = {
            "composite_snapshot": "application/json",
            "grade_evidence": "application/octet-stream",
            "grade_evidence_receipt": "application/json",
            "provider_attempt_ledger": "application/json",
            "provider_cost_closure": "application/json",
            "token_ids": "application/json",
            "tool_boundary_ledger": "application/json",
            "verifier_evidence": "application/octet-stream",
            "verifier_evidence_receipt": "application/json",
            "visible_context": "application/json",
        }
        if role not in media_types:
            raise AssertionError(f"unregistered controller fixture role: {role!r}")
        payload = f"{role}-{label or 'fixture'}".encode()
        digest = hashlib.sha256(payload).hexdigest()
        ref = _write_blob(
            root,
            f"controller-artifacts/{role}/{digest}",
            payload,
        )
        ref["role"] = role
        ref["media_type"] = media_types[role]
        return ref

    if completed_power_consumer_fixture:
        roster_size = 2 if decision_authority == "synthetic_validation" else 160
        task_ids = ["task-1", "task-donor"] + [
            f"task-{index:03d}" for index in range(2, roster_size)
        ]
        roster_tasks = [
            {
                "task_id": task_id,
                "benchmark": "swe",
                "stratum": "python",
                "lineage": f"repo-{index:03d}",
                "groups": [
                    {"kind": "language", "value": "python"},
                    {"kind": "domain", "value": "software"},
                    {"kind": "issue_family", "value": "bug"},
                ],
                "tiers": ([120, 160] if index < 120 else [160]),
            }
            for index, task_id in enumerate(task_ids)
        ]
        registry_tasks = [
            {key: value for key, value in task.items() if key != "tiers"}
            for task in roster_tasks
        ]
    else:
        roster_tasks = [
            {"task_id": "task-1"},
            {"task_id": "task-donor"},
        ]
        if variant == "schedule-roster-subset":
            roster_tasks.append({"task_id": "task-uncovered"})
        registry_tasks = roster_tasks
    normalizer_ref = raw(
        "normalizer.py",
        (
            {
                "record_kind": "synthetic_assignment_normalizer_v1",
                "schema_version": "1",
                "algorithm": "closed_fixture_components_v1",
            }
            if completed_power_consumer_fixture
            else b"normalizer"
        ),
    )
    tokenizer_ref = raw(
        "tokenizer.json",
        (
            canonical_json_bytes(
                {
                    "record_kind": "synthetic_report_tokenizer_v1",
                    "schema_version": "1",
                    "algorithm": "unicode_whitespace_v1",
                },
                indent=None,
            )
            if completed_power_consumer_fixture
            else {"name": "tokenizer"}
        ),
    )
    if completed_power_consumer_fixture:
        normalizer_ref["role"] = "source_revision"
        tokenizer_ref["role"] = "tokenizer"
        tokenizer_ref["media_type"] = "application/json"
    raws = {
        "tasks": raw(
            "tasks.json",
            (
                {
                    "record_kind": "resampling_task_registry_v1",
                    "schema_version": "1",
                    "tasks": registry_tasks,
                }
                if completed_power_consumer_fixture
                else {"tasks": roster_tasks}
            ),
        ),
        "roster": raw(
            "roster.json",
            (
                {
                    "record_kind": "resampling_roster_v1",
                    "schema_version": "1",
                    "roster_kind": (
                        "synthetic_fixture"
                        if decision_authority == "synthetic_validation"
                        else "eligible_confirmation"
                    ),
                    "supported_tiers": [120, 160],
                    "tasks": roster_tasks,
                }
                if completed_power_consumer_fixture
                else {"tasks": roster_tasks}
            ),
        ),
        "eligibility": raw(
            "eligibility.json",
            {"record_kind": "test_only_eligibility_fixture"},
        ),
        "ceremony_policy": raw(
            "ceremony-policy.json",
            {"record_kind": "test_only_ceremony_policy_fixture"},
        ),
        "power_authority": raw(
            "power-authority.json",
            {
                "authority_kind": decision_authority,
                "tier_membership_sha256": SHA_A,
            },
        ),
        "assignment": raw(
            "assignment.json",
            (
                {
                    "record_kind": "resampling_assignment_program_v1",
                    "schema_version": "1",
                    "assignment_mode": "synthetic_derangement",
                    "matching_algorithm": "synthetic_cyclic_offset_v1",
                    "finding_count_band_upper_bounds": [1, 3],
                    "report_length_band_upper_bounds": [128, 512],
                    "verifier_normalizer_contract": {
                        "contract_id": "assignment-verifier-normalizer-v1",
                        "normalizer_source_ref": normalizer_ref,
                        "normalizer_source_sha256": normalizer_ref["sha256"],
                        "report_tokenizer_sha256": tokenizer_ref["sha256"],
                        "benchmark_component_kinds": {
                            "SWE": ["check_runner", "failure_class"],
                            "TAU": ["evaluator_component"],
                        },
                    },
                    "assignment_runtime_contract": {
                        "implementation": "CPython",
                        "python_version": (
                            f"{sys.version_info.major}.{sys.version_info.minor}."
                            f"{sys.version_info.micro}"
                        ),
                        "unicodedata_unidata_version": unicodedata.unidata_version,
                    },
                    "backend_receipt_ref": None,
                    "stratum_keys": ["benchmark", "language"],
                }
                if completed_power_consumer_fixture
                else {"placeholder": "assignment"}
            ),
        ),
        "provider": raw(
            "provider.json",
            {"lane": "lane-a"},
        ),
        "storage_policy": raw(
            "storage-policy.json",
            (
                {
                    "record_kind": "storage_policy_contract_v1",
                    "schema_version": "1",
                    "mode": "local_test",
                    "test_only": True,
                    "storage_resource_id": None,
                    "measurement_evidence_ref": None,
                    "evidence_verifier_public_key_ed25519_hex": None,
                    "registry_attestation_public_key_ed25519_hex": None,
                    "max_measurement_age_seconds": None,
                    "lease_kind": "local_test_process_lock_v1",
                    "encryption_at_rest": False,
                    "encryption_algorithm": None,
                    "kms_key_version": None,
                    "acl_enforced": False,
                    "acl_policy_sha256": None,
                    "measurement_sha256": None,
                }
                if completed_power_consumer_fixture
                else {"mode": "local_test"}
            ),
        ),
        "tokenizer": tokenizer_ref,
        "template": raw(
            "template.json",
            canonical_json_bytes(
                {
                    "record_kind": "packet_template_v1",
                    "schema_version": "1",
                    "template_id": "canonical_json_private_verifier_guidance_v1",
                    "guidance_record_kind": "private_verifier_guidance_v1",
                    "field_order": [
                        "finding_id",
                        "component",
                        "code",
                        "severity",
                        "evidence",
                    ],
                },
                indent=None,
            ),
        ),
        "policy": raw(
            "policy.json",
            canonical_json_bytes(
                {
                    "record_kind": "packet_policy_v1",
                    "schema_version": "1",
                    "max_findings": 8,
                    "max_evidence_tokens": 256,
                    "normalizer_version": "synthetic_typed_findings_v1",
                },
                indent=None,
            ),
        ),
        "pads": raw(
            "pads.json",
            canonical_json_bytes(
                {
                    "record_kind": "packet_pad_units_v1",
                    "schema_version": "1",
                    "units": [" ."],
                },
                indent=None,
            ),
        ),
        "revision": raw("revision.md", b"revision"),
        "required": raw("required.json", list(FROZEN_UPSTREAM_KINDS)),
        "shared": raw("shared.bin", b"shared"),
        "composite_snapshot": controller_raw("composite_snapshot"),
        "visible_context": controller_raw("visible_context"),
        "token_ids": controller_raw("token_ids"),
        "grade_evidence_receipt": controller_raw("grade_evidence_receipt"),
        "grade_evidence": controller_raw("grade_evidence"),
        "verifier_evidence_receipt": controller_raw("verifier_evidence_receipt"),
        "focal_verifier_evidence": controller_raw(
            "verifier_evidence",
            "focal",
        ),
        "donor_verifier_evidence": controller_raw(
            "verifier_evidence",
            "donor",
        ),
        "provider_attempt_ledger": controller_raw("provider_attempt_ledger"),
        "tool_boundary_ledger": controller_raw("tool_boundary_ledger"),
        "provider_cost_closure": controller_raw("provider_cost_closure"),
        "analysis_config": raw("analysis-config.json", {"alpha": 0.05}),
        "projection_schema": raw("projection-schema.json", {"version": 1}),
        "power_grid": raw(
            "power-grid.json",
            {"cells": [{"cell_id": f"cell-{index}"} for index in range(5)]},
        ),
        "topology": raw("topology.json", {"cpu_count": 1}),
        "power_config": raw("power-config.json", {"datasets": 20_000}),
        "numeric_fixture": raw("numeric-fixture.json", {"digest": SHA_A}),
        "matching_proof": raw("matching-proof.json", {"status": "OPTIMAL"}),
        "alternate": raw("alternate.bin", b"alternate"),
        "focal_verifier": raw(
            "focal-verifier.json",
            (
                {
                    "record_kind": "synthetic_verifier_source_v1",
                    "schema_version": "1",
                    "task_id": "task-1",
                    "benchmark": "swe",
                    "components": [
                        {"kind": "check_runner", "value": "pytest", "count": 1},
                        {"kind": "failure_class", "value": "none", "count": 1},
                    ],
                    "objective_findings": [],
                }
                if completed_power_consumer_fixture
                else {"task_id": "task-1"}
            ),
        ),
        "donor_verifier": raw(
            "donor-verifier.json",
            (
                {
                    "record_kind": "synthetic_verifier_source_v1",
                    "schema_version": "1",
                    "task_id": "task-donor",
                    "benchmark": "swe",
                    "components": [
                        {"kind": "check_runner", "value": "pytest", "count": 1},
                        {"kind": "failure_class", "value": "none", "count": 1},
                    ],
                    "objective_findings": [],
                }
                if completed_power_consumer_fixture
                else {"task_id": "task-donor"}
            ),
        ),
        "report_task": raw(
            "report-task.json",
            {
                "record_kind": "synthetic_verifier_report_v1",
                "schema_version": "1",
                "task_id": "task-1",
                "report_text": "clean",
            },
        ),
        "report_donor": raw(
            "report-donor.json",
            {
                "record_kind": "synthetic_verifier_report_v1",
                "schema_version": "1",
                "task_id": "task-donor",
                "report_text": "clean",
            },
        ),
        "real_packet": raw("real-packet.bin", b"real"),
        "sham_packet": raw("sham-packet.bin", b"sham"),
        "identifier_map": raw("identifier-map.json", {}),
        "normalized_real": raw("normalized-real.bin", b"real"),
        "normalized_donor": raw("normalized-donor.bin", b"donor"),
        "normalized_sham": raw("normalized-sham.bin", b"sham"),
        "attempt_0": raw("attempt-0.json", {"attempt_index": 0}),
        "attempt_1": raw("attempt-1.json", {"attempt_index": 1}),
        "provider_event": raw("provider-event.json", {"outage": True}),
        "adverse_0": raw("adverse-0.json", {"slot_id": "slot-0"}),
        "adverse_1": raw("adverse-1.json", {"slot_id": "slot-1"}),
        "adverse_2": raw("adverse-2.json", {"slot_id": "slot-2"}),
        "adverse_3": raw("adverse-3.json", {"slot_id": "slot-3"}),
    }
    if completed_power_consumer_fixture:

        def authority_json(
            name: str,
            value: dict[str, object],
            *,
            role: str,
        ) -> dict[str, object]:
            ref = raw(name, canonical_json_bytes(value, indent=None))
            ref["role"] = role
            ref["media_type"] = "application/json"
            return ref

        raws["tasks"]["role"] = "task_registry"
        raws["tasks"]["media_type"] = "application/json"
        raws["revision"]["role"] = "source_revision"
        prompt_template_ref = authority_json(
            "authority-prompt.json",
            {"template": "synthetic-prefix-v1"},
            role="prompt_template",
        )
        tool_schema_ref = authority_json(
            "authority-tools.json",
            {"tools": []},
            role="tool_schema",
        )
        clock_source_ref = authority_json(
            "authority-clock.json",
            {"clock": "synthetic-monotonic-v1"},
            role="clock_source",
        )
        watchdog_source_ref = authority_json(
            "authority-watchdog.json",
            {"watchdog": "synthetic-deadline-v1"},
            role="watchdog_source",
        )
        qualification_ref = authority_json(
            "authority-isolation-qualification.json",
            {"qualification": "synthetic-isolation-v1"},
            role="isolation_qualification",
        )
        source_revisions = [raws["revision"]]
        aggregate_caps = {
            "generated_tokens": 40,
            "model_calls": 4,
            "turns": 4,
        }
        per_call_caps = {"generated_tokens": 12, "turns": 1}
        common_call_contract = {
            "schema_version": "1",
            "tokenizer_ref": raws["tokenizer"],
            "prompt_template_ref": prompt_template_ref,
            "tool_schema_ref": tool_schema_ref,
            "request_grammar": "synthetic-request-v1",
            "response_grammar": "synthetic-response-v1",
            "seeded_call_grammar": "call-seed-v1",
            "stateless_client_attestation": "synthetic-stateless-v1",
            "aggregate_caps": aggregate_caps,
            "per_call_caps": per_call_caps,
            "build_id": "synthetic-fixture-build",
            "source_revision_refs": source_revisions,
        }
        subject_contract_ref = authority_json(
            "subject-contract.json",
            {
                **common_call_contract,
                "record_kind": "prefix_subject_contract_v1",
                "model_id": "synthetic-subject",
                "nominal_type": "SyntheticSubject",
            },
            role="subject_contract",
        )
        parser_contract_ref = authority_json(
            "parser-contract.json",
            {
                "record_kind": "prefix_tool_parser_contract_v1",
                "schema_version": "1",
                "nominal_type": "SyntheticToolParser",
                "build_id": "synthetic-fixture-build",
                "response_grammar": "synthetic-response-v1",
                "tool_schema_ref": tool_schema_ref,
                "source_revision_refs": source_revisions,
            },
            role="tool_parser_contract",
        )
        meter_contract_ref = authority_json(
            "meter-contract.json",
            {
                "record_kind": "prefix_meter_contract_v1",
                "schema_version": "1",
                "nominal_type": "SyntheticMeter",
                "build_id": "synthetic-fixture-build",
                "clock_source_ref": clock_source_ref,
                "watchdog_source_ref": watchdog_source_ref,
                "cost_units": {
                    "currency": "usd_micros",
                    "generated_tokens": "tokens",
                    "model_calls": "calls",
                    "wall_clock": "milliseconds",
                },
                "provider_event_grammar": "synthetic-provider-event-v1",
                "settlement_grammar": "synthetic-settlement-v1",
                "zero_cost_synthetic_closure": True,
                "source_revision_refs": source_revisions,
            },
            role="meter_contract",
        )
        task_lane_rows = []
        for task in sorted(
            registry_tasks,
            key=lambda item: cast(str, item["task_id"]).encode("utf-8"),
        ):
            task_id = cast(str, task["task_id"])
            benchmark = cast(str, task["benchmark"])
            task_input_ref = authority_json(
                f"authority/{task_id}-input.json",
                {
                    "record_kind": "prefix_task_input_v1",
                    "schema_version": "1",
                    "task_id": task_id,
                    "benchmark": benchmark,
                    "requires_user_simulator": False,
                    "canonical_task_payload": {"task_id": task_id},
                },
                role="task_input",
            )
            common_task_contract = {
                "schema_version": "1",
                "task_id": task_id,
                "benchmark": benchmark,
                "build_id": "synthetic-fixture-build",
                "source_revision_refs": source_revisions,
            }
            environment_ref = authority_json(
                f"authority/{task_id}-environment.json",
                {
                    **common_task_contract,
                    "record_kind": "prefix_environment_contract_v1",
                    "nominal_factory_type": "SyntheticEnvironmentFactory",
                    "snapshot_grammar": "synthetic-snapshot-v1",
                    "restore_grammar": "synthetic-restore-v1",
                    "raw_evidence_grammar": "synthetic-environment-evidence-v1",
                    "runtime_id": "cpython-test",
                    "container_digest": "sha256:" + SHA_A,
                },
                role="environment_contract",
            )
            grader_ref = authority_json(
                f"authority/{task_id}-grader.json",
                {
                    **common_task_contract,
                    "record_kind": "prefix_grader_contract_v1",
                    "nominal_type": "SyntheticGrader",
                    "raw_evidence_grammar": "synthetic-grade-evidence-v1",
                    "runtime_id": "cpython-test",
                    "container_digest": "sha256:" + SHA_A,
                },
                role="grader_contract",
            )
            verifier_ref = authority_json(
                f"authority/{task_id}-verifier.json",
                {
                    **common_task_contract,
                    "record_kind": "prefix_verifier_contract_v1",
                    "nominal_type": "SyntheticVerifier",
                    "raw_evidence_grammar": "synthetic-verifier-evidence-v1",
                    "runtime_id": "cpython-test",
                    "container_digest": "sha256:" + SHA_A,
                },
                role="verifier_contract",
            )
            isolation_ref = authority_json(
                f"authority/{task_id}-isolation.json",
                {
                    **common_task_contract,
                    "record_kind": "prefix_isolation_contract_v1",
                    "distinct_environment_instances": True,
                    "distinct_processes": True,
                    "distinct_roots": True,
                    "no_shared_writable_state": True,
                    "qualification_ref": qualification_ref,
                },
                role="isolation_contract",
            )
            task_lane_rows.append(
                {
                    "task_id": task_id,
                    "prefix_lane_ordinal": 0,
                    "lane_ordinals_by_execution_rank": [0, 1, 2, 3],
                    "task_input_ref": task_input_ref,
                    "environment_contract_ref": environment_ref,
                    "grader_contract_ref": grader_ref,
                    "verifier_contract_ref": verifier_ref,
                    "isolation_contract_ref": isolation_ref,
                }
            )
        raws["provider"] = authority_json(
            "provider-v2.json",
            {
                "record_kind": "provider_lane_plan_v2",
                "schema_version": "2",
                "lanes": [
                    {
                        "ordinal": ordinal,
                        "lane_id": f"lane-{ordinal}",
                        "prefix_caps": {
                            "generated_tokens": 40,
                            "model_calls": 4,
                            "tool_calls": 4,
                            "wall_clock_ms": 1_000,
                        },
                        "branch_caps": {
                            "generated_tokens": 20,
                            "model_calls": 2,
                            "tool_calls": 4,
                            "wall_clock_ms": 500,
                            "pending_prefix_calls_count_against_tool_cap": True,
                        },
                        "simulator_caps": {
                            "aggregate_generated_tokens": 0,
                            "aggregate_model_calls": 0,
                            "aggregate_turns": 0,
                            "per_call_generated_tokens": 0,
                            "per_call_turns": 0,
                        },
                        "subject_contract_ref": subject_contract_ref,
                        "simulator_contract_ref": None,
                        "tool_parser_contract_ref": parser_contract_ref,
                        "meter_contract_ref": meter_contract_ref,
                    }
                    for ordinal in range(4)
                ],
                "task_lanes": task_lane_rows,
            },
            role="provider_lane_plan",
        )
        raws["features_task"] = raw(
            "features-task.json",
            {
                "record_kind": "assignment_verifier_features_v1",
                "schema_version": "1",
                "task_id": "task-1",
                "benchmark": "swe",
                "source_verifier_ref": raws["focal_verifier"],
                "source_report_ref": raws["report_task"],
                "components": [
                    {"kind": "check_runner", "value": "pytest", "count": 1},
                    {"kind": "failure_class", "value": "none", "count": 1},
                ],
                "objective_finding_count": 0,
                "normalized_report_token_count": 1,
            },
        )
        raws["features_donor"] = raw(
            "features-donor.json",
            {
                "record_kind": "assignment_verifier_features_v1",
                "schema_version": "1",
                "task_id": "task-donor",
                "benchmark": "swe",
                "source_verifier_ref": raws["donor_verifier"],
                "source_report_ref": raws["report_donor"],
                "components": [
                    {"kind": "check_runner", "value": "pytest", "count": 1},
                    {"kind": "failure_class", "value": "none", "count": 1},
                ],
                "objective_finding_count": 0,
                "normalized_report_token_count": 1,
            },
        )

    manifest_payload: dict[str, object] = {
        "task_registry_ref": raws["tasks"],
        "roster_ref": raws["roster"],
        "eligibility_manifest_ref": (
            None
            if (
                not completed_power_consumer_fixture
                or decision_authority == "synthetic_validation"
            )
            else raws["eligibility"]
        ),
        "roster_ceremony_policy_ref": (
            None
            if (
                not completed_power_consumer_fixture
                or decision_authority == "synthetic_validation"
            )
            else raws["ceremony_policy"]
        ),
        "assignment_program_ref": raws["assignment"],
        "provider_lane_plan_ref": raws["provider"],
        "storage_policy_contract_ref": raws["storage_policy"],
        "power_grid_ref": raws["power_grid"],
        "power_screen_topology_ref": raws["topology"],
        "tokenizer_ref": raws["tokenizer"],
        "packet_template_ref": raws["template"],
        "packet_policy_ref": raws["policy"],
        "pad_unit_set_ref": raws["pads"],
        "source_revision_refs": (
            [raws["revision"], normalizer_ref]
            if completed_power_consumer_fixture
            else [raws["revision"]]
        ),
        "commitment_scheme": "resampling-null-key-ceremony-v1",
        "roster_local_nonce_commitment_sha256": SHA_A,
        "schedule_seed_commitment_sha256": (
            commitment_sha256("schedule-seed", "study-1", U64Field(7))
            if completed_power_consumer_fixture
            else SHA_A
        ),
        "assignment_master_key_commitment_sha256": SHA_A,
        "required_document_kinds_ref": raws["required"],
    }
    if completed_power_consumer_fixture:
        manifest_payload["assignment_master_key_commitment_sha256"] = commitment_sha256(
            "assignment-master-key",
            "study-1",
            BytesField(bytes(range(32))),
        )
    manifest_ref = _write_test_record(
        root,
        "study-manifest.json",
        "resampling_study_manifest",
        manifest_payload,
    )
    if completed_power_consumer_fixture:
        manifest_ref["role"] = "study_manifest"

    schedule_payload = _minimal_payload("resampling_prefix_schedule")
    schedule_payload["manifest_ref"] = manifest_ref
    schedule_payload["power_final_ref"] = raws["power_config"]
    schedule_payload["schedule_authority"] = decision_authority
    schedule_payload["selected_tier"] = (
        None if decision_authority == "synthetic_validation" else 120
    )
    if variant == "schedule-assignment-program":
        schedule_payload["assignment_program_ref"] = raws["alternate"]
    if variant == "schedule-provider-lane":
        schedule_payload["provider_lane_plan_ref"] = raws["alternate"]
    donor_schedule = deepcopy(
        cast(list[dict[str, object]], schedule_payload["tasks"])[0]
    )
    donor_task_spec = cast(dict[str, object], donor_schedule["task"])
    donor_task_spec["task_id"] = "task-donor"
    donor_task_spec["lineage"] = "repo-donor"
    donor_schedule["prefix_seed"] = 12
    for index, slot in enumerate(
        cast(list[dict[str, object]], donor_schedule["slots"])
    ):
        slot["slot_id"] = f"donor-slot-{index}"
        slot["seed"] = 30 + index
    cast(list[dict[str, object]], schedule_payload["tasks"]).append(donor_schedule)
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
        "prefix_caps": {
            "generated_tokens": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "snapshot_ref": raws["composite_snapshot"],
        "visible_context_ref": (
            {**raws["visible_context"], "role": "frankenstein"}
            if variant == "conflicting-ref"
            else raws["visible_context"]
        ),
        "visible_sha256": raws["visible_context"]["sha256"],
        "token_ids_ref": raws["token_ids"],
        "token_ids_sha256": raws["token_ids"]["sha256"],
        "branch_pending_calls": [],
        "terminal_unexecuted_remainder": [],
        "trigger_reason": (
            "first_eligible_mutation"
            if (
                packet_pair
                or failed_second_task
                or variant == "prefix-trigger-state"
                or variant == "triggered-marker"
            )
            else "no_intervention_opportunity"
        ),
        "terminal_failure_kind": "none",
        "y0_grade": {
            "success": 0,
            "partial_reward": 0.0,
            "infrastructure_failure": False,
            "artifact_ref": raws["grade_evidence"],
        },
        "grade_execution_receipt_ref": raws["grade_evidence_receipt"],
        "verifier_receipt": {
            "task_id": "task-1",
            "schedule_sha256": verifier_schedule_sha,
            "snapshot_ref": raws["composite_snapshot"],
            "verifier_artifact_ref": raws["focal_verifier_evidence"],
            "finding_count": 0,
        },
        "verifier_execution_receipt_ref": raws["verifier_evidence_receipt"],
        "counters": {
            "generated_tokens": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "simulator_counters": {
            "generated_tokens": 0,
            "model_calls": 0,
            "tool_calls": 0,
            "wall_clock_ms": 0,
        },
        "call_seeds": [],
        "provider_attempts_ref": raws["provider_attempt_ledger"],
        "boundary_ledger_ref": raws["tool_boundary_ledger"],
        "provider_cost_ref": (
            _ref(
                f"controller-artifacts/provider_cost_closure/{SHA_A}",
                role="provider_cost_closure",
                sha256=SHA_A,
                byte_count=3,
                media_type="application/json",
            )
            if variant == "dangling-ref"
            else raws["provider_cost_closure"]
        ),
    }
    prefix_task_receipts = [prefix_task_receipt]
    if variant != "packet-prefix-coverage":
        donor_receipt = deepcopy(prefix_task_receipt)
        donor_receipt["task_id"] = "task-donor"
        donor_receipt["trigger_reason"] = "no_intervention_opportunity"
        donor_receipt["verifier_receipt"]["task_id"] = "task-donor"  # type: ignore[index]
        donor_receipt["verifier_receipt"][  # type: ignore[index]
            "verifier_artifact_ref"
        ] = raws["donor_verifier_evidence"]
        prefix_task_receipts.append(donor_receipt)
    prefix_ref = _write_test_record(
        root,
        "prefix-receipt.json",
        "resampling_prefix_receipt",
        {
            "schedule_ref": schedule_ref,
            "task_receipts": prefix_task_receipts,
        },
    )

    assignment_schedule_sha = cast(str, schedule_ref["sha256"])
    if variant == "assignment-schedule-hash":
        assignment_schedule_sha = SHA_A
    assignment_prefix_sha = cast(str, prefix_ref["sha256"])
    if variant == "assignment-prefix-hash":
        assignment_prefix_sha = SHA_A
    task_1_triggered = (
        prefix_task_receipt["trigger_reason"] != "no_intervention_opportunity"
    )
    assignment_mode = (
        "synthetic_derangement"
        if decision_authority == "synthetic_validation"
        else "confirmation_lineage_matching"
    )
    matching_algorithm = (
        "synthetic_cyclic_offset_v1"
        if decision_authority == "synthetic_validation"
        else "exact_constrained_min_cost_v1"
    )
    matching_proof_ref = {
        **raws["matching_proof"],
        "role": "matching_proof",
    }
    assignment_payload: dict[str, object] = {
        "manifest_ref": manifest_ref,
        "schedule_ref": schedule_ref,
        "prefix_index_ref": prefix_ref,
        "matching_program_ref": raws["assignment"],
        "assignment_master_key_commitment_sha256": (
            manifest_payload["assignment_master_key_commitment_sha256"]
            if completed_power_consumer_fixture
            else SHA_A
        ),
        "assignment_prefix_view_sha256": SHA_B,
        "assignment_mode": assignment_mode,
        "matching_proof_refs": ([matching_proof_ref] if task_1_triggered else []),
        "assignments": [
            {
                "task_id": "task-1",
                "task_lineage": "repo-1",
                "donor_match_kind": (
                    "matched" if task_1_triggered else "not_applicable_no_trigger"
                ),
                "donor_task_id": "task-donor" if task_1_triggered else None,
                "donor_lineage": "repo-donor" if task_1_triggered else None,
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
                "slot_ids_by_ordinal": [
                    "slot-0",
                    "slot-1",
                    "slot-2",
                    "slot-3",
                ],
                "treatment_allocation_index": 0,
                "allocation_rejection_counter": 0,
                "no_packet_orientation_bit": 0,
                "orientation_rejection_counter": 0,
                "slot_capabilities": [
                    [
                        f"slot-{index}",
                        hashlib.sha256(f"cap-{index}".encode()).hexdigest(),
                    ]
                    for index in range(4)
                ],
            }
        ],
        "donor_match_receipts": [
            (
                {
                    "kind": "matched",
                    "task_id": "task-1",
                    "donor_task_id": "task-donor",
                    "task_lineage": "repo-1",
                    "donor_lineage": "repo-donor",
                    "assignment_mode": assignment_mode,
                    "matching_algorithm": matching_algorithm,
                    "stratum_key": ["swe", "python"],
                    "assignment_prefix_view_sha256": SHA_B,
                    "candidates": [
                        {
                            "donor_task_id": "task-donor",
                            "donor_lineage": "repo-donor",
                            "primary_cost": [0, 0, 0],
                            "fallback_code": None,
                            "tie_hmac_sha256": SHA_A,
                        }
                    ],
                    "chosen_primary_cost": [0, 0, 0],
                    "matching_proof_ref": matching_proof_ref,
                }
                if task_1_triggered
                else {
                    "kind": "not_applicable_no_trigger",
                    "task_id": "task-1",
                    "trigger_reason": "no_intervention_opportunity",
                    "assignment_prefix_view_sha256": SHA_B,
                }
            )
        ],
    }
    cast(
        list[dict[str, object]],
        assignment_payload["assignments"],
    ).append(
        {
            "task_id": "task-donor",
            "task_lineage": "repo-donor",
            "donor_match_kind": "not_applicable_no_trigger",
            "donor_task_id": None,
            "donor_lineage": None,
            "slot_arms": [
                ["donor-slot-0", "SHAM"],
                ["donor-slot-1", "REAL"],
                ["donor-slot-2", "RESAMPLE"],
                ["donor-slot-3", "NONE"],
            ],
            "schedule_sha256": assignment_schedule_sha,
            "prefix_index_sha256": assignment_prefix_sha,
        }
    )
    cast(
        list[dict[str, object]],
        assignment_payload["allocation_receipts"],
    ).append(
        {
            "task_id": "task-donor",
            "slot_ids_by_ordinal": [
                "donor-slot-0",
                "donor-slot-1",
                "donor-slot-2",
                "donor-slot-3",
            ],
            "treatment_allocation_index": 1,
            "allocation_rejection_counter": 0,
            "no_packet_orientation_bit": 1,
            "orientation_rejection_counter": 0,
            "slot_capabilities": [
                [
                    f"donor-slot-{index}",
                    hashlib.sha256(f"donor-cap-{index}".encode()).hexdigest(),
                ]
                for index in range(4)
            ],
        }
    )
    cast(
        list[dict[str, object]],
        assignment_payload["donor_match_receipts"],
    ).append(
        {
            "kind": "not_applicable_no_trigger",
            "task_id": "task-donor",
            "trigger_reason": "no_intervention_opportunity",
            "assignment_prefix_view_sha256": SHA_B,
        }
    )
    assignment_ref = _write_test_record(
        root,
        "assignment-ledger.json",
        "resampling_assignment_ledger",
        assignment_payload,
    )

    if packet_pair or failed_second_task:
        packet_entry: dict[str, object] = {
            "task_id": (
                "task-frankenstein" if variant == "packet-pair-task-id" else "task-1"
            ),
            "donor_task_id": (
                "task-frankenstein"
                if variant == "packet-pair-donor-id"
                else "task-donor"
            ),
            "prefix_index_sha256": cast(str, prefix_ref["sha256"]),
            "real_ref": raws["real_packet"],
            "sham_ref": raws["sham_packet"],
            "real_token_count": 1,
            "sham_token_count": 1,
            "focal_verifier_ref": (
                raws["alternate"]
                if variant == "packet-focal-verifier"
                else raws["focal_verifier_evidence"]
            ),
            "donor_verifier_ref": (
                raws["alternate"]
                if variant == "packet-donor-verifier"
                else raws["donor_verifier_evidence"]
            ),
            "assignment_ref": assignment_ref,
            "identifier_map_ref": raws["identifier_map"],
            "tokenizer_ref": raws["tokenizer"],
            "packet_template_ref": raws["template"],
            "normalized_real_ref": raws["normalized_real"],
            "normalized_donor_ref": raws["normalized_donor"],
            "normalized_sham_ref": raws["normalized_sham"],
            "packet_policy_ref": raws["policy"],
            "pad_unit_set_ref": raws["pads"],
            "padding_search": {
                "pad_unit_set_sha256": cast(str, raws["pads"]["sha256"]),
                "target_token_count": 1,
                "states_explored": 1,
                "selected_unit_counts": [],
                "search_algorithm": "exact_dynamic_program_v1",
            },
            "field_order": [],
            "severity_multiset": [],
            "schema_parity": True,
            "field_parity": True,
            "severity_parity": True,
            "focal_collision_count": 0,
            "rewrite_expected": 0,
            "rewrite_completed": 0,
            "unmapped_identifiers": [],
            "donor_literal_collisions": [],
            "truncation_receipts": [],
        }
    else:
        packet_entry = {
            "task_id": "task-1",
            "prefix_index_sha256": cast(str, prefix_ref["sha256"]),
            "trigger_reason": "no_intervention_opportunity",
        }
    donor_packet_entry = {
        "task_id": "task-donor",
        "prefix_index_sha256": cast(str, prefix_ref["sha256"]),
        "trigger_reason": "no_intervention_opportunity",
    }
    candidate_payload: dict[str, object] = {
        "stage": "candidate",
        "assignment_ref": assignment_ref,
        "prefix_index_ref": prefix_ref,
        "tokenizer_ref": (
            raws["alternate"] if variant == "packet-tokenizer" else raws["tokenizer"]
        ),
        "packet_template_ref": raws["template"],
        "packet_policy_ref": raws["policy"],
        "pad_unit_set_ref": raws["pads"],
        "entries": [packet_entry, donor_packet_entry],
    }
    candidate_ref = _write_test_record(
        root,
        "packet-candidate.json",
        "resampling_packet_index",
        candidate_payload,
    )
    sealed_payload: dict[str, object] = {
        "stage": "sealed",
        "candidate_ref": candidate_ref,
        "assignment_ref": assignment_ref,
        "prefix_index_ref": prefix_ref,
        "tokenizer_ref": candidate_payload["tokenizer_ref"],
        "packet_template_ref": raws["template"],
        "packet_policy_ref": (
            raws["alternate"] if variant == "sealed-packet-policy" else raws["policy"]
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
    if failed_second_task:
        task_payload = _failed_second_task_block_payload(task_parent_refs)
        attempts = cast(list[dict[str, object]], task_payload["attempts"])
        for attempt_index, attempt in enumerate(attempts):
            attempt["attempt_ref"] = raws[f"attempt_{attempt_index}"]
            for terminal in cast(
                list[dict[str, object]],
                attempt["terminal_receipts"],
            ):
                terminal["final_snapshot_ref"] = raws["shared"]
                terminal["provider_cost_ref"] = raws["shared"]
        outage = cast(dict[str, object], task_payload["outage_receipt"])
        outage["provider_event_ref"] = raws["provider_event"]
        outage["first_attempt"] = deepcopy(attempts[0])
        outage["work_order_sha256s"] = deepcopy(attempts[0]["work_order_sha256s"])
        failed_terminals = cast(
            list[dict[str, object]],
            task_payload["terminal_slot_receipts"],
        )
        outcomes = cast(
            list[dict[str, object]],
            task_payload["slot_outcomes"],
        )
        executions = cast(
            list[dict[str, object]],
            task_payload["execution_receipts"],
        )
        for index, (terminal, outcome, execution) in enumerate(
            zip(failed_terminals, outcomes, executions, strict=True)
        ):
            adverse_ref = raws[f"adverse_{index}"]
            terminal["failed_attempt_ref"] = raws["attempt_1"]
            terminal["adverse_event_ref"] = adverse_ref
            terminal["provider_cost_ref"] = raws["shared"]
            outcome["artifact_ref"] = adverse_ref
            execution["source_receipt_sha256"] = canonical_digest(terminal)
            execution["outcome"] = deepcopy(outcome)
    elif packet_pair or variant == "triggered-marker":
        task_payload = _triggered_task_block_payload(task_parent_refs)
    else:
        task_payload = _no_trigger_task_block_payload(task_parent_refs)

    focal_capability_ids = [
        hashlib.sha256(f"cap-{index}".encode()).hexdigest() for index in range(4)
    ]
    focal_slot_ids = [f"slot-{index}" for index in range(4)]
    focal_outcomes = cast(
        list[dict[str, object]],
        task_payload["slot_outcomes"],
    )
    for index, outcome in enumerate(focal_outcomes):
        outcome["task_id"] = "task-1"
        outcome["benchmark"] = "swe"
        outcome["opaque_arm_id"] = focal_capability_ids[index]
        if task_payload["triggered"] is True and not failed_second_task:
            outcome["artifact_ref"] = raws["shared"]
        if task_payload["triggered"] is False:
            outcome["success"] = prefix_task_receipt["y0_grade"]["success"]  # type: ignore[index]
            outcome["prefix_success"] = prefix_task_receipt["y0_grade"][  # type: ignore[index]
                "success"
            ]
            outcome["partial_reward"] = prefix_task_receipt["y0_grade"][  # type: ignore[index]
                "partial_reward"
            ]
            outcome["infrastructure_failure"] = prefix_task_receipt[  # type: ignore[index]
                "y0_grade"
            ]["infrastructure_failure"]
            outcome["counters"] = deepcopy(prefix_task_receipt["counters"])
            outcome["artifact_ref"] = deepcopy(
                prefix_task_receipt["y0_grade"]["artifact_ref"]  # type: ignore[index]
            )

    focal_attempts = task_payload.get("attempts")
    if isinstance(focal_attempts, list):
        for attempt_index, attempt in enumerate(focal_attempts):
            attempt["attempt_ref"] = raws[f"attempt_{attempt_index}"]
            for index, terminal in enumerate(
                cast(list[dict[str, object]], attempt["terminal_receipts"])
            ):
                terminal["slot_id"] = focal_slot_ids[index]
                terminal["opaque_capability_id"] = focal_capability_ids[index]
                terminal["final_snapshot_ref"] = raws["shared"]
                terminal["provider_cost_ref"] = raws["shared"]
        top_terminals = cast(
            list[dict[str, object]],
            task_payload["terminal_slot_receipts"],
        )
        for index, terminal in enumerate(top_terminals):
            terminal["slot_id"] = focal_slot_ids[index]
            terminal["opaque_capability_id"] = focal_capability_ids[index]
            terminal["provider_cost_ref"] = raws["shared"]
            if "final_snapshot_ref" in terminal:
                terminal["final_snapshot_ref"] = raws["shared"]
            else:
                terminal["failed_attempt_ref"] = raws["attempt_1"]
        executions = cast(
            list[dict[str, object]],
            task_payload["execution_receipts"],
        )
        for index, execution in enumerate(executions):
            execution["source_receipt_sha256"] = canonical_digest(top_terminals[index])
            execution["outcome"] = deepcopy(focal_outcomes[index])
            grade = execution.get("grade_receipt")
            if isinstance(grade, dict):
                for field in (
                    "success",
                    "partial_reward",
                    "infrastructure_failure",
                    "artifact_ref",
                ):
                    grade[field] = deepcopy(focal_outcomes[index][field])
        outage_receipt = task_payload.get("outage_receipt")
        if isinstance(outage_receipt, dict):
            outage_receipt["first_attempt"] = deepcopy(focal_attempts[0])
            outage_receipt["work_order_sha256s"] = deepcopy(
                focal_attempts[0]["work_order_sha256s"]
            )

    if variant == "task-schedule-metadata":
        task_payload["stratum"] = "forged"
    if variant == "task-assignment-capability":
        for index, outcome in enumerate(
            cast(list[dict[str, object]], task_payload["slot_outcomes"])
        ):
            outcome["opaque_arm_id"] = f"forged-capability-{index}"
    if variant == "task-assignment-slot":
        forged_slot_ids = [f"forged-slot-{index}" for index in range(4)]
        forged_attempts = cast(
            list[dict[str, object]],
            task_payload["attempts"],
        )
        for attempt in forged_attempts:
            for index, terminal in enumerate(
                cast(list[dict[str, object]], attempt["terminal_receipts"])
            ):
                terminal["slot_id"] = forged_slot_ids[index]
        forged_terminals = cast(
            list[dict[str, object]],
            task_payload["terminal_slot_receipts"],
        )
        for index, terminal in enumerate(forged_terminals):
            terminal["slot_id"] = forged_slot_ids[index]
        for index, execution in enumerate(
            cast(
                list[dict[str, object]],
                task_payload["execution_receipts"],
            )
        ):
            execution["source_receipt_sha256"] = canonical_digest(
                forged_terminals[index]
            )
        forged_outage = task_payload.get("outage_receipt")
        if isinstance(forged_outage, dict):
            forged_outage["first_attempt"] = deepcopy(forged_attempts[0])
            forged_outage["work_order_sha256s"] = deepcopy(
                forged_attempts[0]["work_order_sha256s"]
            )
    task_ref = _write_test_record(
        root,
        "task-1.json",
        "resampling_task_block",
        task_payload,
    )

    donor_task_payload = _no_trigger_task_block_payload(task_parent_refs)
    donor_task_payload["task_id"] = "task-donor"
    donor_outcomes = cast(
        list[dict[str, object]],
        donor_task_payload["slot_outcomes"],
    )
    donor_capability_ids = [
        hashlib.sha256(f"donor-cap-{index}".encode()).hexdigest() for index in range(4)
    ]
    for index, outcome in enumerate(donor_outcomes):
        outcome["task_id"] = "task-donor"
        outcome["opaque_arm_id"] = donor_capability_ids[index]
        outcome["artifact_ref"] = donor_receipt["y0_grade"]["artifact_ref"]  # type: ignore[index]
    donor_task_ref = _write_test_record(
        root,
        "task-donor.json",
        "resampling_task_block",
        donor_task_payload,
    )
    task_refs = [task_ref, donor_task_ref]
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

    def projected_row(
        payload: dict[str, object],
        *,
        lineage: str,
        slot_prefix: str,
    ) -> dict[str, object]:
        return {
            "task_id": payload["task_id"],
            "benchmark": payload["benchmark"],
            "stratum": payload["stratum"],
            "lineage": lineage,
            "sensitivity_groups": deepcopy(payload["sensitivity_groups"]),
            "prefix_success": payload["prefix_success"],
            "triggered": payload["triggered"],
            "slots": [
                {
                    "label": label,
                    "slot_id": f"{slot_prefix}{index}",
                    "outcome": deepcopy(payload["slot_outcomes"][index]),  # type: ignore[index]
                }
                for index, label in enumerate(("A", "B", "C", "D"))
            ],
            "pipeline_valid": payload["pipeline_valid"],
            "validity_codes": deepcopy(payload["validity_codes"]),
        }

    projection_payload = {
        "schedule_ref": schedule_ref,
        "analysis_freeze_ref": freeze_ref,
        "task_block_refs": task_refs,
        "rows": [
            projected_row(
                task_payload,
                lineage="repo-1",
                slot_prefix="slot-",
            ),
            projected_row(
                donor_task_payload,
                lineage="repo-donor",
                slot_prefix="donor-slot-",
            ),
        ],
        "expected_task_count": 2,
        "complete": True,
    }
    if variant == "projection-row-reconstruction":
        projection_payload["rows"][0]["lineage"] = "repo-forged"  # type: ignore[index]
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
            "expected_task_count": 2,
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
                "row_count": 2,
                "result": _analysis_result(),
                "numeric_receipt": {"finite": True},
            },
        )

    common_power = {
        "authority_ref": raws["power_authority"],
        "roster_ref": raws["roster"],
        "tier_membership_sha256": SHA_A,
        "grid_ref": raws["power_grid"],
        "screen_topology_ref": raws["topology"],
        "rng_contract_sha256": SHA_B,
        "config_ref": raws["power_config"],
        "numeric_fixture_ref": raws["numeric_fixture"],
        "numeric_contract": _numeric_contract(),
    }
    active_generation = 1 if earlier_power_partial else 0

    def bind_power(
        payload: dict[str, object],
        *,
        phase: str = "gaussian_approximation",
    ) -> None:
        payload.update(deepcopy(common_power))
        payload["phase"] = phase
        payload["decision_authority"] = decision_authority
        payload["generation"] = active_generation
        stage = cast(str, payload["stage"])
        if stage != "final":
            payload["kernel_id"] = _T3_S02_POWER_KERNEL_IDS[(stage, phase)]
            payload["shard_count"] = 2

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
    earlier_attempt_refs: list[dict[str, object]] = []
    if earlier_power_partial:
        earlier_screen = _power_payload("screen")
        bind_power(earlier_screen)
        earlier_screen["generation"] = 0
        earlier_screen["cell_count"] = 5
        earlier_screen_ref = _write_test_record(
            root,
            "power/gaussian-earlier-screen.json",
            "resampling_power_report",
            earlier_screen,
        )
        earlier_shard = _power_payload("shard", shard_index=0)
        bind_power(earlier_shard)
        earlier_shard["generation"] = 0
        earlier_shard["parent_refs"] = [earlier_screen_ref]
        earlier_shard["cell_results"] = [
            _cell_result(cell_id) for cell_id in partitions[0]
        ]
        earlier_shard_ref = _write_test_record(
            root,
            "power/gaussian-earlier-shard-0.json",
            "resampling_power_report",
            earlier_shard,
        )
        earlier_attempt_refs.extend([earlier_screen_ref, earlier_shard_ref])
    shard_positions = (
        [] if no_go_stage == "screen" else [0] if no_go_stage == "shard" else [0, 1]
    )
    if no_go_stage == "shard" and no_go_mutation == "shard-gap":
        shard_positions = [1]
    for shard_position in shard_positions:
        shard_payload = _power_payload("shard", shard_index=shard_position)
        bind_power(shard_payload)
        shard_payload["parent_refs"] = [screen_ref]
        shard_payload["cell_results"] = [
            _cell_result(cell_id) for cell_id in partitions[shard_position]
        ]
        if variant == "power-shard-dataset-count" and shard_position == 1:
            shard_payload["dataset_count"] = 19_999
            for result in cast(
                list[dict[str, object]],
                shard_payload["cell_results"],
            ):
                result["alternative_trial_count"] = 19_999
                result["null_trial_count"] = 19_999
        if variant == "power-shard-gap" and shard_position == 1:
            shard_payload["shard_index"] = 2
            shard_payload["shard_count"] = 3
        elif variant == "power-shard-count" and shard_position == 1:
            shard_payload["shard_count"] = 3
        if variant == "power-shard-parent" and shard_position == 1:
            shard_payload["parent_refs"] = [raws["alternate"]]
        if shard_position == 1:
            if variant == "power-authority-ref-drift":
                shard_payload["authority_ref"] = raws["alternate"]
            elif variant == "power-membership-drift":
                shard_payload["tier_membership_sha256"] = SHA_B
            elif variant == "power-rng-drift":
                shard_payload["rng_contract_sha256"] = SHA_A
            elif variant == "power-screen-topology-drift":
                shard_payload["screen_topology_ref"] = raws["alternate"]
            elif variant == "power-authority-label-drift":
                shard_payload["decision_authority"] = (
                    "roster_bound_selection"
                    if decision_authority == "synthetic_validation"
                    else "synthetic_validation"
                )
        gaussian_shard_payloads.append(shard_payload)
        gaussian_shard_refs.append(
            _write_test_record(
                root,
                f"power/gaussian-shard-{shard_position}.json",
                "resampling_power_report",
                shard_payload,
            )
        )
    selection_ref: dict[str, object] | None = None
    if no_go_stage in (None, "selection", "validation"):
        selection_payload = _power_payload("selection")
        bind_power(selection_payload)
        selection_payload["parent_refs"] = [screen_ref, *gaussian_shard_refs]
        if variant == "power-shard-count-mirror-drift":
            selection_payload["shard_count"] = 3
        if variant == "power-selection-parent":
            selection_payload["parent_refs"] = [
                screen_ref,
                gaussian_shard_refs[0],
            ]
        selection_ref = _write_test_record(
            root,
            "power/gaussian-selection.json",
            "resampling_power_report",
            selection_payload,
        )
    gaussian_validation_ref: dict[str, object] | None = None
    if no_go_stage in (None, "validation"):
        assert selection_ref is not None
        gaussian_validation = _power_payload("validation")
        bind_power(gaussian_validation)
        gaussian_validation["parent_refs"] = [
            screen_ref,
            *gaussian_shard_refs,
            selection_ref,
        ]
        if (
            no_go_stage == "validation"
            and no_go_reason == "power_or_type_i_gate_failed"
        ):
            gaussian_validation["approximation_receipt"] = {
                "max_absolute_gate_pass_rate_difference": 0.01,
                "gaussian_tier_decision": "FEASIBILITY_NO_GO",
                "full_multiplier_tier_decision": "FEASIBILITY_NO_GO",
                "tier_decision_unchanged": True,
                "passed": True,
            }
        elif (
            fallback and variant != "fallback-after-pass"
        ) or no_go_stage == "validation":
            gaussian_validation["approximation_receipt"] = {
                "max_absolute_gate_pass_rate_difference": 0.02,
                "gaussian_tier_decision": (
                    "C160"
                    if decision_authority == "roster_bound_selection"
                    else "CONDITIONAL_ONLY"
                ),
                "full_multiplier_tier_decision": (
                    "C120"
                    if decision_authority == "roster_bound_selection"
                    else "CONDITIONAL_ONLY"
                ),
                "tier_decision_unchanged": (
                    decision_authority == "synthetic_validation"
                ),
                "passed": False,
            }
        elif decision_authority == "synthetic_validation":
            gaussian_validation["approximation_receipt"] = {
                "max_absolute_gate_pass_rate_difference": 0.01,
                "gaussian_tier_decision": "CONDITIONAL_ONLY",
                "full_multiplier_tier_decision": "CONDITIONAL_ONLY",
                "tier_decision_unchanged": True,
                "passed": True,
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
        *earlier_attempt_refs,
        screen_ref,
        *gaussian_shard_refs,
    ]
    if selection_ref is not None:
        attempt_refs.append(selection_ref)
    if gaussian_validation_ref is not None:
        attempt_refs.append(gaussian_validation_ref)
    selected_phase = "gaussian_approximation"
    selected_generation = active_generation
    if no_go_stage is None:
        assert selection_ref is not None
        assert gaussian_validation_ref is not None
        finalization: dict[str, object] = {
            "kind": "completed_chain",
            "selected_phase": "gaussian_approximation",
            "selected_generation": active_generation,
            "selected_kernel_id": "power-final-gaussian-v1",
            "selected_shard_count": 2,
            "selected_screen_ref": screen_ref,
            "selected_shard_refs": (
                [gaussian_shard_refs[0]]
                if variant == "power-finalization-shard-gap"
                else gaussian_shard_refs
            ),
            "selected_selection_ref": selection_ref,
            "selected_validation_ref": gaussian_validation_ref,
            "selected_tier": (
                160 if decision_authority == "roster_bound_selection" else None
            ),
            "decision": (
                "GO"
                if decision_authority == "roster_bound_selection"
                else "CONDITIONAL_ONLY"
            ),
        }
        if verdict_mutation == "completed-no-tier":
            finalization["selected_tier"] = None
        elif verdict_mutation == "completed-no-go":
            finalization["decision"] = "NO_GO"
        elif verdict_mutation == "synthetic-tier":
            finalization["selected_tier"] = 160
            finalization["decision"] = "GO"
    else:
        terminal_ref = (
            screen_ref
            if no_go_stage == "screen"
            else gaussian_shard_refs[-1]
            if no_go_stage == "shard"
            else selection_ref
            if no_go_stage == "selection"
            else gaussian_validation_ref
        )
        assert terminal_ref is not None
        finalization = {
            "kind": "feasibility_no_go",
            "terminal_attempt_ref": (
                raws["alternate"]
                if no_go_mutation == "fictitious-ref"
                else terminal_ref
            ),
            "terminal_stage": (
                "screen"
                if no_go_mutation == "wrong-stage" and no_go_stage != "screen"
                else "shard"
                if no_go_mutation == "wrong-stage"
                else no_go_stage
            ),
            "terminal_phase": "gaussian_approximation",
            "terminal_kernel_id": "power-final-gaussian-v1",
            "terminal_shard_count": 2,
            "reason": (
                no_go_reason
                if no_go_reason is not None
                else "gaussian_screen_exhausted"
                if no_go_stage == "screen"
                else "attempt_incomplete"
            ),
            "selected_tier": None,
            "decision": "NO_GO",
        }
        if decision_authority == "synthetic_validation":
            finalization["kind"] = "synthetic_validation_failed"
            finalization["decision"] = "CONDITIONAL_ONLY"

    if fallback:
        assert gaussian_validation_ref is not None
        fallback_trigger = gaussian_validation_ref
        if variant == "fallback-trigger-screen":
            fallback_trigger = screen_ref
        full_screen = _power_payload("screen")
        bind_power(full_screen, phase="full_multiplier_fallback")
        full_screen["cell_count"] = 5
        full_screen["parent_refs"] = [fallback_trigger]
        full_screen["fallback_trigger_ref"] = fallback_trigger
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
            selected_tier=(
                None
                if full_gate_failure
                else 160
                if decision_authority == "roster_bound_selection"
                else None
            ),
            decision=(
                "NO_GO"
                if full_gate_failure
                else "GO"
                if decision_authority == "roster_bound_selection"
                else "CONDITIONAL_ONLY"
            ),
        )
        if full_gate_failure and variant == "full-gate-terminal-go":
            full_validation["selected_tier"] = 160
            full_validation["decision"] = "GO"
        full_validation_ref = _write_test_record(
            root,
            "power/full-validation.json",
            "resampling_power_report",
            full_validation,
        )
        attempt_refs.extend([full_screen_ref, *full_shard_refs, full_validation_ref])
        selected_phase = "full_multiplier_fallback"
        if full_gate_failure:
            finalization = {
                "kind": "feasibility_no_go",
                "terminal_attempt_ref": full_validation_ref,
                "terminal_stage": "validation",
                "terminal_phase": "full_multiplier_fallback",
                "terminal_kernel_id": "power-final-full-multiplier-v1",
                "terminal_shard_count": 2,
                "reason": "power_or_type_i_gate_failed",
                "selected_tier": None,
                "decision": "NO_GO",
            }
        else:
            finalization = {
                "kind": "completed_chain",
                "selected_phase": selected_phase,
                "selected_generation": active_generation,
                "selected_kernel_id": "power-final-full-multiplier-v1",
                "selected_shard_count": 2,
                "fallback_trigger_ref": fallback_trigger,
                "selected_screen_ref": full_screen_ref,
                "selected_shard_refs": full_shard_refs,
                "full_grid_validation_ref": full_validation_ref,
                "selected_tier": (
                    160 if decision_authority == "roster_bound_selection" else None
                ),
                "decision": (
                    "GO"
                    if decision_authority == "roster_bound_selection"
                    else "CONDITIONAL_ONLY"
                ),
            }
            if verdict_mutation == "completed-no-tier":
                finalization["selected_tier"] = None
            elif verdict_mutation == "completed-no-go":
                finalization["decision"] = "NO_GO"
            elif verdict_mutation == "synthetic-tier":
                finalization["selected_tier"] = 160
                finalization["decision"] = "GO"

    if retry_after_terminal == "gaussian_no_go":
        assert gaussian_validation_ref is not None
        retry_generation = active_generation + 1
        retry_screen = _power_payload("screen")
        bind_power(retry_screen)
        retry_screen["generation"] = retry_generation
        retry_screen["cell_count"] = 5
        retry_screen_ref = _write_test_record(
            root,
            "power/gaussian-retry-screen.json",
            "resampling_power_report",
            retry_screen,
        )
        retry_shard_refs: list[dict[str, object]] = []
        for shard_index, cell_ids in enumerate(partitions):
            retry_shard = _power_payload("shard", shard_index=shard_index)
            bind_power(retry_shard)
            retry_shard["generation"] = retry_generation
            retry_shard["parent_refs"] = [retry_screen_ref]
            retry_shard["cell_results"] = [
                _cell_result(cell_id) for cell_id in cell_ids
            ]
            retry_shard_refs.append(
                _write_test_record(
                    root,
                    f"power/gaussian-retry-shard-{shard_index}.json",
                    "resampling_power_report",
                    retry_shard,
                )
            )
        retry_selection = _power_payload("selection")
        bind_power(retry_selection)
        retry_selection["generation"] = retry_generation
        retry_selection["parent_refs"] = [
            retry_screen_ref,
            *retry_shard_refs,
        ]
        retry_selection_ref = _write_test_record(
            root,
            "power/gaussian-retry-selection.json",
            "resampling_power_report",
            retry_selection,
        )
        retry_validation = _power_payload("validation")
        bind_power(retry_validation)
        retry_validation["generation"] = retry_generation
        retry_validation["parent_refs"] = [
            retry_screen_ref,
            *retry_shard_refs,
            retry_selection_ref,
        ]
        retry_validation_ref = _write_test_record(
            root,
            "power/gaussian-retry-validation.json",
            "resampling_power_report",
            retry_validation,
        )
        attempt_refs.extend(
            [
                retry_screen_ref,
                *retry_shard_refs,
                retry_selection_ref,
                retry_validation_ref,
            ]
        )
        selected_phase = "gaussian_approximation"
        selected_generation = retry_generation
        finalization = {
            "kind": "completed_chain",
            "selected_phase": selected_phase,
            "selected_generation": retry_generation,
            "selected_kernel_id": "power-final-gaussian-v1",
            "selected_shard_count": 2,
            "selected_screen_ref": retry_screen_ref,
            "selected_shard_refs": retry_shard_refs,
            "selected_selection_ref": retry_selection_ref,
            "selected_validation_ref": retry_validation_ref,
            "selected_tier": 160,
            "decision": "GO",
        }
    elif retry_after_terminal == "full_no_go":
        assert fallback
        assert gaussian_validation_ref is not None
        retry_generation = active_generation + 1
        retry_screen = _power_payload("screen")
        bind_power(retry_screen, phase="full_multiplier_fallback")
        retry_screen["generation"] = retry_generation
        retry_screen["cell_count"] = 5
        retry_screen["parent_refs"] = [gaussian_validation_ref]
        retry_screen["fallback_trigger_ref"] = gaussian_validation_ref
        retry_screen_ref = _write_test_record(
            root,
            "power/full-retry-screen.json",
            "resampling_power_report",
            retry_screen,
        )
        retry_shard_refs = []
        for shard_index, cell_ids in enumerate(partitions):
            retry_shard = _power_payload("shard", shard_index=shard_index)
            bind_power(retry_shard, phase="full_multiplier_fallback")
            retry_shard["generation"] = retry_generation
            retry_shard["parent_refs"] = [retry_screen_ref]
            retry_shard["cell_results"] = [
                _cell_result(cell_id) for cell_id in cell_ids
            ]
            retry_shard_refs.append(
                _write_test_record(
                    root,
                    f"power/full-retry-shard-{shard_index}.json",
                    "resampling_power_report",
                    retry_shard,
                )
            )
        retry_validation = _power_payload("validation")
        bind_power(retry_validation, phase="full_multiplier_fallback")
        retry_validation["generation"] = retry_generation
        for field in (
            "selected_cells",
            "interval_receipts",
            "validation_dataset_count",
            "approximation_receipt",
        ):
            del retry_validation[field]
        retry_validation.update(
            parent_refs=[
                gaussian_validation_ref,
                retry_screen_ref,
                *retry_shard_refs,
            ],
            fallback_trigger_ref=gaussian_validation_ref,
            complete_cell_ids=[f"cell-{index}" for index in range(5)],
            expected_cell_count=5,
            observed_cell_count=5,
            raw_counts_ref=raws["shared"],
            numeric_receipt_ref=raws["numeric_fixture"],
            selected_tier=160,
            decision="GO",
        )
        retry_validation_ref = _write_test_record(
            root,
            "power/full-retry-validation.json",
            "resampling_power_report",
            retry_validation,
        )
        attempt_refs.extend([retry_screen_ref, *retry_shard_refs, retry_validation_ref])
        selected_phase = "full_multiplier_fallback"
        selected_generation = retry_generation
        finalization = {
            "kind": "completed_chain",
            "selected_phase": selected_phase,
            "selected_generation": retry_generation,
            "selected_kernel_id": "power-final-full-multiplier-v1",
            "selected_shard_count": 2,
            "fallback_trigger_ref": gaussian_validation_ref,
            "selected_screen_ref": retry_screen_ref,
            "selected_shard_refs": retry_shard_refs,
            "full_grid_validation_ref": retry_validation_ref,
            "selected_tier": 160,
            "decision": "GO",
        }

    if later_power_partial:
        assert no_go_stage is None
        later_generation = active_generation + 1
        later_screen = _power_payload("screen")
        bind_power(later_screen, phase=selected_phase)
        later_screen["generation"] = later_generation
        later_screen["cell_count"] = 5
        if selected_phase == "full_multiplier_fallback":
            assert gaussian_validation_ref is not None
            later_screen["parent_refs"] = [gaussian_validation_ref]
            later_screen["fallback_trigger_ref"] = gaussian_validation_ref
        later_screen_ref = _write_test_record(
            root,
            f"power/{selected_phase}-later-screen.json",
            "resampling_power_report",
            later_screen,
        )
        later_shard = _power_payload("shard", shard_index=0)
        bind_power(later_shard, phase=selected_phase)
        later_shard["generation"] = later_generation
        later_shard["parent_refs"] = [later_screen_ref]
        later_shard["cell_results"] = [
            _cell_result(cell_id) for cell_id in partitions[0]
        ]
        later_shard_ref = _write_test_record(
            root,
            f"power/{selected_phase}-later-shard-0.json",
            "resampling_power_report",
            later_shard,
        )
        attempt_refs.extend([later_screen_ref, later_shard_ref])

    if variant == "power-selected-shard-count-drift":
        finalization["selected_shard_count"] = 3
    elif variant == "power-terminal-phase-drift":
        finalization["terminal_phase"] = "full_multiplier_fallback"
    elif variant == "power-terminal-kernel-drift":
        finalization["terminal_kernel_id"] = "power-final-full-multiplier-v1"
    elif variant == "power-terminal-count-drift":
        finalization["terminal_shard_count"] = 3

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


@pytest.mark.parametrize(
    ("decision_authority", "expected_tier"),
    [
        ("synthetic_validation", None),
        ("roster_bound_selection", 160),
    ],
)
def test_t3_s07_completed_power_consumer_derives_manifest_membership(
    tmp_path: Path,
    decision_authority: str,
    expected_tier: int | None,
) -> None:
    root = tmp_path / decision_authority
    installed = _build_full_study(
        root,
        decision_authority=decision_authority,
        completed_power_consumer_fixture=True,
    )
    final_paths = [
        path
        for path in (root / "power").glob("*.json")
        if load_record(path)["payload"]["stage"] == "final"  # type: ignore[index]
    ]
    assert len(final_paths) == 1
    final_path = final_paths[0]
    final_bytes = final_path.read_bytes()
    selection = require_schedulable_power_final(
        ArtifactRef(**cast(dict[str, Any], installed["manifest_ref"])),
        ArtifactRef(
            role="resampling_power_report",
            relative_path=final_path.relative_to(root).as_posix(),
            sha256=hashlib.sha256(final_bytes).hexdigest(),
            byte_count=len(final_bytes),
            media_type="application/json",
        ),
        run_root=root,
    )
    assert selection.schedule_authority == decision_authority
    assert selection.selected_tier == expected_tier
    expected_count = 2 if decision_authority == "synthetic_validation" else 160
    assert len(selection.selected_task_ids) == expected_count
    assert selection.selected_task_ids[:2] == ("task-1", "task-donor")


def test_t3_s07_local_storage_lease_is_nominal_exclusive_and_single_use(
    tmp_path: Path,
) -> None:
    root = tmp_path / "local-storage"
    installed = _build_full_study(
        root,
        completed_power_consumer_fixture=True,
    )
    manifest_ref = ArtifactRef(**cast(dict[str, Any], installed["manifest_ref"]))
    lease = claim_local_test_storage(
        transaction="prefix",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=None,
    )
    with pytest.raises(RecordValidationError, match="already held"):
        claim_local_test_storage(
            transaction="prefix",
            run_root=root,
            manifest_ref=manifest_ref,
            schedule_ref=None,
        )
    with pytest.raises(TypeError, match="created only by core"):
        LocalTestStorageLease(object())  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="unavailable"):
        ConfirmationStorageLease()
    begin = lease._begin()
    assert begin.observation == "begin"
    end = lease._end()
    assert end.observation == "end"
    with pytest.raises(RecordValidationError, match="cannot end"):
        lease._end()
    lease._abort()
    with pytest.raises(RecordValidationError, match="cannot begin"):
        lease._begin()
    with pytest.raises(ValueError, match="transaction"):
        claim_local_test_storage(
            transaction=cast(Any, "../../escape"),
            run_root=root,
            manifest_ref=manifest_ref,
            schedule_ref=None,
        )

    confirmation_root = tmp_path / "confirmation-storage"
    confirmation = _build_full_study(
        confirmation_root,
        decision_authority="roster_bound_selection",
        completed_power_consumer_fixture=True,
    )
    with pytest.raises(RecordValidationError, match="synthetic manifest"):
        claim_local_test_storage(
            transaction="prefix",
            run_root=confirmation_root,
            manifest_ref=ArtifactRef(
                **cast(dict[str, Any], confirmation["manifest_ref"])
            ),
            schedule_ref=None,
        )


def test_t3_s07_local_storage_publication_binds_science_and_fixed_receipt(
    tmp_path: Path,
) -> None:
    root = tmp_path / "local-publication"
    installed = _build_full_study(
        root,
        completed_power_consumer_fixture=True,
    )
    manifest_ref = ArtifactRef(**cast(dict[str, Any], installed["manifest_ref"]))
    lease = claim_local_test_storage(
        transaction="prefix",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=None,
    )
    prepared = b'{"prepared":"science"}'
    ref = _publish_local_test_scientific(
        lease,
        out=root / "prepared-science.json",
        role="test_science",
        media_type="application/json",
        prepare=lambda: prepared,
    )
    assert (root / ref.relative_path).read_bytes() == prepared
    receipt_path = root / "operational/storage-policy/prefix.json"
    receipt = json.loads(receipt_path.read_bytes())
    assert receipt["fixed_receipt_is_acceptance_marker"] is True
    assert receipt["publication_commit"]["scientific_sha256"] == ref.sha256
    assert (
        receipt["transaction_intent_sha256"]
        == receipt["publication_commit"]["transaction_intent_sha256"]
    )
    commit_id = receipt["publication_commit"]["registry_commit_id"]
    proof_path = (
        root
        / "operational"
        / "storage-policy"
        / "registry"
        / "commits"
        / f"{commit_id}.json"
    )
    assert proof_path.is_file()
    receipt_path.unlink()
    original_proof = proof_path.read_bytes()
    forged_proof = json.loads(original_proof)
    forged_proof["extra"] = "receipt-splice"
    proof_path.write_bytes(canonical_json_bytes(forged_proof, indent=None))
    forged_recovery_lease = claim_local_test_storage(
        transaction="prefix",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=None,
    )
    with pytest.raises(RecordValidationError, match="proof"):
        _publish_local_test_scientific(
            forged_recovery_lease,
            out=root / "prepared-science.json",
            role="test_science",
            media_type="application/json",
            prepare=lambda: pytest.fail("forged recovery must not prepare science"),
        )
    proof_path.write_bytes(original_proof)
    recovery_lease = claim_local_test_storage(
        transaction="prefix",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=None,
    )
    recovered = _publish_local_test_scientific(
        recovery_lease,
        out=root / "prepared-science.json",
        role="test_science",
        media_type="application/json",
        prepare=lambda: pytest.fail("post-commit recovery must not prepare science"),
    )
    assert recovered == ref
    assert receipt_path.is_file()
    with pytest.raises(RecordValidationError, match="cannot begin"):
        lease._begin()


def test_t3_s07_prefix_schedule_is_derived_and_published_inside_lease(
    tmp_path: Path,
) -> None:
    root = tmp_path / "prefix-schedule"
    installed = _build_full_study(
        root,
        completed_power_consumer_fixture=True,
    )
    (root / "prefix-schedule.json").unlink()
    manifest_ref = ArtifactRef(**cast(dict[str, Any], installed["manifest_ref"]))
    final_paths = [
        path
        for path in (root / "power").glob("*.json")
        if load_record(path)["payload"]["stage"] == "final"  # type: ignore[index]
    ]
    assert len(final_paths) == 1
    final_path = final_paths[0]
    final_bytes = final_path.read_bytes()
    power_final_ref = ArtifactRef(
        role="resampling_power_report",
        relative_path=final_path.relative_to(root).as_posix(),
        sha256=hashlib.sha256(final_bytes).hexdigest(),
        byte_count=len(final_bytes),
        media_type="application/json",
    )
    wrong_seed_lease = claim_local_test_storage(
        transaction="prefix",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=None,
    )
    with pytest.raises(RecordValidationError, match="commitment"):
        seal_prefix_schedule(
            manifest_ref,
            power_final_ref,
            schedule_seed_reveal=8,
            storage_policy_lease=wrong_seed_lease,
            run_root=root,
            out=root / "prefix-schedule.json",
        )
    assert not (root / "prefix-schedule.json").exists()
    lease = claim_local_test_storage(
        transaction="prefix",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=None,
    )
    schedule_ref = seal_prefix_schedule(
        manifest_ref,
        power_final_ref,
        schedule_seed_reveal=7,
        storage_policy_lease=lease,
        run_root=root,
        out=root / "prefix-schedule.json",
    )
    schedule = load_record(root / schedule_ref.relative_path)
    payload = cast(dict[str, object], schedule["payload"])
    assert payload["schedule_authority"] == "synthetic_validation"
    assert payload["selected_tier"] is None
    tasks = cast(list[dict[str, object]], payload["tasks"])
    assert [cast(dict[str, object], task["task"])["task_id"] for task in tasks] == [
        "task-1",
        "task-donor",
    ]
    for task in tasks:
        slots = cast(list[dict[str, object]], task["slots"])
        assert len({slot["slot_id"] for slot in slots}) == 4
        assert sorted(slot["execution_order"] for slot in slots) == [0, 1, 2, 3]
        assert all(slot["hardware_lane"] == slot["execution_order"] for slot in slots)
    receipt = json.loads((root / "operational/storage-policy/prefix.json").read_bytes())
    assert receipt["publication_commit"]["scientific_sha256"] == schedule_ref.sha256
    authority = load_prefix_execution_authority(
        run_root=root,
        schedule_ref=schedule_ref,
        task_id="task-1",
    )
    assert authority.simulator_contract_ref is None
    assert authority.simulator_caps == CallContractCaps(0, 0, 0, 0, 0)


def test_t3_s09_branch_assignment_is_derived_inside_assignment_lease(
    tmp_path: Path,
) -> None:
    root = tmp_path / "branch-assignment"
    installed = _build_full_study(
        root,
        completed_power_consumer_fixture=True,
    )
    forbidden = {
        "resampling_assignment_ledger",
        "resampling_packet_index",
        "resampling_task_block",
        "resampling_blinded_projection",
        "resampling_analysis_freeze",
        "resampling_analysis",
        "resampling_unblind_receipt",
        "resampling_artifact_root",
    }
    for path in root.rglob("*.json"):
        try:
            value = json.loads(path.read_bytes())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(value, dict) and value.get("record_kind") in forbidden:
            path.unlink()

    manifest_ref = ArtifactRef(**cast(dict[str, Any], installed["manifest_ref"]))
    old_prefix = load_record(root / "prefix-receipt.json")
    old_prefix_payload = cast(dict[str, object], old_prefix["payload"])
    (root / "prefix-receipt.json").unlink()
    (root / "prefix-schedule.json").unlink()
    final_paths = [
        path
        for path in (root / "power").glob("*.json")
        if load_record(path)["payload"]["stage"] == "final"  # type: ignore[index]
    ]
    assert len(final_paths) == 1
    final_path = final_paths[0]
    final_raw = final_path.read_bytes()
    power_final_ref = ArtifactRef(
        role="resampling_power_report",
        relative_path=final_path.relative_to(root).as_posix(),
        sha256=hashlib.sha256(final_raw).hexdigest(),
        byte_count=len(final_raw),
        media_type="application/json",
    )
    prefix_storage_lease = claim_local_test_storage(
        transaction="prefix",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=None,
    )
    schedule_ref = seal_prefix_schedule(
        manifest_ref,
        power_final_ref,
        schedule_seed_reveal=7,
        storage_policy_lease=prefix_storage_lease,
        run_root=root,
        out=root / "prefix-schedule.json",
    )
    old_prefix_payload["schedule_ref"] = asdict(schedule_ref)
    for receipt in cast(
        list[dict[str, object]],
        old_prefix_payload["task_receipts"],
    ):
        receipt["schedule_sha256"] = schedule_ref.sha256
        cast(dict[str, object], receipt["verifier_receipt"])["schedule_sha256"] = (
            schedule_ref.sha256
        )
    prefix_ref_value = _write_test_record(
        root,
        "prefix-receipt.json",
        "resampling_prefix_receipt",
        old_prefix_payload,
    )
    prefix_ref = ArtifactRef(**prefix_ref_value)
    lease = claim_local_test_storage(
        transaction="assignment",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=schedule_ref,
    )
    secret_path = tmp_path / "assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o400)
    store = AssignmentSecretStore(secret_path)
    handle = store.claim_assignment(
        manifest_ref,
        schedule_ref,
        run_root=root,
    )
    prefix_storage_receipt_path = root / "operational/storage-policy/prefix.json"
    prefix_storage_receipt_bytes = prefix_storage_receipt_path.read_bytes()
    forged_prefix_storage_receipt = json.loads(prefix_storage_receipt_bytes)
    forged_prefix_storage_receipt["publication_commit"]["scientific_sha256"] = SHA_A
    prefix_storage_receipt_path.write_bytes(
        canonical_json_bytes(forged_prefix_storage_receipt, indent=None)
    )
    with pytest.raises(RecordValidationError, match="accepted schedule"):
        seal_branch_assignment(
            schedule_ref,
            prefix_ref,
            assignment_secret_handle=handle,
            matching_backend_session=None,
            storage_policy_lease=lease,
            run_root=root,
            out=root / "assignment-ledger.json",
        )
    prefix_storage_receipt_path.write_bytes(prefix_storage_receipt_bytes)
    ledger_ref = seal_branch_assignment(
        schedule_ref,
        prefix_ref,
        assignment_secret_handle=handle,
        matching_backend_session=None,
        storage_policy_lease=lease,
        run_root=root,
        out=root / "assignment-ledger.json",
    )
    ledger = load_record(root / ledger_ref.relative_path)
    payload = cast(dict[str, object], ledger["payload"])
    assert payload["assignment_mode"] == "synthetic_derangement"
    assert payload["matching_proof_refs"] == []
    assert [
        assignment["task_id"]
        for assignment in cast(list[dict[str, object]], payload["assignments"])
    ] == ["task-1", "task-donor"]
    assert all(
        receipt["kind"] == "not_applicable_no_trigger"
        for receipt in cast(
            list[dict[str, object]],
            payload["donor_match_receipts"],
        )
    )
    storage_receipt = json.loads(
        (root / "operational/storage-policy/assignment.json").read_bytes()
    )
    assert (
        storage_receipt["publication_commit"]["scientific_sha256"] == ledger_ref.sha256
    )
    manifest = load_record(root / manifest_ref.relative_path)
    manifest_payload = cast(dict[str, object], manifest["payload"])
    tokenizer_ref = ArtifactRef(
        **cast(dict[str, Any], manifest_payload["tokenizer_ref"])
    )
    packet_template_ref = ArtifactRef(
        **cast(dict[str, Any], manifest_payload["packet_template_ref"])
    )
    packet_policy_ref = ArtifactRef(
        **cast(dict[str, Any], manifest_payload["packet_policy_ref"])
    )
    pad_unit_set_ref = ArtifactRef(
        **cast(dict[str, Any], manifest_payload["pad_unit_set_ref"])
    )
    packet_candidate_ref = write_packet_candidate(
        [
            NoInterventionPacketMarker(
                task_id,
                prefix_ref.sha256,
                "no_intervention_opportunity",
            )
            for task_id in ("task-1", "task-donor")
        ],
        assignment_ref=ledger_ref,
        prefix_index_ref=prefix_ref,
        tokenizer_ref=tokenizer_ref,
        packet_template_ref=packet_template_ref,
        packet_policy_ref=packet_policy_ref,
        pad_unit_set_ref=pad_unit_set_ref,
        run_root=root,
        out=root / "packet-candidate.json",
    )
    with pytest.raises(PacketInvalid, match="roster"):
        audit_and_seal_packet_index(
            packet_candidate_ref,
            expected_task_ids={"task-1"},
            assignment_ref=ledger_ref,
            schedule_ref=schedule_ref,
            prefix_index_ref=prefix_ref,
            tokenizer_ref=tokenizer_ref,
            packet_template_ref=packet_template_ref,
            packet_policy_ref=packet_policy_ref,
            pad_unit_set_ref=pad_unit_set_ref,
            run_root=root,
            out=root / "packet-index-rejected.json",
        )
    sealed_packet_ref = audit_and_seal_packet_index(
        packet_candidate_ref,
        expected_task_ids={"task-1", "task-donor"},
        assignment_ref=ledger_ref,
        schedule_ref=schedule_ref,
        prefix_index_ref=prefix_ref,
        tokenizer_ref=tokenizer_ref,
        packet_template_ref=packet_template_ref,
        packet_policy_ref=packet_policy_ref,
        pad_unit_set_ref=pad_unit_set_ref,
        run_root=root,
        out=root / "packet-index.json",
    )
    assert (
        load_record(root / sealed_packet_ref.relative_path)["payload"]["stage"]
        == "sealed"
    )
    with pytest.raises(ValueError, match="consumed"):
        store._consume_into(handle, bytearray(32))  # type: ignore[arg-type]


def test_t3_s10_triggered_assignment_publishes_one_reachable_cas_proof(
    tmp_path: Path,
) -> None:
    root = tmp_path / "triggered-assignment"
    _build_full_study(
        root,
        completed_power_consumer_fixture=True,
    )
    forbidden = {
        "resampling_assignment_ledger",
        "resampling_packet_index",
        "resampling_task_block",
        "resampling_blinded_projection",
        "resampling_analysis_freeze",
        "resampling_analysis",
        "resampling_unblind_receipt",
        "resampling_artifact_root",
    }
    for path in root.rglob("*.json"):
        try:
            value = json.loads(path.read_bytes())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(value, dict) and value.get("record_kind") in forbidden:
            path.unlink()

    old_manifest = load_record(root / "study-manifest.json")
    manifest_payload = cast(dict[str, object], old_manifest["payload"])
    old_prefix = load_record(root / "prefix-receipt.json")
    old_receipts = cast(
        list[dict[str, object]],
        old_prefix["payload"]["task_receipts"],  # type: ignore[index]
    )
    (root / "study-manifest.json").unlink()
    (root / "prefix-schedule.json").unlink()
    (root / "prefix-receipt.json").unlink()

    third_task = {
        "task_id": "task-third",
        "benchmark": "swe",
        "stratum": "python",
        "lineage": "repo-002",
        "groups": [
            {"kind": "language", "value": "python"},
            {"kind": "domain", "value": "software"},
            {"kind": "issue_family", "value": "bug"},
        ],
        "tiers": [120, 160],
    }
    old_registry = json.loads(
        (
            root
            / cast(dict[str, object], manifest_payload["task_registry_ref"])[
                "relative_path"
            ]
        ).read_bytes()
    )
    old_roster = json.loads(
        (
            root
            / cast(dict[str, object], manifest_payload["roster_ref"])["relative_path"]
        ).read_bytes()
    )
    old_provider = json.loads(
        (
            root
            / cast(
                dict[str, object],
                manifest_payload["provider_lane_plan_ref"],
            )["relative_path"]
        ).read_bytes()
    )
    old_registry["tasks"].append(
        {key: value for key, value in third_task.items() if key != "tiers"}
    )
    old_roster["tasks"].append(third_task)
    registry_ref = _write_blob(
        root,
        "sources/tasks-triggered.json",
        canonical_json_bytes(old_registry, indent=None),
    )
    roster_ref = _write_blob(
        root,
        "sources/roster-triggered.json",
        canonical_json_bytes(old_roster, indent=None),
    )
    template_provider_row = old_provider["task_lanes"][0]
    third_provider_row = {
        "task_id": "task-third",
        "prefix_lane_ordinal": 0,
        "lane_ordinals_by_execution_rank": [0, 1, 2, 3],
    }
    for ref_field in (
        "task_input_ref",
        "environment_contract_ref",
        "grader_contract_ref",
        "verifier_contract_ref",
        "isolation_contract_ref",
    ):
        template_ref = template_provider_row[ref_field]
        template_value = json.loads(
            (root / cast(dict[str, object], template_ref)["relative_path"]).read_bytes()
        )
        template_value["task_id"] = "task-third"
        third_ref = _write_blob(
            root,
            f"sources/authority/task-third-{ref_field}.json",
            canonical_json_bytes(template_value, indent=None),
        )
        third_ref["role"] = cast(dict[str, object], template_ref)["role"]
        third_ref["media_type"] = "application/json"
        third_provider_row[ref_field] = third_ref
    old_provider["task_lanes"].append(third_provider_row)
    provider_ref = _write_blob(
        root,
        "sources/provider-triggered.json",
        canonical_json_bytes(old_provider, indent=None),
    )
    manifest_payload["task_registry_ref"] = registry_ref
    manifest_payload["roster_ref"] = roster_ref
    manifest_payload["provider_lane_plan_ref"] = provider_ref
    manifest_ref_value = _write_test_record(
        root,
        "study-manifest.json",
        "resampling_study_manifest",
        manifest_payload,
    )
    manifest_ref = ArtifactRef(**manifest_ref_value)

    final_paths = [
        path
        for path in (root / "power").glob("*.json")
        if load_record(path)["payload"]["stage"] == "final"  # type: ignore[index]
    ]
    assert len(final_paths) == 1
    final_path = final_paths[0]
    final_raw = final_path.read_bytes()
    power_final_ref = ArtifactRef(
        role="resampling_power_report",
        relative_path=final_path.relative_to(root).as_posix(),
        sha256=hashlib.sha256(final_raw).hexdigest(),
        byte_count=len(final_raw),
        media_type="application/json",
    )
    prefix_storage_lease = claim_local_test_storage(
        transaction="prefix",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=None,
    )
    schedule_ref = seal_prefix_schedule(
        manifest_ref,
        power_final_ref,
        schedule_seed_reveal=7,
        storage_policy_lease=prefix_storage_lease,
        run_root=root,
        out=root / "prefix-schedule.json",
    )

    third_verifier = _write_blob(
        root,
        "sources/verifier-third.json",
        canonical_json_bytes(
            {
                "record_kind": "synthetic_verifier_source_v1",
                "schema_version": "1",
                "task_id": "task-third",
                "benchmark": "swe",
                "components": [
                    {"kind": "check_runner", "value": "pytest", "count": 1},
                    {"kind": "failure_class", "value": "none", "count": 1},
                ],
                "objective_findings": [
                    {
                        "finding_id": "third-finding",
                        "component": "pytest",
                        "code": "charlie",
                        "severity": "high",
                        "atoms": [
                            {"atom_kind": "literal", "text": "inspect "},
                            {
                                "atom_kind": "identifier",
                                "entity_id": "src/third.py",
                                "identifier_kind": "repository_file",
                            },
                        ],
                    }
                ],
            },
            indent=None,
        ),
    )
    third_report = _write_blob(
        root,
        "sources/report-third.json",
        canonical_json_bytes(
            {
                "record_kind": "synthetic_verifier_report_v1",
                "schema_version": "1",
                "task_id": "task-third",
                "report_text": "clean",
            },
            indent=None,
        ),
    )
    third_features = _write_blob(
        root,
        "sources/features-third.json",
        canonical_json_bytes(
            {
                "record_kind": "assignment_verifier_features_v1",
                "schema_version": "1",
                "task_id": "task-third",
                "benchmark": "swe",
                "source_verifier_ref": third_verifier,
                "source_report_ref": third_report,
                "components": [
                    {"kind": "check_runner", "value": "pytest", "count": 1},
                    {"kind": "failure_class", "value": "none", "count": 1},
                ],
                "objective_finding_count": 1,
                "normalized_report_token_count": 1,
            },
            indent=None,
        ),
    )
    packet_feature_refs: dict[str, dict[str, object]] = {"task-third": third_features}
    for packet_task_id, packet_identifier, packet_code in (
        ("task-1", "src/task-one.py", "alpha"),
        ("task-donor", "src/task-donor.py", "bravo"),
    ):
        packet_source = _write_blob(
            root,
            f"sources/verifier-{packet_task_id}-typed.json",
            canonical_json_bytes(
                {
                    "record_kind": "synthetic_verifier_source_v1",
                    "schema_version": "1",
                    "task_id": packet_task_id,
                    "benchmark": "swe",
                    "components": [
                        {"kind": "check_runner", "value": "pytest", "count": 1},
                        {"kind": "failure_class", "value": "none", "count": 1},
                    ],
                    "objective_findings": [
                        {
                            "finding_id": f"finding-{packet_task_id}",
                            "component": "pytest",
                            "code": packet_code,
                            "severity": "high",
                            "atoms": [
                                {"atom_kind": "literal", "text": "inspect "},
                                {
                                    "atom_kind": "identifier",
                                    "entity_id": packet_identifier,
                                    "identifier_kind": "repository_file",
                                },
                            ],
                        }
                    ],
                },
                indent=None,
            ),
        )
        packet_report = _write_blob(
            root,
            f"sources/report-{packet_task_id}-typed.json",
            canonical_json_bytes(
                {
                    "record_kind": "synthetic_verifier_report_v1",
                    "schema_version": "1",
                    "task_id": packet_task_id,
                    "report_text": "clean",
                },
                indent=None,
            ),
        )
        packet_feature_refs[packet_task_id] = _write_blob(
            root,
            f"sources/features-{packet_task_id}-typed.json",
            canonical_json_bytes(
                {
                    "record_kind": "assignment_verifier_features_v1",
                    "schema_version": "1",
                    "task_id": packet_task_id,
                    "benchmark": "swe",
                    "source_verifier_ref": packet_source,
                    "source_report_ref": packet_report,
                    "components": [
                        {"kind": "check_runner", "value": "pytest", "count": 1},
                        {"kind": "failure_class", "value": "none", "count": 1},
                    ],
                    "objective_finding_count": 1,
                    "normalized_report_token_count": 1,
                },
                indent=None,
            ),
        )
    receipts = deepcopy(old_receipts)
    third_receipt = deepcopy(receipts[1])
    third_receipt["task_id"] = "task-third"
    cast(dict[str, object], third_receipt["verifier_receipt"])["task_id"] = "task-third"
    cast(dict[str, object], third_receipt["verifier_receipt"])[
        "verifier_artifact_ref"
    ] = third_features
    cast(dict[str, object], third_receipt["verifier_receipt"])["finding_count"] = 1
    receipts.append(third_receipt)
    for receipt in receipts:
        verifier = cast(dict[str, object], receipt["verifier_receipt"])
        verifier["verifier_artifact_ref"] = packet_feature_refs[
            cast(str, receipt["task_id"])
        ]
        verifier["finding_count"] = 1
        receipt["schedule_sha256"] = schedule_ref.sha256
        receipt["trigger_reason"] = "first_eligible_mutation"
        verifier["schedule_sha256"] = schedule_ref.sha256
    prefix_ref_value = _write_test_record(
        root,
        "prefix-receipt.json",
        "resampling_prefix_receipt",
        {
            "schedule_ref": asdict(schedule_ref),
            "task_receipts": receipts,
        },
    )
    prefix_ref = ArtifactRef(**prefix_ref_value)
    normalized_a = normalize_synthetic_packet_findings(
        ArtifactRef(**third_features),
        task_id="task-third",
        run_root=root,
        out=root / "private-audit/normalized-third-a.json",
    )
    normalized_b = normalize_synthetic_packet_findings(
        ArtifactRef(**third_features),
        task_id="task-third",
        run_root=root,
        out=root / "private-audit/normalized-third-b.json",
    )
    assert normalized_a.sha256 == normalized_b.sha256
    assert (root / normalized_a.relative_path).read_bytes() == (
        root / normalized_b.relative_path
    ).read_bytes()
    normalized_by_task = {"task-third": normalized_a}
    for normalized_task_id in ("task-1", "task-donor"):
        normalized_by_task[normalized_task_id] = normalize_synthetic_packet_findings(
            ArtifactRef(**packet_feature_refs[normalized_task_id]),
            task_id=normalized_task_id,
            run_root=root,
            out=(root / f"private-audit/normalized-{normalized_task_id}.json"),
        )
    assignment_lease = claim_local_test_storage(
        transaction="assignment",
        run_root=root,
        manifest_ref=manifest_ref,
        schedule_ref=schedule_ref,
    )
    secret_path = tmp_path / "triggered-assignment-master.key"
    secret_path.write_bytes(bytes(range(32)))
    secret_path.chmod(0o400)
    store = AssignmentSecretStore(secret_path)
    handle = store.claim_assignment(
        manifest_ref,
        schedule_ref,
        run_root=root,
    )
    ledger_ref = seal_branch_assignment(
        schedule_ref,
        prefix_ref,
        assignment_secret_handle=handle,
        matching_backend_session=None,
        storage_policy_lease=assignment_lease,
        run_root=root,
        out=root / "assignment-ledger.json",
    )
    payload = cast(
        dict[str, object],
        load_record(root / ledger_ref.relative_path)["payload"],
    )
    proof_refs = cast(list[dict[str, object]], payload["matching_proof_refs"])
    assert len(proof_refs) == 1
    proof_ref = ArtifactRef(**proof_refs[0])
    assert proof_ref.relative_path == (f"blobs/matching/proof/{proof_ref.sha256}.json")
    proof = json.loads((root / proof_ref.relative_path).read_bytes())
    assert proof["proof_kind"] == "synthetic_cyclic_offset_v1"
    assert proof["canonical_focal_task_ids"] == [
        "task-1",
        "task-donor",
        "task-third",
    ]
    mapping = dict(proof["donor_by_task"])
    assert (
        set(mapping)
        == set(mapping.values())
        == {
            "task-1",
            "task-donor",
            "task-third",
        }
    )
    assert all(focal != donor for focal, donor in mapping.items())
    donor_receipts = cast(
        list[dict[str, object]],
        payload["donor_match_receipts"],
    )
    assert all(receipt["kind"] == "matched" for receipt in donor_receipts)
    assert all(
        receipt["matching_proof_ref"] == proof_refs[0] for receipt in donor_receipts
    )
    assert all(
        len(cast(list[object], receipt["candidates"])) == 2
        for receipt in donor_receipts
    )
    assignment_storage_receipt_path = (
        root / "operational/storage-policy/assignment.json"
    )
    assignment_storage_receipt_bytes = assignment_storage_receipt_path.read_bytes()
    forged_assignment_storage_receipt = json.loads(assignment_storage_receipt_bytes)
    forged_assignment_storage_receipt["publication_commit"]["scientific_sha256"] = SHA_A
    assignment_storage_receipt_path.write_bytes(
        canonical_json_bytes(
            forged_assignment_storage_receipt,
            indent=None,
        )
    )
    with pytest.raises(RecordValidationError, match="accepted ledger"):
        _require_assignment_publication(
            ledger_ref,
            manifest_ref=manifest_ref,
            schedule_ref=schedule_ref,
            run_root=root,
        )
    assignment_storage_receipt_path.write_bytes(assignment_storage_receipt_bytes)
    _require_assignment_publication(
        ledger_ref,
        manifest_ref=manifest_ref,
        schedule_ref=schedule_ref,
        run_root=root,
    )
    assert (
        verify_synthetic_assignment_graph(
            ledger_ref,
            run_root=root,
        )["payload"]
        == payload
    )
    proof_path = root / proof_ref.relative_path
    proof_bytes = proof_path.read_bytes()
    forged_proof = json.loads(proof_bytes)
    forged_proof["selected_offset"] = 2
    proof_path.write_bytes(canonical_json_bytes(forged_proof, indent=None))
    with pytest.raises(RecordValidationError, match="digest|SHA|bytes"):
        verify_synthetic_assignment_graph(
            ledger_ref,
            run_root=root,
        )
    proof_path.write_bytes(proof_bytes)
    reconstruction_handle = store.claim_assignment(
        manifest_ref,
        schedule_ref,
        run_root=root,
    )
    with pytest.raises(RecordValidationError, match="confirmation ledger"):
        require_confirmation_assignment(
            ledger_ref,
            assignment_secret_handle=reconstruction_handle,
            matching_backend_session=None,
            run_root=root,
        )
    reconstructed = require_assignment_reconstruction(
        ledger_ref,
        assignment_secret_handle=reconstruction_handle,
        matching_backend_session=None,
        run_root=root,
    )
    assert [assignment.task_id for assignment in reconstructed.assignments] == [
        "task-1",
        "task-donor",
        "task-third",
    ]
    assert (
        reconstructed.assignment_prefix_view_sha256
        == payload["assignment_prefix_view_sha256"]
    )
    tokenizer_ref = ArtifactRef(
        **cast(dict[str, Any], manifest_payload["tokenizer_ref"])
    )
    packet_template_ref = ArtifactRef(
        **cast(dict[str, Any], manifest_payload["packet_template_ref"])
    )
    packet_policy_ref = ArtifactRef(
        **cast(dict[str, Any], manifest_payload["packet_policy_ref"])
    )
    pad_unit_set_ref = ArtifactRef(
        **cast(dict[str, Any], manifest_payload["pad_unit_set_ref"])
    )
    identifiers = {
        "task-1": "src/task-one.py",
        "task-donor": "src/task-donor.py",
        "task-third": "src/third.py",
    }
    prefix_verifiers = {
        cast(str, receipt["task_id"]): ArtifactRef(
            **cast(
                dict[str, Any],
                cast(dict[str, object], receipt["verifier_receipt"])[
                    "verifier_artifact_ref"
                ],
            )
        )
        for receipt in receipts
    }
    packet_store = SyntheticPacketArtifactStore(root)
    packet_entries = []
    for assignment in reconstructed.assignments:
        donor_task_id = cast(str, assignment.donor_task_id)
        rewrite_artifacts = derive_packet_rewrite_artifacts(
            {
                IdentifierAtom(
                    identifiers[donor_task_id],
                    IdentifierKind.REPOSITORY_FILE,
                ): IdentifierAtom(
                    identifiers[assignment.task_id],
                    IdentifierKind.REPOSITORY_FILE,
                )
            },
            focal_task_id=assignment.task_id,
            donor_task_id=donor_task_id,
            normalized_real_ref=normalized_by_task[assignment.task_id],
            normalized_donor_ref=normalized_by_task[donor_task_id],
            run_root=root,
            identifier_map_out=(root / f"private-audit/map-{assignment.task_id}.json"),
            normalized_sham_out=(
                root / f"private-audit/sham-{assignment.task_id}.json"
            ),
        )
        packet_entries.append(
            build_packet_pair(
                run_root=root,
                normalized_real_ref=normalized_by_task[assignment.task_id],
                normalized_donor_ref=normalized_by_task[donor_task_id],
                normalized_sham_ref=rewrite_artifacts.normalized_sham_ref,
                artifact_store=packet_store,
                real_relative_path=f"private-packets/{assignment.task_id}-real.txt",
                sham_relative_path=f"private-packets/{assignment.task_id}-sham.txt",
                task_id=assignment.task_id,
                donor_task_id=donor_task_id,
                prefix_index_sha256=prefix_ref.sha256,
                focal_verifier_ref=prefix_verifiers[assignment.task_id],
                donor_verifier_ref=prefix_verifiers[donor_task_id],
                assignment_ref=ledger_ref,
                identifier_map_ref=rewrite_artifacts.identifier_map_ref,
                tokenizer_ref=tokenizer_ref,
                packet_template_ref=packet_template_ref,
                packet_policy_ref=packet_policy_ref,
                pad_unit_set_ref=pad_unit_set_ref,
            )
        )
    candidate_ref = write_packet_candidate(
        packet_entries,
        assignment_ref=ledger_ref,
        prefix_index_ref=prefix_ref,
        tokenizer_ref=tokenizer_ref,
        packet_template_ref=packet_template_ref,
        packet_policy_ref=packet_policy_ref,
        pad_unit_set_ref=pad_unit_set_ref,
        run_root=root,
        out=root / "packet-candidate-triggered.json",
    )
    first_packet_path = root / packet_entries[0].real_ref.relative_path
    first_packet_bytes = first_packet_path.read_bytes()
    first_packet_path.write_bytes(first_packet_bytes + b" ")
    with pytest.raises(PacketInvalid, match="bytes|plaintext"):
        audit_and_seal_packet_index(
            candidate_ref,
            expected_task_ids={"task-1", "task-donor", "task-third"},
            assignment_ref=ledger_ref,
            schedule_ref=schedule_ref,
            prefix_index_ref=prefix_ref,
            tokenizer_ref=tokenizer_ref,
            packet_template_ref=packet_template_ref,
            packet_policy_ref=packet_policy_ref,
            pad_unit_set_ref=pad_unit_set_ref,
            run_root=root,
            out=root / "packet-index-forged.json",
        )
    first_packet_path.write_bytes(first_packet_bytes)
    sealed_packet_ref = audit_and_seal_packet_index(
        candidate_ref,
        expected_task_ids={"task-1", "task-donor", "task-third"},
        assignment_ref=ledger_ref,
        schedule_ref=schedule_ref,
        prefix_index_ref=prefix_ref,
        tokenizer_ref=tokenizer_ref,
        packet_template_ref=packet_template_ref,
        packet_policy_ref=packet_policy_ref,
        pad_unit_set_ref=pad_unit_set_ref,
        run_root=root,
        out=root / "packet-index-triggered.json",
    )
    assert (
        load_record(root / sealed_packet_ref.relative_path)["payload"]["stage"]
        == "sealed"
    )

    forged_ledger = load_record(root / ledger_ref.relative_path)
    forged_payload = cast(dict[str, object], forged_ledger["payload"])
    forged_allocations = cast(
        list[dict[str, object]],
        forged_payload["allocation_receipts"],
    )
    forged_capabilities = cast(
        list[list[str]],
        forged_allocations[0]["slot_capabilities"],
    )
    forged_capabilities[0][1] = (
        "0" if forged_capabilities[0][1][0] != "0" else "1"
    ) + forged_capabilities[0][1][1:]
    forged_bytes = canonical_json_bytes(forged_ledger, indent=2)
    (root / ledger_ref.relative_path).write_bytes(forged_bytes)
    forged_ledger_ref = ArtifactRef(
        role=ledger_ref.role,
        relative_path=ledger_ref.relative_path,
        sha256=hashlib.sha256(forged_bytes).hexdigest(),
        byte_count=len(forged_bytes),
        media_type=ledger_ref.media_type,
    )
    forged_handle = store.claim_assignment(
        manifest_ref,
        schedule_ref,
        run_root=root,
    )
    with pytest.raises(RecordValidationError, match="keyed|reconstruction"):
        require_assignment_reconstruction(
            forged_ledger_ref,
            assignment_secret_handle=forged_handle,
            matching_backend_session=None,
            run_root=root,
        )


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


def _power_payload(
    stage: str,
    *,
    shard_index: int | None = None,
    phase: str = "gaussian_approximation",
) -> dict[str, object]:
    parent_refs = [] if stage == "screen" else [_ref("parents/power-parent.json")]
    base: dict[str, object] = {
        "stage": stage,
        "authority_ref": _ref(
            "parents/power-authority.json",
            role="power_authority",
        ),
        "decision_authority": "synthetic_validation",
        "phase": phase,
        "generation": 0,
        "roster_ref": _ref("parents/roster.json", role="roster"),
        "tier_membership_sha256": SHA_A,
        "grid_ref": _ref("parents/grid.json", role="grid"),
        "screen_topology_ref": _ref(
            "parents/topology.json",
            role="topology",
        ),
        "rng_contract_sha256": SHA_B,
        "parent_refs": parent_refs,
        "config_ref": _ref("parents/power-config.json", role="power_config"),
        "numeric_fixture_ref": _ref(
            "parents/numeric-fixture.json",
            role="numeric_fixture",
        ),
        "numeric_contract": _numeric_contract(),
    }
    if stage != "final":
        base["kernel_id"] = _T3_S02_POWER_KERNEL_IDS[(stage, phase)]
        base["shard_count"] = 2
    if stage == "screen":
        base.update(projected_wall_seconds=1, cell_count=1, dataset_count=200)
        if phase == "full_multiplier_fallback":
            fallback_trigger_ref = _ref(
                "power/failed-gaussian-validation.json",
                role="fallback_trigger",
            )
            base["fallback_trigger_ref"] = fallback_trigger_ref
            base["parent_refs"] = [fallback_trigger_ref]
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
    elif stage == "validation" and phase == "gaussian_approximation":
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
    elif stage == "validation":
        fallback_trigger_ref = _ref(
            "power/failed-gaussian-validation.json",
            role="fallback_trigger",
        )
        base.update(
            fallback_trigger_ref=fallback_trigger_ref,
            complete_cell_ids=["cell-0"],
            expected_cell_count=1,
            observed_cell_count=1,
            raw_counts_ref=_ref(
                "power/raw-counts.json",
                role="raw_counts",
            ),
            numeric_receipt_ref=_ref(
                "power/numeric-receipt.json",
                role="numeric_receipt",
            ),
            selected_tier=None,
            decision="CONDITIONAL_ONLY",
        )
    elif stage == "final":
        attempt_refs = [
            _ref(f"power/attempt-{index}.json", role="power_attempt")
            for index in range(4)
        ]
        base.update(
            all_attempt_refs=attempt_refs,
            finalization={
                "kind": "synthetic_validation_failed",
                "terminal_attempt_ref": attempt_refs[0],
                "terminal_stage": "screen",
                "terminal_phase": phase,
                "terminal_kernel_id": _T3_S02_POWER_KERNEL_IDS[("final", phase)],
                "terminal_shard_count": 2,
                "reason": (
                    "gaussian_screen_exhausted"
                    if phase == "gaussian_approximation"
                    else "full_multiplier_screen_exhausted"
                ),
                "selected_tier": None,
                "decision": "CONDITIONAL_ONLY",
            },
        )
    return base


_T3_S02_POWER_KERNEL_IDS = {
    ("screen", "gaussian_approximation"): "power-screen-gaussian-v1",
    ("shard", "gaussian_approximation"): "power-grid-gaussian-v1",
    (
        "selection",
        "gaussian_approximation",
    ): "power-worst-five-selection-v1",
    (
        "validation",
        "gaussian_approximation",
    ): "power-gaussian-vs-multiplier-validation-v1",
    ("final", "gaussian_approximation"): "power-final-gaussian-v1",
    (
        "screen",
        "full_multiplier_fallback",
    ): "power-screen-full-multiplier-v1",
    (
        "shard",
        "full_multiplier_fallback",
    ): "power-grid-full-multiplier-v1",
    (
        "validation",
        "full_multiplier_fallback",
    ): "power-full-grid-validation-v1",
    (
        "final",
        "full_multiplier_fallback",
    ): "power-final-full-multiplier-v1",
}


def _t3_s02_power_payload(
    stage: str,
    *,
    phase: str = "gaussian_approximation",
) -> dict[str, object]:
    return _power_payload(stage, phase=phase)


@pytest.mark.parametrize(
    ("stage", "phase"),
    list(_T3_S02_POWER_KERNEL_IDS),
)
def test_t3_s02_power_accepts_exact_authority_bound_stage_arms(
    stage: str,
    phase: str,
) -> None:
    validate_record(
        _record(
            "resampling_power_report",
            _t3_s02_power_payload(stage, phase=phase),
        )
    )


@pytest.mark.parametrize(
    "field",
    [
        "authority_ref",
        "tier_membership_sha256",
        "screen_topology_ref",
        "rng_contract_sha256",
        "kernel_id",
        "shard_count",
    ],
)
def test_t3_s02_power_nonfinal_requires_every_authority_mirror(
    field: str,
) -> None:
    payload = _t3_s02_power_payload("screen")
    del payload[field]
    with pytest.raises(
        RecordValidationError,
        match="(?i)(required|authority|membership|topology|rng|kernel|shard)",
    ):
        validate_record(_record("resampling_power_report", payload))


def test_t3_s02_power_rejects_stale_topology_alias() -> None:
    payload = _t3_s02_power_payload("screen")
    payload["topology_ref"] = payload["screen_topology_ref"]
    with pytest.raises(
        RecordValidationError,
        match="(?i)(additional|topology|property)",
    ):
        validate_record(_record("resampling_power_report", payload))


@pytest.mark.parametrize(
    ("stage", "phase"),
    [pair for pair in _T3_S02_POWER_KERNEL_IDS if pair[0] != "final"],
)
def test_t3_s02_power_rejects_wrong_stage_phase_kernel(
    stage: str,
    phase: str,
) -> None:
    payload = _t3_s02_power_payload(stage, phase=phase)
    payload["kernel_id"] = "power-final-gaussian-v1"
    with pytest.raises(
        RecordValidationError,
        match="(?i)(kernel|const|expected|valid)",
    ):
        validate_record(_record("resampling_power_report", payload))


def test_t3_s02_power_forbids_fallback_selection() -> None:
    payload = _t3_s02_power_payload("selection")
    payload["phase"] = "full_multiplier_fallback"
    payload["kernel_id"] = "power-grid-full-multiplier-v1"
    with pytest.raises(
        RecordValidationError,
        match="(?i)(phase|selection|const|valid)",
    ):
        validate_record(_record("resampling_power_report", payload))


def test_t3_s02_power_screen_trigger_is_phase_discriminated() -> None:
    gaussian = _t3_s02_power_payload("screen")
    gaussian["fallback_trigger_ref"] = _ref("power/fabricated-trigger.json")
    with pytest.raises(
        RecordValidationError,
        match="(?i)(fallback|trigger|additional|property)",
    ):
        validate_record(_record("resampling_power_report", gaussian))

    fallback = _t3_s02_power_payload(
        "screen",
        phase="full_multiplier_fallback",
    )
    del fallback["fallback_trigger_ref"]
    with pytest.raises(
        RecordValidationError,
        match="(?i)(fallback|trigger|required)",
    ):
        validate_record(_record("resampling_power_report", fallback))


@pytest.mark.parametrize("phase", list({pair[1] for pair in _T3_S02_POWER_KERNEL_IDS}))
def test_t3_s02_power_final_accepts_synthetic_failure_arm(phase: str) -> None:
    validate_record(
        _record(
            "resampling_power_report",
            _t3_s02_power_payload("final", phase=phase),
        )
    )


@pytest.mark.parametrize(
    ("phase", "identity_field"),
    [
        ("gaussian_approximation", "terminal_phase"),
        ("gaussian_approximation", "terminal_kernel_id"),
        ("gaussian_approximation", "terminal_shard_count"),
        ("full_multiplier_fallback", "terminal_phase"),
        ("full_multiplier_fallback", "terminal_kernel_id"),
        ("full_multiplier_fallback", "terminal_shard_count"),
    ],
)
def test_t3_s02_power_failed_finalization_requires_terminal_identity(
    phase: str,
    identity_field: str,
) -> None:
    payload = _t3_s02_power_payload("final", phase=phase)
    finalization = cast(dict[str, object], payload["finalization"])
    del finalization[identity_field]
    with pytest.raises(
        RecordValidationError,
        match="(?i)(terminal|phase|kernel|shard|required)",
    ):
        validate_record(_record("resampling_power_report", payload))


@pytest.mark.parametrize(
    ("phase", "identity_field"),
    [
        ("gaussian_approximation", "selected_kernel_id"),
        ("gaussian_approximation", "selected_shard_count"),
        ("full_multiplier_fallback", "selected_kernel_id"),
        ("full_multiplier_fallback", "selected_shard_count"),
    ],
)
def test_t3_s02_power_completed_finalization_requires_selected_identity(
    phase: str,
    identity_field: str,
) -> None:
    payload = _t3_s02_power_payload("final", phase=phase)
    attempt_refs = cast(list[dict[str, object]], payload["all_attempt_refs"])
    common = {
        "kind": "completed_chain",
        "selected_phase": phase,
        "selected_generation": 0,
        "selected_kernel_id": _T3_S02_POWER_KERNEL_IDS[("final", phase)],
        "selected_shard_count": 2,
        "selected_screen_ref": attempt_refs[0],
        "selected_shard_refs": [attempt_refs[1]],
        "selected_tier": None,
        "decision": "CONDITIONAL_ONLY",
    }
    if phase == "gaussian_approximation":
        common.update(
            selected_selection_ref=attempt_refs[2],
            selected_validation_ref=attempt_refs[3],
        )
    else:
        common.update(
            fallback_trigger_ref=attempt_refs[0],
            full_grid_validation_ref=attempt_refs[3],
        )
    payload["finalization"] = common
    validate_record(_record("resampling_power_report", payload))
    del common[identity_field]
    with pytest.raises(
        RecordValidationError,
        match="(?i)(selected|kernel|shard|required)",
    ):
        validate_record(_record("resampling_power_report", payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("alternative_pass_count", 20_001),
        ("null_pass_count", 20_001),
        ("alternative_trial_count", 19_999),
        ("null_trial_count", 19_999),
    ],
)
def test_power_shard_rejects_impossible_or_mismatched_counts(
    field: str,
    value: int,
) -> None:
    payload = _power_payload("shard")
    payload["cell_results"] = [_cell_result("cell-0")]
    payload["cell_results"][0][field] = value  # type: ignore[index]
    with pytest.raises(
        RecordValidationError,
        match="(?i)(pass|trial|dataset|count)",
    ):
        validate_record(_record("resampling_power_report", payload))


def test_power_shard_accepts_zero_and_all_pass_boundaries() -> None:
    payload = _power_payload("shard")
    result = _cell_result("cell-0")
    result["alternative_pass_count"] = 0
    result["null_pass_count"] = result["null_trial_count"]
    payload["cell_results"] = [result]
    validate_record(_record("resampling_power_report", payload))


@pytest.mark.parametrize(
    "field",
    [
        "alternative_pass_count",
        "alternative_trial_count",
        "null_pass_count",
        "null_trial_count",
    ],
)
def test_power_shard_count_fields_forbid_booleans(field: str) -> None:
    payload = _power_payload("shard")
    payload["cell_results"] = [_cell_result("cell-0")]
    payload["cell_results"][0][field] = True  # type: ignore[index]
    with pytest.raises(
        RecordValidationError,
        match="(?i)(integer|boolean|valid)",
    ):
        validate_record(_record("resampling_power_report", payload))


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
        "authority_ref",
        "roster_ref",
        "grid_ref",
        "screen_topology_ref",
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


def test_task_write_rejects_forged_direct_parent_semantics(tmp_path: Path) -> None:
    root = tmp_path / "run"
    _build_full_study(root)
    task_record = load_record(root / "task-1.json")
    task_payload = cast(dict[str, object], task_record["payload"])
    task_payload["stratum"] = "forged"
    out = root / "forged-task.json"

    with pytest.raises(
        RecordValidationError,
        match="(?i)(task|schedule|stratum|ancestry)",
    ):
        write_record(
            out,
            task_record,
            run_root=root,
            role="task_block",
        )
    assert not out.exists()


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
        "storage-policy",
        "power-grid",
        "power-topology",
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
                {
                    "commitment_scheme": "resampling-null-key-ceremony-v1",
                    "roster_local_nonce_commitment_sha256": SHA_A,
                    "schedule_seed_commitment_sha256": SHA_A,
                    "assignment_master_key_commitment_sha256": SHA_A,
                },
            )
        ),
        encoding="utf-8",
    )
    run_root = tmp_path / "run"
    run_root.mkdir()

    import time

    monkeypatch.setattr(
        time, "time", lambda: (_ for _ in ()).throw(AssertionError("clock"))
    )
    manifest_ref = seal_study_manifest(
        study,
        sources["tasks"],
        sources["roster"],
        sources["assignment"],
        sources["provider"],
        sources["storage-policy"],
        sources["power-grid"],
        sources["power-topology"],
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
    payload = cast(dict[str, object], manifest["payload"])
    for key in (
        "task_registry_ref",
        "roster_ref",
        "assignment_program_ref",
        "provider_lane_plan_ref",
        "storage_policy_contract_ref",
        "power_grid_ref",
        "power_screen_topology_ref",
        "tokenizer_ref",
        "packet_template_ref",
        "packet_policy_ref",
        "pad_unit_set_ref",
        "required_document_kinds_ref",
    ):
        source_ref = cast(dict[str, object], payload[key])
        assert (run_root / cast(str, source_ref["relative_path"])).is_file()
    assert len(cast(list[object], payload["source_revision_refs"])) == 2
    assert payload["eligibility_manifest_ref"] is None
    assert payload["roster_ceremony_policy_ref"] is None
    assert payload["commitment_scheme"] == "resampling-null-key-ceremony-v1"
    assert payload["roster_local_nonce_commitment_sha256"] == SHA_A
    assert payload["schedule_seed_commitment_sha256"] == SHA_A
    assert payload["assignment_master_key_commitment_sha256"] == SHA_A
    assert manifest["frozen_created_at"] == FROZEN


@pytest.mark.parametrize(
    "failure_mode",
    [
        None,
        "binding",
        "synthetic_meter",
        "authority_mismatch",
        "confirmation_missing",
        "confirmation_conditional",
        "synthetic_conditional",
    ],
)
def test_t5_s02a_study_seal_copies_v2_provider_nested_refs_atomically(
    tmp_path: Path,
    failure_mode: str | None,
) -> None:
    fixture = ProviderAuthorityFixture.build_study(
        tmp_path,
        failure_mode=failure_mode,
    )
    run_root = fixture.run_root
    seal = fixture.seal

    if failure_mode in {
        "binding",
        "synthetic_meter",
        "authority_mismatch",
        "confirmation_missing",
        "synthetic_conditional",
    }:
        message_by_mode = {
            "binding": "benchmark",
            "synthetic_meter": "zero-cost synthetic",
            "authority_mismatch": "authority disagree",
            "confirmation_missing": "confirmation.*requires.*eligibility",
            "synthetic_conditional": "synthetic.*forbids.*eligibility",
        }
        message = message_by_mode[failure_mode]
        with pytest.raises(RecordValidationError, match=message):
            seal()
        assert list(run_root.iterdir()) == []
        return
    manifest_ref = seal()
    assert (run_root / manifest_ref.relative_path).is_file()
    if failure_mode == "confirmation_conditional":
        manifest_payload = load_record(run_root / manifest_ref.relative_path)["payload"]
        assert isinstance(manifest_payload, dict)
        assert manifest_payload["eligibility_manifest_ref"] is not None
        assert manifest_payload["roster_ceremony_policy_ref"] is not None
    for ref in fixture.nested_refs:
        assert (run_root / cast(str, ref["relative_path"])).is_file()


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
                {
                    "commitment_scheme": "resampling-null-key-ceremony-v1",
                    "roster_local_nonce_commitment_sha256": SHA_A,
                    "schedule_seed_commitment_sha256": SHA_A,
                    "assignment_master_key_commitment_sha256": SHA_A,
                },
            )
        ),
        encoding="utf-8",
    )
    root = tmp_path / "run"
    root.mkdir()

    def seal_with_revisions(revisions: Sequence[Path]) -> None:
        seal_study_manifest(
            study_source=study,
            tasks_source=source,
            roster_source=source,
            assignment_program_source=source,
            provider_lane_plan_source=source,
            storage_policy_contract_source=source,
            power_grid_source=source,
            power_screen_topology_source=source,
            tokenizer_source=source,
            packet_template_source=source,
            packet_policy_source=source,
            pad_unit_set_source=source,
            source_revision_sources=revisions,
            required_document_kinds_source=source,
            run_root=root,
            out=root / "study-manifest.json",
        )

    with pytest.raises(ValueError, match="non-empty"):
        seal_with_revisions([])
    z = tmp_path / "z.json"
    a = tmp_path / "a.json"
    z.write_text("{}", encoding="utf-8")
    a.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="sorted"):
        seal_with_revisions([z, a])


def test_artifact_root_follows_raw_refs_and_detects_byte_changes(
    tmp_path: Path,
) -> None:
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
    if variant == "conflicting-ref":
        with pytest.raises(RecordValidationError):
            _build_full_study(root, variant=variant)
        return
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


def test_no_trigger_task_block_rejects_forged_positive_y0_outcomes() -> None:
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
    payload = _no_trigger_task_block_payload(refs)
    for outcome in cast(
        list[dict[str, object]],
        payload["slot_outcomes"],
    ):
        outcome["success"] = 1
        outcome["prefix_success"] = 1
        outcome["partial_reward"] = 1.0

    with pytest.raises(
        RecordValidationError,
        match="(?i)(prefix|Y_0|outcome|success)",
    ):
        validate_record(_record("resampling_task_block", payload))


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
                "generated_tokens": 0,
                "model_calls": 0,
                "tool_calls": 0,
                "wall_clock_ms": 0,
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
                "success": payload["slot_outcomes"][index]["success"],  # type: ignore[index]
                "partial_reward": payload["slot_outcomes"][index][  # type: ignore[index]
                    "partial_reward"
                ],
                "infrastructure_failure": payload["slot_outcomes"][index][  # type: ignore[index]
                    "infrastructure_failure"
                ],
                "artifact_ref": deepcopy(
                    payload["slot_outcomes"][index]["artifact_ref"]  # type: ignore[index]
                ),
            },
            "outcome": deepcopy(payload["slot_outcomes"][index]),  # type: ignore[index]
        }
        for index in range(4)
    ]
    return payload


def test_triggered_task_block_binds_outcome_prefix_to_frozen_prefix() -> None:
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
    payload["slot_outcomes"][0]["prefix_success"] = 1  # type: ignore[index]
    payload["execution_receipts"][0]["outcome"]["prefix_success"] = 1  # type: ignore[index]

    with pytest.raises(
        RecordValidationError,
        match="(?i)(prefix|outcome|success)",
    ):
        validate_record(_record("resampling_task_block", payload))


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

    with pytest.raises(
        RecordValidationError, match="(?i)(causal|receipt|outcome|slot)"
    ):
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
    payload["terminal_slot_receipts"] = deepcopy(second_attempt["terminal_receipts"])
    execution_receipts = cast(
        list[dict[str, object]],
        payload["execution_receipts"],
    )
    second_terminal_receipts = cast(
        list[dict[str, object]],
        second_attempt["terminal_receipts"],
    )
    payload["execution_receipts"] = [
        {
            **deepcopy(receipt),
            "source_receipt_sha256": canonical_digest(second_terminal_receipts[index]),
        }
        for index, receipt in enumerate(execution_receipts)
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


def _failed_second_task_block_payload(
    refs: dict[str, dict[str, object]],
) -> dict[str, object]:
    payload = _triggered_task_block_payload(refs)
    first_attempt = deepcopy(payload["attempts"][0])  # type: ignore[index]
    first_attempt["terminal_receipts"] = first_attempt["terminal_receipts"][:2]
    first_attempt["complete"] = False
    second_attempt = deepcopy(payload["attempts"][0])  # type: ignore[index]
    second_attempt["attempt_index"] = 1
    second_attempt["attempt_ref"] = _ref("attempts/attempt-1.json")
    second_attempt["terminal_receipts"] = second_attempt["terminal_receipts"][:1]
    second_attempt["complete"] = False
    payload["attempts"] = [first_attempt, second_attempt]
    payload["selected_attempt_index"] = 1
    payload["outage_receipt"] = {
        "task_id": "task-1",
        "provider_event_ref": _ref("events/provider-outage.json"),
        "first_attempt": deepcopy(first_attempt),
        "detected_before_endpoint_readable": True,
        "work_order_sha256s": deepcopy(first_attempt["work_order_sha256s"]),
        "rerun_index": 1,
    }
    failed_receipts = [
        {
            "slot_id": f"slot-{index}",
            "opaque_capability_id": f"opaque-{index}",
            "failed_attempt_ref": deepcopy(second_attempt["attempt_ref"]),
            "adverse_event_ref": _ref(f"events/adverse-{index}.json"),
            "provider_cost_ref": _ref(f"costs/failed-{index}.json"),
            "failure_kind": "infrastructure",
            "endpoint_readable": False,
        }
        for index in range(4)
    ]
    outcomes = [
        {
            "task_id": "task-1",
            "benchmark": "swe",
            "opaque_arm_id": f"opaque-{index}",
            "success": 0,
            "prefix_success": 0,
            "partial_reward": 0.0,
            "infrastructure_failure": True,
            "counters": {
                "generated_tokens": 0,
                "model_calls": 0,
                "tool_calls": 0,
                "wall_clock_ms": 0,
            },
            "artifact_ref": deepcopy(receipt["adverse_event_ref"]),
        }
        for index, receipt in enumerate(failed_receipts)
    ]
    payload["terminal_slot_receipts"] = failed_receipts
    payload["slot_outcomes"] = deepcopy(outcomes)
    payload["execution_receipts"] = [
        {
            "source_receipt_sha256": canonical_digest(failed_receipts[index]),
            "source_kind": "failed_second_attempt",
            "grade_receipt": None,
            "outcome": deepcopy(outcome),
        }
        for index, outcome in enumerate(outcomes)
    ]
    return payload


def test_partial_attempt_accepts_canonical_nonprefix_slot_subset() -> None:
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
    attempts = cast(list[dict[str, object]], payload["attempts"])
    completed_receipts = cast(
        list[dict[str, object]],
        attempts[1]["terminal_receipts"],
    )
    attempts[0]["terminal_receipts"] = [deepcopy(completed_receipts[2])]
    outage = cast(dict[str, object], payload["outage_receipt"])
    outage["first_attempt"] = deepcopy(attempts[0])
    validate_record(_record("resampling_task_block", payload))


def test_failed_second_attempt_is_a_closed_adverse_zero_branch() -> None:
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
    payload = _failed_second_task_block_payload(refs)
    validate_record(_record("resampling_task_block", payload))


@pytest.mark.parametrize(
    "mutation",
    [
        "selected-attempt",
        "complete-second",
        "mixed-terminal-kind",
        "failed-attempt-ref",
        "source-digest",
        "nonzero-success",
        "nonzero-partial",
        "not-infrastructure",
        "nonzero-counters",
        "wrong-artifact",
        "second-partial-slot",
    ],
)
def test_failed_second_attempt_rejects_frankenstein_finalization(
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
    payload = _failed_second_task_block_payload(refs)
    if mutation == "selected-attempt":
        payload["selected_attempt_index"] = 0
    elif mutation == "complete-second":
        attempts = cast(list[dict[str, object]], payload["attempts"])
        first_terminal_receipts = cast(
            list[dict[str, object]],
            attempts[0]["terminal_receipts"],
        )
        attempts[1]["terminal_receipts"] = deepcopy(first_terminal_receipts) * 2
        attempts[1]["complete"] = True
    elif mutation == "mixed-terminal-kind":
        payload["terminal_slot_receipts"][0] = deepcopy(  # type: ignore[index]
            payload["attempts"][0]["terminal_receipts"][0]  # type: ignore[index]
        )
    elif mutation == "failed-attempt-ref":
        payload["terminal_slot_receipts"][0]["failed_attempt_ref"] = deepcopy(  # type: ignore[index]
            payload["attempts"][0]["attempt_ref"]  # type: ignore[index]
        )
    elif mutation == "source-digest":
        payload["execution_receipts"][0]["source_receipt_sha256"] = SHA_A  # type: ignore[index]
    elif mutation == "nonzero-success":
        payload["slot_outcomes"][0]["success"] = 1  # type: ignore[index]
        payload["execution_receipts"][0]["outcome"]["success"] = 1  # type: ignore[index]
    elif mutation == "nonzero-partial":
        payload["slot_outcomes"][0]["partial_reward"] = 0.5  # type: ignore[index]
        payload["execution_receipts"][0]["outcome"]["partial_reward"] = 0.5  # type: ignore[index]
    elif mutation == "not-infrastructure":
        payload["slot_outcomes"][0]["infrastructure_failure"] = False  # type: ignore[index]
        payload["execution_receipts"][0]["outcome"][  # type: ignore[index]
            "infrastructure_failure"
        ] = False
    elif mutation == "nonzero-counters":
        payload["slot_outcomes"][0]["counters"]["model_calls"] = 1  # type: ignore[index]
        payload["execution_receipts"][0]["outcome"]["counters"][  # type: ignore[index]
            "model_calls"
        ] = 1
    elif mutation == "wrong-artifact":
        payload["slot_outcomes"][0]["artifact_ref"] = _ref("wrong.json")  # type: ignore[index]
        payload["execution_receipts"][0]["outcome"]["artifact_ref"] = _ref(  # type: ignore[index]
            "wrong.json"
        )
    else:
        payload["attempts"][1]["terminal_receipts"][0][  # type: ignore[index]
            "opaque_capability_id"
        ] = "opaque-x"
    with pytest.raises(
        RecordValidationError,
        match=(
            "(?i)(failed|second|adverse|zero|attempt|terminal|slot|receipt|"
            "infrastructure)"
        ),
    ):
        validate_record(_record("resampling_task_block", payload))


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
    with pytest.raises(
        RecordValidationError,
        match="(?i)(schedule|roster|task)",
    ):
        _build_full_study(other, variant="extra-task")


def test_artifact_root_rejects_rewired_forged_prefix_y0_chain(
    tmp_path: Path,
) -> None:
    root = tmp_path / "forged-prefix-y0"
    study = _build_full_study(root)
    alternate_ref = cast(dict[str, object], study["raws"])["alternate"]

    def forge_task(payload: dict[str, object]) -> None:
        payload["prefix_success"] = 1
        for outcome in cast(
            list[dict[str, object]],
            payload["slot_outcomes"],
        ):
            outcome["success"] = 1
            outcome["prefix_success"] = 1
            outcome["partial_reward"] = 1.0
            outcome["artifact_ref"] = alternate_ref

    task_ref = _force_replace_test_record(root, "task-1.json", forge_task)
    forged_task = load_record(root / "task-1.json")
    forged_task_payload = cast(dict[str, object], forged_task["payload"])

    def forge_projection(payload: dict[str, object]) -> None:
        current_refs = cast(
            list[dict[str, object]],
            payload["task_block_refs"],
        )
        payload["task_block_refs"] = [task_ref, current_refs[1]]
        row = cast(list[dict[str, object]], payload["rows"])[0]
        row["prefix_success"] = 1
        for index, slot in enumerate(cast(list[dict[str, object]], row["slots"])):
            slot["outcome"] = deepcopy(
                cast(list[dict[str, object]], forged_task_payload["slot_outcomes"])[
                    index
                ]
            )

    projection_ref = _replace_test_record(
        root,
        "projection.json",
        forge_projection,
    )

    def rewire_unblind(payload: dict[str, object]) -> None:
        payload["projection_ref"] = projection_ref

    unblind_ref = _replace_test_record(
        root,
        "unblind.json",
        rewire_unblind,
    )

    def rewire_analysis(payload: dict[str, object]) -> None:
        payload["projection_ref"] = projection_ref
        payload["unblind_receipt_ref"] = unblind_ref

    _replace_test_record(root, "analysis.json", rewire_analysis)

    with pytest.raises(
        RecordValidationError,
        match="(?i)(prefix|Y_0|task|projection|receipt)",
    ):
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
        "task-schedule-metadata",
        "prefix-trigger-state",
        "task-assignment-capability",
        "projection-row-reconstruction",
    ],
)
def test_artifact_root_rejects_cross_record_semantic_drift(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / variant
    with pytest.raises(
        RecordValidationError,
        match=(
            "(?i)(schedule|prefix|trigger|assignment|capability|projection|"
            "metadata|row|task)"
        ),
    ):
        _build_full_study(root, variant=variant)
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


@pytest.mark.parametrize(
    ("packet_pair", "failed_second_task"),
    [(True, False), (False, True)],
    ids=["completed-attempt", "failed-second-attempt"],
)
def test_artifact_root_rejects_task_slot_identity_drift(
    tmp_path: Path,
    packet_pair: bool,
    failed_second_task: bool,
) -> None:
    root = tmp_path / ("failed-second-slot" if failed_second_task else "completed-slot")
    with pytest.raises(
        RecordValidationError,
        match="(?i)(schedule|assignment|slot|task)",
    ):
        _build_full_study(
            root,
            variant="task-assignment-slot",
            packet_pair=packet_pair,
            failed_second_task=failed_second_task,
        )
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_task_write_rejects_triggered_no_intervention_marker(
    tmp_path: Path,
) -> None:
    root = tmp_path / "triggered-marker"
    with pytest.raises(
        RecordValidationError,
        match="(?i)(packet|trigger|intervention|task)",
    ):
        _build_full_study(root, variant="triggered-marker")
    assert not (root / "task-1.json").exists()


def test_task_write_rejects_forged_packet_parent_ancestry(
    tmp_path: Path,
) -> None:
    root = tmp_path / "forged-packet-parent"
    with pytest.raises(
        RecordValidationError,
        match="(?i)(packet|verifier|parent|ancestry)",
    ):
        _build_full_study(
            root,
            variant="packet-focal-verifier",
            packet_pair=True,
        )
    assert not (root / "task-1.json").exists()


def test_artifact_root_rejects_schedule_roster_subset(tmp_path: Path) -> None:
    root = tmp_path / "schedule-roster-subset"
    _build_full_study(root, variant="schedule-roster-subset")
    with pytest.raises(
        RecordValidationError,
        match="(?i)(schedule|roster|coverage|task)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
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
        "power-authority-ref-drift",
        "power-membership-drift",
        "power-rng-drift",
        "power-screen-topology-drift",
        "power-authority-label-drift",
        "power-shard-count-mirror-drift",
        "power-selected-shard-count-drift",
    ],
)
def test_t3_s02_power_chain_rejects_authority_or_identity_drift(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / variant
    _build_full_study(root, variant=variant)
    with pytest.raises(
        RecordValidationError,
        match="(?i)(power|authority|membership|rng|topology|shard|identity)",
    ):
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
        "power-terminal-phase-drift",
        "power-terminal-kernel-drift",
        "power-terminal-count-drift",
    ],
)
def test_t3_s02_power_no_go_rejects_terminal_identity_drift(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / variant
    _build_full_study(
        root,
        variant=variant,
        no_go_stage="screen",
        decision_authority="roster_bound_selection",
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(terminal|phase|kernel|shard|power|identity)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


@pytest.mark.parametrize(
    ("terminal_stage", "reason"),
    [
        ("screen", None),
        ("validation", "synthetic_validation_gate_failed"),
    ],
)
def test_t3_s02_synthetic_failure_chain_is_authority_bound(
    tmp_path: Path,
    terminal_stage: str,
    reason: str | None,
) -> None:
    root = tmp_path / f"synthetic-validation-failed-{terminal_stage}"
    _build_full_study(
        root,
        no_go_stage=terminal_stage,
        no_go_reason=reason,
        decision_authority="synthetic_validation",
    )
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()


def test_t3_s02_synthetic_validation_reason_requires_validation_terminal(
    tmp_path: Path,
) -> None:
    root = tmp_path / "synthetic-validation-reason-at-screen"
    _build_full_study(
        root,
        no_go_stage="screen",
        no_go_reason="synthetic_validation_gate_failed",
        decision_authority="synthetic_validation",
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(reason|stage|terminal|validation)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_artifact_root_rejects_inconsistent_power_shard_dataset_counts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "shard-dataset-count-mismatch"
    _build_full_study(root, variant="power-shard-dataset-count")
    with pytest.raises(
        RecordValidationError,
        match="(?i)(dataset|shard|count)",
    ):
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
    with pytest.raises(RecordValidationError, match="(?i)(ancestry|ref|hash|source)"):
        _build_full_study(root, variant=variant)
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_packet_pair_verifier_ancestry_seals_exact_prefix_artifacts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "packet-pair"
    _build_full_study(root, packet_pair=True)
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()


@pytest.mark.parametrize(
    "variant",
    [
        "packet-focal-verifier",
        "packet-donor-verifier",
        "packet-pair-task-id",
        "packet-pair-donor-id",
        "packet-prefix-coverage",
    ],
)
def test_packet_pair_rejects_substituted_or_uncovered_verifier_ancestry(
    tmp_path: Path,
    variant: str,
) -> None:
    root = tmp_path / variant
    with pytest.raises(
        RecordValidationError,
        match="(?i)(packet|verifier|prefix|task|donor|coverage)",
    ):
        _build_full_study(root, variant=variant, packet_pair=True)
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


@pytest.mark.parametrize(
    ("decision_authority", "fallback"),
    [
        ("synthetic_validation", False),
        ("synthetic_validation", True),
        ("roster_bound_selection", False),
        ("roster_bound_selection", True),
    ],
)
def test_power_completed_chain_has_authority_bound_success_verdict(
    tmp_path: Path,
    decision_authority: str,
    fallback: bool,
) -> None:
    root = tmp_path / f"{decision_authority}-{fallback}"
    _build_full_study(
        root,
        fallback=fallback,
        decision_authority=decision_authority,
    )
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()


@pytest.mark.parametrize(
    ("decision_authority", "fallback", "mutation"),
    [
        ("roster_bound_selection", False, "completed-no-tier"),
        ("roster_bound_selection", False, "completed-no-go"),
        ("roster_bound_selection", True, "completed-no-tier"),
        ("roster_bound_selection", True, "completed-no-go"),
        ("synthetic_validation", False, "synthetic-tier"),
        ("synthetic_validation", True, "synthetic-tier"),
    ],
)
def test_power_completed_chain_rejects_wrong_authority_or_no_go_verdict(
    tmp_path: Path,
    decision_authority: str,
    fallback: bool,
    mutation: str,
) -> None:
    root = tmp_path / f"{decision_authority}-{fallback}-{mutation}"
    with pytest.raises(
        RecordValidationError,
        match="(?i)(authority|tier|decision|completed|no.go|verdict)",
    ):
        _build_full_study(
            root,
            fallback=fallback,
            decision_authority=decision_authority,
            verdict_mutation=mutation,
        )
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_artifact_root_seals_failed_second_attempt_causal_closure(
    tmp_path: Path,
) -> None:
    root = tmp_path / "failed-second-attempt"
    _build_full_study(root, failed_second_task=True)
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()


def test_completed_power_chain_may_supersede_an_earlier_partial_attempt(
    tmp_path: Path,
) -> None:
    root = tmp_path / "earlier-partial"
    _build_full_study(
        root,
        earlier_power_partial=True,
        decision_authority="roster_bound_selection",
    )
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()


def test_completed_power_chain_rejects_a_later_partial_attempt(
    tmp_path: Path,
) -> None:
    root = tmp_path / "later-partial"
    _build_full_study(
        root,
        later_power_partial=True,
        decision_authority="roster_bound_selection",
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(terminal|latest|generation|attempt)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


@pytest.mark.parametrize(
    "retry_after_terminal",
    ["gaussian_no_go", "full_no_go"],
)
def test_power_validation_no_go_is_terminal_against_retries(
    tmp_path: Path,
    retry_after_terminal: str,
) -> None:
    root = tmp_path / retry_after_terminal
    if retry_after_terminal == "gaussian_no_go":
        _build_full_study(
            root,
            retry_after_terminal=retry_after_terminal,
            decision_authority="roster_bound_selection",
            no_go_stage="validation",
            no_go_reason="power_or_type_i_gate_failed",
        )
    else:
        _build_full_study(
            root,
            retry_after_terminal=retry_after_terminal,
            decision_authority="roster_bound_selection",
            fallback=True,
            full_gate_failure=True,
        )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(terminal|validation|retry|supersed|generation|no.go)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_full_fallback_rejects_a_passing_gaussian_trigger(
    tmp_path: Path,
) -> None:
    root = tmp_path / "fallback-after-pass"
    _build_full_study(
        root,
        variant="fallback-after-pass",
        fallback=True,
        decision_authority="roster_bound_selection",
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(fallback|Gaussian|validation|passed|terminal)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


@pytest.mark.parametrize(
    "terminal_stage", ["screen", "shard", "selection", "validation"]
)
def test_power_no_go_seals_at_each_real_terminal_stage(
    tmp_path: Path,
    terminal_stage: str,
) -> None:
    root = tmp_path / terminal_stage
    _build_full_study(
        root,
        no_go_stage=terminal_stage,
        no_go_reason=(
            "power_or_type_i_gate_failed" if terminal_stage == "validation" else None
        ),
        decision_authority="roster_bound_selection",
    )
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()


@pytest.mark.parametrize(
    "reason",
    [
        "gaussian_screen_exhausted",
        "numeric_fixture_failed",
        "runtime_bound_exceeded",
    ],
)
def test_gaussian_screen_no_go_accepts_only_declared_screen_reasons(
    tmp_path: Path,
    reason: str,
) -> None:
    root = tmp_path / reason
    _build_full_study(
        root,
        no_go_stage="screen",
        no_go_reason=reason,
        decision_authority="roster_bound_selection",
    )
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()


@pytest.mark.parametrize(
    ("terminal_stage", "wrong_reason"),
    [
        ("screen", "full_multiplier_screen_exhausted"),
        ("screen", "attempt_incomplete"),
        ("screen", "power_or_type_i_gate_failed"),
        ("shard", "gaussian_screen_exhausted"),
        ("shard", "power_or_type_i_gate_failed"),
        ("selection", "numeric_fixture_failed"),
        ("selection", "power_or_type_i_gate_failed"),
        ("validation", "runtime_bound_exceeded"),
    ],
)
def test_power_no_go_rejects_reason_that_narrates_another_terminal(
    tmp_path: Path,
    terminal_stage: str,
    wrong_reason: str,
) -> None:
    root = tmp_path / f"{terminal_stage}-{wrong_reason}"
    _build_full_study(
        root,
        no_go_stage=terminal_stage,
        no_go_reason=wrong_reason,
        decision_authority="roster_bound_selection",
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(reason|stage|phase|terminal)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def test_persisted_validation_cannot_finalize_as_attempt_incomplete(
    tmp_path: Path,
) -> None:
    root = tmp_path / "persisted-validation-attempt-incomplete"
    _build_full_study(
        root,
        no_go_stage="validation",
        no_go_reason="attempt_incomplete",
        decision_authority="roster_bound_selection",
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(validation|completed|reason|attempt.incomplete)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


def _rewrite_fallback_as_screen_no_go(root: Path, *, reason: str) -> None:
    final_path = root / "power/final.json"
    record = load_record(final_path)
    payload = cast(dict[str, object], record["payload"])
    attempt_refs = cast(list[dict[str, object]], payload["all_attempt_refs"])
    full_screen_ref = next(
        ref for ref in attempt_refs if ref["relative_path"] == "power/full-screen.json"
    )
    removed_refs = [
        ref
        for ref in attempt_refs
        if cast(str, ref["relative_path"]).startswith("power/full-shard-")
        or ref["relative_path"] == "power/full-validation.json"
    ]
    for ref in removed_refs:
        (root / cast(str, ref["relative_path"])).unlink()
    retained_refs = [ref for ref in attempt_refs if ref not in removed_refs]
    payload["phase"] = "full_multiplier_fallback"
    payload["generation"] = 0
    payload["parent_refs"] = retained_refs
    payload["all_attempt_refs"] = retained_refs
    payload["finalization"] = {
        "kind": "feasibility_no_go",
        "terminal_attempt_ref": full_screen_ref,
        "terminal_stage": "screen",
        "terminal_phase": "full_multiplier_fallback",
        "terminal_kernel_id": "power-final-full-multiplier-v1",
        "terminal_shard_count": 2,
        "reason": reason,
        "selected_tier": None,
        "decision": "NO_GO",
    }
    final_path.unlink()
    write_record(
        final_path,
        record,
        run_root=root,
        role="resampling_power_report",
    )


@pytest.mark.parametrize(
    ("reason", "valid"),
    [
        ("full_multiplier_screen_exhausted", True),
        ("numeric_fixture_failed", True),
        ("runtime_bound_exceeded", True),
        ("gaussian_screen_exhausted", False),
        ("attempt_incomplete", False),
        ("power_or_type_i_gate_failed", False),
    ],
)
def test_full_multiplier_screen_no_go_reason_is_bound_to_its_phase(
    tmp_path: Path,
    reason: str,
    valid: bool,
) -> None:
    root = tmp_path / reason
    _build_full_study(
        root,
        fallback=True,
        decision_authority="roster_bound_selection",
    )
    _rewrite_fallback_as_screen_no_go(root, reason=reason)

    def seal() -> None:
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )

    if valid:
        seal()
    else:
        with pytest.raises(
            RecordValidationError,
            match="(?i)(reason|stage|phase|terminal)",
        ):
            seal()


def test_validation_gate_failure_has_closed_no_tier_no_go_verdict() -> None:
    payload = _power_payload("final")
    payload["decision_authority"] = "roster_bound_selection"
    finalization = cast(dict[str, object], payload["finalization"])
    finalization.update(
        kind="feasibility_no_go",
        terminal_stage="validation",
        reason="power_or_type_i_gate_failed",
        selected_tier=None,
        decision="NO_GO",
    )
    validate_record(_record("resampling_power_report", payload))

    for field, value in (
        ("selected_tier", 120),
        ("decision", "GO"),
    ):
        mutated = deepcopy(payload)
        mutated["finalization"][field] = value  # type: ignore[index]
        with pytest.raises(
            RecordValidationError,
            match="(?i)(tier|decision|no.go|finalization)",
        ):
            validate_record(_record("resampling_power_report", mutated))


def test_full_multiplier_completed_validation_can_finalize_no_go(
    tmp_path: Path,
) -> None:
    root = tmp_path / "full-validation-no-go"
    _build_full_study(
        root,
        fallback=True,
        full_gate_failure=True,
        decision_authority="roster_bound_selection",
    )
    receipt = seal_artifact_root(
        root,
        FROZEN_UPSTREAM_KINDS,
        root / "p0-core-receipt.json",
        study_id="study-1",
        frozen_created_at=FROZEN,
        provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
    )
    assert (root / receipt.relative_path).is_file()


def test_gate_failure_no_go_must_match_full_validation_verdict(
    tmp_path: Path,
) -> None:
    root = tmp_path / "full-validation-frankenstein"
    _build_full_study(
        root,
        variant="full-gate-terminal-go",
        fallback=True,
        full_gate_failure=True,
        decision_authority="roster_bound_selection",
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(gate|validation|tier|decision|no.go|verdict)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )


@pytest.mark.parametrize(
    ("terminal_stage", "mutation"),
    [
        ("selection", "wrong-stage"),
        ("validation", "fictitious-ref"),
        ("shard", "shard-gap"),
    ],
)
def test_power_no_go_rejects_fictitious_or_malformed_terminal_chains(
    tmp_path: Path,
    terminal_stage: str,
    mutation: str,
) -> None:
    root = tmp_path / f"{terminal_stage}-{mutation}"
    _build_full_study(
        root,
        no_go_stage=terminal_stage,
        no_go_mutation=mutation,
        decision_authority="roster_bound_selection",
    )
    with pytest.raises(
        RecordValidationError,
        match="(?i)(terminal|attempt|stage|shard|parent)",
    ):
        seal_artifact_root(
            root,
            FROZEN_UPSTREAM_KINDS,
            root / "p0-core-receipt.json",
            study_id="study-1",
            frozen_created_at=FROZEN,
            provenance={"design_sha256": SHA_A, "code_sha256": SHA_B},
        )
