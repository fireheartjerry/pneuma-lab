# Foundation Training Launch Preparation Design

**Status:** Approved design. Implementation may prepare every launch artifact,
but it must not execute an optimizer update.

**Date:** 2026-07-13

## Goal

Make the Qwen3.5-2B Pneuma foundation program genuinely ready for its first
100K-token training smoke run. Preparation includes an executable runner,
deterministic data packaging, exact authorization bindings, a reproducible WSL2
environment, a verified pinned-model download, dry-run verification, recovery
controls, and a marked operator guide. Training itself remains a separate,
explicit human action.

All ten active dataset families participate in the program. Participation does
not imply gradient weight: training, evaluation, and governance are distinct
roles, and role violations fail closed.

## Non-goals

- Do not execute backward propagation or an optimizer step.
- Do not train, resume, evaluate a learned checkpoint, or promote a model.
- Do not download, load, train, or serve Qwen3.5-397B.
- Do not write to `C:\pneuma-data`.
- Do not upload raw `C:\pneuma-data` content to a cloud provider.
- Do not turn held-out benchmarks into training sources.
- Do not process SWE-Chat payloads before a privacy decision and redaction
    contract exist.
- Do not process exploit-bearing SEC-Bench-Pro payloads or generate or execute
    functioning exploits.
- Do not create a second notebook-only training implementation.
- Do not spend money, create cloud resources, or enable recurring billing.

## Current truth that the implementation must preserve

- Training has not started.
- The foundation authorization is `not_authorized`, has no bound shard, has no
    positive-weight group, and has no operator approval.
- No foundation end-to-end runner exists. The current CLI exposes only
    `doctor` and `duration`.
- Ubuntu WSL2 and the RTX 5060 Laptop GPU are present, but no WSL training
    environment exists. WSL currently exposes Python 3.14.4 and about 15 GiB
    RAM.
- The pinned Qwen3.5-2B checkpoint is not cached.
- `build/foundation/` does not yet exist.
- The older signed PneumaBrain-v0.1 authorization is not authority for a Qwen
    foundation run.
- All ten source families are governed, but none is currently registry-approved
    for positive foundation gradient weight.
- Filesystem metadata shows SWE-Chat bytes even though older prose says they are
    absent. This is status drift, not permission to inspect them.

## Chosen approach

Use one non-interactive, CLI-first implementation for local WSL2 and the single
optional RunPod reproduction. A notebook is not required. Any optional notebook
may contain explanatory cells and shell out to the same CLI, but it cannot own
training behavior.

The primary path is local and costs $0 beyond electricity. Cloud use remains a
single, post-local-gates reproduction job with a tax-inclusive lifetime ceiling
of $45.

## Dataset role matrix

The registry remains the source of truth. The preparation command must emit a
suite-completeness report containing every active family and must reject an
unknown, missing, or multiply contradictory role.

| Active family | Preparation role | Gradient posture for first launch |
|---|---|---|
| `swe-gym` | OpenHands Sampled is the first candidate; verifier and Lite remain expansion lanes | positive only after exact license, shard, split, leakage, and authorization gates |
| `open-swe-traces` | second trajectory candidate | zero until full conversion, grouped split, overlap quarantine, and output-ToS decision pass |
| `multi-swe-bench` | expansion candidate | zero until artifact license and adapter gates pass |
| `swe-evo` | expansion candidate | zero until overlap quarantine and adapter gates pass |
| `swe-polybench` | evaluation/difficulty or later expansion candidate | zero until a defensible target and adapter exist |
| `swe-bench` | canonical held-out evaluation | always zero for this program |
| `swe-mera` | anti-contamination held-out evaluation | always zero for this program |
| `swe-bench-pro` | blocked, likely future evaluation | zero while artifact license and role are unresolved |
| `swe-chat` | privacy-governance lane | zero; metadata-only until privacy and redaction approval |
| `sec-bench-pro` | dual-use governance lane | zero; metadata-only with no exploit generation or execution |

The first smoke-run authorization may name only `swe-gym` as positive weight,
and only through the OpenHands Sampled lane. Open-SWE-Traces can join a later
authorization without changing the runner. All other role changes require a
separate registry review and new authorization digest.

