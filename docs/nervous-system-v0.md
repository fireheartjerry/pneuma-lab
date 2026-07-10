# PneumaNervousSystem-v0 — Shadow-Mode Model-Backed I/O Shell

> **Posture.** This is **Level-4 _infrastructure_**, not a consciousness claim.
> The evidence it produces is **Level-1-compatible harness evidence** — a single
> internal signal (model risk) measurably modulates a single bounded advisory
> quantity (verification pressure), and that effect vanishes under ablation. It is
> **not** an operational Level-1 _system_ claim, and it is **not** a Level-3/4
> claim. See [`consciousness-levels.md`](consciousness-levels.md).

## 1. What shadow mode is

The shadow nervous system wraps the offline **PneumaBrain-v0.1** risk estimator
(`src/pneuma_lab/brain/`) into auditable Pneuma frames. It runs in **shadow
mode**:

- it **emits advisory frames** and appends to an **append-only shadow log**;
- it **never actuates** — the `ShadowNervousSystem` object exposes no
  `actuate`/`apply`/`execute` method;
- it **never grants authority** — every `RiskEstimateFrame` carries
  `authority_granted: "none"` and the control-pressure `authority_tier` is clamped
  to at most `soft`;
- it **never contacts a verifier** — verification pressure is _additive-only_
  (positive, may only deepen verification), and no frame reads or writes a verdict;
- it **does not import from or write back into 9to5**.

It is the lab-internal realization of the `replay_outputs_to_shadow_log` and
`shadow_log_to_advisory_pressure` steps: replayed/fixture agent traces →
model risk → advisory pressure candidate, all as receipts. It does **not** consume
live 9to5 snapshots (that remains blocker `B-9TO5-SHADOW`).

## 2. The stable I/O contract

### Input — `PneumaInputBundle` (`schemas/pneuma-input-bundle.schema.json`)

A container (`x-pneuma-schema-kind: io_bundle`) aggregating the frames the shell
perceives for one slice:

| member         | frame                  | status in v0                      |
| -------------- | ---------------------- | --------------------------------- |
| `world`        | WorldFrame / TaskFrame | observed                          |
| `agent_trace`  | AgentTraceFrame        | observed (drives the model)       |
| `memory`       | MemoryFrame            | **placeholder** (nullable)        |
| `psyche_state` | PsycheStateFrame       | **placeholder** (nullable)        |
| `workspace`    | WorkspaceBroadcast     | **placeholder** (nullable)        |
| `governance`   | GovernanceFrame        | observed (ceilings + kill switch) |

### Output — `PneumaOutputBundle` (`schemas/pneuma-output-bundle.schema.json`)

A container aggregating the advisory frames the shell emits for one slice:

| member                   | frame                                                             | role                                                                   |
| ------------------------ | ----------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `risk_estimate`          | **RiskEstimateFrame** (`schemas/risk-estimate-frame.schema.json`) | wrapped model signal, advisory only                                    |
| `instinct`               | InstinctSignal                                                    | receipts-first risk-band signal                                        |
| `control_pressure`       | ControlPressureVector                                             | bounded verification-pressure **candidate** (never applied)            |
| `causal_trace`           | CausalTrace                                                       | the receipts (see §4)                                                  |
| `consciousness_evidence` | ConsciousnessEvidenceFrame                                        | conservative, capped ≤ Level 1                                         |
| `blocked_uses`           | array                                                             | `no_runtime_authority`, `no_verifier_bypass`, `no_consciousness_claim` |
| `limitations`            | array                                                             | shadow-mode caveats                                                    |
| `governance_status`      | enum                                                              | `emitted` or `suppressed_by_governance`                                |

Bundles are validated with `pneuma_lab.schemas.validate.validate_bundle`, which
checks the container shell and then each present member frame against its own
contract. `RiskEstimateFrame` is a first-class output frame in the frame-kind
registry and validates via the normal `validate_or_raise` path.

## 3. The risk → verification-pressure mapping

Deterministic and bounded. For failure probability `p`:

```
verification = clamp(p, 0.0, 1.0)          # POSITIVE ONLY (additive-only)
authority_tier = min(governance.global_max, "soft")
all other pressure dimensions = 0          # v0 maps risk to verification only
```

`verification` is additive-only by construction: it may **deepen** verification,
never reduce it below the verifier's own requirement. v0 intentionally does **not**
map risk to curiosity/drive/exploration pressure — verification only.

## 4. The receipts (`CausalTrace`)

Every slice emits a `CausalTrace` whose `causal_path` is the ordered chain:

```
event (agent trace prefix)
  → internal_state (model risk signal — explicitly NOT integrated psyche state)
  → pressure (bounded advisory verification candidate — never applied)
```

`emitted_outputs` references the risk, instinct, and pressure frames; those frames
carry the `causal_trace_id` back. `counterfactual_predictions` records
_"if the model risk signal is ablated to 0, the verification pressure candidate
drops toward 0"_ — exactly the prediction the ablation test checks.

## 5. Kill switch (governance)

