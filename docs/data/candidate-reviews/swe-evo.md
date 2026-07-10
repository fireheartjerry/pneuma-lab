# Dataset Status Review: SWE-EVO

**Decision: TRAINING CANDIDATE (low priority) — trajectory adapter pending;
severe cross-dataset repo overlap.** Clean license and trajectory-bearing, but
tiny and highly redundant with existing lanes.

## Source

| Field            | Value                                                                                                                                                            |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| HF repo          | `Fsoft-AIC/SWE-EVO`                                                                                                                                              |
| Revision         | `77310c70d3648d6815f6a7555ecc492bc28c44ec`                                                                                                                       |
| Declared license | code MIT; **hf_dataset Apache-2.0**                                                                                                                              |
| Local status     | downloaded (full incl. trajectories, pinned; ~7GB)                                                                                                               |
| Shape            | release-note/SRS task prompts, Python repo snapshots + patch diffs, FAIL/PASS_TO_PASS (avg 874 tests/instance), OpenHands/SWE-agent infer_logs + llm_completions |
| Core size        | **48 tasks** (core benchmark); the bulk is trajectory logs                                                                                                       |

## Assessment

- **License: clean (Apache-2.0 dataset).** No license/privacy/dual-use block.
- **Trajectory-bearing.** infer_logs + llm_completions could feed a
  trajectory-bearing lane like Open-SWE-Traces (`RISK_PREDICTION` etc.).
- **Severe cross-dataset leakage.** The 7 Python projects include
  `conan`, `dask`, `dvc`, `modin`, `scikit-learn` — these overlap heavily with
  both Dataset #1 (SWE-Gym) and Dataset #2 (Open-SWE-Traces) repos already
  flagged in the cross-dataset leakage registry. As a _training_ source SWE-EVO
  is largely redundant and would worsen repo-level overlap.
- **Tiny core (48 tasks).** Low marginal value for a unified model.

## Lane status & next step

- `current_stage: planned`, `training_readiness: local-research-only`,
  `training_weight: 0.0`.
- Next (low priority): if pursued, build a trajectory-bearing adapter over the
  infer_logs, but **first** register its repo set in the cross-dataset leakage
  registry and quarantine the overlapping repos. Given the redundancy, SWE-EVO
  is a better fit as a held-out **eval** slice for evolution/release-note tasks
  than as a training source; revisit after the higher-value lanes are built.
