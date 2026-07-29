"""Private controller-owned synthetic prefix execution.

This module can replay only sealed local fixture bytes. It has no provider,
model, network, credential, spend, branch, or publication path.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping, cast, final

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .authority_refs import AuthorityRefReader, closed_mapping, load_json_bytes
from .controller import derive_call_seed
from .controller_artifacts import ControllerArtifactStore
from .evidence import (
    AttemptBoundZeroCostClosure,
    CompletedToolBoundaryReceipt,
    ProviderAttemptStatus,
    ProviderCallAttemptReceipt,
    ProviderDispatchIntent,
    ProviderSettlement,
    SyntheticZeroAttemptCostClosure,
    ToolBoundaryLedger,
)
from .execution_authority import PrefixExecutionAuthority
from .prefix_contracts import (
    AUTHORITY_ASSET_ROLE_MEDIA,
    ImplementationDescriptor,
    RawProviderObservation,
    SyntheticClockRead,
    SyntheticPrefixProgram,
    SyntheticProviderTranscriptRow,
    StableSourceProvenance,
    load_synthetic_prefix_program,
)
from .synthetic_environment import (
    InitialQualificationAuthority,
    SyntheticByteTokenizer,
    SyntheticEnvironmentHandle,
    _InitialQualificationResult,
    _SnapshotState,
    _decode_snapshot_state,
    _open_qualified_initial_restore,
)
from .types import (
    ArtifactRef,
    CallContractCaps,
    FailureKind,
    PrefixCaps,
    ResourceCounters,
    SubjectTurn,
    ToolCall,
    TriggerReason,
)


TransportKind = Literal[
    "response",
    "provider_error",
    "infrastructure_error",
    "timeout_no_response",
]
ParserKind = Literal["turn", "refusal", "malformed", "not_applicable"]


REGISTERED_LOOP_DESCRIPTOR_FIELDS: Mapping[
    str,
    dict[str, object],
] = MappingProxyType(
    {
        "environment": {
            "purpose": "environment",
            "nominal_type": (
                "pneuma_lab.resampling_null.synthetic_environment."
                "SyntheticEnvironmentFactory"
            ),
            "build_id": "synthetic-environment-v1",
            "request_grammar": None,
            "response_grammar": None,
            "snapshot_grammar": "synthetic-environment-snapshot-v1",
            "restore_grammar": "synthetic-environment-snapshot-v1",
            "evidence_grammar": "synthetic-environment-evidence-v1",
            "runtime_id": "cpython-3.12-local",
            "container_digest": "sha256:" + "0" * 64,
        },
        "tokenizer": {
            "purpose": "tokenizer",
            "nominal_type": (
                "pneuma_lab.resampling_null.synthetic_environment."
                "SyntheticByteTokenizer"
            ),
            "build_id": "synthetic-byte-tokenizer-v1",
            "request_grammar": None,
            "response_grammar": None,
            "snapshot_grammar": None,
            "restore_grammar": None,
            "evidence_grammar": None,
            "runtime_id": None,
            "container_digest": None,
        },
        **{
            purpose: {
                "purpose": purpose,
                "nominal_type": (
                    "pneuma_lab.resampling_null.synthetic_prefix_loop."
                    + {
                        "subject": "SyntheticProviderActor",
                        "simulator": "SyntheticProviderActor",
                        "meter": "SyntheticTraceMeter",
                        "request_renderer": "SyntheticRequestRenderer",
                        "response_parser": "SyntheticResponseParser",
                        "grader": "SyntheticGradeCodec",
                        "verifier": "SyntheticVerifierCodec",
                        "provider_event_codec": "SyntheticProviderEventCodec",
                        "settlement_codec": "SyntheticSettlementCodec",
                    }[purpose]
                ),
                "build_id": f"synthetic-{purpose.replace('_', '-')}-v1",
                "request_grammar": (
                    "synthetic-request-v1"
                    if purpose in ("subject", "simulator", "request_renderer")
                    else None
                ),
                "response_grammar": (
                    "synthetic-response-v1"
                    if purpose in ("subject", "simulator", "response_parser")
                    else None
                ),
                "snapshot_grammar": None,
                "restore_grammar": None,
                "evidence_grammar": (
                    {
                        "meter": "synthetic-meter-v1",
                        "grader": "synthetic-grade-v1",
                        "verifier": "synthetic-verifier-v1",
                        "provider_event_codec": "synthetic-provider-event-v1",
                        "settlement_codec": "synthetic-provider-settlement-v1",
                    }.get(purpose)
                ),
                "runtime_id": (
                    "cpython-3.12-local" if purpose in ("grader", "verifier") else None
                ),
                "container_digest": (
                    "sha256:" + "0" * 64 if purpose in ("grader", "verifier") else None
                ),
            }
            for purpose in (
                "subject",
                "simulator",
                "meter",
                "request_renderer",
                "response_parser",
                "grader",
                "verifier",
                "provider_event_codec",
                "settlement_codec",
            )
        },
    }
)

_SOURCE_ROOT = Path(__file__).parents[3]
_SOURCE_PATH_BY_PURPOSE = MappingProxyType(
    {
        "environment": Path("src/pneuma_lab/resampling_null/synthetic_environment.py"),
        "tokenizer": Path("src/pneuma_lab/resampling_null/synthetic_environment.py"),
        **{
            purpose: Path("src/pneuma_lab/resampling_null/synthetic_prefix_loop.py")
            for purpose in REGISTERED_LOOP_DESCRIPTOR_FIELDS
            if purpose not in ("environment", "tokenizer")
        },
    }
)


@final
class SyntheticTraceMeter:
    """Fresh zero-position meter over one sealed named trace."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticTraceMeter is final")

    def __init__(
        self,
        *,
        program_bytes: bytes,
        clock_trace: tuple[SyntheticClockRead, ...],
    ) -> None:
        if type(program_bytes) is not bytes:
            raise TypeError("program_bytes must be exact bytes")
        if type(clock_trace) is not tuple or not all(
            type(read) is SyntheticClockRead for read in clock_trace
        ):
            raise TypeError("clock_trace must contain exact clock reads")
        self._program_sha256 = hashlib.sha256(program_bytes).hexdigest()
        self._trace = clock_trace
        self._position = 0
        self._last_value: int | None = None

    def read(self, *, label: str, program_sha256: str) -> int:
        if program_sha256 != self._program_sha256:
            raise ValueError("meter program digest differs from sealed program")
        if self._position >= len(self._trace):
            raise ValueError("meter trace is exhausted")
        row = self._trace[self._position]
        if row.label != label:
            raise ValueError(
                f"meter label differs: expected {row.label!r}, received {label!r}"
            )
        if self._last_value is not None and row.uint64_ms < self._last_value:
            raise ValueError("meter trace decreased")
        self._position += 1
        self._last_value = row.uint64_ms
        return row.uint64_ms

    def assert_exhausted(self) -> None:
        if self._position != len(self._trace):
            raise ValueError("meter trace has unread observations")


