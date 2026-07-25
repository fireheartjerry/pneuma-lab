"""Tests for donor assignment, the leakage audit, and the judge-free check.

The load-bearing assertions here are negative: no self-donation on any path,
no correlation between derangements drawn under different seeds, no donor
admitted that shares an 8-gram with the target's reference solution, and no LLM
judge anywhere in the module.
"""

from __future__ import annotations

import json

import pytest

from pneuma_lab.placebo.donors import (
    LEAKAGE_NGRAM_SIZE,
    MANIFEST_DIGEST_FIELD,
    MANIPULATION_METHOD,
    METHOD_TFIDF_MATCHED,
    METHOD_UNIFORM,
    USES_LLM_JUDGE,
    VERDICT_DONOR_CONTENT,
    VERDICT_TASK_BLIND,
    DonorCandidate,
    LeakageTarget,
    SelectionTarget,
    assignDonorsMatched,
    assignDonorsUniform,
    auditLeakage,
    buildDerangement,
    buildDonorManifest,
    extractNgrams,
    loadDonorManifest,
    manipulationCheck,
    normalizeCodeTokens,
    rankMatchedDonors,
    selectMatchedDonor,
    selectUniformDonor,
    verifyDonorManifest,
    writeDonorManifest,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REFERENCE_SOLUTION = (
    "def nearestPalindrome(numeral):\n"
    "    lower = _scanDownward(numeral)\n"
    "    upper = _scanUpward(numeral)\n"
    "    return lower if numeral - lower <= upper - numeral else upper\n"
)


def rosterIds(count: int) -> list[str]:
    return [f"P{index:03d}" for index in range(count)]


def selectionRoster() -> list[SelectionTarget]:
    return [
        SelectionTarget("P000", "sort a list of integers ascending and return it"),
        SelectionTarget("P001", "sort an array of integers descending and return it"),
        SelectionTarget("P002", "parse an ISO date string into year month and day"),
        SelectionTarget("P003", "compute the greatest common divisor of two integers"),
        SelectionTarget("P004", "parse a date string in ISO form and return the year"),
    ]


# ---------------------------------------------------------------------------
# Derangements
# ---------------------------------------------------------------------------


def test_derangementNeverSelfDonates() -> None:
    for seed in range(12):
        mapping = buildDerangement(rosterIds(30), seed=seed)
        assert all(target != donor for target, donor in mapping.items())


def test_derangementIsABijectionOverTheRoster() -> None:
    ids = rosterIds(30)
    mapping = buildDerangement(ids, seed=3)
    assert sorted(mapping) == sorted(ids)
    assert sorted(mapping.values()) == sorted(ids)


def test_derangementIsDeterministicInItsSeed() -> None:
    ids = rosterIds(40)
    assert buildDerangement(ids, seed=11) == buildDerangement(ids, seed=11)


def test_derangementsAreIndependentAcrossSeeds() -> None:
    """Different seeds are independent draws, not perturbations of one another."""
    ids = rosterIds(60)
    mappings = [buildDerangement(ids, seed=seed) for seed in range(6)]
    for i in range(len(mappings)):
        for j in range(i + 1, len(mappings)):
            agreements = sum(1 for key in ids if mappings[i][key] == mappings[j][key])
            assert mappings[i] != mappings[j]
            # Under independence the expected agreement count is ~1 for n = 60.
            assert agreements / len(ids) < 0.15


def test_derangementRefusesARosterTooSmallToDerange() -> None:
    with pytest.raises(ValueError, match="at least 2"):
        buildDerangement(["only"], seed=0)


def test_derangementRefusesDuplicateIds() -> None:
    with pytest.raises(ValueError, match="unique"):
        buildDerangement(["a", "a", "b"], seed=0)


# ---------------------------------------------------------------------------
# Selection sees task text only
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "smuggled",
    [
        {"problem_id": "P000", "task_text": "sort", "grade": True},
        {"problem_id": "P000", "generated_output": "def f(): ..."},
        "P000",
        None,
    ],
)
def test_selectionRefusesAnythingButASelectionTarget(smuggled: object) -> None:
    roster = selectionRoster()
    with pytest.raises(TypeError):
        selectUniformDonor(smuggled, roster, seed=0)
    with pytest.raises(TypeError):
        selectMatchedDonor(smuggled, roster)


