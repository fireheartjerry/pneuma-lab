# G-1 Pre-Registration — Is the self-report confidence channel a measurement instrument?

**Status:** pre-registered. Written and committed **before** any model call of the study
was made. Base commit: `0e8f728`. Date: 2026-07-28.

**One sentence.** We subject the elicited self-report confidence channel — the number a
verification pipeline reads when it asks an agent "how sure are you?" — to the same
measurement-system analysis (MSA) that industrial metrology, analytical chemistry,
clinimetrics, and clinical trials require of any instrument before its readings are allowed
into an inference, and we pre-register that it fails at the level of _resolution_, not
noise, which makes placebo-controlled contrasts on that channel **uninterpretable rather
than merely underpowered**.

**Falsifiability of our own thesis is the point.** Section 7 lists exactly what result
would refute us. If any facet cell reaches `USABLE`, or any of the five remedies reaches the
pre-registered usability floor, we publish that and the thesis is dead. E-0
(`e0-results.md`) is this repo's precedent: a pre-registered FAIL published in full.

---

## 1. Background and the gap this fills

Two literatures exist and neither answers the question.

**Calibration.** ECE / Brier / reliability diagrams / AUROC for verbalized confidence.
These measure **validity** — agreement between the reading and the truth. Every one of them
presumes the reading is a _reading_: a quantity that would come out approximately the same
if you asked again, or asked in different words, or asked on a differently-worded scale.

**Reliability.** Nobody reports it for elicited LLM metrics. The field reports
`temperature=0` as if determinism were reliability (it is not: a broken ruler that always
reads 30 cm is perfectly repeatable and carries zero information), and reports
self-consistency sample counts as if averaging were a fix (it is only a fix for the
_exchangeable_ part of the error).

The gap is exactly the one that MSA was invented to close. In metrology you do not report a
part measurement until a Gauge R&R study shows the gauge can resolve parts at all. The
governing question is not "is the reading right?" but **"can this gauge tell two different
parts apart?"** — and the answer is a variance decomposition, not a correlation with truth.

**Precedent for the standard we propose.** AIAG MSA 4th ed. and ISO 5725 (industrial
metrology: `%GRR`, `ndc`); ICH Q2(R2) (analytical procedure validation: precision reported
before accuracy); COSMIN (clinimetrics: reliability is a _separate, prior_ measurement
property from validity); ICC reporting requirements for clinical outcome instruments. In
every one of those fields, publishing a measurement without its measurement-system analysis
is a desk reject. In ML evaluation it is the norm.

**Why it is not only about introspection.** If the failure were introspective — a model
being bad at knowing its own mind — it would not appear when the model rates code it never
wrote. We include a foreign-provenance arm precisely to test that. A foreign-provenance
elicited score **is** an LLM-as-judge score. If the collapse is identical there, the result
is not about self-knowledge; it is about elicitation as a measurement modality, and it
transfers to every LLM-as-judge number and every elicited eval score in the field.

---

## 2. The object under study

An **elicited channel** $\chi$ is a procedure that maps an item $x$ and a set of nuisance
facets $\phi$ (prompt wording, response scale, decoding seed, model build) to a number
$y \in [0,1]$ by prompting a model. A verification pipeline reads $y$ and acts on it.

Measurement model, item $i \in 1..I$ (random effect — the "part"), condition
$o \in 1..O$ (random effect — the "operator"; here a wording x scale combination),
replicate $r \in 1..R$:

$$
y_{ior} = \mu + \alpha_i + \beta_o + (\alpha\beta)_{io} + \varepsilon_{ior},
$$

with $\alpha_i \sim (0, \sigma_I^2)$, $\beta_o \sim (0, \sigma_O^2)$,
$(\alpha\beta)_{io} \sim (0, \sigma_{IO}^2)$, $\varepsilon_{ior} \sim (0, \sigma_\varepsilon^2)$,
all mutually independent.

- **Repeatability (EV)** $\sigma_\varepsilon^2$ — same item, same condition, ask again.
- **Reproducibility (AV)** $\sigma_O^2 + \sigma_{IO}^2$ — same item, different wording/scale.
- **Gauge variation** $\sigma_{GRR}^2 = \sigma_\varepsilon^2 + \sigma_O^2 + \sigma_{IO}^2$.
- **Part variation** $\sigma_I^2$ — the only variance that carries information about items.
- $\sigma_{tot}^2 = \sigma_I^2 + \sigma_{GRR}^2$.

Reported statistics:

