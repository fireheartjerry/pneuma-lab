from __future__ import annotations

import copy
import json
import os

import pytest

from pneuma_lab.adapters import envelope as env
from pneuma_lab.adapters import openhands_sampled as oh
from pneuma_lab.schemas import validate

FIXTURE = os.path.join("fixtures", "adapters", "openhands_sampled")
REV = "baf3a4e4bff514d48ddc08a93a2ade5c126212c7"
SRC = "fixtures/adapters/openhands_sampled/input_rows.jsonl"


def _jsonl(name):
    with open(os.path.join(FIXTURE, name), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _rows():
    return _jsonl("input_rows.jsonl")


def _task_index():
    return oh.build_task_index(_jsonl("task_rows.jsonl"))


def _trace(row_idx: int):
    row = _rows()[row_idx]
    task = _task_index().get(row["instance_id"])
    return oh.build_trace(row, task, REV, SRC, row_idx)


def _fully_valid(trace) -> list[str]:
    errs = env.envelope_errors(trace) + env.consistency_errors(trace)
    errs += [e for f in trace["frames"] for e in validate.iter_errors(f)]
    return errs


def test_resolved_trace_is_fully_valid():
    trace = _trace(0)
    assert _fully_valid(trace) == []
    assert trace["schema_version"] == "0.2.0"
    assert trace["labels"]["has_trajectory"] is True
    assert trace["labels"]["resolved"] is True
    assert trace["trajectory"]["num_agent_steps"] == 3
    assert trace["trajectory"]["agent_run_id"] == "fixture-run_1"
    assert trace["outcome"]["resolved"] is True
    assert trace["outcome"]["report"]["resolved"] is True
    assert trace["outcome"]["git_patch_length"] > 0
    kinds = [f["frame_kind"] for f in trace["frames"]]
    assert kinds == ["world", "governance", "agent_trace", "agent_trace", "agent_trace"]


def test_objective_is_redacted_but_real():
    trace = _trace(0)
    text = trace["frames"][0]["objective"]["text"]
    assert "dev@example.com" not in text
    assert "[REDACTED:email]" in text
    assert "off-by-one" in text  # real task text survives
    assert trace["privacy"]["status"] == "redacted"
    assert {"kind": "email", "count": 1} in trace["privacy"]["redactions"]
    assert trace["privacy"]["pii_scanned"] is True


def test_task_join_supplies_oracle_and_head_sha():
    trace = _trace(0)
    assert trace["provenance"]["task_join"]["joined"] is True
    assert trace["frames"][0]["repo_state"]["head_sha"] == "a" * 40
    assert trace["oracle"]["fail_to_pass"] == ["tests/test_alpha.py::test_count"]
    assert trace["labels"]["has_patch"] is True
    assert trace["labels"]["has_tests"] is True
    sup = trace["reference_supervision"]
    assert set(sup) == {"gold_patch_sha256", "test_patch_sha256"}


def test_missing_task_join_stays_honest():
    trace = _trace(2)
    assert _fully_valid(trace) == []
    assert trace["provenance"]["task_join"]["joined"] is False
    assert trace["labels"]["repo"] == "demo/beta"  # parsed from instance_id
    assert trace["oracle"]["fail_to_pass"] == []
    assert trace["labels"]["has_patch"] is False
    assert trace["reference_supervision"] == {}
    assert "head_sha" not in trace["frames"][0]["repo_state"]
    # no harness dict at all -> outcome still records the resolved label only
    assert trace["outcome"] == {"kind": "swe-gym-harness-report", "resolved": False}


def test_failed_run_keeps_observable_failure_shape():
    trace = _trace(1)
    assert _fully_valid(trace) == []
    assert trace["labels"]["resolved"] is False
    assert trace["outcome"]["report"]["empty_generation"] is True
    agent_frames = [f for f in trace["frames"] if f["frame_kind"] == "agent_trace"]
    assert agent_frames[1]["retry_count"] == 1  # identical bash call repeated
    assert agent_frames[0]["observations"][0]["error_marker"] is True


def test_unusable_messages_skip_row():
    row = _rows()[3]
    with pytest.raises(oh.SkipRow):
        oh.build_trace(row, None, REV, SRC, 3)


def test_run_counts_quarantine_and_report():
    files = oh.run([(SRC, _rows())], _task_index(), hf_revision=REV)
    report = json.loads(files["adapter_report.json"])
    assert report["counts"] == {
        "source_rows": 4,
        "traces_emitted": 3,
        "valid": 3,
        "invalid": 0,
        "skipped": 1,
    }
    assert report["trajectory"]["traces_with_task_join"] == 2
    assert report["trajectory"]["traces_missing_task_join"] == 1
    assert report["trajectory"]["resolved_true"] == 1
    assert {"kind": "email", "count": 1} in report["privacy"]["redaction_totals"]
    index = [json.loads(l) for l in files["trace_index.jsonl"].splitlines()]
    assert [r["num_agent_steps"] for r in index] == [3, 3, 1]
    assert files["pneuma_traces.invalid.jsonl"] == ""


def test_raw_trajectory_text_never_reaches_agent_frames():
    trace = _trace(0)
    agent_blob = env.canonical_json(
        [f for f in trace["frames"] if f["frame_kind"] == "agent_trace"]
    )
    assert "pytest -x" not in agent_blob
    assert "replacement applied" not in agent_blob
    assert "Fixed the loop bound" not in agent_blob


# ---- anti-fake-cognition consistency gate ----------------------------------


def test_gate_rejects_agent_frames_without_trajectory_block():
    trace = _trace(0)
    broken = copy.deepcopy(trace)
    del broken["trajectory"]
    errs = env.consistency_errors(broken)
    assert any("fabricated cognition" in e for e in errs)


def test_gate_rejects_label_mismatch():
    trace = _trace(0)
    broken = copy.deepcopy(trace)
    broken["labels"]["has_trajectory"] = False
    assert any("has_trajectory" in e for e in env.consistency_errors(broken))


def test_gate_rejects_step_count_mismatch():
    trace = _trace(0)
    broken = copy.deepcopy(trace)
    broken["trajectory"]["num_agent_steps"] = 99
    assert any("num_agent_steps" in e for e in env.consistency_errors(broken))


def test_gate_rejects_undeclared_frame_source():
    trace = _trace(0)
    broken = copy.deepcopy(trace)
    del broken["build"]["frame_sources"]["agent-trace-frame"]
    assert any("frame_sources" in e for e in env.consistency_errors(broken))


def test_gate_rejects_fake_memory_frame():
    trace = _trace(0)
    broken = copy.deepcopy(trace)
    broken["frames"].append({"frame_kind": "memory", "schema_version": "0.1.0"})
    assert any("memory-frame" in e for e in env.consistency_errors(broken))


def test_task_only_v01_traces_still_pass():
    from pneuma_lab.adapters import swe_gym_lite as swe

    with open(
        os.path.join("fixtures", "adapters", "swe_gym_lite", "input_rows.jsonl"),
        encoding="utf-8",
    ) as fh:
        rows = [json.loads(line) for line in fh if line.strip()]
    files = swe.run(rows, hf_revision="rev", source_file="f")
    for line in files["pneuma_traces.jsonl"].splitlines():
        trace = json.loads(line)
        assert env.envelope_errors(trace) == []
        assert env.consistency_errors(trace) == []
