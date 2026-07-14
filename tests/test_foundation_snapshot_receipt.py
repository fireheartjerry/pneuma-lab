"""Offline, receipt-bound pinned snapshot verification tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from pneuma_lab.foundation.snapshot_receipt import (
    SnapshotReceiptError,
    verify_pinned_snapshot,
)
from pneuma_lab.foundation.specs import MODEL_SPECS


def _snapshot(tmp_path: Path) -> Path:
    root = tmp_path / "snapshot"
    root.mkdir()
    spec = MODEL_SPECS["2b"]
    files = {
        "config.json": json.dumps(
            {
                "hidden_size": spec.hidden_size,
                "layer_types": list(spec.expected_layer_types),
                "num_hidden_layers": spec.layer_count,
            },
            sort_keys=True,
        ).encode("utf-8"),
        "tokenizer.json": b'{"model":{"type":"fixture"}}\n',
    }
    for name, payload in files.items():
        (root / name).write_bytes(payload)
    _write_receipt(root, files)
    return root


def _write_receipt(
    root: Path,
    files: dict[str, bytes],
    **overrides,
) -> None:
    spec = MODEL_SPECS["2b"]
    receipt = {
        "receipt_kind": "pneuma_pinned_model_snapshot",
        "receipt_schema_version": "0.1.0",
        "model_id": spec.model_id,
        "revision": spec.revision,
        "files": [
            {
                "path": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in sorted(files.items())
        ],
        **overrides,
    }
    (root / "pneuma-snapshot-receipt.json").write_text(
        json.dumps(receipt, indent=4, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _receipt(root: Path) -> dict:
    return json.loads(
        (root / "pneuma-snapshot-receipt.json").read_text(encoding="utf-8")
    )


def _replace_receipt(root: Path, receipt: dict) -> None:
    (root / "pneuma-snapshot-receipt.json").write_text(
        json.dumps(receipt, indent=4, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _make_directory_alias(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            pytest.skip(f"directory junctions unavailable: {result.stderr.strip()}")
        return
    try:
        link.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def test_verify_pinned_snapshot_returns_deterministic_receipt_binding(
    tmp_path: Path,
) -> None:
    root = _snapshot(tmp_path)

    first = verify_pinned_snapshot("2b", snapshot_path=root)
    second = verify_pinned_snapshot("2b", snapshot_path=root)

    assert first == second
    assert first.snapshot_path == root
    assert first.receipt_path == root / "pneuma-snapshot-receipt.json"
    assert first.model_id == MODEL_SPECS["2b"].model_id
    assert first.revision == MODEL_SPECS["2b"].revision
    assert len(first.receipt_sha256) == 64
    assert len(first.snapshot_sha256) == 64
    assert tuple(item.path for item in first.files) == (
        "config.json",
        "tokenizer.json",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("receipt_kind", "other"),
        ("receipt_schema_version", "9.9.9"),
        ("model_id", "Qwen/not-the-pin"),
        ("revision", "0" * 40),
    ),
)
def test_verify_pinned_snapshot_rejects_wrong_receipt_identity(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    root = _snapshot(tmp_path)
    receipt = _receipt(root)
    receipt[field] = value
    _replace_receipt(root, receipt)

    with pytest.raises(SnapshotReceiptError, match="receipt|model|revision|schema"):
        verify_pinned_snapshot("2b", snapshot_path=root)


@pytest.mark.parametrize("case", ("tampered", "missing", "extra", "unsafe"))
def test_verify_pinned_snapshot_rejects_file_set_or_digest_mismatch(
    tmp_path: Path,
    case: str,
) -> None:
    root = _snapshot(tmp_path)
    if case == "tampered":
        (root / "tokenizer.json").write_bytes(b"X" * 29)
    elif case == "missing":
        (root / "tokenizer.json").unlink()
    elif case == "extra":
        (root / "unreceipted.txt").write_text("extra", encoding="utf-8")
    else:
        receipt = _receipt(root)
        receipt["files"][0]["path"] = "../config.json"
        _replace_receipt(root, receipt)

    with pytest.raises(SnapshotReceiptError, match="file|path|digest|size|missing|extra"):
        verify_pinned_snapshot("2b", snapshot_path=root)


@pytest.mark.parametrize(
    "payload",
    (
        b'{"receipt_kind":"pneuma_pinned_model_snapshot",'
        b'"receipt_kind":"duplicate"}',
        b'{"receipt_kind":"pneuma_pinned_model_snapshot","files":NaN}',
    ),
)
def test_verify_pinned_snapshot_rejects_non_strict_receipt_json(
    tmp_path: Path,
    payload: bytes,
) -> None:
    root = _snapshot(tmp_path)
    (root / "pneuma-snapshot-receipt.json").write_bytes(payload)

    with pytest.raises(SnapshotReceiptError, match="strict|duplicate|finite|JSON"):
        verify_pinned_snapshot("2b", snapshot_path=root)


def test_verify_pinned_snapshot_requires_tokenizer_artifact(tmp_path: Path) -> None:
    root = _snapshot(tmp_path)
    (root / "tokenizer.json").unlink()
    config = (root / "config.json").read_bytes()
    _write_receipt(root, {"config.json": config})

    with pytest.raises(SnapshotReceiptError, match="tokenizer"):
        verify_pinned_snapshot("2b", snapshot_path=root)


def test_verify_pinned_snapshot_validates_receipted_config(tmp_path: Path) -> None:
    root = _snapshot(tmp_path)
    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    config["hidden_size"] = 1
    config_payload = json.dumps(config, sort_keys=True).encode("utf-8")
    (root / "config.json").write_bytes(config_payload)
    tokenizer_payload = (root / "tokenizer.json").read_bytes()
    _write_receipt(
        root,
        {
            "config.json": config_payload,
            "tokenizer.json": tokenizer_payload,
        },
    )

    with pytest.raises(SnapshotReceiptError, match="config|hidden_size|pinned"):
        verify_pinned_snapshot("2b", snapshot_path=root)


def test_verify_pinned_snapshot_rejects_hard_link_alias(tmp_path: Path) -> None:
    root = _snapshot(tmp_path)
    alias = root / "tokenizer-copy.json"
    try:
        os.link(root / "tokenizer.json", alias)
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")
    receipt = _receipt(root)
    payload = alias.read_bytes()
    receipt["files"].append(
        {
            "path": alias.name,
            "size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    )
    receipt["files"].sort(key=lambda item: item["path"])
    _replace_receipt(root, receipt)

    with pytest.raises(SnapshotReceiptError, match="hard.link|alias"):
        verify_pinned_snapshot("2b", snapshot_path=root)


def test_verify_pinned_snapshot_rejects_link_or_reparse_member(
    tmp_path: Path,
) -> None:
    root = _snapshot(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    _make_directory_alias(root / "linked", outside)

    with pytest.raises(SnapshotReceiptError, match="link|reparse|junction"):
        verify_pinned_snapshot("2b", snapshot_path=root)


def test_verify_pinned_snapshot_rejects_link_or_reparse_ancestry(
    tmp_path: Path,
) -> None:
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    root = _snapshot(real_parent)
    alias_parent = tmp_path / "alias"
    _make_directory_alias(alias_parent, real_parent)

    with pytest.raises(SnapshotReceiptError, match="link|reparse|junction|ancestry"):
        verify_pinned_snapshot("2b", snapshot_path=alias_parent / root.name)