$$
\%GRR = 100\frac{\sigma_{GRR}}{\sigma_{tot}}, \qquad
ndc = \left\lfloor 1.41\frac{\sigma_I}{\sigma_{GRR}} \right\rfloor, \qquad
ICC = \frac{\sigma_I^2}{\sigma_{tot}^2}.
$$

`ndc` is the number of distinct categories the gauge can resolve. AIAG requires
$ndc \ge 5$. **`ndc < 2` means the instrument cannot separate any two items** — the scale it
induces has fewer than two distinguishable levels.

Because `ndc` degenerates when $\sigma_I \to 0$, we add two distribution-free statistics
that stay defined and carry the theorems:

**Discrimination index.** Split the replicates of each item into two disjoint passes
$A, B$. For item pair $(i,j)$ and single measurements $a \in A$, $b \in B$, score agreement
as $1$ if $\mathrm{sign}(y_{ia}-y_{ja}) = \mathrm{sign}(y_{ib}-y_{jb}) \neq 0$, as $0$ if the
nonzero signs disagree, and as $\tfrac12$ if either sign is zero (a tie carries no ordering
information, so it is scored as a coin flip):

$$
\hat D = \frac{1}{\binom{I}{2}} \sum_{i<j} \frac{1}{|A||B|} \sum_{a \in A}\sum_{b \in B} s_{ij}^{ab}.
$$

$\hat D = 1$ is a perfect gauge; $\hat D = 0.5$ is a coin flip on pairwise ordering; a
constant channel gives exactly $0.5$.

**Resolving power.** $\hat\Rho$ = the fraction of item pairs on which both passes return the
_same nonzero_ sign. $\hat\Rho \le \hat D$, and $\hat\Rho$ is the statistic the calibration
theorem is stated on.

**Effective support.** $S_{eff} = \exp(H)$ where $H$ is the Shannon entropy (nats) of the
empirical distribution over distinct emitted values. How many levels the channel actually
uses, irrespective of how many it was offered.

---

## 3. Four results we pre-commit to proving or measuring

### T1 — Attenuation ceiling (proved; measured value plugged in)

For any score $z$ with reliability $\rho_{xx}$ and any external criterion $c$,

$$
|\rho_{zc}^{\text{obs}}| \le \sqrt{\rho_{xx}}.
$$

_Proof._ Classical test theory: $z = \tau + e$ with $\mathrm{Cov}(\tau,e)=0$,
$\rho_{xx} = \sigma_\tau^2/\sigma_z^2$. Then
$\rho_{zc} = \mathrm{Cov}(\tau,c)/(\sigma_z\sigma_c) = \rho_{\tau c}\,\sigma_\tau/\sigma_z
= \rho_{\tau c}\sqrt{\rho_{xx}}$, and $|\rho_{\tau c}| \le 1$. $\blacksquare$

**Consequence we pre-register:** the maximum AUROC any downstream use of this channel can
ever attain is a _fixed function of its reliability and the base rate_, independent of
sample size. Under a binormal model with base rate $p$, invert
$r_{pb} = d/\sqrt{d^2 + 1/(p(1-p))}$ for $d$ and report $\mathrm{AUROC}_{\max} = \Phi(d/\sqrt2)$.
More data cannot move this number. This is what makes the failure _structural_.

### T2 — Calibration futility (proved; empirical run only confirms the implementation)

Let $z$ be the score the pipeline reads and let $g$ be any post-hoc recalibration map — by
definition a function of the score alone.

1. If $g$ is **strictly** increasing then $\mathrm{sign}(g(u)-g(v)) = \mathrm{sign}(u-v)$ for
   all $u,v$, so every indicator in $\hat D$ and $\hat\Rho$ is unchanged:
   $\hat D(g(z)) = \hat D(z)$ and $\hat\Rho(g(z)) = \hat\Rho(z)$ **exactly**. Likewise
   $\mathrm{AUROC}(g(z),c) = \mathrm{AUROC}(z,c)$ exactly.
2. If $g$ is **weakly** increasing (isotonic regression, histogram binning) it can only
   merge previously ordered points into ties, so $\hat\Rho(g(z)) \le \hat\Rho(z)$, and
   $\mathrm{AUROC}(g(z),c) \le \mathrm{AUROC}(z,c)$ whenever the latter is $\ge 0.5$.

Every standard calibration method — Platt/logistic, temperature, beta, isotonic, histogram
binning, quantile mapping — is weakly increasing. **Therefore no standard calibration
method can increase the resolution of a gauge.** It relocates the scale, which reduces ECE,
and that reduction is routinely reported as if the metric had been repaired. $\blacksquare$

This is the sharpest claim in the study and it is analytic: remedy 3 is dead before any data
is collected. The empirical run reports ECE-before/after alongside $\hat\Rho$-before/after
to show the size of the illusion.

