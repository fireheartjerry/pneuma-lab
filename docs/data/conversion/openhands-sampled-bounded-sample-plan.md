# OpenHands Sampled Bounded-Sample Conversion Plan

Status: planning only.

This document plans a future bounded processed-sample conversion pass for
`swe-gym-openhands-sampled`. It does not implement a converter, read the full
processed JSONL, emit converted examples, write outputs to `C:/pneuma-data`,
train models, run E1/E2, calibrate, change runtime behavior, implement
J-space/Jacobian Lens, process SWE-chat, inspect raw sensitive content, mutate
raw or processed data, or make consciousness claims.

## 1. Purpose

The next implementation should convert only a tiny bounded sample of processed,
redaction-verified OpenHands sampled `PneumaTrace` records into canonical
`PneumaTrainingExample` records. This is a bridge between the committed
fixture-only converter and any later full conversion.

The bounded pass should answer one narrow question: can the existing
fixture-first converter safely handle a small number of real processed,
redaction-verified `PneumaTrace` envelopes while preserving schema validity,
determinism, conservative training authorization, and input leakage controls?

## 2. Source Constraints

Source dataset:

| Field | Value |
|---|---|
| Dataset ID | `swe-gym-openhands-sampled` |
| Dataset family | `swe-gym` |
| Processed path | `C:/pneuma-data/processed/swe-gym/openhands-sampled/` |
| Adapter report | `C:/pneuma-data/processed/swe-gym/openhands-sampled/adapter_report.json` |
| Adapter | `openhands-sampled` v0.1.0 |
| Envelope schema | `PneumaTrace` v0.2.0 |
| Source revision | `baf3a4e4bff514d48ddc08a93a2ade5c126212c7` |

Adapter report metadata:

| Field | Value |
|---|---:|
| Source rows | 6,055 |
| Traces emitted | 6,055 |
| Valid traces | 6,055 |
| Invalid traces | 0 |
| Skipped rows | 0 |
| Agent steps | 114,461 |
| Resolved | 491 |
| Unresolved | 5,564 |
| Task joins present | 6,055 |
| Task joins missing | 0 |

Processed artifact metadata observed without reading JSONL contents:

| Artifact | Size |
|---|---:|
| `adapter_report.json` | 1,079 bytes |
| `pneuma_traces.jsonl` | 384,761,698 bytes |
| `trace_index.jsonl` | 3,228,770 bytes |
| `pneuma_traces.invalid.jsonl` | 0 bytes |

Hashes from the adapter report:

| Artifact | SHA-256 |
|---|---|
| `pneuma_traces.jsonl` | `6ec06b724e71be2735b2495291a3d5102bc3efa4f24f0d03d824f549f79feb6b` |
| `trace_index.jsonl` | `b1d99a62197cb6091067a3ae585f05459ec3f59a77699632e674856f8e6637a1` |
| `pneuma_traces.invalid.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Redaction status: the processed outputs are redaction-verified by the adapter
report. Deterministic redaction totals are 103 emails, 4 AWS access keys, and
16 assigned secrets.

Known caveats:

- Labels are OpenHands/SWE-Gym harness outcomes, not Pneuma outcomes.
- The traces describe OpenHands behavior, not Pneuma or 9to5 interiority.
- Class balance is strongly skewed: 491 resolved and 5,564 unresolved.
- Timestamps are synthetic ordinals; order is preserved, wall-clock time is not.
- Raw trajectory content remains non-targeted and must not be read.
- Counts and hashes should be reconciled against `adapter_report.json`, not
  hand-maintained in generated outputs.

## 3. Bounded Sample Policy

Future implementation policy:

- Require an explicit `--limit`; no implicit full conversion path.
- Recommended bounded limit: `10` traces.
- Hard maximum: `25` traces. Larger values must fail closed.
- Deterministic selection: take the first `N` lines from
  `pneuma_traces.jsonl` in adapter emission order, then stop reading
  immediately. The adapter report states the emission sort key is
  `instance_id, run_id, source_file, source_row`.
- No random unseeded sampling.
- No full `pneuma_traces.jsonl` scan in the bounded pass.
- No raw dataset reads.
- No SWE-chat reads.
- No writes to `C:/pneuma-data` or the processed dataset root.
- Optional later improvement: a manifest-selected sample may be introduced if a
  small reviewed manifest is committed or generated under `build/`; that should
  remain a separate explicit decision.

This first bounded pass is a smoke and safety gate, not a representative
training sample and not a class-balance study.

## 4. Input And Output Paths

Future inputs:

```text
C:/pneuma-data/processed/swe-gym/openhands-sampled/pneuma_traces.jsonl
C:/pneuma-data/processed/swe-gym/openhands-sampled/adapter_report.json
```

Future default outputs should be repo-local generated artifacts under ignored
`build/`, for example:

```text
build/training_examples/openhands-sampled/bounded-sample/examples.jsonl
build/training_examples/openhands-sampled/bounded-sample/conversion_report.json
build/training_examples/openhands-sampled/bounded-sample/hash_manifest.json
```

Do not create these paths in this planning pass. Do not commit generated
bounded-sample outputs. If small golden artifacts are later needed for tests,
use committed synthetic fixtures instead of real processed rows unless the user
explicitly approves a tiny redaction-verified fixture policy.

## 5. Converter Behavior

Reuse the committed fixture-first converter:
`src/pneuma_lab/converters/openhands_sampled_training.py`.

The bounded implementation should:

- open `pneuma_traces.jsonl` only long enough to load the requested bounded
  number of processed `PneumaTrace` records;
- call the existing converter library for each trace;
- emit one full-trace `TrajectoryExample` per loaded `PneumaTrace`;
- validate each emitted record against
  `schemas/pneuma-training-example.schema.json`;
- produce a small conversion report with requested limit, loaded count,
  emitted count, invalid/quarantined count, source hashes, adapter report ref,
  converter version, and schema version;
- produce a deterministic hash manifest for examples, report, and manifest;
- preserve conservative defaults:
  `model_use_tier: train_after_adapter` and `training_weight: 0.0`;
- keep `target.resolved` only in `target`, sourced from approved harness outcome
  fields;
- keep `input` observable-only, using trace IDs, run IDs, task/repo metadata,
  trajectory counts, tool call summaries, retry summaries, strategy switch
  summaries, error marker summaries, length summaries, digest metadata, and
  feature refs;
- keep `evidence_refs` non-empty, with refs for trace ID, adapter report,
  schema, and bounded conversion manifest metadata.

Forbidden input fields and keys include:

- `resolved`
- `outcome`
- `labels`
- `gold`
- `oracle`
- `fail_to_pass`
- `pass_to_pass`
- `patch`
- `verdict`

## 6. Validation Checks

Future tests/checks should prove:

- bounded sample size is enforced;
- `--limit` is required;
- limit values above the hard cap fail closed;
- no raw dataset path is opened;
- no SWE-chat path is opened;
- no full processed JSONL conversion mode exists in this pass;
- no writes to `C:/pneuma-data`;
- two bounded runs produce byte-identical examples and hash manifests;
- all emitted examples validate against
  `schemas/pneuma-training-example.schema.json`;
- emitted count reconciles with requested sample size;
- one loaded trace emits one full-trace `TrajectoryExample`;
- `task_type` is `RISK_PREDICTION`;
- `task_mask` is exactly `["RISK_PREDICTION"]`;
- `model_use_tier` is `train_after_adapter`;
- `training_weight` is `0.0`;
- `evidence_refs` are non-empty and include trace/schema/report/manifest refs;
- `input` does not contain the forbidden leakage keys listed above;
- source refs point back to adapter report metadata and trace IDs;
- no generated output contains raw data paths, raw objective text, oracle test
  lists, patch material, verifier answers, or target-bearing input fields.

Implementation should also retain the existing fixture converter tests so the
fixture-only layer remains protected independently from the processed bounded
sample path.

## 7. CLI Design

Add a conservative CLI to the existing converter module only after this plan is
approved. Keeping the CLI in
`pneuma_lab.converters.openhands_sampled_training` makes it share the same
library conversion code as the fixture tests while keeping full conversion
unimplemented.

Example future command:

```powershell
python -m pneuma_lab.converters.openhands_sampled_training `
  --input C:/pneuma-data/processed/swe-gym/openhands-sampled/pneuma_traces.jsonl `
  --adapter-report C:/pneuma-data/processed/swe-gym/openhands-sampled/adapter_report.json `
  --output build/training_examples/openhands-sampled/bounded-sample/examples.jsonl `
  --report build/training_examples/openhands-sampled/bounded-sample/conversion_report.json `
  --hash-manifest build/training_examples/openhands-sampled/bounded-sample/hash_manifest.json `
  --limit 10 `
  --mode bounded-sample
```

