# Phase B Steps 4–13 — file-by-file implementation plan

**Status:** planning document; no implementation, freeze, or authorization
**Prepared:** 2026-07-31
**Revised:** 2026-07-31 (review corrections 1–18 applied)
**Scope:** Steps 4–13 of
`docs/research/neurips-2026-workshop/36-step4a-to-aws-credit-launch-roadmap.md`

This document is subordinate to the scientific contract, the controlling plan,
`docs/project-status.json`, the live Tasks 6–10 handoff, the decision log, the
cloud spend ledger, and the append-only execution journal. If any of those
conflict with this plan, stop and reconcile them in the decision log before
execution. It is a plan, not an authority: it freezes nothing, authorizes
nothing, and promotes nothing.

**Supersession note (DL-171).** All former one-L40S/8-vCPU, four-L40S/48-vCPU,
TP2, H100-substitution, and co-located-simulator wording below is historical
planning text. The live AWS primary contract is two independent Spot
`g6e.2xlarge` workers (16 vCPUs total), canonical disjoint partitioning, and
per-worker one-GPU admission. Azure remains separately governed. This note
changes no scientific input, roster, endpoint, or authorization.

## Boundary of this document

- It is **not** Step 4. No hypothesis, arm, endpoint, stopping rule, benchmark
  roster, model, or topology is frozen here. Step 4 is described, not performed.
- It is **not** Step 14. The pre-experiment hostile launch review is deferred.
- **On Step 4B.** Phase B is deliberately pre-experiment preparation, so it is
  intended to leave Step 4B better prepared. The correct boundary is narrower
  and stricter: Phase B must not **execute** Step 4B, **authorize** it,
  **fabricate or pre-stage evidence** for it, or **weaken** any of its gates,
  authority checks, or admission criteria.
- It records **no** cloud, paid, provider, benchmark, image-build, model-pull,
  or dataset-pull action. None occurred while preparing or revising it.
- It does **not** touch, resume, finalize, analyze, or cite the preserved
  incomplete root
  `build/research/neurips-2026-workshop/p0-lineage-20260730`.
- It promotes nothing past its honestly recorded state (see §3).

---

## 1. Method and evidence basis

The inventory was produced by direct repository reads plus bounded read-only
subprocess inventories (`codex --yolo exec` for symbol-level enumeration;
`claude --dangerously-skip-permissions -p` for quoted extraction of binding
language and cross-document conflicts). Subprocess output was treated as
untrusted: every value reproduced below was re-verified directly against the
repository. Where a subprocess claim did not survive verification it was
dropped.

Verification commands used for the revision, each well inside the 60-second
ceiling:

```txt
git log --oneline -6
git status --short
grep -oE "DL-[0-9]+" docs/research/neurips-2026-workshop/15-decision-log.md | sort -t- -k2 -n | tail -1
grep -n "EXPECTED_" tests/test_schema_loads.py
sed -n '81,110p' src/pneuma_lab/schemas/__init__.py
sed -n '12,16p' scripts/check_test_budget.py
python -c "import json; ..."   # project-status.json systems/blocker inspection
```

---

## 2. Phase A state — verify, do not assume

### 2.1 Forensic history (not a live rule)

At the time the **first draft** of this document was written, `git status`
showed Phase A work in flight:

```txt
 M docs/research/neurips-2026-workshop/36-step4a-to-aws-credit-launch-roadmap.md
 M src/pneuma_lab/resampling_null/cli.py
 M tests/resampling_null/provider_authority_fixture.py
 M tests/resampling_null/test_cli.py
?? src/pneuma_lab/resampling_null/release.py
?? tests/resampling_null/test_release.py
```

**This snapshot is forensic history and is not a live collision rule.** It is
retained only to explain why the first draft deferred shared-surface edits. Do
not act on it.

### 2.2 Phase A is not known to be complete

Commit `19f499d` ("feat(resampling-null): add task10 release inspection") landed
`src/pneuma_lab/resampling_null/release.py` and
`tests/resampling_null/test_release.py`. **That commit is not equivalent to a
complete Phase A**, and this plan does not treat it as such. Measured evidence
that Phase A remains open:

- `docs/project-status.json` `systems[]` contains
  `neurips_resampling_null_task6`, `task7`, `task8`, and `task9` — **there is no
  `neurips_resampling_null_task10` entry at all.** Task 10 is not registered as
  reaching any status.
- Roadmap Phase A has three items. Item 3 is "Complete Task 10 implementation
  and release preparation", whose exit gate is that Task 10 implementation "is
  complete and capable of consuming a future canonical lineage".
- `src/pneuma_lab/resampling_null/cli.py` and
  `tests/resampling_null/test_cli.py` were still modified after `19f499d`.

**Blocking precondition, to be evaluated at execution time, not assumed now:**

> Before starting any Phase B step, re-verify Phase A completion directly:
> `git status --short` is clean for Phase A paths; `docs/project-status.json`
> carries a `neurips_resampling_null_task10` record with justified
> `implementation_status`; the roadmap's Phase A exit gates 1–3 are each
> journaled; and `python -m pneuma_lab.status --check` passes. If any of these
> fails, Phase A is not complete — record that finding and do not silently
> proceed as though it were.

### 2.3 Live collision rules

These survive regardless of Phase A state, because they are properties of the
architecture rather than of a moment in time:

1. Phase B code lands in a **new package**, `src/pneuma_lab/cloud/`, with **its
   own CLI module**. The single eventual touchpoint on
   `src/pneuma_lab/resampling_null/cli.py` is one `top.add_parser("cloud")`
   line, added when the surrounding step is otherwise complete.
2. `power.py` and `branch_controller.py` are **wrapped, never modified**. Any
   change invalidates the Task 8 and Task 9 receipts and the Step 4A continuity
   results.
3. All new schema files carry the `cloud-` prefix, so no `$id` can collide with
   the `resampling-*` family or with a Task 10 schema.
4. Append-only surfaces (`15-decision-log.md`, `33-execution-journal.md` and its
   shards, `32-cloud-spend-ledger.md`) are appended to at the end only. Never
   renumber, reorder, or edit published content; corrections are later events.

---

## 3. State model — five distinct states per step

A passing fixture test never promotes a real external-input lock, container
digest, cloud deployment, pilot, or launch claim. Every Phase B step is tracked
against all five states below, and each must be reported separately.

| state | meaning | what can satisfy it |
| --- | --- | --- |
| `implementation_complete` | the code, schema, and focused tests exist and pass on bounded local fixtures | a narrow high-signal test command plus a static check |
| `external_verification_pending` | the step's real-world artifact (retrieved input, built image, account-bound plan) has not been produced or independently verified | only a separately authorized retrieval, build, or account-bound action clears this |
| `authority_freeze_pending` | no registered freeze, manifest promotion, or authority record binds the result | a decision-log row plus the corresponding registered artifact |
| `launch_review_pending` | Step 14's hostile review has not audited the step | only Step 14 clears this |
| `execution_pending` | nothing has actually been run against the real experiment | only an authorized execution clears this |

Every step in §6 declares its terminal state. **No Phase B step reaches
"scientifically complete" or "launch-ready".** In the repository's existing
vocabulary, the best any Phase B step reaches is
`implementation_complete; E2E_pending`, with the additional pendings above named
explicitly.

---

## 4. Milestone recording cadence

`AGENTS.md:50` is binding:

> "Update the handoff/status documentation after each major implementation
> milestone or coherent commit group, not after every command. Record scientific
> executions and deviations in the append-only execution journal. Never let
> progress prose outrun committed evidence."

The first draft of this plan wrongly deferred **all** status, handoff,
decision-log, spend-ledger, and journal updates to a single final reconciliation
commit. That is corrected: **each completed Phase B step records its own
justified authority, status, and journal evidence** at the milestone boundary,
without rewriting append-only history.

Per-step recording obligations:

| surface | what a completed Phase B step appends |
| --- | --- |
| `docs/project-status.json` | a new `systems[]` `status_record`. The `$defs/status_record` shape requires `id`, `status`, `scope`, `evidence_refs`, `blockers`, with optional `implementation_status` and `e2e_status`; `additionalProperties: false`. `status` ∈ `implemented\|partial\|specified\|in_progress\|not_implemented\|blocked\|boundary_only`; `scope` ∈ `standalone\|internal_harness\|offline_research\|production_9to5\|none`; `evidence_refs` are unique relative repo paths; `blockers` match `^B-[A-Z0-9-]+$`. **No schema edit is needed** to add a `systems[]` record. The root object and the `evidence` object are `additionalProperties: false` and const-pinned, so any *new top-level key* or `evidence` change would require editing `schemas/project-status.schema.json` — avoid that. |
| `15-decision-log.md` | one appended row per registered decision |
| `33-execution-journal.md` | one appended event under `## Current volume` |
| `34-tasks-6-10-vps-handoff.md` | a checkpoint paragraph only where evidence justifies it |
| `32-cloud-spend-ledger.md` | a `CL-0xx` row for any action with a cost dimension, **including zero-cost planning actions**, matching existing practice |

**Identifiers are computed at execution time, never hard-coded here.** The
first draft's hard-coded "next free DL-148" is removed. At the time of this
revision the highest present identifiers are `DL-147` and, in the current
journal volume, `EJ-20260730-0230`. Both will move. Compute them when you write:

