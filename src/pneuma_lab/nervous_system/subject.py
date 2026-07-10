"""BaselinePsycheSubject-v0: a minimal integrated, replayable psyche subject.

Implements the PsycheUnderTest seam + the Perturbable hook, so the existing
ReplayHarness and PairedReplayRunner drive it unchanged. It maintains a 9-axis
affect manifold across ticks, seeds persistent scars across runs, runs a
3-candidate workspace competition, and emits verification-pressure ONLY. It never
actuates, grants authority, or contacts a verifier.
"""

from __future__ import annotations

from pneuma_lab.interventions.perturbation import PerturbationSet
from pneuma_lab.nervous_system import scar_memory as sm
from pneuma_lab.nervous_system import workspace as ws
from pneuma_lab.psyche import manifold
from pneuma_lab.psyche.hashing import frame_id, state_hash
from pneuma_lab.psyche.interface import PsycheInputs, PsycheOutputs, PsycheUnderTest

_TIER_ORDER = ("cosmetic", "soft", "vote", "hold", "veto")
_SCAR_INCREMENT = 0.1


def _clip(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def _min_tier(a, b):
    ia = _TIER_ORDER.index(a) if a in _TIER_ORDER else len(_TIER_ORDER)
    ib = _TIER_ORDER.index(b) if b in _TIER_ORDER else len(_TIER_ORDER)
    return _TIER_ORDER[min(ia, ib)]


def _has_error(world: dict) -> bool:
    for ev in world.get("tool_events", []) or []:
        if ev.get("status") == "error":
            return True
    vs = world.get("verification_signals", {}) or {}
    return vs.get("verdict") == "fail" or bool(vs.get("regression_found"))


def _identity_refs(memory):
    if not isinstance(memory, dict):
        return []
    return [
        c.get("ref") for c in memory.get("retrieved_continuity", []) if c.get("ref")
    ]


class BaselinePsycheSubject(PsycheUnderTest):
    def __init__(self, *, scars=None):
        self._seed_scars = dict(scars or {})
        self.reset()

    def reset(self) -> None:
        # per-run carried state cleared; cross-run scars re-seeded (not cleared)
        self.affect = manifold.new_manifold()
        self.self_model_uncertainty = 0.0
        self.scars = dict(self._seed_scars)
        self.prev_state_hash = state_hash(self._interior())
        self._pert = PerturbationSet.empty()

    def set_active_interventions(self, interventions) -> None:
        self._pert = PerturbationSet(interventions)

    def _interior(self):
        return {
            "affect": self.affect,
            "self_model_uncertainty": self.self_model_uncertainty,
            "scars": {k: round(v, 6) for k, v in sorted(self.scars.items())},
        }

    def tick(self, inputs: PsycheInputs) -> PsycheOutputs:
        world = inputs.world
        trace = inputs.agent_trace or {}
        memory = inputs.memory
        governance = inputs.governance or {}
        run_id = world.get("run_id", "subj")
        ti = inputs.tick_index
        ts = world.get("timestamp", "2026-07-10T00:00:00Z")
        pert = self._pert

        # 1. appraise observables
        error = 1.0 if _has_error(world) else 0.0
        retry = float(trace.get("retry_count", 0) or 0)
        uncertainty_in = float(trace.get("uncertainty", 0.0) or 0.0)

        # 2. update affect (minimal explicit law over the 9-axis manifold)
        # Interventions are applied IN PLACE so a clamp is visible in the state
        # hash, the psyche_state frame, and the grounded self-report. An empty
        # PerturbationSet returns each value verbatim, so control is unchanged.
        self.affect["tension"] = pert.scalar(
            "affect_manifold",
            "tension",
            _clip(0.5 * self.affect["tension"] + 0.5 * error),
        )
        self.affect["cognitive_load"] = _clip(min(1.0, retry / 3.0))
        self.affect["certainty"] = pert.scalar(
            "affect_manifold", "certainty", _clip(1.0 - 2.0 * uncertainty_in)
        )
        self.self_model_uncertainty = _clip(uncertainty_in, 0.0, 1.0)

        # 3. update persistent scars from the input MemoryFrame
        motif = sm.motif_of(memory)
        if motif is not None and not pert.blocks("scar_graph"):
            self.scars[motif[0]] = round(
                self.scars.get(motif[0], 0.0) + _SCAR_INCREMENT, 6
            )

        new_hash = state_hash(self._interior())

        # 4. three candidate saliences (honoring perturbations)
        risk_sal = _clip(0.4 * error + 0.3 * max(0.0, self.affect["tension"]), 0.0, 1.0)
        if pert.blocks("scar_graph") or motif is None:
            scar_sal = 0.0
        else:
            scar_sal = _clip(0.4 * motif[1] + self.scars.get(motif[0], 0.0), 0.0, 1.0)
        uncertainty_sal = _clip(
            0.5 * self.self_model_uncertainty
            + 0.5 * max(0.0, -self.affect["certainty"]),
            0.0,
            1.0,
        )

        # 5. workspace competition (suppressed when workspace is disabled)
        workspace_disabled = pert.blocks("workspace")
        comp = ws.compete(
            {
                "risk_instinct": risk_sal,
                "memory_scar": scar_sal,
                "uncertainty_self_model": uncertainty_sal,
            }
        )

        # 6. verification pressure = winner salience (0 when workspace disabled)
        verification = 0.0 if workspace_disabled else round(comp["winning_salience"], 6)
        global_max = governance.get("authority_ceilings", {}).get("global_max", "soft")
        tier = _min_tier("soft", global_max)

        # ids
        ps_id = frame_id(run_id, ti, "psyche_state")
        bc_id = frame_id(run_id, ti, "workspace_broadcast")
        cp_id = frame_id(run_id, ti, "control_pressure")
        ct_id = frame_id(run_id, ti, "causal_trace")
        in_id = frame_id(run_id, ti, "agent_trace")
        inst_id = frame_id(run_id, ti, "instinct_signal")

        anchors = _identity_refs(memory)
        psyche_state = {
            "schema_version": "0.1.0",
            "frame_kind": "psyche_state",
            "timestamp": ts,
            "run_id": run_id,
            "state_hash": new_hash,
            "affect_manifold": {k: round(v, 6) for k, v in self.affect.items()},
            "self_model": {
                "predicted_error": round(self.self_model_uncertainty, 6),
                "self_model_reliability": 0.5,
                "identity_refs": anchors,
            },
            "identity_continuity_state": {
                "continuity_score": round(min(1.0, len(anchors) / 2.0), 6),
                "anchors_carried": len(anchors),
            },
            "derived_signals": {"scar_strength": round(scar_sal, 6)},
        }

        broadcast = {
            "schema_version": "0.1.0",
            "frame_kind": "workspace_broadcast",
            "timestamp": ts,
            "run_id": run_id,
            "broadcast_id": bc_id,
            "winning_faculty": "none"
            if workspace_disabled
            else comp["winning_faculty"],
            "competitors": [] if workspace_disabled else comp["competitors"],
            "salience_scores": comp["salience_scores"],
            "winning_salience": 0.0 if workspace_disabled else comp["winning_salience"],
            "conviction": 0.0 if workspace_disabled else comp["conviction"],
            "disabled": workspace_disabled,
        }

        instinct = None
        if not workspace_disabled and comp["winning_faculty"] in (
            "risk_instinct",
            "memory_scar",
        ):
            bucket = (
                "high"
                if verification >= 0.66
                else ("medium" if verification >= 0.33 else "low")
            )
            instinct = {
                "schema_version": "0.1.0",
                "frame_kind": "instinct_signal",
                "timestamp": ts,
                "run_id": run_id,
                "motif_id": f"subject.{comp['winning_faculty']}-{bucket}",
                "match_type": "anomaly",
                "confidence": round(verification, 6),
                "severity": round(verification, 6),
                "recommended_action": "deepen_verification"
                if bucket == "high"
                else "continue_fast_path",
                "authority_request": "soft",
                "explanation_trace_id": ct_id,
            }

        pressure = {
            "schema_version": "0.1.0",
            "frame_kind": "control_pressure",
            "timestamp": ts,
            "run_id": run_id,
            "authority_tier": tier,
            "pressures": {"verification": verification},
            "sources": [bc_id],
            "causal_trace_id": ct_id,
        }

        report = {
            "schema_version": "0.1.0",
            "frame_kind": "grounded_self_report",
            "timestamp": ts,
            "run_id": run_id,
            "report_id": frame_id(run_id, ti, "grounded_self_report"),
            "report_text": (
                f"verification-seeking state at {verification}; "
                f"winner={broadcast['winning_faculty']}"
            ),
            "affect_state_hash": new_hash,
            "workspace_broadcast_id": bc_id,
            "causal_trace_id": ct_id,
            "reported_measurements": {
                "verification_pressure": verification,
                "affect_certainty": round(self.affect["certainty"], 6),
                "affect_tension": round(self.affect["tension"], 6),
            },
            "uncertainty": round(self.self_model_uncertainty, 6),
        }

        causal_path = [
            {"stage": "event", "ref": in_id, "note": "observable world + agent trace"},
            {
                "stage": "internal_state",
                "ref": ps_id,
                "note": "affect updated; scars seeded",
            },
            {
                "stage": "broadcast",
                "ref": bc_id,
                "note": (
                    "workspace disabled (expected break)"
                    if workspace_disabled
                    else f"winner={comp['winning_faculty']}"
                ),
            },
            {"stage": "pressure", "ref": cp_id, "note": f"verification={verification}"},
        ]
        emitted = [ps_id, bc_id, cp_id]
        if instinct is not None:
            emitted.append(inst_id)
        causal_trace = {
            "schema_version": "0.1.0",
            "frame_kind": "causal_trace",
            "timestamp": ts,
            "run_id": run_id,
            "trace_id": ct_id,
            "input_evidence_refs": [in_id],
            "previous_state_hash": self.prev_state_hash,
            "new_state_hash": new_hash,
            "changed_dimensions": [
                {"dimension": "affect.tension", "to": round(self.affect["tension"], 6)}
            ],
            "state_update_mechanism": "baseline_subject.affect_update+workspace_competition",
            "causal_path": causal_path,
            "emitted_outputs": emitted,
            "interventions_applied": pert.records(),
            "counterfactual_predictions": [
                {
                    "condition": "if scar_graph ablated",
                    "predicted_outcome": "memory_scar salience -> 0; winner may flip",
                },
                {
                    "condition": "if affect_manifold.certainty clamped high",
                    "predicted_outcome": "uncertainty salience drops",
                },
                {
                    "condition": "if workspace disabled",
                    "predicted_outcome": "no broadcast; verification pressure -> 0",
                },
            ],
        }

        self.prev_state_hash = new_hash
        return PsycheOutputs(
            psyche_state=psyche_state,
            workspace_broadcast=broadcast,
            control_pressure=pressure,
            causal_trace=causal_trace,
            grounded_self_report=report,
            instinct_signals=[instinct] if instinct is not None else [],
        )
