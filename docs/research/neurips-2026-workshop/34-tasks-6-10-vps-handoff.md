# Tasks 6–10 VPS execution handoff

**Status:** current execution handoff for the remaining zero-spend core

**Prepared:** 2026-07-30

**Branch:** `codex/neurips-2026-empirical`

**Controlling plan:** `docs/superpowers/plans/2026-07-28-resampling-null-core.md`
**Scientific contract:** `docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md`

**Paper-facing name:** the PLACEBO Protocol / the PLACEBO Trial (DL-160).
Internal `resampling_null` identifiers are unchanged.

This document is a routing summary, not a replacement for the controlling plan,
design, decision log, or execution journal. Read those authorities completely
before changing scientific behavior.

Paper-facing artifacts for this lineage live alongside the core:
`paper/placebo_protocol.tex`, `src/pneuma_lab/placebo_paper/`, and
`src/pneuma_lab/adversarial_review/`. Task 10 release preparation must produce
a package that `pneuma_lab.placebo_paper.admit` accepts; the exact field
contract is in `docs/research/placebo-paper/00-result-to-paper-pipeline.md` §1.
Step 4A, Step 4B, the incomplete P0 root, synthetic fixtures, and pilots are
refused by name, so a release that produces numbers the paper cannot use will
fail at admission rather than in review.

## Current boundary

Tasks 1–5 of the benchmark-independent, zero-spend core have been implemented
through the synthetic prefix-index publication boundary. The delivered surface
includes typed records and schemas, canonical artifact ancestry, deterministic
assignment and schedule authority, token-exact REAL/SHAM packet machinery,
subprocess-backed synthetic prefix execution, independent semantic replay, and
transactional prefix-index publication.

The delivery remains `synthetic_validation` only. It has produced no external
model call, benchmark outcome, paid inference, causal result, or promoted
scientific claim.

Task 8B's shard substrate is repaired: family-specific raw count simulations,
full chunk/aggregate replay receipts, manifest-group layouts, and write-closure
guards are committed. Do not treat the old validation record as evidence: fresh
2,000-dataset validation-domain simulation, true 99,999-draw multiplier
comparison/fallback, full-fallback finalization, and adversarial end-to-end
closure tests remain required before any P0 result or feasibility statement.

The fast test surface was deliberately compressed after implementation. The
seven-case cold oracle and compact milestone tests are guardrails, not a
substitute for the Task-10 isolated result-of-record and broader Linux
verification receipts.

## Required source order

1. `AGENTS.md`
2. `docs/project-status.json`
3. `VPS_NEURIPS_2026_HANDOFF.md`
4. this handoff
5. `docs/superpowers/plans/2026-07-28-resampling-null-core.md`
6. `docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md`
7. `docs/research/neurips-2026-workshop/15-decision-log.md`
8. `docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md`
9. `docs/research/neurips-2026-workshop/33-execution-journal.md` and its
   sharded event files

If these sources conflict, stop and reconcile authority in the decision log
before production work. Do not infer current state from commit subjects alone.

## Task 6 — freeze, blinded projection, and gated unblinding

**Implementation checkpoint (2026-07-30):** analysis inputs now snapshot into
the immutable source namespace; the projection candidate is a subprocess-tested
pure module that accepts only stripped opaque outcomes; trusted sealing reloads
schedule/freeze/task-block ancestry and validates the recomputable candidate
digest. Unblind permit framing consumes the nominal unblind handle and derives
only the unblind subkey. Review correction now preserves frozen schedule order,
closes the blinded outcome schema, and verifies copied freeze inputs. Full
Task-6 controller hardening is now complete: sealing and unblinding take a
dedicated run-root controller lock, reject run-wide duplicate singleton records
regardless of output path, verify the complete present scientific graph, and
verify every frozen `CurrentAnalysisInputs` snapshot. Unblinding verifies public
context and raw ledger bytes before ledger decoding, then writes a durable,
one-way outcome-taint marker before assignment rows are exposed. That marker
rejects later freeze, task-block, and blinded-projection work; there is no
production reset API. The focused adversarial gate covers durable taint and
concurrent alternate-destination singleton rejection. Review correction:
`unblind_projection` now requires an exact `CurrentAnalysisInputs` value and
calls the full external-byte/packet-parent `verify_analysis_freeze` comparison
before any ledger read. A ledger-excluding graph pass discovers and rejects any
alternate ledger identity (including an alias/hardlink) before permit
validation; after a valid controlled permit, the durable taint marker is
installed before the complete graph is permitted to parse ledger structure.

Implement the exact Task-6 contract in the controlling plan:

- pre-outcome freeze of estimands, tests, multiplicity, verdict regions,
  failure handling, manifests, and executable digests;
- capability-separated blinded projection that cannot access assignment labels,
  raw arm identities, or efficacy contrasts;
- fresh-context unblinding that validates the exact freeze, manifest, selected
  tier, assignment authority, and `K_unblind` permit;
- immutable analysis-freeze, blinded-projection, and unblind receipts;
- permanent context-taint and protected-path enforcement.

Task 6 must not implement Task 8 power production, choose a tier from outcomes,
read external benchmark outcomes, or perform paid execution.

**Paired-publication repair (2026-07-30):** The production `analyze` route no
longer publishes a singleton unblind receipt before it attempts row conversion
or numerical analysis. Its staged Task-6 API taints before the first
clear-ledger parse, holds clear rows only in memory, constructs and validates
the receipt/analysis pair (including the future receipt digest binding), then
publishes both. A durable no-clear prepared-pair transaction supports recovery
across arbitrary root-relative output directories: an authenticated future
paired-unblind controller finalizes an intact pair or deletes a matching partial pair; malformed/substituted state
blocks fail-closed. Focused failure injection proves no receipt or analysis
after a builder/second-write failure while taint remains permanent. This is not
an unblind E2E receipt: no real completed lineage exists yet.

**Implementation-complete checkpoint (2026-07-30):** Focused hostile review
found and repaired one remaining freeze-integrity defect: verification had
compared an unordered multiset of bytes, so two named analysis inputs could
exchange contents without detection. The freeze schema now binds every source
name to its exact immutable ArtifactRef, and verification checks each named
source plus the config and projection schema independently. The scoped Task-6
gate passes after the repair. Canonical status is
`implementation_complete; E2E_pending`: no authority-backed P0 lineage reaches
real unblind and paired analysis, so Task 6 is not scientifically complete.

**Task 6 Step 5 revalidation against Step 4A (2026-07-31):** The preserved
miniature production-path root
`build/research/neurips-2026-workshop/step4a-iv-20260730-210059` was re-read
without executing either lineage path. `validate_scientific_graph` passed;
`verify_frozen_analysis_inputs` passed against the immutable freeze; and the
sealed analysis-freeze, blinded-projection, unblind-receipt, and registered
analysis records were present with the journaled identities
`b30f59452aa6bfb91f45d4f4aed300181d7696f16a5fb2ba42aabadb84e3f89a`,
`84dab953889ffef52cfad93f40f4c6e48b41ff928c3553b55c2e5f057756acef`,
`c1142f4d4e19a7ccdbc098e8f4f22df1ac4f49af3ef58ba7e7ed291e5d94108a`, and
`b21ef75c1b2b7bbbd90937483d66b7f3363d4a2314dbfcaa8645371fc591b38e`.
The durable Task-6 outcome-taint marker is present. This strengthens
implementation verification only; it does not remove `B-NEURIPS-TASK6-E2E`
or promote Step 4A records to P0/scientific evidence. Step 4B remains pending.

