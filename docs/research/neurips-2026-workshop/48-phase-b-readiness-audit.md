# 48 — Phase B Readiness Audit

**Date:** 2026-07-31
**Scope:** final audit of Phase B preparation through Step 13

## Reconciliation note

DL-161 supersedes the retired four-L40S, 48-vCPU AWS planning topology with the
approved single-L40S `g6e.2xlarge` (8-vCPU) contract. This is a bounded
topology reconciliation, not a scientific execution, input receipt, image
build, account plan, or launch approval. Azure remains separately governed.

## Implemented preparation

Steps 4, 5A, 6, 7A, 8, 9, 10, 11 (T1), 12, and 13 are
`implementation_complete` in their bounded local/static scope. Each has a
committed status record, focused tests, append-only decision/ledger/journal
record, and a pushed commit. They establish no scientific result.

## Gates that remain open

| item | implementation | external verification | authority freeze | launch review | execution |
| --- | --- | --- | --- | --- | --- |
| Step 5B real inputs | implementation_complete: retrieval workflow, offline receipt-verification path, and unsigned shape-demo candidate | pending: no retrieved receipts; host storage insufficient for the projected retrieval | pending: candidate unsigned and bound to a fixture lock; request 50 outstanding | pending | pending |
| Step 7B real builds | double-build/SBOM receipt path complete | pending: no image/SBOM/repeat-build receipts | pending request 50 | pending | pending |
| G-ROSTER | evaluator implementation_complete | pending: both tiers FEASIBILITY_NO_GO; C/C++ shortfalls provisional only (DL-163) | pending base-commit admissibility audit or reviewed amendment | pending | pending |
| AWS architecture | 8-vCPU single-L40S reconciliation complete; static/L1 Terraform validation complete | authenticated console audit confirms On-Demand 8, Spot 16, and `g6e.2xlarge` in `us-east-1a`-`1d`; CLI credentials, Terraform L3 plan, and an account-bound receipt remain pending | pending request 50 A1 | pending | pending |
| Azure parity/other studies | boundary only; user reports $10k incoming | official balance/terms remain unverified | separate authority required | pending | pending |
| pilot | protocol and exact receipt path complete | pending admission evidence | pending hash-bound human/spend authorization | pending | pending |

The authorization audit found no NeurIPS-specific, positive, hash-bound
authorization capable of permitting external input retrieval or deterministic
container builds. Foundation-training authorizations are unrelated authority and
cannot be reused. Therefore no Step 5B retrieval, Step 7B build, provider call,
cloud provisioning, paid action, Step 14, Step 4B, or pilot was performed.

The host currently exposes about 153 GiB free on its only writable disk, below
the 321–470 GiB historical retrieval estimate and the conservative 600 GiB
request ceiling. The signed pending action request is document 50. It is not
authority. Step 14 spec generation now refuses to substitute contract prose
for the five required evidence receipts and exits before writing a spec.

This closes the requested implementation-preparation track, **not Phase B as a
fully externally verified or launch-ready phase**.

## Topology change and its residual empirical risk

DL-161 selects an 8-vCPU `g6e.2xlarge` single-L40S AWS path with sequential
execution, and the schemas, validator, quota preflight, pilot protocol, and
Terraform have been reconciled to it. That reconciliation does not itself
establish quota class, model fit, throughput, cost, or launch readiness.

The current upstream serving record also leaves one-L40S feasibility explicitly
empirical: the current vLLM recipe documents the FP8 variant at 42 GiB and
single-GPU verification on H100/H200, not L40S. It is therefore a reason to
keep the frozen OOM/tool-call/output-parity/p10-throughput admission gate, not
a reason to waive it.
