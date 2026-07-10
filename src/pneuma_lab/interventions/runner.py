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
from .certified_subjects import is_certified
from .provenance import _PairedReplayProvenance, counterbalanced_orders
from .schedule import InterventionSchedule


@dataclass
class PairedReplayResult:
    """Everything a paired run produced: three replays, a report, an evidence frame."""

    control: ReplayResult
    treated: ReplayResult
    null: ReplayResult
    report: dict
    evidence_frame: dict


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
        schedules = {
            "control": None,
            "treated": schedule,
            "null": schedule.neutralized(),
        }
        replay_passes: list[dict[str, ReplayResult]] = []
        for order in counterbalanced_orders():
            replay_passes.append(
                {arm: self._run(input_frames, schedules[arm]) for arm in order}
            )
        primary = replay_passes[0]
        control = primary["control"]
        treated = primary["treated"]
        null = primary["null"]
        provenance = _PairedReplayProvenance.issue(
            input_frames,
            [
                {
                    arm: replay_result.tick_outputs
                    for arm, replay_result in replay_pass.items()
                }
                for replay_pass in replay_passes
            ],
            self._factory,
            subject_factory_eligible=(
                self._factory is ReferencePsyche or is_certified(self._factory)
            ),
        )

        run_id = _run_id(input_frames)
        ticks = group_into_ticks(input_frames)
        evidence, report = self._scorer._score_paired_runner_verified(
            run_id=run_id,
            input_frames=input_frames,
            control_outputs=control.tick_outputs,
            treated_outputs=treated.tick_outputs,
            null_outputs=null.tick_outputs,
            interventions_executed=treated.interventions_executed,
            memory_readback_present=any(t.memory for t in ticks),
            provenance=provenance,
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
