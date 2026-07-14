"""Canonical, atomic foundation artifact helpers."""

from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

import pytest

from pneuma_lab.foundation import artifacts
from pneuma_lab.foundation.artifacts import (
    ArtifactPublicationError,
    bind_artifact_publication,
    sha256_file,
    write_atomic_bytes,
    write_atomic_json,
    write_atomic_jsonl,
)


def test_linux_mount_id_parser_and_transition_guard() -> None:
    assert artifacts._parse_linux_mount_id(
        "pos:\t0\nflags:\t0100000\nmnt_id:\t417\nino:\t12\n"
    ) == 417
    artifacts._require_single_mount_identity(417, (417, 417, 417))
    with pytest.raises(ArtifactPublicationError, match="mount"):
        artifacts._require_single_mount_identity(417, (417, 901, 417))


def test_protected_identity_alias_guard_uses_device_and_inode() -> None:
    artifacts._reject_protected_identity_alias(
        ((11, 21, 31), (11, 22, 31)),
        ((12, 21, 31),),
    )
    with pytest.raises(ArtifactPublicationError, match="protected|alias"):
        artifacts._reject_protected_identity_alias(
            ((11, 21, 901),),
            ((11, 21, 417),),
        )


def test_linux_mountinfo_parser_unescapes_nested_mount_roots() -> None:
    mounts = artifacts._parse_linux_mountinfo(
        "41 25 8:1 /protected\\040data/subtree "
        "/repo\\040root rw,nosuid shared:7 - ext4 /dev/sda1 rw\n"
        "52 41 8:1 /protected\\040data/subtree/nested "
        "/repo\\040root/nested rw - ext4 /dev/sda1 rw\n"
    )
    assert mounts[41].device == "8:1"
    assert mounts[41].root == PurePosixPath("/protected data/subtree")
    assert mounts[41].mountpoint == PurePosixPath("/repo root")
    assert artifacts._underlying_location_for_mount(
        mounts[41],
        PurePosixPath("/repo root/build/out"),
    ) == ("8:1", PurePosixPath("/protected data/subtree/build/out"))
    assert artifacts._underlying_location_for_mount(
        mounts[52],
        PurePosixPath("/repo root/nested/output"),
    ) == (
        "8:1",
        PurePosixPath("/protected data/subtree/nested/output"),
    )


def test_underlying_location_guard_allows_sibling_and_rejects_descendants() -> None:
    protected = (("8:1", PurePosixPath("/srv/pneuma-data")),)
    artifacts._reject_protected_underlying_alias(
        (("8:1", PurePosixPath("/srv/repo")),),
        protected,
    )
    with pytest.raises(ArtifactPublicationError, match="protected|alias"):
        artifacts._reject_protected_underlying_alias(
            (("8:1", PurePosixPath("/srv/pneuma-data")),),
            protected,
        )
    with pytest.raises(ArtifactPublicationError, match="protected|alias"):
        artifacts._reject_protected_underlying_alias(
            (("8:1", PurePosixPath("/srv/pneuma-data/subtree/repo")),),
            protected,
        )
    artifacts._reject_protected_underlying_alias(
        (("9:1", PurePosixPath("/srv/pneuma-data/subtree")),),
        protected,
    )


@pytest.mark.parametrize(
    "mountinfo",
    (
        "",
        "41 25 bad-device / /repo rw - ext4 /dev/sda rw\n",
        "41 25 8:1 relative /repo rw - ext4 /dev/sda rw\n",
        "41 25 8:1 / /repo\\12x rw - ext4 /dev/sda rw\n",
    ),
)
def test_linux_mountinfo_parser_fails_closed(mountinfo: str) -> None:
    with pytest.raises(ArtifactPublicationError, match="mount"):
        artifacts._parse_linux_mountinfo(mountinfo)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux mount IDs")
