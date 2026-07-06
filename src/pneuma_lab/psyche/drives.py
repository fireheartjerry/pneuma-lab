"""Drives — the 8-drive homeostatic core of the human-nature layer.

Ported verbatim (stdlib only) from
``migration/copied-from-9to5/reference-interfaces/drives.py``. Each core drive is
a (level, setpoint) pair; a deficit (level < setpoint) produces positive pressure
that motivates behavior. Pure.
"""

from __future__ import annotations

from typing import Any

CORE = (
    "mastery",
    "curiosity",
    "coherence",
    "economy",
    "agency",
    "commitment",
    "integrity",
    "recovery",
)

_DEFAULT_SETPOINT = 0.7
_RECOVERY_SETPOINT = 0.5


def new_drives() -> dict[str, dict[str, float]]:
    return {
        name: {
            "level": 0.5,
            "setpoint": _RECOVERY_SETPOINT if name == "recovery" else _DEFAULT_SETPOINT,
        }
        for name in CORE
    }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _nudge(level: float, amount: float) -> float:
    return _clamp(level + amount)


def update(d: dict[str, Any], outcome_features: dict[str, Any]) -> dict[str, Any]:
    """Pure: returns a new drives dict shifted by outcome_features."""
    new_d = {name: dict(v) for name, v in d.items()}
    verified_success = bool(outcome_features.get("verified_success", False))
    novelty = float(outcome_features.get("novelty", 0.0))
    progress = float(outcome_features.get("progress", 0.5))
    diff_size = float(outcome_features.get("diff_size", 0.0))
    integrity_violation = bool(outcome_features.get("integrity_violation", False))

    if verified_success:
        new_d["mastery"]["level"] = _nudge(new_d["mastery"]["level"], 0.1)
        new_d["recovery"]["level"] = _nudge(new_d["recovery"]["level"], 0.05)
        new_d["agency"]["level"] = _nudge(new_d["agency"]["level"], 0.05)
    else:
        new_d["recovery"]["level"] = _nudge(new_d["recovery"]["level"], -0.05)

    new_d["curiosity"]["level"] = _nudge(new_d["curiosity"]["level"], novelty * 0.2)

    if progress < 0.5:
        new_d["commitment"]["level"] = _nudge(
            new_d["commitment"]["level"], -0.1 * (0.5 - progress)
        )
    else:
        new_d["commitment"]["level"] = _nudge(
            new_d["commitment"]["level"], 0.1 * (progress - 0.5)
        )

    new_d["economy"]["level"] = _nudge(new_d["economy"]["level"], -0.05 * diff_size)

    if integrity_violation:
        new_d["integrity"]["level"] = _nudge(new_d["integrity"]["level"], -0.2)
    else:
        new_d["integrity"]["level"] = _nudge(new_d["integrity"]["level"], 0.02)

    new_d["coherence"]["level"] = _nudge(
        new_d["coherence"]["level"],
        0.05 if verified_success and not integrity_violation else -0.02,
    )

    return new_d


def pressure(d: dict[str, Any]) -> dict[str, float]:
    return {
        name: max(0.0, float(v["setpoint"]) - float(v["level"]))
        for name, v in d.items()
    }


__all__ = ["CORE", "new_drives", "update", "pressure"]
