from __future__ import annotations

from dataclasses import asdict, replace
import hashlib
import inspect
import json
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.evidence import ProviderAttemptStatus
from pneuma_lab.resampling_null.controller import derive_call_seed
from pneuma_lab.resampling_null.prefix_contracts import (
    ImplementationDescriptor,
    RawProviderCompletionKind,
    RawProviderObservation,
    SyntheticClockRead,
    load_synthetic_prefix_program,
)
from pneuma_lab.resampling_null.synthetic_prefix_loop import (
    REGISTERED_LOOP_DESCRIPTOR_FIELDS,
    SyntheticProviderActor,
    SyntheticTraceMeter,
    _derive_provider_status,
    _open_prefix_loop,
    _pre_dispatch_failure,
    _pre_provider_action_failure,
    _render_request,
    _validate_descriptor_registry,
    _validate_provider_observation,
)
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    BranchCaps,
    BranchSlot,
    BranchSlotSet,
    CallContractCaps,
    FailureKind,
    GroupKind,
    GroupLabel,
    PrefixCaps,
    ResourceCounters,
    SubjectTurn,
    TaskSchedule,
    TaskSpec,
    ToolCall,
    TriggerReason,
)
from pneuma_lab.resampling_null.execution_authority import PrefixExecutionAuthority
from tests.resampling_null.test_s02c_initial_restore import _authority


def _ref(role: str, payload: bytes, media_type: str) -> ArtifactRef:
    return ArtifactRef(
        role=role,
        relative_path=f"sources/{role}-{hashlib.sha256(payload).hexdigest()}",
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type=media_type,
    )


