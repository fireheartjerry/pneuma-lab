"""Stable value records for zero-spend resampling-null experiments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite
from pathlib import PurePosixPath


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


class Verdict(str, Enum):
    """Closed interpretation vocabulary for a completed comparison."""

    CAUSAL_CONTENT = "CAUSAL_CONTENT"
    SHAM_PACKET_ONLY = "SHAM_PACKET_ONLY"
    RESAMPLING_CONSISTENT = "RESAMPLING_CONSISTENT"
    HARMFUL_OR_MISDIRECTING = "HARMFUL_OR_MISDIRECTING"
    UNRESOLVED_RESAMPLING = "UNRESOLVED_RESAMPLING"
    PIPELINE_INVALID = "PIPELINE_INVALID"
    FEASIBILITY_NO_GO = "FEASIBILITY_NO_GO"


def _require_nonempty_string(value: object, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _require_exact_nonnegative_int(value: object, name: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{name} must be an exact int")
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _require_sha256(value: object, name: str) -> None:
    _require_nonempty_string(value, name)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")


def _require_seed(value: object, name: str) -> None:
    _require_exact_nonnegative_int(value, name)
    if value >= 2**64:
        raise ValueError(f"{name} must be smaller than 2**64")


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    benchmark: str
    stratum: str
    lineage: str

    def __post_init__(self) -> None:
        for name in ("task_id", "benchmark", "stratum", "lineage"):
            _require_nonempty_string(getattr(self, name), name)


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
        if not isinstance(self.partial_reward, (int, float)) or isinstance(self.partial_reward, bool):
            raise TypeError("partial_reward must be numeric")
        if not isfinite(self.partial_reward):
            raise ValueError("partial_reward must be finite")
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
        _require_nonempty_string(self.relative_path, "relative_path")
        if (
            "\\" in self.relative_path
            or self.relative_path.startswith("/")
            or (len(self.relative_path) >= 2 and self.relative_path[0].isalpha() and self.relative_path[1] == ":")
        ):
            raise ValueError("relative_path must be a normalized POSIX-relative path")
        path = PurePosixPath(self.relative_path)
        if ".." in path.parts or path.as_posix() != self.relative_path or self.relative_path == ".":
            raise ValueError("relative_path must be a normalized POSIX-relative path")
        _require_sha256(self.sha256, "sha256")
        _require_exact_nonnegative_int(self.byte_count, "byte_count")
        _require_nonempty_string(self.media_type, "media_type")


@dataclass(frozen=True, slots=True)
class BranchSlotSet:
    """The four execution slots used for one paired resampling comparison."""

    slots: tuple[BranchSlot, ...]

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
    donor_task_id: str
    donor_lineage: str
    slot_arms: tuple[tuple[str, Arm], ...]
    schedule_sha256: str
    verifier_index_sha256: str

    def __post_init__(self) -> None:
        for name in ("task_id", "task_lineage", "donor_task_id", "donor_lineage"):
            _require_nonempty_string(getattr(self, name), name)
        if self.task_id == self.donor_task_id:
            raise ValueError("task_id and donor_task_id must differ")
        if self.task_lineage == self.donor_lineage:
            raise ValueError("task_lineage and donor_lineage must differ")
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
        _require_sha256(self.verifier_index_sha256, "verifier_index_sha256")
