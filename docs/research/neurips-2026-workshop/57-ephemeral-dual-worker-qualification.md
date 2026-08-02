# 57 — Ephemeral dual-worker qualification path

**Status:** implementation-only; no cloud qualification has run.

The separate `infra/terraform/qualification/` stack is the only future apply
surface for the bounded infrastructure qualification. It owns three
destroyable AWS Batch control-plane objects: an enabled Spot compute
environment, a queue, and a fixture-only GPU job definition. The environment
is pinned to exactly two `g6e.2xlarge` workers (8 vCPUs and one L40S each), a
16-vCPU ceiling, and `SPOT_PRICE_CAPACITY_OPTIMIZED`. The main experiment
stack is unchanged and its `prevent_destroy` lifecycle remains authoritative.

The job definition enforces a 3,600-second attempt timeout and one attempt
(`retry_strategy.attempts = 1`, equivalent to zero retries). The provider-free
admission package additionally requires exactly two distinct worker identities,
zero retries, the USD 100 total ceiling, and post-destroy provider-absence
proof. These checks are hard gates; AWS Budget notifications are not used as
enforcement.

The future runner is restricted to fixed admission fixtures and the canonical
partition/interruption-recovery drill. It must submit exactly two jobs, stop on
any capacity/image/runtime/receipt/teardown failure, and execute destroy plus
fresh absence verification. It must not run P0, Step 4B, a pilot, benchmark,
shard, unblind, analysis, or claim promotion.

This document records code contracts only. It is not a provider receipt and
does not claim that a worker, GPU, model, benchmark, or experiment ran.
