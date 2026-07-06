# Pneuma Lab Phase 1 — Deterministic Replay Harness + Level-3 Architecture Exercise

**Date:** 2026-07-06
**Status:** Approved design (decisions confirmed with user)
**Scope:** Phase 1 only. No Level-4 interventions. No model training.

## 1. Goal

Stand up the first live surface of Pneuma Lab:

1. A **deterministic replay harness** that loads recorded input-frame sequences,
   validates them, replays the timeline through a psyche-under-test, and stores
   the emitted output frames linked by IDs/hashes.
2. A **Level-3 psyche-under-test** (`ReferencePsyche`) that instantiates and
   _exercises_ every consciousness-indicator family listed in
   `docs/consciousness-levels.md` §Level 3, wired into the frame system and
   producing schema-valid output frames with real `CausalTrace` receipts.
3. An honest **`ConsciousnessEvidenceFrame` scorer** that can score **Level 0–3
   only** and _refuses_ Level 4+ because Phase 1 produces no intervention
   evidence.

Central rule from the evaluation guide: **"No receipts, no claim."** Every
control-relevant output must trace back to input evidence.

## 2. Non-goals (explicit Phase-1 boundaries)

- No `InterventionFrame` execution (clamp/disable/boost/ablate). The harness
  _accepts_ the frame kind and the psyche exposes the seam, but Phase 1 never
  runs a perturbation → `causal_intervention_robustness` stays **unevidenced**.
- No learned estimators / ML. All psyche math is deterministic and hand-audited.
- No write-back into 9to5. Reference math is _ported_ (copied + adapted) from
  `migration/copied-from-9to5/reference-interfaces/`, not imported.

## 3. Architecture

```
input JSONL ──▶ ReplayHarness ──▶ PsycheUnderTest.tick() ──▶ output frames (JSONL)
                     │                    (ReferencePsyche)          │
                     ├─ schema validate (jsonschema, hard)           ├─ psyche_state
                     ├─ group frames into ticks (by run/subtask/ts)  ├─ workspace_broadcast
                     ├─ carry psyche state tick→tick (recurrence)    ├─ instinct_signal*
                     └─ collect + link by ids/hashes                 ├─ control_pressure
                                                                     ├─ authority_request*
                     ConsciousnessEvidenceScorer ◀── run log ──┐     ├─ causal_trace
                     └─▶ consciousness_evidence (level 0–3)     └─────┴─ grounded_self_report
```

### 3.1 Package layout (new)

```
src/pneuma_lab/
    psyche/
        __init__.py        # exports interface + reference psyche
        hashing.py         # canonical-json → sha256 state hashing (determinism)
        manifold.py        # ported affect_manifold.py (9-axis, pure)
        prototypes.py      # ported prototype RBF projection + hysteresis
        mood.py            # ported slow mood homeostat (config inlined)
        drives.py          # ported 8-drive homeostat
        authority.py       # ported 5-cap authority resolution (config inlined)
        interface.py       # PsycheUnderTest ABC + PsycheInputs/PsycheOutputs
        reference.py       # ReferencePsyche — wires all 9 families, emits frames
    replay/
        __init__.py        # exports ReplayHarness, run_replay
        frames.py          # JSONL load/save, tick grouping, id/hash linking
        harness.py         # ReplayHarness orchestrator
        __main__.py        # CLI: python -m pneuma_lab.replay <in.jsonl> -o <dir>
    schemas/
        validate.py        # jsonschema wrapper (validate_frame / validate_or_raise)
    evals/
        evidence.py        # ConsciousnessEvidenceScorer (Level 0–3, hard cap)
fixtures/
    sample_run.jsonl       # a failure-motif escalation timeline (input frames)
tests/
    test_psyche_outputs.py     # every emitted frame is schema-valid
    test_determinism.py        # same input → identical hashes/outputs
    test_evidence_scoring.py   # families exercised; level capped at 3
    test_replay_harness.py     # end-to-end over the fixture
```

### 3.2 Units and interfaces

**`PsycheUnderTest` (ABC)** — the stable seam. One method:

```python
def tick(self, inputs: PsycheInputs) -> PsycheOutputs: ...
def reset(self) -> None: ...          # clear per-run carried state
```

- `PsycheInputs`: `{world, agent_trace, memory, governance, tick_index}` (each an
  already-validated frame dict; memory/governance/agent_trace optional).
- `PsycheOutputs`: `{psyche_state, workspace_broadcast, control_pressure,
causal_trace, grounded_self_report, instinct_signals: list, authority_requests:
list}`. Always-present frames are non-null; instinct/authority are lists (0..n).

Any future psyche (a ported 9to5 mind, a learned model) implements this same ABC.
The harness and scorer depend only on the ABC + the JSON schemas — never on
`ReferencePsyche` internals.

**`ReferencePsyche`** — carries persistent state across ticks (this _is_ the
recurrence): `affect_manifold`, `mood`, `drives`, `personality_baseline`,
`competence{domain}`, `scars{motif→base_rate}`, `self_model{predicted_error,
reliability, calibration_samples, brier_sum}`, `identity_anchors`,
`prev_dominant_prototype`, `prev_state_hash`, `pending_prediction`.

### 3.3 The 9 indicator families → concrete, exercised mechanisms

