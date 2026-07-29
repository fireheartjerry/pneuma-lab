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
_PATH_FLAGS = getattr(os, "O_PATH", 0) | os.O_NOFOLLOW | os.O_CLOEXEC
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
    device: int | None
    inode: int | None


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
    device: int | None
    inode: int | None


@dataclass(frozen=True, slots=True)
class _QuarantinedSource:
    parent_descriptor: int
    source_descriptor: int
    source_metadata: os.stat_result
    quarantine_name: str
    quarantine_relative: str


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


def _close_source(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        pass


def _quarantine_source(
    *,
    parent_parts: tuple[str, ...],
    name: str,
    relative_path: str,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
) -> tuple[_QuarantinedSource | None, list[str], list[str]]:
    parent = descriptor_for(parent_parts)
    quarantine_name = quarantine_name_for(index)
    quarantine_relative = PurePosixPath(
        *parent_parts,
        quarantine_name,
    ).as_posix()
    if not getattr(os, "O_PATH", 0):
        return (
            None,
            [f"{relative_path}: O_PATH identity binding unavailable"],
            [relative_path],
        )
    try:
        source_descriptor = os.open(name, _PATH_FLAGS, dir_fd=parent)
    except FileNotFoundError:
        return None, [], []
    except BaseException as exc:
        return (
            None,
            [f"{relative_path} source identity open: {type(exc).__name__}: {exc}"],
            [relative_path],
        )
    keep_open = False
    try:
        source_metadata = os.fstat(source_descriptor)
        try:
            rename(
                name,
                quarantine_name,
                source_descriptor=parent,
                destination_descriptor=parent,
            )
        except FileNotFoundError as exc:
            return (
                None,
                [
                    f"{relative_path}: ownership lost before quarantine move: "
                    f"{type(exc).__name__}: {exc}"
                ],
                [relative_path],
            )
        except BaseException as exc:
            return (
                None,
                [
                    f"{relative_path} quarantine move to "
                    f"{quarantine_relative}: {type(exc).__name__}: {exc}"
                ],
                [relative_path],
            )
        try:
            named = os.stat(
                quarantine_name,
                dir_fd=parent,
                follow_symlinks=False,
            )
        except BaseException as exc:
            failures = [
                f"{quarantine_relative} identity inspection: "
                f"{type(exc).__name__}: {exc}"
            ]
            try:
                _restore_quarantine(
                    parent,
                    quarantine_name,
                    name,
                    rename=rename,
                )
            except BaseException as restore_exc:
                failures.append(
                    f"{quarantine_relative} restore: "
                    f"{type(restore_exc).__name__}: {restore_exc}"
                )
                return None, failures, [quarantine_relative]
            return None, failures, [relative_path]
        if (named.st_dev, named.st_ino) != (
            source_metadata.st_dev,
            source_metadata.st_ino,
        ):
            try:
                held_after_move = os.fstat(source_descriptor)
            except BaseException as exc:
                ownership_reachable = True
                failures = [
                    f"{relative_path}: ownership reachability inspection: "
                    f"{type(exc).__name__}: {exc}"
                ]
            else:
                ownership_reachable = getattr(held_after_move, "st_nlink", 1) > 0
                failures = (
                    [f"{relative_path}: ownership lost after quarantine move"]
                    if ownership_reachable
                    else []
                )
            try:
                _restore_quarantine(
                    parent,
                    quarantine_name,
                    name,
                    rename=rename,
                )
            except BaseException as exc:
                failures.append(
                    f"{quarantine_relative} restore: {type(exc).__name__}: {exc}"
                )
                return None, failures, [quarantine_relative]
            if ownership_reachable:
                return None, failures, [relative_path]
            return None, [], []
        binding = _QuarantinedSource(
            parent_descriptor=parent,
            source_descriptor=source_descriptor,
            source_metadata=source_metadata,
            quarantine_name=quarantine_name,
            quarantine_relative=quarantine_relative,
        )
        keep_open = True
        return binding, [], []
    finally:
        if not keep_open:
            _close_source(source_descriptor)


def _restore_bound_source(
    binding: _QuarantinedSource,
    destination_name: str,
    *,
    relative_path: str,
    rename: RenameNoReplace,
    failure: str | None = None,
) -> tuple[list[str], list[str]]:
    failures = [] if failure is None else [failure]
    try:
        _restore_quarantine(
            binding.parent_descriptor,
            binding.quarantine_name,
            destination_name,
            rename=rename,
        )
    except BaseException as exc:
        failures.append(
            f"{binding.quarantine_relative} restore: {type(exc).__name__}: {exc}"
        )
        return failures, [binding.quarantine_relative]
    if failure is None:
        return [], []
    return failures, [relative_path]


def _binding_matches_named(
    binding: _QuarantinedSource,
    metadata: os.stat_result,
) -> bool:
    return (metadata.st_dev, metadata.st_ino) == (
        binding.source_metadata.st_dev,
        binding.source_metadata.st_ino,
    )


def _recheck_quarantine(
    binding: _QuarantinedSource,
    destination_name: str,
    *,
    relative_path: str,
    rename: RenameNoReplace,
) -> tuple[bool, list[str], list[str]]:
    try:
        named = os.stat(
            binding.quarantine_name,
            dir_fd=binding.parent_descriptor,
            follow_symlinks=False,
        )
    except BaseException as exc:
        failures, residuals = _restore_bound_source(
            binding,
            destination_name,
            relative_path=relative_path,
            rename=rename,
            failure=(
                f"{binding.quarantine_relative} identity inspection: "
                f"{type(exc).__name__}: {exc}"
            ),
        )
        return False, failures, residuals
    if not _binding_matches_named(binding, named):
        failures, residuals = _restore_bound_source(
            binding,
            destination_name,
            relative_path=relative_path,
            rename=rename,
            failure=(f"{relative_path}: ownership lost after quarantine move"),
        )
        return False, failures, residuals
    return True, [], []


def _rollback_owned(
    owned: OwnedPublication,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
    read_flags: int,
) -> tuple[list[str], list[str]]:
    binding, failures, residuals = _quarantine_source(
        parent_parts=owned.parent_parts,
        name=owned.name,
        relative_path=owned.relative_path,
        index=index,
        descriptor_for=descriptor_for,
        quarantine_name_for=quarantine_name_for,
        rename=rename,
    )
    if binding is None:
        return failures, residuals
    try:
        source_is_owned = stat.S_ISREG(binding.source_metadata.st_mode) and (
            binding.source_metadata.st_dev,
            binding.source_metadata.st_ino,
        ) == (owned.device, owned.inode)
        if not source_is_owned:
            matches, failures, residuals = _recheck_quarantine(
                binding,
                owned.name,
                relative_path=owned.relative_path,
                rename=rename,
            )
            if not matches:
                return failures, residuals
            return _restore_bound_source(
                binding,
                owned.name,
                relative_path=owned.relative_path,
                rename=rename,
            )
        try:
            descriptor = os.open(
                binding.quarantine_name,
                read_flags,
                dir_fd=binding.parent_descriptor,
            )
            try:
                metadata = os.fstat(descriptor)
                if not _binding_matches_named(binding, metadata):
                    raise OSError("quarantine read identity changed")
                digest, size = descriptor_digest(descriptor)
            finally:
                os.close(descriptor)
        except BaseException as exc:
            matches, failures, residuals = _recheck_quarantine(
                binding,
                owned.name,
                relative_path=owned.relative_path,
                rename=rename,
            )
            if not matches:
                return failures, residuals
            return _restore_bound_source(
                binding,
                owned.name,
                relative_path=owned.relative_path,
                rename=rename,
                failure=(
                    f"{owned.relative_path} quarantine inspection: "
                    f"{type(exc).__name__}: {exc}"
                ),
            )
        matches, failures, residuals = _recheck_quarantine(
            binding,
            owned.name,
            relative_path=owned.relative_path,
            rename=rename,
        )
        if not matches:
            return failures, residuals
        identity_matches = (
            stat.S_ISREG(metadata.st_mode)
            and digest == owned.sha256
            and size == owned.byte_count
        )
        link_count = getattr(metadata, "st_nlink", 1)
        if identity_matches and link_count == 1:
            try:
                os.unlink(
                    binding.quarantine_name,
                    dir_fd=binding.parent_descriptor,
                )
                os.fsync(binding.parent_descriptor)
            except BaseException as exc:
                return (
                    [f"{binding.quarantine_relative}: {type(exc).__name__}: {exc}"],
                    [binding.quarantine_relative],
                )
            return [], []
        if identity_matches:
            failure = (
                f"{owned.relative_path}: link count {link_count} prevents rollback"
            )
        else:
            failure = f"{owned.relative_path}: owned content changed during rollback"
        return _restore_bound_source(
            binding,
            owned.name,
            relative_path=owned.relative_path,
            rename=rename,
            failure=failure,
        )
    finally:
        _close_source(binding.source_descriptor)


def _rollback_temporary(
    temporary: OwnedTemporary,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
) -> tuple[list[str], list[str]]:
    if temporary.device is None or temporary.inode is None:
        return (
            [
                f"{temporary.relative_path}: identity unavailable; "
                "uncertain created name preserved"
            ],
            [temporary.relative_path],
        )
    binding, failures, residuals = _quarantine_source(
        parent_parts=temporary.parent_parts,
        name=temporary.name,
        relative_path=temporary.relative_path,
        index=index,
        descriptor_for=descriptor_for,
        quarantine_name_for=quarantine_name_for,
        rename=rename,
    )
    if binding is None:
        return failures, residuals
    try:
        source_is_owned = stat.S_ISREG(binding.source_metadata.st_mode) and (
            binding.source_metadata.st_dev,
            binding.source_metadata.st_ino,
        ) == (temporary.device, temporary.inode)
        matches, failures, residuals = _recheck_quarantine(
            binding,
            temporary.name,
            relative_path=temporary.relative_path,
            rename=rename,
        )
        if not matches:
            return failures, residuals
        if not source_is_owned:
            return _restore_bound_source(
                binding,
                temporary.name,
                relative_path=temporary.relative_path,
                rename=rename,
            )
        try:
            os.unlink(
                binding.quarantine_name,
                dir_fd=binding.parent_descriptor,
            )
            os.fsync(binding.parent_descriptor)
        except BaseException as exc:
            return (
                [f"{binding.quarantine_relative}: {type(exc).__name__}: {exc}"],
                [binding.quarantine_relative],
            )
        return [], []
    finally:
        _close_source(binding.source_descriptor)


def _rollback_directory(
    created: CreatedDirectory,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
) -> tuple[list[str], list[str]]:
    if created.device is None or created.inode is None:
        return (
            [
                f"{created.relative_path}: identity unavailable; "
                "uncertain created name preserved"
            ],
            [created.relative_path],
        )
    binding, failures, residuals = _quarantine_source(
        parent_parts=created.parent_parts,
        name=created.name,
        relative_path=created.relative_path,
        index=index,
        descriptor_for=descriptor_for,
        quarantine_name_for=quarantine_name_for,
        rename=rename,
    )
    if binding is None:
        return failures, residuals
    try:
        source_is_owned = stat.S_ISDIR(binding.source_metadata.st_mode) and (
            binding.source_metadata.st_dev,
            binding.source_metadata.st_ino,
        ) == (created.device, created.inode)
        matches, failures, residuals = _recheck_quarantine(
            binding,
            created.name,
            relative_path=created.relative_path,
            rename=rename,
        )
        if not matches:
            return failures, residuals
        if not source_is_owned:
            return _restore_bound_source(
                binding,
                created.name,
                relative_path=created.relative_path,
                rename=rename,
                failure=(
                    f"{created.relative_path}: "
                    "directory identity changed during rollback"
                ),
            )
        try:
            os.rmdir(
                binding.quarantine_name,
                dir_fd=binding.parent_descriptor,
            )
            os.fsync(binding.parent_descriptor)
        except BaseException as exc:
            return (
                [f"{binding.quarantine_relative}: {type(exc).__name__}: {exc}"],
                [binding.quarantine_relative],
            )
        return [], []
    finally:
        _close_source(binding.source_descriptor)


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
