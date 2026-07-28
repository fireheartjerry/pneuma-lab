# Self-Report Gauge Study (G-1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a dependency-free measurement-system-analysis (MSA) toolkit that decides
whether an _elicited_ LLM metric (self-reported confidence, LLM-as-judge score, elicited
eval rating) is a measurement instrument at all — plus the placebo-controlled study that
runs it on six local models and falsifies all five standard remedies.

**Architecture:** A `ResponseCube` (item x condition x replicate) is the single data
structure. Every statistic is a pure function of the cube: crossed random-effects ANOVA
gives variance components; resolution statistics (`%GRR`, `ndc`, `ICC`, discrimination
index `D`, effective support `S_eff`) are derived from those; theory functions convert
reliability into hard ceilings on achievable validity; the five remedies are _re-analyses
of the same cube_, so falsifying them costs zero extra model calls. A `GaugeCard` is the
schema-validated reporting artifact. Elicitation is behind an injectable `generate` seam
so every test runs offline.

**Tech Stack:** Python 3.12, stdlib only for all math (no numpy/scipy — determinism and a
one-command install matter more than speed), `jsonschema` for card validation (already a
repo dependency), local Ollama over `urllib` for elicitation (pattern copied from
`src/pneuma_lab/voice/ollama.py`).

**Non-negotiable repo invariants this plan inherits:** 4-space indent everywhere; no new
heavy dependencies; conservative claims; pre-registration committed before any run;
determinism (fixed seeds, sorted iteration, byte-stable artifacts).

---

## File Structure

| File                                                    | Responsibility                                                                                                     |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `schemas/gauge-card.schema.json`                        | The reporting standard. Draft 2020-12, `x-pneuma-schema-kind: gauge_card`.                                         |
| `src/pneuma_lab/gauge/cube.py`                          | `Response`, `ResponseCube`; JSONL IO; facet slicing/collapsing.                                                    |
| `src/pneuma_lab/gauge/stats.py`                         | stdlib numerics: mean/var, `normalCdf`, `normalQuantile`, deterministic bootstrap, percentile CI, Shannon entropy. |
| `src/pneuma_lab/gauge/anova.py`                         | Crossed two-way random-effects ANOVA with replication -> `VarianceComponents`.                                     |
| `src/pneuma_lab/gauge/resolution.py`                    | `%GRR`, `ndc`, `ICC`, discrimination index `D`, effective support `S_eff`, verdict rule.                           |
| `src/pneuma_lab/gauge/theory.py`                        | T1 attenuation ceiling, AUROC ceiling, T3 Spearman-Brown asymptote + required-`k`, MDE.                            |
| `src/pneuma_lab/gauge/remedies.py`                      | The five remedies, each returning a post-remedy statistic + CI + verdict.                                          |
| `src/pneuma_lab/gauge/placebo.py`                       | Sham-arm contrast, placebo-dominance ratio `Pi`, significance-without-resolution demo.                             |
| `src/pneuma_lab/gauge/items.py`                         | Item bank loader; hidden-test execution for ground truth (subprocess, timeout).                                    |
| `src/pneuma_lab/gauge/elicit.py`                        | Wordings, response scales, prompt construction, parse, threaded runner.                                            |
| `src/pneuma_lab/gauge/card.py`                          | Assemble + validate + write `gauge_card.json` / `gauge_card.md`.                                                   |
| `src/pneuma_lab/gauge/__main__.py`                      | One command: `python -m pneuma_lab.gauge`. Subcommands `run`, `analyze`, `card`, `selftest`.                       |
| `fixtures/gauge/item_bank.jsonl`                        | 48 reference items (24 specs x {correct, seeded-bug}) with hidden tests.                                           |
| `docs/research/experiments/g1-gauge-preregistration.md` | Locked hypotheses, constants, thresholds. Committed BEFORE the run.                                                |
| `docs/research/experiments/g1-gauge-results.md`         | Numbers + verdict, written after.                                                                                  |
| `docs/gauge-card-standard.md`                           | The reporting standard, aimed at reviewers/other labs.                                                             |

Tests mirror source: `tests/test_gauge_{cube,stats,anova,resolution,theory,remedies,placebo,items,elicit,card,cli}.py`.

---

### Task 1: Statistics primitives (`stats.py`)

**Files:** Create `src/pneuma_lab/gauge/stats.py`, `tests/test_gauge_stats.py`.

