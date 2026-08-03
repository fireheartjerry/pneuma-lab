from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "infra/aws/qualification-image-build-user-data.sh"


def _bash_path(path: Path) -> str:
    """Return a path usable by the WSL Bash invoked on Windows."""
    if os.name != "nt":
        return path.as_posix()
    return f"/mnt/{path.drive[0].lower()}{path.as_posix()[2:]}"


def test_negative_check_expected_failure_reaches_post_check_sentinel(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_bytes(
        b"#!/bin/sh\ncase \" $* \" in *' --version'*) printf '%s\\n' 'aws-cli/2.36.14 Python/3.14 Linux/fixture'; exit 0;; esac\nprintf '%s\\n' 'QUALIFICATION_CODE is required' >&2\nexit 37\n"
    )
    docker.chmod(0o755)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    portable_bootstrap = tmp_path / "qualification-image-build-user-data.sh"
    portable_bootstrap.write_bytes(BOOTSTRAP.read_bytes().replace(b"\r\n", b"\n"))
    portable_bootstrap.chmod(0o755)
    command = (
        f"PATH={shlex.quote(_bash_path(fake_bin))}:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; "
        "export PATH; "
        f"source {shlex.quote(_bash_path(portable_bootstrap))}; "
        f"run_pre_push_checks image:action-002 {shlex.quote(_bash_path(output_dir))}"
    )
    completed = subprocess.run(
        ["bash", "-c", command],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )

    assert completed.returncode == 0, completed.stderr
    negative = json.loads(
        (output_dir / "entrypoint-negative.json").read_text(encoding="utf-8")
    )
    assert negative["returncode"] == 37
    assert negative["qualification_code_required"] is True
    assert json.loads(
        (output_dir / "post-negative-check-sentinel.json").read_text(encoding="utf-8")
    ) == {"reached": True, "stage": "post-negative-check"}
    assert "if docker run" in BOOTSTRAP.read_text(encoding="utf-8")
    assert "set +e" not in BOOTSTRAP.read_text(encoding="utf-8")
    assert "trap - ERR" not in BOOTSTRAP.read_text(encoding="utf-8")


def test_fixture_runtime_check_is_bound_after_the_negative_entrypoint_check() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert "qualification_image_fixture_check.py" in text
    assert "--network none" in text
    assert 'run_pre_push_checks "$IMAGE_REF" "$OUTPUT_DIR"' in text


def test_image_build_rechecks_the_immutable_ecr_digest_configuration() -> None:
    text = BOOTSTRAP.read_text(encoding="utf-8")
    assert 'docker pull "$IMMUTABLE_IMAGE_REF"' in text
    assert 'docker image inspect "$IMMUTABLE_IMAGE_REF"' in text
    assert "fresh_ecr_image_config" in text
    assert "fresh_ecr_fixture_runtime" in text
    assert "fresh_ecr_sidecar_sha256" in text
    assert "aws-cli/2" in text
