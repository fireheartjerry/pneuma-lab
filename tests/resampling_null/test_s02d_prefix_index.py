from __future__ import annotations

import base64
from dataclasses import asdict, replace
import fcntl
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

import pneuma_lab.resampling_null.prefix_index as prefix_index_module
from pneuma_lab.resampling_null import run_prefix, seal_prefix_index
from pneuma_lab.resampling_null.artifacts import validate_record
from pneuma_lab.resampling_null.evidence import (
    FrozenPrefixReceipt,
    load_controller_provider_cost_closure,
    load_controller_provider_event,
    load_controller_provider_settlement,
    load_provider_attempt,
    load_provider_attempt_ledger,
    load_provider_dispatch_intent,
    load_tool_boundary_ledger,
)
from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.prefix_contracts import (
    CONTROLLER_ROLE_MEDIA,
    RawProviderCompletionKind,
    SyntheticClockRead,
    load_synthetic_prefix_program,
)
from pneuma_lab.resampling_null.synthetic_prefix_loop import (
    _open_prefix_loop,
)
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    CallSeedReceipt,
    FrozenVerifierReceipt,
    GradeReceipt,
    SubjectTurn,
    TriggerReason,
)
from tests.resampling_null.provider_authority_fixture import (
    ProviderAuthorityFixture,
)
from tests.resampling_null.test_s02c_prefix_loop import _loop_authority


def _completed_candidates(
    tmp_path: Path,
) -> tuple[Path, ProviderAuthorityFixture, tuple[ArtifactRef, ArtifactRef]]:
    run_root = tmp_path / "run"
    fixture = ProviderAuthorityFixture.build(
        run_root,
        executable_sources=True,
        requires_simulator=False,
        simulator_present=False,
    )
    schedule_path = run_root / "prefix-schedule.json"
    schedule = json.loads(schedule_path.read_bytes())
    registry = json.loads((run_root / "sources/tasks.json").read_bytes())
    second = json.loads(json.dumps(schedule["payload"]["tasks"][0]))
    second["task"] = {
        "task_id": registry["tasks"][1]["task_id"],
        "benchmark": registry["tasks"][1]["benchmark"],
        "stratum": registry["tasks"][1]["stratum"],
        "lineage": registry["tasks"][1]["lineage"],
        "sensitivity_groups": registry["tasks"][1]["groups"],
    }
    second["prefix_seed"] = 12
    schedule["payload"]["tasks"].append(second)
    validate_record(schedule)
    schedule_bytes = canonical_json_bytes(schedule, indent=None)
    schedule_path.write_bytes(schedule_bytes)
    fixture = ProviderAuthorityFixture(
        schedule_ref=ArtifactRef(
            role="resampling_prefix_schedule",
            relative_path="prefix-schedule.json",
            sha256=hashlib.sha256(schedule_bytes).hexdigest(),
            byte_count=len(schedule_bytes),
            media_type="application/json",
        ),
        refs=fixture.refs,
    )
    candidates = tuple(
        run_prefix(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            task_id=task_id,
        )
        for task_id in ("task-1", "task-foreign")
    )
    return run_root, fixture, candidates


def _nonempty_execution_graph(
    tmp_path: Path,
) -> prefix_index_module._CandidateGraph:
    authority = _loop_authority(tmp_path)
    opened = _open_prefix_loop(run_root=tmp_path, authority=authority)

    def payload(ref: ArtifactRef) -> bytes:
        return (tmp_path / ref.relative_path).read_bytes()

    def controller_ref(role: str, salt: str) -> ArtifactRef:
        digest = hashlib.sha256(f"{role}:{salt}".encode()).hexdigest()
        return ArtifactRef(
            role,
            f"controller-artifacts/{role}/{digest}",
            digest,
            1,
            CONTROLLER_ROLE_MEDIA[role],
        )

    snapshot_ref = controller_ref("composite_snapshot", "snapshot")
    visible_ref = controller_ref("visible_context", "visible")
    token_ref = controller_ref("token_ids", "tokens")
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
        y0_grade=GradeReceipt(
            0,
            0.0,
            False,
            controller_ref("grade_evidence", "grade"),
        ),
        grade_execution_receipt_ref=controller_ref(
            "grade_evidence_receipt",
            "grade-receipt",
        ),
        verifier_receipt=FrozenVerifierReceipt(
            authority.task_schedule.task.task_id,
            authority.schedule_ref.sha256,
            snapshot_ref,
            controller_ref("verifier_evidence", "verifier"),
            0,
        ),
        verifier_execution_receipt_ref=controller_ref(
            "verifier_evidence_receipt",
            "verifier-receipt",
        ),
        counters=opened.primary_counters,
        simulator_counters=opened.simulator_counters,
        call_seeds=tuple(
            CallSeedReceipt(intent.subject_role, intent.call_index, intent.seed)
            for intent in opened.intents
        ),
        provider_attempts_ref=opened.provider_attempts_ref,
        boundary_ledger_ref=opened.boundary_ledger_ref,
        provider_cost_ref=opened.provider_cost_ref,
    )
    ledger = load_provider_attempt_ledger(payload(opened.provider_attempts_ref))
    cost = load_controller_provider_cost_closure(payload(opened.provider_cost_ref))
    tool_ledger = load_tool_boundary_ledger(payload(opened.boundary_ledger_ref))
    intents = {
        ref: load_provider_dispatch_intent(payload(ref))
        for ref in ledger.ledger.intent_refs
    }
    attempts = {ref: load_provider_attempt(payload(ref)) for ref in ledger.attempt_refs}
    events = {
        attempt.provider_event_ref: load_controller_provider_event(
            payload(attempt.provider_event_ref)
        )
        for attempt in attempts.values()
    }
    settlements = {
        ref: load_controller_provider_settlement(payload(ref))
        for ref in cost.settlement_refs
    }
    payloads = dict(opened._payloads)
    reachable_controller_refs = {
        receipt.provider_attempts_ref,
        receipt.provider_cost_ref,
        receipt.boundary_ledger_ref,
        *ledger.ledger.intent_refs,
        *ledger.attempt_refs,
        *events,
        *cost.settlement_refs,
        *(boundary.tool_call_ref for boundary in tool_ledger.boundaries),
        *(boundary.tool_result_ref for boundary in tool_ledger.boundaries),
    }
    payloads.update({ref: payload(ref) for ref in reachable_controller_refs})
    graph = prefix_index_module._CandidateGraph(
        receipt=receipt,
        authority=authority,
        program=opened._program,
        program_bytes=opened._program_bytes,
        payloads=payloads,
        snapshot=SimpleNamespace(  # type: ignore[arg-type]
            episode_terminal=(
                opened.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY
            ),
            cumulative_mutation=False,
        ),
        initial_restore=None,  # type: ignore[arg-type]
        grade_restore=None,  # type: ignore[arg-type]
        verifier_restore=None,  # type: ignore[arg-type]
        grade_execution=None,  # type: ignore[arg-type]
        verifier_execution=None,  # type: ignore[arg-type]
        provider_ledger=ledger,
        cost_record=cost,
        tool_ledger=tool_ledger,
        intents=intents,
        attempts=attempts,
        events=events,
        settlements=settlements,
        subject_attestations=(),
        simulator_attestations=(),
        runtime_attestations=(),
        container_attestations=(),
    )
    opened.close()
    return graph


def _response_bytes(
    *,
    finish_reason: str,
    text: str,
    tool_calls: tuple[object, ...] = (),
) -> bytes:
    generated_tokens = 0
    while True:
        payload = canonical_json_bytes(
            {
                "finish_reason": finish_reason,
                "generated_tokens": generated_tokens,
                "text": text,
                "tool_calls": [
                    {
                        "call_id": call.call_id,
                        "canonical_arguments_json": call.canonical_arguments_json,
                        "name": call.name,
                    }
                    for call in tool_calls
                ],
            },
            indent=None,
        )
        if len(payload) == generated_tokens:
            return payload
        generated_tokens = len(payload)


