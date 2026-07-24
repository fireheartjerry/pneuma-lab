# 23 — Placebo Memory: Experiment Design

**Date:** 2026-07-24
**Status:** DESIGN. Freezes into a preregistration before any evaluation data is read.
**Supersedes:** the pilot described in `21-pivot-and-claim-retirement.md` §4. This is the
paper's primary experiment, not a nuisance-parameter pilot.

---

## 1. The question

Agent-memory systems report large gains. Every published comparison in our audit is
**memory-on versus memory-removed**, which confounds two different things:

- the **content** of what was remembered, and
- the **apparatus** that carries it — extra retrieved context, an extra reasoning step, a
  longer prompt, an additional model call.

A memory system that helps only because it lengthens the prompt is not a memory system.
No paper in the audited frame separates these. `22-audit-rubric.md` field F5 returned
`ablation_only` or `none` for **10 of 10** systems.

This experiment runs the missing control.

---

## 2. Estimand

Four arms produce a three-way decomposition of the total reported gain:

$$
\underbrace{\text{Real} - \text{None}}_{\text{total gain}}
= \underbrace{(\text{Real} - \text{P}_{\text{match}})}_{\text{content}}
+ \underbrace{(\text{P}_{\text{match}} - \text{P}_{\text{rand}})}_{\text{plausibility}}
+ \underbrace{(\text{P}_{\text{rand}} - \text{None})}_{\text{apparatus}}
$$

- **Apparatus effect** — what you get from retrieval-shaped context of the right size and
  format, containing nothing relevant.
- **Plausibility effect** — what you get additionally when that irrelevant context _looks_
  topically related to the question.
- **Content effect** — what you get additionally when the retrieved facts are actually the
  user's own.

**Primary endpoint:** the content effect. **Primary claim:** the fraction of the total gain
attributable to content, with a clustered simultaneous interval.

This decomposition does not exist in the agent-memory literature. It is the contribution.

---

## 3. Arms

All four arms share one frozen model, one prompt template, one retrieval implementation,
one value of `k`, and one decoding configuration. Only the **contents of the retrieved
set** differ.

| Arm               | Retrieval runs | Retrieved items drawn from                                                | Purpose               |
| ----------------- | -------------- | ------------------------------------------------------------------------- | --------------------- |
| `none`            | no             | —                                                                         | floor                 |
| `placebo_random`  | yes            | a **donor** user's memory store, selected without regard to the query     | isolates apparatus    |
| `placebo_matched` | yes            | the **donor** store, selected by nearest-neighbour to the query embedding | isolates plausibility |
| `real`            | yes            | the **target** user's own store, nearest-neighbour to the query           | published condition   |

### Donor assignment

Donors are assigned by a **fixed derangement** over the target set, seeded and recorded in
the preregistration before any evaluation run. No target may be its own donor. The mapping
is published with the artifact. This is not re-drawn if results are unfavourable.

### Parity requirements — these are validity gates, not aspirations

Every one is measured per item and reported; a failure is a reported defect, not a silent
repair.

1. **Item-count parity.** All three retrieval arms return exactly `k` items.
2. **Token-length parity.** The distribution of injected-context token counts must not
   differ across the three retrieval arms by more than a preregistered tolerance. Report
   the realized distributions.
3. **Structural parity.** Identical serialization, ordering convention, delimiters, and
   position in the prompt.
4. **Call parity.** Identical number of model calls, identical decoding parameters,
   identical seed schedule.
5. **No leakage.** A donor store must contain no memory originating from the target user.
   Verified by identity check, not by assumption.

If `placebo_random` cannot be made token-matched to `real` — because real retrieval returns
systematically longer or shorter items — that asymmetry is itself reported and the analysis
adds injected-token count as a covariate.

---

## 4. Dataset

**LongMemEval** (arXiv:2410.10813), `LongMemEval_S`.

Chosen over LoCoMo on statistical grounds. LongMemEval compiles a **separate chat history
per question**, so questions do not share a conversation. Its coarsest generator grouping is
the 164-attribute ontology.

|                                |               LoCoMo |             LongMemEval |
| ------------------------------ | -------------------: | ----------------------: |
| Observations                   |      ~2000 questions |           500 questions |
| Coarsest grouping              | **10 conversations** | **164 user attributes** |
| Effective $n$ at $\rho{=}0.05$ |                  183 |                     454 |
| Effective $n$ at $\rho{=}0.20$ |               **49** |                 **355** |
| Effective $n$ at $\rho{=}0.50$ |                   20 |                     247 |

Design effect $\text{DEFF} = 1 + (m-1)\rho$ with $m$ = observations per cluster.

**Independent unit for all inference: the user attribute (164).** Not the question.
Registered before any run, consistent with `22-audit-rubric.md` F2.

---

## 5. Sample size

Minimum detectable difference for the paired content contrast, one-sided $\alpha = 0.05$,
80% power, by discordant-pair rate:

| $n_\text{eff}$ |  disc 0.15 |  disc 0.25 |  disc 0.40 |
| -------------: | ---------: | ---------: | ---------: |
|            100 |     9.6 pt |    12.4 pt |    15.7 pt |
|            200 |     6.8 pt |     8.8 pt |    11.1 pt |
|        **355** | **5.1 pt** | **6.6 pt** | **8.3 pt** |
|            500 |     4.3 pt |     5.6 pt |     7.0 pt |

Published agent-memory gains are 20–30 points. At the expected $n_\text{eff} \approx 355$
the study resolves a content effect down to roughly a fifth of a typical claimed gain.

**Powered no-go rule, frozen before running:** if the measured attribute-level ICC pushes
$n_\text{eff}$ below 150, the content contrast is reported as **inconclusive with a stated
interval**. It is never rescued by switching the independent unit to the question.

---

## 6. Secondary endpoint — placebo-induced fabrication

LongMemEval contains 30 abstention items whose correct answer is that the information was
never provided. The registered secondary question:

> Does injecting another user's memories cause the agent to confidently answer questions it
> should decline?

Endpoint: abstention accuracy on those items, by arm. A drop from `none` to
`placebo_matched` is direct evidence that plausible-but-wrong retrieved context manufactures
false confidence. This rides free on the same runs and requires no additional generation.

---

## 7. What we implement

**Not a reimplementation of any named system.** We implement the _canonical_ architecture
shared across the audited frame — extract atomic facts from the history, embed, retrieve
top-`k` by cosine, inject into context — and say so plainly.

This is deliberate. Reimplementing Mem0 or A-MEM invites a "you built it wrong" rebuttal and
makes the result about one system. Testing the shared architecture makes the result about
the class, and removes reimplementation risk from the critical path.

Where the canonical architecture underperforms a published system, that is stated as a
limitation, not hidden.

---

## 8. Analysis plan — frozen before any evaluation data is read

- **Unit:** user attribute (164). Whole-cluster resampling throughout.
- **Intervals:** attribute-clustered bootstrap, ≥ 10,000 draws, studentized max-T
  simultaneous one-sided bounds across the three decomposition contrasts.
- **No Wald intervals.** At this cluster count a Wald interval is a correctness bug.
- **Judge:** one pass, not repeated. Judge stochasticity is measured separately on a
  subsample and reported as a distinct quantity — it is **never** presented as the study's
  uncertainty. This is the exact error documented in the audit and we do not repeat it.
- **Multiplicity:** the three decomposition contrasts form one family under simultaneous
  max-T bounds. The abstention endpoint is registered secondary and receives no confirmatory
  p-value.
- **Missingness:** a generation failure, refusal, timeout, or malformed output is scored
  adverse and stays in the denominator. Denominator is fixed by the item roster before any
  run.

---

## 9. What we do not claim

- Not that any published memory system does not work. We test a canonical architecture on
  one benchmark with one model.
- Not that the placebo arms are the only possible controls. They are the ones nobody ran.
- No claim about consciousness, interiority, or machine experience. The word does not appear.
- Single model, single benchmark, single language. Stated as a limitation, not buried.

---

## 10. Why both outcomes are publishable

| Outcome                              | Reading                                                                                                            |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| content $\approx$ 0, apparatus large | The field's gains are prompt engineering. Bombshell, and it explains the audit's findings.                         |
| content large, apparatus small       | The first properly controlled causal evidence that memory content matters. That evidence currently does not exist. |
| content moderate, plausibility large | Retrieved context works largely by _looking_ relevant. Novel and uncomfortable.                                    |
| inconclusive                         | Reported with the interval and the powered no-go rule, alongside the audit. Still a paper.                         |

The design is chosen so that no result requires spin.

---

## 11. Execution

| Milestone                                                      | Date       |
| -------------------------------------------------------------- | ---------- |
| Design frozen, donor derangement seeded and committed          | 2026-07-28 |
| Canonical memory implemented, parity gates green on fixtures   | 2026-08-02 |
| Preregistration frozen — arms, endpoints, analysis, no-go rule | 2026-08-05 |
| Runs complete (4 arms x 500 items)                             | 2026-08-12 |
| Analysis, figures, audit table finalized                       | 2026-08-18 |
| Full draft                                                     | 2026-08-24 |
| Anonymization and submission gates                             | 2026-08-27 |

**Compute.** 4 arms x 500 items = 2000 generations, plus judging. On a local 7B model at
laptop throughput this is on the order of 16–20 hours of generation — one to two overnight
runs. No cloud dependency. Cloud credits are a schedule buffer, not a requirement.

**Hard gate 2026-08-12.** If runs are not complete, the submission falls back to the audit
paper at 4 pages with the placebo design published as specified-but-not-run. That fallback
requires zero further compute.
