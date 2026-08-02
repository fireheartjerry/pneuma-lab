from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from pneuma_lab.cloud.manifests import validate_production_role_receipt


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


def test_e2e_role_handshake_is_content_addressed(tmp_path) -> None:
    harness = tmp_path / "e2e-harness.json"
    payload = {
        "record_kind": "cloud_production_e2e_harness",
        "schema_version": "0.1.0",
        "action_id": "production-surface-test-001",
        "input_lock_sha256": "f" * 64,
        "request": {
            "request_id": "req-001",
            "prompt": "return a bounded qualification response",
            "max_tokens": 4,
            "temperature": 0.0,
        },
    }
    harness.write_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode() + b"\n")
    harness_digest = hashlib.sha256(harness.read_bytes()).hexdigest()

    def run(role: str, input_path=None):
        command = [
            sys.executable,
            "-m",
            "pneuma_lab.cloud.production_runtime",
            role,
            "--protocol",
            "e2e",
            "--harness",
            str(harness),
            "--harness-sha256",
            harness_digest,
        ]
        if input_path is not None:
            command.extend(["--input", str(input_path)])
        return subprocess.run(command, capture_output=True, text=True, check=False)

    controller = run("controller")
    assert controller.returncode == 0
    controller_path = tmp_path / "controller.json"
    controller_path.write_text(controller.stdout, encoding="utf-8")
    controller_receipt = json.loads(controller.stdout)
    assert validate_production_role_receipt(controller_receipt)["state"] == "DISPATCHED"

    model = run("model-server", controller_path)
    assert model.returncode == 0
    model_path = tmp_path / "model.json"
    model_path.write_text(model.stdout, encoding="utf-8")
    model_receipt = json.loads(model.stdout)
    assert validate_production_role_receipt(model_receipt)["state"] == "RESPONDED"

    worker = run("benchmark-worker", model_path)
    assert worker.returncode == 0
    worker_receipt = validate_production_role_receipt(json.loads(worker.stdout))
    assert worker_receipt["state"] == "COMPLETE"
    assert worker_receipt["payload"]["accepted"] is True

    wrong_predecessor = tmp_path / "wrong.json"
    wrong_predecessor.write_text(json.dumps({"record_kind": "cloud_production_role_receipt"}), encoding="utf-8")
    failed = run("model-server", wrong_predecessor)
    assert failed.returncode == 2
    assert json.loads(failed.stdout)["reason"] == "predecessor_harness_mismatch"
