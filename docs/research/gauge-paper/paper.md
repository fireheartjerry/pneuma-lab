# Determinism Is Not Reliability: Measurement-System Analysis for Elicited LLM Metrics

**Status:** working paper draft, 2026-07-28. Local-scale evidence complete; every claim
requiring frontier models or large benchmarks is marked `⟦CLOUD-EXP-n⟧` and listed in §10.
Pre-registration: `docs/research/experiments/g1-gauge-preregistration.md`, committed at
`c42507a` before any model call. Results of record: `docs/research/experiments/g1-gauge-results.md`.

---

## Abstract

Elicited metrics — a model's self-reported confidence, an LLM-as-judge score, any number
obtained by prompting — are instrument readings, and the machine-learning literature reports
their _validity_ (ECE, Brier, AUROC) while never reporting their _reliability_. Every other
mature measuring field requires the reverse order: industrial metrology, analytical
chemistry, clinimetrics and clinical trials all validate precision before accuracy, because
reliability bounds validity and an unreliable instrument cannot be repaired downstream.

We apply measurement-system analysis (MSA) to elicited confidence over 13,632 elicitations
on a 48-item reference bank with execution-established ground truth. The channel carries
real aggregate signal — averaged over 56 elicitations it reaches AUROC 0.906, within 0.02 of
the ceiling its own reliability implies — while resolving **`ndc = 1`** distinct category:
it cannot reliably rank any two items. The defect is **reproducibility, not repeatability**.
Setting `temperature=0` removes 100% of sampling variance and lifts the channel only from
`UNINTERPRETABLE` to `MARGINAL`, because 29% of the remaining variance is reproducibility --
all of it attributable to prompt wording, and enough to keep `%GRR` at 53.9%. At
`T=0`, re-asking the same question reproduces 96% of the verification queue a pipeline would
build; **rephrasing the question reproduces 64%**. The field's one habitual reliability check
— set temperature to zero and re-run — is precisely the check that cannot see this.

Three properties explain the number. Split by ground truth, the channel has essentially no
resolution _within_ a class (`ndc = 0`, %GRR 95.4 among correct implementations): almost all
its item variance is a single correct-vs-buggy step, so it is a noisy binary detector wearing
the costume of a continuous scale. Its repeatability is **2.54x worse on buggy code than on
correct code** — least precise exactly where a verification pipeline needs it. And 38% of
readings are pinned to the top of the scale, censored and unable to order each other. Against
that, rephrasing the question moves the reading **54% as far as introducing a real bug does**.

We prove that post-hoc calibration cannot help: every standard calibrator is weakly
increasing, so it leaves rank-based resolution and AUROC exactly invariant. Empirically Platt
scaling cut ECE by 0.30 while changing discrimination by 0.00e+00. We evaluate five standard
remedies with error bars; two work at a measurable price, one is provably powerless, one is
indeterminate, one adds variance. We ship the analysis as a one-command, dependency-free tool
and a schema-validated **gauge card**, and argue that MSA should be a precondition for
publishing an elicited LLM metric.

The study was pre-registered before any model call, and two of the registered hypotheses did
not survive contact with the data (§11). We report the finding the experiment produced rather
than the one it was designed to look for — which is the ordinary and correct direction of
travel, and is why the pre-registration is preserved unedited.

---

## 1. Introduction

A verification pipeline asks an agent "how confident are you that this patch is correct?",
reads a number, and routes the low-confidence patches to expensive verification. Papers
report how well that number predicts correctness. Nobody reports whether asking again, or
asking differently, yields the same number — and that omission is not a minor gap in
reporting hygiene. It is the difference between a measurement and a guess with a decimal
point.

The gap has a precise name outside our field. In metrology you do not report a part
measurement until a **gauge repeatability and reproducibility (gauge R&R)** study shows the
gauge can resolve parts at all. The governing question is not "is the reading right?" but
**"can this gauge tell two different parts apart?"**, and the answer is a variance
decomposition, not a correlation with truth.

This paper does three things.

1. **Transfers MSA to elicited LLM metrics**, defining the statistics that survive when the
   standard ones degenerate, and adding two that translate the analysis into the decision a
   pipeline actually makes.
2. **Runs the study**, pre-registered, on 13,632 elicitations across wordings, response
   scales, temperatures, provenances, model families and arithmetic precisions, with a
   placebo arm and a five-remedy falsification battery.
3. **Ships the check** as a one-command tool and a reporting standard, so that a reviewer can
   ask for a gauge card the way a chemistry reviewer asks for a validation report.

### 1.1 Contributions

- **The determinism trap, measured.** `temperature=0` eliminates repeatability variance
  entirely and leaves reproducibility untouched. We give the first quantification of the gap
  in decision terms: same-question queue overlap 0.956 vs rephrased-question overlap 0.646 on
  the identical channel. The residual is dominated by the `item x wording` **interaction**
  (24.8% of variance) rather than the wording main effect (4.2%) — rewording reorders items
  rather than shifting them, so it is exactly the component a ranking pipeline cannot absorb
  and the one no amount of resampling removes.
