"""Tests for the prompt-perturbation noise floor variants.

What is locked here is the set of properties that make a measured floor mean
what the paper will say it means. In order of consequence:

  * the variants are token-exact and structurally identical, so any difference in
    outcome is attributable to surface tokens and to nothing else;
  * they are lexically distinct AFTER shared scaffolding is discounted, because
    a floor measured over near-identical text is a floor of zero;
  * shared padding is reported rather than absorbed, because it makes the floor
    conservative and a reader must be able to see by how much;
  * a bank is never silently reused, because a duplicated pair contributes an
    artificial zero to the spread.
"""

from __future__ import annotations

import pytest

from pneuma_lab.placebo.blocks import (
    NEUTRAL_SENTENCES,
    PAYLOAD_DELIMITER,
    PAYLOAD_HEADER,
    SCHEMA_SECTIONS,
)
from pneuma_lab.placebo.surface_floor import (
    MAX_LEXICAL_OVERLAP,
    SURFACE_BANKS,
    assertSurfaceDistinctness,
    buildSurfaceVariants,
    contentWords,
    lexicalOverlap,
    sharedPadFraction,
    surfaceArmId,
)

FEASIBLE_TARGET = 100


def variants(target: int = FEASIBLE_TARGET, count: int = 6):
    return buildSurfaceVariants(target_tokens=target, variant_count=count)


# ---------------------------------------------------------------------------
# Construction invariants
# ---------------------------------------------------------------------------


def test_variants_are_token_exact_to_the_same_target() -> None:
    blocks = variants()
    assert {b.token_count for b in blocks} == {FEASIBLE_TARGET}


def test_variants_are_structurally_identical() -> None:
    blocks = variants()
    for block in blocks:
        assert block.header == PAYLOAD_HEADER
        assert block.delimiter == PAYLOAD_DELIMITER
        assert block.section_order == SCHEMA_SECTIONS
        assert block.prompt_slot_index == blocks[0].prompt_slot_index
        assert block.bullet_counts == blocks[0].bullet_counts


def test_variants_have_distinct_text() -> None:
    blocks = variants()
    assert len({b.text for b in blocks}) == len(blocks)
    assert len({b.text_digest for b in blocks}) == len(blocks)


def test_first_bank_is_the_committed_neutral_prose() -> None:
    """The study's own floor arm sits inside its own noise floor, not outside it."""
    assert SURFACE_BANKS[0][1] == NEUTRAL_SENTENCES


def test_arm_ids_are_stable_and_ordered() -> None:
    blocks = variants()
    assert [b.arm for b in blocks] == [surfaceArmId(i) for i in range(len(blocks))]


def test_provenance_marks_these_as_floor_variants_not_treatment_arms() -> None:
    for index, block in enumerate(variants()):
        assert block.provenance["is_floor_variant"] is True
        assert block.provenance["surface_variant_index"] == index
        assert block.provenance["surface_bank"] == SURFACE_BANKS[index][0]
        # Inert by construction: no model call, saw nothing about any task.
        assert block.provenance["model_call"] is False
        assert block.provenance["saw_problem_statement"] is False
        assert block.provenance["saw_failed_program"] is False


# ---------------------------------------------------------------------------
# Distinctness
# ---------------------------------------------------------------------------


def test_banks_are_lexically_distinct_once_scaffolding_is_discounted() -> None:
    record = assertSurfaceDistinctness(variants())
    assert record.max_overlap <= MAX_LEXICAL_OVERLAP
    assert record.usable


def test_padding_vocabulary_is_excluded_from_the_overlap_measure() -> None:
    """The defect this prevents: every bank looking similar because all padding is shared.

    Measured during construction -- including pad words put the worst pair at
    0.355, above the ceiling, purely because `fitSectionsToTarget` appends the
    same words to every bank.
    """
    blocks = variants(target=200)
    record = assertSurfaceDistinctness(blocks)
    # At this target most bullet words are padding...
    assert record.shared_pad_fraction > 0.5
    # ...yet the banks themselves remain distinct.
    assert record.max_overlap <= MAX_LEXICAL_OVERLAP


def test_identical_blocks_have_full_overlap() -> None:
    blocks = variants()
    assert lexicalOverlap(blocks[0], blocks[0]) == pytest.approx(1.0)


def test_content_words_exclude_the_schema_section_names() -> None:
    words = contentWords(variants()[0])
    for name in SCHEMA_SECTIONS:
        assert name.lower().split()[0] not in words


# ---------------------------------------------------------------------------
# Shared padding is reported, not absorbed
# ---------------------------------------------------------------------------


def test_shared_padding_grows_with_the_token_target() -> None:
    short = assertSurfaceDistinctness(variants(target=100))
    long = assertSurfaceDistinctness(variants(target=200))
    assert long.shared_pad_fraction > short.shared_pad_fraction


def test_heavy_padding_marks_the_floor_as_a_lower_bound_without_invalidating_it() -> (
    None
):
    record = assertSurfaceDistinctness(variants(target=200))
    assert record.floor_is_lower_bound
    # Conservative, not broken: the floor still supports a claim, it just
    # understates true sensitivity.
    assert record.usable
    assert any("lower bound" in d for d in record.defects)


def test_light_padding_does_not_flag_a_lower_bound() -> None:
    record = assertSurfaceDistinctness(variants(target=100))
    assert not record.floor_is_lower_bound


def test_pad_fraction_of_an_unpadded_block_is_zero_or_small() -> None:
    blocks = variants(target=100)
    assert 0.0 <= sharedPadFraction(blocks[0]) < 1.0


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


def test_a_single_variant_is_not_a_floor() -> None:
    with pytest.raises(ValueError, match="at least two"):
        buildSurfaceVariants(target_tokens=FEASIBLE_TARGET, variant_count=1)


def test_banks_are_never_reused_to_pad_the_variant_count() -> None:
    """A duplicated bank would contribute an artificial zero to the spread."""
    with pytest.raises(ValueError, match="reusing one"):
        buildSurfaceVariants(
            target_tokens=FEASIBLE_TARGET, variant_count=len(SURFACE_BANKS) + 1
        )


def test_token_target_below_the_structural_floor_raises_rather_than_approximating() -> (
    None
):
    with pytest.raises(ValueError, match="structural floor"):
        buildSurfaceVariants(target_tokens=10)


def test_distinctness_needs_two_blocks() -> None:
    with pytest.raises(ValueError, match="at least two"):
        assertSurfaceDistinctness(variants()[:1])


# ---------------------------------------------------------------------------
# Defect reporting
# ---------------------------------------------------------------------------


def test_a_token_count_mismatch_is_reported_not_raised() -> None:
    mixed = list(variants(target=100)[:3]) + list(variants(target=120)[3:])
    record = assertSurfaceDistinctness(mixed)
    assert not record.token_exact
    assert not record.usable
    assert any("token counts differ" in d for d in record.defects)


def test_worst_pair_is_identified_by_arm_id() -> None:
    record = assertSurfaceDistinctness(variants())
    arms = {b.arm for b in variants()}
    assert record.worst_pair[0] in arms
    assert record.worst_pair[1] in arms
    assert record.worst_pair[0] != record.worst_pair[1]
