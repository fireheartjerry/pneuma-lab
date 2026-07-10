# PneumaBrain-v0.1 — Model Card & Usage Guide

Status: trained (local research), advisory-only. Not a runtime component, not a
consciousness claim. Produced by the gated trainer on the D1 minimum-viable
corpus. Reproduce with the commands in the "Reproduce" section.

## What it is

PneumaBrain-v0.1 is a deterministic, CPU-only, **early-warning failure-risk
estimator** for autonomous SWE-agent trajectories. Given the observable-only
summary of an agent run — tool histograms, retry/error dynamics, strategy
switches, message/observation lengths — it emits a calibrated
`RiskEstimateFrame`: the probability that the run will fail (not resolve),
available after the first 25%, 50%, or 100% of the trajectory.

It is the learned _cognition substrate_ the research program calls for: a
supervised replacement for hand-tuned instinct/verification priors. It sits
**below** the deterministic governance/verifier gates and only produces
evidence-bearing priors — it never changes authority or bypasses verification.

## What it is NOT

- Not the agent, not the verifier, not a code generator.
- Not a consciousness, sentience, or self-improvement claim. A logistic risk
  estimator is not a mind; the RSI loop remains not operational.
- Not wired into any runtime. It is _ready to be wired_ as advisory pressure
  through the deterministic gates — that integration is a separate, gated step.

## Training data

- **Corpus:** D1 = `swe-gym-openhands-sampled`, 6055 real agent trajectories
  across 11 repositories, materialized as `PneumaTrainingExample` records.
- **Label:** `RISK_PREDICTION`, failure=1, from the harness outcome
  (`resolved`). Base failure rate 91.9% (491 resolved / 5564 unresolved).
- **Leakage controls:** features are observable-only; the extractor deletes
  `outcome`/`oracle`/`reference_supervision`/`labels.resolved` before computing
  anything. Split is repo-grouped (no repo in both train and eval).
- **Gating:** training required a schema-valid, `decision=authorized` corpus
  authorization bound to the corpus-manifest hash and an empty output root.

## Results (leave-one-repo-out cross-validation)

Honest generalization: every repository is predicted only by models trained on
the _other_ repositories. AUROC is the primary metric (the corpus is highly
imbalanced, so accuracy is uninformative).

| Trajectory seen | OOF AUROC | 95% bootstrap CI |
| --------------- | --------: | ---------------: |
| First 25%       |     0.774 |   [0.755, 0.794] |
| First 50%       |     0.801 |   [0.784, 0.818] |
| Full            |     0.826 |   [0.811, 0.840] |

Per-repo full-trajectory OOF AUROC ranges **0.76–0.91** across all 11 repos
(weakest: iterative/dvc 0.76, conan 0.77; strongest: hydra 0.91, bokeh 0.87,
mypy 0.87). The model generalizes to unseen repositories, not just unseen runs.

**Baseline comparison:** the E-0 pre-registered study measured a plain
observable-feature logistic at ~0.70 AUROC (prefix-10) and the hand-wired
`ReferencePsyche` instinct/verification signals at ~0.34 (worse than chance).
PneumaBrain-v0.1 reaches 0.77 from just the first 25% of a trajectory and 0.83
on the full trajectory. (E-0 used a fixed 10-step window; the prefixes here are
trajectory fractions, so the comparison is indicative, not identical.)

**Calibration:** the raw logistic probabilities are already well-calibrated
(ECE ≈ 0.012–0.021 across prefixes). Platt calibration is applied in logit space
behind a guard that reverts to identity unless it strictly improves ECE and
keeps a non-negative slope, so calibration can never invert the advisory or
worsen calibration. Exact pre/post ECE per prefix is in the run's
`metrics.json` / `report.md`.

## How to use it

```python
from pneuma_lab.brain import predict

model = predict.load_model("build/brain/v0-1/elite-final/model.json")
# `trace` is a raw PneumaTrace dict with agent_trace frames.
frame = predict.risk_estimate(model, trace, prefix="prefix_50")
# -> {"frame_type": "RiskEstimateFrame", "failure_probability": 0.71,
#     "risk_bucket": "high", "recommended_use": "advisory_only",
#     "blocked_uses": ["no_runtime_authority", "no_verifier_bypass",
#                      "no_consciousness_claim"], ...}
```

Prefixes: `"prefix_25"`, `"prefix_50"`, `"full"`. Earlier prefixes trade accuracy
for earliness (useful mid-run); `full` is the strongest retrospective signal.

Intended consumption (all advisory, all gated downstream): the
`RiskEstimateFrame` feeds an `InstinctSignal` / `ControlPressureVector` that the
deterministic governance layer _may_ weigh — it can raise verification pressure
or suggest replanning, but can never abort, bypass the verifier, or change
authority by itself.

## Reproduce

```bash
# 1. Materialize the corpus (writes to gitignored build/)
python -m pneuma_lab.converters.openhands_sampled_training --mode full \
  --confirm-full-conversion \
  --input  C:/pneuma-data/processed/swe-gym/openhands-sampled/pneuma_traces.jsonl \
  --adapter-report C:/pneuma-data/processed/swe-gym/openhands-sampled/adapter_report.json \
  --output build/training_examples/openhands-sampled/full/examples.jsonl

# 2. Elite training (gated by the signed corpus authorization)
python -m pneuma_lab.brain.train_full \
  --traces C:/pneuma-data/processed/swe-gym/openhands-sampled/pneuma_traces.jsonl \
  --authorization docs/data/training-authorizations/pneuma-brain-v0.signed.json \
  --corpus-manifest docs/data/training-readiness/pneuma-brain-v0-corpus.json \
  --out build/brain/v0-1/elite-final
```

Deterministic: identical inputs produce byte-identical `model.json`. Artifacts
live under `build/` (gitignored); commit only report summaries if you want them
tracked.

## Limits & honest caveats

- One dataset, 11 repos, one label family. Breadth (more datasets, proxy heads
  for verification-pressure / failure-shape / difficulty) is future work; the
  framework masks unlabeled heads so it is data-extensible.
- Full-trajectory features see the whole run (retrospective); the prefix heads
  are the ones suitable for live early warning.
- Advisory only. No runtime integration exists or is authorized here. This model
  supports the Level-5 program as _infrastructure_; it is not itself evidence of
  interiority.