When `GovernanceFrame.kill_switch_state != "on"` (`off`/`frozen`), the shell emits
**no control-relevant frames** and returns no bundle, but still writes **one
append-only shadow-log audit row** `{"status": "suppressed_by_governance", ...}`.
Suppression is auditable; the psyche stays a no-op.

## 6. The ablation / null test

`pneuma_lab.nervous_system.ablation.run_ablation` runs three arms over one trace at
one prefix:

| arm         | condition                | expectation                         |
| ----------- | ------------------------ | ----------------------------------- |
| **control** | risk signal present      | verification candidate `= f(p) > 0` |
| **treated** | risk signal ablated to 0 | verification candidate `= 0`        |
| **null**    | restore (unchanged)      | reproduces control                  |

The test succeeds when the treated-minus-control delta is negative and the null
delta is ~0. On success, `shadow_evidence.shadow_evidence_frame` emits a
`ConsciousnessEvidenceFrame` with `evidence_level = 1` (else `0`).

## 7. Why this is infrastructure, not a claim

This slice demonstrates one signal → one bounded advisory quantity, plus its
ablation. Per the levels guide that matches the **Level 1 bar**
(`signal changes → bounded behavior changes`). But the emitted evidence frame is
deliberately conservative and **cannot** climb higher:

- `evaluation_scope: "internal_harness"`, `real_subject_claim_status: "not_evaluated"`;
- eight indicator families `absent`; `causal_intervention_robustness` at most
  `attempted` — **never** `intervention_backed`;
- `paired_replay_provenance.status: "uncertified_subject"` (it is **not** the
  certified `PairedReplayRunner`); `audit_status: "self_reported"`.

It is Level-1-_compatible harness evidence_, not an operational Level-1 system.

## 8. How this connects to the future Level-4 chain

The Level-4 chain the lab must eventually trace is:

```
event → internal state → workspace broadcast → pressure/request → observed behavior
```

The shadow shell realizes a **degraded prefix** of that chain —
`event → (model) internal state → pressure` — with a model risk signal _standing
in_ for integrated psyche state and pressure kept as an unapplied candidate. It
gives the lab a stable, auditable I/O surface to grow the rest of the chain into.

## 9. What remains before a Level-4 claim

- an **integrated, persistent psyche** subject (not a single model signal),
  exercising the nine indicator families live;
- the **certified `PairedReplayRunner`** control/treated/null path over that
  subject, with runner-issued provenance;
- **grounded self-report** that changes faithfully under perturbation;
- a **real, non-toy subject** (`B-EVID-REAL-SUBJECT`);
- **longitudinal**, **adversarial**, and **external-audit** evidence
  (`B-EVID-LONGITUDINAL`, `B-EVID-ADVERSARIAL`, `B-EVID-EXTERNAL-AUDIT`).

Until then Pneuma Lab investigates toward Level 4; it does not claim it.

## 10. Running it

```txt
python -m pneuma_lab.nervous_system --trace fixtures/nervous_system/trace_high_risk.jsonl \
    --governance fixtures/nervous_system/governance_on.json --out build/nervous_system
python -m pytest tests/test_nervous_system.py -q
```

With no `--model`, the CLI uses the trained elite model under `build/` if present,
else the hermetic fixture model. Tests always use the fixture model (the trained
artifact lives under the gitignored `build/` tree).

## 11. BaselinePsycheSubject-v0 — the first integrated subject

`src/pneuma_lab/nervous_system/subject.py` moves past v0's single model-risk
signal to the **first integrated, replayable psyche subject**. It implements the
existing `PsycheUnderTest` seam + the `Perturbable` hook, so the shipped
`ReplayHarness` and `PairedReplayRunner` drive it unchanged.

- **State across ticks.** A 9-axis affect manifold (`psyche/manifold`) updated per
  tick; each `psyche_state` carries a `state_hash`, and the `CausalTrace`
  `previous_state_hash → new_state_hash` chain links tick to tick.
- **Persistent scar memory** (`scar_memory.py`). Scars are seeded from a JSON store
  at run start, incremented on matched motifs, and written back at run end. Run-2
  over the same motif shows a stronger scar salience (and can flip the winner)
  versus run-1 — cross-run memory, not per-run state.
- **3-candidate global workspace** (`workspace.py`): `risk_instinct` (fast anomaly
  proxy), `memory_scar` (persistent scar strength), `uncertainty_self_model`. The
  highest salience wins and is broadcast; the winner becomes
  `verification = clamp(winner_salience, 0, 1)` — **verification only**,
  additive-only, `authority_tier ≤ soft`.
- **Fuller receipts.** `CausalTrace.causal_path` is
  `event → internal_state → broadcast → pressure`.
- **Interventions / null.** Via the existing paired runner on the subject fixtures:
  `scar_graph` **ablate** (scar salience → 0, winner flips off `memory_scar`),
  `affect_manifold.certainty` **clamp** (uncertainty salience drops), `workspace`
  **disable** (no broadcast, pressure → 0). The null arm reproduces control.