def test_selectionTargetHasNoSlotForAnOutcome() -> None:
    target = SelectionTarget("P000", "sort a list")
    assert set(SelectionTarget.__slots__) == {"problem_id", "task_text"}
    assert not hasattr(target, "__dict__")
    for forbidden in ("grade", "reflection", "generated_output"):
        assert not hasattr(target, forbidden)
        # Frozen + slots: CPython raises TypeError rather than
        # FrozenInstanceError here; either way the assignment cannot land.
        with pytest.raises((AttributeError, TypeError)):
            setattr(target, forbidden, "smuggled")


def test_uniformSelectionNeverReturnsTheTarget() -> None:
    roster = selectionRoster()
    for target in roster:
        for seed in range(8):
            assert selectUniformDonor(target, roster, seed=seed) != target.problem_id


def test_matchedSelectionPicksTheNearestOtherTaskText() -> None:
    roster = selectionRoster()
    assert selectMatchedDonor(roster[0], roster) == "P001"
    assert selectMatchedDonor(roster[2], roster) == "P004"
    assert selectMatchedDonor(roster[4], roster) == "P002"


def test_matchedRankingIsTotalAndExcludesSelf() -> None:
    roster = selectionRoster()
    ranked = rankMatchedDonors(roster[0], roster)
    assert [pid for pid, _ in ranked] == sorted(
        [pid for pid, _ in ranked],
        key=lambda pid: (-dict(ranked)[pid], pid),
    )
    assert "P000" not in dict(ranked)


# ---------------------------------------------------------------------------
# Roster assignment
# ---------------------------------------------------------------------------


def test_uniformAssignmentIsADerangementOverTheRoster() -> None:
    assignment = assignDonorsUniform(selectionRoster(), seed=4)
    assert assignment.method == METHOD_UNIFORM
    assignment.assertNoSelfDonation()
    assert sorted(assignment.mapping.values()) == sorted(assignment.mapping)


def test_uniformAssignmentHonoursExcludedPairs() -> None:
    roster = selectionRoster()
    base = assignDonorsUniform(roster, seed=4)
    victim = "P000"
    banned = [(victim, base.mapping[victim])]
    repaired = assignDonorsUniform(roster, seed=4, excluded_pairs=banned)
    assert repaired.mapping.get(victim) != base.mapping[victim]
    repaired.assertNoSelfDonation()
    for target, donor in repaired.mapping.items():
        assert (target, donor) not in set(banned)


def test_matchedAssignmentHonoursExcludedPairsAndNeverSelfDonates() -> None:
    roster = selectionRoster()
    banned = [("P000", "P001")]
    assignment = assignDonorsMatched(roster, seed=1, excluded_pairs=banned)
    assert assignment.method == METHOD_TFIDF_MATCHED
    assert assignment.mapping["P000"] != "P001"
    assignment.assertNoSelfDonation()


# ---------------------------------------------------------------------------
# Leakage audit
# ---------------------------------------------------------------------------


def plantedOverlapDonor() -> DonorCandidate:
    """A donor whose payload quotes a contiguous 8-token run of the solution."""
    tokens = normalizeCodeTokens(REFERENCE_SOLUTION)
    planted = " ".join(tokens[4 : 4 + LEAKAGE_NGRAM_SIZE])
    return DonorCandidate(
        problem_id="P901",
        task_text="an unrelated interval merging problem",
        payload_material=f"Consider the shape of the fix: {planted} handles the tie.",
    )


def cleanDonor() -> DonorCandidate:
    return DonorCandidate(
        problem_id="P902",
        task_text="merge overlapping numeric intervals into a minimal covering set",
        payload_material="Re-derive the boundary condition before changing the loop.",
    )


