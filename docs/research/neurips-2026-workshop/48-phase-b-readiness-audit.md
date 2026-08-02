# 48 — Phase B Readiness Audit

**Date:** 2026-07-31
**Scope:** final audit of Phase B preparation through Step 13

## Reconciliation note

DL-161 supersedes the retired four-L40S, 48-vCPU AWS planning topology with the
approved single-L40S `g6e.2xlarge` (8-vCPU) contract. This is a bounded
topology reconciliation, not a scientific execution, input receipt, image
build, account plan, or launch approval. Azure remains separately governed.

## Implemented preparation

Steps 4, 5A, 6, 7A, 8, 9, 10, 11 (T1), and 12 are
`implementation_complete` in their bounded local/static scope. Each has a
committed status record, focused tests, append-only decision/ledger/journal
record, and a pushed commit. They establish no scientific result.

## Gates that remain open

| item | implementation | external verification | authority freeze | launch review | execution |
| --- | --- | --- | --- | --- | --- |
| Step 5B real inputs | implementation_complete: retrieval workflow, offline receipt-verification path, unsigned shape-demo candidate, and exact metadata-only inventory candidate | pending: local licence/OCI evidence exists, but no complete model/tokenizer/benchmark/verifier snapshot receipt set or real input lock exists | no signed preparation envelope or concrete admission is committed; each real action requires both | pending | pending |
| Step 7B real builds | double-build/SBOM receipt verifier complete; one hardened qualification image exists | pending: no complete three-role image/SBOM/repeat-build set, and no production cloud-controller or benchmark-worker entrypoint exists | no signed preparation envelope or concrete build admission is committed | pending | pending |
| G-ROSTER | evaluator implementation_complete | pending: both tiers FEASIBILITY_NO_GO; C/C++ shortfalls provisional only (DL-163) | pending base-commit admissibility audit or reviewed amendment | pending | pending |
| AWS architecture | 8-vCPU single-L40S reconciliation and static/L1 Terraform validation complete; B1 account bootstrap and read-only account-bound plan complete | authenticated CloudShell audit confirms On-Demand 8, Spot 16, `g6e.2xlarge` in `us-east-1a`-`1d`, and the exact S3/DynamoDB/IAM/network substrate; no compute/deployment or teardown-drill receipt | B1 consumed for substrate only; future compute action requires fresh authority | pending | pending |
| Azure parity/other studies | boundary only; user reports $10k incoming | official balance/terms remain unverified | separate authority required | pending | pending |
| pilot | implementation_complete: protocol now freezes an 8.0 output-token/sec p10 floor and receipt-vs-protocol validation | pending admission evidence | an exact signed envelope/admission and all upstream receipts remain required | pending | pending |

The B1 authorization was consumed only for the bounded non-compute substrate
recorded in receipt 52. CL-028 records local contract work; it is not a signed
preparation envelope and authorizes nothing. No concrete action admission, external input retrieval,
deterministic container build, compute capacity, GPU measurement, or pilot
authorization exists. Foundation-training authorizations are unrelated
authority and cannot be reused. Therefore no Step 5B retrieval, Step 7B build,
compute/deployment, paid execution, Step 14, Step 4B, or pilot was performed.

The host currently exposes about 153 GiB free on its only writable disk, below
the 321–470 GiB historical retrieval estimate and the conservative 600 GiB
request ceiling. Document 50 is a historical, unsigned non-authorizing request
whose listed hashes predate the later admission and input-inventory hardening;
it must not be signed or reused. No operative preparation envelope exists.
Step 14 spec generation now refuses to substitute contract prose for
the five required evidence receipts and exits before writing a spec.

This closes the requested implementation-preparation track, **not Phase B as a
fully externally verified or launch-ready phase**.

## 2026-08-02 reconciliation

The previously pending Step 7B row is now externally closed for its bounded
image-build/SBOM scope. KMS-admitted AWS action 009 produced two matching
digests for each of the three roles, three nonempty SPDX SBOMs, positive and
wrong-hash probe receipts, and an independently verified teardown. The exact
receipt is `evidence/step7b-aws-builder-success-009-20260802.json`.

This does not close the production execution-surface gate: the current role
runtime remains a byte-verifying qualification boundary, not a real
controller/model-server/benchmark-worker adapter. Interruption/recovery and
Step 14 therefore remain open, and no pilot or experiment is authorized.

The first fresh image-bound attempt for the new handshake (KMS-admitted action
010) failed closed at the controller reproducibility gate: its two image IDs
were different, so no probe, SBOM, or role-chain receipt was admissible. The
failure and independent teardown are sealed in
`evidence/step7b-aws-builder-failure-010-20260802.json`; action 010 is
exhausted with zero retries and action 009's older images are not a substitute.

The timestamp-stability successor action 011 failed at the same controller
double-build reproducibility gate despite exporting `SOURCE_DATE_EPOCH`,
setting `BUILDKIT_MULTI_PLATFORM=1`, and pinning `linux/amd64`. Its failure and
teardown are sealed in
`evidence/step7b-aws-builder-failure-011-20260802.json`; no current image-bound
production-surface receipt exists.

The explicit exporter successor action 012 passed the controller and
model-server double-build gates, then failed closed at benchmark-worker
reproducibility: IDs `sha256:6ab20d3b...b4d1139` and
`sha256:86630dda...b3112af` differed. Partial controller/model-server probes
and SBOMs are preserved, but benchmark-worker probes/SBOM and the production
surface were not run. Failure and teardown are sealed in
`evidence/step7b-aws-builder-failure-012-20260802.json`; the current
production-surface gate remains open and action 012 is exhausted.

## Topology change and its residual empirical risk

DL-161 selects an 8-vCPU `g6e.2xlarge` single-L40S AWS path with sequential
execution, and the schemas, validator, quota preflight, pilot protocol, and
Terraform have been reconciled to it. That reconciliation does not itself
establish quota class, model fit, throughput, cost, or launch readiness.

The current upstream serving record also leaves one-L40S feasibility explicitly
empirical: official long-context examples use multi-way tensor parallelism and
community reports do not establish this exact L40S/tool-call configuration. It
is therefore a reason to keep the frozen OOM/tool-call/output-parity/p10-
throughput admission gate, not a reason to waive it.
