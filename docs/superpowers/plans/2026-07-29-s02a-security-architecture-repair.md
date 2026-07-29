# S02A Security and Architecture Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make first-record publication descriptor-confined and ownership-safe while splitting S02A authority reconstruction into acyclic, inspectable modules and reusable fixtures.

**Architecture:** `publication.py` owns one root descriptor for a multi-file transaction, reaches descendants only with componentwise `openat`, and rolls back through held parent descriptors with quarantine/restore semantics. `errors.py`, `authority_refs.py`, `provider_contracts.py`, and `task_schedule_codec.py` form a one-way authority stack; `execution_authority.py`, `schedule.py`, and `artifacts.py` consume public internal interfaces without private circular imports. Tests use one explicit `ProviderAuthorityFixture` graph and isolate publication fault injection from public sealing integrations.

**Tech Stack:** Python 3.12, POSIX `openat`/`mkdirat`/`renameat`/`linkat` primitives through `os`, frozen dataclasses, pytest, Ruff, mypy.

---

### Task 1: Freeze Descriptor-Confinement and Rollback Failures

**Files:**
- Create: `tests/resampling_null/test_publication.py`
- Modify: `tests/resampling_null/test_artifacts.py`

- [x] **Step 1: Add ancestor-swap RED tests**

Create a real `BoundPublication` integration that swaps the named run root or an intermediate `sources` component after binding. Each test must assert that publication raises, no file appears in the outside replacement, no success ArtifactRef is returned, and the original bound directory contains no accepted transaction residue.

- [x] **Step 2: Add descriptor-cleanup RED tests**

Snapshot `/proc/self/fd`, inject `os.fstat` and `os.stat` failures at each binding checkpoint, run the failed transaction, force garbage collection only for diagnostics, and assert the descriptor set returns exactly to baseline without relying on object finalizers.

- [x] **Step 3: Add quarantine rollback RED tests**

Inject a peer replacement immediately before rollback quarantine; assert peer bytes remain at the destination. Add a hard-link alias to an owned inode and assert rollback reports the exact residual instead of claiming cleanup. Deny temporary-file unlink and assert the outer causal error names the exact `.tmp` residual.

- [x] **Step 4: Run RED**

Run:

```bash
timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py -q
```

Expected: failures showing full-path ancestor escape, one leaked descriptor on a stat/fstat exception, check/reopen rollback races, false-complete hard-link cleanup, and unnamed temporary residue.

### Task 2: Implement Held-Root Publication

**Files:**
- Create: `src/pneuma_lab/resampling_null/publication.py`
- Modify: `src/pneuma_lab/resampling_null/artifacts.py`
- Test: `tests/resampling_null/test_publication.py`

- [x] **Step 1: Bind the root once**

Implement `BoundPublication(root: Path)` as a context-managed transaction. Open the root with `O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC`, store its device/inode, and close it in every constructor, enter, exit, commit, and rollback failure branch.

- [x] **Step 2: Traverse and create components with dirfds**

Implement a componentwise walker accepting canonical relative POSIX paths. Reject empty, dot, dot-dot, absolute, and noncanonical components. For every directory component, use `os.open(component, ..., dir_fd=parent_fd)`; on absence use `os.mkdir(component, dir_fd=parent_fd)`, reopen no-follow, and verify the named inode equals the opened inode.

- [x] **Step 3: Install without replacement**

Prepare and fsync a transaction-named temporary under the held parent fd, call `os.link(temp, destination, src_dir_fd=parent_fd, dst_dir_fd=parent_fd, follow_symlinks=False)`, and record destination name, held parent fd, device, inode, SHA-256, and size only after successful link. Track temporary names from creation until confirmed unlink.

- [x] **Step 4: Verify root identity before commit**

Before returning success, compare `os.stat(root, follow_symlinks=False)` with the held root device/inode. On mismatch, rollback only through held descriptors and reject the transaction.

- [x] **Step 5: Run GREEN**

Run:

```bash
timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py -q
```