def test_leakageAuditRejectsAPlantedEightGramOverlap() -> None:
    targets = [LeakageTarget("P100", REFERENCE_SOLUTION)]
    candidates = [plantedOverlapDonor(), cleanDonor()]
    audit = auditLeakage(targets, candidates)
    assert audit.isExcluded("P100", "P901")
    assert not audit.isExcluded("P100", "P902")
    assert audit.excludedDonorsFor("P100") == ("P901",)
    assert audit.findings[0].donor_id == "P901"
    assert audit.findings[0].shared_ngram_count >= 1
    assert len(audit.findings[0].example_ngram) == LEAKAGE_NGRAM_SIZE


def test_leakageAuditAdmitsACleanDonor() -> None:
    audit = auditLeakage([LeakageTarget("P100", REFERENCE_SOLUTION)], [cleanDonor()])
    assert audit.findings == ()
    assert audit.excludedDonorsFor("P100") == ()


def test_leakageAuditIsInsensitiveToWhitespaceReformatting() -> None:
    tokens = normalizeCodeTokens(REFERENCE_SOLUTION)
    planted = "\n   ".join(tokens[2 : 2 + LEAKAGE_NGRAM_SIZE])
    donor = DonorCandidate("P903", "unrelated", f"hint:\n   {planted}\n")
    audit = auditLeakage([LeakageTarget("P100", REFERENCE_SOLUTION)], [donor])
    assert audit.isExcluded("P100", "P903")


def test_leakageAuditRespectsTheNgramThreshold() -> None:
    """A 7-token overlap is below the 8-gram rule and is not excluded."""
    tokens = normalizeCodeTokens(REFERENCE_SOLUTION)
    short = " ".join(tokens[4 : 4 + LEAKAGE_NGRAM_SIZE - 1])
    donor = DonorCandidate("P904", "unrelated", f"note: {short}")
    audit = auditLeakage([LeakageTarget("P100", REFERENCE_SOLUTION)], [donor])
    assert not audit.isExcluded("P100", "P904")
    stricter = auditLeakage(
        [LeakageTarget("P100", REFERENCE_SOLUTION)],
        [donor],
        ngram_size=LEAKAGE_NGRAM_SIZE - 1,
    )
    assert stricter.isExcluded("P100", "P904")


def test_leakageAuditAlwaysExcludesTheSelfPair() -> None:
    audit = auditLeakage(
        [LeakageTarget("P100", REFERENCE_SOLUTION)],
        [DonorCandidate("P100", "same problem", "same payload")],
    )
    assert audit.isExcluded("P100", "P100")


def test_extractNgramsReturnsNothingBelowTheWindow() -> None:
    assert extractNgrams("a b c", 8) == set()


def test_leakageExclusionsFlowIntoEveryArm() -> None:
    """An excluded pair must be absent from the uniform AND matched assignments."""
    roster = selectionRoster()
    targets = [LeakageTarget(t.problem_id, REFERENCE_SOLUTION) for t in roster]
    tokens = normalizeCodeTokens(REFERENCE_SOLUTION)
    planted = " ".join(tokens[:LEAKAGE_NGRAM_SIZE])
    candidates = [
        DonorCandidate(
            t.problem_id,
            t.task_text,
            planted if t.problem_id == "P001" else "generic procedural note",
        )
        for t in roster
    ]
    audit = auditLeakage(targets, candidates)
    banned = audit.excluded_pairs
    assert ("P000", "P001") in banned

    uniform = assignDonorsUniform(roster, seed=2, excluded_pairs=banned)
    matched = assignDonorsMatched(roster, seed=2, excluded_pairs=banned)
    for assignment in (uniform, matched):
        for target, donor in assignment.mapping.items():
            assert (target, donor) not in set(banned)


# ---------------------------------------------------------------------------
# Manipulation check -- deterministic, judge-free
# ---------------------------------------------------------------------------


def test_moduleContainsNoLlmJudge() -> None:
    assert USES_LLM_JUDGE is False
    record = manipulationCheck(
        "Re-derive your assumptions before editing.",
        target_task_text="sort a list of integers ascending",
        expectation="task_blind",
    )
    assert record.uses_llm_judge is False
    assert record.method == MANIPULATION_METHOD


