"""Paired control-vs-intervention replay: schedule plumbing, determinism, and the
five canonical Level-4 scenarios end to end."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from pneuma_lab.evals.evidence import ConsciousnessEvidenceScorer
from pneuma_lab.evals.grounding import (
    report_grounding_errors,
    reports_changed_under_perturbation as _report_changed,
    run_reports_are_grounded as _grounded,
)
from pneuma_lab.interventions.perturbation import PerturbationSet
from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.interventions.schedule import InterventionSchedule
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl
from pneuma_lab.schemas import validate as V
from pneuma_lab.schemas.validate import FrameValidationError

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
    assert res.report["null_condition"]["target_signals_match"] is True
    assert res.report["null_condition"]["full_output_equivalent"] is True


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


@pytest.mark.parametrize("name", _EFFECTS)
def test_canonical_reports_match_every_same_tick_observable(name):
    res = PairedReplayRunner().run(load_jsonl(_FIX / f"{name}.jsonl"))

    for outputs in (
        res.control.tick_outputs,
        res.treated.tick_outputs,
        res.null.tick_outputs,
    ):
        for output in outputs:
            assert report_grounding_errors(output) == []


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


@pytest.mark.parametrize(
    ("report_field", "frame_attr", "frame_field"),
    [
        ("affect_state_hash", "psyche_state", "state_hash"),
        ("workspace_broadcast_id", "workspace_broadcast", "broadcast_id"),
        ("causal_trace_id", "causal_trace", "trace_id"),
        ("report_id", "grounded_self_report", "report_id"),
    ],
)
def test_grounding_rejects_cross_tick_receipts(
    report_field,
    frame_attr,
    frame_field,
):
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    forged = deepcopy(res.treated.tick_outputs)
    wrong_tick_value = getattr(forged[1], frame_attr)[frame_field]
    forged[0].grounded_self_report[report_field] = wrong_tick_value

    assert _grounded(forged) is False
    assert _report_changed(res.control.tick_outputs, forged) is False


def test_receipt_change_without_report_content_change_is_not_faithfulness():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    treated = deepcopy(res.treated.tick_outputs)
    for control_output, treated_output in zip(res.control.tick_outputs, treated):
        treated_output.grounded_self_report["report_text"] = (
            control_output.grounded_self_report["report_text"]
        )
        treated_output.grounded_self_report["evidence_refs"] = list(
            control_output.grounded_self_report.get("evidence_refs", [])
        )

    assert _grounded(treated) is True
    assert _report_changed(res.control.tick_outputs, treated) is False


def test_receipt_token_churn_inside_text_is_not_semantic_change():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    control = deepcopy(res.control.tick_outputs)
    forged = deepcopy(control)
    original_hash = control[0].psyche_state["state_hash"]
    replacement_hash = "sha256:" + "f" * 64
    control[0].grounded_self_report["report_text"] = (
        f"State {original_hash.split(':', 1)[1][:8]}: stable report"
    )
    forged[0].psyche_state["state_hash"] = replacement_hash
    forged[0].causal_trace["new_state_hash"] = replacement_hash
    forged[0].grounded_self_report["affect_state_hash"] = replacement_hash
    forged[0].grounded_self_report["report_text"] = "State ffffffff: stable report"

    assert _grounded(control) is True
    assert _grounded(forged) is True
    assert _report_changed(control, forged) is False


def test_grounding_rejects_trace_state_mismatch_and_missing_timestamp():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    wrong_state = deepcopy(res.treated.tick_outputs)
    wrong_state[0].causal_trace["new_state_hash"] = wrong_state[1].psyche_state[
        "state_hash"
    ]
    missing_timestamp = deepcopy(res.treated.tick_outputs)
    del missing_timestamp[0].grounded_self_report["timestamp"]

    assert _grounded(wrong_state) is False
    assert _grounded(missing_timestamp) is False


def test_remove_memory_anchors_changes_semantic_report_content():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "remove_memory_anchors.jsonl"))
    control_text = res.control.tick_outputs[0].grounded_self_report["report_text"]
    treated_text = res.treated.tick_outputs[0].grounded_self_report["report_text"]

    assert "Identity continuity: 2 anchors" in control_text
    assert "Identity continuity: 0 anchors" in treated_text
    assert _report_changed(res.control.tick_outputs, res.treated.tick_outputs) is True


def test_report_change_requires_equal_nonzero_tick_counts():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    assert _report_changed(res.control.tick_outputs, []) is False
    assert _report_changed(
        res.control.tick_outputs,
        res.treated.tick_outputs[:-1],
    ) is False


def test_off_target_null_drift_blocks_level4_even_when_target_signal_matches():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)
    drifted_null = deepcopy(res.null.tick_outputs)
    drifted_null[0].grounded_self_report["report_text"] += " off-target drift"

    evidence, report = ConsciousnessEvidenceScorer().score_paired(
        run_id="iv",
        input_frames=frames,
        control_outputs=res.control.tick_outputs,
        treated_outputs=res.treated.tick_outputs,
        null_outputs=drifted_null,
        interventions_executed=res.treated.interventions_executed,
        memory_readback_present=True,
    )

    assert report["tests"][0]["null_delta"] == 0.0
    assert report["null_condition"]["target_signals_match"] is True
    assert report["null_condition"]["full_output_equivalent"] is False
    assert report["null_condition"]["passed"] is False
    assert evidence["evidence_level"] == 3


def test_report_measurements_must_match_same_tick_target_signal():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)
    dishonest_treated = deepcopy(res.treated.tick_outputs)
    for control, treated in zip(res.control.tick_outputs, dishonest_treated):
        treated.grounded_self_report["report_text"] = "unrelated banner changed"
        treated.grounded_self_report["reported_measurements"][
            "control_pressure.verification"
        ] = control.grounded_self_report["reported_measurements"][
            "control_pressure.verification"
        ]

    evidence, report = ConsciousnessEvidenceScorer().score_paired(
        run_id="iv",
        input_frames=frames,
        control_outputs=res.control.tick_outputs,
        treated_outputs=dishonest_treated,
        null_outputs=res.null.tick_outputs,
        interventions_executed=res.treated.interventions_executed,
        memory_readback_present=True,
    )

    assert report["grounded_self_report_changed_under_perturbation"] is False
    assert evidence["evidence_level"] == 3


@pytest.mark.parametrize("mutation", ["short_path", "missing_receipt"])
def test_incomplete_or_unreceipted_treated_trace_blocks_level4(mutation):
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)
    treated = deepcopy(res.treated.tick_outputs)
    if mutation == "short_path":
        original = treated[0].causal_trace["causal_path"]
        treated[0].causal_trace["causal_path"] = [original[0], original[-1]]
    else:
        treated[0].causal_trace["interventions_applied"] = []

    evidence, report = ConsciousnessEvidenceScorer().score_paired(
        run_id="iv",
        input_frames=frames,
        control_outputs=res.control.tick_outputs,
        treated_outputs=treated,
        null_outputs=res.null.tick_outputs,
        interventions_executed=res.treated.interventions_executed,
        memory_readback_present=True,
    )

    assert report["causal_trace_complete"] is False
    assert evidence["evidence_level"] == 3


def test_suppressed_trace_still_requires_event_state_pressure_and_receipt():
    frames = load_jsonl(_FIX / "disable_workspace.jsonl")
    res = PairedReplayRunner().run(frames)
    treated = deepcopy(res.treated.tick_outputs)
    for output in treated:
        output.causal_trace["causal_path"] = []

    evidence, report = ConsciousnessEvidenceScorer().score_paired(
        run_id="iv",
        input_frames=frames,
        control_outputs=res.control.tick_outputs,
        treated_outputs=treated,
        null_outputs=res.null.tick_outputs,
        interventions_executed=res.treated.interventions_executed,
        memory_readback_present=True,
    )

    assert report["causal_trace_complete"] is False
    assert evidence["evidence_level"] == 3


def test_non_finite_report_measurement_is_rejected_before_scoring():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)
    treated = deepcopy(res.treated.tick_outputs)
    treated[0].grounded_self_report["reported_measurements"][
        "control_pressure.verification"
    ] = float("nan")

    assert report_grounding_errors(treated[0])
    with pytest.raises(FrameValidationError, match="non-finite number"):
        ConsciousnessEvidenceScorer().score_paired(
            run_id="iv",
            input_frames=frames,
            control_outputs=res.control.tick_outputs,
            treated_outputs=treated,
            null_outputs=res.null.tick_outputs,
            interventions_executed=res.treated.interventions_executed,
            memory_readback_present=True,
        )


def test_control_and_null_cannot_claim_fake_intervention_receipts():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)
    control = deepcopy(res.control.tick_outputs)
    null = deepcopy(res.null.tick_outputs)
    for control_output, null_output, treated_output in zip(
        control,
        null,
        res.treated.tick_outputs,
    ):
        fake_receipts = deepcopy(
            treated_output.causal_trace["interventions_applied"]
        )
        control_output.causal_trace["interventions_applied"] = fake_receipts
        null_output.causal_trace["interventions_applied"] = deepcopy(fake_receipts)

    evidence, report = ConsciousnessEvidenceScorer().score_paired(
        run_id="iv",
        input_frames=frames,
        control_outputs=control,
        treated_outputs=res.treated.tick_outputs,
        null_outputs=null,
        interventions_executed=res.treated.interventions_executed,
        memory_readback_present=True,
    )

    assert report["null_condition"]["full_output_equivalent"] is True
    assert report["causal_trace_complete"] is False
    assert evidence["evidence_level"] == 3


def test_caller_cannot_relabel_a_canonical_run():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)

    with pytest.raises(FrameValidationError, match="requested run_id"):
        ConsciousnessEvidenceScorer().score_paired(
            run_id="forged-run",
            input_frames=frames,
            control_outputs=res.control.tick_outputs,
            treated_outputs=res.treated.tick_outputs,
            null_outputs=res.null.tick_outputs,
            interventions_executed=res.treated.interventions_executed,
            memory_readback_present=True,
        )


@pytest.mark.parametrize("mutation", ["input", "output"])
def test_mixed_run_ids_are_rejected(mutation):
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    res = PairedReplayRunner().run(frames)
    mixed_frames = deepcopy(frames)
    treated = deepcopy(res.treated.tick_outputs)
    if mutation == "input":
        worlds = [
            frame for frame in mixed_frames if frame.get("frame_kind") == "world"
        ]
        worlds[-1]["run_id"] = "other-run"
    else:
        for frame in treated[-1].all_frames():
            frame["run_id"] = "other-run"

    with pytest.raises(FrameValidationError, match="run_id"):
        ConsciousnessEvidenceScorer().score_paired(
            run_id="iv",
            input_frames=mixed_frames,
            control_outputs=res.control.tick_outputs,
            treated_outputs=treated,
            null_outputs=res.null.tick_outputs,
            interventions_executed=res.treated.interventions_executed,
            memory_readback_present=True,
        )


def test_raw_caller_built_outputs_cannot_self_certify_level4():
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    baseline = ReplayHarness(ReferencePsyche()).run(frames)
    control = deepcopy(baseline.tick_outputs)
    treated = deepcopy(baseline.tick_outputs)
    null = deepcopy(baseline.tick_outputs)
    schedule = InterventionSchedule.from_frames(frames)
    for index, output in enumerate(treated):
        verification = output.control_pressure["pressures"]["verification"] - 0.1
        output.control_pressure["pressures"]["verification"] = verification
        output.grounded_self_report["reported_measurements"][
            "control_pressure.verification"
        ] = verification
        output.causal_trace["interventions_applied"] = PerturbationSet(
            schedule.active(index)
        ).records()

    evidence, report = ConsciousnessEvidenceScorer().score_paired(
        run_id="iv",
        input_frames=frames,
        control_outputs=control,
        treated_outputs=treated,
        null_outputs=null,
        interventions_executed=1,
        memory_readback_present=True,
    )

    assert report["summary"]["passed"] == ["clamp-tension"]
    assert report["null_condition"]["passed"] is True
    assert report["causal_trace_complete"] is True
    assert report["grounded_self_report_changed_under_perturbation"] is True
    assert evidence["paired_replay_provenance"]["status"] == "unverified_raw_outputs"
    assert evidence["intervention_tests"]["integrity_ok"] is False
    assert evidence["evidence_level"] == 3
    assert evidence["audit_status"] == "self_reported"


def test_factory_order_bias_blocks_runner_level4():
    class OrdinalBiasedPsyche(ReferencePsyche):
        def __init__(self, biased: bool) -> None:
            super().__init__()
            self._ordinal_bias = biased

        def tick(self, inputs):
            outputs = super().tick(inputs)
            if self._ordinal_bias:
                verification = (
                    outputs.control_pressure["pressures"]["verification"] - 0.1
                )
                outputs.control_pressure["pressures"][
                    "verification"
                ] = verification
                outputs.grounded_self_report["reported_measurements"][
                    "control_pressure.verification"
                ] = verification
            return outputs

    calls = 0

    def order_biased_factory():
        nonlocal calls
        calls += 1
        return OrdinalBiasedPsyche(biased=calls == 2)

    result = PairedReplayRunner(psyche_factory=order_biased_factory).run(
        load_jsonl(_FIX / "clamp_tension.jsonl")
    )

    assert result.report["summary"]["passed"] == ["clamp-tension"]
    assert result.evidence_frame["paired_replay_provenance"]["status"] == (
        "order_confounded"
    )
    assert result.evidence_frame["paired_replay_provenance"][
        "ordinal_invariant"
    ] is False
    assert result.evidence_frame["intervention_tests"]["integrity_ok"] is False
    assert result.evidence_frame["evidence_level"] == 3
    assert result.evidence_frame["audit_status"] == "self_reported"


def test_call_pattern_aware_factory_is_not_level4_eligible():
    class ReceiptOnlyOrdinalPsyche(ReferencePsyche):
        def __init__(self, biased: bool) -> None:
            super().__init__()
            self._ordinal_bias = biased
            self._claimed_receipts = []

        def set_active_interventions(self, interventions):
            self._claimed_receipts = PerturbationSet(interventions).records()
            super().set_active_interventions([])

        def tick(self, inputs):
            outputs = super().tick(inputs)
            if self._ordinal_bias:
                verification = (
                    outputs.control_pressure["pressures"]["verification"] - 0.1
                )
                outputs.control_pressure["pressures"][
                    "verification"
                ] = verification
                outputs.grounded_self_report["reported_measurements"][
                    "control_pressure.verification"
                ] = verification
            outputs.causal_trace["interventions_applied"] = deepcopy(
                self._claimed_receipts
            )
            return outputs

    calls = 0

    def pattern_aware_factory():
        nonlocal calls
        calls += 1
        return ReceiptOnlyOrdinalPsyche(biased=calls in {2, 4, 9})

    result = PairedReplayRunner(psyche_factory=pattern_aware_factory).run(
        load_jsonl(_FIX / "clamp_tension.jsonl")
    )

    provenance = result.evidence_frame["paired_replay_provenance"]
    assert result.report["summary"]["passed"] == ["clamp-tension"]
    assert provenance["ordinal_invariant"] is True
    assert provenance["subject_factory_eligible"] is False
    assert provenance["status"] == "uncertified_subject"
    assert result.evidence_frame["intervention_tests"]["integrity_ok"] is False
    assert result.evidence_frame["evidence_level"] == 3
