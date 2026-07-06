# Pneuma Lab -- AI navigation index

> Hand-authored from the 9to5 agent guide pattern for this standalone scaffold.
> Keep it short, current, and useful for fresh agent sessions.

## Mental Model

1. **Contracts first** -- `schemas/` defines the observable I/O frame language.
2. **Loaders second** -- `src/pneuma_lab/schemas/` proves the contracts are
    locatable and parseable from Python.
3. **Replay later** -- adapters, replay, and evals are named seams until real
    producers and fixtures exist.
4. **Claims last** -- consciousness language is evidence-graded, conservative,
    and tied to externally auditable causal traces.

## Commands

| Task | Command |
|---|---|
| Install dev extras | `pip install -e ".[dev]"` |
| Run scaffold tests | `python -m pytest tests/ -q` |
| Run schema tests only | `python -m pytest tests/test_schema_loads.py -q` |
| Check whitespace | `git diff --check` |
| List tracked/untracked state | `git status --short` |

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
- **Add evals:** place scoring and perturbation suites under
    `src/pneuma_lab/evals/`, then tie claims back to
    `docs/consciousness-levels.md`.

## Tree Guide

- `README.md` gives the public one-page overview.
- `CLAUDE.md` gives session guidance for coding agents.
- `schemas/` is the stable frame-contract surface.
- `src/pneuma_lab/` is the importable package.
- `tests/` protects schema validity and scaffold importability.
- `docs/` contains the research narrative, invariants, and crosswalks.
- `migration/` contains provenance and read-only reference material copied from
    9to5 and manager-data.

## Packages

| Package | Purpose | Status |
|---|---|---|
| `pneuma_lab` | Public package metadata and frame lists | scaffolded |
| `pneuma_lab.schemas` | Schema pathing/loading helpers | implemented |
| `pneuma_lab.adapters` | Future imports from exported 9to5/manager data | seam |
| `pneuma_lab.replay` | Future deterministic replay harness | seam |
| `pneuma_lab.evals` | Future perturbation and evidence scoring suites | seam |

## Boundaries

- This repo does not import from 9to5.
- This repo does not modify 9to5 branches, PRs, runtime state, or private data.
- Migration files are reference/provenance unless the user explicitly asks to
    promote something into the live package.
- Use 4-space indentation everywhere.
