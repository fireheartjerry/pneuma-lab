# 16 — Protocol v2 Hardening Addendum

**Status:** hardening rationale and amendment history, 2026-07-22. The revised
`02-research-thesis.md` now incorporates this addendum and is canonical; this
document supersedes incompatible Protocol-v1 text retained behind stop banners
in documents 04–12. The unchanged anchor
question is whether persistent, causally active, machine-addressable state helps
a software-engineering agent notice recurring failure patterns, avoid repeating
them, and accurately attribute behaviour changes. No phenomenal claim is made.

No confirmatory run may start until the canonical thesis, task backlog, schemas,
power simulation, and preregistration all agree with this addendum. Changes to
locked constants are recorded as DL-16–DL-41 in `15-decision-log.md`.

## 1. Why protocol v1 is no-go

The repository and methodology audit found that zero of the 39 planned tasks is
implemented and that the following problems are in the design, not merely the
code:

1. **Post-treatment eligibility.** V1 defined first exposure separately within
   each arm and dropped motifs that never failed. Treatment therefore changed
   both the RUF numerator and denominator.
2. **Retrospective signal used prospectively.** `detectFailure` fired only after a
   failure but was also supposed to tell the head which motif was currently at
   risk. It could not prevent the event it had already observed.
3. **Shared treatment/outcome label path.** The same detector both updated state
   and scored the primary outcome, admitting mechanical label leakage.
4. **Impossible counterfactuals.** Freezing prompts, retrieved memory, and tool
   transcripts after behaviour diverged fixed descendants of treatment and
   created off-policy worlds.
5. **Incoherent treatment/null.** Memory-trust required retrieval although the
   state arm was specified as retrieval-free; clamping only `s_m` left other
   state paths active and could not be expected to reproduce Base.
6. **Weak heuristic control.** A within-task retry counter did not control for a
   persistent per-motif count/EMA controller, the simplest explanation for any
   state benefit.
7. **Gaming.** An agent could reduce RUF by refusing, stopping, or substituting a
   new failure. Task utility and attempt/completion were not headline co-gates.
8. **Invalid inference.** The bootstrap ignored crossed sequence/seed/repository
   dependence; post-treatment token/action adjustment targeted a mediator; the
   best observed baseline and five uncorrected hypothesis families inflated
   error.
9. **Overstated generalization and introspection.** A motif-indexed state cannot
   transfer to an unseen motif without an explicit generalizer, and a reporter
   given clamp metadata measures receipt copying rather than causal attribution.
10. **Execution/data mismatch.** Open-SWE-Traces has trajectories but no checked-
    out source/test oracle and is not a live task suite. The local data root has
    no repository snapshots or runnable images.

These are fatal for a confirmatory claim. The remainder defines the replacement.

## 2. Target estimands

### 2.1 Primary: standardized post-exposure recurrence

The independent unit is the highest shared authored prototype/generator lineage
`g`; surface variants, challenges, and seeds are nested replicates. Each sequence
`q` contains motif family `m`, a common pre-treatment failure receipt `E_qm`, and
`J_qm` scheduled post-exposure opportunity tasks. The exposure is generated live
by the same frozen checkpoint/scaffold under a common untreated prefix at a
preregistered seed, verified before arm mapping, and then cloned. It contains
legitimate observable history from the subject's own earlier failed run, not an
oracle motif id or evaluator judgment. Each arm may process only actor-visible
fields through its declared carrier, and Base discards all prior-task
information. Scripted/foreign exposures remain engineering fixtures.

For condition `a` and registered opportunity `j`:

```
repeat_harm_q(a) =
    (1 / J_qm) * sum_j 1[same-family harmful failure or observed agent-side
                          non-engagement/branch-local runtime failure under a]
```

