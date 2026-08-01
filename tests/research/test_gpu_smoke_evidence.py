from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "docs/research/neurips-2026-workshop/evidence/gpu-smoke-20260801"


def test_gpu_smoke_receipt_binds_exact_linux_evidence() -> None:
    receipt = json.loads((EVIDENCE / "receipt.json").read_text(encoding="utf-8"))
    inspect_path = EVIDENCE / "worker-inspect.json"
    nvidia_path = EVIDENCE / "nvidia-smi.csv"
    assert receipt["instance_type"] == "g6e.2xlarge"
    assert receipt["worker_inspect"]["cuda_device_count"] == 1
    assert receipt["worker_inspect"]["cuda_name"] == "NVIDIA L40S"
    assert receipt["worker_inspect"]["cuda_total_memory_bytes"] == 47_665_709_056
    assert receipt["worker_inspect_sha256"] == hashlib.sha256(inspect_path.read_bytes()).hexdigest()
    assert receipt["nvidia_smi_sha256"] == hashlib.sha256(nvidia_path.read_bytes()).hexdigest()
    assert receipt["image"].endswith("@sha256:1fc54d73f9ec36356bec5c2c8497b671f72a9e43c0bae4fbb84be3ee6ede9ae2")
    assert receipt["worker_inspect"] == json.loads(inspect_path.read_text(encoding="utf-8"))
