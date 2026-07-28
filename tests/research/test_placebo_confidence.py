"""Tests for the logit-elicited, polarity-symmetrized self-report readout.

The properties locked here are the ones whose absence produced a wrong number
during instrument validation, not a generic API sweep. In order of how badly each
would corrupt the study:

  * mass summed over a TOKEN SET, because the API spreads the answer across case
    and whitespace variants and reading one token understates it;
  * escaped mass reported rather than hidden, because a normalized ratio always
    looks confident regardless of how much of the distribution it ignored;
  * an unanswerable probe raising instead of returning a value, because a
    silently substituted 0.5 is indistinguishable from a real coin flip;
  * symmetrization arithmetic, because a sign error there is invisible and
    displaces every arm by roughly 0.1.
"""

from __future__ import annotations

import math

import pytest

from pneuma_lab.placebo.confidence import (
    MIN_DECISIVE_MASS,
    NEGATIVE_PROBE,
    POSITIVE_PROBE,
    BinaryReadout,
    ConfidenceError,
    aggregateBinaryMass,
    elicitConfidence,
    normalizeToken,
    ollamaLogprobRequest,
    readoutFromPayload,
    symmetrize,
)


def entry(token: str, probability: float) -> dict:
    return {"token": token, "logprob": math.log(probability)}


