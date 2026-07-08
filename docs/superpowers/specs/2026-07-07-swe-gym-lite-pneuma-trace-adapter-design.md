# Phase 3 — SWE-Gym-Lite → PneumaTrace Adapter (Design Spec)

Date: 2026-07-07. Status: **design, awaiting review**. Scope: the first dataset
adapter for Pneuma Lab. Deliberately small and boringly correct — it establishes
the durable, deterministic, provenance-carrying pipeline that the messier datasets
(SWE-chat, trajectory corpora) will reuse.

## 1. Goal & non-goals

**Goal:** convert each SWE-Gym-Lite task row into a durable, validated,
byte-deterministic `PneumaTrace` JSONL artifact.

Flow: `raw parquet row → PneumaTrace envelope → existing validated frames + oracle/supervision → out-of-repo artifact + hermetic test fixture → deterministic adapter_report`.

**Non-goals (this slice):**

- No agent trajectories (no OpenHands join) — that is **Phase 3.1**.
- No synthetic/faked runtime cognition (no `agent-trace-frame`, no `memory-frame`).
- No new cognition schema. The only new schema is the (non-cognitive) envelope.
- No ML training. No changes to 9to5.

## 2. Output artifact: `PneumaTrace` envelope

`PneumaTrace` is an **envelope only** — provenance + privacy + labels + oracle +
supervision, wrapping a list of _existing, validated_ Pneuma input frames. Top level:

    {
      "schema_version": "0.1.0",
      "trace_id": "ptrace:<blake2b(dataset, instance_id, hf_revision)>",
      "run_id":   "run:<same_hash>",
      "adapter":  { "name": "swe-gym", "version": "0.1.0" },
      "provenance": {
        "dataset": "swe-gym", "dataset_variant": "SWE-Gym-Lite",
        "source_id": "getmoto__moto-5752",
        "hf_repo": "SWE-Gym/SWE-Gym-Lite", "hf_revision": "f70b1a29…",
        "source_file": "raw/swe-gym/SWE-Gym-Lite/data/train-00000-of-00001.parquet",
        "source_row": 0
      },
      "build": {
        "deterministic": true,
        "content_hash": "<blake2b of canonical trace, self-excluded>",
        "generated_from": ["dataset", "instance_id", "hf_revision"],
        "frame_sources": {
          "world-frame": "dataset-derived",
          "governance-frame": "synthetic-contract-minimum"
        }
      },
      "privacy": { "status": "clean", "pii_scanned": false, "redactions": [] },
      "validation": { "schema": "pneuma_trace.schema.json", "status": "valid" },
      "labels": {
        "instance_id": "getmoto__moto-5752", "benchmark": "swe-gym-lite",
        "repo": "getmoto/moto", "language": "python", "split": "train",
        "task_family": "issue-resolution",
        "has_patch": true, "has_tests": true, "has_trajectory": false
      },
      "oracle": {
        "kind": "test-based",
        "fail_to_pass": ["tests/…::test_x"],
        "pass_to_pass": ["tests/…::test_y"]
      },
      "reference_supervision": {
        "gold_patch": "diff --git …",   "gold_patch_sha256": "…",
        "test_patch": "diff --git …",   "test_patch_sha256": "…",
        "hints_text": "Here's the culprit: …"
      },
      "frames": [ /* world-frame, governance-frame */ ]
    }

**Field-placement principles (settled):**

- `adapter` (transform) is separate from `provenance` (origin) — clean audit.
- `privacy` is always present (identical shape across datasets; SWE-chat is not a
  special case). SWE-Gym-Lite is `status: "clean"`.
- No wall-clock timestamps anywhere top-level. Deterministic metadata only (`build`).
  Real dataset timestamps live _inside_ frames (`created_at`).
- `labels` = cheap factual metadata + boolean capabilities.
- `oracle` = the test oracle.
- `reference_supervision` = gold patch, test patch, hints (+ sha256s). Hints are
  supervision material, not neutral labels.
- Gold patch / tests / hints are **never** psyche-input frames.

## 3. Frames emitted (honest, task-only)

Exactly two frames, both contract-valid, no faked cognition:

**`world-frame`** (real, dataset-derived — the exteroception at t0):

- `run_id` = the sibling run id; `phase` = `"preamble"`; `timestamp` = row
  `created_at` normalized to ISO-8601 UTC.
- `repo_state` = `{ head_sha: <base_commit>, repo: <repo> }` (repo via
  `additionalProperties`).
- `objective` = `problem_statement`.
- `test_state` = `{ ran: false, not_yet_run: true }` (honest — tests were not run
  in this trace; the pass/fail oracle lives in `labels`/`oracle`).

