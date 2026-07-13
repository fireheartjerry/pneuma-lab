# Consciousness Evidence Levels (legacy methodology)

> **Historical snapshot. Archived and non-authoritative.** This internal reference-harness
> methodology is retained for replay compatibility only. It is not a
> learned-subject delivery gate and does not establish phenomenal
> consciousness. See `docs/archive/consciousness-level-methodology.md` and the
> canonical `docs/project-status.json`.

Pneuma Lab is an **evidence-graded, consciousness-relevant** research project.

Canonical current implementation and blocker status:
[`docs/project-status.json`](project-status.json).

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
The conceptual ladder is stricter than the current executable harness proxies;
the distinction is explicit below and in every v0.2 `ConsciousnessEvidenceFrame`.

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

- **Near-term:** validate the Level-4 methodology internally, then apply it to a
  qualifying non-toy subject without carrying over the internal score.
- **Long-term north star:** Level 5 (strong candidate).

## How a level is earned (not asserted)

A `ConsciousnessEvidenceFrame` records, per indicator family: a score, supporting
and refuting refs, the **audit status** (self-report alone never raises the level),
the **roleplay/confabulation risk**, and the **intervention tests passed/failed**.

Current executable proxy rules (evidence-frame v0.2, internal harness only):

| To reach | You must show                                                                                                                                                        |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| L1       | A nonzero bounded control signal and its event-to-behavior causal path are emitted. This is a mechanism proxy, not intervention proof.                               |
| L2       | Supplied memory readback changes continuity/scar outputs within the replay. Cross-run persistence in a real subject is not evaluated.                                |
| L3       | The indicator _architecture_ present and exercised (not just scored).                                                                                                |
| L4       | Internal L3 proxies **+** isolated causal intervention **+** grounded self-report **+** full causal trace **+** reproducible artifacts **+** low confabulation risk. |
| L5       | L4 convergent across all families, adversarially robust, independently audited over time.                                                                            |

**Anti-gaming rails:** self-reported coherence/confidence is never an optimization
target; evidence must survive counterfactual/null conditions; a beautiful narration
with no intervention support scores **zero** on the family it narrates.

These proxy levels validate the machinery and the measurement protocol. They do
not satisfy the corresponding conceptual level for a real subject: most notably,
v0.2 does not establish cross-run persistence, independent external audit, or any
phenomenal property.

## Phase 2 status — Level 4 is now reachable in-harness

The intervention harness (`pneuma_lab.interventions`) executes `InterventionFrame`s
and runs a **paired** control/treated/null replay, so Level 4 is no longer a
structural ceiling. The scorer promotes to Level 4 for a run only when **every** gate
below holds; any missing or failed piece keeps the level at ≤ 3 (honest refusal):

1. **Level 3 on the control run** — the full indicator architecture exercised.
2. **Intervention inventory is exact and isolated** — exactly one tick-attached
   intervention is registered in the current v0.2 protocol; executed count and
   reported passed/failed/total IDs agree exactly. Duplicate, stray, or joint-arm
   interventions are refused until isolated arms or a joint hypothesis exist.
   Raw caller-supplied output lists are diagnostic only and remain capped at L3.
3. **Runner provenance is bound and counterbalanced** — the official paired runner
   hashes the input and every arm, rotates control/treated/null through all factory
   ordinals, and requires each logical arm to reproduce byte-identically. Factory
   order effects or digest mismatches block promotion. In v0.2, the exact
   deterministic `ReferencePsyche` factory is certified, and the snapshot/clone
   equivalence protocol (`interventions/certified_subjects.py`) now certifies
   additional deterministic factories that pass its probe (clone equivalence +
   reset determinism + ordinal invariance + interface). Certification grants only
   the mechanical factory contract: promotion still requires the full L3/L4 gate
   (all indicator families + a passing intervention + null + complete causal trace
    - grounded-report change + low confabulation), so a certified but minimal
      subject stays diagnostic. Every pass/arm digest is retained in the evidence
      artifact for audit.
4. **A genuine intervention passes** — at least one non-`restore` directional test's
   observed `target_signal` delta matches its pre-registered `direction` (within
   `bound`), and one failure blocks L4. A passing no-op never earns intervention backing.
5. **Null condition** — the neutralized (`restore`) replay reproduces control, so the
   delta is attributable to the perturbation, not the timeline.
6. **Causal trace complete** — the treated run still traces
   `event → state → broadcast → pressure → behavior` (a `workspace` disable's break
   is an _expected, recorded_ break, not a crash). Treated traces carry the exact
   active intervention receipts; control and neutralized traces must carry none.
7. **Grounded self-report tracks the tested signal** — every report binds to its
   same tick's state hash, workspace broadcast, causal trace, run, and timestamp.
   Its structured `reported_measurements` must equal the actual same-tick values
   and change on the pre-registered target signal. Unrelated prose or changed
   receipt tokens do not count.
8. **Low confabulation risk** — ≤ 0.2 using the same same-tick receipt binding.
   All source and evidence frames must also be strict JSON: NaN and infinities are
   rejected before semantic comparisons.

The scorer derives one canonical run ID from the world timeline and requires every
input and output frame to match it. A caller cannot relabel an evidence artifact.

When Level 4 is met, `audit_status` becomes `internally_audited` (the harness is an
independent recompute of the psyche's receipts, never the psyche scoring itself) and
`evidence_level` is **hard-capped at 4**. External audit over time, adversarial
robustness, and convergence across _all_ families remain Level-5 requirements and are
listed in `missing_requirements`. Phase 2 makes **no** Level-5 claim.

### Evidence-frame v0.2 migration

`ConsciousnessEvidenceFrame` v0.2 replaces the permissive v0.1 intervention arrays
with one typed result record per registered experiment, requires the complete
generated evidence surface, and schema-hard-caps the executable contract at Level 4.
It also requires `paired_replay_provenance`: only counterbalanced runner-issued
digests can support L4; consistent raw outputs alone cannot self-certify.
Every frame also fixes `evaluation_scope` to `internal_harness` and
`real_subject_claim_status` to `not_evaluated`. Thus `evidence_level: 4` means the
co-designed replay methodology passed its internal gates; it is not a claim that a
real biological or deployed agent subject satisfies the conceptual ladder. In
particular, the executable L1/L2 predicates are within-run mechanism proxies, not
proof of intervention-backed behavior and cross-run persistence in a real subject.
Old v0.1 evidence artifacts are historical only and must be regenerated; a future
Level-5 implementation requires an explicit schema version and migration rather
than relabeling a v0.2 artifact.
