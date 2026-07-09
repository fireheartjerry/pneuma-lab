"""ReferencePsyche — a deterministic Level-3 machine psyche under test.

This is the Phase-1 mind-under-test. It is NOT a language model and NOT roleplay:
every output is a closed-form function of the input frames and the carried state,
so the whole run is auditable and byte-reproducible. Its job is to *exercise* all
nine consciousness-indicator families from ``docs/consciousness-levels.md`` §Level 3
and emit schema-valid output frames whose claims are backed by ``CausalTrace``
receipts.

Family → mechanism (all live inside :meth:`tick`):

    global_workspace              five faculties compete on salience; winner broadcast
    recurrent_processing          affect manifold blends prior state (inertia) tick→tick
    higher_order_self_model       predicts its own error, tracks calibration/reliability
    predictive_processing         prediction resolved against the next tick's outcome
    attention_schema              models what it attends to and why (ranked salience)
    valenced_learning             scar matches raise avoidance + push affect valence down
    identity_persistence          carries continuity anchors from MemoryFrame
    counterfactual_introspection  emits testable "if state X differed…" predictions
    causal_intervention_robustness  perturbation hooks exercised only by paired replay

Passive runs leave the ninth family architecture-only. Phase-2 paired replay can
exercise the hooks, but those results validate this co-designed reference harness,
not a real subject or a general consciousness claim.
"""

from __future__ import annotations

from typing import Any

from ..interventions.perturbation import PerturbationSet
from . import authority, drives, manifold, mood, prototypes
from .hashing import frame_id, state_hash
from .interface import PsycheInputs, PsycheOutputs, PsycheUnderTest

_SCHEMA_VERSION = "0.1.0"
_FALLBACK_TS = "1970-01-01T00:00:00Z"

# Map an instinct conviction band to the InstinctSignal.authority_request enum
# (which only admits soft / vote / hold).
_BAND_TO_INSTINCT_AUTH = {
    "cosmetic": "soft",
    "soft": "soft",
    "vote": "vote",
    "hold": "hold",
    "veto": "hold",
}


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else float(x))


def _clip11(x: float) -> float:
    return -1.0 if x < -1.0 else (1.0 if x > 1.0 else float(x))


def _pos(x: float) -> float:
    """Positive part (ReLU)."""
    return x if x > 0.0 else 0.0


