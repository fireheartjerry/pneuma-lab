# 43 — Spend Protection

**Status:** Step 9 implementation complete; external verification pending

The local control plane rejects any reservation that violates either the
provider-balance or project-tier-stop invariant, rejects an unreserved
settlement, binds approvals to exact manifest bytes, and refuses new work after
a stale watchdog lease or projection overrun. Budget alarms are not represented
as enforcement.

All balances, ceilings, authorizations, and receipts used by tests are fixtures.
No live pricing, balance digest, AWS Budget, watcher, provider action, or spend
occurred. AWS balance cannot authorize Azure in the typed provider field.
