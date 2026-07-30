# Task 8 Timing No-Go Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a fail-closed, power-ancestry-incompatible representation of the frozen P0 host-specific timing lower-bound no-go.

**Architecture:** A new closed JSON Schema and one isolated Python module own the record. The module validates bound immutable inputs, exact projection arithmetic, monotonic termination evidence, non-claim flags, canonical exclusive publication, and the continued absence of forbidden descendants.

**Tech Stack:** Python 3.12, Draft 2020-12 JSON Schema, pytest, canonical JSON/SHA-256, POSIX create-exclusive file IO.

---

### Task 1: Freeze the dedicated schema and negative contract

**Files:**
- Create: `schemas/resampling-timing-no-go.schema.json`
- Modify: `src/pneuma_lab/schemas/__init__.py`
- Create: `tests/resampling_null/test_timing_no_go.py`

- [ ] Write a focused schema test that requires record kind
  `resampling_timing_no_go`, outcome `timing_infeasible_lower_bound`, exact
  projection and termination structures, and all closed false claim flags.
- [ ] Run `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_timing_no_go.py tests/test_schema_loads.py -q` and confirm it fails because the schema/module does not exist.
- [ ] Add the closed Draft 2020-12 schema and register it only in
  `RESAMPLING_SCHEMA_FILES`.
- [ ] Run the same focused command and confirm the schema slice passes while
  production-module tests remain red.
- [ ] Commit the schema/test slice.

### Task 2: Implement construction and exclusive canonical creation

**Files:**
- Create: `src/pneuma_lab/resampling_null/timing_no_go.py`
- Modify: `tests/resampling_null/test_timing_no_go.py`

- [ ] Add red tests for exact authority/grid/topology bindings, Task-10
  execution versus Task-8 machinery ownership, strict `> 432` lower bound,
  monotonic sample consistency, all-false claims, no forbidden descendants,
  and duplicate exclusive creation.
- [ ] Run the focused test file and verify each new test fails for the missing
  behavior.
- [ ] Implement immutable input/evidence dataclasses, exact frozen arithmetic,
  bound-artifact byte/SHA checks, run/host binding checks, forbidden-descendant
  discovery, and canonical `O_EXCL` publication with file and directory fsync.
- [ ] Run the focused test file and confirm green.
- [ ] Commit the production slice.

### Task 3: Implement hostile verification

**Files:**
- Modify: `src/pneuma_lab/resampling_null/timing_no_go.py`
- Modify: `tests/resampling_null/test_timing_no_go.py`

- [ ] Add red mutation tests for record byte drift/noncanonical formatting,
  threshold equality, missing binding, altered grid/topology/authority bytes,
  false-to-true claim promotion, and a screen/verifier/shard/final/downstream
  artifact appearing after publication.
- [ ] Run the focused test file and verify expected failures.
- [ ] Implement verification that reloads canonical bytes, validates the schema,
  recomputes all identities/arithmetic, and rescans forbidden descendants on
  every call.
- [ ] Run the focused test file and confirm green.
- [ ] Commit the verification slice.

### Task 4: Record proposal-only reconciliation and hostile reviews

**Files:**
- Create: `docs/research/neurips-2026-workshop/35-task8-timing-no-go-temporary-handoff.md`

- [ ] Record exact implemented behavior, Task-10/Task-8 provenance distinction,
  no-claim boundary, exact E2E blockers, and proposed future edits to shared
  status/journal/live handoff without applying them.
- [ ] Run a bounded read-only Claude review using
  `claude --dangerously-skip-permissions` and record its task, model/cost receipt,
  output, and direct disposition in the temporary handoff.
- [ ] Run a bounded read-only Codex review using `codex --yolo` and record its
  task, model/token receipt, output, and direct disposition.
- [ ] Fix every directly verified critical/important finding through red-first
  tests, then rerun the focused gate.
- [ ] Commit the review/reconciliation slice.

### Task 5: Final verification and completion audit

**Files:**
- Inspect all Task-8 changed files.

- [ ] Run `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_timing_no_go.py tests/test_schema_loads.py -q`.
- [ ] Run `timeout 60s .venv/bin/python -m compileall -q src/pneuma_lab/resampling_null/timing_no_go.py`.
- [ ] Run `.venv/bin/python -m pneuma_lab.status --check`.
- [ ] Run `git diff --check`, inspect `git status --short`, and compare the full
  branch diff to the original requirements.
- [ ] Confirm no Task-9 module, CLI registration, shared status, execution
  journal, or live Tasks-6–10 handoff changed.
- [ ] Commit any final coherent corrections and report
  `implementation_complete; E2E_pending` with exact blockers and no scientific
  claim.
