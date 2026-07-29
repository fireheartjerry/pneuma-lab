# 33 — Execution Journal

> **NON-AUTHORITATIVE EVIDENCE INDEX AND CURRENT VOLUME.** This journal records
> execution evidence but does not amend or outrank repository authority.

## Sharded recording contract

The user authorized a byte-preserving storage migration after the original
journal became costly to load. Events through `EJ-20260728-0518` and the original
prologue are stored as immutable historical segments in `execution-journal/`.
Their ordered concatenation reconstructs the exact pre-migration file with
SHA-256 `91e615b381d75cdc6b0a92c18db509a8dd8c3ff76bbc3d03afe4b91b5963ee24`.

New receipts append only below `## Current volume`. A rotation may move complete
event ranges into new immutable segments, but it must preserve event bytes,
update the machine-readable manifest, and pass the repository checker before
release. Published event content is never silently edited, deleted, reordered,
duplicated, or renumbered. Corrections remain later events. Event allocation
must scan the archived manifest and current volume as one logical sequence.

The detailed capture, no-clobber allocation, compact-receipt, raw-retention,
two-commit delivery, and non-authority rules in the archived prologue remain in
force. Routine full stdout/stderr stays local under ignored `build/`; committed
receipts remain compact and content-addressed.

## Immutable archive manifest

- Machine-readable manifest: `execution-journal/manifest.json`
- Archived event count: `518`
- Archived range: `EJ-20260728-0001` through `EJ-20260728-0518`
- Exact reconstructed bytes: `749791`
- Exact reconstructed lines: `10946`
- Exact reconstructed SHA-256: `91e615b381d75cdc6b0a92c18db509a8dd8c3ff76bbc3d03afe4b91b5963ee24`

| Segment | Range | Bytes | Lines | SHA-256 |
|---|---:|---:|---:|---|
| prologue.md | prologue | 5591 | 94 | `8c52e02244f6a489d1d9939d69f29feca396b2c43522f44c4a45dae595eb3ad5` |
| events-20260728-0001-0050.md | EJ-20260728-0001–EJ-20260728-0050 | 100202 | 1891 | `8bec600956bd17584efd48677f4a7cbdad3f4bcdbd11368caff8796c0eac62af` |
| events-20260728-0051-0100.md | EJ-20260728-0051–EJ-20260728-0100 | 68420 | 1423 | `ae684a8cd9e7f2ed79931e129a71df21f86cc91393140d7fd8f72fe6bd78090d` |
| events-20260728-0101-0150.md | EJ-20260728-0101–EJ-20260728-0150 | 58775 | 1280 | `4ea5abfe6277f50b120c96d1eb726ef6ba9900ba6e393971d86e084158d67859` |
| events-20260728-0151-0200.md | EJ-20260728-0151–EJ-20260728-0200 | 78897 | 1609 | `f226f43c4a8843e876686d807085fe6c88b6dc74c434f49c30faf9618d070652` |
| events-20260728-0201-0250.md | EJ-20260728-0201–EJ-20260728-0250 | 83647 | 1569 | `1590527a4d505121b22a48a409897d26d3898e886803cfc49ebdaf95237a0dab` |
| events-20260728-0251-0300.md | EJ-20260728-0251–EJ-20260728-0300 | 62691 | 614 | `05325cccf338be3cc2235b5c9f9786516931d5ce77debc7b4f47f617f11e17af` |
| events-20260728-0301-0350.md | EJ-20260728-0301–EJ-20260728-0350 | 67097 | 531 | `5f0bec9bae995c37bc4793e50d140fd758dd162a25b7ef20db8e00c18093fba2` |
| events-20260728-0351-0400.md | EJ-20260728-0351–EJ-20260728-0400 | 64790 | 564 | `6989ae2e5630a70ea22ca33b13df43405206fa6fef494b5c45e4dd6d3b9a39b8` |
| events-20260728-0401-0450.md | EJ-20260728-0401–EJ-20260728-0450 | 73729 | 632 | `cf15230a1fb058bff579744f8985ce3707fd18c63609d7803ccca289670fdf4b` |
| events-20260728-0451-0468.md | EJ-20260728-0451–EJ-20260728-0468 | 22822 | 212 | `b4650b694d1ae64110288a094a1dc315f38e7a505a2228dd16c1fe5d3ba106c4` |
| events-20260728-0469-0518.md | EJ-20260728-0469–EJ-20260728-0518 | 63130 | 527 | `fded85af1a8adb5a743e3fa6e89705e01033b281f2a05e19d475975b2ae8b16d` |

Run `.venv/bin/python -m scripts.research.execution_journal check` to verify
segment hashes, exact historical reconstruction, and global event continuity.

## Current volume

The next event after the archived migration boundary is appended below.
### EJ-20260728-0519 — pin the deterministic import contract

