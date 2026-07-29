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