def _terminal_turn_graph(
    tmp_path: Path,
    *,
    subject_role: str = "primary_subject",
    bind_derived_actor: bool = True,
) -> prefix_index_module._CandidateGraph:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    assert row.response_ref is not None
    response = _response_bytes(finish_reason="terminal", text="done")
    turn = SubjectTurn("done", (), len(response), "terminal")
    seed = prefix_index_module.derive_call_seed(
        graph.authority.task_schedule.prefix_seed,
        subject_role,
        0,
    )
    model_ref = graph.authority.subject_contract_ref
    if subject_role == "user_simulator":
        model_ref = replace(model_ref, role="simulator_contract")
        graph.authority = replace(
            graph.authority,
            simulator_caps=graph.authority.subject_contract_caps,
            simulator_contract_caps=graph.authority.subject_contract_caps,
            simulator_contract_ref=model_ref,
        )
    if bind_derived_actor and hasattr(graph.authority, "actor_roles"):
        graph.authority = replace(
            graph.authority,
            actor_roles=(subject_role,),
        )
    request = canonical_json_bytes(
        {
            "context_base64": base64.b64encode(
                (
                    b"synthetic-simulator-context"
                    if subject_role == "user_simulator"
                    else b'{"instruction":"four tools"}\n'
                )
            ).decode("ascii"),
            "subject_role": subject_role,
        },
        indent=None,
    )
    request_ref = ArtifactRef(
        "synthetic_request",
        f"sources/{subject_role}-terminal-request.json",
        hashlib.sha256(request).hexdigest(),
        len(request),
        "application/json",
    )
    controller_request_ref = replace(
        request_ref,
        role="provider_request",
        relative_path=(
            "controller-artifacts/provider_request/"
            f"{hashlib.sha256(request).hexdigest()}"
        ),
    )
    token_payload = canonical_json_bytes({"token_ids": list(request)}, indent=None)
    token_ref = ArtifactRef(
        "input_token_ids",
        "controller-artifacts/input_token_ids/"
        f"{hashlib.sha256(token_payload).hexdigest()}",
        hashlib.sha256(token_payload).hexdigest(),
        len(token_payload),
        "application/json",
    )
    intent = replace(
        graph.provider_ledger.ledger.intents[0],
        subject_role=subject_role,
        seed=seed,
        request_ref=controller_request_ref,
        input_token_ids_ref=token_ref,
        model_contract_ref=model_ref,
    )
    attempt = replace(
        graph.provider_ledger.ledger.attempts[0],
        subject_role=subject_role,
        seed=seed,
        request_ref=controller_request_ref,
        input_token_ids_ref=token_ref,
        model_contract_ref=model_ref,
        generated_tokens=len(response),
    )
    graph.provider_ledger = replace(
        graph.provider_ledger,
        ledger=replace(
            graph.provider_ledger.ledger,
            intents=(intent,),
            attempts=(attempt,),
        ),
    )
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        provider_transcript=(
            replace(
                row,
                subject_role=subject_role,
                seed=seed,
                model_contract_sha256=model_ref.sha256,
                expected_request_ref=request_ref,
                expected_request_sha256=request_ref.sha256,
                expected_input_token_ids=tuple(request),
                typed_turn=turn,
                reported_output_token_ids=tuple(response),
                reported_generated_tokens=len(response),
            ),
        ),
        tool_observations=(),
        clock_trace=(
            graph.program.clock_trace[0],
            replace(
                graph.program.clock_trace[1],
                label=f"before_{subject_role}_0",
            ),
            replace(
                graph.program.clock_trace[2],
                label=f"after_{subject_role}_0",
            ),
        ),
    )
    graph.payloads[request_ref] = request
    graph.payloads[controller_request_ref] = request
    graph.payloads[token_ref] = token_payload
    graph.payloads[row.response_ref] = response
    graph.tool_ledger = replace(graph.tool_ledger, boundaries=())
    graph.receipt = replace(
        graph.receipt,
        trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        terminal_failure_kind=prefix_index_module.FailureKind.NONE,
        branch_pending_calls=(),
        terminal_unexecuted_remainder=(),
    )
    graph.snapshot = SimpleNamespace(  # type: ignore[assignment]
        episode_terminal=True,
        cumulative_mutation=False,
    )
    return graph


def _replay_authority_with_actor_roles(
    authority: object,
    actor_roles: tuple[str, ...],
) -> SimpleNamespace:
    values = {
        name: getattr(authority, name)
        for name in getattr(authority, "__dataclass_fields__")
    }
    values["actor_roles"] = actor_roles
    return SimpleNamespace(**values)


@pytest.mark.parametrize(
    "tamper",
    [
        "completion_claim",
        "raw_transport",
        "clock_elapsed",
        "tool_clock_elapsed",
        "intent_deadline",
        "typed_queue",
        "per_call_cap",
        "per_call_turns",
        "aggregate_tokens",
        "aggregate_models",
        "aggregate_turns",
        "branch_pending",
        "terminal_remainder",
    ],
)
def test_s02d_replays_execution_semantics_from_raw_evidence(
    tmp_path: Path,
    tamper: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    if tamper == "completion_claim":
        graph.program = replace(
            graph.program,
            provider_transcript=(
                replace(
                    row,
                    completion_kind=RawProviderCompletionKind.REFUSAL,
                ),
            ),
        )
    elif tamper == "raw_transport":
        raw_event = json.loads(graph.payloads[row.provider_event_ref])
        raw_event["transport_kind"] = "provider_error"
        graph.payloads[row.provider_event_ref] = canonical_json_bytes(
            raw_event,
            indent=None,
        )
    elif tamper == "clock_elapsed":
        graph.program = replace(
            graph.program,
            clock_trace=tuple(
                replace(read, uint64_ms=read.uint64_ms + 1)
                if read.label == "after_primary_subject_0"
                else read
                for read in graph.program.clock_trace
            ),
        )
    elif tamper == "tool_clock_elapsed":
        graph.program = replace(
            graph.program,
            clock_trace=tuple(
                replace(read, uint64_ms=read.uint64_ms + 1)
                if read.label == "after_tool_call-1"
                else read
                for read in graph.program.clock_trace
            ),
        )
    elif tamper == "intent_deadline":
        intent_ref = graph.provider_ledger.ledger.intent_refs[0]
        intent = replace(
            graph.provider_ledger.ledger.intents[0],
            absolute_deadline_ms=(
                graph.provider_ledger.ledger.intents[0].absolute_deadline_ms + 1
            ),
        )
        graph.provider_ledger = replace(
            graph.provider_ledger,
            ledger=replace(
                graph.provider_ledger.ledger,
                intents=(intent,),
            ),
        )
        graph.intents[intent_ref] = intent
    elif tamper == "typed_queue":
        assert row.typed_turn is not None
        calls = row.typed_turn.tool_calls
        graph.program = replace(
            graph.program,
            provider_transcript=(
                replace(
                    row,
                    typed_turn=replace(
                        row.typed_turn,
                        tool_calls=(calls[1], calls[0], *calls[2:]),
                    ),
                ),
            ),
        )
    elif tamper == "per_call_cap":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                per_call_generated_tokens=0,
            ),
        )
    elif tamper == "per_call_turns":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                per_call_turns=0,
            ),
        )
    elif tamper == "aggregate_tokens":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                aggregate_generated_tokens=0,
            ),
        )
    elif tamper == "aggregate_models":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                aggregate_model_calls=0,
            ),
        )
    elif tamper == "aggregate_turns":
        graph.authority = replace(
            graph.authority,
            subject_contract_caps=replace(
                graph.authority.subject_contract_caps,
                aggregate_turns=0,
            ),
        )
    elif tamper == "branch_pending":
        graph.receipt = replace(
            graph.receipt,
            branch_pending_calls=(row.typed_turn.tool_calls[0],),  # type: ignore[union-attr]
        )
    else:
        graph.receipt = replace(
            graph.receipt,
            trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
            terminal_failure_kind=prefix_index_module.FailureKind.MODEL,
            terminal_unexecuted_remainder=(
                row.typed_turn.tool_calls[0],  # type: ignore[union-attr]
            ),
        )

    with pytest.raises(ValueError):
        prefix_index_module._assert_execution_semantics(graph)


@pytest.mark.parametrize("overshoot", ["wall_before_mutation", "token_before_mutation"])
def test_s02d_replays_terminal_precedence_before_mutation_trigger(
    tmp_path: Path,
    overshoot: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    first = graph.tool_ledger.boundaries[0]
    graph.tool_ledger = replace(
        graph.tool_ledger,
        boundaries=(
            replace(
                first,
                mutation_committed=True,
                verifier_eligible_after=True,
                elapsed_ms=(
                    graph.authority.prefix_caps.wall_clock_ms + 1
                    if overshoot == "wall_before_mutation"
                    else first.elapsed_ms
                ),
            ),
        ),
    )
    row = graph.program.provider_transcript[0]
    assert row.typed_turn is not None
    if overshoot == "wall_before_mutation":
        cutoff = graph.authority.prefix_caps.wall_clock_ms + 1
        after_first = False
        shifted = []
        for read in graph.program.clock_trace:
            if read.label == "after_tool_call-1":
                after_first = True
            shifted.append(
                replace(read, uint64_ms=read.uint64_ms + cutoff - 5)
                if after_first
                else read
            )
        graph.program = replace(
            graph.program,
            clock_trace=tuple(shifted[:5]),
        )
    else:
        graph.authority = replace(
            graph.authority,
            prefix_caps=replace(
                graph.authority.prefix_caps,
                generated_tokens=row.reported_generated_tokens - 1,
            ),
        )
        graph.tool_ledger = replace(graph.tool_ledger, boundaries=())
        graph.program = replace(
            graph.program,
            clock_trace=graph.program.clock_trace[:3],
            tool_observations=(),
        )
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        tool_observations=(
            (
                replace(
                    graph.program.tool_observations[0],
                    mutation_committed=True,
                    verifier_eligible=True,
                ),
            )
            if overshoot == "wall_before_mutation"
            else ()
        ),
    )
    expected_wall = (
        graph.authority.prefix_caps.wall_clock_ms + 1
        if overshoot == "wall_before_mutation"
        else graph.provider_ledger.ledger.attempts[0].elapsed_ms
    )
    graph.receipt = replace(
        graph.receipt,
        prefix_caps=graph.authority.prefix_caps,
        trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        terminal_failure_kind=(
            prefix_index_module.FailureKind.TIMEOUT
            if overshoot == "wall_before_mutation"
            else prefix_index_module.FailureKind.TOKEN_CAP
        ),
        branch_pending_calls=(),
        terminal_unexecuted_remainder=(
            row.typed_turn.tool_calls[1:]
            if overshoot == "wall_before_mutation"
            else row.typed_turn.tool_calls
        ),
        counters=replace(
            graph.receipt.counters,
            tool_calls=1 if overshoot == "wall_before_mutation" else 0,
            wall_clock_ms=expected_wall,
        ),
        simulator_counters=replace(
            graph.receipt.simulator_counters,
            wall_clock_ms=expected_wall,
        ),
    )
    graph.snapshot = SimpleNamespace(  # type: ignore[assignment]
        episode_terminal=True,
        cumulative_mutation=False,
    )

    prefix_index_module._assert_execution_semantics(graph)


