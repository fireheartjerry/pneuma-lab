# 33 — Execution Journal

> **NON-AUTHORITATIVE EVIDENCE INDEX.** This append-only journal records what
> operators and agents did. It does not amend or outrank `AGENTS.md`,
> `docs/project-status.json`, `VPS_NEURIPS_2026_HANDOFF.md`, the current
> resampling-null design and implementation plan, or `15-decision-log.md`. If a
> journal entry conflicts with an authority source, the authority source wins,
> execution stops, and the conflict is resolved there before work resumes.

## Recording contract

Event IDs are `EJ-YYYYMMDD-NNNN`, with a monotonically increasing four-digit
sequence within each UTC date. IDs are never reused. Published events are never
edited or deleted; a correction is a later event with `corrects_event_ids` and
both the old and corrected facts. Reconstructed history is labeled
`receipt_mode: reconstructed`; unavailable facts are written as `unavailable`,
not inferred.

Every task command receives an event, including read-only probes/searches,
environment/version checks, tests, validators, file/status/hash inspection,
and Git/remote operations. Only mechanics whose sole effect is appending this
journal are exempt from recursive self-logging. If capture is missed, the next
event records the omission as a deviation. Each event records, where
applicable:

- local timestamp with offset, UTC timestamp, precision, and timestamp source;
- actor and reviewer identities or the narrowest honest description available;
- intent, authority refs/hashes, exact cwd, exact argv, and exit code;
- bounded stdout/stderr summary plus complete-stream SHA-256 and byte count;
- input/output hashes, files touched, and before/after file hashes;
- RED/GREEN classification, expected/actual result, and test counts;
- reviewer findings, repairs, dispositions, and verification reruns;
- dependency, lock, interpreter, binary, platform, and source provenance;
- commit/tree/parent SHA, push argv/result, remote/ref observation, or an
  explicit statement that those facts are unavailable;
- deviations, unresolved anomalies, evidence availability, and next gate.

The committed journal defaults to compact receipts plus content hashes. Full
stdout/stderr is captured locally under the ignored path
`build/research/neurips-2026-workshop/execution-journal/<event-id>/`, with
`stdout.log` and `stderr.log` where each stream exists. Routine raw output,
including routine pytest output, is not committed. Each compact receipt records
the raw path, byte count, digest, and retention state. All captured raw streams
remain locally inspectable at least through `2026-11-27`—90 days after the
submission deadline—and are never automatically deleted. Debugging, anomaly,
and decisive-failure streams additionally remain until the associated
deviation is closed, if later. Cleanup requires explicit user direction plus a
journaled hash/path manifest; no event claims an earlier availability deadline
unless the user explicitly approves one. Evidence is promoted to Git only by
an explicit reviewed event that names its destination, digest, classification,
and rationale. Secrets, credentials, private data, or unsafe raw output are
never promoted.

Capture directories are immutable event slots. Allocation is serialized under
one atomic parent lock directory. A wrapper must acquire that lock with plain
`mkdir`, parse the last published journal ID and prove the proposed heading
absent, atomically reserve the exact event directory with plain `mkdir`, and
release the allocator lock before the task command begins. Failure to acquire
the lock, a stale lock, an unparsable/noncontiguous last ID, an existing
heading/path, or a failed reservation stops before task execution. `mkdir -p`,
truncating redirection, reuse, overwrite, and silent ID selection are
forbidden. The task wrapper never reuses or truncates a slot. A stale allocator
lock or collision is a journaled deviation requiring explicit review.

One task command receives one event, stdout stream, stderr stream, and exit code
by default. Timestamping, reservation, stream hashing, byte counting, and
receipt append mechanics do not count as additional task commands. If a
genuinely atomic aggregate gate is necessary, it must be one explicit
script/process that records every component status and exits nonzero when any
component fails. A `set +e` brace group whose last successful command can mask
an earlier failure is informational only, never authoritative fail-closed
proof.

Journal writes are exempt from logging their own append command; otherwise the
act of recording a receipt would recurse forever. Delivery uses two commits:

1. substantive commit **A** contains the slice change and all pre-commit
   receipts, then A is pushed;
2. before it exists, journal-only commit **B** pre-records the exact planned
   `git commit` and `git push` argv, plus A's immutable SHA, push result,
   remote/ref observation, journal review, and next gate; then those B
   commit/push mechanics run.

B's mechanics are exempt from an immediate in-band result commit. The opening
receipt of the next substantive A must record B's actual SHA, push result, and
fresh remote/ref verification before any slice command runs. Final handoff
must name a terminal pending B if there is no next substantive A. Git content
addressing is the evidence boundary for committed bytes; it is not magical
external immutable anchoring and cannot prove an unobserved remote state. This
is the sole self-reference break. It cannot omit journal content review, the A
delivery receipt, or the next-A reconciliation.

## Reconstructed receipts

