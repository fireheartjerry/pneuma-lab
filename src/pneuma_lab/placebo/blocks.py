"""Payload builders and parity asserters for the seven-arm repair study.

Design source: ``docs/research/neurips-2026-workshop/25-placebo-selfreport-design.md``,
sections 5 (arms), 6 (parity), and 9b (the placebo construction). Section 9b is
binding and supersedes the section-5 placebo definitions.

The central commitment, restated because it is easy to get wrong:

    **The primary placebo is a TASK-BLIND PROCEDURAL reflection, not a donor
    reflection about a different problem.**

A donor reflection introduces concrete but irrelevant or false advice, so the
donor contrast estimates *content versus misinformation*. It is retained as a
separate arm (:func:`buildDonorReflection`) precisely because that contrast is
interesting, but it is not the primary placebo. The primary placebo
(:func:`buildTaskBlindPlacebo`) is produced by the same frozen reflector model
under an identical schema and field order, with every task-specific field
replaced by deterministic, token-count-matched withheld material.

Task-blindness is enforced **structurally, not by convention**:
:func:`buildTaskBlindPlacebo` refuses anything except a
:class:`BlindReflectorInputs`, and that type has ``__slots__`` holding only two
allowlisted enum-like strings and three integer token counts. There is no field
on it that can carry problem text, generated code, test names or values,
exceptions, entity names, the real reflection, or any solution. The only bridge
from a :class:`FailureTuple` is :func:`redactToBlind`, which reads lengths and
discards content.

Every payload -- real, task-blind, donor, neutral filler, and both oracle doses
-- shares one fixed schema (``Observation`` / ``Principle`` / ``Revision plan``),
one byte-identical header and delimiter pair, and one absolute prompt-slot
index.

Parity is a **validity gate reported as data**. The asserters here measure and
return a per-item record; they never silently repair a defect and they do not
raise on a parity failure, because a parity failure is a finding that belongs in
the matching-audit table.

Nothing in this module performs network I/O. The reflector backend is resolved
lazily at call time, so a caller that supplies its own ``generate`` callable
never imports it at all.
"""

from __future__ import annotations

import hashlib
import re
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, fields

# ---------------------------------------------------------------------------
# Arm identifiers
# ---------------------------------------------------------------------------

# Family R -- post-failure reflection.
ARM_R0_NONE: str = "R0_NONE"
ARM_R1_PLACEBO_RANDOM: str = "R1_PLACEBO_RANDOM"
ARM_R2_PLACEBO_MATCHED: str = "R2_PLACEBO_MATCHED"
ARM_R3_REAL: str = "R3_REAL"

# The primary placebo of section 9b. Named separately from the donor arms so no
# analysis can accidentally treat a donor reflection as "the placebo".
ARM_P_TASK_BLIND: str = "P_TASK_BLIND"

# Family C -- graded positive control.
ARM_C1_ORACLE_FULL: str = "C1_ORACLE_FULL"
ARM_C2_ORACLE_REDACTED: str = "C2_ORACLE_REDACTED"

# Shared -- compute control. No payload content; the runner draws ONE ADDITIONAL
# independent attempt-2 sample at matched decoding and matched compute.
#
# Without it the nonspecific-helper term is confounded with "the arm simply got
# another draw." Note the precondition, which is not optional and is enforced by
# `assertResampleIsMeaningful`: under greedy decoding a second draw at the same
# prompt is BYTE-IDENTICAL, so this arm measures exactly nothing at temperature
# zero and its inclusion there would be decorative.
ARM_S_RESAMPLE: str = "S_RESAMPLE"

# The confirmatory roster, in reporting order. Seven arms: `C2_ORACLE_REDACTED`
# was dropped as descope item one and `S_RESAMPLE` took the budget, so the count
# is unchanged and the compute control is bought with the second oracle dose.
ARM_ORDER: tuple[str, ...] = (
    ARM_R0_NONE,
    ARM_P_TASK_BLIND,
    ARM_R1_PLACEBO_RANDOM,
    ARM_R2_PLACEBO_MATCHED,
    ARM_R3_REAL,
    ARM_S_RESAMPLE,
    ARM_C1_ORACLE_FULL,
)

# Every arm this module can build, including the descoped one. Kept so a parity
# record over an opt-in roster still orders its rows, and so restoring C2 is a
# flag rather than a rebuild.
ARM_ORDER_ALL: tuple[str, ...] = ARM_ORDER + (ARM_C2_ORACLE_REDACTED,)

# The arm whose realized token count defines the parity target for the tuple.
REFERENCE_ARM: str = ARM_R3_REAL

# All arms whose payload is a placebo in the paper's sense. They share ONE
# tolerance, applied identically -- asymmetric tolerances would let the analysis
# tune which placebo looks best matched.
PLACEBO_ARMS: tuple[str, ...] = (
    ARM_P_TASK_BLIND,
    ARM_R1_PLACEBO_RANDOM,
    ARM_R2_PLACEBO_MATCHED,
)

ORACLE_DOSE_FULL: str = "full"
ORACLE_DOSE_REDACTED: str = "redacted"
ORACLE_DOSES: tuple[str, ...] = (ORACLE_DOSE_FULL, ORACLE_DOSE_REDACTED)

# The confirmatory roster carries the FULL dose only. `C2_ORACLE_REDACTED` is
# item one of the preregistered descope order, and it is dropped so the budget
# it consumed goes to the perturbation floor instead. What is given up is stated
# rather than quietly lost: with one dose the positive control can still show
# that the injection path works, but it can no longer report the MINIMUM content
# dose the instrument resolves. The builder is retained and tested so the arm can
# be restored without rebuilding it.
CONFIRMATORY_ORACLE_DOSES: tuple[str, ...] = (ORACLE_DOSE_FULL,)

# ---------------------------------------------------------------------------
# Fixed payload structure. Structural parity is defined against these constants;
# changing any of them invalidates every previously collected parity receipt.
# ---------------------------------------------------------------------------

PAYLOAD_HEADER: str = "### POST-FAILURE REFLECTION"
PAYLOAD_DELIMITER: str = "-----"
BULLET_MARKER: str = "-"
SCHEMA_SECTIONS: tuple[str, ...] = ("Observation", "Principle", "Revision plan")

DEFAULT_BULLETS_PER_SECTION: int = 3
DEFAULT_PROMPT_SLOT_INDEX: int = 3  # slot 4 of the five-slot attempt-2 prompt
TOKEN_PARITY_TOLERANCE: int = 2

# ---------------------------------------------------------------------------
# Reflector prompt structure. Real and task-blind reflections render through the
# SAME field-order constant, so identical field order is a property of the code
# rather than a property of two hand-maintained templates.
# ---------------------------------------------------------------------------

REFLECTOR_FIELD_ORDER: tuple[str, ...] = (
    "language",
    "verification_status",
    "problem_statement",
    "failed_program",
    "verifier_feedback",
)

# The oracle control is deliberately NOT field-order matched to the reflector
# arms: it is a known-informative positive control, not a matched placebo. Only
# its rendered payload block is held to parity.
ORACLE_FIELD_ORDER: tuple[str, ...] = REFLECTOR_FIELD_ORDER + ("hidden_test_stderr",)