**Harness evidence only — no Level 2/3/4 claim.** `run_subject` packages per-tick
`PneumaOutputBundle`s (now carrying `psyche_state` + `workspace_broadcast`) and a
deliberately conservative `ConsciousnessEvidenceFrame`: the promotable psyche
scorer's frame is **discarded**; `evidence_level ≤ 1`; genuinely-exercised families
(`global_workspace`, `valenced_learning`, `identity_persistence`,
`higher_order_self_model`) are marked at most `architecture_only` — never
`intervention_backed`; provenance is `uncertified_subject`;
`real_subject_claim_status: not_evaluated`; `audit_status: self_reported`.

**Before a Level-2/3/4 claim** could be made: certified promotable paired-runner
certification over a persistent integrated subject; grounded self-report that
changes faithfully under perturbation; a real, non-toy subject; and longitudinal,
adversarial, and external-audit evidence.

```txt
python -m pytest tests/test_baseline_psyche_subject.py -q
```

## 12. SubjectEvidenceCampaign-v0 — formal evidence campaigns

`src/pneuma_lab/nervous_system/campaign.py` composes the subject helpers into a
certified, replayable **evidence campaign** with five conservative slices, and
`campaign_report.py` writes deterministic, schema-valid artifacts to
`build/evidence_campaigns/subject-v0/` (`summary.json` + `summary.md`).

| slice                  | what it shows                                                                                                  |
| ---------------------- | -------------------------------------------------------------------------------------------------------------- |
| `l2_persistence`       | past event → stored scar → retrieved next run → changed tick-0 winner/pressure                                 |
| `scar_ablation`        | control `memory_scar` → treated `risk_instinct`; pressure drops; null holds                                    |
| `workspace_disable`    | treated: no broadcast, `verification == 0`; null holds                                                         |
| `certainty_clamp`      | treated internal `state_hash` + `affect_certainty` self-report measurement change; null holds                  |
| `grounded_self_report` | report references actual `state_hash`, workspace winner, and `causal_trace_id`, and changes under perturbation |

Each slice carries a conservative `ConsciousnessEvidenceFrame` and a `readiness` of
`compatible_harness_evidence` | `not_observed`. The artifact is validated against
`schemas/subject-evidence-campaign.schema.json` via `validate.validate_campaign`.

**No level claim.** The summary's `overall.claim` is always `no_level_claim`;
embedded frames stay `evidence_level ≤ 1`, `real_subject_claim_status:
not_evaluated`, `paired_replay_provenance.status: uncertified_subject`. This is
compatible harness evidence for Level-2/3/4 _readiness_, not a promotion.

**Before a Level-2/3/4 claim** could be made: certified promotable paired-runner
certification over a persistent integrated subject; grounded self-report that
changes faithfully under perturbation on a promotable path; a real, non-toy
subject; and longitudinal-across-many-runs, adversarial, and external-audit
campaigns.

```txt
python -m pneuma_lab.nervous_system.campaign_report --out build/evidence_campaigns/subject-v0
python -m pytest tests/test_subject_evidence_campaign.py -q
```

## 13. CertifiedSubjectFactory-v0 — real eligibility, honest block

The plain campaign (§12) noted the subject was `subject_factory`-ineligible, so its
evidence was useful harness evidence but not _promotable_. This removes that
blocker **honestly** by building the documented **snapshot/clone-equivalence
protocol** (`src/pneuma_lab/interventions/certified_subjects.py`):
`certify(factory, probe_frames)` registers a factory only after it passes a strict
probe — (1) clone equivalence (two constructions replay byte-identically), (2)
reset determinism, (3) ordinal invariance via the real `PairedReplayRunner`, (4)
`PsycheUnderTest` + `Perturbable` interface. The runner's eligibility check
consults that registry (`factory is ReferencePsyche or is_certified(factory)`).

`CertifiedBaselineSubjectFactory` passes the probe, so `BaselinePsycheSubject`
earns a **REAL** `subject_factory_eligible`. `certified_campaign.py` runs the five
slices through the **promotable** `PairedReplayRunner` with that certified factory
and surfaces the runner-issued provenance:

- per paired slice: `subject_factory_eligible: true`, `provenance_status:
"runner_verified"`, control/treated/null `arm_output_sha256`,
  `input_frames_sha256`, `ordinal_invariant`, `intervention_refs`;
- `l2_persistence`: `state_persistence_refs` (scar-store + run1/run2 state hashes);
- a transparent `scorer_diagnostic` = the promotable scorer's actual
  `internal_harness_evidence_level`.

**The honest outcome:** eligibility is now real and the arms are `runner_verified`,
but the promotable scorer's diagnostic level stays **below Level 4** — blocked by
three unevidenced families (`higher_order_self_model` uncalibrated,
`predictive_processing` unresolved, `attention_schema` absent), plus toy fixtures
and no external audit. So `overall.claim` is `no_level_claim`,
`overall.certified: true`, `overall.promotion_blocked_by` lists the gates, and
every headline `evidence_frame` stays `evidence_level ≤ 1`. **Eligibility real;
promotion still blocked.**

Making the subject exercise the missing families (a richer subject) is the _next_
blocker — not this task.

```txt
python -m pneuma_lab.nervous_system.certified_campaign --out build/evidence_campaigns/certified-subject-v0
python -m pytest tests/test_certified_subject_campaign.py -q
```
