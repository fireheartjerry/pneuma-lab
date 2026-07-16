"""Pinned 2B snapshot cache preparation and offline verification tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from pneuma_lab.foundation.model_cache import (
    CachedSnapshot,
    ModelCacheError,
    pinned_snapshot_path,
    prepare_pinned_snapshot,
    verify_pinned_snapshot,
)
from pneuma_lab.foundation.specs import MODEL_SPECS


_SPEC = MODEL_SPECS["2b"]
_RECEIPT_NAME = "pneuma-snapshot-receipt.json"


def _pinned_config() -> dict:
    return {
        "hidden_size": _SPEC.hidden_size,
        "layer_types": list(_SPEC.expected_layer_types),
        "num_hidden_layers": _SPEC.layer_count,
    }


def _fake_snapshot(tmp_path: Path, calls: list, kwargs: dict) -> None:
    calls.append(kwargs)
    local_dir = Path(kwargs["local_dir"])
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "config.json").write_text(
        json.dumps(_pinned_config(), sort_keys=True),
        encoding="utf-8",
    )
    (local_dir / "tokenizer.json").write_text(
        '{"model":{"type":"fixture"}}\n',
        encoding="utf-8",
    )
    (local_dir / "model.safetensors").write_bytes(b"\x00fixture-weights")
    hub_metadata = local_dir / ".cache" / "huggingface" / "download"
    hub_metadata.mkdir(parents=True, exist_ok=True)
    (hub_metadata / "config.json.metadata").write_text(
        "etag: fixture\n",
        encoding="utf-8",
    )


def _prepare(tmp_path: Path, calls: list | None = None) -> CachedSnapshot:
    calls = [] if calls is None else calls
    return prepare_pinned_snapshot(
        "2b",
        cache_root=tmp_path,
        snapshot_download=lambda **kwargs: _fake_snapshot(tmp_path, calls, kwargs),
    )


def test_cache_download_is_exactly_2b_and_writes_verified_receipt(
    tmp_path: Path,
) -> None:
    calls: list = []
    result = prepare_pinned_snapshot(
        "2b",
        cache_root=tmp_path,
        snapshot_download=lambda **kwargs: _fake_snapshot(tmp_path, calls, kwargs),
    )
    assert calls[0]["repo_id"] == "Qwen/Qwen3.5-2B"
    assert calls[0]["revision"] == "15852e8c16360a2fea060d615a32b45270f8a8fc"
    assert result.receipt_path.is_file()
    assert all(not path.is_symlink() for path in result.snapshot_path.rglob("*"))
    with pytest.raises(ModelCacheError, match="2B"):
        prepare_pinned_snapshot(
            "4b",
            cache_root=tmp_path,
            snapshot_download=lambda **kwargs: None,
        )


def test_prepare_targets_the_authorization_cache_layout(tmp_path: Path) -> None:
    calls: list = []
    result = _prepare(tmp_path, calls)
    expected_root = Path(tmp_path).resolve() / "models" / "2b" / _SPEC.revision
    assert result == CachedSnapshot(
        model_key="2b",
        snapshot_path=expected_root,
        receipt_path=expected_root / _RECEIPT_NAME,
        revision=_SPEC.revision,
    )
    assert Path(calls[0]["local_dir"]) == expected_root
    assert calls[0]["allow_patterns"] == (
        "*.json",
        "*.safetensors",
        "*.model",
        "*.txt",
        "*.tiktoken",
    )
    assert result.snapshot_path == pinned_snapshot_path("2b", cache_root=tmp_path)


def test_prepare_prunes_hub_metadata_and_writes_sorted_receipt(
    tmp_path: Path,
) -> None:
    result = _prepare(tmp_path)
    assert not (result.snapshot_path / ".cache").exists()
    receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
    assert set(receipt) == {
        "receipt_kind",
        "receipt_schema_version",
        "model_id",
        "revision",
        "files",
    }
    assert receipt["receipt_kind"] == "pneuma_pinned_model_snapshot"
    assert receipt["receipt_schema_version"] == "0.1.0"
    assert receipt["model_id"] == _SPEC.model_id
    assert receipt["revision"] == _SPEC.revision
    paths = [item["path"] for item in receipt["files"]]
    assert paths == sorted(paths)
    assert paths == ["config.json", "model.safetensors", "tokenizer.json"]
    for item in receipt["files"]:
        payload = (result.snapshot_path / item["path"]).read_bytes()
        assert item["size"] == len(payload)
        assert item["sha256"] == hashlib.sha256(payload).hexdigest()


def test_prepare_requires_config_json(tmp_path: Path) -> None:
    def download_without_config(**kwargs) -> None:
        local_dir = Path(kwargs["local_dir"])
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "tokenizer.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ModelCacheError, match="config.json"):
        prepare_pinned_snapshot(
            "2b",
            cache_root=tmp_path,
            snapshot_download=download_without_config,
        )


def test_prepare_rejects_symlinked_snapshot_members(tmp_path: Path) -> None:
    def download_with_symlink(**kwargs) -> None:
        local_dir = Path(kwargs["local_dir"])
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / "config.json").write_text(
            json.dumps(_pinned_config()),
            encoding="utf-8",
        )
        (local_dir / "tokenizer.json").write_text("{}\n", encoding="utf-8")
        try:
            os.symlink(local_dir / "config.json", local_dir / "alias.json")
        except OSError as exc:
            pytest.skip(f"symlinks unavailable: {exc}")

    with pytest.raises(ModelCacheError, match="symlink"):
        prepare_pinned_snapshot(
            "2b",
            cache_root=tmp_path,
            snapshot_download=download_with_symlink,
        )


def test_verify_round_trips_a_prepared_snapshot(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    verified = verify_pinned_snapshot("2b", cache_root=tmp_path)
    assert verified == prepared


def test_verify_rejects_a_tampered_file(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    weights = prepared.snapshot_path / "model.safetensors"
    weights.write_bytes(b"\x00tampered-weights")
    with pytest.raises(ModelCacheError, match="model.safetensors"):
        verify_pinned_snapshot("2b", cache_root=tmp_path)


def test_verify_rejects_missing_and_extra_files(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    extra = prepared.snapshot_path / "extra.json"
    extra.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ModelCacheError, match="missing or extra"):
        verify_pinned_snapshot("2b", cache_root=tmp_path)
    extra.unlink()
    (prepared.snapshot_path / "tokenizer.json").unlink()
    with pytest.raises(ModelCacheError, match="missing or extra"):
        verify_pinned_snapshot("2b", cache_root=tmp_path)


def test_verify_rejects_a_missing_receipt(tmp_path: Path) -> None:
    prepared = _prepare(tmp_path)
    prepared.receipt_path.unlink()
    with pytest.raises(ModelCacheError):
        verify_pinned_snapshot("2b", cache_root=tmp_path)


def test_verify_rejects_a_drifted_pinned_config(tmp_path: Path) -> None:
    def download_with_wrong_config(**kwargs) -> None:
        local_dir = Path(kwargs["local_dir"])
        local_dir.mkdir(parents=True, exist_ok=True)
        config = _pinned_config()
        config["hidden_size"] = 4096
        (local_dir / "config.json").write_text(
            json.dumps(config),
            encoding="utf-8",
        )
        (local_dir / "tokenizer.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ModelCacheError, match="hidden_size"):
        prepare_pinned_snapshot(
            "2b",
            cache_root=tmp_path,
            snapshot_download=download_with_wrong_config,
        )


def test_verify_rejects_unloadable_model_keys(tmp_path: Path) -> None:
    with pytest.raises(ModelCacheError, match="397b"):
        verify_pinned_snapshot("397b", cache_root=tmp_path)
    with pytest.raises(ModelCacheError, match="unknown"):
        verify_pinned_snapshot("unknown", cache_root=tmp_path)


def test_prepare_is_idempotent_over_an_existing_receipt(tmp_path: Path) -> None:
    first = _prepare(tmp_path)
    second = _prepare(tmp_path)
    assert first == second
    assert verify_pinned_snapshot("2b", cache_root=tmp_path) == second
