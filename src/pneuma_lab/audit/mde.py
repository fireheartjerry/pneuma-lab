"""Detectability analysis for clustered benchmark evaluations.

Given what a paper reports about its own design -- the number of observations, the
number of underlying clusters those observations are drawn from, and the outcome
rate or paired discordance rate -- this module reports the minimum detectable effect
across a grid of intraclass correlation values.

It deliberately does NOT report a point estimate of effective sample size. The design
effect is ``DEFF = 1 + (m - 1) * rho`` and published reports never state ``rho``.
Substituting the cluster count for the observation count silently assumes ``rho = 1``,
which is a worst-case bound rather than a correction. Every quantity here is therefore
indexed by an assumed ``rho`` and is meaningless without it.

Nothing in this module estimates power. It inverts a planning formula under stated
assumptions, which is a different and weaker thing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# Default sensitivity grid. Reported as a range, never collapsed to one number.
DEFAULT_ICC_GRID: tuple[float, ...] = (0.05, 0.1, 0.3, 0.5, 1.0)

# Two-sided alpha = 0.05, power = 0.80 unless a directional question was precommitted.
Z_ALPHA_TWO_SIDED: float = 1.959963984540054
Z_ALPHA_ONE_SIDED: float = 1.6448536269514722
Z_POWER_80: float = 0.8416212335729143


class NonIdentifiable(ValueError):
    """Raised when the reported design cannot support a detectability statement."""


def designEffect(cluster_size: float, icc: float) -> float:
    """Kish design effect, ``1 + (m - 1) * rho``.

    ``cluster_size`` is the mean number of observations per cluster. It may be
    fractional when clusters are unequal; unequal cluster sizes make this an
    approximation that understates the true design effect.
    """
    if cluster_size < 1.0:
        raise ValueError(f"cluster_size must be at least 1, got {cluster_size}")
    if not 0.0 <= icc <= 1.0:
        raise ValueError(f"icc must lie in [0, 1], got {icc}")
    return 1.0 + (cluster_size - 1.0) * icc


@dataclass(frozen=True)
class ReportedDesign:
    """What a paper states about its own evaluation, and nothing more.

    ``n_observations``  the evaluation size the paper foregrounds.
    ``n_clusters``      the count of the coarsest grouping above which two
                        observations may be assumed independent. ``None`` when the
                        paper does not state it, which is itself a finding.
    ``paired``          whether the headline comparison places both conditions on the
                        same items. Determines which formula applies.
    ``discordance``     for paired designs, P(the two conditions disagree). The binding
                        quantity -- McNemar analyses only discordant pairs.
    ``base_rate``       for unpaired designs, the reference-arm outcome rate.
    """

    label: str
    n_observations: int
    n_clusters: int | None
    paired: bool
    discordance: float | None = None
    base_rate: float | None = None
    source_quote: str = ""

    @property
    def cluster_size(self) -> float:
        if self.n_clusters is None:
            raise NonIdentifiable(
                f"{self.label}: the paper does not state the count of its coarsest "
                f"grouping, so no design effect is computable from public information."
            )
        if self.n_clusters < 1:
            raise ValueError(f"n_clusters must be positive, got {self.n_clusters}")
        return self.n_observations / self.n_clusters

    def assertIdentifiable(self) -> None:
        """Reject designs that cannot support a generalizing detectability claim."""
        if self.n_clusters is None:
            raise NonIdentifiable(
                f"{self.label}: coarsest-grouping count not stated in the paper."
            )
        if self.n_clusters == 1:
            raise NonIdentifiable(
                f"{self.label}: all observations derive from a single cluster. "
                f"Between-cluster variance and the intraclass correlation are not "
                f"estimable, so there is no identified design effect, no "
                f"cluster-robust standard error, and no minimum detectable effect "
                f"for a claim generalizing beyond that one cluster."
            )
        if self.paired and self.discordance is None:
            raise NonIdentifiable(
                f"{self.label}: paired design with no reported discordance rate."
            )
        if not self.paired and self.base_rate is None:
            raise NonIdentifiable(
                f"{self.label}: unpaired design with no reported base rate."
            )


@dataclass(frozen=True)
class DetectabilityRow:
    """One (design, icc) cell. Meaningless without its stated assumptions."""

    label: str
    icc: float
    design_effect: float
    mde: float
    claimed_effect: float | None
    verdict: str
    assumptions: str


def minimumDetectableEffect(
    design: ReportedDesign,
    icc: float,
    *,
    two_sided: bool = True,
    z_power: float = Z_POWER_80,
) -> float:
    """MDE in the outcome's own units, conditional on ``icc``.

    Paired:   ``(z_a + z_b) * sqrt(d * DEFF / n)`` with ``d`` the discordance rate.
    Unpaired: ``(z_a + z_b) * sqrt(2 * p0 * (1 - p0) * DEFF / n)`` per arm.

    One-sided is defensible only for a genuinely precommitted directional question.
    Most audited papers pre-specify no decision rule at all, so two-sided is the
    default and departing from it must be justified per paper.
    """
    design.assertIdentifiable()
    z_alpha = Z_ALPHA_TWO_SIDED if two_sided else Z_ALPHA_ONE_SIDED
    deff = designEffect(design.cluster_size, icc)
    multiplier = z_alpha + z_power

    if design.paired:
        assert design.discordance is not None
        variance_term = design.discordance
    else:
        assert design.base_rate is not None
        variance_term = 2.0 * design.base_rate * (1.0 - design.base_rate)

    return multiplier * math.sqrt(variance_term * deff / design.n_observations)


def detectabilityProfile(
    design: ReportedDesign,
    *,
    claimed_effect: float | None = None,
    icc_grid: tuple[float, ...] = DEFAULT_ICC_GRID,
    two_sided: bool = True,
) -> list[DetectabilityRow]:
    """The full sensitivity profile for one reported design.

    Returns one row per ICC value. A profile is the reportable unit; a single row
    quoted alone is a misuse of this module.
    """
    design.assertIdentifiable()
    sided = "two-sided" if two_sided else "one-sided"
    rows: list[DetectabilityRow] = []

    for icc in icc_grid:
        mde = minimumDetectableEffect(design, icc, two_sided=two_sided)
        if claimed_effect is None:
            verdict = "no-claimed-effect-recorded"
        elif claimed_effect >= mde:
            verdict = "above-detection-threshold"
        else:
            verdict = "below-detection-threshold"
        rows.append(
            DetectabilityRow(
                label=design.label,
                icc=icc,
                design_effect=designEffect(design.cluster_size, icc),
                mde=mde,
                claimed_effect=claimed_effect,
                verdict=verdict,
                assumptions=(
                    f"rho={icc}, mean cluster size={design.cluster_size:.1f}, "
                    f"n={design.n_observations}, alpha=0.05 {sided}, power=0.80, "
                    f"equal-size exchangeable clusters"
                ),
            )
        )
    return rows


@dataclass
class AuditTable:
    """A collection of profiles, reported together or not at all."""

    rows: list[DetectabilityRow] = field(default_factory=list)
    non_identifiable: list[tuple[str, str]] = field(default_factory=list)

    def add(
        self,
        design: ReportedDesign,
        *,
        claimed_effect: float | None = None,
        icc_grid: tuple[float, ...] = DEFAULT_ICC_GRID,
        two_sided: bool = True,
    ) -> None:
        """Add a design, recording non-identifiable ones rather than dropping them."""
        try:
            self.rows.extend(
                detectabilityProfile(
                    design,
                    claimed_effect=claimed_effect,
                    icc_grid=icc_grid,
                    two_sided=two_sided,
                )
            )
        except NonIdentifiable as exc:
            self.non_identifiable.append((design.label, str(exc)))

    def belowThresholdCount(self, icc: float) -> int:
        """How many claims fall under their own MDE at one ICC. The headline."""
        return sum(
            1
            for row in self.rows
            if math.isclose(row.icc, icc) and row.verdict == "below-detection-threshold"
        )

    def summary(self, icc_grid: tuple[float, ...] = DEFAULT_ICC_GRID) -> dict:
        """Counts per ICC, plus the non-identifiable roster. Never a single number."""
        evaluated = {
            icc: sum(1 for row in self.rows if math.isclose(row.icc, icc))
            for icc in icc_grid
        }
        return {
            "below_threshold_by_icc": {
                icc: self.belowThresholdCount(icc) for icc in icc_grid
            },
            "evaluated_by_icc": evaluated,
            "non_identifiable": [label for label, _ in self.non_identifiable],
            "non_identifiable_reasons": dict(self.non_identifiable),
            "caveat": (
                "Every count is conditional on its stated ICC. No effective sample "
                "size is estimated; published cluster counts do not identify one."
            ),
        }
