# OpenHands Sampled Bounded Smoke Review

Status: reviewed bounded artifact output only.

This review inspected the existing bounded-sample artifacts under
`build/training_examples/openhands-sampled/bounded-sample/`. It did not
implement new conversion behavior, run full conversion, train models, run E1/E2,
calibrate, change runtime behavior, implement J-space/Jacobian Lens, process
SWE-chat, inspect raw sensitive content, mutate raw or processed data, or write
outputs to `C:/pneuma-data`.

## Reviewed Artifacts

| Artifact | Size |
|---|---:|
| `examples.jsonl` | 27,809 bytes |
| `conversion_report.json` | 1,280 bytes |
| `hash_manifest.json` | 665 bytes |

The generated artifacts remain under ignored `build/` paths and should not be
committed.

## Pass/Fail Summary

| Check | Result | Evidence |
|---|---|---|
| Requested limit is 10 | PASS | `conversion_report.input.requested_limit == 10` |
| Loaded trace count is 10 | PASS | `conversion_report.input.loaded_traces == 10` |
| Emitted example count is 10 | PASS | `conversion_report.output.examples_emitted == 10` |
| Invalid examples are 0 | PASS | `conversion_report.output.invalid_examples == 0` |
| Quarantined examples are 0 | PASS | `conversion_report.output.quarantined_examples == 0` |
| All examples validate against schema | PASS | 10 examples, 0 schema errors |
| Target appears only in `target` | PASS | `target` has only `resolved`; no forbidden input hits |
| Input is leakage-free by key scan | PASS | 0 hits for forbidden keys in `input` |
| Conservative training defaults preserved | PASS | all examples use `train_after_adapter` and `training_weight: 0.0` |
| Task fields preserved | PASS | all examples use `RISK_PREDICTION` and `["RISK_PREDICTION"]` |
| Evidence refs are non-empty | PASS | each example includes trace, adapter report, schema, and manifest refs |
| Adapter report metadata is present | PASS | source counts, hashes, and redaction totals are present |
| Example/report hashes verify | PASS | `examples_jsonl_sha256` and `conversion_report_json_sha256` match bytes on disk |

Forbidden input keys checked:

- `resolved`
- `outcome`
- `labels`
- `gold`
- `oracle`
- `fail_to_pass`
- `pass_to_pass`
- `patch`
- `verdict`

## Findings

1. The 10 emitted `PneumaTrainingExample` records are schema-valid and shaped as
   intended: one full-trace `TrajectoryExample` per processed `PneumaTrace`.
2. `input` is observable-only in the reviewed sample. It contains trace/run/task
   identifiers, repo metadata, trajectory counts, tool/retry/error/length
   summaries, feature refs, and objective digest/length metadata. It does not
   include raw objective text, oracle lists, patch material, verifier answers,
   outcome blocks, labels blocks, or `resolved`.
3. `target.resolved` is isolated in `target`, with harness provenance preserved
   through `label_provenance`.
4. `evidence_refs` are useful enough for this bounded stage: every example
   points to its trace ID, adapter report, schema, and bounded hash manifest.
5. `conversion_report.json` is audit-useful for the bounded stage. It records
   mode, dataset ID/family, requested/loaded/emitted counts, invalid/quarantine
   counts, source hashes, source counts, redaction totals, schema name, and
   conservative training authorization.
6. `hash_manifest.json` is useful for example/report integrity. Its
   `examples_jsonl_sha256` and `conversion_report_json_sha256` values match the
   generated files.

## Follow-Up Update

- The later full-conversion infrastructure pass updated
  `hash_manifest_json_sha256` to use a directly recomputable convention:
  hash the canonical manifest JSON with
  `hashes.hash_manifest_json_sha256` set to `null`, then store that digest in
  the final manifest.

## Caveats

- The reviewed sample is a bounded smoke over the first 10 adapter-emitted
  traces. It is not class-balanced, representative, or suitable for training.
- The report does not yet include an explicit `schema_validation_passed: true`
  field or output paths. The validation passed in this review, but adding those
  fields would make future human review faster.

## Recommendation

Do not move to full OpenHands conversion yet.

Recommended next order:

1. Keep this bounded smoke as the Dataset #1 conversion checkpoint.
2. Add a small polish issue or future patch for the manifest self-hash
   convention and optional report ergonomics.
3. Onboard Dataset #2: `dialogue-swe-bench`.
4. Define a fixture-first converter for Dataset #2 before returning to full
   Dataset #1 conversion planning.

This protects the unified `PneumaBrain-v0` path from overfitting its data
contract assumptions to trajectory-only OpenHands records.