@pytest.mark.parametrize("subject_role", ["primary_subject", "user_simulator"])
def test_s02d_accepts_clean_provider_terminal_turn(
    tmp_path: Path,
    subject_role: str,
) -> None:
    graph = _terminal_turn_graph(tmp_path, subject_role=subject_role)

    prefix_index_module._assert_exact_execution_replay(graph)


def test_s02d_rejects_coherent_row_role_swap_against_task_actor_order(
    tmp_path: Path,
) -> None:
    graph = _terminal_turn_graph(
        tmp_path,
        subject_role="user_simulator",
        bind_derived_actor=False,
    )
    graph.authority = _replay_authority_with_actor_roles(
        graph.authority,
        ("primary_subject",),
    )  # type: ignore[assignment]

    with pytest.raises(ValueError, match="actor"):
        prefix_index_module._assert_exact_execution_replay(graph)


def test_s02d_rejects_initial_simulator_context_against_first_task_actor(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.authority = _replay_authority_with_actor_roles(
        graph.authority,
        ("primary_subject",),
    )  # type: ignore[assignment]
    snapshot_bytes = canonical_json_bytes(
        {
            "branch_pending_calls": [],
            "episode_terminal": False,
            "failure_kind": "none",
            "mutation_committed": False,
            "program_sha256": hashlib.sha256(graph.program_bytes).hexdigest(),
            "simulator_context": base64.b64encode(
                b"synthetic-simulator-context"
            ).decode("ascii"),
            "terminal_unexecuted_remainder": [],
            "turns": [],
            "verifier_eligible": False,
            "visible_context": base64.b64encode(b"task").decode("ascii"),
        },
        indent=None,
    )
    snapshot_ref = ArtifactRef(
        "environment_snapshot",
        "controller-artifacts/environment_snapshot/initial.json",
        hashlib.sha256(snapshot_bytes).hexdigest(),
        len(snapshot_bytes),
        "application/json",
    )
    graph.payloads[snapshot_ref] = snapshot_bytes
    graph.initial_restore = SimpleNamespace(  # type: ignore[assignment]
        episode_terminal=False,
        failure_kind=prefix_index_module.FailureKind.NONE,
        initial_environment_snapshot_ref=snapshot_ref,
    )

    with pytest.raises(ValueError, match="simulator context|actor"):
        prefix_index_module._assert_exact_execution_replay(graph)


def test_s02d_accepts_initially_terminal_empty_execution(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.authority = replace(graph.authority, actor_roles=())
    graph.initial_restore = SimpleNamespace(  # type: ignore[assignment]
        episode_terminal=True,
        failure_kind=prefix_index_module.FailureKind.NONE,
    )
    graph.snapshot = SimpleNamespace(  # type: ignore[assignment]
        episode_terminal=True,
        cumulative_mutation=False,
    )
    graph.program = replace(
        graph.program,
        provider_transcript=(),
        tool_observations=(),
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        clock_trace=graph.program.clock_trace[:1],
    )
    graph.provider_ledger = replace(
        graph.provider_ledger,
        ledger=replace(
            graph.provider_ledger.ledger,
            intents=(),
            intent_refs=(),
            attempts=(),
        ),
        attempt_refs=(),
    )
    graph.tool_ledger = replace(graph.tool_ledger, boundaries=())
    graph.receipt = replace(
        graph.receipt,
        trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        terminal_failure_kind=prefix_index_module.FailureKind.NONE,
        branch_pending_calls=(),
        terminal_unexecuted_remainder=(),
    )

    prefix_index_module._assert_exact_execution_replay(graph)


@pytest.mark.parametrize("initial_state", ["terminal", "failure"])
def test_s02d_rejects_dispatch_from_initially_terminal_or_failed_restore(
    tmp_path: Path,
    initial_state: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.initial_restore = SimpleNamespace(  # type: ignore[assignment]
        episode_terminal=initial_state == "terminal",
        failure_kind=(
            prefix_index_module.FailureKind.MODEL
            if initial_state == "failure"
            else prefix_index_module.FailureKind.NONE
        ),
    )

    with pytest.raises(ValueError, match="initial.*terminal|failed restore"):
        prefix_index_module._assert_exact_execution_replay(graph)


def test_s02d_rejects_terminal_turn_with_tools(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    assert row.response_ref is not None
    assert row.typed_turn is not None
    response = _response_bytes(
        finish_reason="terminal",
        text="not actually terminal",
        tool_calls=row.typed_turn.tool_calls,
    )
    graph.payloads[row.response_ref] = response
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                row,
                typed_turn=replace(
                    row.typed_turn,
                    text="not actually terminal",
                    generated_tokens=len(response),
                    finish_reason="terminal",
                ),
                reported_output_token_ids=tuple(response),
                reported_generated_tokens=len(response),
            ),
        ),
    )

    with pytest.raises(ValueError, match="terminal.*tools"):
        prefix_index_module._assert_exact_execution_replay(graph)


def test_s02d_rejects_row_after_clean_provider_terminal(
    tmp_path: Path,
) -> None:
    graph = _terminal_turn_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    first_intent = graph.provider_ledger.ledger.intents[0]
    first_attempt = graph.provider_ledger.ledger.attempts[0]
    second_seed = prefix_index_module.derive_call_seed(
        graph.authority.task_schedule.prefix_seed,
        "primary_subject",
        1,
    )
    second_event_ref = ArtifactRef(
        "synthetic_provider_event",
        "sources/terminal-second-event.json",
        "f" * 64,
        1,
        "application/json",
    )
    second_row = replace(
        row,
        call_index=1,
        seed=second_seed,
        provider_event_ref=second_event_ref,
    )
    graph.payloads[second_event_ref] = canonical_json_bytes(
        {
            "observed_at_ms": 5,
            "record_kind": "synthetic_raw_provider_event_v1",
            "schema_version": "1",
            "transport_kind": "response",
        },
        indent=None,
    )
    graph.authority = replace(
        graph.authority,
        actor_roles=("primary_subject", "primary_subject"),
        prefix_caps=replace(graph.authority.prefix_caps, model_calls=2),
        subject_contract_caps=replace(
            graph.authority.subject_contract_caps,
            aggregate_model_calls=2,
            aggregate_turns=2,
        ),
    )
    graph.program = replace(
        graph.program,
        provider_transcript=(row, second_row),
        clock_trace=(
            *graph.program.clock_trace,
            SyntheticClockRead("before_primary_subject_1", 4),
            SyntheticClockRead("after_primary_subject_1", 5),
        ),
    )
    object.__setattr__(
        graph.provider_ledger.ledger,
        "intents",
        (
            first_intent,
            replace(first_intent, call_index=1, seed=second_seed),
        ),
    )
    object.__setattr__(
        graph.provider_ledger.ledger,
        "attempts",
        (
            first_attempt,
            replace(
                first_attempt,
                call_index=1,
                seed=second_seed,
                elapsed_ms=4,
            ),
        ),
    )

    with pytest.raises(ValueError, match="terminal outcome"):
        prefix_index_module._assert_exact_execution_replay(graph)


@pytest.mark.parametrize("pretool_failure", ["tool_cap", "timeout"])
def test_s02d_uses_pretool_clock_as_terminal_wall_time(
    tmp_path: Path,
    pretool_failure: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    assert row.typed_turn is not None
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        clock_trace=graph.program.clock_trace[:4],
        tool_observations=(),
    )
    graph.tool_ledger = replace(graph.tool_ledger, boundaries=())
    failure = prefix_index_module.FailureKind.TOOL_CAP
    if pretool_failure == "tool_cap":
        graph.authority = replace(
            graph.authority,
            prefix_caps=replace(graph.authority.prefix_caps, tool_calls=0),
        )
    else:
        failure = prefix_index_module.FailureKind.TIMEOUT
        graph.authority = replace(
            graph.authority,
            prefix_caps=replace(graph.authority.prefix_caps, wall_clock_ms=3),
        )
        intent_ref = graph.provider_ledger.ledger.intent_refs[0]
        intent = replace(
            graph.provider_ledger.ledger.intents[0],
            absolute_deadline_ms=4,
        )
        graph.provider_ledger = replace(
            graph.provider_ledger,
            ledger=replace(graph.provider_ledger.ledger, intents=(intent,)),
        )
        graph.intents[intent_ref] = intent
    graph.receipt = replace(
        graph.receipt,
        prefix_caps=graph.authority.prefix_caps,
        trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        terminal_failure_kind=failure,
        branch_pending_calls=(),
        terminal_unexecuted_remainder=row.typed_turn.tool_calls,
        counters=replace(graph.receipt.counters, tool_calls=0, wall_clock_ms=4),
        simulator_counters=replace(
            graph.receipt.simulator_counters,
            wall_clock_ms=4,
        ),
    )
    graph.snapshot = SimpleNamespace(  # type: ignore[assignment]
        episode_terminal=True,
        cumulative_mutation=False,
    )

    prefix_index_module._assert_execution_semantics(graph)


def test_s02d_counts_parser_valid_turn_with_noncompleted_transport(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    assert row.typed_turn is not None
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                row,
                subject_role="user_simulator",
                completion_kind=RawProviderCompletionKind.PROVIDER_ERROR,
                typed_turn=replace(row.typed_turn, tool_calls=()),
            ),
        ),
    )

    assert (
        prefix_index_module._parsed_response_turn_count(
            program=graph.program,
            payloads=graph.payloads,
            subject_role="user_simulator",
        )
        == 1
    )


