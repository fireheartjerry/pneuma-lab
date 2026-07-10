"""Tests for SubjectEvidenceCampaign-v0: conservative replayable evidence campaigns.

Covers the subject refinement (interventions visible in state/report), the campaign
summary schema, the five evidence slices, deterministic schema-valid artifacts, and
the conservative (no-overclaim) posture.
"""

import json
from pathlib import Path

from pneuma_lab.schemas import validate

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "fixtures" / "nervous_system" / "subject"


def _frames(name):
    return [
        json.loads(x)
        for x in (FIX / name).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


# --------------------------------------------------------------------------- #
# Task 1: interventions visible in subject state + self-report                #
# --------------------------------------------------------------------------- #
def test_certainty_clamp_changes_state_and_report_but_not_control():
    from pneuma_lab.nervous_system.subject_ablation import run_subject_ablation

    res = run_subject_ablation(
        _frames("clamp_certainty.jsonl"), seed_scars={"m1:regress": 0.5}
    )
    assert res["treated_state"]["state_hash"] != res["control_state"]["state_hash"]
    assert (
        res["treated_report"]["reported_measurements"]["affect_certainty"]
        != res["control_report"]["reported_measurements"]["affect_certainty"]
    )
    assert res["null_holds"] is True
    assert (
        res["control_report"]["affect_state_hash"] == res["control_state"]["state_hash"]
    )


# --------------------------------------------------------------------------- #
# Task 2: campaign summary schema + validate_campaign                          #
# --------------------------------------------------------------------------- #
def _min_families():
    fams = (
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
    return {
        f: {
            "score": 0.0,
            "status": "absent",
            "ticks_exercised": 0,
            "note": "",
            "supporting_refs": [],
            "refuting_refs": [],
        }
        for f in fams
    }


def test_campaign_schema_registered_and_validates():
    from pneuma_lab import schemas

    all_schemas = schemas.load_all_schemas()
    assert "subject-evidence-campaign.schema.json" in all_schemas
    summary = {
        "manifest_kind": "subject_evidence_campaign",
        "schema_version": "0.1.0",
        "campaign_id": "subject-evidence-campaign-v0",
        "subject": "BaselinePsycheSubject-v0",
        "generated_from": ["base.jsonl"],
        "slices": [
            {
                "id": "l2_persistence",
                "kind": "persistence",
                "hypothesis": "stored scar changes later behaviour",
                "effect_observed": True,
                "readiness": "compatible_harness_evidence",
                "observed": {"run1": 0.46, "run2": 0.76},
                "evidence_frame": {
                    "schema_version": "0.2.0",
                    "frame_kind": "consciousness_evidence",
                    "timestamp": "2026-07-10T00:00:00Z",
                    "run_id": "subj",
                    "evaluation_id": "e",
                    "evaluation_scope": "internal_harness",
                    "real_subject_claim_status": "not_evaluated",
                    "indicator_families": _min_families(),
                    "evidence_level": 1,
                    "missing_requirements": [],
                    "strongest_positive_evidence": None,
                    "strongest_negative_evidence": None,
                    "audit_status": "self_reported",
                    "roleplay_confabulation_risk": 0.1,
                    "intervention_tests": {
                        "results": [],
                        "executed_count": 0,
                        "reported_total": 0,
                        "integrity_ok": False,
                        "integrity_errors": [],
                        "genuine_perturbation": False,
                    },
                    "paired_replay_provenance": {
                        "status": "uncertified_subject",
                        "runner": None,
                        "subject_factory": None,
                        "subject_factory_eligible": False,
                        "input_frames_sha256": None,
                        "arm_output_sha256": {
                            "control": None,
                            "treated": None,
                            "null": None,
                        },
                        "arm_orders": [],
                        "counterbalanced_passes": [],
                        "ordinal_invariant": False,
                    },
                },
            }
        ],
        "overall": {
            "claim": "no_level_claim",
            "posture": "compatible_harness_evidence_only",
        },
    }
    validate.validate_campaign(summary)


# --------------------------------------------------------------------------- #
# Task 3: campaign slices + run_campaign                                       #
# --------------------------------------------------------------------------- #
def test_run_campaign_slices_and_conservatism(tmp_path):
    from pneuma_lab.nervous_system.campaign import run_campaign

    summary = run_campaign(work_dir=tmp_path)
    validate.validate_campaign(summary)
    by_id = {s["id"]: s for s in summary["slices"]}
    assert set(by_id) == {
        "l2_persistence",
        "scar_ablation",
        "workspace_disable",
        "certainty_clamp",
        "grounded_self_report",
    }
    assert by_id["l2_persistence"]["effect_observed"] is True
    for sid in ("scar_ablation", "workspace_disable", "certainty_clamp"):
        obs = by_id[sid]["observed"]
        assert {"control", "treated", "null"} <= set(obs)
        assert obs["null_holds"] is True
    assert by_id["scar_ablation"]["observed"]["treated"]["winner"] != "memory_scar"
    assert by_id["workspace_disable"]["observed"]["treated"]["verification"] == 0.0
    gsr = by_id["grounded_self_report"]["observed"]
    assert gsr["references_state_hash"] is True
    assert gsr["references_winner"] is True
    assert gsr["references_causal_trace"] is True
    assert gsr["report_changed_under_perturbation"] is True
    assert summary["overall"]["claim"] == "no_level_claim"
    for s in summary["slices"]:
        f = s["evidence_frame"]
        assert f["evidence_level"] <= 1
        assert f["real_subject_claim_status"] == "not_evaluated"
        assert f["paired_replay_provenance"]["status"] == "uncertified_subject"
        assert (
            f["indicator_families"]["causal_intervention_robustness"]["status"]
            != "intervention_backed"
        )


def test_run_campaign_is_deterministic(tmp_path):
    from pneuma_lab.nervous_system.campaign import run_campaign

    a = run_campaign(work_dir=tmp_path / "a")
    b = run_campaign(work_dir=tmp_path / "b")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# --------------------------------------------------------------------------- #
# Task 4: report writer + CLI                                                  #
# --------------------------------------------------------------------------- #
def test_write_campaign_is_deterministic_and_schema_valid(tmp_path):
    from pneuma_lab.nervous_system.campaign import run_campaign
    from pneuma_lab.nervous_system.campaign_report import write_campaign

    summary = run_campaign(work_dir=tmp_path / "work")
    out1 = write_campaign(summary, tmp_path / "out1")
    out2 = write_campaign(summary, tmp_path / "out2")
    j1 = out1["json"].read_text(encoding="utf-8")
    j2 = out2["json"].read_text(encoding="utf-8")
    assert j1 == j2
    validate.validate_campaign(json.loads(j1))
    assert out1["md"].exists()
    assert "no_level_claim" in out1["md"].read_text(encoding="utf-8")


def test_campaign_cli_writes_artifacts(tmp_path):
    import subprocess
    import sys

    out = tmp_path / "camp"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pneuma_lab.nervous_system.campaign_report",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "summary.json").exists()
    validate.validate_campaign(
        json.loads((out / "summary.json").read_text(encoding="utf-8"))
    )


def test_campaign_causal_trace_refs_resolve():
    from pneuma_lab.nervous_system.subject_runtime import run_subject

    bundle = run_subject(_frames("base.jsonl"))[-1]
    ct = bundle["causal_trace"]
    assert bundle["control_pressure"]["causal_trace_id"] == ct["trace_id"]
    assert bundle["workspace_broadcast"]["broadcast_id"] in ct["emitted_outputs"]
    assert bundle["psyche_state"]["state_hash"] == ct["new_state_hash"]
