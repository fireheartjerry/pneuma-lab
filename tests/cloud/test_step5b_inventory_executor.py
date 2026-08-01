from __future__ import annotations

import hashlib
import json

import pytest

from scripts.research import execute_step5b_inventory as executor


def test_docker_manifest_must_match_frozen_digest(monkeypatch) -> None:
    manifest = {"schemaVersion": 2, "config": {"digest": "sha256:" + "1" * 64, "size": 1}, "layers": []}
    raw = json.dumps(manifest).encode()
    monkeypatch.setattr(executor, "_request_json", lambda *args, **kwargs: (
        ({"token": "t"}, {}, b"token") if "auth.docker.io" in args[0] else (manifest, {}, raw)
    ))
    with pytest.raises(RuntimeError, match="frozen digest"):
        executor._docker_inventory("docker.io/vllm/vllm-openai", "sha256:" + "0" * 64)


def test_hf_inventory_distinguishes_lfs_sha256_from_git_sha1(monkeypatch) -> None:
    payload = [
        {"type": "file", "path": "weights.safetensors", "oid": "a" * 40, "size": 9, "lfs": {"oid": "b" * 64, "size": 10}},
        {"type": "file", "path": "config.json", "oid": "c" * 40, "size": 20},
    ]
    raw = json.dumps(payload).encode()
    monkeypatch.setattr(executor, "_request_json", lambda *args, **kwargs: (payload, {}, raw))
    result = executor._hf_inventory("owner/repo", "d" * 40, dataset=False)
    assert [(item["identity_algorithm"], item["size_bytes"]) for item in result["items"]] == [
        ("git_sha1", 20), ("sha256", 10)
    ]
    assert result["pages"][0]["sha256"] == hashlib.sha256(raw).hexdigest()


def test_execution_region_is_fail_closed(monkeypatch) -> None:
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")
    with pytest.raises(RuntimeError, match="execution region"):
        executor.require_execution_region()
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    executor.require_execution_region()
