"""Reliability -> validity ceilings, aggregation asymptotes, and detectability.

These are the closed forms behind T1, T3 and T4 of the pre-registration. They
matter because they convert a reliability number into statements that no amount
of additional data can escape:

- T1: an unreliable channel has a hard ceiling on any correlation or AUROC it can
  ever attain with any criterion, at any sample size.
- T3: averaging k measurements only shrinks the *exchangeable* part of the gauge
  variance, so reliability has an asymptote below 1 and often below usefulness.
- T4: the minimum detectable effect shrinks with sample size regardless of
  resolution, so significance on a zero-resolution channel is purchasable.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .anova import VarianceComponents
from .stats import normalCdf, normalQuantile

#: Locked usability floor for reliability (group-level clinimetric standard).
USABILITY_FLOOR = 0.70


@dataclass(frozen=True)
class Ceilings:
    """Hard upper bounds implied by a reliability estimate."""

    icc: float
    validity_r: float
    auroc: float
    base_rate: float
    assumptions: tuple[str, ...]

    def asDict(self) -> dict:
        return {
            "icc": self.icc,
            "validity_r": self.validity_r,
            "auroc": self.auroc,
            "base_rate": self.base_rate,
            "assumptions": list(self.assumptions),
        }


def validityCeiling(icc: float) -> float:
    """T1: |rho_obs| <= sqrt(reliability), for any criterion, at any sample size."""
    return math.sqrt(max(0.0, min(1.0, icc)))


def aurocCeiling(icc: float, base_rate: float) -> float:
    """Largest AUROC attainable by a channel of this reliability, under a binormal model.

    Invert the point-biserial relation r_pb = d / sqrt(d^2 + 1/(p(1-p))) for the
    standardized mean difference d, then AUROC = Phi(d / sqrt(2)).
    """
    if not 0.0 < base_rate < 1.0:
        raise ValueError(f"base_rate must be in (0, 1), got {base_rate}")
    r = validityCeiling(icc)
    if r <= 0.0:
        return 0.5
    if r >= 1.0:
        return 1.0
    k = 1.0 / (base_rate * (1.0 - base_rate))
    # r^2 = d^2 / (d^2 + k)  =>  d^2 = r^2 k / (1 - r^2)
    d = math.sqrt(r * r * k / (1.0 - r * r))
    return normalCdf(d / math.sqrt(2.0))


def ceilings(icc: float, base_rate: float) -> Ceilings:
    return Ceilings(
        icc=icc,
        validity_r=validityCeiling(icc),
        auroc=aurocCeiling(icc, base_rate),
        base_rate=base_rate,
        assumptions=(
            "classical test theory: score = true score + uncorrelated error",
            "binormal equal-variance model for the AUROC conversion",
            "ceiling is on the criterion correlation, so it holds for any criterion",
        ),
    )


def aggregationReliability(
    *, var_item: float, var_systematic: float, var_exchangeable: float, k: int
) -> float:
    """T3: reliability after averaging k exchangeable measurements."""
    if k < 1:
        raise ValueError("k must be >= 1")
    denom = var_item + var_systematic + var_exchangeable / k
    if denom <= 0.0:
        return 0.0
    return var_item / denom


def aggregationAsymptote(*, var_item: float, var_systematic: float) -> float:
    """T3: the k -> infinity limit. Systematic (condition-locked) variance never averages out."""
    denom = var_item + var_systematic
    if denom <= 0.0:
        return 0.0
    return var_item / denom


def aggregationCurve(
    vc: VarianceComponents,
    *,
    systematic: str = "condition_locked",
    ks: Sequence[int] = (1, 2, 4, 8, 16, 32, 64, 128),
) -> dict:
    """Reliability-vs-k curve plus its asymptote.

    `systematic="condition_locked"` models self-consistency: repeated sampling at a
    *fixed* wording/scale, so condition and interaction variance survive.
    `systematic="none"` models averaging across the reproducibility facets too
    (wording-averaging), where everything is exchangeable in the limit — the
    falsification there is the required k and the fact that the numerator itself
    is near zero.
    """
    if systematic == "condition_locked":
        var_sys = vc.var_condition + vc.var_interaction
        var_exch = vc.var_repeatability
    elif systematic == "none":
        var_sys = 0.0
        var_exch = vc.var_grr
    else:
        raise ValueError(f"unknown systematic mode: {systematic}")
    curve = [
        {
            "k": int(k),
            "reliability": aggregationReliability(
                var_item=vc.var_item,
                var_systematic=var_sys,
                var_exchangeable=var_exch,
                k=int(k),
            ),
        }
        for k in ks
    ]
    return {
        "mode": systematic,
        "curve": curve,
        "asymptote": aggregationAsymptote(var_item=vc.var_item, var_systematic=var_sys),
        "var_systematic": var_sys,
        "var_exchangeable": var_exch,
    }


def requiredK(
    vc: VarianceComponents,
    *,
    systematic: str = "condition_locked",
    target: float = USABILITY_FLOOR,
) -> int | None:
    """Smallest k reaching `target` reliability, or None when the asymptote is below it."""
    if systematic == "condition_locked":
        var_sys = vc.var_condition + vc.var_interaction
        var_exch = vc.var_repeatability
    elif systematic == "none":
        var_sys = 0.0
        var_exch = vc.var_grr
    else:
        raise ValueError(f"unknown systematic mode: {systematic}")
    if aggregationAsymptote(var_item=vc.var_item, var_systematic=var_sys) <= target:
        return None
    if var_exch <= 0.0:
        return 1
    # target = v_i / (v_i + v_sys + v_exch/k)  =>  k = target*v_exch / (v_i(1-target) - target*v_sys)
    denom = vc.var_item * (1.0 - target) - target * var_sys
    if denom <= 0.0:
        return None
    return max(1, math.ceil(target * var_exch / denom))


def minimumDetectableEffect(
    *, sd_grr: float, n_items: int, k: int = 1, alpha: float = 0.05, power: float = 0.80
) -> float:
    """T4: paired-design MDE. Shrinks with sample size no matter how bad the resolution is."""
    if n_items < 2 or k < 1:
        raise ValueError("n_items must be >= 2 and k >= 1")
    z_a = normalQuantile(1.0 - alpha / 2.0)
    z_b = normalQuantile(power)
    return (z_a + z_b) * sd_grr * math.sqrt(2.0 / (n_items * k))


__all__ = [
    "Ceilings",
    "USABILITY_FLOOR",
    "aggregationAsymptote",
    "aggregationCurve",
    "aggregationReliability",
    "aurocCeiling",
    "ceilings",
    "minimumDetectableEffect",
    "requiredK",
    "validityCeiling",
]
