"""Milestone coverage for isolated branch execution and attempt closure.

Every test here drives real code: ``run_opaque_slot`` spawns a real isolated
environment subprocess, restores a real hand-sealed prefix snapshot, and closes
a real unscored receipt.  Nothing about the executor is stubbed, because the
property under test — that the frozen prefix is proved *before* the subject may
act — is only meaningful against the real restore path.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.branch_controller import (
    authorize_full_block_rerun,
    finalize_failed_second_attempt,
    seal_unscored_attempt,
)
from pneuma_lab.resampling_null.branch_records import (
    AttemptReceipt,
    FailedSlotReceipt,
    OutageReceipt,
    SlotExecutionReceipt,
    UnscoredSlotReceipt,
    terminal_receipt_digest,
    work_order_digest,
)
from pneuma_lab.resampling_null.controller import derive_call_seed
from pneuma_lab.resampling_null.controller_artifacts import ControllerArtifactStore
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.packet_capabilities import (
    opaque_guidance_relative_path,
)
from pneuma_lab.resampling_null.prefix_contracts import (
    RawProviderCompletionKind,
    SyntheticFailureInjection,
    SyntheticGradeResult,
    SyntheticPrefixProgram,
    SyntheticProviderTranscriptRow,
    SyntheticToolObservation,
    SyntheticVerifierResult,
    synthetic_prefix_program_bytes,
)
from pneuma_lab.resampling_null.synthetic_branch_loop import (
    grade_opaque_slot,
    render_branch_request,
    run_opaque_slot,
    token_ids_bytes,
)
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    BranchCaps,
    FailureKind,
    OpaqueSlotIdentity,
    OpaqueSlotWorkOrder,
    ResourceCounters,
    SubjectTurn,
    ToolCall,
    TriggerReason,
)


pytestmark = pytest.mark.milestone


_STUDY_ID = "study-branch"
_BENCHMARK = "synthetic-branch"
_TASK_ID = "task-branch-0"
_PENDING_CALL = ToolCall(
    call_id="prefix-pending-0",
    name="inspect",
    canonical_arguments_json="{}\n",
)
_BRANCH_CALL = ToolCall(
    call_id="branch-call-0",
    name="commit",
    canonical_arguments_json="{}\n",
)
_BRANCH_CAPS = BranchCaps(
    generated_tokens=4096,
    model_calls=8,
    tool_calls=16,
    wall_clock_ms=120_000,
    pending_prefix_calls_count_against_tool_cap=True,
)
_ENVIRONMENT_SOURCE = Path(
    "src/pneuma_lab/resampling_null/synthetic_environment.py"
)
_TASK_INPUT_BYTES = canonical_json_bytes(
    {
        "canonical_task_payload": {"synthetic_actor_order": ["primary_subject"]},
        "task_id": _TASK_ID,
    },
    indent=None,
)
_GRADE_EVIDENCE = canonical_json_bytes(
    {"infrastructure_failure": False, "partial_reward": 1.0, "success": 1},
    indent=None,
)
_VERIFIER_EVIDENCE = canonical_json_bytes({"finding_count": 0}, indent=None)


def _capability(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _write_source(run_root: Path, relative_path: str, payload: bytes) -> None:
    target = run_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


def _asset_ref(
    run_root: Path,
    *,
    role: str,
    relative_path: str,
    payload: bytes,
    media_type: str = "application/json",
) -> ArtifactRef:
    _write_source(run_root, relative_path, payload)
    return ArtifactRef(
        role=role,
        relative_path=relative_path,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type=media_type,
    )


def _environment_source_ref() -> ArtifactRef:
    """Name the reviewed worker source the spawned subprocess self-verifies."""

    root = Path(__file__).resolve().parents[2]
    payload = (root / _ENVIRONMENT_SOURCE).read_bytes()
    return ArtifactRef(
        role="source_revision",
        relative_path=_ENVIRONMENT_SOURCE.as_posix(),
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type="application/octet-stream",
    )


def _call_mapping(call: ToolCall) -> dict[str, object]:
    return {
        "call_id": call.call_id,
        "canonical_arguments_json": call.canonical_arguments_json,
        "name": call.name,
    }


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return {
        "byte_count": ref.byte_count,
        "media_type": ref.media_type,
        "relative_path": ref.relative_path,
        "role": ref.role,
        "sha256": ref.sha256,
    }


def _prefix_environment_snapshot() -> bytes:
    """Hand-seal the exact worker state a frozen prefix would have produced.

    Sealing the state directly rather than replaying a prefix is what lets the
    fixture hand the branch a *non-empty* pending queue with zero consumed
    transcript turns, which is the case the pre-injection ordering rule exists
    for.
    """

    return canonical_json_bytes(
        {
            "branch_pending_calls": [_call_mapping(_PENDING_CALL)],
            "episode_terminal": False,
            "failure_kind": "none",
            "mutation_committed": False,
            # The prefix program digest; the branch restore path does not bind
            # it, because each branch slot carries its own sealed program.
            "program_sha256": hashlib.sha256(_TASK_INPUT_BYTES).hexdigest(),
            "simulator_context": None,
            "terminal_unexecuted_remainder": [],
            "turns": [],
            "verifier_eligible": False,
            "visible_context": base64.b64encode(_TASK_INPUT_BYTES).decode("ascii"),
        },
        indent=None,
    )


@dataclass(frozen=True, slots=True)
class SlotFixture:
    """One executable branch slot: an order plus its sealed execution assets."""

    work_order: OpaqueSlotWorkOrder
    task_input_ref: ArtifactRef
    program_ref: ArtifactRef
    environment_source_ref: ArtifactRef


def _build_program(
    run_root: Path,
    *,
    label: str,
    seed: int,
    guidance_bytes: bytes | None,
) -> ArtifactRef:
    """Seal a one-call branch program bound to this slot's derived call seed."""

    call_seed = derive_call_seed(seed, "primary_subject", 0)
    request_bytes = render_branch_request(
        subject_role="primary_subject",
        context_bytes=_TASK_INPUT_BYTES,
        guidance_bytes=guidance_bytes,
    )
    request_ref = _asset_ref(
        run_root,
        role="synthetic_request",
        relative_path=f"sources/{label}/request-0.json",
        payload=request_bytes,
    )
    response_bytes = canonical_json_bytes({"branch_response": label}, indent=None)
    response_ref = _asset_ref(
        run_root,
        role="synthetic_response",
        relative_path=f"sources/{label}/response-0.json",
        payload=response_bytes,
    )
    event_ref = _asset_ref(
        run_root,
        role="synthetic_provider_event",
        relative_path=f"sources/{label}/event-0.json",
        payload=canonical_json_bytes(
            {
                "record_kind": "synthetic_raw_provider_event_v1",
                "schema_version": "1",
                "transport_kind": "response",
                "observed_at_ms": 0,
            },
            indent=None,
        ),
    )
    tool_schema_ref = _asset_ref(
        run_root,
        role="tool_schema",
        relative_path="sources/tool-schema.json",
        payload=canonical_json_bytes({"tools": []}, indent=None),
    )
    grade_ref = _asset_ref(
        run_root,
        role="synthetic_grade_result",
        relative_path="sources/grade-evidence.json",
        payload=_GRADE_EVIDENCE,
    )
    verifier_ref = _asset_ref(
        run_root,
        role="synthetic_verifier_result",
        relative_path="sources/verifier-evidence.json",
        payload=_VERIFIER_EVIDENCE,
    )
    result_ref = _asset_ref(
        run_root,
        role="synthetic_tool_result",
        relative_path="sources/tool-result.json",
        payload=canonical_json_bytes({"ok": True}, indent=None),
    )
    program = SyntheticPrefixProgram(
        record_kind="synthetic_prefix_program_v1",
        schema_version="1",
        task_id=_TASK_ID,
        expected_trigger_reason=TriggerReason.FIRST_ELIGIBLE_MUTATION,
        tool_schema_ref=tool_schema_ref,
        provider_transcript=(
            SyntheticProviderTranscriptRow(
                subject_role="primary_subject",
                call_index=0,
                seed=call_seed,
                model_contract_sha256=hashlib.sha256(b"model").hexdigest(),
                expected_request_ref=request_ref,
                expected_request_sha256=request_ref.sha256,
                expected_input_token_ids=tuple(request_bytes),
                response_ref=response_ref,
                typed_turn=SubjectTurn(
                    text="branch",
                    tool_calls=(_BRANCH_CALL,),
                    generated_tokens=len(response_bytes),
                    finish_reason="stop",
                ),
                reported_output_token_ids=tuple(response_bytes),
                reported_generated_tokens=len(response_bytes),
                provider_event_ref=event_ref,
                completion_kind=RawProviderCompletionKind.COMPLETED,
            ),
        ),
        tool_observations=(
            SyntheticToolObservation(
                call_id=_PENDING_CALL.call_id,
                result_ref=result_ref,
                mutation_committed=True,
                verifier_eligible=False,
                episode_terminal=False,
                failure_kind=FailureKind.NONE,
            ),
            SyntheticToolObservation(
                call_id=_BRANCH_CALL.call_id,
                result_ref=result_ref,
                mutation_committed=True,
                verifier_eligible=True,
                episode_terminal=True,
                failure_kind=FailureKind.NONE,
            ),
        ),
        grade_result=SyntheticGradeResult(
            evidence_ref=grade_ref,
            success=1,
            partial_reward=1.0,
            infrastructure_failure=False,
        ),
        verifier_result=SyntheticVerifierResult(
            evidence_ref=verifier_ref,
            finding_count=0,
        ),
        failure_injection=SyntheticFailureInjection(
            stage="none",
            subject_role=None,
            call_index=None,
            tool_call_id=None,
        ),
        clock_trace=(),
    )
    return _asset_ref(
        run_root,
        role="synthetic_execution_program",
        relative_path=f"sources/{label}/program.json",
        payload=synthetic_prefix_program_bytes(program),
    )


