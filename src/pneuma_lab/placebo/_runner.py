"""Child-process test runner for the placebo grader. NOT imported by the parent.

This file is executed as a standalone script (``python <abs path> payload result``)
so the child never needs ``src/`` on its import path and never imports
``pneuma_lab``. It is stdlib-only apart from a lazy ``numpy`` import used for the
float-tolerance comparison.

Contract
--------
argv[1]  pickle payload written by ``grader.gradeSolution``
argv[2]  path the JSON result is written to

The payload is pickled rather than JSON-encoded because EvalPlus test inputs and
expected outputs contain tuples, sets, and other non-JSON types whose identity the
oracle depends on. It is NOT untrusted input: the parent writes it to a
process-private temp file microseconds earlier and deletes it on return, so the
unpickle is strictly a same-process-tree handoff. Nothing model-generated is ever
pickled -- the candidate solution travels as a plain string and is only ever
``compile``d, and the file is executed with the child's own interpreter, in an
already-isolated subprocess whose entire purpose is running that untrusted code.

Isolation model
---------------
The parent gives this process exactly one candidate solution. Each test case runs
on a daemon thread that the runner joins with a hard per-test timeout; a thread
that overruns cannot be killed, so the runner records the timeout, flushes what it
has, and hard-exits. That is what keeps a hanging candidate from wedging the batch.

Comparison semantics mirror ``evalplus.eval.unsafe_execute`` (exact match, then
float tolerance, plus the per-dataset special oracles). The parent resolves the
oracle membership so this file stays free of any evalplus import.
"""

from __future__ import annotations

import contextlib
import io
import math
import os
import pickle
import sys
import threading
import traceback

MAX_TRACEBACK_CHARS = 4000
MAX_REPR_CHARS = 600
FLOAT_ATOL_FLOOR = 1e-6
FLOAT_RTOL = 1e-07


# --- special oracles, ported verbatim from evalplus.eval._special_oracle ----


def _surfaceArea(base_edge, height):
    """Oracle for Mbpp/581: height is the perpendicular base-to-apex distance."""
    slant_height = math.sqrt((base_edge / 2) ** 2 + height**2)
    base_area = base_edge**2
    lateral_area = 4 * (base_edge * slant_height) / 2
    return round(base_area + lateral_area)


def _digitDistanceNums(num1, num2):
    """Oracle for Mbpp/558: zero-pad both numbers to equal length, sum |digit diffs|."""
    str_num1, str_num2 = str(num1), str(num2)
    max_length = max(len(str_num1), len(str_num2))
    str_num1, str_num2 = str_num1.zfill(max_length), str_num2.zfill(max_length)
    total_difference = 0
    for digit1, digit2 in zip(str_num1, str_num2):
        total_difference += abs(int(digit1) - int(digit2))
    return total_difference


def _poly(xs: list, x: float):
    """Oracle for HumanEval/32: evaluate the polynomial with coefficients ``xs``."""
    return sum([coeff * math.pow(x, i) for i, coeff in enumerate(xs)])


def isFloats(value) -> bool:
    """True for float, list[float], tuple[float], or a float numpy array."""
    if isinstance(value, float):
        return True
    if isinstance(value, (list, tuple)) and value:
        return all(isinstance(item, float) for item in value)
    numpy_module = sys.modules.get("numpy")
    if numpy_module is not None and isinstance(value, numpy_module.ndarray):
        return (
            value.dtype == numpy_module.float64 or value.dtype == numpy_module.float32
        )
    return False


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated, {len(text) - limit} more chars]"


def safeRepr(value) -> str:
    """repr() that can never itself raise or blow up the result file."""
    try:
        return _clip(repr(value), MAX_REPR_CHARS)
    except BaseException:  # noqa: BLE001 - a candidate's __repr__ may do anything
        return "<unreprable object>"


def matches(
    out,
    expected,
    *,
    entry_point: str,
    dataset: str,
    atol: float,
    args,
    set_eq_oracle: bool,
    not_none_oracle: bool,
) -> bool:
    """Mirror evalplus's per-test oracle. Raises on mismatch is avoided: returns bool."""
    exact_match = out == expected

    if dataset == "mbpp":
        if entry_point == "are_equivalent":  # Mbpp/164
            return True
        if entry_point == "sum_div":  # Mbpp/295
            exact_match = exact_match or out == 0
        elif entry_point == "surface_Area":  # Mbpp/581
            exact_match = exact_match or abs(out - _surfaceArea(*args)) <= atol
        elif entry_point == "digit_distance_nums":  # Mbpp/558
            exact_match = exact_match or out == _digitDistanceNums(*args)
        elif set_eq_oracle:
            return set(out) == set(expected)
        elif not_none_oracle:
            # ``expected`` is True when the reference output was not None.
            if isinstance(out, bool):
                return out == expected
            return expected == (out is not None)

    if dataset == "humaneval" and entry_point == "find_zero":  # HumanEval/32
        return abs(_poly(*args, out)) <= atol

    if exact_match:
        return True

    # evalplus mutates its shared ``atol`` here; we keep it test-local so one
    # float-valued case cannot silently loosen every later case.
    test_atol = FLOAT_ATOL_FLOOR if (atol == 0 and isFloats(expected)) else atol
    if test_atol == 0:
        return False

    import numpy  # lazy: only float-tolerance comparisons need it

    if type(out) is not type(expected):
        return False
    if isinstance(expected, (list, tuple)) and len(out) != len(expected):
        return False
    try:
        return bool(numpy.allclose(out, expected, rtol=FLOAT_RTOL, atol=test_atol))
    except BaseException:  # noqa: BLE001 - ragged / non-numeric inputs
        return False


