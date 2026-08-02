# VPS agent handoff — NeurIPS execution continuation

**Prepared:** 2026-08-01  
**Repository:** `fireheartjerry/pneuma-lab`  
**Branch:** `codex/neurips-2026-empirical`  
**Handoff commit floor:** `9abc45b` (`Close isolation teardown evidence`)

This document transfers orchestration from the Windows Codex session to a
persistent Linux VPS session. It is an operational handoff, not scientific
authority and not permission to weaken any fail-closed contract.

## First actions on the VPS

1. Clone or update the repository and check out
   `codex/neurips-2026-empirical`.
2. Read `AGENTS.md` completely.
3. Read, in order:
   - `docs/project-status.json`
   - `docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md`
   - this document
   - `docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md`
   - the tail of `docs/research/neurips-2026-workshop/33-execution-journal.md`
4. Treat the repository and AWS provider state as authoritative. Re-observe all
   live state before relying on this snapshot.
5. Run the status checker and inspect the worktree before changing anything.

```bash
git fetch origin
git checkout codex/neurips-2026-empirical
git pull --ff-only
git status --short
python -m pneuma_lab.status --check
```

Do not copy AWS credentials, private signing keys, or browser session material
into the repository, prompts, tmux scrollback, or logs. Prefer a scoped IAM
instance role/workload identity for unattended VPS operation. AWS Agent Toolkit
is useful for agent tooling but does not itself provide process persistence;
run the agent inside `tmux` and keep its receipts on durable storage.

## Reconciled AWS actions

The previously active one-L40S p10 qualification `step5b-throughput-001` is
sealed and independently torn down. Its bounded receipt remains
infrastructure evidence only: it is not a benchmark, pilot, experiment, or
scientific result.

- action: `step5b-throughput-001`
- region: `us-east-1`
- instance: `i-057047dfb078a326e`
- observed root volume: `vol-0160c8cc693ca39d2`
- launch time: `2026-08-01T19:33:15Z`
- plan: `docs/research/neurips-2026-workshop/evidence/throughput-plan-001-20260801.json`
- plan SHA-256: `ad69fe00f42c8eef23690c3f367cf9c16ba95211e3d9e9a7009485582692e6c1`
- hard ceiling: `$5.00`
- projected spend: `$4.00`
- runtime ceiling: 100 minutes
- retry budget: **zero**
- input-lock SHA-256:
  `e6746ad843b0da9a6144fa84a5a231dd350b6845a321ffaff171df4540f67b84`
- immutable worker image:
  `sha256:1fc54d73f9ec36356bec5c2c8497b671f72a9e43c0bae4fbb84be3ee6ede9ae2`
- output prefix:
  `s3://pneuma-phase-b-892077329800/runs/qualification/throughput-001/outputs/`

- `step5b-throughput-001` completed both registered rungs above the frozen p10
  floor; its instance and encrypted root volume are absent. The exact receipt
  and raw-object verification remain in the execution journal.
- `step7b-aws-builder-009` then completed the three-role double-build/SBOM
  action. Its exact success receipt is
  `evidence/step7b-aws-builder-success-009-20260802.json`; instance
  `i-0bdfb8bedd57ab630`, root `vol-09c73e10cb4679fa6`, and temporary group
  `sg-0c3acb5ff13aebea2` are independently absent.

## Completed evidence relevant to continuation

- C120 G-ROSTER qualification is committed (`fb61441`).
- Linux isolation qualification passed 33/33 registered pairs.
- Isolation teardown was independently rechecked: AWS returned
  `InvalidInstanceID.NotFound` for `i-01d2a6e41101fc6df` and
  `InvalidVolume.NotFound` for `vol-0ddb5ff0c80f2ce39`; closure is committed in
  `9abc45b`.
- The production execution-surface contract exists in commit `2e5c98e`; the
  bounded controller → model-server → benchmark-worker handshake is now
  implemented and locally tested in document 54. Real image E2E receipts are
  still missing. Do not substitute fixture-only tests for that provider-bound
  evidence.
- Step 7B reproducible three-role builds and SBOMs are now externally verified
  under the zero-retry KMS-admitted action 009. This closes image-build
  evidence only; it does not close the production execution surface.
