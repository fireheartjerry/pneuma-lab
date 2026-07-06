"""Prototype projection — continuous affect manifold → discrete emotion labels.

Ported from ``migration/copied-from-9to5/reference-interfaces/prototypes.py``.
RBF activation yields a soft ``mixture`` and a hysteresis-stabilised ``dominant``
label so the label does not flicker on small manifold jitter. Pure, stdlib only.
"""

from __future__ import annotations

import math

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

# Emotion prototype anchors. Each is a subset of AXES; omitted axes = 0.0.
PROTOTYPES: dict[str, dict] = {
    "frustration": {"valence": -0.6, "arousal": 0.6, "tension": 0.6},
    "anxiety": {"valence": -0.5, "arousal": 0.4, "certainty": -0.5, "tension": 0.5},
    "curiosity": {"valence": 0.4, "arousal": 0.3, "novelty": 0.7},
    "boredom": {"arousal": -0.5, "novelty": -0.5},
    "satisfaction": {"valence": 0.7, "arousal": 0.2, "dominance": 0.4},
    "neutral": {},
}

_SIGMA = 0.6
_TWO_SIGMA_SQ = 2.0 * _SIGMA * _SIGMA


def _dist2(a: dict, anchor: dict) -> float:
    """Squared Euclidean distance over all AXES (missing components = 0.0)."""
    total = 0.0
    for ax in AXES:
        d = float(a.get(ax, 0.0)) - float(anchor.get(ax, 0.0))
        total += d * d
    return total


def _activations(a: dict) -> dict[str, float]:
    """Raw (un-normalized) RBF activation in (0, 1] for each prototype."""
    return {
        label: math.exp(-_dist2(a, anchor) / _TWO_SIGMA_SQ)
        for label, anchor in PROTOTYPES.items()
    }


def mixture(a: dict) -> dict[str, float]:
    """RBF activation per prototype, normalized so the values sum to 1.0."""
    raw = _activations(a)
    total = sum(raw.values())
    if total <= 0.0:  # unreachable (exp > 0), but keep normalization safe
        n = len(raw)
        return {label: 1.0 / n for label in raw}
    return {label: value / total for label, value in raw.items()}


def dominant(
    a: dict,
    prev: str | None = None,
    theta_on: float = 0.5,
    theta_off: float = 0.35,
) -> str:
    """Dominant emotion label for manifold ``a`` with flicker-resistant hysteresis."""
    raw = _activations(a)
    non_neutral = {k: v for k, v in raw.items() if k != "neutral"}
    top_label = max(non_neutral, key=non_neutral.get)
    top_val = non_neutral[top_label]

    if prev is not None and prev != "neutral":
        prev_val = raw.get(prev, 0.0)
        if prev_val >= theta_off:
            if top_label != prev and top_val >= theta_on and top_val > prev_val:
                return top_label
            return prev

    if top_val >= theta_on:
        return top_label
    return "neutral"


__all__ = ["PROTOTYPES", "mixture", "dominant"]
