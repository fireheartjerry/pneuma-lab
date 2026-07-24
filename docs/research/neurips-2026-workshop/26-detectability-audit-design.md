# 26 — Ten Conversations, Two Thousand Questions

**What agent-memory evaluations could actually have detected.**

**Date:** 2026-07-24
**Status:** PRIMARY STUDY. Supersedes `25-placebo-selfreport-design.md` and
`23-placebo-memory-design.md`, both retained as deferred designs.
**Target:** Who Verifies the Agents? @ NeurIPS 2026. 4–9 pages, double-blind, non-archival,
**2026-08-29 AoE**.

---

## 1. The claim

Agent-memory papers report sample sizes that assume benchmark items are independent. They are
not. Questions nest inside conversations. Tasks nest inside repositories and websites. Human
rankings nest inside a single simulation run. Every standard error and every implicit power
calculation in this subfield rests on an independence assumption that the benchmarks
themselves violate by construction.

We audit $N \le 25$ published systems from public information only, compute what effect each
design could have detected across a range of defensible clustering assumptions, and report
**how often the published conclusion survives**.

Verified examples, quoted from the papers themselves:

| System                | Reported         | Coarsest independent grouping |
| --------------------- | ---------------- | ----------------------------- |
| Mem0                  | ~2,000 questions | **10 conversations**          |
| Agent Workflow Memory | 1,000+ tasks     | **5 websites** (WebArena arm) |
| Generative Agents     | 100 rankings     | **1 simulation**              |
| ExpeL                 | 134 tasks        | **3 environments**            |

## 2. Why this is not bookkeeping

The distinction the paper lives or dies on. **We do not compute effective sample size.**
It is not identifiable from published information.

The design effect is $\text{DEFF} = 1 + (m-1)\rho$ with $n_{\text{eff}} = n / \text{DEFF}$.
Published reports give $n$ and the cluster count, hence $m$ — but never $\rho$. Substituting
the cluster count for $n$ silently assumes $\rho = 1$, which is a worst-case bound, not a
correction.

Therefore:

- **MDE is reported across an ICC grid**, $\rho \in \{0.05, 0.1, 0.3, 0.5, 1\}$, as an
  identified range with a worst-case bound — never a point estimate.
- **Single-cluster designs are marked non-identifiable.** Generative Agents does not get
  $n_{\text{eff}} = 1$; it gets _"between-simulation variance is unidentified from one
  simulation; population-level uncertainty cannot be estimated."_
- **The headline is the fraction of conclusions that change**, not the size of the ratios.
- MDE scales as $1/\sqrt{n_{\text{eff}}}$, so a 100–200× reduction in effective $n$ inflates
  the detectable effect roughly **10–14×** — one order of magnitude. Not two. Any draft
  claiming two is wrong.

## 2b. The exact statistics

**Paired comparison** on the same binary-scored items — the usual case, since these papers
compare a memory-augmented system against its own ablation on identical items. Let
$D_i = Y_{Ai} - Y_{Bi} \in \{-1,0,1\}$ and let $d = P(D_i \neq 0) = p_{10} + p_{01}$ be the
discordance rate. Then

$$
\mathrm{MDE}(\rho_D) \approx \left(z_{1-\alpha/2} + z_{1-\beta}\right)
\sqrt{\frac{d \cdot \mathrm{DEFF}_D(\rho_D)}{n}}, \qquad
\mathrm{DEFF}_D(\rho_D) = 1 + (m-1)\rho_D
$$

The binding quantity is the **discordance rate**, not either system's accuracy — McNemar
analyses only discordant pairs. Multiplier is $1.96 + 0.842 = 2.802$ two-sided, or
$1.645 + 0.842 = 2.487$ one-sided.

**Unpaired**, equal allocation, $n$ per arm, reference rate $p_0$:

$$
\mathrm{MDE}(\rho) \approx \left(z_{1-\alpha/2}+z_{1-\beta}\right)
\sqrt{\frac{2p_0(1-p_0)\,\mathrm{DEFF}(\rho)}{n}}
$$

**Three technical constraints that must not be violated:**

1. **$\rho_D$ is the ICC of the paired contrast $D_i$, not of raw correctness.** Pairing can
   remove shared item difficulty, so mechanically applying a raw-score ICC is wrong and may
   be far too pessimistic. Where a paper's comparison is paired, the grid is over $\rho_D$
   and the doc says so.
2. **With few clusters, $z$ is the wrong critical value.** Design-effect arithmetic does not
   solve the degrees-of-freedom problem; small-sample cluster-level critical values are
   required and the correction is reported.