REFLECTOR_PREAMBLE: str = (
    "You are the reflector. A repair attempt has been verified and did not pass."
)

REFLECTOR_INSTRUCTION_TEMPLATE: str = (
    "Write a post-failure reflection using exactly the schema below.\n"
    "Use exactly {bullets} bullet lines under each of the three headings.\n"
    "Do not add headings, preamble, commentary, or code.\n"
    "Observation:\n"
    "- <bullet>\n"
    "Principle:\n"
    "- <bullet>\n"
    "Revision plan:\n"
    "- <bullet>"
)

# ---------------------------------------------------------------------------
# Withheld material. The blind reflector sees a marker plus filler sized to the
# real field's token count, so the two prompts are token-matched without the
# blind prompt ever containing a task-derived character.
# ---------------------------------------------------------------------------

WITHHELD_TOKEN: str = "<withheld>"
WITHHELD_WORD: str = "withheld"
WITHHELD_TOKEN_COST: int = 3  # "<", "withheld", ">" under COUNT_TOKEN_PATTERN

ALLOWED_BLIND_LANGUAGES: frozenset[str] = frozenset({"Python"})
ALLOWED_BLIND_VERIFICATION_STATUS: frozenset[str] = frozenset({"failed"})

REDACTION_MASK: str = "<redacted>"

# Neutral filler vocabulary. Task-irrelevant by construction: none of these
# sentences names an algorithm, an API, an entity, or a failure mode.
# Kept deliberately short: these sentences set the structural floor below which
# a token-exact neutral block is impossible, and the floor must sit under the
# shortest real reflection the study will encounter.
NEUTRAL_SENTENCES: tuple[str, ...] = (
    "This block carries no information.",
    "The procedure here is unchanged.",
    "No material was supplied.",
    "The slot is held open.",
    "Nothing further is recorded.",
    "This position is reserved.",
)

PAD_WORDS: tuple[str, ...] = (
    "noted",
    "recorded",
    "reviewed",
    "considered",
    "unchanged",
    "reserved",
    "retained",
    "logged",
)

# ---------------------------------------------------------------------------
# Deterministic proxy tokenizer.
#
# The study's realized token counts must eventually be reported under the study
# model's own tokenizer. This proxy is what the builders use to *construct*
# matched payloads offline and what the tests assert against; every public entry
# point accepts a ``tokenizer`` override so the real tokenizer can be swapped in
# without touching the fitting logic.
# ---------------------------------------------------------------------------

COUNT_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")
WORD_TOKEN_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SENTENCE_PATTERN = re.compile(r"[^.!?]*[.!?]+|[^.!?]+$")

Tokenizer = Callable[[str], int]
ReflectorFn = Callable[[str, int], str]


def countTokens(text: str) -> int:
    """Deterministic proxy token count: word runs plus standalone punctuation."""
    return len(COUNT_TOKEN_PATTERN.findall(text))


def splitSentences(text: str) -> list[str]:
    """Split on sentence boundaries, preserving terminal punctuation."""
    return [part.strip() for part in SENTENCE_PATTERN.findall(text) if part.strip()]


def wordTokens(text: str) -> list[str]:
    """Lowercased identifier-like words, used only by the leak scanner."""
    return [match.lower() for match in WORD_TOKEN_PATTERN.findall(text)]


def withheldMaterial(token_count: int) -> str:
    """Deterministic withheld filler of exactly ``token_count`` proxy tokens.

    The first three tokens spell the ``<withheld>`` marker so the reflector can
    see that a field was suppressed rather than empty; the remainder repeats a
    single neutral word. Nothing here depends on the withheld content.
    """
    if token_count <= 0:
        return WITHHELD_TOKEN
    if token_count < WITHHELD_TOKEN_COST:
        return " ".join([WITHHELD_WORD] * token_count)
    remainder = token_count - WITHHELD_TOKEN_COST
    return " ".join([WITHHELD_TOKEN] + [WITHHELD_WORD] * remainder)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FailureTuple:
    """One failed attempt-1 repair target.

    This is the *unredacted* record. It is accepted by the real, donor, and
    oracle builders. It is never accepted by :func:`buildTaskBlindPlacebo`.

    ``reference_solution`` and ``hidden_test_stderr`` are held here for the
    leakage audit and the oracle control respectively. No reflector arm other
    than the oracle ever reads ``hidden_test_stderr``, and no arm at all reads
    ``reference_solution``.
    """

    problem_id: str
    problem_statement: str
    failed_program: str
    verifier_feedback: str
    reference_solution: str = ""
    hidden_test_stderr: str = ""
    language: str = "Python"
    verification_status: str = "failed"


