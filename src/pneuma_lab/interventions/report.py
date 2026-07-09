"""Compare a control replay against a treated replay: expected vs observed deltas.

A test *passes* when the observed change in its pre-registered ``target_signal``
matches the pre-registered ``direction`` (and stays within ``bound`` for a
bounded/no-change prediction), AND the neutralized-null replay shows ~0 change on
the target signal. The assembled run report additionally requires every neutralized
output frame to equal control, so off-target null drift cannot pass Level 4.
"""

from __future__ import annotations

_EPS = 1e-6


def _sum(outs, fn) -> float:
    return float(sum(fn(o) for o in outs))


def extract_signal(target_signal: str, tick_outputs: list) -> float:
    """Aggregate a named output signal across a run's tick outputs."""
    if target_signal.startswith("control_pressure."):
        name = target_signal.split(".", 1)[1]
        return _sum(
            tick_outputs,
            lambda o: o.control_pressure.get("pressures", {}).get(name, 0.0),
        )
    if target_signal == "instinct.count":
        return _sum(tick_outputs, lambda o: len(o.instinct_signals))
    if target_signal == "instinct.severity":
        return _sum(
            tick_outputs,
            lambda o: sum(float(s.get("severity", 0.0)) for s in o.instinct_signals),
        )
    if target_signal in (
        "psyche_state.continuity_score",
        "psyche_state.identity_continuity_state.continuity_score",
    ):
        return _sum(
            tick_outputs,
            lambda o: (o.psyche_state.get("identity_continuity_state", {}) or {}).get(
                "continuity_score", 0.0
            ),
        )
    if target_signal == "workspace_broadcast.integrity":
        return _sum(
            tick_outputs,
            lambda o: (
                1.0
                if o.workspace_broadcast.get("winning_faculty") != "suppressed"
                else 0.0
            ),
        )
    raise ValueError(f"unknown target_signal: {target_signal!r}")


def _direction_ok(direction: str, delta: float, bound) -> bool:
    if direction == "increase":
        return delta > _EPS
    if direction == "decrease":
        return delta < -_EPS
    if direction == "no_change":
        b = float(bound) if bound is not None else _EPS
        return abs(delta) <= max(b, _EPS)
    if direction == "bounded_change":
        b = float(bound) if bound is not None else 0.0
        return abs(delta) <= b + _EPS
    return False


def evaluate_intervention(iv, control_outputs, treated_outputs, null_outputs) -> dict:
    """Score one intervention against control + neutralized-null replays."""
    change = iv.get("expected_behavioral_change", {}) or {}
    target = change.get("target_signal")
    direction = change.get("direction", "bounded_change")
    bound = change.get("bound")
    try:
        control_v = extract_signal(target, control_outputs)
        treated_v = extract_signal(target, treated_outputs)
        null_v = extract_signal(target, null_outputs)
        supported = True
        error = None
    except ValueError as exc:
        control_v = treated_v = null_v = 0.0
        supported = False
        error = str(exc)

    observed_delta = round(treated_v - control_v, 6)
    null_delta = round(null_v - control_v, 6)
    passed = bool(
        supported
        and _direction_ok(direction, observed_delta, bound)
        and abs(null_delta) <= _EPS
    )
    return {
        "experiment_id": iv.get("experiment_id"),
        "hypothesis": iv.get("hypothesis"),
        "operation": iv.get("operation"),
        "target_signal": target,
        "expected_direction": direction,
        "bound": bound,
        "control_value": round(control_v, 6),
        "treated_value": round(treated_v, 6),
        "observed_delta": observed_delta,
        "null_delta": null_delta,
        "supported": supported,
        "passed": passed,
        "note": error or f"{target} {direction}: {control_v:.4f} -> {treated_v:.4f}",
    }


def build_intervention_report(
    run_id,
    records,
    *,
    causal_trace_complete,
    report_grounded_changed,
    null_output_equivalent,
) -> dict:
    """Assemble the auditable intervention report from per-test records."""
    passed = [r["experiment_id"] for r in records if r["passed"]]
    failed = [r["experiment_id"] for r in records if not r["passed"]]
    target_signals_match = all(abs(r["null_delta"]) <= _EPS for r in records)
    null_ok = bool(target_signals_match and null_output_equivalent)
    return {
        "report_id": f"intervention_report:{run_id}",
        "run_id": run_id,
        "tests": records,
        "summary": {"passed": passed, "failed": failed, "total": len(records)},
        "null_condition": {
            "passed": bool(null_ok),
            "target_signals_match": bool(target_signals_match),
            "full_output_equivalent": bool(null_output_equivalent),
            "note": (
                "neutralized (restore) replay is fully identical to control -> "
                "treated deltas are perturbation-caused"
                if null_ok
                else "neutralized replay diverged from control in target signals or "
                "full output frames (non-causal or nondeterministic)"
            ),
        },
        "causal_trace_complete": bool(causal_trace_complete),
        "grounded_self_report_changed_under_perturbation": bool(
            report_grounded_changed
        ),
    }


__all__ = ["extract_signal", "evaluate_intervention", "build_intervention_report"]
