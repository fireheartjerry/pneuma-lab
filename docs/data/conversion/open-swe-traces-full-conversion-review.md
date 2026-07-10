# Open-SWE-Traces Conversion Review

Reviews the stage-1 adapter + stage-2 converter over **real** Open-SWE-Traces
parquet rows. Representative run: one full shard
(`minimax_m25_openhands_trajectories/train-00000-of-00020`, 2,500 rows). No
training, no runtime change, no committed data — all artifacts under ignored
`build/`.

## Adapter (stage 1: parquet -> PneumaTrace)

| Metric                              |   Value |
| ----------------------------------- | ------: |
| Source rows                         |   2,500 |
| Valid traces                        |   1,960 |
| Skipped (`resolved == -1`, unknown) |     540 |
| Invalid (schema/consistency)        |       0 |
| Total agent steps                   | 113,361 |

Every trace passes envelope schema + `consistency_errors` (agent-trace frames
require a real trajectory; step counts reconcile). `resolved` is mapped
`1 -> True`, `0 -> False`; the 540 `-1` rows are skipped, never coerced —
consistent with the honest-outcome rule.

## Converter (stage 2: PneumaTrace -> PneumaTrainingExample)

| Metric                |             Value |
| --------------------- | ----------------: |
| Traces read           |             1,960 |
| Examples emitted      |             1,960 |
| Invalid / quarantined |                 0 |
| Resolved / unresolved |       826 / 1,134 |
| Count reconciliation  | reconciled = true |

Each example is schema-valid, passes the governance leakage scan (digest-only
input, no raw text/identifiers, `resolved` never echoed into input), and
carries `label_provenance.kind = constructed_label` at `confidence: medium`,
`model_use_tier = train_after_adapter`, `training_weight = 0.0`. The
Minimax/Qwen output-ToS caveat rides in `blocked_training_uses` and the
conversion-report `warnings`.

## Class balance vs Dataset #1

Among convertible rows (~79% of the corpus), ~**42% are resolved-true** — far
healthier than Dataset #1's ~8%. The dominant-class imbalance that Dataset #1
must handle is not a blocker here.

## Full-corpus status

Full 84-shard conversion is now **practical via per-shard streaming** and tested,
but is **left un-run to completion** this pass (its ~7.5GB output is ignored
build, not committed, and correctness is already proven representatively).

- `adapters.open_swe_traces.run_streaming` (CLI `--stream`) processes one shard
  at a time, appending traces incrementally, so peak memory is ~one shard
  (~90MB) instead of the whole corpus (~7.5GB). The old single-batch `run()`
  held everything in memory (~7.5GB) — that was the impracticality.
- A determinism test asserts streaming output is **byte-identical** to the
  in-memory `run()` over the same shard definitions; a real 2-shard smoke
  confirms the parquet path (100 rows -> 86 traces, 14 `-1` skips).
- The converter already streams line-by-line over the trace JSONL, so the full
  pipeline is memory-bounded end to end.

To run it for real: `python -m pneuma_lab.adapters.open_swe_traces --stream
--out build/adapters/open-swe-traces/full` then the converter in `--mode full`
over that output.

## Determinism & provenance

Canonical JSON, identity ids, synthetic-ordinal timestamps, content hashes;
`--emit-fixture` guards the golden fixture against drift. Raw trajectory/tool/
patch text never enters a frame or an example; only `provenance.source_id`
retains the raw join key.
