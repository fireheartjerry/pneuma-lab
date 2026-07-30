# Aggressive Test Pruning and Cold Micro-Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace Pneuma Lab's sprawling default pytest surface with one honest, identical Windows/Linux micro-gate of at most eight cases, delete at least 85% of the `resampling_null` test functions, and make a cold developer gate finish within five seconds.

**Architecture:** `tests/smoke/test_micro_gate.py` is the only default collection surface. It exercises portable public contracts with compact immutable fixtures and no skips, network, credentials, or POSIX-only transaction. `pneuma_lab.resampling_null` becomes a lazy package boundary so native Windows can import portable APIs without importing `fcntl`. The old reviewer-archaeology matrix is replaced by a small explicit milestone suite; a transitional `scripts/test_fast.py` runs the cold gate under a hard deadline until the resident supervisor plan replaces its internals.

**Tech Stack:** Python 3.12, pytest 8, PEP 562 lazy package exports, `subprocess`, `compileall` checked-hash bytecode, PowerShell, WSL2/Linux.

---

## Hard Budgets

- Default collection: at most 8 cases in exactly one test module.
- `tests/resampling_null/`: at most 65 `def test_` functions total.
- `test_s02d_prefix_index.py`: at most 4 `def test_` functions.
- Cold optimized gate: at most 5 seconds in an already provisioned Windows or Linux environment.
- Cold pytest oracle: at most 10 seconds.
- No skip, xfail, external call, provider action, credential read, spend, or experiment in the default gate.

### Task 1: Freeze Baselines and Build a Mechanical Budget Checker

**Files:**
- Create: `scripts/check_test_budget.py`
- Create: `tests/tooling/test_test_budget.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write the failing budget-checker tests**

Create `tests/tooling/test_test_budget.py` with temporary repositories that prove:

1. eight smoke cases and 65 resampling functions pass;
2. a ninth smoke case fails;
3. a 66th resampling function fails;
4. a fifth S02D function fails; and
5. `pytest.skip`, `pytest.xfail`, `unittest.skip`, `@pytest.mark.xfail`, and
   `@pytest.mark.parametrize` in `tests/smoke/` fail.

The tests call a pure `inspect_test_budget(root: Path) -> tuple[str, ...]`; they do not spawn pytest.
Parameterization is forbidden in the micro-gate so the AST case count cannot
hide expanded pytest node IDs.

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/tooling/test_test_budget.py -q
```

Expected: import failure because `scripts.check_test_budget` does not exist.

- [ ] **Step 3: Implement AST-only accounting**

In `scripts/check_test_budget.py`, parse Python files with `ast.parse`, count top-level and class-contained functions whose names start with `test_`, and report stable sorted diagnostics. Export:

```python
def inspect_test_budget(root: Path) -> tuple[str, ...]: ...
def main(argv: Sequence[str] | None = None) -> int: ...
```

The CLI exits `0` only when every budget is satisfied. Do not import test modules; this checker must remain cheap and platform-neutral.

- [ ] **Step 4: Register the test tiers**

Change `pyproject.toml` to:

```toml
[tool.pytest.ini_options]
testpaths = ["tests/smoke"]
pythonpath = ["src"]
addopts = "--import-mode=importlib -p no:cacheprovider -q"
markers = [
    "milestone: explicit pre-experiment, pre-result, or pre-release contract gate",
    "forensic: opt-in adversarial investigation; never part of the ordinary agent loop",
    "qwen_smoke: opt-in smoke test that loads the real pinned Qwen 2B snapshot",
    "foundation: local-Qwen foundation program; frozen and off the NeurIPS paper critical path",
]
```

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` remains a launcher environment setting because pytest configuration is processed after plugin discovery begins.

- [ ] **Step 5: Run GREEN and capture the real baseline**

Run:

```powershell
python -m pytest tests/tooling/test_test_budget.py -q
python scripts/check_test_budget.py
```

Expected: checker unit tests pass; the repository budget command fails and prints the current 437/61 overages.

- [ ] **Step 6: Commit**

```powershell
git add scripts/check_test_budget.py tests/tooling/test_test_budget.py pyproject.toml
git commit -m "test: enforce microscopic suite budgets"
```

### Task 2: Make the Public Resampling Package Importable on Windows

**Files:**
- Modify: `src/pneuma_lab/resampling_null/__init__.py`
- Create: `tests/smoke/test_micro_gate.py`
- Reference: `src/pneuma_lab/interventions/__init__.py`

- [ ] **Step 1: Write the portable-import RED case**

Add the first micro-case:

```python
def test_public_package_import_is_platform_neutral() -> None:
    package = importlib.import_module("pneuma_lab.resampling_null")
    assert "pneuma_lab.resampling_null.prefix_index" not in sys.modules
    assert "pneuma_lab.resampling_null.publication" not in sys.modules
    assert "pneuma_lab.resampling_null.storage" not in sys.modules
    assert package.derive_seed(7, "task-1", "prefix") == 15058118438168183076
