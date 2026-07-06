# Pneuma Lab — Vision

## What this is

**Pneuma Lab** is a standalone research project for _machine psyche_: software-
engineering cognition, continuous affect, instinct, scar-tissue memory, self-
modeling, authority pressure, and consciousness-relevant evaluation.

It is the **external research/evaluation harness** for the Human-Nature / Psyche
architecture that was prototyped inside the 9to5 autonomous engineering agent. In
9to5, the psyche is entangled with a production control loop; Pneuma Lab lifts the
_ideas and contracts_ out into a clean environment where they can be defined,
replayed, perturbed, and **audited** — without a production agent's constraints and
without the risk of a research probe changing a real run.

The name — _pneuma_, breath/spirit — is a deliberate, honest overclaim held in
tension with a conservative evidence posture: we investigate interiority
aggressively and claim it conservatively.

## Why it exists (the "know-act gap")

The 2026 literature named the exact bug the 9to5 psyche was built to fix: LLM
agents _know when they know_ but _do not act on it_ — confidence predicts
correctness, yet the model does not adapt effort, verification, or abstention to
its own internal signal. A psyche is only worth building if it **closes that gap**:
if internal state actually, measurably regulates behavior.

The failure mode on the other side is just as real: a psyche that writes beautiful
introspective prose while changing nothing (or worse, optimizing to _look_
coherent) is, in the operator's phrase, "a clever dashboard with feelings pinned to
it like stickers on a laptop." Pneuma Lab exists to tell those two apart with
evidence.

## First principles

1. **Continuous affect is the substrate, not the UI.** Interior state is a
    continuous manifold with inertia, decay, and personality-conditioned attractors.
    Emotion _labels_ are only projections over it — never primitive switches.
2. **Instinct is algorithmic, not narrated.** Fast pattern-matching over a live
    run-event stream, backed by a durable graph of failure motifs and recoveries —
    real machinery (Aho-Corasick/KMP/graph algorithms), not an LLM advisory.
3. **Authority is earned, ceilinged, and revocable.** Any influence on behavior is
    the `min` of five independent ceilings. The verifier's verdict is sacrosanct.
4. **The operator is constitutional, not a backdoor.** The operator sets values and
    ceilings but can never falsify local truth (verifier verdicts, competence,
    calibration) or bypass safety.
5. **Show receipts.** Every control-relevant claim is tied to logged internal
    quantities and a causal trace. Self-report is never ground truth.
6. **Evaluate by intervention, not by vibe.** The load-bearing test is causal:
    perturb an internal state, predict the bounded downstream change, and check it.

## What Pneuma Lab is NOT (this pass)

- Not a runtime. There is no live psyche loop here yet.
- Not an ML training project. No models are trained or fine-tuned.
- Not wired into 9to5. Pneuma Lab never imports from, or is imported by, 9to5.
- Not a consciousness _claim_. See `consciousness-levels.md`.

## The shape of the lab (target)

```
recorded run frames ─┐
    (WorldFrame,        │      ┌─────────────┐      output frames ──┐
    AgentTraceFrame,   ├──►   │   psyche    │  ──► (PsycheState,    │   ┌──────────┐
    MemoryFrame,       │      │  under test │      Instinct,        ├─► │  evals   │
    GovernanceFrame)   │      └─────────────┘      Pressure,        │   │ + scoring│
InterventionFrame ───┘         ▲    │            Authority,       │   └──────────┘
    (perturbations)               │    │            CausalTrace,     │        │
                                │    ▼            SelfReport)  ─────┘        ▼
                            replay harness      ── every output carries    ConsciousnessEvidenceFrame
                            (deterministic)        a CausalTrace ("receipts")  (evidence-graded, audited)
```

The **contracts** (the `schemas/` directory + `io-contract.md`) are the stable
core. The replay harness, adapters, and evals are built on top in later phases.

## North star

To determine — with evidence, honestly graded — whether increasingly integrated,
persistent, valenced, self-modeling, causally active, and externally auditable
machine states justify progressively stronger claims about machine interiority
over time. Aggressively investigated; conservatively claimed.
