# 02 — Research Thesis and Locked Design Constants

**Status:** canonical, Protocol v2, revised 2026-07-22. Every downstream
document MUST agree with Section 8. Changes to a locked constant require a row
in `15-decision-log.md`. `16-protocol-v2-hardening.md` records the red-team that
motivated DL-16–DL-45; this file incorporates those decisions and is now the
canonical statement of the study. `18-mathematical-formalism.md` is its
subordinate mathematical companion; it adds notation and conditional proofs but
cannot amend a locked constant.

The current research goal authorizes local implementation, tests, governed
data processing, and local experiments. It does not authorize paid RunPod use:
that remains blocked until the user approves an exact matrix and worst-case
cost. The repository remains standalone and must neither import from nor write
to the 9to5 repository.

---

## 1. One-sentence description

We test whether giving a software-engineering agent a **persistent, causally
active, machine-addressable internal state** reduces fixed-denominator repeated
harm after a standardized prior failure under the DL-45 selected-tier
comparison and causal-intervention rule. Notice and explanation are
registered-secondary descriptive outputs in this gate-first study; they cannot
gate or rescue the tier-primary claim.

## 2. Anchor question—do not drift

> Does giving a software agent a persistent, causally active internal state
> reduce repeated harm after a standardized prior failure, and by how much?

The inert notice readout and post-behaviour explanation program remain
registered-secondary/descriptive under DL-45. They test recognition and
attribution without entering selected-tier power or confirmatory continuation.

The study is a controlled behavioural comparison plus randomized state-level
interventions. It is **not** a consciousness or sentience demonstration.
Interiority terms such as scar, confidence, caution, and self-model name
measurable engineering variables only; no phenomenal claim is made.

## 3. Confirmatory estimand and primary hypothesis

### 3.1 Primary estimand

Each independently authored prototype/generator lineage `g` contains one or more
surface/task sequences `q`. Variants, challenges, and decoding seeds descended
from the same prototype are nested replicates, not new independent units. Each
sequence contains:

- a live verified pre-treatment failure exposure receipt `E_qm` for motif family
  `m`, produced by the same frozen checkpoint and shared scaffold under a common
  untreated prefix at a preregistered seed, then cloned into every condition
  before arm mapping; and
- a fixed list of `J_qm` post-exposure opportunity tasks whose registered slots
  are fixed by the generator before execution.

The receipt binds checkpoint, prompt, tools, seed, sandbox, full prefix trace,
actor-visible fields, and exact mechanical failure verification. Each condition
may consume only the actor-visible fields of that same subject's receipt through
its declared carrier; Base discards all prior-task information. No arm receives
an oracle motif id, counterfactual label, or evaluator judgment. Scripted or
foreign-model exposures are engineering fixtures only and cannot enter
confirmatory evidence.
For arm `a`, define:

```text
repeat_harm_q(a) =
    (1 / J_qm) * sum_j I[same-family harmful failure OR observed agent-side
                          non-engagement/branch-local runtime failure under a]
```

Every observed refusal, timeout, premature finish, budget exhaustion, invalid
action, model error, OOM/disk exhaustion, sandbox corruption, or runtime failure
confined to one branch is an adverse event, not missing data; no cross-world
judgment about whether treatment "caused" it is required. Success and different-
family failures remain in the denominator; the latter also enters the total/new-
family-failure co-gate. A block may be removed only when immutable,
preregistered, arm-blind telemetry proves that one exogenous outage made the
complete seven-arm block unobservable independently of arm. Every uncertain or
branch-local case stays adverse, and even valid exclusions receive best/worst-
case attrition sensitivity analysis. A branch-local missing scheduled slot is
scored adverse. A missing generator artifact or failed common preflight
invalidates the run before assignment rather than creating an outcome-dependent
exclusion.
This is the effect of policy after a **standardized prior failure**. Natural
end-to-end first-failure incidence and recurrence are secondary outcomes and
never use an arm-specific eligibility denominator.

### 3.2 Operational meaning of “notice”

“Notice” means that, at one frozen pre-action decision point, a calibrated
`NoticeReadout` identifies the generator-held pretreatment fact that the current
opportunity matches the subject's previously exposed known motif. This target is
fixed before action and cannot be changed by condition or outcome. Every arm
emits the same schema from identical current-task/within-opportunity observables
plus only that arm's legitimate carrier: no prior-task carrier for Base,
retrieved records for Retrieval, written lessons for Reflection, retry count for
Retry-count, scalar hazard for Motif-count/EMA, and structured state for Pneuma
and Influence-off. The shared current-only recognizer has no persistent input;
carrier-conditioned notice logic is arm-local and may not become a hidden shared
memory channel. Carrier access follows each arm's declared contract. Pneuma's
structured state may be serialized only into the separately metered,
behaviourally inert notice-measurement call; it is never serialized into a
candidate-generation, repair, fallback, tool, or other behaviour-producing
prompt. Retrieval and Reflection use only their declared carriers at the same
measurement boundary.