```

Use only public exports. Do not monkeypatch `sys.platform`, and do not skip on Windows.

- [ ] **Step 2: Run RED on native Windows**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest tests/smoke/test_micro_gate.py -q
```

Expected: import fails because the eager package initializer reaches `prefix_index.py`, `publication.py`, or `storage.py` and imports `fcntl`.

- [ ] **Step 3: Replace eager imports with a typed lazy export table**

Follow the existing PEP 562 pattern in `pneuma_lab.interventions`. In `resampling_null.__init__`:

- keep only package metadata and `TYPE_CHECKING` imports at module import time;
- define an immutable `name -> (module, attribute)` export table;
- implement `__getattr__` with `importlib.import_module`;
- cache a successfully resolved attribute into `globals()`;
- define `__dir__` and an exact `__all__`; and
- raise normal `AttributeError` for unknown names.

Portable exports such as `derive_seed` must not resolve any POSIX module. POSIX-only exports may still fail clearly when explicitly accessed on Windows; the package import itself may not.

- [ ] **Step 4: Run GREEN on Windows and Linux**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest tests/smoke/test_micro_gate.py -q
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/smoke/test_micro_gate.py -q"
```

Expected: one case passes on each OS and neither process imports `fcntl`.

- [ ] **Step 5: Commit**

```powershell
git add src/pneuma_lab/resampling_null/__init__.py tests/smoke/test_micro_gate.py
git commit -m "refactor: isolate POSIX resampling imports"
```

### Task 3: Build the Eight-Case Canonical Micro-Gate

**Files:**
- Modify: `tests/smoke/test_micro_gate.py`
- Create: `tests/smoke/conftest.py`
- Reference: `tests/resampling_null/test_assignment.py`
- Reference: `tests/resampling_null/test_packets.py`
- Reference: `tests/resampling_null/test_preflight.py`
- Reference: `tests/test_project_status.py`

- [ ] **Step 1: Add compact session fixtures**

In `tests/smoke/conftest.py`, build only immutable canonical bytes, digests, one minimal task identity, and one `SyntheticPacketArtifactStore` root. Use session scope for immutable values and function scope for mutable filesystem state. No fixture may construct the complete study graph.

- [ ] **Step 2: Add the seven presently implementable cases**

Keep the import case from Task 2 and add exactly these six cases:

1. `test_status_and_schema_contracts_are_coherent` calls `load_manifest()` and `validate_manifest()` and validates the registered schema set once.
2. `test_confirmation_preflight_fails_closed_without_live_adapter` proves `ConfirmationPreflightRegistry` raises `ConfirmationPreflightUnavailable`.
3. `test_assignment_and_call_seed_vectors_are_exact` checks the normative `derive_seed` vector plus deterministic/domain-separated `derive_call_seed`.
4. `test_real_and_sham_packet_contract_is_token_exact` verifies intended REAL/SHAM equality and difference surfaces using canonical bytes.
5. `test_minimal_synthetic_controller_path_is_deterministic` runs the smallest public controller operation that needs no provider, clock sleep, subprocess, or POSIX lock.
6. `test_artifact_store_rejects_tamper_and_overwrite` writes one artifact, verifies its reference, mutates bytes, and proves validation fails closed; combine overwrite rejection because it uses the same fixture.

The eighth slot remains absent until the registered Task 7 statistical calculation exists. Do not manufacture a placeholder test.

- [ ] **Step 3: Prove defect sensitivity**

Temporarily apply each of these local mutations one at a time and verify at least one named micro-case fails:

- alter a registered schema filename;
- make confirmation preflight return success without an adapter;
- alter one assignment domain separator;
- make REAL and SHAM packet treatment text identical; and
- bypass artifact digest verification.

Revert each mutation immediately with `apply_patch`; do not use `git checkout` or `git reset`.

- [ ] **Step 4: Verify the collection ceiling**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest --collect-only -q
python scripts/check_test_budget.py
```

