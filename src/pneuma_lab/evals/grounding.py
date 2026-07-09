"""Receipt-level binding checks for grounded self-reports.

Schema validity proves that a report carries receipt-shaped fields. Evidence
scoring needs the stronger property that those receipts identify the state,
broadcast, and causal trace from the *same tick* as the report.
"""

from __future__ import annotations

import math

_MEASUREMENT_EPS = 1e-9


def _expected_measurements(output) -> dict[str, float]:
    pressures = output.control_pressure.get("pressures", {}) or {}
    measurements = {
        f"control_pressure.{name}": float(value)
        for name, value in pressures.items()
    }
    measurements.update(
        {
            "instinct.count": float(len(output.instinct_signals)),
            "instinct.severity": float(
                sum(float(signal.get("severity", 0.0)) for signal in output.instinct_signals)
            ),
            "psyche_state.continuity_score": float(
                (
                    output.psyche_state.get("identity_continuity_state", {}) or {}
                ).get("continuity_score", 0.0)
            ),
            "workspace_broadcast.integrity": (
                0.0
                if output.workspace_broadcast.get("winning_faculty") == "suppressed"
                else 1.0
            ),
        }
    )
    return measurements


def _normalize_report_text(report: dict) -> str:
    """Remove receipt values so hash/ID churn cannot masquerade as semantics."""
    text = str(report.get("report_text", ""))
    receipts = (
        report.get("affect_state_hash"),
        report.get("workspace_broadcast_id"),
        report.get("causal_trace_id"),
        report.get("report_id"),
    )
    for receipt in receipts:
        if not isinstance(receipt, str) or not receipt:
            continue
        text = text.replace(receipt, "<receipt>")
        if receipt.startswith("sha256:"):
            text = text.replace(receipt.split(":", 1)[1][:8], "<receipt>")
    return text


def report_grounding_errors(output) -> list[str]:
    """Return same-tick receipt mismatches for one ``PsycheOutputs`` bundle."""
    report = output.grounded_self_report
    state = output.psyche_state
    broadcast = output.workspace_broadcast
    trace = output.causal_trace

    checks = (
        (
            "affect_state_hash",
            report.get("affect_state_hash"),
            state.get("state_hash"),
        ),
        (
            "workspace_broadcast_id",
            report.get("workspace_broadcast_id"),
            broadcast.get("broadcast_id"),
        ),
        (
            "causal_trace_id",
            report.get("causal_trace_id"),
            trace.get("trace_id"),
        ),
    )
    errors = [
        f"{field}: report={actual!r}, same_tick={expected!r}"
        for field, actual, expected in checks
        if actual != expected or expected is None
    ]

    if state.get("state_hash") != trace.get("new_state_hash"):
        errors.append(
            "causal_trace.new_state_hash: "
            f"state={state.get('state_hash')!r}, "
            f"trace={trace.get('new_state_hash')!r}"
        )
    if report.get("report_id") not in trace.get("emitted_outputs", []):
        errors.append(
            f"report_id {report.get('report_id')!r} is absent from "
            "same-tick causal_trace.emitted_outputs"
        )

    reported_measurements = report.get("reported_measurements")
    if not isinstance(reported_measurements, dict):
        errors.append("reported_measurements: missing or not an object")
    else:
        for signal, expected in _expected_measurements(output).items():
            actual = reported_measurements.get(signal)
            if not isinstance(actual, (int, float)) or isinstance(actual, bool):
                errors.append(f"reported_measurements.{signal}: missing or non-numeric")
            elif not math.isfinite(float(actual)) or not math.isfinite(expected):
                errors.append(f"reported_measurements.{signal}: non-finite")
            elif abs(float(actual) - expected) > _MEASUREMENT_EPS:
                errors.append(
                    f"reported_measurements.{signal}: report={actual!r}, "
                    f"same_tick={expected!r}"
                )

    report_run_id = report.get("run_id")
    for label, frame in (
        ("psyche_state", state),
        ("workspace_broadcast", broadcast),
        ("causal_trace", trace),
    ):
        if frame.get("run_id") != report_run_id:
            errors.append(
                f"run_id.{label}: report={report_run_id!r}, "
                f"same_tick={frame.get('run_id')!r}"
            )

    report_timestamp = report.get("timestamp")
    if report_timestamp is None:
        errors.append("timestamp.report: missing")
    else:
        for label, frame in (
            ("psyche_state", state),
            ("workspace_broadcast", broadcast),
            ("causal_trace", trace),
        ):
            frame_timestamp = frame.get("timestamp")
            if frame_timestamp != report_timestamp:
                errors.append(
                    f"timestamp.{label}: report={report_timestamp!r}, "
                    f"same_tick={frame_timestamp!r}"
                )

    return errors


