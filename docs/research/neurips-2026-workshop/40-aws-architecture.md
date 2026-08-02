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