def _seal_prefix_snapshot(run_root: Path) -> ArtifactRef:
    """Publish the one composite prefix snapshot all four slots restore."""

    snapshot_bytes = _prefix_environment_snapshot()
    with ControllerArtifactStore(run_root) as store:
        environment_snapshot_ref = store.write(
            role="environment_snapshot",
            payload=snapshot_bytes,
            media_type="application/octet-stream",
        )
        visible_context_ref = store.write(
            role="visible_context",
            payload=_TASK_INPUT_BYTES,
            media_type="application/json",
        )
        token_ids_ref = store.write(
            role="token_ids",
            payload=token_ids_bytes(_TASK_INPUT_BYTES),
            media_type="application/json",
        )
        return store.write(
            role="composite_snapshot",
            payload=canonical_json_bytes(
                {
                    "record_kind": "branch_prefix_snapshot_fixture_v1",
                    "environment_snapshot_ref": _ref_mapping(
                        environment_snapshot_ref
                    ),
                    "visible_context_ref": _ref_mapping(visible_context_ref),
                    "token_ids_ref": _ref_mapping(token_ids_ref),
                    "visible_sha256": hashlib.sha256(
                        _TASK_INPUT_BYTES
                    ).hexdigest(),
                    "token_ids_sha256": hashlib.sha256(
                        token_ids_bytes(_TASK_INPUT_BYTES)
                    ).hexdigest(),
                    "branch_pending_calls": [_call_mapping(_PENDING_CALL)],
                },
                indent=None,
            ),
            media_type="application/json",
        )


