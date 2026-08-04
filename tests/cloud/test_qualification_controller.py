from __future__ import annotations

import json
from pathlib import Path
import stat

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.qualification_controller import (
    QualificationController,
    QualificationStateStore,
)


def binding(action_id: str = "dual-l40s-qualification-test") -> dict[str, object]:
    return {
        "action_id": action_id,
        "region": "us-east-1",
        "terraform_plan_binding_sha256": "a" * 64,
        "output_root": f"s3://bucket/runs/qualification/{action_id}/outputs/",
    }


def test_state_history_is_atomic_mode_600_and_restartable(tmp_path: Path) -> None:
    path = tmp_path / "controller-state.json"
    first = QualificationController(
        QualificationStateStore(path, action_id=binding()["action_id"], binding=binding())
    )
    assert first.start_or_resume().phase == "prepared"
    first.transition("applying")
    first.transition("applied")
    first.transition("ready")
    first.transition("submitting")
    submitted = first.transition(
        "submitted",
        {
            "parent_job_id": "parent-1",
            "child_job_ids": ["parent-1:0", "parent-1:1"],
            "submit_count": 1,
        },
    )
    assert submitted.parent_job_id == "parent-1"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600

    restarted = QualificationController(
        QualificationStateStore(path, action_id=binding()["action_id"], binding=binding())
    )
    resumed = restarted.start_or_resume()
    assert resumed.phase == "submitted"
    assert resumed.parent_job_id == "parent-1"
    assert resumed.child_job_ids == ("parent-1:0", "parent-1:1")
    assert resumed.resume_count == 1
    assert resumed.state_sha256 != submitted.state_sha256


def test_state_rejects_tampering_and_invalid_transitions(tmp_path: Path) -> None:
    path = tmp_path / "controller-state.json"
    store = QualificationStateStore(path, action_id=binding()["action_id"], binding=binding())
    store.start()
    with pytest.raises(CloudManifestError, match="invalid qualification controller transition"):
        store.append("submitted", {"parent_job_id": "parent"})

    document = json.loads(path.read_text(encoding="utf-8"))
    document["events"][0]["payload"] = {"tampered": True}
    path.write_text(json.dumps(document), encoding="utf-8")
    path.chmod(0o600)
    with pytest.raises(CloudManifestError, match="event digest differs"):
        QualificationStateStore(path, action_id=binding()["action_id"], binding=binding())
