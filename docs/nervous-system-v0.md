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

```

```
