"""Descriptor-held quarantine identity state machine."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import PurePosixPath
from typing import Protocol


_PATH_FLAGS = getattr(os, "O_PATH", 0) | os.O_NOFOLLOW | os.O_CLOEXEC


@dataclass(frozen=True, slots=True)
class UnlocatedOwnedIdentity:
    device: int
    inode: int
    logical_former_path: str


@dataclass(frozen=True, slots=True)
class DescriptorCloseResidual:
    descriptor: int
    purpose: str


RollbackResidual = str | UnlocatedOwnedIdentity | DescriptorCloseResidual
RollbackResult = tuple[list[str], list[RollbackResidual]]


@dataclass(frozen=True, slots=True)
class QuarantinedSource:
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


def render_rollback_residual(residual: RollbackResidual) -> str:
    if isinstance(residual, str):
        return f"residual path: {residual}"
    if isinstance(residual, DescriptorCloseResidual):
        return (
            "descriptor close state uncertain: "
            f"fd={residual.descriptor}, purpose={residual.purpose}"
        )
    return (
        "unlocated owned identity: "
        f"device={residual.device}, inode={residual.inode}, "
        f"logical former path={residual.logical_former_path}"
    )


def restore_quarantine(
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


def close_source(
    descriptor: int,
    *,
    purpose: str,
) -> RollbackResult:
    try:
        os.close(descriptor)
    except OSError as exc:
        return (
            [f"{purpose} close: {type(exc).__name__}: {exc}"],
            [
                DescriptorCloseResidual(
                    descriptor=descriptor,
                    purpose=purpose,
                )
            ],
        )
    return [], []


def _finish_unbound_source(
    result: RollbackResult,
    descriptor: int,
) -> RollbackResult:
    failures, residuals = result
    close_failures, close_residuals = close_source(
        descriptor,
        purpose="rollback source",
    )
    return (
        [*failures, *close_failures],
        [*residuals, *close_residuals],
    )


def _move_source_to_quarantine(
    *,
    parent: int,
    name: str,
    relative_path: str,
    source_descriptor: int,
    quarantine_name: str,
    quarantine_relative: str,
    rename: RenameNoReplace,
) -> tuple[os.stat_result | None, list[str], list[RollbackResidual]]:
    try:
        source_metadata = os.fstat(source_descriptor)
    except BaseException as exc:
        return (
            None,
            [
                f"{relative_path} source identity inspection: "
                f"{type(exc).__name__}: {exc}"
            ],
            [relative_path],
        )
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
    return source_metadata, [], []


def _rebind_expected_quarantine(
    *,
    parent: int,
    source_descriptor: int,
    quarantine_name: str,
    quarantine_relative: str,
    expected_identity: tuple[int, int],
) -> tuple[QuarantinedSource | None, list[str], list[RollbackResidual]]:
    try:
        rebound_descriptor = os.open(
            quarantine_name,
            _PATH_FLAGS,
            dir_fd=parent,
        )
    except BaseException as exc:
        return (
            None,
            [f"{quarantine_relative} identity rebind: {type(exc).__name__}: {exc}"],
            [quarantine_relative],
        )
    try:
        rebound = os.fstat(rebound_descriptor)
        if (rebound.st_dev, rebound.st_ino) != expected_identity:
            raise OSError("expected quarantine identity changed during rebind")
    except BaseException as exc:
        close_failures, close_residuals = close_source(
            rebound_descriptor,
            purpose="rollback rebound source",
        )
        return (
            None,
            [
                f"{quarantine_relative} identity rebind: {type(exc).__name__}: {exc}",
                *close_failures,
            ],
            [quarantine_relative, *close_residuals],
        )
    close_failures, close_residuals = close_source(
        source_descriptor,
        purpose="rollback superseded source",
    )
    return (
        QuarantinedSource(
            parent_descriptor=parent,
            source_descriptor=rebound_descriptor,
            source_metadata=rebound,
            quarantine_name=quarantine_name,
            quarantine_relative=quarantine_relative,
        ),
        close_failures,
        close_residuals,
    )


def _held_ownership_reachable(
    *,
    source_descriptor: int,
    relative_path: str,
) -> tuple[bool, list[str]]:
    try:
        held_after_move = os.fstat(source_descriptor)
    except BaseException as exc:
        return (
            True,
            [
                f"{relative_path}: ownership reachability inspection: "
                f"{type(exc).__name__}: {exc}"
            ],
        )
    ownership_reachable = getattr(held_after_move, "st_nlink", 1) > 0
    if ownership_reachable:
        return (
            True,
            [f"{relative_path}: ownership lost after quarantine move"],
        )
    return False, []


def _resolve_identity_mismatch(
    *,
    parent: int,
    name: str,
    relative_path: str,
    source_descriptor: int,
    source_metadata: os.stat_result,
    named: os.stat_result,
    quarantine_name: str,
    quarantine_relative: str,
    expected_device: int,
    expected_inode: int,
    rename: RenameNoReplace,
) -> tuple[QuarantinedSource | None, list[str], list[RollbackResidual]]:
    expected_identity = (expected_device, expected_inode)
    named_identity = (named.st_dev, named.st_ino)
    held_identity = (source_metadata.st_dev, source_metadata.st_ino)
    if named_identity == expected_identity:
        return _rebind_expected_quarantine(
            parent=parent,
            source_descriptor=source_descriptor,
            quarantine_name=quarantine_name,
            quarantine_relative=quarantine_relative,
            expected_identity=expected_identity,
        )
    ownership_reachable = False
    loss_failures: list[str] = []
    if held_identity == expected_identity:
        ownership_reachable, loss_failures = _held_ownership_reachable(
            source_descriptor=source_descriptor,
            relative_path=relative_path,
        )
    try:
        restore_quarantine(
            parent,
            quarantine_name,
            name,
            rename=rename,
        )
    except BaseException as exc:
        loss_failures.append(
            f"{quarantine_relative} restore: {type(exc).__name__}: {exc}"
        )
        residuals: list[RollbackResidual] = [quarantine_relative]
        if ownership_reachable:
            residuals.append(
                UnlocatedOwnedIdentity(
                    device=expected_device,
                    inode=expected_inode,
                    logical_former_path=relative_path,
                )
            )
        return None, loss_failures, residuals
    if ownership_reachable:
        return (
            None,
            loss_failures,
            [
                UnlocatedOwnedIdentity(
                    device=expected_device,
                    inode=expected_inode,
                    logical_former_path=relative_path,
                )
            ],
        )
    return None, [], []


def quarantine_source(
    *,
    parent_parts: tuple[str, ...],
    name: str,
    relative_path: str,
    index: int,
    descriptor_for: DescriptorResolver,
    quarantine_name_for: QuarantineName,
    rename: RenameNoReplace,
    expected_device: int,
    expected_inode: int,
) -> tuple[QuarantinedSource | None, list[str], list[RollbackResidual]]:
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
    source_metadata, failures, residuals = _move_source_to_quarantine(
        parent=parent,
        name=name,
        relative_path=relative_path,
        source_descriptor=source_descriptor,
        quarantine_name=quarantine_name,
        quarantine_relative=quarantine_relative,
        rename=rename,
    )
    if source_metadata is None:
        return (
            None,
            *_finish_unbound_source(
                (failures, residuals),
                source_descriptor,
            ),
        )
    try:
        named = os.stat(
            quarantine_name,
            dir_fd=parent,
            follow_symlinks=False,
        )
    except BaseException as exc:
        failures = [
            f"{quarantine_relative} identity inspection: {type(exc).__name__}: {exc}"
        ]
        try:
            restore_quarantine(
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
            return (
                None,
                *_finish_unbound_source(
                    (failures, [quarantine_relative]),
                    source_descriptor,
                ),
            )
        return (
            None,
            *_finish_unbound_source(
                (failures, [relative_path]),
                source_descriptor,
            ),
        )
    if (named.st_dev, named.st_ino) != (
        source_metadata.st_dev,
        source_metadata.st_ino,
    ):
        binding, failures, residuals = _resolve_identity_mismatch(
            parent=parent,
            name=name,
            relative_path=relative_path,
            source_descriptor=source_descriptor,
            source_metadata=source_metadata,
            named=named,
            quarantine_name=quarantine_name,
            quarantine_relative=quarantine_relative,
            expected_device=expected_device,
            expected_inode=expected_inode,
            rename=rename,
        )
        if binding is not None:
            return binding, failures, residuals
        return (
            None,
            *_finish_unbound_source(
                (failures, residuals),
                source_descriptor,
            ),
        )
    return (
        QuarantinedSource(
            parent_descriptor=parent,
            source_descriptor=source_descriptor,
            source_metadata=source_metadata,
            quarantine_name=quarantine_name,
            quarantine_relative=quarantine_relative,
        ),
        [],
        [],
    )


def restore_bound_source(
    binding: QuarantinedSource,
    destination_name: str,
    *,
    relative_path: str,
    rename: RenameNoReplace,
    failure: str | None = None,
    failure_residuals: list[RollbackResidual] | None = None,
) -> RollbackResult:
    failures = [] if failure is None else [failure]
    try:
        restore_quarantine(
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
    if failure_residuals is not None:
        return failures, failure_residuals
    return failures, [relative_path]


def binding_matches_named(
    binding: QuarantinedSource,
    metadata: os.stat_result,
) -> bool:
    return (metadata.st_dev, metadata.st_ino) == (
        binding.source_metadata.st_dev,
        binding.source_metadata.st_ino,
    )


def recheck_quarantine(
    binding: QuarantinedSource,
    destination_name: str,
    *,
    relative_path: str,
    rename: RenameNoReplace,
    expected_device: int,
    expected_inode: int,
) -> tuple[bool, list[str], list[RollbackResidual]]:
    try:
        named = os.stat(
            binding.quarantine_name,
            dir_fd=binding.parent_descriptor,
            follow_symlinks=False,
        )
    except BaseException as exc:
        failures, residuals = restore_bound_source(
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
    if not binding_matches_named(binding, named):
        binding_is_expected = (
            binding.source_metadata.st_dev,
            binding.source_metadata.st_ino,
        ) == (expected_device, expected_inode)
        failure_residuals: list[RollbackResidual] = []
        if binding_is_expected:
            failure_residuals.append(
                UnlocatedOwnedIdentity(
                    device=expected_device,
                    inode=expected_inode,
                    logical_former_path=relative_path,
                )
            )
        failures, residuals = restore_bound_source(
            binding,
            destination_name,
            relative_path=relative_path,
            rename=rename,
            failure=f"{relative_path}: ownership lost after quarantine move",
            failure_residuals=failure_residuals,
        )
        return False, failures, residuals
    return True, [], []


__all__ = (
    "DescriptorCloseResidual",
    "QuarantinedSource",
    "RollbackResidual",
    "RollbackResult",
    "UnlocatedOwnedIdentity",
    "binding_matches_named",
    "close_source",
    "quarantine_source",
    "recheck_quarantine",
    "render_rollback_residual",
    "restore_bound_source",
)
