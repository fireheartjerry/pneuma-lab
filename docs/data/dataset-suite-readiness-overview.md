# Pneuma Dataset Suite — Readiness Overview

Single source of truth for where every dataset lane stands before the unified
`PneumaBrain-v0` trainer phase. Machine-readable companion:
`docs/data/training-readiness/dataset-registry.json` (validated by
`python -m pneuma_lab.dataset_readiness --check`). This doc authorizes no
training; every lane stays `training_weight: 0.0` until a specific
authorization manifest says otherwise.

## The training-vs-eval distinction

A dataset is only a _supervised training source_ for the current
`RISK_PREDICTION` objective if it carries **real agent attempts with a
distributed pass/fail outcome**. Gold-patch benchmarks (every instance ships a
correct patch that passes) have no negative class and no agent trajectory — they
are **held-out evaluation** sets, not training sources. This splits the suite
cleanly:

| Kind                        | Has agent attempts + outcome distribution? | Role            |
| --------------------------- | ------------------------------------------ | --------------- |
| Trajectory + outcome corpus | yes                                        | training source |
| Gold-patch benchmark        | no (gold always passes)                    | held-out eval   |
| Privacy/dual-use corpus     | n/a                                        | blocked         |

## Lane status (11 families)

| Lane                               | License                 | Signal                              | Role              | Stage                       | Next step                                               |
| ---------------------------------- | ----------------------- | ----------------------------------- | ----------------- | --------------------------- | ------------------------------------------------------- |
| **swe-gym-openhands-sampled** (D1) | swe-gym                 | agent traj + resolved               | **train**         | preflight-only              | human training authorization                            |
| **open-swe-traces** (D2)           | cc-by-4.0               | agent traj + resolved (synthetic)   | **train**         | leakage-blocked             | full-corpus convert + ToS + quarantine 7 overlap repos  |
| swe-gym-openhands-verifier         | swe-gym                 | agent traj + verifier verdict       | train (verdict)   | join-blocked                | validate joins; verdict≠task-outcome converter          |
| swe-evo                            | apache-2.0              | agent infer_logs (98%)              | train (low pri)   | planned                     | quarantine heavy repo overlap; adapter over infer_logs  |
| multi-swe-bench                    | CC0 claim / `other` tag | task+patch, RL variant has attempts | train (RL) / eval | planned                     | confirm license; RL-variant attempts for training       |
| swe-gym-lite                       | swe-gym                 | task-only                           | eval / difficulty | adapter-only                | task-only converter needs a constructed target          |
| swe-polybench                      | mit                     | task-only, no outcome/traj          | **eval**          | planned                     | held-out eval or TASK_DIFFICULTY proxy (no RISK target) |
| swe-bench                          | undeclared              | task-only benchmark                 | **eval-only**     | eval-only                   | wire as held-out eval; contamination role               |
| swe-bench-pro                      | unspecified HF          | task-only benchmark                 | eval / blocked    | license-blocked-for-release | explicit artifact license                               |
| swe-mera                           | mit/CC-BY               | task-only, anti-contamination       | **eval-only**     | eval-only                   | held-out eval/calibration only                          |
| sec-bench-pro                      | mit/apache              | security exploit content            | **blocked**       | provenance-blocked          | dual-use review + redaction + no-PoC                    |
| swe-chat                           | odc-by                  | human PII, gated                    | **blocked**       | provenance-blocked          | HF token + terms + PII redaction plan                   |
| dialogue-swe-bench (archived)      | undeclared              | dialogue                            | **blocked**       | license-blocked-for-release | superseded by open-swe-traces                           |

## Implication for the unified trainer

The `PneumaBrain-v0` training corpus is small and trajectory-based by nature:
**Dataset #1 + Dataset #2** today, with `swe-gym-openhands-verifier`,
`swe-evo`, and the `multi-swe-RL` variant as the realistic expansion set once
their label semantics and (for swe-evo/multi) repo-overlap quarantine are
resolved. Everything else is **held-out evaluation** or **blocked** — which is
the correct posture: benchmarks must stay out of training to remain valid
evaluation.

Before any joint run: the cross-dataset leakage registry
(`cross-dataset-leakage-registry.json`) must be populated for every training
lane pair and overlapping repos quarantined. The D1×D2 check already found 7
overlapping repos (pandas, dask, moto, dvc, modin, conan, hydra).

## Hard gates preserved across all lanes

License / provenance / privacy / dual-use gates; per-row and cross-dataset
leakage checks; `training_weight: 0.0` and `model_use_tier` non-`train_ok`
until an explicit authorization manifest exists; no runtime integration; no
E1/E2-as-training; no J-space work; no raw/processed/build data committed.
