"""Cheap local canary for the durable qualification controller.

This is deliberately a control-plane-only rehearsal.  It exercises the same
persisted controller and restart path as the AWS runner without contacting AWS,
creating resources, or materializing any worker/model workload.
"""

from __future__ import annotations

import json
from pathlib import Path
import stat
import tempfile
from typing import Any

from pneuma_lab.cloud.qualification_controller import (
    QualificationController,
    QualificationStateStore,
)


class CanaryControlPlane:
    def __init__(self) -> None:
        self.parent: str | None = None
        self.submit_count = 0
        self.describe_failures_remaining = 3

    def reconcile_submission(self) -> str | None:
        return self.parent

    def submit(self) -> str:
        if self.parent is not None:
            raise AssertionError("canary attempted a duplicate Batch submission")
        self.submit_count += 1
        self.parent = "canary-parent"
        return self.parent

    def describe_and_reconcile(self) -> dict[str, Any]:
        if self.describe_failures_remaining:
            self.describe_failures_remaining -= 1
            raise RuntimeError("injected unclassified describe-jobs failure")
        return {
            "parent_status": "SUCCEEDED",
            "child_statuses": ["SUCCEEDED", "SUCCEEDED"],
            "worker_indices": [0, 1],
        }


def _store(path: Path, binding: dict[str, Any]) -> QualificationStateStore:
    return QualificationStateStore(
        path,
        action_id=binding["action_id"],
        binding=binding,
    )


def run_canary() -> dict[str, Any]:
    binding: dict[str, Any] = {
        "action_id": "dual-l40s-controller-canary-001",
        "region": "us-east-1",
        "fixture_only": True,
        "max_retries": 0,
    }
    control = CanaryControlPlane()
    with tempfile.TemporaryDirectory(prefix="pneuma-controller-canary-") as directory:
        state_path = Path(directory) / "state.json"
        controller = QualificationController(_store(state_path, binding))
        controller.start_or_resume({"fixture_only": True})
        for phase in ("applying", "applied", "ready", "submitting"):
            controller.transition(phase, {"fixture_only": True})
        parent = control.reconcile_submission() or control.submit()
        controller.transition(
            "submitted",
            {"parent_job_id": parent, "child_job_ids": [f"{parent}:0", f"{parent}:1"]},
        )
        controller.transition(
            "launch_reconciled",
            {"parent_job_id": parent, "child_job_ids": [f"{parent}:0", f"{parent}:1"]},
        )
        controller.transition("observing", {"parent_job_id": parent})

        for failure_index in range(3):
            try:
                control.describe_and_reconcile()
            except RuntimeError as exc:
                controller.transition(
                    "observation_pending",
                    {
                        "stage": "admission",
                        "failure_index": failure_index,
                        "error": str(exc),
                        "parent_job_id": parent,
                        "child_job_ids": [f"{parent}:0", f"{parent}:1"],
                        "resumed": failure_index > 0,
                    },
                )
            if failure_index < 2:
                restarted = QualificationController(_store(state_path, binding))
                restarted.start_or_resume()
                restarted.transition(
                    "observing",
                    {
                        "resumed": True,
                        "parent_job_id": parent,
                        "child_job_ids": [f"{parent}:0", f"{parent}:1"],
                    },
                )
                controller = restarted

        restarted = QualificationController(_store(state_path, binding))
        restarted.start_or_resume()
        assert restarted.snapshot.parent_job_id == parent
        assert control.reconcile_submission() == parent
        restarted.transition(
            "observing",
            {
                "resumed": True,
                "parent_job_id": parent,
                "child_job_ids": [f"{parent}:0", f"{parent}:1"],
            },
        )
        admission = control.describe_and_reconcile()
        restarted.transition("admission_reconciled", admission)
        restarted.transition("artifact_reconciled", {"worker_indices": [0, 1]})
        restarted.transition("recovering", {"parent_job_id": parent})
        restarted.transition(
            "recovery_reconciled",
            {"restored_completed_boundary": True},
        )
        restarted.transition("teardown_started", {"explicit": True})
        restarted.transition("teardown_complete", {"absence_proven": True})
        mode = stat.S_IMODE(state_path.stat().st_mode)
        if mode != 0o600:
            raise AssertionError(f"canary state mode is {oct(mode)}, expected 0o600")
        result = {
            "record_kind": "cloud_qualification_controller_canary",
            "schema_version": "0.1.0",
            "status": "passed",
            "aws_calls": 0,
            "submit_count": control.submit_count,
            "injected_describe_failures": 3,
            "duplicate_submit": False,
            "teardown_after_reconciliation": True,
            "controller_state": restarted.snapshot.summary(),
        }
    return result


if __name__ == "__main__":
    print(json.dumps(run_canary(), sort_keys=True))
