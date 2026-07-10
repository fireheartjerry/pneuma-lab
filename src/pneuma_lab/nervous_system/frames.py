"""Pure, deterministic builders that turn a wrapped model risk dict into frames.

No wall clock, no randomness: every id is a content digest and every timestamp is
supplied by the caller (derived from the input frame). Repeat calls are byte-equal.

The frames produced here are ADVISORY. The control-pressure vector is a *candidate*
that is never applied; the causal trace records a model risk signal explicitly
labelled as NOT integrated psyche state.
"""

from __future__ import annotations

import hashlib
import json

from pneuma_lab.nervous_system import BLOCKED_USES, MODEL_ID

_TIER_ORDER = ("cosmetic", "soft", "vote", "hold", "veto")


def _digest(obj) -> str:
    """Stable short content digest for deterministic ids/hashes."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()[:16]


def _min_tier(a: str, b: str) -> str:
    """The weaker (lower) of two authority tiers; unknown tiers sort weakest-last."""
    ia = _TIER_ORDER.index(a) if a in _TIER_ORDER else len(_TIER_ORDER)
    ib = _TIER_ORDER.index(b) if b in _TIER_ORDER else len(_TIER_ORDER)
    return _TIER_ORDER[min(ia, ib)]


def risk_estimate_frame(
    brain_dict, *, run_id, timestamp, features_digest, causal_trace_id
):
    """Map a brain ``risk_estimate`` dict into a formal RiskEstimateFrame."""
    p = float(brain_dict["failure_probability"])
    return {
        "schema_version": "0.1.0",
        "frame_kind": "risk_estimate",
        "timestamp": timestamp,
        "run_id": run_id,
        "model_id": MODEL_ID,
        "model_version": brain_dict.get("model_version", "pneuma-brain/0.1.0"),
        "prefix": brain_dict["prefix"],
        "failure_probability": round(p, 6),
        "success_probability": round(1.0 - p, 6),
        "raw_score": round(float(brain_dict.get("raw_score", 0.0)), 6),
        "risk_bucket": brain_dict["risk_bucket"],
        "recommended_use": "advisory_only",
        "authority_granted": "none",
        "blocked_uses": list(brain_dict.get("blocked_uses", BLOCKED_USES)),
        "features_digest": features_digest,
        "causal_trace_id": causal_trace_id,
    }


def instinct_signal(brain_dict, *, run_id, timestamp, trace_id):
    """Bounded, receipts-first instinct signal derived from the model risk band."""
    p = float(brain_dict["failure_probability"])
    bucket = brain_dict["risk_bucket"]
    action = "deepen_verification" if bucket == "high" else "continue_fast_path"
    return {
        "schema_version": "0.1.0",
        "frame_kind": "instinct_signal",
        "timestamp": timestamp,
        "run_id": run_id,
        "motif_id": f"shadow.model-risk-{bucket}",
        "match_type": "anomaly",
        "confidence": round(p, 6),
        "severity": round(p, 6),
        "recommended_action": action,
        "authority_request": "soft",
        "explanation_trace_id": trace_id,
    }


def control_pressure_candidate(
    brain_dict, governance, *, run_id, timestamp, causal_trace_id
):
    """Bounded verification-pressure CANDIDATE (never applied).

    v0 maps risk to a single dimension: ``verification``. It is POSITIVE ONLY
    (additive-only: it may deepen verification, never reduce it below the
    verifier's own requirement). Authority tier is clamped to at most ``soft``.
    """
    p = max(0.0, min(1.0, float(brain_dict["failure_probability"])))
    global_max = (
        (governance or {}).get("authority_ceilings", {}).get("global_max", "soft")
    )
    tier = _min_tier("soft", global_max)
    return {
        "schema_version": "0.1.0",
        "frame_kind": "control_pressure",
        "timestamp": timestamp,
        "run_id": run_id,
        "authority_tier": tier,
        "pressures": {"verification": round(p, 6)},
        "sources": [f"risk_estimate:{run_id}:{brain_dict['prefix']}"],
        "causal_trace_id": causal_trace_id,
    }


def causal_trace(
    *,
    run_id,
    timestamp,
    input_ref,
    risk_ref,
    pressure_ref,
    instinct_ref,
    failure_probability,
):
    """Receipts: event -> internal_state(model risk) -> pressure(candidate)."""
    prev_hash = _digest({"run_id": run_id, "input_ref": input_ref})
    new_hash = _digest(
        {"risk_ref": risk_ref, "p": round(float(failure_probability), 6)}
    )
    trace_id = _digest({"run_id": run_id, "prev": prev_hash, "new": new_hash})
    return {
        "schema_version": "0.1.0",
        "frame_kind": "causal_trace",
        "timestamp": timestamp,
        "run_id": run_id,
        "trace_id": trace_id,
        "input_evidence_refs": [input_ref],
        "previous_state_hash": prev_hash,
        "new_state_hash": new_hash,
        "changed_dimensions": [
            {
                "dimension": "model_failure_probability",
                "to": round(float(failure_probability), 6),
            }
        ],
        "state_update_mechanism": "pneuma_brain_v0_1.risk_estimate",
        "causal_path": [
            {
                "stage": "event",
                "ref": input_ref,
                "note": "observable agent trace prefix",
            },
            {
                "stage": "internal_state",
                "ref": risk_ref,
                "note": "model risk signal, NOT integrated psyche state",
            },
            {
                "stage": "pressure",
                "ref": pressure_ref,
                "note": "bounded advisory verification-pressure candidate (never applied)",
            },
        ],
        "emitted_outputs": [risk_ref, instinct_ref, pressure_ref],
        "interventions_applied": [],
        "counterfactual_predictions": [
            {
                "condition": "if model risk signal ablated to 0",
                "predicted_outcome": "verification pressure candidate drops toward 0",
            }
        ],
    }
