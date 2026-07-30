# Sacrificial-Worker Agent Test Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make repeated Codex/Claude test runs complete in roughly 100 milliseconds without stale imports by keeping only metadata and pristine infrastructure resident, selecting exact impacted node IDs, and executing every request in a previously unused process.

**Architecture:** A checkout-scoped authenticated supervisor owns the test manifest, dependency graph, fingerprints, private checked-hash pycache, immutable fixture index, and a pool of pristine sacrificial workers. Linux uses a frozen forkserver-style parent; Windows consumes one pre-spawned worker from a replenished magazine. Workers import current application source, invoke pytest exactly once, return a bounded canonical-JSON result, and exit. `sys.monitoring` oracle runs build runtime dependencies, static analysis widens them, and uncertainty always widens selection to the full micro-gate.

**Tech Stack:** CPython 3.12 `sys.monitoring`, `multiprocessing.connection`, `multiprocessing` forkserver/spawn contexts, canonical JSON over `send_bytes`/`recv_bytes`, pytest 8, AST import/resource analysis, mmap, checked-hash bytecode, Windows detached processes, POSIX process groups.

---

## Security and Freshness Invariants

1. The supervisor never imports `pneuma_lab` application modules.
2. Every test request consumes a worker that has never executed application code.
3. The wire protocol never uses `Connection.send`/`recv`, pickle, `eval`, `exec`, or caller-supplied module/function names.
4. A worker executes only exact node IDs already present in the supervisor manifest.
5. Unknown dependencies, structural edits, prior failures, or invalid fingerprints widen selection; uncertainty never returns an empty pass.
6. Protocol error, timeout, worker crash, stale fingerprint, or malformed result kills the supervisor and fails the command without retry.
7. The independent `python -m pytest -q` oracle remains outside the resident architecture.

### Task 1: Define the Bounded Canonical Protocol

**Files:**
- Create: `src/pneuma_lab/testd/__init__.py`
- Create: `src/pneuma_lab/testd/protocol.py`
- Create: `tests/tooling/test_testd_protocol.py`

- [ ] **Step 1: Write protocol RED tests**

Cover:

- exact canonical JSON encoding with sorted keys and no NaN/Infinity;
- maximum message size of 256 KiB;
- rejection of duplicate keys, unknown fields, wrong protocol version, wrong types, and unknown commands;
- accepted commands limited to `run`, `smoke`, `status`, and `stop`;
- result node IDs limited to manifest-shaped strings; and
- `send_bytes`/`recv_bytes` use with no pickle path.

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/tooling/test_testd_protocol.py -q
```

Expected: import failure because `pneuma_lab.testd.protocol` does not exist.

- [ ] **Step 3: Implement frozen wire records**

Define frozen slotted request/result dataclasses with explicit `to_wire` and `from_wire` methods. Encode UTF-8 canonical JSON bytes. Use `json.loads(..., object_pairs_hook=...)` to reject duplicate keys and `parse_constant` to reject nonfinite tokens. Reject extra fields rather than ignoring them.

Expose byte-only helpers:

```python
def send_message(connection: Connection, message: WireMessage) -> None: ...
def receive_message(connection: Connection) -> WireMessage: ...
```

These must call `send_bytes` and `recv_bytes(maxlength=MAX_MESSAGE_BYTES)` only.

- [ ] **Step 4: Run GREEN**

Run:

```powershell
python -m pytest tests/tooling/test_testd_protocol.py -q
```

Expected: all protocol and adversarial parsing tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/pneuma_lab/testd tests/tooling/test_testd_protocol.py
git commit -m "feat(testd): define non-pickle wire protocol"
```

### Task 2: Fingerprint the Checkout, Interpreter, Sources, and Resources

**Files:**
- Create: `src/pneuma_lab/testd/fingerprint.py`
- Create: `tests/tooling/test_testd_fingerprint.py`

- [ ] **Step 1: Write fingerprint RED tests**

Prove that the fingerprint changes for:

- source bytes;
- `pyproject.toml` or `uv.lock`;
- schema/fixture/template bytes;
- Python cache tag, executable, or version;
- platform/system/machine tuple;
- pytest/package version; and
- relevant environment keys.

