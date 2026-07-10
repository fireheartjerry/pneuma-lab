# PneumaNervousSystem-v0 — Design Spec

**Date:** 2026-07-10
**Status:** approved (brainstorming), pending implementation
**Advances:** the lab-internal shadow slice of the Level-4 causal chain
(`event → internal-state signal → bounded pressure`), realized as auditable frames.

---

## 1. Purpose and posture

Build the stable, model-backed **I/O shell** that wraps `PneumaBrain-v0.1` risk
predictions into auditable Pneuma frames, running in **shadow mode**: advisory
only, zero actuation, no authority, no verifier contact, no runtime change.

This is **Level-4 _infrastructure_.** The evidence it produces is
**Level-1-compatible harness evidence** — it demonstrates that one internal
signal (model risk) causally modulates one bounded advisory quantity
(verification pressure) and that the effect disappears under ablation. It is
**not** a claim that the shadow is an operational Level-1 _system_, and it is
explicitly **not** a Level-3/4 claim: the subject is a risk estimator, not the
integrated psyche, and it is never run through the certified
`PairedReplayRunner`.

### Hard constraints (non-negotiable)

- Do **not** train a new model. Wrap the existing `PneumaBrain-v0.1`.
- Do **not** change agent/planner/verifier runtime behavior.
- Do **not** grant authority to the model. Pressure is a _candidate_, never applied.
- Do **not** bypass verifier isolation. Verification pressure is additive-only (≥ 0).
- Do **not** make Level 4/5/6 claims.
- Keep Pneuma Lab standalone. No import from / write-back into 9to5.

---

## 2. What already exists (reused, not rebuilt)

- `src/pneuma_lab/brain/predict.py::risk_estimate(model, trace, *, prefix)` →
  returns an ad-hoc `RiskEstimateFrame`-shaped dict
  (`failure_probability`, `risk_bucket`, `recommended_use: "advisory_only"`,
  `blocked_uses`). We **wrap** this; we do not modify `brain/`.
- `src/pneuma_lab/brain/predict.py::load_model(path)`; prefixes
  `("prefix_25", "prefix_50", "full")`.
- Trained model artifact: `build/brain/v0-1/elite-final/model.json` (gitignored,
  so **tests use a hermetic fixture model** — never that artifact).
- `src/pneuma_lab/schemas/validate.py::validate_or_raise(frame)` and the
  `FRAME_KIND_TO_SCHEMA` registry.
- The 13 existing frame contracts; `control-pressure-vector`, `instinct-signal`,
  `causal-trace`, `consciousness-evidence-frame` are the direct outputs.

The `ConsciousnessEvidenceScorer` is **not** reused: it is coupled to psyche
replay ticks and 9 indicator families over `ReferencePsyche`. Feeding it model
risk would be a category error and would risk overclaiming. The shadow slice gets
its own deliberately conservative evidence builder.

---

## 3. New schemas (3)

All Draft 2020-12, 4-space indent, no BOM/comments.

### 3.1 `schemas/risk-estimate-frame.schema.json`

- `x-pneuma-frame-kind: output`, `frame_kind: "risk_estimate"`, version `0.1.0`.
- Formalizes the brain's dict into a first-class output frame.
- Fields: `schema_version`, `frame_kind`, `timestamp`, `run_id`, `model_id`
  (`"PneumaBrain-v0.1"`), `model_version`, `prefix` (enum), `failure_probability`
  [0,1], `success_probability` [0,1], `raw_score`, `risk_bucket`
  (`low|medium|high`), `recommended_use` (`const "advisory_only"`),
  `authority_granted` (`const "none"`), `blocked_uses` (array),
  `features_digest`, `causal_trace_id` (nullable).
- Required: `schema_version, frame_kind, timestamp, run_id, model_id, prefix,
failure_probability, risk_bucket, recommended_use, authority_granted`.
- Wired into `OUTPUT_SCHEMA_FILES` and `FRAME_KIND_TO_SCHEMA["risk_estimate"]`.

### 3.2 `schemas/pneuma-input-bundle.schema.json`

- `x-pneuma-schema-kind: "io_bundle"` (like the `pneuma-trace` envelope — a
  container, **not** a cognition frame, kept out of the frame_kind registry).
- `bundle_kind: "pneuma_input"`, version `0.1.0`.
- Members: `world` (WorldFrame or TaskFrame), `agent_trace` (AgentTraceFrame),
  `memory` (nullable **placeholder**), `psyche_state` (nullable placeholder),
  `workspace` (nullable placeholder), `governance` (GovernanceFrame).
- Members typed loosely (`object|null`) here; deep validation is delegated to the
  per-member `validate_or_raise` call in the bundle validator (see §4).

### 3.3 `schemas/pneuma-output-bundle.schema.json`

- `x-pneuma-schema-kind: "io_bundle"`, `bundle_kind: "pneuma_output"`, `0.1.0`.
- Members: `risk_estimate`, `instinct` (InstinctSignal), `control_pressure`
  (ControlPressureVector _candidate_), `causal_trace`, `consciousness_evidence`.
