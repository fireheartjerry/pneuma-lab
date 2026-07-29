"""Closed provider-plan validation and cross-contract binding."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .authority_refs import AuthorityRefReader, closed_mapping, exact_nonnegative_int
from .errors import RecordValidationError
from .provider_contract_assets import (
    ValidatedCallContract,
    decode_branch_caps,
    decode_call_contract_caps,
    decode_contract_ref,
    decode_prefix_caps,
    validate_call_contract,
    validate_meter_contract,
    validate_parser_contract,
    validate_task_contract,
    validate_task_input,
)
from .prefix_contracts import ImplementationDescriptor
from .types import (
    ArtifactRef,
    BranchCaps,
    CallContractCaps,
    PrefixCaps,
)


LANE_FIELDS = (
    "ordinal",
    "lane_id",
    "prefix_caps",
    "branch_caps",
    "simulator_caps",
    "subject_contract_ref",
    "simulator_contract_ref",
    "tool_parser_contract_ref",
    "meter_contract_ref",
)
TASK_LANE_FIELDS = (
    "task_id",
    "prefix_lane_ordinal",
    "lane_ordinals_by_execution_rank",
    "task_input_ref",
    "environment_contract_ref",
    "grader_contract_ref",
    "verifier_contract_ref",
    "isolation_contract_ref",
)


@dataclass(frozen=True, slots=True)
class ValidatedTaskLane:
    task_id: str
    prefix_lane_ordinal: int
    lane_ordinals_by_execution_rank: tuple[int, int, int, int]
    task_input_ref: ArtifactRef
    environment_contract_ref: ArtifactRef
    grader_contract_ref: ArtifactRef
    verifier_contract_ref: ArtifactRef
    isolation_contract_ref: ArtifactRef
    requires_user_simulator: bool
    program_ref: ArtifactRef | None
    program_tool_schema_ref: ArtifactRef | None
    descriptors: tuple[ImplementationDescriptor, ...]


@dataclass(frozen=True, slots=True)
class ValidatedLane:
    ordinal: int
    lane_id: str
    prefix_caps: PrefixCaps
    branch_caps: BranchCaps
    simulator_caps: CallContractCaps
    subject_contract_caps: CallContractCaps
    simulator_contract_caps: CallContractCaps | None
    subject_contract_ref: ArtifactRef
    simulator_contract_ref: ArtifactRef | None
    tool_parser_contract_ref: ArtifactRef
    meter_contract_ref: ArtifactRef
    tool_schema_ref: ArtifactRef
    descriptors: tuple[ImplementationDescriptor, ...]


@dataclass(frozen=True, slots=True)
class ValidatedProviderPlan:
    lanes: tuple[ValidatedLane, ...]
    task_lanes: tuple[ValidatedTaskLane, ...]


def _validate_lane_bindings(
    *,
    field: str,
    prefix_caps: PrefixCaps,
    branch_caps: BranchCaps,
    simulator_caps: CallContractCaps,
    subject: ValidatedCallContract,
    simulator: ValidatedCallContract | None,
    parser_response_grammar: str,
    parser_tool_schema_ref: ArtifactRef,
) -> None:
    if (
        max(prefix_caps.generated_tokens, branch_caps.generated_tokens)
        != subject.caps.aggregate_generated_tokens
        or max(prefix_caps.model_calls, branch_caps.model_calls)
        != subject.caps.aggregate_model_calls
    ):
        raise RecordValidationError(
            f"{field} subject contract caps do not exactly match lane caps"
        )
    if parser_response_grammar != subject.response_grammar:
        raise RecordValidationError(
            f"{field} parser response grammar differs from subject"
        )
    if parser_tool_schema_ref != subject.tool_schema_ref:
        raise RecordValidationError(f"{field} parser tool schema differs from subject")
    if simulator is None:
        if simulator_caps != CallContractCaps(0, 0, 0, 0, 0):
            raise RecordValidationError(
                f"{field} absent simulator requires all-zero simulator caps"
            )
        return
    if simulator_caps != simulator.caps:
        raise RecordValidationError(
            f"{field} simulator caps differ from simulator contract"
        )
    if any(
        value <= 0
        for value in (
            simulator_caps.aggregate_generated_tokens,
            simulator_caps.aggregate_model_calls,
            simulator_caps.aggregate_turns,
            simulator_caps.per_call_generated_tokens,
            simulator_caps.per_call_turns,
        )
    ):
        raise RecordValidationError(f"{field} present simulator caps must be positive")
    if parser_response_grammar != simulator.response_grammar:
        raise RecordValidationError(
            f"{field} parser response grammar differs from simulator"
        )
    if parser_tool_schema_ref != simulator.tool_schema_ref:
        raise RecordValidationError(
            f"{field} parser tool schema differs from simulator"
        )


def _decode_lane(
    value: object,
    *,
    ordinal: int,
    tokenizer_ref: ArtifactRef,
    manifest_revisions: tuple[ArtifactRef, ...],
    reader: AuthorityRefReader,
    schedule_authority: str | None,
) -> ValidatedLane:
    field = f"provider lane plan lanes[{ordinal}]"
    lane = closed_mapping(value, fields=set(LANE_FIELDS), field=field)
    if type(lane["ordinal"]) is not int or lane["ordinal"] != ordinal:
        raise RecordValidationError(
            "provider lanes must have contiguous zero-based ordinals"
        )
    lane_id = lane["lane_id"]
    if type(lane_id) is not str or not lane_id:
        raise RecordValidationError(f"{field}.lane_id must be non-empty exact text")
    subject_ref = decode_contract_ref(
        lane["subject_contract_ref"],
        field=f"{field}.subject_contract_ref",
        expected_role="subject_contract",
    )
    simulator_ref = (
        None
        if lane["simulator_contract_ref"] is None
        else decode_contract_ref(
            lane["simulator_contract_ref"],
            field=f"{field}.simulator_contract_ref",
            expected_role="simulator_contract",
        )
    )
    parser_ref = decode_contract_ref(
        lane["tool_parser_contract_ref"],
        field=f"{field}.tool_parser_contract_ref",
        expected_role="tool_parser_contract",
    )
    meter_ref = decode_contract_ref(
        lane["meter_contract_ref"],
        field=f"{field}.meter_contract_ref",
        expected_role="meter_contract",
    )
    subject = validate_call_contract(
        subject_ref,
        expected_kind="prefix_subject_contract_v1",
        tokenizer_ref=tokenizer_ref,
        manifest_revisions=manifest_revisions,
        reader=reader,
        field=f"{field} subject contract",
    )
    simulator = (
        None
        if simulator_ref is None
        else validate_call_contract(
            simulator_ref,
            expected_kind="prefix_simulator_contract_v1",
            tokenizer_ref=tokenizer_ref,
            manifest_revisions=manifest_revisions,
            reader=reader,
            field=f"{field} simulator contract",
        )
    )
    parser = validate_parser_contract(
        parser_ref,
        manifest_revisions=manifest_revisions,
        reader=reader,
    )
    meter = validate_meter_contract(
        meter_ref,
        manifest_revisions=manifest_revisions,
        reader=reader,
    )
    if schedule_authority == "synthetic_validation" and not meter.zero_cost:
        raise RecordValidationError(
            f"{field} requires zero-cost synthetic meter closure"
        )
    prefix_caps = decode_prefix_caps(lane["prefix_caps"], field=f"{field}.prefix_caps")
    branch_caps = decode_branch_caps(lane["branch_caps"], field=f"{field}.branch_caps")
    simulator_caps = decode_call_contract_caps(
        lane["simulator_caps"],
        field=f"{field}.simulator_caps",
    )
    _validate_lane_bindings(
        field=field,
        prefix_caps=prefix_caps,
        branch_caps=branch_caps,
        simulator_caps=simulator_caps,
        subject=subject,
        simulator=simulator,
        parser_response_grammar=parser.response_grammar,
        parser_tool_schema_ref=parser.tool_schema_ref,
    )
    return ValidatedLane(
        ordinal=ordinal,
        lane_id=lane_id,
        prefix_caps=prefix_caps,
        branch_caps=branch_caps,
        simulator_caps=simulator_caps,
        subject_contract_caps=subject.caps,
        simulator_contract_caps=None if simulator is None else simulator.caps,
        subject_contract_ref=subject_ref,
        simulator_contract_ref=simulator_ref,
        tool_parser_contract_ref=parser_ref,
        meter_contract_ref=meter_ref,
        tool_schema_ref=parser.tool_schema_ref,
        descriptors=(
            *subject.descriptors,
            *((*simulator.descriptors,) if simulator is not None else ()),
            parser.descriptor,
            *meter.descriptors,
        ),
    )


def _decode_task_lane(
    value: object,
    *,
    index: int,
    lane_count: int,
    registry_by_id: dict[str, dict[str, object]],
    manifest_revisions: tuple[ArtifactRef, ...],
    reader: AuthorityRefReader,
    require_execution_program: bool,
) -> ValidatedTaskLane:
    field = f"provider lane plan task_lanes[{index}]"
    row = closed_mapping(value, fields=set(TASK_LANE_FIELDS), field=field)
    task_id = row["task_id"]
    if type(task_id) is not str or not task_id:
        raise RecordValidationError(f"{field}.task_id must be non-empty exact text")
    prefix_ordinal = exact_nonnegative_int(
        row["prefix_lane_ordinal"],
        field=f"{field}.prefix_lane_ordinal",
    )
    rank_ordinals = row["lane_ordinals_by_execution_rank"]
    if not isinstance(rank_ordinals, list) or len(rank_ordinals) != 4:
        raise RecordValidationError(
            f"{field}.lane_ordinals_by_execution_rank must have four items"
        )
    exact_rank_ordinals = tuple(
        exact_nonnegative_int(
            item,
            field=f"{field}.lane_ordinals_by_execution_rank[{rank}]",
        )
        for rank, item in enumerate(rank_ordinals)
    )
    if any(ordinal >= lane_count for ordinal in (prefix_ordinal, *exact_rank_ordinals)):
        raise RecordValidationError("provider task lane ordinal is out of range")
    registry_task = registry_by_id.get(task_id)
    if registry_task is None:
        raise RecordValidationError(
            "provider task lanes do not exactly cover the task registry"
        )
    refs = {
        name: decode_contract_ref(
            row[f"{name}_ref"],
            field=f"{field}.{name}_ref",
            expected_role="task_input" if name == "task_input" else name,
        )
        for name in (
            "task_input",
            "environment_contract",
            "grader_contract",
            "verifier_contract",
            "isolation_contract",
        )
    }
    benchmark = cast(str, registry_task["benchmark"])
    task_input = validate_task_input(
        refs["task_input"],
        task_id=task_id,
        benchmark=benchmark,
        reader=reader,
        require_execution_program=require_execution_program,
    )
    descriptors: list[ImplementationDescriptor] = []
    for contract_kind in ("environment", "grader", "verifier", "isolation"):
        descriptor = validate_task_contract(
            refs[f"{contract_kind}_contract"],
            contract_kind=contract_kind,
            task_id=task_id,
            benchmark=benchmark,
            manifest_revisions=manifest_revisions,
            reader=reader,
        )
        if descriptor is not None:
            descriptors.append(descriptor)
            if contract_kind == "environment":
                descriptors.append(
                    ImplementationDescriptor(
                        purpose="tokenizer",
                        nominal_type=(
                            "pneuma_lab.resampling_null.synthetic_environment."
                            "SyntheticByteTokenizer"
                        ),
                        build_id="synthetic-byte-tokenizer-v1",
                        request_grammar=None,
                        response_grammar=None,
                        snapshot_grammar=None,
                        restore_grammar=None,
                        evidence_grammar=None,
                        runtime_id=None,
                        container_digest=None,
                        implementation_source_ref=(
                            descriptor.implementation_source_ref
                        ),
                    )
                )
    return ValidatedTaskLane(
        task_id=task_id,
        prefix_lane_ordinal=prefix_ordinal,
        lane_ordinals_by_execution_rank=cast(
            tuple[int, int, int, int],
            exact_rank_ordinals,
        ),
        task_input_ref=refs["task_input"],
        environment_contract_ref=refs["environment_contract"],
        grader_contract_ref=refs["grader_contract"],
        verifier_contract_ref=refs["verifier_contract"],
        isolation_contract_ref=refs["isolation_contract"],
        requires_user_simulator=task_input.requires_user_simulator,
        program_ref=task_input.program_ref,
        program_tool_schema_ref=(
            task_input.program.tool_schema_ref
            if task_input.program is not None
            else None
        ),
        descriptors=tuple(descriptors),
    )


def _validate_simulator_assignments(
    lanes: list[ValidatedLane],
    task_lanes: list[ValidatedTaskLane],
) -> None:
    for lane in lanes:
        assigned = [
            row
            for row in task_lanes
            if lane.ordinal
            in (row.prefix_lane_ordinal, *row.lane_ordinals_by_execution_rank)
        ]
        requirements = {row.requires_user_simulator for row in assigned}
        if requirements == {False, True}:
            raise RecordValidationError(
                f"provider lane {lane.lane_id!r} has mixed simulator capability"
            )
        if lane.simulator_contract_ref is None and requirements == {True}:
            raise RecordValidationError(
                f"provider lane {lane.lane_id!r} is missing a required simulator"
            )
        if lane.simulator_contract_ref is not None and requirements != {True}:
            raise RecordValidationError(
                f"provider lane {lane.lane_id!r} has unnecessary simulator authority"
            )


def validate_provider_lane_plan(
    value: object,
    *,
    reader: AuthorityRefReader,
    registry: dict[str, object],
    tokenizer_ref: ArtifactRef,
    manifest_revisions: tuple[ArtifactRef, ...],
    schedule_authority: str | None = None,
    require_execution_program: bool = False,
) -> ValidatedProviderPlan:
    plan = closed_mapping(
        value,
        fields={"record_kind", "schema_version", "lanes", "task_lanes"},
        field="provider lane plan",
    )
    if plan["record_kind"] != "provider_lane_plan_v2" or plan["schema_version"] != "2":
        raise RecordValidationError("provider lane plan has wrong identity")
    lanes_value = plan["lanes"]
    if not isinstance(lanes_value, list) or not lanes_value:
        raise RecordValidationError("provider lane plan lanes must be non-empty")
    lanes = [
        _decode_lane(
            lane,
            ordinal=ordinal,
            tokenizer_ref=tokenizer_ref,
            manifest_revisions=manifest_revisions,
            reader=reader,
            schedule_authority=schedule_authority,
        )
        for ordinal, lane in enumerate(lanes_value)
    ]
    if len({lane.lane_id for lane in lanes}) != len(lanes):
        raise RecordValidationError("provider lane IDs must be unique")
    registry_tasks = cast(list[dict[str, object]], registry["tasks"])
    registry_by_id = {cast(str, task["task_id"]): task for task in registry_tasks}
    task_lanes_value = plan["task_lanes"]
    if not isinstance(task_lanes_value, list):
        raise RecordValidationError("provider task_lanes must be an array")
    task_lanes = [
        _decode_task_lane(
            row,
            index=index,
            lane_count=len(lanes),
            registry_by_id=registry_by_id,
            manifest_revisions=manifest_revisions,
            reader=reader,
            require_execution_program=require_execution_program,
        )
        for index, row in enumerate(task_lanes_value)
    ]
    encoded_ids = [row.task_id.encode("utf-8") for row in task_lanes]
    if encoded_ids != sorted(set(encoded_ids)):
        raise RecordValidationError("provider task lanes are not strict task-ID sorted")
    if {row.task_id for row in task_lanes} != set(registry_by_id):
        raise RecordValidationError(
            "provider task lanes do not exactly cover the task registry"
        )
    _validate_simulator_assignments(lanes, task_lanes)
    return ValidatedProviderPlan(tuple(lanes), tuple(task_lanes))


__all__ = (
    "ValidatedLane",
    "ValidatedProviderPlan",
    "ValidatedTaskLane",
    "validate_provider_lane_plan",
)
