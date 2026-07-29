"""Tiny controller-contract tripwire; execution evidence stays mechanism-led."""

from dataclasses import dataclass, FrozenInstanceError
from enum import Enum
import inspect
from pathlib import Path

import pytest

from pneuma_lab.resampling_null import (
    ArtifactRef,
    BranchCaps,
    CallSeedReceipt,
    ContextMessage,
    FailureKind,
    GradeReceipt,
    OpaqueSlotIdentity,
    PrefixCaps,
    PrefixExecutionAuthority,
    CallContractCaps,
    SubjectContext,
    SubjectTurn,
    TaskSchedule,
    ToolBoundary,
    ToolCall,
    derive_call_seed,
    load_prefix_execution_authority,
)
from pneuma_lab.resampling_null.artifacts import (
    RecordValidationError,
)
from tests.resampling_null.provider_authority_fixture import (
    ProviderAuthorityFixture,
)




def test_t5_s02a_loads_frozen_schedule_ancestry_authority(tmp_path: Path) -> None:
    schedule_ref, refs = ProviderAuthorityFixture.build(tmp_path / "run")
    authority = load_prefix_execution_authority(
        run_root=tmp_path / "run",
        schedule_ref=schedule_ref,
        task_id="task-1",
    )

    assert type(authority) is PrefixExecutionAuthority
    assert type(authority.task_schedule) is TaskSchedule
    assert authority.task_schedule.prefix_seed == 11
    assert authority.task_schedule.provider_lane == "lane-0"
    assert authority.prefix_caps == PrefixCaps(40, 4, 4, 1_000)
    assert authority.branch_caps == BranchCaps(20, 2, 4, 500, True)
    assert authority.simulator_caps == CallContractCaps(40, 4, 4, 12, 1)
    assert authority.subject_contract_caps == CallContractCaps(40, 4, 4, 12, 1)
    assert authority.simulator_contract_caps == CallContractCaps(40, 4, 4, 12, 1)
    assert authority.task_input_ref == refs["task-1_input"]
    assert authority.environment_contract_ref == refs["task-1_environment"]
    assert authority.grader_contract_ref == refs["task-1_grader"]
    assert authority.verifier_contract_ref == refs["task-1_verifier"]
    assert authority.isolation_contract_ref == refs["task-1_isolation"]
    assert authority.subject_contract_ref == refs["subject"]
    assert authority.simulator_contract_ref == refs["simulator"]
    assert authority.tool_parser_contract_ref == refs["parser"]
    assert authority.meter_contract_ref == refs["meter"]
    with pytest.raises(FrozenInstanceError):
        authority.prefix_caps = PrefixCaps(0, 0, 0, 0)  # type: ignore[misc]

    parameters = inspect.signature(load_prefix_execution_authority).parameters
    assert tuple(parameters) == ("run_root", "schedule_ref", "task_id")
    for forbidden in ("task", "caps", "factory", "task_input_ref"):
        assert forbidden not in parameters
    with pytest.raises(RecordValidationError, match="selected"):
        load_prefix_execution_authority(
            run_root=tmp_path / "run",
            schedule_ref=schedule_ref,
            task_id="task-foreign",
        )


@pytest.mark.parametrize(
    ("fixture_kwargs", "message"),
    [
        ({"plan_kind": "provider_lane_plan_v1"}, "identity"),
        ({"subject_extra": True}, "shape"),
        ({"environment_benchmark": "tau"}, "benchmark"),
    ],
)
def test_t5_s02a_rejects_v1_open_and_mismatched_authority(
    tmp_path: Path,
    fixture_kwargs: dict[str, object],
    message: str,
) -> None:
    schedule_ref, _refs = ProviderAuthorityFixture.build(
        tmp_path / "run",
        **fixture_kwargs,  # type: ignore[arg-type]
    )
    with pytest.raises(RecordValidationError, match=message):
        load_prefix_execution_authority(
            run_root=tmp_path / "run",
            schedule_ref=schedule_ref,
            task_id="task-1",
        )


def test_t5_s02a_rejects_tampered_plan_or_nested_contract(tmp_path: Path) -> None:
    for target in ("plan", "subject"):
        root = tmp_path / target
        schedule_ref, refs = ProviderAuthorityFixture.build(root)
        path = root / refs[target].relative_path
        path.write_bytes(path.read_bytes() + b" ")
        with pytest.raises(RecordValidationError, match="bytes mismatch"):
            load_prefix_execution_authority(
                run_root=root,
                schedule_ref=schedule_ref,
                task_id="task-1",
            )


@pytest.mark.parametrize("damage", ["tamper", "dangle"])
def test_t5_s02a_rejects_deep_authority_ref_damage(
    tmp_path: Path,
    damage: str,
) -> None:
    root = tmp_path / damage
    schedule_ref, refs = ProviderAuthorityFixture.build(root)
    leaf = root / refs["deep_leaf"].relative_path
    if damage == "tamper":
        leaf.write_bytes(leaf.read_bytes() + b" ")
    else:
        leaf.unlink()
    with pytest.raises(RecordValidationError, match="(?i)(bytes|dangling)"):
        load_prefix_execution_authority(
            run_root=root,
            schedule_ref=schedule_ref,
            task_id="task-1",
        )


