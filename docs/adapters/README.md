# Dataset Adapters (Phase 3)

`src/pneuma_lab/adapters/` converts external SWE datasets into durable, validated,
byte-deterministic **`PneumaTrace`** artifacts.

## PneumaTrace envelope

A `PneumaTrace` (`schemas/pneuma-trace.schema.json`, `x-pneuma-schema-kind:
"envelope"`) is an **envelope only** — it introduces no new cognition semantics. It
wraps a list of _existing, validated_ Pneuma input frames plus:

- `provenance` (dataset, source_id, hf_repo, hf_revision, source_file, source_row)
  and `adapter` (name, version) — kept separate (origin vs. transform).
- `build` — deterministic metadata: `content_hash`, `generated_from`,
  `frame_sources` (which frames are dataset-derived vs. synthetic).
- `privacy` — always present (`status`, `pii_scanned`, `redactions`), so the shape
  is identical across datasets (SWE-chat is not a special case).
- `labels` (factual metadata + capability booleans), `oracle` (test oracle),
  `reference_supervision` (gold patch, test patch, hints + sha256s).
- `frames` — the validated input frames.

Determinism: canonical JSON (`sort_keys`, compact separators, `ensure_ascii=False`,
LF), `blake2b` identity ids (`trace_id`/`run_id`) and a `blake2b` content hash; no
wall-clock, no randomness. `adapters/envelope.py` is dataset-agnostic; each dataset
gets its own `adapters/<dataset>.py`.

## `swe_gym_lite` (first adapter)

Task-only. Per SWE-Gym-Lite row it emits **one real dataset-derived `world-frame`**
(repo@base_commit, problem_statement, `test_state: not-run`) + **one minimal
synthetic `governance-frame`** (verifier_isolation, kill_switch=off). No
`agent-trace-frame`/`memory-frame` — no agent ran, so no faked cognition. The gold
patch, test patch, `FAIL_TO_PASS`/`PASS_TO_PASS`, and hints are **supervision in the
envelope**, not psyche frames.

Policy: valid traces → `pneuma_traces.jsonl`; built-but-invalid → quarantined to
`pneuma_traces.invalid.jsonl`; unbuildable rows → `skipped_source_ids`; only
adapter/system bugs hard-crash.

Run (out-of-repo output under `C:/pneuma-data/processed/swe-gym/lite/`):

```
python -m pneuma_lab.adapters.swe_gym_lite
```

Outputs: `pneuma_traces.jsonl`, `pneuma_traces.invalid.jsonl`, `trace_index.jsonl`,
`adapter_report.json` (all byte-deterministic; the report is timestamp-free and
carries whole-file sha256s). A tiny **hermetic golden fixture** under
`fixtures/adapters/swe_gym_lite/` keeps tests free of `/c/pneuma-data` and network;
`--emit-fixture` fails on drift, `--update-fixture` regenerates it.

Design + plan:

- `docs/superpowers/specs/2026-07-07-swe-gym-lite-pneuma-trace-adapter-design.md`
- `docs/superpowers/plans/2026-07-07-swe-gym-lite-pneuma-trace-adapter.md`

## Next

Phase 3.1: fuzzy-join `OpenHands-SFT-Trajectories` → real `agent-trace-frame`s.
Then reuse the envelope for SWE-bench, Multi-SWE-bench, and (privacy-gated) SWE-chat.