def test_s02d_rejects_provider_row_after_first_adverse_status(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    first_row = graph.program.provider_transcript[0]
    first_intent = graph.provider_ledger.ledger.intents[0]
    first_attempt = replace(
        graph.provider_ledger.ledger.attempts[0],
        status=prefix_index_module.ProviderAttemptStatus.PROVIDER_ERROR,
    )

    def fresh_controller_ref(role: str, salt: str) -> ArtifactRef:
        digest = hashlib.sha256(f"{role}:{salt}".encode()).hexdigest()
        return ArtifactRef(
            role,
            f"controller-artifacts/{role}/{digest}",
            digest,
            1,
            CONTROLLER_ROLE_MEDIA[role],
        )

    second_intent_ref = fresh_controller_ref(
        "provider_dispatch_intent",
        "second-intent",
    )
    second_attempt_ref = fresh_controller_ref("provider_attempt", "second-attempt")
    second_event_ref = fresh_controller_ref("provider_event", "second-event")
    second_settlement_ref = fresh_controller_ref(
        "provider_settlement",
        "second-settlement",
    )
    second_seed = first_row.seed + 1
    second_row = replace(first_row, call_index=1, seed=second_seed)
    second_intent = replace(first_intent, call_index=1, seed=second_seed)
    second_attempt = replace(
        graph.provider_ledger.ledger.attempts[0],
        dispatch_intent_ref=second_intent_ref,
        call_index=1,
        seed=second_seed,
        provider_event_ref=second_event_ref,
        elapsed_ms=13,
    )
    graph.provider_ledger = replace(
        graph.provider_ledger,
        ledger=replace(
            graph.provider_ledger.ledger,
            intents=(first_intent, second_intent),
            intent_refs=(
                graph.provider_ledger.ledger.intent_refs[0],
                second_intent_ref,
            ),
            attempts=(first_attempt, second_attempt),
        ),
        attempt_refs=(
            graph.provider_ledger.attempt_refs[0],
            second_attempt_ref,
        ),
    )
    first_settlement_ref = graph.cost_record.settlement_refs[0]
    graph.cost_record = replace(
        graph.cost_record,
        attempt_refs=(
            graph.provider_ledger.attempt_refs[0],
            second_attempt_ref,
        ),
        settlement_refs=(first_settlement_ref, second_settlement_ref),
    )
    graph.settlements[second_settlement_ref] = replace(
        graph.settlements[first_settlement_ref],
        call_index=1,
        seed=second_seed,
    )
    raw_event = json.loads(graph.payloads[first_row.provider_event_ref])
    raw_event["transport_kind"] = "provider_error"
    graph.payloads[first_row.provider_event_ref] = canonical_json_bytes(
        raw_event,
        indent=None,
    )
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                first_row,
                completion_kind=RawProviderCompletionKind.PROVIDER_ERROR,
            ),
            second_row,
        ),
        failure_injection=replace(
            graph.program.failure_injection,
            stage="provider_transport",
            subject_role="primary_subject",
            call_index=0,
        ),
        clock_trace=(
            *graph.program.clock_trace,
            SyntheticClockRead(
                "before_primary_subject_1",
                13,
            ),
            SyntheticClockRead(
                "after_primary_subject_1",
                14,
            ),
        ),
    )
    graph.authority = replace(
        graph.authority,
        actor_roles=("primary_subject", "primary_subject"),
    )

    with pytest.raises(ValueError, match="continues after terminal outcome"):
        prefix_index_module._assert_execution_semantics(graph)


