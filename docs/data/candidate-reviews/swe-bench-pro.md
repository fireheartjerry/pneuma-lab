# Dataset Status Review: SWE-bench Pro (public split)

**Decision: BLOCKED — unspecified HF artifact license (+ held-out benchmark
role).** Only the public split exists locally; no adapter, no converter, no
`PneumaTrainingExample` output.

## Source

| Field            | Value                                                                                                                                 |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| HF repo          | `ScaleAI/SWE-bench_Pro` (canonical public split)                                                                                      |
| Revision         | `7ab5114912baf22bb098818e604c02fe7ad2c11f`                                                                                            |
| Declared license | code repo MIT; paper CC BY 4.0; **HF card: unspecified**                                                                              |
| Local status     | partial-public: PUBLIC split (11 repos / 731 instances) downloaded; HELD-OUT (12 repos) + COMMERCIAL (18 repos) unavailable by design |
| Shape            | problem_statement / requirements / interface text, golden patch + test_patch diffs, repo/lang metadata, dockerhub_tag execution refs  |

## Why blocked

1. **Unspecified HF artifact license.** As with the archived `dialogue-swe-bench`
   candidate, the dataset artifact carries no explicit HF license key. The
   code-repo MIT and paper CC BY 4.0 are **not** the dataset-artifact license.
   Per the project's license gate, an unspecified artifact license blocks
   training use.
2. **Held-out benchmark role.** SWE-bench Pro is the successor eval benchmark
   OpenAI moved to after SWE-bench Verified; the public split is meant for
   evaluation, and only 731 of the paper's 1,865 instances are even
   reconstructable (held-out + commercial are unavailable by design).
3. Pneuma constructs (expected_loss etc.) would be synthesized, not native.

## Next unblock step

1. Obtain an **explicit dataset-artifact license** (or an authoritative
   statement that the public split is released under a named license).
2. Decide role: most likely `eval_only` (benchmark), not a training lane, given
   the held-out design and contamination overlap with the SWE-bench family.
3. Only with an explicit license AND a non-eval decision would a task-only
   adapter (patch/test metadata, oracle kept out of input) be designed.

Until then SWE-bench Pro stays `license-blocked-for-release` /
`training_readiness: blocked`, `training_weight: 0.0`.
