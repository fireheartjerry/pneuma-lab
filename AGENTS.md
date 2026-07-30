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
7. **Conditional compute stays gated** -- NeurIPS external-credit context is in
    `docs/superpowers/specs/2026-07-22-neurips-execution-discovery-design.md`
    §9.3; pending credits never bypass the §9.2 per-action approval gate.

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

## Commands

| Task | Command |
|---|---|
| Check current project status | `.venv/bin/python -m pneuma_lab.status --check` |
| Install current dev extras | `pip install -e ".[dev]"` |
| Check WSL2 foundation readiness | `.venv/bin/python -m pneuma_lab.foundation doctor` |
| Default cold oracle (smoke only) | `python -m pytest -q` |
| Opt-in Qwen collection/run | `python -m pytest tests/test_foundation_qwen_smoke.py -m qwen_smoke -q` |
| Foundation suite | Use the explicit PowerShell path set below (slow; suitable Linux execution environment) |
| Compact paper milestone | Unavailable until aggressive pruning Task 4 marks and retains the suite |
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

The compact milestone command is unavailable until aggressive pruning Task 4 marks and retains the suite.

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