- Plus `blocked_uses` (array, required) and `limitations` (array, required).
- `governance_status` enum `emitted | suppressed_by_governance`.

### 3.4 Loader wiring

- Add `IO_BUNDLE_SCHEMA_FILES` tuple; fold into `ALL_SCHEMA_FILES` so
  `load_all_schemas()` / `test_schema_loads` cover them.

---

## 4. New package `src/pneuma_lab/nervous_system/`

### 4.1 `frames.py` — pure deterministic builders

- `risk_estimate_frame(brain_dict, *, run_id, timestamp, features_digest,
causal_trace_id) -> dict` — maps brain output → formal `RiskEstimateFrame`.
- `instinct_signal(risk, *, run_id, timestamp, trace_id) -> dict` — motif
  `shadow.model-risk-<bucket>`, `match_type: "anomaly"` (model-derived, honest),
  `confidence = severity = failure_probability`, `recommended_action`
  = `deepen_verification` (high) / `continue_fast_path` (else),
  `authority_request: "soft"`, `explanation_trace_id = causal_trace_id`.
- `control_pressure_candidate(risk, governance, *, run_id, timestamp,
causal_trace_id) -> dict` — **only** `verification` is set:
  `verification = round(clamp(failure_probability, 0.0, 1.0), 6)` (**positive
  only** — additive-only; never eases verification). All other pressures 0.
  `authority_tier = min(governance_global_max, "soft")` — the model can never
  request `vote/hold/veto`.
- `causal_trace(...) -> dict` — `event`(agent_trace) → `internal_state`
  (risk_estimate; **note: model risk signal, NOT integrated psyche state**) →
  `pressure`(candidate). `previous_state_hash` = digest(input bundle),
  `new_state_hash` = digest(risk). `state_update_mechanism =
"pneuma_brain_v0_1.risk_estimate"`. `emitted_outputs` and
  `input_evidence_refs` all resolve inside the bundle.
  `counterfactual_predictions: [{condition: "if model risk signal ablated to 0",
predicted_outcome: "verification pressure candidate drops toward 0"}]`.
- `input_bundle(...) / output_bundle(...)` assemblers.
- **Determinism:** every id = content digest (sha256 prefix); every timestamp is
  derived from the input frame timestamp (no wall clock). Repeat run ⇒
  byte-identical bundles.

### 4.2 `shadow_evidence.py` — conservative evidence builder

- `shadow_evidence_frame(*, ablation_result, run_id, timestamp) -> dict`.
- Emits a schema-valid `ConsciousnessEvidenceFrame` capped at **Level 1**:
    - `evaluation_scope: "internal_harness"`, `real_subject_claim_status:
"not_evaluated"`.
    - `evidence_level = 1` iff (ablation shows verification drop in predicted
      direction AND null holds), else `0`.
    - 9 families: mostly `absent`/`architecture_only`;
      `causal_intervention_robustness` at most `attempted` — **never**
      `intervention_backed`.
    - `paired_replay_provenance.status: "uncertified_subject"`, `runner: null`,
      all digests null.
    - `audit_status: "self_reported"`, `roleplay_confabulation_risk` low but noted.
    - `missing_requirements` lists the Level-3/4 gaps (certified paired runner,
      integrated persistent psyche subject, real subject, grounded self-report,
      external audit).
    - Family/`note` text states plainly: _Level-1-compatible harness evidence, not
      an operational Level-1 system claim._

### 4.3 `runtime.py` — `ShadowNervousSystem`

- `__init__(self, model: dict, *, shadow_log_path: str | Path | None = None)` —
  model is an in-memory dict (from `load_model` or a fixture). No actuation
  method exists on the object, by design.
- `classmethod from_model_path(path) -> ShadowNervousSystem`.
- `run_trace(self, trace: dict, governance: dict, *, prefixes=(...)) ->
list[dict]` — for each supported prefix, compute features
  (`brain.prefix_features.feature_vector`), call `brain.predict.risk_estimate`,
  build the frames, assemble and **validate** a `PneumaOutputBundle`; append a
  shadow-log row per bundle. Returns the bundles.
