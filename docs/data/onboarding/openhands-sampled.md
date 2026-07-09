# Dataset Onboarding: SWE-Gym OpenHands Sampled Trajectories

## Status

Onboarded as the first single-dataset registry pilot.

## Why this dataset was selected

This dataset is the best first onboarding target because it is already processed
into PneumaTrace v0.2, trajectory-bearing, labeled, deterministic,
adapter-backed, large enough to matter, and mapped by an existing adapter:
`pneuma_lab.adapters.openhands_sampled`.

OpenHands Verifier is also adapter-backed, but its current adapter report records
missing task joins. SWE-Gym Lite is cleaner but too small to stress the registry
pattern. OpenHands sampled has both real agent-step structure and complete task
joins, so it is the strongest first pilot.

## Dataset Facts

Source of truth: `adapter_report.json` under the processed dataset directory.

| Field | Value |
|---|---:|
| Source rows | 6055 |
| Processed traces | 6055 |
| Invalid traces | 0 |
| Skipped rows | 0 |
| Agent steps | 114461 |
| Resolved | 491 |
| Unresolved | 5564 |
| Task joins present | 6055 |
| Task joins missing | 0 |

Labels are available through `labels.resolved`, `outcome.resolved`, and harness
report fields when present. Label provenance is the SWE-Gym/OpenHands sampled
trajectory harness output carried through the PneumaTrace envelope.

Processed outputs are redaction-verified. The adapter report records
deterministic redaction totals of 103 emails, 4 AWS access keys, and 16 assigned
secrets. This onboarding pass validates manifests, reports, paths, and hashes;
it does not inspect raw trajectory content.

## Schema and Adapter Mapping

The adapter emits `PneumaTrace` envelope version `0.2.0`.

- `world-frame`: task objective and repo/test context from the dataset/task join.
- `governance-frame`: minimal synthetic contract frame.
- `agent-trace-frame`: observable assistant/tool steps from real recorded
  OpenHands trajectories.

The anti-fake-cognition gate requires agent traces to be backed by a trajectory
block and `labels.has_trajectory`; undeclared cognition-bearing frames are
rejected. The traces are evidence about OpenHands behavior and outcomes, not
Pneuma interiority.

## Validation Performed

Use these commands for this onboarding pass:

```powershell
python scripts/verify_local_datasets.py --data-root C:/pneuma-data
python scripts/verify_swe_gym_sample.py --data-root C:/pneuma-data
python scripts/verify_dataset_onboarding.py --dataset swe-gym-openhands-sampled --data-root C:/pneuma-data
python -m pytest tests/ -q
```

The adapter fixture drift check is:

```powershell
python -m pneuma_lab.adapters.openhands_sampled --emit-fixture
```

That command compares the committed fixture output and does not rewrite large
processed outputs unless `--update-fixture` is explicitly used.

## Known Caveats

- The class balance is strongly skewed: 491 resolved vs 5564 unresolved.
- Labels are OpenHands/SWE-Gym harness outcomes, not Pneuma outcomes.
- These traces describe OpenHands and its model/scaffold, not Pneuma or 9to5.
- Timestamps are synthetic ordinals; order is preserved, but wall-clock timing is
  not observed.
- Processed outputs are redaction-verified, but raw trajectory content remains
  non-targeted in this pass.
- Counts and hashes can drift if processed outputs are regenerated; compare
  against `adapter_report.json` instead of hand-editing values.

## Allowed Next Steps

- Use this dataset for feature extraction planning.
- Use this dataset for split design.
- Use this dataset for later E1/E2 modeling only after separate approval.
- Reuse the registry pattern to onboard a second dataset.

## Blocked Next Steps

- No ML training in this pass.
- No E1/E2 estimator fitting or calibration in this pass.
- No runtime integration.
- No J-space or Jacobian Lens work.
- No SWE-chat processing.
- No consciousness-level claims.

## Scaling Notes

The reusable pattern is:

1. Choose one dataset with clear processed artifacts or a low-risk adapter path.
2. Keep paths relative to `PNEUMA_DATA_ROOT`.
3. Treat the dataset's generated report as the source of truth.
4. Commit only small registry/report metadata.
5. Add validation that compares registry expectations against generated reports.
6. Preserve explicit allowed and blocked uses so onboarding cannot quietly become
   training or runtime integration.
