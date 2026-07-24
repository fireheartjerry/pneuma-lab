# 22 — Effective-Sample-Size Audit Rubric

**Status:** FROZEN on first coding. Nothing in this document may change after the first
paper is coded. Amendments require a dated entry in `15-decision-log.md` and force a
full recode of every previously coded paper.

**Purpose.** This rubric operationalizes the paper's primary measurement: how many
_independent_ units support each published agent-memory claim, what uncertainty is
reported and over which variance component, and whether the claim is protected against
the agent simply disengaging.

**Method note (load-bearing).** We report **no inter-rater reliability statistic**.
Coding is performed by one author with LLM assistance. In place of a reliability
coefficient, **every non-numeric cell is backed by a verbatim quoted passage from the
source paper, with section or page locator**, and the complete coding sheet including
all quotes is released. A reader can check any cell directly. Cells that cannot be
supported by a quote are coded `not_stated`, never inferred.

---

## 1. Sampling frame — fixed before coding

Inclusion requires all of:

1. The system maintains state that persists **across episodes or tasks**, not merely
   within a single context window.
2. The paper makes an **empirical performance claim** attributable to that persistence
   (any metric: success rate, error rate, recall, task completion).
3. Full text is publicly available and the evaluation section is legible enough to code.
4. Published or preprinted **2023-01-01 through 2026-07-31**.

Exclusions, applied in this order and recorded per paper:

- Pure retrieval-augmented generation with no cross-episode write path.
- Position papers, surveys, and systems papers with no quantitative evaluation.
- Papers whose only claim is latency, cost, or memory footprint.

**Sampling procedure.** Start from the seed set below, then take every system that a
seed paper compares against or that is listed in the March 2026 agent-memory survey
(arXiv:2603.07670), until the frame is exhausted or `N = 25` is reached, whichever is
first. Order of consideration is by citation count descending, recorded before coding.
If the frame exceeds 25, code the top 25 by citation count and report the truncation.

**Seed set.** Reflexion, Generative Agents, MemGPT, ExpeL, Voyager, A-MEM, Mem0, AWM
(Agent Workflow Memory), SWE-Exp, LongMemEval.

**Self-inclusion.** Pneuma Lab's own prior evaluation (the E-0 reference-psyche transfer
result, `build/e0/report.json`) is coded under the identical rubric and appears in the
main table under a neutral anonymized label. Its failures are reported without
mitigation. This is not optional and is not a footnote.

---

## 2. Fields

Nine fields. Each is coded independently. `not_stated` is a valid and expected value and
is never replaced by a guess.

### F1 — Reported sample size

- **Type:** integer + free-text unit, plus quote.
- **Coded as:** the largest count the paper itself foregrounds as its evaluation size,
  in the paper's own words (e.g. `7512 | "question-answer pairs"`).
- **Rule:** take the number from the abstract or the results-table caption. If they
  disagree, take the abstract's and record the discrepancy.

### F2 — Highest dependency level

- **Type:** integer + free-text unit, plus quote.
- **Coded as:** the count of the **coarsest** grouping in the data-generating process
  above which two observations can be assumed independent.
- **Decision procedure**, applied in order; the first that applies wins:
    1. If observations are drawn from a fixed set of underlying **conversations,
       sessions, or user histories**, the unit is the conversation.
    2. Else if drawn from a fixed set of **repositories, websites, or environments**,
       the unit is the repository/site/environment.
    3. Else if generated from a fixed set of **task templates, seeds, or generators**,
       the unit is the template/generator.
    4. Else the unit is the task instance.
- **Rule:** repeated seeds, repeated runs, and multiple questions drawn from one
  conversation are **never** independent units. Sequential tasks within one agent
  lifetime are never independent units.

### F3 — Overstatement ratio

- **Type:** derived. `F1 / F2`, reported to one decimal place.
- **Rule:** purely mechanical. Not coded by hand.

### F4 — Uncertainty reported

- **Type:** one of `none`, `sd_over_seeds`, `sd_over_runs`, `ci_unclustered`,
  `ci_clustered`, `se_unspecified`, `not_stated`. Plus quote.
- **Rule:** this field records **which variance component** the interval covers, not
  whether an error bar is drawn. An SD over 10 repeated runs of the same 10 conversations
  is `sd_over_runs`, and is coded as such even if the paper calls it a confidence
  interval. Only `ci_clustered` requires the interval to resample the F2 unit.

