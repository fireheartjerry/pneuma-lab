"""Production model/benchmark adapters and raw worker evidence contracts.

The adapters are intentionally small and explicit: a real run uses an
OpenAI-compatible vLLM endpoint plus the registered benchmark adapter command;
tests use local mock adapters through the identical worker control flow.  The
mock path is structurally incapable of producing ``official_candidate``
evidence.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
from typing import Protocol, cast
from urllib import error as urllib_error
from urllib import request as urllib_request

from pneuma_lab.foundation.artifacts import write_atomic_bytes

from .errors import CloudManifestError
from .manifests import (
    validate_production_raw_worker_output,
    validate_production_worker_evidence,
)
from .production_run import (
    FileBinding,
    OFFICIAL_ENGINE,
    OFFICIAL_ENGINE_VERSION,
    OFFICIAL_MODEL_REPOSITORY,
    OFFICIAL_MODEL_REVISION,
    OFFICIAL_TOKENIZER_REVISION,
    ProductionRunSpec,
    canonical_bytes,
    canonical_digest,
    resolve_binding,
    task_rows,
    work_ids_for_worker,
)


class ProductionExecutionError(CloudManifestError):
    """A model/benchmark execution failure with a safe public classification."""

    def __init__(self, classification: str, message: str = "") -> None:
        self.classification = classification
        super().__init__(message or classification)


@dataclass(frozen=True, slots=True)
class ModelResponse:
    raw: object

    @property
    def sha256(self) -> str:
        return canonical_digest(self.raw)


class ModelAdapter(Protocol):
    def generate(self, request: Mapping[str, object]) -> ModelResponse: ...


class BenchmarkAdapter(Protocol):
    def prepare(self, task: Mapping[str, object]) -> Mapping[str, object]: ...

    def evaluate(self, task: Mapping[str, object], response: ModelResponse) -> object: ...


class LocalMockModelAdapter:
    """Deterministic local adapter; it can never be selected for official mode."""

    def generate(self, request: Mapping[str, object]) -> ModelResponse:
        task_id = request.get("task_id")
        if type(task_id) is not str or not task_id:
            raise ProductionExecutionError("MODEL_ERROR", "local mock request lacks task_id")
        value = {
            "adapter": "local-mock-model-v1",
            "task_id": task_id,
            "text": f"local-mock:{hashlib.sha256(task_id.encode()).hexdigest()[:16]}",
        }
        return ModelResponse(value)


class LocalMockBenchmarkAdapter:
    """Deterministic local evaluator for focused control-flow tests only."""

    def prepare(self, task: Mapping[str, object]) -> Mapping[str, object]:
        return {"task_id": task["work_id"], "prompt": f"local-mock-input:{task['work_id']}"}

    def evaluate(self, task: Mapping[str, object], response: ModelResponse) -> object:
        return {
            "adapter": "local-mock-benchmark-v1",
            "task_id": task["work_id"],
            "accepted": True,
            "response_sha256": response.sha256,
        }


class OpenAICompatibleModelAdapter:
    """Call the pinned vLLM OpenAI-compatible server without shelling out."""

    def __init__(self, spec: ProductionRunSpec) -> None:
        if spec.run_mode != "official":
            raise CloudManifestError("the real model adapter requires official run mode")
        self.spec = spec
        self.endpoint = str(cast(Mapping[str, object], spec.value["model_server"])["endpoint"]).rstrip("/") + "/chat/completions"
        self.timeout = int(cast(Mapping[str, object], spec.value["model_server"])["request_timeout_seconds"])

    def generate(self, request: Mapping[str, object]) -> ModelResponse:
        model = cast(Mapping[str, object], self.spec.value["model"])
        benchmark = request.get("benchmark")
        sampling_values = model.get("sampling_by_benchmark")
        if isinstance(sampling_values, Mapping) and benchmark in sampling_values:
            sampling = cast(Mapping[str, object], sampling_values[benchmark])
        else:
            sampling = cast(Mapping[str, object], model["sampling"])
        body = {
            "model": OFFICIAL_MODEL_REPOSITORY,
            "messages": [{"role": "user", "content": request["prompt"]}],
            "temperature": sampling["temperature"],
            "top_p": sampling["top_p"],
            "top_k": sampling["top_k"],
            "seed": cast(Mapping[str, object], self.spec.value["rng"])["root_u64"],
            "max_tokens": request["max_tokens"],
        }
        for field in ("presence_penalty", "repetition_penalty"):
            if field in sampling:
                body[field] = sampling[field]
        encoded = canonical_bytes(body)
        http_request = urllib_request.Request(
            self.endpoint,
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(http_request, timeout=self.timeout) as response:
                raw_response = response.read()
        except urllib_error.HTTPError as exc:
            classification = "PROVIDER_TIMEOUT" if exc.code in {408, 429, 504} else "MODEL_ERROR"
            raise ProductionExecutionError(classification) from exc
        except (urllib_error.URLError, TimeoutError, OSError) as exc:
            raise ProductionExecutionError("PROVIDER_TIMEOUT") from exc
        try:
            decoded = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductionExecutionError("MODEL_ERROR") from exc
        if not isinstance(decoded, Mapping):
            raise ProductionExecutionError("MODEL_ERROR")
        choices = decoded.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            raise ProductionExecutionError("MODEL_ERROR")
        message = choices[0].get("message")
        if not isinstance(message, Mapping) or "content" not in message:
            raise ProductionExecutionError("MODEL_ERROR")
        # Preserve the complete server response in the raw artifact, while the
        # worker contract records only its digest.
        return ModelResponse(decoded)


class SubprocessBenchmarkAdapter:
    """Run the registered benchmark adapter's prepare/evaluate subcommands."""

    def __init__(self, spec: ProductionRunSpec) -> None:
        if spec.run_mode != "official":
            raise CloudManifestError("the registered benchmark adapter requires official run mode")
        adapter = cast(Mapping[str, object], spec.value["benchmark_adapter"])
        entrypoint = adapter["entrypoint"]
        if not isinstance(entrypoint, list) or not entrypoint:
            raise CloudManifestError("benchmark adapter entrypoint is empty")
        self.entrypoint = tuple(cast(str, value) for value in entrypoint)
        self.timeout = int(adapter["timeout_seconds"])

    def _call(self, operation: str, payload: Mapping[str, object]) -> Mapping[str, object]:
        command = [*self.entrypoint, operation]
        try:
            result = subprocess.run(
                command,
                input=canonical_bytes(payload),
                capture_output=True,
                check=False,
                timeout=self.timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProductionExecutionError("PROVIDER_TIMEOUT") from exc
        except OSError as exc:
            raise ProductionExecutionError("INFRASTRUCTURE_ERROR") from exc
        if result.returncode != 0:
            diagnostic = (result.stderr or b"").lower()
            classification = "OOM" if b"out of memory" in diagnostic or b"oom" in diagnostic else "BENCHMARK_ERROR"
            raise ProductionExecutionError(classification)
        try:
            decoded = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProductionExecutionError("BENCHMARK_ERROR") from exc
        if not isinstance(decoded, Mapping):
            raise ProductionExecutionError("BENCHMARK_ERROR")
        return cast(Mapping[str, object], decoded)

    def prepare(self, task: Mapping[str, object]) -> Mapping[str, object]:
        value = self._call("prepare", {"task": dict(task)})
        prompt = value.get("prompt")
        max_tokens = value.get("max_tokens")
        if type(prompt) is not str or not prompt or type(max_tokens) is not int or max_tokens <= 0:
            raise ProductionExecutionError("BENCHMARK_ERROR")
        return value

    def evaluate(self, task: Mapping[str, object], response: ModelResponse) -> object:
        return self._call(
            "evaluate",
            {"task": dict(task), "model_response": response.raw},
        )


def launch_model_server(spec: ProductionRunSpec, *, run_root: Path) -> None:
    """Replace the authorized model-server process with the pinned vLLM argv.

    This function is intentionally never called by a controller.  The image
    role invokes it only after the provider admission layer has supplied the
    official authorization and run-spec bytes.
    """

    if spec.run_mode != "official":
        raise CloudManifestError("model-server launch requires official run mode")
    spec.verify_official_authorization(run_root=run_root)
    model_server = cast(Mapping[str, object], spec.value["model_server"])
    argv = model_server.get("launch_argv")
    if not isinstance(argv, list) or not argv:
        raise CloudManifestError("model-server launch argv is empty")
    command = [cast(str, value) for value in argv]
    if "vllm.entrypoints.openai.api_server" not in command:
        raise CloudManifestError("model-server launch is not the registered vLLM server")
    environment = dict(os.environ)
    environment["PNEUMA_RUN_SPEC_SHA256"] = spec.digest
    environment["PNEUMA_MODEL_REVISION"] = OFFICIAL_MODEL_REVISION
    array_index = environment.get("AWS_BATCH_JOB_ARRAY_INDEX")
    simulator_argv = model_server.get("simulator_launch_argv")
    if array_index == "1" and isinstance(simulator_argv, list) and simulator_argv:
        simulator_command = [cast(str, value) for value in simulator_argv]
        if "vllm.entrypoints.openai.api_server" not in simulator_command:
            raise CloudManifestError("simulator launch is not the registered vLLM server")
        control = run_root / "control"
        control.mkdir(parents=True, exist_ok=True)
        requested = control / "simulator.requested"
        ready = control / "simulator.ready"
        ready.unlink(missing_ok=True)
        process = subprocess.Popen(command, env=environment)
        try:
            while process.poll() is None and not requested.is_file():
                time.sleep(2)
            if process.poll() is not None:
                raise CloudManifestError("subject model server exited before phase switch")
            process.terminate()
            try:
                process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=30)
            simulator_environment = dict(environment)
            simulator_environment["PNEUMA_MODEL_REVISION"] = str(
                cast(Mapping[str, object], spec.value["model_server"])[
                    "simulator_revision"
                ]
            )
            simulator = subprocess.Popen(simulator_command, env=simulator_environment)
            ready.write_text("simulator\n", encoding="utf-8")
            return_code = simulator.wait()
            if return_code != 0:
                raise CloudManifestError("simulator model server exited unsuccessfully")
            return
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=30)
    os.execvpe(command[0], command, environment)
    raise AssertionError("os.execvpe returned unexpectedly")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _identity_digest(spec: ProductionRunSpec, worker_id: str) -> str:
    supplied = os.environ.get("PNEUMA_WORKER_IDENTITY")
    if spec.run_mode == "official" and (not supplied or not supplied.strip()):
        raise CloudManifestError("official workers require PNEUMA_WORKER_IDENTITY from the launch environment")
    identity = supplied.strip() if supplied else f"local-mock:{worker_id}:{platform.node()}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _failure_classification(exc: BaseException) -> str:
    if isinstance(exc, ProductionExecutionError):
        return exc.classification
    return "INFRASTRUCTURE_ERROR"


