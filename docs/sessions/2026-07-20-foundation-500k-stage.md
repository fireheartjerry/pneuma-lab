# Session: foundation 500K stage (2026-07-20)

Operator-directed continuation of the local training ladder after the
completed 100K smoke stage. All work local; paid compute remains $0; no
cloud resource was created.

## What ran

1. **500k stage enablement** (commit `0104b77`): the suite policy, expected
   family matrix, suite-report schema, and authorization scope copy gained an
   explicit `payload_access_500k` column with values identical to the 100k
   column. Only the approved OpenHands-Sampled swe-gym lane opens payloads;
   2m-and-later stages stay fail-closed until their own column lands.
2. **Coherence-gate fix** (commit `13fbba4`): the candidate coherence gate
   required the suite report `first_stage.stage` to equal the run stage,
   which only ever held at 100k. It now pins `first_stage` to `100k` and
   requires a string `payload_access_<stage>` per family for the run stage.
   Regression case added to
   `tests/test_foundation_authorization.py`
   (`suite_stage_access` contradiction).
3. **500K run** under a fresh exact authorization (scope digest
   `b4b5f1da90aff5abbec57fdbaec9e8f8a6a1755944ee96234e43eecf8732f5a2`,
   operator `student-operator`, code commit `13fbba4`):
   prepare twice (candidate byte-identical,
   shard `52c2201a…d0d8`), scope reviewed, finalize, preflight READY,
   train at the selected 2e-4.

## Result

| Run          | Steps | Tokens seen | Best val loss | Last val loss |
| ------------ | ----- | ----------- | ------------- | ------------- |
| `500k` @2e-4 | 32    | 200,874     | 3.8832        | 3.9076        |

Run id `foundation-500k-b4b5f1da90aff5ab`; artifacts under ignored
`build/foundation/runs/500k-2e-4/` (manifest, events, checkpoint-00000032).
Formal `evaluate` remains blocked by the known missing
`validation_batches.json` persistence (aggregate best/last loss only).

## Finding: the ladder is data-bound

The OpenHands-Sampled lane yields 6,055 converted examples across only 6
repositories. Repo-grouped splitting leaves a 202,162-token train split;
the greedy selector packed all of it (1,031 records) under the 500K
ceiling, and the single-pass trainer consumed it entirely (200,874 tokens).
Consequences, recorded in `START-HERE-TRAINING.md` and
`docs/foundation/cloud-training-handoff.md`:

- The 500K ceiling (and all later ceilings) is unreachable from the single
  authorized lane.
- A 2M run over the same lane would re-train the identical shard; it was
  deliberately not run.
- Meaningful 2M+ requires multi-lane readiness work
  (`multi-swe-bench`, `open-swe-traces`, `swe-evo` conversion lanes plus a
  multi-lane candidate/authorization redesign) and, for the kill gate, the
  four-variant paired evaluation harness (does not exist).
- The ten-family suite is fully exercised in its policy roles: the one
  gradient-eligible lane trained to data exhaustion, the three eval
  identity families gated contamination, and the governance families were
  probed by metadata only and never opened.

## Verification

- Full suite after enablement: 1932 passed, 3 skipped.
- Focused authorization/suite tests after the gate fix: 367 passed.
- Prepare determinism: two runs, byte-identical candidate SHA-256.
