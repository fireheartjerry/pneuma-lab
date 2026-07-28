# Program State + Glow-Up Mandate

This document has two parts, deliberately different in register. **Part A** is
an exhaustive, technical account of exactly where this research program stands
today — read it as ground truth, not as a to-do list. **Part B** is the actual
ask, and it is intentionally short, high-level, and non-technical: every
technical decision from here — thesis framing, experiment design, models,
methods, statistics, paper structure — is left to you.

---

## Part A — Where this program stands today (context, not instructions)

### A.1 Repo and current state

Pneuma Lab, `C:\pneuma-lab`, branch `codex/neurips-2026-empirical`. That branch
was just consolidated (merged in a divergent gauge-study line, committed
outstanding WIP) and the full suite passes: 1287 tests passed, 8 skipped, 0
failed. Repo conventions: standalone (no imports from or writes back into
`C:\9to5`), 4-space indentation, JSON Schema Draft 2020-12 for `schemas/`, no
BOM/comments in schema files.

### A.2 The ground-zero idea: the placebo / causal-effect program

The root concept this whole effort grew from, and the one thing that should
survive whatever comes next: testing whether an intervention on an agent
(a prompt payload, a piece of advice, a memory injection) has a **real causal
effect**, versus the agent just landing on a different outcome because greedy/
low-temperature decoding reroutes generation down a different path the moment
any token in the prompt changes. The design pattern is a three-arm comparison
— `real` (actual payload), `placebo` (inert payload, matched surface form),
`none` (nothing) — plus a fourth control, `RESAMPLE` (no payload change, one
more independent attempt at matched decoding and matched compute), so the
"just re-sampling" effect size is measured directly instead of assumed zero.
This lives in:

- `docs/research/neurips-2026-workshop/24-placebo-program.md` — the umbrella
  design.
- `docs/research/neurips-2026-workshop/23-placebo-memory-design.md` — placebo
  applied to memory/scar injection.
- `docs/research/neurips-2026-workshop/25-placebo-selfreport-design.md` — placebo
  applied to self-reported confidence/Brier-scored outcomes; the `S RESAMPLE`
  arm is specified around line 170; a five-week execution cadence (pilot →
  confirmatory batch A → confirmatory batch B → draft/red-team/submit) is
  specified at the end of that file.

### A.3 What actually got built and measured so far: the G1 gauge-card MSA paper

A concrete instantiation of "is an elicited number a real measurement or a
noisy instrument" was built out fully at local scale and is a complete,
pre-registered, results-locked paper:

- Paper draft: `docs/research/gauge-paper/paper.md`.
- Pre-registration (committed before any model call): `docs/research/experiments/g1-gauge-preregistration.md`, commit `c42507a`.
- Results of record: `docs/research/experiments/g1-gauge-results.md`.
- Implementation: `src/pneuma_lab/gauge/` (card, cube, elicit, remedies, stats,
  anova, resolution, theory, bank, synthetic, placebo modules), schema at
  `schemas/gauge-card.schema.json`.

**Thesis as currently written:** elicited LLM metrics (self-reported
confidence, LLM-as-judge scores) are validated for accuracy (ECE, Brier,
AUROC) but never for reliability. Applying measurement-system analysis (MSA —
%GRR, ICC, `ndc`, discrimination index `D`) to 13,632 elicitations across 48
items, 6 models, multiple wordings/scales/temperatures/precisions finds the
elicited-confidence channel resolves `ndc = 1` distinguishable category (can't
reliably rank two items) despite AUROC 0.906 in aggregate — a reproducibility
defect (sensitivity to wording), not a repeatability one (sensitivity to
sampling). Post-hoc calibration is proven incapable of fixing this. Cross-model
spread (`ndc` 0–3 across six models) dwarfs cross-precision spread (F16 vs
Q4_K_M differs by 0.006). Two pre-registered hypotheses were falsified and
reported as such. §9 (limitations) and §10 (`⟦CLOUD-EXP-1⟧`–`⟦CLOUD-EXP-8⟧`) of
the paper already lay out eight pre-specified, not-yet-run cloud-scale
extensions (frontier-model replication, judge-benchmark generalization, real
verified-benchmark items, logit-based-vs-verbalized elicitation head-to-head,
human-rater reference, domain threshold calibration, prompt-population
sampling, provider/version drift) with priority already implied by the paper's
own text ("EXP-1 and EXP-2 must land before the central claim can be stated
for the field").

**This thesis is not locked.** It is one concrete answer to the ground-zero
placebo/causal-effect question (A.2), built to a high bar of rigor, and it is
fully available to reuse, extend, replace, or fold into something bigger.

### A.4 External review already received (signal, not instructions)

A domain-knowledgeable outside reader gave feedback on an earlier description
of this work, already partly reflected in A.2/A.3's design:

- The abstract's novelty claim, as stated to them, was flagged as overstated —
  they still judge the underlying idea novel enough, just not the specific
  framing sentence used.
- The self-report elicitation setup they were shown (`Qwen2.5-Coder-1.5B-Instruct`,
  4-bit, greedy decoding) was flagged as producing compressed, unreliable
  verbalized output (clustering 80–95 regardless of correctness) — they
  recommended a materially stronger model (they suggested Qwen3.5) and
  suggested eliciting probability mass from raw next-token logits (binary
  yes/no framing) rather than parsing a verbalized number.
  they suggested harder ground-truth benchmarks (LiveCodeBench, a SWE-bench
  Verified subset) to compensate for a stronger model being less discriminable
  on toy items.
  they independently re-derived the decoding-path confound that motivated the
  `RESAMPLE` arm in A.2.

### A.5 Resources available

- Confirmed pending redemption via the YC deals page (checked 2026-07-24, per
  `docs/research/neurips-2026-workshop/15-decision-log.md`): AWS $10,000,
  Microsoft Azure $10,000 (GPU compute), OpenAI $2,500, Anthropic $500
  (frontier API) — roughly $23,000 total.
- Full computer-use / browser-use access via an authenticated Chrome session,
  and any plugins/tools available to you.
- Target venue: "Who Verifies the Agents? — Toward Reliable Agent Development"
  @ NeurIPS 2026, 4–9 pages, double-blind, non-archival, **deadline 2026-08-29
  AoE** (fallback IAB @ NeurIPS 2026). Today is 2026-07-28.

---

## Part B — The ask

Take Part A as the current state of the art for this program, not as a brief
to fulfill literally. Give this program a full, bottom-up, advanced glow-up:
make it as novel, powerful, and professionally compelling as you're capable of
making it, using whatever technical approach, models, experiments, and scale
you judge best, with full autonomy over the budget and access in A.5, by the
2026-08-29 deadline.

The one thing that should survive intact is the ground-zero idea in A.2 — real
causal effect versus resampling noise. Everything else (thesis, framing,
experiment design, methods, statistics, structure) is yours to keep, sharpen,
or replace. Decide the path. Report back what you built and why.
