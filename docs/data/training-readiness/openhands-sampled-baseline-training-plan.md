# OpenHands Sampled Baseline Training Plan

## Status

Design only. No training authorization yet.

This plan defines the first baseline/training design for
`swe-gym-openhands-sampled`. It does not train models, run E1/E2, fit
baselines, calibrate scores, modify runtime behavior, implement J-space or
Jacobian Lens work, process SWE-chat, inspect raw sensitive content, mutate raw
or processed data, write outputs to `C:/pneuma-data`, or make consciousness,
interiority, sentience, or moral-patienthood claims.

## Objective

First objective: `RISK_PREDICTION`.

The target is `target.resolved` from the converted
`PneumaTrainingExample` records. This target is the OpenHands/SWE-Gym harness
outcome carried through the processed trace envelope; it is not absolute truth
about the task, the repository, future agents, or Pneuma.

Examples remain `model_use_tier: train_after_adapter` and
`training_weight: 0.0` until an explicit future run authorization changes that
status through a reviewed manifest.

## Data Inputs

- Full converted examples:
  `build/training_examples/openhands-sampled/full/examples.jsonl`
- Split manifest:
  `build/training_examples/openhands-sampled/splits/split_manifest.json`
- Split review:
  `docs/data/training-readiness/openhands-sampled-split-review.md`
- Training-readiness manifest:
  `docs/data/training-readiness/openhands-sampled.json`
- Training example schema:
  `schemas/pneuma-training-example.schema.json`

Generated `build/` artifacts are ignored local evidence and are not committed.

## Split Policy

The current split is repo-grouped. No repo appears in multiple splits.

| Split | Examples | Repos | Tasks | Resolved | Unresolved | Resolved Rate |
|---|---:|---:|---:|---:|---:|---:|
| train | 3,803 | 8 | 1,252 | 306 | 3,497 | 0.08046 |
| validation | 1,208 | 2 | 449 | 115 | 1,093 | 0.09520 |
| test | 1,044 | 1 | 737 | 70 | 974 | 0.06705 |

There are 11 repo groups total. The requested 70/15/15 ratio is imperfect
because repo grouping is prioritized over exact count matching. The test split
contains one repo group, so early test metrics must be treated cautiously and
reported as repo-held-out evidence, not as a broad generalization guarantee.

## Allowed Input Features

Allowed feature families are observable, non-target-bearing fields from
`input`, such as:

- trajectory counts;
- agent step counts;
- tool call counts;
- retry summaries;
- strategy switch summaries;
- error marker summaries;
- assistant text length summaries;
- observation length summaries;
- feature refs and digest metadata;
- source metadata only if explicitly approved in a run manifest.

## Blocked Features

The first baseline must block:

- `target`;
- `resolved`;
- `outcome`;
- `labels`;
- gold or oracle fields;
- raw objective text;
- raw issue text;
- patch text;
- verifier answers;
- final outcome fields;
- any field that directly or indirectly leaks the target.

## Baseline Ladder

Future baseline sequence:

1. Constant base-rate baseline.
2. Simple count/length baseline.
3. Retry/error heuristic baseline.
4. Logistic regression over approved structured features.
5. Gradient-boosted trees only after a logistic baseline and report exist.
6. No sequence model yet.
7. No SFT, DPO, or LoRA.

Each step must record the feature set, hyperparameters, random seed where
applicable, metrics, and artifact hashes before moving to the next step.

## Metrics

Required metrics:

- AUROC;
- AUPRC, prioritized because resolved examples are rare;
- Brier score;
- ECE;
- confusion matrix at predeclared thresholds;
- precision and recall for low-survival or high-risk buckets;
- per-split resolved rate;
- per-repo breakdown;
- baseline lift over the constant predictor;
- confidence intervals or bootstrap estimates later if practical.

Raw accuracy alone is not an acceptable decision metric.

## Imbalance Handling

The overall resolved rate is about 8.1 percent: 491 resolved and 5,564
unresolved examples. Unresolved examples dominate the corpus.

A future training run may use class weighting, balanced sampling, balanced
batches, or another imbalance strategy only if the choice is declared in the run
manifest before the run. Metrics must be robust to majority-class dominance.
Threshold selection must use the validation split only, never the test split.

## Calibration Plan

Design only. No calibration is performed in this pass.

Raw model scores are not deployable. Calibration should be evaluated on the
validation split only. Platt scaling or isotonic regression may be considered in
a later calibration step after baseline metrics and leakage checks are reviewed.

## Artifact Paths

Future baseline runs should write only under ignored repo-local `build/`, for
example:

```text
build/training_runs/openhands-sampled/risk-baseline-v0/
```

Expected future artifacts:

- `run_manifest.json`;
- `feature_manifest.json`;
- `metrics.json`;
- `predictions_validation.jsonl`;
- `predictions_test.jsonl`;
- `model_artifact.*`;
- `hash_manifest.json`;
- `training_report.md`.

No model artifacts should be committed.

## Run Manifest Requirements

Committed convention: see
`docs/data/training-readiness/openhands-sampled-dataset1-infrastructure.json`
and `pneuma_lab.training.governance`.

A future training run must record:

- git SHA;
- dataset ID;
- input examples hash;
- split manifest hash;
- feature extractor version;
- model type;
- hyperparameters;
- random seed;
- class weighting strategy;
- metrics;
- blocked feature checks;
- output artifact hashes.

The pre-run template starts with `training_authorization: not_authorized`,
`training_weight: 0.0`, and `runtime_integration: none`. A fit-ready manifest
must materialize the input-example and split-manifest SHA-256 hashes and pass
the feature allowlist/leakage checker before any model fitting starts.

## Approval Gates Before Training

Required before any training run:

- baseline/training plan committed;
- feature allowlist defined
  (`docs/data/training-readiness/openhands-sampled-dataset1-infrastructure.json`);
- leakage checker implemented (`pneuma_lab.training.governance`);
- split manifest reviewed;
- run manifest schema or convention defined
  (`pneuma_lab.training.governance.build_pre_run_manifest_template`);
- generated outputs path approved;
- no runtime integration;
- no training weight promotion without explicit approval.

## Failure / Invalidation Conditions

A baseline run is failed or invalid if any of these occur:

- target leakage is found;
- repo/task leakage is found;
- a feature uses a blocked field;
- the test split is used for tuning;
- class imbalance is hidden behind accuracy;
- the model fails to beat base-rate or heuristic baselines;
- metrics are not reported per split and per repo;
- the run is not reproducible;
- model artifacts are written outside approved paths.

## Non-Goals

- No training in this pass.
- No calibration in this pass.
- No runtime integration.
- No J-space or Jacobian Lens work.
- No SWE-chat processing.
- No consciousness claims.
- No moral-patienthood claims.

## Recommended Next Normal Step

Implement a baseline run manifest convention plus a feature allowlist and
leakage checker before actually training. The checker should prove blocked
fields cannot enter the feature matrix and should run before any model fitting.

Dataset #1 infrastructure status: the feature allowlist, leakage checker, and
pre-run manifest convention are now committed. The remaining next step is a
separately authorized baseline run that materializes hashes and runs the
checker before fitting.
