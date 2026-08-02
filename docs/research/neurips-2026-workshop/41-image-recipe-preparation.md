# 41 — Image Recipe Preparation

**Status:** Step 7B build/SBOM qualification complete; production execution-surface E2E pending

Three role-separated recipes now exist for controller, model server, and
benchmark worker. Each overlays the exact sealed standard-library role runtime
on the one Linux/amd64 `vllm/vllm-openai` digest already enumerated in the real
Step 5B input lock. Their dependency closures are intentionally empty because
the probe imports only the standard library; no resolver runs during the build.
The companion executor checks every bound source byte, builds each role twice,
runs positive and wrong-hash probes with Docker networking disabled, emits SPDX
SBOMs, and rejects any image-config digest mismatch.

The Step 7B receipt contract now requires two image digests per role, an SBOM,
builder/recipe/Dockerfile/base/dependency-lock bindings, and one exact Step 5B
input-lock digest shared by all three roles. It also requires exact three-role
coverage and a truthful reproducibility comparison. The KMS-admitted AWS
successor action 009 now provides the real receipt set: each role has two
identical image IDs, positive and wrong-hash probes behaved as required, and a
nonempty SPDX SBOM is independently hashed. The complete versioned output set
is sealed in `evidence/step7b-aws-builder-success-009-20260802.json`.
This build-only qualification neither loads a model nor runs a benchmark; the
real production execution-surface E2E remains pending.

The fresh successor action 010 bound to the new handshake did not produce a
qualifying image set: its controller double-build IDs differed and the
executor failed closed before probes or SBOM publication. That failure is
sealed in `evidence/step7b-aws-builder-failure-010-20260802.json`; action 010
is exhausted and action 009's older-runtime images cannot be reused as E2E
evidence.

## Immutable base candidates (metadata only)

The real role recipes use the following pre-locked Linux/amd64 manifest identity.
It is an input-lock binding, not a completed image-pull or build receipt.

| Roles | Candidate | Linux/amd64 manifest digest |
| --- | --- | --- |
| controller, model-server, benchmark-worker | `vllm/vllm-openai` | `sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90` |
