"""Verified create-exclusive local controller artifact storage.

This is cooperative local/synthetic authority. It does not claim protection
from a malicious same-UID process or production-backend equivalence.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
from typing import final

from .errors import RecordValidationError
from .types import ArtifactRef


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
_ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_ARTIFACT_DIRECTORY = "controller-artifacts"
_CHUNK_BYTES = 1024 * 1024


def _validate_root(run_root: Path) -> tuple[Path, tuple[int, int]]:
    root = Path(run_root)
    try:
        metadata = os.stat(root, follow_symlinks=False)
    except OSError as exc:
        raise RecordValidationError("controller artifact root is unavailable") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RecordValidationError(
            "controller artifact root must be a non-symlink directory"
        )
    return root.absolute(), (metadata.st_dev, metadata.st_ino)


def _bind_root(run_root: Path) -> tuple[Path, int]:
    root, expected_identity = _validate_root(run_root)
    try:
        descriptor = os.open(root, _DIRECTORY_FLAGS)
        bound = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(bound.st_mode)
            or (bound.st_dev, bound.st_ino) != expected_identity
        ):
            raise RecordValidationError(
                "controller artifact root identity changed during binding"
            )
    except BaseException:
        if "descriptor" in locals():
            os.close(descriptor)
        raise
    return root, descriptor


def _role(value: object) -> str:
    if type(value) is not str:
        raise TypeError("role must be exact text")
    role = value
    if _ROLE_PATTERN.fullmatch(role) is None:
        raise ValueError("role must be a normalized registered-style identifier")
    return role


def _media_type(value: object) -> str:
    if type(value) is not str:
        raise TypeError("media_type must be exact text")
    media_type = value
    if not media_type or any(character.isspace() for character in media_type):
        raise ValueError("media_type must be non-empty and contain no whitespace")
    return media_type


def _mkdir_or_open(parent: int, name: str) -> int:
    try:
        os.mkdir(name, mode=0o700, dir_fd=parent)
        os.fsync(parent)
    except FileExistsError:
        pass
    try:
        descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent)
    except OSError as exc:
        raise RecordValidationError(
            f"controller artifact directory is unsafe: {name!r}"
        ) from exc
    metadata = os.fstat(descriptor)
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise RecordValidationError(
            f"controller artifact component is not a directory: {name!r}"
        )
    return descriptor


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    offset = 0
    while offset < len(view):
        written = os.write(descriptor, view[offset:])
        if written <= 0:
            raise OSError("short controller artifact write")
        offset += written


def _read_and_hash(descriptor: int) -> tuple[bytes, str, int]:
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    size = 0
    while chunk := os.read(descriptor, _CHUNK_BYTES):
        chunks.append(chunk)
        digest.update(chunk)
        size += len(chunk)
    return b"".join(chunks), digest.hexdigest(), size


@final
class ControllerArtifactStore:
    """One-use root-bound create-exclusive controller CAS writer."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("ControllerArtifactStore is final")

    def __init__(self, run_root: Path) -> None:
        try:
            self._root, root_descriptor = _bind_root(run_root)
            self._root_descriptor: int | None = root_descriptor
        except OSError as exc:
            raise RecordValidationError(
                "controller artifact root could not be bound"
            ) from exc
        self._artifact_descriptor: int | None = None
        try:
            self._artifact_descriptor = _mkdir_or_open(
                self._root_descriptor,
                _ARTIFACT_DIRECTORY,
            )
        except BaseException:
            os.close(self._root_descriptor)
            self._root_descriptor = None
            raise

    def __enter__(self) -> ControllerArtifactStore:
        self._require_open()
        return self

    def __exit__(self, *_exception: object) -> None:
        self.close()

    def _require_open(self) -> tuple[int, int]:
        if self._root_descriptor is None or self._artifact_descriptor is None:
            raise RuntimeError("controller artifact store is closed")
        return self._root_descriptor, self._artifact_descriptor

    def write(self, *, role: str, payload: bytes, media_type: str) -> ArtifactRef:
        """Create, sync, reopen, and verify one content-addressed artifact."""

        _root_descriptor, artifact_descriptor = self._require_open()
        validated_role = _role(role)
        validated_media_type = _media_type(media_type)
        if type(payload) is not bytes:
            raise TypeError("payload must be exact bytes")
        digest = hashlib.sha256(payload).hexdigest()
        role_descriptor = _mkdir_or_open(artifact_descriptor, validated_role)
        try:
            descriptor = os.open(
                digest,
                _WRITE_FLAGS,
                0o600,
                dir_fd=role_descriptor,
            )
            try:
                _write_all(descriptor, payload)
                os.fsync(descriptor)
            except Exception as write_error:
                cleanup_errors: list[Exception] = []
                try:
                    os.close(descriptor)
                except OSError as exc:
                    cleanup_errors.append(exc)
                try:
                    os.unlink(digest, dir_fd=role_descriptor)
                except OSError as exc:
                    cleanup_errors.append(exc)
                try:
                    os.fsync(role_descriptor)
                except OSError as exc:
                    cleanup_errors.append(exc)
                if cleanup_errors:
                    raise ExceptionGroup(
                        "controller artifact write cleanup is uncertain",
                        [write_error, *cleanup_errors],
                    )
                raise
            else:
                os.close(descriptor)
            os.fsync(role_descriptor)
            read_descriptor = os.open(
                digest,
                _READ_FLAGS,
                dir_fd=role_descriptor,
            )
            try:
                metadata = os.fstat(read_descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise RecordValidationError(
                        "new controller artifact is not a regular file"
                    )
                observed, observed_digest, observed_size = _read_and_hash(
                    read_descriptor
                )
                named = os.stat(
                    digest,
                    dir_fd=role_descriptor,
                    follow_symlinks=False,
                )
                if stat.S_ISLNK(named.st_mode) or (
                    metadata.st_dev,
                    metadata.st_ino,
                ) != (named.st_dev, named.st_ino):
                    raise RecordValidationError(
                        "controller artifact identity changed after write"
                    )
            finally:
                os.close(read_descriptor)
        finally:
            os.close(role_descriptor)
        if (
            observed != payload
            or observed_digest != digest
            or observed_size != len(payload)
        ):
            raise RecordValidationError(
                "controller artifact bytes changed during verified write"
            )
        return ArtifactRef(
            role=validated_role,
            relative_path=f"{_ARTIFACT_DIRECTORY}/{validated_role}/{digest}",
            sha256=digest,
            byte_count=len(payload),
            media_type=validated_media_type,
        )

    def close(self) -> None:
        artifact_descriptor = self._artifact_descriptor
        root_descriptor = self._root_descriptor
        self._artifact_descriptor = None
        self._root_descriptor = None
        errors: list[Exception] = []
        if artifact_descriptor is not None:
            try:
                os.fsync(artifact_descriptor)
            except OSError as exc:
                errors.append(exc)
            try:
                os.close(artifact_descriptor)
            except OSError as exc:
                errors.append(exc)
        if root_descriptor is not None:
            try:
                os.fsync(root_descriptor)
            except OSError as exc:
                errors.append(exc)
            try:
                os.close(root_descriptor)
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup(
                "controller artifact store close was incomplete",
                errors,
            )


@final
class ControllerArtifactResolver:
    """Fresh root-bound resolver that recomputes every ArtifactRef property."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("ControllerArtifactResolver is final")

    def __init__(self, run_root: Path) -> None:
        try:
            self._root, root_descriptor = _bind_root(run_root)
            self._root_descriptor: int | None = root_descriptor
            self._artifact_descriptor: int | None = os.open(
                _ARTIFACT_DIRECTORY,
                _DIRECTORY_FLAGS,
                dir_fd=self._root_descriptor,
            )
        except OSError as exc:
            maybe_root_descriptor = getattr(self, "_root_descriptor", None)
            if maybe_root_descriptor is not None:
                os.close(maybe_root_descriptor)
            self._root_descriptor = None
            self._artifact_descriptor = None
            raise RecordValidationError(
                "controller artifact tree could not be freshly bound"
            ) from exc

    def __enter__(self) -> ControllerArtifactResolver:
        self._require_open()
        return self

    def __exit__(self, *_exception: object) -> None:
        self.close()

    def _require_open(self) -> tuple[int, int]:
        if self._root_descriptor is None or self._artifact_descriptor is None:
            raise RuntimeError("controller artifact resolver is closed")
        return self._root_descriptor, self._artifact_descriptor

    def resolve(self, ref: ArtifactRef, *, expected_role: str) -> bytes:
        """Reopen and recompute role, path, hash, length, and exact bytes."""

        _root_descriptor, artifact_descriptor = self._require_open()
        if type(ref) is not ArtifactRef:
            raise TypeError("ref must be exact ArtifactRef")
        validated_role = _role(expected_role)
        if ref.role != validated_role:
            raise RecordValidationError(
                "controller artifact role differs from controller expectation"
            )
        expected_path = f"{_ARTIFACT_DIRECTORY}/{validated_role}/{ref.sha256}"
        if ref.relative_path != expected_path:
            raise RecordValidationError(
                "controller artifact path does not bind role and digest"
            )
        try:
            role_descriptor = os.open(
                validated_role,
                _DIRECTORY_FLAGS,
                dir_fd=artifact_descriptor,
            )
            try:
                descriptor = os.open(
                    ref.sha256,
                    _READ_FLAGS,
                    dir_fd=role_descriptor,
                )
                try:
                    metadata = os.fstat(descriptor)
                    if not stat.S_ISREG(metadata.st_mode):
                        raise RecordValidationError(
                            "controller artifact must be a regular file"
                        )
                    payload, digest, size = _read_and_hash(descriptor)
                    named = os.stat(
                        ref.sha256,
                        dir_fd=role_descriptor,
                        follow_symlinks=False,
                    )
                    if stat.S_ISLNK(named.st_mode) or (
                        metadata.st_dev,
                        metadata.st_ino,
                    ) != (named.st_dev, named.st_ino):
                        raise RecordValidationError(
                            "controller artifact identity changed during read"
                        )
                finally:
                    os.close(descriptor)
            finally:
                os.close(role_descriptor)
        except RecordValidationError:
            raise
        except OSError as exc:
            raise RecordValidationError(
                "controller artifact could not be safely resolved"
            ) from exc
        if digest != ref.sha256 or size != ref.byte_count:
            raise RecordValidationError(
                "controller artifact digest or length does not match"
            )
        return payload

    def close(self) -> None:
        artifact_descriptor = self._artifact_descriptor
        root_descriptor = self._root_descriptor
        self._artifact_descriptor = None
        self._root_descriptor = None
        if artifact_descriptor is not None:
            os.close(artifact_descriptor)
        if root_descriptor is not None:
            os.close(root_descriptor)