```txt
grep -oE "DL-[0-9]+" docs/research/neurips-2026-workshop/15-decision-log.md | sort -t- -k2 -n | tail -1
```

Note the journal's ID convention has two live forms: the documented numeric
`EJ-YYYYMMDD-NNNN` (per `execution-journal/prologue.md`, "a monotonically
increasing four-digit sequence within each UTC date; IDs are never reused") and
a slug form used by recent entries (for example
`EJ-20260731-task6-step4a-revalidation`,
`EJ-20260731-task10-release-preparation`). Match whichever form the surrounding
current-volume entries use, and validate with
`python -m scripts.research.execution_journal check`.

---

## 5. Existing surfaces

### 5.1 The scientific contract already freezes most of Step 4

The binding contract is
`docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md` (3,949
lines); the controlling plan is
`docs/superpowers/plans/2026-07-28-resampling-null-core.md`. The Tasks 6–10
handoff fixes the source order `AGENTS.md` → `docs/project-status.json` →
`VPS_NEURIPS_2026_HANDOFF.md` → handoff → plan → design → decision log → spend
ledger → execution journal.

| Roadmap Step-4 item | Frozen at | Value |
| --- | --- | --- |
| Hypotheses / claim of record | §1, §3.1 | The Resampling Null; gate-conditional; a positive point estimate alone is insufficient |
| Arms | §6 | `REAL`, `SHAM`, `NONE`, `RESAMPLE`; uniform within-task draw of `{REAL, SHAM, NO_PACKET, NO_PACKET}` over 12 allocations, then a fair coin labels the two no-packet slots; sealed before any continuation |
| Post-trigger quotas | §6.1 | SWE 32,768 tokens / 32 tool calls / 60 min; τ³ 16,384 / 16 turns / 30 min |
| Endpoints | §8.1 | Objective binary `success`; all allocated blocks remain in ITT; an arm-specific infrastructure or model failure is zero |
| Estimands | §8.2 | Co-primary `Δ_content = Y_R − Y_S` and `Δ_excess = Y_R − no_feedback`; equal SWE/τ³ weighting; raw rows never pooled |
| Decision rule | §9.3 | Seven-condition intersection-union gate |
| Resolution floor | §9.4 | `q0` / `r95`; failure to exceed both `delta_star = 0.05` and `r95` yields `UNRESOLVED_RESAMPLING` |
| Verdict taxonomy | §9.6 | Seven verdicts, all publishable; none authorizes changing endpoints or deleting blocks |
| Power / tier | §9.5 | ≥ 0.80 power, ≤ 0.05 type-I; Clopper–Pearson tails `0.05/729` and `0.05/2187`; `C160` preferred, `C120` minimum; tier selection may not use pilot arm efficacy |
| Failure criteria | §16 | Thirteen stop-or-narrow triggers |
| Admission gates | §7.4, §4.1, §4.2 | Blinded packet-classifier AUROC upper bound below 0.60; eight SWE conditions; ten τ³ conditions |
| Differential-failure gate | §8.1 | `max \|f_a − f_a'\| ≤ 0.02`; larger imbalance marks the pipeline invalid and never licenses task deletion |
| Benchmark roster | §4.1, §4.2 | `microsoft/SWE-bench-Live@70ec57e8…`, dataset `SWE-bench-Live/MultiLang@608f7ae9…`, `microsoft/RepoLaunch@7735b1e7…`; `sierra-research/tau2-bench` v1.0.1 tag object `b711c1ea…`, peeled commit `fc0055dc…`, MIT |
| Subject model | §4.3 | `Qwen/Qwen3.6-35B-A3B-FP8` revision `95a723d0…`, Apache 2.0, `vllm==0.19.0`, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder` |
| Simulator | §4.2 | `Qwen/Qwen3.5-9B` revision `c2022362…`, greedy, separately metered serving subject |
| Sampling | §4.3 | SWE `T=0.6` / top-p 0.95 / top-k 20; τ³ `T=1.0` / top-p 0.95 / top-k 20 / presence 1.5 |
| **Topology candidate ladder** | §4.3 | **Already preregistered — see §5.2** |
| AWS architecture | §13.1 | Full Batch / ECR / S3 / DynamoDB / VPC / watchdog specification |
| Interruption contract | §13.3 | Checkpoint contents plus an atomic completion marker |
| Spend gate | §15 | Twelve-step pre-action gate and two hard invariants |

Consequence: **Step 4 is a reconciliation and ratification task, not a selection
task.**

### 5.2 The topology ladder already exists — Step 4 references it, does not invent it

The review asked for "a preregistered candidate ladder plus deterministic pilot
selection rule". Verification shows the design **already contains exactly that**,
at §4.3:

> "The topology and context cap are deliberately not frozen before the memory
> pilot. … The predeclared ladder is:
> 1. the sole L40S on `g6e.2xlarge` with tensor parallelism 1 at 32,768 tokens;
> 2. the sole L40S on `g6e.2xlarge` with tensor parallelism 1 at 65,536 tokens.
>
> The largest candidate that passes OOM, tool-call, output-parity, and p10
> throughput gates is frozen before confirmation. A topology change is a subject
> change because it can change kernels and numerics."

**This resolves the Step-4 exit-gate contradiction.** The frozen object is not a
single topology; it is *the two-rung one-GPU ladder plus the deterministic selection
rule* "largest candidate passing the four gates". The roadmap's requirement that
"no model choice remains ambiguous" is therefore satisfiable and must be stated
that way: the subject, roster, and candidate ladder are unambiguous; only the
rung is pilot-determined, by a rule fixed in advance.

Two constraints Step 4 must record explicitly, and Step 13 must enforce:

- **The pilot selects only among the two frozen rungs.** It may not invent,
  substitute, or interpolate a new subject configuration.
- **Selection uses only OOM, tool-call, output-parity, and p10 throughput
  gates** — never observed efficacy. This mirrors §9.5's rule that tier
  selection may not use pilot arm efficacy, and §10's rule that no arm-specific
  pilot effect may select a model, benchmark, endpoint, task, reserve, sample
  tier, or analysis.

Related: `VLLM_BATCH_INVARIANT=1` byte-equality is tested at Tier 1 with fixed
request order, concurrency, topology, and per-call seeds; failure is a Tier-1
no-go under the displayed topology and hour table.

### 5.3 Roster feasibility is a blocking gate, not a preference

Both tiers are currently recorded infeasible. Exact contract language:

> "`C120` is currently `FEASIBILITY_NO_GO`, not merely fragile. It becomes
> conditionally feasible only if the full base-commit, image, isolation, and
> three-pair audit yields, for every split `s`,
> `eligible_s >= C120_quota_s + 2 pilot_s + fixed_reserve_s`."

> "`C160` is presently `FEASIBILITY_NO_GO`: the current proxy has only nine C
> lineages. … The final gate is
> `eligible_s >= C160_quota_s + 2 pilot_s + fixed_reserve_s` for every split."

Concretely, under the current metadata proxy C120 needs at least 11 qualified C
and 16 qualified C++ lineages while the proxy has 9 and 14. The **only** remedy
the design offers is running the full base-commit, image, isolation, and
three-independent-pair qualification audit to convert proxy counts into real
qualified lineages. There is no fallback roster, no quota relaxation, and no
substitution path; failure records `FEASIBILITY_NO_GO`.

**Blocking gate G-ROSTER:**

> Phase B may proceed with **tier-agnostic** infrastructure. No final experiment
> manifest may be promoted, no pilot authorization may be issued, and no
> launch-readiness claim may be made, until either the eligibility inequality is
> genuinely satisfied for every split, or an explicit reviewed protocol
> amendment is adopted and registered through the authority surfaces.

Practical consequence for the design of the code: `cloud/manifests.py`,
`cloud/architecture.py`, `cloud/orchestration.py`, and `cloud/spend.py` must
**parameterize** tier rather than embed `C120`/`C160` constants, and the
manifest promotion path must refuse while `G-ROSTER` is unmet.

### 5.4 The nine cross-document conflicts Step 4 must resolve

1. **The roadmap treats roster and model as open; the design pins both.**
   Step 4 ratifies by reference and records the supersession.
2. **SWE-bench Verified and LiveCodeBench are already rejected alternatives.**
   DL-122 rejects SWE-bench Verified because 500 tasks collapse to twelve
   repository lineages. LiveCodeBench appears only as third-party reviewer
   feedback inside `31-cloud-execution-brief.md`, a file whose own text labels
   Part A "context, not instructions". Neither is an open option.
3. **`00-README.md` routes readers to a different paper.** It describes the
   detectability-audit study, states "Compute required: none", names
   `26-detectability-audit-design.md` as "The paper. Start here", and never
   routes to `docs/superpowers/specs/`. That referenced file is **absent** from
   the directory. Highest-severity documentation defect in scope.
4. **Both tiers are `FEASIBILITY_NO_GO`** — now handled as blocking gate
   `G-ROSTER` (§5.3), not as a caveat.
5. **τ³ version-string conflict, already adjudicated.** `pyproject.toml`
   declares `1.0.1` while the pinned `uv.lock` `tau2` entry declares `1.0.0`;
   the design makes commit, tag object, source blobs, lockfile blob, environment
   image, and installed dependency receipts authoritative. A pointer, not a
   decision.
6. **Serving topology and context cap** — resolved by §5.2 as a frozen ladder
   plus a deterministic rule, not as an open choice.
7. **Simulator compute is separate.** The AWS primary controller may not host a
   simulator; any simulator subject remains separately governed and cannot be
   pooled into the one-L40S AWS topology.
8. **Stale model rows in the decision log.** DL-01, DL-79, and DL-82 still name
   Qwen2.5-Coder-7B / `qwen2.5-coder:7b`. They belong to the retired
   placebo/gauge lineage and are not marked superseded by DL-122.
9. **The design's own calendar is stale.** §17 allocates "Aug 7–8 | freeze
   dependencies, preregistration, task roster, analysis hash", while the roadmap
   still has Task 10, Steps B6–B14, and Step 4B ahead of that point.

### 5.5 Azure — unresolved protocol dependency, not part of an AWS-only pilot

Verified status: Azure is a **parity/precision slice, not scientifically
mandatory for the primary claim**.

> "Azure is a parity/precision slice, not an automatic full-confirmation
> fallback." … "Full Azure substitution therefore needs a new budget and
> approval."

BF16 is a distinct subject: "A BF16 run is a distinct subject and may be used
only as a separately reported precision/provider replication", and "FP8 and BF16
results are never pooled as if they were the same subject." If the exact NC48
node cannot be allocated, the BF16 block is dropped; if the A10 simulator node
is unavailable, BF16 replication is SWE-only.

**However, there is a genuine unresolved inconsistency in the binding design.**
Tier-1 gate item 7 reads:

> "7. the independent AWS and Azure lease-expiry kill drills remove every tagged
> compute, pool, disk, endpoint/IP, and sibling container without relying on the
> study controller;"

and §13 closes with "Failure of any item invalidates the topology, hour table,
and cost table." As literally written, an unconditional Tier-1 item names a
provider the same section calls optional. No sentence anywhere in §13 states
what happens to item 7 if Azure is unavailable.

Compounding this: the spend ledger records Azure **verified spendable $0.00**,
with the new application declined because the account previously received
sponsorship. **AWS credits do not authorize Azure spending.**

**Resolution for this plan:** Azure execution is marked an **unresolved protocol
dependency**, explicitly outside the AWS-only pilot. Phase B implements the
AWS lease-expiry kill drill only. Step 4 must register a decision that either
(a) amends Tier-1 item 7 to be AWS-only for the AWS-only pilot, scoping the
Azure drill to a later Azure-authorized phase, or (b) retains item 7 as written
and records the resulting dependency: a separate Azure account, separate quota,
separate cost, and a separate authorization, none of which exist. Silence is not
an option, because item 7 as written blocks Tier 1.

### 5.6 Secrets — two distinct classes, two distinct rules

The first draft's blanket "never argv or environment" was too strong as a
general statement and too weak as a specific one. Verification shows the design
imposes a **very strict rule on scientific key material** and a **different rule
on infrastructure credentials**. Both must be stated separately.

**Class A — scientific key material** (assignment master key, unblind key, and
every derived subkey). Design §4.0:

> "Neither the assignment master key nor any derived subkey may appear as an
> argv value, environment variable, run-root file, scientific/operational
> record, exception, log, telemetry event, worker input, or packet capability. A
> CLI may receive only the path to an owner-only-readable key file outside the
> run root. The trusted process opens it unbuffered, preallocates
> `bytearray(32)`, performs one exact `readinto`, rejects a short read, attempts
> a one-byte `readinto` and rejects extra data, and never copies the file."

and:

> "No public transaction accepts master/subkey bytes or a caller-implemented
> secret source. The concrete trusted-controller `AssignmentSecretStore` is the
> only component that opens the owner-only master-key file."

So for Class A, "never environment" is **correct and contractually required**.
The existing implementation is `resampling_null/secrets.py`
(`AssignmentSecretStore`, non-copyable purpose-bound `AssignmentSecretHandle`
and `UnblindSecretHandle`). Phase B must not create a second path to this
material.

**Class B — infrastructure credentials** (ECR pull, S3 write, DynamoDB lease
read). The roadmap says only:

> "Store secrets through AWS-managed secret mechanisms, never Git or images."

Normal AWS Batch and Secrets Manager delivery — an IAM task/execution role, or a
`secrets` entry in a job definition resolving into the container environment —
is therefore **permitted for Class B**, and the plan no longer forbids it. The
design's actual container-level constraints are about *who* holds credentials,
not about the injection channel:

> "benchmark containers receive neither the Docker socket nor cloud credentials,
> and their network namespaces block IMDS. The controller uses a minimal per-run
> role restricted to its content-addressed storage prefix plus consistent
> `GetItem` on the exact run lease key/table; it cannot renew the lease. The
> independent watcher has a separate write/termination identity."

**Threat model and minimum invariants (both classes):** no secret of either
class may enter Git, an image layer, argv, a log, a receipt, a scientific
record, an exception, a telemetry event, or any **worker-visible scientific
environment**. Class A additionally may never enter *any* environment variable
or run-root file, and is delivered only as a path to an owner-only file outside
the run root. Class B is delivered by IAM role or AWS-managed secret injection,
scoped per-run and least-privilege, and never reaches a benchmark container.
The preferred Class B posture remains role-based credentials with no long-lived
secret at all.

### 5.7 Reusable code — do not rebuild these

| Concern | Existing surface | What it already guarantees |
| --- | --- | --- |
| Content-addressed records, schema validation | `resampling_null/artifacts.py`: `validate_record`, `load_record`, `write_record`, `write_jsonl_artifact`, `validate_scientific_graph`, `validate_preunblind_graph`, `seal_artifact_root`, `verify_artifact_root` | registered-schema validation, atomic no-overwrite writes, ancestry and closure checks, root receipts hashing the complete closure |
| Root-confined reads | `resampling_null/authority_refs.py`: `AuthorityRefReader.read_bound/read_bytes/decode_json/verify_closure`, `decode_artifact_ref`, `walk_artifact_refs` | descriptor-bound reads confined to the run root, mandatory digest and length verification, strict JSON decoding, closure validation |
| Strict JSON | `resampling_null/json_io.py`: `plain_json`, `load_json_bytes`, `run_root`, `resolve_inside` | duplicate-key and non-finite-constant rejection, confined path resolution |
| Publication transactions | `publication.py` (`BoundPublication.publish_bytes/commit`), `publication_quarantine.py` (`quarantine_source`, `restore_bound_source`, `recheck_quarantine`), `publication_rollback.py` (`rollback_publication`, `rename_no_replace`), `task6_state.py` (`begin_paired_publication`, `recover_paired_publication`, `prepare_paired_publication_entry`, `install_paired_publication_entry`) | namespace lease, no-overwrite atomic publish, identity checks, quarantine and rollback, recoverable all-or-none two-file commit |
| Deterministic shard allocation | `power.py`: `simulate_power_shard`, `_assert_power_write_open`, `_complete_shards`, `select_validation_cells` | contiguous immutable cell ranges per `shard_index`, rejection of out-of-topology indices and duplicate `(stage, phase, generation, shard_index)` identities, complete-shard-set requirement before any authority merge |
| Interruption and rerun semantics | `branch_controller.py`: `prepare_opaque_work_orders`, `seal_unscored_attempt`, `authorize_full_block_rerun`, `finalize_failed_second_attempt`, `seal_task_block` | four fixed ordered opaque slot work orders; exactly one byte-identical full-block rerun for a validated pre-endpoint outage; conservative infrastructure-failure outcomes without grading |
| Prefix sealing | `prefix_index.py`: `seal_prefix_index`, `_rollback_owned_publication`, `_seal_transaction_outcome` | unique candidate refs, process reservation plus root transaction, fresh candidate reconstruction, rollback and recovery |
| Timing cap and no-go | `power.py`: `PowerGridSpec.max_projected_wall_seconds` (loader requires `43200`), `screen_power_grid`, `_projected_screen_wall_seconds`, `_production_timing_probe`, `_validate_screen_timing_admission`; `timing_no_go.py`: `TimingNoGoBindings`, `create_timing_no_go`, `verify_timing_no_go` | authority-bound all-cell timing probe; rejection of a screen whose projected total work exceeds the frozen twelve-hour cap with no parallelism discount; exclusive host- and artifact-bound no-go record |
| Provider, meter, parser pinning | `provider_contracts.py`: `ValidatedTaskLane`, `ValidatedLane`, `ValidatedProviderPlan`, `validate_provider_lane_plan`; `provider_contract_assets.py`: `decode_contract_ref`, `_verify_ref_closure`, `_verify_registered_authority_graph`, `_validate_source_revisions`, `validate_call_contract`, `validate_parser_contract`, `validate_meter_contract`, `validate_task_contract` | closed per-lane provider plan with `prefix_caps`, `branch_caps`, `simulator_caps`, subject/simulator/tool-parser/meter contract refs, cap decoders over `generated_tokens`, `model_calls`, `tool_calls`, `wall_clock_ms` |
| Capability isolation | `packet_capabilities.py`: `resolve_packet_capabilities`, `OpaqueSlotGrant`, `TaskPacketCapabilities`, `SealedSlotCapability`, `seal_slot_capability`, `SlotArtifactLoader` | four preregistered-order opaque grants whose worker-visible packet names are a pure function of `(task_id, allocation capability digest)`; a role allowlist containing no scientific record kind; descriptor-bound `O_NOFOLLOW` walks with mandatory digest verification |
| Secret custody (Class A) | `secrets.py`: `AssignmentSecretStore`, `AssignmentSecretHandle`, `UnblindSecretHandle` | store-minted, non-copyable, purpose-bound single-use handles consumed from a validated owner-only path outside the run root |
| Blinding and unblinding | `freeze.py` (`snapshot_sources`, `freeze_analysis`, `verify_analysis_freeze`, `verify_frozen_analysis_inputs`), `blinding.py` (`seal_blinded_projection`, `issue_unblind_permit`, `unblind_and_publish_analysis`) | named-source freeze binding each name to an exact immutable `ArtifactRef`; HMAC permit bound to manifest, schedule, prefix, ledger, projection, freeze; clear rows held only in memory; durable one-way taint before any clear-ledger parse |
| Execution authority | `execution_authority.py`: `PrefixExecutionAuthority`, `load_prefix_execution_authority`; `power.py`: `SyntheticPowerAuthority`, `ImplementationVerificationPowerAuthority`, `RosterBoundPowerAuthority`, `load_power_authority`, `load_power_config` | authority projection from manifest/schedule/registry; strict separation of synthetic, implementation-verification, and roster-bound authority kinds |
| Canonical import and preflight | `preflight.py`: `import_closed_json`, `import_task_registry`, `import_assignment_program`, `verify_ed25519_canonical_json`, `_publish_cas`, `ConfirmationPreflightRegistry` | canonical signed JSON import, content-addressed publication, closed task and assignment grammars |
| Local isolation substrate | `synthetic_environment.py`: `SyntheticEnvironmentFactory`, `SyntheticEnvironmentHandle`, `ControllerEnvironmentIPC` (1 MiB frame cap, 2.0 s timeout), `_assert_pairwise_isolated`, fd-scoped `_open_root`/`_open_workspace` | isolated worker execution with proven pairwise isolation and bounded controller IPC |
| Digest and snapshot receipts | `foundation/artifacts.py`: `sha256_file`, `canonical_json_bytes`, `write_atomic_bytes/json/jsonl`, `bind_artifact_publication`, `read_bound_artifact_set`; `foundation/snapshot_receipt.py`: `verify_pinned_snapshot`, `SnapshotFile`, `SnapshotInventoryEntry`; `foundation/model_cache.py`: `pinned_snapshot_path`, `prepare_pinned_snapshot`, `verify_pinned_snapshot` | per-file SHA-256 model-snapshot receipts, symlink and reparse rejection, TOCTOU inventory re-check, canonical-JSON binding |
| Lockfile pinning | `foundation/environment.py`: `setup_plan`, `verify_lock` with `UV_VERSION`, `PYTHON_SERIES`, exact `TRANSFORMERS_COMMIT`, registry-source enforcement, `MAX_LOCK_BYTES` | rejection of unpinned or non-registry dependency edges |
| Cloud quote/authorization *pattern* | `foundation/budget.py`: `BudgetState`, `ItemizedCloudQuote`, `CloudQuote`, `CloudAuthorization`, `authorize_reproduction_quote`, `authorize_optional_cloud_job`, `record_cloud_job`; `foundation/cloud_bundle.py`: `CloudBundleRequest`, `conservative_cloud_quote`, `build_bundle_manifest`, `build_cloud_bundle` | a reusable *shape* only. `MAX_LIFETIME_CLOUD_USD = 45.0` and `MAX_PREPAID_CREDIT_USD = 38.0` are foundation-training-scoped and are **not** this study's caps |
| Resource watchdog *pattern* | `foundation/resources.py`: `ResourceSample`, `ResourceDecision`, `ResourceGuard`, `GUARD_REASONS`; `foundation/telemetry.py`: `LiveResourceSampler`, `read_nvidia_smi`, `aggregate_telemetry` | pause/fail decisions from samples with a closed reason set |

### 5.8 Schema integration surfaces — registry edits, not just new files

**Verified:** the schema registry is explicit tuples, **not** a glob. A new
schema file on disk is invisible until registered, and there is no
orphan-file-on-disk test, so an unregistered file fails nothing silently.

`src/pneuma_lab/schemas/__init__.py` exports
`SCHEMA_DIR`, `INPUT_SCHEMA_FILES`, `OUTPUT_SCHEMA_FILES`,
`ENVELOPE_SCHEMA_FILES`, `IO_BUNDLE_SCHEMA_FILES`,
`EVIDENCE_CAMPAIGN_SCHEMA_FILES`, `EXPRESSIVE_VIEW_SCHEMA_FILES`,
`TRAINING_SCHEMA_FILES`, `MANIFEST_SCHEMA_FILES`, `FOUNDATION_SCHEMA_FILES`,
`GAUGE_SCHEMA_FILES`, `RESAMPLING_SCHEMA_FILES`, `ALL_SCHEMA_FILES`,
`schema_path`, `load_schema`, `load_all_schemas`.

Registering the Phase B schemas requires **all** of the following, and each step
that adds a schema must do its own share:

1. Define a new `CLOUD_SCHEMA_FILES` tuple in
   `src/pneuma_lab/schemas/__init__.py` (a new bucket is correct: these are
   non-frame manifests, not input/output frames).
2. Add `CLOUD_SCHEMA_FILES` to the `ALL_SCHEMA_FILES` concatenation.
3. Add `"CLOUD_SCHEMA_FILES"` to `__all__`.
4. **No** `validate.py` change: `FRAME_KIND_TO_SCHEMA` and
   `BUNDLE_KIND_TO_SCHEMA` are for frames and bundles. These schemas declare
   `x-pneuma-schema-kind`, not `x-pneuma-frame-kind`, so they need no
   frame-kind entry. A dedicated validator, if wanted, follows the existing
   `_campaign_validator` / `validate_campaign` pattern.
5. **No** `src/pneuma_lab/__init__.py` change: `INPUT_FRAMES` / `OUTPUT_FRAMES`
   are frame-only.
6. `tests/test_schema_loads.py` — add `EXPECTED_CLOUD_COUNT`, assert it in
   `test_expected_counts`, and add a `test_cloud_schema_bucket_registered`
   exact-name-tuple test mirroring `test_resampling_schema_bucket_registered`.
   Note this file already asserts `len(RESAMPLING_SCHEMA_FILES) == 14` and
   `EXPECTED_RESAMPLING_COUNT = 14`; do not disturb those.
7. `docs/io-contract.md` — add a short H2 section after `## Bundles (I/O
   containers)` stating the `x-pneuma-schema-kind` and validator entry point.
   Do **not** add rows to the two frame tables.
8. `docs/source-map.md` — these are lab-original with no 9to5 grounding, so
   they belong under `## Divergences (Pneuma Lab is not a 1:1 port)`, following
   the existing "_new to the lab_" precedent, not in the grounding tables.
