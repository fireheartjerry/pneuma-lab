# Pneuma local-first foundation

This is the active engineering program for a laptop-scale, persistent,
self-monitoring software agent. It does not depend on a consciousness claim or
the archived Level ladder.

Canonical current status: [`docs/project-status.json`](../project-status.json).

## Model pins

| Role | Model | Revision | Status |
|---|---|---|---|
| Research | `Qwen/Qwen3.5-2B` | `15852e8c16360a2fea060d615a32b45270f8a8fc` | implementation ready, not trained |
| Promotion candidate | `Qwen/Qwen3.5-4B` | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` | gated on the 2B falsification result |
| Compatibility reference | `Qwen/Qwen3.5-397B-A17B` | `8472618112abcbd45acbcdc58436aff4233c23f7` | downloads and execution forbidden |

Junction positions are derived from the pinned `layer_types` schedule. The
loader refuses a changed revision, hidden width, layer count, or hybrid block
schedule before allocating model weights.

## What is implemented

- A fixed-width 256-dimensional recurrent core with 64 local memory slots, two
    candidate plans, four total latent microsteps, and base-specific projection
    shells.
- One primary full-attention junction, with a second junction unavailable until
    the recurrent design clears the early kill gate.
- Four-variant paired evaluation and bootstrap confidence gating.
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

## Current authorization truth

`docs/data/training-authorizations/pneuma-foundation-v0.pending.json` is
schema-valid but explicitly `not_authorized`. No positive-weight foundation
shard has been approved, no Qwen checkpoint has been downloaded by this work,
no foundation training run has occurred, and no model has been promoted to the
runtime.

`C:\pneuma-data` is immutable input. All derived shards, checkpoints, reports,
SQLite files, and weights belong under ignored `build/foundation/` storage.

## WSL2 environment

The official Qwen3.5 model card currently requires Transformers from its main
branch. Install the local foundation extra in WSL2, then install the current
Transformers main branch in the same environment:

```bash
wsl -d Ubuntu
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,foundation]"
pip install "transformers @ git+https://github.com/huggingface/transformers.git@main"
python -m pneuma_lab.foundation doctor
```

The first authorized run is a 100K-token correctness and throughput smoke test.
Its measured tokens/second, not a theoretical estimate, sets the wall-clock
forecast for later stages.

## Hardware-dependent gates

Hardware validation is currently `not_run`. The first authorized smoke run must
record peak VRAM, peak process RAM, tokens/second, p50 and p95 latency, maximum
GPU temperature, thermal-throttling intervals, and wall time. Promotion remains
blocked until those measurements demonstrate the 7.5GB VRAM, 24GB RAM, 20%
additional-FLOP, 25% p95-latency, and 85 C thermal limits. The read-only
`doctor` command reports environment prerequisites but does not satisfy these
measured gates.

## Claim boundary

Learned-subject outputs validate against
`schemas/learned-subject-profile.schema.json`. Foundation and runtime modules
cannot import the legacy evidence scorer. A successful engineering program can
therefore end with strong capabilities, persistence, self-monitoring, memory
integrity, and governance while making no consciousness designation.
