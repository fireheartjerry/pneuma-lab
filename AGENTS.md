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

## Commands

| Task | Command |
|---|---|
| Check current project status | `python -m pneuma_lab.status --check` |
| Install dev extras | `pip install -e ".[dev]"` |
| Check WSL2 foundation readiness | `python -m pneuma_lab.foundation doctor` |
| Run the full suite | `python -m pytest tests/ -q` |
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
