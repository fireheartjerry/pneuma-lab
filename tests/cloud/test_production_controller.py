from __future__ import annotations

import stat
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.production_controller import (
    ProductionOrchestrator,
    ProductionStateStore,
    ProductionSubmission,
)


def test_production_controller_is_restartable_and_preserves_submission_on_observation_error(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "controller.json"
    binding = {"action_id": "official-study-test-001", "run_spec_sha256": "a" * 64}
    store = ProductionStateStore(
        state_path,
        action_id="official-study-test-001",
        run_spec_sha256="a" * 64,
        binding=binding,
    )
    assert store.prepare({"allocation": {"worker-0": ["a"], "worker-1": ["b"]}}).phase == "prepared"
    submitted = store.submit_once(parent_job_id="parent-1", child_job_ids=("child-0", "child-1"))
    assert submitted.phase == "submitted"
    restarted = ProductionStateStore(
        state_path,
        action_id="official-study-test-001",
        run_spec_sha256="a" * 64,
        binding=binding,
    )
    errored = restarted.record_observation_error(detail_sha256="b" * 64)
    assert errored.parent_job_id == "parent-1"
    assert errored.child_job_ids == ("child-0", "child-1")
    assert restarted.submit_once(parent_job_id="parent-1", child_job_ids=("child-0", "child-1")).phase == "observation_error"
    with pytest.raises(CloudManifestError, match="immutable first submission"):
        restarted.submit_once(parent_job_id="parent-2", child_job_ids=("child-0", "child-1"))
    assert restarted.teardown(success=True).phase == "teardown_complete"
    assert stat.S_IMODE(state_path.stat().st_mode) == 0o600


class _Provider:
    def __init__(self) -> None:
        self.submit_count = 0

    def submit(self, *, client_token: str, allocation: dict[str, tuple[str, ...]]) -> ProductionSubmission:
        assert client_token.startswith("pneuma-production-")
        assert len(client_token) <= 64
        assert allocation == {"worker-0": ("a",), "worker-1": ("b",)}
        self.submit_count += 1
        return ProductionSubmission("parent-1", ("child-0", "child-1"))

    def observe(self, submission: ProductionSubmission) -> dict[str, object]:
        assert submission.parent_job_id == "parent-1"
        return {"terminal": True, "provider_state": "SUCCEEDED"}

    def teardown(self, submission: ProductionSubmission | None) -> dict[str, object]:
        assert submission is not None
        return {"absent": True}


def test_production_orchestrator_uses_provider_idempotency_and_terminal_teardown(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "controller.json"
    kwargs = {
        "action_id": "official-study-test-002",
        "run_spec_sha256": "c" * 64,
        "binding": {"action_id": "official-study-test-002", "run_spec_sha256": "c" * 64},
    }
    provider = _Provider()
    first = ProductionOrchestrator(
        ProductionStateStore(state_path, **kwargs),
        action_id=kwargs["action_id"],
        run_spec_sha256=kwargs["run_spec_sha256"],
        allocation={"worker-0": ("a",), "worker-1": ("b",)},
    )
    assert first.submit(provider).phase == "submitted"
    restarted = ProductionOrchestrator(
        ProductionStateStore(state_path, **kwargs),
        action_id=kwargs["action_id"],
        run_spec_sha256=kwargs["run_spec_sha256"],
        allocation={"worker-0": ("a",), "worker-1": ("b",)},
    )
    assert restarted.submit(provider).phase == "submitted"
    assert provider.submit_count == 1
    assert restarted.observe(provider).phase == "workload_terminal"
    assert restarted.teardown(provider).phase == "teardown_complete"
