"""Real two-worker executor for the frozen C120 four-arm study.

This is deliberately separate from the historical one-response production
probe.  It executes one common prefix and four continuations per task, keeps
clear arms controller-only, and publishes restart-safe task artifacts to S3.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import concurrent.futures
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import shlex
import tarfile
import threading
import time
from typing import Any, cast
from urllib.parse import urlparse

from pneuma_lab.resampling_null.controller import derive_call_seed

from .errors import CloudManifestError
from .official_execution_assets import validate_swe_execution_assets
from .production_run import ProductionRunSpec, canonical_bytes, canonical_digest


ARMS = frozenset({"REAL", "SHAM", "NONE", "RESAMPLE"})
SUBJECT_MODEL = "Qwen/Qwen3.6-35B-A3B-FP8"
SIMULATOR_MODEL = "Qwen/Qwen3.5-9B"
SWE_PREFIX_TOOL_CAP = 4
SWE_BRANCH_TOOL_CAP = 32
SWE_BRANCH_TOKEN_CAP = 32_768
SWE_BRANCH_SECONDS = 3_600
TAU_BRANCH_STEPS = 16
TAU_BRANCH_SECONDS = 1_800


def _load_canonical(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError(f"invalid official execution input: {path}") from exc
    if not isinstance(value, dict) or canonical_bytes(value) != raw:
        raise CloudManifestError(f"official execution input is not canonical: {path}")
    return value


def _s3_root(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise CloudManifestError("official output must be an S3 URI")
    return parsed.netloc, parsed.path.strip("/")


class CoordinationStore:
    """Create-once S3 coordination and evidence store."""

    def __init__(self, uri: str) -> None:
        self.bucket, self.prefix = _s3_root(uri)
        import boto3

        self.client = boto3.client("s3", region_name="us-east-1")

    def _key(self, relative: str) -> str:
        return f"{self.prefix}/{relative.strip('/')}"

    def put_once(self, relative: str, value: object) -> str:
        payload = canonical_bytes(value)
        digest = hashlib.sha256(payload).hexdigest()
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=self._key(relative),
                Body=payload,
                ServerSideEncryption="AES256",
                ContentType="application/json",
                IfNoneMatch="*",
                Metadata={"sha256": digest},
            )
        except self.client.exceptions.ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code"))
            if code not in {"PreconditionFailed", "412"}:
                raise
            existing = self.get(relative)
            if canonical_bytes(existing) != payload:
                raise CloudManifestError("create-once S3 evidence differs") from exc
        return digest

    def get(self, relative: str) -> dict[str, Any]:
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=self._key(relative),
        )
        payload = response["Body"].read()
        value = json.loads(payload.decode("utf-8"))
        if not isinstance(value, dict) or canonical_bytes(value) != payload:
            raise CloudManifestError("S3 coordination artifact is not canonical")
        return value

    def exists(self, relative: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._key(relative))
            return True
        except self.client.exceptions.ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code")) in {"404", "NoSuchKey"}:
                return False
            raise

    def wait_for(self, relatives: Sequence[str], *, deadline: float) -> None:
        pending = set(relatives)
        while pending and time.monotonic() < deadline:
            pending = {item for item in pending if not self.exists(item)}
            if pending:
                time.sleep(10)
        if pending:
            raise TimeoutError(f"official coordination barrier timed out: {sorted(pending)}")

    def list_relative(self, relative_prefix: str) -> list[str]:
        key_prefix = self._key(relative_prefix).rstrip("/") + "/"
        paginator = self.client.get_paginator("list_objects_v2")
        result: list[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=key_prefix):
            for item in page.get("Contents", []):
                key = item.get("Key")
                if isinstance(key, str):
                    result.append(key[len(self.prefix) + 1 :])
        return sorted(result)


class SimulatorRpcProxy:
    """Local OpenAI-compatible HTTP proxy backed by create-once S3 RPC."""

    def __init__(self, store: CoordinationStore, *, port: int = 18_080) -> None:
        self.store = store
        self.port = port
        self.counter = 0
        self.lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/v1/chat/completions":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length)
                try:
                    value = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self.send_error(400)
                    return
                if not isinstance(value, dict):
                    self.send_error(400)
                    return
                with outer.lock:
                    ordinal = outer.counter
                    outer.counter += 1
                request_id = hashlib.sha256(
                    b"pneuma-simulator-rpc-v1\0"
                    + ordinal.to_bytes(8, "big")
                    + canonical_bytes(value)
                ).hexdigest()
                outer.store.put_once(
                    f"coordination/simulator-rpc/requests/{request_id}.json",
                    {"request_id": request_id, "ordinal": ordinal, "body": value},
                )
                response_key = f"coordination/simulator-rpc/responses/{request_id}.json"
                outer.store.wait_for([response_key], deadline=time.monotonic() + 3600)
                response = outer.store.get(response_key)
                status = response.get("status_code")
                payload = response.get("body")
                if type(status) is not int or not isinstance(payload, dict):
                    self.send_error(502)
                    return
                encoded = canonical_bytes(payload)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def log_message(self, _format: str, *_args: object) -> None:
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=10)


def serve_simulator_rpc(
    store: CoordinationStore,
    *,
    local_endpoint: str = "http://127.0.0.1:8000",
    poll_seconds: float = 0.25,
) -> None:
    import requests

    completed: set[str] = set()
    pending: dict[concurrent.futures.Future[None], str] = {}

    def serve_one(relative: str) -> None:
        request_id = Path(relative).stem
        response_key = f"coordination/simulator-rpc/responses/{request_id}.json"
        if store.exists(response_key):
            return
        request = store.get(relative)
        body = request.get("body")
        if not isinstance(body, dict):
            raise CloudManifestError("simulator RPC request is malformed")
        response = requests.post(
            local_endpoint.rstrip("/") + "/v1/chat/completions",
            json=body,
            timeout=3600,
        )
        try:
            response_body = response.json()
        except ValueError as exc:
            raise CloudManifestError("simulator RPC returned non-JSON") from exc
        if not isinstance(response_body, dict):
            raise CloudManifestError("simulator RPC returned a non-object")
        store.put_once(
            response_key,
            {
                "request_id": request_id,
                "status_code": response.status_code,
                "body": response_body,
            },
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        while not store.exists("coordination/tau/worker-0.complete.json") or pending:
            for future in list(pending):
                if future.done():
                    future.result()
                    completed.add(pending.pop(future))
            active = set(pending.values())
            if not store.exists("coordination/tau/worker-0.complete.json"):
                for relative in store.list_relative("coordination/simulator-rpc/requests"):
                    request_id = Path(relative).stem
                    if request_id in completed or request_id in active:
                        continue
                    future = executor.submit(serve_one, relative)
                    pending[future] = request_id
                    if len(pending) >= 4:
                        break
            time.sleep(poll_seconds)


class VllmChatClient:
    def __init__(self, endpoint: str, *, request_timeout: int) -> None:
        self.endpoint = endpoint.rstrip("/") + "/v1/chat/completions"
        self.request_timeout = request_timeout

    def generate(
        self,
        *,
        model: str,
        messages: Sequence[Mapping[str, object]],
        tools: Sequence[Mapping[str, object]] | None,
        seed: int,
        sampling: Mapping[str, object],
        max_tokens: int,
    ) -> dict[str, Any]:
        import requests

        body: dict[str, object] = {
            "model": model,
            "messages": list(messages),
            "seed": seed,
            "temperature": sampling["temperature"],
            "top_p": sampling["top_p"],
            "top_k": sampling["top_k"],
            "presence_penalty": sampling.get("presence_penalty", 0.0),
            "repetition_penalty": sampling.get("repetition_penalty", 1.0),
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = list(tools)
            body["tool_choice"] = "auto"
        response = requests.post(
            self.endpoint,
            json=body,
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        value = response.json()
        if not isinstance(value, dict):
            raise CloudManifestError("vLLM returned a non-object")
        choices = value.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise CloudManifestError("vLLM returned the wrong choice cardinality")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            raise CloudManifestError("vLLM returned no assistant message")
        usage = value.get("usage")
        generated = usage.get("completion_tokens") if isinstance(usage, dict) else None
        if type(generated) is not int or generated < 0:
            raise CloudManifestError("vLLM returned invalid token usage")
        return {"raw": value, "message": message, "generated_tokens": generated}


@dataclass(slots=True)
class SwePrefix:
    task_id: str
    language: str
    lineage: str
    container: Any
    snapshot_image: Any
    messages: list[dict[str, object]]
    pending_calls: list[dict[str, object]]
    subject_calls: int
    generated_tokens: int
    triggered: bool
    trigger_reason: str
    prefix_grade: dict[str, object]
    packet_text: str
    packet_token_ids: list[int]


class DockerSweRuntime:
    """Trusted Docker-socket controller for isolated SWE task containers."""

    SHELL_TOOL = {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "Run one shell command in /testbed. Inspect and repair the repository. Do not use networking.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(
        self,
        *,
        run_root: Path,
        worker_id: str,
        parser_image: str,
        host_run_root: str,
    ) -> None:
        import docker

        self.client = docker.from_env()
        self.run_root = run_root
        self.worker_id = worker_id
        self.parser_image = parser_image
        self.host_run_root = host_run_root.rstrip("/")
        self._lock = threading.Lock()

    def pull(self, image_ref: str) -> None:
        with self._lock:
            self.client.images.pull(image_ref)

    def start(self, task: Mapping[str, object], *, suffix: str) -> Any:
        name = "pneuma-" + hashlib.sha256(
            f"{self.worker_id}:{task['task_id']}:{suffix}".encode()
        ).hexdigest()[:20]
        try:
            old = self.client.containers.get(name)
            old.remove(force=True)
        except Exception:
            pass
        return self.client.containers.run(
            str(task["image_ref"]),
            command=["sleep", "infinity"],
            detach=True,
            name=name,
            network_disabled=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            pids_limit=8192,
            mem_limit="46g",
            labels={
                "PneumaStudy": "neurips-2026-resampling-null",
                "PneumaTask": str(task["task_id"]),
                "PneumaWorker": self.worker_id,
            },
            working_dir="/testbed",
        )

    @staticmethod
    def exec(container: Any, command: str, *, seconds: int = 900) -> tuple[int, str]:
        wrapped = [
            "bash",
            "-lc",
            f"timeout --signal=KILL {int(seconds)}s bash -lc {shlex.quote(command)}",
        ]
        result = container.exec_run(wrapped, workdir="/testbed", demux=False)
        payload = result.output if isinstance(result.output, bytes) else bytes(result.output)
        text = payload.decode("utf-8", errors="replace")
        if len(text) > 80_000:
            text = text[:40_000] + "\n...[truncated]...\n" + text[-40_000:]
        return int(result.exit_code), text

    def state_digest(self, container: Any) -> tuple[str, bool]:
        _, status = self.exec(
            container,
            "git status --porcelain=v2 --untracked-files=all 2>/dev/null || true",
            seconds=60,
        )
        return hashlib.sha256(status.encode()).hexdigest(), bool(status.strip())

    def commit(self, container: Any, *, label: str) -> Any:
        repository = "pneuma-official-snapshot"
        tag = hashlib.sha256(label.encode()).hexdigest()[:32]
        return container.commit(repository=repository, tag=tag, pause=True)

    def clone(self, image: Any, task: Mapping[str, object], *, suffix: str) -> Any:
        cloned = dict(task)
        cloned["image_ref"] = image.id
        return self.start(cloned, suffix=suffix)

    @staticmethod
    def _put_text(container: Any, path: str, payload: str) -> None:
        parent, name = path.rsplit("/", 1)
        stream = io.BytesIO()
        encoded = payload.encode("utf-8")
        with tarfile.open(fileobj=stream, mode="w") as archive:
            info = tarfile.TarInfo(name)
            info.size = len(encoded)
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(encoded))
        container.put_archive(parent, stream.getvalue())

    def _parse_log(self, parser_source: str, log: str, *, task_id: str) -> dict[str, str]:
        if parser_source.strip().lower() == "pytest":
            result: dict[str, str] = {}
            for line in log.splitlines():
                if " PASSED" in line:
                    result[line.split(" PASSED", 1)[0].strip()] = "pass"
                elif " FAILED" in line:
                    result[line.split(" FAILED", 1)[0].strip()] = "fail"
            return result
        slug = hashlib.sha256(task_id.encode()).hexdigest()[:20]
        local = self.run_root / "parser" / slug
        local.mkdir(parents=True, exist_ok=True)
        request = local / "request.json"
        output = local / "output.json"
        request.write_bytes(canonical_bytes({"parser_source": parser_source, "log": log}))
        output.unlink(missing_ok=True)
        host_dir = f"{self.host_run_root}/parser/{slug}"
        child = self.client.containers.run(
            self.parser_image,
            command=[
                "python3",
                "-m",
                "pneuma_lab.cloud.swe_parser_sandbox",
                "/sandbox/request.json",
                "/sandbox/output.json",
            ],
            detach=True,
            network_disabled=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            read_only=True,
            mem_limit="1g",
            pids_limit=128,
            volumes={host_dir: {"bind": "/sandbox", "mode": "rw"}},
        )
        result = child.wait(timeout=120)
        logs = child.logs().decode("utf-8", errors="replace")
        child.remove(force=True)
        if int(result["StatusCode"]) != 0 or not output.is_file():
            raise CloudManifestError(
                "isolated SWE parser failed: " + hashlib.sha256(logs.encode()).hexdigest()
            )
        value = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise CloudManifestError("isolated SWE parser returned a non-object")
        return {str(key): str(status) for key, status in value.items()}

    def grade(self, image: Any, task: Mapping[str, object], *, suffix: str) -> dict[str, object]:
        grader = self.clone(image, task, suffix=f"grade-{suffix}")
        started = time.monotonic()
        try:
            self._put_text(grader, "/tmp/pneuma-test.patch", str(task["test_patch"]))
            apply_rc, apply_log = self.exec(
                grader,
                "git apply --whitespace=nowarn /tmp/pneuma-test.patch",
                seconds=300,
            )
            command_receipts: list[dict[str, object]] = []
            for command in cast(list[str], task["rebuild_cmds"]):
                rc, output = self.exec(grader, command, seconds=1800)
                command_receipts.append(
                    {"kind": "rebuild", "command": command, "rc": rc, "output": output}
                )
                if rc != 0:
                    break
            test_log = ""
            if apply_rc == 0 and all(row["rc"] == 0 for row in command_receipts):
                for command in cast(list[str], task["test_cmds"]):
                    rc, output = self.exec(grader, command, seconds=3600)
                    command_receipts.append(
                        {"kind": "test", "command": command, "rc": rc, "output": output}
                    )
                outputs = []
                for command in cast(list[str], task["print_cmds"]):
                    rc, output = self.exec(grader, command, seconds=300)
                    command_receipts.append(
                        {"kind": "print", "command": command, "rc": rc, "output": output}
                    )
                    outputs.append(output)
                test_log = "\n".join(outputs) or "\n".join(
                    str(row["output"])
                    for row in command_receipts
                    if row["kind"] == "test"
                )
            statuses = (
                self._parse_log(str(task["log_parser"]), test_log, task_id=str(task["task_id"]))
                if apply_rc == 0 and test_log
                else {}
            )
            passed = {name for name, status in statuses.items() if "pass" in status.lower()}
            failed = {name for name, status in statuses.items() if "fail" in status.lower()}
            f2p = set(cast(list[str], task["FAIL_TO_PASS"]))
            p2p = set(cast(list[str], task["PASS_TO_PASS"]))
            observed = passed | failed
            complete = f2p | p2p
            resolved = (
                apply_rc == 0
                and complete.issubset(observed)
                and f2p.issubset(passed)
                and not (p2p & failed)
            )
            return {
                "resolved": resolved,
                "apply_test_patch_rc": apply_rc,
                "registered_check_count": len(complete),
                "observed_check_count": len(complete & observed),
                "fail_to_pass_passed": sorted(f2p & passed),
                "fail_to_pass_failed": sorted(f2p - passed),
                "pass_to_pass_failed": sorted(p2p & failed),
                "status_sha256": canonical_digest(statuses),
                "bounded_log": test_log[-12_000:],
                "command_receipts": command_receipts,
                "elapsed_seconds": max(time.monotonic() - started, 1e-9),
            }
        finally:
            grader.remove(force=True)

    @staticmethod
    def cleanup(prefix: SwePrefix) -> None:
        try:
            prefix.container.remove(force=True)
        finally:
            try:
                prefix.snapshot_image.remove(force=True)
            except Exception:
                pass


def _assistant_message(value: Mapping[str, object]) -> dict[str, object]:
    result: dict[str, object] = {"role": "assistant"}
    for field in ("content", "reasoning_content", "tool_calls"):
        if field in value:
            result[field] = value[field]
    return result


def _tool_calls(message: Mapping[str, object]) -> list[dict[str, object]]:
    calls = message.get("tool_calls")
    if calls is None:
        return []
    if not isinstance(calls, list):
        raise CloudManifestError("assistant tool_calls is not a list")
    result: list[dict[str, object]] = []
    for call in calls:
        if not isinstance(call, dict) or not isinstance(call.get("id"), str):
            raise CloudManifestError("assistant tool call is malformed")
        function = call.get("function")
        if not isinstance(function, dict) or function.get("name") != "shell":
            raise CloudManifestError("SWE subject called an unregistered tool")
        arguments = function.get("arguments")
        if not isinstance(arguments, str):
            raise CloudManifestError("SWE shell arguments are malformed")
        parsed = json.loads(arguments)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("command"), str):
            raise CloudManifestError("SWE shell command is malformed")
        result.append({"id": call["id"], "command": parsed["command"], "raw": call})
    return result


def _packet_from_grade(grade: Mapping[str, object]) -> str:
    return (
        "<verifier_feedback>\n"
        "An isolated verifier evaluated the current repository state.\n"
        f"Observed checks: {grade['observed_check_count']}/{grade['registered_check_count']}\n"
        f"Fail-to-pass checks still failing: {json.dumps(grade['fail_to_pass_failed'])}\n"
        f"Pass-to-pass regressions: {json.dumps(grade['pass_to_pass_failed'])}\n"
        "Bounded verifier log follows:\n"
        f"{str(grade['bounded_log'])[-6000:]}\n"
        "</verifier_feedback>"
    )


class OfficialSweExecutor:
    def __init__(
        self,
        *,
        spec: ProductionRunSpec,
        run_root: Path,
        worker_id: str,
        store: CoordinationStore,
        assignments: Mapping[str, Mapping[str, object]],
        openings: Mapping[str, Mapping[str, object]],
        assets: Mapping[str, Mapping[str, object]],
        sampling: Mapping[str, object],
    ) -> None:
        self.spec = spec
        self.run_root = run_root
        self.worker_id = worker_id
        self.store = store
        self.assignments = assignments
        self.openings = openings
        self.assets = assets
        endpoint = str(cast(Mapping[str, object], spec.value["model_server"])["endpoint"])
        timeout = int(cast(Mapping[str, object], spec.value["model_server"])["request_timeout_seconds"])
        self.model = VllmChatClient(endpoint, request_timeout=timeout)
        self.sampling = sampling
        parser_image = os.environ.get("PNEUMA_BENCHMARK_WORKER_IMAGE_REF")
        host_root = os.environ.get("PNEUMA_HOST_RUN_ROOT")
        if not parser_image or not host_root:
            raise CloudManifestError("official SWE runtime lacks parser image/host root")
        self.docker = DockerSweRuntime(
            run_root=run_root,
            worker_id=worker_id,
            parser_image=parser_image,
            host_run_root=host_root,
        )
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(
            run_root / "payloads/subject-model",
            local_files_only=True,
            trust_remote_code=False,
        )

    def _prefix_messages(self, task: Mapping[str, object]) -> list[dict[str, object]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are a software-engineering agent. Repair the repository in /testbed "
                    "to solve the user issue. Use the shell tool. Do not access the network. "
                    "When the repair is complete, respond briefly without a tool call."
                ),
            },
            {"role": "user", "content": str(task["problem_statement"])},
        ]

    def _call(
        self,
        *,
        messages: list[dict[str, object]],
        root_seed: int,
        call_index: int,
        max_tokens: int,
    ) -> dict[str, Any]:
        return self.model.generate(
            model=SUBJECT_MODEL,
            messages=messages,
            tools=[DockerSweRuntime.SHELL_TOOL],
            seed=derive_call_seed(root_seed, "primary_subject", call_index),
            sampling=self.sampling,
            max_tokens=max_tokens,
        )

    def _run_prefix(self, task: Mapping[str, object]) -> SwePrefix:
        task_id = str(task["task_id"])
        opening = self.openings[task_id]
        self.docker.pull(str(task["image_ref"]))
        container = self.docker.start(task, suffix="prefix")
        messages = self._prefix_messages(task)
        subject_calls = 0
        generated_tokens = 0
        pending: list[dict[str, object]] = []
        triggered = False
        trigger_reason = "no_intervention_opportunity"
        try:
            while subject_calls < SWE_PREFIX_TOOL_CAP and not triggered:
                response = self._call(
                    messages=messages,
                    root_seed=int(opening["common_prefix_root_u64"]),
                    call_index=subject_calls,
                    max_tokens=4096,
                )
                subject_calls += 1
                generated_tokens += int(response["generated_tokens"])
                message = _assistant_message(response["message"])
                messages.append(message)
                calls = _tool_calls(response["message"])
                if not calls:
                    break
                for index, call in enumerate(calls):
                    rc, output = self.docker.exec(container, str(call["command"]))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": json.dumps(
                                {"exit_code": rc, "output": output},
                                sort_keys=True,
                            ),
                        }
                    )
                    _, mutated = self.docker.state_digest(container)
                    completed = sum(
                        1 for row in messages if row.get("role") == "tool"
                    )
                    if mutated or completed >= SWE_PREFIX_TOOL_CAP:
                        triggered = True
                        trigger_reason = (
                            "first_eligible_mutation" if mutated else "fourth_tool_call"
                        )
                        pending = calls[index + 1 :]
                        break
            snapshot = self.docker.commit(container, label=f"{task_id}:prefix")
            grade = self.docker.grade(snapshot, task, suffix="prefix")
            packet = _packet_from_grade(grade)
            ids = self.tokenizer.encode(packet, add_special_tokens=False)
            return SwePrefix(
                task_id=task_id,
                language=str(task["language"]),
                lineage=str(task["repo"]),
                container=container,
                snapshot_image=snapshot,
                messages=messages,
                pending_calls=pending,
                subject_calls=subject_calls,
                generated_tokens=generated_tokens,
                triggered=triggered,
                trigger_reason=trigger_reason,
                prefix_grade=grade,
                packet_text=packet,
                packet_token_ids=ids,
            )
        except Exception:
            container.remove(force=True)
            raise

    def _normalize_packet_pair(self, first: str, second: str) -> tuple[str, str, int]:
        target = 512
        first_ids = self.tokenizer.encode(first, add_special_tokens=False)[:target]
        second_ids = self.tokenizer.encode(second, add_special_tokens=False)[:target]
        pad_id: int | None = None
        for candidate in (" .", "\n.", " _", " -"):
            ids = self.tokenizer.encode(candidate, add_special_tokens=False)
            if len(ids) == 1:
                trial = self.tokenizer.decode(ids * 8, skip_special_tokens=False)
                if self.tokenizer.encode(trial, add_special_tokens=False) == ids * 8:
                    pad_id = int(ids[0])
                    break
        if pad_id is None:
            raise CloudManifestError("no exact neutral tokenizer pad unit exists")

        def close(ids: list[int]) -> str:
            payload = ids + [pad_id] * (target - len(ids))
            text = self.tokenizer.decode(payload, skip_special_tokens=False)
            if self.tokenizer.encode(text, add_special_tokens=False) != payload:
                raise CloudManifestError("packet token padding is not byte-stable")
            return text

        return close(first_ids), close(second_ids), target

    def _continue_branch(
        self,
        *,
        prefix: SwePrefix,
        task: Mapping[str, object],
        slot: Mapping[str, object],
        arm: str,
        packet: str | None,
    ) -> dict[str, object]:
        branch = self.docker.clone(
            prefix.snapshot_image,
            task,
            suffix=f"slot-{slot['ordinal']}",
        )
        messages = [dict(row) for row in prefix.messages]
        started = time.monotonic()
        calls = prefix.subject_calls
        tokens = prefix.generated_tokens
        try:
            for pending in prefix.pending_calls:
                rc, output = self.docker.exec(branch, str(pending["command"]))
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": pending["id"],
                        "content": json.dumps(
                            {"exit_code": rc, "output": output}, sort_keys=True
                        ),
                    }
                )
            if packet is not None:
                messages.append({"role": "system", "content": packet})
            terminal_reason = "model_stop"
            while (
                calls - prefix.subject_calls < SWE_BRANCH_TOOL_CAP
                and tokens - prefix.generated_tokens < SWE_BRANCH_TOKEN_CAP
                and time.monotonic() - started < SWE_BRANCH_SECONDS
            ):
                response = self._call(
                    messages=messages,
                    root_seed=int(slot["model_root_u64"]),
                    call_index=calls - prefix.subject_calls,
                    max_tokens=min(4096, SWE_BRANCH_TOKEN_CAP - (tokens - prefix.generated_tokens)),
                )
                calls += 1
                tokens += int(response["generated_tokens"])
                messages.append(_assistant_message(response["message"]))
                tool_calls = _tool_calls(response["message"])
                if not tool_calls:
                    break
                for call in tool_calls:
                    rc, output = self.docker.exec(branch, str(call["command"]))
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": json.dumps(
                                {"exit_code": rc, "output": output}, sort_keys=True
                            ),
                        }
                    )
            else:
                terminal_reason = "registered_cap"
            final_image = self.docker.commit(
                branch, label=f"{prefix.task_id}:slot:{slot['ordinal']}"
            )
            try:
                grade = self.docker.grade(
                    final_image,
                    task,
                    suffix=f"slot-{slot['ordinal']}",
                )
            finally:
                final_image.remove(force=True)
            _, diff = self.docker.exec(
                branch,
                "git diff --binary HEAD 2>/dev/null || true",
                seconds=120,
            )
            return {
                "slot_id": slot["slot_id"],
                "ordinal": slot["ordinal"],
                "arm": arm,
                "success": bool(grade["resolved"]),
                "terminal_reason": terminal_reason,
                "subject_calls": calls,
                "generated_tokens": tokens,
                "elapsed_seconds": max(time.monotonic() - started, 1e-9),
                "transcript": messages,
                "transcript_sha256": canonical_digest(messages),
                "worktree_diff": diff,
                "worktree_diff_sha256": hashlib.sha256(diff.encode()).hexdigest(),
                "grade": grade,
            }
        finally:
            branch.remove(force=True)

    def run(self, task_ids: Sequence[str]) -> dict[str, object]:
        def create_prefix(task_id: str) -> SwePrefix:
            task = self.assets[task_id]
            prefix = self._run_prefix(task)
            self.store.put_once(
                f"coordination/swe-prefix/{task_id.replace(':', '__')}.json",
                {
                    "record_kind": "cloud_official_swe_prefix_summary",
                    "task_id": task_id,
                    "worker_id": self.worker_id,
                    "language": prefix.language,
                    "lineage": prefix.lineage,
                    "triggered": prefix.triggered,
                    "trigger_reason": prefix.trigger_reason,
                    "packet_text": prefix.packet_text,
                    "packet_token_sha256": canonical_digest(prefix.packet_token_ids),
                    "packet_rank_sha256": self.openings[task_id]["packet_rank_sha256"],
                    "prefix_grade": prefix.prefix_grade,
                },
            )
            return prefix

        heavy = [
            task_id
            for task_id in task_ids
            if str(self.assets[task_id]["language"]).lower() in {"c", "cpp"}
        ]
        light = [task_id for task_id in task_ids if task_id not in set(heavy)]
        prefixes: dict[str, SwePrefix] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {task_id: executor.submit(create_prefix, task_id) for task_id in light}
            for task_id in light:
                prefixes[task_id] = futures[task_id].result()
        for task_id in heavy:
            prefixes[task_id] = create_prefix(task_id)
        self.store.put_once(
            f"coordination/swe-prefix/{self.worker_id}.complete.json",
            {"worker_id": self.worker_id, "task_count": len(prefixes), "state": "COMPLETE"},
        )
        self.store.wait_for(
            [
                "coordination/swe-prefix/worker-0.complete.json",
                "coordination/swe-prefix/worker-1.complete.json",
            ],
            deadline=time.monotonic() + 86_400,
        )
        assignment_tasks = list(self.assignments)
        all_prefixes = {
            task_id: self.store.get(
                f"coordination/swe-prefix/{task_id.replace(':', '__')}.json"
            )
            for task_id in assignment_tasks
            if task_id.startswith("swe:")
        }
        donor_by_task: dict[str, str] = {}
        for task_id, prefix in all_prefixes.items():
            if not prefix["triggered"]:
                continue
            candidates = [
                candidate
                for candidate, other in all_prefixes.items()
                if candidate != task_id
                and other["triggered"]
                and other["language"] == prefix["language"]
                and other["lineage"] != prefix["lineage"]
            ]
            if not candidates:
                raise CloudManifestError("triggered SWE prefix has no matched donor")
            donor_by_task[task_id] = min(
                candidates,
                key=lambda candidate: hashlib.sha256(
                    (
                        str(prefix["packet_rank_sha256"]) + "\0" + candidate
                    ).encode("utf-8")
                ).digest(),
            )

        def complete_task(task_id: str) -> None:
            prefix = prefixes[task_id]
            task = self.assets[task_id]
            assignment = self.assignments[task_id]
            opening_slots = {
                int(slot["ordinal"]): slot
                for slot in cast(list[Mapping[str, object]], self.openings[task_id]["slots"])
            }
            if not prefix.triggered:
                slots = [
                    {
                        "slot_id": slot["slot_id"],
                        "ordinal": slot["ordinal"],
                        "arm": slot["arm"],
                        "success": bool(prefix.prefix_grade["resolved"]),
                        "terminal_reason": "no_intervention_opportunity",
                        "grade": prefix.prefix_grade,
                    }
                    for slot in cast(list[Mapping[str, object]], assignment["slots"])
                ]
                donor = None
                packet_tokens = None
            else:
                donor = donor_by_task[task_id]
                real, sham, packet_tokens = self._normalize_packet_pair(
                    prefix.packet_text,
                    str(all_prefixes[donor]["packet_text"]),
                )
                packet_by_arm = {"REAL": real, "SHAM": sham, "NONE": None, "RESAMPLE": None}
                slots = []
                for clear in cast(list[Mapping[str, object]], assignment["slots"]):
                    arm = str(clear["arm"])
                    if arm not in ARMS:
                        raise CloudManifestError("clear assignment contains an unknown arm")
                    slots.append(
                        self._continue_branch(
                            prefix=prefix,
                            task=task,
                            slot=opening_slots[int(clear["ordinal"])],
                            arm=arm,
                            packet=packet_by_arm[arm],
                        )
                    )
            result = {
                "record_kind": "cloud_official_four_arm_task_result",
                "schema_version": "0.1.0",
                "run_spec_sha256": self.spec.digest,
                "benchmark": "SWE",
                "task_id": task_id,
                "worker_id": self.worker_id,
                "triggered": prefix.triggered,
                "trigger_reason": prefix.trigger_reason,
                "donor_task_id": donor,
                "packet_token_count": packet_tokens,
                "prefix": {
                    "transcript": prefix.messages,
                    "grade": prefix.prefix_grade,
                },
                "slots": slots,
            }
            self.store.put_once(
                f"tasks/swe/{task_id.replace(':', '__')}.json",
                result,
            )
            DockerSweRuntime.cleanup(prefix)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {task_id: executor.submit(complete_task, task_id) for task_id in light}
            for task_id in light:
                futures[task_id].result()
        for task_id in heavy:
            complete_task(task_id)
        completed = len(prefixes)
        self.store.put_once(
            f"coordination/swe-branches/{self.worker_id}.complete.json",
            {"worker_id": self.worker_id, "task_count": completed, "state": "COMPLETE"},
        )
        return {"benchmark": "SWE", "task_count": completed, "state": "COMPLETE"}


def _tau_domain(task_id: str) -> tuple[str, str]:
    parts = task_id.split(":", 2)
    if len(parts) != 3 or parts[0] != "tau":
        raise CloudManifestError("invalid tau2 task identity")
    public_domain = parts[1]
    domain = "banking_knowledge" if public_domain == "banking" else public_domain
    if domain not in {"airline", "telecom", "banking_knowledge"}:
        raise CloudManifestError("unregistered tau2 domain")
    return domain, parts[2]


class _DeterministicUuidModule:
    """Thread-local deterministic replacement for tau2 telecom's uuid module."""

    def __init__(self) -> None:
        self.local = threading.local()

    def set_root(self, root_seed: int) -> None:
        self.local.root_seed = root_seed
        self.local.counter = 0

    def uuid4(self) -> Any:
        import uuid

        root_seed = getattr(self.local, "root_seed", None)
        counter = getattr(self.local, "counter", None)
        if type(root_seed) is not int or type(counter) is not int:
            raise CloudManifestError("tau2 telecom UUID root is unset")
        payload = hashlib.sha256(
            b"pneuma-tau2-telecom-uuid-v1\0"
            + root_seed.to_bytes(8, "big")
            + counter.to_bytes(8, "big")
        ).digest()[:16]
        self.local.counter = counter + 1
        return uuid.UUID(bytes=payload)


