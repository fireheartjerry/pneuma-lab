# Repaired production surface and input closure — 2026-08-04

## Disposition

The pre-outcome statistical-fidelity repair is now bound through the real
production role images and a bounded AWS deployment-surface E2E. The
production implementation and its non-scientific surface admission are
complete. This document is not a scientific result and does not authorize the
official P0/Step-4B study.

The repaired source binding is commit
`c352c9e0e4459c80cddfbf84cce94d0b4c79aaa4`. All prospective bindings made
before the repair remain stale and are not reused.

## Immutable production image set

The three role images were built and pushed from the repaired source with the
registered pinned base image, BuildKit provenance, immutable ECR repositories,
scan-on-push, and Syft 1.50.0 SPDX SBOMs. The build did not download the model
or execute a benchmark.

| role | image digest | SBOM SHA-256 | SBOM bytes |
| --- | --- | --- | ---: |
| controller | `sha256:eb8c8f5bf51e316443212b9e7db57fe9b7596bcf08a6fb00de52f642ad5827cf` | `afc9ae017e0bbe7fb998efafd50bd6f34bd6ddd7e5409877ad467b16429cbca9` | 25,400,759 |
| model-server | `sha256:6b175c1d822af623d77a3241c7d0015854881be63c70940733fe8fd5c3a4854f` | `0b8e8fdd9f7c0ea852b53ac88c169434823e5609e30d2a5c89bfecb0cfcde89a` | 25,404,337 |
| benchmark-worker | `sha256:83f87c3f32aa670a433685b97d59f7b6ab927e6de039f1964a2d6b9e177b00d4` | `4ac7a7327070c8d3f80f700da94a6c8b6f65411d762e773a95714b17aa1c9c72` | 25,411,493 |

The canonical image-set record is
`evidence/official-study-input-package-20260804-repair/evidence/images.json`
(SHA-256
`2497d0e5a30b012c6b9d3ce0e025094a511626d5d5ed58de99078d5603f5c226`). Each
role receipt remains `pending_bounded_surface_e2e`; the E2E result is a
separate receipt and does not mutate build evidence.

## Bounded production-surface E2E

Fresh action `official-surface-e2e-20260804` exercised the exact production
controller and role entrypoints with an explicitly non-scientific handshake.
It used one on-demand `m7i.large` surface instance, one submission, one
attempt, a 900-second maximum duration, and no model, benchmark, roster,
assignment, P0 grid, analysis, or unblind input. The projected cost was
`$0.53`; the bounded admission ceiling was `$3.00`.

The controller proved restart reconciliation and preserved a deliberately
injected observation error before reaching `workload_terminal`. The action
then entered the explicit teardown phase and returned `COMPLETE`.

- surface SHA-256: `0b401d505368505be161ead2fd54d8016bc7fd12aeabe3b4be3e8f8e93114f35`
- E2E receipt SHA-256: `7b36a091252c945d11ace5ac02d7566837b75873d8137565899abab6e64aec18`
- status SHA-256: `922a4d26d3f421fc1a1c3707670ae6d3dc8d378bb0a50a1c5074538d29b5e6ab`
- teardown SHA-256: `dc82ae43653ba4a487a2f655671a96953ff07e9a85ef9c2e7c4f1e803b4413a6`
- instance: `i-0cdc9c7fca9514289`
- security group: `sg-025ca8ce5b31c18ff`

The teardown receipt records terminated compute, deleted network and IAM
resources, and fresh provider absence. Fresh post-action IAM reads returned
`NoSuchEntity` for both the action role and instance profile. Immutable ECR
images, SBOMs, and compact receipts are intentionally retained.

## Repaired pre-launch input package

The package is explicitly `pre_launch_candidate` and `authorizing: false`.
It binds the registered model/task inputs, licenses and contamination
receipts, benchmark adapter revisions, candidate roster, pending assignment,
RNG commitments, provider binding, frozen analysis graph, repaired source
commit, repaired role image digests, and the bounded surface record.

- input lock: `7bb584da29f1fb55e5f46133a985bd3c249f154643dad5a3469ae737aee497e7`
- analysis graph: `aa4310584d605928e2edcba0828381c97f4aab0e51f115569073b9e22f4a44e4`
- provider binding: `f3fceeea6678d48e428ebe8cb19b1ae72859d81b597bc83f2a2eba1fe1cf6154`
- image set: `2497d0e5a30b012c6b9d3ce0e025094a511626d5d5ed58de99078d5603f5c226`
- candidate run spec: `028c39c4e44cf66438df528b64ba73209e49205266e156dfcfbe506b60aa5760`
- candidate package: `d81e4dcfc9ec3ae37f78d3398b8df88f64918a8f4f883460f1ebfd86c8d1a7a4`

The candidate deliberately contains `power_report_ref: null`,
`power_tier: null`, and no official authorization reference. Those nulls are
the fail-closed state, not omissions to be papered over.

## Remaining external/scientific prerequisites

The fresh roster candidate still has `ceremony_status: not_performed` and no
`eligible_confirmation_ref`. A read-only finalization preflight therefore
returned `BLOCKED_NO_LIVE_ELIGIBLE_CONFIRMATION_CEREMONY`; no C120/C160 grid,
power report, tier selection, or power authority receipt was run or minted.

The remaining launch package work is consequently limited to the genuine
scientific and authority boundary:

1. Conduct the registered live Sigstore/drand/Node eligible-roster ceremony
   and independently validate its canonical receipt.
2. Using that eligible-confirmation roster and the repaired bindings, run the
   registered C120 and C160 power/type-I validations, combine both receipts,
   and apply the registered largest-feasible rule. A formal no-go is the only
   valid alternative to a selected tier.
3. Seal packet, assignment, task-block, detectability, leakage, blinding,
   frozen-analysis, spend, and fresh account/quota receipts.
4. Mint a separately signed official authorization bound to the final repaired
   code/image/input/analysis/power/tier digests, then pass the hostile Step-14
   launch review.

Only after those actions may an explicitly authorized official controller run
the real model and approved benchmark. The official P0/Step-4B study remains
unrun, separately authorized, and launch-blocked.

## Non-execution attestation

This closure created no official scientific workload, model evaluation,
benchmark result, pilot, canonical P0 grid, live roster ceremony, unblind,
scientific analysis, scientific claim, power report, tier receipt, or official
authorization. The sole AWS workload was the bounded non-scientific production
surface action named above, and all resources from it were torn down.