def test_manipulationCheckConfirmsATaskBlindPayload() -> None:
    record = manipulationCheck(
        "Reconstruct the assumptions and re-check the boundary conditions.",
        target_task_text="compute the nearest palindromic integer to a numeral",
        donor_task_text="merge overlapping numeric intervals",
        expectation="task_blind",
    )
    assert record.verdict == VERDICT_TASK_BLIND
    assert record.consistent_with_expectation is True


def test_manipulationCheckDetectsDonorContent() -> None:
    record = manipulationCheck(
        "The overlapping intervals were merged incorrectly; sweep the intervals once.",
        target_task_text="compute the nearest palindromic integer to a numeral",
        donor_task_text="merge overlapping numeric intervals into a covering set",
        expectation="donor",
    )
    assert record.verdict == VERDICT_DONOR_CONTENT
    assert record.consistent_with_expectation is True
    assert record.payload_vs_donor_tfidf > record.payload_vs_target_tfidf


def test_manipulationCheckFlagsAMisroutedPayload() -> None:
    """A payload about the target, injected into a donor arm, must not pass."""
    record = manipulationCheck(
        "The palindromic numeral comparison never searches downward.",
        target_task_text="compute the nearest palindromic numeral downward",
        donor_task_text="merge overlapping numeric intervals",
        expectation="donor",
    )
    assert record.consistent_with_expectation is False


def test_manipulationCheckIsDeterministic() -> None:
    args = {
        "target_task_text": "sort a list of integers ascending",
        "donor_task_text": "merge overlapping numeric intervals",
        "expectation": "donor",
    }
    first = manipulationCheck("merge the intervals once", **args)
    second = manipulationCheck("merge the intervals once", **args)
    assert first == second


def test_manipulationCheckRejectsAnUnknownExpectation() -> None:
    with pytest.raises(ValueError, match="expectation"):
        manipulationCheck("x", target_task_text="y", expectation="vibes")


# ---------------------------------------------------------------------------
# Published donor manifest
# ---------------------------------------------------------------------------


def test_manifestRoundTripsAndItsDigestVerifies(tmp_path) -> None:
    roster = selectionRoster()
    audit = auditLeakage(
        [LeakageTarget("P000", REFERENCE_SOLUTION)], [plantedOverlapDonor()]
    )
    assignment = assignDonorsUniform(roster, seed=5)
    manifest = buildDonorManifest(assignment, arm="R1_PLACEBO_RANDOM", audit=audit)

    path = tmp_path / "donors" / "r1_seed5.json"
    digest = writeDonorManifest(manifest, path)
    loaded, recorded = loadDonorManifest(path)
    assert recorded == digest
    assert verifyDonorManifest(loaded, digest)
    assert loaded.mapping == assignment.mapping
    assert loaded.method == METHOD_UNIFORM


def test_manifestDigestDetectsASilentRedraw(tmp_path) -> None:
    assignment = assignDonorsUniform(selectionRoster(), seed=5)
    manifest = buildDonorManifest(assignment, arm="R1_PLACEBO_RANDOM")
    path = tmp_path / "r1.json"
    digest = writeDonorManifest(manifest, path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    victim = sorted(payload["mapping"])[0]
    replacement = next(
        pid
        for pid in sorted(payload["mapping"])
        if pid != payload["mapping"][victim] and pid != victim
    )
    payload["mapping"][victim] = replacement
    path.write_text(json.dumps(payload, indent=4, sort_keys=True), encoding="utf-8")

    tampered, recorded = loadDonorManifest(path)
    assert recorded == digest
    assert verifyDonorManifest(tampered, digest) is False


def test_manifestRecordsTheJudgeFreeReceipt() -> None:
    assignment = assignDonorsUniform(selectionRoster(), seed=5)
    manifest = buildDonorManifest(assignment, arm="R2_PLACEBO_MATCHED")
    assert manifest.toDict()["uses_llm_judge"] is False
    assert MANIFEST_DIGEST_FIELD not in manifest.toDict()
