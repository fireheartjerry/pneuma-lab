from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.iac import (
    ABSENT,
    PRESENT,
    require_terraform_for_l1,
    resolve_terraform,
    terraform_status,
)


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


def test_absent_terraform_is_reported_pending_on_an_isolated_path(tmp_path: Path) -> None:
    """The absent-binary branch, exercised regardless of the host's terraform.

    The search path is an empty directory rather than the ambient PATH, so this
    is deterministic on a machine where terraform *is* installed. The previous
    version of this test read the real PATH and failed outright whenever a
    binary was present, which made an installed toolchain look like a defect.
    """

    empty = tmp_path / "empty-bin"
    empty.mkdir()
    assert resolve_terraform(str(empty)) is None
    status = terraform_status(str(empty))
    assert status["status"] == ABSENT
    assert status["terraform_path"] is None
    assert status["l1_validation_available"] is False
    assert status["account_evidence"] is False

    with pytest.raises(CloudManifestError, match="L1 static validation is pending"):
        require_terraform_for_l1(str(empty))


def test_empty_search_path_searches_nowhere(tmp_path: Path) -> None:
    """An empty search path must not silently fall back to the ambient PATH."""

    assert resolve_terraform("") is None
    assert terraform_status("")["status"] == ABSENT


def test_present_terraform_is_reported_available_on_a_mock_path(tmp_path: Path) -> None:
    """The present-binary branch, exercised without needing a real terraform."""

    mock_bin = tmp_path / "mock-bin"
    mock_bin.mkdir()
    stub = mock_bin / "terraform"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    assert resolve_terraform(str(mock_bin)) == str(stub)
    status = terraform_status(str(mock_bin))
    assert status["status"] == PRESENT
    assert status["l1_validation_available"] is True
    # Availability is still not account evidence.
    assert status["account_evidence"] is False
    assert require_terraform_for_l1(str(mock_bin)) == str(stub)


@pytest.mark.skipif(shutil.which("terraform") is None, reason="terraform unavailable: L1 binary validation is environmental")
def test_real_terraform_passes_the_credential_free_format_check() -> None:
    """Environmental L1 check: runs only where a real binary exists.

    `fmt -check` reads no credentials and contacts no provider. Skipping this
    where terraform is absent is honest reporting, not a masked failure — the
    two tests above already pin the decision logic deterministically.
    """

    terraform = require_terraform_for_l1(os.environ.get("PATH", ""))
    subprocess.run([terraform, "fmt", "-check", "-recursive"], cwd=ROOT, check=True, timeout=60)
