"""Frame validation helper tests (Layer A)."""

from __future__ import annotations

from copy import deepcopy

import pytest

from pneuma_lab.schemas import validate as v


def _good_world_frame() -> dict:
    return {
        "schema_version": "0.1.0",
        "frame_kind": "world",
        "timestamp": "2026-07-06T00:00:00Z",
        "run_id": "run-1",
        "phase": "execution",
    }


def test_good_frame_is_valid() -> None:
    assert v.is_valid(_good_world_frame())
    assert v.iter_errors(_good_world_frame()) == []
    assert v.validate_or_raise(_good_world_frame())["frame_kind"] == "world"


def test_missing_required_field_raises() -> None:
    bad = _good_world_frame()
    del bad["phase"]
    assert not v.is_valid(bad)
    with pytest.raises(v.FrameValidationError):
        v.validate_or_raise(bad)


def test_bad_enum_is_rejected() -> None:
    bad = _good_world_frame()
    bad["phase"] = "not-a-phase"
    assert not v.is_valid(bad)


def test_unknown_frame_kind_raises() -> None:
    with pytest.raises(v.FrameValidationError):
        v.validate_or_raise({"frame_kind": "nonsense"})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_numbers_are_not_valid_json_frames(value) -> None:
    frame = deepcopy(_good_world_frame())
    frame["stakes"] = {"risk": value}

    errors = v.iter_errors(frame)

    assert any("non-finite number" in error for error in errors)
    with pytest.raises(v.FrameValidationError, match="non-finite number"):
        v.validate_or_raise(frame)


def test_all_output_kinds_have_a_schema() -> None:
    from pneuma_lab import OUTPUT_FRAMES

    for kind in OUTPUT_FRAMES:
        assert kind in v.FRAME_KIND_TO_SCHEMA
