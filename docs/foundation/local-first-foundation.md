# Pneuma local-first foundation

This is the active engineering program for a laptop-scale, persistent,
self-monitoring software agent. It does not depend on a consciousness claim or
the archived Level ladder.

Canonical current status: [`docs/project-status.json`](../project-status.json).

## Model pins

| Role                    | Model                    | Revision                                   | Status                                        |
| ----------------------- | ------------------------ | ------------------------------------------ | --------------------------------------------- |
| Research                | `Qwen/Qwen3.5-2B`        | `15852e8c16360a2fea060d615a32b45270f8a8fc` | local ladder complete through 8M (2026-07-21) |
| Promotion candidate     | `Qwen/Qwen3.5-4B`        | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` | gated on the 2B falsification result          |
| Compatibility reference | `Qwen/Qwen3.5-397B-A17B` | `8472618112abcbd45acbcdc58436aff4233c23f7` | downloads and execution forbidden             |

Junction positions are derived from the pinned `layer_types` schedule. The
loader refuses a changed revision, hidden width, layer count, or hybrid block
schedule before allocating model weights.

## What is implemented

- A fixed-width 256-dimensional recurrent core with 64 local memory slots, two
  candidate plans, four total latent microsteps, and base-specific projection
  shells.
- One primary full-attention junction, with a second junction unavailable until
  the recurrent design clears the early kill gate.
- Four-variant paired evaluation and bootstrap confidence gating, plus the
  offline honest-proxy harness (`pneuma_lab.foundation.variants` and the
  `variant-eval` CLI verb) that produces the four paired result files from a
  trained run's last checkpoint over the shard's repo-disjoint held-out
  (validation) records. Every emitted file carries
  `task_semantics: held_out_risk_prediction_correctness` and
  `no_consciousness_claim: true`; the two pre-registered baselines run with
  deterministic untrained initializations until baseline training is
  authorized, and the index manifest records that provenance.
- NF4/double-quant local configuration, staged token ceilings, learning-rate
  selection, gradient accumulation, atomic resume checkpoints, and thermal
  stop rules.
- Content-addressed authorized shards under ignored `build/` storage, ten-group
  governance, and repo/issue/task/commit/patch/text contamination checks.
- SQLite/FTS5 event, knowledge, lineage, and meta-memory with reversible
  suppression and hard erasure that revokes affected adapters.
- Signed local repository/tool scopes and unconditional sole-operator denial of
  deployment, spending, public communication, credentials, destructive
  operations, privilege changes, and self-modification.
- The complete training launch surface: pinned 2B model cache with verified
  snapshot receipts, a no-gradient dry run with parity/latency/FLOPs gates,
  live telemetry and schema-valid run manifests, exact optimizer-boundary
  checkpoint/resume with per-boundary `validation_batches.json` persistence
  (the token-weighted per-batch rows the evaluate CLI consumes), a
  hash-verifying single-document data loader, the preflight-first gated
  runner, claim-bounded evaluation and reports, the
  `python -m pneuma_lab.foundation` CLI (fifteen commands with strict
  command separation), an authorized-only cloud reproduction bundle behind a
  hard budget quote gate, and the drift-checked operator guide
  `START-HERE-TRAINING.md`.

## Launch runbook

`START-HERE-TRAINING.md` at the repository root is the operator runbook. Every
fenced command in it is validated against the real CLI by
`python -m pneuma_lab.foundation.operator_guide START-HERE-TRAINING.md`, and
its final checklist item — the actual `train` command — stays unchecked until
the operator deliberately runs it. The canonical launch truth lives in
`docs/project-status.json` under `foundation_training_launch`
(`training_status: local_8m_completed_doubling_gate_stopped_ladder`,
`optimizer_steps: 1430`).

## Current authorization truth

The committed
`docs/data/training-authorizations/pneuma-foundation-v0.pending.json` remains
schema-valid and `not_authorized`; live authorizations are exact, per-stage,
operator-approved manifests under ignored `build/foundation/authorizations/`.
Under such per-stage authorizations the full local ladder completed on
2026-07-20/21: the 100K smoke stage (three runs, 2e-4 selected), the 500K
stage (32 steps, single-lane supply exhausted), the two-lane 2M stage (330
steps, falsification kill gate PASSED, +28.3 points over the strongest
baseline), a one-time cloud 2M reproduction on RunPod (under $2, pod
terminated), and the two-lane 8M stage (693 steps, 4,193,262 tokens — the
entire train supply; the 8M token ceiling is unreachable until new lanes
earn readiness). The 8M falsification gate PASSED with the identical
+28.3-point margin, but the held-out resolved rate was exactly equal to the
2M result (2180/3399 = 64.14%), so the pre-registered ≥0.5-point-per-
doubling gate stops the ladder at 8M as a recorded negative result. 16M is
unreachable without both new gradient lanes and a fresh doubling gain. No
model has been promoted to the runtime.

`C:\pneuma-data` is immutable input. All derived shards, checkpoints, reports,
SQLite files, and weights belong under ignored `build/foundation/` storage.

Authorization independently reloads the tokenizer from the exact Task 7 cache
path `build/<cache-root>/models/2b/<pinned-revision>` with network access off.
It verifies the snapshot receipt before loading, after loading, and after
recounting every shard prompt and target with special tokens disabled. The
scope digest binds the cache path, receipt digest, and full snapshot digest.

Authorization evidence is also memory bounded. Aggregate held evidence is
limited by stage and capped at 2 GiB; strict JSON/JSONL parsing is budgeted for
approximately 8x transient amplification so verification remains within the
24 GiB local process envelope. Candidate and final authorization manifests are
each capped at 8 MiB before parsing.

## WSL2 environment

The environment is fully pinned (uv 0.11.28, Python 3.12, `uv.lock`, and
Transformers at commit `11ed2ff4df5fdfb3117f0e3365ef6ad94081ba69` per the
Qwen3.5 model card). The setup script installs it and runs the doctor; it can
neither authorize nor train:

```bash
wsl -d Ubuntu
cd /mnt/c/pneuma-lab
bash scripts/foundation/setup-wsl.sh
source .venv/bin/activate
python -m pneuma_lab.foundation doctor
```

The first authorized runs were the 100K-token correctness and throughput
smoke tests. Their measured 312-339 tokens/second, not a theoretical estimate,
sets the wall-clock forecast for later stages (roughly 1.7 hours for 2M and
7 hours for 8M tokens locally).

## Hardware-dependent gates

The 100K smoke runs measured: peak 2.82 GiB process VRAM (limit 7.5), zero
thermal-throttle intervals with live GPU temperatures 63-73 °C (limit 85),
312-339 tokens/second, and ~278-301 s wall time per run. The no-gradient dry
run measured a −5.3% enabled-core p95 latency overhead (limit +25%) with
parity error 0.0 across all five cache boundaries. Promotion to 4B remains
blocked on the later-stage falsification results, not on these hardware
gates.

## Claim boundary

Learned-subject outputs validate against
`schemas/learned-subject-profile.schema.json`. Foundation and runtime modules
cannot import the legacy evidence scorer. A successful engineering program can
therefore end with strong capabilities, persistence, self-monitoring, memory
integrity, and governance while making no consciousness designation.
