"""Strict ArtifactRef decoding and descriptor-confined authority reads."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import NoReturn, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .errors import RecordValidationError
from .types import ArtifactRef


ARTIFACT_REF_FIELDS = (
    "role",
    "relative_path",
    "sha256",
    "byte_count",
    "media_type",
)
_ARTIFACT_REF_FIELD_SET = frozenset(ARTIFACT_REF_FIELDS)
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
_HASH_CHUNK_BYTES = 1024 * 1024


def _raise_after_descriptor_cleanup(
    *,
    descriptor: int,
    primary_error: BaseException,
    message: str,
) -> NoReturn:
    """Close one relinquished descriptor without losing its primary failure."""

    try:
        os.close(descriptor)
    except BaseException as cleanup_error:
        raise BaseExceptionGroup(
            message,
            [primary_error, cleanup_error],
        ) from None
    raise primary_error


@dataclass(frozen=True, slots=True)
class BoundArtifactRead:
    """Bytes and physical identity proven by one continuously held descriptor."""

    payload: bytes
    sha256: str
    byte_count: int
    st_dev: int
    st_ino: int


def closed_mapping(
    value: object,
    *,
    fields: Collection[str],
    field: str,
) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != set(fields):
        raise RecordValidationError(f"{field} has an open or incomplete shape")
    return dict(value)


def exact_text(value: object, *, field: str) -> str:
    if type(value) is not str:
        raise RecordValidationError(f"{field} must be exact text")
    text = cast(str, value)
    if not text:
        raise RecordValidationError(f"{field} must be non-empty")
    return text


def exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise RecordValidationError(f"{field} must be an exact integer")
    integer = cast(int, value)
    if integer < 0:
        raise RecordValidationError(f"{field} must be non-negative")
    return integer


def decode_artifact_ref(
    value: object,
    *,
    field: str,
    expected_role: str | None = None,
) -> ArtifactRef:
    mapping = closed_mapping(
        value,
        fields=ARTIFACT_REF_FIELDS,
        field=field,
    )
    try:
        ref = ArtifactRef(
            role=cast(str, mapping["role"]),
            relative_path=cast(str, mapping["relative_path"]),
            sha256=cast(str, mapping["sha256"]),
            byte_count=cast(int, mapping["byte_count"]),
            media_type=cast(str, mapping["media_type"]),
        )
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is malformed: {exc}") from exc
    if expected_role is not None and ref.role != expected_role:
        raise RecordValidationError(f"{field} role must equal {expected_role!r}")
    return ref


def walk_artifact_refs(value: object) -> tuple[ArtifactRef, ...]:
    refs: list[ArtifactRef] = []

    def walk(candidate: object, *, field: str) -> None:
        if isinstance(candidate, Mapping):
            if set(candidate) == _ARTIFACT_REF_FIELD_SET:
                refs.append(decode_artifact_ref(candidate, field=field))
                return
            for key, nested in candidate.items():
                walk(nested, field=f"{field}.{key}")
        elif isinstance(candidate, list):
            for index, nested in enumerate(candidate):
                walk(nested, field=f"{field}[{index}]")

    walk(value, field="$")
    return tuple(refs)


def load_json_bytes(payload: bytes, *, source: Path) -> object:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise RecordValidationError(f"{source}: UTF-8 BOM is forbidden")

    def reject_constant(value: str) -> object:
        raise RecordValidationError(
            f"{source}: non-finite JSON constant is forbidden: {value}"
        )

    def reject_duplicate_pairs(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise RecordValidationError(f"{source}: duplicate JSON key: {key!r}")
            result[key] = value
        return result

    try:
        text = payload.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_pairs,
            parse_constant=reject_constant,
        )
    except RecordValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecordValidationError(f"{source}: invalid UTF-8 JSON: {exc}") from exc


class AuthorityRefReader:
    """One root-bound authority reader with a per-validation decode cache."""

    def __init__(self, run_root: Path) -> None:
        self.run_root = Path(run_root).resolve(strict=True)
        if not self.run_root.is_dir():
            raise NotADirectoryError(self.run_root)
        self._root_descriptor: int | None = None
        self._decoded: dict[ArtifactRef, object] = {}
        self._bound_reads: dict[ArtifactRef, BoundArtifactRead] = {}
        self._path_bindings: dict[str, ArtifactRef] = {}
        self._physical_bindings: dict[tuple[int, int], ArtifactRef] = {}
        self._semantic_proofs: set[ArtifactRef] = set()

    def __enter__(self) -> AuthorityRefReader:
        owned_descriptor: int | None = os.open(
            self.run_root,
            _DIRECTORY_FLAGS,
        )
        if owned_descriptor is None:
            raise AssertionError("authority root open produced no descriptor")
        try:
            bound = os.fstat(owned_descriptor)
            named = os.stat(self.run_root, follow_symlinks=False)
            if not stat.S_ISDIR(bound.st_mode) or (bound.st_dev, bound.st_ino) != (
                named.st_dev,
                named.st_ino,
            ):
                raise RecordValidationError(
                    "authority run_root identity changed during binding"
                )
        except BaseException as primary_error:
            descriptor_to_close = owned_descriptor
            owned_descriptor = None
            if descriptor_to_close is None:
                raise
            _raise_after_descriptor_cleanup(
                descriptor=descriptor_to_close,
                primary_error=primary_error,
                message="authority acquisition and cleanup both failed",
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
                    "authority traversal and cleanup both failed",
                    [exception, cleanup_error],
                ) from None
            raise

    def _require_root(self) -> int:
        if self._root_descriptor is None:
            raise RuntimeError("authority reader is not active")
        return self._root_descriptor

    def _parts(self, relative_path: str) -> tuple[str, ...]:
        path = PurePosixPath(relative_path)
        parts = path.parts
        if (
            path.is_absolute()
            or not parts
            or parts[0] != "sources"
            or any(part in ("", ".", "..") for part in parts)
            or path.as_posix() != relative_path
        ):
            raise RecordValidationError(
                "artifact_ref is outside the copied authority namespace: "
                f"{relative_path!r}"
            )
        return parts

    def read_bound(self, ref: ArtifactRef) -> BoundArtifactRead:
        """Read, hash, and bind ``ref`` to one stable held file descriptor."""

        parts = self._parts(ref.relative_path)
        bound_ref = self._path_bindings.get(ref.relative_path)
        if bound_ref is not None and bound_ref != ref:
            raise RecordValidationError(
                f"artifact_ref relative path alias: {ref.relative_path!r}"
            )
        self._path_bindings[ref.relative_path] = ref
        cached = self._bound_reads.get(ref)
        if cached is not None:
            return cached
        descriptors: list[int] = []
        file_descriptor: int | None = None
        parent = self._require_root()
        result: BoundArtifactRead | None = None
        primary_error: BaseException | None = None
        try:
            for component in parts[:-1]:
                child = os.open(
                    component,
                    _DIRECTORY_FLAGS,
                    dir_fd=parent,
                )
                descriptors.append(child)
                parent = child
            file_descriptor = os.open(
                parts[-1],
                _READ_FLAGS,
                dir_fd=parent,
            )
            before = os.fstat(file_descriptor)
            if not stat.S_ISREG(before.st_mode):
                raise RecordValidationError(
                    f"artifact_ref must identify a regular file: {ref.relative_path!r}"
                )
            digest = hashlib.sha256()
            chunks: list[bytes] = []
            size = 0
            while chunk := os.read(file_descriptor, _HASH_CHUNK_BYTES):
                chunks.append(chunk)
                digest.update(chunk)
                size += len(chunk)
            after = os.fstat(file_descriptor)
            named = os.stat(
                parts[-1],
                dir_fd=parent,
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
                    f"artifact_ref identity changed during read: {ref.relative_path!r}"
                )
            physical_ref = self._physical_bindings.get(identity)
            if physical_ref is not None and physical_ref != ref:
                raise RecordValidationError(
                    f"artifact_ref physical file alias: {ref.relative_path!r}"
                )
            payload = b"".join(chunks)
            result = BoundArtifactRead(
                payload=payload,
                sha256=digest.hexdigest(),
                byte_count=size,
                st_dev=before.st_dev,
                st_ino=before.st_ino,
            )
        except OSError as exc:
            primary_error = RecordValidationError(
                f"dangling artifact_ref {ref.relative_path!r}"
            )
            primary_error.__cause__ = exc
        except BaseException as exc:
            primary_error = exc
        cleanup_errors: list[BaseException] = []
        if file_descriptor is not None:
            descriptor = file_descriptor
            file_descriptor = None
            try:
                os.close(descriptor)
            except BaseException as exc:
                cleanup_errors.append(exc)
        while descriptors:
            descriptor = descriptors.pop()
            try:
                os.close(descriptor)
            except BaseException as exc:
                cleanup_errors.append(exc)
        if primary_error is not None and cleanup_errors:
            raise BaseExceptionGroup(
                "authority read and cleanup both failed",
                [primary_error, *cleanup_errors],
            ) from None
        if primary_error is not None:
            raise primary_error
        if cleanup_errors:
            if len(cleanup_errors) == 1:
                raise cleanup_errors[0]
            raise BaseExceptionGroup(
                "multiple authority cleanup operations failed",
                cleanup_errors,
            )
        if result is None:
            raise AssertionError("authority read produced no result")
        if result.sha256 != ref.sha256 or result.byte_count != ref.byte_count:
            raise RecordValidationError(
                f"artifact_ref bytes mismatch: {ref.relative_path!r}"
            )
        self._physical_bindings[(result.st_dev, result.st_ino)] = ref
        self._bound_reads[ref] = result
        return result

    def read_bytes(self, ref: ArtifactRef) -> bytes:
        return self.read_bound(ref).payload

    def mark_semantically_validated(self, ref: ArtifactRef) -> None:
        if ref not in self._decoded:
            raise RuntimeError("semantic proof requires a decoded JSON ref")
        self._semantic_proofs.add(ref)

    @property
    def semantically_validated_refs(self) -> frozenset[ArtifactRef]:
        return frozenset(self._semantic_proofs)

    @property
    def decoded_json_refs(self) -> frozenset[ArtifactRef]:
        return frozenset(self._decoded)

    def decode_json(
        self,
        ref: ArtifactRef,
        *,
        field: str,
        canonical: bool,
        expected_role: str,
    ) -> dict[str, object]:
        if ref.role != expected_role:
            raise RecordValidationError(f"{field} role must equal {expected_role!r}")
        if ref.media_type != "application/json":
            raise RecordValidationError(f"{field} must reference application/json")
        if ref not in self._decoded:
            payload = self.read_bytes(ref)
            value = load_json_bytes(
                payload,
                source=self.run_root / ref.relative_path,
            )
            if canonical and payload != canonical_json_bytes(value, indent=None):
                raise RecordValidationError(f"{field} must be compact canonical JSON")
            self._decoded[ref] = value
        value = self._decoded[ref]
        if not isinstance(value, Mapping):
            raise RecordValidationError(f"{field} must reference a JSON object")
        return dict(value)

    def verify_closure(
        self,
        ref: ArtifactRef,
        *,
        field: str,
        expected_role: str | None = None,
        visited: set[ArtifactRef] | None = None,
    ) -> object:
        if expected_role is not None and ref.role != expected_role:
            raise RecordValidationError(f"{field} role must equal {expected_role!r}")
        observed = visited if visited is not None else set()
        if ref in observed:
            return self._decoded.get(ref)
        observed.add(ref)
        payload = self.read_bytes(ref)
        if ref.media_type != "application/json":
            return None
        if ref not in self._decoded:
            value = load_json_bytes(
                payload,
                source=self.run_root / ref.relative_path,
            )
            if payload != canonical_json_bytes(value, indent=None):
                raise RecordValidationError(f"{field} must be compact canonical JSON")
            self._decoded[ref] = value
        value = self._decoded[ref]
        for index, nested_ref in enumerate(walk_artifact_refs(value)):
            self.verify_closure(
                nested_ref,
                field=f"{field} nested ref {index}",
                visited=observed,
            )
        return value
