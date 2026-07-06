# manager-data-pipeline

Local pipeline that turns a raw Claude Code log snapshot into an ML-dataset-shaped
corpus of **manager decision points** — the training substrate for a future
"9to5 Manager Model" that decides what a manager/orchestrator should do next
(continue, run tests, spawn a verifier, ask the user, stop, etc.).

> ⚠️ **Data is intentionally NOT in this repo.** The raw snapshot contains
> credentials and full private logs; the derived datasets are multi-GB,
> redacted-but-private content. Everything under `manager_data/{raw,normalized,
> datasets,manifests,reports}/` is `.gitignore`d. This repo holds **only the
> pipeline source and planning docs.** Never commit anything under those data dirs.

## Repository layout (tracked)

```
*.py                              # early pipeline stages (snapshot, inventory, taxonomy, schema profiling)
manager_data/scripts/*.py         # Steps 5–9 scripts (normalize, reconstruct, consolidate, audit, eval, validate)
step4.md … step9_plan.md          # per-step task briefs / specs
.gitignore                        # keeps all data + secrets out of git
README.md
```

Data directories (gitignored, recreated locally by running the scripts):
`manager_data/raw/` · `manager_data/normalized/` · `manager_data/datasets/` ·
`manager_data/manifests/` · `manager_data/reports/`.

## Pipeline stages

| Step | Script(s) | Output (gitignored) |
|---|---|---|
| 1 Snapshot | `snapshot_claude_raw.py` | immutable raw `.claude` snapshot |
| 2 Inventory | `snapshot_inventory.py` | file inventory + report |
| 3 Source taxonomy | `source_taxonomy.py` | per-file category manifest |
| 4 Event schema profiling | `event_schema_profile.py` | schema variant profile |
| 5 Canonical normalization | `manager_data/scripts/normalize_events.py`, `validate_normalized_events.py` | `normalized/events.jsonl` (one `manager_event_v1` row per raw line) |
| 6 Reconstruction plan | (planning doc) | — |
| 7 Session/workflow/tool reconstruction | `reconstruct_sessions.py`, `validate_session_reconstruction.py` | session/workflow/tool-trajectory indexes + candidate episodes |
| 8 Decision points + weak labels | `consolidate_manager_episodes.py`, `validate_manager_decision_points.py` | `manager_decision_points.jsonl`, action labels, review queue, eval splits |
| 9 Audit + eval cases + baselines | `audit_manager_decision_dataset.py`, `build_manager_eval_cases.py`, `evaluate_manager_baselines.py`, `validate_manager_eval_cases.py` | eval cases, human review pack, audit + baseline reports |
| 10 Gold seed + labeling protocol | *(planned — see below)* | gold review seed, labeling template/guide, balanced diagnostic split |

Every stage is read-only over `raw/`, streams line-by-line (data is large),
redacts secrets to placeholders (`[REDACTED:*]`, `<USER_HOME>`), preserves
`event_id` lineage, and ships a paired `validate_*.py` that scans outputs for
unredacted secrets and confirms raw is never reopened.

## Current state (after Step 9, all validations PASS)

- 460,762 normalized events → 33,168 weak-labeled decision points → 33,168 eval cases.
- Eval splits are **project-level, leakage-safe** (train/val/test = 19,910 / 5,402 / 7,856 DPs).
- Human review pack: 3,161 stratified items.

**Known issues blocking model training (the focus of Step 10):**
- Labels are **weak/heuristic, not gold** (52% low-confidence; `retry` is 32.5%; class imbalance ≈193×).
- Test split is **92.3% one project** (`C--9to5`); `inspect_diff` missing from validation.
- 3 enum actions (`spawn_specialist`, `reroute`, `reject_completion`) were **never produced** by the heuristics.
- Strong baselines are **circular** (re-derive the labels) → not evidence of real manager correctness.

## Step 10 (planned — not yet executed)

**Gold Review Set Construction, Split Rebalancing, and Human Labeling Protocol.**
Build a ~400-case, action-stratified, project-balanced **gold review seed** from the
review pack + eval cases (multi-annotator with inter-annotator agreement, plus a
discovery bucket for the 3 never-produced actions), a labeling template + guide,
and a leakage-safe **balanced diagnostic split** — all so humans can produce true
gold labels **before any training**. No model training, fine-tuning, or deployment
happens until gold labels exist.

## Manager action enum

`continue` · `ask_user` · `spawn_verifier` · `spawn_specialist` · `run_tests` ·
`inspect_diff` · `retry` · `reroute` · `stop_task` · `summarize_state` ·
`accept_completion` · `reject_completion` · `escalate_risk`

Families (7, matching `ACTION_FAMILY` in `consolidate_manager_episodes.py`):
**control** (continue, summarize_state) · **interaction** (ask_user) ·
**verification** (spawn_verifier, run_tests, inspect_diff) · **recovery** (retry,
reroute) · **completion** (accept_completion, reject_completion) · **risk**
(stop_task, escalate_risk) · **delegation** (spawn_specialist).

## Running

Scripts use `pathlib`/`json`/`hashlib`/`argparse` + Rich progress bars; run with
Git Bash / Linux-style commands. Each script's module docstring documents its
exact CLI. Run a stage's `validate_*.py` after it.
