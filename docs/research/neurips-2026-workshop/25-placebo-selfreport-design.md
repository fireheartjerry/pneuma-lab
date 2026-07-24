# 25 — Someone Else's Regret: Primary Study Design

**Date:** 2026-07-24
**Status:** DESIGN. Freezes into a preregistration by 2026-08-07.
**Supersedes as primary study:** `23-placebo-memory-design.md`, which is retained as a
deferred instance of the same instrument.

---

## 1. The claim

When an agent fails and is given a helper — a reflection on what went wrong, a retrieved
example — it usually does better. The field credits the helper's **content**. But the helper
also changes the conditions of inference: more tokens, an extra model call, a structural cue
that the last attempt failed. Switching the helper off removes both at once.

We hold the apparatus exactly fixed and swap only the content, for a genuine helper about a
**different problem**. Then we ask not just whether the agent still succeeds, but **whether
it still believes it succeeded**.

> A verification pipeline that reads agent self-report may be reading the apparatus, and the
> apparatus is free to counterfeit.

## 2. Why the primary outcome is self-report, not task success

The task-success version of this experiment is **occupied**. Mehmet Iscan has three
preregistered, placebo-controlled, derangement-assigned studies on self-repair in frozen
small code models, on HumanEval+ / MBPP+, with length-matched and SHA-deranged placebos:

| arXiv      | Title                                                                                                                                                              | Verified |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- |
| 2606.06454 | Scaffold, Not Vocabulary? A Controlled, Two-Tier, Pre-Registered Study of a Popperian Code-Generation Skill                                                        | fetched  |
| 2606.31511 | Falsification, Not Exposure: An Internally Preregistered Placebo-Controlled Decomposition of Self-Repair Feedback in Frozen Small Code Models                      | fetched  |
| 2607.12962 | Form, Not Content? A Preregistered, Placebo-Controlled Evaluation of Learned Error-Conditioned Self-Repair Through Prompts and Weights in Frozen Small Code Models | fetched  |

A fourth entry in that cell is a replication and will be rejected as one.

**None of the three measures self-reported confidence or a decision to escalate to a
verifier.** Verified against all three abstracts. Neither does Stechly et al.
(arXiv:2310.12397), nor Min et al. (2022). That cell is empty, it is continuous and paired
so it is far better powered than a binary repair rate at our cluster count, and it is the
workshop's own title question.

The repair-rate decomposition is retained as a **powered, two-family extension of Iscan's
40-unit nulls** — cited as motivation in the introduction, never claimed as discovery.

## 3. Estimands

For each contrast, on each outcome:

$$
\Delta_C = \text{Real} - \text{Placebo}, \qquad
\Delta_A = \text{Placebo} - \text{None}, \qquad
\Delta_T = \text{Real} - \text{None}
$$

**These three differences are the primary reported estimands**, with simultaneous
cluster-resampled intervals. The confirmatory question is whether $\Delta_C$ is meaningfully
non-zero — never what fraction it represents.

### The ratio is demoted, deliberately

The content-to-total gain ratio $\Delta_C / \Delta_T$ is the **proportion mediated** of
mediation analysis and inherits its pathology: as $\Delta_T \to 0$ the estimand is
scientifically undefined, and valid confidence sets may be unbounded or disconnected. The
mediation literature's conclusion is that the proportion is optional and descriptive, that
attention belongs on the component effects, and that bounded replacements such as $\kappa^2$
developed their own failures of monotonicity.

Accordingly:

- The ratio is a **gated descriptive secondary**, reported only when a preregistered
  relative-precision condition on $\Delta_T$ is met.
- Intervals come from **studentized cluster-bootstrap Fieller inversion** — test inversion on
  $H_0: \Delta_C - q\,\Delta_T = 0$ — not from percentiles of a bootstrapped ratio.
- Unbounded or disconnected confidence sets are **reported as they come**. That is
  information, not a software failure.
