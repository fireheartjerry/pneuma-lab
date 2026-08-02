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

The build-owned mtime-normalization successor action 013 failed closed even
earlier at controller reproducibility: IDs `sha256:03cfc60c...4991c` and
`sha256:652fd34a...03055` differed. Its versioned failure output and
independent teardown are sealed in
`evidence/step7b-aws-builder-failure-013-20260802.json`; no role probe, SBOM,
or production-surface handshake ran. Action 013 is exhausted with zero
retries, so the current production-surface gate remains open.

The pinned Buildx/BuildKit successor action 014 failed closed during Amazon
Linux bootstrap because requesting `curl` conflicted with the AMI's installed
`curl-minimal` package. No Buildx/BuildKit installation, image build, SBOM,
role probe, or production-surface handshake ran. The failure and teardown are
sealed in `evidence/step7b-aws-builder-failure-014-20260802.json`; action 014
is exhausted with zero retries and the production-surface gate remains open.

Diagnostic successor action 016 is prepared but remains an unsigned candidate.
It binds the inspection stdout/stderr sealing repair, source commit
`4a067231...e0a`, archive `26ab4f4...4e39`, pinned Buildx/BuildKit, and fresh
security group `sg-0c527fadf035615a6`; plan
`2cc7f3724709a831ff925bfc7d0c51a2b39d6a0589ee573e438545aa89983e6d` binds the
exact bytes. No provider execution or new production-surface evidence exists.

Diagnostic action 016 verified Buildx `v0.13.1` and BuildKit `v0.13.2`, then
failed closed at the first controller export because Amazon Linux Docker 25's
Docker exporter cannot export the locked vLLM base manifest list. No image,
SBOM, role probe, or production-surface handshake ran. The failure and
teardown are sealed in `evidence/step7b-aws-builder-failure-016-20260802.json`;
action 016 is exhausted with zero retries and the production-surface gate
remains open.

Platform-export successor action 017 is prepared but remains an unsigned
candidate. It binds removal of the forced multi-platform exporter flag while
retaining the single `linux/amd64` target, timestamp, and rewrite-timestamp
controls, plus source commit `fdd0b6e...bf41`, archive `520badd...42b3`, and
fresh security group `sg-0fa80f9418264fc47`; plan
`5ce31bbc9485e2b5a1d23568390ebf5331ddf852be4b38ec3b282874408b365c` binds the
exact bytes. No provider execution or new production-surface evidence exists.

Admitted action 017 then completed all three reproducible builds, probes, and
SBOMs but failed closed before the production-surface handshake because the
launcher duplicated the role already present in the sealed image ENTRYPOINT.
Its failure and independent teardown are sealed in
`evidence/step7b-aws-builder-failure-017-20260802.json`; action 017 is
exhausted with zero retries.

Successor action 018 bound the image-entrypoint repair and completed the same
three build/probe/SBOM gates. It failed closed at the strict production
surface when the mode-0600 non-secret harness bind was unreadable under
`--cap-drop ALL`; a local strict replay reproduced `PermissionError`. Commit
`f5a871d` repairs the bind-mode handling and the local image-bound replay
passes. The full 21-object cloud inventory and teardown are sealed in
`evidence/step7b-aws-builder-failure-018-20260802.json`; no production-surface
receipt exists, and action 018 is exhausted with zero retries. A fresh action
019 admission is required; no model, benchmark, pilot, or experiment ran.

Action 019 was then signed and its provider preflight passed, but the one
permitted EC2 launch was rejected before instance creation with
`InvalidGroup.NotFound` for the freshly created SG. Immediate independent
reads found the tagged SG, so the failure is recorded as an EC2 control-plane
propagation race rather than a successful launch. The failure and teardown are
sealed in `evidence/step7b-aws-builder-failure-019-20260802.json`; no
bootstrap, image, SBOM, production surface, model, benchmark, pilot, or
experiment ran. Action 019 is exhausted with zero retries; a fresh action 020
must add a consistency-gated SG launch path.

Action 020 was the sole admitted successor after the consistency race repair.
Its fresh SG was created and read back through the same CLI channel used for
the launch, and the one permitted launch succeeded for
`i-0f9fa01a181cccca2`. All three image/SBOM gates passed, but the cloud
image-bound production-surface subprocess failed closed before any handshake
receipt. The 21-object output inventory and independent teardown are sealed in
`evidence/step7b-aws-builder-failure-020-20260802.json`; the local exact-harness
replay passes, while the cloud child stderr remains unpreserved. A fresh
diagnostic action 021 is required; the production-surface gate remains open.

Admitted diagnostic action 021 is prepared from commit `1bb54ab` with fresh
no-ingress SG `sg-0c8eb506d362a5d3d`, archive
`38521fcd...ca93`, and plan digest
`ebc0bec75480b140df2b12ff72c5eeefc351973d659629b70605207cd43a263b`. Its
executor will persist the child production-surface return code/stdout/stderr
before raising. The KMS-signed package and versioned inputs were verified by
exact download-back hashes, and the final same-channel preflight passed. The
action remains unexecuted; the single launch is pending.

Corrected successor action 015 is prepared but remains an unsigned candidate.
It binds the repaired curl-minimal-safe bootstrap, source commit
`98dd81a...c806`, archive `9229854...b579`, pinned Buildx/BuildKit, and fresh
security group `sg-04331c50b912dac3d`; plan
`dbc75690017269be0544d9cc9c3fe3d8870928058fa80cac9c08acd38d35fa5a` binds
the exact bytes. No provider execution or new production-surface evidence
exists from this preparation entry.

Admitted action 015 removed the package conflict and verified Buildx
`v0.13.1`, but failed closed because the provider host did not report the
sealed BuildKit `v0.13.2` during builder validation. No role build, SBOM,
probe, or production-surface handshake ran. The failure and teardown are
sealed in `evidence/step7b-aws-builder-failure-015-20260802.json`; action 015
is exhausted with zero retries and the production-surface gate remains open.

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
