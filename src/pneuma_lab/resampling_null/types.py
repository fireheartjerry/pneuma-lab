"""Stable value records for zero-spend resampling-null experiments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from pathlib import PurePosixPath
from typing import Literal, cast


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
