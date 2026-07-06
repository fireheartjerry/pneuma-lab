"""Mood — the slow, persistent affective homeostat (long-horizon, cross-run).

Ported from ``migration/copied-from-9to5/reference-interfaces/mood.py``. The 9to5
version read ``HN_MOOD_DECAY`` from ``config``; Pneuma Lab is standalone, so the
documented default (0.15) is inlined as :data:`DEFAULT_DECAY_RATE`. Pure.
"""

from __future__ import annotations

from typing import Any

# 9to5 default: config.HN_MOOD_DECAY (inlined for standalone operation).
DEFAULT_DECAY_RATE = 0.15


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def new_mood() -> dict[str, float]:
    return {"valence": 0.0, "arousal": 0.0}


def blend_outcome(
    mood: dict[str, Any],
    run_valence: float,
    run_arousal: float,
    weight: float = 0.3,
) -> dict[str, float]:
    """Exponential moving average of ``mood`` toward this run's outcome signal."""
    weight = max(0.0, min(1.0, float(weight)))
    retention = 1.0 - weight
    new_valence = retention * float(mood.get("valence", 0.0)) + weight * float(
        run_valence
    )
    new_arousal = retention * float(mood.get("arousal", 0.0)) + weight * float(
        run_arousal
    )
    return {"valence": _clamp(new_valence), "arousal": _clamp(new_arousal)}


def decay(
    mood: dict[str, Any], setpoint: dict[str, Any], rate: float
) -> dict[str, float]:
    """Move ``mood`` toward ``setpoint`` by ``rate`` (0=no change, 1=snap). Pure."""
    rate = max(0.0, min(1.0, float(rate)))
    new_valence = float(mood.get("valence", 0.0)) + rate * (
        float(setpoint.get("valence", 0.0)) - float(mood.get("valence", 0.0))
    )
    new_arousal = float(mood.get("arousal", 0.0)) + rate * (
        float(setpoint.get("arousal", 0.0)) - float(mood.get("arousal", 0.0))
    )
    return {"valence": _clamp(new_valence), "arousal": _clamp(new_arousal)}


def congruent_bias(
    valence: float, mood: dict[str, Any], strength: float = 0.5
) -> float:
    """Apply mood-congruent bias to an ambiguous input valence."""
    mood_valence = float(mood.get("valence", 0.0))
    if mood_valence >= 0.0:
        return _clamp(valence)
    old_v = float(valence)
    ambiguity = 1.0 - abs(old_v)
    shift = mood_valence * ambiguity * float(strength)
    return _clamp(old_v + shift)


__all__ = ["DEFAULT_DECAY_RATE", "new_mood", "blend_outcome", "decay", "congruent_bias"]
