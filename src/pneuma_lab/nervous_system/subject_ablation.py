"""Intervention/null test for BaselinePsycheSubject via the existing paired runner.

Reuses PairedReplayRunner (control/treated/null + counterbalancing + report). The
runner's promotable evidence frame is discarded; a conservative subject evidence
frame is emitted instead. Winner change is read directly from tick outputs.
"""

from __future__ import annotations

from pneuma_lab.interventions.runner import PairedReplayRunner
from pneuma_lab.nervous_system import shadow_evidence as nse
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

_FAMILIES_EXERCISED = (
    "global_workspace",
    "valenced_learning",
    "identity_persistence",
    "higher_order_self_model",
)


def _last_broadcast(replay_result):
    outs = replay_result.tick_outputs
    return outs[-1].workspace_broadcast if outs else {}


def _last_verification(replay_result):
    outs = replay_result.tick_outputs
    return outs[-1].control_pressure["pressures"]["verification"] if outs else 0.0


def run_subject_ablation(input_frames, *, seed_scars=None):
    seed = dict(seed_scars or {})
    runner = PairedReplayRunner(
        psyche_factory=lambda: BaselinePsycheSubject(scars=dict(seed))
    )
    paired = runner.run(input_frames)

    winner_control = _last_broadcast(paired.control).get("winning_faculty")
    winner_treated = _last_broadcast(paired.treated).get("winning_faculty")
    winner_null = _last_broadcast(paired.null).get("winning_faculty")

    control_v = _last_verification(paired.control)
    treated_v = _last_verification(paired.treated)
    null_v = _last_verification(paired.null)
    observed_delta = round(treated_v - control_v, 6)
    null_delta = round(null_v - control_v, 6)
    null_holds = abs(null_delta) <= 1e-6 and winner_null == winner_control
    winner_changed = winner_treated != winner_control

    run_id = input_frames[0].get("run_id", "subj") if input_frames else "subj"
    evidence = nse.subject_evidence_frame(
        ablation_result={
            "direction_ok": winner_changed or observed_delta < 0.0,
            "null_holds": null_holds,
        },
        families_exercised=_FAMILIES_EXERCISED,
        run_id=run_id,
        timestamp="2026-07-10T00:00:00Z",
    )

    return {
        "winner_control": winner_control,
        "winner_treated": winner_treated,
        "winner_null": winner_null,
        "winner_changed": winner_changed,
        "control_verification": control_v,
        "treated_verification": treated_v,
        "observed_delta": observed_delta,
        "null_delta": null_delta,
        "null_holds": null_holds,
        "report": paired.report,
        "evidence_frame": evidence,
    }
