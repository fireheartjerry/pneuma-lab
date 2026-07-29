"""Closed decoding for one scheduled task."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from .errors import RecordValidationError
from .types import (
    BranchSlot,
    BranchSlotSet,
    GroupKind,
    GroupLabel,
    TaskSchedule,
    TaskSpec,
)


def _decode_group_labels(
    value: object,
    *,
    field: str,
) -> tuple[GroupLabel, ...]:
    if not isinstance(value, list) or not value:
        raise RecordValidationError(
            f"{field} must be a non-empty group array"
        )
    labels: list[GroupLabel] = []
    for index, group in enumerate(value):
        if not isinstance(group, Mapping) or set(group) != {"kind", "value"}:
            raise RecordValidationError(
                f"{field}[{index}] has wrong shape"
            )
        try:
            labels.append(
                GroupLabel(
                    GroupKind(cast(str, group["kind"])),
                    cast(str, group["value"]),
                )
            )
        except (TypeError, ValueError) as exc:
            raise RecordValidationError(
                f"{field}[{index}] is invalid: {exc}"
            ) from exc
    return tuple(labels)


def decode_task_schedule(value: object, *, field: str) -> TaskSchedule:
    """Decode one exact schedule task without importing a consumer module."""

    if not isinstance(value, Mapping) or set(value) != {
        "task",
        "prefix_seed",
        "slots",
        "provider_lane",
    }:
        raise RecordValidationError(f"{field} has wrong shape")
    task = value["task"]
    if not isinstance(task, Mapping) or set(task) != {
        "task_id",
        "benchmark",
        "stratum",
        "lineage",
        "sensitivity_groups",
    }:
        raise RecordValidationError(f"{field}.task has wrong shape")
    slots_value = value["slots"]
    if not isinstance(slots_value, list) or len(slots_value) != 4:
        raise RecordValidationError(
            f"{field}.slots must contain four rows"
        )
    slots: list[BranchSlot] = []
    for index, slot in enumerate(slots_value):
        if not isinstance(slot, Mapping) or set(slot) != {
            "slot_id",
            "seed",
            "execution_order",
            "hardware_lane",
        }:
            raise RecordValidationError(
                f"{field}.slots[{index}] has wrong shape"
            )
        try:
            slots.append(
                BranchSlot(
                    slot_id=cast(str, slot["slot_id"]),
                    seed=cast(int, slot["seed"]),
                    execution_order=cast(int, slot["execution_order"]),
                    hardware_lane=cast(int, slot["hardware_lane"]),
                )
            )
        except (TypeError, ValueError) as exc:
            raise RecordValidationError(
                f"{field}.slots[{index}] is invalid: {exc}"
            ) from exc
    try:
        exact_slots = cast(
            tuple[BranchSlot, BranchSlot, BranchSlot, BranchSlot],
            tuple(slots),
        )
        return TaskSchedule(
            task=TaskSpec(
                task_id=cast(str, task["task_id"]),
                benchmark=cast(str, task["benchmark"]),
                stratum=cast(str, task["stratum"]),
                lineage=cast(str, task["lineage"]),
                sensitivity_groups=_decode_group_labels(
                    task["sensitivity_groups"],
                    field=f"{field}.task.sensitivity_groups",
                ),
            ),
            prefix_seed=cast(int, value["prefix_seed"]),
            slots=BranchSlotSet(exact_slots),
            provider_lane=cast(str, value["provider_lane"]),
        )
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is invalid: {exc}") from exc
