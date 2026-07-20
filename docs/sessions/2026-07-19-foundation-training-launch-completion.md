# Session report: foundation training launch preparation completed

Date: 2026-07-19/20. Branch: `codex/foundation-training-launch-prep`.
Session tooling: Claude Code (Fable 5) continuing the Codex plan
`docs/superpowers/plans/2026-07-13-foundation-training-launch-preparation.md`.

This session picked the plan up after Task 6 (commit `e9044e2`) and completed
Tasks 7 through 16. Every implementation task went through the plan's
subagent-driven flow: implementer → spec-compliance review → code-quality
review, with review findings fixed and re-reviewed before the task closed.
Training was NOT started; the optimizer step count is zero.

## Commits (oldest first, all on this branch)

| Commit    | Task        | What                                                                                                                                                                                                                                                                                                               |
| --------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `b442739` | 6 (wrap-up) | Committed the in-flight environment hardening; fixed a real regression in `setup-linux.sh` (exact-match uv check could never pass against real `uv --version` output).                                                                                                                                             |
| `bff61c9` | 7           | Pinned 2B model cache (`model_cache.py`) + no-gradient dry run (`dry_run.py`) + `snapshot_path` support in `runtime.py`. Includes a root-caused Windows NTFS birth/ChangeTime asymmetry fix for receipt verification.                                                                                              |
| `4cb793a` | 7 review    | Short-write guard, public `canonical_json_bytes`, `qwen_smoke` marker deselect-by-default.                                                                                                                                                                                                                         |
| `93f0551` | 8           | Telemetry (`telemetry.py`), expanded `ResourceSample`/`ResourceGuard`, run-manifest schema 0.2.0, `RunManifestWriter`.                                                                                                                                                                                             |
| `bc0eb39` | 8 review    | NVML thermal-throttle bitmask classification (benign SwPowerCap/GpuIdle bits no longer pause runs); guard-reason constants schema-locked; disk-usage error wrapping.                                                                                                                                               |
| `244d862` | maintenance | Two pre-existing recursion-wrap tests made deterministic (CPython 3.12.13 raised the C-recursion limit; depth 2000 → 100000).                                                                                                                                                                                      |
| `f71241c` | 9           | Checkpoint format 0.2.0: `ResumeBindings`, `TrainingProgress`, safe-boundary validation, shared-core dedup, LoRA filtering, frozen-base refusal, full RNG capture, verify-before-mutate load, direction-aware retention. Bit-exact resume proven (resumed run with a different seed equals the uninterrupted run). |
| `79e9fb9` | 9 review    | Index written before pruning (crash-window fix), shape pre-check before mutation, fail-closed index parsing.                                                                                                                                                                                                       |
| `a830e5f` | 10          | `dataset.py` (TOCTOU-free hash-verified shard reader, one-document collator, `DeterministicSampler` with checkpointable cursor and complete-window/ceiling semantics) + weighted/masked `train_microbatch`.                                                                                                        |
| `26bf460` | 10 review   | Residency/sampler contract docstrings, strict `example_count` check.                                                                                                                                                                                                                                               |
| `f999ed4` | 11          | The gated runner (`runner.py`): exact preflight order, guarded allocation, safe-boundary loop, resume, SIGINT/SIGTERM pause, schema-valid manifests. Torch-free import proven.                                                                                                                                     |
| `036a8c3` | 12          | Claim-bounded evaluation + reports (`evaluation.py`, `reports.py`): stage-aware gates, CORE_LIMITS regression gate, LR selection, pre-write forbidden-phrase gate, `no_consciousness_claim` on every artifact.                                                                                                     |
| `fbbf734` | 12 review   | Documented the deliberate 1m ladder omission.                                                                                                                                                                                                                                                                      |
| `f92729b` | 11 review   | Terminal-manifest guarantee: transient telemetry failure → `missing_resource_sample` pause; unexpected exceptions still write a terminal manifest/event; finite unmeasured-loss sentinel; effective `data_loader_workers: 0`.                                                                                      |
| `9b86028` | 11 review   | Resume filter excludes the unmeasured sentinel.                                                                                                                                                                                                                                                                    |
| `3d037e7` | 13          | The complete CLI (`cli.py`, 14 commands, exact grammar, lazy imports, BLOCKED/exit-2, finalize path derivation, fail-closed evaluate contract).                                                                                                                                                                    |
| `5543fe5` | 13 review   | Central `ModelCacheError` → BLOCKED translation; `_checkpoint_learning_rate` fail-closed branch coverage; public `build_parser`.                                                                                                                                                                                   |
| `fbc3fe1` | 14          | Authorized-only cloud bundle (`cloud_bundle.py`), `CloudQuote`/`authorize_reproduction_quote` budget gate, `<stage>-cloud.json` finalization, authorization schema 0.3.0 (adds the cloud scope variant).                                                                                                           |
| `de3fc3c` | 15          | `START-HERE-TRAINING.md` operator guide (30 fenced commands, all parser-validated), `operator_guide.py` drift checker + CLI, `foundation_training_launch` truth block in project status (schema 0.2.0), local-first doc refresh.                                                                                   |
| `c392a90` | 16          | Real-corpus fix: identical duplicate eval identities (SWE-bench full vs Lite variant repeats, 730 ids) dedupe; conflicting repeats still fail closed.                                                                                                                                                              |
| `e2d6a31` | 16          | Real-corpus fix: eval-overlapping repositories (`getmoto/moto`, `conan-io/conan`, `pandas-dev/pandas`) are quarantined out of the training selection at split time (`eval-repo-overlap`), per the cross-dataset leakage registry rule; contamination receipt is now genuinely zero-finding.                        |
| `06dd790` | 16          | Examples artifact ceiling scaled to the full lane (conversion renders the whole lane before stage selection; 16 MiB real payload vs the old 12.8 MB stage-scaled cap).                                                                                                                                             |
| `2611fe8` | 16          | Authorization coherence re-derives the quarantine from bound eval identity payloads; shard records must join to unquarantined train assignments.                                                                                                                                                                   |
| `d972804` | 16          | Junction installer locates the decoder in the real multimodal checkpoint (`model.language_model.layers`).                                                                                                                                                                                                          |

