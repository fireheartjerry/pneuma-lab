# Open-SWE-Traces Training Readiness

Status: **adapter + converter + bounded-real conversion + bounded split done;
full conversion gated (available, not run); training not authorized.**

This package brings Dataset #2 (`open-swe-traces`) onto the exact Dataset #1
(`swe-gym-openhands-sampled`) two-stage pipeline so both feed one future
`PneumaBrain-v0` through the same canonical `PneumaTrainingExample` contract.
It authorizes no training. See `open-swe-traces.json` for the machine-readable
manifest.

## Pipeline parity

| Stage                                      | Dataset #1                                 | Dataset #2 (this lane)                      |
| ------------------------------------------ | ------------------------------------------ | ------------------------------------------- |
| Stage 1 adapter (parquet -> PneumaTrace)   | `adapters/openhands_sampled.py`            | `adapters/open_swe_traces.py`               |
| Stage 2 converter (PneumaTrace -> example) | `converters/openhands_sampled_training.py` | `converters/open_swe_traces_training.py`    |
| Split generator                            | `training/splits.py`                       | `training/splits.py` (shared)               |
| Leakage checker                            | `training/governance.py`                   | `governance/open_swe_traces.py`             |
| Cross-dataset leakage                      | (n/a yet)                                  | `training/leakage_registry.py` (foundation) |

Both lanes emit the same `TrajectoryExample` / `RISK_PREDICTION` shape with
`model_use_tier: train_after_adapter` and `training_weight: 0.0`.

## What is different from Dataset #1 (and why)

1. **Digest-only end to end.** Open-SWE-Traces frames and labels never carry
   raw `repo`/`instance_id`/`trajectory_id` — only `sha256:` digests. The world
   frame objective is a digest (`text_sha256` + `text_length`), never the raw
   task text (Dataset #1 embeds redacted task text; this lane is stricter). The
   only raw join key lives in `provenance.source_id`, the sanctioned traceback
   field. Raw trajectory/tool/patch **text never enters a frame** — the
   trajectory extractor and patch stats keep digests + lengths only.
2. **`resolved` is `constructed_label`, never `harness_outcome`.** The verifier
   outcome is automated over synthetic Minimax-M2.5 / Qwen3.5 trajectories.
   `confidence` is capped at `medium`. This is mechanically enforced by
   `governance.validate_label_provenance`.
3. **`resolved` is a tri-state int (`-1 / 0 / 1`).** `1 -> True`, `0 -> False`;
   `-1` (~21% of rows) is an unknown/unevaluated verifier state and is
   **skipped**, never coerced. The onboarding doc's "112,002 true / 95,487
   false = 207,489" figure silently bucketed the `-1` rows; the adapter report
   records the honest per-run 1/0/-1 split instead.
4. **Minimax/Qwen output ToS.** Carried in every example's
   `blocked_training_uses` and in the conversion report `warnings`; it must be
   resolved or signed off before any training authorization.

## Conversion evidence (this pass)

- **Stage-1 adapter** validated on real parquet rows: one full shard
  (`train-00000-of-00020`, 2,500 rows) -> **1,960 valid traces**, 540 skipped
  (`resolved == -1`), 0 invalid, in ~24s (~89MB of processed traces).
- **Bounded-real conversion**: 20 processed traces -> 20 `PneumaTrainingExample`
  records, schema + leakage + label-provenance clean, written under `build/`.
- **Bounded split manifest**: 20 examples, 20 repo groups, train/val/test =
  14/3/3, ~40% resolved-true, `training_authorization: not_authorized`.
- **Full conversion** is implemented and gated behind
  `--confirm-full-conversion` but **not run**: ~33 min and ~7.5GB of ignored
  `build/` output across all 84 shards is impractical for this pass.

All generated artifacts live under ignored `build/` and are not committed.

## Real class balance

Across four sampled shards, convertible rows (`resolved in {0,1}`, ~79% of
rows) are ~**41% resolved-true** — far better balanced than Dataset #1's ~8%.
This removes Dataset #1's dominant-class imbalance blocker but does not remove
any authorization gate.

## Gates before training

Full corpus conversion reproducible; full-corpus split reviewed; leakage scan
passing; **cross-dataset leakage registry populated and disjoint (or
quarantined)**; **Minimax/Qwen output ToS resolved**; class balance + baseline
metrics specified; objective approved; `model_use_tier` promoted via an
approved manifest; outputs restricted to approved paths; no runtime
integration. Until all hold, `training_authorization` stays `not_authorized`
and `training_weight` stays `0.0`.
