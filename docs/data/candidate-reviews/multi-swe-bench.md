# Dataset Status Review: Multi-SWE-bench

**Decision: TRAINING CANDIDATE — task-only adapter pending; license needs
confirmation.** Not hard-blocked, but the artifact license tag is ambiguous and
must be resolved before any release-style training use.

## Source

| Field            | Value                                                                                                                    |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------ |
| HF repos         | `ByteDance-Seed/Multi-SWE-bench` (1,632, curated eval, 7 langs no Python), `ByteDance-Seed/Multi-SWE-RL` (~24GB rolling) |
| Revision         | `85a3cf39ae22a2439f472d2525a2e07ca18809af`                                                                               |
| Declared license | GitHub Apache-2.0; **dataset cards: `other` / cc0-1.0** (README says CC0); upstream per-repo licenses still apply        |
| Local status     | downloaded (pinned)                                                                                                      |
| Shape            | PR/issue text, fix_patch + test_patch diffs, p2p/f2p/s2p outcomes, agent trajectory **ZIPs**                             |

## Assessment

- **License: ambiguous.** README claims CC0-1.0 (maximally permissive) but the
  HF card tag is `other`. This is a softer version of the `swe-bench-pro`
  ambiguity: the favorable CC0 intent is documented, but the `other` tag must be
  confirmed before release-style training use. Treated as a **caveat**, not a
  hard block, because a permissive license is affirmatively claimed.
- **Shape: task-only first.** fix_patch + test_patch + f2p/p2p map cleanly to a
  task-only lane (like swe-gym-lite). The `_trajs` are ZIPs, not JSONL, so a
  trajectory-bearing lane needs an unzip/normalize step and is deferred.
- **No Python** in the curated eval split (7 other languages) — complements the
  Python-heavy SWE-Gym/Open-SWE-Traces lanes.

## Lane status & next step

- `current_stage: planned`, `training_readiness: local-research-only`,
  `training_weight: 0.0`.
- Next: (1) confirm the CC0-vs-`other` license; (2) build a **task-only
  adapter** over the curated 1,632-instance eval split (fix_patch/test_patch
  digests, oracle kept out of input); (3) defer the ZIP trajectory ingestion to
  a later trajectory-bearing pass; (4) leakage-check the multi-language repos
  against the cross-dataset registry.
