# Pneuma Lab Claude Guide

Pneuma Lab is a standalone research and evaluation harness for machine psyche:
software-engineering cognition, continuous affect, instinct, scar-tissue memory,
self-modeling, authority pressure, and consciousness-relevant evaluation.

This repo is intentionally smaller and cleaner than 9to5. Treat the JSON schemas
as the current source of truth; runtime, replay, adapters, and evals are still
scaffold seams.

## Vocabulary

- **Pneuma Lab**: external lab harness for defining, replaying, perturbing, and
  auditing machine-interiority contracts.
- **9to5**: the production autonomous engineering agent that inspired the
  contracts. This repo must not import from or write back into it.
- **Frame**: one versioned JSON Schema contract under `schemas/`.
- **Input frame**: observable world, agent trace, memory, governance, or
  intervention context.
- **Output frame**: psyche state, workspace broadcast, instinct, pressure,
  authority request, causal trace, evidence frame, or grounded self-report.
- **Evidence ladder**: the conservative 0-5 consciousness-evidence scale in
  `docs/consciousness-levels.md`.

## Read When Relevant

- Project overview: `README.md`
- Architecture intent: `docs/vision.md`
- Frame contract map: `docs/io-contract.md`
- Evidence ladder: `docs/consciousness-levels.md`
- 9to5 source crosswalk: `docs/source-map.md`
- Migration account: `migration/MIGRATION_REPORT.md`
- Copied reference material: `migration/copied-from-9to5/` and
  `migration/copied-from-manager-data/`

## Tree Guide

- `schemas/` contains the 13 Draft 2020-12 JSON Schema contracts. Keep these
  valid, versioned, and externally consumable.
- `src/pneuma_lab/schemas/` contains loading helpers (`__init__.py`) and frame
  validation (`validate.py`).
- `src/pneuma_lab/psyche/` (Phase 1) holds the `PsycheUnderTest` interface,
  `ReferencePsyche` (a deterministic Level-3 mind wiring all nine indicator
  families), deterministic hashing, and the pure math ported from
  `migration/copied-from-9to5/reference-interfaces/` (manifold, prototypes,
  mood, drives, authority — with the 9to5 `config` defaults inlined).
- `src/pneuma_lab/replay/` (Phase 1) is the deterministic replay harness + JSONL
  IO + tick grouping + a `python -m pneuma_lab.replay` CLI.
- `src/pneuma_lab/evals/` (Phase 1) holds `ConsciousnessEvidenceScorer`
  (Level 0–3 only; hard-capped because Phase 1 runs no interventions).
- `src/pneuma_lab/adapters/` is still a planned seam (Phase 2).
- `fixtures/sample_run.jsonl` is a failure-motif escalation timeline used by the
  replay tests and CLI.
- `docs/` explains the research contract in human language;
  `docs/superpowers/` holds the Phase-1 design spec + implementation plan.
- `migration/` is read-only provenance and design/reference material.
- `tests/` verifies schema validity, frame validation, ported psyche math,
  output-frame validity, deterministic replay, and evidence scoring.

## Core Rules

- Keep Pneuma Lab standalone. Do not create imports from `C:\9to5` or write back
  into 9to5 unless the user explicitly asks for a separate operation.
- Treat copied migration material as provenance/reference, not live product
  code.
- Keep claims conservative: this repo evaluates possible machine interiority; it
  does not assert present phenomenal consciousness.
- Preserve verifier invariance: evidence and verdicts are additive/auditable,
  never overwritten by the psyche under test.
- Prefer narrow, schema-first changes until runtime/replay/eval surfaces exist.
- Use 4-space indentation across source, schemas, and docs.
- Avoid adding heavy dependencies without a concrete phase that needs them.
- Do not touch secrets, `.git`, caches, virtualenvs, or private datasets unless
  explicitly authorized.

## Fast Editing Loop

1. Inspect the closest contract or doc before editing.
2. Make the smallest change that preserves the current scaffold boundary.
3. Run the focused tests.
4. If a schema changed, verify all schemas parse and validate.
5. Update the nearest doc when a frame meaning, invariant, command, or workflow
   changes.

Useful commands:

```txt
python -m pytest tests/ -q
pip install -e ".[dev]"
python -m pytest tests/test_schema_loads.py -q
git diff --check
```

## Schema Rules

- JSON schemas use Draft 2020-12 and 4-space indentation.
- Every frame declares `$schema`, `$id`, `title`, `description`, `type`,
  `x-pneuma-frame-kind`, and `x-pneuma-version`.
- Required fields should stay minimal until runtime producers exist.
- Put semantics in descriptions when shape stability is still unknown.
- Keep input/output partitioning aligned with `src/pneuma_lab/schemas/__init__.py`.
- Guard strict consumers: no UTF-8 BOM, no comments in JSON, no Python-only
  assumptions in the schema files.

## Final Response After Edits

Report:

- files changed and why
- docs updated
- verification commands and pass/fail status
- skipped checks or remaining risk

4 space indents always
