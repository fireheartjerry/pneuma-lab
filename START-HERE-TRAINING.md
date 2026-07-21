# LOCAL LADDER AND CLOUD 2M COMPLETE — FALSIFICATION GATE PASSED

The local Qwen3.5-2B ladder completed through 2M on 2026-07-20 under exact
per-stage operator authorizations. 100K smoke: three runs (5e-5/1e-4/2e-4),
best validation loss 3.5085 at the selected 2e-4, ~312-339 tokens/second.
500K: run `foundation-500k-b4b5f1da90aff5ab`, 32 steps, 200,874 tokens —
exhausting the single OpenHands-Sampled lane and motivating the multi-lane
redesign. 2M: run `foundation-2m-20a569bfe4a43886` over TWO gradient lanes
(OpenHands-Sampled + the new 160,731-trace open-swe-traces pneuma-trace
lane), 330 steps, 1,997,114 tokens, best validation loss 0.0875. The
four-variant falsification kill gate PASSED on 3,399 repo-disjoint held-out
tasks: pneuma_recurrent 64.14% vs 35.86% for the strongest baseline
(+28.27 absolute points, bootstrap CI95 [0.251, 0.315], honest-proxy
`held_out_risk_prediction_correctness` semantics; the two pre-registered
baselines run from deterministic untrained initializations, disclosed in
every result file). The one-time RunPod cloud reproduction then completed
on 2026-07-21 under a separately finalized two-lane cloud authorization
(scope digest `35f23296…`, $35 all-in job ceiling): run
`foundation-2m-35f2329653ca804e` on an On-Demand A40 ($0.44/hr, CUDA 13.0
host), 330 steps, best validation loss 0.08654 (local: 0.08746), results
archive retrieved and the pod terminated with zero pods and zero volumes
remaining. Lifetime cloud jobs used: 1 of 1; actual paid compute under
$2, within every budget gate.
No Jupyter notebook is required. Local WSL2 and optional RunPod both use the
same CLI. This guide remains the canonical procedure for every later stage.

Every command below is validated against the real CLI by
`python -m pneuma_lab.foundation.operator_guide START-HERE-TRAINING.md`.
The final `train` action at the bottom of this guide is deliberately
unchecked: running it is an explicit operator decision, never an automated
step.

## 1. What “all ten datasets” means

The suite policy `docs/data/training-readiness/pneuma-foundation-v0-suite.json`
governs exactly ten dataset families. During the 100K stage only the
`swe-gym-openhands-sampled` lane may carry a positive in-memory training
weight, and only after exact operator authorization:

- **train (first stage):** `swe-gym` — only the approved processed
  OpenHands-Sampled lane payload is ever opened.
- **train (later stages):** `multi-swe-bench`, `open-swe-traces`, `swe-evo` —
  metadata-only at 100K.
- **eval:** `swe-bench`, `swe-mera`, `swe-polybench` (identity metadata only,
  for contamination checks), `swe-bench-pro` (metadata-only).
- **governance (never trained):** `swe-chat`, `sec-bench-pro` — payloads are
  never opened; presence is probed by filesystem metadata only.

Every persisted training record carries `training_weight: 0.0`. A positive
effective weight exists only in memory, only for the exact authorized lane,
and only while a verified final authorization is loaded.

The 500K stage reuses the exact 100K access matrix (`payload_access_500k`
in the suite policy). The 2M stage (`payload_access_2m`) additionally opens
the approved `open-swe-traces` processed lane
(`processed/open-swe-traces/pneuma-trace`), with the committed
cross-dataset leakage registry quarantining the 7 overlapping repositories
and both lane license receipts pinned. 8M-and-later stages remain
fail-closed until their own `payload_access_<stage>` column lands with its
readiness work.

## 2. Current readiness and hard safety boundaries

- The committed authorization
  `docs/data/training-authorizations/pneuma-foundation-v0.pending.json` is
  explicitly `not_authorized`. Nothing trains until you finalize an exact
  candidate yourself (section 9).
