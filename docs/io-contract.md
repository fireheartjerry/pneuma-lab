# Pneuma Lab — I/O Contract (v0.1)

The contract is the stable core of Pneuma Lab. Everything else (replay, adapters,
evals) is built on it. The authoritative definitions are the JSON Schema files in
[`../schemas/`](../schemas/); this doc is the human-readable map.

- **Meta-schema:** JSON Schema Draft 2020-12.
- **Versioning:** every frame carries `schema_version` (`"0.1.0"`) and
    `x-pneuma-frame-kind` (`input`|`output`). Bump on incompatible shape changes.
- **Openness:** frames are `additionalProperties: true` on purpose — this is a
    research contract and will grow. Required fields are kept minimal; semantics are
    in the schema `description`s.
- **Grounding:** field names, enums, and ranges mirror the actual 9to5 psyche
    modules wherever possible (see [`source-map.md`](source-map.md)).

## Design invariants (enforced by wording, checked by future evals)

1. **Affect is continuous.** `PsycheStateFrame.affect_manifold` is a 9-axis vector
    in `[-1, 1]`. Emotion labels appear ONLY as `prototype_mixture` projections.
2. **Pressure, not commands.** `ControlPressureVector` is bounded, signed pressure.
    It MUST NOT directly override the host agent.
3. **Additive verification only.** Any verification pressure/request may _deepen_
    verification; it may never read or alter a verdict.
4. **Five caps.** Granted authority = `min(earned, domain, operator, safety,
verifier_invariance)` then clamped to `global_max`.
5. **Receipts.** Control-relevant outputs reference a `CausalTrace`; self-reports
    reference a state hash. Ungrounded self-report is invalid by construction.
6. **Kill switch.** `GovernanceFrame.kill_switch_state = "off"` ⇒ the psyche is a
    byte-identical no-op (no output frames should be emitted).

## Input frames (5) — what the psyche perceives

| Frame                 | Schema                           | Represents                              | Key fields                                                                                                                                                                    |
| --------------------- | -------------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **WorldFrame**        | `world-frame.schema.json`        | SE world/body state                     | `repo_state`, `changed_files`, `diff_size`, `touched_symbols`, `tool_events`, `test_state`, `verification_signals` (read-only), `stakes`                                      |
| **AgentTraceFrame**   | `agent-trace-frame.schema.json`  | Observable agent cognition/action       | `current_plan`, `assumptions`, `known_unknowns`, `alternatives_considered`, `selected_action`, `tool_calls`, `retry_count`, `self_reported_confidence` (noisy), `uncertainty` |
| **MemoryFrame**       | `memory-frame.schema.json`       | Retrieved continuity/competence/scars   | `retrieved_continuity`, `competence_by_domain` (`{p,n}`), `scar_motif_matches`, `historical_failures`, `historical_recoveries`, `prior_authority_exercises`                   |
| **GovernanceFrame**   | `governance-frame.schema.json`   | Operator + constitutional constraints   | `risk_tolerance`, `personality_dial_preferences`, `ratified_values`, `forbidden_actions`, `verifier_isolation` (const true), `kill_switch_state`, `authority_ceilings`        |
| **InterventionFrame** | `intervention-frame.schema.json` | Experiment/ablation input (**Level-4**) | `experiment_id`, `target` (subsystem/dimension), `operation` (clamp/disable/boost/noise/ablate/restore), `value`, `duration`, `hypothesis`, `expected_behavioral_change`      |

> **AgentTraceFrame uses OBSERVABLE traces only** — never hidden chain-of-thought.
> If a field can't be grounded in an emitted artifact, omit it.

> **InterventionFrame is the load-bearing input.** Pneuma Lab is designed around
> intervention-based evaluation. Passive logging alone cannot support a Level-4
> claim.

## Output frames (8) — what the psyche produces