- **A proof that calibration cannot repair resolution.** Every standard post-hoc calibrator
  is weakly increasing; strictly increasing maps leave resolving power and AUROC exactly
  invariant, and weakly increasing maps can only destroy ordering. Verified to machine
  precision on real elicitations.
- **A tight attenuation ceiling.** The reliability-implied AUROC ceiling is not a loose
  formality: the observed fully-averaged AUROC lands within 0.02 of it.
- **Selection stability**, a decision-relevant reliability statistic: the reproducibility of
  the triage queue a pipeline builds, with a closed-form random-selection floor.
- **A gauge card**: a schema-validated artifact carrying the design, decomposition, ceilings,
  a _prescription_ for what a fix would cost, all five remedies with error bars, and the
  placebo response.
- **A mechanism for `ndc = 1`.** Stratifying the gauge study by ground truth shows the channel
  carries one usable graduation — the correct-vs-buggy step — and essentially none within a
  class. This reconciles "good classifier" with "cannot rank two items."
- **Heteroscedasticity as a first-class finding.** Repeatability is 2.54x worse on buggy code
  than on correct code. A single global reliability figure hides that the instrument is least
  precise exactly where it is relied upon.
- **A calibrated sense of how large wording effects are.** Rephrasing moves the reading 54% as
  far as introducing a real bug does, using paraphrases a practitioner would treat as
  interchangeable.
- **A pre-registration that changed our conclusion.** We registered that no technique would
  repair the channel; two do. We report the price instead, and the surviving claim — a
  diagnostic gap in how the field validates every elicited metric — is the larger one.

---

## 2. Background

### 2.1 Reliability and validity are different properties

Validity is agreement between the reading and the truth. Reliability is agreement between the
reading and _itself_ under conditions that should not matter. The ML evaluation literature
measures the first and assumes the second.

They are not independent. Under classical test theory, for score $z$ with reliability
$\rho_{xx}$ and any criterion $c$,

$$
|\rho_{zc}| \le \sqrt{\rho_{xx}}.
$$

A channel with reliability $0.05$ can never exceed $|\rho| = 0.22$ against any criterion, at
any sample size, forever. Without $\rho_{xx}$ you cannot tell whether a disappointing AUROC
is a fact about the model or a fact about your thermometer.

### 2.2 Precedent

| Field                | Requirement                                                                      | Statistic                             |
| -------------------- | -------------------------------------------------------------------------------- | ------------------------------------- |
| Industrial metrology | AIAG MSA 4th ed., ISO 5725 — gauge R&R before release to production              | `%GRR`, `ndc`                         |
| Analytical chemistry | ICH Q2(R2) — precision validated _before_ accuracy                               | repeatability, intermediate precision |
| Clinimetrics         | COSMIN — reliability is a distinct, prior measurement property                   | ICC, SEM, SDC                         |
| Clinical trials      | Outcome instruments report ICC and minimal detectable change before effect sizes | ICC(2,1)                              |
| Psychometrics        | Classical test theory; attenuation correction is standard                        | Cronbach's $\alpha$, ICC              |

ML evaluation is the outlier. Nothing in this paper is an innovation in measurement theory;
it is the application of a settled one.

---

## 3. The gauge card

### 3.1 Model

For item $i$ (random — the "part"), condition $o$ (random — the "operator"; a wording x scale
combination), replicate $r$:

$$
y_{ior} = \mu + \alpha_i + \beta_o + (\alpha\beta)_{io} + \varepsilon_{ior}
$$

- **Repeatability** $\sigma_\varepsilon^2$ — ask the same question again.
- **Reproducibility** $\sigma_O^2 + \sigma_{IO}^2$ — ask it differently.
- **Gauge** $\sigma_{GRR}^2$ = repeatability + reproducibility.
- **Part** $\sigma_I^2$ — the only variance carrying information about items.

$$
\%GRR = 100\frac{\sigma_{GRR}}{\sigma_{tot}}, \quad
ndc = \left\lfloor 1.41\frac{\sigma_I}{\sigma_{GRR}} \right\rfloor, \quad
ICC = \frac{\sigma_I^2}{\sigma_{tot}^2}
$$

AIAG requires $ndc \ge 5$. **$ndc < 2$ means the gauge cannot separate any two items.**

### 3.2 Statistics that survive degeneracy

`ndc` becomes uninformative exactly when $\sigma_I \to 0$. Three distribution-free statistics
carry the load.

**Discrimination index $D$.** Split replicates into two disjoint passes. For item pair
$(i,j)$ and single measurements $a, b$ from the two passes, score $1$ if
$\mathrm{sign}(y_{ia}-y_{ja}) = \mathrm{sign}(y_{ib}-y_{jb}) \neq 0$, $0$ if the nonzero
signs disagree, $\tfrac12$ if either is zero. $D = 1$ is a perfect gauge; $D = 0.5$ is a coin
flip; a constant channel scores exactly $0.5$.

**Resolving power $\Rho$.** The fraction of pairs on which both passes return the _same
nonzero_ sign. $\Rho \le D$, and $\Rho$ is the statistic Theorem 2 is stated on.