- When the gate fails we print: _"content-to-total ratio not interpretable because total gain
  is weakly identified"_, and still report $\Delta_C$. The content analysis is never gated on
  the total effect.
- It is named the **content-to-total gain ratio**, not "content fraction". "Fraction"
  promises a stable partition the design cannot guarantee.

## 4. Outcomes

**Raw stated confidence is NOT the primary outcome.** Promoting it because it is unoccupied
would be choosing a measurement channel for its novelty rather than its validity — and there
is direct evidence against it: Iscan (arXiv:2606.06454) found a 0.5B self-judge performed no
better than random and concentrated 60% of its choices on a single index. An unvalidated
verbal channel cannot carry a paper.

**Primary — grounded self-report quality.**

Every attempt-2 ends with a fixed footer:

```
CONFIDENCE: <0-100>      # stated q = P(this repair passes the hidden tests)
ESCALATE: <YES|NO>
ROOT_CAUSE: <one line>
```

The primary outcome is not $q$ itself but **how well $q$ tracks truth**: $q$ is scored
against realized hidden-test correctness with a **proper scoring rule — negative Brier
loss** — and that score is decomposed by $\Delta_C$, $\Delta_A$, $\Delta_T$.

The question therefore becomes: **does a fake helper degrade the agent's ability to know
whether it actually succeeded?** That is a calibration claim against ground truth, not a
claim about a free-floating string, and it cannot be dismissed as prompt-induced verbosity.

**Secondary — escalation as an operational endpoint.** Analyzed by risk–coverage with a
preregistered human-cost utility, not as a raw frequency. **If escalation prevents observing
autonomous success, a sealed shadow repair is generated for every unit after the decision**,
so the counterfactual outcome always exists.

**Secondary anchor — repair rate.** EvalPlus hidden tests, all-pass boolean. Retained as the
objective outcome everyone already trusts.

### Self-report validity gate — held out, before any confirmatory analysis

Self-report is admissible as an outcome only if, on held-out calibration data, confidence is
**nondegenerate**:

- multiple occupied confidence bins,
- no single dominant canned value,
- positive discrimination between successes and failures,
- meaningful Brier improvement over a constant-base-rate predictor.

If it fails, self-report is just another generated string and is demoted to descriptive, with
the failure reported. That outcome is itself publishable: _verbalized confidence at this scale
has no usable signal to decompose._

**The named threat:** prompt-induced reporting behaviour masquerading as metacognition — the
helper shifts stated confidence or triggers escalation **without** changing the relationship
between confidence and correctness. Scoring against ground truth with a proper rule is
precisely what separates the two.

## 5. Arms

Eleven arms. Every arm shares a byte-identical five-slot attempt-2 prompt: task text, failed
attempt-1 code, **public failure signal (traceback + first failing visible example — present
in every arm, so it cannot confound the payload contrast)**, PAYLOAD SLOT, fixed instruction.

**Family R — post-failure reflection**

| Arm                  | Payload                                                                                                                                                                 |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `R0 NONE`            | length-matched, task-irrelevant neutral prose, token-exact to that tuple's real reflection. The real reflection is still generated and discarded, so call counts match. |
| `R1 PLACEBO-RANDOM`  | a genuine reflection the same model wrote about a uniformly random _other_ failed problem                                                                               |
| `R2 PLACEBO-MATCHED` | a genuine reflection about the TF-IDF nearest _other_ failed problem, selected on task text only                                                                        |
| `R3 REAL`            | the model's own reflection on its own failure                                                                                                                           |

**Family C — graded positive control**

| Arm                  | Payload                                                                                     |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `C1 ORACLE-FULL`     | reflection generated with hidden failing-test stderr visible — known-informative, high dose |
| `C2 ORACLE-REDACTED` | same, with assertion values and expected outputs masked — known-informative, low dose       |

Two doses rather than one pass/fail gate, so an all-null result is distinguishable from a
silent harness bug and we can report **the minimum content dose our instrument resolves**.

**Family M — retrieved solved-exemplar memory** (payloads cost zero extra generations)

