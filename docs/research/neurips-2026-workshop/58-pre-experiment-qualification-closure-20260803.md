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
  writes, and eight denied reads/writes/list/delete/abort cases. The future
  path adds two more denied checks for KMS decrypt and IAM policy
  administration (17 fixed checks total); the sealed action-011 record remains
  the historical 15-case matrix. Every retained record is sanitized, bound to
  the independently verified attached role and action-specific policy hash,
  and rehashed before apply and again at receipt serialization.
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

## Plan/show consistency hardening

The future qualification runner now fails closed on malformed or conflicting
Terraform-show digest metadata, and the locked apply re-read reports an
explicit cloud error before mutation if its raw-show digest is unavailable or
invalid. A focused regression covers conflicting plan/show metadata. This is
source-only hardening; action-011 remains exhausted and unchanged.

## Runtime and IAM boundary hardening

The future fixed image path now requires the action ID, artifact prefix, and
output-root environment variables to agree on the exact
`.../<action-id>/outputs/` prefix before any fixture input is materialized or
published. Terraform-show admission now also requires a managed Batch compute
environment and rejects a custom AMI field nested in compute resources. The
IAM simulation adds explicit denied checks for KMS decrypt and IAM policy
administration. Focused probe, runner, Terraform, IAM, and image-fixture tests
pass; this does not alter the sealed action-011 terminal no-go.

## Source/image and plan-semantics closure repair

The next source-only audit repaired three remaining fail-open seams. Future
qualification signing now rejects conflicting IAM policy-hash representations
instead of selecting the first truthy field. Terraform-show admission requires
`us-east-1`, a concrete VPC binding, and no `command`, `entrypoint`, or
`entryPoint` override that could erase the image ENTRYPOINT. The concrete
ephemeral runner now requires the immutable fixture-image digest to match
exactly one complete build receipt whose ECR immutability, AWS CLI v2, package,
schema, fixed-entrypoint, network-none, no-model, five-input, and immutable
worker-artifact checks pass.

The sealed action-011 image digest
`sha256:5433527fb588c009d6cf16a5ac4278c463bbb5fab0c0a6826147b4c98f2e83ff`
was built from source commit
`e36dd15ac2524c29d0fb02a8705ec7fcc48fb34a`, while these post-launch source
repairs are newer. The digest and receipt remain valid historical evidence;
the new runner will correctly refuse to reuse that source/image pair for a
future action. No rebuild, relaunch, retry, or AWS mutation was performed.
Focused image, signer, plan, runner, qualification, and account-verification
tests pass.

## Direct-runner and binding-source closure repair

The next source-only audit closed a direct API freshness bypass: callers that
omit an evidence directory now use the repository's authoritative evidence
root, so an exhausted action cannot be replayed by calling `execute()`
directly. Concrete teardown now disables the queue and compute environment
before draining the submitted Batch parent and both array children, with one
bounded termination request only after the drain window expires. The parser
also requires both top-level and nested exact raw Terraform-show hashes,
exact action tags on compute, launch-template, queue, and job resources, and a
single order-1 queue-to-compute binding. The signing path rejects conflicting
image, subnet, output, projection, and retry representations rather than
choosing a first truthy source, and requires the exact composite plan binding
for a dual-L40S qualification package.

Focused runner, parser, signer, IAM, receipt, image, AWS-account, and Ruff
checks pass. This was source-only closure work: action 011 remains exhausted,
there was no AWS mutation or retry, and the official scientific boundary is
unchanged.

## Remaining blockers before the separately authorized official study

1. The dual-L40S qualification is not passed. Action 011 is exhausted; any
   future qualification attempt requires a fresh action and authority package,
   plus a fresh immutable image receipt bound to the current source revision.
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
