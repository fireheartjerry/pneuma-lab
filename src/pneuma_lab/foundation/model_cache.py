"""Pinned local model snapshot cache with offline-verifiable receipts."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from typing import Callable

from pneuma_lab.foundation.artifacts import _canonical_json_bytes, sha256_file
from pneuma_lab.foundation.snapshot_receipt import (
    SnapshotReceiptError,
    verify_pinned_snapshot as _verify_snapshot_at_path,
)
from pneuma_lab.foundation.specs import MODEL_SPECS


_RECEIPT_NAME = "pneuma-snapshot-receipt.json"
_ALLOW_PATTERNS = ("*.json", "*.safetensors", "*.model", "*.txt", "*.tiktoken")
_HUB_METADATA_DIRECTORY = ".cache"


class ModelCacheError(Exception):
    """Raised when the pinned local model cache cannot be prepared or proven."""


@dataclass(frozen=True)
class CachedSnapshot:
    model_key: str
    snapshot_path: Path
    receipt_path: Path
    revision: str


def pinned_snapshot_path(model_key: str, *, cache_root: Path) -> Path:
    """Return the exact local layout the authorization contract expects."""

    spec = MODEL_SPECS.get(model_key)
    if spec is None:
        raise ModelCacheError(f"unknown model key: {model_key!r}")
    if not spec.download_allowed:
        raise ModelCacheError(
            f"model key {model_key!r} is a compatibility reference and is never cached"
        )
    return Path(cache_root).resolve() / "models" / model_key / spec.revision


def _align_windows_receipt_times(receipt_path: Path) -> None:
    """Make the receipt's NTFS birth and change times identical on Windows.

    The strict verifier cross-checks the receipt's path-stat signature
    against its held-handle signature. On Windows Python reports
    ``st_ctime_ns`` as the birth time for path stats but as the NTFS change
    time for handle stats, so the crossing only holds when those two
    timestamps are equal. Writing (or rewriting) a file leaves them unequal,
    which would make verification of a freshly prepared receipt flaky, so the
    creation time is pinned to the final change time through one attribute
    handle. Linux stats are self-consistent and need no alignment.
    """

    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes

    class FileBasicInfo(ctypes.Structure):
        _fields_ = (
            ("CreationTime", ctypes.c_longlong),
            ("LastAccessTime", ctypes.c_longlong),
            ("LastWriteTime", ctypes.c_longlong),
            ("ChangeTime", ctypes.c_longlong),
            ("FileAttributes", wintypes.DWORD),
        )

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    get_information = kernel32.GetFileInformationByHandleEx
    get_information.argtypes = (
        wintypes.HANDLE,
        wintypes.INT,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    get_information.restype = wintypes.BOOL
    set_information = kernel32.SetFileInformationByHandle
    set_information.argtypes = (
        wintypes.HANDLE,
        wintypes.INT,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    set_information.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL

    file_read_attributes = 0x0080
    file_write_attributes = 0x0100
    file_share_read = 0x00000001
    open_existing = 3
    file_basic_info_class = 0

    def alignment_error() -> ModelCacheError:
        return ModelCacheError(
            "receipt timestamp alignment failed: "
            f"{ctypes.WinError(ctypes.get_last_error())}"
        )

    handle = create_file(
        os.fspath(receipt_path),
        file_read_attributes | file_write_attributes,
        file_share_read,
        None,
        open_existing,
        0,
        None,
    )
    if handle is None or handle == ctypes.c_void_p(-1).value:
        raise alignment_error()
    try:
        info = FileBasicInfo()
        if not get_information(
            handle,
            file_basic_info_class,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            raise alignment_error()
        aligned = FileBasicInfo()
        aligned.CreationTime = info.ChangeTime
        aligned.ChangeTime = info.ChangeTime
        if not set_information(
            handle,
            file_basic_info_class,
            ctypes.byref(aligned),
            ctypes.sizeof(aligned),
        ):
            raise alignment_error()
    finally:
        close_handle(handle)


def _write_receipt(receipt_path: Path, receipt: dict) -> None:
    """Write the canonical receipt bytes directly, without a rename.

    A renamed temporary would permanently carry an NTFS change time later
    than the receipt's birth time, which the verifier's held-handle crossing
    rejects on Windows, so the payload is written in place and its timestamps
    are aligned. The immediate full verification pass in
    :func:`prepare_pinned_snapshot` proves the resulting bytes.
    """

    payload = _canonical_json_bytes(receipt, indent=4)
    descriptor = os.open(
        receipt_path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0),
        0o644,
    )
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _align_windows_receipt_times(receipt_path)


def _default_snapshot_download() -> Callable:
    try:
        import huggingface_hub
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise ModelCacheError(
            "install the foundation extra before downloading the pinned snapshot"
        ) from exc
    return huggingface_hub.snapshot_download


def prepare_pinned_snapshot(
    model_key: str,
    *,
    cache_root: Path,
    snapshot_download: Callable | None = None,
) -> CachedSnapshot:
    """Materialize, receipt, and verify the pinned 2B snapshot locally."""

    if model_key != "2b":
        raise ModelCacheError("preparation may download only the pinned 2B model")
    spec = MODEL_SPECS[model_key]
    root = pinned_snapshot_path(model_key, cache_root=cache_root)
    loader = snapshot_download or _default_snapshot_download()
    loader(
        repo_id=spec.model_id,
        revision=spec.revision,
        local_dir=root,
        allow_patterns=_ALLOW_PATTERNS,
    )
    if not root.is_dir():
        raise ModelCacheError("snapshot download produced no local directory")
    hub_metadata = root / _HUB_METADATA_DIRECTORY
    if hub_metadata.exists():
        shutil.rmtree(hub_metadata)

    receipt_path = root / _RECEIPT_NAME
    files = []
    for path in sorted(
        candidate for candidate in root.rglob("*") if candidate.is_file()
    ):
        if path == receipt_path:
            continue
        if path.is_symlink():
            raise ModelCacheError(f"snapshot contains a symlink: {path}")
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    files.sort(key=lambda item: item["path"])
    if not any(item["path"] == "config.json" for item in files):
        raise ModelCacheError("snapshot is missing config.json")
    receipt = {
        "receipt_kind": "pneuma_pinned_model_snapshot",
        "receipt_schema_version": "0.1.0",
        "model_id": spec.model_id,
        "revision": spec.revision,
        "files": files,
    }
    _write_receipt(receipt_path, receipt)
    verify_pinned_snapshot(model_key, cache_root=cache_root)
    return CachedSnapshot(model_key, root, receipt_path, spec.revision)


def verify_pinned_snapshot(model_key: str, *, cache_root: Path) -> CachedSnapshot:
    """Reverify the cached snapshot offline: hashes, inventory, pinned config."""

    root = pinned_snapshot_path(model_key, cache_root=cache_root)
    try:
        verified = _verify_snapshot_at_path(model_key, snapshot_path=root)
    except SnapshotReceiptError as exc:
        raise ModelCacheError(f"pinned snapshot verification failed: {exc}") from exc
    return CachedSnapshot(
        model_key=verified.model_key,
        snapshot_path=verified.snapshot_path,
        receipt_path=verified.receipt_path,
        revision=verified.revision,
    )


__all__ = [
    "CachedSnapshot",
    "ModelCacheError",
    "pinned_snapshot_path",
    "prepare_pinned_snapshot",
    "verify_pinned_snapshot",
]
