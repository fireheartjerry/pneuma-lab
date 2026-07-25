"""Tests for the subprocess-isolated EvalPlus grader.

None of these require EvalPlus data or a network call: every test injects an explicit
``GradingProblem``, which is also the path an offline replay of a recorded batch takes.
The one test that touches the EvalPlus import path deliberately breaks it, to assert the
error message is actionable rather than a bare ImportError.
"""

from __future__ import annotations

import json
import sys

import pytest

from pneuma_lab.placebo.grader import (
    EVALPLUS_MISSING_MESSAGE,
    EvalPlusUnavailable,
    GradingProblem,
    ProblemNotFound,
    PublicFailureSignal,
    TestCase,
    buildPublicFailureSignal,
    datasetOf,
    dedupeDefinitions,
    extractCode,
    gradeSolution,
    loadEvalPlusProblems,
)

FAST_TIMEOUT_SECONDS = 2.0


def addProblem(
    *,
    entry_point: str = "add",
    visible: list[tuple[tuple, object]] | None = None,
    hidden: list[tuple[tuple, object]] | None = None,
    dataset: str = "humaneval",
    atol: float = 0.0,
    problem_id: str = "HumanEval/999",
) -> GradingProblem:
    """A two-argument-addition problem with explicit visible/hidden splits."""
    visible = visible if visible is not None else [((1, 2), 3), ((0, 0), 0)]
    hidden = hidden if hidden is not None else [((10, 5), 15), ((-4, 4), 0)]
    tests: list[TestCase] = []
    for args, expected in visible:
        tests.append(TestCase(len(tests), args, expected, visible=True))
    for args, expected in hidden:
        tests.append(TestCase(len(tests), args, expected, visible=False))
    return GradingProblem(
        problem_id=problem_id,
        dataset=dataset,
        entry_point=entry_point,
        prompt="def add(a, b):\n",
        atol=atol,
        tests=tuple(tests),
    )


def grade(code: str, problem: GradingProblem | None = None, **kwargs):
    problem = problem or addProblem()
    kwargs.setdefault("per_test_timeout_s", FAST_TIMEOUT_SECONDS)
    return gradeSolution(problem.problem_id, code, problem=problem, **kwargs)


# ---------------------------------------------------------------------------
# Known-passing and known-failing solutions
# ---------------------------------------------------------------------------


def test_knownPassingSolutionPassesEveryTest() -> None:
    result = grade("def add(a, b):\n    return a + b\n")
    assert result.all_tests_pass is True
    assert result.tests_passed == 4
    assert result.tests_failed == 0
    assert result.tests_total == 4
    assert result.timed_out is False
    assert result.syntax_error is False
    assert result.first_failure_stderr == ""
    assert result.failing_indices == ()
    assert result.graded is True


def test_knownFailingSolutionReportsCountsAndFirstFailure() -> None:
    result = grade("def add(a, b):\n    return a - b\n")
    assert result.all_tests_pass is False
    assert result.tests_passed == 1  # only (0, 0) -> 0 survives subtraction
    assert result.tests_failed == 3
    assert result.first_failure_stderr != ""
    assert "expected: 3" in result.first_failure_stderr
    assert result.failing_indices == (0, 2, 3)


def test_gradeResultIsFrozen() -> None:
    result = grade("def add(a, b):\n    return a + b\n")
    with pytest.raises(Exception):
        result.all_tests_pass = False  # type: ignore[misc]


def test_raisingCandidateCapturesTheRealTraceback() -> None:
    result = grade("def add(a, b):\n    raise ValueError('boom')\n")
    assert result.all_tests_pass is False
    assert result.tests_passed == 0
    assert "ValueError: boom" in result.first_failure_stderr
    assert "Traceback" in result.first_failure_stderr


def test_candidateStderrIsCapturedAlongsideTheTraceback() -> None:
    code = (
        "import sys\n"
        "def add(a, b):\n"
        "    sys.stderr.write('diagnostic noise\\n')\n"
        "    return a - b\n"
    )
    result = grade(code)
    assert "diagnostic noise" in result.first_failure_stderr


def test_missingEntryPointIsReportedWithoutClaimingSyntaxError() -> None:
    result = grade("def subtract(a, b):\n    return a - b\n")
    assert result.all_tests_pass is False
    assert result.syntax_error is False
    assert "does not define 'add'" in result.first_failure_stderr
    assert result.tests_failed == result.tests_total


