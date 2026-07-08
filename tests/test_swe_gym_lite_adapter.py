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
