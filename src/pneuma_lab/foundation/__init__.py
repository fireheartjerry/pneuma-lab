"""Local-first Qwen3.5 foundation research tooling.

This package is an offline engineering surface. Importing it never downloads a
model, starts training, grants runtime authority, or makes a consciousness
claim. Expensive operations require explicit CLI flags and signed manifests.
"""

from pneuma_lab.foundation.specs import (
    CORE_LIMITS,
    MODEL_SPECS,
    RUNTIME_LIMITS,
)

__all__ = ["CORE_LIMITS", "MODEL_SPECS", "RUNTIME_LIMITS"]
