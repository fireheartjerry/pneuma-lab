# Aggressive Test Minimization Design

**Status:** proposed for implementation  
**Date:** 2026-07-29  
**Scope:** repository default test policy and the `resampling_null` suite

## Objective

Create one identical canonical developer/PR gate for native Windows and Linux.
It must complete within five seconds when run inside either operating system,
with a warm-run target below one second. Thirty seconds is the absolute
regression ceiling, not the target.

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

`python scripts/test_fast.py` is the canonical cross-platform command. The
wrapper:

- invokes pytest only on `tests/smoke/`;
- sets `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`;
- sets `PYTHONDONTWRITEBYTECODE=1`;
- disables pytest's cache provider and terminal verbosity;
- uses a five-second subprocess deadline; and
- propagates the child exit code without retries.

`python -m pytest -q` is configured to select the same `tests/smoke/` root, but
the wrapper is the timing authority for CI.

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

Use aggressive but portable optimizations:

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

Do not use marshal/pickle caches, private CPython bytecode APIs, import-hook
monkeypatching, or timing races. Those techniques would make portability and
reproducibility worse. The goal is dark performance magic, not cursed state.

## Stable Commands

```text
python scripts/test_fast.py
python -m pytest -q
python -m pytest tests/ -m milestone -q
python -m pytest tests/ -m forensic -q
```

The first two select the identical portable micro-suite. The other commands are
explicit and never run in ordinary CI.

## Acceptance Criteria

1. Default collection contains no more than eight cases.
2. Three consecutive warm native-Windows runs and three consecutive warm Linux
   runs each finish within five seconds; median warm runtime targets one second.
3. A cold run inside either already-provisioned operating system finishes within
   ten seconds.
4. The resampling suite contains at most 65 test functions, with at most four in
   S02D.
5. The micro-gate detects controlled schema, authorization, packet-symmetry, and
   artifact-tamper defects.
6. The micro-gate has zero skips, xfails, external calls, credential use,
   provider actions, spend, or scientific experiments.
7. Project-status coherence and `git diff --check` remain separate cheap gates.

## Non-Goals

- Preserving test count as a quality metric.
- Maintaining executable coverage for every historical decision-log repair.
- Pretending S02D's POSIX transaction is portable before production code is.
- Adding cloud infrastructure or authorizing an AWS experiment.
- Claiming that fewer tests make unfinished Tasks 6–10 experiment-ready.
