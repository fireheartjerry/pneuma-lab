"""Trusted preparation, attempt sealing, and task-block closure for branches.

This module is the arm-blind controller side of Task-5 branch execution.  It is
the only component that holds a clear ``TaskAssignment`` while constructing
worker input, and it hands each isolated worker exactly one
``OpaqueSlotWorkOrder`` plus the sealed read capability that order implies.

Division of trust:

- ``prepare_opaque_work_orders`` reads clear authority and emits four opaque
  orders in preregistered slot order;
- ``run_opaque_slot`` (``synthetic_branch_loop``) executes one order in an
  isolated environment and returns an unscored, endpoint-unreadable receipt;
- ``seal_unscored_attempt`` closes an attempt over those receipts without ever
  grading;
- ``authorize_full_block_rerun`` re-issues the byte-identical orders once, and
  only for a validated pre-endpoint outage;
- ``grade_opaque_slot`` and ``finalize_failed_second_attempt`` produce the four
  execution receipts;
- ``seal_task_block`` publishes the single scientific ``resampling_task_block``.

Nothing here decides a tier, reads an outcome to choose an arm, or writes an
analysis artifact.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Literal, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .authority_refs import decode_artifact_ref
from .branch_records import (
    AttemptReceipt,
    FailedSlotReceipt,
    OutageReceipt,
    SlotExecutionReceipt,
    TaskBlock,
    TerminalSlotReceipt,
    UnscoredSlotReceipt,
    terminal_receipt_digest,
    work_order_digest,
)
from .controller_artifacts import ControllerArtifactStore
from .errors import RecordValidationError
from .packet_capabilities import (
    TaskPacketCapabilities,
    resolve_packet_capabilities,
)
from .types import (
    ArtifactRef,
    BranchCaps,
    BranchOutcome,
    FailureKind,
    GradeReceipt,
    GroupLabel,
    GroupKind,
    OpaqueSlotIdentity,
    OpaqueSlotWorkOrder,
    ResourceCounters,
    TriggerReason,
)


_TASK_BLOCK_KIND = "resampling_task_block"


@dataclass(frozen=True, slots=True)
class FrozenPrefixView:
    """The exact prefix facts a branch preparer is permitted to consult.

    This is a narrow projection of the sealed prefix index: it carries the
    restorable snapshot identity, the pre-injection digests every slot must
    reproduce, the frozen trigger reason, and the ``Y_0`` prefix success.  It
    carries no provider transcript, grade artifact, or verifier finding.
    """

    task_id: str
    snapshot_ref: ArtifactRef
    visible_sha256: str
    token_ids_sha256: str
    trigger_reason: TriggerReason
    prefix_success: int
    y0_grade: GradeReceipt


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must be a JSON object")
    return value


def _record_bytes(ref: ArtifactRef, *, run_root: Path) -> bytes:
    root = Path(run_root).resolve(strict=True)
    named = root / ref.relative_path
    if named.is_symlink():
        raise RecordValidationError(f"{ref.relative_path!r} must not be a symlink")
    try:
        resolved = named.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise RecordValidationError(
            f"unreadable artifact_ref {ref.relative_path!r}"
        ) from exc
    payload = resolved.read_bytes()
    if (
        len(payload) != ref.byte_count
        or hashlib.sha256(payload).hexdigest() != ref.sha256
    ):
        raise RecordValidationError(
            f"artifact_ref bytes mismatch: {ref.relative_path!r}"
        )
    return payload


def _record(ref: ArtifactRef, *, run_root: Path, kind: str, field: str) -> Mapping[str, object]:
    value = json.loads(_record_bytes(ref, run_root=run_root).decode("utf-8"))
    record = _mapping(value, field=field)
    if record.get("record_kind") != kind:
        raise RecordValidationError(f"{field} is not a {kind} record")
    return record


def load_frozen_prefix_view(
    *,
    prefix_index_ref: ArtifactRef,
    task_id: str,
    run_root: Path,
) -> FrozenPrefixView:
    """Project one task's frozen prefix facts out of the sealed prefix index."""

    if prefix_index_ref.role != "resampling_prefix_receipt":
        raise RecordValidationError(
            "prefix_index_ref must use the resampling_prefix_receipt role"
        )
    record = _record(
        prefix_index_ref,
        run_root=run_root,
        kind="resampling_prefix_receipt",
        field="sealed prefix index",
    )
    payload = _mapping(record["payload"], field="prefix index payload")
    rows = payload.get("task_receipts")
    if not isinstance(rows, list) or not rows:
        raise RecordValidationError("prefix index task_receipts is malformed")
    matches = [
        _mapping(row, field="prefix receipt")
        for row in rows
        if isinstance(row, Mapping) and row.get("task_id") == task_id
    ]
    if len(matches) != 1:
        raise RecordValidationError(
            "sealed prefix index does not cover this task exactly once"
        )
    row = matches[0]
    grade = _mapping(row.get("y0_grade"), field="prefix y0_grade")
    success = grade.get("success")
    if type(success) is not int or success not in (0, 1):
        raise RecordValidationError("prefix y0_grade success must be binary")
    reason = row.get("trigger_reason")
    try:
        trigger_reason = TriggerReason(reason)
    except ValueError as exc:
        raise RecordValidationError("prefix trigger_reason is not registered") from exc
    snapshot_ref = decode_artifact_ref(
        row.get("snapshot_ref"), field="prefix snapshot_ref"
    )
    if snapshot_ref.role != "composite_snapshot":
        raise RecordValidationError("prefix snapshot_ref must be a composite snapshot")
    for name in ("visible_sha256", "token_ids_sha256"):
        digest = row.get(name)
        if type(digest) is not str or len(digest) != 64:
            raise RecordValidationError(f"prefix {name} is malformed")
    reward = grade.get("partial_reward")
    if isinstance(reward, bool) or not isinstance(reward, (int, float)):
        raise RecordValidationError("prefix y0_grade partial_reward is malformed")
    failure = grade.get("infrastructure_failure")
    if type(failure) is not bool:
        raise RecordValidationError("prefix y0_grade infrastructure_failure is malformed")
    return FrozenPrefixView(
        task_id=task_id,
        snapshot_ref=snapshot_ref,
        visible_sha256=cast(str, row["visible_sha256"]),
        token_ids_sha256=cast(str, row["token_ids_sha256"]),
        trigger_reason=trigger_reason,
        prefix_success=success,
        y0_grade=GradeReceipt(
            success=success,
            partial_reward=float(reward),
            infrastructure_failure=failure,
            artifact_ref=decode_artifact_ref(
                grade.get("artifact_ref"), field="prefix y0_grade artifact_ref"
            ),
        ),
    )


