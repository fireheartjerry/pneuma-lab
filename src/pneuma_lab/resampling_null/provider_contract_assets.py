"""Provider contract asset decoding and closure validation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

from .authority_refs import (
    AuthorityRefReader,
    closed_mapping,
    decode_artifact_ref,
    exact_nonnegative_int,
    exact_text,
    walk_artifact_refs,
)
from .errors import RecordValidationError
from .prefix_contracts import (
    AUTHORITY_ASSET_ROLE_MEDIA,
    ImplementationDescriptor,
    ImplementationPurpose,
    SyntheticPrefixProgram,
    load_promoted_authority_asset,
    load_synthetic_prefix_program,
)
from .types import (
    ArtifactRef,
    BranchCaps,
    CallContractCaps,
    PrefixCaps,
    SubjectTurn,
    TriggerReason,
)

CAP_FIELDS = (
    "generated_tokens",
    "model_calls",
    "tool_calls",
    "wall_clock_ms",
)
CALL_CONTRACT_CAP_FIELDS = (
    "aggregate_generated_tokens",
    "aggregate_model_calls",
    "aggregate_turns",
    "per_call_generated_tokens",
    "per_call_turns",
)
CALL_CONTRACT_FIELDS = (
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
)


@dataclass(frozen=True, slots=True)
class ValidatedCallContract:
    caps: CallContractCaps
    request_grammar: str
    response_grammar: str
    tool_schema_ref: ArtifactRef
    descriptors: tuple[ImplementationDescriptor, ...]


@dataclass(frozen=True, slots=True)
class ValidatedParserContract:
    response_grammar: str
    tool_schema_ref: ArtifactRef
    descriptor: ImplementationDescriptor


@dataclass(frozen=True, slots=True)
class ValidatedMeterContract:
    zero_cost: bool
    descriptors: tuple[ImplementationDescriptor, ...]


@dataclass(frozen=True, slots=True)
class ValidatedTaskInput:
    requires_user_simulator: bool
    program_ref: ArtifactRef | None
    program: SyntheticPrefixProgram | None
    actor_roles: tuple[Literal["primary_subject", "user_simulator"], ...]


def _synthetic_actor_roles(
    task_input: Mapping[str, object],
    *,
    transcript_length: int,
) -> tuple[Literal["primary_subject", "user_simulator"], ...]:
    """Derive the worker's exact environment-controlled actor sequence."""

    canonical_payload = task_input.get("canonical_task_payload")
    actor_value = (
        canonical_payload.get("synthetic_actor_order")
        if type(canonical_payload) is dict
        else task_input.get("synthetic_actor_order")
    )
    if actor_value is None:
        return tuple("primary_subject" for _ in range(transcript_length))
    if (
        type(actor_value) is not list
        or len(actor_value) != transcript_length
        or any(
            type(role) is not str or role not in ("primary_subject", "user_simulator")
            for role in actor_value
        )
    ):
        raise RecordValidationError("task actor order is invalid")
    return cast(
        tuple[Literal["primary_subject", "user_simulator"], ...],
        tuple(actor_value),
    )


def _closed_mapping(
    value: object,
    *,
    fields: set[str],
    field: str,
) -> dict[str, object]:
    return closed_mapping(value, fields=fields, field=field)


def _exact_text(value: object, *, field: str) -> str:
    return exact_text(value, field=field)


def _exact_nonnegative_int(value: object, *, field: str) -> int:
    return exact_nonnegative_int(value, field=field)


def decode_contract_ref(
    value: object,
    *,
    field: str,
    expected_role: str | None = None,
) -> ArtifactRef:
    ref = decode_artifact_ref(
        value,
        field=field,
        expected_role=expected_role,
    )
    if expected_role is not None:
        expected_media = AUTHORITY_ASSET_ROLE_MEDIA.get(expected_role)
        if expected_media is not None and ref.media_type != expected_media:
            raise RecordValidationError(
                f"{field} media type must equal {expected_media!r}"
            )
    return ref


def _verify_ref_closure(
    ref: ArtifactRef,
    *,
    reader: AuthorityRefReader,
    field: str,
    expected_role: str | None = None,
    visited: set[ArtifactRef] | None = None,
) -> object:
    return reader.verify_closure(
        ref,
        field=field,
        expected_role=expected_role,
        visited=visited,
    )


