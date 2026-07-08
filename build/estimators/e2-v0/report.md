# e2-v0 training report (month-1, doc 08 §4)

Label: y=1 iff labels.resolved is False AND last3_error_density==0.0 at the prefix point (error-quiet eventual failure)

## Split (grouped by labels.repo, sha256 buckets, ~30% eval)

- dev: 2877 traces, 7 repos, 2642 positive (y=1)
- eval: 3141 traces, 4 repos, 2885 positive (y=1)
- label-QC exclusions: 37 (error_eval=28, test_timeout=9); skipped_no_agent_frames=0

## Eval-split metrics per prefix

| prefix | AUROC | Brier | ECE(15) | ablation AUROC (no length) | constant Brier | retry-only AUROC | chance AUROC |
|---|---|---|---|---|---|---|---|
| prefix_25 | 0.9849 | 0.0353 | 0.0205 | n/a | 0.2520 | 0.4906 | 0.5000 |
| prefix_50 | 0.9917 | 0.0299 | 0.0332 | n/a | 0.2457 | 0.6321 | 0.5000 |
| full | 0.9580 | 0.0598 | 0.0199 | n/a | 0.2227 | 0.6494 | 0.5000 |

## Honesty notes

- PROXY LABELS: silent-risk-stage-1 (resolved=False AND last3_error_density==0 at prefix). This conflates 'agent not testing' with 'nothing to find' (doc 08 E2 failure mode); the proxy tag must propagate into any consuming frame provenance.
- The last3_error_density feature partially determines the label by construction (quiet gate); the learned part is failure among quiet prefixes.
- E2 positives [prefix_25]: dev 1642, eval 1637
- E2 positives [prefix_50]: dev 1336, eval 1323
- E2 positives [full]: dev 1927, eval 2090
- No objective-text embedding features: month-1 has no encoder dependency; this omission is deliberate and recorded (doc 08 §2.1 objective-text row deferred).
- ECE is reported RAW (no isotonic/Platt post-calibration fitted); the pre-registered ECE <= 0.05 target was stated post-calibration.
- The length-confound ablation removes every feature that grows monotonically with prefix length: n_steps_prefix, log1p_num_agent_steps, n_tool_calls_total, and all per-tool raw counts.
- Scores are advisory pressure/prior signals over observable receipts; nothing here is an interiority claim.
