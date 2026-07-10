# Pneuma Lab Claude Guide

Pneuma Lab is a standalone research and evaluation harness for machine psyche:
software-engineering cognition, continuous affect, instinct, scar-tissue memory,
self-modeling, authority pressure, and consciousness-relevant evaluation.

This repo is intentionally smaller and cleaner than 9to5. Read
`docs/project-status.json` first for current implementation and blocker state;
the JSON schemas remain the observable contract surface. Replay, paired
interventions, dataset adapters, conversion guardrails, and offline estimators
exist, but live 9to5 integration and JSpace/J-lens experiments do not.

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

- Current machine-readable status: `docs/project-status.json`
- Project overview: `README.md`
- Research program (evidence-graded; start at the overview): `docs/research/00-program-overview.md`
- Architecture intent: `docs/vision.md`
- Frame contract map: `docs/io-contract.md`
- Evidence ladder: `docs/consciousness-levels.md`
- Canonical L3-vs-L4 evidence demo: `docs/level4-evidence-demo.md`
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
  IO + tick grouping + a `python -m pneuma_lab.replay` CLI. The harness accepts an
  optional intervention `schedule` (Phase 2); the CLI auto-runs paired mode when
  the timeline contains `InterventionFrame`s.
- `src/pneuma_lab/interventions/` (Phase 2) is the Level-4 intervention harness:
  pure operation math (`operations`), the `PerturbationSet` surface the psyche
  consults (`perturbation`), duration-window resolution (`schedule`), the
  expected-vs-observed delta report (`report`), and the `PairedReplayRunner`
  (control/treated/null) that scores Level 4 honestly (`runner`). The package
  eager-imports only its two leaf modules and lazily loads the rest to avoid an
  import cycle with `psyche`/`replay`.
- `src/pneuma_lab/evals/` holds `ConsciousnessEvidenceScorer` (Level 0–4). Level 4
  is reachable only via the paired runner: interventions execute AND pass, the
  null holds, the causal trace stays complete, grounded reports change under
  perturbation, and confab risk is low. Hard-capped at 4 (never Level 5).
- `src/pneuma_lab/demo.py` is the canonical evidence demo (`python -m
pneuma_lab.demo`): passive Level-3 replay of `fixtures/sample_run.jsonl` +
  paired replay of every `fixtures/interventions/*.jsonl`, each replayed twice and
  compared byte-for-byte, consolidated into `build/canonical/summary.json` (+
  `summary.md`). It exits non-zero on any determinism regression and never
  re-scores the psyche — it drives the same harness/runner the tests use.
- `src/pneuma_lab/adapters/` (Phase 3 / 3.1) holds the deterministic
  PneumaTrace envelope (`envelope.py`, incl. the v0.2 anti-fake-cognition
  `consistency_errors` gate), the task-only SWE-Gym-Lite adapter
  (`swe_gym_lite.py`), the observable-only trajectory extraction rules
  (`trajectory.py`), and the trajectory-bearing OpenHands-Sampled and
  OpenHands-Verifier adapters (`openhands_sampled.py`, `openhands_verifier.py`).
  See `docs/phase-3-1-trajectory-traces.md`.
  Agent-trace frames are permitted ONLY when a real recorded trajectory
  exists; raw trajectory text never enters frames (digests + lengths only).
- `src/pneuma_lab/replay/bridge.py` expands trajectory-bearing PneumaTrace
  envelopes into deterministic per-step replay timelines.
- `src/pneuma_lab/converters/` and `src/pneuma_lab/training/` implement guarded,
  repo-local training-example conversion, split policy, readiness checks, and a
  tracked authorization/code/source-bound estimator preflight. No current
  manifest positively authorizes a training run.
- `src/pneuma_lab/estimators/` contains deterministic offline E1/E2 advisory
  estimators. They are not runtime control wiring or consciousness evidence.