All arms use the same frozen actor checkpoint, notice prompt scaffold/schema,
decoding settings, maximum measurement tokens, and number and timing of readout
calls. These equal measurement calls are separately metered and reported.
The readout is behaviourally inert: it is captured before action, cannot alter
candidates, prompts, actions, action/token budgets, state updates, or retry
paths, and never enters the behavioural score. Target opportunities, decoys,
and counterfactuals are exactly balanced within every registered notice cell.
For frozen pre-action target `y in {0,1}` and reported probability `p in [0,1]`,
the primary scalar is the bounded proper score

```text
NoticeScore = 1 - mean((p - y)^2)                 # higher is better, [0,1]
```

It is averaged through the same equal cell → lineage → motif hierarchy as the
behavioural endpoint. Macro discrimination/AUROC, calibration, coverage, and
target/decoy/counterfactual specificity remain preregistered hard validity
gates; they are not silently collapsed into the scalar. Calibration is explicitly
with respect to the registered balanced opportunity distribution, not an
estimate of natural-world motif prevalence. `NoticeProbability` is
separate from the online update
signal, actuation pressure `L_m`, and arm-blind outcome evaluator. This does not
mean subjective awareness. If Pneuma fails its frozen discrimination,
calibration, coverage, and five carrier-matched superiority endpoints, the paper
does not claim that it noticed recurrence even if repeat harm decreases.

### 3.3 H1 (recognition and behaviour)

After the common verified exposure, (a) Pneuma's pre-action risk readout meets
frozen known-motif discrimination/calibration/coverage criteria and exceeds the
readout from **each** H1 comparator—Base, Retrieval, Reflection, Retry-count,
and persistent Motif-count/EMA—and (b) Pneuma-state reduces fixed-denominator
`repeat_harm` relative to those same five comparators. Influence-off is an H2
mechanism diagnostic, not a sixth H1 comparator. H1 is an intersection–union
claim, not a comparison selected against the observed best baseline. It is
supported only if every notice contrast, every behavioural contrast, and every
utility/anti-gaming non-inferiority gate passes.

For comparator `a`, let `Delta_a = repeat_harm(a) - repeat_harm(Pneuma)` and
`Gamma_a = NoticeScore(Pneuma) - NoticeScore(a)` after the registered hierarchy;
positive values favour Pneuma. The locked smallest observed behavioural effect
of scientific interest is a 0.05 absolute repeat-harm reduction: every
`Delta_a` point estimate must be at least 0.05 and every simultaneous one-sided
95% lower bound for `Delta_a` and `Gamma_a` must exceed zero. Notice components
also must pass their frozen absolute validity gates, but the behavioural 0.05
magnitude rule is not applied to the notice-score scale. This supports a
statistically positive effect whose observed repeat-harm magnitude is at least
five points; it does not claim the true effect is at least five points.
Utility/engagement/total-failure non-inferiority margins are also 0.05 on their
absolute rate scales and are frozen on dev before pilot.

The observed five-point rule is not the design alternative used for power. The
declared power alternative is `Delta_power = 0.10` on every H1 superiority
component's registered absolute-difference scale. Monte Carlo sample-size
selection must achieve at least 80% probability that the **complete H1
conjunction** passes—all five notice contrasts, all five repeat-harm contrasts,
and every utility/anti-gaming non-inferiority gate—under one frozen joint DGP
with true utility differences zero and the preregistered margins. The blinded
pilot supplies pooled nuisance quantities only and may declare infeasibility
under a preregistered rule; it cannot validate, tune, or alter margins, notice
criteria, the 0.05 observed-effect rule, or `Delta_power`. The study must never
be described as powered at the 0.05 SESOI.

## 4. Supporting hypotheses

- **H2 (causal state influence).** With state updates and receipts held live,
  setting every state-to-action gain to zero removes the Pneuma advantage.
  Randomized eligible-decision clamps of `s_m` and the other state variables
  shift actions/outcomes in the preregistered direction; dose clamps exhibit the
  predicted ordering; restore and no-op operations fall within frozen
  equivalence bounds. A mandatory persistence-off branch resets prior state
  immediately after the common exposure and before the scheduled opportunity.
  Until after the first scheduled decision, the actor, updater, carrier, and
  head receive only a same-shape inert receipt handle. The immutable receipt may
  subsequently enter only the audit/report path; it can never rehydrate reset
  state through an actor path. Current task, candidates, and head are otherwise
  preserved;
  loss of the intact advantage is required to credit persistence. Component
  clamps estimate controlled-coordinate sensitivity and are not required to
  reproduce Base.
