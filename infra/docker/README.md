# Three role recipes (Step 7B candidate)

Each role is based on the exact Linux/amd64 `vllm/vllm-openai` digest already
bound by the real Step 5B input lock.  The image overlays only the sealed
standard-library `production_runtime` byte stream and an intentional empty
dependency closure.  It does not download a model, execute a benchmark, use a
GPU, push to a registry, or contain controller credentials.

A separately signed Step 7B action must build every role twice with
`SOURCE_DATE_EPOCH`, `PYTHONHASHSEED`, and UTC; execute its positive and
wrong-hash role probes under `--network none`; produce an SPDX SBOM from each
first build; and fail closed when either image-config digest differs. Build
arguments are `SOURCE_DATE_EPOCH` and role-specific immutable input refs; the
order is base receipt → dependency closure → source copy → image build → SBOM
→ second identical build → digest comparison. This repository change itself
authorizes no pull, build, push, provider action, or experiment.
