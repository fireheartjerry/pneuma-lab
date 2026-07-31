# Phase B Steps 4–13 — file-by-file implementation plan

**Status:** planning document; no implementation, freeze, or authorization
**Prepared:** 2026-07-31
**Scope:** Steps 4–13 of
`docs/research/neurips-2026-workshop/36-step4a-to-aws-credit-launch-roadmap.md`
**Prepared while:** Phase A (Task 6/7 continuity reconciliation and Task 10
implementation/release preparation) was executing concurrently on the same
branch.

This document is subordinate to the scientific contract, the controlling plan,
`docs/project-status.json`, the live Tasks 6–10 handoff, the decision log, the
cloud spend ledger, and the append-only execution journal. If any of those
conflict with this plan, stop and reconcile them in the decision log before
execution. It is a plan, not an authority: it freezes nothing, authorizes
nothing, and promotes nothing.

## What this document is not

- It is **not** Step 4. No hypothesis, arm, endpoint, stopping rule, benchmark
  roster, or model choice is frozen here. Step 4 is described, not performed.
- It is **not** Step 14. The pre-experiment hostile launch review remains
  deferred and out of scope.
- It does **not** run, prepare, or make easier any part of Step 4B.
- It records **no** cloud, paid, provider, benchmark, image-build, model-pull,
  or dataset-pull action. None occurred while preparing it.
- It does **not** touch, resume, finalize, analyze, or cite the preserved
  incomplete root
  `build/research/neurips-2026-workshop/p0-lineage-20260730`.
- It promotes nothing past `implementation_complete; E2E_pending`.

---

## 0. Method and evidence basis

The inventory below was produced by reading the repository directly plus three
bounded read-only subprocess inventories:

| subprocess | tool | assignment |
| --- | --- | --- |
| resampling-null core inventory | `codex --yolo exec` | exhaustive symbol-level enumeration of `src/pneuma_lab/resampling_null/` and `tests/resampling_null/` across orchestration, spend/timing, evidence/blinding/security, authority, storage/artifacts, and test-tier conventions |
| cloud/infra inventory | `claude --dangerously-skip-permissions -p` | repository-wide search for container, IaC, CI, SBOM, digest-pinning, budget, and configuration surfaces |
| design/authority inventory | `claude --dangerously-skip-permissions -p` | quoted extraction of the binding scientific design plus every cross-document ambiguity |

No subprocess was permitted to edit a file. Every claim below that names a file,
symbol, or value was checked against the repository at commit `e368a54`.

---

## 1. Live collision surface

`git status --short` at the time of writing, on branch
`codex/neurips-2026-empirical`:

```txt
 M docs/research/neurips-2026-workshop/36-step4a-to-aws-credit-launch-roadmap.md
 M src/pneuma_lab/resampling_null/cli.py
 M tests/resampling_null/provider_authority_fixture.py
 M tests/resampling_null/test_cli.py
?? src/pneuma_lab/resampling_null/release.py
?? tests/resampling_null/test_release.py
```

These are Phase A work in flight. The governing rule for every step below:

> Phase B work must not modify `src/pneuma_lab/resampling_null/cli.py`,
> `tests/resampling_null/test_cli.py`,
> `tests/resampling_null/provider_authority_fixture.py`,
> `src/pneuma_lab/resampling_null/release.py`,
> `tests/resampling_null/test_release.py`,
> `docs/project-status.json`,
> `docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md`,
> `docs/research/neurips-2026-workshop/33-execution-journal.md`,
> `docs/research/neurips-2026-workshop/15-decision-log.md`, or
> `docs/research/neurips-2026-workshop/36-step4a-to-aws-credit-launch-roadmap.md`
> until Phase A has landed and merged.

All new Phase B code therefore lands in a **new package**,
`src/pneuma_lab/cloud/`, carrying **its own CLI module**. The single eventual
touchpoint on a Phase A file is one `top.add_parser("cloud")` line in
`src/pneuma_lab/resampling_null/cli.py`, added last, in a dedicated
reconciliation commit.

---

## 2. Existing surfaces

### 2.1 The scientific contract already freezes most of Step 4

The binding contract is
`docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md` (3,949
lines), with `docs/superpowers/plans/2026-07-28-resampling-null-core.md` as the
controlling plan. The Tasks 6–10 handoff names both at its head, and fixes the
source order `AGENTS.md` → `docs/project-status.json` →
`VPS_NEURIPS_2026_HANDOFF.md` → handoff → plan → design → decision log → spend
ledger → execution journal.

| Roadmap Step-4 item | Already frozen at | Value |
| --- | --- | --- |
| Hypotheses / claim of record | §1, §3.1 | The Resampling Null; the claim is gate-conditional, and a positive point estimate alone is insufficient |
| Arms | §6 | `REAL`, `SHAM`, `NONE`, `RESAMPLE`; a uniform within-task draw assigns `{REAL, SHAM, NO_PACKET, NO_PACKET}` over 12 allocations, then a fair coin labels the two no-packet slots; sealed before any continuation |
| Post-trigger quotas | §6.1 | SWE 32,768 tokens / 32 tool calls / 60 min; τ³ 16,384 / 16 turns / 30 min |
| Endpoints | §8.1 | Objective binary `success`; all allocated blocks remain in ITT; an arm-specific infrastructure or model failure is zero |
| Estimands | §8.2 | Co-primary `Δ_content = Y_R − Y_S` and `Δ_excess = Y_R − no_feedback`; equal SWE/τ³ weighting; raw rows never pooled |
| Decision rule | §9.3 | Seven-condition intersection-union gate |
| Resolution floor | §9.4 | `q0` / `r95`; failure to exceed both `delta_star = 0.05` and `r95` yields `UNRESOLVED_RESAMPLING` |
| Verdict taxonomy | §9.6 | Seven verdicts, all publishable; none authorizes changing endpoints or deleting blocks |
| Power / tier | §9.5 | ≥ 0.80 power, ≤ 0.05 type-I; Clopper–Pearson tails `0.05/729` and `0.05/2187`; `C160` preferred, `C120` minimum; tier selection may not use pilot arm efficacy |
| Failure criteria | §16 | Thirteen stop-or-narrow triggers |
| Admission gates | §7.4, §4.1, §4.2 | Blinded packet-classifier AUROC upper bound below 0.60; eight SWE conditions; ten τ³ conditions |
| Differential-failure gate | §8.1 | `max |f_a − f_a'| ≤ 0.02`; larger imbalance marks the pipeline invalid and never licenses task deletion |
| Benchmark roster | §4.1, §4.2 | `microsoft/SWE-bench-Live@70ec57e8…`, dataset `SWE-bench-Live/MultiLang@608f7ae9…`, `microsoft/RepoLaunch@7735b1e7…`; `sierra-research/tau2-bench` v1.0.1 tag object `b711c1ea…`, peeled commit `fc0055dc…`, MIT |
| Subject model | §4.3 | `Qwen/Qwen3.6-35B-A3B-FP8` revision `95a723d0…`, Apache 2.0, `vllm==0.19.0`, `--reasoning-parser qwen3`, `--tool-call-parser qwen3_coder` |
| Simulator | §4.2 | `Qwen/Qwen3.5-9B` revision `c2022362…`, greedy, separately metered serving subject |
| Sampling | §4.3 | SWE `T=0.6` / top-p 0.95 / top-k 20; τ³ `T=1.0` / top-p 0.95 / top-k 20 / presence 1.5 |
| AWS architecture | §13.1 | Full Batch / ECR / S3 / DynamoDB / VPC / watchdog specification |
| Interruption contract | §13.3 | Checkpoint contents plus an atomic completion marker |
| Spend gate | §15 | Twelve-step pre-action gate and two hard invariants |

