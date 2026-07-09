# PneumaTrainingExample Contract

Status: schema foundation only.

`PneumaTrainingExample` is the canonical example contract for future
`PneumaBrain-v0` dataset conversion. The schema lives at
`schemas/pneuma-training-example.schema.json`.

This contract does not train anything. It does not authorize E1/E2 execution,
calibration, runtime integration, J-space/Jacobian Lens work, SWE-chat
processing, or raw-data mutation. It also does not make consciousness,
interiority, moral-patienthood, or Level 4/5 evidence claims.

## Purpose

The contract gives all future datasets one shared shape before any model work:

- controlled dataset-family and task enums;
- explicit example type and input modality;
- task masks so missing labels are masked, not treated as negative labels;
- privacy, redaction, leakage, and model-use gates;
- split metadata for grouped and held-out evaluation;
- evidence references for auditability.

## Training Gates

The schema blocks training weight for examples whose `model_use_tier` is
`blocked` or `eval_only`. It also blocks training weight when `privacy_status`
is `pii_blocked`, `dual_use_blocked`, or `eval_only`.

Trainable examples must provide a non-empty `target` and at least one
`evidence_refs` entry. Raw text is not required by the schema and should not be
assumed by future converters.

## Synthetic Fixtures

The fixtures under `fixtures/training_examples/` are synthetic contract tests.
They are not derived from real dataset rows and are not training artifacts.

Current fixture coverage includes:

- a valid `swe-gym` `TrajectoryExample` for `RISK_PREDICTION`;
- a valid `swe-gym` `VerifierExample` for `VERIFIER_VALUE`;
- a valid `dialogue-swe-bench` `TaskExample` for `TASK_DIFFICULTY`;
- a blocked `swe-chat` example proving privacy-blocked examples cannot train;
- an eval-only `swe-mera` example proving held-out examples cannot train;
- invalid examples for unknown task type, missing required fields, and blocked
  positive training weight.

## Next Step

After this schema-first contract lands, the next implementation pass should
prepare a read-only canonical converter for the approved processed
`swe-gym-openhands-sampled` artifact. That pass should not convert any raw data,
train models, run E1/E2, calibrate, or touch SWE-chat.
