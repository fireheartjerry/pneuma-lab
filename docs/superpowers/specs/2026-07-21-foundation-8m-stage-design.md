# Foundation 8M stage — design (2026-07-21)

## Goal

Run the 8M-token local training stage of the Qwen3.5-2B foundation ladder to
completion, under the same exact-operator-authorization discipline as the
100K/500K/2M stages, and record the gate outcome that decides 16M
reachability.

## Preconditions (all verified)

- The 2M falsification kill gate PASSED (+28.3 points absolute, CI95 strictly
  above zero), so `next_token_stage(2_000_000, falsification_gate_passed=True)`
  returns 8,000,000.
- Data supply (measured at preparation, correcting the pre-run estimate):
  the two approved gradient lanes yield 22,189 selectable train-split
  records totalling 4,195,743 tokens. The 8M ceiling is therefore
  unreachable from the current lanes; the stage runs over the full 4.2M
  train supply — 2.1x the 2M run — and the data-bound-ladder finding
  first recorded at 500K is re-confirmed at 8M. Reaching the ceiling
  requires the `multi-swe-bench`/`swe-evo` conversion lanes (out of
  scope).
- Evaluation, budget, preparation, authorization, CLI, and curriculum code
  already accept the `8m` stage; the ONLY fail-closed gap is the suite
  policy, which has no `payload_access_8m` column.

## Decisions

1. **Local, not cloud.** The one-lifetime cloud reproduction job is consumed
   (2M, under $2). A cloud 8M would require a deliberate reviewed change to
   `budget.py` and the cloud gates; that decision is left to the operator and
   is out of scope here. Local 8M is $0 and ~7 h at the measured
   312-339 tokens/s.
2. **Learning rate 2e-4**, the standing lowest-validation-loss selection from
   the 100K smoke trials, unchanged since.
3. **8m access matrix = 2m access matrix.** The `payload_access_8m` column
   duplicates the 2m column exactly: the two approved processed lanes stay
   open, `multi-swe-bench`/`swe-evo` stay `metadata_only` until their own
   conversion lanes earn readiness, eval/governance families stay
   metadata/identity-only and are never trained on.
4. **Fresh full run, not a resume.** Each ladder stage trains from the pinned
   base snapshot over its own stage-keyed shard, matching all prior stages.

## Change set (code and contracts)

- `src/pneuma_lab/foundation/suite.py`: extend `_EXPECTED_FAMILY_MATRIX`
  rows with the 8m access value, the exact-match validator, and both report
  builders.
- `docs/data/training-readiness/pneuma-foundation-v0-suite.json`: add
  `payload_access_8m` per family.
- `schemas/foundation-suite-report.schema.json`: add `payload_access_8m`
  wherever `payload_access_2m` appears (required lists and per-family
  property blocks).
- `src/pneuma_lab/foundation/authorization.py`: include `payload_access_8m`
  in the reconstructed suite-policy item keys.
- Tests pinning the matrix/report/policy updated accordingly.

## Execution (WSL, per the drift-checked runbook)

prepare ×2 (byte-identical) → authorization-candidate → authorization-finalize
(operator `student-operator`, freshly displayed scope digest and approval
phrase) → preflight → train at 2e-4 → variant-eval (four variants on the last
checkpoint over repo-disjoint held-out records) → evaluate (kill gate +
regression gate) → report.

## Gate semantics after the run

16M is reachable only if the held-out resolved rate improves by ≥0.5 absolute
points over the 2M result (64.14%) with a stable run and a passing regression
gate. A flat or worse result is a valid negative result and stops the ladder;
it is recorded, not retried.

## Out of scope

Cloud 8M budget changes, third-lane (`multi-swe-bench`/`swe-evo`) readiness,
4B promotion, any runtime promotion, any consciousness claim.