Also prove file ordering and path separators do not make equivalent manifests nondeterministic.

- [ ] **Step 2: Implement length-framed SHA-256 fingerprints**

Never hash ambiguous concatenation. Frame every path, byte count, and value with fixed-width lengths. Export separate frozen records for:

- `CheckoutFingerprint`;
- `StableRunnerFingerprint`;
- `ApplicationFingerprint`; and
- `EnvironmentFingerprint`.

Use content hashes, not mtime alone. A cheap stat tuple may decide whether content must be rehashed, but it may never be the final identity.

- [ ] **Step 3: Run GREEN and commit**

```powershell
python -m pytest tests/tooling/test_testd_fingerprint.py -q
git add src/pneuma_lab/testd/fingerprint.py tests/tooling/test_testd_fingerprint.py
git commit -m "feat(testd): bind runner and source fingerprints"
```

### Task 3: Build an Exact Test Manifest and Conservative Selector

**Files:**
- Create: `src/pneuma_lab/testd/manifest.py`
- Create: `src/pneuma_lab/testd/selection.py`
- Create: `tests/tooling/test_testd_selection.py`

- [ ] **Step 1: Write selection RED tests**

Create a tiny synthetic graph and prove:

- a changed directly observed module selects its exact node IDs;
- a changed imported parent selects dependants transitively;
- a changed schema/resource selects its consumers;
- a prior failure always reruns;
- test/config/package-initializer/selector edits widen to every micro-case;
- an unknown changed path widens to every micro-case;
- no dirty paths with a fully known green graph may return an explicit empty
  no-op result without consuming a worker;
- uncertainty may never return that empty no-op result; and
- forensic tests are never selected without an explicit forensic request.

- [ ] **Step 2: Implement manifest collection**

Use a disposable subprocess to collect only `tests/smoke` and
`tests/resampling_null`, then emit exact node IDs. Never point the collector at
repository-wide `tests/`; marker deselection would still import historical
modules. Persist a canonical manifest under `build/testd/manifest.json` bound
to the stable runner and test-source fingerprints. Classify nodes as `micro`,
`milestone`, or `forensic`; reject unclassified tests inside those retained
roots.

- [ ] **Step 3: Implement dependency selection**

Store `dependency path -> node ID set` and transitive module edges. Selection returns a frozen `Selection` containing exact node IDs and machine-readable widening reasons. Sort node IDs to make runs deterministic.

Dirty-tree detection uses:

```text
git status --porcelain=v1 -z --untracked-files=all
```

Parse NUL-delimited records without a shell. Explicit changed paths from the client are normalized and confined to the checkout.

- [ ] **Step 4: Run GREEN and commit**

```powershell
python -m pytest tests/tooling/test_testd_selection.py -q
git add src/pneuma_lab/testd/manifest.py src/pneuma_lab/testd/selection.py tests/tooling/test_testd_selection.py
git commit -m "feat(testd): select exact impacted node ids"
```

### Task 4: Record Runtime Dependencies with `sys.monitoring`

**Files:**
- Create: `src/pneuma_lab/testd/monitoring.py`
- Create: `src/pneuma_lab/testd/static_graph.py`
- Create: `tests/tooling/test_testd_monitoring.py`

- [ ] **Step 1: Write runtime-observation RED tests**

Run two tiny test nodes against two modules and prove each node records only code it executes. Prove the monitor:

- uses one reserved tool ID and releases it;
- associates `PY_START` code filenames with the currently active node;
- normalizes `.pyc` back to source;
- ignores stdlib/site-packages outside the locked dependency set; and
- returns failure rather than partial success if monitoring cannot be installed.

- [ ] **Step 2: Implement the monitoring session**

Register only `sys.monitoring.events.PY_START`; avoid line/opcode tracing. A pytest plugin hook sets and clears the current exact node ID around each test. Record confined source paths in thread-local state and merge only after a green oracle run.

- [ ] **Step 3: Add conservative static widening**

Parse imports with `ast`, resolve local modules without importing them, and scan literal resource accesses for schemas, JSON, fixtures, prompt/templates, and config paths. Always add:

- `pyproject.toml`;
- `uv.lock`;
- relevant package `__init__.py` files;
- `tests/smoke/conftest.py`; and
- selector/worker/protocol sources.

Dynamic or unresolved imports widen the affected node to all micro-cases.

- [ ] **Step 4: Run GREEN and commit**

```powershell
python -m pytest tests/tooling/test_testd_monitoring.py -q
git add src/pneuma_lab/testd/monitoring.py src/pneuma_lab/testd/static_graph.py tests/tooling/test_testd_monitoring.py
git commit -m "feat(testd): learn conservative test dependencies"
```

### Task 5: Implement the Single-Use Worker

**Files:**
- Create: `src/pneuma_lab/testd/worker.py`
- Create: `tests/tooling/test_testd_worker.py`

- [ ] **Step 1: Write worker RED tests**

Prove one worker:

- starts without any `pneuma_lab` application module in `sys.modules`;
- validates selected node IDs against its immutable manifest;
- calls `pytest.main` exactly once;
- reports PID, selected IDs, duration, dependency fingerprint, and application import fingerprint;
- returns bounded captured output;
- exits after one request; and
- cannot accept a second request.

Add a stale-source test: modify a temporary application module between two requests and prove two different workers observe the new value.

- [ ] **Step 2: Implement one-shot execution**

The worker receives one validated request from the supervisor-owned pipe, imports pytest and the selected current sources, invokes:

```text
pytest.main(["-q", "-p", "no:cacheprovider", "--import-mode=importlib", *node_ids], plugins=[observer])
```

Then it emits exactly one `RunResult`, closes descriptors, and calls `os._exit` after flushing the protocol. It never loops.

Set `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, a private `PYTHONPYCACHEPREFIX`, deterministic locale/timezone variables that the suite contract requires, and bounded output capture before importing pytest.

- [ ] **Step 3: Run GREEN and commit**

```powershell
python -m pytest tests/tooling/test_testd_worker.py -q
git add src/pneuma_lab/testd/worker.py tests/tooling/test_testd_worker.py
git commit -m "feat(testd): execute tests in one-shot workers"
```

### Task 6: Build the Linux Frozen Fork Parent

**Files:**
- Create: `src/pneuma_lab/testd/linux_pool.py`
- Create: `tests/tooling/test_testd_linux_pool.py`

- [ ] **Step 1: Write Linux-only pool RED tests**

Under Linux, prove:

- the stable parent contains no application modules;
- two requests have different child PIDs;
- source changed between requests is observed;
- every child executes once and exits;
- parent death closes all children; and
- worker crash/timeout becomes a failed result.

Mark this module `milestone`; collect it only on Linux rather than decorating individual tests with skips.

- [ ] **Step 2: Implement the forkserver-style parent**

Use `multiprocessing.get_context("forkserver")` or a narrowly controlled fork parent where the standard context cannot expose the required pipe lifecycle. Preload only protocol, worker bootstrap, pytest core, immutable manifest, and mmap fixture metadata. Explicitly assert no module under the checkout's `src/` root is loaded.

After preload:

```python
gc.collect()
gc.disable()
gc.freeze()
```

Fork one child per request. Never thaw or mutate parent-owned fixture state. Apply process-group/job cleanup so supervisor death does not orphan children.

- [ ] **Step 3: Run GREEN under WSL/Linux**

```powershell
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 build/test-venv-linux/bin/python -m pytest tests/tooling/test_testd_linux_pool.py -q"
```

Expected: all freshness and lifecycle checks pass.

- [ ] **Step 4: Commit**

```powershell
git add src/pneuma_lab/testd/linux_pool.py tests/tooling/test_testd_linux_pool.py
git commit -m "feat(testd): add frozen Linux worker parent"
```

### Task 7: Build the Windows Single-Use Worker Magazine

**Files:**
- Create: `src/pneuma_lab/testd/windows_pool.py`
- Create: `tests/tooling/test_testd_windows_pool.py`

- [ ] **Step 1: Write native-Windows RED tests**

Prove:

- a configured number of pristine spawned workers waits ready;
- taking one worker removes it permanently from the magazine;
- the consumed PID exits after its result;
- replenishment occurs asynchronously;
- source changed after worker spawn but before request is imported fresh;
- stable-runner/config/lockfile change invalidates the whole magazine; and
- crash, timeout, or invalidation failure returns failure.

Collect this module only on Windows rather than using per-test skips.

- [ ] **Step 2: Implement the magazine**

Use `multiprocessing.get_context("spawn")`. A pristine worker may import protocol, pytest core, and immutable runner metadata, then waits on a private pipe. It must not import application modules before receiving its one exact selection.

The magazine:

- defaults to `min(4, max(2, os.cpu_count() or 2))` workers;
- consumes with an atomic queue operation;
- begins replenishment before waiting for the current result;
- kills every worker on stable fingerprint change; and
- uses Windows Job Objects when available, otherwise explicit process handles, to prevent orphans.

- [ ] **Step 3: Run GREEN on native Windows**

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
python -m pytest tests/tooling/test_testd_windows_pool.py -q
```

