"""Security tests for descriptor-bound multi-file publication."""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest


def _publication_module():
    return importlib.import_module("pneuma_lab.resampling_null.publication")


def _fd_set() -> set[int]:
    return {int(name) for name in os.listdir("/proc/self/fd") if name.isdigit()}


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
        path for path in (run_root / "held-sources").rglob("*") if path.is_file()
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
    original_rename = publication._rename_no_replace
    raced = False

    def replace_before_quarantine(
        source_name: str,
        destination_name: str,
        *,
        source_descriptor: int,
        destination_descriptor: int,
    ) -> None:
        nonlocal raced
        if (
            not raced
            and source_name == "item.json"
            and ".rollback-" in destination_name
        ):
            raced = True
            os.replace(
                peer_source.name,
                source_name,
                src_dir_fd=source_descriptor,
                dst_dir_fd=source_descriptor,
            )
        original_rename(
            source_name,
            destination_name,
            source_descriptor=source_descriptor,
            destination_descriptor=destination_descriptor,
        )

    monkeypatch.setattr(
        publication,
        "_rename_no_replace",
        replace_before_quarantine,
    )
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


def test_owned_content_mutation_is_not_clean_rollback(
    tmp_path: Path,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()

    with pytest.raises(
        publication.PublicationRollbackError,
        match=r"rollback incomplete.*item\.json.*content changed",
    ) as captured:
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            (run_root / "item.json").write_bytes(b"mutated\n")
            raise OSError("injected terminal failure")

    assert isinstance(captured.value.__cause__, OSError)
    assert (run_root / "item.json").read_bytes() == b"mutated\n"


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
        path.read_bytes() == b"owned\n" for path in run_root.iterdir() if path.is_file()
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


def test_quarantine_move_never_replaces_preexisting_peer_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    transaction_token = "1" * 32
    monkeypatch.setattr(
        publication.secrets,
        "token_hex",
        lambda _bytes: transaction_token,
    )
    quarantine = run_root / f".pneuma-{transaction_token}.rollback-1"
    peer_bytes = b"preexisting peer quarantine\n"
    quarantine.write_bytes(peer_bytes)

    with pytest.raises(
        publication.PublicationRollbackError,
        match=r"rollback incomplete.*item\.json.*rollback-1",
    ) as captured:
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            raise OSError("injected terminal failure")

    assert isinstance(captured.value.__cause__, OSError)
    assert quarantine.read_bytes() == peer_bytes
    assert (run_root / "item.json").read_bytes() == b"owned\n"


def test_quarantine_move_failure_collects_and_continues_all_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    original_unlink = publication.os.unlink
    temporary_failure_injected = False
    temporary_unlink_calls = 0

    def fail_first_temporary_unlink(
        path: str,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal temporary_failure_injected, temporary_unlink_calls
        if path.endswith(".tmp"):
            temporary_unlink_calls += 1
        if path.endswith(".tmp") and temporary_unlink_calls == 2:
            temporary_failure_injected = True
            raise PermissionError("injected second temporary unlink failure")
        original_unlink(path, dir_fd=dir_fd)

    def fail_second_quarantine(
        source_name: str,
        destination_name: str,
        *,
        source_descriptor: int,
        destination_descriptor: int,
    ) -> None:
        if source_name == "second.json":
            raise PermissionError("injected quarantine move denial")
        publication.os.rename(
            source_name,
            destination_name,
            src_dir_fd=source_descriptor,
            dst_dir_fd=destination_descriptor,
        )

    monkeypatch.setattr(publication.os, "unlink", fail_first_temporary_unlink)
    monkeypatch.setattr(
        publication,
        "_rename_no_replace",
        fail_second_quarantine,
        raising=False,
    )
    with pytest.raises(
        publication.PublicationRollbackError,
        match=r"rollback incomplete.*second\.json.*move denial",
    ) as captured:
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "first.json",
                b"first\n",
                role="fixture",
                media_type="application/json",
            )
            transaction.publish_bytes(
                "second.json",
                b"second\n",
                role="fixture",
                media_type="application/json",
            )

    assert isinstance(captured.value.__cause__, PermissionError)
    assert temporary_failure_injected
    assert not (run_root / "first.json").exists()
    assert (run_root / "second.json").read_bytes() == b"second\n"
    assert not list(run_root.glob("*.tmp"))


def test_quarantine_rollback_restores_symlink_peer_without_dereference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    peer_target = run_root / "peer-target.txt"
    peer_target.write_text("peer target", encoding="utf-8")
    original_name = publication.BoundPublication._quarantine_name
    injected = False

    def replace_before_name(
        transaction: object,
        index: int,
    ) -> str:
        nonlocal injected
        if not injected:
            injected = True
            (run_root / "item.json").unlink()
            (run_root / "item.json").symlink_to(peer_target.name)
        return original_name(transaction, index)

    monkeypatch.setattr(
        publication.BoundPublication,
        "_quarantine_name",
        replace_before_name,
    )
    with pytest.raises(OSError, match="injected terminal failure"):
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            raise OSError("injected terminal failure")

    restored = run_root / "item.json"
    assert injected
    assert restored.is_symlink()
    assert restored.readlink() == Path(peer_target.name)
    assert peer_target.read_text(encoding="utf-8") == "peer target"
    assert not list(run_root.glob("*.rollback-*"))


def test_quarantine_transient_inspection_failure_is_not_clean_rollback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    original_open = publication.os.open

    def deny_quarantine_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if isinstance(path, str) and ".rollback-" in path:
            raise PermissionError("injected quarantine inspection denial")
        return original_open(path, flags, mode, dir_fd=dir_fd)

    with pytest.raises(
        publication.PublicationRollbackError,
        match=r"rollback incomplete.*item\.json.*inspection denial",
    ) as captured:
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            monkeypatch.setattr(publication.os, "open", deny_quarantine_open)
            raise OSError("injected terminal failure")

    assert isinstance(captured.value.__cause__, OSError)
    assert (run_root / "item.json").read_bytes() == b"owned\n"


def test_created_parent_fsync_failure_closes_unregistered_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    baseline = _fd_set()
    original_fsync = publication.os.fsync
    failed = False

    def fail_created_parent_fsync(descriptor: int) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected created-parent fsync failure")
        original_fsync(descriptor)

    monkeypatch.setattr(publication.os, "fsync", fail_created_parent_fsync)
    with pytest.raises(OSError, match="injected created-parent fsync failure"):
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "sources/item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )

    assert _fd_set() == baseline


def test_parent_registration_fstat_failure_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    baseline = _fd_set()
    original_fstat = publication.os.fstat
    calls = 0

    def fail_registration_fstat(descriptor: int):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("injected registration fstat failure")
        return original_fstat(descriptor)

    monkeypatch.setattr(publication.os, "fstat", fail_registration_fstat)
    with pytest.raises(OSError, match="injected registration fstat failure"):
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "sources/item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )

    assert calls >= 3
    assert _fd_set() == baseline


def test_directory_rollback_preserves_empty_peer_replacement(
    tmp_path: Path,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    moved_owned = run_root / "moved-owned-sources"

    with pytest.raises(
        publication.PublicationRollbackError,
        match=r"rollback incomplete.*sources.*identity changed",
    ) as captured:
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "sources/item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )
            (run_root / "sources").rename(moved_owned)
            (run_root / "sources").mkdir()
            raise OSError("injected terminal failure")

    assert isinstance(captured.value.__cause__, OSError)
    assert (run_root / "sources").is_dir()
    assert list((run_root / "sources").iterdir()) == []
    assert moved_owned.is_dir()


def test_temporary_rollback_preserves_peer_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    publication = _publication_module()
    run_root = tmp_path / "run"
    run_root.mkdir()
    original_unlink = publication.os.unlink
    peer_bytes = b"peer temporary replacement\n"
    replaced_name: str | None = None

    def replace_temporary_before_cleanup(
        path: str,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal replaced_name
        if path.endswith(".tmp") and replaced_name is None:
            assert dir_fd is not None
            original_unlink(path, dir_fd=dir_fd)
            parent = Path(os.readlink(f"/proc/self/fd/{dir_fd}"))
            (parent / path).write_bytes(peer_bytes)
            replaced_name = path
            raise PermissionError("injected temporary replacement race")
        original_unlink(path, dir_fd=dir_fd)

    monkeypatch.setattr(
        publication.os,
        "unlink",
        replace_temporary_before_cleanup,
    )
    with pytest.raises(
        PermissionError,
        match="injected temporary replacement race",
    ) as captured:
        with publication.BoundPublication(run_root) as transaction:
            transaction.publish_bytes(
                "item.json",
                b"owned\n",
                role="fixture",
                media_type="application/json",
            )

    assert captured.value.__cause__ is None
    assert replaced_name is not None
    peer = run_root / replaced_name
    assert peer.read_bytes() == peer_bytes
