"""Pneuma Lab — a standalone research/evaluation harness for machine psyche.

Pneuma Lab studies software-engineering cognition, continuous affect, instinct,
scar-tissue memory, self-modeling, authority pressure, and consciousness-relevant
evaluation. It is the external lab for the Human-Nature / Psyche architecture
prototyped inside 9to5 (see docs/source-map.md).

The package now includes schema validation, deterministic replay, paired
interventions, offline dataset adapters, a trace-to-replay bridge, guarded
training-example conversion, and offline advisory estimators. Its strongest
evidence result is internal-harness methodology validation; it does not evaluate
a real subject or claim phenomenal consciousness.

Pneuma remains standalone: there is no live wiring back into 9to5, no operational
nervous-system loop, and no JSpace/J-lens implementation. See
``docs/project-status.json`` for the canonical current state and blockers.
"""

from __future__ import annotations

__version__ = "0.1.0"

# Frame contract version. Bump when a schema's shape changes incompatibly.
FRAME_SCHEMA_VERSION = "0.1.0"

INPUT_FRAMES = (
    "world",
    "agent_trace",
    "memory",
    "governance",
    "intervention",
)

OUTPUT_FRAMES = (
    "psyche_state",
    "workspace_broadcast",
    "instinct_signal",
    "control_pressure",
    "authority_request",
    "causal_trace",
    "consciousness_evidence",
    "grounded_self_report",
    "risk_estimate",
)

__all__ = [
    "__version__",
    "FRAME_SCHEMA_VERSION",
    "INPUT_FRAMES",
    "OUTPUT_FRAMES",
]