Expected: every confinement, fd, and create-exclusive test passes.

### Task 3: Implement Quarantine Rollback

**Files:**
- Modify: `src/pneuma_lab/resampling_null/publication.py`
- Test: `tests/resampling_null/test_publication.py`

- [x] **Step 1: Quarantine names atomically**

For every owned destination in reverse order, rename its current name under the held parent fd to a transaction-unique `.<transaction>.rollback-<index>` name with no replacement. If the destination disappeared, treat the owned name as gone.

- [x] **Step 2: Verify quarantined ownership**

Open quarantine no-follow, require a regular file with `st_nlink == 1`, and compare device, inode, full digest, and size. A match is unlinked and the parent fsynced.

- [x] **Step 3: Restore non-owned peers**

If quarantine differs from the owned record, restore it to the destination only when the destination is absent and restoration is no-replace. If restoration cannot complete, preserve quarantine and return both the cleanup failure and exact residual name. Never unlink mismatching quarantine.

- [x] **Step 4: Account for temporary residuals**

Rollback every tracked temporary through its held parent fd. Any unlink/fsync failure and any still-named temporary must appear in `PublicationRollbackError` with the original publication exception as `__cause__`.

- [x] **Step 5: Run GREEN and the public integration**

Run:

```bash
timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py tests/resampling_null/test_artifacts.py -q -k 'publication or t5_s02a'
```

Expected: quarantine, peer preservation, hard-link, temp denial, retry, source race, and manifest race tests pass.

### Task 4: Extract Acyclic Authority Reference and Error Layers

**Files:**
- Create: `src/pneuma_lab/resampling_null/errors.py`
- Create: `src/pneuma_lab/resampling_null/authority_refs.py`
- Modify: `src/pneuma_lab/resampling_null/artifacts.py`
- Modify: authority consumers importing `RecordValidationError`

- [x] **Step 1: Move the shared exception**

Define only:

```python
class RecordValidationError(ValueError):
    """Raised when a scientific record or artifact closure is invalid."""
```

in `errors.py`. Import and re-export that same class from `artifacts.py` so existing public imports keep exact identity.

- [x] **Step 2: Extract the strict ref codec**

Move exact ArtifactRef field parsing, expected-role checks, root-confined digest/size reads, strict JSON decoding, recursive exact-ref walking, and a per-validation `dict[ArtifactRef, object]` decoded cache into `authority_refs.py`. It may import only `errors.py`, `types.py`, and standard/foundation canonical byte helpers.

- [x] **Step 3: Redirect only S02A consumers**

Use the new codec in provider contracts, execution authority, schedule, and the v2 provider-copy closure. Leave unrelated legacy ref parsers alone unless they are on this path.

- [x] **Step 4: Keep the focused suite green**

Run:

```bash
timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 't5_s02a or t3_s07_prefix_schedule'
```

Expected: baseline plus new S02A tests pass.

### Task 5: Extract Provider Contracts and Task Schedule Codec

**Files:**
- Create: `src/pneuma_lab/resampling_null/provider_contracts.py`
- Create: `src/pneuma_lab/resampling_null/task_schedule_codec.py`
- Modify: `src/pneuma_lab/resampling_null/execution_authority.py`
- Modify: `src/pneuma_lab/resampling_null/schedule.py`
- Modify: `src/pneuma_lab/resampling_null/branch_assignment.py`
- Modify: `src/pneuma_lab/resampling_null/artifacts.py`
- Modify: `src/pneuma_lab/resampling_null/types.py`
- Modify: `src/pneuma_lab/resampling_null/__init__.py`

- [x] **Step 1: Rename role-neutral caps**

Rename `SimulatorCaps` to `CallContractCaps`, update intentional public exports, and make cap field specifications ordered tuples so error ordering is stable.

- [x] **Step 2: Decompose provider validation**

