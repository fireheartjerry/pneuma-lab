# Dataset Status Review: SWE-MERA

**Decision: EVAL-ONLY — held-out by design (anti-contamination).** Usable for
held-out evaluation / calibration, never as a training target.

## Source

| Field            | Value                                                                                                                             |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| HF repo          | `MERA-evaluation/SWE-MERA` (official)                                                                                             |
| Revision         | `4aa9e55379f335015496b73ec8fbcb4576f2f108`                                                                                        |
| Declared license | `mit` (official HF); paper text says CC BY 4.0 (inconsistent — record both)                                                       |
| Local status     | downloaded (official + secondary mirror, pinned)                                                                                  |
| Shape            | problem_statement / hint_text, patch / test_patch diffs, FAIL/PASS_TO_PASS + freshness timestamps; dev 10 / lite 750 / full 2,738 |

## Why eval-only

1. **Anti-contamination design.** The dossier `usage_restriction` is explicit:
   "HELD-OUT EVALUATION ONLY per anti-contamination design." SWE-MERA is a
   dynamic, continuously refreshed benchmark whose whole value is that models
   have not trained on it.
2. Using it as a training source would destroy its purpose and contaminate any
   evaluation that relies on it (including future PneumaBrain-v0 eval).

## Lane status

- `current_stage: eval-only`, `training_readiness: eval-only`.
- `model_use_tier: eval_only`, `training_weight: 0.0`, `leakage_risk:
eval_only` — the training-example schema enforces that `eval_only` privacy
  status pins `model_use_tier` to `eval_only` and weight to 0.
- License inconsistency (MIT vs CC BY 4.0) is recorded but does not gate an
  eval-only use.

## Next step

Not a training lane. If/when an evaluation harness exists, SWE-MERA can be wired
as a **held-out eval/calibration** set (pin sha + fetch date, since counts
drift). No training conversion is planned.
