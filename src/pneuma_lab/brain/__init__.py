"""PneumaBrain-v0.1 local multi-task trainer (offline, advisory-only).

Deterministic, CPU-only. Consumes PneumaTrainingExample corpora and trains
task-conditioned logistic heads over observable-only features. No runtime
integration, no verifier bypass, no consciousness claim.
"""

from __future__ import annotations

BRAIN_VERSION = "pneuma-brain/0.1.0"

__all__ = ["BRAIN_VERSION"]
