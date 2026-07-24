# Ten Conversations, Two Thousand Questions

**What agent-memory evaluations could actually have detected.**

**Target:** Who Verifies the Agents? — Toward Reliable Agent Development @ NeurIPS 2026.
4–9 pages, double-blind, non-archival, **2026-08-29 AoE**. Fallback: IAB @ NeurIPS 2026.

---

## In one paragraph

Papers that add memory to an AI agent report how many test items they ran — two thousand
questions, a thousand tasks, a hundred human ratings. But those items are not separate
experiments. The two thousand questions come from **ten conversations**. The thousand tasks
come from **five websites**. The hundred ratings all come from **one simulation**. Statistics
treats repeated looks at the same thing very differently from independent samples, and every
error bar in this literature assumes the wrong one. So we go back through the published
record, work out what size of improvement each study could actually have detected once you
account for that, and compare it to the improvement each study claims. The question is not
whether these systems work. It is how many of these papers could have told the difference.

## The core distinction

We **do not** compute effective sample size — it is not identifiable from published
information. The design effect is $\text{DEFF} = 1 + (m-1)\rho$, and $\rho$ is never
reported. Substituting the cluster count for $n$ assumes $\rho = 1$, a worst-case bound.

So the minimum detectable effect is reported **across an ICC grid** as an identified range,
single-cluster designs are marked **non-identifiable**, and the headline is **how often a
conclusion changes** — not how large the ratios are.

## Documents

| Doc                                     | Contents                                                                                                |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `26-detectability-audit-design.md`      | **The paper.** Claim, method, verdict rules, positioning, schedule. Start here.                         |
| `22-audit-rubric.md`                    | The frozen nine-field rubric. Quote-backed cells, no inter-rater coefficient, mandatory self-inclusion. |
| `21-pivot-and-claim-retirement.md`      | Five retired novelty claims with per-citation verification.                                             |
| `15-decision-log.md`                    | Append-only. DL-46 onward record every pivot.                                                           |
| `24-placebo-program.md`                 | The placebo-control method. Deferred — the area is saturated.                                           |
| `25-placebo-selfreport-design.md`       | Deferred design: placebo self-report on EvalPlus.                                                       |
| `23-placebo-memory-design.md`           | Deferred design: placebo memory on LongMemEval.                                                         |
| `supplementary/literature-landscape.md` | Background. Not instructions.                                                                           |
| `archive/protocol-v2/`                  | The superseded seven-arm causal study. Provenance only.                                                 |

## Position

| Work                 | Owns                                    | Leaves                                                |
| -------------------- | --------------------------------------- | ----------------------------------------------------- |
| Card et al. 2020     | the audit-for-power paper shape, in NLP | treats items as **independent**; not agent evaluation |
| Miller 2411.00640    | clustered SEs for LLM evaluation        | audits no published paper                             |
| Bjarnason 2602.07150 | measured run variance, 60k trajectories | _recommends_ power analysis, does not perform one     |
| Huang 2607.12338     | how many tasks reproduce a decision     | reproduction, not power; audits no paper              |

**Air gap:** nobody has shown, over a corpus of published agent-memory results, how often the
reported conclusion fails to survive an estimand-aligned clustering correction.

## Status

- **Coded:** 10 of ≤25 systems, quote-backed. Frame expansion in progress.
- **Findings so far, scoped to the coded frame:** 10/10 report uncertainty over the wrong
  variance component; 0/10 run an inert-content null; 0/10 pre-specify a decision rule; 2/10
  do not state the count of their own coarsest grouping.
- **Compute required:** none.

## Invariants

- Standalone. No imports from `C:\9to5`. `training_weight: 0.0`.
- Every non-numeric cell backed by a verbatim quote. No inter-rater coefficient — two
  instances of one model are not independent raters.
- No claim scoped wider than the coded sample and date range.
- No claim about consciousness, sentience, or phenomenal experience.
- We are in our own table, under the identical rubric, and we fail it too.
