# Pneuma Lab Claude Guide

Pneuma Lab is a standalone research and evaluation harness for machine psyche:
software-engineering cognition, continuous affect, instinct, scar-tissue memory,
self-modeling, authority pressure, and consciousness-relevant evaluation.

This repo is intentionally smaller and cleaner than 9to5. Read
`docs/project-status.json` first for current implementation and blocker state;
the JSON schemas remain the observable contract surface. Replay, paired
interventions, dataset adapters, conversion guardrails, and offline estimators
exist. The local-first 2B-to-4B foundation tooling also exists, but its training
authorization is pending and no foundation model is trained or promoted. Live
9to5 integration and JSpace/J-lens experiments do not exist.

## Current NeurIPS Track

The active paper implementation is the Resampling Null synthetic core. Read
`docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md` before
editing Tasks 6-10 and use
`docs/research/neurips-2026-workshop/33-execution-journal.md` for the
append-only forensic trail.

- Tasks 1-5 are the accepted synthetic foundation. Tasks 6-9 (including Task
  8) are `implementation_complete; E2E_pending`. Step 4A, the bounded
  implementation-verification lineage, has reached a miniature power final and
  sealed schedule but has not reached analysis. Task 10 and the canonical P0
  lineage are not complete.
- Task 6 has strong freeze, blinded-projection, gated-unblind, durable-taint,
  and authenticated paired-publication plumbing. It can reach
  `implementation_complete; E2E_pending` independently, but cannot close E2E
  until real lineage reaches unblind and analysis.
- The canonical P0 screen and ten completed shards are an explicitly
  experiment-only incomplete non-result. Do not resume, mutate, finalize, or
  claim from them without explicit experimental authorization. Never put full
  grid/shard work in a software or integration test.
- The immediate dependency is bounded Step 4A -> implementation-path continuity
  revalidation for Tasks 6/7 -> Task 10 implementation/release preparation.
  Canonical Step 4B remains pending for the separately authorized experiment.
- No real benchmark, model-provider, unblind/analysis, or scientific result of
  record exists. AWS has $10,000 verified EC2-eligible credit plus a separate
  $100 credit. The primary topology is one 8-vCPU `g6e.2xlarge` with one L40S;
  only its matching G/VT quota may satisfy the AWS admission gate. Azure remains
  separately authorized and separately governed.

The public methodology name is **the PLACEBO Protocol** and the registered
experiment is **the PLACEBO Trial** (DL-160,
`docs/research/placebo-paper/01-terminology.md`). Internal `resampling_null`
identifiers, schemas, record kinds, receipts, and artifact identities are
unchanged. Paper materials are `paper/placebo_protocol.tex` and
`src/pneuma_lab/placebo_paper/` (fail-closed: only a verified sealed Task 10
package may supply a number). The pre-launch hostile review is
`src/pneuma_lab/adversarial_review/` and runs at Step 14, before Step 4B or any
GPU execution. Never claim placebo-controlled feedback evaluation is itself
novel.

Use exact status language: `implementation_complete`, `E2E_pending`, and
scientifically complete are different states. Tests validate plumbing; they do
not manufacture evidence.

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
- **Legacy evidence ladder**: archived internal-harness methodology in
  `docs/consciousness-levels.md`; non-authoritative and not a delivery gate.

## Read When Relevant

- Current machine-readable status: `docs/project-status.json`
- Project overview: `README.md`
- Research program (evidence-graded; start at the overview): `docs/research/00-program-overview.md`
- Architecture intent: `docs/vision.md`
- Frame contract map: `docs/io-contract.md`
- Local-first foundation: `docs/foundation/local-first-foundation.md`
- Legacy evidence ladder: `docs/consciousness-levels.md`
- Canonical L3-vs-L4 evidence demo: `docs/level4-evidence-demo.md`
- 9to5 source crosswalk: `docs/source-map.md`
- Migration account: `migration/MIGRATION_REPORT.md`
- Copied reference material: `migration/copied-from-9to5/` and
  `migration/copied-from-manager-data/`

## Tree Guide