- **Predecessor:** `EJ-20260728-0518`
- **Time:** `2026-07-28T22:54:47-07:00` to `2026-07-28T22:54:47-07:00` (`2026-07-29T05:54:47+00:00` UTC)
- **Action:** Inspected the immutable API declarations and the registered schedule/manifest/assignment schema and ancestry references.
- **Result:** Exit `0`. The controller API is explicitly ref-based: scheduling accepts manifest and power-final refs; assignment accepts schedule and prefix-index refs; reconstruction accepts the sealed ledger ref. Existing artifact semantics already compare schedule→manifest and assignment→manifest/prefix links. Slice 5 should expose deterministic imports that return validated immutable authority, while later slices retain sealing, live backend, storage, and secret-consumption ownership.
- **Compact receipt:** stdout `34,849 B`, `564 lines`, SHA-256 `7cc352dd93cd1bc14692046e0b7372c14ddb584cdfdf029a0b71eea074d03470`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0519/`.

### EJ-20260728-0520 — inspect acceptance context and existing ancestry checks

- **Predecessor:** `EJ-20260728-0519`
- **Time:** `2026-07-28T22:55:17-07:00` to `2026-07-28T22:55:17-07:00` (`2026-07-29T05:55:17+00:00` UTC)
- **Action:** Searched the plan/spec/journal for the Slice 5 acceptance language and inspected existing direct-parent plus full-closure ancestry checks and reusable valid-record fixtures.
- **Result:** Exit `0`. The useful result is that full-closure validation already proves schedule→manifest, prefix→schedule, and assignment→schedule/prefix/manifest equality. The search was noisier than warranted because it included the journal and generic `digest-derived` prose; do not repeat it. Implement the minimal import transaction directly against the already isolated acceptance contract.
- **Compact receipt:** stdout `64,294 B`, `716 lines`, SHA-256 `071beea6831f1e8ada2f517ff3129a92a3441f1be64653f81240ddc5c1c2494e`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0520/`.

### EJ-20260728-0521 — recover exact immutable Slice 5 row

- **Predecessor:** `EJ-20260728-0520`
- **Time:** `2026-07-28T22:55:48-07:00` to `2026-07-28T22:55:48-07:00` (`2026-07-29T05:55:48+00:00` UTC)
- **Action:** Located the exact Task 3 Slice 5 table row and its immediate implementation-order context without another broad search.
- **Result:** Exit `0`. Confirmed exclusive ownership of `preflight.py`, `assignment.py`, and their two tests; focused selector `t3_s05`; intended commit `feat(resampling-null): import deterministic assignment authority`. The later signature, storage/power, allocation, synthetic, confirmation, and reconstruction behaviors remain explicitly assigned to Slices 6–11.
- **Compact receipt:** stdout `11,979 B`, `117 lines`, SHA-256 `864b1728895e42ca342ae22d92cc8a5fed67d9734794bb1b0fd298a58b8a1af6`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0521/`.

### EJ-20260728-0522 — isolate assignment-import behavioral requirement

- **Predecessor:** `EJ-20260728-0521`
- **Time:** `2026-07-28T22:56:13-07:00` to `2026-07-28T22:56:13-07:00` (`2026-07-29T05:56:13+00:00` UTC)
- **Action:** Read the Task 3 behavioral-test contract surrounding deterministic imports and the assignment controller.
- **Result:** Exit `0`. Slice 5 must establish two reusable foundations: closed/canonical deterministic asset import (including exact scalar typing, text hygiene, and only declared semantic-set normalization) and ref-only assignment ancestry loading. The assignment controller must accept no schedule object or free mode/program input, load schedule solely through `schedule_ref`, reload manifest through the schedule, load prefix solely through `prefix_index_ref`, and reject wrong/incomplete ancestry. Later slice behavior remains out of scope.
- **Compact receipt:** stdout `10,971 B`, `161 lines`, SHA-256 `7545665c5ca071d6adfe0dc1f2e674613591b793ec1e881ebb90429b19f0efef`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0522/`.

### EJ-20260728-0523 — map fixture and canonical-writer seam

- **Predecessor:** `EJ-20260728-0522`
- **Time:** `2026-07-28T22:57:08-07:00` to `2026-07-28T22:57:08-07:00` (`2026-07-29T05:57:08+00:00` UTC)
- **Action:** Enumerated the small current test surface, inspected reusable artifact fixture construction, the canonical atomic writer, and frozen shared value types.
- **Result:** Exit `0`. No dedicated preflight fixtures exist. Slice 5 can use the existing strict JSON decoder and canonical atomic bytes writer, while keeping its behavioral check compact. The authority return value should expose only immutable identity/refs—not mutable caller-provided schedule objects—so later assignment logic cannot accidentally regain the forbidden caller-controlled seam.
- **Compact receipt:** stdout `13,552 B`, `438 lines`, SHA-256 `95828c4e6e9e0c211b97401ba6db1c959a28161678f1da79995d4ef18efb15e0`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0523/`.

### EJ-20260728-0524 — implement and inspect deterministic authority seam

- **Predecessor:** `EJ-20260728-0523`
- **Time:** `2026-07-28T23:00:22-07:00` to `2026-07-28T23:00:22-07:00` (`2026-07-29T06:00:22+00:00` UTC)
- **Action:** Added the deterministic closed-JSON importer, added the immutable ref-only assignment-authority loader, added compact Slice 5 behavioral checks, and inspected the tracked diff plus the assignment-test insertion seam.
- **Result:** Exit `0` for inspection. The importer rejects open grammars, wrong kinds, non-exact integer fields, non-NFC/control text, and duplicate semantic-set members; only declared sets normalize; canonical bytes publish at a digest-derived inside-root path with byte-identical idempotence. The assignment loader follows schedule→manifest and prefix refs through the existing byte/digest/schema validator and returns only frozen identity/refs. The first diff command omitted the two new untracked files by Git semantics, so their contents remain explicitly in scope and must be included in the subsequent verification/commit.
- **Compact receipt:** stdout `8,006 B`, `221 lines`, SHA-256 `8d1d87cd0955439259524fe45cf98d572372d26c540260f178b14fb13341657d`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0524/`.

