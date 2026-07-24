# 07 — Experimental Protocol

> [!WARNING]
> **Protocol v2 supersession notice (2026-07-22).** This document is retained as
> a historical Protocol-v1 specification. **Do not implement from it.** Use
> `02-research-thesis.md` for the canonical scientific constants,
> `16-protocol-v2-hardening.md` for the hardened rationale and contracts, and
> `17-implementation-plan-v2.md` for the executable build backlog. If this file
> conflicts with those documents, Protocol v2 governs.

Status: **archived Protocol v1; non-authoritative.** This is no longer the
runnable protocol. The material below preserves the old execution procedure for
history and crosswalk purposes only. Its former sibling contracts were:
`04-benchmark-specification.md` (suites/taxonomy), `05-agent-condition-specification.md`
(six conditions), `06-internal-state-specification.md` (state variables + decision
head), `08-metrics-and-statistics.md` (metrics + statistics), `09-intervention-and-causal-validity.md`
(causal arms + two-path validity), `10-anti-gaming-specification.md` (controls),
`11-ablation-matrix.md` (ablations). Build ordering and authorization live in the
planned `12-implementation-plan.md`; any deviation is logged in `15-decision-log.md`.

Scope reminder: this is a **planning** document. It authorizes no run, no data
conversion, and no training. Every data lane referenced stays
`training_weight: 0.0` / `not_authorized` until a human signs an authorization
manifest. On-disk paths are read-only provenance references, not instructions to
write.

Notation: `ALL_CAPS` = pre-registered constant; `snake_case` = indexed quantity;
`camelCase` = named function. A **cell** is a triple $(a, q, \sigma)$ = (condition,
task-sequence, seed). All contrasts are **paired on** $(q,\sigma)$ (doc 08 §3.1).

---

## 1. Experiment inventory

Five headline experiments (E1–E5) plus the ablation battery (doc 11). Every
experiment is scored by the **prose-blind** evaluator on the immutable trace (doc
10 C-01); no experiment reads self-report to move a behavioural number. The RUF
detector, budget caps, splits, and seed set are shared infrastructure (§2), so the
five experiments are five _views_ over one instrument, not five instruments.

### 1.1 Master table

| Exp     | Hypothesis    | Purpose                                                          | Condition / arm set                                                                                                           | Suite(s)                                   | Primary metric(s)                                                                                   | Pass / fail (pre-registered)                                                                                                                                                                                                             | Feeds figure/table                                                      |
| ------- | ------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **E1**  | H1            | Main behavioural: does persistent state reduce repeated failure? | 6 conditions (doc 05): base, retrieval, reflection, pneuma, retry_count, pneuma_ablated                                       | A **and** B (both headline)                | RUF (doc 08 §1); secondaries A–F (§2)                                                               | H1 supported for baseline $a$ iff one-sided 95% bootstrap lower bound of $\overline{\mathrm{RUF}}(a)-\overline{\mathrm{RUF}}(\text{pneuma})>0$ AND $d_z\ge$ floor; composite H1 vs best baseline; retry_count must not match/beat pneuma | Fig-1 (RUF bars ± CI), Tab-1 (secondary panel)                          |
| **E2**  | H2            | Causal: is the reduction _caused by_ the state?                  | Intervention arms A0–A8 (doc 09 §1.1): control/treated/null/state-clamped/reset/mem-del/mem-scramble/influence-off/report-off | A (deterministic-oracle) + B (statistical) | ΔRUF treated−control; treated−null; dose-response slope on $s_m$                                    | H2 supported iff A1 CI excludes 0 (correct dir) AND A2 TOST-equivalent to control AND A3/A7 raise RUF toward base AND A4 dose-response slope CI excludes 0 AND $\tau^\star\ge t_{\text{int}}$                                            | Fig-2 (divergence curve + dose-response), Tab-2 (per-arm decision)      |
| **E3**  | H4            | Generalization: survives surface/repo/motif holdout?             | base vs pneuma (the H1 contrast) restricted to held-out strata                                                                | A (surface, motif) + B (repo)              | Transfer ratios D1/D2/D3 (doc 08 §2 Group D)                                                        | Transfer supported iff retention ratio CI $\approx 1$ (surface, repo) / $>0$ (motif); D3 on never-scarred motifs is strongest                                                                                                            | Fig-3 (retention ratios), Tab-3 (per-stratum RUF)                       |
| **E4**  | H3            | Introspection faithfulness of self-report                        | 4 report conditions over one pneuma run: template, unconstrained-LLM, grounded-LLM, grounded+verified (doc 02 §8.10)          | A + B (same runs as E1)                    | grounding/unsupported-claim rate, clamp-identification accuracy, calibration, behaviour-consistency | H3 supported iff grounded+verified identifies clamped variable above chance across ≥4 clamped vars AND is more faithful than unconstrained AND no less than template; self-report NEVER moves RUF                                        | Fig-4 (faithfulness by report cond), Tab-4 (clamp-ID confusion)         |
| **E5**  | H5            | Discrimination / anti-over-avoidance                             | base, reflection, pneuma on **counterfactual tasks** (doc 10 §2.1)                                                            | A (constructed counterfactual pairs)       | False-avoidance F1 (doc 08 §2 F1); task success A1                                                  | H5 supported iff FalseAvoid(pneuma) non-inferior to FalseAvoid(reflection) AND success(pneuma) not below best baseline, both at margin $\Delta_{\text{NI}}$                                                                              | Fig-5 (false-avoidance vs success scatter), Tab-5 (non-inferiority CIs) |
| **ABL** | H1/H2 defense | Isolate which part does the work; pre-empt confounds             | 6 main-body ablations ABL-01/02/06/11/18/19 (doc 11 §7); extended set in appendix                                             | A (primary), B (robustness)                | RUF paired vs intact pneuma; dose-response where relevant                                           | Each row's pre-registered direction (doc 11 cols); validity ablations (ABL-15/16/17) MUST show no RUF change (a change = leak/bug, not a finding)                                                                                        | Fig-6 (ablation ladder), Tab-6 (full matrix)                            |

