"""Atomic run-state manifests and the append-only run event log."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.foundation.run_manifest import (
    EVENTS_NAME,
    MANIFEST_NAME,
    RunManifestError,
    RunManifestWriter,
)


def _manifest(status: str = "planned") -> dict:
    return {
        "manifest_kind": "pneuma_foundation_run",
        "run_id": "run-001",
        "status": status,
    }


def test_writer_creates_run_root_and_manifest(tmp_path: Path) -> None:
    run_root = tmp_path / "runs" / "run-001"
    writer = RunManifestWriter(run_root)
    path = writer.write_manifest(_manifest())
    assert path == writer.manifest_path == run_root / MANIFEST_NAME
    assert writer.events_path == run_root / EVENTS_NAME
    assert json.loads(path.read_text(encoding="utf-8")) == _manifest()


def test_manifest_bytes_are_canonical(tmp_path: Path) -> None:
    writer = RunManifestWriter(tmp_path)
    writer.write_manifest({"b": 1, "a": {"d": 2, "c": 3}})
    raw = writer.manifest_path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    expected = json.dumps(
        {"a": {"c": 3, "d": 2}, "b": 1},
        ensure_ascii=False,
        indent=4,
        sort_keys=True,
    )
    assert raw == (expected + "\n").encode("utf-8")


def test_manifest_replacement_is_complete_and_leaves_no_temporaries(
    tmp_path: Path,
) -> None:
    writer = RunManifestWriter(tmp_path)
    writer.write_manifest(_manifest("planned"))
    writer.write_manifest(_manifest("running"))
    value = json.loads(writer.manifest_path.read_text(encoding="utf-8"))
    assert value == _manifest("running")
    assert sorted(path.name for path in tmp_path.iterdir()) == [MANIFEST_NAME]


def test_events_append_one_json_object_per_line(tmp_path: Path) -> None:
    writer = RunManifestWriter(tmp_path)
    first = writer.append_event({"event": "run_started", "at": 1.5})
    second = writer.append_event({"event": "paused", "reasons": ["gpu_temperature"]})
    assert first == second == writer.events_path
    lines = writer.events_path.read_text(encoding="utf-8").splitlines()
    assert lines == [
        '{"at":1.5,"event":"run_started"}',
        '{"event":"paused","reasons":["gpu_temperature"]}',
    ]


def test_events_survive_manifest_replacement(tmp_path: Path) -> None:
    writer = RunManifestWriter(tmp_path)
    writer.append_event({"event": "run_started"})
    writer.write_manifest(_manifest("running"))
    writer.append_event({"event": "checkpoint_saved"})
    lines = writer.events_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["event"] for line in lines] == [
        "run_started",
        "checkpoint_saved",
    ]


def test_writer_rejects_non_mapping_payloads(tmp_path: Path) -> None:
    writer = RunManifestWriter(tmp_path)
    with pytest.raises(RunManifestError):
        writer.write_manifest(["not", "a", "mapping"])
    with pytest.raises(RunManifestError):
        writer.append_event("run_started")
    assert not writer.manifest_path.exists()
    assert not writer.events_path.exists()


def test_non_canonical_event_is_rejected_before_any_append(tmp_path: Path) -> None:
    writer = RunManifestWriter(tmp_path)
    writer.append_event({"event": "run_started"})
    with pytest.raises(RunManifestError):
        writer.append_event({"loss": float("nan")})
    with pytest.raises(RunManifestError):
        writer.append_event({"bad": object()})
    lines = writer.events_path.read_text(encoding="utf-8").splitlines()
    assert lines == ['{"event":"run_started"}']


def test_non_canonical_manifest_never_replaces_the_previous_state(
    tmp_path: Path,
) -> None:
    writer = RunManifestWriter(tmp_path)
    writer.write_manifest(_manifest("running"))
    with pytest.raises(RunManifestError):
        writer.write_manifest({"loss": float("inf")})
    with pytest.raises(RunManifestError):
        writer.write_manifest({"bad": object()})
    value = json.loads(writer.manifest_path.read_text(encoding="utf-8"))
    assert value == _manifest("running")
