# Step 4A to AWS Credit Launch Roadmap

**Status:** active execution roadmap  
**Prepared:** 2026-07-31  
**Scope:** work remaining from the completed bounded Step 4A lineage through
the first authorized use of the verified AWS credits

This document is the unambiguous numbered roadmap for the current phase. It
does not replace `docs/project-status.json`, the scientific contract, the live
Tasks 6-10 handoff, the decision log, the cloud spend ledger, or the append-only
execution journal. If those authorities conflict with this roadmap, stop and
reconcile them before execution.

## Current state

- Task 8 implementation/formal disposition: complete;
  `implementation_complete; E2E_pending`.
- Task 9 opaque executor and authority: complete;
  `implementation_complete; E2E_pending`.
- Task 8/9 integration: complete on the bounded production path.
- Step 4A miniature implementation-verification lineage: complete through
  registered analysis in commit `22e236a`.
- Task 6 revalidation against Step 4A: complete in commits `d16f948` and
  `9571fe4`; this proves implementation-path continuity only.
- Task 7 revalidation against Step 4A: complete in commit `c45a3d6`; this
  proves implementation-path continuity only.
- Step 4B canonical authority-backed P0 lineage: deferred, unrun as a complete
  lineage, and experiment-only.
- Task 10 implementation/release preparation: complete;
  `implementation_complete; E2E_pending`.
- AWS funding: $10,000 verified EC2-eligible credit plus a separate $100
  credit.
- AWS G/VT quotas: an authenticated console audit reports applied account-level
  values of 8 vCPUs On-Demand and 16 vCPUs Spot in `us-east-1`, which satisfy
  the DL-161 one-instance, 8-vCPU `g6e.2xlarge` topology. An account-bound
  Terraform plan and deployment receipt remain unapplied. Credits do not bypass
  quota, model-fit, throughput, protocol, or spend gates.

The preserved canonical root
`build/research/neurips-2026-workshop/p0-lineage-20260730` contains only 10 of
64 production shards. It is an incomplete non-result and must not be resumed,
rewritten, finalized, analyzed, deleted, or cited as evidence. Step 4B requires
a fresh root and a new per-run authorization.

## Phase A — close bounded implementation work

### [DONE] 1. Complete Task 7 revalidation against Step 4A

Revalidate the registered Task 7 inference and verdict path against the
completed Step 4A analysis artifact. Verify analysis ancestry, power-final
binding, registered randomness, endpoints, multiplicity, verdict construction,
schema validity, and deterministic receipt identity.

**Exit gate:** focused checks and exact receipt identities are journaled;
Task 7 remains honestly `implementation_complete; E2E_pending`. No Step 4B,
provider, benchmark, cloud, paid-compute, or scientific promotion occurs.

### [DONE] 2. Reconcile the bounded Task 6/7 continuity milestone

Merge the Task 6 and Task 7 revalidation work, resolve append-only journal
edits without rewriting history, and update the live handoff/status only where
the evidence justifies it.

**Exit gate:** both bounded continuity checks are recorded as complete, while
`B-NEURIPS-TASK6-E2E` and `B-NEURIPS-TASK7-E2E` remain open pending Step 4B.
This is not the scientific E2E promotion step.

### [DONE] 3. Complete Task 10 implementation and release preparation

Finish the Task 10 result-of-record machinery, independent verification path,
artifact packaging, failure classification, and release preparation using
bounded fixtures only.

**Exit gate:** Task 10 implementation is complete and capable of consuming a
future canonical lineage, but no result of record is claimed without Step 4B
and the authorized experiment.

## Phase B — make the real experiment launch-ready before quota

The following work can proceed without Step 4B and should be completed while
AWS quota approval is pending.

### 4. Freeze the real experiment design

- Finalize hypotheses, arms, endpoints, stopping rules, failure criteria, and
  admission gates.
- Select the stronger Qwen subject model and simulator configuration.
- Reconcile the benchmark roster before freezing it. The live handoff names
  SWE-bench-Live and τ³; proposals naming SWE-bench Verified or LiveCodeBench
  are alternatives, not silent substitutions.
- Freeze task subsets without outcome leakage.
- Record every design change through the scientific authority surfaces.

**Exit gate:** one internally consistent, reviewable design exists. No
benchmark roster or model choice remains ambiguous.

### 5. Lock external inputs

- Pin model and tokenizer revisions.
- Pin benchmark repositories, task manifests, container bases, and verifier
  sources.
- Record licenses, hashes, contamination checks, and provenance.
- Produce immutable candidate experiment manifests.

**Exit gate:** every scientific input can be retrieved and hash-verified
without consulting mutable tags or unrecorded local state.

### 6. Create the AWS architecture

