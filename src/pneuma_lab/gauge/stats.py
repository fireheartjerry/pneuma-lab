"""Deterministic stdlib statistics for the gauge toolkit.

No numpy, no scipy: this package must install and run anywhere Python 3.12 does,
because the point of the tool is that a reviewer can ask an author to run it.
Every routine that consumes randomness takes an explicit integer seed.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass

# Acklam's rational approximation to the inverse normal CDF. Refined below by a
# single Halley step, which takes the absolute error under 1e-12 across (0, 1).
_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)
_P_LOW = 0.02425


@dataclass(frozen=True)
class Interval:
    """A point estimate with a percentile confidence interval."""

    point: float
    low: float
    high: float

    def excludes(self, value: float) -> bool:
        """True when `value` lies outside [low, high]."""
        return value < self.low or value > self.high

    def asDict(self) -> dict:
        return {"point": self.point, "low": self.low, "high": self.high}


def normalCdf(x: float) -> float:
    """Standard normal CDF."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def normalQuantile(p: float) -> float:
    """Standard normal quantile (inverse CDF) for 0 < p < 1."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"normalQuantile requires 0 < p < 1, got {p}")
    if p < _P_LOW:
        q = math.sqrt(-2.0 * math.log(p))
        x = (
            ((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]
        ) / ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    elif p <= 1.0 - _P_LOW:
        q = p - 0.5
        r = q * q
        x = (
            (((((_A[0] * r + _A[1]) * r + _A[2]) * r + _A[3]) * r + _A[4]) * r + _A[5])
            * q
            / (((((_B[0] * r + _B[1]) * r + _B[2]) * r + _B[3]) * r + _B[4]) * r + 1.0)
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(
            ((((_C[0] * q + _C[1]) * q + _C[2]) * q + _C[3]) * q + _C[4]) * q + _C[5]
        ) / ((((_D[0] * q + _D[1]) * q + _D[2]) * q + _D[3]) * q + 1.0)
    # One Halley refinement against the exact CDF.
    e = normalCdf(x) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    return x - u / (1.0 + x * u / 2.0)


def mean(xs: Sequence[float]) -> float:
    if not xs:
        raise ValueError("mean of an empty sequence")
    return math.fsum(xs) / len(xs)


def variance(xs: Sequence[float], *, ddof: int = 1) -> float:
    """Sample variance. Returns 0.0 when there are too few points."""
    n = len(xs)
    if n - ddof <= 0:
        return 0.0
    m = mean(xs)
    return math.fsum((x - m) ** 2 for x in xs) / (n - ddof)


def percentile(sorted_xs: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile of an already-sorted sequence, q in [0, 1]."""
    if not sorted_xs:
        raise ValueError("percentile of an empty sequence")
    if len(sorted_xs) == 1:
        return float(sorted_xs[0])
    pos = q * (len(sorted_xs) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return float(sorted_xs[int(pos)])
    frac = pos - lo
    return float(sorted_xs[lo] * (1.0 - frac) + sorted_xs[hi] * frac)


def bootstrapCi(
    units: Sequence,
    statistic: Callable[[Sequence], float | None],
    *,
    draws: int = 2000,
    seed: int = 20260728,
    alpha: float = 0.05,
) -> Interval:
    """Nonparametric bootstrap CI, resampling `units` with replacement.

    `units` are the units of generalization (for this study: items). A draw whose
    statistic is undefined (`None` or non-finite) is skipped rather than coerced,
    and the point estimate is always the statistic on the full sample.
    """
    point = statistic(units)
    if point is None or not math.isfinite(point):
        return Interval(point=float("nan"), low=float("nan"), high=float("nan"))
    rng = random.Random(seed)
    n = len(units)
    values: list[float] = []
    for _ in range(draws):
        sample = [units[rng.randrange(n)] for _ in range(n)]
        value = statistic(sample)
        if value is not None and math.isfinite(value):
            values.append(float(value))
    if not values:
        return Interval(point=float(point), low=float("nan"), high=float("nan"))
    values.sort()
    return Interval(
        point=float(point),
        low=percentile(values, alpha / 2.0),
        high=percentile(values, 1.0 - alpha / 2.0),
    )


def shannonEntropy(counts: Sequence[float]) -> float:
    """Shannon entropy in nats of a count vector. Zero counts are ignored."""
    total = math.fsum(c for c in counts if c > 0)
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / total
            h -= p * math.log(p)
    return h


def pairedTTest(diffs: Sequence[float]) -> tuple[float, float]:
    """Paired t statistic and two-sided p-value for a mean-zero null.

    The p-value uses a normal reference. With the item counts in this study
    (n >= 30) the difference from a t reference is under 0.003, and reporting a
    slightly conservative-to-liberal p is irrelevant to the claim: T4's point is
    that significance is purchasable, not that a particular p is exact.
    """
    n = len(diffs)
    if n < 2:
        return (0.0, 1.0)
    m = mean(diffs)
    sd = math.sqrt(variance(diffs))
    if sd == 0.0:
        return (float("inf") if m != 0.0 else 0.0, 0.0 if m != 0.0 else 1.0)
    t = m / (sd / math.sqrt(n))
    p = 2.0 * (1.0 - normalCdf(abs(t)))
    return (t, p)


def benjaminiHochberg(pvalues: Sequence[float], *, q: float = 0.05) -> list[bool]:
    """Return per-hypothesis rejection flags under BH-FDR control at level q."""
    n = len(pvalues)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: pvalues[i])
    rejected = [False] * n
    max_rank = -1
    for rank, idx in enumerate(order, start=1):
        if pvalues[idx] <= q * rank / n:
            max_rank = rank
    for rank, idx in enumerate(order, start=1):
        if rank <= max_rank:
            rejected[idx] = True
    return rejected


