# 33 — Execution Journal

> **NON-AUTHORITATIVE EVIDENCE INDEX AND CURRENT VOLUME.** This journal records
> execution evidence but does not amend or outrank repository authority.

## Sharded recording contract

The user authorized a byte-preserving storage migration after the original
journal became costly to load. Events through `EJ-20260728-0568` and the original
prologue are stored as immutable historical segments in `execution-journal/`.
Their ordered concatenation reconstructs the exact pre-migration file with
SHA-256 `d809772777e6e1b54c31e04555b6cd1344741e60a54c885bf2a9cb46f687b337`.

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
- Archived event count: `568`
- Archived range: `EJ-20260728-0001` through `EJ-20260728-0568`
- Exact reconstructed bytes: `804906`
- Exact reconstructed lines: `11354`
- Exact reconstructed SHA-256: `d809772777e6e1b54c31e04555b6cd1344741e60a54c885bf2a9cb46f687b337`

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
| events-20260728-0519-0568.md | EJ-20260728-0519–EJ-20260728-0568 | 55115 | 408 | `2f252669c8e7fbc1a1e94690edfb476970d21752aea88d21291c6b425a3d601a` |

Run `.venv/bin/python -m scripts.research.execution_journal check` to verify
segment hashes, exact historical reconstruction, and global event continuity.

## Current volume

The next event after the archived migration boundary is appended below.

### EJ-20260728-0569 — rotate exact EJ-0519–0568 shard

- **Predecessor:** `EJ-20260728-0568`
- **Time:** `2026-07-28T23:34:49-07:00` to `2026-07-28T23:34:49-07:00` (`2026-07-29T06:34:49+00:00` UTC)
- **Action:** Appended the exact 50-event range EJ-0519 through EJ-0568 to the immutable archive, then reran the independent checker and hashed the new shard/manifest/live index.
- **Result:** GREEN, exit `0`, zero stderr. Archive contains `568` events with reconstructed SHA-256 `d809772777e6e1b54c31e04555b6cd1344741e60a54c885bf2a9cb46f687b337`; current volume was empty immediately after rotation. Live index is only `3,995 B` / `56 lines` before this receipt.
- **Artifact hashes:** new shard `events-20260728-0519-0568.md` `2f252669c8e7fbc1a1e94690edfb476970d21752aea88d21291c6b425a3d601a`; manifest `00fd1e62bc26d18ba5b74bb8bd94bbab7a12deadbdbe3f6baf82ca6f8148af84`; empty live index `321aca9e49ddf73abe892f6885a8c14dd27dee75151ead98d88930375050deb7`.
- **Compact receipt:** stdout `844 B`, `8 lines`, SHA-256 `8a9bea0caf6dc19d877d73bf39f9254045b596804290ffb424452c621662e293`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0569/`.

### EJ-20260728-0570 — pre-record finite exact-boundary shard delivery

- **Predecessor:** `EJ-20260728-0569`
- **Delivery scope:** live journal, archive manifest, and new EJ-0519–0568 shard only.
- **Planned mechanics:** stage exact three paths; check whitespace/scope; commit `docs(neurips): archive execution journal through ej-0568`; push publicly; compare exact refs.
- **Self-reference break:** reconcile the resulting delivery as the Slice 7 opening event.

### EJ-20260728-0571 — deliver exact-boundary journal shard

- **Predecessor:** `EJ-20260728-0570`
- **Time:** `2026-07-28T23:35:24-07:00` to `2026-07-28T23:35:25-07:00` (`2026-07-29T06:35:24+00:00` to `2026-07-29T06:35:25+00:00` UTC)
- **Action:** Staged exactly the live journal, manifest, and new shard; checked whitespace/scope; committed `docs(neurips): archive execution journal through ej-0568`; pushed publicly; and compared refs.
- **Result:** GREEN, exit `0`. Commit and public remote are exactly `d535ed930df8ddb7792930f5b19f49caae290fdf`.
- **Compact receipt:** stdout `355 B`, `5 lines`, SHA-256 `923650cf896ac5fada7e4bbe4c2bf62f3f114c56e85aa4ec1b06730bae1e0a22`; stderr `110 B`, `2 lines`, SHA-256 `204a0f15b82aae0882aaa600f60a373496b3493ada0fe0f9950e1bd77749d88e`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0571/`.
- **Next:** open Slice 7's storage/power-final consumer boundary from clean public authority.

### EJ-20260728-0572 — correct malformed Slice 7 capture wrapper

- **Predecessor:** `EJ-20260728-0571`
- **Action:** Attempted to allocate and capture the Slice 7 authority read, but the shell rejected the complete command at parse time because of an unmatched subshell parenthesis.
- **Result:** RED, shell exit `2`; no command body executed, no event directory was allocated, and no repository/external state changed. Tool-visible stderr was `/bin/bash: -c: line 16: syntax error near unexpected token ')'` followed by the malformed line. Reissue once with a single straightforward fail-fast capture; do not preserve the attempted placeholder/discard construction.
- **Forensic exception:** No raw receipt exists because Bash parses the complete `-c` program before executing the allocator. This journal event is the compact primary receipt for that parse failure.

### EJ-20260728-0573 — open Slice 7 storage/power consumer authority

- **Predecessor:** `EJ-20260728-0572`
- **Time:** `2026-07-28T23:36:49-07:00` to `2026-07-28T23:36:49-07:00` (`2026-07-29T06:36:49+00:00` UTC)
- **Action:** Reconciled the clean public branch and captured the immutable `require_schedulable_power_final` / `seal_prefix_schedule` / storage-lease contract, all current power/storage implementation references, and the complete power-report schema.
- **Result:** Exit `0`, zero stderr. The bounded capture establishes Slice 7's exact implementation surface without executing any scientific producer or simulator. Next work must separate three authorities before code: completed power-chain consumption, local-test versus confirmation storage capability, and schedule publication ordering. It must not accept caller-mirrored final decisions or implement Task 8's power producer.
- **Compact receipt:** stdout `34,270 B`, `653 lines`, SHA-256 `d9bebed55126d0043fa4880bac105907e7e1fc92ffa188fe8eaf0a6cbb351058`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0573/`.
- **Next gate:** read only the stable consumer transaction and schema-finalization subsections from this local receipt, then implement the smallest complete Slice 7 authority transaction with one focused ≤60-second check.

### EJ-20260728-0574 — capture Slice 7 causal-lock details, with late search RED

- **Predecessor:** `EJ-20260728-0573`
- **Time:** `2026-07-28T23:37:47-07:00` to `2026-07-28T23:37:47-07:00` (`2026-07-29T06:37:47+00:00` UTC)
- **Action:** Captured stable storage/power consumer declarations, completed-final prose, schema keys/body, and the existing artifact power-closure implementation in a fail-fast sequence.
- **Result:** RED, exit `1`, zero stderr, after `38,768 B` / `678` stdout lines. A late exact search returned no matches and stopped the remaining sequence; the receipt is partial and cannot establish that every requested source range executed. Inspect its boundary once, then replace the failed textual assumptions with exact schema definitions/functions rather than broad searches.
- **Compact receipt:** stdout `38,768 B`, `678 lines`, SHA-256 `3caa6de7de66c4a8523945fe7dacc2556b162cbfe750aa92543640f36e64184f`; stderr `0 B`, `0 lines`, SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0574/`.
### EJ-20260728-0575 — classify partial Slice 7 capture and pin consumer invariants

- **Time:** 2026-07-28T23:38:21-07:00 (2026-07-29T06:38:21+00:00)
- **Purpose:** Recover the useful contract evidence from the partial Slice 7 capture and pin the authority-defined consumer boundary before implementation.
- **Result:** Exit 0. The captured authority requires `ScheduleSelection(schedule_authority, selected_tier, selected_task_ids)`, completed-power gating, exact selected-membership scheduling, arm-specific GO/CONDITIONAL_ONLY decisions, and power-final hash ancestry in every prefix. Slice 7 is a consumer of the existing power-final closure, not a Task 8 producer or simulator. The repository already contains substantial power-closure validation in `artifacts.py`; the next inspection will resolve its exact callable surface before any implementation.
- **Compact receipt:** stdout 20,267 bytes / 382 lines / SHA-256 `5ef7d21b1f94f2ef19f0c5dc3d3f66a38d3a79fcae96c01f9012e2bb95fc7179`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0575/` (ignored, retained through 2026-11-27).

### EJ-20260728-0576 — verify EJ-0575 physical placement

- **Time:** 2026-07-28T23:40:00-07:00 (2026-07-29T06:40:00+00:00; command metadata contains the exact timestamps)
- **Purpose:** Capture the live journal head, tail, and diff to verify that the anchorless EJ-0575 patch preserved append-only physical ordering.
- **Result:** Exit 0. The inspection capture completed; its raw receipt is retained for the next explicit review. No scientific or implementation claim was changed.
- **Compact receipt:** stdout 15,448 bytes / 136 lines / SHA-256 `fb6f19d7ec119df79abe0c3a066d8b18fffba3432afe8213a15bdb7c9110954a`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0576/` (ignored, retained through 2026-11-27).

### EJ-20260728-0577 — inspect journal placement and exact power-closure surface

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Review the EJ-0576 placement capture and inspect only the existing power-final closure symbols and implementation required by the Slice 7 consumer.
- **Result:** Exit 0. Captured 1,008 lines for direct review; no files outside the append-only journal were modified.
- **Compact receipt:** stdout 54,186 bytes / 1,008 lines / SHA-256 `3043be41635d1cfb492ad6a244e9c914e0ac4d4e3b096e7ec27b013f7b4cfdc2`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0577/` (ignored, retained through 2026-11-27).

### EJ-20260728-0578 — confirm journal tail and isolate power-final symbols

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Review the bounded placement capture and extract the power-final symbol lines from the larger implementation receipt.
- **Result:** Exit 0. EJ-0575 is physically at the current-volume tail after EJ-0574, so no ordering correction is needed. The existing validator derives completed-chain selection and audits referenced attempt topology in `artifacts.py`; the public consumer seam remains to be resolved before implementation.
- **Compact receipt:** stdout 23,609 bytes / 207 lines / SHA-256 `c1d9415fdf77c1f37a6e26f024e32e2d350f3368dde5a415282b616d29490ab9`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0578/` (ignored, retained through 2026-11-27).

### EJ-20260728-0579 — map the existing artifact API and Slice 7 modules

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Enumerate the artifact module's callable surface and read the current stable types, preflight tail, and assignment implementation before selecting the smallest non-duplicative Slice 7 seam.
- **Result:** Exit 0. The artifact module currently exposes record/root operations but no dedicated public completed-power consumer; its power validation is internal to the scientific-closure machinery. No `ScheduleSelection` or storage-lease value type exists yet. Captured source is read-only.
- **Compact receipt:** stdout 32,594 bytes / 904 lines / SHA-256 `3b4b860735ce0095306e4cbd79dbf51db4fbca2bfdee0aec2feff25fe45f730f`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0579/` (ignored, retained through 2026-11-27).

### EJ-20260728-0580 — resolve Slice 7 authority declarations and power closure

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Reconcile the worktree, capture the immutable Slice 7 declarations, and inspect the power validator's entry/exit plus artifact-root call site.
- **Result:** Exit 0. Captured 792 lines for exact contract analysis. The worktree inspection and source reads made no repository mutation beyond the already-open journal.
- **Compact receipt:** stdout 50,903 bytes / 792 lines / SHA-256 `9b85327eea8539fbfa5743dd19b010c9ae9f588b1bfac12a581320cc2ddc66b3`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0580/` (ignored, retained through 2026-11-27).

### EJ-20260728-0581 — pin exact Slice 7 signatures and completed-chain semantics

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Extract the authority's exact value types/function signatures and the existing completed-chain/failure finalization semantics at their implementation site.
- **Result:** Exit 0. Authority fixes `ScheduleSelection` to the two closed authorities, tier `120 | 160 | None`, and an ordered tuple of task IDs. The existing closure already rejects malformed completed and terminal chains, including authority/decision/tier mismatches and superseded terminal attempts; Slice 7 must reuse that validation and derive membership rather than accept mirrors.
- **Compact receipt:** stdout 26,490 bytes / 614 lines / SHA-256 `3ca3f9d9e0c15a3a0a257111e32cefeca8d0b3f54ff114bcf9940b555b043346`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0581/` (ignored, retained through 2026-11-27).

### EJ-20260728-0582 — inspect exact ref loading and roster extraction primitives

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Determine whether Slice 7 can reuse canonical path/hash/schema/ref loading and roster extraction instead of adding a second parser.
- **Result:** Exit 0. `_read_ref`, `_load_direct_scientific_parent`, `_scientific_documents`, `_manifest_roster_task_ids`, and the power-closure validator already provide the needed fail-closed primitives. Confirmation tier membership still requires exact eligibility-source interpretation; synthetic membership can derive from the manifest-owned registry/roster.
- **Compact receipt:** stdout 16,849 bytes / 436 lines / SHA-256 `59856a70620fa42733c7aed04dabb94dff81c036178f3fba4ac98a5becefacc7`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0582/` (ignored, retained through 2026-11-27).

### EJ-20260728-0583 — add closed ScheduleSelection and inspect membership fixtures

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Added the authority-defined immutable `ScheduleSelection` value type with closed authority/tier rules, nonempty tuple enforcement, and duplicate-ID rejection; then captured its exact diff and the existing manifest, power, and eligibility fixtures.
- **Result:** Exit 0. The new type cannot represent a synthetic tier, a tierless roster-bound decision, an empty membership, or repeated task IDs. No consumer claim is made yet; exact confirmation membership derivation remains the next gate.
- **Compact receipt:** stdout 45,570 bytes / 669 lines / SHA-256 `02579be97168b896b263aa182e65b5c926ea08abbb3c422daf764ebbb08e701e`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0583/` (ignored, retained through 2026-11-27).

### EJ-20260728-0584 — resolve selected membership authority

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Isolate the exact roster/tier membership rules and existing fixture shapes needed by the completed-power consumer.
- **Result:** Exit 0. The manifest-owned roster is already the closed selected population: synthetic schedules its complete ordered roster; confirmation filters the roster's per-row strictly increasing `tiers` by the completed final's selected tier. C120 may be a strict subset of C160. Eligibility remains necessary upstream to prove the roster, but schedule membership is not reconstructed from caller input or the unselected eligible suffix.
- **Compact receipt:** stdout 33,449 bytes / 329 lines / SHA-256 `3c2d660e03132be9c1cebc8029a15b66c42e4d29409f1739d9183e50989b26d6`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0584/` (ignored, retained through 2026-11-27).

### EJ-20260728-0585 — locate consumer module and closure invocation

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Confirm the assignment module's existing authority-loading pattern and the exact place where artifact closure invokes power validation.
- **Result:** Exit 0. `assignment.py` already imports the artifact module's fail-closed scientific-parent loader, while artifact closure passes only power-report documents to `_validate_power_identities`. This supports a thin assignment consumer that reuses the same validator without exposing a producer.
- **Compact receipt:** stdout 6,005 bytes / 199 lines / SHA-256 `09148d09352e09fdf4605ccf6859b86861f23eb91bbc2ce0169d9fdc9ad6cf0a`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0585/` (ignored, retained through 2026-11-27).

### EJ-20260728-0586 — implement and mechanically inspect completed-power consumer

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Implemented `require_schedulable_power_final` in `assignment.py`: exact refs only; manifest/final identity binding; exact final-declared power-chain closure; reuse of the existing full power validator; completed arm enforcement; manifest-owned roster loading; tier-derived membership; synthetic/confirmation authority checks; immutable return. Captured the exact diff and available power-test helpers.
- **Result:** Exit 0; `git diff --check` passed. This is an unverified implementation candidate, not yet a promoted Slice 7 claim. Hostile review and focused tests remain mandatory.
- **Compact receipt:** stdout 12,405 bytes / 281 lines / SHA-256 `9ccaae01865a46bc8e505a7b6faef235363e898557239ad16c91da5959c57bbb`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0586/` (ignored, retained through 2026-11-27).

### EJ-20260728-0587 — locate the narrowest existing power-chain test scaffold

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Avoid building a second giant fixture by locating the existing complete-chain scaffold and reviewing assignment-test conventions.
- **Result:** Exit 0. Complete power-chain construction already lives in `test_artifacts.py`; assignment tests contain no equivalent. The focused Slice 7 consumer test should extend the existing chain scaffold, minimizing test code and runtime.
- **Compact receipt:** stdout 10,156 bytes / 271 lines / SHA-256 `211d49d6c801f7fe227710b909e06f6bb109f9c418024d5344b39942f8134fe5`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0587/` (ignored, retained through 2026-11-27).

### EJ-20260728-0588 — inspect complete-chain fixture reuse boundary

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Read only the complete-chain tests and their record-writing helpers to determine how to exercise the new consumer without duplicating fixture machinery.
- **Result:** Exit 0. `_build_full_study` already constructs valid synthetic and roster-bound completed chains and hostile drift variants. A new `t3_s07` test can derive exact refs from those installed bytes and call the consumer directly; no new power producer/simulator helper is needed.
- **Compact receipt:** stdout 15,707 bytes / 509 lines / SHA-256 `5e6885c87b7e53d789220636b9b06a3fa95ffe123d2349d5daf2f7e0c327f3d5`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0588/` (ignored, retained through 2026-11-27).

### EJ-20260728-0589 — capture installed complete-study paths and builder tail

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Identify the exact manifest/final paths and builder installation sequence for the focused consumer test.
- **Result:** Exit 0. Captured 485 lines of the existing builder and path references; no state changed outside the journal.
- **Compact receipt:** stdout 18,396 bytes / 485 lines / SHA-256 `f721dae8a66dbaf7cdd94a654d5683ac4fa749ec826cc80550cdbeb0df909da5`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0589/` (ignored, retained through 2026-11-27).

### EJ-20260728-0590 — correct builder-range assumption

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Resolve path references from EJ-0589 and detect whether the captured source ranges actually included `_build_full_study`.
- **Result:** Exit 0. The prior range assumption was wrong: `_build_full_study` begins near source line 992, not 3190. The path search confirms `study-manifest.json`; the exact final path still requires the corrected source range. No implementation inference is accepted from the mis-ranged capture.
- **Compact receipt:** stdout 1,659 bytes / 29 lines / SHA-256 `e192d536cfcf2c72df5c0488f8932443cc4abe9c2004024c18aeb86f146faf0f`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0590/` (ignored, retained through 2026-11-27).

### EJ-20260728-0591 — inspect corrected full-study builder range

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Read the actual `_build_full_study` opening and source-install sequence after correcting the prior line-range error.
- **Result:** Exit 0. The legacy artifact-closure fixture uses deliberately minimal raw roster sources (`{"tasks": ...}`), whereas Slice 7's consumer contract requires the newer closed `resampling_roster_v1` grammar. Therefore the consumer test may reuse its power-chain construction but must upgrade the fixture's roster source and confirmation conditional refs; silently weakening the consumer to accept the legacy fixture would violate authority.
- **Compact receipt:** stdout 20,897 bytes / 545 lines / SHA-256 `1e1fea7996ef4c286e7d6b8ae4ccc77c4e086940e79655ed9f38c35f87104804`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0591/` (ignored, retained through 2026-11-27).

### EJ-20260728-0592 — upgrade fixture sources and locate returned authority refs

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Upgraded `_build_full_study` raw task-registry/roster bytes to the closed v1 grammars and paired confirmation eligibility/policy refs while preserving synthetic nulls. Then checked whitespace and located the builder's returned `manifest_ref` plus final-install region.
- **Result:** Exit 0; `git diff --check` passed. The builder returns the exact manifest ref; the focused test can locate the sole installed stage-final report and construct its exact ref from bytes. Existing power construction remains unchanged.
- **Compact receipt:** stdout 13,455 bytes / 372 lines / SHA-256 `3b18d06c826fe0a029655ba615be1d77169424924b8de252b8bd53509a2bdff7`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0592/` (ignored, retained through 2026-11-27).

### EJ-20260728-0593 — focused Slice 7 consumer test exposes fixture-topology drift

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_artifacts.py -q -k t3_s07`
- **Result:** RED, exit 1 in 1.80 seconds: both authority-arm cases stopped before power validation because the upgraded closed roster source was installed under legacy fixture path `raw/roster.json`. The scientific scanner correctly rejects a `resampling_*` object outside the reserved `sources/` subtree as a smuggled scientific record. This contradicts the fixture topology, not the production scanner or closed roster grammar.
- **Correction:** Move this builder's source-blob root from `raw/` to `sources/`, matching `seal_study_manifest`; do not weaken record-smuggling rejection.
- **Compact receipt:** stdout 8,283 bytes / 188 lines / SHA-256 `f7e5cdec8810dae8a820cedea419727faa873784a3cc2bcbaba4a5c988cfa864`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0593/` (ignored, retained through 2026-11-27).

### EJ-20260728-0594 — corrected-topology rerun exposes tier-fixture inconsistency

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** Repeated the same hard-capped focused `t3_s07` command after moving sources to `sources/`.
- **Result:** RED, exit 1 in 1.64 seconds: synthetic passed; roster-bound reached membership derivation and rejected an empty selected set. The legacy completed power fixture selects C160, while the newly formal roster rows declared only C120. This is a fixture self-contradiction the consumer correctly refuses.
- **Correction:** Declare the existing builder's confirmation rows in nested `[120, 160]` tiers and expect its already-frozen C160 final; do not coerce or mirror a caller-selected tier.
- **Compact receipt:** stdout 9,363 bytes / 201 lines / SHA-256 `eb6beca461ea60890750936cd49cb5508393a2d6d74136e92460d1cfa8f59ea8`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0594/` (ignored, retained through 2026-11-27).

### EJ-20260728-0595 — focused completed-power consumer gate passes

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** Repeated the same hard-capped focused `t3_s07` command after aligning the formal roster with the builder's frozen C160 decision.
- **Result:** GREEN, exit 0: both synthetic and roster-bound cases passed; 211 unrelated tests were deselected. Runtime 1.53 seconds. This proves the narrow valid-arm behavior only; hostile mutation coverage and storage/schedule publication remain unfinished.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `5169c6505db2c752953328568d5a6b58b9381862a4f697286053cd30bf96fc78`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0595/` (ignored, retained through 2026-11-27).

### EJ-20260728-0596 — combined static gate for completed-power consumer

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** One combined static gate: Ruff over the resampling-null source/tests, then mypy over the six source modules.
- **Result:** GREEN, exit 0. Ruff: all checks passed. mypy: no issues in six source files. This is static evidence only and does not expand the behavioral claim.
- **Compact receipt:** stdout 86 bytes / 4 lines / SHA-256 `c890f4997c92727adef97347a45394eeec993f24d0febb207d43498d26e80d54`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0596/` (ignored, retained through 2026-11-27).

### EJ-20260728-0597 — hostile review blocks illegal tiny confirmation fixture

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Captured the complete candidate diff/status and reviewed it against the immutable roster authority rather than treating the focused green as sufficient.
- **Result:** BLOCKING FINDING. The positive confirmation case labeled two rows as C160, contradicting the explicit rule that every benchmark/tier `t` has exactly `t` rows. The consumer also did not independently check supported tiers, registry order, complete group labels, per-benchmark tier counts, or resolve the eligibility ref. These omissions could let a malformed roster ride behind an internally consistent power mirror.
- **Correction implemented after capture:** Isolate the closed consumer fixture from legacy artifact tests; generate a real nested 120/160 confirmation roster; validate supported tiers, ordered metadata, complete groups, tier subsets/counts, and eligibility bytes in the consumer.
- **Compact receipt:** stdout 15,651 bytes / 409 lines / SHA-256 `5ea053c0840d968089f5fe3b61b976c480ca9ab8e8ab3c0970103c2bb4aa1001`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0597/` (ignored, retained through 2026-11-27).

### EJ-20260728-0598 — hostile-correction rerun catches missing runtime import

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** Same hard-capped focused `t3_s07` command after implementing the real nested roster and deeper consumer checks.
- **Result:** RED, exit 1 in 1.74 seconds: both cases reached the new canonical-order check and raised `NameError: cast is not defined`. The correction used `typing.cast` without importing it. No authority behavior was evaluated beyond that line.
- **Correction:** Add the missing runtime import, then repeat only the same focused command.
- **Compact receipt:** stdout 5,267 bytes / 134 lines / SHA-256 `8291d53c3debf138f67fb5424b2109c473a308e50647241c6340aafb19b45105`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0598/` (ignored, retained through 2026-11-27).

### EJ-20260728-0599 — real nested-roster consumer gate passes

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** Same hard-capped focused `t3_s07` command after importing `cast`.
- **Result:** GREEN, exit 0: synthetic complete-roster selection and a genuine per-benchmark nested C120/C160 confirmation roster both passed; 211 unrelated tests were deselected. Runtime 1.33 seconds.
- **Scope:** This validates the completed-power consumer only. Storage capability and prefix-schedule transaction publication remain unfinished and unclaimed.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `33809ff9c65f994fb51a7939da7c851401e81c074fe5c0af96fc219f1a566cef`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0599/` (ignored, retained through 2026-11-27).

### EJ-20260728-0600 — final static gate after hostile corrections

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** Repeated the one combined Ruff+mypy static gate because production and fixture code changed after EJ-0596.
- **Result:** GREEN, exit 0. Ruff passed; mypy found no issues in six source files.
- **Compact receipt:** stdout 86 bytes / 4 lines / SHA-256 `c890f4997c92727adef97347a45394eeec993f24d0febb207d43498d26e80d54`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0600/` (ignored, retained through 2026-11-27).

### EJ-20260728-0601 — deliver Slice 7A completed-power consumer

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Checked whitespace/status, staged exactly the two source files, focused fixture/test file, and live journal; checked the staged diff; committed `feat(neurips): gate schedules on completed power`; pushed the public branch; compared local and remote refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `e34a5d2dc5357bebb013ae631345e3c27522937f`. Four files, 621 insertions and 13 deletions. The untracked `raw_root_placeholder` was observed and deliberately left untouched/uncommitted because it is outside this delivery's known scope.
- **Compact receipt:** stdout 813 bytes / 14 lines / SHA-256 `08825227a9aa63398765922b3b5804374ad79172b982647973bb2996b50ec6e5`; stderr 134 bytes / 2 lines / SHA-256 `52074b533faadddee85fb24f70bbff58440c606b4947d158315a10ebb1df42c9`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0601/` (ignored, retained through 2026-11-27).

### EJ-20260728-0602 — open Slice 7B storage publication authority

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Capture the exact storage value records, transaction ordering, local-test/confirmation capability split, retry semantics, and current implementation references before writing Slice 7B.
- **Result:** Exit 0. Captured 326 lines. No storage transaction implementation currently exists in the source tree; the worktree otherwise contains the live journal plus the unrelated untracked `raw_root_placeholder`.
- **Compact receipt:** stdout 17,731 bytes / 326 lines / SHA-256 `53a31c4cdae7ca980ac32d8caa8f2f0b3f6f51553ace5248409a41cd2654761d`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0602/` (ignored, retained through 2026-11-27).

### EJ-20260728-0603 — reduce storage authority to transaction invariants

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Review the captured Slice 7B authority verbatim and isolate the enforceable state machine.
- **Result:** Exit 0. Prefix storage ordering is: claim exact lease before seed/selection/destination; begin; deterministic preparation; fsynced temporary science; non-releasing end; immutable fsynced intent; prove remaining lifetime; atomic science install+parent fsync; durable registry commit consuming lease; exact fixed receipt install+parent fsync. Pre-install abort is recoverable; post-install/pre-commit bytes are permanently quarantined; post-commit recovery may only reproduce the same receipt. Confirmation requires a nominal trusted registry and remains unavailable; local-test uses an exact one-use process lock.
- **Compact receipt:** stdout 17,731 bytes / 326 lines / SHA-256 `53a31c4cdae7ca980ac32d8caa8f2f0b3f6f51553ace5248409a41cd2654761d`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0603/` (ignored, retained through 2026-11-27).

### EJ-20260728-0604 — capture storage observation and intent value contracts

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Recover the preceding storage observation/intent declarations and exact local-test claim interface omitted from the first bounded capture.
- **Result:** Exit 0. Captured 225 lines for direct review; no repository state changed outside the journal.
- **Compact receipt:** stdout 10,046 bytes / 225 lines / SHA-256 `c312d6c478b596f86cae134ac1b48f9867310cd845f5c71cccb920c9ba6fa6de`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0604/` (ignored, retained through 2026-11-27).

### EJ-20260728-0605 — review storage value contracts and recovery boundary

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Display the EJ-0604 capture for direct analysis and preserve an independently addressed raw receipt.
- **Result:** Exit 0. Exact local/confirmation attestation, intent, publication-commit, and receipt fields are pinned. The registry terminal states are mutually exclusive; recovery cannot invoke commit; local commit IDs are deterministic from intent digest; operational state is excluded from scientific closure.
- **Compact receipt:** stdout 10,046 bytes / 225 lines / SHA-256 `c312d6c478b596f86cae134ac1b48f9867310cd845f5c71cccb920c9ba6fa6de`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0605/` (ignored, retained through 2026-11-27).

### EJ-20260728-0606 — capture local storage contract and seed-binding seam

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Recover the exact local-test policy contract, trusted-registry method boundary, and existing seed commitment/derivation references needed for prefix sealing.
- **Result:** Exit 0. Captured 405 lines for direct review; no implementation change occurred.
- **Compact receipt:** stdout 30,466 bytes / 405 lines / SHA-256 `c3ebf400349c5a5895111820af03334d434a90c5e69c74c28d8e7c30f83e3599`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0606/` (ignored, retained through 2026-11-27).

### EJ-20260728-0607 — review local contract and schedule call boundary

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Display the bounded local-policy/registry/schedule excerpt before selecting the implementation seam.
- **Result:** Exit 0. The local policy is a closed explicit non-enforcement record; confirmation storage is only obtainable from `ConfirmationPreflightRegistry.claim_storage`; `seal_prefix_schedule` consumes an already-claimed lease. Therefore core needs a local-only claim factory and one-use nominal lease, while the existing confirmation registry continues to fail closed until its trusted adapter exists.
- **Compact receipt:** stdout 10,467 bytes / 180 lines / SHA-256 `b70e05236dd84e23c67d976998207cc4a940cf9d4c00382ff3f3529971551622`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0607/` (ignored, retained through 2026-11-27).

### EJ-20260728-0608 — implement and focus-check nominal local storage lease

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Added `storage.py` with the exact local attestation/intent/commit/receipt value records, unavailable non-subclassable confirmation lease, non-public exact local lease construction, deterministic tuple binding, exclusive OS transaction lock, begin/end/commit/abort terminal states, copy/serialization rejection, and closed local policy claim. Added one focused lease test and upgraded only the isolated Slice 7 fixture's policy bytes.
- **Result:** GREEN, exit 0. Three `t3_s07` cases passed; 211 unrelated tests deselected. Runtime 2.09 seconds. Publication orchestration is not yet implemented or claimed.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `e0e7f389b71e35a0c0de0690599b7828f940808b28bb1ce816ee8af820d994d6`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0608/` (ignored, retained through 2026-11-27).

### EJ-20260728-0609 — static wrapper exits before compact receipt

- **Time:** command metadata records exact local and UTC start timestamps.
- **Action:** Invoked the combined Ruff+mypy gate, but the wrapper used `exit 1` inside the redirected command group. On a finding, that exited the shell before status, display, byte-count, and hash commands ran.
- **Result:** RED/incomplete wrapper. Tool exit was 1 with no displayed output. Raw stdout/stderr files exist, but their contents and hashes are deliberately not inferred here. The next event will inspect those retained files and distinguish code findings from wrapper behavior.
- **Forensic note:** This event has no complete compact receipt because the wrapper terminated before producing it; do not rerun the checks until the existing raw outputs are classified.

### EJ-20260728-0610 — classify EJ-0609 static output

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Read the retained EJ-0609 metadata/stdout/stderr once and computed the missing compact receipt.
- **Result:** Ruff passed. mypy found exactly one issue: `LocalTestStorageLease.__reduce__` was annotated as returning `object`, broader than `object.__reduce__`'s allowed return. This is a typing defect in an always-raising anti-serialization method, not a runtime test failure.
- **EJ-0609 recovered receipt:** stdout 280 bytes / 5 lines / SHA-256 `2b50ade43023335727ba6023bfb570abf58d424f3d59c5df26b20d70a3aef95f`; stderr empty.
- **Compact receipt:** stdout 964 bytes / 17 lines / SHA-256 `d7e11c0f9fb62c5184cf9e8bc0c3bc3c5274da6621c665663c31943eb066e7dc`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0610/` (ignored, retained through 2026-11-27).

### EJ-20260728-0611 — corrected combined static gate passes

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** Repeated Ruff+mypy with a wrapper that records both statuses without exiting its shell early.
- **Result:** GREEN, exit 0. Ruff passed; mypy found no issues in seven source files.
- **Hostile follow-up:** Static success does not prove runtime authority. Manual review immediately identified three pre-delivery gaps: runtime transaction allowlisting, explicit synthetic-manifest binding, and no-follow lock-file opening. These are being corrected before promotion.
- **Compact receipt:** stdout 86 bytes / 4 lines / SHA-256 `1adc478a560d3a14d1ea46e6acabf21cf4deb367170dd8186ba95d5bd5c27185`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0611/` (ignored, retained through 2026-11-27).

### EJ-20260728-0612 — hostile-corrected local lease gate passes

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Added runtime transaction allowlisting before path use, explicit synthetic manifest/roster binding, and directory-relative `O_NOFOLLOW|O_CLOEXEC` lock opening. Extended the same focused lease test with a traversal-shaped transaction and confirmation-manifest misuse.
- **Result:** GREEN, exit 0. Three focused `t3_s07` tests passed; 211 unrelated tests deselected. Runtime 2.20 seconds.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `69ee95a07aeacec136a548bf0540d9cc7faa27fbfbc766057a6a78af0b3433ae`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0612/` (ignored, retained through 2026-11-27).

### EJ-20260728-0613 — final static gate for local storage capability

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** One combined Ruff+mypy gate after hostile runtime/path corrections.
- **Result:** GREEN, exit 0. Ruff passed; mypy found no issues in seven source files.
- **Compact receipt:** stdout 86 bytes / 4 lines / SHA-256 `1adc478a560d3a14d1ea46e6acabf21cf4deb367170dd8186ba95d5bd5c27185`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0613/` (ignored, retained through 2026-11-27).

### EJ-20260728-0614 — deliver Slice 7B1 nominal local storage capability

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Checked whitespace/status, staged exactly `storage.py`, the focused fixture/test file, and the live journal; checked staged scope; committed `feat(neurips): add nominal local storage lease`; pushed publicly; compared refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `b4b4a09da1f1ec0df722b078a4fb5e5f15652043`. Three files, 691 insertions and one deletion. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Compact receipt:** stdout 736 bytes / 13 lines / SHA-256 `24d2e348e1f0a3994f3d1565bb47282d9525a84097c5fc428f1327c334d4c062`; stderr 134 bytes / 2 lines / SHA-256 `d18a19e4aa4a6a5a4e3d89826448aba8d58d213038c9ef2079664daa3e22fdc9`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0614/` (ignored, retained through 2026-11-27).

### EJ-20260728-0615 — open deterministic prefix-schedule derivation seam

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Inventory existing preflight loaders, provider-lane grammar, and schedule-seed commitment primitives before implementing schedule publication over the new lease.
- **Result:** Exit 0. Captured 270 lines. The next implementation must reuse the closed manifest-owned asset parsers and existing typed KDF/commitment functions; no caller-supplied provider or task mirrors are needed.
- **Compact receipt:** stdout 24,205 bytes / 270 lines / SHA-256 `209605a871647d9b05ba244ce271628a348722d3c866dbdbaccdd54d65f0fcc0`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260728-0615/` (ignored, retained through 2026-11-27).

### EJ-20260729-0001 — roll journal date and resolve prefix derivation inputs

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Start the new local-date event sequence and review EJ-0615's exact loader/provider/commitment capture.
- **Result:** Exit 0. Preflight exposes strict task-registry and assignment-program importers but no provider-plan consumer; Slice 7B2 must implement a closed provider-plan loader. Schedule seed verification reuses the existing typed `commitment_sha256("schedule-seed", study_id, U64Field(seed))`. Provider rows bind a canonical task-sorted complete mapping to prefix lane and four execution-rank lanes.
- **Compact receipt:** stdout 24,205 bytes / 270 lines / SHA-256 `209605a871647d9b05ba244ce271628a348722d3c866dbdbaccdd54d65f0fcc0`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0001/` (ignored, retained through 2026-11-27).

### EJ-20260729-0002 — implement local publication happy path

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Added same-directory fsynced preparation, no-replace hard-link install, fsynced operational intent, bounded post-end lifetime check, durable deterministic local commit proof, fixed receipt construction, and parent fsync. Added one focused binding test covering science bytes, intent/commit digest equality, durable registry proof, acceptance marker, and consumed-lease reuse rejection.
- **Result:** GREEN, exit 0. Four focused `t3_s07` tests passed; 211 unrelated tests deselected. Runtime 2.67 seconds.
- **Caveat:** This proves the initial happy path only. Crash recovery, pre-install intent replacement, and the schedule-specific deterministic preparer remain unfinished and unclaimed.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `d45e50186599622f5a27e6a7b3d2e5eda11495af566f1842dfef41a6d5e7ac14`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0002/` (ignored, retained through 2026-11-27).

### EJ-20260729-0003 — capture slot identity and schedule schema primitives

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Resolve authority for slot IDs, membership digest, execution ordering, task parsing, commitment verification, and stable schedule types before coding the preparer.
- **Result:** Exit 0. Captured 503 lines for bounded analysis; no repository mutation outside the journal.
- **Compact receipt:** stdout 21,501 bytes / 503 lines / SHA-256 `0de8b4fa5b4ff1e03ddfc72a9e4da6ed47b7d612fc943b2cb0ff1f309b1417d6`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0003/` (ignored, retained through 2026-11-27).

### EJ-20260729-0004 — resolve schedule ordering and slot-identity boundary

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Extract only slot, membership, and execution-order authority from EJ-0003.
- **Result:** Exit 0. Authority fixes slot array ordinal order and seed/order roles but does not prescribe a separate free-form slot-ID derivation. To avoid a new derivation role, Slice 7B2 will use the full SHA-256 digest of the already-authorized `slot-{ordinal}` derive-seed frame as the opaque slot ID, while the seed stores its first eight bytes. Execution rank separately uses the full authorized `execution-order-{ordinal}` frame digest with ordinal collision fallback.
- **Compact receipt:** stdout 13,751 bytes / 264 lines / SHA-256 `b89e825db9397af58f60c297903aec9c69e7f72900c0c21e05c9ec4f8e1d0447`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0004/` (ignored, retained through 2026-11-27).

### EJ-20260729-0005 — implement candidate deterministic schedule preparer

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Added `schedule.py` with manifest-only asset loading, full completed-power selection, typed seed-commitment verification, strict task/provider parsing, membership digest recomputation, canonical task/group ordering, authorized prefix/slot/order KDF roles, full-digest opaque slot IDs, deterministic execution ranks, frozen lane mapping, schema validation, and publication through the live lease. Privatized the generic publication helper. Captured the assignment-program grammar and fixture references for the next test fixture correction.
- **Result:** Exit 0; `git diff --check` passed. This is an untested candidate; no schedule-publication claim is promoted.
- **Compact receipt:** stdout 8,081 bytes / 134 lines / SHA-256 `32fa6cdc9f2bae36ee69c0b49deb74d1eb829d42811666909bad31f86f792be5`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0005/` (ignored, retained through 2026-11-27).

### EJ-20260729-0006 — review assignment-program grammar for schedule fixture

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Display the captured assignment-program validator and locate its canonical test fixture without another broad source read.
- **Result:** Exit 0. The schedule fixture must supply the closed synthetic mode/algorithm, strict cutpoints, bound normalizer source/digest/tokenizer/components, CPython runtime identity, null backend, and ordered unique stratum keys. The candidate preparer must additionally enforce the top-level closed key set because `_validate_assignment_program` validates semantics but assumes its importer already enforced closure.
- **Compact receipt:** stdout 8,081 bytes / 134 lines / SHA-256 `32fa6cdc9f2bae36ee69c0b49deb74d1eb829d42811666909bad31f86f792be5`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0006/` (ignored, retained through 2026-11-27).

### EJ-20260729-0007 — focused deterministic schedule publication gate passes

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Upgraded only the isolated Slice 7 fixture with a closed assignment program, complete provider-lane plan, and real purpose-bound schedule-seed commitment. Added one focused end-to-end schedule publication test.
- **Result:** GREEN, exit 0. Five focused `t3_s07` tests passed; 211 unrelated tests deselected. Runtime 3.06 seconds. The test proves manifest/final-derived membership, seed commitment, two-task canonical schedule construction, distinct slot IDs, complete execution ranks, frozen lane mapping, durable publication, and receipt/science digest binding for the synthetic fixture.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `9a4c6224c977a6a7d6c6b4be82c57e967e9f73dff5248e65eba6347d2db077c5`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0007/` (ignored, retained through 2026-11-27).

### EJ-20260729-0008 — schedule static gate finds one unused import

- **Time:** command metadata records exact local and UTC timestamps.
- **Command:** Combined Ruff+mypy gate after schedule implementation.
- **Result:** RED, exit 1. mypy passed eight source files. Ruff found exactly one unused `typing.Any` import in `schedule.py`; no behavioral or typing defect was reported.
- **Correction:** Remove the unused import manually and repeat only the static gate.
- **Compact receipt:** stdout 456 bytes / 17 lines / SHA-256 `025443e2799ba0cfe217fd0832b5db2312d484dfe749a9745c5de70d618cf5ae`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0008/` (ignored, retained through 2026-11-27).

### EJ-20260729-0009 — corrected schedule static gate passes, hostile review continues

- **Time:** command metadata records exact local and UTC timestamps.
- **Result:** GREEN, exit 0. Ruff passed; mypy found no issues in eight source files.
- **Blocking hostile findings:** The schedule entry point must explicitly prove that the exact lease is prefix-bound to the same manifest/root/null schedule and that assignment mode matches schedule authority. The publication layer also lacks the authority-required pre-install abort/intent replacement and post-commit fixed-receipt recovery paths. Slice 7B2 remains unpromoted until these are fixed.
- **Compact receipt:** stdout 86 bytes / 4 lines / SHA-256 `e6c3ec4c203d4605609414c799cc19d939ce33570b35e3d1a8dd5e9f53f7a937`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0009/` (ignored, retained through 2026-11-27).

### EJ-20260729-0010 — recovery- and binding-corrected schedule gate passes

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Bound schedule publication to the exact prefix lease tuple and authority-compatible assignment mode. Added durable post-commit receipt recovery without preparer re-execution, rejection/quarantine when a unique proof is absent, and pre-install stale-intent abort proof/replacement when science and commit are absent. Extended the focused cases with wrong-seed no-write and post-commit deterministic recovery.
- **Result:** GREEN, exit 0. Five focused `t3_s07` tests passed; 211 unrelated tests deselected. Runtime 3.82 seconds.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `7d56196d9cd6f8f06ae701c536f4248ac3353b65a456eac5cc7451745e6c4b7a`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0010/` (ignored, retained through 2026-11-27).

### EJ-20260729-0011 — recovery static gate finds one unused import

- **Time:** command metadata records exact local and UTC timestamps.
- **Result:** RED, exit 1. mypy passed eight source files. Ruff found one unused `collections.abc.Mapping` import in `storage.py`; the recovery implementation uses runtime `dict` checks instead.
- **Correction:** Remove the unused import and repeat only the static gate.
- **Compact receipt:** stdout 538 bytes / 17 lines / SHA-256 `7c212fa9a9b5768cdf66dee1f75b2a11944c535c3efcb551d571de56773a80da`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0011/` (ignored, retained through 2026-11-27).

### EJ-20260729-0012 — corrected recovery static gate passes; proof-splicing review blocks

- **Time:** command metadata records exact local and UTC timestamps.
- **Result:** GREEN, exit 0. Ruff passed; mypy found no issues in eight source files.
- **Blocking hostile finding:** Recovery still accepted a proof located by intent digest without fully closing and cross-binding its authority, lease, generation, expiry, root, mount, local-policy fields, deterministic commit ID/path, and commit freshness. That could turn recovery into a receipt-splicing oracle if operational bytes were tampered with.
- **Correction implemented after capture:** Added exact intent/attestation lifecycle validation, exact proof shape, full tuple cross-binding, deterministic commit-ID/path recomputation, ordered/fresh timestamps, and a forged-extra-field recovery rejection case.
- **Compact receipt:** stdout 86 bytes / 4 lines / SHA-256 `e6c3ec4c203d4605609414c799cc19d939ce33570b35e3d1a8dd5e9f53f7a937`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0012/` (ignored, retained through 2026-11-27).

### EJ-20260729-0013 — proof-splicing-resistant recovery gate passes

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Added closed local intent/attestation validation and fully cross-bound commit-proof recovery. Injected an extra-field forged proof, verified recovery rejected it without running the preparer, restored the original durable proof, and verified deterministic receipt finalization.
- **Result:** GREEN, exit 0. Five focused `t3_s07` tests passed; 211 unrelated tests deselected. Runtime 3.47 seconds.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `c98f326b373c65bc6932c235905b0b8f91e00616a5909ac3e2d972a56381367d`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0013/` (ignored, retained through 2026-11-27).

### EJ-20260729-0014 — final static gate for Slice 7B2 candidate

- **Time:** command metadata records exact local and UTC timestamps.
- **Result:** GREEN, exit 0. Ruff passed; mypy found no issues in eight source files.
- **Compact receipt:** stdout 86 bytes / 4 lines / SHA-256 `e6c3ec4c203d4605609414c799cc19d939ce33570b35e3d1a8dd5e9f53f7a937`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0014/` (ignored, retained through 2026-11-27).

### EJ-20260729-0015 — full diff review blocks incomplete assignment-asset closure

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Captured the full source/test diff and status for hostile pre-delivery review.
- **Result:** Exit 0; whitespace passed. BLOCKING FINDING: schedule reloads and semantically validates the assignment program but does not yet resolve its normalizer implementation ref, prove exact manifest source-revision ownership, bind the report tokenizer digest, or compare the frozen CPython/Unicode runtime to the executing controller. A dangling or lookalike program dependency could therefore reach schedule publication.
- **Correction:** Add all four independent checks and update only the isolated fixture's pinned sources/runtime.
- **Compact receipt:** stdout 34,009 bytes / 918 lines / SHA-256 `60173604dd54b21f564054585577c329431fa86c1359243d8bd0084fc6dd4dd4`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0015/` (ignored, retained through 2026-11-27).

### EJ-20260729-0016 — complete assignment-asset closure gate passes

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Resolved and hashed the normalizer implementation, required exact manifest source-revision membership, resolved and bound the report tokenizer, and compared the frozen CPython/Unicode runtime to the executing controller. Also rechecked science absence immediately before stale-intent abort.
- **Result:** GREEN, exit 0. Five focused `t3_s07` tests passed; 211 unrelated tests deselected. Runtime 3.40 seconds.
- **Compact receipt:** stdout 114 bytes / 2 lines / SHA-256 `7bd9fc06a854c0ff669c55521f73e860a86c39c07273c0125912f300b134963c`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0016/` (ignored, retained through 2026-11-27).

### EJ-20260729-0017 — final static gate after dependency-closure correction

- **Time:** command metadata records exact local and UTC timestamps.
- **Result:** GREEN, exit 0. Ruff passed; mypy found no issues in eight source files.
- **Compact receipt:** stdout 86 bytes / 4 lines / SHA-256 `e6c3ec4c203d4605609414c799cc19d939ce33570b35e3d1a8dd5e9f53f7a937`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0017/` (ignored, retained through 2026-11-27).

### EJ-20260729-0018 — deliver Slice 7B2 deterministic prefix publication

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Checked whitespace/status, staged exactly schedule/storage source, focused fixture/tests, and live journal; checked staged scope; committed `feat(neurips): publish deterministic prefix schedules`; pushed publicly; compared refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `809141e2d9f093da2115d951f1950aaa5b2cedfb`. Four files, 1,413 insertions and eight deletions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Compact receipt:** stdout 876 bytes / 15 lines / SHA-256 `e37eede9687d65b06d0cf383962be1e81479b0a7c2823f61159a0799070bbd53`; stderr 134 bytes / 2 lines / SHA-256 `f282b8acde441f994057d5001ef0f6c10b8d36bab205f18c6495156c8711caa4`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0018/` (ignored, retained through 2026-11-27).

### EJ-20260729-0019 — reconcile next Task 3 slice and canonical status

- **Time:** command metadata records exact local and UTC timestamps.
- **Action:** Enumerated immutable plan task/step/slice headings, inspected worktree scope, and ran the canonical status checker.
- **Result:** Exit 0, zero stderr. Captured 72 lines for next-slice routing; canonical project status currently passes. The live journal and unrelated `raw_root_placeholder` remain the only expected open worktree items.
- **Compact receipt:** stdout 3,365 bytes / 72 lines / SHA-256 `78e522eb74241c20147dac357af157e6c0a758e4cb7f7c94cb45e36b4b0b0364`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0019/` (ignored, retained through 2026-11-27).

### EJ-20260729-0020 — review next-task routing capture

- **Time:** command metadata records exact local and UTC timestamps.
- **Result:** Exit 0. The immutable plan organizes Task 3 as one large eight-step task rather than named slices. Current work has not completed all of Task 3 Step 4/5: assignment sealing, prefix-view construction, matching, allocation, and reconstruction remain. Routing must therefore use the execution design's slice ledger rather than jumping prematurely to Task 4.
- **Compact receipt:** stdout 3,365 bytes / 72 lines / SHA-256 `78e522eb74241c20147dac357af157e6c0a758e4cb7f7c94cb45e36b4b0b0364`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0020/` (ignored, retained through 2026-11-27).

### EJ-20260729-0021 — locate execution-design slice ledger and assignment remainder

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Search immutable design/plan plus current journal for the named Slice 7/8 boundary and remaining assignment reconstruction contract.
- **Result:** Exit 0. The broad context capture is 433 lines and requires one bounded extraction before routing; no implementation conclusion is inferred from unreviewed matches.
- **Compact receipt:** stdout 81,471 bytes / 433 lines / SHA-256 `703582516b2df947c1f06ecad7e5077d14b1e510dd5571b99c242b0c8e6179a5`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0021/` (ignored, retained through 2026-11-27).

### EJ-20260729-0022 — classify next Task 3 boundary as branch assignment

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Extract only named slice and branch-assignment matches from EJ-0021.
- **Result:** Exit 0. The plan explicitly labels completed-power consumption as slice 7. The next unfinished transaction is `seal_branch_assignment`: it must accept only schedule/prefix refs, load the manifest transitively, prove prefix completeness and selected membership, consume an assignment-bound storage lease, then execute the frozen prefix-view/matching/allocation algorithms and reconstruction gate. Task 8 remains forbidden here because it exclusively owns power production/simulation.
- **Compact receipt:** stdout 54,969 bytes / 310 lines / SHA-256 `ce646616138c762f7c3f2c9eb269f5263afdab60a6ffe6be07bd6c0b13fb6a3f`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0022/` (ignored, retained through 2026-11-27).

### EJ-20260729-0023 — open branch-assignment authority and current primitives

- **Time:** command metadata records exact local and UTC timestamps.
- **Purpose:** Capture stable assignment value records, complete Step 4/5 prose, current assignment/secrets callables, and any pre-existing slice tests.
- **Result:** Exit 0. Captured 641 lines for bounded classification; no implementation inference is accepted until its five authority sub-boundaries are extracted.
- **Compact receipt:** stdout 32,941 bytes / 641 lines / SHA-256 `83e40708ab76181d787605f7347626dc4e09bb45ba23fbba001247637bad8b0a`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0023/` (ignored, retained through 2026-11-27).

### EJ-20260729-0024 — display branch-assignment capture; model-context truncation

- **Time:** command metadata records exact local and UTC timestamps in the retained raw receipt.
- **Action:** Displayed the complete EJ-0023 branch-assignment authority capture for review.
- **Result:** Exit 0. The 641-line display exceeded the active model-context boundary and triggered compaction. No scientific or implementation inference is accepted from the truncated display.
- **Forensic correction:** Preserve the raw receipt unchanged and compute its byte counts, line counts, and hashes in the next bounded receipt-inspection event. Do not guess that a displayed copy necessarily equals its source.
- **Compact receipt:** stdout 32,941 bytes / 641 lines / SHA-256 `83e40708ab76181d787605f7347626dc4e09bb45ba23fbba001247637bad8b0a`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0024/` (ignored, retained through 2026-11-27).

### EJ-20260729-0025 — resume after compaction and inspect journal tail

- **Time:** command metadata records the resumed command timing.
- **Action:** Read the final 100 lines of the live journal to reconstruct the exact durable event boundary before taking substantive action.
- **Result:** Exit 0. The journal ends at EJ-0023 and confirms EJ-0024 is the sole unclassified retained command. The current user testing standard is also reaffirmed: software tests remain insignificant tripwires, never research deliverables.
- **Compact receipt:** exact byte/hash measurement unavailable because this resumed command predated restoration of the receipt wrapper; stdout was 100 rendered lines and stderr was empty. Its rendered command result is the forensic source. The initially drafted byte count was removed because tool token metadata is not a byte count.

### EJ-20260729-0026 — classify retained EJ-0024 receipt exactly

- **Time:** command metadata records exact timing.
- **Action:** Listed the three retained receipt files and computed line counts, byte counts, and SHA-256 hashes without replaying raw authority output.
- **Result:** Exit 0. EJ-0024 stdout is byte-for-byte identical to EJ-0023 stdout. Its metadata is 81 bytes / 3 lines / SHA-256 `2117850edef0b35b0abbf9d42f9ae869e8609cd26439c14e4c9a6f6abaf2d438`; stderr is empty.
- **Compact receipt:** rendered stdout 195 tokens; stderr empty. This command also preceded restoration of the wrapper, so its rendered command result is the forensic source.

### EJ-20260729-0027 — reaffirm research-first verification budget

- **Decision:** User explicitly clarified that this is research, not a production SaaS, and software tests must remain a trivial, insignificant part of the work.
- **Standing execution rule:** One narrow high-signal behavioral command and one static command per slice, each hard-capped at 60 seconds. Broad/repeated suites require a concrete shared-surface risk or explicit request. Scientific experiments and falsification remain separate evidence work.
- **Repository authority:** `AGENTS.md` already contains this exact standing rule; no redundant policy edit was needed.

### EJ-20260729-0028 — reconcile assignment-core worktree

- **Action:** Inspected status/diff scope, the standing test policy, stable assignment value records, current key derivation tail, and storage-publication primitives.
- **Result:** Only the live journal was modified; unrelated `raw_root_placeholder` remained untouched. Existing code had authority loading, completed-power consumption, exact KDF/HMAC primitives, and storage publication, but no allocation or synthetic matching implementation.

### EJ-20260729-0029 — reopen exact allocation and capability authority

- **Action:** Read the immutable Step-5 allocation table, prefix allowlist, synthetic-matching proof grammar, and exact capability frame/KAT.
- **Result:** The scientific separation is explicit: allocation/orientation bind only task ID, while capabilities bind study plus manifest/schedule/prefix ancestry, task, slot, and realized arm.

### EJ-20260729-0030 — implement assignment scientific core

- **Action:** Added closed prefix-view/allocation value records; exact allowlist serialization; the 12-row treatment table; unbiased allocation and null-orientation draws; exact capability derivation; and the first-valid synthetic cyclic-offset proof with same-lineage and reciprocal-two-cycle rejection.
- **Boundary:** This slice does not yet publish an assignment ledger or claim Task 3 completion. Caller-provided prefix views remain forbidden at the eventual public transaction boundary.

### EJ-20260729-0031 — focused assignment check exposes KAT expectation error

- **Command:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_assignment.py -q -k t3_s08`
- **Result:** RED, exit 1 in 0.34 seconds. The test compared the published `slot-0/REAL` capability KAT against the realized `slot-0/NONE` capability from deterministic allocation row 3. The allocation and capability derivations were internally correct; the assertion conflated two different arms.
- **Correction:** Factor exact capability derivation and evaluate the published KAT independently from the realized assignment map.

### EJ-20260729-0032 — corrected focused assignment check

- **Result:** GREEN, exit 0. One `t3_s08` test passed, 82 unrelated tests deselected, runtime 0.30 seconds.
- **Coverage:** Exact synthetic proof/mapping agreement, no self/same-lineage donation, normative allocation/orientation draw, exact four-arm map, published capability KAT, and the causal metamorphism that prefix changes preserve arm draws but alter ancestry-bound capabilities.

### EJ-20260729-0033 — initial narrow static check

- **Result:** GREEN, exit 0. Ruff passed the two source files plus focused test; mypy found no issues in the two changed source files. Total wall time was below one second.

### EJ-20260729-0034 — hostile diff review blocks permissive scalar grammar

- **Action:** Reviewed the complete source/test diff against the immutable causal and serialization contracts.
- **Blocking findings:** `bytes.fromhex` admitted uppercase ancestry digests; Python membership admitted booleans as orientation integers; prefix groups could be empty or duplicate dimensions; synthetic stratum/digest inputs were under-validated.
- **Correction:** Require exact lowercase 64-hex, exact integer orientation, non-empty unique group dimensions, exact prefix-task tuple, non-empty strict-text stratum key, and closed digests.
- **Nonblocking boundary:** Global capability uniqueness, internal verifier-feature reconstruction, no-trigger consistency, CAS proof publication, key wiping, and storage-bound ledger installation belong to the still-unfinished transaction orchestrator and remain unclaimed.

### EJ-20260729-0035 — locate receipt mechanism

- **Action:** Searched shell history and repository scripts for a reusable generic raw command-receipt wrapper.
- **Result:** No generic wrapper exists; the research scripts are domain-specific. Final gates for this slice will therefore use a bounded local stdout/stderr capture under the ignored journal receipt root.

### EJ-20260729-0036 — corrected final assignment-algorithm gate

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Command:** Ran exactly one focused `t3_s08` behavioral selection, then one combined Ruff+mypy static gate; both process groups were hard-capped at 60 seconds.
- **Result:** GREEN, exit 0. One focused test passed with 82 unrelated tests deselected in 0.22 seconds. Ruff passed; mypy found no issues in the two changed source files.
- **Compact receipt:** stdout 175 bytes / 4 lines / SHA-256 `3a2cf90d5981650ee368e5eb0c661e2183f09278a72cc9d84513d1d00053d086`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0036/` (ignored, retained through 2026-11-27).

### EJ-20260729-0037 — publish synthetic assignment-algorithm slice

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Action:** Checked whitespace and worktree scope; staged exactly assignment/types source, the single focused test, and live journal; checked staged whitespace/stat; committed `feat(neurips): freeze synthetic assignment algorithms`; pushed the public branch; compared exact local/remote refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `2d8344398cceb077c0f98df6934e0c0966eaf1cd`. Four files, 702 insertions and one deletion. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Compact receipt:** stdout 816 bytes / 15 lines / SHA-256 `ca3b9362aa7dff25024247b9d09710d31bdeb7ae518030067508b71be771115f`; stderr 134 bytes / 2 lines / SHA-256 `dfc793a7f46f8ba540b84231dd913777929f4d32c2793e3fdf3427f6d3023a6d`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0037/` (ignored, retained through 2026-11-27).
- **Claim boundary:** This commit freezes the synthetic donor/allocation algorithms only. It does not yet establish sealed assignment publication, confirmation matching, unkeyed verification, or keyed reconstruction.

### EJ-20260729-0038 — open assignment-publication transaction boundary

- **Action:** Inspected the exact local lease lifecycle/publication API, schedule producer, secret-handle custody, assignment-ledger schema, prefix-receipt grammar, and completed-power fixture topology.
- **Decision:** Implement the authority-derived transaction rather than a free ledger writer. Confirmation remains nominal/fail-closed because the trusted provider registry and matching backend adapters do not exist.

### EJ-20260729-0039 — implement first storage-bound assignment transaction

- **Action:** Added `branch_assignment.py` with schedule/prefix/manifest ancestry loading, closed typed schedule reconstruction, verifier-feature loading, synthetic strata/matching, allocation, global capability uniqueness, CAS proof installation, key wiping, schema validation, and publication through the existing assignment-bound storage transaction.
- **Initial focused result:** RED, exit 1 in 0.95 seconds. Upgrading the manifest master-key commitment exposed a legacy fixture assignment ledger still pinned to `aaaa…`; study construction correctly rejected the split ancestry.
- **Correction:** Bind the setup ledger to the manifest commitment, then remove all ledger/later records before testing the actual transaction.

### EJ-20260729-0040 — initial transaction behavior passes; static typing blocks

- **Focused result:** GREEN, exit 0. One `t3_s09` test passed, 216 unrelated tests deselected, runtime 1.42 seconds.
- **Static result:** RED, exit 1. Ruff passed; mypy found one overly narrow inferred dictionary type in the candidate receipt row.
- **Correction:** Declare the heterogeneous closed receipt as `dict[str, object]`.

### EJ-20260729-0041 — hostile review blocks trusted derived features

- **Blocking attack:** The first implementation validated a feature blob but did not independently recompute it from its source verifier/report. An attacker could steer donor strata and distances using a schema-valid forged feature blob.
- **Correction:** Freeze closed synthetic normalizer/tokenizer descriptors and typed verifier/report parents; inside the live lease, reload parents and recompute component rows, objective-finding count, and normalized report token count before accepting the feature blob.
- **Additional closure:** Reload nested prefix snapshot, visible-context, provider-cost, verifier-snapshot, verifier-feature, and grade refs.

### EJ-20260729-0042 — completed-power ancestry rejects hand-authored schedule

- **Focused result:** RED, exit 1 in 1.13 seconds after adding independent completed-power consumption. The legacy fixture schedule named a dummy `sources/power-config.json`, not the actual final power report.
- **Correction:** In the focused fixture, delete the hand-authored schedule, publish a new schedule through `seal_prefix_schedule` from the actual completed final, then rebuild the prefix receipt against the exact new schedule digest.
- **Corrected result:** GREEN, exit 0. One focused test passed, 216 unrelated tests deselected, runtime 1.13 seconds.

### EJ-20260729-0043 — hostile review blocks unaccepted schedule replay

- **Blocking attack:** A digest-valid schedule file could reach assignment without proving the fixed prefix storage acceptance receipt and durable registry proof.
- **Correction:** Require the closed prefix receipt, recompute its intent digest and deterministic commit ID, verify manifest/root/lease/mount/science path/digest bindings, load the unique durable registry proof, and byte-compare it with the fixed receipt before assignment publication.
- **Adversarial case:** Forge only the fixed receipt's scientific digest. Assignment rejects before lease begin or secret consumption; restore the original receipt and the same lease/handle then complete successfully.

### EJ-20260729-0044 — corrected narrow transaction gates pass

- **Focused result:** GREEN, exit 0. One `t3_s09` transaction test passed with 216 unrelated tests deselected in 1.07 seconds.
- **Static result:** GREEN, exit 0. Ruff passed the transaction/core/types plus focused fixture; mypy found no issues in three source files.
- **Evidence covered:** Actual completed-power-derived schedule; exact prefix coverage/order; accepted prefix storage proof; source-recomputed no-trigger prefix view; key commitment/one-use consumption; two complete four-arm allocations; global capability uniqueness; ledger schema; durable assignment receipt; no ledger/later-record precondition.
- **Claim boundary:** Triggered synthetic CAS proofs are implemented but not promoted by this event because the current complete authority fixture has only two no-trigger tasks. A dedicated three-lineage triggered transaction/falsification fixture is the next gate. Confirmation remains unavailable and unclaimed.

### EJ-20260729-0045 — final captured all-no-trigger transaction gate

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Command:** Ran exactly one focused `t3_s09` behavioral selection and one combined Ruff+mypy static gate, each hard-capped at 60 seconds.
- **Result:** GREEN, exit 0. One test passed with 216 unrelated tests deselected in 1.16 seconds. Ruff passed; mypy found no issues in three source files.
- **Compact receipt:** stdout 176 bytes / 4 lines / SHA-256 `170cae229899b41a361fa1a728802e9fe8ffd24315238c6c81f0c155f0609e99`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0045/` (ignored, retained through 2026-11-27).

### EJ-20260729-0046 — publish storage-bound synthetic assignment slice

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Action:** Checked whitespace/status; staged exactly the new transaction module, focused authority fixture, and journal; checked staged scope; committed `feat(neurips): seal synthetic branch assignments`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `756aa3f5eb487cf8a329bdb61031a208e3143a08`. Three files, 1,360 insertions and seven deletions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Compact receipt:** stdout 778 bytes / 14 lines / SHA-256 `70c7b91dc4e3508204c23e66c384da94f05cb80ae38d801cc1263d355d7599f6`; stderr 134 bytes / 2 lines / SHA-256 `1ccb7e9abd843b1a26717ee98c1a37f4be80079aaa0adfcfe113f8d4ba0d949f`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0046/` (ignored, retained through 2026-11-27).

### EJ-20260729-0047 — construct genuine three-lineage triggered authority fixture

- **Action:** Reused the completed synthetic power chain while replacing only manifest-owned registry, roster, and provider-lane sources before resealing the manifest. Published a new three-task schedule through the real completed-power consumer; created closed verifier/report/feature parents; froze all three prefixes as triggered.
- **First result:** RED, exit 1 in 1.03 seconds. The provider-lane plan covered only the original two tasks, correctly exposing an execution-confounding authority gap.
- **Correction:** Extend the provider plan with the third task before manifest sealing.

### EJ-20260729-0048 — triggered CAS transaction passes

- **Result:** GREEN, exit 0. One focused `t3_s10` test passed, 217 unrelated tests deselected, runtime 1.47 seconds.
- **Evidence:** Three distinct lineages form one triggered stratum; publication emits one digest-derived CAS proof; proof mapping is a complete self-free permutation; all three matched receipts reference that exact proof and retain two complete eligible candidates.
- **Static correction:** Ruff found one unused fixture binding; an initially over-broad patch hit an older used binding, which was immediately restored while removing only the intended unused binding.
- **Corrected static result:** GREEN, exit 0. Ruff passed; mypy found no issues in the transaction module.

### EJ-20260729-0049 — hostile triggered-publication review

- **Findings:** Proof bytes are compact canonical and path-derived from their digest; existing CAS accepts only byte identity. Matching completes before proof installation for each stratum. A later failure may leave unreachable immutable proof blobs, which authority explicitly permits; without the final ledger they are not published science. The ledger references exactly one proof per triggered stratum and is installed only by the committed storage transaction.
- **Promotion:** Triggered synthetic publication is now defensible for the closed three-lineage fixture.
- **Remaining gates:** No unkeyed proof-graph verifier or keyed assignment reconstruction exists yet. Confirmation matching remains unavailable and unclaimed.

### EJ-20260729-0050 — final captured triggered-publication gate

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Command:** Ran exactly one focused `t3_s10` behavioral selection and one combined Ruff+mypy static gate, each hard-capped at 60 seconds.
- **Result:** GREEN, exit 0. One test passed with 217 unrelated tests deselected in 1.16 seconds. Ruff passed; mypy found no issues in one source file.
- **Compact receipt:** stdout 175 bytes / 4 lines / SHA-256 `d3b68b7107ef1aed83be09006c67979e81f4b0bdd081dc7feb0f847ec15e5804`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0050/` (ignored, retained through 2026-11-27).

### EJ-20260729-0051 — publish triggered synthetic proof promotion

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Action:** Checked whitespace/status; staged exactly the triggered authority fixture and journal; checked staged scope; committed `test(neurips): promote triggered assignment proofs`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `99b902721ad6f2a86d47cefb4555cac472bc0964`. Two files, 309 insertions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Compact receipt:** stdout 553 bytes / 11 lines / SHA-256 `4b7c9a7b941fcb6b2294cccfc861d44faedaaf260bab8a740b2421c60bf18ca3`; stderr 134 bytes / 2 lines / SHA-256 `eba9473c7ec915411880bf9463eb3262a18aa1668a3eeda81143181c76e1ac1e`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0051/` (ignored, retained through 2026-11-27).

### EJ-20260729-0052 — implement key-independent assignment-graph verifier

- **Action:** Added a public verifier that loads only ledger-reachable schedule/prefix/proof refs and never accepts or opens a secret handle/backend. It checks closed compact proof grammar, digest-derived CAS paths, ancestry, exact schedule-order coverage, cyclic offset/trial reconstruction, permutation/self/lineage/two-cycle feasibility, public allocation-to-arm reconstruction, global capability uniqueness, matched/N/A donor ancestry, candidate coverage, and proof reachability.
- **Adversarial case:** Mutate the selected offset in the installed proof bytes. The verifier rejects the digest/bytes mismatch.
- **Focused result:** GREEN, exit 0. One `t3_s10` test passed with 217 unrelated tests deselected in 1.30 seconds.

### EJ-20260729-0053 — static and hostile parser review

- **Initial static result:** RED. Ruff found one unused `hashlib` import; removed it.
- **Hostile findings:** Short donor arrays could raise an incidental `IndexError`; non-text/duplicate focal IDs were under-closed; duplicate donor IDs with altered metadata could satisfy set-only coverage; matched mode/algorithm/lineage/stratum bindings were incomplete.
- **Corrections:** Added explicit lengths/types/UTF-8 order/uniqueness, exact public trial failure reconstruction, candidate cardinality, lineage/mode/algorithm/view/stratum agreement, and synthetic zero-fallback cost grammar.
- **Corrected result:** GREEN, exit 0. One focused test passed in 0.99 seconds; Ruff passed; mypy found no issues in the new verifier.
- **Claim boundary:** This proves key-independent graph closure only. HMAC order, exact keyed draws, and capabilities still require fresh-handle reconstruction.

### EJ-20260729-0054 — final captured unkeyed graph-verification gate

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Command:** Ran exactly one focused triggered behavior selection and one combined Ruff+mypy static gate, each hard-capped at 60 seconds.
- **Result:** GREEN, exit 0. One test passed with 217 unrelated tests deselected in 1.08 seconds. Ruff passed; mypy found no issues in one source file.
- **Compact receipt:** stdout 175 bytes / 4 lines / SHA-256 `f48e7a9f2a6cf9feb0b679fca5e410c3766aed4b35b5e1c26d03909dc0338715`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0054/` (ignored, retained through 2026-11-27).

### EJ-20260729-0055 — publish unkeyed synthetic graph verifier

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Action:** Checked whitespace/status; staged exactly the new verifier, focused tamper case, and journal; checked staged scope; committed `feat(neurips): verify synthetic assignment graphs`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `4733e24b545e902994760b6bed9fa0794f52eb00`. Three files, 522 insertions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Compact receipt:** stdout 750 bytes / 14 lines / SHA-256 `99b5c0cd2673f0f232e6976be6af7f5d67e44e702948291c8a36c88e77017d9e`; stderr 134 bytes / 2 lines / SHA-256 `9ac9c4c8c9c9bd8348c5fe40d7a5b5ad4730bddd85edd22be38d90a45fcfbdb9`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0055/` (ignored, retained through 2026-11-27).

### EJ-20260729-0056 — implement fresh-handle keyed reconstruction

- **Action:** Added `require_assignment_reconstruction`. It first runs the key-independent graph verifier, reloads manifest/schedule/prefix/program ancestry, verifies accepted prefix publication, revalidates the closed assignment program plus manifest-pinned normalizer/tokenizer sources, reconstructs the source-derived prefix view, and only then consumes one exact assignment-purpose handle.
- **Keyed audit:** Reverify master commitment; derive only donor/allocation/orientation/capability subkeys; recompute every stratum HMAC order, offset trial, selected donor mapping, candidate order/cost, allocation draw, orientation draw, capability, assignment, donor receipt, and proof byte sequence; byte-compare the complete ledger arrays; wipe master/subkeys on every exit.
- **Adversarial case:** Replace one capability with another valid unique lowercase digest and recompute the ledger ref. The public graph verifier accepts structural feasibility, while keyed reconstruction rejects the exact capability mismatch.
- **Focused result:** GREEN, exit 0. One `t3_s10` test passed with 217 unrelated tests deselected in 1.40 seconds.

### EJ-20260729-0057 — close reconstruction authority and confirmation boundary

- **Hostile finding:** Initial reconstruction reused source feature recomputation but did not independently revalidate the manifest-pinned normalizer/tokenizer descriptors and closed program grammar.
- **Correction:** Validate the complete assignment program, normalizer/source digest, tokenizer digest, normalizer source membership in manifest revisions, and exact synthetic implementations before handle consumption.
- **Confirmation wrapper:** Added a thin fail-closed entry point. It rejects synthetic ledgers without consuming the fresh handle and cannot accept confirmation until the nominal trusted matching-backend reconstruction adapter exists.
- **Result:** GREEN, exit 0. One focused test passed with 217 unrelated tests deselected in 1.65 seconds; Ruff passed; mypy found no issues in the reconstruction source.
- **Claim boundary:** Synthetic keyed reconstruction is promoted. Confirmation reconstruction and `verify_result_bundle` storage composition remain unavailable/unclaimed.

### EJ-20260729-0058 — final captured keyed-reconstruction gate

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Command:** Ran exactly one focused triggered behavior selection and one combined Ruff+mypy static gate, each hard-capped at 60 seconds.
- **Result:** GREEN, exit 0. One test passed with 217 unrelated tests deselected in 1.48 seconds. Ruff passed; mypy found no issues in one source file.
- **Compact receipt:** stdout 175 bytes / 4 lines / SHA-256 `c964986883eed5ef127733c02050c586fdbf94ed67ef713f1d7dd991dc50ae44`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0058/` (ignored, retained through 2026-11-27).

### EJ-20260729-0059 — publish keyed synthetic reconstruction

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Action:** Checked whitespace/status; staged exactly reconstruction source, focused keyed forgery case, and journal; checked staged scope; committed `feat(neurips): reconstruct synthetic assignments`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `6ffecf2ffba83c8249939db465cf3dde13b83058`. Three files, 512 insertions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Compact receipt:** stdout 673 bytes / 13 lines / SHA-256 `14ec2a15bd167ee1b525898a57e2d1a2d88d7747d5190fd0b432a22b93d16272`; stderr 134 bytes / 2 lines / SHA-256 `50d42d2f68fc298c1c4178fcb8b8cecbbd5e58f52df687b7ab9052523c5993cf`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0059/` (ignored, retained through 2026-11-27).

### EJ-20260729-0060 — close typed assignment-ledger API

- **Action:** Added frozen `DonorCandidateReceipt`, matched and N/A donor receipts, their closed union, and `AssignmentLedger`. Enforced mode/algorithm coherence, distinct focal/donor identity and lineage, unique complete candidates, chosen-cost agreement, shared task order, typed refs, exact digests, and unique proof refs.
- **API:** Keyed reconstruction now returns `AssignmentLedger`, not an untyped document dictionary. Exported assignment sealing, public graph verification, keyed/confirmation reconstruction, typed ledger, and bundle verification from the package surface.
- **Focused result:** GREEN, exit 0. One focused triggered test passed with 217 unrelated tests deselected in 1.30 seconds.
- **Static correction:** mypy initially inferred the donor list as N/A-only from its first append; explicitly typed it as the closed `DonorMatchReceipt` union. Corrected Ruff/mypy gate passed.

### EJ-20260729-0061 — compose assignment storage and result-bundle verification

- **Action:** Added exact assignment fixed-receipt verification: compact intent digest, deterministic commit ID, exact manifest/schedule/root/science binding, begin/end lease tuple, generation/expiry, authority, mount, mode, freshness/lifecycle booleans, commit flags, and byte-equal durable registry proof.
- **Adversarial case:** Forge only the fixed assignment receipt's scientific digest. Verification rejects; restoring the original receipt succeeds.
- **Bundle orchestration:** `verify_result_bundle` performs keyed reconstruction (which already checks public graph and prefix acceptance), verifies assignment acceptance, then calls immutable artifact-root verification with the exact required-kind authority.
- **Claim boundary:** Assignment receipt verification is exercised. Full bundle success awaits a complete post-analysis artifact-root fixture; compilation alone is not promoted as end-to-end bundle evidence.
- **Result:** GREEN, exit 0. One focused test passed in 1.37 seconds; Ruff passed; mypy found no issues in three source files.

### EJ-20260729-0062 — final captured typed/composition gate

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Command:** Ran exactly one focused triggered behavior selection and one combined Ruff+mypy static gate, each hard-capped at 60 seconds.
- **Result:** GREEN, exit 0. One test passed with 217 unrelated tests deselected in 1.20 seconds. Ruff passed; mypy found no issues in three source files.
- **Compact receipt:** stdout 176 bytes / 4 lines / SHA-256 `4069e7f1e9b8a5502d6fb83b95caaa7777fd2bc6dc09423bd277d52321761d5b`; stderr 0 bytes / 0 lines / SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0062/` (ignored, retained through 2026-11-27).

### EJ-20260729-0063 — publish typed assignment result verification

- **Time:** raw metadata records exact local/UTC start and end timestamps.
- **Action:** Checked whitespace/status; staged exactly types, reconstruction/composition, package exports, focused forgery cases, and journal; checked staged scope; committed `feat(neurips): close assignment result verification`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `b81ed98758923f26f85557a5c4c3d1ee9e672e89`. Five files, 611 insertions and 12 deletions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Compact receipt:** stdout 932 bytes / 17 lines / SHA-256 `2e8e41bb8e95358fe33e5dc507b5a2c9ff2fc806c1325fc97134699d1284b9bb`; stderr 134 bytes / 2 lines / SHA-256 `b491c6fb93585dc87e231ad51077e321a2fb167eb85f95eb490fa862ff876071`; raw local receipt `build/research/neurips-2026-workshop/execution-journal/EJ-20260729-0063/` (ignored, retained through 2026-11-27).

### EJ-20260729-0064 — route Task 4 to the causal placebo mechanism

- **Authority:** Re-read immutable Task 4 requirements and signatures from the accepted resampling-null plan before implementation. Scope this slice to pure REAL/SHAM pair construction; candidate/sealed-prefix chronology remains the next slice.
- **Research decision:** Treat token/field/severity parity, type-preserving identifier aliases, donor-leakage closure, true-focal collision rejection, bounded truncation receipts, and exact neutral padding as causal-identification controls rather than production-software embellishment.
- **Known authority seam:** The immutable builder signature provides no distinct normalized-artifact store operation or paths. This slice therefore binds `normalized_real_ref` and `normalized_sham_ref` to the persisted packet refs. That is explicit provisional plumbing, not evidence that a separate normalization stage exists; closure repair is required before claim promotion.
- **Testing budget:** Per user direction, software verification remains an insignificant tripwire: one focused behavioral selection and one static source check, each hard-capped at 60 seconds. No broad suite or coverage work is authorized.

### EJ-20260729-0065 — implement and adversarially repair token-exact packet pairs

- **Implementation:** Added frozen typed finding/atom/policy/receipt records and a pure `build_packet_pair` path. It pairs bounded REAL and donor findings, retains focal finding IDs and severities, applies type-preserving donor-to-focal identifier rewrites, rejects unmapped or literal donor leakage, records deterministic trailing-atom truncation, rejects SHAM signatures colliding with known true-focal signatures, searches authorized neutral padding to exact tokenizer parity, persists private guidance, and returns ancestry/claim receipts.
- **Self-attack finding:** The first safe-padding regex used an over-escaped `\\s` inside its character class, authorizing the literal character `s` rather than whitespace. Also, equal-token packets could bypass validation of an unused but malicious pad-unit authority.
- **Repair:** Corrected the regex to actual whitespace, centralized exact-type/nonempty/non-executable pad-unit validation, and invoked it before comparing packet lengths. Added one adversarial assertion that instruction-bearing padding is rejected even when the inputs would otherwise be equal length.
- **Source hashes after repair:** `packets.py` SHA-256 `23a7c192128f2539112187f5a41dec2a65fe0da1a919a150b955fcb13331f29a`; focused fixture SHA-256 `76d9b87cc5bbd3be4e18ff4c7ea22a2950d55b703184e098e6e2b15738e26921`.

### EJ-20260729-0066 — minimal packet tripwire and static diagnostics

- **Behavioral command:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_packets.py -q -k t4_s01`.
- **Behavioral result:** GREEN, exit 0. Exactly one test passed in 0.20 seconds. It checks exact token parity, field/severity binding, type-preserving rewrite, donor-identity absence, focal alias presence, truncation monotonicity, kind-confusion rejection, malicious-padding rejection, and true-focal collision rejection.
- **First static command:** Ruff plus mypy over source and the compact fixture, each hard-capped at 60 seconds.
- **First static result:** MIXED. Ruff passed. Mypy produced 28 fixture-only `**dict[str, object]` argument diagnostics because the intentionally compact shared-call dictionary erases keyword types. No implementation diagnostic was reported. Per the explicit insignificant-test policy, the fixture was not expanded into typed test scaffolding.
- **Corrected source-only static command:** Ruff over the three touched files plus mypy over `packets.py` and package exports, each hard-capped at 60 seconds.
- **Corrected static result:** GREEN, exit 0. Ruff passed; mypy found no issues in two source files. `git diff --check` passed.

### EJ-20260729-0067 — expose the provisional packet-pair API

- **Action:** Exported the builder, findings, identifier atoms/kinds, policy, receipt, and failure type from `pneuma_lab.resampling_null`.
- **Package-export hash:** `src/pneuma_lab/resampling_null/__init__.py` SHA-256 `3766d1ecaf5bfbb806ba52e3131ad4e23efb33feccf8623063bcab27eb942923`.
- **Claim boundary:** This is only a synthetic pure-construction slice. No sealed-prefix candidate audit, no donor eligibility index, no confirmation adapter, no real experiment, and no causal result exists or is claimed.

### EJ-20260729-0068 — publish token-exact packet-pair slice

- **Action:** Staged exactly the packet implementation, package exports, one focused tripwire, and journal; checked staged whitespace/scope; committed `feat(neurips): construct token-exact sham packets`; pushed to the public research branch; compared exact local and remote refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `4dfd0e0c6cb0a3ac408f52f6b34a716a71ad4655`. Four files, 748 insertions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Next research action:** Implement deterministic donor-candidate enumeration and sealed-prefix audit chronology. Do not expand software tests absent a concrete failure mode.

### EJ-20260729-0069 — open candidate/seal chronology slice

- **Authority and scope:** Continued immutable Task 4 using plan SHA-256 `a2ca4fc419f353e9a38350025e1e2996fd21d66eb16b2d8d011af2c2e1d491b1` and design SHA-256 `d2a3c5a20059574ab8dad92a45b29f06aeeaf2bd9dafbc8716c5449848a687db`. Work stayed on `codex/neurips-2026-empirical`; the checkout is a normal dedicated-branch workspace, not a linked Git worktree. No subagent, model subprocess, spend, cloud action, training, or confirmation ceremony occurred.
- **User-directed verification budget:** Software checks remain tiny tripwires, never research deliverables: one focused command selecting only the packet constructor and packet chronology behavior, plus one source-static command, all hard-capped at 60 seconds.
- **Intent:** Publish a non-authoritative candidate covering exact schedule order, then permit a sealed execution-authority index only where the audit can be reconstructed from parent bytes.

### EJ-20260729-0070 — implement candidate publication and no-trigger sealing

- **Implementation:** Added the typed `NoInterventionPacketMarker`; candidate publication loads and byte-verifies the assignment ledger, rejects empty/duplicate task coverage, binds every pair to assignment/prefix/tokenizer/template/policy/pad parents, rejects open claimed parity/leakage gates, and writes one immutable schema-valid candidate record. The audit loads exact candidate/assignment/schedule/prefix records, checks their byte digests and chronology, requires exact selected-schedule order and expected-roster equality, verifies manifest-frozen config bytes, and accepts only exact typed markers for no-trigger assignments before writing the sealed record.
- **Mechanical correction:** The first patch accidentally inserted candidate helpers between REAL and SHAM persistence. Inspection caught it before execution; the SHAM write and receipt return were restored to the builder boundary and the helpers moved after the function.
- **Hardening:** Added exact closed ArtifactRef decoding, exact integer-tuple tokenizer outputs, distinct focal/donor IDs, lowercase prefix digest validation, distinct REAL/SHAM requested paths, and rejection when the artifact store aliases or renames arm artifacts.

### EJ-20260729-0071 — hostile seal audit blocks self-attested science

- **Rejection attack:** The immutable seal signature receives tokenizer/template/policy/pad ArtifactRefs but no canonical normalized-finding values, no canonical identifier-map encoding, and no executable tokenizer reconstruction authority. Its first implementation could therefore re-read pair receipts and packet bytes but could not independently reproduce every `true` audit gate. A hostile reviewer would correctly call that self-attestation.
- **Correction:** Removed the pseudo-independent triggered-pair audit. Candidate publication may retain triggered pair proposals, but `audit_and_seal_packet_index` now rejects every triggered packet with an explicit pending-recomputation-authority error. Only an all-no-trigger roster—where packet parity/collision gates are vacuous and marker/chronology/config-byte closure is directly provable—can be sealed.
- **Required authority repair:** A future DL-135 must define canonical normalized REAL/SHAM artifacts, canonical identifier-map/policy/pad/template contracts, exact builder-to-ref byte binding, and an independently reconstructable tokenizer registry before triggered sealing or claim promotion.
- **Claim boundary:** No triggered packet index, confirmation packet index, causal result, or independent semantic packet audit is claimed.

### EJ-20260729-0072 — insignificant focused verification gate

- **Behavior command:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_packets.py tests/resampling_null/test_artifacts.py -q -k 't4_s01 or t3_s09'`.
- **Behavior result:** GREEN, exit 0. Exactly two relevant tripwires passed with 217 unrelated tests deselected in 1.09 seconds: token-exact pair construction and no-trigger candidate/seal chronology with a roster-forgery rejection.
- **Static command:** Ruff over the two touched source files and two touched fixtures, then mypy over the two source files; each process hard-capped at 60 seconds.
- **Static result:** GREEN, exit 0. Ruff passed; mypy found no issues. `git diff --check` passed.
- **Final content hashes:** `packets.py` `ae625ec0692286ef12a16ce54e1b8f5d30fc3c49e53d555b4c67ac3df537fbda`; package exports `627be476c9d23118643f890bf87db79bc610137c1a7eb4aac684ab55d101d12a`; focused chronology fixture `db06464e0d0db1cd8a29d0f1380cd0e35af95987a7a44e71effe157bc0ad5676`.

### EJ-20260729-0073 — publish fail-closed packet chronology

- **Action:** Staged exactly packet chronology source, package exports, the reused focused authority fixture, and journal; checked staged whitespace/scope; committed `feat(neurips): seal no-trigger packet indexes`; pushed publicly; compared exact local and remote refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `69f29854bb7a60de87b4d17d5d459f0bc4ee5931`. Four files, 491 insertions and 11 deletions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Next gate:** DL-135 authority repair for independent triggered-packet recomputation; current triggered sealing remains deliberately unavailable.

### EJ-20260729-0074 — promote hostile packet finding into DL-135

- **Authority action:** Amended the Task-4 plan and design, then appended DL-135 to the authoritative decision log. The amendment supersedes naked caller values and receipt rereading as triggered-packet sealing authority.
- **Normative repair:** Require manifest-pinned normalizers; canonical focal/donor/SHAM typed artifacts; canonical complete identifier-map, policy, pad, template, and tokenizer contracts; internal tokenizer reconstruction; exhaustive derived focal collision signatures; trusted decrypt-for-audit; and byte-equal independent reconstruction of packets and every receipt. Add `normalized_donor_ref`; normalized refs may never alias packet text.
- **Availability:** Synthetic adapters must be closed named fixtures. Confirmation remains fail-closed until separately reviewed SWE/tau normalizers, tokenizer loaders, and decrypt-for-audit adapters are pinned before the manifest. All-no-trigger sealing remains valid because packet gates are vacuous.
- **Testing standard:** DL-135 incorporates the user’s current rule: one narrow behavior command and one source-static command per slice, each at most 60 seconds; broad suites and coverage work are forbidden without a concrete shared-surface failure mode.

### EJ-20260729-0075 — verify refreshed authority hashes

- **Result:** `git diff --check` passed. The decision row exactly records refreshed plan SHA-256 `50070ddd47a9ac7957d1a0a5bd050bbc5cf79471110abcef4f545540a0272673` and design SHA-256 `f9d3333bc3a4378be13a1235fc224052856ffbe693763d42a822b78dbf13928e`; recomputation matched both. Decision-log SHA-256 after DL-135 is `338ec7e8175e65b67db212c7aed08196eb60f0df82394cf6eecf765ca19c6237`.
- **Scope:** Docs/authority only. No empirical claim, result, spend, training, cloud action, confirmation adapter, or triggered seal was created.

### EJ-20260729-0076 — publish DL-135 authority repair

- **Action:** Staged exactly decision log, journal, Task-4 plan, and design; checked staged whitespace/scope; committed `docs(neurips): require reconstructable packet audits`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `9d2174ae387bf5bc55e96b05b4c0d4cd8e4442e4`. Four files, 100 insertions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Next gate:** Implement canonical synthetic packet-source artifacts and ref-byte binding under the refreshed DL-135 authority before reopening triggered sealing.

### EJ-20260729-0077 — implement first reconstructable packet parent

- **Action:** Added the closed `packet_normalized_findings_v1` synthetic derivation. It loads exact verifier-feature bytes, requires the closed assignment feature grammar, follows and byte-verifies both source-verifier and source-report refs, validates task/benchmark/components/finding count/report token count, parses only closed typed literal/identifier atom arms, rejects duplicate finding IDs, emits deterministic ordered canonical JSON, and installs it as an immutable referenced blob inside `run_root`.
- **Schema:** Added required `normalized_donor_ref` to every packet-pair receipt. Focal, donor, and derived SHAM normalization are now three distinct conceptual parents under DL-135; the old two-ref model cannot represent rewrite reconstruction.
- **Fixture:** Upgraded the existing three-lineage triggered authority fixture with one typed objective finding and derived the normalized artifact twice to distinct paths. Canonical payload bytes and SHA-256 are identical.
- **Provisional boundary:** The pre-DL-135 `build_packet_pair` still emits provisional normalized refs and triggered sealing still rejects them. This slice establishes the source artifact primitive; it does not reopen triggered authority.

### EJ-20260729-0078 — hostile normalized-parent repair

- **Finding:** The initial normalizer followed the source-verifier ref but did not load the feature wrapper's source-report ref, and runtime task ID exact typing relied on annotations. A forged or missing report parent could therefore escape this local closure even though assignment verification would normally catch it.
- **Repair:** Require a nonempty exact-string task ID; load and byte-verify the report ref; require its closed synthetic report grammar, exact task binding, and exact whitespace-token count agreement with the feature wrapper.
- **Result boundary:** This proves deterministic synthetic normalization from the named verifier chain only. It does not prove SWE/tau normalization, identifier-map completeness, SHAM falsity, tokenizer reconstruction, encrypted packet equality, or any empirical effect.

### EJ-20260729-0079 — minimal normalized-source gate

- **Behavior command:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_artifacts.py -q -k t3_s10`.
- **Behavior result:** GREEN, exit 0. Exactly one triggered authority fixture passed with 217 unrelated tests deselected in 1.79 seconds.
- **Static command:** Ruff over the touched source/export/fixture files and mypy over the two source files, each hard-capped at 60 seconds.
- **Static result:** GREEN, exit 0. Ruff passed; mypy found no issues. `git diff --check` passed.
- **Content hashes:** packet-index schema `b3e878fb98c6b76d396aa71900ba950049abe71abe69d63d707191a7ce14f6d2`; `packets.py` `98734a7bc5580add82d63f8344a3fd4ac175a6834d13998b176c647f75d825f2`; exports `3e0451ecb1f81dd4f5f677207562e006fb4e42b55a3099adee3b2c9fd2bd0764`; fixture `13826660edf661080e12dcd468d925c372a43441636ba7656c5d6d47b0eade5d`.

### EJ-20260729-0080 — publish canonical normalized findings

- **Action:** Staged exactly packet schema, normalizer source/export, reused triggered fixture, and journal; checked staged whitespace/scope; committed `feat(neurips): canonicalize packet findings`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `a092ecc5a7b4e8db4f9f2e9acb0848261be6af87`. Five files, 293 insertions and three deletions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Next gate:** Derive a complete canonical type-preserving identifier map and distinct normalized SHAM artifact from canonical focal/donor parents.

### EJ-20260729-0081 — derive canonical map and normalized SHAM

- **Implementation:** Added frozen `PacketRewriteArtifacts` and `derive_packet_rewrite_artifacts`. It reloads compact canonical focal/donor normalized parents, requires distinct task IDs and nonempty findings, derives the complete donor identifier set, rejects literal donor leakage, requires exact map-key coverage, unique destinations, same-kind replacements, and destinations already present in the focal artifact, then serializes a UTF-8 byte-ordered canonical `packet_identifier_map_v1`.
- **SHAM derivation:** Applies the frozen map to donor atoms, copies focal finding IDs/severities and donor component/code fields in deterministic pair order, rejects donor identity across every semantic string and atom field, and writes a distinct canonical `packet_normalized_sham_v1` bound to focal/donor normalized refs and the map ref.
- **Fixture evidence:** The existing triggered fixture creates one independent focal verifier chain, normalizes it, maps donor `src/third.py` to focal `src/focal.py`, and verifies the normalized SHAM contains only the focal alias. No new test subsystem was created.

### EJ-20260729-0082 — hostile rewrite durability and leakage repair

- **Findings:** The first version scanned SHAM atoms but could miss donor identity embedded in component/code/severity fields. It also wrote the identifier map before the SHAM artifact, so a crash between writes left an identical retry blocked by `FileExistsError`.
- **Repairs:** Scan every rendered semantic field against donor task/identifier strings; forbid focal destinations containing any donor identity substring; freeze the mapping against unstable iteration; and make canonical audit-blob installation idempotent only when existing bytes are exactly equal, while differing bytes remain fail-closed.
- **Boundary:** The map and SHAM are now deterministic candidate parents. Independent audit must still regenerate them from raw verifier/config bytes before triggered sealing.

### EJ-20260729-0083 — minimal rewrite gate

- **Behavior command:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_artifacts.py -q -k t3_s10`.
- **Behavior result:** GREEN, exit 0. Exactly one triggered authority fixture passed with 217 unrelated tests deselected in 1.53 seconds.
- **Static command/result:** Ruff over touched source/export/fixture and mypy over the two source files, each capped at 60 seconds; GREEN, exit 0. `git diff --check` passed.
- **Content hashes:** `packets.py` `4f76ec83a5dba4174e0bd40899acd30c802e6223f05d054da5e7e05bf2d1fda5`; exports `b773153ba2e5830bf7dd06e186ccd7acd6217c4e68295c9ccfb6d4508cc7b4ca`; fixture `7c1fa4aa37e54e9fbaafccc4dd548675d56dd1433b73228c988646476aaf7d82`.

### EJ-20260729-0084 — publish canonical rewrite authority

- **Action:** Staged exactly rewrite source/export, the reused triggered fixture, and journal; checked staged whitespace/scope; committed `feat(neurips): derive canonical sham findings`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `cc7ff3c4d6da1733e2af18494006a84a78e75367`. Four files, 359 insertions and two deletions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Next gate:** Load closed manifest-pinned policy, pad, template, and tokenizer bytes into one internal synthetic packet authority; caller objects remain non-authoritative.

### EJ-20260729-0085 — load closed synthetic packet authority

- **Implementation:** Added frozen `PacketAuthority` and `load_synthetic_packet_authority`. It byte-verifies and parses only the manifest-pinned closed synthetic tokenizer, canonical packet template, exact policy, and ordered neutral pad-unit contracts. It rejects unknown keys/versions/algorithms, invalid policy types, another normalizer, unsafe/duplicate/unsorted pads, or any noncanonical byte representation.
- **Tokenizer:** The internal `unicode_whitespace_v1` fixture tokenizer derives deterministic full SHA-256 integer token IDs from whitespace-separated tokens. Full 256-bit IDs replace an initial 64-bit truncation so the fixture does not create an avoidable collision attack.
- **Caller boundary:** The returned tokenizer/policy/pads are reconstructed from ArtifactRef bytes. An injected `Tokenizer` or naked config object remains useful only for provisional pure construction and has no audit authority.

### EJ-20260729-0086 — canonical-byte rejection and fixture repair

- **First result:** RED, exit 1. The focused fixture reached the new authority loader, which correctly rejected `sources/tokenizer.json`: the fixture helper emitted compact sorted JSON without the project canonical terminal newline, so bytes did not equal `canonical_json_bytes(..., indent=None)`.
- **Repair:** Materialize exactly the four packet-authority fixture sources—tokenizer, template, policy, pads—from `canonical_json_bytes` before study sealing. This changes fixture authority bytes and their manifest-bound refs; it does not weaken the canonical check.
- **Corrected result:** GREEN, exit 0. One `t3_s10` fixture passed with 217 unrelated tests deselected in 1.41 seconds. Ruff passed; mypy found no issues in two source files.

### EJ-20260729-0087 — packet-authority slice hashes

- **Checks:** `git diff --check` passed. No broad suite, coverage, subprocess, spend, cloud action, or training ran.
- **Content hashes:** `packets.py` `c4e448bdbe6055e635e696be8d27bdb46d4b260b48d13ab682db5e8d54a033e5`; exports `f67f15a2e1814b872a374ad744c5f46e874d5a7f067b68c2ac3a0e196ae66596`; fixture `d1f4270aa2f0618221fafb414292cb5b9d8b4a4010d61811318a8d61b24bd36c`.
- **Next gate:** Refactor packet construction to consume canonical normalized focal/donor/SHAM/map plus reconstructed packet authority, eliminating provisional normalized-ref aliases and caller collision authority.

### EJ-20260729-0088 — publish canonical packet authority

- **Action:** Staged exactly packet-authority source/export, the reused triggered fixture, and journal; checked staged whitespace/scope; committed `feat(neurips): load canonical packet authority`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `92f588e82c86090d3e139c0fc290012329451787`. Four files, 213 insertions and eight deletions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Next gate:** Rebuild packet construction from canonical parents, then make the independent audit reproduce and byte-compare the entire triggered pair before allowing a sealed index.

### EJ-20260729-0089 — replace provisional packet-construction authority

- **API change:** Replaced the public naked-value builder with `build_packet_pair` that accepts only `run_root`, canonical normalized focal/donor/SHAM refs, the canonical identifier-map ref, manifest config refs, sealed focal/donor verifier refs, assignment/prefix ancestry, artifact destinations, and the synthetic artifact store. The old value constructor is now private implementation machinery.
- **Derived authority:** The public builder reloads canonical config, independently re-derives focal/donor normalized documents from raw verifier chains and byte-compares them, parses the closed canonical map, reruns map/SHAM derivation idempotently, verifies normalized SHAM ancestry/bytes, derives exhaustive focal collision signatures internally, and only then renders packets.
- **Receipt correction:** Padding-search `pad_unit_set_sha256` now equals the manifest parent ArtifactRef digest rather than a second ad hoc digest of the unit list. Normalized focal/donor/SHAM refs are the distinct canonical artifacts, never packet or verifier aliases.
- **Synthetic storage:** Added `SyntheticPacketArtifactStore`, an ignored-run-root plaintext-only fixture store with path containment, no differing overwrite, idempotent equal-byte recovery, exact refs, and no confirmation claim.

### EJ-20260729-0090 — independent triggered reconstruction and sealing

- **Audit transaction:** Added a read-only verifying packet store. The sealer derives exact schedule/prefix/assignment donor/verifier ancestry, invokes canonical construction from candidate parent refs, requires both reconstructed plaintext packets to byte-equal their referenced synthetic artifacts, and canonical-JSON-compares the entire reconstructed receipt with the candidate entry. Only then can it emit the sealed index.
- **Assignment acceptance:** Exposed `require_assignment_publication` as a public wrapper around the existing fixed-receipt/registry-proof verifier. Candidate publication and sealing now both require durable assignment acceptance plus the public synthetic assignment-graph verifier; an orphan ledger cannot authorize packets.
- **Fixture:** Extended the existing three-lineage triggered transaction with one typed objective finding per task, three canonical normalized parents, assignment-derived donor maps, three canonical SHAM parents, six packet artifacts, one candidate, a deliberate one-byte REAL corruption that must fail, restoration, and successful sealed-index publication.
- **Test reduction:** Replaced the obsolete 175-line packet unit fixture with one 46-line primitive tripwire. Full causal reconstruction lives in the single authority transaction; test scaffolding shrank rather than becoming a parallel product.

### EJ-20260729-0091 — triggered-seal RED corrections

- **First RED:** Whole-record leakage correctly rejected an obsolete standalone donor whose code field contained `task-third`. Removed the redundant standalone probe and retained the stricter leakage gate; scheduled fixture codes are donor-neutral `alpha`/`bravo`/`charlie`.
- **Second RED:** Packet plaintext and semantic reconstruction succeeded, but Python equality compared dataclass tuples with candidate JSON arrays. Corrected the terminal receipt comparison to compact canonical JSON bytes, the actual authority representation; no field or gate was relaxed.
- **Corruption falsification:** Appending one byte to the first REAL artifact caused sealing to reject before output. Restoring exact bytes allowed reconstruction and sealing.

### EJ-20260729-0092 — hostile triggered-seal review

- **Closed attacks:** Caller findings/tokenizer/map/collision authority; normalized-ref aliases; incomplete/type-changing maps; donor identity in atoms or semantic fields; unsafe pads; noncanonical configs; packet path alias/escape/overwrite; candidate roster/order drift; focal/donor verifier drift; assignment orphan/graph forgery; packet-byte mutation; receipt mutation; and candidate-as-execution-authority.
- **Implementation-independence boundary:** Construction and audit are separate transactions with disjoint write/read-only stores and no trust in candidate booleans, but share reviewed deterministic transformation code. This proves parent-to-byte reproducibility, not N-version implementation independence. Independent manipulation experiments and blind audits remain later scientific gates.
- **Production boundary:** The complete synthetic plaintext fixture path is implemented. No production decrypt-for-audit capability, SWE/tau normalizer, confirmation tokenizer loader, confirmation packet seal, manipulation success, or causal result exists or is claimed.

### EJ-20260729-0093 — minimal complete synthetic packet gate

- **Behavior command:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_artifacts.py -q -k t3_s10`.
- **Final behavior result:** GREEN, exit 0. Exactly one three-lineage triggered authority transaction passed with 217 unrelated tests deselected in 1.81 seconds.
- **Static command:** Ruff over three touched source files and two touched fixtures; mypy over the same three source files; every process capped at 60 seconds.
- **Static result:** GREEN, exit 0. Ruff passed; mypy found no issues. `git diff --check` passed.
- **Content hashes:** `packets.py` `8232b9b1e3e509128eaf40a9f7da7ab7b6b20eec598c789af6e0391693655b08`; assignment verification `7088852553d503f075084d9a0c8ae41f4ebba1e7dbd995f9c05312402c349395`; exports `1d1332148506f5bd0011d8618556159606802cda315f43f3a5e0f9ca8fa8cb31`; authority fixture `92367a33030d9fadd7db1438b25da749817b83a1d089babfc87db8afd4ec4c52`; primitive tripwire `a769d0aad886a048820c5aad3f622fe68ae97a0a6190af2fc222745321fe293a`.

### EJ-20260729-0094 — publish reconstructable triggered packet seals

- **Action:** Staged exactly packet construction/audit source, public assignment-acceptance wrapper, exports, reduced primitive tripwire, extended authority fixture, and journal; checked staged whitespace/scope; committed `feat(neurips): reconstruct triggered packet seals`; pushed publicly; compared exact refs.
- **Result:** GREEN, exit 0. Local and public remote are exactly `ebf24d6f1c852928debc67fb1669b5b5daf4a844`. Six files, 759 insertions and 309 deletions. The unrelated untracked `raw_root_placeholder` remains untouched.
- **Promotion:** Complete synthetic triggered packet parent-to-byte reconstruction and sealed-index publication are now implemented and evidenced. Confirmation/production manipulation validity remains unavailable and unclaimed.

### EJ-20260729-0095 — freeze controller boundary primitives

- **Implementation:** Added frozen slotted context, tool-call, cap, grade, call-seed, subject-turn, tool-boundary, and opaque-slot records; the closed failure vocabulary; and the role/index-separated `call-seed-v1` derivation. Tool arguments must byte-equal compact project-canonical JSON object bytes, including the terminal LF, with duplicate keys and nonfinite constants rejected. Exported only these primitive contracts and the seed derivation.
- **Scope:** This slice has no prefix/branch runner, work order, synthetic environment, attempt/block seal, schema, provider call, spend, or scientific decision.

### EJ-20260729-0096 — T5-S01 RED/GREEN evidence

- **RED command/result:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py -q`; RED, exit 1. The focused tripwire showed `CallSeedReceipt` accepted `call_index == 2**64`, violating its uint64 boundary.
- **Repair and GREEN:** Reused the exact uint64 validator for `call_index`. The same focused command was GREEN, exit 0: one test passed in 0.21 seconds.
- **Static evidence:** `timeout 60s .venv/bin/ruff check` over the three touched source files and focused test was GREEN, exit 0. `timeout 60s .venv/bin/mypy` over the three touched source files was GREEN, exit 0 with no issues. `git diff --check` passed.

### EJ-20260729-0097 — hostile primitive-boundary review and non-claims

- **Boundary review:** Exact-int guards reject booleans; uint64 guards reject negative and overflowing seeds/indexes; tuple fields reject lists and wrong record members; frozen slots prevent post-construction mutation; incomplete tool boundaries cannot mutate, become verifier-eligible, or claim `NONE`; opaque capabilities require lowercase SHA-256; grade failures cannot be both infrastructural and successful. Canonical argument parsing rejects whitespace drift, missing terminal LF, duplicate keys, nonfinite constants, and non-object JSON before any future execution layer can consume them.
- **Residual boundary:** These records constrain values but do not establish provider determinism, wall-clock enforcement, tool sandboxing, mutation detection, grading validity, identity blindness, successful resampling, or causal evidence. No experiment ran and no empirical or consciousness claim is promoted.

### EJ-20260729-0098 — hostile review finds subtype boundary gaps

- **Finding:** `subject_role` membership could accept equality-overloaded objects or foreign string-enum values before downstream framing rejected them; receipt construction accepted them outright. Tuple and member checks used `isinstance`, admitting tuple subclasses and record subclasses with extra state. Controller uint64 guards and two receipt branches also classified wrong scalar types as value errors.
- **RED:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py -q` failed exactly three new regression tests while the original primitive test passed. Failures exposed the late role rejection, accepted tuple subclass, and wrong `ValueError` for boolean `slot_seed`.

### EJ-20260729-0099 — tighten exact primitive boundaries

- **Repair:** Require exact `str` before closed role membership in both seed derivation and receipt construction; require exact tuple containers and exact context/tool-call record members; split scalar type failures from range/value failures; and exercise the primitive API only through public package exports.
- **GREEN/static:** The same focused behavior command passed four tests in 0.23 seconds. The same capped Ruff slice over controller, types, exports, and focused test passed; the capped mypy slice over three source files reported no issues. `git diff --check` passed.
- **Boundary/non-claims:** Subclass/equality smuggling at these primitive boundaries is closed. No runner, provider call, tool execution, seal, schema, spend, experiment, causal result, or consciousness claim was added or promoted.

### EJ-20260729-0100 — independent T5-S01 review and final local gate

- **Spec review:** An independent read-only reviewer compared the committed implementation with the bounded T5-S01 contract and found it compliant. The reviewer independently reran the focused behavior command: four tests passed, with no unrelated test selection.
- **Quality review:** A separate hostile reviewer rejected the first commit because equality-overloaded role values and tuple/record subclasses could cross nominally closed forensic boundaries. After the TDD repair in EJ-0098/0099, the same reviewer re-inspected the exact follow-up diff and approved it with no remaining critical, important, or minor finding.
- **Fresh behavior gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py -q`; GREEN, exit 0, four tests passed in 0.21 seconds.
- **Fresh static gate:** Ruff over controller, types, exports, and the focused test passed; mypy over the three source files reported no issues; every process was capped at 60 seconds. `git diff --check` passed.
- **Final content hashes:** controller `0f032ef5d581275abdf5d2fe07c6dabdc6ac187d59b1b0c192f4a00273b5f12c`; types `143a492b76045be7b71434e13dcc31e210235652ef0d77027784c01f958275e4`; exports `2e270d1f192a1b5fca0d22e4985689c1892f8caaf58891e641a9164c8979d5c2`; focused test `bda9b1be4e588de27cec75b320d0efb5c7458e5fa93de39f505430b993849604`.

### EJ-20260729-0101 — hostile Task-5 prefix-authority stop

- **Finding:** The approved pre-DL-136 `run_prefix` sketch could not prove its mandatory schedule digest or provider-cost ref, passed caller schedules/caps, let adapters self-certify counts/refs/terminal state, treated `grade_clone` and `verify_clone` names as isolation, omitted subject/simulator state from snapshots, and provided no verified create-only artifact closure. Implementing it would have made the shared causal prefix self-consistent but unauthoritative.
- **Action boundary:** Stopped T5-S02 code before adding receipt or runner behavior. Commissioned a read-only hostile contract audit as an untrusted proposal; the root agent retained scientific and decision authority. No subprocess, provider, cloud, model, experiment, training, or spend action ran.

### EJ-20260729-0102 — promote controller evidence authority into DL-136

- **Authority repair:** Amended the plan and design and appended DL-136. `provider_lane_plan_v2` now pins task input, primary/simulator/parser/meter, environment/restore/grader/verifier, isolation, caps, builds, source revisions, and closed evidence grammars. The controller must derive them from sealed schedule ancestry.
- **Execution closure:** Added immutable dispatch-intent to terminal-attempt to final-cost ancestry; complete failure/late/partial attempt states; controller tokenization; cumulative earliest-trigger state; separate terminal remainder and branch-pending queues; exact primary/simulator accounting; a closed composite snapshot; initial restore qualification; distinct grade/verify instance/process/root receipts; raw ref-free grade/verifier evidence; concrete create-exclusive fsynced storage plus fresh resolver readback; and schedule-derived prefix-index coverage.
- **ITT correction:** Natural no-trigger copies clone-derived `Y_0`. Adverse pre-trigger failure retains raw grade/verifier audit evidence but forces scientific `Y_0.success`, partial reward, and all four outcomes to zero. This prevents a successful last snapshot from converting timeout/refusal into success.
- **Review loop:** The first advisory review rejected caller-selected environment authority, success-only cost receipts, nominal fresh factories, ambiguous cumulative mutation, incomplete cap/parser/snapshot semantics, and schema ownership. The second rejected mutable dispatch persistence, unsettled-cost sealing, terminal queue contradiction, and caller coverage. The third found the adverse-`Y_0` contradiction. Each issue was repaired before the same reviewer approved with no remaining critical or important finding.

### EJ-20260729-0103 — DL-136 authority hashes and non-claims

- **Hash verification:** Plan SHA-256 `4c1e5bb3a17c887a3c0bfa8ecf917b9ea0360ab41822486283d89e9021f72a4f`; design SHA-256 `57b3ee0b8d98ec8f7c1baed5f1e4ef20554d5facb73576dac0c6820a2d23ced3`. DL-136 records those exact values; independent recomputation matched.
- **Static gate:** `git diff --check` passed. This is docs/authority only, so no software test or scientific experiment was substituted for review.
- **Boundary:** DL-136 authorizes no provider call, spend, confirmation run, model execution, empirical result, or claim promotion. Existing T5-S01 primitives remain implemented; provider-plan v2, receipt schema, verified evidence primitives, prefix engine, and prefix publication remain unimplemented next gates.

### EJ-20260729-0104 — reconstruct T5-S02A execution authority

- **TDD RED:** The focused controller command first failed at collection because the public `PrefixExecutionAuthority` did not exist. After upgrading the completed-power fixture to v2, the existing schedule-publication test failed on the historical v1-only validator. The nested-sealing test then failed because `seal_study_manifest` had not copied the provider closure.
- **Repair:** Added a frozen schedule-ancestry authority loader with exact public input types; closed v2 lane/task/cap grammars; canonical task input and subject/simulator/parser/meter/environment/grader/verifier/isolation contract validation; manifest revision, tokenizer, task, benchmark, lane, and simulator binding; and byte verification of every selected ref. Schedule sealing now consumes only the v2 validator. Study sealing recursively plans exact nested refs relative to the provider source root, verifies their bytes, copies them to the identical run-root paths, and reuses the same validator before manifest publication. Historical non-v2 provider sources remain opaque only for legacy generic copy coverage.
- **GREEN/static:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py::test_t5_s02a_study_seal_copies_v2_provider_nested_refs tests/resampling_null/test_artifacts.py::test_t3_s07_prefix_schedule_is_derived_and_published_inside_lease -q` passed 11 tests in 1.48 seconds. Focused Ruff passed all changed source/tests. Focused mypy with the repository's missing third-party stubs ignored reported no issues in five source files. `git diff --check` passed.
- **Boundary:** This slice reconstructs policy and refs only. It adds no provider dispatch, spend, training, model access, confirmation adapter, prefix execution, experiment, result, or promoted claim.

### EJ-20260729-0105 — repair rejected S02A closure

- **Review rejection:** Spec review rejected EJ-0104 because deep JSON refs were not recursively verified, known fixed JSON inputs stopped sealing recursion, semantic failure could leave partial sources, parsed call caps and grammars were discarded, simulator nullability was one-way, synthetic zero-cost closure was not enforced, and ArtifactRef roles were not purpose-bound.
- **Corrective RED:** Before production changes, `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 't5_s02a or t3_s07_prefix_schedule'` failed 36 tests with three passes. The matrix covered deep tamper/dangle, every named role, lane drift, simulator iff/zero caps, subject/simulator cap drift, parser grammar/tool drift, synthetic meter drift, known-revision recursion, and failed-seal atomicity.
- **Repair:** Added a cycle-safe exact-ArtifactRef closure walk for canonical JSON assets; exact roles at every named boundary; retained typed subject/simulator contract caps; conservative lane/aggregate and per-call/aggregate checks; exact simulator contract/lane equality; parser-to-subject/simulator grammar and tool-schema equality; simulator iff with all-zero absence; synthetic meter closure; and known-fixed JSON traversal. V2 study sealing now validates a complete temporary root and writes nothing to the run root until semantic validation succeeds.
- **GREEN:** The same focused command passed 39 tests with 221 unrelated tests deselected in 3.03 seconds. No provider dispatch, spend, training, model access, execution, experiment, result, or claim promotion was introduced.
- **Static:** Focused Ruff passed all changed source/tests; focused mypy with missing third-party stubs ignored reported no issues in five source files; project status and whitespace checks passed.

### EJ-20260729-0106 — close second S02A hostile review

- **Review rejection and RED:** A second spec review found four publication/authority holes: sequential final writes had no rollback, a lane could mix simulator-required and simulator-free tasks, study sealing did not derive synthetic authority from roster plus assignment facts, and subject aggregate caps were ceilings rather than exact lane maxima. The focused command failed exactly those four counterexamples while 39 checks passed.
- **Repair:** Final publication now tracks only transaction-attempted destinations and directories created by that call; any `BaseException` unlinks those destinations, removes only now-empty transaction-created directories, preserves the original exception, and leaves preexisting content untouched. An injected second-write failure proves an empty transaction footprint, absent manifest, preserved unrelated file, and exact retry success. Lane validation rejects mixed simulator capability before execution and enforces simulator presence only for homogeneous all-required lanes.
- **Authority and caps:** V2 study sealing now derives `synthetic_validation` only from a closed `synthetic_fixture` roster paired with a closed `synthetic_derangement` assignment, and `confirmation` only from the corresponding eligible-confirmation pair; disagreement or unknown authority fails before run-root publication. The derived authority reaches the staged provider validator, so a non-zero-cost synthetic meter cannot seal. Subject aggregate generated-token and model-call caps must equal the maximum prefix/branch values exactly.
- **GREEN/static:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 't5_s02a or t3_s07_prefix_schedule'` passed 45 tests with 221 deselected in 4.01 seconds. Focused Ruff passed. Raw focused mypy stopped only on the repository's absent third-party `jsonschema` stubs; rerunning with missing third-party imports ignored found no issues in the two source files. Project status, `git diff --check`, and scope checks passed.
- **Content hashes:** artifacts `687aa21200066aaae020e521f3fdc0297ed46659116693cd8033fdd85f16e444`; execution authority `277fd4eec1528e00c80969abe770aa91ea93783b0947de4b7ad78c5cba896848`; artifact tests `eb29afd07a28694c3a3e1237b51fc685264c0dae83520333f7efeafa0adcdd26`; controller tests `6cd8270c70c6c042a00568dd8cd7e16f5d3256ef98d13c9e198481e693c14170`.
- **Boundary:** No provider call, spend, model execution, training, experiment, causal result, or claim promotion occurred.

### EJ-20260729-0107 — ownership-safe S02A publication

- **Third review rejection and RED:** Review demonstrated that EJ-0106 tracked attempted names rather than proven ownership: a concurrent source or manifest could appear after the absence precheck, be replaced by the atomic writer, or be blindly deleted during rollback. It also found that derived synthetic/confirmation authority was not bound to conditional eligibility and ceremony refs. The focused command failed exactly six new counterexamples while 44 checks passed: source peer race, manifest winner race, cleanup denial, later-link failure, confirmation without conditionals, and synthetic with conditionals.
- **Create-exclusive repair:** Every final source and the manifest now use the same local POSIX create-exclusive transaction: create and fsync a no-follow same-directory temporary through a bound directory descriptor, atomically `link` it into an absent destination without replacement, unlink the temporary, fsync the parent, reopen no-follow, and verify exact device, inode, digest, and size. Ownership is recorded only after the link succeeds. The manifest is serialized from the already validated record and receives the identical install path and exact ArtifactRef.
- **Rollback repair:** Rollback opens each current name no-follow, compares device/inode and full bytes with its owned publication, and unlinks only a match. A peer-owned replacement is never removed. Cleanup failures and still-owned residual paths are collected rather than swallowed; any such result raises `RecordValidationError` with the original publication error as cause and names the incomplete cleanup. Normal later failure removes owned files and directories, preserves unrelated content, and permits an exact retry.
- **Conditional authority:** `synthetic_fixture` plus `synthetic_derangement` now requires both conditional refs null. `eligible_confirmation` plus `confirmation_lineage_matching` requires both non-null. Both mismatches fail before run-root publication, and a positive confirmation fixture proves both copied refs seal.
- **GREEN/static:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 't5_s02a or t3_s07_prefix_schedule'` passed 51 tests with 221 deselected in 4.50 seconds. Focused Ruff and mypy with missing third-party imports ignored passed; project status and `git diff --check` passed.
- **Content hashes:** artifacts `60b1fb1aa7236906c1ab149c15253baa81919f7f40567031b2ffaa67e760d079`; artifact tests `a5c284821d16e066116c6ff9c34b48be97104319efd37365a342db2ad20b9985`.
- **Boundary:** This changes only S02A authority reconstruction and first-record publication. No provider call, spend, model execution, training, experiment, result, or claim promotion occurred.

### EJ-20260729-0108 — reject path-bound publication and monolithic authority

- **Quality rejection:** Hostile review rejected commit `221e9e0` despite its create-exclusive leaf install. The transaction reopened parents by pathname, did not bind a single root descriptor across the transaction, could not safely distinguish a peer replacement during rollback, swallowed cleanup detail, and left the S02A validator/loader as a 1,271-line private-import knot with two giant duplicated fixtures.
- **Security RED:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py -q` initially failed all seven new tests because no descriptor-bound publication module existed. The matrix covered named-root swap, intermediate-ancestor swap, `fstat`/`stat` bind failures and fd closure, final peer replacement, hard-link alias rollback, and named temporary residue.
- **Repair:** Added one held-root `BoundPublication` transaction. It uses componentwise no-follow dirfd traversal/creation, same-directory fsynced temporaries, no-replace hard-link installation, root/ancestor and final-file identity verification, and reverse-order quarantine rollback. Quarantine verifies device, inode, full digest, size, and single-link ownership before deletion; mismatching peers are restored no-replace; aliases, temporary residues, descriptor-close failures, and rollback failures are reported with causal chaining.
- **Publication evidence:** The isolated publication/authority-cache/seal-publication command passed 11 tests in 1.07 seconds. Semantic seal integration injects faults by named role/path rather than `os.link` call count and proves peer-manifest preservation, rollback of an identified later roster failure, unrelated-file preservation, and clean retry.

### EJ-20260729-0109 — split and cache S02A execution authority

- **Architecture:** Moved the shared exception to `errors.py`; strict ordered ArtifactRef codec, descriptor-confined reads, recursive closure, and per-validation payload/decode caches to `authority_refs.py`; strict JSON/path utilities to `json_io.py`; provider asset validation to `provider_contract_assets.py`; provider-plan assembly/cross-binding to `provider_contracts.py`; schedule decoding to `task_schedule_codec.py`; and the public direct-parent boundary to `scientific_records.py`. `execution_authority.py` now contains the frozen result and schedule-to-task projection and has no private artifacts import. Schedule and manifest sealing statically consume the public provider validator; the dynamic execution-authority import is gone.
- **Contract correction:** Renamed role-neutral `SimulatorCaps` to `CallContractCaps`, made cap-field contracts ordered tuples, required exact non-empty roster/assignment authority text before pair lookup, and retained the cached decoded authority graph through each provider validation. Public registry/assignment validators replace new private cross-module reach-through.
- **Fixture repair:** Replaced the 481-line controller builder and 462-line study-seal setup with shared `ProviderAuthorityFixture` support split into 529- and 560-line modules. Publication unit tests and study-seal integration are separate. The pre-existing triggered-assignment fixture was corrected to mint the five task-bound provider refs for its added third task instead of appending an invalid incomplete v2 row.
- **Observed broad check:** A capped resampling-null run reached 460 passes and one failure in 56.71 seconds; the sole failure was that incomplete third-task fixture row. After the fixture repair, its exact isolated test passed with 224 deselected in 1.92 seconds. This is recorded as diagnostic evidence, not represented as a fresh full-suite pass.

### EJ-20260729-0110 — final local security/architecture gate

- **Fresh behavior:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_authority_refs.py tests/resampling_null/test_publication.py tests/resampling_null/test_study_seal_publication.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 'authority_reader or publication or t5_s02a or t3_s07_prefix_schedule or test_t3_s10_triggered_assignment_publishes_one_reachable_cas_proof'`; GREEN, exit 0, 60 passed and 219 deselected in 5.82 seconds.
- **Fresh static/status:** Ruff over all resampling-null source/tests passed. Focused mypy over six authority/publication modules reported no issues. `.venv/bin/python -m pneuma_lab.status --check` passed checkout coherence. `git diff --check` passed. Every process was capped at 60 seconds where applicable.
- **Size audit:** `authority_refs.py` 340 lines; `provider_contract_assets.py` 624; `provider_contracts.py` 436; `scientific_records.py` 73; `execution_authority.py` 359; `publication.py` 649. Provider core functions are 26–107 lines; execution projection/loader are 61/133; publication methods are at most 86 lines.
- **Content hashes:** authority refs `299ba53e61a001566a56e70c02e048d6afed8a6f9626e80b70a200ab14040982`; provider assets `f4f4fd543efbac8f8e6cc466411fd7b8c0f515aa27ad7bff29bdddd438d19237`; provider plan `702fb196bd44adf5813482fff5a5d831a1f96df2546ea4ad8d610d98147a1188`; scientific records `5216c35a5e6bd9835bf4e8c49f1a956b6639321398dd7a52211c63a6678371c5`; execution authority `ac162807137da004d37ba81f7199a6d52ead147a24467bb33ddb482dce9a37fe`; publication `0d783a227a139843144d836aafaa6781b3c7287596c847d8352556d5672edadd`.
- **Boundary:** This repair strengthens local S02A authority reconstruction and first-record publication only. No provider dispatch, spend, model execution, training, experiment, causal result, or claim promotion occurred. Confirmation execution and empirical evidence remain absent.

### EJ-20260729-0111 — reject unsafe rollback races and descriptor leaks

- **Post-commit rejection:** Hostile review rejected `76b8689296478c6dececa3e18e1b205d26db92ee`. Ordinary rename could overwrite a peer-created quarantine target; a quarantine-move error aborted later cleanup; nonregular peers could be stranded in quarantine; transaction-created directory and temporary names were deleted without rechecking identity; transient inspection failure could be misclassified as positive peer evidence; and two parent-directory failure paths leaked descriptors.
- **Corrective RED:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py -q` failed seven new rollback/fd counterexamples while eight prior checks passed. The added transient-inspection tripwire independently failed before repair. Final precommit audit added one same-inode content-mutation tripwire; it failed because changed owned content was restored as if positively identified peer state. The matrix precreated a quarantine peer, injected an initial move failure with two owned files plus one temporary, swapped in symlink/directory/temporary peers, mutated an owned inode, counted `/proc/self/fd` across created-parent fsync and parent-registration `fstat` failures, and denied positive quarantine classification.
- **Ownership rule:** Absence or uncertainty never authorizes deletion. Every published file, temporary, and created directory carries its recorded device/inode identity into rollback. A moved name is inspected no-follow in quarantine; exact owned objects may be removed, positively identified peer objects are restored without replacement, and any uncertainty or failed restore is reported with the exact residual path.

### EJ-20260729-0112 — no-replace quarantine repair and final local gate

- **Repair:** Added Linux `renameat2(RENAME_NOREPLACE)` quarantine/restore primitives that fail closed when unavailable. Rollback now continues across all temporaries, publications, and directories, collecting every failure/residual and chaining `PublicationRollbackError` from the original exception. Parent descriptors close on created-directory fsync failure and post-open registration failure. Quarantine mechanics were extracted one-way into `publication_rollback.py`; `publication.py` retains transaction orchestration and test-injectable naming/rename boundaries.
- **Fresh behavior:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py tests/resampling_null/test_study_seal_publication.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 'publication or t5_s02a or t3_s07_prefix_schedule or test_t3_s10_triggered_assignment_publishes_one_reachable_cas_proof'`; GREEN, exit 0, 68 passed and 219 deselected in 5.53 seconds. The publication-only matrix passed all 17 checks after the final hostile audit.
- **Fresh static/status:** Ruff check and format-check passed over the two publication modules and focused test. Mypy reported no issues in the two source modules. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. Every test/static process was capped at 60 seconds.
- **Size/hashes:** `publication.py` 461 lines, SHA-256 `918bae1a2882b22744c230e7734c9003aa3aa88e219e2992187c08311569c547`; `publication_rollback.py` 543 lines, SHA-256 `e638843415a1a6594cfb294f18470374339667a240f357255e2fae8dd1abb639`; focused test SHA-256 `d59acb297bf83e508927a1e2c60b942d7ea6b6b01b2f408a9f4ba6d6be55931a`. Rollback item functions are 90–131 lines.
- **Boundary:** This remains local S02A authority/publication hardening. No provider dispatch, spend, model execution, training, experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0113 — reject pre-ledger creation and post-move substitution

- **Review rejection:** Exact-commit review rejected `2c020b2e9c4dee5130fa9a28a4bb7d3cc55794e6`. A temporary existed after create-exclusive `open` but before its first `fstat` ledger entry; a directory existed after `mkdir` but before reopen/`fstat` registration; and rollback trusted the quarantine name after rename without proving it remained the moved source. Those windows allowed raw original exceptions, unreported created names, or a substituted peer restored cleanly while moved owned bytes survived elsewhere.
- **Corrective RED:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py -q -k 'temporary_first_fstat or created_directory_binding_failure or post_move_quarantine_substitution'`; RED, exit 1, all six selected cases failed with 17 deselected in 0.46 seconds. The matrix injected first temporary `fstat`, created-directory reopen and `fstat` failures, plus deterministic post-move symlink substitution for a published file, temporary, and created directory.
- **Fail-closed rule:** Creation is ledgered immediately with unknown identity and upgraded only after successful descriptor metadata. Unknown names are never moved or deleted and are reported as exact residuals. Known rollback sources require a held identity across quarantine movement; post-move name substitution cannot become positive peer evidence.

### EJ-20260729-0114 — bind rollback identity across quarantine movement

- **Repair:** Temporary and directory ledgers now receive an unknown-identity record immediately after successful creation. Rollback preserves and reports those names if identity establishment fails. For known files, temporaries, directories, and symlinks, rollback opens the source with Linux `O_PATH|O_NOFOLLOW|O_CLOEXEC`, holds that descriptor across true no-replace rename, and compares the no-follow quarantine device/inode to the held source before classification, restore, or deletion. A mismatch restores the current peer no-replace but reports ownership loss and the logical residual while the moved object remains linked.
- **Legacy-race distinction:** A pre-rename peer replacement can make the held owned inode unreachable rather than move it. A post-mismatch `fstat` link-count check distinguishes zero-link destruction, which has no owned residual, from a still-linked moved object, which blocks clean rollback. This retained the existing final-race behavior without weakening the new stolen-object gate.
- **Fresh behavior:** The publication-only matrix passed all 23 checks in 0.31 seconds. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py tests/resampling_null/test_study_seal_publication.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 'publication or t5_s02a or t3_s07_prefix_schedule or test_t3_s10_triggered_assignment_publishes_one_reachable_cas_proof'`; GREEN, exit 0, 74 passed and 219 deselected in 5.51 seconds.
- **Fresh static/status:** Ruff check and format-check passed over both publication modules and the focused test. Mypy reported no issues in the two source modules. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. Every test/static process was capped at 60 seconds.
- **Size/hashes:** `publication.py` 483 lines, SHA-256 `67c48af8fb0f36ce1c9efde00fa3a2aa2249a219635823c792285e6727ff7659`; `publication_rollback.py` 697 lines, SHA-256 `e5de80b796bdbaf56a1abef9743c8fd6a5c1db377c0451efc4dd452492f14404`; focused test SHA-256 `c67cf4f62d271c9ef4cebbbb0c27f26383444986ae083756eafa0fe19592f2bc`. Identity/quarantine core functions are 36–133 lines.
- **Boundary:** This is local S02A publication hardening only. No provider dispatch, spend, model execution, training, experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0115 — reject zero-link ordering and conditional-unlink claims

- **Review rejection:** Exact-commit review rejected `2b3a283b29284602e9d655fe0d19480d4a345c2a`. In the opposite pre-rename ordering, rollback could hold a peer inode, move the ledger-owned inode into quarantine, observe the held peer at zero links, restore the owned inode, and return clean. Ownership-loss reporting also mislabeled a restored peer pathname as the owned residual. Separately, the final no-follow stat followed by name-based `unlink`/`rmdir` was described too strongly: POSIX has no atomic conditional unlink by device/inode.
- **Corrective RED:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py -q -k 'post_move_quarantine_substitution or opposite_pre_rename or publication_namespace_lease'`; RED, exit 1, all six selected cases failed with 20 deselected in 0.48 seconds. The matrix covered file/temp/directory unlocated ownership, deterministic held-peer/named-owned inversion, concurrent publication exclusion, lease release, and setup-failure descriptor cleanup.
- **Boundary decision:** Do not use rename-exchange loops as security theater. Local cleanup may rely only on a held cooperative namespace lease. An uncooperative same-UID mutator remains outside that boundary; hostile namespace mode would require quarantine-only rollback and operator garbage collection.

### EJ-20260729-0116 — cooperative publication lease and truthful residuals

- **Identity repair:** Quarantine binding now receives the expected ledger device/inode. When the moved quarantine name equals that expected identity despite a stale held peer, rollback reopens it with `O_PATH`, verifies the rebound descriptor, and continues owned cleanup before considering the stale descriptor's zero-link state. Ownership that remains linked but no longer has a known path is represented by a typed device/inode plus logical-former-path token, never as a false residual pathname.
- **Cooperative lease:** `BoundPublication` holds nonblocking exclusive `flock` leases on its stable root directory descriptor and a root-confined no-follow regular `.pneuma-publication.lock` for the complete root-descriptor lifetime. A second cooperating publisher fails closed. Setup, rollback, commit, cleanup, and close paths release both locks and descriptors; the lock file is identity-checked and removed while the root lease remains held.
- **Threat model:** The repair plan now states the final stat-to-unlink/rmdir namespace gap explicitly. The local lease serializes cooperating writers only and does not claim malicious same-UID safety. Confirmation/production remains fail-closed until registry-backed exclusive-writer authority plus an operator-enforced ACL, dedicated UID, protected mount namespace, or equivalent boundary exists.
- **Fresh behavior:** The publication-only matrix passed all 26 checks in 0.35 seconds. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py tests/resampling_null/test_study_seal_publication.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 'publication or t5_s02a or t3_s07_prefix_schedule or test_t3_s10_triggered_assignment_publishes_one_reachable_cas_proof'`; GREEN, exit 0, 77 passed and 219 deselected in 5.47 seconds.
- **Fresh static/status:** Ruff check and format-check passed over the three publication modules and focused test. Mypy reported no issues in all three source modules. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. Every test/static process was capped at 60 seconds.
- **Maintainability/hashes:** `publication.py` 615 lines, SHA-256 `0db7a0b3ab139ad3cbf68869d4b9c063c2e62785b9418027f1537f357ec308c0`; `publication_rollback.py` 488, `017455b278fbb5865e6a265fe41477dc016c86f68ae148a86ea910a2467d8816`; new `publication_quarantine.py` 435, `dac9fdbf95c0ad016a8d2534939d41dbc485e7b776d23a941d25886ad77f79bd`; focused test `53390a398db7ebc48b00700abb49244844456646966331988631c1d2336ca56d`; repair plan `49c76f87011e5952bc80f2a2b0fd653536a587da28fc9a40f216c73087075ae2`. Quarantine state-machine functions are 24–120 lines.
- **Boundary:** No provider dispatch, spend, model execution, training, experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0117 — make publication cleanup failures forensic

- **Review rejection and RED:** Exact-commit review rejected `894a4026974b55347b01fd9182ba27f60051e619`. `BoundPublication.__enter__` discarded namespace-lock unlock, descriptor-close, lock-unlink, and root-unlock failures, while root close could replace the original setup exception. The O_PATH rollback-source finalizer also discarded close failures. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py -q -k 'setup_cleanup_failure_is_aggregated or rollback_source_close_failure_is_typed_and_aggregated'` was RED, exit 1: all six selected cases failed with 26 deselected in 0.68 seconds.
- **Setup repair:** A mutable setup-ownership record now explicitly tracks the root descriptor, namespace-lock descriptor, whether the lock name was created, and acquired locks until successful transfer into the transaction. Setup cleanup attempts every owned release operation, records each failure, names the lock path only when unlink actually fails, represents close uncertainty as a typed descriptor residual, and raises `PublicationRollbackError` from the original setup exception only when cleanup is incomplete. A successful cleanup still re-raises the original exception unchanged.
- **Rollback repair:** O_PATH close is now a result-bearing operation at every early-return, rebind, superseded-binding, and terminal rollback site. Filesystem results and descriptor results are merged: successful deletion plus close failure reports no false file-path residual, retains the original terminal cause, and emits the exact descriptor number and purpose as close-state uncertainty. The injected close wrapper performs the real close before raising, proving the process fd set returns to baseline while the syscall result remains correctly treated as uncertain.
- **Fresh behavior:** The six-case corrective matrix passed with 26 deselected in 0.41 seconds; the complete publication matrix passed all 32 checks in 0.41 seconds. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_publication.py tests/resampling_null/test_study_seal_publication.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py -q -k 'publication or t5_s02a or t3_s07_prefix_schedule or test_t3_s10_triggered_assignment_publishes_one_reachable_cas_proof'`; GREEN, exit 0, 83 passed and 219 deselected in 6.00 seconds.
- **Fresh static/status:** Ruff check and format-check passed over the three publication modules and focused test. Mypy reported no issues in the three source modules. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. Every process was capped at 60 seconds.
- **Maintainability/hashes:** `publication.py` 678 lines, SHA-256 `7cc715feac2ebc1b4c4a35511e271545de794b6b5c72a059c5611ede348b5832`; `publication_quarantine.py` 550, `bf85f5a3c5e647b7f03e6d66c56b9b4a561b882b9441ee6cb16486474ebc96a9`; `publication_rollback.py` 571, `11f96b94da4cc47c893a742df82c809d6d5bca3ce7d395f27ba456082b01a2d0`; focused test `aea4483d9fa2085ebbb1e00fd9dbc0edd08f67980d2d26e04b584e631e03c2bc`. All three modules remain below 700 lines; setup enter is 86 lines, `quarantine_source` 126, and the largest rollback item function 148.
- **Boundary:** This is failure-accounting hardening for local S02A publication only. The cooperative-writer threat boundary is unchanged. No provider dispatch, spend, model execution, training, experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0118 — independent final S02A review

- **Spec review:** The independent spec reviewer approved exact implementation SHA `bfe923bdf065f2a9fa9a766a591f3f144593ec39` with no critical, important, or minor finding. The reviewer verified the new setup and O_PATH cleanup accounting, typed descriptor uncertainty, unchanged cooperative-local threat boundary, and unchanged S02A authority surface.
- **Quality review:** The independent hostile quality reviewer approved the same exact SHA with no critical or important finding. Both prior cleanup blockers were closed: setup cleanup now preserves the original cause while aggregating every release failure, and every O_PATH close route merges descriptor uncertainty without inventing a filesystem residual. The reviewer retained one nonblocking note that the two shared test-fixture builders remain roughly 480 lines each; the earlier duplicated fixtures are gone.
- **Review receipts:** The reviewers independently reported a 32-check publication matrix, targeted six-case cleanup and prior rollback/lease gates, authority-inclusive focused integration, Ruff/format, mypy, project-status, and whitespace success. These are review receipts, not substitutes for the root agent's fresh release gate.
- **Boundary:** S02A reconstructs sealed execution authority and hardens first-record local publication. It does not implement provider dispatch, prefix execution, confirmation storage, training, spend, an experiment, an empirical result, or a promoted claim. Production remains fail-closed without registry-backed exclusivity and an operator-enforced namespace boundary.

### EJ-20260729-0119 — T5-S02B verified evidence primitives

- **Observed RED:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_controller_artifacts.py -q` failed collection because the new `evidence` and `controller_artifacts` modules did not exist. The independently added frozen-prefix cross-check test later failed collection because `FrozenPrefixReceipt` did not exist. The amended-schema test rejected the DL-136 receipt because the old schema still required `pending_tool_calls`.
- **Evidence closure:** Added frozen/slotted exact provider intents and terminal attempts, closed status/evidence nullability including explicit late and response-less timeout forms, exact ordered provider/tool ledgers, refusal vocabulary, complete settlement ancestry, typed zero-attempt and attempt-bound zero-cost closures, a closed canonical composite snapshot codec with distinct branch/terminal queues, raw ref-free grade/verifier evidence, and distinct restore instance/process/root receipts. `FrozenPrefixReceipt` byte-checks every duplicated snapshot field.
- **Local CAS:** Added a final cooperative-local controller store and fresh resolver. Writes are role-confined and content-addressed, no-follow/create-exclusive, file/parent fsynced, reopened and byte/hash/length/path/role checked; resolver reads independently after close and requires the controller's expected role. Traversal, root-identity swap, symlink roots/leaves, collision, tamper, cross-role paths, use-after-close, and uncertain cleanup fail closed. This is not malicious same-UID or production-backend authority.
- **Schema correction:** Amended pre-release `resampling-prefix-receipt` v0.1.0 with schedule-bound caps, exact token ref/digest, separated queues, terminal failure, simulator counters, provider-attempt and boundary-ledger refs, uint64 call indexes, and closed unknown-field rejection. Existing minimal and downstream artifact fixtures were migrated.
- **Fresh behavior:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_artifacts.py -q -k 'evidence_primitives or controller_artifacts or prefix_receipt_schema_v01 or registry_and_schema_metadata_are_closed or prefix_receipts_are_nonempty'`; GREEN, exit 0, 43 passed and 223 deselected in 1.24 seconds.
- **Fresh static/status:** Focused Ruff passed. Focused mypy reported no issues in the two new source modules. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed.
- **Boundary:** No `run_prefix`, provider dispatch, tool execution, grade/verifier execution, prefix-index publication, branch behavior, provider/model/network call, spend, training, experiment, empirical result, or claim promotion was implemented or performed.

### EJ-20260729-0120 — reject nominal refs and close S02B forensic ancestry

- **Review rejection:** Exact-SHA review rejected `b2bdc264ae8fde16ebd6f32c3d5ee579d8cf16b6`. Exact nominal `ArtifactRef` types did not purpose-bind role/path, snapshot digests were not tied to their refs, caps and terminal/Y0 state were underclosed, grade/verify restore receipts were not reachable from the prefix record, custom schema semantics lagged the Python records, provider events could repeat, and resolver close could skip its second descriptor.
- **Observed RED:** The focused repair selection initially failed all 18 cases. Counterexamples covered wrong controller roles and non-CAS paths, subject/simulator contract crossing, visible/token digest mismatch, adverse nonterminal snapshot state, cap mismatch, adverse nonzero Y0, duplicate provider events, wrong schema edge roles, both pending queues, branch-plus-timeout, duplicate/gapped role-local call indexes, unequal wall counters, simulator tool use, wrong snapshot role, and resolver close failure. Follow-up REDs exposed missing verifier ancestry, duplicate queue call IDs, direct frozen-receipt digest checks, and the incompatibility of treating raw verifier evidence as an execution receipt.
- **Repair:** Controller refs now require exact purpose role plus `controller-artifacts/{role}/{sha256}`; S02A refs require exact registered roles. Provider/model/tool/settlement/snapshot/grade/verifier edges are closed field by field. Composite and frozen snapshots bind visible/token digests, terminal/failure state, queue order/uniqueness, counters, remaining quotas, and caps. Adverse no-trigger requires forced-zero scientific Y0. Raw grade/verifier evidence remains on the legacy direct edges for packet/outcome compatibility, while new required `grade_execution_receipt_ref` and `verifier_execution_receipt_ref` fields make distinct restore ancestry reachable without implementing execution. Schema roles and `validate_record` semantics now mirror these rules. Provider-event uniqueness and aggregate resolver cleanup are enforced.
- **Fresh behavior:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_artifacts.py -q -k 'evidence_primitives or controller_artifacts or prefix_receipt_schema_v01 or t5_s02b_prefix_semantics or registry_and_schema_metadata_are_closed or prefix_receipts_are_nonempty or packet_pair_verifier_ancestry_seals_exact_prefix_artifacts or artifact_root_rejects_dangling_and_conflicting_refs or t3_s07_completed_power_consumer_derives_manifest_membership'`; GREEN, exit 0, 75 passed and 218 deselected in 4.38 seconds.
- **Fresh static/status:** Focused Ruff and format-check passed. Focused mypy with missing third-party stubs ignored reported no issues in the three touched source modules. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed.
- **Boundary:** This remains immutable evidence/schema/local-CAS repair only. No `run_prefix`, provider dispatch, tool/grade/verifier execution, prefix publication, branch behavior, network/model/provider call, spend, training, experiment, empirical result, or claim promotion was implemented or performed.

### EJ-20260729-0121 — DL-137 trigger/terminal and provenance authority

- **Review rejection:** Exact-SHA re-review of `e836bbdcf24dd41881c67f396fff8a1233275cb1` found that the implemented explicit grade/verifier execution receipt edges were absent from the governing Task-5 record sketch and that `FrozenPrefixReceipt.validate_snapshot_bytes` did not bind trigger class to the composite snapshot's terminal state.
- **Observed RED:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_evidence_primitives.py -q -k 'cross_binds_trigger or coherent_trigger_terminal'` failed the three contradictory pairs while the three coherent pairs passed: no-trigger/nonterminal, first-eligible/terminal, and fourth-tool/terminal were incorrectly accepted.
- **Authority amendment:** The plan and design now preserve direct raw grade/verifier evidence refs, require separate reachable grade/verifier execution receipt refs, and require no-trigger iff terminal versus either branch trigger iff nonterminal. Appended DL-137 without rewriting DL-136. Recomputed plan SHA-256 `62f9b221d7080087e56b631418ff5cec3670cd7adff2e268fd0aed53ae87a576` and design SHA-256 `a7369435afaedc182fe5a8a22a1da46a9bfc0edf564c51d39d14f2f93815c0ff`; `docs/project-status.json` contains no superseded DL-136 authority-hash field requiring amendment.
- **Repair/GREEN:** Snapshot validation now requires `NO_INTERVENTION_OPPORTUNITY` exactly when `episode_terminal` is true and either branch trigger exactly when it is false. The corrective six-case command passed all 6 checks. Fresh focused behavior `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_evidence_primitives.py -q` passed all 34 checks in 0.39 seconds.
- **Fresh static/status:** Focused Ruff and format-check passed. Focused mypy with missing third-party stubs ignored reported no issues. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed.
- **Boundary:** DL-137 and this repair add governance and immutable cross-validation only. No provider call, tool execution, grade/verifier execution, prefix publication, branch execution, network/model call, spend, training, experiment, empirical result, or claim promotion occurred.

### EJ-20260729-0122 — DL-138 S02B quality-rejection repair

- **Quality rejection:** Exact-SHA review rejected `fd0ca3b021295cc5c1240e8b259c0e7a0ac9241f` with no critical and four important findings. A failed tool boundary could remain nonterminal and be followed by later execution; prefix artifact mappings bypassed exact runtime `ToolCall`/grade/verifier contracts and did not bind both schedule digests to the outer ref; controller refs and resolver trusted forgeable media metadata; and post-create close/read/verification failures could strand a digest or mask the primary error.
- **Observed RED:** The first three-module command was hard-stopped by `timeout 60s` near completion and is not counted as evidence. The corrected targeted 13-case command completed in 1.16 seconds with 8 failures and 5 already-protected cases: nonterminal failure, missing resolver media expectation, uppercase media acceptance, stranded close-failure digest/retry collision, masked verification/read-close/role-close errors, noncanonical tool arguments, successful infrastructure failure, and schema whitespace media acceptance. A strengthened outer-schedule case set both nested digests wrong together. A final strict-TDD cleanup cycle changed the close-failure expectation to mandatory `ExceptionGroup`; it failed once with the bare primary `OSError` before repair.
- **Authority and DL-138:** The plan and design now require failure-terminal-final chronology, exact mapping-to-runtime decoding, both receipt schedules bound to `payload.schedule_ref.sha256`, canonical role-bound media types with required resolver expectation, and transactional post-create cleanup with uncertain-close ownership relinquished before the one close attempt. Appended DL-138 without rewriting DL-137. Plan SHA-256 is `33d2da73479fb1274aec2ad9df6354b8b6c379c249f5b2f7d74ce30e1da41e10`; design SHA-256 is `1bc82b73e5ccd0014b89baea253fc098f20cb674d39e09c9f9635e7071bb8ccc`.
- **Repair:** `CompletedToolBoundaryReceipt` rejects every non-`none` nonterminal failure and the ledger retains terminal-final enforcement. Prefix validation locally imports and instantiates exact frozen runtime values, converts runtime exceptions to `RecordValidationError`, and checks task plus verifier schedules against the enclosing schedule ref. Schema and runtime refs purpose-bind JSON versus raw octet-stream media; the resolver requires exact expected role and media. CAS write ownership is centralized: after creation, any failure attempts each still-owned close once, reopens the role directory when an uncertain close relinquished it, unlinks the digest, fsyncs the role directory, and raises an `ExceptionGroup` retaining the primary and all cleanup failures.
- **Fresh GREEN:** The targeted rejection suite passed 13/13 in 0.91 seconds. The full evidence/CAS modules passed 48/48 in 0.46 seconds. The focused prefix artifact selection passed 17 checks with 224 deselected in 0.52 seconds. Schema loading passed 201/201 in 1.68 seconds. The post-aggregation cleanup selection passed 3/3 in 0.32 seconds. Every test process was hard-capped at 60 seconds.
- **Fresh static/status:** Focused Ruff lint and format-check passed. Raw mypy stopped only on the repository's absent third-party `jsonschema` stubs; the established rerun with missing third-party imports ignored reported no issues in the three changed source modules. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. The untracked `raw_root_placeholder` was preserved untouched.
- **Boundary:** This is immutable evidence/schema/cooperative-local CAS hardening only. No `run_prefix`, provider dispatch, tool/grade/verifier execution, prefix publication, branch execution, network/model/provider call, spend, training, experiment, empirical result, causal result, or claim promotion was implemented or performed.

### EJ-20260729-0123 — correct incomplete S02B GREEN and BaseException cleanup

- **Receipt correction:** EJ-0122's fresh-GREEN paragraph was true only for its listed narrow commands and was insufficient as the S02B authority gate. It omitted the exact standalone prefix-schema fixture and shared full-study ancestry consumers. Exact-SHA quality re-review of `102d120f130f32e16bc2164514eaa02ba15e74c3` therefore remained RED: the reviewer's focused authority command reported 3 failed, 87 passed, and 222 deselected. The schema fixture still labeled raw grade/verifier evidence as `application/json`; the shared `_build_full_study` helper still labeled newly JSON-bound controller records as `application/octet-stream`, so dangling-ref and packet-pair ancestry checks failed before reaching their intended assertions. The same review found that `ControllerArtifactStore.write` caught only `Exception`, contradicting DL-138 for `KeyboardInterrupt`/other `BaseException` after create-exclusive publication. This entry corrects the receipt; EJ-0122 remains append-only and unedited.
- **Observed RED:** An expanded authority-inclusive reproduction over evidence primitives, controller artifacts, exact prefix schema, prefix semantics, registry/nonempty checks, packet-pair ancestry, dangling/conflicting refs, and completed-power consumers failed 5 with 89 passed and 218 deselected in 3.40 seconds; the two additional failures were the same shared-fixture defect reached through completed-power consumers. The new post-create `KeyboardInterrupt` regression caught the original interruption but retry collided with the stranded digest. A separate non-`Exception` plus unlink-failure regression received the bare primary instead of the required `BaseExceptionGroup`.
- **Repair:** The exact schema fixture and shared full-study builder now use one closed controller role-to-media mapping: raw grade/verifier evidence is `application/octet-stream`; composite snapshots, visible context, token IDs, provider/boundary/cost ledgers, and grade/verifier execution receipts are `application/json`. The deliberately dangling provider-cost ref is also JSON so the test reaches dangling ancestry rather than failing early on metadata. The CAS transaction catches `BaseException` only after the role/digest creation boundary, performs the existing one-attempt ownership cleanup without retrying uncertain closes, re-raises the original non-`Exception` when cleanup succeeds, and raises `BaseExceptionGroup` containing the primary plus every cleanup `Exception` when cleanup is uncertain. Ordinary `Exception` behavior remains unchanged.
- **Fresh GREEN:** The two BaseException regressions passed with 13 unrelated CAS checks deselected in 0.37 seconds. The expanded authority-inclusive command passed all 96 selected checks with 218 deselected in 5.49 seconds. This is the authority-inclusive receipt missing from EJ-0122.
- **Authority:** DL-138 already requires cleanup after any post-create failure and canonical role-bound media; no authority changed and no new decision-log row is needed. Plan SHA-256 remains `33d2da73479fb1274aec2ad9df6354b8b6c379c249f5b2f7d74ce30e1da41e10`; design SHA-256 remains `1bc82b73e5ccd0014b89baea253fc098f20cb674d39e09c9f9635e7071bb8ccc`.
- **Fresh static/status:** Focused Ruff and format-check passed over the changed source and fixtures. Focused mypy with missing third-party imports ignored reported no issues in the changed source. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. Every process was capped at 60 seconds; the untracked `raw_root_placeholder` remained untouched.
- **Boundary:** This is fixture/receipt correction and cooperative-local CAS failure cleanup only. No `run_prefix`, provider dispatch, tool/grade/verifier execution, prefix publication, branch execution, network/model/provider call, spend, training, experiment, empirical result, causal result, or claim promotion was implemented or performed.

### EJ-20260729-0124 — final independent S02B review and root gate

- **Exact-SHA review:** The independent spec and hostile quality reviewers approved `b73ebcb48dccdad4ecfd7057ea1dc10ddd3bd0ef` with no critical, important, or minor finding. Both independently verified post-create `BaseException` cleanup, non-double-close ownership, canonical role/media fixtures, the append-only EJ-0123 correction, unchanged DL-138 authority hashes, and absence of S02C execution overbuild. The quality reviewer independently reproduced the 96-check authority gate; the spec reviewer separately reproduced its focused cleanup and status gates.
- **Fresh root behavior:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_artifacts.py -q -k 'evidence_primitives or controller_artifacts or prefix_receipt_schema_v01 or t5_s02b_prefix_semantics or registry_and_schema_metadata_are_closed or prefix_receipts_are_nonempty or packet_pair_verifier_ancestry_seals_exact_prefix_artifacts or artifact_root_rejects_dangling_and_conflicting_refs or t3_s07_completed_power_consumer_derives_manifest_membership'`; GREEN, exit 0, 90 passed and 224 deselected in 4.73 seconds.
- **Fresh root static/status:** Ruff lint and format-check passed over all substantively edited/new S02B Python files; focused mypy with missing third-party imports ignored passed over `evidence.py`, `controller_artifacts.py`, and `artifacts.py`; project status, the full S02B range whitespace check, and worktree check passed. The touched `types.py` adds one already-formatted enum member, but whole-file Ruff formatting was excluded because the exact pre-S02B base independently fails the same formatter check and applying it would introduce unrelated 15-hunk churn. Plan SHA-256 remained `33d2da73479fb1274aec2ad9df6354b8b6c379c249f5b2f7d74ce30e1da41e10`; design SHA-256 remained `1bc82b73e5ccd0014b89baea253fc098f20cb674d39e09c9f9635e7071bb8ccc`. The untracked `raw_root_placeholder` remained untouched.
- **Release decision:** T5-S02B is complete for immutable provider/tool/grade/verifier evidence primitives, strict frozen-prefix mapping/schema validation, and the cooperative-local create-exclusive CAS/fresh resolver. The next gate is S02C prefix execution; S02B does not authorize or implement it.
- **Boundary:** No provider dispatch, tool/grade/verifier execution, prefix publication, branch execution, network/model/provider call, spend, training, experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0125 — DL-139 S02C executable-authority closure

- **Hostile audit:** The pre-DL-139 S02C sketch still accepted a caller store and broad adapters, retained confirmation prose, left parser/tokenizer/renderer/evidence codecs injectable, let exact fixture types hide caller-selected programs, treated logical clone labels as isolation, omitted an initial-restore ancestry edge, lacked a closed raw-provider observation, left equality-at-deadline/overshoot/turn/model-cap semantics ambiguous, forced known terminal remainder toward malformed action, allowed environment-self-certified tool state, treated byte-identical CAS reuse as a collision, and blurred candidate construction with prefix publication. Implementing it literally could have produced stable but non-reconstructable evidence.
- **Authority choice:** Appended DL-139 and amended the plan/design. S02C is now synthetic-validation-only and split into four reviewable internal slices: contracts/source attestation plus verified CAS reuse; subprocess-backed initial restore identities; the controller-owned provider/simulator/tool loop; and final snapshot/grade/verify/fresh-resolver candidate construction. Exact final fixtures bind the canonical program bytes; internal registries instantiate codecs; raw observations, named clock reads, cap/failure/trigger precedence, controller-created root/PID/inode identities, restore receipts, independently queried tool state, canonical zero-cost events/settlements, and close-before-fresh-resolve are closed. S02D alone performs independent full-roster reload, coverage/order/cost checks, and prefix-index sealing.
- **Authority hashes:** Final plan SHA-256 is `c3d0752ba672e8d35b6cbb6fceb9d10613ffddf90011723a177b96dba38e9303`; final design SHA-256 is `92cc3cc903445e40129eb6056de15d15e9d9c798cfcacc9f5dd457c339b51b56`. DL-139 records these exact values.
- **Fresh docs gate:** `.venv/bin/python -m pneuma_lab.status --check` passed; `git diff --check` passed; independent `sha256sum` reproduced both DL-139 authority hashes. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This entry and DL-139 are docs-only authority. No Python, schema, or test file changed; no fixture execution, provider/model/network/external call, credential use, spend, confirmation, branch, assignment, packet, prefix publication, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0126 — DL-140 exact S02C authority-rejection repair

- **Exact-authority rejection:** Review rejected `edcd096` before implementation. Its post-action cap ordering could suppress the valid fourth-tool trigger at equality; `run_prefix` returned trusted in-memory state instead of immutable candidate bytes; simulator order could be selected by an ambiguous split script; supplied exact fixture objects could still hide caller state; module-file hashing was described too much like execution attestation; factory-owned process identity and underspecified root cleanup weakened isolation; and the optional/inline program plus incomplete response/event/parser timing rules left status self-certifiable.
- **Repair:** Appended DL-140 and amended the current plan/design without rewriting DL-139 or EJ-0125. Discrete caps are now inclusive pre-action maxima and only token/wall overshoot can newly fail after completion; boundary-four failure/terminal/overshoot precedes an otherwise valid trigger. S02C stores and fresh-resolves one canonical `prefix_candidate_receipt` wrapper and returns its ref; S02D alone accepts ordered wrapper refs and seals coverage. One controller-derived actor loop uses `simulator_context`, forbids simulator tools, and consumes one role-bearing transcript. `run_prefix` has no fixture arguments; a closed descriptor registry constructs every component at zero position. Stable no-follow source reads are explicitly only cooperative-local provenance. The controller owns create-exclusive roots, Popen/IPC, final liveness/alias checks, and success/failure cleanup aggregation. One required manifest-copied program pins request bytes/digests/input tokens and observations, while a complete deadline/response/transport/parser table derives status before mutation.
- **Authority hashes:** Final plan SHA-256 is `fe0cb22b71c81b94c65376e6544ebee2bedeb74f0b35cfe60fb5fb5b5cf0a149`; final design SHA-256 is `8862066d00741126665a0183c1d55478e51376c91a17d46e4d1f912bff05d78f`. DL-140 records those exact values.
- **Fresh docs gate:** `.venv/bin/python -m pneuma_lab.status --check`, `git diff --check`, and independent authority `sha256sum` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is append-only docs authority repair. No Python, schema, or test changed; no fixture, provider/model/network/external call, credential use, spend, confirmation, branch, assignment, packet, prefix publication, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0127 — DL-141 destination and loader-class repair

- **Re-review rejection:** Exact re-review of `1d4be8b` found two important authority seams. The repaired S02D signature had accidentally omitted its publication destination, and “fresh-resolve the whole graph” did not specify which mutually exclusive loader could verify controller artifacts, copied authority assets, and scientific schedule/manifest parents. A controller resolver cannot honestly verify all three.
- **Repair:** Appended DL-141 and amended the plan/design. `seal_prefix_index` again requires an exact normalized, run-root-confined, nonreserved `out`, publishes create-exclusively with file and parent fsync plus reopen verification, and rejects existing targets; S02C cannot call it. One closed disjoint role registry now dispatches scientific parents to a fresh scientific-record loader, controller roles to a fresh `ControllerArtifactResolver`, and copied authority roles to a separately fresh `AuthorityRefReader`. Unknown/cross-class/aliased refs reject, and every recursive ref is loaded by exactly one class before S02C return and again from entirely fresh instances before S02D publication.
- **Authority hashes:** Final plan SHA-256 is `ead8a1b1000b3ca8c50df25bc8519ebebd5d8a29fe28429dae55d696415f535e`; final design SHA-256 is `cabcf98402b9b74411ba5667e18902c3ce71f4c57a52027222c661f6d4638c98`. DL-141 records those exact values.
- **Fresh docs gate:** `.venv/bin/python -m pneuma_lab.status --check`, `git diff --check`, and independent `sha256sum` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is docs-only authority repair. No code/schema/test or external call occurred; no provider/model/network call, credential use, spend, confirmation, S02C publication, branch, assignment, packet, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0128 — final independent S02C authority review

- **Exact-SHA verdict:** The independent hostile authority reviewer approved `40ec7e4fd296d155adfef584f077a2c1041eaf2b` with no critical, important, or minor finding. The reviewer confirmed that DL-141 closes the explicit S02D destination and heterogeneous recursive-loader seams while every DL-140 cap/trigger, candidate handoff, simulator, caller-state, source-provenance, process/root, program/status, and non-claim boundary remains intact.
- **Independent hashes/status:** The reviewer independently reproduced plan SHA-256 `ead8a1b1000b3ca8c50df25bc8519ebebd5d8a29fe28429dae55d696415f535e` and design SHA-256 `cabcf98402b9b74411ba5667e18902c3ce71f4c57a52027222c661f6d4638c98`; project status passed and `raw_root_placeholder` remained untouched.
- **Release decision:** DL-139--DL-141 are approved as the executable authority for the four internal T5-S02C implementation slices. This approval authorizes implementation and local deterministic software tests only; it is not a fixture result, scientific experiment, confirmation run, provider/model/network call, spend authorization, empirical result, or claim promotion.

### EJ-20260729-0129 — T5-S02C-a contract, provenance, and idempotent-CAS core

- **Observed RED:** The first focused S02C-a collection failed because the closed contract module did not exist. Subsequent exact behavior REDs proved create-exclusive `EEXIST` still raised instead of verifying identical bytes; tampered and symlink reuse escaped the required typed failure; source refs lacked a held no-follow stable-read/recheck contract; candidate role/media validation was absent; terminal remainder was restricted to malformed action; overshoot incorrectly required `used + remaining == cap`; and `MODEL_CALL_CAP`/`TURN_CAP` were missing. Execution-authority RED then rejected the new required task-program field as open shape and lacked schedule/program/source/descriptor projection. A broad resampling-null diagnostic produced incomplete output and is not counted as release evidence.
- **Implementation:** Added one import-time validated, disjoint scientific/controller/authority role registry; frozen/slotted implementation, raw provider, ordered synthetic-program, clock, tool, grade, verifier, and physical environment-identity values; compact canonical strict program and candidate-wrapper codecs; exact candidate role/media/path validation; and a held-fd cooperative-local source-provenance reader with pre/post identity checks plus an explicit second-read API. `ControllerArtifactStore.write` now treats `EEXIST` only as no-follow, regular-file, identity/hash/length/exact-byte verified reuse, never unlinks a pre-existing blob, and retains DL-138 cleanup solely for a blob newly created by the current call.
- **Authority and receipt semantics:** Execution-ready authority is synthetic-only and exposes the manifest tokenizer, ordered source revisions, one required sealed program ref, and exact ordered descriptors for environment, subject, optional simulator, meter, tokenizer, renderer, parser, grader, verifier, event codec, and settlement codec. Historical schedule-sealing validation remains compatible while the execution-authority loader alone fail-closes on the new program field. `FailureKind` adds discrete model-call and turn caps; adverse no-trigger receipts may preserve any known queue; natural clean termination and branch triggers cannot; remaining primary quota is exactly `max(0, cap - used)`, preserving token/wall overshoot.
- **Fresh GREEN:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py::test_t3_s07_prefix_schedule_is_derived_and_published_inside_lease -q` passed 126 checks in 2.52 seconds.
- **Fresh static/status:** Focused Ruff over the changed resampling-null source and fixtures passed; `git diff --check` passed; `.venv/bin/python -m pneuma_lab.status --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Explicit remaining S02C-a work:** The subprocess-backed initial/snapshot restore record codecs and recursive heterogeneous graph traversal are not implemented in this review point. The former stays for the bounded S02C-a continuation before S02C-b environment execution; the latter remains expressly deferred to its DL-141 implementation slice. No partial `run_prefix` exists.
- **Boundary/non-claims:** No subprocess environment, provider/model/network/external call, tool execution, grade/verifier execution, credential use, spend, candidate publication, prefix index, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.
- **Final pre-commit rerun:** After type-only decoder casts, the same 126-check behavior command passed in 2.17 seconds; focused mypy with missing third-party imports ignored passed over all seven changed source modules.
- **Canonical-media RED/GREEN correction:** A final authority-asset regression first accepted a `text/plain` clock ref, proving loader media drift remained possible. Binding `decode_contract_ref` to the canonical authority registry made that case reject; the expanded final behavior gate passed 127 checks in 2.26 seconds.

### EJ-20260729-0130 — T5-S02C-a exact-contract authority correction

- **Review rejection and observed RED:** Exact-SHA review of `c800563777bbe4441dde8494a7fab9a9ab4ed6aa` found that the required initial/snapshot restore receipt contracts and the composite-snapshot qualification edge were absent; the public role maps were mutable; controller storage still admitted unregistered roles; provider rows carried caller-asserted transport/parser classifications; and failure injection named only a stage rather than one reachable actor/call/tool point. The first focused correction collection failed during import because `InitialRestoreQualificationReceipt` did not exist. Subsequent REDs covered mutable registries, unknown store roles, exact canonical restore round trips/ancestry, and incomplete failure targets.
- **Contract correction:** Added exact frozen/slotted `InitialRestoreQualificationReceipt` and purpose-bound `SnapshotRestoreReceipt` values with compact canonical strict codecs, canonical role/media/path validation, snapshot/resnapshot and visible/token digest binding, exact queues/terminal/failure state, controller-observed process identities, and `verified is True`. `CompositeSnapshotEnvelope` now requires the sole `initial_restore_qualification_ref` ancestry edge. This remains contract/codecs only: no restore, subprocess, environment, provider, tool, grade, or verifier execution was implemented.
- **Authority correction:** The controller, copied-authority, scientific-parent, and derived load-class maps are now immutable mapping proxies with import-time disjointness/coverage checks. `ControllerArtifactStore` rejects every unregistered role and derives its sole canonical media from that authority. Study source copying, execution-authority manifest source/tokenizer loading, controller evidence validation, and fixtures now use the same canonical role/media authority; the test-only generic deep role was replaced with the legitimate `synthetic_tool_result` role.
- **Program and failure closure:** Removed transport/parser fields from the caller-authored synthetic transcript; those classifications remain controller derivations from event/response bytes under DL-140. `SyntheticFailureInjection` now closes stage plus exact nullable actor, role-local call index, and tool-call ID. Task-input validation verifies an optional program even outside execution mode, recursively closure-verifies every nested program ref, rejects unknown/noncanonical nested roles/media, canonical-decodes the pinned tool schema, requires a nonempty schema for a trigger program, rejects response tool names absent from that schema, and rejects unreachable provider/tool failure targets. A copied third-task fixture now owns a task-bound program instead of reusing another task's assertion.
- **Hostile adjacent audit:** Canonical `source_revision` media is now selected by role during study source copying rather than inferred from a `.json` suffix; nested JSON authority used for closure testing moved into the canonical task payload because source-revision bytes are opaque. Targeted regressions reject empty trigger schemas, unreachable injection points, tampered nested program evidence, and an optional-but-unverified program. A broader artifact diagnostic reached the mandatory 60-second ceiling and is not release evidence; its isolated legacy branch-assignment raw-verifier fixture failure is outside this bounded S02C-a correction.
- **Fresh GREEN and static/status gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py::test_t3_s07_prefix_schedule_is_derived_and_published_inside_lease tests/resampling_null/test_artifacts.py::test_t5_s02a_study_seal_copies_v2_provider_nested_refs_atomically -q` passed 140 checks in 3.27 seconds. Focused Ruff passed. Focused mypy passed for six changed source modules with only missing third-party import stubs ignored. `git diff --check` and `.venv/bin/python -m pneuma_lab.status --check` passed; the untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** No S02C-b/c/d implementation or execution occurred. No subprocess environment, provider/model/network/external call, credential use, spend, candidate or prefix-index publication, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0131 — T5-S02C-a execution-ancestry and failure-target correction

- **Exact-SHA rejection and observed RED:** Re-review of `464528a785e748a18263d4d6f86335f9481230a9` found four remaining authority defects: superseded logical restore identities and over-wide grade/verifier wrappers survived beside the DL-139 records; the fresh controller resolver trusted caller-supplied expected role/media without consulting the immutable registry; generic task-payload JSON was mislabeled as a synthetic tool result and recursively nested roles bypassed the registry; and a failure injection could target a nominal completed provider row or a successful tool observation. The first focused collection failed because exact `GradeExecutionReceipt` was absent. Separate counterexamples then reproduced resolver unknown-role admission up to filesystem open, nested unknown-role laundering, and nominal-success failure targeting.
- **Execution-receipt correction:** Removed `RestoreIdentity`, `GradeEvidenceReceipt`, `VerifierEvidenceReceipt`, and `EvidenceExecutionPair`. Added only the exact frozen/slotted DL-139 records: grade binds `grade_restore_receipt` plus raw `grade_evidence`; verifier binds `verifier_restore_receipt` plus raw `verifier_evidence`. Their compact canonical codecs reject open shapes and noncanonical role/media/path bindings. Added exact two-ref schema definitions and migrated public exports/tests. `FrozenPrefixReceipt` retains its separate direct raw-evidence edges and required execution-receipt ancestry refs.
- **Resolver and authority-graph correction:** `ControllerArtifactResolver.resolve` now rejects an unknown expected role or noncanonical expected media from `CONTROLLER_ROLE_MEDIA` before any role/blob open. Generic nested fixture JSON uses the explicit immutable `deep_authority_asset -> application/json` authority role, never `synthetic_tool_result`. Task payload and program graphs are breadth-first role/media checked—including refs recursively discovered inside referenced JSON—before closure verification; unknown or media-drifted descendants fail closed.
- **Failure-target correction:** Added one immutable stage-to-completion mapping. `provider_parser` injection requires `MALFORMED_RESPONSE`; `provider_transport` requires `TIMEOUT_NO_RESPONSE`, `PROVIDER_ERROR`, or `INFRASTRUCTURE_ERROR`; a nominal completion/refusal/parser-only failure cannot satisfy it. Tool injection requires the exact actor/call/tool target, exactly one corresponding observation, and a non-`NONE` adverse failure. This adds no caller transport/parser field and no execution behavior; runtime derivation from bytes remains deferred to S02C-c.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_controller.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_artifacts.py::test_t5_s02a_study_seal_copies_v2_provider_nested_refs_atomically -q` passed 144 checks in 2.70 seconds. Focused Ruff and mypy passed; `git diff --check` and `.venv/bin/python -m pneuma_lab.status --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** No S02C-b/c/d implementation or execution occurred. No subprocess environment, provider/model/network/external call, credential use, spend, candidate or prefix-index publication, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0132 — T5-S02C-a exact DL-139 field and late-status correction

- **Exact correction and observed RED:** Re-review of `d9d225dcbaaf7b5b08e8904fd0fa6ee85717e415` found two bounded transcription errors. The DL-139 execution records require exact fields `grade_evidence_ref` and `verifier_evidence_ref`, without the added `raw_` aliases. Also, DL-140 deadline precedence permits `TIMEOUT_LATE_RESPONSE` as the final completion claim for either an injected transport failure or an injected parser failure. Focused REDs rejected both exact constructor/schema field names and both late-response injection cases while retaining rejection of nominal `COMPLETED` targets.
- **Repair:** Renamed the frozen/slotted record fields, compact canonical codec keys/loaders, schema definitions, and tests to the exact DL-139 names with no compatibility aliases. Added `TIMEOUT_LATE_RESPONSE` to both immutable provider failure-stage completion sets; the transport set otherwise remains timeout-no-response/provider/infrastructure error, and the parser set otherwise remains malformed response. A nominal completed row still satisfies neither stage.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_controller.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_artifacts.py::test_t5_s02a_study_seal_copies_v2_provider_nested_refs_atomically -q` passed 144 checks. Focused Ruff and mypy passed; `git diff --check` and `.venv/bin/python -m pneuma_lab.status --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** No other contract or behavior changed. No S02C-b/c/d implementation or execution, subprocess environment, provider/model/network/external call, credential use, spend, publication, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0133 — T5-S02C-a reader alias, simulator quota, and cleanup correction

- **Hostile rejection and observed RED:** Exact-SHA quality review of `7ebe62c5f794316f196931af6857f1c37cde7354` found three remaining fail-open seams. `AuthorityRefReader` admitted copied-authority roles under controller/scientific/operational/wrong namespaces and did not bind one path or physical inode to one exact ref across reads. Snapshot validation checked primary quota arithmetic but accepted arbitrary simulator remaining quotas. `StableSourceProvenance` let setup/read/drift/body failures be masked by one cleanup group. Focused REDs reproduced controller-path admission, same-path clock/watchdog aliasing, hardlink aliasing, missing simulator validation, and loss of primary `BaseException` under setup/read/drift/body plus injected close failures.
- **Reader correction:** Copied-authority reads are confined to the live `sources/` namespace; controller, scientific-parent, operational, and other namespace paths reject before file open. One reader lifetime now binds exact relative path and `(st_dev, st_ino)` identities to one `ArtifactRef`; exact repeat is cached/idempotent, while role/ref/path and hardlink aliases reject across separate closure calls. Recursive task/program verification shares one visited set, while reader-lifetime bindings remain authoritative across graph verification. Scientific-parent loading no longer routes through the authority reader; this is the bounded class-boundary repair, not full DL-141 heterogeneous traversal.
- **Simulator quota correction:** `FrozenPrefixReceipt.validate_snapshot_bytes` now requires externally reconstructed `simulator_caps` and `observed_simulator_turns`; neither comes from snapshot self-attestation. Null caps/turns/remaining quotas couple exactly to simulator-free authority. Otherwise turns are an exact nonnegative integer no greater than dispatched simulator model calls, and aggregate generated-token/model-call/turn remaining quotas equal `max(0, cap - used)`, including overshoot-to-zero. Quiescent per-call ceilings remain unchanged. The approved snapshot/receipt field lists remain unchanged; later S02D must reconstruct turn usage from freshly loaded attempt/parser evidence before validation.
- **Provenance cleanup correction:** Constructor and context exit now attempt every held descriptor close and raise one `ExceptionGroup` or `BaseExceptionGroup` containing the primary failure first followed by every cleanup failure. Setup/open, initial read, stable-read drift, ordinary context-body failure, and `BaseException` are preserved rather than masked or left only in exception chaining. Cooperative-local threat wording and provenance scope are unchanged.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_authority_refs.py tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller.py tests/resampling_null/test_artifacts.py::test_t5_s02a_study_seal_copies_v2_provider_nested_refs_atomically -q` passed 113 checks in 2.53 seconds. Focused Ruff and mypy passed; `git diff --check` and `.venv/bin/python -m pneuma_lab.status --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** No full DL-141 traversal and no S02C-b/c/d implementation or execution occurred. No subprocess environment, provider/model/network/external call, credential use, spend, publication, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0134 — T5-S02C-a scientific-loader and discrete-cap correction

- **Hostile rejection and observed RED:** Exact-SHA review of `1c6393642583691cb5ccbfa99cdaab48e52bc84c` found two remaining fail-open seams. The scientific-parent loader verified bytes and record kind but did not bind the expected kind to its one canonical role and live top-level path, so valid scientific bytes could be relabeled as `clock_source` or loaded through copied-authority, controller-artifact, or operational namespaces. Prefix snapshot validation also clamped every remaining dimension to zero, allowing primary model/tool calls and simulator model calls/turns to exceed their discrete maxima. The focused RED reported seven failures across those counterexamples.
- **Scientific-loader correction:** `load_scientific_parent` now derives the unique expected role from the immutable `SCIENTIFIC_PARENT_KIND` registry, requires exact `application/json`, and binds the two live classes to exact top-level paths: `resampling_prefix_schedule -> prefix-schedule.json` and `study_manifest -> study-manifest.json`. Cross-role and `sources/`, `controller-artifacts/`, `operational/`, or any other path substitution rejects before bytes are read. Existing execution-authority schedule and manifest loads continue through this boundary.
- **Discrete-cap correction:** Snapshot validation now rejects primary model calls above the prefix model-call cap, primary tool calls above the prefix tool-call cap, simulator model calls above the aggregate model-call cap, and observed simulator turns above either dispatched simulator model calls or the aggregate turn cap. Equality remains valid. Primary generated-token/wall-clock overshoot and simulator generated-token overshoot remain authorized and clamp remaining quota to zero; per-call simulator ceilings remain unchanged.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_controller.py tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_artifacts.py::test_t5_s02a_study_seal_copies_v2_provider_nested_refs_atomically -q` passed 128 checks in 2.48 seconds. Focused Ruff and mypy passed.
- **Boundary/non-claims:** No S02C-b/c/d implementation or execution occurred. No subprocess environment, provider/model/network/external call, credential use, spend, publication, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred. The untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0135 — final independent T5-S02C-a review receipt

- **Exact-SHA verdicts:** The independent specification reviewer and a separate hostile code-quality reviewer approved exact implementation SHA `f86c3418b5b1af42a7ed040b3f65a9c5821f3512` with no critical or important finding. The spec reviewer reconfirmed every earlier restore-contract, role/media, program, evidence-field, failure-binding, scientific-loader, and cap-semantics correction. The hostile reviewer independently reconfirmed create-exclusive CAS reuse and cleanup ownership, immutable registry and loader-class boundaries, path/inode alias rejection, strict codecs and ancestry, external simulator-quota authority, stable-source primary-plus-cleanup aggregation, and absence of execution or publication overbuild.
- **Independent and root behavior:** The hostile reviewer reproduced 156 focused checks and the spec reviewer reproduced 146. Fresh root verification ran `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_authority_refs.py tests/resampling_null/test_evidence_primitives.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_controller.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_prefix_receipt_schema_v01.py tests/resampling_null/test_artifacts.py::test_t5_s02a_study_seal_copies_v2_provider_nested_refs_atomically -q`; GREEN, exit 0, 163 passed in 2.82 seconds.
- **Fresh root static/status:** Ruff lint passed over every changed S02C-a source and test module. Project status and the complete `b4c186a..f86c341` whitespace check passed. Approved plan SHA-256 remained `ead8a1b1000b3ca8c50df25bc8519ebebd5d8a29fe28429dae55d696415f535e`; approved design SHA-256 remained `cabcf98402b9b74411ba5667e18902c3ce71f4c57a52027222c661f6d4638c98`. The untracked `raw_root_placeholder` remained untouched.
- **Release decision:** T5-S02C-a is complete for closed execution/program/raw/restore/evidence contracts, implementation-source provenance, authoritative role/media and loader-class primitives, verified idempotent controller CAS reuse, exact candidate codec, synthetic-only authority projection, and primary/simulator cap/terminal arithmetic. S02C-b remains the next implementation gate for subprocess-backed initial restore and OS identities.
- **Boundary/non-claims:** No `run_prefix`, subprocess environment, provider/simulator/tool loop, grade/verifier execution, candidate return, recursive heterogeneous S02C graph traversal, prefix-index publication, provider/model/network/external call, credential use, spend, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0136 — T5-S02C-b subprocess initial-restore implementation

- **Authority and observed RED:** Implemented only the approved DL-139--DL-141 S02C-b boundary on exact base `6ef1f1c864b4d55cb6a47d24e6f296c09673e386`. The first focused collection failed because the subprocess environment module did not exist. Subsequent REDs rejected unbound task/program bytes, an unregistered environment or tokenizer descriptor, and the absence of the exact internal live-session opener. No caller fixture, store, codec, PID, root identity, or task script seam was added.
- **Subprocess and identity closure:** Added one exact final synthetic factory, byte tokenizer, controller-owned pipe pair, closed environment handle, and isolated worker command. The controller creates each root by bounded create-exclusive suffix search beneath held no-follow run/workspace dirfds, treats every existing directory or symlink name as stale without opening or mutating it, directly retains the real `Popen`, runs it from the held writable root with an empty environment, and derives the receipt PID plus root `(st_dev, st_ino)` itself. Factory binding accepts only the controller's exact `Popen`, IPC value, root fd, and ordinal; it has no PID/root/identity parameter.
- **Restore qualification:** The live subprocess starts from sealed task/program bytes, snapshots canonical state, and a separately spawned process/root starts fresh, restores those exact bytes, then resnapshots. The controller compares full snapshot bytes, visible bytes, tokenizer-derived IDs, ordered branch and terminal queues, terminal state, and failure kind; it independently queries terminal/failure state from both handles. It stores the snapshot, visible context, token IDs, and exact canonical `InitialRestoreQualificationReceipt` through `ControllerArtifactStore`, performs final object/PID/root/name/liveness checks, and rechecks both held implementation-source provenances after last use.
- **Lifecycle and hostile cases:** The internal live-session opener retains both handles, processes, IPC resources, root fds, and source fds for later S02C slices. The bounded qualification transaction proves success and failure teardown: every handle and IPC endpoint is attempted, each live child gets terminate/wait with closed kill/wait escalation, each still-held root and name must retain the receipt identity before any cleanup, and primary plus all cleanup `BaseException` values are preserved. Tests cover stale directory and symlink skipping, suffix exhaustion, workspace symlink rejection, factory anti-spoof shape, exact restore byte/visible/token/queue/terminal/failure drift, object/PID/root aliasing, premature process death, and injected cleanup `KeyboardInterrupt`.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py -q` passed 42 checks in 0.68 seconds. Focused mypy and final focused Ruff passed for the new controller surface; `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is deterministic local synthetic fixture execution and software verification only. No public `run_prefix`, provider/simulator/tool loop, grade/verifier transaction, candidate return, heterogeneous graph traversal, prefix-index publication, provider/model/network/external call, credential use, spend, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0137 — T5-S02C-b provenance and lifecycle rejection repair

- **Exact-SHA rejection and observed RED:** Review of `0bd382f8c566a1ddb1e7cce99bbf54646914aa9b` found four fail-open lifecycle seams: the executed worker lived in a second source file not bound by the environment descriptor; root ownership began only after open, leaking a just-created root and blindly removing names after close; IPC construction leaked descriptors when its second pipe, either duplicate, or either `fdopen` failed; and factory program/task/digest state was publicly assignable. Adjacent review also found incomplete terminate/wait/kill error sequencing. The focused RED produced 10 failures across source binding, root open/replacement/nested-content cleanup, and all five IPC acquisition points; a later RED reproduced a `poll()` cleanup failure aborting the remaining process policy.
- **Single-source execution repair:** Deleted the standalone worker module. The exact reviewed `synthetic_environment.py` now contains and executes its worker entry under `--synthetic-worker`; the factory command pins the descriptor's source SHA-256 and the child hashes the actual executed file before accepting IPC. The same held `StableSourceProvenance` rereads that file after last fixture use. There is still one environment descriptor and one source ref—no new purpose, source authority, or plugin seam.
- **Transactional root and IPC repair:** Root ownership now begins immediately after create-exclusive `mkdirat`. The controller records the named inode before open, fsyncs the parent, binds a held no-follow fd, and verifies named/held identity. Every later failure recursively clears child-created contents only through a verified held fd, removes the exact still-bound name before closing the fd, and fsyncs the parent. Open-before-fd failure removes an empty name only after reproducing its newly created identity; replacement or missing-identity cases preserve the replacement and emit explicit residual uncertainty. IPC creation now tracks both pipe pairs, both duplicates, and both streams from acquisition; every `BaseException` attempts all owned closes once and preserves the primary plus cleanup errors.
- **Frozen factory and cleanup repair:** `SyntheticEnvironmentFactory` is final, frozen, slotted, private-state-only, and revalidates task/program/source seals at command and bind. Normal reassignment rejects and one-field `object.__setattr__` drift is detected under the cooperative-local threat model. Success and spawn-failure cleanup share a closed process policy: observe, terminate, wait, and only on timeout kill then wait; terminate, kill, poll, and wait failures are retained while every permitted next step and root cleanup is still attempted. Handle/IPC failures cannot skip process/root/source cleanup.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py -q` passed 55 checks in 0.97 seconds. Focused Ruff and mypy passed; `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** The repair changes only S02C-b local synthetic provenance and resource ownership. No provider/simulator/tool loop, grade/verifier transaction, public `run_prefix`, candidate return, graph traversal, prefix publication, provider/model/network/external call, credential use, spend, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0138 — T5-S02C-b directory-fd ownership correction

- **Bounded rejection and observed RED:** Review of `bedfb66315c3fc726d7322dac6ae0a38197bbc6c` found that `_open_root` and `_open_workspace` leaked an acquired fd when `fstat` or validation raised, while `_EnvironmentFleet.__init__` could let a root-fd close failure mask the workspace primary. It also found that IPC creation removed the controller-side raw write/read fd from its ownership ledger before `close` succeeded. Focused REDs reproduced both directory-fd leaks, primary/cleanup ordering loss, fleet masking, and a close-after-effect IPC uncertainty with an untracked cleanup obligation.
- **Ownership repair:** Each directory opener now enters a closed transaction immediately after `open`: every subsequent `fstat`, identity, type-validation, or other `BaseException` attempts the one owned close; a close failure yields one `BaseExceptionGroup` with the primary first and cleanup second. Fleet workspace setup applies the same ordering to its already-held root fd. IPC raw descriptors remain in the tracked set until `os.close` returns successfully; a close that raises after taking effect stays explicit, receives one bounded cleanup attempt, and preserves both the primary uncertainty and cleanup result without a silent fd leak.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py -q` passed 60 checks in 0.93 seconds. Focused Ruff and mypy passed; `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This correction changes only root/workspace/IPC descriptor ownership and failure aggregation. The exact process terminate/wait/kill policy is unchanged. No S02C-c/d behavior, provider/simulator/tool loop, grade/verifier transaction, public `run_prefix`, candidate return, traversal, publication, external action, spend, experiment, result, or claim was added.

### EJ-20260729-0139 — T5-S02C-b POSIX uncertain-close correction

- **Tiny correctness rejection and observed RED:** Review of `6f4baa7ad717fa6d43d0dbd46832912c7e79db91` identified a POSIX close-semantics error in EJ-0138's IPC repair. Keeping a numeric fd in the raw ownership set until `close` returns permits a raised close-after-effect to be retried after the kernel has already recycled that number. Parameterized REDs forced immediate descriptor-number reuse at each controller-side parent raw close and proved the cleanup path closed the unrelated replacement.
- **Once-only repair and adjacent audit:** IPC creation now removes each controller-side raw write/read descriptor from the safely owned set immediately before its one `os.close` attempt. A close `BaseException` remains the primary uncertainty, every other stream/raw fd is still closed exactly once, and the uncertain numeric fd is never retried. The regression keeps the immediately reused replacement open through cleanup for both parent raw closes. An audit of every other `os.close` site in the new synthetic-environment module confirmed the same relinquish-before-attempt or otherwise once-only local ownership pattern; no process-policy or wider behavior changed.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py -q` passed 61 checks in 0.90 seconds. Focused Ruff and mypy passed; `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This correction is limited to two IPC raw-fd close attempts and their regression. No S02C-c/d behavior, provider/simulator/tool loop, grade/verifier transaction, public entry, candidate, traversal, publication, external action, spend, experiment, result, or claim was added.

### EJ-20260729-0140 — hostile S02C-b authority, closure, framing, and reap repair

- **Exact-base rejection and observed RED:** Hostile review of exact base `1ba1e7030ad344823eed578c71483cf83ceca9ce` rejected five important fail-open seams. Qualification authority accepted noncanonical role media/paths and could be mutated after construction; source provenance could close before its final reread and leaked on pre-fleet factory/tokenizer failure; snapshot equality omitted independently queried simulator context, program binding, empty-turn state, and mutation/verifier flags; newline IPC used unbounded blocking stream operations and permissive JSON; and process cleanup treated nonzero pre-exit and uncertain wait/poll state as clean enough to remove the writable root. Focused REDs covered authority ref and post-construction drift, pre-fleet lifecycle failure, embedded/query snapshot disagreement, duplicate/nonfinite/noncanonical/truncated/oversized/stalled IPC, partial/zero writes, nonzero exit, wait error with a live process, and uncertain reap with a populated root.
- **Authority and lifecycle repair:** `InitialQualificationAuthority` now validates every canonical registry media/path class and seals the complete refs, descriptors, and task/program byte identities. The seal is revalidated at qualification entry, immediately before artifact creation, and immediately before returning a retained session. Every partial or retained lifecycle now closes the fleet first, rereads every held source second, and closes every source third, aggregating the primary and all cleanup `BaseException` values. This corrects EJ-0136/0137's overly broad wording: a retained live session cannot claim a final post-use source reread until its workers have actually stopped; bounded qualification obtains that final verification during `result.close()`.
- **Snapshot and IPC closure:** Qualification now strictly decodes canonical snapshot JSON with duplicate, nonfinite, UTF-8, base64, shape, and byte checks; it binds the exact program digest, embedded visible and simulator contexts, empty turn history, both ordered queues, terminal/failure state, and independently queried mutation/verifier ineligibility across live and fresh-restored subprocesses. Controller and worker IPC now use one exact newline frame with a 1 MiB payload cap, monotonic two-second read/write deadlines, nonblocking descriptors, partial-write progress, strict compact canonical JSON, closed request operation shapes, and rejection of missing, multiple, trailing, duplicate-key, nonfinite, noncanonical, oversized, stalled, or dead-peer frames.
- **Process/root closure:** Cleanup reports an already exited nonzero child as a reaped failure. After terminate, a non-timeout wait error is repolled: a confirmed-live child proceeds through kill/final-wait, while poll uncertainty is explicit and marks the child unreaped. A failed final wait likewise remains unreaped. Root cleanup is permitted only after confirmed reap; otherwise the held root fd is closed but the populated owned root is preserved with a typed residual instead of risking deletion under a possibly live child.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_initial_restore.py -q` passed 57 checks in 1.12 seconds. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py -q` passed 86 checks in 1.15 seconds. Focused Ruff passed, and focused mypy reported no issues in `synthetic_environment.py`. `.venv/bin/python -m pneuma_lab.status --check` and `git diff --check` passed. Source SHA-256 is `87e19f5131bafa350e9c2345b7acf5ebc34dac717f2591ad12d70877f2f3ae18`; focused-test SHA-256 is `f6a4f6785f80abf5ecc8362c65005e5680ce88b1ccc8eceed5f20b1d1a7ce608`. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This repair remains private deterministic local S02C-b qualification and software verification. It adds no S02C-c/d behavior, public `run_prefix`, provider/simulator/tool loop, grade/verifier transaction, candidate return, graph traversal, prefix publication, external action, credentials, spend, scientific experiment, empirical result, causal result, or promoted claim.

### EJ-20260729-0141 — retained-worker idle-wait correction

- **Bounded rejection and observed RED:** Review of exact SHA `d1072402cc8b9454e7bf0bed295dbbc5450c8a21` found that EJ-0140 applied the two-second deadline to the worker's top-level wait for its next controller request. A valid retained session left idle for 2.1 seconds caused the worker to emit an unsolicited timeout error, poisoning the next snapshot exchange. The retained-session regression failed with `RecordValidationError: synthetic environment rejected operation: TimeoutError: IPC frame read timed out`; a direct clean-EOF regression separately failed because the frame reader did not accept an unbounded wait.
- **Minimal repair:** `_read_frame_fd` now accepts `timeout_seconds=None`. Only the worker's top-level next-request wait uses it, blocking in `select`/`read` for arbitrary controller idle while retaining the exact frame-size and strict-decoding bounds. Clean EOF with no partial frame still returns normally. Controller request writes, controller response reads, and worker reply writes remain deadline-bounded at exactly two seconds; no idle timeout is caught or emitted.
- **Fresh bounded gate:** The two corrective regressions passed in 2.56 seconds. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py -q` passed 88 checks in 3.45 seconds. Focused Ruff passed, and focused mypy reported no issues in `synthetic_environment.py`. Source SHA-256 is `64b7c34d7fef64e9e12c3b2c6c4f742c2d39dd658a6c14ab7a6fba5b6259fa09`; focused-test SHA-256 is `222173453ed784877ae998371c16f1ff2593b81fa8c2b5651b914fd1ea001a70`.
- **Boundary/non-claims:** This correction changes only idle waiting between controller requests. It adds no S02C-c/d behavior, external action, spend, experiment, result, or claim. The untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0142 — final independent T5-S02C-b review receipt

- **Exact-SHA verdicts:** The independent specification reviewer and a separate hostile code-quality reviewer approved exact implementation SHA `fb68d3c309ab99331bd2a17ae8a72e83e559d0f5` with no critical or important finding. They independently reconfirmed canonical sealed ancestry, binding of the actual executed worker source, exact initial snapshot/fresh-restore/state/identity evidence, controller-owned Popen/IPC/root identities, retained-session liveness and idle behavior, post-worker source verification, strict deadline-bounded in-flight framing, transactional and once-only kernel-resource ownership, reap-gated root cleanup, and absence of S02C-c/d overbuild.
- **Independent and root behavior:** The hostile reviewer reproduced 59 focused checks including a retained session surviving more than two seconds idle; the spec reviewer reproduced the 88-check authority-inclusive gate. Fresh root verification ran `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py -q`; GREEN, exit 0, 88 passed in 3.55 seconds.
- **Fresh root static/status:** Ruff lint passed over the new S02C-b source and focused test module. Project status and the complete `6ef1f1c..fb68d3c` whitespace check passed. Approved plan SHA-256 remained `ead8a1b1000b3ca8c50df25bc8519ebebd5d8a29fe28429dae55d696415f535e`; approved design SHA-256 remained `cabcf98402b9b74411ba5667e18902c3ce71f4c57a52027222c661f6d4638c98`. The untracked `raw_root_placeholder` remained untouched.
- **Release decision:** T5-S02C-b is complete for the private subprocess-backed synthetic environment, controller-owned IPC/Popen/root lifecycle, exact initial restore qualification, physical process/root identities, retained live-session handoff, and fail-closed cleanup aggregation. S02C-c remains the next gate for the controller-owned provider/simulator/tool loop and zero-cost settlement.
- **Boundary/non-claims:** No public `run_prefix`, provider/model/network call, simulator or tool loop, grade/verifier clone transaction, candidate return, heterogeneous graph traversal, prefix-index publication, credential use, spend, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0143 — T5-S02C-c controller-owned synthetic prefix loop

- **Authority and observed REDs:** Implemented only the approved DL-139--DL-141 S02C-c boundary on exact base `38cc9add17b259a1735e08d3326c6144433b8b14`. The first focused collection failed because the private loop module did not exist. Subsequent REDs reproduced missing subprocess append/tool/terminate operations, every listed and excluded provider truth-table row, deadline equality and retained late bytes, misleading completion claims, descriptor drift, request-token drift, transcript-versus-environment actor disagreement, inclusive discrete-cap boundaries, and lost adverse pending queues.
- **Closed controller loop:** Added one private `_open_prefix_loop(*, run_root, authority)` seam over exact `PrefixExecutionAuthority`; no caller fixture, codec, store, parser, renderer, meter, script, or plugin is accepted. A closed descriptor registry constructs exact final local subject/simulator actors, byte tokenizer, renderer, parser, named-trace meter, provider-event codec, settlement codec, and deferred grade/verifier codecs from one canonical program at position zero. The subprocess handle now exposes distinct role-safe append operations, raw-only tool execution, independent state queries, simulator context, and exact adverse termination; snapshots persist all resulting turn, queue, mutation, eligibility, terminal, and failure state.
- **Evidence and precedence:** The controller derives the actor from environment context, verifies canonical request bytes/digest/input IDs before one dispatch, reconstructs raw response tokens and parser status, applies the complete deadline/response/transport/parser table before mutation, and retains late bytes. Calls count at dispatch, typed turns only after parser success, generated bytes by controller tokenization, and tools only after a validated result. Explicit failure/terminal/wall/token outcomes precede cumulative eligible mutation and tool-four triggers; model/turn/tool equality blocks only the next action, so the fourth completed tool remains a valid trigger. Every attempt has an intent, canonical event, terminal attempt, exact final zero-cost settlement, and attempt-bound closure; adverse termination preserves the exact known queue.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_prefix_loop.py tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_evidence_primitives.py -q` passed 159 checks in 4.43 seconds after final formatting. Focused Ruff and formatter checks passed, focused mypy reported no issues in the two changed source modules, `.venv/bin/python -m pneuma_lab.status --check` passed, and `git diff --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** The retained private result is intentionally unfinished S02C-c state for S02C-d. No final composite snapshot, grade or verifier clone transaction, candidate wrapper or return, heterogeneous recursive traversal, public `run_prefix`, prefix-index publication, provider/model/network/external call, credential use, spend, assignment, packet, branch, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0144 — T5-S02C-c exact-SHA specification-rejection repair

- **Exact-SHA rejection and observed REDs:** Specification review of `54a3b82ac1be6b380c1f3d85a3159ec30dde8771` found four important authority defects. Descriptor refs were treated as local-source metadata without opening their copied authority files; the provider actor accepted a controller-supplied transcript position and retained caller-owned parsed state; tool observations were matched by ID instead of consumed in order and were not compared field-for-field with independent environment queries; and discrete model/turn caps were evaluated before the next action's wall deadline. Focused REDs deleted a copied implementation source, inspected the forbidden actor argument, reversed the tool-observation array, and reproduced deadline/model-cap equality choosing the wrong failure.
- **Source and actor repair:** Every descriptor now opens and holds two no-follow stable provenances before fixture use: its copied `sources/` authority file and its registered local implementation file. Exact bytes are compared, both fds are retained through the private result, and failure/success cleanup rereads and closes every source while preserving all errors. The exact provider `invoke` surface no longer accepts transcript position. Each final actor copies canonical program bytes and payload bytes into immutable internal state, reparses and seals its own program digest, owns one role-local zero-position cursor, revalidates the seal on invocation, and advances only after producing one closed observation.
- **Tool and precedence repair:** The controller consumes tool observations through one monotonic position, checks the next call before mutation, compares raw result bytes and every mutation/eligibility/terminal/failure field against separately queried handle state, samples completion time, and only then writes tool evidence. Missing, extra, or reordered observations reject. Pre-provider order is now observed failure/terminal, wall deadline, token allowance, then model/turn allowance; tool order remains failure/terminal, wall, token, tool allowance before execution and explicit failure, terminal, wall/token overshoot before either trigger after completion. Deadline equality on the next pending action therefore yields `TIMEOUT`, not a discrete-cap classification.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_prefix_loop.py tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_evidence_primitives.py -q` passed 163 checks in 4.43 seconds. Focused Ruff and formatter checks passed, and focused mypy reported no issues in the two S02C source modules. The approved plan/design authority remains unchanged.
- **Boundary/non-claims:** This is a local deterministic S02C-c correction only. It adds no S02C-d composite snapshot, grade/verifier clone, candidate wrapper or return, recursive traversal, public `run_prefix`, prefix publication, provider/model/network/external call, credential use, spend, experiment, result, or claim. The untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0145 — token-equality and provider-derived-state seal correction

- **Exact-SHA rejection and observed REDs:** Follow-up specification review of exact SHA `fcd1bd28b6a4bd7907dc6a105e7f9e33e5b01c63` found two important regressions. The tool pre-action check treated generated-token equality as exhaustion even though tools consume no generated tokens, preventing the existing four-tool fixture from reaching `FOURTH_TOOL_CALL` when both prefix and subject-contract token caps exactly equaled the completed response count. The provider actor's seal also omitted its derived role rows and role-local cursor, so `object.__setattr__` could substitute a typed response row while sealed program bytes and their digest still verified. The two focused REDs failed respectively with a sealed-trigger mismatch after premature token termination and with no exception before the substituted observation.
- **Correction and adjacent audit:** Queued tool admission now permits exact generated-token equality and defensively rejects only aggregate overshoot against the minimum of the prefix and subject-model aggregate caps. Per-call and aggregate overshoot remain checked immediately after provider completion; equality still blocks the next provider dispatch, and discrete model/turn/tool equality semantics are unchanged. The actor seal now includes the exact derived role rows and cursor, reparses the sealed program bytes at every invocation, compares the exact role-local rows, validates the cursor and sealed flag before observation, selects the row from the reparsed program, and advances cursor plus seal together only after constructing a valid observation.
- **Fresh bounded gate:** The two corrective regressions passed together. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_prefix_loop.py tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_evidence_primitives.py -q` passed 165 checks in 4.62 seconds. Focused Ruff lint and formatter checks passed, and focused mypy reported no issues in the two audited S02C source modules.
- **Boundary/non-claims:** This is a deterministic local S02C-c correction only. It adds no S02C-d composite snapshot, grade/verifier clone, candidate wrapper or return, recursive traversal, public `run_prefix`, prefix publication, provider/model/network/external call, credential use, spend, experiment, empirical result, causal result, or claim promotion. The untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0146 — transcript, registry, and meter authority closure

- **Exact-SHA rejection and observed REDs:** Hostile quality review of exact SHA `809ff75288bc16aed5d33cd16867c667e4509e6b` found three important fail-open surfaces. A branch or early terminal could return while global provider rows and role-local actor rows remained unconsumed, including a declared but never reached provider-failure target. The descriptor registry's outer proxy retained mutable inner dictionaries, and duplicate purposes were silently collapsed before comparison. The meter accepted a separately supplied trace, discarded its program bytes, and left its digest, trace, cursor, and last value mutable. Six focused REDs reproduced an extra ordinary row, an extra declared failure row, hidden primary rows across role interleaving, inner-registry mutation plus duplicate-purpose collapse, independent meter-trace injection, and meter derived-state drift.
- **Authority closure:** Successful loop completion now requires exact global provider-transcript consumption and calls a private exhaustion check on every instantiated actor; each actor reparses and seal-verifies its role-local rows and cursor before proving exhaustion. The registry is deeply immutable and duplicate purposes reject before mapping construction. The meter constructor accepts canonical program bytes only, reparses the exact clock trace internally, retains bytes and digest, starts at zero, seals immutable and cursor-derived state, and verifies canonical bytes, digest, trace, cursor, previous value, and sealed flag before every read or private exhaustion check. Each successful read advances cursor, previous value, and seal as one controlled transition.
- **Fresh bounded gate:** The six corrective regressions passed together. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_prefix_loop.py tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_evidence_primitives.py -q` passed 170 checks in 5.12 seconds. Focused Ruff lint and formatter checks passed, and focused mypy reported no issues in the two audited S02C source modules.
- **Boundary/non-claims:** This remains deterministic private S02C-c authority hardening. It adds no S02C-d composite snapshot, grade/verifier clone transaction, candidate wrapper or return, recursive traversal, public `run_prefix`, prefix publication, provider/model/network/external call, credential use, spend, experiment, empirical result, causal result, or claim promotion. The untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0147 — final independent T5-S02C-c review receipt

- **Exact-SHA verdicts:** The independent specification reviewer and a separate hostile code-quality reviewer approved exact implementation SHA `5241bc634a84d1f234753eca1df6a226858edd4a` with no critical or important finding. Across the rejected predecessor SHAs and the approved repair, they directly reproduced and closed missing copied-source reads, a caller-selected provider cursor, unordered and self-certified tool observations, deadline/discrete-cap inversion, token-equality suppression of queued tools, mutable provider-derived rows, unconsumed transcript and injected-failure rows, shallow/duplicate-collapsing descriptor authority, and a mutable clock detached from canonical program bytes.
- **Independent and root behavior:** The final hostile re-review passed its eight-case repair matrix and the complete 170-check bounded S02C gate, including cleanup after adversarial transcript rejection. Fresh root verification ran `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_prefix_loop.py tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_evidence_primitives.py -q`; GREEN, exit 0, 170 passed in 5.22 seconds.
- **Fresh root static/status:** Focused Ruff lint passed over both S02C source modules and the prefix-loop test module. Project status and the complete `38cc9ad..5241bc6` whitespace check passed. Approved plan SHA-256 remained `ead8a1b1000b3ca8c50df25bc8519ebebd5d8a29fe28429dae55d696415f535e`; approved design SHA-256 remained `cabcf98402b9b74411ba5667e18902c3ce71f4c57a52027222c661f6d4638c98`. The untracked `raw_root_placeholder` remained untouched.
- **Release decision:** T5-S02C-c is complete for the private controller-owned subject/simulator/provider/tool loop, exact raw-provider truth derivation, inclusive cap and trigger precedence, ordered independent tool-state evidence, attempt-bound zero-cost settlement, sealed descriptor/provider/meter state, exact program-sequence exhaustion, and retained qualified-session handoff. T5-S02C-d remains the next gate for final snapshot, grade/verifier restores, canonical candidate materialization, fresh recursive reload, and the public local entry point.
- **Boundary/non-claims:** No S02C-d behavior, candidate return, graph publication, provider/model/network call, credential use, spend, assignment, packet, branch execution, training, scientific experiment, empirical result, causal result, or claim promotion occurred.

### EJ-20260729-0148 — T5-S02C-d canonical synthetic candidate

- **Authority and observed REDs:** Implemented only the approved T5-S02C-d boundary on exact base `7c752f0950a627ec9a719acff526d5b15d35fef1`. Focused REDs first reproduced the absent finalizer, then demonstrated that open controller JSON and wrong request/ref roles were accepted, and finally required an explicit natural-versus-adverse no-trigger Y0 rule. Hostile review also found that the executable authority projection could not reproduce the reviewed synthetic descriptor registry; the fixture and provider-authority projection were repaired to bind exact local source revisions and exact nominal/build/grammar/runtime/container identities without weakening registry validation.
- **Candidate and clone closure:** The retained private loop result now transfers its single controller artifact store into finalization and closes it exactly once before fresh reload. Finalization records one canonical composite snapshot, restores independent grade and verifier subprocesses from it, requires exact re-snapshot/state/visible-context/token-ID identity, proves each evidence query read-only, and records four pairwise-distinct process/root identities. The scientific Y0 grade is the natural grade unless an adverse no-trigger termination requires the forced-zero grade. One frozen prefix receipt and one wrapper are materialized, and the sole public keyword-only `run_prefix(*, run_root, schedule_ref, task_id) -> ArtifactRef` entry point returns only that wrapper ref.
- **Fresh graph closure:** A fresh authority load and fresh resolver recursively traverse exactly three artifact classes through a closed role-to-loader registry. Strict controller JSON shapes, exact scientific payload decoding, global logical-path uniqueness, held-fd no-follow physical identity uniqueness, exact retained-store bytes, the explicit five-ref prior-subtransaction allow-set, and exact reachability of every final-store write are all required. Unexpected controller refs, malformed/wrong-role records, retained alternate bytes, hardlink aliases, and unreachable writes fail closed.
- **Fresh bounded gates and correction:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_prefix_loop.py tests/resampling_null/test_s02c_candidate.py tests/resampling_null/test_controller_artifacts.py -q` passed 135 checks in 6.90 seconds. The first combined static run exposed three mypy local-variable inference errors in the new grade/verifier worker branch; explicit candidate typing and a distinct evidence-match name corrected them. The repeated bounded gate passed Ruff lint and format for all eight changed code/test files, focused mypy for five source modules, project-status coherence, and `git diff --check`. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is deterministic local `synthetic_validation` candidate machinery only. No prefix-index publication, S02D work, provider/model/network/external call, credential use, spend, assignment, packet, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion occurred.

### EJ-20260729-0149 — T5-S02C-d semantic reconstruction repair

- **Exact-SHA rejection and observed REDs:** Final specification review rejected exact SHA `0ba19f3d7d2a6dc4995edf2d13ea15fbcc574fa0` because fresh traversal proved canonical shapes and bytes but discarded runtime semantics. Strict REDs showed that it accepted `attempt_refs: [false]`, `intent_refs: ["not-a-ref"]`, a nonzero provider-event cost and boolean response digest, boolean/integer/list settlement digests, and a subject attestation with boolean program digest, numeric kind, and `stateless: false`. A separate RED reproduced absent cross-edge reconciliation for intent, event, settlement, and tool records; authority-leaf REDs reproduced invalid request base64/actor and a non-text tool-result call ID.
- **Typed reconstruction:** Added reusable exact evidence loaders for dispatch intents, attempts, the ordered attempt ledger and refs, controller provider events, final settlements, exact-zero cost closure, tool boundaries/calls, and subject/simulator/runtime/container attestations. Fresh traversal now retains typed records and reconciles the ordered ledger and individual artifacts to the already-built attempt-bound or zero-attempt closure, including request/input/model/response ancestry, status/tokens, sealed completion time, provider event identity and exact-zero cost, every settlement digest edge, one-to-one attempt/settlement coverage with no extras or duplicates, total cost, and exact tool call/result/boundary semantics.
- **Authority and attestation closure:** Request and tool-result authority leaves use reusable strict decoders; responses pass the existing response parser, raw events pass `_decode_raw_event`, and grade/verifier leaves pass their existing codecs. Every traversed synthetic program, including foreign-task manifest programs, owns complete/no-extra typed leaf coverage; the selected authority program must exactly equal the retained executed program. Subject/simulator attestations bind exact kind/schema/program digest/stateless authority, and runtime/container attestations bind the reviewed environment source, runtime ID, and container identity.
- **Fresh bounded gates and corrections:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_contracts.py tests/resampling_null/test_s02c_initial_restore.py tests/resampling_null/test_s02c_prefix_loop.py tests/resampling_null/test_s02c_candidate.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_evidence_primitives.py -q` passed 185 checks in 7.61 seconds. Static cleanup removed four unused test imports, applied focused formatting, and corrected one mypy loop-variable inference collision. The final bounded static gate passed Ruff lint/format for four changed code/test files, focused mypy for three source modules, project-status coherence, and `git diff --check`. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This repair only closes T5-S02C-d local semantic reload. It does not add S02D, prefix-index publication, provider/model/network/external calls, credential use, spend, assignment, packet, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion.

### EJ-20260729-0150 — T5-S02C-d hostile authority rejection

- **Exact-SHA verdict:** Specification re-review approved exact SHA `a4fea947c47d5fa5e8d29610bab7840c3f01abd6`, but a separate hostile quality review rejected it with two important and two minor findings. Most non-synthetic authority JSON still fell through to canonical JSON plus generic ref walking; raw grade/verifier decoding admitted Boolean substitution, omitted/extra values, and program-filled evidence; physical alias identity came from a second reopen; and the identity reader did not causally aggregate close failure with an active traversal failure.
- **Counterexample:** A canonical open foreign task object could traverse without its exact task validator. `{"success": false}` could certify a zero-success program with any program-supplied partial reward, and `{"finding_count": false}` compared equal to integer zero. Set coverage could collapse one shared incomplete evidence ref across incompatible programs.
- **Decision:** Implementation stopped fail-closed. No attempt was made to invent role semantics in Python or weaken DL-141's no-opaque-leaf requirement.
- **Boundary/non-claims:** No source, fixture, schema, S02D, publication, provider/model/network/external action, credential use, spend, experiment, result, or claim was produced from the rejected commit. The untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0151 — DL-142 exact authority-leaf repair

- **Authority defect:** Inventory confirmed exact validators for task registry, provider lane plan, task input/program, task/environment/call/parser/meter contracts, and the seven synthetic execution leaves. The committed authority had no semantic grammar beyond canonical JSON for tokenizer, prompt template, tool schema, clock source, watchdog source, isolation qualification, or deep authority assets. DL-141 nevertheless prohibited opaque leaves.
- **Authority choice:** Appended DL-142 and amended the plan/design before resuming implementation. The seven roles gain explicit synthetic-only version-1 closed records; source revisions remain explicitly byte-only; grade/verifier bytes must directly carry exact typed values; attribution is occurrence-aware; and verified bytes plus physical identity must come from the same held no-follow descriptor with stable pre/post checks and causal close aggregation. Confirmation cannot reuse the synthetic record kinds.
- **Authority hashes:** Plan SHA-256 is `042d1b6c1d40c213ca5240d667a12934aa6972f526bfa004a6a40f719df97863`; design SHA-256 is `460570329ecb231f3469fc34369f943472e25597f8067fbf73242dac0765edb8`.
- **Boundary/non-claims:** This is docs-only authority repair. No Python, fixture, schema, S02D publication, provider/model/network call, credential use, spend, branch, experiment, empirical result, or claim promotion occurred.

### EJ-20260729-0152 — T5-S02C-d DL-142 authority and bound-read closure

- **Authority and observed REDs:** Resumed only after DL-142 promoted exact synthetic-only grammars under plan SHA-256 `042d1b6c1d40c213ca5240d667a12934aa6972f526bfa004a6a40f719df97863` and design SHA-256 `460570329ecb231f3469fc34369f943472e25597f8067fbf73242dac0765edb8`. Strict REDs first reproduced absent decoders for all seven promoted roles, an absent closed decoder registry, Boolean/missing/extra/integer substitution in direct grade/verifier bytes, a same-byte inode swap between read and named identity proof, and loss of an active traversal failure under an injected reader-close failure.
- **Closed authority decoding:** Added one exact 26-role `AUTHORITY_ASSET_DECODER_BY_ROLE` with no fallback: eleven task/plan/contract roles require fresh proofs from their existing production validators, seven execution leaves invoke their existing exact loaders/codecs, seven DL-142 promoted roles use closed version-1 synthetic-only records, and `source_revision` remains byte-only. Provider validation proves the exact registry/plan refs and every lane and task ref, including foreign task inputs and contracts; traversal then requires each actually visited typed ref to match that proof. Tool-schema validation now composes the promoted decoder. Deep links are exact same-role refs, and migrated synthetic fixtures use only the promoted leaf/link identities.
- **Evidence attribution and physical proof:** Grade and verifier records now decode direct exact closed fields (`int` 0/1, finite exact `float`, exact `bool`, and nonnegative exact `int`) rather than filling values from a program. Grade/verifier reconciliation is program-occurrence aware, so one shared ref is decoded against every owning program and contradictory claims reject. Authority, controller, and scientific loaders now return bytes, digest/count, and `(st_dev, st_ino)` from the same continuously held no-follow descriptor after stable pre/post `fstat` plus named identity checks. Fresh traversal consumes those identities directly; the former reopen-only identity reader was removed. Reader/store/resolver ownership is relinquished before uncertain close, and active traversal plus all cleanup failures are causally aggregated.
- **Hostile regressions:** Added direct rejection coverage for every promoted role's open/wrong-kind/wrong-type forms, the exact 26-role registry, same-role deep links, open foreign task inputs and environment contracts, contradictory shared grade authority, Boolean/missing/extra grade/verifier fields, same-byte inode substitution in all three load classes, and traversal-plus-close failure aggregation in all three graph readers. Synthetic-only execution authority remains gated by the existing exact `schedule_authority == "synthetic_validation"` boundary; no confirmation path invokes these decoders.
- **Fresh bounded gates:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_candidate.py tests/resampling_null/test_s02c_prefix_loop.py tests/resampling_null/test_controller.py tests/resampling_null/test_study_seal_publication.py tests/resampling_null/test_controller_artifacts.py tests/resampling_null/test_authority_refs.py -q` passed 159 checks. Focused Ruff and mypy passed over the changed source surface; `git diff --check`, byte compilation, and `.venv/bin/python -m pneuma_lab.status --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is deterministic local T5-S02C-d repair only. No S02D, prefix-index publication, provider/model/network/external call, credential use, spend, assignment, packet, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion occurred.

### EJ-20260729-0153 — T5-S02C-d acquisition cleanup correction

- **Exact-SHA rejection and observed REDs:** Specification review rejected exact SHA `75ad2ff34d0bcdf690be3c3a1a854d3d4cc9e185` because acquisition cleanup still closed locally or object-owned descriptors before relinquishing ownership and let a close failure replace the primary acquisition failure. Six focused REDs reproduced authority-root `fstat` plus close failure, scientific named-identity plus close failure, controller-root identity plus close failure, store artifact-tree acquisition plus close failure, resolver artifact-tree `OSError` plus close failure, and resolver artifact-tree `KeyboardInterrupt` plus close failure. The store/resolver counterexamples also proved stale descriptor ownership after uncertain close.
- **Bounded correction:** Added one internal primary-first descriptor-cleanup primitive. Authority, scientific, and controller root acquisition now transfer the descriptor to a local cleanup owner, clear the original ownership slot, attempt close exactly once, and raise one `BaseExceptionGroup` containing the acquisition failure followed by the cleanup failure. Controller store and resolver constructors initialize both ownership fields to `None`, clear both before artifact-tree cleanup, and use the same primitive. Resolver artifact-tree acquisition now cleans up for every `BaseException`; an `OSError` retains the existing public `RecordValidationError` wrapper and cause, while non-`OSError` failures retain their exact primary type.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_candidate.py tests/resampling_null/test_controller_artifacts.py -q` passed 63 checks. Focused Ruff and mypy passed over the three changed source modules and two regression modules; `git diff --check` and `.venv/bin/python -m pneuma_lab.status --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** No DL-142 semantics, public signature, S02C execution behavior, S02D, publication, provider/model/network/external call, credential use, spend, experiment, result, or claim changed.

### EJ-20260729-0154 — T5-S02C-d controller acquisition wrapper correction

- **Exact-SHA rejection and observed REDs:** Specification review rejected exact SHA `938603efc032f26a1ef80ad5dac41647d5df7676` because `_bind_root` grouped a raw post-open `OSError` with close failure before Store or Resolver could apply its established public `RecordValidationError` wrapper. Cleanup-success therefore exposed the wrapper while cleanup-failure exposed raw `OSError`. Adjacent hostile review also found `_mkdir_or_open` left its newly opened directory descriptor unowned during `fstat` and directory validation. Focused REDs reproduced both consumers across root-`fstat` cleanup success/failure, artifact-tree `fstat` plus close failure, and not-directory validation plus close failure.
- **Bounded correction:** Store and Resolver now normalize only the primary `_bind_root` error at their consumer boundary. Raw `OSError` becomes the same consumer-specific `RecordValidationError` with the raw failure retained as `__cause__`, including when it is the first member of a cleanup group; existing identity `RecordValidationError` and non-`OSError` `BaseException` types remain unchanged. `_mkdir_or_open` now owns its descriptor transactionally through post-open `fstat` and directory validation, relinquishes before one uncertain close, and preserves primary followed by cleanup failure. Failed constructors retain both descriptor fields as `None`.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_candidate.py tests/resampling_null/test_controller_artifacts.py -q` passed 69 checks. Focused Ruff lint and `ruff format --check` passed for the changed source/test files; focused mypy, `git diff --check`, and `.venv/bin/python -m pneuma_lab.status --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** No DL-142 grammar, public signature, S02C execution behavior, S02D, publication, provider/model/network/external call, credential use, spend, experiment, result, or claim changed.

### EJ-20260729-0155 — T5-S02C-d cumulative format-receipt correction

- **Receipt correction:** Root verification of exact SHA `71384b11274423ddbce4f979e5da0c1c3e8c439e` found that the cumulative five-file S02C-d surface did not satisfy `ruff format --check`: `authority_refs.py`, `scientific_records.py`, and `test_s02c_candidate.py` required formatting even though the narrower EJ-0154 controller-only format check passed. The earlier receipt remains in this append-only journal and is superseded for cumulative formatting by this entry.
- **Mechanical-only change:** Applied Ruff formatting to the exact five-file repair surface: authority, scientific, and controller readers plus the candidate and controller-artifact regressions. No runtime logic, test assertion, public signature, DL-142 grammar, or scientific claim changed.
- **Fresh cumulative gate:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02c_candidate.py tests/resampling_null/test_controller_artifacts.py -q` passed 69 checks. Ruff lint and `ruff format --check` passed over all five files; `git diff --check` and `.venv/bin/python -m pneuma_lab.status --check` passed. The untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is a formatting and forensic-receipt correction only. No S02C behavior, S02D, publication, external action, spend, experiment, result, or claim changed.

### EJ-20260729-0156 — T5-S02C-d final independent approval

- **Specification approval:** Independent re-review approved exact SHA `7ab1dffc901e52bddae69d48b4e2214f30b6bfe0` with no findings. It verified stable consumer-specific `RecordValidationError` primaries and exact `OSError` causes across cleanup success/failure, primary-first cleanup groups, exact preservation of identity-validation and non-`OSError` failures, relinquish-before-close ownership, transactional `_mkdir_or_open`, and no regression to the approved DL-142 authority, held-descriptor, reachability, public-signature, close-before-reload, or S02C-only boundaries.
- **Quality approval:** A separate hostile code-quality review approved the same exact SHA with no critical, important, or minor findings. It verified once-only close and no fd-reuse seam, flat root-error normalization, real-helper regression coverage rather than mocked false positives, append-only receipt honesty, and AST identity across the final Ruff-only Python delta.
- **Fresh exact-SHA receipts:** Root reproduced `69 passed in 7.55s` under the bounded focused command. Both reviewers independently reproduced all 69 checks. Ruff lint and cumulative five-file format checks passed; mypy, project-status coherence, whitespace, and reviewer AST-equivalence checks passed. The only worktree residue remained the pre-existing untracked `raw_root_placeholder`, which was untouched.
- **Release boundary:** This approves deterministic local T5-S02C-d only. No S02D, prefix-index publication, provider/model/network/external call, credential use, spend, training, scientific experiment, empirical result, causal result, model promotion, or consciousness claim is authorized or implied.

### EJ-20260729-0157 — T5-S02D independent prefix-index publication

- **Authority and RED:** Implemented only the approved DL-139--DL-142 T5-S02D boundary on clean base `d841c8652a002f382b733ddbbd62e5d7cbcd3674`. The initial focused RED failed at import because the exact public `seal_prefix_index(*, run_root, schedule_ref, candidate_refs, out) -> ArtifactRef` seam did not exist. Hostile cases then required exact unique tuple input, exact selected-schedule coverage and order, reserved/existing/symlink destination rejection, and rollback of the transaction-owned target under injected write and close failures.
- **Fresh reconstruction:** S02D opens one entirely fresh scientific/controller/authority reader trio and one global visited/path/physical-identity map rooted at the schedule and all ordered candidate refs. Every role passes the closed `REF_LOAD_CLASS_BY_ROLE` partition and exact decoder registry. It reconstructs selected authority, program occurrence, snapshot and initial/grade/verifier restore ancestry, four-way process/root isolation, visible bytes and byte-token IDs, provider intent/attempt/event/settlement ancestry, exact-zero cost, counters, call seeds, monotonic chronology, earliest trigger, direct grade/verifier evidence, and exact stateless/runtime/container attestations before constructing the schema-valid index.
- **Publication:** The output is an exact absolute normalized path strictly below the resolved run root and outside the three reserved operational subtrees. One held root descriptor binds validation through create-exclusive publication and reopen verification. Directory traversal is no-follow; the final file is written completely, file-fsynced, closed once, parent-fsynced, and reread by held descriptors. Failure tracks the post-`O_EXCL` target before first `fstat`, unlinks only the transaction-owned identity when safely bound, and causally preserves primary plus cleanup failures.
- **Fresh bounded gates:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02d_prefix_index.py -q` passed 7 checks in 5.31 seconds. Focused Ruff lint and formatting passed; focused mypy reported no issues; byte compilation, `.venv/bin/python -m pneuma_lab.status --check`, and `git diff --check` passed. The pre-existing untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is deterministic local synthetic prefix-index reconstruction and publication only. It performs no provider/model/network/external call, credential use, spend, assignment, packet construction, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion.

### EJ-20260729-0158 — T5-S02D exact-SHA rejection repair

- **Exact-SHA rejection and honest RED receipts:** Repaired rejected exact SHA `beef0b21dc1638aeccef0cef550e41bdfae15453`. The rejected implementation trusted sealed completion and counter state too heavily, did not replay typed-turn queues and terminal precedence, reopened scientific parents outside the one transaction reader, omitted reader/root identity equality and all-program occurrence reconciliation, and could leave an exclusively created target after several late publication failures. Two implementation prototypes preceded their intended focused REDs; this ordering defect was not hidden. The tests were copied into a detached worktree at the exact rejected SHA to recover an honest baseline: the first nonempty replay comparison produced 3 failures and 2 pre-existing passes, and the final expanded hostile comparison produced 14 failures and 6 passes in 6.30 seconds. Independent reader/root tests produced four rejected-SHA failures. Five of six initial late-publication cases failed on the rejected SHA; parent-directory fsync rollback already passed there.
- **Independent replay and authority closure:** S02D now reconstructs provider status from raw event transport, freshly parsed response bytes, and the exact deadline; binds each intent deadline to prefix epoch plus the frozen wall cap; derives token/model/turn admission and post-call terminal state; clamps elapsed time to the controller rule; rejects transcript continuation after the first provider or tool terminal outcome; and replays exact typed-turn queues, pre-tool admission, boundary order, wall/token/tool precedence, cumulative eligible mutation, fourth-call trigger, branch pending calls, and terminal remainder. Parser-valid adverse simulator turns count from response parsing rather than completed status. One held-root scientific/controller/authority trio serves the whole traversal, every reader fstat-binds to the held root identity, one global path/physical map covers all classes, and every reachable program occurrence is independently reconciled against its grade/verifier and execution leaves.
- **Publication rollback closure:** Exclusive publication now returns an inode-bound owned-target record. File close, parent fsync, directory cleanup, reopen/read/stat/semantic verification cleanup, rollback-guard duplication, and final root close all either complete or identity-check and unlink exactly the owned target followed by parent fsync. Primary and cleanup failures remain causally grouped. The nine-case late-failure matrix proves no residue and a successful retry without `EEXIST`; replaced targets are never unlinked.
- **Fresh bounded gates:** `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02d_prefix_index.py -q` passed 41 checks in 26.16 seconds. The suite includes a full-seal replay-routing probe over a real nonempty controller execution graph, full-seal cross-class physical-alias rejection, non-selected contradictory occurrence rejection, raw-transport tampering and explicit later-row rejection after an adverse provider status, exact deadline/provider/tool clocks, per-call and aggregate allowance tampering, branch/remainder tampering, terminal precedence, all three reader/root mismatches, and all publication failure stages. Focused Ruff lint passed; focused mypy reported no issues in the five changed source modules. Project-status coherence and `git diff --check` passed. The pre-existing untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This remains deterministic local synthetic prefix-index repair. It performs no provider/model/network/external call, credential use, spend, assignment, packet construction, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion.

### EJ-20260729-0159 — T5-S02D exact replay and atomic-rollback correction

- **Correction to EJ-0158 and honest RED:** Hostile review of the actual submitted SHA `19ad00d3801ee3b8f365033aea100beffcd5578a` rejected three EJ-0158 claims. Its all-program pass reconciled leaf references but did not independently replay raw transport/parser/completion or exhaust every occurrence's clock/tool observations. Its rollback performed a separate `stat` then `unlink`, so a replacement could be deleted in the gap. Its named “full-seal nonempty” test was only a routing probe that injected a separate nonempty graph; it did not prove that the sealed candidate was nonempty. New tests were written before this repair and produced 10 failures plus 1 pre-existing pass in 4.17 seconds across exact clock ordering/exhaustion, tool-observation exhaustion, seed derivation, mutation state, nonselected occurrence evidence, post-close guard recovery, and the replacement race.
- **Exact selected replay:** S02D now consumes the S02C meter trace as one chronological sequence: prefix epoch, each provider before/after pair, and each primary tool queue's before/after pair. It rejects reversed, cross-stream, missing, or surplus reads and observations; derives each call seed from the frozen schedule prefix seed, role, and call index; rederives provider status from raw evidence; applies terminal precedence; and binds the replayed clean-terminal state to the final snapshot. Final environment `mutation_committed` is checked as the last boundary's edge-local value (false with no boundary), while the composite snapshot is checked as the cumulative OR.
- **Every-occurrence reconciliation:** Every manifest-reachable program occurrence now independently checks exact raw transport/parser/completion compatibility, raw event time against the chronological meter, ordered primary tool observations, and complete clock/tool-observation consumption. Direct `completed` plus raw `provider_error` rejects. This occurrence-only pass deliberately does **not** claim deadline or cap validation because nonselected programs do not carry selected execution authority; selected candidates retain the authority-bound deadline/cap replay.
- **Atomic rollback and close ownership:** Prefix publication rollback now uses the existing `renameat2(RENAME_NOREPLACE)` quarantine primitives to atomically bind the named source before identity/content verification and removal. Incomplete exclusive creations use the identity-bound temporary path; sealed publications use identity plus digest/count. The former `stat`/`unlink` gap is gone. A rollback-guard close that raises after closing is never reused or reclosed: recovery separately reopens the named root, verifies its saved `(st_dev, st_ino)`, performs rollback, and closes that new descriptor once.
- **Fresh bounded gates:** The original repair slice passed 11 checks with 41 deselected in 3.91 seconds. The complete S02D file passed `52 passed in 30.06s`. A final rollback-focused rerun passed 4 checks with 48 deselected in 1.47 seconds. Focused Ruff lint and format, focused mypy, byte compilation, `.venv/bin/python -m pneuma_lab.status --check`, and `git diff --check` passed. The renamed routing-probe test remains exactly that; no actual nonempty sealed-candidate claim is made. The pre-existing untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is deterministic local S02D verification and publication hardening only. It performs no provider/model/network/external call, credential use, spend, assignment, packet construction, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion.

### EJ-20260729-0160 — DL-143 cooperative publication and exact replay repair

- **Exact-SHA rejection, docs-first authority, and honest RED:** Repaired rejected exact SHA `f14bc22d97ebbf2e7be49eb713cb89eb6b59429b`. Before production edits, the focused new/changed S02D slice on that exact implementation produced 17 failures and 1 pre-existing pass, with 49 tests deselected, in 7.36 seconds. DL-143 was then frozen docs-first: plan SHA-256 `568660fe01ecbcd196182ca20fb1443aea338cd13108584000c9bb9c225cebac`; design SHA-256 `2a30625b1e4264adeceb30d95693162a4195e1f5b06743702bedda24720707aa`.
- **Correction to EJ-0158--EJ-0159:** “Replaced targets are never unlinked” and “atomic rollback” were too broad. The implemented primitive is an atomic no-replace quarantine move only inside one cooperative-local root transaction whose in-scope S02D writers and recovery paths honor the same exclusive advisory lock. POSIX has no compare-and-unlink-by-inode syscall; arbitrary same-UID or kernel-interposed mutation can occur between any final user-space identity check and a namespace syscall. That hostile syscall-gap property is impossible here, not proved. Detected missing or changed ownership before quarantine now preserves the unowned name, reports an explicit residual, and fails closed; ordinary replacement detection remains active.
- **Selected exact replay:** Initial terminal or failed restore state forbids provider dispatch. Provider failure, late completion, and token overshoot derive terminal state and the exact queued remainder. A parsed clean `finish_reason == "terminal"` is terminal for primary and simulator lanes only when it has no tools; terminal-plus-tools and any later transcript row reject. Every queued primary tool consumes its pre-tool clock before wall/tool-cap admission, and pre-tool timeout or cap termination uses that consumed clock as the final controller wall counter. The former duplicate replay was removed, leaving one exact chronological implementation and exact clock/observation exhaustion.
- **One authority transaction for every occurrence:** One `AuthorityRefReader` now validates one `ValidatedProviderPlan`; every selected task and every reachable program occurrence is projected from that same object without weaker reparsing or reopening. Occurrence replay derives exact lane deadline/caps/contracts, reuses raw provider-observation validation, permits parsed provider/infrastructure errors without misclassifying on-time rows as late, consumes every primary queued tool before deciding whether absent evidence is causally explained by wall/token/tool-cap termination, and rejects surplus or missing clocks/observations.
- **Cooperative publication regressions:** The former logical-target unlink hook was removed because production quarantines the name. Regressions now exercise actual exclusive root-lock contention and actual replacement/lost ownership before quarantine, requiring the replacement and displaced survivor to remain present while rollback returns an explicit residual. This proves the cooperative protocol only; it is not adversarial-filesystem safety.
- **Fresh bounded gates:** The focused repair slice passed 18 checks with 49 deselected in 6.47 seconds. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02d_prefix_index.py -q` passed all 68 checks in 35.05 seconds. Project-status coherence passed. The first focused static gate found one obsolete unused import; removing only that import corrected it. The repeated bounded gate passed Ruff lint and format over the two source modules and S02D test, focused mypy over both source modules, byte compilation, and `git diff --check`.
- **Boundary/non-claims:** This remains deterministic local S02D verification and publication repair. It performs no provider/model/network/external call, credential use, spend, assignment, packet construction, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0161 — S02D actor and occurrence-seed authority correction

- **Exact-SHA rejection and honest RED:** Root audit rejected internally green, unapproved, and unpushed exact SHA `830546629d53c903ca1c0330f7e59beb4463938b`. Selected replay still trusted each program row's `subject_role`; occurrence replay passed `row.seed` back as its own expected seed; and occurrence token overshoot without a queued tool did not enter terminal precedence before a later row. Five focused coherent counterexamples produced 5 failures with 68 deselected in 2.06 seconds: selected actor-role substitution, contradictory initial simulator context, a shared program checked under two different task actor sequences, a nonselected wrong prefix seed, and no-tool token overshoot reaching the next row under the wrong causal classification.
- **Actor authority repair:** The already held `AuthorityRefReader` now derives and validates the worker-equivalent exact actor sequence while validating each sealed task input: `canonical_task_payload.synthetic_actor_order`, the worker's top-level fallback when applicable, all-primary fallback when absent, exact transcript length, and only the two closed roles. The single `ValidatedProviderPlan` retains that sequence through each task lane and selected `PrefixExecutionAuthority`. Selected and every occurrence replay bind exact task identity, transcript position, and row role to it. When the initial snapshot exposes simulator context, its presence must agree with the first derived actor. Coherently changing row, intent, attempt, request, model, seed, and clock evidence therefore cannot substitute actor authority.
- **Occurrence seed and precedence repair:** Each occurrence authority now carries its selected task ID and exact schedule prefix seed from the same validated-plan/reader transaction. Before raw observation validation, replay requires `row.seed == derive_call_seed(prefix_seed, subject_role, call_index)`. Provider failure remains prior to token classification; otherwise per-call or aggregate token overshoot stops the occurrence immediately, including a parsed no-tool turn, so a later provider row rejects as continuation after a terminal outcome.
- **GREEN and fixture correction:** The five focused regressions passed with 68 deselected in 1.86 seconds. The first complete S02D run then produced 4 failures and 69 passes because older unit fixtures changed transcript length or task identity without changing their newly authoritative actor/task occurrence projections. Those fixtures were corrected to remain internally coherent; no validator was weakened. The four fixture regressions passed with 69 deselected in 1.52 seconds, and `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02d_prefix_index.py -q` then passed all 73 checks in 36.80 seconds. After the occurrence raw validator was wired directly to the already derived expected seed rather than the equal checked row field, a final complete rerun passed all 73 checks in 36.16 seconds.
- **Fresh static gate and boundary:** Ruff lint and format passed over the four source modules and two affected test modules; focused mypy passed over all four source modules; byte compilation and `git diff --check` passed. This remains deterministic local S02D authority repair only. No provider/model/network/external call, credential use, spend, branch execution, training, experiment, empirical result, causal result, or claim promotion occurred. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0162 — DL-144 commit-point and occurrence-transition correction

- **Exact-SHA dual rejection, docs-first authority, and RED:** Repaired exact SHA `1137394768d7d011fa05ee7fdf4843456b12b0a5` after specification and quality rejection. DL-144 was frozen before production edits: plan SHA-256 `2ff3eea1880a657dd2104f99b3a89851ba17f4074f394947124ead5fa488c911`; design SHA-256 `e067daf4a4f96f63b2c36987a377ea49e5fe17eebd8e2548a02121cf4c2675a0`. Six focused regressions produced 6 failures with 70 deselected in 3.62 seconds across clean-terminal remainder, execution past first eligible mutation, expected-trigger tampering, locked-root `fstat` leakage, and post-commit close rollback semantics. The initial fifth-tool case correctly failed earlier on incoherent typed response bytes; after regenerating a parser-coherent five-tool response, its isolated RED failed because occurrence replay accepted execution beyond tool four.
- **Correction to EJ-0160/DL-143:** “Retains [the lock] through ... all transaction cleanup” was impossible once final lock-descriptor close could release the lock and then raise. DL-144 defines the commit point after fresh traversal, create-exclusive publication, file/parent fsync, reopen semantic verification, every namespace-mutating rollback, and every ordinary descriptor cleanup succeeds under the exclusive lock. Lock release is the final non-mutating action. A post-commit close error now returns an explicit committed-publication cleanup residual and preserves the verified target; it never reopens the root or rolls back. This is cooperative-local only and makes no arbitrary same-UID or kernel-interposition claim.
- **Acquisition cleanup:** Successful `flock` now puts the immediately following root `fstat` and every later pre-commit action inside one causal cleanup guard. Root-`fstat` failure closes the lock descriptor once, leaves no target, and permits immediate nonblocking acquisition by a subsequent transaction. A pre-commit primary plus final close failure remains causally grouped. The rollback-guard duplicate/reopen maze and its obsolete after-close rollback semantics were removed.
- **Shared exact tool state machine:** Selected and all-occurrence replay now call the same pre-tool classifier and the same pure completed-tool transition. The latter applies tool failure, clean terminal with no queued remainder, after-tool wall timeout, token overshoot, first cumulative eligible mutation, and fourth completed tool in that exact order. Occurrence replay accumulates mutation, derives the first trigger, stops there, rejects later clocks/observations/rows through exact exhaustion, and requires equality with `program.expected_trigger_reason`.
- **GREEN, compatibility, and fresh gates:** The six focused regressions passed with 70 deselected in 3.37 seconds. The complete S02D file passed all 76 checks in 35.46 seconds; after formatting, a final fresh run passed all 76 in 37.19 seconds. Existing DL-143 lock contention and pre-quarantine ownership-loss residuals and all actor, seed, deadline, provider, terminal, and tool tests remained green. Ruff lint/format, focused mypy, byte compilation, project-status coherence, and `git diff --check` passed.
- **Boundary/non-claims:** This remains deterministic local S02D authority and publication repair. No provider/model/network/external call, credential use, spend, branch execution, training, experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion occurred. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0163 — S02D live-EOF and asynchronous commit-boundary correction

- **Exact-SHA dual rejection and honest RED:** Repaired exact SHA `26c501b877817cf18f1d2f7076be597e8dc68faf` without changing DL-144 authority. Six focused regressions produced 6 failures with 76 deselected in 5.98 seconds. Two parser-, seed-, clock-, cap-, and observation-coherent nonempty occurrences exhausted their evidence while remaining live: one ordinary no-tool stop turn and one three-tool prefix below every terminal/trigger boundary. Four `sys.settrace` injections at reviewer-named boundaries surfaced raw `KeyboardInterrupt`: after locked root `fstat`, before the verified callee return, after the verified result returned to the caller, and after final close before cleanup classification.
- **Exact occurrence end state:** Occurrence replay now distinguishes evidence exhaustion from a valid state-machine end. Empty transcript remains the worker-defined initially terminal case. Every nonempty occurrence must end through provider failure/cap/clean terminal, pre-tool timeout/tool cap, completed-tool failure/clean terminal/wall/token stop, or a derived branch trigger. An ordinary no-tool turn or fewer than four clean ineligible tools at EOF remains live and rejects even when every clock and observation is exactly consumed and the sealed expected trigger says no opportunity.
- **Callee and caller asynchronous closure:** `_seal_bound_prefix_index` returns its verified owned publication from inside the same `try` whose `except` performs identity-bound rollback, so an asynchronous exception before return is still pre-commit and removes the target under the held lock. The outer transaction uses one enclosing `BaseException` capture with a final descriptor-close attempt in `finally`. The assigned non-`None` owned result is the commit marker; the separate `committed = True` line and gap are gone. A boundary exception before assignment is classified as an explicit pre-commit interruption, causally grouped with close failure when present. A boundary exception after assignment or after final close is an explicit committed-publication residual, preserves the verified target, and never rolls back. No raw or pre/post-commit-misclassified `KeyboardInterrupt` remains in the injected matrix.
- **GREEN and fresh gates:** The six focused regressions passed with 76 deselected in 5.84 seconds. The complete S02D file passed all 82 checks in 41.06 seconds; after formatting, the final fresh run passed all 82 in 40.52 seconds. Existing lock-contention, locked-root-`fstat`, post-commit close, ownership-loss residual, actor, seed, deadline, provider, terminal, trigger, and tool tests remained green. Ruff lint/format, focused mypy, byte compilation, project-status coherence, and `git diff --check` passed.
- **Boundary/non-claims:** This remains deterministic local S02D replay and transaction-safety repair. No provider/model/network/external call, credential use, spend, branch execution, training, experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion occurred. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0164 — S02D instruction-atomic commit and explicit unlock correction

- **Exact-SHA rejection and honest opcode RED:** Repaired exact SHA `5ff70c56206d959a295b357567ea6ceb56f76b7c` without changing the frozen plan, design, or DL-144 authority. `sys.monitoring` instruction injection exposed two gaps hidden by the prior line-level matrix: the callee could return its verified owned publication before the caller's `STORE_FAST result`, and `close_attempted` could become true before `os.close` ran. The initial exact slice produced 3 failures with 82 deselected in 4.01 seconds: the call/store gap was misclassified pre-commit, the pre-close gap retained the cooperative lease, and no explicit `LOCK_UN` existed. Updating the superseded pre-return expectation to the exact DL-144 commit point produced the expanded honest RED of 4 failures with 81 deselected in 5.41 seconds.
- **Correction to EJ-0163:** EJ-0163's claims that the caller assignment was a gap-free commit marker and that any exception before the callee return remained pre-commit were too broad at instruction granularity. One exact mutable transaction state is now created by `seal_prefix_index` and passed into `_seal_bound_prefix_index`. After semantic verification, one `STORE_ATTR` publishes the owned result into that state inside the rollback guard. An interruption before that store rolls back under the held lock; an interruption after it, including before callee return or caller `STORE_FAST`, never rolls back and is classified solely from the committed state as a committed-publication residual.
- **DL-144 explicit release and namespace safety:** Final cleanup now performs idempotent `flock(fd, LOCK_UN)` before descriptor close. An interruption after unlock but before its phase store safely retries `LOCK_UN`; `EBADF` proves release already completed. Only after unlock succeeds does cleanup enter an ambiguous-close phase before calling `close`, so re-entry never double-closes a descriptor that the kernel may already have recycled. A dedicated reuse regression closes the transaction descriptor, reopens an unrelated file on the same descriptor number, injects `KeyboardInterrupt`, and proves cleanup preserves that unrelated descriptor. Committed state never reaches rollback; pre-commit state rolls back only while the lock is held.
- **GREEN, gates, and boundary:** The six instruction/line/descriptor regressions passed with 81 deselected in 6.76 seconds. The complete S02D file passed all 87 checks in 47.49 seconds; the final fresh run passed all 87 in 45.93 seconds. Focused Ruff lint/format, mypy, byte compilation, project-status coherence, and `git diff --check` passed. This remains deterministic local S02D transaction-safety repair: no provider/model/network/external call, credential use, spend, branch execution, training, experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion occurred. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0165 — S02D causal-cleanup storage and unlock-ABA correction

- **Exact-SHA dual rejection and honest RED:** Repaired exact SHA `501e677c8ea42ea1c59080aecfea79ad9d0c76e0` without changing the frozen plan, design, or DL-144 authority. After correcting one instruction-selector test bug, the exact two-regression slice produced 2 failures with 87 deselected in 3.20 seconds. An ambiguous-close `OSError` returned only as the helper's transient value disappeared when `KeyboardInterrupt` landed before caller storage. Separately, wrapped `LOCK_UN` could really unlock, close the transaction fd, reopen an unrelated victim on the same number, raise, and cause cleanup re-entry to unlock and close that victim.
- **Correction to EJ-0164:** EJ-0164's blanket causal-preservation and descriptor-reuse claims were too broad. The transaction state now owns every release error before the helper returns, and outcome classification reads that state directly; no caller assignment is cleanup authority. Release moves to `unlock_ambiguous` before the `LOCK_UN` call. Re-entry first binds the descriptor against the stored root device/inode and uses a separately opened, identity-checked named-root lock probe. `EBADF`, different identity, or an available fresh probe means the original lease was released or the fd was reused, so cleanup never unlocks or closes that ambiguous fd.
- **Bounded ambiguous recovery:** If the ambiguous fd still has the exact root identity and the fresh probe proves the root lock remains held, cleanup performs at most one identity-bound unlock retry, immediately marks its fd close-ambiguous, and proves release with a second fresh probe. It never closes an ambiguity-owned descriptor. Failure to prove ownership or release records an explicit residual and performs no unbounded retry. The exact ABA regression preserves the same-number victim, the original `KeyboardInterrupt`, the verified target, and future cooperative lock availability; a pre-`LOCK_UN` instruction interruption also releases the root lock and remains an explicit committed residual.
- **GREEN and fresh gates:** The two rejection regressions passed with 87 deselected in 2.81 seconds; the three final cleanup-boundary regressions passed with 87 deselected in 3.65 seconds. The async/lock compatibility slice passed 12 checks with 77 deselected in 14.68 seconds. The complete S02D file passed all 90 checks in 51.98 seconds; after final formatting, the fresh bounded run passed all 90 in 49.82 seconds. The first static gate identified only the new dataclass `field` import shadowing two existing loop variables; aliasing that import and formatting the test corrected it. Focused Ruff lint/format, mypy, byte compilation, project-status coherence, and `git diff --check` then passed. This remains deterministic local S02D transaction-safety repair: no provider/model/network/external call, credential use, spend, branch execution, training, experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion occurred. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0166 — DL-145 fail-stop ambiguous-release correction

- **Exact-SHA dual rejection and docs-first authority:** Repaired rejected exact SHA `73b1270717caeb6ca99a02642ccd99c9f4764556`. Before production edits, DL-145 froze plan SHA-256 `8bbb3e50020def9e1d9ccc89661fbc56ecd94e6141a4d7023d6956a400d33075` and design SHA-256 `035e0fb0ca0dfa32e76d3047b50484c351f0c3b1e7e96a9aea19b3d9be8013f7`. This explicitly corrects EJ-0165: pure Python cannot prove open-file-description ownership from a numeric fd, same inode, or fresh named-root lock probe, and it cannot make caller-side cleanup-error storage atomic against instruction-level asynchronous replacement.
- **Honest RED and fail-stop repair:** The exact two-regression slice failed twice with 88 deselected in 3.71 seconds: an interrupt before `LOCK_UN` still allowed later S02D work, and same-number same-root reuse let recovery unlock an independently locked victim. Release now arms one process-local fail-stop latch and records `unlock_ambiguous` before `LOCK_UN` and `close_ambiguous` before close. Any exception from either ambiguous phase preserves the verified target, performs no retry, probe, close, unlock, or other numeric-fd touch, and rejects later S02D work until process restart or out-of-band cleanup proof. Normal release remains ordered unlock then close and clears the latch only after completion; precommit rollback remains under the held lock. A held descriptor or lease is an allowed explicit residual, and this correction makes no immediate future-lock-availability claim.
- **Causal limit and regressions:** The same-root ABA regression proves zero victim unlocks, zero victim closes, zero fresh probes, a still-open independently locked victim, a preserved target, and a later fail-stop. The pre-`LOCK_UN` regression preserves the target, makes no availability claim, and manually closes the intentionally held test fd. A close `OSError` replaced by `KeyboardInterrupt` before the handler's `STORE_FAST` is not overclaimed as an explicit two-member group: the committed residual contains the interrupt, while the original `OSError` survives only through `__context__`. The focused REDs passed in 2.72 seconds; the 16-check interruption/release compatibility slice passed with 74 deselected in 16.79 seconds; the complete S02D file passed all 90 checks in 51.33 seconds. After final formatting, the fresh bounded rerun passed all 90 in 49.98 seconds.
- **Fresh gates and disclosed environment limit:** Focused Ruff passed, and authority-prescribed mypy reported no issues in all 29 resampling-null source files. Project-status coherence and `git diff --check` passed. The repository-wide `timeout 60s .venv/bin/python -m pytest tests/ -q` gate did not collect the suite: eight foundation modules failed import because the existing `.venv` lacks optional `torch`; no dependency was installed and no all-suite pass is claimed. The pre-existing untracked `raw_root_placeholder` remained untouched.
- **Boundary/non-claims:** This is deterministic local S02D namespace-safety and causal-reporting repair only. It adds no provider/model/network/external call, credential use, spend, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion.

### EJ-20260729-0167 — S02D atomic process-reservation and mypy-receipt correction

- **Correction to EJ-0166's static claim:** EJ-0166 incorrectly called the 29-file mypy result “authority-prescribed” without disclosing its ignore flag. The exact command actually run was `timeout 60s .venv/bin/python -m mypy --ignore-missing-imports src/pneuma_lab/resampling_null`, which passed only under that explicitly relaxed policy. Root's exact `.venv/bin/mypy src/pneuma_lab/resampling_null` command is environment-blocked: it exits `1` because `types-jsonschema` is absent for `artifacts.py`, reporting one `import-untyped` error across 29 checked source files. No dependency was installed. Exact focused `.venv/bin/mypy src/pneuma_lab/resampling_null/prefix_index.py` passes for the changed source; no package-wide no-ignore mypy pass is claimed. EJ-0166's separate repository-wide pytest disclosure remains unchanged: collection is still environment-blocked by absent optional `torch`.
- **Exact-SHA rejection and honest concurrency RED:** Root audit rejected internal unpushed SHA `eed99b93fbfacbb1be4d27f1aecc5bd06e70d883`. The global fail-stop check and later assignment were separate operations with root work between them, so two threads could both enter; the later transaction could overwrite or clear the first transaction's fail-stop state. A deterministic owner/contender interleaving produced 2 failures with 90 deselected in 3.01 seconds: contender B completed instead of rejecting while A paused before root `os.open`, and no atomic process-reservation object existed.
- **Atomic reservation repair:** S02D now acquires one private process-local `threading.Lock` nonblocking before the transaction root descriptor is opened. A concurrent or fail-stopped call rejects before `os.open` and cannot overwrite or clear the active owner. The reservation remains held through traversal, publication, final explicit unlock, and final close. An exception or interruption in `unlock_ambiguous` or `close_ambiguous` leaves both reservation and fail-stop armed permanently; later calls reject and production exports no reset seam. Only the owning production path after an accepted complete release clears state and releases the guard. Tests replace private state only to model a fresh process between cases.
- **DL-145 close rule and regression evidence:** Root's review shorthand “only fully normal close” is corrected here to frozen DL-145: normal close return or ordinary `EBADF` advances `closed` and permits reservation release; every other exception/interruption remains armed. The first post-fix run had one passing test and one test-only failure because instrumentation counted A's legitimate traversal reopens as contender entry; narrowing the counter to root opens by blocked callers B/C corrected the measurement without changing production. The exact two-test gate then passed with 90 deselected in 2.91 seconds. It proves B rejects with zero root opens, cannot disarm A, A's ambiguous release leaves the reservation locked, C also rejects with zero root opens, and two normal sequential transactions each release the reservation. The complete S02D file passed all 92 checks in 54.53 seconds; after restoring the exact frozen `EBADF` rule and placing the guard immediately before descriptor open, the final fresh bounded rerun passed all 92 in 52.57 seconds.
- **Fresh static/status and boundary:** Focused Ruff lint/format, exact focused mypy, project-status coherence, and `git diff --check` passed. This correction changes only S02D process serialization/fail-stop ownership and its forensic receipt. It performs no provider/model/network/external call, credential use, spend, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0168 — S02D ordinary root-open reservation release

- **Exact-SHA rejection and lifecycle gap:** Root audit rejected internal unpushed SHA `14d25165c028672d6d391345578ed377d0ac6ece`. EJ-0167's atomic guard correctly rejected overlap and preserved ambiguous final release, but `descriptor = os.open(root, ...)` sat outside any ordinary-error handling. A normal root-open `OSError` therefore left the process reservation permanently held even though the syscall returned no fd, no root lock existed, and no final-release ownership ambiguity had begun. That exceeded DL-145's namespace-safety boundary.
- **Honest RED and minimal repair:** A focused regression injected `OSError("ordinary root open failure")` only on the first transaction root open. It failed once in 1.67 seconds because the original error and absent target were correct but the reservation remained locked. The root open is now guarded by `except OSError` only: that ordinary no-fd result releases the process reservation and re-raises the same error. The code deliberately does not catch `BaseException`; an instruction interruption after the C open returns but before Python stores the fd remains ownership-ambiguous and conservatively leaves the process fail-stop reservation armed. No public or runtime reset seam was added.
- **GREEN and bounded compatibility:** The exact regression passed in 1.65 seconds. It proves the identical original `OSError`, zero failed target, an available reservation, a succeeding second valid S02D transaction, a valid second target, and normal reservation release. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02d_prefix_index.py -q` passed all 93 checks in 53.71 seconds; after strengthening the exception-identity assertion, the final fresh bounded rerun passed all 93 in 56.94 seconds.
- **Fresh static/status:** Focused Ruff lint/format, exact focused mypy for `prefix_index.py`, byte compilation, project-status coherence, `git diff --check`, and the frozen DL-145 plan/design hashes passed.
- **Boundary/non-claims:** This correction changes only ordinary pre-descriptor root-open failure ownership. It performs no provider/model/network/external call, credential use, spend, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0169 — DL-146 fail-stop ambiguous initial acquisition

- **Docs-first authority and exact-SHA rejection:** Specification review rejected internal unpushed SHA `66f22be7685cc8db740914cb8d47fa299057e7ba`. DL-146 was frozen before production edits: plan SHA-256 `83f750abf53f0cc0adb52511053ee677be8ee797196827e72ffe1d6204dd3474`; design SHA-256 `a3c2696867c96dd687c7fcc7a86fea4a7a27392e7e5b9d4e0af47bd1a919561a`. It supersedes DL-145 only for initial nonblocking `LOCK_EX` ambiguity and preserves DL-145 final release, DL-144 commit/locked rollback, cooperative scope, shared transitions, and all non-claims.
- **Honest RED:** The four-case acquisition slice produced 3 failures and 1 pass with 89 deselected in 5.06 seconds. A wrapper really acquired `LOCK_EX`, closed/reused the same descriptor number for the same root, independently locked the victim, then raised `KeyboardInterrupt`; cleanup collapsed it to lock-unavailable and touched the victim. An instruction interruption immediately before the acquisition syscall was likewise collapsed and cleaned. Ordinary external contention incorrectly issued `LOCK_UN` on its proven-unlocked descriptor. The already-existing normal-acquisition/root-`fstat` cleanup case passed.
- **Symmetric acquisition state machine:** Transactions now start `lock_pending`, store `lock_ambiguous`, and arm fail-stop before one `LOCK_EX | LOCK_NB`. Only normal return advances to `unlock_pending`. Documented `BlockingIOError` with `EAGAIN`/`EWOULDBLOCK` is the closed no-lock outcome: S02D performs no unlock, stores `close_ambiguous`, closes once, and after normal close or ordinary `EBADF` releases the reservation and raises the existing `RecordValidationError` from the contention cause. Any other acquisition `BaseException` is an explicit precommit acquisition residual; production performs no `fstat`, flock, unlock, close, probe, reopen, or retry on that numeric fd and leaves fail-stop armed. Any other contention-close failure likewise remains an explicit fail-stop residual.
- **GREEN, compatibility, and runtime discipline:** The four-case slice first passed with 89 deselected in 4.47 seconds. The same-root ABA victim remained open and independently locked with zero cleanup flock/close/`fstat` and zero later root opens; the pre-syscall interruption had zero post-interrupt fd touches; ordinary contention closed once without unlock, released the reservation, and preserved the error cause; normal acquisition followed by `fstat` failure normally unlocked/closed and allowed retry. One full run passed 93 checks in 55.70 seconds, but a fresh repeat honestly hit the hard 60-second ceiling near completion and produced no pass receipt. To restore margin, the chronological contention → external unlock → acquired `fstat` failure → successful retry checks were consolidated into one fixture and the redundant standalone `fstat` fixture was retired. The final three-test/four-case gate passed with 89 deselected in 3.74 seconds, and `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02d_prefix_index.py -q` passed all 92 checks in 55.80 seconds.
- **Fresh static/status:** Focused Ruff lint/format, exact focused mypy for `prefix_index.py`, byte compilation, project-status coherence, `git diff --check`, and the frozen DL-146 plan/design hashes passed.
- **Boundary/non-claims:** This correction changes only S02D initial root-lock acquisition ownership and failure classification. It performs no provider/model/network/external call, credential use, spend, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260729-0170 — DL-147 no recoverable acquisition exception

- **Docs-first authority and exact-SHA rejection:** Independent quality review rejected internal unpushed SHA `80cc19f73ba0c3f5e5c0d1b8f5a31eddcefb7096`. DL-147 was frozen before production edits: plan SHA-256 `f4584d120bfa683d4d2a06526eaabdc3e2f2d6136b19971336bdfff567ecb382`; design SHA-256 `f65c33d7b20ccd9c93b001f48c78e40f9824cb37a8ed1d60fd5346806b952a2b`. It supersedes DL-146 only for contention recoverability and preserves acquisition phases, DL-145 final release, DL-144 commit/rollback, cooperative scope, shared transitions, and every non-claim.
- **Honest RED:** The focused three-test gate produced 2 failures and 1 pass with 89 deselected in 3.42 seconds. An exact interposed wrapper really acquired the lease, closed/reused the same number for the same root, independently locked the victim, and then raised `BlockingIOError(EWOULDBLOCK)`; DL-146 trusted that synthetic errno, closed the victim, released fail-stop, and returned lock-unavailable. Plain kernel contention likewise closed its ambiguity-owned descriptor and released the process reservation. The consolidated ordinary root-open plus normal uncontended acquisition/`fstat` cleanup/retry case remained green.
- **No exception-based recovery:** The ordinary-contention close/release helper and errno special case were deleted. Every `BaseException` from initial `LOCK_EX | LOCK_NB`, including `BlockingIOError`, now enters the one explicit precommit acquisition-ambiguous residual path. Production performs zero `fstat`, flock, unlock, close, probe, reopen, or retry on the numeric fd, leaves `lock_ambiguous`, fail-stop, and process reservation armed, and rejects later S02D. Normal flock return alone advances to `unlock_pending`; ambiguity-owned test descriptors and external locks are manually cleaned only after assertions.
- **GREEN and bounded compatibility:** The exact three-test gate passed with 89 deselected in 3.07 seconds. The interposed same-root victim remained open and independently locked with zero post-exception touches; plain external contention performed zero unlock/close and fail-stopped later S02D; normal uncontended acquisition followed by `fstat` failure still normally unlocked/closed and allowed retry. `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_s02d_prefix_index.py -q` passed all 92 checks in 52.59 seconds.
- **Fresh static/status:** Focused Ruff lint/format, exact focused mypy for `prefix_index.py`, byte compilation, project-status coherence, `git diff --check`, and the frozen DL-147 plan/design hashes passed.
- **Boundary/non-claims:** This correction removes only S02D acquisition-exception recovery and its liveness claim. It performs no provider/model/network/external call, credential use, spend, branch execution, training, scientific experiment, empirical result, causal result, phenomenal-consciousness claim, or claim promotion. The pre-existing untracked `raw_root_placeholder` remained untouched.

### EJ-20260730-0171 — Task 6 freeze and blinded-projection checkpoint

- **TDD receipt:** Added focused RED tests for missing freeze/candidate modules,
  then for duplicate/escaping analysis snapshots, capability isolation in a clean
  subprocess, deterministic A–D ordering, prefix mismatch, and incomplete
  coverage. The REDs failed because the modules did not exist; the focused
  `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py -q`
  gate is GREEN: 6 passed.
- **Implementation boundary:** Analysis source/config/schema bytes are copied
  under `sources/analysis-freeze`, bound to a validated sealed packet index, and
  published through the immutable record writer. The candidate module imports
  neither artifact/assignment/secret/packet loaders nor arm records; it emits
  only the closed blinded outcome fields. Trusted sealing reloads parents and
  artifact validation recomputes the stripped candidate digest.
- **Static and non-claim:** `git diff --check` and byte compilation passed. No
  provider/model/network call, secret disclosure, spend, execution, experiment,
  result, causal claim, or claim promotion occurred.

### EJ-20260730-0172 — Task 6 review correction

- **Review correction:** The first checkpoint did not preserve provided schedule
  order and the blinded-outcome schema still exposed forbidden identity fields.
  The candidate now preserves frozen order; the schema is closed to only binary
  outcomes, finite reward, failure bit, and counters. Freeze verification now
  compares copied current bytes and rejects reserved source-name collisions.
- **Fresh gate:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py
  tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q` passed
  211 tests; byte compilation and `git diff --check` passed. This remains a
  guarded implementation slice, not a result or scientific claim.

### EJ-20260730-0173 — Task 6 irreversible-taint and singleton correction

- **Correction to EJ-0171/0172:** Those checkpoints did not establish a
  run-wide singleton transaction or permanent post-unblind protection. The
  implementation now has a dedicated Task-6 controller lock (not the
  prefix-index transaction), scans the full run namespace for existing blinded
  projection/unblind receipts, validates the complete present scientific graph,
  and serializes discovery through atomic record installation.
- **Unblind ordering:** Before any ledger decode, the unblinder reloads and
  binds manifest/schedule/prefix/freeze/projection, verifies every immutable
  `CurrentAnalysisInputs` byte ref and the raw ledger digest, and consumes the
  nominal unblind handle. It then writes/fsyncs a one-way outcome-taint marker
  before decoding assignment rows. There is intentionally no production reset;
  later freeze, task-block, or projection creation rejects.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_artifacts.py tests/resampling_null/test_assignment.py
  tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py
  tests/resampling_null/test_task6_state.py -q` passed 16 tests in under one
  second. The adversarial tests cover durable taint and a concurrent controller
  attempting an alternate projection destination. `git diff --check` and byte
  compilation passed.
- **Boundary/non-claims:** No provider/model/network action, secret disclosure,
  spend, training, branch execution, experiment, empirical result, causal
  claim, or claim promotion occurred.

### EJ-20260730-0174 — Task 6 pre-ledger CurrentAnalysisInputs correction

- **Correction to EJ-0173:** Checking immutable copied snapshots alone did not
  prove the caller's current config/schema/source bytes or packet-index parent
  still matched the freeze. `unblind_projection` now requires exact
  `CurrentAnalysisInputs` and invokes `verify_analysis_freeze` before any
  ledger byte read or decode.
- **Ordering and bypass repair:** A new ledger-excluding scientific graph pass
  validates the available graph without opening the ledger. Only then do the
  current-input/packet-parent comparison and controlled handle/commitment/raw
  digest permit routine run; only a valid permit authorizes the complete graph
  pass that parses ledger structure. The unsafe private standalone framed-permit
  helper was deleted, leaving no alternative permit derivation path.
- **Capability boundary evidence:** The projection candidate has a closed
  JSON stdin/stdout worker protocol. Its adversarial test uses `python -I`, an
  empty environment, a fresh cwd, and supplies no run-root path. A separate
  ledger-loader spy proves `pregraph -> current -> permit -> graph -> ledger`.
- **Fresh bounded gate:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_artifacts.py tests/resampling_null/test_assignment.py
  tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py
  tests/resampling_null/test_task6_state.py tests/test_schema_loads.py -q`
  passed 220 tests in under three seconds; byte compilation and `git diff
  --check` passed. No provider/model/network action, secret disclosure, spend,
  execution, experiment, result, causal claim, or claim promotion occurred.

### EJ-20260730-0175 — Task 6 taint-before-ledger-graph correction

- **Correction to EJ-0174:** The complete graph pass can decode assignment
  ledger structure. It previously ran before the durable outcome-taint marker,
  so a failure at that boundary could leave a potentially exposed context
  apparently clean. After the non-ledger graph/current-input/packet-parent and
  valid handle/permit checks, unblinding now fsyncs the one-way taint marker
  immediately before full graph validation. Invalid permit/HMAC paths remain
  untainted because they stop before that boundary.
- **Alias discovery:** The pre-unblind graph no longer blindly excludes the
  supplied ledger path. It shallowly discovers all ledger-shaped scientific
  JSON names and accepts exactly one matching bound name; an alternate path,
  hardlink, or byte-identical alias rejects before controlled ledger loading.
- **Focused proof:** Added a graph-failure regression showing that a valid
  permit taints before the full graph throws, plus the existing ordering spy.
  No provider/model/network action, secret disclosure, spend, execution,
  experiment, result, causal claim, or claim promotion occurred.

### EJ-20260730-0176 — Task 6 escaped-ledger discriminator correction

- **Correction to EJ-0175:** Raw substring discovery could miss JSON-escaped
  `record_kind` keys or values. The pre-permit discriminator now safely decodes
  only top-level keys and the scalar `record_kind` string while lexically
  skipping nested payloads; it does not invoke the ledger semantic loader.
  Escaped ledger aliases and hardlink aliases reject before permit.

### EJ-20260730-0177 — Task 7A registered statistical primitives

- **Action:** Added immutable analysis result records and pure Task-7A kernels:
  registered six-contrast decomposition; exact enumerated and dynamic-program
  sharp Fisher tails; 12-way sharp-global omnibus max-T; Philox
  domain-separated add-one fallback; benchmark-stratified Rademacher max-t
  bounds with frozen no-interpolation order; and exact equal/unequal-roster
  `q0`/`r95` sign-flip calculations.
- **Focused evidence:** The test-first import failure was observed, then
  `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_analysis.py
  -q` passed 9 tests. Ruff, byte compilation, and `git diff --check` passed.
- **Boundary/non-claim:** This slice reads no artifacts, manifests, assignments,
  or outcomes outside supplied rows; it does not implement analysis admission,
  scientific seed derivation, binary kernels, gates, verdicts, experiments,
  spend, or any causal claim. Task 7B must bind every production seed to the
  manifest-owned inference RNG contract.

### EJ-20260730-0178 — Task 7A hostile-review correction

- **Finding and correction:** The first omnibus implementation incorrectly
  studentized by a row sample standard error. It now calculates each
  equal-benchmark weighted component's conditional 12-allocation variance from
  unordered within-task outcomes. This makes the registered one-task-positive
  fixture finite (`max T = sqrt(8 / 3)`) and preserves the sharp-null meaning.
  The primitives now reject any roster other than exactly SWE and TAU, and the
  multiplier canonicalizes a unique task-ID order before consuming Philox bits.
- **Fresh focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_analysis.py -q` passed 12 tests. Ruff, byte
  compilation, and `git diff --check` passed.
- **Boundary/non-claim:** This correction remains pure Task 7A statistical
  machinery. It does not add manifest ancestry, binary kernels, `analyze`,
  gates, verdicts, or externally authorized inference randomness.

### EJ-20260730-0179 — Task 7A canonical identity correction

- **Finding and correction:** Global `task_id` uniqueness was unnecessarily
  strict and the multiplier sort key was not the frozen cross-benchmark
  identity. Multiplier draws now sort exact UTF-8 `(benchmark, task_id)` bytes
  and require uniqueness only of that pair.
- **Focused evidence:** An interleaved SWE/TAU fixture reuses `a` and `z` task
  IDs across benchmarks and produces bit-identical bounds after input reversal.
  `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_analysis.py
  -q` passed 13 tests; Ruff and `git diff --check` passed.
- **Boundary/non-claim:** Pure Task 7A correction only; Task 7B remains owner
  of manifest reconstruction, gate evaluation, analysis admission, and verdicts.

### EJ-20260730-0180 — Task 7B binary gate admission and outcome classification

- **Action:** Added immutable binary sufficient-statistics records, scalar and
  batched gate evaluation, equal-benchmark weighting, adverse ITT failure-gap
  gating, roster-byte/row-membership admission, and closed outcome precedence
  that cannot emit `FEASIBILITY_NO_GO`.
- **Focused evidence:** Test-first import failure was observed; then `timeout
  60s .venv/bin/python -m pytest tests/resampling_null/test_analysis.py -q`
  passed 14 tests. Ruff, byte compilation, and `git diff --check` passed.
- **Boundary/non-claim:** No provider/model/network action, spend, experiment,
  outcome data, causal result, or claim promotion occurred. This is analysis
  machinery only; production use still requires the separately sealed study
  manifest, power, schedule, and unblinding chains.

### EJ-20260730-0181 — Task 7B hostile-review admission correction

- **Correction:** Analysis admission now requires manifest and completed-power
  ArtifactRefs, derives roster authority from the manifest, and verifies the
  closed selected-roster membership before computing a statistic. Secondary
  multiplier p-values now use the same Philox draw stream as their family
  bounds and receive proper ordered Holm adjustment; benchmark and leave-one
  estimates are calculated rather than emitted as placeholders.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_analysis.py -q` passed 15 tests, including
  classifier precedence. Ruff and `git diff --check` passed.
- **Boundary/non-claim:** No spend, provider/model/network action, experiment,
  external outcome, causal result, or claim promotion occurred.

### EJ-20260730-0182 — Task 7B vector-kernel correction

- **Correction:** The batch gate path now calculates estimates, covariance,
  lower bounds, failure gap, benchmark checks, and leave-one membership checks
  directly from NumPy count tensors; it no longer constructs rows or invokes
  the scalar gate function per replicate. Scalar sharp gates now consume the
  caller's shared analysis seed rather than a hidden zero seed.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_analysis.py -q` passed 15 tests; Ruff and
  `git diff --check` passed.

### EJ-20260730-0183 — Task 7B count-level Fisher and resolution correction

- **Correction:** Batch gates now compute registered sharp Fisher tails from
  pattern-count dynamic states and compute exact NONE/RESAMPLE resolution from
  count-level integer distributions. The covariance uses the scalar kernel's
  ddof convention. Verdict fixtures cover all closed outcome labels other than
  the intentionally unreachable feasibility label, including sham-only and
  resampling-consistent paths.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_analysis.py -q` passed 15 tests; Ruff and
  `git diff --check` passed.

### EJ-20260730-0184 — Task 7B exact-resolution probability-mass repair

- **Correction:** Equal-roster `r95` now accumulates binomial mass for equal
  absolute sign-flip values instead of overwriting it. The 14-discordant-task
  regression gives the exact 95th-percentile resolution `4/7`.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_analysis.py -q` passed 16 tests; Ruff and
  `git diff --check` passed.
- **Status:** This is a narrowly isolated repair. Task 7B remains incomplete:
  authority-chain integration, scalable batch execution, and full hostile
  fixture coverage are still open. No causal, experimental, or spend claim.

### EJ-20260730-0185 — Task 8A frozen power authority contracts

- **Implementation:** Added the closed P0 grid/RNG fixture and synthetic
  roster fixture, plus manifest-derived synthetic and roster-bound power
  authority blobs. The only public power configuration constructor now reloads
  those authority, grid, and topology ArtifactRefs; it accepts no roster,
  decision-arm, seed, or numeric-science override. Artifact validation now
  re-derives every power report's authority mirrors before accepting its staged
  chain.
- **Focused evidence:** Test-first import failure was observed. `timeout 60s
  .venv/bin/python -m pytest tests/resampling_null/test_power_authority.py
  tests/resampling_null/test_artifacts.py tests/resampling_null/test_analysis.py
  tests/test_schema_loads.py -q` passed 224 tests; byte compilation and
  `git diff --check` passed.
- **Boundary/non-claim:** This is contract and authority plumbing only. It does
  not implement a simulator, screen, shard, selection, validation, finalizer,
  CLI, provider action, spend, benchmark execution, P0 result, or tier choice.
  Synthetic authority remains conditional-only and non-decisive by contract.

### EJ-20260730-0186 — Task 8A authority-proof correction

- **Finding and correction:** The first roster-bound authority check proved
  only that the manifest-pinned eligibility blob existed. That was not an
  authority proof. It now requires a closed eligibility grammar with the
  study-bound commitment/reveal receipts, accepted/rejected identities, nested
  C120/C160 membership, exact per-task group labels, and ordered disjoint
  reserves; each surface must reproduce the manifest roster exactly.
- **Staged-record correction:** `resampling_power_report` now persists
  `grid_content_sha256` in addition to the complete RNG-contract digest.
  Artifact validation reloads the authority and calls the closed config/grid
  loaders before accepting report mirrors, rejecting swapped topology/grid refs
  and malformed or noncanonical grid content.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power_authority.py
  tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q`
  passed 211 tests, including real schema-valid staged-screen attacks. Ruff,
  byte compilation, and `git diff --check` passed.
- **Boundary/non-claim:** Still no simulator, screening, tier selection,
  provider action, spend, benchmark execution, P0 result, or promoted claim.

### EJ-20260730-0187 — Task 8A ceremony-cryptography correction

- **Correction:** Replaced shaped eligibility receipt hashes with the shared
  typed commitment frame: the nonce reveal now recomputes the manifest's
  `roster-local-nonce` commitment, the precommit repeats all three manifest
  commitments and is canonically digested, the timestamp binds that digest and
  frozen timestamp, and the roster seed is recomputed from the fixed drand
  chain/round/randomness with the exact `roster-seed-v1` frame. Altered study,
  nonce, commitment, precommit, beacon, or seed bytes fail before authority
  sealing.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power_authority.py -q` passed 6 tests; Ruff and
  byte compilation passed. No external ceremony, provider, spend, simulation,
  or scientific result occurred.

### EJ-20260730-0188 — Task 8A confirmation authority fail-closed correction

- **Finding and correction:** The exact local frames prove internal byte
  consistency but do not authenticate an external timestamp or drand receipt.
  The preflight contract confirms that no reviewed live ceremony adapter exists.
  Roster-bound authority now always raises `RecordValidationError` with the
  explicit unavailable-adapter reason; arbitrary beacon/timestamp fields are
  therefore rejected rather than treated as proof. The prior local ceremony
  parsing is non-authoritative and cannot mint an authority blob.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power_authority.py -q` passed 6 tests, including
  arbitrary beacon/timestamp rejection. No confirmation authority, provider
  action, spend, simulator, P0 result, or claim exists.

### EJ-20260730-0189 — Task 8B deterministic P0 substrate

- **Implementation:** Added public ordered frozen grid expansion (729
  alternative and 2,187 null-family cells), 96-point Gauss-Hermite pattern
  probabilities, 128-point Plackett integration, bounded Gaussian-max and
  one-sided Clopper-Pearson inversions, framed Philox mapping, and immutable
  synthetic screen-record creation. The screen accepts no seed, generator,
  roster override, decision authority, provider, or spend input.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py -q`
  passed 11 tests.
- **Boundary/non-claim:** The synthetic screen is not a P0 result or tier
  selection and never mints roster-bound confirmation authority.

### EJ-20260730-0190 — Task 8B staged synthetic authority closeout

- **Implementation:** Finalization now globally discovers and validates every
  append-only non-final report for its exact power-authority ArtifactRef,
  canonicalizes the complete ledger, rejects a second final, and parents every
  discovered attempt. A resumed Gaussian generation therefore cannot omit an
  earlier immutable screen. The synthetic failure arm likewise rejects a
  caller-selected partial ledger. Restored the schema-required derived final
  kernel mirror. The 20,000-trial Clopper--Pearson calculations now use a
  bounded continued-fraction incomplete-beta evaluation instead of overflowing
  direct binomial-coefficient summation.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power_authority.py::test_synthetic_final_discovers_every_prior_authority_attempt
  -q` exercised screen -> every shard -> selection -> validation -> final,
  included a prior resumed generation, and called full scientific-graph
  validation. The asserted output decision was `CONDITIONAL_ONLY` with a null
  synthetic tier. `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py
  -q`, byte compilation, and `git diff --check` were also run.
- **Boundary/non-claim:** This creates no canonical run artifact and performs
  no provider call, confirmation action, spend, external benchmark execution,
  P0 claim, or tier selection.

### EJ-20260730-0191 — Task 8B count-level authority-path migration

- **Implementation:** Replaced the static-binomial shard shortcut with framed
  Philox regeneration of exact `n=20` fixed-size trigger partitions and
  sixteen-pattern sufficient statistics. Every bounded chunk passes through
  the Task-7 batch gate; artifacts retain only compact gate totals, an
  eight-leaf replay frontier, and a full Merkle commitment. Staged validation
  rejects malformed totals/frontiers, and merge consumers reject incomplete
  synthetic chunks before selection/finalization.
- **Focused evidence:** `timeout 60 .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py
  tests/test_schema_loads.py -q` passed. The tiny two-dataset/one-cell fixture
  proves receipt formation and separately proves it cannot enter an authority
  merge.
- **Boundary/non-claim:** Production remains unrun and requires the complete
  frozen grid. The fixture escape hatch is synthetic-only and cannot mint a
  selection, final report, tier, result, or claim.

### EJ-20260730-0192 — Task 8B hostile receipt repair

- **Implementation:** Replaced the eight-leaf sample frontier with a replayable
  receipt that commits every bounded chunk's ordinal range, dataset/pass totals,
  and Merkle root, plus the full aggregate root and exact Task-7 totals. Shard
  results now execute exactly one frozen family (`alternative`, `null_both`,
  `null_content`, or `null_excess`) rather than duplicating alternative totals
  into a null field. The joint layout derives from manifest benchmark/group
  labels; task-ID spelling is no longer treated as an experimental covariate.
  Pre-write authority closure/generation identity checks and a measured
  non-constant screen timing receipt were also added.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py -q`
  passed 20 tests after the red receipt-coverage test. `git diff --check` and
  byte compilation were run in the same slice.
- **Boundary/non-claim:** Gaussian validation remains unaccepted: it still
  needs fresh 2,000-outcome validation-domain runs, a true full-multiplier
  fallback producer/finalizer, and complete end-to-end closure tests. No P0
  outcome, type-I bound, tier selection, provider action, or spend occurred.

### EJ-20260730-0193 — Task 8B multiplier-validation closure substrate

- **Implementation:** Replaced the fabricated Gaussian validation receipt with
  validation-domain count regeneration, actual one-sided Clopper--Pearson
  intervals, and a deterministic 99,999-draw raw-count Rademacher max test.
  Added the phase-closed full-grid fallback producer/finalizer: it is reachable
  only from a persisted failed Gaussian validation, measures the real multiplier
  kernel before screen admission, and writes canonical raw-count and decision
  receipts.  Synthetic results remain null-tier `CONDITIONAL_ONLY`.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py -q`
  passed after the multiplier engine test was first observed failing on the
  missing public routine.
- **Boundary/non-claim:** No 2,000-outcome validation or full-grid fallback was
  executed here. Those calculations are intentionally expensive evidence work,
  not a unit-test fixture; no P0 result, provider action, spend, or claim exists.

### EJ-20260730-0194 — Task 8B hostile contract repair

- **Implementation:** The count simulator now preserves the manifest's joint
  sensitivity-cell labels and expands each `(benchmark, group, pattern)` count
  into `BinarySufficientStatisticsBatch`; Task-7 leave-one-group gates now see
  real group tensors rather than an overall-only projection. Fallback screen
  prewrite reloads the current maximal Gaussian validation and rejects any
  non-failed, foreign-authority, grid, or topology-mismatched trigger before
  timing or persistence. Screen timing is projected as measured work per cell
  times full cells times production datasets divided by frozen shard count.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py -q`
  passed 23 tests; the focused suite includes group-tensor routing and exact
  production-work timing projection. `git diff --check` passed.
- **Boundary/non-claim:** No P0 grid, Gaussian validation, multiplier fallback,
  provider action, external benchmark, spend, tier selection, or scientific
  claim was run or created.

### EJ-20260730-0195 — Task 8B canonical joint-label receipt binding

- **Implementation:** The replay receipt now serializes the canonical ordered
  `(benchmark, joint-cell, group-kind, value)` labels and includes them in its
  layout digest. Identity validation reloads those exact labels from the roster
  and passes them into receipt replay; equal-sized joint cells can no longer be
  relabeled without detection. The power-report schema requires the label
  commitment. A controlled batch confirms that registering a hostile group
  changes the Task-7 leave-one-group result, rather than merely changing tensor
  shape.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py -q`
  passed 25 tests; `timeout 60s .venv/bin/python -m pytest
  tests/test_schema_loads.py -q` passed 201 tests. `git diff --check` and
  `compileall` also passed.
- **Boundary/non-claim:** No P0 grid, Gaussian validation, full-multiplier
  fallback, provider action, spend, tier selection, or scientific claim ran.
  The full lifecycle remains deliberately unrun: its 2,000-outcome / 99,999-draw
  evidence path is not a bounded unit-test fixture.

### EJ-20260730-0196 — Task 9 conditional CLI slice

- **Implementation:** Added the fail-closed module entry point and JSON-only
  command adapter for study sealing/validation, synthetic or roster-bound power
  authority, immutable screen/shard/selection/validation/final stages, artifact
  sealing/verification, and read-only status. Scientific paths are confined to
  normalized root-relative names; the parser has no seed, roster, decision
  authority, provider, cloud, or secret option. The synthetic terminal arm
  requires an explicit closed terminal stage and reason.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_cli.py -q` passed (2 tests); `compileall` and
  `git diff --check` passed.
- **Boundary/non-claim:** No selftest, P0 grid/shard, validation, provider
  action, external benchmark, spend, tier selection, or scientific claim ran.

### EJ-20260730-0197 — Task 9 CLI hostile-review correction

- **Correction:** The completed full-multiplier final arm now calls the actual
  fallback finalizer and requires its exact screen, numeric shard-prefix, and
  fallback-validation parents. Final arms reject missing selected references
  before converting them to paths. CLI scientific inputs/outputs now require
  canonical nonempty POSIX relative names (no dot segments, doubled slash,
  backslash, or overwrite); shard discovery accepts only the exact numeric
  suffix boundary. Malformed mappings and type/key failures are normalized to
  the same one-object redacted JSON failure surface.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_cli.py -q` passed 4 tests; `compileall` and
  `git diff --check` passed.
- **Boundary/non-claim:** This correction executed no P0 simulation, full
  multiplier validation, provider action, benchmark, spend, or claim.

### EJ-20260730-0198 — Task 9 selftest staging preflight checkpoint

- **Implementation:** Added the exact `selftest` parser surface with an
  explicit `--stop-after-study`/`--resume-after-power` mutual exclusion and
  rejected the meaningless `--stop-after-study --defer-artifact-root` pair.
  The committed production-owned, zero-spend fixture materializer now writes
  its fixed source closure under `sources/selftest-fixture/` and uses the real
  study-seal contract to create only `study-manifest.json` and copied inputs.
  Resume performs its read-only admission check before any descendant write:
  exactly one study manifest, a root-confined final reference, the manifest's
  complete compatible schedulable power chain, and no schedule or later
  scientific record. It returns a specific redacted checkpoint gate instead of
  pretending descendant materialization exists.
- **Focused evidence:** The new parser/resume tests were first observed RED
  (the command was absent and argparse returned only a generic error), then
  `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_cli.py -q`
  passed 7 tests. `compileall`, `git diff --check`, and
  `.venv/bin/python -m pneuma_lab.status --check` passed.
- **Blocker/next gate:** The materializer is a deliberately minimal committed
  fixture closure, not the planned public static JSON bundle, and its source
  stage has no completed P0 final. Next, bind the frozen public P0
  grid/roster/topology fixture identities into that closure, then implement the
  selected-descendant materializer against an admitted completed final.
- **Boundary/non-claim:** The focused test sealed only a synthetic fixture
  manifest and copied inputs. No P0 work, provider action, external benchmark,
  spend, tier selection, or scientific claim occurred.

### EJ-20260730-0199 — Task 9 hostile-review repair: frozen P0 stage binding

- **Correction:** Replaced the selftest materializer's placeholder power inputs
  with the exact committed frozen `p0-power-grid.json` and a committed frozen
  screen-topology contract. The study manifest now binds their copied artifact
  identities, and a synthetic authority can load the manifest-bound P0 config
  without invoking a screen or grid. Study-only preflight occurs before source
  materialization: an existing manifest or receipt refuses with no write.
  CLI parsing now uses a redacted parser exception rather than argparse's usage
  emitter; malformed input produces exactly one JSON object on stdout and no
  stderr. Explicit `--debug` adds only the safe classification
  `argument parsing failed`, never a traceback or secret value.
- **Focused evidence:** New tests were first observed RED for placeholder-grid
  binding, mutation-before-refusal, and argparse stderr leakage. `timeout 60s
  .venv/bin/python -m pytest tests/resampling_null/test_cli.py -q` then passed
  10 tests. `compileall`, `git diff --check`, and
  `.venv/bin/python -m pneuma_lab.status --check` passed.
- **Boundary/non-claim:** This loaded configuration only; it did not run a P0
  screen, shard, validation, final, provider, benchmark, paid action, or make a
  tier/scientific claim. Resume descendants remain intentionally unimplemented.

### EJ-20260730-0200 — Task 9 hostile-review repair: full roster determinism

- **Correction:** Replaced the one-task selftest roster/registry shortcut with
  the exact committed `fixtures/resampling_null/p0-roster-synthetic.json`.
  The materializer derives its closed task registry from all 40 frozen roster
  tasks and constructs corresponding offline provider-contract lanes; it no
  longer imports host Python or Unicode versions into scientific source bytes.
  The registered runtime identity is fixed at CPython 3.12.0 / Unicode 15.0.0.
- **Focused evidence:** The pre-repair study-stage test was observed RED with
  `provider task lanes do not exactly cover the task registry`; after the full
  lane closure, it passed. The new exact-roster/determinism test verifies the
  copied roster digest, 40 tasks across SWE and TAU, and byte-identical manifest
  output from two separate roots. `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_cli.py -q` passed 11 tests; `compileall` and
  `git diff --check` passed.
- **Boundary/non-claim:** This materialized only deterministic synthetic study
  inputs and a manifest. No P0 screen/shard/validation/final, provider,
  benchmark execution, spend, tier selection, or scientific claim occurred.

### EJ-20260730-0201 — Task 9 selected-descendant CLI wiring checkpoint

- **Implementation:** Added fail-closed `schedule seal`, `synthetic prefixes`,
  and `assignment seal` parser/dispatch routes. Schedule preflights the exact
  root-confined manifest and complete compatible final before output/lease
  allocation, then accepts only an external decimal-U64 seed reveal. Prefixes
  take only direct study/schedule refs; assignment takes only direct
  schedule/prefix refs plus an external secret-file handle, preserving the
  existing single-use, in-memory 32-byte commitment check. All new root-side
  names reuse strict normalized POSIX/no-overwrite handling.
- **Focused evidence:** The parser-surface test was observed RED because all
  three commands were absent. After wiring, `timeout 60s .venv/bin/python -m
  pytest tests/resampling_null/test_cli.py -q` passed 15 tests; `git diff
  --check` and `.venv/bin/python -m pneuma_lab.status --check` passed.
- **Blocker/next gate:** The success routing fixture is bounded at the CLI/API
  boundary because no completed P0 final exists. A hostile review must inspect
  ancestor/ref/secret handling, then a genuine admitted synthetic final is
  required before running prefixes or assignment and before making any
  descendant-execution claim.
- **Boundary/non-claim:** No power simulation/final, prefix/provider action,
  assignment ledger, benchmark outcome, paid action, or scientific result was
  executed.

### EJ-20260730-0202 — Task 9 packet command authority checkpoint

- **Implementation:** Added `packets build` and `packets audit` as
  root-confined, ref-only CLI transitions. Both reload the supplied sealed
  study, assignment, and prefix records, prove assignment/prefix/schedule
  ancestry reaches that exact manifest, and derive tokenizer/template/policy/pad
  authority solely from the manifest. Build invokes the existing Task-5
  normalizer, type-preserving rewrite, packet-pair constructor, and candidate
  writer; audit derives the selected task roster from the supplied schedule and
  invokes the existing independent sealed-index reconstruction. No command
  accepts an arm, donor, packet text, key, capability, provider, or external
  source argument. Output names remain normalized root-relative POSIX and
  refuse overwrite.
- **Focused evidence:** New parser, exact-parent routing, and real malformed
  root-name/no-write tests were observed RED before the command existed. Then
  `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_packets.py
  tests/resampling_null/test_cli.py -q` passed 19 tests; `py_compile` and
  `git diff --check` passed.
- **Blocker/next gate:** This is controller wiring only. No admissible completed
  P0 final exists, so no schedule/prefix/assignment/packet artifact was
  materialized. A hostile review must inspect the full controller slice; only a
  genuinely admitted synthetic final can authorize descendant execution.
- **Boundary/non-claim:** No P0 work, provider action, benchmark execution,
  secret handling, spend, packet delivery, causal result, or claim occurred.

### EJ-20260730-0203 — Task 9 packet prewrite closure correction

- **Correction:** Made `packets build` reserve its candidate output name in a
  named preflight step before entering the Task-5 builder, rather than relying
  on argument-evaluation order. The new occupied-output regression asserts that
  an existing candidate leaves the root byte-for-byte path-set unchanged and
  never enters the packet-work builder.
- **Focused evidence:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_cli.py -q` passed 19 tests; `git diff --check`
  passed.
- **Blocker/next gate:** A requested no-mock build-to-audit CLI integration
  test is not honestly constructible from the current provider fixture. Its
  deliberately minimal sealed manifest aliases tokenizer-shaped blobs as
  roster/storage refs: replacing them with local-test-valid assets breaks the
  fixture's promoted-authority replay, while preserving them fails the storage
  lease admission. A dedicated valid synthetic lineage fixture is therefore a
  later Task-9 fixture slice, not something this command patch may forge.
- **Boundary/non-claim:** No packet build/audit, P0, provider, benchmark,
  secret, spend, or claim was executed.

### EJ-20260730-0204 — Task 9 completed-lineage fixture admission audit

- **Action:** Audited whether a dedicated test-only sealed lineage could run
  the real CLI schedule, prefix, assignment, packet-build, and packet-audit
  transitions from a completed synthetic power final without executing P0.
  The existing bounded producer was traced through its merge and schedule
  consumers; no record bytes were fabricated or manually promoted.
- **Result:** BLOCKED BY LIVE CONTRACT, intentionally. The only bounded API,
  `simulate_power_shard(..., max_datasets/max_cells)`, persists
  `execution_complete: false`; `_complete_shards` rejects that state before
  selection, validation, both completed finalizers, and schedule admission.
  `load_power_config` accepts only the manifest-pinned frozen 2,916-cell,
  20,000-dataset-per-cell P0 grid (with 2,000 validation datasets and 99,999
  multiplier draws). Thus there is no compatible small completed final to
  derive via current APIs. Hand-authoring one would bypass replay receipts and
  the discovered append-only authority ledger, which is fabricated authority,
  not a fixture.
- **Evidence:** Existing focused regression
  `test_tiny_synthetic_shards_cannot_enter_the_authority_merge` exercises the
  bounded producer and observes the exact merge rejection. Static contract
  inspection identified the frozen-grid and completed-chain checks in
  `power.py` and `assignment.py`. No long P0 evaluation was launched.
- **Next gate:** Execute the already frozen full synthetic P0 only under its
  separate scientific runtime protocol, then build the genuine descendant E2E;
  alternatively design a separate miniature non-authority protocol that cannot
  enter this P0 schedule chain. No P0 result, provider action, packet,
  assignment, spend, or scientific claim was produced.

### EJ-20260730-0205 — Task 9 analysis CLI authority boundary

- **Implementation:** Added the registered `analysis freeze`, `project seal`,
  `synthetic branches`, and `analyze` command surfaces. Freeze resolves only
  an external source root plus normalized relative names and external
  config/projection-schema files, validates a sealed packet parent, and calls
  the existing snapshotting freeze authority. Project reserves its output
  before outcome access, invokes the pure projection candidate builder in a
  `-I` subprocess with stripped bytes only and no controller-root argument,
  then hands the candidate to the existing trusted Task-6 reconstruction seal.
  Analyze derives schedule/power context from sealed parents, obtains both
  unblind-purpose handles internally from the external key file, consumes the
  permit internally, and only then calls the registered analysis API.
- **Critical correction / blocker:** The source tree contains no Task-5 opaque
  branch executor (the controller exports only prefix-era seed derivation), so
  `synthetic branches` is deliberately fail-closed after its parser/ref
  admission. It reports `synthetic branch executor is not installed` and never
  creates a task block. This is not a completed branch route or E2E claim.
- **Focused evidence:** New parser/refusal tests were observed RED while the
  commands were absent. After wiring, `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_cli.py tests/resampling_null/test_freeze.py
  tests/resampling_null/test_blinding.py -q` passed 31 tests; `py_compile` and
  `git diff --check` passed.
- **Boundary/non-claim:** No P0 run, completed final, branch, packet delivery,
  projection, clear outcome, analysis result, provider action, spend, or claim
  occurred. The next gate is implementation and hostile review of the missing
  branch executor, followed by a genuinely admitted full P0 lineage.

### EJ-20260730-0206 — Task 9 P0 clear-ledger boundary repair

- **Correction:** Hostile review found that `analyze` decoded the clear
  assignment ledger before permit issue and that `issue_unblind_permit` decoded
  it after HMAC creation. The CLI now derives the public prefix parent from the
  sealed packet index and checks its opaque ledger ref by exact equality; it
  never parses ledger JSON. Permit issuance binds raw bytes only. The sole
  clear-ledger parser remains `unblind_projection`, after pregraph and permit
  checks.
- **Focused evidence:** New spies were observed RED against both old paths.
  `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_blinding.py::test_permit_issuance_never_decodes_the_clear_ledger
  tests/resampling_null/test_cli.py::test_cli_analyze_does_not_decode_ledger_before_guard -q`
  passed 2 tests; compile and whitespace checks passed.
- **P1 architecture audit:** Existing Task-6 `unblind_projection` must durably
  taint before outcome parsing and writes its singleton receipt before returning
  rows. Task-9 numerical analysis is subsequently computed and atomically
  written with a separate single-record `write_record`; no paired transaction
  primitive exists. A later analysis failure can leave the receipt without an
  analysis record. This is recorded as unresolved—not papered over with unsafe
  receipt/taint rollback. A future repair requires a reviewed staged-unblind
  plus paired-publication protocol.
- **Boundary/non-claim:** No unblind, P0, analysis, provider action, spend, or
  scientific result was executed.

### EJ-20260730-0207 — Task 6 / Task 9 paired unblind-publication repair

- **Correction:** Replaced the CLI's receipt-first unblind/then-analysis write
  sequence with a staged controller transaction. After the valid permit and
  irrevocable pre-decode taint, clear rows remain in memory while registered
  row conversion and numeric analysis construct a fully validated analysis
  record. The future receipt digest is derived from validated deterministic
  bytes, so the analysis binds it before either artifact is public. Both output
  destinations are preflighted before taint; neither may preexist.
- **Publication recovery:** Since receipt and analysis may reside in different
  root-relative directories, the single-directory foundation publisher cannot
  make them one kernel rename. The controller therefore durably writes a
  no-clear prepared-pair intent (only target paths/digests/sizes), then writes
  the two already-validated public records. A controlled second-write failure
  removes the matching first record. A future authenticated paired-unblind
  controller rederives the permit-bound transaction key and recovers a crash:
  two matching targets complete the transaction; a matching
  partial target is removed; malformed or substituted targets fail closed.
  No raw assignment mapping, key, or clear row is serialized in the intent.
- **Focused evidence:** The new builder-failure regression was observed RED
  before the staged API existed. It now proves analysis failure leaves neither
  receipt nor analysis while the outcome taint remains and blocks protected
  work. A second-write failure-injection regression proves receipt rollback;
  a simulated crash proves authenticated next-controller recovery removes a partial pair.
  `timeout 60s .venv/bin/python -m pytest tests/resampling_null/test_blinding.py
  tests/resampling_null/test_cli.py -q` passed 34 tests; `py_compile`,
  project-status check, and whitespace check passed.
- **Boundary/non-claim:** This is controller integrity plumbing only. No
  unblind ceremony, P0, provider, benchmark, spending action, or numerical
  scientific result was executed. The actual full-lineage unblind/analysis E2E
  remains blocked by the unrun full P0 and absent Task-5 branch executor.

### EJ-20260730-0208 — Hostile-review repair: pair ownership and no-replace install

- **Correction:** Review correctly rejected the initial recovery design: a
  digest-matched replacement could be deleted, and a check-then-atomic-replace
  writer could overwrite a post-preflight creator. Pair entries now receive
  private, owner-only staging paths before any public install. Their exact
  `(device,inode)` identities are durably recorded only after full bytes are
  fsynced. The private link remains until commit/recovery, pinning that inode
  against same-bytes replacement/reuse.
- **Publication/recovery rule:** Public installation is POSIX `link` from that
  bound staging inode, which atomically creates the target and fails if any
  later writer already created it; it never replaces. Recovery removes only
  targets and staging files whose identity *and* bytes match the transaction.
  An external/replaced/malformed target leaves all suspect files in place and
  raises a fail-closed ownership error. The obsolete public receipt-only
  `unblind_projection` entry point was removed; only the paired route may
  expose a staged clear projection to the controller callback.
- **Focused evidence:** New adversarial tests prove a same-byte replacement is
  retained with an ownership failure, and a post-preflight creator is never
  overwritten. The existing injected second-install failure still removes only
  the owned first target. `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_blinding.py tests/resampling_null/test_cli.py -q`
  passed 37 tests after the repair.
- **Boundary/non-claim:** No clear assignment mapping, key, or arm is written
  to the no-clear transaction intent or exposed through this repair. No P0,
  provider, spend, unblind ceremony, or scientific result was run.

### EJ-20260730-0209 — Hostile-review repair: authenticated crash recovery

- **Correction:** Review found the remaining crash window between private temp
  creation and the later inode-identity journal update. The intent now
  predeclares a keyed private staging name before creation. Recovery can sweep
  that exact authenticated alias when identity is absent, so a controller crash
  cannot permanently strand the run. Once identity exists, deletion remains
  exact inode-plus-byte ownership only.
- **Intent authority:** The intent carries an HMAC over state/entries using a
  non-persisted key derived from the already validated in-memory unblind permit
  under a pair-specific domain. After a crash, the legitimate controller
  rederives that permit from a fresh bound unblind handle and the committed
  refs; a bare lock has no deletion authority and fails closed. Mutated intent
  bytes therefore cannot redirect recovery cleanup. No raw secret is stored.
- **Focused evidence:** Fault injection after private `O_EXCL` creation but
  before identity journal update recovers the keyed temp and intent. A forged
  intent that names a victim via a hard-linked staging alias fails
  authentication and leaves the victim/alias intact. `timeout 60s
  .venv/bin/python -m pytest tests/resampling_null/test_blinding.py
  tests/resampling_null/test_cli.py -q` passed 39 tests.
- **Boundary/non-claim:** This recovery authorization is controller plumbing;
  no external data, key, arm mapping, P0, provider, spend, or scientific result
  was exposed or executed.

### EJ-20260730-0210 — Hostile-review repair: recovery key separation

- **Correction:** The prior transaction HMAC was derived from the permit MAC.
  Because a completed receipt serializes that permit MAC, it was not a durable
  recovery secret. Added the registered `pair_recovery` assignment-subkey
  domain and a capability-only derivation from the master key, study, manifest,
  and schedule. The recovery key exists only in a mutable buffer during a
  fresh bound unblind-handle claim and is wiped before return; it is neither
  serialized nor derivable from receipt bytes.
- **Controller flow:** `analyze` now obtains a distinct fresh unblind handle
  for recovery-key derivation, in addition to the permit and final
  clear-boundary handles. A pending pair may therefore be authenticated and
  recovered only by a controller that can reopen the owner-custodied master
  key with the exact committed bindings.
- **Focused evidence:** The forged-intent/hardlink regression now recomputes
  its fake HMAC using a simulated readable receipt permit. Recovery with the
  genuine pair key rejects it and leaves the victim intact. `timeout 60s
  .venv/bin/python -m pytest tests/resampling_null/test_blinding.py
  tests/resampling_null/test_cli.py -q` passed 39 tests.
- **Boundary/non-claim:** No master key, recovery key, unblind mapping, P0,
  provider action, spend, or scientific result was persisted or executed.

### EJ-20260730-0211 — Task-9 repair: preserve closed power-ref media identity

- **Correction:** The canonical CLI `_ref` adapter had reconstructed every
  artifact reference as generic `application/json`. Consequently, a genuine
  `power authority synthetic` record could not enter the immediately following
  `power screen` command: `load_power_authority` correctly rejected the
  downgraded authority identity. The adapter now has an explicit power-role
  media registry: `power_authority` uses the closed
  `application/vnd.pneuma.power-authority+json` media type, while the frozen
  grid, screen topology, and JSON power reports remain explicitly
  `application/json`.
- **Focused evidence:** A fresh selftest study root seals a synthetic authority
  through the public CLI, then runs the canonical Gaussian `power screen`
  command against the manifest's own grid/topology refs. The screen succeeds
  with the registered 64-shard topology and writes a stage=`screen` report.
  The initial test failed before the fix with the exact closed-media rejection.
  `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_cli.py::test_cli_power_authority_then_screen_uses_closed_authority_media_type
  tests/resampling_null/test_cli.py::test_cli_selftest_study_binds_frozen_p0_inputs_and_admits_power_config -q`
  passed 2 tests; whitespace check passed.
- **Boundary/non-claim:** This runs one bounded screen preflight only. It does
  not execute a production shard, validation, multiplier fallback, final P0,
  schedule, provider, spend, benchmark, or scientific result.

### EJ-20260730-0212 — Task-10 canonical P0 timing admission deviation

- **Action:** Created the ignored canonical synthetic root
  `build/research/neurips-2026-workshop/p0-canonical`, sealed its study
  manifest (`4a0c0d9f...`), sealed synthetic power authority
  (`136aee9708...`), and sealed the Gaussian screen
  (`95b34c87...`) with the manifest-bound committed grid/topology and the
  admissible immutable 64-shard topology. The historical plan's 16-shard
  example is not admissible against the current frozen timing projection.
- **Observed deviation:** One production shard (`shard_index=0`) was begun as
  an exact registered timing measurement. It remained CPU-bound across eight
  numerical threads for approximately 13 minutes 35 seconds without writing a
  shard artifact. A sequential 64-shard extrapolation therefore exceeds the
  frozen 43,200-second (12-hour) cap. The process was sent `SIGTERM` before it
  emitted any scientific shard record; no other shard was launched.
- **Gate/result:** This is a timing-admission no-go, not a partial P0 result.
  The pre-run screen's 3,436-second projection was non-conservative in this
  environment. Do not resume, shrink the grid, alter shard count, or claim a
  completed/failed P0 final from this root. Reconcile the production timing
  estimator and rerun a newly screened immutable generation before any P0
  continuation.
- **Boundary/non-claim:** Zero spend, no provider or benchmark action, no
  validation/finalization, no schedule/descendant, and no scientific result or
  claim. The terminated command left no `shard-0.json` artifact.

### EJ-20260730-0213 — Task-8B timing-admission repair

- **Root cause:** The sealed screen measured only `frozen_power_cells()[0]` at
  200 draws, then divided the extrapolated total by its artifact shard count.
  Production instead evaluates every frozen cell through the Task-7 count gate,
  while the current operator path executes those receipt partitions
  sequentially. The canonical shard-0 timing therefore exposed a structural,
  not stochastic, under-estimate.
- **Correction:** A screen now runs the manifest-frozen 200 screen-domain draws
  for all 2,916 cells through the production gate, commits a deterministic
  all-cell replay-receipt digest bound to authority, roster membership, grid,
  phase, and cell order, and projects all 20,000-dataset production work with
  no assumed concurrency discount. The receipt is replayable through the
  exported validator. The power-report schema requires this timing receipt.
- **Focused evidence:** Test-first regression changes the former four-shard
  optimistic projection from 145,800 to 583,200 seconds; a mocked slow
  production-representative probe is rejected before a screen record can be
  written. The all-cell probe test proves every cell receives exactly 200
  screen-domain Task-7 draws. `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py
  tests/test_schema_loads.py -q` passed.
- **Next gate:** Run a new immutable canonical screen generation. If its
  committed total-work projection exceeds 43,200 seconds, finalize only the
  appropriate non-decisive synthetic timing failure; do not resume the old
  shard, change the scientific grid, or claim P0 evidence.
- **Boundary/non-claim:** No production shard, P0 final, validation, provider,
  spend, benchmark result, or scientific claim was produced by this repair.

### EJ-20260730-0214 — Hostile-review repair: one-time timing verification

- **Correction:** The first timing repair exposed a second defect: its full
  replay validator was dead, and naïvely invoking it in every resumed shard
  would multiply the bounded 2,916-cell probe by the shard count. The one full
  replay now occurs inside `power screen` while an exclusive run-root screen
  lock is held. The immutable screen record is published only after that probe
  and structural verification; an `O_EXCL`, fsync'd verifier marker then binds
  the exact screen ArtifactRef, authority ref, and timing-probe bytes.
- **Consumer gate:** Every shard and every merge/final path performs cheap
  exact frozen-layout/projection checks and requires the one-time marker to
  bind the exact immutable screen. Missing, substituted, malformed, or
  cross-authority markers fail before shard prewrite. This prevents an old
  marker from authorizing a changed screen without rerunning the all-cell work.
- **Threat model:** The power authority has no private signing/HMAC capability;
  it is deterministic public authority. These receipts protect normal local
  operator/concurrent-writer workflows and detect ref-bound substitution. They
  cannot attest execution against an adversary who can rewrite the complete
  local run root and forge both screen and marker bytes. No digest is claimed
  to prove computation under that stronger threat; such a threat requires a
  new reviewed signing/custody authority, not a hash patch.
- **Focused evidence:** Tests reject a tampered screen (marker absent), a
  projection/elapsed mismatch, and a forged marker; a second marker creation
  fails `O_EXCL`. `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_power.py tests/resampling_null/test_power_authority.py
  tests/test_schema_loads.py -q` passed 232 tests, followed by a passing
  project-status check and whitespace check.
- **Next gate:** A fresh locked immutable canonical screen generation must
  perform its one-time full probe. Its total-work projection, not a shard
  count, decides whether any P0 shard may start.
- **Boundary/non-claim:** No canonical screen rerun, production shard, P0
  final, provider action, spend, or scientific result occurred.

### EJ-20260730-0215 — Fresh canonical all-cell timing admission in flight

- **Action:** Started a fresh, isolated canonical screen at
  `build/research/neurips-2026-workshop/p0-canonical-timing-rerun` after the
  one-time timing-verification repair.  It sealed the same synthetic study and
  authority closure as the prior canonical attempt, then invoked the immutable
  Gaussian generation-0 screen with the manifest-bound 2,916-cell grid, 200
  screen draws per cell, and the admissible 64-shard receipt topology.
- **Observed state at this checkpoint:** The all-cell probe remains actively
  CPU-bound after more than two hours (eight threads); it has emitted neither
  `power/screen.json` nor any shard/final/descendant artifact.  Under the
  registered total-work formula, elapsed time already exceeds the largest
  possible passing timing numerator.  This is a lower-bound observation, not a
  sealed screen result: the probe must finish or fail through its own
  fail-closed path before it can be recorded as a formal P0 timing decision.
- **Gate/result:** No shard has begun and the root lock remains held.  Do not
  treat an active process, elapsed time, or this journal event as a completed
  screen, a power final, or a synthetic scientific result.
- **Boundary/non-claim:** Zero spend, provider/benchmark action, validation,
  finalization, schedule, branch, unblind, analysis, and scientific claim.

### EJ-20260730-0216 — Task-9 branch authority: opaque work-order contract

- **Action:** Added the first missing Task-5 descendant primitive:
  `OpaqueSlotWorkOrder`.  It is frozen and contains only task/snapshot,
  capability-scoped slot identity, optional private-guidance ref, public
  parent digests, and immutable branch caps; it has no arm, donor, clear-ledger,
  or peer-slot field.
- **Hostile-review finding/correction:** A worker-visible packet reference is
  an arm side channel.  The contract now requires the composite-snapshot and
  private-guidance roles and rejects `REAL`/`SHAM`/`NONE`/`RESAMPLE` labels in a
  worker-visible guidance path.  Existing packet construction currently writes
  `private-real`/`private-sham` filenames, so it cannot yet feed this worker
  contract.  This is an explicit implementation dependency, not a reason to
  relax the opacity rule.
- **Focused evidence:** A red-first controller test confirms immutable
  capability-only construction and rejects an arm-labeled guidance ref;
  `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_controller.py -q` passed, followed by a passing
  whitespace check.
- **Next gate:** Introduce a sealed opaque packet-capability view, then
  implement restore/run/attempt/task-block transactions through it.  Do not
  enable `synthetic branches` before those records are independently reviewed.
- **Boundary/non-claim:** No worker, task block, packet rewrite, provider,
  spend, benchmark execution, unblind, analysis, or P0 result occurred.

### EJ-20260730-0217 — User-authorized termination of decisive timing no-go

- **Action:** After the all-cell timing probe had remained active for more
  than two hours, the user explicitly directed its termination.  The verified
  PID was sent `SIGTERM`; it exited cleanly.
- **Reason:** The registered 200-to-20,000 draw extrapolation has a 100x
  multiplier, so a passing 43,200-second production projection requires the
  entire timing probe to finish within 432 seconds.  The live elapsed lower
  bound already exceeded that threshold by a large margin; additional compute
  could not change a passing decision.
- **Observed state:** The ignored rerun root retains only its study manifest,
  screen lock, and power authority.  It contains no screen record, verifier
  marker, shard, final, or downstream artifact.
- **Gate/result:** This is a user-authorized **non-result termination**, not a
  sealed timing-failure report or a P0 final.  The configuration remains
  inadmissible on the observed host; a formal no-go representation would need
  a separately reviewed record path.  Future decisive lower-bound no-gos must
  stop promptly, preserve state, and proceed to the next implementation gate.
- **Boundary/non-claim:** No provider/spend/benchmark action, scientific
  result, schedule, branch, unblind, analysis, or claim occurred.

### EJ-20260730-0218 — Task 6 implementation-complete / E2E-pending gate

- **Authority refresh:** Fast-forwarded the active branch from `d9cd83d` to
  `730eefd` at the user's direction, then reread the updated `AGENTS.md` and
  `CLAUDE.md`. The new explicit gate permits the exact state
  `implementation_complete; E2E_pending` only after scoped code, focused tests,
  and hostile review pass.
- **Cheap-clerk receipts:** Two bounded read-only hostile-audit attempts used
  `claude --dangerously-skip-permissions --print --model haiku --effort low`
  with maximum budgets of USD 0.30 and USD 0.18. The first task requested a
  Task-6 requirement/evidence matrix; it was manually interrupted after
  yielding no result (`claude-haiku-4-5`, actual USD 0.195186). The second
  requested at most 12 ranked Task-6 findings and exhausted its budget without
  a usable result (`claude-haiku-4-5`, actual USD 0.1912334). Total observed
  clerk cost: USD 0.3864194. Neither subprocess supplied authority or final
  verification; direct review continued.
- **Hostile-review defect and correction:** `verify_analysis_freeze` compared
  current and frozen inputs as a digest-sorted multiset of bytes. Swapping the
  contents of two named analysis inputs therefore preserved the multiset and
  could pass. A red-first regression now demonstrates the attack. The freeze
  schema and writer bind each source name to its immutable ArtifactRef;
  verification compares every named source independently and separately checks
  config and projection-schema bytes through their digest-valid refs.
- **Focused evidence:** Before the correction, `timeout 60s .venv/bin/python
  -m pytest tests/resampling_null/test_freeze.py
  tests/resampling_null/test_blinding.py
  tests/resampling_null/test_task6_state.py
  tests/resampling_null/test_artifacts.py tests/test_schema_loads.py -q`
  passed. The new regression then failed on the missing named binding and
  passed after the correction; the same focused gate passed again.
- **Status:** The canonical project manifest now records Task 6 as
  `implementation_complete` with `E2E_pending` and blocker
  `B-NEURIPS-TASK6-E2E`.
- **Boundary/non-claim:** No authority-backed P0 lineage, real unblind, paired
  analysis, provider/benchmark action, spend, scientific result, or claim was
  produced. Passing software tests establishes implementation behavior only.

### EJ-20260730-0219 — Task 6 final status and shared-surface verification

- **Status correction:** The first canonical-status encoding used overall
  system status `implemented` while retaining the honest E2E blocker. The
  checker rejected that contradiction and the missing registry entry. The
  system is now overall `partial`, with the orthogonal exact fields
  `implementation_status = implementation_complete` and
  `e2e_status = E2E_pending`; the current-state registry binds that status and
  scope.
- **Fresh verification:** The focused Task-6/schema command passed; the compact
  Linux milestone command `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null -m milestone -q` passed; `timeout 60s
  .venv/bin/python -m pytest tests/test_project_status.py -q` passed; and
  `.venv/bin/python -m pneuma_lab.status --check` plus `git diff --check`
  passed.
- **Boundary/non-claim:** This closes Task 6 implementation only. E2E remains
  blocked on a complete authority-backed P0 lineage reaching real unblind and
  paired analysis; no empirical or scientific completion is claimed.

### EJ-20260730-0220 — Codex clerk review and freeze-contract closure

- **Cheap-clerk receipt:** Ran `codex --yolo exec --ephemeral` with
  `gpt-5.6-sol` at low reasoning for the exact bounded task: inspect only the
  uncommitted Task-6 diff and return at most five concrete implementation,
  status, or E2E findings; no edits, tests, network, or authority decisions.
  The subprocess used 33,662 tokens; the CLI reported no dollar cost or
  enforceable cost bound.
- **Untrusted proposal, directly verified:** The clerk correctly identified
  that changing `source_refs` from ArtifactRef values to named bindings was a
  breaking schema change still advertised as `0.1.0`, and that the first
  regression mocked the loaded freeze rather than proving the production
  writer matched the schema. It also correctly confirmed that the E2E caveat
  remained explicit. Its warning that status prose must not outrun committed
  evidence is handled by committing the coherent verified slice before final
  handoff.
- **Red/green correction:** Added a production-writer test that passes the
  emitted record through `validate_record` and requires named bindings under
  schema version `0.2.0`. It failed against the old writer version, then passed
  after both producer and public schema were bumped to `0.2.0`. The full
  focused Task-6/schema gate passed again.
- **Boundary/non-claim:** The clerk was advisory only. No E2E lineage, real
  unblind, paired analysis, scientific result, provider action, or spend was
  produced.

### EJ-20260730-0221 — Task 7 authority, totality, and hostile-review closure

- **Cheap-clerk receipts:** A read-only
  `claude --dangerously-skip-permissions --print --model haiku --effort low`
  Task-7 contract audit exhausted its USD 0.18 maximum without output. A
  read-only `codex --yolo exec --ephemeral` audit used `gpt-5.6-sol` at low
  reasoning and was terminated by the 60-second test/process ceiling before a
  final memo; its trace independently exposed caller-selected analysis seed,
  open config constants, and non-finite schema concerns. A final diff-only
  Haiku review with a USD 0.22 maximum also hit the 60-second ceiling without
  usable output. The Codex CLI reported no enforceable dollar bound; no clerk
  supplied authority or verification.
- **Red/green authority repair:** Regressions first proved that production
  `analyze` exposed a seed, frozen config admitted altered decision constants,
  and CLI config bytes admitted a caller seed. The wrapper now reloads exact
  power/manifest authority, derives `inference-philox-v1` from study ID plus
  manifest digest, and exposes no production seed. Config constants are closed
  to the registered alpha, materiality, draw counts, and failure gap.
- **Hostile-review repairs:** Sensitivity buckets had incorrectly applied
  language/domain/issue labels to both benchmarks. They now apply only SWE
  language and TAU domain/issue-family labels, and reported leave-one estimates
  use the registered equal-benchmark renormalization. Empty deletions become
  explicit invalid uncertainty. Analysis schema `0.2.0` serializes invalid
  uncertainty as JSON null, permits quantile order zero only when no valid
  quantile exists, rejects unexpected non-finite values, and permits the honest
  empty reason list of a positive verdict.
- **Focused evidence:** Red-first tests failed on the exposed seed, mutable
  constants, caller-seed config, cross-benchmark sensitivity labels, crashing
  empty deletion, and non-JSON uncertainty. After correction,
  `tests/resampling_null/test_analysis.py` passed 30 tests. The first broad
  mixed gate reached the mandatory 60-second ceiling and was treated as no
  evidence. The narrowed analysis/power/touched-CLI/schema/status gate then
  passed at exit 0 in 5.81 seconds. The compact Linux milestone passed at exit
  0 in 5.12 seconds; project-status coherence, Python compilation, whitespace,
  and diff checks also passed. Hostile fixtures cover asymmetric benchmark
  effects, differential failure, and no-feedback label imbalance.
- **Status/boundary:** Task 7 is recorded as
  `implementation_complete; E2E_pending`. No complete P0 lineage, real unblind,
  registered analysis artifact, provider/benchmark action, spend, empirical
  result, or scientific claim was produced.

### EJ-20260730-0222 — Task 9 opaque packet capabilities and branch execution

- **Isolation from concurrent work:** Executed in a separate worktree on branch
  `task9/opaque-branch-executor`, rebased onto the committed Task-7 head
  (`4302dfe`) once that agent's tree was clean. No Task-7 statistical
  primitive, inference gate, verdict, or its tests were modified. Two shared
  files were touched by necessity and kept narrow: `cli.py` (the
  `synthetic branches` dispatch only) and `test_cli.py` (only the two tests
  that asserted the now-removed "executor is not installed" stub).
- **Sealed opaque packet-capability layer (`packet_capabilities.py`):** The
  trusted preparer converts a clear `TaskAssignment` plus `PacketPairReceipt`
  into four preregistered-order opaque grants.
  `opaque_guidance_relative_path` makes every worker-visible packet name a pure
  function of `(task_id, allocation capability digest)`, so the REAL packet
  cannot be handed to the slot allocated SHAM without detection.
  `SealedSlotCapability` closes worker reads to `WORKER_READABLE_ROLES`, which
  contains no scientific record kind; `seal_slot_capability` derives authority
  only from the work order. `SlotArtifactLoader` reads through a
  descriptor-bound `O_NOFOLLOW` component walk with mandatory digest checks.
- **Hostile-review receipts (clerk):** A read-only `codex --yolo exec` review of
  the capability layer returned seven finding categories. Confirmed and
  repaired: candidate-versus-sealed envelope identity was unchecked; entry
  `prefix_index_sha256` and `donor_task_id` were unchecked; a no-trigger marker
  could also carry packet refs; record refs were not role/media validated;
  guidance bytes were granted without being read; the delimiter-bounded
  arm-word regex admitted `private REAL.txt`, `guidance(SHAM).txt` and
  `realPacket.txt`; the reader was pathname-bound and symlink-racy. The
  arm-word gate is now a plain substring test, which is strictly stronger and
  safe because every arm word contains a non-hex character, plus a canonical
  name whitelist. Rejected as out of the documented threat model: hardlink
  aliasing of digest-pinned bytes, and forgery by a preparer that is already
  trusted with the clear ledger — both are now stated explicitly rather than
  implied. One review claim was **corrected**: REAL-versus-SHAM is not, and was
  never, hidden from the packet-bearing worker itself; the registered property
  is peer-slot and donor opacity. The module docstring previously overstated
  this and now does not.
- **Branch contracts and preparer (`branch_records.py`, `branch_controller.py`):**
  The task-block value records mirror `resampling-task-block.schema.json` field
  for field and add two bindings the schema cannot express: each execution
  receipt names its terminal receipt by digest and slot position, and the
  published `opaque_arm_id` must equal that slot's capability. The controller
  holds `prepare_opaque_work_orders`, `prepare_no_intervention_slots`,
  `seal_unscored_attempt` (preregistered slot order, never grades),
  `authorize_full_block_rerun` (byte-identical orders, validated pre-endpoint
  outage only), `finalize_failed_second_attempt`, `seal_task_block` and
  `seal_no_intervention_block`. These records live outside `types.py`
  deliberately, to stay clear of the concurrent Task-7 edits; the controlling
  plan places them in `types.py` and that file placement is an open
  reconciliation item, not a contract change.
- **Isolated branch executor (`synthetic_branch_loop.py`):** `run_opaque_slot`
  spawns one isolated environment subprocess, restores the frozen composite
  prefix snapshot, and proves snapshot identity, visible-context digest and
  token-id projection **before** the subject may emit a turn. It then drains
  the frozen pending prefix tool calls against the branch tool quota, records
  the post-pending pre-injection digests, and only then lets the optional
  packet become visible on the first post-trigger model call. It returns an
  `UnscoredSlotReceipt` that is structurally incapable of naming an outcome.
  `grade_opaque_slot` is a separate later read-only pass in a fresh disposable
  environment. Worker read authority widens in three stages, each authorized
  only by bytes the previous stage verified.
- **Registered deviations:** the final snapshot is a closed
  `branch_final_snapshot_v1` under the `composite_snapshot` role, because a
  full `CompositeSnapshotEnvelope` names roles no worker may read; branch
  requests use a `branch-request-v1` grammar that has a field for the optional
  packet; a bound model-call cap terminates as `TOKEN_CAP`, which is the
  registered unscored failure set's nearest member; `wall_clock_ms` is really
  measured and is therefore the one nondeterministic receipt field.
- **CLI:** `synthetic branches` no longer reports "synthetic branch executor is
  not installed". It performs real admission — ancestry, sealed packet
  capabilities, frozen prefix view, preregistered slot order — closes an
  untriggered task completely by copying `Y_0` to its four opaque slots, and
  for a triggered task prepares the four opaque work orders and then stops at
  the single remaining authority gate: no study manifest names the per-slot
  branch execution programs an isolated worker would replay. Inventing those
  programs in the CLI would script four slot trajectories outside frozen
  authority, so the gate is deliberate.
- **Focused evidence:** `tests/resampling_null -m milestone` passed 74 tests;
  `tests/resampling_null/test_packet_capabilities.py` passed 19;
  `tests/resampling_null/test_branch_controller.py` passed 7, of which the
  restore, digest-rejection, seed-divergence and grading tests drive real
  environment subprocesses. `scripts/test_fast.py`,
  `python -m pneuma_lab.status --check`, and `git diff --check` passed.
- **Status/boundary:** Task 9 is recorded as
  `implementation_complete; E2E_pending`. No compatible P0 final, real
  lineage, task block of record, unblind, analysis, provider or benchmark
  action, spend, or scientific claim was produced. The remaining Task-9
  dependency is manifest-authorized per-slot branch programs plus a genuinely
  admitted completed final.

### EJ-20260730-0223 — Task 9 branch-layer hostile review and repairs

- **Clerk receipt:** A read-only `codex --yolo exec` review of
  `branch_records.py`, `branch_controller.py`, `synthetic_branch_loop.py` and
  the new CLI functions returned six defect categories and one clean category.
- **Confirmed and repaired:**
  1. Four pairwise-distinct work orders were not required to be *one block*.
     A set drawn from different tasks passed both attempt sealing and rerun
     authorization. `_order_digests` now requires every block-level field
     (`study_id`, `task_id`, `benchmark`, `snapshot_ref`,
     `prefix_visible_sha256`, `packet_index_sha256`, `analysis_freeze_sha256`,
     `branch_caps`) to be identical and every slot-level identity to be
     distinct; `private_guidance_ref` is deliberately excluded because exactly
     two of four slots carry one. Rerun authorization compares the outage task
     against all four orders, not just the first.
  2. A failed-second-attempt block did not bind its four `FailedSlotReceipt`s
     to the attempt they died in. A failed receipt can never equal an attempt's
     embedded unscored receipt, so descent is now proved by reference:
     `failed_attempt_ref` must equal the selected attempt's `attempt_ref`, and
     the outage must embed this block's own first attempt.
  3. `seal_slot_capability(additional_refs=...)` accepted any allowlisted role,
     so a peer slot's `composite_snapshot` could be passed as `task_input_ref`
     and read. The generic list now refuses the two slot-identifying roles
     outright; a grading pass supplies its one legitimate second snapshot
     through a dedicated `terminal_snapshot_ref` parameter, and
     `grade_opaque_slot` first proves the receipt's slot and capability equal
     the order's.
  4. `environment_source_ref` minted an implementation identity from a
     caller-asserted digest. The referenced bytes are now read from the
     checked-out package source — the same file the spawned worker re-hashes
     against `--source-sha256` — and must reproduce the digest.
  5. `grade_opaque_slot` did not check `program.task_id == order.task_id`,
     unlike `run_opaque_slot`. It does now.
  6. `synthetic branches` published an untriggered task's block before a later
     triggered task failed admission. Admission is now a whole-run barrier:
     every task is admitted first, and nothing is written unless all pass.
- **Rejected with reasons:** the reviewer framed the adverse-zero overwrite in
  `finalize_failed_second_attempt` as admitting a readable endpoint. It does
  not: `UnscoredSlotReceipt.endpoint_readable` is structurally `False` and no
  grader runs on that path, so no endpoint was ever readable. Overwriting the
  slots that did finish with adverse zeros is the registered conservative
  behaviour of the controlling plan, and the code now says so. The narrower
  real gap — the same sealed attempt being relabelled as the second one — was
  confirmed and closed. Hardlink aliasing of digest-pinned bytes and forgery by
  an already-trusted preparer remain outside the documented trusted-run-root
  threat model and are stated rather than silently assumed.
- **Focused evidence:** four new regressions cover mixed-task work orders,
  a foreign outage task, a relabelled second attempt, and grading a peer
  slot's receipt. `tests/resampling_null/test_branch_controller.py` passed 11
  and `test_packet_capabilities.py` passed 19; `tests/resampling_null -m
  milestone` passed 78; the CLI module passed 25 excluding its pre-existing
  slow Gaussian power-screen test, which is unrelated to this slice.
  `scripts/test_fast.py`, `python -m pneuma_lab.status --check`, compilation,
  and `git diff --check` passed.
- **Boundary/non-claim:** No P0 final, lineage, task block of record, unblind,
  analysis, provider or benchmark action, spend, or scientific claim.

### EJ-20260730-0224 — Correction: one CLI test cannot complete on this host

- **Correction to EJ-20260730-0223.** That entry reported the CLI module as
  "passed 25 excluding its pre-existing slow Gaussian power-screen test". The
  exclusion was accurate but the characterisation was too generous, and the
  correction matters for Task 10's verification planning.
- **Finding:** `test_cli_power_authority_then_screen_uses_closed_authority_media_type`
  is not merely slow. It invokes `power screen` with `--phase
  gaussian_approximation --generation 0 --shard-count 64` against the
  manifest-bound grid and screen-topology refs — that is the canonical frozen
  2,916-cell all-cell screen, the same workload EJ-20260730-0215 and
  EJ-20260730-0217 already recorded as unable to finish within the registered
  budget on this host. A dedicated single-test run was given 3,000 seconds and
  was terminated by that ceiling at roughly 41 minutes of sustained ~355% CPU
  with no assertion failure and no output. It did not pass; it did not fail; it
  does not terminate in bounded time here.
- **Attribution:** pre-existing and untouched by the Task-9 slice. `git diff
  codex/neurips-2026-empirical..HEAD -- tests/resampling_null/test_cli.py`
  shows the Task-9 change is confined to the two `synthetic branches` tests;
  this test's body is byte-identical to its parent commit. The only shared
  runtime files Task 9 touches on its path are `cli.py` (confined to the
  `synthetic branches` dispatch and its imports) and `prefix_contracts.py`
  (three added controller-role entries), neither of which can affect a power
  screen.
- **Consequence:** `tests/resampling_null/test_cli.py` has no bounded green
  run of record on this host, and no Task-9 claim rests on one. The evidence
  Task 9 does rest on is the 25 remaining CLI tests, the compact milestone
  suite, and the focused branch/capability suites, all of which completed.
- **Next gate for Task 10, not Task 9:** decide whether this test should be
  marked as an opt-in tier like the other full-grid work, or reduced to a
  bounded machinery fixture. Do not silently delete it, and do not report a
  broad CLI-module pass until it terminates or is reclassified under review.
- **Boundary/non-claim:** No P0 screen, final, lineage, provider or benchmark
  action, spend, or scientific claim was produced by this observation.

### EJ-20260730-0225 — Task 8 and Task 9 integration into the empirical branch

- **Action:** Merged `task9/opaque-branch-executor` and then
  `codex/task8-timing-no-go` into `codex/neurips-2026-empirical`, both with
  `--no-ff`, in a dedicated merge worktree.
- **Conflicts:** none. Both branches fork from `4302dfe` and their file sets
  are disjoint. Task 8 deliberately opened a separate
  `35-task8-timing-no-go-temporary-handoff.md` instead of editing the shared
  journal or `34-tasks-6-10-vps-handoff.md`, and it did not touch
  `docs/project-status.json`, so the Task-9 status entry and journal entries
  merged untouched. No conflict was resolved by discarding either side.
- **Integration repair:** Task 8's three new documents each ended with a
  trailing blank line, which fails the repository's own `git diff --check`
  gate. Trimmed to a single terminating newline; no other byte of Task-8 work
  was altered.
- **Post-merge evidence:** `tests/resampling_null -m milestone` passed 78;
  `test_timing_no_go.py`, `test_branch_controller.py`,
  `test_packet_capabilities.py`, `test_controller.py`,
  `test_package_exports.py` and `tests/smoke` passed together;
  `tests/test_schema_loads.py` passed; `test_cli.py` passed 25 of 26;
  `scripts/test_fast.py`, `python -m pneuma_lab.status --check`, `compileall`,
  the 148-name package export resolution, and `git diff --check` all passed.
- **Known exclusion, unchanged by this merge:**
  `test_cli_power_authority_then_screen_uses_closed_authority_media_type`
  remains the one CLI test with no bounded green run on this host, for the
  reason recorded in EJ-20260730-0224.
- **Open item, not decided here:** Task 8 registers no system entry in
  `docs/project-status.json`. That is the Task-8 owner's status claim to make;
  it was deliberately not invented during integration.
- **Boundary/non-claim:** A merge is not evidence. No P0 screen, final,
  lineage, task block of record, unblind, analysis, provider or benchmark
  action, spend, or scientific claim was produced.

### EJ-20260730-0226 — Task 9 manifest-bound branch-program authority

- **Scope and authority:** Added the reviewed
  `resampling_branch_program_registry_v1` contract and made its reference a
  required study-manifest input. The registry freezes four programs per task
  by pre-schedule ordinal `0..3`; it does not fabricate future `slot_id` or
  allocation capabilities. Study sealing copies the registry and recursively
  verifies/copies its complete program closure before publishing the first
  scientific record. Registry task coverage must equal the frozen task
  registry and every program must bind its row's task.
- **Runtime admission:** Added a manifest-rooted resolver that fresh-reads the
  study and registry closure, validates program role/media/task/trigger
  identity, and reconciles branch ordinals to the later
  schedule/assignment-derived opaque work-order order. `synthetic branches`
  admits the complete selected task roster before starting the first worker,
  passes each resolved program to `run_opaque_slot`, seals the complete
  unscored attempt, grades each terminal receipt in isolation, and publishes
  the triggered task block. No CLI program-ref input or runtime program
  synthesis exists.
- **TDD RED:** The codec test first failed at collection because
  `branch_program_authority` did not exist. The manifest test then failed
  because a manifest without `branch_program_registry_ref` still validated.
  Resolver and CLI delegation tests failed because their entry points did not
  exist. The first shared milestone run found four direct fixture manifests
  missing the new required ref; after adding a real registry record, the next
  run correctly rejected its previously unknown authority role during fresh
  prefix-graph reconstruction.
- **Corrections from hostile verification:** The original design attempted to
  freeze later slot/capability identities in the first scientific record,
  which is circular; the committed correction uses ordinals and later exact
  reconciliation. Prefix replay now validates the branch registry record but
  treats its nested programs as future branch authority rather than importing
  them into prefix-program occurrence coverage. The full-grid CLI test remains
  excluded for the pre-existing bounded-runtime reason in EJ-20260730-0224.
- **Fresh behavior evidence:** The focused registry/CLI gate passed 22 tests;
  the branch-controller/packet-capability gate passed 30; the study-seal,
  artifact, and schema gate passed completely; and
  `tests/resampling_null -m milestone -q` passed 78 tests. The first combined
  focused command exceeded the mandatory 60-second ceiling and exited `124`,
  so it is not evidence; the split bounded commands above replace it.
- **Fresh static/status evidence:** `scripts/test_fast.py` passed 7 tests;
  `pneuma_lab.status --check`, resampling-null `compileall`, critical
  Ruff checks over the touched legacy CLI/selftest/prefix loop, full Ruff over
  the new authority module/tests, focused mypy over the new module, and
  `git diff --check` all passed. Raw mypy over `artifacts.py` remains blocked
  by pre-existing unrelated typing debt; the focused new-module command used
  `--follow-imports=skip` and is the only type-check claim.
- **Canonical state:** Removed
  `B-NEURIPS-TASK9-BRANCH-PROGRAM-AUTHORITY`. Task 9 remains
  `implementation_complete; E2E_pending` with
  `B-NEURIPS-TASK9-E2E`. The next gate is one genuinely admitted full P0
  lineage through real branch execution and a task block of record.
- **Boundary/non-claim:** No compatible P0 final, real lineage, task block of
  record, unblind, analysis, provider or benchmark action, spend, or scientific
  claim was produced.

### EJ-20260730-0227 — Task 8 reconciliation and the P0 timing-admission repair

- **Scope:** Reconciled the Task-8 temporary branch handoff into the shared
  canonical surfaces and repaired the implementation defect that made the
  frozen P0 grid inadmissible on this host. No scientific constant, RNG
  contract, grid, topology, cap, multiplier, or projection formula changed.
- **Status recorded:** `docs/project-status.json` now carries
  `neurips_resampling_null_task8` as `implementation_complete` /
  `E2E_pending` with `B-NEURIPS-TASK8-E2E`, and
  `src/pneuma_lab/status.py` admits the new canonical system id. Task 8 had
  registered no system entry before this entry; the Task-8 owner's claim was
  deliberately not invented during the 2026-07-30 merge (EJ-20260730-0225).
- **Preserved non-result:** EJ-20260730-0215, EJ-20260730-0217, and the
  terminated all-cell rerun remain non-result terminations. No
  `resampling_timing_no_go` record was created: the historical run emitted no
  machine-verifiable monotonic-clock termination evidence, and fabricating the
  readings is forbidden. The ignored rerun root still holds only a study
  manifest, screen lock, and power authority.
- **Measured defect:** A fresh instrumented all-cell measurement on this host
  projected about 2,740 seconds of total registered screen work against the
  432-second admissible threshold (100x multiplier, 43,200-second cap). The
  cost was concentrated in three places that are pure functions of frozen
  inputs recomputed per replicate: the 96-node Gauss-Hermite rule and the
  latent-Gaussian 16-pattern table (about 72% of the simulator), the
  `Fraction`-based sharp-tail dynamic program (about 82% of the Task-7 batch
  gate), and per-draw `np.random.Philox` allocation at 18.7 microseconds each
  against 1.5 microseconds to reseed.
- **Correction (commit `87a013b`):** memoized the pattern table and quadrature
  rule; carried the randomization support as integer numerators over the
  common denominator `lcm(4*n_SWE, 4*n_TAU)`; regrouped the tail convolution
  only when a lattice bound proves no sequential prefix can reach
  `_DYNAMIC_STATE_LIMIT`, cached on its sufficient statistic; cached `r95` on
  `(roster, discordant)`; reseeded one per-thread Philox behind a documented
  single-use internal entry point while `philox_generator` stays the public
  non-aliasing constructor; cached field-independent text admission and
  replaced the per-character digest scan with a regex.
- **Equivalence evidence:** A detached worktree at the pre-change commit
  `75bb096` and the corrected tree produced byte-identical per-cell
  `(gate_totals, replay_receipt)` digests for 20 grid-spread cells across the
  `screen`, `grid`, and `validation` draw domains. A 120-tensor differential
  check against a re-derived `Fraction` oracle, including unequal rosters,
  found no mismatch. `tests/resampling_null/test_kernel_equivalence.py` pins
  the tails, resolution, Philox stream, shared-slot aliasing, cached text
  admission, and digest admission permanently.
- **Fresh measurement after repair:** all-cell screen work about 275 seconds
  (simulator about 153 s, Task-7 gate about 121 s) on the same host, whose
  load average was 8.5 on 8 cores from unrelated resident processes. The
  admissible threshold is 432 seconds.
- **Verification:** `tests/resampling_null -m milestone` passed 92;
  `test_analysis.py` and `test_power.py` passed 48; the branch/packet/
  controller/export gate passed 35; `scripts/test_fast.py` passed 7;
  `tests/smoke` passed 7; `pneuma_lab.status --check`, resampling-null
  `compileall`, Ruff over the four touched files, and `git diff --check` all
  passed. Every command stayed under the 60-second ceiling.
- **Boundary/non-claim:** This is an implementation correction plus a status
  reconciliation. No screen, shard, validation, power final, schedule, branch,
  task block, unblind, analysis, provider or benchmark action, spend, or
  scientific claim was produced.

### EJ-20260730-0228 — First admitted P0 screen and full-grid execution

- **Run root:** `build/research/neurips-2026-workshop/p0-lineage-20260730`
  (git-ignored). Study manifest
  `67dad43634c59bdf97050bcb2433f34fca1bb8c4bde708665439205fa741e623`,
  byte-identical to an independently materialized fixture root, which
  re-proves the study seal's determinism.
- **Authority:** `power/authority.json`
  `09d7cb2a240abd7027fe5654b8a40ac6d719bb39ef4fe40784a3149c73c08c98`,
  `synthetic_validation` kind. No roster-bound or confirmation authority was
  minted.
- **Screen admitted:** `power/screen-gen0.json`
  `122cbcab3b12bd56547b9aca48092cc8b14b02a82b4433d423a41d3982ff8b88`,
  phase `gaussian_approximation`, generation 0, shard count 64. The all-cell
  timing probe executed the frozen 2,916 cells at 200 screen-domain datasets
  each through the same Task-7 gate as production, committing
  `replay_receipts_sha256`
  `97090bd6c7862d7f6b230398e6891744979bc504075312308c25b4d17cc1ad9b`. Measured
  probe work was 320.0036 seconds; the registered total-work projection is
  32,001 seconds against the frozen 43,200-second cap, i.e. 74% of budget with
  no parallelism discount applied. Wall time for the command was 5:20.84 at 99%
  of one core.
- **Significance:** this is the first admitted P0 screen of record in the
  project. The prior 2026-07-30 attempts (EJ-20260730-0215, EJ-20260730-0217)
  could not be admitted and were terminated without artifacts; the difference
  is the implementation correction in EJ-20260730-0227, not any change to the
  grid, topology, multiplier, cap, or projection formula.
- **Grid execution:** the 64 frozen shards are executing through
  `scripts/run_p0_shards.sh`, which is a bounded-concurrency wrapper around the
  committed `power simulate` CLI route and adds no scientific input. Shards are
  independent immutable attempt identities, so concurrency is an execution
  convenience only; the cap was already charged against the complete sequential
  workload before admission. First-wave shards took 642-665 seconds each at
  five workers. Host load averaged 8.5-19 on 8 cores throughout, from unrelated
  resident processes.
- **First observed outcomes:** shard 0 reports `execution_complete: true` at
  the frozen 20,000 datasets per cell, with `causal_pass_count: 0` on its
  leading `alternative` cells. At the synthetic fixture roster of 20 SWE plus
  20 TAU tasks, the registered causal gate does not fire even under the
  registered alternative. That is a real P0 observation about the synthetic
  configuration, not a defect, and it is exactly what the null-tier
  `CONDITIONAL_ONLY` synthetic arm exists to represent. It is not a claim about
  the real C120/C160 confirmation rosters.
- **Boundary/non-claim:** no selection, validation, power final, schedule,
  prefix, assignment, packet, task block, unblind, analysis, provider or
  benchmark action, spend, or scientific claim exists at this entry. A screen
  is an admission to execute, not a result.

### EJ-20260730-0229 — Canonical P0 execution stopped by explicit scope correction

- **Action:** The user directed that the canonical full-grid execution stop and
  that canonical screens and production shards be reclassified as
  experiment-only workloads. All shard processes and both drivers were killed
  at 17:56 local. Shard artifacts are written atomically, so the interrupted
  shards left nothing behind.
- **Preserved state (not to be deleted, rewritten, finalized, analyzed, or
  claimed):** `build/research/neurips-2026-workshop/p0-lineage-20260730`
  holds the study manifest, the `synthetic_validation` power authority, the
  admitted screen `power/screen-gen0.json`, and exactly 10 of 64 production
  shards (`shard-gen0-00` through `shard-gen0-09`).
- **Classification:** this is an **incomplete non-result caused by an explicit
  scope correction**. It is not a no-go, not an infeasibility, and not a
  result. The timing admission passed decisively (320.0036 s measured against
  the 432 s decisive threshold; 32,001 s projected against the 43,200 s cap),
  so nothing about this stop reflects on feasibility. `_complete_shards`
  requires all 64 shards at the frozen 20,000 datasets, so no selection,
  validation, or power final exists or may be constructed from these 10.
- **Reclassification adopted:** canonical full-grid screens and canonical
  production shards are **explicitly authorized experiment-only workloads**.
  They must never appear in bounded software or integration gates, must never
  block implementation completion, and require a per-run authorization. The
  autouse guard added in commit `2d4fe8d` enforces the test-surface half of
  this rule.
- **Deviation:** `scripts/run_p0_shards.sh` was edited while bash was
  executing it, which killed both drivers at about 17:33 and cost roughly 20
  minutes. Execution was restarted detached from immutable copies under
  `build/step4/`. No artifact was affected; only wall time was lost.
- **Next:** Step 4A is a separate miniature production-path lineage in a fresh
  run root, using tiny structurally equivalent fixtures through the same real
  authority, scheduling, opaque-branch, task-block, freeze, projection,
  unblind, and analysis machinery, labeled implementation verification only.
  Step 4B, the canonical authority-backed lineage, stays pending for the
  actual experimental phase.
- **Boundary/non-claim:** no power final, schedule, lineage, task block,
  unblind, analysis, provider or benchmark action, spend, or scientific claim
  exists.

### EJ-20260730-0230 — Step 4A bounded implementation-verification attempt

- **Scope/authority:** Ran `scripts/run_iv_lineage.sh` only with a fresh
  implementation-verification root and the separate miniature grid. No
  canonical full-grid screen, canonical shard, model/provider call, cloud
  resource, paid compute, or P0 record was invoked.
- **Execution:** The launcher was repaired for Linux output-parent creation and
  explicit implementation-verification authority sealing. Fixture continuity
  repairs bound implementation descriptors to the actual reviewed source,
  made the synthetic lane explicitly simulator-free with zero simulator caps,
  supplied reconstructible synthetic grade/verifier evidence, and admitted the
  manifest-owned source roles to fresh candidate replay. Focused CLI checks
  passed (`27` cases).
- **Receipts:** Fresh root
  `build/research/neurips-2026-workshop/step4a-iv-20260730-194008` produced
  implementation-verification authority
  `ce5771c1e9107668b9749f30ea22e9d15a897602d9cb207da2fe853667fcdb41`, power
  final `a90e4edfeaa8bd30b6e86204c36b4c15f5493397ba0ab6cf60e67fa1ce8a377d`,
  and schedule `614254eb39b3e9e3b74a4a2453d3165b28679fcdf076f774d4c4d8815016b567`.
- **Terminal outcome:** Prefix candidate fresh-graph replay failed closed on
  the upstream `power_contract` role outside the copied prefix authority
  namespace. No prefix index or downstream artifact was emitted. Step 4A did
  **not** reach registered analysis. This is implementation verification only,
  not scientific evidence, not a P0 result, and not a claim of failure in the
  scientific protocol.
- **Next:** Repair the narrow power-contract namespace boundary, then rerun
  from another fresh implementation-verification root. Defer broad hostile
  campaigns and exhaustive forensic sweeps to the dedicated pre-experiment
  launch review.

### EJ-20260730-implementation-verification-lineage-follow-up

- **Scope/authority:** Used only fresh `implementation_verification` roots and
  the miniature frozen fixture grid. No canonical P0/full-grid screen, model
  or provider call, cloud resource, paid compute, or admissible scientific
  record was used.
- **Focused repairs:** Added the controller-owned verifier source/report/
  feature chain while preserving raw verifier execution provenance; declared
  its receipt/schema edge; repaired Linux-safe isolated projection shaping and
  trusted reconstruction; corrected analysis-freeze tuple unpacking; and
  supplied a distinct external analysis fixture. These were execution/contract
  continuity repairs only.
- **Latest receipts:** Fresh root
  `build/research/neurips-2026-workshop/step4a-iv-20260730-203436` produced
  power final `f6073ab0a88625eb0dbe936be31f6cd9b5e87b27e98f71d5fbdad6a1cd8938e2`,
  schedule `79a09dfb8121f7b820d62ad7a1ad56eeca753fa569f529d9f933f7c6fe092c31`,
  prefix index `337e997ae6002a1ea5067157e11b9eba275f0473814f76e7961bba4b83409205`,
  assignment `5c9e64520c2ca8df2ad840df9cfe6be603d083cd4e263503a7fbb37c9683c275`,
  packet index `619107c1651702b599e4be6456250b4b0f7d68fac0d4ba110daf91d6bef36819`,
  freeze `8e3fa835a107a5c4a8753270f85e642f5d89995212a9f2dec4cdc29759cf258a`,
  and projection `2f10c83e119db898bc9e103eb246a6ad6da539930a3001029678d3d48f4ba735`.
- **Terminal outcome:** Isolated branch execution and blinded projection
  completed. Gated unblind reached the registered analysis builder, which
  failed closed on the finite-critical-value precondition because the
  no-trigger miniature fixture has zero outcome variance. Step 4A **did not
  reach registered analysis**. This is implementation verification only and
  produces no scientific evidence or P0 result.
- **Checks:** Focused CLI contract tests passed; broad adversarial campaigns
  and exhaustive forensic sweeps were intentionally deferred to the dedicated
  pre-experiment launch review.

### EJ-20260730-implementation-verification-lineage-complete

- **Scope/authority:** Fresh root
  `build/research/neurips-2026-workshop/step4a-iv-20260730-210059` used only
  the separate `implementation_verification` authority and miniature frozen
  grid. No canonical P0/full-grid screen, model/provider call, cloud resource,
  paid compute, or scientific evidence was used.
- **Complete path:** Power final, schedule, prefixes, assignment, opaque
  packets, isolated branch execution, task blocks, analysis freeze, blinded
  projection, gated unblind, and registered analysis all completed with exit
  code `0`.
- **Receipts:** Power final
  `238c2a8838c03698ca18a8b9690efd9f5b98930333b1c9f3eea2e047c5e861ef`,
  schedule `8bee0c62c19968da3018913c3a9a2a14318cdb6457eaf84fe47dfcf26ffdc66d`,
  prefix index
  `a465778eed719d9c4b1909256a7b874532670dfe1c2152ff47f4a1234d812d34`,
  assignment `47a322b523447d64468a0d6fd37239b38f773428eff2f748856baa4274eb37a`,
  packet index `c2502f0c4467246787f1be8721b4679ba7db699d56524aa5c75409237f03b97a`,
  freeze `b30f59452aa6bfb91f45d4f4aed300181d7696f16a5fb2ba42aabadb84e3f89a`,
  projection `84dab953889ffef52cfad93f40f4c6e48b41ff928c3553b55c2e5f057756acef`,
  and registered analysis
  `b21ef75c1b2b7bbbd90937483d66b7f3363d4a2314dbfcaa8645371fc591b38e`.
- **Classification:** Step 4A reached registered analysis, but the entire
  lineage is implementation verification only and cannot enter P0/scientific
  evidence. Focused CLI tests and status checks passed; broad hostile review
  remains deferred to the dedicated pre-experiment launch review.

### EJ-20260731-task6-step5-revalidation

- **Scope/authority:** Re-read the preserved Step 4A root
  `build/research/neurips-2026-workshop/step4a-iv-20260730-210059` only. No
  lineage runner was invoked, no Step 4B action occurred, and no provider,
  cloud, paid, or canonical P0 work was performed.
- **Exact bounded check:**
  `timeout 60s .venv/bin/python - <<'PY' ... validate_scientific_graph(root); verify_frozen_analysis_inputs(ref, run_root=root) ... PY`
  exited `0`. It loaded and hash-checked the study, schedule, prefix index,
  assignment, packet index, analysis freeze, blinded projection, unblind
  receipt, and registered analysis records. `validate_scientific_graph` and
  `verify_frozen_analysis_inputs` both passed.
- **Receipt identity:** Freeze
  `b30f59452aa6bfb91f45d4f4aed300181d7696f16a5fb2ba42aabadb84e3f89a`,
  projection
  `84dab953889ffef52cfad93f40f4c6e48b41ff928c3553b55c2e5f057756acef`,
  unblind receipt
  `c1142f4d4e19a7ccdbc098e8f4f22df1ac4f49af3ef58ba7e7ed291e5d94108a`, and
  analysis
  `b21ef75c1b2b7bbbd90937483d66b7f3363d4a2314dbfcaa8645371fc591b38e` matched
  the preserved records. The durable
  `operational/task6/outcome-tainted.json` marker is present.
- **Classification:** This revalidates the Task 6 implementation path against
  the completed miniature lineage only. It does not remove
  `B-NEURIPS-TASK6-E2E`, promote Step 4A to scientific evidence, or establish
  a P0 result; Step 4B remains pending.

### EJ-20260731-task6-step5-revalidation-command-receipt

- **Receipt correction:** The preceding entry's bounded-check line was a
  compact notation, not a literal shell transcript. The exact command was:

  ```bash
  timeout 60s .venv/bin/python - <<'PY'
  import hashlib
  from pathlib import Path
  from pneuma_lab.resampling_null.artifacts import load_record, validate_scientific_graph
  from pneuma_lab.resampling_null.freeze import verify_frozen_analysis_inputs
  from pneuma_lab.resampling_null.types import ArtifactRef
  root = Path('build/research/neurips-2026-workshop/step4a-iv-20260730-210059')
  paths = ['study-manifest.json','prefix-schedule.json','prefix/prefix-index.json','assignment/ledger.json','packets/index.json','analysis/freeze.json','analysis/projection.json','analysis/unblind-receipt.json','analysis/analysis.json']
  records = {rel: load_record(root / rel) for rel in paths}
  validate_scientific_graph(root)
  p = root / 'analysis/freeze.json'; b = p.read_bytes()
  ref = ArtifactRef(role='analysis_freeze', relative_path='analysis/freeze.json', sha256=hashlib.sha256(b).hexdigest(), byte_count=len(b), media_type='application/json')
  verify_frozen_analysis_inputs(ref, run_root=root)
  assert (root / 'operational/task6/outcome-tainted.json').exists()
  print('PASS')
  PY
  ```
- **Result:** Exit `0`, output `PASS`. This receipt is read-only and remains
  implementation verification only; no Step 4B or scientific execution was
  performed.

### EJ-20260731-task7-step4a-revalidation

- **Scope/authority:** Re-read the preserved Step 4A root
  `build/research/neurips-2026-workshop/step4a-iv-20260730-210059` only. No
  lineage runner, unblind, projection, provider, cloud, paid, or canonical P0
  action occurred, and Step 4B was not run. The Step 4A records remain
  implementation verification only and inadmissible as scientific evidence.
- **Exact command:**
  `timeout 120s .venv/bin/python scripts/research/task7_step4a_continuity.py`
  from the repository root. Exit `0`, final line `PASS`. The script is a
  one-off forensic receipt, not a delivery gate and not part of any test tier.
- **What it verified against the completed registered analysis:**
  - `validate_scientific_graph` still binds the whole preserved record DAG.
  - `require_schedulable_power_final` still admits the preserved power final
    (`schedule_authority=implementation_verification`, `selected_tier=None`,
    40 selected task ids).
  - The frozen analysis-config bytes hash-match their `config_ref`, parse into
    the exact registered `AnalysisConfig` (alpha `0.05`, delta* `0.05`,
    sharp draws `999999`, multiplier draws `99999`), and carry no seed.
  - Manifest-owned inference randomness is continuous: the seed the current
    `manifest_inference_seed` derives from the preserved manifest ref,
    `0xc915d2f169f54fd1` = `14489719310441074641`, is exactly the seed recorded
    in the preserved primary and secondary simultaneous bounds; mutating the
    manifest digest or the study id diverges the seed.
  - Roster ancestry: the manifest `roster_ref` bytes hash-match and cover every
    selected task (40 of 40, `synthetic_fixture`).
  - Live vocabulary parity: running the unmodified `analyze` statistical core on
    three synthetic hand-fixture rows in memory reproduces the preserved
    record's 12 gate codes in identical order and the identical 16-key result
    payload shape. The three admission I/O seams
    (`require_schedulable_power_final`, `_load_direct_scientific_parent`,
    `_verify_roster_rows`) were shimmed in-process exactly as
    `tests/resampling_null/test_analysis.py` shims them; the probe wrote no
    artifact and never touched the Step 4A root.
  - Outcome totality: `reasons` is exactly the unmet gates in gate order; all
    12 recorded gates' `passed` values recompute from their own
    observed/comparator/threshold; and rebuilding the recorded contrasts,
    resolution, and secondary family and re-running the live `classify_verdict`
    returns the preserved `UNRESOLVED_RESAMPLING` across all 19,683
    reconstructions of the nine JSON-null (non-finite) uncertainty fields.
  - `row_count` 40 equals the projection record's `expected_task_count`, its row
    count, and the selected-task count; projection bytes hash-match.
- **Focused tests:** `.venv/bin/python -m pytest
  tests/resampling_null/test_analysis.py -q` → 30 passed, exit `0`.
  `.venv/bin/python -m pneuma_lab.status --check` → PASS.
- **Known limits (not papered over):** nothing here re-derives the Step 4A
  estimates, p-values, bounds, or resolution values from task-block data — the
  clear analysis rows exist only transiently during unblind, so numeric
  reproduction is impossible without re-running the lineage. Gate arithmetic is
  checked for internal consistency against its own recorded observed/threshold,
  and the non-finite reconstruction proves the recorded verdict is forced by the
  record, not that the record's numbers are correct. The Step 4A draws are the
  implementation-verification-capped 999, not the frozen production draws.
- **Classification:** This revalidates the Task 7 implementation path against
  the completed miniature lineage only. It does not remove
  `B-NEURIPS-TASK7-E2E`, does not promote Task 7 or Step 4A to scientific
  evidence, and establishes no P0 result. Step 4B remains pending.

### EJ-20260731-task6-step4a-revalidation

- **Scope/authority:** Re-read the preserved Step 4A root
  `build/research/neurips-2026-workshop/step4a-iv-20260730-210059` only. No
  Task 6 lineage step and no Task 6 closure occurred: nothing froze, sealed,
  permitted, unblinded, tainted, locked, or published. Step 4B was not run, and
  no provider, cloud, paid, or canonical P0 action occurred. The Step 4A records
  remain implementation verification only and inadmissible as scientific
  evidence.
- **Exact command:**
  `timeout 180s .venv/bin/python scripts/research/task6_step4a_continuity.py`
  from the repository root. Exit `0`, final line `PASS`. The script is a one-off
  forensic receipt, not a delivery gate and not part of any test tier. It
  captures a `(path, size, mtime_ns)` inventory of all 1,392 run-root files
  before any live code runs and re-asserts it identical at the end.
- **What it verified against the preserved Task 6 records:**
  - `validate_scientific_graph` passes, and `validate_preunblind_graph` passes
    with exactly one assignment ledger at `assignment/ledger.json` (no alias).
  - `verify_frozen_analysis_inputs` accepts the freeze's own bytes
    (`b30f59452aa6…`, 2,056 bytes) and fails closed on a mutated `sha256` and on
    a mutated `byte_count`, so the pass is not vacuous.
  - All three frozen inputs (source, config, projection schema) live under
    `sources/analysis-freeze/` and are byte-identical to their refs; the freeze
    binds `packets/index.json` as a `resampling_packet_index` at
    `stage=sealed` with a matching `study_id`.
  - Blinded-projection continuity is re-derived, not merely re-read: the pure
    `projection_candidate.build_candidate` run over the 40 preserved schedule
    slot IDs and the 40 preserved task blocks' slot outcomes reproduces the
    recorded `projection_candidate_sha256` `597fd15ebcf0d85a…` exactly.
  - Blindness holds: all 40 rows expose only `A`–`D` labelled slots with the
    closed five-key outcome, and the raw projection bytes contain no
    `opaque_arm_id`/`arm_id` and no clear arm token.
  - Gated unblind: the receipt's `projection_ref`, `analysis_freeze_ref`, and
    `assignment_ledger_ref` equal refs recomputed from those files' own bytes,
    `expected_task_count=40` matches the projection, the analysis record binds
    the receipt's own byte-derived ref (the paired-publication invariant), and
    `operational/task6/paired-publication.json` is absent.
  - Durable taint still fails closed under today's code:
    `operational/task6/outcome-tainted.json` is present with payload
    `{"state": "outcome_tainted_v1"}`, `require_preunblind_context` raises for
    all three protected actions while passing for an unprotected one, and
    `require_singleton_absent` raises for both run-wide singleton kinds.
  - Chain coverage: `task-blocks/*.json` = `task_block_refs` = projection rows =
    distinct schedule tasks = `analysis.row_count` = `expected_task_count` = 40;
    projection row order equals frozen schedule order; every block binds
    byte-identical freeze and schedule refs.
- **Focused tests:** `.venv/bin/python -m pytest
  tests/resampling_null/test_freeze.py tests/resampling_null/test_blinding.py
  tests/resampling_null/test_task6_state.py
  tests/resampling_null/test_publication.py -q` → 57 passed, exit `0`.
- **Known limits (not papered over):** `prefix_success` is an outcome rather
  than a schedule field, so the candidate rebuild takes it from the task blocks
  and `build_candidate`'s prefix cross-check is block-internal, not
  schedule-versus-block. The permit's `permit_hmac_sha256` cannot be recomputed
  without the unblind secret and the permit path. The clear ledger-to-analysis
  join is not re-derived — that join is the unblind step itself.
  `verify_current_analysis_inputs` was not run because it requires the original
  external source paths, which live outside the preserved root.
- **Classification:** This revalidates the Task 6 implementation path against
  the completed miniature lineage only. It is not Task 6 closure. It does not
  remove `B-NEURIPS-TASK6-E2E`, does not promote Task 6 or Step 4A to scientific
  evidence, and establishes no P0 result. Step 4B remains pending.

### EJ-20260731-task10-release-preparation

- **Scope:** bounded Task-10 release-preparation implementation only. Added a
  sealed-root release inspector, independent byte-closure rehash, external
  content-addressed package manifest, and explicit terminal classifications.
  The surface labels implementation verification and synthetic fixture failures
  `not_a_scientific_result`; a future canonical GO or registered no-go remains
  `requires_step4b_release_authorization`.
- **Fixture verification:** copied (without modifying) the preserved bounded
  Step 4A root to a temporary local directory, sealed that copy, and ran
  `artifacts verify` plus the independent `artifacts inspect` path. The copied
  root classified as `implementation_fixture` with terminal decision
  `IMPLEMENTATION_VERIFICATION_ONLY`; it was not promoted or cited as a result.
- **Focused commands/results:** `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_release.py
  tests/resampling_null/test_cli.py::test_cli_artifact_inspection_uses_the_independent_release_reader
  tests/resampling_null/test_cli.py::test_cli_artifact_package_requires_an_external_destination -q`
  passed 7 checks. `timeout 60s .venv/bin/python -m pytest
  tests/resampling_null/test_s02d_prefix_index.py -q` passed 4 checks after
  correcting the stale test-only tokenizer authority shape. `timeout 60s
  .venv/bin/python -m pytest tests/resampling_null -m milestone -q` passed all
  93 checks. `git diff --check` and `.venv/bin/python -m pneuma_lab.status
  --check` passed.
- **Boundary:** no Step 4B, canonical P0 work, provider/benchmark action,
  cloud/AWS use, paid compute, spend, or scientific/causal claim occurred.
  This journal entry is a release-preparation slice, not a Task-10 scientific
  completion claim.

### EJ-20260731-task10-bounded-resume-runner

- **Implementation:** `selftest --resume-after-power` now composes the existing
  sealed controller commands for schedule, prefix index, assignment, packet
  build/audit, freeze, isolated branches, projection, paired unblind/analysis,
  and optional artifact-root seal/verify. It requires external schedule seed,
  32-byte assignment key, analysis source root/source names, config, and schema;
  every external input resolves before the first schedule write.
- **Focused proof:** the preflight-refusal and complete nine-command descendant
  sequence tests passed, together with all release tests (8 passed). A fresh
  temporary `implementation_verification` study successfully sealed authority,
  Gaussian screen/shards/selection/validation, fallback screen, and fallback
  shards. Its fallback validation was terminated by the mandatory 60-second
  process ceiling before publishing an artifact, so no completed final or
  descendant was produced from that temporary root.
- **Disposition:** Task 10 is `implementation_complete; E2E_pending`. The
  release machinery can independently inspect/package a future sealed canonical
  lineage and classify a registered no-go, but no Step 4B lineage, canonical P0
  result, provider/benchmark action, cloud/AWS use, paid compute, spend, or
  scientific claim occurred.

### EJ-20260731-step4-design-freeze

- **Scope:** Phase B Step 4 documentation and authority records only.
  `38-experiment-design-freeze.md` ratifies the existing design by reference,
  registers `G-ROSTER`, and records the four-rung topology ladder plus its
  gate-only selection rule. DL-149 resolves the Azure wording for an AWS-only
  pilot without authorizing an Azure slice.
- **Verification:** the clean Phase-A precondition and project-status schema
  check passed; whitespace check passed after repair. The journal checker was
  run and correctly exposed its inherited `EJ-20260729-0170` to
  `EJ-20260730-0171` contiguity defect, so it is recorded as a failed forensic
  check rather than a passing Step-4 receipt. The status record reports
  `implementation_complete; E2E_pending` and retains roster, launch-review,
  and execution blockers.
- **Boundary:** no external input was retrieved; no provider, benchmark,
  model, cloud, quota, provisioning, paid-compute, Step 4B, pilot, or scientific
  execution occurred. The feasibility gate remains a real blocker, not a prose
  caveat.

### EJ-20260731-step5a-input-lock

- **Scope:** local Step 5A contract implementation. Added the two registered
  cloud-manifest schemas, strict validators, and an offline retrieval-plan
  derivation over synthetic immutable receipts.
- **Verification:** focused cloud manifest/input tests, schema registry tests,
  Ruff, status validation, and whitespace check passed. The inherited journal
  contiguity failure remains outside this slice.
- **Boundary:** no real input receipt, lookup, pull, mirror, provider action,
  cloud resource, spend, Step 5B, Step 4B, pilot, or experiment occurred.

### EJ-20260731-step6-aws-architecture

- **Scope:** static Step 6 implementation. Added the architecture manifest,
  tier-agnostic Batch/IAM Terraform declarations, and local policy-boundary
  checks.
- **Verification:** focused architecture/IaC fixture tests and Ruff passed.
  Terraform is absent, so its binary-dependent test recorded an explicit skip;
  it is not an L1 pass. The inherited journal contiguity failure remains
  outside this slice.
- **Boundary:** no AWS credential, account-bound plan, provider API call,
  quota action, resource creation, apply, reservation, spend, pilot, Step 4B,
  or experiment occurred.

### EJ-20260731-step7a-image-recipes

- **Scope:** static recipe/manifest implementation only. Three fixture-pinned
  role recipes, dependency lock shapes, deterministic build instructions, and
  image-manifest validation were added.
- **Verification:** focused image-recipe tests, schema registry tests, Ruff,
  status validation, and whitespace checks passed.
- **Boundary:** all bases resolve to `registry.invalid`; no pull, image build,
  SBOM, image digest, external receipt, provider action, spend, Step 5B/7B,
  pilot, or experiment occurred.

### EJ-20260731-step8-orchestration

- **Scope:** local Step 8 lease, shard, and reconciliation implementation.
- **Verification:** focused orchestration tests, mypy, schema registry tests,
  status validation, and whitespace checks passed.
- **Boundary:** no cloud scheduler, lease store, storage service, provider call,
  resource, retry, resume, execution, or spend occurred.

### EJ-20260731-step9-spend-protection

- **Scope:** local reservation, approval, projection, and watchdog contracts.
- **Verification:** focused spend tests, Ruff, schema registry tests, status
  validation, and whitespace checks passed.
- **Boundary:** no live price/balance receipt, alarm, provider, resource,
  reservation, authorization, execution, or spend occurred.

### EJ-20260731-step10-security-controls

- **Scope:** local binding, worker environment, Class-B reference, journal, and
  wording-control implementation.
- **Verification:** focused security tests, Ruff, schema registry tests, status
  validation, and whitespace checks passed.
- **Boundary:** no secret retrieval, cloud worker, image, provider action,
  execution, or spend occurred.

### EJ-20260731-step11-emulation

- **Scope:** T1 local fault-matrix and network-forbid guard.
- **Verification:** focused emulation test, Ruff, status validation, and
  whitespace checks passed.
- **Boundary:** no botocore dependency, AWS request, provider resource,
  execution, or spend occurred; T2/T3 remain pending.

### EJ-20260731-step12-deployment-preflight

- **Scope:** local quota preflight, environment configuration, and ownership
  manifest teardown planning.
- **Verification:** focused preflight tests, Ruff, status validation, and
  whitespace checks passed.
- **Boundary:** no deployment, resource query, teardown, provider action,
  execution, or spend occurred.

### EJ-20260731-step13-pilot-protocol

- **Scope:** protocol-only pilot ceiling, rung, and non-efficacy selection
  implementation.
- **Verification:** focused pilot tests, Ruff, schema registry tests, status
  validation, and whitespace checks passed.
- **Boundary:** no pilot authorization, provider action, resource, execution,
  scientific result, or spend occurred.

### EJ-20260731-phase-b-readiness-audit

- **Scope:** read-only final audit of Steps 5B/7B authorization readiness and
  Phase B state.
- **Result:** no applicable positive hash-bound NeurIPS authorization, real
  input receipt, real image/SBOM receipt, or account-bound cloud receipt exists.
  Implementation preparation through Step 13 is complete; external/authority
  gates remain open.
- **Boundary:** no retrieval, build, provider action, cloud resource, paid
  execution, pilot, Step 14, Step 4B, or scientific claim occurred.

### EJ-20260731-placebo-paper-and-adversarial-review

- **Scope:** paper-track and review-track implementation on an isolated
  worktree/branch (`codex/placebo-paper-review`), merged as `e701d7d`.
  Adds `src/pneuma_lab/adversarial_review/` (twelve-role hostile rejection
  review, fail-closed input contract, evidence grounding, conflict detection,
  dissent-preserving synthesis, falsification chair, hash-bound disposition),
  `src/pneuma_lab/placebo_paper/` (fail-closed result-to-paper pipeline),
  `paper/placebo_protocol.tex` (pre-results double-blind manuscript), and
  `schemas/adversarial-review/`.
- **Rebrand:** public naming applied to shared surfaces under DL-160. No
  package, schema `$id`, record kind, receipt field, artifact identity, or
  historical decision row was renamed. `schemas/project-status.schema.json`
  gained one additive optional `public_naming` block.
- **Verification:** 84 focused tests across `tests/adversarial_review` and
  `tests/placebo_paper` passed; default smoke gate passed; schema-load tests
  passed; `python -m pneuma_lab.status --check` PASS.
- **Known state:** the paper preflight BLOCKS, which is correct — no arm has
  run, no evidence package exists, and the closest-prior-art citation
  ("Try Again, Don't Look Back") is recorded `unresolved` in
  `paper/placebo/citation-queue.json` rather than cited from memory. No LaTeX
  toolchain is installed, so the manuscript is uncompiled and all PDF-level
  checks report `pending`, never `pass`. The Step 14 campaign spec is prepared
  and fails closed for want of sealed transcripts.
- **Boundary:** no hostile campaign was run, no cloud or paid resource was
  used, no experiment input was retrieved, the preserved incomplete P0 root was
  not touched, and no Step 4B, unblind, analysis, or scientific claim occurred.

### EJ-20260731-single-l40s-topology-amendment

- **Input:** user supplied an AWS Support notice reporting partial approval of
  8 G/VT vCPUs in us-east-1 and directed a smaller experiment topology. The
  notice does not identify whether the applied quota is On-Demand, Spot, or
  both. The user also reports USD 10,000 of Azure credits incoming; no official
  balance or eligibility receipt was supplied.
- **Decision:** DL-161 prospectively selects one `g6e.2xlarge`/L40S with
  sequential arm/replica execution. The scientific contract is unchanged; the
  old 48-vCPU requirement is treated as concurrency architecture, not sample
  size. Existing Terraform remains unreconciled.
- **Boundary:** documentation only. No account query, provider action, resource,
  retrieval, build, spend, smoke, pilot, training, Step 4B, experiment, result,
  or claim occurred. Azure remains verified spendable 0.00 until official
  evidence is recorded, and any Azure training/other experiment requires a
  separate design and authority lineage.

### EJ-20260731-aws-single-l40s-reconciliation

- **Scope:** DL-161 static AWS-topology reconciliation. The cloud architecture
  validator, quota preflight, pilot protocol, schemas, Terraform configuration,
  fixtures, status, and handoff now bind exactly one 8-vCPU `g6e.2xlarge` with
  one L40S and 44 GiB usable device memory. The Terraform admission definition
  reserves one GPU, eight vCPUs, and 60,000 MiB host memory.
- **Verification:** focused cloud and schema-registry tests passed (with the
  explicit Terraform-on-PATH test skipped by design), Ruff for
  `src/pneuma_lab/cloud`, status validation, whitespace check, and Terraform
  L1 `fmt -check`, backend-free `init`, and `validate` passed.
  The provider was initialized only to validate configuration; no credentials,
  account plan, provider read, resource change, or `apply` occurred.
- **Research correction:** current upstream material describes the Qwen3.6
  FP8 variant at roughly 42 GiB and single-GPU validation on H100/H200 rather
  than L40S. Community reports are mixed and include tool-call and thinking
  failure modes. These are admission risks, not a substitute for a receipt.
- **Boundary:** no Step 5B retrieval, G-ROSTER qualification, Step 7B image
  build, AWS account/quota request, Docker pull/build, one-GPU measurement,
  pilot, Step 14 campaign, experiment, Azure action, or spend occurred.

### EJ-20260731-phase-b-external-evidence-preflight

- **Implementation:** Step 5B retrieval planning now includes tokenizer,
  dataset, and verifier sources and byte-verifies every referenced receipt.
  Step 7B has a complete three-role, two-build, SBOM, and reproducibility
  receipt contract. AWS account evidence has an offline validator binding STS
  identity, both applied G/VT quotas, account-visible `g6e.2xlarge` zones, and
  Terraform config/plan digests. Step 14 generation now requires all five real
  Phase B evidence receipts and writes nothing while any are absent.
- **Tooling/evidence:** AWS CLI 2.35.19 was installed user-locally after the
  installer signature matched AWS's documented fingerprint; GPG reported that
  signing key expired, which remains a trust-chain caveat. Terraform 1.15.8 was
  checksum-verified and installed user-locally. Terraform L1 init/validate and
  all focused cloud/schema tests passed. The first STS read failed with
  `NoCredentials`; no account data was obtained.
- **Resource gate:** the sole writable disk has about 153 GiB free versus the
  historical 321–470 GiB retrieval estimate. Pending request 50 names exact
  A1–A3 scopes and hashes, but authorizes nothing.
- **Boundary:** no input or image retrieval, container build, AWS mutation,
  Terraform plan/apply, quota change, GPU use, reviewer campaign, experiment,
  Azure action, or spend occurred.

### EJ-20260731-aws-authenticated-console-audit

- **Scope:** fresh read-only inspection of the authenticated AWS console in
  `us-east-1`; no account, quota, or resource mutation was attempted.
- **Identity:** the console account name and 12-digit account identifier matched
  the expected Jerry Mathos AI account. The identifier is retained in the
  private console evidence and is not copied into this public-facing journal.
- **Quota evidence:** Service Quotas reported applied account-level values of
  8 vCPUs for `Running On-Demand G and VT instances` and 16 vCPUs for
  `All G and VT Spot Instance Requests`. Both satisfy the exact 8-vCPU
  `g6e.2xlarge` topology gate.
- **Offering evidence:** the EC2 instance-type detail page reported
  `g6e.2xlarge` in `us-east-1a`, `us-east-1b`, `us-east-1c`, and
  `us-east-1d`, with 8 vCPUs, one NVIDIA L40S, and 44.7 GiB GPU memory.
- **Residual gate:** this read-only console evidence does not supply CLI
  credentials, a principal ARN receipt, Terraform variables, or an
  account-bound Terraform plan hash. A same-session CloudShell `sts` read
  subsequently confirmed the root-principal ARN. The account exposes a
  default VPC with subnets in the available zones and its default security
  group, but `dynamodb list-tables` and `s3api list-buckets` both returned
  empty sets. The required lease table and artifact bucket do not exist, so a
  real plan cannot be prepared without a separately authorized infrastructure
  creation decision.
- **Boundary:** no quota request, launch, Terraform plan/apply, provider
  mutation, resource creation, GPU use, experiment, Azure action, or spend
  occurred.

## 2026-07-31 — Step 5B workflow and the G-ROSTER evaluation

- **Scope:** isolated worktree/branch (`codex/step5b-groster`). Adds
  `schemas/cloud-retrieval-authorization.schema.json`,
  `schemas/cloud-qualification-audit.schema.json`,
  `src/pneuma_lab/cloud/retrieval.py`, `src/pneuma_lab/cloud/qualification.py`,
  `fixtures/cloud/`, `tests/cloud/test_retrieval.py`,
  `tests/cloud/test_qualification.py`, and
  `docs/research/neurips-2026-workshop/51-step5b-retrieval-and-qualification.md`.
- **Evaluation (DL-163):** both tiers are `FEASIBILITY_NO_GO`. Against the
  current-metadata proxy, C120 requires 11 C and 16 C++ root lineages versus 9
  and 14, and C160 requires 14 C versus 9.
- **Correction made under hostile review — recorded because it changes the
  conclusion.** The first draft of this work claimed the inequality was
  *unsatisfiable by any audit outcome*, reasoning that qualification only
  filters the proxy pool. Independent hostile review showed the premise is
  unsound: the DL-128 proxy filters present-day repository metadata, while the
  registered eligibility criterion is base-commit licence evidence. A repository
  archived or unlicensed today may still be admissible at its pinned base
  commit, so the proxy is not an upper bound on eligibility. The draft had also
  hard-coded that premise as a validation error, which would have made the one
  finding capable of overturning the verdict impossible to record. Both are
  fixed: records now declare `proxy_basis`, monotonicity is enforced only for
  `base_commit_admissible`, and the shortfalls are reported
  `provisional_unsatisfiable`. The strong claim is withdrawn.
- **Other hostile-review repairs:** the human signature is now a binding digest
  over the record (it was unverified free-text hex); the roster gate now
  requires resolvable evidence bytes and the bound input-lock digest (a
  hand-written JSON file previously reached `CONDITIONALLY_FEASIBLE`); verifier
  sources are now a retrieval scope (they were silently omitted); mirror paths
  are kind-scoped and collision-checked; the receipt plan binds the lock; and
  the byte ceiling is checked before each declared fetch.
- **Consequence for sequencing:** Step 5B and G-ROSTER are genuinely coupled.
  The base-commit admissibility enumeration that settles the roster question is
  Step 5B's licence audit, so the roster cannot be closed from a desk.
- **Read-only corroboration (CL-027):** public sources corroborate 743 tasks /
  381 repository strings for SWE-bench-Live MultiLang and the τ² domain counts
  (airline 50, telecom 114, banking 97). The per-language lineage breakdown is
  **not publicly published**, so the 9 C / 14 C++ proxy remains internal CL-009
  evidence; no response artifact was committed for that check, so it is
  unrecomputable by a reviewer and independent re-derivation stays pending.
- **Second hostile review and further repairs.** A second independent review
  found the roster gate still reachable from a hand-written record, `FEASIBLE`
  accepting the weak `current_repository_metadata` basis it argues cannot bound
  eligibility, and `build_audit_plan` silently skipping the benchmark
  `dataset_revision` and `task_manifest_sha256` — the very bytes the roster
  counts derive from. Fixed: `FEASIBLE` now requires
  `base_commit_admissible`; the gate recomputes the lock digest from a supplied
  lock instead of trusting a caller string; the dataset revision and task
  manifest are planned and verified; and `require_complete_scopes` refuses an
  authorization that would leave a pinned input unretrieved. The gate's residual
  limit — it is a consistency check, not an authenticity check, satisfiable by
  whoever writes both the record and the evidence files — is now stated in the
  docstring, in doc 51, and pinned by a test named for what it actually proves.
- **Verification:** `tests/cloud` and `tests/test_schema_loads.py` pass on this
  branch except `test_iac_plan.py::test_terraform_binary_check_is_explicitly_skipped_when_absent`,
  which `pytest.fail`s whenever a terraform binary is on PATH; that test is
  unmodified here and its outcome is environmental. `ruff check` is clean on the
  new modules and tests; the default smoke gate and
  `python -m pneuma_lab.status --check` pass. Two independent hostile reviews
  were run and every BLOCKING and MAJOR finding was repaired before commit.
- **Boundary:** no external input was retrieved, no registry/provider/account
  was contacted, no image or dataset byte was pulled, no meaningful storage was
  consumed, no manifest was promoted, no roster was weakened, no credit was
  spent, and no Step 4B, pilot, unblind, analysis, or scientific claim occurred.
  The committed authorization record is an unsigned candidate bound to a
  synthetic fixture lock and grants nothing.
## 2026-07-31 — Authenticated Step 5B readiness

- **Scope:** isolated worktree/branch (`codex/step5b-authenticated-readiness`).
  Adds `schemas/cloud-approver-key-registry.schema.json`,
  `schemas/cloud-licence-audit.schema.json`,
  `src/pneuma_lab/cloud/{authorization_keys,input_lock,licence_audit,iac}.py`,
  tau2 qualification fixtures, and focused tests; revises
  `cloud-retrieval-authorization` to 0.2.0 and `cloud-qualification-audit` to
  0.2.0.
- **Checkout reconciliation (prior commit `7bc7ad9`).** Two lines of work had
  descended from `d0b7fdd`: the pushed Step 5B/G-ROSTER commits and an unpushed
  working tree that had reconciled the DL-161 single-L40S topology into code,
  schemas, Terraform, and quota preflight. Both were genuine and both were
  merged; the pre-merge tree is preserved on the local backup branch
  `backup/dirty-worktree-20260731-130853` (`c3f9721`). **`3e2d825` had truncated
  `34-tasks-6-10-vps-handoff.md` from 870 to 513 lines**, dropping the VPS start
  commands, the Task 8/9/10 checkpoints, the execution-class policy, the Step
  4A/4B definitions, and the canonical-run-stopped notice. All of it was
  restored. DL-161 appeared on both sides describing the same decision at two
  stages and was merged into one row citing both 49-* documents; no decision was
  renumbered.
- **Authentication (DL-164).** The DL-162 binding digest is replaced by Ed25519
  over the complete canonical body, verified against a key enumerated in advance
  in the committed registry, with validity-window, revocation, and expiry checks
  and a ledger-row content binding. The registry names one real key generated in
  the user's CloudShell by a separately authorized session; **this lineage did
  not perform that key ceremony and cannot attest to private-key custody.**
- **Arithmetic correction (DL-165).** `fixed_reserve` and the C160
  `hamilton_allocation` now fail closed when no authority has fixed them,
  instead of defaulting to 0 — the one substitution that can only make the gate
  easier. A registered floor (`registered_minimum_units`) outranks the
  inequality where the design states one directly.
- **Family separation (DL-166).** SWE and tau2 qualify different units on
  different evidence; the promotion gate now requires both and refuses a
  single-family submission.
- **Two independent hostile reviews were run and every finding repaired before
  commit.** Review 1 (can an unauthorized byte move?) found that ISO-8601
  timestamps were compared as **strings** while the schema permits fractional
  seconds; because `.` sorts below `Z`, `…T00:00:00.001Z` compared as *earlier*
  than `…T00:00:00Z`, so an authorization that had expired a millisecond
  earlier verified as live. Timestamps are now parsed to instants. Review 1 also
  found that the byte-ceiling controls — pre-fetch declared-size refusal and the
  post-fetch backstop — had lost **all** test coverage when the retrieval tests
  were rewritten for the authenticated signature; that coverage is restored.
  Review 2 (does the record system overclaim?) found tau2 C160's registered
  "at least 47 qualified airline tasks" was not modelled at all, understating
  that split by twenty tasks against a quota-plus-pilots reading of 27.
- **Verification:** `tests/cloud` and `tests/test_schema_loads.py` pass (455
  cases) in the isolated worktree; `ruff` is clean on every new and revised
  module and test; `python -m pneuma_lab.status --check` and `git diff --check`
  pass. The Terraform environmental test now exercises the absent-binary branch
  against an isolated empty search path and the present-binary branch against a
  mock one, so it is deterministic whether or not terraform is installed; the
  real `fmt -check` remains an honestly skipped environmental check.
- **Residual limitations, stated because they are load-bearing.** A verifying
  signature is not proof of a person: no hardware binding, threshold, or
  transparency log exists, and revocation is only as fresh as the last commit.
  The qualification gate remains a **consistency** check, not an authenticity
  one — whoever writes both the audit record and its evidence files can satisfy
  it. `real_candidate` classification speaks only to the *form* of an identity;
  it does not establish that the identity exists or that any byte was fetched.
  No licence-audit record exists, and CL-009/DL-128 proxy prose is explicitly
  refused as qualification. The tau2 one-pilot-per-split shape is a modelling
  assumption in the conservative direction.
- **Boundary:** no external input or image retrieval, registry/provider/account
  contact, container build, cloud mutation, Terraform plan or apply, quota
  change, GPU use, credit spend, pilot, Step 4B, unblind, analysis, reviewer
  campaign, Azure action, or scientific claim occurred from this lineage. The
  `pneuma_lab.cloud` package imports no network, provider, or subprocess module,
  so it cannot retrieve by construction. Separately authorized concurrent
  sessions operating on the primary checkout did perform AWS bootstrap work;
  that work is theirs, is recorded in their own documents, and is not part of
  this branch.
### EJ-20260731-step5b-execution-safety-repair

- **Trigger:** pre-promotion review of the authenticated Step 5B slice reported
  three launch-blocking authority issues and three portability failures. All six
  were reproduced and are closed here; none was disputed.
- **Caller-controlled authorization time (P1).** The execution gate accepted an
  `at` string from its caller, which made expiry advisory: replaying an expired
  authorization needed nothing more than passing an earlier in-window instant.
  `require_authorized` and `retrieve_and_verify` no longer take an evaluation
  instant at all; validity resolves through `trusted_now`. An injected clock
  remains available as a **test seam** and a test asserts the parameter is
  absent from both signatures. Honest limit: `trusted_now` is trusted only in
  the sense that it is not caller-supplied — it is still host time, and binding
  validity to an external time authority or a countersigned execution receipt
  would close that gap and is not implemented.
- **Ceiling enforced after spending (P1).** `declared_sizes` was optional and
  fetcher-supplied, so an arbitrarily oversized object could transfer in full
  before the post-fetch check rejected it. Sizes are now **authenticated**:
  `cloud-input-lock` 0.2.0 pins `size_bytes` per receipt plus
  `task_manifest_size_bytes` and `manifest_size_bytes`, and the lock digest sits
  inside the signed authorization body, so a size is approved rather than
  declared. The whole plan is checked against the ceiling before the first byte
  moves, and the fetch boundary now yields chunks so each one is counted as it
  arrives. A flooding fetcher is cut off within one chunk of its authenticated
  size, which a test pins.
- **Receipts named unwritten files (P1).** `mirror_path` was returned but never
  written or reopened. Bytes now stream to a staged file, are fsynced and
  atomically installed at the mirror path, then **reopened and rehashed
  independently** — not reusing the streaming digest — before a receipt is
  emitted. Receipts carry `installed_path` and `size_bytes`; an occupied
  destination is refused rather than overwritten; a failed transfer publishes
  nothing, which a test verifies by asserting the mirror is empty.
- **Portability.** Provenance digests bound raw checkout bytes, so a CRLF
  checkout invalidated every committed hash on Windows. `cloud/provenance.py`
  canonicalizes text (UTF-8, LF, BOM-stripped) before hashing, matching the
  content Git stores for a normalised text blob; the refresh script, the licence
  audit's self-binding, and the provenance tests all use it. Every repository
  document read in tests now specifies `encoding="utf-8"` rather than the
  platform default. The Terraform mock stub is created as `terraform.bat` on
  Windows, since an extensionless file is correctly not an executable there.
- **Verification:** `tests/cloud` and `tests/test_schema_loads.py` pass (466
  cases), and **the entire suite was re-run against a simulated CRLF checkout of
  the design freeze, decision log, spend ledger, and both bound modules, and
  passed unchanged**. The Terraform tests pass both with a real binary on PATH
  and with `PATH` emptied. Ruff is clean on every new and revised module and
  test; the default smoke gate, `python -m pneuma_lab.status --check`, and
  `git diff --check` pass.
- **Boundary:** no external retrieval, registry/provider/account contact, image
  or dataset pull, container build, cloud mutation, Terraform plan or apply,
  quota change, credit spend, pilot, Step 4B, unblind, analysis, manifest
  promotion, or scientific claim occurred. The committed authorization is still
  an unsigned candidate bound to the synthetic fixture lock, so the repaired
  retrieval path remains unreachable. C120 and C160 remain
  `FEASIBILITY_NO_GO` and nothing was weakened.

## 2026-07-31 — Human-readable unattended low-risk authority

- **Decision:** DL-168 permits one readable, tightly bounded standing envelope
  for cheap retrieval, non-scientific smoke, or API-pilot work. The committed
  policy is inactive and authorizes nothing.
- **Implementation:** added its closed schema, admission module, candidate
  fixture, registry entry, and focused tests. No external action occurred.

## 2026-08-01 — C160 AWS substrate and immutable worker receipts

- **Authority:** DL-169 records the user's root-MFA exception and preserves all
  non-MFA scientific, cost, image, qualification, and admission gates.
- **AWS substrate:** plan SHA-256
  `86aa19def10af6f1a334c1558f39d0d69271f6bef94292d43954aeca705a6ba2`
  was applied only for the private non-compute substrate. Because AWS requires
  a new Batch compute environment to be born enabled, Terraform now gates the
  compute environment, queue, and job definition behind
  `create_batch_resources=false`. Direct queries returned no environment or
  queue. State SHA-256 is
  `78e36e9659e7f0eee41881b68c6382f22306c83a16ef9e698b2d4e0e0a5b7cdf`.
- **Step 5B evidence:** selection SHA-256
  `8d6c3bc3dd332a7a0998a31b22ab2f46395889d9ada74d2c1d187bba797ff114`
  binds 176 repositories, all with full OCI manifest/config/layer receipts and
  zero unresolved entries. Encrypted bundles are recorded under CL-031.
- **Worker image:** CodeBuild
  `pneuma-c160-worker-build:36ed3cce-b613-4b98-811b-730270ec4cac`
  produced ECR digest
  `sha256:1fc54d73f9ec36356bec5c2c8497b671f72a9e43c0bae4fbb84be3ee6ede9ae2`.
  Its completed ECR scan has an empty severity map. Full scan-response SHA-256
  `122dbb5176582d1e066aa1a36a44fb21785b7555d34a16d1eaa2a7f9ffa299ad`
  is mirrored encrypted at
  `s3://pneuma-phase-b-892077329800/receipts/ecr/c160-noffmpeg-1fc54d73f9ec-scan.json`.
- **Boundary:** no Batch environment, queue, EC2 instance, EBS worker volume,
  GPU smoke, model inference, pilot, canonical experiment, analysis, or result
  promotion occurred.

## 2026-08-01 — Cross-platform receipt portability gate

- **Implementation:** added a canonical receipt-bundle contract and offline
  verifier. It binds the validated input lock, a complete ordered SWE/tau2
  G-ROSTER audit set, and exact copied receipt payload identities using UTF-8,
  terminal LF, fixed UTC time, canonical relative POSIX paths, and SHA-256.
- **Verification:** `python -m pytest tests/cloud/test_portability.py -q` passed
  2 cases on Windows; module compilation, `git diff --check`, and
  `python -m pneuma_lab.status --check` passed. Fixtures prove input/record
  ordering cannot change sealed bytes and CRLF payload drift is rejected.
- **Boundary:** no upstream refetch, AWS operation, Docker/GPU/CUDA action,
  scientific execution, spend, or result promotion occurred. A real sealed
  bundle has not yet produced matching Windows/Linux receipts; E2E remains
  pending.

### E2E completion

- Windows sealed the synthetic input lock, both C160 proxy roster records, and
  the existing immutable C160 selection receipt. Local verification emitted
  bundle `e655584c668f67375f7f1ef8eb4c31554501af3c21ad7b2704646f2595326d94`,
  G-ROSTER `fe76744fa51f35ce64ae206f8734b014e01abf7aa0de970312ea112b60c393c2`,
  and input-lock `bfe5848f3858e7648938428616e5ac81ef7c0ea9e6a2b597a1506e8f1597d2c3`.
- The exact ZIP bytes were uploaded to authenticated AWS CloudShell in account
  `892077329800`, region `us-west-2`. Linux matched archive SHA-256
  `c6c3bcbc979051a8306b1f86b515436938c2babbd808c4e9db00a57fbc6239b4`
  and independently reproduced all three digests above. The machine-readable
  comparison is `evidence/portability-e2e-20260801.json`.
- **Status:** cross-platform portability is E2E-complete for this exact
  implementation-verification proxy lineage. The input lock is synthetic and
  the rosters are proxies; real input authority, qualified G-ROSTER, Docker,
  isolation, CUDA, throughput, interruption, and durability remain pending.

## 2026-08-01 — Concrete preparation-admission authority

- **Finding:** documents 48 and 51 required a signed
  `cloud_preparation_admission`, but the repository contained no schema,
  validator, or execution gate for that record.
- **Implementation:** added closed preparation-envelope and one-action admission
  schemas plus a two-signature/two-ledger verifier. It binds the exact envelope,
  action, provider/region, input lock, manifest, prior cumulative spend and
  history digest, projected cost, retries, teardown protection, and expiry.
- **Verification:** focused authority and schema-registry tests pass (292
  cases); Ruff, project status, and whitespace checks pass.
- **Boundary:** no envelope or admission was signed and no AWS action, resource,
  retrieval, build, GPU use, pilot, experiment, or spend occurred.

## 2026-08-01 — Step 5B inventory bootstrap freeze

- **Implementation:** added a closed `cloud_input_inventory_plan` contract and
  deterministic generator for the eight frozen upstream roles. The plan permits
  immutable tree/LFS/OCI metadata discovery only and explicitly forbids
  payload, weight, layer, and experiment execution.
- **Candidate:** `fixtures/cloud/input-inventory-plan-candidate.json`, canonical
  SHA-256 `c817eff762d1ebdeef30956bb719a06c67e30c79e8619777a0e78ddc70ae8c4f`,
  AWS `us-east-1`, zero-dollar ceiling, one retry.
- **Correction:** the live Step 5B record now acknowledges the already-produced
  local 743-task/724-pair licence audit, 176-lineage selection, and complete OCI
  metadata while refusing to promote those ignored bytes without a real input
  lock and exact admitted qualification records.
- **Boundary:** no authority was signed and no metadata query, payload fetch,
  model pull, image-layer pull, provider mutation, GPU action, pilot, experiment,
  or spend occurred.

## 2026-08-01 — Step 7B executable-surface audit

- **Finding:** the repository has a real hardened qualification-worker image
  and a static three-role receipt contract, but the controller, model-server,
  and benchmark-worker recipes remain `registry.invalid` fixtures. More
  importantly, no production cloud-controller or benchmark-worker entrypoint
  exists for those images to run.
- **Correction:** repaired the readiness audit's false claim that CL-028 is a
  signed operative preparation envelope. CL-028 is a zero-spend local contract
  record; no signed envelope or action admission is committed.
- **Boundary:** no recipe was laundered into production status, and no image
  pull/build/push, SBOM generation, provider action, GPU use, pilot, experiment,
  or spend occurred.

### Fail-closed launch-gate repair

- Added a sixth mandatory Step 14 input: an E2E-qualified production execution
  surface covering the controller, model server, and benchmark worker. Image
  receipts can no longer satisfy launch review while their executables are
  absent.
- Focused regression pins the new receipt path and exact six-receipt set.

## 2026-08-01 — Step 5B exact signing ceremony prepared

- Added pending ledger rows CL-034/CL-035 and a CloudShell-only two-stage
  ceremony. It signs the zero-dollar envelope first, binds the admission to the
  resulting exact envelope digest, then independently verifies both signatures,
  ledger rows, plan, provider/region, retry ceiling, and spend history before
  writing a package.
- The script accepts only the existing registered Ed25519 private key; it never
  generates or prints key material. PEM, raw 32-byte, and 64-hex encodings are
  supported.
- Hostile portability review caught raw Markdown hashing before commit. Spend
  history now hashes canonical UTF-8/LF text, and LF/CRLF parity is tested.
- **Boundary:** both ledger rows remain pending exact user signature. No key was
  accessed, no authority signed, and no provider action or spend occurred.

## 2026-08-01 — CloudShell approver-key rotation

- **Finding:** after exact action approval, authenticated CloudShell account
  `892077329800` contained no persistent file or environment handle for the
  registered `pneuma-b1-20260731` private key. The earlier custody statement
  was false and that identity could not sign.
- **Authorized repair:** the user explicitly approved rotation. CloudShell
  generated Ed25519 key `pneuma-b1-20260801-r1` at `2026-08-01T08:09:10Z`;
  private PEM `~/.pneuma/approver-20260801.pem` is mode 0600 and remains there.
  Only public key `666953e2e6aaea11366280608b1b5cebe7641b6a9518b36ea9b14e65d361f932`
  and a non-secret private-file checksum were observed outside CloudShell.
- **Governance:** the lost identity is revoked before any preparation action;
  the rotation is the only active registry key. No action has yet been signed.

## 2026-08-01 — Step 5B metadata inventory executed E2E

- **Authority:** user-approved zero-dollar plan SHA-256
  `c817eff762d1ebdeef30956bb719a06c67e30c79e8619777a0e78ddc70ae8c4f`.
  Oregon CloudShell signed and independently verified envelope body
  `d580345e47c7fee1575126a027011474e86f8d3fdfca0dd8400af8173d1d0494`
  and admission body
  `d6bedd4fd1795694070465d2a8d0119b266111280d822f149c93deb16f80918a`.
  The public signing package is exact-byte SHA-256
  `e7bce1acf98e60fa66ecf88b6810e04f02dd3382923be40a2899d2908e98c073`;
  the private key never left Oregon CloudShell.
- **Execution surface:** before action execution, AWS STS returned account
  `892077329800` and root ARN `arn:aws:iam::892077329800:root`; both
  `AWS_REGION` and `AWS_DEFAULT_REGION` were `us-east-1`. The transferred
  executor bundle independently matched SHA-256
  `5e6dd0b9a3360aeffa0dac53b415309bffbb8505058550f1c3e5a7142b5911a2`.
- **Result:** the first and only attempt completed at `2026-08-01T08:49:04Z`.
  Canonical receipt
  `evidence/step5b-inventory-metadata-20260801.json` is 373,712 bytes with
  SHA-256 `ce9274cdb0825f93e52fec7a30b5210253f92289c4ae43bf4b922efa138f9452`:
  eight exact frozen roles, 1,762 metadata entries, and eight response pages.
  Local verification reproduced the plan/source ordering, identity formats,
  unique per-source paths, canonical bytes, and receipt digest.
- **Boundary:** this is inventory metadata, not an input lock. Ordinary Git/HF
  blobs carry Git SHA-1 identities rather than downloaded-byte SHA-256, so a
  separately signed payload retrieval remains necessary. No payload, weight,
  dataset blob, OCI layer, instance, GPU, pilot, experiment, or spend occurred.

## 2026-08-01 — Step 5B payload-manifest derivation

- **Contract repair:** added a distinct `cloud_payload_retrieval_manifest`
  contract so pre-retrieval upstream identities cannot masquerade as a final
  SHA-256 input lock. Object IDs, ordering, consumers, identity algorithms,
  gitlink treatment, counts, and byte totals are all recomputed.
- **Derivation:** exact metadata receipt
  `ce9274cdb0825f93e52fec7a30b5210253f92289c4ae43bf4b922efa138f9452`
  deterministically produced canonical manifest digest
  `1f738eff8667f0b863cdd8259c7bfa071ec3a37b2d9963e999f11e7dda1087e4`.
  Its 1,762 entries collapse to 1,706 unique objects because the subject model
  and tokenizer share 56 exact objects. One SWE gitlink resolves to the frozen
  RepoLaunch role, leaving 1,705 retrievable objects and an exact authenticated
  byte ceiling of 67,483,211,374 bytes.
- **Boundary:** the manifest authorizes nothing and is not a final input lock.
  No payload byte, network request, provider action, GPU job, experiment, or
  spend occurred.

## 2026-08-01 — Step 5B payload-action candidate

- **Candidate:** deterministic plan digest
  `18f8edebbcb9e394259b1d7e0afc4d92cc01c05f933f871ead4fcf094330511a`
  binds manifest `1f738eff8667f0b863cdd8259c7bfa071ec3a37b2d9963e999f11e7dda1087e4`,
  1,705 objects, 67,483,211,374 bytes, AWS account `892077329800`, and
  `us-east-1`.
- **Controls:** exact content-addressed prefix under the encrypted, versioned,
  lifecycle-governed artifact bucket; 35-day retention maximum; one action
  retry; USD 5.00 hard ceiling; exact upstream/S3 hosts; and explicit bans on
  compute provisioning, GPU use, model loading, container/experiment execution,
  and result promotion.
- **Fail-closed state:** `pricing_receipt_sha256` is null, therefore status is
  `candidate`, not `ready_for_signature`. No signature, authority, network,
  provider mutation, reservation, or spend occurred.

## 2026-08-01 — Step 5B payload action 001 stopped fail-closed

- Exact plan `9334ffeb...4606a` was signed in authenticated AWS account
  `892077329800`; signing-package SHA-256 is `1b97f4b1...22a1d`.
- Attempt 1 stopped before payload transfer because Botocore selected legacy
  `s3.amazonaws.com`; the signed regional endpoint boundary rejected it.
  The sole authorized retry set AWS's regional-endpoint control.
- Attempt 2 safely installed and reread 31 content-addressed objects totaling
  22,384,787 bytes, then stopped when Docker redirected to the observed but
  unlisted `production.cloudfront.docker.com`. No host-boundary bypass occurred.
- AWS independently regenerated the Git ZIP as `d3ba28...a228`, differing from
  Windows `03e1ff...e7550` because `git archive --format=zip` carries
  platform-specific container metadata. The LF-normalized executor-source
  digest matched exactly on both systems and remains the portable authority.
- Successor action 002 adds only that observed CDN, retains the same destination,
  lifecycle, USD 5 ceiling, and one retry, and binds executor surface
  `fbaf4793...0ade`; plan digest is `53dc77c9...e088`. Existing objects will be
  HEAD/GET verified rather than overwritten.

### Action 002 public-dataset namespace failure

- Action 002 signing package SHA-256 was `5372ebe3...f518`. Its first attempt
  resumed successfully and advanced the verified mirror to 83 objects totaling
  3,443,039,872 bytes.
- It then stopped on HTTP 401 for frozen object `0b1d3a...c803f`. Inspection
  proved the repository is public; the executor had generated a model URL
  `huggingface.co/<repo>/resolve/...` instead of the dataset URL
  `huggingface.co/datasets/<repo>/resolve/...`.
- The correction is consumer-specific: only `swe_dataset` receives the datasets
  namespace; subject/simulator model URLs remain unchanged. A focused regression
  covers both routes. Successor action 003 binds executor `b4377bf9...a9617`
  and plan `eca7d02e...a2215`. No substitute data or credential bypass is used.

## 2026-08-01 — Step 5B live S3 price qualification

- **Official source:** AWS Price List AmazonS3 `us-east-1` offer version
  `20260728131000`, published `2026-07-28T13:10:00Z`, exact source SHA-256
  `6568366729d8ec8a581178a35204d18cab66c009eecc9745c2e417ce8e17cae6`.
  Extracted rates are USD 0.023/GB-month S3 Standard, USD 0.000005 per
  Tier-1 request, and USD 0.0000004 per Tier-2 request.
- **Recomputed bound:** 72 billable copy-days cover 35 current, 30 noncurrent
  retry, and 7 abandoned-multipart days. Request ceilings cover 5,542 PUT-class,
  3,410 LIST, and 13,640 GET-class operations. Worst case rounds upward to USD
  3.78 under the USD 5.00 ceiling. Canonical pricing receipt SHA-256 is
  `386cb5c1906fa6e8b93b8b05dc19534d18ea97a3a581f11f2cc9d86d9db6709f`.
- **Ready record:** the price-qualified plan is
  `fixtures/cloud/payload-retrieval-plan-ready.json`, canonical digest
  `e2a2869d75b6596804075f208fc48227979b6e1f2a55f1ee2aacd02368267542`.
  `ready_for_signature` is a mechanical state, not authority. No signature,
  provider mutation, reservation, payload retrieval, or spend occurred.

### Receipt-PUT and lifecycle correction

- Hostile executor review found CL-039 omitted the final receipt PUT from each
  allowed action attempt and assumed a 35-day bound while the live general
  `runs/` lifecycle is 365 days. Neither defect is acceptable in signed bytes.
- Corrected pricing receipt SHA-256 is
  `a0eaa16b4d431ffbba6ae160d65d910927830afbbb1b52dc3b82bea2009e4a5c`,
  with 5,544 PUT-class requests; rounded worst-case cost remains USD 3.78.
  Corrected ready-plan digest is
  `b06f2a9e629960e1844b227fd7188c06b3be1461da9c08db833063b5fbc467c8`.
- Terraform now declares an overlapping, narrower
  `runs/step5b/payloads/` lifecycle: current <=35 days, noncurrent <=30, and
  incomplete multipart <=7. This is implementation only; until an exact
  account-bound plan/apply proves the rule live, payload execution fails closed.

## 2026-08-01 — Step 5B payload executor implementation

- **Code binding:** ready plan digest
  `6b5a87e38e4b003497b9ece033576d0dc486e27fb6ecc8e6c74c8f2d1afc6fab`
  binds portable executor-surface digest
  `33a85fd0381fc896aef98b6d53941878f32148047360b764d6c2daf3e29e0493`.
  The surface includes the entrypoint, all cloud Python contracts, all cloud
  schemas, and package/schema loaders; CRLF/LF differences normalize to LF.
- **Streaming invariants:** HTTP Content-Length and encoding are checked before
  transfer; Git blobs use `sha1("blob <size>\\0" + bytes)`, while LFS/OCI use
  SHA-256. Small bytes verify before PUT. Multipart bytes verify before Complete;
  failure aborts the upload. S3 bytes are then independently reread to compute
  final payload SHA-256 before a receipt can exist.
- **Resume/security:** content-addressed keys use conditional publication;
  existing objects must match size, AES256, versioning metadata, upstream
  identity, and a full reread. Redirects are restricted to signed hosts and
  cross-host redirects strip authorization. The executor verifies STS account,
  region, bucket public-access/ownership/encryption/versioning, and the exact
  35/30/7 lifecycle before the first payload request.
- **Receipt:** closed schema and offline verifier recompute the exact 1,705-item
  roster, keys, upstream identities, SHA-256 values, byte sum, action/manifest/
  pricing bindings, and request ceilings. Focused tests passed; no live network,
  provider mutation, authority, payload, reservation, or spend occurred.

## 2026-08-01 — Account-bound Step 5B lifecycle plan

- **Pre-plan rejection:** comparison against exact applied config/state found
  the new lifecycle block accidentally nested under the S3 encryption resource.
  Local string tests had missed the invalid HCL because Terraform is absent on
  Windows. The block was moved into the lifecycle resource and a structural
  regression now rejects that placement error.
- **Lineage:** authenticated account `892077329800`; provider region
  `us-east-1`; Terraform 1.15.8 / AWS provider 5.91.0; exact pre-plan state
  SHA-256 `78e36e9659e7f0eee41881b68c6382f22306c83a16ef9e698b2d4e0e0a5b7cdf`.
  The lifecycle-only config was derived from the exact applied config, excluding
  unrelated later disabled-Batch implementation drift.
- **Plan:** binary SHA-256
  `b8f0e95a05051ca4ba05eeb7bcf6316d0ad57834c71723435915095aca9fd243`;
  JSON `037609810584d2c5d23238afa3556493bd23107080fe1b64678c9ecfaba95b07`;
  text `8bac0518dc7e346d79a132c34bc83a519e98e7100921ef8a3f1046ecc2876bb4`.
  Exactly 0 add, 1 in-place update, 0 destroy. The old `runs/` 365/30/7 rule
  remains and exact `runs/step5b/payloads/` 35/30/7 is added.
- **Live boundary:** direct readback still returned only the old lifecycle rule.
  The plan remains stored in CloudShell and was not applied. Incremental cost is
  zero; no mutation, payload retrieval, reservation, or spend occurred.

### Payload-readiness state correction

- The payload plan previously called itself `ready_for_signature` while the
  lifecycle it depends on remained unapplied. That label could permit signing
  before the retention guarantee existed, even though runtime would later
  refuse execution.
- The contract now has distinct `lifecycle_apply_pending` state and binds both
  Terraform plan SHA-256
  `b8f0e95a05051ca4ba05eeb7bcf6316d0ad57834c71723435915095aca9fd243`
  and a mandatory future live-receipt SHA-256. The live receipt has a closed
  schema and recomputes account, region, bucket, before/after state, apply
  output, 0/1/0 plan counts, zero incremental cost, and exact rules.
- Current pending payload plan digest is
  `28a925f2a925fae75eca4017aad2f6e26832bc1d1eedd54040e3a06839b3384c`;
  updated executor surface is
  `15c2fa66d872cfb03f86fff60c34f2d4866efe34814c9c3fdc069d50e619259c`.
  No live receipt exists, so no payload plan is signable.

## 2026-08-01 — Step 5B lifecycle applied and live-proof sealed

- **Authority:** explicit user approval covered only saved Terraform binary
  `b8f0e95a05051ca4ba05eeb7bcf6316d0ad57834c71723435915095aca9fd243`.
  The authenticated account check and binary hash both passed before apply.
- **Result:** Terraform reported 0 added, 1 changed, 0 destroyed. State advanced
  from `78e36e...b7cdf` to `dff0f6...b57b5`; incremental cost is zero.
- **Independent readback:** S3 returned the unchanged `runs/` 365/30/7 rule and
  live `runs/step5b/payloads/` 35/30/7 rule. Canonical lifecycle receipt digest
  is `5525f0016d91d1158c59215c88d5e454409942d08f649b0dc554d00712754c1d`.
- **Consequence:** successor payload plan digest
  `9334ffebd443dd4aee2a1a566ae5b29479b40a2856afe825a71e0c09ff74606a`
  is `ready_for_signature` but remains unsigned and authorizes nothing. No
  payload, GPU, model load, pilot, experiment, reservation, or spend occurred.

## 2026-08-01 — Step 5B payload-signing ceremony prepared

- Added a deterministic signing entrypoint that revalidates the exact ready
  plan, payload manifest, pricing bytes, lifecycle receipt, executor-source
  digest, ledger rows, trusted key, and projected USD 3.78 cost before emitting
  the two-stage Ed25519 package.
- Pending ledger rows CL-045/CL-046 bind envelope ceiling USD 5.00 and exact
  action digest `9334ffeb...4606a`. They grant nothing while unsigned.
- Focused signing/admission tests, Ruff, status coherence, digest parity, and
  whitespace checks passed. No private key was accessed; no signature, payload,
  provider action, reservation, or spend occurred.

### Cross-platform payload handoff bundle

- `git archive` over immutable commit `e7b910e` produced a 4,933,610-byte ZIP
  with 1,166 relative POSIX entries. A second independent archive reproduction
  was byte-identical.
- Native Windows and WSL2 Ubuntu independently computed SHA-256
  `03e1ff2d5d2236867a3cab4eceb54492fc85028d0075368256cef51afdfe7550`.
  This closes local checkout/CRLF portability for the handoff bytes; it does not
  substitute for the required AWS-side digest check.
- Evidence is sealed in
  `evidence/step5b-payload-handoff-bundle-20260801.json`. No signature, payload,
  provider mutation, reservation, or spend occurred.

## 2026-08-01 — Step 5B payload mirror completed

- Actions 001–003 failed closed on endpoint/host, dataset namespace, and
  expired anonymous Docker-token defects. Preserved content-addressed objects
  were independently reread on each successor and never overwritten.
- Signed action 004 bound plan `d40223db7385dc19ebcf7290029841b6318a66eb30a1f76e618cc6c856df1cf7`
  and executor `b817f51b6ad97b5d152cff3e6ebe9d5ec70c5a175cf65e5f498f27122589f16b`.
- AWS completed exactly 1,705 objects / 67,483,211,374 bytes with request
  counts 1,916 PUT, zero LIST, and 3,416 GET, inside the signed ceilings.
- AWS wrote and reread the receipt. Windows downloaded the same 980,909 bytes
  at SHA-256 `69d3e0db08788639de72d020af1ac061a2aa5f6a8742a288eb7d592ee8e7a89c`;
  offline semantic verification accepted the complete ordered roster and gave
  canonical-record digest `8c00a40138792498f62ed16a54401e4c421b9a9d15c986bc8fd8f03d0e664ca0`.
- Payload retrieval is settled. Real input lock, G-ROSTER, Linux worker
  qualification, and experiments remain open.

## 2026-08-01 — Real candidate input lock sealed cross-platform

- Derived seven role-specific artifact snapshot receipts from the complete
  payload roster, plus source-license, task-license, and public-artifact
  contamination evidence. Source licenses were verified from mirrored bytes:
  Qwen 3.5/3.6 are Apache-2.0; SWE harness/dataset, tau2, and RepoLaunch are MIT.
- The resulting lock classifies as `real_candidate`; all nine referenced local
  receipts verify. Windows and AWS Linux independently produced identical
  input-lock digest `e6746ad843b0da9a6144fa84a5a231dd350b6845a321ffaff171df4540f67b84`.
- This closes input-lock construction and portability. It does not promote a
  G-ROSTER tier or authorize scientific execution.

## 2026-08-01 — Model-fit action 003 failed closed on read-only Triton cache

- Signed action `step5b-model-fit-003` reconstructed and independently SHA-256
  verified all 72 sealed model objects / 56,822,409,329 bytes and pulled the
  immutable vLLM worker image.
- Subject 32k, subject 65k, and simulator 32k each exited 1 before model load or
  generation. The first causal exception is `OSError: [Errno 30] Read-only file
  system: '/root/.triton'`; vLLM architecture inspection tried to initialize
  Triton's cache beneath the intentionally read-only root filesystem.
- The published receipt is preserved under `evidence/model-fit-003-20260801/`.
  A successor may change only the cache location to the existing writable
  `/tmp` tmpfs. This is qualification evidence, not a scientific result.

## 2026-08-01 — Model-fit action 004 failed closed on non-executable tmpfs

- The successor reconstructed the same 72 objects / 56,822,409,329 bytes and
  successfully redirected Triton's cache into `/tmp`.
- All three rungs again exited 1 before model load or generation. Triton built
  its CUDA helper, then dynamic loading failed with `failed to map segment from
  shared object`: Docker's tmpfs was not executable.
- The exact action-004 receipt is preserved under
  `evidence/model-fit-004-20260801/`. A successor may add only `exec` to the
  existing isolated `/tmp` tmpfs. Network isolation and read-only root remain.

## 2026-08-01 — Real-model fit qualification passed

- Signed action `step5b-model-fit-005` bound plan SHA-256
  `141562f5b7b60620f39ce108791b47204596503be224df6dbc3b506f8348a24e`
  and package SHA-256
  `171729725e25b84b220b1bfeb3a6af444dfc48666dbaf3b0895295faf8eceedd`.
  It used zero retries and reconstructed and SHA-256 verified all 72 immutable
  model objects / 56,822,409,329 bytes.
- The 35B FP8 subject generated 128 tokens at both 32,768 and 65,536 context,
  measuring 8.0345 and 8.0569 output tokens/second. The 9B simulator generated
  109 tokens before EOS at 32,768 context, measuring 14.7979 output
  tokens/second. All three result codes were zero on one NVIDIA L40S with Torch
  2.10.0+cu129 and vLLM 0.19.0.
- Exact receipt SHA-256 is
  `0725e12255c790daf2260f3c6998260e5ebfbedbd99cafced998f973cd6bbfcd`.
  EC2 instance `i-0c0449cd0776839dc` and encrypted delete-on-termination volume
  `vol-015492544df656a45` both independently return not found after teardown.
- **Boundary:** this establishes real-model fit and a bounded single-prompt
  throughput observation only. It is not a benchmark, pilot, experiment, or
  scientific result. G-ROSTER isolation pairs, interruption/recovery,
  portability closure, and hostile launch review remain blocking.

## 2026-08-01 — C120 G-ROSTER isolation qualification passed

- Signed action `step5b-isolation-001` bound plan SHA-256
  `f7ef1a40789be4b64b232f129e9b1ef84bd7b56311def38227b48c19429b6bf6`,
  case-manifest digest
  `f9f78c85c9647159ba098520bae42850feab65b873650e81aad0ebe653c39abd`,
  real input lock `e6746a...67b84`, and package SHA-256
  `f9b368697ee07358f8cbfc8c6007ec9941d03064a2f571c5dabad293df4a08fe`.
- Linux x86_64 / Docker 25.0.16 executed exactly 33 pairs: three distinct
  immutable units for every eight SWE and three tau2 C120 splits. Every pair
  independently proved exact image digest, linux/amd64, network none, all
  capabilities dropped, no-new-privileges, clean pair creation, bidirectional
  cross-marker absence, and clean recreation. Result code was zero and stderr
  was empty.
- Exact AWS receipt bytes are 25,856 bytes at SHA-256
  `599527e896e9f48a53252585d02e98fd725074e8faa503ab7ce017cf1997b284`;
  canonical receipt digest is
  `ac0e726612cdbfd48c0ef62fc51bba9c4a2b2346fa1411336be188db256903a1`.
  A native-Windows checkout initially added a second newline; hostile byte
  verification caught it before promotion. Governed evidence JSON is now
  pinned to LF and the exact AWS digest reproduces locally.
- Deterministic final audits resolve every evidence byte and evaluate both SWE
  and tau2 as `CONDITIONALLY_FEASIBLE` at C120. Audit SHA-256 values are
  `b1dae7a4623b211b83263333324c2fa9049597ddc7d2b2f2f636db995903d5fa`
  and `4cb111081f2d5d411efd04de7dd3d8d004a9fd221f33c675e4076b63702d0ef0`;
  closure SHA-256 is
  `a887370640d2c6e9514e350c476e786d1040e6bcf3799422dee6c60b70944209`.
- **Boundary:** this closes G-ROSTER qualification only. Throughput admission,
  interruption/recovery, portability closure, and hostile launch review still
  block any pilot or experiment.

### Isolation teardown independently closed

- After AWS authentication resumed, exact provider reads returned
  `InvalidInstanceID.NotFound` for instance `i-01d2a6e41101fc6df` and
  `InvalidVolume.NotFound` for encrypted delete-on-termination volume
  `vol-0ddb5ff0c80f2ce39` in `us-west-2`.
- This closes the previously pending teardown observation. It adds no new
  isolation, pilot, experiment, or scientific evidence.

## 2026-08-01 — Step 5B registered p10 throughput qualification sealed

- **Live re-observation:** authenticated AWS STS returned account `892077329800`.
  The exact tagged `g6e.2xlarge` action `step5b-throughput-001` had stopped
  after publishing its complete output prefix. The signed package, frozen plan,
  runner, user-data, subject snapshot, receipt, and every output object were
  downloaded from encrypted, versioned S3 and checked by SHA-256.
- **Authority and execution:** plan
  `ad69fe00f42c8eef23690c3f367cf9c16ba95211e3d9e9a7009485582692e6c1`,
  input lock `e6746a...67b84`, and signed package `13df9a...29c4b` verify.
  The action used its first and only allowed attempt. The runner and user-data
  hashes match the sealed plan; the 56 subject objects / 37,493,015,668 bytes
  reconstructed with return code zero; immutable image digest matches exactly.
- **Result:** both registered rungs completed with return code zero. The raw
  ten-sample nearest-rank p10 values are 11.555050851717397 output tok/s at
  32,768 and 11.548052621929092 output tok/s at 65,536, each above the frozen
  8.0 floor. Container stdout contains vLLM diagnostics followed by one terminal
  JSON record; parsing that terminal record and recomputing every rate and p10
  passed. This is bounded infrastructure qualification, not a benchmark, pilot,
  experiment, or scientific result.
- **Teardown:** after a fresh tag/volume/delete-on-termination check, the VPS
  terminated `i-057047dfb078a326e`. AWS reports it terminated and independently
  returns `InvalidVolume.NotFound` for encrypted root
  `vol-0160c8cc693ca39d2`. Exact evidence and raw-object hashes are sealed in
  `evidence/throughput-001-20260801/verification.json`.

## 2026-08-01 — Production execution-surface runtime boundary

- Added `pneuma_lab.cloud.production_runtime`, the exact three-role executable
  boundary for controller, model-server, and benchmark-worker images. It accepts
  only a role plus a supplied harness file and its lowercase SHA-256, verifies
  the exact bytes, and emits one canonical terminal `READY` or failure record.
- The production-surface validator now rejects any role record that does not
  name this runtime and its exact role argument. Subprocess regressions prove
  acceptance of matching bytes and fail-closed rejection of a digest mismatch.
- Focused production-surface/runtime tests, Ruff, and whitespace checks passed.
  This is implementation only: the recipes remain fixture-only, no image was
  built or run, no receipt was promoted, and Step 7B/E2E qualification remains
  pending.

### KMS signer bootstrap attempt 001 failed closed

- The existing registered CloudShell key signed exact plan
  `221427aa...8837`; signed-package SHA-256 is `4978ce0f...bc05`.
- AWS created only IAM role `pneuma-kms-signer-v1` at
  `2026-08-01T20:32:46Z`. The subsequent first and only KMS `CreateKey` call
  failed with `MalformedPolicyDocumentException` because the newly created
  role had not propagated as a valid key-policy principal. CloudTrail request
  ID: `e32f453c-a21e-4a4a-b479-0d549c997fb3`.
- Provider inventory confirms no customer-managed signer key or alias was
  created. The zero-retry action was not reused. Successor plan
  `37b36480...bd56` excludes role creation and binds the observed role.

### KMS signer resources created; root cannot assume roles

- Signed successor package SHA-256 `67280246...b67e0` authorized action 002.
  Its first and only create call produced enabled Ed25519 SIGN_VERIFY key
  `8c240f51-e35b-40d7-955e-4230b8d291ce`, alias
  `alias/pneuma-approver`, and the exact signer-role permission.
- Exported public bytes are
  `8bec051c2614356d4e25da7e2b1f5205ec68a1da45c62ea1a4ac0f73847f8de7`.
  Root direct `kms:Sign` returned `AccessDeniedException`, as required.
- AWS rejects `AssumeRole` from an account-root session (`Roles may not be
  assumed by root accounts`). No role signature was emitted; a zero-byte probe
  output failed offline verification and was not promoted. A new exact action
  is required to provision a scoped non-root bootstrap identity.

### VPS signer identity attempt 003 failed closed

- Signed package SHA-256 `ea954732...86fbd` authorized action 003.
- AWS created only user `pneuma-vps-signer-bootstrap` at
  `2026-08-01T20:43:28Z`. Inline-policy submission then failed with
  `MalformedPolicyDocument`; the zero-retry action stopped.
- Provider reads prove the user has no inline policies and no access keys, and
  the signer role retains its prior root-only trust. Successor action 004 binds
  committed policy JSON files instead of shell-escaped policy text.

### KMS custody activation closed

- Action 004 completed after the committed policy files were applied. The VPS
  now uses profile `pneuma-signer-bootstrap` (only `sts:AssumeRole` on the exact
  signer role) and profile `pneuma-kms-signer` for temporary role credentials.
- One KMS signature was produced through the role and verified offline against
  public key `8bec051c2614356d4e25da7e2b1f5205ec68a1da45c62ea1a4ac0f73847f8de7`.
  The root session's direct `kms:Sign` attempt returned `AccessDenied`.
- The public key is now enumerated as active registry key
  `pneuma-kms-20260801-r1`. No private signing key left KMS; the bootstrap IAM
  access key was handled only inside the VPS and was never printed.

### EJ-20260801-step7b-builder-network

- **Scope:** one zero-cost, KMS-authorized prerequisite network action for the
  Step 7B image builder. The exact signed action `step7b-builder-network-001`
  created security group `sg-0c3acb5ff13aebea2` in the default VPC.
- **Verification:** an independent fresh provider read confirms zero ingress and
  exactly three egress rules: TCP/UDP 53 to `172.31.0.2/32` and TCP 443 to the
  public internet. No builder instance exists.
- **Correction:** the original read-only observation used `IpPermissions` for
  both ingress and egress and therefore incorrectly reported the predecessor
  group as egress-empty. A fresh `IpPermissionsEgress` query showed it was
  already correct. The signed authority is immutable; this append-only receipt
  preserves the mistake and retains the newly created exact group for the
  successor builder rather than silently reusing an unbound predecessor.
- **Boundary:** no image pull/build/SBOM, model download, GPU use, benchmark,
  experiment, or billable compute occurred.

### EJ-20260801-step7b-aws-builder-005-failure

- **Scope:** the first and only execution of KMS-authorized action
  `step7b-aws-builder-005`, a CPU-only pre-experiment image-build action.
- **Outcome:** bootstrap failed before source retrieval when Amazon Linux 2023
  reported that its installed `curl-minimal` conflicts with `dnf install curl`.
  The status and full bootstrap log were published to the sealed output prefix.
- **Teardown:** the stopped instance `i-07e32d42c932b901a` was terminated. AWS
  then returned `InvalidVolume.NotFound` for delete-on-termination encrypted root
  `vol-026f4a5117f32d93f`.
- **Boundary:** no image build, SBOM, model download, GPU use, benchmark,
  pilot, experiment, or scientific result occurred. This action has zero retries
  and is not reusable; a corrected successor needs independent hashes and KMS
  authority.

### EJ-20260801-step7b-aws-builder-006-failure

- **Scope:** the first and only execution of KMS-authorized action
  `step7b-aws-builder-006`, after the AL2023 package correction.
- **Outcome:** package setup, Syft installation, source retrieval, and Docker
  startup completed. The controller build then failed closed because its
  Dockerfile expected `controller.lock` at the build-context root, whereas the
  sealed executor intentionally supplied the repository root. No image build
  completed, no SBOM was generated, and no benchmark, model download, GPU use,
  pilot, experiment, or scientific result occurred.
- **Teardown:** AWS reports instance `i-01301ecefb3b70cb7` terminated and its
  delete-on-termination encrypted root `vol-0a0f1b6b958cde412` as
  `InvalidVolume.NotFound`. Output log and status versions are sealed in the
  failure receipt.
- **Successor rule:** action 006 is exhausted. Candidate 007 changes only the
  three lock-file `COPY` paths and has independent source, plan, ledger, and
  KMS-signature requirements.

### EJ-20260802-step7b-aws-builder-007-failure

- **Scope:** the single KMS-authorized attempt completed both controller builds
  with the same image ID, then failed closed at the network-isolated probe.
- **Outcome:** the pinned vLLM base exposes `python3`; the role entrypoints used
  `python`, producing exit 127. No SBOM, benchmark, model workload, GPU use,
  pilot, experiment, or scientific result occurred.
- **Teardown:** `i-0918b57add957b178` is terminated and encrypted root
  `vol-08825f7f6964e0b3f` returns `InvalidVolume.NotFound`. The immutable
  status and log are recorded in the failure receipt. Action 007 is exhausted.

### EJ-20260802-agent-session-preexperiment-audit

- **Task and cost bound:** `agent-session` ran one read-only Claude Haiku
  (`--tier cheap`, 900-second timeout) audit of the named pre-experiment
  authorities. No incremental currency estimate was exposed by the tool; the
  enforced bound was one cheap-tier turn and the recorded transcript/result
  under local session `preexperiment-audit`.
- **Receipt:** the child exited zero and returned a checklist. It was treated as
  an untrusted proposal and checked directly against the current status,
  decision log, spend ledger, and execution journal.
- **Rejection:** the proposal falsely reported that no provider action had
  occurred, described the decision log as ending at obsolete row numbers, and
  contradicted the live AWS qualification and Step 7B execution receipts.
  None of its completion or gate claims is promoted or relied upon.

### EJ-20260802-step7b-aws-builder-008-preparation

- **Correction and local gate:** the three role Dockerfiles use `python3` for
  their immutable production-runtime entrypoints. The focused successor-plan,
  build-executor, and production-runtime gate passed, as did Ruff and
  whitespace checks.
- **Reproducible authority input:** the successor generator derived exact plan
  `88f6ad03...a910a2` from exhausted action 007 and live committed source
  `d4861e5...fc551e`. Its `git archive` is 28,682,240 bytes at SHA-256
  `c87cbec4...64a5f74`; all executor, bootstrap, runtime, recipe, lock, and
  Dockerfile digests were reread rather than copied by assertion.
- **Boundary:** this is an unsigned zero-retry candidate. No upload, signature,
  provider mutation, image build, SBOM, GPU use, model download, benchmark,
  pilot, experiment, or scientific result has occurred under action 008.

### EJ-20260802-step7b-aws-builder-008-kms-admission

- **Fresh-state check:** account `892077329800`, region `us-east-1`, clean
  committed candidate `afdd491...598797`, and zero live instances tagged for
  action 008 were re-observed immediately before signing. The scoped signer
  assumed `pneuma-kms-signer-v1`; its Ed25519 public identity matches active
  registry key `pneuma-kms-20260801-r1`.
- **Authority receipt:** KMS signed the exact envelope and action admission
  bound to plan `88f6ad03...a910a2`, ledger rows CL-114/CL-115, zero retries,
  projected cost USD 2.25, and expiry `2026-08-02T12:18:51Z`. Canonical package
  bytes have SHA-256 `5dd7ee3d...428b60`; the production verifier accepted both
  signatures and all ledger, spend-history, action, manifest, and input-lock
  bindings before publication.
- **Boundary:** signing grants only this bounded CPU image-build action. No
  upload, instance, image build, SBOM, GPU use, model download, benchmark,
  pilot, experiment, or scientific result occurred in this step.

### EJ-20260802-step7b-aws-builder-008-failure

- **Execution:** the one authorized attempt launched exact instance
  `i-0b11e1f80f10a14df`. Fresh reads proved the expected AMI, `m7i.xlarge`,
  subnet/VPC, no-ingress security group, instance profile, IMDSv2, monitoring,
  exact user-data SHA-256 `68769c8d...097383`, action tags, and a 650 GiB
  encrypted delete-on-termination root.
- **Outcome:** both controller builds produced image ID
  `sha256:f7b3e748...d39ce6`; the corrected `python3` entrypoint advanced past the
  positive probe. Syft then failed closed while saving the image under its
  default `/tmp` because that staging surface lacked space. The zero-byte SBOM
  is preserved as failure evidence and is not admissible.
- **Receipts and teardown:** versioned log SHA-256 `01978f88...40b00` and
  status SHA-256 `f64d6f3e...7216e7` were reread before termination. AWS now
  reports the instance terminated and `InvalidVolume.NotFound` for encrypted
  root `vol-0ab935d326c7ed6f5`. Action 008 is exhausted; no retry occurred.
- **Successor condition:** bind Syft temporary storage to the verified large
  root surface and enforce the plan's 600 GiB free-space floor before the first
  build. No GPU, model workload, benchmark, pilot, experiment, or scientific
  result occurred.

### EJ-20260802-step7b-aws-builder-009-preparation

- **Repair:** the executor now rejects less than the sealed 600 GiB free-space
  floor before any build and passes a dedicated root-volume-backed `TMPDIR` to
  Syft. The bootstrap creates and exports the same staging location. Focused
  failure tests, executor compatibility, Ruff, whitespace, and status checks
  pass.
- **Candidate:** exact successor plan `51abcdc1...674359f` binds committed
  source `e4f589d...ac0413`, archive `67bef926...e55a3a3`, executor
  `ebd57fa2...4675fc`, and bootstrap `7ad89afa...715352`.
- **Boundary:** action 009 remains unsigned and unexecuted. No upload,
  signature, provider mutation, image build, SBOM, GPU, model workload,
  benchmark, pilot, experiment, or scientific result occurred in preparation.

### EJ-20260802-step7b-aws-builder-009-kms-admission

- Fresh account, scoped signer, clean-tree, and zero-live-action checks passed.
  KMS signed the exact CL-117/CL-118 envelope and admission for plan
  `51abcdc1...674359f`, zero retries, USD 2.25 projected cost, and expiry
  `2026-08-02T12:39:19Z`.
- The production verifier accepted every signature, ledger, spend-history,
  action, manifest, and input-lock binding. Canonical signed-package SHA-256 is
  `d86c680b...0aac4c`.
- Signing authorizes only the bounded CPU image qualification. No upload,
  instance, SBOM, GPU, model workload, benchmark, pilot, experiment, or
  scientific result occurred in this step.

### EJ-20260802-step7b-aws-builder-009-success

- **Execution:** The single admitted attempt launched `i-0bdfb8bedd57ab630`
  (`m7i.xlarge`, `us-east-1`, 650 GiB encrypted gp3 root) from the exact
  rendered user-data SHA-256 `d92b56be624f242f0d1370630a3b61b9b360bd8fe81f806367b4b8f53f19c54`.
  The controller, model-server, and benchmark-worker each completed two
  `--no-cache --pull=false --provenance=false --sbom=false` builds. The two
  image IDs were equal for every role: controller
  `sha256:042add3a17590f1b96de2399dd63d0e7ea50284018259cbb398ecd85f47a0cc3`,
  model-server
  `sha256:eb00c9ae3dcec74ede579f46ee3976464fffebc4e9015859fae8f2da3132f4b6`,
  and benchmark-worker
  `sha256:bffc7427e155e68c5d5c1e6bf2e58c7a85843de2c573ab2483989af534c3338e`.
- **Probes and SBOMs:** All three positive exact-harness probes emitted
  `READY`; all three wrong-hash probes emitted `FAILED` with
  `harness_sha256_mismatch` and exit code 2. SPDX SBOMs are nonempty and
  independently SHA-256 verified: controller `b009cea7...d56ec3` (25,296,943
  bytes), model-server `68c3ae81...a848b3` (25,300,521 bytes), and
  benchmark-worker `f0f7218f...c38970` (25,307,677 bytes). The canonical build
  receipt SHA-256 is `a00791ba0f2513d004529349fcc0b8c153a8a2ccad093799cb2a3c88f17aaf2a`.
- **Publication:** The terminal status was
  `{"state":"COMPLETE","action_id":"step7b-aws-builder-009"}`. Every
  output object was downloaded from the versioned S3 prefix, compared against
  its recorded size/hash, and checked against the image-receipt schema and
  plan/input/runtime/executor bindings. The complete evidence receipt is
  `evidence/step7b-aws-builder-success-009-20260802.json`.
- **Boundary:** This is a CPU-only reproducible image/SBOM qualification. It
  does not qualify the real production execution surface, load a model, run a
  benchmark, establish a pilot, or create a scientific result.

### EJ-20260802-step7b-aws-builder-009-teardown

- After the instance self-stopped, a fresh provider read confirmed the exact
  action tag, root volume, and delete-on-termination setting before the one
  authorized termination call. AWS reports `i-0bdfb8bedd57ab630` terminated;
  `vol-09c73e10cb4679fa6` returns `InvalidVolume.NotFound` and the temporary
  builder security group `sg-0c3acb5ff13aebea2` returns
  `InvalidGroup.NotFound` after dependency checks showed no attached ENI or
  instance. No residual action-tagged resource remains.
- Spend is recorded as pending provider billing settlement under CL-119/CL-120;
  no cash charge or credit application has been observed yet. Action 009 is
  exhausted with zero retries and is not reusable.

### EJ-20260802-production-surface-handshake-implementation

- Replaced the former READY-only role stub with a bounded content-addressed
  handshake: controller dispatch, model-server response, and benchmark-worker
  terminal receipt. Each role rejects mismatched harness, authority, request,
  predecessor state, response digest, or token payload; the wrong-hash probe
  remains fail-closed.
- Added the role-receipt schema, aggregate E2E runner, and focused subprocess
  regressions. The local chain and malformed/wrong-hash cases pass, with no
  network, model load, benchmark task, provider action, or scientific result.
- **Boundary:** this is implementation evidence only. A fresh image-bound E2E
  action must execute the same chain under network-none/read-only isolation and
  bind its receipts before the production-surface gate can close.

### EJ-20260802-step7b-aws-builder-010-preparation

- **Successor binding:** after the production-surface runtime and builder
  executor were committed, a fresh `git archive --format=tar HEAD` produced
  source archive SHA-256 `321a907aa92da24794480b29e90427f78eb9a7cfc5a979a05b67582ef9440b02`
  (28,753,920 bytes). Candidate plan
  `898d7f534c761d3618b73da971b6a64c9d89a8365de8ab455d4f6d86f1414f61` binds
  source commit `efa632570c20b8e81f410ec5dccc96d4279c98db`, executor
  `d7c0e7b8b7983e49a919c0844cb34b3bcf5919bd3b96b1d3883a5a5cf549aa06`,
  runtime `e684adf0b78aba1af207cf7a509179279267ea9f1ed913bacb43570c98b88055`,
  and the canonical harness digest
  `d32bb3d94a19ffda0718117b7273b05a117ae4a14b88c66d341db60ca9b0174f`.
- **Scope:** action `step7b-aws-builder-010` remains an unsigned, zero-retry
  CPU image-build candidate. It adds only the explicitly bound infrastructure
  handshake after the six builds; it still forbids model download, benchmark
  execution, registry push, GPU use, pilot, experiment, and scientific claims.
  No upload, signature, provider mutation, image build, SBOM, or spend occurred
  in this preparation step.

### EJ-20260802-step7b-aws-builder-010-kms-admission

- **Fresh-state admission:** account `892077329800`, region `us-east-1`, clean
  committed candidate, no live action-010 instance, and no action-010 security
  group were reread before signing. The scoped `pneuma-kms-signer` role
  returned the registered Ed25519 KMS identity; no root direct-sign path was
  used.
- **Authority receipt:** KMS signed the exact CL-121/CL-122 envelope and
  admission for plan `898d7f534c761d3618b73da971b6a64c9d89a8365de8ab455d4f6d86f1414f61`,
  zero retries, projected USD 2.25, and expiry `2026-08-02T14:30:00Z`.
  Signed-package SHA-256 is
  `a9313f61ca4d624831571f5d382c8741ed8107ffe2f5a9d12d1e3e3c3f89b38f`.
  The package binds envelope body
  `ff224b3453c6c06fbb71802bc4508fbd4d73a878ddb6a42e553768fd1134fd57`,
  admission body
  `3244e16d2ebb6f6f27d7f7bfa345908e9dcba711222eaf1424604f317034b4a4`,
  and the canonical production harness digest
  `d32bb3d94a19ffda0718117b7273b05a117ae4a14b88c66d341db60ca9b0174f`.
- **Boundary:** authorization covers one CPU image-build attempt plus the
  explicitly bound infrastructure handshake. It does not authorize a model
  download, benchmark episode, pilot, experiment, registry push, or scientific
  claim.

### EJ-20260802-step7b-aws-builder-010-failure

- **Execution:** The one admitted attempt launched exact instance
  `i-0cd61b4b43fdee032` (`m7i.xlarge`, 650 GiB encrypted gp3 root) from
  rendered user-data SHA-256
  `cdd86c1958fadc7901704387db1ad3ba9c3f98fabfd708221bb20e9c9a60dd55`.
  AMI, profile, subnet, action tags, IMDSv2, and the no-ingress/DNS+443-only
  security group were fresh-checked.
- **Failure:** The pinned base pulled successfully and the controller image
  built once as `sha256:0a3834cc4c4ca299258dcbf0c35f9b044aa4cb7fd15c88d1bbbd3a6dfbb996b9`.
  The second no-cache build produced
  `sha256:84fef39d73180640261cf89626bc426f73bdb63acf808fcd77fd6081790b2da`,
  so the executor stopped before a positive probe, the other roles, SBOMs, or
  the production-surface handshake. This is a reproducibility failure, not a
  scientific result or a production-surface pass.
- **Receipt:** Versioned S3 outputs are preserved: bootstrap log
  `wReQknvOKR1y6_WimXIVpbD1kpWpQo_.` / SHA-256
  `1e1b4c8a1b188edfe852e24c8cdcb4be57c68e96e6d69171319f2e013b09c3e1`,
  bootstrap status `gLHeX7WanFLgSZWcIYSuIyFhQHaWyWhK` / SHA-256
  `f64d6f3e5daca6f36022798a81113d1df04f8b5732f9063ae5e145b1ff7216e7`.
  Failure receipt is
  `evidence/step7b-aws-builder-failure-010-20260802.json`; action 010 is
  exhausted with zero retries.

### EJ-20260802-step7b-aws-builder-010-teardown

- The instance self-stopped after the fail-closed executor; one independent
  termination call returned `terminated`. Fresh provider reads show encrypted
  root `vol-0382ce24cd85aec6a` as `InvalidVolume.NotFound`. The temporary
  security group `sg-055557b40784442b3` had no attached ENI or instance, was
  deleted, and then returned `InvalidGroup.NotFound`.
- No action-tagged resource remains. The signed action's projected USD 2.25 is
  recorded as pending provider billing settlement under CL-123/CL-124; no
  model, benchmark, pilot, experiment, or scientific result occurred.

### EJ-20260802-step7b-aws-builder-011-preparation

- **Repair:** action 010's controller double-build mismatch was preserved as a
  no-retry failure. The successor executor now exports the sealed
  `SOURCE_DATE_EPOCH` into each Docker build environment, passes
  `BUILDKIT_MULTI_PLATFORM=1`, and the AWS bootstrap exports the same timestamp
  before invoking Docker. Focused executor tests, Ruff, whitespace, and status
  checks pass.
- **Candidate:** a fresh `git archive --format=tar HEAD` produced archive
  `fb68f972d434aa2984fef49854f77a58d9c82b422b386704b9c4a48071eeae62`
  (28,774,400 bytes). Plan
  `32714d078b9a14b30d4762b523913ca5fd62a2eb01a75d2a176d3669a810e205` binds
  source `06de1bf88ae85dee47ad62a3c1b914b83d25cf9c`, executor
  `e5df9b73a53d7058ee0f5ea9f49135a05d273eba1d5b6695cae02aa8b430d654`,
  bootstrap `fad19b0dac4bab6c91dc565898873226b70eea2e0e46c197136f13adb9aad759`,
  and production harness `ba404049586f4ac289cdc25002234d6b79c9b815b94f481d5f720cca0a78b750`.
- **Boundary:** action 011 is an unsigned zero-retry candidate. No upload,
  signature, provider mutation, image build, SBOM, role-chain E2E, or
  scientific execution occurred in this preparation entry.

### EJ-20260802-step7b-aws-builder-011-kms-admission

- Fresh account `892077329800`, region `us-east-1`, clean committed candidate,
  and zero live action-011 resources were reread before signing. The scoped
  `pneuma-kms-signer` role matched the active Ed25519 registry identity.
- KMS signed the exact CL-125/CL-126 envelope and admission for plan
  `32714d078b9a14b30d4762b523913ca5fd62a2eb01a75d2a176d3669a810e205`, zero
  retries, projected USD 2.25, and expiry `2026-08-02T14:45:00Z`.
  Signed-package SHA-256 is
  `e2f6c22675bdf1467e81b0ee33487af6efd9a9e20aeb21f3b3ef191a52bcdb5c`;
  envelope body is
  `33e926dbffd51e2652e823086f0aacc957830a38a37cc9ce7a88f565a220c0c6`,
  admission body is
  `3d1bb19653b3fe73e14e5719b48db4de2c7e3d0973c254a06d4828558b6f7a3f`.
- Authorization remains limited to one CPU image-build attempt and its
  explicitly bound infrastructure handshake; no model, benchmark, pilot,
  experiment, registry push, or scientific claim is authorized.

### EJ-20260802-step7b-aws-builder-012-failure

- **Execution:** The one admitted attempt launched exact instance
  `i-0b9fca99f7ba96475` (`m7i.xlarge`, 650 GiB encrypted gp3 root) from
  rendered user-data SHA-256
  `ce9ab0440b9875ebc034279beb8a2e67c62587aae231e85d31533bad5fbc5643`.
  The controller built twice as the identical image ID
  `sha256:2392c5d503a3d3f9234d0f61f9ae8b7416b98dc550f6705f3f5b19944825dbd6`;
  the model-server also built twice as the identical ID
  `sha256:30d963461192a92711891f3d4727f90e7f04cbfba7153675cf32266a78474c3b`.
  Their positive probes returned `READY`, wrong-hash probes returned
  `FAILED`, and their nonempty SPDX SBOMs were uploaded.
- **Failure:** The benchmark-worker first build produced
  `sha256:6ab20d3b18d22adfbbcb0b6840f2bed9f52bd9a4efc3ae7072e14c9e5b4d1139`;
  the second produced
  `sha256:86630dda644139c97d54c9a2c007421c92443344e0530a2f9a5204a07b3112af`.
  The executor failed closed before benchmark-worker probes/SBOM and before
  the production-surface handshake. This is a reproducibility failure, not an
  E2E or scientific result.
- **Receipt:** Versioned S3 outputs are sealed under
  `runs/preparation/step7b-aws-builder-012/outputs/`: bootstrap status
  `a_qEyx.aH.nESM5kHY6ear4VzxCvLcI0` / SHA-256
  `f64d6f3e5daca6f36022798a81113d1df04f8b5732f9063ae5e145b1ff7216e7`, and
  bootstrap log `OLGrxCuIZ_wPeHbZnRKcr.eKnpeMsYV1` / SHA-256
  `13a3e997a971fcf44e318d09b7fe235483aa33da2c8c4107b27e1123e61b2955`.
  The complete partial-output inventory, image IDs, and teardown evidence are
  sealed in `evidence/step7b-aws-builder-failure-012-20260802.json`; action 012
  is exhausted with zero retries.

### EJ-20260802-step7b-aws-builder-012-teardown

- The instance self-stopped after the fail-closed executor. One independent
  termination call returned `terminated` at 03:37:26Z. Fresh provider reads
  show encrypted root `vol-041c4388f42887c31` as `InvalidVolume.NotFound`.
  The temporary security group `sg-05ffcf16e3f1b5ead` had no attached ENI or
  instance, was deleted, and then returned `InvalidGroup.NotFound`.
- No action-tagged resource remains. The projected USD 2.25 is recorded as
  pending provider billing settlement under CL-131/CL-132; no model,
  benchmark, pilot, experiment, or scientific result occurred.

### EJ-20260802-step7b-aws-builder-013-preparation

- **Repair:** action 012 showed that the pinned Docker/BuildKit path could
  leave build-owned `COPY` and work-directory mtimes host-dependent even when
  `SOURCE_DATE_EPOCH` and the exporter flag were present. The three role
  Dockerfiles now normalize `/opt/pneuma` and `/opt` with the sealed epoch
  before the entrypoint; focused executor/image tests, Ruff, whitespace, and
  status checks pass.
- **Candidate:** a fresh `git archive --format=tar HEAD` produced archive
  `b7587d7166c97f5e8761d02bae3b8b0289d025e5866e15285ce890fbf21ff6f2`
  (28,815,360 bytes). Plan
  `41ef38ad1b508aabe32e067c91a6701ac8e47462a43a778316d25bfed17c9019` binds
  source `99953946e0171b91a4f01e51c97e2c2fac9d16a3`, executor
  `17e4c43ba34924a79f8219386dbb9b6aa9d2eda5a92f484ed561e04eb4770776`, the
  fresh no-ingress SG `sg-09037f520fd0c97d8`, and production harness
  `7fb36e364914187ad4f14845e43f18c00fc05488835604d94fcbd808d57efb4e`.
- **Boundary:** action 013 is an unsigned zero-retry candidate. No source or
  plan upload, signature, instance launch, image build, SBOM, role-chain E2E,
  or scientific execution has occurred in this preparation entry.

### EJ-20260802-step7b-aws-builder-011-failure

- **Execution:** The one admitted attempt launched exact instance
  `i-0fb19c8b0aaf1e231` (`m7i.xlarge`, 650 GiB encrypted gp3 root) from
  rendered user-data SHA-256
  `361139a18f6866a70d34fd75df227a37e919e046a4e7bbefa9a521b4754df16c`.
  The pinned base completed its pull and the controller built once as
  `sha256:04fbf1b4200af24f2c7b251fd98a2a1e847bf84da39afd7eb16432aaf35116bc`.
- **Failure:** The second build, despite the exported timestamp,
  `BUILDKIT_MULTI_PLATFORM=1`, and pinned `linux/amd64`, produced
  `sha256:ff196cd7c3fc87017716987032e51ad6fdd86dedb97508c236131a7d27d6f9f2`.
  The executor failed closed before a positive probe, the other roles, SBOMs,
  or production-surface handshake. This remains a reproducibility failure, not
  an E2E or scientific result.
- **Receipt:** Versioned S3 outputs are sealed: bootstrap log
  `kr6rkCAlj2R8OsA2YvbBzyXOpcMs6_4C` / SHA-256
  `e3e0de0eabe8ad797b9d0ce9ee29a92ecf1b8c40593cdd82f42944dcc7de1f17`,
  bootstrap status `aU8YPPaL0Y.fvkhKhMCtbneSlHIv0PJE` / SHA-256
  `f64d6f3e5daca6f36022798a81113d1df04f8b5732f9063ae5e145b1ff7216e7`.
  Failure receipt is
  `evidence/step7b-aws-builder-failure-011-20260802.json`; action 011 is
  exhausted with zero retries.

### EJ-20260802-step7b-aws-builder-011-teardown

- The instance self-stopped after the fail-closed executor; one independent
  termination call returned `terminated`. Fresh provider reads show encrypted
  root `vol-01d76a36d200005f1` as `InvalidVolume.NotFound`. The temporary
  security group `sg-085a6dcdb09d9fa9c` had no attached ENI or instance, was
  deleted, and then returned `InvalidGroup.NotFound`.
- No action-tagged resource remains. The projected USD 2.25 is recorded as
  pending provider billing settlement under CL-127/CL-128; no model,
  benchmark, pilot, experiment, or scientific result occurred.

### EJ-20260802-step7b-aws-builder-012-preparation

- **Repair:** action 011 showed that timestamp environment and multi-platform
  flags alone did not stabilize Docker's image exporter. The successor
  executor now pins `linux/amd64` and requests BuildKit's explicit
  `type=docker,rewrite-timestamp=true` exporter while retaining the sealed
  timestamp and no-provenance/no-SBOM build flags. Focused executor tests,
  Ruff, whitespace, and status checks pass.
- **Candidate:** a fresh `git archive --format=tar HEAD` produced archive
  `6328e5d414b21963d7472d6050f1b34224c6701e61a17e4c21c354ffa02f0bcf`
  (28,794,880 bytes). Plan
  `c4fb3a7fe68654c4caf142a55406b2a9948ba2bab147289e16b174d1806ab11a` binds
  source `46f005f8fab83bda47c2a7121d15bc47a45d66f2`, executor
  `17e4c43ba34924a79f8219386dbb9b6aa9d2eda5a92f484ed561e04eb4770776`, and
  production harness `a43d9da3e8a43c9af2ffbe93fac979c092903cf225995107d99651b957984327`.
- **Boundary:** action 012 is an unsigned zero-retry candidate. No upload,
  signature, provider mutation, image build, SBOM, role-chain E2E, or
  scientific execution occurred in this preparation entry.

### EJ-20260802-step7b-aws-builder-012-kms-admission

- Fresh account `892077329800`, region `us-east-1`, clean committed candidate,
  and zero live action-012 resources were reread before signing. The scoped
  `pneuma-kms-signer` role matched the active Ed25519 registry identity.
- KMS signed the exact CL-129/CL-130 envelope and admission for plan
  `c4fb3a7fe68654c4caf142a55406b2a9948ba2bab147289e16b174d1806ab11a`, zero
  retries, projected USD 2.25, and expiry `2026-08-02T15:15:00Z`.
  Signed-package SHA-256 is
  `a70729135d1c9a96d9dfd9f35fa5dc718ae940a0f1c70eb067f7e01fedb7d62e`;
  envelope body is
  `d75e4e01251623fbc87c1cfc38a18ca9a00ed66f7ce6806208dbc93eecb73381`,
  admission body is
  `c6ff3761adfe98af159d0d3cfa3c27fba55a04c9704efe483d8aeb1bbdb37c4e`.
- Authorization remains limited to one CPU image-build attempt and its
  explicitly bound infrastructure handshake; no model, benchmark, pilot,
  experiment, registry push, or scientific claim is authorized.

### EJ-20260802-step7b-aws-builder-013-failure

- **Execution:** The one admitted attempt launched exact instance
  `i-03d76c4d5910ec427` (`m7i.xlarge`, 650 GiB encrypted gp3 root) from
  rendered user-data SHA-256
  `9dace810871bd46fe621d0738a8a9d177c9916f10e15d57427547257183892b9`.
  The source archive was the plan-bound 28,815,360-byte object with SHA-256
  `b7587d7166c97f5e8761d02bae3b8b0289d025e5866e15285ce890fbf21ff6f2`.
- **Failure:** The controller's first image export produced
  `sha256:03cfc60ce5758346211e708287cb42191960e4a5822e3e74d50b53c47614991c`;
  its second no-cache export produced
  `sha256:652fd34ae2fb9a9f3006f8582a65bdd4753e29fb2254bdfe092bc09b22303055`.
  This remained a reproducibility failure despite the explicit
  `SOURCE_DATE_EPOCH`/`BUILDKIT_MULTI_PLATFORM` bindings, pinned
  `linux/amd64`, `rewrite-timestamp=true`, and Dockerfile-owned mtime
  normalization. The executor failed closed before controller probes/SBOM,
  the other roles, or the production-surface handshake. This is not an E2E
  or scientific result.
- **Receipt:** Versioned S3 outputs are sealed under
  `runs/preparation/step7b-aws-builder-013/outputs/`: bootstrap status
  `mz8wPbCV8sWdlhbic5xNz9ydX61qRWIv` / SHA-256
  `f64d6f3e5daca6f36022798a81113d1df04f8b5732f9063ae5e145b1ff7216e7`, and
  bootstrap log `SNALFNgLueszdsAtKl7GuhmdIShqv5ko` / SHA-256
  `5a27224bbc38e7b5beae4383eb9993b779e21b53907c017cf25ca8ddcda7d8c7`.
  The complete partial-output inventory and teardown evidence are sealed in
  `evidence/step7b-aws-builder-failure-013-20260802.json`; action 013 is
  exhausted with zero retries.

### EJ-20260802-step7b-aws-builder-013-teardown

- The fail-closed executor stopped the host; one independent termination call
  returned `terminated`. Fresh provider reads show encrypted root
  `vol-07a56f141a5e8fd50` as `InvalidVolume.NotFound`. The temporary security
  group `sg-09037f520fd0c97d8` had no attached ENI or instance, was deleted,
  and then returned `InvalidGroup.NotFound`.
- No action-tagged resource remains. The projected USD 2.25 is recorded as
  pending provider billing settlement under CL-135/CL-136; no model,
  benchmark, pilot, experiment, or scientific result occurred.

### EJ-20260802-step7b-aws-builder-014-preparation

- **Repair:** action 013 reproduced the old Docker-packaged BuildKit failure
  even after Dockerfile-owned mtime normalization. A bounded local control
  reproduced the same behavior with BuildKit 0.12.5: two identical exports
  had different image IDs. The same control with content-addressed BuildKit
  v0.13.2 produced identical image IDs. The executor now installs and hashes
  Buildx v0.13.1, creates a named `docker-container` builder from the exact
  BuildKit v0.13.2 image, verifies both versions, and retains the strict
  digest gate.
- **Candidate:** a fresh `git archive --format=tar HEAD` produced archive
  `e0e99d23417a864519d555f17f377d1ef9ee593e2d1632a56c50d77f6986266c`
  (28,846,080 bytes). Plan
  `9db1962d326d733718e510b3ba60b6bb9fb487dddb144d5d884d12f3f9c51457` binds
  source `e687554a02fded64ae469a394945cdbe5d232d0e`, executor
  `4ecfc977817ceedc444ae5efaeb32705971697c62e096a3b976b054ea0983288`,
  Buildx SHA-256
  `3e2bc8ed25a9125d6aeec07df4e0211edea6288e075b524160ef3fd305d3d74c`,
  BuildKit image
  `moby/buildkit:v0.13.2@sha256:9194b5ec1be368f41c516df7f93f7f540630ea06136056b2ffebb62226ed4ad6`,
  fresh no-ingress SG `sg-024de73fe15daaafc`, and production harness
  `1d94c0f17cd25e0c42acf91badec55f964be567db67f0c31d67caf0b68958968`.
- **Boundary:** action 014 is an unsigned zero-retry candidate. No source or
  plan upload, signature, instance launch, image build, SBOM, role-chain E2E,
  or scientific execution has occurred in this preparation entry.

### EJ-20260802-step7b-aws-builder-014-failure

- **Execution:** The single admitted attempt launched exact instance
  `i-020f7544dcf95f161` (`m7i.xlarge`, 650 GiB encrypted gp3 root) from
  rendered user-data SHA-256
  `4d0d763ae30ce4259a853f63470fd46a0225625694039eb59e7dc92ac9eddb19`.
- **Failure:** Amazon Linux bootstrap ran `dnf install -y docker tar gzip
  curl`; the AMI's preinstalled `curl-minimal` caused a package conflict and
  the bootstrap entered `FAILED` before Buildx or BuildKit installation. No
  source retrieval, image build, SBOM, role probe, production-surface
  handshake, model, benchmark, pilot, or experiment occurred. The sealed
  status/log versions and hashes, partial-result states, and bindings are in
  `evidence/step7b-aws-builder-failure-014-20260802.json`; action 014 is
  exhausted with zero retries.

### EJ-20260802-step7b-aws-builder-014-teardown

- The host was stopped and terminated at `2026-08-02T04:21:44Z`. Fresh
  provider reads show encrypted root `vol-01ef175a0b60a325d` as
  `InvalidVolume.NotFound`. The temporary security group
  `sg-024de73fe15daaafc` had no ENI or instance dependencies, was deleted, and
  then returned `InvalidGroup.NotFound`. No action-tagged resource remains.
- The projected USD 2.25 is recorded as pending provider billing settlement
  under CL-139/CL-140; no scientific work occurred.

### EJ-20260802-step7b-aws-builder-015-preparation

- **Repair:** Action 014's only fault was the Amazon Linux package conflict:
  the bootstrap requested `curl` while the AMI supplied `curl-minimal`. The
  template now installs `docker tar gzip` only; its focused executor/bootstrap
  tests, Ruff, whitespace, and status checks pass.
- **Candidate:** A clean archive from committed source `98dd81a...c806` is
  `9229854312d86740e02b1cff25419abc7aaaff3bdfc023973a92d7940b80b579`
  (28,866,560 bytes). Plan
  `dbc75690017269be0544d9cc9c3fe3d8870928058fa80cac9c08acd38d35fa5a`
  binds the corrected template, pinned Buildx `v0.13.1`, content-addressed
  BuildKit `v0.13.2`, production harness
  `f97d3c87622f932656266922ca7f488a33057e37c333afe2de1f483e9d876172`, and
  fresh no-ingress security group `sg-04331c50b912dac3d`.
- **Boundary:** Action 015 is an unsigned zero-retry candidate. No source or
  plan upload, signature, instance launch, image build, SBOM, role-chain E2E,
  or scientific execution has occurred in this preparation entry.

### EJ-20260802-step7b-aws-builder-015-failure

- **Execution:** The single admitted attempt launched exact instance
  `i-0a053da387bc63267` (`m7i.xlarge`, 650 GiB encrypted gp3 root) from
  rendered user-data SHA-256
  `b0851044b5e676cc135de11039ba878de724b3c1e4dd91d653f802d7e23329f6`.
- **Failure:** The corrected package install completed and Buildx
  `v0.13.1` was verified, but the executor failed closed because
  `docker buildx inspect` did not report the sealed BuildKit `v0.13.2`. The
  old executor did not publish the inspection text, so the exact provider
  mismatch remains an explicit diagnostic gap. No role build, SBOM, probe,
  production-surface handshake, model, benchmark, pilot, or experiment ran.
  The sealed status/log/tool outputs and bindings are in
  `evidence/step7b-aws-builder-failure-015-20260802.json`; action 015 is
  exhausted with zero retries.

### EJ-20260802-step7b-aws-builder-015-teardown

- The host self-terminated at `2026-08-02T04:32:28Z`; fresh provider reads at
  `2026-08-02T04:34:58Z` show encrypted root `vol-02d4da5bf566445bd` as
  `InvalidVolume.NotFound`. The temporary security group
  `sg-04331c50b912dac3d` had no ENI or instance dependencies, was deleted, and
  then returned `InvalidGroup.NotFound`. No action-tagged resource remains.
- The projected USD 2.25 is recorded as pending provider billing settlement
  under CL-143/CL-144; no scientific work occurred.
