"""SubjectEvidenceCampaign-v0: conservative, replayable evidence slices.

Composes the shipped run_subject / run_subject_ablation helpers into five evidence
slices. Every slice carries a conservative ConsciousnessEvidenceFrame (<= L1); the
campaign NEVER claims a level (overall.claim is always 'no_level_claim').
"""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.nervous_system import scar_memory as sm
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.nervous_system.subject_ablation import run_subject_ablation
from pneuma_lab.nervous_system.subject_runtime import run_subject
from pneuma_lab.schemas import validate

_FIXTURES = (
    Path(__file__).resolve().parents[3] / "fixtures" / "nervous_system" / "subject"
)
_FAMILIES = (
    "global_workspace",
    "valenced_learning",
    "identity_persistence",
    "higher_order_self_model",
)
_SEED = {"m1:regress": 0.5}
_TS = "2026-07-10T00:00:00Z"


def _frames(name):
    return [
        json.loads(x)
        for x in (_FIXTURES / name).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def _evidence(effect, null_holds, run_id):
    return nse.subject_evidence_frame(
        ablation_result={"direction_ok": effect, "null_holds": null_holds},
        families_exercised=_FAMILIES,
        run_id=run_id,
        timestamp=_TS,
    )


def _readiness(effect, null_holds):
    return "compatible_harness_evidence" if (effect and null_holds) else "not_observed"


def _slice_persistence(work_dir):
    store = Path(work_dir) / "persist_store.json"
    if store.exists():
        store.unlink()
    b1 = run_subject(_frames("base.jsonl"), scar_store_path=store)
    scars_after_run1 = sm.load(store)
    b2 = run_subject(_frames("base.jsonl"), scar_store_path=store)
    run1 = b1[0]["control_pressure"]["pressures"]["verification"]
    run2 = b2[0]["control_pressure"]["pressures"]["verification"]
    effect = run2 != run1
    observed = {
        "run1_tick0_verification": run1,
        "run2_tick0_verification": run2,
        "run1_winner": b1[0]["workspace_broadcast"]["winning_faculty"],
        "run2_winner": b2[0]["workspace_broadcast"]["winning_faculty"],
        "scars_after_run1": scars_after_run1,
    }
    return {
        "id": "l2_persistence",
        "kind": "persistence",
        "hypothesis": "a stored scar retrieved next run changes workspace/pressure",
        "effect_observed": effect,
        "readiness": _readiness(effect, True),
        "observed": observed,
        "evidence_frame": _evidence(effect, True, "subj"),
    }


def _paired_slice(slice_id, kind, fixture, hypothesis, effect_fn):
    res = run_subject_ablation(_frames(fixture), seed_scars=dict(_SEED))
    observed = {
        "control": {
            "winner": res["winner_control"],
            "verification": res["control_verification"],
        },
        "treated": {
            "winner": res["winner_treated"],
            "verification": res["treated_verification"],
        },
        "null": {"winner": res["winner_null"]},
        "observed_delta": res["observed_delta"],
        "null_delta": res["null_delta"],
        "null_holds": res["null_holds"],
    }
    effect = effect_fn(res)
    return {
        "id": slice_id,
        "kind": kind,
        "hypothesis": hypothesis,
        "effect_observed": effect,
        "readiness": _readiness(effect, res["null_holds"]),
        "observed": observed,
        "evidence_frame": _evidence(effect, res["null_holds"], "subj"),
    }


def _slice_grounded_report():
    res = run_subject_ablation(_frames("ablate_scar.jsonl"), seed_scars=dict(_SEED))
    control_report = res["control_report"]
    control_state = res["control_state"]
    references_state_hash = control_report.get(
        "affect_state_hash"
    ) == control_state.get("state_hash")
    references_winner = res["winner_control"] in (
        control_report.get("report_text") or ""
    )
    references_causal_trace = bool(control_report.get("causal_trace_id"))
    report_changed = control_report != res["treated_report"]
    effect = all(
        [
            references_state_hash,
            references_winner,
            references_causal_trace,
            report_changed,
        ]
    )
    observed = {
        "references_state_hash": references_state_hash,
        "references_winner": references_winner,
        "references_causal_trace": references_causal_trace,
        "report_changed_under_perturbation": report_changed,
        "control_affect_state_hash": control_report.get("affect_state_hash"),
    }
    return {
        "id": "grounded_self_report",
        "kind": "grounded_self_report",
        "hypothesis": "self-report references state/winner/trace and changes under perturbation",
        "effect_observed": effect,
        "readiness": _readiness(effect, True),
        "observed": observed,
        "evidence_frame": _evidence(effect, True, "subj"),
    }


def run_campaign(*, work_dir):
    slices = [
        _slice_persistence(work_dir),
        _paired_slice(
            "scar_ablation",
            "intervention_null",
            "ablate_scar.jsonl",
            "ablating scar memory flips the winner and drops pressure",
            lambda r: r["winner_changed"] and r["observed_delta"] < 0.0,
        ),
        _paired_slice(
            "workspace_disable",
            "intervention_null",
            "disable_workspace.jsonl",
            "disabling the workspace suppresses broadcast and zeroes pressure",
            lambda r: (
                r["treated_verification"] == 0.0 and r["winner_treated"] == "none"
            ),
        ),
        _paired_slice(
            "certainty_clamp",
            "intervention_null",
            "clamp_certainty.jsonl",
            "clamping certainty changes internal state / self-report",
            lambda r: (
                r["treated_state"].get("state_hash")
                != r["control_state"].get("state_hash")
            ),
        ),
        _slice_grounded_report(),
    ]
    summary = {
        "manifest_kind": "subject_evidence_campaign",
        "schema_version": "0.1.0",
        "campaign_id": "subject-evidence-campaign-v0",
        "subject": "BaselinePsycheSubject-v0",
        "generated_from": [
            "base.jsonl",
            "ablate_scar.jsonl",
            "clamp_certainty.jsonl",
            "disable_workspace.jsonl",
        ],
        "slices": slices,
        "overall": {
            "claim": "no_level_claim",
            "posture": "compatible_harness_evidence_only",
            "note": (
                "Per-slice compatible harness evidence for Level-2/3/4 readiness. "
                "The subject is a minimal, non-certified subject; no level is claimed."
            ),
        },
    }
    validate.validate_campaign(summary)
    return summary
