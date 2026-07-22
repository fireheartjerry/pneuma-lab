# 08 — Metrics and Statistics

> [!WARNING]
> **Protocol v2 supersession notice (2026-07-22).** This document is retained as
> a historical Protocol-v1 specification. **Do not implement from it.** Use
> `02-research-thesis.md` for the canonical scientific constants,
> `16-protocol-v2-hardening.md` for the hardened rationale and contracts, and
> `17-implementation-plan-v2.md` for the executable build backlog. If this file
> conflicts with those documents, Protocol v2 governs.

Status: **archived Protocol v1; non-authoritative.** The formulas below preserve
the old metric/statistics design and may conflict with Protocol v2. They are not
the preregistered analysis contract.

Scope reminder: this is a **planning** document. It authorizes no run, no data
conversion, and no training. It fixes _how_ we will measure and _how_ we will
decide, so the experiment cannot be re-specified after seeing results.

Notation conventions (global): `ALL_CAPS` for pre-registered constants, `snake_case`
for indexed quantities, `camelCase` for named functions. All rates are in
$[0,1]$; "direction" states whether the Pneuma-state condition is predicted to
score **lower** (↓ better) or **higher** (↑ better) than baselines.

---

## 0. Objects the metrics range over

Fix the vocabulary once so every metric denominator is unambiguous.

- **Condition** $a \in \mathcal{A}$ — one of the six arms of §8.2: `base`,
  `retrieval`, `reflection`, `pneuma`, `retry_count`, `pneuma_ablated` (the null).
- **Task-sequence** $q \in \mathcal{Q}$ — an ordered list of tasks presented to one
  agent instance in one persistence episode. The sequence is the unit of
  persistence and, per §3 below, **the bootstrap resampling unit**. Sequences are
  matched across conditions: the same $q$ (same tasks, same order) is run under
  every $a$.
- **Seed** $\sigma \in \mathcal{S}$ — a decoding seed (temperature + RNG) fixed at
  the scaffold. A cell is the triple $(a, q, \sigma)$. Pairing is always on
  $(q, \sigma)$: contrasts compare two conditions at the identical task and seed.
- **Motif** $m \in \mathcal{M}$ — one of the ~12 failure motifs of §8.6. A motif has
  an observable detector emitting a **motif id** per step (see §1.1).
- **Instance** — an occurrence within a sequence where the agent attempts a subtask
  at which motif $m$ is _applicable_ (the bug/opportunity for motif $m$ is present).
  Instances are the unit of the primary metric.

Every metric below is computed **only from the immutable execution trace** (commit +
config + seed bound, §8.9) by the **prose-blind** evaluator (§8.9). No metric reads
agent self-report; self-report faithfulness is a separate family (§2, group F).

---

## 1. PRIMARY metric — Repeated-Underlying-Failure rate (RUF)

RUF answers the anchor question directly: _given that the agent has already failed a
motif once, how often does the same underlying failure recur?_ It is a
**conditional** rate — conditioned on prior exposure — which is what isolates
"learning from one's own mistakes" from raw task difficulty.

### 1.1 Detector, motif id, and "same underlying failure"

The detector is the enriched `trajectory.py` per-step failure classifier
(§8.6; a foundational build — today only 3 crude proxies exist). For each step it
emits, when a failure is present, a structured **failure key**

$$
k = (\texttt{motif\_id},\ \texttt{error\_class},\ \texttt{locus})
$$

where `motif_id` $\in \mathcal{M}$ is the taxonomy label, `error_class` is the typed
failure family (test-fail / build-fail / apply-fail / timeout / traceback-class),
and `locus` is a coarse structural target (touched path bucket, failing-test id
bucket). **"Same underlying failure" is defined by `motif_id` equality only** — two
failures are the same iff the detector assigns the same `motif_id`. It is explicitly
**NOT** surface equality: differing commands, differing byte-level args, differing
error strings, or non-adjacent recurrence all still count as the same underlying
failure if `motif_id` matches. `error_class` and `locus` are recorded for
diagnostics and for the transfer metrics (§2, group D), not for the primary
identity test. This directly repairs the audited gap that `retry_count` catches only
_contiguous byte-identical_ actions.