### EJ-20260728-0525 — run the sole focused Slice 5 behavior gate

- **Predecessor:** `EJ-20260728-0524`
- **Time:** `2026-07-28T23:01:20-07:00` to `2026-07-28T23:01:21-07:00` (`2026-07-29T06:01:20+00:00` to `2026-07-29T06:01:21+00:00` UTC)
- **Action:** Ran exactly the immutable Slice 5 selector under a hard 60-second interrupt/kill ceiling: `.venv/bin/python -m pytest tests/resampling_null/test_preflight.py tests/resampling_null/test_assignment.py -q -k t3_s05`.
- **Result:** GREEN, exit `0`, completed in under one second, zero stderr. This is the single behavioral test command for the slice; do not repeat it without a concrete code repair.
- **Compact receipt:** stdout `113 B`, `2 lines`, SHA-256 `71897f54c207af63002d9b61692b506cf0a7bf697ef29d7fcfea500cee8eb701`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0525/`.

### EJ-20260728-0526 — run the sole combined Slice 5 static gate

- **Predecessor:** `EJ-20260728-0525`
- **Time:** `2026-07-28T23:01:54-07:00` to `2026-07-28T23:01:54-07:00` (`2026-07-29T06:01:54+00:00` UTC)
- **Action:** Ran one fail-closed static command containing the authority-prescribed Ruff and mypy invocations, each independently capped at 60 seconds.
- **Result:** GREEN, exit `0`, zero stderr. Ruff reports all checks passed; mypy reports success across the resampling-null source surface. This is the slice's single static gate.
- **Compact receipt:** stdout `62 B`, `2 lines`, SHA-256 `43d453bd2d33b121f758026f728256a1a5a2ba9ef1d758bf40a05ab302310ee9`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0526/`.

### EJ-20260728-0527 — hostile-review Slice 5 before delivery

- **Predecessor:** `EJ-20260728-0526`
- **Time:** `2026-07-28T23:02:21-07:00` to `2026-07-28T23:02:21-07:00` (`2026-07-29T06:02:21+00:00` UTC)
- **Action:** Read every changed source/test line as a maximally hostile reviewer, checked whitespace/worktree scope, and hashed the four Slice 5 implementation/test files.
- **Result:** DELIVERY BLOCKED BY REVIEW despite green gates. The ref-only assignment loader is directionally sound, but the importer is only a caller-configured top-level toolkit. It does not itself freeze the concrete manifest-owned grammars or recursively enforce exact nested integer/object/array structure; therefore it is too weak to satisfy the immutable acceptance text. Its existing-path publication also needs a race-safe binding audit before it can claim fail-closed idempotence. Do not commit this state. Expand concrete recursive authority, repair publication binding, then rerun only the directly affected focused/static gates.
- **Current content hashes:** `preflight.py` `099a397e8cc24e39f0b07698f173d4ceba138c2597ed5f187c60bbd09162029b`; `assignment.py` `a695c72cd637a21ef43f5ebc40931f296ab5336f2ffa354a564a5b4053313444`; `test_preflight.py` `0042557a30bf11ca26fc60338525d907ee22bc6adc6bcafeb01ad59ba3011f07`; `test_assignment.py` `a7a4c5610710fb39abf2477caaf1644955b772d9b824b4136aa6a115f2ebe4eb`.
- **Compact receipt:** stdout `17,580 B`, `508 lines`, SHA-256 `74dd2499b5fcd6a5863c1f20a258383fa44d62d5176ab478c2a327fe15639add`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0527/`.

### EJ-20260728-0528 — extract concrete manifest-owned import authority

- **Predecessor:** `EJ-20260728-0527`
- **Time:** `2026-07-28T23:03:16-07:00` to `2026-07-28T23:03:16-07:00` (`2026-07-29T06:03:16+00:00` UTC)
- **Action:** Enumerated the plan's closed record kinds and read the exact task-registry, roster/ceremony, qualification, assignment-program, backend, build-provenance, and verifier-feature import requirements.
- **Result:** Exit `0`. Concrete authority confirms nested closure and ordering are scientific, not generic JSON hygiene. Immediate repair must at minimum freeze task-registry and assignment-program structures as actual trusted grammars, distinguish semantic-set arrays from authority-ordered arrays, validate exact non-negative integers recursively, and leave signature/runtime/live-capability checks to their assigned later slice. The importer remains a canonical copying boundary, not a claim that parsing alone verifies ceremony or backend provenance.
- **Compact receipt:** stdout `30,925 B`, `556 lines`, SHA-256 `835a1964ddaf19e954f838c38cc08f121853adb8d18351be2d203a93b6344cf2`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0528/`.