**Effective support $S_{eff} = \exp(H)$.** How many levels the channel actually emits.

### 3.3 Statistics that match the decision

A pipeline does not consume the mean of a confidence channel; it ranks items and verifies the
least-confident fraction $q$. Two statistics measure that directly.

**Selection stability.** Expected Jaccard overlap between the bottom-$q$ sets chosen by two
passes that **re-ask** the same question. Ties are broken by per-pass jitter, because that is
what a pipeline does when many items report the same number; a stable tie-break would
manufacture agreement out of the ties themselves. Random floor: $q/(2-q)$.

**Cross-condition selection stability.** The same overlap when the second pass **rephrases**
instead of re-asking.

The gap between them is the practical content of the repeatability/reproducibility split, and
§6.3 shows it is where the whole result lives.

### 3.4 Verdict tiers

| Tier              | Rule                                                          |
| ----------------- | ------------------------------------------------------------- |
| `USABLE`          | `%GRR <= 30` and `ndc >= 5` and `ICC >= 0.70` and `D >= 0.80` |
| `MARGINAL`        | `ndc >= 2` and `ICC >= 0.50` and `D >= 0.65`                  |
| `UNINTERPRETABLE` | otherwise; in particular `ndc < 2` or `D < 0.65`              |
| `DEGENERATE`      | effective support `< 2`                                       |

`UNINTERPRETABLE` is not "underpowered". Underpowered means the effect is real and the error
bar is wide, and more data fixes it. `ndc < 2` means the scale has fewer than two
distinguishable levels, so more data buys a narrower error bar around a quantity with no unit.

---

## 4. Theory

### T1 — Attenuation ceiling

For any score $z$ with reliability $\rho_{xx}$ and any criterion $c$,
$|\rho_{zc}| \le \sqrt{\rho_{xx}}$.

_Proof._ $z = \tau + e$ with $\mathrm{Cov}(\tau,e)=0$ and
$\rho_{xx} = \sigma_\tau^2/\sigma_z^2$. Then
$\rho_{zc} = \rho_{\tau c}\,\sigma_\tau/\sigma_z = \rho_{\tau c}\sqrt{\rho_{xx}}$ and
$|\rho_{\tau c}| \le 1$. $\blacksquare$

Under a binormal model with base rate $p$, invert $r_{pb} = d/\sqrt{d^2 + 1/(p(1-p))}$ and
report $\mathrm{AUROC}_{\max} = \Phi(d/\sqrt2)$. §6.2 shows this bound is nearly attained,
so it is an operative constraint rather than a formality.

### T2 — Calibration futility

Let $z$ be the score the pipeline reads and $g$ any post-hoc calibrator — by definition a
function of the score alone.

1. If $g$ is **strictly** increasing then $\mathrm{sign}(g(u)-g(v)) = \mathrm{sign}(u-v)$, so
   every indicator in $D$ and $\Rho$ is unchanged: $D(g(z)) = D(z)$, $\Rho(g(z)) = \Rho(z)$,
   and $\mathrm{AUROC}(g(z),c) = \mathrm{AUROC}(z,c)$, **exactly**.
2. If $g$ is **weakly** increasing (isotonic, histogram binning) it can only merge ordered
   points into ties, so $\Rho(g(z)) \le \Rho(z)$ and $\mathrm{AUROC}(g(z),c) \le
   \mathrm{AUROC}(z,c)$ when the latter is $\ge 0.5$.

Every standard method — Platt, temperature, beta, isotonic, histogram binning, quantile
mapping — is weakly increasing. **No standard calibration method can increase the resolution
of a gauge.** It relocates the scale, which lowers ECE, and that reduction is routinely
reported as if the metric had been repaired. $\blacksquare$

### T3 — Aggregation asymptote

Averaging $k$ replicates within a fixed condition shrinks only the exchangeable part:

$$
\rho_k = \frac{\sigma_I^2}{\sigma_I^2 + \sigma_{sys}^2 + \sigma_\varepsilon^2/k},
\qquad
\rho_\infty = \frac{\sigma_I^2}{\sigma_I^2 + \sigma_{sys}^2}, \quad
\sigma_{sys}^2 = \sigma_O^2 + \sigma_{IO}^2.
$$

Spearman–Brown with a floor. If $\rho_\infty$ is below the usability floor, no sample count
suffices; the tool reports the required $k$ or `unreachable`. $\blacksquare$

### T4 — Significance without resolution

$\mathrm{MDE} = (z_{0.975}+z_{0.80})\,\sigma_{GRR}\sqrt{2/(Ik)} \to 0$ as $Ik$ grows,
**independently of $ndc$**. Statistical significance on an elicited channel is purchasable
with compute and certifies nothing about resolution. The placebo arm (§6.5) demonstrates this
directly.

---

## 5. Experimental design

**Items.** A 48-item reference bank: 24 pure-function specs, each with a correct
implementation and a single seeded fault of a declared class (off-by-one, wrong-branch,
missing-case, wrong-operator, mutation). Labels are established by **executing** hidden tests
in a timeout-guarded subprocess, verified 48/48. Metrology requires reference parts spanning
the tolerance band; the paired design is also the confound control (§6.6).