- **H3 (causal-attribution faithfulness).** Across randomized intervention pairs,
  the same frozen actor checkpoint, invoked in a separate post-behaviour report
  call with a fixed prompt/scaffold and no tools or feedback, must predict one
  of nine joint labels—four variables × two
  directions plus `no_attributable_change`—from a target-symmetric public trace
  schema that withholds operation names, target fields, assignment metadata, and
  target-dependent missingness. The non-none label is correct only when a
  verified action/outcome divergence occurs; otherwise the correct label is
  `no_attributable_change`. Frozen macro accuracy/recall, minimum coverage,
  risk–coverage, and simultaneous bounds must exceed uniform/prior and receipt-
  only decoder baselines; all nine classes require adequate support or H3 is
  inconclusive. The call receives only a target-symmetric public packet and its
  legitimate report-time state, has a separately metered report budget/cost,
  and can never feed behaviour. Conditional direction accuracy and no-change
  specificity remain separate diagnostics. Grounded+verified must improve on
  unconstrained reporting. Deterministic-template and receipt-only decoders are
  controls, not agent self-reports. This is trace-grounded causal attribution,
  not phenomenal introspection.
- **H4 (known-motif generalization).** H1's effect survives preregistered surface
  transformations and repository holdouts for known motif families. Zero-shot
  transfer to unseen motif families is exploratory unless a separate, leakage-
  controlled motif generalizer is implemented and preregistered.
- **H5 (discrimination rather than inertia).** Pneuma-state does not manufacture
  lower repeat harm by refusing, timing out, stopping early, or avoiding a
  previously bad strategy when it becomes correct. Attempt/completion, verified
  task success, total/new-family failure severity, and counterfactual false
  avoidance must all satisfy frozen non-inferiority gates.

## 5. Claim tiers

1. **Engineering:** the seven arms, benchmark, state path, causal harness,
   prose-blind evaluator, and artifact binding run reproducibly.
2. **Behavioural:** H1, supported by fixed-denominator paired cluster contrasts
   and simultaneous intervals.
3. **Causal:** H2, supported by randomized influence-off/clamp/dose/null evidence.
4. **Generalization:** H4, restricted to tested known-motif surface/repo regimes.
5. **Causal attribution:** H3, tested separately from behaviour.
6. **Phenomenal consciousness:** **not claimed**.

Tiers 1–3 are the core. Tiers 4–5 strengthen the paper. Tier 6 is explicitly
outside scope. Every result sentence must identify its tier and evidence path.

## 6. Decision regions and honest negatives

Every hypothesis has three preregistered regions: **supported**, **practically
refuted** relative to a frozen equivalence/smallest-effect interval, or
**inconclusive**. Failure to reject a null is never described as falsification.

- **H1 supported** only if the recognition endpoint, all comparator superiority
  tests, and all H5 co-gates pass. It is practically refuted for the broad claim
  if recognition fails its frozen practical region or a comparator contrast
  excludes the required benefit. Otherwise it is inconclusive.
- **H2 supported** only after H1 passes and the influence-off, randomized clamp,
  dose, mandatory persistence-off reset, equivalence-powered stochastic null,
  and wiring-null pattern is jointly coherent. If influence-off is practically
  equivalent to intact Pneuma, state is epiphenomenal; if persistence-off does
  not remove the preregistered carryover advantage, persistence is not credited;
  if a wiring null moves behaviour, the harness is invalid.
- **H3 supported** only on intervention-blinded nine-class reports with frozen
  macro, coverage, risk–coverage, no-change, calibration, and baseline-superiority
  criteria. Receipt copying, asymmetric public fields, access to clamp metadata,
  a matching receipt-only decoder, or inadequate class support blocks the agent-
  explanation claim.
- **H4 supported** only for the exact preregistered holdout axes that retain the
  H1 decision. A surface-only result is not called repository generalization.
- **H5 passes as H1's anti-gaming component** only if every utility gate passes.
  It is not a second global hypothesis test. A repeat-harm reduction with worse
  utility is reported as avoidance/inertia, not useful learning.

The mandatory Retry-count control follows the recorded E-0 negative result:
passive psyche signals predicted failure worse than retry count (AUROC 0.34 vs
0.71) because of a length/activity confound. The dependent variable here is
behavioural repeat reduction under causal intervention, not passive failure
prediction. Identical ex-ante caps, resource-frontier reporting, and
fixed-denominator scoring address the confound without conditioning the primary
effect on post-treatment token/action use.

Negative and null causal results are first-class outcomes. For example, H1 true
with H2 practically null becomes evidence that persistent state correlates with,
but did not cause, the behavioural difference under this implementation.

## 7. Novelty boundary

The novelty claim is deliberately narrow: we test the **conjunction** of

1. persistent machine-addressable, non-prose state on the action-selection path;
2. paired randomized intervention on that state under frozen exogenous
   preconditions and live descendant branches;
3. a prose-blind behavioural endpoint separated from self-report; and
4. cross-task structural recurrence with anti-gaming utility co-gates.

Memory, reflection, recurrence tracking, agent interpretability, process-level
failure analysis, and interventions each have close prior work. The paper must
not claim that no prior work intervenes on memory, that prose cannot be
mechanistically analyzed, or that numeric state is intrinsically more
interpretable. `03-related-work-positioning.md` audits the closest 2025–2026
neighbors and limits any “first” language to the verified conjunction above.

---

## 8. LOCKED DESIGN CONSTANTS