def _failure_detail_digest(exc: BaseException) -> str:
    return hashlib.sha256(type(exc).__name__.encode("utf-8")).hexdigest()


def _task_output_parity(task: Mapping[str, object]) -> str:
    return canonical_digest(
        {
            "task_id": task["task_id"],
            "benchmark": task["benchmark"],
            "input_sha256": task["input_sha256"],
            "model_response_sha256": task["model_response_sha256"],
            "benchmark_output_sha256": task["benchmark_output_sha256"],
            "status": task["status"],
        }
    )


@dataclass(frozen=True, slots=True)
class WorkerExecutionResult:
    evidence: Mapping[str, object]
    raw_artifact: bytes


class ProductionWorkerExecutor:
    """Execute one canonical worker partition through real or local adapters."""

    def __init__(
        self,
        spec: ProductionRunSpec,
        *,
        run_root: Path,
        model_adapter: ModelAdapter | None = None,
        benchmark_adapter: BenchmarkAdapter | None = None,
    ) -> None:
        self.spec = spec
        self.run_root = run_root
        if spec.run_mode == "official_candidate":
            raise CloudManifestError("pre-launch official candidate cannot execute a worker")
        if spec.run_mode == "local_mock":
            if model_adapter is not None and not isinstance(model_adapter, LocalMockModelAdapter):
                raise CloudManifestError("local_mock requires the local mock model adapter")
            if benchmark_adapter is not None and not isinstance(benchmark_adapter, LocalMockBenchmarkAdapter):
                raise CloudManifestError("local_mock requires the local mock benchmark adapter")
            self.model_adapter = model_adapter or LocalMockModelAdapter()
            self.benchmark_adapter = benchmark_adapter or LocalMockBenchmarkAdapter()
        else:
            spec.verify_official_authorization(run_root=run_root)
            if isinstance(model_adapter, LocalMockModelAdapter) or isinstance(benchmark_adapter, LocalMockBenchmarkAdapter):
                raise CloudManifestError("official production execution cannot use local mock adapters")
            self.model_adapter = model_adapter or OpenAICompatibleModelAdapter(spec)
            self.benchmark_adapter = benchmark_adapter or SubprocessBenchmarkAdapter(spec)

    def execute(self, worker_id: str) -> WorkerExecutionResult:
        if worker_id not in self.spec.worker_ids:
            raise CloudManifestError("worker_id is not in the immutable production topology")
        rows = {cast(str, row["work_id"]): row for row in task_rows(self.spec, run_root=self.run_root)}
        assigned = work_ids_for_worker(self.spec, worker_id=worker_id, run_root=self.run_root)
        started = _utc_now()
        monotonic_start = time.monotonic()
        task_outputs: list[dict[str, object]] = []
        raw_tasks: list[dict[str, object]] = []
        failures: list[dict[str, object]] = []
        for work_id in assigned:
            task = rows[work_id]
            input_sha256 = canonical_digest(task)
            try:
                request = {**dict(self.benchmark_adapter.prepare(task)), "benchmark": task["benchmark"]}
                response = self.model_adapter.generate(request)
                benchmark_output = self.benchmark_adapter.evaluate(task, response)
                model_sha256 = response.sha256
                benchmark_sha256 = canonical_digest(benchmark_output)
                outcome = {
                    "task_id": work_id,
                    "benchmark": task["benchmark"],
                    "status": "SUCCEEDED",
                    "input_sha256": input_sha256,
                    "model_response_sha256": model_sha256,
                    "benchmark_output_sha256": benchmark_sha256,
                    "output_parity_sha256": "",
                }
                outcome["output_parity_sha256"] = _task_output_parity(outcome)
                task_outputs.append(outcome)
                raw_tasks.append({
                    "task_id": work_id,
                    "benchmark": task["benchmark"],
                    "input": dict(task),
                    "request": dict(request),
                    "model_response": response.raw,
                    "benchmark_output": benchmark_output,
                    "status": "SUCCEEDED",
                })
            except Exception as exc:
                classification = _failure_classification(exc)
                detail_digest = _failure_detail_digest(exc)
                failures.append({"task_id": work_id, "classification": classification, "detail_sha256": detail_digest})
                failure_outcome = {
                    "task_id": work_id,
                    "benchmark": task["benchmark"],
                    "status": "FAILED",
                    "input_sha256": input_sha256,
                    "model_response_sha256": hashlib.sha256(b"failed-model-response").hexdigest(),
                    "benchmark_output_sha256": hashlib.sha256(b"failed-benchmark-output").hexdigest(),
                    "output_parity_sha256": "",
                }
                failure_outcome["output_parity_sha256"] = _task_output_parity(failure_outcome)
                task_outputs.append(failure_outcome)
                raw_tasks.append({
                    "task_id": work_id,
                    "benchmark": task["benchmark"],
                    "input": dict(task),
                    "status": "FAILED",
                    "failure_classification": classification,
                })
        finished = _utc_now()
        raw_value = {
            "record_kind": "cloud_production_raw_worker_output",
            "schema_version": "0.1.0",
            "run_spec_sha256": self.spec.digest,
            "worker_id": worker_id,
            "tasks": raw_tasks,
        }
        raw_artifact = canonical_bytes(raw_value)
        raw_sha256 = hashlib.sha256(raw_artifact).hexdigest()
        parity_sha256 = canonical_digest([task["output_parity_sha256"] for task in task_outputs])
        artifact_digests = [
            raw_sha256,
            *[cast(str, task["model_response_sha256"]) for task in task_outputs],
            *[cast(str, task["benchmark_output_sha256"]) for task in task_outputs],
        ]
        evidence: dict[str, object] = {
            "record_kind": "cloud_production_worker_evidence",
            "schema_version": "0.1.0",
            "evidence_class": "official_candidate" if self.spec.run_mode == "official" else "local_mock_non_scientific",
            "run_spec_sha256": self.spec.digest,
            "worker_id": worker_id,
            "worker_identity_sha256": _identity_digest(self.spec, worker_id),
            "code_commit": self.spec.value["code_commit"],
            "image_digest": self.spec.image_bindings["benchmark-worker"],
            "model": {
                "repository": OFFICIAL_MODEL_REPOSITORY,
                "revision": OFFICIAL_MODEL_REVISION,
                "tokenizer_revision": OFFICIAL_TOKENIZER_REVISION,
                "serving_engine": OFFICIAL_ENGINE,
                "serving_engine_version": OFFICIAL_ENGINE_VERSION,
            },
            "benchmarks": [
                {
                    "benchmark_id": item["benchmark_id"],
                    "repository": item["repository"],
                    "revision": item["revision"],
                    "dataset_repository": item["dataset_repository"],
                    "dataset_revision": item["dataset_revision"],
                }
                for item in cast(list[Mapping[str, object]], self.spec.value["benchmarks"])
            ],
            "task_manifest_sha256": self.spec.task_manifest_ref.sha256,
            "partition_sha256": canonical_digest(list(assigned)),
            "task_ids": list(assigned),
            "tasks": task_outputs,
            "timing": {"started_at": started, "finished_at": finished, "elapsed_seconds": max(time.monotonic() - monotonic_start, 1e-9)},
            "output": {
                "raw_artifact_sha256": raw_sha256,
                "raw_artifact_bytes": len(raw_artifact),
                "output_parity_sha256": parity_sha256,
                "artifact_digests": sorted(set(artifact_digests)),
            },
            "failures": failures,
            "state": "SUCCEEDED" if not failures else "FAILED",
        }
        validate_worker_evidence(evidence, self.spec, run_root=self.run_root, raw_artifact=raw_artifact)
        return WorkerExecutionResult(evidence=evidence, raw_artifact=raw_artifact)


