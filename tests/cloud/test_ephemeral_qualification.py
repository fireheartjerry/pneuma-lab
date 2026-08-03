from __future__ import annotations

from pathlib import Path
import re

import pytest

from pneuma_lab.cloud.ephemeral_qualification import (
    require_cost_ceiling,
    require_teardown_complete,
    require_two_workers,
    require_watchdog,
    validate_plan,
)
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.ephemeral_runner import EXPECTED_RESOURCE_ADDRESSES


ROOT = Path(__file__).resolve().parents[2]


def plan() -> dict[str, object]:
    namespace = {}
    exec(
        (ROOT / "scripts/research/ephemeral_dual_worker_qualification.py").read_text(),
        namespace,
    )
    return namespace["qualification_plan"]()


def test_plan_binds_two_workers_zero_retry_and_hard_bounds() -> None:
    validate_plan(plan())
    assert plan()["worker_count"] == 2
    assert plan()["max_retries"] == 0


@pytest.mark.parametrize(
    "field,value", [("worker_count", 1), ("max_retries", 1), ("total_spot_vcpus", 8)]
)
def test_plan_rejects_topology_or_retry_changes(field: str, value: object) -> None:
    candidate = plan()
    candidate[field] = value
    with pytest.raises(CloudManifestError):
        validate_plan(candidate)


def test_two_worker_cardinality_is_exact() -> None:
    assert require_two_workers(("i-a", "i-b")) == ("i-a", "i-b")
    with pytest.raises(CloudManifestError):
        require_two_workers(("i-a",))
    with pytest.raises(CloudManifestError):
        require_two_workers(("i-a", "i-a"))


def test_watchdog_rejects_expiry_and_wrong_limit() -> None:
    require_watchdog(started_at=100, now=200)
    with pytest.raises(CloudManifestError):
        require_watchdog(started_at=100, now=3700)
    with pytest.raises(CloudManifestError):
        require_watchdog(started_at=100, now=200, runtime_limit_seconds=60)


def test_cost_ceiling_is_independent_of_budget_alerts() -> None:
    require_cost_ceiling(projected_cost_usd=99.99, observed_cost_usd=20)
    with pytest.raises(CloudManifestError):
        require_cost_ceiling(projected_cost_usd=100.01)


def test_teardown_requires_post_destroy_absence() -> None:
    require_teardown_complete({"resources_absent": True, "provider_errors": []})
    with pytest.raises(CloudManifestError):
        require_teardown_complete({"resources_absent": False, "provider_errors": []})


def test_ephemeral_stack_has_destroyable_watchdog_and_no_retry_contract() -> None:
    text = (ROOT / "infra/terraform/qualification/main.tf").read_text()
    assert re.search(r"max_vcpus\s*=\s*16", text)
    assert 'allocation_strategy = "SPOT_PRICE_CAPACITY_OPTIMIZED"' in text
    assert "attempt_duration_seconds = 3600" in text
    assert "attempts = 1" in text
    dockerfile = (ROOT / "infra/docker/qualification-worker/Dockerfile").read_text()
    assert "fixed_admission_entrypoint.sh" in dockerfile
    assert "qualification-entrypoint" not in dockerfile
    assert "prevent_destroy" not in text


def test_ephemeral_plan_guard_names_exactly_four_owned_resources() -> None:
    hcl = (ROOT / "infra/terraform/qualification/main.tf").read_text()
    addresses = {
        f"{kind}.{name}"
        for kind, name in re.findall(r'resource\s+"([^"]+)"\s+"([^"]+)"', hcl)
    }
    assert addresses == EXPECTED_RESOURCE_ADDRESSES
    assert "aws_launch_template.qualification" in addresses
    assert len(addresses) == 4


def test_image_and_batch_command_bind_fixed_probe_and_distinct_outputs() -> None:
    dockerfile = (ROOT / "infra/docker/qualification-worker/Dockerfile").read_text()
    hcl = (ROOT / "infra/terraform/qualification/main.tf").read_text()
    adapter = (ROOT / "src/pneuma_lab/cloud/fixed_admission_probe.py").read_text()
    probe = (ROOT / "src/pneuma_lab/cloud/dual_worker_admission_probe.py").read_text()
    assert "COPY src/pneuma_lab /opt/pneuma/pneuma_lab" in dockerfile
    assert 'ENTRYPOINT ["/opt/pneuma/fixed_admission_entrypoint.sh"]' in dockerfile
    assert "command = []" not in hcl
    assert 'value = "60000"' in hcl
    assert "qualification_action_id" in hcl
    assert 'name = "QUALIFICATION_CODE"' in hcl
    assert 'name = "QUALIFICATION_ACTION_ID"' in hcl
    assert 'resource_type = "volume"' in hcl
    assert "QualificationActionId" in hcl
    assert "worker-{raw_index}" in adapter
    assert '"--code"' in adapter
    assert "_WATCHDOG_SECONDS = 3500" in probe