9. `docs/project-status.json` — reference the new schema paths from the
   relevant `systems[]` record's `evidence_refs`.

### 5.9 Confirmed absences — the actual Phase B build

Verified repository-wide, excluding `.git` and `.venv`:

- **No** `Dockerfile`, `Containerfile`, `docker-compose*`, `*.tf`, `*.tfvars`,
  `*cloudformation*`, or `cdk.json`.
- **No** `.github/` directory and **no** tracked `*.yml` or `*.yaml`.
- **No** SBOM in any format.
- **No** `boto3`/`botocore` in `pyproject.toml` dependencies or `dev` extras,
  and **not present in `.venv`**. They exist only in the ambient system Python
  (1.34.46). Any use is therefore a **new dependency decision**, governed by
  `CLAUDE.md`'s "avoid adding heavy dependencies without a concrete phase that
  needs them". See §6, Step 11.
- **No** dollar-denominated spend enforcement for this study, **no** runtime
  watchdog process, **no** lease or idempotency store. `storage.py`'s
  `LocalTestStorageLease` is explicitly local-test.
- **No** license, contamination, OCI-digest, or dataset-revision field anywhere
  in the `resampling-*` schema family; the only `provenance` definition is
  `{design_sha256, code_sha256}`.
- **No** forensic-journal implementation. `scripts/research/execution_journal.py`
  provides `check` and `migrate` over the markdown journal; there is no
  machine-written run journal, and no `forensic`-marked test exists under
  `tests/resampling_null/`.
