from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts.research.run_step7b_builds import plan_digest, require_plan


def _write(path: Path, value: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return hashlib.sha256(value).hexdigest()


def _plan(root: Path) -> dict:
    runtime = _write(root / "src/pneuma_lab/cloud/production_runtime.py", b"runtime")
    roles = {}
    for role in ("controller", "model-server", "benchmark-worker"):
        dockerfile = _write(root / f"infra/docker/{role}/Dockerfile", role.encode())
        lock = _write(root / f"infra/docker/{role}/{role}.lock", b"stdlib-only")
        roles[role] = {
            "dockerfile": {"path": f"infra/docker/{role}/Dockerfile", "sha256": dockerfile},
            "lock": {"path": f"infra/docker/{role}/{role}.lock", "sha256": lock},
            "base_digest": "sha256:" + "a" * 64,
        }
    plan = {
        "action_id": "step7b-aws-builder-001", "action_class": "image_build", "max_retries": 0,
        "input_lock_sha256": "b" * 64, "source_date_epoch": 0, "recipe_sha256": "c" * 64,
        "executor_sha256": "d" * 64, "runtime": {"path": "src/pneuma_lab/cloud/production_runtime.py", "sha256": runtime},
        "roles": roles,
        "requirements": {"forbidden": ["cloud_build", "ecr_push", "gpu_use", "benchmark_execution", "model_download"]},
    }
    plan["plan_sha256"] = plan_digest(plan)
    return plan


def test_executor_rejects_changed_recipe_bytes(tmp_path) -> None:
    plan = _plan(tmp_path)
    require_plan(plan, tmp_path)
    (tmp_path / "infra/docker/controller/Dockerfile").write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="does not match the sealed plan"):
        require_plan(plan, tmp_path)


def test_executor_rejects_plan_digest_drift(tmp_path) -> None:
    plan = _plan(tmp_path)
    plan["max_retries"] = 1
    with pytest.raises(ValueError, match="zero-retry"):
        require_plan(plan, tmp_path)
    plan["max_retries"] = 0
    plan["recipe_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="plan_sha256"):
        require_plan(plan, tmp_path)


def test_executor_rejects_non_builder_action_identity(tmp_path) -> None:
    plan = _plan(tmp_path)
    plan["action_id"] = "step7b-build-001"
    plan["plan_sha256"] = plan_digest(plan)
    with pytest.raises(ValueError, match="numbered Step 7B"):
        require_plan(plan, tmp_path)
