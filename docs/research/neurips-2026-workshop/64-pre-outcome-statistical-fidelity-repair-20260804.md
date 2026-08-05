# Pre-outcome statistical fidelity repair — 2026-08-04

## Status

This is a prospective implementation correction, not a scientific execution or
result. No official task outcome, unblind material, benchmark run, pilot, claim,
or promoted receipt was read or created while making these changes.

The official study must not launch from an analysis image or signed run
specification that predates this repair. Production must rebuild the affected
role image, rerun the registered C120/C160 power finalisation, and bind the new
source/image/report digests into a fresh official run specification and
authorization.

## Corrected defects

1. The benchmark-stratified multiplier process applied an extra factor of one
   half, shrinking simulated max statistics and making simultaneous bounds too
   permissive. It now uses the same equal-benchmark weighting as the estimator.
2. The power finalisation path used two fixed 20-task synthetic benches and a
   fixed 1.96 critical value. It now evaluates the real candidate roster sizes,
   uses the registered benchmark-stratified Rademacher multiplier gate, and
   computes the Gaussian screen from the estimated two-contrast correlation.
3. Tier decisions were handed cell-level rows although the registered decision
   consumes four family-level worst-case rows. Cells are now conservatively
   aggregated before C120/C160 selection.
4. One unsupported leave-one-group-out dataset poisoned every dataset in a
   vectorised batch. Support failure is now local to the affected dataset.
5. `SHAM_PACKET_ONLY` used joint co-primary benchmark and leave-one gates when
   deciding whether the content estimand failed. It now uses content-specific
   benchmark and leave-one state.

The estimands, four arms, frozen nuisance grid, power/type-I thresholds,
practical threshold, resolution rule, and verdict precedence are unchanged.
This repair makes the implementation conform to those registered choices; it
does not tune them using outcomes.

## Mathematical clarification

The manuscript now states the rank-four contrast geometry explicitly. It calls
the sham contrast a packet-bearing intervention bundle rather than a pure
packet-form effect, separates the duplicate-control invariant and
anti-invariant coordinates, and records the exact conditional Rademacher
variance. A supplemental proof source is provided at
`paper/placebo_math_appendix.tex` but is not included in the main paper unless
the venue permits a supplement.

The audits' unsupported or design-changing suggestions were not adopted:
`q0` is not called an outcome variance; no new monotone resolution envelope was
inserted; no ordinary-classifier AUROC-to-total-variation theorem is claimed;
and no fifth-arm evidence/deception decomposition is presented as identified.

## Local verification

- Focused analysis and power tests: 53 passed under the Linux runtime.
- Ruff on the changed Python surface: passed.
- Schema test suite: passed.
- Canonical status checker: passed.
- Hardened LaTeX build: passed; `paper/main.pdf` is 10 pages.
