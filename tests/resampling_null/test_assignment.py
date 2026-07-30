"""Milestone claims: canonical assignment frames, seeds, and bounded draws."""

from __future__ import annotations

import hashlib

import pytest

from pneuma_lab.resampling_null.assignment import (
    BytesField,
    TextField,
    U64Field,
    UniformDraw,
    derive_seed,
    kdf_frame,
    uniform_below,
)


pytestmark = pytest.mark.milestone


def test_seed_frame_and_normative_vector_are_exact() -> None:
    frame = kdf_frame(
        "derive-seed-v1",
        (U64Field(7), TextField("task-1"), TextField("prefix")),
    )

    assert hashlib.sha256(frame).hexdigest() == (
        "d0f92ef02cc64124ae8d651ad65c1f799f94fac4bd9923804cefbec2928cb327"
    )
    assert derive_seed(7, "task-1", "prefix") == 15058118438168183076


def test_framing_is_type_and_boundary_separated() -> None:
    assert kdf_frame("frame-v1", (TextField("a"), TextField("bc"))) != kdf_frame(
        "frame-v1", (TextField("ab"), TextField("c"))
    )
    assert kdf_frame("frame-v1", (TextField("7"),)) != kdf_frame(
        "frame-v1", (U64Field(7),)
    )


def test_uniform_draw_is_bounded_and_rejects_invalid_key_material() -> None:
    draw = uniform_below(bytearray(range(32)), b"allocation-frame", 12)

    assert type(draw) is UniformDraw
    assert 0 <= draw.value < 12
    with pytest.raises(ValueError, match="key"):
        uniform_below(b"x" * 32, b"allocation-frame", 12)  # type: ignore[arg-type]


def test_uniform_draw_counter_is_domain_framed() -> None:
    first = uniform_below(
        bytearray(range(32)), kdf_frame("draw", (BytesField(b"a"),)), 2
    )
    second = uniform_below(
        bytearray(range(32)), kdf_frame("draw", (BytesField(b"b"),)), 2
    )

    assert (first, second) == (UniformDraw(0, 0), UniformDraw(1, 0))
