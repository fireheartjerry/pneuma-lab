"""Resolve InterventionFrame duration windows into per-tick active sets.

A tick is opened by a WorldFrame (mirrors ``replay.frames.group_into_ticks``). An
intervention is attached to the tick it arrives in; its ``duration`` decides how
many later ticks it also covers. All resolution is index-based and deterministic.
"""

from __future__ import annotations

from ..replay.frames import group_into_ticks


class InterventionSchedule:
    """Per-tick active interventions, resolved from duration windows."""

    def __init__(self, windows: dict[int, list[dict]]) -> None:
        # tick_index -> ordered list of active intervention dicts
        self._windows = windows

    @classmethod
    def from_frames(cls, frames: list[dict]) -> "InterventionSchedule":
        ticks = group_into_ticks(frames)
        n = len(ticks)
        windows: dict[int, list[dict]] = {i: [] for i in range(n)}
        for onset, tick in enumerate(ticks):
            phase = tick.world.get("phase") or tick.world.get("subtask_id")
            for iv in tick.interventions:
                for j in cls._covered(onset, n, iv, ticks, phase):
                    windows[j].append(iv)
        return cls(windows)

    @staticmethod
    def _covered(onset, n, iv, ticks, onset_phase):
        dur = iv.get("duration") or {}
        kind = dur.get("kind", "ticks")
        amount = dur.get("amount")
        if kind in ("run", "permanent", "seconds"):
            # seconds has no wall clock in replay; treated as run-to-end (documented).
            return range(onset, n)
        if kind == "subtask":
            end = onset
            while end + 1 < n and (
                (
                    ticks[end + 1].world.get("phase")
                    or ticks[end + 1].world.get("subtask_id")
                )
                == onset_phase
            ):
                end += 1
            return range(onset, end + 1)
        # "ticks"
        span = int(amount) if amount else 1
        return range(onset, min(n, onset + max(1, span)))

    def active(self, tick_index: int) -> list[dict]:
        return list(self._windows.get(tick_index, []))

    def experiment_ids(self) -> set:
        return {iv.get("experiment_id") for ivs in self._windows.values() for iv in ivs}

    def is_empty(self) -> bool:
        return not any(self._windows.values())

    def neutralized(self) -> "InterventionSchedule":
        """A copy with every op replaced by ``restore`` (the null / no-op run)."""
        neu: dict[int, list[dict]] = {}
        for i, ivs in self._windows.items():
            neu[i] = [{**iv, "operation": "restore"} for iv in ivs]
        return InterventionSchedule(neu)


__all__ = ["InterventionSchedule"]
