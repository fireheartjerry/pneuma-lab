"""Deliberately conservative ConsciousnessEvidenceFrame for the shadow slice.

This is Level-1-COMPATIBLE HARNESS EVIDENCE, not an operational Level-1 system
claim and never a Level-3/4 claim. The subject is a risk estimator, not the
integrated psyche, and is never run through the certified PairedReplayRunner.
The frame therefore:

  * caps ``evidence_level`` at 1 (0 when the ablation coupling does not hold),
  * marks eight indicator families ``absent`` and the ninth at most ``attempted``
    (never ``intervention_backed``),
  * records ``paired_replay_provenance.status = "uncertified_subject"``,
  * keeps ``audit_status`` at ``self_reported`` and ``real_subject_claim_status``
    at ``not_evaluated``.
"""

from __future__ import annotations

_FAMILIES = (
    "global_workspace",
    "recurrent_processing",
    "higher_order_self_model",
    "predictive_processing",
    "attention_schema",
    "valenced_learning",
    "identity_persistence",
    "counterfactual_introspection",
    "causal_intervention_robustness",
)

_MISSING = [
    "certified paired control/treated/null runner over the subject",
    "integrated, persistent psyche subject (not a single model signal)",
    "grounded self-report that changes faithfully under perturbation",
    "a real, non-toy evaluated subject",
    "longitudinal, adversarial, and external audit",
]


def _family(status, score, note):
    return {
        "score": score,
        "status": status,
        "ticks_exercised": 0,
        "note": note,
        "supporting_refs": [],
        "refuting_refs": [],
    }


def shadow_evidence_frame(*, ablation_result, run_id, timestamp):
    """Build the conservative evidence frame for one shadow ablation slice."""
    coupled = bool(ablation_result.get("direction_ok")) and bool(
        ablation_result.get("null_holds")
    )
    level = 1 if coupled else 0
    robustness_status = "attempted" if coupled else "absent"
    robustness_score = 0.3 if coupled else 0.0
    note = (
        "Level-1-compatible harness evidence: one model signal modulates one "
        "bounded advisory pressure and the effect vanishes under ablation. NOT an "
        "operational Level-1 system claim; NOT a Level-3/4 claim."
    )
    families = {
        name: _family("absent", 0.0, "not exercised in shadow slice")
        for name in _FAMILIES
    }
    families["causal_intervention_robustness"] = _family(
        robustness_status, robustness_score, note
    )
    return {
        "schema_version": "0.2.0",
        "frame_kind": "consciousness_evidence",
        "timestamp": timestamp,
        "run_id": run_id,
        "evaluation_id": f"shadow_evidence:{run_id}",
        "evaluation_scope": "internal_harness",
        "real_subject_claim_status": "not_evaluated",
        "indicator_families": families,
        "evidence_level": level,
        "missing_requirements": list(_MISSING),
        "strongest_positive_evidence": (
            "risk-signal ablation drops the verification-pressure candidate; null holds"
            if coupled
            else None
        ),
        "strongest_negative_evidence": (
            "single non-integrated model signal; no certified paired runner; no real subject"
        ),
        "audit_status": "self_reported",
        "roleplay_confabulation_risk": 0.1,
        "intervention_tests": {
            "results": [],
            "executed_count": 0,
            "reported_total": 0,
            "integrity_ok": False,
            "integrity_errors": [
                "shadow slice is not a certified paired-runner intervention"
            ],
            "genuine_perturbation": False,
        },
        "paired_replay_provenance": {
            "status": "uncertified_subject",
            "runner": None,
            "subject_factory": None,
            "subject_factory_eligible": False,
            "input_frames_sha256": None,
            "arm_output_sha256": {"control": None, "treated": None, "null": None},
            "arm_orders": [],
            "counterbalanced_passes": [],
            "ordinal_invariant": False,
        },
    }
