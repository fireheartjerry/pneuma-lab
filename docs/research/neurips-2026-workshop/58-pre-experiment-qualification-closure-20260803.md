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

## Hostile closure review

The focused hostile review checked the actual receipt, ledger rows, runner,
image/plan bindings, IAM claims, single-launch boundary, and absence proof. It
confirmed the no-go and found no basis to call this a successful qualification.
It also noted that the literal cause of the queue deletion is not proven by
the retained evidence; this closure records only AWS Batch's observed status
reason and invents no root cause.

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
