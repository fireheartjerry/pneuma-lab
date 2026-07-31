from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.research.execution_journal import (
    JournalIntegrityError,
    migrate_journal,
    verify_journal,
)


def _journal_bytes(event_ids: list[str]) -> bytes:
    payload = b"# Test journal\n\n## Contract\n\nKeep every event.\n\n"
    for event_id in event_ids:
        payload += f"### {event_id} \u2014 test\n\n- payload: {event_id}\n".encode()
    return payload


def test_migration_preserves_exact_bytes_and_builds_small_live_index(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "33-execution-journal.md"
    archive = tmp_path / "execution-journal"
    original = _journal_bytes(
        [f"EJ-20260728-{sequence:04d}" for sequence in range(1, 6)]
    )
    journal.write_bytes(original)

    manifest_path = migrate_journal(
        journal,
        archive,
        cutoff_event_id="EJ-20260728-0005",
        shard_size=2,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reconstructed = b"".join(
        (archive / segment["path"]).read_bytes()
        for segment in manifest["segments"]
    )
    assert reconstructed == original
    assert "- payload:" not in journal.read_text(encoding="utf-8")
    assert "EJ-20260728-0005" in journal.read_text(encoding="utf-8")
    assert verify_journal(journal, manifest_path)["last_event_id"] == (
        "EJ-20260728-0005"
    )


def test_migration_refuses_noncontiguous_events(tmp_path: Path) -> None:
    journal = tmp_path / "33-execution-journal.md"
    journal.write_bytes(
        _journal_bytes(["EJ-20260728-0001", "EJ-20260728-0003"])
    )

    with pytest.raises(JournalIntegrityError, match="noncontiguous"):
        migrate_journal(
            journal,
            tmp_path / "execution-journal",
            cutoff_event_id="EJ-20260728-0003",
            shard_size=2,
        )


def test_verifier_rejects_archived_byte_tampering(tmp_path: Path) -> None:
    journal = tmp_path / "33-execution-journal.md"
    archive = tmp_path / "execution-journal"
    journal.write_bytes(
        _journal_bytes(
            [f"EJ-20260728-{sequence:04d}" for sequence in range(1, 4)]
        )
    )
    manifest_path = migrate_journal(
        journal,
        archive,
        cutoff_event_id="EJ-20260728-0003",
        shard_size=2,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_event_shard = archive / manifest["segments"][1]["path"]
    tampered = bytearray(first_event_shard.read_bytes())
    tampered[-2] ^= 1
    first_event_shard.write_bytes(tampered)

    with pytest.raises(JournalIntegrityError, match="SHA-256"):
        verify_journal(journal, manifest_path)


def test_migration_never_spans_date_boundaries_in_a_shard(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "33-execution-journal.md"
    archive = tmp_path / "execution-journal"
    journal.write_bytes(
        _journal_bytes(
            [
                "EJ-20260728-0001",
                "EJ-20260728-0002",
                "EJ-20260729-0001",
                "EJ-20260729-0002",
            ]
        )
    )

    manifest_path = migrate_journal(
        journal,
        archive,
        cutoff_event_id="EJ-20260729-0002",
        shard_size=50,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    event_paths = [segment["path"] for segment in manifest["segments"][1:]]
    assert event_paths == [
        "events-20260728-0001-0002.md",
        "events-20260729-0001-0002.md",
    ]


def test_migration_appends_only_a_contiguous_live_prefix(tmp_path: Path) -> None:
    journal = tmp_path / "33-execution-journal.md"
    archive = tmp_path / "execution-journal"
    journal.write_bytes(
        _journal_bytes(
            [f"EJ-20260728-{sequence:04d}" for sequence in range(1, 4)]
        )
    )
    manifest_path = migrate_journal(
        journal,
        archive,
        cutoff_event_id="EJ-20260728-0003",
        shard_size=2,
    )
    with journal.open("ab") as stream:
        stream.write(
            _journal_bytes(
                [f"EJ-20260728-{sequence:04d}" for sequence in range(4, 8)]
            ).split(b"Keep every event.\n\n", 1)[1]
        )

    migrate_journal(
        journal,
        archive,
        cutoff_event_id="EJ-20260728-0005",
        shard_size=2,
    )

    verified = verify_journal(journal, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert verified == {
        "status": "ok",
        "archived_sha256": manifest["archived_original_sha256"],
        "archived_event_count": 5,
        "current_event_count": 2,
        "last_event_id": "EJ-20260728-0007",
    }
    assert manifest["segments"][-1]["path"] == (
        "events-20260728-0004-0005.md"
    )
    assert "### EJ-20260728-0004 " not in journal.read_text(encoding="utf-8")
    assert "### EJ-20260728-0006 " in journal.read_text(encoding="utf-8")
