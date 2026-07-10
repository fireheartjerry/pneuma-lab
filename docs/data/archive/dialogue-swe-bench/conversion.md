# Dialogue SWE-Bench to PneumaTrainingExample Plan

**ARCHIVED — inactive.** Superseded as the active Dataset #2 by
`open-swe-traces`. Kept for provenance; not deleted.

Status: planning only.

This document plans a future converter from `dialogue-swe-bench` metadata and
records into canonical `PneumaTrainingExample` records for future
`PneumaBrain-v0` data work. It does not implement a converter, emit examples,
train models, run E1/E2, calibrate, change runtime behavior, implement
J-space/Jacobian Lens work, process SWE-chat, inspect raw dialogue row content,
mutate raw or processed data, or make consciousness, Level 4/5, interiority,
sentience, or moral-patienthood claims.

Implementation note: a synthetic fixture-first converter now exists at
`src/pneuma_lab/converters/dialogue_swe_bench_training.py`. It consumes only the
committed synthetic fixture
`fixtures/training_examples/dialogue_swe_bench_synthetic_source.json`, emits
schema-valid blocked examples with `training_weight: 0.0`, and carries the
local `null` license caveat into example metadata and blocked uses. It did not
run bounded conversion, full conversion, real parquet-row inspection, training,
calibration, runtime integration, SWE-chat processing, or writes to
`C:/pneuma-data`. Upstream license review and separate approval remain required
before any real-data bounded conversion or training-oriented use.

Readiness update: the Dataset #2 license/provenance review and guardrail
manifest are now committed at
`docs/data/archive/dialogue-swe-bench/license-provenance-review.md`
and `docs/data/archive/dialogue-swe-bench/training-readiness.json`. Real-row bounded
conversion remains blocked because the local provenance license is `null`, the
local normalized metadata says `hf_dataset=not declared; github=none`, and live
source checks did not find a dataset license.

Repository state observed for this planning pass:

- `git status --short --branch` reported `main...origin/main [ahead 13]`.
- The working tree was clean before creating this planning document.
- Because the branch is ahead of `origin/main` by many commits, pushing should
  be considered before more work, but this plan does not push.

## 1. Purpose

The future converter should test whether the unified
`PneumaTrainingExample` contract can represent dialogue/operator-shaped
examples before any privacy-blocked SWE-chat work. The useful question is
whether `dialogue-swe-bench` can be mapped into schema-valid, auditable,
leakage-controlled examples with conservative label provenance.

This document only prepares that future conversion. It is not training
authorization, not a model plan, and not a claim that simulated dialogue labels
represent real human operator behavior.

## 2. Source Dataset Summary

Source registry: `docs/data/archive/dialogue-swe-bench/registry.json`

Onboarding doc: `docs/data/archive/dialogue-swe-bench/onboarding.md`

Source of truth metadata sidecars:

- `C:/pneuma-data/processed/dialogue-swe-bench/row_counts.json`
- `C:/pneuma-data/processed/dialogue-swe-bench/file_index.jsonl`
- `C:/pneuma-data/processed/dialogue-swe-bench/provenance.json`
- `C:/pneuma-data/processed/dialogue-swe-bench/normalized_metadata.jsonl`

| Field                     | Value                                                     |
| ------------------------- | --------------------------------------------------------- |
| Dataset ID                | `dialogue-swe-bench`                                      |
| Dataset family            | `dialogue-swe-bench`                                      |
| Raw path                  | `raw/dialogue-swe-bench/SWE-Bench_Dialogue`               |
| Processed path            | `processed/dialogue-swe-bench`                            |
| Source files              | 2 parquet files                                           |
| Total rows                | 550                                                       |
| Test split rows           | 500                                                       |
| Ablation split rows       | 50                                                        |
| Hugging Face repo         | `Brendan/SWE-Bench_Dialogue`                              |
| Hugging Face revision     | `88f083e830d9cd48e19470aa887a9df2914d3547`                |
| Git provenance            | `https://github.com/jlab-nlp/dialogue_swe_bench`          |
| Git commit                | `86689bbb8e4eb459939fc7eb8b3e4220b5215ede`                |
| Local license status      | `null` in local provenance                                |
| Privacy status            | public/simulated benchmark-style metadata-only onboarding |
| Adapter report            | none yet                                                  |
| Current conversion status | no canonical converter, no emitted examples               |

Source files:

| Source file                                                                      | Rows | SHA-256                                                            |
| -------------------------------------------------------------------------------- | ---: | ------------------------------------------------------------------ |
| `raw/dialogue-swe-bench/SWE-Bench_Dialogue/data/ablation-00000-of-00001.parquet` |   50 | `d25937529e38c4d0e7db22fdaebb35e6df13b2eaf10e0f30591c011856c8c83f` |
| `raw/dialogue-swe-bench/SWE-Bench_Dialogue/data/test-00000-of-00001.parquet`     |  500 | `fecd76c172a41ae56db9b110385b192cca620d3e20d6df914ab253b97cb8211a` |

Schema-level fields observed from the dataset card and parquet footers:

- `repo`
- `instance_id`
- `base_commit`
- `patch`
- `test_patch`
- `problem_statement`
- `hints_text`
- `created_at`
- `version`
- `FAIL_TO_PASS`
- `PASS_TO_PASS`
- `environment_setup_commit`
- `difficulty`
- `persona`
- `issue_title`
- `draft_problem_statement`
- `full_problem_statement`

Caveats:

- The local license is `null`, so upstream license review is required before
  any training-oriented use.
- Dialogue/persona labels are simulated, not real-human operator behavior.
- SWE-Bench lineage requires contamination and leakage controls before
  training-oriented conversion or evaluation claims.
- No adapter report exists yet, so future conversion must create its own
  deterministic report before any bounded real-data pass.
- Current onboarding validated metadata sidecars only and did not inspect raw
  dialogue row content.

## 3. Candidate Example Types

Conservative future mappings:

| Example type        | Candidate use                                                                                                                 | Current status                                                                                                            |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `TaskExample`       | Task and difficulty metadata from `repo`, `instance_id`, `base_commit`, `difficulty`, `persona`, and approved issue metadata. | Plausible after license review and adapter implementation.                                                                |
| `PatchExample`      | Patch/test supervision from `patch`, `test_patch`, `FAIL_TO_PASS`, and `PASS_TO_PASS`.                                        | Plausible only with strict leakage controls; gold patch and oracle material must stay out of input.                       |
| `PreferenceExample` | Pairwise or ranked choice supervision.                                                                                        | Blocked unless source records expose explicit pairwise/ranked labels. Do not infer preferences from persona labels alone. |
| `SelfReportExample` | Claim-vs-correction or report-faithfulness structures.                                                                        | Blocked unless a future schema pass confirms receipt-grounded report/correction structure.                                |
| `TrajectoryExample` | Dialogue-turn summaries as an observable event sequence.                                                                      | Possible later only if a future adapter exposes turns safely and without raw dialogue text by default.                    |

Label provenance must be conservative. Simulated correction, persona, or
dialogue labels should use `simulated_label` or `proxy_label`, not
`human_label`. SWE-Bench-derived patch/test outcomes should use `source_label`,
`gold_patch`, or a carefully described harness/proxy provenance, depending on
the target.

## 4. Label Mapping Plan

| Task type                  | Source fields needed                                                                                          | Label provenance                                                                | Confidence                     | Default authorization                                                               | Leakage risk            | Caveats                                                                                        |
| -------------------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | ------------------------------ | ----------------------------------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------------------- |
| `TASK_DIFFICULTY`          | `difficulty`, plus optional task metadata such as `repo`, `instance_id`, and `base_commit` for grouping only. | `source_label` if upstream difficulty is documented; otherwise `proxy_label`.   | Medium.                        | `train_after_adapter` only after license review; `training_weight: 0.0` by default. | Medium.                 | Difficulty may encode dataset construction choices, not an independent human difficulty label. |
| `OPERATOR_PUSHBACK`        | Explicit simulated correction/pushback labels if exposed by the future adapter.                               | `simulated_label` or `proxy_label`.                                             | Low to medium.                 | Blocked until explicit labels are confirmed; never `human_label`.                   | Medium.                 | Do not treat simulated correction/dialogue/persona labels as real operator pushback.           |
| `SELF_REPORT_FAITHFULNESS` | Clear report-vs-correction or claim-vs-receipt structures, if present after schema review.                    | `simulated_label` or `proxy_label`; `source_label` only if upstream defines it. | Low until confirmed.           | Blocked until a future adapter proves receipt-grounded structure.                   | Medium.                 | Persona or dialogue text alone is not a faithfulness target.                                   |
| `PATCH_SUCCESS`            | `patch`, `test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS`, and outcome/test metadata.                             | `source_label` or `gold_patch`, depending on target design.                     | Medium after leakage controls. | `train_after_adapter` only after license review and contamination flags.            | High unless controlled. | Gold patches, oracle tests, and final outcomes must not leak into input.                       |
| `VERIFICATION_PRESSURE`    | Future derived signals such as test uncertainty, correction frequency, or disagreement indicators.            | `constructed_label` or `proxy_label`.                                           | Low.                           | Blocked until a separately approved proxy design exists.                            | High.                   | Do not fabricate verifier-value labels from absent data.                                       |

