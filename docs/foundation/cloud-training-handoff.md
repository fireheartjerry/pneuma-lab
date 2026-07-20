# Cloud training handoff — for the next agent

Audience: a future agent (for example one driving a browser via the
Claude-in-Chrome skill) that will take the Pneuma foundation program from the
completed local 100K smoke stage to the later local stages and the optional
paid cloud reproduction. Read `START-HERE-TRAINING.md` first — it is the
drift-checked command runbook; this document is the state, the numbers, and
the exact remaining path.

## Where the program stands (2026-07-20)

- Branch `codex/foundation-training-launch-prep`. All sixteen tasks of the
  launch-preparation plan are implemented, reviewed, and verified (full suite
  1888+ passed). Session audit:
  `docs/sessions/2026-07-19-foundation-training-launch-completion.md`.
- The local 100K smoke stage is COMPLETE under exact operator authorization:

| Run           | Steps | Tokens | Tokens/s | Best val loss | Last val loss |
| ------------- | ----- | ------ | -------- | ------------- | ------------- |
| `100k` @ 5e-5 | 15    | 93,967 | 339.0    | 3.5294        | 4.0125        |
| `100k` @ 1e-4 | 15    | 93,967 | 314.5    | 3.5216        | 4.0018        |
| `100k` @ 2e-4 | 15    | 93,967 | 312.6    | **3.5085**    | **3.9648**    |

Peak process VRAM 2.82 GiB (limit 7.5); zero thermal throttling; live GPU
temperature 63–73 °C (limit 85). **2e-4 is the selected learning rate** by
the lowest-validation-loss rule (no tie). Artifacts live under ignored
`build/foundation/runs/100k-<rate>/` (manifest.json, events.jsonl,
checkpoints/checkpoint-00000015.pt).

- Throughput forecast at ~320 tokens/s local: 500K ≈ 26 min, 2M ≈ 1.7 h,
  8M ≈ 7 h of pure training time (plus ~1 min model load per run).
- Paid compute spent: $0. Cloud resources created: 0. Lifetime cloud cap: $45
  (hard-coded gate).

## 500K stage result (2026-07-20) and the data-supply finding

The 500K stage completed at the selected 2e-4 under a fresh exact
authorization (scope digest `b4b5f1da…32f5a2`, code commit `13fbba4`):

| Run          | Steps | Tokens  | Best val loss | Last val loss |
| ------------ | ----- | ------- | ------------- | ------------- |
| `500k` @2e-4 | 32    | 200,874 | 3.8832        | 3.9076        |

Two launch-preparation bugs were fixed on the way (commits `0104b77`,
`13fbba4`): the suite policy lacked a `payload_access_500k` column, and the
candidate coherence gate wrongly required the suite report `first_stage` to
equal the run stage (it now pins `100k` and requires a
`payload_access_<stage>` string per family instead).

**Finding: the ladder is data-bound, not compute-bound.** The
OpenHands-Sampled lane converts to 6,055 examples but spans only 6
repositories; the repo-grouped split leaves a 202,162-token train split,
all of which the 500K run consumed in a single pass (the trainer does not
repeat epochs). The 500K ceiling — and every later ceiling — is
unreachable from this lane. A 2M run over the same lane would re-train the
identical shard, so it was deliberately not run. Before 2M is meaningful,
the later train families (`multi-swe-bench`, `open-swe-traces`, `swe-evo`)
need their own conversion lanes and a multi-lane candidate/authorization
redesign; the 2M falsification kill-gate additionally needs the four-variant
paired evaluation harness, which does not exist yet.

## The staged ladder from here

Roles are fixed by the suite policy
(`docs/data/training-readiness/pneuma-foundation-v0-suite.json`): only
`swe-gym-openhands-sampled` carries weight at 100K; `multi-swe-bench`,
`open-swe-traces`, `swe-evo` become gradient-eligible at LATER stages only
after their own readiness work; eval families (`swe-bench`, `swe-bench-pro`,
`swe-mera`, `swe-polybench`) and governance families (`swe-chat`,
`sec-bench-pro`) are never trained on.

1. **500K local** — same procedure as 100K with `--stage 500k` everywhere:
   prepare (twice, byte-identical) → candidate → finalize → preflight → train
   at the selected 2e-4. Evaluation stays smoke-only pre-2M.
2. **2M local** — the falsification kill-gate stage: requires the
   four-variant paired evaluation before 8M is reachable.
3. **Optional 2M cloud reproduction (RunPod)** — only after the local 2M
   gates pass and only with a fresh live quote. This is where the
   browser-driving agent earns its keep (see below).
4. **8M+ local or cloud** — gated on a ≥0.5-point held-out resolved-rate
   improvement per doubling; 8M cloud additionally needs ≥30.9 measured
   tokens/s and all-in budget fit.

## Exact per-stage command sequence (WSL)