def build_slot_fixture(
    run_root: Path,
    *,
    label: str,
    seed: int,
    with_guidance: bool,
    snapshot_ref: ArtifactRef,
    execution_order: int = 0,
) -> SlotFixture:
    """Build one runnable slot: sealed program, packet, and opaque work order."""

    capability = _capability(label)
    guidance_ref: ArtifactRef | None = None
    guidance_bytes: bytes | None = None
    if with_guidance:
        guidance_bytes = f"branch guidance for {label}".encode("utf-8")
        guidance_ref = _asset_ref(
            run_root,
            role="private_guidance",
            relative_path=opaque_guidance_relative_path(_TASK_ID, capability),
            payload=guidance_bytes,
            media_type="text/plain",
        )
    task_input_ref = _asset_ref(
        run_root,
        role="task_input",
        relative_path="sources/task-input.json",
        payload=_TASK_INPUT_BYTES,
    )
    program_ref = _build_program(
        run_root, label=label, seed=seed, guidance_bytes=guidance_bytes
    )
    return SlotFixture(
        work_order=OpaqueSlotWorkOrder(
            study_id=_STUDY_ID,
            task_id=_TASK_ID,
            benchmark=_BENCHMARK,
            slot=OpaqueSlotIdentity(
                slot_id=f"slot-{label}",
                opaque_capability_id=capability,
                seed=seed,
                execution_order=execution_order,
                hardware_lane=0,
            ),
            snapshot_ref=snapshot_ref,
            private_guidance_ref=guidance_ref,
            prefix_visible_sha256=hashlib.sha256(_TASK_INPUT_BYTES).hexdigest(),
            packet_index_sha256=_capability("packet-index"),
            analysis_freeze_sha256=_capability("analysis-freeze"),
            branch_caps=_BRANCH_CAPS,
        ),
        task_input_ref=task_input_ref,
        program_ref=program_ref,
        environment_source_ref=_environment_source_ref(),
    )


