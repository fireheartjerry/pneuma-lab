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