Consequence: **Step 4 is a reconciliation and ratification task, not a selection
task**, unless the intent is to change the pinned subject or roster — which
would itself be a registered design change.

### 2.2 The nine conflicts Step 4 must actually resolve

1. **The roadmap treats roster and model as open; the design pins both.** Step 4
   should ratify by reference and record the supersession, not re-decide.
2. **SWE-bench Verified and LiveCodeBench are already rejected alternatives.**
   Decision-log row DL-122 rejects SWE-bench Verified because 500 tasks collapse
   to twelve repository lineages. LiveCodeBench appears only as third-party
   reviewer feedback inside `31-cloud-execution-brief.md`, a file whose own text
   labels Part A "context, not instructions". Neither is an open option.
3. **`00-README.md` routes readers to a different paper.** It describes the
   detectability-audit/clustering study, states "Compute required: none", names
   `26-detectability-audit-design.md` as "The paper. Start here", and never
   mentions the Resampling Null design or routes to `docs/superpowers/specs/`.
   The referenced `26-detectability-audit-design.md` is **absent** from the
   directory. This is the highest-severity documentation defect in scope: a
   reader starting from the README freezes the wrong study.
4. **Both tiers are currently formally infeasible on the SWE side.** The design
   records `C120` as `FEASIBILITY_NO_GO`, not merely fragile, and `C160`
   likewise. Any Step-4 freeze must name the tier it freezes *toward* and
   restate that `eligible_s >= quota_s + 2·pilot_s + fixed_reserve_s` is unmet
   under the current metadata proxy.
5. **τ³ version-string conflict, already adjudicated.** `pyproject.toml`
   declares `1.0.1` while the editable `tau2` entry in the pinned `uv.lock`
   still declares `1.0.0`; the design makes commit, tag object, source blobs,
   lockfile blob, environment image, and installed dependency receipts
   authoritative. Step 4 needs a pointer, not a decision.
6. **Serving topology and context cap are deliberately unfrozen.** The design
   specifies a four-rung L40S→H100 ladder and states that a topology change is a
   subject change. The roadmap's exit gate "no benchmark roster or model choice
   remains ambiguous" therefore **cannot be fully satisfied** for topology until
   the Tier-1 pilot runs. Record an explicit scoped carve-out; do not claim
   closure.
7. **Simulator compute is conditional.** The `g6e.12xlarge` schedule reserves one
   L40S for the 9B simulator during τ³ work; if that node is not eligible or
   available, the BF16 replication is SWE-only, and simulator compute is never
   treated as free.
8. **Stale model rows in the decision log.** DL-01 and the deferred-decisions
   block still name Qwen2.5-Coder-7B as the primary family; DL-79 and DL-82
   select `qwen2.5-coder:7b`. These belong to the retired placebo/gauge lineage
   and are not marked superseded by DL-122. They read as a live conflict.
9. **The design's own calendar is stale.** §17 allocates "Aug 7–8 | freeze
   dependencies, preregistration, task roster, analysis hash", while the roadmap
   still has Task 10, Steps B6–B14, and Step 4B ahead of that point.

Registration surfaces for any Step-4 output:

| surface | path | role |
| --- | --- | --- |
| Scientific contract | `docs/superpowers/specs/2026-07-28-neurips-resampling-null-design.md` | the frozen design; hashed as `design_sha256` in later decision rows |
| Controlling plan | `docs/superpowers/plans/2026-07-28-resampling-null-core.md` | hashed as `plan_sha256` |
| Decision log (append-only) | `docs/research/neurips-2026-workshop/15-decision-log.md` | next free identifier is **DL-148**; supersession is explicit |
| Machine-readable status | `docs/project-status.json` | validated by `python -m pneuma_lab.status --check` |
| Live handoff | `docs/research/neurips-2026-workshop/34-tasks-6-10-vps-handoff.md` | listed in `authoritative_docs` |
| Execution journal (append-only, sharded) | `docs/research/neurips-2026-workshop/33-execution-journal.md` plus `execution-journal/` and its `manifest.json` | published event content is never silently edited, reordered, or renumbered |
| Spend ledger | `docs/research/neurips-2026-workshop/32-cloud-spend-ledger.md` | `CL-0xx` rows |
| Repo-root handoff | `VPS_NEURIPS_2026_HANDOFF.md` | position 3 in the source order |
| Roadmap (subordinate) | `docs/research/neurips-2026-workshop/36-step4a-to-aws-credit-launch-roadmap.md` | explicitly does not replace the authorities above |

