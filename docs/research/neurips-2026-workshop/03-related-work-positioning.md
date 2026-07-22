# 03 — Related Work and Defensible Positioning

**Status:** Protocol-v2-aligned literature audit. Search frozen 2026-07-22;
refresh before the anonymous source freeze. Primary venue: Verify-Agents at
NeurIPS 2026 in Sydney, Australia; IAB is the fallback.
Primary sources below are peer-reviewed proceedings or paper records; arXiv-only
work is labelled as such.

## 0. Claim discipline

Prior work already shows that agents can retain structured experience, reduce
recurring mistakes, maintain compact state, and benefit from active memory or
activation interventions. Therefore the paper makes none of these claims:

- not the first persistent agent memory;
- not the first structured, compact, or private memory/state;
- not the first system intended to avoid recurrent errors;
- not the first causal intervention on memory, experience, or agent activations;
- not the first process-level analysis of coding-agent trajectories;
- not the first verifier-backed state-centered agent architecture; and
- no consciousness, sentience, or phenomenal-interiority claim.

The defensible contribution is the following conjunction:

> A low-dimensional state that is never placed in a language-model prompt on the
> behavioural/action path and can only boundedly rerank a common set of
> model-proposed actions (with state visible only to one-way inert measurement/
> post-behaviour reporting sinks); a same-subject
> live pretreatment failure under a common untreated prefix, followed by
> independent task snapshots and fixed scheduled opportunities; a current-only
> shared recognizer, carrier-matched notice readouts for every arm, and a
> pretreatment recurrence label; randomized live state
> clamps with Influence-off, persistence-off, update-off, dose, permutation, and
> powered stochastic wiring nulls; exact conditional replay of the randomized
> seven-arm policy-to-stream mapping with independent stream order and
> prototype/generator lineage as the independent unit; an actor/updater/evaluator
> firewall with task-utility co-gates; and a target-symmetric nine-label reporter
> evaluated against a receipt-only decoder.

As of the frozen search, no identified study evaluates this full contract in a
live software-engineering agent. That is a qualified “to our knowledge” claim,
not an absolute priority claim. If a pre-submission refresh finds the full
combination, the paper becomes an independent replication/extension and says so.

## 1. Cross-task experience in software-engineering agents

### 1.1 Reflection and accumulated experience

Reflexion uses linguistic feedback stored in episodic memory, ExpeL extracts and
reuses experience across tasks, and Self-Refine iteratively conditions on its own
feedback. These establish strong textual reflection baselines; they do not
justify treating reflection as a strawman.

SWE-Exp stores successful and failed repair experience and reports strong
SWE-bench Verified resolution. FailureMem converts failed repair attempts into
reusable guidance. PROBE uses telemetry, structured diagnosis, and bounded next-
attempt recovery guidance. Structurally Aligned Subtask-Level Memory aligns
storage, retrieval, and updates with a coding agent's functional subtasks rather
than whole episodes. PROJECTMEM records typed coding events and uses a
deterministic pre-action gate to warn about repeated failed fixes. All are close
to the intervention target even when their memory carrier, evidence strength, or
outcome differs.

### 1.2 Recurrence and continual coding

SWE-Bench-CL explicitly orders repository issues chronologically and measures
continual transfer, forgetting, and tool efficiency. Zhao et al.'s dynamic coding
memory in machine-learning-engineering agents captures task/package/error/fix
records; its chain-based agents avoid recurring mistakes, while memory can reduce
search diversity in tree-based agents. Accumulated Behavioral Rules directly
reports reduced error-class recurrence across 11 production sessions, although
without randomized condition assignment.

These papers invalidate any claim that cross-task recurrence is absent from the
literature. Our narrower question is whether **non-prose machine-addressable
state** contributes causally beyond retrieval, reflection, retry count, and a
persistent scalar controller selected from a published last-bit/count/EWMA/Beta
grid with at least the same development budget, under standardized exposure and
fixed opportunities.

Key sources:

- Reflexion: Shinn et al., NeurIPS 2023,
  <https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Abstract-Conference.html>
- ExpeL: Zhao et al., AAAI 2024, DOI 10.1609/aaai.v38i17.29936,
  <https://ojs.aaai.org/index.php/AAAI/article/view/29936>
- Self-Refine: Madaan et al., NeurIPS 2023,
  <https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html>
- SWE-Exp: Chen et al., arXiv:2507.23361,
  <https://arxiv.org/abs/2507.23361>
- SWE-Bench-CL: Joshi, Chowdhury, and Uysal, arXiv:2507.00014,
  <https://arxiv.org/abs/2507.00014>
- Demystify the Role of Memory in Machine Learning Engineering Agents: Xinyu
  Zhao et al., Findings of ACL 2026, DOI 10.18653/v1/2026.findings-acl.525,
  <https://aclanthology.org/2026.findings-acl.525/>
- Self-Improving AI Coding Agents Through Accumulated Behavioral Rules:
  Aggarwal and Farhady Ghalaty, arXiv:2607.13091; the paper record reports ICE
  2026 presentation, <https://arxiv.org/abs/2607.13091>
- FailureMem: Ma et al., arXiv:2603.17826,
  <https://arxiv.org/abs/2603.17826>
- Debugging the Debuggers / PROBE: Chenyu Zhao et al., arXiv:2605.08717,
  <https://arxiv.org/abs/2605.08717>
- Structurally Aligned Subtask-Level Memory for Software Engineering Agents:
  Shen et al., ICML 2026, arXiv:2602.21611,
  <https://arxiv.org/abs/2602.21611>;
  <https://openreview.net/forum?id=2CoRS45Ucj>
- PROJECTMEM: Malo and Qiu, arXiv:2606.12329; evaluated as a two-month,
  10-project self-study rather than a randomized agent trial,
  <https://arxiv.org/abs/2606.12329>

## 2. Structured, active, and controllable memory/state

MemGPT virtualizes context with tiered memory. A-MEM organizes agent memories
agentically. MEM1 learns to update a compact shared internal state each turn.
Remember When It Matters is the closest identified active-memory neighbor: a separate
memory agent maintains structured private status and selectively injects
memory-grounded reminders rather than exposing a passive bank. StructAgent uses
unified state, verifier-backed transitions, checkpoints, and targeted recovery.
SteeM explicitly controls memory reliance in long-term interaction. Memory in
the Loop causally varies retrieval latency under a fixed per-turn budget and
links slower access to redundant action; Useful Memories Become Faulty shows
that repeated LLM consolidation can make initially useful memories harmful.

Thus the meaningful distinction is not “active memory versus passive memory.”
It is the exact **carrier and actuation contract**. Pneuma's state stays outside
the frozen LM weights and every candidate/action-path prompt, has no retrieval-
text channel in its core arm, and can only add bounded biases to model-proposed
candidate intents. One-way inert notice measurement and post-behaviour report
calls may read the state but cannot affect action. This makes state influence
directly zeroable without changing the behavioural prompt or candidate-
generation call. The claim is about this experimental isolation, not inherent
superiority of numbers over language.

Key sources:

- MemGPT: Packer et al., arXiv:2310.08560,
  <https://arxiv.org/abs/2310.08560>
- A-MEM: Agentic Memory for LLM Agents, Xu et al., NeurIPS 2025,
  <https://proceedings.neurips.cc/paper_files/paper/2025/hash/19909c36f51abc4856b4560aff3d36d6-Abstract-Conference.html>
- MEM1: Zhou et al., arXiv:2506.15841,
  <https://arxiv.org/abs/2506.15841>
- Remember When It Matters: Wu et al., arXiv:2607.08716,
  <https://arxiv.org/abs/2607.08716>
- StructAgent: Wu et al., arXiv:2607.11388,
  <https://arxiv.org/abs/2607.11388>
- Controllable Memory Usage / SteeM: Tian et al., ACL 2026,
  <https://aclanthology.org/2026.acl-long.670/>