### 1.2 Per-experiment detail

- **E1 — main behavioural (H1).**
    - _Inputs:_ frozen base model (≥2 sizes, §2.1); matched sequence set (§4);
      shared seed set (§2.2); enriched-`trajectory.py` detector emitting
      `motif_id` (doc 04 §5, doc 08 §1.1).
    - _Condition set:_ all six (doc 05 §2). Conditions 1–4 test H1; 5 is the E-0
      falsification guard; 6 (ablated null) is carried here so E2 reuses the same
      traces.
    - _Metrics:_ RUF (primary, doc 08 §1) + secondary groups A–F. B1/B2
      (action/token count) are confound guards, not success (doc 08 §2 Group B).
    - _Pass/fail:_ doc 08 §3.3 pre-registered primary test; secondaries
      BH-FDR-corrected (doc 08 §3.5).

- **E2 — causal (H2).**
    - _Inputs:_ E1's pneuma and pneuma_ablated traces plus the intervention arm
      roster A0–A8 (doc 09 §1.1), run through the **two-path** causal design (doc
      09 §2–3): deterministic-oracle path on Suite A, statistical path on Suite B.
    - _Arm set:_ A0 control, A1 treated, A2 neutralized-null, A3 state-clamped, A4
      state-reset, A5 memory-deleted, A6 memory-scrambled, A7 influence-disabled,
      A8 self-report-disabled.
    - _Metrics:_ paired ΔRUF (treated−control), null equivalence (TOST), dose-
      response slope on accumulated/erased $s_m$, branch-divergence onset $\tau^\star$.
    - _Pass/fail:_ doc 09 §4 per-arm decision table + §4.2 H2 falsifiers. A result
      where H1 holds but H2 fails is a **publishable negative** (doc 02 §6).

- **E3 — generalization (H4).**
    - _Inputs:_ E1 pneuma vs base traces, partitioned by the crossed repo × motif ×
      surface holdout cells (doc 04 §6). Strictest cell = held-out repo × held-out
      motif.
    - _Arm set:_ base, pneuma (the reduction whose _retention_ is measured).
    - _Metrics:_ Transfer$_x$ retention ratios D1 (surface), D2 (repo), D3 (motif),
      doc 08 §2 Group D.
    - _Pass/fail:_ ratio CI near 1 (surface/repo) / $>0$ (motif). D3 on motifs
      never grown into scars is the anti-memorization headline.