CLI requirements:

- require `--mode bounded-sample`;
- require explicit `--limit`;
- enforce hard cap `25`;
- refuse any value like `--mode full` or missing mode;
- default output paths to repo-local `build/` only when omitted;
- never default outputs to `C:/pneuma-data`;
- read only the first `N` processed trace lines and stop;
- require `--adapter-report` and include its hashes in report metadata;
- emit examples, report, and hash manifest;
- perform schema validation before writing final outputs;
- write atomically through temporary files under the selected output directory;
- do not train, fit estimators, calibrate, run E1/E2, or touch runtime code.

Library API requirements:

- expose a small bounded reader function that accepts a path and explicit
  limit;
- keep `convert_trace` and `convert_traces` as pure in-memory conversion
  helpers;
- keep report and hash generation deterministic and testable without accessing
  `C:/pneuma-data`.

## 8. Non-Goals

- No full conversion.
- No ML training.
- No estimator fitting.
- No E1/E2 execution.
- No calibration.
- No runtime integration.
- No verifier bypass.
- No J-space or Jacobian Lens work.
- No SWE-chat processing.
- No raw sensitive content reading.
- No raw data mutation.
- No processed data mutation.
- No writes to `C:/pneuma-data`.
- No committed large generated outputs.
- No consciousness, Level 4/5, interiority, or moral-patienthood claims.

## 9. Recommended Implementation Prompt

Use this prompt after this planning document is approved:

```text
Work in C:\pneuma-lab. Implement the bounded processed-sample conversion pass
for OpenHands sampled PneumaTrace records into PneumaTrainingExample records.

Do not run full conversion. Do not train models, run E1/E2, calibrate, modify
runtime behavior, implement J-space/Jacobian Lens, process SWE-chat, inspect raw
sensitive content, mutate raw or processed data, or write outputs to
C:/pneuma-data.

Reuse src/pneuma_lab/converters/openhands_sampled_training.py. Add a
conservative bounded-sample CLI/API that requires --mode bounded-sample and an
explicit --limit, enforces hard cap 25, reads only the first N processed
PneumaTrace JSONL lines, calls the existing converter library, validates every
PneumaTrainingExample against schemas/pneuma-training-example.schema.json, and
writes examples/report/hash manifest only under repo-local build/ paths by
default. Preserve model_use_tier: train_after_adapter and training_weight: 0.0.
Add tests for limit enforcement, determinism, schema validation, leakage keys,
evidence refs, no full conversion, no raw/SWE-chat access, and no
C:/pneuma-data writes.

Validate with:
python -m pytest tests/ -q
git diff --check
```

Exact next implementation step: implement the bounded-sample CLI/API with the
strict limit and repo-local output policy above.