- [ ] **Step 1: Write failing tests**

```python
from pneuma_lab.gauge.stats import normalCdf, normalQuantile, bootstrapCi, shannonEntropy

def test_normal_cdf_known_points():
    assert abs(normalCdf(0.0) - 0.5) < 1e-12
    assert abs(normalCdf(1.959963985) - 0.975) < 1e-6

def test_normal_quantile_roundtrip():
    for p in (0.01, 0.25, 0.5, 0.75, 0.99):
        assert abs(normalCdf(normalQuantile(p)) - p) < 1e-6

def test_bootstrap_ci_is_deterministic_and_brackets():
    xs = [float(i) for i in range(100)]
    a = bootstrapCi(xs, lambda s: sum(s) / len(s), draws=500, seed=11)
    b = bootstrapCi(xs, lambda s: sum(s) / len(s), draws=500, seed=11)
    assert a == b
    assert a.low < 49.5 < a.high

def test_shannon_entropy_of_uniform_three():
    import math
    assert abs(shannonEntropy([1, 1, 1]) - math.log(3)) < 1e-12
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_gauge_stats.py -q`, expect ImportError.

- [ ] **Step 3: Implement.** `normalCdf(x) = 0.5 * erfc(-x / sqrt(2))` via `math.erfc`.
      `normalQuantile` = Acklam rational approximation refined by one Halley step against
      `normalCdf` (accuracy < 1e-9). `bootstrapCi` uses `random.Random(seed)` and
      `sorted` percentile interpolation, returning a frozen `Interval(low, high, point)`.
      `shannonEntropy(counts)` returns natural-log entropy, ignoring zero counts.

- [ ] **Step 4: Run tests** — expect PASS.
- [ ] **Step 5: Commit** — `feat(gauge): stdlib statistics primitives`.

---

### Task 2: Response cube (`cube.py`)

**Files:** Create `src/pneuma_lab/gauge/cube.py`, `tests/test_gauge_cube.py`.

`Response` is a frozen dataclass with fields:
`item_id: str`, `model: str`, `wording_id: str`, `scale_id: str`, `provenance: str`
(`"foreign" | "self_authored"`), `arm: str` (`"base" | "sham" | "treated"`),
`temperature: float`, `replicate: int`, `raw_text: str`, `value: float | None`,
`parse_ok: bool`.

`ResponseCube` holds `tuple[Response, ...]`, plus:

- `fromJsonl(path)` / `toJsonl(path)` — sorted by
  `(item_id, model, scale_id, wording_id, arm, provenance, replicate)` so files are byte-stable.
- `filter(**facets)` -> new cube.
- `conditionKey(response, facets)` -> tuple; `conditionIds(facets)` -> sorted list.
- `matrix(condition_facets)` -> `dict[(item_id, condition_key)] -> list[float]`, dropping
  `parse_ok=False` rows and recording `parse_failure_rate`.
- `balancedMatrix(...)` -> truncates every cell to the minimum common replicate count and
  drops items/conditions with an empty cell, so ANOVA sees a balanced design; returns
  `(matrix, n_items, n_conditions, n_reps, dropped)`.

- [ ] **Step 1: Failing tests** — build a 2-item x 2-condition x 2-replicate cube in code;
      assert `toJsonl` then `fromJsonl` round-trips byte-identically; assert
      `balancedMatrix` truncates a 3-replicate cell to 2 and reports `dropped == 0`;
      assert a `parse_ok=False` row is excluded and raises the failure rate.
- [ ] **Step 2: Run, expect fail.**
- [ ] **Step 3: Implement as above.**
- [ ] **Step 4: Run, expect pass.**
- [ ] **Step 5: Commit** — `feat(gauge): response cube + byte-stable JSONL IO`.

---

### Task 3: Variance components (`anova.py`)

**Files:** Create `src/pneuma_lab/gauge/anova.py`, `tests/test_gauge_anova.py`.

Model, for item $i \in 1..I$ (random), condition $o \in 1..O$ (random), replicate $r \in 1..R$:

$$
y_{ior} = \mu + lpha_i + eta_o + (lphaeta)_{io} + arepsilon_{ior}
$$

Mean squares (balanced design):

$$
MS_{I} = \frac{OR}{I-1}\sum_i (\bar y_{i..} - \bar y)^2, \quad
   MS_{O} = \frac{IR}{O-1}\sum_o (\bar y_{.o.} - \bar y)^2