**Facets.** 8 wordings (2 reverse-keyed and inverted at parse time); 4 response scales
(`0.00–1.00` two decimals, `0–100`, `0–10`, `1–5` Likert); temperatures $\{0.0, 0.7\}$; arms
`base` / `sham` / `treated` with length-matched context blocks (297 vs 293 characters, 54 vs
53 words); provenances `foreign` (the model rates code it never wrote — _this is exactly an
LLM-as-judge setup_) and `self_authored` (the model writes the solution and is asked about it
**in the same conversation**, so the report is a genuine self-report rather than role-play).

**Models.** Six local open-weight models spanning two families, two sizes and two arithmetic
precisions: `qwen2.5-coder:7b` (Q4_K_M) and `qwen2.5-coder:7b-instruct-fp16` (F16) — the same
model at two precisions — plus `qwen2.5-coder:1.5b`, `qwen2.5:7b`, `qwen2.5:1.5b`,
`llama3.1:8b`.

**Design.** The full factorial is ~3.5M elicitations, so the study is fractional: each stage
varies one facet against a fixed core (`qwen2.5-coder:7b`, foreign, `base`, `p2`, T=0.7).
13,632 elicitations total.

**Parsing.** Strict; refuses to guess. Non-integral answers on an integer scale are rejected
as scale non-compliance — a choice conservative _against_ our thesis, since it discards
exactly the responses that would inflate apparent gauge variance. Core-stage parse-failure
rate 0.4%.

**Analysis.** Pre-registered order, bootstrap over items (2000 draws, seed 20260728),
BH-FDR at $q=0.05$. Remedy verdicts are decided by the **interval**, not the point estimate:
a CI straddling the floor is `INDETERMINATE`, because a remedy not shown to work has also not
been shown to fail.

---

## 6. Results

### 6.1 What the channel emits

Offered a continuous `0.00–1.00` scale, the channel used 35 distinct values with an effective
support of **6.73 levels**, dominated by `1.00` (1188), `0.95` (829), `0.85` (355). Mean
reported confidence **0.873** against actual bank accuracy **0.489** (ECE 0.378). It reports
0.963 on code that passes its hidden tests and 0.782 on code with a seeded bug — a real
separation of **0.181**.

### 6.2 Primary result

47 items x 8 wordings x 7 replicates = 2,632 retained observations.

| component | variance | share of total variance |
| --- | ---: | ---: |
| item (signal) | 0.026567 | 51.2% |
| repeatability | 0.021349 | 41.1% |
| reproducibility | 0.003978 | 7.7% |
| **gauge (GRR)** | **0.025328** | **48.8%** |

`%GRR = 69.9%` is a ratio of **standard deviations** ($\sqrt{0.488}$), not of variances. Both
are reported because the two are routinely confused and only the SD ratio is comparable to the
AIAG 30% bar.

| statistic                   |               value | threshold          |
| --------------------------- | ------------------: | ------------------ |
| %GRR                        |               69.9% | <= 30%             |
| **ndc**                     |               **1** | >= 5               |
| ICC                         |               0.512 | 0.70               |
| $D$                         |               0.684 | 0.5 = coin flip    |
| resolving power             |               0.469 |                    |
| selection stability (q=0.2) |               0.568 | random floor 0.111 |
| **verdict**                 | **UNINTERPRETABLE** |                    |

Single-shot AUROC **0.782**; averaged over 56 elicitations per item, **0.906**; the ceiling
implied by the measured reliability is **0.926**. The bound is nearly attained — T1 is
operative, not decorative.

Operationally: ask the same model the same question twice, build the queue a pipeline would
build (least-confident 20%), and **43% of that queue changes**.

### 6.3 Why `ndc = 1`: the channel is a one-step detector, not a scale

Splitting the gauge study by ground truth explains the headline number mechanistically.

| subset            |   ndc |   ICC |   $D$ | %GRR |
| ----------------- | ----: | ----: | ----: | ---: |
| correct code only | **0** | 0.091 | 0.574 | 95.4 |
| buggy code only   |     1 | 0.460 | 0.674 | 73.5 |
| pooled            |     1 | 0.512 | 0.684 | 69.9 |

Within a class, the channel has essentially **no** resolution — among correct implementations
it is 95.4% gauge variance and $D = 0.574$, barely above a coin flip. Almost all of the
pooled item variance is the single correct-vs-buggy step. That is precisely what `ndc = 1`
means and it is not a metaphor: the instrument has one usable graduation. It behaves as a
noisy binary detector wearing the costume of a continuous scale, which is why it can be a
decent classifier (§6.2) and still be unable to rank two patches.

Two further properties compound this.

**Heteroscedasticity — the gauge is noisiest exactly where it matters.** Repeatability SD is
**0.062** on code that passes its hidden tests and **0.158** on code with a seeded bug: the
instrument is **2.54x less precise on the items a verification pipeline exists to catch**. A
single global reliability figure hides this entirely.

