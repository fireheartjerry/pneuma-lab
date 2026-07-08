# Full SWE Dataset Suite — Acquisition & Preprocessing Spike

Status: **complete** (acquisition + load-verification + inventory + normalized
metadata). Date: 2026-07-07. Scope: acquire the 10-dataset SWE suite from the
deep-research report, verify provenance/licensing, load-verify every parquet /
jsonl / csv / json with real row counts, extract samples, and build canonical
inventories. **No ML training, no full adapter, no 9to5 changes.** This exists so
the Phase-3 adapter is designed against real observed structure.

Companion: [`swe-gym-spike.md`](swe-gym-spike.md) (the original SWE-Gym-only spike).

## Where the data lives (outside the repo)

All corpora live under `C:\pneuma-data` (`/c/pneuma-data`), never in the repo.
`.gitignore` guards against accidental in-repo copies.

```
/c/pneuma-data/
  raw/<dataset>/<hf-repo-leaf>/...        # exact HF files (parquet/jsonl/csv/json)
  processed/<dataset>/                     # normalized_metadata.jsonl, file_index.jsonl,
                                           #   row_counts.json, samples.jsonl, provenance.json
  samples/<dataset>/samples.jsonl          # 5-20 provenance-tagged sample records
  manifests/<dataset>_inventory.json       # per-dataset inventory (spec schema)
  manifests/global_inventory.json          # roll-up
  manifests/provenance_dossiers.json       # pinned SHAs + frame maps (9 research agents)
  logs/                                    # acquisition scripts + logs + venv
```

## Suite summary (verified by loading every file)

Total local: **10 groups, 8,521,307 verified rows across 37,711 structured-data
files, ~46 GB** (all 10 downloaded; ~58 GB on disk incl. `.log`/`.zip` artifacts
not row-parsed). `dev`/`test`/`train` etc. all counted. **SWE-chat was acquired
manually** (HF token + accepted terms) and is now local.

