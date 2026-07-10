"""Dataset-specific governance modules.

Each module in this package defines the input allowlist, blocked raw/target
field tokens, label-provenance policy, and training-authorization defaults for
one dataset. These modules are infrastructure only: no model fitting,
calibration, runtime integration, or raw dataset reads.
"""

from __future__ import annotations

__all__: list[str] = []