- `src/pneuma_lab/brain/` (Phase 4) is the offline, CPU-only PneumaBrain-v0.1
  multi-task trainer: observable-only features, repo-grouped split, per-task
  logistic heads, a fail-closed corpus-authorization preflight, and a
  deterministic model/metrics/report writer. Advisory-only; no runtime.
- `src/pneuma_lab/nervous_system/` (PneumaNervousSystem-v0) is the shadow-mode,
  advisory-only I/O shell: it wraps PneumaBrain-v0.1 risk into a `RiskEstimateFrame`,
  a bounded verification-pressure CANDIDATE, an `InstinctSignal`, and a `CausalTrace`,
  aggregated into `PneumaInputBundle`/`PneumaOutputBundle` containers. An
  ablation/null test emits a conservative Level-1-compatible
  `ConsciousnessEvidenceFrame`. It never actuates, grants authority, or contacts a
  verifier; the kill switch suppresses control frames and writes an audit row.
  It also hosts BaselinePsycheSubject-v0 (`subject.py`): a minimal integrated,
  replayable `PsycheUnderTest` with persistent scar memory (`scar_memory.py`), a
  3-candidate global workspace (`workspace.py`), verification-only pressure, and
  scar/affect/workspace intervention tests (`subject_ablation.py`) — driven by the
  existing `ReplayHarness`/`PairedReplayRunner` but reported as conservative
  harness evidence only (no Level 2/3/4 claim). See `docs/nervous-system-v0.md`.
- `src/pneuma_lab/status.py` validates and reports the canonical current-state
  manifest with `python -m pneuma_lab.status --check`.
- `fixtures/sample_run.jsonl` is a failure-motif escalation timeline used by the
  replay tests and CLI. `fixtures/interventions/` holds the canonical Level-4
  scenarios (ablate scar graph, clamp tension, boost curiosity, remove identity
  anchors, disable workspace) plus a `restore` null and a failing-hypothesis case.
- `docs/` explains the research contract in human language;
  `docs/superpowers/` holds the Phase-1 and Phase-2 design specs + plans.
- `migration/` is read-only provenance and design/reference material.
- `tests/` verifies schema validity, frame validation, ported psyche math,
  output-frame validity, deterministic replay, evidence scoring, the perturbation
  hooks, the intervention schedule/report, deterministic paired replay, and the
  Level-4 gate (including honest refusal when interventions are absent or fail),
  and the canonical demo (valid summary, byte-determinism, L3/L4 buckets).

## Core Rules

- Keep Pneuma Lab standalone. Do not create imports from `C:\9to5` or write back
  into 9to5 unless the user explicitly asks for a separate operation.
- Treat copied migration material as provenance/reference, not live product
  code.
- Keep claims conservative: this repo evaluates possible machine interiority; it
  does not assert present phenomenal consciousness.
- Preserve verifier invariance: evidence and verdicts are additive/auditable,
  never overwritten by the psyche under test.
- Prefer narrow, schema-first changes and preserve implemented replay/eval
  invariants.
- Use 4-space indentation across source, schemas, and docs.
- Avoid adding heavy dependencies without a concrete phase that needs them.
- Do not touch secrets, `.git`, caches, virtualenvs, or private datasets unless
  explicitly authorized.

## Fast Editing Loop

1. Inspect the closest contract or doc before editing.
2. Make the smallest change that preserves the current standalone boundary.
3. Run the focused tests.
4. If a schema changed, verify all schemas parse and validate.
5. Update the nearest doc when a frame meaning, invariant, command, or workflow
   changes.

Useful commands:

```txt
python -m pytest tests/ -q
pip install -e ".[dev]"
python -m pneuma_lab.status --check
python -m pytest tests/test_schema_loads.py -q
git diff --check
```

## Schema Rules

- JSON schemas use Draft 2020-12 and 4-space indentation.
- Every frame declares `$schema`, `$id`, `title`, `description`, `type`,
  `x-pneuma-frame-kind`, and `x-pneuma-version`; non-frame manifests declare
  `x-pneuma-schema-kind` instead.
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