@pytest.mark.parametrize(
    "tamper",
    ["swapped_provider_pair", "cross_stream_reorder", "unused_extra_read"],
)
def test_s02d_consumes_exact_clock_trace_sequence(
    tmp_path: Path,
    tamper: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    trace = list(graph.program.clock_trace)
    if tamper == "swapped_provider_pair":
        trace[1], trace[2] = trace[2], trace[1]
    elif tamper == "cross_stream_reorder":
        trace[2], trace[3] = trace[3], trace[2]
    else:
        trace.append(SyntheticClockRead("unused_extra_read", trace[-1].uint64_ms))
    object.__setattr__(graph.program, "clock_trace", tuple(trace))

    with pytest.raises(ValueError, match="clock"):
        prefix_index_module._assert_execution_semantics(graph)


def test_s02d_rejects_unconsumed_tool_observation(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    extra = replace(
        graph.program.tool_observations[-1],
        call_id="unconsumed-call",
    )
    graph.program = replace(
        graph.program,
        tool_observations=(*graph.program.tool_observations, extra),
    )

    with pytest.raises(ValueError, match="tool observation"):
        prefix_index_module._assert_execution_semantics(graph)


def test_s02d_rederives_provider_seed_from_schedule(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    changed_seed = row.seed + 1
    intent_ref = graph.provider_ledger.ledger.intent_refs[0]
    attempt_ref = graph.provider_ledger.attempt_refs[0]
    event_ref = graph.provider_ledger.ledger.attempts[0].provider_event_ref
    settlement_ref = graph.cost_record.settlement_refs[0]
    changed_intent = replace(
        graph.provider_ledger.ledger.intents[0],
        seed=changed_seed,
    )
    changed_attempt = replace(
        graph.provider_ledger.ledger.attempts[0],
        seed=changed_seed,
    )
    graph.program = replace(
        graph.program,
        provider_transcript=(replace(row, seed=changed_seed),),
    )
    graph.provider_ledger = replace(
        graph.provider_ledger,
        ledger=replace(
            graph.provider_ledger.ledger,
            intents=(changed_intent,),
            attempts=(changed_attempt,),
        ),
    )
    graph.intents[intent_ref] = changed_intent
    graph.attempts[attempt_ref] = changed_attempt
    graph.events[event_ref] = replace(
        graph.events[event_ref],
        seed=changed_seed,
    )
    graph.settlements[settlement_ref] = replace(
        graph.settlements[settlement_ref],
        seed=changed_seed,
    )
    graph.receipt = replace(
        graph.receipt,
        call_seeds=(replace(graph.receipt.call_seeds[0], seed=changed_seed),),
    )

    with pytest.raises(ValueError, match="seed"):
        prefix_index_module._assert_execution_semantics(graph)


def test_s02d_binds_edge_local_and_cumulative_mutation(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    boundaries = (
        replace(
            graph.tool_ledger.boundaries[0],
            mutation_committed=True,
            verifier_eligible_after=False,
        ),
        replace(
            graph.tool_ledger.boundaries[1],
            mutation_committed=False,
            verifier_eligible_after=True,
        ),
    )

    prefix_index_module._assert_mutation_semantics(
        boundaries=boundaries,
        final_edge_mutation=False,
        snapshot_cumulative=True,
    )
    with pytest.raises(ValueError, match="mutation"):
        prefix_index_module._assert_mutation_semantics(
            boundaries=boundaries,
            final_edge_mutation=True,
            snapshot_cumulative=False,
        )


def test_s02d_derives_trigger_instead_of_trusting_program_claim(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
    )

    with pytest.raises(ValueError, match="fresh replay outcome"):
        prefix_index_module._assert_execution_semantics(graph)


def test_s02d_seals_exact_schedule_order_after_fresh_graph_reload(
    tmp_path: Path,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    out = run_root / "prefix-index.json"

    ref = seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=out,
    )

    assert ref.role == "resampling_prefix_receipt"
    assert ref.relative_path == "prefix-index.json"
    assert ref.media_type == "application/json"
    record = validate_record(json.loads(out.read_bytes()))
    assert record["payload"]["schedule_ref"] == asdict(fixture.schedule_ref)  # type: ignore[index]
    assert [
        receipt["task_id"]  # type: ignore[index]
        for receipt in record["payload"]["task_receipts"]  # type: ignore[index]
    ] == ["task-1", "task-foreign"]


def test_s02d_full_seal_routing_probe_invokes_nonempty_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    nonempty = _nonempty_execution_graph(tmp_path / "nonempty")
    real_replay = prefix_index_module._assert_execution_semantics
    replayed_nonempty = False

    def replay_with_nonempty_probe(
        graph: prefix_index_module._CandidateGraph,
    ) -> None:
        nonlocal replayed_nonempty
        if not replayed_nonempty:
            real_replay(nonempty)
            replayed_nonempty = True
        real_replay(graph)

    monkeypatch.setattr(
        prefix_index_module,
        "_assert_execution_semantics",
        replay_with_nonempty_probe,
    )

    seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=run_root / "prefix-index.json",
    )

    assert replayed_nonempty


def test_s02d_full_seal_supplies_lane_authority_for_every_program_occurrence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    real_reconcile = prefix_index_module._assert_all_program_occurrences
    observed_programs = 0

    def capture_lane_authority(
        traversal: prefix_index_module._FreshTraversal,
        *,
        program_authorities: dict[ArtifactRef, object],
    ) -> None:
        nonlocal observed_programs
        programs = {
            ref
            for ref, value in traversal.decoded.items()
            if ref.role == "synthetic_execution_program"
            and isinstance(value, prefix_index_module.SyntheticPrefixProgram)
        }
        assert set(program_authorities) == programs
        observed_programs = len(programs)
        real_reconcile(
            traversal,
            program_authorities=program_authorities,
        )

    monkeypatch.setattr(
        prefix_index_module,
        "_assert_all_program_occurrences",
        capture_lane_authority,
    )
    seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=run_root / "prefix-index.json",
    )

    assert observed_programs >= 2


def test_s02d_reconciles_nonselected_reachable_program_leaves(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    fixture = ProviderAuthorityFixture.build(
        run_root,
        executable_sources=True,
    )
    selected_ref = fixture.refs["task-1_program"]
    foreign_ref = fixture.refs["task-foreign_program"]
    selected = load_synthetic_prefix_program(
        (run_root / selected_ref.relative_path).read_bytes()
    )
    foreign = load_synthetic_prefix_program(
        (run_root / foreign_ref.relative_path).read_bytes()
    )
    foreign = replace(
        foreign,
        grade_result=replace(foreign.grade_result, partial_reward=0.5),
    )
    leaf_refs = {
        selected.grade_result.evidence_ref,
        selected.verifier_result.evidence_ref,
    }
    payloads = {
        ref: (run_root / ref.relative_path).read_bytes()
        for ref in (selected_ref, foreign_ref, *leaf_refs)
    }
    traversal = prefix_index_module._FreshTraversal(
        visited={},
        path_bindings={},
        physical_bindings={},
        payloads=payloads,
        nested={},
        decoded={selected_ref: selected, foreign_ref: foreign},
        scientific_refs=set(),
    )
    authority_graph = _nonempty_execution_graph(tmp_path / "authority")
    selected_authority = _program_occurrence_authority(
        authority_graph,
        task_id=selected.task_id,
        actor_roles=(),
    )
    foreign_authority = _program_occurrence_authority(
        authority_graph,
        task_id=foreign.task_id,
        actor_roles=(),
    )

    with pytest.raises(ValueError, match="grade"):
        prefix_index_module._assert_all_program_occurrences(
            traversal,
            program_authorities={
                selected_ref: (selected_authority,),
                foreign_ref: (foreign_authority,),
            },
        )


@pytest.mark.parametrize(
    "tamper",
    ["raw_transport", "clock_extra", "tool_observation_extra"],
)
def test_s02d_replays_every_reachable_program_occurrence(
    tmp_path: Path,
    tamper: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    program_ref = graph.authority.program_ref
    if tamper == "raw_transport":
        event_ref = graph.program.provider_transcript[0].provider_event_ref
        raw_event = json.loads(graph.payloads[event_ref])
        raw_event["transport_kind"] = "provider_error"
        graph.payloads[event_ref] = canonical_json_bytes(raw_event, indent=None)
    elif tamper == "clock_extra":
        trace = (
            *graph.program.clock_trace,
            SyntheticClockRead(
                "unconsumed_nonselected_clock",
                graph.program.clock_trace[-1].uint64_ms,
            ),
        )
        graph.program = replace(graph.program, clock_trace=trace)
    else:
        graph.program = replace(
            graph.program,
            tool_observations=(
                *graph.program.tool_observations,
                replace(
                    graph.program.tool_observations[-1],
                    call_id="unconsumed-nonselected-tool",
                ),
            ),
        )
    traversal = prefix_index_module._FreshTraversal(
        visited={},
        path_bindings={},
        physical_bindings={},
        payloads=graph.payloads,
        nested={},
        decoded={program_ref: graph.program},
        scientific_refs=set(),
    )

    with pytest.raises(ValueError):
        prefix_index_module._assert_all_program_occurrences(
            traversal,
            program_authorities={
                program_ref: (_program_occurrence_authority(graph),),
            },
        )


def _program_occurrence_inputs(
    graph: prefix_index_module._CandidateGraph,
) -> tuple[dict[ArtifactRef, tuple[str, object]], dict[ArtifactRef, tuple[str, int]]]:
    responses = {
        row.response_ref: prefix_index_module.SyntheticResponseParser().parse(
            graph.payloads[row.response_ref]
        )
        for row in graph.program.provider_transcript
        if row.response_ref is not None
    }
    raw_events = {
        row.provider_event_ref: prefix_index_module._decode_raw_event(
            graph.payloads[row.provider_event_ref]
        )
        for row in graph.program.provider_transcript
    }
    return responses, raw_events


def _program_occurrence_authority(
    graph: prefix_index_module._CandidateGraph,
    *,
    prefix_caps: object | None = None,
    actor_roles: tuple[str, ...] | None = None,
    task_id: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        task_id=graph.program.task_id if task_id is None else task_id,
        prefix_seed=graph.authority.task_schedule.prefix_seed,
        actor_roles=(
            tuple(row.subject_role for row in graph.program.provider_transcript)
            if actor_roles is None
            else actor_roles
        ),
        prefix_caps=graph.authority.prefix_caps if prefix_caps is None else prefix_caps,
        simulator_caps=graph.authority.simulator_caps,
        subject_contract_caps=graph.authority.subject_contract_caps,
        simulator_contract_caps=graph.authority.simulator_contract_caps,
        subject_contract_ref=graph.authority.subject_contract_ref,
        simulator_contract_ref=graph.authority.simulator_contract_ref,
    )


def test_s02d_shared_program_validates_each_task_actor_order(
    tmp_path: Path,
) -> None:
    graph = _terminal_turn_graph(tmp_path, subject_role="user_simulator")
    program_ref = graph.authority.program_ref
    traversal = prefix_index_module._FreshTraversal(
        visited={},
        path_bindings={},
        physical_bindings={},
        payloads=graph.payloads,
        nested={},
        decoded={program_ref: graph.program},
        scientific_refs=set(),
    )

    with pytest.raises(ValueError, match="actor"):
        prefix_index_module._assert_all_program_occurrences(
            traversal,
            program_authorities={
                program_ref: (
                    _program_occurrence_authority(
                        graph,
                        actor_roles=("user_simulator",),
                    ),
                    _program_occurrence_authority(
                        graph,
                        actor_roles=("primary_subject",),
                    ),
                )
            },
        )


def test_s02d_nonselected_rejects_coherent_wrong_prefix_seed(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    graph.program = replace(
        graph.program,
        provider_transcript=(replace(row, seed=row.seed + 1),),
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="seed"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(graph),
        )


def test_s02d_nonselected_rejects_on_time_timeout_late_claim(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                row,
                completion_kind=RawProviderCompletionKind.TIMEOUT_LATE_RESPONSE,
            ),
        ),
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="completion"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(graph),
        )


def test_s02d_nonselected_accepts_provider_error_with_parsed_response(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    raw_event = json.loads(graph.payloads[row.provider_event_ref])
    raw_event["transport_kind"] = "provider_error"
    graph.payloads[row.provider_event_ref] = canonical_json_bytes(
        raw_event,
        indent=None,
    )
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                row,
                completion_kind=RawProviderCompletionKind.PROVIDER_ERROR,
            ),
        ),
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        clock_trace=graph.program.clock_trace[:3],
        tool_observations=(),
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    prefix_index_module._assert_program_occurrence_replay(
        program=graph.program,
        responses=responses,
        raw_events=raw_events,
        payloads=graph.payloads,
        authority=_program_occurrence_authority(graph),
    )


def test_s02d_nonselected_token_overshoot_stops_before_later_row(
    tmp_path: Path,
) -> None:
    graph = _terminal_turn_graph(tmp_path)
    first = graph.program.provider_transcript[0]
    assert first.response_ref is not None
    response = _response_bytes(finish_reason="stop", text="done")
    first = replace(
        first,
        typed_turn=SubjectTurn("done", (), len(response), "stop"),
        reported_output_token_ids=tuple(response),
        reported_generated_tokens=len(response),
    )
    second_event = canonical_json_bytes(
        {
            "observed_at_ms": 5,
            "record_kind": "synthetic_raw_provider_event_v1",
            "schema_version": "1",
            "transport_kind": "response",
        },
        indent=None,
    )
    second_event_ref = ArtifactRef(
        "synthetic_provider_event",
        "sources/token-overshoot-second-event.json",
        hashlib.sha256(second_event).hexdigest(),
        len(second_event),
        "application/json",
    )
    second = replace(
        first,
        call_index=1,
        seed=prefix_index_module.derive_call_seed(
            graph.authority.task_schedule.prefix_seed,
            "primary_subject",
            1,
        ),
        provider_event_ref=second_event_ref,
    )
    graph.payloads[first.response_ref] = response
    graph.payloads[second_event_ref] = second_event
    graph.program = replace(
        graph.program,
        provider_transcript=(first, second),
        clock_trace=(
            SyntheticClockRead("prefix_epoch", 1),
            SyntheticClockRead("before_primary_subject_0", 2),
            SyntheticClockRead("after_primary_subject_0", 3),
            SyntheticClockRead("before_primary_subject_1", 4),
            SyntheticClockRead("after_primary_subject_1", 5),
        ),
    )
    responses, raw_events = _program_occurrence_inputs(graph)
    prefix_caps = replace(
        graph.authority.prefix_caps,
        generated_tokens=len(response) - 1,
        model_calls=2,
    )

    with pytest.raises(ValueError, match="continues after terminal outcome"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(
                graph,
                prefix_caps=prefix_caps,
                actor_roles=("primary_subject", "primary_subject"),
            ),
        )


def test_s02d_nonselected_rejects_clean_terminal_tool_with_remainder(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        tool_observations=(
            replace(
                graph.program.tool_observations[0],
                episode_terminal=True,
            ),
        ),
        clock_trace=graph.program.clock_trace[:5],
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="clean terminal.*remainder"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(graph),
        )


def test_s02d_nonselected_rejects_execution_past_first_eligible_mutation(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.FIRST_ELIGIBLE_MUTATION,
        tool_observations=(
            replace(
                graph.program.tool_observations[0],
                mutation_committed=True,
                verifier_eligible=True,
            ),
            *graph.program.tool_observations[1:],
        ),
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="unconsumed|first eligible|trigger"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(graph),
        )


def test_s02d_nonselected_rejects_fifth_tool_after_fourth_tool_trigger(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    assert row.typed_turn is not None
    assert row.response_ref is not None
    fifth_call = replace(row.typed_turn.tool_calls[-1], call_id="call-5")
    response = _response_bytes(
        finish_reason=row.typed_turn.finish_reason,
        text=row.typed_turn.text,
        tool_calls=(*row.typed_turn.tool_calls, fifth_call),
    )
    last_clock = graph.program.clock_trace[-1].uint64_ms
    graph.payloads[row.response_ref] = response
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                row,
                typed_turn=replace(
                    row.typed_turn,
                    tool_calls=(*row.typed_turn.tool_calls, fifth_call),
                    generated_tokens=len(response),
                ),
                reported_output_token_ids=tuple(response),
                reported_generated_tokens=len(response),
            ),
        ),
        tool_observations=(
            *graph.program.tool_observations,
            replace(
                graph.program.tool_observations[-1],
                call_id=fifth_call.call_id,
            ),
        ),
        clock_trace=(
            *graph.program.clock_trace,
            SyntheticClockRead(
                f"before_tool_{fifth_call.call_id}",
                last_clock + 1,
            ),
            SyntheticClockRead(
                f"after_tool_{fifth_call.call_id}",
                last_clock + 2,
            ),
        ),
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="unconsumed|fourth|trigger"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(
                graph,
                prefix_caps=replace(
                    graph.authority.prefix_caps,
                    tool_calls=5,
                ),
            ),
        )


