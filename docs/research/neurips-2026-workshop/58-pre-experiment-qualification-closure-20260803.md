# Pre-experiment AWS qualification closure — 2026-08-03

## Verdict

**B — post-launch terminal no-go.** Action
`dual-l40s-qualification-011` was launched exactly once. CloudTrail proves one
size-two Batch array with one permitted attempt. Both children became `FAILED`
with provider status reason `JobQueue deleted` and zero attempts. The required
two-worker qualification therefore did not pass; no retry or successor launch
was performed.

No official P0/Step 4B experiment, benchmark/model workload, pilot, subject
workload, unblind, scientific analysis, or claim promotion occurred.

## Sealed facts

- Immutable fixture-only image:
  `sha256:5433527fb588c009d6cf16a5ac4278c463bbb5fab0c0a6826147b4c98f2e83ff`
- IAM simulation: **pass**. Five exact input `GetObject` reads and two exact
  worker-indexed `PutObject` writes were allowed. Output reads, wrong-worker,
  other-action, unrelated-object, `ListBucket`, delete, abort, decrypt, and
  IAM administration were denied. Policy SHA-256:
  `73666739e4e41f136fd11049715130e9b5086e6cafc21cee642ebe179fb0f24b`.
- Plan hashes:
  - saved plan:
    `7c665827ed95bd4d55657e81ee9c2edf718f287cd58af325b4c714ce2b901ddc`
  - raw Terraform show:
    `01387c775cf497046bbcc4cc6a82b08052f836a127dca214660bacf03ed70141`
  - composite binding:
    `f4b627f943a0989222fd0aab53d8d01329ccca733de12135b54777914d5d0516`
- Authority hashes:
  - package:
    `8b3ae0892add4452464c00b0982f2dccc24a9a5cdf8dd944e6fa8783c8eddb7e`
  - envelope body:
    `606852028e73aafb61498e4b6e47e4428c33f81032c915901ba95b4198784c82`
  - admission body:
    `5cd6042eb58687c969d21dd54d03f0ed07116785ce5285a1aa399fefa6783016`
  - both signatures verified with `ED25519_SHA_512`.
- Spot projection: **USD 4.4842** for two `g6e.2xlarge` workers at 3,600
  seconds, below the USD 100 bound. Observed worker duration: **none**;
  neither child reached `STARTING`/`RUNNING`.
- Worker identity hashes: **none**. Raw artifact hashes: **none**; the
  action output prefix contains zero objects. Recovery: **not run**, because
  admission never reached two successful children.

## Teardown proof

Fresh AWS reads show no live action-scoped jobs, active job definition, queue,
compute environment, launch template, instance, volume, network interface, or
security group. AWS retains the deregistered `INACTIVE` job-definition revision
as provider history; it is not runnable. The initial verifier incorrectly
treated that history and terminal Batch job records as residual resources; the
narrow repair and focused regression now model AWS semantics correctly.

Receipt:
`evidence/dual-l40s-qualification-011-execution-receipt-20260803.json`
(SHA-256
`2452cc4a1a531e39bf170c038c8ba56829b57ea77b58ea532b2f61acb3990854`).
The receipt is now bound to
`cloud-ephemeral-dual-worker-qualification-receipt.schema.json`; direct
validation and the focused retry-drift regression pass.

## Concrete runner repair after hostile audit

The concrete runner previously emitted a legacy flat receipt shape and discarded
Batch child observations when admission failed. The repair now captures the
single CloudTrail `SubmitJob` evidence, preserves the parent and both child
status records through teardown, proves the output-prefix object count and
inactive job-definition history, and emits only the registered schema-bound
receipt after a submitted lifecycle. Pre-launch failures do not write a fake
execution receipt. Focused provider-free cloud/schema regressions pass; no AWS
resource was created and action-011 was not retried.

## Hostile closure review

