"""ShadowNervousSystem: wraps PneumaBrain-v0.1 into advisory frames. No actuation.

The runtime consumes a PneumaTrace-shaped dict (its ``frames`` carry the
observable agent trace), computes a risk estimate at each supported prefix, and
assembles a validated PneumaOutputBundle. It appends one row per emission to an
append-only shadow log. It deliberately exposes NO actuation method: it emits
frames and logs, and never applies pressure, grants authority, or touches a
verifier verdict.
"""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.brain import predict as brain_predict
from pneuma_lab.brain import prefix_features as brain_pf
from pneuma_lab.nervous_system import BLOCKED_USES, LIMITATIONS
from pneuma_lab.nervous_system import ablation as nsa
from pneuma_lab.nervous_system import frames as nsf
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.schemas import validate

DEFAULT_PREFIXES = ("prefix_25", "prefix_50", "full")

# The model is timeless, so bundles reuse the input trace's own base timestamp
# when present (keeps outputs deterministic), else a fixed epoch string.
_FALLBACK_TS = "2026-07-10T00:00:00Z"


def _features_digest(model, trace, prefix):
    row = brain_pf.feature_vector(trace, prefix, model["tool_vocab"])
    return nsf._digest([round(float(v), 6) for v in row])


def _base_timestamp(trace):
    for frame in trace.get("frames", []):
        ts = frame.get("timestamp")
        if isinstance(ts, str):
            return ts
    return _FALLBACK_TS


class ShadowNervousSystem:
    """Advisory-only. Emits frames + appends to a shadow log; never actuates."""

    def __init__(self, model: dict, *, shadow_log_path=None):
        self._model = model
        self._log_path = Path(shadow_log_path) if shadow_log_path else None

    @classmethod
    def from_model_path(cls, path, *, shadow_log_path=None):
        return cls(brain_predict.load_model(path), shadow_log_path=shadow_log_path)

    def _append_log(self, row: dict) -> None:
        if self._log_path is None:
            return
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def run_trace(
        self, trace: dict, governance: dict, *, prefixes=DEFAULT_PREFIXES
    ) -> list:
        run_id = trace.get("run_id", "unknown")
        timestamp = _base_timestamp(trace)
        kill = (governance or {}).get("kill_switch_state", "on")
        if kill != "on":
            # Governance suppresses all control-relevant frames, but the shadow
            # log still records that the slice was suppressed (audit trail).
            self._append_log(
                {
                    "status": "suppressed_by_governance",
                    "run_id": run_id,
                    "kill_switch_state": kill,
                    "timestamp": timestamp,
                }
            )
            return []
        return [
            self._run_prefix(trace, governance, run_id, timestamp, p) for p in prefixes
        ]

    def _run_prefix(self, trace, governance, run_id, timestamp, prefix):
        brain_dict = brain_predict.risk_estimate(self._model, trace, prefix=prefix)
        digest = _features_digest(self._model, trace, prefix)
        risk_ref = f"risk_estimate:{run_id}:{prefix}"
        instinct_ref = f"instinct:{run_id}:{prefix}"
        pressure_ref = f"control_pressure:{run_id}:{prefix}"
        input_ref = f"agent_trace:{run_id}:{prefix}"

        trace_frame = nsf.causal_trace(
            run_id=run_id,
            timestamp=timestamp,
            input_ref=input_ref,
            risk_ref=risk_ref,
            pressure_ref=pressure_ref,
            instinct_ref=instinct_ref,
            failure_probability=brain_dict["failure_probability"],
        )
        trace_id = trace_frame["trace_id"]
        risk = nsf.risk_estimate_frame(
            brain_dict,
            run_id=run_id,
            timestamp=timestamp,
            features_digest=digest,
            causal_trace_id=trace_id,
        )
        instinct = nsf.instinct_signal(
            brain_dict, run_id=run_id, timestamp=timestamp, trace_id=trace_id
        )
        pressure = nsf.control_pressure_candidate(
            brain_dict,
            governance,
            run_id=run_id,
            timestamp=timestamp,
            causal_trace_id=trace_id,
        )
        coupling = nsa.run_ablation_for_trace(
            self._model, trace, governance, prefix=prefix
        )
        evidence = nse.shadow_evidence_frame(
            ablation_result=coupling, run_id=run_id, timestamp=timestamp
        )
        bundle = {
            "schema_version": "0.1.0",
            "bundle_kind": "pneuma_output",
            "run_id": run_id,
            "timestamp": timestamp,
            "governance_status": "emitted",
            "risk_estimate": risk,
            "instinct": instinct,
            "control_pressure": pressure,
            "causal_trace": trace_frame,
            "consciousness_evidence": evidence,
            "blocked_uses": list(BLOCKED_USES),
            "limitations": list(LIMITATIONS),
        }
        validate.validate_bundle(bundle)
        self._append_log(
            {
                "status": "emitted",
                "run_id": run_id,
                "prefix": prefix,
                "risk": risk["failure_probability"],
                "timestamp": timestamp,
            }
        )
        return bundle
