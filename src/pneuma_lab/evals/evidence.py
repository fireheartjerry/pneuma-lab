"""ConsciousnessEvidenceScorer — honest, conservative Level 0-3 scoring.

This scorer reads a whole replay's output frames and decides an ``evidence_level``
using the ladder in ``docs/consciousness-levels.md``. It is built to *under*-claim:

    * a family counts as evidenced only if a real frame receipt exists for it —
    architecture without a receipt drops to unevidenced (Layer B / "no receipts,
    no claim");
    * it NEVER promotes on self-report; ``roleplay_confabulation_risk`` is
    computed by checking every grounded self-report's hashes against the run log,
    not from how the prose reads;
    * it HARD-CAPS at Level 3. Level 4 needs intervention + null-condition
    evidence, which Phase 1 never produces (``interventions_executed == 0``), so
    the L4 requirements always appear in ``missing_requirements``.

The nine indicator families map to the mechanisms ``ReferencePsyche`` exercises;
``causal_intervention_robustness`` is the one family that is architecture-only in
Phase 1 and is reported as such.
"""

from __future__ import annotations

# The Level-4 evidence that a passive (no-intervention) run structurally cannot provide.
_L4_MISSING = [
    "intervention_evidence: no InterventionFrame was executed",
    "null_condition_evidence: no ablation/null-condition runs compared in-harness",
    "grounded_self_report_perturbation: reports not yet shown to change under state perturbation",
    "external_audit: audit_status is self_reported, not externally audited",
]

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


class ConsciousnessEvidenceScorer:
    """Score a replay's output frames into a Level 0-3 ConsciousnessEvidenceFrame."""

    def score(
        self,
        *,
        run_id: str | None,
        input_frames: list[dict],
        tick_outputs: list,
        interventions_executed: int,
        memory_readback_present: bool,
        intervention_tests: dict | None = None,
        null_condition_passed: bool = False,
        causal_trace_complete: bool = False,
        grounded_report_changed: bool = False,
    ) -> dict:
        # Intervention test results (supplied only by the paired runner). A single
        # replay passes ``intervention_tests=None`` and therefore can never reach L4.
        passed = list((intervention_tests or {}).get("passed", []))
        failed = list((intervention_tests or {}).get("failed", []))
        interventions_ok = bool(intervention_tests) and bool(passed) and not failed

        families = self._score_families(tick_outputs, intervention_tests)
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
        )

        positive = self._strongest_positive(families, level, passed)
        negative = self._strongest_negative(
            families, ungrounded, interventions_ok, failed
        )
        audit_status = "internally_audited" if interventions_ok else "self_reported"

        ts = self._timestamp(tick_outputs)
        return {
            "schema_version": "0.1.0",
            "frame_kind": "consciousness_evidence",
            "timestamp": ts,
            "run_id": run_id,
            "evaluation_id": f"eval:{run_id}",
            "indicator_families": families,
            "evidence_level": min(level, 4),  # HARD CAP: never Level 5 in Phase 2
            "missing_requirements": missing,
            "strongest_positive_evidence": positive,
            "strongest_negative_evidence": negative,
            "audit_status": audit_status,
            "roleplay_confabulation_risk": round(confab_risk, 6),
            "intervention_tests": {"passed": passed, "failed": failed},
        }

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
    ) -> list[str]:
        if level >= 4:
            return list(_L5_MISSING)
        missing = list(_L4_MISSING)
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
        self, tick_outputs: list, intervention_tests: dict | None
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
        passed = list((intervention_tests or {}).get("passed", []))
        failed = list((intervention_tests or {}).get("failed", []))
        if intervention_tests and passed and not failed:
            fam["causal_intervention_robustness"] = rec(
                "intervention_backed",
                len(passed),
                f"perturbations produced the predicted bounded change, absent under the "
                f"null ({len(passed)} test(s) passed): {passed}",
            )
        elif intervention_tests and (passed or failed):
            fam["causal_intervention_robustness"] = rec(
                "attempted",
                len(passed),
                f"interventions executed but not all passed (passed={passed}, failed={failed}); "
                "blocks Level 4",
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
        """Fraction of self-reports not grounded in a real state + trace hash."""
        state_hashes = {o.psyche_state.get("state_hash") for o in tick_outputs}
        trace_ids = {o.causal_trace.get("trace_id") for o in tick_outputs}
        reports = [o.grounded_self_report for o in tick_outputs]
        if not reports:
            return 0.0, 0
        ungrounded = 0
        for r in reports:
            grounded = (
                r.get("affect_state_hash") in state_hashes
                and r.get("causal_trace_id") in trace_ids
            )
            if not grounded:
                ungrounded += 1
        return ungrounded / len(reports), ungrounded

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
        families: dict, ungrounded: int, interventions_ok: bool, failed: list
    ) -> str:
        if failed:
            negative = (
                f"intervention test(s) {failed} did not produce the predicted change, "
                "so causal-intervention robustness is not established (blocks Level 4)."
            )
        elif not interventions_ok:
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
