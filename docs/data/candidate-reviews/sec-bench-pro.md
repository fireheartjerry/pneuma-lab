# Dataset Status Review: SEC-bench-Pro

**Decision: BLOCKED — dual-use security content.** Metadata onboarded only; no
adapter, no converter, no `PneumaTrainingExample` output, no PoC execution.

## Source

| Field           | Value                                                                                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| HF repos        | `SEC-bench/SEC-bench` (MIT), `SEC-bench/Seed` (MIT), `SEC-bench/SEC-bench-Pro` (Apache-2.0)                                                            |
| Revision (base) | `11422e774857272b8f5460c699dca7a64046308b`                                                                                                             |
| Local status    | downloaded **metadata only** (no PoC execution)                                                                                                        |
| Shape           | JSONL/parquet task records (instance_id, project, error_type, description), sanitizer_report / bug_report text, Dockerfile/build refs, fix-patch diffs |

## Why blocked

1. **Dual-use.** The dossier `safety_restriction` is explicit: "metadata/
   structure only; do NOT run PoCs or reproduce exploits." Content covers
   memory-safety / sandbox / JIT bugs in V8 / SpiderMonkey plus some VRP-bounty
   rows.
2. **Exploit-adjacent text.** `description` / `bug_report` / `patch` fields
   contain exploit-adjacent detail that must be gated/redacted before any
   pass-through into frames.
3. **Project hard rule.** "Preserve license/provenance/privacy/dual-use gates."
   Licenses themselves are permissive (MIT / Apache-2.0), so this is a
   **dual-use** block, not a license block.

## Next unblock step (eval-only path at most)

1. A committed **dual-use review** deciding whether the corpus may be used at
   all, and if so only as `eval_only` (never a training target).
2. A **redaction pass** removing exploit-reproduction detail from any field that
   would enter a frame, with a `redaction_receipt`.
3. A hard guarantee of **no PoC build/execution** anywhere in the pipeline.

Until then SEC-bench-Pro stays `provenance-blocked` (dual-use) /
`training_readiness: blocked`, `training_weight: 0.0`. Best realistic outcome is
`eval_only`, not a training lane.
