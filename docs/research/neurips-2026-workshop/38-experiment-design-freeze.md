# 38 — Resampling Null Experiment Design Freeze

**Status:** registered implementation freeze; not an execution authorization
**Date:** 2026-07-31
**Authority records:** DL-148, DL-149, DL-161, and DL-171

> **2026-08-02 topology amendment and reconciliation:** DL-171 supersedes the
> former sequential one-L40S execution shape with two independent
> `g6e.2xlarge`/L40S Spot workers and canonical disjoint partitioning. See
> `55-dual-l40s-spot-topology-reconciliation.md`. The scientific design below
> remains frozen. Per-worker fit/throughput admission, partition/recovery, and
> Step 14 review remain blocking.

## Frozen object

This record ratifies, by reference, the Resampling Null design in
`docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md` and its
controlling implementation plan. It does not replace either document or select
new scientific inputs, except that DL-149 expressly supersedes the AWS-only
application of design §13 Tier-1 item 7 as recorded below.

The frozen object is the complete subject-and-design contract already specified
there: the REAL, SHAM, NONE, and RESAMPLE arms; ITT binary-success endpoint;
co-primary content and excess estimands; seven-condition decision rule;
resolution floor; failure criteria; admission gates; and the pinned SWE-bench
Live/MultiLang and tau2-bench roster definitions, Qwen3.6-35B-A3B-FP8 subject,
and Qwen3.5-9B simulator.

DL-171 supersedes the former one-worker topology in the referenced design. The
AWS primary subject topology is frozen as two independent `g6e.2xlarge` Spot
workers: 16 Spot vCPUs total, with each worker providing 8 vCPUs, 64 GiB host
memory, one L40S, and 44 GiB usable device memory. The only candidate context
rungs are both TP1 on each independently admitted worker:

1. one worker L40S, TP1, 32,768 tokens;
2. one worker L40S, TP1, 65,536 tokens.

The pilot may select only the largest rung passing OOM, tool-call,
output-parity, and p10-throughput gates on **each** worker. It may not invent,
substitute, or interpolate a configuration, and it may never use efficacy, arm
effects, benchmark outcomes, or any other outcome signal for selection.

## Reconciliations and gates

- The design, rather than stale roadmap wording, is authoritative for the
  pinned model and roster. SWE-bench Verified and LiveCodeBench remain rejected
  alternatives, not fallback options.
- `G-ROSTER` is registered as a blocking gate. Both C120 and C160 remain
  `FEASIBILITY_NO_GO` until every split satisfies the contract's eligibility
  inequality through the full base-commit, image, isolation, and three-pair
  qualification audit, or a reviewed protocol amendment is separately
  registered. No final experiment manifest, pilot authorization, or
  launch-readiness claim may occur first.
- The tau2 version-string discrepancy is resolved only by the already-pinned
  tag object, peeled commit, source blobs, lockfile blob, environment image,
  and installed-dependency receipts. A human-readable version string is not an
  authority override.
- Stale decision-log model rows belong to retired placebo/gauge work and do not
  alter this freeze. The calendar in the design is historical planning prose,
  not a permission or schedule commitment.
- Azure is a separately authorized parity/precision replication, not an
  AWS-only-pilot dependency. For an AWS-only pilot, Tier-1 item 7 is amended to
  require the independent **AWS** lease-expiry kill drill; the Azure drill is
  required only before an Azure slice. Azure has no verified spendable balance,
  authorization, quota, or account-bound plan, so no Azure action is licensed
  by this decision. DL-149 is the controlling adjudication of that otherwise
  conflicting clause; all other design gates remain unchanged.
- The user reports USD 10,000 of Azure credits incoming. This is acknowledged
  as a pending planning resource, not a verified spendable balance. Once
  verified, it may support separately designed training or other experiments;
  it does not modify or authorize this inference protocol.
- The AWS controller cannot co-locate the τ³ simulator with the primary
  subject. Any simulator capacity is a separate, explicitly metered and
  separately authorized dependency; it is not supplied by Azure or inferred
  from this single-GPU topology. Azure remains a separate subject and may not
  be pooled with the AWS FP8 results.

## State and non-claims

This completes the documentation/authority implementation of Step 4. Roster
feasibility remains externally unverified; Step 14 review and every scientific
execution remain pending. This record does not retrieve an input, create or
modify cloud resources, spend credits, authorize a pilot, execute Step 4B, or
establish a scientific result.
