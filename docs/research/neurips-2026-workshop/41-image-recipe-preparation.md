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

The timestamp-stability successor action 011 also failed closed at the same
controller double-build gate after exporting `SOURCE_DATE_EPOCH`, setting
`BUILDKIT_MULTI_PLATFORM=1`, and pinning `linux/amd64`. Its failure and teardown
are sealed in `evidence/step7b-aws-builder-failure-011-20260802.json`; no
current production-surface image set exists.

The explicit exporter successor action 012 made the controller and model-server
double-build IDs equal, but failed closed at the benchmark-worker gate: its two
IDs were `sha256:6ab20d3b...b4d1139` and `sha256:86630dda...b3112af`.
The controller/model-server probes and SBOMs are preserved as partial evidence,
but the benchmark-worker probes, SBOM, and production-surface handshake were
not run. The failure and independent teardown are sealed in
`evidence/step7b-aws-builder-failure-012-20260802.json`; no current
image-bound production-surface receipt exists and action 012 is exhausted with
zero retries.

The build-owned mtime-normalization successor action 013 then failed closed at
the controller gate: its two image IDs were
`sha256:03cfc60c...4991c` and `sha256:652fd34a...03055`. The exact failure,
partial output inventory, and independent teardown are sealed in
`evidence/step7b-aws-builder-failure-013-20260802.json`; action 013 is
exhausted with zero retries. No role probes, SBOMs, or production-surface
handshake were run, and no current image-bound production-surface receipt
exists.

## Immutable base candidates (metadata only)

The real role recipes use the following pre-locked Linux/amd64 manifest identity.
It is an input-lock binding, not a completed image-pull or build receipt.

| Roles | Candidate | Linux/amd64 manifest digest |
| --- | --- | --- |
| controller, model-server, benchmark-worker | `vllm/vllm-openai` | `sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90` |
