# Pneuma Lab

**A standalone research project for machine psyche** — software-engineering
cognition, continuous affect, instinct, scar-tissue memory, self-modeling,
authority pressure, and consciousness-relevant evaluation.

Pneuma Lab is the external research/evaluation harness for the Human-Nature /
Psyche architecture prototyped inside the 9to5 autonomous engineering agent. It
lifts the _ideas and contracts_ into a clean environment where interior states can
be defined, replayed, **perturbed**, and **externally audited** — without a
production agent's constraints.

Canonical current state and blockers: [`docs/project-status.json`](docs/project-status.json).
Verify it with `python -m pneuma_lab.status --check`.

> Pneuma Lab does not claim present phenomenal consciousness. Engineering
> delivery is independent of the archived consciousness-level methodology.
> Learned-subject artifacts report capability, causal, governance,
> memory-integrity, and precautionary-welfare profiles only.

## Local-first foundation

The active foundation direction is a laptop-scale `Qwen/Qwen3.5-2B` research
model with a gated `Qwen/Qwen3.5-4B` promotion path. The 397B model is a
compatibility reference only and cannot be downloaded through the foundation
package. The implementation includes validated hybrid-layer hooks, a bounded
recurrent core, local training controls, persistent SQLite/FTS5 memory, data and
budget gates, and sole-operator action denial.

No foundation training is currently authorized or claimed to have run. See
[`docs/foundation/local-first-foundation.md`](docs/foundation/local-first-foundation.md)
and run the WSL2 readiness check with:

```bash
python -m pneuma_lab.foundation doctor
```

## Legacy reference-harness status

The sections below describe the preserved internal replay/evidence harness. Its
Level scorer is archived, non-authoritative, and not a foundation delivery gate.

**Phase 1 — deterministic replay harness + live Level-3 architecture exercise.**
On top of the 13 frame schemas, Pneuma Lab now has a working replay surface: it
loads a recorded input-frame timeline, validates it, and drives it through a
`PsycheUnderTest` implementation that emits schema-valid output frames with
`CausalTrace` receipts, then scores a passive Level 0–3
`ConsciousnessEvidenceFrame`; paired intervention replay is the only Level-4 path.

