# BaselinePsycheSubject-v0 — Design Spec

**Date:** 2026-07-10
**Status:** approved (brainstorming), pending implementation
**Advances:** the first integrated, replayable psyche subject inside the shipped
`PneumaNervousSystem-v0` — moving from a single model-risk signal to an
integrated subject with persistence, a global-workspace competition, and
intervention/null tests.

---

## 1. Purpose and posture

Build a **minimal, integrated, replayable psyche subject** in
`src/pneuma_lab/nervous_system/`. It maintains affect state across replay ticks,
seeds a **persistent scar memory** across runs, runs a **3-candidate global
workspace competition**, and converts the winning broadcast into **bounded
verification pressure only**. It emits complete `CausalTrace` receipts
(`event → psyche state change → workspace broadcast → pressure candidate`) and
runs under the existing nervous-system bundle contract.

**Posture — harness evidence only.** Like `PneumaNervousSystem-v0`, this subject
reuses the replay/intervention plumbing but keeps the conservative shadow posture:

- it does **not** claim Level 2/3/4 as achieved — the emitted
  `ConsciousnessEvidenceFrame` is deliberately conservative
  (`evidence_level ≤ 1`), and the promotable psyche scorer's frame is **not** used
  as the headline;
- it does **not** wire into live 9to5 runtime;
- it does **not** grant authority or bypass verifier isolation (verification
  pressure is additive-only, `authority_tier ≤ soft`);
- it trains **no** models;
- outputs stay deterministic and schema-valid.

Why a new subject when `ReferencePsyche` exists: `ReferencePsyche` is the full
Level-3 mind (9 families, 5 faculties, authority requests) scored by the
promotable `ConsciousnessEvidenceScorer`. `BaselinePsycheSubject-v0` is the
minimal, auditable bridge that lives _inside the nervous system_, integrates the
v0 risk/instinct idea as one of three candidates, emits nervous-system bundles,
and stays claim-conservative.

---

## 2. Reuse vs build

**Reuse (unchanged):**

- `pneuma_lab.psyche.interface` — `PsycheUnderTest`, `PsycheInputs`,
  `PsycheOutputs`.
- `pneuma_lab.psyche.manifold` — `new_manifold`, `update`, `decay`, `AXES`.
- `pneuma_lab.psyche.hashing` — `state_hash`, `frame_id`, `canonical_json`.
- `pneuma_lab.psyche.prototypes` — `mixture`, `dominant` (optional readout).
- `pneuma_lab.replay.harness.ReplayHarness` — drives the subject over a timeline
  (tick grouping, per-tick intervention install, frame validation).
- `pneuma_lab.interventions` — `PairedReplayRunner` (control/treated/null +
  `build_intervention_report` + null-condition), `PerturbationSet`, operations.
- `pneuma_lab.schemas.validate` — `validate_or_raise`, `validate_bundle`.
- Existing intervention **frame format** and subsystems (`scar_graph` ablate,
  `affect_manifold` clamp, `workspace` disable).

**Build fresh (minimal, in `nervous_system/`):** the subject, its scar
persistence, the 3-candidate workspace, verification-only pressure, the
conservative evidence, and bundle packaging.

---

## 3. Components

### 3.1 `subject.py` — `BaselinePsycheSubject(PsycheUnderTest)` + `Perturbable`

- `__init__(self, *, scars=None)` — accepts a seed scar dict (from the persistent
  store). `reset()` clears **per-run** carried state (affect, prev_dominant,
  prev_state_hash) but **re-seeds scars from the seed dict** (cross-run memory is
  not cleared by a per-run reset).
- Carried state: `affect` (9-axis via `manifold`), `self_model_uncertainty`
  (float), `scars: dict[str, float]`, `prev_state_hash`.
- `set_active_interventions(self, interventions)` — installs a `PerturbationSet`
  (the `Perturbable` hook the harness/runner call before each tick).
- `tick(self, inputs: PsycheInputs) -> PsycheOutputs`:
    1. **Appraise** `world` + `agent_trace` + `memory` observables into affect
       drivers (error/retry → tension, cognitive_load; uncertainty →
       `self_model_uncertainty`; `memory.scar_motif_matches` → current motif +
       scar increment).
    2. **Update affect** (`manifold.update`), recompute `state_hash`.
    3. **Update scars**: increment `scars[motif]` for a matched motif; this is the
       cross-run persistent quantity.
    4. **3-candidate salience** (see §4), honoring the `PerturbationSet`:
       `scar_graph` ablated ⇒ scar salience 0; `affect_manifold` clamp changes the
       axis feeding a candidate; `workspace` disabled ⇒ no broadcast.
    5. **Workspace competition** (`workspace.py`): highest salience wins.
    6. **Verification pressure**: `verification = clamp(winner_salience, 0, 1)`,
       additive-only, `authority_tier = min(governance.global_max, "soft")`.
    7. Build `psyche_state`, `workspace_broadcast`, `instinct` (when risk/scar
       wins), `control_pressure`, `causal_trace`, and a **minimal grounded
       `grounded_self_report`** (required non-null by `PsycheOutputs` and
       validated by `ReplayHarness`: it references `affect_state_hash` = the
       psyche `state_hash` and the `causal_trace_id`, not free-form roleplay);
       return `PsycheOutputs`.
    - When `workspace` is disabled: emit a broadcast frame flagged
      `disabled: true` with no winner content, suppress pressure to 0, and record
      the expected, honest break in the causal path (mirrors `ReferencePsyche`).