### EJ-20260728-0529 — audit existing atomic writer before CAS repair

- **Predecessor:** `EJ-20260728-0528`
- **Time:** `2026-07-28T23:03:44-07:00` to `2026-07-28T23:03:44-07:00` (`2026-07-29T06:03:44+00:00` UTC)
- **Action:** Read the existing bound publication transaction and canonical serializer to determine whether it could satisfy immutable content-addressed import semantics.
- **Result:** Exit `0`. The existing writer is ancestry-bound and rollback-safe for ordinary artifact publication, but deliberately replaces an existing target after backup. That is the wrong semantic for a CAS import, where byte-identical preexistence is allowed and any mismatch must never be overwritten. Slice 5 therefore now uses an exclusive-create/no-follow installer, binds and verifies an existing regular single-link file, compares exact bytes, refuses replacement, verifies inode identity, and fsyncs file plus parent. Cleanup is inode-conditional so it cannot unlink a path swapped by a peer.
- **Compact receipt:** stdout `10,869 B`, `309 lines`, SHA-256 `68080f2107678456901568bb1970bff6643409ce77e8752a5f6f066148731bbe`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0529/`.

### EJ-20260728-0530 — verify hostile-review repair behavior

- **Predecessor:** `EJ-20260728-0529`
- **Time:** `2026-07-28T23:06:28-07:00` to `2026-07-28T23:06:29-07:00` (`2026-07-29T06:06:28+00:00` to `2026-07-29T06:06:29+00:00` UTC)
- **Action:** After expanding concrete nested task-registry and assignment-program authority and replacing overwrite publication with exclusive CAS semantics, reran only the directly affected `t3_s05` selector under the 60-second hard ceiling.
- **Result:** GREEN, exit `0`, under one second, zero stderr. This repair rerun is justified by substantive source/test changes after EJ-0527; no broader suite ran.
- **Compact receipt:** stdout `113 B`, `2 lines`, SHA-256 `93054f1d69674b5c14d1d253896310678dfcdb76c51513a20c00561ddf313353`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0530/`.

### EJ-20260728-0531 — static repair gate exposes annotations only

- **Predecessor:** `EJ-20260728-0530`
- **Time:** `2026-07-28T23:06:59-07:00` to `2026-07-28T23:07:00-07:00` (`2026-07-29T06:06:59+00:00` to `2026-07-29T06:07:00+00:00` UTC)
- **Action:** Reran the combined Ruff/mypy gate after the substantive hostile-review repair.
- **Result:** RED, exit `1`, zero stderr. Ruff is green. Mypy found exactly three static typing defects: dynamic `ArtifactRef(**mapping)` cannot prove its mixed field types, and a fixed four-byte tuple built by comprehension is inferred variadically. No runtime/behavior failure was reported. Repair with explicit typed construction only; do not rerun behavioral tests because semantics do not change.
- **Compact receipt:** stdout `570 B`, `5 lines`, SHA-256 `1324fcb65c5c7faba093103c897f5677411740c0c9726d2003ebc01abb31bd2a`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0531/`.

### EJ-20260728-0532 — close annotation-only static repair

- **Predecessor:** `EJ-20260728-0531`
- **Time:** `2026-07-28T23:07:38-07:00` to `2026-07-28T23:07:39-07:00` (`2026-07-29T06:07:38+00:00` to `2026-07-29T06:07:39+00:00` UTC)
- **Action:** Replaced only the two ambiguous dynamic constructions with explicit typed fields/fixed tuple construction, then reran the combined static gate.
- **Result:** GREEN, exit `0`, zero stderr. Ruff and mypy both pass. Behavioral tests were correctly not rerun because the repair changed annotations/construction spelling only.
- **Compact receipt:** stdout `62 B`, `2 lines`, SHA-256 `43d453bd2d33b121f758026f728256a1a5a2ba9ef1d758bf40a05ab302310ee9`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0532/`.

### EJ-20260728-0533 — close source-snapshot and directory-binding attacks