**`governance-frame`** (minimal synthetic, contract validity only):

- `verifier_isolation: true` (schema `const`), `kill_switch_state: "off"` (the
  schema's own definition: "the psyche is a byte-identical no-op" — correct: this
  is data, not a live run). `run_id`, `timestamp` as above.

**Not emitted:** `agent-trace-frame` (no agent ran), `memory-frame` (nothing
retrieved for a cold task). Adding real `agent-trace-frame`s is Phase 3.1.

**Frame origin is machine-readable, not prose-only.** `build.frame_sources`
records the provenance of each emitted frame — `world-frame: "dataset-derived"`,
`governance-frame: "synthetic-contract-minimum"` — so downstream consumers can tell
real exteroception from synthetic contract-filler without reading this doc.

## 4. Determinism (the crux)

Pneuma's replay tests byte-compare output; the adapter must be fully deterministic
— no wall-clock, no randomness.

- **Canonical JSON** (hashing + file output):
  `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`,
  UTF-8, one object per line + `\n`.
- **`trace_id` / `run_id`** — sibling ids from one identity hash:
  `H = blake2b(dataset + instance_id + hf_revision)`; `trace_id = "ptrace:"+H`,
  `run_id = "run:"+H`.
- **`content_hash`** — integrity hash over the canonical JSON of the fully built
  trace with `build.content_hash` blanked and the `validation` block excluded (no
  self-reference). Hashing is computed **before** attaching the final `validation`
  block, or equivalently with `validation` removed — so the ordering of build-vs-hash
  is never ambiguous. `trace_index.content_hash` copies this exact value.
- **`timestamp`** — real `created_at` → UTC ISO-8601. No current time.
- **Emission order** — sorted by `instance_id` (do not trust parquet row order);
  `provenance.source_row` still records the original parquet index.

## 5. Input & output

- **Input (source of truth):** the **raw** SWE-Gym-Lite parquet
  `C:/pneuma-data/raw/swe-gym/SWE-Gym-Lite/data/train-00000-of-00001.parquet` (via
  pyarrow). NOT `normalized_metadata.jsonl` (it intentionally drops patches/hints/tests).
- **Output (out-of-repo), variant-scoped:** `C:/pneuma-data/processed/swe-gym/lite/`
  - `pneuma_traces.jsonl` — valid traces only (trustworthy for replay/training).
  - `pneuma_traces.invalid.jsonl` — quarantined built-but-invalid traces (full
    validation errors + `source_id` + `trace_id` + which schema failed).
  - `trace_index.jsonl` — lightweight index (below).
  - `adapter_report.json` — deterministic summary (below).

## 6. Validation & failure policy

Three validations per trace: envelope vs `pneuma_trace.schema.json`; each frame vs
its existing schema — reusing `src/pneuma_lab/schemas/validate.py`.

- **valid** → `pneuma_traces.jsonl`.
- **built-but-invalid** → `pneuma_traces.invalid.jsonl`; `source_id` in
  `invalid_source_ids`.
- **unbuildable** (e.g. missing `base_commit`) → no trace; `{source_id, reason}` in
  `skipped_source_ids`; continue (dirty data is never a crash).
- **hard crash only** for adapter/system bugs: schema-loader failure, unreadable
  input, or a **nondeterminism violation**.

SWE-Gym-Lite is clean → we expect `invalid: 0`, `skipped: 0`; the policy is
future-proofing for the messy datasets.

## 7. `trace_index.jsonl` (one row per valid trace)

    { "trace_id":"ptrace:…", "run_id":"run:…", "source_id":"getmoto__moto-5752",
      "repo":"getmoto/moto", "split":"train", "benchmark":"swe-gym-lite",
      "has_patch":true, "has_tests":true, "has_trajectory":false,
      "num_frames":2, "frame_kinds":["world-frame","governance-frame"],
      "oracle_kind":"test-based", "privacy_status":"clean",
      "validation_status":"valid", "content_hash":"…" }

## 8. `adapter_report.json` (deterministic — no timestamps)

    { "adapter_report_schema_version":"0.1.0",
      "adapter":{"name":"swe-gym","version":"0.1.0"},
      "dataset":"swe-gym","hf_repo":"SWE-Gym/SWE-Gym-Lite","hf_revision":"f70b1a29…",
      "counts":{"source_rows":230,"traces_emitted":230,"valid":230,"invalid":0,"skipped":0},
      "frame_validation":{"world-frame":{"valid":230,"invalid":0},
                          "governance-frame":{"valid":230,"invalid":0}},
      "oracle_coverage":{"fail_to_pass_present":230,"pass_to_pass_present":230,
                         "gold_patch_present":230,"test_patch_present":230,"hints_present":N},
      "ordering":{"emission_sort_key":"instance_id","source_row_preserved":true},
      "skipped_source_ids":[], "invalid_source_ids":[],
      "traces_file_sha256":"…", "trace_index_file_sha256":"…",
      "invalid_traces_file_sha256":"…", "warnings":[] }

