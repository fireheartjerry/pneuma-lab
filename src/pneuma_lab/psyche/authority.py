"""Earned control-authority ladder (5-cap resolution).

Ported from ``migration/copied-from-9to5/reference-interfaces/authority.py``. The
9to5 version read HN_THETA_* / HN_AUTHORITY_MAX from ``config``; those documented
defaults are inlined here for standalone operation.

The system PROPOSES; authority is EARNED and multiply-capped; humans and safety
gates can always clamp it down. ``resolve`` returns the minimum tier over every
independent cap (conviction band, earned track-record ceiling, per-domain,
operator, safety, verifier) then a final hard clamp. Pure.
"""

from __future__ import annotations

from typing import Any

# Ordered tiers: index 0 = weakest, index 4 = strongest.
TIERS: tuple[str, ...] = ("cosmetic", "soft", "vote", "hold", "veto")

# Inlined 9to5 config defaults.
THETA_SOFT = 0.60
THETA_VOTE = 0.72
THETA_HOLD = 0.85
THETA_VETO = 0.95
AUTHORITY_MAX = "hold"  # config.HN_AUTHORITY_MAX default

# Earned-ceiling volume gates and rate thresholds.
MIN_SAMPLES = 5
VOTE_MIN_TOTAL = 20
VETO_MIN_TOTAL = 40
RATE_SOFT = 0.65
RATE_VOTE = 0.75
RATE_HOLD = 0.85
RATE_VETO = 0.95


def band(conviction: float) -> str:
    """Raw authority tier for ``conviction`` from the theta thresholds."""
    c = float(conviction)
    if c < THETA_SOFT:
        return "cosmetic"
    if c < THETA_VOTE:
        return "soft"
    if c < THETA_HOLD:
        return "vote"
    if c < THETA_VETO:
        return "hold"
    return "veto"


def earned_ceiling(track: dict[str, Any]) -> str:
    """5-tier earned authority ceiling from a ``track_record``-shaped dict.

    Cold start (``total < MIN_SAMPLES``) floors at cosmetic.
    """
    total = int(track.get("total", 0))
    rate = float(track.get("rate", 0.0))

    if total < MIN_SAMPLES:
        return "cosmetic"
    if rate >= RATE_VETO and total >= VETO_MIN_TOTAL:
        return "veto"
    if rate >= RATE_HOLD and total >= VOTE_MIN_TOTAL:
        return "hold"
    if rate >= RATE_VOTE and total >= VOTE_MIN_TOTAL:
        return "vote"
    if rate >= RATE_SOFT:
        return "soft"
    return "cosmetic"


def cap(tier: str, ceil: str) -> str:
    """Return ``min(tier, ceil)`` on the ``TIERS`` ordering (unknown = weakest)."""
    tier_idx = TIERS.index(tier) if tier in TIERS else 0
    ceil_idx = TIERS.index(ceil) if ceil in TIERS else 0
    return TIERS[min(tier_idx, ceil_idx)]


def resolve(
    conviction: float,
    track: dict[str, Any],
    domain_ceiling: str,
    operator_ceiling: str,
    safety_ceiling: str,
    verifier_ceiling: str,
) -> dict[str, Any]:
    """Effective control authority = ``min`` over every cap, then a hard clamp.

    Returns a resolution dict recording each cap and which one bound the result —
    the shape the ``AuthorityRequest.resolution`` field expects.
    """
    # cap keys use the AuthorityRequest.resolution schema vocabulary.
    caps = {
        "earned": earned_ceiling(track),
        "domain": domain_ceiling,
        "operator": operator_ceiling,
        "safety": safety_ceiling,
        "verifier_invariance": verifier_ceiling,
        "global_max": AUTHORITY_MAX,
    }
    tier = band(conviction)
    binding = "conviction_band"
    for name in (
        "earned",
        "domain",
        "operator",
        "safety",
        "verifier_invariance",
        "global_max",
    ):
        capped = cap(tier, caps[name])
        if TIERS.index(capped) < TIERS.index(tier):
            tier = capped
            binding = name
    return {
        "granted_tier": tier,
        "binding_cap": binding,
        "conviction_band": band(conviction),
        "caps": caps,
    }


__all__ = ["TIERS", "band", "earned_ceiling", "cap", "resolve"]