- `C:\pneuma-data` (WSL: `/mnt/c/pneuma-data`) is an immutable input root.
  Preparation proves with before/after metadata receipts that it did not
  change. All derived artifacts stay under ignored `build/foundation/`.
- Hard local limits enforced at runtime: 7.5 GiB process VRAM, 24 GiB process
  RAM, 85 °C GPU temperature, disk-headroom and non-finite-loss stops. Every
  pause or failure lands at a safe optimizer boundary with a checkpoint and a
  schema-valid run manifest.
- Paid compute is $0. The lifetime cloud cap is $45 and requires its own
  separately finalized cloud authorization (section 13).
- Only the pinned `Qwen/Qwen3.5-2B` snapshot is ever downloaded. The 397B
  compatibility reference is forbidden to download or load.

## 3. Windows WSL2 memory setup

Check whether `%UserProfile%\.wslconfig` already exists. If it does and its
contents differ from the reviewed example, do not overwrite it silently —
merge deliberately. Then:

```powershell
Copy-Item .wslconfig.foundation.example "$HOME\.wslconfig"
wsl --shutdown
wsl -d Ubuntu
```

The example grants WSL 24 GB RAM with 8 GB swap. The doctor requires at least
22 GiB visible inside WSL. You can print the full planned setup sequence at
any time:

```bash
python -m pneuma_lab.foundation setup-plan --json
```

## 4. WSL Python 3.12 environment

```bash
cd /mnt/c/pneuma-lab
bash scripts/foundation/setup-wsl.sh
source .venv/bin/activate
python -m pneuma_lab.foundation doctor
```

The setup script pins uv 0.11.28, Python 3.12, and the locked foundation
dependency set (torch 2.13.0, bitsandbytes 0.49.2, peft 0.19.1, accelerate
1.14.0, transformers at the pinned commit). It ends with `SETUP COMPLETE` and
`TRAINING HAS NOT STARTED`; it can neither authorize nor train. `doctor` must
print `READY` before you continue.

## 5. Close GPU-heavy Windows applications

The local card has slightly under 8 GiB of VRAM and the run budget is
7.5 GiB. Close browsers with hardware acceleration, games, video editors, and
anything else holding GPU memory before training. `nvidia-smi` on the Windows
side shows current consumers.

## 6. Download and verify only Qwen3.5-2B

```bash
python -m pneuma_lab.foundation download-model --model 2b
```

This is the only network step. It downloads the pinned revision
`15852e8c16360a2fea060d615a32b45270f8a8fc` into
`build/foundation/cache/models/2b/<revision>/`, hashes every file, writes
`pneuma-snapshot-receipt.json`, and re-verifies the receipt. Everything after
this step runs offline (`HF_HUB_OFFLINE=1`).

## 7. Prepare the deterministic 100K shard

```bash
python -m pneuma_lab.foundation prepare --stage 100k --data-root /mnt/c/pneuma-data
```

Run it twice; both runs must print identical shard, manifest, split,
contamination, diversity, selection, and candidate hashes. Expected outputs
under `build/foundation/preparation/100k/`: the preparation manifest, suite
report, license receipt, source before/after presence and integrity receipts,
split, contamination, diversity, and selection receipts, and the
content-addressed zero-weight shard with its manifest. The final operation
emits `build/foundation/authorizations/candidates/100k.json`.

## 8. Review the exact authorization candidate

```bash
python -m pneuma_lab.foundation authorization-candidate --stage 100k
```

This prints the exact scope (model and tokenizer pins, stage, token ceiling,
learning rates, code commit, artifact hashes, lane weights, budget), the
scope digest, and the deliberate approval phrase. Read the scope. The phrase
embeds the digest, so approving one scope can never authorize another.

## 9. Finalize only the displayed digest

Paste exactly the two values printed by `authorization-candidate` — the scope
digest and the approval phrase. Empty input or values that differ from the
candidate fail closed.

