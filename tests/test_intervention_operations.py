"""Pure operation semantics: clamp/disable/boost/noise/ablate/restore + noise determinism."""

from __future__ import annotations

from pneuma_lab.interventions import operations as ops


def test_clamp_forces_value():
    assert ops.apply_scalar("clamp", 0.9, 0.0) == 0.0
    assert ops.apply_scalar("clamp", -0.5, 0.3) == 0.3


def test_boost_is_additive_and_clipped():
    assert ops.apply_scalar("boost", 0.5, 0.2) == 0.7
    assert ops.apply_scalar("boost", 0.95, 0.2) == 1.0  # clipped to +1


def test_disable_and_ablate_zero_the_scalar():
    assert ops.apply_scalar("disable", 0.8, None) == 0.0
    assert ops.apply_scalar("ablate", -0.8, None) == 0.0


def test_restore_is_a_noop():
    assert ops.apply_scalar("restore", 0.42, 0.0) == 0.42


def test_noise_is_deterministic_and_bounded():
    a = ops.apply_scalar("noise", 0.0, 1.0, seed="exp:3:tension")
    b = ops.apply_scalar("noise", 0.0, 1.0, seed="exp:3:tension")
    c = ops.apply_scalar("noise", 0.0, 1.0, seed="exp:4:tension")
    assert a == b  # same seed ⇒ same perturbation (replay-safe)
    assert a != c  # different seed ⇒ different perturbation
    assert -1.0 <= a <= 1.0


def test_deterministic_noise_unit_range():
    n = ops.deterministic_noise("anything")
    assert -1.0 <= n <= 1.0


def test_unknown_operation_raises():
    import pytest

    with pytest.raises(ValueError):
        ops.apply_scalar("teleport", 0.0, 1.0)