## Canonical foundation training record

The existing canonical training example is not directly consumable by the
foundation optimizer. Add a schema and renderer for a `FoundationTrainingRecord`
that contains:

- record and source identifiers;
- active dataset family and exact lane identifier;
- terminal role: `train`, `eval`, or `governance`;
- source revision and receipt hashes;
- repository, issue or pull request, task, base commit, patch hash, test-patch
    hash, and fuzzy-text hash;
- split identifier and leakage-quarantine identifier;
- deterministic rendered prompt text and target text;
- token count and tokenizer revision;
- training weight, which must be zero unless the registry and authorization
    both permit a positive value;
- the eight `MetacognitiveForecast` targets;
- an applicability mask for each forecast target;
- outcome-derived provenance for every applicable target;
- language, tools, trajectory length, and observable labels used by the
    diversity inventory;
- privacy, license, dual-use, and oracle-leakage dispositions.

Unavailable forecast outcomes are masked, never invented. The loss averages
only applicable, outcome-derived targets and fails if a positive-weight record
has no supervised language target or no applicable forecast target.

## Preparation data flow

1. Load only committed registry, readiness, and policy metadata.
2. Verify that all ten active families have one coherent terminal role.
3. Reconcile filesystem-presence metadata without opening blocked payloads.
4. Run authorized existing converters for the selected positive lane.
5. Render canonical foundation records deterministically.
6. Deduplicate by repository, issue/PR, task, base commit, patch, test patch,
    and fuzzy text.
7. Generate repository-grouped train, validation, and held-out splits.
8. Compare every positive-weight record against every evaluation identity and
    fail on overlap.
9. Write content-addressed shards only below `build/foundation/shards/`.
10. Write token, repository, issue, language, tool, trajectory-length, label,
    target-applicability, and role counts.
11. Write conversion, split, leakage, diversity, and suite-completeness
    receipts.
12. Generate a hash-bound authorization candidate without approving it.

Preparation is restartable and deterministic. Re-running it from the same
commit and source receipts must reproduce the same shard and manifest hashes.

## Authorization handshake

The software cannot authorize itself. The workflow has two explicit phases:

1. `authorization-candidate` prints and writes the exact model pin, code commit,
    shard hashes, split and leakage receipts, dataset roles, positive groups,
    token ceiling, output root, local budget, and scope digest.
2. `authorization-finalize` requires the operator to provide the displayed
    scope digest and a deliberate approval phrase. It writes a separate signed
    local authorization record. Any changed byte invalidates it.

Design approval is not run authorization. After implementation produces the
real hashes, the operator must review that exact scope. The runner verifies the
authorization before `train` or `resume` loads model weights or creates an
optimizer. The separate `dry-run` path may load the pinned model under a
non-training preparation manifest, but it cannot construct an optimizer or
enable gradients.

## CLI surface

Extend `python -m pneuma_lab.foundation` with these commands:

- `doctor`: inspect host prerequisites without downloads.
- `setup-plan`: print the pinned WSL setup and required restart steps.
- `prepare --stage 100k`: produce canonical records, shards, splits, receipts,
    inventories, and an authorization candidate.
- `preflight --stage 100k`: verify environment, model pin, data hashes,
    authorization, output containment, resources, and clean code provenance.
- `download-model --model 2b`: download only the pinned public 2B revision into
    ignored foundation cache and verify the snapshot revision.
- `dry-run --stage 100k`: load the pinned quantized model, install validated
    hooks, test disabled-core parity, tokenize one authorized synthetic record,
    and execute one no-gradient forward pass. It must not create an optimizer.
- `authorization-candidate`: show the exact approval scope.
- `authorization-finalize`: record explicit human approval of that exact scope.
- `train --stage 100k --lr ...`: execute the run only after every gate passes.
    This command is implemented and tested but not invoked during preparation.
- `resume --checkpoint ...`: restore an interrupted run exactly. This command
    is implemented and tested but not invoked during preparation.
- `evaluate --run ...`: run held-out and regression gates after training.
- `report --run ...`: materialize the run, resource, capability, governance,
    and memory-integrity reports.