def _run(fixture: SlotFixture, run_root: Path) -> UnscoredSlotReceipt:
    return run_opaque_slot(
        fixture.work_order,
        run_root=run_root,
        task_input_ref=fixture.task_input_ref,
        program_ref=fixture.program_ref,
        environment_source_ref=fixture.environment_source_ref,
    )


def _composite_digests(run_root: Path) -> set[str]:
    directory = run_root / "controller-artifacts" / "composite_snapshot"
    if not directory.is_dir():
        return set()
    return {entry.name for entry in directory.iterdir()}


@pytest.fixture()
def prepared(tmp_path: Path) -> tuple[Path, SlotFixture]:
    snapshot_ref = _seal_prefix_snapshot(tmp_path)
    return tmp_path, build_slot_fixture(
        tmp_path,
        label="alpha",
        seed=11,
        with_guidance=True,
        snapshot_ref=snapshot_ref,
    )


def test_run_opaque_slot_restores_verifies_and_stays_unreadable(
    prepared: tuple[Path, SlotFixture],
) -> None:
    run_root, fixture = prepared
    receipt = _run(fixture, run_root)

    assert receipt.endpoint_readable is False
    assert receipt.slot_id == fixture.work_order.slot.slot_id
    assert receipt.opaque_capability_id == (
        fixture.work_order.slot.opaque_capability_id
    )
    # The pre-injection digests are taken after the frozen pending prefix call
    # drains and before the subject speaks, so they must still equal the frozen
    # prefix the work order committed to.
    assert receipt.pre_injection_visible_sha256 == (
        fixture.work_order.prefix_visible_sha256
    )
    assert receipt.pre_injection_token_ids_sha256 == hashlib.sha256(
        token_ids_bytes(_TASK_INPUT_BYTES)
    ).hexdigest()
    assert receipt.failure_kind is FailureKind.NONE
    assert receipt.counters.model_calls == 1
    # One frozen pending prefix call plus one subject-issued call.
    assert receipt.counters.tool_calls == 2
    assert receipt.call_seeds == (
        type(receipt.call_seeds[0])(
            "primary_subject", 0, derive_call_seed(11, "primary_subject", 0)
        ),
    )
    assert receipt.final_snapshot_ref.role == "composite_snapshot"
    assert receipt.provider_cost_ref.role == "provider_cost_closure"


