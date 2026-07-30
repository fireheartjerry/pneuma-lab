"""Capability boundary tests for the blinded projection candidate."""

from __future__ import annotations

import subprocess
import sys

import pytest


pytestmark = pytest.mark.milestone


def test_candidate_module_is_capability_minimal_in_a_clean_subprocess() -> None:
    program = """
import ast
import inspect
import pneuma_lab.resampling_null.projection_candidate as candidate
source = inspect.getsource(candidate)
tree = ast.parse(source)
names = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
names |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
for forbidden in ('pathlib', 'artifacts', 'assignment', 'secrets', 'packets'):
    assert not any(forbidden in name for name in names), names
assert 'BranchOutcome' not in source
assert 'Arm' not in source
"""
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr


def test_candidate_sorts_schedule_and_strips_outcomes() -> None:
    from pneuma_lab.resampling_null.projection_candidate import build_candidate

    candidate = build_candidate(
        [
            {"task_id": "z", "prefix_success": 1, "slot_ids": ["z0", "z1", "z2", "z3"]},
            {"task_id": "a", "prefix_success": 0, "slot_ids": ["a0", "a1", "a2", "a3"]},
        ],
        {
            "a": [{"success": 0, "prefix_success": 0, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}] * 4,
            "z": [{"success": 1, "prefix_success": 1, "partial_reward": 1.0, "infrastructure_failure": False, "counters": {"generated_tokens": 1, "model_calls": 1, "tool_calls": 0, "wall_clock_ms": 1}}] * 4,
        },
    )

    assert [row["task_id"] for row in candidate.rows] == ["a", "z"]
    assert [slot["label"] for slot in candidate.rows[0]["slots"]] == ["A", "B", "C", "D"]
    assert "artifact_ref" not in repr(candidate.rows)


def test_candidate_rejects_prefix_mismatch_and_incomplete_coverage() -> None:
    from pneuma_lab.resampling_null.projection_candidate import build_candidate

    row = {"task_id": "a", "prefix_success": 0, "slot_ids": ["0", "1", "2", "3"]}
    outcome = {"success": 1, "prefix_success": 1, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}
    with pytest.raises(ValueError, match="coverage"):
        build_candidate([row], {})
    with pytest.raises(ValueError, match="prefix"):
        build_candidate([row], {"a": [outcome] * 4})


def test_trusted_sealer_is_not_exposed_by_the_candidate_module() -> None:
    import pneuma_lab.resampling_null.projection_candidate as candidate
    from pneuma_lab.resampling_null.blinding import seal_blinded_projection

    assert not hasattr(candidate, "seal_blinded_projection")
    assert callable(seal_blinded_projection)
