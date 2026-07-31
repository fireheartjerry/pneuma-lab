"""Private controller-owned synthetic prefix execution.

This module can replay only sealed local fixture bytes. It has no provider,
model, network, credential, spend, branch, or publication path.
"""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, dataclass
import hashlib
from math import isfinite
from pathlib import Path
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Callable, Literal, Mapping, cast, final

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .authority_refs import (
    AuthorityRefReader,
    closed_mapping,
    decode_artifact_ref,
    load_json_bytes,
    walk_artifact_refs,
)
from .branch_program_authority import load_branch_program_registry
from .controller import derive_call_seed
from .controller_artifacts import (
    ControllerArtifactResolver,
    ControllerArtifactStore,
)
from .evidence import (
    AttemptBoundZeroCostClosure,
    CompositeSnapshotEnvelope,
    CompletedToolBoundaryReceipt,
    ControllerProviderCostClosure,
    ControllerProviderEvent,
    ControllerProviderSettlement,
    FrozenPrefixReceipt,
    GradeEvidence,
    GradeExecutionReceipt,
    ProviderAttemptLedgerRecord,
    ProviderAttemptStatus,
    ProviderCallAttemptReceipt,
    ProviderDispatchIntent,
    ProviderSettlement,
    RuntimeAttestation,
    StatelessAttestation,
    SyntheticZeroAttemptCostClosure,
    ToolBoundaryLedger,
    ContainerAttestation,
    VerifierEvidence,
    VerifierExecutionReceipt,
    composite_snapshot_bytes,
    grade_execution_receipt_bytes,
    load_container_attestation,
    load_controller_provider_cost_closure,
    load_controller_provider_event,
    load_controller_provider_settlement,
    load_composite_snapshot,
    load_grade_execution_receipt,
    load_provider_attempt,
    load_provider_attempt_ledger,
    load_provider_dispatch_intent,
    load_runtime_attestation,
    load_stateless_attestation,
    load_tool_call,
    load_tool_boundary_ledger,
    load_verifier_execution_receipt,
    validate_snapshot_receipt_fields,
    verifier_execution_receipt_bytes,
)
from .execution_authority import (
    PrefixExecutionAuthority,
    _load_prefix_execution_authority_with_reader,
    load_prefix_execution_authority,
)
from .prefix_contracts import (
    AUTHORITY_ASSET_ROLE_MEDIA,
    CONTROLLER_ROLE_MEDIA,
    PRODUCTION_VALIDATED_AUTHORITY_ROLES,
    REF_LOAD_CLASS_BY_ROLE,
    ImplementationDescriptor,
    RawProviderCompletionKind,
    RawProviderObservation,
    SnapshotRestoreReceipt,
    SyntheticClockRead,
    SyntheticPrefixProgram,
    SyntheticProviderTranscriptRow,
    SyntheticRequestPayload,
    SyntheticToolResultPayload,
    StableSourceProvenance,
    load_initial_restore_qualification_receipt,
    load_promoted_authority_asset,
    load_prefix_candidate_receipt,
    load_snapshot_restore_receipt,
    load_synthetic_request_payload,
    load_synthetic_prefix_program,
    load_synthetic_tool_result_payload,
    prefix_candidate_receipt_bytes,
    snapshot_restore_receipt_bytes,
    synthetic_prefix_program_bytes,
)
from .synthetic_environment import (
    InitialQualificationAuthority,
    SyntheticByteTokenizer,
    SyntheticEnvironmentHandle,
    _InitialQualificationResult,
    _SnapshotState,
    _assert_pairwise_isolated,
    _decode_snapshot_state,
    _open_qualified_initial_restore,
)
from .types import (
    ArtifactRef,
    CallSeedReceipt,
    CallContractCaps,
    FailureKind,
    FrozenVerifierReceipt,
    GradeReceipt,
    PrefixCaps,
    ResourceCounters,
    SubjectTurn,
    ToolCall,
    TriggerReason,
)
from .scientific_records import (
    ScientificRefReader,
    decode_scientific_parent,
)


TransportKind = Literal[
    "response",
    "provider_error",
    "infrastructure_error",
    "timeout_no_response",
]
ParserKind = Literal["turn", "refusal", "malformed", "not_applicable"]


def _freeze_descriptor_fields(
    registry: dict[str, dict[str, object]],
) -> Mapping[str, Mapping[str, object]]:
    return MappingProxyType(
        {purpose: MappingProxyType(fields) for purpose, fields in registry.items()}
    )


