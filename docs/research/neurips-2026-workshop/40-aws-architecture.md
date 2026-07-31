# 40 — AWS Architecture Contract

**Status:** Step 6 static implementation complete; external verification pending

> **Superseded execution shape (2026-07-31):** DL-161 and
> `49-single-l40s-topology-amendment.md` prospectively select one
> `g6e.2xlarge`, 8 vCPUs, and one L40S with sequential execution. The static
> Terraform described below still encodes the former `g6e.12xlarge` shape and
> must be reconciled and reverified before Step 14. It is not launch-ready.

This is a tier-agnostic, static transcription of the AWS primary-path contract:
`us-east-1`; disabled managed EC2 Batch controller shape with one
`g6e.2xlarge` (8 vCPUs, one L40S, 44 GiB usable GPU memory), `minvCpus=0`,
`maxvCpus=8`, and `BEST_FIT`; AMI, root snapshot, and bootstrap-digest
variables; immutable S3 prefix and lifecycle inputs; and a DynamoDB lease read
limited to the exact configured table/key. The controller is one-GPU only;
TP2, multi-replica scheduling, H100 substitution, and simulator co-location
are prohibited by the topology contract.

The controller identity may read the lease and read/write only its configured
content-addressed S3 prefix. It cannot renew a lease. The watcher identity is
separate and is the only declared holder of lease-update/termination authority.
No benchmark-container execution surface is declared in this slice, so no
credential, IMDS, or Docker-socket access is introduced.

The committed provider selection is static. Terraform L1 evidence and any L2
plan remain distinct from L3 account-bound planning. Provisioning, `apply`,
spending, pilot authorization, and experiment execution remain out of scope and
unperformed.