def test_s02d_nonselected_rejects_expected_trigger_tamper(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="trigger"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(graph),
        )


def test_s02d_nonselected_rejects_nonterminal_no_tool_eof(
    tmp_path: Path,
) -> None:
    graph = _terminal_turn_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    assert row.response_ref is not None
    response = _response_bytes(finish_reason="stop", text="still alive")
    graph.payloads[row.response_ref] = response
    graph.program = replace(
        graph.program,
        provider_transcript=(
            replace(
                row,
                typed_turn=SubjectTurn("still alive", (), len(response), "stop"),
                reported_output_token_ids=tuple(response),
                reported_generated_tokens=len(response),
            ),
        ),
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="nonterminal|live|end state"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(graph),
        )


def test_s02d_nonselected_rejects_subfour_tool_nonterminal_eof(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    row = graph.program.provider_transcript[0]
    assert row.typed_turn is not None
    assert row.response_ref is not None
    calls = row.typed_turn.tool_calls[:3]
    response = _response_bytes(
        finish_reason=row.typed_turn.finish_reason,
        text=row.typed_turn.text,
        tool_calls=calls,
    )
    graph.payloads[row.response_ref] = response
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        provider_transcript=(
            replace(
                row,
                typed_turn=replace(
                    row.typed_turn,
                    tool_calls=calls,
                    generated_tokens=len(response),
                ),
                reported_output_token_ids=tuple(response),
                reported_generated_tokens=len(response),
            ),
        ),
        tool_observations=graph.program.tool_observations[:3],
        clock_trace=graph.program.clock_trace[:9],
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="nonterminal|live|end state"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(graph),
        )


def test_s02d_nonselected_rejects_unexplained_zero_tool_evidence(
    tmp_path: Path,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    graph.program = replace(
        graph.program,
        clock_trace=graph.program.clock_trace[:3],
        tool_observations=(),
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    with pytest.raises(ValueError, match="tool"):
        prefix_index_module._assert_program_occurrence_replay(
            program=graph.program,
            responses=responses,
            raw_events=raw_events,
            payloads=graph.payloads,
            authority=_program_occurrence_authority(graph),
        )


@pytest.mark.parametrize("pretool_failure", ["tool_cap", "timeout"])
def test_s02d_nonselected_accepts_causal_pretool_failure(
    tmp_path: Path,
    pretool_failure: str,
) -> None:
    graph = _nonempty_execution_graph(tmp_path)
    caps = graph.authority.prefix_caps
    if pretool_failure == "tool_cap":
        caps = replace(caps, tool_calls=0)
    else:
        caps = replace(caps, wall_clock_ms=3)
    graph.program = replace(
        graph.program,
        expected_trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        clock_trace=graph.program.clock_trace[:4],
        tool_observations=(),
    )
    responses, raw_events = _program_occurrence_inputs(graph)

    prefix_index_module._assert_program_occurrence_replay(
        program=graph.program,
        responses=responses,
        raw_events=raw_events,
        payloads=graph.payloads,
        authority=_program_occurrence_authority(graph, prefix_caps=caps),
    )


@pytest.mark.parametrize("case", ["duplicate", "reverse"])
def test_s02d_rejects_nonexact_candidate_roster(
    tmp_path: Path,
    case: str,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    invalid = (
        (candidates[0], candidates[0])
        if case == "duplicate"
        else tuple(reversed(candidates))
    )

    with pytest.raises((TypeError, ValueError)):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=invalid,
            out=run_root / "prefix-index.json",
        )

    assert not (run_root / "prefix-index.json").exists()


def test_s02d_rejects_reserved_or_existing_destination(tmp_path: Path) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    existing = run_root / "prefix-index.json"
    existing.write_bytes(b"do not overwrite")

    for out in (
        existing,
        run_root / "controller-artifacts" / "prefix-index.json",
    ):
        with pytest.raises((FileExistsError, ValueError)):
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=out,
            )

    assert existing.read_bytes() == b"do not overwrite"


def test_s02d_rejects_symlink_destination_component(tmp_path: Path) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (run_root / "publication-link").symlink_to(outside, target_is_directory=True)

    with pytest.raises((OSError, ValueError)):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=run_root / "publication-link" / "prefix-index.json",
        )

    assert not (outside / "prefix-index.json").exists()


