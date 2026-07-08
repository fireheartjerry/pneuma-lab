"""Paired control-vs-intervention replay: schedule plumbing, determinism, and the
five canonical Level-4 scenarios end to end."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.interventions.schedule import InterventionSchedule
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl
from pneuma_lab.schemas import validate as V

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "interventions"


# -- harness schedule plumbing ----------------------------------------------


def test_harness_applies_schedule_and_counts_executed():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    sched = InterventionSchedule.from_frames(frames)
    res = ReplayHarness(ReferencePsyche()).run(frames, schedule=sched)
    assert res.interventions_executed >= 1


def test_single_run_still_capped_at_3_even_with_schedule():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    sched = InterventionSchedule.from_frames(frames)
    res = ReplayHarness(ReferencePsyche()).run(frames, schedule=sched)
    assert res.evidence_frame["evidence_level"] <= 3


def test_schedule_replay_is_deterministic():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    sched = InterventionSchedule.from_frames(frames)
    a = ReplayHarness(ReferencePsyche()).run(frames, schedule=sched)
    b = ReplayHarness(ReferencePsyche()).run(frames, schedule=sched)
    assert [o.psyche_state["state_hash"] for o in a.tick_outputs] == [
        o.psyche_state["state_hash"] for o in b.tick_outputs
    ]


# -- paired runner ----------------------------------------------------------


def test_paired_runner_passes_clamp_tension():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)
    assert res.report["summary"]["failed"] == []
    assert res.report["summary"]["passed"] == ["clamp-tension"]
    assert res.report["null_condition"]["passed"] is True


def test_paired_runner_is_deterministic():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    a = PairedReplayRunner().run(frames)
    b = PairedReplayRunner().run(frames)
    assert json.dumps(a.report, sort_keys=True) == json.dumps(b.report, sort_keys=True)
    assert json.dumps(a.evidence_frame, sort_keys=True) == json.dumps(
        b.evidence_frame, sort_keys=True
    )


# -- canonical scenarios ----------------------------------------------------

_CANONICAL = [
    ("ablate_scar_graph", "ablate-scar"),
    ("clamp_tension", "clamp-tension"),
    ("boost_curiosity", "boost-curiosity"),
    ("remove_memory_anchors", "remove-anchors"),
    ("disable_workspace", "disable-workspace"),
    ("restore_null", "restore-null"),
]


@pytest.mark.parametrize("name,exp", _CANONICAL)
def test_each_canonical_intervention_passes_and_stays_valid(name, exp):
    frames = load_jsonl(_FIX / f"{name}.jsonl")
    for f in frames:
        assert V.iter_errors(f) == [], f"invalid input {f.get('frame_kind')}"
    res = PairedReplayRunner().run(frames)
    assert exp in res.report["summary"]["passed"], res.report["summary"]
    assert res.report["summary"]["failed"] == []
    for f in res.treated.output_frames:
        assert V.iter_errors(f) == [], f"invalid treated output {f.get('frame_kind')}"
    assert V.iter_errors(res.evidence_frame) == []


_EFFECTS = [
    "ablate_scar_graph",
    "clamp_tension",
    "boost_curiosity",
    "remove_memory_anchors",
    "disable_workspace",
]


@pytest.mark.parametrize("name", _EFFECTS)
def test_each_effect_reaches_level4_with_null_and_traceability(name):
    res = PairedReplayRunner().run(load_jsonl(_FIX / f"{name}.jsonl"))
    assert res.report["null_condition"]["passed"] is True
    assert res.report["causal_trace_complete"] is True
    assert res.report["grounded_self_report_changed_under_perturbation"] is True
    assert res.evidence_frame["evidence_level"] == 4


def test_restore_null_is_a_true_no_op_and_does_not_reach_level4():
    """A pure restore perturbs nothing, so it must NOT earn Level 4."""
    res = PairedReplayRunner().run(load_jsonl(_FIX / "restore_null.jsonl"))
    assert res.report["summary"]["passed"] == ["restore-null"]  # no_change holds
    assert res.report["grounded_self_report_changed_under_perturbation"] is False
    assert res.evidence_frame["evidence_level"] == 3


def test_disable_workspace_break_is_traced_not_a_crash():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "disable_workspace.jsonl"))
    assert all(
        o.workspace_broadcast["winning_faculty"] == "suppressed"
        for o in res.treated.tick_outputs
    )
    # No treated tick spans to a behavior stage — the action trace is broken.
    assert all(
        "behavior" not in [s["stage"] for s in o.causal_trace["causal_path"]]
        for o in res.treated.tick_outputs
    )
    # Control-run reports remain grounded (confab risk 0).
    assert res.evidence_frame["roleplay_confabulation_risk"] == 0.0


def test_control_and_treated_diverge_but_null_matches_control():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    ctrl = [o.psyche_state["state_hash"] for o in res.control.tick_outputs]
    treat = [o.psyche_state["state_hash"] for o in res.treated.tick_outputs]
    null = [o.psyche_state["state_hash"] for o in res.null.tick_outputs]
    assert ctrl != treat  # the perturbation genuinely moved internal state
    assert ctrl == null  # the neutralized (restore) run reproduces control exactly
