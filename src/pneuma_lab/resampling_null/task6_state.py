"""Dedicated Task-6 controller lock and irreversible outcome-taint marker.

This is deliberately not the prefix-index publication transaction: Task 6 has
one small cross-destination namespace invariant of its own.
"""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Iterator

from .errors import RecordValidationError
from pneuma_lab.foundation.artifacts import canonical_json_bytes


_LOCK = ".pneuma-task6-controller.lock"
_TAINT = "operational/task6/outcome-tainted.json"
_PAIR_TRANSACTION = "operational/task6/paired-publication.json"
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
        # A process can die between the two paired writes.  Every later Task-6
        # controller entry resolves that durable intent before it can observe
        # or add to a half-published scientific graph.
        recover_paired_publication(root)
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


def _pair_transaction_path(root: Path) -> Path:
    return root / _PAIR_TRANSACTION


def _fsync_parent(path: Path) -> None:
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _unlink_fsynced(path: Path) -> None:
    path.unlink()
    _fsync_parent(path)


def begin_paired_publication(root: Path, entries: tuple[tuple[Path, bytes], ...]) -> None:
    """Durably record a no-clear pair intent before the first public write."""
    if len(entries) != 2 or entries[0][0] == entries[1][0]:
        raise RecordValidationError("paired publication requires two distinct targets")
    transaction = _pair_transaction_path(root)
    if transaction.exists():
        raise RecordValidationError("unfinished paired publication requires recovery")
    encoded_entries = []
    for target, payload in entries:
        if target.exists():
            raise FileExistsError(target)
        try:
            relative = target.relative_to(root).as_posix()
        except ValueError as exc:
            raise RecordValidationError("paired publication target escapes run root") from exc
        encoded_entries.append({
            "relative_path": relative,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "byte_count": len(payload),
        })
    transaction.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        transaction, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600,
    )
    try:
        payload = canonical_json_bytes({"state": "prepared_v1", "entries": encoded_entries}, indent=None)
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                raise OSError("paired publication transaction write failed")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_parent(transaction)


def recover_paired_publication(root: Path) -> None:
    """Finish a completed pair or erase an interrupted partial pair fail-closed."""
    transaction = _pair_transaction_path(root)
    if not transaction.exists():
        return
    try:
        value = json.loads(transaction.read_text(encoding="utf-8"))
        entries = value["entries"] if value.get("state") == "prepared_v1" else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError, KeyError, TypeError) as exc:
        raise RecordValidationError("paired publication transaction is malformed") from exc
    if not isinstance(entries, list) or len(entries) != 2:
        raise RecordValidationError("paired publication transaction is malformed")
    matched: list[Path] = []
    absent = 0
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"relative_path", "sha256", "byte_count"}:
            raise RecordValidationError("paired publication transaction is malformed")
        relative = entry["relative_path"]
        digest = entry["sha256"]
        size = entry["byte_count"]
        if not isinstance(relative, str) or not isinstance(digest, str) or type(size) is not int:
            raise RecordValidationError("paired publication transaction is malformed")
        try:
            target = (root / relative).resolve(strict=False)
            target.relative_to(root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise RecordValidationError("paired publication target escapes run root") from exc
        try:
            payload = target.read_bytes()
        except FileNotFoundError:
            absent += 1
            continue
        except OSError as exc:
            raise RecordValidationError("paired publication target cannot be read") from exc
        if len(payload) != size or hashlib.sha256(payload).hexdigest() != digest:
            raise RecordValidationError("paired publication target differs from transaction")
        matched.append(target)
    if len(matched) == 2:
        _unlink_fsynced(transaction)
        return
    for target in matched:
        _unlink_fsynced(target)
    _unlink_fsynced(transaction)


def abort_paired_publication(root: Path) -> None:
    """Recover synchronously after a controlled publication exception."""
    recover_paired_publication(root)
