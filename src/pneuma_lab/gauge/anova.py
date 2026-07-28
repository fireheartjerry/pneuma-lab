"""Crossed two-way random-effects variance components (AIAG ANOVA gauge study).

Model, for item i (random, the "part"), condition o (random, the "operator"),
replicate r:

    y_ior = mu + alpha_i + beta_o + (alpha*beta)_io + eps_ior

The ANOVA method of moments recovers the four variance components from the four
mean squares. Negative estimates are truncated at zero, which is the standard
convention, and every truncation is recorded so a card can report it: a
truncated `sigma2_item` is not a technicality, it is the finding.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .cube import BalancedMatrix


@dataclass(frozen=True)
class VarianceComponents:
    """Variance decomposition of one gauge study."""

    var_item: float
    var_condition: float
    var_interaction: float
    var_repeatability: float
    n_items: int
    n_conditions: int
    n_reps: int
    truncated: tuple[str, ...]
    grand_mean: float

    @property
    def var_reproducibility(self) -> float:
        return self.var_condition + self.var_interaction

    @property
    def var_grr(self) -> float:
        return self.var_repeatability + self.var_reproducibility

    @property
    def var_total(self) -> float:
        return self.var_item + self.var_grr

    @property
    def sd_item(self) -> float:
        return math.sqrt(max(self.var_item, 0.0))

    @property
    def sd_condition(self) -> float:
        return math.sqrt(max(self.var_condition, 0.0))

    @property
    def sd_interaction(self) -> float:
        return math.sqrt(max(self.var_interaction, 0.0))

    @property
    def sd_repeatability(self) -> float:
        return math.sqrt(max(self.var_repeatability, 0.0))

    @property
    def sd_reproducibility(self) -> float:
        return math.sqrt(max(self.var_reproducibility, 0.0))

    @property
    def sd_grr(self) -> float:
        return math.sqrt(max(self.var_grr, 0.0))

    @property
    def sd_total(self) -> float:
        return math.sqrt(max(self.var_total, 0.0))

    def asDict(self) -> dict:
        return {
            "var_item": self.var_item,
            "var_condition": self.var_condition,
            "var_interaction": self.var_interaction,
            "var_repeatability": self.var_repeatability,
            "var_reproducibility": self.var_reproducibility,
            "var_grr": self.var_grr,
            "var_total": self.var_total,
            "sd_item": self.sd_item,
            "sd_repeatability": self.sd_repeatability,
            "sd_reproducibility": self.sd_reproducibility,
            "sd_grr": self.sd_grr,
            "sd_total": self.sd_total,
            "n_items": self.n_items,
            "n_conditions": self.n_conditions,
            "n_reps": self.n_reps,
            "truncated": list(self.truncated),
            "grand_mean": self.grand_mean,
        }


def varianceComponents(
    cells: Mapping[tuple, Sequence[float]] | BalancedMatrix,
) -> VarianceComponents:
    """Estimate variance components from a balanced (item, condition) -> replicates map."""
    if isinstance(cells, BalancedMatrix):
        matrix = cells.cells
    else:
        matrix = dict(cells)
    if not matrix:
        raise ValueError("varianceComponents requires a non-empty design")

    items = sorted({k[0] for k in matrix})
    conditions = sorted({k[1] for k in matrix}, key=str)
    n_i, n_o = len(items), len(conditions)
    rep_counts = {len(v) for v in matrix.values()}
    if len(rep_counts) != 1:
        raise ValueError(f"unbalanced replicate counts: {sorted(rep_counts)}")
    n_r = rep_counts.pop()
    if n_i < 2 or n_o < 2:
        raise ValueError(
            f"need >= 2 items and >= 2 conditions, got items={n_i} conditions={n_o}"
        )
    if n_r < 2:
        raise ValueError(
            "need >= 2 replicates per cell; repeatability is otherwise unidentifiable"
        )
    if len(matrix) != n_i * n_o:
        raise ValueError("design is not fully crossed")

    cell_means = {k: math.fsum(v) / n_r for k, v in matrix.items()}
    grand = math.fsum(cell_means.values()) / (n_i * n_o)
    item_means = {
        i: math.fsum(cell_means[(i, o)] for o in conditions) / n_o for i in items
    }
    cond_means = {
        o: math.fsum(cell_means[(i, o)] for i in items) / n_i for o in conditions
    }

    ss_item = n_o * n_r * math.fsum((item_means[i] - grand) ** 2 for i in items)
    ss_cond = n_i * n_r * math.fsum((cond_means[o] - grand) ** 2 for o in conditions)
    ss_inter = n_r * math.fsum(
        (cell_means[(i, o)] - item_means[i] - cond_means[o] + grand) ** 2
        for i in items
        for o in conditions
    )
    ss_err = math.fsum(
        math.fsum((v - cell_means[k]) ** 2 for v in matrix[k]) for k in matrix
    )

    ms_item = ss_item / (n_i - 1)
    ms_cond = ss_cond / (n_o - 1)
    ms_inter = ss_inter / ((n_i - 1) * (n_o - 1))
    ms_err = ss_err / (n_i * n_o * (n_r - 1))

    raw = {
        "var_repeatability": ms_err,
        "var_interaction": (ms_inter - ms_err) / n_r,
        "var_condition": (ms_cond - ms_inter) / (n_i * n_r),
        "var_item": (ms_item - ms_inter) / (n_o * n_r),
    }
    truncated = tuple(sorted(name for name, value in raw.items() if value < 0.0))
    clipped = {name: max(value, 0.0) for name, value in raw.items()}

    return VarianceComponents(
        var_item=clipped["var_item"],
        var_condition=clipped["var_condition"],
        var_interaction=clipped["var_interaction"],
        var_repeatability=clipped["var_repeatability"],
        n_items=n_i,
        n_conditions=n_o,
        n_reps=n_r,
        truncated=truncated,
        grand_mean=grand,
    )


__all__ = ["VarianceComponents", "varianceComponents"]
