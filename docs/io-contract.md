# Pneuma Lab — I/O Contract

The contract is the stable core of Pneuma Lab. Everything else (replay, adapters,
evals) is built on it. The authoritative definitions are the JSON Schema files in
[`../schemas/`](../schemas/); this doc is the human-readable map.

- **Meta-schema:** JSON Schema Draft 2020-12.
- **Versioning:** every frame carries `schema_version` and
  `x-pneuma-frame-kind` (`input`|`output`). Most contracts remain `0.1.0`;
  `ConsciousnessEvidenceFrame` is `0.2.0` after its fail-closed gate migration.
  Incompatible changes bump the affected frame version.
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

| Frame                          | Schema                                     | Represents                               | Key fields                                                                                                                                                                                              |
| ------------------------------ | ------------------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **PsycheStateFrame**           | `psyche-state-frame.schema.json`           | Integrated internal state                | `affect_manifold` (9 axes), `prototype_mixture`, `mood`, `drives` (8×`{level,setpoint}`), `derived_signals`, `personality_ref`, `self_model`, `dissonance`, `identity_continuity_state`, `state_hash`   |
| **WorkspaceBroadcast**         | `workspace-broadcast.schema.json`          | GWT competition winner                   | `winning_faculty`, `competitors`, `salience_scores` (10 terms), `conviction`, `urgency`, `broadcast_packet`, `expected_loss_if_ignored`                                                                 |
| **InstinctSignal**             | `instinct-signal.schema.json`              | Fast scar/motif/anomaly detection        | `motif_id`, `match_type`, `confidence`, `severity`, `matched_events`, `historical_base_rate`, `false_positive_rate`, `recommended_action`, `authority_request`, `explanation_trace_id`                  |
| **ControlPressureVector**      | `control-pressure-vector.schema.json`      | Bounded pressure (NOT commands)          | `authority_tier`, `pressures` (effort, verification, planning, execution, society_debate, memory_consolidation, exploration, scope_narrowing, strategy_switching), `causal_trace_id`                    |
| **AuthorityRequest**           | `authority-request.schema.json`            | Discrete requested authority             | `requesting_faculty`, `domain`, `requested_tier`, `conviction`, `track_record_support`, `expected_loss_if_denied`, `resolution` (granted_tier + binding_cap + all 5 caps)                               |
| **CausalTrace**                | `causal-trace.schema.json`                 | Auditable causal linkage (**Level-4**)   | `input_evidence_refs`, `previous_state_hash`, `new_state_hash`, `changed_dimensions`, `state_update_mechanism`, `causal_path`, `emitted_outputs`, `interventions_applied`, `counterfactual_predictions` |
| **ConsciousnessEvidenceFrame** | `consciousness-evidence-frame.schema.json` | Evidence-level scoring                   | `indicator_families` (9), `evidence_level` (0–4 in v0.2), `evaluation_scope`, `real_subject_claim_status`, typed `intervention_tests.results`, `paired_replay_provenance`                               |
| **GroundedSelfReport**         | `grounded-self-report.schema.json`         | Human-facing report, downstream of state | `report_text`, `affect_state_hash` (required), `workspace_broadcast_id`, `causal_trace_id`, `reported_measurements`, `evidence_refs`, `filtered_forbidden_claims`                                       |
| **RiskEstimateFrame**          | `risk-estimate-frame.schema.json`          | Advisory model risk (shadow mode)        | `model_id`, `prefix`, `failure_probability`, `risk_bucket`, `recommended_use` (`advisory_only`), `authority_granted` (`none`), `blocked_uses`, `features_digest`, `causal_trace_id`                     |

## Bundles (I/O containers)

Two container manifests aggregate the frames above for the shadow nervous system
(`x-pneuma-schema-kind: io_bundle`, validated via `validate.validate_bundle`):

| Bundle                 | Schema                             | Members                                                                                                                                                                                                                                                           |
| ---------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **PneumaInputBundle**  | `pneuma-input-bundle.schema.json`  | `world`, `agent_trace`, `governance` + nullable placeholders `memory`, `psyche_state`, `workspace`                                                                                                                                                                |
| **PneumaOutputBundle** | `pneuma-output-bundle.schema.json` | `risk_estimate`, `instinct`, `control_pressure` (candidate), `causal_trace`, `consciousness_evidence`, `blocked_uses`, `limitations`, `governance_status`; also `psyche_state` + `workspace_broadcast` when produced by `BaselinePsycheSubject` via `run_subject` |

The producer is the shadow nervous system (`python -m pneuma_lab.nervous_system`);
it wraps PneumaBrain-v0.1 risk into advisory frames without runtime authority or
verifier contact. See [`nervous-system-v0.md`](nervous-system-v0.md).

