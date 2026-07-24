# 21 — Pivot and Claim Retirement

**Date:** 2026-07-24
**Status:** AUTHORITATIVE. Supersedes the novelty claims in `02-research-thesis.md` §7 and
the venue/outline plan in `13-publication-plan.md` §3–§5.

This document is the single source of truth for what this project claims and what it has
stopped claiming. It exists because the retirement evidence otherwise lives only in a
session transcript, and retired claims regrow.

---

## 1. What happened

An adversarial prior-art audit was run on 2026-07-24 against the six novelty claims in the
planning package. Each claim was reconnoitred, then attacked by an independent agent
instructed to default to refutation and to search beyond the reconnaissance.

**Five of six claims were refuted.** The refutations are driven by work published between
**March and July 2026** — after this planning package was authored.

Separately, the statistical P0 power gate returned **no-go** (commit `bfa20b3`): at design
alternative `Delta_power = 0.10` and `G = 48` lineages, complete-conjunction power is
0.039 (U0 core) / 0.079 (U0 floor) / 0.054 (U1 core) / 0.115 (U1 floor), with
`P(no-go) = 1.0` for both utility scopes. The binding components are the utility
non-inferiority co-gates (marginal power ~0.35), not the superiority test.

The combination of these two results retires the original paper.

---

## 2. Retired claims

Verification status is recorded per citation. `VERIFIED` means the abstract was fetched
directly and confirmed to state what is attributed to it. `UNVERIFIED` means the citation
comes from the audit transcript and has **not** yet been independently checked.
**No UNVERIFIED citation may enter a submitted draft.**

| Claim  | Was                                                                           | Status                                       | Killer prior art                                                                                                                                                                                                                                                                      | Verified                                                 |
| ------ | ----------------------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| **C1** | Bounded reranker as a novel memory carrier; "not definable on a text carrier" | **RETIRED**                                  | RAPO, arXiv:2604.07428 — persistent decayed-count hazard memory as a leaky integrator, actuating only through a clipped bounded reweighting over a mass-preserving kernel, with a frozen policy, an influence-off null, and dose sweeps. Owns the entire instrument, not a component. | VERIFIED                                                 |
| **C2** | Randomized live mid-rollout state clamp as a novel causal-validity method     | **RETIRED as novelty**                       | Xiao Jia, arXiv:2605.09692 — intervention-coupled evaluation of language agents with state lesions, scrambled-context and action-prior controls, and restoration checks, over 57,816 records including 300 SWE-bench Lite issues.                                                     | VERIFIED                                                 |
| **C3** | `repeat_harm` as a novel primary endpoint                                     | **RETIRED**                                  | BenchTrace, arXiv:2605.29225 — Failure Avoidance Rate over 1,821 annotated episodes; denominator fixed by benchmark construction, opportunities generator-scheduled.                                                                                                                  | VERIFIED                                                 |
| **C4** | Anti-gaming utility co-gates as a novel evaluation framework                  | **RETIRED as novelty; survives as transfer** | Schultzberg, Ankargren & Frånberg, arXiv:2402.11609, peer-reviewed in _Comput. Stat. Data Anal._ 2026 — the success-plus-guardrail ship rule stated verbatim, with the intersection-union rationale.                                                                                  | UNVERIFIED                                               |
| **C5** | Prose-blind firewall + standardized-exposure design                           | **RETIRED**                                  | Al-Tawaha et al., arXiv:2605.17830 — trigger-probe protocol evaluating a fixed probe set against **read-only memory snapshots** at varying prefix lengths. Strictly stronger isolation than our live same-subject exposure.                                                           | VERIFIED                                                 |
| **C6** | Conjunctive power audit of agent-memory claims                                | **SURVIVES, reframed**                       | None found. Nearest is Card et al. 2020, _With Little Power Comes Great Responsibility_, which is single-endpoint, two-model, items-as-units, and explicitly defers the multi-endpoint case.                                                                                          | Card VERIFIED by prior familiarity; gap claim UNVERIFIED |

### Additional prior art named by the audit, all UNVERIFIED

Recorded so the verification obligation is tracked, not so it may be cited:
arXiv:2605.10448 (denominator rule), arXiv:2607.10059 (AgentAbstain, paired
act/abstain twins), arXiv:2607.18867 (HindsightBench), arXiv:2606.29824 (Neural
Procedural Memory), arXiv:2604.27707 (Xu et al., context-memory separation theorem),
arXiv:2606.21399 (prefix branching with verified replay), arXiv:2607.07753 and
arXiv:2606.19831 (dose-graded single-coordinate agent-state manipulation),
arXiv:2601.10960 (SWAI), arXiv:2603.07670 (agent-memory survey), arXiv:2602.07150
(Bjarnason et al.), arXiv:2607.12338, arXiv:2411.00640 (Miller), arXiv:2410.06703
(ST-WebAgentBench CuP), arXiv:2607.19449.

**Obligation.** Every citation above must be fetched and confirmed before it appears in a
draft. A citation that cannot be confirmed is dropped, not softened.

### Verification pass, 2026-07-24