These choices supersede incompatible Protocol-v1 text retained in documents
04–12.
Rationale and rejected alternatives appear in `15-decision-log.md`.

### 8.1 Subject model and shared scaffold (DL-01, DL-02, DL-31)

- Use one frozen open-weight coding-instruct checkpoint for each registered
  model stratum. Every arm within a stratum uses the exact checkpoint, prompt
  templates, sampler, candidate count, tools, repair path, retry cap, ex-ante
  model-call/action/token caps, task order, sandbox distribution, and seed
  schedule. A second same-family size is robustness evidence, not permission to
  pool incompatible models.
- The common caps count every candidate/repair/fallback call, reflection-writing
  call, retrieval or state-maintenance call that uses the model, input/output
  token, attempted tool action, retry, and failed call. Prompt truncation and
  context-slot allocation are deterministic and frozen. Same-length shuffled-
  text and structured-state serialization diagnostics are mandatory before
  claiming that an effect survives a token/context explanation.
- Local development uses pinned Qwen2.5-Coder 1.5B and 7B quantizations subject
  to checkpoint/model-card and seed audits. Final checkpoint choice and
  replication scope are frozen after feasibility/power work, before the
  confirmatory split is revealed.
- The live subject is a minimal seed-pinnable structured-action loop outside
  `src/pneuma_lab/replay/`, with tools `read_file`, `edit_file`, `run_tests`,
  `search`, and `finish`. Replay remains an engineering/instrumentation path.
- Deterministic byte equality is an engineering property of pure fixtures, not
  evidence about a stochastic LLM agent.

### 8.2 Conditions (DL-03, DL-19, DL-31)

Seven core conditions are mandatory:

1. **Base:** no cross-task memory and zero state pressure.
2. **Retrieval:** deterministic top-k semistructured textual failure records.
3. **Reflection:** fixed-budget natural-language lessons re-injected later.
4. **Retry-count:** within-task identical-retry controller from the E-0 baseline.
5. **Motif-count/EMA:** the strongest dev-selected scalar per-motif hazard
   controller from a published grid containing last-failure bit, count, EWMA,
   and Beta-posterior hazard. It receives the same current-only recognizer,
   `LearningSignal`, motif vocabulary, clock, numeric precision, persistence
   scope, receipt rules, head, and at least the same development-trial budget as
   Pneuma; the full search ledger is frozen before pilot.
6. **Pneuma-state:** the four-variable state in §8.3 drives bounded reranking.
7. **Influence-off:** state updates/receipts remain live, but all state-to-action
   gains are exactly zero; this is H2's primary null.

Optional diagnostics, only if powered, are State×Retrieval, token-matched
shuffled memory, and recurrent-hidden-state controls. Component clamps are
interventions, not extra headline baselines.

Realized token/action use is an outcome and possible mediator. Fairness comes
from the complete common accounting boundary, identical ex-ante caps, and
candidate generation, not context padding or post-treatment matching/regression.
If the scalar controller ties Pneuma while both beat non-state/text arms, the
supported conclusion is that simple persistent state helps; the four-variable
controller is not credited as necessary.

### 8.3 Internal state (DL-04, DL-20, DL-28, DL-40)

State is external to the frozen model weights, deterministically updated at
task/opportunity boundaries, capped, and receipt-bound. It is never serialized
into any model prompt on the behavioural/action path. The only permitted prompt
serialization is through two one-way diagnostic sinks: the equal-metered inert
pre-action notice measurement in §3.2/§8.5 and the separately metered
post-behaviour report in §8.11. Neither sink can affect action, update, retry,
budget allocation, evaluation, or a later task:

1. `s_m`: decayed failure sensitivity for motif `m`.
2. `c`: reliability/calibration of the actor-side prospective forecast.
3. `t`: bounded caution homeostat, updated in task time rather than token/action
   time.
4. `r_m`: reliability of the prospective motif-risk recognizer. It is not
   retrieval trust and creates no hidden text-memory channel.

The centered expected-loss signal is

```text
L_m(x) = applicability_m(x) * r_m
         * clip(w_s*s_m + w_c*max(0, 0.5-c) + w_t*t, 0, 1)
```

Neutral state produces exactly zero pressure. `L_m` is bounded actuation pressure,
not a calibrated failure probability; `NoticeProbability` in §3.2 is a separate
readout with a defined pretreatment target. Constants are selected on the dev
split under the same search budget as Motif-count/EMA and frozen before
confirmatory execution. Every variable has update-off, influence-off, clamp,
restore, and audit hooks. The four variables and H3's nine labels are locked.
If `r_m` cannot pass its non-circularity and causal-activity development checks,
development stops; removing it requires a new decision-log amendment before
pilot and a global, synchronized change to a three-variable/seven-label
protocol. There is no automatic fallback.

### 8.4 Pressure, not commands (DL-05, DL-20)

In one identical model call, the scaffold requests a ranked fixed-size set of
structured candidate actions with normalized scores. Each candidate already
contains the model-proposed tool and arguments. The decision head may only add a
bounded score bias to a fixed meta-action class and rerank:

```text
chosen = argmax_k(log(model_score_k) + bounded_pressure[class(k)])
```

It cannot invent a tool call, change arguments, expand the candidate set, or
force an unavailable command. Base and Influence-off execute the same head with
a zero vector. Invalid-JSON repair and fallback behaviour are identical and
metered across arms. This is the operational meaning of “Pneuma emits pressure,
not commands.”

### 8.5 Three independent label paths and notice readout (DL-07, DL-17, DL-28, DL-34, DL-41)

1. **Prospective current-only recognizer, actor-side:** before selection, maps
   only current-task and within-opportunity observables to motif-applicability
   probabilities. It cannot consume a prior-task trace, exposure receipt,
   persistent store/state, generator id, future outcome, offline judge label, or
   report prose. Cross-task information reaches treatment arms only through
   their declared memory/state carrier.
2. **Online learning signal, actor-side:** after action/outcome, maps immediate
   tool status, tests, and structured history to a bounded update. It cannot
   import the offline evaluator.
3. **Offline evaluator, arm-blind:** scores immutable traces from pseudonymous arm
   ids. It cannot import condition/state/voice modules. Exact mechanical labels
   define the primary endpoint; judged semantic labels are secondary.

No shared learned parameters, test-set threshold tuning, or classifier output
may administer treatment and define the confirmatory outcome.

At the frozen pre-action point, a same-schema `NoticeReadout` combines the
current-only recognizer's public output with only the current arm's legitimate
carrier. It is recorded by a one-way instrumentation interface that has no
action, prompt, update, budget-allocation, retry, or evaluator capability. Each
arm's carrier adapter is separate; no shared notice component may retain
cross-task information. Checkpoint, prompt/schema, decoding, maximum measurement
tokens, and number/timing of calls are frozen identically, separately metered,
and reported for every arm. Pneuma's five carrier-matched notice contrasts
belong to H1, while Influence-off's readout is a mechanism diagnostic only.

### 8.6 Benchmark roles (DL-06, DL-16, DL-26, DL-27, DL-32)

- **Suite A—controlled live micro-repositories:** exact tests, behaviour labels,
  a same-subject live common pre-treatment failure, fixed opportunities, decoys,
  counterfactuals, and metamorphically validated surface transforms. Every
  scheduled opportunity starts from its own digest-bound repository snapshot;
  only the declared internal memory/state persists across tasks. Each authored
  prototype/generator lineage has a frozen digest carried into split, leakage,
  randomization, and preregistration manifests. These tasks create an opportunity
  for a behavioural failure to recur; they do not pretend to inject an agent
  failure as a source-code bug.
- **Suite B-offline—external validity:** re-extract governed raw Open-SWE-Traces
  and SWE-Gym/OpenHands trajectories to measure prevalence, observability,
  recognizer behaviour, and evaluator agreement. Open-SWE has 207,489 source
  rows, 160,731 emitted trajectories, and 14,107,506 steps in the audited local
  build; the processed digest-only JSONL is insufficient for semantic
  enrichment. Open-SWE is not a live causal suite.
- **Suite B-live—executable real repositories:** a power-feasible preregistered
  SWE-Gym subset with repository/base-commit/problem/test oracles, acquired into
  isolated digest-bound sandboxes. Its target population is the mechanically
  scorable known-motif subset, not natural SWE tasks in general; embedded
  standardized opportunities establish repository transfer, not prevalence.
- Use separate surface-holdout, repository-holdout, and motif-family analyses.
  Quarantine overlaps through the leakage registry. Do not promise a globally
  repo-and-motif-atomic split if the bipartite components make it infeasible.
- Subject-model weight training is out of scope. Derived analysis artifacts have
  explicit provenance and may not write back to `C:\pneuma-data`.

### 8.7 Failure taxonomy and outcome observability (DL-07, DL-17, DL-24)

The confirmatory taxonomy includes only motifs with preregistered observable
opportunity and outcome rules that the exact evaluator can score from typed
events. Candidate families include retrying a broken strategy, ignoring failing
tests, wrong-target edits, skipping required verification, destructive action,
and unsupported success claims. Each family remains provisional until fixtures,
metamorphic tests, blinded agreement, and evaluator error bounds pass.

The exact arm-blind outcome schema treats refusal, timeout, premature finish,
budget exhaustion, invalid action, model error, OOM/disk exhaustion, sandbox
corruption, and every branch-local runtime failure as adverse. `exogenous_outage`
is a separate, narrowly typed block-level outcome that is valid only when frozen
telemetry proves the same external event made all seven arms unobservable;
unknown or incomplete evidence cannot instantiate it.

Prose-dependent or low-agreement motifs are descriptive. Governed adapters may
process raw text transiently, but public trace frames contain typed bounded
features and digests rather than objective/output prose.

### 8.8 Metrics and anti-gaming co-gates (DL-08, DL-21, DL-24, DL-31, DL-35)

