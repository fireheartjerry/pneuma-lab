"""Level-4 scoring gate: reachable only when interventions execute AND pass; hard
refusal otherwise; never exceeds Level 4."""

from __future__ import annotations

from pathlib import Path

from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "interventions"
_PHASE1 = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"


def test_level4_reached_when_intervention_passes():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    ev = res.evidence_frame
    assert ev["evidence_level"] == 4
    fam = ev["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] == "intervention_backed"
    assert fam["score"] == 0.85
    assert ev["intervention_tests"]["passed"] == ["clamp-tension"]
    assert ev["intervention_tests"]["failed"] == []
    assert ev["audit_status"] == "internally_audited"


def test_level_never_exceeds_4():
    for name in ("clamp_tension", "ablate_scar_graph", "disable_workspace"):
        res = PairedReplayRunner().run(load_jsonl(_FIX / f"{name}.jsonl"))
        assert res.evidence_frame["evidence_level"] <= 4


def test_l4_evidence_frame_lists_l5_gaps_not_l4_gaps():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    missing = " ".join(res.evidence_frame["missing_requirements"])
    assert "adversarial_robustness" in missing  # L5 requirement
    assert "external_audit" in missing  # remaining audit gap up to L5
    assert "no InterventionFrame was executed" not in missing  # L4 gate is satisfied


def test_hard_refusal_when_intervention_fails():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "failing_hypothesis.jsonl"))
    ev = res.evidence_frame
    assert ev["intervention_tests"]["failed"] == ["bad-hyp"]
    assert ev["evidence_level"] <= 3
    fam = ev["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] != "intervention_backed"
    assert fam["status"] == "attempted"
    joined = " ".join(ev["missing_requirements"])
    assert "intervention_tests_failed" in joined


def test_hard_refusal_when_restore_only():
    """A no-op restore passes its no_change test but perturbs nothing ⇒ not Level 4."""
    res = PairedReplayRunner().run(load_jsonl(_FIX / "restore_null.jsonl"))
    assert res.evidence_frame["evidence_level"] == 3


def test_hard_refusal_when_no_interventions():
    """The Phase-1 fixture (no intervention frames) still tops out at Level 3."""
    res = ReplayHarness(ReferencePsyche()).run(load_jsonl(_PHASE1))
    ev = res.evidence_frame
    assert ev["evidence_level"] == 3
    assert ev["intervention_tests"] == {"passed": [], "failed": []}
    assert ev["audit_status"] == "self_reported"
    fam = ev["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] == "architecture_only"
