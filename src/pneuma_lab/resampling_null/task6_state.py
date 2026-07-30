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
import secrets
import stat
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


def _write_all(descriptor: int, payload: bytes) -> None:
    written = 0
    while written < len(payload):
        count = os.write(descriptor, payload[written:])
        if count <= 0:
            raise OSError("paired publication write failed")
        written += count


def _write_transaction(root: Path, value: dict[str, object]) -> None:
    transaction = _pair_transaction_path(root)
    payload = canonical_json_bytes(value, indent=None)
    temporary = transaction.parent / f".{transaction.name}.{secrets.token_hex(16)}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        os.replace(temporary, transaction)
        _fsync_parent(transaction)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _inside(root: Path, relative: str, *, field: str) -> Path:
    if not relative or "\\" in relative:
        raise RecordValidationError(f"paired publication {field} is malformed")
    try:
        target = (root / relative).resolve(strict=False)
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RecordValidationError(f"paired publication {field} escapes run root") from exc
    return target


def _load_transaction(root: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    transaction = _pair_transaction_path(root)
    try:
        value = json.loads(transaction.read_text(encoding="utf-8"))
        entries = value["entries"] if value.get("state") == "prepared_v2" else None
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError, KeyError, TypeError) as exc:
        raise RecordValidationError("paired publication transaction is malformed") from exc
    if not isinstance(value, dict) or not isinstance(entries, list) or len(entries) != 2:
        raise RecordValidationError("paired publication transaction is malformed")
    for entry in entries:
        required = {"relative_path", "sha256", "byte_count", "temporary_relative_path", "temporary_identity"}
        if not isinstance(entry, dict) or set(entry) != required:
            raise RecordValidationError("paired publication transaction is malformed")
        relative, digest, size = entry["relative_path"], entry["sha256"], entry["byte_count"]
        temporary, identity = entry["temporary_relative_path"], entry["temporary_identity"]
        if not isinstance(relative, str) or not isinstance(digest, str) or type(size) is not int or size < 0 or not isinstance(temporary, str):
            raise RecordValidationError("paired publication transaction is malformed")
        target = _inside(root, relative, field="target")
        temp = _inside(root, temporary, field="temporary target")
        if target.parent != temp.parent or temp.name == target.name:
            raise RecordValidationError("paired publication temporary target is malformed")
        if identity is not None and (not isinstance(identity, dict) or set(identity) != {"device", "inode"} or type(identity["device"]) is not int or type(identity["inode"]) is not int):
            raise RecordValidationError("paired publication transaction is malformed")
    return value, entries


def begin_paired_publication(root: Path, entries: tuple[tuple[Path, bytes], ...]) -> None:
    """Durably name private, no-replace staging files before public install."""
    if len(entries) != 2 or entries[0][0] == entries[1][0]:
        raise RecordValidationError("paired publication requires two distinct targets")
    transaction = _pair_transaction_path(root)
    if transaction.exists():
        raise RecordValidationError("unfinished paired publication requires recovery")
    encoded_entries: list[dict[str, object]] = []
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
            "temporary_relative_path": (target.parent / f".{target.name}.{secrets.token_hex(16)}.task6-pair.tmp").relative_to(root).as_posix(),
            "temporary_identity": None,
        })
    transaction.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(transaction, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        payload = canonical_json_bytes({"state": "prepared_v2", "entries": encoded_entries}, indent=None)
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_parent(transaction)


def _identity(path: Path) -> dict[str, int]:
    metadata = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(metadata.st_mode):
        raise RecordValidationError("paired publication target is not a regular file")
    return {"device": metadata.st_dev, "inode": metadata.st_ino}


def _owned(path: Path, entry: dict[str, object]) -> bool:
    identity = entry["temporary_identity"]
    if identity is None:
        return False
    try:
        actual = _identity(path)
        payload = path.read_bytes()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise RecordValidationError("paired publication target cannot be read") from exc
    return actual == identity and len(payload) == entry["byte_count"] and hashlib.sha256(payload).hexdigest() == entry["sha256"]


def prepare_paired_publication_entry(root: Path, index: int, payload: bytes) -> None:
    """Write one private staged file and durably bind its creation identity."""
    value, entries = _load_transaction(root)
    if type(index) is not int or not 0 <= index < len(entries):
        raise RecordValidationError("paired publication entry index is invalid")
    entry = entries[index]
    if hashlib.sha256(payload).hexdigest() != entry["sha256"] or len(payload) != entry["byte_count"]:
        raise RecordValidationError("paired publication payload differs from intent")
    if entry["temporary_identity"] is not None:
        raise RecordValidationError("paired publication entry is already staged")
    target = _inside(root, entry["relative_path"], field="target")
    temporary = _inside(root, entry["temporary_relative_path"], field="temporary target")
    if target.exists() or temporary.exists():
        raise FileExistsError("paired publication destination already exists")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    try:
        _write_all(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_parent(temporary)
    entry["temporary_identity"] = _identity(temporary)
    _write_transaction(root, value)


def install_paired_publication_entry(root: Path, index: int) -> None:
    """Atomically create one public target from its bound private staging inode."""
    _value, entries = _load_transaction(root)
    if type(index) is not int or not 0 <= index < len(entries):
        raise RecordValidationError("paired publication entry index is invalid")
    entry = entries[index]
    if entry["temporary_identity"] is None:
        raise RecordValidationError("paired publication entry is not staged")
    target = _inside(root, entry["relative_path"], field="target")
    temporary = _inside(root, entry["temporary_relative_path"], field="temporary target")
    if not _owned(temporary, entry):
        raise RecordValidationError("paired publication staging ownership mismatch")
    try:
        os.link(temporary, target, follow_symlinks=False)
    except FileExistsError:
        raise FileExistsError("paired publication destination already exists") from None
    _fsync_parent(target)
    if not _owned(target, entry):
        raise RecordValidationError("paired publication installed target ownership mismatch")
    # Retain the private hard link until pair commit/recovery.  It pins the
    # inode, so a same-bytes replacement cannot recycle the owned identity.


def recover_paired_publication(root: Path) -> None:
    """Finish a completed pair or erase an interrupted partial pair fail-closed."""
    transaction = _pair_transaction_path(root)
    if not transaction.exists():
        return
    _value, entries = _load_transaction(root)
    targets: list[Path] = []
    temporaries: list[Path] = []
    target_present = 0
    for entry in entries:
        target = _inside(root, entry["relative_path"], field="target")
        temporary = _inside(root, entry["temporary_relative_path"], field="temporary target")
        for candidate, label in ((target, "target"), (temporary, "temporary target")):
            if candidate.exists():
                if not _owned(candidate, entry):
                    raise RecordValidationError(f"paired publication {label} ownership mismatch")
                (targets if candidate == target else temporaries).append(candidate)
        if target.exists():
            target_present += 1
    if target_present == 2:
        for temporary in temporaries:
            _unlink_fsynced(temporary)
        _unlink_fsynced(transaction)
        return
    for target in targets:
        _unlink_fsynced(target)
    for temporary in temporaries:
        _unlink_fsynced(temporary)
    _unlink_fsynced(transaction)


def abort_paired_publication(root: Path) -> None:
    """Recover synchronously after a controlled publication exception."""
    recover_paired_publication(root)
