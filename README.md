# Pneuma Lab

**A standalone research project for machine psyche** — software-engineering
cognition, continuous affect, instinct, scar-tissue memory, self-modeling,
authority pressure, and consciousness-relevant evaluation.

Pneuma Lab is the external research/evaluation harness for the Human-Nature /
Psyche architecture prototyped inside the 9to5 autonomous engineering agent. It
lifts the _ideas and contracts_ into a clean environment where interior states can
be defined, replayed, **perturbed**, and **externally audited** — without a
production agent's constraints.

> Pneuma Lab does not claim present phenomenal consciousness by assertion.
> It is designed to build and evaluate progressively stronger machine interiority:
> persistent, integrated, valenced, self-modeling, causally active, perturbable,
> and externally auditable internal states.
> Aggressively investigated; conservatively claimed. See
> [`docs/consciousness-levels.md`](docs/consciousness-levels.md).

## Status

**Phase 1 — deterministic replay harness + live Level-3 architecture exercise.**
On top of the 13 frame schemas, Pneuma Lab now has a working replay surface: it
loads a recorded input-frame timeline, validates it, and drives it through a
`PsycheUnderTest` implementation that emits schema-valid output frames with
`CausalTrace` receipts, then scores a Level 0–3 `ConsciousnessEvidenceFrame`.

The reference mind (`ReferencePsyche`) is deterministic (no ML, no roleplay) and
wires **all nine consciousness-indicator families** into the live control loop, so
the run honestly reaches **Level 3** ("consciousness-indicator architecture is live
and causally connected"). It cannot claim Level 4: Phase 1 runs no interventions,
so `causal_intervention_robustness` stays architecture-only and the scorer
hard-caps at 3. No ML training, no wiring back into 9to5. See
[`migration/MIGRATION_REPORT.md`](migration/MIGRATION_REPORT.md) and the Phase-1
design/plan under `docs/superpowers/`.

### Run a replay

```bash
pip install -e ".[dev]"
python -m pneuma_lab.replay fixtures/sample_run.jsonl -o build/replay
# -> writes build/replay/output_frames.jsonl + build/replay/evidence.json
#    prints: ... evidence_level=3 confab_risk=0.0 (interventions_seen=0, executed=0)
```

## Layout

```
schemas/                     13 JSON Schema (Draft 2020-12) frame contracts
    world-frame · agent-trace-frame · memory-frame · governance-frame · intervention-frame   (5 inputs)
    psyche-state-frame · workspace-broadcast · instinct-signal · control-pressure-vector ·
    authority-request · causal-trace · consciousness-evidence-frame · grounded-self-report    (8 outputs)

docs/
    vision.md                  what this is and why
    io-contract.md             human-readable map of the 13 frames + invariants
    consciousness-levels.md    the 0–5 evidence ladder (near-term target: Level 4)
    source-map.md              schema ↔ 9to5 module cross-walk
    migration-notes.md         how the scaffold was derived + gotchas

src/pneuma_lab/              schemas are the real contract; Phase 1 adds live surfaces
    schemas/                   schema load helpers + validate.py (frame validation)
    psyche/                    PsycheUnderTest interface + ReferencePsyche (Level-3 mind)
                               + ported pure math (manifold, prototypes, mood, drives, authority)
    replay/                    ReplayHarness + JSONL IO + tick grouping + CLI (implemented)
    evals/                     ConsciousnessEvidenceScorer (Level 0–3, implemented)
    adapters/                  empty seam (Phase 2: 9to5-trace adapters)

fixtures/
    sample_run.jsonl           a failure-motif escalation timeline (input frames)

tests/
    test_schema_loads.py       every schema exists, parses, and is a valid JSON Schema
    test_validate.py           frame validation helper
    test_psyche_math.py        ported manifold/drives/authority/hash math
    test_psyche_outputs.py     ReferencePsyche emits valid, bounded output frames
    test_replay_harness.py     end-to-end replay reaches Level 3, capped below 4
    test_evidence_scoring.py   memory-readback ablation (Level-2 proof) + conservatism
    test_determinism.py        same input ⇒ byte-identical outputs + hash chain

migration/
    MIGRATION_REPORT.md        the formal migration account (read this)
    copied-from-9to5/          READ-ONLY reference: spec, plan, module map, pure interfaces
    copied-from-manager-data/  READ-ONLY reference: pipeline README + operator-integration doc
```

## The contract in one breath

Input frames describe the **world, the agent's observable trace, retrieved memory,
operator governance, and experimental interventions**. Output frames describe the
**integrated psyche state (continuous affect + drives), workspace broadcast,
instinct signals, bounded control pressure, discrete authority requests, an
auditable causal trace, an evidence-graded consciousness frame, and a grounded
self-report**. Invariants: affect is continuous (labels are projections); outputs
are _pressure, not commands_; verification is additive-only; authority is the `min`
of five ceilings; every claim shows receipts; the kill switch is a byte-identical
no-op. Full map: [`docs/io-contract.md`](docs/io-contract.md).

## Develop

```bash
pip install -e ".[dev]"             # jsonschema (runtime) + pytest
python -m pytest tests/ -q          # schema + psyche + replay + evidence + determinism
python -m pneuma_lab.replay fixtures/sample_run.jsonl -o build/replay
```

Requires Python ≥ 3.11. The psyche math is standard-library only; `jsonschema` is
now a runtime dependency because the replay harness validates every input and
output frame (evaluation Layer A).

## Boundaries

- Pneuma Lab never imports from — nor is imported by — 9to5.
- No 9to5 production code, branch, or PR (#38) is modified by this project.
- manager-data is **possible future operator-preference context only**, never the
  base mind and never overfit to. No data/secrets were copied.