def validate_worker_evidence(
    record: Mapping[str, object],
    spec: ProductionRunSpec,
    *,
    run_root: Path | None = None,
    raw_artifact: bytes | None = None,
) -> dict[str, object]:
    """Recompute all binding and parity checks before evidence admission."""

    validate_production_worker_evidence(record)
    if record.get("record_kind") != "cloud_production_worker_evidence" or record.get("schema_version") != "0.1.0":
        raise CloudManifestError("worker evidence has the wrong identity")
    if record.get("run_spec_sha256") != spec.digest:
        raise CloudManifestError("worker evidence run specification digest differs")
    worker_id = record.get("worker_id")
    if worker_id not in spec.worker_ids:
        raise CloudManifestError("worker evidence worker identity is not approved")
    expected_class = "official_candidate" if spec.run_mode == "official" else "local_mock_non_scientific"
    if record.get("evidence_class") != expected_class:
        raise CloudManifestError("worker evidence class does not match the run mode")
    if record.get("code_commit") != spec.value["code_commit"]:
        raise CloudManifestError("worker evidence code commit differs")
    if record.get("image_digest") != spec.image_bindings["benchmark-worker"]:
        raise CloudManifestError("worker evidence image binding differs")
    model = record.get("model")
    if model != {
        "repository": OFFICIAL_MODEL_REPOSITORY,
        "revision": OFFICIAL_MODEL_REVISION,
        "tokenizer_revision": OFFICIAL_TOKENIZER_REVISION,
        "serving_engine": OFFICIAL_ENGINE,
        "serving_engine_version": OFFICIAL_ENGINE_VERSION,
    }:
        raise CloudManifestError("worker evidence model or serving binding differs")
    if record.get("task_manifest_sha256") != spec.task_manifest_ref.sha256:
        raise CloudManifestError("worker evidence task manifest binding differs")
    expected_ids = work_ids_for_worker(spec, worker_id=cast(str, worker_id), run_root=spec_root(run_root)) if run_root is not None else None
    task_ids = record.get("task_ids")
    if not isinstance(task_ids, list) or any(type(item) is not str for item in task_ids):
        raise CloudManifestError("worker evidence task_ids must be a string array")
    if expected_ids is not None and tuple(cast(list[str], task_ids)) != expected_ids:
        raise CloudManifestError("worker evidence partition assignment differs")
    if record.get("partition_sha256") != canonical_digest(task_ids):
        raise CloudManifestError("worker evidence partition digest differs")
    tasks = record.get("tasks")
    if not isinstance(tasks, list) or [item.get("task_id") for item in cast(list[Mapping[str, object]], tasks)] != task_ids:
        raise CloudManifestError("worker evidence task outcomes do not match the partition")
    for index, task in enumerate(cast(list[Mapping[str, object]], tasks)):
        if task.get("output_parity_sha256") != _task_output_parity(task):
            raise CloudManifestError(f"worker evidence task[{index}] output parity differs")
    output = record.get("output")
    if not isinstance(output, Mapping):
        raise CloudManifestError("worker evidence output is not an object")
    expected_parity = canonical_digest([task["output_parity_sha256"] for task in cast(list[Mapping[str, object]], tasks)])
    if output.get("output_parity_sha256") != expected_parity:
        raise CloudManifestError("worker evidence aggregate output parity differs")
    raw = raw_artifact
    if raw is None and run_root is not None:
        raw_ref = output.get("raw_artifact_ref")
        if isinstance(raw_ref, Mapping):
            raw_binding = FileBinding.from_value(raw_ref, field="output.raw_artifact_ref")
            _path, raw = resolve_binding(raw_binding, run_root=run_root)
    if raw is not None:
        if len(raw) != output.get("raw_artifact_bytes") or hashlib.sha256(raw).hexdigest() != output.get("raw_artifact_sha256"):
            raise CloudManifestError("worker evidence raw artifact digest/size differs")
        try:
            raw_value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CloudManifestError("worker evidence raw artifact is not canonical JSON") from exc
        if not isinstance(raw_value, Mapping) or canonical_bytes(raw_value) != raw:
            raise CloudManifestError("worker evidence raw artifact is not canonical JSON")
        raw_record = validate_production_raw_worker_output(raw_value)
        if (
            raw_record["run_spec_sha256"] != spec.digest
            or raw_record["worker_id"] != worker_id
            or [item["task_id"] for item in raw_record["tasks"]] != task_ids
        ):
            raise CloudManifestError("worker evidence raw artifact does not bind its worker partition")
    failures = record.get("failures")
    if not isinstance(failures, list):
        raise CloudManifestError("worker evidence failures must be an array")
    failure_ids = {cast(str, item["task_id"]) for item in cast(list[Mapping[str, object]], failures)}
    failed_ids = {cast(str, task["task_id"]) for task in cast(list[Mapping[str, object]], tasks) if task.get("status") == "FAILED"}
    if failure_ids != failed_ids:
        raise CloudManifestError("worker evidence failure classification does not match task states")
    state = record.get("state")
    if state == "SUCCEEDED" and (failures or any(task.get("status") != "SUCCEEDED" for task in cast(list[Mapping[str, object]], tasks))):
        raise CloudManifestError("successful worker evidence contains a failed task")
    if state == "FAILED" and not failures:
        raise CloudManifestError("failed worker evidence has no classified failure")
    return dict(record)


