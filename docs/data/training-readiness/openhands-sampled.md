# OpenHands Sampled Training Readiness

## Status

Training-readiness packaging only. No training authorization.

This document prepares future split and mixture decisions for
`swe-gym-openhands-sampled` without running training, E1/E2, calibration,
runtime integration, J-space/Jacobian Lens work, SWE-chat processing, raw data
inspection, raw or processed data mutation, or writes to `C:/pneuma-data`.

## Source Artifacts

- Registry manifest:
  `docs/data/registry/openhands-sampled.json`
- Onboarding report:
  `docs/data/onboarding/openhands-sampled.md`
- Conversion plan:
  `docs/data/conversion/openhands-sampled-to-training-examples.md`
- Full conversion review:
  `docs/data/conversion/openhands-sampled-full-conversion-review.md`
- Split review:
  `docs/data/training-readiness/openhands-sampled-split-review.md`
- Baseline/training plan:
  `docs/data/training-readiness/openhands-sampled-baseline-training-plan.md`
- Ignored full conversion report:
  `build/training_examples/openhands-sampled/full/conversion_report.json`
- Ignored full hash manifest:
  `build/training_examples/openhands-sampled/full/hash_manifest.json`
- Ignored split report:
  `build/training_examples/openhands-sampled/splits/split_report.json`
- Ignored split hash manifest:
  `build/training_examples/openhands-sampled/splits/hash_manifest.json`

The generated `build/` artifacts are local review evidence and are not committed
repository state.

## Converted Corpus Summary

| Field | Value |
|---|---:|
| Examples | 6,055 |
| Invalid examples | 0 |
| Quarantined examples | 0 |
| Resolved targets | 491 |
| Unresolved targets | 5,564 |
| Agent steps | 114,461 |

Class balance warning: resolved examples are only about 8.1 percent of the
converted corpus. Future training must address the unresolved-class dominance
before any positive training weight is approved.

Every emitted example remains `model_use_tier: train_after_adapter` and
`training_weight: 0.0`.

## Recommended Training Role

- Primary initial corpus for future `RISK_PREDICTION` experiments after
  explicit training authorization.
- Source for future `FAILURE_SHAPE` only after a label taxonomy is defined and
  reviewed.
- Source for future `SCAR_MOTIF` only after motif extraction exists and its
  leakage behavior is tested.
- Not suitable for `OPERATOR_PUSHBACK`, because the dataset has no operator
  chat labels.
- Not suitable for `SELF_REPORT_FAITHFULNESS`, because the current frames do
  not encode receipt-grounded claim audits.
- Not suitable for `WORKSPACE_SALIENCE_LATER`, because there are no live
  workspace or J-space targets in this corpus.

## Split Policy

Status: generated and reviewed.

Recommended primary policy: repo-grouped split.

- Group by repository first, using `split_group.repo`.
- Preserve task/instance grouping where available through `split_group.task_id`.
- Avoid placing the same repo or task/instance in both train and test whenever
  possible.
- Preserve trace IDs and source ordering for audit and deterministic reporting.
- Document limitations if the actual repo groups are too few or too imbalanced
  for a clean repo-only split.
- Do not use outcome labels in split assignment except for stratification
  reporting and post-hoc balance checks.

Generated split summary:

| Split | Examples | Repos | Tasks | Resolved | Unresolved | Resolved Rate |
|---|---:|---:|---:|---:|---:|---:|
| train | 3,803 | 8 | 1,252 | 306 | 3,497 | 0.08046 |
| validation | 1,208 | 2 | 449 | 115 | 1,093 | 0.09520 |
| test | 1,044 | 1 | 737 | 70 | 974 | 0.06705 |

Every example was assigned exactly once, and no repo appears in multiple splits.
The 70/15/15 ratios are imperfect because repo groups are assigned intact; the
train split differs from the target by more than five percent of the corpus.

## Mixture Policy

- The dataset is allowed into a future mixture only after explicit training
  authorization.
- Initial `training_weight` remains `0.0`.
- Any future candidate weight should be capped because the dataset is highly
  imbalanced and comes from one OpenHands/SWE-Gym source family.
- Class weighting, stratified sampling, balanced batches, or another documented
  imbalance strategy is likely required.
- Per-dataset metrics are required before any pooled model use.
- Leave-one-dataset-out evaluation is required once additional converted
  datasets are available.

## Authorization Gates

Required before any training-oriented use:

- Full conversion artifacts are reproducible.
- Split manifest is generated and reviewed.
- Leakage scan passes for emitted inputs.
- Class imbalance handling is specified.
- Baseline metrics are specified.
- Training objective is approved.
- Examples' `model_use_tier` is promoted, or a training job explicitly
  overrides it through an approved manifest.
- Training run writes only under approved build or model artifact paths.
- No runtime integration is added as part of training readiness.

## Leakage Risks

- `resolved`, `outcome`, and `labels` leakage into inputs.
- Task or repo ID shortcut risk.
- Objective digest or objective length shortcut risk.
- Source-order shortcut risk.
- Benchmark contamination from SWE-Gym lineage.
- OpenHands/SWE-Gym label is a harness outcome, not absolute truth.

## Next Steps

1. Implement a baseline run manifest convention.
2. Implement a feature allowlist and leakage checker.
3. Only then consider a first baseline or training run, still behind explicit
   authorization.
