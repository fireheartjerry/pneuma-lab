# SWE-Gym Dataset Acquisition Spike

Status: **complete** (acquisition + inspection). Date: 2026-07-07.
Scope: acquire SWE-Gym locally, inspect real shape, verify provenance/licensing,
produce an inventory. **No adapter, no schema, no training** — those are later
phases. This spike exists so the Phase-3 adapter is designed against the _real_
observed dataset structure rather than guesses.

## Where the data lives (outside the repo)

Raw corpora live under `C:\pneuma-data` (`/c/pneuma-data`), never inside
`C:\pneuma-lab`. `.gitignore` guards against accidental in-repo copies.

```
/c/pneuma-data/
  raw/swe-gym/<Dataset>/...        # parquet / jsonl as published on HF
  samples/swe-gym/tasks/*.json     # 10 provenance-tagged task records
  samples/swe-gym/trajectories/*.json  # 3 provenance-tagged trajectory records
  samples/swe-gym/PROVENANCE.json
  manifests/swe_gym_inventory.json # machine-readable inventory (source of truth)
  processed/swe-gym/               # empty; reserved for Phase-3 adapter output
  logs/                            # acquire logs + download scripts + stats
```

## Provenance & licensing

- **Project**: SWE-Gym — <https://github.com/SWE-Gym/SWE-Gym> (code Apache-2.0).
- **Paper**: _Training Software Engineering Agents and Verifiers with SWE-Gym_,
  ICML 2025 — <https://arxiv.org/abs/2412.21139>.
- **Lineage**: SWE-Bench data-collection procedure over 11 Python repos
  (getmoto/moto, python/mypy, iterative/dvc, Project-MONAI/MONAI, pydantic,
  dask, conan, hydra, pandas, modin, bokeh).
- **Data licenses (HF cards)**: `SWE-Gym` and `OpenHands-SFT-Trajectories` are
  **MIT**. The other dataset cards leave `license` unspecified (treat as
  inheriting the project's terms; underlying repo code stays under each source
  repo's own license — relevant once repo snapshots are fetched for execution).
- All datasets are **public and ungated** on Hugging Face (`SWE-Gym` org).
- Exact HF commit SHAs per dataset are recorded in the inventory JSON.

## How it was acquired

Direct HTTPS pulls from HF `resolve/main` endpoints (`curl`), no HF cache/token,
so bytes land under `/c/pneuma-data` only. Scripts:
`/c/pneuma-data/logs/bulk_download2.sh` (parquet corpora + moatless JSONL).
Total **1.24 GB**, **81,338 rows** verified by loading every file.

| Dataset                                 | Kind       | Rows (verified) | Format  | Local MB |
| --------------------------------------- | ---------- | --------------: | ------- | -------: |
| SWE-Gym/SWE-Gym                         | task       |           2,438 | parquet |       42 |
| SWE-Gym/SWE-Gym-Lite                    | task       |             230 | parquet |      0.9 |
| SWE-Gym/SWE-Gym-Raw                     | task       |          64,689 | parquet |      695 |
| OpenHands-SFT-Trajectories              | trajectory |             491 | parquet |       10 |
| OpenHands-Sampled-Trajectories          | trajectory |           6,055 | parquet |      288 |
| OpenHands-Verifier-Trajectories         | trajectory |           5,272 | parquet |      114 |
| MoatlessTools-Agent-Verifier-Train-Data | trajectory |           2,163 | jsonl   |       32 |

Referenced-only (README pulled, bulk data left on HF):
`MoatlessTools-Sampled-Trajectories` (~5.5 GB), `Codebase-Index-Lite`.

## What was inspected

**Task record** (`SWE-Gym-Lite`, SWE-Bench-shaped) — columns:
`instance_id, hints_text, patch, test_patch, created_at, problem_statement,
repo, base_commit, version, PASS_TO_PASS, FAIL_TO_PASS`. Confirmed on a real
row (`getmoto__moto-5752`): natural-language `problem_statement`, gold `patch`,
`test_patch`, and explicit `FAIL_TO_PASS` / `PASS_TO_PASS` test-id lists.

**Trajectory record** (`OpenHands-SFT-Trajectories`) — single column `messages`:
a list of `{role, content}` chat turns. Real example had 29 messages, role
sequence `system → user → assistant → user → …`, assistant turns emitting
tool calls (`execute_bash`, `str_replace_editor`) and user turns carrying
observations. Moatless variants are OpenAI-format `*.openai.jsonl`.

## Candidate Pneuma frame mapping (NOT yet formalized)

| Pneuma frame      | SWE-Gym task fields              | SWE-Gym trajectory fields             |
| ----------------- | -------------------------------- | ------------------------------------- |
| `WorldFrame`      | `repo`, `base_commit`, `version` | user turn embeds repo path + PR text  |
| `AgentTraceFrame` | gold `patch`, `test_patch`       | `messages[]` (actions + observations) |
| `MemoryFrame`     | `hints_text`                     | prior turns as accumulated context    |
| `GovernanceFrame` | `problem_statement` (task spec)  | `messages[0]` system/tool contract    |
| `OutcomeFrame`    | `FAIL_TO_PASS`, `PASS_TO_PASS`   | success encoded in split name         |

`instance_id` is the stable join key across tasks ↔ trajectories ↔ outcomes.

## What remains unknown / missing

- **Execution not run.** `FAIL_TO_PASS`/`PASS_TO_PASS` are test-id _lists_, not
  observed pass/fail results. Producing real outcomes needs the SWE-Gym /
  SWE-Bench per-instance **Docker images** — not built in this spike.
- **No repo snapshots locally** — rows carry `repo` + `base_commit` only; source
  trees are external (fetched at execution time).
- Trajectory ↔ task linkage exists via the embedded repo/PR but has not been
  parsed into an explicit `instance_id` join yet.
- Moatless verifier example counts are not on the HF card (verified locally: 2,163).

## Next recommended adapter design (Phase 3, not started)

1. Read parquet with pyarrow; stream rows (Raw is 64k rows / 695 MB).
2. Deterministic `instance_id`-keyed loader emitting draft `WorldFrame` /
   `GovernanceFrame` / `AgentTraceFrame` / `MemoryFrame` / `OutcomeFrame`.
3. Parse OpenHands `messages` into per-step `AgentTraceFrame`s (map tool calls to
   actions, tool results to observations); join to tasks by repo+PR → `instance_id`.
4. Keep `OutcomeFrame` honest: mark test outcomes _unverified_ until a Docker
   execution seam exists. Do not synthesize pass/fail.
5. Write normalized frames to `/c/pneuma-data/processed/swe-gym/`; never commit them.

## Verify locally (offline)

```
python scripts/verify_swe_gym_sample.py
```

Confirms samples + inventory exist, prints counts and disk usage, validates the
inventory JSON. No network required.
