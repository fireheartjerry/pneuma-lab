"""Filesystem-metadata-only presence reports for foundation data families."""

from __future__ import annotations

import os
import stat as stat_module
from dataclasses import dataclass
from pathlib import Path

from pneuma_lab.foundation.data import ACTIVE_DATASET_GROUPS


@dataclass(frozen=True)
class FamilyPresence:
    family: str
    exists: bool
    file_count: int
    byte_count: int
    newest_mtime_ns: int | None
    inspection: str = "filesystem_metadata_only"
    payload_opened: bool = False


class SourcePresenceError(ValueError):
    """Raised when a presence probe cannot establish a safe trust boundary."""


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        metadata = path.lstat()
    except OSError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(
        stat_module,
        "FILE_ATTRIBUTE_REPARSE_POINT",
        0x400,
    )
    return bool(attributes & reparse_flag)


def _establish_trust_boundary(data_root: Path, family_root: Path) -> Path:
    processed_root = data_root / "processed"
    for component in (data_root, processed_root, family_root):
        if _is_link_or_reparse(component):
            raise SourcePresenceError(
                f"filesystem trust boundary contains a link or reparse point: {component}"
            )
    try:
        resolved_data_root = data_root.resolve(strict=False)
        resolved_processed_root = processed_root.resolve(strict=False)
        resolved_family_root = family_root.resolve(strict=False)
    except OSError as exc:
        raise SourcePresenceError(
            f"filesystem trust boundary cannot be resolved: {exc}"
        ) from exc
    if (
        not _is_within(resolved_processed_root, resolved_data_root)
        or not _is_within(resolved_family_root, resolved_processed_root)
        or not _is_within(resolved_family_root, resolved_data_root)
    ):
        raise SourcePresenceError(
            "filesystem trust boundary resolves outside the supplied data root"
        )
    return resolved_family_root


def probe_family_presence(data_root: Path, family: str) -> FamilyPresence:
    """Summarize one processed family using enumeration and stat metadata only."""

    if family not in ACTIVE_DATASET_GROUPS:
        raise ValueError(f"unknown active dataset family: {family!r}")
    try:
        data_root = Path(data_root)
    except TypeError as exc:
        raise SourcePresenceError("data root must be path-compatible") from exc
    root = data_root / "processed" / family
    resolved_root = _establish_trust_boundary(data_root, root)
    exists = root.exists()
    count = 0
    byte_count = 0
    newest = None
    if exists:
        for directory, subdirs, files in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            subdirs[:] = [
                name
                for name in subdirs
                if not _is_link_or_reparse(directory_path / name)
                and _is_within(
                    (directory_path / name).resolve(strict=False),
                    resolved_root,
                )
            ]
            for name in files:
                path = directory_path / name
                if _is_link_or_reparse(path) or not _is_within(
                    path.resolve(strict=False),
                    resolved_root,
                ):
                    continue
                stat = path.stat()
                count += 1
                byte_count += stat.st_size
                newest = (
                    stat.st_mtime_ns
                    if newest is None
                    else max(newest, stat.st_mtime_ns)
                )
    return FamilyPresence(family, exists, count, byte_count, newest)


__all__ = ["FamilyPresence", "SourcePresenceError", "probe_family_presence"]
