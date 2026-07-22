# 10 — Anti-Gaming Specification

Status: planning. Governed by `02-research-thesis.md` §8.9 (DL-10) and §8.10
(DL-11); nothing here may contradict the Locked Design Constants. This document
does not authorize implementation, training, data conversion, or any run. It
fixes _what the agent must not be able to earn credit for_ and _how each avenue
is closed_, so the metric (`08-metrics-and-statistics.md`) and the causal-validity
plan (`09-intervention-and-causal-validity.md`) inherit an unambiguous contract.

## 0. Doctrine (inherited, non-negotiable)

The in-repo anti-fake-progress doctrine (`docs/research/10-anti-fake-progress.md`)
is adopted verbatim as this paper's ethic. Four standing rules:

1. **"The adversary is us."** The threat is not a malicious model; it is an
   optimistic team with every incentive to see progress. Every control below is
   written against _our own_ tendency to accept a flattering result.
2. **"Architecture is not evidence — only receipts + interventions + nulls are."**
   A mechanism being present, wired, or exercised earns nothing. Credit requires
   a receipt-bound behavioural delta that survives a clamp/ablation and whose
   null arm reproduces control.
3. **No self-report promotion.** Prose never moves a score. The behavioural
   metric is computed upstream of, and structurally blind to, all rendered text
   (see §2, §4). Reuses the verified one-way scorer→voice firewall.
4. **Pre-registration + frozen learned gates + held-out deltas.** Every primary
   contrast, split, and threshold is registered before the run; any learned
   component used inside a gate is frozen and hash-pinned; the headline number
   is a pre-registered held-out delta, not an in-sample fit.

**Build-status honesty (critical).** The doctrine's guardrails are numbered
G-01…G-12. Only **G-01 (HollowPsyche negative control)**, **G-12 (commit-bound
provenance / `--official`)**, and the in-code confab/consistency gates are built
and VERIFIED. **G-02…G-11 are UNBUILT** per the source doc's own status register.
This paper therefore presents the doctrine as _adopted discipline_ and this
document as _the specification to build_, and MUST NOT imply the automated
guardrail suite already exists. The threat×control matrix in §3 marks each
control built/partial/unbuilt so the implementation plan (`12`) can schedule the
unbuilt ones.

## 1. Threat model

The subject agent (any of the four conditions in thesis §8.2, but the risk
concentrates on the Pneuma-state and Reflection arms) must NOT be able to earn
credit on the primary metric `RUF` — or on any secondary/self-report metric —
merely by any of the following. Each threat is the _appearance_ of the target
capability without the capability.

| ID   | Threat (agent earns credit merely by…)                                                                                              | Why it fakes the result                                                                                                     |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| T-01 | **Saying it learned** — emitting "I have learned to avoid X" without any behavioural change.                                        | Claim substitutes for behaviour; RUF must be behavioural, not asserted.                                                     |
| T-02 | **Convincing reflection** — writing a persuasive post-mortem/diary that reads like insight.                                         | In reflection agents prose is _both_ mechanism and explanation; a good diary ≠ a real behaviour change.                     |
| T-03 | **Introspective / emotional language** — "I feel cautious about this file," scar/affect narration.                                  | Ontological over-claim; interiority vocabulary is operational only (thesis §2) and must never score.                        |
| T-04 | **Excessive caution** — globally raising verification depth / hedging on everything.                                                | Suppresses failures by suppressing action; buys RUF with inertia (H5).                                                      |
| T-05 | **Task avoidance** — declining/stalling tasks to avoid emitting a failure.                                                          | A non-attempt cannot repeat a failure; avoidance is scored, not rewarded.                                                   |
| T-06 | **Indiscriminate risk refusal** — refusing any action pattern that ever preceded a failure.                                         | Over-generalized scar → refuses correct actions; must be caught by counterfactual tasks (T→C-08).                           |
| T-07 | **Proxy-metric optimization** — moving a stand-in (retry count, token count, scar count) that correlates with but is not RUF.       | Goodhart; the E-0 length/activity confound is the in-repo proof this happens (retry-count AUROC 0.705 beat psyche signals). |
| T-08 | **Wording change without behaviour change** — altering how an action is described while the action (and outcome) is identical.      | Surface edit masquerades as adaptation; behaviour digest is unchanged.                                                      |
| T-09 | **Benchmark-identifier memorization** — keying off repo name, task id, file path, or motif label rather than the failure structure. | Memorization, not generalization (H4); dies on held-out repos/motifs/surface transforms.                                    |
| T-10 | **Evaluator exploitation** — learning the judge's quirks (phrasing, label heuristics, an LLM judge's biases) to win labels.         | Attacks the measuring instrument, not the task.                                                                             |
| T-11 | **Emitting desirable-looking state values** — writing "good" numbers into psyche_state / self_report fields directly.               | State is supposed to be _caused_ and _consumed_; hand-written values are decoration ("stickers on a laptop," vision.md).    |