**Task 6 continuity revalidation, deepened (2026-07-31):** The same preserved
root was re-read again via
`timeout 180s .venv/bin/python scripts/research/task6_step4a_continuity.py`
(exit `0`, `PASS`; see EJ-20260731-task6-step4a-revalidation), with a
before/after inventory of all 1,392 run-root files proving nothing was written.
Beyond the earlier structural pass this adds: fail-closed negatives on
`verify_frozen_analysis_inputs` (mutated digest and mutated byte count both
raise); frozen-input namespace and byte identity plus a sealed packet-index
binding; a genuine re-derivation of the blinded projection — the pure
`build_candidate` over the 40 preserved schedule slot IDs and task-block slot
outcomes reproduces the recorded `projection_candidate_sha256`
`597fd15ebcf0d85a…`; a blindness check showing only `A`–`D` slots and no arm
token in the projection bytes; receipt/analysis byte-ref binding with the
paired-publication transaction marker absent; the durable taint gate still
raising for all three protected actions (and passing for an unprotected one)
with both singleton kinds present; and 40-way chain coverage across task blocks,
projection rows, schedule tasks, and `analysis.row_count`. The permit HMAC and
the clear ledger-to-analysis join remain unverifiable without executing the
unblind. This is continuity verification, **not Task 6 closure**: it does not
remove `B-NEURIPS-TASK6-E2E`, promote Step 4A to P0/scientific evidence, or
complete Task 6, and Step 4B remains pending.

## Task 7 — registered inference and verdicts

Implement the frozen statistical API and hand-calculation fixtures:

- sharp randomization tests for the registered REAL–SHAM and
  REAL–retry contrasts;
- paired NONE/RESAMPLE discordance and retry-instability summaries;
- average-effect bounds and finite-sample resolution reporting;
- intersection-union, multiplicity, equivalence, utility, differential-failure,
  and cap-binding gates exactly as specified;
- total handling of positive, null, negative, invalid, and infeasible outcomes;
- manifest-owned inference randomness with no caller-selected scientific seed.

Task 7 consumes finalized authority. It must not tune endpoints, select a
benchmark roster, alter the subject, or use observed efficacy to change a
decision region.

### Task 7A handoff — statistical primitives (2026-07-30)

The initial Task 7 slice adds frozen `AnalysisRow`, randomization, simultaneous
bound, and resolution value records plus pure `analysis.py` primitives. It
implements equal-benchmark task contrasts; exact enumerated/dynamic-program
REAL/SHAM and REAL-versus-no-feedback Fisher tails; a 12-way sharp-global
omnibus max-T tail; domain-separated Philox add-one Monte Carlo fallback;
frozen-order task-cluster Rademacher bounds; and exact equal/unequal-roster
`q0`/`r95`. Hand fixtures cover the arithmetic and modes.

Task 7B must wire these primitives only after the Task-6 artifact/manifest
authority is reloaded and verified. It owns roster ancestry, binary sufficient
statistics/batch kernels, multiplicity/gates, `analyze`, and every verdict.
The primitive `seed` parameters are deliberately test/kernel inputs; Task 7B
must derive them from the manifest-owned inference RNG contract and expose no
caller-selected scientific seed.

### Task 7A correction — review finding closure (2026-07-30)

The original omnibus used a row-sample standard error, which is not the
registered statistic and can become non-finite on a single informative task.
It now uses equal-benchmark weighted `T_k` with the exact conditional 12-way
allocation variance of each unordered task outcome. The registered roster is
now explicitly closed to exactly `SWE` and `TAU`; no one- or three-benchmark
generalization is silently accepted. Multiplier inputs are sorted by unique
`task_id` before Philox draws, making input permutations byte-identical.

### Task 7A correction — canonical multiplier identity (2026-07-30)

Multiplier canonicalization is the exact UTF-8 byte ordering of
`(benchmark, task_id)`, and uniqueness is required only for that pair. The
same task identifier may therefore occur once in SWE and once in TAU without
altering the Philox stream; an interleaved cross-benchmark fixture proves
input-order invariance.

### Task 7 implementation-complete checkpoint (2026-07-30)

Task 7 is `implementation_complete; E2E_pending`. The production wrapper now
reloads the completed power selection and exact study-manifest/roster bytes,
rejects missing or changed selected rows, and derives its sole scientific
Philox root as the first unsigned-big-endian 64 bits of
`SHA256(FRAME("inference-philox-v1", [TEXT(study_id),
BYTES(hex_decode(manifest_sha256))]))`. The frozen analysis config contains no
seed and rejects every non-registered decision constant.

The scalar and batch kernels apply sensitivity groups only where registered:
SWE language, and TAU domain plus issue family. Leave-one estimates are
equal-benchmark estimates after renormalizing the affected benchmark; an empty
deletion is explicit invalid uncertainty, never an exception or silently
dropped group. Non-finite standard errors/bounds serialize as schema-registered
JSON nulls under analysis schema `0.2.0`, while unexpected non-finite estimates
still fail closed. Positive verdicts may honestly carry an empty failure-reason
list. Focused hostile fixtures cover asymmetric benchmark effects,
differential branch failure, no-feedback label imbalance, caller-selected RNG,
and invalid uncertainty.

**Task 7 revalidation against Step 4A (2026-07-31):** The preserved miniature
production-path root
`build/research/neurips-2026-workshop/step4a-iv-20260730-210059` was re-read
without executing either lineage path, via
`timeout 120s .venv/bin/python scripts/research/task7_step4a_continuity.py`
(exit `0`, `PASS`; see EJ-20260731-task7-step4a-revalidation). The preserved
power final is still schedulable under `require_schedulable_power_final`; the
frozen analysis config still parses into the exact registered constants with no
seed; the current `manifest_inference_seed` derivation reproduces the seed
`14489719310441074641` actually recorded in the preserved primary and secondary
bounds; roster ancestry covers all 40 selected tasks; the unmodified `analyze`
core reproduces the record's 12 gate codes in order and its 16-key result
payload shape; `reasons` is exactly the unmet gates in gate order; every gate's
`passed` recomputes; and live `classify_verdict` returns the preserved
`UNRESOLVED_RESAMPLING` for all 19,683 reconstructions of the JSON-null
non-finite uncertainty fields. Nothing re-derives the Step 4A numbers — the
clear rows exist only transiently during unblind — and the Step 4A draws are the
implementation-verification-capped 999. This strengthens implementation
verification only; it does not remove `B-NEURIPS-TASK7-E2E`, promote Step 4A
records to P0/scientific evidence, or complete Task 7. Step 4B remains pending.

The design registers no mean-equivalence decision gate: `q0/r95` is the
NONE/RESAMPLE instability/resolution procedure. Utility and cap-binding remain
mandatory reported secondary outcomes, not causal-verdict gates. No completed
authority-backed P0 lineage reaches unblind and analysis, so this checkpoint is
software implementation evidence only, not an empirical result or scientific
completion.

## Task 8 — frozen-grid P0 power and type-I authority

**Task 8B checkpoint (2026-07-30):** The frozen P0 grid/RNG contract and the
synthetic closed power-authority blob are implemented. Roster-bound authority
is intentionally unavailable: the repository has no reviewed verified external
ceremony adapter, so arbitrary local beacon/timestamp JSON cannot mint
confirmation authority. Synthetic staged screen, shard, selection, validation,
and terminal finalization are now covered by a full local regression. The
finalizer discovers the entire append-only authority ledger rather than trusting
a selected report list; its terminal synthetic output is always null-tier
`CONDITIONAL_ONLY`. The registered 20,000-trial Clopper--Pearson path uses a
stable incomplete-beta tail calculation. This remains local synthetic machinery,
not a P0 result, confirmation claim, provider call, or spend authorization.

