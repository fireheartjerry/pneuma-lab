"""Canonical, atomic foundation artifact helpers."""

from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
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

    with pytest.raises(ArtifactPublicationError, match="ancestry|output"):
        with bind_artifact_publication(
            output,
            anchor_root=repo_root,
            allowed_root=repo_root / "build",
            forbidden_roots=(forbidden,),
        ) as publication:
            real_replace = publication._replace

            def rename_then_replace(temporary_name: str, name: str) -> None:
                output.rename(moved)
                real_replace(temporary_name, name)

            monkeypatch.setattr(publication, "_replace", rename_then_replace)
            publication.write_bytes(target, b"payload")
    assert tuple(moved.iterdir()) == ()


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
    real_commit = artifacts.BoundArtifactPublication.commit

    def rename_then_commit(publication) -> None:
        output.rename(moved)
        real_commit(publication)

    monkeypatch.setattr(
        artifacts.BoundArtifactPublication,
        "commit",
        rename_then_commit,
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


def test_commit_rejects_published_content_mutation(tmp_path: Path) -> None:
    output = tmp_path / "repo/build/out"
    output.mkdir(parents=True)
    target = output / "artifact.bin"
    with pytest.raises(ArtifactPublicationError, match="content|digest|size"):
        with bind_artifact_publication(
            output,
            anchor_root=tmp_path / "repo",
            allowed_root=tmp_path / "repo/build",
        ) as publication:
            publication.write_bytes(target, b"expected")
            target.write_bytes(b"tampered")
    assert not target.exists()


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
