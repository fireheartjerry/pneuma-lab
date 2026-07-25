"""EvalPlus grading for the placebo-controlled code-repair experiment.

Grades one candidate Python solution against a problem's EvalPlus unit tests in an
isolated subprocess, and returns a frozen result that carries the two things the
study design (`docs/research/neurips-2026-workshop/25-placebo-selfreport-design.md`)
needs kept apart:

1.  the **hidden-test verdict** -- the secondary anchor outcome, all-pass over the
    full base+plus roster (design section 4);
2.  the **public failure signal** -- traceback plus the first failing *visible*
    example, which section 5 requires to be present in every arm of the attempt-2
    prompt so it cannot confound the payload contrast. It is a distinct field
    precisely because it must be constructible without ever looking at the hidden
    result.

Nothing here calls a model, and nothing here is an LLM judge: design section 6
forbids a judge in any primary, secondary, or manipulation check.

Execution isolation lives in ``_runner.py``, which the grader invokes as a plain
script. A candidate that hangs, segfaults, or calls ``os._exit`` costs one
subprocess and a recorded flag; it never takes down the batch.
"""

from __future__ import annotations

import ast
import os
import pickle
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

PER_TEST_TIMEOUT_SECONDS = 10.0
RUNNER_STARTUP_OVERHEAD_SECONDS = 20.0
BACKSTOP_SECONDS_PER_TEST = 0.5
MAX_TRAILING_TRIM_LINES = 40
MAX_LEADING_TRIM_LINES = 40
HUMANEVAL_DATASET = "humaneval"
MBPP_DATASET = "mbpp"
RUNNER_PATH = Path(__file__).resolve().parent / "_runner.py"

EVALPLUS_MISSING_MESSAGE = (
    "The placebo grader needs EvalPlus to load problem definitions and reference "
    "outputs, and it is not importable in this interpreter "
    "({executable}).\n"
    "Fix: `pip install evalplus`, then warm the dataset + ground-truth cache once "
    'with `python -c "from evalplus.data import get_human_eval_plus, get_mbpp_plus; '
    'get_human_eval_plus(); get_mbpp_plus()"`.\n'
    "The first call downloads HumanEvalPlus/MbppPlus and needs network access; "
    "every later call is offline.\n"
    "To grade without EvalPlus installed, pass an explicit `problem=GradingProblem(...)` "
    "or a `provider=` callable to gradeSolution().\n"
    "Underlying import error: {cause}"
)


class GraderError(RuntimeError):
    """Base class for grading failures that are the harness's fault, not the candidate's."""


class EvalPlusUnavailable(GraderError):
    """EvalPlus could not be imported or its data could not be loaded."""


class ProblemNotFound(GraderError):
    """The requested problem id is not in the EvalPlus roster."""


# ---------------------------------------------------------------------------
# Frozen result / problem records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestCase:
    """One EvalPlus input tuple and its reference output.

    ``visible`` marks the EvalPlus *base* inputs -- the examples that appear in the
    problem statement and that an agent is allowed to see. Plus inputs are hidden.
    """

    # Not a pytest class, despite the name: this is an EvalPlus unit test case.
    __test__ = False

    index: int
    args: tuple
    expected: Any
    visible: bool


@dataclass(frozen=True)
class GradingProblem:
    """Everything the grader needs about one problem, detached from EvalPlus."""

    problem_id: str
    dataset: str
    entry_point: str
    prompt: str
    atol: float
    tests: tuple[TestCase, ...]
    set_eq_oracle: bool = False
    not_none_oracle: bool = False

    @property
    def visible_tests(self) -> tuple[TestCase, ...]:
        return tuple(test for test in self.tests if test.visible)