Implement the deterministic full-grid producer:

- canonical task-level Bernoulli-pattern probabilities and the complete
  registered null/alternative grid;
- `power-outcome-philox-v2` and `inference-philox-v1` domains with the exact
  manifest bindings;
- C120/C160 support, deterministic highest-supported-tier selection, and
  complete power-final ancestry;
- joint Clopper–Pearson bounds and the paired Gaussian/fallback audits using
  the same raw production outcomes;
- fixed global namespace discovery with no caller-selected report set;
- append-only attempts, resumability, retry accounting, and timing receipts.

The tiny machinery fixture is non-decisive. Only the full configured grid may
produce P0 authority. P0 may return a clean no-go; passing tests is not the same
as passing power.

**Timing-admission correction (2026-07-30):** The first canonical production
shard disproved the previous screen estimator: it sampled one convenient cell
and credited a shard partition as guaranteed concurrency. Screens now execute
the frozen 200-dataset screen-domain work for all 2,916 cells through the same
Task-7 count gate as production, commit an all-cell replay-receipt digest, and
charge the total 20,000-dataset workload against the 12-hour cap without a
parallelism discount. A screen that exceeds the cap writes no screen record and
permits only a later immutable generation after a genuine implementation or
topology correction; shrinking the scientific grid, inventing benchmark data,
or declaring more shards is not a remedy.

**Timing-verification boundary (2026-07-30):** The all-cell timing replay is
performed once during locked screen sealing, not once per shard. A fsync'd
`O_EXCL` verifier marker binds the screen ArtifactRef, power authority, and
probe bytes; every shard and merge requires it plus exact frozen
layout/projection checks. This is integrity plumbing for the local trusted
run-root/concurrent-writer model, not cryptographic execution attestation:
power authority contains no private signing capability, so an attacker able to
rewrite the entire local root can forge all public bytes. Treat that stronger
threat as a hard boundary requiring new reviewed custody/signing authority.

## Task 9 — CLI and deterministic synthetic P0

Implement the plan's exact command surface:

- create and validate the synthetic study root;
- run/resume the full P0 grid without changing scientific identity;
- materialize selected descendants only from a completed power final;
- expose verification/status commands that fail closed on drift;
- emit canonical, content-addressed artifacts and concise operator output.

The CLI must not expose secret material, arbitrary seed overrides, alternate
artifact roots after commitment, confirmation shortcuts, provider calls, or
cloud provisioning.

**Task 9 CLI checkpoint (2026-07-30):** `python -m
pneuma_lab.resampling_null` now has a root-confined JSON command adapter for
study ceremony, closed P0 authority and power attempts, artifact-root
verification, and status. It is non-executing unless an operator explicitly
invokes a stage; no full P0/selftest was run for this checkpoint. Remaining
orchestration descendants are still governed by their existing Task-4–6 APIs.
The checkpoint correction binds the full-multiplier final to its implemented
fallback finalizer and rejects malformed/noncanonical paths before record IO.

**Task 9 power-ref media repair (2026-07-30):** The CLI's canonical
argv-to-`ArtifactRef` boundary now preserves the closed power-authority media
identity rather than reconstructing it as generic JSON. Grid, screen-topology,
and power-report roles are explicitly audited as JSON; only
`power_authority` receives its registered vendor media type. A new no-mock
fresh-root command test proves `power authority synthetic` feeds the
manifest-bound Gaussian `power screen` command and produces a screen report.
This is a bounded feasibility preflight, not a P0 execution or result. Next
gate remains the absent Task-5 opaque branch executor, followed by a genuinely
admitted full P0 lifecycle; do not treat this screen record as a final or
descendant admission.

**Task 9 selftest staging preflight (2026-07-30):** The CLI now recognizes the
three planned `selftest` forms and rejects ambiguous study-only/artifact-root
deferral. Resume is read-only until it proves one manifest, an exact compatible
complete power chain, and no schedule/later scientific record. The current
checkpoint then returns a redacted “descendants not implemented” gate. A
committed production-owned zero-spend fixture materializer now uses the live
study-seal contract: `--stop-after-study` writes only
`study-manifest.json` plus `sources/` closure/copies—no power, schedule,
assignment, packets, analysis, or receipt. It is intentionally a minimal
fixture materializer rather than the plan's final public static JSON bundle;
the hostile-review repair now binds the exact committed frozen P0 grid and
screen-topology bytes into the manifest, and proves a synthetic authority can
load that configuration without running it. Preflight is before any write for
a pre-existing manifest/receipt, and malformed CLI input emits one redacted
stdout JSON object (with a safe debug classification only on explicit
`--debug`). **Correction:** it now binds/copies the exact committed 40-task
SWE/TAU `p0-roster-synthetic.json`, derives the matching task registry and
offline provider lane closure, and fixes CPython/Unicode identity rather than
leaking host values. Two stage roots have byte-identical manifests. Next:
hostile-review the full fixture closure, then add descendant materialization
only after a real admitted completed final.

**Task 9 selected-descendant CLI checkpoint (2026-07-30):** The CLI now wires
the first three descendant transitions to the existing Task-3/4 APIs:
`schedule seal`, `synthetic prefixes`, and `assignment seal`. Schedule
admission reloads the exact manifest/final pair and requires a completed,
compatible schedulable final before it resolves an external, root-excluded
decimal U64 seed file or allocates an output/lease. Prefix materialization
accepts only study/schedule refs, proves direct study ancestry, and performs
the existing per-task synthetic candidate/replay plus prefix-index sealing.
Assignment accepts only schedule/prefix refs and an external root-excluded,
owner-custodied 32-byte key file, with the existing in-memory commitment check
and local-test lease. Root names are canonical relative POSIX paths and never
overwrite. Focused CLI tests cover parser admission, missing authority/no-write
failure, and a bounded schedule routing fixture; whitespace and status checks
pass. This is plumbing only: no compatible final, prefix execution, ledger,
provider, benchmark, spend, or result-of-record was run. Next gate: hostile
review the command-to-API boundary and add a real completed-final synthetic
fixture before claiming any descendant execution evidence.

**Task 8B handoff (2026-07-30):** Power shards now generate real manifest-bound
`n=20` pattern-count tensors in chunks and route them through the Task-7 batch
gate. Persist only aggregate gate totals plus compact replay/Merkle receipts;
do not restore a binomial-rate shortcut or serialize raw simulated rows.
Production uses the frozen full grid. `max_datasets`/`max_cells` are
synthetic-fixture-only and deliberately produce incomplete shards that merge
consumers reject.

**Task 8B repair handoff (2026-07-30):** Keep the complete joint-group manifest
through every simulated batch: overall-only tensors silently disable Task-7
leave-one-group gates. A full-multiplier screen must first reload the current
same-authority/grid/topology failed Gaussian validation; an arbitrary artifact
ref or a passing Gaussian is not a fallback trigger. Timing admission is
per-cell measured work projected to full production cells/datasets per shard;
if it exceeds the frozen cap, stop rather than shrinking the estimate.

**Task 8B final receipt handoff (2026-07-30):** Persist canonical ordered
joint-cell group labels—not only their sizes—in every replay receipt and bind
them into `group_layout_sha256`. Artifact identity replay must reload those
labels from the authority roster and pass them into the Task-7 batch gate. An
equal-size label swap is a receipt failure; do not accept a shape-only gate
test as evidence that leave-one sensitivity was executed.

## Task 10 — isolated result of record and closure

