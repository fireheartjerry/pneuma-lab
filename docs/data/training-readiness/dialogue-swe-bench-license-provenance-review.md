# Dialogue SWE-Bench License And Provenance Review

Status: conversion blocked by unresolved dataset license.

This review advances Dataset #2 as far as the current evidence permits. It does
not convert real rows, inspect raw dialogue row content, train models, run E1/E2,
calibrate, change runtime behavior, implement J-space/Jacobian Lens work,
process SWE-chat, mutate raw or processed data, write to `C:/pneuma-data`, or
make consciousness, Level 4/5, interiority, sentience, or moral-patienthood
claims.

## Repo State

`git status --short --branch` reported:

```text
## main...origin/main [ahead 20]
```

The working tree was clean before this pass. The branch is ahead of
`origin/main` by many commits, so pushing should be considered separately, but
this pass does not push.

## Evidence Reviewed

Local committed metadata:

- `docs/data/registry/dialogue-swe-bench.json`
- `docs/data/onboarding/dialogue-swe-bench.md`
- `docs/data/conversion/dialogue-swe-bench-to-training-examples.md`
- `src/pneuma_lab/converters/dialogue_swe_bench_training.py`
- `tests/test_dialogue_swe_bench_training_converter.py`

Local sidecars under `C:/pneuma-data/processed/dialogue-swe-bench/`:

- `provenance.json`
- `row_counts.json`
- `file_index.jsonl`
- `normalized_metadata.jsonl`

External source check:

- Hugging Face dataset page for `Brendan/SWE-Bench_Dialogue`
- GitHub repo `jlab-nlp/dialogue_swe_bench`
- arXiv paper page for Dialogue-SWEBench

## Findings

The local provenance sidecar records the GitHub repo at commit
`86689bbb8e4eb459939fc7eb8b3e4220b5215ede` with `license: null`.

The normalized metadata records the effective license note as:
`paper=CC BY 4.0; hf_dataset=not declared; github=none`.

The Hugging Face dataset page exposes the expected 550 rows and schema columns
such as patch, test patch, problem statement, difficulty, persona, and oracle
test lists, but it does not declare a dataset license in the page metadata.

The GitHub repo page did not expose a license. The arXiv paper page is marked
CC BY 4.0, but that applies to the paper page and is not sufficient to treat the
dataset artifacts as licensed for conversion or training-oriented use.

## Decision

Bounded real-data conversion is blocked.

The gate is not data size or implementation readiness. The gate is unresolved
license/provenance:

- local provenance license is `null`;
- local normalized metadata says the HF dataset license is not declared;
- local normalized metadata says GitHub has no license;
- live source check did not find a dataset license;
- raw fields include dialogue/task text, gold patches, test patches, and oracle
    lists, so leakage controls must be in place before any future conversion.

## Safe Work Completed

- Added a Dataset #2 governance module:
  `src/pneuma_lab/training/dialogue_governance.py`.
- Added a committed readiness/guardrail manifest:
  `docs/data/training-readiness/dialogue-swe-bench.json`.
- Updated the registry/readiness references so Dataset #2 has a mechanical
    block instead of an informal caveat.
- Added tests for license gating, input leakage checks, manifest consistency,
    and bounded-conversion request rejection.

## Remaining Safe Next Step

Resolve upstream licensing first. Acceptable evidence would be a dataset card,
repository license, release note, or author-confirmed permission that applies to
the dataset artifacts, not only to the paper text.

If this gate remains blocked, the next dataset to consider is the OpenHands
verifier lane because it is adapter-backed and avoids SWE-chat privacy risk.
That path still needs its own caveat handling for missing task joins before any
training-oriented use.