3. **Defaults are two-sided $\alpha = 0.05$ and 80% power.** One-sided is defensible only for
   a genuinely precommitted directional question, which these papers do not have (0/10
   pre-specify any decision rule).

**Single-cluster designs.** With all observations from one cluster, between-cluster variance
and ICC are not estimable, so there is no identified design effect, no cluster-robust standard
error, and no MDE for generalization — only an assumption-indexed one. The
cluster-randomized-trial literature states this directly (Murray et al.; Eldridge et al.), and
one cluster in total is strictly more restrictive than one cluster per condition.

**The sentences we may and may not write.**

Licensed:

> Published item and cluster counts do not identify a unique effective sample size or minimum
> detectable effect for claims generalizing beyond the observed conversations, repositories,
> websites, or simulations. Under an equal-size exchangeable-cluster working model we report
> ICC-indexed sensitivity ranges rather than point estimates; every reported MDE is
> conditional on the stated ICC, cluster size, discordance or base rate, and testing
> assumptions.

Forbidden:

> ~~The study's effective sample size was the number of clusters.~~ (sets $\rho = 1$ silently)

> ~~The study could not detect effects smaller than $x$.~~ — unless $x$ carries its full
> qualification: _under $\rho = 0.10$, equal cluster sizes, two-sided 0.05, 80% power, and
> the stated discordance rate._

The strongest public-information claim is about **non-identification and sensitivity**, never
about a study's true power.

## 2c. Two precedents found late, and how we stand against them

| Work                                                                                                                                              | Status                                | What it owns                                                                                                                                                                   | What it leaves                                                                                                                                                                                                                                     |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Siska, Marazopoulou, Ailem & Bono**, _Examining the robustness of LLM evaluation to the distributional assumptions of benchmarks_, **ACL 2024** | **VERIFIED by fetch**                 | The closest peer-reviewed precedent for the core insight: correlation across test prompts is non-random, and accounting for it **changes model rankings** on major benchmarks. | Test-prompt correlation within a benchmark, not hierarchical nesting in conversations, repositories, or simulations. Concerns model _rankings_, not what a study could detect. No design effects, no ICC, no MDE. Does not audit published claims. |
| **TMLS AI Research (2026)**, _eval sample complexity_ — benchmark MDE atlas with explicit DEFF treatment for templates and conversations          | **UNVERIFIED — URL returns HTTP 403** | Described as the closest exact precedent.                                                                                                                                      | Unknown.                                                                                                                                                                                                                                           |

**Siska must be cited in the introduction's first paragraph.** Failing to cite the ACL paper
that established non-independence in LLM benchmarks would, on its own, justify rejection.

**The TMLS report is an open risk and a blocking obligation.** Per this project's standing
rule an unverifiable citation is dropped rather than softened — but a 403 is not evidence of
absence. It must be resolved before submission by another route (direct contact, a mirror, or
a search for a published version). If it does what it is described as doing, our contribution
narrows to the agent-memory corpus and the claimed-effect-versus-MDE comparison, and the paper
must say so plainly.

**Revised air gap, stated honestly:** no _peer-reviewed_ work systematically reanalyzes
published **agent-memory** claims with ICC-sensitivity MDEs at the conversation, repository, or
simulation level, and none compares a paper's claimed effect against what its own design could
have detected. Novelty must not be overstated relative to Siska or to the TMLS report.

## 3. What each paper contributes to the table

Per system, from the frozen nine-field rubric in `22-audit-rubric.md`, plus:

| Column            | Contents                                                      |
| ----------------- | ------------------------------------------------------------- |
| Reported $n$      | with unit and verbatim quote                                  |
| Coarsest grouping | count, unit, and which rubric decision rule fired             |
| $m$               | observations per cluster                                      |
| MDE range         | at $\rho = 0.05 \ldots 1$, or `non-identifiable`              |
| Claimed effect    | the paper's own headline improvement, quoted                  |
| **Verdict**       | `supported` / `below-detection-at-<rho>` / `non-identifiable` |

The verdict column is the paper. A claim is `below-detection-at-<rho>` when the claimed
effect falls under the MDE at that clustering assumption — meaning the study could not
reliably have detected the effect it reports, so the reported estimate is either a favourable
draw or the interval is understated.

## 4. Secondary findings, scoped honestly

From the ten systems coded so far. **Every one of these is a statement about our coded frame
and date range, never about the field.**

