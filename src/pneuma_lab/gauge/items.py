"""Item loading and executable ground truth.

Correctness labels in this study are established by *running* hidden tests, not by
annotation. That matters twice over: it makes the reference bank's labels
auditable, and it lets the self-authored provenance arm be labelled the same way
as the foreign arm, so the two arms are comparable.

Execution happens in a subprocess with a hard timeout so a non-terminating
candidate is reported as a failure instead of hanging the run. Candidates come
from local models solving toy pure-function tasks; the subprocess boundary and
the timeout are the containment, and no candidate is ever imported into this
process.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .bank import bankItems

_DRIVER = """
import json, sys
_payload = json.loads({payload!r})
def _canon(v):
    # JSON has no tuple, so expected values arrive as lists. Compare structurally.
    if isinstance(v, (list, tuple)):
        return [_canon(x) for x in v]
    if isinstance(v, dict):
        return {{k: _canon(x) for k, x in v.items()}}
    return v

_ns = {{}}
try:
    exec(_payload["source"], _ns)
except Exception as exc:
    print(json.dumps({{"passed": False, "detail": "load error: " + repr(exc)}}))
    sys.exit(0)
fn = _ns.get(_payload["entry"])
if not callable(fn):
    print(json.dumps({{"passed": False, "detail": "missing entry point " + _payload["entry"]}}))
    sys.exit(0)
for args, expected in _payload["tests"]:
    try:
        got = fn(*args)
    except Exception as exc:
        print(json.dumps({{"passed": False, "detail": "raised on " + repr(args) + ": " + repr(exc)}}))
        sys.exit(0)
    if _canon(got) != _canon(expected):
        print(json.dumps({{"passed": False, "detail": "on " + repr(args) + " expected " + repr(expected) + " got " + repr(got)}}))
        sys.exit(0)
print(json.dumps({{"passed": True, "detail": "all {{}} hidden tests passed".format(len(_payload["tests"]))}}))
"""


@dataclass(frozen=True)
class TestOutcome:
    passed: bool
    detail: str


def runHiddenTests(
    source: str, entry: str, tests: list, *, timeout: float = 10.0
) -> TestOutcome:
    """Execute `source` against hidden tests in a subprocess. Never raises on candidate failure."""
    payload = json.dumps({"source": source, "entry": entry, "tests": _normalize(tests)})
    script = _DRIVER.format(payload=payload)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "driver.py"
        path.write_text(script, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-S", str(path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
            )
        except subprocess.TimeoutExpired:
            return TestOutcome(False, f"timed out after {timeout}s")
    line = (proc.stdout or "").strip().splitlines()
    if not line:
        return TestOutcome(
            False, f"no output (exit {proc.returncode}): {(proc.stderr or '')[:200]}"
        )
    try:
        result = json.loads(line[-1])
    except ValueError:
        return TestOutcome(False, f"unparseable driver output: {line[-1][:200]}")
    return TestOutcome(bool(result["passed"]), str(result["detail"]))


def _normalize(tests) -> list:
    """Accept tuple- or list-shaped tests; JSON round-trips tuples to lists."""
    out = []
    for entry in tests:
        args, expected = entry[0], entry[1]
        out.append([list(args), expected])
    return out


def loadItems() -> list[dict]:
    """The 48-item reference bank, deterministic order."""
    return bankItems()


def truthLabels(items: list[dict]) -> dict[str, int]:
    return {item["item_id"]: int(item["label"]) for item in items}


def verifyBank(items: list[dict] | None = None, *, timeout: float = 10.0) -> list[dict]:
    """Run every item against its hidden tests and return per-item outcomes."""
    items = items if items is not None else loadItems()
    report = []
    for item in items:
        outcome = runHiddenTests(
            item["source"], item["entry"], item["hidden_tests"], timeout=timeout
        )
        report.append(
            {
                "item_id": item["item_id"],
                "expected_pass": item["label"] == 1,
                "passed": outcome.passed,
                "detail": outcome.detail,
                "agrees": outcome.passed == (item["label"] == 1),
            }
        )
    return report


__all__ = ["TestOutcome", "loadItems", "runHiddenTests", "truthLabels", "verifyBank"]