Complete the zero-spend core:

- run the focused behavioral and static gates specified by the plan;
- build one isolated result-of-record root from the committed fixtures;
- complete the conditional P0 screen and full grid;
- resume from the completed final and build the selected descendants;
- execute deterministic end-to-end verification twice outside the result root;
- update canonical status and seal a plan/implementation receipt;
- run the broadest relevant Linux verification justified by shared-surface
  risk, with every process hard-capped at 60 seconds unless the user explicitly
  approves otherwise;
- record exact environment, commands, hashes, outcomes, deviations, review,
  zero spend, commits, and pushes in the forensic journals.

Task 10 closes only the benchmark-independent synthetic core. It does not
authorize SWE-bench-Live, τ³, Qwen serving, AWS Batch, paid compute, pilot,
confirmation, or a causal claim.

## Definition of done

**Current Task 7 status (2026-07-30): `implementation_complete;
E2E_pending`.** Manifest/power admission, the scalable batch kernel, closed
verdicts, manifest-owned inference randomness, invalid-result serialization,
and focused hostile fixtures are implemented. There is still no real completed
lineage or analysis result; do not promote passing software gates to scientific
completion.

Tasks 6–10 are complete only when:

- every controlling-plan artifact and test exists;
- the complete synthetic authority graph reconstructs from fresh reads;
- P0 produces either a valid selected-tier final or an honest immutable no-go;
- two isolated end-to-end verification runs agree on logical scientific
  outcomes and decisions;
- the result-of-record and plan receipt are content-addressed and sealed;
- independent hostile specification and quality review have no unresolved
  critical or important finding;
- status, decision, spend, and execution records are current;
- the branch is clean, committed, and pushed.

Do not report completion because the fast smoke oracle passes, because code was
written for all five task names, or because a cloud quota becomes available.

## After Task 10

**Phase B Step 7A checkpoint (2026-07-31):** Static cloud image recipes and
manifest validation are implementation complete only. They use invalid fixture
bases intentionally; Step 7B real receipts/builds/SBOMs remain unstarted and
separately authorized. No Task 6–10 state or scientific lineage changed.

**Phase B Step 8 checkpoint (2026-07-31):** Local lease, deterministic-shard,
and reconciliation contracts are implementation complete against fakes only.
They do not prove AWS Batch/DynamoDB/S3 semantics or authorize execution; no
Task 6–10 state or scientific lineage changed.

**Phase B Step 9 checkpoint (2026-07-31):** Local spend/approval/watchdog
contracts are implementation complete against fixtures only. No real balance,
price, provider, authorization, or execution was used; no Task 6–10 state or
scientific lineage changed.

**Phase B Step 10 checkpoint (2026-07-31):** Local evidence/security controls
are implementation complete only. They preserve peer-slot/donor capability
scope and exclude Class-A material; no cloud worker, secret, journal, or Task
6–10 scientific lineage changed.

**Phase B Step 11 checkpoint (2026-07-31):** T1 local emulation gates and a
no-network test guard are implementation complete. T2/T3 cloud semantics remain
pending; no Task 6–10 state or scientific lineage changed.

**Phase B Step 12 checkpoint (2026-07-31):** Local quota-preflight and
ownership-manifest teardown preparation are implementation complete. No
deployment/teardown or Task 6–10 scientific lineage changed.

**Phase B Step 13 checkpoint (2026-07-31):** The pilot protocol is frozen in
code only; G-ROSTER and all authority/external gates still block a pilot. No
Task 6–10 scientific lineage changed.

**Phase B readiness audit (2026-07-31):** Steps 4–13 preparation is
implementation complete where scoped, but 5B/7B, G-ROSTER, Azure, account/cloud
semantics, quota, authority, and launch-review gates remain open. No Task 6–10
scientific lineage changed.

**Phase B authenticated-readiness checkpoint (2026-07-31):** Step 5B
authorization is now authenticated rather than binding-digest bound (DL-164):
Ed25519 over the complete canonical body, an enumerated trusted key registry,
validity-window/revocation/expiry checks, and a ledger-row content binding, plus
an independent requirement that the input lock classify as a real candidate
rather than the Step 5A shape demonstration. G-ROSTER arithmetic is corrected
(DL-165): unfixed reserves and the C160 Hamilton allocation fail closed instead
of defaulting to zero, and a registered floor outranks the inequality. tau2 now
has its own qualification path (DL-166) and the gate requires both families.
Both tiers remain `FEASIBILITY_NO_GO` with **provisional** shortfalls; no
verdict improved and no roster, quota, reserve, or floor was weakened. The
committed authorization is still an unsigned candidate bound to a synthetic
lock, no licence-audit record exists, and no external input has been retrieved
from this lineage. No Task 6-10 scientific lineage changed.

**Phase B Step 5B / G-ROSTER checkpoint (2026-07-31):** The Step 5B retrieval
and hash-verification workflow is `implementation_complete` and fail-closed; its
authorization is committed as an unsigned candidate bound to a *synthetic*
fixture lock, so it is a shape demonstration, not a queued request, and no
external input has been retrieved. G-ROSTER: both tiers are
`FEASIBILITY_NO_GO`. The C and C++ shortfalls against the current-metadata proxy
are **provisional**, not a determination that a tier is dead — eligibility is
judged at the pinned base commits, so the metadata proxy is not an upper bound.
Settling it requires the Step 5B base-commit admissibility enumeration or a
reviewed amendment (DL-163, `51-step5b-retrieval-and-qualification.md`). Do not
weaken quotas, reserves, or pilot pairs, and do not substitute a roster or
benchmark, to manufacture feasibility. No Task 6-10 scientific lineage changed.

The next phase is separately gated real-experiment work:

1. SWE-bench-Live and τ³ adapter/roster qualification;
2. pinned Qwen3.6/vLLM serving and Qwen3.5 simulator parity;
3. AWS Batch/ECR/S3/DynamoDB/network/watchdog implementation;
4. a hash-approved, bounded paid Tier-1 spike;
5. pilot, blinded discovery/confirmation execution, analysis, and submission.

AWS currently has verified $10,000 EC2-eligible YC credit plus a separate $100
Free Tier credit. The live AWS topology requires only 8 G/VT vCPUs for one
`g6e.2xlarge`; historical quota support requests may remain at a different
number, but neither a request nor a credit is account evidence. Applied quota
is unverified in the current environment and does not bypass any scientific or
per-action spending gate.

## VPS start commands

```bash
git fetch origin
git switch codex/neurips-2026-empirical
git pull --ff-only origin codex/neurips-2026-empirical
git status --short
git log --oneline -12
.venv/bin/python -m pneuma_lab.status --check
python -m pytest -q
git diff --check
```

On Windows, use `.venv\Scripts\python.exe` where applicable. Do not install
missing optional dependencies merely to manufacture a broad-suite pass; record
the environment blocker and run the narrow authoritative gate for the slice.

## Task 9 packet CLI checkpoint (2026-07-30)

`packets build` and `packets audit` now expose the existing Task-5
construction/audit APIs without adding packet, donor, arm, key, provider, or
external-source knobs. Both command paths prove their supplied root refs descend
through the same study manifest; build additionally closes
assignment/prefix/schedule ancestry before deriving manifest-owned packet
authority. Build writes only the Task-5 candidate path; audit derives schedule
task membership and is the only CLI route that can call the sealed-index audit.
Focused packet+CLI tests, compile, and whitespace checks pass. This is unrun
controller plumbing: no candidate/sealed packet index, packet content,
provider/benchmark action, P0 result, spending, or claim exists. Next gate:
hostile-review this command boundary, then produce a genuinely admitted
synthetic final before any descendant execution is attempted.

