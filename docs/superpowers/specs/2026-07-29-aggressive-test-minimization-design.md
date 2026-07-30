# Aggressive Test Minimization Design

**Status:** approved for implementation
**Date:** 2026-07-29
**Scope:** repository default test policy and the `resampling_null` suite

**Implementation plans:**

- `docs/superpowers/plans/2026-07-29-aggressive-test-pruning.md`
- `docs/superpowers/plans/2026-07-29-agent-test-supervisor.md`

## Objective

Create one canonical developer/PR gate for native Windows and Linux. Optimize
primarily for the hot agent loop: repeated test runs in one checkout while
Codex or Claude edits a small number of files.

An impacted warm run targets 100 milliseconds median and 250 milliseconds p95.
The complete micro-gate targets one second warm. A cold run inside either
already provisioned operating system must complete within five seconds. Thirty
seconds is the absolute regression ceiling, not the target.

The current shape is unacceptable: `tests/resampling_null/` contains 437 test
functions across roughly 740 KiB, and the S02D file alone expands to 92 cases
and takes about 53 seconds. There is no checked-in GitHub Actions workflow, so
the immediate problem is the repository's default policy, collection surface,
and test volume.

## Policy

Tests survive only when they can falsify a distinct paper-critical or
public-contract claim. Historical implementation anxieties, reviewer-specific
regressions, private call-shape assertions, exhaustive fault-stage products,
and multiple tests of the same invariant are deleted.

Deleting a test is preferable to trivializing it. Meaningful tests must never
be replaced with `assert True`, empty mocks, assertions that merely restate
fixture values, or other fake coverage.

## Canonical Micro-Gate

Pytest markers alone are insufficient because pytest still discovers, imports,
and parametrizes excluded files. The default pytest gate therefore uses one
`tests/smoke/` module containing at most eight test cases.

The cases cover:

1. project-status and schema coherence;
2. portable public-package import;
3. one authorization-denial path;
4. one deterministic assignment vector;
5. one token-exact REAL/SHAM packet vector;
6. one minimal synthetic controller path;
7. one compact artifact-tamper rejection; and
8. one registered statistical hand calculation once Task 7 exists.

Cases may combine related assertions when they consume the same fixture. Test
count is a ceiling, not a quota.

## Hot Agent Architecture

`python scripts/test_fast.py` is the canonical cross-platform agent command. It
is a client for one checkout-scoped resident **supervisor**. The supervisor
never repeatedly executes changed application tests in its own interpreter.
It keeps only stable infrastructure warm:

- the test manifest and exact node IDs;
- the runtime/static dependency graph;
- source, resource, environment, package, and lockfile fingerprints;
- a checked-hash private pycache;
- immutable mmap fixture indexes; and
- pristine worker inventory.

The first invocation starts the supervisor. Later invocations send the changed
path set or request automatic dirty-tree detection. The supervisor selects exact
impacted node IDs. If dependency certainty is incomplete, it widens to all
eight micro-cases; it never returns an empty selection from uncertainty.

The manifest indexes every retained micro and milestone test. Ordinary impacted
runs may select directly affected milestone tests, but forensic tests require an
explicit request. The sub-250-millisecond target applies to the common unit-test
slice; the client reports separately when a legitimate integration selection
exceeds that target.

The supervisor uses `sys.monitoring` during oracle runs to record Python code
executed by each test. The dependency graph also records imported modules,
schemas, fixture files, prompt/templates, relevant environment keys, package
versions, `pyproject.toml`, and `uv.lock`. Static import/resource analysis widens
runtime observations for code paths not exercised by the last green run.

### Linux worker

Linux uses a forkserver-style parent that preloads only CPython, pytest core,
the minimal runner, and immutable fixture metadata. It does not import
application modules. After preload it runs `gc.collect()`, disables collection,
and calls `gc.freeze()` before forking.

Every request forks one sacrificial worker. The worker imports current
application source, executes the selected node IDs, emits one bounded result,
and exits. Changed source is therefore never hidden by the supervisor's
`sys.modules`.

### Windows worker magazine

