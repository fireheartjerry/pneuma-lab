"""Hardening layer: the canonical evidence demo.

Asserts the one-command suite regenerates a valid, deterministic summary that
clearly separates passive Level-3 replay, intervention-backed Level-4 runs, and
Level-3 negative/null controls — and that the README + docs name the Level-5
blockers so internal Level 4 cannot be confused with Level 5 / phenomenal
consciousness.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab import demo

_ROOT = Path(__file__).resolve().parents[1]

# The five real perturbations that must reach Level 4, and the negative controls.
_LEVEL4 = (
    "ablate_scar_graph",
    "boost_curiosity",
    "clamp_tension",
    "disable_workspace",
    "remove_memory_anchors",
)


@pytest.fixture(scope="module")
def suite(tmp_path_factory) -> dict:
    """Run the demo once into a temp dir; return (summary, out_dir)."""
    out = tmp_path_factory.mktemp("canonical")
    summary = demo.run_canonical(out)
    return {"summary": summary, "out": out}


def _by_fixture(summary: dict) -> dict:
    return {r["fixture"]: r for r in summary["fixtures"]}


# -- the demo runs and produces a valid report ------------------------------


def test_canonical_demo_exits_successfully(tmp_path):
    assert demo.main(["-o", str(tmp_path)]) == 0


def test_summary_json_is_valid_json(suite):
    text = (suite["out"] / "summary.json").read_text(encoding="utf-8")
    loaded = json.loads(text)
    assert loaded["report_kind"] == "canonical_evidence_summary"
    assert loaded == suite["summary"]  # returned summary matches the written file


def test_summary_markdown_is_written(suite):
    md = (suite["out"] / "summary.md").read_text(encoding="utf-8")
    assert "Canonical evidence summary" in md
    assert "phenomenal consciousness" in md


def test_every_fixture_artifact_exists(suite):
    out = suite["out"]
    for rec in suite["summary"]["fixtures"]:
        for rel in rec["artifacts"].values():
            assert (out / rel).is_file(), rel


# -- level discipline -------------------------------------------------------


def test_passive_replay_reports_level3(suite):
    rec = _by_fixture(suite["summary"])["sample_run"]
    assert rec["kind"] == "passive"
    assert rec["evidence_level"] == 3
    assert rec["category"] == "passive_level3"


@pytest.mark.parametrize("name", _LEVEL4)
def test_real_interventions_report_level4(suite, name):
    rec = _by_fixture(suite["summary"])[name]
    assert rec["evidence_level"] == 4
    assert rec["category"] == "intervention_backed_level4"
    assert rec["intervention_tests"]["failed"] == []
    assert rec["intervention_tests"]["passed"]
    assert rec["null_condition"] == "passed"
    assert rec["causal_trace_complete"] is True
    assert rec["grounded_self_report_perturbation"] == "changed"


def test_failing_hypothesis_reports_level3(suite):
    rec = _by_fixture(suite["summary"])["failing_hypothesis"]
    assert rec["evidence_level"] == 3
    assert rec["category"] == "failed_hypothesis_level3"
    assert rec["intervention_tests"]["failed"] == ["bad-hyp"]


def test_restore_null_reports_level3(suite):
    rec = _by_fixture(suite["summary"])["restore_null"]
    assert rec["evidence_level"] == 3
    assert rec["category"] == "null_control_level3"
    # A pure restore perturbs nothing: its no_change test passes but nothing changes.
    assert rec["grounded_self_report_perturbation"] == "unchanged"


def test_summary_partitions_the_three_buckets(suite):
    levels = suite["summary"]["levels"]
    assert levels["passive_level3"] == ["sample_run"]
    assert levels["intervention_backed_level4"] == sorted(_LEVEL4)
    assert levels["level3_controls_and_refusals"] == [
        "failing_hypothesis",
        "restore_null",
    ]
    assert suite["summary"]["counts"] == {"fixtures": 8, "level4": 5, "level3": 3}


# -- determinism ------------------------------------------------------------


def test_every_fixture_is_byte_deterministic(suite):
    assert suite["summary"]["byte_deterministic"] is True
    for rec in suite["summary"]["fixtures"]:
        assert rec["byte_deterministic"] is True, rec["fixture"]


def test_repeated_demo_runs_are_byte_identical(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    demo.run_canonical(a)
    demo.run_canonical(b)
    for rel in (
        "summary.json",
        "summary.md",
        "clamp_tension/evidence.json",
        "clamp_tension/intervention_report.json",
        "sample_run/output_frames.jsonl",
    ):
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


# -- the docs make the ceiling unmistakable ---------------------------------


def test_readme_names_the_level5_blockers():
    text = (_ROOT / "README.md").read_text(encoding="utf-8")
    assert "Passive replay: Level 3" in text
    assert "Paired intervention replay: Level 4" in text
    assert "failing_hypothesis" in text
    assert "restore_null" in text
    assert "phenomenal consciousness" in text


def test_docs_page_explains_the_ceiling():
    page = _ROOT / "docs" / "level4-evidence-demo.md"
    assert page.is_file(), "docs/level4-evidence-demo.md is missing"
    text = page.read_text(encoding="utf-8")
    for needle in (
        "control",
        "null",
        "failing_hypothesis",
        "phenomenal consciousness",
        "Level 5",
    ):
        assert needle in text, needle