def _capabilities_for(
    capabilities: Sequence[TaskPacketCapabilities],
    *,
    task_id: str,
) -> TaskPacketCapabilities:
    matches = [item for item in capabilities if item.task_id == task_id]
    if len(matches) != 1:
        raise RecordValidationError(
            "sealed packet capabilities do not cover this task exactly once"
        )
    return matches[0]


def _ordered_slots(
    slots: Sequence[object],
    capabilities: TaskPacketCapabilities,
) -> tuple[tuple[object, str], ...]:
    """Pair each scheduled slot with its allocation capability, in slot order."""

    by_slot_id = {
        grant.slot_id: grant.opaque_capability_id for grant in capabilities.grants
    }
    ordered: list[tuple[object, str]] = []
    for slot in slots:
        slot_id = getattr(slot, "slot_id", None)
        if slot_id not in by_slot_id:
            raise RecordValidationError(
                "scheduled slot has no sealed packet capability"
            )
        ordered.append((slot, by_slot_id[slot_id]))
    order = [grant.slot_id for grant in capabilities.grants]
    if [getattr(slot, "slot_id") for slot, _ in ordered] != order:
        raise RecordValidationError(
            "scheduled slot order differs from the preregistered allocation order"
        )
    return tuple(ordered)


def prepare_opaque_work_orders(
    *,
    study_id: str,
    benchmark: str,
    prefix: FrozenPrefixView,
    slots: Sequence[object],
    branch_caps: BranchCaps,
    packet_index_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    run_root: Path,
) -> tuple[
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
]:
    """Emit the four worker-visible orders for one triggered task.

    The clear assignment is consumed here and nowhere downstream: each order
    names only an opaque capability and, when the allocation granted one, a
    canonically named guidance artifact.
    """

    if prefix.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY:
        raise RecordValidationError(
            "an untriggered task must use prepare_no_intervention_slots"
        )
    if type(branch_caps) is not BranchCaps:
        raise RecordValidationError("branch_caps must be exact BranchCaps")
    if packet_index_ref.role != "packet_index_sealed":
        raise RecordValidationError("packet_index_ref must be the sealed packet index")
    if analysis_freeze_ref.role != "analysis_freeze":
        raise RecordValidationError("analysis_freeze_ref must be the analysis freeze")
    capabilities = _capabilities_for(
        resolve_packet_capabilities(
            packet_index_ref=packet_index_ref, run_root=run_root
        ),
        task_id=prefix.task_id,
    )
    if not capabilities.triggered:
        raise RecordValidationError(
            "sealed packet capabilities mark this task no-intervention"
        )
    ordered = _ordered_slots(slots, capabilities)
    orders = tuple(
        OpaqueSlotWorkOrder(
            study_id=study_id,
            task_id=prefix.task_id,
            benchmark=benchmark,
            slot=OpaqueSlotIdentity(
                slot_id=getattr(slot, "slot_id"),
                opaque_capability_id=capability,
                seed=getattr(slot, "seed"),
                execution_order=getattr(slot, "execution_order"),
                hardware_lane=getattr(slot, "hardware_lane"),
            ),
            snapshot_ref=prefix.snapshot_ref,
            private_guidance_ref=capabilities.grant_for(capability).guidance_ref,
            prefix_visible_sha256=prefix.visible_sha256,
            packet_index_sha256=packet_index_ref.sha256,
            analysis_freeze_sha256=analysis_freeze_ref.sha256,
            branch_caps=branch_caps,
        )
        for slot, capability in ordered
    )
    if len(orders) != 4:
        raise RecordValidationError("a task must prepare exactly four opaque slots")
    if len({work_order_digest(order) for order in orders}) != 4:
        raise RecordValidationError("prepared work orders must be pairwise distinct")
    return cast(
        tuple[
            OpaqueSlotWorkOrder,
            OpaqueSlotWorkOrder,
            OpaqueSlotWorkOrder,
            OpaqueSlotWorkOrder,
        ],
        orders,
    )


