"""Contract tests for the resampling-null core records."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from math import inf, nan

import pytest

from pneuma_lab.resampling_null import (
    Arm,
    ArtifactRef,
    BranchOutcome,
    BranchSlot,
    BranchSlotSet,
    FrozenVerifierReceipt,
    ResourceCounters,
    TaskAssignment,
    TaskSchedule,
    TaskSpec,
    Treatment,
    Verdict,
)


def task() -> TaskSpec:
    return TaskSpec("task-1", "benchmark-a", "stratum-a", "lineage-a")


def slot(slot_id: str = "slot-1", seed: int = 1, execution_order: int = 0) -> BranchSlot:
    return BranchSlot(slot_id, seed, execution_order, 0)


def counters() -> ResourceCounters:
    return ResourceCounters(0, 0, 0, 0)


def outcome(**overrides: object) -> BranchOutcome:
    values: dict[str, object] = {
        "task_id": "task-1",
        "benchmark": "benchmark-a",
        "opaque_arm_id": "arm-token",
        "success": 1,
        "prefix_success": 0,
        "partial_reward": 0.0,
        "infrastructure_failure": False,
        "counters": counters(),
        "artifact_sha256": "a" * 64,
    }
    values.update(overrides)
    return BranchOutcome(**values)  # type: ignore[arg-type]


def test_arm_order_and_names_are_canonical() -> None:
    assert list(Arm) == [Arm.REAL, Arm.SHAM, Arm.NONE, Arm.RESAMPLE]
    assert [member.value for member in Arm] == ["REAL", "SHAM", "NONE", "RESAMPLE"]


def test_treatment_order_is_pre_orientation_canonical() -> None:
    assert list(Treatment) == [Treatment.REAL, Treatment.SHAM, Treatment.NO_PACKET]


def test_verdict_values_are_closed_and_apparatus_only_is_absent() -> None:
    assert [member.value for member in Verdict] == [
        "CAUSAL_CONTENT",
        "SHAM_PACKET_ONLY",
        "RESAMPLING_CONSISTENT",
        "HARMFUL_OR_MISDIRECTING",
        "UNRESOLVED_RESAMPLING",
        "PIPELINE_INVALID",
        "FEASIBILITY_NO_GO",
    ]
    assert not hasattr(Verdict, "APPARATUS_ONLY")


@pytest.mark.parametrize("factory", [task, slot, counters, outcome])
def test_records_are_frozen_and_slotted(factory: object) -> None:
    value = factory()  # type: ignore[operator]
    with pytest.raises(FrozenInstanceError):
        setattr(value, fields(value)[0].name, "changed")
    assert not hasattr(value, "__dict__")


@pytest.mark.parametrize("field", ["task_id", "benchmark", "stratum", "lineage"])
def test_task_spec_rejects_empty_identifiers(field: str) -> None:
    values = {"task_id": "task", "benchmark": "bench", "stratum": "stratum", "lineage": "lineage"}
    values[field] = ""
    with pytest.raises(ValueError):
        TaskSpec(**values)


@pytest.mark.parametrize("seed", [-1, 2**64, True, 1.0])
def test_branch_slot_rejects_invalid_seed(seed: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        BranchSlot("slot", seed, 0, 0)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [-1, True, 1.0])
def test_branch_slot_rejects_invalid_order_or_lane(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        BranchSlot("slot", 0, value, 0)  # type: ignore[arg-type]
    with pytest.raises((TypeError, ValueError)):
        BranchSlot("slot", 0, 0, value)  # type: ignore[arg-type]


@pytest.mark.parametrize("field", ["generated_tokens", "model_calls", "tool_calls", "wall_clock_ms"])
@pytest.mark.parametrize("value", [-1, True, 1.0])
def test_resource_counters_require_exact_nonnegative_ints(field: str, value: object) -> None:
    values: dict[str, object] = {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}
    values[field] = value
    with pytest.raises((TypeError, ValueError)):
        ResourceCounters(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [True, False, 1.0, 2, -1])
def test_branch_outcome_requires_binary_exact_int_success_fields(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        outcome(success=value)
    with pytest.raises((TypeError, ValueError)):
        outcome(prefix_success=value)


@pytest.mark.parametrize("value", [nan, inf, -inf])
def test_branch_outcome_rejects_nonfinite_partial_reward(value: float) -> None:
    with pytest.raises(ValueError):
        outcome(partial_reward=value)


@pytest.mark.parametrize("digest", ["A" * 64, "g" * 64, "a" * 63, "a" * 65])
def test_branch_outcome_requires_exact_lowercase_sha256(digest: str) -> None:
    with pytest.raises(ValueError):
        outcome(artifact_sha256=digest)


def test_infrastructure_failure_requires_adverse_zero_outcome() -> None:
    assert outcome(success=0, infrastructure_failure=True).infrastructure_failure
    with pytest.raises(ValueError):
        outcome(success=1, infrastructure_failure=True)


def test_branch_slot_set_requires_four_pairwise_distinct_slot_dimensions() -> None:
    slots = tuple(slot(f"slot-{index}", index, index) for index in range(4))
    assert BranchSlotSet(slots).slots == slots
    with pytest.raises(ValueError):
        BranchSlotSet((slots[0], slots[1], slots[2], slot("slot-3", 3, 2)))
    with pytest.raises(ValueError):
        BranchSlotSet((slots[0], slots[1], slots[2], slot("slot-4", 2, 3)))
    with pytest.raises(ValueError):
        BranchSlotSet((slots[0], slots[1], slots[2], slot("slot-2", 3, 3)))


def test_artifact_ref_accepts_a_normalized_posix_relative_reference() -> None:
    artifact = ArtifactRef("receipt", "receipts/task-1.json", "b" * 64, 0, "application/json")
    assert artifact.relative_path == "receipts/task-1.json"


@pytest.mark.parametrize("path", ["", "/receipt.json", "C:/receipt.json", "dir/../receipt.json", "./receipt.json", "dir//receipt.json", "dir\\receipt.json"])
def test_artifact_ref_rejects_non_normalized_or_unsafe_paths(path: str) -> None:
    with pytest.raises((TypeError, ValueError)):
        ArtifactRef("receipt", path, "b" * 64, 0, "application/json")


@pytest.mark.parametrize("value", [-1, True, 1.0])
def test_artifact_ref_requires_an_exact_nonnegative_byte_count(value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        ArtifactRef("receipt", "receipt.json", "b" * 64, value, "application/json")  # type: ignore[arg-type]


@pytest.mark.parametrize("role,media_type", [("", "application/json"), ("receipt", "")])
def test_artifact_ref_requires_role_and_media_type(role: str, media_type: str) -> None:
    with pytest.raises(ValueError):
        ArtifactRef(role, "receipt.json", "b" * 64, 0, media_type)


def test_task_schedule_binds_a_task_prefix_seed_and_exactly_four_unique_slots() -> None:
    slots = tuple(slot(f"slot-{index}", index, index) for index in range(4))
    schedule = TaskSchedule(task(), 7, BranchSlotSet(slots), "provider-a")
    assert schedule.prefix_seed == 7
    with pytest.raises((TypeError, ValueError)):
        TaskSchedule(task(), True, BranchSlotSet(slots), "provider-a")  # type: ignore[arg-type]
    with pytest.raises((TypeError, ValueError)):
        TaskSchedule(task(), 7, BranchSlotSet(slots), "")


def test_frozen_verifier_receipt_is_digest_only_and_rejects_invalid_counts() -> None:
    receipt = FrozenVerifierReceipt("task-1", "c" * 64, "d" * 64, 0)
    assert tuple(field.name for field in fields(FrozenVerifierReceipt)) == (
        "task_id",
        "prefix_receipt_sha256",
        "verifier_artifact_sha256",
        "finding_count",
    )
    assert receipt.finding_count == 0
    with pytest.raises((TypeError, ValueError)):
        FrozenVerifierReceipt("task-1", "c" * 64, "d" * 64, True)


def assignment(**overrides: object) -> TaskAssignment:
    values: dict[str, object] = {
        "task_id": "task-1",
        "task_lineage": "lineage-1",
        "donor_task_id": "task-2",
        "donor_lineage": "lineage-2",
        "slot_arms": tuple((f"slot-{index}", arm) for index, arm in enumerate(Arm)),
        "schedule_sha256": "e" * 64,
        "verifier_index_sha256": "f" * 64,
    }
    values.update(overrides)
    return TaskAssignment(**values)  # type: ignore[arg-type]


def test_task_assignment_maps_every_arm_once_across_four_unique_slots() -> None:
    value = assignment()
    assert {arm for _, arm in value.slot_arms} == set(Arm)
    with pytest.raises(ValueError):
        assignment(slot_arms=(("slot-0", Arm.REAL), ("slot-1", Arm.SHAM), ("slot-2", Arm.NONE), ("slot-2", Arm.RESAMPLE)))
    with pytest.raises(ValueError):
        assignment(slot_arms=(("slot-0", Arm.REAL), ("slot-1", Arm.SHAM), ("slot-2", Arm.NONE), ("slot-3", Arm.NONE)))


@pytest.mark.parametrize(
    "overrides",
    [
        {"donor_task_id": "task-1"},
        {"donor_lineage": "lineage-1"},
        {"schedule_sha256": "E" * 64},
        {"verifier_index_sha256": "f" * 63},
    ],
)
def test_task_assignment_rejects_shared_ancestry_or_invalid_digests(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        assignment(**overrides)
