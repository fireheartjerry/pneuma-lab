"""Descriptor confinement and caching tests for authority references."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null import authority_refs
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.types import ArtifactRef


def test_authority_reader_caches_verified_reference_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "run"
    source = root / "sources" / "asset.json"
    source.parent.mkdir(parents=True)
    payload = b'{"asset":"authority"}'
    source.write_bytes(payload)
    ref = ArtifactRef(
        role="fixture",
        relative_path="sources/asset.json",
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type="application/json",
    )
    original_open = authority_refs.os.open
    asset_opens = 0

    def count_asset_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal asset_opens
        if path == "asset.json":
            asset_opens += 1
        return original_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(authority_refs.os, "open", count_asset_open)
    with authority_refs.AuthorityRefReader(root) as reader:
        assert reader.read_bytes(ref) == payload
        assert reader.read_bytes(ref) == payload

    assert asset_opens == 1


@pytest.mark.parametrize(
    "relative_path",
    [
        "controller-artifacts/clock_source/forged",
        "study-manifest.json",
        "operational/clock.json",
        "wrong-namespace/clock.json",
    ],
)
def test_authority_reader_rejects_cross_class_path_before_open(
    tmp_path: Path,
    relative_path: str,
) -> None:
    root = tmp_path / "run"
    payload = b'{"clock":"forged"}'
    digest = hashlib.sha256(payload).hexdigest()
    path = root / relative_path
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)
    ref = ArtifactRef(
        "clock_source",
        relative_path,
        digest,
        len(payload),
        "application/json",
    )
    with authority_refs.AuthorityRefReader(root) as reader:
        with pytest.raises(RecordValidationError, match="authority namespace"):
            reader.read_bytes(ref)


def test_authority_reader_rejects_path_and_inode_aliases_but_repeats_exact_ref(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    source = root / "sources" / "clock.json"
    source.parent.mkdir(parents=True)
    payload = canonical_json_bytes({"clock": "fixture"}, indent=None)
    source.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    clock_ref = ArtifactRef(
        "clock_source",
        "sources/clock.json",
        digest,
        len(payload),
        "application/json",
    )
    same_path_watchdog_ref = ArtifactRef(
        "watchdog_source",
        "sources/clock.json",
        digest,
        len(payload),
        "application/json",
    )
    hardlink = root / "sources" / "watchdog.json"
    os.link(source, hardlink)
    hardlink_watchdog_ref = ArtifactRef(
        "watchdog_source",
        "sources/watchdog.json",
        digest,
        len(payload),
        "application/json",
    )
    with authority_refs.AuthorityRefReader(root) as reader:
        assert reader.verify_closure(
            clock_ref,
            field="clock",
            expected_role="clock_source",
        ) == {"clock": "fixture"}
        assert reader.verify_closure(
            clock_ref,
            field="clock repeat",
            expected_role="clock_source",
        ) == {"clock": "fixture"}
        with pytest.raises(RecordValidationError, match="relative path alias"):
            reader.verify_closure(
                same_path_watchdog_ref,
                field="watchdog",
                expected_role="watchdog_source",
            )
        with pytest.raises(RecordValidationError, match="physical file alias"):
            reader.verify_closure(
                hardlink_watchdog_ref,
                field="hardlink watchdog",
                expected_role="watchdog_source",
            )