Every observed refusal, timeout, premature finish, budget exhaustion, invalid
action, model error, OOM/disk exhaustion, sandbox corruption, or runtime failure
confined to one branch is adverse, not missingness.
Success and different-family failures remain in the denominator. A block is
removed only when immutable, preregistered evidence proves that one exogenous
outage affected every randomized arm independently of treatment; uncertain and
branch-local cases stay adverse, and exclusions trigger worst-case attrition
sensitivity. A branch-local missing scheduled slot is adverse; a missing
generator artifact or failed common preflight invalidates the run before
assignment. The estimand is the average paired difference in `repeat_harm_q`
after aggregation within independent prototype lineages. It is explicitly the
effect **after a standardized prior failure**; it is not an end-to-end natural-
exposure estimand.

### 2.2 Secondary: end-to-end sequence policy value

Conditions are also assigned before a natural sequence begins. The denominator
is every task/opportunity scheduled by the generator, regardless of whether an
arm first fails. Report a two-part outcome: (i) first harmful-failure incidence
and (ii) recurrence conditional on the predeclared exposure opportunity, with
principal-stratum bounds only as sensitivity analysis. Do not condition the
headline on an arm-specific observed first failure.

## 3. Condition roster

All conditions use the same frozen checkpoint, structured-action scaffold,
candidate count, tools, ex-ante model-call/action/token caps, retry cap, task
order, sandbox snapshot, and seed schedule.

Within every complete model×lineage×sequence×decoding-seed block, let
`M ~ Uniform(7!)` map policy labels to fixed clone/RNG-stream ids and independently
let `O ~ Uniform(7!)` order those stream ids, so the joint receipt probability is
`1/(7!)^2`. Pre-issued seeds, support indices, and both realized permutations are
receipt-bound. The primary Fisher test conditions on realized `O` and
rerandomizes `M` over its exact conditional `7!` support. Any restriction or
dependence requires a pre-pilot amendment and replay of the exact conditional
mapping support, or the full joint design if conditioning is invalid. An absent,
non-uniform, or unverifiable assignment voids the confirmatory causal claim.

1. **Base:** no cross-task memory; zero control pressure.
2. **Retrieval:** deterministic top-k semistructured textual failure records.
3. **Reflection:** deterministic-budget written lessons re-injected as text.
4. **Retry-count:** the E-0 within-task identical-retry controller.
5. **Motif-count/EMA:** the strongest dev-selected scalar persistent hazard
   controller from last-failure bit, count, EWMA, and Beta-posterior candidates,
   using the same current-only recognizer, learning signal, clock, numeric
   precision, receipt rules, persistence scope, head, and at least Pneuma's trial
   budget. The full ledger is frozen before pilot.
6. **Pneuma-state:** the four-variable state in §4.
7. **Influence-off null:** state updates and receipts remain live, but every
   state-to-action gain is exactly zero. It is the primary H2 null.

Component clamps are causal mechanism analyses, not Base-equivalent conditions.
A token-matched shuffled-memory control and State×Retrieval arm are diagnostic
ablations if power permits; they are not needed to support H1.

Realized action/token use is an outcome and possible mediator. Primary inference
does not match or regress it away. Common caps include reflection writing,
memory/state maintenance, candidate/repair/fallback calls, input/output tokens,
tools, retries, and failed calls; truncation is deterministic. Resource/utility
frontiers and same-length shuffled-text/state-serialization diagnostics are
mandatory. Context padding is forbidden.

## 4. State and actuation

### 4.1 Four variables

State is internal to the agent system and external to the frozen language-model
weights. It is never serialized into a model prompt on the behavioural/action
path; only the equal-metered inert notice call and the separately metered
post-behaviour report call may receive it through one-way diagnostic sinks:

- `s_m`: task-boundary-decayed failure sensitivity for motif `m`.
- `c`: calibration reliability of the agent-side prospective forecast. The
  forecast itself, not `c`, is scored against outcomes.
- `t`: bounded caution homeostat updated at task/opportunity boundaries, never
  per generated token or action.
- `r_m`: reliability of the prospective risk recognizer for motif `m`. This
  replaces retrieval-dependent memory trust; the state-only arm has no hidden
  retrieval channel.

The derived expected loss is centered so neutral state gives exactly zero:

```
L_m(x) = applicability_m(x) * r_m
         * clip(w_s * s_m + w_c * max(0, 0.5 - c) + w_t * t, 0, 1)
```

`L_m` is actuation pressure, not a calibrated probability. A separate dev-frozen
`NoticeProbability` targets the pre-action generator-held fact that the current
opportunity matches the subject's exposed motif.

Every update is deterministic, capped, receipt-bound, and performed in exposure
time/task time rather than trajectory length. Constants are selected on the dev
split under the same search budget as the count/EMA controller, then frozen.
`r_m` uses a frozen dev-fitted calibration/Beta-posterior update from actor-side
environment diagnostics; no confirmatory/test-set threshold or calibration
retuning is allowed. Four variables and H3's nine labels are locked. If `r_m`
cannot pass its non-circularity and causal-activity development checks,
development stops; removing it requires a new decision-log amendment before
pilot and a synchronized three-variable/seven-label protocol change. There is
no automatic fallback.

### 4.2 Pressure, not commands

In one model call the shared scaffold requests a ranked set of structured
candidate actions with normalized scores. Each candidate already contains a
model-proposed tool and arguments. The decision head adds a bounded bias to the
candidate's fixed meta-action class and reranks:

```
chosen = argmax_k(log(model_score_k) + bounded_pressure[class(k)])
```

Pneuma cannot invent a tool call, edit arguments, or force an unavailable action;
it only reranks actions proposed by the frozen subject. Base and influence-off
run the same head with a zero vector. Candidate generation, invalid-JSON repair,
and fallback behavior are identical and metered in every arm.

## 5. Recognition, learning signal, and scoring are separate

Three modules have non-overlapping interfaces and source files:

1. **Prospective current-only recognizer (actor-side):** before action selection,
   maps only current-task and within-opportunity observables to applicability
   probabilities. It never receives a prior-task trace, exposure receipt,
   persistent store/state, task-generator motif id, counterfactual label, future
   outcome, judge label, or self-report prose.
2. **Online learning signal (actor-side):** after an action, maps immediate tool
   status, test state, and structured action history into a bounded failure
   update. It cannot import the offline evaluator.
3. **Offline outcome evaluator (arm-blind):** scores immutable traces after the
   run. It cannot import condition/state/voice modules and receives pseudonymous
   arm ids. Exact mechanical labels form the primary endpoint; semantic/judged
   motifs are secondary.

The recognizer and evaluator are validated separately. No single classifier's
output may both administer treatment and define the confirmatory outcome.

At one frozen pre-action point, every arm emits the same-schema
`NoticeReadout` for the generator-held pretreatment recurrence fact. It uses
identical current-task/within-opportunity observables plus only that arm's
legitimate carrier: none for Base, retrieved records, written reflection, retry
count, scalar hazard, or four-variable state as applicable. The shared
current-only recognizer has no persistent input, and arm-local carrier adapters
cannot create shared hidden memory. Carrier access follows each condition's
contract. Pneuma state may be serialized only into the separately metered,
behaviourally inert notice-measurement prompt; it never enters a prompt on the
candidate/action, repair, fallback, tool, update, or later-task path.
Retrieval/Reflection use only their declared carriers at the same measurement
boundary. Pneuma must beat Base, Retrieval, Reflection, Retry-count, and
Motif-count/EMA on the frozen notice endpoint; Influence-off is diagnostic, not
an H1 comparator.

Every arm uses the same frozen actor checkpoint, notice prompt scaffold/schema,
decoding settings, maximum measurement tokens, and number/timing of readout
calls. The calls are equally and separately metered. The readout is one-way,
behaviourally inert instrumentation: it cannot alter prompts, candidates,
actions, action/token budgets, updates, retries, or behavioural scoring.

For the pre-action target `y in {0,1}` and probability `p in [0,1]`, the primary
notice scalar is `NoticeScore = 1 - mean((p-y)^2)`, a bounded proper score with
higher values better. Target, decoy, and counterfactual cases are exactly
balanced inside each registered notice cell, and the score follows the equal
cell→lineage→motif hierarchy. Macro discrimination/AUROC, calibration, coverage,
and target/decoy/counterfactual specificity remain separate hard validity gates.
Calibration is design-conditional to the registered balanced opportunity
distribution, not a natural-prevalence estimate.