@dataclass(frozen=True, slots=True)
class BlindReflectorInputs:
    """Everything the placebo reflector is permitted to receive. Nothing else.

    ``__slots__`` means no attribute outside this list can be attached, and the
    only string-valued fields are validated against small allowlists. There is
    therefore no representable value of this type that carries problem text,
    code, test names, values, exceptions, entity names, the real reflection, or
    a solution -- the invariant is enforced by the type, not by reviewer
    discipline.

    The three integer fields are the *token counts* of the withheld fields. A
    count is the only thing the placebo prompt needs in order to be
    token-matched to the real prompt.
    """

    language: str = "Python"
    verification_status: str = "failed"
    problem_statement_tokens: int = 0
    failed_program_tokens: int = 0
    verifier_feedback_tokens: int = 0

    def __post_init__(self) -> None:
        if self.language not in ALLOWED_BLIND_LANGUAGES:
            raise ValueError(
                f"language must be one of {sorted(ALLOWED_BLIND_LANGUAGES)}; got "
                f"{self.language!r}. The blind reflector accepts allowlisted "
                f"labels only, never free text."
            )
        if self.verification_status not in ALLOWED_BLIND_VERIFICATION_STATUS:
            raise ValueError(
                f"verification_status must be one of "
                f"{sorted(ALLOWED_BLIND_VERIFICATION_STATUS)}; got "
                f"{self.verification_status!r}."
            )
        for name in (
            "problem_statement_tokens",
            "failed_program_tokens",
            "verifier_feedback_tokens",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an int, got {type(value).__name__}")
            if value < 0:
                raise ValueError(f"{name} must be non-negative, got {value}")


BLIND_INPUT_FIELD_NAMES: frozenset[str] = frozenset(
    f.name for f in fields(BlindReflectorInputs)
)


def redactToBlind(
    failure: FailureTuple,
    *,
    tokenizer: Tokenizer = countTokens,
) -> BlindReflectorInputs:
    """The ONLY bridge from a failure tuple to the blind reflector's inputs.

    Reads three lengths and two allowlisted labels; discards everything else.
    The returned object cannot carry the discarded material.
    """
    return BlindReflectorInputs(
        language=failure.language,
        verification_status=failure.verification_status,
        problem_statement_tokens=tokenizer(failure.problem_statement),
        failed_program_tokens=tokenizer(failure.failed_program),
        verifier_feedback_tokens=tokenizer(failure.verifier_feedback),
    )


# ---------------------------------------------------------------------------
# Payload block
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PayloadBlock:
    """One rendered payload occupying the attempt-2 payload slot.

    ``defects`` is the honesty channel. Anything the builder had to adjust --
    a bullet count the model got wrong, a token target it could not reach on a
    sentence boundary -- is recorded here and surfaces in the parity record. It
    is never dropped.
    """

    arm: str
    text: str
    token_count: int
    bullet_counts: tuple[int, ...]
    prompt_slot_index: int
    header: str = PAYLOAD_HEADER
    delimiter: str = PAYLOAD_DELIMITER
    section_order: tuple[str, ...] = SCHEMA_SECTIONS
    sections: dict[str, tuple[str, ...]] = field(default_factory=dict)
    provenance: dict[str, object] = field(default_factory=dict)
    defects: tuple[str, ...] = ()
    reflector_prompt: str | None = None

    @property
    def header_digest(self) -> str:
        return hashlib.sha256(self.header.encode("utf-8")).hexdigest()

    @property
    def delimiter_digest(self) -> str:
        return hashlib.sha256(self.delimiter.encode("utf-8")).hexdigest()

    @property
    def text_digest(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def renderPayloadText(sections: Mapping[str, Sequence[str]]) -> str:
    """Render the fixed schema. Header, delimiters, and ordering are constants."""
    lines: list[str] = [PAYLOAD_HEADER, PAYLOAD_DELIMITER]
    for name in SCHEMA_SECTIONS:
        lines.append(f"{name}:")
        for bullet in sections.get(name, ()):
            lines.append(f"{BULLET_MARKER} {bullet}")
    lines.append(PAYLOAD_DELIMITER)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Schema parsing and bullet normalization
# ---------------------------------------------------------------------------

_SECTION_HEADING_PATTERN = re.compile(
    r"^\s*(observation|principle|revision\s+plan)\s*:\s*(.*)$", re.IGNORECASE
)
_BULLET_PATTERN = re.compile(r"^\s*[-*•]\s*(.+)$")

_CANONICAL_SECTION_BY_KEY: dict[str, str] = {
    "observation": "Observation",
    "principle": "Principle",
    "revisionplan": "Revision plan",
}


def parseSchemaSections(text: str) -> tuple[dict[str, list[str]], tuple[str, ...]]:
    """Parse reflector output into the fixed schema.

    Returns ``(sections, defects)``. Missing sections come back empty and are
    reported as a defect rather than quietly invented.
    """
    sections: dict[str, list[str]] = {name: [] for name in SCHEMA_SECTIONS}
    defects: list[str] = []
    current: str | None = None
    for raw_line in text.splitlines():
        heading = _SECTION_HEADING_PATTERN.match(raw_line)
        if heading is not None:
            key = re.sub(r"\s+", "", heading.group(1)).lower()
            current = _CANONICAL_SECTION_BY_KEY[key]
            trailing = heading.group(2).strip()
            if trailing:
                sections[current].append(trailing)
            continue
        if current is None:
            continue
        bullet = _BULLET_PATTERN.match(raw_line)
        if bullet is not None:
            sections[current].append(bullet.group(1).strip())
            continue
        stripped = raw_line.strip()
        if not stripped:
            continue
        if sections[current]:
            sections[current][-1] = f"{sections[current][-1]} {stripped}"
        else:
            sections[current].append(stripped)
    for name in SCHEMA_SECTIONS:
        if not sections[name]:
            defects.append(f"schema_section_missing:{name}")
    return sections, tuple(defects)


def normalizeBulletCounts(
    sections: Mapping[str, Sequence[str]],
    bullet_counts: Sequence[int],
) -> tuple[dict[str, list[str]], tuple[str, ...]]:
    """Force the parsed sections onto the target bullet shape.

    Item parity requires identical bullet counts across arms, and the output
    instruction asks every arm for the same count. When the model disobeys we
    reshape -- but the reshape is recorded as a defect so the matching audit
    reports it. This is adjustment-with-a-receipt, not silent repair.
    """
    if len(bullet_counts) != len(SCHEMA_SECTIONS):
        raise ValueError(
            f"bullet_counts must have {len(SCHEMA_SECTIONS)} entries, got "
            f"{len(bullet_counts)}"
        )
    out: dict[str, list[str]] = {}
    defects: list[str] = []
    for name, target in zip(SCHEMA_SECTIONS, bullet_counts):
        if target < 1:
            raise ValueError(f"bullet count for {name} must be >= 1, got {target}")
        bullets = [b.strip() for b in sections.get(name, ()) if b.strip()]
        if len(bullets) > target:
            merged = " ".join(bullets[target - 1 :])
            defects.append(f"bullet_count_merged:{name}:{len(bullets)}->{target}")
            bullets = bullets[: target - 1] + [merged]
        elif len(bullets) < target:
            defects.append(f"bullet_count_padded:{name}:{len(bullets)}->{target}")
            while len(bullets) < target:
                bullets.append(NEUTRAL_SENTENCES[len(bullets) % len(NEUTRAL_SENTENCES)])
        out[name] = bullets
    return out, tuple(defects)


# ---------------------------------------------------------------------------
# Sentence-boundary length fitting
# ---------------------------------------------------------------------------


def _padSentence(token_budget: int) -> str:
    """A neutral sentence of exactly ``token_budget`` proxy tokens."""
    if token_budget < 1:
        return ""
    if token_budget == 1:
        return PAD_WORDS[0]
    words = [PAD_WORDS[i % len(PAD_WORDS)] for i in range(token_budget - 1)]
    return " ".join(words) + "."


def _dropTrailingSentence(sections: dict[str, list[str]]) -> bool:
    """Drop the last sentence of the last multi-sentence bullet. Never empties one."""
    for name in reversed(SCHEMA_SECTIONS):
        bullets = sections.get(name)
        if not bullets:
            continue
        for index in range(len(bullets) - 1, -1, -1):
            parts = splitSentences(bullets[index])
            if len(parts) >= 2:
                bullets[index] = " ".join(parts[:-1])
                return True
    return False


def _appendPadSentence(sections: dict[str, list[str]], token_budget: int) -> bool:
    for name in reversed(SCHEMA_SECTIONS):
        bullets = sections.get(name)
        if bullets:
            bullets[-1] = f"{bullets[-1]} {_padSentence(token_budget)}".strip()
            return True
    return False


def fitSectionsToTarget(
    sections: dict[str, list[str]],
    target_tokens: int,
    *,
    tokenizer: Tokenizer = countTokens,
) -> tuple[dict[str, list[str]], tuple[str, ...]]:
    """Pad or truncate on sentence boundaries to ``target_tokens``.

    Truncation removes whole trailing sentences and refuses to empty a bullet,
    so a payload whose shortest legal form still exceeds the target overshoots.
    That overshoot is returned as a defect, never hidden by a mid-sentence cut.
    Bullet counts are invariant under this operation, so item parity survives
    token fitting.
    """
    defects: list[str] = []
    count = tokenizer(renderPayloadText(sections))
    while count > target_tokens:
        if not _dropTrailingSentence(sections):
            break
        count = tokenizer(renderPayloadText(sections))
    if count > target_tokens:
        defects.append(f"token_parity_overshoot:{count - target_tokens}")
        return sections, tuple(defects)
    if count < target_tokens:
        _appendPadSentence(sections, target_tokens - count)
        count = tokenizer(renderPayloadText(sections))
        if count != target_tokens:
            defects.append(f"token_parity_residual:{count - target_tokens}")
    return sections, tuple(defects)


# ---------------------------------------------------------------------------
# Reflector prompt construction
# ---------------------------------------------------------------------------


def _renderReflectorPrompt(
    field_values: Mapping[str, str],
    *,
    field_order: Sequence[str] = REFLECTOR_FIELD_ORDER,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
) -> str:
    lines: list[str] = [REFLECTOR_PREAMBLE, ""]
    for name in field_order:
        lines.append(f"{name}:")
        lines.append(field_values.get(name, ""))
        lines.append("")
    lines.append(REFLECTOR_INSTRUCTION_TEMPLATE.format(bullets=bullets_per_section))
    return "\n".join(lines)


def buildRealReflectorPrompt(
    failure: FailureTuple,
    *,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
) -> str:
    """The real reflector sees the problem, the failed program, and the feedback."""
    return _renderReflectorPrompt(
        {
            "language": failure.language,
            "verification_status": failure.verification_status,
            "problem_statement": failure.problem_statement,
            "failed_program": failure.failed_program,
            "verifier_feedback": failure.verifier_feedback,
        },
        bullets_per_section=bullets_per_section,
    )


def buildBlindReflectorPrompt(
    blind: BlindReflectorInputs,
    *,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
) -> str:
    """Identical schema, identical field order, token-matched withheld material."""
    if not isinstance(blind, BlindReflectorInputs):
        raise TypeError(
            "the task-blind reflector accepts BlindReflectorInputs only; got "
            f"{type(blind).__name__}. Use redactToBlind() -- passing a "
            "FailureTuple here would defeat the blind."
        )
    return _renderReflectorPrompt(
        {
            "language": blind.language,
            "verification_status": blind.verification_status,
            "problem_statement": withheldMaterial(blind.problem_statement_tokens),
            "failed_program": withheldMaterial(blind.failed_program_tokens),
            "verifier_feedback": withheldMaterial(blind.verifier_feedback_tokens),
        },
        bullets_per_section=bullets_per_section,
    )


def reflectorFieldOrderOf(prompt: str) -> tuple[str, ...]:
    """Recover the field-label sequence from a rendered reflector prompt."""
    labels: list[str] = []
    known = set(ORACLE_FIELD_ORDER)
    for line in prompt.splitlines():
        stripped = line.strip()
        if stripped.endswith(":"):
            candidate = stripped[:-1]
            if candidate in known:
                labels.append(candidate)
    return tuple(labels)


# ---------------------------------------------------------------------------
# Oracle redaction
# ---------------------------------------------------------------------------

_REDACTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?m)^(?P<keep>.*\bassert\b[^=<>!\n]*(?:==|!=|<=|>=|<|>)\s*).+$"),
    re.compile(r"(?m)^(?P<keep>\s*E?\s*AssertionError:\s*).+$"),
    re.compile(
        r"(?mi)^(?P<keep>\s*(?:expected|actual|got|result)\s*[:=]\s*).+$",
    ),
)


