# 30 — Draft: Method, Taxonomy, Limitations, Conclusion

**Date:** 2026-07-24
**Status:** DRAFT PROSE. Completes the body with `28-draft-core.md` (abstract, results)
and `29-draft-intro.md` (introduction, related work).

---

## §2 What the literature reports

### 2.1 Frame

Thirty systems and benchmarks, selected by a procedure fixed before any paper was read:
ten seeds, plus every system a seed compares against, plus every system cited by the
March 2026 agent-memory survey. Two systems were admitted by a recorded amendment after
the original procedure was found to have under-reached them; that amendment, and every
other adjudication in this paper, is dated and published with its rejected alternatives.

The frame stratifies into **system papers**, which claim a memory mechanism helps, and
**benchmark papers**, which claim nothing about their own memory but impose their sample
structure on everyone who evaluates against them. A benchmark built from fifty
conversations imposes fifty clusters on every downstream user, permanently. We report the
strata separately.

We include our own prior work as a third stratum of one.

### 2.2 Coding

Nine fields per paper, coded against a rubric frozen before the first paper was read.
Every non-numeric cell is backed by a verbatim quoted passage with a section locator, and
the full coding sheet is released.

**We report no inter-rater reliability coefficient.** Coding was performed by one author
with LLM assistance, and two instances of one model are not independent raters. Printing
an agreement statistic between them, in a paper about statistics that do not mean what
they appear to, would be self-refuting. Quote-backing is offered instead and is stronger:
a reader can check any cell against its source rather than trusting a coefficient.

Where a paper does not state something, the cell reads `not_stated`. It is never inferred,
including where the intended value seems obvious.

### 2.3 What the coding found

Reporting practice across the frame, scoped to these thirty papers and this date range:

- **31 of 32 rows pre-specify no decision rule.** The exception is ours, which was
  preregistered.
- **28 of 32 have no inert-content null arm.** Comparisons are to a different system or to
  the augmentation removed, which confounds the content of a memory with the apparatus
  that delivers it.
- **0 of 32 report uncertainty over their own coarsest grouping.** One paper reports
  confidence intervals at all, and each interval sits inside a single task stream, so it
  structurally cannot resample the unit that would matter.

---

## §3 Three kinds of dependence

### 3.1 Substrate

Benchmark items nest. LoCoMo compiles 7,512 questions from 50 dialogues. MemBench
generates 53,000 questions from 500 relation graphs. MemoryAgentBench states the design
choice outright: _"we deliberately design scenarios where multiple questions follow a
single context. This allows us to probe the model's memory multiple times with one
sequential injection."_

This is the kind the existing literature models. It is a property of the measurement
substrate, it exists whether or not anything is being tested, and it propagates: every
system evaluated on a benchmark inherits its clusters.

### 3.2 Endogenous

An agent-memory system accumulates a pool across the evaluation. Memento initialises
memory from scratch and stores trajectories into a case bank across its validation set.
ReasoningBank evaluates on a task stream where "each query is revealed and must be
completed sequentially without access to future ones."

Under such designs task $k$ is conditioned on tasks $1 \ldots k-1$ through the pool, and
the coupling is created by the intervention under test. This produces a specific
awkwardness. Memento's design codes an overstatement ratio of 1.0 — the cleanest in the
frame — for an evaluation whose dependence is total, because a procedure that counts
observations cannot see coupling the system itself creates.

The general statement: **"memory carries information across tasks" and "tasks are
independent evaluation samples" are the same quantity, asserted in one direction as the
contribution and denied in the other as a statistical premise.**

### 3.3 Treatment-artifact

Trace2Skill evolves one skill document from a 200-sample evolving set, then scores it
across 2,649 held-out instances and reports up to 57.65 points. Every scored item shares
that one artifact. For the claim _this document works_, $n = 1$.

The analogy is a drug trial that manufactures a single batch, administers it to 2,649
patients, and reports 2,649 independent tests of the manufacturing process. The patients
are independent; the batch is not.

### 3.4 They compound

The three are independent of one another and can co-occur. Seven of the coded rows carry a
shared memory lifetime; several of those also draw from a clustered substrate. The audit
reports each separately and does not attempt to combine them into a single corrected
number, because the data required to do so is not published.

---

## §4 What a credible claim requires

### 4.1 We bound, we do not estimate