**Packet prewrite correction:** Build now reserves the candidate destination
before any Task-5 packet-work side effect; an occupied output has a focused
zero-sidecar regression. The requested real no-mock build→audit CLI fixture is
still blocked: the existing provider fixture is intentionally not a valid
local-test storage lineage, and mutating its placeholder roster/storage refs
invalidates its promoted-authority replay. Do not fabricate that closure. Next
fixture slice: promote one dedicated fully valid synthetic lineage, then use it
for a genuine command-level build/audit receipt.

**Task 9 lineage-fixture admission audit (2026-07-30):** The requested
test-only, completed-final lineage fixture cannot be constructed honestly from
the current APIs without executing the real configured P0 workflow. The sole
bounded escape hatch (`simulate_power_shard(..., max_datasets/max_cells)`) marks
the shard incomplete; `_complete_shards` rejects it before selection,
validation, finalization, and schedule admission. `load_power_config` also
hard-rejects every grid value other than the committed 2,916-cell,
20,000-dataset-per-cell / 2,000-validation / 99,999-multiplier contract. A
handwritten completed final would evade replay receipts and violate the
append-only authority ledger, so it is specifically not a test fixture. No
valid full P0 final or descendant lineage exists. Next gate: either execute the
authorized full synthetic P0 under its scientific runtime protocol, or add a
separately governed miniature *non-authority* protocol whose records cannot be
admitted by this P0/schedule chain; do not relabel the latter as P0 evidence.

**Task 9 analysis-boundary CLI checkpoint (2026-07-30):** The CLI now exposes
`analysis freeze`, trusted `project seal`, and `analyze` over existing Task-6/7
authority APIs. Freeze accepts only a named external source root plus strict
relative source names, an external config/schema, and a sealed packet index;
it snapshots the exact external bytes through `freeze_analysis`. Project
reserves its destination before reading task-block outcomes, constructs only
the stripped candidate request in an isolated `-I` subprocess with no
controller-root argument, then has the trusted controller reload and seal it.
Analysis accepts no caller permit/verifier/key override: it obtains two fresh
unblind-purpose handles from the external owner-custodied key file,
issues/consumes the permit internally, then calls registered analysis with the
schedule-derived power final. The analysis config is closed JSON, including its
U64 RNG seed. Focused CLI/freeze/blinding tests, compile, and whitespace checks
pass. **Critical blocker:** the checked-in Task-5 controller has no branch
executor—only the prefix executor—so `synthetic branches` has the exact parser
surface but fails closed with `synthetic branch executor is not installed`; it
does not write, claim, or simulate task blocks. No compatible P0 final, branch,
projection, unblind, analysis, provider action, spend, or result was run. Next
gate: implement and independently review the missing opaque branch authority,
then execute only a genuinely admitted full P0 lineage.

**Task 9 P0 unblind-boundary repair (2026-07-30):** `analyze` no longer opens
or decodes the clear assignment ledger. It binds the supplied opaque ledger
bytes to the public prefix through the already-sealed packet index, while
`issue_unblind_permit` now validates only raw ledger bytes/HMAC context. Clear
ledger parsing is exclusive to `unblind_projection`, after its pre-unblind
graph and permit checks. Regression spies cover both former decode routes.
**P1 paired-publication repair (2026-07-30):** `analyze` now uses the reviewed
Task-6 staged transaction rather than receipt-first publication. After the
mandatory pre-decode taint, it keeps the clear rows in memory while row
conversion/numerical analysis constructs a validated record bound to the
future deterministic receipt reference. A durable no-clear prepared-pair
intent makes the cross-directory two-file commit recoverable. Hostile review
required owner-bound recovery: each public target is exclusively installed by
POSIX hard-linking an owner-only staged inode (never replacement), and its
private link stays until commit/recovery. The intent binds the staged
`(device,inode)` plus digest; recovery deletes only that exact owned file and
fails closed on malformed/substituted/same-byte replacement state. Builder and
second-install fault injection prove neither public target remains on
controlled failure while taint persists; a post-preflight creator is not
overwritten. The intent HMAC is derived from a dedicated nonpersisted
`pair_recovery` master-key subkey, never from the receipt-visible permit; a
fresh bound handle rederives it after crash, while a bare lock cannot delete
pending state. Predeclared keyed staging names make the
pre-identity crash window recoverable; forged intent/hardlink attempts fail
authentication without deleting their victim. The old public receipt-only
`unblind_projection` route is removed. This is plumbing, not an
unblind/analysis E2E: the missing branch authority and unrun full P0 remain the
next gates.

**Task 10 canonical timing gate (2026-07-30):** The canonical synthetic study,
authority, and Gaussian screen were sealed under the exact committed grid and
64-shard topology. A real production shard-0 timing measurement then ran for
about 13 minutes 35 seconds without producing a shard artifact; extrapolating
that measured work across 64 sequential shards exceeds the frozen 12-hour cap.
The process was terminated before publication and no other shard ran. This is
a governed timing-admission no-go, not an incomplete P0 result: do not resume,
weaken the grid, alter the sealed topology, or synthesize a final. Next gate:
repair/revalidate the production timing estimator, screen a new immutable
generation, and only then consider a fresh full P0 run. Zero spend/provider/
benchmark activity and no claim occurred.

**Task 10 fresh all-cell rerun checkpoint (2026-07-30):** The repaired
one-time all-cell timing admission is executing in the separate ignored root
`build/research/neurips-2026-workshop/p0-canonical-timing-rerun`; it has not
published a screen or downstream artifact.  At this checkpoint it has run for
more than two hours across eight CPU threads.  That elapsed lower bound already
cannot satisfy the registered 12-hour total-work projection, but it is **not**
yet a sealed timing decision: only the command's eventual fail-closed outcome
may be recorded as such.  The screen lock prevents concurrent rewrite; no
shard, validation, final, schedule, branch, unblind, analysis, provider,
spend, benchmark action, or claim is authorized.  Next gate: let the immutable
probe finish/fail, record the exact receipt or error, then decide whether a
separate reviewed no-go representation is required.  The missing Task-5 opaque
branch executor remains an independent blocker for all Task-9 descendants.

**Task 9 opaque-worker contract checkpoint (2026-07-30):** The first missing
branch primitive, `OpaqueSlotWorkOrder`, is now a frozen public value contract.
It admits only a composite snapshot, an opaque capability identity, public
parent digests/caps, and at most a generic private-guidance ref—never an arm,
donor, clear ledger, or peer slot.  Hostile review caught a concrete side
channel in the existing packet writer: its `private-real`/`private-sham` paths
would reveal an arm to a worker.  The new contract rejects those paths, so the
current packet artifacts cannot yet be passed to a branch worker.  Next gate:
add a sealed opaque packet-capability layer and then the actual isolated
restore/attempt/task-block executor.  This checkpoint does not make
`synthetic branches` available and does not create task blocks or scientific
evidence.

**Task 10 timing rerun termination (2026-07-30):** The user directed the
termination of the active all-cell rerun after its elapsed lower bound made a
passing 12-hour projection mathematically impossible.  The exact screen PID
exited after `SIGTERM`; the ignored root contains only the study manifest,
screen lock, and power authority—no screen/marker/shard/final artifact.  This
is a non-result termination, not a sealed P0 no-go or result.  Future runs must
stop immediately once a registered lower bound makes the requested decision
impossible, record the state, and move to the next gate.  The remaining work is
now implementation-limited, not CPU-process-limited: finish opaque packet
capabilities and branch execution, then revisit a reviewed formal timing
no-go representation.

