# SubjectEvidenceCampaign-v0 — Design Spec

**Date:** 2026-07-10
**Status:** approved (brainstorming), pending implementation
**Advances:** formal, replayable evidence campaigns for `BaselinePsycheSubject-v0`
— moving from fixture-proven behaviour to auditable Level-2/3/4-_readiness_
artifacts, without claiming any level.

---

## 1. Purpose and posture

Build a certified, replayable **evidence campaign runner** that evaluates
`BaselinePsycheSubject-v0` across five evidence slices and writes deterministic,
schema-valid, conservative evidence artifacts under `build/evidence_campaigns/`.

It composes the shipped substrate (`run_subject`, `run_subject_ablation`,
`ReplayHarness`, `PairedReplayRunner`); it introduces no new subject faculties
beyond one small honest grounding refinement (§4).

**Posture — compatible harness evidence, never a level claim.**

- Per-slice readiness is `compatible_harness_evidence` | `not_observed`.
- Every embedded `ConsciousnessEvidenceFrame` stays `evidence_level ≤ 1`,
  `real_subject_claim_status: not_evaluated`, `paired_replay_provenance.status:
uncertified_subject`.
- The campaign summary records `overall.claim: "no_level_claim"`.
- Does not wire into live 9to5, train models, grant authority, or bypass verifier
  isolation.

"Certified" here means the _process_ is rigorous and auditable (real paired
control/treated/null arms, deterministic artifacts) — NOT that any level is
certified.

---

## 2. Components

### 2.1 `schemas/subject-evidence-campaign.schema.json`

- `x-pneuma-schema-kind: "evidence_campaign"`, `manifest_kind:
"subject_evidence_campaign"`, version `0.1.0`.
- Shape: `campaign_id`, `subject`, `generated_from` (fixture refs), `slices[]`
  (each `id`, `kind`, `hypothesis`, `effect_observed`, `readiness`, `observed`
  object, `evidence_frame` object), `overall` (`claim: "no_level_claim"`,
  `posture`, `note`).
- Wired into `MANIFEST`-adjacent loading via a new `EVIDENCE_CAMPAIGN_SCHEMA_FILES`
  tuple folded into `ALL_SCHEMA_FILES`; a `validate.validate_campaign(summary)`
  helper validates the summary shell and each embedded `evidence_frame` against
  `consciousness-evidence-frame.schema.json`.

### 2.2 `src/pneuma_lab/nervous_system/campaign.py`

- `SubjectEvidenceCampaign` with one function per slice and an orchestrator
  `run_campaign(*, fixtures_dir, seed_scars=..., scar_store_path=...) -> dict`
  returning the campaign summary dict (validated, not yet written).
- Slice functions return `{id, kind, hypothesis, observed, effect_observed,
readiness, evidence_frame}` where `evidence_frame` comes from
  `shadow_evidence.subject_evidence_frame` (≤ L1).

### 2.3 `src/pneuma_lab/nervous_system/campaign_report.py`

- `write_campaign(summary, out_dir) -> dict[str, Path]` — writes
  `summary.json` (sorted, deterministic) + `summary.md` (human-readable) and
  returns the paths. Validates via `validate_campaign` before writing.
- `main(argv=None)` for `python -m pneuma_lab.nervous_system.campaign_report`
  → writes to `build/evidence_campaigns/subject-v0/`.

---

## 3. The five slices

| #   | id                     | method                                                        | observed effect                                                                                                                                           |
| --- | ---------------------- | ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `l2_persistence`       | `run_subject(base)` run-1 then run-2 vs one shared scar store | run-2 tick-0 winner/pressure differs from run-1 (past event → stored scar → retrieved next run → changed workspace/pressure)                              |
| 2   | `scar_ablation`        | `run_subject_ablation(ablate_scar)`                           | control winner `memory_scar` → treated `risk_instinct`; verification drops; null reproduces control                                                       |
| 3   | `workspace_disable`    | `run_subject_ablation(disable_workspace)`                     | treated: no broadcast, `verification == 0`; null holds                                                                                                    |
| 4   | `certainty_clamp`      | `run_subject_ablation(clamp_certainty)`                       | treated `state_hash` + `affect_certainty` self-report measurement differ from control (downstream state/self-report change); null holds                   |
| 5   | `grounded_self_report` | control vs the scar-ablated arm's last-tick self-report       | report's `affect_state_hash == psyche_state.state_hash`, references the workspace winner and `causal_trace_id`, and the report changes under perturbation |