Run from Windows via `wsl -d Ubuntu`, repo at `/mnt/c/pneuma-lab`, and use
`.venv/bin/python` (no activation needed). Replace `<stage>`:

```text
.venv/bin/python -m pneuma_lab.foundation prepare --stage <stage> --data-root /mnt/c/pneuma-data
.venv/bin/python -m pneuma_lab.foundation prepare --stage <stage> --data-root /mnt/c/pneuma-data   (must print identical hashes)
.venv/bin/python -m pneuma_lab.foundation authorization-candidate --stage <stage>
.venv/bin/python -m pneuma_lab.foundation authorization-finalize --candidate build/foundation/authorizations/candidates/<stage>.json --scope-digest <displayed> --approval-phrase "<displayed>" --operator-id student-operator
.venv/bin/python -m pneuma_lab.foundation preflight --stage <stage> --authorization build/foundation/authorizations/final/<stage>.json --lr 2e-4
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 .venv/bin/python -m pneuma_lab.foundation train --stage <stage> --authorization build/foundation/authorizations/final/<stage>.json --lr 2e-4
```

The cloud path (candidate `--profile cloud`, `cloud-bundle`, scp/ssh/tmux,
on-pod commands, terminate checklist) is `START-HERE-TRAINING.md` section 13,
verbatim — every command there parses against the real CLI.

## What the browser agent must do on RunPod (summary)

1. Log into a personal RunPod account; read the live On-Demand A40 48GB
   hourly quote and the tax-inclusive checkout total. The quote feeds
   `authorization-candidate --profile cloud` and `cloud-bundle` as
   `--quoted-hourly-usd` / `--quoted-tax-inclusive-usd`; the code gate
   refuses > $38 prepaid, > $45 lifetime tax-inclusive, auto-pay on, or a
   second lifetime cloud job.
2. Create the Pod: official PyTorch template, 30 GB container disk, 80 GB
   volume, 72-hour auto-termination, SSH enabled. No Jupyter workflow — the
   Pod runs the same CLI via SSH + tmux.
3. After the run: download `/workspace/pneuma-results.tar.gz`, then
   **Terminate Pod** and verify no stopped volume or running Pod remains
   (stopped volumes still bill).

Hard rules the gates enforce anyway: never upload `C:\pneuma-data` raw
content, never any `swe-chat`/`sec-bench-pro` bytes, no notebooks in the
bundle, no model weights in the bundle (the Pod re-downloads the pinned
snapshot), secrets never enter Git/bundles/logs.

## Machine-specific operational knowledge (hard-won; read before running)

- **WSL VM auto-shutdown kills detached work.** Any process started inside
  WSL dies shortly after the last `wsl.exe` client exits. Run `train`
  in the foreground of a live `wsl` invocation (a 100K run fits in 10
  minutes; budget stage runtime accordingly), or keep a separate `wsl`
  session open for the duration.
- **`$?` and `$(...)` get mangled through `wsl -- bash -c "..."` from Git
  Bash.** Check `wsl.exe`'s own exit code from the Windows side, or run
  script FILES (`wsl -d Ubuntu -- bash /mnt/c/path/script.sh`) with
  `MSYS2_ARG_CONV_EXCL='*'` set to stop Git Bash path conversion.
- **Line endings:** the repo sets `core.autocrlf=true` in `.git/config` so
  WSL git and Windows git agree. Do not remove it — the clean-checkout
  authorization gate reads `git status --porcelain` from WSL and 193 files
  go phantom-dirty without it.
- **Every commit invalidates the current authorization** (it binds the exact
  clean HEAD). The cycle after any code change: commit → `prepare` twice →
  `authorization-candidate` → `authorization-finalize` → `preflight` →
  `train`. Never quote an old scope digest; always use the freshly displayed
  one.
- **Throughput note:** transformers falls back to the torch implementation of
  the linear-attention kernels (`flash-linear-attention` and `causal-conv1d`
  are not installed). 312–339 tokens/s was measured WITH that fallback.
  Installing them before 2M+ may improve throughput; treat as an environment
  change (rerun doctor; it is not in the pinned lock, so decide deliberately).
- The evaluate/report CLI commands fail closed unless
  `<run>/validation_batches.json` exists; the runner currently persists only
  aggregate best/last validation loss in the manifest. Wiring per-batch
  validation persistence into the runner is the one known gap if formal
  `evaluate` artifacts are wanted for the LR selection already made above.
- The first failed attempt's artifacts (device-placement bug, since fixed)
  are archived at `build/foundation/runs/failed-first-attempt/` for audit.

## Budget posture

Local training is $0 and stays $0. The only money the current code can ever
approve is the one-time RunPod reproduction under the $45 lifetime cap. If a
larger cloud budget is wanted for 8M+ stages, that is a deliberate code and
schema change (`budget.py`, `foundation-training-authorization.schema.json`,
`cloud_bundle.py` quote gate) — make it an explicit reviewed commit, never a
workaround.