**Task 9 branch-authority completion (2026-07-30):** The two remaining
descendants named by the previous checkpoint are implemented, so
`synthetic branches` is available and no longer reports
`synthetic branch executor is not installed`.

`packet_capabilities.py` is the sealed opaque packet-capability layer. The
trusted preparer resolves the clear assignment plus packet pair into four
preregistered-order opaque grants; every worker-visible packet name is a pure
function of `(task_id, allocation capability digest)`, so a REAL packet cannot
reach the slot allocated SHAM undetected. `SealedSlotCapability` closes worker
reads to a role allowlist that contains no scientific record kind, and
`SlotArtifactLoader` reads through a descriptor-bound `O_NOFOLLOW` walk with
mandatory digest verification. Read the module docstring before extending it:
the registered property is **peer-slot and donor opacity, not self-arm
opacity**. A packet-bearing worker reads its own packet text, because that text
is the intervention; the REAL/SHAM contrast is protected by the token-parity
machinery instead. Do not restate the stronger claim.

`branch_records.py` and `branch_controller.py` hold the frozen task-block value
contracts and the arm-blind transactions: opaque work-order preparation, the
no-intervention identity path, attempt sealing in preregistered slot order,
byte-identical rerun authorization for a validated pre-endpoint outage, failed
second-attempt finalization, and both task-block sealers. These records
deliberately live outside `types.py` to avoid colliding with the concurrent
Task-7 edits; the controlling plan places them in `types.py`, and that file
placement is an open reconciliation item.

`synthetic_branch_loop.py` is the isolated executor. `run_opaque_slot` restores
the frozen composite snapshot in a freshly spawned environment subprocess and
proves snapshot identity, visible-context digest, and token-id projection
before the subject may act; it drains the frozen pending prefix calls against
the branch tool quota, records the post-pending pre-injection digests, and only
then exposes the optional packet on the first post-trigger model call. It never
grades. Its registered deviations — a closed `branch_final_snapshot_v1` record
under the `composite_snapshot` role, a `branch-request-v1` grammar with a
packet field, a bound model-call cap reported as `TOKEN_CAP`, and a genuinely
measured `wall_clock_ms` — are documented in the module docstring and must not
be silently changed.

**Task 9 branch-program authority completion (2026-07-30):** The study
manifest now requires one sealed `branch_program_registry_ref`. Its closed
registry binds every frozen task to four post-trigger programs by pre-schedule
ordinal `0..3`; manifest sealing copies and verifies the complete nested
program closure before publishing the first scientific record. It deliberately
does not name future `slot_id` or allocation capabilities, which exist only
after the schedule seed is opened and assignment is sealed. At branch
admission, registry ordinals reconcile to the exact later
schedule/assignment-derived opaque work-order order.

`synthetic branches` resolves programs only through manifest ancestry, checks
task and frozen-trigger binding, admits the complete selected task roster
before the first worker starts, and passes each resolved program to the
isolated executor. Missing, extra, reordered, dangling, wrong-role,
wrong-media, wrong-task, wrong-trigger, or caller-substituted authority fails
closed. No CLI program-ref argument or runtime program synthesis exists.

Canonical status for Task 9 is `implementation_complete; E2E_pending`. No
compatible P0 final, real lineage, task block of record, unblind, analysis,
provider or benchmark action, spend, or scientific claim exists. The next gate
is to execute one genuinely admitted full P0 lineage through this authority;
passing the authority tests is not that execution.

## Task 8 reconciliation (2026-07-30)

Task 8's canonical state is `implementation_complete; E2E_pending`, recorded in
`docs/project-status.json` as `neurips_resampling_null_task8` with
`B-NEURIPS-TASK8-E2E`. The temporary branch handoff
`35-task8-timing-no-go-temporary-handoff.md` is now reconciled into these
shared surfaces; read it for the timing-contract implementation detail.

**Provenance, not ownership.** The 2026-07-30 all-cell probe remains a
**Task-10** canonical-execution event that exercised **Task-8**
timing-admission machinery. Task 8 owns the machinery. It does not own that
execution, and the terminated probe is not Task-8 scientific completion.

**No timing no-go record exists, by design.** `timing_no_go.py` and
`schemas/resampling-timing-no-go.schema.json` can represent a measured
`timing_infeasible_lower_bound`, but the terminated rerun emitted no
machine-verifiable monotonic-clock termination evidence binding start and
observation readings, host identity, physical run-root identity, and explicit
termination authorization. Journal prose is forensic context, not that
authority. Creating a record from reconstructed readings would synthesize
missing evidence and is forbidden.

**The blocker was implementation-limited and has been repaired.** The
all-cell screen probe measured about 2,740 seconds of total registered work on
this host against the frozen 432-second admissible threshold implied by the
100x screen-to-production multiplier and the 43,200-second cap. Commit
`87a013b` is the genuine implementation correction the timing-admission
contract contemplates: memoized frozen quadrature and pattern tables, an
integer-numerator randomization support, a lattice-bounded regrouped
convolution cached on its sufficient statistic, a reseeded per-thread Philox,
and cached text/digest admission. The scientific identity is unchanged —
20 grid-spread cells across all three draw domains reproduce byte-identical
`_gate_totals_for_cell` receipts against the pre-change worktree, and
`tests/resampling_null/test_kernel_equivalence.py` re-derives the tails,
resolution, and Philox stream from the original formulations. Measured
all-cell work is now about 275 seconds on the same contended host.

The frozen grid, the 100x multiplier, the 12-hour cap, the shard topology, and
`_projected_screen_wall_seconds` — which still charges total work with no
parallelism discount — are untouched. Nothing about the scientific protocol was
weakened to obtain admission.

**What is still not done.** Task 8 has no admitted screen, shard, validation,
or power final of record, and therefore no P0 result. Passing the kernel
equivalence gate is software evidence. The next gate is one genuinely admitted
full P0 lineage under the unchanged frozen protocol.

### Cross-platform receipt portability checkpoint — 2026-07-31

`pneuma_lab.cloud.portability` now seals one canonical UTF-8/LF JSON bundle
over a fixed timestamp, canonical relative POSIX receipt paths, exact receipt
byte sizes and SHA-256 identities, the validated input-lock digest, and one
complete tier's ordered SWE/tau2 G-ROSTER audit-set digest. The verifier rejects
noncanonical JSON, duplicate keys, non-finite values, path escape, symlinks,
and any byte, size, lock, or roster drift. It reads only the sealed bundle and
local copied payloads: Windows and Linux never independently refetch upstream
data for this comparison. `python -m pneuma_lab.cloud.portability_cli` emits the
three comparison digests as canonical JSON on either platform.

Focused Windows tests pass, including order invariance and deliberate CRLF
payload drift. The implementation-verification E2E completed on 2026-08-01:
Windows sealed the C160 proxy lineage plus the immutable C160 selection receipt,
AWS CloudShell Linux independently matched the archive, bundle, input-lock, and
G-ROSTER digests, and
`evidence/portability-e2e-20260801.json` records the comparison. This closes
cross-platform portability E2E for that exact proxy bundle only. It does not
promote the synthetic input lock, turn proxy rosters into qualified G-ROSTER,
or qualify Docker, isolation, CUDA, throughput, interruption, or worker
durability; those Linux-only and scientific gates remain pending.

**Preparation-authority correction (2026-08-01):** the two-layer signed
preparation envelope plus exact-action admission named by documents 48 and 51
is now an executable schema/verification contract rather than prose. It checks
both signatures and ledger rows plus exact provider, region, action, input,
manifest, cost, spend-history, retry, teardown, and expiry bindings. No live
envelope or action admission was minted, so this correction authorizes no AWS
operation and changes no scientific status.

