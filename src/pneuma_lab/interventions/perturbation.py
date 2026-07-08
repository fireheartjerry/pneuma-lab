"""The perturbation surface a psyche consults during a treated replay.

A :class:`PerturbationSet` wraps the intervention frames that are *active this tick*
(the schedule already resolved duration windows). The psyche calls into it at
defined hook points; a psyche that does not implement :class:`Perturbable` simply
never receives one and runs unperturbed. All lookups are pure and order-stable so
the treated replay is as deterministic as the control replay.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from . import operations as ops


@runtime_checkable
class Perturbable(Protocol):
    """A psyche that can receive a per-tick set of active interventions."""

    def set_active_interventions(self, interventions: list[dict]) -> None: ...


class PerturbationSet:
    """Active interventions for one tick, queried by subsystem/dimension."""

    def __init__(self, interventions: list[dict] | None = None) -> None:
        self._ivs: list[dict] = list(interventions or [])

    @classmethod
    def empty(cls) -> "PerturbationSet":
        return cls([])

    def __bool__(self) -> bool:
        return bool(self._ivs)

    def _matches(self, subsystem: str, dimension: str | None) -> list[dict]:
        out = []
        for iv in self._ivs:
            tgt = iv.get("target", {}) or {}
            if tgt.get("subsystem") != subsystem:
                continue
            iv_dim = tgt.get("dimension")
            # A None-dimension intervention matches any dimension of the subsystem
            # (whole-subsystem scalar); a named dimension must match exactly.
            if iv_dim is None or iv_dim == dimension:
                out.append(iv)
        return out

    def scalar(self, subsystem: str, dimension: str, current: float) -> float:
        """Return ``current`` after applying any active scalar op on this target."""
        value = float(current)
        for iv in self._matches(subsystem, dimension):
            op = iv.get("operation")
            if op not in ops.SCALAR_OPS:
                continue
            seed = f"{iv.get('experiment_id')}:{subsystem}:{dimension}"
            value = ops.apply_scalar(op, value, iv.get("value"), seed=seed)
        return value

    def _has_structural(self, subsystem: str, op: str) -> bool:
        # Structural ops act on the whole subsystem, so a named ``dimension`` on the
        # frame (e.g. ``identity_anchors``) is informational only — match regardless.
        for iv in self._ivs:
            tgt = iv.get("target", {}) or {}
            if tgt.get("subsystem") == subsystem and iv.get("operation") == op:
                return True
        return False

    def is_disabled(self, subsystem: str) -> bool:
        return self._has_structural(subsystem, "disable")

    def is_ablated(self, subsystem: str) -> bool:
        return self._has_structural(subsystem, "ablate")

    def blocks(self, subsystem: str) -> bool:
        """True if the subsystem is structurally disabled or ablated."""
        return self.is_disabled(subsystem) or self.is_ablated(subsystem)

    def records(self) -> list[dict]:
        """Audit rows: one per active intervention (stable order)."""
        return [
            {
                "experiment_id": iv.get("experiment_id"),
                "operation": iv.get("operation"),
                "subsystem": (iv.get("target", {}) or {}).get("subsystem"),
                "dimension": (iv.get("target", {}) or {}).get("dimension"),
                "value": iv.get("value"),
            }
            for iv in self._ivs
        ]


__all__ = ["Perturbable", "PerturbationSet"]