Expected: exactly seven default node IDs; the checker still fails only on the old resampling suite size.

- [ ] **Step 5: Commit**

```powershell
git add tests/smoke
git commit -m "test: add seven-case paper micro-gate"
```

### Task 4: Replace 437 Resampling Tests with at Most 65 Claims

**Files:**
- Delete: `tests/resampling_null/test_authority_refs.py`
- Delete: `tests/resampling_null/test_controller_artifacts.py`
- Delete: `tests/resampling_null/test_evidence_primitives.py`
- Delete: `tests/resampling_null/test_prefix_receipt_schema_v01.py`
- Delete: `tests/resampling_null/test_s02c_candidate.py`
- Delete: `tests/resampling_null/test_s02c_contracts.py`
- Delete: `tests/resampling_null/test_s02c_initial_restore.py`
- Delete: `tests/resampling_null/test_s02c_prefix_loop.py`
- Replace: `tests/resampling_null/test_artifacts.py`
- Replace: `tests/resampling_null/test_assignment.py`
- Replace: `tests/resampling_null/test_controller.py`
- Replace: `tests/resampling_null/test_packets.py`
- Replace: `tests/resampling_null/test_preflight.py`
- Replace: `tests/resampling_null/test_publication.py`
- Replace: `tests/resampling_null/test_s02d_prefix_index.py`
- Replace: `tests/resampling_null/test_study_seal_publication.py`
- Replace: `tests/resampling_null/test_types.py`

- [ ] **Step 1: Write the surviving claim ledger before deleting**

At the top of each replacement module, include a short module docstring naming the public claims it protects. Allocate the 65-function ceiling as follows:

| Module | Maximum functions | Surviving claims |
|---|---:|---|
| `test_types.py` | 10 | closed enums, frozen records, safe artifact refs, exact task/slot topology, nonfinite rejection |
| `test_assignment.py` | 8 | frame/commitment vectors, seed/HKDF vectors, uniform draw, one secret single-use path, one synthetic allocation |
| `test_packets.py` | 4 | identifier normalization, REAL/SHAM symmetry, token difference, tamper/overwrite |
| `test_controller.py` | 7 | authority load, nested tamper, lane coherence, portable call seed, public boundary rejection |
| `test_preflight.py` | 5 | content-addressed import, nested authority, Ed25519 exact bytes, no live adapter |
| `test_artifacts.py` | 10 | canonical digest, schema closure, no-replace write, ancestry tamper, one complete synthetic artifact chain |
| `test_publication.py` | 7 | root confinement, no-replace, peer preservation, rollback residual, lease exclusion |
| `test_study_seal_publication.py` | 2 | peer no-replace and clean retry |
| `test_s02d_prefix_index.py` | 4 | positive replay, semantic tamper, owned rollback/retry, contention fail-stop |
| **Total ceiling** | **57** | eight spare functions remain below the hard 65 cap |

All retained modules receive `pytestmark = pytest.mark.milestone`. Do not parameterize one function into dozens of cases; each parametrized node counts toward runtime and must contain at most three representative values.

- [ ] **Step 2: Delete reviewer archaeology**

Delete tests that inject faults at every `open`, `fstat`, `fsync`, `close`, `flock`, rename, opcode boundary, asynchronous exception, descriptor reuse, and superseded decision-log edge. Delete private-helper, AST-shape, exact-signature, internal call-count, and repeated schema-field permutations.

Do not replace deleted tests with trivial assertions or blanket mocks.

- [ ] **Step 3: Rebuild compact public-API tests**

Each survivor must call the narrowest public API, assert the returned value or typed public failure, and reuse one compact canonical fixture. Consolidate assertions only when they validate one transaction or one exact vector.

