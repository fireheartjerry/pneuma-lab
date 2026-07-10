"""Intervention/null test for the shadow slice.

control : risk signal present  -> verification candidate = f(failure_probability)
treated : risk signal ablated  -> verification candidate = 0
null    : restore (unchanged)  -> must reproduce control

The observed (treated-minus-control) delta must be negative when control pressure
is nonzero, and the null delta must be ~0. On success this is Level-1-compatible
harness evidence; ``shadow_evidence`` turns it into a conservative frame.
"""

from __future__ import annotations

from pneuma_lab.brain import predict as brain_predict
from pneuma_lab.nervous_system import frames as nsf
from pneuma_lab.nervous_system import shadow_evidence as nse

_ABLATION_TS = "2026-07-10T00:00:00Z"


def _verification_value(brain_dict, governance):
    pressure = nsf.control_pressure_candidate(
        brain_dict,
        governance,
        run_id="ablation",
        timestamp=_ABLATION_TS,
        causal_trace_id=None,
    )
    return pressure["pressures"]["verification"]


def run_ablation(model, trace, governance, *, prefix="full"):
    """Run the control/treated/null arms and attach a conservative evidence frame."""
    brain_dict = brain_predict.risk_estimate(model, trace, prefix=prefix)
    control_value = _verification_value(brain_dict, governance)

    ablated = dict(brain_dict)
    ablated["failure_probability"] = 0.0
    treated_value = _verification_value(ablated, governance)

    null_value = _verification_value(dict(brain_dict), governance)

    observed_delta = round(treated_value - control_value, 6)
    null_delta = round(null_value - control_value, 6)
    direction_ok = (
        observed_delta < 0.0 if control_value > 0.0 else observed_delta == 0.0
    )
    null_holds = abs(null_delta) <= 1e-6

    result = {
        "control_value": control_value,
        "treated_value": treated_value,
        "null_value": null_value,
        "observed_delta": observed_delta,
        "null_delta": null_delta,
        "direction_ok": direction_ok,
        "null_holds": null_holds,
    }
    result["evidence_frame"] = nse.shadow_evidence_frame(
        ablation_result=result,
        run_id=trace.get("run_id", "unknown"),
        timestamp=_ABLATION_TS,
    )
    return result


def run_ablation_for_trace(model, trace, governance, *, prefix="full"):
    """Runtime-facing wrapper: the ablation coupling result minus the nested frame."""
    result = run_ablation(model, trace, governance, prefix=prefix)
    return {
        k: result[k]
        for k in ("observed_delta", "null_delta", "direction_ok", "null_holds")
    }