Rules:

- Do not treat absence of a label as a negative label.
- Missing tasks must be masked through `task_mask`, not encoded as false.
- SWE-Bench-derived outcomes are not clean held-out evaluation without
  contamination flags.
- Dialogue/persona supervision is simulated and should carry a warning in
  `label_provenance.description`.

## 5. Input Payload Design

Future input payloads should be observable-only by default. They should be
small structured summaries, not raw dialogue or answer-bearing text.

Allowed input fields may include:

- dataset ID and dataset family;
- source split, source file hash, and source row number;
- task ID such as `instance_id`;
- repo and issue metadata only if approved as non-sensitive and not used as a
  shortcut for leakage-prone evaluation;
- `base_commit` or commit-era metadata for grouping or controlled features;
- difficulty/persona metadata when it is an approved input for the task;
- dialogue structure metadata, if a future adapter exposes it safely:
  - number of turns;
  - role sequence;
  - turn length summaries;
  - correction count summaries;
  - approved categorical labels;
- patch/test metadata only as digest, size, or structural summaries when the
  target is not defined by the same material.

Avoid by default:

- raw dialogue text;
- raw issue text unless a separate privacy and leakage decision approves it;
- `problem_statement`, `draft_problem_statement`, and
  `full_problem_statement` raw text;
- gold patch text;
- oracle test lists such as raw `FAIL_TO_PASS` and `PASS_TO_PASS`;
- final target-bearing labels;
- solution text;
- exact hidden test details;
- any field that makes the answer learnable from the input.

Candidate structured input shape:

```json
{
  "dataset": {
    "dataset_id": "dialogue-swe-bench",
    "dataset_family": "dialogue-swe-bench",
    "source_split": "test",
    "source_file_sha256": "sha256:..."
  },
  "task": {
    "instance_id": "opaque-or-digest",
    "repo": "repo-name-or-null",
    "base_commit": "commit-or-null",
    "difficulty": "category-or-null",
    "persona": "category-or-null"
  },
  "dialogue_summary": {
    "has_dialogue": true,
    "turn_count": null,
    "role_sequence": [],
    "turn_length_summary": {}
  },
  "patch_summary": {
    "has_patch": true,
    "patch_text_included": false,
    "patch_sha256": "sha256:...",
    "test_patch_sha256": "sha256:..."
  }
}
```

The exact payload should be fixture-first and schema-tested before any bounded
real conversion.

## 6. Target Design

Possible future targets:

| Task type                  | Target shape                                                                                | Authorization status                                                            |
| -------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------- |
| `TASK_DIFFICULTY`          | `{"difficulty": "category"}` or a numeric bucket only if upstream semantics are documented. | Adapter-only pending; allowed after license review and label documentation.     |
| `OPERATOR_PUSHBACK`        | `{"simulated_pushback": true                                                                | false}` or a categorical correction label only if explicit source labels exist. | Blocked until explicit simulated labels are confirmed; never real-human pushback. |
| `SELF_REPORT_FAITHFULNESS` | `{"faithfulness_label": "..."}` only for clear report-vs-correction/receipt structures.     | Blocked until receipt-grounded structures are proven.                           |
| `PATCH_SUCCESS`            | `{"patch_success": true                                                                     | false}` or test-derived outcome summary.                                        | Adapter-only pending; requires leakage controls and contamination flags.          |
| `VERIFICATION_PRESSURE`    | Derived proxy such as `{"verification_pressure": "low                                       | medium                                                                          | high"}`.                                                                          | Blocked until separately designed. |

Every target must include explicit `label_provenance` and must avoid treating
missing fields as negative labels. Targets that depend on gold patch, oracle
tests, or final outcomes must keep those source fields out of `input`.

## 7. Split And Leakage Strategy

Recommended split policy:

- use `task_grouped` so every row or future variant for the same
  `instance_id` stays in the same split;
- use `repo_grouped` where repo exists, especially for task difficulty or patch
  success claims;
- preserve the original `test` and `ablation` split metadata as a source
  grouping signal and possible held-out adapter sanity check;