The primary taxonomy is restricted to motifs with observable opportunity and
outcome rules. Prose-dependent or low-agreement motifs remain descriptive. Raw
text may be processed transiently inside governed adapters, but public frames
carry only typed tokens, bounded features, and digests.

## 6. Benchmark roles

### Suite A — controlled live micro-repositories

Suite A creates software tasks that expose an agent to decisions where a known
behavioral failure can recur. It does **not** claim to inject an agent failure as
a repository bug. Each sequence has a same-subject live exposure receipt, fixed
scheduled opportunities, exact tests, exact behavior labels, decoys,
counterfactuals, and metamorphically validated surface transforms. Every
opportunity starts from an independent digest-bound task snapshot; only declared
memory/state persists. Prototype-lineage digests enter every split and registry.
Live LLM runs use the statistical design; the deterministic oracle is only an
engineering positive control.

### Suite B-offline — trajectory external validity

Raw governed Open-SWE-Traces and SWE-Gym/OpenHands trajectories are re-extracted
to validate prevalence, observability, recognizer behavior, and evaluator
agreement. The processed digest-only JSONL cannot supply enrichment or semantic
labels. Open-SWE is not presented as a live causal benchmark.

### Suite B-live — executable real repositories

A power-feasible, preregistered subset of SWE-Gym tasks supplies repository,
base-commit, issue text, and test oracles. Repositories/images are acquired into
isolated sandboxes and bound by digest. Separate repo-holdout, surface-holdout,
and motif-family analyses replace an infeasible single split that makes both repo
and motif globally atomic.

The target population is this mechanically scorable known-motif repository/
prototype subset, not natural SWE tasks generally. Standardized opportunities in
real repositories establish repository transfer, not prevalence.

Confirmatory generalization is to new surfaces and repositories for known motif
families. Zero-shot unseen-motif transfer is exploratory unless an explicit
motif generalizer is added and trained without held-out-family leakage.

## 7. Causal interventions

Only the common pre-intervention prefix, initial sandbox snapshot, task/config,
model checkpoint, sampler settings, and exogenous seed schedule are frozen. Each
branch then interacts live with its own cloned environment. Later prompts, tool
outputs, files, and state may differ because they are descendants of treatment.

The causal battery contains:

- intact Pneuma versus influence-off;
- randomized `s_m` clamp at eligible decision points;
- randomized low/high/dose clamps for monotonicity;
- update-off versus influence-off to separate learning from actuation;
- mandatory persistence-off reset after exposure but before the scheduled
  opportunity, with current task, candidates, and head fixed; until after the
  first scheduled decision, actor, updater, carrier, and head receive only a
  same-shape inert receipt handle; the immutable receipt may subsequently enter
  only the audit/report path and can never rehydrate state through an actor path;
- motif-memory permutation/scramble;
- restore/no-op operations as wiring nulls.

The deterministic pure-function subject remains an instrumentation test and is
never evidence for an LLM behavioral effect. For stochastic subjects, empirical
meta-action distributions across seeds are compared with total variation or
Jensen–Shannon distance on frozen support. Stochastic nulls require powered
equivalence margins, symmetric RNG, and sham/no-op/restore distributions; failure
to detect a difference is insufficient. Paired randomized outcomes provide the
causal effect. Token-level logits are not assumed available.

## 8. Outcomes and anti-gaming co-gates

The headline uses the fixed-denominator repeat-harm endpoint and must pass all of
these predeclared gates:

- attempt and completion rates are non-inferior;
- verified task success is non-inferior;
- total/new-family failure severity is non-inferior;
- refusal, timeout, and premature finish are included as outcomes;
- counterfactual false avoidance is non-inferior;
- immutable trace and prose-blind firewall checks pass.

