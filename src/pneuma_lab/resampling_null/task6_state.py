"""Dedicated Task-6 controller lock and irreversible outcome-taint marker.

This is deliberately not the prefix-index publication transaction: Task 6 has
one small cross-destination namespace invariant of its own.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
from typing import Iterator

from .errors import RecordValidationError


_LOCK = ".pneuma-task6-controller.lock"
_TAINT = "operational/task6/outcome-tainted.json"
_SINGLETONS = frozenset({"resampling_blinded_projection", "resampling_unblind_receipt"})
_PROTECTED = frozenset({
    "resampling_analysis_freeze", "resampling_task_block",
    "resampling_blinded_projection",
})


def _root(run_root: Path) -> Path:
    root = Path(run_root).resolve(strict=True)
    if not root.is_dir():
        raise RecordValidationError("Task-6 run root must be a directory")
    return root


@contextmanager
def task6_controller_lock(run_root: Path) -> Iterator[Path]:
    """Serialize Task-6 commits across processes for this exact run root."""
    root = _root(run_root)
    fd = os.open(root / _LOCK, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield root
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _tainted(root: Path) -> bool:
    return (root / _TAINT).exists()


def require_preunblind_context(run_root: Path, action: str) -> None:
    """Reject protected production actions permanently after outcome exposure."""
    if action in _PROTECTED and _tainted(_root(run_root)):
        raise RecordValidationError(
            f"outcome-tainted Task-6 context cannot perform protected action {action}"
        )


def require_singleton_absent(root: Path, kind: str) -> None:
    if kind not in _SINGLETONS:
        return
    for candidate in root.rglob("*.json"):
        relative = candidate.relative_to(root)
        if relative.parts and relative.parts[0] in {"operational", "sources"}:
            continue
        try:
            raw = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(raw, dict) and raw.get("record_kind") == kind:
            raise RecordValidationError(f"{kind} is a run-wide singleton and already exists")


def mark_outcome_tainted(root: Path) -> None:
    """Create the one-way durable marker before parsing outcome-bearing ledger data."""
    target = root / _TAINT
    if target.exists():
        raise RecordValidationError("Task-6 run is already outcome-tainted")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = b'{"state":"outcome_tainted_v1"}\n'
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
