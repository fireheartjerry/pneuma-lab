"""Milestone claims: deterministic controller seeds and closed call boundaries."""

from __future__ import annotations

import pytest

from pneuma_lab.resampling_null.controller import derive_call_seed
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    BranchCaps,
    CallSeedReceipt,
    OpaqueSlotIdentity,
    OpaqueSlotWorkOrder,
    PrefixCaps,
    ToolCall,
)


pytestmark = pytest.mark.milestone


def test_call_seed_vectors_are_role_and_index_separated() -> None:
    assert (
        derive_call_seed(42, "primary_subject", 0),
        derive_call_seed(42, "primary_subject", 1),
        derive_call_seed(42, "user_simulator", 0),
    ) == (5596737105796749176, 5168650295223317663, 12950473227392358843)


def test_controller_public_inputs_reject_unregistered_or_open_values() -> None:
    with pytest.raises(ValueError, match="registered"):
        derive_call_seed(0, "assistant", 0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="canonical"):
        ToolCall("call-1", "read", '{ "path": "x" }')


def test_controller_records_are_closed_and_frozen() -> None:
    receipt = CallSeedReceipt("primary_subject", 0, 7)
    assert PrefixCaps(0, 0, 0, 0).generated_tokens == 0
    with pytest.raises(Exception):
        receipt.seed = 0  # type: ignore[misc]


def test_opaque_branch_work_order_is_capability_only_and_immutable() -> None:
    ref = ArtifactRef("composite_snapshot", "controller/snapshot.json", "a" * 64, 1, "application/json")
    order = OpaqueSlotWorkOrder(
        study_id="study", task_id="task", benchmark="SWE",
        slot=OpaqueSlotIdentity("slot-0", "b" * 64, 7, 0, 0),
        snapshot_ref=ref, private_guidance_ref=None,
        prefix_visible_sha256="c" * 64, packet_index_sha256="d" * 64,
        analysis_freeze_sha256="e" * 64,
        branch_caps=BranchCaps(1, 1, 1, 1, True),
    )
    assert order.slot.opaque_capability_id == "b" * 64
    with pytest.raises(Exception):
        order.task_id = "replacement"  # type: ignore[misc]
    with pytest.raises(ValueError, match="opaque"):
        OpaqueSlotWorkOrder(
            study_id="study", task_id="task", benchmark="SWE",
            slot=OpaqueSlotIdentity("slot-0", "b" * 64, 7, 0, 0),
            snapshot_ref=ref,
            private_guidance_ref=ArtifactRef(
                "private_guidance", "packet-work/private-real.txt", "f" * 64,
                1, "text/plain",
            ),
            prefix_visible_sha256="c" * 64, packet_index_sha256="d" * 64,
            analysis_freeze_sha256="e" * 64,
            branch_caps=BranchCaps(1, 1, 1, 1, True),
        )
