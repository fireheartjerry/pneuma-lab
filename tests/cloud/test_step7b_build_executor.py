from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.research import run_step7b_builds
from scripts.research.run_step7b_builds import (
    BUILDX_SHA256,
    BUILDX_VERSION,
    BUILDKIT_VERSION,
    plan_digest,
    require_free_storage,
    require_plan,
)


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
        "executor_sha256": hashlib.sha256(Path(run_step7b_builds.__file__).read_bytes()).hexdigest(),
        "buildx": {
            "version": BUILDX_VERSION,
            "url": "https://example.invalid/buildx",
            "sha256": BUILDX_SHA256,
        },
        "buildkit": {
            "version": BUILDKIT_VERSION,
            "image": "moby/buildkit:v0.13.2@sha256:" + "d" * 64,
        },
        "runtime": {"path": "src/pneuma_lab/cloud/production_runtime.py", "sha256": runtime},
        "roles": roles,
        "requirements": {
            "forbidden": ["cloud_build", "ecr_push", "gpu_use", "benchmark_execution", "model_download"],
            "minimum_verified_free_storage_gib": 600,
        },
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


def test_executor_rejects_changed_executor_bytes(tmp_path, monkeypatch) -> None:
    plan = _plan(tmp_path)
    monkeypatch.setattr(run_step7b_builds, "sha256_file", lambda _: "0" * 64)
    with pytest.raises(ValueError, match="executor bytes"):
        require_plan(plan, tmp_path)


def test_executor_enforces_sealed_free_storage_floor(tmp_path, monkeypatch) -> None:
    plan = _plan(tmp_path)
    monkeypatch.setattr(
        run_step7b_builds.shutil,
        "disk_usage",
        lambda _: SimpleNamespace(free=599 * 1024**3),
    )
    with pytest.raises(ValueError, match="below the sealed 600 GiB floor"):
        require_free_storage(plan, tmp_path)


def test_executor_uses_root_backed_syft_staging() -> None:
    source = Path(run_step7b_builds.__file__).read_text(encoding="utf-8")
    assert 'syft_tmp = output.parent / "syft-tmp"' in source
    assert 'syft_env = dict(os.environ, TMPDIR=str(syft_tmp))' in source
    assert 'build_environment["SOURCE_DATE_EPOCH"]' in source
    assert '"BUILDKIT_MULTI_PLATFORM=1"' not in source
    assert 'type=docker,rewrite-timestamp=true' in source
    assert '"buildx",\n                "build"' in source
    assert '"--builder"' in source
    assert 'docker-container' in source
    assert '"linux/amd64"' in source
    assert 'buildx-builder-stderr.txt' in source
    assert 'inspection_result.returncode' in source
    assert 'BuildKit(?: version)?' in source


def test_production_surface_failure_receipt_preserves_child_output() -> None:
    source = Path(run_step7b_builds.__file__).read_text(encoding="utf-8")
    assert "subprocess.run(command, check=False, text=True, capture_output=True" in source
    assert '"returncode": completed.returncode' in source
    assert '"stdout": completed.stdout' in source
    assert '"stderr": completed.stderr' in source
    assert 'if completed.returncode != 0:' in source


def test_role_dockerfiles_use_the_repository_build_context() -> None:
    """The executor supplies the sealed source root as Docker's build context."""
    repository = Path(__file__).resolve().parents[2]
    for role in ("controller", "model-server", "benchmark-worker"):
        text = (repository / f"infra/docker/{role}/Dockerfile").read_text(encoding="utf-8")
        assert f"COPY infra/docker/{role}/{role}.lock " in text
        assert f'ENTRYPOINT ["python3", "-m", "pneuma_lab.cloud.production_runtime", "{role}"]' in text
        assert 'find /opt/pneuma -xdev -exec touch --date="@${SOURCE_DATE_EPOCH}"' in text


def test_aws_bootstrap_pins_the_reproducible_builder_client() -> None:
    template = (Path(__file__).resolve().parents[2] / "infra/aws/step7b-aws-builder-user-data.sh").read_text(encoding="utf-8")
    assert "__BUILDX_URL__" in template
    assert "__BUILDX_SHA256__" in template
    assert "dnf install -y docker tar gzip\n" in template
    assert "dnf install -y docker tar gzip curl" not in template
    assert "docker buildx version" in template
    assert "docker/cli-plugins/docker-buildx" in template
    assert "buildx_digest_mismatch" in template