def test_moduleLevelExceptionIsReportedBeforeAnyTestRuns() -> None:
    result = grade(
        "raise RuntimeError('import-time explosion')\n"
        "def add(a, b):\n    return a + b\n"
    )
    assert result.all_tests_pass is False
    assert result.syntax_error is False
    assert "import-time explosion" in result.first_failure_stderr


# ---------------------------------------------------------------------------
# Timeout behaviour
# ---------------------------------------------------------------------------


def test_hangingCandidateTimesOutWithoutTakingDownTheHarness() -> None:
    result = grade(
        "def add(a, b):\n    while True:\n        pass\n", per_test_timeout_s=1.0
    )
    assert result.timed_out is True
    assert result.all_tests_pass is False
    assert result.tests_passed == 0
    assert "TimeoutError" in result.first_failure_stderr
    # The harness itself is fine: it graded the unit and returned a usable row.
    assert result.graded is True


def test_timeoutIsPerTestSoLaterTestsAreStillCountedAgainstTheCandidate() -> None:
    result = grade(
        "def add(a, b):\n    while True:\n        pass\n", per_test_timeout_s=1.0
    )
    assert result.tests_failed == result.tests_total


def test_harnessSurvivesACandidateThatKillsItsOwnProcess() -> None:
    result = grade("import os\ndef add(a, b):\n    os._exit(3)\n")
    assert result.all_tests_pass is False
    assert result.graded is False  # a harness-side failure must not enter analysis
    assert result.harness_error != ""


def test_gradingKeepsWorkingAfterAHangingCandidate() -> None:
    grade("def add(a, b):\n    while True:\n        pass\n", per_test_timeout_s=1.0)
    healthy = grade("def add(a, b):\n    return a + b\n")
    assert healthy.all_tests_pass is True


# ---------------------------------------------------------------------------
# Syntax / parse failures
# ---------------------------------------------------------------------------


def test_syntaxErrorIsFlaggedAndCarriesAMessage() -> None:
    result = grade("def add(a, b)\n    return a + b\n", extract=False)
    assert result.syntax_error is True
    assert result.all_tests_pass is False
    assert "SyntaxError" in result.syntax_error_message
    assert result.tests_failed == result.tests_total


def test_emptyOutputIsAParseFailureNotACrash() -> None:
    result = grade("   \n\n  ")
    assert result.syntax_error is True
    assert result.all_tests_pass is False
    assert result.public_failure_signal.has_signal is True


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------


def test_extractsFromATaggedMarkdownFence() -> None:
    raw = "Here you go:\n\n```python\ndef add(a, b):\n    return a + b\n```\n\nHope that helps!"
    extracted = extractCode(raw, "add")
    assert extracted.parsed is True
    assert extracted.code.strip() == "def add(a, b):\n    return a + b"
    assert "fenced" in extracted.strategy


def test_extractsFromAnUntaggedFence() -> None:
    extracted = extractCode("```\ndef add(a, b):\n    return a + b\n```", "add")
    assert extracted.parsed is True
    assert "def add" in extracted.code


def test_extractsFromAnUnterminatedFence() -> None:
    """Models truncated by max_tokens routinely never close the fence."""
    extracted = extractCode(
        "Sure:\n```python\ndef add(a, b):\n    return a + b\n", "add"
    )
    assert extracted.parsed is True
    assert "return a + b" in extracted.code


def test_prefersTheFencedBlockThatDefinesTheEntryPoint() -> None:
    raw = (
        "First, the helper we will use:\n"
        "```python\nimport math\n```\n"
        "And here is the answer:\n"
        "```python\ndef add(a, b):\n    return a + b\n```\n"
    )
    extracted = extractCode(raw, "add")
    assert extracted.parsed is True
    assert "def add" in extracted.code
    assert "import math" not in extracted.code


def test_takesTheLastBlockWhenSeveralDefineTheEntryPoint() -> None:
    raw = (
        "A first draft:\n```python\ndef add(a, b):\n    return a - b\n```\n"
        "That was wrong. Corrected:\n```python\ndef add(a, b):\n    return a + b\n```\n"
    )
    extracted = extractCode(raw, "add")
    assert "return a + b" in extracted.code
    assert "return a - b" not in extracted.code


def test_extractsBareCodeWithNoFenceAtAll() -> None:
    extracted = extractCode("def add(a, b):\n    return a + b\n", "add")
    assert extracted.parsed is True
    assert extracted.strategy.startswith("bare")


