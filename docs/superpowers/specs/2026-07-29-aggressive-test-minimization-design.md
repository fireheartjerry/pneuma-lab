# Aggressive Test Minimization Design

**Status:** proposed for implementation  
**Date:** 2026-07-29  
**Scope:** repository default test policy and the `resampling_null` suite

## Objective

Create one identical canonical developer/PR gate for native Windows and Linux.
Optimize primarily for the hot agent loop: repeated test runs in one checkout
while Codex or Claude edits a small number of files. A no-change warm run targets
100 milliseconds, while a cold run inside either operating system must complete
within five seconds. Thirty seconds is the absolute regression ceiling, not the
target.

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
and parametrizes excluded files. The default gate therefore uses a dedicated
`tests/smoke/` collection root containing at most eight test cases.

`python scripts/test_fast.py` is the canonical cross-platform command. It is a
client for one checkout-scoped resident test daemon:

- the first invocation starts the daemon and performs one cold run;
- later invocations reuse the same initialized CPython process;
- the daemon preloads only the micro-gate dependency graph;
- the client enforces a five-second response deadline;
- any protocol error, failed check, invalidation failure, or timeout kills the
  daemon and returns failure without retrying; and
- the daemon exits after one hour idle or when its checkout fingerprint changes.

The daemon uses a localhost authenticated `multiprocessing.connection` channel,
which is implemented on both Windows and Linux. Its random auth key and endpoint
metadata live only under ignored `build/testd/`. The protocol accepts only
`run`, `status`, and `stop`; it never evaluates caller-supplied Python.

`python -m pytest -q` remains the cold, ordinary, independently understandable
fallback over the same assertions in `tests/smoke/`. The daemon is the timing
authority for the agent loop; cold CI may use either path but must periodically
cross-check daemon results against pytest.

The daemon snapshots working directory, environment, warning filters, random
state, registered validators, and fixture digests before each run. The checks
are pure and receive immutable inputs. Any unexplained state drift fails the
run and kills the daemon instead of contaminating later verdicts.

The eight-case maximum covers:

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

## Cross-Platform Boundary

The default suite is identical on Windows and Linux: no OS-conditional skips,
xfails, or alternate expectations.

The current prefix-index module imports POSIX `fcntl` through the package's
eager public import graph. Implementation must isolate that module behind a
lazy platform-neutral package boundary so importing and testing the remaining
public package works on Windows. The micro-gate does not execute S02D namespace
locking. S02D's reduced integration coverage belongs to the Linux milestone
suite until the production transaction itself becomes portable.

This is honest scope separation, not a Windows pass produced by skipping a
selected test.

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

## Harness-Level Optimizations

Use aggressive portable optimizations:

- explicit collection roots instead of global discovery plus markers;
- one test module for the micro-gate to minimize import and collection work;
- module/session-scoped immutable canonical fixtures;
- copy-on-mutate shallow records instead of rebuilding study graphs;
- cached compiled JSON Schema validators;
- precomputed canonical bytes and digests for unchanged golden fixtures;
- in-process pure checks instead of subprocesses in smoke cases;
- deterministic fake clocks instead of waiting;
- no coverage, tracing, plugin autoload, pytest cache, or bytecode writes;
- no autouse fixtures outside the micro-suite; and
- direct imports from narrow modules rather than package-wide eager imports.

Use these benchmark-gated CPython-specific accelerators in the daemon:

- call `gc.collect()` once after preload, then `gc.freeze()` and disable cyclic
  GC during each pure micro-run;
- deliberately warm CPython 3.12 adaptive bytecode and inline caches before the
  daemon reports ready, retaining specialization across agent runs;
- intern repeated schema keys and bind hot callables/constants into local tuples;
- store canonical fixture bytes in one read-only mmap slab and expose
  `memoryview` slices without copying;
- pre-seed shared SHA-256 prefix states and use `.copy()` for related records;
- compile project modules into checked-hash code objects keyed by CPython magic,
  cache tag, source SHA-256, dependency SHA-256, OS, architecture, and lockfile;
- marshal those locally compiled code objects into one content-addressed mmap
  pack with a compact offset table;
- install a narrow `MetaPathFinder` that serves only exact-hash
  `pneuma_lab`/micro-harness modules from that pack;
- use `CodeType.replace()` only to specialize generated harness dispatch with
  immutable check/fixture constants; and
- prebind the resulting check vector and call it directly, bypassing pytest
  collection, fixtures, hooks, reports, and plugin dispatch on hot runs.

The bytecode pack is never trusted by filename. Before `marshal.loads`, the
daemon verifies the pack digest, interpreter magic/cache tag, platform tuple,
exact source/dependency hashes, and `uv.lock` hash. Any mismatch deletes or
ignores the pack and recompiles from source. Production functions under test
must not be patched or replaced; specialization is restricted to generated
harness dispatch and immutable fixture access.

After every source edit, the client sends a compact stat fingerprint. Unchanged
files remain O(1) metadata checks. Any size/mtime drift triggers SHA-256 of the
affected dependency closure; semantic drift restarts the daemon before running.
This gives aggressive incremental invalidation without returning a pass from
stale production code.

## Stable Commands

```text
python scripts/test_fast.py
python scripts/test_fast.py --cold
python -m pytest -q
python -m pytest tests/ -m milestone -q
python -m pytest tests/ -m forensic -q
```

The first command uses the resident daemon. `--cold` starts a disposable daemon
and is the optimized cold-path receipt. Pytest runs the same logical checks
without the daemon or bytecode pack. Milestone and forensic commands are
explicit and never run in the ordinary agent loop.

## Acceptance Criteria

1. Default collection contains no more than eight cases.
2. Ten consecutive no-change warm runs on native Windows and ten on Linux have
   median wall time at or below 100 milliseconds and p95 at or below 250
   milliseconds.
3. A relevant one-file edit invalidates, reloads, and runs within two seconds.
4. A cold optimized run inside either already-provisioned operating system
   finishes within five seconds; cold pytest finishes within ten seconds.
5. The resampling suite contains at most 65 test functions, with at most four in
   S02D.
6. The micro-gate detects controlled schema, authorization, packet-symmetry, and
   artifact-tamper defects.
7. The micro-gate has zero skips, xfails, external calls, credential use,
   provider actions, spend, or scientific experiments.
8. Fifty alternating daemon/pytest runs over controlled passing and failing
   mutations produce identical verdicts.
9. A stale, corrupted, foreign-platform, or wrong-interpreter bytecode pack is
   rejected before code-object loading.
10. Project-status coherence and `git diff --check` remain separate cheap gates.

## Non-Goals

- Preserving test count as a quality metric.
- Maintaining executable coverage for every historical decision-log repair.
- Pretending S02D's POSIX transaction is portable before production code is.
- Adding cloud infrastructure or authorizing an AWS experiment.
- Claiming that fewer tests make unfinished Tasks 6–10 experiment-ready.