- **Predecessor:** `EJ-20260728-0532`
- **Time:** `2026-07-28T23:09:34-07:00` to `2026-07-28T23:09:36-07:00` (`2026-07-29T06:09:34+00:00` to `2026-07-29T06:09:36+00:00` UTC)
- **Action:** Repaired two newly identified self-adversarial paths, added direct checks, and reran only `t3_s05` under the 60-second ceiling.
- **Result:** GREEN, exit `0`, about one second, zero stderr. Concrete imports now parse, recursively validate, and publish the same captured byte snapshot—there is no second source read that can substitute weaker nested bytes. CAS publication holds a no-follow directory descriptor, addresses the leaf relative to it, verifies directory and leaf inode identity, never overwrites, conditionally cleans only its own inode, and fsyncs the bound directory. The focused check proves one source read and mismatch-preserving fixed-path idempotence.
- **Compact receipt:** stdout `113 B`, `2 lines`, SHA-256 `03a4b541606c432f04ee9f0cf875d8ad67b8d7065b59faa4137ed6de0eaf13bf`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0533/`.

### EJ-20260728-0534 — verify snapshot/CAS repair statically

- **Predecessor:** `EJ-20260728-0533`
- **Time:** `2026-07-28T23:10:04-07:00` to `2026-07-28T23:10:05-07:00` (`2026-07-29T06:10:04+00:00` to `2026-07-29T06:10:05+00:00` UTC)
- **Action:** Ran the combined Ruff/mypy gate after the source-snapshot and directory-bound CAS repair.
- **Result:** GREEN, exit `0`, zero stderr. Both static authorities pass.
- **Compact receipt:** stdout `62 B`, `2 lines`, SHA-256 `43d453bd2d33b121f758026f728256a1a5a2ba9ef1d758bf40a05ab302310ee9`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0534/`.

### EJ-20260728-0535 — verify declared semantic-set normalization

- **Predecessor:** `EJ-20260728-0534`
- **Time:** `2026-07-28T23:11:25-07:00` to `2026-07-28T23:11:25-07:00` (`2026-07-29T06:11:25+00:00` UTC)
- **Action:** Corrected task-registry task/group arrays from rejection-only ordering to the authority-required semantic-set normalization, added directory-path rebound verification to the existing-object arm, and reran only `t3_s05`.
- **Result:** GREEN, exit `0`, under one second, zero stderr. Reordered registry/group sources now canonicalize deterministically while duplicates still reject; assignment-program cutpoints/component/stratum arrays remain authority-ordered and are validated rather than resorted.
- **Compact receipt:** stdout `113 B`, `2 lines`, SHA-256 `36d6893b7da186ee578f28d4a2d3d6408bebe6836757648aa4b5be8b983733d4`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0535/`.

### EJ-20260728-0536 — close semantic-set repair statically

- **Predecessor:** `EJ-20260728-0535`
- **Time:** `2026-07-28T23:11:56-07:00` to `2026-07-28T23:11:57-07:00` (`2026-07-29T06:11:56+00:00` to `2026-07-29T06:11:57+00:00` UTC)
- **Action:** Ran the combined Ruff/mypy gate after semantic-set and directory-rebind repair.
- **Result:** GREEN, exit `0`, zero stderr. Both static authorities pass.
- **Compact receipt:** stdout `62 B`, `2 lines`, SHA-256 `43d453bd2d33b121f758026f728256a1a5a2ba9ef1d758bf40a05ab302310ee9`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0536/`.

### EJ-20260728-0537 — final hostile source and authority audit

- **Predecessor:** `EJ-20260728-0536`
- **Time:** `2026-07-28T23:12:25-07:00` to `2026-07-28T23:12:25-07:00` (`2026-07-29T06:12:25+00:00` UTC)
- **Action:** Inspected the complete implementation source, worktree scope, whitespace, journal checker, immutable authority hashes, diff size, and final content hashes.
- **Result:** Exit `0`. Plan/design remain exactly `a2ca4fc419f353e9a38350025e1e2996fd21d66eb16b2d8d011af2c2e1d491b1` / `d2a3c5a20059574ab8dad92a45b29f06aeeaf2bd9dafbc8716c5449848a687db`. Worktree scope is exactly the journal and four Slice 5 files. No whitespace error. Source review finds the earlier nested-grammar, source-snapshot, overwrite, symlink/directory-rebind, cleanup, scalar-type, and semantic-set defects repaired. The journal checker emitted two stderr lines despite exit `0`; classify those exact lines before delivery rather than silently treating zero exit as sufficient.
- **Current content hashes:** `preflight.py` `bd1bc1580824c773f14775dfb5ac878250fd058a479368af22be31cec4fecb15`; `assignment.py` `a695c72cd637a21ef43f5ebc40931f296ab5336f2ffa354a564a5b4053313444`; `test_preflight.py` `13c47bc72eac92c431db2554da0a7e6ad2dc1555fdd8cadfa071a66b64e7ef50`; `test_assignment.py` `a7a4c5610710fb39abf2477caaf1644955b772d9b824b4136aa6a115f2ebe4eb`.
- **Compact receipt:** stdout `27,852 B`, `760 lines`, SHA-256 `f96ca0351adbbffff520f80ee5fc3d87787b76a374c0afc60ab3ce2c796bfcb5`; stderr `128 B`, `2 lines`, SHA-256 `a9ec6d7abd577b31890e7d459d97354da4c1823f1afc958861631fb734c50cab`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0537/`.

### EJ-20260728-0538 — classify EJ-0537 stderr and invalidate false aggregate green

- **Predecessor:** `EJ-20260728-0537`
- **Time:** `2026-07-28T23:13:06-07:00` to `2026-07-28T23:13:06-07:00` (`2026-07-29T06:13:06+00:00` UTC)
- **Action:** Displayed exactly the two unexplained EJ-0537 stderr lines.
- **Result:** The journal checker was invoked with invalid syntax (`--check` instead of the required `check` subcommand). More importantly, EJ-0537's brace group continued after that failure and returned the final successful command's status, so its aggregate exit `0` does not prove every subcheck passed. Preserve the other directly observed facts, but invalidate EJ-0537's checker/aggregate-green interpretation. Rerun the checker with correct syntax in a fail-fast command before delivery.
- **Compact receipt:** stdout `128 B`, `2 lines`, SHA-256 `a9ec6d7abd577b31890e7d459d97354da4c1823f1afc958861631fb734c50cab`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0538/`.