def test_bind_mount_output_is_rejected_before_publication(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    output = repo_root / "build/out"
    output.mkdir(parents=True)
    protected = tmp_path / "pneuma-data"
    protected.mkdir()
    mounted = subprocess.run(
        ["mount", "--bind", str(protected), str(output)],
        capture_output=True,
        check=False,
        text=True,
    )
    if mounted.returncode != 0:
        pytest.skip(f"bind mounts unavailable: {mounted.stderr.strip()}")
    try:
        with pytest.raises(ArtifactPublicationError, match="mount"):
            with bind_artifact_publication(
                output,
                anchor_root=repo_root,
                allowed_root=repo_root / "build",
                forbidden_roots=(protected,),
            ) as publication:
                publication.write_bytes(output / "escaped.bin", b"blocked")
        assert tuple(protected.iterdir()) == ()
    finally:
        unmounted = subprocess.run(
            ["umount", str(output)],
            capture_output=True,
            check=False,
            text=True,
        )
        if unmounted.returncode != 0:
            pytest.fail(f"test bind mount could not be unmounted: {unmounted.stderr}")


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux bind mount")
def test_bind_mounted_protected_root_cannot_be_repository_anchor(
    tmp_path: Path,
) -> None:
    protected = tmp_path / "pneuma-data"
    output_relative = Path("build/out")
    (protected / output_relative).mkdir(parents=True)
    sentinel = protected / "sentinel.txt"
    sentinel.write_text("immutable", encoding="utf-8")
    before = tuple(sorted(path.relative_to(protected) for path in protected.rglob("*")))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    mounted = subprocess.run(
        ["mount", "--bind", str(protected), str(repo_root)],
        capture_output=True,
        check=False,
        text=True,
    )
    if mounted.returncode != 0:
        pytest.skip(f"bind mounts unavailable: {mounted.stderr.strip()}")
    try:
        with pytest.raises(ArtifactPublicationError, match="protected|alias"):
            with bind_artifact_publication(
                repo_root / output_relative,
                anchor_root=repo_root,
                allowed_root=repo_root / "build",
                forbidden_roots=(protected,),
            ) as publication:
                publication.write_bytes(
                    repo_root / output_relative / "escaped.bin",
                    b"blocked",
                )
        after = tuple(
            sorted(path.relative_to(protected) for path in protected.rglob("*"))
        )
        assert after == before
        assert sentinel.read_text(encoding="utf-8") == "immutable"
    finally:
        unmounted = subprocess.run(
            ["umount", str(repo_root)],
            capture_output=True,
            check=False,
            text=True,
        )
        if unmounted.returncode != 0:
            pytest.fail(f"test bind mount could not be unmounted: {unmounted.stderr}")


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux bind mount")
def test_bind_mounted_protected_descendant_cannot_be_repository_anchor(
    tmp_path: Path,
) -> None:
    protected = tmp_path / "pneuma-data"
    protected_subtree = protected / "nested/subtree"
    output_relative = Path("build/out")
    (protected_subtree / output_relative).mkdir(parents=True)
    sentinel = protected / "sentinel.txt"
    sentinel.write_text("immutable", encoding="utf-8")
    before = tuple(sorted(path.relative_to(protected) for path in protected.rglob("*")))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    mounted = subprocess.run(
        ["mount", "--bind", str(protected_subtree), str(repo_root)],
        capture_output=True,
        check=False,
        text=True,
    )
    if mounted.returncode != 0:
        pytest.skip(f"bind mounts unavailable: {mounted.stderr.strip()}")
    try:
        with pytest.raises(ArtifactPublicationError, match="protected|alias"):
            with bind_artifact_publication(
                repo_root / output_relative,
                anchor_root=repo_root,
                allowed_root=repo_root / "build",
                forbidden_roots=(protected,),
            ) as publication:
                publication.write_bytes(
                    repo_root / output_relative / "escaped.bin",
                    b"blocked",
                )
        after = tuple(
            sorted(path.relative_to(protected) for path in protected.rglob("*"))
        )
        assert after == before
        assert sentinel.read_text(encoding="utf-8") == "immutable"
    finally:
        unmounted = subprocess.run(
            ["umount", str(repo_root)],
            capture_output=True,
            check=False,
            text=True,
        )
        if unmounted.returncode != 0:
            pytest.fail(f"test bind mount could not be unmounted: {unmounted.stderr}")


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux mount IDs")
def test_commit_rechecks_bound_mount_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "repo/build/out"
    output.mkdir(parents=True)
    target = output / "artifact.bin"
    real_mount_id = artifacts._linux_mount_id_from_fd
    drift = False
    publication = None

    def changed_mount_id(descriptor: int) -> int:
        value = real_mount_id(descriptor)
        if drift and publication is not None:
            if descriptor == publication._directory_binding:
                return value + 1
        return value

    monkeypatch.setattr(artifacts, "_linux_mount_id_from_fd", changed_mount_id)
    with pytest.raises(ArtifactPublicationError, match="mount"):
        with bind_artifact_publication(
            output,
            anchor_root=tmp_path / "repo",
            allowed_root=tmp_path / "repo/build",
        ) as publication:
            publication.write_bytes(target, b"payload")
            drift = True
    assert not target.exists()


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="POSIX rename race")
def test_rename_into_forbidden_root_before_replace_rolls_back(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    output = repo_root / "build/out"
    output.mkdir(parents=True)
    forbidden = tmp_path / "pneuma-data"
    forbidden.mkdir()
    moved = forbidden / "moved-output"
    target = output / "artifact.bin"
    protected_write_observed = False

    with pytest.raises(
        ArtifactPublicationError,
        match="ancestry|output|publication",
    ):
        with bind_artifact_publication(
            output,
            anchor_root=repo_root,
            allowed_root=repo_root / "build",
            forbidden_roots=(forbidden,),
        ) as publication:
            real_replace = publication._replace

            def rename_then_replace(temporary_name: str, name: str) -> None:
                nonlocal protected_write_observed
                output.rename(moved)
                try:
                    real_replace(temporary_name, name)
                finally:
                    protected_write_observed = (moved / name).exists()

            monkeypatch.setattr(publication, "_replace", rename_then_replace)
            publication.write_bytes(target, b"payload")
    assert tuple(moved.iterdir()) == ()
    assert protected_write_observed is False


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="POSIX rename race")
def test_commit_rejects_output_renamed_after_last_write(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    output = repo_root / "build/out"
    output.mkdir(parents=True)
    forbidden = tmp_path / "pneuma-data"
    forbidden.mkdir()
    moved = forbidden / "moved-output"
    target = output / "artifact.bin"
    def move_before_final_verify(_publication) -> None:
        output.rename(moved)

    monkeypatch.setattr(
        artifacts.BoundArtifactPublication,
        "_before_final_verify",
        move_before_final_verify,
        raising=False,
    )
    with pytest.raises(ArtifactPublicationError, match="ancestry|output"):
        with bind_artifact_publication(
            output,
            anchor_root=repo_root,
            allowed_root=repo_root / "build",
            forbidden_roots=(forbidden,),
        ) as publication:
            publication.write_bytes(target, b"payload")
    assert tuple(moved.iterdir()) == ()


def test_commit_rejects_published_content_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "repo/build/out"
    output.mkdir(parents=True)
    target = output / "artifact.bin"

    def mutate_before_final_verify(_publication) -> None:
        target.write_bytes(b"tampered")

    monkeypatch.setattr(
        artifacts.BoundArtifactPublication,
        "_before_final_verify",
        mutate_before_final_verify,
        raising=False,
    )
    with pytest.raises(ArtifactPublicationError, match="content|digest|size"):
        with bind_artifact_publication(
            output,
            anchor_root=tmp_path / "repo",
            allowed_root=tmp_path / "repo/build",
        ) as publication:
            publication.write_bytes(target, b"expected")
    assert not target.exists()


def test_postcommit_backup_cleanup_failure_leaves_recoverable_state(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "repo/build/out"
    output.mkdir(parents=True)
    target = output / "artifact.bin"
    sibling = output / "artifact-hardlink.bin"
    target.write_bytes(b"preserved")
    os.link(target, sibling)

    with bind_artifact_publication(
        output,
        anchor_root=tmp_path / "repo",
        allowed_root=tmp_path / "repo/build",
    ) as publication:
        real_unlink = publication._unlink

        def fail_backup_cleanup(name: str, **kwargs) -> None:
            if name.endswith(".publication-backup"):
                raise OSError("injected backup cleanup failure")
            real_unlink(name, **kwargs)

        monkeypatch.setattr(publication, "_unlink", fail_backup_cleanup)
        publication.write_bytes(target, b"committed")

    assert target.read_bytes() == b"committed"
    assert sibling.read_bytes() == b"preserved"
    backups = tuple(
        path for path in output.iterdir()
        if path.name.endswith(".publication-backup")
    )
    assert len(backups) == 1
    assert os.path.samefile(backups[0], sibling)


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="POSIX dir fsync")
def test_postcommit_directory_fsync_failure_does_not_invalidate_commit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "repo/build/out/artifact.bin"
    calls = 0
    real_fsync = artifacts._fsync_descriptor

    def fail_cleanup_fsync(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected postcommit fsync failure")
        real_fsync(descriptor)

    monkeypatch.setattr(artifacts, "_fsync_descriptor", fail_cleanup_fsync)
    write_atomic_bytes(target, b"committed")
    assert calls == 2
    assert target.read_bytes() == b"committed"


def test_concurrency_boundary_is_documented_honestly() -> None:
    documentation = artifacts.BoundArtifactPublication.commit.__doc__ or ""
    assert "same-UID" in documentation
    assert "commit instant" in documentation
    assert "cannot prevent" in documentation


def test_rollback_restores_same_inode_hardlink_and_mode(tmp_path: Path) -> None:
    output = tmp_path / "repo/build/out"
    output.mkdir(parents=True)
    target = output / "artifact.bin"
    sibling = output / "artifact-hardlink.bin"
    target.write_bytes(b"preserved")
    try:
        os.link(target, sibling)
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")
    target.chmod(0o640)
    before = target.stat()

    with pytest.raises(ArtifactPublicationError, match="abort publication"):
        with bind_artifact_publication(
            output,
            anchor_root=tmp_path / "repo",
            allowed_root=tmp_path / "repo/build",
        ) as publication:
            publication.write_bytes(target, b"replacement")
            raise RuntimeError("abort publication")

    after = target.stat()
    assert os.path.samefile(target, sibling)
    assert (after.st_dev, after.st_ino) == (before.st_dev, before.st_ino)
    assert stat.S_IMODE(after.st_mode) == stat.S_IMODE(before.st_mode)
    assert target.read_bytes() == b"preserved"
    assert not any("backup" in path.name for path in output.iterdir())


def test_existing_target_is_not_snapshotted_into_memory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"preserved")

    def reject_snapshot(*_args, **_kwargs):
        pytest.fail("existing artifact was snapshotted into memory")

    monkeypatch.setattr(
        artifacts.BoundArtifactPublication,
        "_read_bound_bytes",
        reject_snapshot,
        raising=False,
    )
    write_atomic_bytes(target, b"replacement")
    assert target.read_bytes() == b"replacement"


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="Linux fd table")
def test_failed_target_final_path_check_does_not_leak_descriptor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "repo/build/out"
    output.mkdir(parents=True)
    target = output / "artifact.bin"
    target.write_bytes(b"payload")
    before = len(tuple(Path("/proc/self/fd").iterdir()))
    with bind_artifact_publication(
        output,
        anchor_root=tmp_path / "repo",
        allowed_root=tmp_path / "repo/build",
    ) as publication:
        real_final_path = artifacts._linux_final_path_from_fd

        def fail_final_path(_descriptor: int) -> Path:
            raise ArtifactPublicationError("injected final path failure")

        monkeypatch.setattr(
            artifacts,
            "_linux_final_path_from_fd",
            fail_final_path,
        )
        with pytest.raises(ArtifactPublicationError, match="final path"):
            publication._open_target_descriptor(target.name)
        monkeypatch.setattr(
            artifacts,
            "_linux_final_path_from_fd",
            real_final_path,
        )
    after = len(tuple(Path("/proc/self/fd").iterdir()))
    assert after == before