`M0 NONE`, `M1 PLACEBO-RANDOM`, `M2 PLACEBO-MATCHED`, `M3 REAL`. $k=3$ exemplars, real =
nearest solved problems by task text, placebos = the exemplar set retrieved for a different
target under derangement.

**Shared**

`S RESAMPLE` — no payload, one additional independent attempt 2 at matched decoding and
matched compute. Without this the apparatus term is indistinguishable from extra sampled
compute, which the multi-agent literature has already shown matters.

## 6. Parity — measured, asserted, and reported as data

Never silently repaired. A parity failure is a reported defect.

1. **Token parity.** Payloads padded or truncated on sentence boundaries to the token count
   of that tuple's REAL payload; target ±2 tokens median; the realized distribution and its
   KS statistic reported. Placebo arms use the same tolerance as each other — no asymmetry.
2. **Item parity.** Identical $k$, identical bullet count.
3. **Structural parity.** Byte-identical header, delimiters, ordering, absolute prompt
   position.
4. **Call parity.** Identical number and order of model calls per (tuple, seed, arm),
   asserted at runtime; a violation aborts the batch.
5. **Decoding parity.** Identical temperature, top-p, max tokens, seed schedule.
6. **Leakage audit.** Any exemplar sharing an $\ge 8$-gram with the target reference solution
   is excluded from **all** arms. No self-donation. One independent derangement per seed.
7. **Manipulation check.** Deterministic TF-IDF / identifier-overlap, **not an LLM judge**.
   A judge-free paper cannot contain a judge.

## 7. Population and analysis

- **Benchmark:** EvalPlus — MBPP+ (378) ∪ HumanEval+ (164) = 542, minus a 60-problem
  calibration slice = **482 study problems**.
- **Attempt 1** generated **once** per problem at temperature 0 and graded. Only failures
  enter the study; each is one **failure tuple**. Expected pool ≈ 140 clusters, floor 110.
  Three retry seeds per tuple.
- **Independent unit:** the problem. Seeds and arms nest inside. **Two-way cluster bootstrap
  over target problem and donor problem**, because donors are shared across targets.
- **Grading:** EvalPlus hidden unit tests, subprocess-isolated, 10 s per test. No LLM judge
  in any primary, secondary, or manipulation check.
- **Model:** selected in Week 1 by preflight on the frozen calibration slice — the model
  whose greedy pass rate falls in $[0.55, 0.75]$. Candidates in order: Qwen2.5-Coder-7B-
  Instruct Q4_K_M, Qwen2.5-7B-Instruct Q4_K_M, Llama-3.1-8B-Instruct Q4_K_M.

**Power.** Repair-rate MDE at ~140 clusters is ~10 pp — near the edge, and openly stated as
such. Stated confidence is continuous and paired and resolves to roughly ±2 points at the
same cluster count. This is precisely why self-report is primary: **there is no
gate-passing scenario in which the paper has no number.**

## 8. What we claim, and what we do not

**We do not claim** to be first to run a placebo control on code self-repair. Iscan is. We
cite all three preprints in the introduction and position the repair-rate portion as a
powered, donor-arm, two-family extension of their nulls.

**We do not claim** anything about frontier models, multi-turn trajectories, tool use,
repo-scale tasks, or cross-episode memory. Our tasks are single-turn function repair. The
audited systems motivate the protocol; they are not tested here, and this is said in the
abstract, not the appendix.

**We do not claim** the placebo is inert. Donor reflections about near-duplicate problems can
be genuinely applicable; we measure that contamination via adoption rate and report content
estimates as **lower bounds** wherever PLACEBO-RANDOM exceeds NONE.

**Verbatim distinguishing sentences, for the related-work section:**

> _Versus Stechly et al. (arXiv:2310.12397):_ Stechly et al. corrupt the **correctness** of a
> critique on symbolic planning puzzles and ask whether the agent still improves; we hold the
> apparatus exactly fixed, swap in **uncorrupted content about a different problem**, anchor
> the contrast with graded known-informative doses, and ask what fraction of the gain and of
> the agent's **own stated confidence and escalation decision** survives.

