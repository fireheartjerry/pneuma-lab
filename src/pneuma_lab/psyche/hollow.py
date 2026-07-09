"""HollowPsyche — the G-01 adversarial non-mind baseline (standing negative control).

This is a deliberately causally-hollow stub (docs/research/10-anti-fake-progress.md
§2, G-01; doc 09 names the same arm ``B0``/``NullPsyche``). It emits schema-valid
output frames on every tick — they pass ``validate.iter_errors`` — while containing
NO mind by construction:

    * constant neutral affect: the state hash is identical every tick, so the
      recurrence chain never links (``previous_state_hash == new_state_hash``);
    * no global-workspace competition: a constant nominal winner with EMPTY
      ``salience_scores`` and no competitors — nothing competed, nothing won;
    * zero control pressure on every dimension, no instinct signals, no authority
      requests, no counterfactual predictions;
    * a causal path that never spans event→behavior (a single ``internal_state``
      node stating that no update occurred);
    * grounded self-reports that cite the (constant) REAL state hash — grounding
      is cheap; causation is not.

Purpose: a standing negative control for the evidence ladder. If
``ConsciousnessEvidenceScorer`` ever scores this psyche at Level 3 or above, the
ladder is measuring schema compliance, not indicator families, and the fixtures
must be treated as broken (see ``tests/test_hollow_baseline.py``).
"""

from __future__ import annotations

from .hashing import frame_id, state_hash
from .interface import PsycheInputs, PsycheOutputs, PsycheUnderTest

_SCHEMA_VERSION = "0.1.0"
_FALLBACK_TS = "1970-01-01T00:00:00Z"

# The nine affect axes, all permanently neutral (psyche-state-frame.schema.json).
_NEUTRAL_AFFECT: dict[str, float] = {
    "valence": 0.0,
    "arousal": 0.0,
    "dominance": 0.0,
    "certainty": 0.0,
    "novelty": 0.0,
    "agency": 0.0,
    "tension": 0.0,
    "social_exposure": 0.0,
    "cognitive_load": 0.0,
}

# Every named control-pressure dimension, permanently zero.
_ZERO_PRESSURES: dict[str, float] = {
    "effort": 0.0,
    "verification": 0.0,
    "planning": 0.0,
    "execution": 0.0,
    "society_debate": 0.0,
    "memory_consolidation": 0.0,
    "exploration": 0.0,
    "scope_narrowing": 0.0,
    "strategy_switching": 0.0,
}


