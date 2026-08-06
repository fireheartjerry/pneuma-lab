# Rapid Experiment Campaign Orchestrator Implementation Plan

> **For agentic workers:** Execute task-by-task with the `executing-plans`
> workflow. Preserve the prepared r2 action and all unrelated untracked
> evidence. No task may modify the frozen runtime images or C120 receipt.

**Goal:** Implement the autonomous, USD 7,500-capped launch -> results ->
analysis -> hostile review -> accept/redesign loop described in the approved
God Mode design, then import the exact prepared r2 action without rebuilding
or rerunning C120.

**Architecture:** Add an isolated `pneuma_lab.rapid_campaign` package. Canonical
records and a hash-chained state store drive a restartable orchestrator through
pluggable execution, analysis, review, and amendment adapters. The official
adapter shells out to the unchanged, already reviewed Batch submission and
cleanup scripts; local fakes prove the complete loop before any AWS mutation.

**Tech stack:** Python 3.12 stdlib, JSON Schema 2020-12, existing cloud and
adversarial-review packages, boto3 only in the existing launch surface, pytest,
Ruff.

---

## File map

- Create `schemas/rapid-campaign-manifest.schema.json` and
  `schemas/rapid-campaign-version.schema.json`: closed campaign/version
  contracts.
- Create `src/pneuma_lab/rapid_campaign/records.py`: strict immutable records,
  canonical encoding, loading, and digest verification.
- Create `src/pneuma_lab/rapid_campaign/impact.py`: C0-C4 invalidation engine.
- Create `src/pneuma_lab/rapid_campaign/spend.py`: reservation/observation
  ledger with the USD 7,500 invariant.
- Create `src/pneuma_lab/rapid_campaign/store.py`: mode-600 atomic hash-chained
  event store and restart reconciliation state.
- Create `src/pneuma_lab/rapid_campaign/decision.py`: scientific decision
  policy that separates validity from favorability.
- Create `src/pneuma_lab/rapid_campaign/orchestrator.py`: adapter protocols and
  resumable campaign state machine.
- Create `src/pneuma_lab/rapid_campaign/adapters.py`: command adapters, official
  r2 import/launch surface, sealed-output collection, analysis, hostile review,
  and teardown integration.
- Create `src/pneuma_lab/rapid_campaign/cli.py`, `__main__.py`, and `__init__.py`:
  `godmode init/status/dry-run/run/inspect/stop`.
- Create `tests/rapid_campaign/`: focused records, impact, spend, state,
  decision, adapter, and provider-free E2E tests.
- Modify `src/pneuma_lab/schemas/__init__.py`: register the two schemas.
- Modify `docs/project-status.json`: register implementation state without
  claiming the scientific experiment ran.

### Task 1: Freeze records, invalidation, and spending semantics

- [ ] Write failing tests for strict manifest/version records, immutable parent
  digests, C0-C4 dependency closure, C120 reuse, and cumulative cost accounting.
- [ ] Run only `tests/rapid_campaign/test_records.py`,
  `test_impact.py`, and `test_spend.py`; confirm RED.
- [ ] Add the two schemas plus `records.py`, `impact.py`, and `spend.py`.
- [ ] Require `observed + outstanding reservations <= ceiling`, retain unknown
  reservations, reject any new reservation over the remainder, and enforce the
  tighter of the campaign remainder and each version's immutable authorization
  ceiling (USD 5,100 for r2).
- [ ] Run focused tests, focused Ruff, schema loading test, and `git diff
  --check` within 60 seconds each.
- [ ] Commit the slice.

### Task 2: Build the durable state machine and decision firewall

- [ ] Write failing tests for every state transition, hash-chain tampering,
  restart, one immutable submission identity, observation errors, teardown
  ordering, and terminal states.
- [ ] Write decision tests proving valid unfavorable/null results can be
  accepted and cannot trigger a rerun merely for favorability.
- [ ] Implement `store.py`, `decision.py`, and `orchestrator.py` with injected
  provider/analysis/review/amendment protocols.