All four output files are byte-comparable across reruns. `pneuma_traces.invalid.jsonl`
is **always created and hashed even when empty** — hashing emptiness looks silly but
is deterministic, and a present-but-empty quarantine file beats an absent one.
`hints_present` = count of rows with non-empty `hints_text`.

## 9. Code & schema layout (in-repo)

- **`schemas/pneuma_trace.schema.json`** — Draft 2020-12; repo conventions
  (`$schema`, `$id`, `title`, `description`, `type`, `x-pneuma-version`); marker
  **`x-pneuma-schema-kind: "envelope"`** (a contract, not a frame).
- **`src/pneuma_lab/schemas/__init__.py`** — expose three buckets: input frames,
  output frames, **envelopes**.
- **`src/pneuma_lab/adapters/envelope.py`** — dataset-agnostic: canonical JSON,
  deterministic id derivation, `content_hash`, envelope validation, serialization.
- **`src/pneuma_lab/adapters/swe_gym_lite.py`** — dataset-specific: read parquet,
  map fields, build world/governance frames + labels/oracle/supervision,
  validate/quarantine, write the four files + report.
- **`src/pneuma_lab/adapters/__main__.py`** — CLI.

**CLI:**

    python -m pneuma_lab.adapters.swe_gym_lite \
        [--input PARQUET] [--out DIR] [--hf-revision SHA] [--emit-fixture]

Defaults: pinned raw Lite parquet → `processed/swe-gym/lite/`. `--emit-fixture` is
a **drift check** against the committed golden fixture (fails on mismatch);
regeneration requires an explicit `--update-fixture` (or env var).

## 10. Hermetic test fixture

A tiny committed sample so `pytest` never touches `/c/pneuma-data` or the network:

- `fixtures/adapters/swe_gym_lite/` — ~3–5 SWE-Gym-Lite rows (small patches, no PII,
  with a `LICENSE_PROVENANCE.md` note), clearly marked a **test fixture** (not
  redistributed dataset bulk), plus frozen golden `pneuma_traces.jsonl` /
  `pneuma_traces.invalid.jsonl` / `trace_index.jsonl` / `adapter_report.json`.
- **Hard constraint:** fixture rows preserve **only the minimum fields required for
  the tests**, each with source attribution + license/provenance note. This stops
  "tiny fixture" from quietly drifting into "oops, we committed half a dataset for
  convenience."
- Governed by `.gitignore` review so only the tiny fixture is committed.

## 11. Test suite (TDD, all hermetic)

1. Schema validity — `pneuma_trace.schema.json` parses; all `schemas/` load;
   envelope registered in the `envelopes` bucket.
2. Envelope unit — deterministic `trace_id`/`run_id`; `content_hash` stability &
   self-exclusion; canonical-JSON round-trip.
3. Frame construction — world/governance frames from a sample row validate against
   their existing schemas via `validate.py`.
4. Golden byte-match — adapter on the fixture input → byte-identical to committed
   golden outputs.
5. Two-run determinism — same input twice → byte-identical.
6. Quarantine + skip — missing `base_commit` → `skipped_source_ids`; forced invalid
   frame → `pneuma_traces.invalid.jsonl`.
7. Malformed envelope rejected by `pneuma_trace.schema.json`.
8. Oracle-coverage counts — report counts (fail/pass_to_pass, gold/test patch,
   hints present) are correct (catches silent field-dropping).
9. Fixture-drift protection — `--emit-fixture` fails on drift; rewrite only via
   explicit update mode.

## 12. Definition of done

- `schemas/pneuma_trace.schema.json` exists, valid, registered in `envelopes` bucket.
- `envelope.py` + `swe_gym_lite.py` + CLI produce the four files under
  `processed/swe-gym/lite/` for all 230 Lite rows, byte-deterministically.
- All 9 tests pass; full suite (`pytest tests/ -q`) stays green.
- Tiny hermetic golden fixture committed; no `/c/pneuma-data` or network in tests.
- No raw dataset bulk in the repo; no 9to5 changes; no ML training.
- Nearest docs updated (io-contract / a short adapter note).

## 13. Next (out of scope here)

- **Phase 3.1:** fuzzy-join `OpenHands-SFT-Trajectories` → real `agent-trace-frame`s.
- Then reuse the same envelope/pipeline for SWE-bench, Multi-SWE-bench, and the
  privacy-gated SWE-chat (where `privacy` finally earns its keep).