def test_s02d_uses_one_scientific_reader_for_the_whole_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    real_enter = prefix_index_module.ScientificRefReader.__enter__
    entered = 0

    def counted_enter(
        reader: object,
    ) -> object:
        nonlocal entered
        entered += 1
        return real_enter(reader)  # type: ignore[arg-type]

    monkeypatch.setattr(
        prefix_index_module.ScientificRefReader,
        "__enter__",
        counted_enter,
    )
    real_authority_load = (
        prefix_index_module._load_prefix_execution_authority_and_plan_with_reader
    )
    authority_loads = 0

    def reader_bound_authority_load(*args: object, **kwargs: object) -> object:
        nonlocal authority_loads
        authority_loads += 1
        assert kwargs.get("scientific_reader") is not None
        return real_authority_load(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        prefix_index_module,
        "_load_prefix_execution_authority_and_plan_with_reader",
        reader_bound_authority_load,
    )
    seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=run_root / "prefix-index.json",
    )

    assert entered == 1
    assert authority_loads == 1


@pytest.mark.parametrize(
    "reader_type",
    [
        prefix_index_module.ScientificRefReader,
        prefix_index_module.ControllerArtifactResolver,
        prefix_index_module.AuthorityRefReader,
    ],
)
def test_s02d_rejects_reader_bound_to_another_root_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reader_type: type[object],
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    monkeypatch.setattr(
        reader_type,
        "bound_root_identity",
        property(lambda _reader: (-1, -1)),
        raising=False,
    )

    with pytest.raises(
        ValueError,
        match="reader root identity differs",
    ):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=run_root / "prefix-index.json",
        )

    assert not (run_root / "prefix-index.json").exists()


def test_s02d_rejects_cross_class_physical_alias_in_one_transaction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    shared_identity = (999_991, 999_983)
    real_scientific = prefix_index_module.ScientificRefReader.read_bound
    real_authority = prefix_index_module.AuthorityRefReader.read_bound

    def scientific_alias(reader: object, ref: ArtifactRef) -> object:
        bound = real_scientific(reader, ref)  # type: ignore[arg-type]
        return (
            replace(
                bound,
                st_dev=shared_identity[0],
                st_ino=shared_identity[1],
            )
            if ref == fixture.schedule_ref
            else bound
        )

    def authority_alias(reader: object, ref: ArtifactRef) -> object:
        bound = real_authority(reader, ref)  # type: ignore[arg-type]
        return replace(
            bound,
            st_dev=shared_identity[0],
            st_ino=shared_identity[1],
        )

    monkeypatch.setattr(
        prefix_index_module.ScientificRefReader,
        "read_bound",
        scientific_alias,
    )
    monkeypatch.setattr(
        prefix_index_module.AuthorityRefReader,
        "read_bound",
        authority_alias,
    )

    with pytest.raises(ValueError, match="physical file"):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=run_root / "prefix-index.json",
        )


@pytest.mark.parametrize("operation", ["write", "close"])
def test_s02d_publication_fault_removes_only_owned_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    target = run_root / "prefix-index.json"
    real_write = prefix_index_module.os.write
    real_close = prefix_index_module.os.close
    injected = False

    def is_target(descriptor: int) -> bool:
        try:
            return Path(f"/proc/self/fd/{descriptor}").resolve() == target
        except OSError:
            return False

    def failing_write(descriptor: int, payload: object) -> int:
        nonlocal injected
        if not injected and is_target(descriptor):
            injected = True
            raise OSError("injected write failure")
        return real_write(descriptor, payload)  # type: ignore[arg-type]

    def failing_close(descriptor: int) -> None:
        nonlocal injected
        if not injected and is_target(descriptor):
            injected = True
            real_close(descriptor)
            raise OSError("injected close failure")
        real_close(descriptor)

    monkeypatch.setattr(
        prefix_index_module.os,
        operation,
        failing_write if operation == "write" else failing_close,
    )
    root_descriptor = prefix_index_module.os.open(
        run_root,
        prefix_index_module._DIRECTORY_FLAGS,
    )
    try:
        with pytest.raises(BaseException):
            prefix_index_module._publish_once(
                root_descriptor=root_descriptor,
                relative_path="prefix-index.json",
                payload=b"payload",
            )
    finally:
        prefix_index_module.os.close(root_descriptor)

    assert injected
    assert not target.exists()


@pytest.mark.parametrize(
    "stage",
    [
        "parent_fsync",
        "reopen",
        "read",
        "verification_stat",
        "semantic_validation",
        "directory_close",
        "verification_close",
    ],
)
def test_s02d_late_publication_failure_rolls_back_and_retry_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    real_open = prefix_index_module.os.open
    real_read = prefix_index_module.os.read
    real_fsync = prefix_index_module.os.fsync
    real_stat = prefix_index_module.os.stat
    real_close = prefix_index_module.os.close
    real_validate = prefix_index_module.validate_record
    real_seal_bound = prefix_index_module._seal_bound_prefix_index
    injected = False
    verification_read = False
    outer_root_descriptor: int | None = None

    def descriptor_path(descriptor: int) -> Path | None:
        try:
            return Path(f"/proc/self/fd/{descriptor}").resolve()
        except OSError:
            return None

    def failing_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        nonlocal injected
        if (
            stage == "reopen"
            and not injected
            and target.exists()
            and path == "prefix-index.json"
            and flags & prefix_index_module.os.O_ACCMODE
            == prefix_index_module.os.O_RDONLY
        ):
            injected = True
            raise OSError("injected reopen failure")
        return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

    def failing_read(descriptor: int, count: int) -> bytes:
        nonlocal injected, verification_read
        if descriptor_path(descriptor) == target:
            verification_read = True
            if stage == "read" and not injected:
                injected = True
                raise OSError("injected verification read failure")
        return real_read(descriptor, count)

    def failing_stat(
        path: object,
        *args: object,
        **kwargs: object,
    ) -> object:
        nonlocal injected
        if (
            stage == "verification_stat"
            and not injected
            and verification_read
            and path == "prefix-index.json"
        ):
            injected = True
            raise OSError("injected verification stat failure")
        return real_stat(path, *args, **kwargs)

    def failing_validate(record: object) -> object:
        nonlocal injected
        if stage == "semantic_validation" and not injected and verification_read:
            injected = True
            raise ValueError("injected semantic verification failure")
        return real_validate(record)  # type: ignore[arg-type]

    def failing_fsync(descriptor: int) -> None:
        nonlocal injected
        if (
            stage == "parent_fsync"
            and not injected
            and target.exists()
            and descriptor_path(descriptor) == run_root
        ):
            injected = True
            raise OSError("injected parent fsync failure")
        real_fsync(descriptor)

    def failing_close(descriptor: int) -> None:
        nonlocal injected
        path = descriptor_path(descriptor)
        should_fail = (
            stage == "directory_close"
            and not injected
            and target.exists()
            and path == run_root
            and descriptor != outer_root_descriptor
        ) or (
            stage == "verification_close"
            and not injected
            and verification_read
            and path == target
        )
        if should_fail:
            injected = True
            real_close(descriptor)
            raise OSError(f"injected {stage} failure")
        real_close(descriptor)

    def capture_outer_root(*args: object, **kwargs: object) -> object:
        nonlocal outer_root_descriptor
        outer_root_descriptor = kwargs["root_descriptor"]  # type: ignore[assignment]
        return real_seal_bound(*args, **kwargs)  # type: ignore[arg-type]

    with monkeypatch.context() as scoped:
        scoped.setattr(prefix_index_module.os, "open", failing_open)
        scoped.setattr(prefix_index_module.os, "read", failing_read)
        scoped.setattr(prefix_index_module.os, "stat", failing_stat)
        scoped.setattr(prefix_index_module.os, "fsync", failing_fsync)
        scoped.setattr(prefix_index_module.os, "close", failing_close)
        scoped.setattr(prefix_index_module, "validate_record", failing_validate)
        scoped.setattr(
            prefix_index_module,
            "_seal_bound_prefix_index",
            capture_outer_root,
        )
        with pytest.raises(BaseException):
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=target,
            )

    assert injected
    assert not target.exists()
    seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=target,
    )
    assert target.is_file()


def test_s02d_locked_root_fstat_failure_releases_transaction_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    real_fstat = prefix_index_module.os.fstat
    leaked_descriptor: int | None = None
    injected = False

    def failing_fstat(descriptor: int) -> object:
        nonlocal injected, leaked_descriptor
        try:
            descriptor_path = Path(f"/proc/self/fd/{descriptor}").resolve()
        except OSError:
            descriptor_path = None
        if not injected and descriptor_path == run_root:
            injected = True
            leaked_descriptor = descriptor
            raise OSError("injected locked-root fstat failure")
        return real_fstat(descriptor)

    with monkeypatch.context() as scoped:
        scoped.setattr(prefix_index_module.os, "fstat", failing_fstat)
        with pytest.raises(OSError, match="locked-root fstat"):
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=target,
            )

    contender = os.open(run_root, prefix_index_module._DIRECTORY_FLAGS)
    try:
        fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(contender, fcntl.LOCK_UN)
    finally:
        os.close(contender)
        if leaked_descriptor is not None:
            try:
                os.close(leaked_descriptor)
            except OSError:
                pass

    assert injected
    assert not target.exists()