Expected: all single-use and invalidation checks pass.

- [ ] **Step 4: Commit**

```powershell
git add src/pneuma_lab/testd/windows_pool.py tests/tooling/test_testd_windows_pool.py
git commit -m "feat(testd): add Windows worker magazine"
```

### Task 8: Implement the Authenticated Checkout-Scoped Supervisor

**Files:**
- Create: `src/pneuma_lab/testd/supervisor.py`
- Create: `tests/tooling/test_testd_supervisor.py`

- [ ] **Step 1: Write supervisor RED tests**

Cover:

- random 256-bit auth key and endpoint metadata under ignored `build/testd/`;
- connection with wrong auth key is rejected;
- endpoint metadata permissions are owner-only where the OS supports it;
- request checkout/interpreter fingerprint mismatch kills the supervisor;
- endpoint metadata binds PID, process birth time, executable, and a random
  supervisor nonce so PID reuse cannot target a foreign process;
- `run`, `smoke`, `status`, and `stop` are the only commands;
- uncertainty widens to the complete micro-gate;
- prior failures rerun;
- one-hour idle timeout exits cleanly;
- malformed result, worker crash, or invalidation failure kills the supervisor; and
- no retry occurs.

- [ ] **Step 2: Implement endpoint lifecycle**

Use `multiprocessing.connection.Listener` bound to loopback with `authkey`, but immediately switch to the byte-only protocol helpers. Choose an ephemeral TCP port on Windows and Linux to avoid platform-specific named-pipe/Unix-socket divergence. Atomically publish endpoint JSON containing protocol version, PID, port, auth key, checkout fingerprint, interpreter fingerprint, and start time.

Before replacing endpoint metadata, use `psutil` to prove the recorded PID,
birth time, executable, checkout/interpreter fingerprint, and authenticated
supervisor nonce all match. If they do not, quarantine the stale endpoint
metadata and fail closed; never signal the ambiguous PID. Remove only the exact
checkout-scoped endpoint file on clean exit.

- [ ] **Step 3: Implement the request loop**

The supervisor owns no application imports. For each request it:

1. refreshes fingerprints;
2. invalidates manifest/workers when required;
3. selects exact node IDs conservatively;
4. consumes one sacrificial worker;
5. waits under the request deadline;
6. validates the bounded result and worker freshness fields;
7. updates dependency/prior-failure metadata only after a coherent result; and
8. responds once.

- [ ] **Step 4: Run GREEN on both OSes**

```powershell
python -m pytest tests/tooling/test_testd_supervisor.py -q
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && build/test-venv-linux/bin/python -m pytest tests/tooling/test_testd_supervisor.py -q"
```