- Local tooling: `docker` **is** present at `/usr/bin/docker`; `terraform` and
  `syft` are **not** installed.
- `configs/` contains exactly one file, `configs/g1.json` (gauge study, local
  Ollama host), with no cloud content.

### 5.10 Funding and quota reality

Verified eligible AWS balance **$10,000.00** (YC Activate, active through
2028-07-31, EC2 explicitly in the applicable-products list). The separate $100
Free Tier credit (through 2027-07-27) is **conservatively excluded**. Azure,
OpenAI, and Anthropic verified spendable balances are **$0.00**. Settled
economic cost, active reservations, and cash charged are all **$0.00**.

Cumulative kill caps (CL-004): **$500**, then **$5,100** for `C120` or **$6,400**
for `C160`, then **$14,900** / **$16,200** after the respective eligible
expansion.

Quota (CL-013, **pending**): `us-east-1` On-Demand and Spot G/VT support cases
`178540521600334` and `178540523000045`, require 8 vCPUs for the approved
one-instance topology. **Applied quotas remain 0.** A requested quota is not an
applied quota, and credits do not bypass quotas or spend gates.

No current account/AZ-specific rate is a receipt for `g6e.2xlarge`; re-query
and bind it during the separately authorized account-plan step. S3 Standard
and gp3 planning numbers remain historical planning inputs, not spend authority.