The `evidence_campaign` manifest kind (`subject-evidence-campaign.schema.json`,
validated via `validate.validate_campaign`) is a conservative, no-level-claim
evidence-campaign summary over `BaselinePsycheSubject-v0`, produced by
`python -m pneuma_lab.nervous_system.campaign_report`. Its slices may also carry
runner-issued `provenance` (`subject_factory_eligible` + control/treated/null arm
digests) and a `scorer_diagnostic`, with `overall.certified` /
`promotion_blocked_by`, when produced by the certified promotable path
`python -m pneuma_lab.nervous_system.certified_campaign`.

## Cloud preparation manifests

`cloud-input-lock.schema.json`, `cloud-experiment-manifest.schema.json`,
`cloud-architecture-manifest.schema.json`, and `cloud-image-manifest.schema.json`
are lab-original `x-pneuma-schema-kind: cloud-manifest` records. They are
validated by `pneuma_lab.cloud.manifests`; they are not frames, bundles, or an
authorization to retrieve inputs or run cloud infrastructure.

`thought-stream.schema.json` (`x-pneuma-schema-kind: expressive_view`) is a
derived, non-authoritative rendering of the output frames above (produced by
`src/pneuma_lab/voice/`) — read-only, never a source of truth. See
[`pneuma-voice-v0.md`](pneuma-voice-v0.md).

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
`ConsciousnessEvidenceScorer` scores a single replay at Level 0–3; only the paired
control/treated/null path can produce a v0.2 Level-4 frame. The `causal_path` chain is emitted per tick and the
state-hash chain links tick to tick.

`causal_intervention_robustness` is the one indicator family a _passive_ replay
leaves architecture-only: no `InterventionFrame` is executed, so the scorer
hard-caps at Level 3. Executing interventions (Phase 2, below) is what can unlock a
Level-4 claim.

## Phase 2 — executing interventions (the Level-4 path)

When the input timeline contains one or more `InterventionFrame`s, the CLI runs a
**paired replay** instead of a single passive one:

```
python -m pneuma_lab.replay <timeline-with-interventions.jsonl> -o <out_dir>
```

Three replays are driven off the one timeline through fresh psyches:

| Replay      | Schedule applied                 | Purpose                                                 |
| ----------- | -------------------------------- | ------------------------------------------------------- |
| **control** | none                             | the healthy baseline; Levels 0–3 are read from here     |
| **treated** | the intervention schedule        | perturbs internal state at each covered tick            |
| **null**    | schedule neutralized (`restore`) | must reproduce control ⇒ deltas are perturbation-caused |

The runner writes `control_frames.jsonl`, `intervention_frames.jsonl`,
`intervention_report.json`, and `evidence.json`.

**Operations** (`InterventionFrame.operation`) act at defined psyche hook points:

| operation            | kind       | effect on `ReferencePsyche`                                         |
| -------------------- | ---------- | ------------------------------------------------------------------- |
| `clamp`              | scalar     | force a target dimension to `value`                                 |
| `boost`              | scalar     | additive change to a target dimension by `value`                    |
| `noise`              | scalar     | add `value * deterministic_noise(seed)` (replay-stable)             |
| `disable` / `ablate` | structural | zero a scalar / drop a whole store (scar graph, workspace, anchors) |
| `restore`            | null       | no-op — the neutralized operation used for the null replay          |

**Subsystems / dimensions** the reference psyche honors: `scar_graph`
(scar_strength), `affect_manifold` (any of the 9 axes, e.g. `tension`), `drives`
(e.g. `curiosity`), `self_model` (`identity_anchors`), `workspace` (disable ⇒
suppressed broadcast + broken action trace).

**`expected_behavioral_change.target_signal`** the report understands:
`control_pressure.<name>`, `instinct.count`, `instinct.severity`,
`psyche_state.continuity_score`, `workspace_broadcast.integrity`. A test **passes**
when the observed treated-minus-control delta matches `direction` (within `bound`
for bounded/no-change) AND the null delta is ~0.

**Level-4 gate** (all must hold; any gap ⇒ level stays ≤ 3): Level 3 on the control
run, every executed intervention test passes, the null condition holds, the causal
trace stays complete (a `workspace` disable's break is an _expected, recorded_
break), grounded self-reports change faithfully under perturbation, and
confabulation risk stays ≤ 0.2. `evidence_level` is hard-capped at 4 — no Level-5
claim is made in Phase 2. When Level 4 is met, `audit_status` becomes
`internally_audited` (the harness independently recomputes the psyche's receipts);
external audit and adversarial robustness remain Level-5 requirements.