- **Primary:** fixed-denominator, equal-opportunity-weight `repeat_harm` in §3.
  Severity-weighted recurrence is secondary. RUF is
  retained only as a readable alias when it denotes this exact estimand; all old
  arm-specific post-exposure definitions are retired.
- **Mandatory co-gates:** attempt, completion, verified task success,
  total/new-family failure severity, refusal, timeout, premature finish,
  invalid/model/runtime failure, and counterfactual false avoidance.
- **Secondary:** first harmful-failure incidence, natural-sequence policy value,
  recovery, resource use/frontiers, constraint violations, calibration,
  intervention effects, surface/repo transfer, and cross-seed stability.

Self-report is never a behavioural input. A new failure, refusal, or budget
exhaustion cannot silently count as a successful avoidance.

### 8.9 Causal branch semantics (DL-09, DL-18, DL-30, DL-32, DL-40)

Freeze the common prefix, initial sandbox snapshot, checkpoint, prompts/config,
sampler settings, and exogenous seed schedule. Clone that state, apply the
randomized intervention, then run every descendant branch live. Later prompts,
tool outputs, files, state, and actions may differ because they are downstream
of treatment; freezing their realized transcript would create an incoherent
off-policy world.

The causal battery is intact vs Influence-off, randomized `s_m` and component
clamps at eligible decisions, low/high/dose clamps, update-off vs influence-off,
motif permutation/scramble, mandatory persistence-off reset immediately after
exposure and before a scheduled opportunity, a no-op/sham receipt schedule,
self-report disabled, prompt-text serialization of the same structured
information, and restore/no-op wiring nulls. Persistence-off preserves the
current task, candidate call, and head, but the actor, updater, carrier, and head
receive only a same-shape inert receipt handle until after the first scheduled
decision. The immutable audit/report receipt remains sealed from those paths at
all times and cannot rehydrate state; after the decision it may enter only the
audit/report path. A branch that fails to reach the scheduled opportunity
is retained as adverse ITT. Exact
prefix equality must hold through intervention time `t0`; post-intervention
divergence may begin no earlier. For stochastic subjects, compare the first post-
intervention structured-intent distributions across seeds with total-variation
or Jensen–Shannon summaries on frozen categorical support. Null validity uses a
preregistered equivalence margin, symmetric RNG handling, powered repeated
draws, and sham/no-op/restore distributions—not failure to reject a difference.
Active causal effects come from randomized assignments and paired outcomes; TV/
JS is a gate/diagnostic, not causal evidence by itself. Do not align arbitrary
later ticks after branch lengths differ. Byte-equal clones remain an engineering
oracle only.

### 8.10 Estimation, inference, multiplicity, and power

#### Estimand aggregation and lineage (DL-26, DL-35)

- The primary opportunity indicator has weight one. First average all scheduled
  opportunities within a registered sequence×surface×challenge×decoding-seed
  cell. Within the highest shared authored semantic prototype/generator lineage,
  give equal fixed design weight to every such registered cell; then give equal
  weight to lineages within motif and equal weight to every preregistered motif
  stratum. The registry fixes the nesting and cell weights before pilot.
  Severity-weighted and alternative population-weighted estimates are secondary.
- Tasks sharing task-semantic prototype code, generator function/template, or
  task-specific verifier ancestry are one lineage; literals, names, surface
  rewrites, challenges, and decoding seeds descended from it are nested. A
  shared generic runtime, sandbox scaffold, or evaluator interface alone does
  not merge independently authored semantic opportunities. The registry records
  ancestry and digests. Any ambiguity is resolved before outcomes by arm-blind
  adjudication using a conservative merge; it may not be split after results.
- A post-assignment branch-local missing opportunity occupies its registered
  slot and is adverse. One proven common exogenous outage masks that exact slot
  atomically for all seven arms. Remaining fixed design weights are renormalized
  by the same arm-independent rule, and best/worst attrition sensitivity is
  mandatory. A missing generator artifact or failed common preflight invalidates
  the run before assignment; it cannot be repaired as selective missingness.

#### Assignment and two distinct inference targets (DL-25, DL-36, DL-37)

- In every complete model×lineage×sequence×seed block, let `M ~ Uniform(7!)`
  map seven policy labels to fixed clone/RNG-stream ids. Independently let
  `O ~ Uniform(7!)` order those stream ids for execution, giving every joint draw
  probability `1/(7!)^2`. Pre-issued seeds bind both draws, their support indices,
  and realized permutations into the run receipt. Any later restriction or
  dependence requires a pre-pilot decision-log/preregistration amendment and
  replay of the exact conditional mapping support, or the full joint design if
  conditioning is no longer valid. Missing, non-uniform, or unverifiable
  assignment makes the
  confirmatory causal claim no-go rather than turning randomization inference
  into decoration.
