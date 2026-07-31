# PLACEBO rebrand — reconciliation patch for shared surfaces

**Status:** APPLIED on 2026-07-31 under DL-160, after Phase B reached its
readiness audit (DL-159, EJ-20260731-phase-b-readiness-audit). Retained as the
record of what was changed and, in the final section, what was deliberately
left alone.

One deviation from the plan below: `docs/project-status.json` is validated by
`schemas/project-status.schema.json`, which sets `additionalProperties: false`,
so adding `public_naming` required an additive optional block in that schema.
The block constrains `internal_identifiers_unchanged` to `const: true` — a
rebrand that renamed identifiers would not be a rebrand, and the schema now
refuses to record one.

This branch (`codex/placebo-paper-review`) confined every edit to new
paper-facing and review-facing files. The shared scientific-authority surfaces
below were deliberately left untouched to avoid colliding with concurrent
Phase B work. This document is the explicit patch to apply later, in one
coherent commit, once Phase B is quiescent.

## Applying it

1. Confirm no Phase B work is in flight on the shared branch.
2. Apply the edits below in order; each is additive prose, not a rewrite.
3. Do **not** rename any package, module, schema `$id`, record kind, receipt
   field, artifact identity, or historical decision entry. The rebrand is a
   presentation layer only — see `01-terminology.md` §3.
4. Register the rebrand as a decision-log entry that states, in one sentence,
   that no internal identifier changed.

## Edits

### `docs/research/neurips-2026-workshop/00-README.md`

Add, after the first paragraph:

> The public-facing name for this methodology is **the PLACEBO Protocol**, and
> for the registered experiment **the PLACEBO Trial**
> (`docs/research/placebo-paper/01-terminology.md`). Internal identifiers —
> the `resampling_null` package, `resampling-*` schemas and record kinds,
> receipts, and artifact identities — are unchanged and remain authoritative.

### `docs/research/neurips-2026-workshop/15-decision-log.md`

Append one entry:

> **DL-NNN — PLACEBO public rebrand.** The submission-primary study is branded
> PLACEBO (Preregistered, Label-blind, Arm-controlled, Causal Evaluation of
> Behavioral Outcomes) for all paper-facing material. "The PLACEBO Protocol"
> names the methodology; "the PLACEBO Trial" names the registered experiment.
> No package, schema, record kind, receipt, artifact identity, or historical
> decision entry is renamed. The rebrand carries no scientific claim; in
> particular the paper does not claim that placebo-controlled feedback
> evaluation is novel, and candidate novelty is confined to the seven-part
> conjunction in `docs/research/placebo-paper/01-terminology.md` §4.

### `docs/project-status.json`

Add a `public_naming` block alongside the existing status fields; do not alter
any existing status value:

```json
"public_naming": {
    "protocol": "The PLACEBO Protocol",
    "trial": "The PLACEBO Trial",
    "internal_identifiers_unchanged": true,
    "terminology_doc": "docs/research/placebo-paper/01-terminology.md"
}
```

### `docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md`

Add to the header block:

> Paper-facing artifacts for this lineage live on the paper/review branch:
> `paper/placebo_protocol.tex`, `src/pneuma_lab/placebo_paper/`, and
> `src/pneuma_lab/adversarial_review/`. Task 10 release preparation must
> produce a package that `pneuma_lab.placebo_paper.admit` accepts; see
> `docs/research/placebo-paper/00-result-to-paper-pipeline.md` §1 for the exact
> field contract.

### `docs/research/neurips-2026-workshop/36-step4a-to-aws-credit-launch-roadmap.md`

Insert Step 14 detail:

> **Step 14 — hostile review.** Run campaign 1 of the adversarial rejection
> system (`stage_1_pre_launch`) after Steps 4–13 and **before** Step 4B or any
> GPU execution. Procedure and blocking rules:
> `docs/research/placebo-review/00-operating-procedure.md`. A
> `no_blocking_findings` disposition is not launch authority; launch authority
> remains in the decision log and the spend gate.

### `docs/research/neurips-2026-workshop/37-phase-b-4-13-implementation-plan.md`

Add to the Task 10 section:

> Task 10 release preparation must emit a sealed package satisfying the
> admission contract in `src/pneuma_lab/placebo_paper/package.py`: kind
> `resampling_task10_sealed`, lineage `canonical_confirmation`, sealed, a
> recursively verified artifact root, a completed unblind ceremony, the nine
> required receipts, a taxonomy verdict, and an emitted `numbers` object whose
> keys match `render.PRIMARY_ROWS`, `render.RESOLUTION_ROWS`, and
> `render.ENVIRONMENT_ROWS`.

### `docs/research/neurips-2026-workshop/33-execution-journal.md`

Append one entry recording the branch, its commits, and the fact that no
scientific artifact, cloud resource, or spend was touched.

### `CLAUDE.md`

Add to the "Current NeurIPS Track" section:

> The public methodology name is the PLACEBO Protocol and the registered
> experiment is the PLACEBO Trial. Internal `resampling_null` identifiers are
> unchanged. Paper materials are `paper/placebo_protocol.tex` and
> `src/pneuma_lab/placebo_paper/`; the pre-launch hostile review is
> `src/pneuma_lab/adversarial_review/` and runs at Step 14.

## Surfaces intentionally NOT changed

`docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md`,
`38-experiment-design-freeze.md`, `39-external-input-lock.md`,
`40-aws-architecture.md`, and
`docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md`.

These are frozen or authority-bearing records. A rebrand is not a reason to
touch a design freeze, and a renamed input lock is a changed input lock.
