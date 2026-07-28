# The Gauge Card — a reporting standard for elicited LLM metrics

**Status:** proposed standard, v0.1.0. Schema: `schemas/gauge-card.schema.json`.
Tool: `python -m pneuma_lab.gauge`. Study that motivated it:
`docs/research/experiments/g1-gauge-preregistration.md`.

---

## The one-paragraph version

If a number in your paper was produced by _prompting a model_ — self-reported
confidence, an LLM-as-judge score, an elicited rating, a verbalized probability —
then it is an instrument reading, and instrument readings are not admissible until
someone has shown the instrument can resolve the thing it is pointed at. That
demonstration is a **measurement-system analysis**, it is a variance decomposition
rather than a correlation with truth, and it is **prior to calibration**. A gauge
card is that demonstration in one page. Producing one costs one command and no
new model calls beyond the replicates the design already needs.

## Why this is not already covered by calibration

Calibration answers **validity**: does the reading agree with the truth? ECE,
Brier, reliability diagrams and AUROC are all validity statistics.

Every one of them presumes the reading is a _reading_ — a quantity that would come
out approximately the same if you asked again, or asked in different words, or
asked on a differently-worded scale. That presumption is **reliability**, and it is
a separate measurement property that the ML evaluation literature does not report.

The two are not independent. Reliability _bounds_ validity:

$$
|
ho_{	ext{score},	ext{criterion}}| \;\le\; \sqrt{
ho_{xx}}
$$

so a channel with reliability $0.05$ can never exceed $|\rho| = 0.22$ against any
criterion, at any sample size, forever. If you have not measured $\rho_{xx}$ you do
not know whether your disappointing AUROC is a fact about the model or a fact
about your thermometer.

Two traps this standard is designed to close:

- **Determinism is not reliability.** `temperature=0` makes a broken ruler read
  30 cm every time. Perfect repeatability with zero part variance is _worse_ than
  noise, not better: it is a gauge with one category.
- **Calibration cannot repair reliability.** Post-hoc calibration is by definition
  a function of the score alone, and every standard method (Platt, temperature,
  beta, isotonic, histogram binning) is weakly increasing. Strictly increasing maps
  leave rank-based resolution and AUROC _exactly_ invariant; weakly increasing maps
  can only destroy ordering by creating ties. So a calibrator can lower your ECE
  substantially while changing the instrument's resolution by exactly zero. Papers
  report the ECE drop. The gauge card reports both, side by side, so the gap is
  visible.

## Precedent: every mature measuring field already requires this

| Field                | Requirement                                                                             | Statistic                             |
| -------------------- | --------------------------------------------------------------------------------------- | ------------------------------------- |
| Industrial metrology | AIAG MSA 4th ed., ISO 5725 — gauge R&R study before the gauge is released to production | `%GRR`, `ndc`                         |
| Analytical chemistry | ICH Q2(R2) — precision is validated _before_ accuracy                                   | repeatability, intermediate precision |
| Clinimetrics         | COSMIN — reliability is a distinct, prior measurement property from validity            | ICC, SEM, SDC                         |
| Clinical trials      | Outcome instruments report ICC and minimal detectable change before effect sizes        | ICC(2,1)                              |
| Psychometrics        | Classical test theory — attenuation correction is standard practice                     | Cronbach's alpha, ICC                 |

Machine-learning evaluation is the outlier. This standard is not an innovation in
measurement theory; it is the application of a settled one.

## What a gauge card contains

1. **Channel identity** — model, provenance (did the model author what it is
   rating?), temperature, response scales, wordings, and a digest of the exact
   prompt shape. Cards are comparable only when these match.
2. **Design** — items, conditions, replicates, total observations, parse-failure
   rate, dropped items. A design that cannot identify repeatability is not a card.
3. **Variance decomposition** — item (signal), repeatability, reproducibility,
   gauge (GRR), total. Components whose raw estimate was negative are listed as
   truncated; a truncated item component is a finding, not a footnote.
4. **Resolution** — `%GRR`, `ndc`, `ICC` with CI, discrimination index `D` with CI,
   resolving power, effective support, and the two selection-stability statistics
   below.
5. **Ceilings** — the maximum $|r|$ and AUROC this reliability permits against any
   criterion, at any sample size.
6. **Prescription** — what it would cost to make this channel usable: how many
   replicates or distinct wordings reach the floor, or a statement that the target
   is unreachable at any $k$. A card that only diagnoses is easy to ignore.
7. **Remedies** — the five standard fixes, each re-analysed on the collected data
   with its own error bar, each verdicted `HELPS` / `FAILS` / `INDETERMINATE` /
   `SKIPPED`. Verdicts are decided by the interval, not the point estimate: a CI
   straddling the floor is `INDETERMINATE`, because a remedy that has not been shown
   to work has also not been shown to fail. A remedy that could not be evaluated is
   recorded with a reason; it is never omitted.
8. **Placebo response** — the channel's reaction to a known-inert, length-matched
   context block, reported as the placebo-dominance ratio.
9. **Verdict** plus the literal threshold rule, so nobody has to trust the label.
10. **Reproduction** — the exact command and the data digest.

## The statistics, defined

For item $i$ (random), condition $o$ (random — a wording x scale combination),
replicate $r$:

$$
y_{ior} = \mu + lpha_i + eta_o + (lphaeta)_{io} + arepsilon_{ior}
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

