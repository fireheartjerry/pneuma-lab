from __future__ import annotations

import json

import pytest

from pneuma_lab.adapters import envelope as env
from pneuma_lab.adapters import trajectory as traj
from pneuma_lab.schemas import validate

RUN_ID = "run:0123abcd"

USER_TEXT = "Fix the parser crash reported in issue 42."
TOOL_OUT_FAIL = "Error: Traceback (most recent call last): ValueError"
TOOL_OUT_OK = "3 passed in 0.12s"
FINAL_TEXT = "All tests pass now."


def _call(name: str, arguments: str, call_id: str) -> dict:
    return {
        "function": {"name": name, "arguments": arguments},
        "id": call_id,
        "index": 0,
        "type": "function",
    }


def _messages() -> list[dict]:
    return [
        {"role": "system", "content": "You are an agent."},
        {"role": "user", "content": USER_TEXT},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [_call("execute_bash", '{"command": "pytest"}', "c1")],
        },
        {"role": "tool", "content": TOOL_OUT_FAIL},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [_call("execute_bash", '{"command": "pytest"}', "c2")],
        },
        {"role": "tool", "content": TOOL_OUT_FAIL},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [_call("str_replace_editor", '{"path": "a.py"}', "c3")],
        },
        {"role": "tool", "content": TOOL_OUT_OK},
        {"role": "assistant", "content": FINAL_TEXT},
    ]


def test_step_grouping_counts_and_schema_validity():
    out = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)
    assert out["num_messages"] == 9
    assert out["num_agent_steps"] == 4
    assert out["first_user_text"] == USER_TEXT
    assert len(out["frames"]) == 4
    for frame in out["frames"]:
        assert validate.iter_errors(frame) == []
    # observations attach to the step that caused them
    assert len(out["frames"][0]["observations"]) == 1
    assert out["frames"][3]["observations"] == []


def test_retry_count_and_strategy_switches():
    frames = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)["frames"]
    # step 1 repeats step 0's exact (tool, args) set
    assert frames[0]["retry_count"] == 0
    assert frames[1]["retry_count"] == 1
    # step 2 switches tool -> no retry, one switch; step 3 has no tool call
    assert frames[2]["retry_count"] == 0
    assert frames[0]["strategy_switches"] == 0
    assert frames[1]["strategy_switches"] == 0
    assert frames[2]["strategy_switches"] == 1
    assert frames[3]["strategy_switches"] == 2


def test_error_marker_is_lexical():
    frames = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)["frames"]
    assert frames[0]["observations"][0]["error_marker"] is True
    assert frames[2]["observations"][0]["error_marker"] is False


def test_synthetic_ordinal_timestamps():
    frames = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)["frames"]
    assert frames[0]["timestamp"] == "1970-01-01T00:00:00+00:00"
    assert frames[2]["timestamp"] == "1970-01-01T00:00:02+00:00"
    assert all(f["timestamp_provenance"] == "synthetic-ordinal" for f in frames)


def test_frames_never_embed_raw_text():
    out = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)
    blob = env.canonical_json(out["frames"])
    for raw in (USER_TEXT, TOOL_OUT_FAIL, TOOL_OUT_OK, FINAL_TEXT, "pytest"):
        assert raw not in blob
    # but the observable action identity IS present
    assert "execute_bash" in blob
    assert "str_replace_editor" in blob


def test_phase_is_observational_only():
    frames = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)["frames"]
    assert [f["phase"] for f in frames] == [
        "execution",
        "execution",
        "execution",
        "other",
    ]


def test_extraction_is_deterministic():
    a = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)
    b = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)
    assert a == b


def test_redact_text_email_and_token():
    clean, ledger = traj.redact_text("mail bob@corp.example and use ghp_" + "a" * 30)
    assert "bob@corp.example" not in clean
    assert "ghp_" + "a" * 30 not in clean
    assert "[REDACTED:email]" in clean
    assert "[REDACTED:github_token]" in clean
    kinds = {item["kind"]: item["count"] for item in ledger}
    assert kinds == {"email": 1, "github_token": 1}


def test_merge_redactions_sums_and_sorts():
    merged = traj.merge_redactions(
        [
            [{"kind": "email", "count": 2}],
            [{"kind": "aws_access_key", "count": 1}, {"kind": "email", "count": 1}],
        ]
    )
    assert merged == [
        {"kind": "aws_access_key", "count": 1},
        {"kind": "email", "count": 3},
    ]


def test_args_digest_stable():
    assert traj.args_digest('{"a": 1}') == traj.args_digest('{"a": 1}')
    assert traj.args_digest('{"a": 1}') != traj.args_digest('{"a": 2}')


def test_no_assistant_step_raises():
    with pytest.raises(ValueError):
        traj.extract_agent_trace_frames(
            [{"role": "user", "content": "hi"}], run_id=RUN_ID
        )


def test_messages_accepts_json_string():
    as_string = json.dumps(_messages())
    a = traj.extract_agent_trace_frames(as_string, run_id=RUN_ID)
    b = traj.extract_agent_trace_frames(_messages(), run_id=RUN_ID)
    assert a == b
