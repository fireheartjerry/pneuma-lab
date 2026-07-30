# Task 9 Branch Program Authority Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make four post-trigger branch programs per selected task immutable,
manifest-bound execution authority without claiming that a P0 lineage ran.

**Architecture:** Add a strict branch-program registry schema and codec, seal
the registry plus its complete program closure as a required study-manifest
input, and resolve its task/ordinal rows only through manifest ancestry at the
branch CLI boundary. Branch ordinals exist at study freeze; later opaque slot
and allocation-capability identities are reconciled in schedule-derived
work-order order, avoiding circular authority.

**Tech Stack:** Python 3.12, frozen dataclasses, JSON Schema 2020-12,
content-addressed `ArtifactRef` records, pytest, Ruff, mypy.

---

## File map

- Create `schemas/resampling-branch-program-registry.schema.json`: closed
  machine-readable registry contract.
- Create `src/pneuma_lab/resampling_null/branch_program_authority.py`: strict
  codec, source-closure planner, manifest-rooted resolver, and reconciliation.
- Create `tests/resampling_null/test_branch_program_authority.py`: focused
  schema, codec, closure, resolution, and hostile mismatch tests.
- Modify `schemas/resampling-study-manifest.schema.json`: require the sealed
  registry reference.
- Modify `src/pneuma_lab/schemas/__init__.py`: register the new schema.
- Modify `src/pneuma_lab/resampling_null/artifacts.py`: seal the registry and
  nested program closure before manifest publication.
- Modify `src/pneuma_lab/resampling_null/cli.py`: accept the registry source at
  study seal and consume manifest-only program authority during branches.
- Modify `tests/resampling_null/provider_study_fixture.py`,
  `tests/resampling_null/test_artifacts.py`, and
  `tests/resampling_null/test_cli.py`: migrate the canonical study fixture and
  prove whole-run admission.
- Modify `docs/project-status.json`,
  `docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md`, and
  `docs/research/neurips-2026-workshop/33-execution-journal.md`: record the
  completed authority milestone without promoting E2E.

### Task 1: Freeze the registry schema and strict codec

- [ ] **Step 1: Write the failing schema and codec tests**

Create tests that construct this exact valid shape:

```python
registry = {
    "record_kind": "resampling_branch_program_registry_v1",
    "schema_version": "0.1.0",
    "tasks": [
        {
            "task_id": "task-1",
            "programs": [
                {"branch_ordinal": ordinal, "program_ref": ref_value(ref)}
                for ordinal, ref in enumerate(program_refs)
            ],
        }
    ],
}
```

Assert exact round-trip decoding and rejection of:

```python
hostile_mutations = (
    missing_task,
    duplicate_task,
    missing_ordinal,
    duplicate_ordinal,
    reordered_ordinal,
    fifth_ordinal,
    wrong_program_role,
    wrong_program_media_type,
    open_top_level,
    open_task_row,
    open_program_row,
)
```

- [ ] **Step 2: Run RED**

Run:

```bash
timeout 60s .venv/bin/python -m pytest \
  tests/resampling_null/test_branch_program_authority.py -q
```

Expected: collection fails because
`pneuma_lab.resampling_null.branch_program_authority` does not exist.

- [ ] **Step 3: Add the schema and minimal codec**

Implement:

```python
@dataclass(frozen=True, slots=True)
class BranchProgramEntry:
    branch_ordinal: int
    program_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class BranchProgramTask:
    task_id: str
    programs: tuple[
        BranchProgramEntry,
        BranchProgramEntry,
        BranchProgramEntry,
        BranchProgramEntry,
    ]


@dataclass(frozen=True, slots=True)
class BranchProgramRegistry:
    tasks: tuple[BranchProgramTask, ...]


def load_branch_program_registry(payload: bytes) -> BranchProgramRegistry:
    ...
```

The loader requires canonical task order, ordinals exactly `(0, 1, 2, 3)`,
unique task IDs, `synthetic_execution_program` role, and
`application/json` media type.

- [ ] **Step 4: Run GREEN and static checks**

Run the focused pytest command above, then:

```bash
timeout 60s .venv/bin/ruff check \
  src/pneuma_lab/resampling_null/branch_program_authority.py \
  tests/resampling_null/test_branch_program_authority.py
timeout 60s .venv/bin/mypy \
  src/pneuma_lab/resampling_null/branch_program_authority.py \
  --ignore-missing-imports
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add schemas/resampling-branch-program-registry.schema.json \
  src/pneuma_lab/schemas/__init__.py \
  src/pneuma_lab/resampling_null/branch_program_authority.py \
  tests/resampling_null/test_branch_program_authority.py \
  tests/test_schema_loads.py
git commit -m "test: freeze Task 9 branch program authority"
```

### Task 2: Seal the registry and complete nested program closure

- [ ] **Step 1: Write failing sealing tests**

Extend the canonical provider study fixture with one registry source. Assert
that `seal_study_manifest`:

```python
manifest["payload"]["branch_program_registry_ref"] == ref_value(sealed_registry)
```

and that every program-reachable request, event, tool result, grade, verifier,
tool schema, clock trace, and environment ref is copied at the same relative
path and exact digest.

Add hostile cases for dangling refs, source-root escape, symlink traversal,
wrong bytes, conflicting destinations, wrong program task ID, task coverage
different from the task registry, and publication failure leaving no partial
scientific record.

- [ ] **Step 2: Run RED**

```bash
timeout 60s .venv/bin/python -m pytest \
  tests/resampling_null/test_branch_program_authority.py \
  tests/resampling_null/test_artifacts.py \
  -q -k 'branch_program_authority or t5_s02a'
```

Expected: valid sealing fails because `seal_study_manifest` has no required
registry source or payload field.

- [ ] **Step 3: Implement the sealing boundary**

Change the public signature to require:

```python
def seal_study_manifest(
    ...,
    branch_program_registry_source: Path,
    ...,
) -> ArtifactRef:
    ...
```

Add `plan_branch_program_registry_closure(...) -> tuple[_SourceCopy, ...]`.
Reuse `AuthorityRefReader`, closed role/media registries, stable no-follow
reads, `_SourceCopy`, and `BoundPublication`; do not create a second copier.
Require registry task coverage to equal the frozen task registry exactly.

- [ ] **Step 4: Run GREEN and static checks**

Run the focused command from Step 2 and focused Ruff/mypy over
`artifacts.py`, `branch_program_authority.py`, and changed tests.

- [ ] **Step 5: Commit**

```bash
git add schemas/resampling-study-manifest.schema.json \
  src/pneuma_lab/resampling_null/artifacts.py \
  src/pneuma_lab/resampling_null/branch_program_authority.py \
  tests/resampling_null/provider_study_fixture.py \
  tests/resampling_null/test_artifacts.py \
  tests/resampling_null/test_branch_program_authority.py
git commit -m "feat: seal Task 9 branch program authority"
```

### Task 3: Resolve authority against later opaque work orders

- [ ] **Step 1: Write failing resolver tests**

Specify this public seam:

```python
refs = resolve_branch_program_refs(
    run_root=root,
    study_ref=study_ref,
    task_id="task-1",
    work_orders=work_orders,
)
assert refs == program_refs
```

Prove failure for a wrong manifest registry ref, wrong task, wrong program task
binding, incomplete closure, non-four work-order tuple, duplicate slots,
duplicate capabilities, wrong task IDs in work orders, and reordered
schedule-derived work orders. Prove no API accepts caller-supplied program refs.

- [ ] **Step 2: Run RED**

```bash
timeout 60s .venv/bin/python -m pytest \
  tests/resampling_null/test_branch_program_authority.py -q \
  -k 'resolve or reconcile'
```

Expected: failure because `resolve_branch_program_refs` does not exist.

- [ ] **Step 3: Implement minimal manifest-rooted resolution**

Implement:

```python
def resolve_branch_program_refs(
    *,
    run_root: Path,
    study_ref: ArtifactRef,
    task_id: str,
    work_orders: tuple[
        OpaqueSlotWorkOrder,
        OpaqueSlotWorkOrder,
        OpaqueSlotWorkOrder,
        OpaqueSlotWorkOrder,
    ],
) -> tuple[ArtifactRef, ArtifactRef, ArtifactRef, ArtifactRef]:
    ...
```