> _Versus Min et al. (2022):_ Min et al. show in-context **demonstrations** survive randomized
> labels in classification, a statement about how models read few-shot exemplars; we intervene
> on an agent's **post-failure feedback channel** with real content about a different episode's
> failure, and measure the effect not only on task success but on the agent's self-reported
> confidence and on whether it asks a verifier to review its work.

## 9. Schedule and the hard gate

| Week | Dates           | Work                                                                                                                                                                     |
| ---- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | Jul 24 – Aug 1  | Grader, backend, attempt-1 sweep, payload builders, donor machinery, parity asserts. 60-problem calibration preflight. Select the study model.                           |
| 2    | Aug 2 – Aug 8   | 40-tuple pilot on all 11 arms, drawn from the calibration slice only. Validate analysis on synthetic ground truth. **Preregistration frozen to a commit hash by Aug 7.** |
| 3    | Aug 9 – Aug 15  | Confirmatory batch A: families R and C, four overnight batches.                                                                                                          |
| 4    | Aug 16 – Aug 22 | Confirmatory batch B: family M and RESAMPLE. Analysis script run **exactly once**.                                                                                       |
| 5    | Aug 23 – Aug 29 | Draft Aug 25, red-team Aug 26, anonymized artifact Aug 27, **submit Aug 28**.                                                                                            |

### HARD GATE — 2026-08-08, three criteria, all measured on the pilot

- **(a) Supply:** ≥ 110 failure-pool clusters in the study pool.
- **(b) Instrument sensitivity:** ORACLE-FULL − NONE ≥ 10 pp repair rate. This is the
  anti-silent-bug check. Failing it means the payload slot is broken, **not** that content is
  inert.
- **(c) Self-report variance:** footer parse rate ≥ 98% **and** cross-tuple SD of stated
  confidence ≥ 8 points.

**If (b) fails:** stop, debug the injection path, re-pilot once. Twice and no confirmatory
run launches.
**If (a) fails:** drop to the next preflight model, re-run attempt 1. Costs one day; budget
exists.
**If (c) fails:** confidence is saturated. Drop it from the primary family, promote escalation

- repair-rate decomposition, and state plainly that verbalized confidence at this scale has no
  variance to decompose — itself a reportable result.
  **If the gate fails outright and is unrepaired by Aug 12:** ship the 10-system audit, the
  parity protocol and checklist, the released harness, and the measured minimum detectable
  content dose from pilot data. Four pages, no confirmatory claim. A weaker paper that is still
  submitted.

**Preregistered descope order, fixed now, applied without deliberation:** drop C2 →
drop M1 → drop the third seed. Never drop R3/R2/R0, never drop S, never drop C1.

## 9b. The placebo construction — task-blind procedural

**This supersedes the placebo definitions in section 5.** The primary placebo is **not** a
donor reflection about a different problem.

The placebo is generated by the **same frozen reflector model** as the real reflection, under
an identical schema and field order, with every task-specific field replaced by
deterministic, token-count-matched `<withheld>` material.

|                              | Real reflector sees | Placebo reflector sees |
| ---------------------------- | ------------------- | ---------------------- |
| Problem statement            | yes                 | `<withheld>`           |
| Failed program               | yes                 | `<withheld>`           |
| Verifier / test feedback     | yes                 | `<withheld>`           |
| `language=Python`            | yes                 | yes                    |
| `verification_status=failed` | yes                 | yes                    |
| Output instructions          | identical           | identical              |

It may **never** see: problem text or identifiers, generated code, test names or values or
exceptions, algorithm/API/entity names, the real reflection, or any successful solution.

Both outputs use the same fixed schema (`Observation / Principle / Revision plan`), the same
decoding configuration, the same exact output-token budget, wrapper, delimiters, and position
in actor context. The placebo can offer generic procedural advice — reconstruct your
assumptions, check boundary cases — but cannot make a task-specific diagnostic claim.

