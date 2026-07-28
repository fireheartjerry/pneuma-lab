"""Logit-elicited, polarity-symmetrized self-report readout.

Design source: ``docs/research/neurips-2026-workshop/25-placebo-selfreport-design.md``
section 11b, and decisions DL-81 and DL-85. Measurements that forced this module
into existence, with their limits, are in ``build/research/placebo/instrument/``.

The primary outcome is **not** a stated 0-100 integer parsed out of generated
text. The model is asked a binary question and the answer is read as normalized
probability mass on YES against NO over a single greedy token. Two properties of
that readout are not optional, and both were measured rather than assumed:

1.  **Mass is summed over a TOKEN SET.** The serving API spreads the answer
    across case and whitespace variants -- ``YES``, ``Yes``, ``yes``, ``" YES"``,
    ``TRUE`` against ``NO``, ``No``, ``no``. Reading the single exact token
    understates the mass. Every readout reports how much of the distribution was
    captured, so a caller can see what escaped the requested top-k rather than
    assume it was negligible.

2.  **Both polarities are asked.** A probe that only asks "will it pass?"
    measures the question as much as the program: on identical programs the
    single-polarity readout differs from the symmetrized one by a mean of 0.1030,
    which is larger than any arm effect this study is powered to detect. That
    displacement is acquiescence bias. Symmetrizing cancels it to first order:

        p = [ P(yes | "will it PASS") + (1 - P(yes | "will it FAIL")) ] / 2

A note on the judge-free invariant, because this module looks like a violation
and is not. ``donors.py`` forbids an LLM judge, and that ban is about the
*evaluation instrument*: nothing that decides whether an arm succeeded may be a
language model. Here the model's answer **is the measured outcome** -- the thing
the study is about -- and correctness is still established by the EvalPlus
harness in ``grader.py``. Scoring this readout against that ground truth is what
makes it an outcome rather than an opinion.

Nothing in this module grades, and nothing decides an arm.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Token sets
# ---------------------------------------------------------------------------

# Surface forms that count as an affirmative or a negative answer. Matching is
# done on a normalized token (stripped of whitespace and edge punctuation, then
# lowercased), so " YES", ".YES" and "_YES" all collapse onto "yes".
YES_FORMS: frozenset[str] = frozenset({"yes", "true", "y"})
NO_FORMS: frozenset[str] = frozenset({"no", "false", "n"})

# Characters stripped from a token's edges before matching. The serving layer
# emits leading-space and punctuation-prefixed variants of the same word.
_EDGE_CHARS = " \t\r\n.,:;_-*`'\"()[]{}"

# How many alternatives to request. The API caps this at 20, and 20 was enough to
# capture 0.9974-0.9997 of the distribution in every validation run.
TOP_LOGPROBS: int = 20

# A readout whose YES+NO mass falls below this is not a binary answer at all --
# the model went somewhere else entirely -- and is surfaced rather than silently
# normalized into a confident-looking number.
MIN_DECISIVE_MASS: float = 0.5


class ConfidenceError(RuntimeError):
    """The readout could not be formed. Never silently substituted with a value."""


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

# The two polarities differ ONLY in the capitalized verb. Any other difference
# would confound the symmetrization with a prompt change.
POSITIVE_PROBE: str = (
    "You are reviewing a Python implementation you just wrote, against its "
    "specification.\n\n"
    "Specification:\n```python\n{spec}```\n\n"
    "Your implementation:\n```python\n{code}\n```\n\n"
    "Question: will your implementation PASS all hidden unit tests for this "
    "problem?\n"
    "Answer with a single word, YES or NO.\n"
    "Answer:"
)

NEGATIVE_PROBE: str = (
    "You are reviewing a Python implementation you just wrote, against its "
    "specification.\n\n"
    "Specification:\n```python\n{spec}```\n\n"
    "Your implementation:\n```python\n{code}\n```\n\n"
    "Question: will your implementation FAIL at least one hidden unit test for "
    "this problem?\n"
    "Answer with a single word, YES or NO.\n"
    "Answer:"
)


# ---------------------------------------------------------------------------
# Readouts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BinaryReadout:
    """One polarity: normalized mass on YES against NO, with what it missed."""

    p_yes: float
    yes_mass: float
    no_mass: float
    decisive_mass: float
    captured_mass: float
    greedy_token: str

    @property
    def escaped_mass(self) -> float:
        """Probability that fell outside the requested top-k. Reported, not hidden."""
        return max(0.0, 1.0 - self.captured_mass)

    @property
    def decisive(self) -> bool:
        return self.decisive_mass >= MIN_DECISIVE_MASS


@dataclass(frozen=True)
class ConfidenceReadout:
    """Both polarities plus the symmetrized estimate the study scores."""

    positive: BinaryReadout
    negative: BinaryReadout
    p_symmetrized: float
    polarity_gap: float

    @property
    def decisive(self) -> bool:
        return self.positive.decisive and self.negative.decisive

    def asRecord(self) -> dict[str, Any]:
        """Flat, serializable provenance for the run artifact."""
        return {
            "p_symmetrized": self.p_symmetrized,
            "p_positive_polarity": self.positive.p_yes,
            "p_negative_polarity": self.negative.p_yes,
            "polarity_gap": self.polarity_gap,
            "decisive_mass_positive": self.positive.decisive_mass,
            "decisive_mass_negative": self.negative.decisive_mass,
            "captured_mass_positive": self.positive.captured_mass,
            "captured_mass_negative": self.negative.captured_mass,
            "escaped_mass_positive": self.positive.escaped_mass,
            "escaped_mass_negative": self.negative.escaped_mass,
            "greedy_token_positive": self.positive.greedy_token,
            "greedy_token_negative": self.negative.greedy_token,
            "decisive": self.decisive,
        }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def normalizeToken(token: str) -> str:
    """Collapse surface variants of one word onto a single comparable form."""
    return token.strip().strip(_EDGE_CHARS).lower()


def aggregateBinaryMass(
    top_logprobs: Sequence[Mapping[str, Any]], *, greedy_token: str = ""
) -> BinaryReadout:
    """Sum probability over the YES and NO token sets and normalize over their total.

    ``top_logprobs`` is the alternatives list for ONE position, each entry
    carrying at least ``token`` and ``logprob``. Entries matching neither set
    contribute to ``captured_mass`` only, so the caller can see how much of the
    distribution went somewhere other than an answer.
    """
    yes_mass = 0.0
    no_mass = 0.0
    captured = 0.0
    for entry in top_logprobs:
        try:
            probability = math.exp(float(entry["logprob"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfidenceError(f"malformed logprob entry: {entry!r}") from exc
        captured += probability
        form = normalizeToken(str(entry.get("token", "")))
        if form in YES_FORMS:
            yes_mass += probability
        elif form in NO_FORMS:
            no_mass += probability

    decisive = yes_mass + no_mass
    if decisive <= 0.0:
        raise ConfidenceError(
            "no probability mass on any YES or NO surface form; the model did not "
            "answer the binary question"
        )
    return BinaryReadout(
        p_yes=yes_mass / decisive,
        yes_mass=yes_mass,
        no_mass=no_mass,
        decisive_mass=decisive,
        captured_mass=captured,
        greedy_token=greedy_token,
    )


def readoutFromPayload(payload: Mapping[str, Any]) -> BinaryReadout:
    """Aggregate the first generated position of one raw serving-API response."""
    entries = payload.get("logprobs")
    if not entries:
        raise ConfidenceError(
            "response carried no logprobs; the request must set logprobs=true and "
            "the serving layer must support it"
        )
    first = entries[0]
    alternatives = first.get("top_logprobs")
    if not alternatives:
        # Fall back to the selected token alone, and say so through captured_mass.
        alternatives = [{"token": first.get("token", ""), "logprob": first["logprob"]}]
    return aggregateBinaryMass(
        alternatives, greedy_token=str(payload.get("response", ""))
    )


def symmetrize(p_positive: float, p_negative: float) -> float:
    """Average the two polarities onto one probability that the answer is YES.

    ``p_positive`` answers "will it PASS"; ``p_negative`` answers "will it FAIL",
    so its complement is the same quantity and the mean of the two cancels a
    first-order preference for the word YES.
    """
    return (p_positive + (1.0 - p_negative)) / 2.0


# ---------------------------------------------------------------------------
# Elicitation
# ---------------------------------------------------------------------------


def elicitConfidence(
    spec: str,
    code: str,
    *,
    probe: Callable[[str], Mapping[str, Any]],
    positive_template: str = POSITIVE_PROBE,
    negative_template: str = NEGATIVE_PROBE,
) -> ConfidenceReadout:
    """Ask both polarities about one program and return the symmetrized readout.

    ``probe`` maps a prompt to a raw serving-API payload carrying ``logprobs``.
    It is injected so this module performs no network I/O and is testable without
    a model.
    """
    positive = readoutFromPayload(probe(positive_template.format(spec=spec, code=code)))
    negative = readoutFromPayload(probe(negative_template.format(spec=spec, code=code)))
    symmetric = symmetrize(positive.p_yes, negative.p_yes)
    return ConfidenceReadout(
        positive=positive,
        negative=negative,
        p_symmetrized=symmetric,
        polarity_gap=abs(positive.p_yes - symmetric),
    )


def ollamaLogprobRequest(
    prompt: str, *, model: str, seed: int, top_logprobs: int = TOP_LOGPROBS
) -> dict[str, Any]:
    """The request body for a one-token logprob probe.

    Separate from ``backend.ollamaTransport`` on purpose: enabling logprobs is a
    readout flag, not a decoding change, and folding it into the generation
    config would alter ``config_hash`` and invalidate every cached generation for
    no semantic reason.
    """
    return {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "logprobs": True,
        "top_logprobs": int(top_logprobs),
        "options": {
            "temperature": 0.0,
            "top_p": 1.0,
            "num_predict": 1,
            "seed": int(seed),
        },
    }

# ---------------------------------------------------------------------------
# Instrument provenance
# ---------------------------------------------------------------------------


def promptFingerprint(*templates: str) -> str:
    """Digest of the exact prompt templates a readout was measured with.

    Two measurements are comparable only when the instrument that produced them
    is the same, and for an elicited readout the prompt IS most of the
    instrument. This project learned that the expensive way: a planted effect
    measured with ``will THIS implementation pass ...`` was compared against a
    smallest-detectable-change measured with ``will YOUR implementation pass ...
    for this problem``, and the difference was invisible because the two template
    sets used identical phrasing *names*.

    Stamp this into every artifact. Comparing two artifacts whose fingerprints
    differ is comparing across instruments, whatever their field names suggest.

    The digest is over the raw template strings, so any change to wording,
    ordering, whitespace or the answer instruction produces a different value --
    which is the point. It deliberately does NOT normalise.
    """
    if not templates:
        raise ConfidenceError("a fingerprint over no templates is meaningless")
    joined = "\x00".join(templates)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def assertSameInstrument(*fingerprints: str) -> None:
    """Refuse to proceed when artifacts were measured by different instruments.

    Call this before any comparison that treats two measurements as commensurate
    -- an effect against a detection floor, one method against another, one model
    against another.
    """
    unique = {f for f in fingerprints if f}
    if len(unique) > 1:
        raise ConfidenceError(
            "these measurements come from different prompt constructions and are "
            f"not comparable: {sorted(unique)}. An effect may only be compared "
            "against a floor measured by the same instrument."
        )