Windows maintains a small magazine of pristine spawned workers. Each worker
preloads only stable runner infrastructure and waits without importing
application modules. One request consumes one worker exactly once; after the
result, that worker exits and the supervisor replenishes the magazine
asynchronously.

Any edit to stable runner infrastructure, configuration, dependency metadata,
or the worker bootstrap invalidates the entire magazine before selection.
This preserves fresh application imports without paying spawn latency on the
critical path.

### Supervisor protocol

The supervisor uses an authenticated localhost `multiprocessing.connection`
channel available on both Windows and Linux. A random auth key and endpoint
metadata live only under ignored `build/testd/`. The protocol accepts only
`run`, `smoke`, `status`, and `stop`; it never evaluates caller-supplied Python.

The client enforces a five-second response deadline. A protocol error, worker
crash, failed invalidation, timeout, or malformed result kills the supervisor
and returns failure without retrying. The supervisor exits after one hour idle
or when its checkout/interpreter fingerprint changes.

## Correctness Oracle

`python -m pytest -q` is the ordinary cold oracle over the same
`tests/smoke/` assertions. It disables broad discovery and plugin autoload but
does not use impacted selection or resident workers.

Fast-path results are periodically compared with pytest over controlled passing
and failing mutations. The fast selector is valid only when its selected tests
are a superset of every micro-test that fails under the oracle. Prior failures
always rerun. Structural changes to tests, schemas, configuration, package
initializers, or the selector widen to the entire micro-gate.

Workers report process identity, selected node IDs, dependency fingerprint, and
application import fingerprint. A reused worker, stale import, missing
dependency, or unexplained global state change is a failed run.

## Cross-Platform Boundary

The default micro-suite is identical on Windows and Linux: no OS-conditional
skips, xfails, or alternate expectations.

The current prefix-index module imports POSIX `fcntl` through the package's
eager public import graph. Implementation must isolate that module behind a
lazy platform-neutral package boundary so importing and testing the remaining
public package works on Windows. The micro-gate does not execute S02D namespace
locking. S02D's reduced integration coverage belongs to the Linux milestone
suite until the production transaction itself becomes portable.

This is scope separation, not a Windows pass produced by skipping a selected
test.

## Remaining Tiers

### Milestone

The explicit milestone suite contains the smallest additional set required
before an experiment, paper result, or release. It must complete within 60
seconds on Linux and is never part of the default loop.

It retains one representative failure for each public resampling transaction,
registered statistical golden vectors, deterministic replay, and one
prefix-index publication/rollback integration. It does not restore exhaustive
operating-system fault matrices.

### Forensic

Any surviving expensive adversarial test uses the `forensic` marker and runs
only for a specific investigation. A forensic test is not presumed valuable
because it already exists. No CI workflow runs this tier automatically.

## Aggressive Reduction Rules

Reduce `tests/resampling_null/` by at least 85% by test-function count, from 437
to at most 65. Reduce `test_s02d_prefix_index.py` from 61 functions to at most
four. The default micro-gate contains at most eight cases.

Delete or consolidate:

- exact duplicates and near-duplicates;
- permutations that exercise the same validation branch;
- tests of private helpers, signatures, AST shape, or internal sequencing;
- injected failure at every individual `open`, `fstat`, `fsync`, `close`,
  `flock`, rename, and cleanup stage;
- numeric-file-descriptor reuse, bytecode-interruption, and asynchronous
  exception archaeology;
- tests whose sole purpose was closing a superseded decision-log finding;
- repeated schema-shape tests already enforced by one canonical validator;
- large fixtures used only to vary one field; and
- slow positive-path reconstruction repeated in many negative tests.

Retain only:

- one positive public-API path;
- one representative negative path per distinct public invariant;
- one deterministic golden vector where exact bytes or hashes are contractual;
- spend/authorization fail-closed behavior;
- REAL/SHAM intended-equality and intended-difference checks;
- registered statistical hand calculations; and
- one end-to-end synthetic placebo artifact chain at the milestone tier.

## Performance Optimizations