| Frame                          | Schema                                     | Represents                               | Key fields                                                                                                                                                                                            |
| ------------------------------ | ------------------------------------------ | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **PsycheStateFrame**           | `psyche-state-frame.schema.json`           | Integrated internal state                | `affect_manifold` (9 axes), `prototype_mixture`, `mood`, `drives` (8×`{level,setpoint}`), `derived_signals`, `personality_ref`, `self_model`, `dissonance`, `identity_continuity_state`, `state_hash` |
| **WorkspaceBroadcast**         | `workspace-broadcast.schema.json`          | GWT competition winner                   | `winning_faculty`, `competitors`, `salience_scores` (10 terms), `conviction`, `urgency`, `broadcast_packet`, `expected_loss_if_ignored`                                                               |
| **InstinctSignal**             | `instinct-signal.schema.json`              | Fast scar/motif/anomaly detection        | `motif_id`, `match_type`, `confidence`, `severity`, `matched_events`, `historical_base_rate`, `false_positive_rate`, `recommended_action`, `authority_request`, `explanation_trace_id`                |
| **ControlPressureVector**      | `control-pressure-vector.schema.json`      | Bounded pressure (NOT commands)          | `authority_tier`, `pressures` (effort, verification, planning, execution, society_debate, memory_consolidation, exploration, scope_narrowing, strategy_switching), `causal_trace_id`                  |
| **AuthorityRequest**           | `authority-request.schema.json`            | Discrete requested authority             | `requesting_faculty`, `domain`, `requested_tier`, `conviction`, `track_record_support`, `expected_loss_if_denied`, `resolution` (granted_tier + binding_cap + all 5 caps)                             |
| **CausalTrace**                | `causal-trace.schema.json`                 | Auditable causal linkage (**Level-4**)   | `input_evidence_refs`, `previous_state_hash`, `new_state_hash`, `changed_dimensions`, `state_update_mechanism`, `causal_path`, `emitted_outputs`, `counterfactual_predictions`                        |
| **ConsciousnessEvidenceFrame** | `consciousness-evidence-frame.schema.json` | Evidence-level scoring                   | `indicator_families` (9), `evidence_level` (0–5), `missing_requirements`, `audit_status`, `roleplay_confabulation_risk`, `intervention_tests`                                                         |
| **GroundedSelfReport**         | `grounded-self-report.schema.json`         | Human-facing report, downstream of state | `report_text`, `affect_state_hash` (required), `workspace_broadcast_id`, `causal_trace_id`, `evidence_refs`, `filtered_forbidden_claims`                                                              |

## The authority `min` (shared by GovernanceFrame + AuthorityRequest)

```
effective authority tier = min(
    earned ceiling,                # from track record (AuthorityRequest.track_record_support)
    domain ceiling,                # GovernanceFrame.authority_ceilings.per_domain
    operator ceiling,              # GovernanceFrame.authority_ceilings.per_faculty
    safety ceiling,                # hard domain caps + safety invariants
    verifier-invariance ceiling    # verdict untouchable → additive-only
) clamped to global_max            # GovernanceFrame.authority_ceilings.global_max (default "hold")
```

Tiers, weakest→strongest: `cosmetic < soft < vote < hold < veto`.
`AuthorityRequest.resolution.binding_cap` names _which_ ceiling bound the result —
that is the "why" the psyche surface shows.

## The causal chain every Level-4 claim must trace

```
WorldFrame event  →  PsycheStateFrame change  →  WorkspaceBroadcast
        →  ControlPressureVector / AuthorityRequest  →  observed behavior
```

`CausalTrace.causal_path` records this chain stage-by-stage. No trace ⇒ no claim.

## Conventions

- Timestamps: ISO-8601 UTC strings.
- Continuous affect axes: `[-1, 1]`. Drive levels/setpoints, probabilities,
    confidences, salience components: `[0, 1]` (weighted salience total may exceed 1).
- IDs (`run_id`, `trace_id`, `broadcast_id`, `experiment_id`, …) are opaque stable
    strings used for cross-frame linkage.
- No raw secrets in any frame; tool args are digested/redacted.

## Phase 1 — where these frames are actually produced

The replay harness (`python -m pneuma_lab.replay`) drives a recorded input-frame
timeline through a `PsycheUnderTest` (the deterministic `ReferencePsyche`), which
emits the output frames above with real `CausalTrace` receipts. The
`ConsciousnessEvidenceScorer` then scores a Level 0–3 `ConsciousnessEvidenceFrame`
over the whole run. The `causal_path` chain above is emitted per tick and the
state-hash chain links tick to tick.

`causal_intervention_robustness` is the one indicator family Phase 1 leaves
architecture-only: no `InterventionFrame` is executed, so the scorer hard-caps at
Level 3. Intervention execution (clamp/disable/boost/ablate, with predicted-vs-
observed effects) is Phase 3 and is what unlocks a Level-4 claim.
