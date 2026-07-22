# 11 — Ablation Matrix

Status: planning. Consistent with `02-research-thesis.md` §8 (Locked Design
Constants). This document enumerates the ablations that isolate _which part_ of
the Pneuma-state condition is doing the work, so a reviewer cannot attribute the
H1/H2 effect to context volume, tokens, or a lucky confound. Nothing here
authorizes implementation, training, or runs.

Cross-references (conceptual — those docs are planned, not yet written):

- Internal-state variables `s_m`, `c`, `t`, `r`, derived `L`: `02` §8.3, to be
  detailed in `06-internal-state-specification.md`.
- Intervention arms, clamp seams, statistical null path: `02` §8.2 / §8.8, to be
  detailed in `09-intervention-and-causal-validity.md`.
- Anti-gaming evaluator + prose-blind firewall: `02` §8.9, in
  `10-anti-gaming-specification.md`.
- Metric `RUF` and secondaries: `02` §8.7, in `08-metrics-and-statistics.md`.

---

## 1. How to read this matrix

Each ablation is a controlled removal or degradation of ONE aspect of the
Pneuma-state condition, holding base model, tools, budget, retry cap, task order,
and environment fixed (`02` §8.1). Every ablation shares the same scaffold and
decision head (`02` §8.4); only the named piece changes. Unless noted, the
comparison is **paired** against the intact Pneuma-state arm on the same tasks and
seed set, scored by the prose-blind evaluator on `RUF`.

Columns:

- **id** — stable label (`ABL-xx`).
- **what is changed** — the exact manipulation.
- **hypothesis** — what we expect the manipulation to do to the mechanism.
- **expected result** — the predicted quantitative direction on `RUF` (and,
  where relevant, the H2 causal contrast).
- **interpretation IF expected result FAILS** — what a non-result would mean
  (this is the load-bearing column; it converts each row into a real test).
- **challenges** — whether a failure threatens the MAIN claim (H1 behavioural /
  H2 causal) or only a SECONDARY design choice (variable count, encoding, update
  law). "MAIN (H1/H2)" rows are the ones a reviewer will weight most.

Baseline anchors referenced below: `RUF(base)` (no state), `RUF(pneuma)` (intact
four-variable state), `RUF(reflection)`, `RUF(retrieval)`. H1 predicts
`RUF(pneuma) < min(RUF(base), RUF(retrieval), RUF(reflection))`; H2 predicts
ablating the failure-memory variable returns `RUF → RUF(base)`.

---

## 2. Core ablation matrix — state existence and plumbing

| id     | what is changed                                                                                                                                                           | hypothesis                                                                                        | expected result                                                                                               | interpretation IF expected result FAILS                                                                                                                                   | challenges                 |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| ABL-01 | **No persistent state.** The Base arm: no cross-task memory of any kind; fresh context each task.                                                                         | State is what enables cross-task failure avoidance; without it the agent repeats motifs.          | `RUF(pneuma) < RUF(no-state)`; this IS the H1 contrast.                                                       | If `RUF` equal, H1 is false — persistent state buys nothing over a memoryless agent at matched budget. This is the primary falsifier.                                     | MAIN (H1)                  |
| ABL-02 | **State present but not used** (influence-disabled): variables update normally but the decision head's state feed is zeroed.                                              | The _content_ of the state is irrelevant unless it gates action; disconnecting influence = Base.  | `RUF(influence-disabled) ≈ RUF(base)`, and `> RUF(pneuma)`. Isolates coupling from mere presence.             | If `RUF(influence-disabled) < RUF(base)`, the improvement is leaking through a side channel (tokens/context), not the coupling — H2 causal story is contaminated.         | MAIN (H2)                  |
| ABL-03 | **State randomly permuted**: at each decision, the four state values are shuffled/replaced with draws from the run's own state distribution.                              | Structure (right value on right variable) matters, not just presence of numbers.                  | `RUF(permuted) ≈ RUF(base)`; well above `RUF(pneuma)`. The head fires on meaningless signal.                  | If permuted state still helps, the head is exploiting a distributional artefact (e.g. "more caution overall"), not motif-specific memory — weakens the specificity claim. | MAIN (H2)                  |
| ABL-04 | **State reset between tasks**: variables are re-initialized to baseline at each task boundary (within-task dynamics kept).                                                | Cross-task persistence is the mechanism; kill it and the effect dies while within-task use stays. | `RUF(reset) ≈ RUF(base)` for repeated-across-task motifs; within-task recovery metrics may hold.              | If reset makes no difference, the benefit is purely within-task and "persistent" is the wrong word — reframes claim from longitudinal to episodic.                        | MAIN (H1/H2)               |
| ABL-05 | **Memory retrieval disabled**: the retrieval-baseline machinery (`foundation/memory.py` FTS5 store) returns nothing; affects Retrieval arm and any retrieval feeding `r`. | Retrieval contributes independently of structured state; removing it degrades the Retrieval arm.  | `RUF(retrieval-no-fetch) ≈ RUF(base)`; Pneuma-state arm largely unaffected (it does not depend on retrieval). | If disabling retrieval also degrades the Pneuma-state arm, the two are entangled and `memory-trust r` is not separable from the retrieval baseline.                       | SECONDARY (arm separation) |

