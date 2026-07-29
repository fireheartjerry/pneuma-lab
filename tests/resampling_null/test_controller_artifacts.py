from __future__ import annotations

import hashlib
import os

import pytest

import pneuma_lab.resampling_null.controller_artifacts as controller_artifacts
from pneuma_lab.resampling_null.controller_artifacts import (
    ControllerArtifactResolver,
    ControllerArtifactStore,
)
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.types import ArtifactRef


def test_controller_store_is_create_only_content_addressed_and_freshly_resolved(
    tmp_path,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    payload = b"controller evidence"
    ref = store.write(
        role="provider_request",
        payload=payload,
        media_type="application/octet-stream",
    )
    assert ref.sha256 == hashlib.sha256(payload).hexdigest()
    assert ref.byte_count == len(payload)
    assert ref.relative_path.endswith(ref.sha256)
    with pytest.raises(FileExistsError):
        store.write(
            role="provider_request",
            payload=payload,
            media_type="application/octet-stream",
        )
    store.close()
    with pytest.raises(RuntimeError):
        store.write(role="later", payload=b"x", media_type="text/plain")
    resolver = ControllerArtifactResolver(tmp_path)
    assert (
        resolver.resolve(
            ref,
            expected_role="provider_request",
            expected_media_type="application/octet-stream",
        )
        == payload
    )
    with pytest.raises(RecordValidationError):
        resolver.resolve(
            ref,
            expected_role="provider_response",
            expected_media_type="application/octet-stream",
        )
    resolver.close()


def test_controller_store_rejects_traversal_symlinks_and_subclassing(tmp_path) -> None:
    store = ControllerArtifactStore(tmp_path)
    for role in ("../escape", "a/b", ".", ""):
        with pytest.raises((TypeError, ValueError)):
            store.write(role=role, payload=b"x", media_type="text/plain")
    store.close()

    symlink_root = tmp_path / "symlink-root"
    symlink_root.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(RecordValidationError):
        ControllerArtifactStore(symlink_root)

    with pytest.raises(TypeError):

        class AttemptedStoreSubclass(ControllerArtifactStore):
            pass

    with pytest.raises(TypeError):

        class AttemptedResolverSubclass(ControllerArtifactResolver):
            pass


def test_controller_store_rejects_root_identity_swap_during_binding(
    tmp_path,
    monkeypatch,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    original = tmp_path / "original"
    real_open = os.open
    swapped = False

    def swap_then_open(
        path: object, flags: int, *args: object, **kwargs: object
    ) -> int:
        nonlocal swapped
        if not swapped and os.fspath(path) == os.fspath(run_root.absolute()):
            swapped = True
            run_root.rename(original)
            replacement.rename(run_root)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(controller_artifacts.os, "open", swap_then_open)
    with pytest.raises(RecordValidationError, match="identity"):
        ControllerArtifactStore(run_root)


def test_controller_resolver_rejects_tamper_path_role_and_symlink(tmp_path) -> None:
    store = ControllerArtifactStore(tmp_path)
    ref = store.write(role="snapshot", payload=b"before", media_type="application/json")
    store.close()
    target = tmp_path / ref.relative_path
    target.write_bytes(b"tampered")
    resolver = ControllerArtifactResolver(tmp_path)
    with pytest.raises(RecordValidationError):
        resolver.resolve(
            ref,
            expected_role="snapshot",
            expected_media_type="application/json",
        )
    resolver.close()

    other = tmp_path / "other"
    other.write_bytes(b"before")
    target.unlink()
    target.symlink_to(other)
    resolver = ControllerArtifactResolver(tmp_path)
    with pytest.raises(RecordValidationError):
        resolver.resolve(
            ref,
            expected_role="snapshot",
            expected_media_type="application/json",
        )
    resolver.close()

    wrong_role = ArtifactRef(
        role="other",
        relative_path=ref.relative_path,
        sha256=ref.sha256,
        byte_count=ref.byte_count,
        media_type=ref.media_type,
    )
    resolver = ControllerArtifactResolver(tmp_path)
    with pytest.raises(RecordValidationError):
        resolver.resolve(
            wrong_role,
            expected_role="snapshot",
            expected_media_type="application/json",
        )
    resolver.close()


def test_controller_resolver_rejects_forged_media_type_for_same_bytes(
    tmp_path,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    ref = store.write(
        role="snapshot",
        payload=b"{}",
        media_type="application/json",
    )
    store.close()
    forged = ArtifactRef(
        role=ref.role,
        relative_path=ref.relative_path,
        sha256=ref.sha256,
        byte_count=ref.byte_count,
        media_type="application/octet-stream",
    )
    resolver = ControllerArtifactResolver(tmp_path)
    with pytest.raises(RecordValidationError, match="media type"):
        resolver.resolve(
            forged,
            expected_role="snapshot",
            expected_media_type="application/json",
        )
    resolver.close()


@pytest.mark.parametrize(
    "media_type",
    ["Application/JSON", "application/json; charset=utf-8", " application/json"],
)
def test_controller_store_rejects_noncanonical_media_type(
    tmp_path,
    media_type: str,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    with pytest.raises(ValueError, match="media_type"):
        store.write(role="snapshot", payload=b"{}", media_type=media_type)
    store.close()


def test_success_path_close_failure_removes_artifact_for_retry(
    tmp_path,
    monkeypatch,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    real_close = os.close
    close_calls = 0

    def close_then_fail_once(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(descriptor)
        if close_calls == 1:
            raise OSError("injected successful-path close failure")

    monkeypatch.setattr(controller_artifacts.os, "close", close_then_fail_once)
    with pytest.raises(ExceptionGroup) as raised:
        store.write(role="request", payload=b"x", media_type="text/plain")
    assert "successful-path close failure" in str(raised.value.exceptions[0])
    monkeypatch.setattr(controller_artifacts.os, "close", real_close)
    ref = store.write(role="request", payload=b"x", media_type="text/plain")
    assert ref.byte_count == 1
    store.close()


def test_base_exception_after_create_removes_artifact_for_retry(
    tmp_path,
    monkeypatch,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    real_write_all = controller_artifacts._write_all

    def interrupt_write(descriptor: int, payload: bytes) -> None:
        raise KeyboardInterrupt("injected write interruption")

    monkeypatch.setattr(controller_artifacts, "_write_all", interrupt_write)
    with pytest.raises(KeyboardInterrupt, match="write interruption"):
        store.write(role="request", payload=b"x", media_type="text/plain")
    monkeypatch.setattr(controller_artifacts, "_write_all", real_write_all)
    ref = store.write(role="request", payload=b"x", media_type="text/plain")
    assert ref.byte_count == 1
    store.close()


def test_base_exception_preserves_cleanup_errors_in_base_exception_group(
    tmp_path,
    monkeypatch,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    real_unlink = os.unlink

    class InjectedInterruption(BaseException):
        pass

    def interrupt_write(descriptor: int, payload: bytes) -> None:
        raise InjectedInterruption("injected write interruption")

    def fail_unlink(path: str, *, dir_fd: int | None = None) -> None:
        raise OSError("injected interruption cleanup failure")

    monkeypatch.setattr(controller_artifacts, "_write_all", interrupt_write)
    monkeypatch.setattr(controller_artifacts.os, "unlink", fail_unlink)
    with pytest.raises(BaseExceptionGroup) as raised:
        store.write(role="request", payload=b"x", media_type="text/plain")
    assert isinstance(raised.value.exceptions[0], InjectedInterruption)
    assert "cleanup failure" in str(raised.value.exceptions[1])
    monkeypatch.setattr(controller_artifacts.os, "unlink", real_unlink)
    store.close()


def test_verification_and_descriptor_close_failures_are_all_preserved(
    tmp_path,
    monkeypatch,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    real_close = os.close
    real_read_and_hash = controller_artifacts._read_and_hash
    close_calls = 0

    def corrupt_read(descriptor: int) -> tuple[bytes, str, int]:
        return b"y", hashlib.sha256(b"y").hexdigest(), 1

    def fail_read_and_role_close(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(descriptor)
        if close_calls in (2, 3):
            raise OSError(f"injected close failure {close_calls}")

    monkeypatch.setattr(controller_artifacts, "_read_and_hash", corrupt_read)
    monkeypatch.setattr(controller_artifacts.os, "close", fail_read_and_role_close)
    with pytest.raises(ExceptionGroup) as raised:
        store.write(role="request", payload=b"x", media_type="text/plain")
    messages = " | ".join(str(error) for error in raised.value.exceptions)
    assert "bytes changed" in messages
    assert "injected close failure 2" in messages
    assert "injected close failure 3" in messages
    monkeypatch.setattr(controller_artifacts, "_read_and_hash", real_read_and_hash)
    monkeypatch.setattr(controller_artifacts.os, "close", real_close)
    ref = store.write(role="request", payload=b"x", media_type="text/plain")
    assert ref.byte_count == 1
    store.close()


def test_store_close_attempts_both_descriptor_closures_after_fsync_error(
    tmp_path,
    monkeypatch,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    real_fsync = os.fsync
    real_close = os.close
    fsync_calls = 0
    closed: list[int] = []

    def fail_first_fsync(descriptor: int) -> None:
        nonlocal fsync_calls
        fsync_calls += 1
        if fsync_calls == 1:
            raise OSError("injected artifact fsync failure")
        real_fsync(descriptor)

    def record_close(descriptor: int) -> None:
        closed.append(descriptor)
        real_close(descriptor)

    monkeypatch.setattr(controller_artifacts.os, "fsync", fail_first_fsync)
    monkeypatch.setattr(controller_artifacts.os, "close", record_close)
    with pytest.raises(ExceptionGroup):
        store.close()
    assert len(closed) == 2
    with pytest.raises(RuntimeError):
        store.write(role="closed", payload=b"x", media_type="text/plain")


def test_failed_write_reports_cleanup_uncertainty(tmp_path, monkeypatch) -> None:
    store = ControllerArtifactStore(tmp_path)
    real_write = os.write
    real_unlink = os.unlink

    def fail_write(descriptor: int, payload: object) -> int:
        raise OSError("injected write failure")

    def fail_unlink(
        path: str,
        *,
        dir_fd: int | None = None,
    ) -> None:
        raise OSError("injected cleanup failure")

    monkeypatch.setattr(controller_artifacts.os, "write", fail_write)
    monkeypatch.setattr(controller_artifacts.os, "unlink", fail_unlink)
    with pytest.raises(ExceptionGroup, match="cleanup is uncertain"):
        store.write(role="request", payload=b"x", media_type="text/plain")
    monkeypatch.setattr(controller_artifacts.os, "write", real_write)
    monkeypatch.setattr(controller_artifacts.os, "unlink", real_unlink)
    store.close()


def test_resolver_close_aggregates_and_attempts_both_descriptors(
    tmp_path,
    monkeypatch,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    store.close()
    resolver = ControllerArtifactResolver(tmp_path)
    real_close = os.close
    close_calls = 0

    def fail_first_close(descriptor: int) -> None:
        nonlocal close_calls
        close_calls += 1
        real_close(descriptor)
        if close_calls == 1:
            raise OSError("injected resolver close failure")

    monkeypatch.setattr(controller_artifacts.os, "close", fail_first_close)
    with pytest.raises(ExceptionGroup):
        resolver.close()
    assert close_calls == 2
