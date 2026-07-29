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
from .prefix_contracts import CONTROLLER_ROLE_MEDIA
from .types import ArtifactRef


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
_ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MEDIA_TYPE_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+*-]*/[a-z0-9][a-z0-9!#$&^_.+*-]*$"
)
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
    if _MEDIA_TYPE_PATTERN.fullmatch(media_type) is None:
        raise ValueError(
            "media_type must be a lowercase canonical type/subtype without parameters"
        )
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
        self._writes: dict[ArtifactRef, bytes] = {}
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
        registered_media_type = CONTROLLER_ROLE_MEDIA.get(validated_role)
        if registered_media_type is None:
            raise RecordValidationError("controller artifact role is not registered")
        if validated_media_type != registered_media_type:
            raise RecordValidationError(
                "controller artifact media type differs from canonical role authority"
            )
        if type(payload) is not bytes:
            raise TypeError("payload must be exact bytes")
        digest = hashlib.sha256(payload).hexdigest()
        role_descriptor = _mkdir_or_open(artifact_descriptor, validated_role)
        owned: dict[str, int] = {"role": role_descriptor}
        created = False

        def close_owned(name: str, errors: list[Exception] | None = None) -> None:
            descriptor = owned.pop(name, None)
            if descriptor is None:
                return
            try:
                os.close(descriptor)
            except OSError as exc:
                if errors is None:
                    raise
                errors.append(exc)

        try:
            try:
                owned["write"] = os.open(
                    digest,
                    _WRITE_FLAGS,
                    0o600,
                    dir_fd=role_descriptor,
                )
            except FileExistsError:
                try:
                    owned["read"] = os.open(
                        digest,
                        _READ_FLAGS,
                        dir_fd=role_descriptor,
                    )
                except OSError as exc:
                    raise RecordValidationError(
                        "existing controller artifact could not be safely reopened"
                    ) from exc
                metadata = os.fstat(owned["read"])
                if not stat.S_ISREG(metadata.st_mode):
                    raise RecordValidationError(
                        "existing controller artifact is not a regular file"
                    )
                observed, observed_digest, observed_size = _read_and_hash(owned["read"])
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
                        "existing controller artifact identity changed during reuse"
                    )
                if (
                    observed != payload
                    or observed_digest != digest
                    or observed_size != len(payload)
                ):
                    raise RecordValidationError(
                        "existing controller artifact differs from exact reuse bytes"
                    )
                close_owned("read")
                close_owned("role")
                reused_ref = ArtifactRef(
                    role=validated_role,
                    relative_path=(f"{_ARTIFACT_DIRECTORY}/{validated_role}/{digest}"),
                    sha256=digest,
                    byte_count=len(payload),
                    media_type=validated_media_type,
                )
                self._writes[reused_ref] = payload
                return reused_ref
            created = True
            _write_all(owned["write"], payload)
            os.fsync(owned["write"])
            close_owned("write")
            os.fsync(role_descriptor)
            owned["read"] = os.open(
                digest,
                _READ_FLAGS,
                dir_fd=role_descriptor,
            )
            metadata = os.fstat(owned["read"])
            if not stat.S_ISREG(metadata.st_mode):
                raise RecordValidationError(
                    "new controller artifact is not a regular file"
                )
            observed, observed_digest, observed_size = _read_and_hash(owned["read"])
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
            if (
                observed != payload
                or observed_digest != digest
                or observed_size != len(payload)
            ):
                raise RecordValidationError(
                    "controller artifact bytes changed during verified write"
                )
            close_owned("read")
            close_owned("role")
        except BaseException as primary_error:
            cleanup_errors: list[Exception] = []
            close_owned("write", cleanup_errors)
            close_owned("read", cleanup_errors)
            cleanup_role = owned.get("role")
            if cleanup_role is None and created:
                try:
                    cleanup_role = os.open(
                        validated_role,
                        _DIRECTORY_FLAGS,
                        dir_fd=artifact_descriptor,
                    )
                    owned["cleanup_role"] = cleanup_role
                except OSError as exc:
                    cleanup_errors.append(exc)
            if created and cleanup_role is not None:
                try:
                    os.unlink(digest, dir_fd=cleanup_role)
                except OSError as exc:
                    cleanup_errors.append(exc)
                try:
                    os.fsync(cleanup_role)
                except OSError as exc:
                    cleanup_errors.append(exc)
            close_owned("role", cleanup_errors)
            close_owned("cleanup_role", cleanup_errors)
            if not isinstance(primary_error, Exception):
                if cleanup_errors:
                    raise BaseExceptionGroup(
                        "controller artifact write cleanup is uncertain",
                        [primary_error, *cleanup_errors],
                    )
                raise
            if created or cleanup_errors:
                message = (
                    "controller artifact write cleanup is uncertain"
                    if cleanup_errors
                    else "controller artifact write transaction aborted"
                )
                raise ExceptionGroup(
                    message,
                    [primary_error, *cleanup_errors],
                )
            raise
        written_ref = ArtifactRef(
            role=validated_role,
            relative_path=f"{_ARTIFACT_DIRECTORY}/{validated_role}/{digest}",
            sha256=digest,
            byte_count=len(payload),
            media_type=validated_media_type,
        )
        self._writes[written_ref] = payload
        return written_ref

    def snapshot_writes(self) -> dict[ArtifactRef, bytes]:
        """Copy exact caller bytes for every successful write in this transaction."""

        self._require_open()
        return dict(self._writes)

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
        self._path_bindings: dict[str, ArtifactRef] = {}
        self._physical_bindings: dict[tuple[int, int], ArtifactRef] = {}
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

    def resolve(
        self,
        ref: ArtifactRef,
        *,
        expected_role: str,
        expected_media_type: str,
    ) -> bytes:
        """Reopen and recompute role, path, hash, length, and exact bytes."""

        _root_descriptor, artifact_descriptor = self._require_open()
        if type(ref) is not ArtifactRef:
            raise TypeError("ref must be exact ArtifactRef")
        validated_role = _role(expected_role)
        validated_media_type = _media_type(expected_media_type)
        authoritative_media_type = CONTROLLER_ROLE_MEDIA.get(validated_role)
        if authoritative_media_type is None:
            raise RecordValidationError("controller artifact role is not registered")
        if validated_media_type != authoritative_media_type:
            raise RecordValidationError(
                "controller artifact expected media is not canonical"
            )
        if ref.role != validated_role:
            raise RecordValidationError(
                "controller artifact role differs from controller expectation"
            )
        if ref.media_type != validated_media_type:
            raise RecordValidationError(
                "controller artifact media type differs from controller expectation"
            )
        previous_path = self._path_bindings.get(ref.relative_path)
        if previous_path is not None and previous_path != ref:
            raise RecordValidationError(
                "controller artifact path is aliased across refs"
            )
        self._path_bindings[ref.relative_path] = ref
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
                    physical = (metadata.st_dev, metadata.st_ino)
                    previous_physical = self._physical_bindings.get(physical)
                    if previous_physical is not None and previous_physical != ref:
                        raise RecordValidationError(
                            "controller artifact physical file is aliased"
                        )
                    self._physical_bindings[physical] = ref
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
        errors: list[Exception] = []
        if artifact_descriptor is not None:
            try:
                os.close(artifact_descriptor)
            except OSError as exc:
                errors.append(exc)
        if root_descriptor is not None:
            try:
                os.close(root_descriptor)
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup(
                "controller artifact resolver close was incomplete",
                errors,
            )