The design effect is $\mathrm{DEFF} = 1 + (m-1)\rho$, giving
$n_{\mathrm{eff}} = n / \mathrm{DEFF}$. Published reports state $n$ and the cluster count,
hence $m$ — but never $\rho$. **Substituting the cluster count for the observation count
silently assumes $\rho = 1$**, which is a worst-case bound rather than a correction.

We therefore report the minimum detectable effect across a grid,
$\rho \in \{0.05, 0.1, 0.3, 0.5, 1.0\}$ crossed with paired discordance
$d \in \{0.15, 0.25, 0.40\}$, as a range. No point estimate of effective sample size
appears anywhere in this paper.

For a paired comparison on binary-scored items — the usual case, since these papers
compare a system against its own ablation on identical items — with $D_i \in \{-1,0,1\}$
and discordance $d = P(D_i \neq 0)$:

$$\mathrm{MDE}(\rho_D) \approx \left(z_{1-\alpha/2}+z_{1-\beta}\right)\sqrt{\frac{d \cdot \mathrm{DEFF}_D(\rho_D)}{n}}$$

The binding quantity is the discordance rate, not either system's accuracy, because
McNemar analyses only discordant pairs. We use two-sided $\alpha = 0.05$ and 80% power;
one-sided would be defensible only for a precommitted directional question, and 31 of 32
papers pre-specify no decision rule at all.

### 4.2 Non-identifiable designs

Where all observations derive from one cluster, between-cluster variance and $\rho$ are
not estimable. There is no identified design effect, no cluster-robust standard error, and
no minimum detectable effect for a claim generalizing beyond that cluster. Such designs
are reported as **non-identifiable with their reason**, never assigned a number.

Generative Agents is the clearest case: 100 rankings, one simulation. The honest statement
is not that its effective sample size is one. It is that population-level uncertainty
cannot be estimated from these data.

### 4.3 Verdict stability

A verdict computed at one assumed $\rho$ and one assumed $d$ is a rendering of those
assumptions. We therefore report, for every checkable claim, whether its verdict holds
across the entire two-dimensional surface or flips somewhere, and where.

Three of six hold everywhere. Two flip. One — Reflexion — holds under its coded unit and
flips under a defensible alternative reading of that unit, and is reported as such rather
than counted as clean.

---

## §7 Limitations

**The method is not ours.** Detectability analysis is Card et al.'s; clustered inference
for evaluation is Miller's; non-independence in LLM benchmarks is Siska et al.'s; the
closest execution on real data is Kotawala's. Our contribution is the corpus, the
taxonomy, and the observation that two of the three dependence kinds arise from the
intervention. A reader who wants the statistical machinery should cite them, not us.

**The frame is thirty papers and one date range.** Every count in this paper describes
that frame. None is a claim about agent-memory research in general, and the sampling
procedure is published so a reader can disagree with a known quantity.

**The independent unit is a judgment.** Our rubric fixes a four-rule decision procedure,
and we apply it mechanically rather than by preference. Six rows carry a defensible
alternative unit; we publish both and report the verdict under each. A reader who prefers
the alternative can read our table under it.

**$\rho$ is unobserved.** We bound rather than estimate, and the bound is wide. For several
papers the MDE range spans an order of magnitude across the grid. That width is honest
reporting of what public information supports; it is not precision.

**Six of thirty-two.** Most of the frame yields no verdict. This limits the strength of any
quantitative summary of the literature's detectability, and we resist reporting a rate
over the six as though it characterised the thirty.

**We are in the frame and we score worst.** Our own prior result carries the highest
overstatement ratio here, and its item-level inference inflated confidence in a **negative**
finding. The same error inflates nulls as readily as positives. We report this in the body
rather than an appendix because an audit that applied its critique only to favourable
results would be practising the selective rigour it documents.

---

## §8 Conclusion

The question is not whether agent memory works. It is whether the published record can
tell us. On the evidence of thirty papers: mostly not — not because the field is careless,
but because the standard reporting conventions were built for evaluations whose items are
independent, and agent memory is the case where the intervention itself makes them not.

A memory system that works is a memory system whose evaluation violates the assumption
used to test it. That is not a flaw anyone introduced. It is a structural feature of
testing something whose entire purpose is to carry information between the things you are
counting as independent.