The structural fast path uses:

- exact node IDs instead of broad collection;
- runtime dependency selection with conservative static widening;
- one micro-test module;
- module/session-scoped immutable canonical fixtures;
- copy-on-mutate shallow records instead of rebuilding study graphs;
- cached compiled JSON Schema validators;
- precomputed canonical bytes and digests;
- deterministic fake clocks instead of waiting;
- no nested subprocesses inside smoke checks;
- no coverage, tracing, third-party plugin autoload, or pytest cache;
- direct narrow imports instead of eager package imports;
- `--import-mode=importlib`;
- a private `PYTHONPYCACHEPREFIX`;
- checked-hash bytecode invalidation; and
- one read-only mmap fixture slab with zero-copy `memoryview` slices.

Stable runner infrastructure is deliberately warmed so CPython 3.12 adaptive
bytecode and inline caches survive in the supervisor/forkserver or pristine
Windows workers. Application code is imported only in sacrificial workers.

Pre-seeded SHA-256 prefix states may be cloned with `.copy()` for related
canonical records. Repeated schema keys may be interned, and hot runner
callables/constants may be prebound into local tuples.

### Experimental accelerator lane

The following are permitted only after the supervisor/selection architecture is
green and benchmarked. Each remains only if it improves representative p50 and
p95 without changing oracle verdicts:

- a content-addressed mmap pack of locally compiled marshalled code objects;
- a narrow `MetaPathFinder` serving only exact-hash stable runner modules;
- `CodeType.replace()` specialization of generated harness dispatch;
- `-X no_debug_ranges` for disposable workers; and
- a packed immutable fixture/resource table.

No accelerator may patch or replace production functions under test. Before
`marshal.loads`, the loader must verify pack digest, CPython magic/cache tag,
platform tuple, exact source/dependency hashes, and `uv.lock`. Any mismatch
ignores the pack and recompiles from source.

## Stable Commands

```text
python scripts/test_fast.py
python scripts/test_fast.py --smoke
python scripts/test_fast.py --cold
python -m pytest -q
python -m pytest tests/resampling_null -m milestone -q
python -m pytest tests/resampling_null -m forensic -q
```

The first command runs the impacted hot slice. `--smoke` runs all micro-cases
through sacrificial workers. `--cold` starts a disposable supervisor and runs
the micro-gate. Pytest is the independent oracle. Milestone and forensic
commands use the compact resampling path directly so pytest never imports the
historical repository-wide suite merely to deselect it. They never run in the
ordinary agent loop.

## Acceptance Criteria

1. Default oracle collection contains no more than eight cases.
2. Ten consecutive no-change impacted runs on native Windows and ten on Linux
   have median wall time at or below 100 milliseconds and p95 at or below 250
   milliseconds.
3. Ten complete warm micro-gates on each OS finish within one second.
4. A relevant one-file edit invalidates, imports current source, and runs within
   two seconds.
5. A cold optimized run inside either already provisioned OS finishes within
   five seconds; cold pytest finishes within ten seconds.
6. The resampling suite contains at most 65 test functions, with at most four in
   S02D.
7. The micro-gate detects controlled schema, authorization, packet-symmetry, and
   artifact-tamper defects.
8. The micro-gate has zero skips, xfails, external calls, credential use,
   provider actions, spend, or scientific experiments.
9. Fifty alternating fast/oracle runs over controlled passing and failing
   mutations produce identical verdicts, and impacted selection never excludes
   an oracle failure.
10. Every fast execution occurs in a previously unused worker that imports the
    current application fingerprint.
11. A stale, corrupted, foreign-platform, or wrong-interpreter bytecode pack is
    rejected before code-object loading.
12. Project-status coherence and `git diff --check` remain separate cheap gates.

## Non-Goals

- Preserving test count as a quality metric.
- Maintaining executable coverage for every historical decision-log repair.
- Pretending S02D's POSIX transaction is portable before production code is.
- Adding cloud infrastructure or authorizing an AWS experiment.
- Claiming that fewer tests make unfinished Tasks 6–10 experiment-ready.