@pytest.mark.parametrize(
    (
        "observed_ms",
        "deadline_ms",
        "response_present",
        "transport",
        "parser",
        "expected",
    ),
    [
        (11, 10, True, "response", "turn", ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE),
        (
            11,
            10,
            True,
            "provider_error",
            "refusal",
            ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE,
        ),
        (
            11,
            10,
            True,
            "infrastructure_error",
            "malformed",
            ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE,
        ),
        (
            11,
            10,
            False,
            "provider_error",
            "not_applicable",
            ProviderAttemptStatus.TIMEOUT_NO_RESPONSE,
        ),
        (
            11,
            10,
            False,
            "infrastructure_error",
            "not_applicable",
            ProviderAttemptStatus.TIMEOUT_NO_RESPONSE,
        ),
        (
            11,
            10,
            False,
            "timeout_no_response",
            "not_applicable",
            ProviderAttemptStatus.TIMEOUT_NO_RESPONSE,
        ),
        (
            10,
            10,
            False,
            "provider_error",
            "not_applicable",
            ProviderAttemptStatus.PROVIDER_ERROR,
        ),
        (
            10,
            10,
            False,
            "infrastructure_error",
            "not_applicable",
            ProviderAttemptStatus.INFRASTRUCTURE_ERROR,
        ),
        (10, 10, True, "provider_error", "turn", ProviderAttemptStatus.PROVIDER_ERROR),
        (
            10,
            10,
            True,
            "infrastructure_error",
            "refusal",
            ProviderAttemptStatus.INFRASTRUCTURE_ERROR,
        ),
        (10, 10, True, "response", "refusal", ProviderAttemptStatus.REFUSAL),
        (
            10,
            10,
            True,
            "response",
            "malformed",
            ProviderAttemptStatus.MALFORMED_RESPONSE,
        ),
        (10, 10, True, "response", "turn", ProviderAttemptStatus.COMPLETED),
    ],
)
def test_provider_truth_table_is_controller_derived(
    observed_ms: int,
    deadline_ms: int,
    response_present: bool,
    transport: str,
    parser: str,
    expected: ProviderAttemptStatus,
) -> None:
    assert (
        _derive_provider_status(
            observed_ms=observed_ms,
            deadline_ms=deadline_ms,
            response_present=response_present,
            transport=transport,
            parser=parser,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("response_present", "transport", "parser"),
    [
        (False, "response", "not_applicable"),
        (False, "timeout_no_response", "not_applicable"),
        (False, "provider_error", "turn"),
        (True, "timeout_no_response", "turn"),
        (True, "response", "not_applicable"),
        (True, "response", "unknown"),
    ],
)
def test_provider_truth_table_rejects_every_unlisted_on_time_combination(
    response_present: bool,
    transport: str,
    parser: str,
) -> None:
    with pytest.raises(ValueError, match="unlisted"):
        _derive_provider_status(
            observed_ms=10,
            deadline_ms=10,
            response_present=response_present,
            transport=transport,
            parser=parser,
        )


def test_trace_meter_derives_and_seals_program_clock_state(tmp_path: Path) -> None:
    authority = _loop_authority(tmp_path)
    program_bytes = (tmp_path / authority.program_ref.relative_path).read_bytes()
    program = load_synthetic_prefix_program(program_bytes)
    meter = SyntheticTraceMeter(program_bytes=program_bytes)

    assert (
        meter.read(
            label="prefix_epoch",
            program_sha256=hashlib.sha256(program_bytes).hexdigest(),
        )
        == program.clock_trace[0].uint64_ms
    )
    with pytest.raises(ValueError, match="label"):
        meter.read(
            label="wrong",
            program_sha256=hashlib.sha256(program_bytes).hexdigest(),
        )
    for row in program.clock_trace[1:]:
        meter.read(
            label=row.label,
            program_sha256=hashlib.sha256(program_bytes).hexdigest(),
        )
    meter._assert_exhausted()

    with pytest.raises(ValueError, match="digest"):
        SyntheticTraceMeter(program_bytes=program_bytes).read(
            label="prefix_epoch",
            program_sha256="0" * 64,
        )


def test_trace_meter_has_closed_program_only_surface_and_rejects_drift(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)
    program_bytes = (tmp_path / authority.program_ref.relative_path).read_bytes()
    program = load_synthetic_prefix_program(program_bytes)

    assert tuple(inspect.signature(SyntheticTraceMeter).parameters) == (
        "program_bytes",
    )
    with pytest.raises(TypeError, match="clock_trace"):
        SyntheticTraceMeter(  # type: ignore[call-arg]
            program_bytes=program_bytes,
            clock_trace=(SyntheticClockRead("forged", 0),),
        )

    meter = SyntheticTraceMeter(program_bytes=program_bytes)
    with pytest.raises(AttributeError, match="sealed"):
        meter._trace = ()  # type: ignore[misc]
    object.__setattr__(meter, "_trace", ())
    with pytest.raises(ValueError, match="sealed state drifted"):
        meter.read(
            label=program.clock_trace[0].label,
            program_sha256=hashlib.sha256(program_bytes).hexdigest(),
        )

    meter = SyntheticTraceMeter(program_bytes=program_bytes)
    object.__setattr__(meter, "_position", 1)
    with pytest.raises(ValueError, match="sealed state drifted"):
        meter._assert_exhausted()

    meter = SyntheticTraceMeter(program_bytes=program_bytes)
    object.__setattr__(meter, "_program_sha256", "0" * 64)
    with pytest.raises(ValueError, match="sealed state drifted"):
        meter.read(
            label=program.clock_trace[0].label,
            program_sha256=hashlib.sha256(program_bytes).hexdigest(),
        )


def test_raw_provider_validation_derives_tokens_parser_event_and_status() -> None:
    generated_tokens = 0
    while True:
        response = canonical_json_bytes(
            {
                "finish_reason": "stop",
                "generated_tokens": generated_tokens,
                "text": "ok",
                "tool_calls": [],
            },
            indent=None,
        )
        if len(response) == generated_tokens:
            break
        generated_tokens = len(response)
    turn = SubjectTurn("ok", (), len(response), "stop")
    event = canonical_json_bytes(
        {
            "observed_at_ms": 10,
            "record_kind": "synthetic_raw_provider_event_v1",
            "schema_version": "1",
            "transport_kind": "response",
        },
        indent=None,
    )
    observation = RawProviderObservation(
        subject_role="primary_subject",
        call_index=0,
        seed=7,
        model_contract_sha256="a" * 64,
        response_bytes=response,
        typed_turn=turn,
        reported_output_token_ids=tuple(response),
        reported_generated_tokens=len(response),
        provider_event_bytes=event,
        completion_kind=RawProviderCompletionKind.COMPLETED,
    )

    validated = _validate_provider_observation(
        observation=observation,
        expected_role="primary_subject",
        expected_call_index=0,
        expected_seed=7,
        expected_model_sha256="a" * 64,
        deadline_ms=10,
        completion_ms=10,
    )

    assert validated.status is ProviderAttemptStatus.COMPLETED
    assert validated.parser_kind == "turn"
    assert validated.output_token_ids == tuple(response)
    assert validated.typed_turn == turn

    misleading = replace(
        observation,
        completion_kind=RawProviderCompletionKind.REFUSAL,
    )
    with pytest.raises(ValueError, match="completion"):
        _validate_provider_observation(
            observation=misleading,
            expected_role="primary_subject",
            expected_call_index=0,
            expected_seed=7,
            expected_model_sha256="a" * 64,
            deadline_ms=10,
            completion_ms=10,
        )

    late_event = canonical_json_bytes(
        {
            "observed_at_ms": 11,
            "record_kind": "synthetic_raw_provider_event_v1",
            "schema_version": "1",
            "transport_kind": "response",
        },
        indent=None,
    )
    late = _validate_provider_observation(
        observation=replace(
            observation,
            provider_event_bytes=late_event,
            completion_kind=RawProviderCompletionKind.TIMEOUT_LATE_RESPONSE,
        ),
        expected_role="primary_subject",
        expected_call_index=0,
        expected_seed=7,
        expected_model_sha256="a" * 64,
        deadline_ms=10,
        completion_ms=11,
    )
    assert late.status is ProviderAttemptStatus.TIMEOUT_LATE_RESPONSE
    assert late.output_token_ids == tuple(response)
    assert late.typed_turn == turn


def test_discrete_caps_are_inclusive_and_block_only_the_next_action() -> None:
    prefix_caps = PrefixCaps(10, 1, 4, 100)
    contract_caps = CallContractCaps(10, 1, 1, 10, 1)

    assert (
        _pre_dispatch_failure(
            counters=ResourceCounters(0, 0, 0, 0),
            parsed_turns=0,
            prefix_caps=prefix_caps,
            contract_caps=contract_caps,
        )
        is FailureKind.NONE
    )
    assert (
        _pre_dispatch_failure(
            counters=ResourceCounters(10, 0, 0, 10),
            parsed_turns=0,
            prefix_caps=prefix_caps,
            contract_caps=contract_caps,
        )
        is FailureKind.TOKEN_CAP
    )
    assert (
        _pre_dispatch_failure(
            counters=ResourceCounters(0, 1, 0, 0),
            parsed_turns=0,
            prefix_caps=prefix_caps,
            contract_caps=contract_caps,
        )
        is FailureKind.MODEL_CALL_CAP
    )
    assert (
        _pre_dispatch_failure(
            counters=ResourceCounters(0, 0, 0, 0),
            parsed_turns=1,
            prefix_caps=prefix_caps,
            contract_caps=contract_caps,
        )
        is FailureKind.TURN_CAP
    )


def _worker_program_bytes() -> bytes:
    return canonical_json_bytes(
        {
            "clock_trace": [],
            "expected_trigger_reason": "no_intervention_opportunity",
            "failure_injection": {
                "call_index": None,
                "stage": "none",
                "subject_role": None,
                "tool_call_id": None,
            },
            "grade_result": {},
            "provider_transcript": [
                {"subject_role": "primary_subject"},
                {"subject_role": "user_simulator"},
            ],
            "record_kind": "synthetic_prefix_program_v1",
            "schema_version": "1",
            "task_id": "task-0",
            "tool_observations": [
                {
                    "call_id": "call-1",
                    "episode_terminal": False,
                    "failure_kind": "none",
                    "mutation_committed": True,
                    "result_ref": {},
                    "verifier_eligible": True,
                }
            ],
            "tool_schema_ref": {},
            "verifier_result": {},
        },
        indent=None,
    )


def test_worker_persists_role_safe_turn_tool_and_termination_state(
    tmp_path: Path,
) -> None:
    from pneuma_lab.resampling_null.synthetic_environment import (
        _decode_snapshot_state,
        _open_qualified_initial_restore,
    )

    authority = _authority()
    program_bytes = _worker_program_bytes()
    task_bytes = canonical_json_bytes(
        {
            "synthetic_actor_order": [
                "primary_subject",
                "user_simulator",
            ]
        },
        indent=None,
    )
    authority = replace(
        authority,
        task_input_ref=_ref("task_input", task_bytes, "application/json"),
        task_input_bytes=task_bytes,
        program_ref=_ref(
            "synthetic_execution_program",
            program_bytes,
            "application/json",
        ),
        program_bytes=program_bytes,
    )
    result = _open_qualified_initial_restore(
        run_root=tmp_path,
        authority=authority,
    )
    try:
        handle = result._resources[0].handle
        call = ToolCall("call-1", "read", "{}\n")
        handle.append_assistant_turn(SubjectTurn("use tool", (call,), 8, "tool"))
        assert handle.simulator_context() == b"synthetic-simulator-context"
        executed_id, raw_result = handle.execute_tool(call)
        assert executed_id == "call-1"
        assert raw_result == canonical_json_bytes({"call_id": "call-1"}, indent=None)
        assert handle.mutation_committed() is True
        assert handle.verifier_eligible() is True
        handle.append_simulator_turn(SubjectTurn("continue", (), 8, "stop"))
        handle.terminate(FailureKind.TOKEN_CAP, (call,))
        snapshot = _decode_snapshot_state(handle.snapshot())
        assert snapshot.branch_pending_calls == ()
        assert snapshot.terminal_unexecuted_remainder == (call,)
        assert snapshot.episode_terminal is True
        assert snapshot.failure_kind is FailureKind.TOKEN_CAP
        assert snapshot.mutation_committed is True
        assert snapshot.verifier_eligible is True
        assert len(snapshot.turns) == 2
    finally:
        result.close()


def test_worker_actor_order_comes_from_environment_context_not_transcript(
    tmp_path: Path,
) -> None:
    from pneuma_lab.resampling_null.synthetic_environment import (
        _open_qualified_initial_restore,
    )

    program = json.loads(_worker_program_bytes())
    program["provider_transcript"][0]["subject_role"] = "user_simulator"
    program_bytes = canonical_json_bytes(program, indent=None)
    task_bytes = canonical_json_bytes(
        {
            "synthetic_actor_order": [
                "primary_subject",
                "user_simulator",
            ]
        },
        indent=None,
    )
    authority = replace(
        _authority(),
        task_input_ref=_ref("task_input", task_bytes, "application/json"),
        task_input_bytes=task_bytes,
        program_ref=_ref(
            "synthetic_execution_program",
            program_bytes,
            "application/json",
        ),
        program_bytes=program_bytes,
    )
    result = _open_qualified_initial_restore(
        run_root=tmp_path,
        authority=authority,
    )
    try:
        handle = result._resources[0].handle
        assert handle.simulator_context() is None
        handle.append_assistant_turn(SubjectTurn("primary", (), 0, "stop"))
        assert handle.simulator_context() == b"synthetic-simulator-context"
        with pytest.raises(Exception, match="crosses derived role"):
            handle.append_assistant_turn(SubjectTurn("wrong", (), 0, "stop"))
    finally:
        result.close()


def _write_source(
    root: Path,
    *,
    role: str,
    name: str,
    payload: bytes,
    media_type: str,
) -> ArtifactRef:
    path = root / "sources" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return ArtifactRef(
        role=role,
        relative_path=f"sources/{name}",
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type=media_type,
    )


def _loop_authority(root: Path) -> PrefixExecutionAuthority:
    environment_source = (
        Path(__file__).parents[2]
        / "src/pneuma_lab/resampling_null/synthetic_environment.py"
    ).read_bytes()
    loop_source = (
        Path(__file__).parents[2]
        / "src/pneuma_lab/resampling_null/synthetic_prefix_loop.py"
    ).read_bytes()
    environment_source_ref = _write_source(
        root,
        role="source_revision",
        name="synthetic_environment.py",
        payload=environment_source,
        media_type="application/octet-stream",
    )
    loop_source_ref = _write_source(
        root,
        role="source_revision",
        name="synthetic_prefix_loop.py",
        payload=loop_source,
        media_type="application/octet-stream",
    )
    task_input_bytes = canonical_json_bytes(
        {"instruction": "four tools"},
        indent=None,
    )
    task_input_ref = _write_source(
        root,
        role="task_input",
        name="task-input.json",
        payload=task_input_bytes,
        media_type="application/json",
    )
    request_bytes = _render_request(
        subject_role="primary_subject",
        context_bytes=task_input_bytes,
    )
    request_ref = _write_source(
        root,
        role="synthetic_request",
        name="request.json",
        payload=request_bytes,
        media_type="application/json",
    )
    calls = tuple(ToolCall(f"call-{index}", "read", "{}\n") for index in range(1, 5))
    generated_tokens = 0
    while True:
        response_bytes = canonical_json_bytes(
            {
                "finish_reason": "tool",
                "generated_tokens": generated_tokens,
                "text": "run tools",
                "tool_calls": [
                    {
                        "call_id": call.call_id,
                        "canonical_arguments_json": call.canonical_arguments_json,
                        "name": call.name,
                    }
                    for call in calls
                ],
            },
            indent=None,
        )
        if len(response_bytes) == generated_tokens:
            break
        generated_tokens = len(response_bytes)
    response_ref = _write_source(
        root,
        role="synthetic_response",
        name="response.json",
        payload=response_bytes,
        media_type="application/json",
    )
    event_bytes = canonical_json_bytes(
        {
            "observed_at_ms": 3,
            "record_kind": "synthetic_raw_provider_event_v1",
            "schema_version": "1",
            "transport_kind": "response",
        },
        indent=None,
    )
    event_ref = _write_source(
        root,
        role="synthetic_provider_event",
        name="event.json",
        payload=event_bytes,
        media_type="application/json",
    )
    tool_result_refs = [
        _write_source(
            root,
            role="synthetic_tool_result",
            name=f"tool-{call.call_id}.json",
            payload=canonical_json_bytes({"call_id": call.call_id}, indent=None),
            media_type="application/json",
        )
        for call in calls
    ]
    tool_schema_ref = _write_source(
        root,
        role="tool_schema",
        name="tools.json",
        payload=canonical_json_bytes(
            {
                "record_kind": "synthetic_tool_schema_asset_v1",
                "schema_version": "1",
                "tools": [{"name": "read"}],
            },
            indent=None,
        ),
        media_type="application/json",
    )
    grade_ref = _write_source(
        root,
        role="synthetic_grade_result",
        name="grade.json",
        payload=canonical_json_bytes(
            {
                "success": 0,
                "partial_reward": 0.0,
                "infrastructure_failure": False,
            },
            indent=None,
        ),
        media_type="application/json",
    )
    verifier_ref = _write_source(
        root,
        role="synthetic_verifier_result",
        name="verifier.json",
        payload=canonical_json_bytes({"finding_count": 0}, indent=None),
        media_type="application/json",
    )
    model_contract_bytes = b"subject contract\n"
    subject_ref = _write_source(
        root,
        role="subject_contract",
        name="subject.json",
        payload=model_contract_bytes,
        media_type="application/json",
    )
    program = {
        "clock_trace": [
            {"label": "prefix_epoch", "uint64_ms": 1},
            {"label": "before_primary_subject_0", "uint64_ms": 2},
            {"label": "after_primary_subject_0", "uint64_ms": 3},
            *[
                row
                for index in range(1, 5)
                for row in (
                    {"label": f"before_tool_call-{index}", "uint64_ms": 3 + index * 2},
                    {"label": f"after_tool_call-{index}", "uint64_ms": 4 + index * 2},
                )
            ],
        ],
        "expected_trigger_reason": "fourth_tool_call",
        "failure_injection": {
            "call_index": None,
            "stage": "none",
            "subject_role": None,
            "tool_call_id": None,
        },
        "grade_result": {
            "evidence_ref": asdict(grade_ref),
            "infrastructure_failure": False,
            "partial_reward": 0.0,
            "success": 0,
        },
        "provider_transcript": [
            {
                "call_index": 0,
                "completion_kind": "completed",
                "expected_input_token_ids": list(request_bytes),
                "expected_request_ref": asdict(request_ref),
                "expected_request_sha256": request_ref.sha256,
                "model_contract_sha256": subject_ref.sha256,
                "provider_event_ref": asdict(event_ref),
                "reported_generated_tokens": len(response_bytes),
                "reported_output_token_ids": list(response_bytes),
                "response_ref": asdict(response_ref),
                "seed": derive_call_seed(11, "primary_subject", 0),
                "subject_role": "primary_subject",
                "typed_turn": {
                    "finish_reason": "tool",
                    "generated_tokens": len(response_bytes),
                    "text": "run tools",
                    "tool_calls": [
                        {
                            "call_id": call.call_id,
                            "canonical_arguments_json": call.canonical_arguments_json,
                            "name": call.name,
                        }
                        for call in calls
                    ],
                },
            }
        ],
        "record_kind": "synthetic_prefix_program_v1",
        "schema_version": "1",
        "task_id": "task-0",
        "tool_observations": [
            {
                "call_id": call.call_id,
                "episode_terminal": False,
                "failure_kind": "none",
                "mutation_committed": False,
                "result_ref": asdict(result_ref),
                "verifier_eligible": False,
            }
            for call, result_ref in zip(calls, tool_result_refs, strict=True)
        ],
        "tool_schema_ref": asdict(tool_schema_ref),
        "verifier_result": {
            "evidence_ref": asdict(verifier_ref),
            "finding_count": 0,
        },
    }
    program_bytes = canonical_json_bytes(program, indent=None)
    program_ref = _write_source(
        root,
        role="synthetic_execution_program",
        name="program.json",
        payload=program_bytes,
        media_type="application/json",
    )

    def generic(role: str) -> ArtifactRef:
        return _write_source(
            root,
            role=role,
            name=f"{role}.json",
            payload=canonical_json_bytes({"role": role}, indent=None),
            media_type="application/json",
        )

    descriptors = []
    for purpose, fields in REGISTERED_LOOP_DESCRIPTOR_FIELDS.items():
        if purpose == "simulator":
            continue
        source_ref = (
            environment_source_ref
            if purpose in ("environment", "tokenizer")
            else loop_source_ref
        )
        descriptors.append(
            ImplementationDescriptor(
                **fields,
                implementation_source_ref=source_ref,
            )
        )
    slots = tuple(
        BranchSlot(f"slot-{index}", 20 + index, index, 0) for index in range(4)
    )
    return PrefixExecutionAuthority(
        schedule_ref=ArtifactRef(
            "resampling_prefix_schedule",
            "prefix-schedule.json",
            "a" * 64,
            1,
            "application/json",
        ),
        manifest_ref=ArtifactRef(
            "study_manifest",
            "study-manifest.json",
            "b" * 64,
            1,
            "application/json",
        ),
        provider_lane_plan_ref=generic("provider_lane_plan"),
        schedule_authority="synthetic_validation",
        tokenizer_ref=generic("tokenizer"),
        source_revision_refs=(environment_source_ref, loop_source_ref),
        program_ref=program_ref,
        implementation_descriptors=tuple(descriptors),
        task_schedule=TaskSchedule(
            TaskSpec(
                "task-0",
                "swe",
                "python",
                "repo-0",
                (
                    GroupLabel(GroupKind.LANGUAGE, "python"),
                    GroupLabel(GroupKind.DOMAIN, "software"),
                    GroupLabel(GroupKind.ISSUE_FAMILY, "bug"),
                ),
            ),
            11,
            BranchSlotSet(slots),  # type: ignore[arg-type]
            "lane-0",
        ),
        prefix_caps=PrefixCaps(10_000, 1, 4, 1_000),
        branch_caps=BranchCaps(100, 2, 4, 500, True),
        simulator_caps=CallContractCaps(0, 0, 0, 0, 0),
        subject_contract_caps=CallContractCaps(10_000, 1, 1, 10_000, 1),
        simulator_contract_caps=None,
        actor_roles=("primary_subject",),
        task_input_ref=task_input_ref,
        environment_contract_ref=generic("environment_contract"),
        grader_contract_ref=generic("grader_contract"),
        verifier_contract_ref=generic("verifier_contract"),
        isolation_contract_ref=generic("isolation_contract"),
        subject_contract_ref=subject_ref,
        simulator_contract_ref=None,
        tool_parser_contract_ref=generic("tool_parser_contract"),
        meter_contract_ref=generic("meter_contract"),
    )


def test_private_loop_reaches_fourth_tool_and_closes_every_zero_cost_attempt(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)

    result = _open_prefix_loop(run_root=tmp_path, authority=authority)
    try:
        assert result.trigger_reason is TriggerReason.FOURTH_TOOL_CALL
        assert result.failure_kind is FailureKind.NONE
        assert result.primary_counters.tool_calls == 4
        assert result.primary_counters.model_calls == 1
        assert len(result.attempts) == 1
        assert len(result.settlements) == 1
        assert result.cost_closure.total_cost_microunits == 0
        assert result.branch_pending_calls == ()
        assert result.terminal_unexecuted_remainder == ()
        assert result.final_observation.episode_terminal is False
    finally:
        result.close()


def test_token_cap_equality_allows_queued_tools_and_fourth_tool_trigger(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)
    program = json.loads((tmp_path / authority.program_ref.relative_path).read_bytes())
    generated = program["provider_transcript"][0]["reported_generated_tokens"]
    assert isinstance(generated, int)
    authority = replace(
        authority,
        prefix_caps=replace(
            authority.prefix_caps,
            generated_tokens=generated,
        ),
        subject_contract_caps=replace(
            authority.subject_contract_caps,
            aggregate_generated_tokens=generated,
            per_call_generated_tokens=generated,
        ),
    )

    result = _open_prefix_loop(run_root=tmp_path, authority=authority)
    try:
        assert result.primary_counters.generated_tokens == generated
        assert result.primary_counters.tool_calls == 4
        assert result.trigger_reason is TriggerReason.FOURTH_TOOL_CALL
        assert result.failure_kind is FailureKind.NONE
    finally:
        result.close()


def _rewrite_program(
    root: Path,
    authority: PrefixExecutionAuthority,
    mutate: object,
) -> PrefixExecutionAuthority:
    path = root / authority.program_ref.relative_path
    value = json.loads(path.read_bytes())
    assert isinstance(value, dict)
    mutate(value)  # type: ignore[operator]
    payload = canonical_json_bytes(value, indent=None)
    path.write_bytes(payload)
    return replace(
        authority,
        program_ref=ArtifactRef(
            "synthetic_execution_program",
            authority.program_ref.relative_path,
            hashlib.sha256(payload).hexdigest(),
            len(payload),
            "application/json",
        ),
    )


def test_loop_rejects_unconsumed_ordinary_provider_row(tmp_path: Path) -> None:
    authority = _loop_authority(tmp_path)

    def mutate(value: dict[str, object]) -> None:
        transcript = value["provider_transcript"]
        assert isinstance(transcript, list)
        assert isinstance(transcript[0], dict)
        extra = dict(transcript[0])
        extra["call_index"] = 1
        extra["seed"] = derive_call_seed(11, "primary_subject", 1)
        transcript.append(extra)

    authority = _rewrite_program(tmp_path, authority, mutate)
    result = None
    try:
        with pytest.raises(BaseExceptionGroup, match="prefix loop failed") as raised:
            result = _open_prefix_loop(run_root=tmp_path, authority=authority)
        assert "unconsumed provider transcript" in repr(raised.value.exceptions)
    finally:
        if result is not None:
            result.close()


def test_loop_rejects_unconsumed_declared_provider_failure_target(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)

    def mutate(value: dict[str, object]) -> None:
        transcript = value["provider_transcript"]
        assert isinstance(transcript, list)
        assert isinstance(transcript[0], dict)
        extra = dict(transcript[0])
        extra["call_index"] = 1
        extra["completion_kind"] = "provider_error"
        extra["seed"] = derive_call_seed(11, "primary_subject", 1)
        transcript.append(extra)
        value["failure_injection"] = {
            "call_index": 1,
            "stage": "provider_transport",
            "subject_role": "primary_subject",
            "tool_call_id": None,
        }

    authority = _rewrite_program(tmp_path, authority, mutate)
    result = None
    try:
        with pytest.raises(BaseExceptionGroup, match="prefix loop failed") as raised:
            result = _open_prefix_loop(run_root=tmp_path, authority=authority)
        assert "unconsumed provider transcript" in repr(raised.value.exceptions)
    finally:
        if result is not None:
            result.close()


def test_private_loop_has_no_fixture_codec_store_or_script_seam() -> None:
    assert tuple(inspect.signature(_open_prefix_loop).parameters) == (
        "run_root",
        "authority",
    )


def test_provider_actor_has_exact_closed_invoke_surface() -> None:
    assert tuple(inspect.signature(SyntheticProviderActor.invoke).parameters) == (
        "self",
        "request_bytes",
        "dispatch_intent_sha256",
        "subject_role",
        "call_index",
        "seed",
        "model_contract_sha256",
        "remaining_caps",
        "absolute_deadline_ms",
    )


def test_provider_actor_rejects_derived_row_and_cursor_drift_before_observation(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)
    program_bytes = (tmp_path / authority.program_ref.relative_path).read_bytes()
    program = load_synthetic_prefix_program(program_bytes)
    row = next(
        item
        for item in program.provider_transcript
        if item.subject_role == "primary_subject"
    )
    refs = (
        row.expected_request_ref,
        row.provider_event_ref,
        *(() if row.response_ref is None else (row.response_ref,)),
    )
    payloads = {ref: (tmp_path / ref.relative_path).read_bytes() for ref in refs}
    actor = SyntheticProviderActor(
        subject_role="primary_subject",
        program_bytes=program_bytes,
        payloads=payloads,
    )
    assert row.typed_turn is not None
    object.__setattr__(
        actor,
        "_role_rows",
        (replace(row, typed_turn=replace(row.typed_turn, text="drifted")),),
    )

    with pytest.raises(ValueError, match="sealed state drifted"):
        actor.invoke(
            request_bytes=payloads[row.expected_request_ref],
            dispatch_intent_sha256="d" * 64,
            subject_role="primary_subject",
            call_index=row.call_index,
            seed=row.seed,
            model_contract_sha256=row.model_contract_sha256,
            remaining_caps=authority.subject_contract_caps,
            absolute_deadline_ms=authority.prefix_caps.wall_clock_ms,
        )

    actor = SyntheticProviderActor(
        subject_role="primary_subject",
        program_bytes=program_bytes,
        payloads=payloads,
    )
    object.__setattr__(actor, "_cursor", 1)
    with pytest.raises(ValueError, match="sealed state drifted"):
        actor.invoke(
            request_bytes=payloads[row.expected_request_ref],
            dispatch_intent_sha256="d" * 64,
            subject_role="primary_subject",
            call_index=row.call_index,
            seed=row.seed,
            model_contract_sha256=row.model_contract_sha256,
            remaining_caps=authority.subject_contract_caps,
            absolute_deadline_ms=authority.prefix_caps.wall_clock_ms,
        )


def test_provider_actor_role_interleaving_cannot_hide_unconsumed_cursor(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)

    def mutate(value: dict[str, object]) -> None:
        transcript = value["provider_transcript"]
        assert isinstance(transcript, list)
        assert isinstance(transcript[0], dict)
        first = transcript[0]
        first_turn = first["typed_turn"]
        assert isinstance(first_turn, dict)
        simulator = {
            **first,
            "call_index": 0,
            "seed": derive_call_seed(11, "user_simulator", 0),
            "subject_role": "user_simulator",
            "typed_turn": {
                **first_turn,
                "finish_reason": "stop",
                "text": "continue",
                "tool_calls": [],
            },
        }
        second_primary = {
            **first,
            "call_index": 1,
            "seed": derive_call_seed(11, "primary_subject", 1),
        }
        value["provider_transcript"] = [
            first,
            simulator,
            second_primary,
        ]

    authority = _rewrite_program(tmp_path, authority, mutate)
    program_bytes = (tmp_path / authority.program_ref.relative_path).read_bytes()
    program = load_synthetic_prefix_program(program_bytes)
    primary_rows = tuple(
        row
        for row in program.provider_transcript
        if row.subject_role == "primary_subject"
    )
    row = primary_rows[0]
    refs = {
        ref
        for item in primary_rows
        for ref in (
            item.expected_request_ref,
            item.provider_event_ref,
            *(() if item.response_ref is None else (item.response_ref,)),
        )
    }
    payloads = {ref: (tmp_path / ref.relative_path).read_bytes() for ref in refs}
    actor = SyntheticProviderActor(
        subject_role="primary_subject",
        program_bytes=program_bytes,
        payloads=payloads,
    )
    actor.invoke(
        request_bytes=payloads[row.expected_request_ref],
        dispatch_intent_sha256="d" * 64,
        subject_role="primary_subject",
        call_index=row.call_index,
        seed=row.seed,
        model_contract_sha256=row.model_contract_sha256,
        remaining_caps=authority.subject_contract_caps,
        absolute_deadline_ms=authority.prefix_caps.wall_clock_ms,
    )

    with pytest.raises(ValueError, match="unconsumed"):
        actor._assert_exhausted()


def test_loop_rejects_descriptor_registry_drift_before_execution(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)
    subject = next(
        item
        for item in authority.implementation_descriptors
        if item.purpose == "subject"
    )
    drifted = replace(subject, build_id="unreviewed")
    authority = replace(
        authority,
        implementation_descriptors=tuple(
            drifted if item is subject else item
            for item in authority.implementation_descriptors
        ),
    )

    with pytest.raises(ValueError, match="descriptor"):
        _open_prefix_loop(run_root=tmp_path, authority=authority)

    assert not (tmp_path / "prefix-environments").exists()


def test_descriptor_registry_is_deeply_immutable_and_rejects_duplicates(
    tmp_path: Path,
) -> None:
    fields = REGISTERED_LOOP_DESCRIPTOR_FIELDS["subject"]
    with pytest.raises(TypeError):
        fields["build_id"] = "unreviewed"  # type: ignore[index]
    assert fields["build_id"] == "synthetic-subject-v1"

    authority = _loop_authority(tmp_path)
    subject = next(
        item
        for item in authority.implementation_descriptors
        if item.purpose == "subject"
    )
    duplicated = replace(
        authority,
        implementation_descriptors=(
            *authority.implementation_descriptors,
            subject,
        ),
    )
    with pytest.raises(ValueError, match="duplicate"):
        _validate_descriptor_registry(duplicated)


def test_loop_requires_every_copied_descriptor_source_before_fixture_use(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)
    (tmp_path / "sources" / "synthetic_prefix_loop.py").unlink()

    with pytest.raises(BaseExceptionGroup, match="prefix loop") as raised:
        _open_prefix_loop(run_root=tmp_path, authority=authority)

    assert "source" in repr(raised.value.exceptions).lower()
    assert not (tmp_path / "prefix-environments").exists()


def test_loop_rejects_request_token_drift_before_dispatch(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)

    def mutate(value: dict[str, object]) -> None:
        transcript = value["provider_transcript"]
        assert isinstance(transcript, list)
        assert isinstance(transcript[0], dict)
        transcript[0]["expected_input_token_ids"] = [999]

    authority = _rewrite_program(tmp_path, authority, mutate)
    with pytest.raises(BaseExceptionGroup, match="prefix loop failed"):
        _open_prefix_loop(run_root=tmp_path, authority=authority)


def test_token_overshoot_preserves_the_exact_known_tool_queue(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)
    generated = json.loads(
        (tmp_path / authority.program_ref.relative_path).read_bytes()
    )["provider_transcript"][0]["reported_generated_tokens"]
    assert isinstance(generated, int)

    def mutate(value: dict[str, object]) -> None:
        value["expected_trigger_reason"] = "no_intervention_opportunity"
        clock = value["clock_trace"]
        assert isinstance(clock, list)
        value["clock_trace"] = clock[:3]
        value["tool_observations"] = []

    authority = _rewrite_program(tmp_path, authority, mutate)
    authority = replace(
        authority,
        prefix_caps=replace(
            authority.prefix_caps,
            generated_tokens=generated - 1,
        ),
    )

    result = _open_prefix_loop(run_root=tmp_path, authority=authority)
    try:
        assert result.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY
        assert result.failure_kind is FailureKind.TOKEN_CAP
        assert tuple(call.call_id for call in result.terminal_unexecuted_remainder) == (
            "call-1",
            "call-2",
            "call-3",
            "call-4",
        )
        assert result.final_observation.branch_pending_calls == ()
        assert (
            result.final_observation.terminal_unexecuted_remainder
            == result.terminal_unexecuted_remainder
        )
    finally:
        result.close()


def test_tool_observations_are_consumed_in_exact_program_order(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)

    def mutate(value: dict[str, object]) -> None:
        observations = value["tool_observations"]
        assert isinstance(observations, list)
        value["tool_observations"] = list(reversed(observations))

    authority = _rewrite_program(tmp_path, authority, mutate)
    with pytest.raises(BaseExceptionGroup, match="prefix loop failed"):
        _open_prefix_loop(run_root=tmp_path, authority=authority)


def test_deadline_precedes_discrete_cap_at_next_action_boundary() -> None:
    prefix_caps = PrefixCaps(100, 1, 4, 10)
    contract_caps = CallContractCaps(100, 1, 1, 100, 1)
    counters = ResourceCounters(10, 1, 0, 10)

    assert (
        _pre_provider_action_failure(
            now_ms=11,
            deadline_ms=11,
            counters=counters,
            parsed_turns=1,
            prefix_caps=prefix_caps,
            contract_caps=contract_caps,
        )
        is FailureKind.TIMEOUT
    )
    assert (
        _pre_provider_action_failure(
            now_ms=10,
            deadline_ms=11,
            counters=counters,
            parsed_turns=1,
            prefix_caps=prefix_caps,
            contract_caps=contract_caps,
        )
        is FailureKind.MODEL_CALL_CAP
    )
