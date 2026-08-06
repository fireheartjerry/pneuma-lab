from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "cleanup_official_batch", ROOT / "scripts/research/cleanup_official_batch.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_cleanup_refuses_a_resource_from_another_action() -> None:
    value = {"Tags": [{"Key": "ActionId", "Value": "action-a"}]}
    MODULE._require_owned(value, "action-a", "test resource")
    with pytest.raises(RuntimeError, match="non-owned"):
        MODULE._require_owned(value, "action-b", "test resource")


def test_official_cleanup_has_terminal_only_job_policy() -> None:
    assert MODULE.TERMINAL_JOB_STATES == {"SUCCEEDED", "FAILED"}
    assert set(MODULE.ACTIVE_JOB_STATES).isdisjoint(MODULE.TERMINAL_JOB_STATES)