- **E4 — introspection faithfulness (H3).**
    - _Inputs:_ the same pneuma runs as E1/E2 with the four report conditions
      generated as **read-outs** over the identical trace (never a second rollout),
      plus the E2 clamp records so "which variable changed the decision" has ground
      truth.
    - _Arm set:_ template / unconstrained-LLM / grounded-LLM / grounded+verified
      (fail-closed entailment judge).
    - _Metrics:_ grounding / unsupported-claim rate (receipt-hash, doc 10 C-02),
      clamp-identification accuracy vs the E2 clamped variable, state calibration
      (E2 metric), behaviour-consistency.
    - _Pass/fail:_ doc 02 §8.10 + doc 08 §3.7 tier-5 row. Self-report quality NEVER
      feeds RUF (firewall, doc 10 §4).

- **E5 — discrimination / over-avoidance (H5).**
    - _Inputs:_ counterfactual task pairs $(\tau_{\text{punish}}, \tau_{\text{reward}})$
      (doc 10 §2.1), pre-registered and frozen before any run.
    - _Arm set:_ base, reflection, pneuma (reflection is the non-inferiority
      comparator for false-avoidance).
    - _Metrics:_ false-avoidance F1 (doc 08 §2 F1), task success A1.
    - _Pass/fail:_ non-inferiority at margin $\Delta_{\text{NI}}$ (doc 08 §3.3).
      Fails if pneuma buys RUF with inertia.

- **ABL — ablation battery (doc 11).**
    - _Inputs:_ E1 pneuma traces + the per-ablation manipulation (doc 11 §2–5).
    - _Arm set:_ main-body six (ABL-01 no-state, ABL-02 influence-off, ABL-06
      reflection-substituted, ABL-11 remove $s_m$, ABL-18 anti-gaming-removed,
      ABL-19 prompt-text-only); extended set in appendix (doc 11 §7).
    - _Metrics:_ RUF paired vs intact pneuma; dose-response where flagged.
    - _Pass/fail:_ each row's pre-registered direction (doc 11); ABL-15/16/17 are
      **validity ablations** whose expected result is "no RUF change" — a change is
      a leak to fix, not a finding (doc 11 §6).

### 1.3 Trace-sharing map (run once, analyze many)

To avoid re-rolling the model, E1 is the **generative** experiment; E2–E5 and the
ablations are largely **re-analyses or targeted extensions** of E1's immutable
traces:

| Experiment | New rollouts required?                                                                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| E1         | Yes — the full six-condition × sequence × seed grid (the expensive run).                                                                                     |
| E2         | Partial — A0/A1/A6 reuse E1 (pneuma=treated, base=control, ablated=one null); A3/A4/A5/A7/A8 need targeted clamped re-rolls under frozen inputs (doc 09 §2). |
| E3         | No new rollouts — partition E1 traces by holdout stratum.                                                                                                    |
| E4         | No new rollouts — generate 4 report read-outs over E1/E2 traces.                                                                                             |
| E5         | Yes — counterfactual task pairs are a distinct task set (3 arms only).                                                                                       |
| ABL        | Mixed — ABL-01/06 reuse E1 arms; ABL-02/11/19 need switched-feed re-rolls; ABL-15/16/17 are trace/report re-analyses.                                        |

---

## 2. Global setup procedure (run once, before any experiment)

Execute in order. Every step writes an artifact bound into the run manifest (§3.3).
No step may be skipped for an `--official` run (§7).

1. **Pin the subject model(s).** Record, per model size (≥2, doc 02 §8.1), the
   exact checkpoint SHA, tokenizer hash, quantization/serving flags, and the local
   server version. Decoding params (temperature, top-p, stop tokens, max-new-tokens)
   are fixed **identically across all arms** and recorded. The local Qwen foundation
   subject is NOT the actor (doc 05 §4).
2. **Fix the seed set.** Draw the shared decoding seed set $\{\sigma_1..\sigma_K\}$,
   $K\ge 5$ (doc 08 §3.7). The **same** seed set is used by every arm and every
   experiment; the N-sample distributional nulls (doc 09 §2) sample over exactly
   this set. Pin the **bootstrap RNG seed** separately so CIs are byte-reproducible
   (doc 08 §3.2). No re-rolling of seeds to replace an aborted cell (doc 08 §3.6).
