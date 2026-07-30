"""Pin the P0 kernel optimizations to the exact prior arithmetic.

The screen and grid kernels were made fast enough to satisfy the frozen
12-hour total-work cap.  Every change was a representation or reuse change,
never a scientific one, so these tests re-derive each result with the original
`Fraction`/fresh-generator formulation and require exact equality.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction

import numpy as np
import pytest

from pneuma_lab.resampling_null.analysis import (
    _DYNAMIC_STATE_LIMIT,
    _PATTERNS,
    _count_resolution,
    _count_sharp_tail,
    _rng,
)
from pneuma_lab.resampling_null.assignment import _TEXT_CACHE_MAX_LENGTH, _text_payload
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.power import (
    _philox_draw,
    _strict_sha256,
    bernoulli_pattern_probabilities,
    philox_generator,
)

pytestmark = pytest.mark.milestone

_DIGEST = "ab" * 32
_GRID = "cd" * 32


def _reference_sharp_tail(counts: np.ndarray, *, excess: bool, draws: int, seed: int) -> np.ndarray:
    """The original exact-rational per-choice dynamic program."""
    result = np.empty(counts.shape[0], dtype=float)
    for run in range(counts.shape[0]):
        choices: list[tuple[Fraction, ...]] = []
        observed = Fraction()
        for benchmark_index in range(2):
            n = int(counts[run, benchmark_index].sum())
            weight = Fraction(1, 2 * n)
            for index, amount in enumerate(counts[run, benchmark_index]):
                real, sham, none, resample = _PATTERNS[index]
                if excess:
                    values = (real, none, resample)
                    options = tuple(weight * Fraction(3 * value - sum(values), 2) for value in values)
                    observed += weight * Fraction(2 * real - none - resample, 2) * int(amount)
                else:
                    options = (weight * (real - sham), weight * (sham - real))
                    observed += weight * (real - sham) * int(amount)
                choices.extend([options] * int(amount))
        distribution: Counter[Fraction] = Counter({Fraction(): 1})
        for options in choices:
            following: Counter[Fraction] = Counter()
            for previous, mass in distribution.items():
                for option in options:
                    following[previous + option] += mass
            distribution = following
            if len(distribution) > _DYNAMIC_STATE_LIMIT:
                generator = _rng(seed, "excess" if excess else "content")
                exceeds = 0
                for _ in range(draws):
                    statistic = sum(
                        (option[int(generator.integers(len(option)))] for option in choices), Fraction(),
                    )
                    exceeds += statistic >= observed
                result[run] = (1 + exceeds) / (1 + draws)
                break
        else:
            total = sum(distribution.values())
            result[run] = sum(mass for value, mass in distribution.items() if value >= observed) / total
    return result


def _reference_resolution(counts: np.ndarray) -> np.ndarray:
    output = np.empty(counts.shape[0], dtype=float)
    for run in range(counts.shape[0]):
        roster = [int(counts[run, benchmark].sum()) for benchmark in range(2)]
        discordant = [
            int(sum(
                counts[run, benchmark, index]
                for index, pattern in enumerate(_PATTERNS) if pattern[2] != pattern[3]
            ))
            for benchmark in range(2)
        ]
        distribution: Counter[Fraction] = Counter({Fraction(): 1})
        for benchmark, count in enumerate(discordant):
            weight = Fraction(1, 2 * roster[benchmark])
            for _ in range(count):
                following: Counter[Fraction] = Counter()
                for old, mass in distribution.items():
                    following[old + weight] += mass
                    following[old - weight] += mass
                distribution = following
        masses: Counter[Fraction] = Counter()
        for value, mass in distribution.items():
            masses[abs(value)] += mass
        total, cumulative = sum(masses.values()), 0
        for value in sorted(masses):
            cumulative += masses[value]
            if cumulative * 20 >= total * 19:
                output[run] = float(value)
                break
    return output


def _random_count_tensors(seed: int, trials: int) -> list[np.ndarray]:
    generator = np.random.default_rng(seed)
    tensors = []
    for trial in range(trials):
        swe = int(generator.integers(4, 21))
        tau = swe if trial % 2 else int(generator.integers(4, 21))
        rows = [generator.multinomial(size, np.full(16, 1 / 16)) for size in (swe, tau)]
        tensors.append(np.asarray([rows], dtype=np.int64))
    return tensors


@pytest.mark.parametrize("excess", [False, True])
def test_count_sharp_tail_matches_exact_rational_reference(excess: bool) -> None:
    for counts in _random_count_tensors(20260730, 40):
        expected = _reference_sharp_tail(counts, excess=excess, draws=9, seed=0)
        assert np.array_equal(_count_sharp_tail(counts, excess=excess, draws=9, seed=0), expected)


def test_count_resolution_matches_exact_rational_reference() -> None:
    for counts in _random_count_tensors(20260731, 40):
        assert np.array_equal(_count_resolution(counts), _reference_resolution(counts))


def test_reused_philox_slot_emits_the_public_generator_stream() -> None:
    cases = (
        ("screen", "screen_trigger_partition", 0),
        ("grid", "grid_triggered_pattern", 3),
        ("validation", "gaussian_validation_no_trigger_success", 7),
    )
    for replicate in range(8):
        for domain, kind, index in cases:
            arguments = (
                "synthetic_validation", _DIGEST, _GRID, domain,
                "gaussian_approximation", f"cell-{replicate}", replicate, kind, index,
            )
            expected = philox_generator(*arguments).integers(0, 2**63, size=19)
            assert np.array_equal(_philox_draw(*arguments).integers(0, 2**63, size=19), expected)


def test_reused_philox_slot_is_invalidated_by_the_next_draw() -> None:
    """The shared slot is documented as single-use; prove the aliasing is real."""
    first = _philox_draw("synthetic_validation", _DIGEST, _GRID, "screen",
                         "gaussian_approximation", "cell-0", 0, "screen_trigger_partition", 0)
    second = _philox_draw("synthetic_validation", _DIGEST, _GRID, "screen",
                          "gaussian_approximation", "cell-0", 1, "screen_trigger_partition", 0)
    assert first is second


def test_cached_text_admission_keeps_per_field_messages() -> None:
    """The admission cache is keyed on the text alone; the label must not leak."""
    for _ in range(2):
        with pytest.raises(ValueError, match="frame tag must already be NFC-normalized"):
            _text_payload("Á", field="frame tag")
        with pytest.raises(ValueError, match="TEXT field value must already be NFC-normalized"):
            _text_payload("Á", field="TEXT field value")
        with pytest.raises(ValueError, match="frame tag must be non-empty"):
            _text_payload("", field="frame tag")
        with pytest.raises(ValueError, match="frame tag contains a forbidden Unicode category"):
            _text_payload("a\x00b", field="frame tag")
    long_value = "a" * (_TEXT_CACHE_MAX_LENGTH + 1)
    assert _text_payload(long_value, field="frame tag") == long_value.encode("ascii")
    assert _text_payload("power-rng-key-v1", field="frame tag") == b"power-rng-key-v1"


@pytest.mark.parametrize("value", ["A" * 64, "a" * 63, "a" * 65, "g" * 64, "a" * 63 + "\n", 42])
def test_strict_sha256_rejects_non_lowercase_hex(value: object) -> None:
    with pytest.raises(RecordValidationError):
        _strict_sha256(value, field="digest")


def test_strict_sha256_accepts_the_registered_form() -> None:
    assert _strict_sha256(_DIGEST, field="digest") == _DIGEST


def test_pattern_probability_memoization_is_value_stable() -> None:
    first = bernoulli_pattern_probabilities((0.25, 0.4, 0.6, 0.8), 0.4)
    second = bernoulli_pattern_probabilities((0.25, 0.4, 0.6, 0.8), 0.4)
    assert first == second
    assert first.probabilities == second.probabilities
    with pytest.raises(ValueError):
        bernoulli_pattern_probabilities((0.25, 0.4, 0.6, 1.0), 0.4)
