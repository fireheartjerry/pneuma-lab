# Pneuma Lab → NeurIPS 2026 Workshop — Technical Blueprint

**Status:** planning package, complete. **Planning only** — nothing here
authorizes implementation, training, data conversion, or experiments. Every
downstream document reaffirms `training_weight: 0.0` / `not_authorized`.

This package converts Pneuma Lab from a broad artificial-psyche research system
into a rigorous, falsifiable empirical study for a NeurIPS 2026 workshop
(primary target: **IAB — Interpreting Agent Behavior**, deadline **2026-08-29**,
9pp long / 4pp short, non-archival).

## The one-sentence claim

We test whether giving a software-engineering agent a **persistent, causally
active internal state** helps it notice its own recurring failure patterns,
avoid repeating them, and accurately explain why its behaviour changed —
measured against no-memory, retrieved-memory, and written-reflection agents
identical in every other respect, with the causal contribution isolated by
clamp/ablation interventions.

## What the audit established (see `01`)

The instrument is publication-grade; the evidence is synthetic-only. The paired
control/treated/null causal runner, the prose-blind behaviour/self-report
firewall, the scar-memory loop, leakage-safe splits, and determinism are all
real and tested — but only on a hand-built deterministic toy mind over ~6
fixtures. **Three load-bearing pieces are missing and constitute the build:**
(1) a real failure detector, (2) a state→action decision head, (3) a real-data
outcome experiment. Two on-disk trajectory corpora (Open-SWE-Traces, SWE-Gym
Sampled) supply real recurring-failure structure.

## Reading order

| #   | Document                                 | What it fixes                                                                                       |
| --- | ---------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 01  | `01-current-state-audit.md`              | Honest maturity map of every subsystem (from 15 code-tracing audits)                                |
| 02  | `02-research-thesis.md`                  | **Canonical.** Research question, H1–H5, claim tiers, falsification, §8 Locked Design Constants     |
| 03  | `03-related-work-positioning.md`         | Five clusters, closest neighbors (SWE-Exp, Reflexion, ExpeL, A-MEM, MemGPT), reviewer rebuttals     |
| 04  | `04-benchmark-specification.md`          | Dual suite (synthetic motif + real repo), 12-motif taxonomy, splits, leakage, trajectory enrichment |
| 05  | `05-agent-condition-specification.md`    | Six conditions, fairness matrix, budget equalization                                                |
| 06  | `06-internal-state-specification.md`     | The four state variables + derived `L` + decision head, exact update rules                          |
| 07  | `07-experimental-protocol.md`            | End-to-end runnable procedure for E1–E5 + ablations                                                 |
| 08  | `08-metrics-and-statistics.md`           | RUF + 15 secondary metrics, paired bootstrap, BH-FDR, E-0 confound controls                         |
| 09  | `09-intervention-and-causal-validity.md` | Nine arms + the statistical causal path replacing byte-equality                                     |
| 10  | `10-anti-gaming-specification.md`        | Threat model, 15 controls, prose-blind enforcement                                                  |
| 11  | `11-ablation-matrix.md`                  | 19 ablations + minimal 6 for the paper                                                              |
| 12  | `12-implementation-plan.md`              | **Executable.** 9 workstreams, 39 dependency-ordered tasks at file/class/test granularity           |
| 13  | `13-publication-plan.md`                 | IAB target, 9-page outline, figures, artifacts, ethics                                              |
| 14  | `14-risk-register.md`                    | 24 ranked risks with mitigation + contingency                                                       |
| 15  | `15-decision-log.md`                     | DL-01…DL-15 with rejected alternatives                                                              |

**Newcomer path:** 02 → 01 → 06 → 09 → 12. **Reviewer path:** 02 → 03 → 08 → 14.

## Claim → evidence map

| Claim tier     | Hypothesis | Experiment                       | Metric                               | Doc    |
| -------------- | ---------- | -------------------------------- | ------------------------------------ | ------ |
| Behavioural    | H1         | E1 (six conditions, both suites) | RUF (paired, CI)                     | 07, 08 |
| Causal         | H2         | E2 (clamp/ablation arms)         | treated−null contrast, dose-response | 09     |
| Generalization | H4         | E3 (surface/repo/motif holdout)  | RUF transfer retention               | 04, 08 |
| Introspection  | H3         | E4 (four report conditions)      | self-report faithfulness             | 06, 10 |
| Discrimination | H5         | E5 (counterfactual tasks)        | false-avoidance, success             | 08, 10 |
| Phenomenal     | —          | **not made**                     | —                                    | 02 §5  |

## Critical path (from `12`)

`WS-A` (trajectory enrichment + failure detector) → `WS-B` (benchmark) →
`WS-F` (statistical causal harness) → `WS-G` (metrics + prose-blind evaluator) →
`WS-I` (orchestration + official-run gate), with `WS-C` (live driver) → `WS-D`
(conditions) → `WS-E` (state + decision head) feeding in. The failure detector
(WS-A) and the statistical null path (WS-F) are the two highest-risk unlocks
(risks T-02, T-01 in `14`).

## Provenance

Built from 15 parallel read-only code-tracing audits of the repository (working
notes in the session scratchpad under `audit/`) plus a verified related-work and
on-disk-data survey. Design constants were locked before the specification
documents were written; deviations, if any, are recorded in `15`.
