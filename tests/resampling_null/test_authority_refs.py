"""Descriptor confinement and caching tests for authority references."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pneuma_lab.resampling_null import authority_refs
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
