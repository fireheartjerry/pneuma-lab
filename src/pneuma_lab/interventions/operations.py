"""Pure operation semantics for Level-4 interventions.

Every operation is a closed-form function of its inputs so a perturbed replay
stays byte-reproducible. ``noise`` derives its jitter from a hash of a caller-
supplied seed string (never wall clock / RNG state), so the same intervention on
the same tick always produces the same perturbation.

    clamp    -> force the target to ``value``.
    boost    -> additive change by ``value`` (clipped to the axis range).
    noise    -> current + value * deterministic_noise(seed).
    disable  -> scalar form drives the target to 0.0 (structural form: whole store).
    ablate   -> scalar form drives the target to 0.0 (structural form: whole store).
    restore  -> no-op: return the natural value unchanged (the null operation).
"""

from __future__ import annotations

import hashlib

SCALAR_OPS = frozenset({"clamp", "boost", "noise"})
STRUCTURAL_OPS = frozenset({"disable", "ablate"})
OPERATIONS = SCALAR_OPS | STRUCTURAL_OPS | {"restore"}


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return lo if x < lo else (hi if x > hi else float(x))


def deterministic_noise(seed: str) -> float:
    """Map a seed string to a stable pseudo-random float in [-1, 1]."""
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    # 8 bytes -> unsigned int -> [0, 1) -> [-1, 1)
    n = int.from_bytes(digest[:8], "big") / float(1 << 64)
    return _clip(2.0 * n - 1.0)


def apply_scalar(
    operation: str,
    current: float,
    value,
    *,
    seed: str | None = None,
    clip: bool = True,
) -> float:
    """Apply ``operation`` to a scalar ``current`` given the intervention ``value``."""
    cur = float(current)
    if operation == "clamp":
        out = float(value)
    elif operation == "boost":
        out = cur + float(value)
    elif operation == "noise":
        mag = 1.0 if value is None else float(value)
        out = cur + mag * deterministic_noise(seed if seed is not None else "noise")
    elif operation in STRUCTURAL_OPS:
        out = 0.0
    elif operation == "restore":
        out = cur
    else:
        raise ValueError(f"unknown operation: {operation!r}")
    return _clip(out) if clip else out


__all__ = [
    "OPERATIONS",
    "SCALAR_OPS",
    "STRUCTURAL_OPS",
    "apply_scalar",
    "deterministic_noise",
]
