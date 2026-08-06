# Rapid Experiment Campaign Orchestrator Design

## Goal

Build a separate, resumable control plane for ultra-fast PLACEBO experiment
iteration. The operator-facing name is **God Mode**; the implementation name is
the **Rapid Experiment Campaign Orchestrator** (RECO).

RECO owns the campaign loop:

1. launch an immutable experiment version;
2. collect and seal its raw outputs;
3. run its registered analysis and prepare paper-facing evidence;
4. run an evidence-grounded hostile review;
5. accept the result or create a justified successor version; and
6. repeat autonomously until acceptance, a terminal scientific no-go, an
   external provider failure, or the campaign spending ceiling.

The first version is the already authorized C120 action
`official-p0-step4b-c120-20260806-r2`. RECO must consume that version exactly as
prepared. It must not rewrite its package, authorization, run specification,
images, power receipt, or action identity.

## Standing campaign policy

The campaign receives autonomous authority to build, launch, observe, analyse,
review, amend, and rerun experiment versions within these bounds:

- cumulative AWS ceiling: **USD 7,500** across the whole campaign;
- the ceiling includes image builds, pilots, official versions, failed
  launches, storage, and teardown work attributable to the campaign;
- every charge or conservative projection is debited before the next mutation;
- the ceiling is cumulative, never refreshed per version;
- an iteration may not begin unless its conservative projected cost is less
  than or equal to the unreserved remainder;
- live observed/provider cost replaces its reservation when available;
- reaching the ceiling stops new mutations and triggers teardown; and
- credits may reduce the bill but never increase the USD 7,500 control limit.

Each experiment version also retains its own immutable authorization ceiling.
The effective launch limit is the minimum of the version ceiling and the
campaign's unreserved remainder. In particular, prepared r2 remains bounded by
its signed USD 5,100 maximum even though the campaign-wide ceiling is USD 7,500.

AWS billing and budgets are delayed signals, not atomic circuit breakers. The
software therefore enforces the limit using pessimistic pre-launch reservation,
an append-only local spend ledger, provider observations, and immediate
teardown. The design does not claim that AWS can prevent every cent of
eventual delayed charge.

This standing policy removes repeated human authorization from ordinary
campaign iterations. It does not authorize unrelated training, other projects,
credential export, destructive account-wide operations, paper submission, or
scientific misrepresentation.

## Chosen architecture

RECO is an isolated package under `src/pneuma_lab/rapid_campaign/` with a thin
CLI entry point. It wraps existing execution and review surfaces through narrow
adapters. It does not extend the signed runtime containers and does not modify
the current production controller.

The alternatives were rejected:

- A raw shell loop would be quick to type but would lose crash recovery,
  version identity, spend accounting, and defensible result provenance.
- Adding the loop to `ProductionOrchestrator` would couple scientific policy to
  one AWS action and force unnecessary image/package rebinding.

The isolated controller keeps campaign policy local while each scientific run
remains immutable and independently reproducible.

## Core records

All durable records use canonical JSON, explicit schema versions, SHA-256
content identities, atomic writes, and append-only event history.

### Campaign manifest

The manifest binds:

- campaign ID and parent study identity;
- USD 7,500 cumulative ceiling and currency;
- allowed AWS account, region, resource classes, and resource-tag namespace;
- initial version and exact prepared action bindings;
- accepted change-impact policy version;
- analysis and hostile-review adapters;
- stop conditions, deadline, and teardown policy; and
- current immutable version head.

The manifest stores no AWS secret or private credential.

### Experiment version

Every version is a node in an immutable directed acyclic graph. It binds:

- version ID, parent version, and amendment rationale;
- hypothesis status: `confirmatory`, `exploratory`, or `operational_repair`;
- protocol, roster, assignment, packet, task-block, model, benchmark, RNG,
  image, analysis, budget, and run-spec digests;
- the exact authority and package when required by its launch adapter;
- declared evaluation criteria established before launch;
- impact classification and invalidated artifact set; and
- launch, output, analysis, review, and decision receipt references.

No successor may edit or delete its parent. A failed or unfavorable run remains
part of the campaign history.

### Campaign event log

Events form a hash chain and monotonically increasing sequence. Event types
cover preparation, reservation, submission, observation, sealed output,
analysis, review, decision, amendment, teardown, provider error, and terminal
stop. Restarting the CLI reconciles this log with provider state before doing
anything new.

### Spend ledger

The spend ledger records projected reservations and observed replacements by
version and AWS resource. The invariant is:

`observed charges + outstanding conservative reservations <= USD 7,500`.

Unknown costs retain their full reservation. Failed observations never erase a
reservation. Manual reconciliation may lower a reservation only with a bound
provider receipt.

