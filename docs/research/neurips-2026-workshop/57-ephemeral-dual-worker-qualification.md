# 57 — Ephemeral dual-worker qualification path

**Status:** implementation-only; no cloud qualification has run.

The separate `infra/terraform/qualification/` stack is the only future apply
surface for the bounded infrastructure qualification. It owns four
destroyable AWS control-plane objects: an enabled Spot compute environment,
its qualification launch template, a queue, and a fixture-only GPU job
definition. The environment is pinned to exactly two `g6e.2xlarge` workers
(8 vCPUs and one L40S each), a
16-vCPU ceiling, and `SPOT_PRICE_CAPACITY_OPTIMIZED`. The main experiment
stack is unchanged and its `prevent_destroy` lifecycle remains authoritative.

The job definition enforces a 3,600-second attempt timeout and one attempt
(`retry_strategy.attempts = 1`, equivalent to zero retries). The provider-free
admission package additionally requires exactly two distinct worker identities,
zero retries, and post-destroy provider-absence proof. The USD 100 value is a
fail-closed reservation/projection bound combined with timeout and teardown;
it is not an impossible-to-exceed AWS billing cap. AWS Budget alarms are
observability only and are never called enforcement.

The future runner is restricted to fixed admission fixtures and the canonical
partition/interruption-recovery drill. It must submit exactly two jobs, stop on
any capacity/image/runtime/receipt/teardown failure, and execute destroy plus
fresh absence verification. It must not run P0, Step 4B, a pilot, benchmark,
shard, unblind, analysis, or claim promotion.

This document records code contracts only. It is not a provider receipt and
does not claim that a worker, GPU, model, benchmark, or experiment ran.

Future Terraform mutations must use state locking with a bounded lock timeout;
`-lock=false` is forbidden. The runner verifies the signed preparation
envelope/action admission and the four-resource account plan before calling
Terraform, submits one size-two Batch array only, and always disables/drains
before destroy followed by tagged absence checks for jobs, instances, volumes,
job definition, queue, and compute environment.
