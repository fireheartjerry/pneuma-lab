# Session: foundation 8M stage — full train-supply run, gate passed, ladder stopped (2026-07-21)

Continuation of the 2026-07-20 2M session and the completed cloud 2M
reproduction. Everything in this session is local; paid compute $0; no cloud
resource created or contacted.

## Opening the 8m stage (commits `fef152f`..`d088dc1`)

1. **Design**: spec at
   `docs/superpowers/specs/2026-07-21-foundation-8m-stage-design.md` —
   local-only 8M at the standing 2e-4, cloud out of scope (the one lifetime
   reproduction job is consumed), 8m access matrix = exact 2m matrix.
2. **Policy/code** (`50c9c03`): the `payload_access_8m` column added to the
   suite policy contract — `suite.py` matrix/validator/report builders, the
   committed suite policy, `foundation-suite-report.schema.json`, the
   authorization policy-item keys, and the pinning tests. Full suite green in
   the WSL venv (2085 passed).
3. **Data-supply correction** (`d088dc1`): the measured selectable train
   supply is 22,189 records / 4,195,743 tokens — the 8M ceiling is
   unreachable from the two lanes; the pre-run ~19M-token estimate in the
   spec was wrong and was corrected to the measured truth.

## Determinism note (new operational knowledge)

Conversion reports embed `converter.git_sha`, whose hash feeds every
record's `source.receipt_hashes`, so record ids and shard digests are
**commit-bound**: the prepare-twice byte-identical proof must run both
passes at the same clean HEAD. A docs-only commit between passes produced a
different (equally valid) shard digest before this was understood.

## The 8M run

- prepare ×2 at HEAD `d088dc1`: byte-identical shard `7c346511…b403`
  (22,189 train records, 4,195,743 of the 8,000,000 ceiling — pool
  exhaustion, not ceiling; quarantine 240 cross-dataset-leakage + 259
  eval-repo-overlap validation records excluded from evaluation).
- Authorization scope digest
  `3c6018f9243e0f1ce54a97cff12967f03add155c31a7f0f838c9876df01077f0`,
  operator `student-operator`; preflight `ready: true` at 2e-4.
- Train @2e-4: run `foundation-8m-3c6018f9243e0f1c`, **693 optimizer steps,
  4,193,262 tokens**, best/last validation loss 0.0796/0.1584, 296.8
  tokens/s, peak 2.82 GiB process VRAM, peak 65 °C, zero thermal pauses.
  The wrapping WSL client was killed at step 593 (~86%); the exact
  optimizer-boundary `resume` from `checkpoint-00000593.pt` completed the
  run cleanly — the first real exercise of checkpoint resume on an
  authorized stage.

## Falsification gate: PASSED — doubling gate: STOPPED

The evaluation shard (22,189 train + 3,399 unquarantined validation
records, digest `1804ee26…`) was built by the same ad-hoc construction as
the 2m stage. `variant-eval` on the 3,399 repo-disjoint held-out tasks:

| Variant              | Resolved rate | p95 overhead | FLOPs overhead |
| -------------------- | ------------- | ------------ | -------------- |
| untouched_qwen       | 35.86%        | 0            | 0              |
| continued_deltanet   | 35.86%        | −14.5%       | 7.7e-06        |
| feed_forward_adapter | 35.86%        | −6.7%        | 5.5e-06        |
| pneuma_recurrent     | **64.14%**    | −4.2%        | 1.4e-05        |

`evaluate`: kill=false, +0.2827 absolute over the strongest baseline, CI95
[0.2504, 0.3151], zero gate failures — the same margin as 2M. The honesty
constraints are unchanged (held-out risk-prediction proxy semantics,
untrained pre-registered baselines, disclosed in every file; run-level
p95/FLOPs unmeasured by the trainer, variant-harness overheads carried in
`local_gate_report.json` with provenance).

**Doubling decision:** the held-out resolved rate is exactly equal to the
2M result — 2180/3399 = 0.6413651… at both stages, gain 0.0 points against
the pre-registered ≥0.5-point-per-doubling requirement.
`next_stage_decision("8m", …)` returns `None`: **the ladder stops at 8M.**
This is a recorded negative result, not a failure — 2.1× the gradient data
produced no measurable held-out gain on the proxy, i.e. the metric is
saturated for this architecture/data regime.

Artifacts: `build/foundation/runs/8m-2e-4/` (manifest, events,
validation_batches.json, evaluation_report.json, local_gate_report.json,
checkpoints through 693), `build/foundation/variants/8m/` (four variant
results + index), `build/foundation/variants/8m-eval-shard/`, and six
claim-bounded section reports under
`build/foundation/runs/foundation-8m-3c6018f9243e0f1c/reports/`.

## What would reopen the ladder

1. **New gradient lanes**: `multi-swe-bench` and/or `swe-evo` conversion
   lanes with their own readiness work (license receipts, adapters,
   leakage quarantine, suite-policy columns) — required even to reach the
   8M ceiling, and the only path to a meaningful 16M stage.
2. **A better proxy**: the resolved-rate proxy is saturated at 64.14%;
   doubling decisions may need a finer-grained held-out metric before more
   scale is justifiable.
3. **4B promotion decision**: the 2B falsification result is positive and
   reproduced; promotion to the 4B candidate remains a deliberate
   operator/schema decision, not an automatic consequence.
4. **Cloud 8M+**: blocked by design — one lifetime cloud job (used) and
   the $45 cap are hard-coded; enlarging that is an explicit reviewed
   change to `budget.py`, the authorization schema, and the bundle gates.

## Verification

- Full suite green in the WSL venv before the run (2085 passed, 3 skipped).
- `python -m pneuma_lab.status --check` and the operator-guide checker pass
  after the status/schema/title updates in this commit.