## State machine

Each version progresses through:

`draft -> classified -> prepared -> submitted -> observing -> outputs_sealed -> analysed -> reviewed -> decided -> teardown_complete`

Observation errors are retryable observations, not new submissions. Submission
uses the existing action identity and provider idempotency. A version can have
exactly one immutable scientific submission unless its decision creates a new
version.

Terminal decisions are:

- `ACCEPT_VALID_RESULT`: the run is valid and sufficiently informative for its
  declared question, regardless of whether the effect is favorable;
- `REDESIGN_OPERATIONAL`: execution or evidence integrity failed and a minimal
  operational repair is justified;
- `REDESIGN_SCIENTIFIC`: the design was valid but insufficiently informative;
  the successor is explicitly labeled and cannot overwrite the result;
- `TERMINAL_SCIENTIFIC_NO_GO`: no defensible successor is available within the
  registered decision rules or remaining budget;
- `EXTERNAL_BLOCK`: provider/account/capacity state prevents meaningful
  progress; and
- `BUDGET_EXHAUSTED`: no new mutation fits under the remaining ceiling.

Teardown is attempted after every terminal workload state and on every stop
path. Evidence objects and inactive provider history may remain when explicitly
declared; active compute and campaign-owned mutable infrastructure may not.

## Minimal invalidation engine

RECO computes the transitive artifact impact of a proposed amendment before it
does work. The purpose is to avoid repeating expensive ceremony that the change
cannot invalidate.

| Change class | Examples | Required regeneration |
|---|---|---|
| C0: reporting | prose, tables, plots, paper mapping | analysis/paper artifacts only; no launch |
| C1: control plane | dashboard, observer retry, campaign policy code | control-plane checks only; no images or power |
| C2: launch surface | Batch wiring, resource size, teardown adapter | affected provider/package receipts; power only if scientific exposure changes |
| C3: runtime/input | model, benchmark adapter, task data, packet, assignment, image code | affected seals, images/SBOMs, run spec, package, and authorization |
| C4: power-critical | eligible roster, sample size, estimand, effect target, allocation, stopping rule, power RNG | C3 work plus a new applicable power result |

The frozen C120 power result is reused unless a C4 dependency changes. A commit
hash alone is not power-critical. Paper edits, dashboard work, controller
retries, packaging repairs, and equivalent image rebuilds do not rerun C120.

The classifier emits both the selected class and a machine-readable dependency
proof. Ambiguity selects the higher-impact class rather than silently reusing
stale evidence. A dry-run command shows the exact regeneration set and cost
projection before mutation.

## Execution adapters

The first launch adapter calls the existing verified surface in
`scripts/research/submit_official_batch.py` with the exact prepared r2 action,
package, package digest, run-spec digest, and production image set. It captures
the returned submission receipt before observation begins.

The adapter must not reimplement AWS resource construction. Observation and
cleanup reconcile action-owned Batch, EC2, network, IAM, S3, and evidence state
using the existing production controller and cleanup semantics. Provider
errors are classified as observation, capacity, permission, or terminal
workload errors; an observation error never causes a second submission.

Later versions use the same adapter interface but supply their own immutable
version bindings. An adapter can be replaced without changing scientific
inputs when the invalidation engine proves equivalence.

## Output and analysis pipeline

Raw provider outputs are downloaded to a version-specific staging directory,
validated against the run specification, hashed, and sealed read-only before
analysis. Analysis reads only the sealed output index and the version's
registered analysis graph.

The analysis adapter emits:

- machine-readable result tables and estimator diagnostics;
- registered primary and secondary outcomes;
- resolution-floor and sensitivity diagnostics;
- exclusions, failures, OOMs, timing, and missingness accounting;
- paper-facing tables/figures with source digests; and
- a concise interpretation that distinguishes evidence, inference, and
  unregistered exploration.

Paper integration produces a proposed patch or result bundle. It never silently
rewrites claims or promotes exploratory findings to confirmatory results.

## Hostile evaluator and decision policy

RECO reuses `pneuma_lab.adversarial_review` as an evidence-grounded evaluator.
The campaign input set includes the immutable version, raw-output index,
analysis products, protocol, claims, environment, and receipts. Reviewer
findings retain their original evidence and severity semantics.

The campaign decision engine is deliberately separate from the reviewer. The
reviewer identifies grounded validity, interpretation, reproducibility, and
paper-risk findings; it does not authorize spending or select a desired answer.

The decision engine may redesign only when at least one preregistered condition
holds:

- the run is operationally invalid or incomplete;
- required evidence is missing or internally inconsistent;
- the registered design cannot resolve its stated question;
- a hostile finding identifies a correctable causal, leakage, power, or
  measurement defect; or
- the result supports a new explicitly exploratory hypothesis whose successor
  is labeled accordingly.

An unfavorable effect, null result, or failed claim is not itself a redesign
condition. The engine must not search versions until statistical significance,
discard versions, change the primary outcome after seeing it, or call the best
observed version confirmatory. Data-informed confirmatory successors require a
fresh independent evidence allocation when the scientific contract demands it.

## Operator experience

The CLI exposes:

- `godmode init`: create and validate the campaign manifest around r2;
- `godmode status`: show version, state, spend, remaining budget, provider
  state, current decision, and next action;
- `godmode dry-run`: display impact, work avoided, projected cost, and exact
  mutations;
- `godmode run`: resume the autonomous loop from durable state;
- `godmode inspect`: open a version's bindings and evidence index; and
- `godmode stop`: stop new work, reconcile state, and teardown owned resources.

`run` is foreground-visible by default and emits structured JSON Lines plus a
stable terminal dashboard. Every phase has a real provider- or artifact-backed
progress signal; fabricated percentages and synthetic ETAs are forbidden.

The orchestrator is safe to stop and restart. Ctrl+C records the interruption,
stops new submissions, and begins bounded teardown unless the workload has an
explicit preserve-and-resume policy.

## Error handling and recovery

- Input or digest mismatch: fail before reservation or mutation.
- Cost cannot be bounded: do not launch; retain the reservation rationale.
- Submit response lost: reconcile by idempotency token and tags; never blindly
  resubmit.
- Observation failure: preserve submission identity and retry observation with
  bounded backoff.
- Workload failure: seal diagnostics, teardown, review, then decide whether a
  new operational-repair version is justified.
- Analysis failure: preserve raw outputs and rerun analysis without relaunching.
- Reviewer failure: preserve analysis and rerun only the reviewer.
- Teardown failure: stop new campaign mutations and continue action-owned
  cleanup until success or a genuine external block.

## Security and scope

God Mode is powerful inside one campaign, not an unbounded account shell. AWS
mutations require the campaign tag namespace, allowed account and region, and
the declared resource classes. The orchestrator cannot mutate unrelated
resources, expose credentials, broaden IAM without a versioned provider need,
or delete retained scientific evidence.

This is the practical form of full autonomy: no repeated semantic permission
loops, but strong scope, cost, provenance, and teardown invariants. Removing
those invariants would make iteration less reliable, not faster.

## Verification strategy

Implementation uses narrow, high-signal tests within the repository's software
test ceiling:

1. transition and restart/idempotency tests;
2. exact C0-C4 invalidation matrix tests, including C120 reuse;
3. cumulative reservation/observed-cost invariants at the USD 7,500 boundary;
4. one-submit behavior under lost responses and observation errors;
5. raw-output sealing and analysis-only recovery;
6. decision tests proving that unfavorable results cannot trigger reruns;
7. immutable version-DAG and lineage tests;
8. teardown-on-stop/failure ordering; and
9. a provider-free end-to-end campaign simulation.

An AWS mutation is not needed to prove the control plane. After local
verification, the already prepared r2 action is the first real campaign
version and its launch remains a separately visible event in the campaign log.

## Delivery slices

1. Schemas, canonical records, version DAG, spend ledger, and impact engine.
2. Durable state machine, CLI, dashboard/event stream, and local fake adapters.
3. Existing official Batch launch/observe/cleanup adapter and exact r2 import.
4. Output sealing, registered analysis, paper-result bundle, and hostile-review
   adapter.
5. Decision engine, successor amendment builder, autonomous resume loop, and
   provider-free end-to-end verification.
6. Dry-run the exact r2 campaign, verify its USD reservation and mutation plan,
   then run only when the operator invokes the mutating `godmode run` command.

## Acceptance criteria

RECO is ready when:

- it imports r2 without changing any frozen digest;
- `godmode dry-run` identifies no unnecessary C120, image, or input rebuild;
- the full local loop survives process interruption without duplicate launch;
- every version and result remains inspectable and hash-bound;
- the spend invariant holds across success, failure, and unknown-cost paths;
- hostile review can accept a valid negative result and reject an invalid
  favorable result;
- analysis/review repairs never relaunch a scientific workload;
- scientific amendments regenerate only the dependencies they invalidate; and
- all stop paths reconcile and teardown campaign-owned active resources.

This design changes no scientific result and authorizes no claim. It creates the
fast, autonomous machinery that executes and iterates the experiment without
repeating irrelevant work or sacrificing the paper's evidentiary integrity.
