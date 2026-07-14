"""Canonical, atomic foundation artifact helpers."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import pytest

from pneuma_lab.foundation import artifacts
from pneuma_lab.foundation.artifacts import (
    sha256_file,
    write_atomic_bytes,
    write_atomic_json,
    write_atomic_jsonl,
)


def test_atomic_json_and_jsonl_are_canonical(tmp_path: Path) -> None:
    json_path = tmp_path / "receipt.json"
    jsonl_path = tmp_path / "identities.jsonl"
    write_atomic_json(json_path, {"b": 2, "a": 1})
    write_atomic_jsonl(jsonl_path, ({"b": 2, "a": 1},))
    assert json_path.read_bytes() == b'{\n    "a": 1,\n    "b": 2\n}\n'
    assert jsonl_path.read_bytes() == b'{"a":1,"b":2}\n'
    assert sha256_file(jsonl_path) == hashlib.sha256(
        jsonl_path.read_bytes()
    ).hexdigest()


def test_atomic_bytes_creates_parent_and_replaces_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "artifact.bin"
    write_atomic_bytes(path, b"first")
    write_atomic_bytes(path, b"second")
    assert path.read_bytes() == b"second"
    assert tuple(path.parent.iterdir()) == (path,)


@pytest.mark.parametrize("writer", (write_atomic_json, write_atomic_jsonl))
def test_json_writers_reject_nonfinite_values_without_partial_publish(
    tmp_path: Path,
    writer,
) -> None:
    path = tmp_path / "artifact.json"
    path.write_bytes(b"preserved")
    values = {"value": math.nan} if writer is write_atomic_json else (
        {"value": math.inf},
    )
    with pytest.raises(ValueError):
        writer(path, values)
    assert path.read_bytes() == b"preserved"


def test_jsonl_rejects_non_mapping_records_without_partial_publish(
    tmp_path: Path,
) -> None:
    path = tmp_path / "artifact.jsonl"
    path.write_bytes(b"preserved")
    with pytest.raises(TypeError, match="mapping"):
        write_atomic_jsonl(path, ({"valid": True}, ["not-a-mapping"]))
    assert path.read_bytes() == b"preserved"


def test_atomic_bytes_cleans_partial_temp_after_write_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"preserved")
    real_fdopen = artifacts.os.fdopen

    class FailingWriter:
        def __init__(self, descriptor, mode, *, closefd):
            self.stream = real_fdopen(descriptor, mode, closefd=closefd)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.stream.close()

        def write(self, payload):
            self.stream.write(payload[:1])
            raise OSError("injected write failure")

    monkeypatch.setattr(artifacts.os, "fdopen", FailingWriter)
    with pytest.raises(OSError, match="write failure"):
        write_atomic_bytes(path, b"replacement")
    assert path.read_bytes() == b"preserved"
    assert tuple(path.parent.iterdir()) == (path,)


def test_atomic_bytes_cleans_temp_after_fsync_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"preserved")

    def fail_fsync(_stream) -> None:
        raise OSError("injected fsync failure")

    monkeypatch.setattr(artifacts, "_fsync_data", fail_fsync)
    with pytest.raises(OSError, match="fsync failure"):
        write_atomic_bytes(path, b"replacement")
    assert path.read_bytes() == b"preserved"
    assert tuple(path.parent.iterdir()) == (path,)


def test_atomic_bytes_cleans_temp_after_replace_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    path = tmp_path / "artifact.bin"
    path.write_bytes(b"preserved")

    def fail_replace(_source, _target) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(artifacts.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failure"):
        write_atomic_bytes(path, b"replacement")
    assert path.read_bytes() == b"preserved"
    assert tuple(path.parent.iterdir()) == (path,)
