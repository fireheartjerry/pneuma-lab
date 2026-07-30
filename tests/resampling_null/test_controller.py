"""Milestone claims: deterministic controller seeds and closed call boundaries."""

from __future__ import annotations

import pytest

from pneuma_lab.resampling_null.controller import derive_call_seed
from pneuma_lab.resampling_null.types import CallSeedReceipt, PrefixCaps, ToolCall


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
