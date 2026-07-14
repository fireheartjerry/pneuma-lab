"""Canonical atomic writers for repository and build artifacts only."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import errno
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


_HASH_CHUNK_BYTES = 1024 * 1024
_UNSUPPORTED_FSYNC_ERRNOS = frozenset(
    value
    for value in (
        getattr(errno, "EINVAL", None),
        getattr(errno, "ENOSYS", None),
        getattr(errno, "ENOTSUP", None),
    )
    if value is not None
)


def sha256_file(path: Path) -> str:
    """Hash one repository/build artifact without loading it into memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_data(stream) -> None:
    try:
        os.fsync(stream.fileno())
    except OSError as exc:
        if exc.errno not in _UNSUPPORTED_FSYNC_ERRNOS:
            raise


def write_atomic_bytes(path: Path, payload: bytes) -> None:
    """Publish bytes with a unique same-directory temporary and ``os.replace``."""

    if not isinstance(payload, bytes):
        raise TypeError("atomic artifact payload must be bytes")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            _fsync_data(stream)
        os.replace(temporary, target)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _canonical_json_bytes(value: Any, *, indent: int | None) -> bytes:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=indent,
        separators=None if indent is not None else (",", ":"),
        sort_keys=True,
    )
    return (payload + "\n").encode("utf-8")


def write_atomic_json(path: Path, value: Any) -> None:
    """Write deterministic pretty JSON after complete serialization succeeds."""

    write_atomic_bytes(Path(path), _canonical_json_bytes(value, indent=4))


def write_atomic_jsonl(path: Path, records: Iterable[Mapping]) -> None:
    """Write compact deterministic JSONL without publishing partial output."""

    lines: list[bytes] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, Mapping):
            raise TypeError(f"JSONL record {index} must be a mapping")
        lines.append(_canonical_json_bytes(dict(record), indent=None))
    write_atomic_bytes(Path(path), b"".join(lines))


__all__ = [
    "sha256_file",
    "write_atomic_bytes",
    "write_atomic_json",
    "write_atomic_jsonl",
]
