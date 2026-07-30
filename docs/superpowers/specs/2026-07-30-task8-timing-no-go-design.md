# Task 8 Timing No-Go Design

**Status:** approved 2026-07-30

## Scope

Implement a dedicated Task-8 timing-admission record for the frozen P0
configuration. The record represents only a host-specific measured lower-bound
timing no-go. It is not compatible with the power-report graph and cannot be a
screen, P0 attempt, final, scientific result, or authority for descendants.

The historical execution remains Task-10 execution evidence: the Task-10
canonical timing rerun exercised Task-8 timing machinery. Encoding that evidence
in a Task-8 contract does not complete Task 10 or promote Task 8 scientifically.

## Contract

The closed record kind is `resampling_timing_no_go`, schema version `0.1.0`,
with outcome `timing_infeasible_lower_bound`. It binds:

- exact study-manifest, synthetic power-authority, frozen grid, and frozen
  topology ArtifactRefs;
- the run-root identity and host identity used by the terminated rerun;
- the all-cell count, screen and production datasets per cell, 43,200-second
  cap, exact total-work formula, 100x multiplier, and 432-second strict passing
  threshold;
- monotonic-clock evidence whose elapsed value is explicitly a conservative
  lower bound, never a completed duration;
- user-authorized `SIGTERM` evidence and the Task-10 execution-event identity;
- absence of screen, timing-verifier, shard, final, and downstream artifacts;
- closed false flags for screen completion, P0 attempt, P0 final, scientific
  result, Task-8 scientific completion, and Task-10 completion.

Threshold equality is non-decisive and rejected. A valid lower bound must be
strictly greater than 432 seconds.

## Module boundary

`pneuma_lab.resampling_null.timing_no_go` owns construction, canonical
create-exclusive publication, and verification. It does not import
`pneuma_lab.resampling_null.power`, does not emit an `ArtifactRef`, and is not
registered in any power-final ancestry verifier or CLI.

Creation and verification reload every bound artifact by path and SHA-256,
validate the frozen grid/topology constants directly, validate exact projection
arithmetic, and scan the run root for forbidden descendants. Verification also
requires byte-canonical JSON and rechecks descendants on every call, so a later
screen or P0 artifact invalidates the no-go representation.

## Evidence boundary

The implementation does not manufacture a historical monotonic-clock receipt.
It accepts only a closed termination-evidence value containing the clock source,
start and observed monotonic readings, conservative lower bound, authorization
event, signal, and run/host bindings. The real Task-10 rerun can be encoded only
if those inputs are independently available and reviewed. The existing journal
prose alone remains forensic context, not sufficient machine authority.

## Tests and review

Focused tests cover a valid synthetic record and hostile mutations: threshold
equality, claim promotion, missing or drifting refs, grid/topology drift,
noncanonical bytes, duplicate creation, inconsistent monotonic evidence,
wrong execution/task ownership, and every forbidden descendant class.

Schema validation, Python compilation, whitespace checks, a bounded Claude
contract review, a bounded Codex implementation review, and direct manual
verification gate `implementation_complete; E2E_pending`.

