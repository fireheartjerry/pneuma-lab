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
