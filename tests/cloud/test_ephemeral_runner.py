from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from pneuma_lab.cloud.ephemeral_runner import (
    EXPECTED_RESOURCE_ADDRESSES,
    RunnerConfig,
    execute,
    require_account_plan,
    terraform_mutation_commands,
)
from pneuma_lab.cloud.errors import CloudManifestError


def account_plan() -> dict[str, object]:
    return {
        "plan_sha256": "a" * 64,
        "spend_history_sha256": "b" * 64,
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

    def preflight(self, tags):
        self.calls.append("preflight")
        return {"ok": True}

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
        RunnerConfig("qual-1", "us-east-1", 99.0),
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
            RunnerConfig("qual-1", "us-east-1", 99.0),
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
    with pytest.raises(CloudManifestError):
        execute(
            RunnerConfig("qual-1", "us-east-1", 100.01),
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
            RunnerConfig("qual-1", "us-east-1", 100.0),
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


def test_account_plan_rejects_non_qualification_resource() -> None:
    bad = account_plan()
    bad["resource_changes"] = [
        {"address": "aws_instance.unapproved", "actions": ["create"]}
    ]
    with pytest.raises(CloudManifestError):
        require_account_plan(bad)