def redactAssertionValues(text: str) -> str:
    """Mask assertion values and expected outputs; keep the shape of the failure.

    Deterministic regex masking, so the redacted dose is reproducible from the
    full dose. This is what makes ORACLE-REDACTED a genuinely *lower* dose of the
    same information rather than a different signal.
    """
    redacted = text
    for pattern in _REDACTION_PATTERNS:
        redacted = pattern.sub(lambda m: f"{m.group('keep')}{REDACTION_MASK}", redacted)
    return redacted


# ---------------------------------------------------------------------------
# Backend resolution (lazy)
# ---------------------------------------------------------------------------


def _resolveReflector(generate: ReflectorFn | None) -> ReflectorFn:
    """Resolve the reflector backend lazily.

    Importing at call time keeps this module importable -- and testable -- with
    no backend installed and no model process running.
    """
    if generate is not None:
        return generate
    from pneuma_lab.placebo.backend import generate as backend_generate

    return backend_generate


# ---------------------------------------------------------------------------
# Block assembly
# ---------------------------------------------------------------------------


def _assembleBlock(
    *,
    arm: str,
    sections: dict[str, list[str]],
    prompt_slot_index: int,
    tokenizer: Tokenizer,
    provenance: Mapping[str, object],
    defects: Sequence[str],
    reflector_prompt: str | None,
) -> PayloadBlock:
    text = renderPayloadText(sections)
    if not text.strip():
        raise ValueError(
            f"{arm}: rendered payload is empty; a payload slot is never blank"
        )
    return PayloadBlock(
        arm=arm,
        text=text,
        token_count=tokenizer(text),
        bullet_counts=tuple(len(sections.get(n, ())) for n in SCHEMA_SECTIONS),
        prompt_slot_index=prompt_slot_index,
        sections={n: tuple(sections.get(n, ())) for n in SCHEMA_SECTIONS},
        provenance=dict(sorted(provenance.items())),
        defects=tuple(defects),
        reflector_prompt=reflector_prompt,
    )


def _buildFromReflector(
    *,
    arm: str,
    prompt: str,
    generate: ReflectorFn | None,
    seed: int,
    bullet_counts: Sequence[int],
    target_tokens: int | None,
    prompt_slot_index: int,
    tokenizer: Tokenizer,
    provenance: Mapping[str, object],
) -> PayloadBlock:
    reflector = _resolveReflector(generate)
    raw = reflector(prompt, seed)
    parsed, parse_defects = parseSchemaSections(raw)
    shaped, shape_defects = normalizeBulletCounts(parsed, bullet_counts)
    defects = list(parse_defects) + list(shape_defects)
    if target_tokens is not None:
        shaped, fit_defects = fitSectionsToTarget(
            shaped, target_tokens, tokenizer=tokenizer
        )
        defects.extend(fit_defects)
    return _assembleBlock(
        arm=arm,
        sections=shaped,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
        provenance=provenance,
        defects=defects,
        reflector_prompt=prompt,
    )


# ---------------------------------------------------------------------------
# The five builders
# ---------------------------------------------------------------------------


def buildRealReflection(
    failure: FailureTuple,
    *,
    generate: ReflectorFn | None = None,
    seed: int = 0,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    prompt_slot_index: int = DEFAULT_PROMPT_SLOT_INDEX,
    tokenizer: Tokenizer = countTokens,
    target_tokens: int | None = None,
) -> PayloadBlock:
    """Arm ``R3_REAL``. The reflector sees problem, failed program, and feedback.

    This payload *defines* the tuple's parity target: every other arm is fitted
    to its realized token count and bullet shape, so ``target_tokens`` is
    normally left at ``None``.
    """
    prompt = buildRealReflectorPrompt(failure, bullets_per_section=bullets_per_section)
    return _buildFromReflector(
        arm=ARM_R3_REAL,
        prompt=prompt,
        generate=generate,
        seed=seed,
        bullet_counts=[bullets_per_section] * len(SCHEMA_SECTIONS),
        target_tokens=target_tokens,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
        provenance={
            "task_blind": False,
            "donor_problem_id": None,
            "dose": None,
            "model_call": True,
            "saw_problem_statement": True,
            "saw_failed_program": True,
            "saw_verifier_feedback": True,
            "saw_hidden_test_stderr": False,
            "source_problem_id": failure.problem_id,
        },
    )


