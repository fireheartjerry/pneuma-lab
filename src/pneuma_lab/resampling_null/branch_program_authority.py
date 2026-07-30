"""Manifest-frozen authority for post-trigger synthetic branch programs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .authority_refs import (
    AuthorityRefReader,
    closed_mapping,
    decode_artifact_ref,
    exact_text,
    load_json_bytes,
)
from .errors import RecordValidationError
from .prefix_contracts import load_synthetic_prefix_program
from .types import ArtifactRef, OpaqueSlotWorkOrder, TriggerReason


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


def reconcile_branch_program_refs(
    *,
    registry: BranchProgramRegistry,
    task_id: str,
    scheduled_slots: Sequence[object],
    work_orders: Sequence[OpaqueSlotWorkOrder],
) -> tuple[ArtifactRef, ArtifactRef, ArtifactRef, ArtifactRef]:
    """Bind pre-schedule ordinals to the later schedule/assignment slot order."""

    exact_text(task_id, field="branch program task_id")
    if type(registry) is not BranchProgramRegistry:
        raise RecordValidationError("registry must be exact BranchProgramRegistry")
    if len(scheduled_slots) != 4 or len(work_orders) != 4:
        raise RecordValidationError(
            "branch program reconciliation requires exactly four slots and orders"
        )
    if any(type(order) is not OpaqueSlotWorkOrder for order in work_orders):
        raise RecordValidationError("work orders must be exact OpaqueSlotWorkOrder")
    task_rows = [task for task in registry.tasks if task.task_id == task_id]
    if len(task_rows) != 1:
        raise RecordValidationError(
            "branch program registry must cover the task exactly once"
        )
    if any(order.task_id != task_id for order in work_orders):
        raise RecordValidationError("branch work-order task binding mismatch")
    slot_ids = [order.slot.slot_id for order in work_orders]
    capabilities = [order.slot.opaque_capability_id for order in work_orders]
    if len(set(slot_ids)) != 4 or len(set(capabilities)) != 4:
        raise RecordValidationError(
            "branch work orders must name distinct slots and capabilities"
        )
    for ordinal, (scheduled, order) in enumerate(
        zip(scheduled_slots, work_orders, strict=True)
    ):
        for name in ("slot_id", "seed", "execution_order", "hardware_lane"):
            if getattr(scheduled, name, None) != getattr(order.slot, name):
                raise RecordValidationError(
                    f"work orders differ from schedule slot order at ordinal {ordinal}"
                )
    refs = tuple(entry.program_ref for entry in task_rows[0].programs)
    return cast(
        tuple[ArtifactRef, ArtifactRef, ArtifactRef, ArtifactRef],
        refs,
    )


def resolve_branch_program_refs(
    *,
    run_root: Path,
    study_ref: ArtifactRef,
    task_id: str,
    expected_trigger_reason: TriggerReason,
    scheduled_slots: Sequence[object],
    work_orders: Sequence[OpaqueSlotWorkOrder],
) -> tuple[ArtifactRef, ArtifactRef, ArtifactRef, ArtifactRef]:
    """Resolve four programs solely through the sealed study-manifest root."""

    if type(expected_trigger_reason) is not TriggerReason:
        raise RecordValidationError(
            "expected_trigger_reason must be exact TriggerReason"
        )

    from .scientific_records import ScientificRefReader, decode_scientific_parent

    root = Path(run_root).resolve(strict=True)
    with ScientificRefReader(root) as scientific_reader:
        bound_study = scientific_reader.read_bound(study_ref)
    study = decode_scientific_parent(
        study_ref,
        bound_study,
        run_root=root,
        field="branch program study",
        expected_kind="resampling_study_manifest",
    )
    payload = study.value.get("payload")
    if not isinstance(payload, dict):
        raise RecordValidationError("study manifest payload is malformed")
    registry_ref = decode_artifact_ref(
        payload.get("branch_program_registry_ref"),
        field="study manifest branch_program_registry_ref",
        expected_role="branch_program_registry",
    )
    if registry_ref.media_type != "application/json":
        raise RecordValidationError(
            "branch program registry must use application/json"
        )
    with AuthorityRefReader(root) as reader:
        reader.verify_closure(
            registry_ref,
            field="study manifest branch program registry",
            expected_role="branch_program_registry",
        )
        registry = load_branch_program_registry(reader.read_bytes(registry_ref))
        refs = reconcile_branch_program_refs(
            registry=registry,
            task_id=task_id,
            scheduled_slots=scheduled_slots,
            work_orders=work_orders,
        )
        for ordinal, ref in enumerate(refs):
            reader.verify_closure(
                ref,
                field=f"branch program task {task_id!r} ordinal {ordinal}",
                expected_role="synthetic_execution_program",
            )
            try:
                program = load_synthetic_prefix_program(reader.read_bytes(ref))
            except (TypeError, ValueError) as exc:
                raise RecordValidationError(
                    "branch execution program is invalid"
                ) from exc
            if program.task_id != task_id:
                raise RecordValidationError(
                    "branch execution program task binding mismatch"
                )
            if program.expected_trigger_reason is not expected_trigger_reason:
                raise RecordValidationError(
                    "branch execution program trigger binding mismatch"
                )
    return refs