3. **Freeze the environment lockfile.** Pin the sandbox image, dependency lockfile,
   test-runner version, OS, and container digest (doc 05 §1.2 "byte-identical
   sandbox"). Record the git `code_commit` SHA and clean-tree assertion.
4. **Freeze the benchmark.** Materialize and hash both suites: Suite A synthetic
   instances (clean seed repo SHAs + `injected-bug generator version` + per-motif
   parameterized transforms + `surface_variant_id` axis, doc 04 §2); Suite B mined
   instances (`hf_revision`, `instance_id` set, frozen N-judge motif labels, doc 04
   §3). Bind all into `hash_manifest.json` (doc 04 §6).
5. **Freeze the splits.** Run the repo-axis split (`splits.py`, 70/15/15,
   `_repo_overlap` self-check) AND the motif-axis split (the `motif_id`-in-
   `split_group` build, doc 04 §6). Pin the 7 quarantined overlapping repos to a
   single split (`validate_corpus`: `quarantine.repos == overlap set`). Cross the
   axes: reserve held-out repo × held-out motif cells for E3.
6. **Set the budget caps.** Fix — identically across all six arms — the per-task
   token ceiling, step/action cap, wall-clock cap, and retry cap (doc 05 §1.2, doc
   04 §2.7). Fix the retrieval/reflection token budgets `B_ret`, `B_ref`, top-k,
   retry threshold `N`, and the filler-control length policy on a **held-out tuning
   slice** disjoint from every test split (doc 05 §3, doc 08 §4).
7. **Pin the state-machine constants.** Record `ALPHA_S`, `LAMBDA_S`, `RHO_S`,
   `CAP_S`, `SEED_S`, `BETA_C`, `K_T`, `A_T`, `B_T`, `GAMMA_T`, `ETA_R`, `LAMBDA_R`,
   the `L` weights `W1/W2/W3`, and the decision-head thresholds
   `THETA_LOW/MED/HIGH`, `RETRY_STOP`, `DESTRUCTIVE_MOTIFS` (doc 06 §3–6). These are
   frozen; no post-hoc tuning.
8. **Freeze anti-gaming assets.** Pre-register and hash: the hidden-motif subset
   (C-03), held-out surface transforms (C-04), decoy memories (C-10), adversarially-
   misleading reflections (C-11), counterfactual task pairs + ground truth (C-09,
   §2.1), and the N-judge ensemble config with agreement threshold (C-12). Any
   learned gate component is frozen and hash-pinned (doc 10 §0 rule 4).
9. **Register the pre-registration.** Freeze this document's pass/fail criteria,
   the primary test (doc 08 §3.3), the non-inferiority margin $\Delta_{\text{NI}}$,
   the multiplicity family + BH-FDR $q=0.05$ (doc 08 §3.5), the exclusion rules
   (doc 08 §3.6), the "measurable-causal-role-or-cut" table (doc 06 §7), and the
   power targets (doc 08 §3.7). Compute the pre-run **power simulation** (E-0 /
   audit base rates: sampled-lane ~8%, open-swe ~41%) confirming $N_Q\ge 200$
   powers $d_z\ge 0.3$ at $1-\beta=0.8$. Write the prereg to an append-only,
   commit-bound record (G-12 / C-13).

---

## 3. Per-run procedure (one cell = one `(a, q, σ)`)

A single run executes one condition over one task-sequence at one seed. It is the
atomic unit the sequence procedure (§4) and intervention procedure (§5) compose.

1. **Bind provenance up front.** Open an append-only immutable trace stamped with
   `code_commit`, clean/dirty tree flag, model checkpoint SHA, full run config
   (decode params, budgets, retry cap, state constants), seed $\sigma$, split ids,
   and frozen-asset hashes (doc 10 C-13; doc 04 §6). `--official` fails closed on a
   dirty or unpublished tree.
2. **Load persistent state.** For a stateful condition, load the vector
   $(\{s_m\}, c, t, r)$ from the §2.3 store keyed by
   `(agent_condition, subject_model, seed, task_sequence_id)` (doc 06 §2.3, §5).
   Base loads nothing; retrieval/reflection load their store rows/lesson buffer.
3. **Attach the shared decision head.** The bounded head (doc 06 §6) is attached in
   **every** arm; Base and non-state arms feed it zeroed state so it emits
   `proceed` and the action space is held constant (doc 05 §1.1, doc 06 §6).
4. **Run the ReAct loop per task in the sequence.** For each task $\tau$ in $q$, in
   fixed order: present the frozen prompt (system + task + scaffold state + prior
   context), let the actor emit tool calls over the fixed tool set
   (`read_file`/`edit_file`/`run_tests`/`search`/`finish`) under the shared caps.
   At each decision point:
    - run `detectFailure` on the observable per-step record → detected motif events
      $D_n=\{(m,\delta_m,a_m)\}$ (doc 06 §2.1);
    - update state variables per the pinned laws (doc 06 §3): $s_m$ (decay+cap+real
      trigger), $c$ (EMA Brier on real target), $t$ (real-drive + attractor), $r$
      (retrieval-usefulness);
    - recompute $L$ (doc 06 §4); invoke the decision head → `(action_label,
bias_weight)` pressure over the next tool choice (never a raw command);
    - write causal-trace receipts: `event → internal_state → pressure`, each binding
      the `detectFailure` digest and the prior/next state values (doc 06 §3.1
      provenance).
5. **Log per step (typed, no raw text).** Tool call + `args_digest`, `error_class`,
   `norm_path`, `test_id`, exit status, test verdict, `same_class_recurrence`, the
   injected-token count this decision (E-0 guard), and the state/head receipts. Raw
   argument/output/patch text NEVER enters a frame (doc 04 §5.3;
   `consistency_errors` gate).
6. **Record the task oracle result.** Suite A: deterministic `test_oracle`
   (FAIL_TO_PASS flips, PASS_TO_PASS held). Suite B: our scaffold's oracle on the
   instance's tests (the trustworthy harness `report`, not `constructed_label`, doc
   04 §3.5, doc 08 A1 note).