def buildTaskBlindPlacebo(
    blind: BlindReflectorInputs,
    *,
    generate: ReflectorFn | None = None,
    seed: int = 0,
    bullet_counts: Sequence[int] | None = None,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    target_tokens: int | None = None,
    prompt_slot_index: int = DEFAULT_PROMPT_SLOT_INDEX,
    tokenizer: Tokenizer = countTokens,
) -> PayloadBlock:
    """Arm ``P_TASK_BLIND`` -- **the primary placebo** (design doc section 9b).

    A task-blind *procedural* reflection: the same frozen reflector model, the
    same schema, the same field order, the same output instructions, the same
    decoding configuration, and every task-specific field replaced by
    deterministic token-count-matched withheld material.

    The parameter type is the enforcement. Passing a :class:`FailureTuple` --
    or a dict, or anything else that could carry problem text, code, test names,
    values, exceptions, entity names, the real reflection, or a solution --
    raises :class:`TypeError`. There is no keyword through which task content
    can reach this function.
    """
    if not isinstance(blind, BlindReflectorInputs):
        raise TypeError(
            "buildTaskBlindPlacebo accepts BlindReflectorInputs only; got "
            f"{type(blind).__name__}. The blind is structural: derive inputs with "
            "redactToBlind(), which keeps token counts and discards content."
        )
    prompt = buildBlindReflectorPrompt(blind, bullets_per_section=bullets_per_section)
    counts = (
        list(bullet_counts)
        if bullet_counts is not None
        else [bullets_per_section] * len(SCHEMA_SECTIONS)
    )
    return _buildFromReflector(
        arm=ARM_P_TASK_BLIND,
        prompt=prompt,
        generate=generate,
        seed=seed,
        bullet_counts=counts,
        target_tokens=target_tokens,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
        provenance={
            "task_blind": True,
            "donor_problem_id": None,
            "dose": None,
            "model_call": True,
            "saw_problem_statement": False,
            "saw_failed_program": False,
            "saw_verifier_feedback": False,
            "saw_hidden_test_stderr": False,
            "withheld_token_counts": (
                blind.problem_statement_tokens,
                blind.failed_program_tokens,
                blind.verifier_feedback_tokens,
            ),
        },
    )


def buildDonorReflection(
    donor: FailureTuple,
    *,
    target_problem_id: str,
    arm: str = ARM_R1_PLACEBO_RANDOM,
    generate: ReflectorFn | None = None,
    seed: int = 0,
    bullet_counts: Sequence[int] | None = None,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    target_tokens: int | None = None,
    prompt_slot_index: int = DEFAULT_PROMPT_SLOT_INDEX,
    tokenizer: Tokenizer = countTokens,
) -> PayloadBlock:
    """Arms ``R1_PLACEBO_RANDOM`` / ``R2_PLACEBO_MATCHED`` -- a SEPARATE ARM.

    A genuine reflection the same model wrote about a **different** failed
    problem.

    **This is not the primary placebo.** A donor reflection carries concrete but
    irrelevant or false diagnostic advice, so the donor-minus-real contrast
    estimates *content versus misinformation*, not *content versus nothing*.
    Section 9b of the design assigns the primary-placebo role to
    :func:`buildTaskBlindPlacebo`; the donor arms are retained only because the
    misinformation contrast is independently interesting, and their estimates
    must be labelled as such wherever they are reported.

    Self-donation is refused unconditionally.
    """
    if arm not in (ARM_R1_PLACEBO_RANDOM, ARM_R2_PLACEBO_MATCHED):
        raise ValueError(
            f"donor reflections belong to the donor arms only, got arm={arm!r}"
        )
    if donor.problem_id == target_problem_id:
        raise ValueError(
            f"self-donation refused: donor and target are both "
            f"{target_problem_id!r}. A donor arm that can self-donate is not a "
            f"donor arm."
        )
    prompt = buildRealReflectorPrompt(donor, bullets_per_section=bullets_per_section)
    counts = (
        list(bullet_counts)
        if bullet_counts is not None
        else [bullets_per_section] * len(SCHEMA_SECTIONS)
    )
    return _buildFromReflector(
        arm=arm,
        prompt=prompt,
        generate=generate,
        seed=seed,
        bullet_counts=counts,
        target_tokens=target_tokens,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
        provenance={
            "task_blind": False,
            "donor_problem_id": donor.problem_id,
            "target_problem_id": target_problem_id,
            "dose": None,
            "model_call": True,
            "saw_problem_statement": True,
            "saw_failed_program": True,
            "saw_verifier_feedback": True,
            "saw_hidden_test_stderr": False,
            "estimates": "content_vs_misinformation",
        },
    )


def _neutralSections(
    counts: Sequence[int], sentences: Sequence[str] = NEUTRAL_SENTENCES
) -> dict[str, list[str]]:
    """Lay a bank of inert sentences into the fixed schema.

    ``sentences`` is a parameter so that ``surface_floor.py`` can build lexically
    distinct but semantically identical variants of the same inert block. It
    defaults to the committed bank, so every existing caller is unaffected.
    """
    if not sentences:
        raise ValueError("sentence bank must not be empty")
    sections: dict[str, list[str]] = {}
    cursor = 0
    for name, count in zip(SCHEMA_SECTIONS, counts):
        if count < 1:
            raise ValueError(f"bullet count for {name} must be >= 1, got {count}")
        bullets: list[str] = []
        for _ in range(count):
            bullets.append(sentences[cursor % len(sentences)])
            cursor += 1
        sections[name] = bullets
    return sections


def neutralFillerFloorTokens(
    *,
    bullet_counts: Sequence[int] | None = None,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    tokenizer: Tokenizer = countTokens,
) -> int:
    """Shortest token-exact neutral block for a given bullet shape.

    Below this, ``R0_NONE`` cannot be both token-exact and item-parity matched,
    which is a design constraint worth surfacing rather than a bug to paper
    over: it bounds how short a real reflection the instrument can match.
    """
    counts = (
        list(bullet_counts)
        if bullet_counts is not None
        else [bullets_per_section] * len(SCHEMA_SECTIONS)
    )
    return tokenizer(renderPayloadText(_neutralSections(counts)))


