from __future__ import annotations

import copy
import json
import os

import pytest

from pneuma_lab.adapters import envelope as env
from pneuma_lab.adapters import openhands_verifier as ov
from pneuma_lab.schemas import validate

FIXTURE = os.path.join("fixtures", "adapters", "openhands_verifier")
REV = "d47f6cab996d3a5f7ba517c0be57595f4f6201ce"
SRC = "fixtures/adapters/openhands_verifier/input_rows.jsonl"


def _jsonl(name):
    with open(os.path.join(FIXTURE, name), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _rows():
    return _jsonl("input_rows.jsonl")


def _trace(row_idx: int):
    rows = _rows()
    row = rows[row_idx]
    variant = row["policy_variant"]
    # source_row = index within the row's policy-variant batch (per-file index
    # in production, where each variant is one parquet).
    source_row = sum(1 for r in rows[:row_idx] if r["policy_variant"] == variant)
    return ov.build_trace(row, variant, REV, SRC, source_row)


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
    assert trace["labels"]["policy_variant"] == "mixture"
    assert trace["trajectory"]["num_agent_steps"] == 2
    assert trace["trajectory"]["policy_variant"] == "mixture"
    assert trace["trajectory"]["agent_run_id"] == "verifier::mixture::0"
    assert trace["provenance"]["source_id"] == "verifier::mixture::0"
    assert trace["outcome"] == {"kind": "swe-gym-verifier-label", "resolved": True}
    kinds = [f["frame_kind"] for f in trace["frames"]]
    assert kinds == ["world", "governance", "agent_trace", "agent_trace"]


def test_objective_is_redacted_but_real():
    trace = _trace(0)
    text = trace["frames"][0]["objective"]["text"]
    assert "dev@example.com" not in text
    assert "[REDACTED:email]" in text
    assert "off-by-one" in text  # real task text survives
    assert trace["privacy"]["status"] == "redacted"
    assert {"kind": "email", "count": 1} in trace["privacy"]["redactions"]
    assert trace["privacy"]["pii_scanned"] is True


def test_no_task_join_is_possible_and_stays_honest():
    trace = _trace(0)
    assert trace["provenance"]["task_join"] == {
        "hf_repo": "SWE-Gym/SWE-Gym",
        "joined": False,
        "reason": "no instance_id column in source",
    }
    assert "instance_id" not in trace["labels"]  # source has none; never guessed
    assert trace["labels"]["repo"] == ""
    assert trace["labels"]["has_patch"] is False
    assert trace["labels"]["has_tests"] is False
    assert trace["oracle"] == {
        "kind": "test-based",
        "fail_to_pass": [],
        "pass_to_pass": [],
    }
    assert trace["reference_supervision"] == {}
    assert trace["frames"][0]["repo_state"] == {"repo": ""}


def test_failed_run_keeps_observable_failure_shape():
    trace = _trace(1)
    assert _fully_valid(trace) == []
    assert trace["labels"]["resolved"] is False
    assert trace["outcome"] == {"kind": "swe-gym-verifier-label", "resolved": False}
    agent_frames = [f for f in trace["frames"] if f["frame_kind"] == "agent_trace"]
    assert agent_frames[1]["retry_count"] == 1  # identical bash call repeated
    assert agent_frames[0]["observations"][0]["error_marker"] is True


def test_other_policy_variant_gets_distinct_identity():
    trace = _trace(2)
    assert _fully_valid(trace) == []
    assert trace["labels"]["policy_variant"] == "onpolicy"
    assert trace["provenance"]["source_id"] == "verifier::onpolicy::0"
    assert trace["trace_id"] != _trace(0)["trace_id"]
    assert trace["trajectory"]["num_agent_steps"] == 1


def test_unusable_messages_skip_row():
    row = _rows()[3]
    with pytest.raises(ov.SkipRow):
        ov.build_trace(row, row["policy_variant"], REV, SRC, 0)


def test_policy_variant_parsed_from_file_name():
    for variant in ov.POLICY_VARIANTS:
        path = (
            "C:/pneuma-data/raw/swe-gym/OpenHands-Verifier-Trajectories/data/"
            f"train.{variant}-00000-of-00001.parquet"
        )
        assert ov.policy_variant_from_path(path) == variant
    with pytest.raises(ValueError):
        ov.policy_variant_from_path("train.mystery-00000-of-00001.parquet")


def test_run_counts_quarantine_and_report():
    files = ov.run(ov._fixture_batches(), hf_revision=REV)
    report = json.loads(files["adapter_report.json"])
    assert report["counts"] == {
        "source_rows": 4,
        "traces_emitted": 3,
        "valid": 3,
        "invalid": 0,
        "skipped": 1,
    }
    assert report["trajectory"]["traces_with_task_join"] == 0
    assert report["trajectory"]["traces_missing_task_join"] == 3
    assert report["trajectory"]["resolved_true"] == 2
    assert report["trajectory"]["resolved_false"] == 1
    assert report["trajectory"]["by_policy_variant"] == {
        "mixture": {"valid": 2, "resolved_true": 1, "resolved_false": 1},
        "onpolicy": {"valid": 1, "resolved_true": 1, "resolved_false": 0},
    }
    (skip_entry,) = report["skipped_source_ids"]
    assert skip_entry["source_id"] == "verifier::offpolicy::0"
    assert skip_entry["reason"].startswith("unusable messages")
    assert {"kind": "email", "count": 1} in report["privacy"]["redaction_totals"]
    index = [json.loads(l) for l in files["trace_index.jsonl"].splitlines()]
    assert [r["num_agent_steps"] for r in index] == [2, 3, 1]
    assert [r["policy_variant"] for r in index] == ["mixture", "mixture", "onpolicy"]
    assert files["pneuma_traces.invalid.jsonl"] == ""


def test_raw_trajectory_text_never_reaches_agent_frames():
    trace = _trace(0)
    agent_blob = env.canonical_json(
        [f for f in trace["frames"] if f["frame_kind"] == "agent_trace"]
    )
    assert "pytest -x" not in agent_blob
    assert "2 passed" not in agent_blob
    assert "RESOLVED" not in agent_blob


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