@pytest.mark.parametrize(
    ("fixture_kwargs", "message"),
    [
        ({"scheduled_lane": "lane-foreign"}, "lane mismatch"),
        ({"requires_simulator": False}, "unnecessary simulator"),
        (
            {
                "requires_simulator": False,
                "foreign_requires_simulator": True,
            },
            "mixed simulator capability",
        ),
        (
            {"simulator_present": False},
            "required simulator",
        ),
        (
            {"subject_aggregate_generated_tokens": 39},
            "subject contract caps",
        ),
        (
            {"subject_aggregate_generated_tokens": 41},
            "subject contract caps",
        ),
        (
            {"subject_aggregate_model_calls": 5},
            "subject contract caps",
        ),
        (
            {"lane_simulator_aggregate_generated_tokens": 39},
            "simulator caps",
        ),
        (
            {"parser_response_grammar": "drift-response-v1"},
            "response grammar",
        ),
        (
            {"parser_tool_schema_drift": True},
            "tool schema",
        ),
        (
            {"meter_zero_cost": False},
            "zero-cost synthetic",
        ),
    ],
)
def test_t5_s02a_rejects_lane_contract_coherence_drift(
    tmp_path: Path,
    fixture_kwargs: dict[str, object],
    message: str,
) -> None:
    schedule_ref, _refs = ProviderAuthorityFixture.build(
        tmp_path / "run",
        **fixture_kwargs,  # type: ignore[arg-type]
    )
    with pytest.raises(RecordValidationError, match=message):
        load_prefix_execution_authority(
            run_root=tmp_path / "run",
            schedule_ref=schedule_ref,
            task_id="task-1",
        )


def test_t5_s02a_accepts_no_simulator_only_with_zero_caps(tmp_path: Path) -> None:
    schedule_ref, _refs = ProviderAuthorityFixture.build(
        tmp_path / "run",
        requires_simulator=False,
        simulator_present=False,
    )
    authority = load_prefix_execution_authority(
        run_root=tmp_path / "run",
        schedule_ref=schedule_ref,
        task_id="task-1",
    )
    assert authority.simulator_contract_ref is None
    assert authority.simulator_contract_caps is None
    assert authority.simulator_caps == CallContractCaps(0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    "relative_path",
    [
        "prefix-schedule.json",
        "study-manifest.json",
        "sources/provider-plan.json",
        "sources/tasks.json",
        "sources/tokenizer.json",
        "sources/revision.json",
        "sources/task-1-input.json",
        "sources/subject.json",
        "sources/simulator.json",
        "sources/parser.json",
        "sources/meter.json",
        "sources/task-1-environment.json",
        "sources/task-1-grader.json",
        "sources/task-1-verifier.json",
        "sources/task-1-isolation.json",
        "sources/prompt.json",
        "sources/tools.json",
        "sources/clock.txt",
        "sources/watchdog.txt",
        "sources/qualification.json",
    ],
)
def test_t5_s02a_rejects_cross_role_aliasing(
    tmp_path: Path,
    relative_path: str,
) -> None:
    schedule_ref, _refs = ProviderAuthorityFixture.build(
        tmp_path / "run",
        role_overrides={relative_path: "cross_role_alias"},
    )
    with pytest.raises(RecordValidationError, match="role"):
        load_prefix_execution_authority(
            run_root=tmp_path / "run",
            schedule_ref=schedule_ref,
            task_id="task-1",
        )


