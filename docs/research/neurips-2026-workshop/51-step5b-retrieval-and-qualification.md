# 51 — Step 5B Retrieval Workflow and the G-ROSTER Determination

**Status:** `implementation_complete`; `external_verification_pending`;
`authorization_pending`. Local public-source audit bytes exist, but no complete
model/tokenizer/benchmark/verifier snapshot has been retrieved or admitted.
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

An `authorized` record names an active, pre-enumerated Ed25519 public key and
carries a signature over the complete canonical body, including scope, byte
ceiling, input-lock digest, spend-ledger row digest, approval metadata, and
expiry. It cannot survive an edit to any of those fields or be lifted to a
different record. The gate also verifies that the exact referenced ledger row
still exists and matches its approved digest. A candidate has neither a ledger
binding nor a signature.

**Preparation envelope and concrete action.** CL-028 is a signed AWS-only
rolling preparation envelope, not a transferable approval to run arbitrary
jobs. Before any retrieval, audit, build, storage operation, smoke, or bounded
API pilot, `cloud_preparation_admission` must separately be signed and bind the
exact envelope digest, input-lock digest, scopes, provider, projected cost,
retry count, complete spend-history digest, teardown protection, expiry, and
its own exact ledger row. The admission gate verifies both signatures and both
ledger bindings before a provider operation. Training, canonical experiments,
replication, unblinding, result promotion, and publication claims are outside
the envelope and cannot be represented as an admissible action.

**Executable correction (2026-08-01).** The earlier text named that two-layer
gate before its schema or verifier existed. DL-170 closes the gap with
`cloud-preparation-envelope`, `cloud-preparation-admission`, and
`pneuma_lab.cloud.preparation_admission`. The live gate additionally checks the
exact action id/class, provider/region, input/manifest identities, retries,
teardown protection, and prior-plus-projected cumulative envelope spend. No
authorized record is committed by this correction.

**Boundary of the ceremony:** an Ed25519 key establishes possession of that
private key, not a person's intent, comprehension, or hardware identity. The
registry now contains the project-scoped CloudShell public key
`pneuma-b1-20260731`; its private half remains only in CloudShell. An unknown,
revoked, out-of-window, or expired key authorizes nothing. Key compromise,
single-signer trust, and registry-update governance remain explicit residual
risks rather than being papered over by a stronger adjective.

`require_authorized` additionally recomputes the input-lock digest and refuses
any authorization not bound to that exact lock. It resolves the named ledger
row from the append-only ledger and compares the row's exact bytes with the
signed `ledger_row_sha256`; a missing, duplicate, or edited row fails closed.

**Plans.** `build_audit_plan` derives ordered retrieval steps for **every
inventory-listed file** in the model, tokenizer, benchmark, and
**verifier-source** snapshots, plus the dataset manifest and container base.
Each revision pin carries an immutable inventory manifest and that manifest
must also be an artifact in the hashed inventory; a single README or metadata
receipt can therefore never stand in for an unconstrained snapshot. Revisions
are 40-hex identities and container bases use `linux/amd64@sha256:` digests; no
tag is resolved and no registry is consulted. Mirror paths are scoped by kind,
repository, and reference, and uniqueness is enforced on the destination path,
so two artifacts can never be written to one location and clobber it. The plan
is buildable from a *candidate*, which is what makes an unexecuted plan
reviewable in advance. `build_receipt_verification_plan` covers the licence and
contamination receipts — audit outputs verified as mirrored files rather than
fetched — and binds the input-lock digest like the retrieval plan does.

An upstream artifact may legitimately appear in more than one role when the
subject and tokenizer share a pinned repository. That is not a collision: the
role/repository/revision mirror namespace separates the destinations. Duplicate
entries within one snapshot inventory remain forbidden.

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

**Corrected modelling (DL-165).** An earlier draft of this document recorded
`fixed_reserve` as 0 "because no manifest has fixed reserves" and applied the
C160 quota without the Hamilton allocation, calling both conservative. They were
not: reading an *unfixed* term as *zero* is the one substitution that can only
ever make the gate easier, and it silently understated the requirement. Both
terms now fail closed. A `required_lower_bound` that treats unfixed non-negative
terms as 0 is still reported, since a shortfall against it holds a fortiori, but
a split with any unfixed term can never reach a feasible verdict — only a
sharper no-go. The C160 C++ row was previously marked not-blocking only under
the Hamilton-free reading; that reading is withdrawn.

Where the design states a requirement outright rather than through the
inequality, the stated floor governs. `registered_minimum_units` carries such a
floor, and the requirement is the greater of the two. DL-128 registers one:
tau2 C160 needs at least 47 qualified airline tasks, against a quota-plus-pilots
reading of 27. Modelling only the inequality understated that split by twenty
tasks, which independent hostile review caught.

`fixtures/cloud/qualification-audit-c120-proxy.json`,
`qualification-audit-c160-proxy.json`, and the tau2 pair
`qualification-audit-tau2-c120-proxy.json` and
`qualification-audit-tau2-c160-proxy.json` record this evidence with real
provenance digests bound to the design freeze and the evaluating module, and
tests assert the counts against the DL-128 row rather than against themselves.

### Two families, two kinds of evidence (DL-166)

SWE qualification and tau2 qualification are different claims about different
units resting on different evidence, so one record covers exactly one
`benchmark_family`. `swe` qualifies **root lineages** by base-commit licence
evidence against a `base_commit_admissible` pool; `tau2` qualifies **individual
tasks** against the `pinned_objective_pool` DL-128 froze — airline 50, telecom
114, banking 88 DB, with the nine banking ACTION-only tasks excluded. A pool
belongs to a family, and a record borrowing the other family's pool is refused
as a category error rather than accepted as weak evidence.

