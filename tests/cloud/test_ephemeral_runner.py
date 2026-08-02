from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import subprocess
import json

import pytest

from pneuma_lab.cloud.ephemeral_runner import (
    EXPECTED_RESOURCE_ADDRESSES,
    RunnerConfig,
    AwsCliAdapter,
    TerraformAdapter,
    execute,
    require_account_plan,
    terraform_mutation_commands,
)
from pneuma_lab.cloud.errors import CloudManifestError


def account_plan() -> dict[str, object]:
    return {
        "plan_sha256": "a" * 64,
        "spend_history_sha256": "b" * 64,
        "qualification_action_id": "qual-1",
        "resource_changes": [
            {"address": address, "actions": ["create"]}
            for address in sorted(EXPECTED_RESOURCE_ADDRESSES)
        ],
        "approved_existing_inputs": {
            "roles": True,
            "subnets": True,
            "security_groups": True,
        },
    }


@dataclass
class FakeProvider:
    calls: list[str] = field(default_factory=list)
    projection: float = 99.0

    def preflight(self, tags):
        self.calls.append("preflight")
        return {"ok": True}

    def pricing_projection(self, *, worker_seconds):
        self.calls.append("pricing")
        return self.projection

    def submit_array(self, *, size, timeout_seconds, attempts, tags):
        self.calls.append(f"submit:{size}:{timeout_seconds}:{attempts}")
        assert size == 2 and timeout_seconds == 3600 and attempts == 1
        return "parent"

    def collect_admission(self, parent_job_id):
        self.calls.append("collect")
        return {"instance_ids": ("i-a", "i-b"), "raw_evidence": {0: b"a", 1: b"b"}}

    def run_partition_recovery(self, parent_job_id):
        self.calls.append("recovery")
        return {"restored_completed_boundary": True}

    def disable_and_drain(self, tags):
        self.calls.append("disable-drain")

    def verify_absence(self, tags):
        self.calls.append("absence")
        return {
            key: True
            for key in (
                "jobs",
                "instances",
                "volumes",
                "job_definition",
                "queue",
                "compute_environment",
            )
        }


@dataclass
class FakeTerraform:
    calls: list[str] = field(default_factory=list)

    def apply(self, *, lock_timeout, tags):
        self.calls.append(f"apply:{lock_timeout}")

    def destroy(self, *, lock_timeout, tags):
        self.calls.append(f"destroy:{lock_timeout}")


def authority(*args, **kwargs):
    assert kwargs["expected_max_retries"] == 0
    return {"authorized": True}


def test_runner_verifies_authority_then_submits_one_array_and_tears_down() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()
    result = execute(
        RunnerConfig("qual-1", "us-east-1"),
        envelope={},
        admission={},
        key_registry={},
        ledger_path=None,
        account_plan=account_plan(),
        provider=provider,
        terraform=terraform,
        verify_authority=authority,
    )
    assert result["qualification_only"] is True
    assert provider.calls == [
        "pricing",
        "preflight",
        "submit:2:3600:1",
        "collect",
        "recovery",
        "disable-drain",
        "absence",
    ]
    assert terraform.calls == ["apply:60s", "destroy:60s"]


def test_invalid_account_plan_fails_before_provider_or_terraform_mutation() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()
    bad = account_plan()
    bad["resource_changes"] = bad["resource_changes"][:-1]
    with pytest.raises(CloudManifestError):
        execute(
            RunnerConfig("qual-1", "us-east-1"),
            envelope={},
            admission={},
            key_registry={},
            ledger_path=None,
            account_plan=bad,
            provider=provider,
            terraform=terraform,
            verify_authority=authority,
        )
    assert provider.calls == [] and terraform.calls == []


def test_cost_bound_and_recovery_are_fail_closed() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()
    provider.projection = 100.01
    with pytest.raises(CloudManifestError):
        execute(
            RunnerConfig("qual-1", "us-east-1"),
            envelope={},
            admission={},
            key_registry={},
            ledger_path=None,
            account_plan=account_plan(),
            provider=provider,
            terraform=terraform,
            verify_authority=authority,
        )
    with pytest.raises(CloudManifestError):
        execute(
            RunnerConfig("qual-1", "us-east-1"),
            envelope={},
            admission={},
            key_registry={},
            ledger_path=None,
            account_plan=account_plan(),
            provider=provider,
            terraform=terraform,
            verify_authority=authority,
        )


def test_future_terraform_mutations_use_lock_timeout_not_lock_false() -> None:
    apply, destroy = terraform_mutation_commands()
    assert "-lock=false" not in apply + destroy
    assert "-lock-timeout=60s" in apply and "-lock-timeout=60s" in destroy


def test_apply_failure_still_attempts_destroy_and_absence_readback() -> None:
    provider, terraform = FakeProvider(), FakeTerraform()

    def fail_apply(*, lock_timeout, tags):
        terraform.calls.append(f"apply:{lock_timeout}")
        raise RuntimeError("partial apply")

    terraform.apply = fail_apply  # type: ignore[method-assign]
    with pytest.raises(CloudManifestError, match="qualification failed closed"):
        execute(
            RunnerConfig("qual-1", "us-east-1"),
            envelope={},
            admission={},
            key_registry={},
            ledger_path=None,
            account_plan=account_plan(),
            provider=provider,
            terraform=terraform,
            verify_authority=authority,
        )
    assert terraform.calls == ["apply:60s", "destroy:60s"]
    assert provider.calls[-2:] == ["disable-drain", "absence"]


def test_account_plan_rejects_non_qualification_resource() -> None:
    bad = account_plan()
    bad["resource_changes"] = [
        {"address": "aws_instance.unapproved", "actions": ["create"]}
    ]
    with pytest.raises(CloudManifestError):
        require_account_plan(bad)


def test_terraform_adapter_hashes_exact_plan_and_applies_that_path(
    tmp_path: Path,
) -> None:
    plan_path = tmp_path / "saved.tfplan"
    plan_path.write_bytes(b"exact-plan-bytes")
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if argv[2] == "show":
            payload = account_plan()
            return subprocess.CompletedProcess(
                argv, 0, json.dumps(payload).encode(), b""
            )
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    adapter = TerraformAdapter(run)
    plan = adapter.load_account_plan(plan_path)
    assert plan["plan_sha256"] == hashlib.sha256(b"exact-plan-bytes").hexdigest()
    adapter.apply(lock_timeout="60s", tags={})
    assert calls[0][2:4] == ["show", "-json"]
    assert str(plan_path) in calls[1]
    assert "-lock=false" not in calls[1]


def test_aws_adapter_submission_is_one_tagged_size_two_array() -> None:
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, b'{"jobId":"parent"}', b"")

    adapter = AwsCliAdapter(
        run,
        region="us-east-1",
        queue="q",
        job_definition="d",
        output_root="s3://bucket/run",
    )
    assert (
        adapter.submit_array(
            size=2,
            timeout_seconds=3600,
            attempts=1,
            tags={"QualificationAction": "qual-1"},
        )
        == "parent"
    )
    command = " ".join(calls[0])
    assert '--array-properties {"size":2}' in command
    assert '--retry-strategy {"attempts":1}' in command
    assert "qual-1" in command
