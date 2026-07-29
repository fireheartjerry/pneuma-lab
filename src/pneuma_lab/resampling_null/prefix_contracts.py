"""Closed T5-S02C contract, provenance, and loader-role primitives.

This module deliberately contains no prefix execution, provider dispatch,
environment process, grading, verification, or publication behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from enum import Enum
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Literal, cast, final

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .authority_refs import decode_artifact_ref, load_json_bytes
from .types import (
    ArtifactRef,
    FailureKind,
    SubjectTurn,
    ToolCall,
    TriggerReason,
)


CONTROLLER_ROLE_MEDIA: dict[str, str] = {
    "selected_task": "application/json",
    "initial_restore_qualification": "application/json",
    "composite_snapshot": "application/json",
    "environment_snapshot": "application/octet-stream",
    "visible_context": "application/json",
    "token_ids": "application/json",
    "input_token_ids": "application/json",
    "output_token_ids": "application/json",
    "provider_request": "application/json",
    "provider_dispatch_intent": "application/json",
    "provider_response": "application/octet-stream",
    "provider_event": "application/json",
    "provider_attempt": "application/json",
    "provider_attempt_ledger": "application/json",
    "provider_settlement": "application/json",
    "provider_cost_closure": "application/json",
    "tool_call": "application/json",
    "tool_result": "application/octet-stream",
    "tool_boundary_ledger": "application/json",
    "subject_stateless_attestation": "application/json",
    "simulator_stateless_attestation": "application/json",
    "runtime_attestation": "application/json",
    "container_attestation": "application/json",
    "grade_restore_receipt": "application/json",
    "verifier_restore_receipt": "application/json",
    "grade_evidence": "application/octet-stream",
    "verifier_evidence": "application/octet-stream",
    "grade_evidence_receipt": "application/json",
    "verifier_evidence_receipt": "application/json",
    "prefix_candidate_receipt": "application/json",
}

AUTHORITY_ASSET_ROLE_MEDIA: dict[str, str] = {
    "task_registry": "application/json",
    "provider_lane_plan": "application/json",
    "task_input": "application/json",
    "environment_contract": "application/json",
    "grader_contract": "application/json",
    "verifier_contract": "application/json",
    "isolation_contract": "application/json",
    "subject_contract": "application/json",
    "simulator_contract": "application/json",
    "tool_parser_contract": "application/json",
    "meter_contract": "application/json",
    "tokenizer": "application/json",
    "prompt_template": "application/json",
    "tool_schema": "application/json",
    "synthetic_execution_program": "application/json",
    "synthetic_request": "application/json",
    "synthetic_response": "application/json",
    "synthetic_provider_event": "application/json",
    "synthetic_tool_result": "application/json",
    "synthetic_grade_result": "application/json",
    "synthetic_verifier_result": "application/json",
    "clock_source": "application/json",
    "watchdog_source": "application/json",
    "isolation_qualification": "application/json",
    "source_revision": "application/octet-stream",
    "deep_authority_asset": "application/json",
}

SCIENTIFIC_PARENT_KIND: dict[str, str] = {
    "resampling_prefix_schedule": "resampling_prefix_schedule",
    "study_manifest": "resampling_study_manifest",
}

RefLoadClass = Literal[
    "scientific_parent",
    "controller_artifact",
    "authority_asset",
]

REF_LOAD_CLASS_BY_ROLE: dict[str, tuple[RefLoadClass, str]] = {
    **{
        role: ("scientific_parent", kind)
        for role, kind in SCIENTIFIC_PARENT_KIND.items()
    },
    **{
        role: ("controller_artifact", media)
        for role, media in CONTROLLER_ROLE_MEDIA.items()
    },
    **{
        role: ("authority_asset", media)
        for role, media in AUTHORITY_ASSET_ROLE_MEDIA.items()
    },
}

_S02C_CONTROLLER_ROLES = frozenset(
    {
        "initial_restore_qualification",
        "grade_restore_receipt",
        "verifier_restore_receipt",
        "prefix_candidate_receipt",
        "provider_request",
        "provider_response",
        "provider_event",
        "provider_settlement",
        "environment_snapshot",
        "grade_evidence",
        "verifier_evidence",
    }
)


def _validate_role_registries() -> None:
    controller = set(CONTROLLER_ROLE_MEDIA)
    authority = set(AUTHORITY_ASSET_ROLE_MEDIA)
    scientific = set(SCIENTIFIC_PARENT_KIND)
    if controller & authority or controller & scientific or authority & scientific:
        raise RuntimeError("reference load-class role registries overlap")
    if not _S02C_CONTROLLER_ROLES <= controller:
        raise RuntimeError("controller role registry omits a required S02C role")
    for registry in (CONTROLLER_ROLE_MEDIA, AUTHORITY_ASSET_ROLE_MEDIA):
        if any(
            type(role) is not str
            or not role
            or type(media) is not str
            or media != media.lower()
            or ";" in media
            or media.count("/") != 1
            for role, media in registry.items()
        ):
            raise RuntimeError("role/media registry contains noncanonical authority")
    expected = controller | authority | scientific
    if set(REF_LOAD_CLASS_BY_ROLE) != expected:
        raise RuntimeError("reference load-class registry coverage drifted")


_validate_role_registries()


def _exact_text(value: object, field: str) -> str:
    if type(value) is not str or not value:
        raise TypeError(f"{field} must be non-empty exact text")
    return cast(str, value)


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _exact_text(value, field)


def _nonnegative_int(value: object, field: str, *, positive: bool = False) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an exact int")
    integer = cast(int, value)
    if integer < (1 if positive else 0):
        raise ValueError(f"{field} is outside its allowed range")
    return integer


def _digest(value: object, field: str) -> str:
    text = _exact_text(value, field)
    if len(text) != 64 or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _exact_ref(
    value: object,
    field: str,
    *,
    role: str,
    registry: Mapping[str, str] = AUTHORITY_ASSET_ROLE_MEDIA,
) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise TypeError(f"{field} must be an exact ArtifactRef")
    ref = cast(ArtifactRef, value)
    expected_media = registry.get(role)
    if expected_media is None:
        raise RuntimeError(f"unregistered role in contract: {role}")
    if ref.role != role or ref.media_type != expected_media:
        raise ValueError(f"{field} must bind canonical {role!r} authority")
    return ref


def _exact_tuple(
    value: object, field: str, member_type: type[object]
) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    items = cast(tuple[object, ...], value)
    if not all(type(item) is member_type for item in items):
        raise TypeError(f"{field} contains a non-exact {member_type.__name__}")
    return items


ImplementationPurpose = Literal[
    "environment",
    "subject",
    "simulator",
    "meter",
    "tokenizer",
    "request_renderer",
    "response_parser",
    "grader",
    "verifier",
    "provider_event_codec",
    "settlement_codec",
]

_IMPLEMENTATION_PURPOSES = frozenset(
    {
        "environment",
        "subject",
        "simulator",
        "meter",
        "tokenizer",
        "request_renderer",
        "response_parser",
        "grader",
        "verifier",
        "provider_event_codec",
        "settlement_codec",
    }
)


@dataclass(frozen=True, slots=True)
class ImplementationDescriptor:
    purpose: ImplementationPurpose
    nominal_type: str
    build_id: str
    request_grammar: str | None
    response_grammar: str | None
    snapshot_grammar: str | None
    restore_grammar: str | None
    evidence_grammar: str | None
    runtime_id: str | None
    container_digest: str | None
    implementation_source_ref: ArtifactRef

    def __post_init__(self) -> None:
        if (
            type(self.purpose) is not str
            or self.purpose not in _IMPLEMENTATION_PURPOSES
        ):
            raise ValueError("purpose is not a registered implementation purpose")
        _exact_text(self.nominal_type, "nominal_type")
        _exact_text(self.build_id, "build_id")
        for name in (
            "request_grammar",
            "response_grammar",
            "snapshot_grammar",
            "restore_grammar",
            "evidence_grammar",
            "runtime_id",
            "container_digest",
        ):
            _optional_text(getattr(self, name), name)
        _exact_ref(
            self.implementation_source_ref,
            "implementation_source_ref",
            role="source_revision",
        )
        required: dict[str, tuple[str, ...]] = {
            "environment": (
                "snapshot_grammar",
                "restore_grammar",
                "evidence_grammar",
                "runtime_id",
                "container_digest",
            ),
            "subject": ("request_grammar", "response_grammar"),
            "simulator": ("request_grammar", "response_grammar"),
            "meter": ("evidence_grammar",),
            "request_renderer": ("request_grammar",),
            "response_parser": ("response_grammar",),
            "grader": ("evidence_grammar", "runtime_id", "container_digest"),
            "verifier": ("evidence_grammar", "runtime_id", "container_digest"),
            "provider_event_codec": ("evidence_grammar",),
            "settlement_codec": ("evidence_grammar",),
            "tokenizer": (),
        }
        allowed = set(required[cast(str, self.purpose)])
        grammar_fields = {
            "request_grammar",
            "response_grammar",
            "snapshot_grammar",
            "restore_grammar",
            "evidence_grammar",
            "runtime_id",
            "container_digest",
        }
        if any(getattr(self, name) is None for name in allowed):
            raise ValueError("descriptor omits a purpose-required field")
        if any(getattr(self, name) is not None for name in grammar_fields - allowed):
            raise ValueError("descriptor sets a field inapplicable to its purpose")


@dataclass(frozen=True, slots=True)
class EnvironmentProcessIdentity:
    instance_ordinal: int
    writable_root_relative_path: str
    writable_root_st_dev: int
    writable_root_st_ino: int
    child_pid: int

    def __post_init__(self) -> None:
        _nonnegative_int(self.instance_ordinal, "instance_ordinal")
        path = PurePosixPath(
            _exact_text(
                self.writable_root_relative_path,
                "writable_root_relative_path",
            )
        )
        if (
            path.is_absolute()
            or path.as_posix() != self.writable_root_relative_path
            or any(part in ("", ".", "..") for part in path.parts)
        ):
            raise ValueError("writable root path must be normalized and relative")
        _nonnegative_int(self.writable_root_st_dev, "writable_root_st_dev")
        _nonnegative_int(self.writable_root_st_ino, "writable_root_st_ino")
        _nonnegative_int(self.child_pid, "child_pid", positive=True)


class RawProviderCompletionKind(str, Enum):
    COMPLETED = "completed"
    TIMEOUT_NO_RESPONSE = "timeout_no_response"
    TIMEOUT_LATE_RESPONSE = "timeout_late_response"
    REFUSAL = "refusal"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_ERROR = "provider_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


class ProviderTransportKind(str, Enum):
    RESPONSE = "response"
    PROVIDER_ERROR = "provider_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    TIMEOUT_NO_RESPONSE = "timeout_no_response"


class ParserOutcome(str, Enum):
    TURN = "turn"
    REFUSAL = "refusal"
    MALFORMED = "malformed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class RawProviderObservation:
    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int
    model_contract_sha256: str
    response_bytes: bytes | None
    typed_turn: SubjectTurn | None
    reported_output_token_ids: tuple[int, ...] | None
    reported_generated_tokens: int
    provider_event_bytes: bytes
    completion_kind: RawProviderCompletionKind

    def __post_init__(self) -> None:
        if type(self.subject_role) is not str or self.subject_role not in (
            "primary_subject",
            "user_simulator",
        ):
            raise ValueError("subject_role is not registered")
        _nonnegative_int(self.call_index, "call_index")
        _nonnegative_int(self.seed, "seed")
        _digest(self.model_contract_sha256, "model_contract_sha256")
        if self.response_bytes is not None and type(self.response_bytes) is not bytes:
            raise TypeError("response_bytes must be exact bytes or None")
        if self.typed_turn is not None and type(self.typed_turn) is not SubjectTurn:
            raise TypeError("typed_turn must be exact SubjectTurn or None")
        if self.reported_output_token_ids is not None:
            ids = _exact_tuple(
                self.reported_output_token_ids,
                "reported_output_token_ids",
                int,
            )
            for index, token in enumerate(ids):
                _nonnegative_int(token, f"reported_output_token_ids[{index}]")
        _nonnegative_int(self.reported_generated_tokens, "reported_generated_tokens")
        if type(self.provider_event_bytes) is not bytes:
            raise TypeError("provider_event_bytes must be exact bytes")
        if type(self.completion_kind) is not RawProviderCompletionKind:
            raise TypeError("completion_kind must be exact RawProviderCompletionKind")
        response_present = self.response_bytes is not None
        if response_present != (self.reported_output_token_ids is not None):
            raise ValueError(
                "response and output-token evidence must be jointly present"
            )
        if not response_present and (
            self.typed_turn is not None or self.reported_generated_tokens != 0
        ):
            raise ValueError("response-less observation cannot contain turn or tokens")


@dataclass(frozen=True, slots=True)
class SyntheticProviderTranscriptRow:
    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int
    model_contract_sha256: str
    expected_request_ref: ArtifactRef
    expected_request_sha256: str
    expected_input_token_ids: tuple[int, ...]
    response_ref: ArtifactRef | None
    typed_turn: SubjectTurn | None
    reported_output_token_ids: tuple[int, ...] | None
    reported_generated_tokens: int
    provider_event_ref: ArtifactRef
    completion_kind: RawProviderCompletionKind
    transport_kind: ProviderTransportKind
    parser_outcome: ParserOutcome

    def __post_init__(self) -> None:
        if type(self.subject_role) is not str or self.subject_role not in (
            "primary_subject",
            "user_simulator",
        ):
            raise ValueError("provider transcript role is not registered")
        _nonnegative_int(self.call_index, "call_index")
        _nonnegative_int(self.seed, "seed")
        _digest(self.model_contract_sha256, "model_contract_sha256")
        _exact_ref(
            self.expected_request_ref,
            "expected_request_ref",
            role="synthetic_request",
        )
        if _digest(self.expected_request_sha256, "expected_request_sha256") != (
            self.expected_request_ref.sha256
        ):
            raise ValueError("expected request digest differs from its ref")
        token_ids = _exact_tuple(
            self.expected_input_token_ids,
            "expected_input_token_ids",
            int,
        )
        for token in token_ids:
            _nonnegative_int(token, "expected_input_token_ids item")
        if self.response_ref is not None:
            _exact_ref(self.response_ref, "response_ref", role="synthetic_response")
        if self.typed_turn is not None and type(self.typed_turn) is not SubjectTurn:
            raise TypeError("typed_turn must be exact SubjectTurn or None")
        if self.reported_output_token_ids is not None:
            output_ids = _exact_tuple(
                self.reported_output_token_ids,
                "reported_output_token_ids",
                int,
            )
            for token in output_ids:
                _nonnegative_int(token, "reported_output_token_ids item")
        _nonnegative_int(self.reported_generated_tokens, "reported_generated_tokens")
        _exact_ref(
            self.provider_event_ref,
            "provider_event_ref",
            role="synthetic_provider_event",
        )
        for name, enum_type in (
            ("completion_kind", RawProviderCompletionKind),
            ("transport_kind", ProviderTransportKind),
            ("parser_outcome", ParserOutcome),
        ):
            if type(getattr(self, name)) is not enum_type:
                raise TypeError(f"{name} must be exact {enum_type.__name__}")
        response_present = self.response_ref is not None
        if response_present != (self.reported_output_token_ids is not None):
            raise ValueError("response and output tokens must be jointly present")
        if not response_present and (
            self.typed_turn is not None
            or self.reported_generated_tokens != 0
            or self.parser_outcome is not ParserOutcome.NOT_APPLICABLE
        ):
            raise ValueError("response-less transcript row contains response state")
        if self.parser_outcome in (ParserOutcome.TURN, ParserOutcome.REFUSAL):
            if self.typed_turn is None:
                raise ValueError("parsed turn/refusal requires an exact typed turn")
        elif self.typed_turn is not None:
            raise ValueError("non-turn parser outcome cannot contain typed turn")
        if (
            self.subject_role == "user_simulator"
            and self.typed_turn is not None
            and self.typed_turn.tool_calls
        ):
            raise ValueError("simulator transcript turns cannot issue tools")


@dataclass(frozen=True, slots=True)
class SyntheticToolObservation:
    call_id: str
    result_ref: ArtifactRef
    mutation_committed: bool
    verifier_eligible: bool
    episode_terminal: bool
    failure_kind: FailureKind

    def __post_init__(self) -> None:
        _exact_text(self.call_id, "call_id")
        _exact_ref(self.result_ref, "result_ref", role="synthetic_tool_result")
        for name in ("mutation_committed", "verifier_eligible", "episode_terminal"):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be exact bool")
        if type(self.failure_kind) is not FailureKind:
            raise TypeError("failure_kind must be exact FailureKind")
        if self.failure_kind is not FailureKind.NONE and not self.episode_terminal:
            raise ValueError("injected tool failure must be terminal")


@dataclass(frozen=True, slots=True)
class SyntheticGradeResult:
    evidence_ref: ArtifactRef
    success: int
    partial_reward: float
    infrastructure_failure: bool

    def __post_init__(self) -> None:
        _exact_ref(self.evidence_ref, "evidence_ref", role="synthetic_grade_result")
        if type(self.success) is not int or self.success not in (0, 1):
            raise ValueError("success must be exact 0 or 1")
        if type(self.partial_reward) is not float:
            raise TypeError("partial_reward must be an exact finite float")
        if self.partial_reward != self.partial_reward or abs(
            self.partial_reward
        ) == float("inf"):
            raise ValueError("partial_reward must be finite")
        if type(self.infrastructure_failure) is not bool:
            raise TypeError("infrastructure_failure must be exact bool")
        if self.infrastructure_failure and self.success:
            raise ValueError("infrastructure failure cannot report success")


@dataclass(frozen=True, slots=True)
class SyntheticVerifierResult:
    evidence_ref: ArtifactRef
    finding_count: int

    def __post_init__(self) -> None:
        _exact_ref(
            self.evidence_ref,
            "evidence_ref",
            role="synthetic_verifier_result",
        )
        _nonnegative_int(self.finding_count, "finding_count")


@dataclass(frozen=True, slots=True)
class SyntheticFailureInjection:
    stage: Literal[
        "none",
        "provider_transport",
        "provider_parser",
        "tool",
    ]

    def __post_init__(self) -> None:
        if type(self.stage) is not str or self.stage not in (
            "none",
            "provider_transport",
            "provider_parser",
            "tool",
        ):
            raise ValueError("failure injection stage is not registered")


@dataclass(frozen=True, slots=True)
class SyntheticClockRead:
    label: str
    uint64_ms: int

    def __post_init__(self) -> None:
        _exact_text(self.label, "label")
        value = _nonnegative_int(self.uint64_ms, "uint64_ms")
        if value >= 2**64:
            raise ValueError("uint64_ms must fit uint64")


@dataclass(frozen=True, slots=True)
class SyntheticPrefixProgram:
    record_kind: Literal["synthetic_prefix_program_v1"]
    schema_version: Literal["1"]
    task_id: str
    expected_trigger_reason: TriggerReason
    tool_schema_ref: ArtifactRef
    provider_transcript: tuple[SyntheticProviderTranscriptRow, ...]
    tool_observations: tuple[SyntheticToolObservation, ...]
    grade_result: SyntheticGradeResult
    verifier_result: SyntheticVerifierResult
    failure_injection: SyntheticFailureInjection
    clock_trace: tuple[SyntheticClockRead, ...]

    def __post_init__(self) -> None:
        if self.record_kind != "synthetic_prefix_program_v1":
            raise ValueError("program record_kind is wrong")
        if self.schema_version != "1":
            raise ValueError("program schema_version is wrong")
        _exact_text(self.task_id, "task_id")
        if type(self.expected_trigger_reason) is not TriggerReason:
            raise TypeError("expected trigger must be exact TriggerReason")
        _exact_ref(self.tool_schema_ref, "tool_schema_ref", role="tool_schema")
        _exact_tuple(
            self.provider_transcript,
            "provider_transcript",
            SyntheticProviderTranscriptRow,
        )
        _exact_tuple(
            self.tool_observations,
            "tool_observations",
            SyntheticToolObservation,
        )
        if type(self.grade_result) is not SyntheticGradeResult:
            raise TypeError("grade_result must be exact SyntheticGradeResult")
        if type(self.verifier_result) is not SyntheticVerifierResult:
            raise TypeError("verifier_result must be exact SyntheticVerifierResult")
        if type(self.failure_injection) is not SyntheticFailureInjection:
            raise TypeError("failure_injection must be exact SyntheticFailureInjection")
        reads = _exact_tuple(self.clock_trace, "clock_trace", SyntheticClockRead)
        labels = [cast(SyntheticClockRead, item).label for item in reads]
        if len(labels) != len(set(labels)):
            raise ValueError("clock trace labels must be unique")
        values = [cast(SyntheticClockRead, item).uint64_ms for item in reads]
        if values != sorted(values):
            raise ValueError("clock trace must be monotonic")
        next_index = {"primary_subject": 0, "user_simulator": 0}
        for row in self.provider_transcript:
            if row.call_index != next_index[row.subject_role]:
                raise ValueError(
                    "provider transcript role-local indexes must be consecutive"
                )
            next_index[row.subject_role] += 1
        call_ids = [item.call_id for item in self.tool_observations]
        if len(call_ids) != len(set(call_ids)):
            raise ValueError("tool observations must not repeat call_id")


def _closed(value: object, names: tuple[str, ...], field: str) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != set(names):
        raise ValueError(f"{field} has an open or incomplete shape")
    return dict(value)


def _decode_ref(value: object, field: str, role: str) -> ArtifactRef:
    ref = decode_artifact_ref(value, field=field, expected_role=role)
    _exact_ref(ref, field, role=role)
    return ref


def _decode_subject_turn(value: object, field: str) -> SubjectTurn:
    item = _closed(
        value,
        ("text", "tool_calls", "generated_tokens", "finish_reason"),
        field,
    )
    calls_value = item["tool_calls"]
    if type(calls_value) is not list:
        raise TypeError(f"{field}.tool_calls must be an exact array")
    calls = tuple(
        ToolCall(
            call_id=cast(
                str,
                _closed(
                    call,
                    ("call_id", "name", "canonical_arguments_json"),
                    f"{field}.tool_calls[{index}]",
                )["call_id"],
            ),
            name=cast(
                str,
                _closed(
                    call,
                    ("call_id", "name", "canonical_arguments_json"),
                    f"{field}.tool_calls[{index}]",
                )["name"],
            ),
            canonical_arguments_json=cast(
                str,
                _closed(
                    call,
                    ("call_id", "name", "canonical_arguments_json"),
                    f"{field}.tool_calls[{index}]",
                )["canonical_arguments_json"],
            ),
        )
        for index, call in enumerate(cast(list[object], calls_value))
    )
    return SubjectTurn(
        text=cast(str, item["text"]),
        tool_calls=calls,
        generated_tokens=cast(int, item["generated_tokens"]),
        finish_reason=cast(str | None, item["finish_reason"]),
    )


def synthetic_prefix_program_bytes(program: SyntheticPrefixProgram) -> bytes:
    if type(program) is not SyntheticPrefixProgram:
        raise TypeError("program must be exact SyntheticPrefixProgram")
    return canonical_json_bytes(asdict(program), indent=None)


def load_synthetic_prefix_program(payload: bytes) -> SyntheticPrefixProgram:
    if type(payload) is not bytes:
        raise TypeError("payload must be exact bytes")
    value = load_json_bytes(payload, source=Path("<synthetic-prefix-program>"))
    root_names = tuple(field.name for field in fields(SyntheticPrefixProgram))
    root = _closed(value, root_names, "synthetic prefix program")
    transcript_value = root["provider_transcript"]
    tools_value = root["tool_observations"]
    clock_value = root["clock_trace"]
    if (
        type(transcript_value) is not list
        or type(tools_value) is not list
        or type(clock_value) is not list
    ):
        raise TypeError("program ordered records must be exact arrays")
    transcript: list[SyntheticProviderTranscriptRow] = []
    for index, candidate in enumerate(cast(list[object], transcript_value)):
        item = _closed(
            candidate,
            tuple(field.name for field in fields(SyntheticProviderTranscriptRow)),
            f"provider_transcript[{index}]",
        )
        input_ids = item["expected_input_token_ids"]
        output_ids = item["reported_output_token_ids"]
        if type(input_ids) is not list or (
            output_ids is not None and type(output_ids) is not list
        ):
            raise TypeError("provider transcript token IDs must be arrays")
        transcript.append(
            SyntheticProviderTranscriptRow(
                subject_role=cast(
                    Literal["primary_subject", "user_simulator"],
                    item["subject_role"],
                ),
                call_index=cast(int, item["call_index"]),
                seed=cast(int, item["seed"]),
                model_contract_sha256=cast(str, item["model_contract_sha256"]),
                expected_request_ref=_decode_ref(
                    item["expected_request_ref"],
                    "expected_request_ref",
                    "synthetic_request",
                ),
                expected_request_sha256=cast(str, item["expected_request_sha256"]),
                expected_input_token_ids=tuple(cast(list[int], input_ids)),
                response_ref=(
                    _decode_ref(
                        item["response_ref"], "response_ref", "synthetic_response"
                    )
                    if item["response_ref"] is not None
                    else None
                ),
                typed_turn=(
                    _decode_subject_turn(item["typed_turn"], "typed_turn")
                    if item["typed_turn"] is not None
                    else None
                ),
                reported_output_token_ids=(
                    tuple(cast(list[int], output_ids))
                    if output_ids is not None
                    else None
                ),
                reported_generated_tokens=cast(int, item["reported_generated_tokens"]),
                provider_event_ref=_decode_ref(
                    item["provider_event_ref"],
                    "provider_event_ref",
                    "synthetic_provider_event",
                ),
                completion_kind=RawProviderCompletionKind(
                    cast(str, item["completion_kind"])
                ),
                transport_kind=ProviderTransportKind(cast(str, item["transport_kind"])),
                parser_outcome=ParserOutcome(cast(str, item["parser_outcome"])),
            )
        )
    tools: list[SyntheticToolObservation] = []
    for index, candidate in enumerate(cast(list[object], tools_value)):
        item = _closed(
            candidate,
            tuple(field.name for field in fields(SyntheticToolObservation)),
            f"tool_observations[{index}]",
        )
        tools.append(
            SyntheticToolObservation(
                call_id=cast(str, item["call_id"]),
                result_ref=_decode_ref(
                    item["result_ref"],
                    "result_ref",
                    "synthetic_tool_result",
                ),
                mutation_committed=cast(bool, item["mutation_committed"]),
                verifier_eligible=cast(bool, item["verifier_eligible"]),
                episode_terminal=cast(bool, item["episode_terminal"]),
                failure_kind=FailureKind(cast(str, item["failure_kind"])),
            )
        )
    grade = _closed(
        root["grade_result"],
        tuple(field.name for field in fields(SyntheticGradeResult)),
        "grade_result",
    )
    verifier = _closed(
        root["verifier_result"],
        tuple(field.name for field in fields(SyntheticVerifierResult)),
        "verifier_result",
    )
    injection = _closed(root["failure_injection"], ("stage",), "failure_injection")
    clocks_list: list[SyntheticClockRead] = []
    for index, candidate in enumerate(cast(list[object], clock_value)):
        item = _closed(
            candidate,
            ("label", "uint64_ms"),
            f"clock_trace[{index}]",
        )
        clocks_list.append(
            SyntheticClockRead(
                label=cast(str, item["label"]),
                uint64_ms=cast(int, item["uint64_ms"]),
            )
        )
    clocks = tuple(clocks_list)
    program = SyntheticPrefixProgram(
        record_kind=cast(
            Literal["synthetic_prefix_program_v1"],
            root["record_kind"],
        ),
        schema_version=cast(Literal["1"], root["schema_version"]),
        task_id=cast(str, root["task_id"]),
        expected_trigger_reason=TriggerReason(
            cast(str, root["expected_trigger_reason"])
        ),
        tool_schema_ref=_decode_ref(
            root["tool_schema_ref"], "tool_schema_ref", "tool_schema"
        ),
        provider_transcript=tuple(transcript),
        tool_observations=tuple(tools),
        grade_result=SyntheticGradeResult(
            evidence_ref=_decode_ref(
                grade["evidence_ref"],
                "grade_result.evidence_ref",
                "synthetic_grade_result",
            ),
            success=cast(int, grade["success"]),
            partial_reward=cast(float, grade["partial_reward"]),
            infrastructure_failure=cast(bool, grade["infrastructure_failure"]),
        ),
        verifier_result=SyntheticVerifierResult(
            evidence_ref=_decode_ref(
                verifier["evidence_ref"],
                "verifier_result.evidence_ref",
                "synthetic_verifier_result",
            ),
            finding_count=cast(int, verifier["finding_count"]),
        ),
        failure_injection=SyntheticFailureInjection(
            stage=cast(
                Literal[
                    "none",
                    "provider_transport",
                    "provider_parser",
                    "tool",
                ],
                injection["stage"],
            )
        ),
        clock_trace=clocks,
    )
    if payload != synthetic_prefix_program_bytes(program):
        raise ValueError("synthetic prefix program must be compact canonical JSON")
    return program


def prefix_candidate_receipt_bytes(receipt: object) -> bytes:
    from .evidence import FrozenPrefixReceipt

    if type(receipt) is not FrozenPrefixReceipt:
        raise TypeError("receipt must be exact FrozenPrefixReceipt")
    return canonical_json_bytes(
        {
            "record_kind": "frozen_prefix_candidate_v1",
            "schema_version": "1",
            "receipt": asdict(receipt),
        },
        indent=None,
    )


def validate_prefix_candidate_ref(ref: ArtifactRef) -> ArtifactRef:
    validated = _exact_ref(
        ref,
        "prefix_candidate_ref",
        role="prefix_candidate_receipt",
        registry=CONTROLLER_ROLE_MEDIA,
    )
    expected_path = f"controller-artifacts/prefix_candidate_receipt/{validated.sha256}"
    if validated.relative_path != expected_path:
        raise ValueError("prefix candidate ref path does not bind role and digest")
    return validated


def load_prefix_candidate_receipt(payload: bytes) -> object:
    from .artifacts import _decode_prefix_receipt_record
    from .evidence import FrozenPrefixReceipt

    if type(payload) is not bytes:
        raise TypeError("payload must be exact bytes")
    value = load_json_bytes(payload, source=Path("<prefix-candidate-receipt>"))
    root = _closed(
        value,
        ("record_kind", "schema_version", "receipt"),
        "prefix candidate receipt",
    )
    if (
        root["record_kind"] != "frozen_prefix_candidate_v1"
        or root["schema_version"] != "1"
    ):
        raise ValueError("prefix candidate receipt has wrong identity")
    receipt_value = root["receipt"]
    expected = tuple(field.name for field in fields(FrozenPrefixReceipt))
    receipt_mapping = _closed(
        receipt_value, expected, "prefix candidate receipt.receipt"
    )
    receipt = _decode_prefix_receipt_record(
        receipt_mapping,
        field="prefix candidate receipt.receipt",
    )
    if payload != prefix_candidate_receipt_bytes(receipt):
        raise ValueError("prefix candidate receipt must be compact canonical JSON")
    return receipt


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC


@final
class StableSourceProvenance:
    """Held-fd cooperative-local source read with an explicit second check."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("StableSourceProvenance is final")

    def __init__(
        self,
        source_root: Path,
        relative_path: Path,
        expected_ref: ArtifactRef,
    ) -> None:
        if type(source_root) is not type(Path()) or type(relative_path) is not type(
            Path()
        ):
            raise TypeError("source paths must be exact platform Path values")
        _exact_ref(
            expected_ref,
            "expected_ref",
            role="source_revision",
        )
        relative = PurePosixPath(relative_path.as_posix())
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in ("", ".", "..") for part in relative.parts)
            or relative.as_posix() != relative_path.as_posix()
        ):
            raise ValueError("source path must be normalized and relative")
        self._expected_ref = expected_ref
        self._root_fd: int | None = os.open(source_root, _DIRECTORY_FLAGS)
        self._parent_fds: list[int] = []
        self._fd: int | None = None
        parent = self._root_fd
        try:
            for component in relative.parts[:-1]:
                child = os.open(component, _DIRECTORY_FLAGS, dir_fd=parent)
                self._parent_fds.append(child)
                parent = child
            self._name = relative.parts[-1]
            self._parent_fd = parent
            try:
                self._fd = os.open(self._name, _READ_FLAGS, dir_fd=parent)
            except OSError as exc:
                raise ValueError(
                    "implementation source could not be opened without following links"
                ) from exc
            self._initial_identity = self._identity(os.fstat(self._fd))
            self.payload = self._read_and_verify(require_initial=True)
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _identity(metadata: os.stat_result) -> tuple[int, int, int, int]:
        if not stat.S_ISREG(metadata.st_mode):
            raise ValueError("implementation source must be a regular file")
        return (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_size,
            metadata.st_mtime_ns,
        )

    def _read_and_verify(self, *, require_initial: bool) -> bytes:
        if self._fd is None:
            raise RuntimeError("source provenance reader is closed")
        before = self._identity(os.fstat(self._fd))
        if require_initial and before != self._initial_identity:
            raise ValueError("implementation source identity drifted")
        os.lseek(self._fd, 0, os.SEEK_SET)
        chunks: list[bytes] = []
        while chunk := os.read(self._fd, 1024 * 1024):
            chunks.append(chunk)
        after = self._identity(os.fstat(self._fd))
        named = self._identity(
            os.stat(self._name, dir_fd=self._parent_fd, follow_symlinks=False)
        )
        if before != after or after != named or after != self._initial_identity:
            raise ValueError(
                "implementation source identity changed during stable read"
            )
        payload = b"".join(chunks)
        if (
            hashlib.sha256(payload).hexdigest() != self._expected_ref.sha256
            or len(payload) != self._expected_ref.byte_count
        ):
            raise ValueError("implementation source bytes differ from reviewed ref")
        return payload

    def verify_again(self) -> bytes:
        return self._read_and_verify(require_initial=True)

    def __enter__(self) -> StableSourceProvenance:
        if self._fd is None:
            raise RuntimeError("source provenance reader is closed")
        return self

    def __exit__(self, *_exception: object) -> None:
        self.close()

    def close(self) -> None:
        descriptors = (
            ([self._fd] if self._fd is not None else [])
            + list(reversed(self._parent_fds))
            + ([self._root_fd] if self._root_fd is not None else [])
        )
        self._fd = None
        self._parent_fds = []
        self._root_fd = None
        errors: list[Exception] = []
        for descriptor in descriptors:
            try:
                os.close(cast(int, descriptor))
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise ExceptionGroup("source provenance close was incomplete", errors)


__all__ = (
    "AUTHORITY_ASSET_ROLE_MEDIA",
    "CONTROLLER_ROLE_MEDIA",
    "REF_LOAD_CLASS_BY_ROLE",
    "EnvironmentProcessIdentity",
    "ImplementationDescriptor",
    "ParserOutcome",
    "ProviderTransportKind",
    "RawProviderCompletionKind",
    "RawProviderObservation",
    "SCIENTIFIC_PARENT_KIND",
    "StableSourceProvenance",
    "SyntheticClockRead",
    "SyntheticFailureInjection",
    "SyntheticGradeResult",
    "SyntheticPrefixProgram",
    "SyntheticProviderTranscriptRow",
    "SyntheticToolObservation",
    "SyntheticVerifierResult",
    "load_prefix_candidate_receipt",
    "load_synthetic_prefix_program",
    "prefix_candidate_receipt_bytes",
    "synthetic_prefix_program_bytes",
    "validate_prefix_candidate_ref",
)