### EJ-20260728-0539 — corrected fail-fast authority gate

- **Predecessor:** `EJ-20260728-0538`
- **Time:** `2026-07-28T23:13:42-07:00` to `2026-07-28T23:13:42-07:00` (`2026-07-29T06:13:42+00:00` UTC)
- **Action:** Invoked the journal checker with its correct `check` subcommand inside a fail-fast subshell, then checked whitespace and exact immutable plan/design hashes.
- **Result:** GREEN, exit `0`, zero stderr. Journal integrity, whitespace, and both authority hashes are valid. Unlike EJ-0537, any failed subcommand would have determined the event exit.
- **Compact receipt:** stdout `251 B`, `4 lines`, SHA-256 `040594cf28c8536585563d52ca6b6f74f8543aee66806067ff92cdbd6cc45866`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0539/`.

### EJ-20260728-0540 — pre-record finite Slice 5 delivery commit

- **Predecessor:** `EJ-20260728-0539`
- **Delivery scope:** exactly `src/pneuma_lab/resampling_null/{preflight.py,assignment.py}`, `tests/resampling_null/{test_preflight.py,test_assignment.py}`, and this live journal.
- **Planned mechanics:** stage those five paths; fail on whitespace; inspect staged names; commit `feat(resampling-null): import deterministic assignment authority`; push `HEAD` to public `origin/codex/neurips-2026-empirical`; compare local and exact remote refs.
- **Evidence basis:** focused behavior EJ-0535 GREEN; static EJ-0536 GREEN; corrected authority/journal/whitespace EJ-0539 GREEN; final hostile source audit defects repaired.
- **Self-reference break:** reconcile the resulting commit, push, remote SHA, and raw receipt in the next event before further substantive work.

### EJ-20260728-0541 — deliver Task 3 Slice 5 to the public branch

- **Predecessor:** `EJ-20260728-0540`
- **Time:** `2026-07-28T23:14:48-07:00` to `2026-07-28T23:14:49-07:00` (`2026-07-29T06:14:48+00:00` to `2026-07-29T06:14:49+00:00` UTC)
- **Action:** Staged exactly the five pre-recorded paths, checked staged whitespace and names fail-fast, committed `feat(resampling-null): import deterministic assignment authority`, pushed to the public working branch, and compared the exact local/remote refs.
- **Result:** GREEN, exit `0`. Commit and public remote are exactly `be9c06aefa35059939ac1e4f325ba7c8930b8594`. Slice 5 is delivered; the only subsequent tracked delta is this reconciliation receipt.
- **Scientific boundary:** This closes deterministic task-registry/assignment-program imports and ref-only schedule→manifest plus prefix authority loading. It does not claim live ceremony verification, storage/power scheduling, allocation, confirmation matching, or reconstruction; those remain owned by the immutable later slices.
- **Compact receipt:** stdout `368 B`, `6 lines`, SHA-256 `00760d975f70f99040e84ef467164ee3e084aef169aa416499b505effd7d77e1`; stderr `110 B`, `2 lines`, SHA-256 `64c78ab4e50c05556f2bdece66ea19f031e5ab4b653a803adf7418b6147609de`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0541/`.

### EJ-20260728-0542 — pre-record finite Slice 5 receipt commit

- **Predecessor:** `EJ-20260728-0541`
- **Planned mechanics:** stage only this live journal; check whitespace; commit `docs(neurips): record task 3 slice 5 delivery`; push to the public working branch; reconcile the exact remote at the next substantive opening event.
- **Self-reference break:** the finite B commit intentionally records delivery through EJ-0542; its SHA and push receipt remain local until the next event.

### EJ-20260728-0543 — reconcile Slice 5 receipt commit

