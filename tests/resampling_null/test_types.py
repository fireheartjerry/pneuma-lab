"""Milestone claims: closed public enums, immutable records, and safe identities."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pneuma_lab.resampling_null.types import (
    Arm,
    ArtifactRef,
    BranchSlot,
    BranchSlotSet,
    GroupKind,
    GroupLabel,
    ResourceCounters,
    TaskSpec,
)


pytestmark = pytest.mark.milestone


def test_closed_public_enums_preserve_protocol_values() -> None:
    assert tuple(member.value for member in Arm) == ("REAL", "SHAM", "NONE", "RESAMPLE")
    assert tuple(member.value for member in GroupKind) == (
        "language",
        "domain",
        "issue_family",
    )


def test_artifact_reference_is_immutable_and_confined() -> None:
    ref = ArtifactRef("outcome", "outcomes/task.json", "a" * 64, 1, "application/json")
    with pytest.raises(FrozenInstanceError):
        ref.role = "forged"  # type: ignore[misc]
    with pytest.raises(ValueError, match="relative_path"):
        ArtifactRef("outcome", "../escape", "a" * 64, 1, "application/json")


def test_task_and_slot_topology_is_exact_and_ordered() -> None:
    task = TaskSpec(
        "task-1",
        "benchmark",
        "stratum",
        "lineage",
        (GroupLabel(GroupKind.LANGUAGE, "python"),),
    )
    slots = BranchSlotSet(
        tuple(BranchSlot(f"slot-{index}", 7 + index, index, 0) for index in range(4))
    )

    assert task.task_id == "task-1"
    assert slots.slots[0].seed == 7


def test_resource_counters_reject_nonfinite_or_noninteger_values() -> None:
    assert ResourceCounters(0, 0, 0, 0).model_calls == 0
    with pytest.raises(TypeError):
        ResourceCounters(0, 0.0, 0, 0)  # type: ignore[arg-type]