_TELECOM_UUID = _DeterministicUuidModule()


def _tau_json(value: object) -> object:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, Mapping):
        return {str(key): _tau_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_tau_json(item) for item in value]
    return value


@dataclass(slots=True)
class TauPrefix:
    task_id: str
    domain: str
    group: str
    orchestrator: Any
    triggered: bool
    trigger_reason: str
    primary_calls: int
    simulator_calls: int
    subject_tool_calls: int
    grade: dict[str, object]
    packet_text: str


class OfficialTauExecutor:
    """Deep-copy tau2 prefix/branch executor over the pinned staged source."""

    def __init__(
        self,
        *,
        spec: ProductionRunSpec,
        run_root: Path,
        store: CoordinationStore,
        assignments: Mapping[str, Mapping[str, object]],
        openings: Mapping[str, Mapping[str, object]],
        registry_rows: Mapping[str, Mapping[str, object]],
        simulator_endpoint: str,
    ) -> None:
        self.spec = spec
        self.run_root = run_root
        self.store = store
        self.assignments = assignments
        self.openings = openings
        self.registry_rows = registry_rows
        self.simulator_endpoint = simulator_endpoint.rstrip("/")
        self.subject_endpoint = str(
            cast(Mapping[str, object], spec.value["model_server"])["endpoint"]
        ).rstrip("/")
        tau_source = run_root / "payloads/tau2-harness/src"
        tau_data = run_root / "payloads/tau2-harness/data"
        if not tau_source.is_dir() or not tau_data.is_dir():
            raise CloudManifestError("staged tau2 source/data is missing")
        import sys

        sys.path.insert(0, str(tau_source))
        os.environ["TAU2_DATA_DIR"] = str(tau_data)
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(
            run_root / "payloads/subject-model",
            local_files_only=True,
            trust_remote_code=False,
        )

    def _task(self, task_id: str) -> tuple[str, Any]:
        domain, upstream_id = _tau_domain(task_id)
        from tau2.runner.helpers import get_tasks

        tasks = get_tasks(domain, task_ids=[upstream_id])
        if len(tasks) != 1:
            raise CloudManifestError("tau2 task registry lookup was not unique")
        return domain, tasks[0]

    def _config(self, domain: str) -> Any:
        from tau2.data_model.simulation import TextRunConfig

        values: dict[str, object] = {
            "domain": domain,
            "agent": "llm_agent",
            "user": "user_simulator",
            "llm_agent": f"openai/{SUBJECT_MODEL}",
            "llm_user": f"openai/{SIMULATOR_MODEL}",
            "llm_args_agent": {
                "api_base": self.subject_endpoint.rstrip("/") + "/v1",
                "api_key": "local-no-key",
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 20,
                "presence_penalty": 1.5,
                "frequency_penalty": 0.0,
                "parallel_tool_calls": False,
            },
            "llm_args_user": {
                "api_base": self.simulator_endpoint.rstrip("/") + "/v1",
                "api_key": "local-no-key",
                "temperature": 0.0,
                "top_p": 1.0,
                "parallel_tool_calls": False,
            },
            "max_steps": 128,
            "max_errors": 10,
            "timeout": TAU_BRANCH_SECONDS,
            "enforce_communication_protocol": True,
            "seed": 0,
        }
        if domain == "banking_knowledge":
            values["retrieval_config"] = "bm25"
            values["retrieval_config_kwargs"] = {"top_k": 10}
        return TextRunConfig(**values)

    @staticmethod
    def _set_next_seed(orchestrator: Any, root_seed: int, role: str, index: int) -> None:
        if role == "primary_subject":
            orchestrator.agent.llm_args["seed"] = derive_call_seed(
                root_seed, "primary_subject", index
            )
        else:
            orchestrator.user.llm_args["seed"] = derive_call_seed(
                root_seed, "user_simulator", index
            )

    @staticmethod
    def _step_role(orchestrator: Any) -> str | None:
        target = getattr(orchestrator.to_role, "value", str(orchestrator.to_role))
        if str(target).lower().endswith("agent"):
            return "primary_subject"
        if str(target).lower().endswith("user"):
            return "user_simulator"
        return None

    @staticmethod
    def _pending_agent_tool(orchestrator: Any) -> tuple[bool, bool]:
        source = getattr(orchestrator.from_role, "value", str(orchestrator.from_role))
        target = getattr(orchestrator.to_role, "value", str(orchestrator.to_role))
        if not str(source).lower().endswith("agent") or not str(target).lower().endswith("env"):
            return False, False
        message = orchestrator.message
        calls = getattr(message, "tool_calls", None)
        if not isinstance(calls, list) or len(calls) != 1:
            raise CloudManifestError("tau2 subject must issue exactly one tool call per boundary")
        name = calls[0].name
        return True, bool(orchestrator.environment._is_mutating_tool(name))

    @staticmethod
    def _environment_kwargs(domain: str, task: Any) -> dict[str, object]:
        if domain != "banking_knowledge":
            return {}
        allowlist: set[str] = set()
        criteria = getattr(task, "evaluation_criteria", None)
        for action in getattr(criteria, "actions", None) or []:
            if action.name == "call_discoverable_agent_tool":
                name = (action.arguments or {}).get("agent_tool_name")
                if name:
                    allowlist.add(str(name))
        return {
            "retrieval_variant": "bm25",
            "retrieval_kwargs": {"top_k": 10},
            "task": task,
            "read_log_allowlist": allowlist,
        }

    def _grade(self, orchestrator: Any, task: Any, domain: str) -> dict[str, object]:
        from tau2.data_model.simulation import TerminationReason
        from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
        from tau2.orchestrator.modes import CommunicationMode

        clone = deepcopy(orchestrator)
        if not clone.done:
            clone.done = True
            clone.termination_reason = TerminationReason.AGENT_STOP
        simulation = clone._finalize()
        reward = evaluate_simulation(
            simulation,
            task,
            EvaluationType.ALL,
            False,
            domain,
            mode=CommunicationMode.HALF_DUPLEX,
            env_kwargs=self._environment_kwargs(domain, task),
            strict_replay=True,
        )
        value = cast(dict[str, object], _tau_json(reward))
        if any("nl" in str(key).lower() for key in value):
            raise CloudManifestError("tau2 primary endpoint invoked an NL evaluator")
        return value

    @staticmethod
    def _packet(grade: Mapping[str, object]) -> str:
        return (
            "<verifier_feedback>\n"
            "An isolated objective tau2 verifier evaluated the current state.\n"
            f"Current objective reward: {grade.get('reward', 0.0)}\n"
            f"Objective component record: {json.dumps(grade.get('reward_breakdown'), sort_keys=True)}\n"
            "No gold action sequence or expected database state is disclosed.\n"
            "</verifier_feedback>"
        )

    def _normalize_pair(self, first: str, second: str) -> tuple[str, str, int]:
        target = 192
        a = self.tokenizer.encode(first, add_special_tokens=False)[:target]
        b = self.tokenizer.encode(second, add_special_tokens=False)[:target]
        pad_id: int | None = None
        for candidate in (" .", "\n.", " _", " -"):
            ids = self.tokenizer.encode(candidate, add_special_tokens=False)
            if len(ids) == 1:
                trial = self.tokenizer.decode(ids * 8, skip_special_tokens=False)
                if self.tokenizer.encode(trial, add_special_tokens=False) == ids * 8:
                    pad_id = int(ids[0])
                    break
        if pad_id is None:
            raise CloudManifestError("no exact tau2 packet pad unit exists")

        def close(ids: list[int]) -> str:
            expected = ids + [pad_id] * (target - len(ids))
            text = self.tokenizer.decode(expected, skip_special_tokens=False)
            if self.tokenizer.encode(text, add_special_tokens=False) != expected:
                raise CloudManifestError("tau2 packet padding is not stable")
            return text

        return close(a), close(b), target

    def _install_telecom_uuid(self, root_seed: int) -> None:
        from tau2.domains.telecom import tools

        _TELECOM_UUID.set_root(root_seed)
        tools.uuid = _TELECOM_UUID

    def _run_prefix(self, task_id: str) -> TauPrefix:
        from tau2.runner.build import build_orchestrator

        domain, task = self._task(task_id)
        opening = self.openings[task_id]
        root_seed = int(opening["common_prefix_root_u64"])
        if domain == "telecom":
            self._install_telecom_uuid(root_seed)
        orchestrator = build_orchestrator(
            self._config(domain),
            task,
            seed=root_seed,
            simulation_id=hashlib.sha256(f"{task_id}:prefix".encode()).hexdigest(),
        )
        orchestrator.initialize()
        primary_calls = 0
        simulator_calls = 0
        tool_calls = 0
        triggered = False
        reason = "no_intervention_opportunity"
        while not orchestrator.done and not triggered:
            role = self._step_role(orchestrator)
            if role == "primary_subject":
                self._set_next_seed(orchestrator, root_seed, role, primary_calls)
                primary_calls += 1
            elif role == "user_simulator":
                self._set_next_seed(orchestrator, root_seed, role, simulator_calls)
                simulator_calls += 1
            is_agent_tool, mutating = self._pending_agent_tool(orchestrator)
            orchestrator.step()
            if is_agent_tool:
                tool_calls += 1
                if mutating or tool_calls >= 4:
                    triggered = True
                    reason = "first_eligible_mutation" if mutating else "fourth_tool_call"
        grade = self._grade(orchestrator, task, domain)
        group = str(self.registry_rows[task_id].get("stratum", f"domain:{domain}"))
        return TauPrefix(
            task_id=task_id,
            domain=domain,
            group=group,
            orchestrator=orchestrator,
            triggered=triggered,
            trigger_reason=reason,
            primary_calls=primary_calls,
            simulator_calls=simulator_calls,
            subject_tool_calls=tool_calls,
            grade=grade,
            packet_text=self._packet(grade),
        )

    def _continue(
        self,
        *,
        prefix: TauPrefix,
        task: Any,
        slot: Mapping[str, object],
        arm: str,
        packet: str | None,
    ) -> dict[str, object]:
        from tau2.data_model.message import SystemMessage
        from tau2.data_model.simulation import TerminationReason

        branch = deepcopy(prefix.orchestrator)
        root_seed = int(slot["model_root_u64"])
        if prefix.domain == "telecom":
            self._install_telecom_uuid(int(slot["benchmark_root_u64"]))
        if packet is not None:
            branch.agent_state.system_messages.append(
                SystemMessage(role="system", content=packet)
            )
        primary_calls = 0
        simulator_calls = 0
        subject_tools = 0
        started = time.monotonic()
        while (
            not branch.done
            and subject_tools < TAU_BRANCH_STEPS
            and time.monotonic() - started < TAU_BRANCH_SECONDS
        ):
            role = self._step_role(branch)
            if role == "primary_subject":
                self._set_next_seed(branch, root_seed, role, primary_calls)
                primary_calls += 1
            elif role == "user_simulator":
                self._set_next_seed(branch, root_seed, role, simulator_calls)
                simulator_calls += 1
            is_agent_tool, _ = self._pending_agent_tool(branch)
            branch.step()
            if is_agent_tool:
                subject_tools += 1
        if not branch.done:
            branch.done = True
            branch.termination_reason = TerminationReason.MAX_STEPS
        grade = self._grade(branch, task, prefix.domain)
        simulation = branch._finalize()
        messages = [_tau_json(message) for message in simulation.messages]
        return {
            "slot_id": slot["slot_id"],
            "ordinal": slot["ordinal"],
            "arm": arm,
            "success": float(grade.get("reward", 0.0)) == 1.0,
            "reward": grade.get("reward", 0.0),
            "grade": grade,
            "primary_calls": primary_calls,
            "simulator_calls": simulator_calls,
            "subject_tool_calls": subject_tools,
            "elapsed_seconds": max(time.monotonic() - started, 1e-9),
            "messages": messages,
            "messages_sha256": canonical_digest(messages),
            "termination_reason": simulation.termination_reason,
        }

    def run(self, task_ids: Sequence[str]) -> dict[str, object]:
        def create_prefix(task_id: str) -> TauPrefix:
            prefix = self._run_prefix(task_id)
            self.store.put_once(
                f"coordination/tau-prefix/{hashlib.sha256(task_id.encode()).hexdigest()}.json",
                {
                    "record_kind": "cloud_official_tau_prefix_summary",
                    "task_id": task_id,
                    "group": prefix.group,
                    "triggered": prefix.triggered,
                    "trigger_reason": prefix.trigger_reason,
                    "packet_text": prefix.packet_text,
                    "packet_rank_sha256": self.openings[task_id]["packet_rank_sha256"],
                    "grade": prefix.grade,
                },
            )
            return prefix

        prefixes: dict[str, TauPrefix] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {task_id: executor.submit(create_prefix, task_id) for task_id in task_ids}
            for task_id in task_ids:
                prefixes[task_id] = futures[task_id].result()
        donor_by_task: dict[str, str] = {}
        for task_id, prefix in prefixes.items():
            if not prefix.triggered:
                continue
            candidates = [
                candidate
                for candidate, other in prefixes.items()
                if candidate != task_id and other.triggered and other.group == prefix.group
            ]
            if not candidates:
                raise CloudManifestError("triggered tau2 prefix has no matched donor")
            donor_by_task[task_id] = min(
                candidates,
                key=lambda candidate: hashlib.sha256(
                    (
                        str(self.openings[task_id]["packet_rank_sha256"])
                        + "\0"
                        + candidate
                    ).encode()
                ).digest(),
            )
        def complete_task(task_id: str) -> None:
            prefix = prefixes[task_id]
            _, task = self._task(task_id)
            assignment = self.assignments[task_id]
            opening_slots = {
                int(row["ordinal"]): row
                for row in cast(list[Mapping[str, object]], self.openings[task_id]["slots"])
            }
            if not prefix.triggered:
                slots = [
                    {
                        "slot_id": row["slot_id"],
                        "ordinal": row["ordinal"],
                        "arm": row["arm"],
                        "success": float(prefix.grade.get("reward", 0.0)) == 1.0,
                        "reward": prefix.grade.get("reward", 0.0),
                        "grade": prefix.grade,
                        "termination_reason": "no_intervention_opportunity",
                    }
                    for row in cast(list[Mapping[str, object]], assignment["slots"])
                ]
                donor = None
                token_count = None
            else:
                donor = donor_by_task[task_id]
                real, sham, token_count = self._normalize_pair(
                    prefix.packet_text, prefixes[donor].packet_text
                )
                packets = {"REAL": real, "SHAM": sham, "NONE": None, "RESAMPLE": None}
                slots = []
                for row in cast(list[Mapping[str, object]], assignment["slots"]):
                    arm = str(row["arm"])
                    slots.append(
                        self._continue(
                            prefix=prefix,
                            task=task,
                            slot=opening_slots[int(row["ordinal"])],
                            arm=arm,
                            packet=packets[arm],
                        )
                    )
            result = {
                "record_kind": "cloud_official_four_arm_task_result",
                "schema_version": "0.1.0",
                "run_spec_sha256": self.spec.digest,
                "benchmark": "TAU",
                "task_id": task_id,
                "worker_id": "worker-0",
                "triggered": prefix.triggered,
                "trigger_reason": prefix.trigger_reason,
                "donor_task_id": donor,
                "packet_token_count": token_count,
                "prefix": {
                    "messages": [
                        _tau_json(message)
                        for message in prefix.orchestrator.get_messages()
                    ],
                    "grade": prefix.grade,
                },
                "slots": slots,
            }
            self.store.put_once(
                f"tasks/tau/{hashlib.sha256(task_id.encode()).hexdigest()}.json",
                result,
            )
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                task_id: executor.submit(complete_task, task_id) for task_id in task_ids
            }
            for task_id in task_ids:
                futures[task_id].result()
        completed = len(prefixes)
        self.store.put_once(
            "coordination/tau/worker-0.complete.json",
            {"worker_id": "worker-0", "task_count": completed, "state": "COMPLETE"},
        )
        return {"benchmark": "TAU", "task_count": completed, "state": "COMPLETE"}