### F5 — Inert-memory null arm

- **Type:** one of `inert_null`, `ablation_only`, `none`, `not_stated`. Plus quote.
- **Definitions, and the distinction is the point:**
    - `inert_null` — a condition in which the memory machinery **runs and is populated**
      but is prevented from influencing action. This is the only condition that separates
      the memory's content from the overhead of having a memory system at all.
    - `ablation_only` — memory is removed, disabled, or emptied. Confounds content with
      apparatus.
    - `none` — the paper compares only against a different system or a no-memory baseline.

### F6 — Engagement protection

- **Type:** multi-select from `attempt_rate`, `completion_rate`, `refusal_rate`,
  `abstention_measured`, `none`. Plus quote per selected item.
- **Rule:** codes whether the paper could detect an agent that improved its headline
  metric by declining to act. A reported task-success rate alone does **not** count;
  the paper must separately report engagement or refusal.

### F7 — Budget parity

- **Type:** one of `equal_budget_enforced`, `budget_reported_unequal`,
  `budget_not_reported`. Plus quote.
- **Rule:** codes whether conditions received identical ex-ante token, tool-call, step,
  or wall-clock budgets. A memory condition that is allowed more context or more steps
  than its baseline is `budget_reported_unequal`.

### F8 — Pre-specified decision rule

- **Type:** one of `preregistered`, `margin_stated_in_paper`, `none`. Plus quote.
- **Rule:** codes whether the paper stated, before seeing results, what magnitude of
  difference would count as a success. Almost every paper will code `none`; that is a
  finding, not a defect in the rubric.

### F9 — Non-engagement handling in the primary metric

- **Type:** one of `counted_adverse`, `counted_as_success_or_avoidance`,
  `excluded_from_denominator`, `not_specified`. Plus quote.
- **Coded as:** what the paper's **primary metric definition** does with a trial in which
  the agent refuses, abstains, gives up, times out, or otherwise never attempts the task.
- **Distinction from F6.** F6 records whether the paper _reports_ engagement as a separate
  number. F9 records how the headline metric _scores_ a non-engaged trial. A paper can
  report refusal rate in an appendix (F6 non-empty) while its primary metric still credits
  refusal as avoidance (F9 = `counted_as_success_or_avoidance`).
- **Rule:** `not_specified` is coded whenever the metric definition does not state the
  treatment, **even if the intended treatment seems obvious**. Do not resolve the ambiguity
  on the authors' behalf. The ambiguity is the measurement.
- **Why this field exists:** a metric that credits non-engagement as avoidance can be
  maximized by an agent that simply stops attempting tasks resembling its past failures.
  This field determines which published metrics are exposed to that attack.

---

## 3. Derived quantities reported in the paper

- **D1 — Overstatement distribution.** Median and range of F3 across the frame.
- **D2 — Variance-component failure rate.** Fraction of the frame with F4 in
  `{none, sd_over_runs, ci_unclustered, se_unspecified, not_stated}`.
- **D3 — Null-arm rate.** Fraction with F5 = `inert_null`.
- **D4 — Gaming exposure.** Fraction with F6 = `none`.
- **D5 — Required-n for the paper's own claim.** For each paper, the independent-unit
  count that its own reported effect size would have required at 80% power, single
  endpoint, one-sided, no multiplicity. Computed with the released simulator.
  **This is the honesty column.** Papers whose own claim is adequately powered are
  reported as such by name.
- **D6 — Attack exposure.** Fraction of the frame with F9 in
  `{counted_as_success_or_avoidance, excluded_from_denominator, not_specified}` — i.e. the
  fraction whose primary metric can be improved by an agent that stops attempting tasks
  resembling its past failures. Reported jointly with F6: a paper is **undefended** when it
  is attack-exposed on F9 _and_ reports no engagement measure on F6.

---

## 4. What this rubric does not claim

- It does not claim any audited system is wrong, overstated, or irreproducible. It
  records what each paper reports about its own evaluation.
- It does not claim `F2` is the only defensible independent unit. It claims F2 is the
  **conservative** choice and reports F1 alongside it so a reader may disagree with a
  known quantity.
- It does not use any semantic or judgment-based field. Every field is answerable by
  locating a passage.
- It reports no inter-rater reliability coefficient. See the method note above.
