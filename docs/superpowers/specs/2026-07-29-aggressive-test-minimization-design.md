# Aggressive Test Minimization Design

**Status:** proposed for implementation  
**Date:** 2026-07-29  
**Scope:** repository default test policy and the `resampling_null` suite

## Objective

Make the canonical developer and future pull-request test gate complete in less
than 30 seconds on the WSL2/Linux environment used for AWS parity work.

The current shape is unacceptable: `tests/resampling_null/` contains 437 test
functions across roughly 740 KiB, and the S02D file alone expands to 92 cases
and takes about 53 seconds. There is no checked-in GitHub Actions workflow, so
the immediate problem is the repository's default test policy and test volume.

## Policy

Tests are retained only when they can falsify a distinct paper-critical or
public-contract claim. Historical implementation anxieties, reviewer-specific
regressions, internal call-shape assertions, exhaustive fault-stage products,
and multiple tests of the same invariant are not permanent assets.

Deleting a test is preferable to trivializing it. The implementation must not
replace meaningful tests with `assert True`, empty mocks, or assertions that
merely restate fixture values.

## Three Tiers

### 1. Smoke — default and future PR gate

The default command selects only the `smoke` marker and must:

- collect no more than 20 test cases;
- complete within 30 seconds on a warm WSL2/Linux environment;
- avoid foundation/Qwen imports and external data or network access;
- cover status/schema coherence;
- cover one authorization-denial path;
- cover one deterministic assignment/packet vector;
- cover one synthetic controller-to-prefix-index happy path; and
- cover one artifact-tamper rejection.

The canonical CI wrapper enforces the 30-second wall-clock deadline. A timeout
is a failure, not permission to silently drop a test during the run.

### 2. Milestone — explicit pre-experiment gate

The milestone suite contains the smallest additional set needed before a
placebo experiment, paper result, or release. It is never part of the default
developer loop and must complete within five minutes.

It covers one representative failure for each public resampling transaction,
the registered statistical golden vectors, deterministic replay, and artifact
reconstruction. It does not restore exhaustive operating-system fault matrices.

### 3. Forensic — opt-in only

Any surviving expensive adversarial tests use a `forensic` marker and run only
when a specific investigation or release review requires them. Forensic tests
are not presumed valuable merely because they already exist.

## Aggressive Reduction Rules

Reduce `tests/resampling_null/` by at least 75% by test-function count, from 437
to at most 109. Reduce `test_s02d_prefix_index.py` from 61 test functions to at
most 10.

Delete or consolidate:

- exact duplicates and near-duplicates;
- permutations that exercise the same validation branch;
- tests of private helper names, signatures, AST shape, or internal sequencing;
- injected failure at every individual `open`, `fstat`, `fsync`, `close`,
  `flock`, rename, and cleanup stage;
- numeric-file-descriptor reuse, bytecode-interruption, and asynchronous
  exception archaeology;
- tests whose sole purpose was closing a superseded decision-log finding;
- repeated schema-shape tests already enforced by one canonical validator;
- large fixtures used only to vary one field; and
- slow positive-path reconstruction repeated in many negative tests.

Retain:

- one positive public-API path;
- one representative negative path per distinct public invariant;
- one deterministic golden vector where exact bytes or hashes are contractual;
- spend/authorization fail-closed behavior;
- REAL/SHAM causal-packet symmetry and intended-difference checks;
- registered statistical hand calculations; and
- one end-to-end synthetic placebo artifact chain.

Shared fixture construction must happen at the widest safe scope. Negative
cases must mutate a compact canonical fixture rather than rebuild a complete
study independently.

## Platform Boundary

The new prefix-index implementation is POSIX-specific because it uses `fcntl`.
The canonical smoke and milestone receipts therefore run in WSL2/Linux, matching
the intended AWS environment. Native Windows collection is not a release gate.
The WSL environment must be synchronized from `uv.lock` before timing.

## Commands

The implementation will define these stable commands:

```text
python -m pytest -q
python -m pytest -m milestone -q
python -m pytest -m forensic -q
```

The first command is the sub-30-second smoke gate. Explicit marker expressions
may be used for combined milestone/release checks, but no documentation may call
the forensic suite the default or the "full" gate.

## Acceptance Criteria

1. Default collection contains no more than 20 cases.
2. Three consecutive warm WSL2/Linux default runs each finish in under 30
   seconds.
3. The resampling suite contains at most 109 test functions, with at most 10 in
   S02D.
4. The smoke suite detects a deliberately introduced schema error, authorization
   bypass, packet asymmetry, and artifact tamper in controlled verification.
5. No external call, credential use, provider action, spend, or scientific
   experiment occurs during any test tier.
6. Project-status coherence and `git diff --check` remain separate cheap gates.

## Non-Goals

- Preserving test count as a quality metric.
- Maintaining executable coverage for every historical decision-log repair.
- Supporting the POSIX transaction implementation under native Windows.
- Adding cloud infrastructure or authorizing an AWS experiment.
- Claiming that fewer tests make unfinished Tasks 6–10 experiment-ready.
