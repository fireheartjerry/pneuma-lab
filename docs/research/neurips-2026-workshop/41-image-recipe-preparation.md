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

The pinned Buildx/BuildKit successor action 014 did not reach the build: the
Amazon Linux bootstrap requested `curl` even though the AMI already provides
`curl-minimal`, so `dnf` failed closed before Buildx or BuildKit installation.
The versioned failure output and independent teardown are sealed in
`evidence/step7b-aws-builder-failure-014-20260802.json`; action 014 is
exhausted with zero retries. The next successor removes only that conflicting
package request; no image, SBOM, or production-surface evidence is promoted
from action 014.

The corrected successor action 015 is prepared but not yet admitted or run.
It binds source commit `98dd81a...c806`, archive
`9229854312d86740e02b1cff25419abc7aaaff3bdfc023973a92d7940b80b579`, the
curl-minimal-safe bootstrap, pinned Buildx/BuildKit, and fresh no-ingress
security group `sg-04331c50b912dac3d`. Plan
`dbc75690017269be0544d9cc9c3fe3d8870928058fa80cac9c08acd38d35fa5a` is a
zero-retry candidate only; no upload, signature, image, SBOM, or production
surface result exists yet.

The admitted corrected action 015 installed Docker and Buildx `v0.13.1` but
failed closed while validating the pinned Docker-container builder: the host's
`docker buildx inspect` output did not report the sealed BuildKit `v0.13.2`
version. No role build, SBOM, probe, or production-surface handshake ran. The
versioned outputs and teardown are sealed in
`evidence/step7b-aws-builder-failure-015-20260802.json`; action 015 is
exhausted with zero retries. The next successor must publish the exact builder
inspection bytes before attempting any image build.

Diagnostic successor action 016 is prepared but not yet admitted or run. It
binds source commit `4a067231...e0a`, archive
`26ab4f48f37b6492c594c0775b8e9bcb5546f0d4a36b14a3ec17621169764e39`, the
inspection stdout/stderr sealing repair, pinned Buildx/BuildKit, and fresh
no-ingress security group `sg-0c527fadf035615a6`. Plan
`2cc7f3724709a831ff925bfc7d0c51a2b39d6a0589ee573e438545aa89983e6d` is a
zero-retry candidate only; no provider execution or new image evidence exists.

The diagnostic action 016 verified the pinned Buildx/BuildKit stack and then
failed at the first controller export: Amazon Linux Docker 25 reported that
its Docker exporter cannot export the locked vLLM base manifest list. No
controller image, SBOM, role probe, or production-surface handshake ran. The
versioned log, builder inspection, and teardown are sealed in
`evidence/step7b-aws-builder-failure-016-20260802.json`; action 016 is
exhausted with zero retries. The next successor must bind a platform-specific
export repair without weakening the Step 5B base lock.

Platform-export successor action 017 is prepared but not yet admitted or run.
It binds source commit `fdd0b6e...bf41`, archive
`520badd293e94dfb557e8a8913415b13ce0237c9065cc3b2bc850ac9c1c042b3`, pinned
Buildx/BuildKit, the retained single-platform/timestamp exporter controls, and
fresh no-ingress security group `sg-0fa80f9418264fc47`. Plan
`5ce31bbc9485e2b5a1d23568390ebf5331ddf852be4b38ec3b282874408b365c` is a
zero-retry candidate only; no provider execution or new image evidence exists.

Admitted action 017 completed the three role builds, positive and wrong-hash
probes, and non-empty SBOMs, then failed closed before the production-surface
handshake because its launcher supplied a duplicate role argument after the
role already sealed in each image ENTRYPOINT. The failure and teardown are
sealed in `evidence/step7b-aws-builder-failure-017-20260802.json`; action 017
is exhausted with zero retries.

Successor action 018 bound the corrected image-entrypoint launcher and again
completed all three builds, probes, and SBOMs. It failed closed at the strict
image-bound production surface when a mode-0600 read-only harness bind could
not be opened under `--cap-drop ALL`; a local strict replay reproduced the
`PermissionError`. The repair in commit `f5a871d` makes non-secret harness and
predecessor binds readable before strict containers, and the repaired local
image-bound replay passes. The complete cloud output inventory and independent
teardown are sealed in
`evidence/step7b-aws-builder-failure-018-20260802.json`; no production-surface
receipt exists and action 018 is exhausted with zero retries.

Action 019 was the next permitted successor and received a fresh admission,
fresh no-ingress security group, and a new archive of the committed repair.
Action 018's package, group, instance, and partial output were not reused as
authority. This remains build/qualification work only; no model, benchmark,
pilot, experiment, or scientific result is authorized.

Action 019 was then admitted once and rejected before instance creation by
`InvalidGroup.NotFound` on the EC2 launch call, despite an immediate independent
read finding the tagged group. The failure is sealed in
`evidence/step7b-aws-builder-failure-019-20260802.json`; no bootstrap, image,
SBOM, or production-surface output exists, and its SG was independently
deleted. Action 019 is exhausted with zero retries. The next successor must
bind a fresh group and prove a consistency-gated group-readback before its
single launch call; no action-019 resource or authorization may be reused.

Action 020 was the fresh admitted successor. It created and configured its
security group through the same CLI path used for launch, proved the exact
readback gate, and launched once as `i-0f9fa01a181cccca2`. All three image
builds, probes, and SBOMs passed, but the cloud image-bound production-surface
subprocess failed closed before a handshake receipt. The complete 21-object
inventory and independent teardown are sealed in
`evidence/step7b-aws-builder-failure-020-20260802.json`; no production-surface
or scientific result may be claimed. Successor action 021 must preserve the
child stderr and first-role diagnostics before another bounded qualification.

Admitted action 021 was prepared from diagnostic commit `1bb54ab` and a fresh
no-ingress SG `sg-0c8eb506d362a5d3d`. It bound archive
`38521fcd...ca93`, plan digest
`ebc0bec75480b140df2b12ff72c5eeefc351973d659629b70605207cd43a263b`, and an
executor that persisted the production-surface command return code/stdout/stderr
before raising. The one permitted launch completed all three reproducible
builds, probes, and SBOMs, then failed closed before role launch because the
AMI system Python lacked `Draft202012Validator` from the repository's required
`jsonschema` runtime. The exact traceback, 22-object inventory, and independent
teardown are sealed in
`evidence/step7b-aws-builder-failure-021-20260802.json`; action 021 is
exhausted with zero retries. Action 022 must bind an isolated, hash-pinned
runtime dependency before another production-surface qualification.

## Immutable base candidates (metadata only)

The real role recipes use the following pre-locked Linux/amd64 manifest identity.
It is an input-lock binding, not a completed image-pull or build receipt.

| Roles | Candidate | Linux/amd64 manifest digest |
| --- | --- | --- |
| controller, model-server, benchmark-worker | `vllm/vllm-openai` | `sha256:7a0f0fdd2771464b6976625c2b2d5dd46f566aa00fbc53eceab86ef50883da90` |