$$

$$
MS_{IO} = \frac{R}{(I-1)(O-1)}\sum_{i,o} (\bar y_{io.} - \bar y_{i..} - \bar y_{.o.} + \bar y)^2, \quad
   MS_{E} = \frac{\sum_{i,o,r}(y_{ior} - \bar y_{io.})^2}{IO(R-1)}
$$

Components (AIAG ANOVA method, negatives truncated to 0 with a recorded flag):

$$
\hat\sigma^2_{\varepsilon} = MS_E, \quad
   \hat\sigma^2_{IO} = \frac{MS_{IO} - MS_E}{R}, \quad
   \hat\sigma^2_{O} = \frac{MS_O - MS_{IO}}{IR}, \quad
   \hat\sigma^2_{I} = \frac{MS_I - MS_{IO}}{OR}
$$

$$
\sigma^2_{GRR} = \hat\sigma^2_{\varepsilon} + \hat\sigma^2_{O} + \hat\sigma^2_{IO}, \quad
   \sigma^2_{tot} = \hat\sigma^2_{I} + \sigma^2_{GRR}
$$

`VarianceComponents` is a frozen dataclass carrying every term, `n_items`, `n_conditions`,
`n_reps`, and `truncated: tuple[str, ...]`.

- [ ] **Step 1: Failing test — recover known ground truth.** This is the metrological
      validation of our own estimator; it must exist before any real data.

```python
import random
from pneuma_lab.gauge.anova import varianceComponents

def _synthesize(sd_item, sd_cond, sd_inter, sd_err, n_items=40, n_cond=6, n_reps=8, seed=3):
    rng = random.Random(seed)
    a = [rng.gauss(0, sd_item) for _ in range(n_items)]
    b = [rng.gauss(0, sd_cond) for _ in range(n_cond)]
    ab = [[rng.gauss(0, sd_inter) for _ in range(n_cond)] for _ in range(n_items)]
    m = {}
    for i in range(n_items):
        for o in range(n_cond):
            m[(f"i{i}", f"c{o}")] = [
                a[i] + b[o] + ab[i][o] + rng.gauss(0, sd_err) for _ in range(n_reps)
            ]
    return m

def test_recovers_known_variance_components():
    vc = varianceComponents(_synthesize(0.30, 0.10, 0.05, 0.20))
    assert abs(vc.sd_item - 0.30) < 0.06
    assert abs(vc.sd_repeatability - 0.20) < 0.02
    assert abs(vc.sd_condition - 0.10) < 0.06

def test_zero_item_variance_is_detected():
    vc = varianceComponents(_synthesize(0.0, 0.05, 0.02, 0.20))
    assert vc.sd_item < 0.05
    assert "sigma2_item" in vc.truncated or vc.var_item < 2.5e-3
```

- [ ] **Step 2: Run, expect fail.**
- [ ] **Step 3: Implement the formulas above.** Raise `ValueError` when `R < 2`
      (repeatability unidentifiable) or `I < 2` or `O < 2`.
- [ ] **Step 4: Run, expect pass.**
- [ ] **Step 5: Commit** — `feat(gauge): crossed random-effects variance components`.

---

### Task 4: Resolution statistics (`resolution.py`)

**Files:** Create `src/pneuma_lab/gauge/resolution.py`, `tests/test_gauge_resolution.py`.

From `VarianceComponents`:

$$
\%GRR = 100\,\frac{\sigma_{GRR}}{\sigma_{tot}}, \qquad
   ndc = \left\lfloor 1.41\,\frac{\sigma_{I}}{\sigma_{GRR}} \right\rfloor, \qquad
   ICC = \frac{\sigma^2_I}{\sigma^2_{tot}}
$$

Two statistics that stay defined when $\sigma_I \to 0$ (where `ndc` degenerates):

**Discrimination index** `D` — the probability that two independent measurement passes
order the same item pair the same way, ties counted as 0.5:

$$
D = \operatorname{mean}_{i 
eq j}\; \Pr\!ig[\operatorname{sign}(y^{(a)}_i - y^{(a)}_j)
   = \operatorname{sign}(y^{(b)}_i - y^{(b)}_j)\big]
$$

