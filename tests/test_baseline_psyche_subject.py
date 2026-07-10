"""Tests for BaselinePsycheSubject-v0: the first integrated replayable psyche subject.

Covers the bundle schema extension, persistent scar memory, the 3-candidate
workspace, the subject tick loop (via the real ReplayHarness), deterministic
schema-valid bundles + persistence, conservative evidence, and the
intervention/null tests via the existing paired runner.
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
# Task 1: output bundle carries psyche_state + workspace_broadcast            #
# --------------------------------------------------------------------------- #
def test_output_bundle_accepts_psyche_and_workspace_members():
    bundle = {
        "schema_version": "0.1.0",
        "bundle_kind": "pneuma_output",
        "run_id": "r0",
        "timestamp": "2026-07-10T00:00:00Z",
        "governance_status": "emitted",
        "risk_estimate": None,
        "instinct": None,
        "control_pressure": None,
        "causal_trace": None,
        "consciousness_evidence": None,
        "psyche_state": None,
        "workspace_broadcast": None,
        "blocked_uses": ["no_runtime_authority"],
        "limitations": ["shadow_mode"],
    }
    validate.validate_bundle(bundle)
    assert "psyche_state" in validate._BUNDLE_MEMBER_KEYS
    assert "workspace_broadcast" in validate._BUNDLE_MEMBER_KEYS


# --------------------------------------------------------------------------- #
# Task 2: persistent scar memory store                                        #
# --------------------------------------------------------------------------- #
def test_scar_memory_roundtrip_and_motif(tmp_path):
    from pneuma_lab.nervous_system import scar_memory as sm

    path = tmp_path / "scars.json"
    assert sm.load(path) == {}
    sm.save(path, {"m1:regress": 0.3})
    assert sm.load(path) == {"m1:regress": 0.3}
    memory_frame = {
        "frame_kind": "memory",
        "scar_motif_matches": [
            {"motif_id": "m1:regress", "similarity": 0.9},
            {"motif_id": "m2:flaky", "similarity": 0.4},
        ],
    }
    assert sm.motif_of(memory_frame) == ("m1:regress", 0.9)
    assert sm.motif_of({"frame_kind": "memory"}) is None
    assert sm.motif_of(None) is None


# --------------------------------------------------------------------------- #
# Task 3: 3-candidate workspace competition                                   #
# --------------------------------------------------------------------------- #
def test_workspace_competes_deterministically():
    from pneuma_lab.nervous_system import workspace as ws

    result = ws.compete(
        {"risk_instinct": 0.5, "memory_scar": 0.86, "uncertainty_self_model": 0.4}
    )
    assert result["winning_faculty"] == "memory_scar"
    assert result["winning_salience"] == 0.86
    assert result["salience_scores"]["scar_tissue"] == 0.86
    assert result["salience_scores"]["risk"] == 0.5
    assert result["salience_scores"]["uncertainty"] == 0.4
    losers = {c["faculty"] for c in result["competitors"]}
    assert losers == {"risk_instinct", "uncertainty_self_model"}
    tie = ws.compete(
        {"risk_instinct": 0.5, "memory_scar": 0.5, "uncertainty_self_model": 0.5}
    )
    assert tie["winning_faculty"] == "risk_instinct"


# --------------------------------------------------------------------------- #
# Task 4: subject fixtures are valid input-frame timelines                     #
# --------------------------------------------------------------------------- #
def test_subject_fixtures_are_valid_input_frames():
    for name in (
        "base.jsonl",
        "ablate_scar.jsonl",
        "clamp_certainty.jsonl",
        "disable_workspace.jsonl",
    ):
        frames = _frames(name)
        assert frames, name
        for fr in frames:
            validate.validate_or_raise(fr)


# --------------------------------------------------------------------------- #
# Task 5: BaselinePsycheSubject tick loop via the real ReplayHarness           #
# --------------------------------------------------------------------------- #
def test_subject_ticks_produce_valid_linked_frames_via_harness():
    from pneuma_lab.nervous_system.subject import BaselinePsycheSubject
    from pneuma_lab.replay.harness import ReplayHarness

    subject = BaselinePsycheSubject(scars={"m1:regress": 0.5})
    result = ReplayHarness(subject, validate=True).run(_frames("base.jsonl"))
    outs = result.tick_outputs
    assert len(outs) == 3
    prev = None
    for o in outs:
        ps, ct = o.psyche_state, o.causal_trace
        validate.validate_or_raise(ps)
        validate.validate_or_raise(o.workspace_broadcast)
        validate.validate_or_raise(o.control_pressure)
        validate.validate_or_raise(ct)
        validate.validate_or_raise(o.grounded_self_report)
        if prev is not None:
            assert ct["previous_state_hash"] == prev
        prev = ct["new_state_hash"]
        stages = [n["stage"] for n in ct["causal_path"]]
        assert stages == ["event", "internal_state", "broadcast", "pressure"]
        assert o.control_pressure["pressures"]["verification"] >= 0.0
        assert o.control_pressure["authority_tier"] in ("cosmetic", "soft")
        assert o.grounded_self_report["affect_state_hash"] == ps["state_hash"]
    winners = [o.workspace_broadcast["winning_faculty"] for o in outs]
    assert "memory_scar" in winners


# --------------------------------------------------------------------------- #
# Task 7: conservative subject evidence                                        #
# --------------------------------------------------------------------------- #
def test_subject_evidence_is_conservative():
    from pneuma_lab.nervous_system import shadow_evidence as nse

    frame = nse.subject_evidence_frame(
        ablation_result={"direction_ok": True, "null_holds": True},
        families_exercised=(
            "global_workspace",
            "valenced_learning",
            "identity_persistence",
            "higher_order_self_model",
        ),
        run_id="subj",
        timestamp="2026-07-10T00:00:00Z",
    )
    validate.validate_or_raise(frame)
    assert frame["evidence_level"] <= 1
    assert frame["real_subject_claim_status"] == "not_evaluated"
    assert frame["paired_replay_provenance"]["status"] == "uncertified_subject"
    for fam in (
        "global_workspace",
        "valenced_learning",
        "identity_persistence",
        "higher_order_self_model",
        "causal_intervention_robustness",
    ):
        assert frame["indicator_families"][fam]["status"] != "intervention_backed"
    assert frame["indicator_families"]["global_workspace"]["status"] in (
        "attempted",
        "architecture_only",
    )


# --------------------------------------------------------------------------- #
# Task 6: run_subject runtime + persistence                                    #
# --------------------------------------------------------------------------- #
def test_run_subject_is_deterministic_schema_valid_and_persists(tmp_path):
    from pneuma_lab.nervous_system.subject_runtime import run_subject

    frames = _frames("base.jsonl")
    store = tmp_path / "scars.json"
    b1 = run_subject(
        frames, scar_store_path=store, shadow_log_path=tmp_path / "l1.jsonl"
    )
    b2 = run_subject(
        frames,
        scar_store_path=tmp_path / "store2.json",
        shadow_log_path=tmp_path / "l2.jsonl",
    )
    for b in b1:
        validate.validate_bundle(b)
        assert b["control_pressure"]["authority_tier"] in ("cosmetic", "soft")
        assert b["control_pressure"]["pressures"]["verification"] >= 0.0
        assert "verdict" not in b["control_pressure"]
        assert b["causal_trace"]["new_state_hash"] == b["psyche_state"]["state_hash"]
    assert json.dumps(b1, sort_keys=True) == json.dumps(b2, sort_keys=True)
    assert store.exists()
    b3 = run_subject(
        frames, scar_store_path=store, shadow_log_path=tmp_path / "l3.jsonl"
    )
    p1 = b1[0]["control_pressure"]["pressures"]["verification"]
    p3 = b3[0]["control_pressure"]["pressures"]["verification"]
    assert p3 != p1


def test_run_subject_kill_switch_suppresses(tmp_path):
    from pneuma_lab.nervous_system.subject_runtime import run_subject

    frames = _frames("base.jsonl")
    frames[0] = {**frames[0], "kill_switch_state": "off"}
    log = tmp_path / "log.jsonl"
    out = run_subject(frames, scar_store_path=tmp_path / "s.json", shadow_log_path=log)
    assert out == []
    rows = [
        json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()
    ]
    assert rows and rows[0]["status"] == "suppressed_by_governance"