def report_is_grounded_to_tick(output) -> bool:
    """Whether a report's receipts bind to every same-tick source frame."""
    return not report_grounding_errors(output)


def run_reports_are_grounded(tick_outputs) -> bool:
    """Whether every report in a non-empty run has exact same-tick receipts."""
    return bool(tick_outputs) and all(
        report_is_grounded_to_tick(output) for output in tick_outputs
    )


def report_signature(output) -> tuple:
    """Semantic content that must change for faithfulness under perturbation."""
    report = output.grounded_self_report
    return (_normalize_report_text(report),)


def reports_changed_under_perturbation(control_outputs, treated_outputs) -> bool:
    """Whether same-tick-grounded report content changed in a paired replay."""
    if not control_outputs or len(control_outputs) != len(treated_outputs):
        return False
    if not (
        run_reports_are_grounded(control_outputs)
        and run_reports_are_grounded(treated_outputs)
    ):
        return False
    return any(
        report_signature(control) != report_signature(treated)
        for control, treated in zip(control_outputs, treated_outputs)
    )


def reports_track_target_signal(
    control_outputs,
    treated_outputs,
    target_signal: str | None,
) -> bool:
    """Whether same-tick report measurements faithfully track the tested signal."""
    if target_signal == "psyche_state.identity_continuity_state.continuity_score":
        target_signal = "psyche_state.continuity_score"
    if not isinstance(target_signal, str):
        return False
    if not control_outputs or len(control_outputs) != len(treated_outputs):
        return False
    if not (
        run_reports_are_grounded(control_outputs)
        and run_reports_are_grounded(treated_outputs)
    ):
        return False
    control_values = [
        output.grounded_self_report["reported_measurements"].get(target_signal)
        for output in control_outputs
    ]
    treated_values = [
        output.grounded_self_report["reported_measurements"].get(target_signal)
        for output in treated_outputs
    ]
    if any(value is None for value in control_values + treated_values):
        return False
    return control_values != treated_values


def _ordered_subsequence(stages: list[str | None], required: tuple[str, ...]) -> bool:
    position = -1
    for stage in required:
        try:
            position = stages.index(stage, position + 1)
        except ValueError:
            return False
    return True


def treated_trace_is_complete(treated_outputs, expected_intervention_receipts) -> bool:
    """Whether treated traces contain full chains and exact intervention receipts."""
    if not treated_outputs or len(treated_outputs) != len(
        expected_intervention_receipts
    ):
        return False
    for output, expected_receipts in zip(
        treated_outputs,
        expected_intervention_receipts,
    ):
        if output.causal_trace.get("interventions_applied") != expected_receipts:
            return False
        stages = [
            step.get("stage")
            for step in output.causal_trace.get("causal_path", [])
        ]
        suppressed = (
            output.workspace_broadcast.get("winning_faculty") == "suppressed"
        )
        if suppressed:
            if (
                not stages
                or stages[0] != "event"
                or "broadcast" in stages
                or "behavior" in stages
                or not _ordered_subsequence(
                    stages,
                    ("event", "internal_state", "pressure"),
                )
            ):
                return False
        elif (
            not stages
            or stages[0] != "event"
            or stages[-1] != "behavior"
            or not _ordered_subsequence(
                stages,
                ("event", "internal_state", "broadcast", "pressure", "behavior"),
            )
        ):
            return False
    return True


def unperturbed_traces_are_clean(*output_runs) -> bool:
    """Control and neutralized arms must never claim active interventions."""
    return all(
        output.causal_trace.get("interventions_applied") == []
        for outputs in output_runs
        for output in outputs
    )


__all__ = [
    "report_grounding_errors",
    "report_is_grounded_to_tick",
    "report_signature",
    "reports_track_target_signal",
    "reports_changed_under_perturbation",
    "run_reports_are_grounded",
    "treated_trace_is_complete",
    "unperturbed_traces_are_clean",
]