def test_prefix_digest_mismatch_is_rejected_before_any_generation(
    prepared: tuple[Path, SlotFixture],
) -> None:
    run_root, fixture = prepared
    tampered = replace(
        fixture.work_order,
        prefix_visible_sha256=_capability("not-the-frozen-prefix"),
    )
    before = _composite_digests(run_root)

    with pytest.raises(RecordValidationError) as failure:
        run_opaque_slot(
            tampered,
            run_root=run_root,
            task_input_ref=fixture.task_input_ref,
            program_ref=fixture.program_ref,
            environment_source_ref=fixture.environment_source_ref,
        )

    assert "visible context" in str(failure.value)
    # No turn was appended and no slot was closed: the executor writes its
    # composite final snapshot only after the subject loop returns.
    assert _composite_digests(run_root) == before


def test_two_slots_with_different_seeds_derive_different_call_seeds(
    tmp_path: Path,
) -> None:
    snapshot_ref = _seal_prefix_snapshot(tmp_path)
    first = build_slot_fixture(
        tmp_path,
        label="alpha",
        seed=11,
        with_guidance=True,
        snapshot_ref=snapshot_ref,
        execution_order=0,
    )
    second = build_slot_fixture(
        tmp_path,
        label="beta",
        seed=12,
        with_guidance=False,
        snapshot_ref=snapshot_ref,
        execution_order=1,
    )

    first_receipt = _run(first, tmp_path)
    second_receipt = _run(second, tmp_path)

    assert first_receipt.call_seeds[0].seed != second_receipt.call_seeds[0].seed
    for receipt in (first_receipt, second_receipt):
        assert receipt.endpoint_readable is False
        assert receipt.failure_kind is FailureKind.NONE
        assert receipt.pre_injection_visible_sha256 == (
            first.work_order.prefix_visible_sha256
        )
    # Both slots restored the identical frozen prefix, so their pre-injection
    # digests must agree even though their packets and seeds differ.
    assert first_receipt.pre_injection_token_ids_sha256 == (
        second_receipt.pre_injection_token_ids_sha256
    )


def _block_orders(
    run_root: Path,
    snapshot_ref: ArtifactRef,
) -> tuple[OpaqueSlotWorkOrder, ...]:
    return tuple(
        build_slot_fixture(
            run_root,
            label=f"slot{index}",
            seed=100 + index,
            with_guidance=index < 2,
            snapshot_ref=snapshot_ref,
            execution_order=index,
        ).work_order
        for index in range(4)
    )


def _synthetic_receipt(
    order: OpaqueSlotWorkOrder,
    *,
    run_root: Path,
) -> UnscoredSlotReceipt:
    """Close a slot receipt from real, written artifacts without executing it.

    Attempt sealing is a controller property, not an executor one: it must hold
    for any four admissible terminal receipts, so these tests build the
    receipts directly rather than paying four subprocess runs per assertion.
    """

    with ControllerArtifactStore(run_root) as store:
        final_snapshot_ref = store.write(
            role="composite_snapshot",
            payload=canonical_json_bytes(
                {
                    "record_kind": "branch_final_snapshot_v1",
                    "slot_id": order.slot.slot_id,
                },
                indent=None,
            ),
            media_type="application/json",
        )
        provider_cost_ref = store.write(
            role="provider_cost_closure",
            payload=canonical_json_bytes(
                {
                    "record_kind": "synthetic_zero_attempt_cost_closure_v1",
                    "total_cost_microunits": 0,
                },
                indent=None,
            ),
            media_type="application/json",
        )
    return UnscoredSlotReceipt(
        slot_id=order.slot.slot_id,
        opaque_capability_id=order.slot.opaque_capability_id,
        pre_injection_visible_sha256=hashlib.sha256(_TASK_INPUT_BYTES).hexdigest(),
        pre_injection_token_ids_sha256=hashlib.sha256(
            token_ids_bytes(_TASK_INPUT_BYTES)
        ).hexdigest(),
        final_snapshot_ref=final_snapshot_ref,
        counters=ResourceCounters(1, 1, 2, 3),
        call_seeds=(),
        failure_kind=FailureKind.NONE,
        provider_cost_ref=provider_cost_ref,
        endpoint_readable=False,
    )