def test_t5_s01_call_seed_and_frozen_boundary_contract() -> None:
    assert (
        derive_call_seed(42, "primary_subject", 0),
        derive_call_seed(42, "primary_subject", 1),
        derive_call_seed(42, "user_simulator", 0),
        derive_call_seed(42, "user_simulator", 1),
    ) == (
        5596737105796749176,
        5168650295223317663,
        12950473227392358843,
        174950558451330531,
    )
    receipt = CallSeedReceipt("primary_subject", 0, 5596737105796749176)
    with pytest.raises(FrozenInstanceError):
        receipt.seed = 0  # type: ignore[misc]
    with pytest.raises(ValueError, match="smaller than"):
        CallSeedReceipt("primary_subject", 2**64, 0)
    for invalid_integer in (True, -1, 2**64):
        with pytest.raises((TypeError, ValueError)):
            derive_call_seed(invalid_integer, "primary_subject", 0)
        with pytest.raises((TypeError, ValueError)):
            derive_call_seed(0, "primary_subject", invalid_integer)
    with pytest.raises(ValueError, match="registered"):
        derive_call_seed(0, "assistant", 0)  # type: ignore[arg-type]

    PrefixCaps(0, 0, 0, 0)
    with pytest.raises(TypeError, match="exact int"):
        PrefixCaps(True, 0, 0, 0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="pending prefix"):
        BranchCaps(1, 1, 1, 1, False)  # type: ignore[arg-type]

    assert {kind.name for kind in FailureKind} == {
        "NONE",
        "MODEL",
        "MALFORMED_ACTION",
        "TOKEN_CAP",
        "TOOL_CAP",
        "TIMEOUT",
        "INFRASTRUCTURE",
    }
    for mutated, verifier_eligible, failure_kind in (
        (True, False, FailureKind.INFRASTRUCTURE),
        (False, True, FailureKind.INFRASTRUCTURE),
        (False, False, FailureKind.NONE),
    ):
        with pytest.raises(ValueError, match="incomplete boundary"):
            ToolBoundary(
                1,
                False,
                mutated,
                verifier_eligible,
                failure_kind,
            )

    context = SubjectContext((ContextMessage("user", "visible"),), None)
    assert context.private_guidance is None
    with pytest.raises(TypeError, match="tuple"):
        SubjectContext([ContextMessage("user", "visible")], None)  # type: ignore[arg-type]
    assert ToolCall("call-1", "read", '{"path":"x"}\n').name == "read"
    for arguments in (
        '{ "path": "x" }',
        '{"duplicate":1,"duplicate":2}\n',
        '{"constant":NaN}\n',
        "[]\n",
        '{"path":"x"}',
    ):
        with pytest.raises(ValueError):
            ToolCall("call-2", "read", arguments)

    turn = SubjectTurn("", (ToolCall("call-3", "read", "{}\n"),), 0, None)
    assert turn.finish_reason is None
    with pytest.raises(TypeError, match="tuple"):
        SubjectTurn("", [], 0, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty"):
        SubjectTurn("", (), 0, "")

    artifact_ref = ArtifactRef(
        "grade",
        "grades/task.json",
        "0" * 64,
        1,
        "application/json",
    )
    assert GradeReceipt(1, 0.5, False, artifact_ref).partial_reward == 0.5
    with pytest.raises(ValueError, match="requires success"):
        GradeReceipt(1, 0.0, True, artifact_ref)
    for partial_reward in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            GradeReceipt(0, partial_reward, False, artifact_ref)

    identity = OpaqueSlotIdentity("slot-1", "a" * 64, 2**64 - 1, 0, 0)
    assert identity.seed == 2**64 - 1
    with pytest.raises(ValueError, match="lowercase hexadecimal"):
        OpaqueSlotIdentity("slot-1", "A" * 64, 0, 0, 0)


def test_t5_s01_review_rejects_foreign_role_values_at_public_boundary() -> None:
    class ForeignRole(str, Enum):
        PRIMARY_SUBJECT = "primary_subject"

    class EqualityOverloadedRole:
        def __eq__(self, other: object) -> bool:
            return other == "primary_subject"

    for foreign_role in (ForeignRole.PRIMARY_SUBJECT, EqualityOverloadedRole()):
        with pytest.raises(TypeError, match="subject_role must be exact str"):
            derive_call_seed(0, foreign_role, 0)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="subject_role must be exact str"):
            CallSeedReceipt(foreign_role, 0, 0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="registered"):
        CallSeedReceipt("assistant", 0, 0)  # type: ignore[arg-type]


def test_t5_s01_review_requires_exact_tuple_and_record_types() -> None:
    class ForeignTuple(tuple[object, ...]):
        pass

    @dataclass(frozen=True, slots=True)
    class ExtendedContextMessage(ContextMessage):
        hidden_state: str

    @dataclass(frozen=True, slots=True)
    class ExtendedToolCall(ToolCall):
        hidden_state: str

    with pytest.raises(TypeError, match="exact tuple"):
        SubjectContext(ForeignTuple((ContextMessage("user", "visible"),)), None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact ContextMessage"):
        SubjectContext(
            (ExtendedContextMessage("user", "visible", "hidden"),),
            None,
        )
    with pytest.raises(TypeError, match="exact tuple"):
        SubjectTurn("", ForeignTuple(()), 0, None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact ToolCall"):
        SubjectTurn(
            "",
            (ExtendedToolCall("call-4", "read", "{}\n", "hidden"),),
            0,
            None,
        )


def test_t5_s01_review_preserves_scalar_error_taxonomy() -> None:
    for field, invocation in (
        ("slot_seed", lambda: derive_call_seed(True, "primary_subject", 0)),
        ("call_index", lambda: derive_call_seed(0, "primary_subject", True)),
    ):
        with pytest.raises(TypeError, match=field):
            invocation()
    for invocation in (
        lambda: derive_call_seed(-1, "primary_subject", 0),
        lambda: derive_call_seed(0, "primary_subject", 2**64),
    ):
        with pytest.raises(ValueError):
            invocation()
    with pytest.raises(TypeError, match="pending_prefix"):
        BranchCaps(0, 0, 0, 0, 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="success"):
        GradeReceipt(
            True,  # type: ignore[arg-type]
            0.0,
            False,
            ArtifactRef(
                "grade",
                "grades/task.json",
                "0" * 64,
                1,
                "application/json",
            ),
        )
