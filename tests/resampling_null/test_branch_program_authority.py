from __future__ import annotations

import json

import pytest

from pneuma_lab.resampling_null.branch_program_authority import (
    load_branch_program_registry,
)
from pneuma_lab.resampling_null.errors import RecordValidationError


def _ref(char: str) -> dict[str, object]:
    return {
        "role": "synthetic_execution_program",
        "relative_path": f"sources/program-{char}.json",
        "sha256": char * 64,
        "byte_count": 1,
        "media_type": "application/json",
    }


def _registry() -> dict[str, object]:
    return {
        "record_kind": "resampling_branch_program_registry_v1",
        "schema_version": "0.1.0",
        "tasks": [
            {
                "task_id": "task-1",
                "programs": [
                    {"branch_ordinal": ordinal, "program_ref": _ref(char)}
                    for ordinal, char in enumerate("1234")
                ],
            }
        ],
    }


def _bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def test_branch_program_registry_decodes_exact_task_and_ordinal_order() -> None:
    registry = load_branch_program_registry(_bytes(_registry()))

    assert [row.task_id for row in registry.tasks] == ["task-1"]
    assert [entry.branch_ordinal for entry in registry.tasks[0].programs] == [
        0,
        1,
        2,
        3,
    ]
    assert [entry.program_ref.sha256 for entry in registry.tasks[0].programs] == [
        char * 64 for char in "1234"
    ]


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_ordinal",
        "duplicate_ordinal",
        "reordered_ordinal",
        "fifth_ordinal",
        "wrong_role",
        "wrong_media",
        "open_top",
        "open_task",
        "open_entry",
    ),
)
def test_branch_program_registry_rejects_hostile_shapes(mutation: str) -> None:
    value = _registry()
    task = value["tasks"][0]
    programs = task["programs"]
    if mutation == "missing_ordinal":
        programs.pop()
    elif mutation == "duplicate_ordinal":
        programs[1]["branch_ordinal"] = 0
    elif mutation == "reordered_ordinal":
        programs[0], programs[1] = programs[1], programs[0]
    elif mutation == "fifth_ordinal":
        programs.append({"branch_ordinal": 4, "program_ref": _ref("5")})
    elif mutation == "wrong_role":
        programs[0]["program_ref"]["role"] = "task_input"
    elif mutation == "wrong_media":
        programs[0]["program_ref"]["media_type"] = "text/plain"
    elif mutation == "open_top":
        value["extra"] = None
    elif mutation == "open_task":
        task["extra"] = None
    else:
        programs[0]["extra"] = None

    with pytest.raises(RecordValidationError):
        load_branch_program_registry(_bytes(value))


@pytest.mark.parametrize("mutation", ("duplicate", "reordered"))
def test_branch_program_registry_requires_canonical_unique_task_order(
    mutation: str,
) -> None:
    value = _registry()
    second = {
        "task_id": "task-2",
        "programs": [
            {"branch_ordinal": ordinal, "program_ref": _ref(char)}
            for ordinal, char in enumerate("5678")
        ],
    }
    value["tasks"].append(second)
    if mutation == "duplicate":
        second["task_id"] = "task-1"
    else:
        value["tasks"].reverse()

    with pytest.raises(RecordValidationError):
        load_branch_program_registry(_bytes(value))