def test_seal_unscored_attempt_orders_completes_and_refuses_foreign_receipts(
    tmp_path: Path,
) -> None:
    snapshot_ref = _seal_prefix_snapshot(tmp_path)
    orders = _block_orders(tmp_path, snapshot_ref)
    receipts = [_synthetic_receipt(order, run_root=tmp_path) for order in orders]

    shuffled = [receipts[2], receipts[0], receipts[3], receipts[1]]
    attempt = seal_unscored_attempt(
        orders, shuffled, attempt_index=0, run_root=tmp_path
    )
    assert attempt.complete is True
    assert [item.slot_id for item in attempt.terminal_receipts] == [
        order.slot.slot_id for order in orders
    ]
    assert attempt.work_order_sha256s == tuple(
        work_order_digest(order) for order in orders
    )

    partial = seal_unscored_attempt(
        orders, receipts[:3], attempt_index=0, run_root=tmp_path
    )
    assert partial.complete is False

    foreign_order = build_slot_fixture(
        tmp_path,
        label="foreign",
        seed=999,
        with_guidance=False,
        snapshot_ref=snapshot_ref,
        execution_order=3,
    ).work_order
    foreign = _synthetic_receipt(foreign_order, run_root=tmp_path)
    with pytest.raises(RecordValidationError):
        seal_unscored_attempt(
            orders, [*receipts[:3], foreign], attempt_index=0, run_root=tmp_path
        )


def _outage(
    orders: tuple[OpaqueSlotWorkOrder, ...],
    first_attempt: AttemptReceipt,
    *,
    run_root: Path,
) -> tuple[OutageReceipt, ArtifactRef]:
    with ControllerArtifactStore(run_root) as store:
        provider_event_ref = store.write(
            role="provider_event",
            payload=canonical_json_bytes(
                {"record_kind": "provider_outage_v1", "detected": True},
                indent=None,
            ),
            media_type="application/json",
        )
    return (
        OutageReceipt(
            task_id=orders[0].task_id,
            provider_event_ref=provider_event_ref,
            first_attempt=first_attempt,
            detected_before_endpoint_readable=True,
            work_order_sha256s=first_attempt.work_order_sha256s,
            rerun_index=1,
        ),
        provider_event_ref,
    )


def test_authorize_full_block_rerun_reissues_identical_orders(
    tmp_path: Path,
) -> None:
    snapshot_ref = _seal_prefix_snapshot(tmp_path)
    orders = _block_orders(tmp_path, snapshot_ref)
    receipts = [_synthetic_receipt(order, run_root=tmp_path) for order in orders]
    interrupted = seal_unscored_attempt(
        orders, receipts[:2], attempt_index=0, run_root=tmp_path
    )
    outage, _event_ref = _outage(orders, interrupted, run_root=tmp_path)

    reissued = authorize_full_block_rerun(
        orders, interrupted, outage, run_root=tmp_path
    )
    assert reissued == orders
    assert tuple(work_order_digest(order) for order in reissued) == (
        outage.work_order_sha256s
    )

    complete = seal_unscored_attempt(
        orders, receipts, attempt_index=0, run_root=tmp_path
    )
    with pytest.raises(RecordValidationError):
        authorize_full_block_rerun(orders, complete, outage, run_root=tmp_path)

    other_interrupted = seal_unscored_attempt(
        orders, receipts[:1], attempt_index=0, run_root=tmp_path
    )
    mismatched, _ = _outage(orders, other_interrupted, run_root=tmp_path)
    with pytest.raises(RecordValidationError):
        authorize_full_block_rerun(orders, interrupted, mismatched, run_root=tmp_path)

    foreign_orders = tuple(
        build_slot_fixture(
            tmp_path,
            label=f"other{index}",
            seed=200 + index,
            with_guidance=index < 2,
            snapshot_ref=snapshot_ref,
            execution_order=index,
        ).work_order
        for index in range(4)
    )
    with pytest.raises(RecordValidationError):
        authorize_full_block_rerun(
            foreign_orders, interrupted, outage, run_root=tmp_path
        )