Thus switching to a different error, refusing work, or exhausting the budget
cannot manufacture support. Self-report never affects a behavioral endpoint.

## 9. Hypotheses and decision regions

- **H1 recognition and behavior:** Pneuma's same-schema pre-action notice
  readout beats Base, Retrieval, Reflection, Retry-count, and Motif-count/EMA;
  Pneuma also reduces fixed-denominator repeat harm versus all five while every
  utility/anti-gaming co-gate passes. This is an intersection–union claim, not a
  comparison with the observed best baseline. Influence-off is H2-only.
- **H2 causal:** influence-off, targeted randomized clamps, and mandatory
  persistence-off reset remove or dose-dependently reduce the behavioral effect;
  equivalence-powered restore/no-op nulls stay within bounds. Component-null
  results do not imply equality to Base.
- **H3 attribution:** the same frozen actor checkpoint, invoked in a separate
  post-behaviour call with a fixed prompt/scaffold and no tools or feedback,
  predicts one of nine joint labels (four variables×two directions plus no
  attributable change). Frozen macro accuracy/recall, coverage, risk–coverage,
  conditional direction accuracy, and no-change specificity must beat uniform/
  prior and receipt-only decoder baselines with adequate support for every class.
  The call receives only the target-symmetric public packet and legitimate
  report-time state, uses a separate report budget/cost, and never feeds
  behaviour. This is trace-grounded causal attribution, not phenomenal
  introspection; deterministic and receipt-only decoders are controls, not
  self-report.
- **H4 generalization:** full H1-like decisions survive separately on the
  predeclared known-motif surface holdout and repository holdout. Passing only
  one axis is insufficient. Unseen-motif transfer is exploratory.
- **H5 discrimination:** counterfactual false avoidance and task utility are
  non-inferior, preventing an inertia explanation.

Every hypothesis has three regions: supported, practically refuted by a frozen
equivalence/SESOI interval, or inconclusive. Failure to reject zero is never
called falsification.

## 10. Inference and power

The primary opportunity indicator has weight one. Average scheduled
opportunities within each registered
sequence×surface×challenge×decoding-seed cell, weight every registered cell
equally within the highest shared authored semantic prototype/generator lineage,
weight lineages equally within motif, and weight preregistered motif strata
equally. Severity-weighted recurrence is secondary. Tasks sharing semantic
prototype code, generator function/template, or task-specific verifier ancestry
are one lineage; descendants such as literals, surfaces, challenges, and seeds
are nested. A common generic scaffold alone does not merge independently
authored semantic opportunities. Ancestry/digests freeze before pilot, and any
ambiguity receives a conservative arm-blind merge before outcomes.

A post-assignment branch-local missing slot is adverse. A proven common
exogenous outage masks that exact slot for all seven arms, after which fixed
weights renormalize identically without arm outcomes and best/worst attrition
sensitivity is reported. Missing generator/common-preflight artifacts invalidate
the run before assignment.

For each complete block, let `M ~ Uniform(7!)` map seven policy labels to fixed
clone/RNG-stream ids and independently let `O ~ Uniform(7!)` order those stream
ids for execution, so each recorded joint draw has probability `1/(7!)^2`.
Pre-issued seeds, support indices, and both realized permutations are audited in
the receipt. The primary Fisher test conditions on realized `O` and rerandomizes
`M` over its exact conditional `7!` support, which is valid because `M` and `O`
are independent. Any restriction or dependence requires a pre-pilot amendment
and replay of the exact conditional mapping support, or the full joint design if
conditioning is no longer valid. Assignment failure voids the confirmatory
causal claim.

Fisher seven-label randomization/max-T p-values test only the sharp global null.
Use exhaustive enumeration when feasible or at least 100,000 plus-one-corrected
Monte Carlo draws; each draw reruns the complete aggregation, studentization,
and max-T calculation, and seeds aggregate only after rerandomization. A whole-
vector sign flip is invalid. These p-values are design-exact up to declared Monte
Carlo error, not average-effect confidence bounds.

