from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from pneuma_lab.cloud.production_surface import require_production_execution_surface


ROOT = Path(__file__).resolve().parents[2]


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
