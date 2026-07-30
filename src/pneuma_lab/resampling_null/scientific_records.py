"""Public loading boundary for digest-bound scientific records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
from types import MappingProxyType
from typing import cast

from .artifacts import validate_record
from .authority_refs import (
    BoundArtifactRead,
    _raise_after_descriptor_cleanup,
    decode_artifact_ref,
    load_json_bytes,
)
from .errors import RecordValidationError
from .prefix_contracts import SCIENTIFIC_PARENT_KIND
from .types import ArtifactRef


_SCIENTIFIC_PATH_BY_ROLE: Mapping[str, str] = MappingProxyType(
    {
        "resampling_prefix_schedule": "prefix-schedule.json",
        "study_manifest": "study-manifest.json",
    }
)

if set(_SCIENTIFIC_PATH_BY_ROLE) != set(SCIENTIFIC_PARENT_KIND):
    raise RuntimeError("scientific role/path registry coverage drifted")


@dataclass(frozen=True, slots=True)
class ScientificRecord:
    path: Path
    relative_path: str
    value: dict[str, object]
    sha256: str
    byte_count: int


class ScientificRefReader:
    """Root-bound reader for the two direct scientific-parent files."""

    def __init__(self, run_root: Path) -> None:
        self.run_root = Path(run_root).resolve(strict=True)
        self._root_descriptor: int | None = None
        self._bound_reads: dict[ArtifactRef, BoundArtifactRead] = {}
        self._physical_bindings: dict[tuple[int, int], ArtifactRef] = {}

    def __enter__(self) -> ScientificRefReader:
        owned_descriptor: int | None = os.open(
            self.run_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        if owned_descriptor is None:
            raise AssertionError("scientific root open produced no descriptor")
        try:
            before = os.fstat(owned_descriptor)
            named = os.stat(self.run_root, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode) or (before.st_dev, before.st_ino) != (
                named.st_dev,
                named.st_ino,
            ):
                raise RecordValidationError(
                    "scientific run_root identity changed during binding"
                )
        except BaseException as primary_error:
            descriptor_to_close = owned_descriptor
            owned_descriptor = None
            if descriptor_to_close is None:
                raise
            _raise_after_descriptor_cleanup(
                descriptor=descriptor_to_close,
                primary_error=primary_error,
                message="scientific acquisition and cleanup both failed",
            )
        self._root_descriptor = owned_descriptor
        owned_descriptor = None
        return self

    def __exit__(
        self,
        _exception_type: object,
        exception: BaseException | None,
        _traceback: object,
    ) -> None:
        descriptor = self._root_descriptor
        self._root_descriptor = None
        if descriptor is None:
            return
        try:
            os.close(descriptor)
        except BaseException as cleanup_error:
            if exception is not None:
                raise BaseExceptionGroup(
                    "scientific traversal and cleanup both failed",
                    [exception, cleanup_error],
                ) from None
            raise

    def read_bound(self, ref: ArtifactRef) -> BoundArtifactRead:
        cached = self._bound_reads.get(ref)
        if cached is not None:
            return cached
        expected_path = _SCIENTIFIC_PATH_BY_ROLE.get(ref.role)
        if expected_path is None:
            raise RecordValidationError("scientific role is not registered")
        if expected_path != ref.relative_path:
            raise RecordValidationError("scientific path is not registered")
        if ref.media_type != "application/json":
            raise RecordValidationError(
                "scientific parent must reference application/json"
            )
        root_descriptor = self._root_descriptor
        if root_descriptor is None:
            raise RuntimeError("scientific reader is not active")
        descriptor: int | None = None
        result: BoundArtifactRead | None = None
        primary_error: BaseException | None = None
        try:
            descriptor = os.open(
                ref.relative_path,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=root_descriptor,
            )
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise RecordValidationError("scientific parent must be a regular file")
            digest = hashlib.sha256()
            chunks: list[bytes] = []
            size = 0
            while chunk := os.read(descriptor, 1024 * 1024):
                chunks.append(chunk)
                digest.update(chunk)
                size += len(chunk)
            after = os.fstat(descriptor)
            named = os.stat(
                ref.relative_path,
                dir_fd=root_descriptor,
                follow_symlinks=False,
            )
            identity = (before.st_dev, before.st_ino)
            if (
                identity != (after.st_dev, after.st_ino)
                or identity != (named.st_dev, named.st_ino)
                or not stat.S_ISREG(after.st_mode)
                or not stat.S_ISREG(named.st_mode)
            ):
                raise RecordValidationError(
                    "scientific parent identity changed during read"
                )
            previous = self._physical_bindings.get(identity)
            if previous is not None and previous != ref:
                raise RecordValidationError(
                    "scientific parent physical file is aliased"
                )
            result = BoundArtifactRead(
                payload=b"".join(chunks),
                sha256=digest.hexdigest(),
                byte_count=size,
                st_dev=before.st_dev,
                st_ino=before.st_ino,
            )
        except RecordValidationError as exc:
            primary_error = exc
        except OSError as exc:
            primary_error = RecordValidationError(
                "scientific parent could not be safely resolved"
            )
            primary_error.__cause__ = exc
        cleanup_errors: list[BaseException] = []
        if descriptor is not None:
            owned_descriptor = descriptor
            descriptor = None
            try:
                os.close(owned_descriptor)
            except BaseException as exc:
                cleanup_errors.append(exc)
        if primary_error is not None and cleanup_errors:
            raise BaseExceptionGroup(
                "scientific read and cleanup both failed",
                [primary_error, *cleanup_errors],
            ) from None
        if primary_error is not None:
            raise primary_error
        if cleanup_errors:
            raise cleanup_errors[0]
        if result is None:
            raise AssertionError("scientific read produced no result")
        if result.sha256 != ref.sha256 or result.byte_count != ref.byte_count:
            raise RecordValidationError(
                "scientific parent digest or length does not match"
            )
        self._physical_bindings[(result.st_dev, result.st_ino)] = ref
        self._bound_reads[ref] = result
        return result


def decode_scientific_parent(
    ref: ArtifactRef,
    bound: BoundArtifactRead,
    *,
    run_root: Path,
    field: str,
    expected_kind: str,
    expected_stage: str | None = None,
) -> ScientificRecord:
    """Validate one scientific parent from already identity-bound bytes."""

    value: object = ref
    if type(ref) is not ArtifactRef:
        raise TypeError("ref must be an exact ArtifactRef")
    if type(bound) is not BoundArtifactRead:
        raise TypeError("bound must be an exact BoundArtifactRead")
    return _decode_scientific_parent(
        value,
        raw=bound.payload,
        run_root=run_root,
        field=field,
        expected_kind=expected_kind,
        expected_stage=expected_stage,
    )


def _decode_scientific_parent(
    value: object,
    *,
    raw: bytes,
    run_root: Path,
    field: str,
    expected_kind: str,
    expected_stage: str | None = None,
) -> ScientificRecord:
    """Load and validate one direct scientific parent by exact ArtifactRef."""

    ref = (
        cast(ArtifactRef, value)
        if type(value) is ArtifactRef
        else decode_artifact_ref(value, field=field)
    )
    expected_roles = tuple(
        role
        for role, record_kind in SCIENTIFIC_PARENT_KIND.items()
        if record_kind == expected_kind
    )
    if len(expected_roles) != 1:
        raise RecordValidationError(
            f"{field} has no unique registered scientific role for {expected_kind}"
        )
    expected_role = expected_roles[0]
    if ref.role != expected_role:
        raise RecordValidationError(f"{field} scientific role must be {expected_role}")
    if ref.media_type != "application/json":
        raise RecordValidationError(f"{field} must reference application/json")
    expected_path = _SCIENTIFIC_PATH_BY_ROLE[expected_role]
    if ref.relative_path != expected_path:
        raise RecordValidationError(f"{field} scientific path must be {expected_path}")
    root = Path(run_root).resolve(strict=True)
    path = root / ref.relative_path
    decoded = load_json_bytes(raw, source=path)
    if not isinstance(decoded, Mapping):
        raise RecordValidationError(f"{field} must reference a JSON object")
    validated = validate_record(cast(Mapping[str, object], decoded))
    if validated["record_kind"] != expected_kind:
        raise RecordValidationError(
            f"{field} must reference {expected_kind}, got {validated['record_kind']}"
        )
    payload = cast(Mapping[str, object], validated["payload"])
    if expected_stage is not None and payload.get("stage") != expected_stage:
        raise RecordValidationError(
            f"{field} must reference {expected_kind} stage {expected_stage!r}"
        )
    return ScientificRecord(
        path=path,
        relative_path=ref.relative_path,
        value=validated,
        sha256=ref.sha256,
        byte_count=ref.byte_count,
    )


def load_scientific_parent(
    value: object,
    *,
    run_root: Path,
    field: str,
    expected_kind: str,
    expected_stage: str | None = None,
) -> ScientificRecord:
    """Load and validate one direct scientific parent by exact ArtifactRef."""

    ref = decode_artifact_ref(value, field=field)
    root = Path(run_root).resolve(strict=True)
    with ScientificRefReader(root) as reader:
        bound = reader.read_bound(ref)
    return decode_scientific_parent(
        ref,
        bound,
        run_root=root,
        field=field,
        expected_kind=expected_kind,
        expected_stage=expected_stage,
    )


__all__ = (
    "ScientificRecord",
    "ScientificRefReader",
    "decode_scientific_parent",
    "load_scientific_parent",
)
