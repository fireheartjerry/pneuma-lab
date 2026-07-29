from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
import json

import pytest

from pneuma_lab.resampling_null.evidence import (
    AttemptBoundZeroCostClosure,
    CompletedToolBoundaryReceipt,
    CompositeSnapshotEnvelope,
    CostClosure,
    EvidenceExecutionPair,
    FrozenPrefixReceipt,
    GradeEvidence,
    GradeEvidenceReceipt,
    ProviderAttemptLedger,
    ProviderAttemptStatus,
    ProviderCallAttemptReceipt,
    ProviderDispatchIntent,
    ProviderSettlement,
    RestoreIdentity,
    SyntheticZeroAttemptCostClosure,
    ToolBoundaryLedger,
    VerifierEvidence,
    VerifierEvidenceReceipt,
    composite_snapshot_bytes,
    load_composite_snapshot,
    validate_snapshot_receipt_fields,
)
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    CallContractCaps,
    FailureKind,
    FrozenVerifierReceipt,
    GradeReceipt,
    PrefixCaps,
    ResourceCounters,
    TriggerReason,
    ToolCall,
)


SHA = "a" * 64


def _ref(role: str, suffix: str | None = None) -> ArtifactRef:
    name = suffix or role
    digest = SHA if suffix is None else hashlib.sha256(name.encode()).hexdigest()
    return ArtifactRef(
        role=role,
        relative_path=f"controller-artifacts/{role}/{digest}",
        sha256=digest,
        byte_count=1,
        media_type="application/octet-stream",
    )


def _authority_ref(role: str, suffix: str | None = None) -> ArtifactRef:
    name = suffix or role
    digest = SHA if suffix is None else hashlib.sha256(name.encode()).hexdigest()
    return ArtifactRef(
        role=role,
        relative_path=f"authority/{name}.json",
        sha256=digest,
        byte_count=1,
        media_type="application/json",
    )


def _intent(index: int = 0) -> ProviderDispatchIntent:
    return ProviderDispatchIntent(
        subject_role="primary_subject",
        call_index=index,
        seed=min(index + 10, 2**64 - 1),
        request_ref=_ref("provider_request", f"request-{index}"),
        input_token_ids_ref=_ref("input_token_ids", f"input-{index}"),
        model_contract_ref=_authority_ref("subject_contract"),
        absolute_deadline_ms=1000,
    )


def _attempt(
    intent: ProviderDispatchIntent,
    *,
    intent_ref: ArtifactRef | None = None,
    status: ProviderAttemptStatus = ProviderAttemptStatus.COMPLETED,
    response: bool = True,
) -> ProviderCallAttemptReceipt:
    return ProviderCallAttemptReceipt(
        dispatch_intent_ref=intent_ref
        or _ref(
            "provider_dispatch_intent",
            f"intent-{intent.call_index}",
        ),
        subject_role=intent.subject_role,
        call_index=intent.call_index,
        seed=intent.seed,
        status=status,
        request_ref=intent.request_ref,
        input_token_ids_ref=intent.input_token_ids_ref,
        response_ref=(
            _ref("provider_response", f"response-{intent.call_index}")
            if response
            else None
        ),
        output_token_ids_ref=(
            _ref("output_token_ids", f"output-{intent.call_index}")
            if response
            else None
        ),
        model_contract_ref=intent.model_contract_ref,
        generated_tokens=3 if response else 0,
        elapsed_ms=12,
        provider_event_ref=_ref(
            "provider_event",
            f"event-{intent.subject_role}-{intent.call_index}",
        ),
    )


def test_provider_records_are_frozen_slotted_exact_uint64_values() -> None:
    intent = _intent(2**64 - 1)
    assert intent.call_index == 2**64 - 1
    assert not hasattr(intent, "__dict__")
    with pytest.raises(FrozenInstanceError):
        intent.seed = 3  # type: ignore[misc]
    for field, value in (("call_index", True), ("seed", -1), ("seed", 2**64)):
        values = {
            "subject_role": "primary_subject",
            "call_index": 0,
            "seed": 1,
            "request_ref": _ref("provider_request"),
            "input_token_ids_ref": _ref("input_token_ids"),
            "model_contract_ref": _authority_ref("subject_contract"),
            "absolute_deadline_ms": 5,
        }
        values[field] = value
        with pytest.raises((TypeError, ValueError)):
            ProviderDispatchIntent(**values)  # type: ignore[arg-type]


