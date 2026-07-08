from __future__ import annotations

import pytest

from pneuma_lab.adapters import swe_gym_lite as swe
from pneuma_lab.schemas import validate


SAMPLE_ROW = {
    "instance_id": "getmoto__moto-5752",
    "repo": "getmoto/moto",
    "base_commit": "b2300f1eae1323e3e8bc45f97e530ce129dff12e",
    "version": "4.0",
    "created_at": "2022-12-10 20:23:01",
    "problem_statement": "describe_parameters depends on filter order",
    "patch": "diff --git a/moto/ssm/models.py b/moto/ssm/models.py\n@@ -1 +1 @@\n-x\n+y\n",
    "test_patch": "diff --git a/tests/x.py b/tests/x.py\n@@ -1 +1 @@\n-a\n+b\n",
    "hints_text": "Here's the culprit",
    "FAIL_TO_PASS": ["tests/x.py::test_a"],
    "PASS_TO_PASS": ["tests/x.py::test_b"],
}


def test_normalize_created_at():
    assert (
        swe.normalize_created_at("2022-12-10 20:23:01") == "2022-12-10T20:23:01+00:00"
    )


def test_normalize_created_at_iso_z():
    # SWE-Gym-Lite created_at is inconsistent: some rows are ISO-8601 with 'Z'.
    assert (
        swe.normalize_created_at("2020-04-02T01:00:02Z") == "2020-04-02T01:00:02+00:00"
    )
    # space-separated naive still works (unchanged contract)
    assert (
        swe.normalize_created_at("2022-12-10 20:23:01") == "2022-12-10T20:23:01+00:00"
    )


def test_as_list_handles_json_string_and_list():
    assert swe.as_list('["a","b"]') == ["a", "b"]
    assert swe.as_list(["a", "b"]) == ["a", "b"]
    assert swe.as_list(None) == []


def test_world_frame_validates():
    f = swe.build_world_frame(
        SAMPLE_ROW, run_id="run:abc", timestamp="2022-12-10T20:23:01+00:00"
    )
    assert f["frame_kind"] == "world"
    assert validate.iter_errors(f) == []
    assert f["repo_state"]["head_sha"] == SAMPLE_ROW["base_commit"]
    assert f["test_state"] == {"ran": False, "not_yet_run": True}


def test_governance_frame_validates():
    f = swe.build_governance_frame(
        run_id="run:abc", timestamp="2022-12-10T20:23:01+00:00"
    )
    assert f["frame_kind"] == "governance"
    assert f["verifier_isolation"] is True
    assert f["kill_switch_state"] == "off"
    assert validate.iter_errors(f) == []


from pneuma_lab.adapters import envelope as env


def test_build_trace_structure_and_validation():
    trace = swe.build_trace(
        SAMPLE_ROW,
        hf_revision="f70b1a29",
        source_file="raw/.../train.parquet",
        source_row=0,
    )
    assert trace["trace_id"].startswith("ptrace:")
    assert trace["run_id"].startswith("run:")
    assert trace["labels"]["has_patch"] is True
    assert trace["labels"]["benchmark"] == "swe-gym-lite"
    assert trace["oracle"]["fail_to_pass"] == ["tests/x.py::test_a"]
    assert trace["reference_supervision"]["gold_patch"] == SAMPLE_ROW["patch"]
    assert trace["reference_supervision"]["hints_text"] == "Here's the culprit"
    assert (
        trace["build"]["frame_sources"]["governance-frame"]
        == "synthetic-contract-minimum"
    )
    assert [f["frame_kind"] for f in trace["frames"]] == ["world", "governance"]
    # content hash recomputes to the stored value
    assert env.content_hash(trace) == trace["build"]["content_hash"]
    # whole envelope validates
    assert env.envelope_errors(trace) == []
    # each frame validates against its existing schema
    for f in trace["frames"]:
        assert validate.iter_errors(f) == []


def test_build_trace_skips_row_missing_base_commit():
    bad = dict(SAMPLE_ROW)
    del bad["base_commit"]
    with pytest.raises(swe.SkipRow) as ei:
        swe.build_trace(bad, hf_revision="f70b1a29", source_file="f", source_row=1)
    assert "base_commit" in str(ei.value)


def _rows():
    r2 = dict(
        SAMPLE_ROW, instance_id="aaa__lib-1", hints_text=""
    )  # sorts first, no hints
    r3 = dict(SAMPLE_ROW, instance_id="zzz__lib-9")  # sorts last
    return [SAMPLE_ROW, r2, r3]


def test_run_counts_sort_and_determinism():
    out1 = swe.run(_rows(), hf_revision="f70b1a29", source_file="f.parquet")
    out2 = swe.run(_rows(), hf_revision="f70b1a29", source_file="f.parquet")
    assert out1 == out2  # byte-identical across runs

    import json as _json

    report = _json.loads(out1["adapter_report.json"])
    assert report["counts"] == {
        "source_rows": 3,
        "traces_emitted": 3,
        "valid": 3,
        "invalid": 0,
        "skipped": 0,
    }
    assert report["ordering"] == {
        "emission_sort_key": "instance_id",
        "source_row_preserved": True,
    }
    assert report["oracle_coverage"]["hints_present"] == 2  # r2 has empty hints
    # traces sorted by instance_id
    ids = [
        _json.loads(l)["labels"]["instance_id"]
        for l in out1["pneuma_traces.jsonl"].splitlines()
    ]
    assert ids == ["aaa__lib-1", "getmoto__moto-5752", "zzz__lib-9"]
    # index rows carry the required fields
    idx0 = _json.loads(out1["trace_index.jsonl"].splitlines()[0])
    assert idx0["frame_kinds"] == ["world-frame", "governance-frame"]
    assert idx0["content_hash"]


def test_run_skips_unbuildable_row():
    bad = dict(SAMPLE_ROW, instance_id="bad__row-1")
    del bad["base_commit"]
    out = swe.run(_rows() + [bad], hf_revision="f70b1a29", source_file="f.parquet")
    import json as _json

    report = _json.loads(out["adapter_report.json"])
    assert report["counts"]["skipped"] == 1
    assert report["skipped_source_ids"] == [
        {"source_id": "bad__row-1", "reason": "missing base_commit"}
    ]
