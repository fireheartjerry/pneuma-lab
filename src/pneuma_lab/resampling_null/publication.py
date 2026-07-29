"""Descriptor-bound create-exclusive multi-file publication."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import secrets
import stat
from types import TracebackType
from typing import Literal

from .errors import RecordValidationError
from .publication_rollback import (
    CreatedDirectory as _CreatedDirectory,
)
from .publication_rollback import (
    OwnedPublication as _OwnedPublication,
)
from .publication_rollback import (
    OwnedTemporary as _OwnedTemporary,
)
from .publication_rollback import descriptor_digest as _descriptor_digest
from .publication_rollback import rename_no_replace as _rename_no_replace
from .publication_rollback import rollback_publication
from .types import ArtifactRef


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
_TEMPORARY_FLAGS = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC


class PublicationRollbackError(RecordValidationError):
    """Raised when transaction-owned publication state cannot be removed."""


@dataclass(frozen=True, slots=True)
class _DirectoryBinding:
    parts: tuple[str, ...]
    parent_parts: tuple[str, ...]
    name: str
    descriptor: int
    device: int
    inode: int


def _write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("short publication write")
        remaining = remaining[written:]


def _relative_parts(relative_path: str) -> tuple[str, ...]:
    if type(relative_path) is not str or not relative_path:
        raise RecordValidationError(
            "publication relative path must be non-empty exact text"
        )
    path = PurePosixPath(relative_path)
    parts = path.parts
    if (
        path.is_absolute()
        or not parts
        or any(part in ("", ".", "..") for part in parts)
        or path.as_posix() != relative_path
    ):
        raise RecordValidationError(
            "publication relative path must be canonical and confined"
        )
    return parts


class BoundPublication:
    """One held-root, create-exclusive, rollback-capable transaction."""

    def __init__(self, run_root: Path) -> None:
        self._named_root = Path(run_root).resolve(strict=True)
        if not self._named_root.is_dir():
            raise NotADirectoryError(self._named_root)
        self._root_descriptor: int | None = None
        self._root_device: int | None = None
        self._root_inode: int | None = None
        self._directories: dict[tuple[str, ...], _DirectoryBinding] = {}
        self._created_directories: list[_CreatedDirectory] = []
        self._owned: list[_OwnedPublication] = []
        self._temporaries: list[_OwnedTemporary] = []
        self._transaction = secrets.token_hex(16)
        self._counter = 0
        self._committed = False
        self._entered = False

    def __enter__(self) -> BoundPublication:
        if self._entered:
            raise RuntimeError("publication transaction cannot be re-entered")
        descriptor = os.open(self._named_root, _DIRECTORY_FLAGS)
        try:
            bound = os.fstat(descriptor)
            named = os.stat(self._named_root, follow_symlinks=False)
            if not stat.S_ISDIR(bound.st_mode) or (bound.st_dev, bound.st_ino) != (
                named.st_dev,
                named.st_ino,
            ):
                raise RecordValidationError("run_root identity changed during binding")
        except BaseException:
            os.close(descriptor)
            raise
        self._root_descriptor = descriptor
        self._root_device = bound.st_dev
        self._root_inode = bound.st_ino
        self._entered = True
        return self

    def _require_active(self) -> None:
        if not self._entered or self._root_descriptor is None:
            raise RuntimeError("publication transaction is not active")
        if self._committed:
            raise RuntimeError("publication transaction is already committed")

    def _descriptor(self, parts: tuple[str, ...]) -> int:
        if not parts:
            if self._root_descriptor is None:
                raise RuntimeError("publication root descriptor is closed")
            return self._root_descriptor
        return self._directories[parts].descriptor

    def _open_directory(
        self,
        parent_parts: tuple[str, ...],
        name: str,
    ) -> int:
        parent_descriptor = self._descriptor(parent_parts)
        created = False
        try:
            descriptor = os.open(
                name,
                _DIRECTORY_FLAGS,
                dir_fd=parent_descriptor,
            )
        except FileNotFoundError:
            os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
            created = True
            descriptor = os.open(
                name,
                _DIRECTORY_FLAGS,
                dir_fd=parent_descriptor,
            )
        try:
            bound = os.fstat(descriptor)
            named = os.stat(
                name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if not stat.S_ISDIR(bound.st_mode) or (bound.st_dev, bound.st_ino) != (
                named.st_dev,
                named.st_ino,
            ):
                raise RecordValidationError(
                    "directory identity changed during traversal"
                )
            if created:
                relative_path = PurePosixPath(
                    *parent_parts,
                    name,
                ).as_posix()
                self._created_directories.append(
                    _CreatedDirectory(
                        parent_parts=parent_parts,
                        name=name,
                        relative_path=relative_path,
                        device=bound.st_dev,
                        inode=bound.st_ino,
                    )
                )
                os.fsync(parent_descriptor)
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor

    def _parent_descriptor(
        self,
        parent_parts: tuple[str, ...],
    ) -> int:
        current: tuple[str, ...] = ()
        for component in parent_parts:
            child = (*current, component)
            if child not in self._directories:
                descriptor = self._open_directory(current, component)
                try:
                    metadata = os.fstat(descriptor)
                except BaseException:
                    os.close(descriptor)
                    raise
                self._directories[child] = _DirectoryBinding(
                    parts=child,
                    parent_parts=current,
                    name=component,
                    descriptor=descriptor,
                    device=metadata.st_dev,
                    inode=metadata.st_ino,
                )
            current = child
        return self._descriptor(current)

    def _temporary_name(self) -> str:
        self._counter += 1
        return f".pneuma-{self._transaction}-{self._counter}.tmp"

    def publish_bytes(
        self,
        relative_path: str,
        payload: bytes,
        *,
        role: str,
        media_type: str,
    ) -> ArtifactRef:
        self._require_active()
        if type(payload) is not bytes:
            raise TypeError("publication payload must be exact bytes")
        parts = _relative_parts(relative_path)
        parent_parts = parts[:-1]
        name = parts[-1]
        parent_descriptor = self._parent_descriptor(parent_parts)
        temporary_name = self._temporary_name()
        descriptor = os.open(
            temporary_name,
            _TEMPORARY_FLAGS,
            0o600,
            dir_fd=parent_descriptor,
        )
        try:
            created = os.fstat(descriptor)
            temporary = _OwnedTemporary(
                parent_parts=parent_parts,
                name=temporary_name,
                relative_path=PurePosixPath(
                    *parent_parts,
                    temporary_name,
                ).as_posix(),
                device=created.st_dev,
                inode=created.st_ino,
            )
            self._temporaries.append(temporary)
            _write_all(descriptor, payload)
            os.fsync(descriptor)
            prepared = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if not stat.S_ISREG(prepared.st_mode) or prepared.st_size != len(payload):
            raise RecordValidationError(
                "prepared publication is not the expected regular file"
            )
        os.link(
            temporary_name,
            name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        owned = _OwnedPublication(
            parent_parts=parent_parts,
            name=name,
            relative_path=relative_path,
            device=prepared.st_dev,
            inode=prepared.st_ino,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
        )
        self._owned.append(owned)
        os.unlink(temporary_name, dir_fd=parent_descriptor)
        self._temporaries.remove(temporary)
        os.fsync(parent_descriptor)
        self._verify_owned_name(owned, require_single_link=True)
        return ArtifactRef(
            role=role,
            relative_path=relative_path,
            sha256=owned.sha256,
            byte_count=owned.byte_count,
            media_type=media_type,
        )

    def _verify_owned_name(
        self,
        owned: _OwnedPublication,
        *,
        require_single_link: bool,
    ) -> bool:
        parent_descriptor = self._descriptor(owned.parent_parts)
        try:
            descriptor = os.open(
                owned.name,
                _READ_FLAGS,
                dir_fd=parent_descriptor,
            )
        except FileNotFoundError:
            return False
        try:
            metadata = os.fstat(descriptor)
            digest, size = _descriptor_digest(descriptor)
            named = os.stat(
                owned.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        finally:
            os.close(descriptor)
        return (
            stat.S_ISREG(metadata.st_mode)
            and (metadata.st_dev, metadata.st_ino) == (owned.device, owned.inode)
            and (named.st_dev, named.st_ino) == (owned.device, owned.inode)
            and digest == owned.sha256
            and size == owned.byte_count
            and (not require_single_link or getattr(metadata, "st_nlink", 1) == 1)
        )

    def _verify_named_identities(self) -> None:
        if (
            self._root_descriptor is None
            or self._root_device is None
            or self._root_inode is None
        ):
            raise RuntimeError("publication root descriptor is closed")
        try:
            named_root = os.stat(
                self._named_root,
                follow_symlinks=False,
            )
        except FileNotFoundError as exc:
            raise RecordValidationError(
                "run_root identity changed before publication commit"
            ) from exc
        if (named_root.st_dev, named_root.st_ino) != (
            self._root_device,
            self._root_inode,
        ):
            raise RecordValidationError(
                "run_root identity changed before publication commit"
            )
        for parts, binding in self._directories.items():
            parent_descriptor = self._descriptor(binding.parent_parts)
            try:
                named = os.stat(
                    binding.name,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError as exc:
                relative_path = PurePosixPath(*parts).as_posix()
                raise RecordValidationError(
                    f"directory identity changed: {relative_path}"
                ) from exc
            if not stat.S_ISDIR(named.st_mode) or (named.st_dev, named.st_ino) != (
                binding.device,
                binding.inode,
            ):
                relative_path = PurePosixPath(*parts).as_posix()
                raise RecordValidationError(
                    f"directory identity changed: {relative_path}"
                )
        for owned in self._owned:
            if not self._verify_owned_name(owned, require_single_link=True):
                raise RecordValidationError(
                    "published file identity changed before commit: "
                    f"{owned.relative_path}"
                )

    def commit(self) -> None:
        self._require_active()
        self._verify_named_identities()
        self._committed = True

    def _quarantine_name(self, index: int) -> str:
        return f".pneuma-{self._transaction}.rollback-{index}"

    def _temporary_quarantine_name(self, index: int) -> str:
        return f".pneuma-{self._transaction}.temp-rollback-{index}.tmp"

    def _directory_quarantine_name(self, index: int) -> str:
        return f".pneuma-{self._transaction}.dir-rollback-{index}"

    def _rollback(
        self,
        original: BaseException,
    ) -> None:
        failures, residuals = rollback_publication(
            owned=self._owned,
            temporaries=self._temporaries,
            directories=self._created_directories,
            descriptor_for=self._descriptor,
            owned_name_for=self._quarantine_name,
            temporary_name_for=self._temporary_quarantine_name,
            directory_name_for=self._directory_quarantine_name,
            rename=_rename_no_replace,
            read_flags=_READ_FLAGS,
        )
        if failures or residuals:
            details = "; ".join(
                [
                    *failures,
                    *(f"residual path: {path}" for path in residuals),
                ]
            )
            raise PublicationRollbackError(
                f"publication rollback incomplete: {details}"
            ) from original

    def _close(self) -> list[str]:
        failures: list[str] = []
        for binding in reversed(tuple(self._directories.values())):
            try:
                os.close(binding.descriptor)
            except OSError as exc:
                relative_path = PurePosixPath(*binding.parts).as_posix()
                failures.append(f"{relative_path}: {type(exc).__name__}: {exc}")
        self._directories.clear()
        if self._root_descriptor is not None:
            try:
                os.close(self._root_descriptor)
            except OSError as exc:
                failures.append(f"run_root: {type(exc).__name__}: {exc}")
            finally:
                self._root_descriptor = None
        return failures

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        del exception_type, traceback
        original = exception
        if original is None and not self._committed:
            original = RecordValidationError(
                "publication transaction exited without commit"
            )
        rollback_failure: BaseException | None = None
        if original is not None:
            try:
                self._rollback(original)
            except BaseException as exc:
                rollback_failure = exc
        close_failures = self._close()
        if close_failures:
            close_error = PublicationRollbackError(
                "publication descriptor close incomplete: " + "; ".join(close_failures)
            )
            cause = rollback_failure if rollback_failure is not None else original
            if cause is not None:
                raise close_error from cause
            raise close_error
        if rollback_failure is not None:
            raise rollback_failure
        if exception is None and original is not None:
            raise original
        return False