- Memory in the Loop: Khan and Lipizzi, arXiv:2607.05690,
  <https://arxiv.org/abs/2607.05690>
- Useful Memories Become Faulty When Continuously Updated by LLMs: Zhang et
  al., arXiv:2605.12978, <https://arxiv.org/abs/2605.12978>

## 3. Causal dependence on memory and state

Large Language Model Agents Are Not Always Faithful Self-Evolvers performs
empty, shuffled, irrelevant, corrupted, and filler interventions on raw and
condensed agent experience across frameworks. Causal Intervention-Based Memory
Selection compares no-memory, memory, and perturbed-memory conditions. Xiong et
al. use controlled addition/deletion of episodic memories to study experience-
following and error propagation. What Happens Inside Agent Memory uses causal
feature-level circuit analysis. SOPHIA detects self-loops and intervenes with
activation steering.

These works invalidate statements such as “no one intervenes on memory” or “all
causal agent work targets only end-task success.” They also strengthen our design:
causal dependence must be demonstrated, not inferred from memory availability.
Memory in the Loop additionally shows why identical ex-ante action budgets are
not enough on their own: access-path latency can change repetition within those
budgets, so memory/controller latency and realized efficiency must be reported.

Our residual contribution is a system-level intervention on persistent
controller state with:

- one same-subject live verified pretreatment failure under a common untreated
  prefix, cloned before arm mapping, and independently live descendants;
- a fixed repeat-harm estimand independent of treatment-induced eligibility;
- all-state Influence-off plus update-off, dose, persistence reset, permutation,
  and powered restore/no-op stochastic-equivalence controls;
- the same structured-action candidate call and complete accounting of candidate,
  reflection, maintenance, repair/fallback, token, tool, retry, and failed-call
  costs in every arm;
- exact replay of the actual seven-label within-block assignment, prototype/
  generator-lineage aggregation, H1–H4 family decisions, and simultaneous
  intervals, with H5 embedded in H1; and
- task-success, engagement, total-failure, and false-avoidance co-gates.

Every observed branch-local refusal, timeout, premature finish, budget
exhaustion, model error, or runtime failure remains adverse. A block is removable
only when immutable arm-blind evidence identifies one common exogenous outage
that made all seven arms unobservable.

Key sources:

- Large Language Model Agents Are Not Always Faithful Self-Evolvers: Weixiang
  Zhao et al., arXiv:2601.22436 (paper record comments “ICML 2026”),
  <https://arxiv.org/abs/2601.22436>
- Causal Intervention-Based Memory Selection for Long-Horizon LLM Agents:
  Srivastava, arXiv:2605.17641,
  <https://arxiv.org/abs/2605.17641>
- How Memory Management Impacts LLM Agents: Xiong et al., ACL 2026,
  DOI 10.18653/v1/2026.acl-long.27,
  <https://aclanthology.org/2026.acl-long.27/>
- What Happens Inside Agent Memory?: Mao et al., arXiv:2605.03354,
  <https://arxiv.org/abs/2605.03354>
- SOPHIA / Can We Break LLMs Out of Self-Loops?: Yu et al.,
  arXiv:2607.18100, <https://arxiv.org/abs/2607.18100>

## 4. Process-level agent verification

ACT*ONOMY supplies a large hierarchical runtime-behaviour taxonomy. TraceProbe
normalizes coding-agent traces, detects single-trajectory anti-patterns, and
aligns paired trajectories to localize divergence. Failure as a Process analyzes
failure onset, evolution, and recovery. Understanding Code Agent Behaviour
contrasts successful and failed SWE-bench trajectories. SWE-Gym provides 2,438
executable software tasks with execution-based verifiers. AgentProcessBench adds
8,509 human-labelled steps in 1,000 tool-use trajectories and shows that early
termination can inflate apparent step correctness. A 20,574-session field study
finds seven recurring forms of developer-visible coding-agent misalignment, but
is observational and cannot establish a memory intervention effect. AgentAbstain
uses paired executable should-act/should-abstain variants; its paired scoring
directly motivates our false-avoidance and meaningful-engagement co-gates.