- Define ECR repositories for immutable images.
- Define S3 namespaces for immutable inputs, logs, receipts, and results.
- Define DynamoDB or an equivalent lease/idempotency store.
- Define AWS Batch job definitions, queues, and compute environments.
- Define least-privilege IAM roles, VPC/network policy, and audit logging.

**Exit gate:** infrastructure is represented as reviewable code and can be
planned without provisioning GPU capacity.

### 7. Build deterministic containers

- Build separate model-serving, benchmark-worker, and controller/verifier
  images.
- Pin dependencies and base-image digests.
- Emit image digests and software bills of materials.
- Prove that scientific outputs bind to the exact images that produced them.

**Exit gate:** rebuilds are reproducible or deviations are explicit and
blocking.

### 8. Implement orchestration and interruption safety

- Implement submit, lease, resume, cancel, and terminal-state reconciliation.
- Allocate shards deterministically.
- Classify retries under the frozen protocol.
- Publish artifacts idempotently.
- Prevent duplicate scientific samples and result loss after interruption.

**Exit gate:** synthetic interruption and duplicate-delivery exercises produce
one valid terminal history or fail closed.

### 9. Implement spend protection

- Enforce per-job, per-phase, and lifetime dollar ceilings.
- Configure AWS Budget alarms as a secondary warning layer.
- Add runtime watchdogs and automatic termination.
- Require GPU-hour and dollar projections before launch.
- Forbid silent fallback to more expensive instance types or markets.
- Require a human approval receipt bound to exact manifests and cost ceilings.

**Exit gate:** no job can begin or continue beyond its authorized cost and
runtime envelope.

### 10. Implement evidence, blinding, and security controls

- Hash-bind every result to code, image, model, dataset, configuration, and
  authority.
- Preserve stdout, metrics, environment, timing, and failure receipts.
- Keep worker outputs blinded from analysis authority.
- Give workers only opaque assignments.
- Exclude arm identities, answer keys, and analysis thresholds from worker
  environments.
- Store secrets through AWS-managed secret mechanisms, never Git or images.
- Preserve resumable forensic journals.

**Exit gate:** malicious swaps, forged artifacts, stale leases, retries, and
role-boundary violations fail closed in bounded tests.

### 11. Build local and cloud emulation gates

- Run controllers against synthetic fixtures and mocked AWS APIs.
- Exercise interruption, duplicate delivery, corrupt output, expired leases,
  budget kills, and teardown.
- Use CPU-only or extremely small existing-capacity cloud jobs only when
  separately authorized.

**Exit gate:** the control plane is proven without consuming canonical P0 work
or meaningful GPU credit.

### 12. Prepare deployment and teardown artifacts

- Finish Terraform, CloudFormation, or CDK templates.
- Separate environment-specific configuration from immutable scientific
  inputs.
- Provide reproducible deployment, validation, and teardown commands.
- Add a quota/capacity preflight that refuses launch while applied quota is
  zero or insufficient.

**Exit gate:** a dry-run plan is reviewable, teardown is tested, and launch
remains fail closed.

### 13. Freeze the pilot protocol

- Define the smallest scientifically meaningful GPU smoke and pilot.
- Define exact pass/fail/escalation criteria.
- Set maximum cost, runtime, retries, and sample count.
- Bind the human approval receipt to the exact code, images, manifests, model,
  benchmark roster, and ceilings.

**Exit gate:** the pilot cannot quietly expand into the expensive experiment.

### 14. Perform the pre-experiment hostile launch review

Run independent leakage, statistical, security, cost, authority, and
reproducibility audits. Resolve every launch-blocking finding and produce a
signed launch-readiness report.

The campaign spec fails closed unless it binds eight genuine Phase B evidence
roots: Step 5B input lock, C120 G-ROSTER, Step 7B image builds/SBOMs,
production execution surface, AWS account/quota/plan, one-GPU admission,
interruption/recovery, and Windows/Linux receipt portability. Hashing a prose
claim or omitting either of the last two runtime gates cannot admit Step 14.

This is campaign 1 (`stage_1_pre_launch`) of the adversarial rejection-review
system, whose sole objective is to construct the strongest evidence-based case
for rejecting the work. Procedure, input contract, blocking rules, reviewer
prompts, replay process, and the human-override policy are in
`docs/research/placebo-review/00-operating-procedure.md`. Prepare the spec with
`python scripts/build_placebo_review_spec.py`, which pins the exact bytes the
reviewers read at the current commit.

It runs **after** Phase B Steps 4–13 and **before** Step 4B or any GPU
execution. Campaign 2 (`stage_2_pre_submission`) runs after results exist and
before submission.

**Exit gate:** implementation is launch-ready, but actual Step 4B and GPU
launch authorizations remain pending. A `no_blocking_findings` disposition is
**not** launch authority — the disposition says so in its own artifact. Launch
authority remains in the decision log and the spend gate.

## Phase C — run Step 4B as an explicitly authorized experiment

### 15. Issue a fresh Step 4B authorization