**Why this and not the alternatives:**

- **Donor reflection from a different failed problem** — introduces concrete _irrelevant or
  false_ advice, so it estimates content versus **misinformation**, not content versus
  nothing. Retained as a separate arm because that contrast is interesting, but it is not the
  primary placebo.
- **Reflection about the same task from a run that succeeded** — leaks active solution
  information. Disqualified.
- **Entity-scrambled real reflection** — detectable corruption that can preserve partial
  diagnostic information while adding adversarial distraction. Disqualified.

## 9c. Interpretation — what the placebo contrast licenses

The placebo cannot be proven inert, so the language is constrained exactly.

**Licensed:**

> The placebo-minus-none contrast estimates the effect of adding a task-blind, structurally
> and computationally matched **generic helper**, including structural cues, generic
> procedural guidance, and possible distraction costs.

**Not licensed, and must not appear anywhere in the paper:**

> ~~The placebo-minus-none contrast isolates the pure causal effect of extra tokens,
> formatting, and model calls in the absence of informational content.~~

$\Delta_A$ is therefore the **nonspecific-helper effect**, never the "pure apparatus effect."

## 9d. PLACEBO-3 — the portable artifact

The exported contribution is a **standardized report**, not a number. It takes one row per
`independent_unit × arm × seed` for `real`, `placebo`, `none`, aggregates seeds within unit,
and computes cluster-resampled inference. Any paper running three arms on any scalar outcome
can feed it unit-level data and publish the generated card.

**Required report sections:**

| Section             | Fields                                                                                                                                                             |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Study identity      | helper type; model/checkpoint; benchmark roster; outcome and direction; independent unit; prompt templates; decoding policy                                        |
| Arm definitions     | the exact `real`, `placebo`, `none` interventions                                                                                                                  |
| Arm results         | $n$; mean for $R, P, N$; cluster-resampled interval for each                                                                                                       |
| Primary contrasts   | $\Delta_C$, $\Delta_A$, $\Delta_T$ — estimate, simultaneous interval, SESOI, decision                                                                              |
| Dominance           | $D = \Delta_C - \Delta_A$; estimate and simultaneous interval                                                                                                      |
| Gain verdict        | `gain-established` / `harmful` / `weak-unresolved`, from $\Delta_T$ and preregistered $\delta_T$                                                                   |
| Attribution verdict | `content-dominant` / `nonspecific-dominant` / `mixed` / `antagonistic` / `unresolved`                                                                              |
| Descriptive ratio   | $q = \Delta_C/\Delta_T$; gate result; Fieller set including unbounded or disconnected; else `not interpretable`                                                    |
| Parity receipt      | helper-output tokens; actor-context tokens; format; position; call counts; seed schedule; model/config equality; task-blind provenance; missing and failure counts |
| Inference receipt   | cluster variable; bootstrap draws; simultaneous critical-value method; confidence level; software version and seed                                                 |

**Verdict rules, fixed in advance:**

- `content-dominant` — $L(\Delta_C) > \delta_C$ **and** $L(D) > \delta_D$
- `nonspecific-dominant` — $L(\Delta_A) > \delta_A$ **and** $U(D) < -\delta_D$
- `mixed` — both components clear their positive margins, neither dominates
- `antagonistic` — components confidently opposite in sign
- `unresolved` — the joint region crosses category boundaries

**Emitted artifacts:** `placebo3.json`, a one-page card, a content-versus-nonspecific
joint-region plot, and the parity and inference receipts.

**Why it is adoptable:** it works for any scalar outcome, needs no bespoke statistical model,
preserves the actual effect sizes rather than collapsing them, and still yields a quotable
line — _"PLACEBO-3: gain-established, content-dominant."_

## 10. Model selection — a deterministic capability band

Selecting the model on anything downstream of the arms would be tuning on the result. The
rule below fixes the model **before any real or placebo reflection is ever generated.**