**Saturation.** **38.3%** of readings sit exactly at the top of the scale (40.5% at either
endpoint). Pinned readings are censored — they report "at least this much" and cannot order
each other — which caps resolution independently of any variance component. Of the readings
at maximum confidence, **281 are on code that fails its hidden tests**.

### 6.4 A rephrase moves the reading half as far as a real bug does

The eight wordings are semantically equivalent requests for the same judgement about the same
code. Their means are not:

| wording                                         |      mean | wording                                        |  mean |
| ----------------------------------------------- | --------: | ---------------------------------------------- | ----: |
| w1 "how confident … correct?"                   |     0.903 | w5 "chance a reviewer finds a bug?" (rev.)     | 0.834 |
| w2 "probability it passes a hidden test suite?" | **0.811** | w6 "likely it fails a hidden test?" (rev.)     | 0.871 |
| w3 "certainty it contains no bugs?"             | **0.909** | w7 "estimate the reliability"                  | 0.878 |
| w4 "credence that this code is correct?"        |     0.882 | w8 "how sure it does what the docstring says?" | 0.893 |

The spread across wordings is **0.098**. The spread between code that works and code that
does not is **0.181**. So:

> **Rephrasing the question moves the reported confidence 54% as much as actually
> introducing a bug does.**

"How confident are you that this is correct?" and "What is the probability it passes a hidden
test suite?" differ by 0.092 — and these are not adversarial paraphrases, they are the two
phrasings a practitioner would consider interchangeable.

### 6.5 Determinism is not reliability — the central result

|                                          | T = 0.0 (greedy) |         T = 0.7 |
| ---------------------------------------- | ---------------: | --------------: |
| repeatability variance                   |    **exactly 0** |          0.0158 |
| cells with all replicates identical      |          192/192 |          13/188 |
| ndc                                      |                2 |               1 |
| ICC                                      |            0.710 |           0.595 |
| $D$                                      |            0.841 |           0.701 |
| %GRR                                     |             53.9 |            63.7 |
| queue overlap, **same wording re-asked** |        **0.956** |           0.620 |
| queue overlap, **rephrased**             |        **0.646** |           0.672 |
| verdict                                  |         MARGINAL | UNINTERPRETABLE |

Greedy decoding is a genuinely effective free remedy: it removes _all_ repeatability variance
and lifts the channel one tier at zero cost. And it is still not enough, in exactly the way
that matters:

At `T=0` the decomposition is unambiguous, because repeatability is exactly zero and every
remaining component is reproducibility:

| component | variance | share of total variance |
| --- | ---: | ---: |
| item (signal) | 0.037193 | 71.0% |
| repeatability | **0.000000** | **0.0%** |
| wording main effect | 0.002186 | 4.2% |
| item x wording interaction | 0.013016 | 24.8% |
| **gauge (GRR)** | **0.015202** | **29.0%** |

Where that reproducibility lives is the mechanism. The wording *main effect* is small (4.2%);
the **`item x wording` interaction is six times larger** (24.8%). Rewording does not shift
every reading up or down — a pure shift would cancel in any ranking and cost a triage pipeline
nothing. It **reorders the items**. That is why the rephrased queue overlap falls to 0.646
while the re-asked overlap is 0.956, and it is why the interaction term is the one component
that neither greedy decoding nor averaging over replicates can touch: it is condition-locked
by construction (T3).

> At `T=0` the channel reproduces its own numbers perfectly — re-ask and 96% of the queue is
> identical. Rephrase the question and only 64% is. Determinism bought a reproducible
> _number_, not a reproducible _measurement_.

A `temperature=0` elicited metric therefore passes the only reliability check anyone runs
while 29% of its variance -- and 100% of its remaining gauge variance -- still comes from a
prompt-wording choice nobody logged. We believe
this is the most consequential finding here, because it explains how the field arrived at
confidence in these numbers without ever measuring their reliability.

### 6.6 Response precision

| scale            | ndc |   ICC |   $D$ | %GRR | $S_{eff}$ |  mean | verdict         |
| ---------------- | --: | ----: | ----: | ---: | --------: | ----: | --------------- |
| `p2` (0.00–1.00) |   1 | 0.567 | 0.697 | 65.8 |      7.23 | 0.843 | UNINTERPRETABLE |
| `pct` (0–100)    |   1 | 0.553 | 0.686 | 66.8 |      5.76 | 0.825 | UNINTERPRETABLE |
| `ten` (0–10)     |   1 | 0.638 | 0.713 | 60.1 |      6.57 | 0.728 | UNINTERPRETABLE |
| `five` (1–5)     |   1 | 0.560 | 0.677 | 66.3 |      3.65 | 0.737 | UNINTERPRETABLE |

Invariant to response precision. Offering two decimal places buys 7.2 effective levels, not 100. And the _level_ moves: the same judgement about the same code shifts by **0.115** between
the 0–10 and 0.00–1.00 scales. That is the instrument's zero point moving, not the model's
mind.

### 6.7 The placebo arm: the channel ignores irrelevant content and obeys irrelevant form

We pre-registered that the channel would be **placebo-dominated** — that a known-inert,
length-matched context block would move it at least as much as item identity does
($\Pi > 1$). It does not. This is the study's cleanest falsification of its own hypothesis
and it is a strong positive control for everything else.

