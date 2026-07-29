"""Ownership-safe rollback primitives for descriptor-bound publication."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import errno
import hashlib
import os
import stat
from collections.abc import Callable, Iterable
from typing import Any, Protocol, TypeVar

from .publication_quarantine import RollbackResidual
from .publication_quarantine import QuarantinedSource
from .publication_quarantine import UnlocatedOwnedIdentity
from .publication_quarantine import (
    binding_matches_named as _binding_matches_named,
)
from .publication_quarantine import close_source as _close_source
from .publication_quarantine import quarantine_source as _quarantine_source
from .publication_quarantine import recheck_quarantine as _recheck_quarantine
from .publication_quarantine import render_rollback_residual
from .publication_quarantine import (
    restore_bound_source as _restore_bound_source,
)


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
_RollbackResult = tuple[list[str], list[RollbackResidual]]


def _finish_bound_source(
    binding: QuarantinedSource,
    result: _RollbackResult,
    *,
    prior_failures: list[str],
    prior_residuals: list[RollbackResidual],
) -> _RollbackResult:
    failures, residuals = result
    close_failures, close_residuals = _close_source(
        binding.source_descriptor,
        purpose="rollback source",
    )
    return (
        [*prior_failures, *failures, *close_failures],
        [*prior_residuals, *residuals, *close_residuals],
    )


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


def _rollback_owned(
    owned: OwnedPublication,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
    read_flags: int,
) -> _RollbackResult:
    binding, failures, residuals = _quarantine_source(
        parent_parts=owned.parent_parts,
        name=owned.name,
        relative_path=owned.relative_path,
        index=index,
        descriptor_for=descriptor_for,
        quarantine_name_for=quarantine_name_for,
        rename=rename,
        expected_device=owned.device,
        expected_inode=owned.inode,
    )
    if binding is None:
        return failures, residuals
    prior_failures = failures
    prior_residuals = residuals

    def finish(result: _RollbackResult) -> _RollbackResult:
        return _finish_bound_source(
            binding,
            result,
            prior_failures=prior_failures,
            prior_residuals=prior_residuals,
        )

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
                expected_device=owned.device,
                expected_inode=owned.inode,
            )
            if not matches:
                return finish((failures, residuals))
            return finish(
                _restore_bound_source(
                    binding,
                    owned.name,
                    relative_path=owned.relative_path,
                    rename=rename,
                )
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
                expected_device=owned.device,
                expected_inode=owned.inode,
            )
            if not matches:
                return finish((failures, residuals))
            return finish(
                _restore_bound_source(
                    binding,
                    owned.name,
                    relative_path=owned.relative_path,
                    rename=rename,
                    failure=(
                        f"{owned.relative_path} quarantine inspection: "
                        f"{type(exc).__name__}: {exc}"
                    ),
                )
            )
        matches, failures, residuals = _recheck_quarantine(
            binding,
            owned.name,
            relative_path=owned.relative_path,
            rename=rename,
            expected_device=owned.device,
            expected_inode=owned.inode,
        )
        if not matches:
            return finish((failures, residuals))
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
                return finish(
                    (
                        [f"{binding.quarantine_relative}: {type(exc).__name__}: {exc}"],
                        [binding.quarantine_relative],
                    )
                )
            return finish(([], []))
        if identity_matches:
            failure = (
                f"{owned.relative_path}: link count {link_count} prevents rollback"
            )
        else:
            failure = f"{owned.relative_path}: owned content changed during rollback"
        return finish(
            _restore_bound_source(
                binding,
                owned.name,
                relative_path=owned.relative_path,
                rename=rename,
                failure=failure,
            )
        )
    except BaseException as exc:
        return finish(
            (
                [f"{owned.relative_path}: {type(exc).__name__}: {exc}"],
                [owned.relative_path],
            )
        )


def _rollback_temporary(
    temporary: OwnedTemporary,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
) -> _RollbackResult:
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
        expected_device=temporary.device,
        expected_inode=temporary.inode,
    )
    if binding is None:
        return failures, residuals
    prior_failures = failures
    prior_residuals = residuals

    def finish(result: _RollbackResult) -> _RollbackResult:
        return _finish_bound_source(
            binding,
            result,
            prior_failures=prior_failures,
            prior_residuals=prior_residuals,
        )

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
            expected_device=temporary.device,
            expected_inode=temporary.inode,
        )
        if not matches:
            return finish((failures, residuals))
        if not source_is_owned:
            return finish(
                _restore_bound_source(
                    binding,
                    temporary.name,
                    relative_path=temporary.relative_path,
                    rename=rename,
                )
            )
        try:
            os.unlink(
                binding.quarantine_name,
                dir_fd=binding.parent_descriptor,
            )
            os.fsync(binding.parent_descriptor)
        except BaseException as exc:
            return finish(
                (
                    [f"{binding.quarantine_relative}: {type(exc).__name__}: {exc}"],
                    [binding.quarantine_relative],
                )
            )
        return finish(([], []))
    except BaseException as exc:
        return finish(
            (
                [f"{temporary.relative_path}: {type(exc).__name__}: {exc}"],
                [temporary.relative_path],
            )
        )


def _rollback_directory(
    created: CreatedDirectory,
    *,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
) -> _RollbackResult:
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
        expected_device=created.device,
        expected_inode=created.inode,
    )
    if binding is None:
        return failures, residuals
    prior_failures = failures
    prior_residuals = residuals

    def finish(result: _RollbackResult) -> _RollbackResult:
        return _finish_bound_source(
            binding,
            result,
            prior_failures=prior_failures,
            prior_residuals=prior_residuals,
        )

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
            expected_device=created.device,
            expected_inode=created.inode,
        )
        if not matches:
            return finish((failures, residuals))
        if not source_is_owned:
            return finish(
                _restore_bound_source(
                    binding,
                    created.name,
                    relative_path=created.relative_path,
                    rename=rename,
                    failure=(
                        f"{created.relative_path}: "
                        "directory identity changed during rollback"
                    ),
                )
            )
        try:
            os.rmdir(
                binding.quarantine_name,
                dir_fd=binding.parent_descriptor,
            )
            os.fsync(binding.parent_descriptor)
        except BaseException as exc:
            return finish(
                (
                    [f"{binding.quarantine_relative}: {type(exc).__name__}: {exc}"],
                    [binding.quarantine_relative],
                )
            )
        return finish(([], []))
    except BaseException as exc:
        return finish(
            (
                [f"{created.relative_path}: {type(exc).__name__}: {exc}"],
                [created.relative_path],
            )
        )


def _collect_rollbacks(
    items: Iterable[_RollbackItemT],
    operation: Callable[[_RollbackItemT, int], _RollbackResult],
) -> _RollbackResult:
    failures: list[str] = []
    residuals: list[RollbackResidual] = []
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
) -> _RollbackResult:
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
    "UnlocatedOwnedIdentity",
    "descriptor_digest",
    "rename_no_replace",
    "render_rollback_residual",
    "rollback_publication",
)
