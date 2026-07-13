"""Repository and issue/PR evaluation disjointness is mandatory."""

from __future__ import annotations

from pneuma_lab.foundation.contamination import contamination_findings


def test_contamination_detects_repo_issue_task_commit_and_patch_overlap() -> None:
    train = (
        {
            "repo": "Org/Repo",
            "issue_or_pr": "12",
            "task_id": "task-a",
            "base_commit": "abc",
            "patch": "patch-a",
            "test_patch": "test-a",
            "text": "fix the parser",
        },
    )
    evaluation = (
        {
            "repo": "org/repo",
            "issue_or_pr": "12",
            "task_id": "task-b",
            "base_commit": "def",
            "patch": "patch-b",
            "test_patch": "test-b",
            "text": "different task",
        },
    )
    findings = contamination_findings(train, evaluation)
    assert {finding.dimension for finding in findings} == {"repo", "repo_issue_or_pr"}


def test_contamination_accepts_proven_disjoint_sets() -> None:
    train = ({"repo": "org/a", "issue_or_pr": "1", "task_id": "a"},)
    evaluation = ({"repo": "org/b", "issue_or_pr": "1", "task_id": "b"},)
    assert contamination_findings(train, evaluation) == ()