Move call/parser/meter/task contract validation and provider-plan decoding into public internal `validate_provider_lane_plan`. Split lane parsing, task-lane parsing, and cross-lane coherence into separate functions below 150 lines. Return frozen `ValidatedProviderPlan`, `ValidatedLane`, and `ValidatedTaskLane` records.

- [x] **Step 3: Extract task schedule decoding**

Expose `decode_task_schedule` from `task_schedule_codec.py`; both branch assignment and execution authority consume it without importing a private branch function.

- [x] **Step 4: Remove circular/private imports**

`schedule.py` and `artifacts.py` import `validate_provider_lane_plan` statically from `provider_contracts.py`. `execution_authority.py` contains only its frozen public result and schedule-to-selected-task projection, with scientific loading supplied by a one-way record layer. Delete the artifacts dynamic import and the private schedule/provider imports.

- [x] **Step 5: Validate exact authority text**

Before roster/assignment pair lookup, require exact non-empty strings for both values. Unknown or mismatched values retain the existing fail-closed error.

- [x] **Step 6: Run GREEN/static**

Run:

```bash
timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 't5_s02a or t3_s07_prefix_schedule'
timeout 60s .venv/bin/python -m ruff check src/pneuma_lab/resampling_null
timeout 60s .venv/bin/python -m mypy --ignore-missing-imports src/pneuma_lab/resampling_null/authority_refs.py src/pneuma_lab/resampling_null/provider_contracts.py src/pneuma_lab/resampling_null/execution_authority.py src/pneuma_lab/resampling_null/publication.py
```

Expected: behavior stays green; no private-cycle or type error remains.

### Task 6: Consolidate Provider Authority Fixtures

**Files:**
- Create: `tests/resampling_null/__init__.py`
- Create: `tests/resampling_null/provider_authority_fixture.py`
- Modify: `tests/resampling_null/test_controller.py`
- Modify: `tests/resampling_null/test_artifacts.py`

- [x] **Step 1: Build one inspectable graph**

Create shared `ProviderAuthorityFixture` support exposing named ArtifactRefs and explicit build-time mutations for role, cap, simulator, parser, meter, deep-ref, benchmark, and conditional authority.

- [x] **Step 2: Replace controller duplication**

Replace `_authority_fixture` with the shared builder and preserve every existing parametrized mutation and public loader assertion.

- [x] **Step 3: Replace the artifacts god test**

Use the shared source graph in the small public `seal_study_manifest` integration. Move link/fd/quarantine fault injection to `test_publication.py` and keep only semantic path/role publication faults in the small seal integration.

- [x] **Step 4: Run focused GREEN**

Run:

```bash
timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py tests/resampling_null/test_publication.py -q -k 't5_s02a or t3_s07_prefix_schedule or publication'
```

Expected: all focused behavior passes with inspectable named refs and materially smaller test builders.

### Task 7: Final Forensic Gate

**Files:**
- Modify: `docs/research/neurips-2026-workshop/33-execution-journal.md`

- [x] **Step 1: Audit module/function sizes and imports**

Run:

```bash
wc -l src/pneuma_lab/resampling_null/{authority_refs.py,provider_contracts.py,execution_authority.py,publication.py}
rg -n 'from \\.artifacts|from \\.execution_authority|_task_schedule|_validate_provider_lane_plan' src/pneuma_lab/resampling_null
```

Expected: no new module exceeds roughly 700 lines, core functions remain below roughly 150 lines, and the rejected private cycles are absent.

- [x] **Step 2: Run the fresh behavior and static gates**

Run the focused pytest command, focused Ruff, focused mypy, `.venv/bin/python -m pneuma_lab.status --check`, and `git diff --check`, each with the required 60-second ceiling where applicable.

- [x] **Step 3: Append the journal**

Record exact RED/GREEN counts, injected failure evidence, module seams, residual non-claims, commands, results, and content hashes in the append-only execution journal.

- [x] **Step 4: Commit without pushing**

Stage only the planned source, tests, plan, and journal. Confirm `raw_root_placeholder` remains untracked and commit the security/architecture repair without pushing.
