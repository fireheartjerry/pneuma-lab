# Placebo Controls for Agent Augmentation

**Target:** Who Verifies the Agents? — Toward Reliable Agent Development @ NeurIPS 2026.
4–9 pages, double-blind, non-archival, **2026-08-29 AoE**. Fallback: IAB @ NeurIPS 2026.

---

## The claim

Agent-memory systems are evaluated by comparing memory-on against memory-removed. That
contrast cannot separate what the agent _remembered_ from the fact that it received more
context and an extra model call. We run the missing control — a memory system that operates
normally but is populated with **another agent's memories** — and decompose the reported
gain into apparatus, plausibility, and content.

$$
\underbrace{\text{Real} - \text{None}}_{\text{reported gain}}
= \underbrace{(\text{Real} - \text{P}_{\text{match}})}_{\text{content}}
+ \underbrace{(\text{P}_{\text{match}} - \text{P}_{\text{rand}})}_{\text{plausibility}}
+ \underbrace{(\text{P}_{\text{rand}} - \text{None})}_{\text{apparatus}}
$$

An audit of ten agent-memory systems found **0 of 10** run any placebo-equivalent control,
**10 of 10** report uncertainty over the wrong variance component, and **0 of 10**
pre-specify a decision rule.

## Documents

| Doc                                     | Contents                                                                                                                                                   |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `24-placebo-program.md`                 | **Start here.** The general method: apparatus/content decomposition, placebo construction, validity gates, and the seven augmentation types it applies to. |
| `23-placebo-memory-design.md`           | The first study. Four arms, LongMemEval, sample size, analysis plan, execution schedule.                                                                   |
| `22-audit-rubric.md`                    | The frozen nine-field audit rubric. Quote-backed cells, no inter-rater coefficient, mandatory self-inclusion.                                              |
| `21-pivot-and-claim-retirement.md`      | What this project used to claim, why five novelty claims were retired, and the per-citation verification record.                                           |
| `15-decision-log.md`                    | Append-only. DL-46/47/48 record the pivot.                                                                                                                 |
| `supplementary/literature-landscape.md` | Background reading. Not instructions.                                                                                                                      |
| `archive/protocol-v2/`                  | The superseded seven-arm causal study. Retained for provenance. **Do not implement from it.**                                                              |

## Status

- **Audit:** 10 seed systems coded. Snowball to $N \le 25$ outstanding. Four F2
  adjudications pending.
- **Statistics:** `src/pneuma_lab/statistics/power.py` (sealed P0 gate, no-go) and
  `correlation_surface.py` (dependence bracket). Simulator validated against the closed
  form at $\rho = 0$ across 31,536 comparisons, zero failures.
- **Experiment:** designed, not implemented. Design freeze 2026-07-28.

## Invariants

- Pneuma Lab stays standalone. No imports from `C:\9to5`.
- `training_weight: 0.0`. No weight training in this program.
- No claim about consciousness, sentience, or phenomenal experience. This is measurement.
- We are included in our own audit, under the identical rubric, and we fail it too.