The focused hostile review checked the actual receipt, ledger rows, runner,
image/plan bindings, IAM claims, single-launch boundary, and absence proof. It
confirmed the no-go and found no basis to call this a successful qualification.
It also noted that the literal cause of the queue deletion is not proven by
the retained evidence; this closure records only AWS Batch's observed status
reason and invents no root cause.

## Concrete runner readiness repair after the follow-up seam audit

A fresh read-only agent-session audit found two remaining concrete bypasses in
the executable path. The CLI accepted a caller-provided IAM-matrix digest
without performing the simulation, and the runner could be pointed at an
action ID already represented in retained evidence. Both are repaired:

- `iam simulate-principal-policy` now runs the fixed 15-case matrix derived
  from the parsed action plan: five exact input reads, two worker-indexed raw
  writes, and eight denied reads/writes/list/delete/abort cases. The retained
  record is sanitized, bound to the independently verified attached role and
  action-specific policy hash, and rehashed before apply and again at receipt
  serialization.
- The attached worker role ARN returned by the profile/read-role checks is
  carried into the parsed plan for IAM simulation; the instance-profile ARN is
  never substituted. Reuse of an action ID already present in the evidence
  directory, or overwrite of its receipt path, fails before provider mutation.

Focused provider-free IAM, runner, receipt, and schema regressions pass. This
was a source/readiness repair only: it did not create AWS resources, relaunch
action-011, or cross the official P0/Step 4B scientific boundary.

## Concrete seam and policy-source repair after the second audit

The next adversarial pass found and repaired four executable-path gaps without
launching AWS: the concrete Batch submit now sends and CloudTrail-verifies the
3,600-second attempt timeout; IAM simulation retrieves the real S3 bucket
policy and includes its canonical policy bytes in every simulation while
retaining only a sanitized digest; the runner independently fetches the live
KMS Ed25519 public key, matches it to the committed registry, and verifies both
authority signatures; and the authoritative spend ledger is part of the
action-freshness check. The future dual-L40S signing package now binds the
exact saved-plan/show/composite bytes together with the action policy hash,
immutable image digest, four-AZ subnet map, output prefix, fresh projection,
action id, and zero-retry limit.

The Terraform worker inline policy was also repaired at source: its S3
permissions are five exact fixture-input `GetObject` resources and two exact
worker-indexed raw-output `PutObject` resources, with no `ListBucket`, output
read, delete, decrypt, IAM, wildcard-resource, or multipart-abort grant. The
unrelated DynamoDB and managed role policies remain intact. Focused cloud,
signing, schema, and Terraform regressions pass. These changes improve the
next fresh qualification package; they do not alter the sealed action-011
no-go receipt or authorize a retry.

## Raw-show and live-policy binding repair

The final source audit repaired two smaller fail-closed seams without touching
AWS. Account-plan admission now requires the exact lowercase SHA-256 of the
raw Terraform-show bytes and reports a typed cloud error for missing or
malformed metadata. Before IAM simulation, the concrete adapter reads the
`bounded-experiment-access` inline policy from the provider-verified attached
worker role, canonicalizes only its digest, and rejects live policy drift from
the fresh action authority. A focused regression covers that rejection. The
dual-worker topology is now consistent in both permanent agent guides. Action
011 remains exhausted; there was no relaunch, provider mutation, or scientific
workload.

## Remaining blockers before the separately authorized official study

1. The dual-L40S qualification is not passed. Action 011 is exhausted; any
   future qualification attempt requires a fresh action and authority package.
2. Step 14 remains `launch_blocked`: the real authority-backed P0 power/tier
   receipt and packet, assignment, detectability, and unblind receipts are
   still missing from the canonical index.
3. Tasks 6–10 remain `implementation_complete; E2E_pending`; bounded Step 4A
   continuity, analysis, and Task 10 release preparation are not a scientific
   result of record.
4. The official P0/Step 4B authority, canonical lineage, execution, unblind,
   analysis, and claim-promotion gates remain separately authorized work and
   were not performed here.

The precise unsigned handoff checklist is
`59-unsigned-p0-step14-checklist-20260803.md`.