def test_atomic_json_and_jsonl_are_canonical(tmp_path: Path) -> None:
    json_path = tmp_path / "receipt.json"
    jsonl_path = tmp_path / "identities.jsonl"
    write_atomic_json(json_path, {"b": 2, "a": 1})
    write_atomic_jsonl(jsonl_path, ({"b": 2, "a": 1},))
    assert json_path.read_bytes() == b'{\n    "a": 1,\n    "b": 2\n}\n'
    assert jsonl_path.read_bytes() == b'{"a":1,"b":2}\n'
    assert sha256_file(jsonl_path) == hashlib.sha256(
        jsonl_path.read_bytes()
    ).hexdigest()


def test_atomic_bytes_creates_parent_and_replaces_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "artifact.bin"
    write_atomic_bytes(path, b"first")
    write_atomic_bytes(path, b"second")
    assert path.read_bytes() == b"second"
    assert tuple(path.parent.iterdir()) == (path,)


@pytest.mark.parametrize("writer", (write_atomic_json, write_atomic_jsonl))
def test_json_writers_reject_nonfinite_values_without_partial_publish(
    tmp_path: Path,
    writer,
) -> None:
    path = tmp_path / "artifact.json"
    path.write_bytes(b"preserved")
    values = {"value": math.nan} if writer is write_atomic_json else (
        {"value": math.inf},
    )
    with pytest.raises(ValueError):
        writer(path, values)
    assert path.read_bytes() == b"preserved"


