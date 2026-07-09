"""Level-4 scoring gate: reachable only when interventions execute AND pass; hard
refusal otherwise; never exceeds Level 4."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from pneuma_lab.evals.evidence import ConsciousnessEvidenceScorer
from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl
from pneuma_lab.schemas import validate as V

_FIX = Path(__file__).resolve().parents[1] / "fixtures" / "interventions"
_PHASE1 = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"


def test_level4_reached_when_intervention_passes():
    res = PairedReplayRunner().run(load_jsonl(_FIX / "clamp_tension.jsonl"))
    ev = res.evidence_frame
    assert ev["evidence_level"] == 4
    assert ev["evaluation_scope"] == "internal_harness"
    assert ev["real_subject_claim_status"] == "not_evaluated"
    assert ev["paired_replay_provenance"]["status"] == "runner_verified"
    assert ev["paired_replay_provenance"]["ordinal_invariant"] is True
    assert len(ev["paired_replay_provenance"]["counterbalanced_passes"]) == 3
    fam = ev["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] == "intervention_backed"
    assert fam["score"] == 0.85
    assert ev["intervention_tests"]["results"] == [
        {"experiment_id": "clamp-tension", "outcome": "passed"}
    ]
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
    assert ev["intervention_tests"]["results"] == [
        {"experiment_id": "bad-hyp", "outcome": "failed"}
    ]
    assert ev["evidence_level"] <= 3
    fam = ev["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] != "intervention_backed"
    assert fam["status"] == "attempted"
    joined = " ".join(ev["missing_requirements"])
    assert "intervention_tests_failed" in joined


def test_hard_refusal_when_restore_only():
    """A no-op restore passes its no_change test but perturbs nothing ⇒ not Level 4."""
    res = PairedReplayRunner().run(load_jsonl(_FIX / "restore_null.jsonl"))
    ev = res.evidence_frame
    assert ev["evidence_level"] == 3
    assert ev["audit_status"] == "self_reported"
    assert ev["intervention_tests"]["integrity_ok"] is True
    assert ev["paired_replay_provenance"]["status"] == "runner_verified"
    assert ev["intervention_tests"]["genuine_perturbation"] is False
    family = ev["indicator_families"]["causal_intervention_robustness"]
    assert family["status"] == "architecture_only"
    assert family["score"] == 0.2


def test_hard_refusal_when_no_interventions():
    """The Phase-1 fixture (no intervention frames) still tops out at Level 3."""
    res = ReplayHarness(ReferencePsyche()).run(load_jsonl(_PHASE1))
    ev = res.evidence_frame
    assert ev["evidence_level"] == 3
    assert ev["intervention_tests"]["results"] == []
    assert ev["intervention_tests"]["integrity_ok"] is False
    assert ev["audit_status"] == "self_reported"
    fam = ev["indicator_families"]["causal_intervention_robustness"]
    assert fam["status"] == "architecture_only"


def test_scorer_refuses_caller_fabricated_intervention_pass() -> None:
    """The single-run API has no caller-supplied L4 gate parameters."""
    frames = load_jsonl(_PHASE1)
    baseline = ReplayHarness(ReferencePsyche()).run(frames)

    with pytest.raises(TypeError, match="intervention_tests"):
        ConsciousnessEvidenceScorer().score(
            run_id=frames[0]["run_id"],
            input_frames=frames,
            tick_outputs=baseline.tick_outputs,
            interventions_executed=0,
            memory_readback_present=True,
            intervention_tests={"passed": ["fabricated"], "failed": [], "total": 1},
        )


def test_paired_scorer_recomputes_matching_caller_claims_from_outputs() -> None:
    """Matching IDs cannot pass when treated outputs contain no perturbation."""
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    baseline = ReplayHarness(ReferencePsyche()).run(frames)

    ev, report = ConsciousnessEvidenceScorer().score_paired(
        run_id=frames[0]["run_id"],
        input_frames=frames,
        control_outputs=baseline.tick_outputs,
        treated_outputs=baseline.tick_outputs,
        null_outputs=baseline.tick_outputs,
        interventions_executed=1,
        memory_readback_present=True,
    )

    assert report["summary"]["failed"] == ["clamp-tension"]
    assert ev["evidence_level"] == 3
    assert ev["audit_status"] == "self_reported"
    assert ev["intervention_tests"]["integrity_ok"] is False
    assert ev["paired_replay_provenance"]["status"] == "unverified_raw_outputs"
    assert ev["indicator_families"]["causal_intervention_robustness"][
        "status"
    ] == "attempted"


def test_duplicate_experiment_id_splice_cannot_promote_restore() -> None:
    """A genuine duplicate cannot launder a first-seen restore result into L4."""
    frames = load_jsonl(_FIX / "restore_null.jsonl")
    original_index = next(
        index
        for index, frame in enumerate(frames)
        if frame.get("frame_kind") == "intervention"
    )
    duplicate = deepcopy(frames[original_index])
    duplicate.update(
        {
            "operation": "boost",
            "target": {"subsystem": "drives", "dimension": "curiosity"},
            "value": 0.5,
            "hypothesis": "duplicate curiosity boost increases exploration",
            "expected_behavioral_change": {
                "direction": "increase",
                "target_signal": "control_pressure.exploration",
            },
        }
    )
    frames.insert(original_index + 1, duplicate)

    res = PairedReplayRunner().run(frames)
    ev = res.evidence_frame

    # Duplicate IDs make the tested target ambiguous.  Even though one of the
    # operations changes state, the scorer must refuse to credit its report.
    assert res.report["grounded_self_report_changed_under_perturbation"] is False
    assert ev["evidence_level"] == 3
    assert ev["audit_status"] == "self_reported"
    assert ev["intervention_tests"]["integrity_ok"] is False
    assert any(
        "duplicate registered experiment_id" in error
        for error in ev["intervention_tests"]["integrity_errors"]
    )
    assert ev["indicator_families"]["causal_intervention_robustness"][
        "status"
    ] == "architecture_only"


def test_unattached_intervention_frame_cannot_be_counted_as_evidence() -> None:
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    intervention = deepcopy(
        next(frame for frame in frames if frame.get("frame_kind") == "intervention")
    )
    intervention["experiment_id"] = "stray-clamp"
    first_world = next(
        index for index, frame in enumerate(frames) if frame.get("frame_kind") == "world"
    )
    frames.insert(first_world, intervention)

    res = PairedReplayRunner().run(frames)
    ev = res.evidence_frame

    assert res.treated.interventions_executed == 1
    assert ev["evidence_level"] == 3
    assert ev["audit_status"] == "self_reported"
    assert ev["intervention_tests"]["integrity_ok"] is False
    assert any(
        "not attached to any world tick" in error
        for error in ev["intervention_tests"]["integrity_errors"]
    )


def test_multiple_interventions_cannot_piggyback_on_one_joint_treated_arm() -> None:
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    original_index = next(
        index
        for index, frame in enumerate(frames)
        if frame.get("frame_kind") == "intervention"
    )
    piggyback = deepcopy(frames[original_index])
    piggyback.update(
        {
            "experiment_id": "ignored-authority",
            "operation": "disable",
            "target": {"subsystem": "authority", "dimension": None},
            "hypothesis": "an inert target appears to inherit the clamp delta",
        }
    )
    frames.insert(original_index + 1, piggyback)

    res = PairedReplayRunner().run(frames)
    ev = res.evidence_frame

    assert res.report["summary"]["passed"] == [
        "clamp-tension",
        "ignored-authority",
    ]
    assert ev["evidence_level"] == 3
    assert ev["audit_status"] == "self_reported"
    assert ev["intervention_tests"]["integrity_ok"] is False
    assert any(
        "multiple interventions require isolated" in error
        for error in ev["intervention_tests"]["integrity_errors"]
    )


def test_schema_rejects_minimal_forged_level4_artifact() -> None:
    forged = {
        "schema_version": "0.2.0",
        "frame_kind": "consciousness_evidence",
        "evaluation_id": "fake",
        "evidence_level": 4,
        "audit_status": "self_reported",
    }

    errors = V.iter_errors(forged)

    assert errors
    assert any("intervention_tests" in error for error in errors)
    assert any("internally_audited" in error for error in errors)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("audit_status",), "self_reported"),
        (("roleplay_confabulation_risk",), 0.3),
        (("intervention_tests", "results"), []),
        (("intervention_tests", "integrity_ok"), False),
        (("intervention_tests", "genuine_perturbation"), False),
        (("paired_replay_provenance", "status"), "unverified_raw_outputs"),
        (("paired_replay_provenance", "ordinal_invariant"), False),
        (("paired_replay_provenance", "arm_orders"), []),
    ],
)
def test_schema_rejects_incoherent_level4_gate_fields(path, value) -> None:
    frame = deepcopy(
        PairedReplayRunner()
        .run(load_jsonl(_FIX / "clamp_tension.jsonl"))
        .evidence_frame
    )
    target = frame
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    assert V.iter_errors(frame)


def test_schema_hard_caps_current_contract_below_level5() -> None:
    frame = deepcopy(
        PairedReplayRunner()
        .run(load_jsonl(_FIX / "clamp_tension.jsonl"))
        .evidence_frame
    )
    frame["evidence_level"] = 5
    frame["audit_status"] = "externally_audited"

    errors = V.iter_errors(frame)

    assert errors
    assert any("greater than the maximum of 4" in error for error in errors)


def test_schema_rejects_non_finite_evidence_numbers() -> None:
    frame = deepcopy(
        PairedReplayRunner()
        .run(load_jsonl(_FIX / "clamp_tension.jsonl"))
        .evidence_frame
    )
    frame["roleplay_confabulation_risk"] = float("nan")

    errors = V.iter_errors(frame)

    assert any("non-finite number" in error for error in errors)


def test_schema_rejects_duplicate_counterbalanced_orders_for_level4() -> None:
    frame = deepcopy(
        PairedReplayRunner()
        .run(load_jsonl(_FIX / "clamp_tension.jsonl"))
        .evidence_frame
    )
    first_order = frame["paired_replay_provenance"]["arm_orders"][0]
    frame["paired_replay_provenance"]["arm_orders"] = [first_order] * 3

    assert V.iter_errors(frame)


def test_nonzero_bounded_change_counts_as_genuine_perturbation() -> None:
    frames = load_jsonl(_FIX / "clamp_tension.jsonl")
    intervention = next(
        frame for frame in frames if frame.get("frame_kind") == "intervention"
    )
    intervention["expected_behavioral_change"] = {
        "direction": "bounded_change",
        "target_signal": "control_pressure.verification",
        "bound": 1.0,
    }

    ev = PairedReplayRunner().run(frames).evidence_frame

    assert ev["evidence_level"] == 4
    assert ev["intervention_tests"]["genuine_perturbation"] is True