def prepare_no_intervention_slots(
    *,
    prefix: FrozenPrefixView,
    slots: Sequence[object],
    packet_index_ref: ArtifactRef,
    run_root: Path,
) -> tuple[
    OpaqueSlotIdentity,
    OpaqueSlotIdentity,
    OpaqueSlotIdentity,
    OpaqueSlotIdentity,
]:
    """Emit only four opaque identities; no worker or packet is ever involved."""

    if prefix.trigger_reason is not TriggerReason.NO_INTERVENTION_OPPORTUNITY:
        raise RecordValidationError(
            "a triggered task must use prepare_opaque_work_orders"
        )
    capabilities = _capabilities_for(
        resolve_packet_capabilities(
            packet_index_ref=packet_index_ref, run_root=run_root
        ),
        task_id=prefix.task_id,
    )
    if capabilities.triggered:
        raise RecordValidationError(
            "sealed packet capabilities mark this task as triggered"
        )
    ordered = _ordered_slots(slots, capabilities)
    identities = tuple(
        OpaqueSlotIdentity(
            slot_id=getattr(slot, "slot_id"),
            opaque_capability_id=capability,
            seed=getattr(slot, "seed"),
            execution_order=getattr(slot, "execution_order"),
            hardware_lane=getattr(slot, "hardware_lane"),
        )
        for slot, capability in ordered
    )
    if len(identities) != 4:
        raise RecordValidationError("a task must prepare exactly four opaque slots")
    return cast(
        tuple[
            OpaqueSlotIdentity,
            OpaqueSlotIdentity,
            OpaqueSlotIdentity,
            OpaqueSlotIdentity,
        ],
        identities,
    )


def _order_digests(
    work_orders: Sequence[OpaqueSlotWorkOrder],
) -> tuple[str, str, str, str]:
    if len(work_orders) != 4:
        raise RecordValidationError("an attempt must cover exactly four work orders")
    digests = tuple(work_order_digest(order) for order in work_orders)
    if len(set(digests)) != 4:
        raise RecordValidationError("work orders must be pairwise distinct")
    return cast(tuple[str, str, str, str], digests)


