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

## Live AWS action to recover first

The active action at handoff is the registered one-L40S p10 qualification:

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

Last observation before handoff: the instance was running; sealed model and
runner hashes had verified; the NVIDIA driver loaded; ECR login succeeded; no
output object had yet published. That observation is stale by definition.

Recover with read-only provider queries first:

```bash
aws sts get-caller-identity
aws ec2 describe-instances \
  --region us-east-1 \
  --instance-ids i-057047dfb078a326e \
  --query 'Reservations[0].Instances[0].{State:State.Name,LaunchTime:LaunchTime,Volume:BlockDeviceMappings[0].Ebs.VolumeId,Reason:StateTransitionReason}' \
  --output json
aws s3api list-objects-v2 \
  --region us-east-1 \
  --bucket pneuma-phase-b-892077329800 \
  --prefix runs/qualification/throughput-001/outputs/ \
  --query 'Contents[].{Key:Key,Size:Size,Modified:LastModified}' \
  --output json
```

If receipts exist, download all outputs, retain raw samples/stdout/stderr/return
codes, record S3 object versions and SHA-256 values, and verify with the exact
repository verifier. Do not interpret the largest rung as admitted unless every
registered gate passes. This qualification does not establish tool-call parity,
benchmark validity, a pilot result, or a scientific result.

If the action failed, preserve every failure artifact and record the failed
action. **Do not retry it.** A successor requires a newly hashed plan and fresh
action-specific admission. Never silently reuse this plan or authority.

After evidence publication, ensure the instance is terminated and independently
verify both the instance and encrypted delete-on-termination volume are absent.
Record the outcome in the append-only execution journal and spend ledger before
claiming closure.

## Completed evidence relevant to continuation

- C120 G-ROSTER qualification is committed (`fb61441`).
- Linux isolation qualification passed 33/33 registered pairs.
- Isolation teardown was independently rechecked: AWS returned
  `InvalidInstanceID.NotFound` for `i-01d2a6e41101fc6df` and
  `InvalidVolume.NotFound` for `vol-0ddb5ff0c80f2ce39`; closure is committed in
  `9abc45b`.
- The production execution-surface contract exists in commit `2e5c98e`, but
  real production adapters are still missing. Do not substitute decorative
  containers or fixture-only tests for that runtime evidence.
- Step 14 now requires eight receipt classes: input lock, G-ROSTER, Step 7B,
  production surface, AWS account, one-GPU admission, interruption/recovery,
  and Windows/Linux portability.

## Remaining dependency chain

Proceed in this order unless stronger current evidence changes the dependency
graph:

1. Seal `step5b-throughput-001`, including independent teardown verification.
2. Implement and qualify the real controller/model-server/benchmark-worker
   execution surface against the exact harness bytes.
3. Complete Step 7B reproducible three-role builds and SBOM receipts.
4. Execute and seal the AWS interruption/recovery drill.
5. Generate each portability bundle once, then independently verify the exact
   sealed bytes on Linux and native Windows. Require identical input-lock and
   G-ROSTER digests; Linux-only CUDA/Docker results must remain offline
   verifiable on Windows.
6. Run the final hostile Step 14 launch review against all eight receipt
   classes.
7. Complete bounded Step 4A through analysis, then revalidate Tasks 6/7
   continuity and finish Task 10 release preparation.
8. Before any canonical benchmark/model experiment, create fresh immutable,
   hash-bound scientific authority with its own spend, topology, retry,
   stop-condition, and claim boundaries.

No canonical Step 4B run, benchmark task episode, pilot, model experiment,
training run, or scientific claim is authorized merely by this handoff or the
user's standing approval. The preserved partial P0 screen remains an incomplete
experiment-only non-result and must not be resumed or rewritten without new
explicit experiment authority.

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