def spec_root(run_root: Path | None) -> Path:
    if run_root is None:
        raise CloudManifestError("run_root is required to verify a partition")
    return run_root


def write_worker_result(
    result: WorkerExecutionResult,
    *,
    evidence_path: Path,
    raw_path: Path,
    run_root: Path,
) -> Mapping[str, object]:
    """Publish raw bytes first, then the evidence that binds them."""

    if evidence_path.exists() or raw_path.exists():
        raise CloudManifestError("worker output destinations must be new immutable paths")
    try:
        relative_raw = raw_path.resolve().relative_to(run_root.resolve()).as_posix()
    except ValueError as exc:
        raise CloudManifestError("worker raw output must remain beneath run_root") from exc
    evidence = dict(result.evidence)
    output = dict(cast(Mapping[str, object], evidence["output"]))
    output["raw_artifact_ref"] = FileBinding(
        role="cloud_production_raw_worker_output",
        relative_path=relative_raw,
        sha256=hashlib.sha256(result.raw_artifact).hexdigest(),
        byte_count=len(result.raw_artifact),
        media_type="application/json",
    ).as_dict()
    evidence["output"] = output
    validate_production_worker_evidence(evidence)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    write_atomic_bytes(raw_path, result.raw_artifact)
    write_atomic_bytes(evidence_path, canonical_bytes(evidence))
    return evidence


__all__ = [
    "BenchmarkAdapter",
    "LocalMockBenchmarkAdapter",
    "LocalMockModelAdapter",
    "launch_model_server",
    "ModelAdapter",
    "ModelResponse",
    "OpenAICompatibleModelAdapter",
    "ProductionExecutionError",
    "ProductionWorkerExecutor",
    "SubprocessBenchmarkAdapter",
    "WorkerExecutionResult",
    "validate_worker_evidence",
    "write_worker_result",
]