- **Predecessor:** `EJ-20260728-0542`
- **Time:** `2026-07-28T23:15:25-07:00` to `2026-07-28T23:15:26-07:00` (`2026-07-29T06:15:25+00:00` to `2026-07-29T06:15:26+00:00` UTC)
- **Action:** Staged only the journal, checked whitespace/scope, committed `docs(neurips): record task 3 slice 5 delivery`, pushed, and compared exact local/public remote refs.
- **Result:** GREEN, exit `0`. Receipt commit and public remote are exactly `04d6af024f7123b223dfe6cdd03d40a276554394`.
- **Compact receipt:** stdout `222 B`, `4 lines`, SHA-256 `7be5c4b0b282195d4dfa0b1e0789fe8445b059641440c5cd862f57a49b5f5a00`; stderr `110 B`, `2 lines`, SHA-256 `f1d5b52817b92f200d328217c64e19691b51cd5e522353fd6b2fdc6648ebdae7`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0543/`.
- **Next:** apply the established 50-event archive policy before opening Slice 6, so the live journal remains responsive.

### EJ-20260728-0544 — inspect live-journal shard threshold

- **Predecessor:** `EJ-20260728-0543`
- **Time:** `2026-07-28T23:16:05-07:00` to `2026-07-28T23:16:06-07:00` (`2026-07-29T06:16:05+00:00` to `2026-07-29T06:16:06+00:00` UTC)
- **Action:** Inspected the migrator interface, measured the live journal, and read the archive segment manifest.
- **Result:** Exit `0`, zero stderr. The live journal is `94,160 B`, `783 lines`, and `75` events (`EJ-0469` through `EJ-0543` before this receipt). Archive authority ends at EJ-0468. Migrate the next exact 50-event block through `EJ-20260728-0518`, leaving the recent 26-event working tail beginning at EJ-0519.
- **Compact receipt:** stdout `3,966 B`, `124 lines`, SHA-256 `02926f83479065d9c634560f3bbbc0f0c5ae8b0d0f94668414e1000e5e8878c6`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0544/`.

### EJ-20260728-0545 — discover migrator cannot append a shard

- **Predecessor:** `EJ-20260728-0544`
- **Time:** `2026-07-28T23:16:38-07:00` to `2026-07-28T23:16:38-07:00` (`2026-07-29T06:16:38+00:00` UTC)
- **Action:** Attempted the exact 50-event migration through EJ-0518, followed fail-fast by integrity/size/hash checks.
- **Result:** RED, exit `1`, no committed file changed. The migrator rejects whenever the archive directory already exists (`JournalIntegrityError: archive path already exists`), so it supports only initial conversion and cannot maintain the standing shard policy. Do not manually rewrite forensic history. Extend the migrator to append only a contiguous live prefix after fully verifying the existing manifest/reconstruction, then use one narrow migration integrity check.
- **Compact receipt:** stdout `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; stderr `622 B`, `9 lines`, SHA-256 `4bb9c4c24b1a0bcc964362419da9b94f8973df31b4d2c15f3095f3d114dce8f3`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0545/`.

### EJ-20260728-0546 — design append-only archive rotation

- **Predecessor:** `EJ-20260728-0545`
- **Time:** `2026-07-28T23:17:22-07:00` to `2026-07-28T23:17:22-07:00` (`2026-07-29T06:17:22+00:00` UTC)
- **Action:** Read the complete migrator/verifier and its focused tests, then implemented append rotation rather than bypassing the forensic contract manually.
- **Result:** Exit `0` for inspection. The repair verifies the existing archive/current logical chain first; requires the cutoff inside the current volume and directly contiguous after the archived boundary; shards only that selected prefix; refuses path collisions; retains existing segments byte-for-byte; recomputes aggregate bytes/lines/hash; regenerates the live index plus untouched tail; publishes new shards exclusively; and rolls manifest/live/shards back on failure. A narrow test covers initial migration, a later two-event append, retained live tail, segment naming, and global verification.
- **Correction during review:** the verifier's returned `last_event_id` describes the whole logical chain, not the archive boundary. The append continuity check therefore uses `manifest["last_event_id"]`; this was corrected before execution.
- **Compact receipt:** stdout `17,433 B`, `519 lines`, SHA-256 `41495dd28aa0de4f49f4d72c90f7b7ec1bb8bb46f913ca635f7f66d202aa89c9`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0546/`.

### EJ-20260728-0547 — narrow append test catches an imprecise assertion

- **Predecessor:** `EJ-20260728-0546`
- **Time:** `2026-07-28T23:19:31-07:00` to `2026-07-28T23:19:31-07:00` (`2026-07-29T06:19:31+00:00` UTC)
- **Action:** Ran only `test_migration_appends_only_a_contiguous_live_prefix` under the 60-second ceiling.
- **Result:** RED, exit `1`, zero stderr. Migration and `verify_journal` completed successfully with the expected archived/current counts. The final assertion incorrectly required the archived event ID to be absent from the whole live index, but the immutable manifest table intentionally names that range. Correct the assertion to forbid an archived **event heading** (`### EJ-...`), while allowing the index reference. No production defect is indicated by this failure.
- **Compact receipt:** stdout `2,665 B`, `62 lines`, SHA-256 `afeffd099184dbda71561c11e151ab9cfcb2caa96978ce9f367790b339c60440`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0547/`.

### EJ-20260728-0548 — corrected narrow append-migration check

- **Predecessor:** `EJ-20260728-0547`
- **Time:** `2026-07-28T23:20:13-07:00` to `2026-07-28T23:20:13-07:00` (`2026-07-29T06:20:13+00:00` UTC)
- **Action:** Corrected only the test wording from whole-index absence to archived-heading absence and reran the same one test under 60 seconds.
- **Result:** GREEN, exit `0`, zero stderr, under one second. One test passed; four unrelated journal tests were deselected.
- **Compact receipt:** stdout `112 B`, `2 lines`, SHA-256 `12231b793edcf40030976895c17f7d5df4a4759d0f915ce9617e788c5b07cba7`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0548/`.

