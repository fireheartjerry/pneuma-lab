# Pre-experiment closure — 2026-08-03

## Current disposition

`post_launch_terminal_no_go`. The stale action-004 IAM-preflight report that
previously occupied this path is superseded by the final action-011 closure.

The fresh action `dual-l40s-qualification-011` passed the plan, account,
image, IAM, authority, and projection gates, then launched exactly one
size-two Batch array. Both children ended `FAILED` with provider status reason
`JobQueue deleted` and zero attempts. No worker started, no raw artifact or
worker identity exists, and no recovery drill ran. No retry occurred.

## Sealed qualification evidence

- Immutable fixture-only image:
  `sha256:5433527fb588c009d6cf16a5ac4278c463bbb5fab0c0a6826147b4c98f2e83ff`
- IAM policy SHA-256:
  `73666739e4e41f136fd11049715130e9b5086e6cafc21cee642ebe179fb0f24b`
- IAM simulation matrix SHA-256:
  `12301cd1b1bcaf51d8458de4d012f1a3be960a7cb589e833209d54cf52be3b2c`
- Saved plan SHA-256:
  `7c665827ed95bd4d55657e81ee9c2edf718f287cd58af325b4c714ce2b901ddc`
- Raw Terraform show SHA-256:
  `01387c775cf497046bbcc4cc6a82b08052f836a127dca214660bacf03ed70141`
- Composite plan binding:
  `f4b627f943a0989222fd0aab53d8d01329ccca733de12135b54777914d5d0516`
- KMS package SHA-256:
  `8b3ae0892add4452464c00b0982f2dccc24a9a5cdf8dd944e6fa8783c8eddb7e`
- Spot projection: USD 4.4842, strictly below USD 100.

The complete sanitized receipt is
`dual-l40s-qualification-011-execution-receipt-20260803.json` with SHA-256
`2452cc4a1a531e39bf170c038c8ba56829b57ea77b58ea532b2f61acb3990854`.

## Teardown

Fresh provider reads prove live jobs, active definition, queue, compute
environment, launch template, instances, volumes, ENIs, and security group
absent; the action output prefix is empty. AWS retains only the deregistered
`INACTIVE` job-definition revision as provider history. The teardown verifier
repair and focused regression are committed.

## Remaining gates before official P0 / Step 4B

1. The dual-L40S qualification is not passed; action-011 is exhausted. No
   relaunch is permitted in this closure.
2. Step 14 remains `launch_blocked` pending the real authority-backed P0
   power/tier receipt and packet, assignment, detectability, and unblind
   receipts.
3. Tasks 6–10 remain `implementation_complete; E2E_pending`; bounded Step 4A
   continuity, analysis, and Task 10 release preparation do not constitute a
   scientific result.
4. The official P0/Step 4B authority, lineage, execution, unblind, analysis,
   and claim-promotion gates remain separately reserved and were not run.

No scientific result, benchmark/model result, pilot, unblind, analysis, or
claim promotion exists.
