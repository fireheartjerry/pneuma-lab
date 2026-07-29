"""Tiny controller-contract tripwire; execution evidence stays mechanism-led."""

from dataclasses import FrozenInstanceError

import pytest

from pneuma_lab.resampling_null.controller import derive_call_seed
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    BranchCaps,
    CallSeedReceipt,
    ContextMessage,
    FailureKind,
    GradeReceipt,
    OpaqueSlotIdentity,
    PrefixCaps,
    SubjectContext,
    SubjectTurn,
    ToolBoundary,
    ToolCall,
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
