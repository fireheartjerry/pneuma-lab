# Task 8 timing no-go temporary reconciliation handoff

**Status:** Task-8-specific temporary handoff; proposal-only for shared
reconciliation after Task 9 lands

**Branch:** `codex/task8-timing-no-go`

**Scope:** timing-admission/no-go implementation only

This file does not amend `docs/project-status.json`, the append-only execution
journal, or the live Tasks-6–10 handoff. Those shared surfaces remain untouched
by explicit instruction.

## Implemented boundary

The branch adds:

- `schemas/resampling-timing-no-go.schema.json`, a closed
  `resampling_timing_no_go` contract whose only outcome is
  `timing_infeasible_lower_bound`;
- `pneuma_lab.resampling_null.timing_no_go`, a separate create/verify module
  that does not import the power module, emit an ArtifactRef, register a CLI
  route, or participate in power-final ancestry;
- focused hostile tests under
  `tests/resampling_null/test_timing_no_go.py`.

The record binds the exact ArtifactRefs for the study manifest, synthetic power
authority, frozen grid, frozen screen topology, and termination evidence. It
also binds the physical run-root identity, current host identity, exact
2,916-cell/64-shard topology facts, the total-work formula, 200-to-20,000 draw
ratio, 100x multiplier, 43,200-second cap, and strict 432-second admissible
probe threshold.

Elapsed time is accepted only as a conservative integer lower bound backed by
consistent `time.monotonic_ns` start/observation readings. Equality at 432
seconds is rejected. Projection uses exact integer multiplication, not
floating-point arithmetic.

Creation is canonical and exclusive at
`timing-admission/task8-timing-no-go.json`. It shares the production screen
lock, uses descriptor-rooted `O_NOFOLLOW|O_EXCL` publication, fsyncs the file,
new directory entry, and parent root, and does not unlink a concurrently
substituted pathname on failed-write cleanup. Verification requires canonical
bytes, reloads every binding, recomputes all arithmetic, and rescans the closed
run-root namespace. Any later screen, timing verifier, shard, final, analysis,
schedule, or other non-source descendant invalidates verification, including
malformed bytes and non-JSON filenames.

Every claim/status flag is closed false. The contract cannot call the
observation a completed screen, P0 attempt, P0 final, scientific result,
Task-8 scientific completion, or Task-10 completion.

## Task-10 evidence versus Task-8 machinery

The historical event remains a **Task-10 canonical timing rerun** that exercised
**Task-8 timing-admission machinery**. This implementation creates the Task-8
contract capable of representing such evidence; it does not relabel the
terminated Task-10 execution as Task-8 scientific completion, and it does not
complete Task 10.

The execution facts remain:

- the all-cell probe used the frozen 2,916-cell grid, 200 screen draws per cell,
  and 64-shard receipt topology;
- a passing 43,200-second production projection required the probe to finish
  strictly within 432 seconds because the registered multiplier is 100x;
- the observed elapsed lower bound exceeded two hours before the user
  authorized `SIGTERM`;
- the process exited without a screen record, timing-verifier marker, shard,
  final, or descendant.

These facts support only a measured host-specific timing no-go. They do not
constitute a completed screen, P0 result, scientific result, or portable
performance claim.

## Advisory review receipts

### Claude

Two bounded read-only Haiku review attempts used
`claude --dangerously-skip-permissions --print --model haiku --effort low`.
The first had a USD 0.25 maximum and the second a USD 0.18 maximum. Each was
terminated by the mandatory 60-second process ceiling without usable output.
The CLI emitted no actual-cost receipt. A malformed intermediate invocation
failed immediately before model work because the variadic `--tools` argument
consumed the prompt. No Claude output supplied authority, findings, or
verification.

### Codex

A bounded read-only review used
`codex --yolo exec --ephemeral -m gpt-5.6-sol
-c model_reasoning_effort=low`. It inspected only `4302dfe..HEAD`, used 44,420
tokens, and reported no enforceable dollar cost. Its output was treated as an
untrusted proposal.

Direct inspection reproduced all eight findings:

1. parent-symlink escape during publication;
2. pathname-replacement deletion during failed-write cleanup;
3. a descendant race between absence scan and publication;
4. malformed/non-JSON descendant bypass;
5. floating-point projection arithmetic;
6. asserted rather than grid-derived 2,916-cell identity;
7. circular caller-controlled host identity;
8. missing parent-root fsync after directory creation.

Red-first tests reproduced the symlink escape, malformed canonical descendant,
non-JSON descendant, floating-point/unbounded-integer defect, grid cardinality
drift, and host relabeling. Direct code review closed the cleanup, lock, and
durability defects. The corrections are in commit `0af5697`.

## Exact E2E blockers

Task 8 may be reconciled as `implementation_complete; E2E_pending` only. The
remaining blockers are:

1. The terminated historical rerun did not emit a machine-verifiable
   monotonic-clock termination-evidence artifact containing the exact start and
   observation readings, stable host identity, physical run-root identity, and
   explicit termination authorization. Journal prose is forensic context, not
   that authority.
2. Consequently, no real `resampling_timing_no_go` record has been created for
   the ignored canonical rerun root. Creating one from invented readings would
   synthesize missing evidence and is forbidden.
3. The root still has no completed screen, timing verifier, shard, validation,
   power final, or scientific descendant. That absence is part of the no-go
   boundary, not missing data to fabricate.
4. No full authority-backed P0 lineage exists. Task-9 packet capability,
   branch execution, task-block transaction, and CLI work remain outside this
   branch and outside Task-8 completion.

## Proposed shared reconciliation after Task 9 lands

Do not apply these proposals from this branch:

- `docs/project-status.json`: add a Task-8 implementation entry with
  `implementation_status = implementation_complete`,
  `e2e_status = E2E_pending`, and a blocker specifically naming the absent
  machine-verifiable historical termination evidence/real no-go record.
- `docs/research/neurips-2026-workshop/33-execution-journal.md`: append the
  implementation/review receipts and preserve EJ-20260730-0217 as a
  non-result termination.
- `docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md`: add a
  Task-8 checkpoint that distinguishes Task-10 execution provenance from
  Task-8 machinery ownership and states the exact non-claim.

No proposed edit may call the terminated probe a screen, P0 attempt, final,
scientific result, or scientifically complete Task 8.
