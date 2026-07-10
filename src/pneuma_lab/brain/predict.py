"""Inference surface for a trained PneumaBrain-v0.1 model.

Loads a ``model.json`` produced by ``train_full`` and emits a calibrated,
advisory ``RiskEstimateFrame`` for a raw trace at a chosen prefix window. This is
the immediately-usable read side of v0.1: it produces evidence-bearing priors,
never control actions. It performs no runtime authority change and no verifier
bypass.
"""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.brain import calibration as cal
from pneuma_lab.brain import model as model_mod
from pneuma_lab.brain import prefix_features as pf

RISK_BUCKET_HIGH = 0.66
RISK_BUCKET_MEDIUM = 0.33
BLOCKED_USES = (
    "no_runtime_authority",
    "no_verifier_bypass",
    "no_consciousness_claim",
)


def load_model(path: str | Path) -> dict:
    """Load a trained model.json."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _bucket(probability: float) -> str:
    if probability >= RISK_BUCKET_HIGH:
        return "high"
    if probability >= RISK_BUCKET_MEDIUM:
        return "medium"
    return "low"


def risk_estimate(model: dict, trace: dict, *, prefix: str = "full") -> dict:
    """Calibrated advisory RiskEstimateFrame for one trace at one prefix."""
    if prefix not in model.get("prefixes", {}):
        raise ValueError(f"model has no prefix head {prefix!r}")
    entry = model["prefixes"][prefix]
    row = pf.feature_vector(trace, prefix, model["tool_vocab"])
    if len(row) != len(entry["feature_names"]):
        raise ValueError("feature width does not match the trained head")
    # Calibration was fit in logit space; apply it there so identity params
    # (1.0, 0.0) reproduce the model's own raw probability exactly.
    raw = model_mod.predict_logit(entry["head"], row)
    platt = entry["platt"]
    probability = cal.apply_platt(raw, platt["a"], platt["b"])
    return {
        "frame_type": "RiskEstimateFrame",
        "task_type": "RISK_PREDICTION",
        "failure_probability": probability,
        "success_probability": 1.0 - probability,
        "raw_score": raw,
        "risk_bucket": _bucket(probability),
        "prefix": prefix,
        "model_version": model["model_version"],
        "recommended_use": "advisory_only",
        "blocked_uses": list(BLOCKED_USES),
    }


__all__ = ["BLOCKED_USES", "load_model", "risk_estimate"]