### EJ-20260728-0549 — static-check append migration

- **Predecessor:** `EJ-20260728-0548`
- **Time:** `2026-07-28T23:20:48-07:00` to `2026-07-28T23:20:48-07:00` (`2026-07-29T06:20:48+00:00` UTC)
- **Action:** Ran one Ruff check over only the modified migrator and focused test, under 60 seconds.
- **Result:** GREEN, exit `0`, zero stderr; all checks passed.
- **Compact receipt:** stdout `19 B`, `1 line`, SHA-256 `82b3e6a6c090a57601d22943bd23fca9218d1031dbe5a7b754092f9a156b4f18`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0549/`.

### EJ-20260728-0550 — append the next immutable 50-event journal shard

- **Predecessor:** `EJ-20260728-0549`
- **Time:** `2026-07-28T23:21:17-07:00` to `2026-07-28T23:21:17-07:00` (`2026-07-29T06:21:17+00:00` UTC)
- **Action:** Migrated the exact contiguous prefix EJ-0469 through EJ-0518 into one immutable shard, then independently ran the repository checker and measured/hashed the resulting archive and live volume.
- **Result:** GREEN, exit `0`, zero stderr. Archive now contains `518` contiguous events with reconstructed SHA-256 `91e615b381d75cdc6b0a92c18db509a8dd8c3ff76bbc3d03afe4b91b5963ee24`; current volume retains `31` events through EJ-0549. Live journal fell from `94,160 B` / `783 lines` to `37,443 B` / `305 lines`.
- **Artifact hashes:** new shard `events-20260728-0469-0518.md` `fded85af1a8adb5a743e3fa6e89705e01033b281f2a05e19d475975b2ae8b16d`; updated manifest `eea0efdb02b4ddd4f63a4cff3beb6cc7e2d304e32b4797322511214a5e8abd98`; migrated live journal before this receipt `b4fa83983a131a23b59bcf4e6735e9a0c98b79fc992f00a70b2523418085dc17`.
- **Compact receipt:** stdout `850 B`, `8 lines`, SHA-256 `78f9f8cadd5519af5555d12a5be0f3976f77ab4db7bb7a5e7f0651639d1990eb`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0550/`.

### EJ-20260728-0551 — hostile-audit append migration and exact scope

- **Predecessor:** `EJ-20260728-0550`
- **Time:** `2026-07-28T23:21:54-07:00` to `2026-07-28T23:21:55-07:00` (`2026-07-29T06:21:54+00:00` to `2026-07-29T06:21:55+00:00` UTC)
- **Action:** Checked worktree scope/whitespace, reran the journal verifier, reviewed the entire append implementation/test diff, and hashed every deliverable.
- **Result:** GREEN, exit `0`, zero stderr. Logical journal is contiguous through EJ-0550 with `518` archived and `32` current events. Review found no unresolved in-scope integrity defect: existing segments are never rewritten, new segment creation is exclusive, cutoff/continuity/path collisions fail closed, selected bytes are exact, live tail is preserved, aggregate hashes are recomputed, and the actual repository migration independently verifies.
- **Content hashes:** migrator `8fd6ec6d41e5fad5e72aa53162da00ca8bbb5d009d3e5546f3cdada6e1b38682`; focused test `6fd16a4ade783a6cd059dce0cd940e292b9769d648b063544933f8c38946564e`; new shard `fded85af1a8adb5a743e3fa6e89705e01033b281f2a05e19d475975b2ae8b16d`; manifest `eea0efdb02b4ddd4f63a4cff3beb6cc7e2d304e32b4797322511214a5e8abd98`; live journal before this receipt `2c9f690974c54cbee38ca8f8755d993213e7fbe9b554ee452c73fd04f3728bbd`.
- **Compact receipt:** stdout `11,251 B`, `295 lines`, SHA-256 `f8683db46ca8554131241de3546123c28744c5ad88e1fcc47142be26f4ac74d0`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0551/`.

### EJ-20260728-0552 — pre-record finite append-migration delivery

- **Predecessor:** `EJ-20260728-0551`
- **Delivery scope:** exactly the live journal, archive manifest, new EJ-0469–0518 shard, migrator, and focused migrator test.
- **Planned mechanics:** stage those five paths; fail on whitespace and exact staged names; commit `feat(journal): support append-only archive rotation`; push the public working branch; compare exact local/remote refs.
- **Self-reference break:** reconcile commit/push facts in the next event before opening scientific Slice 6.
