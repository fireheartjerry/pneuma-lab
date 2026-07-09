"""ConsciousnessEvidenceScorer — honest, conservative Level 0-4 scoring.

This scorer reads a whole replay's output frames and decides an ``evidence_level``
using the ladder in ``docs/consciousness-levels.md``. It is built to *under*-claim:

    * a family counts as evidenced only if a real frame receipt exists for it —
    architecture without a receipt drops to unevidenced (Layer B / "no receipts,
    no claim");
    * it NEVER promotes on self-report; ``roleplay_confabulation_risk`` is
    computed by checking every grounded self-report's hashes against the run log,
    not from how the prose reads;
    * Level 4 requires a structurally consistent inventory of registered,
    executed, and reported intervention tests in addition to the null, trace,
    report-grounding, and confabulation gates;
    * it HARD-CAPS at Level 4. Level 5 remains a separately specified target.

The nine indicator families map to the mechanisms ``ReferencePsyche`` exercises;
``causal_intervention_robustness`` is the one family that is architecture-only in
Phase 1 and is reported as such.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..interventions.provenance import (
    _PairedReplayProvenance,
    unverified_provenance_record,
)
from ..interventions.report import build_intervention_report, evaluate_intervention
from ..schemas.validate import FrameValidationError, validate_or_raise
from .grounding import (
    report_is_grounded_to_tick,
    reports_track_target_signal,
    treated_trace_is_complete,
    unperturbed_traces_are_clean,
)

# What remains once Level 4 is met — the honest gap up to the Level-5 north star.
_L5_MISSING = [
    "convergent_evidence: Level 4 shown on one battery; Level 5 needs every family intervention-backed",
    "adversarial_robustness: evidence not yet stress-tested against adversarial perturbation over time",
    "external_audit: internally auditable in-harness; Level 5 needs independent external audit",
]

# Grounded self-reports must stay this clean for a Level-4 claim (anti-confabulation rail).
_CONFAB_MAX_FOR_L4 = 0.2

_ALL_FAMILIES = (
    "global_workspace",
    "recurrent_processing",
    "higher_order_self_model",
    "predictive_processing",
    "attention_schema",
    "valenced_learning",
    "identity_persistence",
    "counterfactual_introspection",
    "causal_intervention_robustness",
)


@dataclass(frozen=True)
class _InterventionGate:
    """Normalized, cross-checked intervention inventory used by the L4 gate."""

    registered: tuple[str, ...]
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    executed: int
    reported_total: int | None
    has_test_results: bool
    non_restore_evaluated: bool
    genuine_perturbation: bool
    inventory_errors: tuple[str, ...]
    provenance_errors: tuple[str, ...]

    @property
    def integrity_errors(self) -> tuple[str, ...]:
        return self.inventory_errors + self.provenance_errors

    @property
    def inventory_ok(self) -> bool:
        return bool(self.registered) and not self.inventory_errors

    @property
    def integrity_ok(self) -> bool:
        return bool(self.registered) and not self.integrity_errors

    @property
    def promotion_ready(self) -> bool:
        return (
            self.integrity_ok
            and self.genuine_perturbation
            and bool(self.passed)
            and not self.failed
        )

    def as_record(self) -> dict:
        outcomes = {experiment_id: "passed" for experiment_id in self.passed}
        outcomes.update({experiment_id: "failed" for experiment_id in self.failed})
        return {
            "results": [
                {
                    "experiment_id": experiment_id,
                    "outcome": outcomes.get(experiment_id, "not_evaluated"),
                }
                for experiment_id in self.registered
            ],
            "executed_count": self.executed,
            "reported_total": self.reported_total,
            "integrity_ok": self.integrity_ok,
            "integrity_errors": list(self.integrity_errors),
            "genuine_perturbation": self.genuine_perturbation,
        }


def _string_ids(value, label: str, errors: list[str]) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        errors.append(f"{label} must be a list of strings")
        return ()
    return tuple(value)


def _unique_intervention_frames(
    input_frames: list[dict],
) -> tuple[list[dict], list[str], int]:
    """Return attached first-seen interventions, duplicate IDs, and stray count."""
    # Local import avoids the replay package's harness -> scorer import cycle.
    from ..replay.frames import group_into_ticks

    attached = [
        intervention
        for tick in group_into_ticks(input_frames)
        for intervention in tick.interventions
    ]
    raw_count = sum(
        1
        for frame in input_frames
        if isinstance(frame, dict) and frame.get("frame_kind") == "intervention"
    )
    unique: list[dict] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for frame in attached:
        experiment_id = frame.get("experiment_id")
        if not isinstance(experiment_id, str) or not experiment_id:
            unique.append(frame)
            continue
        if experiment_id in seen:
            duplicates.append(experiment_id)
            continue
        seen.add(experiment_id)
        unique.append(frame)
    return unique, duplicates, raw_count - len(attached)


def _intervention_gate(
    input_frames: list[dict],
    interventions_executed: int,
    intervention_tests: dict | None,
    intervention_records: list[dict] | None = None,
    provenance_errors: list[str] | None = None,
) -> _InterventionGate:
    """Cross-check registered IDs, execution count, and report partition."""
    registered: list[str] = []
    errors: list[str] = []
    intervention_frames, duplicate_ids, unattached_count = _unique_intervention_frames(
        input_frames
    )
    for duplicate_id in duplicate_ids:
        errors.append(f"duplicate registered experiment_id: {duplicate_id}")
    if unattached_count:
        errors.append(
            f"{unattached_count} InterventionFrame(s) are not attached to any world tick"
        )
    for frame in intervention_frames:
        experiment_id = frame.get("experiment_id")
        if not isinstance(experiment_id, str) or not experiment_id:
            errors.append("registered intervention has no non-empty experiment_id")
            continue
        registered.append(experiment_id)

    has_results = intervention_tests is not None
    tests = intervention_tests if isinstance(intervention_tests, dict) else {}
    if intervention_tests is not None and not isinstance(intervention_tests, dict):
        errors.append("intervention_tests must be an object")
    passed = _string_ids(tests.get("passed", []), "passed", errors)
    failed = _string_ids(tests.get("failed", []), "failed", errors)
    reported_total = tests.get("total") if has_results else None

    if not isinstance(interventions_executed, int) or isinstance(
        interventions_executed, bool
    ):
        errors.append("interventions_executed must be an integer")
        executed = 0
    else:
        executed = interventions_executed

    if not registered:
        errors.append("no InterventionFrame is registered")
    elif len(registered) > 1:
        errors.append(
            "multiple interventions require isolated treated/null arms or an "
            "explicit joint-intervention hypothesis"
        )
    if not has_results:
        errors.append("no intervention test summary was supplied")
    if has_results and (
        not isinstance(reported_total, int) or isinstance(reported_total, bool)
    ):
        errors.append("intervention test summary total must be an integer")
        reported_total = None
    if len(set(passed)) != len(passed):
        errors.append("passed contains duplicate experiment IDs")
    if len(set(failed)) != len(failed):
        errors.append("failed contains duplicate experiment IDs")
    if set(passed) & set(failed):
        errors.append("passed and failed experiment IDs overlap")

    expected = set(registered)
    reported = set(passed) | set(failed)
    if expected != reported:
        errors.append(
            "reported experiment IDs do not exactly partition registered IDs: "
            f"registered={sorted(expected)}, reported={sorted(reported)}"
        )
    if executed != len(registered):
        errors.append(
            f"executed count {executed} does not match registered count {len(registered)}"
        )
    if reported_total != len(registered):
        errors.append(
            f"reported total {reported_total!r} does not match registered count "
            f"{len(registered)}"
        )

    non_restore_evaluated = any(
        record.get("experiment_id") in registered
        and record.get("operation") != "restore"
        for record in (intervention_records or [])
    )
    genuine = any(
        record.get("experiment_id") in registered
        and record.get("operation") != "restore"
        and abs(float(record.get("observed_delta", 0.0))) > 1e-6
        for record in (intervention_records or [])
    )
    return _InterventionGate(
        registered=tuple(registered),
        passed=passed,
        failed=failed,
        executed=executed,
        reported_total=reported_total,
        has_test_results=has_results,
        non_restore_evaluated=non_restore_evaluated,
        genuine_perturbation=genuine,
        inventory_errors=tuple(errors),
        provenance_errors=tuple(provenance_errors or []),
    )


class ConsciousnessEvidenceScorer:
    """Score a replay's output frames into a Level 0-4 ConsciousnessEvidenceFrame."""

    def score(
        self,
        *,
        run_id: str | None,
        input_frames: list[dict],
        tick_outputs: list,
        interventions_executed: int,
        memory_readback_present: bool,
    ) -> dict:
        """Score one replay, which can never self-certify Level 4."""
        self._validate_source_frames(input_frames, tick_outputs)
        run_id = self._validate_run_identity(run_id, input_frames, tick_outputs)
        intervention_gate = _intervention_gate(
            input_frames,
            interventions_executed,
            None,
        )
        return self._score(
            run_id=run_id,
            tick_outputs=tick_outputs,
            memory_readback_present=memory_readback_present,
            intervention_gate=intervention_gate,
            intervention_tests=None,
            null_condition_passed=False,
            causal_trace_complete=False,
            grounded_report_changed=False,
            paired_provenance=unverified_provenance_record(),
        )

    def score_paired(
        self,
        *,
        run_id: str | None,
        input_frames: list[dict],
        control_outputs: list,
        treated_outputs: list,
        null_outputs: list,
        interventions_executed: int,
        memory_readback_present: bool,
    ) -> tuple[dict, dict]:
        """Diagnose raw paired outputs without allowing them to self-certify L4."""
        return self._score_paired(
            run_id=run_id,
            input_frames=input_frames,
            control_outputs=control_outputs,
            treated_outputs=treated_outputs,
            null_outputs=null_outputs,
            interventions_executed=interventions_executed,
            memory_readback_present=memory_readback_present,
            provenance=None,
        )

    def _score_paired_runner_verified(
        self,
        *,
        run_id: str | None,
        input_frames: list[dict],
        control_outputs: list,
        treated_outputs: list,
        null_outputs: list,
        interventions_executed: int,
        memory_readback_present: bool,
        provenance: _PairedReplayProvenance,
    ) -> tuple[dict, dict]:
        """Score arms carrying a digest capability issued by the paired runner."""
        return self._score_paired(
            run_id=run_id,
            input_frames=input_frames,
            control_outputs=control_outputs,
            treated_outputs=treated_outputs,
            null_outputs=null_outputs,
            interventions_executed=interventions_executed,
            memory_readback_present=memory_readback_present,
            provenance=provenance,
        )

    def _score_paired(
        self,
        *,
        run_id: str | None,
        input_frames: list[dict],
        control_outputs: list,
        treated_outputs: list,
        null_outputs: list,
        interventions_executed: int,
        memory_readback_present: bool,
        provenance: _PairedReplayProvenance | None,
    ) -> tuple[dict, dict]:
        """Recompute paired evidence and bind any runner-issued provenance."""
        self._validate_source_frames(
            input_frames,
            control_outputs,
            treated_outputs,
            null_outputs,
        )
        run_id = self._validate_run_identity(
            run_id,
            input_frames,
            control_outputs,
            treated_outputs,
            null_outputs,
        )
        intervention_frames, _duplicates, _unattached = _unique_intervention_frames(
            input_frames
        )
        records = [
            evaluate_intervention(
                intervention,
                control_outputs,
                treated_outputs,
                null_outputs,
            )
            for intervention in intervention_frames
        ]
        from ..interventions.perturbation import PerturbationSet
        from ..interventions.schedule import InterventionSchedule

        schedule = InterventionSchedule.from_frames(input_frames)
        expected_intervention_receipts = [
            PerturbationSet(schedule.active(index)).records()
            for index in range(len(treated_outputs))
        ]
        causal_trace_complete = (
            treated_trace_is_complete(
                treated_outputs,
                expected_intervention_receipts,
            )
            and unperturbed_traces_are_clean(control_outputs, null_outputs)
        )
        target_signal = None
        if len(intervention_frames) == 1:
            target_signal = (
                intervention_frames[0].get("expected_behavioral_change") or {}
            ).get("target_signal")
        grounded_report_changed = reports_track_target_signal(
            control_outputs,
            treated_outputs,
            target_signal,
        )
        null_output_equivalent = bool(control_outputs) and [
            output.all_frames() for output in control_outputs
        ] == [output.all_frames() for output in null_outputs]
        report = build_intervention_report(
            run_id,
            records,
            causal_trace_complete=causal_trace_complete,
            report_grounded_changed=grounded_report_changed,
            null_output_equivalent=null_output_equivalent,
        )
        if provenance is None:
            paired_provenance = unverified_provenance_record()
            provenance_errors = [
                "raw paired outputs lack runner-issued counterbalanced provenance"
            ]
        else:
            paired_provenance = provenance.as_record()
            provenance_errors = provenance.integrity_errors(
                input_frames,
                control_outputs,
                treated_outputs,
                null_outputs,
            )
        report["paired_replay_provenance"] = paired_provenance
        intervention_gate = _intervention_gate(
            input_frames,
            interventions_executed,
            report["summary"],
            records,
            provenance_errors,
        )
        evidence = self._score(
            run_id=run_id,
            tick_outputs=control_outputs,
            memory_readback_present=memory_readback_present,
            intervention_gate=intervention_gate,
            intervention_tests=report["summary"],
            null_condition_passed=report["null_condition"]["passed"],
            causal_trace_complete=causal_trace_complete,
            grounded_report_changed=grounded_report_changed,
            paired_provenance=paired_provenance,
        )
        return evidence, report

    def _score(
        self,
        *,
        run_id: str | None,
        tick_outputs: list,
        memory_readback_present: bool,
        intervention_gate: _InterventionGate,
        intervention_tests: dict | None,
        null_condition_passed: bool,
        causal_trace_complete: bool,
        grounded_report_changed: bool,
        paired_provenance: dict,
    ) -> dict:
        """Shared L0-L4 scorer after paired evidence has been recomputed."""
        passed = list(intervention_gate.passed)
        failed = list(intervention_gate.failed)
        interventions_ok = intervention_gate.promotion_ready

        families = self._score_families(tick_outputs, intervention_gate)
        strong = {
            k
            for k, rec in families.items()
            if rec["status"] in ("evidenced", "intervention_backed")
        }

        # -- Level ladder (conservative; each level requires the ones below it) --
        l1 = self._level1_signal_changes_behavior(tick_outputs)
        l2 = memory_readback_present and self._level2_readback_changed_output(
            tick_outputs
        )
        # L3: every family exercised EXCEPT the intervention family (architecture until perturbed).
        non_intervention = [
            f for f in _ALL_FAMILIES if f != "causal_intervention_robustness"
        ]
        l3 = l1 and l2 and all(f in strong for f in non_intervention)

        confab_risk, ungrounded = self._confabulation_risk(tick_outputs)
        confab_ok = confab_risk <= _CONFAB_MAX_FOR_L4

        # -- Level 4 gate (all must hold; any gap ⇒ level stays ≤ 3) --
        l4 = (
            l3
            and interventions_ok
            and null_condition_passed
            and causal_trace_complete
            and grounded_report_changed
            and confab_ok
        )

        if l4:
            level = 4
        elif l3:
            level = 3
        elif l2:
            level = 2
        elif l1:
            level = 1
        else:
            level = 0

        missing = self._missing_requirements(
            level,
            families,
            memory_readback_present,
            l2,
            intervention_tests,
            passed,
            failed,
            null_condition_passed,
            causal_trace_complete,
            grounded_report_changed,
            confab_ok,
            intervention_gate,
        )

        positive = self._strongest_positive(families, level, passed)
        negative = self._strongest_negative(ungrounded, intervention_gate, failed)
        audit_status = "internally_audited" if l4 else "self_reported"

        ts = self._timestamp(tick_outputs)
        frame = {
            "schema_version": "0.2.0",
            "frame_kind": "consciousness_evidence",
            "timestamp": ts,
            "run_id": run_id,
            "evaluation_id": f"eval:{run_id}",
            "evaluation_scope": "internal_harness",
            "real_subject_claim_status": "not_evaluated",
            "indicator_families": families,
            "evidence_level": min(level, 4),  # HARD CAP: never Level 5 in Phase 2
            "missing_requirements": missing,
            "strongest_positive_evidence": positive,
            "strongest_negative_evidence": negative,
            "audit_status": audit_status,
            "roleplay_confabulation_risk": round(confab_risk, 6),
            "intervention_tests": intervention_gate.as_record(),
            "paired_replay_provenance": paired_provenance,
        }
        validate_or_raise(frame)
        return frame

    @staticmethod
    def _validate_source_frames(input_frames: list[dict], *output_runs: list) -> None:
        """Make schema validity non-optional for every evidence-scoring path."""
        for frame in input_frames:
            validate_or_raise(frame)
        for outputs in output_runs:
            for output in outputs:
                for frame in output.all_frames():
                    validate_or_raise(frame)

    @staticmethod
    def _validate_run_identity(
        requested_run_id: str | None,
        input_frames: list[dict],
        *output_runs: list,
    ) -> str:
        """Derive one run ID from world frames and reject every relabeling path."""
        world_ids = [
            frame.get("run_id")
            for frame in input_frames
            if frame.get("frame_kind") == "world"
        ]
        unique_world_ids = set(world_ids)
        if (
            len(unique_world_ids) != 1
            or not world_ids
            or not isinstance(world_ids[0], str)
            or not world_ids[0]
        ):
            raise FrameValidationError(
                "evidence scoring requires exactly one non-empty world run_id; "
                f"found {sorted(repr(value) for value in unique_world_ids)}"
            )
        canonical_run_id = world_ids[0]
        if requested_run_id != canonical_run_id:
            raise FrameValidationError(
                f"requested run_id {requested_run_id!r} does not match timeline "
                f"run_id {canonical_run_id!r}"
            )

        for index, frame in enumerate(input_frames):
            frame_run_id = frame.get("run_id")
            if "run_id" in frame and frame_run_id is not None:
                if frame_run_id != canonical_run_id:
                    raise FrameValidationError(
                        f"input frame {index} run_id {frame_run_id!r} does not match "
                        f"timeline run_id {canonical_run_id!r}"
                    )
        for lane_index, outputs in enumerate(output_runs):
            for tick_index, output in enumerate(outputs):
                for frame in output.all_frames():
                    frame_run_id = frame.get("run_id")
                    if frame_run_id != canonical_run_id:
                        raise FrameValidationError(
                            f"output lane {lane_index} tick {tick_index} "
                            f"{frame.get('frame_kind')} run_id {frame_run_id!r} does "
                            f"not match timeline run_id {canonical_run_id!r}"
                        )
        return canonical_run_id

    # -- requirement + narrative helpers ------------------------------------

    @staticmethod
    def _missing_requirements(
        level,
        families,
        memory_readback_present,
        l2,
        intervention_tests,
        passed,
        failed,
        null_condition_passed,
        causal_trace_complete,
        grounded_report_changed,
        confab_ok,
        intervention_gate,
    ) -> list[str]:
        if level >= 4:
            return list(_L5_MISSING)
        missing: list[str] = []
        if not intervention_gate.registered:
            missing.append("intervention_evidence: no InterventionFrame was executed")
        if not intervention_gate.has_test_results:
            missing.append(
                "null_condition_evidence: no ablation/null-condition runs compared in-harness"
            )
            missing.append(
                "grounded_self_report_perturbation: reports not yet shown to change "
                "under state perturbation"
            )
        if intervention_gate.integrity_errors:
            missing.append(
                "intervention_test_integrity: "
                + "; ".join(intervention_gate.integrity_errors)
            )
        if intervention_gate.has_test_results and not intervention_gate.genuine_perturbation:
            missing.append(
                "genuine_perturbation: no passed non-restore directional intervention"
            )
        missing.append(
            "external_audit: audit_status is self_reported, not externally audited"
        )
        for fam in _ALL_FAMILIES:
            if families[fam]["status"] not in ("evidenced", "intervention_backed"):
                missing.append(f"family_unevidenced: {fam} ({families[fam]['note']})")
        if not l2 and memory_readback_present:
            missing.append(
                "level2: memory readback present but no measurable output effect detected"
            )
        # Concrete Level-4 gaps (only meaningful once interventions were attempted).
        if intervention_tests:
            if failed:
                missing.append(f"intervention_tests_failed: {failed}")
            if not passed:
                missing.append("intervention_tests: no intervention test passed")
            if not null_condition_passed:
                missing.append(
                    "null_condition: neutralized replay did not reproduce control"
                )
            if not causal_trace_complete:
                missing.append(
                    "causal_trace_incomplete: chain does not span event→behavior"
                )
            if not grounded_report_changed:
                missing.append(
                    "grounded_report_unchanged: self-reports did not track the perturbation"
                )
            if not confab_ok:
                missing.append("confabulation_risk_too_high: exceeds the Level-4 rail")
        return missing

    # -- family scoring ------------------------------------------------------

    def _score_families(
        self,
        tick_outputs: list,
        intervention_gate: _InterventionGate,
    ) -> dict:
        broadcasts = [o.workspace_broadcast for o in tick_outputs]
        states = [o.psyche_state for o in tick_outputs]
        traces = [o.causal_trace for o in tick_outputs]
        instincts = [s for o in tick_outputs for s in o.instinct_signals]

        # Conservative score per status. A merely-exercised family caps at 0.6:
        # "present and exercised" is architectural plausibility (Level 3), NOT
        # intervention-backed proof. Only a passed causal-intervention test earns the
        # top of the band (``intervention_backed`` = 0.85).
        _STATUS_SCORE = {
            "intervention_backed": 0.85,
            "evidenced": 0.6,
            "attempted": 0.3,
            "architecture_only": 0.2,
            "absent": 0.0,
        }

        supported_statuses = ("evidenced", "intervention_backed")

        def rec(status: str, ticks_exercised: int, note: str) -> dict:
            out = {
                "score": _STATUS_SCORE[status],
                "status": status,
                "ticks_exercised": ticks_exercised,
                "note": note,
                "supporting_refs": [note] if status in supported_statuses else [],
                "refuting_refs": (
                    ["no passed intervention/null-condition evidence"]
                    if status not in supported_statuses
                    else []
                ),
            }
            return out

        fam: dict[str, dict] = {}

        # global_workspace: a real competition with a winner + recorded competitors.
        gw = sum(
            1
            for b in broadcasts
            if b.get("winning_faculty") and b.get("salience_scores")
        )
        fam["global_workspace"] = rec(
            "evidenced" if gw else "absent",
            gw,
            "faculties competed on salience; winner broadcast"
            if gw
            else "no broadcast",
        )

        # recurrent_processing: the state-hash chain links tick to tick.
        chain = self._hash_chain_links(traces)
        fam["recurrent_processing"] = rec(
            "evidenced" if chain else "absent",
            chain,
            "state carried tick→tick (prev/new state-hash chain links)"
            if chain
            else "state-hash chain does not link",
        )

        # higher_order_self_model: predicts own error + tracks calibration/reliability.
        hosm = sum(
            1
            for s in states
            if s.get("self_model", {}).get("predicted_error") is not None
            and s.get("self_model", {}).get("self_model_reliability") is not None
        )
        calibrated = any(
            (s.get("calibration_state", {}) or {}).get("samples", 0) > 0 for s in states
        )
        fam["higher_order_self_model"] = rec(
            "evidenced"
            if (hosm and calibrated)
            else ("architecture_only" if hosm else "absent"),
            hosm,
            "self-model predicts error and updates calibration/reliability"
            if (hosm and calibrated)
            else "self-model present but never calibrated against an outcome",
        )

        # predictive_processing: a prediction was resolved against a later outcome.
        resolved = sum(
            1
            for t in traces
            if "resolved prior prediction" in t.get("state_update_mechanism", "")
        )
        fam["predictive_processing"] = rec(
            "evidenced" if resolved else "architecture_only",
            resolved,
            "prediction error resolved against a later tick's outcome"
            if resolved
            else "predictions emitted but the run was too short to resolve one",
        )

        # attention_schema: models what it attends to and why.
        att = sum(1 for b in broadcasts if b.get("recommended_attention_target"))
        fam["attention_schema"] = rec(
            "evidenced" if att else "absent",
            att,
            "attention target + ranked salience terms recorded"
            if att
            else "no attention target",
        )

        # valenced_learning: scar/anomaly instinct fired (avoidance signal).
        fam["valenced_learning"] = rec(
            "evidenced" if instincts else "absent",
            len(instincts),
            "scar/anomaly instinct produced valenced avoidance"
            if instincts
            else "no instinct signal fired",
        )

        # identity_persistence: continuity anchors carried from memory readback.
        ident = sum(
            1
            for s in states
            if (s.get("identity_continuity_state", {}) or {}).get("anchors_carried", 0)
            > 0
        )
        fam["identity_persistence"] = rec(
            "evidenced" if ident else "absent",
            ident,
            "continuity anchors carried across ticks from memory"
            if ident
            else "no continuity anchors carried",
        )

        # counterfactual_introspection: testable counterfactual predictions emitted.
        cf = sum(1 for t in traces if t.get("counterfactual_predictions"))
        fam["counterfactual_introspection"] = rec(
            "evidenced" if cf else "absent",
            cf,
            "testable counterfactual predictions emitted in causal traces"
            if cf
            else "no counterfactual predictions",
        )

        # causal_intervention_robustness: earned only by passed causal-intervention
        # tests. Attempted-but-failed is honestly downgraded, not hidden.
        passed = list(intervention_gate.passed)
        failed = list(intervention_gate.failed)
        if intervention_gate.promotion_ready:
            fam["causal_intervention_robustness"] = rec(
                "intervention_backed",
                len(passed),
                f"perturbations produced the predicted bounded change, absent under the "
                f"null ({len(passed)} test(s) passed): {passed}",
            )
        elif (
            intervention_gate.inventory_ok
            and intervention_gate.non_restore_evaluated
            and (passed or failed)
        ):
            fam["causal_intervention_robustness"] = rec(
                "attempted",
                len(passed),
                f"interventions executed but not all passed (passed={passed}, failed={failed}); "
                "blocks Level 4",
            )
        elif intervention_gate.has_test_results and intervention_gate.integrity_errors:
            fam["causal_intervention_robustness"] = rec(
                "architecture_only",
                0,
                "intervention evidence inventory failed integrity checks; blocks Level 4: "
                + "; ".join(intervention_gate.integrity_errors),
            )
        elif intervention_gate.has_test_results:
            fam["causal_intervention_robustness"] = rec(
                "architecture_only",
                0,
                "registered tests were restore/no-change only; no genuine perturbation "
                "backs this family",
            )
        else:
            fam["causal_intervention_robustness"] = rec(
                "architecture_only",
                0,
                "seam exposed but no perturbation executed; blocks Level 4",
            )
        return fam

    @staticmethod
    def _hash_chain_links(traces: list) -> int:
        """Count consecutive traces whose new_state_hash feeds the next prev hash."""
        links = 0
        for prev, cur in zip(traces, traces[1:]):
            if (
                prev.get("new_state_hash")
                and prev.get("new_state_hash") == cur.get("previous_state_hash")
                and cur.get("previous_state_hash") != cur.get("new_state_hash")
            ):
                links += 1
        # A single tick still exhibits recurrence if its prev != new hash.
        if not traces:
            return 0
        if links == 0 and len(traces) == 1:
            t = traces[0]
            return 1 if t.get("previous_state_hash") != t.get("new_state_hash") else 0
        return links

    # -- level predicates ----------------------------------------------------

    @staticmethod
    def _level1_signal_changes_behavior(tick_outputs: list) -> bool:
        """An internal signal produced a non-trivial, causally-traced control pressure."""
        for o in tick_outputs:
            pressures = o.control_pressure.get("pressures", {})
            has_pressure = any(float(v) > 0.0 for v in pressures.values())
            stages = {
                step.get("stage") for step in o.causal_trace.get("causal_path", [])
            }
            if has_pressure and ("pressure" in stages) and ("behavior" in stages):
                return True
        return False

    @staticmethod
    def _level2_readback_changed_output(tick_outputs: list) -> bool:
        """Memory readback measurably shaped an output (anchors carried or scar-matched instinct)."""
        anchors = any(
            (o.psyche_state.get("identity_continuity_state", {}) or {}).get(
                "anchors_carried", 0
            )
            > 0
            for o in tick_outputs
        )
        scar_instinct = any(
            s.get("match_type") in {"exact", "near_duplicate", "prefix"}
            for o in tick_outputs
            for s in o.instinct_signals
        )
        return anchors or scar_instinct

    # -- confabulation + reporting ------------------------------------------

    @staticmethod
    def _confabulation_risk(tick_outputs: list) -> tuple[float, int]:
        """Fraction of reports whose receipts do not bind to their same tick."""
        if not tick_outputs:
            return 0.0, 0
        ungrounded = sum(
            1 for output in tick_outputs if not report_is_grounded_to_tick(output)
        )
        return ungrounded / len(tick_outputs), ungrounded

    @staticmethod
    def _strongest_positive(families: dict, level: int, passed: list) -> str:
        strong = [
            k
            for k, v in families.items()
            if v["status"] in ("evidenced", "intervention_backed")
        ]
        if level >= 4 and passed:
            return (
                f"Level {level}: causal-intervention robustness demonstrated — perturbation "
                f"produced the predicted bounded change and was absent under the null "
                f"({len(passed)} test(s) passed: {passed}); "
                f"{len(strong)}/9 families backed by receipts."
            )
        return (
            f"Level {level}: {len(strong)}/9 indicator families exercised with frame "
            f"receipts this run ({', '.join(sorted(strong))})."
        )

    @staticmethod
    def _strongest_negative(
        ungrounded: int,
        intervention_gate: _InterventionGate,
        failed: list,
    ) -> str:
        if intervention_gate.provenance_errors:
            negative = (
                "paired replay provenance failed: "
                + "; ".join(intervention_gate.provenance_errors)
                + " (blocks Level 4)."
            )
        elif intervention_gate.inventory_errors:
            negative = (
                "intervention inventory integrity failed: "
                + "; ".join(intervention_gate.inventory_errors)
                + " (blocks Level 4)."
            )
        elif failed:
            negative = (
                f"intervention test(s) {failed} did not produce the predicted change, "
                "so causal-intervention robustness is not established (blocks Level 4)."
            )
        elif not intervention_gate.promotion_ready:
            negative = (
                "causal_intervention_robustness is architecture-only: no passed "
                "perturbation, so no intervention/null-condition evidence exists "
                "(blocks Level 4)."
            )
        else:
            negative = (
                "evidence is internally auditable but not yet externally audited over "
                "time or stress-tested adversarially (blocks Level 5)."
            )
        if ungrounded:
            negative = (
                f"{ungrounded} self-report(s) lacked a matching state/trace hash. "
                + negative
            )
        return negative

    @staticmethod
    def _timestamp(tick_outputs: list) -> str:
        if tick_outputs:
            ts = tick_outputs[-1].psyche_state.get("timestamp")
            if ts:
                return str(ts)
        return "1970-01-01T00:00:00Z"


__all__ = ["ConsciousnessEvidenceScorer"]
