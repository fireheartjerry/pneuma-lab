# Dataset Status Review: SWE-PolyBench

**Decision: EVAL / DIFFICULTY CANDIDATE — not a supervised RISK training
source.** Clean MIT license, well-shaped, not blocked — but the normalized
metadata confirms `has_outcome = 0%` and `has_trajectory = 0%`: it is a
gold-patch benchmark with no agent attempts and no pass/fail distribution, so it
has **no natural `RISK_PREDICTION` target**. Its role is held-out evaluation or
a future `TASK_DIFFICULTY` proxy, not `RISK_PREDICTION` training. See
`docs/data/dataset-suite-readiness-overview.md` for the train-vs-eval framework.

## Source

| Field             | Value                                                                                                                                          |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| HF repos          | `AmazonScience/SWE-PolyBench` (2,110), `AmazonScience/SWE-PolyBench_500` (stratified)                                                          |
| Revision          | `d56445f9940eae4e9d2974ec66820c2f1d7754e6`                                                                                                     |
| Declared license  | `MIT` (benchmark scaffolding); upstream 21 repos retain own licenses                                                                           |
| Local status      | downloaded (3 splits, pinned)                                                                                                                  |
| Shape             | repo + base_commit + problem_statement + hints_text, gold patch + test_patch + Dockerfile + test_command, F2P/P2P, AST metrics; multi-language |
| Native trajectory | none (task-only, like swe-gym-lite)                                                                                                            |

## Assessment

- **License: clean (MIT).** No license/provenance/privacy/dual-use block.
- **Shape: task-only.** Gold patch + test oracle, no recorded agent trajectory,
  so it maps to the `swe-gym-lite` task-only lane, not the trajectory-bearing
  Open-SWE-Traces lane. Expected example types: `TaskExample` / `PatchExample`;
  no `RISK_PREDICTION` trajectory features.
- **Known issues:** Verified count 382 vs 394 discrepancy; CSV metadata only
  (source trees external); GitHub HEAD not pinned to paper release; upstream
  repo licenses not enumerated.

## Lane status & next step

- `current_stage: planned`, `training_readiness: local-research-only`,
  `training_weight: 0.0`.
- Because there is no per-task outcome label, the only training use would
  require a **constructed** target (e.g. a `TASK_DIFFICULTY` proxy from AST
  metrics / test counts), which is speculative. The higher-confidence role is
  **held-out multi-language evaluation**.
- If pursued at all: a task-only stage-1 adapter (mirror
  `src/pneuma_lab/adapters/swe_gym_lite.py`) emitting world + governance +
  oracle frames (no agent-trace frames), used for eval or difficulty scoring —
  never a `RISK_PREDICTION` training target without agent attempts.
