"""End-to-end replay-harness tests over the shipped fixture timeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl
from pneuma_lab.schemas import validate as V

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"

_NON_INTERVENTION_FAMILIES = (
    "global_workspace",
    "recurrent_processing",
    "higher_order_self_model",
    "predictive_processing",
    "attention_schema",
    "valenced_learning",
    "identity_persistence",
    "counterfactual_introspection",
)


@pytest.fixture
def frames() -> list[dict]:
    return load_jsonl(_FIXTURE)


@pytest.fixture
def result(frames):
    return ReplayHarness(ReferencePsyche()).run(frames)


def test_fixture_exists_and_is_valid(frames) -> None:
    assert frames, "fixture is empty"
    for f in frames:
        assert V.iter_errors(f) == [], f"invalid input frame: {f.get('frame_kind')}"


def test_every_output_frame_is_schema_valid(result) -> None:
    assert result.output_frames
    for f in result.output_frames:
        assert V.iter_errors(f) == [], f"invalid output frame {f.get('frame_kind')}"


def test_reaches_level_3(result) -> None:
    assert result.evidence_frame["evidence_level"] == 3


def test_level_is_hard_capped_below_4(result) -> None:
    ev = result.evidence_frame
    # Even on a maximally healthy run, Phase 1 cannot exceed Level 3.
    assert ev["evidence_level"] <= 3
    joined = " ".join(ev["missing_requirements"])
    assert "intervention_evidence" in joined
    assert "null_condition_evidence" in joined
    assert ev["intervention_tests"]["results"] == []
    assert ev["intervention_tests"]["integrity_ok"] is False


def test_all_nine_families_have_records_eight_evidenced(result) -> None:
    fams = result.evidence_frame["indicator_families"]
    assert set(fams) >= set(_NON_INTERVENTION_FAMILIES) | {
        "causal_intervention_robustness"
    }
    for name in _NON_INTERVENTION_FAMILIES:
        assert fams[name]["status"] == "evidenced", name
    # The ninth family must stay honestly unevidenced in Phase 1.
    assert fams["causal_intervention_robustness"]["status"] == "architecture_only"


def test_causal_path_spans_event_to_behavior_with_linked_hashes(result) -> None:
    traces = [o.causal_trace for o in result.tick_outputs]
    # At least one trace's path spans event → … → behavior.
    spanned = False
    for t in traces:
        stages = [s["stage"] for s in t["causal_path"]]
        if stages[0] == "event" and stages[-1] == "behavior":
            spanned = True
    assert spanned, "no causal_path spans event→behavior"
    # The state-hash chain links tick to tick (recurrence + auditability).
    for prev, cur in zip(traces, traces[1:]):
        assert prev["new_state_hash"] == cur["previous_state_hash"]
        assert cur["previous_state_hash"] != cur["new_state_hash"]


def test_self_reports_are_grounded(result) -> None:
    ev = result.evidence_frame
    assert ev["roleplay_confabulation_risk"] == 0.0
    state_hashes = {o.psyche_state["state_hash"] for o in result.tick_outputs}
    trace_ids = {o.causal_trace["trace_id"] for o in result.tick_outputs}
    for o in result.tick_outputs:
        r = o.grounded_self_report
        assert r["affect_state_hash"] in state_hashes
        assert r["causal_trace_id"] in trace_ids
        # It never claims phenomenal consciousness; the forbidden claim is filtered.
        assert r["filtered_forbidden_claims"]


def test_instinct_escalates_and_stays_silent_when_healthy(result) -> None:
    per_tick = [len(o.instinct_signals) for o in result.tick_outputs]
    # The final recovery tick (verdict pass, no scar, no error) fires nothing.
    assert per_tick[-1] == 0
    match_types = [
        s["match_type"] for o in result.tick_outputs for s in o.instinct_signals
    ]
    assert "near_duplicate" in match_types  # scar match escalated
