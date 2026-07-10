# Open-SWE-Traces Split Review

Reviews the repo-grouped split over the representative real conversion
(shard-0 full, 1,960 examples). Same shared generator as Dataset #1
(`pneuma_lab.training.splits`, `--dataset-id open-swe-traces`). Readiness
infrastructure only; authorizes no training. Artifacts under ignored `build/`.

## Split result

| Split      |  Examples |   Repos | Resolved rate |
| ---------- | --------: | ------: | ------------: |
| train      |     1,372 |       — |         0.411 |
| validation |       294 |       — |         0.442 |
| test       |       294 |       — |         0.449 |
| **total**  | **1,960** | **985** |     **0.421** |

Ratios land at 70 / 15 / 15. Class balance is preserved across splits
(resolved rate 0.41–0.45 everywhere), so no split is degenerate.

## Grouping integrity

- Policy: `repo_grouped` on `split_group.repo` (a `sha256:` repo digest).
- **No repo appears in more than one split** (`same_repo_in_multiple_splits =
false`) — the core anti-leakage property holds.
- 985 repo groups over 1,960 examples (~2 examples/repo): fine-grained grouping,
  so target ratios are hit closely with intact repo groups.
- Outcome labels were used only for post-hoc balance reporting, never for
  assignment.

## Cross-dataset leakage (unified-model concern)

The intra-dataset split is clean, but joint training with Dataset #1 is **not**:
the cross-dataset registry finds **7 of Dataset #1's 11 repos also present in
Open-SWE-Traces** (`pandas-dev/pandas`, `dask/dask`, `getmoto/moto`,
`iterative/dvc`, `modin-project/modin`, `conan-io/conan`,
`facebookresearch/hydra`). See
`docs/data/training-readiness/cross-dataset-leakage-registry.json`. Before any
unified `PneumaBrain-v0` run, these repos must be quarantined to one split
across both datasets (or held out).

## Caveats

- Full-corpus split will be regenerated once full-corpus conversion runs; the
  shard-0 split above is representative, not the final manifest.
- Split manifest does not authorize training; `training_weight` stays `0.0`.
- Generated split artifacts are ignored and not committed.