def seal_unscored_attempt(
    work_orders: Sequence[OpaqueSlotWorkOrder],
    receipts: Sequence[UnscoredSlotReceipt],
    *,
    attempt_index: Literal[0, 1],
    run_root: Path,
) -> AttemptReceipt:
    """Close one attempt over completed slots without grading anything.

    A complete attempt embeds exactly four terminal receipts; an
    outage-interrupted attempt embeds the zero-to-three that finished and is
    marked incomplete.  Receipts are emitted in preregistered slot order, not
    completion order, so an attempt cannot encode execution timing.
    """

    if attempt_index not in (0, 1):
        raise RecordValidationError("attempt_index must be 0 or 1")
    digests = _order_digests(work_orders)
    by_capability = {
        order.slot.opaque_capability_id: index
        for index, order in enumerate(work_orders)
    }
    positions: list[int] = []
    for receipt in receipts:
        if type(receipt) is not UnscoredSlotReceipt:
            raise RecordValidationError(
                "an attempt may embed only exact UnscoredSlotReceipt records"
            )
        index = by_capability.get(receipt.opaque_capability_id)
        if index is None:
            raise RecordValidationError(
                "attempt receipt does not belong to these work orders"
            )
        if work_orders[index].slot.slot_id != receipt.slot_id:
            raise RecordValidationError(
                "attempt receipt slot differs from its work order slot"
            )
        positions.append(index)
    if len(set(positions)) != len(positions):
        raise RecordValidationError("an attempt may embed each slot at most once")
    ordered = tuple(
        receipt
        for _, receipt in sorted(zip(positions, receipts), key=lambda pair: pair[0])
    )
    complete = len(ordered) == 4
    with ControllerArtifactStore(run_root) as store:
        attempt_ref = store.write(
            role="branch_attempt",
            payload=canonical_json_bytes(
                {
                    "record_kind": "branch_attempt_v1",
                    "attempt_index": attempt_index,
                    "complete": complete,
                    "endpoint_readable": False,
                    "work_order_sha256s": list(digests),
                    "terminal_receipts": [asdict(item) for item in ordered],
                },
                indent=None,
            ),
            media_type="application/json",
        )
    return AttemptReceipt(
        attempt_index=attempt_index,
        attempt_ref=attempt_ref,
        work_order_sha256s=digests,
        terminal_receipts=ordered,
        complete=complete,
        endpoint_readable=False,
    )


def authorize_full_block_rerun(
    work_orders: Sequence[OpaqueSlotWorkOrder],
    first_attempt: AttemptReceipt,
    outage: OutageReceipt,
    *,
    run_root: Path,
) -> tuple[
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
    OpaqueSlotWorkOrder,
]:
    """Re-issue the byte-identical four orders once, for a validated outage.

    This function accepts no execution receipt and returns no new identity: a
    rerun must repeat exactly the frozen block, or it is not a rerun.
    """

    digests = _order_digests(work_orders)
    if type(first_attempt) is not AttemptReceipt:
        raise RecordValidationError("first_attempt must be exact AttemptReceipt")
    if type(outage) is not OutageReceipt:
        raise RecordValidationError("outage must be exact OutageReceipt")
    if first_attempt.attempt_index != 0:
        raise RecordValidationError("only attempt 0 may authorize a rerun")
    if first_attempt.complete:
        raise RecordValidationError("a complete attempt may not be rerun")
    if outage.first_attempt != first_attempt:
        raise RecordValidationError(
            "the outage must embed the exact interrupted first attempt"
        )
    if outage.work_order_sha256s != digests or (
        first_attempt.work_order_sha256s != digests
    ):
        raise RecordValidationError(
            "rerun authority requires the identical four work orders"
        )
    if outage.task_id != work_orders[0].task_id:
        raise RecordValidationError("the outage names a different task")
    # The provider event must exist and reproduce its digest before a rerun is
    # authorized; an unbacked outage claim cannot buy a second attempt.
    _record_bytes(outage.provider_event_ref, run_root=run_root)
    return cast(
        tuple[
            OpaqueSlotWorkOrder,
            OpaqueSlotWorkOrder,
            OpaqueSlotWorkOrder,
            OpaqueSlotWorkOrder,
        ],
        tuple(work_orders),
    )