There is no schema for a design change as such. The only two authorization
schemas that exist — `schemas/foundation-training-authorization.schema.json` and
`schemas/estimator-training-authorization.schema.json` — govern training, which
the roadmap places outside scope ("Run the controlled inference evaluation, not
unplanned model training").

### 2.3 §13 of the design is already the exact AWS architecture

Step 6 is transcription into reviewable infrastructure code, not architecture
design. The design fixes, among other things:

- region `us-east-1`;
- an AWS Batch managed EC2 compute environment, `minvCpus = 0`, a custom GPU AMI
  pinned by AMI ID plus root-snapshot ID plus a bootstrap SHA-256, one-instance
  maximum, one whole-instance job per node; the On-Demand environment pins
  `instanceTypes=[g6e.12xlarge]`, `maxVCpus=48`, `allocationStrategy=BEST_FIT`,
  with exactly one runnable controller job requesting 48 vCPUs, all four GPUs,
  and allocatable memory;
- four TP1 subject replicas for SWE, or three plus one frozen Qwen3.5-9B
  simulator replica for τ³ — a concurrency assumption that is invalid unless the
  Tier-1 gate passes;
- host Docker exposed only to the privileged controller, with instance-store
  devices enumerated, formatted, and mounted as Docker's data root;
- benchmark containers that receive neither the Docker socket nor cloud
  credentials, whose network namespaces block IMDS;
- a minimal per-run controller role restricted to its content-addressed storage
  prefix plus consistent `GetItem` on the exact run lease key and table — and
  which **cannot renew the lease**;
- ECR for digest-pinned controller, model-server, simulator, and harness images;
- one-AZ private networking with an action-manifested endpoint set (ECR API, ECR
  DKR, S3, DynamoDB lease reads, ECS control/agent/telemetry, CloudWatch Logs,
  and whichever of STS/EC2 the measured bootstrap requires), with endpoint hourly
  and data-processing charges as explicit meters;
- S3 Standard with a manifest-bound lifecycle-policy identifier, absolute
  deletion date, and abort-incomplete-multipart rule;
- CloudWatch Logs with fixed retention;
- AWS Budgets alarms plus a controller-enforced multi-resource watchdog; and
- an **independently deployed** EventBridge Scheduler plus Lambda stop path with
  a DynamoDB lease and a minimal termination role, holding a separate
  write/termination identity from the controller.

Rates recorded for planning: `g6e.12xlarge` at `$10.49264`/hour On-Demand; S3
Standard `$0.023`/GB-month; gp3 `$0.08`/GiB-month. The historical Spot
observation of `$4.467`/hour is explicitly **non-authoritative** because its
availability zone, UTC query response, product description, and digest were not
retained. Confirmation is On-Demand; Spot is eligible only for a Tier-3
expansion after the forced-interruption gate passes and a fresh AZ-specific
`DescribeSpotPriceHistory` response is sealed.

### 2.4 Reusable code — do not rebuild these

| Concern | Existing surface | What it already guarantees |
| --- | --- | --- |
| Content-addressed records, schema validation | `resampling_null/artifacts.py`: `validate_record`, `load_record`, `write_record`, `write_jsonl_artifact`, `validate_scientific_graph`, `validate_preunblind_graph`, `seal_artifact_root`, `verify_artifact_root` | registered-schema validation, atomic no-overwrite writes, ancestry and closure checks, root receipts that hash the complete closure |
| Root-confined reads | `resampling_null/authority_refs.py`: `AuthorityRefReader.read_bound/read_bytes/decode_json/verify_closure`, `decode_artifact_ref`, `walk_artifact_refs` | descriptor-bound reads confined to the run root, mandatory digest and length verification, strict JSON decoding, authority-closure validation |
| Strict JSON | `resampling_null/json_io.py`: `plain_json`, `load_json_bytes`, `run_root`, `resolve_inside` | duplicate-key and non-finite-constant rejection, confined path resolution |
| Publication transactions | `publication.py` (`BoundPublication.publish_bytes/commit`, rollback on exit), `publication_quarantine.py` (`quarantine_source`, `restore_bound_source`, `recheck_quarantine`), `publication_rollback.py` (`rollback_publication`, `rename_no_replace`), `task6_state.py` (`begin_paired_publication`, `recover_paired_publication`, `prepare_paired_publication_entry`, `install_paired_publication_entry`) | namespace lease, no-overwrite atomic publish, identity checks, quarantine and rollback on failure, recoverable all-or-none two-file commit |
| Deterministic shard allocation | `power.py`: `simulate_power_shard`, `_assert_power_write_open`, `_complete_shards`, `select_validation_cells` | contiguous immutable cell ranges per `shard_index`, rejection of out-of-topology indices and duplicate `(stage, phase, generation, shard_index)` identities, complete-shard-set requirement before any authority merge |
| Interruption and rerun semantics | `branch_controller.py`: `prepare_opaque_work_orders`, `seal_unscored_attempt`, `authorize_full_block_rerun`, `finalize_failed_second_attempt`, `seal_task_block` | four fixed ordered opaque slot work orders; exactly one byte-identical full-block rerun for a validated pre-endpoint outage; conservative infrastructure-failure outcomes without grading; duplicate-receipt and complete-attempt-replay prevention |
| Prefix sealing | `prefix_index.py`: `seal_prefix_index`, `_rollback_owned_publication`, `_seal_transaction_outcome` | unique candidate refs, process reservation plus root transaction, fresh candidate reconstruction, rollback and recovery |
| Timing cap and no-go | `power.py`: `PowerGridSpec.max_projected_wall_seconds` (registered loader requires `43200`), `screen_power_grid`, `_projected_screen_wall_seconds`, `_production_timing_probe`, `_validate_screen_timing_admission`; `timing_no_go.py`: `TimingNoGoBindings`, `create_timing_no_go`, `verify_timing_no_go` | authority-bound all-cell timing probe; rejection of a screen whose projected total work exceeds the frozen twelve-hour cap, with no parallelism discount; exclusive host- and artifact-bound no-go record that rejects forbidden descendants |
| Provider, meter, parser pinning | `provider_contracts.py`: `ValidatedTaskLane`, `ValidatedLane`, `ValidatedProviderPlan`, `validate_provider_lane_plan`; `provider_contract_assets.py`: `decode_contract_ref`, `_verify_ref_closure`, `_verify_registered_authority_graph`, `_validate_source_revisions`, `validate_call_contract`, `validate_parser_contract`, `validate_meter_contract`, `validate_task_contract` | closed per-lane provider plan with `prefix_caps`, `branch_caps`, `simulator_caps`, subject/simulator/tool-parser/meter contract refs, and cap decoders over `generated_tokens`, `model_calls`, `tool_calls`, `wall_clock_ms` |
| Capability isolation | `packet_capabilities.py`: `resolve_packet_capabilities`, `OpaqueSlotGrant`, `TaskPacketCapabilities`, `SealedSlotCapability`, `seal_slot_capability`, `SlotArtifactLoader` | four preregistered-order opaque grants whose worker-visible packet names are a pure function of `(task_id, allocation capability digest)`; a role allowlist containing no scientific record kind; descriptor-bound `O_NOFOLLOW` walks with mandatory digest verification |
| Secret custody | `secrets.py`: `AssignmentSecretStore`, `AssignmentSecretHandle`, `UnblindSecretHandle` | store-minted, non-copyable, purpose-bound single-use handles consumed from a validated secret path; never placed in argv or environment |
| Blinding and unblinding | `freeze.py` (`snapshot_sources`, `freeze_analysis`, `verify_analysis_freeze`, `verify_frozen_analysis_inputs`), `blinding.py` (`seal_blinded_projection`, `issue_unblind_permit`, `unblind_and_publish_analysis`) | named-source freeze binding each name to an exact immutable `ArtifactRef`; HMAC permit bound to manifest, schedule, prefix, ledger, projection, and freeze; clear rows held only in memory; durable one-way taint installed before any clear-ledger parse |
| Execution authority | `execution_authority.py`: `PrefixExecutionAuthority`, `load_prefix_execution_authority`; `power.py`: `SyntheticPowerAuthority`, `ImplementationVerificationPowerAuthority`, `RosterBoundPowerAuthority`, `load_power_authority`, `load_power_config` | projection of a selected task's execution authority from manifest, schedule, and registry; strict separation of synthetic, implementation-verification, and roster-bound authority kinds |
| Canonical import and preflight | `preflight.py`: `import_closed_json`, `import_task_registry`, `import_assignment_program`, `verify_ed25519_canonical_json`, `_publish_cas`, `ConfirmationPreflightRegistry` | canonical signed JSON import, content-addressed publication, closed task and assignment grammars |
| Local isolation substrate | `synthetic_environment.py` (2,078 lines): `SyntheticEnvironmentFactory`, `SyntheticEnvironmentHandle`, `ControllerEnvironmentIPC` (1 MiB frame cap, 2.0 s timeout), `_assert_pairwise_isolated`, fd-scoped `_open_root`/`_open_workspace` | isolated worker execution under `prefix-environments` with proven pairwise isolation and bounded controller IPC |
| Digest and snapshot receipts | `foundation/artifacts.py`: `sha256_file`, `canonical_json_bytes`, `write_atomic_bytes/json/jsonl`, `bind_artifact_publication`, `read_bound_artifact_set`; `foundation/snapshot_receipt.py`: `verify_pinned_snapshot`, `SnapshotFile`, `SnapshotInventoryEntry`; `foundation/model_cache.py`: `pinned_snapshot_path`, `prepare_pinned_snapshot`, `verify_pinned_snapshot` | per-file SHA-256 model-snapshot receipts, symlink and reparse rejection, TOCTOU inventory re-check, canonical-JSON binding, alias protection for protected data roots |
| Lockfile pinning | `foundation/environment.py`: `setup_plan`, `verify_lock` with `UV_VERSION`, `PYTHON_SERIES`, exact `TRANSFORMERS_COMMIT`, registry-source enforcement, `MAX_LOCK_BYTES` | rejection of unpinned or non-registry dependency edges |
| Cloud quote and authorization *pattern* | `foundation/budget.py`: `BudgetState`, `ItemizedCloudQuote`, `CloudQuote`, `CloudAuthorization`, `ReproductionQuoteAuthorization`, `authorize_reproduction_quote`, `authorize_optional_cloud_job`, `record_cloud_job`; `foundation/cloud_bundle.py`: `CloudBundleRequest`, `conservative_cloud_quote`, `build_bundle_manifest`, `write_reproducible_tar`, `build_cloud_bundle` | a reusable *shape* only. Its `MAX_LIFETIME_CLOUD_USD = 45.0` and `MAX_PREPAID_CREDIT_USD = 38.0` are foundation-training-scoped and are **not** this study's caps |
| Resource watchdog *pattern* | `foundation/resources.py`: `ResourceSample`, `ResourceDecision`, `ResourceGuard`, `GUARD_REASONS`, `ACTION_CONTINUE/PAUSE/FAIL`; `foundation/telemetry.py`: `LiveResourceSampler`, `read_nvidia_smi`, `aggregate_telemetry` | pause/fail decisions derived from samples, with an enumerated closed reason set |

### 2.5 Confirmed absences — this is the actual Phase B build

Verified by repository-wide search excluding `.git` and `.venv`:

- **No** `Dockerfile`, `Containerfile`, `docker-compose*`, `*.tf`, `*.tfvars`,
  `*cloudformation*`, or `cdk.json` anywhere.
- **No** `.github/` directory and **no** tracked `*.yml` or `*.yaml` file.
- **No** SBOM in any format (no SPDX, no CycloneDX).
- **No** `boto3` or any AWS SDK dependency or code path in `src/`.
- **No** dollar-denominated spend enforcement for this study, **no** runtime
  watchdog process, and **no** lease or idempotency store. `storage.py`'s
  `LocalTestStorageLease` and `claim_local_test_storage` are explicitly
  local-test, not a production lease.
- **No** license, contamination, OCI-digest, or dataset-revision field anywhere
  in the `resampling-*` schema family. The only `provenance` definition is
  `{design_sha256, code_sha256}`.
- **No** forensic-journal implementation. The journal exists as prose plus
  `execution-journal/manifest.json`; no `forensic`-marked test exists under
  `tests/resampling_null/`.
- `configs/` contains exactly one file, `configs/g1.json`, which pins the G1
  gauge-card design against a local Ollama host and has no cloud content.

Everything cloud-side currently exists as ledger prose plus reusable primitives.

### 2.6 Funding and quota reality

From the spend ledger: verified eligible AWS balance **$10,000.00** (YC Activate,
active through 2028-07-31, EC2 explicitly in the applicable-products list). The
separate $100 Free Tier credit (through 2027-07-27) is **conservatively
excluded**. Azure, OpenAI, and Anthropic verified spendable balances are
**$0.00**. Settled economic cost, active reservations, and cash charged are all
**$0.00**.

Cumulative kill caps recorded at CL-004: **$500**, then **$5,100** for `C120` or
**$6,400** for `C160`, then **$14,900** / **$16,200** after the respective
eligible expansion.

Quota, CL-013, **pending**: `us-east-1` On-Demand and Spot G/VT support cases
`178540521600334` and `178540523000045`, amended in writing to 48 vCPUs with a
one-instance maximum. **Applied quotas remain 0.** A requested quota is not an
applied quota, and credits do not bypass quotas or spend gates.

---

## 3. Proposed layout

One new package, deliberately disjoint from every file Phase A is editing.

```txt
src/pneuma_lab/cloud/
    __init__.py          lazy re-exports only, to avoid an import cycle
    errors.py            CloudContractError hierarchy
    manifests.py         Step 5   immutable candidate experiment manifests
    inputs.py            Step 5   retrieval planning and hash verification
    architecture.py      Step 6   typed AWS resource model, pure data
    images.py            Step 7   image digest and SBOM binding
    orchestration.py     Step 8   submit / lease / resume / cancel state machine
    shards.py            Step 8   deterministic shard allocation wrapper
    reconcile.py         Step 8   terminal-state reconciliation
    spend.py             Step 9   ceilings and the two section-15 invariants
    watchdog.py          Step 9   runtime meter and automatic termination
    projection.py        Step 9   GPU-hour and dollar projection
    approval.py          Step 9   hash-bound human approval receipt
    binding.py           Step 10  result to code/image/model/dataset/authority
    receipts.py          Step 10  stdout, metrics, environment, timing, failure
    worker_env.py        Step 10  allowlisted worker environment builder
    secrets_aws.py       Step 10  AWS-managed secret resolution
    journal.py           Step 10  resumable forensic journal
    fakes/               Step 11  mocked Batch, S3, DynamoDB, ECR, Budgets
    emulation.py         Step 11  fault-injection harness
    preflight.py         Step 12  quota and capacity refusal gate
    pilot.py             Step 13  frozen pilot protocol and ceilings
    cli.py               own parser; wired into resampling_null/cli.py LAST

infra/
    terraform/
        versions.tf variables.tf outputs.tf main.tf
        batch.tf ecr.tf s3.tf dynamodb.tf iam.tf vpc.tf logging.tf
        budgets.tf watchdog.tf
        environments/us-east-1.tfvars
    docker/
        controller/Dockerfile
        model-server/Dockerfile
        benchmark-worker/Dockerfile
        *.lock                pinned base-image digests
    README.md                 deploy, validate, and teardown commands

schemas/
    cloud-experiment-manifest.schema.json      Step 5
    cloud-input-lock.schema.json               Step 5
    cloud-architecture-manifest.schema.json    Step 6
    cloud-image-manifest.schema.json           Step 7
    cloud-job-lease.schema.json                Step 8
    cloud-spend-authorization.schema.json      Step 9
    cloud-approval-receipt.schema.json         Step 9
    cloud-result-binding.schema.json           Step 10
    cloud-pilot-protocol.schema.json           Step 13

tests/cloud/
    conftest.py            autouse guard: forbid real network and real boto3
    test_manifests.py test_inputs.py test_architecture.py test_images.py
    test_orchestration.py test_shards.py test_reconcile.py
    test_spend.py test_watchdog.py test_projection.py test_approval.py
    test_binding.py test_worker_env.py test_secrets.py test_journal.py
    test_emulation.py test_preflight.py test_pilot.py test_iac_plan.py

docs/research/neurips-2026-workshop/
    38-experiment-design-freeze.md    Step 4 output
    39-external-input-lock.md         Step 5 output
    40-aws-architecture.md            Step 6 output
    41-pilot-protocol.md              Step 13 output
```

Every new schema follows the existing `resampling-*` conventions verbatim: the
shared `artifact_ref` definition with its anti-traversal `relative_path` regex
(no absolute path, drive letter, backslash, or `..`), `sha256` matching
`^[0-9a-f]{64}$`, strict `Z`-suffixed `frozen_timestamp`, `provenance` requiring
`design_sha256` and `code_sha256`, `additionalProperties: false` throughout,
Draft 2020-12, 4-space indentation, no BOM, no comments, and an
`x-pneuma-schema-kind` plus `x-pneuma-version` of `0.1.0`. The `cloud-` prefix
guarantees no `$id` collision with the `resampling-*` family or with any schema
Phase A may add.

---

## 4. Step-by-step plan

### Step 4 — Freeze the real experiment design

**Character:** documentation and authority records only. No source change.

**Files.** New `docs/research/neurips-2026-workshop/38-experiment-design-freeze.md`.
Appends to `15-decision-log.md` starting at **DL-148**. One execution-journal
event. Possible repair of `00-README.md`.

**Work.** Ratify by reference the hypotheses, arms, endpoints, stopping rules,
failure criteria, and admission gates already frozen in the design. Then resolve
each of the nine conflicts in §2.2 — in particular: record SWE-bench-Live
MultiLang plus τ³ as the closed roster and LiveCodeBench and SWE-bench Verified
as rejected, citing DL-122; mark DL-01, DL-79, and DL-82 superseded by DL-122;
repair or explicitly deprecate `00-README.md`'s routing and its dangling
`26-detectability-audit-design.md` reference; declare the target tier and restate
the current `FEASIBILITY_NO_GO`; and record the serving-topology and context-cap
carve-out as an open item that the Tier-1 pilot resolves.

**Blocked on:** nothing. This is the first step and everything downstream keys
off it.

**Collision risk.** The decision log and execution journal are append-only shared
surfaces that Phase A is also writing. Append at the end only; never renumber or
reorder; reconcile deliberately after the branches merge. Defer any
`docs/project-status.json` edit to the reconciliation commit.

**Verification.** No focused tests apply. If `project-status.json` is eventually
touched, `python -m pneuma_lab.status --check` must pass.

**Exit-gate caveat.** The roadmap's "no benchmark roster or model choice remains
ambiguous" cannot be fully satisfied: serving topology and context cap are
contractually pilot-determined, and the design states that a topology change is a
subject change. Record the carve-out; do not claim closure.

---

### Step 5 — Lock external inputs

**Files.** New `schemas/cloud-input-lock.schema.json`,
`schemas/cloud-experiment-manifest.schema.json`,
`src/pneuma_lab/cloud/{errors,manifests,inputs}.py`,
`tests/cloud/{test_manifests,test_inputs}.py`, and
`docs/research/neurips-2026-workshop/39-external-input-lock.md`.

**Why a new schema is unavoidable.** Confirmed gap: no `resampling-*` schema has
a license, contamination, OCI-digest, or dataset-revision field. The design's
Step-5 obligations — a base-commit license audit, immutable
`linux/amd64@sha256:` manifest/config/layer sets mirrored provider-locally,
bounded contamination disclosure through public-artifact and lineage/date
sensitivities rather than a fictional cutoff, and binding of the complete row
hash, base commit and tree, issue and PR identifiers, date, image digests,
parser/command/F2P/P2P digests, and license evidence — presently have nowhere
typed to land except the untyped `eligibility_manifest_ref` and
`source_revision_refs` slots in `resampling-study-manifest.schema.json`.

`cloud-input-lock` should carry: `model_pins[]` (repository, revision, license,
per-file snapshot receipt ref), `tokenizer_pin`, `benchmark_pins[]` (repository,
commit, dataset revision, license, task-manifest digest), `container_bases[]`
(registry plus `linux/amd64@sha256:` digest), `verifier_sources[]`,
`contamination_receipts[]`, and `license_receipts[]`.

**Reuse.** `foundation/snapshot_receipt.py` and `foundation/model_cache.py` for
the model receipt shape; `foundation/environment.py::verify_lock` for lockfile
pinning; `resampling_null/artifacts.py` plus `authority_refs.py` for writing and
verification; `provider_contract_assets.py::_validate_source_revisions` as the
existing precedent for revision binding.

**Blocked on:** Step 4.
**Collision risk:** none — all new files.

**Focused tests.** Manifest round-trip validity. A mutable tag (`:latest`, a
branch name, an unpinned revision) is rejected. A digest mismatch fails closed. A
missing license receipt fails closed. The retrieval plan resolves offline from
digests alone, with no network and no mutable-tag lookup.

**Zero-cost boundary.** Implement *verification of* pins. Do not pull models,
datasets, or images. The retrieval path is exercised against local fixtures only.

---

### Step 6 — Create the AWS architecture

**Files.** New `infra/terraform/*` (plan-only),
`schemas/cloud-architecture-manifest.schema.json`,
`src/pneuma_lab/cloud/architecture.py`,
`tests/cloud/{test_architecture,test_iac_plan}.py`, and
`docs/research/neurips-2026-workshop/40-aws-architecture.md`.

**Character.** Transcription of design §13.1 (see §2.3 above) into reviewable
code. `architecture.py` holds the typed model and emits the architecture
manifest; the Terraform consumes the same values so drift between the two is
detectable rather than silent.

**Blocked on:** Step 5 — image and input names determine the ECR repositories and
S3 namespaces.
**Collision risk:** none.

**Focused tests.** Manifest-to-`.tf`-variable parity. The IAM policy denies
anything outside the run's content-addressed S3 prefix and the exact DynamoDB
lease key and table. The controller role has no lease-renew action. The watcher
identity is distinct from the controller identity. `terraform validate` runs, in
a test that skips cleanly when the binary is absent; **no** `terraform plan`
against a real account and **no** `apply`.

**Exit-gate note.** The plan must be reviewable without provisioning GPU
capacity, which is satisfied because no apply and no credentialed plan occurs.

---

### Step 7 — Build deterministic containers

**Files.** New `infra/docker/{controller,model-server,benchmark-worker}/Dockerfile`
plus `*.lock`, `schemas/cloud-image-manifest.schema.json`,
`src/pneuma_lab/cloud/images.py`, `tests/cloud/test_images.py`.

**Character.** Three separate images, as the design requires. Benchmark workers
receive neither the Docker socket nor cloud credentials, and their network
namespaces block IMDS. Base images are pinned by digest; `vllm==0.19.0` and the
CUDA, driver, and PyTorch stack are pinned. Each build emits an SBOM and an image
digest into `cloud-image-manifest`, and `images.py` proves the
result-to-image binding consumed by Step 10.

**Blocked on:** Steps 5 and 6.
**Collision risk:** none.

**Focused tests.** Every `FROM` carries an `@sha256:` digest. No unpinned
`pip install` line exists. The manifest digest binding verifies and fails closed
under substitution. An SBOM is present and non-empty.

**Boundary.** Do **not** build images in this phase. Parse and verify only; a
real build is a separate later action requiring its own authorization.

---

### Step 8 — Implement orchestration and interruption safety

**Files.** New `src/pneuma_lab/cloud/{orchestration,shards,reconcile}.py`,
`schemas/cloud-job-lease.schema.json`, and
`tests/cloud/{test_orchestration,test_shards,test_reconcile}.py`.

**Character.** Reuse aggressively. `power.py::simulate_power_shard` already
provides deterministic contiguous shard allocation with duplicate-identity
rejection; `branch_controller.py` already provides the exactly-one
byte-identical rerun and failed-second-attempt semantics; `publication.py` and
`task6_state.py` already provide idempotent, recoverable publication. Step 8 is
therefore a **DynamoDB-backed lease layer plus a submit/cancel/reconcile state
machine over those existing primitives**, not a second results model.

Retry classification consumes the frozen protocol from design §13.3: restore must
match the prior boundary receipt before the next model call, and any mismatch
invalidates the entire four-arm task block — one failed arm is never silently
replaced.

**Blocked on:** Step 6 (the lease table shape).
**Collision risk:** none, **provided** `power.py` and `branch_controller.py` are
wrapped and not modified. Modifying either would invalidate the Task 8 and Task 9
receipts and the Step 4A continuity results.

**Focused tests.** A synthetic interruption mid-shard yields exactly one valid
terminal history. Duplicate delivery of the same assignment produces exactly one
scientific sample. An expired lease fails closed. Conditional-write contention
resolves to a single winner.

---

### Step 9 — Implement spend protection

**Files.** New `src/pneuma_lab/cloud/{spend,watchdog,projection,approval}.py`,
`schemas/cloud-spend-authorization.schema.json`,
`schemas/cloud-approval-receipt.schema.json`, and
`tests/cloud/{test_spend,test_watchdog,test_projection,test_approval}.py`.

**Character.** Implement design §15 literally — the twelve-step pre-action gate
and both invariants:

```txt
provider_settled + provider_active_reservations + proposed_provider_reservation
    <= verified_eligible_provider_balance

project_settled + project_active_reservations + proposed_reservation
    <= applicable_cumulative_tier_stop
```

with the ledger's cumulative kill caps and the verified eligible AWS balance from
§2.6. All invariant terms use the frozen conservative USD-equivalent conversion,
and any tax, fee, or FX exposure not covered by credits enters both the worst-case
reservation and an explicit cash-liability field.

Two design constraints must be encoded as hard behavior, not documentation:

- **AWS Budgets alarms are advisory only.** The design is explicit that budget
  alerts do not enforce a stop and never substitute for the independent
  lease-based watcher plus teardown verification.
- **Silent fallback is forbidden.** A Spot eviction, capacity substitution,
  tensor-parallel or context change, extra retry, added node, or provider
  substitution is not an implicit retry unless its exact behavior was already
  frozen; otherwise it requires a newly priced, hashed, and approved action.

**Reuse.** Copy the *pattern* of `foundation/budget.py`'s
`CloudQuote`/`CloudAuthorization` and `foundation/resources.py`'s `ResourceGuard`
decision model. Do not import those modules: their caps are foundation-training
scoped and would be wrong here.

**Blocked on:** Steps 6 and 7 — rates are keyed to instance type and image.
**Collision risk:** none.

**Focused tests.** Each invariant fails closed exactly at its boundary. The
reservation is appended before resource creation. An unreserved settlement is
rejected. The approval receipt is bound to exact manifest hashes, so a one-byte
manifest change invalidates it. The watchdog terminates on a projection overrun.
No fresh watchdog lease means no new model or API call.

---

### Step 10 — Implement evidence, blinding, and security controls

**Files.** New
`src/pneuma_lab/cloud/{binding,receipts,worker_env,secrets_aws,journal}.py`,
`schemas/cloud-result-binding.schema.json`, and
`tests/cloud/{test_binding,test_worker_env,test_secrets,test_journal}.py`.

**Character.** Extend the existing blinding model across the cloud boundary.

**Read `packet_capabilities.py`'s module docstring before extending it.** The
registered property is **peer-slot and donor opacity, not self-arm opacity** — a
packet-bearing worker reads its own packet text because that text is the
intervention, and the REAL/SHAM contrast is protected by token-parity machinery
instead. No cloud artifact may restate the stronger claim.

`worker_env.py` builds a strict allowlist so worker environments carry no arm
identity, no answer key, no analysis threshold, and no controller credential.
`secrets_aws.py` resolves secrets only through AWS-managed mechanisms — never
Git, never image layers, never argv or environment — mirroring `secrets.py`'s
non-copyable purpose-bound handle design. `journal.py` is the first
*implementation* of the resumable forensic journal, which today exists only as
prose plus `execution-journal/manifest.json`.

**Blocked on:** Steps 5 through 9.
**Collision risk:** none.

**Focused tests.** A forged artifact is rejected. A malicious image swap is
rejected. A stale lease is rejected. A retry does not duplicate a scientific
sample. A worker environment containing an arm token fails closed. A secret never
appears in any serialized receipt. A role-boundary violation fails closed.

---

### Step 11 — Build local and cloud emulation gates

**Files.** New `src/pneuma_lab/cloud/fakes/` (Batch, S3, DynamoDB, ECR, Budgets),
`src/pneuma_lab/cloud/emulation.py`, `tests/cloud/test_emulation.py`, and
`tests/cloud/conftest.py`.

**Character.** `tests/cloud/conftest.py` carries an autouse guard forbidding real
network access and real boto3 clients, mirroring the existing autouse
`_forbid_canonical_grid_execution` guard in `tests/resampling_null/conftest.py`
that fails any test starting a probe over 8 cells or a cell over 1,024 datasets.

Reuse `synthetic_environment.py` as the isolated worker substrate rather than
writing a second isolation layer.

Fault matrix to exercise: interruption, duplicate delivery, corrupt output,
expired lease, budget kill, and teardown.

**Blocked on:** Steps 8 through 10.
**Collision risk:** none.

**Boundary.** CPU-only, with no cloud calls. The roadmap's "extremely small
existing-capacity cloud job" option is **deferred**: it requires separate
authorization and is outside this plan.

---

### Step 12 — Prepare deployment and teardown artifacts

**Files.** New `infra/terraform/environments/*.tfvars`, `infra/README.md`,
`src/pneuma_lab/cloud/preflight.py`, `tests/cloud/test_preflight.py`.

**Character.** Separate environment-specific configuration from immutable
scientific inputs: the scientific inputs live in Step 5's manifest, and the
tfvars carry only region, account, and tags. Provide reproducible deployment,
validation, and teardown commands.

The quota preflight must **refuse launch while applied quota is zero** — which is
the actual current state (§2.6: both support cases pending, applied quota 0).

**Blocked on:** Steps 6 and 9.
**Collision risk:** none.

**Focused tests.** Preflight refuses at applied quota 0. Preflight refuses at
insufficient quota. The teardown plan removes every tagged resource. The dry-run
plan is byte-stable across repeated invocations.

---

### Step 13 — Freeze the pilot protocol

**Files.** New `docs/research/neurips-2026-workshop/41-pilot-protocol.md`,
`schemas/cloud-pilot-protocol.schema.json`, `src/pneuma_lab/cloud/pilot.py`,
`tests/cloud/test_pilot.py`.

**Character.** Encode the design's Tier-1 gate as the pilot's pass/fail criteria.
Its thirteen numbered conditions are the natural content: FP8 Qwen3.6 serving on
one L40S at the frozen context and concurrency cap; BF16 on two A100 80 GB with
tensor parallelism two; four concurrent SWE subject replicas and three τ³
replicas plus one simulator; frozen vLLM deterministic and batch-invariant mode
passing byte equality; forced interruption restoring every arm-visible byte at a
completed boundary; projected durable bytes, p99 boundary delta, upload time,
object requests, and attached GB-hours fitting the frozen allowances; independent
AWS and Azure lease-expiry kill drills removing every tagged resource without
relying on the study controller; the exact private/public network path and all
endpoint and NAT charges passing bootstrap and metering; benchmark containers
failing negative probes for IMDS, node credentials, managed identity, and
Docker-socket access; the A10 simulator passing realistic-context OOM and
throughput gates; and every storage, network, log, registry, and API billing
dimension having an admission meter whose in-flight worst case fits the frozen
cap.

Note the design's measurement discipline: although each L40S is marketed as
48 GB, roughly 44 GiB is usable per GPU on G6e, so the OOM receipt measures
against usable device memory, not nominal capacity.

Bind maximum cost, runtime, retries, and sample count. Bind the human approval
receipt to the exact code, image, manifest, model, benchmark roster, and ceiling
hashes. Pilot efficacy is labelled and excluded from confirmation, and no
arm-specific pilot effect may select a model, benchmark, endpoint, task, reserve,
sample tier, or analysis.

**Blocked on:** Steps 4 through 12.
**Collision risk:** none.

**Focused tests.** A pilot whose sample count or ceiling exceeds the frozen
protocol is rejected. The approval receipt is invalidated by any bound-hash
change. The pilot cannot widen into the expensive experiment.

---

## 5. Optimal sequential order

```txt
4 ──► 5 ──► 6 ──┬─► 7 ──┐
                ├─► 8 ──┼─► 10 ──► 11 ──► 13
                └─► 9 ──┘
                6, 9 ──► 12 ──────────────►┘
```

1. **Step 4** — documentation and authority records. Unblocks everything; the
   conflicts must be resolved before any manifest is written.
2. **Step 5** — the input lock, whose schema every later manifest references.
3. **Step 6** — the architecture, which names the ECR, S3, and DynamoDB surfaces
   that Steps 7 through 9 bind to.
4. **Steps 7, 8, and 9 in parallel** once Step 6's manifest is frozen. The
   roadmap's own parallel-work rule permits exactly this: AWS architecture,
   containers, orchestration, spend controls, and emulation may proceed in
   parallel once their shared contracts are frozen.
5. **Step 10** — needs all three of the above to bind results to.
6. **Step 11** — proves Steps 8 through 10 without consuming credit.
7. **Step 12** — needs Steps 6 and 9.
8. **Step 13** — needs everything, and is the last step before the Step 14
   hostile launch review, which is out of scope here.

**Merge discipline.** Steps 4 through 13 land on a branch touching no Phase A
file. After Phase A merges, one reconciliation commit should:

1. add the single `cloud` subparser line to
   `src/pneuma_lab/resampling_null/cli.py`;
2. append the Phase B entries to `docs/project-status.json`,
   `34-tasks-6-10-vps-handoff.md`, and the execution journal; and
3. re-run `python -m pneuma_lab.status --check`.

---

## 6. Collision risks, ranked

1. **`src/pneuma_lab/resampling_null/cli.py` and `tests/resampling_null/test_cli.py`**
   — under active Phase A edit. Mitigation: an own `cloud/cli.py`, with one-line
   wiring added last.
2. **Append-only shared documents** — `15-decision-log.md`,
   `33-execution-journal.md`, `32-cloud-spend-ledger.md`. Both work streams
   append. Mitigation: append only at the end, never renumber, and reconcile
   after the merge. The roadmap's Phase A step 2 already names this hazard.
3. **`docs/project-status.json`** — schema-validated, and two writers will
   conflict. Mitigation: defer every Phase B edit to the reconciliation commit.
4. **`src/pneuma_lab/resampling_null/release.py`** — new, uncommitted, and owned
   by Phase A. Do not create a file with that name and do not import it.
5. **`tests/resampling_null/provider_authority_fixture.py`** — under active
   Phase A edit. Phase B must not depend on its current shape.
6. **`power.py` and `branch_controller.py`** — Step 8 will be tempted to modify
   them. Do not; wrap them. Any change invalidates the Task 8 and Task 9 receipts
   and the Step 4A continuity results.
7. **New schema `$id` collisions** — prefix everything `cloud-` so nothing can
   collide with the `resampling-*` family or with a Task 10 schema.
8. **Test discovery** — default pytest discovery is intentionally restricted to
   `tests/smoke`, so `tests/cloud/` is invisible by default. That is correct. Run
   it explicitly with `python -m pytest tests/cloud -q`, and do not widen default
   discovery.

---

## 7. Open items this plan deliberately leaves unresolved

- **Serving topology and context cap.** Contractually determined by the Tier-1
  pilot, not by Step 4. Step 4 records a carve-out; Step 13 encodes the gate.
- **Tier target.** Both `C120` and `C160` are currently recorded
  `FEASIBILITY_NO_GO` on the SWE side. Step 4 must name the tier it freezes
  toward and restate the unmet inequality rather than resolving it.
- **`00-README.md` routing defect and the absent
  `26-detectability-audit-design.md`.** Identified here; repair belongs to
  Step 4, executed through the authority surfaces.
- **The roadmap's Step-11 small cloud job.** Deferred; requires separate
  authorization.
- **Step 14 hostile launch review.** Out of scope.
- **Step 4B.** Not run, not prepared, and not made easier to run accidentally.