Estimated by splitting each item's replicates into two disjoint halves (pass $a$ = even
replicate indices, pass $b$ = odd), averaging within half, then averaging sign agreement
over all $\binom{I}{2}$ pairs. `D = 1` is a perfect gauge; `D = 0.5` is a coin flip.

**Effective support** `S_eff` — perplexity of the empirical distribution of distinct
reported values, $S_{eff} = \exp(H)$. Measures how many levels the channel actually emits.

`gaugeVerdict(...)` applies the pre-registered thresholds (Task 12 doc):
`USABLE` iff `%GRR <= 30 and ndc >= 5 and ICC >= 0.70 and D >= 0.80`;
`MARGINAL` iff `ndc >= 2 and ICC >= 0.50 and D >= 0.65`; else `UNINTERPRETABLE`.

- [ ] **Step 1: Failing tests** — a perfect gauge (`sd_err=0.001`, `sd_item=0.3`) gives
      `ndc >= 5`, `D > 0.95`, verdict `USABLE`; a pure-noise gauge (`sd_item=0.0`) gives
      `ndc == 0`, `abs(D - 0.5) < 0.08`, verdict `UNINTERPRETABLE`; a degenerate constant
      channel (every value `0.95`) gives `S_eff == 1.0` and verdict `UNINTERPRETABLE`.
- [ ] **Step 2: Run, expect fail.** - [ ] **Step 3: Implement.** - [ ] **Step 4: Run, expect pass.**
- [ ] **Step 5: Commit** — `feat(gauge): resolution statistics and verdict rule`.

---

### Task 5: Theory ceilings (`theory.py`)

**Files:** Create `src/pneuma_lab/gauge/theory.py`, `tests/test_gauge_theory.py`.

- **T1 attenuation ceiling.** For reliability $\rho_{xx}$, any observed correlation with
  any external criterion obeys $|\rho_{xy}| \le \sqrt{\rho_{xx}}$.
  `validityCeiling(icc) -> sqrt(max(icc, 0))`.
- **AUROC ceiling.** Under a binormal model with base rate $p$, invert the point-biserial
  relation $r_{pb} = d / \sqrt{d^2 + 1/(p(1-p))}$ for $d$, then
  $AUROC = \Phi(d/\sqrt{2})$. `aurocCeiling(icc, base_rate)`. Assumptions recorded in the
  returned dataclass so the card can print them.
- **T3 aggregation asymptote.** Averaging $k$ exchangeable replicates within a fixed
  condition leaves condition-locked variance untouched:

    $$
    \rho_k = \frac{\sigma^2_I}{\sigma^2_I + \sigma^2_{sys} + \sigma^2_{exch}/k},
       \qquad \rho_\infty = \frac{\sigma^2_I}{\sigma^2_I + \sigma^2_{sys}}
    $$

    `aggregationCurve(vc, systematic, exchangeable, ks)` and `requiredK(vc, target=0.70)`
    returning `None` when $\rho_\infty <$ target (i.e. unreachable at any $k$).

- **T4 MDE.** Minimum detectable paired difference at power 0.8, alpha 0.05:
  $MDE = (z_{0.975} + z_{0.80})\,\sigma_{GRR}\sqrt{2/(I k)}$. Shows how a channel with no
  resolution still yields significant contrasts as $I k$ grows.

- [ ] **Step 1: Failing tests** — `validityCeiling(0.04) == 0.2`;
      `aurocCeiling(1.0, 0.5) > 0.99`; `aurocCeiling(0.0, 0.5) == 0.5`;
      monotone in `icc`; `requiredK` returns `None` when `rho_inf < target` and returns the
      analytic $k$ when reachable; `aggregationCurve` is nondecreasing in `k` and
      converges to `rho_inf` within 1e-6 at `k=10**6`.
- [ ] **Step 2-4: red, implement, green.**
- [ ] **Step 5: Commit** — `feat(gauge): reliability-to-validity ceilings`.

---

### Task 6: The five remedies (`remedies.py`)

**Files:** Create `src/pneuma_lab/gauge/remedies.py`, `tests/test_gauge_remedies.py`.

Each remedy returns a `RemedyResult(name, statistic, value, ci, baseline, verdict, note)`
where `verdict in {"FAILS", "HELPS"}` decided against the pre-registered floor
(`D >= 0.80` / `ICC >= 0.70`). All five read the _same_ cube — no extra model calls.