7. **Persist state + close the trace.** Save the updated vector to the store
   (canonical JSON, sorted keys, 6-dp rounding, byte-stable, doc 06 §2.3). Seal the
   immutable trace; its digest is the binding for all downstream metrics (doc 08 §0).
8. **Truncation bookkeeping.** If a cap is hit, record the truncation reason;
   budget exhaustion is a **valid outcome**, not an abort (doc 08 §3.6 rule 2).

---

## 4. Sequence-execution procedure (a task sequence with recurring motifs)

A task sequence is the **unit of persistence** and the **bootstrap resampling atom**
(doc 08 §0, §3.2). This procedure administers one sequence within one persistent-
state session and does the exposure bookkeeping RUF requires.

1. **Assemble the sequence.** For each target motif $m$, place instances at ordered
   positions $p_1<p_2<\dots<p_k$ (doc 04 §2.4). Suite A: the same parameterized
   `injected_bug_patch` transform on _different_ clean repo templates with a
   _different_ `surface_variant_id` at each recurrence. Suite B: distinct real
   instances sharing a mined `motif_id` (rule + N-judge agreement), different
   repos/files/languages (doc 04 §3.4 mode 2). Interleave distractor motifs between
   recurrences so no "just did this" adjacency shortcut exists.
2. **Fix and counterbalance order.** The task order is randomized **once** and
   reused **identically across every arm and seed** (doc 05 §1.2; doc 09 §1.2). The
   motif↔surface assignment is counterbalanced so no arm sees a privileged surface
   variant.
3. **Run the session.** Execute §3 per task in order, carrying the persistent state
   task→task within the sequence (this is where longitudinal persistence lives, doc
   06 §5). `reset()` is NOT called between tasks of a sequence; it is called only
   between paired arms of one intervention (doc 06 §5).
4. **Exposure / post-exposure bookkeeping (RUF).** Walking instances of each motif
   $m$ in order: mark the earliest instance with a detected failure as the
   **first-exposure** $i^\star_m$; every later $m$-instance ($i>i^\star_m$) is
   **post-exposure** and enters the RUF denominator; all instances up to and
   including $i^\star_m$, and every motif the agent never failed, are **excluded**
   (doc 08 §1.2). The numerator is post-exposure instances where the same
   `motif_id` recurred (doc 08 §1.3).
5. **Emit per-sequence scalars.** Compute per-sequence RUF (doc 08 §1.3) and the
   per-sequence aggregate of every secondary metric; these are the atoms §6
   resamples.