`effect_observed` is the boolean the slice hypothesis predicts; `readiness` is
`compatible_harness_evidence` when `effect_observed and null_holds` (where a null
arm applies), else `not_observed`.

---

## 4. Small honest refinement to `subject.py`

To make slice 4 (and stronger grounding for slice 5) real:

1. **Apply interventions to the stored affect axes in place.** Currently the
   perturbed `tension`/`certainty` are local salience-only copies. Change so
   `self.affect["tension"]` and `self.affect["certainty"]` are set through
   `pert.scalar(...)`, so a clamp is visible in `state_hash` and `psyche_state`.
   Control (empty `PerturbationSet`) is unchanged — `pert.scalar` returns the
   input verbatim — so existing subject tests are unaffected.
2. **Add affect measurements to the grounded self-report.**
   `reported_measurements` gains `affect_certainty` and `affect_tension` (the
   actual stored axis values). This strengthens grounding and makes a clamp show
   up in the report.

### 4.1 `subject_ablation.py` additive returns

`run_subject_ablation` gains last-tick fields so the campaign can compose without
re-driving the runner: `control_report`, `treated_report`, `null_report`
(grounded self-reports) and `control_state`, `treated_state` (psyche_state
frames). Existing keys and tests are unchanged (additive only).

---

## 5. Data flow

`run_campaign` runs the five slices → aggregates into the summary dict with an
`overall.claim: "no_level_claim"` block → `write_campaign` validates via
`validate_campaign` and writes `summary.json` + `summary.md`.

**Determinism:** fixed fixture timestamps, content-derived ids, sorted JSON, no
wall clock → byte-identical artifacts on rerun. Tests write to `tmp_path`; the CLI
writes to `build/evidence_campaigns/subject-v0/` (gitignored).

---

## 6. Tests — `tests/test_subject_evidence_campaign.py`

1. **deterministic + schema-valid artifacts** — `run_campaign` twice ⇒ byte-
   identical `summary.json`; `validate.validate_campaign(summary)` passes; every
   embedded `evidence_frame` validates against
   `consciousness-evidence-frame.schema.json`.
2. **CausalTrace refs resolve** — for a captured `run_subject` bundle in the
   campaign, every `causal_trace.emitted_outputs`/`input_evidence_refs` id
   resolves and the `previous→new` state-hash chain links.
3. **longitudinal memory ablation changes later behavior** — the `l2_persistence`
   slice reports `effect_observed == True` (run-2 tick-0 pressure ≠ run-1).
4. **paired replay has control/treated/null provenance** — the `scar_ablation`,
   `workspace_disable`, `certainty_clamp` slices each record `observed.control`,
   `observed.treated`, `observed.null` and `null_holds == True`.
5. **self-report changes under relevant perturbation** — the
   `grounded_self_report` slice: control report is grounded (state-hash matches,
   winner + causal-trace referenced) AND control report ≠ perturbed report.
6. **ConsciousnessEvidenceFrame does not overclaim** — every slice
   `evidence_frame` has `evidence_level ≤ 1`, `real_subject_claim_status ==
"not_evaluated"`, `causal_intervention_robustness.status !=
"intervention_backed"`, `paired_replay_provenance.status ==
"uncertified_subject"`; `overall.claim == "no_level_claim"`.

Then full `python -m pytest tests/ -q`, `python -m pneuma_lab.status --check`,
`git diff --check`.

---

## 7. Docs + status

- `docs/nervous-system-v0.md` — add a "SubjectEvidenceCampaign-v0" section: the
  five slices, the artifact shape, the **no-level-claim** posture, and the
  remaining blockers before a Level-2/3/4 claim.
- `docs/io-contract.md` — one line noting the `evidence_campaign` manifest kind.
- `docs/project-status.json` — extend `pneuma_nervous_system_shadow` evidence_refs
  with the campaign files. Keep `operational_nervous_system: false`,
  `runtime_model_integration: "none"`, the two `nine_to_five` edges
  `not_implemented`, and the evidence/strongest_result block unchanged (no new
  Level claim).
- `CLAUDE.md` — one sentence under the `nervous_system/` entry.

---

## 8. Out of scope for v0 (YAGNI)

- Any Level ≥ 2 claim; any promotion of the subject.
- Real-subject / longitudinal-across-many-runs / adversarial / external-audit
  campaigns (these remain the named blockers).
- New model training, live 9to5 wiring, authority, or verifier contact.
- Changing `ReferencePsyche`, the promotable evidence scorer, or the paired runner.