| Dataset                                  | Status     |      Rows |  Files |    Size | License (data)              |
| ---------------------------------------- | ---------- | --------: | -----: | ------: | --------------------------- |
| SWE-Gym (+trajectories)                  | downloaded |    81,338 |     19 | 6.7 GB¹ | MIT / Apache-2.0            |
| Multi-SWE-bench / RL / mini / trajs      | downloaded |   10,399² |    162 | 24.0 GB | Apache-2.0 / CC0 / other    |
| SWE-bench family (core/Lite/Verified/MM) | downloaded |    22,962 |      8 |  119 MB | MIT harness; mixed upstream |
| SWE-MERA (official + mirror)             | downloaded |     7,610 |      5 |  444 MB | MIT (paper CC-BY)           |
| SWE-EVO (core + full trajectory logs)    | downloaded |   32,211³ | 31,647 |   16 GB | Apache-2.0 (code MIT)       |
| SWE-PolyBench (full/500/Verified)        | downloaded |     2,992 |      3 |  124 MB | MIT                         |
| SWE-bench Pro (public + mirror)          | downloaded |     2,924 |      4 |   75 MB | MIT code / CC-BY paper      |
| SEC-bench (base/Seed/**Pro**)            | downloaded |     1,264 |      5 |   13 MB | MIT / Apache-2.0            |
| Dialogue SWE-Bench                       | downloaded |       550 |      2 |  2.3 MB | unspecified (paper CC-BY)   |
| SWE-chat (6 tables + 5,850 transcripts)  | downloaded | 8,359,057 |  5,856 | 11.9 GB | odc-by (acquired manually)  |

¹ SWE-Gym raw dir is ~6.7 GB incl. the 5.5 GB Moatless-Sampled zips; the
`swe-gym_inventory.json` row count (81,338) covers loadable parquet/jsonl only
(zips are archives, not row-parsed). ² Multi-SWE row count is over the loadable
JSONL (bench+RL+mini); `_trajs` are ZIP archives (not row-parsed). The Multi-SWE-RL
corpus is fully present (23.87 GB, 130/130 files, incl. the single 17 GB
`microsoft__TypeScript` RL file). ³ SWE-EVO is **fully downloaded** — core
benchmark (48 tasks) + all OpenHands (32,160) and SWE-agent (3,595) trajectory
logs = 35,761 files / 16 GB on disk; the 32,211 counted rows are the structured
json/jsonl portion (~8.3 GB), the rest are `.log` agent-trace files not row-parsed.

## Provenance (pinned revisions)

Every dataset's official GitHub repo (+ HEAD SHA), HF repo IDs (+ revision SHA),
paper/arXiv, license, and Pneuma frame-mapping are captured in
`manifests/provenance_dossiers.json` and merged into each `<dataset>_inventory.json`.
Highlights (arXiv): SWE-Gym 2412.21139 (ICML'25), SWE-bench 2310.06770 (ICLR'24),
Multi-SWE-bench 2504.02605, SWE-PolyBench 2504.08703, SWE-bench Pro 2509.16941,
SWE-MERA 2507.11059 (EMNLP'25), SWE-EVO 2512.18470, SEC-bench 2506.11791 (NeurIPS'25)

- SEC-bench Pro 2605.26548, Dialogue SWE-Bench 2606.13995, SWE-chat 2604.20779.

## Acquired-with-caveats / partially-unavailable (recorded, not faked)

- **SWE-chat** (`SALT-NLP/SWE-chat`, odc-by): HF-gated (token + accepted terms).
  **Acquired manually** — now local (11.9 GB: 6 parquet tables incl.
  conversations 2.69M rows + commits w/ authorship, and 5,850 session transcripts;
  8.36M total rows). Privacy-sensitive real-user data — gate `has_security_sensitive`
  / PII handling before any redistribution.
- **SWE-bench Pro** held-out (12 repos) + commercial (18 repos): withheld by design;
  only the 731-instance public split is acquirable (and acquired).
- **SWE-EVO**: fully pulled (16 GB, 35,761 files — core + all trajectory logs).
  Note: the repo is 17 GB, not the ~7 GB the research report estimated.
- **Intelligent-Internet SWE-bench-Pro trajectories**: HF auto-gated → not pulled.
- **SWE-EVO-LongChain-50-images** (~269 GB Docker tars): out of scope (not pulled).

## Acquisition method & reliability notes

- Primary path: `huggingface_hub.snapshot_download` pinned to agent-verified
  revisions (`logs/hf_snapshot_download.py`).
- The `hf-xet` Rust transfer client hit a `brotli DecodingError` on 3 repos
  (Multi-SWE-RL, SWE-EVO, SEC-bench). Fix: an **isolated `dlvenv`** with `hf-xet`
  removed (plain httpx/gzip path) + a `curl -C -` byte-resumable fallback
  (`logs/download_resumable.py`) for the 17 GB single file. Large downloads were
  run in foreground windows (background jobs are reaped when the session idles).
- Row counts use fast paths (parquet metadata, CSV-aware record counting so
  patch newlines don't inflate counts); per-file normalization is capped at 25k
  rows for very large files (full row counts still recorded).

## Candidate Pneuma frame mapping (per dataset, not yet formalized)

`usefulness_for_pneuma` in each inventory maps native fields → frames. Recurring
pattern: `WorldFrame`←repo/base_commit/problem_statement; `AgentTraceFrame`←gold
patch or agent `messages`/trajectory logs; `MemoryFrame`←hints_text or synthesized
motifs; `GovernanceFrame`←FAIL_TO_PASS/PASS_TO_PASS test oracle or dialogue policy;
`OutcomeFrame`←test pass/fail deltas (or Fix Rate for SWE-EVO, commit-survival for
SWE-chat). `instance_id` is the cross-corpus join key.

Signal fit (from the research report): executable/trajectory corpora (SWE-Gym,
Multi-SWE-RL, SWE-EVO logs) → `predicted_error`, `expected_loss`, `scar_motifs`,
`control_pressure`. Dialogue/human corpora (SWE-chat, Dialogue SWE-Bench) →
`authority_request`, `grounded_self_report`, `operator_attention_pressure`.
Contamination-resistant sets (SWE-MERA, SWE-bench Pro, SWE-EVO, SEC-bench) → held-out
evaluation/calibration, **not** training-motif mining. `affect_manifold` has no
direct label anywhere — must be inferred from proxies (failure streaks, reverts,
interruptions).

## Risks / caveats

- **License heterogeneity**: dataset cards ≠ upstream repo licenses; several cards
  omit an explicit license. Metadata/patches are redistributed under mixed upstream
  terms — needs review before any redistribution beyond local research.
- **Contamination / weak tests** in SWE-bench family (solution leakage ~1/3 Verified;
  weak oracles) — use for representation/motif mining, not gold judgment labels.
- **SEC-bench dual-use**: security vulnerability metadata only; **no PoC executed or
  reproduced**. `description`/`bug_report`/`patch` fields need gating/redaction before
  any pass-through.
- **Dynamic datasets** (SWE-MERA, SWE-chat): counts drift; revisions are pinned.

## Next recommended step (Phase 3 adapter — not started)

Build a `PneumaTrace` container adapter (per the report's schema) that reads
`processed/<dataset>/normalized_metadata.jsonl` + raw files, keyed by `instance_id`,
emitting draft `WorldFrame`/`GovernanceFrame`/`AgentTraceFrame`/`MemoryFrame`/
`OutcomeFrame`. Keep `OutcomeFrame` honest (tests are id-lists, not executed —
no Docker built). Start with SWE-Gym + SWE-bench (P0), then Multi-SWE-bench,
then dialogue corpora; reserve SWE-MERA/Pro/EVO/SEC-bench for held-out evaluation.

## Verify locally (offline)

```
python scripts/verify_local_datasets.py        # global roll-up, no network
python scripts/verify_swe_gym_sample.py         # SWE-Gym-specific
```
