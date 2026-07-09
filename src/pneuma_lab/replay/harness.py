"""ReplayHarness — deterministic replay of an input-frame timeline through a psyche.

Pipeline (evaluation-guide Layers A + C + H):

    1. validate every input frame (Layer A),
    2. group the flat stream into ordered ticks,
    3. drive the psyche one tick at a time, carrying its state (recurrence),
    4. validate every emitted output frame (Layer A),
    5. hand the full run log to the evidence scorer (Layers C/D-gap).

Without a schedule, ``InterventionFrame`` inputs are registered but not executed.
With a schedule, the harness can execute perturbations for one treated replay, but
a single replay never self-certifies Level 4: only the paired runner supplies the
cross-checked control/treated/null test inventory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..evals.evidence import ConsciousnessEvidenceScorer
from ..psyche.interface import PsycheInputs, PsycheOutputs, PsycheUnderTest
from ..schemas.validate import validate_or_raise
from .frames import Tick, group_into_ticks


@dataclass
class ReplayResult:
    """Everything one replay produced, ready for storage or scoring."""

    output_frames: list[dict]
    evidence_frame: dict
    tick_outputs: list[PsycheOutputs] = field(default_factory=list)
    input_count: int = 0
    tick_count: int = 0
    interventions_seen: int = 0
    interventions_executed: int = 0


class ReplayHarness:
    """Drive a :class:`PsycheUnderTest` over a recorded input-frame timeline."""

    def __init__(self, psyche: PsycheUnderTest, validate: bool = True) -> None:
        self.psyche = psyche
        self.validate = validate
        self._scorer = ConsciousnessEvidenceScorer()

    def run(
        self,
        input_frames: list[dict],
        *,
        strip_memory: bool = False,
        schedule=None,
    ) -> ReplayResult:
        """Replay ``input_frames`` and return outputs + a scored evidence frame.

        Args:
            input_frames: flat JSONL-style stream of input frame dicts.
            strip_memory: if True, drop MemoryFrames before ticking (used by the
                L2 memory-readback ablation test — no readback ⇒ weaker outputs).
            schedule: an optional ``InterventionSchedule``. When given and the psyche
                implements ``Perturbable``, the interventions active on each tick are
                installed before that tick (a *treated* replay). A single replay never
                self-certifies Level 4 (``intervention_tests=None``); the paired runner
                supplies real pass/fail results.
        """
        from ..interventions.perturbation import (
            Perturbable,
        )  # local: avoid import cycle

        if self.validate:
            for frame in input_frames:
                validate_or_raise(frame)

        ticks = group_into_ticks(input_frames)
        self.psyche.reset()
        perturbable = isinstance(self.psyche, Perturbable)

        output_frames: list[dict] = []
        tick_outputs: list[PsycheOutputs] = []
        interventions_seen = 0
        executed_ids: set = set()

        for tick in ticks:
            interventions_seen += len(tick.interventions)
            active = schedule.active(tick.index) if schedule is not None else []
            if perturbable:
                self.psyche.set_active_interventions(active)
                executed_ids.update(iv.get("experiment_id") for iv in active)
            inputs = self._tick_to_inputs(tick, strip_memory=strip_memory)
            outputs = self.psyche.tick(inputs)
            frames = outputs.all_frames()
            if self.validate:
                for frame in frames:
                    validate_or_raise(frame)
            output_frames.extend(frames)
            tick_outputs.append(outputs)

        interventions_executed = len(executed_ids)
        run_id = ticks[0].world.get("run_id") if ticks else None
        evidence = self._scorer.score(
            run_id=run_id,
            input_frames=input_frames,
            tick_outputs=tick_outputs,
            interventions_executed=interventions_executed,
            memory_readback_present=any(t.memory for t in ticks) and not strip_memory,
        )
        if self.validate:
            validate_or_raise(evidence)

        return ReplayResult(
            output_frames=output_frames,
            evidence_frame=evidence,
            tick_outputs=tick_outputs,
            input_count=len(input_frames),
            tick_count=len(ticks),
            interventions_seen=interventions_seen,
            interventions_executed=interventions_executed,
        )

    @staticmethod
    def _tick_to_inputs(tick: Tick, *, strip_memory: bool) -> PsycheInputs:
        return PsycheInputs(
            world=tick.world,
            tick_index=tick.index,
            agent_trace=tick.agent_trace,
            memory=None if strip_memory else tick.memory,
            governance=tick.governance,
        )


__all__ = ["ReplayHarness", "ReplayResult"]
