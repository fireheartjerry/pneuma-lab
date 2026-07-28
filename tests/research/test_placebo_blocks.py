"""Tests for the seven-arm payload builders and the parity asserters.

The recurring theme: the task-blind placebo's blindness is a property of the
type system, not of reviewer discipline, and every parity gate reports what it
measured instead of quietly fixing it.

No network calls and no model backend. Every test supplies its own reflector.
"""

from __future__ import annotations

import dataclasses

import pytest

from pneuma_lab.placebo.blocks import (
    ARM_C1_ORACLE_FULL,
    ARM_C2_ORACLE_REDACTED,
    ARM_ORDER_ALL,
    ARM_S_RESAMPLE,
    ResamplePreconditionError,
    assertResampleIsMeaningful,
    ARM_P_TASK_BLIND,
    ARM_R0_NONE,
    ARM_R1_PLACEBO_RANDOM,
    ARM_R2_PLACEBO_MATCHED,
    ARM_R3_REAL,
    PAYLOAD_DELIMITER,
    PAYLOAD_HEADER,
    PLACEBO_ARMS,
    REDACTION_MASK,
    SCHEMA_SECTIONS,
    BLIND_INPUT_FIELD_NAMES,
    TOKEN_PARITY_TOLERANCE,
    BlindReflectorInputs,
    FailureTuple,
    assertItemParity,
    assertStructuralParity,
    assertTaskBlindness,
    assertTokenParity,
    buildDonorReflection,
    buildNeutralFiller,
    buildOracleReflection,
    buildParityRecord,
    buildPayloadSet,
    buildRealReflection,
    buildTaskBlindPlacebo,
    countTokens,
    neutralFillerFloorTokens,
    redactAssertionValues,
    redactToBlind,
    reflectorFieldOrderOf,
    withheldMaterial,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def targetFailure() -> FailureTuple:
    return FailureTuple(
        problem_id="MBPP+/311",
        problem_statement=(
            "Write a function nearestPalindrome that takes an integer numeral and "
            "returns the closest palindromic integer, breaking ties downward."
        ),
        failed_program=(
            "def nearestPalindrome(numeral):\n"
            "    candidate = numeral\n"
            "    while str(candidate) != str(candidate)[::-1]:\n"
            "        candidate += 1\n"
            "    return candidate\n"
        ),
        verifier_feedback=(
            "FAILED tests/test_palindrome.py::test_ties_downward\n"
            "E   assert nearestPalindrome(11) == 9\n"
            "E   AssertionError: 11 != 9\n"
        ),
        reference_solution="def nearestPalindrome(numeral): return _searchBothWays(numeral)",
        hidden_test_stderr=(
            "E   assert nearestPalindrome(11) == 9\n"
            "E   AssertionError: expected 9, got 11\n"
            "Expected: 9\n"
        ),
    )


def donorFailure() -> FailureTuple:
    return FailureTuple(
        problem_id="HumanEval+/42",
        problem_statement=(
            "Write a function mergeIntervals that consolidates overlapping numeric "
            "intervals into a minimal covering set."
        ),
        failed_program=(
            "def mergeIntervals(spans):\n    spans.sort()\n    return spans\n"
        ),
        verifier_feedback=(
            "FAILED tests/test_intervals.py::test_overlap\n"
            "E   assert mergeIntervals([[1, 4], [2, 5]]) == [[1, 5]]\n"
        ),
        reference_solution="def mergeIntervals(spans): return _sweep(spans)",
        hidden_test_stderr="E   assert mergeIntervals([[1, 4], [2, 5]]) == [[1, 5]]\n",
    )


def makeReflector(*, sentences_per_bullet: int = 2) -> object:
    """A deterministic stand-in for the frozen reflector.

    Length varies with the prompt, which is exactly the condition token parity
    has to survive: the real prompt is long, the blind prompt is withheld
    filler, and their raw outputs will not naturally match.
    """

    def generate(prompt: str, seed: int) -> str:
        scale = (len(prompt) // 40) + seed
        lines: list[str] = []
        for index, section in enumerate(SCHEMA_SECTIONS):
            lines.append(f"{section}:")
            for bullet in range(3):
                words = 3 + ((scale + index + bullet) % 5)
                body = " ".join(["step"] * words)
                sentence = f"The {section.lower()} note {bullet} covers {body}."
                lines.append(f"- {' '.join([sentence] * sentences_per_bullet)}")
        return "\n".join(lines)

    return generate


def buildSet(**kwargs) -> dict:
    return buildPayloadSet(
        targetFailure(),
        donor_random=donorFailure(),
        donor_matched=donorFailure(),
        generate=makeReflector(),
        seed=7,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Neutral filler -- token exactness and non-emptiness
# ---------------------------------------------------------------------------


def test_neutralFillerIsTokenExactToTheRealPayload() -> None:
    payloads = buildSet()
    real = payloads[ARM_R3_REAL]
    none_arm = payloads[ARM_R0_NONE]
    assert none_arm.token_count == real.token_count
    assert countTokens(none_arm.text) == real.token_count


def test_neutralFillerIsNeverEmpty() -> None:
    payloads = buildSet()
    none_arm = payloads[ARM_R0_NONE]
    assert none_arm.text.strip()
    for section in SCHEMA_SECTIONS:
        assert none_arm.sections[section]
        assert all(bullet.strip() for bullet in none_arm.sections[section])


def test_neutralFillerIsTokenExactAcrossManyTargets() -> None:
    floor = neutralFillerFloorTokens(bullets_per_section=3)
    for target in range(floor, floor + 60):
        block = buildNeutralFiller(target_tokens=target, bullets_per_section=3)
        assert block.token_count == target, target


def test_neutralFillerRefusesTargetsBelowItsStructuralFloor() -> None:
    floor = neutralFillerFloorTokens(bullets_per_section=3)
    with pytest.raises(ValueError, match="structural floor"):
        buildNeutralFiller(target_tokens=floor - 1, bullets_per_section=3)


def test_neutralFillerMakesNoModelCall() -> None:
    floor = neutralFillerFloorTokens(bullets_per_section=3)
    block = buildNeutralFiller(target_tokens=floor + 20, bullets_per_section=3)
    assert block.provenance["model_call"] is False
    assert block.reflector_prompt is None


# ---------------------------------------------------------------------------
# Token parity
# ---------------------------------------------------------------------------


def test_placeboArmsMatchWithinToleranceAndWithoutAsymmetry() -> None:
    payloads = buildSet()
    record = assertTokenParity(payloads)
    assert record.passed, record.defects
    assert set(record.placebo_arms) == set(PLACEBO_ARMS)
    for arm in PLACEBO_ARMS:
        assert record.placebo_absolute_deltas[arm] <= TOKEN_PARITY_TOLERANCE
    # The same tolerance is applied to every placebo arm, and the realized
    # matching is equally good for each -- no arm is better matched than another.
    assert record.placebo_tolerance_symmetric is True
    assert record.placebo_delta_spread == 0
    assert record.median_absolute_delta <= TOKEN_PARITY_TOLERANCE


def test_tokenParityReportsTheRealizedDistributionForEveryArm() -> None:
    payloads = buildSet()
    record = assertTokenParity(payloads)
    assert set(record.realized) == set(payloads)
    assert record.deltas[ARM_R3_REAL] == 0
    assert record.reference_tokens == payloads[ARM_R3_REAL].token_count


def test_tokenParityReportsAFailureInsteadOfRaising() -> None:
    """A parity failure is a reported defect, not an exception and not a repair."""

    def verboseSingleSentence(prompt: str, seed: int) -> str:
        body = " ".join(["overlong"] * 60)
        return "\n".join(f"{section}:\n- {body}" for section in SCHEMA_SECTIONS)

    real = buildRealReflection(targetFailure(), generate=makeReflector(), seed=1)
    donor = buildDonorReflection(
        donorFailure(),
        target_problem_id="MBPP+/311",
        arm=ARM_R1_PLACEBO_RANDOM,
        generate=verboseSingleSentence,
        seed=1,
        bullet_counts=real.bullet_counts,
        target_tokens=real.token_count,
    )
    # Truncation stops at the sentence floor rather than cutting mid-sentence.
    assert any(d.startswith("token_parity_overshoot") for d in donor.defects)

    record = assertTokenParity({ARM_R3_REAL: real, ARM_R1_PLACEBO_RANDOM: donor})
    assert record.passed is False
    assert record.realized[ARM_R1_PLACEBO_RANDOM] > record.reference_tokens
    assert any("token_parity" in defect for defect in record.defects)


# ---------------------------------------------------------------------------
# Structural parity
# ---------------------------------------------------------------------------


def test_headersAndDelimitersAreByteIdenticalAcrossArms() -> None:
    payloads = buildSet()
    headers = {block.header for block in payloads.values()}
    delimiters = {block.delimiter for block in payloads.values()}
    digests = {block.header_digest for block in payloads.values()}
    assert headers == {PAYLOAD_HEADER}
    assert delimiters == {PAYLOAD_DELIMITER}
    assert len(digests) == 1


def test_structuralParityCoversOrderingAndAbsolutePromptPosition() -> None:
    payloads = buildSet()
    record = assertStructuralParity(payloads)
    assert record.passed, record.defects
    assert set(record.section_orders.values()) == {SCHEMA_SECTIONS}
    assert len(set(record.prompt_slot_indices.values())) == 1


def test_structuralParityFlagsADivergentPromptSlot() -> None:
    payloads = buildSet()
    payloads[ARM_P_TASK_BLIND] = dataclasses.replace(
        payloads[ARM_P_TASK_BLIND], prompt_slot_index=1
    )
    record = assertStructuralParity(payloads)
    assert record.passed is False
    assert any(d.startswith("prompt_slot_mismatch") for d in record.defects)


# ---------------------------------------------------------------------------
# Item parity
# ---------------------------------------------------------------------------


def test_itemParityRequiresIdenticalBulletCounts() -> None:
    payloads = buildSet()
    record = assertItemParity(payloads)
    assert record.passed, record.defects
    assert len(set(record.bullet_counts.values())) == 1
    assert record.reference_counts == (3, 3, 3)


def test_itemParityFlagsAMismatchedBulletShape() -> None:
    payloads = buildSet()
    payloads[ARM_R1_PLACEBO_RANDOM] = dataclasses.replace(
        payloads[ARM_R1_PLACEBO_RANDOM], bullet_counts=(3, 2, 3)
    )
    record = assertItemParity(payloads)
    assert record.passed is False
    assert any(d.startswith("item_parity_mismatch") for d in record.defects)


def test_bulletReshapesAreRecordedAsDefectsNotHidden() -> None:
    def twoBulletReflector(prompt: str, seed: int) -> str:
        return "\n".join(f"{section}:\n- one.\n- two." for section in SCHEMA_SECTIONS)

    block = buildRealReflection(
        targetFailure(), generate=twoBulletReflector, bullets_per_section=3
    )
    assert block.bullet_counts == (3, 3, 3)
    assert any(d.startswith("bullet_count_padded") for d in block.defects)


# ---------------------------------------------------------------------------
# Task-blindness -- structural, not conventional
# ---------------------------------------------------------------------------


def test_taskBlindBuilderRefusesAFailureTuple() -> None:
    with pytest.raises(TypeError, match="BlindReflectorInputs"):
        buildTaskBlindPlacebo(targetFailure(), generate=makeReflector())


@pytest.mark.parametrize(
    "smuggled",
    [
        {"problem_statement": "return the closest palindrome"},
        {"failed_program": "def f(): pass"},
        {"verifier_feedback": "AssertionError: 11 != 9"},
        "def nearestPalindrome(n): ...",
        None,
    ],
)
def test_taskBlindBuilderRefusesAnythingButItsOwnInputType(smuggled: object) -> None:
    with pytest.raises(TypeError):
        buildTaskBlindPlacebo(smuggled, generate=makeReflector())


def test_blindInputsHaveNoFieldThatCanCarryTaskContent() -> None:
    names = {f.name for f in dataclasses.fields(BlindReflectorInputs)}
    assert names == {
        "language",
        "verification_status",
        "problem_statement_tokens",
        "failed_program_tokens",
        "verifier_feedback_tokens",
    }
    # The only string fields are allowlisted labels; the rest are counts.
    for name in (
        "problem_statement_tokens",
        "failed_program_tokens",
        "verifier_feedback_tokens",
    ):
        with pytest.raises(TypeError):
            BlindReflectorInputs(**{name: "def nearestPalindrome(n): ..."})


def test_blindInputsRejectFreeTextInTheAllowlistedFields() -> None:
    with pytest.raises(ValueError):
        BlindReflectorInputs(language="return the closest palindrome")
    with pytest.raises(ValueError):
        BlindReflectorInputs(verification_status="failed on test_ties_downward")


def test_blindInputsCannotHaveTaskFieldsAttachedAfterConstruction() -> None:
    blind = BlindReflectorInputs()
    assert not hasattr(blind, "problem_statement")
    assert not hasattr(blind, "__dict__")  # __slots__, so no ad-hoc attributes
    assert BLIND_INPUT_FIELD_NAMES == set(BlindReflectorInputs.__slots__)
    # Frozen + slots: CPython raises TypeError rather than FrozenInstanceError
    # here, so accept either -- what matters is that the assignment fails.
    with pytest.raises((AttributeError, TypeError, dataclasses.FrozenInstanceError)):
        blind.problem_statement = "return the closest palindrome"  # type: ignore[attr-defined]


def test_redactToBlindKeepsOnlyCountsAndPreservedLabels() -> None:
    failure = targetFailure()
    blind = redactToBlind(failure)
    assert blind.language == "Python"
    assert blind.verification_status == "failed"
    assert blind.problem_statement_tokens == countTokens(failure.problem_statement)
    assert blind.failed_program_tokens == countTokens(failure.failed_program)
    assert blind.verifier_feedback_tokens == countTokens(failure.verifier_feedback)
    # Nothing on the blind object serializes back to task content.
    dumped = repr(blind)
    assert "palindrome" not in dumped.lower()
    assert "assert" not in dumped.lower()


def test_blindPromptContainsNoTaskDerivedTerm() -> None:
    payloads = buildSet()
    record = assertTaskBlindness(payloads[ARM_P_TASK_BLIND], targetFailure())
    assert record.prompt_leak_terms == ()
    assert record.passed, record.defects


def test_blindnessScannerDetectsAPlantedLeak() -> None:
    """The scanner is a real gate: plant a task term and it must fail."""
    payloads = buildSet()
    blind = payloads[ARM_P_TASK_BLIND]
    leaked = dataclasses.replace(
        blind,
        reflector_prompt=(blind.reflector_prompt or "")
        + "\nproblem_statement: nearestPalindrome closest palindromic",
    )
    record = assertTaskBlindness(leaked, targetFailure())
    assert record.passed is False
    assert "nearestpalindrome" in record.prompt_leak_terms


def test_realAndBlindPromptsShareSchemaAndFieldOrder() -> None:
    failure = targetFailure()
    real = buildRealReflection(failure, generate=makeReflector())
    blind = buildTaskBlindPlacebo(redactToBlind(failure), generate=makeReflector())
    assert reflectorFieldOrderOf(real.reflector_prompt or "") == reflectorFieldOrderOf(
        blind.reflector_prompt or ""
    )
    # Same output instructions, byte for byte.
    real_tail = (real.reflector_prompt or "").split("Write a post-failure reflection")[
        -1
    ]
    blind_tail = (blind.reflector_prompt or "").split(
        "Write a post-failure reflection"
    )[-1]
    assert real_tail == blind_tail


def test_withheldMaterialIsTokenCountMatched() -> None:
    for count in range(0, 40):
        material = withheldMaterial(count)
        if count <= 0:
            continue
        assert countTokens(material) == count, count


def test_blindProvenanceRecordsThatNothingTaskSpecificWasSeen() -> None:
    payloads = buildSet()
    provenance = payloads[ARM_P_TASK_BLIND].provenance
    assert provenance["task_blind"] is True
    assert provenance["saw_problem_statement"] is False
    assert provenance["saw_failed_program"] is False
    assert provenance["saw_verifier_feedback"] is False
    assert provenance["saw_hidden_test_stderr"] is False


# ---------------------------------------------------------------------------
# Donor arm -- separate arm, labelled as such
# ---------------------------------------------------------------------------


def test_donorReflectionRefusesSelfDonation() -> None:
    donor = donorFailure()
    with pytest.raises(ValueError, match="self-donation"):
        buildDonorReflection(
            donor,
            target_problem_id=donor.problem_id,
            arm=ARM_R1_PLACEBO_RANDOM,
            generate=makeReflector(),
        )


def test_donorArmIsLabelledAsContentVersusMisinformation() -> None:
    payloads = buildSet()
    for arm in (ARM_R1_PLACEBO_RANDOM, ARM_R2_PLACEBO_MATCHED):
        provenance = payloads[arm].provenance
        assert provenance["estimates"] == "content_vs_misinformation"
        assert provenance["donor_problem_id"] == "HumanEval+/42"
        assert provenance["task_blind"] is False


def test_donorBuilderRejectsNonDonorArms() -> None:
    with pytest.raises(ValueError, match="donor arms"):
        buildDonorReflection(
            donorFailure(),
            target_problem_id="MBPP+/311",
            arm=ARM_R3_REAL,
            generate=makeReflector(),
        )


# ---------------------------------------------------------------------------
# Oracle positive control
# ---------------------------------------------------------------------------


def test_oracleFullSeesHiddenStderrAndRedactedMasksValues() -> None:
    failure = targetFailure()
    full = buildOracleReflection(failure, dose="full", generate=makeReflector())
    redacted = buildOracleReflection(failure, dose="redacted", generate=makeReflector())
    assert full.arm == ARM_C1_ORACLE_FULL
    assert redacted.arm == ARM_C2_ORACLE_REDACTED
    assert "AssertionError: expected 9, got 11" in (full.reflector_prompt or "")
    assert "AssertionError: expected 9, got 11" not in (redacted.reflector_prompt or "")
    assert REDACTION_MASK in (redacted.reflector_prompt or "")
    assert full.provenance["saw_hidden_test_stderr"] is True
    assert redacted.provenance["dose"] == "redacted"


def test_redactAssertionValuesMasksValuesAndExpectedOutputs() -> None:
    redacted = redactAssertionValues(targetFailure().hidden_test_stderr)
    assert "== 9" not in redacted
    assert "expected 9, got 11" not in redacted
    assert redacted.count(REDACTION_MASK) >= 3


def test_oracleRejectsAnUnknownDose() -> None:
    with pytest.raises(ValueError, match="dose"):
        buildOracleReflection(targetFailure(), dose="half", generate=makeReflector())


# ---------------------------------------------------------------------------
# Per-item parity record
# ---------------------------------------------------------------------------


def test_parityRecordIsAMatchingAuditRow() -> None:
    payloads = buildSet()
    record = buildParityRecord(
        payloads, problem_id="MBPP+/311", seed=7, failure=targetFailure()
    )
    assert record.passed, record.defects
    row = record.toRow()
    for key in (
        "problem_id",
        "seed",
        "reference_tokens",
        "token_median_abs_delta",
        "placebo_delta_spread",
        "placebo_tolerance_symmetric",
        "token_parity_passed",
        "structural_parity_passed",
        "item_parity_passed",
        "task_blind_passed",
        "parity_passed",
        "defect_count",
    ):
        assert key in row
    assert row["defect_count"] == 0
    assert row["task_blind_passed"] is True
    assert set(record.arms) == set(payloads)


def test_parityRecordCarriesDefectsRatherThanRepairingThem() -> None:
    payloads = buildSet()
    payloads[ARM_R2_PLACEBO_MATCHED] = dataclasses.replace(
        payloads[ARM_R2_PLACEBO_MATCHED],
        token_count=payloads[ARM_R3_REAL].token_count + 11,
    )
    record = buildParityRecord(payloads, problem_id="MBPP+/311", seed=7)
    assert record.passed is False
    assert record.toRow()["defect_count"] > 0
    # The offending payload is untouched -- nothing was silently corrected.
    assert payloads[ARM_R2_PLACEBO_MATCHED].token_count == (
        payloads[ARM_R3_REAL].token_count + 11
    )


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_payloadSetIsDeterministic() -> None:
    first = buildSet()
    second = buildSet()
    assert {arm: block.text for arm, block in first.items()} == {
        arm: block.text for arm, block in second.items()
    }


def test_allSevenArmsAreBuilt() -> None:
    """The confirmatory roster: C2 dropped as descope item one, RESAMPLE added.

    Still seven arms. The compute control is bought with the second oracle dose
    rather than with extra budget, which is the trade the descope order makes.
    """
    payloads = buildSet()
    assert set(payloads) == {
        ARM_R0_NONE,
        ARM_P_TASK_BLIND,
        ARM_R1_PLACEBO_RANDOM,
        ARM_R2_PLACEBO_MATCHED,
        ARM_R3_REAL,
        ARM_S_RESAMPLE,
        ARM_C1_ORACLE_FULL,
    }
    assert ARM_C2_ORACLE_REDACTED not in payloads


def test_theRedactedDoseIsRestorableByFlagNotByRebuild() -> None:
    payloads = buildSet(include_redacted_dose=True)
    assert ARM_C2_ORACLE_REDACTED in payloads
    assert set(payloads) == set(ARM_ORDER_ALL)


def test_resampleCarriesNoContentButDemandsAnExtraDraw() -> None:
    block = buildSet()[ARM_S_RESAMPLE]
    assert block.provenance["requires_independent_resample"] is True
    assert block.provenance["model_call"] is False
    assert block.provenance["saw_problem_statement"] is False
    # Token-exact and structurally identical to every other arm.
    assert block.token_count == buildSet()[ARM_R3_REAL].token_count


def test_resampleRefusesGreedyDecodingBecauseASecondDrawWouldBeIdentical() -> None:
    with pytest.raises(ResamplePreconditionError, match="byte-identical"):
        assertResampleIsMeaningful(temperature=0.0)


def test_resampleAcceptsStochasticDecoding() -> None:
    assertResampleIsMeaningful(temperature=0.7, top_p=0.95, seeds=(1, 2, 3))


def test_resampleRefusesASingleSeed() -> None:
    with pytest.raises(ResamplePreconditionError, match="two distinct seeds"):
        assertResampleIsMeaningful(temperature=0.7, seeds=(4, 4, 4))


def test_buildersDoNotImportTheBackendWhenAReflectorIsSupplied() -> None:
    """The backend is resolved lazily, so tests never depend on it existing."""
    import sys

    sys.modules.pop("pneuma_lab.placebo.backend", None)
    buildSet()
    assert "pneuma_lab.placebo.backend" not in sys.modules
