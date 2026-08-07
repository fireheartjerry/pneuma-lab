from __future__ import annotations

from types import SimpleNamespace

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.official_experiment import (
    _DOCKER_API_TIMEOUT_SECONDS,
    _DOCKER_MAX_COMMAND_SECONDS,
    _DOCKER_PULL_ATTEMPTS,
    _SWE_GRADER_LOG_CHARS,
    _SWE_TOOL_OUTPUT_CHARS,
    _TELEMETRY_ERROR_CHARS,
    _task_span,
    _vllm_seed,
    DockerSweRuntime,
    VllmChatClient,
)


def test_docker_transport_budget_covers_longest_command_budget() -> None:
    """Regression: r8 died at task 103/120 on docker-py's 60s read default.

    `grade` grants test commands 3,600 seconds, so any transport budget at or
    below that guarantees a mid-run `ReadTimeout` on the essential worker.
    """

    assert _DOCKER_API_TIMEOUT_SECONDS > _DOCKER_MAX_COMMAND_SECONDS
    assert _DOCKER_MAX_COMMAND_SECONDS >= 3_600


def test_docker_client_is_built_with_the_explicit_transport_budget(
    monkeypatch, tmp_path
) -> None:
    captured: dict[str, object] = {}

    def from_env(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setitem(
        __import__("sys").modules, "docker", SimpleNamespace(from_env=from_env)
    )
    DockerSweRuntime(
        run_root=tmp_path,
        worker_id="worker-0",
        parser_image="benchmark-image",
        host_run_root=str(tmp_path),
    )

    assert captured["timeout"] == _DOCKER_API_TIMEOUT_SECONDS


def test_command_budget_above_the_transport_budget_fails_fast() -> None:
    container = SimpleNamespace(
        exec_run=lambda *_args, **_kwargs: SimpleNamespace(output=b"", exit_code=0)
    )

    with pytest.raises(CloudManifestError, match="Docker transport budget"):
        DockerSweRuntime.exec(
            container, "true", seconds=_DOCKER_MAX_COMMAND_SECONDS + 1
        )


def test_image_pull_retries_transient_failure_then_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(
        "pneuma_lab.cloud.official_experiment.time.sleep", lambda _seconds: None
    )
    attempts: list[str] = []

    def pull(image_ref: str) -> None:
        attempts.append(image_ref)
        if len(attempts) < _DOCKER_PULL_ATTEMPTS:
            raise ConnectionError("registry flake")

    runtime = object.__new__(DockerSweRuntime)
    runtime.client = SimpleNamespace(images=SimpleNamespace(pull=pull))
    runtime._lock = __import__("threading").Lock()

    runtime.pull("benchmark-image")

    assert len(attempts) == _DOCKER_PULL_ATTEMPTS


def test_image_pull_raises_after_the_attempt_limit(monkeypatch) -> None:
    monkeypatch.setattr(
        "pneuma_lab.cloud.official_experiment.time.sleep", lambda _seconds: None
    )
    attempts: list[str] = []

    def pull(image_ref: str) -> None:
        attempts.append(image_ref)
        raise ConnectionError("registry down")

    runtime = object.__new__(DockerSweRuntime)
    runtime.client = SimpleNamespace(images=SimpleNamespace(pull=pull))
    runtime._lock = __import__("threading").Lock()

    with pytest.raises(ConnectionError):
        runtime.pull("benchmark-image")

    assert len(attempts) == _DOCKER_PULL_ATTEMPTS


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


def test_swe_internal_grader_output_can_use_larger_parse_bound() -> None:
    payload = ("a" * (_SWE_TOOL_OUTPUT_CHARS + 1)).encode()
    container = SimpleNamespace(
        exec_run=lambda *_args, **_kwargs: SimpleNamespace(
            output=payload,
            exit_code=0,
        )
    )

    _, output = DockerSweRuntime.exec(
        container, "true", output_chars=_SWE_GRADER_LOG_CHARS
    )

    assert "context-safe truncation" not in output
    assert len(output) == len(payload)


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


def test_swe_parser_overrides_production_image_entrypoint(tmp_path) -> None:
    captured: dict[str, object] = {}

    class Child:
        @staticmethod
        def wait(timeout):
            assert timeout == 120
            return {"StatusCode": 0}

        @staticmethod
        def logs():
            return b""

        @staticmethod
        def remove(*, force):
            assert force is True

    class Containers:
        @staticmethod
        def run(_image, **kwargs):
            captured.update(kwargs)
            output = tmp_path / "parser" / "30cc437973967f87758d" / "output.json"
            output.write_text("{}\n", encoding="utf-8")
            return Child()

    runtime = object.__new__(DockerSweRuntime)
    runtime.run_root = tmp_path
    runtime.host_run_root = str(tmp_path)
    runtime.parser_image = "benchmark-image"
    runtime.client = SimpleNamespace(containers=Containers())

    assert (
        runtime._parse_log(
            "def parser(log): return {}", "", task_id="swe:cthackers__adm-zip-559"
        )
        == {}
    )
    assert captured["entrypoint"] == [
        "python3",
        "-m",
        "pneuma_lab.cloud.swe_parser_sandbox",
    ]
    assert captured["command"] == ["/sandbox/request.json", "/sandbox/output.json"]


def test_simulator_rpc_response_path_polls_faster_than_the_coarse_barrier() -> None:
    """Regression: the RPC hot path must not inherit the 10s barrier interval.

    It runs once per simulator turn across the whole TAU phase, so a coarse
    interval would add hours of pure polling latency.
    """

    from pneuma_lab.cloud.official_experiment import (
        _BARRIER_POLL_SECONDS,
        _SIMULATOR_RPC_POLL_SECONDS,
    )

    assert _SIMULATOR_RPC_POLL_SECONDS < _BARRIER_POLL_SECONDS
    assert _SIMULATOR_RPC_POLL_SECONDS <= 1.0


def test_wait_for_uses_the_requested_poll_interval(monkeypatch) -> None:
    from pneuma_lab.cloud.official_experiment import CoordinationStore

    store = object.__new__(CoordinationStore)
    slept: list[float] = []
    seen: dict[str, int] = {"calls": 0}

    def exists(_relative: str) -> bool:
        seen["calls"] += 1
        return seen["calls"] > 2

    monkeypatch.setattr("pneuma_lab.cloud.official_experiment.time.sleep", slept.append)
    store.exists = exists  # type: ignore[method-assign]

    CoordinationStore.wait_for(
        store,
        ["k.json"],
        deadline=__import__("time").monotonic() + 60,
        poll_seconds=0.5,
    )

    assert slept and all(value == 0.5 for value in slept)


def test_wait_for_defaults_to_the_coarse_barrier_interval(monkeypatch) -> None:
    from pneuma_lab.cloud.official_experiment import (
        _BARRIER_POLL_SECONDS,
        CoordinationStore,
    )

    store = object.__new__(CoordinationStore)
    slept: list[float] = []
    seen: dict[str, int] = {"calls": 0}

    def exists(_relative: str) -> bool:
        seen["calls"] += 1
        return seen["calls"] > 1

    monkeypatch.setattr("pneuma_lab.cloud.official_experiment.time.sleep", slept.append)
    store.exists = exists  # type: ignore[method-assign]

    CoordinationStore.wait_for(
        store, ["k.json"], deadline=__import__("time").monotonic() + 60
    )

    assert slept == [_BARRIER_POLL_SECONDS]


def test_wait_for_raises_when_the_deadline_passes(monkeypatch) -> None:
    from pneuma_lab.cloud.official_experiment import CoordinationStore

    store = object.__new__(CoordinationStore)
    monkeypatch.setattr(
        "pneuma_lab.cloud.official_experiment.time.sleep", lambda _seconds: None
    )
    store.exists = lambda _relative: False  # type: ignore[method-assign]

    with pytest.raises(TimeoutError, match="coordination barrier timed out"):
        CoordinationStore.wait_for(
            store, ["missing.json"], deadline=__import__("time").monotonic() - 1
        )
