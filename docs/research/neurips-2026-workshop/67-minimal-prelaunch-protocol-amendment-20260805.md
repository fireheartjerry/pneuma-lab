# Prospective protocol amendment: minimal official-study prelaunch gate

**Effective:** 2026-08-05, prospectively and before any official-study outcome
is accessed

**Scope:** official P0 / Step-4B launch admission only

## Amendment

The external Sigstore, Rekor, drand, and live Node roster ceremony is retired
as an official-study launch prerequisite. It remains historical implementation
and qualification evidence only. No future record may describe the replacement
path as having completed that ceremony.

The sufficient pre-outcome commitments are now:

1. a committed, content-addressed freeze of the exact eligible roster and
   protocol, bound to a full Git commit;
2. deterministic committed seeds for roster ordering, schedule, assignment,
   packet construction, model execution, benchmark execution, and unblinding;
3. registered C120 and C160 power/type-I validation on the frozen roster,
   followed by the preregistered largest-feasible-tier rule or a formal
   `FEASIBILITY_NO_GO`;
4. sealed assignment, packet, task-block-plan, blinding, and frozen-analysis
   authorities derived from those commitments;
5. one cryptographically verified official authorization bound to the exact
   final run specification, input lock, analysis graph, selected power report
   and tier, budget, topology, immutable image digests, and teardown policy.

Completed task blocks are not prelaunch artifacts because they contain
execution outcomes. The prelaunch artifact is the exact task-block plan and
authority; task-block records are emitted during execution.

Detectability results, completed task blocks, unblind/analysis receipts,
Step-14 hostile review, release review, and a completed P0 lineage are
execution or release evidence. They are not independent launch prerequisites.

Qualification and fixture-v2 work must not be repeated unless a concrete
infrastructure regression is observed.

## Prospective and non-retroactive status

This is a protocol amendment, not a claim about the original preregistration.
It does not rewrite prior records, validate the failed live ceremony, authorize
an official run by itself, or expose any outcome. Existing ceremony-based
artifacts remain interpretable under their historical contracts.

