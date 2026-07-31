# 38 — Resampling Null Experiment Design Freeze

**Status:** registered implementation freeze; not an execution authorization
**Date:** 2026-07-31
**Authority records:** DL-148, DL-149, and prospective amendment DL-161

> **2026-07-31 prospective topology amendment:**
> `49-single-l40s-topology-amendment.md` supersedes the AWS four-GPU execution
> shape with one `g6e.2xlarge`/L40S and sequential arm/replica execution. The
> scientific design below remains frozen. Implementation reconciliation,
> one-GPU fit/throughput admission, and Step 14 review remain blocking.

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

Topology is frozen as a four-rung candidate ladder plus its deterministic
selection rule, not as an open configuration choice:

1. one L40S, TP1, 32,768 tokens;
2. one L40S, TP1, 65,536 tokens;
3. two L40S, TP2, 65,536 tokens; then
4. one H100 94 GB, TP1, at the largest validated cap not exceeding 131,072
   tokens.

The pilot may select only the largest rung passing OOM, tool-call,
output-parity, and p10-throughput gates. It may not invent, substitute, or
interpolate a configuration, and it may never use efficacy, arm effects,
benchmark outcomes, or any other outcome signal for selection.

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

## State and non-claims

This completes the documentation/authority implementation of Step 4. Roster
feasibility remains externally unverified; Step 14 review and every scientific
execution remain pending. This record does not retrieve an input, create or
modify cloud resources, spend credits, authorize a pilot, execute Step 4B, or
establish a scientific result.