### T3 — Aggregation asymptote (proved; asymptote measured with a CI)

Averaging $k$ replicates within a fixed condition reduces only the exchangeable part of the
gauge variance; the condition-locked part $\sigma_{sys}^2 = \sigma_O^2 + \sigma_{IO}^2$
survives untouched:

$$
\rho_k = \frac{\sigma_I^2}{\sigma_I^2 + \sigma_{sys}^2 + \sigma_\varepsilon^2/k},
\qquad
\rho_\infty = \frac{\sigma_I^2}{\sigma_I^2 + \sigma_{sys}^2}.
$$

This is Spearman–Brown with a floor. **If $\rho_\infty$ is below the usability floor, no
sample count fixes the channel**; we report `requiredK` = the $k$ attaining $\rho^\ast$, or
`unreachable`. Note the degenerate case that we expect to observe: if $\sigma_I^2 \approx 0$
then $\rho_\infty \approx 0$ for _every_ aggregation scheme, including wording-averaging,
which does drive $\sigma_{GRR} \to 0$ in the limit but divides a vanishing numerator.
$\blacksquare$

### T4 — Significance without resolution (measured)

For a paired contrast on $I$ items with $k$ measurements each, the minimum detectable
difference at $\alpha=0.05$, power $0.8$ is
$\mathrm{MDE} = (z_{0.975}+z_{0.80})\,\sigma_{GRR}\sqrt{2/(Ik)}$, which $\to 0$ as $Ik$ grows,
**independently of $ndc$**. Statistical significance on this channel is therefore
purchasable with compute and says nothing about whether the channel measures anything.

We demonstrate this directly with a **sham arm**: a token-length-matched, task-irrelevant
context block. The headline statistic is the

$$
\textbf{placebo-dominance ratio} \qquad
\Pi = \frac{\hat\sigma^2_{\text{sham}}}{\hat\sigma^2_{I}},
$$

the variance the channel shows in response to a _known-inert_ manipulation divided by the
variance it shows in response to the thing it purports to measure. $\Pi > 1$ means the
channel responds more strongly to a placebo than to its target. A significant sham effect
co-occurring with $ndc < 2$ is the study's central exhibit: **placebo-controlled claims read
off this channel are uninterpretable, because the channel has no unit in which to state the
effect.**

---

## 4. Locked design constants

| Constant                    | Value                                                                                                                                                                                                   |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Items $I$                   | 48 (24 specs x {correct, seeded-bug}), executable ground truth                                                                                                                                          |
| Wordings $W$                | 8 (`w1..w8`), 2 of which are reverse-keyed                                                                                                                                                              |
| Response scales $S$         | 4 — `p2` (0.00–1.00, 2dp), `pct` (0–100 int), `ten` (0–10 int), `five` (1–5 Likert)                                                                                                                     |
| Replicates $R$              | 8 per cell                                                                                                                                                                                              |
| Temperatures                | $\{0.0, 0.7\}$ — both pre-registered; 0.0 is the "determinism is not reliability" control                                                                                                               |
| Models                      | `qwen2.5-coder:7b` (Q4_K_M), `qwen2.5-coder:7b-instruct-fp16` (F16), `qwen2.5-coder:1.5b`, `qwen2.5:7b`, `qwen2.5:1.5b`, `llama3.1:8b` — 2 families x 2 sizes x 2 arithmetic precisions x coder/general |
| Provenance arms             | `foreign` (model rates bank code it never wrote — this is the LLM-as-judge condition) and `self_authored` (model writes the solution, then rates it)                                                    |
| Intervention arms           | `base`, `sham` (length-matched irrelevant block), `treated` (length-matched genuine prior-failure memo)                                                                                                 |
| Usability floor $\rho^\ast$ | **0.70** (group-level clinimetric standard; 0.90 for individual decisions — we use the _lenient_ one)                                                                                                   |
| Bootstrap                   | 2000 draws, resampling **items** (the unit of generalization), seed 20260728, percentile CI                                                                                                             |
| Multiplicity                | Benjamini–Hochberg FDR at $q=0.05$ across the pre-registered hypothesis family                                                                                                                          |

**Verdict tiers (locked, applied mechanically):**

| Tier              | Rule                                                                                                                                      |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `USABLE`          | $\%GRR \le 30$ **and** $ndc \ge 5$ **and** $ICC \ge 0.70$ **and** $\hat D \ge 0.80$                                                       |
| `MARGINAL`        | $ndc \ge 2$ **and** $ICC \ge 0.50$ **and** $\hat D \ge 0.65$                                                                              |
| `UNINTERPRETABLE` | otherwise — specifically $ndc < 2$ or $\hat D < 0.65$: the channel induces no reliable ordering, so a contrast measured on it has no unit |
| `DEGENERATE`      | $S_{eff} < 2$ — the channel emits fewer than two effective levels                                                                         |