@dataclass(frozen=True)
class PublicFailureSignal:
    """Traceback + first failing visible example. Safe to place in every arm's prompt.

    Derived only from visible (base) test cases, so injecting it into the attempt-2
    prompt leaks nothing about the hidden roster that decides the outcome.
    """

    has_signal: bool
    traceback_text: str
    example_call: str
    expected_repr: str
    actual_repr: str
    text: str

    @staticmethod
    def empty(note: str = "") -> "PublicFailureSignal":
        return PublicFailureSignal(
            has_signal=False,
            traceback_text="",
            example_call="",
            expected_repr="",
            actual_repr="",
            text=note,
        )


@dataclass(frozen=True)
class ExtractedCode:
    """Result of pulling a runnable program out of raw model output."""

    code: str
    strategy: str
    parsed: bool
    parse_error: str = ""


@dataclass(frozen=True)
class GradeResult:
    """Frozen verdict for one (problem, candidate) pair."""

    problem_id: str
    all_tests_pass: bool
    tests_passed: int
    tests_failed: int
    tests_total: int
    first_failure_stderr: str
    timed_out: bool
    syntax_error: bool
    public_failure_signal: PublicFailureSignal
    syntax_error_message: str = ""
    extraction_strategy: str = ""
    harness_error: str = ""
    per_test_timeout_s: float = PER_TEST_TIMEOUT_SECONDS
    failing_indices: tuple[int, ...] = field(default_factory=tuple)

    @property
    def graded(self) -> bool:
        """False when the harness itself failed, so the row must not enter analysis."""
        return not self.harness_error


# ---------------------------------------------------------------------------
# Code extraction
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(
    r"```[ \t]*([A-Za-z0-9_+#-]*)[ \t]*\r?\n(.*?)(?:\r?\n[ \t]*```|\Z)", re.DOTALL
)
_PYTHON_LANGS = {"", "python", "python3", "py", "pycon"}
_CODE_START_RE = re.compile(
    r"^(?:import\s|from\s+\S+\s+import|def\s|async\s+def\s|class\s|@\w|#!|"
    r"if\s+__name__|try\s*:|with\s|[A-Za-z_][A-Za-z_0-9]*\s*(?::[^=]+)?=[^=])"
)


def _parses(code: str) -> tuple[bool, str]:
    try:
        ast.parse(code)
    except (SyntaxError, ValueError) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    return True, ""


