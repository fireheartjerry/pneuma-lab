"""Tests for the cross-artifact reuse detector.

The detector's value is entirely in what it still catches AFTER a declaration is
added. A declaration that quietly widened to cover a whole artifact pair would
turn the check into decoration -- it would report green while the next copied row
went through, which is exactly the failure it exists to prevent.

So the properties under test are the negative ones: a declared pair does not
excuse a third artifact, a different row, or a different field.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "paper" / "check_instrument_reuse.py"
)
_spec = importlib.util.spec_from_file_location("check_instrument_reuse", _MODULE_PATH)
assert _spec and _spec.loader
reuse = importlib.util.module_from_spec(_spec)
sys.modules["check_instrument_reuse"] = reuse
_spec.loader.exec_module(reuse)

# The declared known-defect pair: floor_metrology <-> resolving_power's
# logit_symmetric row.
DEFECT_ENTRY = next(
    patterns
    for patterns, reason in reuse.DECLARED
    if any(name == "floor_metrology.json" for name, _path in patterns)
)


def test_the_declared_defect_is_covered() -> None:
    sites = [
        ("floor_metrology.json", "sem"),
        ("resolving_power.json", "summary.logit_symmetric.sem"),
    ]
    assert reuse.isDeclared(sites, DEFECT_ENTRY)


def test_a_third_artifact_is_not_excused() -> None:
    """A value in the declared pair AND somewhere new is new information."""
    sites = [
        ("floor_metrology.json", "sem"),
        ("resolving_power.json", "summary.logit_symmetric.sem"),
        ("gauge_llama3_1_8b.json", "gauge.sem"),
    ]
    assert not reuse.isDeclared(sites, DEFECT_ENTRY)


def test_a_different_row_of_the_same_artifact_is_not_excused() -> None:
    """Declaring the copied row must not excuse a copy into a clean row."""
    sites = [
        ("floor_metrology.json", "sem"),
        ("resolving_power.json", "summary.verbalized_int.sem"),
    ]
    assert not reuse.isDeclared(sites, DEFECT_ENTRY)


def test_before_after_reuse_is_covered_but_after_values_are_not() -> None:
    before_entry = next(
        patterns
        for patterns, reason in reuse.DECLARED
        if any(name == "interaction_gate.json" for name, _path in patterns)
    )
    before = [
        ("interaction_gate.json", "d_by_phrasing.terse"),
        ("planted_effect_verified.json", "by_phrasing.terse.before"),
    ]
    after = [
        ("interaction_gate.json", "d_by_phrasing.terse"),
        ("planted_effect_verified.json", "by_phrasing.terse.after"),
    ]
    assert reuse.isDeclared(before, before_entry)
    assert not reuse.isDeclared(after, before_entry), (
        "an 'after' value equal to the original would mean the re-analysis "
        "changed nothing, which is a real finding and must not be declared away"
    )


@pytest.mark.parametrize(
    ("value", "expected_at_least"),
    [(0.22271899371832724, 17), (0.7100115640563864, 16), (0.5, 1), (53.85, 4)],
)
def test_significant_digits_separates_copies_from_agreement(
    value: float, expected_at_least: int
) -> None:
    assert reuse.significantDigits(value) >= expected_at_least


def test_rounded_agreement_is_below_the_copy_threshold() -> None:
    """Two runs agreeing to four decimals must NOT be flagged as a copy."""
    assert reuse.significantDigits(0.2227) < reuse.SIGNIFICANT_DIGITS


def test_structural_keys_are_not_treated_as_measurements() -> None:
    """Shared part counts and seeds are meaningful agreement, not copying."""
    found = reuse.walkFloats({"n_parts": 40.0, "sdc95": 0.22271899371832724})
    paths = [path for path, _value in found]
    assert "sdc95" in paths
    assert "n_parts" not in paths


def test_bulk_measurement_arrays_are_skipped() -> None:
    """A shared element of a score matrix is noise; a shared summary stat is not."""
    long_list = {"scores": [0.1234567890123456] * 40}
    assert reuse.walkFloats(long_list) == []


def test_the_check_passes_on_the_current_artifacts() -> None:
    """The released artifacts must contain no undeclared reuse."""
    assert reuse.main() == 0


def test_floor_bindings_hold_on_the_current_artifacts() -> None:
    """Every declared floor must equal the artifact it claims to come from."""
    assert reuse.checkFloorBindings((_MODULE_PATH.parent,)) == []


def test_every_floor_binding_names_a_real_pair() -> None:
    """A binding pointing at a missing file would pass vacuously if unchecked."""
    assert reuse.FLOOR_BINDINGS, "at least the figure floor must be bound"
    for file, path, source_file, source_path in reuse.FLOOR_BINDINGS:
        assert file and path and source_file and source_path
        assert file != source_file, "a floor bound to itself checks nothing"


def test_resolve_path_walks_nested_keys() -> None:
    payload = {"gauge": {"sdc95": 0.25}, "flat": 1.0}
    assert reuse.resolvePath(payload, "gauge.sdc95") == 0.25
    assert reuse.resolvePath(payload, "flat") == 1.0
    assert reuse.resolvePath(payload, "gauge.missing") is None
    assert reuse.resolvePath(payload, "flat.deeper") is None


def test_prose_counts_match_their_artifacts() -> None:
    """Every count the paper asserts must equal the artifact behind it."""
    assert reuse.checkTexBindings("placebo", (_MODULE_PATH.parent,)) == []


def test_a_binding_whose_sentence_vanished_is_reported() -> None:
    """A binding that matches nothing silently guards nothing.

    This is the failure mode that makes check suites decorative: the sentence is
    rewritten, the regex stops matching, and the check keeps reporting green while
    covering nothing. It must be loud instead.
    """
    problems = reuse.checkTexBindings("no_such_job", (_MODULE_PATH.parent,))
    assert problems == [], "a missing job file is not an error"

    original = reuse.TEX_BINDINGS
    try:
        reuse.TEX_BINDINGS = (
            (
                r"this sentence does not appear anywhere \((\d+)\)",
                "make_figure_data.json",
                "n_pairs",
                "deliberately unmatched",
            ),
        )
        problems = reuse.checkTexBindings("placebo", (_MODULE_PATH.parent,))
        assert len(problems) == 1
        assert "guards nothing" in problems[0]
    finally:
        reuse.TEX_BINDINGS = original


def test_every_tex_binding_has_exactly_one_capture_group() -> None:
    import re

    for pattern, _file, _path, label in reuse.TEX_BINDINGS:
        assert re.compile(pattern).groups == 1, label


@pytest.mark.parametrize(
    "value",
    [
        0.7133333333333334,  # 214/300, the live false positive
        0.7466666666666667,  # 56/75
        0.755,  # 151/200
        0.5,
    ],
)
def test_discrete_statistics_are_not_treated_as_fingerprints(value: float) -> None:
    """AUROC over fixed labels can only take n_pos*n_neg+1 values; ties are expected."""
    assert reuse.isDiscreteStatistic(value)


@pytest.mark.parametrize(
    "value",
    [
        0.22271899371832724,  # SDC95, a real copy
        0.7100115640563864,  # ICC, a real copy
        0.0803500565088129,  # SEM, a real copy
        53.850574364960465,  # %GRR, a real copy
    ],
)
def test_continuous_measurements_are_still_fingerprints(value: float) -> None:
    """The filter must not excuse the copies the check was written to catch."""
    assert not reuse.isDiscreteStatistic(value)


def test_discrete_detection_tolerates_arithmetic_rounding() -> None:
    """A count-ratio computed as a difference is still a count-ratio.

    0.14705882352941174 is 5/34 -- a recall spread over 34 failures -- but
    computing it as max minus min left it one ULP from float(5/34). Exact equality
    called it continuous and the check reported a false copy.
    """
    assert reuse.isDiscreteStatistic(0.14705882352941174)
    assert reuse.isDiscreteStatistic(3 / 34 - 1 / 34)


def test_tolerance_does_not_swallow_real_copies() -> None:
    """The loosened comparison must not excuse the four copies it was built for."""
    for value in (
        0.22271899371832724,
        0.7100115640563864,
        0.0803500565088129,
        53.850574364960465,
    ):
        assert not reuse.isDiscreteStatistic(value), value
