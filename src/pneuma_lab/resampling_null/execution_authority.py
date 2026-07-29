"""Schedule-ancestry authority for prefix execution policy."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import (
    RecordValidationError,
    _load_direct_scientific_parent,
    _load_json_bytes,
    _read_ref,
)
from .branch_assignment import _task_schedule
from .preflight import _validate_task_registry
from .types import (
    ArtifactRef,
    BranchCaps,
    PrefixCaps,
    SimulatorCaps,
    TaskSchedule,
)


_REF_FIELDS = {
    "role",
    "relative_path",
    "sha256",
    "byte_count",
    "media_type",
}
_CAP_FIELDS = {
    "generated_tokens",
    "model_calls",
    "tool_calls",
    "wall_clock_ms",
}
_SIMULATOR_CAP_FIELDS = {
    "aggregate_generated_tokens",
    "aggregate_model_calls",
    "per_call_generated_tokens",
    "per_call_turns",
}
_CALL_CONTRACT_FIELDS = {
    "record_kind",
    "schema_version",
    "model_id",
    "tokenizer_ref",
    "prompt_template_ref",
    "tool_schema_ref",
    "request_grammar",
    "response_grammar",
    "seeded_call_grammar",
    "stateless_client_attestation",
    "aggregate_caps",
    "per_call_caps",
    "nominal_type",
    "build_id",
    "source_revision_refs",
}


@dataclass(frozen=True, slots=True)
class PrefixExecutionAuthority:
    """Immutable execution policy reconstructed only from sealed schedule ancestry."""

    schedule_ref: ArtifactRef
    manifest_ref: ArtifactRef
    provider_lane_plan_ref: ArtifactRef
    task_schedule: TaskSchedule
    prefix_caps: PrefixCaps
    branch_caps: BranchCaps
    simulator_caps: SimulatorCaps
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
        if type(self.task_schedule) is not TaskSchedule:
            raise TypeError("task_schedule must be an exact TaskSchedule")
        if type(self.prefix_caps) is not PrefixCaps:
            raise TypeError("prefix_caps must be exact PrefixCaps")
        if type(self.branch_caps) is not BranchCaps:
            raise TypeError("branch_caps must be exact BranchCaps")
        if type(self.simulator_caps) is not SimulatorCaps:
            raise TypeError("simulator_caps must be exact SimulatorCaps")
        if (
            self.simulator_contract_ref is not None
            and type(self.simulator_contract_ref) is not ArtifactRef
        ):
            raise TypeError(
                "simulator_contract_ref must be an exact ArtifactRef or None"
            )


@dataclass(frozen=True, slots=True)
class _TaskLane:
    task_id: str
    prefix_lane_ordinal: int
    lane_ordinals_by_execution_rank: tuple[int, int, int, int]
    task_input_ref: ArtifactRef
    environment_contract_ref: ArtifactRef
    grader_contract_ref: ArtifactRef
    verifier_contract_ref: ArtifactRef
    isolation_contract_ref: ArtifactRef
    requires_user_simulator: bool


@dataclass(frozen=True, slots=True)
class _Lane:
    ordinal: int
    lane_id: str
    prefix_caps: PrefixCaps
    branch_caps: BranchCaps
    simulator_caps: SimulatorCaps
    subject_contract_ref: ArtifactRef
    simulator_contract_ref: ArtifactRef | None
    tool_parser_contract_ref: ArtifactRef
    meter_contract_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class _ValidatedProviderPlan:
    lanes: tuple[_Lane, ...]
    task_lanes: tuple[_TaskLane, ...]


def _closed_mapping(
    value: object,
    *,
    fields: set[str],
    field: str,
) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise RecordValidationError(f"{field} has an open or incomplete shape")
    return dict(value)


def _exact_text(value: object, *, field: str) -> str:
    if type(value) is not str:
        raise RecordValidationError(f"{field} must be exact text")
    text = cast(str, value)
    if not text:
        raise RecordValidationError(f"{field} must be non-empty")
    return text


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    if type(value) is not int:
        raise RecordValidationError(f"{field} must be an exact integer")
    integer = cast(int, value)
    if integer < 0:
        raise RecordValidationError(f"{field} must be non-negative")
    return integer


def _artifact_ref(value: object, *, field: str) -> ArtifactRef:
    mapping = _closed_mapping(value, fields=_REF_FIELDS, field=field)
    try:
        ref = ArtifactRef(
            role=cast(str, mapping["role"]),
            relative_path=cast(str, mapping["relative_path"]),
            sha256=cast(str, mapping["sha256"]),
            byte_count=cast(int, mapping["byte_count"]),
            media_type=cast(str, mapping["media_type"]),
        )
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is malformed: {exc}") from exc
    return ref


def _read_json_ref(
    ref: ArtifactRef,
    *,
    run_root: Path,
    field: str,
    canonical: bool,
) -> dict[str, object]:
    if ref.media_type != "application/json":
        raise RecordValidationError(f"{field} must reference application/json")
    path, raw = _read_ref(ref, run_root=run_root)
    value = _load_json_bytes(raw, source=path)
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must reference a JSON object")
    plain = dict(value)
    if canonical and raw != canonical_json_bytes(plain, indent=None):
        raise RecordValidationError(f"{field} must be compact canonical JSON")
    return plain


def _validate_source_revisions(
    value: object,
    *,
    field: str,
    manifest_revisions: tuple[ArtifactRef, ...],
    run_root: Path,
) -> None:
    if not isinstance(value, list) or not value:
        raise RecordValidationError(f"{field} must be a non-empty array")
    refs = tuple(
        _artifact_ref(item, field=f"{field}[{index}]")
        for index, item in enumerate(value)
    )
    if len(refs) != len(set(refs)):
        raise RecordValidationError(f"{field} must not contain duplicates")
    if any(ref not in manifest_revisions for ref in refs):
        raise RecordValidationError(
            f"{field} contains a non-manifest source revision"
        )
    for ref in refs:
        _read_ref(ref, run_root=run_root)


def _validate_named_caps(
    value: object,
    *,
    fields: set[str],
    field: str,
) -> dict[str, int]:
    mapping = _closed_mapping(value, fields=fields, field=field)
    return {
        name: _exact_nonnegative_int(mapping[name], field=f"{field}.{name}")
        for name in fields
    }


def _validate_call_contract(
    ref: ArtifactRef,
    *,
    expected_kind: str,
    tokenizer_ref: ArtifactRef,
    manifest_revisions: tuple[ArtifactRef, ...],
    run_root: Path,
    field: str,
) -> None:
    value = _read_json_ref(ref, run_root=run_root, field=field, canonical=True)
    contract = _closed_mapping(
        value,
        fields=_CALL_CONTRACT_FIELDS,
        field=field,
    )
    if (
        contract["record_kind"] != expected_kind
        or contract["schema_version"] != "1"
    ):
        raise RecordValidationError(f"{field} has wrong identity")
    for name in (
        "model_id",
        "request_grammar",
        "response_grammar",
        "seeded_call_grammar",
        "stateless_client_attestation",
        "nominal_type",
        "build_id",
    ):
        _exact_text(contract[name], field=f"{field}.{name}")
    if contract["seeded_call_grammar"] != "call-seed-v1":
        raise RecordValidationError(f"{field} has wrong seeded-call grammar")
    contract_tokenizer = _artifact_ref(
        contract["tokenizer_ref"],
        field=f"{field}.tokenizer_ref",
    )
    if contract_tokenizer != tokenizer_ref:
        raise RecordValidationError(f"{field} tokenizer differs from manifest")
    _read_ref(contract_tokenizer, run_root=run_root)
    for name in ("prompt_template_ref", "tool_schema_ref"):
        nested_ref = _artifact_ref(contract[name], field=f"{field}.{name}")
        _read_ref(nested_ref, run_root=run_root)
    _validate_named_caps(
        contract["aggregate_caps"],
        fields={"generated_tokens", "model_calls", "turns"},
        field=f"{field}.aggregate_caps",
    )
    _validate_named_caps(
        contract["per_call_caps"],
        fields={"generated_tokens", "turns"},
        field=f"{field}.per_call_caps",
    )
    _validate_source_revisions(
        contract["source_revision_refs"],
        field=f"{field}.source_revision_refs",
        manifest_revisions=manifest_revisions,
        run_root=run_root,
    )


def _validate_parser_contract(
    ref: ArtifactRef,
    *,
    manifest_revisions: tuple[ArtifactRef, ...],
    run_root: Path,
) -> None:
    field = "tool parser contract"
    contract = _closed_mapping(
        _read_json_ref(ref, run_root=run_root, field=field, canonical=True),
        fields={
            "record_kind",
            "schema_version",
            "nominal_type",
            "build_id",
            "response_grammar",
            "tool_schema_ref",
            "source_revision_refs",
        },
        field=field,
    )
    if (
        contract["record_kind"] != "prefix_tool_parser_contract_v1"
        or contract["schema_version"] != "1"
    ):
        raise RecordValidationError(f"{field} has wrong identity")
    for name in ("nominal_type", "build_id", "response_grammar"):
        _exact_text(contract[name], field=f"{field}.{name}")
    tool_schema_ref = _artifact_ref(
        contract["tool_schema_ref"],
        field=f"{field}.tool_schema_ref",
    )
    _read_ref(tool_schema_ref, run_root=run_root)
    _validate_source_revisions(
        contract["source_revision_refs"],
        field=f"{field}.source_revision_refs",
        manifest_revisions=manifest_revisions,
        run_root=run_root,
    )


def _validate_meter_contract(
    ref: ArtifactRef,
    *,
    manifest_revisions: tuple[ArtifactRef, ...],
    run_root: Path,
) -> None:
    field = "meter contract"
    contract = _closed_mapping(
        _read_json_ref(ref, run_root=run_root, field=field, canonical=True),
        fields={
            "record_kind",
            "schema_version",
            "nominal_type",
            "build_id",
            "clock_source_ref",
            "watchdog_source_ref",
            "cost_units",
            "provider_event_grammar",
            "settlement_grammar",
            "zero_cost_synthetic_closure",
            "source_revision_refs",
        },
        field=field,
    )
    if (
        contract["record_kind"] != "prefix_meter_contract_v1"
        or contract["schema_version"] != "1"
    ):
        raise RecordValidationError(f"{field} has wrong identity")
    for name in (
        "nominal_type",
        "build_id",
        "provider_event_grammar",
        "settlement_grammar",
    ):
        _exact_text(contract[name], field=f"{field}.{name}")
    for name in ("clock_source_ref", "watchdog_source_ref"):
        nested_ref = _artifact_ref(contract[name], field=f"{field}.{name}")
        _read_ref(nested_ref, run_root=run_root)
    units = _closed_mapping(
        contract["cost_units"],
        fields={"currency", "generated_tokens", "model_calls", "wall_clock"},
        field=f"{field}.cost_units",
    )
    for name, unit in units.items():
        _exact_text(unit, field=f"{field}.cost_units.{name}")
    if type(contract["zero_cost_synthetic_closure"]) is not bool:
        raise RecordValidationError(
            f"{field}.zero_cost_synthetic_closure must be exact bool"
        )
    _validate_source_revisions(
        contract["source_revision_refs"],
        field=f"{field}.source_revision_refs",
        manifest_revisions=manifest_revisions,
        run_root=run_root,
    )


def _validate_task_input(
    ref: ArtifactRef,
    *,
    task_id: str,
    benchmark: str,
    run_root: Path,
) -> bool:
    field = f"task input {task_id!r}"
    task_input = _closed_mapping(
        _read_json_ref(ref, run_root=run_root, field=field, canonical=True),
        fields={
            "record_kind",
            "schema_version",
            "task_id",
            "benchmark",
            "requires_user_simulator",
            "canonical_task_payload",
        },
        field=field,
    )
    if (
        task_input["record_kind"] != "prefix_task_input_v1"
        or task_input["schema_version"] != "1"
    ):
        raise RecordValidationError(f"{field} has wrong identity")
    if task_input["task_id"] != task_id:
        raise RecordValidationError(f"{field} task binding mismatch")
    if task_input["benchmark"] != benchmark:
        raise RecordValidationError(f"{field} benchmark binding mismatch")
    if type(task_input["requires_user_simulator"]) is not bool:
        raise RecordValidationError(
            f"{field}.requires_user_simulator must be exact bool"
        )
    if not isinstance(task_input["canonical_task_payload"], Mapping):
        raise RecordValidationError(
            f"{field}.canonical_task_payload must be an object"
        )
    return cast(bool, task_input["requires_user_simulator"])


def _validate_task_contract(
    ref: ArtifactRef,
    *,
    contract_kind: str,
    task_id: str,
    benchmark: str,
    manifest_revisions: tuple[ArtifactRef, ...],
    run_root: Path,
) -> None:
    record_kind = f"prefix_{contract_kind}_contract_v1"
    field = f"{contract_kind} contract for {task_id!r}"
    common_fields = {
        "record_kind",
        "schema_version",
        "task_id",
        "benchmark",
        "build_id",
        "source_revision_refs",
    }
    if contract_kind == "environment":
        fields = common_fields | {
            "nominal_factory_type",
            "snapshot_grammar",
            "restore_grammar",
            "raw_evidence_grammar",
            "runtime_id",
            "container_digest",
        }
    elif contract_kind in ("grader", "verifier"):
        fields = common_fields | {
            "nominal_type",
            "raw_evidence_grammar",
            "runtime_id",
            "container_digest",
        }
    elif contract_kind == "isolation":
        fields = common_fields | {
            "distinct_environment_instances",
            "distinct_processes",
            "distinct_roots",
            "no_shared_writable_state",
            "qualification_ref",
        }
    else:
        raise AssertionError("unregistered task contract kind")
    contract = _closed_mapping(
        _read_json_ref(ref, run_root=run_root, field=field, canonical=True),
        fields=fields,
        field=field,
    )
    if (
        contract["record_kind"] != record_kind
        or contract["schema_version"] != "1"
    ):
        raise RecordValidationError(f"{field} has wrong identity")
    if contract["task_id"] != task_id:
        raise RecordValidationError(f"{field} task binding mismatch")
    if contract["benchmark"] != benchmark:
        raise RecordValidationError(f"{field} benchmark binding mismatch")
    _exact_text(contract["build_id"], field=f"{field}.build_id")
    if contract_kind == "environment":
        text_fields: tuple[str, ...] = (
            "nominal_factory_type",
            "snapshot_grammar",
            "restore_grammar",
            "raw_evidence_grammar",
            "runtime_id",
            "container_digest",
        )
    elif contract_kind in ("grader", "verifier"):
        text_fields = (
            "nominal_type",
            "raw_evidence_grammar",
            "runtime_id",
            "container_digest",
        )
    else:
        text_fields = ()
        for name in (
            "distinct_environment_instances",
            "distinct_processes",
            "distinct_roots",
            "no_shared_writable_state",
        ):
            if contract[name] is not True:
                raise RecordValidationError(f"{field}.{name} must equal true")
        qualification_ref = _artifact_ref(
            contract["qualification_ref"],
            field=f"{field}.qualification_ref",
        )
        _read_ref(qualification_ref, run_root=run_root)
    for name in text_fields:
        _exact_text(contract[name], field=f"{field}.{name}")
    _validate_source_revisions(
        contract["source_revision_refs"],
        field=f"{field}.source_revision_refs",
        manifest_revisions=manifest_revisions,
        run_root=run_root,
    )


def _prefix_caps(value: object, *, field: str) -> PrefixCaps:
    caps = _validate_named_caps(value, fields=_CAP_FIELDS, field=field)
    return PrefixCaps(**caps)


def _branch_caps(value: object, *, field: str) -> BranchCaps:
    mapping = _closed_mapping(
        value,
        fields=_CAP_FIELDS | {"pending_prefix_calls_count_against_tool_cap"},
        field=field,
    )
    if mapping["pending_prefix_calls_count_against_tool_cap"] is not True:
        raise RecordValidationError(
            f"{field}.pending_prefix_calls_count_against_tool_cap must equal true"
        )
    caps = {
        name: _exact_nonnegative_int(mapping[name], field=f"{field}.{name}")
        for name in _CAP_FIELDS
    }
    return BranchCaps(
        **caps,
        pending_prefix_calls_count_against_tool_cap=True,
    )


def _simulator_caps(value: object, *, field: str) -> SimulatorCaps:
    caps = _validate_named_caps(
        value,
        fields=_SIMULATOR_CAP_FIELDS,
        field=field,
    )
    return SimulatorCaps(**caps)


def _validate_provider_lane_plan(
    value: object,
    *,
    run_root: Path,
    registry: dict[str, object],
    tokenizer_ref: ArtifactRef,
    manifest_revisions: tuple[ArtifactRef, ...],
) -> _ValidatedProviderPlan:
    plan = _closed_mapping(
        value,
        fields={"record_kind", "schema_version", "lanes", "task_lanes"},
        field="provider lane plan",
    )
    if (
        plan["record_kind"] != "provider_lane_plan_v2"
        or plan["schema_version"] != "2"
    ):
        raise RecordValidationError("provider lane plan has wrong identity")
    registry_tasks = cast(list[dict[str, object]], registry["tasks"])
    registry_by_id = {
        cast(str, task["task_id"]): task
        for task in registry_tasks
    }
    lanes_value = plan["lanes"]
    if not isinstance(lanes_value, list) or not lanes_value:
        raise RecordValidationError("provider lane plan lanes must be non-empty")
    lanes: list[_Lane] = []
    lane_ids: set[str] = set()
    for ordinal, lane_value in enumerate(lanes_value):
        field = f"provider lane plan lanes[{ordinal}]"
        lane = _closed_mapping(
            lane_value,
            fields={
                "ordinal",
                "lane_id",
                "prefix_caps",
                "branch_caps",
                "simulator_caps",
                "subject_contract_ref",
                "simulator_contract_ref",
                "tool_parser_contract_ref",
                "meter_contract_ref",
            },
            field=field,
        )
        if type(lane["ordinal"]) is not int or lane["ordinal"] != ordinal:
            raise RecordValidationError(
                "provider lanes must have contiguous zero-based ordinals"
            )
        lane_id = _exact_text(lane["lane_id"], field=f"{field}.lane_id")
        if lane_id in lane_ids:
            raise RecordValidationError("provider lane IDs must be unique")
        lane_ids.add(lane_id)
        subject_ref = _artifact_ref(
            lane["subject_contract_ref"],
            field=f"{field}.subject_contract_ref",
        )
        simulator_ref = (
            None
            if lane["simulator_contract_ref"] is None
            else _artifact_ref(
                lane["simulator_contract_ref"],
                field=f"{field}.simulator_contract_ref",
            )
        )
        parser_ref = _artifact_ref(
            lane["tool_parser_contract_ref"],
            field=f"{field}.tool_parser_contract_ref",
        )
        meter_ref = _artifact_ref(
            lane["meter_contract_ref"],
            field=f"{field}.meter_contract_ref",
        )
        _validate_call_contract(
            subject_ref,
            expected_kind="prefix_subject_contract_v1",
            tokenizer_ref=tokenizer_ref,
            manifest_revisions=manifest_revisions,
            run_root=run_root,
            field=f"{field} subject contract",
        )
        if simulator_ref is not None:
            _validate_call_contract(
                simulator_ref,
                expected_kind="prefix_simulator_contract_v1",
                tokenizer_ref=tokenizer_ref,
                manifest_revisions=manifest_revisions,
                run_root=run_root,
                field=f"{field} simulator contract",
            )
        _validate_parser_contract(
            parser_ref,
            manifest_revisions=manifest_revisions,
            run_root=run_root,
        )
        _validate_meter_contract(
            meter_ref,
            manifest_revisions=manifest_revisions,
            run_root=run_root,
        )
        lanes.append(
            _Lane(
                ordinal=ordinal,
                lane_id=lane_id,
                prefix_caps=_prefix_caps(
                    lane["prefix_caps"],
                    field=f"{field}.prefix_caps",
                ),
                branch_caps=_branch_caps(
                    lane["branch_caps"],
                    field=f"{field}.branch_caps",
                ),
                simulator_caps=_simulator_caps(
                    lane["simulator_caps"],
                    field=f"{field}.simulator_caps",
                ),
                subject_contract_ref=subject_ref,
                simulator_contract_ref=simulator_ref,
                tool_parser_contract_ref=parser_ref,
                meter_contract_ref=meter_ref,
            )
        )

    task_lanes_value = plan["task_lanes"]
    if not isinstance(task_lanes_value, list):
        raise RecordValidationError("provider task_lanes must be an array")
    task_lanes: list[_TaskLane] = []
    prior_task_id: bytes | None = None
    for index, row_value in enumerate(task_lanes_value):
        field = f"provider lane plan task_lanes[{index}]"
        row = _closed_mapping(
            row_value,
            fields={
                "task_id",
                "prefix_lane_ordinal",
                "lane_ordinals_by_execution_rank",
                "task_input_ref",
                "environment_contract_ref",
                "grader_contract_ref",
                "verifier_contract_ref",
                "isolation_contract_ref",
            },
            field=field,
        )
        task_id = _exact_text(row["task_id"], field=f"{field}.task_id")
        task_id_bytes = task_id.encode("utf-8")
        if prior_task_id is not None and task_id_bytes <= prior_task_id:
            raise RecordValidationError(
                "provider task lanes are not strict task-ID sorted"
            )
        prior_task_id = task_id_bytes
        prefix_ordinal = _exact_nonnegative_int(
            row["prefix_lane_ordinal"],
            field=f"{field}.prefix_lane_ordinal",
        )
        rank_ordinals = row["lane_ordinals_by_execution_rank"]
        if (
            not isinstance(rank_ordinals, list)
            or len(rank_ordinals) != 4
        ):
            raise RecordValidationError(
                f"{field}.lane_ordinals_by_execution_rank must have four items"
            )
        exact_rank_ordinals = tuple(
            _exact_nonnegative_int(
                item,
                field=f"{field}.lane_ordinals_by_execution_rank[{rank}]",
            )
            for rank, item in enumerate(rank_ordinals)
        )
        all_ordinals = (prefix_ordinal, *exact_rank_ordinals)
        if any(ordinal >= len(lanes) for ordinal in all_ordinals):
            raise RecordValidationError("provider task lane ordinal is out of range")
        registry_task = registry_by_id.get(task_id)
        if registry_task is None:
            raise RecordValidationError(
                "provider task lanes do not exactly cover the task registry"
            )
        benchmark = cast(str, registry_task["benchmark"])
        refs = {
            name: _artifact_ref(
                row[f"{name}_ref"],
                field=f"{field}.{name}_ref",
            )
            for name in (
                "task_input",
                "environment_contract",
                "grader_contract",
                "verifier_contract",
                "isolation_contract",
            )
        }
        requires_simulator = _validate_task_input(
            refs["task_input"],
            task_id=task_id,
            benchmark=benchmark,
            run_root=run_root,
        )
        for contract_kind in ("environment", "grader", "verifier", "isolation"):
            _validate_task_contract(
                refs[f"{contract_kind}_contract"],
                contract_kind=contract_kind,
                task_id=task_id,
                benchmark=benchmark,
                manifest_revisions=manifest_revisions,
                run_root=run_root,
            )
        task_lanes.append(
            _TaskLane(
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
                requires_user_simulator=requires_simulator,
            )
        )
    if {row.task_id for row in task_lanes} != set(registry_by_id):
        raise RecordValidationError(
            "provider task lanes do not exactly cover the task registry"
        )
    for validated_lane in lanes:
        assigned = [
            row
            for row in task_lanes
            if validated_lane.ordinal
            in (
                row.prefix_lane_ordinal,
                *row.lane_ordinals_by_execution_rank,
            )
        ]
        if (
            validated_lane.simulator_contract_ref is None
            and any(row.requires_user_simulator for row in assigned)
        ):
            raise RecordValidationError(
                "provider lane "
                f"{validated_lane.lane_id!r} is missing a required simulator"
            )
    return _ValidatedProviderPlan(tuple(lanes), tuple(task_lanes))


def _manifest_ref(value: object, *, field: str) -> ArtifactRef:
    return _artifact_ref(value, field=field)


def load_prefix_execution_authority(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    task_id: str,
) -> PrefixExecutionAuthority:
    """Reconstruct one selected task's execution policy from sealed ancestry."""

    if type(run_root) is not type(Path()):
        raise TypeError("run_root must be an exact platform Path")
    if type(schedule_ref) is not ArtifactRef:
        raise TypeError("schedule_ref must be an exact ArtifactRef")
    if type(task_id) is not str:
        raise TypeError("task_id must be exact text")
    if not task_id:
        raise ValueError("task_id must be non-empty")
    root = run_root.resolve(strict=True)
    schedule = _load_direct_scientific_parent(
        asdict(schedule_ref),
        run_root=root,
        field="schedule_ref",
        expected_kind="resampling_prefix_schedule",
    )
    schedule_payload = cast(dict[str, object], schedule.value["payload"])
    manifest_ref = _manifest_ref(
        schedule_payload["manifest_ref"],
        field="schedule manifest_ref",
    )
    manifest = _load_direct_scientific_parent(
        asdict(manifest_ref),
        run_root=root,
        field="schedule manifest_ref",
        expected_kind="resampling_study_manifest",
    )
    if (
        schedule.value["study_id"] != manifest.value["study_id"]
        or schedule.value["frozen_created_at"] != manifest.value["frozen_created_at"]
        or schedule.value["provenance"] != manifest.value["provenance"]
    ):
        raise RecordValidationError("schedule and manifest envelopes differ")
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
    task_schedule = _task_schedule(selected[0], field="selected schedule task")
    manifest_payload = cast(dict[str, object], manifest.value["payload"])
    registry_ref = _artifact_ref(
        manifest_payload["task_registry_ref"],
        field="manifest task_registry_ref",
    )
    registry = _read_json_ref(
        registry_ref,
        run_root=root,
        field="task registry",
        canonical=False,
    )
    if (
        set(registry) != {"record_kind", "schema_version", "tasks"}
        or registry.get("record_kind") != "resampling_task_registry_v1"
    ):
        raise RecordValidationError("task registry has wrong shape or identity")
    _validate_task_registry(registry)
    registry_by_id = {
        cast(str, task["task_id"]): task
        for task in cast(list[dict[str, object]], registry["tasks"])
    }
    registry_task = registry_by_id.get(task_id)
    if registry_task is None:
        raise RecordValidationError("scheduled task is absent from task registry")
    scheduled_task = cast(Mapping[str, object], cast(Mapping[str, object], selected[0])["task"])
    if (
        scheduled_task.get("benchmark") != registry_task["benchmark"]
        or scheduled_task.get("stratum") != registry_task["stratum"]
        or scheduled_task.get("lineage") != registry_task["lineage"]
        or scheduled_task.get("sensitivity_groups") != registry_task["groups"]
    ):
        raise RecordValidationError(
            "selected schedule task differs from task registry binding"
        )
    tokenizer_ref = _artifact_ref(
        manifest_payload["tokenizer_ref"],
        field="manifest tokenizer_ref",
    )
    _read_ref(tokenizer_ref, run_root=root)
    revisions_value = manifest_payload["source_revision_refs"]
    if not isinstance(revisions_value, list) or not revisions_value:
        raise RecordValidationError(
            "manifest source_revision_refs must be a non-empty array"
        )
    manifest_revisions = tuple(
        _artifact_ref(value, field=f"manifest source_revision_refs[{index}]")
        for index, value in enumerate(revisions_value)
    )
    for revision_ref in manifest_revisions:
        _read_ref(revision_ref, run_root=root)
    provider_ref = _artifact_ref(
        manifest_payload["provider_lane_plan_ref"],
        field="manifest provider_lane_plan_ref",
    )
    provider_plan = _read_json_ref(
        provider_ref,
        run_root=root,
        field="provider lane plan",
        canonical=False,
    )
    validated_plan = _validate_provider_lane_plan(
        provider_plan,
        run_root=root,
        registry=registry,
        tokenizer_ref=tokenizer_ref,
        manifest_revisions=manifest_revisions,
    )
    task_rows = [
        row for row in validated_plan.task_lanes if row.task_id == task_id
    ]
    if len(task_rows) != 1:
        raise RecordValidationError("selected task has no unique provider row")
    task_row = task_rows[0]
    selected_lane = validated_plan.lanes[task_row.prefix_lane_ordinal]
    if task_schedule.provider_lane != selected_lane.lane_id:
        raise RecordValidationError(
            "provider lane mismatch between schedule and provider plan"
        )
    for slot in task_schedule.slots.slots:
        expected_lane = task_row.lane_ordinals_by_execution_rank[
            slot.execution_order
        ]
        if slot.hardware_lane != expected_lane:
            raise RecordValidationError(
                "schedule slot lane mismatch with provider plan"
            )
    if (
        task_row.requires_user_simulator
        and selected_lane.simulator_contract_ref is None
    ):
        raise RecordValidationError("selected task is missing a required simulator")
    return PrefixExecutionAuthority(
        schedule_ref=schedule_ref,
        manifest_ref=manifest_ref,
        provider_lane_plan_ref=provider_ref,
        task_schedule=task_schedule,
        prefix_caps=selected_lane.prefix_caps,
        branch_caps=selected_lane.branch_caps,
        simulator_caps=selected_lane.simulator_caps,
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


__all__ = (
    "PrefixExecutionAuthority",
    "load_prefix_execution_authority",
)
