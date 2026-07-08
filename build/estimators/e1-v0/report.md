# e1-v0 training report (month-1, doc 08 §4)

Label: y=1 iff labels.resolved is False (failure risk)

## Split (grouped by labels.repo, sha256 buckets, ~30% eval)

- dev: 2877 traces, 7 repos, 2642 positive (y=1)
- eval: 3141 traces, 4 repos, 2885 positive (y=1)
- label-QC exclusions: 37 (error_eval=28, test_timeout=9); skipped_no_agent_frames=0

## Eval-split metrics per prefix

| prefix | AUROC | Brier | ECE(15) | ablation AUROC (no length) | constant Brier | retry-only AUROC | chance AUROC |
|---|---|---|---|---|---|---|---|
| prefix_25 | 0.7805 | 0.0688 | 0.0198 | 0.7738 | 0.0749 | 0.5241 | 0.5000 |
| prefix_50 | 0.8025 | 0.0684 | 0.0233 | 0.7883 | 0.0749 | 0.6406 | 0.5000 |
| full | 0.8381 | 0.0661 | 0.0142 | 0.8297 | 0.0749 | 0.7165 | 0.5000 |

## Honesty notes

- E1 monotonicity probe (20 synthetic vectors, error_density 0->1) [prefix_25]: FAIL
- E1 monotonicity probe (20 synthetic vectors, error_density 0->1) [prefix_50]: PASS
- E1 monotonicity probe (20 synthetic vectors, error_density 0->1) [full]: PASS
- Pre-registered targets: AUROC >= 0.65 at prefix_50 (observed 0.8025, MET); >= 0.7 full (observed 0.8381, MET).
- No objective-text embedding features: month-1 has no encoder dependency; this omission is deliberate and recorded (doc 08 §2.1 objective-text row deferred).
- ECE is reported RAW (no isotonic/Platt post-calibration fitted); the pre-registered ECE <= 0.05 target was stated post-calibration.
- The length-confound ablation removes every feature that grows monotonically with prefix length: n_steps_prefix, log1p_num_agent_steps, n_tool_calls_total, and all per-tool raw counts.
- Scores are advisory pressure/prior signals over observable receipts; nothing here is an interiority claim.