- The successor action 010 bound to the new production-surface handshake
  failed closed before probes because its two controller image IDs differed
  (`0a3834…996b9` versus `84fef3…0b2da`). Its failure and teardown are sealed
  in `evidence/step7b-aws-builder-failure-010-20260802.json`; it is exhausted
  with zero retries. Do not treat action 009's older-runtime images as E2E
evidence or silently reuse action 010.
- The timestamp-stability successor action 011 also failed closed at the same
  controller double-build gate despite `SOURCE_DATE_EPOCH`,
  `BUILDKIT_MULTI_PLATFORM=1`, and `linux/amd64`. Its failure and teardown are
  sealed in `evidence/step7b-aws-builder-failure-011-20260802.json`; action 011
  is exhausted and the production-surface gate remains open.
- The explicit exporter successor action 012 passed controller and model-server
  reproducibility, then failed closed at benchmark-worker reproducibility:
  image IDs `sha256:6ab20d3b...b4d1139` and `sha256:86630dda...b3112af` differed.
  Its partial receipts and teardown are sealed in
  `evidence/step7b-aws-builder-failure-012-20260802.json`; benchmark-worker
  probes/SBOM and the production-surface handshake were not run. Action 012 is
  exhausted with zero retries; no current image-bound production-surface
  receipt exists.
- The build-owned mtime-normalization successor action 013 failed closed at
  the controller reproducibility gate: image IDs
  `sha256:03cfc60c...4991c` and `sha256:652fd34a...03055` differed. Its
  failure, partial output inventory, and teardown are sealed in
  `evidence/step7b-aws-builder-failure-013-20260802.json`; no role probes,
  SBOMs, or production-surface handshake ran. Action 013 is exhausted with
  zero retries; do not treat any partial output as a production-surface pass.
- The pinned Buildx/BuildKit successor action 014 failed closed before any
  build because Amazon Linux's preinstalled `curl-minimal` conflicted with the
  bootstrap's explicit `curl` package request. Its failure and teardown are
  sealed in `evidence/step7b-aws-builder-failure-014-20260802.json`; action
  014 is exhausted with zero retries, and no production-surface evidence was
created. The next action must bind the corrected bootstrap bytes afresh.
- Corrected successor action 015 is now prepared but not admitted or run. It
  binds source commit `98dd81a...c806`, archive
  `9229854312d86740e02b1cff25419abc7aaaff3bdfc023973a92d7940b80b579`, the
  curl-minimal-safe bootstrap, pinned Buildx/BuildKit, and fresh no-ingress
  security group `sg-04331c50b912dac3d`. Plan
  `dbc75690017269be0544d9cc9c3fe3d8870928058fa80cac9c08acd38d35fa5a` is a
  zero-retry candidate only; no provider execution or production-surface
  receipt exists.
- Admitted action 015 installed and verified Buildx `v0.13.1`, then failed
  closed because `docker buildx inspect` did not report the sealed BuildKit
  `v0.13.2` version. No role builds, SBOMs, probes, or production-surface
  handshake ran. Its output inventory and teardown are sealed in
  `evidence/step7b-aws-builder-failure-015-20260802.json`; action 015 is
  exhausted with zero retries. A successor must bind and publish the exact
  builder inspection output before any further build attempt.
- Diagnostic successor action 016 is prepared but not admitted or run. It
  binds source commit `4a067231...e0a`, archive
  `26ab4f48f37b6492c594c0775b8e9bcb5546f0d4a36b14a3ec17621169764e39`, the
  inspection stdout/stderr sealing repair, pinned Buildx/BuildKit, and fresh
  no-ingress security group `sg-0c527fadf035615a6`. Plan
  `2cc7f3724709a831ff925bfc7d0c51a2b39d6a0589ee573e438545aa89983e6d` is a
  zero-retry candidate only; no provider execution or production-surface
  receipt exists.
- Diagnostic action 016 verified pinned Buildx `v0.13.1` and BuildKit
  `v0.13.2`, then failed at the first controller export because Amazon Linux
  Docker 25's Docker exporter cannot export the locked vLLM base manifest list.
  No controller image, SBOM, role probe, or production-surface handshake ran.
  Its log, builder inspection, and teardown are sealed in
  `evidence/step7b-aws-builder-failure-016-20260802.json`; action 016 is
  exhausted with zero retries. The next action must bind a platform-specific
  exporter repair without weakening the Step 5B base lock.
