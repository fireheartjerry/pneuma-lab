"""Schedule-to-task projection of sealed prefix execution authority."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from .authority_refs import AuthorityRefReader, decode_artifact_ref
from .errors import RecordValidationError
from .preflight import validate_task_registry
from .prefix_contracts import (
    AUTHORITY_ASSET_ROLE_MEDIA,
    ImplementationDescriptor,
    PRODUCTION_VALIDATED_AUTHORITY_ROLES,
)
from .provider_contracts import (
    ValidatedProviderPlan,
    validate_provider_lane_plan,
)
from .scientific_records import (
    ScientificRefReader,
    decode_scientific_parent,
    load_scientific_parent,
)
from .task_schedule_codec import decode_task_schedule
from .types import (
    ArtifactRef,
    BranchCaps,
    PrefixCaps,
    CallContractCaps,
    TaskSchedule,
)


@dataclass(frozen=True, slots=True)
class PrefixExecutionAuthority:
    """Immutable execution policy reconstructed from schedule ancestry."""

    schedule_ref: ArtifactRef
    manifest_ref: ArtifactRef
    provider_lane_plan_ref: ArtifactRef
    schedule_authority: Literal["synthetic_validation"]
    tokenizer_ref: ArtifactRef
    source_revision_refs: tuple[ArtifactRef, ...]
    program_ref: ArtifactRef
    implementation_descriptors: tuple[ImplementationDescriptor, ...]
    task_schedule: TaskSchedule
    prefix_caps: PrefixCaps
    branch_caps: BranchCaps
    simulator_caps: CallContractCaps
    subject_contract_caps: CallContractCaps
    simulator_contract_caps: CallContractCaps | None
    actor_roles: tuple[Literal["primary_subject", "user_simulator"], ...]
    task_input_ref: ArtifactRef
    environment_contract_ref: ArtifactRef
    grader_contract_ref: ArtifactRef
    verifier_contract_ref: ArtifactRef
    isolation_contract_ref: ArtifactRef
    subject_contract_ref: ArtifactRef
    simulator_contract_ref: ArtifactRef | None
    tool_parser_contract_ref: ArtifactRef
    meter_contract_ref: ArtifactRef

    def __post_init__(self) -> None:
        for name in (
            "schedule_ref",
            "manifest_ref",
            "provider_lane_plan_ref",
            "tokenizer_ref",
            "program_ref",
            "task_input_ref",
            "environment_contract_ref",
            "grader_contract_ref",
            "verifier_contract_ref",
            "isolation_contract_ref",
            "subject_contract_ref",
            "tool_parser_contract_ref",
            "meter_contract_ref",
        ):
            if type(getattr(self, name)) is not ArtifactRef:
                raise TypeError(f"{name} must be an exact ArtifactRef")
        if self.schedule_authority != "synthetic_validation":
            raise ValueError("schedule_authority must equal 'synthetic_validation'")
        if (
            type(self.source_revision_refs) is not tuple
            or not self.source_revision_refs
        ):
            raise TypeError("source_revision_refs must be a non-empty exact tuple")
        if not all(type(ref) is ArtifactRef for ref in self.source_revision_refs):
            raise TypeError(
                "source_revision_refs must contain exact ArtifactRef values"
            )
        if type(self.implementation_descriptors) is not tuple:
            raise TypeError("implementation_descriptors must be an exact tuple")
        if not all(
            type(item) is ImplementationDescriptor
            for item in self.implementation_descriptors
        ):
            raise TypeError("implementation_descriptors must contain exact descriptors")
        if type(self.task_schedule) is not TaskSchedule:
            raise TypeError("task_schedule must be an exact TaskSchedule")
        if type(self.prefix_caps) is not PrefixCaps:
            raise TypeError("prefix_caps must be exact PrefixCaps")
        if type(self.branch_caps) is not BranchCaps:
            raise TypeError("branch_caps must be exact BranchCaps")
        for name in ("simulator_caps", "subject_contract_caps"):
            if type(getattr(self, name)) is not CallContractCaps:
                raise TypeError(f"{name} must be exact CallContractCaps")
        if (
            self.simulator_contract_caps is not None
            and type(self.simulator_contract_caps) is not CallContractCaps
        ):
            raise TypeError(
                "simulator_contract_caps must be exact CallContractCaps or None"
            )
        if type(self.actor_roles) is not tuple or any(
            type(role) is not str or role not in ("primary_subject", "user_simulator")
            for role in self.actor_roles
        ):
            raise TypeError("actor_roles must be an exact closed-role tuple")
        if (
            self.simulator_contract_ref is not None
            and type(self.simulator_contract_ref) is not ArtifactRef
        ):
            raise TypeError(
                "simulator_contract_ref must be an exact ArtifactRef or None"
            )


def _selected_schedule_task(
    schedule_payload: dict[str, object],
    *,
    task_id: str,
) -> Mapping[str, object]:
    selected = [
        value
        for value in cast(list[object], schedule_payload["tasks"])
        if isinstance(value, Mapping)
        and isinstance(value.get("task"), Mapping)
        and cast(Mapping[str, object], value["task"]).get("task_id") == task_id
    ]
    if len(selected) != 1:
        raise RecordValidationError(
            f"task_id {task_id!r} is not exactly once selected by the schedule"
        )
    return cast(Mapping[str, object], selected[0])


def _validate_registry_binding(
    selected: Mapping[str, object],
    registry: dict[str, object],
    *,
    task_id: str,
) -> None:
    registry_by_id = {
        cast(str, task["task_id"]): task
        for task in cast(list[dict[str, object]], registry["tasks"])
    }
    registry_task = registry_by_id.get(task_id)
    if registry_task is None:
        raise RecordValidationError("scheduled task is absent from task registry")
    scheduled_task = cast(Mapping[str, object], selected["task"])
    if (
        scheduled_task.get("benchmark") != registry_task["benchmark"]
        or scheduled_task.get("stratum") != registry_task["stratum"]
        or scheduled_task.get("lineage") != registry_task["lineage"]
        or scheduled_task.get("sensitivity_groups") != registry_task["groups"]
    ):
        raise RecordValidationError(
            "selected schedule task differs from task registry binding"
        )


def _manifest_revisions(
    value: object,
    *,
    reader: AuthorityRefReader,
) -> tuple[ArtifactRef, ...]:
    if not isinstance(value, list) or not value:
        raise RecordValidationError(
            "manifest source_revision_refs must be a non-empty array"
        )
    revisions = tuple(
        decode_artifact_ref(
            item,
            field=f"manifest source_revision_refs[{index}]",
            expected_role="source_revision",
        )
        for index, item in enumerate(value)
    )
    expected_media = AUTHORITY_ASSET_ROLE_MEDIA["source_revision"]
    if any(ref.media_type != expected_media for ref in revisions):
        raise RecordValidationError(
            "manifest source revisions have noncanonical media type"
        )
    for revision in revisions:
        reader.verify_closure(
            revision,
            field="manifest source revision",
            expected_role="source_revision",
        )
    return revisions


def _project_task_authority(
    *,
    schedule_ref: ArtifactRef,
    manifest_ref: ArtifactRef,
    provider_ref: ArtifactRef,
    task_schedule: TaskSchedule,
    validated_plan: ValidatedProviderPlan,
    task_id: str,
    schedule_authority: Literal["synthetic_validation"],
    tokenizer_ref: ArtifactRef,
    source_revision_refs: tuple[ArtifactRef, ...],
) -> PrefixExecutionAuthority:
    task_rows = [row for row in validated_plan.task_lanes if row.task_id == task_id]
    if len(task_rows) != 1:
        raise RecordValidationError("selected task has no unique provider row")
    task_row = task_rows[0]
    selected_lane = validated_plan.lanes[task_row.prefix_lane_ordinal]
    if task_schedule.provider_lane != selected_lane.lane_id:
        raise RecordValidationError(
            "provider lane mismatch between schedule and provider plan"
        )
    for slot in task_schedule.slots.slots:
        expected_lane = task_row.lane_ordinals_by_execution_rank[slot.execution_order]
        if slot.hardware_lane != expected_lane:
            raise RecordValidationError(
                "schedule slot lane mismatch with provider plan"
            )
    if (
        task_row.requires_user_simulator
        and selected_lane.simulator_contract_ref is None
    ):
        raise RecordValidationError("selected task is missing a required simulator")
    if task_row.program_tool_schema_ref != selected_lane.tool_schema_ref:
        raise RecordValidationError(
            "synthetic program tool schema differs from selected lane"
        )
    if task_row.program_ref is None:
        raise RecordValidationError(
            "execution-ready task input requires one synthetic program ref"
        )
    descriptor_values = (*task_row.descriptors, *selected_lane.descriptors)
    descriptor_by_purpose = {
        descriptor.purpose: descriptor for descriptor in descriptor_values
    }
    if len(descriptor_by_purpose) != len(descriptor_values):
        raise RecordValidationError("implementation descriptor purposes must be unique")
    expected_purposes = (
        "environment",
        "subject",
        *(("simulator",) if selected_lane.simulator_contract_ref is not None else ()),
        "meter",
        "tokenizer",
        "request_renderer",
        "response_parser",
        "grader",
        "verifier",
        "provider_event_codec",
        "settlement_codec",
    )
    if set(descriptor_by_purpose) != set(expected_purposes):
        raise RecordValidationError(
            "implementation descriptors do not exactly cover required purposes"
        )
    descriptors = tuple(descriptor_by_purpose[purpose] for purpose in expected_purposes)
    if any(
        descriptor.implementation_source_ref not in source_revision_refs
        for descriptor in descriptors
    ):
        raise RecordValidationError(
            "implementation descriptor source is not manifest-authorized"
        )
    return PrefixExecutionAuthority(
        schedule_ref=schedule_ref,
        manifest_ref=manifest_ref,
        provider_lane_plan_ref=provider_ref,
        schedule_authority=schedule_authority,
        tokenizer_ref=tokenizer_ref,
        source_revision_refs=source_revision_refs,
        program_ref=task_row.program_ref,
        implementation_descriptors=descriptors,
        task_schedule=task_schedule,
        prefix_caps=selected_lane.prefix_caps,
        branch_caps=selected_lane.branch_caps,
        simulator_caps=selected_lane.simulator_caps,
        subject_contract_caps=selected_lane.subject_contract_caps,
        simulator_contract_caps=selected_lane.simulator_contract_caps,
        actor_roles=task_row.actor_roles,
        task_input_ref=task_row.task_input_ref,
        environment_contract_ref=task_row.environment_contract_ref,
        grader_contract_ref=task_row.grader_contract_ref,
        verifier_contract_ref=task_row.verifier_contract_ref,
        isolation_contract_ref=task_row.isolation_contract_ref,
        subject_contract_ref=selected_lane.subject_contract_ref,
        simulator_contract_ref=selected_lane.simulator_contract_ref,
        tool_parser_contract_ref=selected_lane.tool_parser_contract_ref,
        meter_contract_ref=selected_lane.meter_contract_ref,
    )


def _load_prefix_execution_authority_and_plan_with_reader(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    task_id: str,
    reader: AuthorityRefReader,
    scientific_reader: ScientificRefReader | None = None,
) -> tuple[PrefixExecutionAuthority, ValidatedProviderPlan]:
    """Reconstruct one selected task's execution policy from sealed ancestry."""

    if type(run_root) is not type(Path()):
        raise TypeError("run_root must be an exact platform Path")
    if type(schedule_ref) is not ArtifactRef:
        raise TypeError("schedule_ref must be an exact ArtifactRef")
    if schedule_ref.role != "resampling_prefix_schedule":
        raise RecordValidationError(
            "schedule_ref role must equal 'resampling_prefix_schedule'"
        )
    if type(task_id) is not str:
        raise TypeError("task_id must be exact text")
    if not task_id:
        raise ValueError("task_id must be non-empty")
    root = run_root.resolve(strict=True)
    schedule = (
        load_scientific_parent(
            asdict(schedule_ref),
            run_root=root,
            field="schedule_ref",
            expected_kind="resampling_prefix_schedule",
        )
        if scientific_reader is None
        else decode_scientific_parent(
            schedule_ref,
            scientific_reader.read_bound(schedule_ref),
            run_root=root,
            field="schedule_ref",
            expected_kind="resampling_prefix_schedule",
        )
    )
    schedule_payload = cast(dict[str, object], schedule.value["payload"])
    manifest_ref = decode_artifact_ref(
        schedule_payload["manifest_ref"],
        field="schedule manifest_ref",
        expected_role="study_manifest",
    )
    manifest = (
        load_scientific_parent(
            asdict(manifest_ref),
            run_root=root,
            field="schedule manifest_ref",
            expected_kind="resampling_study_manifest",
        )
        if scientific_reader is None
        else decode_scientific_parent(
            manifest_ref,
            scientific_reader.read_bound(manifest_ref),
            run_root=root,
            field="schedule manifest_ref",
            expected_kind="resampling_study_manifest",
        )
    )
    if (
        schedule.value["study_id"] != manifest.value["study_id"]
        or schedule.value["frozen_created_at"] != manifest.value["frozen_created_at"]
        or schedule.value["provenance"] != manifest.value["provenance"]
    ):
        raise RecordValidationError("schedule and manifest envelopes differ")
    selected = _selected_schedule_task(
        schedule_payload,
        task_id=task_id,
    )
    task_schedule = decode_task_schedule(
        selected,
        field="selected schedule task",
    )
    manifest_payload = cast(dict[str, object], manifest.value["payload"])
    with nullcontext(reader):
        registry_ref = decode_artifact_ref(
            manifest_payload["task_registry_ref"],
            field="manifest task_registry_ref",
            expected_role="task_registry",
        )
        registry = reader.decode_json(
            registry_ref,
            field="task registry",
            canonical=False,
            expected_role="task_registry",
        )
        if (
            set(registry) != {"record_kind", "schema_version", "tasks"}
            or registry.get("record_kind") != "resampling_task_registry_v1"
        ):
            raise RecordValidationError("task registry has wrong shape or identity")
        validate_task_registry(registry)
        reader.mark_semantically_validated(registry_ref)
        _validate_registry_binding(
            selected,
            registry,
            task_id=task_id,
        )
        for schedule_row in cast(list[object], schedule_payload["tasks"]):
            if not isinstance(schedule_row, Mapping):
                raise RecordValidationError("selected schedule task is not a mapping")
            scheduled = decode_task_schedule(
                schedule_row,
                field="selected schedule task",
            )
            _validate_registry_binding(
                schedule_row,
                registry,
                task_id=scheduled.task.task_id,
            )
        tokenizer_ref = decode_artifact_ref(
            manifest_payload["tokenizer_ref"],
            field="manifest tokenizer_ref",
            expected_role="tokenizer",
        )
        if tokenizer_ref.media_type != AUTHORITY_ASSET_ROLE_MEDIA["tokenizer"]:
            raise RecordValidationError(
                "manifest tokenizer has noncanonical media type"
            )
        reader.verify_closure(
            tokenizer_ref,
            field="manifest tokenizer_ref",
            expected_role="tokenizer",
        )
        revisions = _manifest_revisions(
            manifest_payload["source_revision_refs"],
            reader=reader,
        )
        provider_ref = decode_artifact_ref(
            manifest_payload["provider_lane_plan_ref"],
            field="manifest provider_lane_plan_ref",
            expected_role="provider_lane_plan",
        )
        provider_plan = reader.decode_json(
            provider_ref,
            field="provider lane plan",
            canonical=False,
            expected_role="provider_lane_plan",
        )
        schedule_authority = cast(str, schedule_payload["schedule_authority"])
        if schedule_authority != "synthetic_validation":
            raise RecordValidationError(
                "prefix execution requires schedule_authority 'synthetic_validation'"
            )
        validated_plan = validate_provider_lane_plan(
            provider_plan,
            reader=reader,
            registry=registry,
            tokenizer_ref=tokenizer_ref,
            manifest_revisions=revisions,
            schedule_authority=schedule_authority,
            require_execution_program=True,
        )
        validated_refs = {
            provider_ref,
            *(
                ref
                for lane in validated_plan.lanes
                for ref in (
                    lane.subject_contract_ref,
                    lane.tool_parser_contract_ref,
                    lane.meter_contract_ref,
                    *(
                        ()
                        if lane.simulator_contract_ref is None
                        else (lane.simulator_contract_ref,)
                    ),
                )
            ),
            *(
                ref
                for row in validated_plan.task_lanes
                for ref in (
                    row.task_input_ref,
                    row.environment_contract_ref,
                    row.grader_contract_ref,
                    row.verifier_contract_ref,
                    row.isolation_contract_ref,
                )
            ),
        }
        if {ref.role for ref in validated_refs} - PRODUCTION_VALIDATED_AUTHORITY_ROLES:
            raise RuntimeError("production validator proof role coverage drifted")
        for validated_ref in validated_refs:
            reader.mark_semantically_validated(validated_ref)
    authority = _project_task_authority(
        schedule_ref=schedule_ref,
        manifest_ref=manifest_ref,
        provider_ref=provider_ref,
        task_schedule=task_schedule,
        validated_plan=validated_plan,
        task_id=task_id,
        schedule_authority=cast(
            Literal["synthetic_validation"],
            schedule_authority,
        ),
        tokenizer_ref=tokenizer_ref,
        source_revision_refs=revisions,
    )
    return authority, validated_plan