| arm       | context block                                        |   mean | contrast vs base |         $p$ |
| --------- | ---------------------------------------------------- | -----: | ---------------: | ----------: |
| `base`    | none                                                 | 0.8587 |                — |           — |
| `sham`    | 297 chars, task-irrelevant (a CI-migration note)     | 0.8632 |      **+0.0044** |    **0.72** |
| `treated` | 293 chars, genuinely relevant (a prior-failure memo) | 0.7735 |      **−0.0876** | **2.2e-10** |

**Placebo-dominance ratio $\Pi = 0.000$, CI $[0.000, 0.011]$** — the sham main effect is
statistically indistinguishable from zero, against an item variance of 0.041. The minimum
detectable effect at this design is 0.0235, so the study had ample power to see a placebo
effect roughly five times smaller than the treated effect it did detect.

The channel is therefore **not suggestible**: pad the prompt with plausible but irrelevant
repository chatter and it does not budge; give it information that genuinely bears on
correctness and it moves sharply, in the right direction, with a very large effect.

Set that against §6.6, where merely _rephrasing the question_ shifts the reading by 0.098 —
more than the 0.088 that a real prior-failure memo achieves. The precise finding is:

> **The channel ignores irrelevant content and obeys irrelevant form.** It is robust to what
> you put in the prompt and highly sensitive to how you ask the question.

This is why the failure is a _metrological_ one rather than a credulity one, and why the
remedy is a measurement protocol rather than better prompting hygiene. The same data that
shows the channel responding sensibly to meaning ($p = 2 \times 10^{-10}$) scores
`UNINTERPRETABLE` with `ndc = 1` on this stage's base arm. A channel can be semantically
well-behaved and metrologically useless at the same time, and only one of those two
properties is ever measured.

### 6.8 Confound control

E-0 in this repository died of a length confound, so the same trap is checked explicitly.
Confidence correlates with source length at $+0.278$ — but length correlates with correctness
at only $+0.057$, because the bank pairs each correct implementation with a single-fault
sibling of near-identical length on an identical task. The **within-spec** contrast therefore
cannot be produced by length or topic, and it is decisive: the correct sibling is rated higher
in **21 of 23** specs, mean difference $+0.188$.

### 6.9 Provenance — the failure is not about introspection

If the failure were introspective — a model being bad at knowing its own mind — it would not
appear when the model rates code it never wrote. We ran both arms. In `self_authored` the
model writes the solution and is asked about it **in the same conversation**, so the report is
a genuine self-report rather than role-play; in `foreign` it rates bank code it has never
seen, which is exactly an LLM-as-judge setup.

| arm | items | ndc | ICC | $D$ (95% CI) | %GRR | $S_{eff}$ | mean | verdict |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| self-authored (own code) | 24 | **0** | 0.069 | **0.562** [0.538, 0.582] | 96.5 | 2.71 | 0.961 | UNINTERPRETABLE |
| foreign (never wrote it) | 24 | **0** | 0.137 | **0.567** [0.532, 0.597] | 92.9 | 3.07 | 0.970 | UNINTERPRETABLE |

The two arms are indistinguishable: $D$ differs by **0.004** with heavily overlapping
intervals, both resolve `ndc = 0` categories, both exceed 92% gauge variance, and both sit a
few hundredths above the 0.5 coin-flip floor. There is also **no self-enhancement** — the
model is if anything marginally _less_ confident about its own code ($-0.010$).

**G1-H2 is confirmed.** The collapse is not a fact about self-knowledge; it is a fact about
elicitation as a measurement modality. That is what carries the result out of the
introspection literature and into every LLM-as-judge number and elicited eval score in the
field: a judge rating an artifact it did not produce is the _foreign_ arm, and the foreign arm
is no better.