1. **`secondModel(cube, judge_model)`** — replace the self-report condition with a second
   model's rating of the same items. Statistic: `ICC` and `D` of the second model, plus
   cross-model agreement `ICC(2,1)` treating models as raters. A second gauge with its own
   `sigma_GRR` adds reproducibility variance; the falsification is that pooled `D` does not
   exceed the floor.
2. **`thresholding(cube, cuts)`** — binarize at each cut. Statistic: Cohen's `kappa`
   between the two split-half passes, plus the near-cut flip rate. Sweep cuts over the
   observed support; report the best cut (a generous, adversarial-to-us choice).
3. **`calibration(cube, truth)`** — fit Platt and isotonic on a held-out half; report
   `ECE` before/after AND `D`/`AUROC` before/after. **T2 (proved in the pre-registration):
   any strictly monotone map leaves `D` and `AUROC` exactly invariant; weakly monotone maps
   (isotonic, histogram binning) can only lower them by creating ties.** The test asserts
   invariance to machine precision — this remedy is falsified analytically and the empirical
   run only confirms the implementation.
4. **`wordingAveraging(cube)`** — average over wordings. Statistic: `ICC` of the
   wording-averaged score, plus the asymptote `rho_inf` from Task 5 and `requiredK`.
5. **`selfConsistency(cube, ks)`** — average `k` replicates within a fixed condition.
   Statistic: `ICC` vs `k` curve, its asymptote, and `requiredK`.

- [ ] **Step 1: Failing tests.** Key ones:

```python
def test_monotone_calibration_leaves_discrimination_exactly_invariant():
    # T2: strictly monotone g => D(g(y)) == D(y) exactly
    base = _cube_from_matrix(...)
    d0 = discriminationIndex(base)
    for g in (lambda v: 1 / (1 + math.exp(-6 * (v - 0.5))), lambda v: v ** 3):
        assert discriminationIndex(_apply(base, g)) == d0

def test_isotonic_can_only_lose_ordering():
    assert discriminationIndex(_apply(base, _isotonicFit(base, truth))) <= d0 + 1e-12

def test_self_consistency_asymptote_below_floor_when_item_variance_is_zero():
    r = selfConsistency(_zero_item_cube(), ks=(1, 2, 4, 8, 16))
    assert r.value < 0.70 and r.verdict == "FAILS"
    assert r.note.startswith("rho_inf=")
```

- [ ] **Step 2-4: red, implement, green.**
- [ ] **Step 5: Commit** — `feat(gauge): five-remedy falsification battery`.

---

### Task 7: Placebo arm (`placebo.py`)

**Files:** Create `src/pneuma_lab/gauge/placebo.py`, `tests/test_gauge_placebo.py`.

**Placebo-dominance ratio** — the headline number:

$$
\Pi = rac{\hat\sigma^2_{	ext{sham}}}{\hat\sigma^2_{	ext{item}}}
$$

where $\hat\sigma^2_{\text{sham}}$ is the variance the channel shows in response to a
_known-inert_ prompt manipulation (a token-length-matched irrelevant context block) and
$\hat\sigma^2_{\text{item}}$ is the variance it shows in response to the thing it claims to
measure. $\Pi > 1$ means the channel is more sensitive to a placebo than to its target.

Also `placeboContrast(cube)` -> paired bootstrap + paired `t` on the sham-vs-base mean
difference, so the results doc can state "significant placebo effect at `p = ...` on a
channel with `ndc = ...`" — significance and resolution are independent, which is the
point of T4.

- [ ] **Step 1: Failing tests** — a synthetic channel with zero item variance and a
      +0.05 sham shift yields `Pi > 1`, a significant contrast at `I=48, k=8`, and
      `verdict == "UNINTERPRETABLE"` from Task 4 on the same data.
- [ ] **Step 2-4: red, implement, green.** - [ ] **Step 5: Commit** — `feat(gauge): placebo-dominance ratio`.

---

### Task 8: Item bank (`items.py`, `fixtures/gauge/item_bank.jsonl`)

**Files:** Create `src/pneuma_lab/gauge/items.py`, `fixtures/gauge/item_bank.jsonl`,
`tests/test_gauge_items.py`.