@final
class SyntheticRequestRenderer:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticRequestRenderer is final")

    def render(
        self,
        *,
        subject_role: Literal["primary_subject", "user_simulator"],
        context_bytes: bytes,
    ) -> bytes:
        return _render_request(
            subject_role=subject_role,
            context_bytes=context_bytes,
        )


@final
class SyntheticResponseParser:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticResponseParser is final")

    def parse(self, payload: bytes) -> tuple[ParserKind, SubjectTurn | None]:
        return _parse_response(payload)


@final
class SyntheticProviderEventCodec:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticProviderEventCodec is final")

    def decode_raw(self, payload: bytes) -> tuple[TransportKind, int]:
        return _decode_raw_event(payload)

    def encode_controller(
        self,
        *,
        row: SyntheticProviderTranscriptRow,
        intent_sha256: str,
        status: ProviderAttemptStatus,
        response_bytes: bytes | None,
        observed_at_ms: int,
    ) -> bytes:
        return _controller_event_bytes(
            row=row,
            intent_sha256=intent_sha256,
            status=status,
            response_bytes=response_bytes,
            observed_at_ms=observed_at_ms,
        )


@final
class SyntheticSettlementCodec:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticSettlementCodec is final")

    def encode(
        self,
        *,
        row: SyntheticProviderTranscriptRow,
        intent_sha256: str,
        attempt_sha256: str,
        provider_event_sha256: str,
    ) -> bytes:
        return _settlement_bytes(
            row=row,
            intent_sha256=intent_sha256,
            attempt_sha256=attempt_sha256,
            provider_event_sha256=provider_event_sha256,
        )


@final
class SyntheticGradeCodec:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticGradeCodec is final")


@final
class SyntheticVerifierCodec:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticVerifierCodec is final")


@dataclass(frozen=True, slots=True)
class _ValidatedProviderObservation:
    status: ProviderAttemptStatus
    parser_kind: ParserKind
    typed_turn: SubjectTurn | None
    output_token_ids: tuple[int, ...] | None
    generated_tokens: int
    transport_kind: TransportKind
    observed_at_ms: int


