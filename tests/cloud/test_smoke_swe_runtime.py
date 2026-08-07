from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "smoke_swe_runtime", ROOT / "scripts/research/smoke_swe_runtime.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _tasks() -> dict[str, dict[str, object]]:
    return {
        "swe:a__a-1": {"task_id": "swe:a__a-1", "language": "c"},
        "swe:b__b-2": {"task_id": "swe:b__b-2", "language": "cpp"},
        "swe:c__c-3": {"task_id": "swe:c__c-3", "language": "c"},
    }


def test_explicit_task_ids_are_selected_in_order() -> None:
    selected = MODULE._select(
        _tasks(), task_ids=["swe:c__c-3", "swe:a__a-1"], language=None, count=1
    )

    assert [row["task_id"] for row in selected] == ["swe:c__c-3", "swe:a__a-1"]


def test_unregistered_task_id_is_rejected() -> None:
    with pytest.raises(SystemExit, match="unregistered task IDs"):
        MODULE._select(_tasks(), task_ids=["swe:missing__x-9"], language=None, count=1)


def test_language_filter_is_bounded_by_count() -> None:
    selected = MODULE._select(_tasks(), task_ids=[], language="c", count=1)

    assert [row["task_id"] for row in selected] == ["swe:a__a-1"]


def test_unknown_language_is_rejected() -> None:
    with pytest.raises(SystemExit, match="no registered tasks for language"):
        MODULE._select(_tasks(), task_ids=[], language="cobol", count=1)


def test_run_root_inside_the_repository_is_refused() -> None:
    """The smoke lane writes parser sandbox IO; keep it out of the tree."""

    with pytest.raises(SystemExit, match="outside the repository"):
        MODULE.main(
            [
                "--task-id",
                "swe:fluent__fluent-bit-10563",
                "--run-root",
                str(ROOT / "build" / "smoke"),
            ]
        )


def test_receipt_is_marked_non_official_and_non_authorizing() -> None:
    """A smoke receipt must never read as an official or scientific artifact."""

    source = (ROOT / "scripts/research/smoke_swe_runtime.py").read_text(
        encoding="utf-8"
    )
    assert '"status": "NON_OFFICIAL_SMOKE"' in source
    assert '"authorizing": False' in source
    assert '"scientific_result": False' in source
    assert "runs/official" not in source.split('"""', 2)[2]
