from __future__ import annotations

from copy import deepcopy

import pytest

from pneuma_lab import schemas as schema_registry


SHA_A = "a" * 64
SHA_B = "b" * 64


def _ref(role: str) -> dict[str, object]:
    return {
        "role": role,
        "relative_path": f"controller-artifacts/{role}/{SHA_A}",
        "sha256": SHA_A,
        "byte_count": 1,
        "media_type": "application/json",
    }


def _receipt() -> dict[str, object]:
    return {
        "record_kind": "resampling_prefix_receipt",
        "schema_version": "0.1.0",
        "study_id": "study-1",
        "frozen_created_at": "2026-07-29T00:00:00Z",
        "provenance": {
            "design_sha256": SHA_A,
            "code_sha256": SHA_B,
        },
        "payload": {
            "schedule_ref": _ref("prefix_schedule"),
            "task_receipts": [
                {
                    "task_id": "task-1",
                    "schedule_sha256": SHA_A,
                    "prefix_caps": {
                        "generated_tokens": 10,
                        "model_calls": 2,
                        "tool_calls": 4,
                        "wall_clock_ms": 100,
                    },
                    "snapshot_ref": _ref("composite_snapshot"),
                    "visible_context_ref": _ref("visible_context"),
                    "visible_sha256": SHA_A,
                    "token_ids_ref": _ref("token_ids"),
                    "token_ids_sha256": SHA_B,
                    "branch_pending_calls": [],
                    "terminal_unexecuted_remainder": [],
                    "trigger_reason": "no_intervention_opportunity",
                    "terminal_failure_kind": "none",
                    "y0_grade": {
                        "success": 0,
                        "partial_reward": 0.0,
                        "infrastructure_failure": False,
                        "artifact_ref": _ref("grade_evidence"),
                    },
                    "grade_execution_receipt_ref": _ref("grade_evidence_receipt"),
                    "verifier_receipt": {
                        "task_id": "task-1",
                        "schedule_sha256": SHA_A,
                        "snapshot_ref": _ref("composite_snapshot"),
                        "verifier_artifact_ref": _ref("verifier_evidence"),
                        "finding_count": 0,
                    },
                    "verifier_execution_receipt_ref": _ref("verifier_evidence_receipt"),
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
                    "provider_attempts_ref": _ref("provider_attempt_ledger"),
                    "boundary_ledger_ref": _ref("tool_boundary_ledger"),
                    "provider_cost_ref": _ref("provider_cost_closure"),
                }
            ],
        },
    }


def _validator():
    jsonschema = pytest.importorskip("jsonschema")
    return jsonschema.Draft202012Validator(
        schema_registry.load_schema("resampling-prefix-receipt.schema.json")
    )


def test_dl136_prefix_receipt_schema_accepts_exact_closed_shape() -> None:
    _validator().validate(_receipt())


def test_dl136_prefix_receipt_rejects_old_pending_tool_calls_only_shape() -> None:
    value = _receipt()
    task = value["payload"]["task_receipts"][0]  # type: ignore[index]
    task["pending_tool_calls"] = []  # type: ignore[index]
    del task["branch_pending_calls"]  # type: ignore[index]
    del task["terminal_unexecuted_remainder"]  # type: ignore[index]
    with pytest.raises(Exception):
        _validator().validate(value)


@pytest.mark.parametrize(
    "field",
    [
        "prefix_caps",
        "token_ids_ref",
        "branch_pending_calls",
        "terminal_unexecuted_remainder",
        "terminal_failure_kind",
        "simulator_counters",
        "provider_attempts_ref",
        "boundary_ledger_ref",
        "grade_execution_receipt_ref",
        "verifier_execution_receipt_ref",
    ],
)
def test_dl136_prefix_receipt_rejects_omitted_new_fields(field: str) -> None:
    value = _receipt()
    task = value["payload"]["task_receipts"][0]  # type: ignore[index]
    del task[field]  # type: ignore[index]
    with pytest.raises(Exception):
        _validator().validate(value)


def test_dl136_prefix_receipt_rejects_unknown_field() -> None:
    value = deepcopy(_receipt())
    task = value["payload"]["task_receipts"][0]  # type: ignore[index]
    task["adapter_claimed_usage"] = 0  # type: ignore[index]
    with pytest.raises(Exception):
        _validator().validate(value)


@pytest.mark.parametrize(
    ("field", "wrong_role"),
    [
        ("snapshot_ref", "snapshot"),
        ("visible_context_ref", "context"),
        ("token_ids_ref", "tokens"),
        ("provider_attempts_ref", "attempts"),
        ("boundary_ledger_ref", "boundaries"),
        ("provider_cost_ref", "cost"),
    ],
)
def test_dl136_prefix_receipt_rejects_wrong_edge_roles(
    field: str,
    wrong_role: str,
) -> None:
    value = _receipt()
    task = value["payload"]["task_receipts"][0]  # type: ignore[index]
    task[field]["role"] = wrong_role  # type: ignore[index]
    with pytest.raises(Exception):
        _validator().validate(value)


@pytest.mark.parametrize(
    "edge",
    [
        "grade_evidence",
        "grade_execution",
        "verifier_evidence",
        "verifier_execution",
    ],
)
def test_dl136_prefix_receipt_rejects_wrong_grade_verifier_roles(
    edge: str,
) -> None:
    value = _receipt()
    task = value["payload"]["task_receipts"][0]  # type: ignore[index]
    if edge == "grade_evidence":
        task["y0_grade"]["artifact_ref"]["role"] = "wrong"  # type: ignore[index]
    elif edge == "grade_execution":
        task["grade_execution_receipt_ref"]["role"] = "wrong"  # type: ignore[index]
    elif edge == "verifier_evidence":
        task["verifier_receipt"]["verifier_artifact_ref"]["role"] = "wrong"  # type: ignore[index]
    else:
        task["verifier_execution_receipt_ref"]["role"] = "wrong"  # type: ignore[index]
    with pytest.raises(Exception):
        _validator().validate(value)
