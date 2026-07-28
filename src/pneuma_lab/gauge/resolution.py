"""Resolution statistics: can this gauge tell two items apart?

`%GRR`, `ndc` and `ICC` come straight from the variance components. They are the
AIAG-standard reporting triple, and `ndc >= 5` is the AIAG acceptance rule.

`ndc` degenerates exactly where we expect to land (sigma_item -> 0 makes it 0 and
uninformative about *how* it failed), so two distribution-free statistics carry
the load instead:

- `discriminationIndex` (D): probability that two independent measurement passes
  order an item pair the same way, ties scored as coin flips. 1 = perfect gauge,
  0.5 = no ordering information, and a constant channel scores exactly 0.5.
- `resolvingPower` (P): fraction of item pairs on which both passes return the
  *same nonzero* sign. This is the statistic T2 is proved on: strictly monotone
  post-processing leaves it exactly invariant, weakly monotone post-processing can
  only lower it.

`effectiveSupport` reports how many levels the channel actually emits, which is
often the whole story on its own.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .anova import VarianceComponents, varianceComponents
from .cube import BalancedMatrix
from .stats import shannonEntropy

#: Locked verdict thresholds (see g1-gauge-preregistration.md section 4).
USABLE_PCT_GRR = 30.0
USABLE_NDC = 5
USABLE_ICC = 0.70
USABLE_D = 0.80
MARGINAL_NDC = 2
MARGINAL_ICC = 0.50
MARGINAL_D = 0.65
DEGENERATE_SUPPORT = 2.0

#: AIAG's constant: 1.41 = sqrt(2), converting a variance ratio into distinct categories.
NDC_CONSTANT = 1.41


@dataclass(frozen=True)
class GaugeResolution:
    """Everything needed to render a verdict."""

    pct_grr: float
    ndc: int
    icc: float
    d: float
    resolving_power: float
    s_eff: float
    verdict: str
    components: VarianceComponents

    def asDict(self) -> dict:
        return {
            "pct_grr": self.pct_grr,
            "ndc": self.ndc,
            "icc": self.icc,
            "d": self.d,
            "resolving_power": self.resolving_power,
            "s_eff": self.s_eff,
            "verdict": self.verdict,
        }


def pctGrr(vc: VarianceComponents) -> float:
    if vc.sd_total <= 0.0:
        return 100.0
    return 100.0 * vc.sd_grr / vc.sd_total


def ndc(vc: VarianceComponents) -> int:
    if vc.sd_grr <= 0.0:
        # A perfectly repeatable gauge with no part variance still resolves nothing.
        return 0 if vc.sd_item <= 0.0 else 10**6
    return int(math.floor(NDC_CONSTANT * vc.sd_item / vc.sd_grr))


def icc(vc: VarianceComponents) -> float:
    if vc.var_total <= 0.0:
        return 0.0
    return vc.var_item / vc.var_total


def _passes(values: Sequence[float]) -> tuple[list[float], list[float]]:
    """Split replicates into two disjoint passes: even indices vs odd indices."""
    return (list(values[0::2]), list(values[1::2]))


def _pairStats(
    matrix: Mapping[tuple, Sequence[float]] | BalancedMatrix,
) -> tuple[float, float]:
    """Return (discrimination index D, resolving power P).

    Both are computed on *single measurements*, not on replicate averages: that is
    what a deployed pipeline actually reads, and it is what makes the monotone
    invariance in T2 exact rather than approximate.
    """
    cells = matrix.cells if isinstance(matrix, BalancedMatrix) else dict(matrix)
    items = sorted({k[0] for k in cells})
    conditions = sorted({k[1] for k in cells}, key=str)
    if len(items) < 2:
        return (float("nan"), float("nan"))

    agree_total = 0.0
    nonzero_agree_total = 0.0
    comparisons = 0
    for ci in range(len(items)):
        for cj in range(ci + 1, len(items)):
            item_a, item_b = items[ci], items[cj]
            for cond in conditions:
                va = cells.get((item_a, cond))
                vb = cells.get((item_b, cond))
                if not va or not vb:
                    continue
                a_first, a_second = _passes(va)
                b_first, b_second = _passes(vb)
                if not a_first or not a_second or not b_first or not b_second:
                    continue
                for x1, y1 in zip(a_first, b_first, strict=False):
                    s1 = _sign(x1 - y1)
                    for x2, y2 in zip(a_second, b_second, strict=False):
                        s2 = _sign(x2 - y2)
                        comparisons += 1
                        if s1 == 0 or s2 == 0:
                            agree_total += 0.5
                        elif s1 == s2:
                            agree_total += 1.0
                            nonzero_agree_total += 1.0
    if comparisons == 0:
        return (float("nan"), float("nan"))
    return (agree_total / comparisons, nonzero_agree_total / comparisons)


def discriminationIndex(matrix) -> float:
    return _pairStats(matrix)[0]


def resolvingPower(matrix) -> float:
    return _pairStats(matrix)[1]


def effectiveSupport(values: Sequence[float], *, quantum: float = 1e-9) -> float:
    """exp(entropy) of the empirical distribution over distinct emitted values."""
    if not values:
        return 0.0
    counts: dict[int, int] = {}
    for v in values:
        key = int(round(float(v) / quantum))
        counts[key] = counts.get(key, 0) + 1
    return math.exp(shannonEntropy(list(counts.values())))


def gaugeVerdict(
    *, pct_grr: float, ndc_value: int, icc_value: float, d: float, s_eff: float
) -> str:
    """Apply the locked verdict tiers. `DEGENERATE` outranks the others."""
    if s_eff < DEGENERATE_SUPPORT:
        return "DEGENERATE"
    if (
        pct_grr <= USABLE_PCT_GRR
        and ndc_value >= USABLE_NDC
        and icc_value >= USABLE_ICC
        and d >= USABLE_D
    ):
        return "USABLE"
    if ndc_value >= MARGINAL_NDC and icc_value >= MARGINAL_ICC and d >= MARGINAL_D:
        return "MARGINAL"
    return "UNINTERPRETABLE"


def gaugeResolution(matrix: BalancedMatrix) -> GaugeResolution:
    """Full resolution analysis of a balanced design."""
    vc = varianceComponents(matrix)
    d, p = _pairStats(matrix)
    flat = [v for values in matrix.cells.values() for v in values]
    s_eff = effectiveSupport(flat)
    g = pctGrr(vc)
    n = ndc(vc)
    i = icc(vc)
    return GaugeResolution(
        pct_grr=g,
        ndc=n,
        icc=i,
        d=d,
        resolving_power=p,
        s_eff=s_eff,
        verdict=gaugeVerdict(pct_grr=g, ndc_value=n, icc_value=i, d=d, s_eff=s_eff),
        components=vc,
    )


def _sign(x: float) -> int:
    if x > 0.0:
        return 1
    if x < 0.0:
        return -1
    return 0


__all__ = [
    "DEGENERATE_SUPPORT",
    "GaugeResolution",
    "MARGINAL_D",
    "MARGINAL_ICC",
    "MARGINAL_NDC",
    "USABLE_D",
    "USABLE_ICC",
    "USABLE_NDC",
    "USABLE_PCT_GRR",
    "discriminationIndex",
    "effectiveSupport",
    "gaugeResolution",
    "gaugeVerdict",
    "icc",
    "ndc",
    "pctGrr",
    "resolvingPower",
]