REGISTERED_LOOP_DESCRIPTOR_FIELDS: Mapping[
    str,
    Mapping[str, object],
] = _freeze_descriptor_fields(
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
            item: {
                "purpose": item,
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
                    }[item]
                ),
                "build_id": f"synthetic-{item.replace('_', '-')}-v1",
                "request_grammar": (
                    "synthetic-request-v1"
                    if item in ("subject", "simulator", "request_renderer")
                    else None
                ),
                "response_grammar": (
                    "synthetic-response-v1"
                    if item in ("subject", "simulator", "response_parser")
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
                    }.get(item)
                ),
                "runtime_id": (
                    "cpython-3.12-local" if item in ("grader", "verifier") else None
                ),
                "container_digest": (
                    "sha256:" + "0" * 64 if item in ("grader", "verifier") else None
                ),
            }
            for item in (
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

    _last_value: int | None
    _position: int
    _program_bytes: bytes
    _program_sha256: str
    _seal: tuple[object, ...]
    _sealed: bool
    _trace: tuple[SyntheticClockRead, ...]

    __slots__ = (
        "_last_value",
        "_position",
        "_program_bytes",
        "_program_sha256",
        "_seal",
        "_sealed",
        "_trace",
    )

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticTraceMeter is final")

    def __init__(
        self,
        *,
        program_bytes: bytes,
    ) -> None:
        if type(program_bytes) is not bytes:
            raise TypeError("program_bytes must be exact bytes")
        sealed_program = bytes(program_bytes)
        program = load_synthetic_prefix_program(sealed_program)
        if synthetic_prefix_program_bytes(program) != sealed_program:
            raise ValueError("meter program bytes are not canonical")
        trace = program.clock_trace
        digest = hashlib.sha256(sealed_program).hexdigest()
        position = 0
        last_value: int | None = None
        object.__setattr__(self, "_program_bytes", sealed_program)
        object.__setattr__(self, "_program_sha256", digest)
        object.__setattr__(self, "_trace", trace)
        object.__setattr__(self, "_position", position)
        object.__setattr__(self, "_last_value", last_value)
        object.__setattr__(
            self,
            "_seal",
            (
                digest,
                len(sealed_program),
                trace,
                position,
                last_value,
            ),
        )
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("SyntheticTraceMeter state is sealed")
        object.__setattr__(self, name, value)

    def _verify_seal(self) -> tuple[SyntheticClockRead, ...]:
        program = load_synthetic_prefix_program(self._program_bytes)
        trace = program.clock_trace
        observed = (
            hashlib.sha256(self._program_bytes).hexdigest(),
            len(self._program_bytes),
            self._trace,
            self._position,
            self._last_value,
        )
        expected_last = (
            None
            if self._position == 0
            else trace[self._position - 1].uint64_ms
            if type(self._position) is int and 0 < self._position <= len(trace)
            else None
        )
        if (
            observed != self._seal
            or self._program_sha256 != observed[0]
            or self._trace != trace
            or type(self._position) is not int
            or not 0 <= self._position <= len(trace)
            or self._last_value != expected_last
            or self._sealed is not True
            or synthetic_prefix_program_bytes(program) != self._program_bytes
        ):
            raise ValueError("meter sealed state drifted")
        return trace

    def read(self, *, label: str, program_sha256: str) -> int:
        trace = self._verify_seal()
        if program_sha256 != self._program_sha256:
            raise ValueError("meter program digest differs from sealed program")
        if self._position >= len(trace):
            raise ValueError("meter trace is exhausted")
        row = trace[self._position]
        if row.label != label:
            raise ValueError(
                f"meter label differs: expected {row.label!r}, received {label!r}"
            )
        if self._last_value is not None and row.uint64_ms < self._last_value:
            raise ValueError("meter trace decreased")
        position = self._position + 1
        last_value = row.uint64_ms
        object.__setattr__(self, "_position", position)
        object.__setattr__(self, "_last_value", last_value)
        object.__setattr__(
            self,
            "_seal",
            (
                self._program_sha256,
                len(self._program_bytes),
                trace,
                position,
                last_value,
            ),
        )
        return row.uint64_ms

    def _assert_exhausted(self) -> None:
        trace = self._verify_seal()
        if self._position != len(trace):
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

    def decode(
        self,
        *,
        payload: bytes,
        program: SyntheticPrefixProgram,
        expected_payload: bytes,
    ) -> GradeEvidence:
        if payload != expected_payload:
            raise ValueError("grade evidence differs from sealed program bytes")
        value = load_json_bytes(payload, source=Path("<synthetic-grade-evidence>"))
        mapping = closed_mapping(
            value,
            fields=("success", "partial_reward", "infrastructure_failure"),
            field="grade evidence",
        )
        success = mapping["success"]
        partial_reward = mapping["partial_reward"]
        infrastructure_failure = mapping["infrastructure_failure"]
        if type(success) is not int or success not in (0, 1):
            raise TypeError("grade evidence success must be exact int 0 or 1")
        if type(partial_reward) is not float or not isfinite(partial_reward):
            raise TypeError("grade evidence partial_reward must be finite exact float")
        if type(infrastructure_failure) is not bool:
            raise TypeError(
                "grade evidence infrastructure_failure must be exact bool"
            )
        result = program.grade_result
        if (
            success != result.success
            or partial_reward != result.partial_reward
            or infrastructure_failure is not result.infrastructure_failure
        ):
            raise ValueError("grade evidence fields differ from sealed result")
        if payload != canonical_json_bytes(value, indent=None):
            raise ValueError("grade evidence must be compact canonical JSON")
        return GradeEvidence(
            success=success,
            partial_reward=partial_reward,
            infrastructure_failure=infrastructure_failure,
            raw_payload=payload,
        )


@final
class SyntheticVerifierCodec:
    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticVerifierCodec is final")

    def decode(
        self,
        *,
        payload: bytes,
        program: SyntheticPrefixProgram,
        expected_payload: bytes,
    ) -> VerifierEvidence:
        if payload != expected_payload:
            raise ValueError("verifier evidence differs from sealed program bytes")
        value = load_json_bytes(payload, source=Path("<synthetic-verifier-evidence>"))
        mapping = closed_mapping(
            value,
            fields=("finding_count",),
            field="verifier evidence",
        )
        finding_count = mapping["finding_count"]
        if type(finding_count) is not int or finding_count < 0:
            raise TypeError(
                "verifier evidence finding_count must be nonnegative exact int"
            )
        if (
            finding_count != program.verifier_result.finding_count
            or payload != canonical_json_bytes(value, indent=None)
        ):
            raise ValueError("verifier evidence differs from sealed result")
        return VerifierEvidence(
            finding_count=finding_count,
            raw_payload=payload,
        )


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


def _pre_provider_action_failure(
    *,
    now_ms: int,
    deadline_ms: int,
    counters: ResourceCounters,
    parsed_turns: int,
    prefix_caps: PrefixCaps,
    contract_caps: CallContractCaps,
) -> FailureKind:
    """Apply wall, token, then discrete pre-dispatch precedence."""

    if (
        type(now_ms) is not int
        or type(deadline_ms) is not int
        or now_ms < 0
        or deadline_ms < 0
    ):
        raise TypeError("pre-dispatch times must be nonnegative exact integers")
    if now_ms >= deadline_ms:
        return FailureKind.TIMEOUT
    return _pre_dispatch_failure(
        counters=counters,
        parsed_turns=parsed_turns,
        prefix_caps=prefix_caps,
        contract_caps=contract_caps,
    )


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
    _cursor: int
    _payloads: Mapping[ArtifactRef, bytes]
    _program: SyntheticPrefixProgram
    _program_bytes: bytes
    _program_sha256: str
    _role_rows: tuple[SyntheticProviderTranscriptRow, ...]
    _seal: tuple[object, ...]
    _sealed: bool
    _subject_role: Literal["primary_subject", "user_simulator"]

    __slots__ = (
        "_cursor",
        "_payloads",
        "_program",
        "_program_bytes",
        "_program_sha256",
        "_role_rows",
        "_seal",
        "_sealed",
        "_subject_role",
    )

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticProviderActor is final")

    def __init__(
        self,
        *,
        subject_role: Literal["primary_subject", "user_simulator"],
        program_bytes: bytes,
        payloads: Mapping[ArtifactRef, bytes],
    ) -> None:
        if subject_role not in ("primary_subject", "user_simulator"):
            raise ValueError("provider actor role is not registered")
        if type(program_bytes) is not bytes:
            raise TypeError("provider actor program_bytes must be exact bytes")
        if not isinstance(payloads, Mapping):
            raise TypeError("provider actor payloads must be a mapping")
        copied_payloads: dict[ArtifactRef, bytes] = {}
        for ref, payload in payloads.items():
            if type(ref) is not ArtifactRef or type(payload) is not bytes:
                raise TypeError("provider actor payload state is not exact")
            copied_payloads[ref] = bytes(payload)
        sealed_program = bytes(program_bytes)
        program = load_synthetic_prefix_program(sealed_program)
        role_rows = tuple(
            row
            for row in program.provider_transcript
            if row.subject_role == subject_role
        )
        payload_seal = tuple(
            sorted(
                (
                    ref.relative_path,
                    ref.sha256,
                    hashlib.sha256(payload).hexdigest(),
                    len(payload),
                )
                for ref, payload in copied_payloads.items()
            )
        )
        cursor = 0
        object.__setattr__(self, "_subject_role", subject_role)
        object.__setattr__(self, "_program_bytes", sealed_program)
        object.__setattr__(
            self,
            "_program_sha256",
            hashlib.sha256(sealed_program).hexdigest(),
        )
        object.__setattr__(self, "_program", program)
        object.__setattr__(self, "_role_rows", role_rows)
        object.__setattr__(self, "_payloads", MappingProxyType(copied_payloads))
        object.__setattr__(self, "_cursor", cursor)
        object.__setattr__(
            self,
            "_seal",
            (
                subject_role,
                hashlib.sha256(sealed_program).hexdigest(),
                len(sealed_program),
                role_rows,
                cursor,
                payload_seal,
            ),
        )
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, name: str, value: object) -> None:
        if getattr(self, "_sealed", False):
            raise AttributeError("SyntheticProviderActor state is sealed")
        object.__setattr__(self, name, value)

    def _verify_seal(
        self,
    ) -> tuple[SyntheticProviderTranscriptRow, ...]:
        program = load_synthetic_prefix_program(self._program_bytes)
        role_rows = tuple(
            row
            for row in program.provider_transcript
            if row.subject_role == self._subject_role
        )
        payload_seal = tuple(
            sorted(
                (
                    ref.relative_path,
                    ref.sha256,
                    hashlib.sha256(payload).hexdigest(),
                    len(payload),
                )
                for ref, payload in self._payloads.items()
            )
        )
        observed = (
            self._subject_role,
            hashlib.sha256(self._program_bytes).hexdigest(),
            len(self._program_bytes),
            self._role_rows,
            self._cursor,
            payload_seal,
        )
        if (
            observed != self._seal
            or self._program_sha256 != observed[1]
            or self._role_rows != role_rows
            or type(self._cursor) is not int
            or not 0 <= self._cursor <= len(role_rows)
            or self._sealed is not True
            or synthetic_prefix_program_bytes(self._program) != self._program_bytes
        ):
            raise ValueError("provider actor sealed state drifted")
        return role_rows

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
    ) -> RawProviderObservation:
        role_rows = self._verify_seal()
        if (
            subject_role != self._subject_role
            or type(remaining_caps) is not CallContractCaps
            or type(absolute_deadline_ms) is not int
            or len(dispatch_intent_sha256) != 64
        ):
            raise ValueError("provider invocation differs from registered actor")
        try:
            row = role_rows[self._cursor]
        except IndexError as exc:
            raise ValueError("provider actor transcript is exhausted") from exc
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
        observation = RawProviderObservation(
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
        cursor = self._cursor + 1
        object.__setattr__(self, "_cursor", cursor)
        object.__setattr__(
            self,
            "_seal",
            (
                self._subject_role,
                self._program_sha256,
                len(self._program_bytes),
                role_rows,
                cursor,
                self._seal[-1],
            ),
        )
        return observation

    def _assert_exhausted(self) -> None:
        role_rows = self._verify_seal()
        if self._cursor != len(role_rows):
            raise ValueError("provider actor has unconsumed role-local rows")


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
    program_bytes: bytes,
    payloads: Mapping[ArtifactRef, bytes],
) -> _LoopComponents:
    _validate_descriptor_registry(authority)
    return _LoopComponents(
        subject=SyntheticProviderActor(
            subject_role="primary_subject",
            program_bytes=program_bytes,
            payloads=payloads,
        ),
        simulator=(
            None
            if authority.simulator_contract_ref is None
            else SyntheticProviderActor(
                subject_role="user_simulator",
                program_bytes=program_bytes,
                payloads=payloads,
            )
        ),
        meter=SyntheticTraceMeter(
            program_bytes=program_bytes,
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
    cumulative_mutation: bool
    _store: ControllerArtifactStore | None
    _authority: PrefixExecutionAuthority
    _program: SyntheticPrefixProgram
    _program_bytes: bytes
    _payloads: Mapping[ArtifactRef, bytes]
    _components: _LoopComponents
    _provenances: tuple[StableSourceProvenance, ...]

    def close(self) -> None:
        errors: list[BaseException] = []
        store = self._store
        self._store = None
        if store is not None:
            try:
                store.close()
            except BaseException as exc:
                errors.append(exc)
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
    descriptors = authority.implementation_descriptors
    if len(descriptors) != len({item.purpose for item in descriptors}):
        raise ValueError("authority has duplicate descriptor purposes")
    by_purpose: dict[str, ImplementationDescriptor] = {
        descriptor.purpose: descriptor for descriptor in descriptors
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
    if authority.schedule_authority not in {"synthetic_validation", "implementation_verification"}:
        raise ValueError(
            "prefix loop requires a synthetic or implementation-verification authority"
        )
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
    store: ControllerArtifactStore | None = None
    try:
        for purpose, descriptor in descriptors.items():
            authority_provenance = StableSourceProvenance(
                root,
                Path(descriptor.implementation_source_ref.relative_path),
                descriptor.implementation_source_ref,
            )
            loop_provenances.append(authority_provenance)
            local_provenance = StableSourceProvenance(
                _SOURCE_ROOT,
                _SOURCE_PATH_BY_PURPOSE[purpose],
                descriptor.implementation_source_ref,
            )
            loop_provenances.append(local_provenance)
            if authority_provenance.payload != local_provenance.payload:
                raise ValueError(
                    f"{purpose} copied source differs from registered local source"
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
        store = ControllerArtifactStore(root)
        return _execute_open_loop(
            run_root=root,
            authority=authority,
            program=program,
            program_bytes=program_bytes,
            payloads=payloads,
            qualification=qualification,
            store=store,
            loop_provenances=tuple(loop_provenances),
        )
    except BaseException as primary:
        errors: list[BaseException] = [primary]
        if qualification is not None:
            try:
                qualification.close()
            except BaseException as exc:
                errors.append(exc)
        if store is not None:
            try:
                store.close()
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
    store: ControllerArtifactStore,
    loop_provenances: tuple[StableSourceProvenance, ...],
) -> _PrefixLoopResult:
    authority_seal = repr(authority)
    live = qualification._resources[0]
    handle: SyntheticEnvironmentHandle = live.handle
    components = _construct_components(
        authority=authority,
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
    tool_observation_position = 0
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

    with nullcontext(store):
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

            before_label = f"before_{role}_{call_indexes[role]}"
            before = meter.read(
                label=before_label,
                program_sha256=program_sha256,
            )
            elapsed = max(0, before - epoch)
            pre_action_failure = _pre_provider_action_failure(
                now_ms=before,
                deadline_ms=deadline,
                counters=role_counter,
                parsed_turns=parsed_turns[role],
                prefix_caps=role_prefix_caps,
                contract_caps=contract_caps,
            )
            if (
                pre_action_failure is FailureKind.NONE
                and contract_caps.per_call_turns == 0
            ):
                pre_action_failure = FailureKind.TURN_CAP
            if pre_action_failure is not FailureKind.NONE:
                terminate(pre_action_failure, ())
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
                tool_token_cap = min(
                    authority.prefix_caps.generated_tokens,
                    authority.subject_contract_caps.aggregate_generated_tokens,
                )
                # Aggregate and per-call overshoot are resolved immediately after
                # provider completion. Tools consume no generated tokens, so exact
                # equality remains admissible while a queued tool is executed.
                if primary.generated_tokens > tool_token_cap:
                    terminate(FailureKind.TOKEN_CAP, pending)
                    break
                if primary.tool_calls >= authority.prefix_caps.tool_calls:
                    terminate(FailureKind.TOOL_CAP, pending)
                    break
                if tool_observation_position >= len(program.tool_observations):
                    raise ValueError("tool observation program is exhausted")
                expected_tool = program.tool_observations[tool_observation_position]
                if expected_tool.call_id != call.call_id:
                    raise ValueError("tool observation order differs from parsed queue")
                executed_id, result_bytes = handle.execute_tool(call)
                if (
                    executed_id != call.call_id
                    or result_bytes != payloads[expected_tool.result_ref]
                ):
                    raise ValueError("tool result differs from sealed observation")
                mutation = handle.mutation_committed()
                mutation_has_returned = mutation_has_returned or mutation
                eligible = handle.verifier_eligible()
                terminal = handle.episode_terminal()
                failure = handle.failure_kind()
                if (
                    mutation != expected_tool.mutation_committed
                    or eligible != expected_tool.verifier_eligible
                    or terminal != expected_tool.episode_terminal
                    or failure is not expected_tool.failure_kind
                ):
                    raise ValueError(
                        "independent tool state differs from sealed observation"
                    )
                completion_tool = meter.read(
                    label=f"after_tool_{call.call_id}",
                    program_sha256=program_sha256,
                )
                elapsed = max(0, completion_tool - epoch)
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
                tool_observation_position += 1
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

        if transcript_position != len(program.provider_transcript):
            raise ValueError("program has unconsumed provider transcript rows")
        for actor in actors.values():
            actor._assert_exhausted()
        if program.expected_trigger_reason is not trigger:
            raise ValueError("derived trigger differs from sealed post-hoc expectation")
        if tool_observation_position != len(program.tool_observations):
            raise ValueError("tool observation program has unconsumed rows")
        meter._assert_exhausted()
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
        cumulative_mutation=mutation_has_returned,
        _store=store,
        _authority=authority,
        _program=program,
        _program_bytes=program_bytes,
        _payloads=payloads,
        _components=components,
        _provenances=loop_provenances,
    )


def _remaining_prefix_caps(
    caps: PrefixCaps,
    counters: ResourceCounters,
) -> PrefixCaps:
    return PrefixCaps(
        max(0, caps.generated_tokens - counters.generated_tokens),
        max(0, caps.model_calls - counters.model_calls),
        max(0, caps.tool_calls - counters.tool_calls),
        max(0, caps.wall_clock_ms - counters.wall_clock_ms),
    )


def _remaining_call_caps(
    caps: CallContractCaps,
    counters: ResourceCounters,
    *,
    parsed_turns: int,
) -> CallContractCaps:
    return CallContractCaps(
        max(0, caps.aggregate_generated_tokens - counters.generated_tokens),
        max(0, caps.aggregate_model_calls - counters.model_calls),
        max(0, caps.aggregate_turns - parsed_turns),
        caps.per_call_generated_tokens,
        caps.per_call_turns,
    )


def _scientific_y0_grade(
    *,
    trigger_reason: TriggerReason,
    failure_kind: FailureKind,
    evidence: GradeEvidence,
    evidence_ref: ArtifactRef,
) -> GradeReceipt:
    adverse_no_trigger = (
        trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY
        and failure_kind is not FailureKind.NONE
    )
    return GradeReceipt(
        success=0 if adverse_no_trigger else evidence.success,
        partial_reward=0.0 if adverse_no_trigger else evidence.partial_reward,
        infrastructure_failure=evidence.infrastructure_failure,
        artifact_ref=evidence_ref,
    )


def _attestation_bytes(
    *,
    kind: str,
    authority_ref: ArtifactRef,
    program_sha256: str,
    values: Mapping[str, object] | None = None,
) -> bytes:
    return canonical_json_bytes(
        {
            "authority_ref": _ref_mapping(authority_ref),
            "program_sha256": program_sha256,
            "record_kind": kind,
            "schema_version": "1",
            **({} if values is None else dict(values)),
        },
        indent=None,
    )


def _restore_exact_snapshot(
    *,
    owned: object,
    purpose: Literal["grade", "verify"],
    environment_snapshot: bytes,
    expected_state: _SnapshotState,
    expected_visible: bytes,
    expected_token_ids: tuple[int, ...],
    tokenizer: SyntheticByteTokenizer,
    authority: PrefixExecutionAuthority,
    task_ref: ArtifactRef,
    composite_snapshot_ref: ArtifactRef,
    environment_snapshot_ref: ArtifactRef,
    visible_context_ref: ArtifactRef,
    token_ids_ref: ArtifactRef,
) -> SnapshotRestoreReceipt:
    from .synthetic_environment import _OwnedEnvironment

    if type(owned) is not _OwnedEnvironment:
        raise TypeError("restore environment must be exact owned environment")
    environment = cast(_OwnedEnvironment, owned)
    handle = environment.handle
    handle.start()
    handle.restore(environment_snapshot)
    resnapshot = handle.snapshot()
    if resnapshot != environment_snapshot:
        raise ValueError(f"{purpose} restore snapshot bytes differ")
    state = _decode_snapshot_state(resnapshot)
    if state != expected_state:
        raise ValueError(f"{purpose} restored state differs")
    visible = handle.visible_context()
    if visible != expected_visible:
        raise ValueError(f"{purpose} restored visible context differs")
    token_ids = tokenizer.encode(visible)
    if token_ids != expected_token_ids:
        raise ValueError(f"{purpose} restored token IDs differ")
    independent = (
        (
            "simulator context",
            handle.simulator_context(),
            expected_state.simulator_context,
        ),
        (
            "mutation state",
            handle.mutation_committed(),
            expected_state.mutation_committed,
        ),
        (
            "verifier eligibility",
            handle.verifier_eligible(),
            expected_state.verifier_eligible,
        ),
        (
            "terminal state",
            handle.episode_terminal(),
            expected_state.episode_terminal,
        ),
        (
            "failure state",
            handle.failure_kind(),
            expected_state.failure_kind,
        ),
    )
    for field, observed, expected in independent:
        if observed != expected:
            raise ValueError(f"{purpose} restored {field} differs")
    return SnapshotRestoreReceipt(
        purpose=purpose,
        schedule_ref=authority.schedule_ref,
        task_ref=task_ref,
        task_input_ref=authority.task_input_ref,
        environment_contract_ref=authority.environment_contract_ref,
        isolation_contract_ref=authority.isolation_contract_ref,
        composite_snapshot_ref=composite_snapshot_ref,
        environment_snapshot_ref=environment_snapshot_ref,
        observed_resnapshot_sha256=hashlib.sha256(resnapshot).hexdigest(),
        observed_resnapshot_byte_count=len(resnapshot),
        branch_pending_calls=state.branch_pending_calls,
        terminal_unexecuted_remainder=state.terminal_unexecuted_remainder,
        visible_context_ref=visible_context_ref,
        visible_sha256=hashlib.sha256(visible).hexdigest(),
        token_ids_ref=token_ids_ref,
        token_ids_sha256=token_ids_ref.sha256,
        episode_terminal=state.episode_terminal,
        failure_kind=state.failure_kind,
        restored_identity=environment.identity,
        verified=True,
    )


def _assert_evidence_call_read_only(
    *,
    purpose: Literal["grade", "verify"],
    handle: SyntheticEnvironmentHandle,
    environment_snapshot: bytes,
    expected_state: _SnapshotState,
) -> None:
    if handle.snapshot() != environment_snapshot:
        raise ValueError(f"{purpose} evidence call mutated snapshot bytes")
    if (
        handle.visible_context() != expected_state.visible_context
        or handle.simulator_context() != expected_state.simulator_context
        or handle.mutation_committed() != expected_state.mutation_committed
        or handle.verifier_eligible() != expected_state.verifier_eligible
        or handle.episode_terminal() != expected_state.episode_terminal
        or handle.failure_kind() is not expected_state.failure_kind
    ):
        raise ValueError(f"{purpose} evidence call mutated observable state")


_CONTROLLER_JSON_FIELDS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "selected_task": frozenset({"prefix_seed", "provider_lane", "slots", "task"}),
        "visible_context": frozenset(),
        "token_ids": frozenset({"token_ids"}),
        "input_token_ids": frozenset({"token_ids"}),
        "output_token_ids": frozenset({"token_ids"}),
        "provider_request": frozenset({"context_base64", "subject_role"}),
        "provider_dispatch_intent": frozenset(
            {
                "absolute_deadline_ms",
                "call_index",
                "input_token_ids_ref",
                "model_contract_ref",
                "request_ref",
                "seed",
                "subject_role",
            }
        ),
        "provider_event": frozenset(
            {
                "call_index",
                "completion_kind",
                "cost_microunits",
                "dispatch_intent_sha256",
                "model_contract_sha256",
                "observed_at_ms",
                "response_sha256",
                "schema_version",
                "seed",
                "subject_role",
            }
        ),
        "provider_attempt": frozenset(
            {
                "call_index",
                "dispatch_intent_ref",
                "elapsed_ms",
                "generated_tokens",
                "input_token_ids_ref",
                "model_contract_ref",
                "output_token_ids_ref",
                "provider_event_ref",
                "request_ref",
                "response_ref",
                "seed",
                "status",
                "subject_role",
            }
        ),
        "provider_attempt_ledger": frozenset(
            {"attempt_refs", "attempts", "intent_refs", "intents"}
        ),
        "provider_settlement": frozenset(
            {
                "attempt_sha256",
                "call_index",
                "cost_microunits",
                "currency",
                "dispatch_intent_sha256",
                "final",
                "provider_event_sha256",
                "schema_version",
                "seed",
                "subject_role",
            }
        ),
        "provider_cost_closure": frozenset(
            {"attempt_refs", "settlement_refs", "total_cost_microunits"}
        ),
        "tool_call": frozenset({"call_id", "canonical_arguments_json", "name"}),
        "tool_boundary_ledger": frozenset({"boundaries"}),
        "subject_stateless_attestation": frozenset(
            {
                "authority_ref",
                "program_sha256",
                "record_kind",
                "schema_version",
                "stateless",
            }
        ),
        "simulator_stateless_attestation": frozenset(
            {
                "authority_ref",
                "program_sha256",
                "record_kind",
                "schema_version",
                "stateless",
            }
        ),
        "runtime_attestation": frozenset(
            {
                "authority_ref",
                "program_sha256",
                "record_kind",
                "runtime_id",
                "schema_version",
            }
        ),
        "container_attestation": frozenset(
            {
                "authority_ref",
                "container_digest",
                "program_sha256",
                "record_kind",
                "schema_version",
            }
        ),
        "verifier_source": frozenset(
            {
                "record_kind",
                "schema_version",
                "task_id",
                "benchmark",
                "components",
                "objective_findings",
            }
        ),
        "verifier_report": frozenset(
            {"record_kind", "schema_version", "task_id", "report_text"}
        ),
        "verifier_feature": frozenset(
            {
                "record_kind",
                "schema_version",
                "task_id",
                "benchmark",
                "source_verifier_ref",
                "source_report_ref",
                "components",
                "objective_finding_count",
                "normalized_report_token_count",
            }
        ),
    }
)

_ARTIFACT_REF_KEYS = frozenset(
    {"role", "relative_path", "sha256", "byte_count", "media_type"}
)


def _reject_malformed_ref_shapes(value: object, *, field: str) -> None:
    if isinstance(value, Mapping):
        overlap = set(value) & _ARTIFACT_REF_KEYS
        if overlap and set(value) != _ARTIFACT_REF_KEYS:
            raise ValueError(f"{field} contains an open ArtifactRef shape")
        for key, nested in value.items():
            _reject_malformed_ref_shapes(nested, field=f"{field}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_malformed_ref_shapes(nested, field=f"{field}[{index}]")


def _require_mapping_fields(
    value: object,
    expected: frozenset[str],
    *,
    field: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"{field} has an open or incomplete shape")
    return cast(Mapping[str, object], value)


def _decode_expected_ref(
    value: object,
    *,
    field: str,
    expected_role: str,
) -> ArtifactRef:
    try:
        return decode_artifact_ref(
            value,
            field=field,
            expected_role=expected_role,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is invalid") from exc


def _exact_nonnegative_json_int(value: object, *, field: str) -> int:
    if type(value) is not int or cast(int, value) < 0:
        raise ValueError(f"{field} must be a nonnegative exact int")
    return cast(int, value)


def _validate_controller_json_shape(role: str, value: object) -> None:
    if role == "visible_context":
        return
    expected = _CONTROLLER_JSON_FIELDS.get(role)
    if expected is None:
        return
    mapping = _require_mapping_fields(value, expected, field=role)
    if role in ("token_ids", "input_token_ids", "output_token_ids"):
        token_ids = mapping["token_ids"]
        if type(token_ids) is not list or any(
            type(token_id) is not int or token_id < 0
            for token_id in cast(list[object], token_ids)
        ):
            raise ValueError(f"{role}.token_ids must be nonnegative integers")
    elif role == "provider_request":
        if type(mapping["context_base64"]) is not str:
            raise TypeError("provider_request.context_base64 must be exact text")
        if mapping["subject_role"] not in (
            "primary_subject",
            "user_simulator",
        ):
            raise ValueError("provider_request.subject_role is not registered")
    elif role == "provider_dispatch_intent":
        subject_role = mapping["subject_role"]
        if subject_role not in ("primary_subject", "user_simulator"):
            raise ValueError("provider_dispatch_intent.subject_role is not registered")
        for name in ("absolute_deadline_ms", "call_index", "seed"):
            _exact_nonnegative_json_int(
                mapping[name],
                field=f"provider_dispatch_intent.{name}",
            )
        for name, expected_role in (
            ("input_token_ids_ref", "input_token_ids"),
            ("request_ref", "provider_request"),
            (
                "model_contract_ref",
                (
                    "subject_contract"
                    if subject_role == "primary_subject"
                    else "simulator_contract"
                ),
            ),
        ):
            _decode_expected_ref(
                mapping[name],
                field=f"provider_dispatch_intent.{name}",
                expected_role=expected_role,
            )
    elif role == "provider_attempt":
        subject_role = mapping["subject_role"]
        if subject_role not in ("primary_subject", "user_simulator"):
            raise ValueError("provider_attempt.subject_role is not registered")
        for name in ("call_index", "elapsed_ms", "generated_tokens", "seed"):
            _exact_nonnegative_json_int(
                mapping[name],
                field=f"provider_attempt.{name}",
            )
        try:
            ProviderAttemptStatus(cast(str, mapping["status"]))
        except (TypeError, ValueError) as exc:
            raise ValueError("provider_attempt.status is invalid") from exc
        for name, expected_role in (
            ("dispatch_intent_ref", "provider_dispatch_intent"),
            ("input_token_ids_ref", "input_token_ids"),
            ("provider_event_ref", "provider_event"),
            ("request_ref", "provider_request"),
            (
                "model_contract_ref",
                (
                    "subject_contract"
                    if subject_role == "primary_subject"
                    else "simulator_contract"
                ),
            ),
        ):
            _decode_expected_ref(
                mapping[name],
                field=f"provider_attempt.{name}",
                expected_role=expected_role,
            )
        for name, expected_role in (
            ("output_token_ids_ref", "output_token_ids"),
            ("response_ref", "provider_response"),
        ):
            if mapping[name] is not None:
                _decode_expected_ref(
                    mapping[name],
                    field=f"provider_attempt.{name}",
                    expected_role=expected_role,
                )
        if (mapping["output_token_ids_ref"] is None) != (
            mapping["response_ref"] is None
        ):
            raise ValueError("provider_attempt response/output refs must co-occur")
    elif role == "provider_event":
        for name in (
            "call_index",
            "cost_microunits",
            "observed_at_ms",
            "seed",
        ):
            _exact_nonnegative_json_int(
                mapping[name],
                field=f"provider_event.{name}",
            )
        if mapping["schema_version"] != "1" or mapping["subject_role"] not in (
            "primary_subject",
            "user_simulator",
        ):
            raise ValueError("provider_event identity is invalid")
        try:
            ProviderAttemptStatus(cast(str, mapping["completion_kind"]))
        except (TypeError, ValueError) as exc:
            raise ValueError("provider_event completion_kind is invalid") from exc
        for name in ("dispatch_intent_sha256", "model_contract_sha256"):
            candidate = mapping[name]
            if (
                type(candidate) is not str
                or len(cast(str, candidate)) != 64
                or any(character not in "0123456789abcdef" for character in candidate)
            ):
                raise ValueError(f"provider_event.{name} is not a digest")
    elif role == "provider_settlement":
        for name in ("call_index", "cost_microunits", "seed"):
            _exact_nonnegative_json_int(
                mapping[name],
                field=f"provider_settlement.{name}",
            )
        if (
            mapping["schema_version"] != "1"
            or mapping["currency"] != "synthetic_microunit"
            or mapping["cost_microunits"] != 0
            or mapping["final"] is not True
            or mapping["subject_role"] not in ("primary_subject", "user_simulator")
        ):
            raise ValueError("provider_settlement identity is invalid")
    elif role == "tool_call":
        for name in ("call_id", "canonical_arguments_json", "name"):
            if type(mapping[name]) is not str or not mapping[name]:
                raise ValueError(f"tool_call.{name} must be nonempty exact text")
    if role == "selected_task":
        slots = mapping["slots"]
        task = mapping["task"]
        if type(slots) is not list:
            raise ValueError("selected_task.slots must be an array")
        for index, slot in enumerate(cast(list[object], slots)):
            _require_mapping_fields(
                slot,
                frozenset({"execution_order", "hardware_lane", "seed", "slot_id"}),
                field=f"selected_task.slots[{index}]",
            )
        _require_mapping_fields(
            task,
            frozenset(
                {
                    "benchmark",
                    "lineage",
                    "sensitivity_groups",
                    "stratum",
                    "task_id",
                }
            ),
            field="selected_task.task",
        )
    elif role == "provider_attempt_ledger":
        for plural, singular, fields_set in (
            (
                "attempts",
                "attempt",
                _CONTROLLER_JSON_FIELDS["provider_attempt"],
            ),
            (
                "intents",
                "intent",
                _CONTROLLER_JSON_FIELDS["provider_dispatch_intent"],
            ),
        ):
            rows = mapping[plural]
            if type(rows) is not list:
                raise ValueError(f"{role}.{plural} must be an array")
            for index, row in enumerate(cast(list[object], rows)):
                _require_mapping_fields(
                    row,
                    fields_set,
                    field=f"{role}.{singular}[{index}]",
                )
                _validate_controller_json_shape(
                    (
                        "provider_attempt"
                        if plural == "attempts"
                        else "provider_dispatch_intent"
                    ),
                    row,
                )
    elif role == "tool_boundary_ledger":
        rows = mapping["boundaries"]
        if type(rows) is not list:
            raise ValueError("tool boundary ledger must contain an array")
        for index, row in enumerate(cast(list[object], rows)):
            _require_mapping_fields(
                row,
                frozenset(
                    {
                        "call_id",
                        "elapsed_ms",
                        "episode_terminal",
                        "failure_kind",
                        "mutation_committed",
                        "tool_call_ref",
                        "tool_result_ref",
                        "verifier_eligible_after",
                    }
                ),
                field=f"tool_boundary_ledger.boundaries[{index}]",
            )
            typed = cast(Mapping[str, object], row)
            _decode_expected_ref(
                typed["tool_call_ref"],
                field=f"tool_boundary_ledger.boundaries[{index}].tool_call_ref",
                expected_role="tool_call",
            )
            _decode_expected_ref(
                typed["tool_result_ref"],
                field=f"tool_boundary_ledger.boundaries[{index}].tool_result_ref",
                expected_role="tool_result",
            )
    elif role == "provider_cost_closure":
        for name, expected_role in (
            ("attempt_refs", "provider_attempt"),
            ("settlement_refs", "provider_settlement"),
        ):
            refs = mapping[name]
            if type(refs) is not list:
                raise ValueError(f"provider_cost_closure.{name} must be an array")
            for index, ref in enumerate(cast(list[object], refs)):
                _decode_expected_ref(
                    ref,
                    field=f"provider_cost_closure.{name}[{index}]",
                    expected_role=expected_role,
                )
        if mapping["total_cost_microunits"] != 0:
            raise ValueError("provider cost closure must equal exact zero")
    elif role.endswith("_attestation"):
        if mapping["schema_version"] != "1":
            raise ValueError(f"{role} schema_version is invalid")
        expected_authority_role = (
            "subject_contract"
            if role == "subject_stateless_attestation"
            else (
                "simulator_contract"
                if role == "simulator_stateless_attestation"
                else "source_revision"
            )
        )
        _decode_expected_ref(
            mapping["authority_ref"],
            field=f"{role}.authority_ref",
            expected_role=expected_authority_role,
        )


def _controller_nested_refs(role: str, payload: bytes) -> tuple[ArtifactRef, ...]:
    if CONTROLLER_ROLE_MEDIA[role] == "application/octet-stream":
        return ()
    if role == "prefix_candidate_receipt":
        load_prefix_candidate_receipt(payload)
    elif role == "composite_snapshot":
        load_composite_snapshot(payload)
    elif role == "initial_restore_qualification":
        load_initial_restore_qualification_receipt(payload)
    elif role in ("grade_restore_receipt", "verifier_restore_receipt"):
        load_snapshot_restore_receipt(payload)
    elif role == "grade_evidence_receipt":
        load_grade_execution_receipt(payload)
    elif role == "verifier_evidence_receipt":
        load_verifier_execution_receipt(payload)
    value = load_json_bytes(payload, source=Path(f"<{role}>"))
    if payload != canonical_json_bytes(value, indent=None):
        raise ValueError(f"{role} must be compact canonical JSON")
    _reject_malformed_ref_shapes(value, field=role)
    typed_loader = _CONTROLLER_TYPED_LOADERS.get(role)
    if typed_loader is None:
        _validate_controller_json_shape(role, value)
    else:
        typed_loader(payload)
    return walk_artifact_refs(value)


_CONTROLLER_TYPED_LOADERS: Mapping[str, Callable[[bytes], object]] = MappingProxyType(
    {
        "provider_dispatch_intent": load_provider_dispatch_intent,
        "provider_attempt": load_provider_attempt,
        "provider_attempt_ledger": load_provider_attempt_ledger,
        "provider_event": load_controller_provider_event,
        "provider_settlement": load_controller_provider_settlement,
        "provider_cost_closure": load_controller_provider_cost_closure,
        "tool_boundary_ledger": load_tool_boundary_ledger,
        "subject_stateless_attestation": lambda payload: load_stateless_attestation(
            payload,
            expected_role="primary_subject",
        ),
        "simulator_stateless_attestation": lambda payload: load_stateless_attestation(
            payload,
            expected_role="user_simulator",
        ),
        "runtime_attestation": load_runtime_attestation,
        "container_attestation": load_container_attestation,
    }
)


AuthorityAssetDecoder = Callable[
    [ArtifactRef, bytes, object | None, frozenset[ArtifactRef]],
    tuple[ArtifactRef, ...],
]


def _decode_prevalidated_authority_asset(
    ref: ArtifactRef,
    _payload: bytes,
    value: object | None,
    prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    if ref not in prevalidated_refs:
        raise ValueError(
            f"{ref.role} lacks a fresh exact production-validator proof"
        )
    return walk_artifact_refs(value)


def _decode_promoted_authority_asset(
    ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    return load_promoted_authority_asset(
        role=ref.role,
        payload=payload,
    ).nested_refs


def _decode_source_revision(
    _ref: ArtifactRef,
    _payload: bytes,
    value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    if value is not None:
        raise ValueError("source_revision must remain byte-only")
    return ()


def _decode_manifest_source_asset(
    _ref: ArtifactRef,
    payload: bytes,
    value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    """Load a manifest-owned JSON source reached during fresh graph replay."""

    if value is None:
        raise ValueError("manifest source must be canonical JSON")
    return walk_artifact_refs(value)


def _decode_power_authority_asset(
    _ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    if not payload:
        raise ValueError("power authority must not be empty")
    return ()


def _decode_program_asset(
    _ref: ArtifactRef,
    payload: bytes,
    value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    load_synthetic_prefix_program(payload)
    return walk_artifact_refs(value)


def _decode_branch_program_registry_asset(
    _ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    """Validate future branch authority without importing it into prefix replay."""

    load_branch_program_registry(payload)
    return ()


def _decode_request_asset(
    _ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    load_synthetic_request_payload(payload)
    return ()


def _decode_response_asset(
    _ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    SyntheticResponseParser().parse(payload)
    return ()


def _decode_provider_event_asset(
    _ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    _decode_raw_event(payload)
    return ()


def _decode_tool_result_asset(
    _ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    load_synthetic_tool_result_payload(payload)
    return ()


def _decode_grade_result_asset(
    _ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    value = load_json_bytes(payload, source=Path("<synthetic-grade-evidence>"))
    mapping = closed_mapping(
        value,
        fields=("success", "partial_reward", "infrastructure_failure"),
        field="grade evidence",
    )
    if type(mapping["success"]) is not int or mapping["success"] not in (0, 1):
        raise TypeError("grade evidence success must be exact int 0 or 1")
    if (
        type(mapping["partial_reward"]) is not float
        or not isfinite(cast(float, mapping["partial_reward"]))
    ):
        raise TypeError("grade evidence partial_reward must be finite exact float")
    if type(mapping["infrastructure_failure"]) is not bool:
        raise TypeError("grade evidence infrastructure_failure must be exact bool")
    return ()


def _decode_verifier_result_asset(
    _ref: ArtifactRef,
    payload: bytes,
    _value: object | None,
    _prevalidated_refs: frozenset[ArtifactRef],
) -> tuple[ArtifactRef, ...]:
    value = load_json_bytes(payload, source=Path("<synthetic-verifier-evidence>"))
    mapping = closed_mapping(
        value,
        fields=("finding_count",),
        field="verifier evidence",
    )
    if type(mapping["finding_count"]) is not int or mapping["finding_count"] < 0:
        raise TypeError(
            "verifier evidence finding_count must be nonnegative exact int"
        )
    return ()


_PROMOTED_AUTHORITY_ROLES = frozenset(
    {
        "tokenizer",
        "prompt_template",
        "tool_schema",
        "clock_source",
        "watchdog_source",
        "isolation_qualification",
        "deep_authority_asset",
    }
)

AUTHORITY_ASSET_DECODER_BY_ROLE: Mapping[
    str,
    AuthorityAssetDecoder,
] = MappingProxyType(
    {
        **{
            role: _decode_prevalidated_authority_asset
            for role in PRODUCTION_VALIDATED_AUTHORITY_ROLES
        },
        **{
            role: _decode_promoted_authority_asset
            for role in _PROMOTED_AUTHORITY_ROLES
        },
        "synthetic_execution_program": _decode_program_asset,
        "branch_program_registry": _decode_branch_program_registry_asset,
        "synthetic_request": _decode_request_asset,
        "synthetic_response": _decode_response_asset,
        "synthetic_provider_event": _decode_provider_event_asset,
        "synthetic_tool_result": _decode_tool_result_asset,
        "synthetic_grade_result": _decode_grade_result_asset,
        "synthetic_verifier_result": _decode_verifier_result_asset,
            "source_revision": _decode_source_revision,
            "power_authority": _decode_power_authority_asset,
            **{
                role: _decode_manifest_source_asset
                for role in (
                    "assignment_program",
                    "packet_policy",
                    "packet_template",
                    "pad_unit_set",
                    "power_grid",
                    "power_screen_topology",
                    "required_document_kinds",
                    "roster",
                    "storage_policy_contract",
                    "synthetic_verifier_source",
                    "synthetic_verifier_report",
                )
            },
        }
)

if set(AUTHORITY_ASSET_DECODER_BY_ROLE) != set(AUTHORITY_ASSET_ROLE_MEDIA):
    raise RuntimeError("authority asset decoder registry coverage drifted")


def _reconcile_reloaded_execution_records(
    *,
    authority: PrefixExecutionAuthority,
    program: SyntheticPrefixProgram,
    expected_cost_closure: (
        AttemptBoundZeroCostClosure | SyntheticZeroAttemptCostClosure
    ),
    expected_boundaries: tuple[CompletedToolBoundaryReceipt, ...],
    ledger: ProviderAttemptLedgerRecord,
    intents_by_ref: Mapping[ArtifactRef, ProviderDispatchIntent],
    attempts_by_ref: Mapping[ArtifactRef, ProviderCallAttemptReceipt],
    events_by_ref: Mapping[ArtifactRef, ControllerProviderEvent],
    settlements_by_ref: Mapping[ArtifactRef, ControllerProviderSettlement],
    cost_record: ControllerProviderCostClosure,
    tool_ledger: ToolBoundaryLedger,
    tool_calls_by_ref: Mapping[ArtifactRef, ToolCall],
) -> None:
    """Reconstruct exact execution semantics instead of accepting JSON shape."""

    if type(authority) is not PrefixExecutionAuthority:
        raise TypeError("authority must be exact PrefixExecutionAuthority")
    if type(program) is not SyntheticPrefixProgram:
        raise TypeError("program must be exact SyntheticPrefixProgram")
    if type(ledger) is not ProviderAttemptLedgerRecord:
        raise TypeError("ledger must be exact ProviderAttemptLedgerRecord")
    if type(cost_record) is not ControllerProviderCostClosure:
        raise TypeError("cost_record must be exact ControllerProviderCostClosure")
    if type(tool_ledger) is not ToolBoundaryLedger:
        raise TypeError("tool_ledger must be exact ToolBoundaryLedger")

    if type(expected_cost_closure) is AttemptBoundZeroCostClosure:
        expected_intents = expected_cost_closure.intents
        expected_intent_refs = expected_cost_closure.intent_refs
        expected_attempts = expected_cost_closure.attempts
        expected_attempt_refs = expected_cost_closure.attempt_refs
        expected_settlements = expected_cost_closure.settlements
    elif type(expected_cost_closure) is SyntheticZeroAttemptCostClosure:
        expected_intents = ()
        expected_intent_refs = ()
        expected_attempts = ()
        expected_attempt_refs = ()
        expected_settlements = ()
    else:
        raise TypeError("expected_cost_closure has an unavailable type")

    if (
        ledger.ledger.intents != expected_intents
        or ledger.ledger.intent_refs != expected_intent_refs
        or ledger.ledger.attempts != expected_attempts
        or ledger.attempt_refs != expected_attempt_refs
    ):
        raise ValueError("reloaded provider intent/attempt ledger differs")
    if dict(intents_by_ref) != dict(zip(expected_intent_refs, expected_intents)):
        raise ValueError("reloaded provider intent records differ")
    if dict(attempts_by_ref) != dict(zip(expected_attempt_refs, expected_attempts)):
        raise ValueError("reloaded provider attempt records differ")

    expected_event_refs = tuple(
        attempt.provider_event_ref for attempt in expected_attempts
    )
    expected_settlement_refs = tuple(
        settlement.settlement_ref for settlement in expected_settlements
    )
    if set(events_by_ref) != set(expected_event_refs):
        raise ValueError("reloaded provider event coverage differs")
    if set(settlements_by_ref) != set(expected_settlement_refs):
        raise ValueError("reloaded provider settlement coverage differs")
    if (
        cost_record.attempt_refs != expected_attempt_refs
        or cost_record.settlement_refs != expected_settlement_refs
        or cost_record.total_cost_microunits
        != expected_cost_closure.total_cost_microunits
    ):
        raise ValueError("reloaded provider cost closure differs")

    program_rows = {
        (row.subject_role, row.call_index): row for row in program.provider_transcript
    }
    if len(program_rows) != len(program.provider_transcript):
        raise ValueError("program provider identities are duplicated")
    clock_values = {read.label: read.uint64_ms for read in program.clock_trace}
    if len(clock_values) != len(program.clock_trace):
        raise ValueError("program clock labels are duplicated")
    for intent, intent_ref, attempt, attempt_ref, settlement in zip(
        expected_intents,
        expected_intent_refs,
        expected_attempts,
        expected_attempt_refs,
        expected_settlements,
        strict=True,
    ):
        row = program_rows.get((intent.subject_role, intent.call_index))
        if row is None:
            raise ValueError("provider intent has no exact program row")
        if (
            row.seed != intent.seed
            or row.model_contract_sha256 != intent.model_contract_ref.sha256
            or row.expected_request_ref.sha256 != intent.request_ref.sha256
            or hashlib.sha256(
                canonical_json_bytes(
                    {"token_ids": list(row.expected_input_token_ids)},
                    indent=None,
                )
            ).hexdigest()
            != intent.input_token_ids_ref.sha256
        ):
            raise ValueError("provider intent differs from sealed program row")
        expected_response_sha256 = (
            None if row.response_ref is None else row.response_ref.sha256
        )
        actual_response_sha256 = (
            None if attempt.response_ref is None else attempt.response_ref.sha256
        )
        if (
            attempt.dispatch_intent_ref != intent_ref
            or attempt.request_ref != intent.request_ref
            or attempt.input_token_ids_ref != intent.input_token_ids_ref
            or attempt.model_contract_ref != intent.model_contract_ref
            or attempt.subject_role != row.subject_role
            or attempt.call_index != row.call_index
            or attempt.seed != row.seed
            or attempt.status.value != row.completion_kind.value
            or attempt.generated_tokens != row.reported_generated_tokens
            or actual_response_sha256 != expected_response_sha256
        ):
            raise ValueError("provider attempt differs from intent/program edges")
        event = events_by_ref[attempt.provider_event_ref]
        after_label = f"after_{attempt.subject_role}_{attempt.call_index}"
        expected_observed_at = clock_values.get(after_label)
        if expected_observed_at is None:
            raise ValueError("provider event has no sealed completion clock")
        if (
            event.subject_role != attempt.subject_role
            or event.call_index != attempt.call_index
            or event.seed != attempt.seed
            or event.completion_kind is not attempt.status
            or event.dispatch_intent_sha256 != intent_ref.sha256
            or event.model_contract_sha256 != attempt.model_contract_ref.sha256
            or event.response_sha256 != actual_response_sha256
            or event.observed_at_ms != expected_observed_at
            or event.cost_microunits != 0
        ):
            raise ValueError("provider event differs from attempt/program edges")
        settlement_record = settlements_by_ref[settlement.settlement_ref]
        if (
            settlement.dispatch_intent_ref != intent_ref
            or settlement.attempt_receipt_ref != attempt_ref
            or settlement.provider_event_ref != attempt.provider_event_ref
            or settlement.cost_microunits != 0
            or settlement_record.subject_role != attempt.subject_role
            or settlement_record.call_index != attempt.call_index
            or settlement_record.seed != attempt.seed
            or settlement_record.dispatch_intent_sha256 != intent_ref.sha256
            or settlement_record.attempt_sha256 != attempt_ref.sha256
            or settlement_record.provider_event_sha256
            != attempt.provider_event_ref.sha256
            or settlement_record.cost_microunits != 0
        ):
            raise ValueError("provider settlement differs from attempt/event edges")

    if tool_ledger != ToolBoundaryLedger(expected_boundaries):
        raise ValueError("reloaded tool boundary ledger differs")
    expected_calls: dict[str, ToolCall] = {}
    for row in program.provider_transcript:
        if row.typed_turn is None:
            continue
        for call in row.typed_turn.tool_calls:
            if call.call_id in expected_calls:
                raise ValueError("program repeats a tool call ID")
            expected_calls[call.call_id] = call
    expected_tool_refs = {boundary.tool_call_ref for boundary in expected_boundaries}
    if set(tool_calls_by_ref) != expected_tool_refs:
        raise ValueError("reloaded tool call coverage differs")
    observations = {item.call_id: item for item in program.tool_observations}
    if len(observations) != len(program.tool_observations):
        raise ValueError("program repeats a tool observation ID")
    for boundary in expected_boundaries:
        if tool_calls_by_ref[boundary.tool_call_ref] != expected_calls.get(
            boundary.call_id
        ):
            raise ValueError("reloaded tool call differs from sealed program")
        observation = observations.get(boundary.call_id)
        if (
            observation is None
            or boundary.tool_result_ref.sha256 != observation.result_ref.sha256
            or boundary.mutation_committed != observation.mutation_committed
            or boundary.verifier_eligible_after != observation.verifier_eligible
            or boundary.episode_terminal != observation.episode_terminal
            or boundary.failure_kind is not observation.failure_kind
        ):
            raise ValueError("reloaded tool boundary differs from program result")


def _reconcile_reloaded_attestations(
    *,
    authority: PrefixExecutionAuthority,
    program: SyntheticPrefixProgram,
    program_bytes: bytes,
    subject: StatelessAttestation,
    simulator: StatelessAttestation | None,
    runtime: RuntimeAttestation,
    container: ContainerAttestation,
) -> None:
    """Bind every attestation field to executed authority and program bytes."""

    if type(authority) is not PrefixExecutionAuthority:
        raise TypeError("authority must be exact PrefixExecutionAuthority")
    if type(program) is not SyntheticPrefixProgram:
        raise TypeError("program must be exact SyntheticPrefixProgram")
    if type(program_bytes) is not bytes:
        raise TypeError("program_bytes must be exact bytes")
    if program_bytes != synthetic_prefix_program_bytes(program):
        raise ValueError("attestation program bytes differ from typed program")
    program_sha256 = hashlib.sha256(program_bytes).hexdigest()
    if (
        subject.record_kind != "synthetic_subject_stateless_v1"
        or subject.authority_ref != authority.subject_contract_ref
        or subject.program_sha256 != program_sha256
        or subject.stateless is not True
    ):
        raise ValueError("subject attestation differs from authority/program")
    if authority.simulator_contract_ref is None:
        if simulator is not None:
            raise ValueError("simulator-free authority forbids simulator attestation")
    elif (
        simulator is None
        or simulator.record_kind != "synthetic_simulator_stateless_v1"
        or simulator.authority_ref != authority.simulator_contract_ref
        or simulator.program_sha256 != program_sha256
        or simulator.stateless is not True
    ):
        raise ValueError("simulator attestation differs from authority/program")
    descriptors = _validate_descriptor_registry(authority)
    environment = descriptors["environment"]
    if (
        runtime.authority_ref != environment.implementation_source_ref
        or runtime.program_sha256 != program_sha256
        or runtime.runtime_id != environment.runtime_id
    ):
        raise ValueError("runtime attestation differs from authority/program")
    if (
        container.authority_ref != environment.implementation_source_ref
        or container.program_sha256 != program_sha256
        or container.container_digest != environment.container_digest
    ):
        raise ValueError("container attestation differs from authority/program")


def _reconcile_reloaded_authority_leaves(
    *,
    program: SyntheticPrefixProgram,
    requests: Mapping[ArtifactRef, SyntheticRequestPayload],
    responses: Mapping[ArtifactRef, tuple[ParserKind, SubjectTurn | None]],
    raw_events: Mapping[ArtifactRef, tuple[TransportKind, int]],
    tool_results: Mapping[ArtifactRef, SyntheticToolResultPayload],
    grade_results: Mapping[ArtifactRef, GradeEvidence],
    verifier_results: Mapping[ArtifactRef, VerifierEvidence],
) -> None:
    """Bind every traversed synthetic authority leaf to its program row."""

    expected_requests = {
        row.expected_request_ref for row in program.provider_transcript
    }
    expected_responses = {
        row.response_ref
        for row in program.provider_transcript
        if row.response_ref is not None
    }
    expected_events = {row.provider_event_ref for row in program.provider_transcript}
    expected_tool_results = {
        observation.result_ref for observation in program.tool_observations
    }
    if set(requests) != expected_requests:
        raise ValueError("synthetic request authority coverage differs")
    if set(responses) != expected_responses:
        raise ValueError("synthetic response authority coverage differs")
    if set(raw_events) != expected_events:
        raise ValueError("raw provider event authority coverage differs")
    if set(tool_results) != expected_tool_results:
        raise ValueError("synthetic tool-result authority coverage differs")
    if set(grade_results) != {program.grade_result.evidence_ref}:
        raise ValueError("synthetic grade authority coverage differs")
    if set(verifier_results) != {program.verifier_result.evidence_ref}:
        raise ValueError("synthetic verifier authority coverage differs")

    clock_values = {read.label: read.uint64_ms for read in program.clock_trace}
    for row in program.provider_transcript:
        request = requests[row.expected_request_ref]
        if request.subject_role != row.subject_role:
            raise ValueError("synthetic request actor differs from program")
        if row.response_ref is not None:
            parser_kind, turn = responses[row.response_ref]
            if turn != row.typed_turn:
                raise ValueError("synthetic response differs from program turn")
            if (
                (
                    row.completion_kind is RawProviderCompletionKind.COMPLETED
                    and parser_kind != "turn"
                )
                or (
                    row.completion_kind is RawProviderCompletionKind.REFUSAL
                    and parser_kind != "refusal"
                )
                or (
                    row.completion_kind is RawProviderCompletionKind.MALFORMED_RESPONSE
                    and parser_kind != "malformed"
                )
            ):
                raise ValueError("synthetic response parser kind differs from program")
        _, observed_at_ms = raw_events[row.provider_event_ref]
        if observed_at_ms != clock_values.get(
            f"after_{row.subject_role}_{row.call_index}"
        ):
            raise ValueError("raw provider event time differs from program clock")
    for observation in program.tool_observations:
        if tool_results[observation.result_ref].call_id != observation.call_id:
            raise ValueError("synthetic tool result differs from program observation")
    grade = grade_results[program.grade_result.evidence_ref]
    if (
        grade.success != program.grade_result.success
        or grade.partial_reward != program.grade_result.partial_reward
        or grade.infrastructure_failure
        is not program.grade_result.infrastructure_failure
    ):
        raise ValueError("synthetic grade result differs from program")
    verifier = verifier_results[program.verifier_result.evidence_ref]
    if verifier.finding_count != program.verifier_result.finding_count:
        raise ValueError("synthetic verifier result differs from program")


def _fresh_reload_candidate_graph(
    *,
    run_root: Path,
    candidate_ref: ArtifactRef,
    authority: PrefixExecutionAuthority,
    program: SyntheticPrefixProgram,
    program_bytes: bytes,
    expected_cost_closure: (
        AttemptBoundZeroCostClosure | SyntheticZeroAttemptCostClosure
    ),
    expected_boundaries: tuple[CompletedToolBoundaryReceipt, ...],
    expected_provider_attempts_ref: ArtifactRef,
    expected_boundary_ledger_ref: ArtifactRef,
    expected_provider_cost_ref: ArtifactRef,
    expected_controller_payloads: Mapping[ArtifactRef, bytes],
    allowed_prior_controller_refs: frozenset[ArtifactRef],
) -> None:
    root = Path(run_root).resolve(strict=True)
    visited: dict[ArtifactRef, str] = {}
    path_bindings: dict[str, ArtifactRef] = {}
    physical_bindings: dict[tuple[int, int], ArtifactRef] = {}
    pending = [candidate_ref]
    seen_expected: set[ArtifactRef] = set()
    intents_by_ref: dict[ArtifactRef, ProviderDispatchIntent] = {}
    attempts_by_ref: dict[ArtifactRef, ProviderCallAttemptReceipt] = {}
    events_by_ref: dict[ArtifactRef, ControllerProviderEvent] = {}
    settlements_by_ref: dict[ArtifactRef, ControllerProviderSettlement] = {}
    tool_calls_by_ref: dict[ArtifactRef, ToolCall] = {}
    ledgers: dict[ArtifactRef, ProviderAttemptLedgerRecord] = {}
    cost_records: dict[ArtifactRef, ControllerProviderCostClosure] = {}
    tool_ledgers: dict[ArtifactRef, ToolBoundaryLedger] = {}
    subject_attestations: list[StatelessAttestation] = []
    simulator_attestations: list[StatelessAttestation] = []
    runtime_attestations: list[RuntimeAttestation] = []
    container_attestations: list[ContainerAttestation] = []
    synthetic_requests: dict[ArtifactRef, SyntheticRequestPayload] = {}
    synthetic_responses: dict[
        ArtifactRef,
        tuple[ParserKind, SubjectTurn | None],
    ] = {}
    synthetic_raw_events: dict[ArtifactRef, tuple[TransportKind, int]] = {}
    synthetic_tool_results: dict[ArtifactRef, SyntheticToolResultPayload] = {}
    synthetic_programs: dict[ArtifactRef, SyntheticPrefixProgram] = {}
    synthetic_grade_payloads: dict[ArtifactRef, bytes] = {}
    synthetic_verifier_payloads: dict[ArtifactRef, bytes] = {}
    with (
        ControllerArtifactResolver(root) as resolver,
        AuthorityRefReader(root) as authority_reader,
        ScientificRefReader(root) as scientific_reader,
    ):
        fresh_authority = _load_prefix_execution_authority_with_reader(
            run_root=root,
            schedule_ref=authority.schedule_ref,
            task_id=authority.task_schedule.task.task_id,
            reader=authority_reader,
        )
        if fresh_authority != authority:
            raise ValueError("fresh schedule ancestry differs from executed authority")
        prevalidated_authority_refs = (
            authority_reader.semantically_validated_refs
        )
        while pending:
            ref = pending.pop()
            load_authority = REF_LOAD_CLASS_BY_ROLE.get(ref.role)
            if load_authority is None:
                raise ValueError(f"candidate graph has unknown role {ref.role!r}")
            load_class, expected = load_authority
            previous_class = visited.get(ref)
            if previous_class is not None:
                if previous_class != load_class:
                    raise ValueError("candidate ref crosses load classes")
                continue
            previous_path = path_bindings.get(ref.relative_path)
            if previous_path is not None and previous_path != ref:
                raise ValueError(
                    "candidate graph aliases one relative path: "
                    f"{previous_path!r} != {ref!r}"
                )
            relative = PurePosixPath(ref.relative_path)
            if (
                relative.is_absolute()
                or relative.as_posix() != ref.relative_path
                or any(part in ("", ".", "..") for part in relative.parts)
            ):
                raise ValueError("candidate graph has a noncanonical path")
            visited[ref] = load_class
            path_bindings[ref.relative_path] = ref
            if load_class == "controller_artifact":
                bound = resolver.resolve_bound(
                    ref,
                    expected_role=ref.role,
                    expected_media_type=expected,
                )
                payload = bound.payload
                physical = (bound.st_dev, bound.st_ino)
                retained_payload = expected_controller_payloads.get(ref)
                if retained_payload is not None:
                    if payload != retained_payload:
                        raise ValueError(
                            "fresh controller bytes differ from retained input bytes"
                        )
                    seen_expected.add(ref)
                elif ref not in allowed_prior_controller_refs:
                    raise ValueError(
                        "candidate graph contains an unexpected controller artifact"
                    )
                nested = _controller_nested_refs(ref.role, payload)
                if ref.role == "provider_dispatch_intent":
                    intents_by_ref[ref] = load_provider_dispatch_intent(payload)
                elif ref.role == "provider_attempt":
                    attempts_by_ref[ref] = load_provider_attempt(payload)
                elif ref.role == "provider_event":
                    events_by_ref[ref] = load_controller_provider_event(payload)
                elif ref.role == "provider_settlement":
                    settlements_by_ref[ref] = load_controller_provider_settlement(
                        payload
                    )
                elif ref.role == "provider_attempt_ledger":
                    ledgers[ref] = load_provider_attempt_ledger(payload)
                elif ref.role == "provider_cost_closure":
                    cost_records[ref] = load_controller_provider_cost_closure(payload)
                elif ref.role == "tool_boundary_ledger":
                    tool_ledgers[ref] = load_tool_boundary_ledger(payload)
                elif ref.role == "tool_call":
                    tool_calls_by_ref[ref] = load_tool_call(payload)
                elif ref.role == "subject_stateless_attestation":
                    subject_attestations.append(
                        load_stateless_attestation(
                            payload,
                            expected_role="primary_subject",
                        )
                    )
                elif ref.role == "simulator_stateless_attestation":
                    simulator_attestations.append(
                        load_stateless_attestation(
                            payload,
                            expected_role="user_simulator",
                        )
                    )
                elif ref.role == "runtime_attestation":
                    runtime_attestations.append(load_runtime_attestation(payload))
                elif ref.role == "container_attestation":
                    container_attestations.append(load_container_attestation(payload))
            elif load_class == "authority_asset":
                if ref.media_type != expected:
                    raise ValueError("authority asset media differs from registry")
                bound = authority_reader.read_bound(ref)
                payload = bound.payload
                physical = (bound.st_dev, bound.st_ino)
                value: object | None = None
                if ref.media_type == "application/json":
                    value = load_json_bytes(
                        payload,
                        source=root / ref.relative_path,
                    )
                    if payload != canonical_json_bytes(value, indent=None):
                        raise ValueError(
                            "authority asset must be compact canonical JSON"
                        )
                    _reject_malformed_ref_shapes(
                        value,
                        field=f"authority_asset[{ref.role}]",
                    )
                    if ref.role == "synthetic_execution_program":
                        synthetic_programs[ref] = load_synthetic_prefix_program(payload)
                    elif ref.role == "synthetic_request":
                        synthetic_requests[ref] = load_synthetic_request_payload(
                            payload
                        )
                    elif ref.role == "synthetic_response":
                        synthetic_responses[ref] = SyntheticResponseParser().parse(
                            payload
                        )
                    elif ref.role == "synthetic_provider_event":
                        synthetic_raw_events[ref] = _decode_raw_event(payload)
                    elif ref.role == "synthetic_tool_result":
                        synthetic_tool_results[ref] = (
                            load_synthetic_tool_result_payload(payload)
                        )
                    elif ref.role == "synthetic_grade_result":
                        synthetic_grade_payloads[ref] = payload
                    elif ref.role == "synthetic_verifier_result":
                        synthetic_verifier_payloads[ref] = payload
                try:
                    decoder = AUTHORITY_ASSET_DECODER_BY_ROLE[ref.role]
                except KeyError as exc:
                    raise ValueError(
                        f"authority asset has no decoder for {ref.role!r}"
                    ) from exc
                nested = decoder(
                    ref,
                    payload,
                    value,
                    prevalidated_authority_refs,
                )
            else:
                if ref.media_type != "application/json":
                    raise ValueError("scientific parent media must be application/json")
                bound = scientific_reader.read_bound(ref)
                physical = (bound.st_dev, bound.st_ino)
                record = decode_scientific_parent(
                    ref,
                    bound,
                    run_root=root,
                    field=ref.role,
                    expected_kind=expected,
                )
                # Schedule sealing already validates the complete power
                # ancestry.  Prefix replay binds the sealed final, but does
                # not reopen the power subsystem's separate contract
                # namespace during candidate graph reload.
                nested = () if ref.role == "power_report" else walk_artifact_refs(record.value)
            previous_physical = physical_bindings.get(physical)
            if previous_physical is not None and previous_physical != ref:
                raise ValueError(
                    "candidate graph aliases one physical file across refs"
                )
            physical_bindings[physical] = ref
            pending.extend(reversed(nested))
    missing_expected = set(expected_controller_payloads) - seen_expected
    if missing_expected:
        raise ValueError(
            "final controller store contains unreachable writes: "
            f"{sorted((ref.role, ref.sha256) for ref in missing_expected)!r}"
        )
    if set(ledgers) != {expected_provider_attempts_ref}:
        raise ValueError("candidate graph provider ledger identity differs")
    if set(cost_records) != {expected_provider_cost_ref}:
        raise ValueError("candidate graph cost closure identity differs")
    if set(tool_ledgers) != {expected_boundary_ledger_ref}:
        raise ValueError("candidate graph tool ledger identity differs")
    _reconcile_reloaded_execution_records(
        authority=authority,
        program=program,
        expected_cost_closure=expected_cost_closure,
        expected_boundaries=expected_boundaries,
        ledger=ledgers[expected_provider_attempts_ref],
        intents_by_ref=intents_by_ref,
        attempts_by_ref=attempts_by_ref,
        events_by_ref=events_by_ref,
        settlements_by_ref=settlements_by_ref,
        cost_record=cost_records[expected_provider_cost_ref],
        tool_ledger=tool_ledgers[expected_boundary_ledger_ref],
        tool_calls_by_ref=tool_calls_by_ref,
    )
    if synthetic_programs.get(authority.program_ref) != program:
        raise ValueError("fresh executed program differs from retained program")
    expected_request_refs = {
        row.expected_request_ref
        for candidate_program in synthetic_programs.values()
        for row in candidate_program.provider_transcript
    }
    expected_response_refs = {
        row.response_ref
        for candidate_program in synthetic_programs.values()
        for row in candidate_program.provider_transcript
        if row.response_ref is not None
    }
    expected_raw_event_refs = {
        row.provider_event_ref
        for candidate_program in synthetic_programs.values()
        for row in candidate_program.provider_transcript
    }
    expected_tool_result_refs = {
        observation.result_ref
        for candidate_program in synthetic_programs.values()
        for observation in candidate_program.tool_observations
    }
    grade_occurrences = tuple(
        (program_ref, candidate_program.grade_result.evidence_ref)
        for program_ref, candidate_program in synthetic_programs.items()
    )
    verifier_occurrences = tuple(
        (program_ref, candidate_program.verifier_result.evidence_ref)
        for program_ref, candidate_program in synthetic_programs.items()
    )
    expected_grade_refs = {ref for _program_ref, ref in grade_occurrences}
    expected_verifier_refs = {
        ref for _program_ref, ref in verifier_occurrences
    }
    for observed_refs, expected_refs, field in (
        (set(synthetic_requests), expected_request_refs, "request"),
        (set(synthetic_responses), expected_response_refs, "response"),
        (set(synthetic_raw_events), expected_raw_event_refs, "raw event"),
        (set(synthetic_tool_results), expected_tool_result_refs, "tool result"),
        (set(synthetic_grade_payloads), expected_grade_refs, "grade result"),
        (set(synthetic_verifier_payloads), expected_verifier_refs, "verifier result"),
    ):
        if observed_refs != expected_refs:
            raise ValueError(f"synthetic authority {field} coverage differs")
    for program_ref, grade_ref in grade_occurrences:
        candidate_program = synthetic_programs[program_ref]
        verifier_ref = candidate_program.verifier_result.evidence_ref
        _reconcile_reloaded_authority_leaves(
            program=candidate_program,
            requests={
                ref: synthetic_requests[ref]
                for ref in {
                    row.expected_request_ref
                    for row in candidate_program.provider_transcript
                }
            },
            responses={
                ref: synthetic_responses[ref]
                for ref in {
                    row.response_ref
                    for row in candidate_program.provider_transcript
                    if row.response_ref is not None
                }
            },
            raw_events={
                ref: synthetic_raw_events[ref]
                for ref in {
                    row.provider_event_ref
                    for row in candidate_program.provider_transcript
                }
            },
            tool_results={
                ref: synthetic_tool_results[ref]
                for ref in {
                    observation.result_ref
                    for observation in candidate_program.tool_observations
                }
            },
            grade_results={
                grade_ref: SyntheticGradeCodec().decode(
                    payload=synthetic_grade_payloads[grade_ref],
                    program=candidate_program,
                    expected_payload=synthetic_grade_payloads[grade_ref],
                )
            },
            verifier_results={
                verifier_ref: SyntheticVerifierCodec().decode(
                    payload=synthetic_verifier_payloads[verifier_ref],
                    program=candidate_program,
                    expected_payload=synthetic_verifier_payloads[verifier_ref],
                )
            },
        )
    if (
        len(subject_attestations) != 1
        or len(simulator_attestations)
        != (0 if authority.simulator_contract_ref is None else 1)
        or len(runtime_attestations) != 1
        or len(container_attestations) != 1
    ):
        raise ValueError("candidate graph attestation coverage differs")
    _reconcile_reloaded_attestations(
        authority=authority,
        program=program,
        program_bytes=program_bytes,
        subject=subject_attestations[0],
        simulator=(None if not simulator_attestations else simulator_attestations[0]),
        runtime=runtime_attestations[0],
        container=container_attestations[0],
    )


def _finalize_prefix_candidate(
    *,
    run_root: Path,
    authority: PrefixExecutionAuthority,
    opened: _PrefixLoopResult,
) -> ArtifactRef:
    if type(authority) is not PrefixExecutionAuthority:
        raise TypeError("authority must be exact PrefixExecutionAuthority")
    if type(opened) is not _PrefixLoopResult:
        raise TypeError("opened must be exact retained prefix result")
    if opened._authority != authority:
        raise ValueError("retained prefix authority differs")
    store = opened._store
    if store is None:
        raise RuntimeError("retained prefix store ownership is unavailable")
    candidate_ref: ArtifactRef | None = None
    store_relinquished = False
    try:
        live = opened.qualification._resources[0]
        fleet = opened.qualification._fleet
        if fleet is None:
            raise RuntimeError("retained environment fleet is unavailable")
        environment_snapshot = live.handle.snapshot()
        final_state = _decode_snapshot_state(environment_snapshot)
        if final_state != opened.final_observation:
            raise ValueError("live final snapshot drifted before freeze")
        visible = live.handle.visible_context()
        if visible != final_state.visible_context:
            raise ValueError("live visible context differs from final snapshot")
        token_ids = opened._components.tokenizer.encode(visible)
        environment_snapshot_ref = store.write(
            role="environment_snapshot",
            payload=environment_snapshot,
            media_type="application/octet-stream",
        )
        visible_ref = store.write(
            role="visible_context",
            payload=visible,
            media_type="application/json",
        )
        token_bytes = canonical_json_bytes(
            {"token_ids": list(token_ids)},
            indent=None,
        )
        token_ref = store.write(
            role="token_ids",
            payload=token_bytes,
            media_type="application/json",
        )
        program_sha256 = hashlib.sha256(opened._program_bytes).hexdigest()
        subject_attestation_ref = store.write(
            role="subject_stateless_attestation",
            payload=_attestation_bytes(
                kind="synthetic_subject_stateless_v1",
                authority_ref=authority.subject_contract_ref,
                program_sha256=program_sha256,
                values={"stateless": True},
            ),
            media_type="application/json",
        )
        simulator_attestation_ref = (
            None
            if authority.simulator_contract_ref is None
            else store.write(
                role="simulator_stateless_attestation",
                payload=_attestation_bytes(
                    kind="synthetic_simulator_stateless_v1",
                    authority_ref=authority.simulator_contract_ref,
                    program_sha256=program_sha256,
                    values={"stateless": True},
                ),
                media_type="application/json",
            )
        )
        descriptors = _validate_descriptor_registry(authority)
        environment_descriptor = descriptors["environment"]
        runtime_ref = store.write(
            role="runtime_attestation",
            payload=_attestation_bytes(
                kind="synthetic_runtime_attestation_v1",
                authority_ref=environment_descriptor.implementation_source_ref,
                program_sha256=program_sha256,
                values={"runtime_id": environment_descriptor.runtime_id},
            ),
            media_type="application/json",
        )
        container_ref = store.write(
            role="container_attestation",
            payload=_attestation_bytes(
                kind="synthetic_container_attestation_v1",
                authority_ref=environment_descriptor.implementation_source_ref,
                program_sha256=program_sha256,
                values={"container_digest": environment_descriptor.container_digest},
            ),
            media_type="application/json",
        )
        snapshot = CompositeSnapshotEnvelope(
            schema_version="0.1.0",
            study_ref=authority.manifest_ref,
            task_ref=opened.qualification.receipt.task_ref,
            schedule_ref=authority.schedule_ref,
            task_input_ref=authority.task_input_ref,
            environment_contract_ref=authority.environment_contract_ref,
            isolation_contract_ref=authority.isolation_contract_ref,
            initial_restore_qualification_ref=opened.qualification.receipt_ref,
            environment_snapshot_ref=environment_snapshot_ref,
            branch_pending_calls=opened.branch_pending_calls,
            terminal_unexecuted_remainder=opened.terminal_unexecuted_remainder,
            visible_context_ref=visible_ref,
            visible_sha256=visible_ref.sha256,
            token_ids_ref=token_ref,
            token_ids_sha256=token_ref.sha256,
            boundary_ledger_ref=opened.boundary_ledger_ref,
            provider_attempts_ref=opened.provider_attempts_ref,
            primary_counters=opened.primary_counters,
            simulator_counters=opened.simulator_counters,
            primary_remaining_quotas=_remaining_prefix_caps(
                authority.prefix_caps,
                opened.primary_counters,
            ),
            simulator_remaining_quotas=(
                None
                if authority.simulator_contract_caps is None
                else _remaining_call_caps(
                    authority.simulator_contract_caps,
                    opened.simulator_counters,
                    parsed_turns=opened.simulator_parsed_turns,
                )
            ),
            cumulative_mutation=opened.cumulative_mutation,
            episode_terminal=final_state.episode_terminal,
            terminal_failure_kind=opened.failure_kind,
            subject_stateless_attestation_ref=subject_attestation_ref,
            simulator_stateless_attestation_ref=simulator_attestation_ref,
            runtime_ref=runtime_ref,
            container_ref=container_ref,
            source_revision_ref=environment_descriptor.implementation_source_ref,
        )
        snapshot_bytes = composite_snapshot_bytes(snapshot)
        snapshot_ref = store.write(
            role="composite_snapshot",
            payload=snapshot_bytes,
            media_type="application/json",
        )
        grade_owned = fleet.spawn(2)
        grade_restore = _restore_exact_snapshot(
            owned=grade_owned,
            purpose="grade",
            environment_snapshot=environment_snapshot,
            expected_state=final_state,
            expected_visible=visible,
            expected_token_ids=token_ids,
            tokenizer=opened._components.tokenizer,
            authority=authority,
            task_ref=opened.qualification.receipt.task_ref,
            composite_snapshot_ref=snapshot_ref,
            environment_snapshot_ref=environment_snapshot_ref,
            visible_context_ref=visible_ref,
            token_ids_ref=token_ref,
        )
        grade_raw = grade_owned.handle.grade()
        grade_evidence = opened._components.grade_codec.decode(
            payload=grade_raw,
            program=opened._program,
            expected_payload=opened._payloads[
                opened._program.grade_result.evidence_ref
            ],
        )
        _assert_evidence_call_read_only(
            purpose="grade",
            handle=grade_owned.handle,
            environment_snapshot=environment_snapshot,
            expected_state=final_state,
        )
        grade_restore_ref = store.write(
            role="grade_restore_receipt",
            payload=snapshot_restore_receipt_bytes(grade_restore),
            media_type="application/json",
        )
        grade_evidence_ref = store.write(
            role="grade_evidence",
            payload=grade_raw,
            media_type="application/octet-stream",
        )
        grade_execution = GradeExecutionReceipt(
            grade_restore_ref,
            grade_evidence_ref,
        )
        grade_execution_ref = store.write(
            role="grade_evidence_receipt",
            payload=grade_execution_receipt_bytes(grade_execution),
            media_type="application/json",
        )
        verifier_owned = fleet.spawn(3)
        verifier_restore = _restore_exact_snapshot(
            owned=verifier_owned,
            purpose="verify",
            environment_snapshot=environment_snapshot,
            expected_state=final_state,
            expected_visible=visible,
            expected_token_ids=token_ids,
            tokenizer=opened._components.tokenizer,
            authority=authority,
            task_ref=opened.qualification.receipt.task_ref,
            composite_snapshot_ref=snapshot_ref,
            environment_snapshot_ref=environment_snapshot_ref,
            visible_context_ref=visible_ref,
            token_ids_ref=token_ref,
        )
        verifier_raw = verifier_owned.handle.verify()
        verifier_evidence = opened._components.verifier_codec.decode(
            payload=verifier_raw,
            program=opened._program,
            expected_payload=opened._payloads[
                opened._program.verifier_result.evidence_ref
            ],
        )
        _assert_evidence_call_read_only(
            purpose="verify",
            handle=verifier_owned.handle,
            environment_snapshot=environment_snapshot,
            expected_state=final_state,
        )
        verifier_restore_ref = store.write(
            role="verifier_restore_receipt",
            payload=snapshot_restore_receipt_bytes(verifier_restore),
            media_type="application/json",
        )
        verifier_evidence_ref = store.write(
            role="verifier_evidence",
            payload=verifier_raw,
            media_type="application/octet-stream",
        )
        verifier_execution = VerifierExecutionReceipt(
            verifier_restore_ref,
            verifier_evidence_ref,
        )
        verifier_execution_ref = store.write(
            role="verifier_evidence_receipt",
            payload=verifier_execution_receipt_bytes(verifier_execution),
            media_type="application/json",
        )
        verifier_components = [
            {"kind": "fixture", "value": "verifier", "count": 1}
        ]
        verifier_source_ref = store.write(
            role="verifier_source",
            payload=canonical_json_bytes(
                {
                    "record_kind": "synthetic_verifier_source_v1",
                    "schema_version": "1",
                    "task_id": authority.task_schedule.task.task_id,
                    "benchmark": authority.task_schedule.task.benchmark,
                    "components": verifier_components,
                    "objective_findings": [],
                },
                indent=None,
            ),
            media_type="application/json",
        )
        verifier_report_ref = store.write(
            role="verifier_report",
            payload=canonical_json_bytes(
                {
                    "record_kind": "synthetic_verifier_report_v1",
                    "schema_version": "1",
                    "task_id": authority.task_schedule.task.task_id,
                    "report_text": "",
                },
                indent=None,
            ),
            media_type="application/json",
        )
        verifier_feature_ref = store.write(
            role="verifier_feature",
            payload=canonical_json_bytes(
                {
                    "record_kind": "assignment_verifier_features_v1",
                    "schema_version": "1",
                    "task_id": authority.task_schedule.task.task_id,
                    "benchmark": authority.task_schedule.task.benchmark,
                    "source_verifier_ref": asdict(verifier_source_ref),
                    "source_report_ref": asdict(verifier_report_ref),
                    "components": verifier_components,
                    "objective_finding_count": 0,
                    "normalized_report_token_count": 0,
                },
                indent=None,
            ),
            media_type="application/json",
        )
        _assert_pairwise_isolated(tuple(fleet.instances))
        y0_grade = _scientific_y0_grade(
            trigger_reason=opened.trigger_reason,
            failure_kind=opened.failure_kind,
            evidence=grade_evidence,
            evidence_ref=grade_evidence_ref,
        )
        verifier_receipt = FrozenVerifierReceipt(
            task_id=authority.task_schedule.task.task_id,
            schedule_sha256=authority.schedule_ref.sha256,
            snapshot_ref=snapshot_ref,
            verifier_artifact_ref=verifier_evidence_ref,
            verifier_features_ref=verifier_feature_ref,
            finding_count=verifier_evidence.finding_count,
        )
        call_seeds = tuple(
            CallSeedReceipt(intent.subject_role, intent.call_index, intent.seed)
            for intent in opened.intents
        )
        receipt = FrozenPrefixReceipt(
            task_id=authority.task_schedule.task.task_id,
            schedule_sha256=authority.schedule_ref.sha256,
            prefix_caps=authority.prefix_caps,
            snapshot_ref=snapshot_ref,
            visible_context_ref=visible_ref,
            visible_sha256=visible_ref.sha256,
            token_ids_ref=token_ref,
            token_ids_sha256=token_ref.sha256,
            branch_pending_calls=opened.branch_pending_calls,
            terminal_unexecuted_remainder=opened.terminal_unexecuted_remainder,
            trigger_reason=opened.trigger_reason,
            terminal_failure_kind=opened.failure_kind,
            y0_grade=y0_grade,
            grade_execution_receipt_ref=grade_execution_ref,
            verifier_receipt=verifier_receipt,
            verifier_execution_receipt_ref=verifier_execution_ref,
            counters=opened.primary_counters,
            simulator_counters=opened.simulator_counters,
            call_seeds=call_seeds,
            provider_attempts_ref=opened.provider_attempts_ref,
            boundary_ledger_ref=opened.boundary_ledger_ref,
            provider_cost_ref=opened.provider_cost_ref,
        )
        validate_snapshot_receipt_fields(
            snapshot,
            snapshot_ref=snapshot_ref,
            snapshot_bytes=snapshot_bytes,
            visible_context_ref=visible_ref,
            visible_sha256=visible_ref.sha256,
            token_ids_ref=token_ref,
            token_ids_sha256=token_ref.sha256,
            branch_pending_calls=opened.branch_pending_calls,
            terminal_unexecuted_remainder=opened.terminal_unexecuted_remainder,
            boundary_ledger_ref=opened.boundary_ledger_ref,
            provider_attempts_ref=opened.provider_attempts_ref,
            primary_counters=opened.primary_counters,
            simulator_counters=opened.simulator_counters,
            terminal_failure_kind=opened.failure_kind,
        )
        candidate_ref = store.write(
            role="prefix_candidate_receipt",
            payload=prefix_candidate_receipt_bytes(receipt),
            media_type="application/json",
        )
        expected_controller_payloads = store.snapshot_writes()
        qualification_receipt = opened.qualification.receipt
        allowed_prior_controller_refs = frozenset(
            {
                opened.qualification.receipt_ref,
                qualification_receipt.task_ref,
                qualification_receipt.initial_environment_snapshot_ref,
                qualification_receipt.visible_context_ref,
                qualification_receipt.token_ids_ref,
            }
        )
        opened._store = None
        store_relinquished = True
        store.close()
        _fresh_reload_candidate_graph(
            run_root=run_root,
            candidate_ref=candidate_ref,
            authority=authority,
            program=opened._program,
            program_bytes=opened._program_bytes,
            expected_cost_closure=opened.cost_closure,
            expected_boundaries=opened.boundaries,
            expected_provider_attempts_ref=opened.provider_attempts_ref,
            expected_boundary_ledger_ref=opened.boundary_ledger_ref,
            expected_provider_cost_ref=opened.provider_cost_ref,
            expected_controller_payloads=expected_controller_payloads,
            allowed_prior_controller_refs=allowed_prior_controller_refs,
        )
        _assert_pairwise_isolated(tuple(fleet.instances))
        opened.close()
        return candidate_ref
    except BaseException as primary:
        errors: list[BaseException] = [primary]
        if not store_relinquished:
            opened._store = None
            try:
                store.close()
            except BaseException as exc:
                errors.append(exc)
        try:
            opened.close()
        except BaseException as exc:
            errors.append(exc)
        raise BaseExceptionGroup(
            "prefix candidate transaction failed", errors
        ) from None


def run_prefix(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    task_id: str,
) -> ArtifactRef:
    """Construct one synthetic candidate; no branch or publication occurs."""

    authority = load_prefix_execution_authority(
        run_root=run_root,
        schedule_ref=schedule_ref,
        task_id=task_id,
    )
    opened = _open_prefix_loop(
        run_root=run_root,
        authority=authority,
    )
    return _finalize_prefix_candidate(
        run_root=run_root,
        authority=authority,
        opened=opened,
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


__all__ = ["run_prefix"]
