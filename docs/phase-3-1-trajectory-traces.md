# Phase 3.1 — Trajectory-Bearing PneumaTrace (v0.2)

**Status:** implemented. Adapter: `pneuma_lab.adapters.openhands_sampled`.
Envelope contract: `schemas/pneuma-trace.schema.json` v0.2.0.

## What changed and why

Phase 3 traces were task-only: a real world-frame + minimal governance-frame,
no agent cognition, because no agent ran. Phase 3.1 admits **real recorded
agent trajectories** (OpenHands sampled runs over SWE-Gym) and emits
AgentTraceFrames — but only under a hard honesty contract:

```text
real recording -> observable events -> AgentTraceFrame
no recording   -> no agent_trace frame, ever
```

The point is to give estimators (Phase 4) real behavioral sequences with real
outcome labels (`resolved`), without fabricating a single bit of cognition.

## Envelope v0.2 schema changes

- `schema_version`: enum `["0.1.0", "0.2.0"]` — every existing v0.1 task-only
  trace remains valid unchanged (that IS the migration path; no rewrite).
- New optional `trajectory` block (required fields: `present` (const true),
  `source_kind`, `agent_run_id`, `num_messages`, `num_agent_steps`,
  `timestamp_provenance`). Present **iff** the trace was built from a real
  recording.
- New optional `outcome` block (`kind`, `resolved`, plus harness report
  booleans and patch digest). Observed execution result — label material for
  the RSI loop, never a psyche judgment.

## Anti-fake-cognition gate (code, not prose)

`envelope.consistency_errors(trace)` enforces what JSON Schema cannot:

1. `agent_trace` frames ⟺ `trajectory` block ⟺ `labels.has_trajectory` —
   all three or none.
2. `trajectory.num_agent_steps` == count of emitted agent_trace frames.
3. `build.frame_sources["agent-trace-frame"]` must declare
   `dataset-derived-trajectory`; same rule for memory frames. An undeclared
   cognition-bearing frame is rejected as fabricated.

Both adapters route every emitted trace through this gate; failures land in
`pneuma_traces.invalid.jsonl` (quarantine), never in the valid stream.

## Event extraction rules (`adapters/trajectory.py`)

One AgentTraceFrame per assistant step. Every field is observable:

| field                                               | grounding                                                                                      |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `tool_calls[].tool` / `args_digest` / `args_length` | the call the agent actually issued (args hashed, never embedded)                               |
| `observations[]`                                    | sha256 + length + lexical `error_marker` of each tool output                                   |
| `retry_count`                                       | count of immediately-preceding identical (tool, args_digest) action sets                       |
| `strategy_switches`                                 | cumulative count of observable action-set changes                                              |
| `assistant_text_sha256` / `_length`                 | digest of the agent's visible message                                                          |
| `selected_action`                                   | tool names, or "assistant message" — never inferred intent                                     |
| `phase`                                             | `execution` iff a tool call was issued, else `other` — observational, not a mental-state guess |

Omissions are deliberate: no `self_reported_confidence`, no `current_plan`,
no `assumptions` — the OpenHands recordings do not surface them, so the
frames do not contain them. Absent observable ⇒ absent field.

### Timestamps

The recordings carry no wall-clock. Frame timestamps are **synthetic-ordinal**
(epoch base + step index), declared per-frame (`timestamp_provenance`) and in
the trajectory block. Order is real; time is not observed; nothing pretends
otherwise.

## Privacy rules

- Raw message/tool text NEVER enters frames — digests + lengths only. Raw
  bytes stay in the source parquet, reachable via provenance.
- The one embedded text (world-frame objective = the task text the agent
  actually saw) passes deterministic redaction (emails, GitHub/AWS/Slack
  tokens, private-key blocks, bearer tokens, assigned secrets). The redaction
  ledger records kind+count, never the matched text.
- `privacy.status` = `redacted` when the ledger is non-empty, else `clean`;
  `pii_scanned: true` because the scan actually ran.

## Determinism

Same construction as Phase 3: canonical JSON, identity ids
(`derive_ids(dataset, instance_id::agent_run_id, hf_revision)`), content hash
with self-referential fields blanked, emission sorted by
`(instance_id, run_id, source_file, source_row)`. Golden fixture +
two-run-equality tests enforce byte determinism; `--emit-fixture` fails on
drift.

## Provenance and joins

Each trace records the trajectory repo/revision AND the task-table join
(`provenance.task_join`): `SWE-Gym/SWE-Gym` supplies `base_commit`, oracle
test lists, and gold-patch digests. A missing join is recorded honestly
(`joined: false`, empty oracle lists) — never guessed.

## Tests

- `tests/test_trajectory_extraction.py` — grouping, retry/switch counters,
  lexical error marker, synthetic-ordinal timestamps, no-raw-text invariant,
  redaction, determinism, schema validity of every emitted frame.
- `tests/test_openhands_sampled_adapter.py` — full-trace validity
  (envelope + frames + consistency), redacted-but-real objective, join present
  and join missing, failure-shape preservation, SkipRow quarantine, report
  counts, and the consistency gate rejecting each fabrication mode.
- `tests/test_openhands_sampled_golden.py` — golden byte-match, two-run
  determinism, drift detection.

All hermetic: fixture rows are synthetic (shaped like real rows, seeded with
fake PII to exercise redaction); no `/c/pneuma-data`, no network.

## What this does NOT claim

These are traces OF another agent (OpenHands + its LLM), observed from the
outside. They say nothing about Pneuma's interiority and earn no evidence
level by themselves. Their role is supervision substrate: real behavior, real
outcomes, real failure shapes for Phase 4 estimators and replay-based evals.