def load_official_execution_inputs(
    run_root: Path,
) -> tuple[
    dict[str, Mapping[str, object]],
    dict[str, Mapping[str, object]],
    dict[str, Mapping[str, object]],
]:
    assignment = _load_canonical(run_root / "sealed/assignment.controller-only.json")
    openings = _load_canonical(run_root / "sealed/execution-seeds.controller-only.json")
    assets_doc = _load_canonical(
        run_root / "inputs/execution/swe-tasks.controller-only.json"
    )
    validate_swe_execution_assets(assets_doc)
    assignment_rows = assignment.get("rows")
    opening_rows = openings.get("rows")
    asset_rows = assets_doc.get("tasks")
    if not all(isinstance(rows, list) for rows in (assignment_rows, opening_rows, asset_rows)):
        raise CloudManifestError("official execution rows are malformed")
    assignments = {
        str(row["task_id"]): cast(Mapping[str, object], row)
        for row in cast(list[Mapping[str, object]], assignment_rows)
    }
    seed_openings = {
        str(row["task_id"]): cast(Mapping[str, object], row)
        for row in cast(list[Mapping[str, object]], opening_rows)
    }
    assets = {
        str(row["task_id"]): cast(Mapping[str, object], row)
        for row in cast(list[Mapping[str, object]], asset_rows)
    }
    if set(assignments) != set(seed_openings) or set(assets) != {
        task_id for task_id in assignments if task_id.startswith("swe:")
    }:
        raise CloudManifestError("official execution inputs disagree on task coverage")
    return assignments, seed_openings, assets


__all__ = [
    "CoordinationStore",
    "DockerSweRuntime",
    "OfficialSweExecutor",
    "OfficialTauExecutor",
    "SimulatorRpcProxy",
    "VllmChatClient",
    "load_official_execution_inputs",
    "serve_simulator_rpc",
]