6. **Repeat across seeds and conditions.** Run the identical sequence under every
   $\sigma$ and every condition $a$, forming the matched cells $(a,q,\sigma)$ that
   the paired contrast requires (doc 08 §3.1).

---

## 5. Intervention-execution procedure (control / treated / null / clamp arms)

This procedure realizes E2 (H2) and the clamp-based ablations. It runs the two-path
causal design of doc 09: the **deterministic-oracle path** on Suite A (reuses
`PairedReplayRunner` verbatim) and the **statistical path** on Suite B (frozen
inputs + N-sample distributional nulls).

1. **Select the path.** Suite A synthetic deterministic-oracle sub-experiments →
   deterministic path (byte-equality null is _satisfiable_, doc 09 §3). Suite B
   real stochastic agent → statistical path (byte-equality would cap at Level 3,
   doc 09 §2.1).
2. **Apply the four freezes (statistical path).** Per tick, snapshot and digest-
   bind: (i) the model seed set $\{\sigma_k\}$ + deterministic-kernel flags; (ii)
   the exact realized prompt string; (iii) the exact retrieved-memory set and its
   order; (iv) the recorded tool/env transcript (tool outputs, filesystem deltas,
   test verdicts keyed by `(task,tick,action)`) (doc 09 §2.2). These make
   control/treated/null share an identical decode path **up to the intervention
   point**.
3. **Run each arm under counterbalanced order.** Execute every arm under the three
   counterbalanced orders `(control,treated,null)`, `(treated,null,control)`,
   `(null,control,treated)` (doc 09 §1.2; `provenance._COUNTERBALANCED_ORDERS`); the
   per-arm digest (deterministic) or per-arm distribution (statistical) must be
   order-invariant.
4. **Execute the arm roster (doc 09 §1.1).** A0 control (`schedule=None`); A1
   treated (full resolved schedule); A2 neutralized-null (`restore`); A3 state-
   clamped (`clamp` $s_m$/$t$/$c$ on `scar_graph`/`affect_manifold`/`self_model`);
   A4 state-reset (`clamp`→seed); A5 memory-deleted (`ablate`/`disable`); A6 memory-
   scrambled (`noise`); A7 influence-disabled (`disable` the `state→L` head edge);
   A8 self-report-disabled (`disable` report head). `reset()` restores each arm's
   seeded vector so arms start identical and never leak state (doc 06 §5).
5. **Capture branch divergence (statistical path).** Record **divergence onset**
   $\tau^\star$ (first tick treated and control action distributions differ beyond
   band) and the **divergence magnitude** curve (KL / total-variation / bounded
   edit-distance over the K seeds), plus the **null divergence floor** (control-vs-
   null must stay in-band every tick) (doc 09 §2). A treated run whose $\tau^\star <
   t_{\text{intervention}}$ indicates freeze leakage and is **rejected before
   scoring** (off-target-null-drift block).
6. **Score the causal contrast.** Deterministic path: exact scalar ΔRUF, null byte-
   reproduces control. Statistical path: paired bootstrap of `RUF(treated) −
RUF(control)` (CI excludes 0, correct direction) + TOST equivalence
   `RUF(null) − RUF(control) ∈ ±band` + dose-response regression of ΔRUF on
   clamped/erased $s_m$ (doc 09 §2). An arm **passes** only if treated is
   admissible AND null holds AND $\tau^\star\ge t_{\text{intervention}}$ (doc 09
   §4.1).
7. **Corroborate across paths.** The oracle path is the **positive control for the
   instrument** (its known delta must be recovered by the same statistical estimator
   at large $K$); agreement → effect real and correctly measured; disagreement →
   either freeze leak (oracle passes, agent shows pre-clamp $\tau^\star$) or genuine
   stochastic-only effect (oracle exact, agent CI includes 0) (doc 09 §3).

---

## 6. Analysis pipeline (raw traces → figures)

Deterministic, re-runnable from committed traces + pinned bootstrap seed. Order is
fixed; no step may read a result and re-specify an earlier step (doc 08 §9 intent).

1. **Integrity filter.** Reject any trace failing the commit+config+seed integrity
   check; apply the pre-registered abort/exclusion rule with **listwise deletion on
   the pairing key** $(q,\sigma)$ (doc 08 §3.6). Budget exhaustion is retained.
   Report per-condition attrition; if listwise deletion removes $>10\%$ of pairs,
   run the pre-registered complete-case + worst-case-imputation sensitivity analysis.
