"""Independent T5-S02D prefix-candidate reconstruction and publication."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Mapping, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import validate_record
from .authority_refs import AuthorityRefReader, load_json_bytes, walk_artifact_refs
from .controller_artifacts import ControllerArtifactResolver
from .errors import RecordValidationError
from .evidence import (
    AttemptBoundZeroCostClosure,
    CompositeSnapshotEnvelope,
    ContainerAttestation,
    ControllerProviderCostClosure,
    ControllerProviderEvent,
    ControllerProviderSettlement,
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
    _load_prefix_execution_authority_with_reader,
)
from .prefix_contracts import (
    REF_LOAD_CLASS_BY_ROLE,
    InitialRestoreQualificationReceipt,
    SnapshotRestoreReceipt,
    SyntheticPrefixProgram,
    load_initial_restore_qualification_receipt,
    load_prefix_candidate_receipt,
    load_snapshot_restore_receipt,
    load_synthetic_prefix_program,
)
from .scientific_records import (
    ScientificRecord,
    ScientificRefReader,
    decode_scientific_parent,
)
from .synthetic_environment import _decode_snapshot_state
from .synthetic_prefix_loop import (
    AUTHORITY_ASSET_DECODER_BY_ROLE,
    SyntheticGradeCodec,
    SyntheticVerifierCodec,
    _controller_nested_refs,
    _decode_raw_event,
    _reconcile_reloaded_attestations,
    _reconcile_reloaded_authority_leaves,
    _reconcile_reloaded_execution_records,
)
from .types import ArtifactRef, FailureKind, TriggerReason


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

    authority = _load_prefix_execution_authority_with_reader(
        run_root=root,
        schedule_ref=schedule_ref,
        task_id=expected_task_id,
        reader=authority_reader,
    )
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
            traversal.scientific_refs.add(ref)
            payload = bound.payload
            nested = walk_artifact_refs(record.value)
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
            else sum(
                1
                for attempt in graph.provider_ledger.ledger.attempts
                if attempt.subject_role == "user_simulator"
                and attempt.status is ProviderAttemptStatus.COMPLETED
            )
        ),
    )
    final_state = _decode_snapshot_state(
        graph.payloads[snapshot.environment_snapshot_ref]
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
        or final_state.mutation_committed is not snapshot.cumulative_mutation
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


def _assert_execution_semantics(graph: _CandidateGraph) -> None:
    receipt = graph.receipt
    authority = graph.authority
    program = graph.program
    ledger = graph.provider_ledger
    cost_closure = _cost_closure(graph)
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
    maximum_elapsed = max((*attempt_elapsed, *boundary_elapsed), default=0)
    if receipt.counters.wall_clock_ms != maximum_elapsed:
        raise ValueError("wall-clock counter differs from execution chronology")

    cumulative_mutation = False
    derived_trigger = TriggerReason.NO_INTERVENTION_OPPORTUNITY
    for index, boundary in enumerate(graph.tool_ledger.boundaries, start=1):
        cumulative_mutation = cumulative_mutation or boundary.mutation_committed
        if (
            boundary.failure_kind is not FailureKind.NONE
            or boundary.episode_terminal
            or boundary.elapsed_ms > authority.prefix_caps.wall_clock_ms
        ):
            break
        if cumulative_mutation and boundary.verifier_eligible_after:
            derived_trigger = TriggerReason.FIRST_ELIGIBLE_MUTATION
            break
        if index == 4:
            derived_trigger = TriggerReason.FOURTH_TOOL_CALL
            break
    if derived_trigger is not TriggerReason.NO_INTERVENTION_OPPORTUNITY and len(
        graph.tool_ledger.boundaries
    ) != next(
        index
        for index, boundary in enumerate(graph.tool_ledger.boundaries, start=1)
        if (
            (
                derived_trigger is TriggerReason.FIRST_ELIGIBLE_MUTATION
                and any(
                    prior.mutation_committed
                    for prior in graph.tool_ledger.boundaries[:index]
                )
                and boundary.verifier_eligible_after
            )
            or (derived_trigger is TriggerReason.FOURTH_TOOL_CALL and index == 4)
        )
    ):
        raise ValueError("tool evidence continues after the earliest trigger")
    if (
        receipt.trigger_reason is not derived_trigger
        or program.expected_trigger_reason is not derived_trigger
    ):
        raise ValueError("trigger differs from fresh chronological derivation")


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


def _verify_published(
    *,
    root_descriptor: int,
    relative_path: str,
    expected: ArtifactRef,
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
            or hashlib.sha256(payload).hexdigest() != expected.sha256
            or len(payload) != expected.byte_count
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


def _publish_once(
    *,
    root_descriptor: int,
    relative_path: str,
    payload: bytes,
) -> ArtifactRef:
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
        owned = file_descriptor
        file_descriptor = None
        if target_created and created_identity is None:
            try:
                created = os.fstat(owned)
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
            os.close(owned)
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
        if (
            parent_descriptor is not None
            and target_created
            and created_identity is not None
        ):
            try:
                named = os.stat(
                    parts[-1],
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                if (named.st_dev, named.st_ino) != created_identity:
                    raise RecordValidationError(
                        "refusing to unlink a replaced prefix-index target"
                    )
                os.unlink(parts[-1], dir_fd=parent_descriptor)
                os.fsync(parent_descriptor)
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
    if cleanup_errors:
        raise BaseExceptionGroup(
            "prefix-index directory descriptor cleanup failed",
            cleanup_errors,
        )
    return ArtifactRef(
        role="resampling_prefix_receipt",
        relative_path=relative_path,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type="application/json",
    )


def _seal_bound_prefix_index(
    *,
    root: Path,
    root_descriptor: int,
    schedule_ref: ArtifactRef,
    candidate_refs: tuple[ArtifactRef, ...],
    relative_path: str,
) -> ArtifactRef:
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
        for task_id, candidate_ref in zip(task_ids, candidate_refs, strict=True):
            graph = _load_candidate_graph(
                root=root,
                schedule_ref=schedule_ref,
                schedule=schedule,
                expected_task_id=task_id,
                candidate_ref=candidate_ref,
                scientific_reader=scientific_reader,
                resolver=resolver,
                authority_reader=authority_reader,
                traversal=traversal,
            )
            _validate_candidate(graph)
            receipts.append(graph.receipt)
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
    _verify_published(
        root_descriptor=root_descriptor,
        relative_path=relative_path,
        expected=published,
    )
    return published


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
    descriptor = os.open(root, _DIRECTORY_FLAGS)
    result: ArtifactRef | None = None
    primary: BaseException | None = None
    try:
        result = _seal_bound_prefix_index(
            root=root,
            root_descriptor=descriptor,
            schedule_ref=schedule_ref,
            candidate_refs=candidate_refs,
            relative_path=relative_path,
        )
    except BaseException as exc:
        primary = exc
    cleanup: BaseException | None = None
    try:
        os.close(descriptor)
    except BaseException as exc:
        cleanup = exc
    if primary is not None and cleanup is not None:
        raise BaseExceptionGroup(
            "prefix-index transaction and root cleanup both failed",
            [primary, cleanup],
        )
    if primary is not None:
        raise primary
    if cleanup is not None:
        raise cleanup
    if result is None:
        raise AssertionError("prefix-index transaction produced no result")
    return result


__all__ = ("seal_prefix_index",)