Our taxonomy is therefore not presented as the scientific novelty. Its role is
measurement validity: preregistered opportunity/outcome rules, exact mechanical
primary motifs, a current-task/within-opportunity-only prospective recognizer
distinct from the update signal, a generator-held recurrence label fixed before
action, an arm-blind offline scorer, and immutable typed traces. Semantic labels
and judge ensembles are secondary external-validity evidence. Suite B-live
supports only the frozen mechanically scorable known-motif repository/prototype
population, not natural software-engineering tasks generally.

Key sources:

- How to Interpret Agent Behavior / ACT*ONOMY: Gao et al.,
  arXiv:2605.13625, <https://arxiv.org/abs/2605.13625>
- What Resolve Rate Hides / TraceProbe: Shu et al., arXiv:2607.06184,
  <https://arxiv.org/abs/2607.06184>
- Failure as a Process: Xiangxin Zhao et al., arXiv:2607.09510,
  <https://arxiv.org/abs/2607.09510>
- Understanding Code Agent Behaviour: Majgaonkar et al., arXiv:2511.00197,
  <https://arxiv.org/abs/2511.00197>
- SWE-Gym: Pan et al., ICML 2025, PMLR 267,
  <https://proceedings.mlr.press/v267/pan25g.html>
- SWE-agent: Yang et al., NeurIPS 2024,
  <https://proceedings.neurips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html>
- AgentProcessBench: Fan et al., arXiv:2603.14465,
  <https://arxiv.org/abs/2603.14465>
- How Coding Agents Fail Their Users: Tang et al., arXiv:2605.29442,
  <https://arxiv.org/abs/2605.29442>
- AgentAbstain: Liu et al., arXiv:2607.10059,
  <https://arxiv.org/abs/2607.10059>

## 5. Self-report and causal attribution

Language-model verbal reports can be calibrated in some settings but can also be
unfaithful to causal influences and semantically unstable. The paper therefore
does not equate fluent explanation with access to mechanism. H3 is a balanced
nine-label classification/abstention task: four variables × two directions plus
`no_attributable_change`. The reporter receives target-symmetric public inputs
and no intervention identity, its prose is behaviourally inert, and it must beat
uniform/prior and receipt-only decoder baselines on frozen macro metrics,
coverage, and risk–coverage while distinguishing verified paired divergence from
no attributable change.

Relevant sources include Turpin et al. on unfaithful chain-of-thought, Betley et
al. on self-knowledge reports, Mayne et al. on positive conditions for
faithfulness, and Szeider on semantic invariance failures. Their collective
lesson is to validate reports against interventions rather than rhetorical
plausibility.

- Language Models Don't Always Say What They Think: Turpin et al., NeurIPS
  2023,
  <https://proceedings.neurips.cc/paper_files/paper/2023/hash/ed3fea9033a80fea1376299fa7863f4a-Abstract-Conference.html>
- Tell Me About Yourself: Betley et al., arXiv:2501.11120,
  <https://arxiv.org/abs/2501.11120>
- A Positive Case for Faithfulness: Mayne et al., arXiv:2602.02639,
  <https://arxiv.org/abs/2602.02639>
- LLM Self-Explanations Fail Semantic Invariance: Szeider,
  arXiv:2603.01254, <https://arxiv.org/abs/2603.01254>

## 6. Motivation boundary

Global-workspace and machine-consciousness-indicator literature motivates why
persistent broadcast-like state and self-model variables might be worth testing.
It supplies no outcome label and no consciousness inference. The relevant Global
Workspace review is Baars (2005), DOI 10.1016/S0079-6123(05)50004-9; the DOI is
not a Dehaene coauthored paper. Extended consciousness discussion belongs in a
short motivation/limitations paragraph, not the empirical claim or related-work
center of gravity.

