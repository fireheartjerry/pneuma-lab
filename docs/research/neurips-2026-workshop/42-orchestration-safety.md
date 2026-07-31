# 42 — Orchestration and Interruption Safety

**Status:** Step 8 implementation complete against local fakes; external verification pending

The cloud control layer implements conditional local lease acquisition, expiry
refusal, one-terminal-sample delivery, deterministic contiguous shard ranges,
and reconciliation that invalidates the entire task block when a restoration
boundary mismatch is detected. It wraps no scientific producer and does not
alter `power.py` or `branch_controller.py`.

No DynamoDB conditional write, Batch scheduling, cloud interruption, or real
checkpoint restoration was exercised. Those remain external verification work;
no retry or resume authorization is created by these fakes.
