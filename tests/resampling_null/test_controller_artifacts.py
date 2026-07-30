from __future__ import annotations

import hashlib
import os
import stat

import pytest

import pneuma_lab.resampling_null.controller_artifacts as controller_artifacts
from pneuma_lab.resampling_null.controller_artifacts import (
    ControllerArtifactResolver,
    ControllerArtifactStore,
)
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.types import ArtifactRef


@pytest.mark.parametrize(
    ("consumer_type", "expected_message"),
    [
        (
            ControllerArtifactStore,
            "controller artifact root could not be bound",
        ),
        (
            ControllerArtifactResolver,
            "controller artifact tree could not be freshly bound",
        ),
    ],
)
@pytest.mark.parametrize("close_fails", [False, True])
def test_controller_root_fstat_oserror_keeps_public_primary_with_cleanup(
    tmp_path,
    monkeypatch,
    consumer_type,
    expected_message: str,
    close_fails: bool,
) -> None:
    original_close = controller_artifacts.os.close

    def fstat(_descriptor: int):
        raise OSError("injected controller root fstat failure")

    def close(descriptor: int) -> None:
        original_close(descriptor)
        if close_fails:
            raise OSError("injected controller root cleanup failure")

    monkeypatch.setattr(controller_artifacts.os, "fstat", fstat)
    monkeypatch.setattr(controller_artifacts.os, "close", close)
    consumer = object.__new__(consumer_type)
    with pytest.raises(BaseException) as captured:
        consumer.__init__(tmp_path)

    if close_fails:
        assert isinstance(captured.value, BaseExceptionGroup)
        primary = captured.value.exceptions[0]
        assert str(captured.value.exceptions[1]) == (
            "injected controller root cleanup failure"
        )
    else:
        primary = captured.value
    assert isinstance(primary, RecordValidationError)
    assert str(primary) == expected_message
    assert isinstance(primary.__cause__, OSError)
    assert str(primary.__cause__) == "injected controller root fstat failure"
    assert consumer._root_descriptor is None
    assert consumer._artifact_descriptor is None


def test_controller_root_acquisition_preserves_identity_and_close_failures(
    tmp_path,
    monkeypatch,
) -> None:
    original_fstat = controller_artifacts.os.fstat
    original_close = controller_artifacts.os.close

    def fstat(descriptor: int):
        metadata = original_fstat(descriptor)
        values = list(metadata)
        values[1] += 1
        return os.stat_result(values)

    def close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("injected controller root close failure")

    monkeypatch.setattr(controller_artifacts.os, "fstat", fstat)
    monkeypatch.setattr(controller_artifacts.os, "close", close)
    store = object.__new__(ControllerArtifactStore)
    with pytest.raises(BaseExceptionGroup) as captured:
        store.__init__(tmp_path)

    assert isinstance(captured.value.exceptions[0], RecordValidationError)
    assert "identity changed" in str(captured.value.exceptions[0])
    assert str(captured.value.exceptions[1]) == (
        "injected controller root close failure"
    )
    assert getattr(store, "_root_descriptor", None) is None


def test_controller_store_tree_acquisition_clears_stale_owner_and_aggregates(
    tmp_path,
    monkeypatch,
) -> None:
    original_close = controller_artifacts.os.close

    def open_tree(_root_descriptor: int, _name: str) -> int:
        raise ValueError("injected controller store tree failure")

    def close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("injected controller store acquisition close failure")

    monkeypatch.setattr(controller_artifacts, "_mkdir_or_open", open_tree)
    monkeypatch.setattr(controller_artifacts.os, "close", close)
    store = object.__new__(ControllerArtifactStore)
    with pytest.raises(BaseExceptionGroup) as captured:
        store.__init__(tmp_path)

    assert [str(error) for error in captured.value.exceptions] == [
        "injected controller store tree failure",
        "injected controller store acquisition close failure",
    ]
    assert store._root_descriptor is None
    assert store._artifact_descriptor is None


def test_controller_store_tree_fstat_and_close_failures_are_causal(
    tmp_path,
    monkeypatch,
) -> None:
    original_fstat = controller_artifacts.os.fstat
    original_close = controller_artifacts.os.close
    calls = 0
    tree_descriptor: int | None = None
    closed: list[int] = []

    def fstat(descriptor: int):
        nonlocal calls, tree_descriptor
        calls += 1
        if calls == 2:
            tree_descriptor = descriptor
            raise OSError("injected artifact tree fstat failure")
        return original_fstat(descriptor)

    def close(descriptor: int) -> None:
        closed.append(descriptor)
        original_close(descriptor)
        if descriptor == tree_descriptor:
            raise OSError("injected artifact tree close failure")

    monkeypatch.setattr(controller_artifacts.os, "fstat", fstat)
    monkeypatch.setattr(controller_artifacts.os, "close", close)
    store = object.__new__(ControllerArtifactStore)
    with pytest.raises(BaseExceptionGroup) as captured:
        store.__init__(tmp_path)

    assert [str(error) for error in captured.value.exceptions] == [
        "injected artifact tree fstat failure",
        "injected artifact tree close failure",
    ]
    assert tree_descriptor in closed
    assert len(closed) == 2
    assert store._root_descriptor is None
    assert store._artifact_descriptor is None