def _load_prefix_execution_authority_with_reader(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    task_id: str,
    reader: AuthorityRefReader,
    scientific_reader: ScientificRefReader | None = None,
) -> PrefixExecutionAuthority:
    authority, _ = _load_prefix_execution_authority_and_plan_with_reader(
        run_root=run_root,
        schedule_ref=schedule_ref,
        task_id=task_id,
        reader=reader,
        scientific_reader=scientific_reader,
    )
    return authority


def _project_prefix_execution_authority_from_plan(
    *,
    anchor: PrefixExecutionAuthority,
    schedule_payload: dict[str, object],
    task_id: str,
    validated_plan: ValidatedProviderPlan,
) -> PrefixExecutionAuthority:
    selected = _selected_schedule_task(schedule_payload, task_id=task_id)
    task_schedule = decode_task_schedule(selected, field="selected schedule task")
    return _project_task_authority(
        schedule_ref=anchor.schedule_ref,
        manifest_ref=anchor.manifest_ref,
        provider_ref=anchor.provider_lane_plan_ref,
        task_schedule=task_schedule,
        validated_plan=validated_plan,
        task_id=task_id,
        schedule_authority=anchor.schedule_authority,
        tokenizer_ref=anchor.tokenizer_ref,
        source_revision_refs=anchor.source_revision_refs,
    )


def load_prefix_execution_authority(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    task_id: str,
) -> PrefixExecutionAuthority:
    """Reconstruct authority with one fresh shared authority-asset reader."""

    root = Path(run_root).resolve(strict=True)
    with AuthorityRefReader(root) as reader:
        return _load_prefix_execution_authority_with_reader(
            run_root=root,
            schedule_ref=schedule_ref,
            task_id=task_id,
            reader=reader,
        )


__all__ = (
    "PrefixExecutionAuthority",
    "load_prefix_execution_authority",
)