`ndc` is the number of distinct categories the gauge resolves. AIAG requires
$\ge 5$. **$ndc < 2$ means the gauge cannot separate any two items.**

`ndc` degenerates exactly when $\sigma_I \to 0$, so two distribution-free
statistics carry the load:

- **Discrimination index `D`** — probability that two independent measurement
  passes order an item pair the same way, ties scored as coin flips. `D = 1`
  perfect, `D = 0.5` no ordering information, and a constant channel scores
  exactly `0.5`.
- **Resolving power** — the fraction of item pairs on which both passes return the
  _same nonzero_ sign. This is the monotone-safe statistic: strictly increasing
  post-processing leaves it exactly unchanged, weakly increasing post-processing
  can only lower it.
- **Effective support** $S_{eff} = \exp(H)$ — how many levels the channel actually
  emits, regardless of how many it was offered.

Two statistics translate all of that into the decision a pipeline actually makes.
A pipeline does not consume the mean of a confidence channel; it ranks items and
verifies the least-confident fraction $q$. So:

- **Selection stability** — expected Jaccard overlap between the bottom-$q$ sets
  chosen by two independent passes that **re-ask the same question**. Ties are
  broken by per-pass jitter, because that is what a real pipeline does when many
  items report the same number; a stable tie-break would manufacture agreement out
  of the ties themselves. The random-selection floor is $q/(2-q)$.
- **Cross-condition selection stability** — the same overlap when the second pass
  **rephrases** the question instead of re-asking it.

The gap between those two is the practical meaning of the repeatability /
reproducibility split, and it is the single most important pair of numbers on the
card. Setting `temperature=0` can drive the first to nearly 1.0 while leaving the
second untouched — a channel whose _numbers_ reproduce perfectly and whose
_measurement_ does not. Reporting only the first is how a metric passes the only
check most authors run.

## Verdict tiers

| Tier              | Rule                                                          | What it licenses                                                                                     |
| ----------------- | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `USABLE`          | `%GRR <= 30` and `ndc >= 5` and `ICC >= 0.70` and `D >= 0.80` | Report effects measured on this channel.                                                             |
| `MARGINAL`        | `ndc >= 2` and `ICC >= 0.50` and `D >= 0.65`                  | Report with the reliability stated inline and effects disattenuated.                                 |
| `UNINTERPRETABLE` | otherwise (in particular `ndc < 2` or `D < 0.65`)             | Do not report contrasts on this channel. A difference in means is a difference in an undefined unit. |
| `DEGENERATE`      | effective support `< 2`                                       | The channel emits fewer than two levels. Nothing is being measured.                                  |

`UNINTERPRETABLE` is not "underpowered". Underpowered means the effect is real and
the error bar is wide; more data fixes it. `ndc < 2` means the measurement scale
has fewer than two distinguishable levels, so more data buys you a _narrower error
bar around a quantity with no unit_. The minimum detectable effect shrinks like
$\sigma_{GRR}\sqrt{2/(Ik)}$ regardless of resolution, so significance on such a
channel is purchasable with compute and certifies nothing.

## Minimum acceptable design

- **Items** $\ge 30$, spanning the range you care about. Metrology calls these
  reference parts and requires them to span the tolerance band; the analogue is a
  benchmark that contains both easy and hard cases, and ideally items whose truth
  you can establish independently.
- **Replicates** $\ge 5$ per cell. With fewer than 2, repeatability is not
  identifiable and no card can be produced.
- **At least two reproducibility facets.** One is not enough: the most common
  real-world failure is a channel that is stable under resampling and unstable
  under rewording, and a single-facet design cannot see it.
- **Report the parse-failure rate.** Responses your parser rejected are data about
  the channel, not noise to be swept up.

## Using it

```txt
python -m pneuma_lab.gauge selftest                 # validate the estimator itself, offline
python -m pneuma_lab.gauge run --config <cfg.json>  # elicit, analyze, write the card
python -m pneuma_lab.gauge analyze --cube <cube>    # re-analyze existing data, no model calls
```

Exit code `2` on `UNINTERPRETABLE` / `DEGENERATE`, so a CI job can gate on it.

`selftest` matters: a measurement-system-analysis tool that has not itself been
checked against gauges of known ground truth is an unvalidated instrument. The
command simulates four gauges whose variance components are known by construction
and confirms the estimator recovers the correct verdict for each.

## What a card does not say

A card describes **a channel plus a protocol**, not a model. `UNINTERPRETABLE` does
not mean the model lacks internal states, lacks calibrated beliefs, or is bad. It
means _this way of asking_ does not yield a measurement. Logit-based confidence,
internal probes, and ensemble disagreement are different channels and may well card
as `USABLE`; if anything a failing elicited card is an argument for using them.

Nor is a card a licence to skip calibration. It is the step _before_ calibration:
establish that there is a reading, then ask whether the reading is true.

## For reviewers

One line, which an author can satisfy in one command:

> Table N reports an elicited model score. Please include a gauge card (or an
> equivalent measurement-system analysis) reporting `%GRR`, `ndc`, `ICC` and the
> discrimination index for that channel, with the replicate and rewording design
> used to estimate them.

If the answer is that reliability was never estimated, that is the same situation
as a chemistry paper reporting concentrations from an unvalidated assay. The fix is
cheap. The cost of not asking is a literature of significant differences measured
in undefined units.

---

Current implementation and blocker state for this subsystem is tracked in
[docs/project-status.json](project-status.json) under the `pneuma_gauge_msa`
system id.