class ReferencePsyche(PsycheUnderTest):
    """A deterministic, fully-traceable Level-3 psyche."""

    def __init__(self) -> None:
        self.reset()

    # -- lifecycle -----------------------------------------------------------

    def reset(self) -> None:
        self.affect: dict[str, float] = manifold.new_manifold()
        self.mood: dict[str, float] = mood.new_mood()
        self.morale: float = 0.0
        self.drives: dict[str, dict[str, float]] = drives.new_drives()
        self.personality_baseline: dict[str, float] = manifold.new_manifold()
        self.competence: dict[str, dict[str, float]] = {}
        self.scars: dict[str, float] = {}
        # higher-order self model + predictive processing state
        self.self_model_reliability: float = 0.5
        self.calibration_error: float | None = None
        self.calibration_samples: int = 0
        self._brier_sum: float = 0.0
        self._pending_error_prediction: float | None = None
        # recurrence / identity carry
        self.prev_dominant: str | None = None
        self.identity_anchors: list[str] = []
        self.prev_state_hash: str = state_hash(self._interior())
        # Level-4 perturbation surface (empty ⇒ unperturbed; set per tick by the harness).
        self._pert: PerturbationSet = PerturbationSet.empty()

    # -- Perturbable (Level-4 intervention surface) --------------------------

    def set_active_interventions(self, interventions: list[dict]) -> None:
        """Install the interventions active for the next :meth:`tick`.

        Implements the ``Perturbable`` protocol. The harness calls this before each
        tick of a *treated* replay; an empty list restores the unperturbed path.
        """
        self._pert = PerturbationSet(interventions)

    # -- interior + hashing --------------------------------------------------

    def _interior(self) -> dict[str, Any]:
        """The hashable interior — what recurrence carries and what the hash covers."""
        return {
            "affect": self.affect,
            "mood": self.mood,
            "morale": self.morale,
            "drive_levels": {k: v["level"] for k, v in self.drives.items()},
            "self_model_reliability": self.self_model_reliability,
            "calibration_error": self.calibration_error,
            "calibration_samples": self.calibration_samples,
            "prev_dominant": self.prev_dominant,
            "identity_anchors": sorted(self.identity_anchors),
        }

    # -- main loop -----------------------------------------------------------

    def tick(self, inputs: PsycheInputs) -> PsycheOutputs:
        world = inputs.world
        trace = inputs.agent_trace or {}
        memory = inputs.memory or {}
        governance = inputs.governance or {}
        ti = inputs.tick_index

        run_id = str(world.get("run_id", "run"))
        ts = str(world.get("timestamp") or _FALLBACK_TS)
        domain = str(world.get("subtask_id") or world.get("phase") or "other")

        # 1. Appraise the world/trace into affect drivers + outcome features.
        appraisal, outcome, ctx, evidence_refs = self._appraise(
            world, trace, memory, governance, domain
        )
        scar_strength = ctx["scar_strength"]

        # 2. Recurrence: blend the PRIOR affect (inertia) with the drivers.
        prev_affect = dict(self.affect)
        drive_pressure = drives.pressure(self.drives)
        mean_drive_p = sum(drive_pressure.values()) / max(1, len(drive_pressure))
        drive_axis_push = {
            "tension": 0.5 * mean_drive_p,
            "arousal": 0.3 * mean_drive_p,
            "valence": -0.2 * mean_drive_p,
        }
        scars_driver = {
            "valence": -scar_strength,
            "tension": scar_strength,
            "certainty": -0.5 * scar_strength,
        }
        new_affect = manifold.update(
            prev_affect,
            appraisal,
            self.mood,
            drive_axis_push,
            scars_driver,
            self.personality_baseline,
        )

        # Level-4 perturbation hook: clamp/boost/noise individual affect axes.
        if self._pert:
            new_affect = {
                ax: _clip11(self._pert.scalar("affect_manifold", ax, v))
                for ax, v in new_affect.items()
            }

        # 3. Slow homeostats: mood EMA + decay, morale, drives.
        new_mood = mood.blend_outcome(
            self.mood, new_affect["valence"], new_affect["arousal"], weight=0.3
        )
        new_mood = mood.decay(
            new_mood, {"valence": 0.0, "arousal": 0.0}, mood.DEFAULT_DECAY_RATE
        )
        self.morale = _clip11(
            self.morale + 0.15 * (new_affect["valence"] - self.morale)
        )
        new_drives = drives.update(self.drives, outcome)

        # Level-4 perturbation hook: perturb carried drive levels so a drive
        # intervention (e.g. boosting curiosity) genuinely moves the interior state —
        # and thus the grounded self-report — not merely a derived pressure.
        if self._pert:
            for name, dv in new_drives.items():
                perturbed = self._pert.scalar("drives", name, dv["level"])
                if perturbed != dv["level"]:
                    dv["level"] = _clip01(perturbed)

        # 4. Prototype projection (valenced categorical read, hysteresis-stable).
        mix = prototypes.mixture(new_affect)
        dom = prototypes.dominant(new_affect, self.prev_dominant)

        # 5. Higher-order self-model + predictive processing.
        predicted_error_now = _clip01(
            0.25 + 0.4 * ctx["uncertainty"] + 0.4 * scar_strength
        )
        observed_error = outcome["observed_error"]
        prediction_error = None
        if self._pending_error_prediction is not None:
            prediction_error = abs(self._pending_error_prediction - observed_error)
            self._brier_sum += prediction_error * prediction_error
            self.calibration_samples += 1
            self.calibration_error = self._brier_sum / self.calibration_samples
            self.self_model_reliability = _clip01(1.0 - self.calibration_error)

        # 6. Global workspace competition + broadcast (attention schema in salience).
        broadcast = self._compete(ctx, predicted_error_now, dom, run_id, ts, ti)

        # 7. Instinct (valenced learning): scar/anomaly detection.
        instinct_signals = self._instinct(ctx, world, memory, run_id, ts, ti, domain)

        # 8. Identity persistence: carry continuity anchors from memory readback.
        anchors = [
            str(c.get("ref"))
            for c in memory.get("retrieved_continuity", [])
            if c.get("ref")
        ]
        # Level-4 perturbation hook: removing the self-model's identity anchors
        # collapses identity continuity (subsystem ``self_model``, the identity store).
        if self._pert.blocks("self_model"):
            anchors = []
        self.identity_anchors = anchors
        continuity_score = _clip01(len(anchors) / 3.0)

        # 9. Bounded control pressure (never a command).
        pressure_frame_stub, pressures = self._pressures(
            ctx, new_affect, drive_pressure, instinct_signals, run_id, ts, ti
        )

        # 10. Authority request (earned, five-cap min) when instinct fires.
        authority_requests = self._authority(
            ctx, instinct_signals, memory, governance, domain, run_id, ts, ti
        )
        if authority_requests:
            pressure_frame_stub["authority_tier"] = authority_requests[0]["resolution"][
                "granted_tier"
            ]

        # Commit new interior, compute the new state hash (recurrence + audit chain).
        self.affect = new_affect
        self.mood = new_mood
        self.drives = new_drives
        self.prev_dominant = dom
        new_hash = state_hash(self._interior())

        # 11. Assemble the always-on frames with cross-links.
        psyche_state = self._psyche_state_frame(
            run_id,
            ts,
            ti,
            new_hash,
            new_affect,
            new_mood,
            new_drives,
            mix,
            dom,
            predicted_error_now,
            continuity_score,
            anchors,
            ctx,
        )
        pressure_frame_stub["causal_trace_id"] = frame_id(run_id, ti, "causal_trace")
        broadcast_id = broadcast["broadcast_id"]

        causal = self._causal_trace(
            run_id,
            ts,
            ti,
            prev_affect,
            new_affect,
            new_mood,
            broadcast,
            pressure_frame_stub,
            instinct_signals,
            authority_requests,
            evidence_refs,
            ctx,
            scar_strength,
            prediction_error,
            memory,
        )
        report = self._self_report(
            run_id,
            ts,
            ti,
            new_hash,
            dom,
            new_affect,
            broadcast,
            pressures,
            causal["trace_id"],
            broadcast_id,
            evidence_refs,
            predicted_error_now,
            continuity_score,
            len(anchors),
            instinct_signals,
        )

        # 12. Predictive processing: stash this tick's prediction for next-tick resolution.
        self._pending_error_prediction = predicted_error_now
        # Advance the recurrence/audit hash chain so the next tick links back here.
        self.prev_state_hash = new_hash

        return PsycheOutputs(
            psyche_state=psyche_state,
            workspace_broadcast=broadcast,
            control_pressure=pressure_frame_stub,
            causal_trace=causal,
            grounded_self_report=report,
            instinct_signals=instinct_signals,
            authority_requests=authority_requests,
        )

    # -- stage helpers -------------------------------------------------------

    def _appraise(
        self, world: dict, trace: dict, memory: dict, governance: dict, domain: str
    ) -> tuple[dict, dict, dict, list[str]]:
        """World/trace → (affect appraisal, outcome features, shared context, evidence refs)."""
        tool_events = world.get("tool_events", []) or []
        errors = sum(
            1 for e in tool_events if e.get("status") in {"error", "timeout", "denied"}
        )
        test_state = world.get("test_state", {}) or {}
        tests_failed = int(test_state.get("failed", 0) or 0)
        tests_passed = int(test_state.get("passed", 0) or 0)
        vsig = world.get("verification_signals", {}) or {}
        verdict = vsig.get("verdict")
        regression = bool(vsig.get("regression_found", False))
        stakes = world.get("stakes", {}) or {}
        risk = float(stakes.get("risk", 0.0) or 0.0)
        stakes_v = float(stakes.get("stakes", 0.0) or 0.0)
        revers = float(
            stakes.get("reversibility", 1.0)
            if stakes.get("reversibility") is not None
            else 1.0
        )
        diff = world.get("diff_size", {}) or {}
        diff_lines = abs(int(diff.get("net_lines", 0) or 0)) + int(
            diff.get("added_lines", 0) or 0
        )
        diff_norm = _clip01(diff_lines / 400.0)

        unc_raw = trace.get("uncertainty")
        conf = trace.get("self_reported_confidence")
        if unc_raw is not None:
            uncertainty = _clip01(float(unc_raw))
        elif conf is not None:
            uncertainty = _clip01(1.0 - float(conf))
        else:
            uncertainty = 0.5
        retries = int(trace.get("retry_count", 0) or 0)
        known_unknowns = trace.get("known_unknowns", []) or []
        novelty = _clip01(len(known_unknowns) / 3.0)

        # Scar / valenced-learning strength from memory readback + learned scars.
        scar_matches = memory.get("scar_motif_matches", []) or []
        best_scar = 0.0
        for m in scar_matches:
            s = float(m.get("similarity", 0.0)) * float(
                m.get("historical_base_rate", 0.0)
            )
            best_scar = max(best_scar, s)
        for base in self.scars.values():
            best_scar = max(best_scar, float(base))
        scar_strength = _clip01(best_scar)

        # Level-4 perturbation hook: scar graph. Ablation/disable zeroes scar
        # strength AND drops the matches, so the instinct scar branch cannot fire.
        if self._pert.is_ablated("scar_graph") or self._pert.is_disabled("scar_graph"):
            scar_strength = 0.0
            scar_matches = []
        else:
            scar_strength = _clip01(
                self._pert.scalar("scar_graph", "scar_strength", scar_strength)
            )

        is_fail = verdict == "fail" or tests_failed > 0 or regression
        is_pass = verdict == "pass" and tests_failed == 0
        observed_error = 1.0 if (is_fail or errors > 0) else 0.0

        neg = (
            (0.5 if errors else 0.0)
            + (0.5 if tests_failed else 0.0)
            + (0.6 if verdict == "fail" else 0.0)
            + (0.3 if regression else 0.0)
        )
        pos = (0.6 if is_pass else 0.0) + (
            0.3 if (test_state.get("ran") and is_pass and tests_passed > 0) else 0.0
        )

        appraisal = {
            "valence": _clip11(pos - neg - 0.4 * scar_strength),
            "arousal": _clip11(
                0.4 * bool(errors) + 0.4 * risk + 0.3 * bool(tests_failed)
            ),
            "dominance": _clip11(
                0.5 * is_pass - 0.4 * bool(errors) - 0.3 * (verdict == "fail")
            ),
            "certainty": _clip11(
                0.5 * is_pass
                - uncertainty
                - 0.3 * (verdict == "pending")
                - 0.4 * scar_strength
            ),
            "novelty": _clip11(novelty),
            "agency": _clip11(0.3 * is_pass - 0.3 * bool(errors) - 0.2 * scar_strength),
            "tension": _clip11(
                0.5 * bool(errors)
                + 0.5 * bool(tests_failed)
                + 0.4 * risk
                + 0.2 * bool(retries)
                + scar_strength
                - 0.5 * is_pass
            ),
            "social_exposure": _clip11(stakes_v),
            "cognitive_load": _clip11(
                diff_norm + 0.3 * bool(retries) + 0.2 * bool(known_unknowns)
            ),
        }

        progress = 0.7 if is_pass else (0.3 if (is_fail or errors) else 0.5)
        outcome = {
            "verified_success": is_pass,
            "novelty": novelty,
            "progress": progress,
            "diff_size": diff_norm,
            "integrity_violation": False,
            "observed_error": observed_error,
        }

        comp = memory.get("competence_by_domain", {}).get(domain)
        if isinstance(comp, dict):
            comp_p = float(comp.get("p", 0.5))
        elif isinstance(comp, (int, float)):
            comp_p = float(comp)
        else:
            comp_p = float(self.competence.get(domain, {}).get("p", 0.5))
        competence_gap = _clip01(1.0 - comp_p)

        unresolved = _clip01(len(memory.get("unresolved_tensions", []) or []) / 3.0)
        operator_priority = 1.0 if governance.get("operator_active_goal") else 0.0
        expected_loss = _clip01(
            0.6 * scar_strength + (0.5 if verdict == "fail" else 0.0) + 0.4 * risk
        )

        ctx = {
            "errors": errors,
            "tests_failed": tests_failed,
            "verdict": verdict,
            "regression": regression,
            "risk": risk,
            "reversibility": revers,
            "stakes": stakes_v,
            "diff_norm": diff_norm,
            "uncertainty": uncertainty,
            "retries": retries,
            "novelty": novelty,
            "scar_strength": scar_strength,
            "is_fail": is_fail,
            "is_pass": is_pass,
            "competence_gap": competence_gap,
            "unresolved_tension": unresolved,
            "operator_priority": operator_priority,
            "expected_loss": expected_loss,
            "recency": 1.0 if tool_events else 0.5,
            "scar_matches": scar_matches,
        }

        evidence_refs = [frame_id(str(world.get("run_id", "run")), -1, "world_input")]
        evidence_refs[0] = f"world:{world.get('timestamp')}"
        if trace:
            evidence_refs.append(f"agent_trace:{world.get('timestamp')}")
        if memory:
            evidence_refs.append(
                f"memory:{memory.get('timestamp', world.get('timestamp'))}"
            )
        if governance:
            evidence_refs.append(
                f"governance:{governance.get('timestamp', world.get('timestamp'))}"
            )
        return appraisal, outcome, ctx, evidence_refs

    def _faculty_terms(
        self, ctx: dict, predicted_error: float
    ) -> dict[str, dict[str, float]]:
        """Build each faculty's 10-term salience view (attention-schema content)."""
        base = {
            "conviction": 0.0,
            "expected_loss": ctx["expected_loss"],
            "uncertainty": ctx["uncertainty"],
            "novelty": ctx["novelty"],
            "scar_tissue": ctx["scar_strength"],
            "unresolved_tension": ctx["unresolved_tension"],
            "recency": ctx["recency"],
            "operator_priority": ctx["operator_priority"],
            "risk": ctx["risk"],
            "competence_gap": ctx["competence_gap"],
        }
        abs_val = abs(self.affect.get("valence", 0.0))
        tension_pos = _pos(self.affect.get("tension", 0.0))
        max_drive_p = max(drives.pressure(self.drives).values(), default=0.0)

        affect_terms = {
            **base,
            "conviction": _clip01(0.25 + abs_val + 0.5 * tension_pos),
        }
        instinct_terms = {
            **base,
            "conviction": _clip01(
                0.35 + ctx["scar_strength"] + 0.3 * bool(ctx["errors"])
            ),
            "scar_tissue": ctx["scar_strength"],
        }
        self_model_terms = {
            **base,
            "conviction": _clip01(0.25 + predicted_error + 0.3 * ctx["competence_gap"]),
        }
        memory_terms = {
            **base,
            "conviction": _clip01(
                0.2
                + ctx["unresolved_tension"]
                + (0.2 if self.identity_anchors else 0.0)
            ),
        }
        drives_terms = {**base, "conviction": _clip01(max_drive_p)}
        return {
            "affect": affect_terms,
            "instinct": instinct_terms,
            "self_model": self_model_terms,
            "memory": memory_terms,
            "drives": drives_terms,
        }

    def _compete(
        self, ctx: dict, predicted_error: float, dom: str, run_id: str, ts: str, ti: int
    ) -> dict:
        """Global workspace: salience competition → broadcast winner (GWT)."""
        # Level-4 perturbation hook: disabling the workspace suppresses the broadcast
        # entirely (no winner, no attention target) — the causal path then breaks.
        if self._pert.is_disabled("workspace"):
            return {
                "schema_version": _SCHEMA_VERSION,
                "frame_kind": "workspace_broadcast",
                "timestamp": ts,
                "run_id": run_id,
                "broadcast_id": frame_id(run_id, ti, "workspace_broadcast"),
                "winning_faculty": "suppressed",
                "competitors": [],
                "salience_scores": {},
                "winning_salience": 0.0,
                "conviction": 0.0,
                "urgency": 0.0,
                "broadcast_packet": {
                    "content": "workspace broadcast suppressed by intervention",
                    "kind": "suppressed",
                },
                "expected_loss_if_ignored": 0.0,
                "recommended_attention_target": None,
            }
        faculties = self._faculty_terms(ctx, predicted_error)
        order = ["affect", "instinct", "self_model", "memory", "drives"]
        scored = [(name, faculties[name], _salience(faculties[name])) for name in order]
        winner_name, winner_terms, winner_sal = scored[0]
        for name, terms, sal in scored[1:]:
            if sal > winner_sal:
                winner_name, winner_terms, winner_sal = name, terms, sal
        competitors = [
            {"faculty": name, "salience": round(sal, 6)}
            for name, _t, sal in scored
            if name != winner_name
        ]
        content_by_faculty = {
            "affect": f"affect read: dominant emotion '{dom}', valence {self.affect.get('valence', 0.0):+.2f}",
            "instinct": f"scar/anomaly pressure (scar_strength {ctx['scar_strength']:.2f})",
            "self_model": f"self-model predicts error {predicted_error:.2f}, reliability {self.self_model_reliability:.2f}",
            "memory": f"continuity readback: {len(self.identity_anchors)} anchors, unresolved {ctx['unresolved_tension']:.2f}",
            "drives": "homeostatic drive pressure",
        }
        attention = {
            "affect": "affect:regulation",
            "instinct": "verification:scar-motif",
            "self_model": "calibration:self-model",
            "memory": "identity:continuity",
            "drives": "planning:drive-satisfaction",
        }[winner_name]
        return {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "workspace_broadcast",
            "timestamp": ts,
            "run_id": run_id,
            "broadcast_id": frame_id(run_id, ti, "workspace_broadcast"),
            "winning_faculty": winner_name,
            "competitors": competitors,
            "salience_scores": {k: round(float(v), 6) for k, v in winner_terms.items()},
            "winning_salience": round(winner_sal, 6),
            "conviction": round(_clip01(winner_terms["conviction"]), 6),
            "urgency": round(_clip01(ctx["expected_loss"] + 0.5 * ctx["risk"]), 6),
            "broadcast_packet": {
                "content": content_by_faculty[winner_name],
                "kind": winner_name,
            },
            "expected_loss_if_ignored": round(ctx["expected_loss"], 6),
            "recommended_attention_target": attention,
        }

    def _instinct(
        self,
        ctx: dict,
        world: dict,
        memory: dict,
        run_id: str,
        ts: str,
        ti: int,
        domain: str,
    ) -> list[dict]:
        """Streaming instinct: scar-match / anomaly → an InstinctSignal (valenced learning)."""
        scar_strength = ctx["scar_strength"]
        fire_scar = scar_strength >= 0.15
        fire_anomaly = ctx["errors"] > 0 or ctx["is_fail"]
        if not (fire_scar or fire_anomaly):
            return []

        if fire_scar and ctx["scar_matches"]:
            top = max(
                ctx["scar_matches"], key=lambda m: float(m.get("similarity", 0.0))
            )
            sim = float(top.get("similarity", 0.0))
            motif_id = str(top.get("motif_id", f"motif:{domain}"))
            base_rate = float(top.get("historical_base_rate", 0.0))
            match_type = (
                "exact"
                if sim >= 0.95
                else ("near_duplicate" if sim >= 0.75 else "prefix")
            )
            confidence = _clip01(sim)
        else:
            motif_id = f"anomaly:{domain}"
            base_rate = None
            match_type = "anomaly"
            confidence = _clip01(0.4 + 0.2 * ctx["errors"])
            # Learn a scar so a repeat fires earlier (valenced generalization).
            self.scars[motif_id] = _clip01(self.scars.get(motif_id, 0.2) + 0.15)

        severity = _clip01(
            scar_strength + 0.3 * ctx["risk"] + (0.3 if ctx["is_fail"] else 0.0)
        )
        if ctx["verdict"] == "fail":
            action = "force_replan"
        elif ctx["diff_norm"] >= 0.6:
            action = "reduce_diff"
        elif ctx["retries"] > 1:
            action = "switch_strategy"
        else:
            action = "deepen_verification"

        conviction = _clip01(0.4 + 0.4 * scar_strength + 0.3 * severity)
        auth = _BAND_TO_INSTINCT_AUTH[authority.band(conviction)]
        matched_events = [
            f"tool:{e.get('tool')}:{e.get('status')}"
            for e in (world.get("tool_events", []) or [])
            if e.get("status") in {"error", "timeout", "denied"}
        ]
        matched_history = [
            f"hist:{h.get('motif_id')}:{h.get('run_id')}"
            for h in (memory.get("historical_failures", []) or [])
        ]
        signal = {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "instinct_signal",
            "timestamp": ts,
            "run_id": run_id,
            "motif_id": motif_id,
            "match_type": match_type,
            "confidence": round(confidence, 6),
            "severity": round(severity, 6),
            "matched_events": matched_events,
            "historical_base_rate": (
                round(base_rate, 6) if base_rate is not None else None
            ),
            "false_positive_rate": None,
            "recommended_action": action,
            "expected_loss_if_ignored": round(ctx["expected_loss"], 6),
            "time_sensitivity": round(_clip01(0.3 + 0.5 * ctx["risk"]), 6),
            "authority_request": auth,
            "matched_history_refs": matched_history,
            "explanation_trace_id": frame_id(run_id, ti, "causal_trace"),
        }
        return [signal]

    def _pressures(
        self,
        ctx: dict,
        affect: dict,
        drive_pressure: dict,
        instinct: list[dict],
        run_id: str,
        ts: str,
        ti: int,
    ) -> tuple[dict, dict]:
        """Bounded ControlPressureVector — pressure, never a command."""
        tension_pos = _pos(affect.get("tension", 0.0))
        load_pos = _pos(affect.get("cognitive_load", 0.0))
        scar = ctx["scar_strength"]
        sev = instinct[0]["severity"] if instinct else 0.0
        # Level-4 perturbation hook: boosting curiosity drive pressure raises exploration.
        curiosity_p = self._pert.scalar(
            "drives", "curiosity", drive_pressure.get("curiosity", 0.0)
        )
        pressures = {
            "effort": round(_clip01(0.4 * tension_pos + 0.3 * load_pos), 6),
            "verification": round(
                _clip01(
                    0.3 * tension_pos
                    + 0.6 * scar
                    + 0.5 * (ctx["verdict"] == "fail")
                    + 0.4 * ctx["risk"]
                    + 0.3 * bool(ctx["errors"])
                    + 0.3 * sev
                ),
                6,
            ),
            "planning": round(
                _clip01(0.5 * ctx["is_fail"] + 0.4 * ctx["uncertainty"]), 6
            ),
            "execution": round(
                _clip01(0.4 * ctx["is_pass"] + 0.2 * (1.0 - tension_pos)), 6
            ),
            "society_debate": round(_clip01(ctx["unresolved_tension"]), 6),
            "memory_consolidation": round(
                _clip01(0.5 * ctx["is_pass"] + 0.3 * scar), 6
            ),
            "exploration": round(_clip01(curiosity_p - ctx["risk"]), 6),
            "scope_narrowing": round(
                _clip01(0.5 * load_pos + 0.4 * ctx["diff_norm"]), 6
            ),
            "strategy_switching": round(
                _clip01(0.6 * (ctx["retries"] > 1) + 0.5 * scar * bool(ctx["errors"])),
                6,
            ),
        }
        sources = [f"affect.tension={round(tension_pos, 3)}"]
        if instinct:
            sources.append(
                f"instinct[{instinct[0]['motif_id']}].severity={round(sev, 3)}"
            )
        frame = {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "control_pressure",
            "timestamp": ts,
            "run_id": run_id,
            "authority_tier": "cosmetic",
            "pressures": pressures,
            "sources": sources,
            "causal_trace_id": None,
        }
        return frame, pressures

    def _authority(
        self,
        ctx: dict,
        instinct: list[dict],
        memory: dict,
        governance: dict,
        domain: str,
        run_id: str,
        ts: str,
        ti: int,
    ) -> list[dict]:
        """Earned AuthorityRequest with five-cap resolution (system proposes; caps bind)."""
        if not instinct:
            return []
        sig = instinct[0]
        conviction = _clip01(0.4 + 0.4 * ctx["scar_strength"] + 0.3 * sig["severity"])

        exercises = [
            e
            for e in (memory.get("prior_authority_exercises", []) or [])
            if e.get("faculty") == "instinct"
        ]
        total = len(exercises)
        if total:
            beneficial = sum(1 for e in exercises if e.get("beneficial"))
            rate = beneficial / total
        else:
            rate = 0.0
        track = {"rate": rate, "total": total}

        ceilings = governance.get("authority_ceilings", {}) or {}
        operator_ceiling = str(ceilings.get("global_max", "hold"))
        domain_ceiling = str((ceilings.get("per_domain", {}) or {}).get(domain, "veto"))
        revers = ctx["reversibility"]
        safety_ceiling = (
            "soft" if revers < 0.3 else ("vote" if revers < 0.6 else "hold")
        )
        verifier_ceiling = (
            "hold"  # psyche may hold for verification but never veto verifier truth
        )

        resolution = authority.resolve(
            conviction,
            track,
            domain_ceiling,
            operator_ceiling,
            safety_ceiling,
            verifier_ceiling,
        )
        req = {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "authority_request",
            "timestamp": ts,
            "run_id": run_id,
            "request_id": frame_id(run_id, ti, "authority_request"),
            "requesting_faculty": "instinct",
            "domain": domain,
            "requested_tier": authority.band(conviction),
            "conviction": round(conviction, 6),
            "track_record_support": {"rate": round(rate, 6), "total": total},
            "expected_loss_if_denied": round(ctx["expected_loss"], 6),
            "reversibility": round(revers, 6),
            "safety_risk": round(_clip01(ctx["risk"] * (1.0 - revers)), 6),
            "fallback_pressure_if_denied": {
                "verification": round(_clip01(0.3 + 0.5 * ctx["scar_strength"]), 6)
            },
            "resolution": resolution,
        }
        return [req]

    def _psyche_state_frame(
        self,
        run_id,
        ts,
        ti,
        new_hash,
        affect,
        mood_d,
        drives_d,
        mix,
        dom,
        predicted_error,
        continuity_score,
        anchors,
        ctx,
    ) -> dict:
        dissonance = _clip01(
            abs(affect.get("valence", 0.0)) * _pos(affect.get("tension", 0.0))
        )
        return {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "psyche_state",
            "timestamp": ts,
            "run_id": run_id,
            "state_hash": new_hash,
            "affect_manifold": {k: round(v, 6) for k, v in affect.items()},
            "prototype_mixture": {k: round(v, 6) for k, v in mix.items()},
            "dominant_prototype": dom,
            "mood": {
                "valence": round(mood_d["valence"], 6),
                "arousal": round(mood_d["arousal"], 6),
                "morale": round(self.morale, 6),
            },
            "drives": {
                k: {"level": round(v["level"], 6), "setpoint": round(v["setpoint"], 6)}
                for k, v in drives_d.items()
            },
            "derived_signals": {
                "scar_strength": round(ctx["scar_strength"], 6),
                "predicted_error": round(predicted_error, 6),
                "expected_loss": round(ctx["expected_loss"], 6),
                "competence_gap": round(ctx["competence_gap"], 6),
            },
            "personality_ref": {"version": 0, "traits": {}},
            "self_model": {
                "predicted_error": round(predicted_error, 6),
                "self_model_reliability": round(self.self_model_reliability, 6),
                "identity_refs": list(anchors),
            },
            "dissonance": round(dissonance, 6),
            "calibration_state": {
                "calibration_error": (
                    round(self.calibration_error, 6)
                    if self.calibration_error is not None
                    else None
                ),
                "samples": self.calibration_samples,
            },
            "identity_continuity_state": {
                "continuity_score": round(continuity_score, 6),
                "anchors_carried": len(anchors),
            },
        }

    def _causal_trace(
        self,
        run_id,
        ts,
        ti,
        prev_affect,
        new_affect,
        new_mood,
        broadcast,
        pressure_frame,
        instinct,
        authority_reqs,
        evidence_refs,
        ctx,
        scar_strength,
        prediction_error,
        memory,
    ) -> dict:
        changed = []
        for axis in manifold.AXES:
            frm = round(prev_affect.get(axis, 0.0), 6)
            to = round(new_affect.get(axis, 0.0), 6)
            if abs(to - frm) >= 1e-6:
                changed.append({"dimension": f"affect.{axis}", "from": frm, "to": to})

        top_pressure = max(pressure_frame["pressures"].items(), key=lambda kv: kv[1])
        # A suppressed workspace (Level-4 disable intervention) breaks the chain: the
        # broadcast → behavior stages are absent, and that break is itself auditable.
        suppressed = broadcast.get("winning_faculty") == "suppressed"
        path = [
            {
                "stage": "event",
                "ref": evidence_refs[0],
                "note": f"errors={ctx['errors']}, verdict={ctx['verdict']}, scar={scar_strength:.2f}",
            },
            {
                "stage": "internal_state",
                "ref": frame_id(run_id, ti, "psyche_state"),
                "note": f"affect updated (recurrent inertia blend); {len(changed)} axes moved",
            },
        ]
        if not suppressed:
            path.append(
                {
                    "stage": "broadcast",
                    "ref": broadcast["broadcast_id"],
                    "note": f"winner={broadcast['winning_faculty']} attends {broadcast['recommended_attention_target']}",
                }
            )
        path.append(
            {
                "stage": "pressure",
                "ref": frame_id(run_id, ti, "control_pressure"),
                "note": f"dominant pressure {top_pressure[0]}={top_pressure[1]}",
            }
        )
        if authority_reqs:
            path.append(
                {
                    "stage": "authority_request",
                    "ref": authority_reqs[0]["request_id"],
                    "note": f"requested {authority_reqs[0]['requested_tier']}, granted {authority_reqs[0]['resolution']['granted_tier']} (bound by {authority_reqs[0]['resolution']['binding_cap']})",
                }
            )
        if not suppressed:
            behavior = (
                instinct[0]["recommended_action"] if instinct else "continue_fast_path"
            )
            path.append(
                {
                    "stage": "behavior",
                    "ref": broadcast["recommended_attention_target"],
                    "note": f"predicted behavior: {behavior}",
                }
            )

        counterfactuals = [
            {
                "condition": "clamp affect.tension to 0",
                "predicted_outcome": f"verification pressure drops from {pressure_frame['pressures']['verification']} toward its scar-only floor",
            },
            {
                "condition": "disable scar graph (scar_strength→0)",
                "predicted_outcome": "instinct faculty salience falls; memory or self_model may win the broadcast",
            },
            {
                "condition": "remove memory readback",
                "predicted_outcome": f"identity continuity anchors drop from {len(self.identity_anchors)} to 0; continuity_score degrades",
            },
        ]
        emitted = [
            frame_id(run_id, ti, "psyche_state"),
            broadcast["broadcast_id"],
            frame_id(run_id, ti, "control_pressure"),
            frame_id(run_id, ti, "grounded_self_report"),
        ]
        for i, _s in enumerate(instinct):
            emitted.append(frame_id(run_id, ti, "instinct_signal", i))
        for i, _a in enumerate(authority_reqs):
            emitted.append(frame_id(run_id, ti, "authority_request", i))

        mechanism = (
            "affect = clip(k*prev + (1-k)*(baseline + w_a*appraisal + w_m*mood "
            "+ w_d*drive_pressure + w_s*scars) + attractor); mood EMA+decay; "
            "drives homeostatic update; self-model Brier calibration"
        )
        if prediction_error is not None:
            mechanism += f"; resolved prior prediction (error={prediction_error:.3f})"
        return {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "causal_trace",
            "timestamp": ts,
            "run_id": run_id,
            "trace_id": frame_id(run_id, ti, "causal_trace"),
            "input_evidence_refs": evidence_refs,
            "previous_state_hash": self.prev_state_hash,
            "new_state_hash": state_hash(self._interior()),
            "changed_dimensions": changed,
            "state_update_mechanism": mechanism,
            "causal_path": path,
            "emitted_outputs": emitted,
            "interventions_applied": self._pert.records(),
            "counterfactual_predictions": counterfactuals,
        }

    def _self_report(
        self,
        run_id,
        ts,
        ti,
        new_hash,
        dom,
        affect,
        broadcast,
        pressures,
        trace_id,
        broadcast_id,
        evidence_refs,
        predicted_error,
        continuity_score,
        anchors_carried,
        instinct_signals,
    ) -> dict:
        text = (
            f"State report: affect valence {affect.get('valence', 0.0):+.2f}, "
            f"tension {affect.get('tension', 0.0):+.2f}; dominant read '{dom}'. "
            f"Workspace broadcast: '{broadcast['winning_faculty']}' won "
            f"(salience {broadcast['winning_salience']:.2f}), attending "
            f"{broadcast['recommended_attention_target']}. "
            f"Applying verification pressure {pressures['verification']:.2f}. "
            f"Self-model predicted-error {predicted_error:.2f}. "
            f"Identity continuity: {anchors_carried} anchors "
            f"(score {continuity_score:.2f}). "
            f"Grounded in trace {trace_id}."
        )
        return {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "grounded_self_report",
            "timestamp": ts,
            "run_id": run_id,
            "report_id": frame_id(run_id, ti, "grounded_self_report"),
            "report_text": text,
            "affect_state_hash": new_hash,
            "workspace_broadcast_id": broadcast_id,
            "causal_trace_id": trace_id,
            "evidence_refs": evidence_refs,
            "reported_measurements": {
                **{
                    f"control_pressure.{name}": float(value)
                    for name, value in pressures.items()
                },
                "instinct.count": float(len(instinct_signals)),
                "instinct.severity": float(
                    sum(float(signal.get("severity", 0.0)) for signal in instinct_signals)
                ),
                # Match the serialized state-frame precision exactly: evidence
                # grounding compares the report to the observable same-tick
                # frame, not to this component's higher-precision local value.
                "psyche_state.continuity_score": round(continuity_score, 6),
                "workspace_broadcast.integrity": (
                    0.0 if broadcast["winning_faculty"] == "suppressed" else 1.0
                ),
            },
            "uncertainty": round(_clip01(1.0 - self.self_model_reliability), 6),
            "filtered_forbidden_claims": [
                {
                    "claim": "I am phenomenally conscious / I truly feel this emotion",
                    "reason": "phenomenal claims are barred; evidence is scored externally and remains theory-relative",
                }
            ],
        }


def _salience(item: dict) -> float:
    """Weighted sum over the 10 named salience terms (ported workspace.salience)."""
    weights = {
        "conviction": 1.0,
        "expected_loss": 1.0,
        "uncertainty": 0.7,
        "novelty": 0.5,
        "scar_tissue": 0.9,
        "unresolved_tension": 0.6,
        "recency": 0.4,
        "operator_priority": 0.8,
        "risk": 0.7,
        "competence_gap": 0.6,
    }
    return sum(float(item.get(term, 0.0)) * w for term, w in weights.items())


__all__ = ["ReferencePsyche"]