def payloadOf(pairs: list[tuple[str, float]], response: str = "") -> dict:
    return {
        "response": response,
        "logprobs": [
            {
                "token": response,
                "logprob": math.log(max(pairs[0][1], 1e-12)),
                "top_logprobs": [entry(t, p) for t, p in pairs],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Token normalization and set membership
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("YES", "yes"),
        ("Yes", "yes"),
        (" YES", "yes"),
        (".YES", "yes"),
        ("_YES", "yes"),
        ("yes.", "yes"),
        ("  NO  ", "no"),
        ("No", "no"),
        ("TRUE", "true"),
    ],
)
def test_normalize_collapses_surface_variants(raw: str, expected: str) -> None:
    assert normalizeToken(raw) == expected


def test_mass_is_summed_over_the_whole_token_set_not_one_token() -> None:
    """The defect this exists to prevent: reading only the exact `YES` token.

    Observed live on the study model: YES 0.977, Yes 0.012, " YES" 0.0007,
    NO 0.0093. Taking the single token would report a different number from the
    one the model actually expressed.
    """
    readout = aggregateBinaryMass(
        [
            entry("YES", 0.60),
            entry("Yes", 0.20),
            entry(" YES", 0.05),
            entry("NO", 0.10),
            entry("No", 0.05),
        ]
    )
    assert readout.yes_mass == pytest.approx(0.85)
    assert readout.no_mass == pytest.approx(0.15)
    assert readout.p_yes == pytest.approx(0.85)
    # The single-token reading would have produced 0.60/(0.60+0.10) = 0.857.
    assert readout.p_yes != pytest.approx(0.60 / 0.70)


def test_non_answer_tokens_count_toward_captured_but_not_the_ratio() -> None:
    readout = aggregateBinaryMass(
        [entry("YES", 0.4), entry("NO", 0.2), entry("Maybe", 0.3)]
    )
    assert readout.decisive_mass == pytest.approx(0.6)
    assert readout.captured_mass == pytest.approx(0.9)
    assert readout.p_yes == pytest.approx(0.4 / 0.6)


def test_escaped_mass_is_reported_so_a_ratio_cannot_look_better_than_its_evidence() -> (
    None
):
    readout = aggregateBinaryMass([entry("YES", 0.05), entry("NO", 0.05)])
    assert readout.captured_mass == pytest.approx(0.10)
    assert readout.escaped_mass == pytest.approx(0.90)
    # The ratio is a confident-looking 0.5 while 90% of the distribution is
    # unaccounted for. The flag is what stops that being read as a coin flip.
    assert readout.p_yes == pytest.approx(0.5)
    assert not readout.decisive


def test_decisive_threshold_matches_the_declared_constant() -> None:
    just_under = aggregateBinaryMass(
        [entry("YES", MIN_DECISIVE_MASS / 2 - 0.01), entry("NO", MIN_DECISIVE_MASS / 2)]
    )
    assert not just_under.decisive
    just_over = aggregateBinaryMass(
        [entry("YES", MIN_DECISIVE_MASS / 2 + 0.01), entry("NO", MIN_DECISIVE_MASS / 2)]
    )
    assert just_over.decisive


# ---------------------------------------------------------------------------
# Refusals: a missing readout is never a substituted number
# ---------------------------------------------------------------------------


def test_no_yes_or_no_mass_raises_rather_than_returning_a_half() -> None:
    with pytest.raises(ConfidenceError, match="did not answer"):
        aggregateBinaryMass([entry("Maybe", 0.6), entry("Perhaps", 0.4)])


def test_missing_logprobs_raises_with_an_actionable_message() -> None:
    with pytest.raises(ConfidenceError, match="logprobs=true"):
        readoutFromPayload({"response": "YES"})


def test_malformed_entry_raises_rather_than_being_skipped() -> None:
    with pytest.raises(ConfidenceError, match="malformed"):
        aggregateBinaryMass([{"token": "YES"}])


def test_absent_alternatives_fall_back_to_the_selected_token_and_show_it() -> None:
    payload = {
        "response": "YES",
        "logprobs": [{"token": "YES", "logprob": math.log(0.9)}],
    }
    readout = readoutFromPayload(payload)
    assert readout.p_yes == pytest.approx(1.0)
    # Only one token was visible, so nearly all the mass is unaccounted for and
    # the readout says so instead of presenting a confident 1.0 unqualified.
    assert readout.captured_mass == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Symmetrization
# ---------------------------------------------------------------------------


def test_symmetrize_is_the_mean_of_a_polarity_and_its_complement() -> None:
    assert symmetrize(0.9, 0.1) == pytest.approx(0.9)
    assert symmetrize(0.5, 0.5) == pytest.approx(0.5)
    assert symmetrize(0.8, 0.8) == pytest.approx(0.5)


def test_symmetrize_cancels_a_uniform_yes_bias() -> None:
    """A model that adds the same push toward YES on both polarities nets out."""
    truth = 0.30
    bias = 0.25
    p_positive = min(1.0, truth + bias)
    p_negative = min(1.0, (1.0 - truth) + bias)
    assert symmetrize(p_positive, p_negative) == pytest.approx(truth, abs=1e-9)
    # ...whereas the single-polarity readout is off by exactly the bias.
    assert p_positive - truth == pytest.approx(bias)


def test_two_probes_differ_only_in_the_polarity_verb() -> None:
    """Any other difference would confound symmetrization with a prompt change."""
    positive = POSITIVE_PROBE.replace("PASS all hidden unit tests", "<Q>")
    negative = NEGATIVE_PROBE.replace("FAIL at least one hidden unit test", "<Q>")
    assert positive == negative


# ---------------------------------------------------------------------------
# End-to-end elicitation against an injected probe
# ---------------------------------------------------------------------------


def test_elicit_reports_both_polarities_and_the_gap() -> None:
    calls: list[str] = []

    def probe(prompt: str) -> dict:
        calls.append(prompt)
        if "PASS all hidden" in prompt:
            return payloadOf([("YES", 0.9), ("NO", 0.1)], response="YES")
        return payloadOf([("YES", 0.6), ("NO", 0.4)], response="YES")

    readout = elicitConfidence("spec", "code", probe=probe)
    assert len(calls) == 2
    assert readout.positive.p_yes == pytest.approx(0.9)
    assert readout.negative.p_yes == pytest.approx(0.6)
    assert readout.p_symmetrized == pytest.approx((0.9 + 0.4) / 2)
    # The gap is what the single-polarity design would have silently carried.
    assert readout.polarity_gap == pytest.approx(abs(0.9 - 0.65))


def test_elicit_is_deterministic_for_one_program() -> None:
    def probe(_prompt: str) -> dict:
        return payloadOf([("YES", 0.7), ("NO", 0.3)], response="YES")

    first = elicitConfidence("spec", "code", probe=probe)
    second = elicitConfidence("spec", "code", probe=probe)
    assert first.asRecord() == second.asRecord()


def test_record_carries_the_provenance_a_reader_needs_to_check_it() -> None:
    def probe(_prompt: str) -> dict:
        return payloadOf([("YES", 0.5), ("NO", 0.3), ("Maybe", 0.1)], response="YES")

    record = elicitConfidence("spec", "code", probe=probe).asRecord()
    for field in (
        "p_symmetrized",
        "p_positive_polarity",
        "p_negative_polarity",
        "polarity_gap",
        "decisive_mass_positive",
        "captured_mass_positive",
        "escaped_mass_positive",
        "decisive",
    ):
        assert field in record


# ---------------------------------------------------------------------------
# Request shape
# ---------------------------------------------------------------------------


def test_request_asks_for_one_greedy_token_with_alternatives() -> None:
    body = ollamaLogprobRequest("p", model="m", seed=7)
    assert body["logprobs"] is True
    assert body["top_logprobs"] == 20
    assert body["options"]["num_predict"] == 1
    assert body["options"]["temperature"] == 0.0
    assert body["options"]["seed"] == 7
    assert body["stream"] is False


def test_binary_readout_is_frozen() -> None:
    readout = BinaryReadout(0.5, 0.5, 0.5, 1.0, 1.0, "YES")
    with pytest.raises(Exception):
        readout.p_yes = 0.9  # type: ignore[misc]
