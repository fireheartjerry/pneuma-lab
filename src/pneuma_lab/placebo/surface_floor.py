"""The prompt-perturbation noise floor: K inert payloads, one meaning, K surfaces.

Design source: ``docs/research/neurips-2026-workshop/25-placebo-selfreport-design.md``
section 11b. This closes the hole that makes a deterministic placebo contrast
uninterpretable.

The problem, stated exactly. Under greedy decoding a single changed token sends
generation down a different path. Arms in this study differ by construction in
the text occupying the payload slot. So when the placebo arm scores differently
from the no-payload arm, two explanations are observationally identical:

    (a) the generic helper content did something, or
    (b) the prompt changed and the decode rerouted.

No amount of care in writing the placebo separates them, because the placebo IS
a prompt change. The only way to separate them is to measure how far the outcome
moves under prompt changes that carry no information at all, and then require a
claimed effect to clear that floor.

That is what this module builds. Every variant here is:

    * **semantically identical** -- each bank says the same six inert things in
      different words, none of which refers to any task, program, or test;
    * **structurally identical** -- same header, delimiters, section order,
      bullet counts, prompt-slot index, and token count as every other arm;
    * **lexically distinct** -- the bullet prose shares as few content words as
      possible across banks, which is the whole point and is asserted, not hoped
      for.

The spread of the outcome across these variants is the **floor**. An arm
difference smaller than the floor is not evidence of anything, and this study
reports the floor next to every contrast rather than after a reviewer asks.

Nothing here calls a model. Distinctness is measured, and a violation is
returned as a record rather than raised, on the same principle as the parity
asserters in ``blocks.py``: a defect belongs in the audit table, not in an
exception that tempts a caller to widen the tolerance.
"""

from __future__ import annotations

import itertools
import re
from collections.abc import Sequence
from dataclasses import dataclass

from pneuma_lab.placebo.blocks import (
    DEFAULT_BULLETS_PER_SECTION,
    DEFAULT_PROMPT_SLOT_INDEX,
    NEUTRAL_SENTENCES,
    PAD_WORDS,
    SCHEMA_SECTIONS,
    PayloadBlock,
    Tokenizer,
    buildNeutralFiller,
    countTokens,
)

# ---------------------------------------------------------------------------
# Arm identifiers
# ---------------------------------------------------------------------------

ARM_SURFACE_PREFIX: str = "N_SURFACE_"


def surfaceArmId(index: int) -> str:
    return f"{ARM_SURFACE_PREFIX}{index:02d}"


# ---------------------------------------------------------------------------
# Banks
# ---------------------------------------------------------------------------

# Bank 0 is the committed `NEUTRAL_SENTENCES`, so the study's own R0_NONE prose
# sits INSIDE its own noise floor rather than being privileged as the reference.
# Each later bank restates the same six propositions with as little shared
# vocabulary as English comfortably allows.
SURFACE_BANKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("committed", NEUTRAL_SENTENCES),
    (
        "absent",
        (
            "No content is present in this section.",
            "The method above remains as before.",
            "Nothing was provided here.",
            "The field stays empty.",
            "There is no additional entry.",
            "This space is set aside.",
        ),
    ),
    (
        "vacant",
        (
            "This area holds no data.",
            "The steps stay exactly the same.",
            "No input arrived for this part.",
            "The placeholder remains vacant.",
            "No further detail exists.",
            "This region has been allocated.",
        ),
    ),
    (
        "empty",
        (
            "Zero information appears below.",
            "The routine is not altered.",
            "Nothing has been contributed.",
            "The opening is preserved.",
            "No extra note follows.",
            "This entry is claimed.",
        ),
    ),
    (
        "blank",
        (
            "There is nothing informative here.",
            "The approach continues unmodified.",
            "No submission was received.",
            "The gap is maintained.",
            "Nothing else has been logged.",
            "This slot is designated.",
        ),
    ),
    (
        "void",
        (
            "No knowledge is conveyed in this text.",
            "The sequence proceeds without change.",
            "Nothing came through for this item.",
            "The blank is kept.",
            "No supplementary record is present.",
            "This location is booked.",
        ),
    ),
)

DEFAULT_VARIANT_COUNT: int = len(SURFACE_BANKS)

