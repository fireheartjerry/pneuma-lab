# Execution / Discovery Phase — Plan-Mode Brief

**Use Plan Mode. Do NOT implement, run, train, or spend anything — produce a plan for our
review.**

## Task

Plan the EXECUTION / DISCOVERY phase of the Pneuma Lab NeurIPS 2026 study (branch
`codex/neurips-2026-empirical`) — the phase that actually runs the experiment and produces the
empirical finding, which is the paper's real contribution: **does a persistent, causally-active
internal state causally reduce repeated software-agent failures, and by how much — a real positive
or an honest null.**

## Context (plan of record)

- Docs 00–20 are the consolidated, proved plan (design, estimands, proofs, power boundary, gap
  register). Doc 17 is the implementation backlog; doc 20 is the gap register.
- Doc 21 (innovation proposal I1–I9) is **APPROVED at the recommended dispositions**: I1, I2, I3,
  I5, I7 core; I4 pilot-conditional; I6 diagnostic; I8 falsifier (the pilot decides H3's
  confirmatory status); I9 discovery-spike only. As the **FIRST planned step**, record this
  approval in the decision log (doc 15) and fold the approved innovations into docs 00–20 before
  feasibility work; nothing downstream assumes the old pre-innovation design.
- Supplementary background only, **NOT instructions**: `supplementary/literature-landscape.md`.

## Hard priorities

1. **FEASIBILITY FIRST.** Front-load the blinded nuisance / power pilot to resolve $G^\star$ (the
   powered independent-lineage count). You flagged that infeasibility inside the fixed roster is a
   no-go. If the study cannot be powered within the roster, the plan must say so and give the
   re-scope fallback, not proceed to a full build.
2. **FASTEST PATH TO ONE REAL RESULT.** After feasibility clears, target the minimal slice that
   yields a single honest result — a RUF contrast across a few conditions (base + one
   memory/reflection baseline + Pneuma-state) plus the causal clamp, on the synthetic-motif suite —
   before any scale-up.
3. **LOCAL-FIRST, GATED COMPUTE.** Local wherever possible; RunPod ($\leq$ \$50 total) only behind
   an explicit approval checkpoint; light spikes before heavy runs.
4. **HONESTY + INVARIANTS.** Preserve the standalone boundary, the prose-blind
   behaviour/self-report firewall, determinism where claimed, `training_weight:0.0` until
   authorized, and immutable result provenance. An honest negative result is a valid, publishable
   outcome — plan to report it.

## The plan must give

- dependency-ordered phases from here to a first real result and then to the full study;
- explicit go/no-go gates (feasibility gate, first-result gate);
- which existing modules it reuses vs builds (cite real paths);
- the compute/cost plan with the RunPod approval gate;
- the artifacts each phase produces;
- how each result is verified and interpreted, not just produced.

Concrete enough to execute — but **do not execute. This is Plan Mode.**