def test_s02d_postcommit_lock_close_failure_preserves_verified_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    real_close = prefix_index_module.os.close
    real_seal_bound = prefix_index_module._seal_bound_prefix_index
    outer_root_descriptor: int | None = None
    injected = False

    def capture_outer_root(*args: object, **kwargs: object) -> object:
        nonlocal outer_root_descriptor
        outer_root_descriptor = kwargs["root_descriptor"]  # type: ignore[assignment]
        return real_seal_bound(*args, **kwargs)  # type: ignore[arg-type]

    def failing_close(descriptor: int) -> None:
        nonlocal injected
        if not injected and descriptor == outer_root_descriptor and target.exists():
            injected = True
            real_close(descriptor)
            raise OSError("injected postcommit lock close failure")
        real_close(descriptor)

    with monkeypatch.context() as scoped:
        scoped.setattr(prefix_index_module.os, "close", failing_close)
        scoped.setattr(
            prefix_index_module,
            "_seal_bound_prefix_index",
            capture_outer_root,
        )
        with pytest.raises(BaseException) as captured:
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=target,
            )

    assert injected
    assert "committed" in repr(captured.value).lower()
    assert validate_record(json.loads(target.read_bytes()))


def _source_line(function: object, fragment: str) -> int:
    lines, start = inspect.getsourcelines(function)
    matches = [start + index for index, line in enumerate(lines) if fragment in line]
    if len(matches) != 1:
        raise AssertionError(f"source fragment {fragment!r} is not unique")
    return matches[0]


def test_s02d_interrupt_after_locked_fstat_is_precommit_and_releases_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    function = prefix_index_module.seal_prefix_index
    fstat_line = _source_line(function, "os.fstat(descriptor)")
    armed = False
    outer_descriptor: int | None = None
    real_flock = prefix_index_module.fcntl.flock

    def capture_flock(descriptor: int, operation: int) -> object:
        nonlocal outer_descriptor
        if operation == fcntl.LOCK_EX | fcntl.LOCK_NB:
            outer_descriptor = descriptor
        return real_flock(descriptor, operation)

    def interrupt_after_fstat(
        frame: object,
        event: str,
        _argument: object,
    ) -> object:
        nonlocal armed
        if getattr(frame, "f_code") is function.__code__ and event == "line":
            line = getattr(frame, "f_lineno")
            if armed and line != fstat_line:
                sys.settrace(None)
                raise KeyboardInterrupt("injected after locked fstat")
            if line == fstat_line:
                armed = True
        return interrupt_after_fstat

    with monkeypatch.context() as scoped:
        scoped.setattr(prefix_index_module.fcntl, "flock", capture_flock)
        sys.settrace(interrupt_after_fstat)
        try:
            with pytest.raises(BaseException) as captured:
                seal_prefix_index(
                    run_root=run_root,
                    schedule_ref=fixture.schedule_ref,
                    candidate_refs=candidates,
                    out=target,
                )
        finally:
            sys.settrace(None)

    try:
        assert type(captured.value) is BaseExceptionGroup
        assert "precommit" in repr(captured.value).lower()
        assert not target.exists()
        contender = os.open(run_root, prefix_index_module._DIRECTORY_FLAGS)
        try:
            real_flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            real_flock(contender, fcntl.LOCK_UN)
        finally:
            os.close(contender)
    finally:
        if outer_descriptor is not None:
            try:
                os.close(outer_descriptor)
            except OSError:
                pass


def test_s02d_interrupt_before_verified_publication_return_rolls_back(
    tmp_path: Path,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    function = prefix_index_module._seal_bound_prefix_index
    return_line = _source_line(function, "return published")

    def interrupt_before_return(
        frame: object,
        event: str,
        _argument: object,
    ) -> object:
        if (
            getattr(frame, "f_code") is function.__code__
            and event == "line"
            and getattr(frame, "f_lineno") == return_line
        ):
            sys.settrace(None)
            raise KeyboardInterrupt("injected before verified publication return")
        return interrupt_before_return

    sys.settrace(interrupt_before_return)
    try:
        with pytest.raises(BaseException) as captured:
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=target,
            )
    finally:
        sys.settrace(None)

    assert type(captured.value) is BaseExceptionGroup
    assert "precommit" in repr(captured.value).lower()
    assert not target.exists()


def test_s02d_interrupt_after_verified_result_is_committed_residual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    function = prefix_index_module.seal_prefix_index
    real_seal_bound = prefix_index_module._seal_bound_prefix_index
    armed = False

    def arm_after_verified(*args: object, **kwargs: object) -> object:
        nonlocal armed
        result = real_seal_bound(*args, **kwargs)  # type: ignore[arg-type]
        armed = True
        return result

    def interrupt_after_verified(
        frame: object,
        event: str,
        _argument: object,
    ) -> object:
        if armed and getattr(frame, "f_code") is function.__code__ and event == "line":
            sys.settrace(None)
            raise KeyboardInterrupt("injected after verified result")
        return interrupt_after_verified

    with monkeypatch.context() as scoped:
        scoped.setattr(
            prefix_index_module,
            "_seal_bound_prefix_index",
            arm_after_verified,
        )
        sys.settrace(interrupt_after_verified)
        try:
            with pytest.raises(BaseException) as captured:
                seal_prefix_index(
                    run_root=run_root,
                    schedule_ref=fixture.schedule_ref,
                    candidate_refs=candidates,
                    out=target,
                )
        finally:
            sys.settrace(None)

    assert type(captured.value) is BaseExceptionGroup
    assert "committed" in repr(captured.value).lower()
    assert validate_record(json.loads(target.read_bytes()))


def test_s02d_interrupt_before_cleanup_classification_is_committed_residual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    function = prefix_index_module.seal_prefix_index
    real_close = prefix_index_module.os.close
    real_seal_bound = prefix_index_module._seal_bound_prefix_index
    outer_descriptor: int | None = None
    armed = False

    def capture_outer(*args: object, **kwargs: object) -> object:
        nonlocal outer_descriptor
        outer_descriptor = kwargs["root_descriptor"]  # type: ignore[assignment]
        return real_seal_bound(*args, **kwargs)  # type: ignore[arg-type]

    def arm_after_close(descriptor: int) -> None:
        nonlocal armed
        real_close(descriptor)
        if descriptor == outer_descriptor:
            armed = True

    def interrupt_before_classification(
        frame: object,
        event: str,
        _argument: object,
    ) -> object:
        if armed and getattr(frame, "f_code") is function.__code__ and event == "line":
            sys.settrace(None)
            raise KeyboardInterrupt("injected before cleanup classification")
        return interrupt_before_classification

    with monkeypatch.context() as scoped:
        scoped.setattr(prefix_index_module.os, "close", arm_after_close)
        scoped.setattr(
            prefix_index_module,
            "_seal_bound_prefix_index",
            capture_outer,
        )
        sys.settrace(interrupt_before_classification)
        try:
            with pytest.raises(BaseException) as captured:
                seal_prefix_index(
                    run_root=run_root,
                    schedule_ref=fixture.schedule_ref,
                    candidate_refs=candidates,
                    out=target,
                )
        finally:
            sys.settrace(None)

    assert type(captured.value) is BaseExceptionGroup
    assert "committed" in repr(captured.value).lower()
    assert validate_record(json.loads(target.read_bytes()))


def test_s02d_rejects_when_cooperative_root_transaction_lock_is_held(
    tmp_path: Path,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    target = run_root / "prefix-index.json"
    competing_descriptor = os.open(
        run_root,
        prefix_index_module._DIRECTORY_FLAGS,
    )
    fcntl.flock(competing_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(BaseException, match="lock|lease"):
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=target,
            )
    finally:
        fcntl.flock(competing_descriptor, fcntl.LOCK_UN)
        os.close(competing_descriptor)

    assert not target.exists()


def test_s02d_reports_prequarantine_ownership_loss_and_preserves_replacement(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    target = run_root / "prefix-index.json"
    survivor = run_root / "owned-survivor"
    root_descriptor = prefix_index_module.os.open(
        run_root,
        prefix_index_module._DIRECTORY_FLAGS,
    )
    owned = prefix_index_module._publish_once(
        root_descriptor=root_descriptor,
        relative_path="prefix-index.json",
        payload=b"owned-payload",
    )
    os.rename(target, survivor)
    target.write_bytes(b"replacement")
    try:
        with pytest.raises(BaseException, match="rollback incomplete") as captured:
            prefix_index_module._rollback_owned_publication(
                root_descriptor=root_descriptor,
                owned=owned,
            )
    finally:
        prefix_index_module.os.close(root_descriptor)

    assert "ownership lost" in repr(captured.value)
    assert target.read_bytes() == b"replacement"
    assert survivor.read_bytes() == b"owned-payload"