def test_stripsLeadingProse() -> None:
    raw = "Sure! The fix is straightforward.\nWe just add them.\ndef add(a, b):\n    return a + b\n"
    extracted = extractCode(raw, "add")
    assert extracted.parsed is True
    assert extracted.code.startswith("def add")


def test_stripsTrailingProse() -> None:
    raw = "def add(a, b):\n    return a + b\nThat should pass all the tests now.\n"
    extracted = extractCode(raw, "add")
    assert extracted.parsed is True
    assert "That should pass" not in extracted.code


def test_dropsAnEarlierDuplicateDefinitionOfTheEntryPoint() -> None:
    raw = (
        "```python\n"
        "def add(a, b):\n"
        '    """Stub."""\n'
        "    pass\n"
        "\n"
        "def add(a, b):\n"
        "    return a + b\n"
        "```\n"
    )
    extracted = extractCode(raw, "add")
    assert extracted.parsed is True
    assert extracted.code.count("def add") == 1
    assert "return a + b" in extracted.code
    assert "dedupe" in extracted.strategy


def test_duplicatedDefinitionsStillGradeCorrectly() -> None:
    raw = (
        "```python\n"
        "def add(a, b):\n    return a - b\n\n"
        "def add(a, b):\n    return a + b\n"
        "```\n"
    )
    assert grade(raw).all_tests_pass is True


def test_dedupeLeavesUnrelatedHelpersAlone() -> None:
    code = "def helper(x):\n    return x\n\ndef add(a, b):\n    return a + b\n"
    deduped, changed = dedupeDefinitions(code, "add")
    assert changed is False
    assert deduped == code


def test_dedupeIsANoOpOnUnparseableCode() -> None:
    code = "def add(a, b)\n    return a + b\n"
    deduped, changed = dedupeDefinitions(code, "add")
    assert (deduped, changed) == (code, False)


def test_emptyModelOutputIsReportedNotGuessed() -> None:
    extracted = extractCode("", "add")
    assert extracted.parsed is False
    assert extracted.strategy == "empty"
    assert extracted.parse_error


def test_unrecoverableOutputReportsAParseErrorRatherThanRaising() -> None:
    extracted = extractCode("I'm sorry, I cannot help with that request.", "add")
    assert extracted.parsed is False
    assert extracted.parse_error


def test_extractionStrategyIsCarriedOntoTheGradeResult() -> None:
    raw = "```python\ndef add(a, b):\n    return a + b\n```"
    assert "fenced" in grade(raw).extraction_strategy


def test_extractionIsSkippableForAlreadyCleanCode() -> None:
    result = grade("def add(a, b):\n    return a + b\n", extract=False)
    assert result.all_tests_pass is True
    assert result.extraction_strategy == "verbatim"


# ---------------------------------------------------------------------------
# Public failure signal -- design section 5
# ---------------------------------------------------------------------------


def test_publicFailureSignalCarriesTracebackAndFirstFailingVisibleExample() -> None:
    result = grade("def add(a, b):\n    return a - b\n")
    signal = result.public_failure_signal
    assert signal.has_signal is True
    assert signal.example_call == "add(1, 2)"
    assert signal.expected_repr == "3"
    assert signal.actual_repr == "-1"
    assert "First failing visible example" in signal.text
    assert signal.traceback_text


def test_publicFailureSignalIsADistinctFieldNotDerivedFromHiddenTests() -> None:
    """A candidate that passes every visible example but fails a hidden one still
    yields a hidden-test failure, and a public signal that discloses no hidden case."""
    problem = addProblem(
        visible=[((1, 2), 3)],
        hidden=[((100, 100), 200)],
    )
    result = grade("def add(a, b):\n    return 3 if a == 1 else 0\n", problem)
    assert result.all_tests_pass is False
    assert result.tests_passed == 1
    assert result.public_failure_signal.has_signal is False
    assert "100" not in result.public_failure_signal.text


def test_passingCandidateHasNoPublicFailureSignal() -> None:
    signal = grade("def add(a, b):\n    return a + b\n").public_failure_signal
    assert signal.has_signal is False
    assert signal.traceback_text == ""


def test_syntaxFailureStillProducesAPublicSignalForTheNoneArm() -> None:
    """Design section 5 needs the slot filled in every arm, including unparseable
    attempt-1 output, or NONE and REAL stop being structurally identical."""
    result = grade("def add(a, b)\n    return a + b\n", extract=False)
    signal = result.public_failure_signal
    assert signal.has_signal is True
    assert "SyntaxError" in signal.traceback_text
    assert signal.example_call == "add(1, 2)"