---

## 6. Step-by-step plan

### Test policy applied to every step

`AGENTS.md:94` is binding and governs all of the below:

> "Software tests are lightweight guardrails, not research deliverables. Default
> to one narrow high-signal test command per behavior change and one static
> check per slice; do not run broad or repeated suites without a concrete
> shared-surface risk or explicit user request. Every test process has a hard
> 60-second wall-clock ceiling unless the user explicitly approves longer."

Therefore:

- The first draft's routine `python -m pytest tests/cloud -q` is **withdrawn**.
- Each step below names **one narrow command** plus **one static check**.
- Every test process is invoked under `timeout 60s`.
- `scripts/check_test_budget.py` enforces `SMOKE_BUDGET = 8` and
  `RESAMPLING_BUDGET = 65` test functions; Phase B must not inflate
  `tests/smoke` or `tests/resampling_null`. If a Phase B budget is wanted for
  `tests/cloud`, add it there deliberately rather than growing without bound.
- Default pytest discovery is `testpaths = ["tests/smoke"]` with
  `addopts = "--import-mode=importlib -p no:cacheprovider -q -m \"not qwen_smoke and not foundation\""`.
  `tests/cloud/` is therefore invisible by default, which is correct; do not
  widen discovery.
- Broad hostile and adversarial campaigns remain **deferred to Step 14**.

Static check per slice, one of:
`timeout 60s python -m ruff check <paths>`,
`timeout 60s python -m mypy <paths>`,
`timeout 60s python -m compileall -q <paths>`,
`git diff --check`.

---

### Step 4 — Freeze the real experiment design

**Character:** documentation and authority records only. No source change.

**Files.** New `docs/research/neurips-2026-workshop/38-experiment-design-freeze.md`.
Appended rows in `15-decision-log.md` (identifier computed at write time; highest
present at revision was `DL-147`). One appended execution-journal event. Possible
repair of `00-README.md`. A `systems[]` record and a `CL-0xx` zero-cost ledger
row.

**Work.** Ratify by reference the already-frozen design (§5.1). Register the
frozen object as **subject + roster + two-rung one-GPU candidate ladder + deterministic
selection rule** (§5.2), explicitly forbidding pilot invention of a new
configuration and explicitly forbidding efficacy-based rung selection. Resolve
the nine conflicts in §5.4. Register the Azure decision required by §5.5.
Register `G-ROSTER` (§5.3) as a blocking gate.

**Blocked on:** §2.2's Phase A verification.

**Terminal state:** `implementation_complete` (documents exist);
`authority_freeze_pending` cleared for the items it registers;
`external_verification_pending` for roster feasibility (`G-ROSTER`);
`launch_review_pending`; `execution_pending`.

**Verification.** `timeout 60s python -m pneuma_lab.status --check` after the
`systems[]` edit; `timeout 60s python -m scripts.research.execution_journal check`
after the journal append; `git diff --check`.

---

### Step 5A — Input-lock schema, verifier, fixtures, retrieval protocol

**Files.** New `schemas/cloud-input-lock.schema.json`,
`schemas/cloud-experiment-manifest.schema.json`,
`src/pneuma_lab/cloud/{errors,manifests,inputs}.py`,
`tests/cloud/{test_manifests,test_inputs}.py`, registry edits per §5.8,
`docs/research/neurips-2026-workshop/39-external-input-lock.md`.

**Why a new schema is unavoidable.** No `resampling-*` schema has a license,
contamination, OCI-digest, or dataset-revision field. The design's Step-5
obligations — base-commit license audit; immutable `linux/amd64@sha256:`
manifest/config/layer sets mirrored provider-locally; bounded contamination
disclosure through public-artifact and lineage/date sensitivities rather than a
fictional cutoff; binding of the complete row hash, base commit and tree, issue
and PR identifiers, date, image digests, parser/command/F2P/P2P digests, and
license evidence — have nowhere typed to land except the untyped
`eligibility_manifest_ref` and `source_revision_refs` slots.

`cloud-input-lock` carries `model_pins[]` (repository, revision, license,
per-file snapshot receipt ref), `tokenizer_pin`, `benchmark_pins[]` (repository,
commit, dataset revision, license, task-manifest digest), `container_bases[]`
(registry plus `linux/amd64@sha256:` digest), `verifier_sources[]`,
`contamination_receipts[]`, `license_receipts[]`. All follow the existing
`resampling-*` `$defs` verbatim: `artifact_ref` with its anti-traversal
`relative_path` regex, `sha256` `^[0-9a-f]{64}$`, strict `Z`-suffixed
`frozen_timestamp`, `provenance` requiring `design_sha256` and `code_sha256`,
`additionalProperties: false`, Draft 2020-12, 4-space indentation, no BOM, no
comments, `x-pneuma-schema-kind`, `x-pneuma-version 0.1.0`.

**Reuse.** `foundation/snapshot_receipt.py`, `foundation/model_cache.py`,
`foundation/environment.py::verify_lock`, `resampling_null/artifacts.py`,
`authority_refs.py`, and `provider_contract_assets.py::_validate_source_revisions`.

**Blocked on:** Step 4.

