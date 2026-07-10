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