The promotion gate requires a satisfied audit for **both** registered families
and refuses a single-family submission, so abundant SWE evidence can never
stand in for absent tau2 evidence. The registered tiers remain exactly C120 and
C160; no tau2-only tier exists and none may be introduced through this record.

One modelling assumption, in the direction that *overstates* the requirement:
DL-128 states telecom pilots as one per family, and the same one-pilot shape is
carried across the airline and banking splits, which no authority states
explicitly.

### Authenticated authorization (DL-164)

The DL-162 binding digest is superseded. An `authorized` record now carries an
Ed25519 signature over the complete canonical body — every field of the record,
plus the approval's own approver id, key id, grant time, and expiry, so none of
them can be edited after signing. Verification requires a public key
**enumerated in advance** in `fixtures/cloud/approver-key-registry.json`: an
unenumerated key authorizes nothing however mathematically valid its signature,
which is what moves trust from the signature to the registry. The key must be
unrevoked and inside its validity window; the approval must not have expired;
and the referenced `CL-0xx` spend-ledger row must exist with its exact line
bytes still matching the bound digest, so an approved row cannot be quietly
rewritten afterwards.

Independently of authentication, the input lock must classify as a real
candidate. A perfectly signed approval over a lock full of placeholder
identities is refused, because it would otherwise read as authority to retrieve
nothing in particular.

What this still does not establish, stated plainly: a verifying signature is not
proof of a person. A stolen or coerced key signs perfectly well; there is no
hardware binding, no threshold or multi-party requirement, and no transparency
log, so a single compromised key is a single point of failure. Nothing proves
the approver understood what they signed. Revocation is only as timely as the
committed registry. The registry currently names one real key generated in the
user's CloudShell by a separately authorized session; **this lineage did not
perform that ceremony and cannot attest to private-key custody.**

### Real candidate locks versus the Step 5A demonstration

`src/pneuma_lab/cloud/input_lock.py` classifies a lock as `real_candidate` or
`synthetic_demonstration`, and the classification is **derived, never
asserted** — there is no field to set, because such a field would be exactly as
trustworthy as whoever wrote it. It rejects placeholder and reserved-namespace
repositories, filler digests, mutable tags where an immutable commit or
`linux/amd64@sha256:` digest is required, unnamed licences, and two artifacts
sharing one receipt path. `build_candidate_input_lock` refuses to emit anything
that does not classify as real, so the constructor cannot launder a placeholder
into something authoritative.

The committed `fixtures/cloud/input-lock-fixture.json` classifies as
`synthetic_demonstration`, and a test pins that. What `real_candidate` means is
narrow and worth stating: every required identity is present, immutable, and not
obviously a placeholder. It does **not** mean the identity exists, resolves to
anything, or that a single byte behind it was fetched or verified.

### The base-commit licence audit exists locally but is not yet admitted

`src/pneuma_lab/cloud/licence_audit.py` provides the deterministic derivation
command, an ordered roster carrying each lineage's base commit, explicit
inclusion or exclusion reason, observed licence and licence-evidence digest, the
pinned dataset and task-manifest identities, per-language counts recomputed from
the roster rather than asserted beside it, and a qualification receipt bound to
the deriving code and to every input byte. Order is part of the record: a
reordered roster is a different roster and fails its receipt.

It deliberately cannot manufacture the audit. `derive_audit` requires a
caller-supplied observation per lineage and treats a missing one as a failure
rather than an exclusion, because "we did not look" and "we looked and found
nothing" are different findings and only the second is evidence. The command
fails closed and writes nothing, which is the correct state until Step 5B runs.
**CL-009/DL-128 proxy prose is explicitly refused as qualification**: it was
derived from present-day metadata rather than base commits, and CL-027 records
that no response artifact, URL, or digest was committed, so a reviewer cannot
recompute it. A later local public-source run produced a commit-addressed audit
covering 743 tasks and 724 repository/base pairs: 557 admissible, 122 excluded,
and 45 unresolved. A deterministic 176-lineage C160 selection and complete OCI
manifest/config/layer metadata for those 176 images also exist under ignored
`build/` evidence. Those bytes are useful raw evidence, but they are not yet an
admitted `cloud_licence_audit` or `cloud_qualification_audit`, do not bind a real
input lock, and contain no three-pair isolation evidence. Calling G-ROSTER
closed from them would be enthusiastic bookkeeping, not science.

### Exact inventory bootstrap

The real input lock has a bootstrap dependency: its snapshot receipts need the
complete file inventory, hashes, and authenticated sizes before the lock can be
signed. `cloud_input_inventory_plan` now freezes the only permitted discovery
action for that step. Candidate digest
`c817eff762d1ebdeef30956bb719a06c67e30c79e8619777a0e78ddc70ae8c4f`
enumerates eight exact upstream roles and permits metadata listing only. Model
weights, payload files, container layers, and experiment execution are all
forbidden. The candidate itself grants no provider authority; an exact signed
preparation envelope and admission remain required before execution.

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

Step 5B remains **partially evidenced but unadmitted**: `implementation_complete`,
`external_verification_pending`. No signed preparation envelope or concrete
admission is committed. The metadata-only inventory candidate does not turn the
synthetic lock into an authorized retrieval. `authority_freeze_pending`,
`launch_review_pending`, and `execution_pending` remain. G-ROSTER remains
**open and blocking**, awaiting either the base-commit qualification audit or a
reviewed amendment. No experiment manifest is promoted, no pilot is authorized,
no provider was contacted, no credit was spent, and no scientific result exists.
