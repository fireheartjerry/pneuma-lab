"""Strict ArtifactRef decoding and descriptor-confined authority reads."""

from __future__ import annotations

from collections.abc import Collection, Mapping
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import cast

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
_DIRECTORY_FLAGS = (
    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
)
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
_HASH_CHUNK_BYTES = 1024 * 1024


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
        raise RecordValidationError(
            f"{field} role must equal {expected_role!r}"
        )
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
                raise RecordValidationError(
                    f"{source}: duplicate JSON key: {key!r}"
                )
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
        raise RecordValidationError(
            f"{source}: invalid UTF-8 JSON: {exc}"
        ) from exc


class AuthorityRefReader:
    """One root-bound authority reader with a per-validation decode cache."""

    def __init__(self, run_root: Path) -> None:
        self.run_root = Path(run_root).resolve(strict=True)
        if not self.run_root.is_dir():
            raise NotADirectoryError(self.run_root)
        self._root_descriptor: int | None = None
        self._decoded: dict[ArtifactRef, object] = {}
        self._payloads: dict[ArtifactRef, bytes] = {}
        self._path_bindings: dict[str, ArtifactRef] = {}
        self._physical_bindings: dict[tuple[int, int], ArtifactRef] = {}

    def __enter__(self) -> AuthorityRefReader:
        descriptor = os.open(self.run_root, _DIRECTORY_FLAGS)
        try:
            bound = os.fstat(descriptor)
            named = os.stat(self.run_root, follow_symlinks=False)
            if (
                not stat.S_ISDIR(bound.st_mode)
                or (bound.st_dev, bound.st_ino)
                != (named.st_dev, named.st_ino)
            ):
                raise RecordValidationError(
                    "authority run_root identity changed during binding"
                )
        except BaseException:
            os.close(descriptor)
            raise
        self._root_descriptor = descriptor
        return self

    def __exit__(self, *_exception: object) -> None:
        if self._root_descriptor is not None:
            os.close(self._root_descriptor)
            self._root_descriptor = None

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

    def read_bytes(self, ref: ArtifactRef) -> bytes:
        parts = self._parts(ref.relative_path)
        bound_ref = self._path_bindings.get(ref.relative_path)
        if bound_ref is not None and bound_ref != ref:
            raise RecordValidationError(
                f"artifact_ref relative path alias: {ref.relative_path!r}"
            )
        self._path_bindings[ref.relative_path] = ref
        cached = self._payloads.get(ref)
        if cached is not None:
            return cached
        descriptors: list[int] = []
        parent = self._require_root()
        try:
            for component in parts[:-1]:
                child = os.open(
                    component,
                    _DIRECTORY_FLAGS,
                    dir_fd=parent,
                )
                descriptors.append(child)
                parent = child
            descriptor = os.open(
                parts[-1],
                _READ_FLAGS,
                dir_fd=parent,
            )
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode):
                    raise RecordValidationError(
                        "artifact_ref must identify a regular file: "
                        f"{ref.relative_path!r}"
                    )
                physical_identity = (metadata.st_dev, metadata.st_ino)
                physical_ref = self._physical_bindings.get(physical_identity)
                if physical_ref is not None and physical_ref != ref:
                    raise RecordValidationError(
                        "artifact_ref physical file alias: "
                        f"{ref.relative_path!r}"
                    )
                self._physical_bindings[physical_identity] = ref
                digest = hashlib.sha256()
                chunks: list[bytes] = []
                size = 0
                while chunk := os.read(descriptor, _HASH_CHUNK_BYTES):
                    chunks.append(chunk)
                    digest.update(chunk)
                    size += len(chunk)
                named = os.stat(
                    parts[-1],
                    dir_fd=parent,
                    follow_symlinks=False,
                )
                if (metadata.st_dev, metadata.st_ino) != (
                    named.st_dev,
                    named.st_ino,
                ):
                    raise RecordValidationError(
                        "artifact_ref identity changed during read: "
                        f"{ref.relative_path!r}"
                    )
            finally:
                os.close(descriptor)
        except (FileNotFoundError, NotADirectoryError, OSError) as exc:
            if isinstance(exc, RecordValidationError):
                raise
            raise RecordValidationError(
                f"dangling artifact_ref {ref.relative_path!r}"
            ) from exc
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)
        payload = b"".join(chunks)
        if (
            digest.hexdigest() != ref.sha256
            or size != ref.byte_count
        ):
            raise RecordValidationError(
                f"artifact_ref bytes mismatch: {ref.relative_path!r}"
            )
        self._payloads[ref] = payload
        return payload

    def decode_json(
        self,
        ref: ArtifactRef,
        *,
        field: str,
        canonical: bool,
        expected_role: str,
    ) -> dict[str, object]:
        if ref.role != expected_role:
            raise RecordValidationError(
                f"{field} role must equal {expected_role!r}"
            )
        if ref.media_type != "application/json":
            raise RecordValidationError(
                f"{field} must reference application/json"
            )
        if ref not in self._decoded:
            payload = self.read_bytes(ref)
            value = load_json_bytes(
                payload,
                source=self.run_root / ref.relative_path,
            )
            if canonical and payload != canonical_json_bytes(value, indent=None):
                raise RecordValidationError(
                    f"{field} must be compact canonical JSON"
                )
            self._decoded[ref] = value
        value = self._decoded[ref]
        if not isinstance(value, Mapping):
            raise RecordValidationError(
                f"{field} must reference a JSON object"
            )
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
            raise RecordValidationError(
                f"{field} role must equal {expected_role!r}"
            )
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
                raise RecordValidationError(
                    f"{field} must be compact canonical JSON"
                )
            self._decoded[ref] = value
        value = self._decoded[ref]
        for index, nested_ref in enumerate(walk_artifact_refs(value)):
            self.verify_closure(
                nested_ref,
                field=f"{field} nested ref {index}",
                visited=observed,
            )
        return value
