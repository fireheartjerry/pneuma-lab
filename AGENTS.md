# Pneuma Lab -- AI navigation index

> Hand-authored from the 9to5 agent guide pattern for this standalone lab.
> Keep it short, current, and useful for fresh agent sessions.

## Mental Model

1. **Status first** -- `docs/project-status.json` is the canonical current-state
    manifest; run its checker before trusting dated research prose.
2. **Contracts next** -- `schemas/` defines frames, envelopes, training records,
    and machine-readable status.
3. **Evidence by replay** -- replay and paired interventions are implemented for
    the archived internal reference harness; they are not delivery gates.
4. **Integration is absent** -- Pneuma is not wired into 9to5 and is not an
    operational nervous system.
5. **Foundation is local and unrun** -- `pneuma_lab.foundation` implements the
    guarded 2B-to-4B tooling, but training remains unauthorized and no model is
    promoted.
6. **Claims last** -- learned-subject delivery does not import the legacy scorer
    or establish phenomenal consciousness.
7. **NeurIPS execution is active but gated** -- the Resampling Null synthetic
    core is the current implementation track. The AWS primary topology is two
    independent 8-vCPU Spot `g6e.2xlarge` workers (two L40S devices, 16 Spot
    vCPUs total), with canonical disjoint partitioning and freeze-and-resume
    recovery. AWS has $10,000 verified EC2-eligible credit plus a separate
    $100 credit, but fresh capacity/account evidence remains an admission gate.
    Credits never bypass protocol, authority, quota, or spend gates.

## Current NeurIPS Execution State

- Read `docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md`
  before changing Tasks 6-10. It is the live implementation handoff; the
  execution journal remains the forensic record.
- Tasks 1-5 are the accepted synthetic foundation. Tasks 6-9 are
  `implementation_complete; E2E_pending`; Task 8 is reconciled to the same
  state. Step 4A (the bounded implementation-verification lineage) remains
  unfinished beyond its miniature power final and sealed schedule. There is no
  complete authority-backed P0 lineage, benchmark/provider result, or
  scientific result of record. Task 10 is not complete.
- Task 6's freeze/projection/unblind and authenticated paired-publication
  plumbing is strong. It may be reported as `implementation_complete;
  E2E_pending` only after its scoped code, focused tests, and hostile review
  pass; it cannot be reported scientifically complete without real lineage.
- The canonical P0 screen and its first ten shards are preserved as an
  incomplete, experiment-only non-result. Do not resume, rewrite, finalize, or
  claim from them without a new explicit experimental authorization. Canonical
  full-grid/shard work never belongs in a software or integration gate.
- The immediate dependency chain is: complete bounded Step 4A through analysis
  -> revalidate Tasks 6/7 as implementation-path continuity -> finish Task 10
  implementation/release preparation. Canonical Step 4B and any real
  benchmark/model experiment remain separately authorized scientific work.
- Update the handoff/status documentation after each major implementation
  milestone or coherent commit group, not after every command. Record
  scientific executions and deviations in the append-only execution journal.
  Never let progress prose outrun committed evidence.
- **Implementation cadence:** defer broad hostile/adversarial campaigns and
  expensive forensic sweeps until the pre-experiment launch review. During
  implementation, run only focused, high-signal regressions needed to prevent
  data loss, authority bypass, leakage, or false scientific artifacts. This is
  a speed policy, not permission to weaken fail-closed contracts or skip the
  final hostile review.

## Standing Hostile-Review and Release Standard

- For every scientific, implementation, evidence, and release decision, model
    the strongest possible NeurIPS reviewer: prodigiously capable, maximally
    hostile, and personally motivated to reject the work. Proactively find the
    strongest rejection argument, exploit, ambiguity, leakage path, causal
    flaw, receipt mismatch, and reproducibility failure before making a claim.
    Keep the review professional, specific, and evidence-based.
- Preserve a forensic execution trail under the live contract in
    `docs/research/neurips-2026-workshop/33-execution-journal.md`. The journal is
    non-authoritative and append-only: it records commands, results, review,
    deviations, and corrections but never rewrites scientific authority.
- Cheap Claude/Codex CLI subprocesses may be used as expendable clerks for
    bounded menial work only when their incremental cost is kept low and the
    active governance/spend gates authorize the call. Record the exact task,
    tool/model, best available cost bound or actual cost, and compact
    input/output receipts. Treat every subprocess result as an untrusted
    proposal until directly verified; never delegate scientific authority,
    claim promotion, approval decisions, or final verification to it.
- Treat honest `do not claim` statements as baselines, not automatically as
    permanent endpoints. Maintain an evidence-to-claim upgrade ledger:
    non-claim -> missing evidence or novelty -> build/experiment -> hostile
    prior-art and causal audit -> falsification gate -> defensible promoted
    claim. Never erase caveats rhetorically or overclaim; distinguish permanent
    epistemic boundaries from unfinished or unrun work.
- Paper production and submission have a fail-closed release gate. At that
    time, freshly verify the manuscript and submission package against the live
    official venue and workshop guidance and official LaTeX template; remembered
    or previously cached rules are not authority. Verify anonymity, exact page
    limits and what counts toward them, margins, fonts, style files,
    bibliography/appendix/supplement policy, metadata, PDF build and visual
    rendering, embedded fonts, filenames and size limits, submission-form
    fields, and the deadline with its timezone. Any mismatch blocks release.
