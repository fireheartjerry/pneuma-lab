"""Frozen attempt-1 sweep over the study pool.

One initial attempt per problem at temperature 0 under a single preregistered seed.
Only problems the model fails enter the study; each becomes one failure tuple.

Per `25-placebo-selfreport-design.md` section 11, this must be **one** attempt per
problem. Generating several attempts and keeping whichever seeds happened to fail
selects on the outcome and is regression-to-the-mean soup.

The output manifest is the frozen population. Nothing downstream may add to it,
and the digest exists so a silent redraw is detectable.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ATTEMPT1_SEED = 20260724
CALIBRATION_SLICE_SIZE = 40


@dataclass(frozen=True)
class AttemptRecord:
    """One problem's initial attempt. Recorded whether it passed or failed."""

    problem_id: str
    source: str
    passed: bool
    tests_passed: int
    tests_total: int
    timed_out: bool
    syntax_error: bool
    public_failure_signal: str
    latency_s: float
    output_tokens: int
    output_digest: str


def digestOf(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def buildStudyPool(human_eval: dict, mbpp: dict) -> tuple[dict, dict]:
    """Split the pooled roster into a calibration slice and the study pool.

    The calibration slice is taken from the front of the sorted MBPP+ ids so that
    it matches the slice the model-selection preflight already consumed. Study
    problems must be disjoint from it: a model chosen on a problem cannot then be
    evaluated on that same problem.
    """
    calibration_ids = sorted(mbpp)[:CALIBRATION_SLICE_SIZE]
    calibration = {pid: mbpp[pid] for pid in calibration_ids}
    study = {pid: item for pid, item in sorted(human_eval.items())}
    study.update(
        {pid: item for pid, item in sorted(mbpp.items()) if pid not in calibration}
    )
    return study, calibration


def writeFailurePool(records: list[AttemptRecord], path: Path, model: str) -> dict:
    """Freeze the failure pool. The digest makes a silent redraw detectable."""
    failures = [r for r in records if not r.passed]
    body = {
        "schema_version": "pneuma-placebo-failure-pool/1.0.0",
        "model": model,
        "attempt1_seed": ATTEMPT1_SEED,
        "calibration_slice_size": CALIBRATION_SLICE_SIZE,
        "n_study_problems": len(records),
        "n_failures": len(failures),
        "failure_rate": round(len(failures) / max(len(records), 1), 4),
        "note": (
            "One frozen attempt per problem at temperature 0. Problems are NOT "
            "resampled and failures are NOT reselected. Nothing downstream may add "
            "to this pool."
        ),
        "failure_ids": [r.problem_id for r in failures],
        "records": [asdict(r) for r in records],
    }
    payload = json.dumps(body, indent=2, sort_keys=True)
    body["pool_digest"] = digestOf(payload)
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return body


def summarize(records: list[AttemptRecord]) -> dict:
    """Counts by source, so a per-benchmark stratum is available downstream."""
    out: dict = {}
    for source in sorted({r.source for r in records}):
        rows = [r for r in records if r.source == source]
        failed = [r for r in rows if not r.passed]
        out[source] = {
            "n": len(rows),
            "failures": len(failed),
            "failure_rate": round(len(failed) / max(len(rows), 1), 4),
            "timeouts": sum(1 for r in rows if r.timed_out),
            "syntax_errors": sum(1 for r in rows if r.syntax_error),
        }
    return out
