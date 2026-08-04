# Three role recipes (Step 7B candidate)

Each role is based on the exact Linux/amd64 `vllm/vllm-openai` digest already
bound by the real Step 5B input lock.  The image overlays the sealed cloud
production package, the closed task-registry validator, and the required
schemas.  The build checks that the digest-pinned vLLM base exposes the
reviewed `cryptography` and `jsonschema` runtime closure.  It does not download
a model, execute a benchmark, use a GPU, push to a registry, or contain
controller credentials.  The `verify` and `e2e` protocols remain
qualification-only; `production` requires a separately bound run
specification and official authorization.

A separately signed Step 7B action must build every role twice with
`SOURCE_DATE_EPOCH`, `PYTHONHASHSEED`, and UTC; execute its positive and
wrong-hash role probes under `--network none`; produce an SPDX SBOM from each
first build; and fail closed when either image-config digest differs. Build
arguments are `SOURCE_DATE_EPOCH` and role-specific immutable input refs; the
order is base receipt → dependency closure → source copy → image build → SBOM
→ second identical build → digest comparison. This repository change itself
authorizes no pull, build, push, provider action, or experiment.

The role Dockerfiles also normalize the build-owned `/opt` tree to
`SOURCE_DATE_EPOCH`. The AWS executor uses a content-addressed BuildKit
`v0.13.2` container through a content-addressed Buildx `v0.13.1` client. The
older Docker-packaged BuildKit `v0.12.x` path does not reliably produce
reproducible exported image metadata even with `SOURCE_DATE_EPOCH` and
`rewrite-timestamp=true`; relying on an accidental same-second double build
would be an invalid reproducibility claim.