- [ ] Preserve successful submission across observation errors and make
  analysis/review failures resume their own phase without relaunch.
- [ ] Run the focused state/decision/orchestrator tests and static checks.
- [ ] Commit the slice.

### Task 3: Add the CLI, truthful progress surface, and local full-loop proof

- [ ] Write failing CLI tests for `init`, `status`, `dry-run`, `run`, `inspect`,
  and `stop` plus stable JSON output.
- [ ] Implement the CLI and a terminal renderer that reports only actual state,
  provider events, costs, and artifact counts; no fabricated percentage or ETA.
- [ ] Add fake adapters that simulate success, operational failure, valid null,
  invalid favorable result, analysis retry, review retry, and budget exhaustion.
- [ ] Prove one provider-free E2E loop, including one justified successor and
  teardown, without AWS or scientific claims.
- [ ] Run focused CLI/E2E tests and static checks.
- [ ] Commit the slice.

### Task 4: Bind the unchanged official r2 launch and teardown surfaces

- [ ] Write failing adapter tests with fake subprocess/AWS discovery transports.
  Assert exact action, package, run-spec, image-set, source commit, account,
  region, and receipt bindings from the final launch review.
- [ ] Implement r2 import from
  `official-study-final-launch-review-20260806.json` plus a private package path
  supplied at `godmode init`; verify bytes before recording the version.
- [ ] Invoke the existing `scripts/research/submit_official_batch.py` and
  `cleanup_official_batch.py` without editing either file.
- [ ] Reconcile lost submit output by exact action-owned names/tags. Never call
  the submission script twice for one version.
- [ ] Collect action-owned S3 output keys into a canonical sealed index before
  teardown; retain scientific evidence while removing active resources.
- [ ] Run focused adapter tests and the existing official submission/cleanup
  tests.
- [ ] Commit the slice.

### Task 5: Integrate registered analysis, hostile review, and amendments

- [ ] Write failing adapter tests for sealed-output-only analysis, replayable
  analysis commands, adversarial-review input construction, and decision
  translation.
- [ ] Implement a digest-bound command adapter for the registered analysis
  graph; its output must be a version-owned result bundle.
- [ ] Build a post-result `pneuma_lab.adversarial_review` campaign over the
  version, raw index, analysis, protocol, claims, environment, and receipts.
- [ ] Implement amendment proposals as immutable child versions passed through
  the C0-C4 classifier. Regenerate only invalidated dependencies; C4 is the sole
  route that can require new power evidence.
- [ ] Prove analysis/review-only recovery causes zero provider submissions and
  that exploratory children cannot be relabeled confirmatory.
- [ ] Run focused tests and static checks.
- [ ] Commit the slice.

### Task 6: Reconcile status and dry-run the exact campaign

- [ ] Add God Mode implementation status and evidence references to
  `docs/project-status.json` without changing official experiment execution
  status before a real submission.
- [ ] Run the status checker, rapid-campaign suite, existing official
  submission/cleanup tests, focused adversarial-review tests, Ruff, schema
  validation, and `git diff --check`; keep every software command under 60
  seconds.
- [ ] Initialize a local private campaign around
  `official-p0-step4b-c120-20260806-r2`, ceiling USD 7,500, and the exact package
  SHA `1ced6e56db66da1949ac1f9ec4f355c890f5c87dbcace6de49876ee54c05adf1`.
- [ ] Run `godmode dry-run` and prove it schedules no C120 replay, no image
  rebuild, and no frozen-input regeneration.
- [ ] Commit and push the implementation and tracked non-scientific evidence.
- [ ] Start the real campaign only through the mutating `godmode run` surface;
  report the exact submitted action/job identity immediately and continue
  monitoring without duplicate submission.

## Completion boundary

Implementation is complete only when Tasks 1-6 pass. A successful local loop
is software evidence, not a scientific result. The experiment becomes
`submitted` only after AWS returns one action-bound submission identity, and it
becomes scientifically complete only after sealed outputs, registered analysis,
and the result decision exist.
