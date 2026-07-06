# Reference material copied from `C:\9to5` (READ-ONLY, NOT ACTIVE RUNTIME)

Everything in this directory is **migrated reference material**, copied verbatim
from the 9to5 repository on 2026-07-06 for grounding the Pneuma Lab I/O contracts.

> ⚠️ **None of this is active Pneuma Lab runtime code.** The `.py` files under
> `reference-interfaces/` are _snapshots of 9to5's pure interface modules_. They
> are intentionally kept **outside** `src/` and outside the pytest test paths so
> they are never imported or executed by Pneuma Lab. They exist only so the
> schemas in `../../schemas/` can be checked against the shapes they mirror.
> Do not import them. Do not treat them as a dependency. When Phase 2 ports
> selected pure modules, it will re-derive clean versions, not run these copies.

## Contents

| Path                                                | What                                                                       | Why kept                                                                          |
| --------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `specs/2026-07-06-human-nature-psyche-v2-design.md` | The full v2 "Psyche" design spec (APPROVED IN PRINCIPLE, NOT implemented). | Source of truth for the whole architecture; the schemas are derived from it.      |
| `specs/2026-07-06-human-nature-psyche-v2.md`        | The implementation plan generated from the spec.                           | Phase structure + task breakdown for the future port.                             |
| `human_nature-AGENTS.md`                            | Generated module map of `9to5/human_nature/`.                              | Names every faculty module + its exports; the `source-map.md` cross-walk uses it. |
| `reference-interfaces/*.py`                         | 10 small, **pure** interface modules (state shapes, update laws, enums).   | Ground the field names / enums / ranges in the schemas against the real code.     |

## The reference interfaces (what each grounds)

- `self_state.py` — the interior dict shape (schema v2), competence `{p, n}`, affect.
- `affect_manifold.py` — the 9 continuous axes + update law + decay (→ `PsycheStateFrame.affect_manifold`).
- `prototypes.py` — smooth label projection (→ `prototype_mixture`).
- `mood.py` — slow persistent homeostat (→ `PsycheStateFrame.mood`).
- `drives.py` — the 8 core drives + derived signals (→ `PsycheStateFrame.drives` / `derived_signals`).
- `authority.py` — the 5-tier ladder + `resolve()` `min`-over-caps (→ `AuthorityRequest`).
- `operator_authority.py` — domain/operator/safety/verifier-invariance ceilings (→ `GovernanceFrame`, `AuthorityRequest.resolution`).
- `run_events.py` — the discrete run-event enum (→ `WorldFrame.tool_events` / instinct inputs).
- `workspace.py` — the 10-term salience function + GWT competition (→ `WorkspaceBroadcast`).
- `instinct_signal.py` — the `InstinctSignal` dataclass + enums (→ `instinct-signal.schema.json`, near-exact mirror).

These were chosen because they are **pure** (stdlib-only, no I/O, no hot-path
coupling). Bridge/coupling code, persistence, and the Discord surface were
**deliberately not copied** — see `../MIGRATION_REPORT.md` §4.