- `schemas/` contains the Draft 2020-12 JSON Schema contracts. Keep these
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
  harness evidence only (no Level 2/3/4 claim). SubjectEvidenceCampaign-v0
  (`campaign.py`, `campaign_report.py`) runs five conservative evidence slices
  (L2 persistence, scar ablation, workspace disable, certainty clamp, grounded
  self-report) over the subject and writes deterministic, schema-valid
  `evidence_campaign` artifacts to `build/evidence_campaigns/` — no Level 2/3/4
  claim. CertifiedSubjectFactory-v0 (`interventions/certified_subjects.py`,
  `nervous_system/certified_subject.py`, `certified_campaign.py`) earns a REAL
  `subject_factory_eligible` via a snapshot/clone-equivalence probe and runs the
  five slices through the promotable `PairedReplayRunner`; eligibility is real but
  Level 2/3/4 promotion stays blocked by unevidenced families — no level claim.
  See `docs/nervous-system-v0.md`.
- `src/pneuma_lab/voice/` (PneumaVoice-v0, Phase A) is the read-only expressive
  surface: per-tick output frames → `ThoughtAtom`s (pure fact + receipts) →
  `RenderedThought` + evidence sidecar, deterministic and receipt-bound. The
  observed-vs-credited gate always shows observed atoms and hedges
  uncredited-family atoms as "architecture-only, not promotable evidence"; the
  scorer never reads rendered prose. Ships a byte-deterministic transcript
  (`stream.md`/`stream.jsonl`/`sidecar.json`) and a
  `python -m pneuma_lab.voice` CLI. Phase B (verified LLM voiced skin) and
  Phase C (HTML mind monitor) are implemented; v0.1 (`config.py`, `ollama.py`)
  adds an optional dependency-free local Ollama elaboration layer — a voiced
  skin plus a fail-closed entailment judge over a structured grounding packet,
  surfaced as seven `voice_status` values — and monitor v2 (internal-state
  panel + timeline scrubber); prose stays non-canonical and the scorer stays
  prose-blind. See `docs/pneuma-voice-v0.md`.
- `src/pneuma_lab/status.py` validates and reports the canonical current-state
  manifest with `python -m pneuma_lab.status --check`.
- `src/pneuma_lab/foundation/` contains the pinned Qwen3.5 architecture
  contracts, bounded recurrent junction, falsification/curriculum/resource
  gates, immutable shard tooling, checkpoint/resume, SQLite/FTS5 memory, local
  action scopes, and offline runtime loader. It never imports the legacy scorer;
  its committed authorization is `not_authorized`.
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
- During implementation, prioritize momentum: use focused high-signal tests and
  only repair concrete data-loss, authority, leakage, or false-artifact risks.
  Defer broad hostile/adversarial campaigns and expensive forensic sweeps to the
  dedicated pre-experiment launch review. This does not permit bypassing
  fail-closed contracts or ignoring a concrete high-severity flaw.
- Update the live handoff/status docs after each major implementation
  milestone or coherent commit group, not after every command. Journal
  scientific runs and deviations at the granularity required for replay.

## Fast Editing Loop

1. Inspect the closest contract or doc before editing.
2. Make the smallest change that preserves the current standalone boundary.
3. Run the focused tests.
4. If a schema changed, verify all schemas parse and validate.
5. Update the nearest doc when a frame meaning, invariant, command, or workflow
   changes.

Useful commands:

```txt
python -m pytest -q                                                    # default cold oracle: smoke only
python scripts/test_fast.py                                             # disposable five-second smoke gate
python scripts/test_fast.py --smoke
python scripts/test_fast.py --cold
python -m pytest tests/resampling_null -m milestone -q                 # explicit compact Linux milestone
python -m pytest tests/resampling_null -m forensic -q                  # explicit forensic tier
python -m pytest tests/test_foundation_qwen_smoke.py -m qwen_smoke -q # opt-in Qwen smoke
pip install -e ".[dev]"
python -m pneuma_lab.status --check
python -m pytest tests/test_schema_loads.py -q
git diff --check
```

Default pytest discovery is intentionally restricted to `tests/smoke`; bare
marker commands cannot discover opt-in Qwen, foundation, or milestone tests.
The explicit-path commands above retain the marker opt-outs and allow a final
`-m` selector to opt in. The compact milestone suite is Linux-only where it
exercises the production POSIX lock transaction; native-Windows timing and
oracle receipts remain pending external verification.

The foundation files retain two legacy sibling imports. Use this collection-
verified PowerShell path set (the actual suite is slow and intended for a
suitable Linux execution environment):

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'tests')
$foundationTests = Get-ChildItem -Path tests -Filter test_foundation_*.py -File | Select-Object -ExpandProperty FullName
python -m pytest $foundationTests -m foundation --import-mode=prepend -q
```

On Windows the foundation shard-digest tests fail on a CRLF checkout and are
xfail environment artifacts, not regressions.

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
