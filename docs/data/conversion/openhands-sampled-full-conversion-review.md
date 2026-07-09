# OpenHands Sampled Full Conversion Review

Status: reviewed full processed conversion smoke.

This review covers the explicitly gated full processed conversion from
`swe-gym-openhands-sampled` processed `PneumaTrace` records into canonical
`PneumaTrainingExample` records. It is conversion infrastructure only. It does
not authorize model training, E1/E2, calibration, runtime behavior changes,
J-space/Jacobian Lens work, SWE-chat processing, raw data inspection, raw or
processed data mutation, or writes to `C:/pneuma-data`.

## Command Reviewed

```powershell
python -m pneuma_lab.converters.openhands_sampled_training `
  --mode full `
  --confirm-full-conversion `
  --input C:/pneuma-data/processed/swe-gym/openhands-sampled/pneuma_traces.jsonl `
  --adapter-report C:/pneuma-data/processed/swe-gym/openhands-sampled/adapter_report.json `
  --output build/training_examples/openhands-sampled/full/examples.jsonl `
  --report build/training_examples/openhands-sampled/full/conversion_report.json `
  --hash-manifest build/training_examples/openhands-sampled/full/hash_manifest.json `
  --invalid-output build/training_examples/openhands-sampled/full/invalid_examples.jsonl
```

## Output Artifacts

Generated artifacts:

| Artifact | Status |
|---|---|
| `build/training_examples/openhands-sampled/full/examples.jsonl` | ignored, not committed |
| `build/training_examples/openhands-sampled/full/conversion_report.json` | ignored, not committed |
| `build/training_examples/openhands-sampled/full/hash_manifest.json` | ignored, not committed |
| `build/training_examples/openhands-sampled/full/invalid_examples.jsonl` | ignored, not committed |

The generated artifacts are under ignored repo-local `build/` paths. They are
not source artifacts and should not be committed.

## Review Results

| Check | Result |
|---|---:|
| Examples emitted | 6,055 |
| Invalid examples | 0 |
| Quarantined examples | 0 |
| Resolved targets | 491 |
| Unresolved targets | 5,564 |
| Agent steps reconciled | 114,461 |
| Schema validation | passed |
| Forbidden input-key hits | 0 |
| Output hashes recomputed | passed |
| Manifest self-hash recomputed | passed |

The emitted examples remain `model_use_tier: train_after_adapter` and
`training_weight: 0.0`. `target.resolved` is preserved in `target`, while
inputs remain observable-only and exclude forbidden leakage keys such as
`resolved`, `outcome`, `labels`, `gold`, `oracle`, `fail_to_pass`,
`pass_to_pass`, `patch`, and `verdict`.

## Hash Manifest Convention

`hash_manifest_json_sha256` is now directly recomputable. The convention is to
hash canonical manifest JSON with `hashes.hash_manifest_json_sha256` set to
`null`, then store that digest in the final manifest. This avoids a
self-referential manifest hash.

## Caveats

- The full conversion is not training authorization.
- The class balance remains skewed: 491 resolved and 5,564 unresolved.
- Generated full outputs are review evidence under `build/`, not committed
  repository state.
- Any nonzero `training_weight`, model fitting, calibration, E1/E2 execution,
  runtime integration, or new task-head expansion requires a separate approval.

## Recommended Next Step

Review and commit the converter, tests, and documentation only. After that,
keep Dataset #1 conversion artifacts as ignored local evidence and move to an
explicit split/mixture planning pass before any training-oriented use.
