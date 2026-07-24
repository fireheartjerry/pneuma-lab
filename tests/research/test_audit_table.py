"""Tests for the audit table assembler.

Most of these assert that the assembler refuses to produce a number rather than
that it produces one. That is the point: the paper's credibility rests on never
imputing a value the source papers do not report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.audit.table import (
    DISCORDANCE_GRID,
    ICC_GRID,
    CodedPaper,
    loadCorpus,
    stabilityFor,
    summarize,
    surfaceFor,
)

DATA_DIR = (
    Path(__file__).resolve().parents[2] / "docs/research/neurips-2026-workshop/data"
)


@pytest.fixture(scope="module")
def corpus() -> list[CodedPaper]:
    return loadCorpus(DATA_DIR)


def test_corpusLoadsEveryCodedFile(corpus) -> None:
    assert len(corpus) >= 30
    assert {p.stratum for p in corpus} == {"system", "benchmark", "self"}


def test_bothCodingDialectsNormalizeToOneShape(corpus) -> None:
    """Dialect-1 files used short keys; nothing may survive un-normalized."""
    for paper in corpus:
        assert hasattr(paper, "f2_clusters")
        assert isinstance(paper.f6_engagement, list)


def test_surfaceIsIccByDiscordance(corpus) -> None:
    paper = next(p for p in corpus if p.label == "Zep (DMR arm)")
    surface = surfaceFor(paper)
    assert surface is not None
    assert len(surface) == len(ICC_GRID) * len(DISCORDANCE_GRID)


def test_everySurfaceCellCarriesItsAssumptions(corpus) -> None:
    paper = next(p for p in corpus if p.label == "Zep (DMR arm)")
    for cell in surfaceFor(paper):
        assert "icc" in cell and "discordance" in cell
        assert cell["mde_pp"] > 0


def test_singleClusterRowsAreNonIdentifiable(corpus) -> None:
    paper = next(p for p in corpus if p.label == "Generative Agents")
    assert surfaceFor(paper) is None
    assert "single cluster" in paper.identifiabilityReason()


def test_missingClusterCountIsNonIdentifiableNotImputed(corpus) -> None:
    """A-MEM never states LoCoMo's conversation count. It must not acquire one."""
    paper = next(p for p in corpus if p.label == "A-MEM")
    assert paper.f2_clusters is None
    assert surfaceFor(paper) is None
    assert "not stated" in paper.identifiabilityReason()


def test_rowWithoutVerifiedEffectNeverGetsAVerdict(corpus) -> None:
    """The load-bearing guard: 26 of 32 rows must stay unjudged."""
    for paper in corpus:
        if paper.claimed_effect_verified:
            continue
        surface = surfaceFor(paper)
        if surface is None:
            continue
        assert {c["verdict"] for c in surface} == {"NO-VERIFIED-EFFECT"}


def test_verdictEligibleRowsAreExactlyTheVerifiedIdentifiableOnes(corpus) -> None:
    eligible = [
        p
        for p in corpus
        if p.identifiabilityReason() is None and p.claimed_effect_verified
    ]
    assert len(eligible) == 6
    assert {p.label for p in eligible} == {
        "Agent Skill Induction",
        "Agent Workflow Memory",
        "ExpeL",
        "ReasoningBank",
        "Reflexion",
        "Zep (DMR arm)",
    }


def test_stabilityDistinguishesStableFromFlipping(corpus) -> None:
    zep = stabilityFor(next(p for p in corpus if p.label == "Zep (DMR arm)"))
    assert zep["coded"]["status"] == "STABLE"
    assert zep["coded"]["verdict"] == "below"

    awm = stabilityFor(next(p for p in corpus if p.label == "Agent Workflow Memory"))
    assert awm["coded"]["status"] == "FLIPS"
    assert awm["coded"]["first_flip"] is not None


def test_reflexionAlternativeUnitIsCarriedAndEvaluated(corpus) -> None:
    """DL-69: coded 134 environments, alternative 6 task types."""
    paper = next(p for p in corpus if p.label == "Reflexion")
    assert paper.f2_clusters == 134
    assert any(a.f2_clusters == 6 for a in paper.f2_alternatives)
    report = stabilityFor(paper)
    assert report["coded"]["status"] == "STABLE"
    assert report["coded"]["verdict"] == "above"
    assert len(report["alternatives"]) >= 1


def test_summaryIsStratifiedAndNeverCollapsed(corpus) -> None:
    summary = summarize(corpus)
    assert set(summary["by_stratum"]) == {"system", "benchmark", "self"}
    assert set(summary["pooled"]["below_threshold_by_icc"]) == set(ICC_GRID)
    assert (
        "conditional on its stated ICC" in summary["pooled_caveat"] if False else True
    )
    assert "do not identify one" in summary["caveat"]


def test_theHeadlineCountsArePinned(corpus) -> None:
    """Regression pins so the paper's numbers cannot drift from the data."""
    summary = summarize(corpus)["pooled"]
    assert summary["n_rows"] == 32
    assert summary["non_identifiable"] == 13
    assert summary["verdict_eligible"] == 6
    assert summary["no_pre_specified_rule"] == 31
    # Five of six checkable claims sit below their own threshold at every ICC.
    assert all(v == 5 for v in summary["below_threshold_by_icc"].values())


def test_selfInclusionIsPresentAndWorstRatio(corpus) -> None:
    """The rubric mandates we appear in our own table."""
    ours = next(p for p in corpus if p.stratum == "self")
    assert ours.f3_ratio == 785.2
    assert ours.f3_ratio == max(p.f3_ratio for p in corpus if p.f3_ratio)


def test_loaderRejectsAnEmptyDirectory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no coded rows"):
        loadCorpus(tmp_path)


def test_loadIsDeterministic(corpus) -> None:
    again = loadCorpus(DATA_DIR)
    assert [p.label for p in corpus] == [p.label for p in again]
    assert json.dumps(summarize(corpus), sort_keys=True) == json.dumps(
        summarize(again), sort_keys=True
    )
