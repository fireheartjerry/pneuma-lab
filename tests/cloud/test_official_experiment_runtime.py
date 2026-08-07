from __future__ import annotations

from types import SimpleNamespace

from pneuma_lab.cloud.official_experiment import (
    _SWE_TOOL_OUTPUT_CHARS,
    _TELEMETRY_ERROR_CHARS,
    _task_span,
    _vllm_seed,
    DockerSweRuntime,
    VllmChatClient,
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

    rows = [
        __import__("json").loads(line) for line in capsys.readouterr().out.splitlines()
    ]
    assert [row["phase"] for row in rows] == [
        "model_request_started",
        "model_request_completed",
    ]
    assert all(row["task_id"] == "swe:repo__task-1" for row in rows)
    assert all(row["call_index"] == 2 for row in rows)


def test_vllm_seed_preserves_uint64_bits_in_signed_api_domain() -> None:
    assert _vllm_seed(0) == 0
    assert _vllm_seed(2**63 - 1) == 2**63 - 1
    assert _vllm_seed(2**63) == -(2**63)
    assert _vllm_seed(2**64 - 1) == -1
    for seed in (0, 1, 2**63 - 1, 2**63, 2**64 - 1):
        assert _vllm_seed(seed) % 2**64 == seed


def test_task_span_emits_bounded_failure_detail(capsys) -> None:
    try:
        with _task_span("swe:repo__task-2", "model_request"):
            raise RuntimeError("diagnostic " + "x" * 2_000)
    except RuntimeError:
        pass

    rows = [
        __import__("json").loads(line) for line in capsys.readouterr().out.splitlines()
    ]
    failure = rows[-1]
    assert failure["phase"] == "model_request_failed"
    assert failure["error_type"] == "RuntimeError"
    assert failure["error_detail"].startswith("diagnostic ")
    assert len(failure["error_detail"]) == _TELEMETRY_ERROR_CHARS


def test_vllm_client_adapts_uint64_seed_at_http_boundary(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class Response:
        ok = True

        @staticmethod
        def json() -> dict[str, object]:
            return {
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"completion_tokens": 1},
            }

    def post(_endpoint, *, json, timeout):
        captured.update(json)
        assert timeout == 5
        return Response()

    monkeypatch.setattr("requests.post", post)
    result = VllmChatClient("http://model", request_timeout=5).generate(
        model="model",
        messages=[{"role": "user", "content": "test"}],
        tools=None,
        seed=2**64 - 1,
        sampling={"temperature": 0.5, "top_p": 1.0, "top_k": 0},
        max_tokens=8,
    )

    assert captured["seed"] == -1
    assert result["generated_tokens"] == 1