| Family                         | Mechanism in `tick()`                                                                                                    | Frame receipt                                                          |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- | -------------------------- | -------------------------------------------------- |
| global_workspace               | 5 faculties (instinct, self_model, memory, drives, affect) emit salience terms → weighted competition → winner broadcast | `workspace_broadcast` (winner, competitors, salience_scores)           |
| recurrent_processing           | affect manifold update blends prior state (inertia) → state carried tick→tick                                            | `causal_trace.previous_state_hash`→`new_state_hash` chain              |
| higher_order_self_model        | predict error _before_ outcome, compare to actual next tick, update reliability + calibration                            | `psyche_state.self_model`, `calibration_state`                         |
| predictive_processing          | prediction error =                                                                                                       | predicted_success − observed_outcome                                   | drives drive/affect update | `causal_trace.changed_dimensions` + counterfactual |
| attention_schema               | model _what_ is attended and _why_ via ranked salience terms                                                             | `workspace_broadcast.recommended_attention_target` + `salience_scores` |
| valenced_learning              | scar-motif match → raises instinct severity + pushes affect valence negative (avoidance) + updates scar base rate        | `instinct_signal`, affect valence delta in trace                       |
| identity_persistence           | carry `retrieved_continuity` anchors from `MemoryFrame`; continuity_score = anchors_carried / expected                   | `psyche_state.identity_continuity_state`                               |
| counterfactual_introspection   | "if internal state X had differed, behavior Y would change"                                                              | `causal_trace.counterfactual_predictions`                              |
| causal_intervention_robustness | **architecture present, seam exposed, NOT exercised in Phase 1**                                                         | scorer marks `unevidenced` → blocks L4                                 |

### 3.4 Input → appraisal (world/trace → 9 affect axes)

Deterministic appraisal deltas (bounded), e.g.:

- tool `error`/`timeout`/`denied` → `tension+`, `valence−`, `certainty−`, `dominance−`
- test failures / `verdict==fail` / regression → `valence−`, `tension+`, `arousal+`
- verdict `pending` / known_unknowns → `certainty−` (uncertainty)
- large diff (`diff_size`) → `cognitive_load+`; drives `economy` pressure
- `stakes.risk`/`stakes` → `arousal+`, `tension+`
- verified success (`verdict==pass`, tests pass) → `valence+`, `dominance+`, `tension−`
- scar-motif match (from memory) → `scars` driver negative valence/tension (avoidance)

The manifold `update()` blends inertia + personality baseline + (appraisal, mood,
drive-pressure, scars) drivers — ported verbatim from 9to5.

### 3.5 Determinism

- **No wall-clock**: output-frame `timestamp` is copied from the driving
  `WorldFrame.timestamp` (or the latest input frame in the tick).
- **No RNG**: all math is closed-form.
- **Stable IDs**: `f"{run_id}:{tick_index}:{kind}"` and hashes from canonical
  JSON (`sort_keys`, fixed float formatting) → sha256. Same input ⇒ same output
  bytes ⇒ auditable/replayable (Layer H).

### 3.6 Evidence scoring (Level 0–3, honest cap)

`ConsciousnessEvidenceScorer` consumes the full run log (all emitted frames) and
decides `evidence_level`:

- **L0** baseline (always attainable).
- **L1** — at least one internal signal _causally changed_ a bounded behavior:
  affect/instinct → non-trivial `ControlPressureVector` component, evidenced in a
  `causal_trace` path reaching stage `pressure`/`behavior`.
- **L2** — cross-run persistence read back: a `MemoryFrame` field (scar match,
  continuity anchor, competence) measurably changed an output vs the no-memory
  baseline (the harness records both when memory present).
- **L3** — _all 9 families present AND exercised AND causally connected_ this run
  (every family has ≥1 receipt; `causal_intervention_robustness` is the sole
  architecture-only family and is explicitly logged as unevidenced).
- **L4 refused** — no `InterventionFrame` was executed, so there is no
  intervention/null-condition evidence. Scorer hard-caps at 3 and lists
  `"intervention_evidence"`, `"null_condition_evidence"`,
  `"grounded_self_report_perturbation"` in `missing_requirements`.

`roleplay_confabulation_risk` is computed, not narrated: low when every
`grounded_self_report` references a real `affect_state_hash` + `causal_trace_id`
that exist in the run log; rises if any report lacks grounding. `audit_status`
= `"self_reported"` (Phase 1 is self-scored, not externally audited).

**Invariant guard (Layer B):** the scorer never promotes on self-report alone; a
missing `causal_trace` for a claimed family drops that family to unevidenced.

## 4. Testing strategy

- **Schema validity (Layer A):** every input in the fixture and every emitted
  output frame validates against its Draft-2020-12 schema.
- **Determinism:** run the fixture twice → byte-identical output frames and
  identical `state_hash` chain.
- **Family coverage:** evidence frame shows all 9 families with a populated
  record; 8 evidenced, `causal_intervention_robustness` unevidenced.
- **Honest cap:** `evidence_level <= 3` and the L4 `missing_requirements` are
  present even on a maximally healthy run.
- **Causal completeness:** at least one tick's `causal_trace.causal_path` spans
  `event → internal_state → broadcast → pressure → behavior` and its
  `previous_state_hash`/`new_state_hash` link to the neighboring psyche states.
- **L2 readback:** replay with vs without the `MemoryFrame` scar match →
  different `control_pressure` (verification pressure) → proves readback.

## 5. Dependencies

- Promote `jsonschema>=4.20` from dev-only to a runtime dependency
  (`[project.dependencies]`). Phase-1 mandates frame validation (Layer A); the
  harness validates every input and output and raises on violation.

## 6. Risks / open edges

- Ported `mood.py`/`authority.py` referenced 9to5 `config`; we inline the
  documented defaults (`HN_MOOD_DECAY=0.15`, `HN_THETA_*`, `HN_AUTHORITY_MAX=hold`)
  as module constants. Behavior matches the reference defaults.
- `additionalProperties: true` on the schemas means validation is permissive;
  tests additionally assert required fields + enum/range correctness for the
  fields the psyche populates, so we don't lean on schema laxity.
- The evidence scorer's L1/L2/L3 predicates are conservative by construction; if
  a family's receipt is missing it degrades honestly rather than overclaiming.
