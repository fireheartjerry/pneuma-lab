# Pre-experiment closure — 2026-08-03

## Disposition

`launch_blocked`. The CPU-only worker image and account topology gates passed,
but the qualification stopped at the read-only IAM least-privilege gate. No
action-004 envelope, admission, KMS signature, Terraform apply, Batch job, GPU
worker, or scientific workload was created or run.

The sanitized preflight evidence is
`evidence/dual-l40s-qualification-004-preflight-no-go-20260803.json`.

## What remains before official P0 / Step 4B execution

1. Repair the existing worker instance-profile policy so effective permissions
   read exactly the five action-scoped fixture objects and write exactly the two
   worker-indexed raw-output objects required by the fixed probe. Re-run the
   read-only IAM simulation and account-bound Terraform plan after that repair.
2. Complete a fresh qualification authority ceremony: append the plan,
   envelope, and admission records; bind the exact saved-plan and raw
   `terraform show -json` bytes; bind the image digest, four-AZ subnet map,
   projection, and zero-retry policy; sign with the registered KMS key; and
   verify before any apply.
3. Execute the fixture-only qualification once, if all gates pass, and retain
   parent/child success evidence, distinct worker identities, immutable raw
   artifacts, the canonical freeze/restore receipt, and fresh provider absence
   proof.
4. Produce the missing official scientific authority receipts: the real P0
   power report/tier, packet, assignment, detectability, unblind, and Step 14
   authority records. These are not fabricated or signed by this closure.
5. Keep Task 6–10 at `implementation_complete; E2E_pending` until a separately
   authorized, authority-backed scientific lineage exists. Keep Step 14 at
   `launch_blocked` until its real authority requirements are met.

No scientific result, benchmark result, model result, unblind, analysis, or
claim promotion exists.