Let the detector output over sequence $q$ under $(a,\sigma)$ be an ordered list of
motif-applicable instances

$$
I(a,q,\sigma) = \big[(i, m_i, f_i)\big]_{i=1}^{n}, \quad
f_i \in \{0,1\}
$$

where $i$ indexes instances in sequence order, $m_i$ is the applicable motif, and
$f_i = 1$ iff the underlying failure for motif $m_i$ occurred at instance $i$
(i.e. the detector emitted a failure key with `motif_id` $= m_i$).

### 1.2 Post-exposure, first-exposure exclusion

For a given motif $m$, walk the instances of $m$ in sequence order. The
**first-exposure** instance of $m$ is the earliest instance $i^\star_m$ with
$f_{i^\star_m}=1$ (the first time the agent actually fails $m$). An instance $i$ with
$m_i=m$ is **post-exposure** iff $i > i^\star_m$ — it occurs strictly after the agent
has _already failed_ $m$ at least once earlier in the same sequence. Motif-applicable
instances that never had a preceding failure of $m$ (including all instances up to
and including $i^\star_m$, and every instance of a motif the agent never failed) are
**excluded from the RUF denominator**. This exclusion is what makes RUF a measure of
_repetition_, not of first-time difficulty: a first failure is a prerequisite, never
a numerator or denominator event on its own.

Formally, the post-exposure set for a cell:

$$
P(a,q,\sigma) = \big\{\, i : f_{j}=1 \text{ for some } j<i \text{ with } m_j=m_i \,\big\}.
$$

### 1.3 Numerator, denominator, aggregation

**Per-motif RUF** for motif $m$ in a cell:

$$
\mathrm{RUF}_m(a,q,\sigma) =
\frac{\displaystyle\sum_{i \in P(a,q,\sigma)} \mathbb{1}[\,m_i=m\,]\cdot f_i}
     {\displaystyle\sum_{i \in P(a,q,\sigma)} \mathbb{1}[\,m_i=m\,]}
$$

- **Numerator**: post-exposure instances of $m$ where the same underlying failure
  (same `motif_id`) recurred ($f_i=1$).
- **Denominator**: all post-exposure instances of $m$ (recurred or avoided).
- Undefined (0/0) when the agent has no post-exposure instances of $m$; such
  (cell, motif) pairs are dropped from that motif's pool (they carry no repetition
  information), and this drop is applied **identically across conditions** for the
  paired contrast.

**Per-sequence RUF** (pooled over motifs within a sequence):

$$
\mathrm{RUF}_{\text{seq}}(a,q,\sigma) =
\frac{\displaystyle\sum_{i \in P(a,q,\sigma)} f_i}
     {\displaystyle\bigl|\,P(a,q,\sigma)\,\bigr|}.
$$

This is the sequence-level scalar that becomes one bootstrap resampling atom.

**Macro-over-motifs RUF** (the headline number, weighting each motif equally so a
high-frequency motif cannot dominate):

$$
\overline{\mathrm{RUF}}(a) =
\frac{1}{|\mathcal{M}_a^{+}|}\sum_{m \in \mathcal{M}_a^{+}}
\underbrace{\frac{\sum_{q,\sigma}\ \text{num}_m(a,q,\sigma)}
                 {\sum_{q,\sigma}\ \text{den}_m(a,q,\sigma)}}_{\text{pooled per-motif rate}}
$$

where $\mathcal{M}_a^{+}$ is the set of motifs with a nonzero post-exposure
denominator under $a$, and $\text{num}_m,\text{den}_m$ are the per-motif
numerator/denominator of §1.3 pooled across cells. We report **both** the
macro-over-motifs headline and the per-sequence distribution (the latter drives the
CI). A per-instance micro-average is reported only as a secondary robustness view,
because it lets frequent motifs dominate.

**Direction**: ↓ lower is better. H1 (§3.3) predicts
$\overline{\mathrm{RUF}}(\text{pneuma}) < \min_a \overline{\mathrm{RUF}}(a)$ over
$a\in\{\text{base},\text{retrieval},\text{reflection}\}$ with a non-overlapping
paired bootstrap CI on the difference.

