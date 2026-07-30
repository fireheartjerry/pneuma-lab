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
