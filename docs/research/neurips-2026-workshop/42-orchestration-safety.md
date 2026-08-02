# 42 — Orchestration and Interruption Safety

**Status:** Step 8 implementation complete against local fakes; DynamoDB contention and Batch array semantics verified; cloud checkpoint and scientific E2E remain pending

The cloud control layer implements conditional local lease acquisition, expiry
refusal, one-terminal-sample delivery, deterministic contiguous shard ranges,
and reconciliation that invalidates the entire task block when a restoration
boundary mismatch is detected. It wraps no scientific producer and does not
alter `power.py` or `branch_controller.py`.

Real DynamoDB conditional-write contention was exercised once under the signed
`lease-contention-009` action: one contender won and 31 received conditional
failures. The first action's delete failed closed; the separately signed
`lease-contention-cleanup-010` action deleted the exact item and proved
consistent-read absence. The receipts are infrastructure evidence only.
The separately signed `batch-array-qualification-014` action then created a
VALID Fargate compute environment and queue, ran a pinned public Alpine digest
as a size-three array with child indices 0/1/2 each `SUCCEEDED` exactly once,
observed a `SUCCEEDED` parent, and proved exact IAM/Batch teardown. The receipt
is infrastructure evidence only; no Batch environment or queue remains.
Cloud interruption/checkpoint restoration and scientific E2E remain external
verification work; no retry or resume authorization is created by these fakes.