## Execution-class policy (2026-07-30)

Canonical full-grid P0 work — an all-cell screen probe over the frozen 2,916
cells, and any production shard at the frozen 20,000 datasets per cell — is an
**explicitly authorized experiment-only workload**. It is scientific execution,
not verification.

- It must never appear in a bounded software or integration gate. The autouse
  guard in `tests/resampling_null/conftest.py` fails any test that starts a
  probe over 8 cells or a cell over 1,024 datasets.
- It must never block implementation completion. A task may reach
  `implementation_complete` on bounded machinery fixtures and a miniature
  production-path lineage.
- It requires a per-run authorization and its own journal entry.
- During such a run, the registered decisive-lower-bound timing admission is
  enforced: once the 12-hour projection is mathematically impossible, execution
  stops immediately with a formal no-go. A full shard is never completed merely
  to reconfirm an already decisive infeasibility.

### Step 4A versus Step 4B

- **Step 4A — miniature production-path lineage.** A fresh run root driven by
  tiny, structurally equivalent fixtures through the same real authority,
  scheduling, opaque-branch, task-block, analysis-freeze, blinded-projection,
  gated-unblind, and registered-analysis machinery. Its outcome is
  **implementation verification only**. It is not scientific evidence, not a P0
  result, and its records are deliberately inadmissible to the P0 authority
  chain.
- **Step 4B — canonical authority-backed lineage.** Pending the actual
  experimental phase.

### Step 4A execution checkpoint — 2026-07-30

The bounded implementation-verification run was attempted from the fresh root
`build/research/neurips-2026-workshop/step4a-iv-20260730-194008` using only the
`implementation_verification` authority and miniature grid. Authority sealing,
power finalization, and schedule sealing completed. The real prefix route then
failed closed during fresh candidate-graph replay on an upstream
`power_contract` reference outside the copied prefix authority namespace.
No prefix index, assignment, packet, task block, analysis freeze, projection,
unblind, registered analysis, provider/model call, cloud resource, spend, or
P0-admissible record was produced. Step 4A therefore **did not reach registered
analysis**; it remains `E2E_pending` with implementation continuity repair still
required. This is an implementation-verification failure, not scientific
evidence and not a P0 result.

Follow-up bounded runs repaired the execution-only namespace, verifier-feature,
Linux projection, analysis-freeze, and degenerate-miniature analysis seams. The
fresh root `build/research/neurips-2026-workshop/step4a-iv-20260730-210059`
completed authority, power final, schedule, prefix index, assignment, packets,
analysis freeze, isolated branches, blinded projection, gated unblind, and
registered analysis. Step 4A reached registered analysis as
**implementation verification only**. Its records remain inadmissible as
scientific evidence or P0 results; broad hostile review remains deferred to the
pre-experiment launch review.

### Canonical run stopped 2026-07-30

`build/research/neurips-2026-workshop/p0-lineage-20260730` holds an admitted
screen and 10 of 64 production shards. It is preserved exactly as-is as an
incomplete non-result caused by an explicit scope correction — not a no-go and
not a result. Do not delete, rewrite, finalize, analyze, or claim from it. See
EJ-20260730-0229.

### Task 10 release-preparation checkpoint — 2026-07-31

The controller now has a bounded, independent release-inspection path for an
already sealed artifact root. It first executes the primary graph/receipt
verification, then separately rehashes every receipt-declared byte and the
ordered closure digest. The resulting external package manifest classifies
`implementation_verification`, synthetic fixture failure, registered canonical
no-go, and canonical-lineage-candidate states without letting any of them
silently become a scientific result. An implementation-verification fixture
therefore emits the explicit boundary `not_a_scientific_result`; a future
canonical GO or no-go remains bound to Step 4B release authorization.

Focused Task-10 release tests and the compact 93-case milestone suite pass on
the current Linux checkout. The latter also repaired a stale test-only promoted
tokenizer fixture to its now-closed `synthetic_report_tokenizer_v1` contract.
No canonical P0 screen/shard, provider, benchmark, cloud, paid-compute, or
Step 4B action ran. **Task 10 is now `implementation_complete; E2E_pending`:**
the staged `selftest --resume-after-power` runner requires and preflights all
external secrets and frozen analysis inputs before its first write, then invokes
the complete bounded-fixture descendant sequence. It may defer the final root
seal for independent verification. The release inspector can consume a future
sealed canonical lineage, but neither surface creates or promotes one. A
temporary miniature fallback validation hit the 60-second process ceiling and
published no final artifact; that is an honest bounded-fixture non-result, not
a Step 4B execution or a scientific conclusion.

### AWS topology reconciliation checkpoint — 2026-07-31

DL-161 now binds the AWS primary path to exactly one `g6e.2xlarge`: 8 vCPUs,
one L40S, and 44 GiB usable device memory. The retired four-L40S, 48-vCPU,
TP2/H100, multi-replica, and simulator-co-location descriptions are historical
only and cannot reopen through a Task 6–10 implementation path. Terraform L1
format and validation now cover the whole-node one-GPU job definition, but that
is static implementation evidence only. Step 5B input retrieval, G-ROSTER,
Step 7B double-build/SBOM evidence, account-bound plan and quota verification,
one-GPU admission measurements, Step 14, and any paid or scientific execution
remain independently blocked. Azure remains a separately governed path.

### Step 5B inventory-bootstrap checkpoint — 2026-08-01

The eight exact frozen upstream identities now have a schema-validated,
metadata-only discovery plan with digest
`c817eff762d1ebdeef30956bb719a06c67e30c79e8619777a0e78ddc70ae8c4f`.
It forbids payload/model/layer downloads and experiment execution. The local
743-task/724-pair audit and 176-image OCI metadata are raw evidence, not admitted
G-ROSTER. The exact envelope and one-action admission were signed with registered
key `pneuma-b1-20260801-r1`, independently verified, and executed once in
authenticated AWS account `892077329800` / `us-east-1`. Canonical receipt
`evidence/step5b-inventory-metadata-20260801.json` has SHA-256
`ce9274cdb0825f93e52fec7a30b5210253f92289c4ae43bf4b922efa138f9452`
and lists 1,762 immutable metadata entries across all eight roles. Next
dependency: the repaired pre-retrieval contract has now bound those entries as
1,706 unique objects at canonical payload-manifest digest
`1f738eff8667f0b863cdd8259c7bfa071ec3a37b2d9963e999f11e7dda1087e4`.
One gitlink is lineage-only; the other 1,705 objects have an exact authenticated
67,483,211,374-byte ceiling. This manifest authorizes nothing. Separately sign
payload retrieval, verify Git/LFS/OCI identities while streaming, compute final
SHA-256 receipts, then seal the real input lock; Git SHA-1 metadata must not be
laundered into a verified-byte claim.