- `cloud-bundle --stage ...`: export only code provenance, authorization,
    receipts, and authorized content-addressed shards; raw corpus paths are
    rejected.

Every mutating command supports `--dry-run` where meaningful and prints the
paths it would write. `train` and `resume` require an explicit run authorization
and cannot be reached from `prepare` or `dry-run` by fall-through.

## Integrated runner

The runner connects the existing pinned loader, hybrid-layer validation,
junction installer, optimizer loop, curriculum, checkpoint manager,
falsification gate, and resource guard. It additionally owns:

- tokenizer loading and deterministic prompt/target encoding;
- a document-boundary-aware collator;
- deterministic sampler order and persisted cursor;
- AdamW and scheduler construction;
- gradient checkpoint activation;
- BF16 capability validation;
- learning-rate trial selection;
- validation cadence and metric aggregation;
- structured event logs and run-manifest updates;
- checkpoint pruning and best-checkpoint retention;
- graceful signal, thermal, memory, and budget termination;
- model-core artifact export without exporting the immutable base checkpoint.

The base performs one forward per decision. DeltaNet state resets between
documents and only deliberately continues across tool ticks. Packing multiple
documents into one recurrent state is rejected.

## Exact checkpoint and resume

Checkpoint only at optimizer-step boundaries. A checkpoint contains:

- Pneuma core, projection, and permitted LoRA state;
- optimizer and scheduler state;
- CPU and every CUDA RNG state;
- epoch, sampler permutation seed, dataset cursor, microbatch count, optimizer
    step, processed token count, and selected learning rate;
- recurrent and active-memory buffers;
- authorization digest, model revision, shard hashes, and code commit;
- telemetry accumulator and last safe resource sample;
- best-validation state and checkpoint lineage;
- termination reason when the save is caused by a stop condition.

Because saves occur only after accumulated gradients are applied, no pending
gradient tensors need reconstruction. The 30-minute rule requests a checkpoint
at the next safe boundary. Resume refuses changed code, data, authorization,
model revision, optimizer definition, or curriculum parameters.

An automated interruption test must prove that uninterrupted and resumed fake
training produce exactly equal trainable weights, optimizer/scheduler states,
cursor position, and metrics.

## Resource monitoring and stop behavior

A background sampler records, at bounded cadence:

- GPU allocation and reservation;
- total GPU use and free VRAM;
- process and system RAM;
- GPU temperature, power, utilization, and throttle reasons when available;
- tokens/second and optimizer steps/second;
- p50 and p95 base and core latency;
- checkpoint duration and disk use.

The run pauses at a safe boundary on temperature above 85 C, sustained thermal
throttling, process VRAM above 7.5 GB, process RAM above 24 GB, repeated
instability, or explicit operator interruption. It stops and records failure on
NaN/Inf loss, changed authorization inputs, disk exhaustion risk, or regression
gate failure.

## Local WSL2 preparation

Use Ubuntu WSL2 with Python 3.12 in an isolated environment. Do not use the
current Python 3.14 system interpreter for the launch environment. Pin the
complete dependency set, including the exact Transformers commit required by
the pinned Qwen snapshot.

The operator guide includes:

- a reviewed `.wslconfig` example that raises the current WSL memory cap while
    retaining host headroom;
- the explicit `wsl --shutdown` restart step;
- environment creation and lock verification;
- CUDA and bitsandbytes verification;
- repository and source-root path checks;
- model download and dry-run commands;
- instructions to close GPU-heavy Windows applications before measurement;
- checkpoint, log, report, and recovery locations;
- commands to prove that `C:\pneuma-data` was not modified.

The setup script may install dependencies and download the pinned 2B model. It
must not finalize authorization or call `train`.

## Optional RunPod reproduction

Cloud is not used for exploratory sweeps or the first local run. After all local
gates pass, the marked guide recommends one RunPod On-Demand A40 with 48 GB
VRAM, using the official PyTorch template, SSH, and `tmux`.

The current planning quote is $0.44/hour for one A40. The operator must re-check
the live quote. Use at most $38 USD of one-time prepaid credit, verify the
tax-inclusive checkout remains at or below $45, and keep auto-pay disabled. Use
a 30 GB container disk, an 80 GB volume disk, and automatic termination at 72
hours. Download all required results before terminating the Pod; stopped volume
storage still incurs charges.

