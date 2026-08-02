from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from pneuma_lab.cloud.production_surface import require_production_execution_surface
from scripts.research import run_production_surface_e2e


ROOT = Path(__file__).resolve().parents[2]


def test_image_role_uses_sealed_entrypoint_without_duplicate_role(tmp_path, monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"{}", stderr=b"")

    monkeypatch.setattr(run_production_surface_e2e.subprocess, "run", fake_run)
    run_production_surface_e2e.run_role(
        "model-server",
        image="pneuma-step7b-model-server:build-1",
        harness=tmp_path / "harness.json",
        harness_sha256="a" * 64,
        input_path=None,
        work=tmp_path,
        controller_privileged=False,
    )
    command = commands[0]
    image_index = command.index("pneuma-step7b-model-server:build-1")
    assert command[image_index + 1 : image_index + 3] == ["--protocol", "e2e"]


def test_container_bind_receipts_get_read_bits(tmp_path) -> None:
    harness = tmp_path / "harness.json"
    harness.write_bytes(b"qualification harness")
    harness.chmod(0o600)

    run_production_surface_e2e._ensure_container_bind_readable(harness)

    assert harness.stat().st_mode & 0o444 == 0o444


def test_local_three_role_surface_e2e(tmp_path) -> None:
    harness = tmp_path / "harness.json"
    harness_bytes = json.dumps(
        {
            "record_kind": "cloud_production_e2e_harness",
            "schema_version": "0.1.0",
            "action_id": "production-surface-test-001",
            "input_lock_sha256": "f" * 64,
            "request": {
                "request_id": "req-001",
                "prompt": "bounded qualification request",
                "max_tokens": 4,
                "temperature": 0.0,
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode() + b"\n"
    harness.write_bytes(harness_bytes)
    digest = hashlib.sha256(harness_bytes).hexdigest()
    output = tmp_path / "e2e"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/research/run_production_surface_e2e.py"),
            "--harness",
            str(harness),
            "--harness-sha256",
            digest,
            "--output-dir",
            str(output),
            "--source-root",
            str(ROOT),
            "--source-commit",
            "1" * 40,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    surface = json.loads((output / "surface.json").read_text(encoding="utf-8"))
    assert len(require_production_execution_surface(surface)["roles"]) == 3
    assert json.loads((output / "benchmark-worker.json").read_text(encoding="utf-8"))["state"] == "COMPLETE"
    for role in ("controller", "model-server", "benchmark-worker"):
        assert json.loads((output / f"{role}-wrong-hash.json").read_text(encoding="utf-8"))["state"] == "FAILED"