---

## 5. Hypotheses

- **G1-H1 (primary).** Pooled over all facets, the self-report channel scores
  $ndc \le 1$ and $\hat D < 0.65$, i.e. verdict `UNINTERPRETABLE`.
- **G1-H2 (not introspection).** The `foreign` provenance arm is _not better_ than
  `self_authored`: $\hat D_{\text{foreign}} - \hat D_{\text{self}} < 0.10$ with the CI
  excluding a jump to the floor. Establishes the result as a property of elicitation, not
  of self-knowledge, and therefore transfers to LLM-as-judge.
- **G1-H3 (family/size/precision invariance).** No model cell reaches `USABLE`. In
  particular the F16 vs Q4_K_M pair of the _same_ 7B model differs by
  $|\Delta \hat D| < 0.10$: the failure is not a quantization artifact.
- **G1-H4 (temperature horns).** At $T{=}0$, $\sigma_\varepsilon \approx 0$ **and**
  $\sigma_I \approx 0$ and $S_{eff} < 2$; at $T{=}0.7$, $\sigma_\varepsilon \gg \sigma_I$.
  Neither temperature yields $ndc \ge 2$. Determinism does not buy resolution.
- **G1-H5 (all five remedies fail).** Each of {second model, thresholding, calibration,
  wording-averaging, self-consistency} leaves the post-remedy statistic below $\rho^\ast$,
  each reported with its own bootstrap CI. Calibration additionally falsified analytically
  by T2.
- **G1-H6 (placebo dominance).** $\Pi > 1$ with CI excluding 1, and the sham-vs-base
  contrast is significant at $\alpha=0.05$ while the same data scores
  `UNINTERPRETABLE`.

---

## 6. Analysis order (locked, to prevent selection)

1. Parse-failure rate and support audit ($S_{eff}$) — reported before anything else.
2. Pooled ANOVA -> variance components -> `%GRR`, `ndc`, `ICC`, $\hat D$, $\hat\Rho$ (G1-H1).
3. Per-model, per-provenance, per-scale, per-temperature cells (G1-H2, H3, H4).
4. Remedy battery on the _already collected_ cube — no new elicitation (G1-H5).
5. Placebo arm: $\Pi$, contrast, MDE (G1-H6).
6. Gauge cards written for every cell; determinism re-check (byte-identical on re-analysis).

No statistic is computed outside this list. Any exploratory analysis is labelled
`EXPLORATORY` in the results doc and excluded from the claim set.

---

## 7. What would falsify us

We commit to publishing, prominently, any of:

- Any facet cell reaching `USABLE`, or the pooled analysis reaching `MARGINAL`.
- Any of the five remedies lifting the post-remedy statistic to $\rho^\ast = 0.70$ or above.
- $\hat D_{\text{self\_authored}} \ge 0.80$ (would make the channel genuinely introspective
  and confine the failure to LLM-as-judge).
- $\Pi < 1$ with the CI excluding 1 (the channel is more item-sensitive than
  placebo-sensitive, and placebo contrasts would then be merely noisy rather than
  uninterpretable).
- A model cell where `ndc >= 5` — which would make this a model-selection problem, not a
  modality problem.

---

## 8. Scope, honesty, and what this does _not_ claim

- This studies **elicited numeric self-report**, not logit-based or internal-probe
  confidence. Those are different channels and may well be measurement instruments; if
  anything, this study strengthens the case for using them.
- Six open-weight models at 1.5B–8B, run locally. We do **not** claim frontier models
  behave identically; we claim the _method_ applies to them and we ship the tool so that
  anyone can run it in one command.
- A `UNINTERPRETABLE` verdict is a statement about a channel-plus-protocol, not about
  whether the model "has" calibrated internal beliefs.
- Nothing here authorizes training, promotion, or any consciousness-evidence claim. This
  study is measurement methodology and is explicitly outside the Level-0..4 evidence ladder.

---

## 9. Artifacts of record

- Cube: `build/gauge/g1/cube.jsonl` (every raw response text retained).
- Cards: `build/gauge/g1/cards/*.json` validated against `schemas/gauge-card.schema.json`.
- Reproduction: `python -m pneuma_lab.gauge run --config configs/g1.json`.
- Results: `docs/research/experiments/g1-gauge-results.md`, written after the run,
  containing every pre-registered number including those that refute us.