def test_finalize_failed_second_attempt_yields_four_adverse_zero_outcomes(
    tmp_path: Path,
) -> None:
    snapshot_ref = _seal_prefix_snapshot(tmp_path)
    orders = _block_orders(tmp_path, snapshot_ref)
    receipts = [_synthetic_receipt(order, run_root=tmp_path) for order in orders]
    first = seal_unscored_attempt(
        orders, receipts[:2], attempt_index=0, run_root=tmp_path
    )
    second = seal_unscored_attempt(
        orders, receipts[:1], attempt_index=1, run_root=tmp_path
    )
    outage, _event_ref = _outage(orders, first, run_root=tmp_path)
    with ControllerArtifactStore(tmp_path) as store:
        adverse_event_ref = store.write(
            role="branch_adverse_event",
            payload=canonical_json_bytes(
                {"record_kind": "branch_adverse_event_v1", "abandoned": True},
                indent=None,
            ),
            media_type="application/json",
        )
    cost_refs = tuple(receipt.provider_cost_ref for receipt in receipts)

    failed, executions = finalize_failed_second_attempt(
        orders,
        first_attempt=first,
        failed_second_attempt=second,
        outage=outage,
        adverse_event_ref=adverse_event_ref,
        provider_cost_refs=cost_refs,
        prefix_success=1,
        run_root=tmp_path,
    )

    assert len(failed) == 4 and all(
        type(item) is FailedSlotReceipt for item in failed
    )
    assert len(executions) == 4
    for order, item, execution in zip(orders, failed, executions, strict=True):
        assert item.failure_kind is FailureKind.INFRASTRUCTURE
        assert item.endpoint_readable is False
        assert execution.grade_receipt is None
        assert execution.source_kind == "failed_second_attempt"
        assert execution.source_receipt_sha256 == terminal_receipt_digest(item)
        assert execution.outcome.success == 0
        assert execution.outcome.partial_reward == 0.0
        assert execution.outcome.infrastructure_failure is True
        assert execution.outcome.opaque_arm_id == order.slot.opaque_capability_id


def test_grade_opaque_slot_binds_its_source_to_the_terminal_receipt(
    prepared: tuple[Path, SlotFixture],
) -> None:
    run_root, fixture = prepared
    unscored = _run(fixture, run_root)

    execution = grade_opaque_slot(
        fixture.work_order,
        unscored,
        run_root=run_root,
        task_input_ref=fixture.task_input_ref,
        program_ref=fixture.program_ref,
        environment_source_ref=fixture.environment_source_ref,
        prefix_success=1,
    )

    assert type(execution) is SlotExecutionReceipt
    assert execution.source_kind == "graded_unscored"
    assert execution.source_receipt_sha256 == terminal_receipt_digest(unscored)
    assert execution.grade_receipt is not None
    assert execution.grade_receipt.success == 1
    assert execution.grade_receipt.artifact_ref.role == "grade_evidence"
    assert execution.outcome.opaque_arm_id == (
        fixture.work_order.slot.opaque_capability_id
    )
    assert execution.outcome.counters == unscored.counters
    assert execution.outcome.prefix_success == 1