- never mix the same SWE-Bench task across train and test;
- attach contamination flags because the corpus is SWE-Bench-derived.

Leakage controls:

- exclude gold patch text from input;
- exclude raw test patch and oracle lists from input unless the task explicitly
  targets patch/test structure and uses digest-only summaries;
- exclude final outcomes and dialogue labels from input when they define the
  target;
- exclude raw dialogue text by default;
- keep repo and task IDs as split/evidence metadata by default, not predictive
  features, unless a later experiment explicitly permits them;
- require a leakage manifest from any future converter explaining which fields
  were stripped and which tests prove target-bearing fields cannot affect
  input features.

## 8. Training Authorization Defaults

Conservative future defaults for any first emitted examples:

```json
{
  "privacy_status": "public_or_benchmark",
  "redaction_receipt": {
    "status": "not_needed",
    "report_ref": null
  },
  "model_use_tier": "train_after_adapter",
  "training_weight": 0.0,
  "leakage_risk": "medium"
}
```

These defaults should become stricter when needed:

- use `blocked` instead of `train_after_adapter` until upstream license review
  is complete, if the project wants license gating to be mechanical;
- use `leakage_risk: "high"` for `PATCH_SUCCESS` examples until gold/oracle
  leakage tests pass;
- use `label_provenance.kind: "simulated_label"` for simulated dialogue,
  correction, or persona labels;
- use `label_provenance.kind: "proxy_label"` for constructed social or
  operator-shaped signals;
- do not use `human_label` unless a future provenance review proves the label is
  real human annotation and training use is approved.

`training_weight` should remain `0.0` until a separate training authorization
changes both the mixture policy and `model_use_tier`.

## 9. Validation Plan For Future Converter

Future implementation should include tests and reports for:

- schema validation of every emitted `PneumaTrainingExample`;
- deterministic conversion over synthetic fixtures;
- count reconciliation with `row_counts.json` and `file_index.jsonl`;
- no raw dialogue text in default output;
- no raw problem statement text in default output unless explicitly approved;
- no target leakage keys in `input`;
- no gold patch, oracle tests, final outcomes, or label fields in `input`;
- label provenance marks simulated labels as `simulated_label` or `proxy_label`;
- examples remain `training_weight: 0.0` until license review and explicit
  training authorization;
- license status is copied into the conversion report or manifest;
- split groups populate `repo`, `task_id`, and source split metadata;
- generated examples cite registry, schema, provenance, file index, source file
  hash, and converter version;
- invalid or ambiguous rows are quarantined rather than coerced;
- fixture-first converter exists before any bounded real conversion;
- bounded conversion, if approved later, reads only the requested records and
  writes only repo-local generated artifacts unless separately authorized.

Recommended test order:

1. Synthetic fixture tests for each candidate task mapping.
2. Schema-gate tests against `schemas/pneuma-training-example.schema.json`.
3. Leakage tests proving forbidden fields cannot affect input payloads.
4. Deterministic report/hash tests.
5. Metadata reconciliation tests against committed tiny fixtures.
6. Optional bounded real-data smoke only after fixture tests and license gates
   are reviewed.

## 10. Non-Goals

- No converter implementation.
- No emitted `PneumaTrainingExample` records.
- No ML training.
- No E1/E2 execution.
- No calibration.
- No runtime integration.
- No J-space or Jacobian Lens work.
- No SWE-chat processing.
- No raw sensitive content inspection.
- No raw dialogue row inspection.
- No raw or processed data mutation.
- No writes to `C:/pneuma-data`.
- No training authorization before upstream license review.
- No claims about real human operator behavior.
- No consciousness, Level 4/5, interiority, sentience, or moral-patienthood
  claims.

## 11. Recommended Next Step

After this planning document is reviewed, commit it as a planning-only artifact.
Then, in a separate approved pass, implement a synthetic fixture-first
`dialogue-swe-bench` converter only after license and provenance caveats are
encoded.

The next implementation prompt should require:

- no raw dialogue row content access;
- no bounded or full real-data conversion yet;
- synthetic fixtures only;
- explicit label mapping for `TASK_DIFFICULTY`, simulated
  `OPERATOR_PUSHBACK`, optional `SELF_REPORT_FAITHFULNESS`, and
  `PATCH_SUCCESS`;
- mechanical license caveat propagation;
- leakage tests for raw text, gold patches, oracle tests, final outcomes, and
  target-bearing dialogue labels;
- `model_use_tier: "train_after_adapter"` or `blocked`;
- `training_weight: 0.0`.