def buildNeutralFiller(
    *,
    target_tokens: int,
    bullet_counts: Sequence[int] | None = None,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    prompt_slot_index: int = DEFAULT_PROMPT_SLOT_INDEX,
    tokenizer: Tokenizer = countTokens,
    sentences: Sequence[str] = NEUTRAL_SENTENCES,
    arm: str = ARM_R0_NONE,
) -> PayloadBlock:
    """Arm ``R0_NONE`` -- a LENGTH-MATCHED NEUTRAL BLOCK, never an empty string.

    An empty payload slot shortens the attempt-2 prompt and removes the
    structural cue that a helper exists, so it is itself a confound: the
    resulting contrast would mix content, length, and format. ``R0_NONE``
    therefore carries task-irrelevant neutral prose that is token-exact to the
    tuple's real payload and identical to it in header, delimiters, section
    order, bullet counts, and prompt position.

    No model call happens here. The real reflection is still generated and
    discarded by the runner so that per-arm call counts match; that is call
    parity, and it is the runner's obligation, not this builder's.
    """
    counts = (
        list(bullet_counts)
        if bullet_counts is not None
        else [bullets_per_section] * len(SCHEMA_SECTIONS)
    )
    floor_sections = _neutralSections(counts, sentences)
    while tokenizer(renderPayloadText(floor_sections)) > target_tokens:
        if not _dropTrailingSentence(floor_sections):
            break
    floor_tokens = tokenizer(renderPayloadText(floor_sections))
    if floor_tokens > target_tokens:
        raise ValueError(
            f"target_tokens={target_tokens} is below the structural floor of the "
            f"neutral filler ({floor_tokens} tokens for bullet shape "
            f"{tuple(counts)}). Token-exactness is contractual for R0_NONE, so "
            f"this is raised rather than silently approximated."
        )

    fitted, defects = fitSectionsToTarget(
        floor_sections, target_tokens, tokenizer=tokenizer
    )
    block = _assembleBlock(
        arm=arm,
        sections=fitted,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
        provenance={
            "task_blind": True,
            "donor_problem_id": None,
            "dose": None,
            "model_call": False,
            "saw_problem_statement": False,
            "saw_failed_program": False,
            "saw_verifier_feedback": False,
            "saw_hidden_test_stderr": False,
            "neutral_filler": True,
            "target_tokens": target_tokens,
        },
        defects=defects,
        reflector_prompt=None,
    )
    if block.token_count != target_tokens:
        raise ValueError(
            f"neutral filler missed its token target: {block.token_count} != "
            f"{target_tokens}. R0_NONE must be token-exact."
        )
    return block


def buildOracleReflection(
    failure: FailureTuple,
    *,
    dose: str,
    generate: ReflectorFn | None = None,
    seed: int = 0,
    bullet_counts: Sequence[int] | None = None,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    target_tokens: int | None = None,
    prompt_slot_index: int = DEFAULT_PROMPT_SLOT_INDEX,
    tokenizer: Tokenizer = countTokens,
) -> PayloadBlock:
    """Arms ``C1_ORACLE_FULL`` / ``C2_ORACLE_REDACTED`` -- the graded positive control.

    ``full`` generates the reflection with the hidden failing-test stderr
    visible. ``redacted`` shows the same stderr with assertion values and
    expected outputs masked, i.e. the same signal at a lower dose.

    Two doses rather than one pass/fail gate is what distinguishes an all-null
    result from a broken payload pipeline, and it lets the paper report the
    minimum content dose the instrument resolves. If ``C1 - R0`` does not clear
    the preregistered sensitivity margin, the injection path is broken -- that
    finding is about the harness, not about content.
    """
    if dose not in ORACLE_DOSES:
        raise ValueError(f"dose must be one of {ORACLE_DOSES}, got {dose!r}")
    if dose == ORACLE_DOSE_FULL:
        arm = ARM_C1_ORACLE_FULL
        stderr = failure.hidden_test_stderr
    else:
        arm = ARM_C2_ORACLE_REDACTED
        stderr = redactAssertionValues(failure.hidden_test_stderr)
    prompt = _renderReflectorPrompt(
        {
            "language": failure.language,
            "verification_status": failure.verification_status,
            "problem_statement": failure.problem_statement,
            "failed_program": failure.failed_program,
            "verifier_feedback": failure.verifier_feedback,
            "hidden_test_stderr": stderr,
        },
        field_order=ORACLE_FIELD_ORDER,
        bullets_per_section=bullets_per_section,
    )
    counts = (
        list(bullet_counts)
        if bullet_counts is not None
        else [bullets_per_section] * len(SCHEMA_SECTIONS)
    )
    return _buildFromReflector(
        arm=arm,
        prompt=prompt,
        generate=generate,
        seed=seed,
        bullet_counts=counts,
        target_tokens=target_tokens,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
        provenance={
            "task_blind": False,
            "donor_problem_id": None,
            "dose": dose,
            "model_call": True,
            "saw_problem_statement": True,
            "saw_failed_program": True,
            "saw_verifier_feedback": True,
            "saw_hidden_test_stderr": True,
            "positive_control": True,
            "source_problem_id": failure.problem_id,
        },
    )


class ResamplePreconditionError(ValueError):
    """The RESAMPLE arm was configured where a second draw cannot differ."""


def assertResampleIsMeaningful(
    *, temperature: float, top_p: float = 1.0, seeds: Sequence[int] = ()
) -> None:
    """Refuse a RESAMPLE arm that cannot possibly measure anything.

    The arm exists to separate the nonspecific-helper effect from "the arm got
    an extra draw." That separation requires the extra draw to be able to differ
    from the first. Under greedy decoding it cannot: temperature zero makes a
    second generation on the same prompt byte-identical, and the seed is inert
    because nothing is sampled.

    Raising here rather than warning is deliberate. A silently-included RESAMPLE
    arm at temperature zero produces a clean-looking null that would be read as
    "extra compute does not matter" when it actually reads "we ran the same
    prompt twice and got the same string."
    """
    if temperature <= 0.0:
        raise ResamplePreconditionError(
            f"RESAMPLE requires stochastic decoding; temperature={temperature} "
            "makes the second draw byte-identical to the first, so the arm "
            "measures nothing. Either raise the temperature for the resample "
            "track or drop the arm and state that the nonspecific-helper term "
            "is not separated from extra sampled compute."
        )
    if top_p <= 0.0:
        raise ResamplePreconditionError(
            f"top_p={top_p} collapses the sampling distribution to a point"
        )
    distinct = len({int(s) for s in seeds})
    if seeds and distinct < 2:
        raise ResamplePreconditionError(
            f"RESAMPLE needs at least two distinct seeds, got {distinct}"
        )


def buildPayloadSet(
    failure: FailureTuple,
    *,
    donor_random: FailureTuple | None = None,
    donor_matched: FailureTuple | None = None,
    generate: ReflectorFn | None = None,
    seed: int = 0,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    prompt_slot_index: int = DEFAULT_PROMPT_SLOT_INDEX,
    tokenizer: Tokenizer = countTokens,
    include_oracle: bool = True,
    include_redacted_dose: bool = False,
    include_resample: bool = True,
) -> dict[str, PayloadBlock]:
    """Build every arm for one failure tuple, parity-targeted on ``R3_REAL``.

    The real payload is built first and its realized token count and bullet
    shape become the target for every other arm, which is what makes the parity
    target a property of the tuple rather than a global constant.
    """
    real = buildRealReflection(
        failure,
        generate=generate,
        seed=seed,
        bullets_per_section=bullets_per_section,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
    )
    target_tokens = real.token_count
    counts = list(real.bullet_counts)
    payloads: dict[str, PayloadBlock] = {ARM_R3_REAL: real}

    payloads[ARM_P_TASK_BLIND] = buildTaskBlindPlacebo(
        redactToBlind(failure, tokenizer=tokenizer),
        generate=generate,
        seed=seed,
        bullet_counts=counts,
        bullets_per_section=bullets_per_section,
        target_tokens=target_tokens,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
    )
    payloads[ARM_R0_NONE] = buildNeutralFiller(
        target_tokens=target_tokens,
        bullet_counts=counts,
        bullets_per_section=bullets_per_section,
        prompt_slot_index=prompt_slot_index,
        tokenizer=tokenizer,
    )
    for donor, arm in (
        (donor_random, ARM_R1_PLACEBO_RANDOM),
        (donor_matched, ARM_R2_PLACEBO_MATCHED),
    ):
        if donor is None:
            continue
        payloads[arm] = buildDonorReflection(
            donor,
            target_problem_id=failure.problem_id,
            arm=arm,
            generate=generate,
            seed=seed,
            bullet_counts=counts,
            bullets_per_section=bullets_per_section,
            target_tokens=target_tokens,
            prompt_slot_index=prompt_slot_index,
            tokenizer=tokenizer,
        )
    if include_resample:
        payloads[ARM_S_RESAMPLE] = buildNeutralFiller(
            target_tokens=target_tokens,
            bullet_counts=counts,
            bullets_per_section=bullets_per_section,
            prompt_slot_index=prompt_slot_index,
            tokenizer=tokenizer,
            arm=ARM_S_RESAMPLE,
        )
        payloads[ARM_S_RESAMPLE].provenance.update(
            {
                "requires_independent_resample": True,
                "resample_index": 1,
                "neutral_filler": True,
            }
        )

    doses = ORACLE_DOSES if include_redacted_dose else CONFIRMATORY_ORACLE_DOSES
    if include_oracle:
        for dose in doses:
            block = buildOracleReflection(
                failure,
                dose=dose,
                generate=generate,
                seed=seed,
                bullet_counts=counts,
                bullets_per_section=bullets_per_section,
                target_tokens=target_tokens,
                prompt_slot_index=prompt_slot_index,
                tokenizer=tokenizer,
            )
            payloads[block.arm] = block
    return payloads