def test_provider_refs_are_purpose_bound_by_role_path_and_subject_role() -> None:
    valid = _intent()
    with pytest.raises(ValueError):
        ProviderDispatchIntent(
            **{
                **{field.name: getattr(valid, field.name) for field in fields(valid)},
                "request_ref": _ref("wrong_request"),
            }
        )
    forged_path = ArtifactRef(
        role="provider_request",
        relative_path="elsewhere/request.bin",
        sha256=SHA,
        byte_count=1,
        media_type="application/octet-stream",
    )
    with pytest.raises(ValueError):
        ProviderDispatchIntent(
            **{
                **{field.name: getattr(valid, field.name) for field in fields(valid)},
                "request_ref": forged_path,
            }
        )
    simulator = ProviderDispatchIntent(
        **{
            **{field.name: getattr(valid, field.name) for field in fields(valid)},
            "subject_role": "user_simulator",
            "model_contract_ref": _authority_ref("simulator_contract"),
        }
    )
    assert simulator.model_contract_ref.role == "simulator_contract"


@pytest.mark.parametrize(
    ("status", "response", "valid"),
    [
        (ProviderAttemptStatus.COMPLETED, True, True),
        (ProviderAttemptStatus.REFUSAL, True, True),
        (ProviderAttemptStatus.MALFORMED_RESPONSE, True, True),
        (ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE, True, True),
        (ProviderAttemptStatus.TIMEOUT_NO_RESPONSE, False, True),
        (ProviderAttemptStatus.PROVIDER_ERROR, False, True),
        (ProviderAttemptStatus.INFRASTRUCTURE_ERROR, False, True),
        (ProviderAttemptStatus.PROVIDER_ERROR, True, True),
        (ProviderAttemptStatus.COMPLETED, False, False),
        (ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE, False, False),
        (ProviderAttemptStatus.TIMEOUT_NO_RESPONSE, True, False),
    ],
)
def test_attempt_status_closes_response_evidence(
    status: ProviderAttemptStatus,
    response: bool,
    valid: bool,
) -> None:
    intent = _intent()
    if valid:
        _attempt(intent, status=status, response=response)
    else:
        with pytest.raises(ValueError):
            _attempt(intent, status=status, response=response)


def test_attempt_rejects_half_response_and_dispatch_drift() -> None:
    intent = _intent()
    values = {
        **{
            field.name: getattr(_attempt(intent), field.name)
            for field in fields(ProviderCallAttemptReceipt)
        },
        "output_token_ids_ref": None,
    }
    with pytest.raises(ValueError):
        ProviderCallAttemptReceipt(**values)
    with pytest.raises(ValueError):
        _attempt(
            intent, status=ProviderAttemptStatus.TIMEOUT_NO_RESPONSE, response=False
        ).__class__(
            **{
                **{
                    field.name: getattr(
                        _attempt(
                            intent,
                            status=ProviderAttemptStatus.TIMEOUT_NO_RESPONSE,
                            response=False,
                        ),
                        field.name,
                    )
                    for field in fields(ProviderCallAttemptReceipt)
                },
                "generated_tokens": 1,
            }
        )


def test_provider_attempt_ledger_requires_exact_order_and_dispatch_binding() -> None:
    first = _intent(0)
    second = ProviderDispatchIntent(
        **{
            **{
                field.name: getattr(_intent(0), field.name)
                for field in fields(ProviderDispatchIntent)
            },
            "subject_role": "user_simulator",
            "model_contract_ref": _authority_ref("simulator_contract"),
        }
    )
    first_ref = _ref("provider_dispatch_intent", "intent-0")
    second_ref = _ref("provider_dispatch_intent", "intent-1")
    ledger = ProviderAttemptLedger(
        intents=(first, second),
        intent_refs=(first_ref, second_ref),
        attempts=(
            _attempt(first, intent_ref=first_ref),
            _attempt(second, intent_ref=second_ref),
        ),
    )
    assert ledger.attempts[1].subject_role == "user_simulator"
    with pytest.raises(TypeError):
        ProviderAttemptLedger(
            intents=[first],  # type: ignore[arg-type]
            intent_refs=(first_ref,),
            attempts=(_attempt(first, intent_ref=first_ref),),
        )
    with pytest.raises(ValueError):
        ProviderAttemptLedger(
            intents=(first,),
            intent_refs=(first_ref,),
            attempts=(
                _attempt(first, intent_ref=_ref("provider_dispatch_intent", "wrong")),
            ),
        )


