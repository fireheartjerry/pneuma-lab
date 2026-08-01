from __future__ import annotations

import hashlib
import json
import subprocess
import sys


def test_exact_harness_bytes_are_required(tmp_path) -> None:
    harness = tmp_path / "harness.json"
    harness.write_bytes(b'{"harness":"exact"}')
    digest = hashlib.sha256(harness.read_bytes()).hexdigest()
    command = [sys.executable, "-m", "pneuma_lab.cloud.production_runtime", "controller", "--harness", str(harness), "--harness-sha256", digest]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert json.loads(result.stdout)["state"] == "READY"
    result = subprocess.run([*command[:-1], "0" * 64], capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert json.loads(result.stdout)["reason"] == "harness_sha256_mismatch"
