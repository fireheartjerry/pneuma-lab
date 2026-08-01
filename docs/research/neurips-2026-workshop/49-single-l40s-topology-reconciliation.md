# 49 — Approved single-L40S topology reconciliation

**Date:** 2026-07-31
**Authority:** DL-161; user-approved execution topology
**Status:** implementation reconciliation complete; external gates remain open

Machine-readable state: [`docs/project-status.json`](../../project-status.json).

## Binding AWS primary shape

The AWS primary path is exactly one `g6e.2xlarge` in `us-east-1`: 8 vCPUs,
64 GiB host memory, one NVIDIA L40S, and 44 GiB usable device memory. Batch has
`minvCpus=0`, `maxvCpus=8`, one whole-instance controller job, and
`BEST_FIT`. A G/VT quota receipt must therefore demonstrate at least 8 applied
vCPUs for the exact account and region before launch; a historical 48-vCPU
request is neither required nor evidence of this approval.

The subject may admit only `l40s-tp1-32768` or `l40s-tp1-65536`. It chooses the
largest passing candidate using only OOM, tool-call, output-parity, and p10
throughput measurements. The GPU is treated as 44 GiB usable, not 48 GiB
marketing capacity. TP2, multiple subject replicas, H100 substitution, and
simulator co-location are rejected—not “future optimisation.” One GPU means
one GPU; topology math does not negotiate.

## Preserved boundaries

- `G-ROSTER` is unchanged. A topology edit cannot qualify a task, license,
  image, base commit, isolation property, or three-pair split.
- Step 5B still requires genuine immutable external-input and receipt evidence;
  fixture locks remain insufficient.
- Step 7B still requires separately authorized real double-build, image-digest,
  SBOM, and reproducibility evidence.
- Terraform L1 validation, credential-free planning, and account-bound L3
  planning are distinct evidence levels. No `terraform apply` is permitted.
- The one-GPU fit/throughput gate is an admission measurement, not a benchmark
  experiment and not a scientific result. It cannot run without every required
  hash-bound authorization and upstream receipt.
- Azure remains a separately authorized parity/precision subject. No AWS credit,
  quota, instance, receipt, or measurement authorizes Azure or permits pooling.

## Evidence required before a launch review can clear

1. Step 5B immutable model, tokenizer, benchmark, verifier, license,
   contamination, and OCI receipts, independently hash-verified.
2. A completed `G-ROSTER` qualification audit at the exact base commits.
3. Step 7B two-build image digests and SBOMs, or an explicit blocking
   reproducibility deviation.
4. Terraform L1 plus separately authorized L3 account plan and an 8-vCPU quota
   receipt for the exact AWS account/region.
5. One-GPU OOM, tool-call, output-parity, and p10-throughput receipts bound to
   the approved model/image/input/code hashes and frozen limits. The committed
   `cloud-pilot-admission-receipt` contract additionally pins the protocol,
   architecture, authorization, exact one-GPU topology, raw gate outcomes, and
   measurement counts; it records an observation but cannot confer authority.
6. A fresh Step 14 hostile launch review over those receipts. Its verdict cannot
   authorize an experiment or paid execution by itself.

No item above has been fabricated or inferred from this reconciliation.
