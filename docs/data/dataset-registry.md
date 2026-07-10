# Dataset Registry

Status: multi-dataset metadata registry.

The canonical graded readiness registry is
`docs/data/training-readiness/dataset-registry.json`. Validate it with:

```powershell
python -m pneuma_lab.dataset_readiness --check
```

Each lane separates its current readiness stage from training readiness and
authorization. `training-authorized` is deliberately stricter than
`close-but-needs-human-authorization`: it requires the tracked authorization,
source/split hashes, frozen constants, approved output root, and clean code
binding required by the fail-closed trainer preflight. Planned references are
explicitly marked; all other committed references must exist.

This registry makes local datasets legible to Pneuma Lab without copying raw
data into the repository. Registry entries use relative paths under a data root
so the same manifest can work across machines. The default local root observed
for this checkout is `C:/pneuma-data`; override it with `PNEUMA_DATA_ROOT` or a
validator `--data-root` argument.

## Onboarded Datasets

| Dataset ID                   | Name                                    | Status                                  | Manifest                                    | Report                                      | Training Readiness                                  |
| ---------------------------- | --------------------------------------- | --------------------------------------- | ------------------------------------------- | ------------------------------------------- | --------------------------------------------------- |
| `swe-gym-openhands-sampled`  | SWE-Gym OpenHands Sampled Trajectories  | onboarded                               | `docs/data/registry/openhands-sampled.json` | `docs/data/onboarding/openhands-sampled.md` | `docs/data/training-readiness/openhands-sampled.md` |
| `open-swe-traces`            | Open-SWE-Traces                         | active Dataset #2 (metadata-onboarding) | `docs/data/registry/open-swe-traces.json`   | `docs/data/onboarding/open-swe-traces.md`   | canonical registry                                  |
| `swe-gym-openhands-verifier` | SWE-Gym OpenHands Verifier Trajectories | join-blocked                            | adapter and fixtures                        | adapter tests                               | canonical registry                                  |
| `swe-gym-lite`               | SWE-Gym-Lite Task Rows                  | adapter-only                            | adapter design spec                         | adapter tests                               | canonical registry                                  |

## Archived Datasets

| Dataset ID           | Name               | Status            | Reason                                                                                     | Superseded By     |
| -------------------- | ------------------ | ----------------- | ------------------------------------------------------------------------------------------ | ----------------- |
| `dialogue-swe-bench` | Dialogue SWE-Bench | archived-inactive | dataset artifact license was `null` at every source checked (HF, GitHub, local provenance) | `open-swe-traces` |

Archived dataset docs/manifests live under `docs/data/archive/dialogue-swe-bench/`
(`registry.json`, `onboarding.md`, `conversion.md`, `training-readiness.json`,
`license-provenance-review.md`). They are kept for provenance, not deleted,
and are not validated by the default active-dataset tooling. The converter,
governance module, and tests for this dataset remain in place under `src/`
and `tests/` and continue to enforce the license block; only the dataset's
docs/manifests moved.

## Boundaries

- Registry entries are small, committed metadata files.
- Raw and processed dataset artifacts remain outside the repo.
- `adapter_report.json` is the source of truth for processed counts, hashes,
  redaction totals, and adapter status.
- Datasets without adapter reports may use metadata sidecars such as
  `row_counts.json`, `file_index.jsonl`, `provenance.json`, and
  `normalized_metadata.jsonl`; validators must remain metadata-only.
- This registry does not authorize ML training, estimator fitting, calibration,
  runtime integration, J-space work, or consciousness-level claims.