The S02D file must contain exactly these four public stories:

1. a clean replay publishes the expected prefix index;
2. one coherent-looking semantic tamper is rejected;
3. one late owned-publication failure rolls back and a retry succeeds; and
4. one concurrent reservation is fail-stop.

No S02D test is selected on native Windows because the production transaction itself remains POSIX-only; this is an explicit Linux milestone boundary, not a skip or xfail.

- [ ] **Step 4: Run the mechanical budget**

Run:

```powershell
python scripts/check_test_budget.py
```

Expected: exit `0`, no more than 57 resampling functions, and exactly four S02D functions.

- [ ] **Step 5: Run compact milestones on Linux**

Run:

```powershell
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/resampling_null -m milestone -q"
```

Expected: all retained resampling claims pass in at most 60 seconds.

- [ ] **Step 6: Run the portable subset on Windows**

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest tests/resampling_null -m milestone -q --ignore=tests/resampling_null/test_s02d_prefix_index.py --ignore=tests/resampling_null/test_publication.py --ignore=tests/resampling_null/test_study_seal_publication.py
```

Expected: all portable milestone claims pass. The ignored files correspond only to production POSIX transactions; none are part of the default gate.

- [ ] **Step 7: Commit**

```powershell
git add tests/resampling_null
git commit -m "test: delete resampling archaeology"
```

### Task 5: Implement the Transitional Five-Second Cold Launcher

**Files:**
- Create: `scripts/test_fast.py`
- Create: `tests/tooling/test_test_fast_cold.py`

- [ ] **Step 1: Write launcher RED tests**

Test the pure command builder and a dependency-injected `run_cold` function. Assert:

- it selects only `tests/smoke`;
- it sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`;
- it uses `--import-mode=importlib` and disables pytest cache;
- it creates a checkout-local private pycache under `build/testd/pycache`;
- timeout returns a nonzero fail-closed code; and
- malformed child output never becomes success.

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/tooling/test_test_fast_cold.py -q
```

Expected: import failure because `scripts.test_fast` does not exist.

- [ ] **Step 3: Implement the launcher**

`python scripts/test_fast.py`, `--smoke`, and `--cold` all run the same disposable cold path during this transitional plan. The launcher:

- resolves the checkout from `Path(__file__)`;
- sets a private `PYTHONPYCACHEPREFIX`;
- primes the portable micro-gate dependency roots once on a missing cache with
  `python -m compileall -q --invalidation-mode checked-hash`; subsequent runs
  rely on checked-hash invalidation rather than forcing a full recompile;
- invokes `python -m pytest tests/smoke -q -p no:cacheprovider --import-mode=importlib`;
- gives the total operation five seconds;
- forwards bounded stdout/stderr;
- maps timeout, signal, malformed invocation, and child failure to nonzero exit; and
- never retries.

Use `subprocess.run` with an argument list and no shell. Keep Windows creation flags portable by applying them only when `os.name == "nt"`.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests/tooling/test_test_fast_cold.py -q
python scripts/test_fast.py --cold
```

Expected: unit tests pass and the real micro-gate exits `0` within five seconds.

- [ ] **Step 5: Commit**

```powershell
git add scripts/test_fast.py tests/tooling/test_test_fast_cold.py
git commit -m "feat(test): add fail-closed cold micro-gate"
```

### Task 6: Remove Broad Auto-Marking and Document the New Contract

