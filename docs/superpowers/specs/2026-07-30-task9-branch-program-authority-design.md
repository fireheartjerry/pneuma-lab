# Task 9 Branch Program Authority Design

## Goal

Close Task 9's remaining implementation authority gap by making every
post-trigger synthetic branch program an immutable, manifest-bound input.
This milestone authorizes branch execution but does not execute a P0 lineage
or promote Task 9 beyond `implementation_complete; E2E_pending`.

## Authority boundary

The study manifest gains one required `branch_program_registry_ref`. The
referenced `resampling_branch_program_registry_v1` record is the sole authority
for post-trigger branch programs. CLI arguments, runtime-generated programs,
prefix-program reuse, and fixture-only substitutions are inadmissible.

The registry contains canonical task rows. Each row binds one task identity to
exactly four branch-program entries in the preregistered slot order. Each entry
binds:

- the opaque slot identity;
- the allocation capability digest used by the work order; and
- one `synthetic_execution_program` artifact reference.

Task rows and slot rows use the canonical schedule order. Duplicate, missing,
extra, or reordered tasks or slots fail closed.

## Sealing

`seal_study_manifest` accepts the registry as a required source. Before
publishing the first scientific record it:

1. parses and schema-validates the registry;
2. copies the registry and its complete program closure into the run root;
3. rejects conflicting destinations, paths outside the source boundary,
   symlinks, role/media mismatches, and digest or byte-count mismatches;
4. verifies exact registry coverage against the frozen task registry and
   synthetic provider authority; and
5. places the sealed registry reference in the final manifest payload.

Nested program closure uses the existing
`synthetic_execution_program` contract. Each program must bind the same
`task_id` as its registry row and retain valid tool-schema, request, provider
event, tool-result, grade, verifier, clock, and environment references.

## Runtime resolution

`_branch_program_refs` accepts the sealed study manifest, schedule authority,
task identity, and prepared opaque work orders. It reads only manifest-reachable
artifacts and returns four program references in the work orders'
preregistered order.

Resolution revalidates:

- registry identity and manifest binding;
- exact task coverage;
- exact slot and allocation-capability coverage;
- program task identity;
- program role and JSON media type; and
- complete sealed program closure.

The branch command performs this admission for every triggered task before it
writes any task block or starts a worker. An untriggered task requires no branch
program row and remains on the identity path.

## Failure behavior

All ambiguity fails closed before branch execution. In particular, the system
rejects missing or extra tasks, fewer or more than four slots, duplicate slot
or capability identities, reordered slots, swapped program references, wrong
task bindings, malformed or unsealed nested references, and any caller attempt
to supply a replacement program.

No fallback derives a branch program from the prefix program. No code creates
branch programs after the manifest is sealed.

## Verification

Tests must first fail against the current authority stub, then prove:

- schema and codec strictness for the registry;
- deterministic sealing and full nested closure copying;
- exact task/slot/capability coverage;
- rejection of every hostile mismatch listed above;
- manifest-only CLI resolution in preregistered order;
- whole-run admission before mutation; and
- preservation of the no-intervention identity path.

The focused Task 9 tests, schema tests, fast gate, status checker, and
`git diff --check` must pass within the repository's 60-second software-test
ceiling.

## Evidence and status

After verification, remove `B-NEURIPS-TASK9-BRANCH-PROGRAM-AUTHORITY` from the
canonical Task 9 blocker list and retain `B-NEURIPS-TASK9-E2E`. Update the live
handoff and append-only execution journal with the exact commands, results,
deviations, commit, and push.

This milestone makes branch execution authoritatively admissible. It does not
prove that a full P0 lineage ran, that Tasks 6 or 7 completed E2E, or that a
scientific result exists.
