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
import random
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
    saturation: dict | None
    verdict: str
    components: VarianceComponents
    selection_stability: dict | None = None
    cross_condition_stability: dict | None = None

    def asDict(self) -> dict:
        return {
            "pct_grr": self.pct_grr,
            "ndc": self.ndc,
            "icc": self.icc,
            "d": self.d,
            "resolving_power": self.resolving_power,
            "s_eff": self.s_eff,
            "saturation": self.saturation,
            "verdict": self.verdict,
            "selection_stability": self.selection_stability,
            "cross_condition_stability": self.cross_condition_stability,
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


def saturationRate(
    values: Sequence[float], *, low: float = 0.0, high: float = 1.0, tol: float = 1e-9
) -> dict:
    """Fraction of readings pinned to an endpoint of the scale.

    A saturated reading is censored: the instrument is reporting "at least this
    much" rather than a value. High saturation caps resolution independently of
    every variance component, because pinned readings cannot order each other.
    """
    if not values:
        return {"at_high": 0.0, "at_low": 0.0, "saturated": 0.0}
    n = len(values)
    at_high = sum(1 for v in values if v >= high - tol) / n
    at_low = sum(1 for v in values if v <= low + tol) / n
    return {"at_high": at_high, "at_low": at_low, "saturated": at_high + at_low}


def selectionStability(
    matrix: Mapping[tuple, Sequence[float]] | BalancedMatrix,
    *,
    q: float = 0.2,
    draws: int = 256,
    seed: int = 20260728,
) -> dict:
    """How reproducible is the *triage queue* a pipeline builds from this channel?

    A verification pipeline does not consume the mean of a confidence channel; it
    ranks items and verifies the least-confident fraction `q`. This measures the
    expected Jaccard overlap between the bottom-`q` sets chosen by two independent
    measurement passes.

    Ties are broken by seeded jitter drawn independently per pass, because that is
    what a real pipeline does when many items report the same number. Breaking ties
    by a stable key instead would manufacture agreement out of the ties themselves
    and inflate the statistic, which is precisely the failure mode being measured.

    The random-selection floor for two independent q-subsets is q / (2 - q).
    """
    cells = matrix.cells if isinstance(matrix, BalancedMatrix) else dict(matrix)
    items = sorted({k[0] for k in cells})
    conditions = sorted({k[1] for k in cells}, key=str)
    n_sel = max(1, int(math.ceil(q * len(items))))
    if len(items) < 2:
        return {
            "q": q,
            "jaccard": float("nan"),
            "random_floor": q / (2.0 - q),
            "n_selected": n_sel,
        }

    rng_a = random.Random(seed)
    rng_b = random.Random(seed + 977)
    overlaps: list[float] = []
    for cond in conditions:
        first: dict[str, float] = {}
        second: dict[str, float] = {}
        for item in items:
            series = cells.get((item, cond))
            if not series or len(series) < 2:
                continue
            a, b = series[0::2], series[1::2]
            first[item] = math.fsum(a) / len(a)
            second[item] = math.fsum(b) / len(b)
        shared = sorted(set(first) & set(second))
        if len(shared) < n_sel + 1:
            continue
        for _ in range(draws):
            pick_a = set(
                sorted(shared, key=lambda i: (first[i], rng_a.random()))[:n_sel]
            )
            pick_b = set(
                sorted(shared, key=lambda i: (second[i], rng_b.random()))[:n_sel]
            )
            union = pick_a | pick_b
            overlaps.append(len(pick_a & pick_b) / len(union) if union else 0.0)
    return {
        "q": q,
        "jaccard": (math.fsum(overlaps) / len(overlaps)) if overlaps else float("nan"),
        "random_floor": q / (2.0 - q),
        "n_selected": n_sel,
        "n_items": len(items),
    }


def crossConditionStability(
    matrix: Mapping[tuple, Sequence[float]] | BalancedMatrix,
    *,
    q: float = 0.2,
    draws: int = 256,
    seed: int = 20260728,
) -> dict:
    """Does the triage queue survive *rephrasing*, not just re-asking?

    `selectionStability` re-asks the same question and compares queues. This asks a
    differently-worded version of the same question and compares queues. The gap
    between the two is the practical meaning of the repeatability/reproducibility
    split: setting temperature to zero can drive the first to 1.0 while leaving the
    second untouched, which is how a channel can look perfectly stable and still not
    measure anything stable.
    """
    cells = matrix.cells if isinstance(matrix, BalancedMatrix) else dict(matrix)
    items = sorted({k[0] for k in cells})
    conditions = sorted({k[1] for k in cells}, key=str)
    n_sel = max(1, int(math.ceil(q * len(items))))
    floor = q / (2.0 - q)
    if len(items) < 2 or len(conditions) < 2:
        return {
            "q": q,
            "jaccard": float("nan"),
            "random_floor": floor,
            "n_selected": n_sel,
        }

    rng_a = random.Random(seed)
    rng_b = random.Random(seed + 977)
    overlaps: list[float] = []
    for i in range(len(conditions)):
        for j in range(i + 1, len(conditions)):
            first, second = {}, {}
            for item in items:
                va, vb = (
                    cells.get((item, conditions[i])),
                    cells.get((item, conditions[j])),
                )
                if not va or not vb:
                    continue
                first[item] = math.fsum(va) / len(va)
                second[item] = math.fsum(vb) / len(vb)
            shared = sorted(set(first) & set(second))
            if len(shared) < n_sel + 1:
                continue
            for _ in range(draws):
                pick_a = set(
                    sorted(shared, key=lambda x: (first[x], rng_a.random()))[:n_sel]
                )
                pick_b = set(
                    sorted(shared, key=lambda x: (second[x], rng_b.random()))[:n_sel]
                )
                union = pick_a | pick_b
                overlaps.append(len(pick_a & pick_b) / len(union) if union else 0.0)
    return {
        "q": q,
        "jaccard": (math.fsum(overlaps) / len(overlaps)) if overlaps else float("nan"),
        "random_floor": floor,
        "n_selected": n_sel,
        "n_items": len(items),
        "n_condition_pairs": len(conditions) * (len(conditions) - 1) // 2,
    }


def onewayIcc(groups: Mapping[str, Sequence[float]]) -> float:
    """ICC(1,1) from a balanced one-way random-effects design (item -> k measurements).

    Used by the remedy battery, where each remedy produces a *derived* score per
    item and the question is how reliable that derived score is.
    """
    items = sorted(groups)
    if len(items) < 2:
        return float("nan")
    ks = {len(groups[i]) for i in items}
    if len(ks) != 1:
        raise ValueError(f"onewayIcc requires balanced groups, got sizes {sorted(ks)}")
    k = ks.pop()
    if k < 2:
        return float("nan")
    n = len(items)
    means = {i: math.fsum(groups[i]) / k for i in items}
    grand = math.fsum(means.values()) / n
    ms_between = k * math.fsum((means[i] - grand) ** 2 for i in items) / (n - 1)
    ms_within = math.fsum(
        math.fsum((v - means[i]) ** 2 for v in groups[i]) for i in items
    ) / (n * (k - 1))
    denom = ms_between + (k - 1) * ms_within
    if denom <= 0.0:
        return 0.0
    return max(0.0, (ms_between - ms_within) / denom)


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
        saturation=saturationRate(flat),
        verdict=gaugeVerdict(pct_grr=g, ndc_value=n, icc_value=i, d=d, s_eff=s_eff),
        components=vc,
        selection_stability=selectionStability(matrix),
        cross_condition_stability=crossConditionStability(matrix),
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
    "crossConditionStability",
    "resolvingPower",
    "saturationRate",
    "selectionStability",
]
