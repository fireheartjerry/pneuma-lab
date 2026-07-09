# OpenHands Sampled Authorization Review

## Decision

This is a review-only package for `swe-gym-openhands-sampled`. It does not
authorize training. The package records `training_authorized: false`, leaves
the human decision pending, and keeps the training weight at `0.0`.

The proposed controlled scope is one offline `RISK_PREDICTION` baseline over
the 6,055 converted full-trace examples, using only the approved observable
feature contract. Targets remain in `target.resolved`; target, outcome, oracle,
patch, verifier, and raw-text fields are not permitted as inputs.

## Bound artifacts

The companion manifest binds:

- the SWE-Gym/OpenHands source revision and the three processed source hashes;
- the full conversion output, conversion report, and converter provenance;
- the repo-grouped split manifest, report, hash manifest, and example hash;
- code commit `4e55121396b029565237d41433a9b17142d1a51e`, with `src/`,
  `schemas/`, and `pyproject.toml` protected from drift;
- the repo-local output root
  `build/training_runs/openhands-sampled/risk-baseline-v0/`;
- the frozen baseline constants and required evaluation metrics.

Ignored `build/` paths are referenced as local evidence. The package does not
copy, convert, train, or write dataset data.

## Human approval procedure

1. Review the JSON manifest and reconcile every source, split, code, output,
   and constants binding against the current checkout and locally available
   metadata.
2. Run the commands and checks listed in `pre_training_checks`.
3. Reject the package if any hash, split count, leakage result, code-state
   check, output-root check, or metric/imbalance declaration differs.
4. If all checks pass, record the human decision in a separate tracked
   authorization artifact under `docs/data/training-authorizations/`. That
   artifact must bind the same values and be accepted by the existing
   fail-closed preflight gate.
5. Only after that separate artifact is reviewed and committed may an operator
   prepare a fit-ready run manifest. This review package itself must never be
   changed from `training_authorized: false` to simulate approval.

## Current blocker

OpenHands sampled is ready for human authorization review, but it is not
training-authorized. The remaining blocker is an explicit human approve/reject
decision plus a tracked authorization artifact matching this package. No model
training, calibration, runtime integration, or output under `C:/pneuma-data` is
part of this review.