- Fisher randomization inference addresses only the **sharp global null**.
  Exhaustive enumeration is used when feasible; otherwise at least 100,000
  plus-one-corrected Monte Carlo draws condition on realized `O` and rerandomize
  `M` over its exact conditional `7!` support; this is valid because `M` is
  independent of `O`. Every draw redoes the full
  registered aggregation, studentization, and max-T statistic. Seeds aggregate
  only after rerandomization. A whole-vector sign flip is forbidden. These are
  design-exact sharp-null p-values, up to declared Monte Carlo error; they are
  not confidence bounds for a population-average effect.
- Primary average risk differences and simultaneous one-sided 95% confidence
  intervals use at least 10,000 motif-stratified prototype-lineage cluster-
  bootstrap resamples, carrying every nested cell of a sampled lineage together,
  with studentized max-T across the registered component contrasts. Suite
  B-live uses the highest shared repository plus semantic generator/prototype
  ancestor as its cluster. Random assignment identifies the causal contrasts;
  the cluster bootstrap targets population-average uncertainty. Nested-cell
  resampling, hierarchical logistic/GEE models, and alternative attrition models
  are sensitivity analyses, not replacements for the primary hierarchy.

#### Family decisions and global error control (DL-29, DL-38)

Each component below receives its preregistered one-sided lineage-cluster
population p-value; sharp-null Fisher p-values are reported separately. For an
intersection–union family, the family p-value is the maximum component p-value.
A failed hard validity/coverage/support gate makes that hypothesis inconclusive,
not supported.

- `p_H1` is the maximum over five Pneuma notice-superiority p-values, five
  Pneuma repeat-harm-superiority p-values, and every preregistered utility/
  anti-gaming non-inferiority p-value. Frozen discrimination, calibration, and
  coverage criteria and the observed repeat-harm rule (point estimate at least
  0.05 and simultaneous lower bound above zero for every comparator) are
  additional hard gates. H5 is embedded here and is not retested.
- `p_H2` is the maximum of the intact-over-Influence-off component,
  intact-over-persistence-off component, directional randomized-clamp omnibus,
  monotone dose/order component, and equivalence/wiring-null family. For each
  equivalence contrast with frozen margin `epsilon`, `p_TOST =
  max(p_lower, p_upper)`; the wiring-null family is the maximum over its TOST
  p-values. Restore/sham/no-op integrity remains a hard gate.
- `p_H3` is the maximum over nine-class macro superiority versus uniform,
  empirical-prior, receipt-only decoder, and unconstrained-reporting baselines,
  coverage non-inferiority, no-change specificity, and the frozen risk–coverage
  component. All nine labels,
  target-symmetric packet integrity, and minimum class support are hard gates.
- Surface-holdout and repository-holdout known-motif analyses each form a full
  H1-like family decision. `p_H4` is the maximum of those two family p-values;
  success on only one axis cannot support H4.

Apply Holm's procedure at familywise `alpha = 0.05` across all four prespecified
slots `p_H1`–`p_H4`. An unavailable, invalid, or inconclusive family is assigned
`p = 1`; it is never dropped to reduce multiplicity. Logical interpretation is
stricter than multiplicity alone: H2 is interpreted only if H1 passes; H3 as
“why behaviour changed” only if H1 and H2 pass; H4 only if H1 passes. Freeze any
exploratory BH-FDR family before analysis and never select the observed best
baseline.

#### Power and reporting (DL-21, DL-32, DL-33)

- The fixed 30-lineage disjoint authored-prototype pilot estimates pooled/blinded
  event rates, dependence, detector error, attrition, and paired variance only.
  The deterministic Monte Carlo sample-size rule uses the complete estimator,
  assignment, simultaneous-inference, magnitude, and non-inferiority decision
  logic under one frozen joint DGP. Its declared design alternative is
  `Delta_power = 0.10` for every H1 superiority component, true utility
  differences are zero, and utility margins are the preregistered margins. The
  selected lineage count must give at least 80% probability that the **entire H1
  conjunction** passes. This is not power at the 0.05 observed SESOI. If no
  feasible count satisfies that rule, the confirmatory run is no-go or follows
  a separately preregistered scope-narrowing rule.
- Motifs, transforms, checkpoint-selection rules, notice/evaluator criteria,
  hyperparameters, margins, controller grids, `Delta_power`, and the DGP freeze
  on development before pilot. Blinded nuisance re-estimation cannot alter
  them, and there is no effect-dependent optional stopping. Pilot lineages and
  tuning surfaces never enter confirmation.
- Do not covariate-adjust the primary effect for realized action/token counts;
  report them as outcomes and use only preregistered pre-treatment precision
  covariates in sensitivity analyses. Report absolute paired risk differences,
  risk ratios, motif-specific effects, Monte Carlo error, and sensitivity
  results. Cohen's `d` is never the sole effect size for binary/rate outcomes.

### 8.11 Self-report (DL-11, DL-29, DL-39)

Four report modes operate over the same eligible paired episodes: deterministic
template, unconstrained LLM, grounded LLM, and grounded+verified. The reporter
is the same frozen actor checkpoint invoked in a separate post-behaviour call
with a fixed report prompt/scaffold, no tools or feedback, and a separately
metered report budget/cost. It receives a target-symmetric public packet plus
only its legitimate report-time state and never receives intervention names or
target labels. Public fields expose no operation name, target-specific field,
old/new intervention receipt, assignment probability, or target-dependent
missingness. Report output cannot feed any action, state update, behavioural
score, or later task.