All sixteen exist. Four attributions were wrong and are corrected here. Verification was
against abstracts only; a `NOT_SUPPORTED` result means the abstract does not state the
attributed claim, and the claim may still appear in the body.

| ID         | Actual title                                                              | Attribution verdict                                                                                                                                                                         |
| ---------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2605.10448 | Can Agent Benchmarks Support Their Scores? (Gao)                          | **NOT_SUPPORTED.** No "Denominator rule" in the abstract. C3's retirement now rests on BenchTrace alone.                                                                                    |
| 2607.10059 | AgentAbstain: Do LLM Agents Know When Not to Act? (Liu)                   | SUPPORTED                                                                                                                                                                                   |
| 2607.18867 | HindsightBench (Jia)                                                      | PARTIAL — four-arm matrix yes; prose-blind scoring and generator-fixed denominator not stated                                                                                               |
| 2606.29824 | Neural Procedural Memory: Implicit Activation Steering (Zhao)             | PARTIAL — non-textual persistent memory yes; "numeric carrier" not stated                                                                                                                   |
| 2604.27707 | Contextual Agentic Memory is a Memo, Not True Memory (Xu)                 | PARTIAL — structural separation argued; no named theorem                                                                                                                                    |
| 2606.21399 | Calibration Is Not Control (Zhang)                                        | PARTIAL — same-prefix branching yes; the 100% replay match and discard rule not stated                                                                                                      |
| 2607.07753 | A Transdiagnostic Space of Disorder-Like Phenotypes in RL Agents (Prasad) | SUPPORTED                                                                                                                                                                                   |
| 2606.19831 | Leverage Is Not Reach: single-neuron steering (Liu)                       | **NOT_SUPPORTED.** Neuron steering in LMs, not agent-state clamping. Drop from C2's case.                                                                                                   |
| 2601.10960 | Steering Language Models Before They Speak (An)                           | PARTIAL — top-K log-odds bias yes; "bounded" not stated                                                                                                                                     |
| 2603.07670 | Memory for Autonomous LLM Agents (Du)                                     | SUPPORTED                                                                                                                                                                                   |
| 2602.07150 | On Randomness in Agentic Evals (Bjarnason)                                | SUPPORTED — see C6 positioning below                                                                                                                                                        |
| 2607.12338 | How Many Tasks Are Enough for Agent Benchmark Decisions? (Huang)          | SUPPORTED — see C6 positioning below                                                                                                                                                        |
| 2411.00640 | Adding Error Bars to Evals (Miller)                                       | **NOT_SUPPORTED** for clustered SEs in the abstract; check full text before citing for that                                                                                                 |
| 2410.06703 | ST-WebAgentBench (Levy)                                                   | SUPPORTED — CuP confirmed                                                                                                                                                                   |
| 2607.19449 | Guardrails as Scapegoats (Singh)                                          | PARTIAL                                                                                                                                                                                     |
| 2402.11609 | Risk-aware product decisions in A/B tests (Schultzberg)                   | SUPPORTED. **Venue correction: published in _Journal of Statistical Planning and Inference_ 2026, DOI 10.1016/j.jspi.2026.106393 — NOT _Comput. Stat. Data Anal._ as previously recorded.** |

### C6 positioning against its three nearest neighbours

Checked in full on 2026-07-24. None occupies the claim.

- **Bjarnason, arXiv:2602.07150.** Measures run-to-run variance over 60,000 trajectories on
  SWE-Bench-Verified across three models and two scaffolds; single-run pass@1 varies by
  **2.2 to 6.0 percentage points** depending on which run is selected. It _recommends_
  power analysis; it does not perform one. Single endpoint. No clustering model. No
  literature audit.
  **Use:** this is a measured, citable variance figure. Anchor the simulator's nuisance
  priors on it rather than stipulating them. This materially weakens the "your priors are
  invented" objection at zero cost.
- **Huang, arXiv:2607.12338.** Replays completed task-level records from SWE-bench,
  AppWorld, and tau-bench to ask when a partial task budget reproduces the full benchmark's
  decision. That is a **reproduction** question, not a power question. Task-level unit with
  no clustering model, single endpoint, benchmark records only — it audits no published
  paper — and no released tool.
- **Card et al. 2020.** Single-endpoint, two-model, items-as-units; explicitly defers the
  multi-endpoint case.

**The air gap, stated precisely:** no work combines (a) clustered independent units,
(b) conjunctive multi-endpoint decision rules mixing superiority with non-inferiority
guardrails, and (c) an audit of what published agent-memory papers report as their sample
size. Each neighbour holds exactly one of the three.

---

## 3. Corrections to the audit

Two of the audit's attacks were checked against `src/pneuma_lab/statistics/power.py` and
do **not** hold. Recorded so they are not conceded in the paper.

1. **"The P0 simulator assumes i.i.d. opportunities."** False. `LINEAGE_ICC = (0.05, 0.15,
0.30)` is swept, and effective sample is deflated by the design effect `(1 + ICC)` for
   two nested sequences per lineage. Variance is lineage-clustered.
