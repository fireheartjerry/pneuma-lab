# G-1 Results — the self-report confidence channel as a measurement instrument

**Run:** 2026-07-28. Pre-registration committed at `c42507a` **before** any model call
(`g1-gauge-preregistration.md`). Tool: `pneuma-lab.gauge/0.1.0`. Backend: local Ollama.

**Headline.** The elicited confidence channel is a **real but very low-resolution
instrument**. It carries genuine aggregate signal about correctness — averaged over 56
elicitations it reaches AUROC 0.906, within 0.02 of the hard ceiling its own reliability
implies — while resolving **`ndc = 1`** distinct category, meaning it cannot reliably rank
any two items. The dominant defect is **reproducibility, not repeatability**: setting
temperature to 0 removes 100% of the sampling variance and the channel still fails, because
54% of its total variance comes from _how the question was phrased_.

The channel is also **not suggestible**: a length-matched, task-irrelevant context block does
not move it (p = 0.72) while a genuinely relevant one moves it sharply (p = 2.2e-10). Yet
merely _rephrasing the question_ moves it more than that relevant block does. The channel
**ignores irrelevant content and obeys irrelevant form**.

**Three of our own pre-registered hypotheses were falsified** (H1 partially, H4, H5
partially, H6). They are reported in full below. The finding that survives is not the one we
registered — it is a diagnostic gap in how elicited metrics are validated, which is a larger
claim than the one we set out to test.

---

## 1. What was run

Fractional design; the full factorial would be ~3.5M elicitations. Each stage varies one
facet against a fixed core (`qwen2.5-coder:7b` Q4_K_M, foreign provenance, `base` arm,
`p2` scale, T=0.7). Items are the 48-item reference bank (24 specs x {correct,
seeded-bug}) whose labels are established by **executing** hidden tests, verified 48/48.

| Stage                | Facet varied               | Elicitations |
| -------------------- | -------------------------- | ------------ |
| `core`               | 8 wordings x 8 replicates  | 3,072        |
| `scales`             | 4 response scales          | 2,304        |
| `temperature0`       | T = 0.0                    | 1,536        |
| `placebo`            | base / sham / treated arms | 2,304        |
| `provenance_self`    | model rates its own code   | 768          |
| `provenance_foreign` | matched foreign comparison | 768          |
| `families`           | 5 further models           | 2,880        |
| **Total**            |                            | **13,632**   |

Parse rule is strict and refuses to guess. Non-integral answers on an integer scale are
rejected as scale non-compliance — a choice that is conservative _against_ this study's
thesis, since it discards exactly the responses that would inflate apparent gauge variance.
Parse-failure rate was 0.4% on the core stage.

## 2. Audit: what the channel actually emits

Offered a continuous `0.00`–`1.00` scale, the channel used **35 distinct values** with an
effective support of **6.87 levels**, dominated by a handful:

| value | 1.00 | 0.95 | 0.85 | 0.75 | 0.50 | 0.98 |
| ----- | ---- | ---- | ---- | ---- | ---- | ---- |
| count | 1188 | 829  | 355  | 111  | 106  | 88   |

Mean reported confidence **0.873** against an actual bank accuracy of **0.489**
(ECE = 0.378). On code that passes its hidden tests the channel reports 0.963; on code with
a seeded bug it reports 0.782. The separation is real and it is **0.181**.

## 3. Primary result (G1-H1)

Core stage, 47 items x 8 wordings x 7 replicates = 2,632 retained observations.

| component                 |   variance | share of total |
| ------------------------- | ---------: | -------------: |
| item (signal)             |     0.0262 |          30.1% |
| repeatability             |     0.0221 |          25.4% |
| reproducibility (wording) |     0.0039 |           4.5% |
| **gauge (GRR)**           | **0.0260** |      **69.9%** |

| statistic                        |               value | threshold                                                       |
| -------------------------------- | ------------------: | --------------------------------------------------------------- |
| %GRR                             |               69.9% | AIAG requires <= 30%                                            |
| **ndc**                          |               **1** | AIAG requires >= 5; **< 2 means no two items can be separated** |
| ICC                              |               0.512 | usability floor 0.70                                            |
| discrimination index D           |               0.684 | 0.5 = coin flip on pairwise ordering                            |
| resolving power                  |               0.470 | fraction of item pairs ordered consistently and non-trivially   |
| effective support                |         6.87 levels |                                                                 |
| selection stability (bottom 20%) |               0.568 | random floor 0.111                                              |
| **Verdict**                      | **UNINTERPRETABLE** |                                                                 |

**G1-H1 is partially falsified.** We pre-registered `ndc <= 1` **and** `D < 0.65`.
`ndc = 1` holds; `D = 0.684 > 0.65` does not. The channel is not the coin flip we
predicted — it carries ordering information, just not enough to resolve a second category.

**Validity and its ceiling (T1).** Single-shot AUROC **0.782**; averaged over all 56
elicitations per item, AUROC **0.906**. The ceiling implied by the measured reliability at
this base rate is **0.926**. The observed value sits within 0.02 of it, so the attenuation
bound is not a loose formality here — it is nearly attained, and it is what caps the
channel no matter how much data is collected.

