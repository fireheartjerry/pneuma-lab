"""Stop paths: unauthorized, blocked, drifted, signaled, and guarded runs."""

from __future__ import annotations

import dataclasses
import json
import subprocess
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.authorization import (  # noqa: E402
    FoundationAuthorizationError,
)
from pneuma_lab.foundation.checkpoints import CheckpointError  # noqa: E402
from pneuma_lab.foundation.runner import (  # noqa: E402
    FoundationRunError,
    PauseSignal,
    assert_clean_commit,
    resume_foundation_training,
    run_foundation_training,
)

from test_foundation_runner import (  # noqa: E402
    _run_request,
    _runner_dependencies,
)


def test_unauthorized_train_stops_before_cache_model_or_optimizer(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    deps = _runner_dependencies(calls, authorization_error="not authorized")
    with pytest.raises(FoundationAuthorizationError, match="not authorized"):
        run_foundation_training(_run_request(tmp_path), dependencies=deps)
    assert calls == ["verify_authorization"]


def test_unauthorized_resume_stops_before_cache_model_or_optimizer(
    tmp_path: Path,
) -> None:
    calls: list[str] = []
    deps = _runner_dependencies(calls, authorization_error="not authorized")
    request = dataclasses.replace(
        _run_request(tmp_path),
        checkpoint_path=tmp_path / "checkpoint.pt",
    )
    with pytest.raises(FoundationAuthorizationError, match="not authorized"):
        resume_foundation_training(request, dependencies=deps)
    assert calls == ["verify_authorization"]


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [("pause", "paused"), ("fail", "failed")],
)
def test_runner_stops_at_safe_boundary_and_checkpoints(
    decision: str,
    expected_status: str,
    tmp_path: Path,
) -> None:
    result = run_foundation_training(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(resource_action=decision),
    )
    assert result.status == expected_status
    assert result.last_checkpoint is not None
    assert result.last_checkpoint.exists()
    assert result.progress.microbatch % 32 == 0


@pytest.mark.parametrize(
    ("decision", "expected_status", "expected_reason"),
    [("pause", "paused", "gpu_temperature"), ("fail", "failed", "disk_risk")],
)
def test_stopped_runs_record_the_guard_reason_in_the_manifest(
    decision: str,
    expected_status: str,
    expected_reason: str,
    tmp_path: Path,
) -> None:
    result = run_foundation_training(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(resource_action=decision),
    )
    manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == expected_status
    assert manifest["termination_reason"] == expected_reason
    assert manifest["checkpoints"]["last_path"] == str(result.last_checkpoint)


def test_execution_profile_outside_scope_stops_immediately(tmp_path: Path) -> None:
    calls: list[str] = []
    with pytest.raises(FoundationRunError, match="execution profile"):
        run_foundation_training(
            _run_request(tmp_path, execution_profile="cloud"),
            dependencies=_runner_dependencies(calls),
        )
    assert calls == ["verify_authorization"]


def test_stage_outside_scope_stops_immediately(tmp_path: Path) -> None:
    calls: list[str] = []
    with pytest.raises(FoundationRunError, match="stage"):
        run_foundation_training(
            _run_request(tmp_path, stage="500k"),
            dependencies=_runner_dependencies(calls),
        )
    assert calls == ["verify_authorization"]


def test_dirty_commit_stops_before_cache_verification(tmp_path: Path) -> None:
    calls: list[str] = []
    with pytest.raises(FoundationRunError, match="dirty"):
        run_foundation_training(
            _run_request(tmp_path),
            dependencies=_runner_dependencies(
                calls,
                clean_commit_error="code commit is dirty",
            ),
        )
    assert calls == ["verify_authorization", "clean_commit"]


def test_blocked_environment_never_allocates(tmp_path: Path) -> None:
    calls: list[str] = []
    with pytest.raises(FoundationRunError, match="environment is blocked"):
        run_foundation_training(
            _run_request(tmp_path),
            dependencies=_runner_dependencies(calls, environment_ready=False),
        )
    assert calls == [
        "verify_authorization",
        "clean_commit",
        "verify_cache",
        "environment_probe",
    ]


def test_unapproved_learning_rate_never_allocates(tmp_path: Path) -> None:
    calls: list[str] = []
    with pytest.raises(FoundationRunError, match="learning rate"):
        run_foundation_training(
            _run_request(tmp_path, learning_rate=0.001),
            dependencies=_runner_dependencies(calls),
        )
    assert "load_model" not in calls
    assert "build_optimizer" not in calls


def test_operator_signal_pauses_at_next_boundary_with_checkpoint(
    tmp_path: Path,
) -> None:
    pause = PauseSignal()
    pause.request()
    result = run_foundation_training(
        _run_request(tmp_path),
        dependencies=_runner_dependencies(record_count=64, tokens_per_call=25),
        pause_signal=pause,
    )
    assert result.status == "paused"
    # The handler only sets a flag; the run still finishes the accumulation
    # window and stops at the first safe optimizer boundary.
    assert result.progress.optimizer_step == 1
    assert result.progress.microbatch == 32
    assert result.last_checkpoint is not None
    manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "paused"
    assert manifest["termination_reason"] == "operator_interrupt"


def test_resume_requires_a_checkpoint_path(tmp_path: Path) -> None:
    with pytest.raises(FoundationRunError, match="checkpoint"):
        resume_foundation_training(
            _run_request(tmp_path),
            dependencies=_runner_dependencies(),
        )


def test_resume_rejects_authorization_drift(tmp_path: Path) -> None:
    request = _run_request(tmp_path)
    paused = run_foundation_training(
        request,
        dependencies=_runner_dependencies(resource_action="pause"),
    )
    assert paused.status == "paused"
    assert paused.last_checkpoint is not None
    drifted = _runner_dependencies(scope_digest="2" * 64)
    with pytest.raises(CheckpointError, match="authorization_digest"):
        resume_foundation_training(
            dataclasses.replace(request, checkpoint_path=paused.last_checkpoint),
            dependencies=drifted,
        )


def test_resume_rejects_a_changed_learning_rate(tmp_path: Path) -> None:
    request = _run_request(tmp_path)
    paused = run_foundation_training(
        request,
        dependencies=_runner_dependencies(resource_action="pause"),
    )
    assert paused.last_checkpoint is not None
    # A different learning rate changes the persisted optimizer definition,
    # so the resume-binding verification rejects it before any restore.
    with pytest.raises(CheckpointError, match="optimizer_definition"):
        resume_foundation_training(
            dataclasses.replace(
                request,
                checkpoint_path=paused.last_checkpoint,
                learning_rate=0.0002,
            ),
            dependencies=_runner_dependencies(),
        )


def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "-c",
            "commit.gpgsign=false",
            *arguments,
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def test_assert_clean_commit_accepts_the_exact_clean_head(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / "file.txt").write_text("content\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "initial")
    head = _git(repo, "rev-parse", "HEAD")
    assert_clean_commit(repo, expected=head)


def test_assert_clean_commit_rejects_dirty_or_different_head(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    (repo / "file.txt").write_text("content\n", encoding="utf-8")
    _git(repo, "add", "file.txt")
    _git(repo, "commit", "-m", "initial")
    head = _git(repo, "rev-parse", "HEAD")
    with pytest.raises(FoundationRunError, match="dirty or differs"):
        assert_clean_commit(repo, expected="0" * 40)
    (repo / "file.txt").write_text("changed\n", encoding="utf-8")
    with pytest.raises(FoundationRunError, match="dirty or differs"):
        assert_clean_commit(repo, expected=head)
