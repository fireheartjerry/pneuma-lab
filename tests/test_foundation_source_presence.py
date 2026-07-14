"""Filesystem-metadata-only dataset family presence probes."""

from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.foundation.source_presence import probe_family_presence


def test_blocked_presence_probe_never_opens_payload(tmp_path, monkeypatch) -> None:
    blocked = tmp_path / "processed" / "swe-chat"
    blocked.mkdir(parents=True)
    (blocked / "present.bin").write_bytes(b"metadata probe fixture")
    monkeypatch.setattr(
        Path,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("payload opened")
        ),
    )
    report = probe_family_presence(tmp_path, "swe-chat")
    assert report.inspection == "filesystem_metadata_only"
    assert report.payload_opened is False
    assert report.file_count == 1


def test_presence_probe_counts_nested_files_bytes_and_newest_mtime(
    tmp_path: Path,
) -> None:
    root = tmp_path / "processed" / "swe-evo"
    nested = root / "nested"
    nested.mkdir(parents=True)
    first = root / "first.bin"
    second = nested / "second.bin"
    first.write_bytes(b"one")
    second.write_bytes(b"four")

    report = probe_family_presence(tmp_path, "swe-evo")

    assert report.family == "swe-evo"
    assert report.exists is True
    assert report.file_count == 2
    assert report.byte_count == 7
    assert report.newest_mtime_ns == max(
        first.stat().st_mtime_ns,
        second.stat().st_mtime_ns,
    )


def test_presence_probe_reports_absent_family_without_payload_access(
    tmp_path: Path,
) -> None:
    report = probe_family_presence(tmp_path, "swe-polybench")
    assert report.exists is False
    assert report.file_count == 0
    assert report.byte_count == 0
    assert report.newest_mtime_ns is None
    assert report.payload_opened is False


def test_presence_probe_skips_symlink_that_escapes_family_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "processed" / "swe-chat"
    root.mkdir(parents=True)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"must not be counted")
    link = root / "escape.bin"
    try:
        link.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    report = probe_family_presence(tmp_path, "swe-chat")

    assert report.exists is True
    assert report.file_count == 0
    assert report.byte_count == 0
    assert report.newest_mtime_ns is None
