"""Byte-verifiable sharding for the NeurIPS execution journal."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EVENT_PATTERN = re.compile(
    rb"^#{2,3} (EJ-(?P<date>[0-9]{8})-(?P<sequence>[0-9]{4}))\b",
    re.MULTILINE,
)


class JournalIntegrityError(RuntimeError):
    """Raised when journal bytes do not satisfy the archive contract."""


@dataclass(frozen=True)
class Event:
    event_id: str
    date: str
    sequence: int
    offset: int


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _line_count(payload: bytes) -> int:
    return payload.count(b"\n")


def _events(payload: bytes) -> list[Event]:
    return [
        Event(
            event_id=match.group(1).decode("ascii"),
            date=match.group("date").decode("ascii"),
            sequence=int(match.group("sequence")),
            offset=match.start(),
        )
        for match in EVENT_PATTERN.finditer(payload)
    ]


def _require_contiguous(events: list[Event]) -> None:
    if not events:
        raise JournalIntegrityError("journal contains no event headings")
    for previous, current in zip(events, events[1:], strict=False):
        same_day = current.date == previous.date
        valid_same_day = same_day and current.sequence == previous.sequence + 1
        valid_new_day = (
            current.date > previous.date
            and current.sequence == 1
            and current.date != previous.date
        )
        if not (valid_same_day or valid_new_day):
            raise JournalIntegrityError(
                "noncontiguous event IDs: "
                f"{previous.event_id} -> {current.event_id}"
            )


def _segment_record(
    *,
    path: str,
    payload: bytes,
    first_event_id: str | None,
    last_event_id: str | None,
) -> dict[str, Any]:
    return {
        "path": path,
        "first_event_id": first_event_id,
        "last_event_id": last_event_id,
        "bytes": len(payload),
        "lines": _line_count(payload),
        "sha256": _sha256(payload),
    }


def _live_index(manifest: dict[str, Any]) -> bytes:
    cutoff = manifest["last_event_id"]
    original_sha = manifest["archived_original_sha256"]
    rows = "\n".join(
        "| "
        + " | ".join(
            [
                segment["path"],
                (
                    "prologue"
                    if segment["first_event_id"] is None
                    else (
                        f'{segment["first_event_id"]}–'
                        f'{segment["last_event_id"]}'
                    )
                ),
                str(segment["bytes"]),
                str(segment["lines"]),
                f'`{segment["sha256"]}`',
            ]
        )
        + " |"
        for segment in manifest["segments"]
    )
    return f"""# 33 — Execution Journal

> **NON-AUTHORITATIVE EVIDENCE INDEX AND CURRENT VOLUME.** This journal records
> execution evidence but does not amend or outrank repository authority.

## Sharded recording contract

The user authorized a byte-preserving storage migration after the original
journal became costly to load. Events through `{cutoff}` and the original
prologue are stored as immutable historical segments in `execution-journal/`.
Their ordered concatenation reconstructs the exact pre-migration file with
SHA-256 `{original_sha}`.

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
- Archived event count: `{manifest["event_count"]}`
- Archived range: `{manifest["first_event_id"]}` through `{cutoff}`
- Exact reconstructed bytes: `{manifest["archived_original_bytes"]}`
- Exact reconstructed lines: `{manifest["archived_original_lines"]}`
- Exact reconstructed SHA-256: `{original_sha}`

| Segment | Range | Bytes | Lines | SHA-256 |
|---|---:|---:|---:|---|
{rows}

Run `.venv/bin/python -m scripts.research.execution_journal check` to verify
segment hashes, exact historical reconstruction, and global event continuity.

## Current volume

