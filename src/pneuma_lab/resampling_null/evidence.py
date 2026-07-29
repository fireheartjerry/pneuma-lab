"""Controller-owned immutable evidence records for prefix execution.

These records close evidence shapes and ancestry. They do not dispatch a
provider, execute a tool, grade, verify, or publish a prefix index.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import Enum
import hashlib
from math import isfinite
from pathlib import Path
from typing import Literal, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .authority_refs import decode_artifact_ref, load_json_bytes
from .types import (
    ArtifactRef,
    CallSeedReceipt,
    CallContractCaps,
    FailureKind,
    FrozenVerifierReceipt,
    GradeReceipt,
    PrefixCaps,
    ResourceCounters,
    ToolCall,
    TriggerReason,
)


_U64_LIMIT = 2**64
_SNAPSHOT_SCHEMA_VERSION = "0.1.0"


def _exact_text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be exact text")
    text = cast(str, value)
    if not text:
        raise ValueError(f"{field} must be non-empty")
    return text


def _exact_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise TypeError(f"{field} must be exact bool")
    return cast(bool, value)


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an exact int")
    integer = cast(int, value)
    if integer < 0:
        raise ValueError(f"{field} must be non-negative")
    return integer


def _uint64(value: object, field: str) -> int:
    integer = _nonnegative_int(value, field)
    if integer >= _U64_LIMIT:
        raise ValueError(f"{field} must fit uint64")
    return integer


def _sha256(value: object, field: str) -> str:
    text = _exact_text(value, field)
    if len(text) != 64 or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _exact_ref(value: object, field: str) -> ArtifactRef:
    if type(value) is not ArtifactRef:
        raise TypeError(f"{field} must be an exact ArtifactRef")
    return cast(ArtifactRef, value)


def _authority_ref(value: object, field: str, *, role: str) -> ArtifactRef:
    ref = _exact_ref(value, field)
    if ref.role != role:
        raise ValueError(f"{field} role must equal {role!r}")
    return ref


def _controller_ref(value: object, field: str, *, role: str) -> ArtifactRef:
    ref = _authority_ref(value, field, role=role)
    expected_path = f"controller-artifacts/{role}/{ref.sha256}"
    if ref.relative_path != expected_path:
        raise ValueError(f"{field} path must equal {expected_path!r}")
    return ref


def _exact_tuple(
    value: object,
    *,
    field: str,
    member_type: type[object],
) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{field} must be an exact tuple")
    items = cast(tuple[object, ...], value)
    if not all(type(item) is member_type for item in items):
        raise TypeError(f"{field} must contain exact {member_type.__name__} records")
    return items


def _finite_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field} must be numeric")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{field} must be finite")
    return 0.0 if number == 0.0 else number


class ProviderAttemptStatus(str, Enum):
    """Closed terminal statuses for one provider dispatch."""

    COMPLETED = "completed"
    TIMEOUT_NO_RESPONSE = "timeout_no_response"
    TIMEOUT_LATE_RESPONSE = "timeout_late_response"
    REFUSAL = "refusal"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_ERROR = "provider_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"


@dataclass(frozen=True, slots=True)
class ProviderDispatchIntent:
    """The exact authority published before one role-local dispatch."""

    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int
    request_ref: ArtifactRef
    input_token_ids_ref: ArtifactRef
    model_contract_ref: ArtifactRef
    absolute_deadline_ms: int

    def __post_init__(self) -> None:
        if type(self.subject_role) is not str:
            raise TypeError("subject_role must be exact text")
        if self.subject_role not in ("primary_subject", "user_simulator"):
            raise ValueError("subject_role is not registered")
        _uint64(self.call_index, "call_index")
        _uint64(self.seed, "seed")
        _controller_ref(self.request_ref, "request_ref", role="provider_request")
        _controller_ref(
            self.input_token_ids_ref,
            "input_token_ids_ref",
            role="input_token_ids",
        )
        contract_role = (
            "subject_contract"
            if self.subject_role == "primary_subject"
            else "simulator_contract"
        )
        _authority_ref(
            self.model_contract_ref,
            "model_contract_ref",
            role=contract_role,
        )
        _uint64(self.absolute_deadline_ms, "absolute_deadline_ms")


@dataclass(frozen=True, slots=True)
class ProviderCallAttemptReceipt:
    """Controller record for the terminal observation of one dispatch."""

    dispatch_intent_ref: ArtifactRef
    subject_role: Literal["primary_subject", "user_simulator"]
    call_index: int
    seed: int
    status: ProviderAttemptStatus
    request_ref: ArtifactRef
    input_token_ids_ref: ArtifactRef
    response_ref: ArtifactRef | None
    output_token_ids_ref: ArtifactRef | None
    model_contract_ref: ArtifactRef
    generated_tokens: int
    elapsed_ms: int
    provider_event_ref: ArtifactRef

    def __post_init__(self) -> None:
        _controller_ref(
            self.dispatch_intent_ref,
            "dispatch_intent_ref",
            role="provider_dispatch_intent",
        )
        if type(self.subject_role) is not str:
            raise TypeError("subject_role must be exact text")
        if self.subject_role not in ("primary_subject", "user_simulator"):
            raise ValueError("subject_role is not registered")
        _uint64(self.call_index, "call_index")
        _uint64(self.seed, "seed")
        if type(self.status) is not ProviderAttemptStatus:
            raise TypeError("status must be exact ProviderAttemptStatus")
        _controller_ref(self.request_ref, "request_ref", role="provider_request")
        _controller_ref(
            self.input_token_ids_ref,
            "input_token_ids_ref",
            role="input_token_ids",
        )
        contract_role = (
            "subject_contract"
            if self.subject_role == "primary_subject"
            else "simulator_contract"
        )
        _authority_ref(
            self.model_contract_ref,
            "model_contract_ref",
            role=contract_role,
        )
        _controller_ref(
            self.provider_event_ref,
            "provider_event_ref",
            role="provider_event",
        )
        _nonnegative_int(self.generated_tokens, "generated_tokens")
        _nonnegative_int(self.elapsed_ms, "elapsed_ms")
        response_present = self.response_ref is not None
        tokens_present = self.output_token_ids_ref is not None
        if response_present != tokens_present:
            raise ValueError(
                "response_ref and output_token_ids_ref must appear together"
            )
        if response_present:
            _controller_ref(
                self.response_ref,
                "response_ref",
                role="provider_response",
            )
            _controller_ref(
                self.output_token_ids_ref,
                "output_token_ids_ref",
                role="output_token_ids",
            )
        elif self.generated_tokens != 0:
            raise ValueError("response-less attempts cannot have generated tokens")
        if (
            self.status
            in (
                ProviderAttemptStatus.COMPLETED,
                ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE,
                ProviderAttemptStatus.REFUSAL,
                ProviderAttemptStatus.MALFORMED_RESPONSE,
            )
            and not response_present
        ):
            raise ValueError(f"{self.status.value} requires response evidence")
        if (
            self.status is ProviderAttemptStatus.TIMEOUT_NO_RESPONSE
            and response_present
        ):
            raise ValueError("timeout_no_response forbids response evidence")

    def validate_against(
        self,
        *,
        intent: ProviderDispatchIntent,
        intent_ref: ArtifactRef,
    ) -> None:
        if type(intent) is not ProviderDispatchIntent:
            raise TypeError("intent must be exact ProviderDispatchIntent")
        _controller_ref(
            intent_ref,
            "intent_ref",
            role="provider_dispatch_intent",
        )
        if self.dispatch_intent_ref != intent_ref:
            raise ValueError("attempt dispatch_intent_ref is cross-wired")
        repeated = (
            self.subject_role,
            self.call_index,
            self.seed,
            self.request_ref,
            self.input_token_ids_ref,
            self.model_contract_ref,
        )
        expected = (
            intent.subject_role,
            intent.call_index,
            intent.seed,
            intent.request_ref,
            intent.input_token_ids_ref,
            intent.model_contract_ref,
        )
        if repeated != expected:
            raise ValueError("attempt fields differ from dispatch intent")


@dataclass(frozen=True, slots=True)
class ProviderAttemptLedger:
    """Exact ordered dispatch/terminal-attempt ledger."""

    intents: tuple[ProviderDispatchIntent, ...]
    intent_refs: tuple[ArtifactRef, ...]
    attempts: tuple[ProviderCallAttemptReceipt, ...]

    def __post_init__(self) -> None:
        _exact_tuple(
            self.intents,
            field="intents",
            member_type=ProviderDispatchIntent,
        )
        _exact_tuple(
            self.intent_refs,
            field="intent_refs",
            member_type=ArtifactRef,
        )
        _exact_tuple(
            self.attempts,
            field="attempts",
            member_type=ProviderCallAttemptReceipt,
        )
        if not (len(self.intents) == len(self.intent_refs) == len(self.attempts)):
            raise ValueError("each intent must have exactly one terminal attempt")
        if len(set(self.intent_refs)) != len(self.intent_refs):
            raise ValueError("intent_refs must be pairwise distinct")
        for ref in self.intent_refs:
            _controller_ref(
                ref,
                "intent_refs item",
                role="provider_dispatch_intent",
            )
        provider_events = [attempt.provider_event_ref for attempt in self.attempts]
        if len(provider_events) != len(set(provider_events)):
            raise ValueError("provider_event_ref values must be pairwise distinct")
        next_index = {"primary_subject": 0, "user_simulator": 0}
        for intent, intent_ref, attempt in zip(
            self.intents,
            self.intent_refs,
            self.attempts,
            strict=True,
        ):
            if intent.call_index != next_index[intent.subject_role]:
                raise ValueError("role-local call indexes must be consecutive")
            next_index[intent.subject_role] += 1
            attempt.validate_against(intent=intent, intent_ref=intent_ref)


@dataclass(frozen=True, slots=True)
class CompletedToolBoundaryReceipt:
    """One exact completed tool-result boundary."""

    call_id: str
    tool_call_ref: ArtifactRef
    tool_result_ref: ArtifactRef
    mutation_committed: bool
    verifier_eligible_after: bool
    episode_terminal: bool
    failure_kind: FailureKind
    elapsed_ms: int

    def __post_init__(self) -> None:
        _exact_text(self.call_id, "call_id")
        _controller_ref(self.tool_call_ref, "tool_call_ref", role="tool_call")
        _controller_ref(self.tool_result_ref, "tool_result_ref", role="tool_result")
        _exact_bool(self.mutation_committed, "mutation_committed")
        _exact_bool(self.verifier_eligible_after, "verifier_eligible_after")
        _exact_bool(self.episode_terminal, "episode_terminal")
        if type(self.failure_kind) is not FailureKind:
            raise TypeError("failure_kind must be exact FailureKind")
        _nonnegative_int(self.elapsed_ms, "elapsed_ms")


@dataclass(frozen=True, slots=True)
class ToolBoundaryLedger:
    """Exact chronological tool boundary sequence."""

    boundaries: tuple[CompletedToolBoundaryReceipt, ...]

    def __post_init__(self) -> None:
        _exact_tuple(
            self.boundaries,
            field="boundaries",
            member_type=CompletedToolBoundaryReceipt,
        )
        call_ids = [boundary.call_id for boundary in self.boundaries]
        if len(call_ids) != len(set(call_ids)):
            raise ValueError("completed boundaries must not repeat call_id")
        terminal_indexes = [
            index
            for index, boundary in enumerate(self.boundaries)
            if boundary.episode_terminal
        ]
        if terminal_indexes and terminal_indexes != [len(self.boundaries) - 1]:
            raise ValueError("a terminal boundary must be the final boundary")


@dataclass(frozen=True, slots=True)
class CompositeSnapshotEnvelope:
    """Closed canonical snapshot ancestry and all restorable controller state."""

    schema_version: Literal["0.1.0"]
    study_ref: ArtifactRef
    task_ref: ArtifactRef
    schedule_ref: ArtifactRef
    task_input_ref: ArtifactRef
    environment_contract_ref: ArtifactRef
    isolation_contract_ref: ArtifactRef
    environment_snapshot_ref: ArtifactRef
    branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    visible_context_ref: ArtifactRef
    visible_sha256: str
    token_ids_ref: ArtifactRef
    token_ids_sha256: str
    boundary_ledger_ref: ArtifactRef
    provider_attempts_ref: ArtifactRef
    primary_counters: ResourceCounters
    simulator_counters: ResourceCounters
    primary_remaining_quotas: PrefixCaps
    simulator_remaining_quotas: CallContractCaps | None
    cumulative_mutation: bool
    episode_terminal: bool
    terminal_failure_kind: FailureKind
    subject_stateless_attestation_ref: ArtifactRef
    simulator_stateless_attestation_ref: ArtifactRef | None
    runtime_ref: ArtifactRef
    container_ref: ArtifactRef
    source_revision_ref: ArtifactRef

    def __post_init__(self) -> None:
        if self.schema_version != _SNAPSHOT_SCHEMA_VERSION:
            raise ValueError("snapshot schema_version must equal '0.1.0'")
        for name, role in (
            ("study_ref", "study_manifest"),
            ("schedule_ref", "resampling_prefix_schedule"),
            ("task_input_ref", "task_input"),
            ("environment_contract_ref", "environment_contract"),
            ("isolation_contract_ref", "isolation_contract"),
            ("source_revision_ref", "source_revision"),
        ):
            _authority_ref(getattr(self, name), name, role=role)
        for name, role in (
            ("task_ref", "selected_task"),
            ("environment_snapshot_ref", "environment_snapshot"),
            ("visible_context_ref", "visible_context"),
            ("token_ids_ref", "token_ids"),
            ("boundary_ledger_ref", "tool_boundary_ledger"),
            ("provider_attempts_ref", "provider_attempt_ledger"),
            (
                "subject_stateless_attestation_ref",
                "subject_stateless_attestation",
            ),
            ("runtime_ref", "runtime_attestation"),
            ("container_ref", "container_attestation"),
        ):
            _controller_ref(getattr(self, name), name, role=role)
        _exact_tuple(
            self.branch_pending_calls,
            field="branch_pending_calls",
            member_type=ToolCall,
        )
        _exact_tuple(
            self.terminal_unexecuted_remainder,
            field="terminal_unexecuted_remainder",
            member_type=ToolCall,
        )
        if self.branch_pending_calls and self.terminal_unexecuted_remainder:
            raise ValueError("branch and terminal pending-call queues are exclusive")
        _unique_call_ids(
            self.branch_pending_calls,
            field="branch_pending_calls",
        )
        _unique_call_ids(
            self.terminal_unexecuted_remainder,
            field="terminal_unexecuted_remainder",
        )
        _sha256(self.visible_sha256, "visible_sha256")
        _sha256(self.token_ids_sha256, "token_ids_sha256")
        if self.visible_sha256 != self.visible_context_ref.sha256:
            raise ValueError("visible_sha256 must equal visible_context_ref digest")
        if self.token_ids_sha256 != self.token_ids_ref.sha256:
            raise ValueError("token_ids_sha256 must equal token_ids_ref digest")
        if type(self.primary_counters) is not ResourceCounters:
            raise TypeError("primary_counters must be exact ResourceCounters")
        if type(self.simulator_counters) is not ResourceCounters:
            raise TypeError("simulator_counters must be exact ResourceCounters")
        if self.primary_counters.wall_clock_ms != self.simulator_counters.wall_clock_ms:
            raise ValueError(
                "primary and simulator counters must repeat total wall time"
            )
        if self.simulator_counters.tool_calls != 0:
            raise ValueError("simulator counters cannot include tool calls")
        if type(self.primary_remaining_quotas) is not PrefixCaps:
            raise TypeError("primary_remaining_quotas must be exact PrefixCaps")
        simulator_free = self.simulator_remaining_quotas is None
        if (
            not simulator_free
            and type(self.simulator_remaining_quotas) is not CallContractCaps
        ):
            raise TypeError(
                "simulator_remaining_quotas must be exact CallContractCaps or None"
            )
        if simulator_free != (self.simulator_stateless_attestation_ref is None):
            raise ValueError(
                "simulator attestation is nullable exactly for simulator-free authority"
            )
        simulator_usage_is_zero = (
            self.simulator_counters.generated_tokens == 0
            and self.simulator_counters.model_calls == 0
            and self.simulator_counters.tool_calls == 0
        )
        if simulator_free != simulator_usage_is_zero:
            raise ValueError(
                "simulator-free authority requires exactly zero simulator usage"
            )
        if self.simulator_stateless_attestation_ref is not None:
            _controller_ref(
                self.simulator_stateless_attestation_ref,
                "simulator_stateless_attestation_ref",
                role="simulator_stateless_attestation",
            )
        _exact_bool(self.cumulative_mutation, "cumulative_mutation")
        _exact_bool(self.episode_terminal, "episode_terminal")
        if type(self.terminal_failure_kind) is not FailureKind:
            raise TypeError("terminal_failure_kind must be exact FailureKind")
        if self.episode_terminal and self.branch_pending_calls:
            raise ValueError("a terminal snapshot cannot retain branch-pending calls")
        if (
            self.terminal_failure_kind is not FailureKind.NONE
            and not self.episode_terminal
        ):
            raise ValueError("adverse failure state must be terminal")
        if self.terminal_unexecuted_remainder and (
            not self.episode_terminal
            or self.terminal_failure_kind is not FailureKind.MALFORMED_ACTION
        ):
            raise ValueError(
                "terminal remainder requires terminal malformed-action state"
            )


def _unique_call_ids(calls: tuple[ToolCall, ...], *, field: str) -> None:
    call_ids = [call.call_id for call in calls]
    if len(call_ids) != len(set(call_ids)):
        raise ValueError(f"{field} must not repeat call_id")


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return {field.name: getattr(ref, field.name) for field in fields(ArtifactRef)}


def _tool_call_mapping(call: ToolCall) -> dict[str, object]:
    return {
        "call_id": call.call_id,
        "name": call.name,
        "canonical_arguments_json": call.canonical_arguments_json,
    }


def _counters_mapping(counters: ResourceCounters) -> dict[str, int]:
    return {
        field.name: cast(int, getattr(counters, field.name))
        for field in fields(ResourceCounters)
    }


def _caps_mapping(caps: PrefixCaps | CallContractCaps) -> dict[str, int]:
    return {field.name: cast(int, getattr(caps, field.name)) for field in fields(caps)}


def composite_snapshot_mapping(
    snapshot: CompositeSnapshotEnvelope,
) -> dict[str, object]:
    """Return the exact closed JSON value for a composite snapshot."""

    if type(snapshot) is not CompositeSnapshotEnvelope:
        raise TypeError("snapshot must be exact CompositeSnapshotEnvelope")
    return {
        "schema_version": snapshot.schema_version,
        "study_ref": _ref_mapping(snapshot.study_ref),
        "task_ref": _ref_mapping(snapshot.task_ref),
        "schedule_ref": _ref_mapping(snapshot.schedule_ref),
        "task_input_ref": _ref_mapping(snapshot.task_input_ref),
        "environment_contract_ref": _ref_mapping(snapshot.environment_contract_ref),
        "isolation_contract_ref": _ref_mapping(snapshot.isolation_contract_ref),
        "environment_snapshot_ref": _ref_mapping(snapshot.environment_snapshot_ref),
        "branch_pending_calls": [
            _tool_call_mapping(call) for call in snapshot.branch_pending_calls
        ],
        "terminal_unexecuted_remainder": [
            _tool_call_mapping(call) for call in snapshot.terminal_unexecuted_remainder
        ],
        "visible_context_ref": _ref_mapping(snapshot.visible_context_ref),
        "visible_sha256": snapshot.visible_sha256,
        "token_ids_ref": _ref_mapping(snapshot.token_ids_ref),
        "token_ids_sha256": snapshot.token_ids_sha256,
        "boundary_ledger_ref": _ref_mapping(snapshot.boundary_ledger_ref),
        "provider_attempts_ref": _ref_mapping(snapshot.provider_attempts_ref),
        "primary_counters": _counters_mapping(snapshot.primary_counters),
        "simulator_counters": _counters_mapping(snapshot.simulator_counters),
        "primary_remaining_quotas": _caps_mapping(snapshot.primary_remaining_quotas),
        "simulator_remaining_quotas": (
            _caps_mapping(snapshot.simulator_remaining_quotas)
            if snapshot.simulator_remaining_quotas is not None
            else None
        ),
        "cumulative_mutation": snapshot.cumulative_mutation,
        "episode_terminal": snapshot.episode_terminal,
        "terminal_failure_kind": snapshot.terminal_failure_kind.value,
        "subject_stateless_attestation_ref": _ref_mapping(
            snapshot.subject_stateless_attestation_ref
        ),
        "simulator_stateless_attestation_ref": (
            _ref_mapping(snapshot.simulator_stateless_attestation_ref)
            if snapshot.simulator_stateless_attestation_ref is not None
            else None
        ),
        "runtime_ref": _ref_mapping(snapshot.runtime_ref),
        "container_ref": _ref_mapping(snapshot.container_ref),
        "source_revision_ref": _ref_mapping(snapshot.source_revision_ref),
    }


def composite_snapshot_bytes(snapshot: CompositeSnapshotEnvelope) -> bytes:
    """Serialize one snapshot to compact canonical controller-owned bytes."""

    return canonical_json_bytes(composite_snapshot_mapping(snapshot), indent=None)


def _closed(
    value: object,
    *,
    expected: tuple[str, ...],
    field: str,
) -> dict[str, object]:
    if not isinstance(value, Mapping) or set(value) != set(expected):
        raise ValueError(f"{field} has an open or incomplete shape")
    return dict(value)


def _decode_ref(value: object, field: str) -> ArtifactRef:
    try:
        return decode_artifact_ref(value, field=field)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def _decode_calls(value: object, *, field: str) -> tuple[ToolCall, ...]:
    if type(value) is not list:
        raise TypeError(f"{field} must be an exact JSON array")
    calls: list[ToolCall] = []
    for index, item in enumerate(cast(list[object], value)):
        mapping = _closed(
            item,
            expected=("call_id", "name", "canonical_arguments_json"),
            field=f"{field}[{index}]",
        )
        calls.append(
            ToolCall(
                call_id=cast(str, mapping["call_id"]),
                name=cast(str, mapping["name"]),
                canonical_arguments_json=cast(
                    str,
                    mapping["canonical_arguments_json"],
                ),
            )
        )
    return tuple(calls)


def _decode_record(
    value: object,
    *,
    record_type: type[ResourceCounters] | type[PrefixCaps] | type[CallContractCaps],
    field: str,
) -> ResourceCounters | PrefixCaps | CallContractCaps:
    names = tuple(item.name for item in fields(record_type))
    mapping = _closed(value, expected=names, field=field)
    if record_type is ResourceCounters:
        return ResourceCounters(
            generated_tokens=cast(int, mapping["generated_tokens"]),
            model_calls=cast(int, mapping["model_calls"]),
            tool_calls=cast(int, mapping["tool_calls"]),
            wall_clock_ms=cast(int, mapping["wall_clock_ms"]),
        )
    if record_type is PrefixCaps:
        return PrefixCaps(
            generated_tokens=cast(int, mapping["generated_tokens"]),
            model_calls=cast(int, mapping["model_calls"]),
            tool_calls=cast(int, mapping["tool_calls"]),
            wall_clock_ms=cast(int, mapping["wall_clock_ms"]),
        )
    return CallContractCaps(
        aggregate_generated_tokens=cast(
            int,
            mapping["aggregate_generated_tokens"],
        ),
        aggregate_model_calls=cast(int, mapping["aggregate_model_calls"]),
        aggregate_turns=cast(int, mapping["aggregate_turns"]),
        per_call_generated_tokens=cast(
            int,
            mapping["per_call_generated_tokens"],
        ),
        per_call_turns=cast(int, mapping["per_call_turns"]),
    )


def load_composite_snapshot(payload: bytes) -> CompositeSnapshotEnvelope:
    """Strictly decode and canonical-byte-check one composite snapshot."""

    if type(payload) is not bytes:
        raise TypeError("payload must be exact bytes")
    value = load_json_bytes(payload, source=Path("<composite-snapshot>"))
    expected = tuple(field.name for field in fields(CompositeSnapshotEnvelope))
    mapping = _closed(value, expected=expected, field="composite snapshot")
    try:
        snapshot = CompositeSnapshotEnvelope(
            schema_version=cast(Literal["0.1.0"], mapping["schema_version"]),
            study_ref=_decode_ref(mapping["study_ref"], "study_ref"),
            task_ref=_decode_ref(mapping["task_ref"], "task_ref"),
            schedule_ref=_decode_ref(mapping["schedule_ref"], "schedule_ref"),
            task_input_ref=_decode_ref(mapping["task_input_ref"], "task_input_ref"),
            environment_contract_ref=_decode_ref(
                mapping["environment_contract_ref"],
                "environment_contract_ref",
            ),
            isolation_contract_ref=_decode_ref(
                mapping["isolation_contract_ref"],
                "isolation_contract_ref",
            ),
            environment_snapshot_ref=_decode_ref(
                mapping["environment_snapshot_ref"],
                "environment_snapshot_ref",
            ),
            branch_pending_calls=_decode_calls(
                mapping["branch_pending_calls"],
                field="branch_pending_calls",
            ),
            terminal_unexecuted_remainder=_decode_calls(
                mapping["terminal_unexecuted_remainder"],
                field="terminal_unexecuted_remainder",
            ),
            visible_context_ref=_decode_ref(
                mapping["visible_context_ref"],
                "visible_context_ref",
            ),
            visible_sha256=cast(str, mapping["visible_sha256"]),
            token_ids_ref=_decode_ref(mapping["token_ids_ref"], "token_ids_ref"),
            token_ids_sha256=cast(str, mapping["token_ids_sha256"]),
            boundary_ledger_ref=_decode_ref(
                mapping["boundary_ledger_ref"],
                "boundary_ledger_ref",
            ),
            provider_attempts_ref=_decode_ref(
                mapping["provider_attempts_ref"],
                "provider_attempts_ref",
            ),
            primary_counters=cast(
                ResourceCounters,
                _decode_record(
                    mapping["primary_counters"],
                    record_type=ResourceCounters,
                    field="primary_counters",
                ),
            ),
            simulator_counters=cast(
                ResourceCounters,
                _decode_record(
                    mapping["simulator_counters"],
                    record_type=ResourceCounters,
                    field="simulator_counters",
                ),
            ),
            primary_remaining_quotas=cast(
                PrefixCaps,
                _decode_record(
                    mapping["primary_remaining_quotas"],
                    record_type=PrefixCaps,
                    field="primary_remaining_quotas",
                ),
            ),
            simulator_remaining_quotas=(
                cast(
                    CallContractCaps,
                    _decode_record(
                        mapping["simulator_remaining_quotas"],
                        record_type=CallContractCaps,
                        field="simulator_remaining_quotas",
                    ),
                )
                if mapping["simulator_remaining_quotas"] is not None
                else None
            ),
            cumulative_mutation=cast(bool, mapping["cumulative_mutation"]),
            episode_terminal=cast(bool, mapping["episode_terminal"]),
            terminal_failure_kind=FailureKind(
                cast(str, mapping["terminal_failure_kind"])
            ),
            subject_stateless_attestation_ref=_decode_ref(
                mapping["subject_stateless_attestation_ref"],
                "subject_stateless_attestation_ref",
            ),
            simulator_stateless_attestation_ref=(
                _decode_ref(
                    mapping["simulator_stateless_attestation_ref"],
                    "simulator_stateless_attestation_ref",
                )
                if mapping["simulator_stateless_attestation_ref"] is not None
                else None
            ),
            runtime_ref=_decode_ref(mapping["runtime_ref"], "runtime_ref"),
            container_ref=_decode_ref(mapping["container_ref"], "container_ref"),
            source_revision_ref=_decode_ref(
                mapping["source_revision_ref"],
                "source_revision_ref",
            ),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"composite snapshot is malformed: {exc}") from exc
    if payload != composite_snapshot_bytes(snapshot):
        raise ValueError("composite snapshot bytes must be compact canonical JSON")
    return snapshot


def validate_snapshot_receipt_fields(
    snapshot: CompositeSnapshotEnvelope,
    *,
    snapshot_ref: ArtifactRef,
    snapshot_bytes: bytes,
    visible_context_ref: ArtifactRef,
    visible_sha256: str,
    token_ids_ref: ArtifactRef,
    token_ids_sha256: str,
    branch_pending_calls: tuple[ToolCall, ...],
    terminal_unexecuted_remainder: tuple[ToolCall, ...],
    boundary_ledger_ref: ArtifactRef,
    provider_attempts_ref: ArtifactRef,
    primary_counters: ResourceCounters,
    simulator_counters: ResourceCounters,
    terminal_failure_kind: FailureKind,
) -> None:
    """Byte-check an envelope and all fields duplicated by its outer receipt."""

    if type(snapshot) is not CompositeSnapshotEnvelope:
        raise TypeError("snapshot must be exact CompositeSnapshotEnvelope")
    _controller_ref(snapshot_ref, "snapshot_ref", role="composite_snapshot")
    if type(snapshot_bytes) is not bytes:
        raise TypeError("snapshot_bytes must be exact bytes")
    canonical = composite_snapshot_bytes(snapshot)
    if snapshot_bytes != canonical:
        raise ValueError("snapshot bytes differ from canonical envelope bytes")
    digest = hashlib.sha256(snapshot_bytes).hexdigest()
    expected_path = f"controller-artifacts/{snapshot_ref.role}/{digest}"
    if (
        snapshot_ref.sha256 != digest
        or snapshot_ref.byte_count != len(snapshot_bytes)
        or snapshot_ref.relative_path != expected_path
        or snapshot_ref.media_type != "application/json"
    ):
        raise ValueError("snapshot_ref does not identify exact snapshot bytes")
    duplicates = (
        (snapshot.visible_context_ref, visible_context_ref, "visible_context_ref"),
        (snapshot.visible_sha256, visible_sha256, "visible_sha256"),
        (snapshot.token_ids_ref, token_ids_ref, "token_ids_ref"),
        (snapshot.token_ids_sha256, token_ids_sha256, "token_ids_sha256"),
        (snapshot.branch_pending_calls, branch_pending_calls, "branch_pending_calls"),
        (
            snapshot.terminal_unexecuted_remainder,
            terminal_unexecuted_remainder,
            "terminal_unexecuted_remainder",
        ),
        (snapshot.boundary_ledger_ref, boundary_ledger_ref, "boundary_ledger_ref"),
        (
            snapshot.provider_attempts_ref,
            provider_attempts_ref,
            "provider_attempts_ref",
        ),
        (snapshot.primary_counters, primary_counters, "primary_counters"),
        (snapshot.simulator_counters, simulator_counters, "simulator_counters"),
        (
            snapshot.terminal_failure_kind,
            terminal_failure_kind,
            "terminal_failure_kind",
        ),
    )
    for inside, outside, field in duplicates:
        if inside != outside:
            raise ValueError(f"outer {field} differs from composite snapshot")


@dataclass(frozen=True, slots=True)
class FrozenPrefixReceipt:
    """Closed outer prefix receipt whose duplicated snapshot fields are checked."""

    task_id: str
    schedule_sha256: str
    prefix_caps: PrefixCaps
    snapshot_ref: ArtifactRef
    visible_context_ref: ArtifactRef
    visible_sha256: str
    token_ids_ref: ArtifactRef
    token_ids_sha256: str
    branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    trigger_reason: TriggerReason
    terminal_failure_kind: FailureKind
    y0_grade: GradeReceipt
    grade_execution_receipt_ref: ArtifactRef
    verifier_receipt: FrozenVerifierReceipt
    verifier_execution_receipt_ref: ArtifactRef
    counters: ResourceCounters
    simulator_counters: ResourceCounters
    call_seeds: tuple[CallSeedReceipt, ...]
    provider_attempts_ref: ArtifactRef
    boundary_ledger_ref: ArtifactRef
    provider_cost_ref: ArtifactRef

    def __post_init__(self) -> None:
        _exact_text(self.task_id, "task_id")
        _sha256(self.schedule_sha256, "schedule_sha256")
        if type(self.prefix_caps) is not PrefixCaps:
            raise TypeError("prefix_caps must be exact PrefixCaps")
        for name, role in (
            ("snapshot_ref", "composite_snapshot"),
            ("visible_context_ref", "visible_context"),
            ("token_ids_ref", "token_ids"),
            ("provider_attempts_ref", "provider_attempt_ledger"),
            ("boundary_ledger_ref", "tool_boundary_ledger"),
            ("provider_cost_ref", "provider_cost_closure"),
            ("grade_execution_receipt_ref", "grade_evidence_receipt"),
            ("verifier_execution_receipt_ref", "verifier_evidence_receipt"),
        ):
            _controller_ref(getattr(self, name), name, role=role)
        _sha256(self.visible_sha256, "visible_sha256")
        _sha256(self.token_ids_sha256, "token_ids_sha256")
        if self.visible_sha256 != self.visible_context_ref.sha256:
            raise ValueError("visible_sha256 must equal visible_context_ref digest")
        if self.token_ids_sha256 != self.token_ids_ref.sha256:
            raise ValueError("token_ids_sha256 must equal token_ids_ref digest")
        _exact_tuple(
            self.branch_pending_calls,
            field="branch_pending_calls",
            member_type=ToolCall,
        )
        _exact_tuple(
            self.terminal_unexecuted_remainder,
            field="terminal_unexecuted_remainder",
            member_type=ToolCall,
        )
        if self.branch_pending_calls and self.terminal_unexecuted_remainder:
            raise ValueError("prefix pending-call queues are exclusive")
        _unique_call_ids(self.branch_pending_calls, field="branch_pending_calls")
        _unique_call_ids(
            self.terminal_unexecuted_remainder,
            field="terminal_unexecuted_remainder",
        )
        if type(self.trigger_reason) is not TriggerReason:
            raise TypeError("trigger_reason must be exact TriggerReason")
        if type(self.terminal_failure_kind) is not FailureKind:
            raise TypeError("terminal_failure_kind must be exact FailureKind")
        if (
            self.trigger_reason is not TriggerReason.NO_INTERVENTION_OPPORTUNITY
            and self.terminal_failure_kind is not FailureKind.NONE
        ):
            raise ValueError("a branchable trigger cannot carry terminal failure")
        if (
            self.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY
            and self.branch_pending_calls
        ):
            raise ValueError("a no-trigger receipt cannot retain branch calls")
        if self.terminal_unexecuted_remainder and (
            self.trigger_reason is not TriggerReason.NO_INTERVENTION_OPPORTUNITY
            or self.terminal_failure_kind is not FailureKind.MALFORMED_ACTION
        ):
            raise ValueError(
                "terminal remainder requires no-trigger malformed-action state"
            )
        if type(self.y0_grade) is not GradeReceipt:
            raise TypeError("y0_grade must be exact GradeReceipt")
        _controller_ref(
            self.y0_grade.artifact_ref,
            "y0_grade.artifact_ref",
            role="grade_evidence",
        )
        if (
            self.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY
            and self.terminal_failure_kind is not FailureKind.NONE
            and (self.y0_grade.success != 0 or self.y0_grade.partial_reward != 0.0)
        ):
            raise ValueError("adverse no-trigger requires forced-zero scientific Y0")
        if type(self.verifier_receipt) is not FrozenVerifierReceipt:
            raise TypeError("verifier_receipt must be exact FrozenVerifierReceipt")
        _controller_ref(
            self.verifier_receipt.verifier_artifact_ref,
            "verifier_receipt.verifier_artifact_ref",
            role="verifier_evidence",
        )
        if (
            self.verifier_receipt.task_id != self.task_id
            or self.verifier_receipt.schedule_sha256 != self.schedule_sha256
            or self.verifier_receipt.snapshot_ref != self.snapshot_ref
        ):
            raise ValueError("verifier receipt ancestry differs from prefix")
        if type(self.counters) is not ResourceCounters:
            raise TypeError("counters must be exact ResourceCounters")
        if type(self.simulator_counters) is not ResourceCounters:
            raise TypeError("simulator_counters must be exact ResourceCounters")
        if self.counters.wall_clock_ms != self.simulator_counters.wall_clock_ms:
            raise ValueError("counter records must repeat total wall time")
        if self.simulator_counters.tool_calls != 0:
            raise ValueError("simulator counters cannot include tool calls")
        _exact_tuple(
            self.call_seeds,
            field="call_seeds",
            member_type=CallSeedReceipt,
        )
        next_index = {"primary_subject": 0, "user_simulator": 0}
        for receipt in self.call_seeds:
            if receipt.call_index != next_index[receipt.subject_role]:
                raise ValueError("call_seeds role-local indexes must be consecutive")
            next_index[receipt.subject_role] += 1

    def validate_snapshot_bytes(self, payload: bytes) -> None:
        snapshot = load_composite_snapshot(payload)
        if snapshot.schedule_ref.sha256 != self.schedule_sha256:
            raise ValueError("snapshot schedule differs from prefix receipt")
        cap_pairs = (
            (
                snapshot.primary_counters.generated_tokens,
                snapshot.primary_remaining_quotas.generated_tokens,
                self.prefix_caps.generated_tokens,
            ),
            (
                snapshot.primary_counters.model_calls,
                snapshot.primary_remaining_quotas.model_calls,
                self.prefix_caps.model_calls,
            ),
            (
                snapshot.primary_counters.tool_calls,
                snapshot.primary_remaining_quotas.tool_calls,
                self.prefix_caps.tool_calls,
            ),
            (
                snapshot.primary_counters.wall_clock_ms,
                snapshot.primary_remaining_quotas.wall_clock_ms,
                self.prefix_caps.wall_clock_ms,
            ),
        )
        if any(used + remaining != cap for used, remaining, cap in cap_pairs):
            raise ValueError("snapshot counters plus remaining quotas differ from caps")
        validate_snapshot_receipt_fields(
            snapshot,
            snapshot_ref=self.snapshot_ref,
            snapshot_bytes=payload,
            visible_context_ref=self.visible_context_ref,
            visible_sha256=self.visible_sha256,
            token_ids_ref=self.token_ids_ref,
            token_ids_sha256=self.token_ids_sha256,
            branch_pending_calls=self.branch_pending_calls,
            terminal_unexecuted_remainder=self.terminal_unexecuted_remainder,
            boundary_ledger_ref=self.boundary_ledger_ref,
            provider_attempts_ref=self.provider_attempts_ref,
            primary_counters=self.counters,
            simulator_counters=self.simulator_counters,
            terminal_failure_kind=self.terminal_failure_kind,
        )


@dataclass(frozen=True, slots=True)
class GradeEvidence:
    """Closed raw grade output; deliberately contains no ArtifactRef."""

    success: int
    partial_reward: float
    infrastructure_failure: bool
    raw_payload: bytes

    def __post_init__(self) -> None:
        if type(self.success) is not int:
            raise TypeError("success must be an exact int")
        if self.success not in (0, 1):
            raise ValueError("success must be 0 or 1")
        object.__setattr__(
            self,
            "partial_reward",
            _finite_number(self.partial_reward, "partial_reward"),
        )
        _exact_bool(self.infrastructure_failure, "infrastructure_failure")
        if self.infrastructure_failure and self.success:
            raise ValueError("infrastructure failure requires success == 0")
        if type(self.raw_payload) is not bytes:
            raise TypeError("raw_payload must be exact bytes")


@dataclass(frozen=True, slots=True)
class VerifierEvidence:
    """Closed raw verifier output; deliberately contains no ArtifactRef."""

    finding_count: int
    raw_payload: bytes

    def __post_init__(self) -> None:
        _nonnegative_int(self.finding_count, "finding_count")
        if type(self.raw_payload) is not bytes:
            raise TypeError("raw_payload must be exact bytes")


@dataclass(frozen=True, slots=True)
class RestoreIdentity:
    """Nominal restored environment/process/writable-root identity."""

    instance_id: str
    process_id: int
    writable_root_id: str

    def __post_init__(self) -> None:
        _exact_text(self.instance_id, "instance_id")
        _nonnegative_int(self.process_id, "process_id")
        _exact_text(self.writable_root_id, "writable_root_id")


@dataclass(frozen=True, slots=True)
class GradeEvidenceReceipt:
    identity: RestoreIdentity
    snapshot_ref: ArtifactRef
    restore_receipt_ref: ArtifactRef
    evidence_ref: ArtifactRef

    def __post_init__(self) -> None:
        if type(self.identity) is not RestoreIdentity:
            raise TypeError("identity must be exact RestoreIdentity")
        for name, role in (
            ("snapshot_ref", "composite_snapshot"),
            ("restore_receipt_ref", "grade_restore_receipt"),
            ("evidence_ref", "grade_evidence"),
        ):
            _controller_ref(getattr(self, name), name, role=role)


@dataclass(frozen=True, slots=True)
class VerifierEvidenceReceipt:
    identity: RestoreIdentity
    snapshot_ref: ArtifactRef
    restore_receipt_ref: ArtifactRef
    evidence_ref: ArtifactRef

    def __post_init__(self) -> None:
        if type(self.identity) is not RestoreIdentity:
            raise TypeError("identity must be exact RestoreIdentity")
        for name, role in (
            ("snapshot_ref", "composite_snapshot"),
            ("restore_receipt_ref", "verifier_restore_receipt"),
            ("evidence_ref", "verifier_evidence"),
        ):
            _controller_ref(getattr(self, name), name, role=role)


@dataclass(frozen=True, slots=True)
class EvidenceExecutionPair:
    """Controller proof that grade and verify used disjoint restorations."""

    grade: GradeEvidenceReceipt
    verifier: VerifierEvidenceReceipt

    def __post_init__(self) -> None:
        if type(self.grade) is not GradeEvidenceReceipt:
            raise TypeError("grade must be exact GradeEvidenceReceipt")
        if type(self.verifier) is not VerifierEvidenceReceipt:
            raise TypeError("verifier must be exact VerifierEvidenceReceipt")
        if self.grade.snapshot_ref != self.verifier.snapshot_ref:
            raise ValueError("grade and verifier must restore the same snapshot")
        if self.grade.restore_receipt_ref == self.verifier.restore_receipt_ref:
            raise ValueError("grade and verifier restore receipts must be distinct")
        pairs = (
            (
                self.grade.identity.instance_id,
                self.verifier.identity.instance_id,
                "instance",
            ),
            (
                self.grade.identity.process_id,
                self.verifier.identity.process_id,
                "process",
            ),
            (
                self.grade.identity.writable_root_id,
                self.verifier.identity.writable_root_id,
                "writable root",
            ),
        )
        for grade_value, verifier_value, field in pairs:
            if grade_value == verifier_value:
                raise ValueError(f"grade and verifier {field} identities must differ")


@dataclass(frozen=True, slots=True)
class ProviderSettlement:
    """Pinned provider settlement for exactly one terminal attempt."""

    dispatch_intent_ref: ArtifactRef
    attempt_receipt_ref: ArtifactRef
    provider_event_ref: ArtifactRef
    settlement_ref: ArtifactRef
    cost_microunits: int

    def __post_init__(self) -> None:
        for name, role in (
            ("dispatch_intent_ref", "provider_dispatch_intent"),
            ("attempt_receipt_ref", "provider_attempt"),
            ("provider_event_ref", "provider_event"),
            ("settlement_ref", "provider_settlement"),
        ):
            _controller_ref(getattr(self, name), name, role=role)
        _nonnegative_int(self.cost_microunits, "cost_microunits")

    def validate_against(
        self,
        *,
        intent_ref: ArtifactRef,
        attempt_ref: ArtifactRef,
        attempt: ProviderCallAttemptReceipt,
    ) -> None:
        _controller_ref(
            intent_ref,
            "intent_ref",
            role="provider_dispatch_intent",
        )
        _controller_ref(attempt_ref, "attempt_ref", role="provider_attempt")
        if type(attempt) is not ProviderCallAttemptReceipt:
            raise TypeError("attempt must be exact ProviderCallAttemptReceipt")
        if (
            self.dispatch_intent_ref != intent_ref
            or self.attempt_receipt_ref != attempt_ref
            or self.provider_event_ref != attempt.provider_event_ref
        ):
            raise ValueError("provider settlement ancestry is cross-wired")


def _validate_cost_ancestry(
    *,
    intents: tuple[ProviderDispatchIntent, ...],
    intent_refs: tuple[ArtifactRef, ...],
    attempts: tuple[ProviderCallAttemptReceipt, ...],
    attempt_refs: tuple[ArtifactRef, ...],
    settlements: tuple[ProviderSettlement, ...],
) -> int:
    ProviderAttemptLedger(
        intents=intents,
        intent_refs=intent_refs,
        attempts=attempts,
    )
    _exact_tuple(
        attempt_refs,
        field="attempt_refs",
        member_type=ArtifactRef,
    )
    _exact_tuple(
        settlements,
        field="settlements",
        member_type=ProviderSettlement,
    )
    if len(attempt_refs) != len(attempts) or len(settlements) != len(attempts):
        raise ValueError("every attempt requires exactly one final settlement")
    if len(set(attempt_refs)) != len(attempt_refs):
        raise ValueError("attempt_refs must be pairwise distinct")
    for ref in attempt_refs:
        _controller_ref(ref, "attempt_refs item", role="provider_attempt")
    settlement_refs = [settlement.settlement_ref for settlement in settlements]
    if len(set(settlement_refs)) != len(settlement_refs):
        raise ValueError("settlement_refs must be pairwise distinct")
    total = 0
    for intent_ref, attempt, attempt_ref, settlement in zip(
        intent_refs,
        attempts,
        attempt_refs,
        settlements,
        strict=True,
    ):
        settlement.validate_against(
            intent_ref=intent_ref,
            attempt_ref=attempt_ref,
            attempt=attempt,
        )
        total += settlement.cost_microunits
    return total


@dataclass(frozen=True, slots=True)
class CostClosure:
    """Complete non-empty cost ancestry, derived from pinned settlements."""

    intents: tuple[ProviderDispatchIntent, ...]
    intent_refs: tuple[ArtifactRef, ...]
    attempts: tuple[ProviderCallAttemptReceipt, ...]
    attempt_refs: tuple[ArtifactRef, ...]
    settlements: tuple[ProviderSettlement, ...]
    total_cost_microunits: int

    def __post_init__(self) -> None:
        if not self.intents:
            raise ValueError(
                "zero-attempt cost requires SyntheticZeroAttemptCostClosure"
            )
        total = _validate_cost_ancestry(
            intents=self.intents,
            intent_refs=self.intent_refs,
            attempts=self.attempts,
            attempt_refs=self.attempt_refs,
            settlements=self.settlements,
        )
        _nonnegative_int(self.total_cost_microunits, "total_cost_microunits")
        if self.total_cost_microunits != total:
            raise ValueError("total cost differs from exact settlement sum")


@dataclass(frozen=True, slots=True)
class SyntheticZeroAttemptCostClosure:
    """Typed proof that no dispatch occurred and therefore exact cost is zero."""

    total_cost_microunits: Literal[0] = 0

    def __post_init__(self) -> None:
        if type(self.total_cost_microunits) is not int:
            raise TypeError("total_cost_microunits must be exact int")
        if self.total_cost_microunits != 0:
            raise ValueError("zero-attempt cost closure must equal zero")


@dataclass(frozen=True, slots=True)
class AttemptBoundZeroCostClosure:
    """Typed proof that one or more settled attempts have exact zero cost."""

    intents: tuple[ProviderDispatchIntent, ...]
    intent_refs: tuple[ArtifactRef, ...]
    attempts: tuple[ProviderCallAttemptReceipt, ...]
    attempt_refs: tuple[ArtifactRef, ...]
    settlements: tuple[ProviderSettlement, ...]
    total_cost_microunits: Literal[0] = 0

    def __post_init__(self) -> None:
        if not self.intents:
            raise ValueError("attempt-bound zero closure requires an attempt")
        total = _validate_cost_ancestry(
            intents=self.intents,
            intent_refs=self.intent_refs,
            attempts=self.attempts,
            attempt_refs=self.attempt_refs,
            settlements=self.settlements,
        )
        if type(self.total_cost_microunits) is not int:
            raise TypeError("total_cost_microunits must be exact int")
        if total != 0 or self.total_cost_microunits != 0:
            raise ValueError("attempt-bound zero closure requires exact zero cost")