def test_controller_store_tree_not_directory_preserves_primary_on_close_failure(
    tmp_path,
    monkeypatch,
) -> None:
    original_fstat = controller_artifacts.os.fstat
    original_close = controller_artifacts.os.close
    calls = 0
    tree_descriptor: int | None = None
    closed: list[int] = []

    def fstat(descriptor: int):
        nonlocal calls, tree_descriptor
        calls += 1
        metadata = original_fstat(descriptor)
        if calls == 2:
            tree_descriptor = descriptor
            values = list(metadata)
            values[0] = stat.S_IFREG | 0o600
            return os.stat_result(values)
        return metadata

    def close(descriptor: int) -> None:
        closed.append(descriptor)
        original_close(descriptor)
        if descriptor == tree_descriptor:
            raise OSError("injected non-directory close failure")

    monkeypatch.setattr(controller_artifacts.os, "fstat", fstat)
    monkeypatch.setattr(controller_artifacts.os, "close", close)
    store = object.__new__(ControllerArtifactStore)
    with pytest.raises(BaseExceptionGroup) as captured:
        store.__init__(tmp_path)

    assert isinstance(captured.value.exceptions[0], RecordValidationError)
    assert "not a directory" in str(captured.value.exceptions[0])
    assert str(captured.value.exceptions[1]) == ("injected non-directory close failure")
    assert tree_descriptor in closed
    assert len(closed) == 2
    assert store._root_descriptor is None
    assert store._artifact_descriptor is None


def test_controller_resolver_tree_open_clears_stale_owner_and_aggregates(
    tmp_path,
    monkeypatch,
) -> None:
    with ControllerArtifactStore(tmp_path):
        pass
    original_open = controller_artifacts.os.open
    original_close = controller_artifacts.os.close

    def open_file(path, flags, *args, **kwargs):
        if (
            path == controller_artifacts._ARTIFACT_DIRECTORY
            and kwargs.get("dir_fd") is not None
        ):
            raise OSError("injected controller resolver tree open failure")
        return original_open(path, flags, *args, **kwargs)

    def close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("injected controller resolver acquisition close failure")

    monkeypatch.setattr(controller_artifacts.os, "open", open_file)
    monkeypatch.setattr(controller_artifacts.os, "close", close)
    resolver = object.__new__(ControllerArtifactResolver)
    with pytest.raises(BaseExceptionGroup) as captured:
        resolver.__init__(tmp_path)

    assert isinstance(captured.value.exceptions[0], RecordValidationError)
    assert "tree could not be freshly bound" in str(captured.value.exceptions[0])
    assert isinstance(captured.value.exceptions[0].__cause__, OSError)
    assert "tree open failure" in str(captured.value.exceptions[0].__cause__)
    assert str(captured.value.exceptions[1]) == (
        "injected controller resolver acquisition close failure"
    )
    assert resolver._root_descriptor is None
    assert resolver._artifact_descriptor is None


def test_controller_resolver_tree_baseexception_is_primary_and_owner_is_clear(
    tmp_path,
    monkeypatch,
) -> None:
    with ControllerArtifactStore(tmp_path):
        pass
    original_open = controller_artifacts.os.open
    original_close = controller_artifacts.os.close

    def open_file(path, flags, *args, **kwargs):
        if (
            path == controller_artifacts._ARTIFACT_DIRECTORY
            and kwargs.get("dir_fd") is not None
        ):
            raise KeyboardInterrupt("injected resolver acquisition interrupt")
        return original_open(path, flags, *args, **kwargs)

    def close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("injected interrupted acquisition close failure")

    monkeypatch.setattr(controller_artifacts.os, "open", open_file)
    monkeypatch.setattr(controller_artifacts.os, "close", close)
    resolver = object.__new__(ControllerArtifactResolver)
    with pytest.raises(BaseExceptionGroup) as captured:
        resolver.__init__(tmp_path)

    assert [type(error) for error in captured.value.exceptions] == [
        KeyboardInterrupt,
        OSError,
    ]
    assert str(captured.value.exceptions[0]) == (
        "injected resolver acquisition interrupt"
    )
    assert resolver._root_descriptor is None
    assert resolver._artifact_descriptor is None


