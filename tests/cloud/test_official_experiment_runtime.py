from __future__ import annotations

from types import SimpleNamespace

from pneuma_lab.cloud.official_experiment import (
    _SWE_TOOL_OUTPUT_CHARS,
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
