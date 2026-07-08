# E-0 Results — FAIL (pre-registered null, published in full)

**Run:** 2026-07-07, commit `cf014b7` (pre-registration committed before the
run; `build/e0/report.json` is the artifact of record). Verdict: **FAIL** on
all three pre-registered hypotheses. Per the pre-registration, this is an
informative result, not a setback to be buried: it kills the "hand-coded
appraisal transfers across agents" shortcut with a very large effect and
redirects effort to learned estimators (doc 08), exactly as pre-committed.

## Numbers

- Corpus: 6,018 replayed (37 excluded by pre-registered label QC:
  `error_eval`/`test_timeout`; 0 bridge skips). Determinism gate: every trace
  byte-identical across two replays. Runtime ~61 s.
- Split: dev 2,877 / eval 3,141 (repo-grouped; eval = 4 repo groups —
  cluster count is small, a caveat on generalization). Eval: 2,885 failures,
  256 successes.

| prefix t | AUROC s_vp | AUROC s_instinct | AUROC b1 (max retry) |
| -------- | ---------- | ---------------- | -------------------- |
| 3        | 0.493      | 0.460            | 0.663                |
| 5        | 0.438      | 0.428            | 0.704                |
| 10       | **0.339**  | **0.349**        | **0.705**            |

- H1 (s_vp beats retry heuristic by ≥ 0.02): **FAIL** — delta = −0.367,
  DeLong z = −16.0. Not close.
- H2 (instinct AUROC ≥ 0.54): **FAIL** — 0.349.
- H3 (signal survives retry stratification > 0.52): **FAIL** — 0.355 across
  5 strata (n = 3,124).

## What the inversion means (hypothesis, not conclusion)

Both psyche signals are strongly **anti**-correlated with failure, and the
anti-correlation grows with prefix length. The dominant plausible mechanism is
a **length/activity confound in this corpus**: a large share of unresolved
OpenHands runs fail by early termination / empty generation (few steps, few
tool events), so cumulative signals (s_vp is a sum; instinct fires on events)
are small precisely on failures, while long, busy, error-marker-dense runs are
the ones actively debugging — and disproportionately succeed. `b1` (max retry)
escapes the confound because a single repeated call is informative regardless
of trace length.

This confound was foreseeable (doc 08 pre-registered a no-length-features
ablation for E1 for exactly this reason) but E-0's signals were pre-registered
as raw sums/means, so the result stands as a FAIL. No post-hoc sign-flip is
claimed: "1 − AUROC = 0.66" would be fitting on the eval set.

## What this licenses / redirects

1. **No promotion.** P1 is not unlocked. No claim that replayed
   ReferencePsyche signals carry transferable predictive information.
2. **ReferencePsyche appraisal does not transfer** from its design
   distribution (9to5-shaped failure motifs) to OpenHands/SWE-Gym trajectories
   in raw form. Recorded as a boundary on the toy psyche's validity — further
   evidence that all its Level-4 results are harness-internal methodology
   validation only.
3. **Retry-count is the baseline to beat**: AUROC 0.705 at t=10 from one
   observable integer. E1's real bar is not 0.65; it is "materially above
   0.705 with the length-confound ablation reported."
4. **The learned-estimator path (E1/E2) is now the main line**, with explicit
   length-normalized and length-free feature sets. The failure-mode taxonomy
   (empty-generation vs active-failure) should become a labeled stratum in the
   next experiment's pre-registration (E-1): predicting _active_ failures
   separately from _abandonment_ failures.
5. **Bridge + harness + determinism machinery worked flawlessly at corpus
   scale** (6,018 × 2 replays, byte-identical, one minute) — the
   infrastructure result stands independent of the hypothesis result.

## Caveats

Eval split = 4 repo clusters (repo-grouped hashing on a corpus dominated by a
few big repos); base rate 91.9% failures; `resolved` is the SWE-Gym harness
label; signals computed from a psyche with no memory frames (within-run
anomaly learning only). All pre-declared in the pre-registration.