Load the manifest through `load_scientific_parent`, resolve its registry with
`AuthorityRefReader`, fresh-read every program closure, and require work-order
task equality, unique slot IDs/capabilities, and exact schedule-derived order.
Return refs only in registry ordinal order.

- [ ] **Step 4: Run GREEN and static checks**

Run the focused resolver tests, then focused Ruff/mypy and `git diff --check`.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/resampling_null/branch_program_authority.py \
  tests/resampling_null/test_branch_program_authority.py
git commit -m "feat: resolve manifest-bound branch programs"
```

### Task 4: Wire whole-run CLI admission

- [ ] **Step 1: Write failing CLI tests**

Replace the historical “not authorized by any manifest” test with:

```python
refs = cli._branch_program_refs(
    root=root,
    study_ref=study_ref,
    task_id=task_id,
    work_orders=work_orders,
)
assert refs == expected_refs
```

Add a command-level test proving all triggered tasks resolve before the first
worker or task-block mutation. Inject failure in the final task and assert no
worker call and no task block. Preserve the no-intervention identity-path test.
Assert `study seal` requires `--branch-program-registry-source`.

- [ ] **Step 2: Run RED**

```bash
timeout 60s .venv/bin/python -m pytest \
  tests/resampling_null/test_cli.py \
  tests/resampling_null/test_branch_program_authority.py -q \
  -k 'branch_program or synthetic_branches'
```

Expected: the current `_branch_program_refs(task_id)` stub raises the old
authority error and study seal lacks the new argument.

- [ ] **Step 3: Wire the resolver and execution input**

Change `_branch_program_refs` to delegate only to
`resolve_branch_program_refs`. During `_synthetic_branches`, retain each
triggered task's exact four work orders and resolved four refs in the admission
list before mutation. Pass each `(work_order, program_ref)` pair to the existing
isolated branch executor. Do not add a CLI program-ref option.

- [ ] **Step 4: Run GREEN and static checks**

Run the focused CLI command, then:

```bash
timeout 60s .venv/bin/python -m pytest \
  tests/resampling_null/test_branch_program_authority.py \
  tests/resampling_null/test_cli.py \
  tests/resampling_null/test_branch_controller.py \
  tests/resampling_null/test_packet_capabilities.py -q
```

Run focused Ruff/mypy and `git diff --check`.

- [ ] **Step 5: Commit**

```bash
git add src/pneuma_lab/resampling_null/cli.py \
  tests/resampling_null/test_cli.py \
  tests/resampling_null/test_branch_program_authority.py
git commit -m "feat: admit manifest-bound synthetic branches"
```

### Task 5: Canonical evidence, hostile verification, and publication

- [ ] **Step 1: Update canonical status and handoff**

Remove only `B-NEURIPS-TASK9-BRANCH-PROGRAM-AUTHORITY` from Task 9's blocker
list. Keep:

```json
"implementation_status": "implementation_complete",
"e2e_status": "E2E_pending",
"blockers": ["B-NEURIPS-TASK9-E2E"]
```

Append an execution-journal event with exact RED/GREEN/static commands and
results. Update the handoff to state authority complete and the next gate is a
genuinely admitted full P0 lineage.

- [ ] **Step 2: Run the completion audit**

```bash
timeout 60s .venv/bin/python -m pytest \
  tests/resampling_null/test_branch_program_authority.py \
  tests/resampling_null/test_artifacts.py \
  tests/resampling_null/test_cli.py \
  tests/resampling_null/test_branch_controller.py \
  tests/resampling_null/test_packet_capabilities.py -q
timeout 60s .venv/bin/python -m pytest \
  tests/test_schema_loads.py -q
timeout 60s .venv/bin/python scripts/test_fast.py
.venv/bin/python -m pneuma_lab.status --check
git diff --check
git status --short
```

Every command must exit zero. Passing tests prove implementation authority,
not a scientific result.

- [ ] **Step 3: Commit and push**

```bash
git add docs/project-status.json \
  docs/research/neurips-2026-workshop/33-execution-journal.md \
  docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md
git commit -m "docs: close Task 9 branch authority gate"
git push origin codex/neurips-2026-empirical
git fetch origin
git rev-list --left-right --count \
  origin/codex/neurips-2026-empirical...codex/neurips-2026-empirical
```

Expected final divergence: `0 0`.