def _read_json_ref(
    ref: ArtifactRef,
    *,
    reader: AuthorityRefReader,
    field: str,
    canonical: bool,
    expected_role: str,
) -> dict[str, object]:
    return reader.decode_json(
        ref,
        field=field,
        canonical=canonical,
        expected_role=expected_role,
    )


def _verify_registered_authority_graph(
    value: object,
    *,
    reader: AuthorityRefReader,
    field: str,
) -> None:
    pending = list(walk_artifact_refs(value))
    observed: set[ArtifactRef] = set()
    ordered: list[ArtifactRef] = []
    while pending:
        ref = pending.pop(0)
        if ref in observed:
            continue
        observed.add(ref)
        expected_media = AUTHORITY_ASSET_ROLE_MEDIA.get(ref.role)
        if expected_media is None:
            raise RecordValidationError(f"{field} ref has unregistered authority role")
        if ref.media_type != expected_media:
            raise RecordValidationError(f"{field} ref has noncanonical media type")
        ordered.append(ref)
        if expected_media == "application/json":
            nested = reader.decode_json(
                ref,
                field=f"{field} ref",
                canonical=True,
                expected_role=ref.role,
            )
            pending.extend(walk_artifact_refs(nested))
    closure_visited: set[ArtifactRef] = set()
    for index, ref in enumerate(ordered):
        reader.verify_closure(
            ref,
            field=f"{field} ref {index}",
            expected_role=ref.role,
            visited=closure_visited,
        )


def _validate_source_revisions(
    value: object,
    *,
    field: str,
    manifest_revisions: tuple[ArtifactRef, ...],
    reader: AuthorityRefReader,
) -> tuple[ArtifactRef, ...]:
    if not isinstance(value, list) or not value:
        raise RecordValidationError(f"{field} must be a non-empty array")
    refs = tuple(
        decode_contract_ref(
            item,
            field=f"{field}[{index}]",
            expected_role="source_revision",
        )
        for index, item in enumerate(value)
    )
    if len(refs) != len(set(refs)):
        raise RecordValidationError(f"{field} must not contain duplicates")
    if any(ref not in manifest_revisions for ref in refs):
        raise RecordValidationError(f"{field} contains a non-manifest source revision")
    for ref in refs:
        _verify_ref_closure(
            ref,
            reader=reader,
            field=field,
            expected_role="source_revision",
        )
    return refs


def _validate_named_caps(
    value: object,
    *,
    fields: tuple[str, ...],
    field: str,
) -> dict[str, int]:
    mapping = _closed_mapping(value, fields=set(fields), field=field)
    return {
        name: _exact_nonnegative_int(mapping[name], field=f"{field}.{name}")
        for name in fields
    }