```bash
read -r -p "Paste the displayed scope digest: " PNEUMA_SCOPE_DIGEST
read -r -p "Paste the displayed approval phrase: " PNEUMA_APPROVAL_PHRASE
python -m pneuma_lab.foundation authorization-finalize --candidate build/foundation/authorizations/candidates/100k.json --scope-digest "$PNEUMA_SCOPE_DIGEST" --approval-phrase "$PNEUMA_APPROVAL_PHRASE" --operator-id student-operator
```

The final authorization is written to
`build/foundation/authorizations/final/100k.json`; the candidate file is
never overwritten. Any later byte change to a bound artifact invalidates the
final scope.

## 10. Run non-training preflight and no-gradient dry run

```bash
python -m pneuma_lab.foundation preflight --stage 100k --authorization build/foundation/authorizations/final/100k.json --lr 5e-5
python -m pneuma_lab.foundation dry-run --stage 100k
```

Preflight verifies the authorization, clean code commit, cache, environment,
and learning-rate scope in that exact order and allocates nothing. The dry
run loads the model without gradients, proves junction parity across the five
cache boundaries, measures p95 latency overhead (limit 25%) and estimated
additional FLOPs (limit 20%), and never constructs an optimizer.

## 11. Start, monitor, interrupt, and resume training

The 100K stage is a correctness and throughput smoke test, run three times —
once per approved learning rate (`5e-5`, `1e-4`, `2e-4`). Its measured
tokens/second, not an estimate, sets the wall-clock forecast for later
stages:

```bash
python -m pneuma_lab.foundation duration --tokens 100000 --tps 20
python -m pneuma_lab.foundation duration --tokens 100000 --tps 50
```

| Stage | Tokens    | At 20 tokens/s | At 50 tokens/s |
| ----- | --------- | -------------- | -------------- |
| 100k  | 100,000   | 1.4 h          | 0.6 h          |
| 500k  | 500,000   | 6.9 h          | 2.8 h          |
| 2m    | 2,000,000 | 27.8 h         | 11.1 h         |
| 8m    | 8,000,000 | 111.1 h        | 44.4 h         |

The launch, pause, and resume sequence:

```bash
python -m pneuma_lab.foundation train --stage 100k --authorization build/foundation/authorizations/final/100k.json --lr 5e-5
read -r -p "Paste the run directory printed by train: " PNEUMA_RUN_PATH
read -r -p "Paste the checkpoint path printed by pause: " PNEUMA_CHECKPOINT_PATH
python -m pneuma_lab.foundation resume --authorization build/foundation/authorizations/final/100k.json --checkpoint "$PNEUMA_CHECKPOINT_PATH"
```

- Each run writes `build/foundation/runs/<run-id>/manifest.json` (atomic,
  schema-valid), `events.jsonl` (append-only), and `checkpoints/`.
- Checkpoints land only at safe optimizer boundaries, every 500 optimizer
  steps or 30 minutes, whichever comes first. A resumed run is bit-for-bit
  identical to an uninterrupted one.
- `Ctrl+C` is a safe pause: the signal sets a flag consumed at the next
  boundary, a checkpoint is written, and the manifest records
  `operator_interrupt`. Never kill the process a second time mid-write.
- Thermal (≥ 85 °C), VRAM, RAM, and sustained-throttle conditions pause;
  non-finite loss, authorization drift, and disk risk fail. Both outcomes
  checkpoint and record their reason.

## 12. Evaluate and report

```bash
python -m pneuma_lab.foundation evaluate --run "$PNEUMA_RUN_PATH"
python -m pneuma_lab.foundation report --run "$PNEUMA_RUN_PATH"
```

Evaluation is smoke-only before the 2M stage (`not_applicable_before_2m` for
the falsification gate). Reports land under
`build/foundation/runs/<run-id>/reports/` — six fixed sections plus an index,
every payload carrying `no_consciousness_claim: true`. Across the three 100K
learning-rate runs, the report layer selects the learning rate; ties select
the lower rate.

