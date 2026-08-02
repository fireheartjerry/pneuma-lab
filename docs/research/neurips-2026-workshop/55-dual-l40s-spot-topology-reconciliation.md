# 55 — Dual-L40S Spot topology reconciliation

**Date:** 2026-08-02
**Authority:** DL-171; direct user direction after AWS approved 16 Spot G/VT
vCPUs in `us-east-1`
**Status:** local contract implementation complete; fresh external verification,
launch review, and execution remain pending

Machine-readable state: [`docs/project-status.json`](../../project-status.json).

## Binding AWS primary shape

The AWS primary path is exactly **two independent** `g6e.2xlarge` Spot workers
in `us-east-1`. Each worker has 8 vCPUs, one NVIDIA L40S, and 44 GiB usable
device memory. Batch remains disabled at rest with `minvCpus=0`; its Spot
environment is capped at `maxvCpus=16`, uses
`SPOT_PRICE_CAPACITY_OPTIMIZED`, and permits at most two whole-worker jobs.

Every official work identifier is assigned before submission by the frozen
controller using canonical lexicographic round-robin partitioning:
`worker-0` receives positions 0, 2, 4, ... and `worker-1` receives positions
1, 3, 5, .... The partition is a complete, disjoint cover of the frozen work
set. It cannot be chosen by queue arrival order, worker availability, arm,
outcome, cost, or a post-hoc retry decision.

Each worker may admit only `l40s-tp1-32768` or `l40s-tp1-65536`, selected by
the existing OOM, tool-call, output-parity, and p10-throughput rules. TP2,
H100 substitution, multi-GPU model parallelism, and simulator co-location
remain prohibited. Two workers increase independent throughput and deadline
headroom; they do not change the subject, arms, estimands, roster, or analysis.

The required account receipt must show at least 16 applied Spot G/VT vCPUs and
at least 8 On-Demand G/VT vCPUs. The latter is a recovery floor only: normal
official execution targets the full two-worker Spot envelope. If one or both
Spot workers are unavailable or interrupted, the controller records the exact
boundary, freezes the canonical partition, and resumes only under a fresh
admitted recovery action. It must not reassign a completed, in-flight, or
failed work identifier to another worker under the same action.

## Preserved boundaries

- The AWS quota email and a read-only account receipt establish account quota,
  not current Spot capacity. A fresh capacity and price receipt remains
  required at launch.
- A two-worker static contract is not a deployment, GPU smoke, pilot, model
  episode, benchmark result, or scientific claim.
- Every worker must have a matching image/runtime admission receipt, with a
  distinct EC2 instance identity and raw-measurement digest. One worker's pass
  cannot be silently generalized to its peer or relabelled as two workers.
- The controller must remain outside the two-GPU scientific worker budget or
  use separately authorized non-GPU capacity. It cannot consume a registered
  worker slot and then claim two-worker scientific throughput.
- The registered ceiling and stop/no-go rules remain binding. Parallelism does
  not permit more tasks, different arms, altered endpoints, or an extra retry.
- Spot loss is a recorded protocol event, never a reason to relax blinding,
  isolation, artifact binding, or exact teardown.

## Required fresh evidence before launch review can clear

1. A read-only account/capacity/pricing receipt proving the two-worker Spot
   route remains applicable at the intended start time.
2. Terraform L1 validation and a fresh L3 plan that binds the two-worker Spot
   environment, Spot Fleet role, exact AMI, image, and bootstrap bytes.
3. One bound OOM/tool-call/output-parity/p10 receipt for each worker index,
   compiled from distinct retained raw-measurement bytes using the same frozen
   per-worker rung protocol.
4. A no-overlap allocation receipt and interruption/recovery drill over the
   two-worker partition.
5. A fresh Step 14 hostile review that consumes the revised topology and all
   four receipt classes above.

No item above has been executed or inferred by this local reconciliation.

For the bounded, non-AWS VPS preflight that may precede a separately
authorized launch review, use
[`56-vps-dual-worker-preflight-prompt.md`](56-vps-dual-worker-preflight-prompt.md).
