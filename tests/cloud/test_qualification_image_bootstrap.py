from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "infra/aws/qualification-image-build-user-data.sh"


def test_negative_check_expected_failure_reaches_post_check_sentinel(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text(
        "#!/bin/sh\nprintf '%s\\n' 'QUALIFICATION_CODE is required' >&2\nexit 37\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    command = (
        f"source {BOOTSTRAP.as_posix()}"
        f"; run_pre_push_checks image:action-002 {output_dir.as_posix()}"
    )
    environment = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}")
    completed = subprocess.run(
        ["bash", "-c", command],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    negative = json.loads((output_dir / "entrypoint-negative.json").read_text(encoding="utf-8"))
    assert negative["returncode"] == 37
    assert negative["qualification_code_required"] is True
    assert json.loads(
        (output_dir / "post-negative-check-sentinel.json").read_text(encoding="utf-8")
    ) == {"reached": True, "stage": "post-negative-check"}
    assert "if docker run" in BOOTSTRAP.read_text(encoding="utf-8")
    assert "set +e" not in BOOTSTRAP.read_text(encoding="utf-8")
    assert "trap - ERR" not in BOOTSTRAP.read_text(encoding="utf-8")