def finalize_failed_second_attempt(
    work_orders: Sequence[OpaqueSlotWorkOrder],
    *,
    first_attempt: AttemptReceipt,
    failed_second_attempt: AttemptReceipt,
    outage: OutageReceipt,
    adverse_event_ref: ArtifactRef,
    provider_cost_refs: tuple[ArtifactRef, ArtifactRef, ArtifactRef, ArtifactRef],
    prefix_success: int,
    run_root: Path,
) -> tuple[
    tuple[FailedSlotReceipt, FailedSlotReceipt, FailedSlotReceipt, FailedSlotReceipt],
    tuple[
        SlotExecutionReceipt,
        SlotExecutionReceipt,
        SlotExecutionReceipt,
        SlotExecutionReceipt,
    ],
]:
    """Close a doubly-interrupted block without invoking any grader.

    Every slot becomes an adverse-zero outcome.  No grade receipt exists,
    because no endpoint ever became readable.
    """

    digests = _order_digests(work_orders)
    for attempt, name in (
        (first_attempt, "first_attempt"),
        (failed_second_attempt, "failed_second_attempt"),
    ):
        if type(attempt) is not AttemptReceipt:
            raise RecordValidationError(f"{name} must be exact AttemptReceipt")
        if attempt.complete:
            raise RecordValidationError(
                f"{name} must be incomplete to finalize a failed block"
            )
        if attempt.work_order_sha256s != digests:
            raise RecordValidationError(
                f"{name} does not use the frozen four work orders"
            )
    if (first_attempt.attempt_index, failed_second_attempt.attempt_index) != (0, 1):
        raise RecordValidationError("failed finalization requires attempts 0 then 1")
    if outage.first_attempt != first_attempt:
        raise RecordValidationError(
            "the outage must embed the exact interrupted first attempt"
        )
    if adverse_event_ref.role != "branch_adverse_event":
        raise RecordValidationError(
            "adverse_event_ref must use the branch_adverse_event role"
        )
    _record_bytes(adverse_event_ref, run_root=run_root)
    if len(provider_cost_refs) != 4:
        raise RecordValidationError("failed finalization requires four cost refs")
    failed = tuple(
        FailedSlotReceipt(
            slot_id=order.slot.slot_id,
            opaque_capability_id=order.slot.opaque_capability_id,
            failed_attempt_ref=failed_second_attempt.attempt_ref,
            adverse_event_ref=adverse_event_ref,
            provider_cost_ref=cost_ref,
            failure_kind=FailureKind.INFRASTRUCTURE,
            endpoint_readable=False,
        )
        for order, cost_ref in zip(work_orders, provider_cost_refs, strict=True)
    )
    executions = tuple(
        SlotExecutionReceipt(
            source_receipt_sha256=terminal_receipt_digest(receipt),
            source_kind="failed_second_attempt",
            grade_receipt=None,
            outcome=BranchOutcome(
                task_id=order.task_id,
                benchmark=order.benchmark,
                opaque_arm_id=order.slot.opaque_capability_id,
                success=0,
                prefix_success=prefix_success,
                partial_reward=0.0,
                infrastructure_failure=True,
                counters=ResourceCounters(0, 0, 0, 0),
                artifact_ref=adverse_event_ref,
            ),
        )
        for order, receipt in zip(work_orders, failed, strict=True)
    )
    return (
        cast(
            tuple[
                FailedSlotReceipt,
                FailedSlotReceipt,
                FailedSlotReceipt,
                FailedSlotReceipt,
            ],
            failed,
        ),
        cast(
            tuple[
                SlotExecutionReceipt,
                SlotExecutionReceipt,
                SlotExecutionReceipt,
                SlotExecutionReceipt,
            ],
            executions,
        ),
    )


def _group_labels(value: object) -> tuple[GroupLabel, ...]:
    rows = value if isinstance(value, list) else None
    if not rows:
        raise RecordValidationError("sensitivity_groups must be a non-empty array")
    labels: list[GroupLabel] = []
    for row in rows:
        item = _mapping(row, field="sensitivity group")
        try:
            labels.append(GroupLabel(GroupKind(item.get("kind")), cast(str, item.get("value"))))
        except (TypeError, ValueError) as exc:
            raise RecordValidationError("sensitivity group is malformed") from exc
    return tuple(labels)


