"""Private secret-file custody for resampling-null assignment."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import sys
from typing import Literal

from .types import ArtifactRef


_HANDLE_MINT = object()


class AssignmentSecretHandle:
    """Opaque assignment-purpose handle minted by one concrete store."""

    __slots__ = ("_store",)

    def __init__(
        self,
        mint: object,
        store: AssignmentSecretStore | None = None,
    ) -> None:
        if mint is not _HANDLE_MINT or type(store) is not AssignmentSecretStore:
            raise TypeError("assignment secret handles require private store minting")
        assert store is not None
        self._store = store

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("assignment secret handle is final and nominal")

    def __copy__(self) -> AssignmentSecretHandle:
        raise TypeError("assignment secret handle cannot be copied")

    def __deepcopy__(self, memo: object) -> AssignmentSecretHandle:
        raise TypeError("assignment secret handle cannot be copied")


class UnblindSecretHandle:
    """Opaque unblind-purpose handle minted by one concrete store."""

    __slots__ = ("_store",)

    def __init__(
        self,
        mint: object,
        store: AssignmentSecretStore | None = None,
    ) -> None:
        if mint is not _HANDLE_MINT or type(store) is not AssignmentSecretStore:
            raise TypeError("unblind secret handles require private store minting")
        assert store is not None
        self._store = store

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("unblind secret handle is final and nominal")

    def __copy__(self) -> UnblindSecretHandle:
        raise TypeError("unblind secret handle cannot be copied")

    def __deepcopy__(self, memo: object) -> UnblindSecretHandle:
        raise TypeError("unblind secret handle cannot be copied")


_SecretHandle = AssignmentSecretHandle | UnblindSecretHandle


@dataclass(frozen=True, slots=True)
class _SecretEntry:
    descriptor: int
    identity: tuple[int, int, int, int, int]
    manifest_ref: ArtifactRef
    schedule_ref: ArtifactRef
    run_root: Path
    purpose: Literal["assignment", "unblind"]


def _resolve_absolute_path(path: object, *, field: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError(f"{field} must be an absolute path")
    try:
        return path.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError(f"{field} cannot be resolved") from exc


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _metadata_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_nlink,
    )


class AssignmentSecretStore:
    """Concrete trusted-controller store for one configured secret path."""

    __slots__ = ("_closed", "_registry", "_secret_path")

    def __init__(self, secret_path: Path) -> None:
        self._secret_path = secret_path
        self._registry: dict[_SecretHandle, _SecretEntry] = {}
        self._closed = False

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("assignment secret store is final and concrete")

    def _claim(
        self,
        handle_type: type[AssignmentSecretHandle] | type[UnblindSecretHandle],
        manifest_ref: ArtifactRef,
        schedule_ref: ArtifactRef,
        run_root: Path,
        purpose: Literal["assignment", "unblind"],
    ) -> _SecretHandle:
        if self._closed:
            raise ValueError("assignment secret store is closed")
        if (
            type(manifest_ref) is not ArtifactRef
            or type(schedule_ref) is not ArtifactRef
        ):
            raise TypeError("secret claims require exact ArtifactRef bindings")
        resolved_run_root = _resolve_absolute_path(run_root, field="run root")
        if not resolved_run_root.is_dir():
            raise ValueError("run root must identify a directory")
        resolved_secret = _resolve_absolute_path(
            self._secret_path,
            field="secret path",
        )
        if _is_within(resolved_secret, resolved_run_root):
            raise ValueError("secret path must remain outside the run root")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        try:
            descriptor = os.open(self._secret_path, flags)
        except OSError as exc:
            raise ValueError("secret file could not be opened securely") from exc
        try:
            metadata = os.fstat(descriptor)
            permissions = stat.S_IMODE(metadata.st_mode)
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("secret descriptor must identify a regular file")
            if getattr(metadata, "st_nlink", 1) != 1:
                raise ValueError("secret file must not have hard-link aliases")
            if metadata.st_uid != os.geteuid():
                raise ValueError("secret file must be owned by the effective user")
            if not permissions & 0o400 or permissions & 0o177:
                raise ValueError("secret file permissions must be owner-readable only")
            if not sys.platform.startswith("linux"):
                raise RuntimeError("secret descriptor identity requires Linux")
            final_path = Path(os.readlink(f"/proc/self/fd/{descriptor}")).resolve(
                strict=True
            )
            if final_path != resolved_secret:
                raise ValueError(
                    "secret descriptor final path differs from configuration"
                )
            if _is_within(final_path, resolved_run_root):
                raise ValueError("secret descriptor must remain outside the run root")
        except BaseException:
            os.close(descriptor)
            raise
        handle = handle_type(_HANDLE_MINT, self)
        self._registry[handle] = _SecretEntry(
            descriptor=descriptor,
            identity=_metadata_identity(metadata),
            manifest_ref=manifest_ref,
            schedule_ref=schedule_ref,
            run_root=resolved_run_root,
            purpose=purpose,
        )
        return handle

    def claim_assignment(
        self,
        manifest_ref: ArtifactRef,
        schedule_ref: ArtifactRef,
        *,
        run_root: Path,
    ) -> AssignmentSecretHandle:
        handle = self._claim(
            AssignmentSecretHandle,
            manifest_ref,
            schedule_ref,
            run_root,
            "assignment",
        )
        assert type(handle) is AssignmentSecretHandle
        return handle

    def claim_unblind(
        self,
        manifest_ref: ArtifactRef,
        schedule_ref: ArtifactRef,
        *,
        run_root: Path,
    ) -> UnblindSecretHandle:
        handle = self._claim(
            UnblindSecretHandle,
            manifest_ref,
            schedule_ref,
            run_root,
            "unblind",
        )
        assert type(handle) is UnblindSecretHandle
        return handle

    def _consume_into(
        self,
        handle: _SecretHandle,
        destination: bytearray,
    ) -> None:
        if handle not in self._registry:
            raise ValueError(
                "assignment secret handle is not registered or is consumed"
            )
        entry = self._registry.pop(handle)
        descriptor = entry.descriptor
        try:
            if (type(handle) is AssignmentSecretHandle) != (
                entry.purpose == "assignment"
            ) or _metadata_identity(os.fstat(descriptor)) != entry.identity:
                raise ValueError("secret descriptor identity or purpose changed")
        except BaseException:
            os.close(descriptor)
            raise
        overread = bytearray(1)
        try:
            with os.fdopen(descriptor, "rb", buffering=0, closefd=True) as stream:
                if stream.readinto(destination) != 32:
                    raise ValueError(
                        "assignment master key must contain exactly 32 bytes"
                    )
                if stream.readinto(overread) != 0:
                    raise ValueError(
                        "assignment master key must contain exactly 32 bytes"
                    )
        finally:
            for index in range(len(overread)):
                overread[index] = 0

    def close(self) -> None:
        for entry in self._registry.values():
            os.close(entry.descriptor)
        self._registry.clear()
        self._closed = True


def _require_handle_binding(
    handle: _SecretHandle,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    *,
    run_root: Path,
    purpose: Literal["assignment", "unblind"],
) -> None:
    if type(handle) not in (AssignmentSecretHandle, UnblindSecretHandle):
        raise TypeError("secret handle must be one exact nominal handle")
    store = handle._store
    entry = store._registry.get(handle)
    if entry is None:
        raise ValueError("secret handle is not registered or is consumed")
    try:
        resolved_run_root = _resolve_absolute_path(run_root, field="run root")
    except BaseException:
        store._registry.pop(handle)
        os.close(entry.descriptor)
        raise
    expected_type = (
        AssignmentSecretHandle if purpose == "assignment" else UnblindSecretHandle
    )
    if (
        type(handle) is not expected_type
        or entry.purpose != purpose
        or entry.manifest_ref != manifest_ref
        or entry.schedule_ref != schedule_ref
        or entry.run_root != resolved_run_root
    ):
        store._registry.pop(handle)
        os.close(entry.descriptor)
        raise ValueError("secret handle binding context or purpose does not match")


def _consume_assignment_handle_into(
    handle: _SecretHandle,
    destination: bytearray,
) -> None:
    handle._store._consume_into(handle, destination)