2. **"Joint power 0.039 is an arbitrary interior point with no modelled dependence."**
   Partly false. `CROSS_COMPONENT_CORRELATION = (0.25, 0.50, 0.75)` is swept under a
   single-factor equicorrelation structure with a positive-definiteness guard. The reported
   figure is a weighted average over that grid, not a point choice.

**What does survive from that attack:** the correlation grid excludes `rho = 0` and
`rho -> 1`, so it does not bracket the range, and its weights are stipulated rather than
measured. The remedy is to extend the grid and publish a surface, not to rebuild the model.

---

## 4. Surviving claims

Stated in the exact form the paper should use.

**S1 — Effective-independent-unit audit.** _Across N agent-memory systems, reported sample
size overstates the number of independent units by one to two orders of magnitude,
uncertainty is either absent or estimated over the wrong variance component, and no
flagship system administers an inert-memory null._ This is the only claim that measures an
external object rather than our own assumptions. It cannot be attacked as a modelling
artifact.

**S2 — Guardrail-conjunction cost invariant.** _When an agent-memory efficacy claim is
gated by anti-gaming non-inferiority guardrails, the binding sample-size constraint is the
guardrail conjunction and not the superiority test — an invariant that holds across every
endpoint-correlation, margin, and gate-count configuration explored._ No point estimate is
claimed. The headline is the invariant; the number is a surface.

**S3 — Measured guardrail dependence.** _We measure the correlation structure among
anti-gaming guardrails on live agent lineages and show that most are near-collinear through
a single disengagement channel, so a reduced gate subset achieves equivalent gaming
detection at a fraction of the sample requirement._ Converts the paper's largest liability
into a prescriptive result.

**S4 — Option-set preservation audit.** _We report a per-decision, hash-verified audit of
candidate-multiset preservation under a state-conditioned reranker: byte-equality pass
rate, the empirical distribution of the induced pairwise log-odds shift, and the fraction
of decisions on which the reranker flips the frozen model's argmax._ This is what remains
of C1: a measurement that can fail, where Proposition 1 was a clipping identity.

**S5 — Released, not run.** The carrier x pipeline-position 2x2 (retrieval-as-reranker,
numeric-state-as-prompt) is the correct de-confound for C1 and cannot be executed in the
available time. It is published as a specified design with its computed sample
requirement.

---

## 5. Demotions inside the paper

| Object                          | New role                                                                                                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Proposition 1                   | "Design Invariant 1", three sentences, cited to RAPO / DExperts / Controlled Decoding as lineage                                                                   |
| `repeat_harm`                   | One Methods paragraph, credited as an adaptation of BenchTrace's FAR                                                                                               |
| Seven arms                      | Three: Base, Pneuma-state, Influence-off                                                                                                                           |
| Component clamps                | Apparatus in Methods, not a contribution                                                                                                                           |
| Firewall + exposure design      | Design Controls subsection, with an explicit concession that live same-subject exposure is weaker isolation than Al-Tawaha's reset-and-replay, and why we chose it |
| Doc 17's 39-task V2 plan        | SUSPENDED. Off the critical path.                                                                                                                                  |
| Doc 18's identification results | Appendix                                                                                                                                                           |

---

## 6. Known defects to correct

1. **Infrastructure failure is currently coded adverse** in `repeat_harm`. This biases the
   endpoint _against_ the arms the study exists to support, since state-bearing arms
   consume more budget and bind caps more often. Correct to exclude infrastructure and
   pre-run failures for cause; normalize budget in effective work units; report
   component-wise incidence.
2. **Two clamp doses do not identify a slope.** Either strike the word "slope" or run four
   or more levels.
3. **The clamp estimand is a total effect, not an isolated one.** Clamping one coordinate
   changes actions, which change observations, which feed the other coordinates on the next
   step. Every sentence claiming the clamp "isolates" a coordinate is wrong about its own
   estimand.
4. **The non-inferiority margin 0.05 is asserted, not derived**, and sample size scales as
   `1 / delta^2`. This must be stated, not defended.

---

## 7. Method commitments

- **No inter-rater reliability statistic is reported.** Coding is by one author with LLM
  assistance; every cell is backed by a verbatim quote and the full sheet is released. Two
  instances of the same model are not independent raters, and claiming otherwise in a paper
  about measurement rigor would be self-refuting. See `22-audit-rubric.md`.
- **Self-inclusion is mandatory.** Pneuma Lab's own E-0 result is coded under the identical
  rubric and appears in the main table. Its failures are reported without mitigation.
- **Tone.** The paper reports a field-wide measurement problem in which the authors are
  included. It does not evaluate the quality of any audited system.
- **Front-loaded attribution.** The full mechanism lineage and metric lineage appear in the
  introduction's first two paragraphs, together with an explicit "what we do not claim"
  block. Not in a related-work section on page four.
- **No use of the word "first".** No instance of "not definable on a text carrier".

---

## 8. Standing obligation

**Re-run the prior-art sweep in the week of 2026-08-22.** Six directly adjacent papers
appeared between March and July 2026 and the rate has not slowed. Assume at least two more
land before submission. A reviewer who finds an uncited neighbour concludes the authors are
unaware of their own field, which is a rejection independent of merit.
