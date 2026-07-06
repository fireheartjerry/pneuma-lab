"""Replay — deterministic replay of recorded runs through the contracts (Phase 1).

The replay harness takes a recorded sequence of input frames (WorldFrame,
AgentTraceFrame, MemoryFrame, GovernanceFrame, and optional InterventionFrames),
validates them, groups them into ticks, and drives them through a
``PsycheUnderTest`` implementation — capturing the output frames and CausalTraces
and producing a Level 0-3 ConsciousnessEvidenceFrame for offline scoring.

Phase-1 boundary: InterventionFrames are counted but NOT executed, so the
evidence scorer keeps ``causal_intervention_robustness`` unevidenced and cannot
score past Level 3. Intervention execution is Phase 3.
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