24 short Python specs (pure functions: `median`, `binarySearch`, `runLengthEncode`,
`balancedBrackets`, `romanToInt`, `mergeIntervals`, ...). Each ships:
`spec_id`, `signature`, `docstring`, a `correct` implementation, a `buggy` implementation
with a single seeded fault, `fault_class` (off-by-one / wrong-branch / mutation / edge-case
/ wrong-operator), and `hidden_tests` (list of `(args, expected)` pairs, >= 5, at least one
exercising the seeded fault). 24 x 2 = **48 reference items** spanning the full range of
true correctness, exactly as metrology requires reference parts to span the tolerance band.

`runHiddenTests(source, tests, timeout=5.0)` executes in a **subprocess** with a hard
timeout and a minimal environment, returning `(passed: bool, detail: str)`. It is used to
(a) verify every bank item's label at test time and (b) label model-authored solutions in
the self-authored provenance arm.

- [ ] **Step 1: Failing tests** — every `correct` item passes its hidden tests; every
      `buggy` item fails at least one; `fault_class` values are from the closed set; the
      bank has exactly 48 items and 24 distinct specs; a deliberate infinite loop is killed
      by the timeout and reported as `passed=False` rather than hanging.
- [ ] **Step 2-4: red, author the bank, green.**
- [ ] **Step 5: Commit** — `feat(gauge): 48-item reference bank with executable ground truth`.

---

### Task 9: Elicitation (`elicit.py`)

**Files:** Create `src/pneuma_lab/gauge/elicit.py`, `tests/test_gauge_elicit.py`.

- `WORDINGS`: 8 paraphrases of the confidence question, ids `w1..w8`, spanning
  first-person/third-person, "confident it is correct" / "probability it passes the hidden
  tests" / "chance a reviewer finds a bug" (reverse-keyed, parsed then flipped), etc.
  Reverse-keyed wordings are marked `reverse=True` and inverted at parse time — this is
  itself a reproducibility probe.
- `SCALES`: 4 response scales — `p2` (0.00-1.00, two decimals), `pct` (0-100 integer),
  `ten` (0-10 integer), `five` (1-5 Likert) — each with its own parse + normalization to
  [0,1]. This is the response-precision axis.
- `SHAM_BLOCK`: a token-length-matched, task-irrelevant context block (a fixed lorem-style
  changelog) used for the placebo arm; `TREATED_BLOCK` is the matched-length real
  intervention (a genuine prior-failure memo about the same spec).
- `buildPrompt(item, wording, scale, arm, provenance) -> str`, deterministic; the prompt
  hash goes on the gauge card.
- `parseValue(text, scale) -> float | None` — strict: first numeric token in range, else
  `None` with `parse_ok=False`. Never guesses.
- `elicit(items, models, wordings, scales, arms, reps, generate, workers=8, seed) ->
ResponseCube` — a `ThreadPoolExecutor` over a _deterministically ordered_ job list, with
  one distinct `seed` per (item, model, wording, scale, arm, replicate) so the run is
  reproducible; jobs are grouped by model and executed model-by-model (a single Ollama
  server thrashes when two models interleave).

- [ ] **Step 1: Failing tests** — with a stub `generate` returning `"0.85"`, `elicit`
      produces exactly `len(items)*len(models)*len(wordings)*len(scales)*len(arms)*reps`
      responses; reverse-keyed wordings invert; each scale parses and normalizes its own
      format; `"I'm not sure"` yields `parse_ok=False`; the same call twice with the same
      seed yields an identical cube; job order is grouped by model.
- [ ] **Step 2-4: red, implement, green.**
- [ ] **Step 5: Commit** — `feat(gauge): elicitation runner with wording/scale/arm facets`.

---

### Task 10: Gauge card (`schemas/gauge-card.schema.json`, `card.py`)

**Files:** Create `schemas/gauge-card.schema.json`, `src/pneuma_lab/gauge/card.py`,
`tests/test_gauge_card.py`; modify `src/pneuma_lab/schemas/__init__.py` to register the
new schema.

Card sections (all required): `channel` (model, prompt digest, scale, temperature,
decoding), `design` (n_items, facets, replicates, total_calls, parse_failure_rate),
`variance_components` (each with CI), `resolution` (`pct_grr`, `ndc`, `icc`, `d`, `s_eff`,
each with CI), `ceilings` (`validity_r`, `auroc`, assumptions), `remedies` (5 entries),
`placebo` (`pi`, contrast, p-value), `verdict`, `reproduction` (command + digests).