# ---------------------------------------------------------------------------
# Parity asserters -- validity gates, measured per item and reported
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenParityRecord:
    """Realized token parity for one tuple. Reported, not repaired."""

    reference_arm: str
    reference_tokens: int
    tolerance: int
    realized: dict[str, int]
    deltas: dict[str, int]
    median_absolute_delta: float
    max_absolute_delta: int
    placebo_arms: tuple[str, ...]
    placebo_absolute_deltas: dict[str, int]
    placebo_delta_spread: int
    placebo_tolerance_symmetric: bool
    passed: bool
    defects: tuple[str, ...]


@dataclass(frozen=True)
class StructuralParityRecord:
    """Byte-identical header, delimiters, ordering, absolute prompt position."""

    header_digests: dict[str, str]
    delimiter_digests: dict[str, str]
    section_orders: dict[str, tuple[str, ...]]
    prompt_slot_indices: dict[str, int]
    passed: bool
    defects: tuple[str, ...]


@dataclass(frozen=True)
class ItemParityRecord:
    """Identical bullet counts across arms."""

    bullet_counts: dict[str, tuple[int, ...]]
    reference_arm: str
    reference_counts: tuple[int, ...]
    passed: bool
    defects: tuple[str, ...]


@dataclass(frozen=True)
class BlindnessRecord:
    """Evidence that the task-blind arm never saw task-specific material.

    ``prompt_leak_terms`` is the gate: the blind reflector prompt is built from
    integers and allowlisted labels, so any task term appearing in it is a
    pipeline defect. ``payload_overlap_terms`` is informational only -- generic
    procedural advice can coincidentally reuse a common word, and treating that
    as a leak would produce false defects.
    """

    arm: str
    prompt_leak_terms: tuple[str, ...]
    payload_overlap_terms: tuple[str, ...]
    passed: bool
    defects: tuple[str, ...]


@dataclass(frozen=True)
class ParityRecord:
    """One row of the matching-audit table."""

    problem_id: str
    seed: int
    arms: tuple[str, ...]
    token: TokenParityRecord
    structural: StructuralParityRecord
    item: ItemParityRecord
    blindness: BlindnessRecord | None
    passed: bool
    defects: tuple[str, ...]

    def toRow(self) -> dict[str, object]:
        """Flatten to a single audit-table row. Every defect is carried through."""
        return {
            "problem_id": self.problem_id,
            "seed": self.seed,
            "arms": ",".join(self.arms),
            "reference_arm": self.token.reference_arm,
            "reference_tokens": self.token.reference_tokens,
            "token_tolerance": self.token.tolerance,
            "token_median_abs_delta": self.token.median_absolute_delta,
            "token_max_abs_delta": self.token.max_absolute_delta,
            "placebo_delta_spread": self.token.placebo_delta_spread,
            "placebo_tolerance_symmetric": self.token.placebo_tolerance_symmetric,
            "token_parity_passed": self.token.passed,
            "structural_parity_passed": self.structural.passed,
            "item_parity_passed": self.item.passed,
            "task_blind_passed": None
            if self.blindness is None
            else self.blindness.passed,
            "parity_passed": self.passed,
            "defect_count": len(self.defects),
            "defects": ";".join(self.defects),
        }


def assertTokenParity(
    payloads: Mapping[str, PayloadBlock],
    *,
    reference_arm: str = REFERENCE_ARM,
    tolerance: int = TOKEN_PARITY_TOLERANCE,
    placebo_arms: Sequence[str] = PLACEBO_ARMS,
) -> TokenParityRecord:
    """Measure realized token parity against the tuple's REAL payload.

    Returns the realized distribution rather than raising, because the design
    treats a parity failure as a reported defect: a run that silently repaired
    or aborted here would erase the very quantity section 6 requires be
    published (realized deltas and their spread).

    Every placebo arm is scored under the SAME ``tolerance``; the record carries
    ``placebo_tolerance_symmetric`` as a receipt of that, and
    ``placebo_delta_spread`` so an asymmetry in *realized* matching is visible
    even when both arms individually pass.
    """
    if reference_arm not in payloads:
        raise KeyError(
            f"token parity is defined against {reference_arm!r}, which is absent "
            f"from the payload set {sorted(payloads)}"
        )
    reference_tokens = payloads[reference_arm].token_count
    realized = {arm: block.token_count for arm, block in payloads.items()}
    deltas = {arm: value - reference_tokens for arm, value in realized.items()}
    compared = [abs(d) for arm, d in deltas.items() if arm != reference_arm]
    median_abs = float(statistics.median(compared)) if compared else 0.0
    max_abs = max(compared) if compared else 0

    present_placebos = tuple(arm for arm in placebo_arms if arm in payloads)
    placebo_abs = {arm: abs(deltas[arm]) for arm in present_placebos}
    spread = (
        (max(placebo_abs.values()) - min(placebo_abs.values())) if placebo_abs else 0
    )

    defects: list[str] = []
    for arm, value in deltas.items():
        if arm == reference_arm:
            continue
        if abs(value) > tolerance:
            defects.append(f"token_parity_exceeded:{arm}:{value:+d}")
    if median_abs > tolerance:
        defects.append(f"token_parity_median_exceeded:{median_abs}")
    for arm, block in payloads.items():
        for defect in block.defects:
            if defect.startswith("token_parity_"):
                defects.append(f"{arm}:{defect}")

    return TokenParityRecord(
        reference_arm=reference_arm,
        reference_tokens=reference_tokens,
        tolerance=tolerance,
        realized=realized,
        deltas=deltas,
        median_absolute_delta=median_abs,
        max_absolute_delta=max_abs,
        placebo_arms=present_placebos,
        placebo_absolute_deltas=placebo_abs,
        placebo_delta_spread=spread,
        placebo_tolerance_symmetric=True,
        passed=not defects,
        defects=tuple(defects),
    )