# Overlap above this between two banks' bullet prose means the variants are not
# meaningfully different surfaces and the floor they measure is understated.
MAX_LEXICAL_OVERLAP: float = 0.34

# Above this share of shared padding, the variants differ over too little of
# their surface for the floor they measure to be anything but a lower bound.
MAX_SHARED_PAD_FRACTION: float = 0.40

# Words carried by the schema itself or by any inert statement of "nothing here".
# Excluded from the overlap measure, because every bank must contain some of them
# and counting them would make lexically disjoint banks look similar.
_STRUCTURAL_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "below",
        "by",
        "for",
        "from",
        "has",
        "have",
        "here",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "part",
        "that",
        "the",
        "there",
        "this",
        "to",
        "was",
        "were",
        "will",
        "with",
    }
)

_WORD_RE = re.compile(r"[a-z]+")


# ---------------------------------------------------------------------------
# Distinctness measurement
# ---------------------------------------------------------------------------


def contentWords(block: PayloadBlock) -> frozenset[str]:
    """Content vocabulary of a block's BULLET PROSE only.

    Three vocabularies are excluded because every arm carries them **by
    contract**, so counting them would make lexically disjoint banks look
    similar: the header and delimiter, the schema section names, and the
    ``PAD_WORDS`` that ``fitSectionsToTarget`` appends to reach token-exactness.

    The padding exclusion is not a convenience. Padding is shared across banks by
    construction and grows as a share of the block at longer token targets, which
    is why :func:`assertSurfaceDistinctness` reports ``shared_pad_fraction``
    separately: the banks can be disjoint while the rendered blocks are mostly
    identical scaffolding, and a reader is entitled to see that rather than have
    to infer it.
    """
    words: set[str] = set()
    for bullets in block.sections.values():
        for bullet in bullets:
            words.update(_WORD_RE.findall(bullet.lower()))
    section_words = {
        w for name in SCHEMA_SECTIONS for w in _WORD_RE.findall(name.lower())
    }
    return frozenset(words - _STRUCTURAL_WORDS - section_words - set(PAD_WORDS))


def sharedPadFraction(block: PayloadBlock) -> float:
    """Share of a block's bullet words drawn from the shared padding vocabulary.

    A high value means the variants differ over only a small part of their
    surface, so any floor measured from them is a **lower bound** on true
    perturbation sensitivity.
    """
    total = 0
    padded = 0
    pad = set(PAD_WORDS)
    for bullets in block.sections.values():
        for bullet in bullets:
            for word in _WORD_RE.findall(bullet.lower()):
                total += 1
                if word in pad:
                    padded += 1
    return (padded / total) if total else 0.0


def lexicalOverlap(left: PayloadBlock, right: PayloadBlock) -> float:
    """Jaccard similarity of two blocks' content vocabulary."""
    a = contentWords(left)
    b = contentWords(right)
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


@dataclass(frozen=True)
class SurfaceFloorRecord:
    """Measured properties of one variant set. Defects are reported, not raised."""

    variant_count: int
    token_counts: tuple[int, ...]
    token_exact: bool
    structurally_identical: bool
    max_overlap: float
    mean_overlap: float
    worst_pair: tuple[str, str]
    shared_pad_fraction: float
    defects: tuple[str, ...]

    @property
    def usable(self) -> bool:
        """True when the set can support a floor estimate at all.

        Deliberately does NOT include the padding check. Heavy shared padding
        does not invalidate the floor; it makes the floor conservative, which is
        the safe direction. See :attr:`floor_is_lower_bound`.
        """
        return (
            self.token_exact
            and self.structurally_identical
            and self.max_overlap <= MAX_LEXICAL_OVERLAP
            and self.variant_count >= 3
        )

    @property
    def floor_is_lower_bound(self) -> bool:
        """True when shared padding means the true sensitivity is larger.

        The variants are token-exact, so hitting a long target forces the builder
        to pad, and padding is shared vocabulary. The blocks then differ over a
        smaller share of their surface than the banks do, and a floor measured
        from them understates how far the outcome would move under a real prompt
        change. Any contrast reported against such a floor must say so.
        """
        return self.shared_pad_fraction > MAX_SHARED_PAD_FRACTION


