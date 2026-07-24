"""Tests for the detectability calculator.

The module's whole purpose is to refuse to overclaim, so most of these tests assert
that it declines to produce a number rather than that it produces one.
"""

from __future__ import annotations

import math

import pytest

from pneuma_lab.audit.mde import (
    DEFAULT_ICC_GRID,
    AuditTable,
    NonIdentifiable,
    ReportedDesign,
    designEffect,
    detectabilityProfile,
    minimumDetectableEffect,
)


def mem0Design(claimed: float | None = None) -> ReportedDesign:
    """Mem0 as reported: ~2000 questions drawn from 10 conversations."""
    return ReportedDesign(
        label="Mem0",
        n_observations=2000,
        n_clusters=10,
        paired=True,
        discordance=0.25,
        source_quote="It comprises 10 extended conversations",
    )


def test_designEffectIsOneUnderIndependence() -> None:
    assert designEffect(200.0, 0.0) == pytest.approx(1.0)


def test_designEffectEqualsClusterSizeUnderPerfectCorrelation() -> None:
    assert designEffect(200.0, 1.0) == pytest.approx(200.0)


def test_designEffectMatchesKishFormula() -> None:
    assert designEffect(200.0, 0.05) == pytest.approx(1.0 + 199.0 * 0.05)


def test_designEffectRejectsOutOfRangeIcc() -> None:
    with pytest.raises(ValueError):
        designEffect(10.0, 1.5)
    with pytest.raises(ValueError):
        designEffect(10.0, -0.01)


def test_mdeIsMonotonicIncreasingInIcc() -> None:
    design = mem0Design()
    values = [minimumDetectableEffect(design, icc) for icc in DEFAULT_ICC_GRID]
    assert values == sorted(values)
    assert values[0] < values[-1]


def test_mdeAtPerfectCorrelationMatchesClusterLevelSampleSize() -> None:
    """At rho = 1 the effective n collapses to the cluster count exactly."""
    design = mem0Design()
    at_rho_one = minimumDetectableEffect(design, 1.0)
    cluster_level = ReportedDesign(
        label="cluster-level",
        n_observations=10,
        n_clusters=10,
        paired=True,
        discordance=0.25,
    )
    # DEFF = 1 when m = 1, so this is the same quantity computed on 10 units.
    assert at_rho_one == pytest.approx(minimumDetectableEffect(cluster_level, 0.0))


def test_mdeMatchesHandComputation() -> None:
    """Closed form: (1.95996 + 0.84162) * sqrt(d * DEFF / n)."""
    design = mem0Design()
    icc = 0.1
    deff = 1.0 + (200.0 - 1.0) * icc
    expected = (1.959963984540054 + 0.8416212335729143) * math.sqrt(0.25 * deff / 2000)
    assert minimumDetectableEffect(design, icc) == pytest.approx(expected)


def test_oneSidedIsSmallerThanTwoSided() -> None:
    design = mem0Design()
    one = minimumDetectableEffect(design, 0.1, two_sided=False)
    two = minimumDetectableEffect(design, 0.1, two_sided=True)
    assert one < two


def test_singleClusterIsNonIdentifiable() -> None:
    """Generative Agents: 100 rankings, all from one simulation."""
    design = ReportedDesign(
        label="Generative Agents",
        n_observations=100,
        n_clusters=1,
        paired=False,
        base_rate=0.5,
    )
    with pytest.raises(NonIdentifiable, match="single cluster"):
        design.assertIdentifiable()


def test_missingClusterCountIsNonIdentifiable() -> None:
    """A-MEM never states how many LoCoMo conversations it uses."""
    design = ReportedDesign(
        label="A-MEM",
        n_observations=7512,
        n_clusters=None,
        paired=True,
        discordance=0.25,
    )
    with pytest.raises(NonIdentifiable, match="not stated"):
        design.assertIdentifiable()
    with pytest.raises(NonIdentifiable):
        _ = design.cluster_size


