# 29 — Draft: Introduction and Related Work

**Date:** 2026-07-24
**Status:** DRAFT PROSE. Citations marked `[CITE:key]` await the verified bibliography;
none may enter LaTeX until confirmed against a primary source.

---

## §1 Introduction

An agent-memory paper reports how much it evaluated on. Mem0 reports two thousand
questions. Agent Workflow Memory reports over a thousand tasks. Generative Agents reports
a hundred human rankings. These numbers do the work of establishing that a result is
solid, and every confidence interval, significance test, and implicit power calculation in
the literature is computed against them.

The two thousand questions come from ten conversations. The thousand tasks come from five
websites. The hundred rankings all come from a single two-day simulation.

That benchmark items are correlated rather than independent is known, and correcting for
it changes model rankings `[CITE:siska_robustness_2024]`. That evaluation intervals are
often computed over the wrong quantity is known `[CITE:miller_errorbars_2024]`. That a
literature can be audited for what its designs could detect is known — it is the shape of
`[CITE:card_littlepower_2020]`, which found NLP experiments broadly underpowered, and it
has since been applied to leaderboard rank resolution `[CITE:kotawala_resolution_2026]`
and to benchmark sample complexity `[CITE:huang_howmany_2026]`. None of that is ours, and
we say so here rather than in a related-work section on page four.

What has not been done is to point that instrument at **agent memory**, where the problem
has a structural cause that does not exist in the literatures where these methods were
developed. In NLP benchmarking, item dependence is a property of how the data was built.
In agent memory it is additionally a property of **the thing being tested**.

Consider what a memory system claims. It claims that information acquired while solving
task $k-1$ improves performance on task $k$. That is the contribution. But the standard
inferential treatment of the same evaluation asserts that tasks are independent samples.
Both cannot hold. If memory transfers information across tasks then the observations are
coupled, and the coupling is proportional to how well the memory works. **The stronger the
claimed effect, the more severe the violation of the assumption used to test it.**

A second case has the same character. Several systems induce a single artifact — a skill
document, a workflow library, a distilled experience set — and then score it on thousands
of items. Trace2Skill evolves one skill document from one evolving set and reports up to
57.65 points from it across 2,649 test instances. For the claim _this skill document
works_, the number of independent replications is one.

We therefore distinguish three kinds of dependence, and only the first is what the
existing literature models:

1. **Substrate dependence** — imposed by the benchmark, inherited by every system
   evaluated on it. LoCoMo's fifty conversations become fifty clusters for everyone who
   uses it, permanently.
2. **Endogenous dependence** — created by a memory pool accumulating across the
   evaluation, so that task $k$ is conditioned on tasks $1 \ldots k-1$.
3. **Treatment-artifact dependence** — where all scored observations share one induced
   artifact, so the effective replication count for the claim about that artifact is the
   number of artifacts.

We audit thirty agent-memory systems and benchmarks against a rubric frozen before any
paper was read, compute what effect each design could have detected across a range of
clustering assumptions, and compare that to what each paper claims. The result is less
about power than we expected. **Only six of thirty-two coded rows state an effect
precisely enough to compare against any threshold at all.** Thirteen cannot be bounded
because the paper never states the count of its own coarsest grouping. Of the six that can
be checked, five fall below their own detection threshold at every clustering assumption
we report.

Our contributions are the audit, the taxonomy, a detectability surface reported as a range
rather than a point, and a released tool. **We do not claim that any audited system fails
to work.** We claim that most of these studies could not have detected the effects they
report, and that a majority do not report enough for a reader to check. We include our own
prior work in the audit under the identical rubric, where it records the worst
overstatement ratio in the frame.

---

## §6 Related work

**Power audits of a literature.** `[CITE:card_littlepower_2020]` established this paper's
shape: harvest reported designs, compute what they could detect, report how often the
literature falls short. It treats items as independent, which is correct for the
single-endpoint NLP comparisons it studies and is precisely the assumption that fails
here.

**Non-independence in LLM evaluation.** `[CITE:siska_robustness_2024]` showed that
correlation across test prompts is non-random and that accounting for it changes model
rankings on major benchmarks. That is the closest peer-reviewed ancestor of our core
observation. It concerns correlation among prompts within a benchmark rather than
hierarchical nesting, and it concerns rankings rather than detectability.

**Clustered inference for evaluation.** `[CITE:miller_errorbars_2024]` supplies the
statistical treatment; `[CITE:bowyer_uncertainty_2025]` shows naive intervals understate
uncertainty in small evaluations; `[CITE:wang_clustered_2025]` applies cluster-robust
inference to multi-turn LLM evaluation. `[CITE:kotawala_resolution_2026]` performs the
closest execution of the method we use, computing a real ICC correction on MMLU-Pro and
reporting that unresolved adjacent-rank comparisons rise from four of nine to six of nine
under clustering. It analyses leaderboard rank comparisons, not published claims, and does
not cover agent evaluation.

**Variance in agent evaluation specifically.** `[CITE:bjarnason_randomness_2026]` measured
run-to-run variance over sixty thousand trajectories on SWE-Bench-Verified, finding
single-run pass@1 varies by 2.2 to 6.0 points depending on which run is selected, and
recommends power analysis without performing one. `[CITE:huang_howmany_2026]` asks how
many tasks reproduce a benchmark decision, which is a reproduction question rather than a
detectability one.

**Controls in agent-memory evaluation.** `[CITE:memdelta_2026]` audits one system with
controlled baselines including a random-content retrieval arm, and
`[CITE:budget_tokens_2026]` shows that several skill and memory modules do not beat a
token-matched vanilla agent. Both are direct prior art for the concern that motivates this
audit, and neither computes detectability.

**What remains open.** No work applies detectability analysis to published agent-memory
claims under the nesting specific to agent benchmarks, and none identifies dependence
created by the intervention rather than by the data.
