"""SubjectEvidenceCampaign through the PROMOTABLE, certified paired-runner path.

Unlike the plain campaign (which used the non-promotable shortcut), this runs each
paired slice through PairedReplayRunner with a CERTIFIED factory, surfacing the
runner-issued provenance (subject_factory_eligible + runner_verified + arm digests)
and the scorer's diagnostic level. It stays conservative: the headline evidence is
<= L1 and overall.claim is always 'no_level_claim'. Eligibility is real; promotion
remains blocked by the scorer's family gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.nervous_system import scar_memory as sm
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.nervous_system.campaign_report import write_campaign
from pneuma_lab.nervous_system.certified_subject import certify_baseline_subject
from pneuma_lab.nervous_system.subject_runtime import run_subject

_FIXTURES = (
    Path(__file__).resolve().parents[3] / "fixtures" / "nervous_system" / "subject"
)
_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_OUT = _REPO / "build" / "evidence_campaigns" / "certified-subject-v0"
_FAMILIES = (
    "global_workspace",
    "valenced_learning",
    "identity_persistence",
    "higher_order_self_model",
)
_SEED = {"m1:regress": 0.5}
_TS = "2026-07-10T00:00:00Z"
_PROMOTION_BLOCKED_BY = [
    "family_unevidenced: higher_order_self_model",
    "family_unevidenced: predictive_processing",
    "family_unevidenced: attention_schema",
    "toy_fixtures",
    "no_external_audit",
]


def _frames(name):
    return [
        json.loads(x)
        for x in (_FIXTURES / name).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def _evidence(effect, null_holds):
    return nse.subject_evidence_frame(
        ablation_result={"direction_ok": effect, "null_holds": null_holds},
        families_exercised=_FAMILIES,
        run_id="subj",
        timestamp=_TS,
    )


def _readiness(effect, null_holds):
    return "compatible_harness_evidence" if (effect and null_holds) else "not_observed"


def _last(rr, attr):
    outs = rr.tick_outputs
    return getattr(outs[-1], attr) if outs else {}


def _provenance(res, intervention_refs):
    p = res.evidence_frame["paired_replay_provenance"]
    return {
        "subject_factory_eligible": p["subject_factory_eligible"],
        "runner_certified": p["status"] == "runner_verified",
        "provenance_status": p["status"],
        "subject_factory": p["subject_factory"],
        "input_frames_sha256": p["input_frames_sha256"],
        "arm_output_sha256": p["arm_output_sha256"],
        "ordinal_invariant": p["ordinal_invariant"],
        "intervention_refs": intervention_refs,
    }


def _scorer_diagnostic(res):
    p = res.evidence_frame["paired_replay_provenance"]
    return {
        "internal_harness_evidence_level": res.evidence_frame["evidence_level"],
        "provenance_status": p["status"],
        "real_subject_claim_status": res.evidence_frame["real_subject_claim_status"],
        "note": (
            "internal-harness methodology diagnostic; NOT a real-subject claim; "
            "capped below Level 4 by unevidenced families"
        ),
    }


def _paired_slice(slice_id, kind, fixture, hypothesis, factory, effect_fn):
    frames = _frames(fixture)
    res = PairedReplayRunner(psyche_factory=factory).run(frames)
    winner_c = _last(res.control, "workspace_broadcast").get("winning_faculty")
    winner_t = _last(res.treated, "workspace_broadcast").get("winning_faculty")
    winner_n = _last(res.null, "workspace_broadcast").get("winning_faculty")
    verif_c = _last(res.control, "control_pressure")["pressures"]["verification"]
    verif_t = _last(res.treated, "control_pressure")["pressures"]["verification"]
    verif_n = _last(res.null, "control_pressure")["pressures"]["verification"]
    null_holds = abs(round(verif_n - verif_c, 6)) <= 1e-6 and winner_n == winner_c
    intervention_refs = [t["experiment_id"] for t in res.report.get("tests", [])]
    ctx = {
        "winner_control": winner_c,
        "winner_treated": winner_t,
        "verif_control": verif_c,
        "verif_treated": verif_t,
        "state_control": _last(res.control, "psyche_state"),
        "state_treated": _last(res.treated, "psyche_state"),
        "report_control": _last(res.control, "grounded_self_report"),
        "report_treated": _last(res.treated, "grounded_self_report"),
    }
    effect = effect_fn(ctx)
    observed = {
        "control": {"winner": winner_c, "verification": verif_c},
        "treated": {"winner": winner_t, "verification": verif_t},
        "null": {"winner": winner_n, "verification": verif_n},
        "null_holds": null_holds,
    }
    return {
        "id": slice_id,
        "kind": kind,
        "hypothesis": hypothesis,
        "effect_observed": effect,
        "readiness": _readiness(effect, null_holds),
        "observed": observed,
        "provenance": _provenance(res, intervention_refs),
        "scorer_diagnostic": _scorer_diagnostic(res),
        "evidence_frame": _evidence(effect, null_holds),
    }, ctx


def _slice_persistence(work_dir, factory):
    store = Path(work_dir) / "persist_store.json"
    if store.exists():
        store.unlink()
    b1 = run_subject(_frames("base.jsonl"), scar_store_path=store)
    scars_after_run1 = sm.load(store)
    b2 = run_subject(_frames("base.jsonl"), scar_store_path=store)
    run1_hash = b1[0]["psyche_state"]["state_hash"]
    run2_hash = b2[0]["psyche_state"]["state_hash"]
    run1 = b1[0]["control_pressure"]["pressures"]["verification"]
    run2 = b2[0]["control_pressure"]["pressures"]["verification"]
    effect = run2 != run1
    return {
        "id": "l2_persistence",
        "kind": "persistence",
        "hypothesis": "a stored scar retrieved next run changes workspace/pressure",
        "effect_observed": effect,
        "readiness": _readiness(effect, True),
        "observed": {
            "run1_tick0_verification": run1,
            "run2_tick0_verification": run2,
            "run1_winner": b1[0]["workspace_broadcast"]["winning_faculty"],
            "run2_winner": b2[0]["workspace_broadcast"]["winning_faculty"],
        },
        "provenance": {
            "runner_certified": False,
            "state_persistence_refs": {
                "scars_after_run1": scars_after_run1,
                "run1_tick0_state_hash": run1_hash,
                "run2_tick0_state_hash": run2_hash,
            },
            "note": "cross-run persistence, not a single paired replay",
        },
        "scorer_diagnostic": {
            "internal_harness_evidence_level": None,
            "note": "persistence is cross-run; not scored by a single paired replay",
        },
        "evidence_frame": _evidence(effect, True),
    }


def run_certified_campaign(*, work_dir):
    factory, cert = certify_baseline_subject(seed_scars=dict(_SEED))
    scar_ablation, _ = _paired_slice(
        "scar_ablation",
        "intervention_null",
        "ablate_scar.jsonl",
        "ablating scar memory flips the winner and drops pressure",
        factory,
        lambda c: (
            c["winner_treated"] != "memory_scar"
            and c["verif_treated"] < c["verif_control"]
        ),
    )
    workspace_disable, _ = _paired_slice(
        "workspace_disable",
        "intervention_null",
        "disable_workspace.jsonl",
        "disabling the workspace suppresses broadcast and zeroes pressure",
        factory,
        lambda c: c["verif_treated"] == 0.0 and c["winner_treated"] == "none",
    )
    certainty_clamp, _ = _paired_slice(
        "certainty_clamp",
        "intervention_null",
        "clamp_certainty.jsonl",
        "clamping certainty changes internal state / self-report",
        factory,
        lambda c: (
            c["state_treated"].get("state_hash") != c["state_control"].get("state_hash")
        ),
    )
    grounded, gctx = _paired_slice(
        "grounded_self_report",
        "grounded_self_report",
        "ablate_scar.jsonl",
        "self-report references state/winner/trace and changes under perturbation",
        factory,
        lambda c: (
            c["report_control"].get("affect_state_hash")
            == c["state_control"].get("state_hash")
            and c["winner_control"] in (c["report_control"].get("report_text") or "")
            and bool(c["report_control"].get("causal_trace_id"))
            and c["report_control"] != c["report_treated"]
        ),
    )
    grounded["observed"]["references_state_hash"] = gctx["report_control"].get(
        "affect_state_hash"
    ) == gctx["state_control"].get("state_hash")
    grounded["observed"]["report_changed_under_perturbation"] = (
        gctx["report_control"] != gctx["report_treated"]
    )

    slices = [
        _slice_persistence(work_dir, factory),
        scar_ablation,
        workspace_disable,
        certainty_clamp,
        grounded,
    ]
    summary = {
        "manifest_kind": "subject_evidence_campaign",
        "schema_version": "0.1.0",
        "campaign_id": "certified-subject-evidence-campaign-v0",
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
            "certified": bool(cert["passed"]),
            "subject_factory_eligible": bool(cert["passed"]),
            "posture": "compatible_harness_evidence_only",
            "promotion_blocked_by": list(_PROMOTION_BLOCKED_BY),
            "note": (
                "Subject factory eligibility is REAL (probe-certified) and the paired "
                "slices ran on the runner_verified promotable path, but Level-2/3/4 "
                "promotion remains blocked by the scorer's family-completeness gate. "
                "No level is claimed."
            ),
        },
    }
    from pneuma_lab.schemas import validate

    validate.validate_campaign(summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="pneuma_lab.nervous_system.certified_campaign"
    )
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args(argv)
    out = Path(args.out)
    summary = run_certified_campaign(work_dir=out / "_work")
    write_campaign(summary, out)
    print(f"wrote certified campaign artifacts to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
