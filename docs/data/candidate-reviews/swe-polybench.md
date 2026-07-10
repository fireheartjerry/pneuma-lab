# Dataset Status Review: SWE-PolyBench

**Decision: TRAINING CANDIDATE — task-only adapter pending.** Clean MIT license,
well-shaped; not blocked. Needs a stage-1 adapter (swe_gym_lite pattern) before
it reaches Dataset #1 parity.

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
- Next: build a **task-only stage-1 adapter** (mirror
  `src/pneuma_lab/adapters/swe_gym_lite.py`) emitting task-only PneumaTrace
  envelopes (world + governance + oracle, no agent-trace frames), then a
  converter keeping oracle/patch fields out of `input`. Then split + leakage
  check against the existing cross-dataset registry (multi-language repos, so
  overlap with the SWE-bench family should be low but must be verified).