def _publish(
    block: TaskBlock,
    *,
    run_root: Path,
    out: Path,
    envelope: Mapping[str, object],
) -> ArtifactRef:
    from .artifacts import write_record

    payload = {
        "task_id": block.task_id,
        "benchmark": block.benchmark,
        "stratum": block.stratum,
        "sensitivity_groups": [asdict(group) for group in block.sensitivity_groups],
        "triggered": block.triggered,
        "prefix_success": block.prefix_success,
        "slot_outcomes": [asdict(item) for item in block.slot_outcomes],
        "schedule_ref": asdict(block.schedule_ref),
        "prefix_index_ref": asdict(block.prefix_index_ref),
        "assignment_ref": asdict(block.assignment_ref),
        "packet_index_ref": asdict(block.packet_index_ref),
        "analysis_freeze_ref": asdict(block.analysis_freeze_ref),
        "attempts": (
            None
            if block.attempts is None
            else [asdict(item) for item in block.attempts]
        ),
        "selected_attempt_index": block.selected_attempt_index,
        "terminal_slot_receipts": (
            None
            if block.terminal_slot_receipts is None
            else [asdict(item) for item in block.terminal_slot_receipts]
        ),
        "execution_receipts": (
            None
            if block.execution_receipts is None
            else [asdict(item) for item in block.execution_receipts]
        ),
        "outage_receipt": (
            None if block.outage_receipt is None else asdict(block.outage_receipt)
        ),
        "validity_event_refs": [asdict(ref) for ref in block.validity_event_refs],
        "pipeline_valid": block.pipeline_valid,
        "validity_codes": list(block.validity_codes),
    }
    record = {
        "record_kind": _TASK_BLOCK_KIND,
        "schema_version": "0.1.0",
        "study_id": block.study_id,
        "frozen_created_at": block.frozen_created_at,
        "provenance": dict(cast(Mapping[str, object], envelope["provenance"])),
        "payload": payload,
    }
    return write_record(out, record, run_root=run_root, role="task_block")


def _parent_envelope(
    schedule_ref: ArtifactRef,
    *,
    run_root: Path,
) -> Mapping[str, object]:
    return _record(
        schedule_ref,
        run_root=run_root,
        kind="resampling_prefix_schedule",
        field="prefix schedule",
    )