def test_completed_tool_boundary_and_ledger_are_forensically_closed() -> None:
    boundary = CompletedToolBoundaryReceipt(
        call_id="call-1",
        tool_call_ref=_ref("tool_call"),
        tool_result_ref=_ref("tool_result"),
        mutation_committed=True,
        verifier_eligible_after=True,
        episode_terminal=False,
        failure_kind=FailureKind.NONE,
        elapsed_ms=7,
    )
    ledger = ToolBoundaryLedger(boundaries=(boundary,))
    assert ledger.boundaries == (boundary,)
    assert FailureKind.REFUSAL.value == "refusal"
    with pytest.raises(TypeError):
        ToolBoundaryLedger(boundaries=[boundary])  # type: ignore[arg-type]
    clean_terminal = CompletedToolBoundaryReceipt(
        **{
            **{field.name: getattr(boundary, field.name) for field in fields(boundary)},
            "episode_terminal": True,
            "failure_kind": FailureKind.NONE,
        }
    )
    assert clean_terminal.episode_terminal


def _snapshot() -> CompositeSnapshotEnvelope:
    counters = ResourceCounters(3, 1, 1, 20)
    simulator = ResourceCounters(1, 1, 0, 20)
    return CompositeSnapshotEnvelope(
        schema_version="0.1.0",
        study_ref=_authority_ref("study_manifest"),
        task_ref=_ref("selected_task"),
        schedule_ref=_authority_ref("resampling_prefix_schedule"),
        task_input_ref=_authority_ref("task_input"),
        environment_contract_ref=_authority_ref("environment_contract"),
        isolation_contract_ref=_authority_ref("isolation_contract"),
        environment_snapshot_ref=_ref("environment_snapshot"),
        branch_pending_calls=(ToolCall("c2", "read", "{}\n"),),
        terminal_unexecuted_remainder=(),
        visible_context_ref=_ref("visible_context"),
        visible_sha256=SHA,
        token_ids_ref=_ref("token_ids"),
        token_ids_sha256=SHA,
        boundary_ledger_ref=_ref("tool_boundary_ledger"),
        provider_attempts_ref=_ref("provider_attempt_ledger"),
        primary_counters=counters,
        simulator_counters=simulator,
        primary_remaining_quotas=PrefixCaps(7, 2, 3, 80),
        simulator_remaining_quotas=CallContractCaps(9, 2, 2, 5, 1),
        cumulative_mutation=True,
        episode_terminal=False,
        terminal_failure_kind=FailureKind.NONE,
        subject_stateless_attestation_ref=_ref("subject_stateless_attestation"),
        simulator_stateless_attestation_ref=_ref("simulator_stateless_attestation"),
        runtime_ref=_ref("runtime_attestation"),
        container_ref=_ref("container_attestation"),
        source_revision_ref=_authority_ref("source_revision"),
    )


