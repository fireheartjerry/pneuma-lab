# Tasks 6–10 VPS execution handoff

**Status:** current execution handoff for the remaining zero-spend core

**Prepared:** 2026-07-30

**Branch:** `codex/neurips-2026-empirical`

**Controlling plan:** `docs/superpowers/plans/2026-07-28-resampling-null-core.md`
**Scientific contract:** `docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md`

This document is a routing summary, not a replacement for the controlling plan,
design, decision log, or execution journal. Read those authorities completely
before changing scientific behavior.

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

**Current Task 7B status (2026-07-30): incomplete.** A narrow exact-`r95`
probability-mass repair is committed separately; it does not close the required
manifest/power admission integration, scalable batch-kernel, or hostile-fixture
work. Do not promote it to a scientific result or Task-7 completion.

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

The next phase is separately gated real-experiment work:

1. SWE-bench-Live and τ³ adapter/roster qualification;
2. pinned Qwen3.6/vLLM serving and Qwen3.5 simulator parity;
3. AWS Batch/ECR/S3/DynamoDB/network/watchdog implementation;
4. a hash-approved, bounded paid Tier-1 spike;
5. pilot, blinded discovery/confirmation execution, analysis, and submission.

AWS currently has verified $10,000 EC2-eligible YC credit plus a separate $100
Free Tier credit. On-Demand and Spot G/VT quota requests were opened at 16
vCPUs and immediately amended through Support to the design-required 48 vCPUs.
Applied quotas remain zero until AWS approves the cases. Quota availability
does not bypass any scientific or per-action spending gate.

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
