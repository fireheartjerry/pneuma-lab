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
    assert "min_vcpus           = 0" in main
    assert 'state                    = "DISABLED"' in main
    assert "C120" not in main and "C160" not in main
    assert (ROOT / ".terraform.lock.hcl").is_file()
    iam = (ROOT / "iam.tf").read_text(encoding="utf-8")
    worker = iam.split('data "aws_iam_policy_document" "watcher"')[0]
    assert 'actions   = ["dynamodb:GetItem"]' in worker
    assert "dynamodb:UpdateItem" in iam
    assert "dynamodb:UpdateItem" not in worker


def test_static_iac_has_launch_safety_controls() -> None:
    main = (ROOT / "main.tf").read_text(encoding="utf-8")
    iam = (ROOT / "iam.tf").read_text(encoding="utf-8")
    for required in (
        'map_public_ip_on_launch = false',
        'encrypted             = true',
        'http_tokens                 = "required"',
        'image_tag_mutability = "IMMUTABLE"',
        'scan_on_push = true',
        'block_public_policy     = true',
        'point_in_time_recovery {',
        'resource "aws_budgets_budget" "monthly"',
    ):
        assert required in main
    assert 'resource "aws_iam_role" "worker"' in iam
    assert 'resource "aws_iam_role" "watcher"' in iam


def test_terraform_validate_when_binary_is_available() -> None:
    terraform = shutil.which("terraform")
    if terraform is None:
        pytest.skip("terraform unavailable: L1 binary validation pending")
    completed = subprocess.run(
        [terraform, f"-chdir={ROOT}", "validate", "-no-color"],
        capture_output=True,
        check=False,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