- Software tests are lightweight guardrails, not research deliverables. Default
  to one narrow high-signal test command per behavior change and one static
  check per slice; do not run broad or repeated suites without a concrete
  shared-surface risk or explicit user request. Every test process has a hard
  60-second wall-clock ceiling unless the user explicitly approves longer.
  Scientific experiments/evaluations are evidence work, not software tests,
  and remain governed by their own protocol, compute, and spending gates.
- Distinguish `implementation_complete`, `E2E_pending`, and scientifically
  complete in status reports. Passing tests proves software behavior, not an
  empirical result or claim.

## Commands

| Task | Command |
|---|---|
| Check current project status | `.venv/bin/python -m pneuma_lab.status --check` |
| Install current dev extras | `pip install -e ".[dev]"` |
| Check WSL2 foundation readiness | `.venv/bin/python -m pneuma_lab.foundation doctor` |
| Default cold oracle (smoke only) | `python -m pytest -q` |
| Opt-in Qwen collection/run | `python -m pytest tests/test_foundation_qwen_smoke.py -m qwen_smoke -q` |
| Foundation suite | Use the explicit PowerShell path set below (slow; suitable Linux execution environment) |
| Fast agent gate | `python scripts/test_fast.py` |
| Compact paper milestone | `python -m pytest tests/resampling_null -m milestone -q` |
| Forensic investigation | `python -m pytest tests/resampling_null -m forensic -q` |
| Run schema tests only | `.venv/bin/python -m pytest tests/test_schema_loads.py -q` |
| Check whitespace | `git diff --check` |
| List tracked/untracked state | `git status --short` |

`uv sync --frozen --python 3.12 --extra dev` is the deterministic Task 3
target, but remains fail-closed until slice 1 regenerates `uv.lock` and
`uv lock --check --python 3.12` passes.

Default pytest discovery is intentionally restricted to `tests/smoke`. Bare
marker commands cannot discover Qwen, foundation, or milestone tests; name an
explicit test path as above.

The foundation files retain two legacy sibling imports. In PowerShell, set the
test directory on `PYTHONPATH`, enumerate only foundation files, then run the
suite with prepend import mode:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'tests')
$foundationTests = Get-ChildItem -Path tests -Filter test_foundation_*.py -File | Select-Object -ExpandProperty FullName
python -m pytest $foundationTests -m foundation --import-mode=prepend -q
```

Collection of this exact path set is verified on the current Windows checkout;
the actual foundation suite is slow and intended for a suitable Linux execution
environment.

`python -m pytest -q` is the independent seven-case cold correctness oracle,
not the historical full suite. S02D remains a Linux milestone because its
production locking transaction is POSIX-only. Native-Windows timing and oracle
receipts remain pending external verification.

## How To Do X

- **Add a frame:** add `schemas/<name>.schema.json`, include the core metadata,
    add the filename to `INPUT_SCHEMA_FILES` or `OUTPUT_SCHEMA_FILES` in
    `src/pneuma_lab/schemas/__init__.py`, then update `docs/io-contract.md` and
    tests if counts changed.
- **Change a frame field:** update the schema description and the matching
    human-readable docs in `docs/io-contract.md` or `docs/source-map.md`.
- **Add a 9to5 adapter:** implement under `src/pneuma_lab/adapters/`, consume
    exported data only, and keep Pneuma independent from 9to5 imports.
- **Add replay behavior:** implement under `src/pneuma_lab/replay/` with fixtures
    that make input frames, output frames, and causal traces inspectable.
- **Add foundation behavior:** implement under `src/pneuma_lab/foundation/`,
    keep `C:\pneuma-data` read-only, write generated artifacts only under
    ignored `build/`, and do not import the legacy scorer.

## Tree Guide

- `README.md` gives the public one-page overview.
- `docs/project-status.json` is the machine-readable current-state source.
- `CLAUDE.md` gives session guidance for coding agents.
- `schemas/` is the stable frame-contract surface.
- `src/pneuma_lab/` is the importable package.
- `tests/` protects contracts, replay, interventions, adapters, governance, and
    offline estimator behavior.
- `docs/` contains the research narrative, invariants, and crosswalks.
- `migration/` contains provenance and read-only reference material copied from
    9to5 and manager-data.

## Packages

| Package | Purpose | Status |
|---|---|---|
| `pneuma_lab` | Public package metadata and frame lists | implemented |
| `pneuma_lab.schemas` | Schema pathing/loading helpers | implemented |
| `pneuma_lab.adapters` | Deterministic offline dataset-to-trace adapters | implemented |
| `pneuma_lab.replay` | Deterministic replay + trace bridge | implemented |
| `pneuma_lab.interventions` | Control/treated/null internal harness | implemented |
| `pneuma_lab.evals` | Internal-harness evidence scoring, capped at 4 | implemented |
| `pneuma_lab.converters` | Guarded training-example conversion | implemented |
| `pneuma_lab.training` | Split/readiness governance + estimator-run preflight | implemented, no positive authorization |
| `pneuma_lab.estimators` | Offline advisory E1/E2 estimators | implemented, no runtime wiring |
| `pneuma_lab.foundation` | Local Qwen pins, recurrent core, training/runtime gates, memory, authority | implemented tooling, not trained or promoted |

## Boundaries

- This repo does not import from 9to5.
- This repo does not modify 9to5 branches, PRs, runtime state, or private data.
- Migration files are reference/provenance unless the user explicitly asks to
    promote something into the live package.
- JSpace/J-lens work is a documented research contract only; no implementation,
    model access, or result exists.
- Qwen3.5-397B is a compatibility reference only; never download or serve it.
- Foundation training needs a positive, hash-bound authorization; the committed
    foundation authorization is intentionally pending.
- Use 4-space indentation everywhere.
