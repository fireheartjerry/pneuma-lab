# OpenHands Sampled Split Review

Status: split manifest generated and reviewed.

This review covers deterministic repo-grouped split assignment for the
`swe-gym-openhands-sampled` full converted `PneumaTrainingExample` corpus. It
is split/readiness infrastructure only. It does not authorize training, E1/E2,
calibration, runtime integration, J-space/Jacobian Lens work, SWE-chat
processing, raw data inspection, raw or processed data mutation, or writes to
`C:/pneuma-data`.

## Command Reviewed

```powershell
python -m pneuma_lab.training.splits `
  --input build/training_examples/openhands-sampled/full/examples.jsonl `
  --output build/training_examples/openhands-sampled/splits/split_manifest.json `
  --report build/training_examples/openhands-sampled/splits/split_report.json `
  --hash-manifest build/training_examples/openhands-sampled/splits/hash_manifest.json `
  --dataset-id swe-gym-openhands-sampled `
  --policy repo_grouped `
  --train-ratio 0.70 `
  --validation-ratio 0.15 `
  --test-ratio 0.15
```

## Generated Outputs

| Artifact | Status |
|---|---|
| `build/training_examples/openhands-sampled/splits/split_manifest.json` | ignored, not committed |
| `build/training_examples/openhands-sampled/splits/split_report.json` | ignored, not committed |
| `build/training_examples/openhands-sampled/splits/hash_manifest.json` | ignored, not committed |

## Split Counts

| Split | Examples | Repos | Tasks | Resolved | Unresolved | Resolved Rate |
|---|---:|---:|---:|---:|---:|---:|
| train | 3,803 | 8 | 1,252 | 306 | 3,497 | 0.08046 |
| validation | 1,208 | 2 | 449 | 115 | 1,093 | 0.09520 |
| test | 1,044 | 1 | 737 | 70 | 974 | 0.06705 |

Total examples: 6,055. Every example was assigned exactly once.

## Grouping Result

- Primary grouping: `split_group.repo`.
- Repo groups: 11.
- Same repo in multiple splits: no.
- Source ordering and trace/example IDs remain available for audit through the
  generated manifest.
- Outcome labels were not used for assignment; they were used only for post-hoc
  class-balance reporting.

## Caveats

- The train split count differs from the 70 percent target by more than five
  percent of the full corpus because repo groups are assigned intact.
- The test split is one repo group, so repo-level generalization checks should
  be interpreted with that coarse grouping in mind.
- The corpus remains imbalanced: 491 resolved and 5,564 unresolved overall.
- Generated split artifacts are local ignored `build/` evidence and are not
  committed repository state.
- This split review is not training authorization. Examples remain
  `model_use_tier: train_after_adapter` and `training_weight: 0.0`.

## Hashes

The split hash manifest was recomputed successfully:

- `split_manifest_json_sha256` matched the generated split manifest bytes.
- `split_report_json_sha256` matched the generated split report bytes.
- `hash_manifest_json_sha256` matched the canonical manifest with
  `hashes.hash_manifest_json_sha256` set to `null`.

## Recommended Next Step

Review the split caveats and class balance before planning any baseline. The
next normal step is a baseline/training design document that specifies objective,
class imbalance handling, metrics, artifact paths, and approval gates without
running training.