## 7. Closest-neighbour matrix

| Work | What is already close | Residual difference from Protocol v2 |
| --- | --- | --- |
| Remember When It Matters | Structured private memory; selective active reminders; long-horizon agents | Acts through language injection; does not report a fixed repeated-harm estimand, randomized machine-state clamps, or blinded attribution. |
| Faithful Self-Evolvers | Controlled interventions on raw/condensed experience; explicit causal dependence | Experience remains prompt/context material; does not report a live coding-recurrence study with standardized exposure and utility co-gates. |
| Dynamic Coding Memory | Structured error/fix records; recurring-error avoidance; coding domain | Does not report a randomized state Influence-off/dose/persistence path or treatment-independent opportunity denominator. |
| Structurally Aligned Subtask-Level Memory | Subtask-granular coding memory with aligned retrieve/update operations | Retrieved context rather than prompt-excluded bounded controller state; does not evaluate the fixed repeat-harm causal contract. |
| PROJECTMEM | Typed event log and deterministic pre-action repeated-fix gate | Textual summaries/warnings and small self-study; does not report randomized matched-arm evidence. |
| SWE-Bench-CL | Chronological coding sequences; memory-enabled/disabled comparison; transfer/forgetting | A benchmark/protocol contribution that does not evaluate the same state carrier or causal-mechanism isolation. |
| Accumulated Behavioral Rules | Direct cross-session error-class recurrence objective in production | Human-approved instruction rules; 11-session observational report; does not evaluate randomized matched controls. |
| Causal Memory Selection | No-memory/memory/perturbed-memory comparison | Memory selection rather than bounded non-prompt controller state; does not evaluate a software-recurrence endpoint. |
| StructAgent | Unified compact state; verifier-backed transitions and recovery | Primarily within-task progress state; does not report a same-subject standardized cross-task prior-failure experiment or blinded causal report. |
| SOPHIA | Online self-loop detection and causal activation steering | Evaluates a transient hidden-activation intervention; does not report persistent cross-task machine-addressable controller state. |
| Memory in the Loop | Causal latency intervention with redundant-action endpoint | Evaluates access latency and in-loop retrieval; does not report persistent failure-sensitive state or cross-task recurrence. |
| AgentAbstain | Paired executable act/abstain counterfactuals and anti-inertia scoring | A verification benchmark that does not evaluate a cross-task memory treatment; supplies a key co-gate pattern. |

## 8. Reviewer-objection map

| Objection | Answer that the evidence must support |
| --- | --- |
| “This is Remember When It Matters.” | It is the closest identified active-memory neighbor; our differentiator is non-prompt bounded reranking plus randomized state clamps and fixed recurrence/utility estimands. |
| “Causal memory intervention already exists.” | Correct. We cite it and claim the live system-level causal-verification contract, not first intervention. |
| “This is Dynamic Coding Memory or SWE-Bench-CL.” | Those establish recurrence/continual coding. Our experiment tests a different carrier against both textual experience and a matched persistent count/EMA falsifier. |
| “`s_m` is a renamed counter.” | The scalar arm competes over a frozen last-bit/count/EWMA/Beta grid with the same recognizer, scope, head, and at least Pneuma's development budget; H1 must beat the selected controller. Otherwise the rich state claim fails. |
| “The gain is extra context or compute.” | Core Pneuma adds no prompt text; all arms share the candidate call and complete caps/accounting for reflection, maintenance, repair/fallback, tokens, tools, retries, and failed calls; realized resources and utility frontiers are reported, not adjusted away. |
| “Standardized exposure is artificial or belongs to another agent.” | Yes to artificiality, no to foreign exposure: confirmatory exposure is the same frozen subject's live verified failure under a common untreated prefix. Natural sequences and B-live are secondary, with B-live scoped to its known-motif target population. |
| “The metric rewards refusal, a crash, or a new error.” | Every observed agent-side non-engagement or branch-local failure is adverse; only a proven common exogenous whole-block outage is removable; total/new-family failure, success, completion, and counterfactual false avoidance are mandatory co-gates. |
| “The recognizer smuggles memory in or declares its own success.” | It sees current-task/within-opportunity observables only, predicts a generator-held recurrence fact fixed before action, and is separate from the update signal and arm-blind outcome evaluator in code, data, parameters, imports, and schemas. |
| “The reporter decodes the receipt or clamp metadata.” | Inputs are target-symmetric and intervention identity is withheld; nine-label macro metrics, minimum coverage, risk–coverage, no-change specificity, a receipt-only decoder, and behavioural-inertness controls are required. |
| “There are 96 tasks, so the study is powered.” | Surface variants, challenges, and seeds are nested within the highest shared authored prototype/generator lineage. Power, bootstrap, and assignment replay operate at that auditable lineage unit. |
| “A five-contrast sign flip is not the randomization.” | Correct. Inference replays the recorded seven-arm assignment by permuting all seven labels within each original block and re-aggregating seeds and lineages after every draw; H1–H4 each yield one family decision and H5 is tested only inside H1. |
| “E-0 already says state is worse.” | E-0 is disclosed: it falsified passive failure prediction and motivated Retry-count, fixed opportunities, identical caps, and a causal behavioural endpoint. |
| “Generalization is overstated.” | Confirmatory H4 covers known motifs across new surfaces/repositories only; Suite B-live is limited to its mechanically scorable frozen population and unseen-motif transfer is exploratory. |

