"""Filesystem-metadata-only presence reports for foundation data families."""

from __future__ import annotations

import os
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


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def probe_family_presence(data_root: Path, family: str) -> FamilyPresence:
    """Summarize one processed family using enumeration and stat metadata only."""

    if family not in ACTIVE_DATASET_GROUPS:
        raise ValueError(f"unknown active dataset family: {family!r}")
    root = Path(data_root) / "processed" / family
    exists = root.exists()
    count = 0
    byte_count = 0
    newest = None
    if exists and not root.is_symlink():
        resolved_root = root.resolve()
        for directory, subdirs, files in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            subdirs[:] = [
                name
                for name in subdirs
                if not (directory_path / name).is_symlink()
                and _is_within((directory_path / name).resolve(), resolved_root)
            ]
            for name in files:
                path = directory_path / name
                if path.is_symlink() or not _is_within(path.resolve(), resolved_root):
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


__all__ = ["FamilyPresence", "probe_family_presence"]
