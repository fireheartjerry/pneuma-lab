"""Study-seal integration tests for the publication transaction."""

from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.resampling_null.publication import BoundPublication
from tests.resampling_null.provider_authority_fixture import (
    ProviderAuthorityFixture,
)


def _file_paths(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )


def test_study_seal_preserves_peer_manifest_on_no_replace_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = ProviderAuthorityFixture.build_study(
        tmp_path,
        failure_mode=None,
    )
    peer_bytes = b"peer-owned manifest"
    original = BoundPublication.publish_bytes
    injected = False

    def race_manifest(
        publication: BoundPublication,
        relative_path: str,
        payload: bytes,
        *,
        role: str,
        media_type: str,
    ):
        nonlocal injected
        if relative_path == "study-manifest.json" and not injected:
            injected = True
            (fixture.run_root / relative_path).write_bytes(peer_bytes)
        return original(
            publication,
            relative_path,
            payload,
            role=role,
            media_type=media_type,
        )

    monkeypatch.setattr(BoundPublication, "publish_bytes", race_manifest)
    with pytest.raises(FileExistsError):
        fixture.seal()

    assert injected
    assert (fixture.run_root / "study-manifest.json").read_bytes() == peer_bytes
    assert _file_paths(fixture.run_root) == ["study-manifest.json"]


def test_study_seal_rolls_back_known_later_failure_and_retries_cleanly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = ProviderAuthorityFixture.build_study(
        tmp_path,
        failure_mode=None,
    )
    keep = fixture.run_root / "preexisting" / "keep.txt"
    keep.parent.mkdir()
    keep.write_text("keep", encoding="utf-8")
    original = BoundPublication.publish_bytes
    published_roles: list[str] = []

    def fail_roster(
        publication: BoundPublication,
        relative_path: str,
        payload: bytes,
        *,
        role: str,
        media_type: str,
    ):
        if role == "roster":
            raise OSError("injected roster publication failure")
        result = original(
            publication,
            relative_path,
            payload,
            role=role,
            media_type=media_type,
        )
        published_roles.append(role)
        return result

    monkeypatch.setattr(BoundPublication, "publish_bytes", fail_roster)
    with pytest.raises(OSError, match="injected roster publication failure"):
        fixture.seal()

    assert published_roles
    assert _file_paths(fixture.run_root) == ["preexisting/keep.txt"]
    assert keep.read_text(encoding="utf-8") == "keep"

    monkeypatch.setattr(BoundPublication, "publish_bytes", original)
    manifest_ref = fixture.seal()
    assert (fixture.run_root / manifest_ref.relative_path).is_file()
    assert keep.read_text(encoding="utf-8") == "keep"