Population-average risk differences and simultaneous one-sided 95% intervals
use at least 10,000 motif-stratified prototype-lineage cluster-bootstrap
resamples with studentized max-T, carrying every nested cell together. Real-repo
analysis clusters at the highest shared repository plus semantic generator/
prototype ancestor. Randomization identifies the causal contrasts; bootstrap
targets population uncertainty. Nested-cell resampling, hierarchical models,
and attrition models are sensitivity analyses.

Each one-sided lineage-cluster population component receives a preregistered
p-value. Every intersection–union family p-value is the maximum component
p-value:

- `p_H1` maximizes over five notice-superiority, five repeat-harm-superiority,
  and all utility/anti-gaming non-inferiority components. Frozen notice criteria
  and the per-comparator repeat-harm rule (point estimate at least 0.05 and
  simultaneous lower bound above zero) are additional hard gates; H5 is embedded.
- `p_H2` maximizes intact-over-Influence-off, intact-over-persistence-off,
  directional randomized-clamp omnibus, monotone dose/order, and equivalence/
  wiring-null components. For each frozen-margin equivalence contrast,
  `p_TOST = max(p_lower, p_upper)`; the null family maximizes over its TOSTs.
- `p_H3` maximizes nine-class macro superiority over uniform, empirical-prior,
  and receipt-only decoder baselines, coverage non-inferiority, no-change
  specificity, and risk–coverage. All nine labels, symmetric packet integrity,
  and minimum class support are hard gates.
- Surface- and repository-holdout known-motif analyses each make a full H1-like
  decision; `p_H4` is the maximum of those two family p-values.

Apply Holm at familywise `alpha = 0.05` to all four prespecified H1–H4 slots. An
invalid, unavailable, or inconclusive family receives `p = 1` and is not dropped.
Interpret H2 only if H1 passes, H3 as why behaviour changed only if H1 and H2
pass, and H4 only if H1 passes. Secondary BH-FDR applies only to a frozen
exploratory family.

Before preregistration, deterministic simulation runs the complete estimator,
assignment, simultaneous-inference, observed-magnitude, and non-inferiority rule
under one frozen joint DGP. The declared design alternative is
`Delta_power = 0.10` for every H1 superiority component, true utility differences
are zero, and utility margins are preregistered. The sample size is the number of
independent lineages needed for at least 80% probability that the **complete H1
conjunction** passes. This is not power at the 0.05 observed SESOI. A disjoint
20–30-lineage pilot exposes only pooled/blinded nuisance quantities and may
declare infeasibility or invoke a preregistered scope rule. Motifs, transforms,
checkpoint rules, notice/evaluator criteria, hyperparameters, margins,
controller grids, `Delta_power`, and DGP freeze on dev before pilot; pilot
lineages and tuning surfaces never enter confirmation.

## 11. Compute-feasible staged matrix

Development and Suite-A pilots use the installed local Ollama runtime and two
same-family frozen coding checkpoints (Qwen2.5-Coder 1.5B and 7B quantizations),
subject to a model-card/seed audit. The local 7B model has already demonstrated
seeded byte-identical short generations; this is an engineering observation, not
an experiment result.

Stage gates:

1. deterministic fixtures and oracle/property tests;
2. one sequence × every condition × every intervention;
3. blinded pilot used only for pooled nuisance variance/feasibility after every
   constant and criterion is dev-frozen;
4. power-derived Suite-A official matrix;
5. a smaller executable Suite-B-live matrix plus full offline external-validity
   analysis;
6. optional robustness/ablation expansion only if the core result and budget
   remain intact.

No paid GPU is used until a local bundle, dry-run receipts, exact matrix, runtime
forecast, provider price, and worst-case cost are shown to the user for one
explicit approval. Paid spend is hard-capped at USD 50.

## 12. Self-report protocol

The reporter is the same frozen actor checkpoint invoked in a separate
post-behaviour call with a fixed report prompt/scaffold, no tools or feedback,
and a separately metered report budget/cost. It receives only a target-symmetric
public trace packet plus legitimate report-time state: no operation name,
target-specific field, old/new intervention receipt, assignment probability, or
target-dependent missingness. Its output cannot feed an action, update,
behavioural score, or later task.