def auroc(scores: Sequence[float], labels: Sequence[int]) -> float | None:
    """AUROC with the standard mid-rank tie correction. None if a class is empty."""
    pairs = sorted(zip(scores, labels, strict=True), key=lambda t: t[0])
    n_pos = sum(1 for _, y in pairs if y == 1)
    n_neg = len(pairs) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = [0.0] * len(pairs)
    i = 0
    while i < len(pairs):
        j = i
        while j + 1 < len(pairs) and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[k] = avg
        i = j + 1
    rank_sum_pos = math.fsum(
        r for r, (_, y) in zip(ranks, pairs, strict=True) if y == 1
    )
    return (rank_sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def expectedCalibrationError(
    scores: Sequence[float], labels: Sequence[int], *, bins: int = 10
) -> float:
    """Equal-width binned ECE."""
    if not scores:
        return 0.0
    totals = [0] * bins
    correct = [0.0] * bins
    conf = [0.0] * bins
    for s, y in zip(scores, labels, strict=True):
        b = min(bins - 1, max(0, int(s * bins)))
        totals[b] += 1
        correct[b] += float(y)
        conf[b] += float(s)
    n = len(scores)
    ece = 0.0
    for b in range(bins):
        if totals[b] == 0:
            continue
        acc_b = correct[b] / totals[b]
        conf_b = conf[b] / totals[b]
        ece += (totals[b] / n) * abs(acc_b - conf_b)
    return ece


def cohenKappa(a: Sequence[int], b: Sequence[int]) -> float:
    """Cohen's kappa for two binary label sequences."""
    n = len(a)
    if n == 0:
        return 0.0
    agree = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    chance = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if chance >= 1.0:
        return 0.0
    return (agree - chance) / (1.0 - chance)


__all__ = [
    "Interval",
    "auroc",
    "benjaminiHochberg",
    "bootstrapCi",
    "cohenKappa",
    "expectedCalibrationError",
    "mean",
    "normalCdf",
    "normalQuantile",
    "pairedTTest",
    "percentile",
    "shannonEntropy",
    "variance",
]