Expected: all protocol, lifecycle, widening, and fail-closed tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/pneuma_lab/testd/supervisor.py tests/tooling/test_testd_supervisor.py
git commit -m "feat(testd): supervise authenticated sacrificial workers"
```

### Task 9: Replace the Transitional Client with the Hot Client

**Files:**
- Create: `src/pneuma_lab/testd/client.py`
- Modify: `scripts/test_fast.py`
- Modify: `tests/tooling/test_test_fast_cold.py`
- Create: `tests/tooling/test_testd_client.py`

- [ ] **Step 1: Write client RED tests**

Prove:

- first run starts one detached supervisor and waits for a valid endpoint;
- concurrent first clients converge on one supervisor;
- later runs reuse the endpoint, not an application worker;
- default command sends dirty paths and `run`;
- `--smoke`, `--cold`, `--status`, and `--stop` map to exact protocol commands;
- five-second client deadline is enforced;
- protocol error kills the recorded supervisor only after PID/birth-time/
  executable/nonce identity is authenticated, then returns nonzero;
- no automatic retry occurs; and
- output clearly separates fast unit selection from legitimate slow milestone selection.

- [ ] **Step 2: Implement cross-platform detached startup**

Use `subprocess.Popen` with an argument list and no shell:

- Windows: `CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`;
- Linux: `start_new_session=True`, redirected standard handles, and a parent-death/liveness strategy in the supervisor.

Coordinate concurrent startup with an atomic create-excl lock file carrying PID/fingerprint data. Bound endpoint wait to the same five-second client deadline.

- [ ] **Step 3: Implement CLI behavior**

Stable commands become:

```text
python scripts/test_fast.py
python scripts/test_fast.py --smoke
python scripts/test_fast.py --cold
python scripts/test_fast.py --status
python scripts/test_fast.py --stop
```

`--cold` starts a disposable supervisor, runs the whole micro-gate, and stops it. Default mode sends explicit paths if provided, otherwise uses dirty-tree detection. A passed path outside the checkout is rejected.

- [ ] **Step 4: Run GREEN**

```powershell
python -m pytest tests/tooling/test_testd_client.py tests/tooling/test_test_fast_cold.py -q
python scripts/test_fast.py --stop
python scripts/test_fast.py --smoke
python scripts/test_fast.py --status
```

Expected: tests pass, the first real command starts the supervisor, and status reports a ready pristine worker inventory without application imports.

- [ ] **Step 5: Commit**

```powershell
git add src/pneuma_lab/testd/client.py scripts/test_fast.py tests/tooling/test_testd_client.py tests/tooling/test_test_fast_cold.py
git commit -m "feat(testd): make the agent hot path canonical"
```

### Task 10: Add Immutable Fixture Slab and Private Checked-Hash Cache

**Files:**
- Create: `src/pneuma_lab/testd/cache.py`
- Create: `src/pneuma_lab/testd/fixture_slab.py`
- Create: `tests/tooling/test_testd_cache.py`

- [ ] **Step 1: Write cache RED tests**

Prove:

- cache path is checkout/interpreter/content addressed;
- `.pyc` headers use checked-hash invalidation;
- wrong magic, cache tag, platform tuple, source digest, dependency digest, or `uv.lock` digest rejects the entry;
- fixture slab index ranges are bounded and nonoverlapping;
- returned fixture values are read-only `memoryview` slices; and
- corruption ignores/rebuilds cache rather than loading bytes.

- [ ] **Step 2: Implement checked-hash priming**

Prime stable runner and micro-test sources with `compileall` using `PycInvalidationMode.CHECKED_HASH` into `build/testd/pycache/<fingerprint>/`. Workers receive the exact cache prefix. Do not set `PYTHONDONTWRITEBYTECODE`.

- [ ] **Step 3: Implement the fixture slab**

Pack only immutable canonical fixture bytes used by multiple micro-cases into one content-addressed file. Write an exact path/name/offset/length/digest index, fsync it, then map read-only. No Python object graph, credentials, mutable record, or application callable enters the slab.

- [ ] **Step 4: Run GREEN and commit**

```powershell
python -m pytest tests/tooling/test_testd_cache.py -q
git add src/pneuma_lab/testd/cache.py src/pneuma_lab/testd/fixture_slab.py tests/tooling/test_testd_cache.py
git commit -m "perf(testd): add checked-hash cache and fixture slab"
```

### Task 11: Validate Selector Soundness Against the Pytest Oracle

**Files:**
- Create: `scripts/validate_testd_oracle.py`
- Create: `tests/tooling/test_testd_oracle.py`

- [ ] **Step 1: Define controlled reversible mutations**

Represent mutations as exact preimage/postimage byte pairs, never arbitrary Python callbacks. Include:

1. schema registry filename corruption;
2. authorization fail-open corruption;
3. assignment domain-separator corruption;
4. packet REAL/SHAM symmetry corruption;
5. artifact digest bypass;
6. unrelated documentation edit; and
7. stable runner/config edit.

The harness restores the exact preimage in `finally` and verifies the final digest.

- [ ] **Step 2: Compare fifty alternating runs**

For each mutation, alternate:

1. fast impacted run in a sacrificial worker;
2. independent `python -m pytest -q` oracle;
3. clean restoration;
4. fast impacted run; and
5. independent oracle.

Accumulate at least fifty fast/oracle pairs across passing and failing states.

- [ ] **Step 3: Enforce the superset rule**

The validator fails if:

- fast and oracle verdicts differ;
- a micro-test failing under the oracle was excluded by selection;
- any worker PID repeats;
- application import fingerprint differs from current source;
- a previous failure does not rerun; or
- a structural mutation does not widen to the full micro-gate.

- [ ] **Step 4: Run GREEN on Windows and Linux**

```powershell
python scripts/validate_testd_oracle.py --pairs 50
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && build/test-venv-linux/bin/python scripts/validate_testd_oracle.py --pairs 50"
```

Expected: 50 coherent pairs per OS, zero stale workers, zero missed oracle failures.

- [ ] **Step 5: Commit**

```powershell
git add scripts/validate_testd_oracle.py tests/tooling/test_testd_oracle.py
git commit -m "test(testd): prove fast-path oracle equivalence"
```

### Task 12: Benchmark the Structural Fast Path

**Files:**
- Modify: `scripts/benchmark_test_gate.py`
- Create: `docs/benchmarks/2026-07-29-test-supervisor.json`
- Modify: `docs/project-status.json`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `README.md`

- [ ] **Step 1: Add hot-run benchmark modes**

Record supervisor PID, worker PID, selected node IDs, widening reason, application fingerprint, dependency fingerprint, and wall duration for each run. Reject repeated worker PIDs or changed supervisor PID during a warm series.
An explicit fully-known no-change result has `worker_pid = null`; repeated nulls
are permitted. Every nonempty selection must report a unique worker PID.

- [ ] **Step 2: Benchmark no-change impacted runs**

On native Windows and Linux, warm once and record ten subsequent default runs:

```powershell
python scripts/test_fast.py --smoke
python scripts/benchmark_test_gate.py --label windows-hot-impacted --runs 10 --output build/windows-hot.json -- python scripts/test_fast.py
wsl.exe -- bash -lc "cd /mnt/c/pneuma-lab && build/test-venv-linux/bin/python scripts/test_fast.py --smoke && build/test-venv-linux/bin/python scripts/benchmark_test_gate.py --label linux-hot-impacted --runs 10 --output build/linux-hot.json -- build/test-venv-linux/bin/python scripts/test_fast.py"
```

Acceptance: median at most 100 ms and p95 at most 250 ms on each OS.

- [ ] **Step 3: Benchmark complete warm micro-gates**

Run ten `--smoke` requests per OS.

Acceptance: every complete warm micro-gate is at most one second.

- [ ] **Step 4: Benchmark a relevant one-file edit**

Use a reversible whitespace-neutral edit to one dependency of the assignment micro-case, run the impacted gate, and restore exact bytes.

Acceptance: the current source fingerprint is loaded by a new worker, the expected exact node ID is selected, and the run is at most two seconds.

- [ ] **Step 5: Publish the benchmark receipt and docs**

Merge raw Windows/Linux results into `docs/benchmarks/2026-07-29-test-supervisor.json`. Update canonical status and command docs. State measured p50/p95 values, not aspirational numbers.

- [ ] **Step 6: Final verification**

Run:

```powershell
python scripts/test_fast.py --smoke
python -m pytest -q
python scripts/check_test_budget.py
python -m pneuma_lab.status --check
git diff --check
```

Expected: all pass, every fast result uses a unique worker PID, and status reflects measured budgets.

- [ ] **Step 7: Commit**

```powershell
git add scripts/benchmark_test_gate.py docs/benchmarks/2026-07-29-test-supervisor.json docs/project-status.json AGENTS.md CLAUDE.md README.md
git commit -m "perf(testd): prove sub-250ms agent loop"
```

### Task 13: Admit or Reject Experimental CPython Necromancy

**Files:**
- Create only if admitted: `src/pneuma_lab/testd/code_pack.py`
- Create only if admitted: `src/pneuma_lab/testd/importer.py`
- Create only if admitted: `tests/tooling/test_testd_code_pack.py`
- Modify: `docs/benchmarks/2026-07-29-test-supervisor.json`

- [ ] **Step 1: Measure structural headroom first**

If the Task 12 p95 is already at most 250 ms on both OSes, mark every experimental accelerator `rejected-no-need` in the benchmark receipt and create no code.

If either OS misses, profile at least 30 runs and admit an accelerator only when import/dispatch cost, not worker handoff or pytest execution, accounts for at least 20% of p95.

- [ ] **Step 2: Benchmark candidates one at a time**

Candidate order:

1. disposable worker flag `-X no_debug_ranges`;
2. packed immutable fixture/resource table improvements;
3. exact-hash `MetaPathFinder` for stable runner modules;
4. content-addressed mmap marshal pack for stable runner code objects; and
5. `CodeType.replace()` specialization of generated harness dispatch only.

Each candidate needs 30 baseline and 30 treatment runs on both OSes. Retain only candidates that improve both median and p95 by at least 10%, preserve all oracle verdicts, and do not worsen the other OS by more than 2%.

- [ ] **Step 3: Enforce marshal/code-object rejection before load**

If the marshal lane is admitted, verify before `marshal.loads`:

- full pack SHA-256;
- CPython magic and cache tag;
- exact major/minor/micro version;
- platform/system/machine tuple;
- stable source/dependency hashes;
- `pyproject.toml` and `uv.lock` hashes; and
- bounded record offsets and lengths.

Any mismatch ignores the pack and compiles source. Never patch or replace a production function under test.

- [ ] **Step 4: Prove corruption and foreign-cache behavior**

Corrupt every header field and one payload byte; copy a cache between Windows and Linux fixtures; alter the interpreter tag. Every case must reject before code-object loading and still produce the same pytest verdict from source.

- [ ] **Step 5: Record the verdict**

The benchmark receipt names each candidate, measurements, admission/rejection reason, and retained code paths. Delete all rejected experimental code before commit.

- [ ] **Step 6: Commit only measured survivors or the rejection receipt**

```powershell
git add docs/benchmarks/2026-07-29-test-supervisor.json
if (Test-Path tests/tooling/test_testd_code_pack.py) { git add src/pneuma_lab/testd tests/tooling/test_testd_code_pack.py }
git commit -m "perf(testd): benchmark CPython accelerator lane"
```

Stage only files that actually exist. A clean “none admitted” result is success, not an excuse to add exotic machinery.

## Completion Criteria

This plan is complete only when:

1. Ten no-change impacted runs have median at most 100 ms and p95 at most 250 ms on native Windows and Linux.
2. Ten complete warm micro-gates are each at most one second on both OSes.
3. A relevant source edit selects current code and completes within two seconds.
4. Fifty alternating fast/oracle pairs per OS have identical verdicts and no excluded oracle failure.
5. Every nonempty request uses a unique worker PID; an explicit fully-known
   no-change result uses no worker; no application code is imported in the
   supervisor or stable parent.
6. Stable-runner/config/dependency changes invalidate every pristine worker and cached artifact.
7. Protocol, worker crash, timeout, malformed result, and fingerprint mismatch fail closed without retry.
8. Any admitted marshal/import-hook/code-object optimization has a measured cross-platform win and rejects corrupt or foreign packs before load.
9. `python -m pytest -q` remains an independent cold correctness oracle.