def seal_task_block(
    *,
    prefix: FrozenPrefixView,
    task_spec: object,
    work_orders: Sequence[OpaqueSlotWorkOrder],
    attempts: Sequence[AttemptReceipt],
    terminal_receipts: Sequence[TerminalSlotReceipt],
    execution_receipts: Sequence[SlotExecutionReceipt],
    selected_attempt_index: Literal[0, 1],
    outage_receipt: OutageReceipt | None,
    validity_event_refs: Sequence[ArtifactRef],
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    assignment_ref: ArtifactRef,
    packet_index_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Publish the one schema-valid task block for a triggered task."""

    digests = _order_digests(work_orders)
    if len(terminal_receipts) != 4 or len(execution_receipts) != 4:
        raise RecordValidationError("a task block requires exactly four slot closures")
    expected_slots = [order.slot.slot_id for order in work_orders]
    expected_caps = [order.slot.opaque_capability_id for order in work_orders]
    if [receipt.slot_id for receipt in terminal_receipts] != expected_slots or (
        [receipt.opaque_capability_id for receipt in terminal_receipts]
        != expected_caps
    ):
        raise RecordValidationError(
            "terminal receipts must follow the preregistered work-order slot order"
        )
    for attempt in attempts:
        if attempt.work_order_sha256s != digests:
            raise RecordValidationError(
                "every attempt must use the frozen four work orders"
            )
    envelope = _parent_envelope(schedule_ref, run_root=run_root)
    block = TaskBlock(
        study_id=cast(str, envelope["study_id"]),
        task_id=prefix.task_id,
        benchmark=getattr(task_spec, "benchmark"),
        stratum=getattr(task_spec, "stratum"),
        sensitivity_groups=tuple(getattr(task_spec, "sensitivity_groups")),
        frozen_created_at=cast(str, envelope["frozen_created_at"]),
        triggered=True,
        prefix_success=prefix.prefix_success,
        slot_outcomes=cast(
            tuple[BranchOutcome, BranchOutcome, BranchOutcome, BranchOutcome],
            tuple(receipt.outcome for receipt in execution_receipts),
        ),
        schedule_ref=schedule_ref,
        prefix_index_ref=prefix_index_ref,
        assignment_ref=assignment_ref,
        packet_index_ref=packet_index_ref,
        analysis_freeze_ref=analysis_freeze_ref,
        attempts=tuple(attempts),
        selected_attempt_index=selected_attempt_index,
        terminal_slot_receipts=cast(
            tuple[
                TerminalSlotReceipt,
                TerminalSlotReceipt,
                TerminalSlotReceipt,
                TerminalSlotReceipt,
            ],
            tuple(terminal_receipts),
        ),
        execution_receipts=cast(
            tuple[
                SlotExecutionReceipt,
                SlotExecutionReceipt,
                SlotExecutionReceipt,
                SlotExecutionReceipt,
            ],
            tuple(execution_receipts),
        ),
        outage_receipt=outage_receipt,
        validity_event_refs=tuple(validity_event_refs),
        pipeline_valid=outage_receipt is None,
        validity_codes=() if outage_receipt is None else ("provider_outage_rerun",),
    )
    return _publish(block, run_root=run_root, out=out, envelope=envelope)


def seal_no_intervention_block(
    *,
    prefix: FrozenPrefixView,
    task_spec: object,
    slots: Sequence[OpaqueSlotIdentity],
    y0_grade: GradeReceipt,
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    assignment_ref: ArtifactRef,
    packet_index_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Copy ``Y_0`` to all four slots without launching a worker or a packet."""

    if prefix.trigger_reason is not TriggerReason.NO_INTERVENTION_OPPORTUNITY:
        raise RecordValidationError(
            "a no-intervention block requires the no-intervention trigger reason"
        )
    if len(slots) != 4 or len({slot.opaque_capability_id for slot in slots}) != 4:
        raise RecordValidationError("a task block requires four distinct opaque slots")
    if type(y0_grade) is not GradeReceipt:
        raise RecordValidationError("y0_grade must be exact GradeReceipt")
    if y0_grade.success != prefix.prefix_success:
        raise RecordValidationError("y0_grade must agree with the frozen prefix success")
    envelope = _parent_envelope(schedule_ref, run_root=run_root)
    outcomes = tuple(
        BranchOutcome(
            task_id=prefix.task_id,
            benchmark=getattr(task_spec, "benchmark"),
            opaque_arm_id=slot.opaque_capability_id,
            success=y0_grade.success,
            prefix_success=prefix.prefix_success,
            partial_reward=y0_grade.partial_reward,
            infrastructure_failure=y0_grade.infrastructure_failure,
            counters=ResourceCounters(0, 0, 0, 0),
            artifact_ref=y0_grade.artifact_ref,
        )
        for slot in slots
    )
    block = TaskBlock(
        study_id=cast(str, envelope["study_id"]),
        task_id=prefix.task_id,
        benchmark=getattr(task_spec, "benchmark"),
        stratum=getattr(task_spec, "stratum"),
        sensitivity_groups=tuple(getattr(task_spec, "sensitivity_groups")),
        frozen_created_at=cast(str, envelope["frozen_created_at"]),
        triggered=False,
        prefix_success=prefix.prefix_success,
        slot_outcomes=cast(
            tuple[BranchOutcome, BranchOutcome, BranchOutcome, BranchOutcome],
            outcomes,
        ),
        schedule_ref=schedule_ref,
        prefix_index_ref=prefix_index_ref,
        assignment_ref=assignment_ref,
        packet_index_ref=packet_index_ref,
        analysis_freeze_ref=analysis_freeze_ref,
        attempts=None,
        selected_attempt_index=None,
        terminal_slot_receipts=None,
        execution_receipts=None,
        outage_receipt=None,
        validity_event_refs=(),
        pipeline_valid=True,
        validity_codes=(),
    )
    return _publish(block, run_root=run_root, out=out, envelope=envelope)


__all__ = [
    "FrozenPrefixView",
    "authorize_full_block_rerun",
    "finalize_failed_second_attempt",
    "load_frozen_prefix_view",
    "prepare_no_intervention_slots",
    "prepare_opaque_work_orders",
    "seal_no_intervention_block",
    "seal_task_block",
    "seal_unscored_attempt",
]
