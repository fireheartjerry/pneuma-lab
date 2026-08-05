# 40 — AWS Architecture Contract

**Status:** static implementation complete; two-worker Spot external
verification and deployment remain pending

> **Execution shape (2026-08-02):** DL-171 and
> `55-dual-l40s-spot-topology-reconciliation.md` bind the AWS primary path to
> two independent Spot `g6e.2xlarge` workers: 16 vCPUs and two L40S devices in
> total. The static Terraform and manifests encode canonical disjoint work
> partitioning and freeze-and-resume interruption handling. No deployment,
> capacity, price, or launch receipt exists for this revised topology.

This is a tier-agnostic, static transcription of the AWS primary-path contract:
`us-east-1`; disabled managed EC2 Batch Spot shape with two
`g6e.2xlarge` workers (each 8 vCPUs, one L40S, and 44 GiB usable GPU memory),
`minvCpus=0`, `maxvCpus=16`, and `SPOT_PRICE_CAPACITY_OPTIMIZED`; AMI, root
snapshot, and bootstrap-digest variables; immutable S3 prefix and lifecycle
inputs; and a DynamoDB lease read limited to the exact configured table/key.
Canonical round-robin assignment and freeze-and-resume interruption handling
are part of the topology contract. TP2, multi-GPU model parallelism, H100
substitution, and simulator co-location remain prohibited.

The controller identity may read the lease and read/write only its configured
content-addressed S3 prefix. It cannot renew a lease. The watcher identity is
separate and is the only declared holder of lease-update/termination authority.
No benchmark-container execution surface is declared in this slice, so no
credential, IMDS, or Docker-socket access is introduced.

The committed provider selection is static. Terraform L1 evidence, the
read-only bootstrap account plan in receipt 52, and any later compute L3 plan
remain distinct. No compute `apply`, spending, pilot authorization, or
experiment execution is authorized or performed.

## Current amendment — repaired production role surface — 2026-08-04

The historical static-contract statements above remain the architecture
baseline; this amendment is the current status for the implemented production
role surface. The passed action-019 two-L40S qualification remains a separate
qualification receipt. It is not official-study evidence.

The production controller, model-server, and benchmark-worker images were
rebuilt from repaired commit
`c352c9e0e4459c80cddfbf84cce94d0b4c79aaa4` and passed one fresh bounded,
non-scientific AWS surface E2E using the concrete `m7i.large` on-demand SSM
binding. The action proved one-submit/restart reconciliation,
observation-error preservation, role receipt validation, and explicit
teardown. It created no official model or benchmark workload. Fresh provider
absence is sealed in the action teardown receipt; retained ECR images and
SBOMs are intentional.

This closes the production-surface E2E gap, not the scientific E2E gate. The
primary two-worker `g6e.2xlarge` official topology remains separately gated by
the live eligible-roster ceremony, repaired C120/C160 power validation and
registered tier rule, final packet/assignment/detectability/blinding/analysis
receipts, separately signed official authority, and hostile Step-14 review.
Official P0/Step 4B remains unrun and launch-blocked.
