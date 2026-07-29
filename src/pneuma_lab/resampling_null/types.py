"""Stable value records for zero-spend resampling-null experiments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from math import isfinite
from pathlib import PurePosixPath
from typing import Literal, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes


class Arm(str, Enum):
    """Canonical experimental arms."""

    REAL = "REAL"
    SHAM = "SHAM"
    NONE = "NONE"
    RESAMPLE = "RESAMPLE"


class Treatment(str, Enum):
    """Canonical treatments before a slot is oriented to its packet."""

    REAL = "REAL"
    SHAM = "SHAM"
    NO_PACKET = "NO_PACKET"


class TriggerReason(str, Enum):
    """Closed reasons for freezing a packet-intervention opportunity."""

    FIRST_ELIGIBLE_MUTATION = "first_eligible_mutation"
    FOURTH_TOOL_CALL = "fourth_tool_call"
    NO_INTERVENTION_OPPORTUNITY = "no_intervention_opportunity"


class FailureKind(str, Enum):
    """Closed controller terminal/failure classifications."""

    NONE = "none"
    MODEL = "model"
    MALFORMED_ACTION = "malformed_action"
    TOKEN_CAP = "token_cap"
    TOOL_CAP = "tool_cap"
    TIMEOUT = "timeout"
    INFRASTRUCTURE = "infrastructure"


class AssignmentMode(str, Enum):
    """Closed study modes for donor assignment."""

    SYNTHETIC = "synthetic_derangement"
    CONFIRMATION = "confirmation_lineage_matching"


class MatchingAlgorithm(str, Enum):
    """Assignment algorithms permitted by each study mode."""

    SYNTHETIC = "synthetic_cyclic_offset_v1"
    CONFIRMATION = "exact_constrained_min_cost_v1"


class GroupKind(str, Enum):
    """Registered sensitivity-label dimensions."""

    LANGUAGE = "language"
    DOMAIN = "domain"
    ISSUE_FAMILY = "issue_family"


class Verdict(str, Enum):
    """Closed interpretation vocabulary for a completed comparison."""

    CAUSAL_CONTENT = "CAUSAL_CONTENT"
    SHAM_PACKET_ONLY = "SHAM_PACKET_ONLY"
    RESAMPLING_CONSISTENT = "RESAMPLING_CONSISTENT"
    HARMFUL_OR_MISDIRECTING = "HARMFUL_OR_MISDIRECTING"
    UNRESOLVED_RESAMPLING = "UNRESOLVED_RESAMPLING"
    PIPELINE_INVALID = "PIPELINE_INVALID"
    FEASIBILITY_NO_GO = "FEASIBILITY_NO_GO"


def _require_nonempty_string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    validated = value
    if not validated:
        raise ValueError(f"{name} must be non-empty")
    return validated


def _require_exact_nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an exact int")
    validated = cast(int, value)
    if validated < 0:
        raise ValueError(f"{name} must be non-negative")
    return validated


def _require_sha256(value: object, name: str) -> str:
    validated = _require_nonempty_string(value, name)
    if len(validated) != 64 or any(char not in "0123456789abcdef" for char in validated):
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")
    return validated


def _require_seed(value: object, name: str) -> int:
    validated = _require_exact_nonnegative_int(value, name)
    if validated >= 2**64:
        raise ValueError(f"{name} must be smaller than 2**64")
    return validated


def _require_finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    validated = float(value)
    if not isfinite(validated):
        raise ValueError(f"{name} must be finite")
    return 0.0 if validated == 0.0 else validated


def _require_canonical_json_object_text(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact text")

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, nested in pairs:
            if key in result:
                raise ValueError(f"{name} contains duplicate key {key!r}")
            result[key] = nested
        return result

    try:
        parsed = json.loads(
            value,
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(f"{name} contains {constant!r}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} must be strict JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must encode a JSON object")
    if canonical_json_bytes(parsed, indent=None).decode("utf-8") != value:
        raise ValueError(f"{name} must use compact canonical JSON bytes")
    return value


@dataclass(frozen=True, slots=True)
class GroupLabel:
    kind: GroupKind
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, GroupKind):
            raise TypeError("kind must be GroupKind")
        _require_nonempty_string(self.value, "value")


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str
    sensitivity_groups: tuple[GroupLabel, ...]

    def __post_init__(self) -> None:
        for name in ("task_id", "benchmark", "stratum", "lineage"):
            _require_nonempty_string(getattr(self, name), name)
        if not isinstance(self.sensitivity_groups, tuple):
            raise TypeError("sensitivity_groups must be a tuple")
        if not self.sensitivity_groups:
            raise ValueError("sensitivity_groups must not be empty")
        if not all(isinstance(group, GroupLabel) for group in self.sensitivity_groups):
            raise TypeError("sensitivity_groups must contain GroupLabel records")
        kinds = [group.kind for group in self.sensitivity_groups]
        if len(kinds) != len(set(kinds)):
            raise ValueError("sensitivity_groups must not repeat a GroupKind")


@dataclass(frozen=True, slots=True)
class BranchSlot:
    slot_id: str
    seed: int
    execution_order: int
    hardware_lane: int

    def __post_init__(self) -> None:
        _require_nonempty_string(self.slot_id, "slot_id")
        _require_seed(self.seed, "seed")
        _require_exact_nonnegative_int(self.execution_order, "execution_order")
        _require_exact_nonnegative_int(self.hardware_lane, "hardware_lane")


@dataclass(frozen=True, slots=True)
class ResourceCounters:
    generated_tokens: int
    model_calls: int
    tool_calls: int
    wall_clock_ms: int

    def __post_init__(self) -> None:
        for name in ("generated_tokens", "model_calls", "tool_calls", "wall_clock_ms"):
            _require_exact_nonnegative_int(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class BranchOutcome:
    task_id: str
    benchmark: str
    opaque_arm_id: str
    success: int
    prefix_success: int
    partial_reward: float
    infrastructure_failure: bool
    counters: ResourceCounters
    artifact_ref: ArtifactRef

    def __post_init__(self) -> None:
        for name in ("task_id", "benchmark", "opaque_arm_id"):
            _require_nonempty_string(getattr(self, name), name)
        for name in ("success", "prefix_success"):
            value = getattr(self, name)
            if type(value) is not int:
                raise TypeError(f"{name} must be an exact int")
            if value not in (0, 1):
                raise ValueError(f"{name} must be 0 or 1")
        partial_reward = _require_finite_float(self.partial_reward, "partial_reward")
        object.__setattr__(self, "partial_reward", partial_reward)
        if type(self.infrastructure_failure) is not bool:
            raise TypeError("infrastructure_failure must be bool")
        if self.infrastructure_failure and self.success != 0:
            raise ValueError("infrastructure_failure requires success == 0")
        if not isinstance(self.counters, ResourceCounters):
            raise TypeError("counters must be ResourceCounters")
        if not isinstance(self.artifact_ref, ArtifactRef):
            raise TypeError("artifact_ref must be ArtifactRef")


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    role: str
    relative_path: str
    sha256: str
    byte_count: int
    media_type: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.role, "role")
        relative_path = _require_nonempty_string(self.relative_path, "relative_path")
        if (
            "\0" in relative_path
            or "\\" in relative_path
            or relative_path.startswith("/")
            or (len(relative_path) >= 2 and relative_path[0].isalpha() and relative_path[1] == ":")
        ):
            raise ValueError("relative_path must be a normalized POSIX-relative path")
        path = PurePosixPath(relative_path)
        if ".." in path.parts or path.as_posix() != relative_path or relative_path == ".":
            raise ValueError("relative_path must be a normalized POSIX-relative path")
        _require_sha256(self.sha256, "sha256")
        _require_exact_nonnegative_int(self.byte_count, "byte_count")
        _require_nonempty_string(self.media_type, "media_type")


@dataclass(frozen=True, slots=True)
class ScheduleSelection:
    """Closed completed-power decision exposed to schedule construction."""

    schedule_authority: Literal[
        "synthetic_validation",
        "roster_bound_selection",
    ]
    selected_tier: Literal[120, 160] | None
    selected_task_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schedule_authority not in (
            "synthetic_validation",
            "roster_bound_selection",
        ):
            raise ValueError("schedule_authority is not recognized")
        if self.schedule_authority == "synthetic_validation":
            if self.selected_tier is not None:
                raise ValueError("synthetic selection must not select a tier")
        elif self.selected_tier not in (120, 160):
            raise ValueError("roster-bound selection requires tier 120 or 160")
        if not isinstance(self.selected_task_ids, tuple):
            raise TypeError("selected_task_ids must be a tuple")
        if not self.selected_task_ids:
            raise ValueError("selected_task_ids must not be empty")
        for task_id in self.selected_task_ids:
            _require_nonempty_string(task_id, "selected_task_ids item")
        if len(self.selected_task_ids) != len(set(self.selected_task_ids)):
            raise ValueError("selected_task_ids must be pairwise distinct")


@dataclass(frozen=True, slots=True)
class BranchSlotSet:
    """The four execution slots used for one paired resampling comparison."""

    slots: tuple[BranchSlot, BranchSlot, BranchSlot, BranchSlot]

    def __post_init__(self) -> None:
        if not isinstance(self.slots, tuple):
            raise TypeError("slots must be a tuple")
        if len(self.slots) != 4:
            raise ValueError("slots must contain exactly four branch slots")
        if not all(isinstance(slot, BranchSlot) for slot in self.slots):
            raise TypeError("slots must contain only BranchSlot records")
        for attribute in ("slot_id", "seed", "execution_order"):
            values = [getattr(slot, attribute) for slot in self.slots]
            if len(values) != len(set(values)):
                raise ValueError(f"slots must have pairwise-distinct {attribute} values")


@dataclass(frozen=True, slots=True)
class TaskSchedule:
    task: TaskSpec
    prefix_seed: int
    slots: BranchSlotSet
    provider_lane: str

    def __post_init__(self) -> None:
        if not isinstance(self.task, TaskSpec):
            raise TypeError("task must be TaskSpec")
        _require_seed(self.prefix_seed, "prefix_seed")
        if not isinstance(self.slots, BranchSlotSet):
            raise TypeError("slots must be BranchSlotSet")
        _require_nonempty_string(self.provider_lane, "provider_lane")


@dataclass(frozen=True, slots=True)
class FrozenVerifierReceipt:
    task_id: str
    schedule_sha256: str
    snapshot_ref: ArtifactRef
    verifier_artifact_ref: ArtifactRef
    finding_count: int

    def __post_init__(self) -> None:
        _require_nonempty_string(self.task_id, "task_id")
        _require_sha256(self.schedule_sha256, "schedule_sha256")
        if not isinstance(self.snapshot_ref, ArtifactRef):
            raise TypeError("snapshot_ref must be ArtifactRef")
        if not isinstance(self.verifier_artifact_ref, ArtifactRef):
            raise TypeError("verifier_artifact_ref must be ArtifactRef")
        _require_exact_nonnegative_int(self.finding_count, "finding_count")


@dataclass(frozen=True, slots=True)
class AssignmentPrefixTaskView:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str
    sensitivity_groups: tuple[GroupLabel, ...]
    trigger_reason: TriggerReason
    verifier_component_class: str
    objective_finding_count: int
    normalized_report_token_count: int
    telecom_issue_family: str | None

    def __post_init__(self) -> None:
        for name in (
            "task_id",
            "benchmark",
            "stratum",
            "lineage",
            "verifier_component_class",
        ):
            _require_nonempty_string(getattr(self, name), name)
        if not isinstance(self.sensitivity_groups, tuple) or not self.sensitivity_groups:
            raise TypeError("sensitivity_groups must be a non-empty tuple")
        if not all(
            isinstance(group, GroupLabel) for group in self.sensitivity_groups
        ):
            raise TypeError("sensitivity_groups must be a tuple of GroupLabel records")
        group_kinds = [group.kind for group in self.sensitivity_groups]
        if len(group_kinds) != len(set(group_kinds)):
            raise ValueError("sensitivity_groups must not repeat a GroupKind")
        if not isinstance(self.trigger_reason, TriggerReason):
            raise TypeError("trigger_reason must be TriggerReason")
        _require_exact_nonnegative_int(
            self.objective_finding_count,
            "objective_finding_count",
        )
        _require_exact_nonnegative_int(
            self.normalized_report_token_count,
            "normalized_report_token_count",
        )
        if self.telecom_issue_family is not None:
            _require_nonempty_string(
                self.telecom_issue_family,
                "telecom_issue_family",
            )


@dataclass(frozen=True, slots=True)
class AssignmentPrefixView:
    study_id: str
    schedule_sha256: str
    tasks: tuple[AssignmentPrefixTaskView, ...]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.study_id, "study_id")
        _require_sha256(self.schedule_sha256, "schedule_sha256")
        if not isinstance(self.tasks, tuple) or not self.tasks:
            raise TypeError("tasks must be a non-empty tuple")
        if not all(isinstance(task, AssignmentPrefixTaskView) for task in self.tasks):
            raise TypeError("tasks must contain AssignmentPrefixTaskView records")
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("prefix-view task IDs must be unique")


@dataclass(frozen=True, slots=True)
class AllocationReceipt:
    task_id: str
    slot_ids_by_ordinal: tuple[str, str, str, str]
    treatment_allocation_index: int
    allocation_rejection_counter: int
    no_packet_orientation_bit: int
    orientation_rejection_counter: int
    slot_capabilities: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.task_id, "task_id")
        if (
            not isinstance(self.slot_ids_by_ordinal, tuple)
            or len(self.slot_ids_by_ordinal) != 4
        ):
            raise TypeError("slot_ids_by_ordinal must be an exact four-tuple")
        for slot_id in self.slot_ids_by_ordinal:
            _require_nonempty_string(slot_id, "slot_ids_by_ordinal item")
        if len(set(self.slot_ids_by_ordinal)) != 4:
            raise ValueError("slot_ids_by_ordinal must be unique")
        if type(self.treatment_allocation_index) is not int or not (
            0 <= self.treatment_allocation_index < 12
        ):
            raise ValueError("treatment_allocation_index must be in [0, 12)")
        for name in (
            "allocation_rejection_counter",
            "orientation_rejection_counter",
        ):
            _require_exact_nonnegative_int(getattr(self, name), name)
        if (
            type(self.no_packet_orientation_bit) is not int
            or self.no_packet_orientation_bit not in (0, 1)
        ):
            raise ValueError("no_packet_orientation_bit must be 0 or 1")
        if (
            not isinstance(self.slot_capabilities, tuple)
            or len(self.slot_capabilities) != 4
        ):
            raise TypeError("slot_capabilities must be an exact four-tuple")
        for expected_slot, entry in zip(
            self.slot_ids_by_ordinal,
            self.slot_capabilities,
            strict=True,
        ):
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise TypeError("slot_capabilities entries must be pairs")
            slot_id, capability = entry
            if slot_id != expected_slot:
                raise ValueError("slot_capabilities must use slot ordinal order")
            _require_sha256(capability, "slot capability")
        capabilities = [capability for _, capability in self.slot_capabilities]
        if len(set(capabilities)) != 4:
            raise ValueError("slot capabilities must be unique within a task")


@dataclass(frozen=True, slots=True)
class DonorCandidateReceipt:
    donor_task_id: str
    donor_lineage: str
    primary_cost: tuple[int, int, int]
    fallback_code: (
        Literal["cross_family_component_match_unavailable"] | None
    )
    tie_hmac_sha256: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.donor_task_id, "donor_task_id")
        _require_nonempty_string(self.donor_lineage, "donor_lineage")
        if not isinstance(self.primary_cost, tuple) or len(self.primary_cost) != 3:
            raise TypeError("primary_cost must be an exact three-tuple")
        for value in self.primary_cost:
            _require_exact_nonnegative_int(value, "primary_cost item")
        if self.fallback_code not in (
            None,
            "cross_family_component_match_unavailable",
        ):
            raise ValueError("fallback_code is not recognized")
        _require_sha256(self.tie_hmac_sha256, "tie_hmac_sha256")


@dataclass(frozen=True, slots=True)
class MatchedDonorReceipt:
    kind: Literal["matched"]
    task_id: str
    donor_task_id: str
    task_lineage: str
    donor_lineage: str
    assignment_mode: AssignmentMode
    matching_algorithm: MatchingAlgorithm
    stratum_key: tuple[str, ...]
    assignment_prefix_view_sha256: str
    candidates: tuple[DonorCandidateReceipt, ...]
    chosen_primary_cost: tuple[int, int, int]
    matching_proof_ref: ArtifactRef

    def __post_init__(self) -> None:
        if self.kind != "matched":
            raise ValueError("matched donor receipt kind must equal matched")
        for name in (
            "task_id",
            "donor_task_id",
            "task_lineage",
            "donor_lineage",
        ):
            _require_nonempty_string(getattr(self, name), name)
        if self.task_id == self.donor_task_id:
            raise ValueError("matched donor task must differ from focal task")
        if self.task_lineage == self.donor_lineage:
            raise ValueError("matched donor lineage must differ from focal lineage")
        if not isinstance(self.assignment_mode, AssignmentMode):
            raise TypeError("assignment_mode must be AssignmentMode")
        if not isinstance(self.matching_algorithm, MatchingAlgorithm):
            raise TypeError("matching_algorithm must be MatchingAlgorithm")
        if (
            self.assignment_mode is AssignmentMode.SYNTHETIC
            and self.matching_algorithm is not MatchingAlgorithm.SYNTHETIC
        ) or (
            self.assignment_mode is AssignmentMode.CONFIRMATION
            and self.matching_algorithm is not MatchingAlgorithm.CONFIRMATION
        ):
            raise ValueError("assignment mode/algorithm pair differs")
        if not isinstance(self.stratum_key, tuple) or not self.stratum_key:
            raise TypeError("stratum_key must be a non-empty tuple")
        for component in self.stratum_key:
            _require_nonempty_string(component, "stratum_key item")
        _require_sha256(
            self.assignment_prefix_view_sha256,
            "assignment_prefix_view_sha256",
        )
        if not isinstance(self.candidates, tuple) or not self.candidates:
            raise TypeError("candidates must be a non-empty tuple")
        if not all(
            isinstance(candidate, DonorCandidateReceipt)
            for candidate in self.candidates
        ):
            raise TypeError("candidates must contain DonorCandidateReceipt")
        donor_ids = [candidate.donor_task_id for candidate in self.candidates]
        if len(donor_ids) != len(set(donor_ids)):
            raise ValueError("candidate donor task IDs must be unique")
        if self.donor_task_id not in donor_ids:
            raise ValueError("chosen donor must appear in candidates")
        if (
            not isinstance(self.chosen_primary_cost, tuple)
            or len(self.chosen_primary_cost) != 3
        ):
            raise TypeError("chosen_primary_cost must be an exact three-tuple")
        for value in self.chosen_primary_cost:
            _require_exact_nonnegative_int(value, "chosen_primary_cost item")
        chosen = next(
            candidate
            for candidate in self.candidates
            if candidate.donor_task_id == self.donor_task_id
        )
        if chosen.primary_cost != self.chosen_primary_cost:
            raise ValueError("chosen_primary_cost differs from chosen candidate")
        if not isinstance(self.matching_proof_ref, ArtifactRef):
            raise TypeError("matching_proof_ref must be ArtifactRef")


@dataclass(frozen=True, slots=True)
class NoTriggerDonorReceipt:
    kind: Literal["not_applicable_no_trigger"]
    task_id: str
    trigger_reason: Literal["no_intervention_opportunity"]
    assignment_prefix_view_sha256: str

    def __post_init__(self) -> None:
        if self.kind != "not_applicable_no_trigger":
            raise ValueError("no-trigger donor receipt kind differs")
        _require_nonempty_string(self.task_id, "task_id")
        if self.trigger_reason != "no_intervention_opportunity":
            raise ValueError("no-trigger receipt has wrong trigger reason")
        _require_sha256(
            self.assignment_prefix_view_sha256,
            "assignment_prefix_view_sha256",
        )


DonorMatchReceipt = MatchedDonorReceipt | NoTriggerDonorReceipt


@dataclass(frozen=True, slots=True)
class TaskAssignment:
    task_id: str
    task_lineage: str
    donor_match_kind: Literal["matched", "not_applicable_no_trigger"]
    donor_task_id: str | None
    donor_lineage: str | None
    slot_arms: tuple[tuple[str, Arm], ...]
    schedule_sha256: str
    prefix_index_sha256: str

    def __post_init__(self) -> None:
        for name in ("task_id", "task_lineage"):
            _require_nonempty_string(getattr(self, name), name)
        donor_match_kind = _require_nonempty_string(self.donor_match_kind, "donor_match_kind")
        if donor_match_kind == "matched":
            donor_task_id = _require_nonempty_string(self.donor_task_id, "donor_task_id")
            donor_lineage = _require_nonempty_string(self.donor_lineage, "donor_lineage")
            if self.task_id == donor_task_id:
                raise ValueError("task_id and donor_task_id must differ")
            if self.task_lineage == donor_lineage:
                raise ValueError("task_lineage and donor_lineage must differ")
        elif donor_match_kind == "not_applicable_no_trigger":
            if self.donor_task_id is not None or self.donor_lineage is not None:
                raise ValueError("not_applicable_no_trigger requires null donor fields")
        else:
            raise ValueError("donor_match_kind must be matched or not_applicable_no_trigger")
        if not isinstance(self.slot_arms, tuple):
            raise TypeError("slot_arms must be a tuple")
        if len(self.slot_arms) != 4:
            raise ValueError("slot_arms must contain exactly four entries")
        slot_ids: list[str] = []
        arms: list[Arm] = []
        for entry in self.slot_arms:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise TypeError("slot_arms entries must be (slot_id, Arm) tuples")
            slot_id, arm = entry
            _require_nonempty_string(slot_id, "slot_id")
            if not isinstance(arm, Arm):
                raise TypeError("slot_arms values must be Arm members")
            slot_ids.append(slot_id)
            arms.append(arm)
        if len(slot_ids) != len(set(slot_ids)):
            raise ValueError("slot_arms must have unique slot IDs")
        if set(arms) != set(Arm) or len(arms) != len(set(arms)):
            raise ValueError("slot_arms must assign every Arm exactly once")
        _require_sha256(self.schedule_sha256, "schedule_sha256")
        _require_sha256(self.prefix_index_sha256, "prefix_index_sha256")


@dataclass(frozen=True, slots=True)
class AssignmentLedger:
    study_id: str
    frozen_created_at: str
    manifest_ref: ArtifactRef
    schedule_ref: ArtifactRef
    prefix_index_ref: ArtifactRef
    matching_program_ref: ArtifactRef
    assignment_master_key_commitment_sha256: str
    assignment_prefix_view_sha256: str
    assignment_mode: AssignmentMode
    matching_proof_refs: tuple[ArtifactRef, ...]
    assignments: tuple[TaskAssignment, ...]
    allocation_receipts: tuple[AllocationReceipt, ...]
    donor_match_receipts: tuple[DonorMatchReceipt, ...]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.study_id, "study_id")
        _require_nonempty_string(self.frozen_created_at, "frozen_created_at")
        for name in (
            "manifest_ref",
            "schedule_ref",
            "prefix_index_ref",
            "matching_program_ref",
        ):
            if not isinstance(getattr(self, name), ArtifactRef):
                raise TypeError(f"{name} must be ArtifactRef")
        _require_sha256(
            self.assignment_master_key_commitment_sha256,
            "assignment_master_key_commitment_sha256",
        )
        _require_sha256(
            self.assignment_prefix_view_sha256,
            "assignment_prefix_view_sha256",
        )
        if not isinstance(self.assignment_mode, AssignmentMode):
            raise TypeError("assignment_mode must be AssignmentMode")
        for name, expected_type in (
            ("matching_proof_refs", ArtifactRef),
            ("assignments", TaskAssignment),
            ("allocation_receipts", AllocationReceipt),
        ):
            value = getattr(self, name)
            if not isinstance(value, tuple) or not all(
                isinstance(item, expected_type) for item in value
            ):
                raise TypeError(f"{name} has wrong immutable item type")
        if not self.assignments:
            raise ValueError("assignments must not be empty")
        if (
            not isinstance(self.donor_match_receipts, tuple)
            or not all(
                isinstance(
                    item,
                    (MatchedDonorReceipt, NoTriggerDonorReceipt),
                )
                for item in self.donor_match_receipts
            )
        ):
            raise TypeError("donor_match_receipts has wrong immutable item type")
        task_orders = (
            [item.task_id for item in self.assignments],
            [item.task_id for item in self.allocation_receipts],
            [item.task_id for item in self.donor_match_receipts],
        )
        if not task_orders[0] or any(order != task_orders[0] for order in task_orders[1:]):
            raise ValueError("ledger arrays must share exact task order")
        if len(self.matching_proof_refs) != len(set(self.matching_proof_refs)):
            raise ValueError("matching_proof_refs must be unique")


@dataclass(frozen=True, slots=True)
class ContextMessage:
    role: str
    content: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.role, "role")
        if type(self.content) is not str:
            raise TypeError("content must be exact text")


@dataclass(frozen=True, slots=True)
class ToolCall:
    call_id: str
    name: str
    canonical_arguments_json: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.call_id, "call_id")
        _require_nonempty_string(self.name, "name")
        _require_canonical_json_object_text(
            self.canonical_arguments_json,
            "canonical_arguments_json",
        )


@dataclass(frozen=True, slots=True)
class SubjectContext:
    messages: tuple[ContextMessage, ...]
    private_guidance: str | None

    def __post_init__(self) -> None:
        if type(self.messages) is not tuple:
            raise TypeError("messages must be an exact tuple")
        if not all(type(message) is ContextMessage for message in self.messages):
            raise TypeError("messages must contain exact ContextMessage records")
        if self.private_guidance is not None:
            _require_nonempty_string(self.private_guidance, "private_guidance")


@dataclass(frozen=True, slots=True)
class PrefixCaps:
    generated_tokens: int
    model_calls: int
    tool_calls: int
    wall_clock_ms: int

    def __post_init__(self) -> None:
        for name in (
            "generated_tokens",
            "model_calls",
            "tool_calls",
            "wall_clock_ms",
        ):
            _require_exact_nonnegative_int(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class BranchCaps:
    generated_tokens: int
    model_calls: int
    tool_calls: int
    wall_clock_ms: int
    pending_prefix_calls_count_against_tool_cap: Literal[True]

    def __post_init__(self) -> None:
        for name in (
            "generated_tokens",
            "model_calls",
            "tool_calls",
            "wall_clock_ms",
        ):
            _require_exact_nonnegative_int(getattr(self, name), name)
        if type(self.pending_prefix_calls_count_against_tool_cap) is not bool:
            raise TypeError(
                "pending_prefix_calls_count_against_tool_cap must be bool"
            )
        if not self.pending_prefix_calls_count_against_tool_cap:
            raise ValueError(
                "pending prefix calls must count against the branch tool cap"
            )


@dataclass(frozen=True, slots=True)
class SimulatorCaps:
    aggregate_generated_tokens: int
    aggregate_model_calls: int
    aggregate_turns: int
    per_call_generated_tokens: int
    per_call_turns: int

    def __post_init__(self) -> None:
        for name in (
            "aggregate_generated_tokens",
            "aggregate_model_calls",
            "aggregate_turns",
            "per_call_generated_tokens",
            "per_call_turns",
        ):
            _require_exact_nonnegative_int(getattr(self, name), name)


@dataclass(frozen=True, slots=True)
class GradeReceipt:
    success: int
    partial_reward: float
    infrastructure_failure: bool
    artifact_ref: ArtifactRef

    def __post_init__(self) -> None:
        if type(self.success) is not int:
            raise TypeError("success must be an exact int")
        if self.success not in (0, 1):
            raise ValueError("success must be 0 or 1")
        partial_reward = _require_finite_float(
            self.partial_reward,
            "partial_reward",
        )
        object.__setattr__(self, "partial_reward", partial_reward)
        if type(self.infrastructure_failure) is not bool:
            raise TypeError("infrastructure_failure must be bool")
        if self.infrastructure_failure and self.success != 0:
            raise ValueError("infrastructure failure requires success == 0")
        if not isinstance(self.artifact_ref, ArtifactRef):
            raise TypeError("artifact_ref must be ArtifactRef")


@dataclass(frozen=True, slots=True)
class CallSeedReceipt:
    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int

    def __post_init__(self) -> None:
        if type(self.subject_role) is not str:
            raise TypeError("subject_role must be exact str")
        if self.subject_role not in ("primary_subject", "user_simulator"):
            raise ValueError("subject_role is not registered")
        _require_seed(self.call_index, "call_index")
        _require_seed(self.seed, "seed")


@dataclass(frozen=True, slots=True)
class SubjectTurn:
    text: str
    tool_calls: tuple[ToolCall, ...]
    generated_tokens: int
    finish_reason: str | None

    def __post_init__(self) -> None:
        if type(self.text) is not str:
            raise TypeError("text must be exact text")
        if type(self.tool_calls) is not tuple:
            raise TypeError("tool_calls must be an exact tuple")
        if not all(type(call) is ToolCall for call in self.tool_calls):
            raise TypeError("tool_calls must contain exact ToolCall records")
        call_ids = [call.call_id for call in self.tool_calls]
        if len(call_ids) != len(set(call_ids)):
            raise ValueError("tool_calls must not repeat call_id")
        _require_exact_nonnegative_int(
            self.generated_tokens,
            "generated_tokens",
        )
        if self.finish_reason is not None:
            _require_nonempty_string(self.finish_reason, "finish_reason")


@dataclass(frozen=True, slots=True)
class ToolBoundary:
    tool_call_count: int
    completed: bool
    mutated: bool
    verifier_eligible: bool
    failure_kind: FailureKind

    def __post_init__(self) -> None:
        _require_exact_nonnegative_int(self.tool_call_count, "tool_call_count")
        for name in ("completed", "mutated", "verifier_eligible"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool")
        if not isinstance(self.failure_kind, FailureKind):
            raise TypeError("failure_kind must be FailureKind")
        if not self.completed and (
            self.mutated
            or self.verifier_eligible
            or self.failure_kind is FailureKind.NONE
        ):
            raise ValueError(
                "incomplete boundary cannot mutate/be eligible/succeed"
            )


@dataclass(frozen=True, slots=True)
class OpaqueSlotIdentity:
    slot_id: str
    opaque_capability_id: str
    seed: int
    execution_order: int
    hardware_lane: int

    def __post_init__(self) -> None:
        _require_nonempty_string(self.slot_id, "slot_id")
        _require_sha256(self.opaque_capability_id, "opaque_capability_id")
        _require_seed(self.seed, "seed")
        _require_exact_nonnegative_int(
            self.execution_order,
            "execution_order",
        )
        _require_exact_nonnegative_int(self.hardware_lane, "hardware_lane")
