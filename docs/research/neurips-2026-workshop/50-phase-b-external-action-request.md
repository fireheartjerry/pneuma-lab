# 50 — Pending Phase B external-action request

**Prepared:** 2026-07-31
**Decision:** `not_authorized`
**Purpose:** present the exact next actions and bindings for explicit approval;
this document is not approval and cannot be cited as one.

## Requested actions

| ID | Exact scope | Hard ceiling | Explicit exclusions |
| --- | --- | --- | --- |
| A1 | Read-only AWS `sts:GetCallerIdentity`, EC2 Service Quotas listing, `g6e.2xlarge` offering lookup in `us-east-1`, and account-bound Terraform `plan`; write only local receipts | 50 MiB network, 30 minutes, USD 0, zero provider mutations | no quota request/change, apply, resource, reservation, image pull, or execution |
| A2 | Step 5B immutable retrieval and independent byte verification for the frozen model, tokenizer, benchmark, verifier, license, contamination, and OCI inputs; perform the coupled G-ROSTER qualification audit | 500 GiB download, 600 GiB temporary/retained storage, 24 hours, USD 0 | no model serving, benchmark episode, provider mutation, roster amendment, manifest promotion, or claim |
| A3 | Step 7B local deterministic builds of exactly the controller, model-server, and benchmark-worker images, twice per role, followed by SBOM generation and digest comparison | shared A2 storage ceiling, 24 hours, USD 0 | no ECR push, cloud build, GPU use, benchmark execution, or non-reproducibility waiver |

The current host has only about 153 GiB free. Therefore A2/A3 remain
operationally blocked even if approved until at least 600 GiB of suitable
storage is attached or a separately priced provider-local storage action is
authorized. A1 is additionally blocked on an authenticated AWS identity.

One-GPU admission and Step 14 reviewer execution are deliberately absent from
this request. Their exact image/input/account receipts, runtime, current price,
and cost ceilings do not exist yet. They require later, separate hash-bound
requests. Azure is excluded completely and remains separately governed.

## Exact bindings

| Path | SHA-256 |
| --- | --- |
| `docs/research/neurips-2026-workshop/38-experiment-design-freeze.md` | `1fcee2df71dfbe7fdfd8ddd742252f55295ae5c4c80ad4a6765c82c8cf7a430d` |
| `docs/research/neurips-2026-workshop/39-external-input-lock.md` | `2f2dec60cfaa9a5c7c0eabf9c55072e4848b6bf57c4cace81248299f8722b9d2` |
| `docs/research/neurips-2026-workshop/41-image-recipe-preparation.md` | `1124fc2d324200d1774e80de61ee22e41fa4cdeb3dbb2ba92ffdedce1dbf8324` |
| `docs/research/neurips-2026-workshop/47-pilot-protocol.md` | `e813bd245e33ba8fcbf1e8d1d812aa3d96aa27b5f8011bf4b0389c11bd1ef81e` |
| `docs/research/neurips-2026-workshop/49-single-l40s-topology-reconciliation.md` | `ac1c55e810deea0cbb0af9ae0f01a5fcb8be1ca6e240d4575daec417d16560bc` |
| `schemas/cloud-input-lock.schema.json` | `c03a761b459e27ee346e3df704416f4fe178846e60f32a3b3f673396f2dde7fe` |
| `schemas/cloud-image-build-receipt.schema.json` | `0db5ff617e70bb597b46d0818a9077d381673155de0fcea9f9874d38d2b1b8ea` |
| `schemas/cloud-aws-account-verification.schema.json` | `8ee5d90a2d80922476754d1a7218a7aab1b5b2238af76fc546ba7c141678ff17` |
| `schemas/cloud-pilot-admission-receipt.schema.json` | `5dce7f390239c2969bdd7ffa824688aa797a75a7d78afb94dade647d08148631` |
| `infra/terraform/main.tf` | `be1c7de70d1b9c6d44a937b5ad4605d489bc1c713f1c21e3db2886aa7454d5bc` |
| `infra/terraform/iam.tf` | `8e39764c25f9728f86d0ba52a3fff8c6d0954c88dad1738b29a0e17d31465683` |
| `infra/terraform/variables.tf` | `2c8f1160b20242fca7a077cd3ceeed9f3e8116eacc59654faacfce87fde1ce6e` |
| `src/pneuma_lab/cloud/inputs.py` | `4389b1b5e956c042cfefce41ec85c69add642def9f03a16e774ea2366fd26f64` |
| `src/pneuma_lab/cloud/images.py` | `13689da90954671bcb2e907d5a3ac9dbcb886a67eedf0666f5dbfe02a9355ae2` |
| `src/pneuma_lab/cloud/aws_account.py` | `edefae583591001075a94c1e73340904b76fda18b7e052b3176564aa29ac63ba` |
| `src/pneuma_lab/cloud/pilot.py` | `ce0078d7d09ce96ff828fef26e1fddba507b3d5a2a1b8f8a5e39dde83963f419` |
| `scripts/build_placebo_review_spec.py` | `77ee710017df87e1aa1ab81a045d69d5f57448dfdcf5fac566396ca8db7b42ba` |

## Approval form

A valid approval must identify this document by its whole-file SHA-256, name
the approved subset of `A1`, `A2`, and `A3`, repeat the applicable ceilings,
and come from the human operator. Any byte change invalidates that approval.
General permission, prior cloud approval, credits, or approval of a different
digest is insufficient.