---

## 3. Encoding and representation ablations — structured-vs-text

| id     | what is changed                                                                                                                                                                                     | hypothesis                                                                                         | expected result                                                                                    | interpretation IF expected result FAILS                                                                                                                                                                               | challenges                                |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| ABL-06 | **Textual reflection substituted for structured state**: replace the numeric four-variable state + head with a written-reflection note re-injected as context (the Reflection arm), matched budget. | Structured, clampable numeric state beats prose that is re-read as context (differentiator #1).    | `RUF(pneuma) < RUF(reflection)` at equal tokens. This is the structured-vs-text head-to-head.      | If reflection matches or beats Pneuma-state, the novelty claim (structured > text) collapses; paper degrades to "reflection works" — publishable but not novel.                                                       | MAIN (H1, differentiator)                 |
| ABL-07 | **Continuous state converted to binary flags**: each of `s_m, c, t, r` thresholded to 0/1 before the head reads it.                                                                                 | Graded state carries dose information the head exploits; binarizing loses the dose-response.       | `RUF(binary)` between `RUF(pneuma)` and `RUF(base)`; dose-response on scar strength (H2) flattens. | If binary equals continuous, graded state is over-engineered — a SECONDARY simplification, and it weakens the H2 dose-response leg specifically.                                                                      | SECONDARY (encoding) + H2 dose            |
| ABL-08 | **All state collapsed into one scalar**: feed only derived `L = clip(w1·s_m + w2·c' + w3·t)` to the head; drop the four separate variables.                                                         | The single decision scalar may capture most of the signal; per-variable identity may be redundant. | `RUF(L-only) ≈ RUF(pneuma)` or slightly worse; per-variable attribution (H3) becomes impossible.   | If `L-only` is clearly worse, the four variables are non-redundant (good for the design). If equal, the four-variable story is presentational, not causal — SECONDARY, but it removes the H3 introspection substrate. | SECONDARY (variable count) + H3 substrate |

---

## 4. Update-law and dynamics ablations

| id     | what is changed                                                                                           | hypothesis                                                                                         | expected result                                                                                                | interpretation IF expected result FAILS                                                                                                                       | challenges                |
| ------ | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| ABL-09 | **Update rule disabled**: state is initialized but never updated from observed failures (frozen at init). | Learning from failures is the driver; a frozen state cannot track new motifs.                      | `RUF(frozen) ≈ RUF(base)` (no accumulation of failure-sensitivity).                                            | If a frozen state still helps, the benefit is a static prior (constant caution), not adaptive failure-memory — reframes mechanism as a bias, not learning.    | MAIN (H1/H2)              |
| ABL-10 | **Decay disabled**: `s_m` accumulates without the decay term (matches today's no-decay behaviour).        | Some decay is needed so stale scars do not over-suppress; but its removal should be MILD on `RUF`. | `RUF(no-decay) ≈ RUF(pneuma)` on `RUF`, but false-avoidance / H5 over-avoidance rises on counterfactual tasks. | If no-decay materially worsens `RUF`, decay is load-bearing (elevate it in the design). If it worsens H5 only, decay is a SECONDARY safety knob, as expected. | SECONDARY (dynamics) + H5 |
| ABL-11 | **Remove `s_m`** (failure-sensitivity / scar) one-at-a-time; other three variables intact.                | `s_m` is the primary H1/H2 variable; removing it should erase most of the effect.                  | Largest single-variable degradation: `RUF(−s_m) ≈ RUF(base)`. This equals the H2 clamp result.                 | If removing `s_m` barely moves `RUF`, the failure-memory variable is epiphenomenal — H2 is FALSE (the pre-registered H2 falsifier).                           | MAIN (H2)                 |
| ABL-12 | **Remove `c`** (confidence / calibration) one-at-a-time.                                                  | Confidence modulates when to trust `s_m`; removing it causes mis-timed caution but partial effect. | Small-to-moderate `RUF` increase; calibration secondary metric degrades most.                                  | If removing `c` has zero effect, `c` is redundant with `s_m`/`t` — a SECONDARY variable to cut, not a threat to H1.                                           | SECONDARY (variable)      |
| ABL-13 | **Remove `t`** (caution / tension) one-at-a-time.                                                         | `t` gates verification depth; removing it should reduce appropriate verification.                  | Moderate `RUF` increase; verification-completion secondary metric drops.                                       | If no effect, the caution axis is subsumed by `s_m→L`; SECONDARY variable to cut.                                                                             | SECONDARY (variable)      |
| ABL-14 | **Remove `r`** (memory-trust) one-at-a-time.                                                              | `r` weights retrieved memory; removing it mainly hurts the retrieval-interaction, less pure `RUF`. | Small `RUF` change on synthetic; larger effect where retrieval is active; memory-retrieval-precision drops.    | If removing `r` changes nothing anywhere, `r` was not needed for the contrast with the Retrieval baseline — SECONDARY, prune it.                              | SECONDARY (variable)      |

---

## 5. Provenance, self-report, and anti-gaming ablations

| id     | what is changed                                                                                                                                              | hypothesis                                                                                                       | expected result                                                                                       | interpretation IF expected result FAILS                                                                                                                        | challenges                    |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| ABL-15 | **Provenance removed**: run without commit+config+seed-bound immutable traces (`02` §8.9).                                                                   | Provenance does not change the agent's behaviour; it protects the _validity_ of the claim.                       | `RUF` unchanged; but reproducibility / audit integrity is lost — the run cannot be certified.         | If removing provenance changes `RUF`, provenance was silently feeding the agent (leak) — a validity bug, not a science result. Must be zero by construction.   | SECONDARY (validity guard)    |
| ABL-16 | **Self-report removed**: disable the grounded self-report generation entirely.                                                                               | Self-report is a read-out, not a driver; removing it must not change behaviour (firewall).                       | `RUF` and all behavioural metrics unchanged; only H3 (introspection) becomes untestable.              | If removing self-report changes `RUF`, the prose is feeding back into the decision — the behaviour-vs-report firewall (differentiator #3) is broken.           | MAIN (firewall integrity)     |
| ABL-17 | **Intervention receipts removed**: the causal trace no longer records which variable was clamped.                                                            | Receipts are the evidence substrate for H2/H3; removing them blocks scoring, not behaviour.                      | Behaviour unchanged; H2 `causal_trace_complete` gate cannot be satisfied → causal claim un-scoreable. | If behaviour changes, receipts were on the influence path (bug). If the causal claim still scores without receipts, the scorer is not actually receipt-bound.  | MAIN (H2 auditability)        |
| ABL-18 | **Anti-gaming evaluator removed**: replace the prose-blind N-judge / hidden-motif evaluator with a naive success reader.                                     | Removing anti-gaming defences should INFLATE apparent gains (decoys, misleading reflections, memorized surface). | Apparent `RUF` improvement grows spuriously vs the guarded evaluator; the gap is the gaming headroom. | If scores are identical guarded vs naive, either the tasks have no gaming surface (unlikely) or the anti-gaming controls are inert — undermines credibility.   | MAIN (H1 validity)            |
| ABL-19 | **Causal influence replaced by prompt text only**: instead of the numeric state gating the head, inject the same state _described in words_ into the prompt. | Text description of state is weaker than a causal clamp-able coupling (differentiator #1 + #2).                  | `RUF(prompt-text) > RUF(pneuma)` (worse); the state can no longer be cleanly clamped for H2.          | If prompt-text matches numeric coupling, the "causally-active structured state" advantage over "state-as-context" evaporates — differentiators #1/#2 collapse. | MAIN (H1/H2, differentiators) |

---

## 6. Dependency note — which ablations need which build tasks

Ablations are gated by the same three load-bearing builds the audit identifies
(`01` §3): a real failure detector, a state→action decision head, and a
real-data outcome experiment. Mapping to build tasks (cross-ref `02` §8.3
variables and the intervention arms in `02` §8.2 / planned `09`):

| ablation               | requires build task                                                                                                                                                | notes                                                                                            |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| ABL-01, ABL-06         | Four arms (Base / Retrieval / Reflection / Pneuma-state) + shared scaffold (`02` §8.1–8.2).                                                                        | These ARE the headline arms; no extra build beyond the core four.                                |
| ABL-02, ABL-19         | Decision head with a switchable state feed (`02` §8.4); the head must accept zeroed / prompt-only inputs.                                                          | Requires the state→action coupling that does not exist today (`01` §3.1).                        |
| ABL-03, ABL-07, ABL-08 | Per-variable state accessor + transform layer between state and head.                                                                                              | Depends on `06` fixing the four variables `s_m, c, t, r` and derived `L` (`02` §8.3).            |
| ABL-04, ABL-09, ABL-10 | Persistent store with explicit update rule, reset hook, and decay term (`s_m` decay+cap is a NEW build, `02` §8.3).                                                | Real failure detector required so updates are tied to actual failures, not fixtures (`01` §3.2). |
| ABL-05, ABL-14         | `foundation/memory.py` retrieval backend + the NEW `memory_trust r` scalar (`02` §8.3).                                                                            | `r` is a dedicated new variable; the current `identity_anchors` proxy is insufficient.           |
| ABL-11, ABL-12, ABL-13 | Clamp seams for each variable via `PerturbationSet` (`scar_graph`, `self_model`, `affect_manifold`, new `memory_trust`) and the statistical null path (`02` §8.8). | Clamp math exists; the stochastic causal path (seeds + N-sample nulls) is the blocking build.    |
| ABL-15, ABL-17         | Commit+config+seed-bound immutable trace + receipt-recording causal trace (`02` §8.9).                                                                             | Trace infra largely exists; needs binding to the live driver.                                    |
| ABL-16                 | Grounded self-report generator on the live subject + verified prose-blind firewall (`02` §8.10).                                                                   | Firewall audited clean today; must survive the live-driver port.                                 |
| ABL-18                 | Anti-gaming evaluator suite: hidden motifs, decoy memories, misleading reflections, N-judge ensemble (`02` §8.9).                                                  | Prose-blind scorer reusable; adversarial controls are a build.                                   |

Interpretation guard: ABL-15/16/17 are **validity ablations** — their _expected_
result is "no change to `RUF`." A change there is a bug/leak, not a finding, and
must be fixed before any headline number is reported.

---

## 7. Minimal ablation set for the workshop paper (9 pages)

For a 9-page IAB submission (`02` §8.11), the main body can carry ~6 ablations.
Chosen to (a) prove H1, (b) prove H2 causally, (c) defend the four
differentiators, and (d) pre-empt the "just reflection / just retrieval / just
tokens" objection. Everything else moves to the appendix.

**Must-run (main body):**

1. **ABL-01** — no persistent state (Base). The H1 contrast; without it there is no paper.
2. **ABL-11** — remove `s_m` (failure-memory clamp). The H2 causal proof and the pre-registered H2 falsifier.
3. **ABL-06** — textual reflection substituted. The structured-vs-text differentiator (#1) and the top reviewer objection.
4. **ABL-02** — state present but influence-disabled. Separates coupling from context volume (kills the "extra tokens" confound).
5. **ABL-19** — causal influence replaced by prompt text only. Directly isolates "causally-active clamp-able state" (differentiators #1+#2) from "state-as-context."
6. **ABL-18** — anti-gaming evaluator removed. Shows the reported gain survives the prose-blind/adversarial controls (differentiator #3 + firewall).

Rationale: this six-row set touches every MAIN-claim row exactly once
(H1 existence, H2 clamp, structured-vs-text, coupling isolation, causal-vs-text,
anti-gaming) and needs only the three load-bearing builds — no per-variable
sweep, no encoding sweep.

**Appendix / extended (supplementary):**

- ABL-03 (permuted), ABL-04 (reset), ABL-05 (retrieval disabled) — plumbing/specificity robustness.
- ABL-07 (binary), ABL-08 (single scalar) — encoding/representation robustness.
- ABL-09 (frozen update), ABL-10 (decay disabled) — dynamics robustness + H5 over-avoidance.
- ABL-12, ABL-13, ABL-14 (remove `c` / `t` / `r`) — per-variable necessity sweep.
- ABL-15, ABL-16, ABL-17 (provenance / self-report / receipts removed) — validity/firewall integrity checks (report as "no-change confirmations").

If space is tighter (4-page short track), collapse to ABL-01, ABL-11, ABL-06,
ABL-18 and cite the rest as pre-registered supplementary ablations.

---

## 8. Differentiator isolation map

The four differentiators (`02` §7) each need at least one ablation whose failure
would specifically retract that differentiator. This table makes the mapping
explicit so each novelty claim has a dedicated falsifier.

| differentiator                                            | isolating ablation(s)                                               | what the ablation controls for                                                                                  | failure meaning                                                                                     |
| --------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **1. Structured (not re-injected text) state**            | ABL-06 (reflection sub), ABL-19 (prompt-text), ABL-07/08 (encoding) | Holds information constant, varies only the _representation_ (numeric+structured vs prose vs binary vs scalar). | If text/binary/scalar match, "structured" adds nothing → differentiator #1 falls.                   |
| **2. Clamp/ablation causal proof (control/treated/null)** | ABL-11 (`s_m` clamp), ABL-02 (influence off), ABL-09 (update off)   | Isolates causation from correlation by removing the variable / its influence / its learning.                    | If clamping `s_m` doesn't remove the effect, H2 is false → differentiator #2 falls.                 |
| **3. Behaviour-vs-self-report firewall**                  | ABL-16 (self-report removed), ABL-18 (anti-gaming removed)          | Confirms prose is a read-out, not a driver, and that gains survive prose-blind adversarial scoring.             | If removing self-report changes behaviour, prose is on the path → firewall broken.                  |
| **4. Repeated-structural-failure metric (RUF)**           | ABL-04 (reset between tasks), ABL-05 (retrieval disabled)           | Confirms the effect is specifically _cross-task repeat reduction_, not within-task or retrieval-precision.      | If reset doesn't matter, the metric is measuring episodic recovery, not repeated-failure reduction. |

Note: ABL-04 doubles as the operational definition guard for RUF — it verifies
that what `RUF` measures (post-exposure cross-task recurrence) genuinely depends
on cross-task persistence and is not an artefact of within-task dynamics.

---

## 9. Consistency check against Locked Design Constants

- All clamp-based ablations (ABL-02, ABL-11–14, ABL-19) map to the four
  `PerturbationSet` seams named in `02` §8.3 (`scar_graph`, `self_model`,
  `affect_manifold`, new `memory_trust`) and run through the statistical causal
  path in `02` §8.8 (N-sample nulls, bootstrap effect sizes) — NOT the byte-equality
  gate, which caps a stochastic agent at Level 3.
- No ablation trains or updates the subject model's weights (`02` §8.5:
  `training_weight: 0.0`).
- The prose-blind evaluator (`02` §8.9) scores every behavioural row; self-report
  quality never feeds `RUF` (`02` §8.10), which is exactly what ABL-16 verifies.
- Falsification alignment: ABL-01 is the H1 falsifier, ABL-11 is the H2 falsifier,
  ABL-06 defends the primary reviewer objection — all pre-registered in `02` §6.

No deviations from `02` §8; no `15-decision-log.md` entry required.
