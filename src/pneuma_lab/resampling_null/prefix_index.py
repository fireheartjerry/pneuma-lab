"""Independent T5-S02D prefix-candidate reconstruction and publication."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import threading
from typing import Any, Literal, Mapping, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import validate_record
from .authority_refs import AuthorityRefReader, load_json_bytes, walk_artifact_refs
from .controller import derive_call_seed
from .controller_artifacts import ControllerArtifactResolver
from .errors import RecordValidationError
from .evidence import (
    AttemptBoundZeroCostClosure,
    CompositeSnapshotEnvelope,
    ContainerAttestation,
    ControllerProviderCostClosure,
    ControllerProviderEvent,
    ControllerProviderSettlement,
    CompletedToolBoundaryReceipt,
    GradeExecutionReceipt,
    FrozenPrefixReceipt,
    ProviderAttemptLedgerRecord,
    ProviderAttemptStatus,
    ProviderCallAttemptReceipt,
    ProviderDispatchIntent,
    ProviderSettlement,
    RuntimeAttestation,
    StatelessAttestation,
    SyntheticZeroAttemptCostClosure,
    ToolBoundaryLedger,
    VerifierExecutionReceipt,
    load_composite_snapshot,
    load_container_attestation,
    load_controller_provider_cost_closure,
    load_controller_provider_event,
    load_controller_provider_settlement,
    load_grade_execution_receipt,
    load_provider_attempt,
    load_provider_attempt_ledger,
    load_provider_dispatch_intent,
    load_runtime_attestation,
    load_stateless_attestation,
    load_tool_call,
    load_tool_boundary_ledger,
    load_verifier_execution_receipt,
)
from .execution_authority import (
    PrefixExecutionAuthority,
    _load_prefix_execution_authority_and_plan_with_reader,
    _project_prefix_execution_authority_from_plan,
)
from .prefix_contracts import (
    REF_LOAD_CLASS_BY_ROLE,
    InitialRestoreQualificationReceipt,
    SnapshotRestoreReceipt,
    SyntheticPrefixProgram,
    RawProviderObservation,
    load_initial_restore_qualification_receipt,
    load_prefix_candidate_receipt,
    load_snapshot_restore_receipt,
    load_synthetic_request_payload,
    load_synthetic_prefix_program,
    load_synthetic_tool_result_payload,
)
from .publication_rollback import (
    OwnedPublication,
    OwnedTemporary,
    rename_no_replace,
    render_rollback_residual,
    rollback_publication,
)
from .scientific_records import (
    ScientificRecord,
    ScientificRefReader,
    decode_scientific_parent,
)
from .synthetic_environment import _decode_snapshot_state
from .synthetic_prefix_loop import (
    AUTHORITY_ASSET_DECODER_BY_ROLE,
    SyntheticResponseParser,
    SyntheticGradeCodec,
    SyntheticVerifierCodec,
    _controller_nested_refs,
    _decode_raw_event,
    _validate_provider_observation,
    _reconcile_reloaded_attestations,
    _reconcile_reloaded_authority_leaves,
    _reconcile_reloaded_execution_records,
)
from .types import (
    ArtifactRef,
    CallContractCaps,
    FailureKind,
    PrefixCaps,
    ToolCall,
    TriggerReason,
)


_RESERVED_OUTPUT_ROOTS = frozenset(
    {"controller-artifacts", "controller-workspace", "prefix-environments"}
)
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC


@dataclass(slots=True)
class _CandidateGraph:
    receipt: FrozenPrefixReceipt
    authority: PrefixExecutionAuthority
    program: SyntheticPrefixProgram
    program_bytes: bytes
    payloads: dict[ArtifactRef, bytes]
    snapshot: CompositeSnapshotEnvelope
    initial_restore: InitialRestoreQualificationReceipt
    grade_restore: SnapshotRestoreReceipt
    verifier_restore: SnapshotRestoreReceipt
    grade_execution: GradeExecutionReceipt
    verifier_execution: VerifierExecutionReceipt
    provider_ledger: ProviderAttemptLedgerRecord
    cost_record: ControllerProviderCostClosure
    tool_ledger: ToolBoundaryLedger
    intents: dict[ArtifactRef, ProviderDispatchIntent]
    attempts: dict[ArtifactRef, ProviderCallAttemptReceipt]
    events: dict[ArtifactRef, ControllerProviderEvent]
    settlements: dict[ArtifactRef, ControllerProviderSettlement]
    subject_attestations: tuple[StatelessAttestation, ...]
    simulator_attestations: tuple[StatelessAttestation, ...]
    runtime_attestations: tuple[RuntimeAttestation, ...]
    container_attestations: tuple[ContainerAttestation, ...]


@dataclass(slots=True)
class _FreshTraversal:
    visited: dict[ArtifactRef, str]
    path_bindings: dict[str, ArtifactRef]
    physical_bindings: dict[tuple[int, int], ArtifactRef]
    payloads: dict[ArtifactRef, bytes]
    nested: dict[ArtifactRef, tuple[ArtifactRef, ...]]
    decoded: dict[ArtifactRef, object]
    scientific_refs: set[ArtifactRef]

    @classmethod
    def empty(cls) -> _FreshTraversal:
        return cls({}, {}, {}, {}, {}, {}, set())


@dataclass(frozen=True, slots=True)
class _OwnedPrefixPublication:
    ref: ArtifactRef
    identity: tuple[int, int]


@dataclass(slots=True)
class _SealTransactionState:
    descriptor: int
    publication: _OwnedPrefixPublication | None = None
    release_phase: Literal[
        "lock_pending",
        "lock_ambiguous",
        "unlock_pending",
        "unlock_ambiguous",
        "close_pending",
        "close_ambiguous",
        "closed",
    ] = "lock_pending"


_S02D_RELEASE_FAIL_STOP: _SealTransactionState | None = None
_S02D_PROCESS_RESERVATION = threading.Lock()


@dataclass(slots=True)
class _ClockTraceReplay:
    trace: tuple[Any, ...]
    position: int = 0
    last_value: int | None = None

    def peek_label(self) -> str | None:
        if self.position >= len(self.trace):
            return None
        return cast(str, self.trace[self.position].label)

    def consume(self, label: str) -> int:
        if self.position >= len(self.trace):
            raise ValueError(f"clock trace exhausted before {label!r}")
        read = self.trace[self.position]
        if read.label != label:
            raise ValueError(f"clock trace expected {label!r}, observed {read.label!r}")
        if self.last_value is not None and read.uint64_ms < self.last_value:
            raise ValueError("clock trace values are not chronological")
        self.position += 1
        self.last_value = read.uint64_ms
        return read.uint64_ms

    def assert_exhausted(self) -> None:
        if self.position != len(self.trace):
            raise ValueError("clock trace has unconsumed reads")


@dataclass(frozen=True, slots=True)
class _ExecutionReplayResult:
    final_elapsed_ms: int


@dataclass(frozen=True, slots=True)
class _CompletedToolTransition:
    stopped: bool
    terminal: bool
    failure_kind: FailureKind
    trigger_reason: TriggerReason
    terminal_remainder: tuple[ToolCall, ...]
    branch_pending_calls: tuple[ToolCall, ...]


@dataclass(frozen=True, slots=True)
class _ProgramReplayAuthority:
    task_id: str
    prefix_seed: int
    actor_roles: tuple[Literal["primary_subject", "user_simulator"], ...]
    prefix_caps: PrefixCaps
    simulator_caps: CallContractCaps
    subject_contract_caps: CallContractCaps
    simulator_contract_caps: CallContractCaps | None
    subject_contract_ref: ArtifactRef
    simulator_contract_ref: ArtifactRef | None


def _pretool_failure(
    *,
    before_ms: int,
    deadline_ms: int,
    completed_tools: int,
    tool_cap: int,
) -> FailureKind:
    """Apply the shared pre-tool deadline then inclusive-cap precedence."""

    if before_ms >= deadline_ms:
        return FailureKind.TIMEOUT
    if completed_tools >= tool_cap:
        return FailureKind.TOOL_CAP
    return FailureKind.NONE


def _completed_tool_transition(
    *,
    failure_kind: FailureKind,
    episode_terminal: bool,
    completion_ms: int,
    deadline_ms: int,
    token_overshoot: bool,
    cumulative_mutation: bool,
    verifier_eligible: bool,
    completed_tools: int,
    queued_remainder: tuple[ToolCall, ...],
) -> _CompletedToolTransition:
    """Apply the one authoritative completed-tool state transition."""

    if failure_kind is not FailureKind.NONE:
        return _CompletedToolTransition(
            True,
            True,
            failure_kind,
            TriggerReason.NO_INTERVENTION_OPPORTUNITY,
            queued_remainder,
            (),
        )
    if episode_terminal:
        if queued_remainder:
            raise ValueError("clean terminal tool has a queued remainder")
        return _CompletedToolTransition(
            True,
            True,
            FailureKind.NONE,
            TriggerReason.NO_INTERVENTION_OPPORTUNITY,
            (),
            (),
        )
    if completion_ms > deadline_ms:
        return _CompletedToolTransition(
            True,
            True,
            FailureKind.TIMEOUT,
            TriggerReason.NO_INTERVENTION_OPPORTUNITY,
            queued_remainder,
            (),
        )
    if token_overshoot:
        return _CompletedToolTransition(
            True,
            True,
            FailureKind.TOKEN_CAP,
            TriggerReason.NO_INTERVENTION_OPPORTUNITY,
            queued_remainder,
            (),
        )
    if cumulative_mutation and verifier_eligible:
        return _CompletedToolTransition(
            True,
            False,
            FailureKind.NONE,
            TriggerReason.FIRST_ELIGIBLE_MUTATION,
            (),
            queued_remainder,
        )
    if completed_tools == 4:
        return _CompletedToolTransition(
            True,
            False,
            FailureKind.NONE,
            TriggerReason.FOURTH_TOOL_CALL,
            (),
            queued_remainder,
        )
    return _CompletedToolTransition(
        False,
        False,
        FailureKind.NONE,
        TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        (),
        (),
    )


def _assert_program_actor_binding(
    *,
    program: SyntheticPrefixProgram,
    task_id: str,
    actor_roles: tuple[Literal["primary_subject", "user_simulator"], ...],
) -> None:
    """Bind transcript roles to the task-derived environment actor sequence."""

    if program.task_id != task_id:
        raise ValueError("program task identity differs from occurrence authority")
    if len(actor_roles) != len(program.provider_transcript):
        raise ValueError("task actor order length differs from provider transcript")
    if any(
        row.subject_role != actor_role
        for row, actor_role in zip(
            program.provider_transcript,
            actor_roles,
            strict=True,
        )
    ):
        raise ValueError("provider transcript role differs from task-derived actor")


def _exact_output_relative_path(*, root: Path, out: Path) -> str:
    if type(out) is not type(Path()):
        raise TypeError("out must be an exact platform Path")
    if not out.is_absolute():
        raise ValueError("out must be absolute")
    if Path(os.path.normpath(str(out))) != out:
        raise ValueError("out must be normalized")
    try:
        relative = out.relative_to(root)
    except ValueError as exc:
        raise ValueError("out must be strictly beneath run_root") from exc
    parts = relative.parts
    if (
        not parts
        or any(part in ("", ".", "..") for part in parts)
        or parts[0] in _RESERVED_OUTPUT_ROOTS
    ):
        raise ValueError("out is reserved, noncanonical, or not strictly beneath root")
    relative_path = PurePosixPath(*parts).as_posix()
    if root / Path(*parts) != out:
        raise ValueError("out must be an exact normalized path")
    return relative_path


def _schedule_task_ids(schedule: ScientificRecord) -> tuple[str, ...]:
    payload = cast(dict[str, object], schedule.value["payload"])
    tasks = cast(list[object], payload["tasks"])
    result: list[str] = []
    for index, value in enumerate(tasks):
        if not isinstance(value, Mapping):
            raise RecordValidationError(f"schedule task {index} is not a mapping")
        task = value.get("task")
        if not isinstance(task, Mapping) or type(task.get("task_id")) is not str:
            raise RecordValidationError(f"schedule task {index} has no exact task_id")
        result.append(cast(str, task["task_id"]))
    if not result or len(result) != len(set(result)):
        raise RecordValidationError(
            "selected schedule roster must be nonempty and unique"
        )
    return tuple(result)


def _record_physical(
    *,
    ref: ArtifactRef,
    load_class: str,
    physical: tuple[int, int],
    visited: dict[ArtifactRef, str],
    path_bindings: dict[str, ArtifactRef],
    physical_bindings: dict[tuple[int, int], ArtifactRef],
) -> None:
    previous_class = visited.get(ref)
    if previous_class is not None:
        if previous_class != load_class:
            raise ValueError("candidate ref crosses load classes")
        return
    relative = PurePosixPath(ref.relative_path)
    if (
        relative.is_absolute()
        or relative.as_posix() != ref.relative_path
        or any(part in ("", ".", "..") for part in relative.parts)
    ):
        raise ValueError("candidate graph has a noncanonical path")
    previous_path = path_bindings.get(ref.relative_path)
    if previous_path is not None and previous_path != ref:
        raise ValueError("candidate graph aliases one relative path")
    previous_physical = physical_bindings.get(physical)
    if previous_physical is not None and previous_physical != ref:
        raise ValueError("candidate graph aliases one physical file across refs")
    visited[ref] = load_class
    path_bindings[ref.relative_path] = ref
    physical_bindings[physical] = ref


def _single(values: Mapping[ArtifactRef, object], role: str) -> object:
    if len(values) != 1:
        raise ValueError(f"candidate graph must contain exactly one {role}")
    return next(iter(values.values()))


def _load_candidate_graph(
    *,
    root: Path,
    schedule_ref: ArtifactRef,
    schedule: ScientificRecord,
    expected_task_id: str,
    candidate_ref: ArtifactRef,
    authority: PrefixExecutionAuthority,
    scientific_reader: ScientificRefReader,
    resolver: ControllerArtifactResolver,
    authority_reader: AuthorityRefReader,
    traversal: _FreshTraversal,
) -> _CandidateGraph:
    if type(candidate_ref) is not ArtifactRef:
        raise TypeError("candidate_refs must contain exact ArtifactRef values")
    registered = REF_LOAD_CLASS_BY_ROLE.get(candidate_ref.role)
    if registered != ("controller_artifact", "application/json"):
        raise ValueError("candidate ref is not a registered controller artifact")
    if candidate_ref.role != "prefix_candidate_receipt":
        raise ValueError("candidate ref role must equal prefix_candidate_receipt")

    pending: list[ArtifactRef] = []
    local_seen: set[ArtifactRef] = {schedule_ref}
    candidate_bound = resolver.resolve_bound(
        candidate_ref,
        expected_role="prefix_candidate_receipt",
        expected_media_type="application/json",
    )
    receipt = cast(
        FrozenPrefixReceipt,
        load_prefix_candidate_receipt(candidate_bound.payload),
    )
    if receipt.task_id != expected_task_id:
        raise ValueError("candidate order differs from selected schedule order")
    if receipt.schedule_sha256 != schedule_ref.sha256:
        raise ValueError("candidate schedule ancestry differs")
    _record_physical(
        ref=candidate_ref,
        load_class="controller_artifact",
        physical=(candidate_bound.st_dev, candidate_bound.st_ino),
        visited=traversal.visited,
        path_bindings=traversal.path_bindings,
        physical_bindings=traversal.physical_bindings,
    )
    traversal.payloads[candidate_ref] = candidate_bound.payload
    traversal.decoded[candidate_ref] = receipt
    candidate_value = load_json_bytes(
        candidate_bound.payload,
        source=Path("<prefix-candidate-receipt>"),
    )
    candidate_nested = walk_artifact_refs(candidate_value)
    traversal.nested[candidate_ref] = candidate_nested
    pending.extend(reversed(candidate_nested))
    pending.extend(reversed(traversal.nested[schedule_ref]))
    local_seen.add(candidate_ref)

    prevalidated = authority_reader.semantically_validated_refs

    while pending:
        ref = pending.pop()
        if ref in local_seen:
            continue
        local_seen.add(ref)
        registry = REF_LOAD_CLASS_BY_ROLE.get(ref.role)
        if registry is None:
            raise ValueError(f"candidate graph has unknown role {ref.role!r}")
        load_class, expected = registry
        if ref in traversal.visited:
            if traversal.visited[ref] != load_class:
                raise ValueError("candidate ref crosses load classes")
            pending.extend(reversed(traversal.nested[ref]))
            continue
        if load_class == "controller_artifact":
            bound = resolver.resolve_bound(
                ref,
                expected_role=ref.role,
                expected_media_type=expected,
            )
            payload = bound.payload
            nested = _controller_nested_refs(ref.role, payload)
            if ref.role == "composite_snapshot":
                traversal.decoded[ref] = load_composite_snapshot(payload)
            elif ref.role == "initial_restore_qualification":
                traversal.decoded[ref] = load_initial_restore_qualification_receipt(
                    payload
                )
            elif ref.role == "grade_restore_receipt":
                traversal.decoded[ref] = load_snapshot_restore_receipt(payload)
            elif ref.role == "verifier_restore_receipt":
                traversal.decoded[ref] = load_snapshot_restore_receipt(payload)
            elif ref.role == "grade_evidence_receipt":
                traversal.decoded[ref] = load_grade_execution_receipt(payload)
            elif ref.role == "verifier_evidence_receipt":
                traversal.decoded[ref] = load_verifier_execution_receipt(payload)
            elif ref.role == "provider_dispatch_intent":
                traversal.decoded[ref] = load_provider_dispatch_intent(payload)
            elif ref.role == "provider_attempt":
                traversal.decoded[ref] = load_provider_attempt(payload)
            elif ref.role == "provider_event":
                traversal.decoded[ref] = load_controller_provider_event(payload)
            elif ref.role == "provider_settlement":
                traversal.decoded[ref] = load_controller_provider_settlement(payload)
            elif ref.role == "provider_attempt_ledger":
                traversal.decoded[ref] = load_provider_attempt_ledger(payload)
            elif ref.role == "provider_cost_closure":
                traversal.decoded[ref] = load_controller_provider_cost_closure(payload)
            elif ref.role == "tool_boundary_ledger":
                traversal.decoded[ref] = load_tool_boundary_ledger(payload)
            elif ref.role == "subject_stateless_attestation":
                traversal.decoded[ref] = load_stateless_attestation(
                    payload,
                    expected_role="primary_subject",
                )
            elif ref.role == "simulator_stateless_attestation":
                traversal.decoded[ref] = load_stateless_attestation(
                    payload,
                    expected_role="user_simulator",
                )
            elif ref.role == "runtime_attestation":
                traversal.decoded[ref] = load_runtime_attestation(payload)
            elif ref.role == "container_attestation":
                traversal.decoded[ref] = load_container_attestation(payload)
        elif load_class == "authority_asset":
            if ref.media_type != expected:
                raise ValueError("authority asset media differs from registry")
            bound = authority_reader.read_bound(ref)
            payload = bound.payload
            value: object | None = None
            if ref.media_type == "application/json":
                value = load_json_bytes(payload, source=root / ref.relative_path)
                if payload != canonical_json_bytes(value, indent=None):
                    raise ValueError("authority asset must be compact canonical JSON")
                if ref.role == "synthetic_execution_program":
                    traversal.decoded[ref] = load_synthetic_prefix_program(payload)
            decoder = AUTHORITY_ASSET_DECODER_BY_ROLE.get(ref.role)
            if decoder is None:
                raise ValueError(f"authority asset has no decoder for {ref.role!r}")
            nested = decoder(ref, payload, value, prevalidated)
        else:
            if ref.media_type != "application/json":
                raise ValueError("scientific parent media or kind differs")
            bound = scientific_reader.read_bound(ref)
            record = decode_scientific_parent(
                ref,
                bound,
                run_root=root,
                field=ref.role,
                expected_kind=expected,
            )
            if ref.role != "power_report":
                traversal.scientific_refs.add(ref)
            payload = bound.payload
            # The schedule seal already validated the power final's complete
            # upstream ancestry. Prefix-index replay binds that final but does
            # not reopen the separate power-contract namespace.
            nested = () if ref.role == "power_report" else walk_artifact_refs(record.value)
        traversal.payloads[ref] = payload
        traversal.nested[ref] = nested
        _record_physical(
            ref=ref,
            load_class=load_class,
            physical=(bound.st_dev, bound.st_ino),
            visited=traversal.visited,
            path_bindings=traversal.path_bindings,
            physical_bindings=traversal.physical_bindings,
        )
        pending.extend(reversed(nested))

    local_programs = {
        ref: value
        for ref, value in traversal.decoded.items()
        if ref in local_seen and ref.role == "synthetic_execution_program"
    }
    if authority.program_ref not in local_programs:
        raise ValueError("candidate program coverage differs from task authority")
    program = cast(SyntheticPrefixProgram, local_programs[authority.program_ref])
    local_payloads = {
        ref: payload for ref, payload in traversal.payloads.items() if ref in local_seen
    }

    def decoded_for(role: str) -> dict[ArtifactRef, object]:
        return {
            ref: value
            for ref, value in traversal.decoded.items()
            if ref in local_seen and ref.role == role
        }

    return _CandidateGraph(
        receipt=receipt,
        authority=authority,
        program=program,
        program_bytes=local_payloads[authority.program_ref],
        payloads=local_payloads,
        snapshot=cast(
            CompositeSnapshotEnvelope,
            _single(decoded_for("composite_snapshot"), "snapshot"),
        ),
        initial_restore=cast(
            InitialRestoreQualificationReceipt,
            _single(
                decoded_for("initial_restore_qualification"),
                "initial restore qualification",
            ),
        ),
        grade_restore=cast(
            SnapshotRestoreReceipt,
            _single(decoded_for("grade_restore_receipt"), "grade restore receipt"),
        ),
        verifier_restore=cast(
            SnapshotRestoreReceipt,
            _single(
                decoded_for("verifier_restore_receipt"),
                "verifier restore receipt",
            ),
        ),
        grade_execution=cast(
            GradeExecutionReceipt,
            _single(
                decoded_for("grade_evidence_receipt"),
                "grade execution receipt",
            ),
        ),
        verifier_execution=cast(
            VerifierExecutionReceipt,
            _single(
                decoded_for("verifier_evidence_receipt"),
                "verifier execution receipt",
            ),
        ),
        provider_ledger=cast(
            ProviderAttemptLedgerRecord,
            _single(
                decoded_for("provider_attempt_ledger"),
                "provider attempt ledger",
            ),
        ),
        cost_record=cast(
            ControllerProviderCostClosure,
            _single(
                decoded_for("provider_cost_closure"),
                "provider cost closure",
            ),
        ),
        tool_ledger=cast(
            ToolBoundaryLedger,
            _single(
                decoded_for("tool_boundary_ledger"),
                "tool boundary ledger",
            ),
        ),
        intents=cast(
            dict[ArtifactRef, ProviderDispatchIntent],
            decoded_for("provider_dispatch_intent"),
        ),
        attempts=cast(
            dict[ArtifactRef, ProviderCallAttemptReceipt],
            decoded_for("provider_attempt"),
        ),
        events=cast(
            dict[ArtifactRef, ControllerProviderEvent], decoded_for("provider_event")
        ),
        settlements=cast(
            dict[ArtifactRef, ControllerProviderSettlement],
            decoded_for("provider_settlement"),
        ),
        subject_attestations=cast(
            tuple[StatelessAttestation, ...],
            tuple(decoded_for("subject_stateless_attestation").values()),
        ),
        simulator_attestations=cast(
            tuple[StatelessAttestation, ...],
            tuple(decoded_for("simulator_stateless_attestation").values()),
        ),
        runtime_attestations=cast(
            tuple[RuntimeAttestation, ...],
            tuple(decoded_for("runtime_attestation").values()),
        ),
        container_attestations=cast(
            tuple[ContainerAttestation, ...],
            tuple(decoded_for("container_attestation").values()),
        ),
    )


def _assert_ancestry_and_restores(graph: _CandidateGraph) -> None:
    receipt = graph.receipt
    authority = graph.authority
    snapshot = graph.snapshot
    if receipt.prefix_caps != authority.prefix_caps:
        raise ValueError("candidate prefix caps differ from schedule authority")
    expected_snapshot_ancestry = (
        (snapshot.study_ref, authority.manifest_ref, "manifest"),
        (snapshot.schedule_ref, authority.schedule_ref, "schedule"),
        (snapshot.task_input_ref, authority.task_input_ref, "task input"),
        (
            snapshot.environment_contract_ref,
            authority.environment_contract_ref,
            "environment contract",
        ),
        (
            snapshot.isolation_contract_ref,
            authority.isolation_contract_ref,
            "isolation contract",
        ),
    )
    for observed, expected, field in expected_snapshot_ancestry:
        if observed != expected:
            raise ValueError(f"snapshot {field} ancestry differs")
    if snapshot.source_revision_ref not in authority.source_revision_refs:
        raise ValueError("snapshot source revision is not manifest-authorized")
    selected_payload = graph.payloads[snapshot.task_ref]
    schedule_mapping = cast(
        Mapping[str, object],
        load_json_bytes(
            graph.payloads[authority.schedule_ref],
            source=Path("<fresh-schedule>"),
        ),
    )
    schedule_payload = cast(Mapping[str, object], schedule_mapping["payload"])
    schedule_tasks = cast(
        list[object],
        schedule_payload["tasks"],
    )
    matching = [
        item
        for item in schedule_tasks
        if isinstance(item, Mapping)
        and isinstance(item.get("task"), Mapping)
        and cast(Mapping[str, object], item["task"]).get("task_id") == receipt.task_id
    ]
    if len(matching) != 1 or selected_payload != canonical_json_bytes(
        matching[0],
        indent=None,
    ):
        raise ValueError("selected-task controller bytes differ from schedule row")

    receipt.validate_snapshot_bytes(
        graph.payloads[receipt.snapshot_ref],
        simulator_caps=authority.simulator_contract_caps,
        observed_simulator_turns=(
            None
            if authority.simulator_contract_caps is None
            else _parsed_response_turn_count(
                program=graph.program,
                payloads=graph.payloads,
                subject_role="user_simulator",
            )
        ),
    )
    final_state = _decode_snapshot_state(
        graph.payloads[snapshot.environment_snapshot_ref]
    )
    _assert_mutation_semantics(
        boundaries=graph.tool_ledger.boundaries,
        final_edge_mutation=final_state.mutation_committed,
        snapshot_cumulative=snapshot.cumulative_mutation,
    )
    expected_program_sha256 = hashlib.sha256(graph.program_bytes).hexdigest()
    if final_state.program_sha256 != expected_program_sha256:
        raise ValueError("environment snapshot program ancestry differs")
    if (
        final_state.visible_context != graph.payloads[receipt.visible_context_ref]
        or final_state.branch_pending_calls != receipt.branch_pending_calls
        or final_state.terminal_unexecuted_remainder
        != receipt.terminal_unexecuted_remainder
        or final_state.episode_terminal != snapshot.episode_terminal
        or final_state.failure_kind is not receipt.terminal_failure_kind
    ):
        raise ValueError("environment snapshot state differs from composite receipt")
    token_value = load_json_bytes(
        graph.payloads[receipt.token_ids_ref],
        source=Path("<token-ids>"),
    )
    if token_value != {"token_ids": list(final_state.visible_context)}:
        raise ValueError("token IDs differ from byte-tokenized visible context")

    initial = graph.initial_restore
    if snapshot.initial_restore_qualification_ref not in graph.payloads:
        raise ValueError("snapshot initial restore qualification is unreachable")
    common_initial = (
        (initial.schedule_ref, authority.schedule_ref),
        (initial.task_ref, snapshot.task_ref),
        (initial.task_input_ref, authority.task_input_ref),
        (initial.environment_contract_ref, authority.environment_contract_ref),
        (initial.isolation_contract_ref, authority.isolation_contract_ref),
    )
    if any(left != right for left, right in common_initial):
        raise ValueError("initial restore qualification ancestry differs")
    initial_state = _decode_snapshot_state(
        graph.payloads[initial.initial_environment_snapshot_ref]
    )
    if (
        initial_state.program_sha256 != expected_program_sha256
        or initial_state.visible_context != graph.payloads[initial.visible_context_ref]
        or initial_state.branch_pending_calls != initial.branch_pending_calls
        or initial_state.terminal_unexecuted_remainder
        != initial.terminal_unexecuted_remainder
        or initial_state.episode_terminal is not initial.episode_terminal
        or initial_state.failure_kind is not initial.failure_kind
        or initial_state.mutation_committed
        or initial_state.verifier_eligible
    ):
        raise ValueError("initial restore state differs from decoded evidence")
    initial_tokens = load_json_bytes(
        graph.payloads[initial.token_ids_ref],
        source=Path("<initial-token-ids>"),
    )
    if initial_tokens != {"token_ids": list(initial_state.visible_context)}:
        raise ValueError("initial token IDs differ from visible context")

    if graph.grade_execution.restore_receipt_ref not in graph.payloads or (
        graph.verifier_execution.restore_receipt_ref not in graph.payloads
    ):
        raise ValueError("execution receipt restore edge is unreachable")
    if (
        graph.grade_execution.restore_receipt_ref
        != next(ref for ref in graph.payloads if ref.role == "grade_restore_receipt")
        or graph.verifier_execution.restore_receipt_ref
        != next(ref for ref in graph.payloads if ref.role == "verifier_restore_receipt")
        or graph.grade_execution.grade_evidence_ref != receipt.y0_grade.artifact_ref
        or graph.verifier_execution.verifier_evidence_ref
        != receipt.verifier_receipt.verifier_artifact_ref
    ):
        raise ValueError("grade/verifier execution ancestry differs from prefix")

    for restore, purpose in (
        (graph.grade_restore, "grade"),
        (graph.verifier_restore, "verify"),
    ):
        restore_comparisons = (
            (restore.purpose, purpose),
            (restore.schedule_ref, authority.schedule_ref),
            (restore.task_ref, snapshot.task_ref),
            (restore.task_input_ref, authority.task_input_ref),
            (restore.environment_contract_ref, authority.environment_contract_ref),
            (restore.isolation_contract_ref, authority.isolation_contract_ref),
            (restore.composite_snapshot_ref, receipt.snapshot_ref),
            (restore.environment_snapshot_ref, snapshot.environment_snapshot_ref),
            (restore.visible_context_ref, receipt.visible_context_ref),
            (restore.token_ids_ref, receipt.token_ids_ref),
            (restore.branch_pending_calls, receipt.branch_pending_calls),
            (
                restore.terminal_unexecuted_remainder,
                receipt.terminal_unexecuted_remainder,
            ),
            (restore.episode_terminal, snapshot.episode_terminal),
            (restore.failure_kind, receipt.terminal_failure_kind),
        )
        if any(left != right for left, right in restore_comparisons):
            raise ValueError(f"{purpose} restore ancestry or state differs")

    identities = (
        initial.live_identity,
        initial.fresh_restore_identity,
        graph.grade_restore.restored_identity,
        graph.verifier_restore.restored_identity,
    )
    if (
        len({item.child_pid for item in identities}) != len(identities)
        or len(
            {
                (item.writable_root_st_dev, item.writable_root_st_ino)
                for item in identities
            }
        )
        != len(identities)
        or len({item.writable_root_relative_path for item in identities})
        != len(identities)
    ):
        raise ValueError("initial/live/grade/verifier restores are not isolated")


def _parsed_response_turn_count(
    *,
    program: SyntheticPrefixProgram,
    payloads: Mapping[ArtifactRef, bytes],
    subject_role: str,
) -> int:
    """Count parser-valid turns even when transport/deadline status is adverse."""

    return sum(
        1
        for row in program.provider_transcript
        if row.subject_role == subject_role
        and row.response_ref is not None
        and SyntheticResponseParser().parse(payloads[row.response_ref])[1] is not None
    )


def _assert_mutation_semantics(
    *,
    boundaries: tuple[CompletedToolBoundaryReceipt, ...],
    final_edge_mutation: bool,
    snapshot_cumulative: bool,
) -> None:
    """Separate edge-local final state from cumulative mutation history."""

    expected_final = boundaries[-1].mutation_committed if boundaries else False
    expected_cumulative = any(boundary.mutation_committed for boundary in boundaries)
    if final_edge_mutation is not expected_final:
        raise ValueError("final edge-local mutation state differs")
    if snapshot_cumulative is not expected_cumulative:
        raise ValueError("snapshot cumulative mutation state differs")


def _cost_closure(
    graph: _CandidateGraph,
) -> AttemptBoundZeroCostClosure | SyntheticZeroAttemptCostClosure:
    ledger = graph.provider_ledger
    if not ledger.ledger.attempts:
        if graph.cost_record.attempt_refs or graph.cost_record.settlement_refs:
            raise ValueError("zero-attempt candidate has nonempty cost closure")
        return SyntheticZeroAttemptCostClosure()
    if len(graph.cost_record.settlement_refs) != len(ledger.ledger.attempts):
        raise ValueError("settlement coverage differs from provider attempts")
    settlements: list[ProviderSettlement] = []
    for intent_ref, attempt_ref, attempt, settlement_ref in zip(
        ledger.ledger.intent_refs,
        ledger.attempt_refs,
        ledger.ledger.attempts,
        graph.cost_record.settlement_refs,
        strict=True,
    ):
        record = graph.settlements.get(settlement_ref)
        if record is None:
            raise ValueError("cost closure settlement is unreachable")
        settlements.append(
            ProviderSettlement(
                dispatch_intent_ref=intent_ref,
                attempt_receipt_ref=attempt_ref,
                provider_event_ref=attempt.provider_event_ref,
                settlement_ref=settlement_ref,
                cost_microunits=record.cost_microunits,
            )
        )
    return AttemptBoundZeroCostClosure(
        intents=ledger.ledger.intents,
        intent_refs=ledger.ledger.intent_refs,
        attempts=ledger.ledger.attempts,
        attempt_refs=ledger.attempt_refs,
        settlements=tuple(settlements),
        total_cost_microunits=graph.cost_record.total_cost_microunits,
    )


def _provider_failure(status: ProviderAttemptStatus) -> FailureKind:
    return {
        ProviderAttemptStatus.COMPLETED: FailureKind.NONE,
        ProviderAttemptStatus.TIMEOUT_NO_RESPONSE: FailureKind.TIMEOUT,
        ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE: FailureKind.TIMEOUT,
        ProviderAttemptStatus.REFUSAL: FailureKind.REFUSAL,
        ProviderAttemptStatus.MALFORMED_RESPONSE: FailureKind.MALFORMED_ACTION,
        ProviderAttemptStatus.PROVIDER_ERROR: FailureKind.MODEL,
        ProviderAttemptStatus.INFRASTRUCTURE_ERROR: FailureKind.INFRASTRUCTURE,
    }[status]


def _assert_exact_execution_replay(graph: _CandidateGraph) -> _ExecutionReplayResult:
    """Replay the named meter and state machine without lookup-table collapse."""

    authority = graph.authority
    program = graph.program
    receipt = graph.receipt
    ledger = graph.provider_ledger.ledger
    _assert_program_actor_binding(
        program=program,
        task_id=authority.task_schedule.task.task_id,
        actor_roles=authority.actor_roles,
    )
    replay = _ClockTraceReplay(program.clock_trace)
    prefix_epoch = replay.consume("prefix_epoch")
    deadline = prefix_epoch + authority.prefix_caps.wall_clock_ms
    boundaries = graph.tool_ledger.boundaries
    boundary_position = 0
    observation_position = 0
    derived_tokens = {"primary_subject": 0, "user_simulator": 0}
    derived_calls = {"primary_subject": 0, "user_simulator": 0}
    derived_turns = {"primary_subject": 0, "user_simulator": 0}
    cumulative_mutation = False
    trigger = TriggerReason.NO_INTERVENTION_OPPORTUNITY
    failure = FailureKind.NONE
    branch: tuple[ToolCall, ...] = ()
    remainder: tuple[ToolCall, ...] = ()
    terminal_state = (
        False
        if graph.initial_restore is None
        else graph.initial_restore.episode_terminal
    )
    initial_failure = (
        FailureKind.NONE
        if graph.initial_restore is None
        else graph.initial_restore.failure_kind
    )
    if initial_failure is not FailureKind.NONE:
        terminal_state = True
    initial_snapshot_ref = (
        None
        if graph.initial_restore is None
        else getattr(
            graph.initial_restore,
            "initial_environment_snapshot_ref",
            None,
        )
    )
    if initial_snapshot_ref is not None:
        if type(initial_snapshot_ref) is not ArtifactRef:
            raise TypeError("initial environment snapshot ref must be exact")
        initial_state = _decode_snapshot_state(graph.payloads[initial_snapshot_ref])
        expected_initial_simulator = (
            bool(authority.actor_roles) and authority.actor_roles[0] == "user_simulator"
        )
        if (
            initial_state.simulator_context is not None
        ) is not expected_initial_simulator:
            raise ValueError(
                "initial simulator context differs from task-derived actor"
            )
    if rows := program.provider_transcript:
        if terminal_state or initial_failure is not FailureKind.NONE:
            raise ValueError("initial terminal or failed restore cannot dispatch")
    else:
        failure = initial_failure
    stopped = False
    for row_index, (row, intent, attempt) in enumerate(
        zip(rows, ledger.intents, ledger.attempts, strict=True)
    ):
        if stopped:
            raise ValueError("provider transcript continues after terminal outcome")
        expected_seed = derive_call_seed(
            authority.task_schedule.prefix_seed,
            row.subject_role,
            row.call_index,
        )
        if row.seed != expected_seed:
            raise ValueError("program provider seed differs from schedule derivation")
        before = replay.consume(f"before_{row.subject_role}_{row.call_index}")
        completion = replay.consume(f"after_{row.subject_role}_{row.call_index}")
        if before > completion:
            raise ValueError("provider before clock exceeds completion clock")
        if intent.absolute_deadline_ms != deadline:
            raise ValueError(
                "provider intent deadline differs from exact prefix deadline"
            )
        raw_response = (
            None if row.response_ref is None else graph.payloads[row.response_ref]
        )
        validated = _validate_provider_observation(
            observation=RawProviderObservation(
                subject_role=row.subject_role,
                call_index=row.call_index,
                seed=row.seed,
                model_contract_sha256=row.model_contract_sha256,
                response_bytes=raw_response,
                typed_turn=row.typed_turn,
                reported_output_token_ids=row.reported_output_token_ids,
                reported_generated_tokens=row.reported_generated_tokens,
                provider_event_bytes=graph.payloads[row.provider_event_ref],
                completion_kind=row.completion_kind,
            ),
            expected_role=intent.subject_role,
            expected_call_index=intent.call_index,
            expected_seed=intent.seed,
            expected_model_sha256=intent.model_contract_ref.sha256,
            deadline_ms=deadline,
            completion_ms=completion,
        )
        if (
            attempt.seed != expected_seed
            or attempt.status is not validated.status
            or attempt.elapsed_ms != max(0, completion - prefix_epoch)
        ):
            raise ValueError("provider attempt differs from exact seed/status/clock")
        caps = (
            authority.subject_contract_caps
            if row.subject_role == "primary_subject"
            else authority.simulator_contract_caps
        )
        if caps is None:
            raise ValueError("simulator row lacks simulator authority")
        lane_token_cap = (
            authority.prefix_caps.generated_tokens
            if row.subject_role == "primary_subject"
            else authority.simulator_caps.aggregate_generated_tokens
        )
        lane_call_cap = (
            authority.prefix_caps.model_calls
            if row.subject_role == "primary_subject"
            else authority.simulator_caps.aggregate_model_calls
        )
        if (
            before >= deadline
            or caps.per_call_turns == 0
            or derived_tokens[row.subject_role]
            >= min(lane_token_cap, caps.aggregate_generated_tokens)
            or derived_calls[row.subject_role]
            >= min(lane_call_cap, caps.aggregate_model_calls)
            or derived_turns[row.subject_role] >= caps.aggregate_turns
        ):
            raise ValueError("provider dispatch follows an exhausted allowance")
        derived_calls[row.subject_role] += 1
        derived_tokens[row.subject_role] += validated.generated_tokens
        if validated.typed_turn is not None:
            derived_turns[row.subject_role] += 1
        pending = (
            () if validated.typed_turn is None else validated.typed_turn.tool_calls
        )
        failure = _provider_failure(validated.status)
        if failure is FailureKind.NONE and completion > deadline:
            failure = FailureKind.TIMEOUT
        if failure is FailureKind.NONE and (
            validated.generated_tokens > caps.per_call_generated_tokens
            or derived_tokens[row.subject_role]
            > min(lane_token_cap, caps.aggregate_generated_tokens)
        ):
            failure = FailureKind.TOKEN_CAP
        if failure is not FailureKind.NONE:
            remainder = pending
            terminal_state = True
            stopped = True
        elif validated.typed_turn is None:
            raise ValueError("completed provider row lacks a parsed turn")
        elif validated.typed_turn.finish_reason == "terminal":
            if pending:
                raise ValueError("terminal provider turn cannot contain tools")
            terminal_state = True
            stopped = True
        elif row.subject_role == "primary_subject":
            queue = validated.typed_turn.tool_calls
            for tool_index, call in enumerate(queue):
                pending = queue[tool_index:]
                before_tool = replay.consume(f"before_tool_{call.call_id}")
                pretool_failure = _pretool_failure(
                    before_ms=before_tool,
                    deadline_ms=deadline,
                    completed_tools=boundary_position,
                    tool_cap=authority.prefix_caps.tool_calls,
                )
                if pretool_failure is not FailureKind.NONE:
                    failure = pretool_failure
                    remainder = pending
                    terminal_state = True
                    stopped = True
                    break
                if boundary_position >= len(boundaries):
                    raise ValueError("tool queue lacks an executed boundary")
                if observation_position >= len(program.tool_observations):
                    raise ValueError("tool observation program is exhausted")
                boundary = boundaries[boundary_position]
                observation = program.tool_observations[observation_position]
                if (
                    boundary.call_id != call.call_id
                    or observation.call_id != call.call_id
                    or boundary.tool_result_ref.sha256 != observation.result_ref.sha256
                    or boundary.mutation_committed is not observation.mutation_committed
                    or boundary.verifier_eligible_after
                    is not observation.verifier_eligible
                    or boundary.episode_terminal is not observation.episode_terminal
                    or boundary.failure_kind is not observation.failure_kind
                ):
                    raise ValueError(
                        "tool boundary/observation differs from exact queue"
                    )
                completion_tool = replay.consume(f"after_tool_{call.call_id}")
                if before_tool > completion_tool:
                    raise ValueError("tool before clock exceeds completion clock")
                if boundary.elapsed_ms != max(0, completion_tool - prefix_epoch):
                    raise ValueError("tool boundary elapsed differs from clock trace")
                boundary_position += 1
                observation_position += 1
                cumulative_mutation = cumulative_mutation or boundary.mutation_committed
                after_remainder = queue[tool_index + 1 :]
                transition = _completed_tool_transition(
                    failure_kind=boundary.failure_kind,
                    episode_terminal=boundary.episode_terminal,
                    completion_ms=completion_tool,
                    deadline_ms=deadline,
                    token_overshoot=(
                        derived_tokens["primary_subject"]
                        > min(
                            authority.prefix_caps.generated_tokens,
                            authority.subject_contract_caps.aggregate_generated_tokens,
                        )
                    ),
                    cumulative_mutation=cumulative_mutation,
                    verifier_eligible=boundary.verifier_eligible_after,
                    completed_tools=boundary_position,
                    queued_remainder=after_remainder,
                )
                if transition.stopped:
                    failure = transition.failure_kind
                    trigger = transition.trigger_reason
                    remainder = transition.terminal_remainder
                    branch = transition.branch_pending_calls
                    terminal_state = transition.terminal
                    stopped = True
                    break
        if stopped and row_index != len(rows) - 1:
            raise ValueError("provider transcript continues after terminal outcome")
    replay.assert_exhausted()
    if boundary_position != len(boundaries):
        raise ValueError("tool boundary ledger has unconsumed rows")
    if observation_position != len(program.tool_observations):
        raise ValueError("tool observation program has unconsumed rows")
    if (
        receipt.trigger_reason is not trigger
        or program.expected_trigger_reason is not trigger
        or receipt.terminal_failure_kind is not failure
        or receipt.branch_pending_calls != branch
        or receipt.terminal_unexecuted_remainder != remainder
    ):
        raise ValueError("fresh replay outcome differs from exact chronology")
    if graph.snapshot.episode_terminal is not terminal_state:
        raise ValueError("terminal replay differs from final snapshot")
    if terminal_state and trigger is not TriggerReason.NO_INTERVENTION_OPPORTUNITY:
        raise ValueError("clean terminal boundary cannot produce a branch trigger")
    final_clock = replay.last_value
    if final_clock is None:
        raise AssertionError("exact replay consumed no prefix clock")
    return _ExecutionReplayResult(max(0, final_clock - prefix_epoch))


def _assert_execution_semantics(graph: _CandidateGraph) -> None:
    receipt = graph.receipt
    authority = graph.authority
    program = graph.program
    ledger = graph.provider_ledger
    cost_closure = _cost_closure(graph)
    replay_result = _assert_exact_execution_replay(graph)
    _reconcile_reloaded_execution_records(
        authority=authority,
        program=program,
        expected_cost_closure=cost_closure,
        expected_boundaries=graph.tool_ledger.boundaries,
        ledger=ledger,
        intents_by_ref=graph.intents,
        attempts_by_ref=graph.attempts,
        events_by_ref=graph.events,
        settlements_by_ref=graph.settlements,
        cost_record=graph.cost_record,
        tool_ledger=graph.tool_ledger,
        tool_calls_by_ref={
            boundary.tool_call_ref: load_tool_call(
                graph.payloads[boundary.tool_call_ref]
            )
            for boundary in graph.tool_ledger.boundaries
        },
    )
    identities = [
        (attempt.subject_role, attempt.call_index) for attempt in ledger.ledger.attempts
    ]
    program_identities = [
        (row.subject_role, row.call_index) for row in program.provider_transcript
    ]
    if identities != program_identities:
        raise ValueError("provider ledger order differs from program chronology")
    attempt_elapsed = [attempt.elapsed_ms for attempt in ledger.ledger.attempts]
    boundary_elapsed = [
        boundary.elapsed_ms for boundary in graph.tool_ledger.boundaries
    ]
    if attempt_elapsed != sorted(attempt_elapsed) or boundary_elapsed != sorted(
        boundary_elapsed
    ):
        raise ValueError("execution elapsed chronology is not monotonic")

    primary_attempts = [
        attempt
        for attempt in ledger.ledger.attempts
        if attempt.subject_role == "primary_subject"
    ]
    simulator_attempts = [
        attempt
        for attempt in ledger.ledger.attempts
        if attempt.subject_role == "user_simulator"
    ]
    expected_counters = (
        (
            receipt.counters.model_calls,
            len(primary_attempts),
            "primary model calls",
        ),
        (
            receipt.counters.generated_tokens,
            sum(item.generated_tokens for item in primary_attempts),
            "primary generated tokens",
        ),
        (
            receipt.counters.tool_calls,
            len(graph.tool_ledger.boundaries),
            "completed tool calls",
        ),
        (
            receipt.simulator_counters.model_calls,
            len(simulator_attempts),
            "simulator model calls",
        ),
        (
            receipt.simulator_counters.generated_tokens,
            sum(item.generated_tokens for item in simulator_attempts),
            "simulator generated tokens",
        ),
    )
    for observed, expected, field in expected_counters:
        if observed != expected:
            raise ValueError(f"{field} differs from decoded evidence")
    expected_seeds = tuple(
        (intent.subject_role, intent.call_index, intent.seed)
        for intent in ledger.ledger.intents
    )
    observed_seeds = tuple(
        (seed.subject_role, seed.call_index, seed.seed) for seed in receipt.call_seeds
    )
    if observed_seeds != expected_seeds:
        raise ValueError("call-seed receipts differ from dispatch evidence")
    if (
        receipt.counters.wall_clock_ms != replay_result.final_elapsed_ms
        or receipt.simulator_counters.wall_clock_ms != replay_result.final_elapsed_ms
    ):
        raise ValueError("wall-clock counter differs from execution chronology")


def _assert_raw_and_attestation_semantics(graph: _CandidateGraph) -> None:
    program = graph.program
    expected_request_refs = {
        row.expected_request_ref for row in program.provider_transcript
    }
    expected_response_refs = {
        row.response_ref
        for row in program.provider_transcript
        if row.response_ref is not None
    }
    expected_event_refs = {
        row.provider_event_ref for row in program.provider_transcript
    }
    expected_tool_refs = {item.result_ref for item in program.tool_observations}
    requests = {}
    responses = {}
    raw_events = {}
    tool_results = {}
    for ref, payload in graph.payloads.items():
        if ref in expected_request_refs:
            from .prefix_contracts import load_synthetic_request_payload

            requests[ref] = load_synthetic_request_payload(payload)
        elif ref in expected_response_refs:
            from .synthetic_prefix_loop import SyntheticResponseParser

            responses[ref] = SyntheticResponseParser().parse(payload)
        elif ref in expected_event_refs:
            raw_events[ref] = _decode_raw_event(payload)
        elif ref in expected_tool_refs:
            from .prefix_contracts import load_synthetic_tool_result_payload

            tool_results[ref] = load_synthetic_tool_result_payload(payload)
    grade_source = program.grade_result.evidence_ref
    verifier_source = program.verifier_result.evidence_ref
    grade_payload = graph.payloads[graph.grade_execution.grade_evidence_ref]
    verifier_payload = graph.payloads[graph.verifier_execution.verifier_evidence_ref]
    grade = SyntheticGradeCodec().decode(
        payload=grade_payload,
        program=program,
        expected_payload=graph.payloads[grade_source],
    )
    verifier = SyntheticVerifierCodec().decode(
        payload=verifier_payload,
        program=program,
        expected_payload=graph.payloads[verifier_source],
    )
    _reconcile_reloaded_authority_leaves(
        program=program,
        requests=requests,
        responses=responses,
        raw_events=raw_events,
        tool_results=tool_results,
        grade_results={grade_source: grade},
        verifier_results={verifier_source: verifier},
    )
    receipt = graph.receipt
    adverse = (
        receipt.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY
        and receipt.terminal_failure_kind is not FailureKind.NONE
    )
    if (
        receipt.y0_grade.success != (0 if adverse else grade.success)
        or receipt.y0_grade.partial_reward != (0.0 if adverse else grade.partial_reward)
        or receipt.y0_grade.infrastructure_failure is not grade.infrastructure_failure
        or receipt.verifier_receipt.finding_count != verifier.finding_count
    ):
        raise ValueError("scientific grade/verifier values differ from raw evidence")
    if (
        len(graph.subject_attestations) != 1
        or len(graph.simulator_attestations)
        != (0 if graph.authority.simulator_contract_ref is None else 1)
        or len(graph.runtime_attestations) != 1
        or len(graph.container_attestations) != 1
    ):
        raise ValueError("candidate attestation coverage differs")
    _reconcile_reloaded_attestations(
        authority=graph.authority,
        program=program,
        program_bytes=graph.program_bytes,
        subject=graph.subject_attestations[0],
        simulator=(
            None
            if not graph.simulator_attestations
            else graph.simulator_attestations[0]
        ),
        runtime=graph.runtime_attestations[0],
        container=graph.container_attestations[0],
    )


def _validate_candidate(graph: _CandidateGraph) -> None:
    _assert_ancestry_and_restores(graph)
    _assert_execution_semantics(graph)
    _assert_raw_and_attestation_semantics(graph)


def _assert_all_program_occurrences(
    traversal: _FreshTraversal,
    *,
    program_authorities: Mapping[
        ArtifactRef,
        tuple[_ProgramReplayAuthority, ...],
    ],
) -> None:
    """Reconcile every manifest-reachable program, including non-selected rows."""

    programs = {
        ref: cast(SyntheticPrefixProgram, value)
        for ref, value in traversal.decoded.items()
        if ref.role == "synthetic_execution_program"
    }
    if set(program_authorities) != set(programs):
        raise ValueError("program occurrence authority coverage differs")
    for program_ref, program in programs.items():
        request_refs = {row.expected_request_ref for row in program.provider_transcript}
        response_refs = {
            row.response_ref
            for row in program.provider_transcript
            if row.response_ref is not None
        }
        event_refs = {row.provider_event_ref for row in program.provider_transcript}
        tool_refs = {row.result_ref for row in program.tool_observations}
        grade_ref = program.grade_result.evidence_ref
        verifier_ref = program.verifier_result.evidence_ref
        requests = {
            ref: load_synthetic_request_payload(traversal.payloads[ref])
            for ref in request_refs
        }
        responses = {
            ref: SyntheticResponseParser().parse(traversal.payloads[ref])
            for ref in response_refs
        }
        raw_events = {
            ref: _decode_raw_event(traversal.payloads[ref]) for ref in event_refs
        }
        tool_results = {
            ref: load_synthetic_tool_result_payload(traversal.payloads[ref])
            for ref in tool_refs
        }
        _reconcile_reloaded_authority_leaves(
            program=program,
            requests=requests,
            responses=responses,
            raw_events=raw_events,
            tool_results=tool_results,
            grade_results={
                grade_ref: SyntheticGradeCodec().decode(
                    payload=traversal.payloads[grade_ref],
                    program=program,
                    expected_payload=traversal.payloads[grade_ref],
                )
            },
            verifier_results={
                verifier_ref: SyntheticVerifierCodec().decode(
                    payload=traversal.payloads[verifier_ref],
                    program=program,
                    expected_payload=traversal.payloads[verifier_ref],
                )
            },
        )
        authorities = program_authorities[program_ref]
        if not authorities:
            raise ValueError("program occurrence has no provider-lane authority")
        for authority in authorities:
            _assert_program_occurrence_replay(
                program=program,
                responses=responses,
                raw_events=raw_events,
                payloads=traversal.payloads,
                authority=authority,
            )


def _assert_program_occurrence_replay(
    *,
    program: SyntheticPrefixProgram,
    responses: Mapping[ArtifactRef, tuple[str, Any]],
    raw_events: Mapping[ArtifactRef, tuple[str, int]],
    payloads: Mapping[ArtifactRef, bytes],
    authority: _ProgramReplayAuthority,
) -> None:
    """Replay one occurrence under its validated manifest provider lane."""

    _assert_program_actor_binding(
        program=program,
        task_id=authority.task_id,
        actor_roles=authority.actor_roles,
    )
    replay = _ClockTraceReplay(program.clock_trace)
    prefix_epoch = replay.consume("prefix_epoch")
    deadline = prefix_epoch + authority.prefix_caps.wall_clock_ms
    observation_position = 0
    stopped = False
    ended = not program.provider_transcript
    derived_tokens = {"primary_subject": 0, "user_simulator": 0}
    derived_calls = {"primary_subject": 0, "user_simulator": 0}
    derived_turns = {"primary_subject": 0, "user_simulator": 0}
    completed_tools = 0
    cumulative_mutation = False
    trigger = TriggerReason.NO_INTERVENTION_OPPORTUNITY
    for row in program.provider_transcript:
        if stopped:
            raise ValueError("provider transcript continues after terminal outcome")
        expected_seed = derive_call_seed(
            authority.prefix_seed,
            row.subject_role,
            row.call_index,
        )
        if row.seed != expected_seed:
            raise ValueError("program call seed differs from task prefix seed")
        before = replay.consume(f"before_{row.subject_role}_{row.call_index}")
        completion = replay.consume(f"after_{row.subject_role}_{row.call_index}")
        if before > completion:
            raise ValueError("provider before clock exceeds completion clock")
        role_caps = (
            authority.subject_contract_caps
            if row.subject_role == "primary_subject"
            else authority.simulator_contract_caps
        )
        model_ref = (
            authority.subject_contract_ref
            if row.subject_role == "primary_subject"
            else authority.simulator_contract_ref
        )
        if role_caps is None or model_ref is None:
            raise ValueError("program simulator row lacks lane authority")
        lane_token_cap = (
            authority.prefix_caps.generated_tokens
            if row.subject_role == "primary_subject"
            else authority.simulator_caps.aggregate_generated_tokens
        )
        lane_call_cap = (
            authority.prefix_caps.model_calls
            if row.subject_role == "primary_subject"
            else authority.simulator_caps.aggregate_model_calls
        )
        if (
            before >= deadline
            or role_caps.per_call_turns == 0
            or derived_tokens[row.subject_role]
            >= min(lane_token_cap, role_caps.aggregate_generated_tokens)
            or derived_calls[row.subject_role]
            >= min(lane_call_cap, role_caps.aggregate_model_calls)
            or derived_turns[row.subject_role] >= role_caps.aggregate_turns
        ):
            raise ValueError("program provider dispatch exceeds lane allowance")
        validated = _validate_provider_observation(
            observation=RawProviderObservation(
                subject_role=row.subject_role,
                call_index=row.call_index,
                seed=row.seed,
                model_contract_sha256=row.model_contract_sha256,
                response_bytes=(
                    None if row.response_ref is None else payloads[row.response_ref]
                ),
                typed_turn=row.typed_turn,
                reported_output_token_ids=row.reported_output_token_ids,
                reported_generated_tokens=row.reported_generated_tokens,
                provider_event_bytes=payloads[row.provider_event_ref],
                completion_kind=row.completion_kind,
            ),
            expected_role=row.subject_role,
            expected_call_index=row.call_index,
            expected_seed=expected_seed,
            expected_model_sha256=model_ref.sha256,
            deadline_ms=deadline,
            completion_ms=completion,
        )
        parser_kind = (
            "not_applicable"
            if row.response_ref is None
            else responses[row.response_ref][0]
        )
        transport, observed_at = raw_events[row.provider_event_ref]
        if (
            parser_kind != validated.parser_kind
            or transport != validated.transport_kind
            or observed_at != validated.observed_at_ms
        ):
            raise ValueError("provider raw leaf replay differs")
        derived_calls[row.subject_role] += 1
        derived_tokens[row.subject_role] += validated.generated_tokens
        if validated.typed_turn is not None:
            derived_turns[row.subject_role] += 1
        if _provider_failure(validated.status) is not FailureKind.NONE:
            stopped = True
            ended = True
            continue
        if (
            validated.generated_tokens > role_caps.per_call_generated_tokens
            or derived_tokens[row.subject_role]
            > min(lane_token_cap, role_caps.aggregate_generated_tokens)
        ):
            stopped = True
            ended = True
            continue
        if validated.typed_turn is None:
            raise ValueError("completed occurrence lacks parsed turn")
        if validated.typed_turn.finish_reason == "terminal":
            if validated.typed_turn.tool_calls:
                raise ValueError("terminal provider turn cannot contain tools")
            stopped = True
            ended = True
            continue
        if row.subject_role != "primary_subject":
            continue
        queue = validated.typed_turn.tool_calls
        for tool_index, call in enumerate(queue):
            before_tool = replay.consume(f"before_tool_{call.call_id}")
            pretool_failure = _pretool_failure(
                before_ms=before_tool,
                deadline_ms=deadline,
                completed_tools=completed_tools,
                tool_cap=authority.prefix_caps.tool_calls,
            )
            if pretool_failure is not FailureKind.NONE:
                stopped = True
                ended = True
                break
            if observation_position >= len(program.tool_observations):
                raise ValueError("queued tool lacks an exact observation")
            observation = program.tool_observations[observation_position]
            if observation.call_id != call.call_id:
                raise ValueError("tool observation differs from exact queue")
            after_tool = replay.consume(f"after_tool_{call.call_id}")
            if before_tool > after_tool:
                raise ValueError("tool before clock exceeds completion clock")
            observation_position += 1
            completed_tools += 1
            cumulative_mutation = cumulative_mutation or observation.mutation_committed
            transition = _completed_tool_transition(
                failure_kind=observation.failure_kind,
                episode_terminal=observation.episode_terminal,
                completion_ms=after_tool,
                deadline_ms=deadline,
                token_overshoot=(
                    derived_tokens["primary_subject"]
                    > min(
                        authority.prefix_caps.generated_tokens,
                        authority.subject_contract_caps.aggregate_generated_tokens,
                    )
                ),
                cumulative_mutation=cumulative_mutation,
                verifier_eligible=observation.verifier_eligible,
                completed_tools=completed_tools,
                queued_remainder=queue[tool_index + 1 :],
            )
            if transition.stopped:
                trigger = transition.trigger_reason
                stopped = True
                ended = True
                break
    if observation_position != len(program.tool_observations):
        raise ValueError("tool observation program has unconsumed rows")
    replay.assert_exhausted()
    if program.expected_trigger_reason is not trigger:
        raise ValueError(
            "program expected trigger differs from exact occurrence replay"
        )
    if not ended:
        raise ValueError("nonempty program reached a nonterminal live end state")


def _verify_published(
    *,
    root_descriptor: int,
    relative_path: str,
    expected: _OwnedPrefixPublication,
) -> None:
    parts = PurePosixPath(relative_path).parts
    descriptors: list[int] = []
    primary: BaseException | None = None
    try:
        current = os.dup(root_descriptor)
        descriptors.append(current)
        for component in parts[:-1]:
            current = os.open(component, _DIRECTORY_FLAGS, dir_fd=current)
            descriptors.append(current)
        descriptor = os.open(parts[-1], _READ_FLAGS, dir_fd=current)
        descriptors.append(descriptor)
        before = os.fstat(descriptor)
        payload_chunks: list[bytes] = []
        while chunk := os.read(descriptor, 1024 * 1024):
            payload_chunks.append(chunk)
        after = os.fstat(descriptor)
        named = os.stat(parts[-1], dir_fd=current, follow_symlinks=False)
        payload = b"".join(payload_chunks)
        if (
            not stat.S_ISREG(before.st_mode)
            or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
            or (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
            or (before.st_dev, before.st_ino) != expected.identity
            or hashlib.sha256(payload).hexdigest() != expected.ref.sha256
            or len(payload) != expected.ref.byte_count
        ):
            raise RecordValidationError("published prefix index identity differs")
        validate_record(json.loads(payload))
    except BaseException as exc:
        primary = exc
    cleanup_errors: list[BaseException] = []
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except BaseException as exc:
            cleanup_errors.append(exc)
    if primary is not None and cleanup_errors:
        raise BaseExceptionGroup(
            "prefix-index verification and cleanup both failed",
            [primary, *cleanup_errors],
        )
    if primary is not None:
        raise primary
    if cleanup_errors:
        raise BaseExceptionGroup(
            "prefix-index verification cleanup failed",
            cleanup_errors,
        )


def _rollback_owned_publication(
    *,
    root_descriptor: int,
    owned: _OwnedPrefixPublication,
    content_sealed: bool = True,
) -> None:
    path_parts = PurePosixPath(owned.ref.relative_path).parts
    descriptors: dict[tuple[str, ...], int] = {}

    def descriptor_for(parts: tuple[str, ...]) -> int:
        if not parts:
            return root_descriptor
        cached = descriptors.get(parts)
        if cached is not None:
            return cached
        parent = descriptor_for(parts[:-1])
        descriptor = os.open(parts[-1], _DIRECTORY_FLAGS, dir_fd=parent)
        descriptors[parts] = descriptor
        return descriptor

    publication = OwnedPublication(
        parent_parts=path_parts[:-1],
        name=path_parts[-1],
        relative_path=owned.ref.relative_path,
        device=owned.identity[0],
        inode=owned.identity[1],
        sha256=owned.ref.sha256,
        byte_count=owned.ref.byte_count,
    )
    incomplete = OwnedTemporary(
        parent_parts=path_parts[:-1],
        name=path_parts[-1],
        relative_path=owned.ref.relative_path,
        device=owned.identity[0],
        inode=owned.identity[1],
    )
    failures: list[str] = []
    residuals: list[Any] = []
    try:
        parent = descriptor_for(path_parts[:-1])
        try:
            named = os.stat(
                path_parts[-1],
                dir_fd=parent,
                follow_symlinks=False,
            )
        except FileNotFoundError:
            failures = [
                f"{owned.ref.relative_path}: ownership lost before quarantine; "
                "named source is missing"
            ]
            residuals = [owned.ref.relative_path]
        else:
            if (named.st_dev, named.st_ino) != owned.identity:
                failures = [
                    f"{owned.ref.relative_path}: ownership lost before quarantine; "
                    "named source identity changed"
                ]
                residuals = [owned.ref.relative_path]
            else:
                failures, residuals = rollback_publication(
                    owned=[publication] if content_sealed else [],
                    temporaries=[] if content_sealed else [incomplete],
                    directories=[],
                    descriptor_for=descriptor_for,
                    owned_name_for=lambda index: (
                        f".pneuma-prefix-{os.getpid()}-{owned.identity[1]}-"
                        f"{index}.rollback"
                    ),
                    temporary_name_for=lambda index: (
                        f".pneuma-prefix-{os.getpid()}-{owned.identity[1]}-"
                        f"{index}.partial-rollback"
                    ),
                    directory_name_for=lambda index: f".unused-directory-{index}",
                    rename=rename_no_replace,
                    read_flags=_READ_FLAGS,
                )
    except BaseException as exc:
        failures.append(f"{owned.ref.relative_path}: {type(exc).__name__}: {exc}")
    cleanup: list[BaseException] = []
    for descriptor in reversed(tuple(descriptors.values())):
        try:
            os.close(descriptor)
        except BaseException as exc:
            cleanup.append(exc)
    errors: list[BaseException] = [
        *(
            RecordValidationError(f"prefix-index rollback failure: {failure}")
            for failure in failures
        ),
        *(
            RecordValidationError(
                "prefix-index rollback residual: " + render_rollback_residual(residual)
            )
            for residual in residuals
        ),
        *cleanup,
    ]
    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise BaseExceptionGroup("prefix-index rollback incomplete", errors)


def _publish_once(
    *,
    root_descriptor: int,
    relative_path: str,
    payload: bytes,
) -> _OwnedPrefixPublication:
    parts = PurePosixPath(relative_path).parts
    descriptors: list[int] = []
    file_descriptor: int | None = None
    parent_descriptor: int | None = None
    target_created = False
    created_identity: tuple[int, int] | None = None
    primary: BaseException | None = None
    close_error: BaseException | None = None
    try:
        publication_root_descriptor = os.dup(root_descriptor)
        descriptors.append(publication_root_descriptor)
        parent_descriptor = publication_root_descriptor
        for component in parts[:-1]:
            parent_descriptor = os.open(
                component,
                _DIRECTORY_FLAGS,
                dir_fd=parent_descriptor,
            )
            descriptors.append(parent_descriptor)
        file_descriptor = os.open(
            parts[-1],
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=parent_descriptor,
        )
        target_created = True
        created = os.fstat(file_descriptor)
        if not stat.S_ISREG(created.st_mode):
            raise RecordValidationError("prefix index target is not a regular file")
        created_identity = (created.st_dev, created.st_ino)
        remaining = memoryview(payload)
        while remaining:
            written = os.write(file_descriptor, remaining)
            if written <= 0:
                raise OSError("short prefix-index publication write")
            remaining = remaining[written:]
        os.fsync(file_descriptor)
        prepared = os.fstat(file_descriptor)
        if (
            prepared.st_dev,
            prepared.st_ino,
        ) != created_identity or prepared.st_size != len(payload):
            raise RecordValidationError("prepared prefix index identity differs")
    except BaseException as exc:
        primary = exc
    if file_descriptor is not None:
        file_to_close = file_descriptor
        file_descriptor = None
        if target_created and created_identity is None:
            try:
                created = os.fstat(file_to_close)
                created_identity = (created.st_dev, created.st_ino)
            except BaseException as exc:
                if primary is None:
                    primary = exc
                else:
                    primary = BaseExceptionGroup(
                        "publication and target binding both failed",
                        [primary, exc],
                    )
        try:
            os.close(file_to_close)
        except BaseException as exc:
            close_error = exc
    if primary is None and close_error is None:
        try:
            if parent_descriptor is None:
                raise AssertionError("publication parent descriptor is unavailable")
            named = os.stat(
                parts[-1],
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
            if (
                created_identity is None
                or (named.st_dev, named.st_ino) != created_identity
                or not stat.S_ISREG(named.st_mode)
            ):
                raise RecordValidationError(
                    "prefix index target identity changed before durability"
                )
            os.fsync(parent_descriptor)
        except BaseException as exc:
            primary = exc
    if primary is not None or close_error is not None:
        rollback_errors: list[BaseException] = []
        if target_created and created_identity is not None:
            try:
                _rollback_owned_publication(
                    root_descriptor=root_descriptor,
                    owned=_OwnedPrefixPublication(
                        ArtifactRef(
                            "resampling_prefix_receipt",
                            relative_path,
                            hashlib.sha256(payload).hexdigest(),
                            len(payload),
                            "application/json",
                        ),
                        created_identity,
                    ),
                    content_sealed=False,
                )
            except BaseException as exc:
                rollback_errors.append(exc)
        errors = [
            *(() if primary is None else (primary,)),
            *(() if close_error is None else (close_error,)),
            *rollback_errors,
        ]
        if target_created and created_identity is None:
            errors.append(
                RecordValidationError(
                    "created prefix-index target could not be identity-bound "
                    "for safe rollback"
                )
            )
        cleanup_errors: list[BaseException] = []
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except BaseException as exc:
                cleanup_errors.append(exc)
        errors.extend(cleanup_errors)
        if len(errors) == 1:
            raise errors[0]
        raise BaseExceptionGroup("prefix-index publication failed", errors)
    cleanup_errors = []
    for descriptor in reversed(descriptors):
        try:
            os.close(descriptor)
        except BaseException as exc:
            cleanup_errors.append(exc)
    ref = ArtifactRef(
        "resampling_prefix_receipt",
        relative_path,
        hashlib.sha256(payload).hexdigest(),
        len(payload),
        "application/json",
    )
    if created_identity is None:
        raise AssertionError("successful publication lacks a bound identity")
    owned = _OwnedPrefixPublication(ref, created_identity)
    if cleanup_errors:
        try:
            _rollback_owned_publication(
                root_descriptor=root_descriptor,
                owned=owned,
            )
        except BaseException as rollback:
            raise BaseExceptionGroup(
                "publication cleanup and rollback both failed",
                [*cleanup_errors, rollback],
            )
        raise BaseExceptionGroup(
            "prefix-index directory descriptor cleanup failed",
            cleanup_errors,
        )
    return owned


def _seal_bound_prefix_index(
    *,
    root: Path,
    root_descriptor: int,
    schedule_ref: ArtifactRef,
    candidate_refs: tuple[ArtifactRef, ...],
    relative_path: str,
    transaction: _SealTransactionState,
) -> _OwnedPrefixPublication:
    root_identity = os.fstat(root_descriptor)
    named_before = os.stat(root, follow_symlinks=False)
    if not stat.S_ISDIR(root_identity.st_mode) or (
        root_identity.st_dev,
        root_identity.st_ino,
    ) != (named_before.st_dev, named_before.st_ino):
        raise RecordValidationError("run_root identity changed before S02D traversal")
    traversal = _FreshTraversal.empty()
    receipts: list[FrozenPrefixReceipt] = []
    with (
        ScientificRefReader(root) as scientific_reader,
        ControllerArtifactResolver(root) as resolver,
        AuthorityRefReader(root) as authority_reader,
    ):
        expected_root_identity = (root_identity.st_dev, root_identity.st_ino)
        reader_identities = (
            scientific_reader.bound_root_identity,
            resolver.bound_root_identity,
            authority_reader.bound_root_identity,
        )
        if any(identity != expected_root_identity for identity in reader_identities):
            raise RecordValidationError(
                "fresh reader root identity differs from held S02D root"
            )
        schedule_bound = scientific_reader.read_bound(schedule_ref)
        schedule = decode_scientific_parent(
            schedule_ref,
            schedule_bound,
            run_root=root,
            field="schedule_ref",
            expected_kind="resampling_prefix_schedule",
        )
        _record_physical(
            ref=schedule_ref,
            load_class="scientific_parent",
            physical=(schedule_bound.st_dev, schedule_bound.st_ino),
            visited=traversal.visited,
            path_bindings=traversal.path_bindings,
            physical_bindings=traversal.physical_bindings,
        )
        traversal.payloads[schedule_ref] = schedule_bound.payload
        traversal.nested[schedule_ref] = walk_artifact_refs(schedule.value)
        traversal.decoded[schedule_ref] = schedule
        traversal.scientific_refs.add(schedule_ref)
        task_ids = _schedule_task_ids(schedule)
        if len(candidate_refs) != len(task_ids):
            raise ValueError("candidate coverage differs from selected schedule roster")
        anchor_authority, validated_plan = (
            _load_prefix_execution_authority_and_plan_with_reader(
                run_root=root,
                schedule_ref=schedule_ref,
                task_id=task_ids[0],
                reader=authority_reader,
                scientific_reader=scientific_reader,
            )
        )
        schedule_payload = cast(dict[str, object], schedule.value["payload"])
        authorities = {task_ids[0]: anchor_authority}
        authorities.update(
            {
                task_id: _project_prefix_execution_authority_from_plan(
                    anchor=anchor_authority,
                    schedule_payload=schedule_payload,
                    task_id=task_id,
                    validated_plan=validated_plan,
                )
                for task_id in task_ids[1:]
            }
        )
        for task_id, candidate_ref in zip(task_ids, candidate_refs, strict=True):
            graph = _load_candidate_graph(
                root=root,
                schedule_ref=schedule_ref,
                schedule=schedule,
                expected_task_id=task_id,
                candidate_ref=candidate_ref,
                authority=authorities[task_id],
                scientific_reader=scientific_reader,
                resolver=resolver,
                authority_reader=authority_reader,
                traversal=traversal,
            )
            _validate_candidate(graph)
            receipts.append(graph.receipt)
        occurrence_authorities: dict[
            ArtifactRef,
            list[_ProgramReplayAuthority],
        ] = {}
        for task_lane in validated_plan.task_lanes:
            if task_lane.program_ref is None:
                raise ValueError("validated task lane lacks execution program")
            task_authority = authorities.get(task_lane.task_id)
            if task_authority is None:
                raise ValueError(
                    "program occurrence task lacks selected schedule authority"
                )
            lane = validated_plan.lanes[task_lane.prefix_lane_ordinal]
            occurrence_authorities.setdefault(task_lane.program_ref, []).append(
                _ProgramReplayAuthority(
                    task_id=task_lane.task_id,
                    prefix_seed=task_authority.task_schedule.prefix_seed,
                    actor_roles=task_lane.actor_roles,
                    prefix_caps=lane.prefix_caps,
                    simulator_caps=lane.simulator_caps,
                    subject_contract_caps=lane.subject_contract_caps,
                    simulator_contract_caps=lane.simulator_contract_caps,
                    subject_contract_ref=lane.subject_contract_ref,
                    simulator_contract_ref=lane.simulator_contract_ref,
                )
            )
        _assert_all_program_occurrences(
            traversal,
            program_authorities={
                ref: tuple(values) for ref, values in occurrence_authorities.items()
            },
        )
        manifest_refs = {
            ref for ref in traversal.scientific_refs if ref.role == "study_manifest"
        }
        if len(manifest_refs) != 1 or traversal.scientific_refs != {
            schedule_ref,
            *manifest_refs,
        }:
            raise ValueError("S02D scientific-parent partition is not exact")
    named_after = os.stat(root, follow_symlinks=False)
    if (root_identity.st_dev, root_identity.st_ino) != (
        named_after.st_dev,
        named_after.st_ino,
    ):
        raise RecordValidationError(
            "run_root identity changed between validation and publication"
        )

    record = {
        "record_kind": "resampling_prefix_receipt",
        "schema_version": "0.1.0",
        "study_id": schedule.value["study_id"],
        "frozen_created_at": schedule.value["frozen_created_at"],
        "provenance": schedule.value["provenance"],
        "payload": {
            "schedule_ref": asdict(schedule_ref),
            "task_receipts": [asdict(receipt) for receipt in receipts],
        },
    }
    validated = validate_record(record)
    payload = canonical_json_bytes(validated, indent=None)
    published = _publish_once(
        root_descriptor=root_descriptor,
        relative_path=relative_path,
        payload=payload,
    )
    try:
        _verify_published(
            root_descriptor=root_descriptor,
            relative_path=relative_path,
            expected=published,
        )
        transaction.publication = published
        return published
    except BaseException as primary:
        if transaction.publication is not None:
            raise
        try:
            _rollback_owned_publication(
                root_descriptor=root_descriptor,
                owned=published,
            )
        except BaseException as rollback:
            raise BaseExceptionGroup(
                "prefix-index verification and rollback both failed",
                [primary, rollback],
            )
        raise


def _acquire_root_transaction(transaction: _SealTransactionState) -> None:
    """Acquire once; ambiguous ownership is process-fail-stop."""

    global _S02D_RELEASE_FAIL_STOP

    if transaction.release_phase != "lock_pending":
        raise AssertionError("root transaction acquisition cannot be retried")
    transaction.release_phase = "lock_ambiguous"
    _S02D_RELEASE_FAIL_STOP = transaction
    try:
        fcntl.flock(
            transaction.descriptor,
            fcntl.LOCK_EX | fcntl.LOCK_NB,
        )
    except BaseException as exc:
        raise BaseExceptionGroup(
            "precommit root-lock acquisition ambiguous residual",
            [exc],
        )
    transaction.release_phase = "unlock_pending"
    _S02D_RELEASE_FAIL_STOP = None


def _release_root_transaction(transaction: _SealTransactionState) -> None:
    """Perform one normal release; ambiguity is process-fail-stop."""

    global _S02D_RELEASE_FAIL_STOP

    if transaction.release_phase != "unlock_pending":
        raise AssertionError("root transaction release cannot be retried")
    transaction.release_phase = "unlock_ambiguous"
    _S02D_RELEASE_FAIL_STOP = transaction
    fcntl.flock(transaction.descriptor, fcntl.LOCK_UN)
    transaction.release_phase = "close_pending"
    transaction.release_phase = "close_ambiguous"
    try:
        os.close(transaction.descriptor)
    except OSError as exc:
        if exc.errno != errno.EBADF:
            raise
    transaction.release_phase = "closed"
    _S02D_RELEASE_FAIL_STOP = None
    _S02D_PROCESS_RESERVATION.release()


def _seal_transaction_outcome(
    *,
    transaction: _SealTransactionState,
    primary: BaseException | None,
    release_error: BaseException | None,
) -> tuple[ArtifactRef | None, BaseException | None]:
    """Classify one fully closed transaction without performing mutation."""

    errors = [
        *(() if primary is None else (primary,)),
        *(() if release_error is None else (release_error,)),
    ]
    if transaction.publication is not None:
        if errors:
            return None, BaseExceptionGroup(
                "committed prefix-index publication cleanup residual",
                errors,
            )
        return transaction.publication.ref, None
    if not errors:
        return None, AssertionError(
            "prefix-index transaction produced no committed result"
        )
    if len(errors) == 1 and isinstance(errors[0], Exception):
        return None, errors[0]
    return None, BaseExceptionGroup(
        "prefix-index precommit transaction interrupted or cleanup failed",
        errors,
    )


def seal_prefix_index(
    *,
    run_root: Path,
    schedule_ref: ArtifactRef,
    candidate_refs: tuple[ArtifactRef, ...],
    out: Path,
) -> ArtifactRef:
    """Freshly reconstruct all selected candidates and seal the prefix index."""

    if type(run_root) is not type(Path()):
        raise TypeError("run_root must be an exact platform Path")
    if type(candidate_refs) is not tuple:
        raise TypeError("candidate_refs must be an exact tuple")
    if not all(type(ref) is ArtifactRef for ref in candidate_refs):
        raise TypeError("candidate_refs must contain exact ArtifactRef values")
    if len(candidate_refs) != len(set(candidate_refs)):
        raise ValueError("candidate_refs must be pairwise unique")
    root = run_root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    relative_path = _exact_output_relative_path(root=root, out=out)
    if not _S02D_PROCESS_RESERVATION.acquire(blocking=False):
        raise RecordValidationError(
            "S02D process reservation or final-release fail-stop is active; "
            "restart or operator cleanup proof is required"
        )
    try:
        descriptor = os.open(root, _DIRECTORY_FLAGS)
    except OSError:
        _S02D_PROCESS_RESERVATION.release()
        raise
    transaction = _SealTransactionState(descriptor)
    result: _OwnedPrefixPublication | None = None
    primary: BaseException | None = None
    release_error: BaseException | None = None
    try:
        try:
            _acquire_root_transaction(transaction)
            os.fstat(descriptor)
            result = _seal_bound_prefix_index(
                root=root,
                root_descriptor=descriptor,
                schedule_ref=schedule_ref,
                candidate_refs=candidate_refs,
                relative_path=relative_path,
                transaction=transaction,
            )
            if transaction.publication is not result:
                raise AssertionError(
                    "returned publication differs from committed transaction state"
                )
        except BaseException as exc:
            primary = exc
        if transaction.release_phase == "unlock_pending":
            try:
                _release_root_transaction(transaction)
            except BaseException as exc:
                release_error = exc
        outcome_ref, outcome_error = _seal_transaction_outcome(
            transaction=transaction,
            primary=primary,
            release_error=release_error,
        )
    except BaseException as boundary_error:
        if transaction.release_phase == "unlock_pending":
            try:
                _release_root_transaction(transaction)
            except BaseException as exc:
                release_error = exc
        primary = (
            boundary_error
            if primary is None
            else BaseExceptionGroup(
                "prefix-index transaction and boundary interruption",
                [primary, boundary_error],
            )
        )
        outcome_ref, outcome_error = _seal_transaction_outcome(
            transaction=transaction,
            primary=primary,
            release_error=release_error,
        )
    if outcome_error is not None:
        raise outcome_error
    if outcome_ref is None:
        raise AssertionError("successful transaction outcome lacks an ArtifactRef")
    return outcome_ref


__all__ = ("seal_prefix_index",)