def validate_call_contract(
    ref: ArtifactRef,
    *,
    expected_kind: str,
    tokenizer_ref: ArtifactRef,
    manifest_revisions: tuple[ArtifactRef, ...],
    reader: AuthorityRefReader,
    field: str,
) -> ValidatedCallContract:
    expected_role = (
        "subject_contract"
        if expected_kind == "prefix_subject_contract_v1"
        else "simulator_contract"
    )
    value = _read_json_ref(
        ref,
        reader=reader,
        field=field,
        canonical=True,
        expected_role=expected_role,
    )
    contract = _closed_mapping(
        value,
        fields=set(CALL_CONTRACT_FIELDS),
        field=field,
    )
    if contract["record_kind"] != expected_kind or contract["schema_version"] != "1":
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
    contract_tokenizer = decode_contract_ref(
        contract["tokenizer_ref"],
        field=f"{field}.tokenizer_ref",
        expected_role="tokenizer",
    )
    if contract_tokenizer != tokenizer_ref:
        raise RecordValidationError(f"{field} tokenizer differs from manifest")
    _verify_ref_closure(
        contract_tokenizer,
        reader=reader,
        field=f"{field}.tokenizer_ref",
        expected_role="tokenizer",
    )
    prompt_ref = decode_contract_ref(
        contract["prompt_template_ref"],
        field=f"{field}.prompt_template_ref",
        expected_role="prompt_template",
    )
    _verify_ref_closure(
        prompt_ref,
        reader=reader,
        field=f"{field}.prompt_template_ref",
        expected_role="prompt_template",
    )
    tool_schema_ref = decode_contract_ref(
        contract["tool_schema_ref"],
        field=f"{field}.tool_schema_ref",
        expected_role="tool_schema",
    )
    _verify_ref_closure(
        tool_schema_ref,
        reader=reader,
        field=f"{field}.tool_schema_ref",
        expected_role="tool_schema",
    )
    aggregate = _validate_named_caps(
        contract["aggregate_caps"],
        fields=("generated_tokens", "model_calls", "turns"),
        field=f"{field}.aggregate_caps",
    )
    per_call = _validate_named_caps(
        contract["per_call_caps"],
        fields=("generated_tokens", "turns"),
        field=f"{field}.per_call_caps",
    )
    if (
        per_call["generated_tokens"] > aggregate["generated_tokens"]
        or per_call["turns"] > aggregate["turns"]
    ):
        raise RecordValidationError(
            f"{field} per-call caps cannot exceed aggregate caps"
        )
    source_refs = _validate_source_revisions(
        contract["source_revision_refs"],
        field=f"{field}.source_revision_refs",
        manifest_revisions=manifest_revisions,
        reader=reader,
    )
    if len(source_refs) != 1:
        raise RecordValidationError(
            f"{field} requires exactly one implementation source ref"
        )
    purpose = (
        "subject" if expected_kind == "prefix_subject_contract_v1" else "simulator"
    )
    source_ref = source_refs[0]
    request_grammar = cast(str, contract["request_grammar"])
    response_grammar = cast(str, contract["response_grammar"])
    descriptors = (
        ImplementationDescriptor(
            purpose=cast(ImplementationPurpose, purpose),
            nominal_type=cast(str, contract["nominal_type"]),
            build_id=cast(str, contract["build_id"]),
            request_grammar=request_grammar,
            response_grammar=response_grammar,
            snapshot_grammar=None,
            restore_grammar=None,
            evidence_grammar=None,
            runtime_id=None,
            container_digest=None,
            implementation_source_ref=source_ref,
        ),
        *(
            (
                ImplementationDescriptor(
                    purpose="request_renderer",
                    nominal_type=(
                        "pneuma_lab.resampling_null.synthetic_prefix_loop."
                        "SyntheticRequestRenderer"
                    ),
                    build_id="synthetic-request-renderer-v1",
                    request_grammar=request_grammar,
                    response_grammar=None,
                    snapshot_grammar=None,
                    restore_grammar=None,
                    evidence_grammar=None,
                    runtime_id=None,
                    container_digest=None,
                    implementation_source_ref=source_ref,
                ),
            )
            if purpose == "subject"
            else ()
        ),
    )
    return ValidatedCallContract(
        caps=CallContractCaps(
            aggregate_generated_tokens=aggregate["generated_tokens"],
            aggregate_model_calls=aggregate["model_calls"],
            aggregate_turns=aggregate["turns"],
            per_call_generated_tokens=per_call["generated_tokens"],
            per_call_turns=per_call["turns"],
        ),
        request_grammar=request_grammar,
        response_grammar=response_grammar,
        tool_schema_ref=tool_schema_ref,
        descriptors=descriptors,
    )