def test_jsonl_rejects_non_mapping_records_without_partial_publish(
    tmp_path: Path,
) -> None:
    path = tmp_path / "artifact.jsonl"
    path.write_bytes(b"preserved")
    with pytest.raises(TypeError, match="mapping"):
        write_atomic_jsonl(path, ({"valid": True}, ["not-a-mapping"]))
    assert path.read_bytes() == b"preserved"


def test_atomic_bytes_cleans_partial_temp_after_write_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"preserved")
    real_fdopen = artifacts.os.fdopen

    class FailingWriter:
        def __init__(self, descriptor, mode, *, closefd):
            self.stream = real_fdopen(descriptor, mode, closefd=closefd)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.stream.close()

        def write(self, payload):
            self.stream.write(payload[:1])
            raise OSError("injected write failure")

    monkeypatch.setattr(artifacts.os, "fdopen", FailingWriter)
    with pytest.raises(OSError, match="write failure"):
        write_atomic_bytes(path, b"replacement")
    assert path.read_bytes() == b"preserved"
    assert tuple(path.parent.iterdir()) == (path,)


def test_atomic_bytes_cleans_temp_after_fsync_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"preserved")

    def fail_fsync(_stream) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr(artifacts, "_fsync_data", fail_fsync)
    with pytest.raises(OSError, match="fsync failure"):
        write_atomic_bytes(path, b"replacement")
    assert path.read_bytes() == b"preserved"
    assert tuple(path.parent.iterdir()) == (path,)


def test_atomic_bytes_cleans_temp_after_replace_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"preserved")

    def fail_replace(_source, _target, **_kwargs) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(artifacts.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failure"):
        write_atomic_bytes(path, b"replacement")
    assert path.read_bytes() == b"preserved"
    assert tuple(path.parent.iterdir()) == (path,)
