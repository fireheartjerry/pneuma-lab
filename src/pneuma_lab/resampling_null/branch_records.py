"""Frozen value contracts for one opaque four-slot terminal task block.

These records mirror ``schemas/resampling-task-block.schema.json`` field for
field.  They are the in-memory closure an isolated branch executor produces:
per-slot unscored receipts that never expose an endpoint-readable transcript,
the attempt receipts that carry them, the outage closure for a provider event
detected before any endpoint became readable, and the graded execution
receipts that bind each terminal receipt to its published branch outcome.

Nothing here serializes a record payload.  Construction is the validation
boundary: every dataclass rejects an inadmissible value at ``__post_init__``
time, so an inadmissible task block cannot exist long enough to be published.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Literal

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .prefix_contracts import CONTROLLER_ROLE_MEDIA
from .types import (
    ArtifactRef,
    BranchOutcome,
    CallSeedReceipt,
    FailureKind,
    GradeReceipt,
    GroupLabel,
    OpaqueSlotWorkOrder,
    ResourceCounters,
)


_UNSCORED_FAILURE_KINDS = frozenset(
    {
        FailureKind.NONE,
        FailureKind.MODEL,
        FailureKind.MALFORMED_ACTION,
        FailureKind.TOKEN_CAP,
        FailureKind.TOOL_CAP,
        FailureKind.TIMEOUT,
        FailureKind.INFRASTRUCTURE,
    }
)

_EXECUTION_SOURCE_KINDS = ("graded_unscored", "failed_second_attempt")

_TASK_BLOCK_PARENT_ROLES = {
    "schedule_ref": "resampling_prefix_schedule",
    "prefix_index_ref": "resampling_prefix_receipt",
    "assignment_ref": "resampling_assignment_ledger",
    "packet_index_ref": "packet_index_sealed",
    "analysis_freeze_ref": "analysis_freeze",
}


def _require_nonempty_string(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact text")
    if not value:
        raise ValueError(f"{name} must be non-empty")
    return value


def _require_sha256(value: object, name: str) -> str:
    validated = _require_nonempty_string(value, name)
    if len(validated) != 64 or any(
        char not in "0123456789abcdef" for char in validated
    ):
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")
    return validated


def _require_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{name} must be bool")
    return value


def _require_binary_int(value: object, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an exact int")
    if value not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return value


def _require_artifact_ref(
    value: object,
    name: str,
    *,
    role: str | None = None,
) -> ArtifactRef:
    if not isinstance(value, ArtifactRef):
        raise TypeError(f"{name} must be ArtifactRef")
    if role is not None and value.role != role:
        raise ValueError(f"{name} role must equal {role!r}")
    registered_media_type = CONTROLLER_ROLE_MEDIA.get(value.role)
    if registered_media_type is not None and value.media_type != registered_media_type:
        raise ValueError(f"{name} media_type must equal {registered_media_type!r}")
    return value


def _require_work_order_sha256s(value: object, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be an exact tuple")
    if len(value) != 4:
        raise ValueError(f"{name} must contain exactly four work-order digests")
    for digest in value:
        _require_sha256(digest, f"{name} item")
    if len(set(value)) != 4:
        raise ValueError(f"{name} must be pairwise distinct")
    return value


@dataclass(frozen=True, slots=True)
class UnscoredSlotReceipt:
    """One terminal branch slot closed before any endpoint became readable."""

    slot_id: str
    opaque_capability_id: str
    pre_injection_visible_sha256: str
    pre_injection_token_ids_sha256: str
    final_snapshot_ref: ArtifactRef
    counters: ResourceCounters
    call_seeds: tuple[CallSeedReceipt, ...]
    failure_kind: FailureKind
    provider_cost_ref: ArtifactRef
    endpoint_readable: Literal[False]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.slot_id, "slot_id")
        _require_sha256(self.opaque_capability_id, "opaque_capability_id")
        for name in (
            "pre_injection_visible_sha256",
            "pre_injection_token_ids_sha256",
        ):
            _require_sha256(getattr(self, name), name)
        _require_artifact_ref(
            self.final_snapshot_ref,
            "final_snapshot_ref",
            role="composite_snapshot",
        )
        if not isinstance(self.counters, ResourceCounters):
            raise TypeError("counters must be ResourceCounters")
        if type(self.call_seeds) is not tuple:
            raise TypeError("call_seeds must be an exact tuple")
        if not all(isinstance(seed, CallSeedReceipt) for seed in self.call_seeds):
            raise TypeError("call_seeds must contain CallSeedReceipt records")
        pairs = [(seed.subject_role, seed.call_index) for seed in self.call_seeds]
        if len(pairs) != len(set(pairs)):
            raise ValueError(
                "call_seeds must not repeat a (subject_role, call_index) pair"
            )
        next_call_index: dict[str, int] = {}
        for seed in self.call_seeds:
            expected = next_call_index.get(seed.subject_role, 0)
            if seed.call_index != expected:
                raise ValueError(
                    "call_seeds must number each subject_role consecutively from 0"
                )
            next_call_index[seed.subject_role] = expected + 1
        if not isinstance(self.failure_kind, FailureKind):
            raise TypeError("failure_kind must be FailureKind")
        if self.failure_kind not in _UNSCORED_FAILURE_KINDS:
            raise ValueError(
                "failure_kind is not registered for an unscored slot receipt"
            )
        _require_artifact_ref(
            self.provider_cost_ref,
            "provider_cost_ref",
            role="provider_cost_closure",
        )
        _require_bool(self.endpoint_readable, "endpoint_readable")
        if self.endpoint_readable:
            raise ValueError("endpoint_readable must be false")


@dataclass(frozen=True, slots=True)
class AttemptReceipt:
    """One branch attempt over the four frozen work orders of a task."""

    attempt_index: Literal[0, 1]
    attempt_ref: ArtifactRef
    work_order_sha256s: tuple[str, str, str, str]
    terminal_receipts: tuple[UnscoredSlotReceipt, ...]
    complete: bool
    endpoint_readable: Literal[False]

    def __post_init__(self) -> None:
        _require_binary_int(self.attempt_index, "attempt_index")
        _require_artifact_ref(
            self.attempt_ref,
            "attempt_ref",
            role="branch_attempt",
        )
        _require_work_order_sha256s(self.work_order_sha256s, "work_order_sha256s")
        if type(self.terminal_receipts) is not tuple:
            raise TypeError("terminal_receipts must be an exact tuple")
        if not all(
            type(receipt) is UnscoredSlotReceipt for receipt in self.terminal_receipts
        ):
            raise TypeError(
                "terminal_receipts must contain exact UnscoredSlotReceipt records"
            )
        if len(self.terminal_receipts) > 4:
            raise ValueError("terminal_receipts must contain at most four receipts")
        complete = _require_bool(self.complete, "complete")
        if complete and len(self.terminal_receipts) != 4:
            raise ValueError("a complete attempt requires exactly four receipts")
        if not complete and len(self.terminal_receipts) > 3:
            raise ValueError("an incomplete attempt requires at most three receipts")
        slot_ids = [receipt.slot_id for receipt in self.terminal_receipts]
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("terminal_receipts must not repeat a slot_id")
        capabilities = [
            receipt.opaque_capability_id for receipt in self.terminal_receipts
        ]
        if len(capabilities) != len(set(capabilities)):
            raise ValueError(
                "terminal_receipts must not repeat an opaque_capability_id"
            )
        _require_bool(self.endpoint_readable, "endpoint_readable")
        if self.endpoint_readable:
            raise ValueError("endpoint_readable must be false")


@dataclass(frozen=True, slots=True)
class FailedSlotReceipt:
    """One branch slot abandoned after an infrastructure failure on both attempts."""

    slot_id: str
    opaque_capability_id: str
    failed_attempt_ref: ArtifactRef
    adverse_event_ref: ArtifactRef
    provider_cost_ref: ArtifactRef
    failure_kind: Literal[FailureKind.INFRASTRUCTURE]
    endpoint_readable: Literal[False]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.slot_id, "slot_id")
        _require_sha256(self.opaque_capability_id, "opaque_capability_id")
        _require_artifact_ref(
            self.failed_attempt_ref,
            "failed_attempt_ref",
            role="branch_attempt",
        )
        _require_artifact_ref(
            self.adverse_event_ref,
            "adverse_event_ref",
            role="branch_adverse_event",
        )
        _require_artifact_ref(
            self.provider_cost_ref,
            "provider_cost_ref",
            role="provider_cost_closure",
        )
        if not isinstance(self.failure_kind, FailureKind):
            raise TypeError("failure_kind must be FailureKind")
        if self.failure_kind is not FailureKind.INFRASTRUCTURE:
            raise ValueError("a failed slot receipt requires the infrastructure kind")
        _require_bool(self.endpoint_readable, "endpoint_readable")
        if self.endpoint_readable:
            raise ValueError("endpoint_readable must be false")


@dataclass(frozen=True, slots=True)
class SlotExecutionReceipt:
    """One published slot outcome bound to the terminal receipt that produced it."""

    source_receipt_sha256: str
    source_kind: Literal["graded_unscored", "failed_second_attempt"]
    grade_receipt: GradeReceipt | None
    outcome: BranchOutcome

    def __post_init__(self) -> None:
        _require_sha256(self.source_receipt_sha256, "source_receipt_sha256")
        if type(self.source_kind) is not str:
            raise TypeError("source_kind must be exact text")
        if self.source_kind not in _EXECUTION_SOURCE_KINDS:
            raise ValueError("source_kind is not registered")
        if self.source_kind == "graded_unscored":
            if not isinstance(self.grade_receipt, GradeReceipt):
                raise TypeError("a graded execution receipt requires a GradeReceipt")
        elif self.grade_receipt is not None:
            raise ValueError("a failed execution receipt must not carry a grade")
        if not isinstance(self.outcome, BranchOutcome):
            raise TypeError("outcome must be BranchOutcome")


@dataclass(frozen=True, slots=True)
class OutageReceipt:
    """One provider outage closure recorded before any endpoint became readable."""

    task_id: str
    provider_event_ref: ArtifactRef
    first_attempt: AttemptReceipt
    detected_before_endpoint_readable: Literal[True]
    work_order_sha256s: tuple[str, str, str, str]
    rerun_index: Literal[1]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.task_id, "task_id")
        _require_artifact_ref(
            self.provider_event_ref,
            "provider_event_ref",
            role="provider_event",
        )
        if type(self.first_attempt) is not AttemptReceipt:
            raise TypeError("first_attempt must be exact AttemptReceipt")
        if self.first_attempt.complete:
            raise ValueError("an outage receipt requires an incomplete first attempt")
        _require_bool(
            self.detected_before_endpoint_readable,
            "detected_before_endpoint_readable",
        )
        if not self.detected_before_endpoint_readable:
            raise ValueError(
                "an outage must be detected before any endpoint became readable"
            )
        _require_work_order_sha256s(self.work_order_sha256s, "work_order_sha256s")
        if self.work_order_sha256s != self.first_attempt.work_order_sha256s:
            raise ValueError(
                "work_order_sha256s must equal the first attempt work orders"
            )
        if type(self.rerun_index) is not int:
            raise TypeError("rerun_index must be an exact int")
        if self.rerun_index != 1:
            raise ValueError("rerun_index must equal 1")


TerminalSlotReceipt = UnscoredSlotReceipt | FailedSlotReceipt


@dataclass(frozen=True, slots=True)
class TaskBlock:
    """One opaque four-slot terminal task block with complete branch closure."""

    study_id: str
    task_id: str
    benchmark: str
    stratum: str
    sensitivity_groups: tuple[GroupLabel, ...]
    frozen_created_at: str
    triggered: bool
    prefix_success: int
    slot_outcomes: tuple[BranchOutcome, BranchOutcome, BranchOutcome, BranchOutcome]
    schedule_ref: ArtifactRef
    prefix_index_ref: ArtifactRef
    assignment_ref: ArtifactRef
    packet_index_ref: ArtifactRef
    analysis_freeze_ref: ArtifactRef
    attempts: tuple[AttemptReceipt, ...] | None
    selected_attempt_index: int | None
    terminal_slot_receipts: tuple[
        TerminalSlotReceipt,
        TerminalSlotReceipt,
        TerminalSlotReceipt,
        TerminalSlotReceipt,
    ] | None
    execution_receipts: tuple[
        SlotExecutionReceipt,
        SlotExecutionReceipt,
        SlotExecutionReceipt,
        SlotExecutionReceipt,
    ] | None
    outage_receipt: OutageReceipt | None
    validity_event_refs: tuple[ArtifactRef, ...]
    pipeline_valid: bool
    validity_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "study_id",
            "task_id",
            "benchmark",
            "stratum",
            "frozen_created_at",
        ):
            _require_nonempty_string(getattr(self, name), name)
        if type(self.sensitivity_groups) is not tuple:
            raise TypeError("sensitivity_groups must be an exact tuple")
        if not all(
            isinstance(group, GroupLabel) for group in self.sensitivity_groups
        ):
            raise TypeError("sensitivity_groups must contain GroupLabel records")
        if not 1 <= len(self.sensitivity_groups) <= 3:
            raise ValueError("sensitivity_groups must carry one to three labels")
        group_kinds = [group.kind for group in self.sensitivity_groups]
        if len(group_kinds) != len(set(group_kinds)):
            raise ValueError("sensitivity_groups must not repeat a GroupKind")
        triggered = _require_bool(self.triggered, "triggered")
        _require_bool(self.pipeline_valid, "pipeline_valid")
        prefix_success = _require_binary_int(self.prefix_success, "prefix_success")
        if type(self.slot_outcomes) is not tuple:
            raise TypeError("slot_outcomes must be an exact tuple")
        if len(self.slot_outcomes) != 4:
            raise ValueError("slot_outcomes must contain exactly four outcomes")
        if not all(
            isinstance(outcome, BranchOutcome) for outcome in self.slot_outcomes
        ):
            raise TypeError("slot_outcomes must contain BranchOutcome records")
        for outcome in self.slot_outcomes:
            if outcome.task_id != self.task_id:
                raise ValueError("slot_outcomes must share the block task_id")
            if outcome.benchmark != self.benchmark:
                raise ValueError("slot_outcomes must share the block benchmark")
            if outcome.prefix_success != prefix_success:
                raise ValueError("slot_outcomes must share the block prefix_success")
        arm_ids = [outcome.opaque_arm_id for outcome in self.slot_outcomes]
        if len(set(arm_ids)) != 4:
            raise ValueError("slot_outcomes must have unique opaque_arm_id values")
        for name, role in _TASK_BLOCK_PARENT_ROLES.items():
            _require_artifact_ref(getattr(self, name), name, role=role)
        if type(self.validity_event_refs) is not tuple:
            raise TypeError("validity_event_refs must be an exact tuple")
        for ref in self.validity_event_refs:
            _require_artifact_ref(ref, "validity_event_refs item")
        if len(self.validity_event_refs) != len(set(self.validity_event_refs)):
            raise ValueError("validity_event_refs must be pairwise distinct")
        if type(self.validity_codes) is not tuple:
            raise TypeError("validity_codes must be an exact tuple")
        for code in self.validity_codes:
            _require_nonempty_string(code, "validity_codes item")
        if len(self.validity_codes) != len(set(self.validity_codes)):
            raise ValueError("validity_codes must be pairwise distinct")
        if not triggered:
            for name in (
                "attempts",
                "selected_attempt_index",
                "terminal_slot_receipts",
                "execution_receipts",
                "outage_receipt",
            ):
                if getattr(self, name) is not None:
                    raise ValueError(f"an untriggered task block requires null {name}")
            return
        if type(self.attempts) is not tuple:
            raise TypeError("a triggered task block requires an attempts tuple")
        if not all(type(attempt) is AttemptReceipt for attempt in self.attempts):
            raise TypeError("attempts must contain exact AttemptReceipt records")
        if not 1 <= len(self.attempts) <= 2:
            raise ValueError("attempts must contain one or two branch attempts")
        if tuple(attempt.attempt_index for attempt in self.attempts) != tuple(
            range(len(self.attempts))
        ):
            raise ValueError("attempts must number attempt_index from 0 in order")
        if type(self.selected_attempt_index) is not int:
            raise TypeError("selected_attempt_index must be an exact int")
        if self.selected_attempt_index not in (0, 1):
            raise ValueError("selected_attempt_index must be 0 or 1")
        if self.selected_attempt_index >= len(self.attempts):
            raise ValueError("selected_attempt_index must address a recorded attempt")
        terminal_receipts = self.terminal_slot_receipts
        if type(terminal_receipts) is not tuple:
            raise TypeError(
                "a triggered task block requires a terminal_slot_receipts tuple"
            )
        if len(terminal_receipts) != 4:
            raise ValueError(
                "terminal_slot_receipts must contain exactly four receipts"
            )
        if not all(
            type(receipt) in (UnscoredSlotReceipt, FailedSlotReceipt)
            for receipt in terminal_receipts
        ):
            raise TypeError(
                "terminal_slot_receipts must contain exact terminal slot receipts"
            )
        execution_receipts = self.execution_receipts
        if type(execution_receipts) is not tuple:
            raise TypeError(
                "a triggered task block requires an execution_receipts tuple"
            )
        if len(execution_receipts) != 4:
            raise ValueError("execution_receipts must contain exactly four receipts")
        if not all(
            type(receipt) is SlotExecutionReceipt for receipt in execution_receipts
        ):
            raise TypeError(
                "execution_receipts must contain exact SlotExecutionReceipt records"
            )
        if self.outage_receipt is not None and type(
            self.outage_receipt
        ) is not OutageReceipt:
            raise TypeError("outage_receipt must be exact OutageReceipt or None")
        slot_ids = [receipt.slot_id for receipt in terminal_receipts]
        if len(set(slot_ids)) != 4:
            raise ValueError("terminal_slot_receipts must have unique slot IDs")
        capabilities = [
            receipt.opaque_capability_id for receipt in terminal_receipts
        ]
        if len(set(capabilities)) != 4:
            raise ValueError(
                "terminal_slot_receipts must have unique opaque_capability_id values"
            )
        selected_attempt = self.attempts[self.selected_attempt_index]
        if any(
            attempt.work_order_sha256s != selected_attempt.work_order_sha256s
            for attempt in self.attempts
        ):
            raise ValueError(
                "every attempt must reuse the selected attempt work orders"
            )
        failed_second_attempt = (
            len(self.attempts) == 2
            and self.selected_attempt_index == 1
            and all(attempt.complete is False for attempt in self.attempts)
        )
        if failed_second_attempt:
            if not all(
                type(receipt) is FailedSlotReceipt for receipt in terminal_receipts
            ):
                raise ValueError(
                    "a failed second attempt requires four failed slot receipts"
                )
            if not all(
                receipt.source_kind == "failed_second_attempt"
                for receipt in execution_receipts
            ):
                raise ValueError(
                    "a failed second attempt requires failed execution receipts"
                )
            if self.outage_receipt is None:
                raise ValueError("a failed second attempt requires an outage receipt")
            # A FailedSlotReceipt can never equal an attempt's embedded
            # UnscoredSlotReceipt, so descent is proved by reference instead:
            # every failed slot must name the selected attempt it died in.
            if any(
                receipt.failed_attempt_ref != selected_attempt.attempt_ref
                for receipt in terminal_receipts
            ):
                raise ValueError(
                    "failed slot receipts must name the selected failed attempt"
                )
            if self.outage_receipt.first_attempt != self.attempts[0]:
                raise ValueError(
                    "the outage receipt must embed this block's first attempt"
                )
        else:
            if not selected_attempt.complete:
                raise ValueError("the selected attempt must be complete")
            if not all(
                type(receipt) is UnscoredSlotReceipt for receipt in terminal_receipts
            ):
                raise ValueError(
                    "a graded task block requires four unscored slot receipts"
                )
            if terminal_receipts != selected_attempt.terminal_receipts:
                raise ValueError(
                    "terminal_slot_receipts must equal the selected attempt receipts"
                )
            if not all(
                receipt.source_kind == "graded_unscored"
                for receipt in execution_receipts
            ):
                raise ValueError(
                    "a graded task block requires graded execution receipts"
                )
        outcomes = tuple(receipt.outcome for receipt in execution_receipts)
        if outcomes != self.slot_outcomes:
            raise ValueError(
                "execution receipt outcomes must equal slot_outcomes in order"
            )
        # Every published outcome must name the terminal receipt it came from,
        # by digest and by slot position.  Without this, a block could pair
        # slot 0's outcome with slot 3's terminal evidence and still validate.
        for index, (terminal, execution) in enumerate(
            zip(terminal_receipts, execution_receipts, strict=True)
        ):
            if execution.source_receipt_sha256 != terminal_receipt_digest(terminal):
                raise ValueError(
                    f"execution_receipts[{index}] does not descend from "
                    f"terminal_slot_receipts[{index}]"
                )
            if execution.outcome.opaque_arm_id != terminal.opaque_capability_id:
                raise ValueError(
                    f"execution_receipts[{index}] outcome names a different "
                    "opaque slot than its terminal receipt"
                )


def work_order_digest(order: OpaqueSlotWorkOrder) -> str:
    """Return the frozen digest a worker-visible branch work order commits to."""

    if type(order) is not OpaqueSlotWorkOrder:
        raise TypeError("order must be exact OpaqueSlotWorkOrder")
    return hashlib.sha256(
        canonical_json_bytes(asdict(order), indent=None)
    ).hexdigest()


def terminal_receipt_digest(receipt: UnscoredSlotReceipt | FailedSlotReceipt) -> str:
    """Return the digest an execution receipt must name as its source.

    The two terminal shapes are distinguished by a kind tag so a failed slot
    receipt can never collide with an unscored one that happens to share field
    values.
    """

    if type(receipt) is UnscoredSlotReceipt:
        kind = "unscored_slot_receipt"
    elif type(receipt) is FailedSlotReceipt:
        kind = "failed_slot_receipt"
    else:
        raise TypeError("receipt must be an exact terminal slot receipt")
    return hashlib.sha256(
        canonical_json_bytes(
            {"kind": kind, "receipt": asdict(receipt)},
            indent=None,
        )
    ).hexdigest()


__all__ = [
    "AttemptReceipt",
    "FailedSlotReceipt",
    "OutageReceipt",
    "SlotExecutionReceipt",
    "TaskBlock",
    "TerminalSlotReceipt",
    "UnscoredSlotReceipt",
    "terminal_receipt_digest",
    "work_order_digest",
]