def assertStructuralParity(
    payloads: Mapping[str, PayloadBlock],
    *,
    reference_arm: str = REFERENCE_ARM,
) -> StructuralParityRecord:
    """Byte-identical header and delimiters, identical ordering and slot index."""
    if reference_arm not in payloads:
        raise KeyError(f"{reference_arm!r} absent from payload set {sorted(payloads)}")
    header_digests = {arm: block.header_digest for arm, block in payloads.items()}
    delimiter_digests = {arm: block.delimiter_digest for arm, block in payloads.items()}
    section_orders = {
        arm: tuple(block.section_order) for arm, block in payloads.items()
    }
    slots = {arm: block.prompt_slot_index for arm, block in payloads.items()}

    reference = payloads[reference_arm]
    defects: list[str] = []
    for arm, block in payloads.items():
        if block.header != reference.header:
            defects.append(f"header_mismatch:{arm}")
        if block.delimiter != reference.delimiter:
            defects.append(f"delimiter_mismatch:{arm}")
        if tuple(block.section_order) != tuple(reference.section_order):
            defects.append(f"section_order_mismatch:{arm}")
        if tuple(block.section_order) != SCHEMA_SECTIONS:
            defects.append(f"section_order_not_canonical:{arm}")
        if block.prompt_slot_index != reference.prompt_slot_index:
            defects.append(f"prompt_slot_mismatch:{arm}")
        if not block.text.startswith(f"{PAYLOAD_HEADER}\n{PAYLOAD_DELIMITER}\n"):
            defects.append(f"header_not_at_block_start:{arm}")
        if not block.text.endswith(f"{PAYLOAD_DELIMITER}\n"):
            defects.append(f"delimiter_not_at_block_end:{arm}")
    return StructuralParityRecord(
        header_digests=header_digests,
        delimiter_digests=delimiter_digests,
        section_orders=section_orders,
        prompt_slot_indices=slots,
        passed=not defects,
        defects=tuple(defects),
    )


def assertItemParity(
    payloads: Mapping[str, PayloadBlock],
    *,
    reference_arm: str = REFERENCE_ARM,
) -> ItemParityRecord:
    """Identical bullet counts. Builder-side reshapes surface here as defects."""
    if reference_arm not in payloads:
        raise KeyError(f"{reference_arm!r} absent from payload set {sorted(payloads)}")
    reference_counts = tuple(payloads[reference_arm].bullet_counts)
    counts = {arm: tuple(block.bullet_counts) for arm, block in payloads.items()}
    defects: list[str] = []
    for arm, value in counts.items():
        if value != reference_counts:
            defects.append(f"item_parity_mismatch:{arm}:{value}!={reference_counts}")
    for arm, block in payloads.items():
        for defect in block.defects:
            if defect.startswith("bullet_count_") or defect.startswith(
                "schema_section_"
            ):
                defects.append(f"{arm}:{defect}")
    return ItemParityRecord(
        bullet_counts=counts,
        reference_arm=reference_arm,
        reference_counts=reference_counts,
        passed=not defects,
        defects=tuple(defects),
    )


def blindTemplateVocabulary(
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
) -> frozenset[str]:
    """Every word the blind reflector prompt may legitimately contain."""
    skeleton = _renderReflectorPrompt(
        {name: "" for name in REFLECTOR_FIELD_ORDER},
        bullets_per_section=bullets_per_section,
    )
    vocabulary = set(wordTokens(skeleton))
    vocabulary.update(wordTokens(" ".join(sorted(ALLOWED_BLIND_LANGUAGES))))
    vocabulary.update(wordTokens(" ".join(sorted(ALLOWED_BLIND_VERIFICATION_STATUS))))
    vocabulary.update(wordTokens(WITHHELD_TOKEN))
    vocabulary.add(WITHHELD_WORD)
    vocabulary.update(PAD_WORDS)
    return frozenset(vocabulary)


def assertTaskBlindness(
    block: PayloadBlock,
    failure: FailureTuple,
    *,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    minimum_term_length: int = 3,
) -> BlindnessRecord:
    """Scan the blind arm for any term traceable to the target's task material.

    The prompt scan is the gate. It compares the blind reflector prompt against
    the fixed template vocabulary, so *any* word not accounted for by the
    template is flagged -- including one that merely coincides with a task term.
    Because the blind prompt is generated from integers and allowlisted labels,
    a clean pipeline yields the empty set.
    """
    vocabulary = blindTemplateVocabulary(bullets_per_section)
    task_material = " ".join(
        (
            failure.problem_statement,
            failure.failed_program,
            failure.verifier_feedback,
            failure.reference_solution,
            failure.hidden_test_stderr,
        )
    )
    task_terms = {t for t in wordTokens(task_material) if len(t) >= minimum_term_length}

    prompt_terms = set(wordTokens(block.reflector_prompt or ""))
    prompt_leaks = sorted((prompt_terms & task_terms) - vocabulary)
    payload_overlap = sorted(set(wordTokens(block.text)) & task_terms - vocabulary)

    defects = [f"task_blind_prompt_leak:{term}" for term in prompt_leaks]
    if block.provenance.get("task_blind") is not True:
        defects.append("task_blind_provenance_missing")
    for key in (
        "saw_problem_statement",
        "saw_failed_program",
        "saw_verifier_feedback",
        "saw_hidden_test_stderr",
    ):
        if block.provenance.get(key) is not False:
            defects.append(f"task_blind_provenance_violation:{key}")
    return BlindnessRecord(
        arm=block.arm,
        prompt_leak_terms=tuple(prompt_leaks),
        payload_overlap_terms=tuple(payload_overlap),
        passed=not defects,
        defects=tuple(defects),
    )


def buildParityRecord(
    payloads: Mapping[str, PayloadBlock],
    *,
    problem_id: str,
    seed: int = 0,
    failure: FailureTuple | None = None,
    reference_arm: str = REFERENCE_ARM,
    tolerance: int = TOKEN_PARITY_TOLERANCE,
    placebo_arms: Sequence[str] = PLACEBO_ARMS,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
) -> ParityRecord:
    """Assemble the per-item parity record for the matching-audit table."""
    token = assertTokenParity(
        payloads,
        reference_arm=reference_arm,
        tolerance=tolerance,
        placebo_arms=placebo_arms,
    )
    structural = assertStructuralParity(payloads, reference_arm=reference_arm)
    item = assertItemParity(payloads, reference_arm=reference_arm)
    blindness: BlindnessRecord | None = None
    if failure is not None and ARM_P_TASK_BLIND in payloads:
        blindness = assertTaskBlindness(
            payloads[ARM_P_TASK_BLIND],
            failure,
            bullets_per_section=bullets_per_section,
        )
    defects = list(token.defects) + list(structural.defects) + list(item.defects)
    if blindness is not None:
        defects.extend(blindness.defects)
    return ParityRecord(
        problem_id=problem_id,
        seed=seed,
        arms=tuple(arm for arm in ARM_ORDER_ALL if arm in payloads),
        token=token,
        structural=structural,
        item=item,
        blindness=blindness,
        passed=not defects,
        defects=tuple(defects),
    )