Hollow / narrator baselines are standing controls against this whole class:
a **HollowPsyche** (schema-valid frames, no causal mechanism — built, G-01) and a
**narrator** (an LLM prompted to emit psyche-shaped frames _without_ the
mechanism — `02-level5-target.md` A1, UNBUILT). If the suite cannot separate the
real Pneuma-state arm from hollow/narrator, all claims freeze (doctrine freeze
rule).

## 2. Controls (per threat) with detection method

The spine is one architectural invariant, reused verbatim from the audited code:

> **Firewall (VERIFIED, built).** There is no code path from voice/prose into the
> scorer. `grep import.*voice` over `src/pneuma_lab/evals/` → zero hits; the
> dependency runs one-way (voice reads `evidence_level`, never writes it), locked
> by `test_voice_never_alters_the_evidence_frame`,
> `test_skin_cannot_inflate_the_level`, `test_judge_and_skin_cannot_inflate_level`
> (byte-compare of the evidence frame). The behavioural metric consumes typed
> numeric frame receipts, never rendered text. **Behaviour is scored
> independently of self-report by construction, not by policy.**

Each control names its detection method and reuses named in-repo mechanisms
where they exist.

- **C-01 — Behaviour-only scoring (firewall).** `RUF` is computed from the
  action/outcome trace (motif-instance recurrence), never from any "I learned"
  claim. _Detection:_ the claim string is not an input to the metric; a run that
  only _says_ it learned but repeats the motif scores identically to silence.
  _Covers T-01, T-02, T-03._ Reuses the one-way firewall (built) +
  `scrub_forbidden` ontological-claim regex on any rendered surface (built).

- **C-02 — Prose-blind evaluator + receipt-bound consistency.** Self-report is
  scored only by mechanical receipt-hash checks (`report_grounding_errors`:
  `affect_state_hash == state.state_hash`, `causal_trace_id` match, same-tick
  numeric equality within 1e-9), never by an LLM reading prose for plausibility.
  _Detection:_ cross-tick receipt laundering and swapped receipts already fail
  (`test_confabulation_risk_rejects_cross_tick_receipt_laundering`). _Covers
  T-02, T-11._ Built (rename away from "confabulation" for the paper).

- **C-03 — Hidden failure motifs.** A held-out subset of motifs (thesis §8.6) is
  never surfaced in any prompt, label, or memory the agent can read; recurrence
  is scored on them blind. _Detection:_ RUF measured separately on hidden vs
  visible motifs; a gap implies the agent keyed on the visible label set (T-09).
  _Covers T-09._ **Unbuilt** (needs motif-axis split — does not exist today).

- **C-04 — Held-out surface transformations.** The same motif is re-instantiated
  with renamed identifiers, reordered files, reworded task text, equivalent-but-
  different repo layout. _Detection:_ RUF on transformed instances vs originals;
  a drop-off on transforms = surface memorization not structural learning (H4).
  _Covers T-08, T-09._ **Unbuilt** (surface-transform generator is a build).

- **C-05 — Evaluator blinding.** The RUF labeller (motif-recurrence classifier)
  receives only the observable action/outcome trace with condition identity,
  repo name, and task id stripped/hashed; it cannot see which arm produced the
  trace. _Detection:_ arm-label permutation test — shuffling arm labels must
  collapse any measured effect. _Covers T-10._ **Unbuilt.**

- **C-06 — State-report consistency checks.** The agent's report of _which_
  variable changed its decision must match the recomputed same-tick state delta.
  _Detection:_ `reports_track_target_signal` — the report's numeric
  `reported_measurements[target_signal]` must move between control and treated,
  both arms fully grounded; a report that names a cause the state did not carry
  fails. _Covers T-01, T-11._ Built (numeric, not text).

