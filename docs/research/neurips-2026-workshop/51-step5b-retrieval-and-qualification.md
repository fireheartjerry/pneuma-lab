# 51 — Step 5B Retrieval Workflow and the G-ROSTER Determination

**Status:** `implementation_complete`; `external_verification_pending`;
`authorization_pending`. No external input has been retrieved.
**Date:** 2026-07-31
**Authority records:** DL-162, DL-163; ledger rows CL-026, CL-027

This record does two things. It implements the fail-closed workflow that Step 5B
would execute *if* it were authorized, and it evaluates the registered G-ROSTER
inequality against the only roster evidence that exists. It retrieves nothing,
promotes nothing, and authorizes nothing.

## 1. The retrieval workflow

`src/pneuma_lab/cloud/retrieval.py` implements the Step 5B contract as code that
cannot run without authority.

**Authorization.** `cloud-retrieval-authorization` records carry a `status` of
either `candidate` or `authorized`. The invariant is exact: an `authorized`
record requires **both** a `CL-0xx` ledger row and a human authorization block;
a `candidate` must have **neither**. A half-signed record fails closed rather
than degrading to either state.

`signature_sha256` must equal `authorization_binding_digest`, computed over the
record with the signature removed plus the approver and grant time. A signature
therefore cannot be free-text hex, cannot survive an edit to the scopes, byte
ceiling, or lock digest, and cannot be lifted from another record. **Stated
plainly: this is a binding digest, not a cryptographic authentication.** It
proves the approval names this exact record; it does not prove who computed it.
Approver authentication needs a key ceremony this package deliberately does not
implement, so a signed record is evidence of intent, never of identity.

`require_authorized` additionally recomputes the input-lock digest and refuses
any authorization not bound to that exact lock. `ledger_row_id` is checked for
the `CL-0xx` shape only; nothing verifies the row exists, so it records an
intended ledger reference rather than proving one.

**Plans.** `build_audit_plan` derives ordered retrieval steps for the model,
tokenizer, benchmark, **verifier-source**, and container-base scopes from
immutable values only — 40-hex revisions and `linux/amd64@sha256:` digests. No
tag is resolved and no registry is consulted. Mirror paths are scoped by kind,
repository, and reference, and uniqueness is enforced on the destination path,
so two artifacts can never be written to one location and clobber it. The plan
is buildable from a *candidate*, which is what makes an unexecuted plan
reviewable in advance. `build_receipt_verification_plan` covers the licence and
contamination receipts — audit outputs verified as mirrored files rather than
fetched — and binds the input-lock digest like the retrieval plan does.

**Execution.** `retrieve_and_verify` is the only function that moves bytes, and
it does so exclusively through a caller-injected fetcher; the package has no
network client. It requires a real authorization and verifies every artifact
against its pinned digest before the next step runs. The byte ceiling is checked
*before* each fetch against caller-supplied `declared_sizes` when available, so
an over-budget step is refused rather than transferred; the post-fetch check
remains as a backstop for a fetcher that returns more than it declared. Without
declared sizes the ceiling can only report an overrun after the bytes have
moved, which is a real limit of an injected-fetcher design and is why a
retrieval plan should be size-declared before it is signed.

**What exists.** `fixtures/cloud/retrieval-authorization-candidate.json` is a
schema-valid authorization **candidate** covering all seven scopes, with a
470 GiB byte ceiling matching the CL-009 cold-pull projection for the larger
tier, a provider-local mirror root, and null ledger/human fields.

**It is a shape demonstration, not a queued request.** It is hash-bound to
`fixtures/cloud/input-lock-fixture.json`, whose pins are synthetic placeholders
(`org/model`, `org/tokenizer`, `registry.example/base`). Signing it would
authorize retrieval of nothing real. A genuine Step 5B request requires a real
input lock first — which does not exist, because Step 5A produced fixtures only.
The candidate demonstrates the exact document shape a human would sign; it is
not that document. Tests assert both that it grants nothing and that its lock is
the synthetic fixture.

## 2. The G-ROSTER determination

The registered gate is, for every split `s`:

    eligible_s >= confirmation_quota_s + 2 * pilot_s + fixed_reserve_s

`src/pneuma_lab/cloud/qualification.py` evaluates it.

### Two pools, not one

The load-bearing distinction — and the one an earlier draft of this record got
wrong — is that the DL-128 proxy pool and the eligible pool are filtered on
different predicates at different times:

- The proxy is **"the current nonarchived/permissive proxy"**: present-day
  repository metadata.
- Eligibility requires **base-commit licence evidence**: the licence state at
  the pinned historical base commit.

These diverge. A repository archived today, or whose current metadata licence is
absent or unrecognised, may still carry a permissive licence at its pinned base
commit and satisfy every registered eligibility criterion. Such a lineage is
outside the proxy and inside the admissible pool. `eligible_s <= proxy_s` is
therefore **not** unconditional; it holds only against a pool enumerated at the
base commits.

