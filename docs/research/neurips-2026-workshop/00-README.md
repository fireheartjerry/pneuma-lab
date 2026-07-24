# Someone Else's Regret

**Placebo controls for agent augmentation — and what they do to an agent's self-report.**

**Target:** Who Verifies the Agents? — Toward Reliable Agent Development @ NeurIPS 2026.
4–9 pages, double-blind, non-archival, **2026-08-29 AoE**. Fallback: IAB @ NeurIPS 2026.

---

## In one paragraph

When an AI fails a task, a common trick is to have it write a short note about what went
wrong and then try again. It usually does better, and everyone credits the note. But the
second try also comes with more text in front of it, an extra thinking step, and a reminder
that it just failed. So we keep all of that and swap only the note — we hand it a note
written by the same AI that was never allowed to see the actual problem, matched to the same
length and the same shape. Then we check something nobody checks: **does the AI still know
whether it fixed the bug?** If a fake note leaves it just as likely to succeed but worse at
telling whether it did, then anyone trusting an AI's own report of how it is doing is
trusting the ritual, not the thinking.

## The decomposition

$$
\Delta_C = \text{Real} - \text{Placebo}, \qquad
\Delta_A = \text{Placebo} - \text{None}, \qquad
\Delta_T = \text{Real} - \text{None}
$$

Reported on task success **and** on the agent's stated confidence and its decision to
escalate to a verifier. The three differences are primary; the ratio between them is a gated
descriptive secondary, because it is the _proportion mediated_ of mediation analysis and
inherits its pathology.

## Documents

| Doc                                     | Contents                                                                                                         |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `25-placebo-selfreport-design.md`       | **The primary study.** Eleven arms, EvalPlus, parity gates, estimands, hard gate, schedule. Start here.          |
| `24-placebo-program.md`                 | The general method and the seven augmentation types it transfers to.                                             |
| `23-placebo-memory-design.md`           | Deferred instance — episodic memory on LongMemEval. Not the primary study.                                       |
| `22-audit-rubric.md`                    | The frozen nine-field audit rubric. Quote-backed cells, no inter-rater coefficient, mandatory self-inclusion.    |
| `21-pivot-and-claim-retirement.md`      | What this project used to claim, why five novelty claims were retired, and the per-citation verification record. |
| `15-decision-log.md`                    | Append-only. DL-46 through DL-49 record the pivot.                                                               |
| `supplementary/literature-landscape.md` | Background. Not instructions.                                                                                    |
| `archive/protocol-v2/`                  | The superseded seven-arm causal study. Provenance only. **Do not implement from it.**                            |

## Position against the nearest work

- **Mehmet Iscan**, arXiv:2606.06454 / 2606.31511 / 2607.12962 — owns preregistered,
  derangement-assigned, placebo-controlled **self-repair on EvalPlus**. We cite all three as
  motivation and extend their nulls; we do **not** claim the repair-rate result as discovery.
  None of the three measures self-report. That is our cell.
- **Stechly et al.**, arXiv:2310.12397 — corrupts critique _correctness_ on planning puzzles.
  We swap in _uncorrupted content about a different problem_ with the apparatus held fixed.
- **Min et al.** 2022 — in-context demonstrations survive random labels. Ours is a
  post-failure feedback channel, and we measure self-report.

## Status

- **Audit:** 10 systems coded, quote-backed. 0/10 run a placebo-equivalent control, 10/10
  report uncertainty over the wrong variance component, 0/10 pre-specify a decision rule.
- **Statistics:** power simulator validated against the closed form across 31,536
  comparisons, zero failures.
- **Experiment:** designed, not built. First five build tasks are in `25`.

## Invariants

- Standalone. No imports from `C:\9to5`. `training_weight: 0.0`.
- **No LLM judge anywhere** — not in primary, secondary, or manipulation checks. A judge-free
  paper cannot contain a judge.
- No claim about consciousness, sentience, or phenomenal experience.
- We are in our own audit table, under the identical rubric, and we fail it too.
