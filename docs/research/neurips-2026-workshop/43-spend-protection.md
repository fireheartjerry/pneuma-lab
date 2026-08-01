# 43 — Spend Protection

**Status:** Step 9 implementation complete; external verification pending

The local control plane rejects any reservation that violates either the
provider-balance or project-tier-stop invariant, rejects an unreserved
settlement, binds approvals to exact manifest bytes, and refuses new work after
a stale watchdog lease or projection overrun. Budget alarms are not represented
as enforcement.

The unattended low-risk policy removes digests from the operator interaction.
An operator approves one readable envelope: at most USD 5 per job and USD 25 in
any rolling 30-day window, with no more than two retries, limited to bounded
retrieval, non-scientific smoke checks, and bounded API pilots. Canonical
experiments, scientific replications, training, and result promotion always
require separate human-readable authority. The controller computes policy,
request, and input-binding digests only in machine receipts.

The committed policy is a `candidate`, not an active policy. Activation,
revocation, expiry, provider mismatch, action-class drift, retry excess, invalid
input binding, per-job excess, rolling-window excess, and future-dated history
all fail before provider action. Editing a policy does not reset its rolling
spend because receipts accrue by stable `policy_id`, while each receipt also
preserves the exact policy digest used for that admission.

All balances, ceilings, authorizations, and receipts used by tests are fixtures.
No live pricing, balance digest, AWS Budget, watcher, provider action, or spend
occurred. AWS balance cannot authorize Azure in the typed provider field.
The unattended controller remains local fixture machinery: it does not
authenticate provider billing data, activate the candidate, or contact a
provider.
The admission function also depends on the controller supplying the complete
receipt history for the stable policy ID. A caller-selected subset would not be
an enforcement ledger; live activation therefore remains blocked until the
durable ledger/watchdog integration proves history completeness.
