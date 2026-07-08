"""Intervention report: signal extraction + expected-vs-observed evaluation."""

from __future__ import annotations

from types import SimpleNamespace as NS

from pneuma_lab.interventions.report import evaluate_intervention, extract_signal


def _outs(pressures=None, instincts=0, continuity=0.0, faculty="affect"):
    return [
        NS(
            control_pressure={
                "pressures": pressures or {"verification": 0.5, "exploration": 0.1}
            },
            instinct_signals=[{"severity": 0.5}] * instincts,
            psyche_state={
                "identity_continuity_state": {"continuity_score": continuity}
            },
            workspace_broadcast={"winning_faculty": faculty},
        )
    ]


def test_extract_control_pressure_signal():
    assert extract_signal("control_pressure.verification", _outs()) == 0.5


def test_extract_instinct_count():
    assert extract_signal("instinct.count", _outs(instincts=2)) == 2


def test_extract_continuity_score():
    assert extract_signal("psyche_state.continuity_score", _outs(continuity=0.7)) == 0.7


def test_extract_workspace_integrity_counts_non_suppressed():
    assert extract_signal("workspace_broadcast.integrity", _outs(faculty="affect")) == 1
    assert (
        extract_signal("workspace_broadcast.integrity", _outs(faculty="suppressed"))
        == 0
    )


def test_unknown_signal_raises():
    import pytest

    with pytest.raises(ValueError):
        extract_signal("nope.nothing", _outs())


def test_evaluate_decrease_passes_when_signal_drops():
    iv = {
        "experiment_id": "e",
        "hypothesis": "verification drops",
        "expected_behavioral_change": {
            "direction": "decrease",
            "target_signal": "control_pressure.verification",
        },
    }
    control = _outs(pressures={"verification": 0.8, "exploration": 0.1})
    treated = _outs(pressures={"verification": 0.2, "exploration": 0.1})
    rec = evaluate_intervention(iv, control, treated, control)
    assert rec["passed"] is True
    assert rec["observed_delta"] < 0
    assert rec["null_delta"] == 0.0


def test_evaluate_fails_when_direction_wrong():
    iv = {
        "experiment_id": "e",
        "hypothesis": "h",
        "expected_behavioral_change": {
            "direction": "increase",
            "target_signal": "control_pressure.verification",
        },
    }
    control = _outs(pressures={"verification": 0.8, "exploration": 0.1})
    treated = _outs(pressures={"verification": 0.2, "exploration": 0.1})
    rec = evaluate_intervention(iv, control, treated, control)
    assert rec["passed"] is False


def test_evaluate_no_change_passes_within_epsilon():
    iv = {
        "experiment_id": "e",
        "hypothesis": "null",
        "expected_behavioral_change": {
            "direction": "no_change",
            "target_signal": "control_pressure.verification",
        },
    }
    control = _outs()
    rec = evaluate_intervention(iv, control, control, control)
    assert rec["passed"] is True


def test_evaluate_fails_when_null_diverges():
    """If the neutralized replay does not reproduce control, the delta isn't causal."""
    iv = {
        "experiment_id": "e",
        "hypothesis": "h",
        "expected_behavioral_change": {
            "direction": "decrease",
            "target_signal": "control_pressure.verification",
        },
    }
    control = _outs(pressures={"verification": 0.8, "exploration": 0.1})
    treated = _outs(pressures={"verification": 0.2, "exploration": 0.1})
    null = _outs(pressures={"verification": 0.5, "exploration": 0.1})  # != control
    rec = evaluate_intervention(iv, control, treated, null)
    assert rec["passed"] is False
    assert rec["null_delta"] != 0.0
