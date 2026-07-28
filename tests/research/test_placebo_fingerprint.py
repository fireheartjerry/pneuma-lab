"""Tests for instrument provenance on the elicited readout.

These lock the behaviour that would have caught a real defect. Two measurements
in this project were compared as though commensurate -- a planted effect and a
smallest-detectable-change -- while the prompts underneath differed by
"will THIS implementation pass" against "will YOUR implementation pass for this
problem". The template sets carried identical phrasing NAMES, so every review
passed over it, and the paper's headline compared across instruments.

The properties locked here are the ones that make that detectable by string
equality rather than by archaeology.
"""

from __future__ import annotations

import pytest

from pneuma_lab.placebo.confidence import (
    NEGATIVE_PROBE,
    POSITIVE_PROBE,
    ConfidenceError,
    assertSameInstrument,
    promptFingerprint,
)

THIS_WORDING = "Question: will this implementation PASS all hidden unit tests?"
YOUR_WORDING = (
    "Question: will your implementation PASS all hidden unit tests for this problem?"
)


def test_the_actual_defect_is_detected() -> None:
    """The two wordings that were compared across in the paper must not match."""
    assert promptFingerprint(THIS_WORDING) != promptFingerprint(YOUR_WORDING)


def test_identical_templates_fingerprint_identically() -> None:
    assert promptFingerprint(POSITIVE_PROBE) == promptFingerprint(POSITIVE_PROBE)


def test_fingerprint_is_order_sensitive() -> None:
    """A positive/negative pair swapped is a different instrument, not the same one."""
    assert promptFingerprint(POSITIVE_PROBE, NEGATIVE_PROBE) != promptFingerprint(
        NEGATIVE_PROBE, POSITIVE_PROBE
    )


@pytest.mark.parametrize(
    "variant",
    [
        THIS_WORDING + " ",  # trailing space
        THIS_WORDING.replace("PASS", "pass"),  # case
        THIS_WORDING.replace("?", "?\n"),  # whitespace
        THIS_WORDING.replace("hidden unit tests", "hidden tests"),  # wording
    ],
)
def test_fingerprint_does_not_normalise(variant: str) -> None:
    """Deliberately brittle: any textual change is a different instrument.

    Normalising would defeat the purpose. This paper's own result is that
    small wording changes move the readout up to four-fold, so a fingerprint
    that forgave them would certify exactly the comparisons that are unsound.
    """
    assert promptFingerprint(variant) != promptFingerprint(THIS_WORDING)


def test_matching_instruments_are_allowed() -> None:
    fp = promptFingerprint(POSITIVE_PROBE, NEGATIVE_PROBE)
    assertSameInstrument(fp, fp, fp)


def test_mismatched_instruments_raise_rather_than_warn() -> None:
    a = promptFingerprint(THIS_WORDING)
    b = promptFingerprint(YOUR_WORDING)
    with pytest.raises(ConfidenceError, match="not comparable"):
        assertSameInstrument(a, b)


def test_empty_fingerprints_are_ignored_not_treated_as_a_match() -> None:
    """An unstamped artifact must not silently certify a comparison."""
    fp = promptFingerprint(POSITIVE_PROBE)
    assertSameInstrument(fp, "")  # unknown provenance does not itself conflict
    with pytest.raises(ConfidenceError):
        assertSameInstrument(fp, "", promptFingerprint(YOUR_WORDING))


def test_fingerprint_over_nothing_is_refused() -> None:
    with pytest.raises(ConfidenceError, match="meaningless"):
        promptFingerprint()


def test_fingerprint_is_short_enough_to_read_in_an_artifact_header() -> None:
    fp = promptFingerprint(POSITIVE_PROBE)
    assert len(fp) == 16
    assert all(c in "0123456789abcdef" for c in fp)