The default cloud reproduction is the 2M-token falsification run. At 20
tokens/second it takes about 27.8 hours and $12.22 of A40 compute at the planning
quote. An 8M-token cloud run is permitted only if measured cloud throughput is
at least 30.9 tokens/second and the all-in quote still fits both 72 hours and
the remaining tax-inclusive lifetime budget.

Required accounts and credentials are limited to:

- a personal RunPod account for the optional cloud job;
- GitHub authentication only if the repository cannot be cloned anonymously;
- an optional read-only Hugging Face token if public anonymous download limits
    require it.

No SWE-Chat credential, gated-dataset acceptance, notebook upload, paid model
API, hosted database, or recurring cloud service is required. Secrets remain in
the provider secret store or process environment and never enter the repository,
bundle, logs, notebook, or run manifest.

Official planning references:

- <https://www.runpod.io/pricing>
- <https://docs.runpod.io/accounts-billing/billing>
- <https://docs.runpod.io/pods/connect-to-a-pod>
- <https://docs.runpod.io/pods/pricing>
- <https://docs.runpod.io/pods/manage-pods>

## Operator documentation

Create `START-HERE-TRAINING.md` at the repository root with a conspicuous
`TRAINING HAS NOT STARTED` marker. It contains:

- the current readiness summary;
- what the ten-dataset promise means;
- local WSL setup and restart instructions;
- exact environment, preparation, model-download, dry-run, authorization,
    launch, monitor, interrupt, resume, evaluate, and report commands;
- expected successful output after every command;
- checkpoint and log locations;
- common failures and exact recovery commands;
- the local-first duration table;
- the optional RunPod login, billing, Pod, SSH, upload, launch, export, and
    termination sequence;
- a warning that no raw corpus or blocked data may be uploaded;
- an operator checklist whose final unchecked item is the actual `train`
    command.

The guide is generated from or tested against CLI help/constants so commands do
not silently drift.

## Verification strategy

All new behavior follows test-first development. Required automated coverage
includes:

- canonical training-record schema validation and masked-target loss;
- deterministic rendering, tokenization fixtures, and content hashes;
- all-ten suite completeness and role enforcement;
- blocked/eval lane zero-weight rejection;
- SWE-Chat payload non-access and SEC-Bench-Pro no-exploit enforcement;
- repository/issue/task/commit/patch/test/fuzzy leakage detection;
- authorization candidate and exact-digest finalization;
- train refusal before authorization and before resource/model checks;
- one-base-forward and explicit DeltaNet reset behavior;
- safe-boundary checkpoint scheduling and exact interruption/resume;
- live resource sampler parsing with recorded fixtures;
- thermal, memory, NaN, signal, disk, and budget stop paths;
- run-manifest and report completeness;
- cloud-bundle rejection of raw or unapproved paths;
- operator-guide command consistency;
- CLI tests using a fake model and tokenizer;
- an opt-in pinned-Qwen download/load/parity/no-gradient-forward smoke test.

Completion verification runs the full pytest suite, status checker, dataset
readiness checker, foundation preflight in non-training mode, operator-guide
command checker, whitespace check, and a filesystem receipt proving no writes
under `C:\pneuma-data`.

## Definition of preparation complete

Preparation is complete only when:

- the integrated runner and every documented command exist;
- the pinned WSL environment is reproducible;
- Qwen3.5-2B is pinned, cached, and passes a no-gradient dry run;
- the first 100K content-addressed shard, splits, inventories, and receipts are
    real and deterministic;
- all ten families have verified roles;
- the exact positive lane is disjoint from held-out evaluation identities;
- the operator has approved the exact authorization digest;
- `preflight --stage 100k` passes without allocating an optimizer;
- exact-resume and failure-path tests pass;
- `START-HERE-TRAINING.md` contains verified commands;
- no training step has run, no cloud resource has been created, no money has
    been spent, and no source corpus file has changed.

At that point, the only remaining local action is the explicitly marked `train`
command. The only remaining optional cloud actions are account login, prepaid
credit purchase, Pod creation, and launch after the local gates pass.
