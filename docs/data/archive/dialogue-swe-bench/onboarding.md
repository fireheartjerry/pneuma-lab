# Dataset Onboarding: Dialogue SWE-Bench

**ARCHIVED — inactive.** Superseded as the active Dataset #2 by
`open-swe-traces` (see `docs/data/candidate-reviews/open-swe-traces.md`)
because this dataset's license remained unresolved (`null`) at every source
checked. Kept for provenance; not deleted. Do not treat as the active
Dataset #2 candidate.

## Status

Onboarded as Dataset #2 in metadata-only form. This pass makes the dataset
legible to the registry; it does not implement an adapter, emit
`PneumaTrainingExample` records, train a model, run E1/E2, calibrate anything,
touch runtime behavior, process SWE-chat, or make consciousness-level claims.

Current training-readiness status: guardrails are committed in
`docs/data/archive/dialogue-swe-bench/training-readiness.json`, and real-row conversion
is blocked until upstream dataset licensing is resolved. The license/provenance
review is recorded in
`docs/data/archive/dialogue-swe-bench/license-provenance-review.md`.

## Why Selected As Dataset #2

`dialogue-swe-bench` is small, local, and shaped around simulated dialogue and
operator-style task information. It tests whether the registry/onboarding
pattern generalizes beyond trajectory-style OpenHands records before any
privacy-blocked SWE-chat work.

The value is schema and adapter planning, not proof of real operator behavior.
The dialogue/persona shape is simulated and must stay labeled that way.

## Dataset Facts

Source of truth: metadata sidecars under `processed/dialogue-swe-bench/`.

| Field                 |                                            Value |
| --------------------- | -----------------------------------------------: |
| Total rows            |                                              550 |
| Source files          |                                                2 |
| Test rows             |                                              500 |
| Ablation rows         |                                               50 |
| Hugging Face repo     |                     `Brendan/SWE-Bench_Dialogue` |
| Hugging Face revision |       `88f083e830d9cd48e19470aa887a9df2914d3547` |
| GitHub provenance     | `https://github.com/jlab-nlp/dialogue_swe_bench` |
| Git commit            |       `86689bbb8e4eb459939fc7eb8b3e4220b5215ede` |

The raw dataset directory contains a Hugging Face snapshot with a README and two
parquet files. This pass inspected directory listings, metadata sidecars, the
dataset-card schema section, and parquet footers for schema/count information;
it did not inspect raw dialogue row content.

## Shape And Labels

The dataset-card/parquet schema lists SWE-Bench-style task and patch fields:
`repo`, `instance_id`, `base_commit`, `patch`, `test_patch`,
`problem_statement`, `hints_text`, `created_at`, `version`, `FAIL_TO_PASS`,
`PASS_TO_PASS`, `environment_setup_commit`, `difficulty`, `persona`,
`issue_title`, `draft_problem_statement`, and `full_problem_statement`.

The processed metadata inventory records all 550 rows as having dialogue,
patches, tests, and outcome-like structure. It does not expose a canonical
`resolved` label. Future adapter work must map labels explicitly instead of
assuming OpenHands-style resolved outcomes.

## Privacy And Provenance Status

This is treated as public/simulated benchmark-style data for metadata-only
onboarding. No redaction receipt exists because no canonical processed text
outputs or training examples exist yet. License is recorded as `null` in the
local provenance sidecar, so any broader use should review upstream licensing
before conversion or training.

## How It Differs From OpenHands Sampled

OpenHands sampled is an adapter-backed trajectory dataset with
`adapter_report.json`, deterministic hashes, redaction totals, and validated
`PneumaTrace` outputs. `dialogue-swe-bench` currently has metadata sidecars only:
row counts, file index hashes, provenance, and normalized metadata.

OpenHands sampled primarily supports trajectory/risk examples. Dialogue
SWE-Bench is better suited to dialogue-shaped task, patch, simulated preference,
and self-report-faithfulness planning.

## Expected Canonical Example Types

- `TaskExample`
- `PatchExample`
- `PreferenceExample`
- `SelfReportExample`

Small `TrajectoryExample` mappings may be possible later if a future adapter
can expose dialogue turns as observable event sequences without leaking labels
or raw content inappropriately.

## Future Training Relevance For PneumaBrain-v0

After a separate adapter/conversion approval, this dataset can test
`OPERATOR_PUSHBACK`, `SELF_REPORT_FAITHFULNESS`, `TASK_DIFFICULTY`, and
`PATCH_SUCCESS` pathways in the unified `PneumaTrainingExample` contract. Its
weight should remain low/medium because the operator signals are simulated and
the SWE-Bench lineage carries contamination risk.

## Allowed Next Steps

- Use the registry manifest for metadata-only onboarding validation.
- Draft a future adapter/conversion plan for canonical examples.
- Define explicit label mapping and leakage controls before conversion.
- Review upstream license/provenance before any training-oriented use.
- Continue synthetic-fixture converter validation while real-row conversion is
  license-blocked.

## Blocked Next Steps

- Do not train models in this pass.
- Do not run E1/E2 or calibration in this pass.
- Do not convert rows into `PneumaTrainingExample` records in this pass.
- Do not run bounded real-row conversion until a dataset license is declared or
  otherwise resolved.
- Do not inspect raw dialogue content beyond metadata/schema-level evidence.
- Do not process SWE-chat.
- Do not modify runtime behavior.
- Do not implement J-space/Jacobian Lens work.
- Do not make consciousness, interiority, sentience, Level 4/5, or
  moral-patienthood claims.

## Caveats

- Dialogue/operator signals are simulated, not real-human behavior.
- The dataset is SWE-Bench-derived, so contamination and benchmark leakage
  caveats apply.
- No canonical adapter exists yet.
- No redaction receipt or adapter report exists yet.
- License is unresolved in local provenance metadata.
- Metadata sidecars do not expose a canonical `resolved` field.

## Scaling Notes

The reusable Dataset #2 pattern is a registry-only validation profile:

1. Keep raw and processed data outside the repo.
2. Commit only small manifest/report metadata.
3. Validate row counts, file hashes, provenance, and normalized metadata keys.
4. Avoid raw row inspection until an adapter plan explicitly authorizes it.
5. Preserve allowed/blocked uses so onboarding cannot silently become training.