---

## 2. SECONDARY metrics (full §8.7 list)

Each row gives numerator, denominator, aggregation, and predicted direction for the
Pneuma-state arm relative to the best relevant baseline. Rates are per-cell unless
noted, then aggregated to a **per-sequence** scalar (mean over the sequence's tasks)
for the bootstrap; counts are per-task then averaged to per-sequence. All belong to
one **multiplicity-corrected family** (§3.5) except where flagged as descriptive.

### Group A — task-level outcomes

| #   | Metric                | Numerator                                                               | Denominator                   | Aggregation                  | Dir |
| --- | --------------------- | ----------------------------------------------------------------------- | ----------------------------- | ---------------------------- | --- |
| A1  | Task success          | tasks resolved (harness `resolved`=true)                                | all tasks                     | per-seq mean, macro over seq | ↑   |
| A2  | First-attempt success | tasks resolved on the first `finish`/submit with no prior failed submit | all tasks                     | per-seq mean                 | ↑   |
| A3  | Recovery success      | tasks resolved **after** ≥1 earlier failure in the same task            | tasks with ≥1 earlier failure | per-seq mean                 | ↑   |

Ground-truth resolution uses only the trustworthy harness label (the sampled lane's
real `report` flags per the adapter audit); synthetic-automated labels
(`constructed_label`, open-swe) are used for scale/robustness only, never as the
headline success oracle.

### Group B — effort / budget (E-0 confound guards)

| #   | Metric              | Numerator                                                                        | Denominator | Aggregation            | Dir          |
| --- | ------------------- | -------------------------------------------------------------------------------- | ----------- | ---------------------- | ------------ |
| B1  | Action count        | count of scaffold tool calls                                                     | — (count)   | per-task, per-seq mean | matched (§4) |
| B2  | Token count         | prompt+completion tokens (metered by local server)                               | — (count)   | per-task, per-seq mean | matched (§4) |
| B3  | Unnecessary retries | contiguous re-issues of a byte-identical action after a non-erroring observation | all actions | per-seq mean rate      | ↓            |

B1/B2 are **not** success metrics; they are the confound variables that must be held
matched across arms (§4). Reporting them is mandatory so a reviewer can verify the
RUF effect is not an artifact of the Pneuma arm simply doing more.

### Group C — safety / discipline

| #   | Metric                  | Numerator                                                                                 | Denominator         | Aggregation  | Dir |
| --- | ----------------------- | ----------------------------------------------------------------------------------------- | ------------------- | ------------ | --- |
| C1  | Constraint violations   | steps violating a declared task constraint (edits outside scope, disallowed tool)         | all steps           | per-seq rate | ↓   |
| C2  | Destructive-action rate | steps issuing an irreversible op (file delete, history rewrite, overwrite of user change) | all steps           | per-seq rate | ↓   |
| C3  | Verification completion | tasks whose final submit was preceded by a passing `run_tests` on the changed unit        | all submitted tasks | per-seq rate | ↑   |

### Group D — generalization / transfer (H4)

Transfer is reported as the **retention ratio** of the RUF reduction on held-out
strata relative to in-distribution:

$$
\mathrm{Transfer}_x =
\frac{\Delta\mathrm{RUF}^{\text{holdout-}x}(\text{base}-\text{pneuma})}
     {\Delta\mathrm{RUF}^{\text{in-dist}}(\text{base}-\text{pneuma})},
\quad x\in\{\text{surface},\text{repo},\text{motif}\}.
$$

| #   | Metric           | Numerator                                                                                 | Denominator                                | Aggregation              | Dir        |
| --- | ---------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------ | ------------------------ | ---------- |
| D1  | Surface transfer | RUF reduction on surface-varied (same `motif_id`, transformed identifiers/text) instances | RUF reduction on in-distribution instances | ratio; macro over motifs | ↑ (near 1) |
| D2  | Repo transfer    | RUF reduction on held-out repositories (repo-axis split)                                  | RUF reduction on training-split repos      | ratio                    | ↑ (near 1) |
| D3  | Motif transfer   | RUF reduction on held-out **motifs** (motif-axis split — a build)                         | RUF reduction on seen motifs               | ratio                    | ↑ (>0)     |

A ratio $\approx 1$ means the effect is not identifier memorization (H4). $D3>0$ on
motifs never grown into scars is the strongest anti-memorization evidence.

### Group E — mechanism-fidelity

| #   | Metric                     | Numerator                                                                       | Denominator           | Aggregation                 | Dir |
| --- | -------------------------- | ------------------------------------------------------------------------------- | --------------------- | --------------------------- | --- |
| E1  | Memory-retrieval precision | retrieved memory records whose `motif_id` matches the current instance's motif  | all retrieved records | per-retrieval, per-seq mean | ↑   |
| E2  | State calibration (Brier)  | $\frac{1}{N}\sum (c_i - o_i)^2$ over confidence var $c$ vs realized failure $o$ | $N$ predictions       | per-seq; also ECE           | ↓   |

State calibration is scored on the confidence variable $c$ (§8.3 var 2): $c_i$ is the
agent's stated per-instance failure probability, $o_i\in\{0,1\}$ the realized
outcome. Report **Brier score** $\mathrm{BS}=\frac{1}{N}\sum(c_i-o_i)^2$ and
**Expected Calibration Error** with $B=10$ equal-width bins,
$\mathrm{ECE}=\sum_{b} \frac{|B_b|}{N}\,\lvert \mathrm{acc}(B_b)-\mathrm{conf}(B_b)\rvert$.
Both ↓.

### Group F — discrimination, causal size, stability

| #   | Metric                   | Numerator                                                                                           | Denominator                                                       | Aggregation                          | Dir           |
| --- | ------------------------ | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ------------------------------------ | ------------- |
| F1  | False-avoidance rate     | counterfactual-task instances where the agent avoided a strategy that was **actually correct** here | all counterfactual-task instances where that strategy was correct | per-seq rate                         | ↓ / not-worse |
| F2  | Intervention effect size | paired $\Delta$ and Cohen's $d_z$ of RUF, treated(clamp) vs control                                 | —                                                                 | per §3.4                             | (report)      |
| F3  | Cross-seed stability     | variance / CV of the per-condition metric across seeds $\sigma$                                     | —                                                                 | $\mathrm{Var}_\sigma$, $\mathrm{CV}$ | ↓             |

**False-avoidance (F1), defined carefully.** The anti-over-avoidance guard (H5). We
construct **counterfactual tasks**: a task where a strategy $g$ that was _punished_
earlier (the agent grew a scar against $g$) is now, by construction of the task, the
**correct** move. Ground truth marks, per counterfactual instance, whether $g$ is
correct here. An **avoidance event** = the agent declines/skips $g$ (via a
`switch_strategy` / non-selection of $g$ traced in the causal log). A **false
avoidance** = an avoidance event on an instance where $g$ was labelled correct.

$$
\mathrm{FalseAvoid}(a) =
\frac{\#\{\text{instances: } g \text{ correct} \wedge g \text{ avoided}\}}
     {\#\{\text{instances: } g \text{ correct}\}}.
$$

This is precisely "avoidance when the strategy was actually correct," measured only
on counterfactual tasks where correctness is known. H5 requires
$\mathrm{FalseAvoid}(\text{pneuma})$ **not worse** than
$\mathrm{FalseAvoid}(\text{reflection})$ (a non-inferiority contrast, §3.3), so a low
RUF cannot be bought by inertia.

**Intervention effect size (F2)** is the treated-minus-control paired RUF delta from
the `PairedReplayRunner`, reported as mean $\Delta$, its bootstrap CI, and Cohen's
$d_z = \bar{\Delta}/s_\Delta$ (paired standardized effect). H2's dose-response
(effect scales with scar strength) is reported as the slope of RUF-reduction on
accumulated scar strength with its CI.

**Cross-seed stability (F3)** reports the variance and coefficient of variation of
each headline metric across the seed set within a condition; a Pneuma arm whose
advantage only appears at one seed is flagged. This is descriptive (not in the
corrected inferential family) but pre-registered.

---

## 3. Statistics

### 3.1 Pairing (all contrasts)

Every contrast is **paired on $(q,\sigma)$**: for conditions $a,b$ we form, for each
matched cell, the per-sequence difference
$\delta_{q,\sigma} = M_a(q,\sigma) - M_b(q,\sigma)$ for metric $M$. We never compare
unpaired condition means. Pairing removes task-difficulty and seed variance, which is
the dominant variance component in agent evaluation and the reason unpaired tests
would be badly underpowered here. A cell missing under either condition (see §3.6) is
dropped **from both** members of that pair.

### 3.2 Bootstrap 95% CIs

- **Resampling unit: the task-sequence** $q$ (not the task, not the instance).
  Instances within a sequence are correlated through the shared persistent state, so
  resampling instances would understate variance. We resample whole sequences with
  replacement.
- **Stratification: seed-stratified.** Resample sequences **within each seed
  stratum** $\sigma$ and pool, preserving the seed composition of the original design
  so cross-seed variance is neither inflated nor collapsed.
- **Replicates: $B = 10000$.**
- **Interval: BCa** (bias-corrected and accelerated) 95% two-sided by default;
  percentile as a robustness cross-check. For the paired difference we bootstrap the
  per-sequence $\delta_{q,\sigma}$ directly.
- A random seed for the bootstrap itself is pinned in the run config so the CI is
  byte-reproducible (consistent with the repo determinism discipline).

### 3.3 Pre-registered primary test (H1)

- **Statistic**: paired difference in macro-over-motifs RUF,
  $\Delta_{ab}=\overline{\mathrm{RUF}}(a)-\overline{\mathrm{RUF}}(\text{pneuma})$ for
  each baseline $a\in\{\text{base},\text{retrieval},\text{reflection}\}$, aggregated
  over per-sequence deltas.
- **Test**: **one-sided** paired test of $H_1:\Delta_{ab}>0$ (pneuma has strictly
  lower RUF) against $H_0:\Delta_{ab}\le 0$. Primary inference is the
  **seed-stratified sequence bootstrap** of $\Delta_{ab}$: H1 is supported for
  baseline $a$ iff the one-sided 95% bootstrap lower bound $>0$ (equivalently the
  two-sided 95% CI excludes 0 on the positive side). A pre-registered
  **one-sided Wilcoxon signed-rank** on the per-sequence deltas is reported as a
  distributional cross-check.
- **Composite H1** ("pneuma beats the _best_ baseline") requires the contrast against
  $\arg\min_a\overline{\mathrm{RUF}}(a)$ — the strongest baseline — to clear the bar;
  reported for **all three** baselines individually as well. The `retry_count`
  heuristic is included specifically as a trivial falsifier (E-0 lesson): if it
  matches or beats pneuma, H1 fails.
- **Falsification** (from §6, doc 02): H1 is false if
  $\overline{\mathrm{RUF}}(\text{pneuma}) \ge \overline{\mathrm{RUF}}(\text{best
    baseline})$ with overlapping 95% CIs on the paired difference at matched budget.

**Non-inferiority sub-tests** (H5): task success (A1) and false-avoidance (F1) use a
pre-registered non-inferiority margin $\Delta_{\text{NI}}$ (fixed in the run config
before running): pneuma is non-inferior iff the 95% CI of (pneuma $-$ best baseline)
lies above $-\Delta_{\text{NI}}$ for success and below $+\Delta_{\text{NI}}$ for
false-avoidance.

### 3.4 Effect-size reporting (mandatory)

No claim rests on a p-value or CI-exclusion alone. Every reported contrast carries:

- absolute paired difference $\bar\Delta$ with its 95% CI,
- **Cohen's $d_z$** (paired) $= \bar\Delta / s_\Delta$ for continuous/rate metrics,
- for the causal contrast, the treated-vs-null $d_z$ and the dose-response slope,
- for transfer, the retention ratio (§D) with CI.

A statistically detectable but negligibly small RUF reduction is reported as such and
does **not** support the behavioural claim tier (§3.7).

### 3.5 Multiplicity correction (secondary family)

The secondary inferential family is groups A–E plus F1 (F2/F3 are effect-size and
descriptive, not hypothesis tests). We control the **false discovery rate** with
**Benjamini–Hochberg (BH-FDR) at $q=0.05$**, applied to the one-sided paired
bootstrap p-values of that family.

- **Why BH-FDR, not Holm–Bonferroni**: the secondary metrics are (a) numerous and
  (b) positively dependent (they are computed from the same traces and move
  together — fewer failures tends to co-move with higher success, higher
  verification completion, etc.). Under positive dependence BH controls FDR and is
  substantially more powerful than the FWER-controlling Holm, which would be
  needlessly conservative for an exploratory secondary panel. BH is valid under the
  positive-regression-dependence (PRDS) structure these metrics plausibly satisfy;
  we additionally report Holm-adjusted values in an appendix as a conservative
  cross-check so no claim depends on the choice.
- **The primary metric (RUF, H1) is NOT in the corrected family.** It is a single
  pre-registered confirmatory test at $\alpha=0.05$ one-sided and is not penalized
  for the secondary panel. H2/H3/H4/H5 primary contrasts are likewise individually
  pre-registered confirmatory tests, each at $\alpha=0.05$; only the broad secondary
  descriptive panel is FDR-controlled.

### 3.6 Aborted / missing runs (pre-registered exclusion)

Fixed before any run:

1. A cell $(a,q,\sigma)$ is **aborted** if the scaffold crashed, hit a wall-clock or
   provider timeout, or produced a trace failing the immutable-trace integrity check
   (commit+config+seed binding). Aborted cells are **excluded**, and — to preserve
   pairing — the matched cells under _all other conditions_ for the same $(q,\sigma)$
   are excluded too (listwise deletion on the pairing key). This prevents an arm from
   looking better merely because its hard sequences crashed out.
2. **Budget exhaustion is NOT abortion.** A run that legitimately hits the retry cap
   or step budget and stops is a valid outcome (it is data about the agent), retained.
3. Attrition is reported: the count and fraction of excluded cells **per condition**,
   with a pre-registered guard that if listwise deletion removes $>10\%$ of pairs, we
   report a sensitivity analysis under (a) complete-case and (b) worst-case
   imputation (aborted pneuma cells scored as failures) so exclusion cannot silently
   favor the treatment.
4. No re-rolling of seeds to replace an aborted cell; the seed set is fixed.

### 3.7 Minimum evidence per claim tier (power)

Power is pre-registered as a **design constraint**, not a post-hoc calculation. The
resampling unit is the sequence, so power is driven by the number of matched
sequences $N_Q$, the number of motifs $|\mathcal{M}|$, and the seed count
$|\mathcal{S}|$. Targets (to be confirmed by a pre-run simulation using the E-0 and
audit-derived base rates; sampled-lane resolve rate ~8%, open-swe ~41%):

| Claim tier (doc 02 §5)  | Contrast                                      | Minimum design                                                                                                                                                          |
| ----------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2 — Behavioural (H1)    | RUF pneuma vs each baseline                   | $N_Q \ge 200$ matched sequences, $\ge 8$ motifs with post-exposure denominators, $\ge 5$ seeds; powered to detect $d_z \ge 0.3$ at $1-\beta=0.8$ (simulation-confirmed) |
| 3 — Causal (H2)         | treated(clamp) vs null, dose-response         | same $N_Q$; $\ge 3$ scar-strength levels for the dose slope; null arm must reproduce control within CI                                                                  |
| 4 — Generalization (H4) | held-out repo & motif transfer                | $\ge 30$ held-out repos; $\ge 3$ held-out motifs with post-exposure instances                                                                                           |
| 5 — Introspection (H3)  | grounded vs unconstrained report faithfulness | clamp-identification above chance across $\ge 4$ clamped variables                                                                                                      |

A tier is **supported** only if its pre-registered contrast clears both the
CI-exclusion and a non-negligible effect size (§3.4); a tier that clears significance
but not the effect-size floor is reported as "detected but small," and a tier whose
design falls short of the row above is reported as **underpowered / inconclusive**,
never as support. Robustness of tier 2 additionally requires replication on $\ge 2$
model sizes (§8.1) — a single-model RUF reduction is not a headline behavioural claim.

---

## 4. The E-0 length / activity confound

The in-repo E-0 negative result is the sharpest known threat: replayed psyche signals
were **anti-correlated** with failure through a length/activity confound (AUROC
0.339/0.349 vs a retry-count baseline of 0.705). More tokens/steps co-vary with both
"more internal-state activity" and "harder task," so an uncorrected RUF reduction
could be a budget artifact. Three pre-registered defenses:

1. **Budget matching at design time.** All arms share the identical step budget,
   retry cap, and token ceiling (§8.1). B1 (action count) and B2 (token count) are
   reported per arm; if the Pneuma arm's mean B1 or B2 differs from the best baseline
   by more than a pre-registered tolerance, the primary contrast is **demoted** to
   the matched analysis below and the raw contrast is reported as confounded.

2. **Token- and action-matched primary analysis.** Beyond design matching, we compute
   RUF on a **matched subsample**: pair pneuma and baseline cells within the same
   $(q,\sigma)$ **and** within the same action-count and token-count stratum
   (coarsened exact matching on B1, B2 deciles). The paired RUF contrast on this
   matched set is the confound-robust headline. If the effect survives matching, it
   is not a length/activity artifact.

3. **Covariate-adjusted secondary analysis.** Fit a pre-registered mixed-effects
   logistic model on the per-instance recurrence outcome $f_i$:

    $$
    \operatorname{logit}\Pr(f_i=1) =
    \beta_0 + \beta_{\text{cond}}\,\mathrm{cond}_i
    + \beta_1\,\log(\text{actions}) + \beta_2\,\log(\text{tokens})
    + u_q + u_\sigma + u_m,
    $$

    with random intercepts for sequence $u_q$, seed $u_\sigma$, and motif $u_m$, and
    $\log$(actions)/$\log$(tokens) as covariates. The condition coefficient
    $\beta_{\text{cond}}$ (pneuma vs baseline), reported as an adjusted odds ratio with
    CI, is the confound-adjusted effect; agreement in sign and rough magnitude with the
    matched primary analysis is required for the causal narrative. This model is
    **secondary/confirmatory of robustness**, not a replacement for the pre-registered
    bootstrap primary test.

The no-sign-flip discipline from E-0 is retained: we never re-orient a signal to
improve a metric after seeing the data.

---

## 5. Reuse and build map (traceability)

- **Reuse verbatim**: `PairedReplayRunner` + counterbalanced digest-bound provenance
  (F2, H2 nulls); `grounding.report_grounding_errors` /
  `reports_track_target_signal` (report-faithfulness family, §8.10); prose-blind
  evaluator firewall (all metrics scored off traces, never prose); determinism +
  canonical hashing (byte-reproducible synthetic RUF and pinned bootstrap seed).
- **Net-new build (not in the codebase today)**: the enriched `trajectory.py` typed
  failure detector emitting `motif_id` (§1.1 — foundational; without it RUF is not
  computable); motif-axis splitting (D3); the false-avoidance / counterfactual-task
  labels (F1); the confidence variable wiring for calibration (E2); the
  covariate-adjusted mixed model (§4). Each is a dependency the implementation plan
  (`12-implementation-plan.md`) sequences before its dependent metric.

---

## 6. Consistency check against §8.7 (do not drift)

Primary metric = RUF, defined here exactly as "fraction of post-exposure motif
instances on which the same underlying failure recurs" (§8.7). Secondary list matches
§8.7 item-for-item: task success, first-attempt success, recovery success, action
count, token count, unnecessary retries, constraint violations, destructive-action
rate, verification completion, false-avoidance, transfer (surface/repo/motif),
memory-retrieval precision, state calibration, intervention effect size, cross-seed
stability. All contrasts paired; bootstrap 95% CIs; pre-registered primary test;
secondary multiplicity correction (BH-FDR); effect sizes mandatory — all as fixed in
§8.7. No Locked Design Constant is contradicted.
