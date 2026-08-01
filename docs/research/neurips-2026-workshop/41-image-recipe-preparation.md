# 41 — Image Recipe Preparation

**Status:** Step 7B build implementation complete; real receipt verification pending

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
coverage and a truthful reproducibility comparison. A mismatch blocks the set
rather than being waived. No real OCI image digest, build, comparison, SBOM,
or ECR action exists yet. The sealed local-only plan is storage-blocked on this
VPS and cannot authorize AWS; its successor must bind an EC2 builder, source
archive, Syft binary, exact spend ceiling, teardown, and a new KMS admission.
This build-only qualification neither loads a model nor runs a benchmark.

## Immutable base candidates (metadata only)

The real role recipes use the following pre-locked Linux/amd64 manifest identity.
It is an input-lock binding, not a completed image-pull or build receipt.

| Roles | Candidate | Linux/amd64 manifest digest |
| --- | --- | --- |
| controller, model-server, benchmark-worker | `vllm/vllm-openai` | `sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90` |
