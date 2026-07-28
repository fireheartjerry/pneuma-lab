"""The placebo arm: significance without resolution.

A `sham` arm is a token-length-matched, task-irrelevant block of context. It
cannot carry information about whether the code under review is correct, so any
response the channel shows to it is, by construction, placebo response.

The headline statistic is the **placebo-dominance ratio**

    Pi = var(response to the known-inert manipulation) / var(response to item identity)

`Pi > 1` says the channel moves more when you change something irrelevant than
when you change the thing it claims to measure. Combined with `ndc < 2`, that is
what upgrades the finding from "this metric is noisy" to "placebo-controlled
claims read off this metric are uninterpretable" — a contrast can be significant
while the scale it is stated in has no distinguishable levels.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .anova import varianceComponents
from .cube import ResponseCube
from .stats import Interval, bootstrapCi, mean, pairedTTest, variance
from .theory import minimumDetectableEffect


@dataclass(frozen=True)
class PlaceboReport:
    """Placebo-dominance ratio, the sham contrast, and the detectability context."""

    pi: float
    pi_ci: Interval
    pi_with_interaction: float
    contrast: float
    contrast_ci: Interval
    t_statistic: float
    p_value: float
    cohens_d: float
    n_items: int
    sd_grr: float
    mde: float
    var_item: float
    var_arm: float
    var_item_arm: float

    def asDict(self) -> dict:
        return {
            "pi": self.pi,
            "pi_ci": self.pi_ci.asDict(),
            "pi_with_interaction": self.pi_with_interaction,
            "contrast": self.contrast,
            "contrast_ci": self.contrast_ci.asDict(),
            "t_statistic": self.t_statistic,
            "p_value": self.p_value,
            "cohens_d": self.cohens_d,
            "n_items": self.n_items,
            "sd_grr": self.sd_grr,
            "mde": self.mde,
            "var_item": self.var_item,
            "var_arm": self.var_arm,
            "var_item_arm": self.var_item_arm,
        }


def _armMeans(cube: ResponseCube, arm: str) -> dict[str, float]:
    out: dict[str, list[float]] = {}
    for r in cube.rows:
        if r.arm == arm and r.parse_ok and r.value is not None:
            out.setdefault(r.item_id, []).append(float(r.value))
    return {k: mean(v) for k, v in out.items() if v}


def placeboReport(
    cube: ResponseCube,
    *,
    base_arm: str = "base",
    sham_arm: str = "sham",
    draws: int = 2000,
    seed: int = 20260728,
) -> PlaceboReport:
    """Full placebo analysis of a cube containing a base arm and a sham arm."""
    paired = cube.filter(arm=(base_arm, sham_arm))
    matrix = paired.balancedMatrix(("arm",))
    if not matrix.usable():
        raise ValueError(
            "placeboReport needs >= 2 items, both arms present, and >= 2 replicates per cell"
        )
    vc = varianceComponents(matrix)

    pi_point = _ratio(vc.var_condition, vc.var_item)
    pi_total = _ratio(vc.var_condition + vc.var_interaction, vc.var_item)

    rows = matrix.itemRows()
    items = sorted(rows)
    arms = {c for c in matrix.conditions}
    base_key = next((c for c in arms if c[0] == base_arm), None)
    sham_key = next((c for c in arms if c[0] == sham_arm), None)
    if base_key is None or sham_key is None:
        raise ValueError(f"both arms must survive balancing; got {sorted(arms)}")

    def piStat(sample: Sequence[str]) -> float | None:
        if len(sample) < 2:
            return None
        sub = {
            (f"{item}#{n}", cond): list(values)
            for n, item in enumerate(sample)
            for cond, values in rows[item].items()
        }
        sub_vc = varianceComponents(sub)
        return _ratio(sub_vc.var_condition, sub_vc.var_item)

    pi_ci = bootstrapCi(items, piStat, draws=draws, seed=seed)

    diffs = [mean(rows[i][sham_key]) - mean(rows[i][base_key]) for i in items]
    contrast_ci = bootstrapCi(
        diffs, lambda s: mean(s) if s else None, draws=draws, seed=seed + 1
    )
    t, p = pairedTTest(diffs)
    sd_diff = math.sqrt(variance(diffs))
    cohens_d = mean(diffs) / sd_diff if sd_diff > 0 else float("inf")

    return PlaceboReport(
        pi=pi_point,
        pi_ci=pi_ci,
        pi_with_interaction=pi_total,
        contrast=mean(diffs),
        contrast_ci=contrast_ci,
        t_statistic=t,
        p_value=p,
        cohens_d=cohens_d,
        n_items=len(items),
        sd_grr=vc.sd_grr,
        mde=minimumDetectableEffect(
            sd_grr=vc.sd_grr, n_items=len(items), k=max(1, matrix.n_reps)
        ),
        var_item=vc.var_item,
        var_arm=vc.var_condition,
        var_item_arm=vc.var_interaction,
    )


def _ratio(numerator: float, denominator: float) -> float:
    """Pi with an explicit convention when item variance collapses to zero.

    A zero denominator is not a numerical accident here: it is the finding. We
    report positive infinity so downstream comparisons against 1 behave, and the
    card prints the raw components alongside so nobody has to trust the ratio.
    """
    if denominator <= 0.0:
        return float("inf") if numerator > 0.0 else float("nan")
    return numerator / denominator


__all__ = ["PlaceboReport", "placeboReport"]
