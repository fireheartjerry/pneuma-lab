"""Manifest-frozen authority for post-trigger synthetic branch programs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .authority_refs import closed_mapping, decode_artifact_ref, exact_text, load_json_bytes
from .errors import RecordValidationError
from .types import ArtifactRef


@dataclass(frozen=True, slots=True)
class BranchProgramEntry:
    """One pre-schedule branch ordinal and its frozen execution program."""

    branch_ordinal: int
    program_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class BranchProgramTask:
    """The exact four branch programs frozen for one task."""

    task_id: str
    programs: tuple[
        BranchProgramEntry,
        BranchProgramEntry,
        BranchProgramEntry,
        BranchProgramEntry,
    ]


@dataclass(frozen=True, slots=True)
class BranchProgramRegistry:
    """Canonical task-ordered branch-program authority."""

    tasks: tuple[BranchProgramTask, ...]


def _exact_list(value: object, *, field: str) -> list[object]:
    if type(value) is not list:
        raise RecordValidationError(f"{field} must be an exact array")
    return cast(list[object], value)


def load_branch_program_registry(payload: bytes) -> BranchProgramRegistry:
    """Decode the closed registry without resolving its artifact closure."""

    raw = load_json_bytes(payload, source=Path("<branch-program-registry>"))
    top = closed_mapping(
        raw,
        fields={"record_kind", "schema_version", "tasks"},
        field="branch program registry",
    )
    if top["record_kind"] != "resampling_branch_program_registry_v1":
        raise RecordValidationError("branch program registry record_kind is wrong")
    if top["schema_version"] != "0.1.0":
        raise RecordValidationError("branch program registry schema_version is wrong")
    task_values = _exact_list(top["tasks"], field="branch program registry tasks")
    if not task_values:
        raise RecordValidationError("branch program registry tasks must be non-empty")
    tasks: list[BranchProgramTask] = []
    for task_index, task_value in enumerate(task_values):
        task = closed_mapping(
            task_value,
            fields={"task_id", "programs"},
            field=f"branch program registry tasks[{task_index}]",
        )
        task_id = exact_text(
            task["task_id"],
            field=f"branch program registry tasks[{task_index}].task_id",
        )
        program_values = _exact_list(
            task["programs"],
            field=f"branch program registry tasks[{task_index}].programs",
        )
        if len(program_values) != 4:
            raise RecordValidationError(
                "each branch program task must contain exactly four programs"
            )
        entries: list[BranchProgramEntry] = []
        for ordinal, entry_value in enumerate(program_values):
            entry = closed_mapping(
                entry_value,
                fields={"branch_ordinal", "program_ref"},
                field=f"branch program task {task_id!r} programs[{ordinal}]",
            )
            if type(entry["branch_ordinal"]) is not int or entry["branch_ordinal"] != ordinal:
                raise RecordValidationError(
                    "branch program ordinals must equal canonical positions 0..3"
                )
            program_ref = decode_artifact_ref(
                entry["program_ref"],
                field=f"branch program task {task_id!r} programs[{ordinal}].program_ref",
                expected_role="synthetic_execution_program",
            )
            if program_ref.media_type != "application/json":
                raise RecordValidationError(
                    "branch execution program must use application/json"
                )
            entries.append(BranchProgramEntry(ordinal, program_ref))
        tasks.append(
            BranchProgramTask(
                task_id=task_id,
                programs=cast(
                    tuple[
                        BranchProgramEntry,
                        BranchProgramEntry,
                        BranchProgramEntry,
                        BranchProgramEntry,
                    ],
                    tuple(entries),
                ),
            )
        )
    task_ids = [task.task_id for task in tasks]
    if task_ids != sorted(task_ids) or len(task_ids) != len(set(task_ids)):
        raise RecordValidationError(
            "branch program registry tasks must be unique and canonically ordered"
        )
    return BranchProgramRegistry(tasks=tuple(tasks))
