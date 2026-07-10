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