**Files:**
- Modify: `tests/conftest.py`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/project-status.json`

- [ ] **Step 1: Shrink root conftest**

Remove collection hooks that scan every test filename, broad foundation auto-marking, and Windows CRLF xfail behavior from `tests/conftest.py`. Keep only fixtures required by explicitly invoked legacy/milestone tests. The default smoke module must not import root fixtures it does not use.

- [ ] **Step 2: Replace command documentation**

Document these exact commands:

```text
python scripts/test_fast.py
python scripts/test_fast.py --smoke
python scripts/test_fast.py --cold
python -m pytest -q
python scripts/check_test_budget.py
python -m pytest tests/resampling_null -m milestone -q
python -m pytest tests/resampling_null -m forensic -q
```

State plainly that `python -m pytest -q` means the seven-case cold correctness oracle, not the historical full suite. State that S02D remains a Linux milestone until the production lock transaction is portable.
The milestone/forensic commands deliberately name the compact directory:
marker deselection over `tests/` would still import the historical suite.

- [ ] **Step 3: Update canonical status**

Add a compact current-state entry to `docs/project-status.json` recording the default test count, resampling count, S02D count, Windows/Linux boundary, and that the resident hot supervisor is still pending the second implementation plan. Preserve the manifest schema and run its canonical validator.

- [ ] **Step 4: Verify documentation and status**

Run:

```powershell
python -m pneuma_lab.status --check
python scripts/check_test_budget.py
git diff --check
```

Expected: all exit `0`.

- [ ] **Step 5: Commit**

```powershell
git add tests/conftest.py AGENTS.md CLAUDE.md README.md docs/project-status.json
git commit -m "docs: make the micro-gate canonical"
```

### Task 7: Prove Cross-Platform Timing and Correctness

**Files:**
- Create: `scripts/benchmark_test_gate.py`
- Create: `docs/benchmarks/2026-07-29-test-micro-gate.json`

- [ ] **Step 1: Implement a bounded benchmark harness**

The harness runs a supplied command ten times with `time.perf_counter_ns`, records every duration, median, p95, exit code, Python cache tag, platform tuple, and git commit. It rejects nonzero runs and writes canonical sorted JSON only when all ten pass.

- [ ] **Step 2: Run ten cold optimized gates on native Windows**

Run:

```powershell
python scripts/benchmark_test_gate.py --label windows-cold --runs 10 --output build/windows-cold.json -- python scripts/test_fast.py --cold
```

Expected: median and p95 are reported; every run is at most five seconds.

- [ ] **Step 3: Run ten cold optimized gates under Linux**

Provision an ignored Linux environment if needed, then run:

```powershell
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && python3 -m venv build/test-venv-linux && build/test-venv-linux/bin/python -m pip install -e '.[dev]'"
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && build/test-venv-linux/bin/python scripts/benchmark_test_gate.py --label linux-cold --runs 10 --output build/linux-cold.json -- build/test-venv-linux/bin/python scripts/test_fast.py --cold"
```

Expected: every run is at most five seconds.

- [ ] **Step 4: Benchmark the independent pytest oracle**

Run ten times per OS:

```powershell
python scripts/benchmark_test_gate.py --label windows-pytest --runs 10 --output build/windows-pytest.json -- python -m pytest -q
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && build/test-venv-linux/bin/python scripts/benchmark_test_gate.py --label linux-pytest --runs 10 --output build/linux-pytest.json -- build/test-venv-linux/bin/python -m pytest -q"
```

Expected: every oracle run is at most ten seconds.

- [ ] **Step 5: Publish one machine-readable receipt**

Merge the four ignored raw results into `docs/benchmarks/2026-07-29-test-micro-gate.json`. Include exact case/function counts from `scripts/check_test_budget.py`. Do not claim the 100 ms hot target; that belongs to the resident-supervisor plan.

- [ ] **Step 6: Final verification**

Run:

```powershell
python scripts/check_test_budget.py
python -m pytest -q
python -m pneuma_lab.status --check
git diff --check
```

Expected: all exit `0`; default collection is seven cases; the benchmark receipt proves the cold budgets on both OSes.

- [ ] **Step 7: Commit**

```powershell
git add scripts/benchmark_test_gate.py docs/benchmarks/2026-07-29-test-micro-gate.json
git commit -m "perf(test): prove five-second cross-platform gate"
```

## Completion Criteria

This plan is complete only when:

1. `python -m pytest --collect-only -q` reports at most eight node IDs from one module.
2. `python scripts/check_test_budget.py` reports at most 65 resampling functions and at most four S02D functions.
3. The seven present micro-cases detect the controlled schema, authorization, packet-symmetry, assignment, and tamper mutations.
4. Native Windows and Linux use identical default node IDs with zero skips or xfails.
5. Ten cold optimized runs per OS are each at most five seconds.
6. Ten cold pytest oracle runs per OS are each at most ten seconds.
7. The compact Linux milestone resampling suite is at most 60 seconds.
8. Project status and whitespace checks pass.