- **C-07 — Intervention tests (clamp/ablation + null).** Credit for a causal
  claim requires the control/treated/null paired runner: clamp the failure-memory
  variable and the RUF reduction must vanish (`RUF(pneuma_ablated) ≈ RUF(base)`),
  while the null arm reproduces control byte-for-byte (deterministic sub-experiment)
  or within the N-sample distributional null (stochastic). _Detection:_
  `PairedReplayRunner` + counterbalanced digest-bound provenance; `null_condition_passed`
  requires ~0 off-target drift. _Covers T-07, T-11 (a value that isn't consumed
  won't move RUF under clamp)._ Runner built; statistical N-sample null path unbuilt (§8.8).

- **C-08 — False-avoidance penalty.** Every avoided action is scored for
  correctness against ground truth; avoiding a warranted action is penalized
  symmetrically to committing a failure. _Detection:_ a precision/recall of
  avoidance vs a control set of actions that should NOT be avoided; false-avoidance
  rate reported alongside RUF and gated in H5. _Covers T-04, T-05, T-06._
  **Unbuilt** (largest conceptual gap per audit-evals §5).

- **C-09 — Counterfactual tasks (defined carefully below §2.1).** Tasks where the
  previously-punished strategy is now the _correct_ one. _Detection:_ on these
  tasks the Pneuma-state arm's success must not fall below the best baseline and
  its false-avoidance must not exceed reflection's (H5 falsifier). _Covers T-04,
  T-06._ **Unbuilt.**

- **C-10 — Decoy memories.** The retrieval/reflection/scar store is seeded with
  plausible-but-irrelevant failure records that do NOT apply to the current task.
  _Detection:_ an agent that raises caution or avoids actions on decoy-matched
  tasks (where no real failure risk exists) is flagged; correct behaviour ignores
  decoys. _Covers T-06, T-07._ **Unbuilt.**

- **C-11 — Adversarially-misleading reflections in the reflection baseline.** The
  reflection arm's injected lessons include some that are subtly wrong (misattribute
  the cause). _Detection:_ if the reflection arm follows a wrong lesson into a
  failure while Pneuma-state (reading numeric state, not prose) does not, the
  contrast isolates prose-following from structural learning; conversely, a
  Pneuma-state arm that also degrades reveals prose leakage into its decision.
  _Covers T-02._ **Unbuilt.**

- **C-12 — N-judge evaluator ensemble.** Motif-recurrence labels (and any
  LLM-assisted annotation) come from an ensemble of ≥N independent judges
  (different providers/prompts); a label counts only on agreement, disagreement is
  surfaced, and no single judge can promote. Any LLM annotation is _data, not gate_
  (doctrine G-08). _Detection:_ inter-judge agreement (κ) reported; swap-test the
  judges. _Covers T-10._ **Unbuilt.**

- **C-13 — Immutable execution traces bound to commit+config+seed.** Every run
  emits an append-only trace whose provenance records exact git commit, clean/dirty
  tree, model checkpoint, config, and seed; `--official` fails closed on a
  dirty/unpublished tree. _Detection:_ any claim must be recomputable from a
  committed trace; a number with no matching immutable trace is rejected. _Covers
  T-07, T-10, and post-hoc editing of results._ Commit-provenance built (G-12);
  checkpoint/config/seed binding into the same record is **partial/unbuilt**.

