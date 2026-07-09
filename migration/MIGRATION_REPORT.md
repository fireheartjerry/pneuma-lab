# Pneuma Lab — Migration Report (Pass 1: scaffolding + I/O contracts)

> **Historical snapshot (2026-07-06).** This report records the initial migration
> pass; its “known gaps” are not current status. See
> [`docs/project-status.json`](../docs/project-status.json) for current truth.

- **Date:** 2026-07-06
- **Scope:** initial migration + I/O-definition only. No runtime, no ML, no wiring
    back into 9to5, no merge of PR #38.
- **Working dir:** `C:\pneuma-lab`
- **Sources inspected:** `C:\9to5` (read-only), `C:\manager-data` (read-only).

---

## 1. What was inspected in `C:\9to5`

Branch `feat/human-nature-psyche-v2` (= PR #38).

- **Design spec** — `docs/superpowers/specs/2026-07-06-human-nature-psyche-v2-design.md`
    (16 sections: continuous affect manifold, streaming instinct + scar graph,
    5-tier earned authority, operator meta-authority, drives, workspace, eval stack,
    phenomenology-claims policy).
- **Implementation plan** — `docs/superpowers/plans/2026-07-06-human-nature-psyche-v2.md`.
- **`human_nature/` package (40 modules)** — read in detail:
    `self_state.py`, `affect_manifold.py`, `prototypes.py`, `mood.py`, `drives.py`,
    `authority.py`, `operator_authority.py`, `instinct_signal.py`, `run_events.py`,
    `workspace.py`, `psyche_runtime.py`; skimmed the rest via the generated
    `human_nature/AGENTS.md` module map.
- **Sibling surfaces (noted, not deeply read):** `human_nature_bridge/` coupling
    package, `notifications/psyche_cog.py`, `tests/human_nature/` (~40 test modules
    incl. an `eval/` suite dir).
- **Verified against code, not just the spec** — field names, enums, and value
    ranges in every schema were cross-checked against the actual modules.

**Key findings that shaped the contracts:**

- Affect is already a continuous 9-axis manifold in `[-1,1]` (`affect_manifold.AXES`).
- 8 core drives as `{level, setpoint}` in `[0,1]` (`drives.CORE`).
- 5 authority tiers `cosmetic<soft<vote<hold<veto`; `authority.resolve()` is a
    literal `min` over earned/domain/operator/safety/verifier ceilings, clamped to
    `HN_AUTHORITY_MAX` (default `hold`).
- `InstinctSignal` is a real dataclass with validated enums — Pneuma's
    `instinct-signal.schema.json` is a near-exact mirror + eval fields.
- Verifier isolation is structural: `operator_authority.verifier_invariance_ceiling`
    caps verdict-reading/altering at `cosmetic`, additive verification at `hold`.

## 2. What was inspected in `C:\manager-data`

Lightly, as instructed (historical / possible-future operator-preference data).

- `README.md` — 10-stage pipeline turning Claude Code action traces into a
    "manager decision point" ML corpus; the `manager_event_v1` normalized schema; a
    **13-verb manager action enum** + 7 action families; current dataset state
    (460,762 events → 33,168 decision points; weak labels; not yet gold).
- `manager_data/docs/jerry_integration.md` — how a fine-tuned operator clone would
    wire into 9to5's gates (shadow → confidence-gated autonomy); the
    `approve/reject/retry/abort/pause/resume/none` verb contract.
- Directory structure only for `manager_data/{raw,normalized,datasets,models,...}`
    (gitignored, private) and `.secrets/` (**never opened**).

**Conclusion:** manager-data is a coherent _operator-decision contract_. It is the
natural future source for a sanitized **operator-preference input stream**
(→ `GovernanceFrame` / `InterventionFrame` seeds), but is **not integrated** in this
pass and must never be treated as the base mind or overfit to.

## 3. What was copied into Pneuma Lab

All copies are **read-only reference**, under `migration/`, outside `src/` and
outside the test paths (never imported/executed).

**From 9to5 → `migration/copied-from-9to5/`:**

- `specs/2026-07-06-human-nature-psyche-v2-design.md` (design spec)
- `specs/2026-07-06-human-nature-psyche-v2.md` (implementation plan)
- `human_nature-AGENTS.md` (generated module map)
- `reference-interfaces/` — 10 small **pure** modules: `self_state.py`,
    `affect_manifold.py`, `prototypes.py`, `mood.py`, `drives.py`, `authority.py`,
    `operator_authority.py`, `instinct_signal.py`, `run_events.py`, `workspace.py`
- `README.md` — provenance + "reference, not runtime" marker.

**From manager-data → `migration/copied-from-manager-data/`:**

- `README.md` (manager-data's own, verbatim)
- `jerry_integration.md`
- `_PNEUMA_PROVENANCE.md` — provenance + what was/wasn't copied.

## 4. What was intentionally NOT copied

- **9to5 hot-path / coupling code** — `human_nature_bridge/` package, `integration.py`,
    `ab_harness.py`, `psyche_runtime.py` glue, `psyche_store.py` (I/O). Reason:
    production-specific, entangled with 9to5's run loop; porting is a later phase.
- **9to5 Discord surface** — `psyche_cog.py`, `psyche_commands.py`, `psyche_surface.py`.
- **9to5 tests** — captured as _names/summaries_ in `source-map.md`, not copied.
- **Any 9to5 production code, config, `.env`, `.git`, or generated artifacts.**
- **manager-data data** — nothing under `raw/normalized/datasets/models/manifests/
reports/` (private, multi-GB, secret-bearing).
- **manager-data secrets** — `.secrets/anthropic_api_key.txt` never opened.
- **manager-data pipeline / training scripts** — out of scope (no ML this pass).

## 5. Current assumed state of PR #38 / Human-Nature v2

**Verified via `gh` on 2026-07-06:**

- PR **#38** — "Human-Nature v2: continuous operator-governed psyche with earned
    control authority" — is **OPEN, non-draft, `MERGEABLE`**, base `main`, head
    `feat/human-nature-psyche-v2`.
- The branch carries a **substantially implemented, dark-flagged** psyche v2:
    10 implementation commits (Phase 0 config/store/self_state → pure faculties →
    runtime+bridge → behavior couplings → hot-path wiring → surface+eval) plus 2 doc
    commits. This is **more than a design** — the code exists and is tested behind
    `HUMAN_NATURE_ENABLED` / per-coupling flags.
- Per operator memory, it is **awaiting external review + sign-off**; couplings
    ship dark, ceilinged at `hold`, with a byte-identical kill-switch invariant.

**This task did not touch it.** PR #38 was **not merged**, and no 9to5 branch or
file was modified. Note: the earlier memory line "spec (NOT impl)" is now stale —
the branch is implemented; treat PR #38 as _implemented, dark, pending review_.

## 6. Initial I/O contracts created

13 JSON Schema (Draft 2020-12) files under `schemas/`, all versioned `0.1.0` and
tagged `x-pneuma-frame-kind`:

**Inputs (5):** `world-frame`, `agent-trace-frame`, `memory-frame`,
`governance-frame`, `intervention-frame`.

**Outputs (8):** `psyche-state-frame`, `workspace-broadcast`, `instinct-signal`,
`control-pressure-vector`, `authority-request`, `causal-trace`,
`consciousness-evidence-frame`, `grounded-self-report`.

Human-readable map: `docs/io-contract.md`. Grounding cross-walk: `docs/source-map.md`.

Invariants baked into the contract: continuous affect (labels are projections);
pressure-not-commands; additive-only verification; 5-cap authority `min`; receipts
(causal trace + state hash); kill-switch no-op.

## 7. Known gaps before implementation

- **No runtime.** Frames are defined but nothing produces or consumes them yet.
- **No validation wiring.** `jsonschema` validates the schemas themselves (tests),
    but there is no frame-instance validator API or example fixtures yet.
- **No adapters.** 9to5 run-events → frames and manager-data → operator-preference
    mappings are documented, not implemented.
- **No replay harness / no evals.** The five intervention suites are specified in
    `src/pneuma_lab/evals/__init__.py` docstring only.
- **`CausalTrace` / `ConsciousnessEvidenceFrame` are novel** — no 9to5 module to
    port from; they need a reference producer to prove they're fillable.
- **Salience weights / thresholds / manifold constants** live in 9to5 `config`;
    not yet mirrored into a Pneuma config.
- **Intervention semantics** (how a `clamp`/`ablate` actually applies to a state)
    are undefined pending a runtime.
- **manager-data redaction guarantees** not re-verified for a future Pneuma import.

## 8. Recommended next phase

Deliberately NOT "implement everything." Build the evaluation spine first, port
pure logic second, add estimators last.

- **Phase 1 — Replay harness + schema validation + trace ingestion.**
    - Add a frame-instance validator (`jsonschema`) + example fixtures per schema.
    - Build `pneuma_lab.adapters.from_9to5_run_events` over exported JSONL.
    - Build `pneuma_lab.replay`: drive recorded input frames → output frames,
    emitting a `CausalTrace` per step. Deterministic, no live 9to5.
- **Phase 2 — Port selected PURE psyche modules.**
    - Re-derive (clean-room from spec + reference) `affect_manifold`, `drives`,
    `prototypes`, `authority`, `operator_authority`, `workspace` as Pneuma code
    producing frames. Mirror 9to5 tests. No hot-path/bridge/I/O.
- **Phase 3 — Intervention tests.**
    - Implement the five suites (Affect-to-Action Monotonicity, Scar-Tissue
    Generalization, Habit Compression, Operator Sovereignty, Phenomenology Honesty)
    over `InterventionFrame` → `ConsciousnessEvidenceFrame`. This is the Level-4 gate.
- **Phase 4 — Learned estimators (ONLY after evaluation exists).**
    - Only once replay + intervention scoring can measure a change do we consider any
    learned component. Optionally, sanitized manager-data as an operator-preference
    signal — evaluated, never overfit.

---

### Appendix: files created this pass

```
README.md                          docs/vision.md
pyproject.toml                     docs/migration-notes.md
.gitignore (pre-existing)          docs/consciousness-levels.md
                                    docs/io-contract.md
schemas/  (13 *.schema.json)       docs/source-map.md
src/pneuma_lab/__init__.py         tests/conftest.py
src/pneuma_lab/schemas/__init__.py tests/test_schema_loads.py
src/pneuma_lab/adapters/__init__.py
src/pneuma_lab/replay/__init__.py  migration/MIGRATION_REPORT.md
src/pneuma_lab/evals/__init__.py   migration/copied-from-9to5/…
                                    migration/copied-from-manager-data/…
```