2. **Metric computation (prose-blind).** From typed receipts only: RUF numerator/
   denominator per motif with post-exposure exclusion (doc 08 §1); secondary groups
   A–F (doc 08 §2). All aggregated to **per-sequence** scalars.
3. **Pairing.** Form per-sequence differences $\delta_{q,\sigma}=M_a-M_b$ on matched
   $(q,\sigma)$; never compare unpaired means (doc 08 §3.1).
4. **Paired bootstrap.** Seed-stratified resampling of whole **sequences** (not
   instances) with replacement, $B=10000$, BCa 95% two-sided (percentile as
   robustness cross-check), pinned bootstrap seed (doc 08 §3.2).
5. **Pre-registered primary test (H1).** One-sided paired test of
   $\Delta_{ab}>0$ per baseline $a$; supported iff one-sided 95% lower bound $>0$;
   Wilcoxon signed-rank as distributional cross-check; composite H1 vs the strongest
   baseline; retry_count falsifier check (doc 08 §3.3).
6. **E-0 confound defenses.** Report B1/B2 per arm; if the pneuma arm's mean action/
   token count exceeds the best baseline beyond tolerance, **demote** the raw
   contrast to (a) the token/action-matched subsample analysis (coarsened exact
   matching on B1/B2 deciles) and (b) the covariate-adjusted mixed-effects logistic
   model with $u_q,u_\sigma,u_m$ random intercepts (doc 08 §4). No sign-flipping.
7. **Multiplicity-corrected secondaries.** BH-FDR at $q=0.05$ over the secondary
   family (groups A–E + F1); Holm-adjusted appendix cross-check; primary RUF and the
   H2/H3/H4/H5 primary contrasts are individually pre-registered and NOT in the
   corrected family (doc 08 §3.5).
8. **Effect sizes (mandatory).** Every contrast carries absolute $\bar\Delta$ + 95%
   CI, Cohen's $d_z$, and — for causal — treated-vs-null $d_z$ + dose-response
   slope; for transfer, the retention ratio + CI. A detectable-but-negligible RUF
   reduction is reported as "detected but small" and does NOT support the tier (doc
   08 §3.4, §3.7).
9. **Causal + generalization + introspection + discrimination.** Run §5's causal
   scoring (E2), the Group-D retention ratios (E3), the report-faithfulness track
   (E4, receipt-hash grounding + clamp-ID accuracy, never prose plausibility), and
   the non-inferiority tests (E5) (doc 08 §2–3).
10. **Figures/tables.** Emit Fig-1..6 / Tab-1..6 (§1.1) deterministically from the
    scored artifacts. Robustness of tier 2 requires replication on ≥2 model sizes
    (doc 08 §3.7); a single-model RUF reduction is not a headline claim.

---

## 7. Reproducibility + official-run gate (fail-closed record of claim)

No number enters the paper unless it is a **record of claim**: recomputable from a
committed immutable trace under the frozen prereg. The gate is fail-closed.

1. **Pre-run gate.** `--official` refuses to start on a dirty or unpublished tree,
   an unregistered prereg, unfrozen anti-gaming assets, or any state constant not
   pinned (§2). Commit-provenance is built (G-12 / C-13); checkpoint/config/seed
   binding into the same record is a scheduled build.
2. **Per-claim binding.** Every reported statistic carries the digest of the
   trace(s) it was computed from; a number with no matching immutable trace is
   rejected (doc 10 C-13). The evaluator recomputes pass/fail from raw outputs and
   never trusts a supplied summary (`_score_paired` recompute; caller-fabricated
   passes raise `TypeError`) (doc 10 C-14).
3. **Firewall assertion.** Re-run the one-way scorer→voice firewall checks
   (`test_voice_never_alters_the_evidence_frame`,
   `test_skin_cannot_inflate_the_level`,
   `test_judge_and_skin_cannot_inflate_level`) so no prose→score path exists (doc 10
   §4). ABL-16/ABL-15/ABL-17 must show no RUF change (validity confirmations).
