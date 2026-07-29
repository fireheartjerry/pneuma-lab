"""Security tests for descriptor-bound multi-file publication."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest


def _publication_module():
    return importlib.import_module("pneuma_lab.resampling_null.publication")


def _fd_set() -> set[int]:
    return {
        int(name)
        for name in os.listdir("/proc/self/fd")
        if name.isdigit()
    }


def test_bound_publication_rejects_named_root_swap_without_escape(
    tmp_path: Path,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    bound_root = tmp_path / "bound-run"
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(
        publication.RecordValidationError,
        match="run_root identity changed",
    ):
        with publication.BoundPublication(run_root) as transaction:
            run_root.rename(bound_root)
            run_root.symlink_to(outside, target_is_directory=True)
            transaction.publish_bytes(
                "sources/item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            transaction.commit()

    assert list(outside.iterdir()) == []
    assert list(bound_root.rglob("*")) == []


def test_bound_publication_rejects_intermediate_swap_without_escape(
    tmp_path: Path,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(
        publication.RecordValidationError,
        match="directory identity changed",
    ):
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "sources/first.json",
                b"first\n",
                role="fixture",
                media_type="application/json",
            )
            (run_root / "sources").rename(run_root / "held-sources")
            (run_root / "sources").symlink_to(
                outside,
                target_is_directory=True,
            )
            transaction.publish_bytes(
                "sources/second.json",
                b"second\n",
                role="fixture",
                media_type="application/json",
            )
            transaction.commit()

    assert list(outside.iterdir()) == []
    assert [
        path
        for path in (run_root / "held-sources").rglob("*")
        if path.is_file()
    ] == []


@pytest.mark.parametrize("failing_call", ["fstat", "stat"])
def test_bound_publication_closes_root_descriptor_when_binding_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failing_call: str,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    baseline = _fd_set()

    if failing_call == "fstat":
        original_fstat = publication.os.fstat
        failed = False

        def fail_root_fstat(descriptor: int):
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("injected root fstat failure")
            return original_fstat(descriptor)

        monkeypatch.setattr(publication.os, "fstat", fail_root_fstat)
    else:
        original_stat = publication.os.stat
        failed = False

        def fail_named_root_stat(
            path: object,
            *,
            dir_fd: int | None = None,
            follow_symlinks: bool = True,
        ):
            nonlocal failed
            if (
                not failed
                and dir_fd is None
                and Path(path) == run_root
                and not follow_symlinks
            ):
                failed = True
                raise OSError("injected named root stat failure")
            return original_stat(
                path,
                dir_fd=dir_fd,
                follow_symlinks=follow_symlinks,
            )

        monkeypatch.setattr(publication.os, "stat", fail_named_root_stat)

    with pytest.raises(OSError, match=f"injected .* {failing_call} failure"):
        with publication.BoundPublication(run_root):
            pass
    assert _fd_set() == baseline


def test_quarantine_rollback_restores_peer_replaced_at_final_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    peer_bytes = b"peer-winner\n"
    peer_source = run_root / "peer.tmp"
    peer_source.write_bytes(peer_bytes)
    original_rename = publication.os.rename
    raced = False

    def replace_before_quarantine(
        source_name: str,
        destination_name: str,
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal raced
        if (
            not raced
            and source_name == "item.json"
            and ".rollback-" in destination_name
        ):
            raced = True
            assert src_dir_fd is not None
            os.replace(
                peer_source.name,
                source_name,
                src_dir_fd=src_dir_fd,
                dst_dir_fd=src_dir_fd,
            )
        original_rename(
            source_name,
            destination_name,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(publication.os, "rename", replace_before_quarantine)
    with pytest.raises(OSError, match="injected terminal failure"):
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            raise OSError("injected terminal failure")

    assert raced
    assert (run_root / "item.json").read_bytes() == peer_bytes
    assert not list(run_root.glob("*.rollback-*"))


def test_commit_rejects_and_preserves_peer_replaced_after_publication(
    tmp_path: Path,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    peer_bytes = b"peer-winner\n"

    with pytest.raises(
        publication.RecordValidationError,
        match=r"published file identity changed.*item\.json",
    ):
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            peer = run_root / "peer.tmp"
            peer.write_bytes(peer_bytes)
            peer.replace(run_root / "item.json")
            transaction.commit()

    assert (run_root / "item.json").read_bytes() == peer_bytes
    assert not list(run_root.glob("*.rollback-*"))


def test_quarantine_rollback_rejects_hardlink_alias_as_incomplete(
    tmp_path: Path,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()

    with pytest.raises(
        publication.PublicationRollbackError,
        match=r"rollback incomplete.*item\.json.*link count",
    ) as captured:
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            os.link(run_root / "item.json", run_root / "alias.json")
            raise OSError("injected terminal failure")

    assert isinstance(captured.value.__cause__, OSError)
    assert (run_root / "alias.json").read_bytes() == b"owned\n"
    assert any(
        path.read_bytes() == b"owned\n"
        for path in run_root.iterdir()
        if path.is_file()
    )


def test_temporary_cleanup_denial_names_exact_residual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    original_unlink = publication.os.unlink

    def deny_temporary_unlink(
        path: str,
        *,
        dir_fd: int | None = None,
    ) -> None:
        if path.endswith(".tmp"):
            raise PermissionError("injected temporary cleanup denial")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(publication.os, "unlink", deny_temporary_unlink)
    with pytest.raises(
        publication.PublicationRollbackError,
        match=r"rollback incomplete.*\.tmp",
    ) as captured:
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )

    assert isinstance(captured.value.__cause__, PermissionError)
    residuals = sorted(path.name for path in run_root.glob("*.tmp"))
    assert len(residuals) == 1
    assert residuals[0] in str(captured.value)