**Ladder, frozen in advance, same family so capability is the only varying factor:**
Qwen2.5-Coder 1.5B, 3B, 7B (Q4_K_M).

**Calibration set:** 96–120 executable Python problems, disjoint from the study roster, same
task and verifier format. For each candidate, run **only** three things:

1. initial attempt,
2. plain retry after failure,
3. retry with an **oracle bug hint** derived from the verifier.

**Real and placebo reflections are never generated during model selection.**

Measure $f_m$ (initial failure rate), $r_m$ (plain-retry success among failures), $o_m$
(oracle-hint success on the same failures), $u_m = o_m - r_m$ (paired oracle responsiveness),
plus output validity, timeout rate, tokens, and throughput.

**Eligibility** — a model qualifies only if all hold:

- projected usable failures satisfy
  $N_{\text{main}} \cdot L_{90}(f_m) \cdot (1 - \text{attrition}) \ge n_{\min}$
- oracle uplift has $\hat u_m \ge 0.15$ and $L_{90}(u_m) > 0$
- plain retry does not exhaust the available headroom
- format and execution validity clear a preregistered threshold
- the complete run fits the compute deadline

**Then select the LARGEST eligible model — not the one with the largest estimated uplift.**
That yields a band: strong enough to use diagnostic information, weak enough to leave the
required failure roster, and chosen without observing any of $\Delta_C$, $\Delta_A$,
$\Delta_T$.

If none qualifies, expand a roster frozen in advance or declare a feasibility no-go.
**Do not descend to a toy model just to grow $n$.** "Weaker means more correctable" is not
safe — intrinsic self-correction can fail or actively degrade performance at small scale.

After selection, run the frozen initial-attempt census on the study roster. If the realized
eligible count falls below $n_{\min}$, apply the preregistered expansion-or-no-go rule
**before any arm outcomes exist**. Never switch models because the real reflection effect
looked disappointing.

## 11. Corrections to sections 7 and 9

These supersede the corresponding text above.

**One frozen initial attempt per problem**, deterministic or under a single preregistered
seed. Clone only failed prefixes across arms. Do **not** generate several initial attempts
and keep whichever seeds happened to fail — that is regression-to-the-mean soup.

**Problem is the independent unit, after cross-benchmark duplicate and lineage checking.**
Seeds are nested replicates, aggregated within problem _before_ cluster resampling. They buy
measurement precision; they do not manufacture $n$. Pool with equal problem weights,
stratify randomization and bootstrap by benchmark, and report both benchmarks separately.

**The population, stated honestly:** _problems in the frozen, deduplicated
HumanEval+ / MBPP+ roster failed by the selected checkpoint under the frozen initial-attempt
policy._ The claim is about that 542-task roster, not about coding tasks in general.
(MBPP+ is 378 — EvalPlus reduced it from 399 after removing broken tasks.)

**Prompt-template library.** A single handcrafted prompt makes the result a property of that
prompt. Freeze **three** meaning-preserving attempt-2 templates, randomize template
assignment across problems, define the primary estimand as the average over that finite
library, and report template-specific contrasts plus the template-by-arm interaction. Each
problem still runs once per arm — the existing experiment is distributed across variants
rather than tripled. It generalizes only to those three templates, which is far stronger than
one incantation.

**Power, stated without optimism.** ~270 problems detects roughly 8–10 points under
favourable paired discordance; simultaneous intervals and worse discordance push the
effective MDE above 10. **Five points is out of reach and we will not claim otherwise.**
And published reflection gains are estimates of exactly the confounded total contrast we are
criticising — they are a **ceiling, not a prior** for $\Delta_C$. This is another reason
self-report is the primary outcome.

## 12. Standing obligation

Weekly arXiv sweep on `placebo AND (self-repair OR agent OR retrieval)` through Aug 20. Six
adjacent papers appeared between March and July 2026 and the rate has not slowed. If a fourth
paper lands on self-report specifically, pivot the headline to the between-family
content-ratio contrast, which remains unoccupied.