Also: repo-local `core.autocrlf=true` was set in `.git/config` so WSL git and
Windows git agree on line endings (WSL git previously saw 193 phantom-dirty
files, which broke the clean-checkout authorization gate).

## Environment (verified working)

- WSL2 Ubuntu, `.wslconfig` = the reviewed example (24 GB RAM / 8 GB swap);
  `%UserProfile%\.wslconfig` did not previously exist.
- `.venv` at `/mnt/c/pneuma-lab/.venv` from `uv sync --python 3.12 --extra dev
--extra foundation --locked` with uv 0.11.28 (`build/uv-0.11.28/uv`).
- `python -m pneuma_lab.foundation doctor --profile local` → `READY`
  (Python 3.12.13, torch 2.13.0+CUDA, bf16, all pins exact, 7.96 GiB VRAM).

## Real artifacts produced (ignored `build/`, machine-local)

- `build/foundation/cache/models/2b/15852e8c…/` — pinned Qwen3.5-2B snapshot
  (4.3 GB, 9 files, hashed receipt, verified twice).
- `build/foundation/preparation/100k/` — the real 100K preparation, run twice
  with byte-identical CLI output both times: all receipts, eval identity
  indexes, and the content-addressed shard
  `shards/8e10bd50….jsonl` (regenerated after the final commits; see the
  preparation manifest for the exact digest of record). Selection: 2,438
  candidate train records after quarantine → 507 selected, 99,894 / 100,000
  tokens, 40 resolved + 467 unresolved, persisted weight 0.0.
- `build/foundation/authorizations/candidates/100k.json` — candidate bound to
  the final clean commit; `authorization_status: "candidate"`; lane weights
  exactly `{"swe-gym-openhands-sampled": 1.0}`; $0 paid compute.
- `build/foundation/dry-run/100k/dry-run-report.json` — REAL GPU dry run:
  parity `max_absolute_error: 0.0` across the five cache-boundary cases,
  latency overhead −5.3% (limit +25%), zero gradients, no optimizer, junction
  contract verified (latent 256, 64 slots, 2 candidates, 4 microsteps,
  layer 19).

## Verification results

- Full WSL suite: **1888 passed, 3 skipped, 1 deselected** (the deselected
  test is the opt-in `qwen_smoke`, which was run explicitly and **passed**
  against the real cached snapshot).
- `python -m pneuma_lab.status --check` → PASS.
- `python -m pneuma_lab.dataset_readiness --check` → PASS.
- `python -m pneuma_lab.foundation.operator_guide START-HERE-TRAINING.md` →
  valid, no unknown or missing commands.
- `git diff --check` clean; working tree clean.

## Corpus findings future sessions should know

- `processed/swe-bench/normalized_metadata.jsonl` concatenates SWE-bench full
  and SWE-bench Lite; 730 task ids repeat with identical retained identity.
- The OpenHands-Sampled lane spans 11 repos; `getmoto/moto` and
  `conan-io/conan` also appear in SWE-MERA, and `pandas-dev/pandas` and
  `conan-io/conan` in SWE-bench's train split. Those three repos (2,440 of
  6,055 traces) are quarantined out of training selection.
- The pinned Qwen3.5-2B checkpoint loads as
  `Qwen3_5ForConditionalGeneration` with the text decoder at
  `model.language_model.layers` (vision tower alongside), and transformers
  falls back to the torch implementation of the linear-attention kernels
  (flash-linear-attention / causal-conv1d are not installed — acceptable for
  the 100K smoke; consider them for throughput at later stages).

## Exact remaining steps (operator)

Everything is prepared. `START-HERE-TRAINING.md` sections 8–11 are the
runbook; concretely, in WSL (`wsl -d Ubuntu`, `cd /mnt/c/pneuma-lab`):

1. `.venv/bin/python -m pneuma_lab.foundation authorization-candidate --stage 100k`
   — review the printed scope, digest, and approval phrase.
2. `.venv/bin/python -m pneuma_lab.foundation authorization-finalize
--candidate build/foundation/authorizations/candidates/100k.json
--scope-digest <displayed digest> --approval-phrase "<displayed phrase>"
--operator-id student-operator`
3. `.venv/bin/python -m pneuma_lab.foundation preflight --stage 100k
--authorization build/foundation/authorizations/final/100k.json --lr 5e-5`
4. `.venv/bin/python -m pneuma_lab.foundation train --stage 100k
--authorization build/foundation/authorizations/final/100k.json --lr 5e-5`
   — the first authorized optimizer step. Repeat for `--lr 1e-4` and
   `--lr 2e-4`, then `evaluate`/`report` per guide section 12.

Do not commit tracked changes between finalization and training — the
authorization binds the exact clean commit. The optional RunPod path is guide
section 13 and stays gated behind its own cloud authorization and the $45
lifetime cap.
