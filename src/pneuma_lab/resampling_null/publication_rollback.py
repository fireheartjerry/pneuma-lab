"""Ownership-safe rollback primitives for descriptor-bound publication."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import PurePosixPath
import stat
from collections.abc import Callable, Iterable
from typing import Any, Protocol, TypeVar


_HASH_CHUNK_BYTES = 1024 * 1024
_RENAME_NOREPLACE = 1
_LIBC = ctypes.CDLL(None, use_errno=True)
_RENAMEAT2: Any = getattr(_LIBC, "renameat2", None)
if _RENAMEAT2 is not None:
    _RENAMEAT2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    _RENAMEAT2.restype = ctypes.c_int


@dataclass(frozen=True, slots=True)
class CreatedDirectory:
    parent_parts: tuple[str, ...]
    name: str
    relative_path: str
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class OwnedPublication:
    parent_parts: tuple[str, ...]
    name: str
    relative_path: str
    device: int
    inode: int
    sha256: str
    byte_count: int


@dataclass(frozen=True, slots=True)
class OwnedTemporary:
    parent_parts: tuple[str, ...]
    name: str
    relative_path: str
    device: int
    inode: int


class DescriptorResolver(Protocol):
    def __call__(self, parts: tuple[str, ...]) -> int: ...


class QuarantineName(Protocol):
    def __call__(self, index: int) -> str: ...


class RenameNoReplace(Protocol):
    def __call__(
        self,
        source_name: str,
        destination_name: str,
        *,
        source_descriptor: int,
        destination_descriptor: int,
    ) -> None: ...


class RollbackItem(Protocol):
    @property
    def relative_path(self) -> str: ...


_RollbackItemT = TypeVar("_RollbackItemT", bound=RollbackItem)
_RollbackResult = tuple[list[str], list[str]]


def descriptor_digest(descriptor: int) -> tuple[str, int]:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    while chunk := os.read(descriptor, _HASH_CHUNK_BYTES):
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def rename_no_replace(
    source_name: str,
    destination_name: str,
    *,
    source_descriptor: int,
    destination_descriptor: int,
) -> None:
    """Atomically rename one dirfd-relative name without replacement."""

    if _RENAMEAT2 is None:
        raise OSError(
            errno.ENOSYS,
            "renameat2(RENAME_NOREPLACE) is unavailable",
        )
    result = _RENAMEAT2(
        source_descriptor,
        os.fsencode(source_name),
        destination_descriptor,
        os.fsencode(destination_name),
        _RENAME_NOREPLACE,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(
            error_number,
            os.strerror(error_number),
            source_name,
            destination_name,
        )


def _restore_quarantine(
    parent_descriptor: int,
    quarantine_name: str,
    destination_name: str,
    *,
    rename: RenameNoReplace,
) -> None:
    rename(
        quarantine_name,
        destination_name,
        source_descriptor=parent_descriptor,
        destination_descriptor=parent_descriptor,
    )
    os.fsync(parent_descriptor)


def _rollback_owned(
    owned: OwnedPublication,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
    read_flags: int,
) -> tuple[list[str], list[str]]:
    parent = descriptor_for(owned.parent_parts)
    quarantine_name = quarantine_name_for(index)
    quarantine_relative = PurePosixPath(
        *owned.parent_parts,
        quarantine_name,
    ).as_posix()
    try:
        rename(
            owned.name,
            quarantine_name,
            source_descriptor=parent,
            destination_descriptor=parent,
        )
    except FileNotFoundError:
        return [], []
    except BaseException as exc:
        return (
            [
                f"{owned.relative_path} quarantine move to "
                f"{quarantine_relative}: {type(exc).__name__}: {exc}"
            ],
            [owned.relative_path],
        )
    try:
        descriptor = os.open(quarantine_name, read_flags, dir_fd=parent)
        try:
            metadata = os.fstat(descriptor)
            digest, size = descriptor_digest(descriptor)
        finally:
            os.close(descriptor)
    except BaseException as exc:
        classification_failure: BaseException | None = None
        confirmed_peer = False
        try:
            named = os.stat(
                quarantine_name,
                dir_fd=parent,
                follow_symlinks=False,
            )
            confirmed_peer = not stat.S_ISREG(named.st_mode) or (
                named.st_dev,
                named.st_ino,
            ) != (owned.device, owned.inode)
        except BaseException as classification_exc:
            classification_failure = classification_exc
        try:
            _restore_quarantine(
                parent,
                quarantine_name,
                owned.name,
                rename=rename,
            )
        except BaseException as restore_exc:
            return (
                [
                    f"{quarantine_relative} inspection: {type(exc).__name__}: {exc}",
                    f"{quarantine_relative} restore: "
                    f"{type(restore_exc).__name__}: {restore_exc}",
                ],
                [quarantine_relative],
            )
        if confirmed_peer:
            return [], []
        failures = [
            f"{owned.relative_path} quarantine inspection: {type(exc).__name__}: {exc}"
        ]
        if classification_failure is not None:
            failures.append(
                f"{owned.relative_path} quarantine classification: "
                f"{type(classification_failure).__name__}: "
                f"{classification_failure}"
            )
        return failures, [owned.relative_path]
    identity_matches = (
        stat.S_ISREG(metadata.st_mode)
        and (metadata.st_dev, metadata.st_ino) == (owned.device, owned.inode)
        and digest == owned.sha256
        and size == owned.byte_count
    )
    confirmed_peer = not stat.S_ISREG(metadata.st_mode) or (
        metadata.st_dev,
        metadata.st_ino,
    ) != (owned.device, owned.inode)
    link_count = getattr(metadata, "st_nlink", 1)
    if identity_matches and link_count == 1:
        try:
            os.unlink(quarantine_name, dir_fd=parent)
            os.fsync(parent)
        except BaseException as exc:
            return (
                [f"{quarantine_relative}: {type(exc).__name__}: {exc}"],
                [quarantine_relative],
            )
        return [], []
    try:
        _restore_quarantine(
            parent,
            quarantine_name,
            owned.name,
            rename=rename,
        )
        residual_name = owned.relative_path
    except BaseException as exc:
        failures = [f"{quarantine_relative} restore: {type(exc).__name__}: {exc}"]
        residual_name = quarantine_relative
    else:
        failures = []
    if identity_matches:
        failures.append(
            f"{owned.relative_path}: link count {link_count} prevents rollback"
        )
        return failures, [residual_name]
    if confirmed_peer:
        if residual_name == quarantine_relative:
            return failures, [residual_name]
        return failures, []
    failures.append(f"{owned.relative_path}: owned content changed during rollback")
    if residual_name == quarantine_relative:
        return failures, [residual_name]
    return failures, [owned.relative_path]


def _rollback_temporary(
    temporary: OwnedTemporary,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
) -> tuple[list[str], list[str]]:
    parent = descriptor_for(temporary.parent_parts)
    quarantine_name = quarantine_name_for(index)
    quarantine_relative = PurePosixPath(
        *temporary.parent_parts,
        quarantine_name,
    ).as_posix()
    try:
        rename(
            temporary.name,
            quarantine_name,
            source_descriptor=parent,
            destination_descriptor=parent,
        )
    except FileNotFoundError:
        return [], []
    except BaseException as exc:
        return (
            [
                f"{temporary.relative_path} quarantine move to "
                f"{quarantine_relative}: {type(exc).__name__}: {exc}"
            ],
            [temporary.relative_path],
        )
    try:
        metadata = os.stat(
            quarantine_name,
            dir_fd=parent,
            follow_symlinks=False,
        )
    except BaseException as exc:
        try:
            _restore_quarantine(
                parent,
                quarantine_name,
                temporary.name,
                rename=rename,
            )
        except BaseException as restore_exc:
            return (
                [
                    f"{quarantine_relative} inspection: {type(exc).__name__}: {exc}",
                    f"{quarantine_relative} restore: "
                    f"{type(restore_exc).__name__}: {restore_exc}",
                ],
                [quarantine_relative],
            )
        return (
            [
                f"{temporary.relative_path} quarantine inspection: "
                f"{type(exc).__name__}: {exc}"
            ],
            [temporary.relative_path],
        )
    identity_matches = stat.S_ISREG(metadata.st_mode) and (
        metadata.st_dev,
        metadata.st_ino,
    ) == (temporary.device, temporary.inode)
    if identity_matches:
        try:
            os.unlink(quarantine_name, dir_fd=parent)
            os.fsync(parent)
        except BaseException as exc:
            return (
                [f"{quarantine_relative}: {type(exc).__name__}: {exc}"],
                [quarantine_relative],
            )
        return [], []
    try:
        _restore_quarantine(
            parent,
            quarantine_name,
            temporary.name,
            rename=rename,
        )
    except BaseException as exc:
        return (
            [f"{quarantine_relative} restore: {type(exc).__name__}: {exc}"],
            [quarantine_relative],
        )
    return [], []


def _rollback_directory(
    created: CreatedDirectory,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
) -> tuple[list[str], list[str]]:
    parent = descriptor_for(created.parent_parts)
    quarantine_name = quarantine_name_for(index)
    quarantine_relative = PurePosixPath(
        *created.parent_parts,
        quarantine_name,
    ).as_posix()
    try:
        rename(
            created.name,
            quarantine_name,
            source_descriptor=parent,
            destination_descriptor=parent,
        )
    except FileNotFoundError:
        return [], []
    except BaseException as exc:
        return (
            [
                f"{created.relative_path} quarantine move to "
                f"{quarantine_relative}: {type(exc).__name__}: {exc}"
            ],
            [created.relative_path],
        )
    try:
        metadata = os.stat(
            quarantine_name,
            dir_fd=parent,
            follow_symlinks=False,
        )
    except BaseException as exc:
        try:
            _restore_quarantine(
                parent,
                quarantine_name,
                created.name,
                rename=rename,
            )
        except BaseException as restore_exc:
            return (
                [
                    f"{quarantine_relative} inspection: {type(exc).__name__}: {exc}",
                    f"{quarantine_relative} restore: "
                    f"{type(restore_exc).__name__}: {restore_exc}",
                ],
                [quarantine_relative],
            )
        return (
            [f"{created.relative_path}: directory identity changed during rollback"],
            [],
        )
    identity_matches = stat.S_ISDIR(metadata.st_mode) and (
        metadata.st_dev,
        metadata.st_ino,
    ) == (created.device, created.inode)
    if not identity_matches:
        try:
            _restore_quarantine(
                parent,
                quarantine_name,
                created.name,
                rename=rename,
            )
        except BaseException as exc:
            return (
                [
                    f"{created.relative_path}: directory identity "
                    "changed during rollback",
                    f"{quarantine_relative} restore: {type(exc).__name__}: {exc}",
                ],
                [quarantine_relative],
            )
        return (
            [f"{created.relative_path}: directory identity changed during rollback"],
            [],
        )
    try:
        os.rmdir(quarantine_name, dir_fd=parent)
        os.fsync(parent)
    except BaseException as exc:
        return (
            [f"{quarantine_relative}: {type(exc).__name__}: {exc}"],
            [quarantine_relative],
        )
    return [], []


def _collect_rollbacks(
    items: Iterable[_RollbackItemT],
    operation: Callable[[_RollbackItemT, int], _RollbackResult],
) -> _RollbackResult:
    failures: list[str] = []
    residuals: list[str] = []
    for index, item in enumerate(items, start=1):
        try:
            item_failures, item_residuals = operation(item, index)
        except BaseException as exc:
            item_failures = [f"{item.relative_path}: {type(exc).__name__}: {exc}"]
            item_residuals = [item.relative_path]
        failures.extend(item_failures)
        residuals.extend(item_residuals)
    return failures, residuals


def rollback_publication(
    *,
    owned: list[OwnedPublication],
    temporaries: list[OwnedTemporary],
    directories: list[CreatedDirectory],
    descriptor_for: DescriptorResolver,
    owned_name_for: QuarantineName,
    temporary_name_for: QuarantineName,
    directory_name_for: QuarantineName,
    rename: RenameNoReplace,
    read_flags: int,
) -> tuple[list[str], list[str]]:
    """Best-effort all rollback items and return every failure/residual."""

    temporary_failures, temporary_residuals = _collect_rollbacks(
        reversed(temporaries),
        lambda item, index: _rollback_temporary(
            item,
            index=index,
            descriptor_for=descriptor_for,
            quarantine_name_for=temporary_name_for,
            rename=rename,
        ),
    )
    owned_failures, owned_residuals = _collect_rollbacks(
        reversed(owned),
        lambda item, index: _rollback_owned(
            item,
            index=index,
            descriptor_for=descriptor_for,
            quarantine_name_for=owned_name_for,
            rename=rename,
            read_flags=read_flags,
        ),
    )
    directory_failures, directory_residuals = _collect_rollbacks(
        reversed(directories),
        lambda item, index: _rollback_directory(
            item,
            index=index,
            descriptor_for=descriptor_for,
            quarantine_name_for=directory_name_for,
            rename=rename,
        ),
    )
    return (
        [
            *temporary_failures,
            *owned_failures,
            *directory_failures,
        ],
        [
            *temporary_residuals,
            *owned_residuals,
            *directory_residuals,
        ],
    )


__all__ = (
    "CreatedDirectory",
    "OwnedPublication",
    "OwnedTemporary",
    "descriptor_digest",
    "rename_no_replace",
    "rollback_publication",
)