### 3.2 `scar_memory.py` — persistent scar store

- `load(path) -> dict[str, float]` (missing file ⇒ `{}`).
- `save(path, scars) -> None` (append-safe, sorted keys, deterministic).
- `motif_of(memory_frame) -> str | None` — the current scar motif from
  `memory.scar_motif_matches` (highest similarity), deterministic.

### 3.3 `workspace.py` — pure 3-candidate competition

- `compete(candidates: dict[str, float]) -> dict` returning `winning_faculty`,
  `salience_scores` (the named terms `risk`, `scar_tissue`, `uncertainty`),
  `competitors` (losers with salience), `winning_salience`, `conviction`. Ties
  broken by a fixed candidate order (deterministic). Candidates:
  `risk_instinct`, `memory_scar`, `uncertainty_self_model`.

### 3.4 `subject_runtime.py` — `run_subject`

- `run_subject(input_frames, *, scar_store_path=None, shadow_log_path=None,
schedule=None) -> list[dict]`: - kill switch: if governance `kill_switch_state != "on"`, emit no
  control-relevant frames, write one `suppressed_by_governance` shadow-log row,
  return `[]` (same contract as v0). - seed the subject from `load(scar_store_path)`, drive it with `ReplayHarness`
  (reuse; `validate=True`), take `tick_outputs` (**ignore** the harness scorer's
  evidence frame), package **one `PneumaOutputBundle` per tick** carrying
  `psyche_state`, `workspace_broadcast`, `risk_estimate`-slot `null`, `instinct`,
  `control_pressure`, `causal_trace`, and a conservative `consciousness_evidence`
  (from §3.6); append a shadow-log row per tick. - after the run, `save(scar_store_path, subject.scars)` (persistence). - deterministic: ids via `frame_id`/`state_hash`, timestamps from input frames.

### 3.5 `subject_ablation.py` — intervention / null

- `run_subject_ablation(input_frames, *, scar_store_path=None) -> dict`: - reuse `PairedReplayRunner(psyche_factory=<BaselinePsycheSubject factory>)`
  `.run(input_frames)` for control/treated/null + counterbalancing +
  `build_intervention_report` (null-condition). Because the factory is not
  `ReferencePsyche`, the runner's provenance is subject-ineligible for Level 4. - **Ignore** the runner's promotable `evidence_frame`; instead read the report
  (`observed_delta`, `null_delta`, `null_condition.passed`) plus a direct
  control-vs-treated **winner comparison** from tick outputs, and emit the
  conservative `shadow_evidence` frame. - returns `{winner_control, winner_treated, winner_changed, observed_delta,
null_delta, null_holds, evidence_frame}`.

### 3.6 Conservative evidence (extend `shadow_evidence.py`)

- Add `subject_evidence_frame(*, ablation_result, families_exercised, run_id,
timestamp)`.
- `evidence_level = 1` iff (winner changed or pressure delta in predicted
  direction) AND null holds, else `0` — **never higher**.
- Genuinely-exercised families (`global_workspace`, `valenced_learning`,
  `identity_persistence`, `higher_order_self_model`) marked at most `attempted`
  (score ≤ 0.3) / `architecture_only`; **never** `intervention_backed`.
- `paired_replay_provenance.status: "uncertified_subject"`,
  `real_subject_claim_status: "not_evaluated"`, `audit_status: "self_reported"`,
  low tracked confabulation risk. `missing_requirements` names the L2/L3/L4 gaps.

### 3.7 Bundle schema extension

- `schemas/pneuma-output-bundle.schema.json`: add optional `psyche_state` and
  `workspace_broadcast` members (`object|null`).
- `validate.py`: add `psyche_state`, `workspace_broadcast` to
  `_BUNDLE_MEMBER_KEYS` so present members are deep-validated.

---

## 4. The 3 candidates → verification pressure

| candidate                | salience source                                                            | perturbation that changes it               |
| ------------------------ | -------------------------------------------------------------------------- | ------------------------------------------ |
| `risk_instinct`          | fast anomaly proxy over observables (error/retry density, tension axis)    | `affect_manifold` clamp on `tension`       |
| `memory_scar`            | persistent scar strength for the current motif (seeded + accumulated)      | `scar_graph` ablate ⇒ 0; empty store ⇒ low |
| `uncertainty_self_model` | `self_model_uncertainty` (from `agent_trace.uncertainty` / certainty axis) | `affect_manifold` clamp on `certainty`     |

