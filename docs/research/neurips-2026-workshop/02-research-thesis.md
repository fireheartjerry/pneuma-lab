# 02 — Research Thesis and Locked Design Constants

Status: canonical. Every other document in this package MUST stay consistent with
Section 8 (Locked Design Constants). If a downstream document needs to deviate,
it records the deviation in `15-decision-log.md` and updates this file.

Scope reminder: this is a **planning** document. Nothing here authorizes
implementation, training, experiments, or data conversion. It fixes _what_ the
first paper claims and _how_ the claim is structured so the implementation plan
(`12-implementation-plan.md`) is unambiguous.

---

## 1. One-sentence description

We test whether giving a software-engineering agent a **persistent, causally
active internal state** helps it notice its own recurring failure patterns,
avoid repeating them, and accurately explain why its behaviour changed —
measured against no-memory, retrieved-memory, and written-reflection agents that
are identical in every other respect.

## 2. Plain-English research question (anchor — do not drift)

> Does giving a software agent a persistent internal state help it notice its own
> recurring failure patterns, avoid repeating them, and accurately explain why
> its behaviour changed?

The whole program collapses to a controlled comparison plus a causal test. It is
NOT a consciousness demonstration. Machine-interiority language (scars, affect,
instinct, self-model, workspace) is retained only as **operational** vocabulary
for named state variables, never as a phenomenal claim.

## 3. Primary hypothesis

**H1 (behavioural).** Under matched base model, tools, budgets, retry limits, and
task ordering, an agent whose decisions are gated by a persistent, causally
active internal state (the _Pneuma-state_ condition) commits fewer **repeated
structurally-similar failures** across a task sequence than agents using (a) no
cross-task memory, (b) retrieved textual memory, or (c) written reflection.

Formally, let `RUF` be the repeated-underlying-failure rate (defined in
`08-metrics-and-statistics.md`). H1 predicts
`RUF(pneuma) < min(RUF(base), RUF(retrieval), RUF(reflection))`
with a non-overlapping bootstrap confidence interval on the paired difference.

## 4. Supporting hypotheses

- **H2 (causal).** The RUF reduction is _caused by the internal state_, not by
  incidental extra context or tokens. Ablating or clamping the state variable
  that carries failure memory removes the reduction: `RUF(pneuma_ablated) ≈
RUF(base)` and the treated-minus-null contrast is significant while the null
  arm reproduces control. Effect size scales monotonically with accumulated scar
  strength.
- **H3 (introspection faithfulness).** The agent's grounded self-report of _which_
  internal variable changed its decision is accurate: when we clamp variable `v`,
  the self-report's identified cause tracks `v` above chance, and a
  grounded+verified report is more faithful than an unconstrained-LLM report and
  no less faithful than a deterministic template report.
- **H4 (generalization).** The reduction survives (i) surface-varied instances of
  the same failure motif and (ii) held-out repositories and held-out motifs —
  i.e. it is not identifier memorization.
- **H5 (discrimination / anti-over-avoidance).** The Pneuma-state agent does not
  buy failure reduction purely by becoming inert: on **counterfactual tasks**
  where a previously-punished strategy is now correct, its false-avoidance rate is
  not worse than the reflection baseline, and its overall task-success rate is not
  below the best memory/reflection baseline.

## 5. Claim tiers (label every sentence in the paper with one)

1. **Engineering claim** — the system builds and runs end-to-end (four conditions,
   one benchmark, one causal harness). Evidence: reproducible run artifacts.
2. **Behavioural claim** — H1: persistent state reduces repeated failures.
   Evidence: matched-condition RUF contrast with CIs.
3. **Causal claim** — H2: the state _causes_ the reduction. Evidence:
   clamp/ablation removes it; null holds; dose-response on scar strength.
4. **Generalization claim** — H4: transfers across surface/repo/motif holdout.
5. **Introspection-faithfulness claim** — H3: self-report identifies the true
   causal variable; grounded+verified beats unconstrained.
6. **Phenomenal-consciousness claim** — **NOT MADE.** Explicitly disclaimed in the
   paper's scope statement and limitations.

