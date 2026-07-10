from __future__ import annotations

import copy
import json
import os

import pytest

from pneuma_lab.adapters import envelope as env
from pneuma_lab.adapters import open_swe_traces as a
from pneuma_lab.schemas import validate

FIXTURE = os.path.join("fixtures", "adapters", "open_swe_traces")
REV = a.HF_REVISION
SF = "fixtures/adapters/open_swe_traces/input_rows.jsonl"


def _rows() -> list[dict]:
    with open(os.path.join(FIXTURE, "input_rows.jsonl"), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _trace(row_idx: int) -> dict:
    row = _rows()[row_idx]
    return a.build_trace(row, row["_source_group"], SF, row_idx, REV)


def _fully_valid(trace) -> list[str]:
    errs = env.envelope_errors(trace) + env.consistency_errors(trace)
    errs += [e for f in trace["frames"] for e in validate.iter_errors(f)]
    return errs


def test_resolved_trace_is_fully_valid() -> None:
    trace = _trace(0)
    assert _fully_valid(trace) == []
    assert trace["schema_version"] == "0.2.0"
    assert trace["labels"]["has_trajectory"] is True
    assert trace["labels"]["resolved"] is True
    assert trace["trajectory"]["num_agent_steps"] == 3
    assert trace["outcome"]["resolved"] is True
    kinds = [f["frame_kind"] for f in trace["frames"]]
    assert kinds == ["world", "governance", "agent_trace", "agent_trace", "agent_trace"]


def test_resolved_int_maps_to_bool() -> None:
    assert a.resolved_to_bool(1) is True
    assert a.resolved_to_bool(0) is False


@pytest.mark.parametrize("bad", [-1, 2, None, "1"])
def test_unknown_resolved_is_skipped(bad) -> None:
    with pytest.raises(a.SkipRow):
        a.resolved_to_bool(bad)


def test_minus_one_resolved_row_skips_end_to_end() -> None:
    row = _rows()[2]  # gamma, resolved == -1
    assert row["resolved"] == -1
    with pytest.raises(a.SkipRow):
        a.build_trace(row, row["_source_group"], SF, 2, REV)


def test_no_assistant_step_skips() -> None:
    row = _rows()[3]  # delta, only system+user
    with pytest.raises(a.SkipRow):
        a.build_trace(row, row["_source_group"], SF, 3, REV)


def test_objective_is_digest_only_never_raw_text() -> None:
    obj = _trace(0)["frames"][0]["objective"]
    assert obj["mode"] == "digest_only"
    assert obj["present"] is True
    assert obj["text_sha256"].startswith("sha256:")
    assert obj["text_length"] > 0
    assert "text" not in obj  # raw text never embedded


def test_identifiers_and_repo_are_digested_in_frames_and_labels() -> None:
    trace = _trace(0)
    labels = trace["labels"]
    assert labels["repo_digest"].startswith("sha256:")
    assert labels["instance_id_digest"].startswith("sha256:")
    assert labels["trajectory_id_digest"].startswith("sha256:")
    assert trace["frames"][0]["repo_state"] == {"repo_digest": labels["repo_digest"]}
    fl = json.dumps({"frames": trace["frames"], "labels": labels})
    for raw in ("demo/alpha", "demo__alpha-1", "traj-alpha-0001"):
        assert raw not in fl


def test_raw_trajectory_and_patch_text_never_reach_frames() -> None:
    trace = _trace(0)
    blob = json.dumps(
        {
            "frames": trace["frames"],
            "labels": trace["labels"],
            "reference_supervision": trace["reference_supervision"],
        }
    )
    for raw in (
        "pytest -x",
        "replacement applied",
        "count.py",
        "diff --git",
        "dev@example.com",
    ):
        assert raw not in blob


def test_reference_supervision_is_patch_digest_only() -> None:
    ref = _trace(0)["reference_supervision"]
    for key in ("reference_patch", "model_patch"):
        assert set(ref[key]) == {
            "sha256",
            "length",
            "num_modified_files",
            "num_modified_lines",
        }
        assert ref[key]["sha256"].startswith("sha256:")
        assert "patch" not in ref[key]


def test_failed_run_keeps_observable_failure_shape() -> None:
    trace = _trace(1)  # beta, resolved 0, repeated identical build
    assert _fully_valid(trace) == []
    assert trace["labels"]["resolved"] is False
    frames = [f for f in trace["frames"] if f["frame_kind"] == "agent_trace"]
    assert frames[1]["retry_count"] == 1  # identical go build repeated
    assert frames[0]["observations"][0]["error_marker"] is True


def test_run_counts_skips_and_report() -> None:
    rows = _rows()
    batches: dict = {}
    for row in rows:
        batches.setdefault((row["_source_group"], SF), []).append(row)
    batch_list = [(sg, sf, rs) for (sg, sf), rs in sorted(batches.items())]
    files = a.run(batch_list, hf_revision=REV)
    report = json.loads(files["adapter_report.json"])
    assert report["counts"] == {
        "source_rows": 4,
        "traces_emitted": 2,
        "valid": 2,
        "invalid": 0,
        "skipped": 2,
    }
    assert report["trajectory"]["resolved_true"] == 1
    assert report["trajectory"]["resolved_false"] == 1
    assert report["privacy"]["raw_trajectory_text_embedded"] is False
    assert files["pneuma_traces.invalid.jsonl"] == ""
    reasons = {s["reason"].split("(")[0].strip() for s in report["skipped_source_ids"]}
    assert any("resolved is unknown" in r for r in reasons)


def test_default_inputs_cover_all_84_shards() -> None:
    inputs = a.default_inputs()
    assert len(inputs) == 84
    groups = {g for g, _ in inputs}
    assert groups == set(a.SOURCE_GROUP_SHARDS)


# ---- anti-fake-cognition consistency gate ----------------------------------


def test_gate_rejects_agent_frames_without_trajectory_block() -> None:
    broken = copy.deepcopy(_trace(0))
    del broken["trajectory"]
    assert any("fabricated cognition" in e for e in env.consistency_errors(broken))


def test_gate_rejects_step_count_mismatch() -> None:
    broken = copy.deepcopy(_trace(0))
    broken["trajectory"]["num_agent_steps"] = 99
    assert any("num_agent_steps" in e for e in env.consistency_errors(broken))