## 9. Scoop assessment

The component landscape is crowded, especially after the July 2026 releases.
The strongest novelty threats are Remember When It Matters (active structured
memory), Faithful Self-Evolvers (causal experience interventions), Structurally
Aligned Subtask-Level Memory/PROJECTMEM (coding-memory structure and pre-action
gating), and Dynamic Coding Memory/Accumulated Behavioral Rules (coding
recurrence).
None makes our planned result automatic; together they make broad novelty
language indefensible and the Motif-count/EMA baseline mandatory.

The same papers strengthen the Verify-Agents submission:

- active memory can affect behaviour, so causal faithfulness is a real question;
- memory can narrow search, so H5 discrimination/utility co-gates are essential;
- process taxonomies reveal what resolve rate hides, supporting a typed trace
  endpoint rather than final success alone; and
- causal interventions on experience are now expected, raising the bar from
  “memory improves Pass@1” to a verifier-valid, anti-gamed mechanism test.

## 10. Citation and writing rules

1. Use proceedings metadata where available; label all other works “arXiv
   preprint” even if their record comments name a conference.
2. Never write “all prior memory is passive token reinjection,” “no prior work
   intervenes,” “coding agents are memoryless,” “no one studies recurrence,” or
   “TraceProbe is single-trajectory only.”
3. Describe our mechanism accurately: state stays outside the frozen LM weights
   and every behavioural/action prompt and boundedly reranks a shared candidate
   set. Only one-way inert notice-measurement and post-behaviour report calls may
   serialize it; those diagnostic forward passes cannot affect behaviour.
4. Replace every legacy arm-specific RUF statement with fixed-denominator
   `repeat_harm` plus utility co-gates.
5. Replace exact post-treatment transcript replay with a frozen common prefix and
   independently live cloned descendants.
6. Self-report is intervention-blinded causal attribution, not introspection or
   consciousness evidence; it uses nine joint labels, target-symmetric inputs,
   and a receipt-only decoder baseline.
7. Treat the highest shared authored prototype/generator lineage as independent;
   replay the actual seven-label assignment rather than sign-flipping contrasts.
8. Freeze every criterion, margin, transform, and controller grid on development
   data before the pilot; the pilot may expose pooled/blinded nuisance quantities
   only and its lineages never enter confirmation.
9. Refresh arXiv, ACL Anthology, NeurIPS proceedings, OpenReview, and the
   Verify-Agents accepted-paper list immediately before paper freeze; log any
   changed novelty claim in `15-decision-log.md`.