## 13. Optional one-time RunPod reproduction

This section is optional and applies to the 2M stage at the earliest. If the
exact authorization says private cloud transfer is false: `SKIP CLOUD
REPRODUCTION`.

Open <https://www.runpod.io/>, log into a personal RunPod account, and
re-check the live On-Demand A40 48GB quote — the planning quote is not an
authorization; replace it with the live quote in the cloud candidate and
bundle commands below. Hard limits: one-time credit at most $38, tax-inclusive
checkout at most $45 lifetime, auto-pay off, official PyTorch template, 30 GB
container disk and 80 GB volume, 72-hour auto-termination, SSH plus `tmux`.
No notebook upload, no raw corpus upload. Download outputs before
termination; a stopped volume still bills. GitHub login is needed only if the
repository cannot be cloned anonymously. A read-only Hugging Face token is
optional and only needed if anonymous public-model limits block the download.
No dataset credential, gated-dataset acceptance, model API, hosted database,
or recurring service is required. Secrets stay in provider secrets or the
process environment and never enter Git, bundles, logs, manifests, or
notebooks. Official references: [pricing](https://www.runpod.io/pricing),
[billing](https://docs.runpod.io/get-started/billing-information),
[connecting](https://docs.runpod.io/pods/connect-to-a-pod),
[pricing model](https://docs.runpod.io/pods/pricing), and
[pod lifecycle](https://docs.runpod.io/pods/manage-pods).

At 2M the cloud authorization binds the same two gradient lanes as the local
final: the Open-SWE-Traces license receipt, the cross-dataset leakage receipt,
the lane-keyed conversion evidence, and both lane weights travel unchanged
into the cloud scope, and a single-lane 2M cloud candidate fails closed. Both
lane license receipts keep `cloud_redistribution_allowed: false`; the bundle
is not redistribution — it is the private, single-job transfer of derived,
digest-bearing artifacts, permitted only by the operator-approved
`private_cloud_transfer_allowed: true` posture in the finalized cloud scope.

When a passing local-gate report exists and transfer is approved, build the
separately finalized cloud authorization and bundle locally:

```bash
read -r -p "Paste the live hourly A40 quote: " RUNPOD_HOURLY_USD
read -r -p "Paste the tax-inclusive checkout total: " RUNPOD_TAX_TOTAL_USD
read -r -p "Paste the completed local-gate report path: " PNEUMA_LOCAL_GATE_REPORT
python -m pneuma_lab.foundation authorization-candidate --stage 2m --profile cloud --local-authorization build/foundation/authorizations/final/2m.json --local-gate-report "$PNEUMA_LOCAL_GATE_REPORT" --quoted-hourly-usd "$RUNPOD_HOURLY_USD" --quoted-tax-inclusive-usd "$RUNPOD_TAX_TOTAL_USD"
read -r -p "Paste the displayed cloud scope digest: " PNEUMA_CLOUD_SCOPE_DIGEST
read -r -p "Paste the displayed cloud approval phrase: " PNEUMA_CLOUD_APPROVAL_PHRASE
python -m pneuma_lab.foundation authorization-finalize --candidate build/foundation/authorizations/candidates/2m-cloud.json --scope-digest "$PNEUMA_CLOUD_SCOPE_DIGEST" --approval-phrase "$PNEUMA_CLOUD_APPROVAL_PHRASE" --operator-id student-operator
python -m pneuma_lab.foundation cloud-bundle --stage 2m --authorization build/foundation/authorizations/final/2m-cloud.json --quoted-hourly-usd "$RUNPOD_HOURLY_USD" --quoted-tax-inclusive-usd "$RUNPOD_TAX_TOTAL_USD"
read -r -p "Paste the RunPod SSH host: " RUNPOD_SSH_HOST
read -r -p "Paste the RunPod SSH port: " RUNPOD_SSH_PORT
scp -P "$RUNPOD_SSH_PORT" build/foundation/cloud/pneuma-2m.tar "root@$RUNPOD_SSH_HOST:/workspace/"
scp -P "$RUNPOD_SSH_PORT" build/foundation/authorizations/final/2m-cloud.json "root@$RUNPOD_SSH_HOST:/workspace/"
ssh -p "$RUNPOD_SSH_PORT" "root@$RUNPOD_SSH_HOST"
```

On the Pod:

```bash
cd /workspace
mkdir -p pneuma-2m
tar -xf pneuma-2m.tar -C pneuma-2m
cd pneuma-2m
bash scripts/foundation/setup-linux.sh cloud
tmux new -s pneuma
uv run python -m pneuma_lab.foundation doctor --profile cloud
uv run python -m pneuma_lab.foundation download-model --model 2b
uv run python -m pneuma_lab.foundation preflight --stage 2m --profile cloud --authorization /workspace/2m-cloud.json --lr 5e-5
uv run python -m pneuma_lab.foundation train --stage 2m --profile cloud --authorization /workspace/2m-cloud.json --lr 5e-5
tar -czf /workspace/pneuma-results.tar.gz build/foundation/runs
```

Detach from `tmux` with `Ctrl+B`, then `D`. Retrieve results locally:

```bash
scp -P "$RUNPOD_SSH_PORT" "root@$RUNPOD_SSH_HOST:/workspace/pneuma-results.tar.gz" build/foundation/cloud/
```

Finally, and explicitly: verify the result archive locally, click
**Terminate Pod**, confirm termination, and confirm no stopped volume or
running Pod remains.

## 14. Common failures and exact recovery

- **`doctor` prints `BLOCKED`** — every blocker names its condition
  (`insufficient_ram` → redo section 3; `missing_<package>` or version
  mismatches → rerun section 4; `cuda_required` → check the Windows NVIDIA
  driver and `nvidia-smi` inside WSL).
- **GPU temperature pause** — the manifest says `gpu_temperature`; let the
  machine cool, improve airflow, then `resume` with the printed checkpoint.
- **VRAM/RAM pause** — close Windows GPU consumers (section 5) or other WSL
  processes, then `resume`.
- **Disk-risk failure** — free space under `build/` (old runs are safe to
  archive elsewhere); the run refuses to continue without checkpoint
  headroom.
- **Non-finite loss failure** — the run cannot be resumed past the failure;
  restart the stage with a different approved learning rate.
- **Source-integrity doubt** — compare the before/after source receipts in
  `build/foundation/preparation/100k/`; they must be identical. Note that
  `git diff -- C:/pneuma-data` proves nothing because the corpus is a
  separate non-repository root — only the metadata receipts are evidence.
- **Authorization drift** — if any bound file changed, preparation,
  candidate, review, finalization, and preflight must all be redone; the old
  final authorization is permanently invalid.

## 15. Final operator checklist

- [ ] WSL memory configured (section 3) and `wsl --shutdown` completed
- [ ] `bash scripts/foundation/setup-wsl.sh` ended with `SETUP COMPLETE`
- [ ] `python -m pneuma_lab.foundation doctor` printed `READY`
- [ ] `python -m pneuma_lab.foundation download-model --model 2b` wrote a verified receipt
- [ ] `python -m pneuma_lab.foundation prepare --stage 100k` run twice, byte-identical
- [ ] `python -m pneuma_lab.foundation authorization-candidate --stage 100k` scope reviewed
- [ ] `python -m pneuma_lab.foundation authorization-finalize` accepted the pasted digest and phrase
- [ ] `python -m pneuma_lab.foundation preflight` reported ready with no allocation
- [ ] `python -m pneuma_lab.foundation dry-run --stage 100k` passed parity with zero gradients
- [ ] `python -m pneuma_lab.foundation train --stage 100k --authorization build/foundation/authorizations/final/100k.json --lr 5e-5`