- **Kill switch (adjustment #3):** if `governance.kill_switch_state != "on"`
  (`off`/`frozen`), emit **no** control-relevant frames and return no bundle for
  that trace, but **write one append-only shadow-log audit row**
  `{status: "suppressed_by_governance", run_id, kill_switch_state, ...}`.
- Shadow log is **append-only JSONL** (`replay_outputs_to_shadow_log` +
  `shadow_log_to_advisory_pressure`, lab-internal scope only).
- Invariant guards: module imports nothing from 9to5 / any verifier namespace;
  bundle always carries `blocked_uses`
  (`no_runtime_authority, no_verifier_bypass, no_consciousness_claim`).

### 4.4 `ablation.py` — intervention / null test

- `run_ablation(system, trace, governance, *, prefix="full") -> dict`.
- Three arms over the same trace + prefix:
    - **control**: risk signal present → verification candidate = `f(p)`.
    - **treated**: risk signal ablated to `0.0` → verification candidate → 0.
    - **null**: restore (risk unchanged) → must reproduce control.
- Returns `{control_value, treated_value, null_value, observed_delta,
null_delta, direction_ok, null_holds, evidence_frame}` where `evidence_frame`
  comes from `shadow_evidence.py`.
- Mirrors the existing intervention-report contract in spirit (observed vs null
  delta), without borrowing the psyche runner.

### 4.5 `__main__.py` — CLI

- `python -m pneuma_lab.nervous_system --trace <f> [--model <f>] [--out <dir>]`
  → runs the shadow pipeline + ablation over a fixture, writes bundle(s),
  evidence, and shadow log under `build/nervous_system/`. Falls back to the
  fixture model when no `--model` given and the elite model is absent.

---

## 5. Fixtures

- `fixtures/nervous_system/model.json` — tiny hermetic, schema-faithful model:
  3 prefixes, a handful of features, real `head`/`platt` so
  `brain.predict.risk_estimate` runs unchanged.
- `fixtures/nervous_system/trace_high_risk.jsonl` and `trace_low_risk.jsonl` —
  PneumaTrace-shaped traces (`frames[]` with world + agent_trace steps) that the
  fixture model maps to high / low risk.
- `fixtures/nervous_system/governance_on.json`,
  `governance_killswitch_off.json`.

---

## 6. Tests — `tests/test_nervous_system.py` (TDD, red first)

1. **schema validity** — the 3 new schemas parse; `load_all_schemas` includes
   them; a built `RiskEstimateFrame` and both bundles validate;
   `FRAME_KIND_TO_SCHEMA["risk_estimate"]` resolves.
2. **deterministic shadow outputs** — `run_trace` twice ⇒ byte-identical
   (`json.dumps(sort_keys=True)`).
3. **no runtime authority change** — `control_pressure.authority_tier ∈
{cosmetic, soft}`; `risk_estimate.authority_granted == "none"`;
   `ShadowNervousSystem` exposes no `actuate`/`apply`/`execute` attribute.
4. **no verifier bypass** — `verification` pressure ≥ 0 (additive-only); no
   output frame carries a `verdict`; `nervous_system` source imports no verifier
   / 9to5 module.
5. **CausalTrace references complete** — every `emitted_outputs` and
   `input_evidence_refs` id resolves to a frame present in the bundle;
   `causal_path` has ordered `event → internal_state → pressure`;
   pressure/instinct carry the `causal_trace_id`.
6. **intervention/null behaves as expected** — `observed_delta < 0` (treated
   verification drops), `abs(null_delta) <= 1e-6`; low-risk trace yields smaller
   control verification than high-risk.
7. **evidence frame does not overclaim** — `evidence_level <= 1`;
   `real_subject_claim_status == "not_evaluated"`;
   `causal_intervention_robustness.status != "intervention_backed"`;
   `paired_replay_provenance.status == "uncertified_subject"`;
   frame validates against `consciousness-evidence-frame.schema.json`.
8. **kill switch** — `kill_switch_state: "off"` ⇒ no bundle returned, exactly
   one shadow-log row with `status == "suppressed_by_governance"`, and no
   control-relevant frame written.

Run: `python -m pytest tests/test_nervous_system.py -q`, then full
`python -m pytest tests/ -q` and `python -m pneuma_lab.status --check`.

---

## 7. Docs + status

- `docs/nervous-system-v0.md` — new: what shadow mode is; the stable I/O
  contract (input/output bundles + `RiskEstimateFrame`); the risk→verification
  mapping; kill-switch behavior; **why this is Level-4 infrastructure and
  Level-1-compatible harness evidence, not a consciousness claim**; how it
  connects to the future Level-4 chain; **what remains before Level 4** (certified
  paired runner over an integrated persistent psyche subject, real non-toy
  subject, grounded self-report under perturbation, longitudinal + adversarial +
  external audit).
- `docs/io-contract.md` — add `RiskEstimateFrame` and the two bundles to the maps.
- `docs/project-status.json` — **add** a `pneuma_nervous_system_shadow` system
  (implemented, `internal_harness`). Keep `operational_nervous_system: false`,
  `runtime_model_integration: "none"`. **Leave** the two `nine_to_five` edges
  `replay_outputs_to_shadow_log` / `shadow_log_to_advisory_pressure`
  `not_implemented` (our shadow runs on fixtures, not live 9to5); only update
  `B-9TO5-SHADOW`'s summary to note a lab-internal append-only shadow log now
  exists. `CLAUDE.md` Tree Guide gets a one-line `nervous_system/` entry.

---

## 8. Out of scope for v0 (YAGNI)

- Curiosity/drive/exploration pressure (verification only for v0).
- Live 9to5 snapshot ingestion, actuation, feedback edges.
- Any Level ≥ 2 evidence claim; any real-subject evaluation.
- Modifying `brain/`, the psyche, the paired runner, or the evidence scorer.

```

```