def _decode_tool_call(value: object, *, field: str) -> ToolCall:
    mapping = closed_mapping(
        value,
        fields=("call_id", "name", "canonical_arguments_json"),
        field=field,
    )
    try:
        return ToolCall(
            call_id=cast(str, mapping["call_id"]),
            name=cast(str, mapping["name"]),
            canonical_arguments_json=cast(
                str,
                mapping["canonical_arguments_json"],
            ),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is invalid") from exc


def _parse_response(payload: bytes) -> tuple[ParserKind, SubjectTurn | None]:
    try:
        value = load_json_bytes(payload, source=Path("<synthetic-response>"))
        mapping = closed_mapping(
            value,
            fields=("finish_reason", "generated_tokens", "text", "tool_calls"),
            field="synthetic response",
        )
        calls_value = mapping["tool_calls"]
        if type(calls_value) is not list:
            raise ValueError("synthetic response tool_calls must be an array")
        turn = SubjectTurn(
            text=cast(str, mapping["text"]),
            tool_calls=tuple(
                _decode_tool_call(item, field=f"tool_calls[{index}]")
                for index, item in enumerate(calls_value)
            ),
            generated_tokens=cast(int, mapping["generated_tokens"]),
            finish_reason=cast(str | None, mapping["finish_reason"]),
        )
        if canonical_json_bytes(value, indent=None) != payload:
            raise ValueError("synthetic response must be compact canonical JSON")
    except (TypeError, ValueError):
        return "malformed", None
    return ("refusal", turn) if turn.finish_reason == "refusal" else ("turn", turn)


def _decode_raw_event(payload: bytes) -> tuple[TransportKind, int]:
    value = load_json_bytes(payload, source=Path("<synthetic-provider-event>"))
    mapping = closed_mapping(
        value,
        fields=(
            "record_kind",
            "schema_version",
            "transport_kind",
            "observed_at_ms",
        ),
        field="synthetic provider event",
    )
    if (
        mapping["record_kind"] != "synthetic_raw_provider_event_v1"
        or mapping["schema_version"] != "1"
        or canonical_json_bytes(value, indent=None) != payload
    ):
        raise ValueError("synthetic provider event identity is invalid")
    transport = mapping["transport_kind"]
    observed = mapping["observed_at_ms"]
    if transport not in (
        "response",
        "provider_error",
        "infrastructure_error",
        "timeout_no_response",
    ):
        raise ValueError("synthetic provider event transport is invalid")
    if type(observed) is not int or not 0 <= observed < 2**64:
        raise ValueError("synthetic provider event time is invalid")
    return cast(TransportKind, transport), observed


def _validate_provider_observation(
    *,
    observation: RawProviderObservation,
    expected_role: Literal["primary_subject", "user_simulator"],
    expected_call_index: int,
    expected_seed: int,
    expected_model_sha256: str,
    deadline_ms: int,
    completion_ms: int,
    parser: SyntheticResponseParser | None = None,
    event_codec: SyntheticProviderEventCodec | None = None,
) -> _ValidatedProviderObservation:
    """Reconstruct all provider truth before any environment mutation."""

    if type(observation) is not RawProviderObservation:
        raise TypeError("observation must be exact RawProviderObservation")
    if (
        observation.subject_role,
        observation.call_index,
        observation.seed,
        observation.model_contract_sha256,
    ) != (
        expected_role,
        expected_call_index,
        expected_seed,
        expected_model_sha256,
    ):
        raise ValueError("provider observation differs from dispatch identity")
    exact_parser = SyntheticResponseParser() if parser is None else parser
    exact_event_codec = (
        SyntheticProviderEventCodec() if event_codec is None else event_codec
    )
    if (
        type(exact_parser) is not SyntheticResponseParser
        or type(exact_event_codec) is not SyntheticProviderEventCodec
    ):
        raise TypeError("provider validation codecs must be exact registered types")
    transport, event_ms = exact_event_codec.decode_raw(observation.provider_event_bytes)
    if event_ms != completion_ms:
        raise ValueError("provider event time differs from controller meter")
    response = observation.response_bytes
    if response is None:
        parser_kind: ParserKind = "not_applicable"
        typed_turn = None
        output_ids = None
        generated_tokens = 0
    else:
        output_ids = tuple(response)
        generated_tokens = len(output_ids)
        parser_kind, typed_turn = exact_parser.parse(response)
    if observation.reported_output_token_ids != output_ids:
        raise ValueError("reported output token IDs differ from controller tokens")
    if observation.reported_generated_tokens != generated_tokens:
        raise ValueError("reported generated tokens differ from controller tokens")
    if observation.typed_turn != typed_turn:
        raise ValueError("typed turn differs from controller parser")
    if typed_turn is not None and typed_turn.generated_tokens != generated_tokens:
        raise ValueError("typed turn generated count differs from controller tokens")
    if expected_role == "user_simulator" and typed_turn is not None:
        if typed_turn.tool_calls:
            raise ValueError("simulator turns cannot issue tools")
    status = _derive_provider_status(
        observed_ms=completion_ms,
        deadline_ms=deadline_ms,
        response_present=response is not None,
        transport=transport,
        parser=parser_kind,
    )
    if observation.completion_kind.value != status.value:
        raise ValueError("provider completion claim differs from derived status")
    return _ValidatedProviderObservation(
        status=status,
        parser_kind=parser_kind,
        typed_turn=typed_turn,
        output_token_ids=output_ids,
        generated_tokens=generated_tokens,
        transport_kind=transport,
        observed_at_ms=completion_ms,
    )


def _pre_dispatch_failure(
    *,
    counters: ResourceCounters,
    parsed_turns: int,
    prefix_caps: PrefixCaps,
    contract_caps: CallContractCaps,
) -> FailureKind:
    """Apply inclusive same-role pre-dispatch maxima."""

    if (
        type(counters) is not ResourceCounters
        or type(prefix_caps) is not PrefixCaps
        or type(contract_caps) is not CallContractCaps
        or type(parsed_turns) is not int
        or parsed_turns < 0
    ):
        raise TypeError("pre-dispatch authority values have wrong exact types")
    if counters.generated_tokens >= min(
        prefix_caps.generated_tokens,
        contract_caps.aggregate_generated_tokens,
    ):
        return FailureKind.TOKEN_CAP
    if counters.model_calls >= min(
        prefix_caps.model_calls,
        contract_caps.aggregate_model_calls,
    ):
        return FailureKind.MODEL_CALL_CAP
    if parsed_turns >= contract_caps.aggregate_turns:
        return FailureKind.TURN_CAP
    return FailureKind.NONE


def _render_request(
    *,
    subject_role: Literal["primary_subject", "user_simulator"],
    context_bytes: bytes,
) -> bytes:
    if subject_role not in ("primary_subject", "user_simulator"):
        raise ValueError("request role is not registered")
    if type(context_bytes) is not bytes:
        raise TypeError("request context must be exact bytes")
    import base64

    return canonical_json_bytes(
        {
            "context_base64": base64.b64encode(context_bytes).decode("ascii"),
            "subject_role": subject_role,
        },
        indent=None,
    )


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    if type(ref) is not ArtifactRef:
        raise TypeError("ref must be exact ArtifactRef")
    return asdict(ref)


def _call_mapping(call: ToolCall) -> dict[str, object]:
    return {
        "call_id": call.call_id,
        "canonical_arguments_json": call.canonical_arguments_json,
        "name": call.name,
    }


def _intent_bytes(intent: ProviderDispatchIntent) -> bytes:
    return canonical_json_bytes(
        {
            "absolute_deadline_ms": intent.absolute_deadline_ms,
            "call_index": intent.call_index,
            "input_token_ids_ref": _ref_mapping(intent.input_token_ids_ref),
            "model_contract_ref": _ref_mapping(intent.model_contract_ref),
            "request_ref": _ref_mapping(intent.request_ref),
            "seed": intent.seed,
            "subject_role": intent.subject_role,
        },
        indent=None,
    )


def _attempt_bytes(attempt: ProviderCallAttemptReceipt) -> bytes:
    return canonical_json_bytes(
        {
            "call_index": attempt.call_index,
            "dispatch_intent_ref": _ref_mapping(attempt.dispatch_intent_ref),
            "elapsed_ms": attempt.elapsed_ms,
            "generated_tokens": attempt.generated_tokens,
            "input_token_ids_ref": _ref_mapping(attempt.input_token_ids_ref),
            "model_contract_ref": _ref_mapping(attempt.model_contract_ref),
            "output_token_ids_ref": (
                None
                if attempt.output_token_ids_ref is None
                else _ref_mapping(attempt.output_token_ids_ref)
            ),
            "provider_event_ref": _ref_mapping(attempt.provider_event_ref),
            "request_ref": _ref_mapping(attempt.request_ref),
            "response_ref": (
                None
                if attempt.response_ref is None
                else _ref_mapping(attempt.response_ref)
            ),
            "seed": attempt.seed,
            "status": attempt.status.value,
            "subject_role": attempt.subject_role,
        },
        indent=None,
    )


def _controller_event_bytes(
    *,
    row: SyntheticProviderTranscriptRow,
    intent_sha256: str,
    status: ProviderAttemptStatus,
    response_bytes: bytes | None,
    observed_at_ms: int,
) -> bytes:
    return canonical_json_bytes(
        {
            "call_index": row.call_index,
            "completion_kind": status.value,
            "cost_microunits": 0,
            "dispatch_intent_sha256": intent_sha256,
            "model_contract_sha256": row.model_contract_sha256,
            "observed_at_ms": observed_at_ms,
            "response_sha256": (
                None
                if response_bytes is None
                else hashlib.sha256(response_bytes).hexdigest()
            ),
            "schema_version": "1",
            "seed": row.seed,
            "subject_role": row.subject_role,
        },
        indent=None,
    )


def _settlement_bytes(
    *,
    row: SyntheticProviderTranscriptRow,
    intent_sha256: str,
    attempt_sha256: str,
    provider_event_sha256: str,
) -> bytes:
    return canonical_json_bytes(
        {
            "attempt_sha256": attempt_sha256,
            "call_index": row.call_index,
            "cost_microunits": 0,
            "currency": "synthetic_microunit",
            "dispatch_intent_sha256": intent_sha256,
            "final": True,
            "provider_event_sha256": provider_event_sha256,
            "schema_version": "1",
            "seed": row.seed,
            "subject_role": row.subject_role,
        },
        indent=None,
    )


def _remaining_contract(
    caps: CallContractCaps,
    *,
    generated_tokens: int,
    model_calls: int,
    turns: int,
) -> CallContractCaps:
    return CallContractCaps(
        max(0, caps.aggregate_generated_tokens - generated_tokens),
        max(0, caps.aggregate_model_calls - model_calls),
        max(0, caps.aggregate_turns - turns),
        caps.per_call_generated_tokens,
        caps.per_call_turns,
    )


def _selected_task_bytes(authority: PrefixExecutionAuthority) -> bytes:
    schedule = authority.task_schedule
    return canonical_json_bytes(
        {
            "prefix_seed": schedule.prefix_seed,
            "provider_lane": schedule.provider_lane,
            "slots": [
                {
                    "execution_order": slot.execution_order,
                    "hardware_lane": slot.hardware_lane,
                    "seed": slot.seed,
                    "slot_id": slot.slot_id,
                }
                for slot in schedule.slots.slots
            ],
            "task": {
                "benchmark": schedule.task.benchmark,
                "lineage": schedule.task.lineage,
                "sensitivity_groups": [
                    {"kind": group.kind.value, "value": group.value}
                    for group in schedule.task.sensitivity_groups
                ],
                "stratum": schedule.task.stratum,
                "task_id": schedule.task.task_id,
            },
        },
        indent=None,
    )


@final
class SyntheticProviderActor:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticProviderActor is final")

    def __init__(
        self,
        *,
        subject_role: Literal["primary_subject", "user_simulator"],
        program: SyntheticPrefixProgram,
        payloads: Mapping[ArtifactRef, bytes],
    ) -> None:
        self._subject_role = subject_role
        self._program = program
        self._payloads = payloads

    def invoke(
        self,
        *,
        request_bytes: bytes,
        dispatch_intent_sha256: str,
        subject_role: Literal["primary_subject", "user_simulator"],
        call_index: int,
        seed: int,
        model_contract_sha256: str,
        remaining_caps: CallContractCaps,
        absolute_deadline_ms: int,
        transcript_position: int,
    ) -> RawProviderObservation:
        if (
            subject_role != self._subject_role
            or type(remaining_caps) is not CallContractCaps
            or type(absolute_deadline_ms) is not int
            or len(dispatch_intent_sha256) != 64
        ):
            raise ValueError("provider invocation differs from registered actor")
        try:
            row = self._program.provider_transcript[transcript_position]
        except IndexError as exc:
            raise ValueError("provider transcript is exhausted") from exc
        if (
            row.subject_role,
            row.call_index,
            row.seed,
            row.model_contract_sha256,
        ) != (subject_role, call_index, seed, model_contract_sha256):
            raise ValueError("provider transcript differs from dispatch identity")
        expected_request = self._payloads[row.expected_request_ref]
        if request_bytes != expected_request:
            raise ValueError("provider request differs from sealed transcript")
        response = (
            None if row.response_ref is None else self._payloads[row.response_ref]
        )
        return RawProviderObservation(
            subject_role=subject_role,
            call_index=call_index,
            seed=seed,
            model_contract_sha256=model_contract_sha256,
            response_bytes=response,
            typed_turn=row.typed_turn,
            reported_output_token_ids=row.reported_output_token_ids,
            reported_generated_tokens=row.reported_generated_tokens,
            provider_event_bytes=self._payloads[row.provider_event_ref],
            completion_kind=row.completion_kind,
        )


@dataclass(frozen=True, slots=True)
class _LoopComponents:
    subject: SyntheticProviderActor
    simulator: SyntheticProviderActor | None
    meter: SyntheticTraceMeter
    tokenizer: SyntheticByteTokenizer
    renderer: SyntheticRequestRenderer
    parser: SyntheticResponseParser
    event_codec: SyntheticProviderEventCodec
    settlement_codec: SyntheticSettlementCodec
    grade_codec: SyntheticGradeCodec
    verifier_codec: SyntheticVerifierCodec


def _construct_components(
    *,
    authority: PrefixExecutionAuthority,
    program: SyntheticPrefixProgram,
    program_bytes: bytes,
    payloads: Mapping[ArtifactRef, bytes],
) -> _LoopComponents:
    _validate_descriptor_registry(authority)
    return _LoopComponents(
        subject=SyntheticProviderActor(
            subject_role="primary_subject",
            program=program,
            payloads=payloads,
        ),
        simulator=(
            None
            if authority.simulator_contract_ref is None
            else SyntheticProviderActor(
                subject_role="user_simulator",
                program=program,
                payloads=payloads,
            )
        ),
        meter=SyntheticTraceMeter(
            program_bytes=program_bytes,
            clock_trace=program.clock_trace,
        ),
        tokenizer=SyntheticByteTokenizer(),
        renderer=SyntheticRequestRenderer(),
        parser=SyntheticResponseParser(),
        event_codec=SyntheticProviderEventCodec(),
        settlement_codec=SyntheticSettlementCodec(),
        grade_codec=SyntheticGradeCodec(),
        verifier_codec=SyntheticVerifierCodec(),
    )


@dataclass(slots=True)
class _PrefixLoopResult:
    qualification: _InitialQualificationResult
    primary_counters: ResourceCounters
    simulator_counters: ResourceCounters
    primary_parsed_turns: int
    simulator_parsed_turns: int
    intents: tuple[ProviderDispatchIntent, ...]
    intent_refs: tuple[ArtifactRef, ...]
    attempts: tuple[ProviderCallAttemptReceipt, ...]
    attempt_refs: tuple[ArtifactRef, ...]
    settlements: tuple[ProviderSettlement, ...]
    boundaries: tuple[CompletedToolBoundaryReceipt, ...]
    provider_attempts_ref: ArtifactRef
    boundary_ledger_ref: ArtifactRef
    provider_cost_ref: ArtifactRef
    cost_closure: AttemptBoundZeroCostClosure | SyntheticZeroAttemptCostClosure
    trigger_reason: TriggerReason
    failure_kind: FailureKind
    branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    final_observation: _SnapshotState
    _provenances: tuple[StableSourceProvenance, ...]

    def close(self) -> None:
        errors: list[BaseException] = []
        try:
            self.qualification.close()
        except BaseException as exc:
            errors.append(exc)
        provenances = self._provenances
        self._provenances = ()
        for provenance in provenances:
            try:
                provenance.verify_again()
            except BaseException as exc:
                errors.append(exc)
        for provenance in provenances:
            try:
                provenance.close()
            except BaseException as exc:
                errors.append(exc)
        if errors:
            raise BaseExceptionGroup("prefix loop cleanup failed", errors)


def _validate_descriptor_registry(
    authority: PrefixExecutionAuthority,
) -> dict[str, ImplementationDescriptor]:
    if type(authority) is not PrefixExecutionAuthority:
        raise TypeError("authority must be exact PrefixExecutionAuthority")
    by_purpose: dict[str, ImplementationDescriptor] = {
        descriptor.purpose: descriptor
        for descriptor in authority.implementation_descriptors
    }
    expected = set(REGISTERED_LOOP_DESCRIPTOR_FIELDS)
    if authority.simulator_contract_ref is None:
        expected.remove("simulator")
    if set(by_purpose) != expected:
        raise ValueError("authority descriptor purposes differ from registry")
    for purpose, descriptor in by_purpose.items():
        fields = REGISTERED_LOOP_DESCRIPTOR_FIELDS[purpose]
        if any(getattr(descriptor, name) != value for name, value in fields.items()):
            raise ValueError(f"{purpose} descriptor differs from registry")
        if descriptor.implementation_source_ref not in authority.source_revision_refs:
            raise ValueError(f"{purpose} source is not manifest-authorized")
    return by_purpose


def _failure_for_status(status: ProviderAttemptStatus) -> FailureKind:
    return {
        ProviderAttemptStatus.COMPLETED: FailureKind.NONE,
        ProviderAttemptStatus.TIMEOUT_NO_RESPONSE: FailureKind.TIMEOUT,
        ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE: FailureKind.TIMEOUT,
        ProviderAttemptStatus.REFUSAL: FailureKind.REFUSAL,
        ProviderAttemptStatus.MALFORMED_RESPONSE: FailureKind.MALFORMED_ACTION,
        ProviderAttemptStatus.PROVIDER_ERROR: FailureKind.MODEL,
        ProviderAttemptStatus.INFRASTRUCTURE_ERROR: FailureKind.INFRASTRUCTURE,
    }[status]


def _open_prefix_loop(
    *,
    run_root: Path,
    authority: PrefixExecutionAuthority,
) -> _PrefixLoopResult:
    """Execute S02C-c while retaining the qualified environments for S02C-d."""

    descriptors = _validate_descriptor_registry(authority)
    if authority.schedule_authority != "synthetic_validation":
        raise ValueError("prefix loop requires synthetic_validation authority")
    root = Path(run_root)
    task_bytes: bytes
    program_bytes: bytes
    payloads: dict[ArtifactRef, bytes] = {}
    with AuthorityRefReader(root) as reader:
        task_bytes = reader.read_bytes(authority.task_input_ref)
        program_bytes = reader.read_bytes(authority.program_ref)
        program = load_synthetic_prefix_program(program_bytes)
        if program.task_id != authority.task_schedule.task.task_id:
            raise ValueError("program task differs from selected schedule task")
        nested_refs = [
            program.tool_schema_ref,
            program.grade_result.evidence_ref,
            program.verifier_result.evidence_ref,
            *(
                ref
                for row in program.provider_transcript
                for ref in (
                    row.expected_request_ref,
                    row.provider_event_ref,
                    *(() if row.response_ref is None else (row.response_ref,)),
                )
            ),
            *(item.result_ref for item in program.tool_observations),
        ]
        for ref in nested_refs:
            expected_media = AUTHORITY_ASSET_ROLE_MEDIA.get(ref.role)
            if expected_media is None or ref.media_type != expected_media:
                raise ValueError("program nested ref has noncanonical role/media")
            payloads[ref] = reader.read_bytes(ref)

    loop_provenances: list[StableSourceProvenance] = []
    qualification: _InitialQualificationResult | None = None
    try:
        for purpose, descriptor in descriptors.items():
            if purpose not in ("environment", "tokenizer"):
                loop_provenances.append(
                    StableSourceProvenance(
                        _SOURCE_ROOT,
                        _SOURCE_PATH_BY_PURPOSE[purpose],
                        descriptor.implementation_source_ref,
                    )
                )
        with ControllerArtifactStore(root) as task_store:
            task_ref = task_store.write(
                role="selected_task",
                payload=_selected_task_bytes(authority),
                media_type="application/json",
            )
        qualification = _open_qualified_initial_restore(
            run_root=root,
            authority=InitialQualificationAuthority(
                schedule_ref=authority.schedule_ref,
                task_ref=task_ref,
                task_input_ref=authority.task_input_ref,
                environment_contract_ref=authority.environment_contract_ref,
                isolation_contract_ref=authority.isolation_contract_ref,
                program_ref=authority.program_ref,
                environment_descriptor=descriptors["environment"],
                tokenizer_descriptor=descriptors["tokenizer"],
                task_input_bytes=task_bytes,
                program_bytes=program_bytes,
            ),
        )
        return _execute_open_loop(
            run_root=root,
            authority=authority,
            program=program,
            program_bytes=program_bytes,
            payloads=payloads,
            qualification=qualification,
            loop_provenances=tuple(loop_provenances),
        )
    except BaseException as primary:
        errors: list[BaseException] = [primary]
        if qualification is not None:
            try:
                qualification.close()
            except BaseException as exc:
                errors.append(exc)
        for provenance in loop_provenances:
            try:
                provenance.verify_again()
            except BaseException as exc:
                errors.append(exc)
        for provenance in loop_provenances:
            try:
                provenance.close()
            except BaseException as exc:
                errors.append(exc)
        raise BaseExceptionGroup("prefix loop failed", errors) from None


def _execute_open_loop(
    *,
    run_root: Path,
    authority: PrefixExecutionAuthority,
    program: SyntheticPrefixProgram,
    program_bytes: bytes,
    payloads: Mapping[ArtifactRef, bytes],
    qualification: _InitialQualificationResult,
    loop_provenances: tuple[StableSourceProvenance, ...],
) -> _PrefixLoopResult:
    authority_seal = repr(authority)
    live = qualification._resources[0]
    handle: SyntheticEnvironmentHandle = live.handle
    components = _construct_components(
        authority=authority,
        program=program,
        program_bytes=program_bytes,
        payloads=payloads,
    )
    meter = components.meter
    program_sha256 = hashlib.sha256(program_bytes).hexdigest()
    epoch = meter.read(label="prefix_epoch", program_sha256=program_sha256)
    if epoch + authority.prefix_caps.wall_clock_ms >= 2**64:
        raise ValueError("prefix deadline overflows uint64")
    deadline = epoch + authority.prefix_caps.wall_clock_ms
    actors = {"primary_subject": components.subject}
    if components.simulator is not None:
        actors["user_simulator"] = components.simulator
    counters = {
        "primary_subject": ResourceCounters(0, 0, 0, 0),
        "user_simulator": ResourceCounters(0, 0, 0, 0),
    }
    parsed_turns = {"primary_subject": 0, "user_simulator": 0}
    call_indexes = {"primary_subject": 0, "user_simulator": 0}
    intents: list[ProviderDispatchIntent] = []
    intent_refs: list[ArtifactRef] = []
    attempts: list[ProviderCallAttemptReceipt] = []
    attempt_refs: list[ArtifactRef] = []
    settlements: list[ProviderSettlement] = []
    boundaries: list[CompletedToolBoundaryReceipt] = []
    transcript_position = 0
    trigger = TriggerReason.NO_INTERVENTION_OPPORTUNITY
    terminal_failure = FailureKind.NONE
    branch_pending: tuple[ToolCall, ...] = ()
    terminal_remainder: tuple[ToolCall, ...] = ()
    elapsed = 0
    mutation_has_returned = False

    def role_caps(
        role: Literal["primary_subject", "user_simulator"],
    ) -> tuple[PrefixCaps, CallContractCaps, ArtifactRef]:
        if role == "primary_subject":
            return (
                authority.prefix_caps,
                authority.subject_contract_caps,
                authority.subject_contract_ref,
            )
        contract = authority.simulator_contract_caps
        model_ref = authority.simulator_contract_ref
        if contract is None or model_ref is None:
            raise ValueError("environment requested an unauthorized simulator")
        simulator = authority.simulator_caps
        return (
            PrefixCaps(
                simulator.aggregate_generated_tokens,
                simulator.aggregate_model_calls,
                0,
                authority.prefix_caps.wall_clock_ms,
            ),
            contract,
            model_ref,
        )

    def terminate(
        failure: FailureKind,
        pending: tuple[ToolCall, ...],
    ) -> None:
        nonlocal terminal_failure, terminal_remainder
        handle.terminate(failure, pending)
        terminal_failure = failure
        terminal_remainder = pending

    with ControllerArtifactStore(run_root) as store:
        while True:
            observed_failure = handle.failure_kind()
            observed_terminal = handle.episode_terminal()
            if observed_failure is not FailureKind.NONE:
                terminal_failure = observed_failure
                break
            if observed_terminal:
                break
            if transcript_position >= len(program.provider_transcript):
                raise ValueError("nonterminal environment outlived provider transcript")

            simulator_context = handle.simulator_context()
            role: Literal["primary_subject", "user_simulator"] = (
                "user_simulator" if simulator_context is not None else "primary_subject"
            )
            if role not in actors:
                raise ValueError("derived simulator actor is not sealed")
            row = program.provider_transcript[transcript_position]
            if row.subject_role != role:
                raise ValueError("transcript role differs from environment actor")
            role_prefix_caps, contract_caps, model_ref = role_caps(role)
            role_counter = counters[role]
            cap_failure = _pre_dispatch_failure(
                counters=role_counter,
                parsed_turns=parsed_turns[role],
                prefix_caps=role_prefix_caps,
                contract_caps=contract_caps,
            )
            if contract_caps.per_call_turns == 0:
                cap_failure = FailureKind.TURN_CAP
            if cap_failure is not FailureKind.NONE:
                terminate(cap_failure, ())
                break

            before_label = f"before_{role}_{call_indexes[role]}"
            before = meter.read(
                label=before_label,
                program_sha256=program_sha256,
            )
            elapsed = max(0, before - epoch)
            if before >= deadline:
                terminate(FailureKind.TIMEOUT, ())
                break
            context = (
                handle.visible_context()
                if role == "primary_subject"
                else cast(bytes, simulator_context)
            )
            request_bytes = components.renderer.render(
                subject_role=role,
                context_bytes=context,
            )
            expected_request = payloads[row.expected_request_ref]
            if (
                request_bytes != expected_request
                or hashlib.sha256(request_bytes).hexdigest()
                != row.expected_request_sha256
            ):
                raise ValueError("rendered request differs from sealed program")
            input_ids = components.tokenizer.encode(request_bytes)
            if input_ids != row.expected_input_token_ids:
                raise ValueError("input token IDs differ from sealed program")
            expected_seed = derive_call_seed(
                authority.task_schedule.prefix_seed,
                role,
                call_indexes[role],
            )
            if row.seed != expected_seed or row.call_index != call_indexes[role]:
                raise ValueError("program call seed/index differs from controller")
            if row.model_contract_sha256 != model_ref.sha256:
                raise ValueError("program model digest differs from sealed contract")
            request_ref = store.write(
                role="provider_request",
                payload=request_bytes,
                media_type="application/json",
            )
            input_token_bytes = canonical_json_bytes(
                {"token_ids": list(input_ids)},
                indent=None,
            )
            input_ref = store.write(
                role="input_token_ids",
                payload=input_token_bytes,
                media_type="application/json",
            )
            intent = ProviderDispatchIntent(
                subject_role=role,
                call_index=call_indexes[role],
                seed=expected_seed,
                request_ref=request_ref,
                input_token_ids_ref=input_ref,
                model_contract_ref=model_ref,
                absolute_deadline_ms=deadline,
            )
            intent_payload = _intent_bytes(intent)
            intent_ref = store.write(
                role="provider_dispatch_intent",
                payload=intent_payload,
                media_type="application/json",
            )
            intent_sha256 = hashlib.sha256(intent_payload).hexdigest()
            role_counter = ResourceCounters(
                role_counter.generated_tokens,
                role_counter.model_calls + 1,
                role_counter.tool_calls,
                elapsed,
            )
            counters[role] = role_counter
            observation = actors[role].invoke(
                request_bytes=request_bytes,
                dispatch_intent_sha256=intent_sha256,
                subject_role=role,
                call_index=call_indexes[role],
                seed=expected_seed,
                model_contract_sha256=model_ref.sha256,
                remaining_caps=_remaining_contract(
                    contract_caps,
                    generated_tokens=role_counter.generated_tokens,
                    model_calls=role_counter.model_calls,
                    turns=parsed_turns[role],
                ),
                absolute_deadline_ms=deadline,
                transcript_position=transcript_position,
            )
            completion = meter.read(
                label=f"after_{role}_{call_indexes[role]}",
                program_sha256=program_sha256,
            )
            elapsed = max(0, completion - epoch)
            validated = _validate_provider_observation(
                observation=observation,
                expected_role=role,
                expected_call_index=call_indexes[role],
                expected_seed=expected_seed,
                expected_model_sha256=model_ref.sha256,
                deadline_ms=deadline,
                completion_ms=completion,
                parser=components.parser,
                event_codec=components.event_codec,
            )
            response_ref = (
                None
                if observation.response_bytes is None
                else store.write(
                    role="provider_response",
                    payload=observation.response_bytes,
                    media_type="application/octet-stream",
                )
            )
            output_ref = (
                None
                if validated.output_token_ids is None
                else store.write(
                    role="output_token_ids",
                    payload=canonical_json_bytes(
                        {"token_ids": list(validated.output_token_ids)},
                        indent=None,
                    ),
                    media_type="application/json",
                )
            )
            event_payload = components.event_codec.encode_controller(
                row=row,
                intent_sha256=intent_sha256,
                status=validated.status,
                response_bytes=observation.response_bytes,
                observed_at_ms=completion,
            )
            event_ref = store.write(
                role="provider_event",
                payload=event_payload,
                media_type="application/json",
            )
            attempt = ProviderCallAttemptReceipt(
                dispatch_intent_ref=intent_ref,
                subject_role=role,
                call_index=call_indexes[role],
                seed=expected_seed,
                status=validated.status,
                request_ref=request_ref,
                input_token_ids_ref=input_ref,
                response_ref=response_ref,
                output_token_ids_ref=output_ref,
                model_contract_ref=model_ref,
                generated_tokens=validated.generated_tokens,
                elapsed_ms=elapsed,
                provider_event_ref=event_ref,
            )
            attempt_payload = _attempt_bytes(attempt)
            attempt_ref = store.write(
                role="provider_attempt",
                payload=attempt_payload,
                media_type="application/json",
            )
            settlement_payload = components.settlement_codec.encode(
                row=row,
                intent_sha256=intent_sha256,
                attempt_sha256=attempt_ref.sha256,
                provider_event_sha256=event_ref.sha256,
            )
            settlement_ref = store.write(
                role="provider_settlement",
                payload=settlement_payload,
                media_type="application/json",
            )
            settlement = ProviderSettlement(
                dispatch_intent_ref=intent_ref,
                attempt_receipt_ref=attempt_ref,
                provider_event_ref=event_ref,
                settlement_ref=settlement_ref,
                cost_microunits=0,
            )
            intents.append(intent)
            intent_refs.append(intent_ref)
            attempts.append(attempt)
            attempt_refs.append(attempt_ref)
            settlements.append(settlement)
            generated = role_counter.generated_tokens + validated.generated_tokens
            if validated.typed_turn is not None:
                parsed_turns[role] += 1
            counters[role] = ResourceCounters(
                generated,
                role_counter.model_calls,
                role_counter.tool_calls,
                elapsed,
            )
            call_indexes[role] += 1
            transcript_position += 1

            status_failure = _failure_for_status(validated.status)
            pending = (
                () if validated.typed_turn is None else validated.typed_turn.tool_calls
            )
            if status_failure is not FailureKind.NONE:
                terminate(status_failure, pending)
                break
            if handle.episode_terminal():
                if pending:
                    raise ValueError("terminal provider state has pending tools")
                break
            effective_token_cap = min(
                role_prefix_caps.generated_tokens,
                contract_caps.aggregate_generated_tokens,
            )
            if completion > deadline:
                terminate(FailureKind.TIMEOUT, pending)
                break
            if (
                generated > effective_token_cap
                or validated.generated_tokens > contract_caps.per_call_generated_tokens
            ):
                terminate(FailureKind.TOKEN_CAP, pending)
                break
            turn = validated.typed_turn
            if turn is None:
                raise ValueError("completed provider status lacks a typed turn")
            if role == "user_simulator":
                handle.append_simulator_turn(turn)
                continue
            handle.append_assistant_turn(turn)

            queue = turn.tool_calls
            for tool_index, call in enumerate(queue):
                pending = queue[tool_index:]
                before_tool = meter.read(
                    label=f"before_tool_{call.call_id}",
                    program_sha256=program_sha256,
                )
                elapsed = max(0, before_tool - epoch)
                if before_tool >= deadline:
                    terminate(FailureKind.TIMEOUT, pending)
                    break
                primary = counters["primary_subject"]
                if primary.tool_calls >= authority.prefix_caps.tool_calls:
                    terminate(FailureKind.TOOL_CAP, pending)
                    break
                executed_id, result_bytes = handle.execute_tool(call)
                matches = [
                    item
                    for item in program.tool_observations
                    if item.call_id == call.call_id
                ]
                if (
                    len(matches) != 1
                    or executed_id != call.call_id
                    or result_bytes != payloads[matches[0].result_ref]
                ):
                    raise ValueError("tool result differs from sealed observation")
                call_ref = store.write(
                    role="tool_call",
                    payload=canonical_json_bytes(_call_mapping(call), indent=None),
                    media_type="application/json",
                )
                result_ref = store.write(
                    role="tool_result",
                    payload=result_bytes,
                    media_type="application/octet-stream",
                )
                mutation = handle.mutation_committed()
                mutation_has_returned = mutation_has_returned or mutation
                eligible = handle.verifier_eligible()
                terminal = handle.episode_terminal()
                failure = handle.failure_kind()
                completion_tool = meter.read(
                    label=f"after_tool_{call.call_id}",
                    program_sha256=program_sha256,
                )
                elapsed = max(0, completion_tool - epoch)
                primary = ResourceCounters(
                    primary.generated_tokens,
                    primary.model_calls,
                    primary.tool_calls + 1,
                    elapsed,
                )
                counters["primary_subject"] = primary
                boundary = CompletedToolBoundaryReceipt(
                    call_id=call.call_id,
                    tool_call_ref=call_ref,
                    tool_result_ref=result_ref,
                    mutation_committed=mutation,
                    verifier_eligible_after=eligible,
                    episode_terminal=terminal,
                    failure_kind=failure,
                    elapsed_ms=elapsed,
                )
                boundaries.append(boundary)
                remainder = queue[tool_index + 1 :]
                if failure is not FailureKind.NONE:
                    handle.terminate(failure, remainder)
                    terminal_failure = failure
                    terminal_remainder = remainder
                    break
                if terminal:
                    if remainder:
                        raise ValueError("clean terminal tool state has a remainder")
                    break
                if completion_tool > deadline:
                    terminate(FailureKind.TIMEOUT, remainder)
                    break
                if primary.generated_tokens > authority.prefix_caps.generated_tokens:
                    terminate(FailureKind.TOKEN_CAP, remainder)
                    break
                if mutation_has_returned and eligible:
                    trigger = TriggerReason.FIRST_ELIGIBLE_MUTATION
                    branch_pending = remainder
                    break
                if primary.tool_calls == 4:
                    trigger = TriggerReason.FOURTH_TOOL_CALL
                    branch_pending = remainder
                    break
            if (
                trigger is not TriggerReason.NO_INTERVENTION_OPPORTUNITY
                or handle.episode_terminal()
            ):
                break

        if program.expected_trigger_reason is not trigger:
            raise ValueError("derived trigger differs from sealed post-hoc expectation")
        meter.assert_exhausted()
        final_observation = _decode_snapshot_state(handle.snapshot())
        if trigger is TriggerReason.NO_INTERVENTION_OPPORTUNITY:
            if not final_observation.episode_terminal:
                raise ValueError("no-trigger prefix must be terminal")
        elif final_observation.episode_terminal:
            raise ValueError("branch trigger must remain nonterminal")
        if final_observation.failure_kind is not terminal_failure:
            raise ValueError("final environment failure differs from controller")
        if final_observation.terminal_unexecuted_remainder != terminal_remainder:
            raise ValueError("final terminal remainder differs from controller")
        if final_observation.branch_pending_calls != branch_pending:
            raise ValueError("final branch queue differs from controller")

        common_wall = elapsed
        primary = counters["primary_subject"]
        simulator = counters["user_simulator"]
        primary = ResourceCounters(
            primary.generated_tokens,
            primary.model_calls,
            primary.tool_calls,
            common_wall,
        )
        simulator = ResourceCounters(
            simulator.generated_tokens,
            simulator.model_calls,
            0,
            common_wall,
        )
        attempt_ledger_payload = canonical_json_bytes(
            {
                "attempt_refs": [_ref_mapping(ref) for ref in attempt_refs],
                "attempts": [
                    load_json_bytes(
                        _attempt_bytes(attempt),
                        source=Path("<attempt>"),
                    )
                    for attempt in attempts
                ],
                "intent_refs": [_ref_mapping(ref) for ref in intent_refs],
                "intents": [
                    load_json_bytes(_intent_bytes(intent), source=Path("<intent>"))
                    for intent in intents
                ],
            },
            indent=None,
        )
        provider_attempts_ref = store.write(
            role="provider_attempt_ledger",
            payload=attempt_ledger_payload,
            media_type="application/json",
        )
        boundary_payload = canonical_json_bytes(
            {
                "boundaries": [
                    {
                        "call_id": boundary.call_id,
                        "elapsed_ms": boundary.elapsed_ms,
                        "episode_terminal": boundary.episode_terminal,
                        "failure_kind": boundary.failure_kind.value,
                        "mutation_committed": boundary.mutation_committed,
                        "tool_call_ref": _ref_mapping(boundary.tool_call_ref),
                        "tool_result_ref": _ref_mapping(boundary.tool_result_ref),
                        "verifier_eligible_after": (boundary.verifier_eligible_after),
                    }
                    for boundary in boundaries
                ]
            },
            indent=None,
        )
        boundary_ledger_ref = store.write(
            role="tool_boundary_ledger",
            payload=boundary_payload,
            media_type="application/json",
        )
        if attempts:
            cost_closure: (
                AttemptBoundZeroCostClosure | SyntheticZeroAttemptCostClosure
            ) = AttemptBoundZeroCostClosure(
                tuple(intents),
                tuple(intent_refs),
                tuple(attempts),
                tuple(attempt_refs),
                tuple(settlements),
                0,
            )
        else:
            cost_closure = SyntheticZeroAttemptCostClosure()
        cost_payload = canonical_json_bytes(
            {
                "attempt_refs": [_ref_mapping(ref) for ref in attempt_refs],
                "settlement_refs": [
                    _ref_mapping(settlement.settlement_ref)
                    for settlement in settlements
                ],
                "total_cost_microunits": 0,
            },
            indent=None,
        )
        provider_cost_ref = store.write(
            role="provider_cost_closure",
            payload=cost_payload,
            media_type="application/json",
        )
        ToolBoundaryLedger(tuple(boundaries))
        if repr(authority) != authority_seal:
            raise ValueError("prefix execution authority drifted during execution")

    return _PrefixLoopResult(
        qualification=qualification,
        primary_counters=primary,
        simulator_counters=simulator,
        primary_parsed_turns=parsed_turns["primary_subject"],
        simulator_parsed_turns=parsed_turns["user_simulator"],
        intents=tuple(intents),
        intent_refs=tuple(intent_refs),
        attempts=tuple(attempts),
        attempt_refs=tuple(attempt_refs),
        settlements=tuple(settlements),
        boundaries=tuple(boundaries),
        provider_attempts_ref=provider_attempts_ref,
        boundary_ledger_ref=boundary_ledger_ref,
        provider_cost_ref=provider_cost_ref,
        cost_closure=cost_closure,
        trigger_reason=trigger,
        failure_kind=terminal_failure,
        branch_pending_calls=branch_pending,
        terminal_unexecuted_remainder=terminal_remainder,
        final_observation=final_observation,
        _provenances=loop_provenances,
    )


def _derive_provider_status(
    *,
    observed_ms: int,
    deadline_ms: int,
    response_present: bool,
    transport: str,
    parser: str,
) -> ProviderAttemptStatus:
    """Apply the complete DL-140 response/transport/parser truth table."""

    if (
        type(observed_ms) is not int
        or type(deadline_ms) is not int
        or type(response_present) is not bool
    ):
        raise TypeError("provider status inputs must have exact primitive types")
    if observed_ms < 0 or deadline_ms < 0:
        raise ValueError("provider status times must be nonnegative")
    if transport not in (
        "response",
        "provider_error",
        "infrastructure_error",
        "timeout_no_response",
    ) or parser not in ("turn", "refusal", "malformed", "not_applicable"):
        raise ValueError("provider observation is an unlisted combination")

    validated_parser = parser in ("turn", "refusal", "malformed")
    if observed_ms > deadline_ms:
        if (
            response_present
            and transport in ("response", "provider_error", "infrastructure_error")
            and validated_parser
        ):
            return ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE
        if (
            not response_present
            and transport
            in (
                "provider_error",
                "infrastructure_error",
                "timeout_no_response",
            )
            and parser == "not_applicable"
        ):
            return ProviderAttemptStatus.TIMEOUT_NO_RESPONSE
        raise ValueError("provider observation is an unlisted combination")

    if (
        not response_present
        and transport == "provider_error"
        and parser == "not_applicable"
    ):
        return ProviderAttemptStatus.PROVIDER_ERROR
    if (
        not response_present
        and transport == "infrastructure_error"
        and parser == "not_applicable"
    ):
        return ProviderAttemptStatus.INFRASTRUCTURE_ERROR
    if response_present and validated_parser:
        if transport == "provider_error":
            return ProviderAttemptStatus.PROVIDER_ERROR
        if transport == "infrastructure_error":
            return ProviderAttemptStatus.INFRASTRUCTURE_ERROR
        if transport == "response":
            return {
                "turn": ProviderAttemptStatus.COMPLETED,
                "refusal": ProviderAttemptStatus.REFUSAL,
                "malformed": ProviderAttemptStatus.MALFORMED_RESPONSE,
            }[parser]
    raise ValueError("provider observation is an unlisted combination")


__all__ = []