The paper's contribution is tiers 1–3 as the core, 4–5 as strengthening, with a
clean firewall to tier 6.

## 6. Falsification conditions (pre-registered)

- **H1 false** if `RUF(pneuma) ≥ RUF(best baseline)` with overlapping 95% CIs on
  the paired difference at matched budget. A retry-count heuristic controller (see
  §8) is included precisely so a trivial baseline can falsify us — motivated by the
  in-repo E-0 negative result where psyche signals lost to retry-count at failure
  prediction (AUROC 0.34 vs 0.71).
- **H2 false** if ablating/clamping the failure-memory variable leaves
  `RUF(pneuma_ablated) ≈ RUF(pneuma)` (state was epiphenomenal), OR if the null
  arm fails to reproduce control (the harness cannot support a causal claim).
- **H3 false** if grounded self-report identifies the clamped variable at ≤ chance,
  or if unconstrained-LLM reports are equally faithful (grounding buys nothing).
- **H4 false** if the effect vanishes under surface variation or on held-out
  repos/motifs (memorization, not generalization).
- **H5 false** if the Pneuma-state agent's success drop or false-avoidance rate is
  worse than baselines (reduction bought by inertia).

A result where H1 holds but H2 fails is still publishable as a _negative causal
result_ ("internal state correlates with but does not cause the reduction") — the
program's stated ethic (see `docs/research/10-anti-fake-progress.md`) treats
recorded negatives as first-class.

## 7. Why this is novel (see `03-related-work-positioning.md` for citations)

Four differentiators, none of which any single prior system combines:

1. **Persistent, structured, causally-active state** (not re-injected text). Memory
   agents (MemGPT, Generative Agents, A-MEM) and reflection agents (Reflexion,
   ExpeL, SWE-Exp) store natural-language notes that are re-read as context. We
   carry numeric state that _gates the action_ and can be clamped.
2. **Clamp/ablation causal proof** (control/treated/null). Prior memory/reflection
   work reports only end-task success (Pass@1); none intervenes on its own memory
   to prove causation. SWE-Exp — the closest neighbor — reports Pass@1 = 73.0% and
   never measures repeated-failure reduction.
3. **Behaviour-vs-self-report firewall.** In reflection agents the prose is
   simultaneously the mechanism and the explanation; there is no way to tell a real
   behaviour change from a persuasive diary entry. We score behaviour with a
   prose-blind evaluator and test self-report faithfulness separately.
4. **A repeated-structural-failure metric.** SWE benchmarks score memoryless
   per-task resolve rate; single-trajectory failure taxonomies (Failure-as-a-
   Process, TraceProbe) never look _across_ tasks. RUF is a cross-task metric.

Anticipated reviewer objection — "isn't this just Reflexion / just retrieval?" —
is answered structurally: Reflexion and retrieval are _included as baselines under
identical budget_, and the causal clamp isolates the contribution of structured
state over text.

---

## 8. LOCKED DESIGN CONSTANTS

These are the decisions every downstream document inherits. Alternatives and
rationale are in `15-decision-log.md` (referenced as DL-xx).

### 8.1 Subject model and agent scaffold (DL-01, DL-02)

- **Base model:** a single, frozen, open-weight, coding-capable instruct model,
  served **locally** with controllable temperature and seed so all conditions
  share identical decoding and we can draw N independent samples per task for
  distributional causal nulls. The model is a fixed external artifact; **the local
  Qwen foundation subject is NOT on the critical path** (its only real result is a
  saturation plateau vs untrained baselines — see `01-current-state-audit.md`).
  The exact checkpoint is pinned in the run config; the design is model-agnostic
  and must be reproduced on ≥2 model sizes for the robustness section (H1 must not
  be a single-model artifact).
- **Scaffold:** a minimal, deterministic, seed-pinnable ReAct-style tool loop
  (`read_file`, `edit_file`, `run_tests`, `search`, `finish`) built as a new
  `live driver` OUTSIDE `src/pneuma_lab/replay/` (the replay harness is for frozen
  trajectories and cannot drive a live stochastic agent — confirmed in the replay
  and interventions audits). All four conditions share this exact scaffold; only
  the memory/state module differs.