- Platform-export successor action 017 is prepared but not admitted or run. It
  binds source commit `fdd0b6e...bf41`, archive
  `520badd293e94dfb557e8a8913415b13ce0237c9065cc3b2bc850ac9c1c042b3`, pinned
  Buildx/BuildKit, the retained single-platform/timestamp exporter controls,
  and fresh no-ingress security group `sg-0fa80f9418264fc47`. Plan
  `5ce31bbc9485e2b5a1d23568390ebf5331ddf852be4b38ec3b282874408b365c` is a
  zero-retry candidate only; no provider execution or production-surface
  receipt exists.
- Admitted action 017 completed all three reproducible builds, probes, and
  SBOMs, then failed closed before the production-surface handshake because
  the launcher duplicated the role already sealed in each image ENTRYPOINT.
  Failure and teardown are sealed in
  `evidence/step7b-aws-builder-failure-017-20260802.json`; action 017 is
  exhausted with zero retries.
- Successor action 018 bound the image-entrypoint launcher repair and was
  admitted once. It again completed all three builds, probes, and SBOMs, then
  failed closed when the strict image-bound production surface could not open
  its mode-0600 read-only harness bind under `--cap-drop ALL`. Local replay
  reproduced the `PermissionError`; repair commit `f5a871d` makes non-secret
  harness/predecessor binds readable before strict containers. Failure and
  teardown are sealed in
  `evidence/step7b-aws-builder-failure-018-20260802.json`; action 018 is
  exhausted with zero retries and no production-surface receipt exists.
- Action 019 was the next independently admitted step and bound current
  committed source to a fresh no-ingress security group. Action 018's package,
  instance, group, and receipt were not reused; no model, benchmark, pilot, or
  experiment was permitted.
- Action 019 was signed and preflighted, but its one permitted EC2 launch was
  rejected before instance creation with `InvalidGroup.NotFound` for the fresh
  SG, even though an immediate independent read found that SG afterward. This
  is sealed as a control-plane propagation failure in
  `evidence/step7b-aws-builder-failure-019-20260802.json`; action 019 is
  exhausted with zero retries and its SG is deleted. Action 020 must bind a
  fresh SG and a consistency-gated creation/launch path; action 019's launch
  cannot be replayed.
- Action 020 was signed, uploaded, and launched once through that
  consistency-gated CLI path. It completed all three reproducible image
  builds, positive/wrong-hash probes, and non-empty SBOMs, then failed closed
  at the cloud image-bound production-surface subprocess before writing a
  handshake receipt. The 21-object failure inventory and full cleanup are
  sealed in `evidence/step7b-aws-builder-failure-020-20260802.json`; the
  instance self-terminated, its encrypted root and ENI disappeared, and its
  temporary SG was deleted once and verified absent. A local replay with the
  exact harness and debug images passes, but the cloud child stderr was not
  preserved, so a fresh action 021 must add diagnostic stderr/first-role
  capture before any production-surface claim. No model, benchmark, pilot, or
  experiment ran.
- Admitted successor action 021 was prepared from diagnostic commit `1bb54ab`
  with a fresh no-ingress SG `sg-0c8eb506d362a5d3d`; it persisted the child
  production-surface return code/stdout/stderr before raising. Its plan bound
  archive `38521fcd...ca93` and digest
  `ebc0bec75480b140df2b12ff72c5eeefc351973d659629b70605207cd43a263b`.
  The one permitted launch completed all three reproducible builds, probes, and
  SBOMs, then failed closed before any role container launched: the AMI system
  Python's old `jsonschema` lacked `Draft202012Validator`. The exact traceback,
  22-object inventory, and independent teardown are sealed in
  `evidence/step7b-aws-builder-failure-021-20260802.json`; action 021 is
  exhausted with zero retries. A fresh action 022 must bind an isolated,
  hash-pinned runtime dependency and requalify the production surface.
- Step 14 now requires eight receipt classes: input lock, G-ROSTER, Step 7B,
  production surface, AWS account, one-GPU admission, interruption/recovery,
  and Windows/Linux portability.

## Remaining dependency chain

Proceed in this order unless stronger current evidence changes the dependency
graph:

1. Implement and qualify the real controller/model-server/benchmark-worker
   execution surface against the exact harness bytes.
2. Execute and seal the AWS interruption/recovery drill.
3. Generate each portability bundle once, then independently verify the exact
   sealed bytes on Linux and native Windows. Require identical input-lock and
   G-ROSTER digests; Linux-only CUDA/Docker results must remain offline
   verifiable on Windows.