def test_controller_store_is_create_only_content_addressed_and_freshly_resolved(
    tmp_path,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    payload = b"controller evidence"
    ref = store.write(
        role="provider_request",
        payload=payload,
        media_type="application/json",
    )
    assert ref.sha256 == hashlib.sha256(payload).hexdigest()
    assert ref.byte_count == len(payload)
    assert ref.relative_path.endswith(ref.sha256)
    reused = store.write(
        role="provider_request",
        payload=payload,
        media_type="application/json",
    )
    assert reused == ref
    store.close()
    with pytest.raises(RuntimeError):
        store.write(role="later", payload=b"x", media_type="text/plain")
    resolver = ControllerArtifactResolver(tmp_path)
    assert (
        resolver.resolve(
            ref,
            expected_role="provider_request",
            expected_media_type="application/json",
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


def test_controller_store_eexist_mismatch_never_unlinks_existing_blob(
    tmp_path,
    monkeypatch,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    payload = b"controller evidence"
    ref = store.write(
        role="provider_request",
        payload=payload,
        media_type="application/json",
    )
    target = tmp_path / ref.relative_path
    with pytest.raises(RecordValidationError, match="canonical"):
        store.write(
            role="provider_request",
            payload=payload,
            media_type="application/octet-stream",
        )
    assert target.read_bytes() == payload
    target.write_bytes(b"tampered evidence!")
    with pytest.raises(RecordValidationError):
        store.write(
            role="provider_request",
            payload=payload,
            media_type="application/json",
        )
    assert target.read_bytes() == b"tampered evidence!"

    target.unlink()
    symlink_target = tmp_path / "outside"
    symlink_target.write_bytes(payload)
    target.symlink_to(symlink_target)
    with pytest.raises(RecordValidationError):
        store.write(
            role="provider_request",
            payload=payload,
            media_type="application/json",
        )
    assert target.is_symlink()
    assert symlink_target.read_bytes() == payload
    store.close()


def test_controller_store_rejects_traversal_symlinks_and_subclassing(tmp_path) -> None:
    store = ControllerArtifactStore(tmp_path)
    for role in ("../escape", "a/b", ".", ""):
        with pytest.raises((TypeError, ValueError)):
            store.write(role=role, payload=b"x", media_type="text/plain")
    store.close()

    store = ControllerArtifactStore(tmp_path)
    with pytest.raises(RecordValidationError, match="registered"):
        store.write(role="unknown_role", payload=b"x", media_type="text/plain")
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


def test_controller_resolver_rejects_unregistered_authority_before_open(
    tmp_path,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    store.close()
    ref = ArtifactRef(
        role="unknown_controller_role",
        relative_path="controller-artifacts/unknown_controller_role/" + "a" * 64,
        sha256="a" * 64,
        byte_count=0,
        media_type="application/json",
    )
    resolver = ControllerArtifactResolver(tmp_path)
    with pytest.raises(RecordValidationError, match="registered"):
        resolver.resolve(
            ref,
            expected_role="unknown_controller_role",
            expected_media_type="application/json",
        )
    resolver.close()


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
    ref = store.write(
        role="composite_snapshot",
        payload=b"before",
        media_type="application/json",
    )
    store.close()
    target = tmp_path / ref.relative_path
    target.write_bytes(b"tampered")
    resolver = ControllerArtifactResolver(tmp_path)
    with pytest.raises(RecordValidationError):
        resolver.resolve(
            ref,
            expected_role="composite_snapshot",
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
            expected_role="composite_snapshot",
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
            expected_role="composite_snapshot",
            expected_media_type="application/json",
        )
    resolver.close()


def test_controller_resolver_rejects_forged_media_type_for_same_bytes(
    tmp_path,
) -> None:
    store = ControllerArtifactStore(tmp_path)
    ref = store.write(
        role="composite_snapshot",
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
            expected_role="composite_snapshot",
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
        store.write(role="composite_snapshot", payload=b"{}", media_type=media_type)
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
        store.write(
            role="provider_request", payload=b"x", media_type="application/json"
        )
    assert "successful-path close failure" in str(raised.value.exceptions[0])
    monkeypatch.setattr(controller_artifacts.os, "close", real_close)
    ref = store.write(
        role="provider_request",
        payload=b"x",
        media_type="application/json",
    )
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
        store.write(
            role="provider_request", payload=b"x", media_type="application/json"
        )
    monkeypatch.setattr(controller_artifacts, "_write_all", real_write_all)
    ref = store.write(
        role="provider_request",
        payload=b"x",
        media_type="application/json",
    )
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
        store.write(
            role="provider_request", payload=b"x", media_type="application/json"
        )
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
        store.write(
            role="provider_request", payload=b"x", media_type="application/json"
        )
    messages = " | ".join(str(error) for error in raised.value.exceptions)
    assert "bytes changed" in messages
    assert "injected close failure 2" in messages
    assert "injected close failure 3" in messages
    monkeypatch.setattr(controller_artifacts, "_read_and_hash", real_read_and_hash)
    monkeypatch.setattr(controller_artifacts.os, "close", real_close)
    ref = store.write(
        role="provider_request",
        payload=b"x",
        media_type="application/json",
    )
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
        store.write(
            role="provider_request", payload=b"x", media_type="application/json"
        )
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
