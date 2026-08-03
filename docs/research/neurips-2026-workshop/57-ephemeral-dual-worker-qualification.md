# 57 — Ephemeral dual-worker qualification path

**Status:** action `dual-l40s-qualification-011` reached a terminal no-go after
the single permitted launch; it did not qualify two workers. The final receipt
and teardown proof are committed below. No relaunch is permitted in this lane.

The separate `infra/terraform/qualification/` stack is the only future apply
surface for the bounded infrastructure qualification. It owns four
destroyable AWS control-plane objects: an enabled Spot compute environment,
its qualification launch template, a queue, and a fixture-only GPU job
definition. The environment is pinned to exactly two `g6e.2xlarge` workers
(8 vCPUs and one L40S each), a
16-vCPU ceiling, and `SPOT_PRICE_CAPACITY_OPTIMIZED`. The main experiment
stack is unchanged and its `prevent_destroy` lifecycle remains authoritative.
The managed Batch environment deliberately has no custom `image_id` binding or
`ami_id` variable: AWS Batch selects its AWS Batch-managed GPU/ECS AMI, and the
CPU builder AMI is never passed to the worker environment. The account-bound plan
must use every existing available subnet in each offered AZ (`us-east-1a`-
`us-east-1d`) and retain the verified zero-ingress security group for the
existing VPC; this stack creates no networking resources.

The job definition enforces a 3,600-second attempt timeout and one attempt
(`retry_strategy.attempts = 1`, equivalent to zero retries). The provider-free
admission package additionally requires exactly two distinct worker identities,
zero retries, and post-destroy provider-absence proof for jobs, instances,
volumes, launch templates, network interfaces, security groups, the job
definition, queue, and compute environment. The USD 100 value is a
fail-closed reservation/projection bound combined with timeout and teardown;
it is not an impossible-to-exceed AWS billing cap. AWS Budget alarms are
observability only and are never called enforcement.

The future runner is restricted to fixed admission fixtures and the canonical
partition/interruption-recovery drill. It must submit exactly two jobs, stop on
any capacity/image/runtime/receipt/teardown failure, and execute destroy plus
fresh absence verification. It must not run P0, Step 4B, a pilot, benchmark,
shard, unblind, analysis, or claim promotion.

The concrete future admission path also sends and verifies the per-submit
3,600-second Batch timeout, supplies the live S3 bucket policy to all 17 fixed
IAM simulations (15 S3 checks plus denied KMS decrypt and IAM policy
administration checks), independently verifies the live KMS Ed25519 key and
both signed authority records, and rejects action IDs already present in the
authoritative spend ledger. Its future signed package binds the exact saved-plan/show/
composite bytes, action-specific policy hash, image digest, four-AZ map,
action-scoped output prefix, fresh projection, action id, and zero retries.
The worker inline policy source grants only the five exact fixture reads and
two exact raw-output writes; unrelated DynamoDB and managed role policies are
preserved.

The worker fixture is explicitly CUDA-only: it checks one real L40S, exercises
the two registered tensor-allocation rungs, and emits deterministic tool/parity
records. It does not import vLLM, download weights, load a model, or execute a
subject workload. The `QUALIFICATION_MODEL` and revision environment names are
legacy binding fields retained for exact plan/action hashing; only
`fixture-only-cuda` / `fixture-only-v1` are accepted.

This document records code contracts only. It is not a provider receipt and
does not claim that a worker, GPU, model, benchmark, or experiment ran.

The concrete `--execute` runner also requires the exact fresh ignored
`--tfvars` path. It must be a regular mode-600 `.tfvars` file; its bytes are
hashed when the saved plan is loaded, checked again before apply and destroy,
and passed explicitly to the locked destroy command. Teardown therefore
cannot silently fall back to a stale checkout-local `qualification.auto.tfvars`
from another action.

Saved plans must likewise be regular files and are resolved to absolute paths
before Terraform's `-chdir` commands consume them.

The retained qualification image receipt must also have the registered image
build record identity, canonical self-digest, and fresh builder-absence proof;
field-level matches alone are not sufficient for a future action.

Future Terraform mutations must use state locking with a bounded lock timeout;
`-lock=false` is forbidden. The runner verifies the signed preparation
envelope/action admission and the four-resource account plan before calling
Terraform, submits one size-two Batch array only, and always disables/drains
before destroy followed by tagged/name-bound absence checks for jobs, instances,
volumes, launch template, network interfaces, security group, job definition,
queue, and compute environment.

## Action-011 terminal outcome — 2026-08-03

The fresh action-011 plan and authority package bound the exact saved-plan,
raw-show, composite, action-specific IAM policy, fixture-only image, four-AZ
map, and zero-retry contract. The immutable image was
`sha256:5433527fb588c009d6cf16a5ac4278c463bbb5fab0c0a6826147b4c98f2e83ff`;
the two-worker Spot projection was USD 4.4842.

CloudTrail proves exactly one `SubmitJob` with array size two and one attempt.
Batch later reported both children `FAILED` with status reason `JobQueue
deleted`; both had zero attempts, so no worker reached `STARTING` or `RUNNING`.
The output prefix is empty, no worker identity or raw artifact exists, and the
freeze/restore recovery drill did not run. This is a post-launch terminal
no-go, not a qualification pass and not scientific evidence.

Terraform destroy and fresh provider reads prove no live jobs, active job
definition, queue, compute environment, launch template, instance, volume,
network interface, or security group remains. AWS retains the deregistered
`INACTIVE` job-definition revision as provider history. The verifier repair
now treats terminal Batch history and inactive definition history as non-live,
with a focused regression in `tests/cloud/test_ephemeral_runner.py`.

Receipt: `evidence/dual-l40s-qualification-011-execution-receipt-20260803.json`
(SHA-256 `2452cc4a1a531e39bf170c038c8ba56829b57ea77b58ea532b2f61acb3990854`).