The `cloud-qualification-audit` schema makes this explicit with a required
`proxy_basis` of `current_repository_metadata` or `base_commit_admissible`, and
the evaluator enforces the monotonicity invariant only for the latter. Enforcing
it against a metadata proxy would make the single finding capable of overturning
a no-go verdict impossible to record — a conclusion protecting itself.

### The answer: neither tier satisfies the inequality today

Using the DL-128 / CL-009 audit of the pinned SWE-bench-Live MultiLang dataset
revision `608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b` — proxy root lineages of
C 9, C++ 14, C# 26, Go 77, Java 44, JavaScript 35, Rust 28, TypeScript 45 — and
one disjoint pilot pair per split:

| tier | split | required | metadata proxy | status |
| --- | ---: | ---: | ---: | --- |
| C120 | C | 11 | 9 | provisionally short |
| C120 | C++ | 16 | 14 | provisionally short |
| C120 | all others | 18-19 | 26-77 | not blocking |
| C160 | C | 14 | 9 | provisionally short |
| C160 | all others | 14 | 14-77 | not blocking |

**Both tiers are `FEASIBILITY_NO_GO`.** Zero lineages are credited, because no
qualification audit has been run and `proxy_metadata` evidence never counts as
qualification.

The stronger claim — that no audit outcome could ever close the C and C++ gaps —
is **not established**, and this record does not make it. It would follow only
if the metadata proxy were a superset of the base-commit-admissible pool, which
nobody has demonstrated. The evaluator marks these splits
`provisional_unsatisfiable` and reserves `FEASIBILITY_UNSATISFIABLE_BY_AUDIT`
for a record whose `proxy_basis` is `base_commit_admissible`.

Two consequences worth stating plainly:

- **Step 5B and G-ROSTER are genuinely coupled**, exactly as the implementation
  plan said. The base-commit admissibility enumeration that would settle the
  question *is* Step 5B's licence audit. The roster question cannot be closed
  from a desk.
- **The gaps are large enough to be sobering.** C120 needs at least 2 more C and
  2 more C++ base-commit-eligible root lineages than current metadata shows, and
  C160 needs at least 5 more C. Nothing licenses optimism here; it licenses
  running the audit rather than declaring the tier dead or alive.

Modelling notes, both conservative in the direction that *understates* the
requirement: the C160 fixture applies confirmation quota 12 per split without
the Hamilton allocation, and `fixed_reserve` is 0 throughout because no manifest
has fixed reserves. DL-128 says "12 per split plus the Hamilton allocation" and
"plus reserves", so real requirements are at least these. The C160 C++ row
(14 required against a 14 proxy) is marked not-blocking only under that
Hamilton-free reading and is genuinely marginal.

`fixtures/cloud/qualification-audit-c120-proxy.json` and
`qualification-audit-c160-proxy.json` record this evidence with real provenance
digests bound to the design freeze and the evaluating module, and a test asserts
the counts against the DL-128 row rather than against themselves.

### What follows, and what does not

The design offers two remedies: satisfy the inequality through the qualification
audit, or adopt a registered reviewed amendment. **Both remain open.** This
record does not draft an amendment, does not weaken the roster, and does not
declare either tier dead. `require_roster_gate_satisfied` refuses every
promotion path, and now requires resolvable evidence bytes and the bound
input-lock digest before it will credit anything.

### Scope and honesty limits

- This covers the **SWE** roster. The tau2 roster has its own separately frozen
  counts (DL-128: C120 feasible after qualification; C160 requires at least 47
  qualified airline tasks and at most three ordered airline reserves) and is not
  evaluated here. A tau2-only tier is not a registered configuration.
- The per-language lineage counts are **internal CL-009 audit evidence**. A
  read-only public-source check on 2026-07-31 corroborated the dataset-level
  figures (743 tasks, 381 repository strings) and the tau2 domain counts (airline
  50, telecom 114, banking 97 = 88 DB + 9 ACTION-only), but the per-language
  breakdown after the nonarchived/permissive filter is **not published
  anywhere**, and CL-027 records that check without a committed response
  artifact. Independent re-derivation from the pinned revision remains a genuine
  pending external verification.
- If a reviewed amendment changed the admissibility filter itself — a later
  dataset revision, or accepting archived or non-permissive repositories — the
  pool changes and the arithmetic must be redone. That is an amendment, not an
  audit, and nothing here licenses it.

## 3. State

Step 5B remains **unexecuted**: `implementation_complete`,
`external_verification_pending`. `authority_freeze_pending`,
`launch_review_pending`, and `execution_pending` remain. G-ROSTER remains
**open and blocking**, awaiting either the base-commit qualification audit or a
reviewed amendment. No experiment manifest is promoted, no pilot is authorized,
no provider was contacted, no credit was spent, and no scientific result exists.