The bounded payload-action candidate is now
`fixtures/cloud/payload-retrieval-plan-candidate.json`, canonical digest
`18f8edebbcb9e394259b1d7e0afc4d92cc01c05f933f871ead4fcf094330511a`.
It targets the existing encrypted/versioned S3 bucket under a content-addressed
`runs/` prefix, limits retention to 35 days and retries to one, and carries a
USD 5.00 ceiling. That historical candidate remains unsigned and unready. A
successor binds the current AWS pricing receipt from official offer version
`20260728131000`. Hostile review then added the omitted final receipt PUT and
the exact 35-day Step 5B lifecycle rule. AWS applied the immutable Terraform
plan and live readback proved both rules. Lifecycle receipt SHA-256 is
`5525f0016d91d1158c59215c88d5e454409942d08f649b0dc554d00712754c1d`;
the resulting ready-plan digest is
`9334ffebd443dd4aee2a1a566ae5b29479b40a2856afe825a71e0c09ff74606a`.
Worst-case S3 storage/requests recompute to USD 3.78. It is still unsigned and
authorizes nothing, but its explicit state is now `ready_for_signature`. The streaming
executor and offline final-receipt verifier pass
focused hostile regressions and are bound at executor-surface digest
`15c2fa66d872cfb03f86fff60c34f2d4866efe34814c9c3fdc069d50e619259c`;
they remain E2E-unrun.

Authenticated Terraform plan
`b8f0e95a05051ca4ba05eeb7bcf6316d0ad57834c71723435915095aca9fd243`
was applied with exactly 0 add / 1 update / 0 destroy and added only the Step 5B
35/30/7 lifecycle alongside the unchanged general rule. Post-apply state is
`dff0f6b4b76898e1bab0dfb9ccd2ca7e6c44f0f7d3b3949a038ece1b895b57b5`.
The next gate is a separately signed payload action; no payload is authorized yet.
The deterministic signing ceremony is implemented at
`scripts/research/sign_step5b_payload_admission.py`. It refuses stale executor,
pricing, or lifecycle bindings and references pending immutable ledger rows
CL-045/CL-046. Invoking it with the registered private key remains the explicit
authorization boundary.

The committed runtime at `e7b910e` also reproduces as a 4,933,610-byte Git
archive with SHA-256 `03e1ff2d5d2236867a3cab4eceb54492fc85028d0075368256cef51afdfe7550`.
Native Windows and WSL2 Linux independently produced the same digest; all 1,166
entries are relative POSIX paths. AWS-side digest verification remains required
before signing or execution.

Payload action 001 was subsequently signed and run in AWS. Its first attempt
stopped before payload transfer on the legacy global S3 endpoint. Its sole retry
used the regional endpoint, installed and reread 31 objects / 22,384,787 bytes,
then stopped on Docker's observed `production.cloudfront.docker.com` redirect,
which was not in the signed allowlist. Successor action 002 adds only that host,
binds executor surface `fbaf47939878dd9144e9163d6c0d95142f90a75e6b7ada983f3489ec61b80ade`,
and has ready-plan digest `53dc77c9942cad311e13d92ab3de26a337ac9df97ebdf7487b8537afa022e088`.
It remains subject to a fresh CL-047/CL-048 signature before continuation.

Action 002 was signed and its first attempt advanced the verified mirror to 83
objects / 3,443,039,872 bytes before stopping on a public Hugging Face dataset
URL incorrectly constructed without `/datasets/`. Action 003 corrects only that
consumer-specific namespace, binds executor
`b4377bf94ec7b362455fec3faa1c1649ae3be18496cf5b2e1d132b40ce4a9617`,
and has ready-plan digest
`eca7d02e1010958724f9d7cb9c333ff78998f87bc8809f8cb0919067d5da2215`.

### Step 5B payload-completion checkpoint — 2026-08-01

Signed successor action 004 completed the authenticated payload mirror: exactly
1,705 objects and 67,483,211,374 bytes were installed and independently reread.
AWS and Windows match the final receipt bytes at SHA-256
`69d3e0db08788639de72d020af1ac061a2aa5f6a8742a288eb7d592ee8e7a89c`;
the offline verifier accepts its complete ordered roster and exact plan,
manifest, pricing, lifecycle, identity, byte, and request bindings. This closes
payload retrieval only. Next: construct and dual-platform verify the real
candidate input lock, admit SWE/tau2 G-ROSTER, then run Linux-only worker gates.

The real candidate input lock is now sealed at
`e6746ad843b0da9a6144fa84a5a231dd350b6845a321ffaff171df4540f67b84`.
Native Windows and AWS Linux independently classify it as `real_candidate` and
verify all nine referenced receipts. The next blocking dependency is admitted
SWE/tau2 G-ROSTER evidence; no experiment is authorized by the lock alone.

### Real-model fit qualification checkpoint — 2026-08-01

Signed action `step5b-model-fit-005` reconstructed and independently verified
all 72 immutable model objects / 56,822,409,329 bytes. On one L40S, the 35B FP8
subject passed 128-token generation at both 32,768 and 65,536 context (8.0345
and 8.0569 output tokens/second), while the 9B simulator passed at 32,768 and
generated 109 tokens before EOS (14.7979 output tokens/second). Exact receipt
SHA-256 is `0725e12255c790daf2260f3c6998260e5ebfbedbd99cafced998f973cd6bbfcd`.
Instance `i-0c0449cd0776839dc` and encrypted delete-on-termination volume
`vol-015492544df656a45` are absent after teardown.

This closes real-model fit, not scientific execution. The single prompt per
rung is bounded throughput evidence only. G-ROSTER still needs three Linux
isolation pairs per split and final SWE/tau2 audits; interruption/recovery,
portable offline receipt closure, and the hostile pre-experiment launch review
also remain blocking.

### C120 G-ROSTER candidate checkpoint — 2026-08-01

Authority amendment 52 selects C120 and fixes the reserve at one unit per split
before any pilot or experimental outcome. The committed candidate evidence binds
144 distinct SWE repository lineages with admissible base-commit licences and
immutable OCI manifest digests. The separately derived tau2 evidence binds the
sealed 50-task airline pool, exact 114-task telecom `base` split, and 88 DB-basis
banking tasks, then selects the registered minimum 20/16/13 tasks by a fixed
lexicographic rule. Focused derivation tests pass. This is candidate ancestry,
not admitted G-ROSTER: three independent Linux isolation pairs per split and the
final qualification-audit receipts remain blocking. The completed Step 5B
retrieval plan does not authorize GPU provisioning or scientific execution.

### C120 G-ROSTER qualification complete — 2026-08-01

The signed isolation action executed 33/33 passing Linux pairs: three distinct
immutable units for every eight SWE and three tau2 splits. The exact receipt is
25,856 bytes at SHA-256
`599527e896e9f48a53252585d02e98fd725074e8faa503ab7ce017cf1997b284`;
the deterministic final SWE and tau2 audits both evaluate
`CONDITIONALLY_FEASIBLE`, with closure SHA-256
`a887370640d2c6e9514e350c476e786d1040e6bcf3799422dee6c60b70944209`.
G-ROSTER is therefore satisfied for C120 only. Registered p10 throughput,
interruption/recovery, portable offline receipt closure, and the hostile
pre-experiment launch review remain blocking. No pilot or experiment is
authorized.

### Step 7B reproducible build qualification complete — 2026-08-02

The fourth corrected AWS builder action (`step7b-aws-builder-009`) completed
under its zero-retry KMS admission after the earlier package, build-context,
entrypoint, and Syft-storage failures were exhausted. The action built
controller, model-server, and benchmark-worker twice each from the exact
source archive and pinned base digest; every role's two image IDs matched.
All three positive exact-harness probes passed, all three wrong-hash probes
failed closed, and three nonempty SPDX SBOMs were published to versioned S3.
The raw objects and schema/plan/hash verification are sealed in
`evidence/step7b-aws-builder-success-009-20260802.json`.

The instance, encrypted root volume, and temporary security group were
independently removed. This closes Step 7B image-build/SBOM evidence only. The
real three-role production execution surface, interruption/recovery drill,
and Step 14 hostile review remain open; no benchmark, pilot, experiment, or
scientific claim is authorized.
