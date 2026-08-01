# 41 — Image Recipe Preparation

**Status:** Step 7A implementation complete; real image verification pending

Three role-separated recipes exist for controller, model server, and benchmark
worker. Their bases use syntactically pinned but intentionally invalid fixture
registries; their dependency locks are likewise fixtures. This permits static
pin-discipline and manifest-substitution tests without retrieving a single byte.

The Step 7B receipt contract now requires two image digests per role, an SBOM,
builder/recipe/Dockerfile/base/dependency-lock bindings, and one exact Step 5B
input-lock digest shared by all three roles. It also requires exact three-role
coverage and a truthful reproducibility comparison. A mismatch blocks the set
rather than being waived. No real base receipt, dependency lock, OCI image
digest, build, comparison, SBOM, ECR action, or external input retrieval
exists. Step 7B remains blocked on Step 5B, sufficient storage, and a separate
hash-bound authorization for material local/network build action.

## Immutable base candidates (metadata only)

The future real recipe may use the following Linux/amd64 manifest identities,
resolved read-only on 2026-07-31. They are **candidates**, not retrieved base
receipts, and do not replace the `registry.invalid` fixture lines until Step 5B
hash verification and a concrete signed build admission both exist.

| Roles | Candidate | Linux/amd64 manifest digest |
| --- | --- | --- |
| model-server | `vllm/vllm-openai:v0.19.0` | `sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90` |
| controller, benchmark-worker | `python:3.12.12-slim-bookworm` | `sha256:2986c55feb36e6cae00fa1fefb454283e4b33f35e75ff8bdd123b134130be301` |