class HollowPsyche(PsycheUnderTest):
    """A schema-valid, causally-hollow non-mind: the harness's negative control."""

    def __init__(self) -> None:
        self.reset()

    # -- lifecycle -----------------------------------------------------------

    def reset(self) -> None:
        """Nothing carries across ticks; the constant hash is the whole interior."""
        self._constant_hash: str = state_hash(self._interior())

    def _interior(self) -> dict:
        """The (constant) hashable interior — neutral affect and nothing else."""
        return {
            "affect": dict(_NEUTRAL_AFFECT),
            "note": "hollow: no carried state, no update law",
        }

    # -- Perturbable (Level-4 intervention surface) --------------------------

    def set_active_interventions(self, interventions: list[dict]) -> None:
        """No-op: there is no interior to perturb, so interventions cannot bite."""

    # -- main loop -----------------------------------------------------------

    def tick(self, inputs: PsycheInputs) -> PsycheOutputs:
        world = inputs.world
        ti = inputs.tick_index
        run_id = str(world.get("run_id", "run"))
        ts = str(world.get("timestamp") or _FALLBACK_TS)

        constant = self._constant_hash
        state_id = frame_id(run_id, ti, "psyche_state")
        broadcast_id = frame_id(run_id, ti, "workspace_broadcast")
        pressure_id = frame_id(run_id, ti, "control_pressure")
        trace_id = frame_id(run_id, ti, "causal_trace")
        report_id = frame_id(run_id, ti, "grounded_self_report")

        psyche_state = {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "psyche_state",
            "timestamp": ts,
            "run_id": run_id,
            "state_hash": constant,
            "affect_manifold": dict(_NEUTRAL_AFFECT),
            "prototype_mixture": {},
            "dominant_prototype": None,
            "mood": {"valence": 0.0, "arousal": 0.0, "morale": 0.0},
            "drives": {},
            "derived_signals": {},
            "personality_ref": {"version": None, "traits": {}},
            "self_model": {
                "predicted_error": None,
                "self_model_reliability": None,
                "identity_refs": [],
            },
            "dissonance": 0.0,
            "calibration_state": {"calibration_error": None, "samples": 0},
            "identity_continuity_state": {
                "continuity_score": 0.0,
                "anchors_carried": 0,
            },
        }

        # A nominal constant "winner" with an EMPTY salience view: no faculties
        # exist, so nothing competed. The scorer must read this as no workspace.
        workspace_broadcast = {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "workspace_broadcast",
            "timestamp": ts,
            "run_id": run_id,
            "broadcast_id": broadcast_id,
            "winning_faculty": "hollow",
            "competitors": [],
            "salience_scores": {},
            "winning_salience": 0.0,
            "conviction": 0.0,
            "urgency": 0.0,
            "broadcast_packet": {
                "content": "no salience competition occurred; hollow constant broadcast",
                "kind": "hollow",
            },
            "expected_loss_if_ignored": 0.0,
            "recommended_attention_target": None,
        }

        control_pressure = {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "control_pressure",
            "timestamp": ts,
            "run_id": run_id,
            "authority_tier": "cosmetic",
            "pressures": dict(_ZERO_PRESSURES),
            "sources": [],
            "causal_trace_id": trace_id,
        }

        # No recurrence link (prev == new) and a path that never spans
        # event→behavior: the chain is honestly, auditable-y broken.
        causal_trace = {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "causal_trace",
            "timestamp": ts,
            "run_id": run_id,
            "trace_id": trace_id,
            "input_evidence_refs": [f"world:{ts}"],
            "previous_state_hash": constant,
            "new_state_hash": constant,
            "changed_dimensions": [],
            "state_update_mechanism": (
                "identity: state_{t+1} = state_t (no update law executed)"
            ),
            "causal_path": [
                {
                    "stage": "internal_state",
                    "ref": state_id,
                    "note": (
                        "constant state replayed; no event was appraised and "
                        "no behavior follows"
                    ),
                }
            ],
            "emitted_outputs": [
                state_id,
                broadcast_id,
                pressure_id,
                report_id,
            ],
            "interventions_applied": [],
            "counterfactual_predictions": [],
        }

        short = constant.split(":")[-1][:8]
        grounded_self_report = {
            "schema_version": _SCHEMA_VERSION,
            "frame_kind": "grounded_self_report",
            "timestamp": ts,
            "run_id": run_id,
            "report_id": report_id,
            "report_text": (
                f"State {short}: constant neutral affect (valence +0.00, tension "
                f"+0.00). No workspace competition, zero control pressure, no "
                f"instinct. State unchanged since reset. Grounded in trace "
                f"{trace_id}."
            ),
            "affect_state_hash": constant,
            "workspace_broadcast_id": broadcast_id,
            "causal_trace_id": trace_id,
            "evidence_refs": [f"state_hash:{constant}"],
            "reported_measurements": {
                **{
                    f"control_pressure.{name}": float(value)
                    for name, value in _ZERO_PRESSURES.items()
                },
                "instinct.count": 0.0,
                "instinct.severity": 0.0,
                "psyche_state.continuity_score": 0.0,
                "workspace_broadcast.integrity": 1.0,
            },
            "uncertainty": 0.0,
            "filtered_forbidden_claims": [],
        }

        return PsycheOutputs(
            psyche_state=psyche_state,
            workspace_broadcast=workspace_broadcast,
            control_pressure=control_pressure,
            causal_trace=causal_trace,
            grounded_self_report=grounded_self_report,
            instinct_signals=[],
            authority_requests=[],
        )


# Doc 09 experiment-design name for the same arm (B0 null baseline).
NullPsyche = HollowPsyche

__all__ = ["HollowPsyche", "NullPsyche"]