def test_composite_snapshot_is_canonical_closed_and_separates_queues() -> None:
    snapshot = _snapshot()
    payload = composite_snapshot_bytes(snapshot)
    assert (
        payload.rstrip(b"\n")
        == json.dumps(
            json.loads(payload),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    assert load_composite_snapshot(payload) == snapshot
    mapping = json.loads(payload)
    mapping["unknown"] = 1
    with pytest.raises(ValueError):
        load_composite_snapshot(json.dumps(mapping).encode())
    del mapping["unknown"]
    del mapping["token_ids_ref"]
    with pytest.raises(ValueError):
        load_composite_snapshot(json.dumps(mapping).encode())
    with pytest.raises(ValueError):
        CompositeSnapshotEnvelope(
            **{
                **{
                    field.name: getattr(snapshot, field.name)
                    for field in fields(snapshot)
                },
                "terminal_unexecuted_remainder": (ToolCall("c3", "read", "{}\n"),),
            }
        )


def test_snapshot_digest_refs_and_terminal_state_are_closed() -> None:
    snapshot = _snapshot()
    with pytest.raises(ValueError):
        CompositeSnapshotEnvelope(
            **{
                **{
                    field.name: getattr(snapshot, field.name)
                    for field in fields(snapshot)
                },
                "visible_sha256": "d" * 64,
            }
        )
    with pytest.raises(ValueError):
        CompositeSnapshotEnvelope(
            **{
                **{
                    field.name: getattr(snapshot, field.name)
                    for field in fields(snapshot)
                },
                "terminal_failure_kind": FailureKind.TIMEOUT,
            }
        )


def test_simulator_attestation_is_null_exactly_for_zero_simulator_authority() -> None:
    snapshot = _snapshot()
    simulator_free = CompositeSnapshotEnvelope(
        **{
            **{field.name: getattr(snapshot, field.name) for field in fields(snapshot)},
            "simulator_counters": ResourceCounters(0, 0, 0, 20),
            "simulator_remaining_quotas": None,
            "simulator_stateless_attestation_ref": None,
        }
    )
    assert simulator_free.simulator_stateless_attestation_ref is None
    with pytest.raises(ValueError):
        CompositeSnapshotEnvelope(
            **{
                **{
                    field.name: getattr(simulator_free, field.name)
                    for field in fields(simulator_free)
                },
                "simulator_counters": ResourceCounters(1, 0, 0, 20),
            }
        )


def test_snapshot_terminal_queue_and_clean_termination_coherence() -> None:
    snapshot = _snapshot()
    clean_terminal = CompositeSnapshotEnvelope(
        **{
            **{field.name: getattr(snapshot, field.name) for field in fields(snapshot)},
            "branch_pending_calls": (),
            "episode_terminal": True,
            "terminal_failure_kind": FailureKind.NONE,
        }
    )
    assert clean_terminal.episode_terminal
    adverse_remainder = CompositeSnapshotEnvelope(
        **{
            **{field.name: getattr(snapshot, field.name) for field in fields(snapshot)},
            "branch_pending_calls": (),
            "terminal_unexecuted_remainder": (ToolCall("c3", "read", "{}\n"),),
            "episode_terminal": True,
            "terminal_failure_kind": FailureKind.MALFORMED_ACTION,
        }
    )
    assert adverse_remainder.terminal_unexecuted_remainder
    with pytest.raises(ValueError):
        CompositeSnapshotEnvelope(
            **{
                **{
                    field.name: getattr(snapshot, field.name)
                    for field in fields(snapshot)
                },
                "branch_pending_calls": (),
                "terminal_unexecuted_remainder": (ToolCall("c3", "read", "{}\n"),),
            }
        )


def test_snapshot_outer_duplicate_cross_check_uses_exact_values() -> None:
    snapshot = _snapshot()
    validate_snapshot_receipt_fields(
        snapshot,
        snapshot_ref=ArtifactRef(
            role="composite_snapshot",
            relative_path="controller-artifacts/composite_snapshot/"
            + hashlib.sha256(composite_snapshot_bytes(snapshot)).hexdigest(),
            sha256=hashlib.sha256(composite_snapshot_bytes(snapshot)).hexdigest(),
            byte_count=len(composite_snapshot_bytes(snapshot)),
            media_type="application/json",
        ),
        snapshot_bytes=composite_snapshot_bytes(snapshot),
        visible_context_ref=snapshot.visible_context_ref,
        visible_sha256=snapshot.visible_sha256,
        token_ids_ref=snapshot.token_ids_ref,
        token_ids_sha256=snapshot.token_ids_sha256,
        branch_pending_calls=snapshot.branch_pending_calls,
        terminal_unexecuted_remainder=snapshot.terminal_unexecuted_remainder,
        boundary_ledger_ref=snapshot.boundary_ledger_ref,
        provider_attempts_ref=snapshot.provider_attempts_ref,
        primary_counters=snapshot.primary_counters,
        simulator_counters=snapshot.simulator_counters,
        terminal_failure_kind=snapshot.terminal_failure_kind,
    )
    with pytest.raises(ValueError):
        validate_snapshot_receipt_fields(
            snapshot,
            snapshot_ref=_ref("composite_snapshot"),
            snapshot_bytes=composite_snapshot_bytes(snapshot),
            visible_context_ref=snapshot.visible_context_ref,
            visible_sha256="d" * 64,
            token_ids_ref=snapshot.token_ids_ref,
            token_ids_sha256=snapshot.token_ids_sha256,
            branch_pending_calls=snapshot.branch_pending_calls,
            terminal_unexecuted_remainder=snapshot.terminal_unexecuted_remainder,
            boundary_ledger_ref=snapshot.boundary_ledger_ref,
            provider_attempts_ref=snapshot.provider_attempts_ref,
            primary_counters=snapshot.primary_counters,
            simulator_counters=snapshot.simulator_counters,
            terminal_failure_kind=snapshot.terminal_failure_kind,
        )


def test_frozen_prefix_receipt_cross_checks_composite_snapshot_bytes() -> None:
    snapshot = _snapshot()
    payload = composite_snapshot_bytes(snapshot)
    snapshot_ref = ArtifactRef(
        role="composite_snapshot",
        relative_path="controller-artifacts/composite_snapshot/"
        + hashlib.sha256(payload).hexdigest(),
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type="application/json",
    )
    receipt = FrozenPrefixReceipt(
        task_id="task-1",
        schedule_sha256=snapshot.schedule_ref.sha256,
        prefix_caps=PrefixCaps(10, 3, 4, 100),
        snapshot_ref=snapshot_ref,
        visible_context_ref=snapshot.visible_context_ref,
        visible_sha256=snapshot.visible_sha256,
        token_ids_ref=snapshot.token_ids_ref,
        token_ids_sha256=snapshot.token_ids_sha256,
        branch_pending_calls=snapshot.branch_pending_calls,
        terminal_unexecuted_remainder=snapshot.terminal_unexecuted_remainder,
        trigger_reason=TriggerReason.FIRST_ELIGIBLE_MUTATION,
        terminal_failure_kind=snapshot.terminal_failure_kind,
        y0_grade=GradeReceipt(0, 0.0, False, _ref("grade_evidence")),
        grade_execution_receipt_ref=_ref("grade_evidence_receipt"),
        verifier_receipt=FrozenVerifierReceipt(
            "task-1",
            snapshot.schedule_ref.sha256,
            snapshot_ref,
            _ref("verifier_evidence"),
            0,
        ),
        verifier_execution_receipt_ref=_ref("verifier_evidence_receipt"),
        counters=snapshot.primary_counters,
        simulator_counters=snapshot.simulator_counters,
        call_seeds=(),
        provider_attempts_ref=snapshot.provider_attempts_ref,
        boundary_ledger_ref=snapshot.boundary_ledger_ref,
        provider_cost_ref=_ref("provider_cost_closure"),
    )
    receipt.validate_snapshot_bytes(payload)
    with pytest.raises(ValueError):
        FrozenPrefixReceipt(
            **{
                **{
                    field.name: getattr(receipt, field.name)
                    for field in fields(receipt)
                },
                "visible_sha256": "d" * 64,
            }
        )
    with pytest.raises(ValueError, match="call_id"):
        FrozenPrefixReceipt(
            **{
                **{
                    field.name: getattr(receipt, field.name)
                    for field in fields(receipt)
                },
                "branch_pending_calls": (
                    ToolCall("duplicate", "read", "{}\n"),
                    ToolCall("duplicate", "write", "{}\n"),
                ),
            }
        )


def test_frozen_prefix_closes_caps_and_adverse_y0() -> None:
    snapshot = _snapshot()
    payload = composite_snapshot_bytes(snapshot)
    snapshot_ref = ArtifactRef(
        role="composite_snapshot",
        relative_path="controller-artifacts/composite_snapshot/"
        + hashlib.sha256(payload).hexdigest(),
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type="application/json",
    )
    base = FrozenPrefixReceipt(
        task_id="task-1",
        schedule_sha256=snapshot.schedule_ref.sha256,
        prefix_caps=PrefixCaps(10, 3, 4, 100),
        snapshot_ref=snapshot_ref,
        visible_context_ref=snapshot.visible_context_ref,
        visible_sha256=snapshot.visible_sha256,
        token_ids_ref=snapshot.token_ids_ref,
        token_ids_sha256=snapshot.token_ids_sha256,
        branch_pending_calls=snapshot.branch_pending_calls,
        terminal_unexecuted_remainder=(),
        trigger_reason=TriggerReason.FIRST_ELIGIBLE_MUTATION,
        terminal_failure_kind=FailureKind.NONE,
        y0_grade=GradeReceipt(0, 0.0, False, _ref("grade_evidence")),
        grade_execution_receipt_ref=_ref("grade_evidence_receipt"),
        verifier_receipt=FrozenVerifierReceipt(
            "task-1",
            snapshot.schedule_ref.sha256,
            snapshot_ref,
            _ref("verifier_evidence"),
            0,
        ),
        verifier_execution_receipt_ref=_ref("verifier_evidence_receipt"),
        counters=snapshot.primary_counters,
        simulator_counters=snapshot.simulator_counters,
        call_seeds=(),
        provider_attempts_ref=snapshot.provider_attempts_ref,
        boundary_ledger_ref=snapshot.boundary_ledger_ref,
        provider_cost_ref=_ref("provider_cost_closure"),
    )
    with pytest.raises(ValueError, match="caps"):
        FrozenPrefixReceipt(
            **{
                **{field.name: getattr(base, field.name) for field in fields(base)},
                "prefix_caps": PrefixCaps(11, 3, 4, 100),
            }
        ).validate_snapshot_bytes(payload)
    with pytest.raises(ValueError, match="adverse"):
        FrozenPrefixReceipt(
            **{
                **{field.name: getattr(base, field.name) for field in fields(base)},
                "branch_pending_calls": (),
                "trigger_reason": TriggerReason.NO_INTERVENTION_OPPORTUNITY,
                "terminal_failure_kind": FailureKind.TIMEOUT,
                "y0_grade": GradeReceipt(
                    1,
                    1.0,
                    False,
                    _ref("grade_evidence"),
                ),
            }
        )


def _contains_artifact_ref(value: object) -> bool:
    if isinstance(value, ArtifactRef):
        return True
    if is_dataclass(value):
        return any(
            _contains_artifact_ref(getattr(value, item.name)) for item in fields(value)
        )
    if isinstance(value, tuple):
        return any(_contains_artifact_ref(item) for item in value)
    return False


def test_raw_grade_and_verifier_evidence_contain_no_artifact_refs() -> None:
    grade = GradeEvidence(1, 0.5, False, b'{"grade":1}')
    verifier = VerifierEvidence(2, b'{"findings":[]}')
    assert not _contains_artifact_ref(grade)
    assert not _contains_artifact_ref(verifier)
    assert not hasattr(grade, "__dict__")


def test_grade_and_verify_restore_identities_cannot_alias() -> None:
    grade = GradeEvidenceReceipt(
        identity=RestoreIdentity("grade-i", 10, "grade-root"),
        snapshot_ref=_ref("composite_snapshot"),
        restore_receipt_ref=_ref("grade_restore_receipt", "grade"),
        evidence_ref=_ref("grade_evidence"),
    )
    verifier = VerifierEvidenceReceipt(
        identity=RestoreIdentity("verify-i", 11, "verify-root"),
        snapshot_ref=grade.snapshot_ref,
        restore_receipt_ref=_ref("verifier_restore_receipt", "verify"),
        evidence_ref=_ref("verifier_evidence"),
    )
    assert EvidenceExecutionPair(grade, verifier).grade.identity.process_id == 10
    for identity in (
        RestoreIdentity("grade-i", 11, "verify-root"),
        RestoreIdentity("verify-i", 10, "verify-root"),
        RestoreIdentity("verify-i", 11, "grade-root"),
    ):
        with pytest.raises(ValueError):
            EvidenceExecutionPair(
                grade,
                VerifierEvidenceReceipt(
                    identity=identity,
                    snapshot_ref=grade.snapshot_ref,
                    restore_receipt_ref=_ref("verifier_restore_receipt", "verify-2"),
                    evidence_ref=_ref("verifier_evidence"),
                ),
            )


def test_cost_closure_rejects_missing_duplicate_and_cross_wired_ancestry() -> None:
    intent = _intent()
    intent_ref = _ref("provider_dispatch_intent")
    attempt = _attempt(intent, intent_ref=intent_ref)
    attempt_ref = _ref("provider_attempt")
    settlement = ProviderSettlement(
        dispatch_intent_ref=intent_ref,
        attempt_receipt_ref=attempt_ref,
        provider_event_ref=attempt.provider_event_ref,
        settlement_ref=_ref("provider_settlement"),
        cost_microunits=17,
    )
    closure = CostClosure(
        intents=(intent,),
        intent_refs=(intent_ref,),
        attempts=(attempt,),
        attempt_refs=(attempt_ref,),
        settlements=(settlement,),
        total_cost_microunits=17,
    )
    assert closure.total_cost_microunits == 17
    with pytest.raises(ValueError):
        CostClosure(
            intents=(intent, intent),
            intent_refs=(intent_ref, intent_ref),
            attempts=(attempt, attempt),
            attempt_refs=(attempt_ref, attempt_ref),
            settlements=(settlement, settlement),
            total_cost_microunits=34,
        )
    with pytest.raises(ValueError):
        CostClosure(
            intents=(intent,),
            intent_refs=(intent_ref,),
            attempts=(attempt,),
            attempt_refs=(attempt_ref,),
            settlements=(),
            total_cost_microunits=0,
        )
    with pytest.raises(ValueError):
        ProviderSettlement(
            dispatch_intent_ref=_ref("provider_dispatch_intent", "wrong"),
            attempt_receipt_ref=attempt_ref,
            provider_event_ref=attempt.provider_event_ref,
            settlement_ref=_ref("provider_settlement"),
            cost_microunits=0,
        ).validate_against(
            intent_ref=intent_ref,
            attempt_ref=attempt_ref,
            attempt=attempt,
        )


def test_provider_attempt_ledger_rejects_duplicate_provider_event() -> None:
    first = _intent(0)
    second = _intent(1)
    first_ref = _ref("provider_dispatch_intent", "intent-0")
    second_ref = _ref("provider_dispatch_intent", "intent-1")
    first_attempt = _attempt(first, intent_ref=first_ref)
    second_attempt = _attempt(second, intent_ref=second_ref)
    duplicate_event = ProviderCallAttemptReceipt(
        **{
            **{
                field.name: getattr(second_attempt, field.name)
                for field in fields(second_attempt)
            },
            "provider_event_ref": first_attempt.provider_event_ref,
        }
    )
    with pytest.raises(ValueError, match="provider_event"):
        ProviderAttemptLedger(
            intents=(first, second),
            intent_refs=(first_ref, second_ref),
            attempts=(first_attempt, duplicate_event),
        )


def test_typed_zero_cost_closures_are_mandatory_and_distinct() -> None:
    assert SyntheticZeroAttemptCostClosure().total_cost_microunits == 0
    intent = _intent()
    intent_ref = _ref("provider_dispatch_intent")
    attempt = _attempt(intent, intent_ref=intent_ref)
    attempt_ref = _ref("provider_attempt")
    settlement = ProviderSettlement(
        dispatch_intent_ref=intent_ref,
        attempt_receipt_ref=attempt_ref,
        provider_event_ref=attempt.provider_event_ref,
        settlement_ref=_ref("provider_settlement"),
        cost_microunits=0,
    )
    zero = AttemptBoundZeroCostClosure(
        intents=(intent,),
        intent_refs=(intent_ref,),
        attempts=(attempt,),
        attempt_refs=(attempt_ref,),
        settlements=(settlement,),
    )
    assert zero.total_cost_microunits == 0
    with pytest.raises(ValueError):
        CostClosure(
            intents=(),
            intent_refs=(),
            attempts=(),
            attempt_refs=(),
            settlements=(),
            total_cost_microunits=0,
        )