def dedupeDefinitions(code: str, entry_point: str | None = None) -> tuple[str, bool]:
    """Drop earlier top-level definitions shadowed by a later one of the same name.

    Models routinely echo the prompt stub and then emit the real implementation, or
    emit two drafts of the same function. Python already keeps the last binding, so
    this changes no semantics -- but it removes half-written earlier drafts whose
    presence turns a recoverable answer into a whole-module SyntaxError, and it keeps
    the graded artifact readable in the audit log.

    Returns ``(code, changed)``; a no-op when the module does not parse.
    """
    ok, _ = _parses(code)
    if not ok:
        return code, False
    tree = ast.parse(code)
    definitions: dict[str, list[ast.stmt]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.setdefault(node.name, []).append(node)

    drop_spans: list[tuple[int, int]] = []
    for name, nodes in definitions.items():
        if len(nodes) < 2:
            continue
        if entry_point is not None and name != entry_point:
            # Only rewrite the entry point unless we were given no hint at all;
            # a redefined helper may be intentional.
            continue
        for node in nodes[:-1]:
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            drop_spans.append((start, node.end_lineno))

    if not drop_spans:
        return code, False

    dropped = set()
    for start, end in drop_spans:
        dropped.update(range(start, end + 1))
    lines = code.splitlines()
    kept = [line for number, line in enumerate(lines, start=1) if number not in dropped]
    rebuilt = "\n".join(kept).strip("\n") + "\n"
    ok_after, _ = _parses(rebuilt)
    return (rebuilt, True) if ok_after else (code, False)


def _trimToParse(code: str) -> tuple[str, str] | None:
    """Shave leading prose then trailing prose until the module parses."""
    lines = code.splitlines()

    for skip in range(min(MAX_LEADING_TRIM_LINES, len(lines)) + 1):
        window = lines[skip:]
        if not window:
            break
        if skip and not _CODE_START_RE.match(window[0]):
            continue
        candidate = "\n".join(window)
        ok, _ = _parses(candidate)
        if ok and candidate.strip():
            return candidate, ("bare" if skip == 0 else "leading-trim")

    for skip in range(min(MAX_LEADING_TRIM_LINES, len(lines)) + 1):
        window = lines[skip:]
        if skip and not _CODE_START_RE.match(window[0] if window else ""):
            continue
        for drop in range(1, min(MAX_TRAILING_TRIM_LINES, len(window)) + 1):
            candidate = "\n".join(window[: len(window) - drop])
            if not candidate.strip():
                break
            ok, _ = _parses(candidate)
            if ok:
                return candidate, "trailing-trim" if skip == 0 else "both-trim"
    return None


def extractCode(raw_output: str, entry_point: str | None = None) -> ExtractedCode:
    """Pull a runnable program out of raw model output.

    Handles, explicitly and in this order: fenced blocks (tagged or bare, including
    an unterminated final fence), several fenced blocks where only one is the answer,
    bare code with no fence, leading prose, trailing prose, and duplicated definitions
    of the entry point. Extraction failure is a known and non-trivial source of
    spurious "repair failed" rows, so the chosen path is reported in
    ``ExtractedCode.strategy`` and carried into ``GradeResult.extraction_strategy``.
    """
    text = (raw_output or "").replace("\r\n", "\n")
    if not text.strip():
        return ExtractedCode(
            code="",
            strategy="empty",
            parsed=False,
            parse_error="model output was empty",
        )

    blocks = [
        (lang.lower(), body) for lang, body in _FENCE_RE.findall(text) if body.strip()
    ]
    python_blocks = [body for lang, body in blocks if lang in _PYTHON_LANGS]
    if blocks and not python_blocks:
        python_blocks = [body for _, body in blocks]

    if python_blocks:
        parsing = [body for body in python_blocks if _parses(body)[0]]
        with_entry = [
            body
            for body in parsing
            if entry_point is None
            or re.search(
                rf"^\s*(?:async\s+)?def\s+{re.escape(entry_point)}\b",
                body,
                re.MULTILINE,
            )
        ]
        # Prefer the last parsing block that defines the entry point: when a model
        # explains then answers, the answer comes last.
        if with_entry:
            chosen, strategy = with_entry[-1], "fenced"
        elif parsing:
            chosen, strategy = parsing[-1], "fenced-no-entry-point"
        else:
            joined = "\n".join(python_blocks)
            trimmed = _trimToParse(joined)
            if trimmed is not None:
                chosen, strategy = trimmed[0], f"fenced-{trimmed[1]}"
            else:
                longest = max(python_blocks, key=len)
                ok, err = _parses(longest)
                deduped, changed = dedupeDefinitions(longest, entry_point)
                return ExtractedCode(
                    code=deduped,
                    strategy="fenced-unparsed" + ("+dedupe" if changed else ""),
                    parsed=ok,
                    parse_error=err,
                )
    else:
        trimmed = _trimToParse(text)
        if trimmed is not None:
            chosen, strategy = trimmed
        else:
            ok, err = _parses(text)
            return ExtractedCode(code=text, strategy="raw", parsed=ok, parse_error=err)

    chosen = chosen.strip("\n") + "\n"
    deduped, changed = dedupeDefinitions(chosen, entry_point)
    ok, err = _parses(deduped)
    return ExtractedCode(
        code=deduped,
        strategy=strategy + ("+dedupe" if changed else ""),
        parsed=ok,
        parse_error=err,
    )


# ---------------------------------------------------------------------------
# EvalPlus problem loading
# ---------------------------------------------------------------------------

_PROBLEM_CACHE: dict[str, GradingProblem] = {}


def _importEvalPlus():
    try:
        from evalplus.data import (  # noqa: PLC0415
            get_human_eval_plus,
            get_human_eval_plus_hash,
            get_mbpp_plus,
            get_mbpp_plus_hash,
        )
        from evalplus.eval import (  # noqa: PLC0415
            MBPP_OUTPUT_NOT_NONE_TASKS,
            MBPP_OUTPUT_SET_EQ_TASKS,
        )
        from evalplus.evaluate import get_groundtruth  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 - any import-time failure must be actionable
        raise EvalPlusUnavailable(
            EVALPLUS_MISSING_MESSAGE.format(executable=sys.executable, cause=exc)
        ) from exc
    return {
        "get_human_eval_plus": get_human_eval_plus,
        "get_human_eval_plus_hash": get_human_eval_plus_hash,
        "get_mbpp_plus": get_mbpp_plus,
        "get_mbpp_plus_hash": get_mbpp_plus_hash,
        "get_groundtruth": get_groundtruth,
        "not_none_tasks": MBPP_OUTPUT_NOT_NONE_TASKS,
        "set_eq_tasks": MBPP_OUTPUT_SET_EQ_TASKS,
    }


def datasetOf(problem_id: str) -> str:
    """Map an EvalPlus task id onto its dataset name."""
    head = problem_id.split("/", 1)[0].strip().lower()
    if head in ("humaneval", "humanevalplus"):
        return HUMANEVAL_DATASET
    if head in ("mbpp", "mbppplus"):
        return MBPP_DATASET
    raise ProblemNotFound(
        f"cannot infer dataset from problem id {problem_id!r}; "
        "expected 'HumanEval/<n>' or 'Mbpp/<n>'"
    )


def loadEvalPlusProblems(dataset: str) -> dict[str, GradingProblem]:
    """Load and cache every ``GradingProblem`` for one EvalPlus dataset.

    Reference outputs come from EvalPlus's own ground-truth cache, so the verdict
    matches what a plain ``evalplus.evaluate`` run would report.
    """
    dataset = dataset.lower()
    if dataset not in (HUMANEVAL_DATASET, MBPP_DATASET):
        raise ProblemNotFound(f"unknown EvalPlus dataset {dataset!r}")

    api = _importEvalPlus()
    try:
        if dataset == HUMANEVAL_DATASET:
            problems = api["get_human_eval_plus"]()
            hashcode = api["get_human_eval_plus_hash"]()
        else:
            problems = api["get_mbpp_plus"]()
            hashcode = api["get_mbpp_plus_hash"]()
        expected = api["get_groundtruth"](problems, hashcode, api["not_none_tasks"])
    except EvalPlusUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001
        raise EvalPlusUnavailable(
            f"EvalPlus is installed but loading the {dataset} dataset or its "
            f"ground truth failed ({type(exc).__name__}: {exc}). The first load "
            "downloads the dataset and computes reference outputs, which needs "
            "network access and a writable cache dir."
        ) from exc

    loaded: dict[str, GradingProblem] = {}
    for task_id, problem in problems.items():
        oracle = expected[task_id]
        tests: list[TestCase] = []
        for args, out in zip(problem["base_input"], oracle["base"]):
            tests.append(TestCase(len(tests), tuple(args), out, visible=True))
        for args, out in zip(problem["plus_input"], oracle["plus"]):
            tests.append(TestCase(len(tests), tuple(args), out, visible=False))
        entry_point = problem["entry_point"]
        loaded[task_id] = GradingProblem(
            problem_id=task_id,
            dataset=dataset,
            entry_point=entry_point,
            prompt=problem["prompt"],
            atol=float(problem.get("atol") or 0.0),
            tests=tuple(tests),
            set_eq_oracle=entry_point in api["set_eq_tasks"],
            not_none_oracle=entry_point in api["not_none_tasks"],
        )
    _PROBLEM_CACHE.update(loaded)
    return loaded


def loadEvalPlusProblem(problem_id: str) -> GradingProblem:
    """Look up one problem, loading (and caching) its dataset on first use."""
    if problem_id in _PROBLEM_CACHE:
        return _PROBLEM_CACHE[problem_id]
    loaded = loadEvalPlusProblems(datasetOf(problem_id))
    if problem_id not in loaded:
        raise ProblemNotFound(f"{problem_id!r} is not in the EvalPlus roster")
    return loaded[problem_id]


# ---------------------------------------------------------------------------
# Public failure signal
# ---------------------------------------------------------------------------


def _renderCall(entry_point: str, args: Sequence[Any]) -> str:
    rendered = []
    for arg in args:
        try:
            rendered.append(repr(arg))
        except BaseException:  # noqa: BLE001
            rendered.append("<unreprable>")
    joined = ", ".join(rendered)
    if len(joined) > 400:
        joined = joined[:400] + " ..."
    return f"{entry_point}({joined})"


def buildPublicFailureSignal(
    problem: GradingProblem, per_test: Sequence[Mapping[str, Any]]
) -> PublicFailureSignal:
    """Assemble the traceback + first failing *visible* example.

    Design section 5 places this in every arm's attempt-2 prompt, including NONE, so
    the payload contrast is not confounded by whether the agent was told it failed.
    """
    by_index = {int(row["index"]): row for row in per_test}
    for test in problem.visible_tests:
        row = by_index.get(test.index)
        if row is None or row.get("passed"):
            continue
        traceback_text = str(row.get("traceback") or "").strip()
        stderr_text = str(row.get("stderr") or "").strip()
        if stderr_text:
            traceback_text = (traceback_text + "\n" + stderr_text).strip()
        call = _renderCall(problem.entry_point, test.args)
        expected_repr = repr(test.expected)
        actual_repr = str(row.get("actual_repr") or "")
        text = (
            "The previous attempt failed its tests.\n\n"
            f"{traceback_text}\n\n"
            "First failing visible example:\n"
            f"    {call}\n"
            f"    expected: {expected_repr}\n"
            f"    actual:   {actual_repr or '<no value returned>'}"
        )
        return PublicFailureSignal(
            has_signal=True,
            traceback_text=traceback_text,
            example_call=call,
            expected_repr=expected_repr,
            actual_repr=actual_repr,
            text=text,
        )
    return PublicFailureSignal.empty(
        "The previous attempt failed its tests, but every visible example passed."
    )


def _signalFromWholeModuleFailure(
    problem: GradingProblem, traceback_text: str, headline: str
) -> PublicFailureSignal:
    """Signal for candidates that never ran: syntax error, import error, missing name."""
    visible = problem.visible_tests
    call = _renderCall(problem.entry_point, visible[0].args) if visible else ""
    expected_repr = repr(visible[0].expected) if visible else ""
    text = f"{headline}\n\n{traceback_text}"
    if call:
        text += (
            "\n\nFirst visible example (never reached):\n"
            f"    {call}\n"
            f"    expected: {expected_repr}\n"
            "    actual:   <no value returned>"
        )
    return PublicFailureSignal(
        has_signal=True,
        traceback_text=traceback_text,
        example_call=call,
        expected_repr=expected_repr,
        actual_repr="",
        text=text,
    )


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def _backstopTimeout(n_tests: int, per_test_timeout: float) -> float:
    """Parent-side wall clock guard, in case the child's own watchdog never fires."""
    return (
        per_test_timeout
        + RUNNER_STARTUP_OVERHEAD_SECONDS
        + BACKSTOP_SECONDS_PER_TEST * n_tests
    )


def _runChild(
    payload: dict, timeout_s: float, python_executable: str
) -> tuple[dict | None, str]:
    """Run ``_runner.py`` on a temp payload. Returns ``(result, harness_error)``."""
    import json

    workdir = tempfile.mkdtemp(prefix="pneuma-placebo-")
    payload_path = os.path.join(workdir, "payload.pkl")
    result_path = os.path.join(workdir, "result.json")
    try:
        with open(payload_path, "wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
        try:
            completed = subprocess.run(
                [python_executable, str(RUNNER_PATH), payload_path, result_path],
                capture_output=True,
                timeout=timeout_s,
                cwd=workdir,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None, (
                f"TIMEOUT: the grading subprocess exceeded the {timeout_s:g}s parent "
                "backstop and was killed"
            )
        if not os.path.exists(result_path):
            stderr = (completed.stderr or b"").decode("utf-8", "replace")[-2000:]
            return None, (
                f"the grading subprocess exited with code {completed.returncode} "
                f"without writing a result: {stderr.strip() or '<no stderr>'}"
            )
        with open(result_path, "r", encoding="utf-8") as handle:
            return json.load(handle), ""
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    finally:
        for path in (payload_path, result_path):
            try:
                os.remove(path)
            except OSError:
                pass
        try:
            os.rmdir(workdir)
        except OSError:
            pass


def gradeSolution(
    problem_id: str,
    candidate_code: str,
    *,
    problem: GradingProblem | None = None,
    provider: Callable[[str], GradingProblem] | None = None,
    per_test_timeout_s: float = PER_TEST_TIMEOUT_SECONDS,
    total_timeout_s: float | None = None,
    python_executable: str | None = None,
    extract: bool = True,
) -> GradeResult:
    """Grade one candidate solution against a problem's EvalPlus tests.

    ``candidate_code`` may be raw model output; it is run through
    :func:`extractCode` unless ``extract=False``. Pass ``problem=`` or ``provider=``
    to grade without touching EvalPlus (used by the tests, and by any offline
    replay of a recorded batch).
    """
    if problem is None:
        lookup = provider or loadEvalPlusProblem
        problem = lookup(problem_id)

    if extract:
        extracted = extractCode(candidate_code, problem.entry_point)
    else:
        ok, err = _parses(candidate_code or "")
        extracted = ExtractedCode(
            code=candidate_code or "", strategy="verbatim", parsed=ok, parse_error=err
        )

    total = len(problem.tests)

    if not extracted.code.strip():
        message = (
            extracted.parse_error or "no code could be extracted from the model output"
        )
        return GradeResult(
            problem_id=problem.problem_id,
            all_tests_pass=False,
            tests_passed=0,
            tests_failed=total,
            tests_total=total,
            first_failure_stderr=message,
            timed_out=False,
            syntax_error=True,
            syntax_error_message=message,
            public_failure_signal=_signalFromWholeModuleFailure(
                problem, message, "The previous attempt produced no runnable code."
            ),
            extraction_strategy=extracted.strategy,
            per_test_timeout_s=per_test_timeout_s,
            failing_indices=tuple(test.index for test in problem.tests),
        )

    payload = {
        "code": extracted.code,
        "entry_point": problem.entry_point,
        "dataset": problem.dataset,
        "atol": problem.atol,
        "per_test_timeout": float(per_test_timeout_s),
        "set_eq_oracle": problem.set_eq_oracle,
        "not_none_oracle": problem.not_none_oracle,
        "tests": [
            {
                "index": test.index,
                "args": list(test.args),
                "expected": test.expected,
                "visible": test.visible,
            }
            for test in problem.tests
        ],
    }
    timeout_s = total_timeout_s or _backstopTimeout(total, per_test_timeout_s)
    raw, harness_error = _runChild(
        payload, timeout_s, python_executable or sys.executable
    )

    if raw is None:
        timed_out = harness_error.startswith("TIMEOUT:")
        return GradeResult(
            problem_id=problem.problem_id,
            all_tests_pass=False,
            tests_passed=0,
            tests_failed=total,
            tests_total=total,
            first_failure_stderr=harness_error,
            timed_out=timed_out,
            syntax_error=False,
            public_failure_signal=_signalFromWholeModuleFailure(
                problem, harness_error, "The previous attempt could not be graded."
            ),
            extraction_strategy=extracted.strategy,
            # A parent-backstop kill is a real candidate timeout; anything else is
            # ours, and `graded` must be False so the row stays out of analysis.
            harness_error="" if timed_out else harness_error,
            per_test_timeout_s=per_test_timeout_s,
            failing_indices=tuple(test.index for test in problem.tests),
        )

    if raw["syntax_error"]:
        message = raw["syntax_error_message"]
        return GradeResult(
            problem_id=problem.problem_id,
            all_tests_pass=False,
            tests_passed=0,
            tests_failed=total,
            tests_total=total,
            first_failure_stderr=message,
            timed_out=False,
            syntax_error=True,
            syntax_error_message=message,
            public_failure_signal=_signalFromWholeModuleFailure(
                problem, message, "The previous attempt did not parse as Python."
            ),
            extraction_strategy=extracted.strategy,
            per_test_timeout_s=per_test_timeout_s,
            failing_indices=tuple(test.index for test in problem.tests),
        )

    if raw["module_error"]:
        message = raw["module_error"]
        return GradeResult(
            problem_id=problem.problem_id,
            all_tests_pass=False,
            tests_passed=0,
            tests_failed=total,
            tests_total=total,
            first_failure_stderr=message,
            timed_out=False,
            syntax_error=False,
            public_failure_signal=_signalFromWholeModuleFailure(
                problem, message, "The previous attempt failed before any test ran."
            ),
            extraction_strategy=extracted.strategy,
            per_test_timeout_s=per_test_timeout_s,
            failing_indices=tuple(test.index for test in problem.tests),
        )

    per_test = raw["results"]
    passed = sum(1 for row in per_test if row["passed"])
    # Tests after an abort never ran; they count against the candidate, since the
    # abort is caused by the candidate hanging.
    failed = total - passed
    failing_indices = tuple(row["index"] for row in per_test if not row["passed"])
    first_failure = ""
    for row in per_test:
        if row["passed"]:
            continue
        first_failure = str(row.get("traceback") or "").strip()
        stderr_text = str(row.get("stderr") or "").strip()
        if stderr_text:
            first_failure = (first_failure + "\n" + stderr_text).strip()
        break

    all_pass = passed == total and not raw["timed_out"]
    signal = (
        PublicFailureSignal.empty("The previous attempt passed every visible example.")
        if all_pass
        else buildPublicFailureSignal(problem, per_test)
    )
    return GradeResult(
        problem_id=problem.problem_id,
        all_tests_pass=all_pass,
        tests_passed=passed,
        tests_failed=failed,
        tests_total=total,
        first_failure_stderr=first_failure,
        timed_out=bool(raw["timed_out"]),
        syntax_error=False,
        public_failure_signal=signal,
        extraction_strategy=extracted.strategy,
        per_test_timeout_s=per_test_timeout_s,
        failing_indices=failing_indices,
    )


__all__ = [
    "BACKSTOP_SECONDS_PER_TEST",
    "EVALPLUS_MISSING_MESSAGE",
    "EvalPlusUnavailable",
    "ExtractedCode",
    "GradeResult",
    "GraderError",
    "GradingProblem",
    "HUMANEVAL_DATASET",
    "MBPP_DATASET",
    "PER_TEST_TIMEOUT_SECONDS",
    "ProblemNotFound",
    "PublicFailureSignal",
    "RUNNER_PATH",
    "TestCase",
    "buildPublicFailureSignal",
    "datasetOf",
    "dedupeDefinitions",
    "extractCode",
    "gradeSolution",
    "loadEvalPlusProblem",
    "loadEvalPlusProblems",
]