### 8.2 Conditions (DL-03) — see `05-agent-condition-specification.md`

Core four (identical base model, tools, budget, retry cap, task order, env):

1. **Base** — no cross-task state; fresh context per task.
2. **Retrieval-memory** — stores prior failure records as text; retrieves top-k by
   similarity. Backed by the existing `foundation/memory.py` SQLite/FTS5 store.
3. **Reflection** — writes a natural-language lesson after failure; lessons are
   injected on later tasks (Reflexion/ExpeL-style).
4. **Pneuma-state** — persistent numeric internal state (the four variables in
   §8.3) that gates the agent's action via a bounded decision head.

Mandatory extra baselines/arms:

5. **Retry-count heuristic controller** — a trivial non-learned controller that
   deepens verification after N identical retries. Falsification guard against
   E-0-style confounds.
6. **Pneuma-state-ablated (null)** — Pneuma-state present but its failure-memory
   variable clamped to baseline; the causal control for H2.

Optional (architecture-only, reported as ablation not headline): **recurrent
hidden-state** arm using the `foundation` bounded recurrent junction — included
only if it can be run under the same budget; otherwise cited as future work.

### 8.3 Internal-state variables (DL-04) — see `06-internal-state-specification.md`

Exactly four causally-active persistent variables plus one derived scalar. Chosen
by empirical necessity from the existing psyche (each already has a tested clamp
seam):

1. **Failure-sensitivity `s_m` per motif** (scar-tissue memory). Grown from a
   _real_ failure detector (new — the current scar match is fixture-fed), with
   **decay and cap** (both absent today). Primary variable for H1/H2.
2. **Confidence `c`** (self-model reliability / calibration error). Brier-calibrated
   self-estimate of own error rate.
3. **Caution `t`** (affect tension axis). Recurrent; rises with errors/scars; gates
   verification depth.
4. **Memory-trust `r`** — a NEW dedicated scalar weighting how much retrieved
   memory influences the decision (the current `identity_anchors` proxy is
   memory-fed, not a trust weight). Enables an honest contrast with the retrieval
   baseline.
5. **Derived: expected-loss `L = clip(w1·s_m + w2·c' + w3·t)`** — the single scalar
   the decision head consumes.

Every variable must have a measurable causal role or be cut. Each ships with a
clamp hook (all four map to existing `PerturbationSet` seams: `scar_graph`,
`self_model`, `affect_manifold`, and a new `memory_trust` dimension).

### 8.4 State→behaviour coupling (DL-05)

A bounded **decision head** maps state → one of a fixed action-shaping set:
`{proceed, deepen_verification, run_tests_before_edit, switch_strategy,
re_read_repo_structure, escalate_or_ask, stop_and_report}`. The head emits a
_pressure/bias_ over the scaffold's next action, never a raw shell command
(preserving the repo invariant "Pneuma emits pressure, not commands"). The mapping
is deterministic given state; its effect is logged in a causal trace and can be
neutralized (H2). The same head is attached (with its state feed zeroed) to the
Base condition to hold the action-space constant across arms.

### 8.5 Benchmark (DL-06) — see `04-benchmark-specification.md`

- **Synthetic controlled-motif suite:** inject known bug motifs into clean repos
  drawn from SWE-Gym-Raw / SWE-bench-Lite task specs (clean oracle → exact motif
  ground truth, exact repeat structure, controlled surface variation).
- **Real-repo suite:** Open-SWE-Traces (primary; 207k step-level trajectories,
  ~41% resolved, 2 models × 2 harnesses per task → natural recurring-failure
  distribution) + SWE-Gym OpenHands-Sampled (complement; dense failures). Both have
  existing adapters.
- **Splits:** by repository AND by motif (motif-axis splitting does NOT exist today
  — it is a build). The 7 repos overlapping between Open-SWE-Traces and SWE-Gym are
  quarantined per the leakage registry.
- All lanes remain `training_weight: 0.0` / `not_authorized`; the paper does no
  weight training of the subject model.

### 8.6 Failure taxonomy (DL-07) — see `04-benchmark-specification.md`

