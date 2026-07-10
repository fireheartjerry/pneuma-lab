# PneumaBrain-v0.1 Robustness & Strength Addendum

> Extends `2026-07-10-pneuma-brain-v0-1-trainer.md`. The base plan builds a
> deterministic multi-task framework and trains one plain logistic RISK head.
> This addendum turns that into an **elite, trustworthy** v0.1: class-imbalance
> handling, calibration, honest cross-validated generalization with confidence
> intervals, model selection over a small family, and conservative proxy heads.
> It changes nothing about the gates: offline, advisory-only, no runtime
> integration, no consciousness claim.

**Why this exists:** The D1 corpus is 91.9% failure and split across only 11
repos. A single repo-grouped split can be lucky or unlucky, and a naive logistic
will lean on the majority class. "Strong" here means _validated and calibrated_,
not "big". The overnight CPU goes into leave-one-repo-out cross-validation,
bootstrap confidence intervals, and a deterministic hyperparameter/model search
— so the headline number is defensible.

**Determinism rule (unchanged):** every added component is deterministic.
Bootstrap resampling uses a fixed integer seed via `random.Random(seed)`; no
wall-clock, no unseeded randomness. Repeat runs are byte-identical.

**Honesty guardrails (hard):**

- RISK is the only high-confidence head; proxy heads carry
  `label_provenance.kind = constructed_label` and `confidence = low` and never
  drive the headline result.
- No claim of consciousness, self-improvement, or RSI. The artifact is a learned
  advisory substrate. It is _ready to be wired_ as advisory pressure through the
  deterministic gates later — it is not wired now.
- The final selected model is chosen by leave-one-repo-out AUROC, so a buggy or
  weaker candidate can never win by overfitting the dev split.

---

## Component R1: Weighted logistic (`src/pneuma_lab/brain/linear.py`)

A class-weighted full-batch logistic, deterministic (fsum, zero init, fixed
schedule), independent of the frozen E1/E2 `estimators.logistic` (which must not
drift). Inverse-frequency class weights so the 8% success class is not ignored.

- `class_weights(labels) -> dict[int,float]` — inverse frequency, normalized to
  mean 1.0.
- `train_weighted(rows_std, labels, weights, *, l2, lr, lr_decay, iters)` —
  weighted gradient descent; L2 on weights only.
- Tests: weighting shifts the decision boundary toward the minority class;
  identical inputs → identical weights; unweighted equals `estimators.logistic`
  within tolerance when weights are uniform.

## Component R2: Calibration (`src/pneuma_lab/brain/calibration.py`)

Platt scaling: fit a 1-D logistic on dev `(score, label)` pairs, apply to eval.
Report ECE (via `estimators.metrics.ece`) before and after.

- `fit_platt(scores, labels) -> (a, b)`; `apply_platt(score, a, b) -> prob`.
- Tests: calibration reduces or holds ECE on a miscalibrated synthetic set;
  monotonic (order-preserving) so AUROC is unchanged by calibration.

## Component R3: Cross-validated evaluation (`src/pneuma_lab/brain/evaluate.py`)

The heart of the rigor.

- `leave_one_repo_out(examples, fit_fn, predict_fn) -> {per_repo, oof}` — for
  each of the 11 repos: train on the other 10, predict the held-out repo, gather
  out-of-fold predictions; return per-repo AUROC and the pooled OOF AUROC. This
  is the honest generalization estimate (no repo appears in its own training).
- `bootstrap_auroc(scores, labels, *, n_resamples=2000, seed=20260710) ->
{auroc, lo, hi}` — percentile 95% CI over deterministic resamples.
- Tests: LORO on a separable synthetic multi-repo set yields high per-repo AUROC;
  bootstrap CI brackets the point estimate and is reproducible byte-for-byte.

## Component R4: Model/hyperparameter search (`src/pneuma_lab/brain/search.py`)

Deterministic grid, selected by LORO OOF AUROC. Uses real CPU (grid × 11 folds).

- Grid: `l2 ∈ {0.0003, 0.001, 0.003, 0.01}`, `iters ∈ {400, 800, 1600}`,
  `class_weight ∈ {off, on}`. (~24 configs × 11 folds.)
- `search_best(examples, feature_fn) -> {best_config, leaderboard}` — full
  leaderboard recorded for the report; ties broken by a fixed config order.
- Tests: search returns a config from the grid; the leaderboard is sorted and
  deterministic.

## Component R5 (optional, safety-gated): Gradient-boosted stumps (`src/pneuma_lab/brain/trees.py`)

A simple deterministic gradient-boosted depth-1 stump ensemble as a second model
family. Included **only** as a search candidate — it wins only if it beats
weighted logistic under LORO. If it underperforms or is skipped, the logistic
ships and the report says so.

- `fit_stumps(rows, labels, *, n_rounds, lr)` / `predict_stumps`.
- Tests: fits a separable set to high AUROC; deterministic.

## Component R6: Proxy head — TASK_DIFFICULTY (`src/pneuma_lab/brain/proxy_labels.py`)

One conservatively-constructed head so v0.1 is genuinely multi-task, clearly
marked proxy. Difficulty label = 1 if the task's objective length is in the top
tercile among the corpus (a task-side, observable property), else 0. This is a
`constructed_label`, `confidence: low`; it is reported separately and never mixed
into RISK metrics or any headline claim.

- `difficulty_label(example, tercile_threshold) -> int`.
- Tests: threshold logic; masks examples with no objective length.

## Component R7: Elite training orchestrator (`src/pneuma_lab/brain/train_full.py`)

Wraps everything into one gated run that produces the final artifacts:

1. Corpus preflight (base-plan `preflight.verify_corpus_run`).
2. Load real corpus; freeze tool vocab on dev.
3. `search.search_best` (LORO-selected config) for RISK.
4. Refit RISK on dev with the best config; Platt-calibrate on dev.
5. Full evaluation: dev + eval-split metrics, LORO OOF AUROC, bootstrap 95% CI,
   per-repo table, ECE before/after calibration.
6. Train TASK_DIFFICULTY proxy head (reported separately).
7. Write `model.json`, `metrics.json`, `report.md`, `leaderboard.json`,
   `split_manifest.json` (repo→split, hashed for the authorization).
8. Print the headline: RISK LORO AUROC + CI vs the E-0 ~0.70 baseline.

- Test: end-to-end on the synthetic multi-repo fixture writes all artifacts and
  is byte-deterministic across two runs.

## Real run (operator/autonomous, pre-authorized)

1. Corpus already materialized: `build/training_examples/openhands-sampled/full/examples.jsonl` (6055 examples).
2. Sign the corpus authorization (records the operator's pre-authorization) with
   real `corpus_manifest_sha256`, member `source_traces_sha256` (from the adapter
   report), `split_manifest_sha256`, and `authorized_code_commit = HEAD`.
3. Run `train_full` → `build/brain/v0-1/run-1/`.
4. Copy the human-readable `report.md` summary into a tracked docs note; build
   artifacts stay gitignored.

## Self-review

- Imbalance → R1 + weighted metrics; single-split fragility → R3 LORO + R4
  selection; calibration → R2; strength/breadth → R4/R5/R6; trustworthiness →
  R3 bootstrap CIs + per-repo table. Every component is deterministic and tested.
- Anti-overclaim: proxy heads quarantined from headline; no runtime/RSI/
  consciousness claims; final model chosen by honest LORO.