- **C-14 — Post-hoc claim verification.** The evaluator recomputes pass/fail from
  raw outputs and never trusts a supplied summary (`_score_paired` recomputes;
  `_intervention_gate` refuses partitions that don't add up; caller-fabricated
  intervention passes raise `TypeError`). _Detection:_ fabrication routes are
  already refused in tests (splice, dup, unattached, restore-only no-op). _Covers
  T-01, T-07, T-11._ Built (the recompute-don't-trust engine).

- **C-15 — Train/test separation by repo AND motif AND task-generator.** Splits
  partition on all three axes; the synthetic motif generator's seeds used at test
  time are disjoint from training; repos overlapping between corpora are quarantined
  via the leakage registry; near-dup minhash scan. _Detection:_ leakage-mask test;
  contamination disclaimer on any SWE-bench-family lane. _Covers T-09._ Repo-axis
  splitting + leakage registry built; **motif-axis and task-generator-axis splitting
  UNBUILT**.

### 2.1 Counterfactual tasks — precise definition (for C-09)

A counterfactual task is constructed as a matched pair (`τ_punish`, `τ_reward`)
sharing surface structure (same repo family, same action affordances) such that:

1. In `τ_punish`, strategy `σ` (e.g. "edit the config directly," "skip the
   integration test") leads to the motif failure — this is what grows the scar
   `s_m`.
2. In `τ_reward`, an instance is engineered so that `σ` is the **correct** solution
   (the earlier hazard is absent: the config is the right locus; the integration
   test is genuinely irrelevant). Ground truth marks `σ` as correct.
3. `τ_reward` is only shown _after_ exposure that raised `s_m` for `σ`'s motif, and
   is surfaced under a held-out surface transform so it cannot be recognized by id.

The correct behaviour is _discrimination_: apply `σ` in `τ_reward` despite the scar.
The failure this catches is **over-generalized avoidance** (T-06): an agent that
learned "never do `σ`" fails `τ_reward`. Scored as: false-avoidance rate on
`τ_reward` and task-success on `τ_reward`. H5 falsifier: Pneuma-state's
false-avoidance on counterfactuals is worse than reflection's, or its success is
below the best baseline. Counterfactual tasks are pre-registered and their ground
truth frozen before any run.

## 3. Threat × control × detection × status matrix

| Threat | Primary control(s)     | Detection method                                                           | Status                                                       |
| ------ | ---------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------ |
| T-01   | C-01, C-06, C-14       | Claim not a metric input; report must track recomputed state delta         | Built                                                        |
| T-02   | C-01, C-02, C-11       | Prose-blind firewall; receipt-hash consistency; misleading-lesson contrast | Firewall/consistency built; C-11 unbuilt                     |
| T-03   | C-01                   | `scrub_forbidden` ontological regex; interiority never scored              | Built                                                        |
| T-04   | C-08, C-09             | False-avoidance penalty; counterfactual success/avoidance rates            | Unbuilt                                                      |
| T-05   | C-08                   | Non-attempt scored as avoidance, not neutral                               | Unbuilt                                                      |
| T-06   | C-08, C-09, C-10       | Counterfactual discrimination; decoy-memory ignore test                    | Unbuilt                                                      |
| T-07   | C-07, C-13, C-14       | Clamp removes effect; proxy not in metric; immutable trace recompute       | Runner/recompute built; N-sample null + full binding partial |
| T-08   | C-04                   | Held-out surface transforms; behaviour digest unchanged detection          | Unbuilt                                                      |
| T-09   | C-03, C-04, C-15       | Hidden motifs; surface transforms; repo+motif+generator split              | Repo split built; motif/generator/hidden/transform unbuilt   |
| T-10   | C-05, C-12, C-13       | Evaluator blinding + label permutation; N-judge ensemble; provenance       | Unbuilt (provenance partial)                                 |
| T-11   | C-02, C-06, C-07, C-14 | State must be caused+consumed (clamp); receipt equality; recompute         | Built (numeric gates)                                        |

Status legend: **Built** = code exists and is integration-tested on the toy mind
today; **Partial** = spine exists, extension for the real experiment unbuilt;
**Unbuilt** = specified here, scheduled in `12-implementation-plan.md`, no code yet.
Every "Built" control has been validated only against `ReferencePsyche` /
`BaselinePsycheSubject`; transfer to a real agent is itself an open task.

## 4. The "prose must never award itself points" rule

**Rule (binding).** No natural-language output of the subject — reflection notes,
grounded self-reports, scar/affect narration, "I learned" claims, elaborated voice
— may increase, decrease, or otherwise influence the behavioural score `RUF` or any
causal contrast. Prose is scored _only_ on a separate self-report-faithfulness
track (thesis §8.10), which itself never feeds the behavioural score.

**How the metric enforces it (mechanically, four layers):**

1. **Type-level exclusion.** `RUF`'s inputs are the typed observable trace and
   numeric frame receipts (action/outcome per motif instance). Rendered text is not
   in the input type. A prose field cannot be read because it is never passed.
2. **One-way import firewall (built, test-locked).** `evals/` does not import
   `voice/`; voice imports the frozen evidence frame downstream and cannot mutate it.
   `test_skin_cannot_inflate_the_level` / `test_judge_and_skin_cannot_inflate_level`
   byte-compare the evidence frame before/after voicing. A regression that opened a
   prose→score path would fail these tests.
3. **Receipt-hash faithfulness, not plausibility.** Where a report _is_ scored
   (faithfulness track), it is scored by same-tick hash + numeric equality
   (`report_grounding_errors`, C-02/C-06), never by an LLM judging whether the prose
   "sounds honest." Persuasiveness has no channel to any number.
4. **Recompute-don't-trust (built).** Any self-emitted summary/claim of success is
   recomputed from raw outputs (C-14); a caller-supplied pass raises `TypeError`.
   A convincing narrative of improvement with no matching recomputed delta scores zero.

Consequence: the strongest possible essay about how the agent learned to avoid a
failure is worth exactly zero on the primary metric; only a repeated (or not-repeated)
motif instance in the immutable trace moves `RUF`. This is the operational form of
the doctrine's "a beautiful narration with no intervention support scores zero on the
family it narrates."