class _TestOutcome:
    """Mutable box a worker thread fills; the main thread reads it after join()."""

    def __init__(self) -> None:
        self.completed = False
        self.passed = False
        self.actual_repr = ""
        self.traceback_text = ""
        self.stderr_text = ""


def runOneTest(payload: dict, fn, test: dict, outcome: _TestOutcome) -> None:
    """Body of the worker thread: call the candidate and grade one input tuple."""
    captured_out, captured_err = io.StringIO(), io.StringIO()
    try:
        args = test["args"]
        with (
            contextlib.redirect_stdout(captured_out),
            contextlib.redirect_stderr(captured_err),
        ):
            out = fn(*args)
        outcome.actual_repr = safeRepr(out)
        outcome.passed = matches(
            out,
            test["expected"],
            entry_point=payload["entry_point"],
            dataset=payload["dataset"],
            atol=payload["atol"],
            args=args,
            set_eq_oracle=payload["set_eq_oracle"],
            not_none_oracle=payload["not_none_oracle"],
        )
        if not outcome.passed:
            outcome.traceback_text = (
                f"AssertionError: output does not match the expected value\n"
                f"  expected: {safeRepr(test['expected'])}\n"
                f"  actual:   {outcome.actual_repr}"
            )
    except BaseException:  # noqa: BLE001 - candidate code may raise anything
        outcome.traceback_text = _clip(traceback.format_exc(), MAX_TRACEBACK_CHARS)
        outcome.passed = False
    finally:
        outcome.stderr_text = _clip(captured_err.getvalue(), MAX_TRACEBACK_CHARS)
        outcome.completed = True


def _writeResult(result_path: str, result: dict) -> None:
    import json

    with open(result_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle)
        handle.flush()
        os.fsync(handle.fileno())


def main(argv: list) -> int:
    payload_path, result_path = argv[1], argv[2]
    with open(payload_path, "rb") as handle:
        payload = pickle.load(handle)

    result = {
        "syntax_error": False,
        "syntax_error_message": "",
        "module_error": "",
        "results": [],
        "timed_out": False,
        "aborted_at": None,
    }

    code = payload["code"]
    try:
        compiled = compile(code, "<candidate>", "exec")
    except (SyntaxError, ValueError) as exc:
        result["syntax_error"] = True
        result["syntax_error_message"] = _clip(
            "".join(traceback.format_exception_only(type(exc), exc)).strip(),
            MAX_TRACEBACK_CHARS,
        )
        _writeResult(result_path, result)
        return 0

    namespace: dict = {"__name__": "__candidate__"}
    captured_out, captured_err = io.StringIO(), io.StringIO()
    try:
        with (
            contextlib.redirect_stdout(captured_out),
            contextlib.redirect_stderr(captured_err),
        ):
            exec(compiled, namespace)  # noqa: S102 - grading a candidate is the point
        fn = namespace[payload["entry_point"]]
        if not callable(fn):
            raise TypeError(
                f"{payload['entry_point']!r} is defined but is not callable"
            )
    except KeyError:
        result["module_error"] = (
            f"NameError: the solution does not define {payload['entry_point']!r}"
        )
        _writeResult(result_path, result)
        return 0
    except BaseException:  # noqa: BLE001
        result["module_error"] = _clip(traceback.format_exc(), MAX_TRACEBACK_CHARS)
        _writeResult(result_path, result)
        return 0

    per_test_timeout = float(payload["per_test_timeout"])
    for test in payload["tests"]:
        outcome = _TestOutcome()
        worker = threading.Thread(
            target=runOneTest, args=(payload, fn, test, outcome), daemon=True
        )
        worker.start()
        worker.join(per_test_timeout)
        if not outcome.completed:
            result["results"].append(
                {
                    "index": test["index"],
                    "visible": test["visible"],
                    "passed": False,
                    "timed_out": True,
                    "traceback": (
                        f"TimeoutError: test case {test['index']} exceeded "
                        f"{per_test_timeout:g}s"
                    ),
                    "stderr": "",
                    "actual_repr": "",
                }
            )
            result["timed_out"] = True
            result["aborted_at"] = test["index"]
            _writeResult(result_path, result)
            # The overrunning thread is unkillable; leave immediately rather than
            # letting interpreter shutdown block on it.
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(0)
        result["results"].append(
            {
                "index": test["index"],
                "visible": test["visible"],
                "passed": outcome.passed,
                "timed_out": False,
                "traceback": outcome.traceback_text,
                "stderr": outcome.stderr_text,
                "actual_repr": outcome.actual_repr,
            }
        )

    _writeResult(result_path, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
