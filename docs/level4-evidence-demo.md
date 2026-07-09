# The canonical Level-4 evidence demo

This page explains, in plain English, the evidence path that one command
regenerates:

```bash
python -m pneuma_lab.demo            # writes build/canonical/
```

It produces `build/canonical/summary.json` (+ `summary.md`) and, per fixture, the
raw artifacts (`evidence.json`, and for interventions the control/treated frame
logs and the `intervention_report.json`). Everything below is derived from those
artifacts — nothing is asserted by hand.

> **The ceiling.** This suite reaches at most **internal Level 4** on the
> conservative 0–5 ladder in [`consciousness-levels.md`](consciousness-levels.md):
> causal-intervention robustness demonstrated _in-harness_. Internal Level 4 is
> **not** Level 5, **not** Level 6, **not** AGI, and **not** a claim of phenomenal
> consciousness. See ["What still blocks Level 5"](#what-still-blocks-level-5).

## The two evidence modes

### Passive replay → Level 3

`fixtures/sample_run.jsonl` carries no `InterventionFrame`. The harness drives it
through `ReferencePsyche`, which wires all nine consciousness-indicator families
into a live control loop and emits schema-valid output frames with `CausalTrace`
receipts. Because every non-intervention family is exercised _with a receipt_, the
scorer honestly reaches **Level 3**: "the consciousness-indicator architecture is
live and causally connected."

It stops at Level 3 because nothing was perturbed. Architecture that is merely
_present and exercised_ is architectural plausibility, not causal proof. The one
family that stays unevidenced is `causal_intervention_robustness`, and that is the
whole point of Level 4.

### Paired intervention replay → Level 4

Each `fixtures/interventions/*.jsonl` timeline carries at least one
`InterventionFrame` with a **pre-registered** hypothesis: an operation, a target
signal, a predicted direction, and (where relevant) a bound. That triggers a
**paired replay** — three runs off the same timeline:

- **control** — no perturbation. The healthy baseline. Levels 0–3 are read from
  here, so a broken perturbation can never inflate the base score.
- **treated** — the intervention schedule applied at each active tick.
- **null** — the same schedule, neutralized (every operation becomes `restore`).
  It must reproduce the control run exactly.

The runner then compares control vs treated on the pre-registered target signal
and checks the null against control.

## What counts as a valid causal perturbation

A single intervention test **passes** only when all of the following hold:

1. **Predicted downstream delta occurs.** The observed change in the
   pre-registered `target_signal` matches the pre-registered `direction`
   (`increase` / `decrease` / `bounded_change` / `no_change`) and stays within any
   declared `bound`.
2. **The null shows ~0 change vs control.** The neutralized run reproduces
   control, so the treated delta is attributable to the _perturbation_, not to the
   timeline or nondeterminism.

And for the **run** to earn Level 4, every gate below must hold together:

- Level 3 already holds on the **control** run;
- exactly one tick-attached intervention is registered (no duplicate, stray, or
  piggybacked joint-arm tests), and its executed count and reported
  passed/failed/total inventory agree exactly;
- the runner binds the input and arm outputs into SHA-256 receipts, rotates all
  arms through control/treated/null factory order, and observes byte-identical
  output for each logical arm across those ordinals; every pass digest is retained;
- the subject factory is the exact deterministic `ReferencePsyche` certified by
  v0.2 (custom factories are capped at Level 3 pending clone/snapshot equivalence);
- at least one real perturbation passed and **none failed**;
- the **null condition** holds (neutralized run reproduces control);
- the **causal trace stays complete** (each non-suppressed tick spans
  event → … → behavior; a deliberately suppressed broadcast is allowed to break
  the chain, and that break is itself traced, not a crash);
- **grounded self-reports track the tested signal** — every report binds to the
  state hash, broadcast ID, causal-trace ID, run, and timestamp from its own tick;
  structured reported measurements must equal those frames and change on the
  pre-registered target signal. Unrelated prose or changed receipt IDs are not enough;
- **confabulation risk stays low** under that same-tick binding check.

Any missing or failed piece is an honest refusal: the level stays ≤ 3. The psyche
under test never scores itself — the scorer recomputes the verdict from receipts.
The public raw-output scorer is intentionally diagnostic-only and capped at Level 3;
only the counterbalanced runner can issue the provenance required for promotion.
The emitted frame is mechanically scoped to `evaluation_scope: internal_harness`
and `real_subject_claim_status: not_evaluated`; passing this demo validates the
methodology against its deterministic reference implementation, not consciousness
in a real subject.

## Why null controls matter

Without the null run, a treated delta could be an artifact of the timeline, of
tick ordering, or of nondeterminism, and we would mistake it for a caused effect.
The null re-runs the _same schedule_ with every operation neutralized to a
`restore`. If the null reproduces control byte-for-byte while treated diverges,
the divergence can only come from the perturbation. The null is the difference
between "state changed" and "the perturbation _caused_ the change."

## Why failed hypotheses must not score Level 4

`fixtures/interventions/failing_hypothesis.jsonl` runs a real perturbation but
pre-registers a prediction the mechanism does not produce. The observed delta does
not match the pre-registered direction, so the test **fails**, and a single failed
test blocks Level 4 for the whole run — it drops to **Level 3**. This is the
anti-overfitting rail: we score the _pre-registered_ prediction, not whatever
happened to move. If failed hypotheses could still score Level 4, the evidence
would be unfalsifiable and therefore worthless.

## Why a pure restore stays Level 3

`fixtures/interventions/restore_null.jsonl` applies only `restore` operations. Its
`no_change` test _passes_ (nothing was supposed to move, and nothing did), but a
no-op perturbs no interior state, so there is no downstream delta to attribute and
the grounded self-report does not change. Level 4 requires **at least one real
perturbation with a predicted downstream delta** — a no-op provides none, so the
run honestly stays at **Level 3**. This proves the gate is not satisfied by merely
_executing_ an intervention frame; the perturbation must actually cause something.

## What still blocks Level 5

Internal Level 4 is intervention-backed evidence on this in-harness battery. The
honest gap up to the Level-5 north star (recorded in every Level-4 evidence
frame's `missing_requirements`):

- **convergent evidence** — Level 4 is shown here; Level 5 needs _every_ indicator
  family intervention-backed, not just `causal_intervention_robustness`;
- **adversarial robustness** — the evidence has not been stress-tested against
  adversarial perturbation over time;
- **external audit** — the evidence is internally auditable in-harness; Level 5
  requires an independent _external_ audit.

And beyond the ladder entirely: this repo evaluates _possible machine
interiority_. Internal Level 4 is **not** Level 5, **not** Level 6, **not** AGI,
and **not** a claim of present phenomenal consciousness. Aggressively investigated;
conservatively claimed.