def test_publicFailureSignalPicksTheFirstFailingVisibleTestNotTheFirstFailure() -> None:
    problem = addProblem(visible=[((1, 2), 3), ((5, 5), 10)], hidden=[])
    result = grade("def add(a, b):\n    return 3 if a == 1 else 0\n", problem)
    assert result.public_failure_signal.example_call == "add(5, 5)"


def test_buildPublicFailureSignalIsPureAndUsableOffline() -> None:
    problem = addProblem(visible=[((1, 2), 3)], hidden=[])
    signal = buildPublicFailureSignal(
        problem,
        [
            {
                "index": 0,
                "passed": False,
                "traceback": "AssertionError",
                "actual_repr": "9",
            }
        ],
    )
    assert signal.has_signal is True
    assert signal.actual_repr == "9"


def test_emptyPublicFailureSignalHasNoContent() -> None:
    signal = PublicFailureSignal.empty("nothing to report")
    assert signal.has_signal is False
    assert signal.text == "nothing to report"


# ---------------------------------------------------------------------------
# Oracle semantics carried over from EvalPlus
# ---------------------------------------------------------------------------


def test_floatToleranceIsAppliedWhenTheReferenceIsAFloat() -> None:
    problem = addProblem(visible=[((0.1, 0.2), 0.30000000000000004)], hidden=[])
    assert grade(
        "def add(a, b):\n    return round(a + b, 12)\n", problem
    ).all_tests_pass


def test_explicitAtolIsHonoured() -> None:
    problem = addProblem(visible=[((1, 2), 3.0)], hidden=[], atol=0.5)
    assert grade("def add(a, b):\n    return 3.4\n", problem).all_tests_pass is True


def test_typeMismatchIsNotToleratedAway() -> None:
    problem = addProblem(visible=[((1, 2), 3)], hidden=[])
    assert grade("def add(a, b):\n    return '3'\n", problem).all_tests_pass is False


# ---------------------------------------------------------------------------
# EvalPlus availability and problem lookup
# ---------------------------------------------------------------------------


def test_missingEvalPlusRaisesAnActionableErrorNotABareImportError(monkeypatch) -> None:
    for name in [
        key for key in sys.modules if key == "evalplus" or key.startswith("evalplus.")
    ]:
        monkeypatch.delitem(sys.modules, name, raising=False)
    monkeypatch.setitem(sys.modules, "evalplus", None)
    with pytest.raises(EvalPlusUnavailable) as excinfo:
        loadEvalPlusProblems("humaneval")
    message = str(excinfo.value)
    assert "pip install evalplus" in message
    assert "provider=" in message
    assert not isinstance(excinfo.value, ImportError)


def test_evalplusMissingMessageNamesTheInterpreterAndTheCause() -> None:
    rendered = EVALPLUS_MISSING_MESSAGE.format(executable="/x/python", cause="boom")
    assert "/x/python" in rendered
    assert "boom" in rendered


@pytest.mark.parametrize(
    "problem_id,expected",
    [("HumanEval/0", "humaneval"), ("Mbpp/2", "mbpp"), ("HumanEval/163", "humaneval")],
)
def test_datasetOfMapsTaskIds(problem_id: str, expected: str) -> None:
    assert datasetOf(problem_id) == expected


def test_datasetOfRejectsAnUnknownRoster() -> None:
    with pytest.raises(ProblemNotFound):
        datasetOf("SWEBench/1")


def test_loadEvalPlusProblemsRejectsAnUnknownDataset() -> None:
    with pytest.raises(ProblemNotFound):
        loadEvalPlusProblems("mbpp-lite")


# ---------------------------------------------------------------------------
# Result serialisability -- rows have to survive a batch write
# ---------------------------------------------------------------------------


def test_gradeResultFieldsAreJsonSerialisable() -> None:
    result = grade("def add(a, b):\n    return a - b\n")
    row = {
        "problem_id": result.problem_id,
        "all_tests_pass": result.all_tests_pass,
        "tests_passed": result.tests_passed,
        "tests_failed": result.tests_failed,
        "tests_total": result.tests_total,
        "timed_out": result.timed_out,
        "syntax_error": result.syntax_error,
        "first_failure_stderr": result.first_failure_stderr,
        "public_failure_signal": result.public_failure_signal.text,
        "failing_indices": list(result.failing_indices),
    }
    assert json.loads(json.dumps(row))["tests_failed"] == 3