4. Run the final hostile Step 14 launch review against all eight receipt
   classes.
5. Complete bounded Step 4A through analysis, then revalidate Tasks 6/7
   continuity and finish Task 10 release preparation.
6. Before any canonical benchmark/model experiment, create fresh immutable,
   hash-bound scientific authority with its own spend, topology, retry,
   stop-condition, and claim boundaries.

No canonical Step 4B run, benchmark task episode, pilot, model experiment,
training run, or scientific claim is authorized merely by this handoff or the
user's standing approval. The preserved partial P0 screen remains an incomplete
experiment-only non-result and must not be resumed or rewritten without new
explicit experiment authority.

## KMS-backed signing is now active

The VPS has a non-exporting signing path. Use these profiles with the ambient
AWS session variables cleared (the original root `aws login` environment can
override profile credentials):

```bash
env -u AWS_SESSION_TOKEN -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY \
  AWS_PROFILE=pneuma-kms-signer \
  PATH="$HOME/.local/bin:$PATH" \
  aws sts get-caller-identity
```

- `pneuma-signer-bootstrap` is a narrowly scoped IAM user whose only permission
  is `sts:AssumeRole` on `pneuma-kms-signer-v1`.
- `pneuma-kms-signer` is the temporary role profile with KMS `Sign`, `Verify`,
  `GetPublicKey`, and `DescribeKey` only for the registered signer key and only
  with `ED25519_SHA_512` signing.
- KMS alias: `alias/pneuma-approver`; key ARN and public bytes are bound in
  `kms-signer-bootstrap-plan-004-20260801.json`.
- Registered public key: `pneuma-kms-20260801-r1`.
- Root direct `kms:Sign` was independently observed as denied; one role-backed
  signature was verified offline.

The exact Step 7B package is now signed through KMS and committed. Verify it
against the registry and plan before executing any local build action. Never
print, export, rotate, or copy the IAM secret or any KMS private material.

## Operating standard

- Maintain the distinction between `implementation_complete`, `E2E_pending`,
  and scientifically complete.
- Append scientific executions and deviations to
  `33-execution-journal.md`; update status/handoff documents only at coherent
  milestones.
- Use one narrow high-signal test and one static check per implementation slice;
  software tests have a 60-second ceiling unless explicitly extended.
- Never let prose outrun committed evidence.
- Preserve unrelated worktree changes.
- Commit and push each coherent evidence milestone to
  `codex/neurips-2026-empirical`.
- Continue autonomously while safe, scoped work remains. Stop only for a real
  authority boundary, exhausted retry/spend envelope, missing human
  authentication, or another condition the repository explicitly makes
  non-delegable.

## Startup prompt for the VPS agent

```text
Continue the Pneuma Lab NeurIPS execution from the authoritative VPS handoff at
docs/research/neurips-2026-workshop/53-vps-agent-handoff.md on branch
codex/neurips-2026-empirical. Read AGENTS.md and every prerequisite named by the
handoff completely before acting. Re-observe the repository and AWS state; do
not trust stale prose. Recover and seal the live zero-retry
step5b-throughput-001 action first, preserving all success or failure evidence
and independently verifying teardown. Then advance every remaining launch gate
in dependency order. Work autonomously under the user's standing approval, but
never bypass immutable hash-bound authority, spend ceilings, retry limits,
scientific authorization, or fail-closed receipt contracts. Keep the execution
journal, spend ledger, status, commits, and remote branch synchronized at
coherent milestones. Do not claim an experiment or scientific result from
qualification evidence.
```

## `/goal` statement

```text
/goal Complete Pneuma Lab's full pre-experiment NeurIPS launch-readiness chain
from the authoritative state on codex/neurips-2026-empirical: recover and seal
the active zero-retry p10 AWS qualification; implement and qualify the real
controller/model-server/benchmark-worker production surface; complete Step 7B
reproducible three-role builds and SBOM receipts; pass the AWS
interruption/recovery drill; close exact-byte Windows/Linux receipt portability;
pass the eight-receipt hostile Step 14 review; complete bounded Step 4A through
analysis and Tasks 6-10 continuity/release preparation; and prepare the fresh
immutable hash-bound scientific action needed to run the actual experiment.
Preserve all spend, retry, teardown, evidence, and claim boundaries; do not
declare completion until every requirement is proven by current committed
evidence.
```
