"""The ``PsycheUnderTest`` seam — the one interface every mind-under-test implements.

The replay harness and the evidence scorer depend ONLY on this interface plus the
JSON schemas, never on a concrete psyche's internals. That is what lets Pneuma Lab
swap ``ReferencePsyche`` for a future ported-9to5 mind or a learned model without
touching the harness.

A psyche consumes one *tick* of input frames and produces one bundle of output
frames. The psyche is stateful across ticks (that persistence is the recurrence
and identity-continuity substrate); ``reset()`` clears per-run carried state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PsycheInputs:
    """One tick of already-validated input frames.

    ``world`` is required (it opens a tick and carries the timestamp). The other
    frames are optional: a tick may have no fresh agent trace, memory readback, or
    governance update.
    """

    world: dict
    tick_index: int
    agent_trace: dict | None = None
    memory: dict | None = None
    governance: dict | None = None


@dataclass
class PsycheOutputs:
    """One tick of output frames emitted by the psyche.

    The always-on frames are non-null; ``instinct_signals`` and
    ``authority_requests`` are lists because a tick may emit zero or several.
    """

    psyche_state: dict
    workspace_broadcast: dict
    control_pressure: dict
    causal_trace: dict
    grounded_self_report: dict
    instinct_signals: list[dict] = field(default_factory=list)
    authority_requests: list[dict] = field(default_factory=list)

    def all_frames(self) -> list[dict]:
        """Every emitted frame, in a stable order (for validation + logging)."""
        frames: list[dict] = [
            self.psyche_state,
            self.workspace_broadcast,
            *self.instinct_signals,
            self.control_pressure,
            *self.authority_requests,
            self.causal_trace,
            self.grounded_self_report,
        ]
        return frames


class PsycheUnderTest(ABC):
    """Abstract base for any machine psyche driven by the replay harness."""

    @abstractmethod
    def tick(self, inputs: PsycheInputs) -> PsycheOutputs:
        """Advance the psyche one tick and emit its output frames."""

    @abstractmethod
    def reset(self) -> None:
        """Clear per-run carried state so a fresh run starts from the baseline."""


__all__ = ["PsycheInputs", "PsycheOutputs", "PsycheUnderTest"]
