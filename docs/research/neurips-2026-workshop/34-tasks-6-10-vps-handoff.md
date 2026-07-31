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
