"""The elicitation runner, exercised entirely offline through the `chat` seam."""

from __future__ import annotations

import pytest

from pneuma_lab.gauge.elicit import (
    SCALES,
    WORDINGS,
    ElicitError,
    authorSolutions,
    buildJobs,
    elicit,
)
from pneuma_lab.gauge.items import loadItems

ITEMS = loadItems()[:4]


def _stub(reply: str):
    def chat(messages, **kw):
        return reply

    return chat


def test_job_count_is_the_full_product():
    jobs = buildJobs(
        ITEMS,
        models=["a", "b"],
        wordings=WORDINGS[:3],
        scales=SCALES[:2],
        arms=("base", "sham"),
        provenances=("foreign",),
        replicates=4,
    )
    assert len(jobs) == 4 * 2 * 3 * 2 * 2 * 1 * 4


def test_jobs_are_grouped_by_model():
    jobs = buildJobs(
        ITEMS, models=["a", "b"], wordings=WORDINGS[:2], scales=SCALES[:1], replicates=2
    )
    models = [j.model for j in jobs]
    assert models == sorted(models, key=lambda m: 0 if m == "a" else 1)
    assert models[: len(models) // 2] == ["a"] * (len(models) // 2)


def test_seeds_are_deterministic_and_distinct_per_cell():
    jobs = buildJobs(
        ITEMS, models=["a"], wordings=WORDINGS[:2], scales=SCALES[:2], replicates=3
    )
    seeds = [j.seed for j in jobs]
    assert len(set(seeds)) == len(seeds)
    again = buildJobs(
        ITEMS, models=["a"], wordings=WORDINGS[:2], scales=SCALES[:2], replicates=3
    )
    assert [j.seed for j in again] == seeds


def test_elicit_produces_one_response_per_job_and_is_reproducible(tmp_path):
    jobs = buildJobs(
        ITEMS, models=["a"], wordings=WORDINGS[:2], scales=SCALES[:1], replicates=2
    )
    first = elicit(jobs, chat=_stub("0.85"), workers=4)
    second = elicit(jobs, chat=_stub("0.85"), workers=4)
    assert len(first) == len(jobs)
    assert (
        first.toJsonl(tmp_path / "a.jsonl").read_bytes()
        == second.toJsonl(tmp_path / "b.jsonl").read_bytes()
    )
    assert first.parseFailureRate() == 0.0


def test_unparseable_replies_are_retained_not_dropped():
    jobs = buildJobs(
        ITEMS, models=["a"], wordings=WORDINGS[:1], scales=SCALES[:1], replicates=2
    )
    cube = elicit(jobs, chat=_stub("I cannot say"), workers=2)
    assert len(cube) == len(jobs)
    assert cube.parseFailureRate() == 1.0
    assert all(r.raw_text == "I cannot say" for r in cube.rows)


def test_backend_errors_degrade_the_run_instead_of_losing_it():
    def broken(messages, **kw):
        raise ElicitError("connection refused")

    jobs = buildJobs(
        ITEMS, models=["a"], wordings=WORDINGS[:1], scales=SCALES[:1], replicates=2
    )
    cube = elicit(jobs, chat=broken, workers=2)
    assert len(cube) == len(jobs)
    assert all("backend error" in r.raw_text for r in cube.rows)


def test_self_authored_jobs_require_a_solution():
    jobs = buildJobs(
        ITEMS,
        models=["a"],
        wordings=WORDINGS[:1],
        scales=SCALES[:1],
        provenances=("self_authored",),
        replicates=1,
    )
    missing = elicit(jobs, chat=_stub("0.9"), workers=2)
    assert all("missing self-authored solution" in r.raw_text for r in missing.rows)

    solutions = {("a", item["item_id"]): "def f():\n    return 1" for item in ITEMS}
    supplied = elicit(jobs, chat=_stub("0.9"), solutions=solutions, workers=2)
    assert supplied.parseFailureRate() == 0.0


def test_author_solutions_returns_one_per_spec():
    reply = "```python\ndef median(xs):\n    return sorted(xs)[len(xs) // 2]\n```"
    out = authorSolutions(ITEMS, model="a", chat=_stub(reply), workers=2)
    assert set(out) == {item["spec_id"] for item in ITEMS}
    assert all(v.startswith("def ") for v in out.values())


def test_author_solutions_records_generation_failure_instead_of_raising():
    def broken(messages, **kw):
        raise ElicitError("down")

    out = authorSolutions(ITEMS, model="a", chat=broken, workers=2)
    assert all(v.startswith("# generation failed") for v in out.values())


def test_scale_and_wording_facets_reach_the_cube():
    jobs = buildJobs(
        ITEMS, models=["a"], wordings=WORDINGS[:3], scales=SCALES, replicates=2
    )
    cube = elicit(jobs, chat=_stub("0.5"), workers=4)
    assert set(cube.values("wording_id")) == {"w1", "w2", "w3"}
    assert set(cube.values("scale_id")) == {"p2", "pct", "ten", "five"}
    # "0.5" is only valid on the p2 scale; the rest are scale non-compliance.
    assert cube.parseFailureRate() == pytest.approx(0.75)