def test_block_transactions_reject_work_orders_from_more_than_one_task(
    tmp_path: Path,
) -> None:
    """Four pairwise-distinct orders are not automatically one block.

    Hostile review found that distinctness alone admitted a set drawn from
    different tasks, which would let an attempt or a rerun be sealed over four
    slots that never shared a snapshot.
    """
    from dataclasses import replace

    snapshot_ref = _seal_prefix_snapshot(tmp_path)
    orders = _block_orders(tmp_path, snapshot_ref)
    foreign = (replace(orders[0], task_id="task-other"), *orders[1:])
    receipts = [_synthetic_receipt(order, run_root=tmp_path) for order in foreign]
    with pytest.raises(RecordValidationError, match="must share task_id"):
        seal_unscored_attempt(foreign, receipts, attempt_index=0, run_root=tmp_path)

    mixed_benchmark = (replace(orders[0], benchmark="TAU"), *orders[1:])
    with pytest.raises(RecordValidationError, match="must share benchmark"):
        seal_unscored_attempt(
            mixed_benchmark,
            [_synthetic_receipt(order, run_root=tmp_path) for order in mixed_benchmark],
            attempt_index=0,
            run_root=tmp_path,
        )


def test_rerun_authority_rejects_an_outage_naming_another_task(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    snapshot_ref = _seal_prefix_snapshot(tmp_path)
    orders = _block_orders(tmp_path, snapshot_ref)
    receipts = [_synthetic_receipt(order, run_root=tmp_path) for order in orders]
    interrupted = seal_unscored_attempt(
        orders, receipts[:1], attempt_index=0, run_root=tmp_path
    )
    outage, _event_ref = _outage(orders, interrupted, run_root=tmp_path)
    foreign_outage = replace(outage, task_id="task-other")
    with pytest.raises(RecordValidationError, match="names a different task"):
        authorize_full_block_rerun(
            orders, interrupted, foreign_outage, run_root=tmp_path
        )


def test_failed_finalization_requires_two_distinct_sealed_attempts(
    tmp_path: Path,
) -> None:
    snapshot_ref = _seal_prefix_snapshot(tmp_path)
    orders = _block_orders(tmp_path, snapshot_ref)
    receipts = [_synthetic_receipt(order, run_root=tmp_path) for order in orders]
    first = seal_unscored_attempt(
        orders, receipts[:1], attempt_index=0, run_root=tmp_path
    )
    outage, event_ref = _outage(orders, first, run_root=tmp_path)
    with ControllerArtifactStore(tmp_path) as store:
        adverse_ref = store.write(
            role="branch_adverse_event",
            payload=canonical_json_bytes(
                {"record_kind": "branch_adverse_event_v1", "kind": "infrastructure"},
                indent=None,
            ),
            media_type="application/json",
        )
    del event_ref
    # Re-labelling the same sealed attempt as the second one would let a single
    # interruption close a block that never got a second try.
    same = AttemptReceipt(
        attempt_index=1,
        attempt_ref=first.attempt_ref,
        work_order_sha256s=first.work_order_sha256s,
        terminal_receipts=first.terminal_receipts,
        complete=False,
        endpoint_readable=False,
    )
    with pytest.raises(RecordValidationError, match="distinct sealed attempt"):
        finalize_failed_second_attempt(
            orders,
            first_attempt=first,
            failed_second_attempt=same,
            outage=outage,
            adverse_event_ref=adverse_ref,
            provider_cost_refs=tuple(
                receipt.provider_cost_ref for receipt in receipts
            ),
            prefix_success=1,
            run_root=tmp_path,
        )


def test_grading_refuses_a_receipt_from_another_slot(
    tmp_path: Path, prepared: tuple[Path, SlotFixture],
) -> None:
    """A grade must be bound to the slot whose trajectory it scores."""
    run_root, fixture = prepared
    unscored = _run(fixture, run_root)
    other = build_slot_fixture(
        run_root,
        label="peer",
        seed=999,
        with_guidance=False,
        snapshot_ref=fixture.work_order.snapshot_ref,
        execution_order=1,
    )
    with pytest.raises(RecordValidationError, match="does not belong to this"):
        grade_opaque_slot(
            other.work_order,
            unscored,
            run_root=run_root,
            task_input_ref=other.task_input_ref,
            program_ref=other.program_ref,
            environment_source_ref=_environment_source_ref(),
            prefix_success=1,
        )