The paired harness assigns one of eight variable×direction labels only when
action/outcome divergence is verified; otherwise the label is
`no_attributable_change`. A receipt-only decoder receives exactly the same
packet, and a deterministic template remains a system-audit control; neither is
self-report. Report nine-class macro metrics, accuracy/risk–coverage, abstention,
no-change specificity, conditional direction accuracy, unsupported-claim rate,
calibration, and behavior consistency. A matching decoder narrows the claim to
receipt decodability. Never feed prose/scores back to behavior.

## 13. Implementation-order correction

The old A→B→F→G and C→D→E graph contains cycles. The revised order is:

1. schemas, experiment authorization, privacy boundary, frozen backend/model,
   condition protocol, sandbox source, and a reproducible green baseline;
2. raw-data enrichment plus co-developed exact Suite-A fixtures, prospective
   recognizer, online signal, and independent evaluator;
3. sequence generators, explicit split regimes, leakage quarantine, and binding;
4. common trace/manifest infrastructure and live candidate-action driver;
5. deterministic retrieval, state store, four state variables, decision head,
   and all seven conditions;
6. fixed-denominator metric before the statistical causal harness;
7. live clamps, cluster inference, anti-gaming, blinded labels, and self-report;
8. pilot power, preregistration, official-run gate, analysis, and publication.

All new Python APIs use repository-standard `snake_case`. Scientific outcomes
are reported results, never software acceptance gates.

## 14. Publication constraints

**Who Verifies the Agents? — Toward Reliable Agent Development** is the primary
venue by DL-22; IAB is the secondary fallback. Verify-Agents is double-blind,
non-archival, and due 2026-08-29 AoE. It accepts 4–9 pages excluding
references and appendices and directly solicits process-level signals, robust
verifiers, reward-hacking controls, environment-grounded evaluation, calibration,
cost/latency, and long-horizon verification. Those are the paper's load-bearing
contributions after hardening. IAB's public site advertises 2026-08-29 AoE, but
its live OpenReview timestamp has appeared 24 hours earlier; the earlier platform
deadline is binding if we pivot unless organizers resolve it.

The 9-page submission uses the official NeurIPS 2026 `dblblindworkshop` mode and
`\workshoptitle{Who Verifies the Agents? Toward Reliable Agent Development}`.
The 4-page fallback is retained as a compact negative/methodological paper. IAB's
live OpenReview date discrepancy is tracked only as fallback-venue risk.

The official 2026 NeurIPS style and paper build are checksum-pinned. Anonymous
submission artifacts expose hashes and pseudonymous ids, never local usernames,
absolute paths, repository ownership, PDF author metadata, or acknowledgments.

## 15. Go/no-go for an official run

Go only when all are true:

- fixed pre-treatment exposure and fixed opportunity denominator are tested;
- actor recognizer, online updater, and offline evaluator are structurally
  separated and independently validated;
- every arm's same-schema notice readout is carrier-matched, equally metered,
  behaviourally inert, and validated without shared persistent inputs;
- motif-count/EMA, retry-count, and influence-off controls run end to end;
- cloned live post-branch environments replace transcript freezing;
- the receipt proves independent `M` and `O` draws and the Fisher harness
  conditions on order while replaying the exact conditional mapping support;
- equal-cell/lineage/motif aggregation, all four family p-value constructions,
  and the complete-H1 `Delta_power = 0.10` simulation are preregistered;
- task-success/attempt/total-failure/false-avoidance co-gates are frozen;
- persistence-off cannot rehydrate from the sealed audit receipt, and all four
  variables/nine H3 labels remain synchronized;
- every run is bound to code, config, task/sandbox digest, checkpoint digest,
  prompt/template digest, and seed;
- local dry runs pass and any paid cost has explicit approval.

Otherwise the work may produce an engineering report or exploratory pilot, but
not the stated confirmatory causal claim.
