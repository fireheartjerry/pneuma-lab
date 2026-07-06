"""Pneuma Lab — a standalone research/evaluation harness for machine psyche.

Pneuma Lab studies software-engineering cognition, continuous affect, instinct,
scar-tissue memory, self-modeling, authority pressure, and consciousness-relevant
evaluation. It is the external lab for the Human-Nature / Psyche architecture
prototyped inside 9to5 (see docs/source-map.md).

This first pass is scaffolding + I/O contracts only. No runtime, no ML training,
no wiring back into 9to5. See docs/vision.md and migration/MIGRATION_REPORT.md.

The package is deliberately thin: the SCHEMAS (see the repo-root ``schemas/``
directory) are the real contract. Python sub-packages are empty seams to be
filled in later phases:

    - schemas   : schema loading + validation helpers (Phase 1)
    - adapters  : translate 9to5 / manager-data records into Pneuma frames (Phase 1)
    - replay    : deterministic replay of recorded runs through the contracts (Phase 1)
    - evals     : intervention tests + evidence scoring (Phase 3+)
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
)

__all__ = [
    "__version__",
    "FRAME_SCHEMA_VERSION",
    "INPUT_FRAMES",
    "OUTPUT_FRAMES",
]