**What the verdict means operationally.** Ask the same model the same question twice and
build the verification queue a pipeline would build — the least-confident 20% — and
**43% of that queue changes** between the two passes.

## 4. Response precision (numerical precision, part 1)

Every response scale, same channel, same items:

| scale            | ndc |   ICC |     D | %GRR | effective support |  mean | verdict         |
| ---------------- | --: | ----: | ----: | ---: | ----------------: | ----: | --------------- |
| `p2` (0.00–1.00) |   1 | 0.567 | 0.697 | 65.8 |              7.23 | 0.843 | UNINTERPRETABLE |
| `pct` (0–100)    |   1 | 0.553 | 0.686 | 66.8 |              5.76 | 0.825 | UNINTERPRETABLE |
| `ten` (0–10)     |   1 | 0.638 | 0.713 | 60.1 |              6.57 | 0.728 | UNINTERPRETABLE |
| `five` (1–5)     |   1 | 0.560 | 0.677 | 66.3 |              3.65 | 0.737 | UNINTERPRETABLE |

The failure is **invariant to response precision**: `ndc = 1` on all four, and offering a
two-decimal scale buys 7.2 effective levels rather than 100.

Note the means. Asking for the _same_ judgement about the _same_ code on a 0–10 scale
rather than a 0.00–1.00 scale moves reported confidence by **0.115**. That is not the model
changing its mind; it is the instrument changing its zero point.

## 5. Determinism is not reliability (G1-H4)

|                                           | T = 0.0 (greedy) |         T = 0.7 |
| ----------------------------------------- | ---------------: | --------------: |
| repeatability variance                    |    **exactly 0** |          0.0158 |
| cells whose replicates are all identical  |   192/192 (100%) |   13/188 (6.9%) |
| item variance                             |           0.0372 |          0.0303 |
| ndc                                       |                2 |               1 |
| ICC                                       |            0.710 |           0.595 |
| D                                         |            0.841 |           0.701 |
| %GRR                                      |             53.9 |            63.7 |
| queue overlap — **same wording re-asked** |        **0.956** |           0.620 |
| queue overlap — **rephrased**             |        **0.646** |           0.672 |
| verdict                                   |         MARGINAL | UNINTERPRETABLE |

**G1-H4 is falsified.** We pre-registered that at T=0 both `sigma_eps` and `sigma_I` would
collapse, effective support would fall below 2, and neither temperature would reach
`ndc >= 2`. In fact greedy decoding is a genuinely effective free remedy: it eliminates
_all_ repeatability variance and lifts the channel from UNINTERPRETABLE to MARGINAL at zero
additional cost.

And it is still not enough, in the way that matters most:

> At T=0 the channel reproduces its own numbers perfectly — re-ask and 96% of the
> verification queue is identical. **Rephrase the question and only 64% is.** Determinism
> bought a reproducible _number_, not a reproducible _measurement_.

This is the study's sharpest practical finding. A `temperature=0` elicited metric looks
airtight under the only check anyone runs (re-run it, get the same answer) while 54% of its
variance is still coming from a prompt-wording choice nobody logged.

## 6. Placebo arm (G1-H6) — falsified, and it matters

| arm       | context block                 |   mean | contrast vs base |           p |
| --------- | ----------------------------- | -----: | ---------------: | ----------: |
| `base`    | none                          | 0.8587 |                — |           — |
| `sham`    | 297 chars, task-irrelevant    | 0.8632 |      **+0.0044** |    **0.72** |
| `treated` | 293 chars, genuinely relevant | 0.7735 |      **-0.0876** | **2.2e-10** |

Placebo-dominance ratio **Pi = 0.000**, CI [0.000, 0.011], against an item variance of 0.041.
The minimum detectable effect at this design is 0.0235, so the study could comfortably have
seen a placebo effect a fifth the size of the treated effect it did detect.

**G1-H6 is falsified.** We pre-registered that the channel would be placebo-dominated. It is
not suggestible at all: irrelevant repository chatter does not move it, and a genuinely
relevant prior-failure memo moves it sharply in the correct direction.

Set against section 4 — where merely rephrasing the question shifts the reading by 0.098,
_more_ than the 0.088 a real prior-failure memo achieves — the precise statement is:

> The channel **ignores irrelevant content and obeys irrelevant form**. It is robust to what
> you put in the prompt and highly sensitive to how you ask the question.

This is a strong positive control for the whole apparatus, and it relocates the finding: the
failure is metrological, not credulity. The same stage's base arm scores `ndc = 1`,
ICC 0.549, D 0.690, `UNINTERPRETABLE`.

## 7. Provenance — is this about introspection? (G1-H2)

_Pending._

## 8. Model families, sizes, and arithmetic precision (G1-H3)

_Pending._

## 9. The five remedies (G1-H5)

_Pending final numbers; the analytic result for calibration is already fixed._

## 10. Deviations from pre-registration

_Pending._

## 11. Caveats

_Pending._