The next event after the archived migration boundary is appended below.
""".encode()


def _event_segment_payloads(
    payload: bytes,
    events: list[Event],
    *,
    shard_size: int,
    final_offset: int | None = None,
) -> list[tuple[dict[str, Any], bytes]]:
    groups: list[list[Event]] = []
    for event in events:
        if groups and (
            len(groups[-1]) == shard_size or groups[-1][0].date != event.date
        ):
            groups.append([])
        if not groups:
            groups.append([])
        groups[-1].append(event)
    event_index = {event.event_id: index for index, event in enumerate(events)}
    result: list[tuple[dict[str, Any], bytes]] = []
    for group in groups:
        start = group[0].offset
        next_index = event_index[group[-1].event_id] + 1
        end = (
            events[next_index].offset
            if next_index < len(events)
            else (len(payload) if final_offset is None else final_offset)
        )
        segment = payload[start:end]
        path = (
            f"events-{group[0].date}-{group[0].sequence:04d}-"
            f"{group[-1].sequence:04d}.md"
        )
        result.append(
            (
                _segment_record(
                    path=path,
                    payload=segment,
                    first_event_id=group[0].event_id,
                    last_event_id=group[-1].event_id,
                ),
                segment,
            )
        )
    return result


def _replace_bytes(path: Path, payload: bytes, *, mode: int) -> None:
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise JournalIntegrityError(f"temporary path already exists: {temporary}")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def _append_journal_archive(
    journal_path: Path,
    archive_dir: Path,
    *,
    cutoff_event_id: str,
    shard_size: int,
) -> Path:
    manifest_path = archive_dir / "manifest.json"
    verify_journal(journal_path, manifest_path)
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    live = journal_path.read_bytes()
    events = _events(live)
    cutoff_index = next(
        (
            index
            for index, event in enumerate(events)
            if event.event_id == cutoff_event_id
        ),
        None,
    )
    if cutoff_index is None:
        raise JournalIntegrityError(
            f"cutoff {cutoff_event_id} is not in the current volume"
        )
    selected = events[: cutoff_index + 1]
    if not selected:
        raise JournalIntegrityError("append migration selected no events")
    expected_previous = manifest["last_event_id"]
    _require_contiguous(
        [
            Event(
                event_id=expected_previous,
                date=expected_previous.split("-")[1],
                sequence=int(expected_previous.rsplit("-", 1)[1]),
                offset=0,
            ),
            selected[0],
        ]
    )
    tail_offset = (
        events[cutoff_index + 1].offset
        if cutoff_index + 1 < len(events)
        else len(live)
    )
    additions = _event_segment_payloads(
        live,
        selected,
        shard_size=shard_size,
        final_offset=tail_offset,
    )
    existing_paths = {
        cast_segment["path"] for cast_segment in manifest["segments"]
    }
    if any(record["path"] in existing_paths for record, _payload in additions):
        raise JournalIntegrityError("append migration segment path collision")

    existing_payloads = [
        (archive_dir / segment["path"]).read_bytes()
        for segment in manifest["segments"]
    ]
    reconstructed = b"".join(
        existing_payloads + [payload for _record, payload in additions]
    )
    updated = dict(manifest)
    updated["last_event_id"] = selected[-1].event_id
    updated["event_count"] = manifest["event_count"] + len(selected)
    updated["archived_original_bytes"] = len(reconstructed)
    updated["archived_original_lines"] = _line_count(reconstructed)
    updated["archived_original_sha256"] = _sha256(reconstructed)
    updated["segments"] = manifest["segments"] + [
        record for record, _payload in additions
    ]
    updated_manifest_bytes = (
        json.dumps(updated, indent=2, sort_keys=True) + "\n"
    ).encode()
    updated_live = _live_index(updated) + live[tail_offset:]
    journal_mode = stat.S_IMODE(journal_path.stat().st_mode)
    manifest_mode = stat.S_IMODE(manifest_path.stat().st_mode)
    installed: list[Path] = []
    try:
        for record, payload in additions:
            path = archive_dir / record["path"]
            with path.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            installed.append(path)
        _replace_bytes(manifest_path, updated_manifest_bytes, mode=manifest_mode)
        _replace_bytes(journal_path, updated_live, mode=journal_mode)
        verify_journal(journal_path, manifest_path)
    except BaseException:
        _replace_bytes(manifest_path, manifest_bytes, mode=manifest_mode)
        _replace_bytes(journal_path, live, mode=journal_mode)
        for path in reversed(installed):
            path.unlink(missing_ok=True)
        raise
    return manifest_path


def migrate_journal(
    journal_path: Path,
    archive_dir: Path,
    *,
    cutoff_event_id: str,
    shard_size: int = 50,
) -> Path:
    """Create or append a byte-verifiable archive and rotate the live prefix."""
    if shard_size < 1:
        raise JournalIntegrityError("shard_size must be positive")
    if archive_dir.exists():
        return _append_journal_archive(
            journal_path,
            archive_dir,
            cutoff_event_id=cutoff_event_id,
            shard_size=shard_size,
        )

    original = journal_path.read_bytes()
    events = _events(original)
    _require_contiguous(events)
    if events[-1].event_id != cutoff_event_id:
        raise JournalIntegrityError(
            f"cutoff {cutoff_event_id} does not match last event "
            f"{events[-1].event_id}"
        )

    segment_payloads: list[tuple[dict[str, Any], bytes]] = []
    prologue = original[: events[0].offset]
    segment_payloads.append(
        (
            _segment_record(
                path="prologue.md",
                payload=prologue,
                first_event_id=None,
                last_event_id=None,
            ),
            prologue,
        )
    )
    segment_payloads.extend(
        _event_segment_payloads(original, events, shard_size=shard_size)
    )

    reconstructed = b"".join(payload for _, payload in segment_payloads)
    if reconstructed != original:
        raise JournalIntegrityError("in-memory shard reconstruction mismatch")

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "first_event_id": events[0].event_id,
        "last_event_id": events[-1].event_id,
        "event_count": len(events),
        "archived_original_bytes": len(original),
        "archived_original_lines": _line_count(original),
        "archived_original_sha256": _sha256(original),
        "segments": [record for record, _ in segment_payloads],
    }
    temporary_archive = archive_dir.with_name(
        f".{archive_dir.name}.tmp-{os.getpid()}"
    )
    if temporary_archive.exists():
        raise JournalIntegrityError(
            f"temporary archive path already exists: {temporary_archive}"
        )
    temporary_archive.mkdir()
    try:
        for record, payload in segment_payloads:
            (temporary_archive / record["path"]).write_bytes(payload)
        manifest_path = temporary_archive / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        os.replace(temporary_archive, archive_dir)
    except BaseException:
        if temporary_archive.exists() and not any(temporary_archive.iterdir()):
            temporary_archive.rmdir()
        raise

    temporary_journal = journal_path.with_name(
        f".{journal_path.name}.tmp-{os.getpid()}"
    )
    if temporary_journal.exists():
        raise JournalIntegrityError(
            f"temporary journal path already exists: {temporary_journal}"
        )
    journal_mode = stat.S_IMODE(journal_path.stat().st_mode)
    with temporary_journal.open("xb") as stream:
        stream.write(_live_index(manifest))
    if journal_path.read_bytes() != original:
        temporary_journal.unlink()
        raise JournalIntegrityError("source journal changed during migration")
    os.chmod(temporary_journal, journal_mode)
    os.replace(temporary_journal, journal_path)
    return archive_dir / "manifest.json"


def _safe_segment_path(archive_dir: Path, value: object) -> Path:
    if not isinstance(value, str) or Path(value).name != value:
        raise JournalIntegrityError(f"unsafe segment path: {value!r}")
    path = archive_dir / value
    if path.is_symlink() or not path.is_file():
        raise JournalIntegrityError(f"missing or non-regular segment: {value}")
    return path


def verify_journal(journal_path: Path, manifest_path: Path) -> dict[str, Any]:
    """Verify immutable segments, reconstruction, and logical event order."""
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != 1:
        raise JournalIntegrityError("unsupported manifest schema_version")
    segments = manifest.get("segments")
    if not isinstance(segments, list) or not segments:
        raise JournalIntegrityError("manifest has no segments")

    archive_dir = manifest_path.parent
    payloads: list[bytes] = []
    for segment in segments:
        if not isinstance(segment, dict):
            raise JournalIntegrityError("malformed segment record")
        path = _safe_segment_path(archive_dir, segment.get("path"))
        payload = path.read_bytes()
        if len(payload) != segment.get("bytes"):
            raise JournalIntegrityError(f"byte count mismatch for {path.name}")
        if _line_count(payload) != segment.get("lines"):
            raise JournalIntegrityError(f"line count mismatch for {path.name}")
        if _sha256(payload) != segment.get("sha256"):
            raise JournalIntegrityError(f"SHA-256 mismatch for {path.name}")
        payloads.append(payload)

    reconstructed = b"".join(payloads)
    if len(reconstructed) != manifest.get("archived_original_bytes"):
        raise JournalIntegrityError("reconstructed byte count mismatch")
    if _line_count(reconstructed) != manifest.get("archived_original_lines"):
        raise JournalIntegrityError("reconstructed line count mismatch")
    if _sha256(reconstructed) != manifest.get("archived_original_sha256"):
        raise JournalIntegrityError("reconstructed SHA-256 mismatch")

    archived_events = _events(reconstructed)
    _require_contiguous(archived_events)
    if len(archived_events) != manifest.get("event_count"):
        raise JournalIntegrityError("archived event count mismatch")
    if archived_events[0].event_id != manifest.get("first_event_id"):
        raise JournalIntegrityError("archived first event mismatch")
    if archived_events[-1].event_id != manifest.get("last_event_id"):
        raise JournalIntegrityError("archived last event mismatch")

    current_events = _events(journal_path.read_bytes())
    all_events = archived_events + current_events
    _require_contiguous(all_events)
    return {
        "status": "ok",
        "archived_sha256": _sha256(reconstructed),
        "archived_event_count": len(archived_events),
        "current_event_count": len(current_events),
        "last_event_id": all_events[-1].event_id,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    migrate = subparsers.add_parser("migrate")
    migrate.add_argument(
        "--journal",
        type=Path,
        default=Path(
            "docs/research/neurips-2026-workshop/33-execution-journal.md"
        ),
    )
    migrate.add_argument(
        "--archive",
        type=Path,
        default=Path(
            "docs/research/neurips-2026-workshop/execution-journal"
        ),
    )
    migrate.add_argument("--cutoff", required=True)
    migrate.add_argument("--shard-size", type=int, default=50)

    check = subparsers.add_parser("check")
    check.add_argument(
        "--journal",
        type=Path,
        default=Path(
            "docs/research/neurips-2026-workshop/33-execution-journal.md"
        ),
    )
    check.add_argument(
        "--manifest",
        type=Path,
        default=Path(
            "docs/research/neurips-2026-workshop/"
            "execution-journal/manifest.json"
        ),
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "migrate":
        result: dict[str, Any] = verify_journal(
            args.journal,
            migrate_journal(
                args.journal,
                args.archive,
                cutoff_event_id=args.cutoff,
                shard_size=args.shard_size,
            ),
        )
    else:
        result = verify_journal(args.journal, args.manifest)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
