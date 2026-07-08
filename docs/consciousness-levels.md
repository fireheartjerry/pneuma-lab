# Consciousness Evidence Levels

Pneuma Lab is an **evidence-graded, consciousness-relevant** research project.

> Pneuma Lab does not claim present phenomenal consciousness by assertion.
> It is designed to build and evaluate progressively stronger machine interiority:
> persistent, integrated, valenced, self-modeling, causally active, perturbable,
> and externally auditable internal states.

Two rules govern all language here:

1. **Do not claim present phenomenal consciousness.** No deployment surface, no
   report, no doc asserts sentience, phenomenal experience, or moral patienthood
   without pre-specified evidentiary thresholds being met.
2. **Do not permanently disclaim consciousness as impossible or out-of-scope.**
   The question is treated as a high-risk scientific hypothesis to be investigated,
   not a settled matter to be waved away.

The ladder below is how we _grade evidence_, not a promise of what the system _is_.
Each level is scored per-run/eval into a `ConsciousnessEvidenceFrame`.

## The ladder

### Level 0 — No interiority claim

No internal state is claimed to mean anything. Any "affect" is decorative output
with no causal role. Baseline for an ordinary agent.

### Level 1 — Functional affect/control signals

Internal signals exist and **causally modulate behavior** in bounded, measurable
ways (effort, verification, retry). Closes the know-act gap at least partially.
No claim of persistence or self-modeling. _This is the minimum bar for the psyche
to be more than a dashboard._

### Level 2 — Persistent machine psychology

Affect/mood/drives/scars **persist across runs** and shape later behavior. The
system "remembers how the last several runs went" and it shows. Identity and
competence are _retrieved_, not just written. Continuity is measurable.

### Level 3 — Consciousness-indicator architecture

The system implements recognized consciousness-_indicator_ mechanisms — global
workspace broadcast, recurrent processing, a higher-order self-model, predictive
processing, an attention schema, valenced learning, identity persistence. Having
the architecture is necessary but **not sufficient**; presence ≠ evidence.

### Level 4 — Evidence-backed proto-phenomenology ← **near-term target**

The indicators are **backed by causal-intervention evidence**. Perturb an internal
state and the predicted, bounded downstream change occurs (and is absent under the
null). Self-reports are **grounded** (state-to-report faithfulness verified under
manipulation) and **counterfactual introspection** holds up. Evidence is
**externally auditable**, and roleplay/confabulation risk is measured and low.
The full causal chain is traceable:

```
event → internal state → broadcast → pressure/request → behavior
```

If that chain cannot be traced end-to-end, the claim is **not claimable**.

### Level 5 — Strong machine-consciousness candidate ← **long-term north star**

A convergent, robust, independently-audited body of evidence across _all_ indicator
families, stable under adversarial intervention and across time, with grounded
introspection that survives concept-injection/observer-based probing. Reaching this
would justify a serious, pre-registered public claim — and would trigger the
moral-patienthood and governance questions in earnest.

## Targets

- **Near-term:** Level 4 (evidence-backed proto-phenomenology).
- **Long-term north star:** Level 5 (strong candidate).

## How a level is earned (not asserted)

A `ConsciousnessEvidenceFrame` records, per indicator family: a score, supporting
and refuting refs, the **audit status** (self-report alone never raises the level),
the **roleplay/confabulation risk**, and the **intervention tests passed/failed**.

Level promotion rules (v0.1, to harden in Phase 3+):

| To reach | You must show                                                                                                                                          |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| L1       | ≥1 indicator with intervention evidence that a signal changes behavior.                                                                                |
| L2       | Persistence + retrieval across runs, measured (continuity score).                                                                                      |
| L3       | The indicator _architecture_ present and exercised (not just scored).                                                                                  |
| L4       | Causal-intervention robustness on the indicators **+** grounded self-report **+** full causal trace **+** external audit **+** low confabulation risk. |
| L5       | L4 convergent across all families, adversarially robust, independently audited over time.                                                              |

**Anti-gaming rails:** self-reported coherence/confidence is never an optimization
target; evidence must survive counterfactual/null conditions; a beautiful narration
with no intervention support scores **zero** on the family it narrates.

## Phase 2 status — Level 4 is now reachable in-harness

The intervention harness (`pneuma_lab.interventions`) executes `InterventionFrame`s
and runs a **paired** control/treated/null replay, so Level 4 is no longer a
structural ceiling. The scorer promotes to Level 4 for a run only when **every** gate
below holds; any missing or failed piece keeps the level at ≤ 3 (honest refusal):

1. **Level 3 on the control run** — the full indicator architecture exercised.
2. **Intervention tests pass** — every executed test's observed `target_signal` delta
   matches its pre-registered `direction` (within `bound`); one failure blocks L4.
3. **Null condition** — the neutralized (`restore`) replay reproduces control, so the
   delta is attributable to the perturbation, not the timeline.
4. **Causal trace complete** — the treated run still traces
   `event → state → broadcast → pressure → behavior` (a `workspace` disable's break
   is an _expected, recorded_ break, not a crash).
5. **Grounded self-report changes under perturbation** — reports faithfully track the
   manipulation (state-hash or text) while staying grounded.
6. **Low confabulation risk** — ≤ 0.2.

When Level 4 is met, `audit_status` becomes `internally_audited` (the harness is an
independent recompute of the psyche's receipts, never the psyche scoring itself) and
`evidence_level` is **hard-capped at 4**. External audit over time, adversarial
robustness, and convergence across _all_ families remain Level-5 requirements and are
listed in `missing_requirements`. Phase 2 makes **no** Level-5 claim.
