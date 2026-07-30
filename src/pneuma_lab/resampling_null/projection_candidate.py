"""Pure construction of the unlabelled four-slot analysis view."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from math import isfinite
from typing import Any
import sys


_LABELS = ("A", "B", "C", "D")
_COUNTERS = ("generated_tokens", "model_calls", "tool_calls", "wall_clock_ms")


@dataclass(frozen=True, slots=True)
class ProjectionCandidate:
    """Ephemeral, canonical data supplied to the trusted sealing process."""

    rows: tuple[dict[str, object], ...]
    canonical_bytes: bytes
    sha256: str


def _counter_copy(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(_COUNTERS):
        raise ValueError("counters must have the closed nonnegative shape")
    result: dict[str, int] = {}
    for field in _COUNTERS:
        item = value[field]
        if type(item) is not int or item < 0:
            raise ValueError("counters must have the closed nonnegative shape")
        result[field] = item
    return result


def _outcome_copy(value: object, prefix_success: int) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError("outcome must be a mapping")
    allowed = {
        "success",
        "prefix_success",
        "partial_reward",
        "infrastructure_failure",
        "counters",
    }
    if set(value) != allowed:
        raise ValueError("outcome has forbidden or missing fields")
    success = value["success"]
    observed_prefix = value["prefix_success"]
    reward = value["partial_reward"]
    failure = value["infrastructure_failure"]
    if type(success) is not int or success not in (0, 1):
        raise ValueError("success must be binary")
    if type(observed_prefix) is not int or observed_prefix not in (0, 1):
        raise ValueError("prefix success must be binary")
    if observed_prefix != prefix_success:
        raise ValueError("outcome prefix does not match its frozen prefix")
    if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not isfinite(reward):
        raise ValueError("partial reward must be finite")
    if type(failure) is not bool:
        raise ValueError("infrastructure failure must be boolean")
    return {
        "success": success,
        "prefix_success": observed_prefix,
        "partial_reward": float(reward),
        "infrastructure_failure": failure,
        "counters": _counter_copy(value["counters"]),
    }


def build_candidate(
    frozen_schedule: Sequence[Mapping[str, object]],
    closed_outcomes: Mapping[str, Sequence[Mapping[str, object]]],
) -> ProjectionCandidate:
    """Return a deterministic A-through-D view with no identity-bearing data."""

    rows: list[dict[str, object]] = []
    task_ids: set[str] = set()
    for schedule_row in frozen_schedule:
        task_id = schedule_row.get("task_id")
        prefix_success = schedule_row.get("prefix_success")
        slot_ids = schedule_row.get("slot_ids")
        if type(task_id) is not str or not task_id or task_id in task_ids:
            raise ValueError("schedule must have unique task IDs")
        if type(prefix_success) is not int or prefix_success not in (0, 1):
            raise ValueError("schedule prefix success must be binary")
        if not isinstance(slot_ids, Sequence) or isinstance(slot_ids, (str, bytes)):
            raise ValueError("schedule must provide four slots")
        if len(slot_ids) != 4 or any(type(slot) is not str or not slot for slot in slot_ids):
            raise ValueError("schedule must provide four slots")
        outcomes = closed_outcomes.get(task_id)
        if outcomes is None or len(outcomes) != 4:
            raise ValueError("closed outcome coverage must be complete")
        task_ids.add(task_id)
        rows.append({
            "task_id": task_id,
            "prefix_success": prefix_success,
            "slots": [
                {
                    "label": label,
                    "slot_id": slot_ids[index],
                    "outcome": _outcome_copy(outcomes[index], prefix_success),
                }
                for index, label in enumerate(_LABELS)
            ],
        })
    if set(closed_outcomes) != task_ids:
        raise ValueError("closed outcome coverage must exactly match the schedule")
    canonical = json.dumps(
        rows, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return ProjectionCandidate(
        rows=tuple(rows),
        canonical_bytes=canonical,
        sha256=hashlib.sha256(canonical).hexdigest(),
    )


def _main() -> None:
    """Narrow stdin/stdout protocol for an isolated capability-minimal worker."""
    request = json.load(sys.stdin)
    if not isinstance(request, Mapping) or set(request) != {"frozen_schedule", "closed_outcomes"}:
        raise ValueError("candidate request has closed shape")
    candidate = build_candidate(request["frozen_schedule"], request["closed_outcomes"])
    sys.stdout.buffer.write(candidate.canonical_bytes)


if __name__ == "__main__":
    _main()
