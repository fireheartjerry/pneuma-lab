"""Tests for PneumaNervousSystem-v0: the shadow-mode model-backed I/O shell.

Covers schema validity, deterministic shadow outputs, no runtime authority
change, no verifier bypass, complete CausalTrace references, the
intervention/null ablation, honest (non-overclaiming) evidence, kill-switch
suppression, and import hygiene.
"""

import json
import subprocess
import sys
from pathlib import Path

from pneuma_lab import schemas
from pneuma_lab.schemas import validate

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "fixtures" / "nervous_system"


def _load_trace(path):
    return json.loads(Path(path).read_text(encoding="utf-8").strip())


# --------------------------------------------------------------------------- #
# Task 1: RiskEstimateFrame schema                                            #
# --------------------------------------------------------------------------- #
def test_risk_estimate_schema_registered_and_loads():
    all_schemas = schemas.load_all_schemas()
    assert "risk-estimate-frame.schema.json" in all_schemas
    assert (
        validate.FRAME_KIND_TO_SCHEMA["risk_estimate"]
        == "risk-estimate-frame.schema.json"
    )
    frame = {
        "schema_version": "0.1.0",
        "frame_kind": "risk_estimate",
        "timestamp": "2026-07-10T00:00:00Z",
        "run_id": "r0",
        "model_id": "PneumaBrain-v0.1",
        "model_version": "pneuma-brain/0.1.0",
        "prefix": "full",
        "failure_probability": 0.7,
        "success_probability": 0.3,
        "raw_score": 0.8,
        "risk_bucket": "high",
        "recommended_use": "advisory_only",
        "authority_granted": "none",
        "blocked_uses": ["no_runtime_authority"],
        "features_digest": "sha256:ab",
        "causal_trace_id": None,
    }
    validate.validate_or_raise(frame)


# --------------------------------------------------------------------------- #
# Task 2: bundle schemas + validator                                          #
# --------------------------------------------------------------------------- #
def test_bundles_load_and_validate():
    all_schemas = schemas.load_all_schemas()
    assert "pneuma-input-bundle.schema.json" in all_schemas
    assert "pneuma-output-bundle.schema.json" in all_schemas
    out_bundle = {
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
        "blocked_uses": ["no_runtime_authority"],
        "limitations": ["shadow_mode"],
    }
    validate.validate_bundle(out_bundle)
