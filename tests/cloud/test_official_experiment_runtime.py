from __future__ import annotations

from types import SimpleNamespace

from pneuma_lab.cloud.official_experiment import (
    _SWE_TOOL_OUTPUT_CHARS,
    _task_span,
    DockerSweRuntime,
)


def test_swe_shell_output_is_context_bounded() -> None:
    payload = ("a" * 20_000).encode()
    container = SimpleNamespace(
        exec_run=lambda *_args, **_kwargs: SimpleNamespace(
            output=payload,
            exit_code=0,
        )
    )

    return_code, output = DockerSweRuntime.exec(container, "true")

    assert return_code == 0
    assert "context-safe truncation" in output
    assert len(output) < _SWE_TOOL_OUTPUT_CHARS + 100


def test_task_span_emits_structured_start_and_completion(capsys) -> None:
    with _task_span("swe:repo__task-1", "model_request", call_index=2):
        pass

    rows = [__import__("json").loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row["phase"] for row in rows] == [
        "model_request_started",
        "model_request_completed",
    ]
    assert all(row["task_id"] == "swe:repo__task-1" for row in rows)
    assert all(row["call_index"] == 2 for row in rows)
