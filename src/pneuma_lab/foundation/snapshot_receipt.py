"""Strict offline verification for Task 7-compatible pinned snapshots."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat as stat_module
from typing import Mapping

from pneuma_lab.foundation.artifacts import (
    ArtifactPublicationError,
    bind_artifact_publication,
    read_bound_artifact_set,
)
from pneuma_lab.foundation.specs import (
    MODEL_SPECS,
    PinnedConfigMismatch,
    validate_pinned_config,
)


_RECEIPT_NAME = "pneuma-snapshot-receipt.json"
_RECEIPT_KEYS = {
    "receipt_kind",
    "receipt_schema_version",
    "model_id",
    "revision",
    "files",
}
_FILE_KEYS = {"path", "size", "sha256"}
_TOKENIZER_ARTIFACT_NAMES = {
    "tokenizer.json",
    "tokenizer.model",
    "tokenizer.tiktoken",
    "vocab.json",
    "vocab.txt",
}
_HEX = frozenset("0123456789abcdef")


class SnapshotReceiptError(ValueError):
    """Raised when a local snapshot cannot prove its pinned provenance."""


@dataclass(frozen=True)
class SnapshotFile:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True)
class VerifiedPinnedSnapshot:
    model_key: str
    model_id: str
    revision: str
    snapshot_path: Path
    receipt_path: Path
    receipt_sha256: str
    snapshot_sha256: str
    files: tuple[SnapshotFile, ...]


def _strict_json(payload: bytes, *, label: str) -> dict:
    def reject_duplicates(pairs):
        value = {}
        for name, member in pairs:
            if name in value:
                raise SnapshotReceiptError(
                    f"{label} has duplicate JSON member: {name}"
                )
            value[name] = member
        return value

    def reject_constant(value: str):
        raise SnapshotReceiptError(
            f"{label} must not contain a non-finite JSON constant: {value}"
        )

    try:
        value = json.loads(
            payload,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except SnapshotReceiptError:
        raise
    except (json.JSONDecodeError, RecursionError, UnicodeError) as exc:
        raise SnapshotReceiptError(f"{label} must be strict JSON") from exc
    if not isinstance(value, dict):
        raise SnapshotReceiptError(f"{label} must be a JSON object")
    return value


def _is_link_or_reparse(path: Path) -> bool:
    metadata = path.lstat()
    if stat_module.S_ISLNK(metadata.st_mode):
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _validate_snapshot_root(snapshot_path: Path) -> Path:
    try:
        root = Path(snapshot_path)
    except (TypeError, ValueError) as exc:
        raise SnapshotReceiptError("snapshot path must be path-compatible") from exc
    if not root.is_absolute():
        raise SnapshotReceiptError("snapshot path must be absolute")
    try:
        for component in (root, *root.parents):
            if _is_link_or_reparse(component):
                raise SnapshotReceiptError(
                    "snapshot ancestry contains a link, junction, or reparse point"
                )
        metadata = root.lstat()
    except SnapshotReceiptError:
        raise
    except OSError as exc:
        raise SnapshotReceiptError("snapshot ancestry cannot be inspected") from exc
    if not stat_module.S_ISDIR(metadata.st_mode):
        raise SnapshotReceiptError("snapshot root must be a physical directory")
    return root


def _metadata_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
        getattr(metadata, "st_nlink", 1),
    )


def _inventory(root: Path) -> dict[str, tuple[int, ...]]:
    inventory = {}

    def walk_error(exc: OSError) -> None:
        raise SnapshotReceiptError("snapshot tree cannot be enumerated") from exc

    try:
        for directory, subdirectories, files in os.walk(
            root,
            followlinks=False,
            onerror=walk_error,
        ):
            directory_path = Path(directory)
            subdirectories.sort()
            files.sort()
            for name in subdirectories:
                member = directory_path / name
                if _is_link_or_reparse(member):
                    raise SnapshotReceiptError(
                        "snapshot contains a link, junction, or reparse member"
                    )
                if not stat_module.S_ISDIR(member.lstat().st_mode):
                    raise SnapshotReceiptError(
                        "snapshot contains a non-directory tree member"
                    )
            for name in files:
                member = directory_path / name
                if _is_link_or_reparse(member):
                    raise SnapshotReceiptError(
                        "snapshot contains a link, junction, or reparse member"
                    )
                metadata = member.lstat()
                if not stat_module.S_ISREG(metadata.st_mode):
                    raise SnapshotReceiptError(
                        "snapshot contains a non-regular file member"
                    )
                if getattr(metadata, "st_nlink", 1) != 1:
                    raise SnapshotReceiptError(
                        "snapshot contains a hard-link alias"
                    )
                relative = member.relative_to(root).as_posix()
                inventory[relative] = _metadata_signature(metadata)
    except SnapshotReceiptError:
        raise
    except OSError as exc:
        raise SnapshotReceiptError("snapshot metadata cannot be inspected") from exc
    return inventory


def _canonical_file(entry: object) -> SnapshotFile:
    if not isinstance(entry, Mapping) or set(entry) != _FILE_KEYS:
        raise SnapshotReceiptError(
            "snapshot receipt file entries require exact path, size, and sha256 fields"
        )
    raw_path = entry.get("path")
    size = entry.get("size")
    digest = entry.get("sha256")
    if not isinstance(raw_path, str) or not raw_path or "\\" in raw_path:
        raise SnapshotReceiptError("snapshot receipt file path is unsafe")
    path = PurePosixPath(raw_path)
    if (
        path.is_absolute()
        or raw_path != path.as_posix()
        or any(
            part in ("", ".", "..") or "\x00" in part or ":" in part
            for part in path.parts
        )
        or raw_path == _RECEIPT_NAME
    ):
        raise SnapshotReceiptError("snapshot receipt file path is unsafe")
    if type(size) is not int or size < 0:
        raise SnapshotReceiptError("snapshot receipt file size is invalid")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or set(digest) - _HEX
    ):
        raise SnapshotReceiptError("snapshot receipt file digest is invalid")
    return SnapshotFile(path=raw_path, size=size, sha256=digest)


def _canonical_receipt(receipt: Mapping, *, model_key: str) -> tuple[SnapshotFile, ...]:
    spec = MODEL_SPECS.get(model_key)
    if spec is None or not spec.download_allowed:
        raise SnapshotReceiptError("snapshot model key is not loadable")
    if set(receipt) != _RECEIPT_KEYS:
        raise SnapshotReceiptError("snapshot receipt fields do not match the schema")
    if receipt.get("receipt_kind") != "pneuma_pinned_model_snapshot":
        raise SnapshotReceiptError("snapshot receipt kind is invalid")
    if receipt.get("receipt_schema_version") != "0.1.0":
        raise SnapshotReceiptError("snapshot receipt schema version is invalid")
    if receipt.get("model_id") != spec.model_id:
        raise SnapshotReceiptError("snapshot receipt model does not match the pin")
    if receipt.get("revision") != spec.revision:
        raise SnapshotReceiptError("snapshot receipt revision does not match the pin")
    raw_files = receipt.get("files")
    if not isinstance(raw_files, list) or not raw_files:
        raise SnapshotReceiptError("snapshot receipt files must be a nonempty list")
    files = tuple(_canonical_file(entry) for entry in raw_files)
    paths = tuple(item.path for item in files)
    portable_paths = tuple(path.casefold() for path in paths)
    if (
        paths != tuple(sorted(paths))
        or len(paths) != len(set(paths))
        or len(portable_paths) != len(set(portable_paths))
    ):
        raise SnapshotReceiptError(
            "snapshot receipt file paths must be canonical, sorted, and unique"
        )
    if "config.json" not in paths:
        raise SnapshotReceiptError("snapshot receipt is missing config.json")
    if not any(PurePosixPath(path).name in _TOKENIZER_ARTIFACT_NAMES for path in paths):
        raise SnapshotReceiptError(
            "snapshot receipt is missing a tokenizer artifact"
        )
    return files


def _canonical_json_bytes(value: Mapping) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def verify_pinned_snapshot(
    model_key: str,
    *,
    snapshot_path: Path,
) -> VerifiedPinnedSnapshot:
    """Verify one complete pinned snapshot using local, no-follow reads only."""

    root = _validate_snapshot_root(snapshot_path)
    receipt_path = root / _RECEIPT_NAME
    try:
        receipt_reads = read_bound_artifact_set(
            (receipt_path,),
            directory=root,
            anchor_root=root,
            allowed_root=root,
        )
    except (ArtifactPublicationError, OSError) as exc:
        raise SnapshotReceiptError("snapshot receipt cannot be read safely") from exc
    if receipt_reads is None:
        raise SnapshotReceiptError("snapshot receipt is missing")
    receipt_read = receipt_reads[receipt_path]
    receipt = _strict_json(receipt_read.payload, label="snapshot receipt")
    files = _canonical_receipt(receipt, model_key=model_key)
    before = _inventory(root)
    expected_paths = {item.path for item in files} | {_RECEIPT_NAME}
    if set(before) != expected_paths:
        raise SnapshotReceiptError(
            "snapshot has missing or extra files relative to its receipt"
        )

    config_payload = None
    try:
        for item in files:
            path = root.joinpath(*PurePosixPath(item.path).parts)
            with bind_artifact_publication(
                path.parent,
                anchor_root=root,
                allowed_root=root,
            ) as publication:
                if item.path == "config.json":
                    reads = publication.read_bytes_set((path,))
                    assert reads is not None
                    read = reads[path]
                    digest, size = read.sha256, read.size
                    config_payload = read.payload
                else:
                    digest, size = publication.digest_size(path)
            if size != item.size or digest != item.sha256:
                raise SnapshotReceiptError(
                    f"snapshot file digest or size differs from receipt: {item.path}"
                )
    except SnapshotReceiptError:
        raise
    except (ArtifactPublicationError, OSError) as exc:
        raise SnapshotReceiptError("snapshot file cannot be hashed safely") from exc

    after = _inventory(root)
    if before != after:
        raise SnapshotReceiptError("snapshot file metadata changed during verification")
    assert config_payload is not None
    config = _strict_json(config_payload, label="pinned config.json")
    spec = MODEL_SPECS[model_key]
    try:
        validate_pinned_config(
            spec,
            config,
            source_revision=spec.revision,
        )
    except PinnedConfigMismatch as exc:
        raise SnapshotReceiptError(f"pinned config validation failed: {exc}") from exc
    snapshot_payload = {
        "model_id": spec.model_id,
        "revision": spec.revision,
        "files": [
            {"path": item.path, "size": item.size, "sha256": item.sha256}
            for item in files
        ],
    }
    return VerifiedPinnedSnapshot(
        model_key=model_key,
        model_id=spec.model_id,
        revision=spec.revision,
        snapshot_path=root,
        receipt_path=receipt_path,
        receipt_sha256=receipt_read.sha256,
        snapshot_sha256=hashlib.sha256(
            _canonical_json_bytes(snapshot_payload)
        ).hexdigest(),
        files=files,
    )


__all__ = [
    "SnapshotFile",
    "SnapshotReceiptError",
    "VerifiedPinnedSnapshot",
    "verify_pinned_snapshot",
]