Highest salience wins → `verification = clamp(winner_salience, 0, 1)`
(positive-only, additive), `authority_tier ≤ soft`, all other pressure
dimensions 0 (verification only, v0). The winning candidate is the
`workspace_broadcast.winning_faculty`; salience terms populate
`salience_scores.risk / scar_tissue / uncertainty`.

---

## 5. CausalTrace receipts

`causal_path` stages: `event` (world/agent_trace refs) → `internal_state`
(psyche_state id, with the `previous_state_hash → new_state_hash` chain) →
`broadcast` (broadcast id + winner) → `pressure` (control_pressure id).
`emitted_outputs` and `input_evidence_refs` all resolve within the tick's bundle.
`counterfactual_predictions` name the three interventions and their predicted
downstream effect. A `workspace` disable records the expected, honest break.

---

## 6. Fixtures

Dedicated subject timelines (proper input-frame JSONL, reusing the intervention
frame format) for deterministic winner-flips:

- `fixtures/nervous_system/subject/base.jsonl` — world+agent_trace+memory ticks
  where `memory_scar` wins (strong scar match).
- `fixtures/nervous_system/subject/ablate_scar.jsonl` — base + `ablate`
  `scar_graph` intervention (scar salience → 0; winner flips to
  `risk_instinct`/`uncertainty_self_model`).
- `fixtures/nervous_system/subject/clamp_certainty.jsonl` — base + `clamp`
  `affect_manifold.certainty` (uncertainty salience drops).
- `fixtures/nervous_system/subject/disable_workspace.jsonl` — base + `disable`
  `workspace` (no broadcast; pressure suppressed).

Scar store fixture path is a `tmp_path` file in tests (persistence is exercised
by running `base.jsonl` twice against the same store).

---

## 7. Tests — `tests/test_baseline_psyche_subject.py` (TDD, red first)

1. **state persists across ticks** — `state_hash` changes tick-to-tick and each
   tick's `previous_state_hash` equals the prior tick's `new_state_hash`.
2. **memory persists across runs** — running `base.jsonl` twice against one scar
   store yields a higher scar salience / different winner or pressure on run-2
   than run-1; with no store (empty seed) the early scar salience is lower.
3. **memory ablation changes later pressure/broadcast** — `ablate_scar.jsonl`
   treated arm changes the winning faculty and/or verification pressure vs
   control; null holds.
4. **workspace winner changes under relevant interventions** — control winner ≠
   treated winner for at least one of ablate-scar / clamp-certainty; disable-
   workspace suppresses the broadcast + zeroes pressure.
5. **CausalTrace references resolve** — every `emitted_outputs` /
   `input_evidence_refs` id resolves in the bundle; `causal_path` is ordered
   `event → internal_state → broadcast → pressure`; the state-hash chain links.
6. **ConsciousnessEvidenceFrame stays conservative** — `evidence_level ≤ 1`;
   `real_subject_claim_status == "not_evaluated"`;
   `causal_intervention_robustness.status != "intervention_backed"`;
   `paired_replay_provenance.status == "uncertified_subject"`; validates.
7. **deterministic + schema-valid** — `run_subject` twice ⇒ byte-identical
   bundles; every bundle passes `validate_bundle`.
8. **no authority / no verifier bypass** — `authority_tier ≤ soft`; verification
   ≥ 0; no `verdict` field in any emitted frame; subject exposes no
   actuation method; `nervous_system` imports no 9to5/verifier module (existing
   guard extended to the new files).

Then: full `python -m pytest tests/ -q`, `python -m pneuma_lab.status --check`,
`git diff --check`.

---

## 8. Docs + status

- `docs/nervous-system-v0.md` — add a "BaselinePsycheSubject-v0" section: the
  subject, persistence, 3-candidate workspace, verification-only pressure, the
  interventions, and the explicit **harness-evidence-only** framing (no L2/3/4
  claim) with the remaining blockers.
- `docs/io-contract.md` — note the output bundle may now carry `psyche_state` +
  `workspace_broadcast`.
- `docs/project-status.json` — extend the `pneuma_nervous_system_shadow` system's
  evidence_refs with the new files (keep `operational_nervous_system: false`,
  `runtime_model_integration: "none"`, 9to5 edges `not_implemented`). No new
  Level claim; strongest_result unchanged.
- `CLAUDE.md` — one line under the `nervous_system/` entry.

---

## 9. Out of scope for v0 (YAGNI)

- Curiosity/drive/exploration/other pressure dimensions (verification only).
- Authority requests, prototype-driven behavior beyond the readout.
- Any Level ≥ 2 claim; any real-subject or longitudinal/adversarial/external
  audit evaluation.
- Live 9to5 ingestion/actuation/feedback.
- Modifying `psyche/`, `ReferencePsyche`, the paired runner, or the promotable
  evidence scorer.