def validate_parser_contract(
    ref: ArtifactRef,
    *,
    manifest_revisions: tuple[ArtifactRef, ...],
    reader: AuthorityRefReader,
) -> ValidatedParserContract:
    field = "tool parser contract"
    contract = _closed_mapping(
        _read_json_ref(
            ref,
            reader=reader,
            field=field,
            canonical=True,
            expected_role="tool_parser_contract",
        ),
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
    tool_schema_ref = decode_contract_ref(
        contract["tool_schema_ref"],
        field=f"{field}.tool_schema_ref",
        expected_role="tool_schema",
    )
    _verify_ref_closure(
        tool_schema_ref,
        reader=reader,
        field=f"{field}.tool_schema_ref",
        expected_role="tool_schema",
    )
    source_refs = _validate_source_revisions(
        contract["source_revision_refs"],
        field=f"{field}.source_revision_refs",
        manifest_revisions=manifest_revisions,
        reader=reader,
    )
    if len(source_refs) != 1:
        raise RecordValidationError(
            f"{field} requires exactly one implementation source ref"
        )
    return ValidatedParserContract(
        response_grammar=cast(str, contract["response_grammar"]),
        tool_schema_ref=tool_schema_ref,
        descriptor=ImplementationDescriptor(
            purpose="response_parser",
            nominal_type=cast(str, contract["nominal_type"]),
            build_id=cast(str, contract["build_id"]),
            request_grammar=None,
            response_grammar=cast(str, contract["response_grammar"]),
            snapshot_grammar=None,
            restore_grammar=None,
            evidence_grammar=None,
            runtime_id=None,
            container_digest=None,
            implementation_source_ref=source_refs[0],
        ),
    )


def validate_meter_contract(
    ref: ArtifactRef,
    *,
    manifest_revisions: tuple[ArtifactRef, ...],
    reader: AuthorityRefReader,
) -> ValidatedMeterContract:
    field = "meter contract"
    contract = _closed_mapping(
        _read_json_ref(
            ref,
            reader=reader,
            field=field,
            canonical=True,
            expected_role="meter_contract",
        ),
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
    for name, role in (
        ("clock_source_ref", "clock_source"),
        ("watchdog_source_ref", "watchdog_source"),
    ):
        nested_ref = decode_contract_ref(
            contract[name],
            field=f"{field}.{name}",
            expected_role=role,
        )
        _verify_ref_closure(
            nested_ref,
            reader=reader,
            field=f"{field}.{name}",
            expected_role=role,
        )
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
    source_refs = _validate_source_revisions(
        contract["source_revision_refs"],
        field=f"{field}.source_revision_refs",
        manifest_revisions=manifest_revisions,
        reader=reader,
    )
    if len(source_refs) != 1:
        raise RecordValidationError(
            f"{field} requires exactly one implementation source ref"
        )
    source_ref = source_refs[0]
    build_id = cast(str, contract["build_id"])
    event_grammar = cast(str, contract["provider_event_grammar"])
    settlement_grammar = cast(str, contract["settlement_grammar"])
    return ValidatedMeterContract(
        zero_cost=cast(bool, contract["zero_cost_synthetic_closure"]),
        descriptors=(
            ImplementationDescriptor(
                purpose="meter",
                nominal_type=cast(str, contract["nominal_type"]),
                build_id=build_id,
                request_grammar=None,
                response_grammar=None,
                snapshot_grammar=None,
                restore_grammar=None,
                evidence_grammar="synthetic-meter-v1",
                runtime_id=None,
                container_digest=None,
                implementation_source_ref=source_ref,
            ),
            ImplementationDescriptor(
                purpose="provider_event_codec",
                nominal_type=(
                    "pneuma_lab.resampling_null.synthetic_prefix_loop."
                    "SyntheticProviderEventCodec"
                ),
                build_id="synthetic-provider-event-codec-v1",
                request_grammar=None,
                response_grammar=None,
                snapshot_grammar=None,
                restore_grammar=None,
                evidence_grammar=event_grammar,
                runtime_id=None,
                container_digest=None,
                implementation_source_ref=source_ref,
            ),
            ImplementationDescriptor(
                purpose="settlement_codec",
                nominal_type=(
                    "pneuma_lab.resampling_null.synthetic_prefix_loop."
                    "SyntheticSettlementCodec"
                ),
                build_id="synthetic-settlement-codec-v1",
                request_grammar=None,
                response_grammar=None,
                snapshot_grammar=None,
                restore_grammar=None,
                evidence_grammar=settlement_grammar,
                runtime_id=None,
                container_digest=None,
                implementation_source_ref=source_ref,
            ),
        ),
    )


def validate_task_input(
    ref: ArtifactRef,
    *,
    task_id: str,
    benchmark: str,
    reader: AuthorityRefReader,
    require_execution_program: bool = False,
) -> ValidatedTaskInput:
    field = f"task input {task_id!r}"
    task_input_value = _read_json_ref(
        ref,
        reader=reader,
        field=field,
        canonical=True,
        expected_role="task_input",
    )
    base_fields = {
        "record_kind",
        "schema_version",
        "task_id",
        "benchmark",
        "requires_user_simulator",
        "canonical_task_payload",
    }
    expected_fields = (
        base_fields | {"synthetic_execution_program_ref"}
        if (
            require_execution_program
            or "synthetic_execution_program_ref" in task_input_value
        )
        else base_fields
    )
    task_input = _closed_mapping(
        task_input_value,
        fields=expected_fields,
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
        raise RecordValidationError(f"{field}.canonical_task_payload must be an object")
    _verify_registered_authority_graph(
        task_input["canonical_task_payload"],
        reader=reader,
        field=f"{field}.canonical_task_payload",
    )
    has_program = "synthetic_execution_program_ref" in task_input
    if not has_program:
        return ValidatedTaskInput(
            requires_user_simulator=cast(
                bool,
                task_input["requires_user_simulator"],
            ),
            program_ref=None,
            program=None,
            actor_roles=(),
        )
    program_ref = decode_contract_ref(
        task_input["synthetic_execution_program_ref"],
        field=f"{field}.synthetic_execution_program_ref",
        expected_role="synthetic_execution_program",
    )
    if program_ref.media_type != "application/json":
        raise RecordValidationError(
            f"{field}.synthetic_execution_program_ref must be application/json"
        )
    program_value = reader.verify_closure(
        program_ref,
        field=f"{field}.synthetic_execution_program_ref",
        expected_role="synthetic_execution_program",
    )
    if not isinstance(program_value, Mapping):
        raise RecordValidationError(f"{field} program must be a JSON object")
    _verify_registered_authority_graph(
        program_value,
        reader=reader,
        field=f"{field} program",
    )
    program_bytes = reader.read_bytes(program_ref)
    try:
        program = load_synthetic_prefix_program(program_bytes)
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} program is invalid: {exc}") from exc
    if program.task_id != task_id:
        raise RecordValidationError(f"{field} program task binding mismatch")
    reader.decode_json(
        program.tool_schema_ref,
        field=f"{field} program tool schema",
        canonical=True,
        expected_role="tool_schema",
    )
    try:
        decoded_schema = load_promoted_authority_asset(
            role="tool_schema",
            payload=reader.read_bytes(program.tool_schema_ref),
        )
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(
            f"{field} program tool schema is invalid: {exc}"
        ) from exc
    tool_names = cast(tuple[str, ...], decoded_schema.value)
    if (
        program.expected_trigger_reason is not TriggerReason.NO_INTERVENTION_OPPORTUNITY
        and not tool_names
    ):
        raise RecordValidationError(
            f"{field} trigger program requires a nonempty tool schema"
        )
    transcript_tools = {
        call.name
        for row in program.provider_transcript
        if row.typed_turn is not None
        for call in row.typed_turn.tool_calls
    }
    missing_tools = transcript_tools - set(tool_names)
    if missing_tools:
        raise RecordValidationError(
            f"{field} program names tools absent from its tool schema"
        )
    injection = program.failure_injection
    if injection.stage in ("provider_transport", "provider_parser"):
        if not any(
            row.subject_role == injection.subject_role
            and row.call_index == injection.call_index
            for row in program.provider_transcript
        ):
            raise RecordValidationError(
                f"{field} provider failure injection target is unreachable"
            )
    elif injection.stage == "tool":
        target_rows = [
            row
            for row in program.provider_transcript
            if row.subject_role == injection.subject_role
            and row.call_index == injection.call_index
            and row.typed_turn is not None
        ]
        if (
            len(target_rows) != 1
            or injection.tool_call_id
            not in {
                call.call_id
                for call in cast(SubjectTurn, target_rows[0].typed_turn).tool_calls
            }
            or injection.tool_call_id
            not in {item.call_id for item in program.tool_observations}
        ):
            raise RecordValidationError(
                f"{field} tool failure injection target is unreachable"
            )
    return ValidatedTaskInput(
        requires_user_simulator=cast(
            bool,
            task_input["requires_user_simulator"],
        ),
        program_ref=program_ref,
        program=program,
        actor_roles=_synthetic_actor_roles(
            task_input,
            transcript_length=len(program.provider_transcript),
        ),
    )


def validate_task_contract(
    ref: ArtifactRef,
    *,
    contract_kind: str,
    task_id: str,
    benchmark: str,
    manifest_revisions: tuple[ArtifactRef, ...],
    reader: AuthorityRefReader,
) -> ImplementationDescriptor | None:
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
        _read_json_ref(
            ref,
            reader=reader,
            field=field,
            canonical=True,
            expected_role=f"{contract_kind}_contract",
        ),
        fields=fields,
        field=field,
    )
    if contract["record_kind"] != record_kind or contract["schema_version"] != "1":
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
        qualification_ref = decode_contract_ref(
            contract["qualification_ref"],
            field=f"{field}.qualification_ref",
            expected_role="isolation_qualification",
        )
        _verify_ref_closure(
            qualification_ref,
            reader=reader,
            field=f"{field}.qualification_ref",
            expected_role="isolation_qualification",
        )
    for name in text_fields:
        _exact_text(contract[name], field=f"{field}.{name}")
    source_refs = _validate_source_revisions(
        contract["source_revision_refs"],
        field=f"{field}.source_revision_refs",
        manifest_revisions=manifest_revisions,
        reader=reader,
    )
    if contract_kind == "isolation":
        return None
    if len(source_refs) != 1:
        raise RecordValidationError(
            f"{field} requires exactly one implementation source ref"
        )
    source_ref = source_refs[0]
    if contract_kind == "environment":
        return ImplementationDescriptor(
            purpose="environment",
            nominal_type=cast(str, contract["nominal_factory_type"]),
            build_id=cast(str, contract["build_id"]),
            request_grammar=None,
            response_grammar=None,
            snapshot_grammar=cast(str, contract["snapshot_grammar"]),
            restore_grammar=cast(str, contract["restore_grammar"]),
            evidence_grammar=cast(str, contract["raw_evidence_grammar"]),
            runtime_id=cast(str, contract["runtime_id"]),
            container_digest=cast(str, contract["container_digest"]),
            implementation_source_ref=source_ref,
        )
    return ImplementationDescriptor(
        purpose=cast(ImplementationPurpose, contract_kind),
        nominal_type=cast(str, contract["nominal_type"]),
        build_id=cast(str, contract["build_id"]),
        request_grammar=None,
        response_grammar=None,
        snapshot_grammar=None,
        restore_grammar=None,
        evidence_grammar=cast(str, contract["raw_evidence_grammar"]),
        runtime_id=cast(str, contract["runtime_id"]),
        container_digest=cast(str, contract["container_digest"]),
        implementation_source_ref=source_ref,
    )


def decode_prefix_caps(value: object, *, field: str) -> PrefixCaps:
    caps = _validate_named_caps(value, fields=CAP_FIELDS, field=field)
    return PrefixCaps(**caps)


def decode_branch_caps(value: object, *, field: str) -> BranchCaps:
    mapping = _closed_mapping(
        value,
        fields=set(CAP_FIELDS) | {"pending_prefix_calls_count_against_tool_cap"},
        field=field,
    )
    if mapping["pending_prefix_calls_count_against_tool_cap"] is not True:
        raise RecordValidationError(
            f"{field}.pending_prefix_calls_count_against_tool_cap must equal true"
        )
    caps = {
        name: _exact_nonnegative_int(mapping[name], field=f"{field}.{name}")
        for name in CAP_FIELDS
    }
    return BranchCaps(
        **caps,
        pending_prefix_calls_count_against_tool_cap=True,
    )


def decode_call_contract_caps(value: object, *, field: str) -> CallContractCaps:
    caps = _validate_named_caps(
        value,
        fields=CALL_CONTRACT_CAP_FIELDS,
        field=field,
    )
    return CallContractCaps(**caps)


__all__ = (
    "ValidatedCallContract",
    "ValidatedParserContract",
    "ValidatedMeterContract",
    "ValidatedTaskInput",
    "decode_contract_ref",
    "decode_branch_caps",
    "decode_prefix_caps",
    "decode_call_contract_caps",
    "validate_call_contract",
    "validate_meter_contract",
    "validate_parser_contract",
    "validate_task_contract",
    "validate_task_input",
)