Ground truth is one of the eight variable×direction labels only when the paired
intervention changes an action or verified outcome; otherwise it is
`no_attributable_change`. A receipt-only decoder receives exactly the same public
packet, and a deterministic template remains a system-audit control; neither is
called agent self-report. Report nine-class macro metrics, accuracy–coverage,
risk–coverage, abstention, no-change specificity, conditional direction accuracy,
unsupported-claim rate, calibration, and behavioural consistency separately
from H1/H2. If the decoder matches the reporter, describe receipt decodability/
system auditability rather than agent self-explanation.

### 8.12 Fixed nominal roster and power-selected independent sample (DL-44)

The nominal roster is fixed; the independent-lineage count is not guessed.
Before the paid-compute checkpoint:

- nuisance-only pilot: exactly 30 disjoint authored prototype lineages from the
  pilot split;
- Suite-A confirmatory: exactly 96 registered sequences across six
  high-precision motifs (16 per motif), nested within the number of genuinely
  independent authored prototype lineages selected by the locked rule in
  §8.10, with three challenges, seven arms, and two decoding seeds, and
  Qwen2.5-Coder-7B as the primary model; the 96 sequences never count as 96
  independent units unless all 96 highest-lineage digests are distinct;
- local robustness: Qwen2.5-Coder-1.5B on the same design or a preregistered
  subset;
- causal battery: exactly 48 of the registered Suite-A sequences, balanced as
  eight per motif, covering Influence-off, sham, reset, permutation, update-off,
  and dose interventions;
- Suite-B-live external validation: exactly 36 sequences across four
  mechanically scorable known motifs (nine per motif) and the frozen
  repository/prototype target
  population, explicitly labelled underpowered external validation if lineage-
  cluster power is insufficient; and
- Suite-B-offline: Open-SWE/OpenHands discovery and detector/evaluator validation,
  never a live treatment comparison.

The independent Suite-A confirmatory sample size is
$G^\star=\min\{G:\pi_{H1}(G)\geq0.80\}$ under document 18 equation (21), using
only the locked nuisance-only pilot projection. Neither $G^\star$ nor attainment
of the 0.80 target is a proved number at this planning checkpoint because the
nuisance quantities do not yet exist. If $G^\star$ cannot be instantiated
inside the fixed 96-sequence registry, the run is no-go or invokes the
predeclared scope-narrowing rule; nested challenges, transforms, and seeds may
not be counted as substitute lineages.

No controller weight training is planned. Every paid run requires a locally
validated bundle, exact runtime forecast, current provider price, cost ledger,
and explicit user approval; total paid spend is hard-capped at USD 50.

### 8.13 Venue and publication (DL-12, DL-22)

Primary: **Who Verifies the Agents?—Toward Reliable Agent Development @ NeurIPS
2026**. The official call accepts 4–9 pages excluding references and appendices,
uses double-blind review, is non-archival, and lists a **2026-08-29 AoE**
deadline. The fit is direct: process-level verification, environment-grounded
outcomes, verifier validity, reward-hacking controls, calibration, cost, and
long-horizon reliability are the hardened study's central contributions.
The NeurIPS 2026 meeting and workshop are in Sydney, Australia.

Secondary: **IAB—Interpreting Agent Behavior @ NeurIPS 2026**. It remains a
credible fallback for the state-intervention and causal-attribution framing.
The IAB site/OpenReview one-day discrepancy is operationally relevant only if
we pivot.

Use the checksum-pinned official NeurIPS 2026 template in
`dblblindworkshop` mode with
`\workshoptitle{Who Verifies the Agents? Toward Reliable Agent Development}`.
The anonymous submission exposes hashes/pseudonymous ids, not author identity,
local paths, repository ownership, acknowledgments, or PDF author metadata. The
long paper targets 8.7–8.8 body pages before float placement; the four-page
fallback preserves the causal estimand, strongest controls, and honest result.

---

## 9. System coherence

```text
         one frozen model stratum + one structured-action scaffold
                              |
  Base | Retrieval | Reflection | Retry | Motif-EMA | Pneuma | Influence-off
                              |
             common verified exposure receipt
                              |
         fixed opportunities in cloned live sandboxes
                              |
    immutable typed traces with pseudonymous condition labels
                 /                              \
   arm-blind exact evaluator             report-faithfulness track
   repeat_harm + utility gates           (never feeds behaviour)
                 |
  paired cluster inference + randomized state clamps + wiring nulls
```

The prospective recognizer and online updater exist only on the actor side. The
arm-blind evaluator owns the behavioural endpoint. The reporter owns only H3.
All three are separated by interfaces, imports, schemas, and tests. This is the
minimum architecture capable of answering the anchor question without circular
labels, post-treatment selection, or decorative self-report.