**Terminal state:** `implementation_complete`; **`external_verification_pending`
— no real external input has been retrieved or verified**;
`authority_freeze_pending`; `launch_review_pending`; `execution_pending`.
Explicitly: Step 5A **does not** satisfy "Lock external inputs".

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_manifests.py tests/cloud/test_inputs.py -q`,
plus `timeout 60s python -m ruff check src/pneuma_lab/cloud`. Behaviors covered:
manifest round-trip validity; a mutable tag (`:latest`, a branch name, an
unpinned revision) is rejected; a digest mismatch fails closed; a missing license
receipt fails closed; the retrieval plan resolves from digests alone with no
network and no mutable-tag lookup.

**Zero-cost boundary.** Verification of pins only, against local fixtures. No
model, dataset, or image is pulled.

---

### Step 5B — Real external-input receipts *(separately authorized)*

**Character.** This is the step that actually satisfies the roadmap's "Lock
external inputs" exit gate: "every scientific input can be retrieved and
hash-verified without consulting mutable tags or unrecorded local state."

**Work.** Produce genuine license receipts at each task's base commit; genuine
revision and snapshot receipts for the pinned model and tokenizer; genuine
contamination receipts; and genuine OCI manifest/config/layer digests for every
container base. Mirror bytes provider-locally as the design requires.

**Requires separate authorization.** This step performs network retrieval and
consumes local storage at meaningful scale — the ledger's own planning evidence
projects roughly 352 GiB (C120) / 470 GiB (C160) of cold compressed image pulls,
or about 321/428 GiB after sample-like deduplication. That is a real resource
action with a cost dimension and must be requested, approved, and recorded as a
`CL-0xx` ledger row before it begins.

**Blocking rule:** **Step 5B must complete before the immutable experiment
manifest is promoted.** A manifest promoted on Step 5A fixtures alone would be a
false artifact.

**Blocked on:** Step 5A, plus its own authorization. Interacts with `G-ROSTER`:
the base-commit qualification audit that resolves roster feasibility (§5.3) is
substantially the same work as Step 5B's license and image audit, so they should
be planned together.

**Terminal state:** on completion, `external_verification_pending` clears for
inputs; `authority_freeze_pending`, `launch_review_pending`, and
`execution_pending` remain.

---

### Step 6 — Create the AWS architecture

**Files.** New `infra/terraform/*`,
`schemas/cloud-architecture-manifest.schema.json`,
`src/pneuma_lab/cloud/architecture.py`,
`tests/cloud/{test_architecture,test_iac_plan}.py`, registry edits per §5.8,
`docs/research/neurips-2026-workshop/40-aws-architecture.md`.

**Character.** Transcription of design §13.1, which already fixes: region
`us-east-1`; a Batch managed EC2 compute environment with `minvCpus = 0`, a
custom GPU AMI pinned by AMI ID plus root-snapshot ID plus a bootstrap SHA-256,
one-instance maximum, one whole-instance job per node, and an On-Demand
environment pinning `instanceTypes=[g6e.2xlarge]`, `maxVCpus=8`,
`allocationStrategy=BEST_FIT`, with exactly one runnable controller job
requesting 8 vCPUs, one GPU, and allocatable memory; only the two TP1 subject
rungs are admissible and simulator co-location is prohibited; host Docker exposed only to the privileged controller with
instance-store devices enumerated, formatted, and mounted as Docker's data root;
benchmark containers with neither the Docker socket nor cloud credentials and
with IMDS blocked at the network namespace; a minimal per-run controller role
restricted to its content-addressed storage prefix plus consistent `GetItem` on
the exact run lease key and table, which **cannot renew the lease**; ECR for
digest-pinned images; one-AZ private networking with an action-manifested
endpoint set (ECR API, ECR DKR, S3, DynamoDB lease reads, ECS
control/agent/telemetry, CloudWatch Logs, and whichever of STS/EC2 the measured
bootstrap requires) with endpoint hourly and data-processing charges as explicit
meters; S3 Standard with a manifest-bound lifecycle-policy identifier, absolute
deletion date, and abort-incomplete-multipart rule; CloudWatch Logs with fixed
retention; AWS Budgets alarms; and an **independently deployed** EventBridge
Scheduler plus Lambda stop path with a DynamoDB lease and a minimal termination
role holding a separate write/termination identity.

Architecture must be **tier-agnostic** per `G-ROSTER`: tier is a variable, not a
constant.

**Evidence taxonomy — three clearly separated levels.** The first draft wrongly
implied `terraform validate` alone yields a reviewable deployment. It does not.

| level | evidence | authorization |
| --- | --- | --- |
| L1 static | `terraform fmt -check -recursive` (deterministic formatting); `terraform init -backend=false` plus `.terraform.lock.hcl` provider-lock verification; `terraform validate`; static IAM/policy assertions parsed from the `.tf` and manifest; manifest-to-variable parity | none needed; but `terraform` is **not installed locally**, so these tests must skip cleanly and record a skip rather than a pass |
| L2 credential-free plan | `terraform plan` against a mock/offline provider path where technically possible; otherwise explicitly recorded as unavailable | none needed |
| L3 account-bound plan | `terraform plan` against the real account | separate authorization; produces a distinct receipt; **never conflated with L1/L2** |

**`terraform apply` is never run in Phase B, at any level.**

**Blocked on:** Step 5A.

**Terminal state:** `implementation_complete` at L1 (and L2 where possible);
`external_verification_pending` until L3; `authority_freeze_pending`;
`launch_review_pending`; `execution_pending`.

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_architecture.py tests/cloud/test_iac_plan.py -q`,
plus `timeout 60s python -m ruff check src/pneuma_lab/cloud`. Behaviors covered:
manifest-to-`.tf`-variable parity; the IAM policy denies anything outside the
run's content-addressed S3 prefix and the exact DynamoDB lease key and table;
the controller role has no lease-renew action; the watcher identity is distinct
from the controller identity; provider lock file present and pinned; tier does
not appear as a hard-coded constant. Terraform-binary-dependent assertions skip
when the binary is absent and **record that skip explicitly** — a skip is not a
pass.

---

### Step 7A — Dockerfiles, dependency locks, static verification, build recipe

**Files.** New `infra/docker/{controller,model-server,benchmark-worker}/Dockerfile`
plus `*.lock`, `schemas/cloud-image-manifest.schema.json`,
`src/pneuma_lab/cloud/images.py`, `tests/cloud/test_images.py`, registry edits
per §5.8.

**Character.** Three separate images as the design requires. Base images pinned
by digest; `vllm==0.19.0` and the CUDA, driver, and PyTorch stack pinned. A
written, reproducible build recipe with explicit build arguments, ordering, and
determinism measures. Static verification of all of the above.

**Terminal state:** `implementation_complete`; **`external_verification_pending`
— no image exists, no digest exists, no SBOM exists**;
`authority_freeze_pending`; `launch_review_pending`; `execution_pending`.

**Explicitly: Step 7A does not satisfy Step 7.** It cannot satisfy the
reproducibility, image-digest, or SBOM exit gates, because no image has been
built.

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_images.py -q`, plus
`timeout 60s python -m ruff check src/pneuma_lab/cloud`. Behaviors covered:
every `FROM` carries an `@sha256:` digest; no unpinned `pip install` line; the
manifest digest binding verifies and fails closed under substitution; the build
recipe parses and names every determinism control.

---

### Step 7B — Authorized deterministic builds, SBOM, digests

**Character.** This is the step that satisfies Step 7's exit gate ("rebuilds are
reproducible or deviations are explicit and blocking").

**Work.** Perform authorized deterministic builds; generate SBOMs; inspect
images; **build each image at least twice and compare**, recording either
reproducibility or an explicit, blocking deviation; record immutable digests
into `cloud-image-manifest`; prove that scientific outputs bind to the exact
images that produced them.

**Feasibility notes.** `docker` is present locally at `/usr/bin/docker`, so
builds can be **local and zero-credit** — no ECR push and no AWS spend is
required to satisfy this step. No SBOM tool (`syft` or equivalent) is installed;
selecting and pinning one is part of this step and is a dependency decision to
record. GPU-dependent image layers may not be locally verifiable; anything that
cannot be built locally must be named as a residual
`external_verification_pending` item rather than assumed.

**Requires separate authorization** for the build action (network pulls of base
images, meaningful local disk).

**Blocking rule:** **Real builds must occur before the Step 14 launch review**,
even if they remain local and zero-credit.

**Blocked on:** Step 7A, Step 5B (base-image digests), plus its own
authorization.

---

### Step 8 — Implement orchestration and interruption safety

**Files.** New `src/pneuma_lab/cloud/{orchestration,shards,reconcile}.py`,
`schemas/cloud-job-lease.schema.json`,
`tests/cloud/{test_orchestration,test_shards,test_reconcile}.py`, registry edits
per §5.8.

**Character.** Reuse aggressively. `power.py::simulate_power_shard` already
provides deterministic contiguous shard allocation with duplicate-identity
rejection; `branch_controller.py` provides the exactly-one byte-identical rerun
and failed-second-attempt semantics; `publication.py` and `task6_state.py`
provide idempotent, recoverable publication. Step 8 is a **lease layer plus a
submit/cancel/reconcile state machine over those primitives**, not a second
results model.

Retry classification consumes design §13.3: restore must match the prior
boundary receipt before the next model call, and any mismatch invalidates the
entire four-arm task block — one failed arm is never silently replaced.

**Blocked on:** Step 6 (lease table shape).

**Collision:** none, **provided** `power.py` and `branch_controller.py` are
wrapped, not modified.

**Terminal state:** `implementation_complete` against local fakes;
`external_verification_pending` (no real DynamoDB or Batch semantics exercised);
`authority_freeze_pending`; `launch_review_pending`; `execution_pending`.

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_orchestration.py tests/cloud/test_shards.py tests/cloud/test_reconcile.py -q`,
plus `timeout 60s python -m mypy src/pneuma_lab/cloud`. Behaviors covered: a
synthetic interruption mid-shard yields exactly one valid terminal history;
duplicate delivery of the same assignment produces exactly one scientific
sample; an expired lease fails closed; conditional-write contention resolves to
a single winner.

---

### Step 9 — Implement spend protection

**Files.** New `src/pneuma_lab/cloud/{spend,watchdog,projection,approval}.py`,
`schemas/cloud-spend-authorization.schema.json`,
`schemas/cloud-approval-receipt.schema.json`,
`tests/cloud/{test_spend,test_watchdog,test_projection,test_approval}.py`,
registry edits per §5.8.

**Character.** Implement design §15 literally — the twelve-step pre-action gate
and both invariants:

```txt
provider_settled + provider_active_reservations + proposed_provider_reservation
    <= verified_eligible_provider_balance

project_settled + project_active_reservations + proposed_reservation
    <= applicable_cumulative_tier_stop
```

with the caps and balances in §5.10. All invariant terms use the frozen
conservative USD-equivalent conversion; any tax, fee, or FX exposure not covered
by credits enters both the worst-case reservation and an explicit cash-liability
field.

Three constraints encoded as hard behavior, not documentation:

- **AWS Budgets alarms are advisory only.** Budget alerts do not enforce a stop
  and never substitute for the independent lease-based watcher plus teardown
  verification.
- **Silent fallback is forbidden.** A Spot eviction, capacity substitution,
  tensor-parallel or context change, extra retry, added node, or provider
  substitution is not an implicit retry unless already frozen; otherwise it
  requires a newly priced, hashed, and approved action.
- **Cross-provider isolation.** AWS balance never authorizes Azure spending
  (§5.5). The invariant is per-provider by construction.

**Reuse.** Copy the *pattern* of `foundation/budget.py` and
`foundation/resources.py`; do not import them (their caps are foundation-scoped).

**Blocked on:** Steps 6 and 7A.

**Terminal state:** `implementation_complete`; `external_verification_pending`
(no real price re-query, no real balance digest);
`authority_freeze_pending`; `launch_review_pending`; `execution_pending`.

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_spend.py tests/cloud/test_watchdog.py tests/cloud/test_projection.py tests/cloud/test_approval.py -q`,
plus `timeout 60s python -m ruff check src/pneuma_lab/cloud`. Behaviors covered:
each invariant fails closed exactly at its boundary; the reservation is appended
before resource creation; an unreserved settlement is rejected; the approval
receipt is bound to exact manifest hashes so a one-byte change invalidates it;
the watchdog terminates on a projection overrun; no fresh watchdog lease means
no new model or API call.

---

### Step 10 — Implement evidence, blinding, and security controls

**Files.** New
`src/pneuma_lab/cloud/{binding,receipts,worker_env,secrets_aws,journal}.py`,
`schemas/cloud-result-binding.schema.json`,
`tests/cloud/{test_binding,test_worker_env,test_secrets,test_journal}.py`,
registry edits per §5.8.

**The packet-capability claim must be preserved exactly.** The registered
property of `packet_capabilities.py` is **peer-slot and donor opacity, not
self-arm opacity**. A packet-bearing worker reads its own packet text because
that text is the intervention; the REAL/SHAM contrast is protected by
token-parity machinery instead.

**Wording gate (required, not optional).** Add an explicit automated gate that
prevents future documentation or schemas from claiming full self-arm blindness:
a test asserting that the Phase B schema descriptions, module docstrings, and
`docs/research/neurips-2026-workshop/*` Phase B files contain no
self-arm-blindness claim (for example, matching a denylist of phrases such as
"arm-blind worker", "workers cannot see their own arm", "full arm blindness"),
and that any capability description present states the peer-slot/donor scope.
This gate is cheap, runs in the same narrow command, and is the only reliable
defense against the claim drifting upward over time.

**Secrets.** Implement per §5.6's two classes. `secrets_aws.py` handles Class B
only and must not create a second path to Class A material; Class A remains
exclusively `resampling_null/secrets.py`. `worker_env.py` builds a strict
allowlist so worker environments carry no arm identity, no answer key, no
analysis threshold, and no controller credential.

`journal.py` is the first machine-written resumable forensic journal;
`scripts/research/execution_journal.py` remains the markdown-journal checker and
is not a substitute.

**Blocked on:** Steps 5A, 6, 7A, 8, 9.

**Terminal state:** `implementation_complete`; `external_verification_pending`;
`authority_freeze_pending`; `launch_review_pending`; `execution_pending`.

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_binding.py tests/cloud/test_worker_env.py tests/cloud/test_secrets.py tests/cloud/test_journal.py -q`,
plus `timeout 60s python -m ruff check src/pneuma_lab/cloud`. Behaviors covered:
a forged artifact is rejected; a malicious image swap is rejected; a stale lease
is rejected; a retry does not duplicate a scientific sample; a worker
environment containing an arm token fails closed; no secret of either class
appears in any serialized receipt, log, or argv; the self-arm-blindness wording
gate holds.

---

### Step 11 — Build local and cloud emulation gates

**Files.** New `src/pneuma_lab/cloud/fakes/`, `src/pneuma_lab/cloud/emulation.py`,
`tests/cloud/test_emulation.py`, `tests/cloud/conftest.py`.

**The fake layer must not become an inaccurate home-grown AWS emulator.** Split
the semantics into three explicit tiers, and record which tier every assertion
belongs to:

| tier | what it covers | mechanism | honest limit |
| --- | --- | --- | --- |
| T1 — local behavioral contracts | our own state machine: lease acquire/expire/renew-refusal, shard idempotency, duplicate-delivery collapse, corrupt-output rejection, budget-kill propagation, teardown ordering | hand-written in-memory fakes | proves **our** logic only; proves nothing about AWS |
| T2 — official request/response validation | that the requests we construct are well-formed and the responses we parse are shaped as AWS documents them: Batch `SubmitJob`/`DescribeJobs`, DynamoDB conditional `PutItem`/`GetItem`, S3 `PutObject`, ECR `DescribeImages` | `botocore.stub.Stubber` or equivalent official validation | proves request/response shape and parameter validation; does **not** prove service-side semantics |
| T3 — real semantics | DynamoDB conditional-write contention under concurrency, Batch scheduling and array-job behavior, S3 consistency, IAM denial in practice, real teardown | separately authorized real-account smoke | outside Phase B |

**Dependency decision required.** `botocore`/`boto3` are **not** declared in
`pyproject.toml` and are **not** in `.venv`; they exist only in the ambient
system Python. T2 therefore requires adding `botocore` (at minimum) as a **dev**
dependency, which `CLAUDE.md` gates: "avoid adding heavy dependencies without a
concrete phase that needs them." Step 11 is that concrete phase, so record the
decision explicitly in the decision log rather than adding it silently. If the
dependency is declined, T2 is unavailable and every T2 assertion must be
reported as `external_verification_pending`, not quietly folded into T1.

`tests/cloud/conftest.py` carries an autouse guard forbidding real network
access and real AWS clients, mirroring the existing autouse
`_forbid_canonical_grid_execution` guard in `tests/resampling_null/conftest.py`
(which fails any test starting a probe over 8 cells or a cell over 1,024
datasets).

Reuse `synthetic_environment.py` as the isolated worker substrate.

Fault matrix: interruption, duplicate delivery, corrupt output, expired lease,
budget kill, teardown.

**Boundary.** CPU-only, no cloud calls. The roadmap's "extremely small
existing-capacity cloud job" option is **deferred**; it requires separate
authorization.

**Blocked on:** Steps 8, 9, 10.

**Terminal state:** `implementation_complete` at T1 (and T2 if the dependency is
approved); `external_verification_pending` for all T3 semantics;
`authority_freeze_pending`; `launch_review_pending`; `execution_pending`.

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_emulation.py -q`, plus
`timeout 60s python -m ruff check src/pneuma_lab/cloud`.

---

### Step 12 — Prepare deployment and teardown artifacts

**Files.** New `infra/terraform/environments/*.tfvars`, `infra/README.md`,
`src/pneuma_lab/cloud/preflight.py`, `tests/cloud/test_preflight.py`.

**Teardown design — tags are never destructive authority.** The first draft's
promise that teardown "removes every tagged resource", validated by static tests,
is withdrawn as unsafe. Teardown requires all of:

1. **Ownership manifest.** Deployment writes an explicit manifest of every
   resource it created, with identifiers. Teardown acts on the manifest, not on
   a tag query. Tags are a *cross-check*, never the authority.
2. **Protected-resource exclusions.** An explicit denylist of accounts,
   regions, buckets, and prefixes that teardown may never touch, checked before
   any destructive call.
3. **Dependency ordering.** A fixed teardown order (jobs → queue drain →
   compute environment → instances → volumes/endpoints → registry → buckets
   after artifact-copy receipts), because AWS deletion has hard ordering
   constraints.
4. **Idempotency.** Re-running teardown after partial failure converges and
   never errors on already-absent resources.
5. **Residual-resource enumeration.** After teardown, enumerate and report what
   remains, including anything found by tag that is *not* in the ownership
   manifest — an unexpected residual is a finding, not something to delete.
6. **Account-bound teardown drill.** A later, separately authorized drill
   against a real account. Static tests can validate ordering, idempotency
   logic, exclusion enforcement, and manifest handling; they cannot validate
   that AWS actually deleted anything.

Also: separate environment-specific configuration from immutable scientific
inputs — scientific inputs live in Step 5's manifest, and the tfvars carry only
region, account, and tags.

**Quota preflight** must refuse launch while applied quota is zero, which is the
current real state (§5.10).

**Blocked on:** Steps 6, 9.

**Terminal state:** `implementation_complete` for preflight and teardown logic;
**`external_verification_pending` — no account-bound teardown drill has run**;
`authority_freeze_pending`; `launch_review_pending`; `execution_pending`.

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_preflight.py -q`, plus
`timeout 60s python -m ruff check src/pneuma_lab/cloud`. Behaviors covered:
preflight refuses at applied quota 0; preflight refuses at insufficient quota;
teardown honors the ownership manifest and refuses a tag-only target; the
protected-resource exclusion blocks a denylisted target; teardown is idempotent;
residual enumeration reports unexpected survivors; the dry-run plan is
byte-stable across repeated invocations.

---

### Step 13 — Freeze the pilot protocol

**Files.** New `docs/research/neurips-2026-workshop/41-pilot-protocol.md`,
`schemas/cloud-pilot-protocol.schema.json`, `src/pneuma_lab/cloud/pilot.py`,
`tests/cloud/test_pilot.py`, registry edits per §5.8.

**Step 13 freezes an admission protocol. It does not run a pilot and it never
claims a pilot has passed.** Protocol implementation and later authorized pilot
execution are strictly separate; the latter is roadmap Step 22, in Phase D.

**Bind before any pilot outcome exists:** maximum cost, maximum runtime, maximum
retries, maximum sample count, the **two-rung one-GPU candidate topology ladder** from
§5.2, and the **deterministic selection rule** ("largest candidate that passes
OOM, tool-call, output-parity, and p10 throughput gates"). Bind the human
approval receipt to the exact code, image, manifest, model, benchmark roster,
and ceiling hashes.

**Selection constraints, enforced in code:** the pilot may select only among the
four frozen rungs; it may not invent, substitute, or interpolate a
configuration; and selection may use only the four named gates, never observed
efficacy. Pilot efficacy is labelled and excluded from confirmation, and no
arm-specific pilot effect may select a model, benchmark, endpoint, task,
reserve, sample tier, or analysis.

**Admission criteria** come from the design's Tier-1 gate: FP8 Qwen3.6 on one
L40S at the frozen context and concurrency cap; BF16 on two A100 80 GB with
tensor parallelism two; four concurrent SWE subject replicas and three τ³
replicas plus one simulator; `VLLM_BATCH_INVARIANT=1` byte equality under fixed
request order, concurrency, topology, and per-call seeds; forced interruption
restoring every arm-visible byte at a completed boundary; projected durable
bytes, p99 boundary delta, upload time, object requests, and attached GB-hours
fitting the frozen allowances; the AWS lease-expiry kill drill (**Azure drill
excluded per §5.5 and pending the Step-4 decision**); the exact network path and
all endpoint and NAT charges passing bootstrap and metering; benchmark
containers failing negative probes for IMDS, node credentials, managed identity,
and Docker-socket access; the A10 simulator OOM and throughput gates
(**Azure-dependent, same caveat**); and every storage, network, log, registry,
and API billing dimension having an admission meter whose in-flight worst case
fits the frozen cap.

Measurement discipline to preserve: although each L40S is marketed as 48 GB,
roughly 44 GiB is usable per GPU on G6e, so the OOM receipt measures against
usable device memory, not nominal capacity.

**Blocked on:** Steps 4–12, and `G-ROSTER` for any pilot *authorization* (the
protocol may be frozen while `G-ROSTER` is open; the authorization may not).

**Terminal state:** `implementation_complete`;
`external_verification_pending`; `authority_freeze_pending` cleared only for the
protocol itself; `launch_review_pending`; **`execution_pending` — no pilot has
run**.

**Verification.** One narrow command
`timeout 60s python -m pytest tests/cloud/test_pilot.py -q`, plus
`timeout 60s python -m ruff check src/pneuma_lab/cloud`. Behaviors covered: a
pilot whose sample count, cost, runtime, or retry count exceeds the frozen
protocol is rejected; a rung outside the four frozen candidates is rejected; a
selection input carrying efficacy is rejected; the approval receipt is
invalidated by any bound-hash change; the pilot cannot widen into the expensive
experiment.

---

### Downstream contract — what Task 10 must emit for the paper

Task 10 release preparation must produce a sealed package that
`pneuma_lab.placebo_paper.admit` accepts, or the manuscript cannot render a
single number. The contract is enforced in
`src/pneuma_lab/placebo_paper/package.py`:

- `package_kind` = `resampling_task10_sealed`;
- `lineage` = `canonical_confirmation` — Step 4A, Step 4B, the incomplete P0
  root, synthetic fixtures, and pilots are refused **by name**;
- `sealed` true, and `artifact_root.verified` true with a 64-hex digest;
- `unblind.ceremony_completed` true;
- `authority` = `confirmation_execution_authorized`;
- all nine receipts present: `study_manifest`, `prefix_schedule`,
  `assignment_ledger`, `packet_index`, `blinded_projection`, `analysis_freeze`,
  `unblind_receipt`, `artifact_root`, `power_report`;
- `verdict` from the preregistered taxonomy;
- an emitted `numbers` object whose keys cover `render.PRIMARY_ROWS`,
  `render.RESOLUTION_ROWS`, and `render.ENVIRONMENT_ROWS`.

There is no manual-entry path: the renderer reads emitted keys only, so a key
Task 10 does not emit renders as a visibly unfilled cell. See
`docs/research/placebo-paper/00-result-to-paper-pipeline.md`.

---

## 7. Sequential order with blocking gates

```txt
  [verify Phase A complete]  ← blocking precondition, §2.2
             │
             ▼
            4  ──────────────────────────────────────────┐
             │                                            │ registers G-ROSTER,
             ▼                                            │ Azure decision,
            5A                                            │ ladder + rule
             │                                            │
             ├────────────────► 5B *(authorized)* ─────┐  │
             ▼                                          │  │
            6 ──┬─► 7A ──► 7B *(authorized)* ───────────┤  │
                ├─► 8 ──┐                               │  │
                └─► 9 ──┼─► 10 ──► 11 ──────────────────┤  │
                6, 9 ──► 12 ───────────────────────────┤  │
                                                        ▼  ▼
                                                       13 (protocol freeze)
                                                        │
                                    ══════ G-ROSTER ════╪══════
                                    ══════ 5B done ═════╪══════
                                    ══════ 7B done ═════╪══════
                                                        ▼
                                              14 (hostile review, out of scope)
```

Ordered list:

1. **Verify Phase A completion** (§2.2). Blocking precondition.
2. **Step 4** — design ratification; registers `G-ROSTER`, the Azure decision,
   and the ladder-plus-rule framing.
3. **Step 5A** — input-lock schema, verifier, fixtures, retrieval protocol.
4. **Step 6** — architecture, tier-agnostic, at evidence levels L1/L2.
5. **Steps 7A, 8, 9 in parallel** once Step 6's manifest is frozen. The
   roadmap permits this once shared contracts are frozen.
6. **Step 10** — needs 5A, 6, 7A, 8, 9.
7. **Step 11** — proves 8/9/10 at T1 (T2 subject to the dependency decision).
8. **Step 12** — needs 6 and 9.
9. **Step 13** — pilot *protocol* freeze. May proceed while `G-ROSTER` is open.
10. **Steps 5B and 7B** — separately authorized, may start as soon as their
    static counterparts land, and are jointly planned with the roster
    qualification audit.

**Three hard gates before any launch-readiness claim, pilot authorization, or
final experiment-manifest promotion:**

- **`G-ROSTER`** — the eligibility inequality genuinely satisfied for every
  split, or a registered reviewed protocol amendment.
- **Step 5B complete** — real license, revision, snapshot, contamination, and
  digest receipts exist.
- **Step 7B complete** — real deterministic builds, SBOMs, and immutable image
  digests exist, with repeated-build comparison.

Step 14 follows all of the above and is out of scope here.

---

## 8. Collision risks, ranked

1. **Append-only shared documents** — `15-decision-log.md`,
   `33-execution-journal.md` and its shards, `32-cloud-spend-ledger.md`. Append
   at the end only; never renumber or reorder; compute identifiers at write
   time; validate with `python -m scripts.research.execution_journal check`.
2. **`docs/project-status.json`** — schema-validated with
   `additionalProperties: false` at the root and a const-pinned `evidence`
   object. Add `systems[]` records only; never add a top-level key. Re-run
   `python -m pneuma_lab.status --check` after every edit.
3. **`src/pneuma_lab/resampling_null/cli.py`** — Phase A territory. One-line
   `cloud` subparser wiring only, added when the surrounding step is complete.
4. **`src/pneuma_lab/schemas/__init__.py` and `tests/test_schema_loads.py`** —
   the registry is explicit tuples with count and exact-name assertions
   (`EXPECTED_RESAMPLING_COUNT = 14`, `test_resampling_schema_bucket_registered`).
   A new bucket must update `__all__`, `ALL_SCHEMA_FILES`, `EXPECTED_*_COUNT`,
   and add its own bucket test. An unregistered schema file on disk fails
   nothing — silent invisibility is the failure mode to guard against.
5. **`power.py` and `branch_controller.py`** — wrap, never modify. Any change
   invalidates the Task 8/9 receipts and the Step 4A continuity results.
6. **`src/pneuma_lab/resampling_null/release.py`** — Phase A owned. Do not
   create a file with that name and do not import it.
7. **Test budgets** — `scripts/check_test_budget.py` caps `tests/smoke` at 8 and
   `tests/resampling_null` at 65 test functions, and rejects `skip`, `xfail`,
   and `parametrize` in the smoke suite. Phase B must not inflate either.
8. **New schema `$id` collisions** — the `cloud-` prefix prevents collision with
   `resampling-*` or any Task 10 schema.
9. **Test discovery** — `testpaths = ["tests/smoke"]` keeps `tests/cloud/`
   invisible by default. Correct; do not widen. Invoke narrow paths explicitly
   under `timeout 60s`.

---

## 9. Open items this plan deliberately leaves unresolved

- **`G-ROSTER`.** Both tiers are `FEASIBILITY_NO_GO`; the only remedy is the
  full base-commit, image, isolation, and three-pair qualification audit.
  Blocking for manifest promotion, pilot authorization, and launch readiness.
- **Azure.** Scientifically optional for the primary claim, yet named in an
  unconditional Tier-1 gate item, with $0.00 verified spendable balance and no
  authorization. Step 4 must register an explicit decision; silence blocks
  Tier 1.
- **`botocore` dev dependency** for Step 11 T2 validation. A recorded decision,
  not a silent addition.
- **SBOM tool selection** for Step 7B. Not installed; a recorded decision.
- **`terraform` not installed locally.** Step 6 L1 evidence must skip cleanly
  and record the skip; a skip is not a pass.
- **`00-README.md` routing defect** and the absent
  `26-detectability-audit-design.md`. Repair belongs to Step 4.
- **The roadmap's Step-11 small cloud job.** Deferred; separate authorization.
- **Step 14 hostile launch review.** Out of scope.
- **Step 4B.** Not executed, not authorized, no evidence fabricated or
  pre-staged for it, and no gate of it weakened.

## 2026-08-04 implementation-status addendum

Action-019 is the passed two-L40S qualification closure; action-018 remains a
historical post-launch no-go. The post-qualification Action-020 slice now
contains the real configuration-driven production execution contracts,
provider-neutral durable controller, raw worker evidence validation, ceremony
receipt verifier, and roster-bound C120/C160 power/tier finalization machinery.
These components are `implementation_complete` with official E2E pending. The
qualification lane is therefore no longer a current semantic blocker, but its
receipt still cannot satisfy official P0/Step-4B authority. Fresh scientific
inputs, live ceremony, both tier validations, signed official authorization,
release review, and the separately authorized real workload remain required.

The earlier Phase-A collision note that `power.py` and
`branch_controller.py` are "wrapped, never modified" is historical planning
guidance for the preserved Step 4A lineage, not a current blocker on the
Action-020 roster-bound finalizers. Those finalizers are separately scoped,
schema-validated, and do not rewrite or promote any earlier receipt.
