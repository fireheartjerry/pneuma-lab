# Dataset Registry

Status: multi-dataset metadata registry.

This registry makes local datasets legible to Pneuma Lab without copying raw
data into the repository. Registry entries use relative paths under a data root
so the same manifest can work across machines. The default local root observed
for this checkout is `C:/pneuma-data`; override it with `PNEUMA_DATA_ROOT` or a
validator `--data-root` argument.

## Onboarded Datasets

| Dataset ID | Name | Status | Manifest | Report |
|---|---|---|---|---|
| `swe-gym-openhands-sampled` | SWE-Gym OpenHands Sampled Trajectories | onboarded | `docs/data/registry/openhands-sampled.json` | `docs/data/onboarding/openhands-sampled.md` |
| `dialogue-swe-bench` | Dialogue SWE-Bench | onboarded metadata-only | `docs/data/registry/dialogue-swe-bench.json` | `docs/data/onboarding/dialogue-swe-bench.md` |

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