def test_pairedDesignWithoutDiscordanceIsRejected() -> None:
    design = ReportedDesign(
        label="incomplete", n_observations=100, n_clusters=10, paired=True
    )
    with pytest.raises(NonIdentifiable, match="discordance"):
        design.assertIdentifiable()


def test_unpairedDesignWithoutBaseRateIsRejected() -> None:
    design = ReportedDesign(
        label="incomplete", n_observations=100, n_clusters=10, paired=False
    )
    with pytest.raises(NonIdentifiable, match="base rate"):
        design.assertIdentifiable()


def test_profileReturnsOneRowPerIccWithAssumptionsAttached() -> None:
    rows = detectabilityProfile(mem0Design(), claimed_effect=0.05)
    assert len(rows) == len(DEFAULT_ICC_GRID)
    for row in rows:
        assert str(row.icc) in row.assumptions
        assert "power=0.80" in row.assumptions
        assert "n=2000" in row.assumptions


def test_verdictFlipsAsIccRises() -> None:
    """A claim can clear its threshold under weak clustering and fail under strong.

    15 points clears the 10.4-point threshold at rho = 0.05 and fails the 44.3-point
    threshold at rho = 1. The flip is the whole point of reporting a range.
    """
    rows = detectabilityProfile(mem0Design(), claimed_effect=0.15)
    verdicts = {row.icc: row.verdict for row in rows}
    assert verdicts[0.05] == "above-detection-threshold"
    assert verdicts[1.0] == "below-detection-threshold"


def test_mem0IsUndetectableAtEveryIccOnTheGrid() -> None:
    """Regression pin on a headline number.

    Mem0 reports a 26% relative improvement in LLM-as-a-Judge score. Even at rho =
    0.05, the weakest clustering assumption we report, its design resolves only
    ~10.4 percentage points. This test exists so the number cannot drift silently
    between the calculator and the draft.
    """
    design = mem0Design()
    assert minimumDetectableEffect(design, 0.05) == pytest.approx(0.1036, abs=5e-4)
    assert minimumDetectableEffect(design, 1.0) == pytest.approx(0.4429, abs=5e-4)

    rows = detectabilityProfile(design, claimed_effect=0.05)
    assert all(row.verdict == "below-detection-threshold" for row in rows)


def test_noClaimedEffectIsRecordedNotGuessed() -> None:
    rows = detectabilityProfile(mem0Design(), claimed_effect=None)
    assert all(row.verdict == "no-claimed-effect-recorded" for row in rows)


def test_auditTableRecordsNonIdentifiableRatherThanDroppingIt() -> None:
    table = AuditTable()
    table.add(mem0Design(), claimed_effect=0.05)
    table.add(
        ReportedDesign(
            label="Generative Agents",
            n_observations=100,
            n_clusters=1,
            paired=False,
            base_rate=0.5,
        ),
        claimed_effect=0.3,
    )
    assert "Generative Agents" in table.summary()["non_identifiable"]
    assert len(table.rows) == len(DEFAULT_ICC_GRID)


def test_summaryNeverCollapsesToOneNumber() -> None:
    table = AuditTable()
    table.add(mem0Design(), claimed_effect=0.05)
    summary = table.summary()
    assert set(summary["below_threshold_by_icc"]) == set(DEFAULT_ICC_GRID)
    assert "conditional on its stated ICC" in summary["caveat"]


def test_unpairedFormulaUsesBaseRateVariance() -> None:
    design = ReportedDesign(
        label="unpaired",
        n_observations=800,
        n_clusters=5,
        paired=False,
        base_rate=0.5,
    )
    icc = 0.1
    deff = designEffect(160.0, icc)
    expected = (1.959963984540054 + 0.8416212335729143) * math.sqrt(
        2 * 0.5 * 0.5 * deff / 800
    )
    assert minimumDetectableEffect(design, icc) == pytest.approx(expected)