def assertSurfaceDistinctness(
    blocks: Sequence[PayloadBlock], *, max_overlap: float = MAX_LEXICAL_OVERLAP
) -> SurfaceFloorRecord:
    """Measure that the variants differ in surface and in nothing else."""
    if len(blocks) < 2:
        raise ValueError("a floor needs at least two variants")

    defects: list[str] = []
    token_counts = tuple(b.token_count for b in blocks)
    token_exact = len(set(token_counts)) == 1
    if not token_exact:
        defects.append(
            f"token counts differ across variants: {sorted(set(token_counts))}; "
            "a length difference would be measured as surface noise"
        )

    reference = blocks[0]
    structurally_identical = True
    for block in blocks[1:]:
        mismatches = []
        if block.header != reference.header:
            mismatches.append("header")
        if block.delimiter != reference.delimiter:
            mismatches.append("delimiter")
        if block.section_order != reference.section_order:
            mismatches.append("section_order")
        if block.bullet_counts != reference.bullet_counts:
            mismatches.append("bullet_counts")
        if block.prompt_slot_index != reference.prompt_slot_index:
            mismatches.append("prompt_slot_index")
        if mismatches:
            structurally_identical = False
            defects.append(f"{block.arm} differs from {reference.arm} in {mismatches}")

    overlaps: list[tuple[float, str, str]] = []
    for left, right in itertools.combinations(blocks, 2):
        overlaps.append((lexicalOverlap(left, right), left.arm, right.arm))
    worst = max(overlaps, key=lambda item: item[0])
    mean_overlap = sum(o for o, _l, _r in overlaps) / len(overlaps)
    if worst[0] > max_overlap:
        defects.append(
            f"{worst[1]} and {worst[2]} share {worst[0]:.2f} of their content "
            f"vocabulary, above the {max_overlap:.2f} ceiling; the measured floor "
            "understates the true perturbation sensitivity"
        )

    pad_fraction = sum(sharedPadFraction(b) for b in blocks) / len(blocks)
    if pad_fraction > MAX_SHARED_PAD_FRACTION:
        defects.append(
            f"{pad_fraction:.2f} of bullet words are shared padding vocabulary, "
            f"above the {MAX_SHARED_PAD_FRACTION:.2f} ceiling; the variants differ "
            "over too small a share of their surface and the measured floor is a "
            "lower bound"
        )

    return SurfaceFloorRecord(
        variant_count=len(blocks),
        token_counts=token_counts,
        token_exact=token_exact,
        structurally_identical=structurally_identical,
        max_overlap=worst[0],
        mean_overlap=mean_overlap,
        worst_pair=(worst[1], worst[2]),
        shared_pad_fraction=pad_fraction,
        defects=tuple(defects),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def buildSurfaceVariants(
    *,
    target_tokens: int,
    variant_count: int = DEFAULT_VARIANT_COUNT,
    bullet_counts: Sequence[int] | None = None,
    bullets_per_section: int = DEFAULT_BULLETS_PER_SECTION,
    prompt_slot_index: int = DEFAULT_PROMPT_SLOT_INDEX,
    tokenizer: Tokenizer = countTokens,
) -> tuple[PayloadBlock, ...]:
    """Build ``variant_count`` inert payloads that differ only in surface tokens.

    Each is token-exact to ``target_tokens`` and structurally identical to every
    other arm, so the only thing varying across them is which words appear.
    """
    if variant_count < 2:
        raise ValueError("a floor needs at least two variants")
    if variant_count > len(SURFACE_BANKS):
        raise ValueError(
            f"only {len(SURFACE_BANKS)} banks are defined; asking for "
            f"{variant_count} would require reusing one, which would report a "
            "floor of zero for the duplicated pair"
        )

    blocks: list[PayloadBlock] = []
    for index in range(variant_count):
        name, bank = SURFACE_BANKS[index]
        block = buildNeutralFiller(
            target_tokens=target_tokens,
            bullet_counts=bullet_counts,
            bullets_per_section=bullets_per_section,
            prompt_slot_index=prompt_slot_index,
            tokenizer=tokenizer,
            sentences=bank,
            arm=surfaceArmId(index),
        )
        block.provenance["surface_bank"] = name
        block.provenance["surface_variant_index"] = index
        block.provenance["is_floor_variant"] = True
        blocks.append(block)
    return tuple(blocks)