- [ ] **Step 1: Failing tests** — a card built from a synthetic cube validates against the
      schema; a card missing `remedies` fails validation; `gauge_card.json` is byte-stable
      across two builds from the same cube; the Markdown rendering contains the verdict
      string and every remedy verdict.
- [ ] **Step 2-4: red, implement, green.**
- [ ] **Step 5: Commit** — `feat(gauge): gauge-card schema and writer`.

---

### Task 11: One command (`__main__.py`)

**Files:** Create `src/pneuma_lab/gauge/__main__.py`, `tests/test_gauge_cli.py`.

```txt
python -m pneuma_lab.gauge selftest          # estimator validation on synthetic cubes, offline
python -m pneuma_lab.gauge run    --config <json> --out build/gauge/<run>/
python -m pneuma_lab.gauge analyze --cube build/gauge/<run>/cube.jsonl --out ...
python -m pneuma_lab.gauge card   --analysis ... --out gauge_card.{json,md}
```

`run` does all three by default. Exit code 0 = card written; 2 = `UNINTERPRETABLE` verdict
(so CI can gate on it); 1 = error.

- [ ] **Step 1: Failing test** — `selftest` exits 0 offline; `analyze` on a fixture cube
      writes a schema-valid card and exits 2 with verdict `UNINTERPRETABLE`.
- [ ] **Step 2-4: red, implement, green.** - [ ] **Step 5: Commit** — `feat(gauge): one-command CLI`.

---

### Task 12: Pre-registration (docs), committed BEFORE any real run

**Files:** Create `docs/research/experiments/g1-gauge-preregistration.md`.

Locks: hypotheses G1-H1..H6, the four verdict thresholds, the usability floor `rho* = 0.70`,
`I = 48`, `W = 8`, `S = 4`, `R = 8`, `T in {0.0, 0.7}`, the six models, the two provenance
arms, the three intervention arms, the analysis order, and the T1-T4 proofs. States what
would falsify _our_ claim (any cell reaching `USABLE`, or any remedy reaching the floor).

- [ ] **Step 1: Write it.** - [ ] **Step 2: Commit before running** — `docs(gauge): pre-register G-1`.

---

### Task 13: Execute the study

- [ ] Run `python -m pneuma_lab.gauge run --config configs/g1.json` model-by-model.
- [ ] Verify determinism: re-analyze the cube twice, assert byte-identical cards.
- [ ] Write `docs/research/experiments/g1-gauge-results.md` with every number and CI,
      including any cell that came out `USABLE` (publish failures of our own thesis).

---

### Task 14: The standard

**Files:** Create `docs/gauge-card-standard.md`; modify `README.md` and
`docs/project-status.json`.

The reviewer-facing document: what a gauge card is, the four verdict tiers, the minimum
design (`I >= 30`, `R >= 5`, at least two reproducibility facets), the precedent
(AIAG MSA / ISO 5725 industrial metrology, ICH Q2(R2) analytical validation, COSMIN
clinimetrics, ICC reporting in clinical trials), and the one-line command a reviewer can
ask an author to run.

- [ ] **Step 1: Write it.** - [ ] **Step 2: Commit** — `docs(gauge): gauge-card reporting standard`.

---

## Self-Review

**Spec coverage:** placebo-controlled study (Tasks 7, 13) / model families (Task 9 `models`
facet) / self-authored vs foreign (Task 9 `provenance`) / numerical precisions (Task 9
`SCALES` for the response scale, and the `fp16` vs `Q4_K_M` model pair for the arithmetic
precision) / five remedies each with an error bar (Task 6) / one-command tool (Task 11) /
gauge-card standard (Tasks 10, 14) / extension to LLM-as-judge (Task 6 remedy 1 + the
foreign-provenance arm, which _is_ an LLM-as-judge setup).

**Placeholder scan:** every formula is written out; every test has a body; no "TBD".

**Type consistency:** `VarianceComponents` (Task 3) is consumed by Tasks 4, 5, 6, 7, 10 with
the same field names (`var_item`, `sd_item`, `var_repeatability`, `sd_repeatability`,
`var_condition`, `var_interaction`, `var_grr`, `sd_grr`, `var_total`, `sd_total`,
`truncated`). `Interval(low, high, point)` from Task 1 is the single CI type everywhere.
`ResponseCube` (Task 2) is the single input type for Tasks 4, 6, 7, 10.
