from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.brain import predict, train_full

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "brain"
TRACES = FIXTURES / "synthetic_traces.jsonl"
AUTH = FIXTURES / "authorization_authorized.json"


def _train_model(tmp_path) -> Path:
    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"corpus_id":"pneuma-brain-v0"}', encoding="utf-8")
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    auth["corpus_manifest_sha256"] = (
        "sha256:" + hashlib.sha256(manifest.read_bytes()).hexdigest()
    )
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    out = tmp_path / "run"
    train_full.run_full_training(
        traces_path=TRACES,
        authorization_path=auth_path,
        corpus_manifest_path=manifest,
        output_root=out,
        n_resamples=100,
        require_clean_code=False,
    )
    return out / "model.json"


def _a_trace() -> dict:
    with open(TRACES, encoding="utf-8") as handle:
        return json.loads(handle.readline())


def test_risk_estimate_emits_calibrated_advisory_frame(tmp_path):
    model = predict.load_model(_train_model(tmp_path))
    frame = predict.risk_estimate(model, _a_trace(), prefix="full")
    assert frame["frame_type"] == "RiskEstimateFrame"
    assert 0.0 <= frame["failure_probability"] <= 1.0
    assert frame["risk_bucket"] in {"low", "medium", "high"}
    assert frame["recommended_use"] == "advisory_only"
    assert "no_verifier_bypass" in frame["blocked_uses"]


def test_all_prefix_heads_are_usable(tmp_path):
    model = predict.load_model(_train_model(tmp_path))
    trace = _a_trace()
    for prefix in ("prefix_25", "prefix_50", "full"):
        frame = predict.risk_estimate(model, trace, prefix=prefix)
        assert 0.0 <= frame["failure_probability"] <= 1.0


def test_unknown_prefix_is_rejected(tmp_path):
    model = predict.load_model(_train_model(tmp_path))
    with pytest.raises(ValueError):
        predict.risk_estimate(model, _a_trace(), prefix="prefix_10")
