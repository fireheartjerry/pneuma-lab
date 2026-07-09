"""Replay — deterministic replay of recorded runs through the contracts (Phase 1).

The replay harness takes a recorded sequence of input frames (WorldFrame,
AgentTraceFrame, MemoryFrame, GovernanceFrame, and optional InterventionFrames),
validates them, groups them into ticks, and drives them through a
``PsycheUnderTest`` implementation — capturing the output frames and CausalTraces
and producing a Level 0-4 ConsciousnessEvidenceFrame for offline scoring.

``ReplayHarness`` alone cannot self-certify past Level 3. The Phase-2 paired runner
executes scheduled interventions and supplies a reconciled control/treated/null
test inventory before the scorer can reach internal Level 4.
"""

from __future__ import annotations

from .frames import Tick, dump_jsonl, group_into_ticks, load_jsonl
from .harness import ReplayHarness, ReplayResult

__all__ = [
    "ReplayHarness",
    "ReplayResult",
    "Tick",
    "load_jsonl",
    "dump_jsonl",
    "group_into_ticks",
]