- **Uncertainty over the wrong variance component: 10 of 10.** Not one resamples its own
  coarsest grouping. Mem0's $\pm 0.65$ is over 10 repeated judge runs of the _same_ 10
  conversations — smaller than the $\pm 1.05$ you would get if all 2,000 questions were
  independent, so it is not a sampling interval under any clustering assumption.
- **Inert-content null arm: 0 of 10.** Must be scoped explicitly — MemDelta runs a
  random-content retrieval control on Mem0 and is outside our coded frame. Report as
  _"none of the ten systems we coded"_, never as a field-wide absence.
- **Pre-specified decision rule: 0 of 10.**
- **Not auditable from the paper: 2 of 10.** A-MEM never states how many LoCoMo conversations
  it uses; SWE-Exp never states its repository count; MemGPT's headline memory result states
  no sample size anywhere. This is its own finding.

## 5. Position against the nearest work

| Work                                                             | What it owns                                                             | What it leaves                                                                              |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| Card et al. 2020, _With Little Power Comes Great Responsibility_ | the audit-a-literature-for-power paper shape, in NLP                     | treats **items as independent**; single endpoint; does not audit agent evaluation           |
| Miller, arXiv:2411.00640                                         | clustered standard errors for LLM evaluation                             | does not audit published papers or compute what they could have detected                    |
| Bjarnason, arXiv:2602.07150                                      | measured run-to-run variance, 60k trajectories, pass@1 varies 2.2–6.0 pp | _recommends_ power analysis, does not perform one; no clustering model; no literature audit |
| Huang, arXiv:2607.12338                                          | how many tasks reproduce a benchmark decision                            | a reproduction question, not a power question; tasks as units; audits no paper              |

**The air gap in one sentence:** nobody has demonstrated, over a corpus of published
agent-memory results, how often the reported conclusion fails to survive an
estimand-aligned clustering correction.

**The most dangerous objection**, to be pre-empted in the introduction: _"this is Card's
design plus Miller's mathematics on a new corpus, and effective $n$ is not identifiable from
published cluster counts."_ The second half is correct, which is exactly why the paper is a
sensitivity analysis and says so in the abstract.

## 6. What we do not claim

- Not that any audited system does not work. We record what each paper reports about its own
  evaluation and what that design could have detected.
- Not that our chosen grouping is the only defensible unit. It is the **conservative** one,
  reported alongside the paper's own $n$ so a reader can disagree with a known quantity.
- Not that we estimate effective sample size. We bound it.
- Not a field-wide claim from a coded sample of $\le 25$.
- No claim about consciousness, sentience, or phenomenal experience.

**We audit ourselves.** Pneuma Lab's own E-0 result is coded under the identical rubric,
appears in the main table, and its failures are reported without mitigation.

## 7. Deliverables

1. **The audit table** — $N \le 25$, every non-numeric cell backed by a verbatim quote with a
   locator, full coding sheet released.
2. **The MDE surface** — per paper, across the ICC grid, with non-identifiable designs marked.
3. **The verdict count** — how many claims fall below their own detection threshold, as a
   function of $\rho$.
4. **A released tool** that takes a reported design and returns the MDE range.

## 8. Why this is the right paper to ship

- **Zero compute.** No model, no GPU, no laptop thermal risk, no gate that can fail on Aug 8.
- **Cannot be scooped by an experiment.** A better memory system does not touch it. Another
  placebo result becomes a citation.
- **Ten of twenty-five already coded**, quote-backed, under a rubric frozen before coding.
- **It survived a hostile review** designed to kill it. Five sibling claims did not.

The honest cost: it is a measurement paper about other people's papers. It will be respected
more than it is remembered. That is an acceptable trade for the only direction we have that
is both executable and unoccupied.

## 9. Schedule

| Week            | Work                                                                                                                          |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Jul 24 – Aug 1  | Frame closed to $N \le 25$. Remaining systems coded. Methodology section fixed against the partial-identification literature. |
| Aug 2 – Aug 8   | MDE computation and tool. Full table built. Self-audit of E-0 coded.                                                          |
| Aug 9 – Aug 15  | Every cell re-verified against source. Figures.                                                                               |
| Aug 16 – Aug 22 | Draft.                                                                                                                        |
| Aug 23 – Aug 29 | Red-team against the objection list, anonymize, **submit Aug 28.**                                                            |

There is no compute gate because there is no compute. The only failure mode is the frame
being too small, and that is knowable by Aug 1.

## 10. Standing obligation

Weekly arXiv sweep through Aug 20 on `(power OR sample size OR clustering OR design effect)
AND (agent OR LLM) AND evaluation`. Nine adjacent papers appeared between March and July 2026. Assume more.