4. **Determinism replay.** Re-derive every figure from committed traces + the pinned
   bootstrap seed; byte-identical figures are required. Synthetic (Suite A)
   deterministic-oracle sub-experiments additionally byte-reproduce under the
   `PairedReplayRunner` (doc 09 §3).
5. **Negative-result handling.** A pre-registered H1-holds-but-H2-fails outcome, or
   any falsified hypothesis, is recorded and reported as a **first-class negative**
   (doc 02 §6; doc 09 §4.2), never discarded or re-specified.

---

## 8. Dependency-ordered readiness checklist (what must exist before each experiment)

Conceptual cross-reference to the implementation workstreams (`12-implementation-plan.md`).
Each experiment is **blocked** until its prerequisites (all rows above it plus its
own) are `implemented + integration-tested`. Ordering follows the three load-bearing
builds the audit identifies (doc 01 §3): real failure detector, state→action
decision head, real-data outcome experiment.

| Order | Prerequisite (build)                                                                                                                                      | Source spec                    | Unblocks                     |
| ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ | ---------------------------- |
| P-0   | Live ReAct driver OUTSIDE `replay/` (seed-pinnable, 5-tool loop, shared decision head with switchable feed)                                               | doc 05 §1; doc 02 §8.1         | all experiments              |
| P-1   | Enriched `trajectory.py`: `error_class`, `norm_path`, `test_id`, `same_class_recurrence` (+ privacy invariant)                                            | doc 04 §5                      | detector, RUF, all           |
| P-2   | `error_class` precision/recall validated vs sampled-lane 5-flag `report`                                                                                  | doc 04 §5.2                    | RUF trustworthiness          |
| P-3   | `detectFailure` component (motif id + strength $\delta_m$ + similarity $a_m$, deterministic)                                                              | doc 06 §2.1                    | Pneuma-state, E1/E2          |
| P-4   | Four state variables + decay/cap + EMA + new `r` + `memory_trust` seam + `L` + decision head, cross-run store                                             | doc 06 §2–6                    | pneuma condition, E2, ABL    |
| P-5   | Six conditions on the shared substrate incl. embedding retrieval + real Reflexion loop + tuned retry `N`                                                  | doc 05 §2–3                    | E1                           |
| P-6   | Synthetic injector (parameterized per-motif transforms + surface-variant axis) + deterministic oracle                                                     | doc 04 §2, §8                  | Suite A, E1/E2/E3/E5         |
| P-7   | Motif miner + N-judge labeling over Open-SWE / Sampled traces                                                                                             | doc 04 §3.5, §8                | Suite B, E1/E3               |
| P-8   | Motif-axis split (`motif_id` in `split_group`) crossed with repo-axis + 7-repo quarantine                                                                 | doc 04 §6                      | E3 (H4), C-03/C-15           |
| P-9   | Statistical causal path: four freezes + N-sample nulls + branch-divergence metric + pluggable extractors                                                  | doc 09 §2                      | E2 on real agent, ABL clamps |
| P-10  | Reproducibility binding extended to checkpoint SHA + seed + injector version + frozen judge labels; `--official` fail-closed                              | doc 04 §6; doc 10 C-13         | official runs, §7            |
| P-11  | Anti-gaming assets: hidden motifs, surface transforms, decoy memories, misleading reflections, counterfactual tasks, evaluator blinding, N-judge ensemble | doc 10 §2–3                    | E5 (H5), ABL-18, E1 controls |
| P-12  | Report-faithfulness track: 4 report conditions + fail-closed entailment judge + receipt-hash grounding                                                    | doc 02 §8.10; doc 10 C-02/C-06 | E4 (H3)                      |
| P-13  | Power simulation confirming $N_Q\ge200$ / $\ge8$ motifs / $\ge5$ seeds powers $d_z\ge0.3$; prereg registered                                              | doc 08 §3.7; §2 step 9         | green-light any official run |

Readiness rule: **E1** needs P-0..P-8 + P-10 + P-11(controls) + P-13; **E2** adds
P-9; **E3** adds P-8 (motif+repo holdout) already met; **E4** adds P-12; **E5** adds
P-11(counterfactuals); the **ablation battery** needs P-4 + P-9 for the clamp rows
and P-11 for ABL-18. All lanes remain `training_weight: 0.0` / `not_authorized`;
this checklist authorizes nothing until a human signs the manifest (doc 02 §8.5).
