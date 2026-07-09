# OpenHands Sampled to PneumaTrainingExample Plan

Status: read-only planning only.

This document plans a future converter from processed
`swe-gym-openhands-sampled` PneumaTrace records into canonical
`PneumaTrainingExample` records for future `PneumaBrain-v0` work. It does not
convert data, train models, run E1/E2, calibrate, change runtime behavior,
process SWE-chat, inspect raw sensitive content, mutate raw or processed data,
or make consciousness claims.

## 1. Purpose

The converter will eventually map each processed OpenHands sampled
trajectory-bearing `PneumaTrace` into one or more canonical
`PneumaTrainingExample` records. The first useful target is a full-trace
`TrajectoryExample` for `RISK_PREDICTION`, with later prefix examples and
additional task heads staged behind explicit validation.

The converter is a data-shaping step only. It should produce schema-valid,
auditable examples with observable-only inputs and leakage-controlled targets.
It should not fit estimators, compute calibration, wire runtime outputs, or
decide that any model is approved for training.

## 2. Source Dataset

Source registry: `docs/data/registry/openhands-sampled.json`

Onboarding doc: `docs/data/onboarding/openhands-sampled.md`

Source of truth report:
`C:/pneuma-data/processed/swe-gym/openhands-sampled/adapter_report.json`

| Field | Value |
|---|---:|
| Dataset ID | `swe-gym-openhands-sampled` |
| Dataset family | `swe-gym` |
| Raw path | `raw/swe-gym/OpenHands-Sampled-Trajectories` |
| Processed path | `processed/swe-gym/openhands-sampled` |
| Adapter | `pneuma_lab.adapters.openhands_sampled` |
| Adapter version | `0.1.0` |
| Envelope schema | `PneumaTrace` v0.2.0 |
| Source rows | 6,055 |
| Processed traces | 6,055 |
| Valid traces | 6,055 |
| Invalid traces | 0 |
| Skipped rows | 0 |
| Agent steps | 114,461 |
| Resolved | 491 |
| Unresolved | 5,564 |
| Task joins present | 6,055 |
| Task joins missing | 0 |

Hashes from `adapter_report.json`:

| Artifact | SHA-256 |
|---|---|
| `pneuma_traces.jsonl` | `6ec06b724e71be2735b2495291a3d5102bc3efa4f24f0d03d824f549f79feb6b` |
| `trace_index.jsonl` | `b1d99a62197cb6091067a3ae585f05459ec3f59a77699632e674856f8e6637a1` |
| `pneuma_traces.invalid.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

Redaction status: processed outputs are redaction-verified through the adapter
report. The recorded deterministic totals are 103 emails, 4 AWS access keys,
and 16 assigned secrets.

Caveats:

- Labels are OpenHands/SWE-Gym harness outcomes, not Pneuma outcomes.
- The traces describe OpenHands behavior, not Pneuma or 9to5 interiority.
- Class balance is strongly skewed: 491 resolved and 5,564 unresolved.
- Timestamps are synthetic ordinals; order is preserved, wall-clock time is not.
- Raw trajectory content remains non-targeted. Future conversion should consume
  only processed redaction-verified traces, not raw rows.

## 3. Source-To-Target Mapping

Initial mapping:

- one processed `PneumaTrace` should produce one full-trace
  `TrajectoryExample` for `RISK_PREDICTION`;
- `target.resolved` should come from `labels.resolved` or `outcome.resolved`,
  with a validation check that they agree when both exist;
- `input` should be observable-only and should exclude `outcome`, `oracle`,
  `reference_supervision`, `labels.resolved`, and gold/test patch material.

Future mappings:

- prefix `TrajectoryExample` records for 25, 50, 75, and 100 percent trace
  windows, after the converter has a stable prefix policy;
- `FAILURE_SHAPE` examples if a safe label taxonomy is later defined;
- `SCAR_MOTIF` examples after motif extraction exists;
- `VERIFICATION_PRESSURE` proxy examples only after proxy labeling is approved.

Explicit non-mappings:

- no `OPERATOR_PUSHBACK`, because this dataset has no operator chat labels;
- no `SELF_REPORT_FAITHFULNESS`, because the current frames do not encode
  receipt-grounded claim audits;
- no `WORKSPACE_SALIENCE_LATER`, because there are no live workspace/J-space
  targets in this corpus;
- no `PreferenceExample`, because no pairwise preference label is present.

## 4. Field Mapping

| `PneumaTrainingExample` field | Planned mapping |
|---|---|
| `example_id` | Deterministic ID from dataset ID, trace ID, task type, prefix name, and converter version, such as `pte:swe-gym-openhands-sampled:<trace_hash>:risk:full`. |
| `dataset_id` | Registry value: `swe-gym-openhands-sampled`. |
| `dataset_family` | `swe-gym`. |
| `source_path_or_hash` | Prefer processed trace `build.content_hash`; include processed file hash in evidence refs. |
| `source_revision` | Registry/source value `baf3a4e4bff514d48ddc08a93a2ade5c126212c7`. |
| `example_type` | `TrajectoryExample` initially. |
| `input_modality` | `event_sequence` when carrying summary event features, or `structured_features` if the implementation stores only feature summaries. Initial recommendation: `structured_features`. |
| `task_type` | `RISK_PREDICTION` initially. |
| `task_mask` | `["RISK_PREDICTION"]` initially. Missing tasks are masked. |
| `input` | Observable-only feature payload from `trajectory` and `agent_trace` frames, described in section 5. |
| `target` | `{"resolved": true|false}` for initial risk examples. |
| `label_provenance` | `kind: "harness_outcome"`, confidence `high`, description stating SWE-Gym/OpenHands sampled harness outcome carried through the PneumaTrace envelope. |
| `privacy_status` | `redaction_verified`, because the processed artifact records deterministic redaction totals. |
| `redaction_receipt` | `status: "verified"`, `report_ref: "processed/swe-gym/openhands-sampled/adapter_report.json#privacy.redaction_totals"`. |
| `leakage_risk` | `medium` by default. Use `high` if objective-derived features are added later. |
| `allowed_training_uses` | Initially `["schema validation", "feature extraction planning", "later modeling only after separate approval"]`. |
| `blocked_training_uses` | Include current-pass training, E1/E2 execution, calibration, runtime integration, J-space, SWE-chat, and consciousness claims. |
| `model_use_tier` | Recommend `train_after_adapter` for the first converter implementation until validation reports and split manifests exist. Move to `train_ok` only after a separate approval gate. |
| `training_weight` | `0.0` while `model_use_tier` is `train_after_adapter`; later nonzero weights require explicit training authorization and mixture policy. |
| `split_policy` | `repo_grouped` initially. |
| `split_group.repo` | `labels.repo`, derived by the OpenHands sampled adapter from task join or instance ID. |
| `split_group.task_id` | `labels.instance_id` or trace provenance `source_id` split into instance/task component. Prefer `labels.instance_id` for grouping variants. |
| `split_group.session_or_user` | `null`; this is not a user/session corpus. |
| `split_group.era` | `null` unless a safe base-commit date or era join is added later. Do not infer wall-clock from synthetic timestamps. |
| `canonical_feature_refs` | Versioned feature block refs such as `pneuma-estimators-features/0.1.0:full` if using `src/pneuma_lab/estimators/features.py`; otherwise converter-specific feature set ref. |
| `evidence_refs` | At minimum trace ID, adapter report path, registry path, schema path, processed trace hash, and converter version. |

Source locations:

- dataset registry: dataset ID, family, paths, source revision, allowed and
  blocked uses;
- adapter report: counts, hashes, redaction receipt, source revision, adapter
  version;
- trace envelope: trace ID, run ID, provenance, build hash, privacy block,
  labels, trajectory, outcome, and frames;
- labels block: repo, instance ID, split, `resolved`, `has_trajectory`;
- outcome block: `resolved` and label-quality flags, but target only;
- trajectory and `agent_trace` frames: observable input features;
- hashes/evidence refs: report hashes, trace `build.content_hash`, and schema
  paths.

## 5. Input Payload Design

The initial `input` payload should be observable-only and compact. It should
not include raw private text by default. It should not include gold patches,
test patches, oracle lists, final outcome, `labels.resolved`, or any field that
defines the target.

Recommended initial shape:

```json
{
    "trace_id": "ptrace:...",
    "run_id": "run:...",
    "prefix": "full",
    "trajectory": {
        "num_messages": 0,
        "num_agent_steps": 0,
        "timestamp_provenance": "synthetic-ordinal"
    },
    "observable_summary": {
        "tool_call_count": 0,
        "tool_counts": {},
        "retry_count_max": 0,
        "retry_count_mean": 0.0,
        "steps_retry_ge2": 0,
        "strategy_switches_final": 0,
        "error_observation_count": 0,
        "observation_count": 0,
        "error_density": 0.0,
        "assistant_text_length_mean": 0.0,
        "assistant_text_length_max": 0,
        "observation_length_mean": 0.0,
        "observation_length_max": 0
    },
    "objective": {
        "present": true,
        "mode": "digest_or_metadata_only",
        "text_sha256": "sha256:...",
        "text_length": 0
    }
}
```

Implementation notes:

- Prefer reusing `src/pneuma_lab/estimators/features.py` for named
  observable-only summaries where possible. It already scrubs
  `outcome`, `oracle`, `reference_supervision`, and `labels.resolved` before
  featurization.
- The existing feature extractor supports `prefix_25`, `prefix_50`, and `full`.
  The planning request mentions 25/50/75/100 percent prefixes; adding 75
  percent should be a deliberate converter/feature decision, not an accidental
  mismatch.
- If objective metadata is included, use digest and length only unless a later
  privacy/leakage decision approves redacted objective text. Objective text can
  carry benchmark leakage risk and should not be a default feature.
- Tool arguments and observations should remain digest/length/marker based, as
  in `agent_trace` frames.

## 6. Target Design

Initial `RISK_PREDICTION` target:

```json
{
    "resolved": true
}
```

Semantics:

- `resolved: true` means the OpenHands/SWE-Gym harness marked the run resolved;
- `resolved: false` means unresolved under that harness;
- unresolved is not an absolute truth label about the task or future agents;
- downstream risk training may define `risk = !resolved`, but the canonical
  example should preserve the original `resolved` label and provenance.

The converter should reject or quarantine traces where `labels.resolved` and
`outcome.resolved` disagree, unless an explicit reconciliation policy is added.

## 7. Split Strategy

Recommended initial split policy: `repo_grouped`.

Populate:

- `split_group.repo` from `labels.repo`;
- `split_group.task_id` from `labels.instance_id`;
- `split_group.session_or_user` as `null`;
- `split_group.era` as `null` for now.

Future era grouping may be added only if a safe source such as base-commit date
is joined from task metadata. Synthetic ordinal timestamps are not eras and must
not be used as time splits.

Leakage controls:

- repo identity is for grouping and metrics, not model input by default;
- task ID is for grouping and evidence, not a predictive feature by default;
- objective text should be digest/length only unless separately approved;
- `oracle.fail_to_pass`, `oracle.pass_to_pass`, `reference_supervision`, gold
  patches, test patches, outcome fields, and `labels.resolved` are targets or
  label-quality material, not input features;
- if label-quality flags such as `outcome.report.error_eval` or
  `test_timeout` are used, they should filter examples or annotate provenance,
  not enter the feature payload.

## 8. Training Authorization Defaults

Future default values for first emitted examples:

```json
{
    "privacy_status": "redaction_verified",
    "redaction_receipt": {
        "status": "verified",
        "report_ref": "processed/swe-gym/openhands-sampled/adapter_report.json#privacy.redaction_totals"
    },
    "model_use_tier": "train_after_adapter",
    "training_weight": 0.0,
    "leakage_risk": "medium"
}
```

Rationale:

- The processed traces are redaction-verified, but the converter itself does not
  yet have a validation report, deterministic hash report, or split manifest.
- `train_after_adapter` keeps examples non-trainable until a separate approval
  moves the tier to `train_ok`.
- A positive `training_weight` would be rejected by policy until the model-use
  tier is explicitly changed.

Blocked uses should include:

- training in the converter implementation pass;
- E1/E2 execution or calibration;
- runtime control integration;
- verifier bypass;
- J-space/Jacobian Lens work;
- SWE-chat processing;
- consciousness-level or moral-patienthood claims.

## 9. Validation Plan For Future Implementation

The implementation should include:

- schema validation of every emitted `PneumaTrainingExample`;
- deterministic two-run output hash match;
- count reconciliation against `adapter_report.json`;
- invalid/quarantine output for trace/example validation failures;
- no raw content inclusion checks scanning output for raw paths and raw text
  fields;
- no target leakage checks that perturb or strip `outcome`, `oracle`,
  `reference_supervision`, and `labels.resolved` and confirm input features are
  unchanged;
- trainable examples require non-empty `target` and `evidence_refs`;
- blocked/eval-only examples cannot have positive `training_weight`;
- small synthetic fixture tests before real processed traces;
- optional bounded sample conversion test over a tiny number of processed
  redaction-verified records, only after fixture tests pass;
- full conversion only after bounded sample results are reviewed.

Recommended tests:

- pure unit tests over committed synthetic `PneumaTrace` fixtures;
- a converter determinism test comparing two in-memory runs;
- a schema-gate test using `schemas/pneuma-training-example.schema.json`;
- a leakage test proving target/outcome/oracle fields cannot affect `input`;
- a report test that expected counts match valid, invalid, skipped, and
  quarantined examples.

## 10. Output Artifact Plan

Do not create these paths in this planning pass.

Future processed output root:

`C:/pneuma-data/processed/swe-gym/openhands-sampled/training_examples/`

Planned artifacts:

| Artifact | Purpose |
|---|---|
| `pneuma_training_examples.jsonl` | Canonical examples. |
| `pneuma_training_examples.invalid.jsonl` | Quarantined invalid examples with errors. |
| `training_example_index.jsonl` | Compact index: example ID, trace ID, task type, split group, target summary, hash. |
| `conversion_manifest.json` | Converter version, source paths, source hashes, schema version, counts. |
| `conversion_report.json` | Count reconciliation, privacy/redaction receipt, leakage checks, deterministic hashes. |
| `hash_report.json` | Output SHA-256 values and two-run hash comparison. |

Repo-local artifacts should be tiny fixtures only, for example:

- `fixtures/training_examples/openhands_sampled_converter/input_traces.jsonl`
- `fixtures/training_examples/openhands_sampled_converter/golden_examples.jsonl`
- `fixtures/training_examples/openhands_sampled_converter/golden_report.json`

## 11. Non-Goals

- No ML training.
- No estimator fitting.
- No E1/E2 execution.
- No calibration.
- No runtime integration.
- No verifier bypass.
- No J-space or Jacobian Lens work.
- No SWE-chat processing.
- No raw sensitive content reading.
- No raw or processed data mutation.
- No full dataset conversion in the next pass unless separately approved.
- No consciousness, Level 4/5, interiority, or moral-patienthood claims.

## 12. Recommended Implementation Prompt

Use this prompt after this planning document is approved:

```text
Work in C:\pneuma-lab. Implement a tiny fixture-first converter for
OpenHands sampled PneumaTrace records into PneumaTrainingExample records.

Do not train models, run E1/E2, calibrate, modify runtime behavior, implement
J-space/Jacobian Lens, process SWE-chat, inspect raw sensitive content, mutate
raw or processed data, or run full conversion.

Create a converter module that accepts in-memory or fixture PneumaTrace records
and emits schema-valid PneumaTrainingExample records for full-trace
RISK_PREDICTION only. Use committed synthetic or tiny existing OpenHands sampled
fixtures, not C:\pneuma-data raw rows. Keep input observable-only, put
resolved only in target, preserve evidence refs, and emit a deterministic
conversion report. Add tests for schema validity, determinism, count
reconciliation, no target leakage, and no raw content inclusion.

Validate with:
python -m pytest tests/ -q
git diff --check
```

Decision after that fixture-first pass: choose between a bounded sample
converter over a tiny number of processed redaction-verified traces, or a
full-output implementation plan. Full conversion should remain later.
