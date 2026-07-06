"""Affect manifold — continuous 9-axis affect substrate (state-space model).

Ported verbatim (pure functions, stdlib only) from
``migration/copied-from-9to5/reference-interfaces/affect_manifold.py``.

Each step blends the current state (inertia), a personality baseline, and four
drivers (appraisal, mood, drive pressure, scars) via fixed weights, plus a small
restoring attractor that keeps state off the rails. All functions are PURE:
inputs are never mutated and a new dict is returned. The prior-state inertia term
is what makes this *recurrent* — the substrate carries state tick to tick.
"""

from __future__ import annotations

AXES = (
    "valence",
    "arousal",
    "dominance",
    "certainty",
    "novelty",
    "agency",
    "tension",
    "social_exposure",
    "cognitive_load",
)

DEFAULT_INERTIA = 0.5  # per-axis; some axes can differ

# Fixed driver weights (appraisal dominates; the slow signals nudge).
_W_APPRAISAL = 1.0
_W_MOOD = 0.3
_W_DRIVE = 0.3
_W_SCARS = 0.3

# Restoring pull toward baseline for extreme values (bounded; keeps off the rails).
_ATTRACTOR_GAIN = 0.05


def new_manifold() -> dict[str, float]:
    """Return a fresh manifold with every axis at 0.0 (neutral)."""
    return {axis: 0.0 for axis in AXES}


def _get(d: dict | None, axis: str) -> float:
    """Read an axis value from a possibly-missing/empty dict, default 0.0, no NaN."""
    if not d:
        return 0.0
    val = d.get(axis, 0.0)
    try:
        val = float(val)
    except (TypeError, ValueError):
        return 0.0
    if val != val:  # NaN guard
        return 0.0
    return val


def _clip(x: float) -> float:
    return -1.0 if x < -1.0 else (1.0 if x > 1.0 else x)


def update(
    a: dict,
    appraisal: dict,
    mood: dict,
    drive_pressure: dict,
    scars: dict,
    personality_baseline: dict,
    inertia: dict | None = None,
) -> dict:
    """Advance the affect manifold one step (pure; returns a new dict).

    For each axis::

        delta = w_x*appraisal + w_m*mood + w_d*drive + w_s*scars
        A_next = clip( k*a + (1-k)*(baseline + delta) + attractor(a) , -1, 1)

    where ``k = inertia[axis]`` (default :data:`DEFAULT_INERTIA`), baseline comes
    from ``personality_baseline`` (default 0.0), and ``attractor(x) =
    -_ATTRACTOR_GAIN * x`` is a small restoring pull toward baseline.
    """
    out: dict[str, float] = {}
    for axis in AXES:
        k = _get(inertia, axis) if inertia else DEFAULT_INERTIA
        # _get returns 0.0 for a missing axis; only override the default when present.
        if inertia is not None and axis not in inertia:
            k = DEFAULT_INERTIA
        cur = _get(a, axis)
        baseline = _get(personality_baseline, axis)
        delta = (
            _W_APPRAISAL * _get(appraisal, axis)
            + _W_MOOD * _get(mood, axis)
            + _W_DRIVE * _get(drive_pressure, axis)
            + _W_SCARS * _get(scars, axis)
        )
        attractor = -_ATTRACTOR_GAIN * cur
        nxt = k * cur + (1.0 - k) * (baseline + delta) + attractor
        out[axis] = _clip(nxt)
    return out


def decay(a: dict, rate: float, baseline: dict | None = None) -> dict:
    """Pull every axis a fraction ``rate`` toward baseline (default 0.0). Pure."""
    try:
        r = float(rate)
    except (TypeError, ValueError):
        r = 0.0
    if r != r:  # NaN guard
        r = 0.0
    r = 0.0 if r < 0.0 else (1.0 if r > 1.0 else r)
    out: dict[str, float] = {}
    for axis in AXES:
        cur = _get(a, axis)
        base = _get(baseline, axis)
        out[axis] = _clip(cur + (base - cur) * r)
    return out


__all__ = ["AXES", "new_manifold", "update", "decay"]
