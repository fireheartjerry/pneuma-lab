# 49 — Single-L40S AWS Topology Amendment

**Status:** prospective protocol amendment; implementation reconciliation and
launch review pending
**Date:** 2026-07-31
**Authority record:** DL-161

## Decision

The AWS primary path is changed from one `g6e.12xlarge` (48 vCPUs, four L40S
GPUs) to one `g6e.2xlarge` (8 vCPUs, one L40S GPU with 48 GB VRAM). Subject,
task, arm, randomization, endpoint, estimand, blinding, and analysis contracts
do not change. Independent replicas and arms execute sequentially from their
frozen snapshots rather than concurrently on four GPUs.

This is a prospective, outcome-blind resource amendment made before a GPU
pilot or experiment result exists. The former 48-vCPU requirement was an
architecture choice, not a scientific sample-size requirement. No result may
be used to tune this topology.

## Admission conditions

The amended path remains fail closed until all of the following hold:

- the applied 8-vCPU quota is independently verified in the AWS account and
  classified as On-Demand, Spot, or both;
- a bounded non-scientific smoke proves that the pinned subject, tokenizer,
  serving stack, and selected context rung fit one 48 GB L40S;
- measured throughput and the recomputed schedule fit the frozen runtime and
  cost ceilings;
- sequential ordering is manifest-bound and temporal/provider drift controls
  preserve comparable execution conditions across arms;
- simulator placement is explicitly frozen: sequential on the same GPU,
  CPU/off-GPU where valid, or a separately authorized endpoint;
- Terraform, architecture manifests, orchestration, quota preflight, image
  bindings, cost projections, watchdogs, teardown, and pilot hashes are
  reconciled to the one-node/one-GPU shape; and
- Step 14 independently accepts the amendment.

Failure of model-fit, throughput, or isolation admission records a no-go or
requires another reviewed prospective amendment. It does not permit reducing
the scientific roster or changing outcomes after inspection.

## Provider and funding disposition

AWS remains the primary inference provider. More AWS spend may buy more elapsed
time or throughput only after quota/capacity and hash-bound spend authorization
permit additional resources; money does not override service quota or protocol
gates.

The user reports that USD 10,000 of additional Azure credits are incoming.
Until an official balance, expiry, eligibility, and account receipt is
verified, this is a pending planning resource with spendable value recorded as
zero. Once verified and separately authorized, Azure may accelerate other
experiments or training studies. Such training is outside this Resampling Null
inference protocol and must have its own design, data authority, budget, and
evidence lineage. An Azure BF16 replication remains a separately reported
subject and is never pooled with the AWS FP8 primary result.

## Non-authorization

This amendment does not authorize retrieval, image builds, provisioning,
spending, smoke, pilot, training, Step 4B, or scientific execution.
