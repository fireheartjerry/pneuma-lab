"""Paired control-vs-intervention replay + authoritative Level-4 scoring.

Three replays are driven off one input timeline:

    control    — no perturbation (the healthy baseline; L0-3 are read from here),
    treated    — the intervention schedule applied at each tick,
    null       — the schedule neutralized (every op → ``restore``); must reproduce
                 control, proving any treated delta is caused by the perturbation.

The runner then evaluates every intervention (expected vs observed delta), checks
that the causal trace stays complete and that grounded self-reports track the
perturbation, and re-scores the evidence frame with real intervention-test results.
The psyche under test never scores itself: the scorer recomputes from receipts.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..evals.evidence import ConsciousnessEvidenceScorer
from ..psyche import ReferencePsyche
from ..replay.frames import group_into_ticks
from ..replay.harness import ReplayHarness, ReplayResult
from ..schemas.validate import validate_or_raise
from .report import build_intervention_report, evaluate_intervention
from .schedule import InterventionSchedule


@dataclass
class PairedReplayResult:
    """Everything a paired run produced: three replays, a report, an evidence frame."""

    control: ReplayResult
    treated: ReplayResult
    null: ReplayResult
    report: dict
    evidence_frame: dict


def _grounded(tick_outputs) -> bool:
    """True iff every self-report references a real state + trace hash in this run."""
    state_hashes = {o.psyche_state.get("state_hash") for o in tick_outputs}
    trace_ids = {o.causal_trace.get("trace_id") for o in tick_outputs}
    for o in tick_outputs:
        r = o.grounded_self_report
        if (
            r.get("affect_state_hash") not in state_hashes
            or r.get("causal_trace_id") not in trace_ids
        ):
            return False
    return True


def _report_signature(o) -> tuple:
    r = o.grounded_self_report
    return (r.get("affect_state_hash"), r.get("report_text"))


def _report_changed(control_outputs, treated_outputs) -> bool:
    """>=1 tick's grounded self-report faithfully tracked the perturbation.

    Faithfulness is checked against both the state hash the report is grounded in and
    its rendered text: a perturbation that moves interior state (clamp tension, ablate
    scars, boost a drive) shifts the hash; one that suppresses the broadcast shifts the
    text ("winning faculty: suppressed"). Both runs must stay fully grounded.
    """
    if not (_grounded(control_outputs) and _grounded(treated_outputs)):
        return False
    for c, t in zip(control_outputs, treated_outputs):
        if _report_signature(c) != _report_signature(t):
            return True
    return False


def _trace_complete(treated_outputs) -> bool:
    """Every non-suppressed tick spans event→…→behavior; a suppressed break is expected."""
    for o in treated_outputs:
        stages = [s["stage"] for s in o.causal_trace["causal_path"]]
        suppressed = o.workspace_broadcast.get("winning_faculty") == "suppressed"
        if suppressed:
            if "behavior" in stages:
                return False
        else:
            if not stages or stages[0] != "event" or stages[-1] != "behavior":
                return False
    return True


class PairedReplayRunner:
    """Run control/treated/null replays and score Level 4 honestly."""

    def __init__(self, psyche_factory=ReferencePsyche, validate: bool = True) -> None:
        self._factory = psyche_factory
        self._validate = validate
        self._scorer = ConsciousnessEvidenceScorer()

    def _run(self, frames, schedule) -> ReplayResult:
        harness = ReplayHarness(self._factory(), validate=self._validate)
        return harness.run(frames, schedule=schedule)

    def run(self, input_frames: list[dict]) -> PairedReplayResult:
        schedule = InterventionSchedule.from_frames(input_frames)
        control = self._run(input_frames, None)
        treated = self._run(input_frames, schedule)
        null = self._run(input_frames, schedule.neutralized())

        ticks = group_into_ticks(input_frames)
        run_id = _run_id(input_frames)

        # Unique intervention frames, order-stable, for evaluation.
        seen: set = set()
        ivs: list[dict] = []
        for tick in ticks:
            for iv in tick.interventions:
                key = iv.get("experiment_id")
                if key not in seen:
                    seen.add(key)
                    ivs.append(iv)

        records = [
            evaluate_intervention(
                iv, control.tick_outputs, treated.tick_outputs, null.tick_outputs
            )
            for iv in ivs
        ]
        trace_complete = _trace_complete(treated.tick_outputs)
        report_changed = _report_changed(control.tick_outputs, treated.tick_outputs)
        report = build_intervention_report(
            run_id,
            records,
            causal_trace_complete=trace_complete,
            report_grounded_changed=report_changed,
        )

        evidence = self._scorer.score(
            run_id=run_id,
            input_frames=input_frames,
            tick_outputs=control.tick_outputs,  # L0-3 from the clean control run
            interventions_executed=len(records),
            memory_readback_present=any(t.memory for t in ticks),
            intervention_tests=report["summary"],
            null_condition_passed=report["null_condition"]["passed"],
            causal_trace_complete=trace_complete,
            grounded_report_changed=report_changed,
        )
        if self._validate:
            validate_or_raise(evidence)

        return PairedReplayResult(control, treated, null, report, evidence)


def _run_id(frames):
    for f in frames:
        if f.get("frame_kind") == "world":
            return f.get("run_id")
    return frames[0].get("run_id") if frames else None


__all__ = ["PairedReplayRunner", "PairedReplayResult"]
