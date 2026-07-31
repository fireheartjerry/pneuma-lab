from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2] / "infra" / "terraform"


def test_static_iac_contract_is_pinned_and_tier_agnostic() -> None:
    main = (ROOT / "main.tf").read_text(encoding="utf-8")
    assert 'instance_type       = ["g6e.2xlarge"]' in main
    assert "max_vcpus           = 8" in main
    assert "g6e.12xlarge" not in main
    assert 'type = "GPU", value = "1"' in main
    assert 'type = "VCPU", value = "8"' in main
    assert 'type = "MEMORY", value = "60000"' in main
    assert "C120" not in main and "C160" not in main
    assert (ROOT / ".terraform.lock.hcl").is_file()
    iam = (ROOT / "iam.tf").read_text(encoding="utf-8")
    assert 'actions   = ["dynamodb:GetItem"]' in iam
    assert "dynamodb:UpdateItem" in iam
    assert "dynamodb:UpdateItem" not in iam.split('data "aws_iam_policy_document" "watcher"')[0]


def test_terraform_binary_runs_credential_free_format_check_when_present() -> None:
    terraform = shutil.which("terraform")
    if terraform is None:
        pytest.skip("terraform unavailable: L1 binary validation pending")
    subprocess.run(
        [terraform, "fmt", "-check", "-recursive"],
        cwd=ROOT,
        check=True,
        timeout=60,
    )