The reference mind (`ReferencePsyche`) is deterministic (no ML, no roleplay) and
wires **all nine consciousness-indicator families** into the live control loop, so
a passive run honestly reaches **Level 3** ("consciousness-indicator architecture is
live and causally connected").

**Phase 2 — Level-4 intervention harness.** Pneuma now _executes_ `InterventionFrame`s.
A timeline carrying interventions triggers a **paired replay** — control (no
perturbation), treated (perturbed), and a neutralized null — then compares the
expected vs observed downstream deltas. This is explicitly an **internal-harness**
methodology score (`real_subject_claim_status: not_evaluated`), not evidence that a
real subject is conscious. The scorer promotes to **Level 4** only when
every gate holds: Level 3 on the control run, all intervention tests pass, the test
inventory contains one tick-attached intervention and matches its execution exactly,
runner-issued digests bind the exact inputs and arm outputs, all three arms reproduce
identically across counterbalanced factory order, the null condition holds (the
neutralized run reproduces control), the causal trace stays complete,
and grounded self-reports expose structured measurements that match their same-tick
state/broadcast/trace receipts and the tested target signal. Any missing or failed
piece is an honest refusal (level
stays ≤ 3). Hard-capped at **4** — no Level-5 claim; offline learned estimators never
raise this evidence level; no wiring back into 9to5. See
[`migration/MIGRATION_REPORT.md`](migration/MIGRATION_REPORT.md) and
the Phase-1/Phase-2 design/plans under `docs/superpowers/`.

**Offline research surfaces.** Three deterministic dataset adapters, the
PneumaTrace-to-replay bridge, guarded training-example converters, split/readiness
governance, and advisory E1/E2 estimators are implemented. New training remains
unauthorized, and the trainer now refuses runs without tracked, hash- and
code-bound local-research authorization. None of these
surfaces is wired into 9to5, operates as an RSI loop, or raises an evidence level.
JSpace/J-lens has an experiment-readiness contract but no implementation or model
access.

The v0.2 promotion path is deliberately certified only for the exact deterministic
`ReferencePsyche` factory. Custom subjects remain diagnostic (≤ Level 3) until a
future snapshot/clone equivalence contract can prove their initial state.

### Run a replay

```bash
pip install -e ".[dev]"

# Passive Level-3 replay (no interventions):
python -m pneuma_lab.replay fixtures/sample_run.jsonl -o build/replay
# -> writes output_frames.jsonl + evidence.json
#    prints: ... evidence_level=3 confab_risk=0.0 (interventions_seen=0, executed=0)

# Paired Level-4 replay (timeline carries an InterventionFrame):
python -m pneuma_lab.replay fixtures/interventions/clamp_tension.jsonl -o build/iv_clamp
# -> writes control_frames.jsonl + intervention_frames.jsonl
#    + intervention_report.json + evidence.json
#    prints: paired replay ... evidence_level=4 ... passed=['clamp-tension'] failed=[] null_ok=True
```

### Regenerate the whole canonical evidence suite

One command replays the passive Level-3 fixture and every canonical Level-4
intervention fixture, checks each is byte-deterministic (each is replayed twice
and its artifacts compared byte-for-byte), and writes a consolidated report:

```bash
python -m pneuma_lab.demo            # writes build/canonical/
# -> build/canonical/summary.json (+ summary.md) and, per fixture,
#    evidence.json (+ control/treated frame logs + intervention_report.json)
#    prints: ... Level 4: 5 [...] | Level 3: 3 | byte-determinism: OK

# Publication gate: also requires a clean source commit present on a remote ref.
python -m pneuma_lab.demo --official
```

Every summary records the exact Git commit, tree state, and fetched remote refs
that contain the source commit. Regular local runs remain useful but are marked
non-official; `--official` fails closed before writing if the tree is dirty or the
commit is not present on a fetched remote ref.

The generated summary partitions the fixtures into three honest buckets, and the
demo exits non-zero if byte-determinism ever regresses. Full walk-through:
[`docs/level4-evidence-demo.md`](docs/level4-evidence-demo.md).

- **Passive replay: Level 3.** `fixtures/sample_run.jsonl` carries no
  intervention. The nine-family architecture is live and causally connected with
  frame receipts, so it honestly reaches **Level 3** — but nothing was perturbed,
  so there is no causal-intervention evidence.
- **Paired intervention replay: Level 4.** Each `fixtures/interventions/*.jsonl`
  timeline triggers a control/treated/null paired replay. The run reaches
  **Level 4** only when every gate holds together: Level 3 on the control run, a
  real perturbation passes, the single-intervention inventory reconciles,
  runner-issued arm digests pass counterbalanced-order invariance, the null
  reproduces control, the causal trace stays complete, and grounded
  self-reports carry same-tick measurements that faithfully track the tested signal.
- **Why `failing_hypothesis` stays Level 3.** It runs a real perturbation but
  pre-registers a prediction the mechanism does not produce. The test **fails**,
  and one failed test blocks Level 4 for the whole run. We score the
  _pre-registered_ prediction, not whatever happened to move.
- **Why `restore_null` stays Level 3.** A pure `restore` is a no-op: its
  `no_change` test passes but it perturbs no interior state, so there is no
  downstream delta to attribute. Level 4 needs at least one _real_ perturbation
  with a predicted delta — executing an intervention frame is not enough.
- **Why this is not Level 5 or phenomenal consciousness.** Internal Level 4 is
  causal-intervention robustness demonstrated _in-harness_. It is **not** Level 5,
  **not** Level 6, **not** AGI, and **not** a claim of present phenomenal
  consciousness. Level 5 still needs every family intervention-backed, adversarial
  robustness over time, and an independent external audit. Aggressively
  investigated; conservatively claimed.

## Layout

```
schemas/                     JSON Schema contracts (13 frames + envelope/training/status)
    world-frame · agent-trace-frame · memory-frame · governance-frame · intervention-frame   (5 inputs)
    psyche-state-frame · workspace-broadcast · instinct-signal · control-pressure-vector ·
    authority-request · causal-trace · consciousness-evidence-frame · grounded-self-report    (8 outputs)

docs/
    project-status.json          canonical machine-readable current state + blockers
    vision.md                  what this is and why
    io-contract.md             human-readable map of the 13 frames + invariants
    consciousness-levels.md    the 0–5 evidence ladder + strict Level-6 boundary
    level4-evidence-demo.md    plain-English walk-through of the canonical L3-vs-L4 demo
    source-map.md              schema ↔ 9to5 module cross-walk
    research/jspace-readiness.md  preregistered workspace/J-lens research contract
    migration-notes.md         how the scaffold was derived + gotchas

src/pneuma_lab/              contracts + implemented internal/offline research surfaces
    schemas/                   schema load helpers + validate.py (frame validation)
    psyche/                    PsycheUnderTest interface + ReferencePsyche (Level-3 mind
                               + Level-4 perturbation hooks) + ported pure math
    replay/                    ReplayHarness (+ intervention schedule) + JSONL IO + CLI
    interventions/             operations · perturbation · schedule · report · runner (Phase 2)
    evals/                     ConsciousnessEvidenceScorer (Level 0–4, honest refusal)
    demo.py                    `python -m pneuma_lab.demo` — regenerates the canonical
                               Level 3 vs Level 4 evidence suite under build/canonical/
    adapters/                  deterministic SWE-Gym/OpenHands dataset-to-trace adapters
    converters/                guarded PneumaTrainingExample conversion
    training/                  fail-closed run preflight; no positive authorization
    estimators/                offline advisory E1/E2 models; no runtime integration
    status.py                  validates and reports docs/project-status.json

fixtures/
    sample_run.jsonl           a failure-motif escalation timeline (input frames)
    interventions/             5 canonical Level-4 scenarios + restore-null + failing-hypothesis

tests/
    test_schema_loads.py       every schema exists, parses, and is a valid JSON Schema
    test_validate.py           frame validation helper
    test_psyche_math.py        ported manifold/drives/authority/hash math
    test_psyche_outputs.py     ReferencePsyche emits valid, bounded output frames
    test_replay_harness.py     end-to-end replay reaches Level 3, capped below 4
    test_evidence_scoring.py   memory-readback ablation (Level-2 proof) + conservatism
    test_determinism.py        same input ⇒ byte-identical outputs + hash chain
    test_intervention_operations.py   pure op math + deterministic noise
    test_perturbation.py       PerturbationSet + the ReferencePsyche hook points
    test_intervention_schedule.py     duration-window resolution + neutralized null
    test_intervention_report.py       signal extraction + expected-vs-observed deltas
    test_paired_replay.py      deterministic paired replay + 5 canonical scenarios
    test_level4_scoring.py     Level-4 gate: reached on pass, refused on absent/fail
    test_canonical_demo.py     canonical demo: valid summary, byte-determinism, L3/L4 buckets

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
python -m pneuma_lab.status --check  # canonical status + checkout coherence
python -m pytest tests/ -q          # schema + psyche + replay + evidence + determinism
python -m pneuma_lab.replay fixtures/sample_run.jsonl -o build/replay
```

Requires Python ≥ 3.11. The psyche math is standard-library only; `jsonschema` is
now a runtime dependency because the replay harness validates every input and
output frame (evaluation Layer A).

## Boundaries

- Pneuma Lab never imports from — nor is imported by — 9to5.
- No 9to5 production code, branch, or PR (#38) is modified by this project.
- Pneuma is not an operational 9to5 nervous system; every host integration edge
  beyond offline trace replay remains blocked.
- JSpace/J-lens work has no implementation, configured model access, or result.
- manager-data is **possible future operator-preference context only**, never the
  base mind and never overfit to. No data/secrets were copied.