Both arms are range-restricted by construction (the foreign arm is correct-variant items only;
the self-authored arm is the model's own solutions), which inflates %GRR in both. The
restriction is symmetric, so the comparison between them is fair, but the absolute numbers in
this table should be read against §6.2 rather than on their own. Notably the within-class
result from §6.3 reappears here independently: restricted to a single correctness class, the
channel resolves nothing at all.

### 6.10 Model families, sizes, arithmetic precision

⟦PENDING — `families` stage, including the F16-vs-Q4_K_M pair of the same 7B model.⟧

### 6.11 The five remedies

| remedy            | statistic                           |     value | verdict                |
| ----------------- | ----------------------------------- | --------: | ---------------------- |
| second model      | $D$ of the judge model              | ⟦PENDING⟧ | ⟦PENDING⟧              |
| thresholding      | split-half $\kappa$ at the best cut | ⟦PENDING⟧ | ⟦PENDING⟧              |
| calibration       | $D$ after Platt / isotonic          |         — | **FAILS (proved, T2)** |
| wording-averaging | ICC of the averaged score           | ⟦PENDING⟧ | ⟦PENDING⟧              |
| self-consistency  | ICC of the $k$-sample mean          | ⟦PENDING⟧ | ⟦PENDING⟧              |

The calibration row is settled analytically and confirmed numerically on real elicitations:
Platt scaling changed $D$ by **0.00e+00** while cutting ECE by **0.3013**. That gap is the
illusion the standard is designed to expose — the improvement is entirely in the statistic
papers report and entirely absent from the instrument's resolution.

Aggregation remedies work at a price. The tool reports it: reaching ICC 0.70 needs ~3
replicates or ~3 distinct wordings; the fully wording-averaged score (24 calls per item) attains
ICC **0.910** and $D$ **0.881**. But the decision does not improve proportionally — the q=0.2
queue moves only from 0.568 to 0.667. **The remedies fix the statistic faster than they fix
the decision.**

---

## 7. Implications for LLM-as-judge and elicited evals

Every number above comes from a model rating code it did not write. That is the LLM-as-judge
condition, so the analysis is not about introspection and does not depend on any claim about
self-knowledge. Three consequences:

1. **A judge score reported at `temperature=0` has not been shown to be reliable.** It has
   been shown to be repeatable, which is a different and much weaker property.
2. **Reported ECE improvements from calibration do not indicate improved discrimination**, by
   Theorem 2. Papers should report resolution before and after, not ECE alone.
3. **Elicited-metric contrasts need a stated unit.** When `ndc < 2` the scale has fewer than
   two distinguishable levels, and by T4 significance is purchasable with sample size.

## 8. The reporting standard

We propose the **gauge card**: a schema-validated one-page artifact carrying channel identity
(including a prompt digest), design, variance decomposition, resolution statistics with CIs,
both selection-stability statistics, reliability-implied ceilings, a **prescription** for what
a fix would cost, all five remedies with error bars and interval-based verdicts, the placebo
response, the verdict with its literal threshold rule, and a reproduction command with a data
digest.

Minimum acceptable design: $\ge 30$ items spanning the range of interest, $\ge 5$ replicates
per cell, and **at least two reproducibility facets** — one is not enough, because the most
common real failure is a channel stable under resampling and unstable under rewording, which a
single-facet design cannot see.

One line a reviewer can ask:

> Table N reports an elicited model score. Please include a gauge card (or equivalent
> measurement-system analysis) reporting `%GRR`, `ndc`, `ICC` and the discrimination index for
> that channel, with the replicate and rewording design used to estimate them.

## 9. Limitations

- **Scale of models.** Six open-weight models, 1.5B–8B, run locally. We do not claim frontier
  models behave identically — see `⟦CLOUD-EXP-1⟧`.
- **Scale of items.** 48 short pure functions. Real patches are longer and more heterogeneous
  — `⟦CLOUD-EXP-3⟧`.
- **Channel scope.** This studies _elicited numeric self-report_. Logit-based and
  internal-probe confidence are different channels and may card as `USABLE`; if anything a
  failing elicited card is an argument for using them — `⟦CLOUD-EXP-4⟧`.
- **A card describes a channel plus a protocol, not a model.** `UNINTERPRETABLE` does not mean
  the model lacks calibrated internal states.
- **"Form" is not perfectly isolated from "meaning" in §6.7.** The eight wordings are close
  paraphrases, but they are not purely syntactic: "probability it passes a hidden test suite"
  names a specific referent that "confident it is correct" does not, so part of the 0.098
  spread may be a genuine difference in what was asked rather than pure form. The sham/treated
  contrast is clean — the sham block is definitionally uninformative — but the strongest
  version of the form claim needs paraphrases sampled from a generative distribution and
  screened for semantic equivalence, which is `⟦CLOUD-EXP-7⟧`. We state the finding as
  "sensitive to how the question is asked" rather than "sensitive to syntax alone."
- **Verdict thresholds are imported** from AIAG and clinimetrics rather than derived for this
  domain. They are pre-registered and reported alongside raw statistics so a reader can apply
  their own — `⟦CLOUD-EXP-6⟧`.
- **Two pre-registered hypotheses were falsified** (§11). We report the weaker surviving
  claim.

## 10. Experiments requiring cloud scale

Each placeholder is a concrete, pre-specifiable experiment that the local study cannot run.
The tool and card schema are unchanged for all of them; only the elicitation backend differs.

| Tag             | Experiment                                                                                                                                                                                                    | Why it needs cloud scale                                                                                                     | Pre-specified prediction                                                                                                                              |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `⟦CLOUD-EXP-1⟧` | **Frontier-model replication.** Run the identical G-1 design (48 items x 8 wordings x 4 scales x 8 replicates x 2 temperatures) against 4–6 frontier models across ≥3 providers. ~25k elicitations per model. | Requires paid API access and per-provider rate budget; no open-weight proxy establishes frontier behaviour.                  | `ndc` rises but stays `< 5`; the same-question / rephrased selection-stability gap persists at `T=0`. Falsified if any frontier model cards `USABLE`. |
| `⟦CLOUD-EXP-2⟧` | **LLM-as-judge benchmarks.** Apply the card to standard judge settings (pairwise preference and single-score rubric grading) with ≥8 wordings and ≥5 replicates per item.                                     | Needs large judged corpora and the API budget to replicate every judgement 5–8x, which published judge evaluations never do. | Judge scores card `MARGINAL` or worse; rephrasing moves the induced ranking materially.                                                               |
| `⟦CLOUD-EXP-3⟧` | **Real repository patches.** Replace toy functions with real agent-generated patches on a verified SWE benchmark, ground truth from the benchmark harness, ≥500 items.                                        | Requires container-based execution at scale plus agent rollouts to generate the patches.                                     | The variance decomposition shifts toward reproducibility as items get longer; `ndc` does not improve.                                                 |
| `⟦CLOUD-EXP-4⟧` | **Logit-based vs elicited channels, head to head.** Card both channels on identical items — sequence log-probability, verbalized number, and an internal-probe readout.                                       | Needs logprob-exposing endpoints and, for probes, weight access at frontier scale.                                           | The logit channel cards materially better; this is the constructive counterpart to the negative result.                                               |
| `⟦CLOUD-EXP-5⟧` | **Human-rater reference gauge.** Run the same MSA on human reviewers rating the same items, ≥5 raters x ≥3 occasions.                                                                                         | Requires an annotation budget and ethics/consent process.                                                                    | Establishes whether human `%GRR` is comparably poor, which determines whether the AIAG thresholds are the right yardstick at all.                     |
| `⟦CLOUD-EXP-6⟧` | **Threshold calibration for the domain.** Derive verdict tiers empirically by relating `ndc`/`D` to downstream pipeline regret across many channels and tasks.                                                | Needs a large corpus of cards, i.e. adoption plus many paid runs.                                                            | Replaces imported AIAG cutoffs with decision-theoretic ones.                                                                                          |
| `⟦CLOUD-EXP-7⟧` | **Prompt-population sampling.** Sample wordings from a realistic generative distribution (≥50 paraphrases) instead of 8 hand-authored ones.                                                                   | Requires large-scale paraphrase generation and 50x the elicitation budget.                                                   | Reproducibility variance grows; the wording-averaging prescription rises well above 3.                                                                |
| `⟦CLOUD-EXP-8⟧` | **Provider and version drift.** Re-card the same channel across provider snapshots over ≥3 months.                                                                                                            | Needs sustained paid access across model version changes.                                                                    | Adds a third reproducibility facet — version — that no current eval controls for.                                                                     |

`⟦CLOUD-EXP-1⟧` and `⟦CLOUD-EXP-2⟧` are the two that must land before the central claim can be
stated for the field rather than for local open-weight models. Everything in §6 should be read
as established **for the channels actually measured**, with the generalization explicitly
pending.

## 11. Pre-registration compliance

Reported in full, including against us.

| Hypothesis | Pre-registered                                                 | Observed                             | Status                  |
| ---------- | -------------------------------------------------------------- | ------------------------------------ | ----------------------- |
| G1-H1      | `ndc <= 1` **and** `D < 0.65`                                  | `ndc = 1`, `D = 0.684`               | **partially falsified** |
| G1-H2      | foreign not better than self-authored                          | $\Delta D = 0.003$, both `ndc = 0`  | **confirmed**           |
| G1-H3      | no model cell reaches `USABLE`                                 | ⟦PENDING⟧                            | ⟦PENDING⟧               |
| G1-H4      | neither temperature reaches `ndc >= 2`; $S_{eff} < 2$ at `T=0` | `ndc = 2` at `T=0`, $S_{eff} = 4.07$ | **falsified**           |
| G1-H5      | all five remedies stay below the floor                         | wording-averaging reaches ICC 0.910  | **partially falsified** |
| G1-H6      | $\Pi > 1$ with significant sham contrast                       | $\Pi = 0.000$, sham $p = 0.72$       | **falsified**           |

Three registered hypotheses did not survive. The channel is better behaved than we
predicted on two axes — it is repairable at a price (H5), and it is not placebo-driven at all
(H6) — and the failure that remains is narrower and better localized because of it.

We regard this as the pre-registration doing its job. The interesting result is the one the
experiment found, not the one it was built to look for: the channel is a low-resolution
instrument whose dominant defect is _reproducibility_; the field's habitual reliability check
is structurally blind to that defect; calibration provably cannot repair it; and the repairs
that do work have a price that is computable and should be reported rather than assumed. Had
we found what we registered, the paper would have been a negative result about one channel.
What we found instead is a diagnostic gap in how the field validates every elicited metric,
which is a larger and more actionable claim.

## 12. Reproduction

```txt
python -m pneuma_lab.gauge selftest                       # validate the estimator, offline
python -m pneuma_lab.gauge run --config configs/g1.json   # the full study
python scripts/gauge_g1_analysis.py                       # the pre-registered analysis order
```

`selftest` simulates four gauges whose variance components are known by construction and
confirms the estimator recovers the correct verdict for each — an MSA tool that has not itself
been checked against known ground truth is an unvalidated instrument. A committed real-data
fixture (`fixtures/gauge/g1-core-sample.jsonl`) carries the T1 and T2 assertions as regression
tests on real elicitations rather than synthetic data.