Create a per-run authorization bound to:

- the canonical frozen P0 contract and 64-shard topology;
- the exact commit and clean source state;
- the fresh physical run root;
- the host and runtime environment;
- the timing cap and decisive-lower-bound stop rule;
- the operator and start window; and
- the allowed outputs and forbidden claims.

Do not reuse the stopped 10-shard root.

**Exit gate:** authority verification passes before the first canonical screen
or shard starts.

### 16. Execute the fresh canonical P0 lineage

Run the admitted screen, all required production shards, selection, validation,
power finalization, schedule, prefixes, assignment, opaque packets, isolated
branches, task blocks, analysis freeze, blinded projection, gated unblind, and
registered analysis through the canonical authority.

Stop immediately with the registered formal disposition if a decisive timing,
integrity, authority, or scientific gate fails.

**Exit gate:** either one complete, verified canonical lineage exists or one
honest terminal failure/no-go record exists. Partial work is never promoted.

### 17. Complete scientific Task 6 and Task 7 revalidation

Revalidate Task 6 against the canonical freeze/projection/unblind lineage and
Task 7 against the canonical registered analysis. This is the real-lineage
counterpart to the earlier Step 4A continuity checks.

**Exit gate:** exact canonical receipts pass independent verification.

### 18. Decide Tasks 6/7 E2E promotion and finalize Task 10

Promote Tasks 6/7 only if the canonical evidence satisfies their complete
contracts. Produce the Task 10 result of record or the correct registered
negative/no-go disposition. Update status, handoff, journal, evidence package,
and claim boundaries together.

**Exit gate:** documentation does not outrun committed evidence; passing
software tests alone cannot satisfy this gate.

## Phase D — begin using the AWS credits

Step 4B is a scientific pre-launch gate; it does not itself authorize arbitrary
AWS spending. Credit use begins only after applied quota, launch readiness,
and a hash-bound spend authorization all pass.

### 19. Validate credits, quotas, and capacity

- Reconfirm that the $10,000 credit is active, unexpired, and eligible for the
  selected EC2/Batch resources.
- Verify the separately applied On-Demand and/or Spot G/VT quota in the target
  region.
- Verify selected instance availability and current pricing.
- Recompute the maximum pilot and experiment cost.

**Exit gate:** billing eligibility, applied quota, capacity, region, and cost
ceiling are recorded. A requested quota is not an applied quota.

### 20. Deploy and validate the AWS control plane

Deploy the reviewed infrastructure, push digest-pinned images, install immutable
inputs, validate IAM/network boundaries, and exercise monitoring, budget,
watchdog, and teardown paths without starting the scientific GPU pilot.

**Exit gate:** deployment receipts match the reviewed plan and teardown remains
available.

### 21. Run the cheapest authorized GPU smoke

Run the minimum non-scientific GPU-serving check needed to prove model load,
tokenizer parity, verifier connectivity, logging, artifact publication,
watchdogs, and teardown.

**Exit gate:** the smoke stays inside its small bound and creates no scientific
claim.

### 22. Run the bounded scientific pilot

Issue the pilot-specific human and spend authorization, then run exactly the
frozen pilot. Independently verify costs, failures, receipts, leakage controls,
and admission metrics before interpreting efficacy.

**Exit gate:** the registered pilot admission criteria pass. Failure stops the
program for correction or formal disposition; it does not trigger opportunistic
scaling.

### 23. Authorize the expensive experiment

Only after the pilot passes, issue a new authorization bound to the final
experiment hashes and dollar ceiling. Run the controlled inference evaluation,
not unplanned model training. Training is outside scope unless a separately
reviewed scientific design and spend authorization explicitly requires it.

**Exit gate:** the expensive experiment begins only with verified capacity,
immutable authority, intact blinding, enforced spend controls, and a recoverable
evidence trail.

## Parallel-work rules

- Task 7 Step 4A revalidation and Task 10 implementation preparation may run in
  parallel in separate worktrees.
- AWS architecture, containers, orchestration, spend controls, and emulation
  may proceed in parallel once their shared contracts are frozen.
- Shared status, handoff, decision-log, and append-only journal edits must be
  reconciled deliberately after parallel branches merge.
- Step 4B cannot run concurrently with changes to scientific code, manifests,
  images, frozen inputs, or analysis contracts.
- GPU smoke, pilot, and expensive execution are sequential authorization
  stages. A pass at one stage does not authorize the next.

## Immediate next actions

1. Reconcile the bounded Task 6/7 continuity milestone.
2. Complete Task 10 implementation and release preparation.
3. Start Phases B4-B13 while AWS quota approval is pending.
4. Run the hostile launch review.
5. Explicitly authorize and execute a fresh Step 4B.
6. Close scientific Tasks 6/7 and Task 10.
7. Validate applied quota and begin the smoke → pilot → experiment credit
   sequence.