~12 motifs with observable indicators (wrong-file edit, local-fix-breaks-global-
invariant, retry-broken-strategy, ignore-failing-tests, stale-assumption,
overwrite-user-change, premature-destructive-action, single-error-overfit,
skip-verification, misread-repo-structure, unavailable-tool-loop, claim-success-
without-evidence). Indicators are derived from an **enriched** `trajectory.py`
extraction (today only 3 crude proxies exist and argument/output digesting
destroys error-class identity — enrichment is a foundational task).

### 8.7 Primary and secondary metrics (DL-08) — see `08-metrics-and-statistics.md`

- **Primary:** repeated-underlying-failure rate `RUF` — fraction of
  post-exposure motif instances on which the same underlying failure recurs.
- **Secondary (full list in doc 08):** task success, first-attempt success,
  recovery success, action count, token count, unnecessary retries, constraint
  violations, destructive-action rate, verification completion, false-avoidance,
  transfer (surface/repo/motif), memory-retrieval precision, state calibration,
  intervention effect size, cross-seed stability.
- All contrasts are **paired** (same task, same seed set), reported with
  bootstrap 95% CIs and a pre-registered primary test; multiple secondary metrics
  get multiplicity correction.

### 8.8 Causal validity (DL-09) — see `09-intervention-and-causal-validity.md`

The existing clone-equivalence gate is `sha256(outputs_A) == sha256(outputs_B)` —
it admits only deterministic subjects and **caps a real stochastic agent at Level
3**. The paper needs a parallel **statistical causal path**: frozen model seeds,
frozen prompts and frozen retrieved memory, recorded tool/environment transcripts,
a branch-divergence metric, and **N-sample distributional nulls with bootstrap
effect sizes** replacing byte-equality. The deterministic paired runner is reused
verbatim for the synthetic deterministic-oracle sub-experiments.

### 8.9 Anti-gaming (DL-10) — see `10-anti-gaming-specification.md`

Behaviour is scored by a **prose-blind** evaluator (reuse the audited one-way
scorer→voice firewall). Controls: hidden motifs, held-out surface transforms,
false-avoidance penalty, decoy memories, adversarially-misleading reflections,
counterfactual tasks (old strategy becomes correct), an N-judge ensemble for
motif labels, and immutable execution traces bound to commit+config+seed.

### 8.10 Self-report / voice (DL-11)

Secondary. Four report conditions over the same run: deterministic template,
unconstrained-LLM, grounded-LLM, grounded+verified (fail-closed entailment judge).
Self-report quality NEVER feeds the behavioural score. Metrics: grounding /
unsupported-claim rate, calibration, intervention-sensitivity, behaviour
consistency.

### 8.11 Target venue (DL-12)

Primary: **IAB — Interpreting Agent Behavior @ NeurIPS 2026** (9pp long / 4pp short

- refs, non-archival, trajectory-representation special track + empirical error-
  taxonomy track; deadline **2026-08-29**). Secondary: **Who Verifies the Agents?**
  (same deadline). NeurIPS 2026 is Sydney, Dec 6–12 (workshops Dec 11–12).

---

## 9. System coherence (how the pieces connect)

```
                      one frozen base model + one seed-pinnable scaffold
                                         │
        ┌───────────────┬───────────────┼───────────────┬────────────────┐
      Base          Retrieval        Reflection      Pneuma-state      Retry-count
   (no state)     (memory.py)       (Reflexion)   (4 vars→dec.head)   (heuristic)
        └───────────────┴───────────────┴───────────────┴────────────────┘
                                         │ acts on
                        Benchmark: synthetic motifs + real repos
                        (motif ground truth, surface variation, holdout)
                                         │ produces
                       immutable execution traces (commit+config+seed)
                                         │ scored by
        prose-blind behavioural evaluator ──► RUF + secondary metrics (paired, CIs)
                                         │ and causally tested by
     statistical paired runner: control / treated(clamp) / null (N-sample nulls)
                                         │ and separately
        self-report faithfulness eval (4 report conditions, never feeds score)
```

Every claim in §5 maps to a block: behavioural→evaluator, causal→paired runner,
introspection→self-report eval, generalization→holdout splits, engineering→traces.
The implementation plan builds them bottom-up in dependency order.
