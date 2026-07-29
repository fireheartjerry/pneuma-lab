"""Controller-owned subprocess fixture and initial-restore qualification.

This module is local synthetic-validation machinery only. It performs no
provider, model, network, experiment, spend, branch, or publication action.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field as dataclass_field
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import subprocess
import sys
import time
from typing import BinaryIO, cast, final

_IPC_MAX_FRAME_BYTES = 1024 * 1024
_IPC_TIMEOUT_SECONDS = 2.0


def _worker_canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _strict_compact_json(payload: bytes) -> object:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("IPC frame is not strict UTF-8") from exc

    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"IPC frame repeats key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ValueError(f"IPC frame contains {constant!r}")
            ),
        )
    except json.JSONDecodeError as exc:
        raise ValueError("IPC frame is not strict JSON") from exc
    if _worker_canonical(value) != payload:
        raise ValueError("IPC frame is not compact canonical JSON")
    return value


def _write_frame_fd(
    descriptor: int,
    payload: bytes,
    *,
    timeout_seconds: float,
) -> None:
    if type(payload) is not bytes or len(payload) > _IPC_MAX_FRAME_BYTES:
        raise ValueError("IPC frame exceeds the exact byte cap")
    frame = payload + b"\n"
    view = memoryview(frame)
    offset = 0
    deadline = time.monotonic() + timeout_seconds
    while offset < len(view):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("IPC frame write timed out")
        _readable, writable, _exceptional = select.select(
            [],
            [descriptor],
            [],
            remaining,
        )
        if not writable:
            raise TimeoutError("IPC frame write timed out")
        try:
            written = os.write(descriptor, view[offset:])
        except BlockingIOError:
            continue
        if written <= 0:
            raise OSError("IPC frame write made no progress")
        offset += written


def _read_frame_fd(
    descriptor: int,
    *,
    timeout_seconds: float,
    allow_clean_eof: bool = False,
) -> bytes | None:
    chunks = bytearray()
    deadline = time.monotonic() + timeout_seconds
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("IPC frame read timed out")
        readable, _writable, _exceptional = select.select(
            [descriptor],
            [],
            [],
            remaining,
        )
        if not readable:
            raise TimeoutError("IPC frame read timed out")
        try:
            chunk = os.read(
                descriptor,
                min(65536, _IPC_MAX_FRAME_BYTES + 2 - len(chunks)),
            )
        except BlockingIOError:
            continue
        if not chunk:
            if allow_clean_eof and not chunks:
                return None
            raise EOFError("IPC frame ended before one newline")
        chunks.extend(chunk)
        newline = chunks.find(b"\n")
        if newline >= 0:
            if newline != len(chunks) - 1:
                raise ValueError("IPC read contains multiple or trailing frames")
            if newline > _IPC_MAX_FRAME_BYTES:
                raise ValueError("IPC frame exceeds the exact byte cap")
            return bytes(chunks[:newline])
        if len(chunks) > _IPC_MAX_FRAME_BYTES:
            raise ValueError("IPC frame exceeds the exact byte cap")


def _worker_decoded(value: object) -> bytes:
    if type(value) is not str:
        raise ValueError("encoded bytes must be exact text")
    return base64.b64decode(value, validate=True)


def _synthetic_worker_main() -> int:
    """Run the subprocess fixture from this exact reviewed source file."""

    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--synthetic-worker", action="store_true", required=True)
    parser.add_argument("--request-fd", type=int, required=True)
    parser.add_argument("--response-fd", type=int, required=True)
    parser.add_argument("--task-sha256", required=True)
    parser.add_argument("--program-sha256", required=True)
    parser.add_argument("--source-sha256", required=True)
    arguments = parser.parse_args()
    with open(__file__, "rb") as source:
        if hashlib.sha256(source.read()).hexdigest() != arguments.source_sha256:
            raise ValueError("executed worker source differs from reviewed descriptor")
    os.set_blocking(arguments.request_fd, False)
    os.set_blocking(arguments.response_fd, False)
    state: dict[str, object] | None = None

    def encoded(value: bytes) -> str:
        return base64.b64encode(value).decode("ascii")

    def reply(value: object) -> None:
        _write_frame_fd(
            arguments.response_fd,
            _worker_canonical({"ok": True, "value": value}),
            timeout_seconds=_IPC_TIMEOUT_SECONDS,
        )

    expected_keys = {
        "start": {"operation", "program_bytes", "task_input_bytes"},
        "snapshot": {"operation"},
        "restore": {"operation", "snapshot_bytes"},
        "visible_context": {"operation"},
        "simulator_context": {"operation"},
        "mutation_committed": {"operation"},
        "verifier_eligible": {"operation"},
        "episode_terminal": {"operation"},
        "failure_kind": {"operation"},
        "close": {"operation"},
    }
    while True:
        try:
            frame = _read_frame_fd(
                arguments.request_fd,
                timeout_seconds=_IPC_TIMEOUT_SECONDS,
                allow_clean_eof=True,
            )
            if frame is None:
                break
            message = _strict_compact_json(frame)
            if type(message) is not dict:
                raise ValueError("worker request must be one exact object")
            operation = message["operation"]
            if (
                type(operation) is not str
                or operation not in expected_keys
                or set(message) != expected_keys[operation]
            ):
                raise ValueError("worker request has an open operation shape")
            if operation == "start":
                task_bytes = _worker_decoded(message["task_input_bytes"])
                program_bytes = _worker_decoded(message["program_bytes"])
                if hashlib.sha256(task_bytes).hexdigest() != arguments.task_sha256:
                    raise ValueError("task bytes differ from command binding")
                if (
                    hashlib.sha256(program_bytes).hexdigest()
                    != arguments.program_sha256
                ):
                    raise ValueError("program bytes differ from command binding")
                state = {
                    "branch_pending_calls": [],
                    "episode_terminal": False,
                    "failure_kind": "none",
                    "program_sha256": arguments.program_sha256,
                    "simulator_context": None,
                    "terminal_unexecuted_remainder": [],
                    "turns": [],
                    "visible_context": encoded(task_bytes),
                }
                reply(None)
            elif state is None:
                raise ValueError("environment has not started")
            elif operation == "snapshot":
                reply(encoded(_worker_canonical(state) + b"\n"))
            elif operation == "restore":
                candidate = _worker_decoded(message["snapshot_bytes"])
                decoded = json.loads(candidate)
                if (
                    type(decoded) is not dict
                    or _worker_canonical(decoded) + b"\n" != candidate
                ):
                    raise ValueError("snapshot is not a canonical object")
                state = decoded
                reply(None)
            elif operation == "visible_context":
                reply(state["visible_context"])
            elif operation == "simulator_context":
                reply(state["simulator_context"])
            elif operation == "mutation_committed":
                reply(False)
            elif operation == "verifier_eligible":
                reply(False)
            elif operation == "episode_terminal":
                reply(state["episode_terminal"])
            elif operation == "failure_kind":
                reply(state["failure_kind"])
            elif operation == "close":
                reply(None)
                break
            else:
                raise ValueError("operation is unavailable")
        except BaseException as exc:
            _write_frame_fd(
                arguments.response_fd,
                _worker_canonical(
                    {"error": f"{type(exc).__name__}: {exc}", "ok": False}
                ),
                timeout_seconds=_IPC_TIMEOUT_SECONDS,
            )
    os.close(arguments.request_fd)
    os.close(arguments.response_fd)
    return 0


if __name__ == "__main__":
    raise SystemExit(_synthetic_worker_main())


from pneuma_lab.foundation.artifacts import canonical_json_bytes  # noqa: E402

from .controller_artifacts import ControllerArtifactStore  # noqa: E402
from .errors import RecordValidationError  # noqa: E402
from .prefix_contracts import (  # noqa: E402
    AUTHORITY_ASSET_ROLE_MEDIA,
    CONTROLLER_ROLE_MEDIA,
    EnvironmentProcessIdentity,
    ImplementationDescriptor,
    InitialRestoreQualificationReceipt,
    StableSourceProvenance,
    initial_restore_qualification_receipt_bytes,
)
from .types import ArtifactRef, FailureKind, ToolCall  # noqa: E402


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_ROOT_SUFFIX_ATTEMPTS = 16
_WORKSPACE_NAME = "prefix-environments"
_SOURCE_ROOT = Path(__file__).parents[3]
_SOURCE_PATH = Path("src/pneuma_lab/resampling_null/synthetic_environment.py")
_ENVIRONMENT_DESCRIPTOR_FIELDS = {
    "purpose": "environment",
    "nominal_type": (
        "pneuma_lab.resampling_null.synthetic_environment.SyntheticEnvironmentFactory"
    ),
    "build_id": "synthetic-environment-v1",
    "request_grammar": None,
    "response_grammar": None,
    "snapshot_grammar": "synthetic-environment-snapshot-v1",
    "restore_grammar": "synthetic-environment-snapshot-v1",
    "evidence_grammar": "synthetic-environment-evidence-v1",
    "runtime_id": "cpython-3.12-local",
    "container_digest": "sha256:" + "0" * 64,
}
_TOKENIZER_DESCRIPTOR_FIELDS = {
    "purpose": "tokenizer",
    "nominal_type": (
        "pneuma_lab.resampling_null.synthetic_environment.SyntheticByteTokenizer"
    ),
    "build_id": "synthetic-byte-tokenizer-v1",
    "request_grammar": None,
    "response_grammar": None,
    "snapshot_grammar": None,
    "restore_grammar": None,
    "evidence_grammar": None,
    "runtime_id": None,
    "container_digest": None,
}


def _exact_bytes(value: object, field: str) -> bytes:
    if type(value) is not bytes:
        raise TypeError(f"{field} must be exact bytes")
    return value


@dataclass(frozen=True, slots=True)
class InitialQualificationAuthority:
    """Sealed ancestry and bytes needed by initial restore qualification."""

    schedule_ref: ArtifactRef
    task_ref: ArtifactRef
    task_input_ref: ArtifactRef
    environment_contract_ref: ArtifactRef
    isolation_contract_ref: ArtifactRef
    program_ref: ArtifactRef
    environment_descriptor: ImplementationDescriptor
    tokenizer_descriptor: ImplementationDescriptor
    task_input_bytes: bytes
    program_bytes: bytes
    _seal: tuple[object, ...] = dataclass_field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        self._validate_canonical()
        object.__setattr__(self, "_seal", self._seal_value())

    @staticmethod
    def _ref_value(ref: ArtifactRef) -> tuple[object, ...]:
        return (
            ref.role,
            ref.relative_path,
            ref.sha256,
            ref.byte_count,
            ref.media_type,
        )

    @classmethod
    def _descriptor_value(
        cls,
        descriptor: ImplementationDescriptor,
    ) -> tuple[object, ...]:
        return (
            descriptor.purpose,
            descriptor.nominal_type,
            descriptor.build_id,
            descriptor.request_grammar,
            descriptor.response_grammar,
            descriptor.snapshot_grammar,
            descriptor.restore_grammar,
            descriptor.evidence_grammar,
            descriptor.runtime_id,
            descriptor.container_digest,
            cls._ref_value(descriptor.implementation_source_ref),
        )

    def _seal_value(self) -> tuple[object, ...]:
        return (
            *(self._ref_value(getattr(self, field)) for field in (
                "schedule_ref",
                "task_ref",
                "task_input_ref",
                "environment_contract_ref",
                "isolation_contract_ref",
                "program_ref",
            )),
            self._descriptor_value(self.environment_descriptor),
            self._descriptor_value(self.tokenizer_descriptor),
            hashlib.sha256(self.task_input_bytes).hexdigest(),
            len(self.task_input_bytes),
            hashlib.sha256(self.program_bytes).hexdigest(),
            len(self.program_bytes),
        )

    @staticmethod
    def _validate_authority_ref(ref: ArtifactRef, field: str, role: str) -> None:
        if role == "resampling_prefix_schedule":
            if (
                ref.media_type != "application/json"
                or ref.relative_path != "prefix-schedule.json"
            ):
                raise ValueError(f"{field} has noncanonical scientific path/media")
            return
        if role in CONTROLLER_ROLE_MEDIA:
            if (
                ref.media_type != CONTROLLER_ROLE_MEDIA[role]
                or ref.relative_path
                != f"controller-artifacts/{role}/{ref.sha256}"
            ):
                raise ValueError(f"{field} has noncanonical controller path/media")
            return
        if role in AUTHORITY_ASSET_ROLE_MEDIA:
            path = Path(ref.relative_path)
            if (
                ref.media_type != AUTHORITY_ASSET_ROLE_MEDIA[role]
                or not ref.relative_path.startswith("sources/")
                or path.is_absolute()
                or ".." in path.parts
                or path.as_posix() != ref.relative_path
            ):
                raise ValueError(f"{field} has noncanonical authority path/media")
            return
        raise ValueError(f"{field} has unregistered role")

    def _validate_canonical(self) -> None:
        for field, role in (
            ("schedule_ref", "resampling_prefix_schedule"),
            ("task_ref", "selected_task"),
            ("task_input_ref", "task_input"),
            ("environment_contract_ref", "environment_contract"),
            ("isolation_contract_ref", "isolation_contract"),
            ("program_ref", "synthetic_execution_program"),
        ):
            value = getattr(self, field)
            if type(value) is not ArtifactRef or value.role != role:
                raise TypeError(f"{field} must be an exact {role} ArtifactRef")
            self._validate_authority_ref(value, field, role)
        task_input_bytes = _exact_bytes(self.task_input_bytes, "task_input_bytes")
        program_bytes = _exact_bytes(self.program_bytes, "program_bytes")
        for field, ref, payload in (
            ("task_input_bytes", self.task_input_ref, task_input_bytes),
            ("program_bytes", self.program_ref, program_bytes),
        ):
            if (
                hashlib.sha256(payload).hexdigest() != ref.sha256
                or len(payload) != ref.byte_count
            ):
                raise ValueError(f"{field} differ from sealed ArtifactRef")
        descriptor = self.environment_descriptor
        if type(descriptor) is not ImplementationDescriptor or any(
            getattr(descriptor, field) != expected
            for field, expected in _ENVIRONMENT_DESCRIPTOR_FIELDS.items()
        ):
            raise ValueError(
                "environment_descriptor is not the registered environment descriptor"
            )
        tokenizer_descriptor = self.tokenizer_descriptor
        if type(tokenizer_descriptor) is not ImplementationDescriptor or any(
            getattr(tokenizer_descriptor, field) != expected
            for field, expected in _TOKENIZER_DESCRIPTOR_FIELDS.items()
        ):
            raise ValueError(
                "tokenizer_descriptor is not the registered tokenizer descriptor"
            )
        for field, descriptor in (
            ("environment_descriptor", descriptor),
            ("tokenizer_descriptor", tokenizer_descriptor),
        ):
            self._validate_authority_ref(
                descriptor.implementation_source_ref,
                f"{field}.implementation_source_ref",
                "source_revision",
            )

    def verify_seal(self) -> None:
        self._validate_canonical()
        if self._seal_value() != self._seal:
            raise RecordValidationError("initial qualification authority seal drifted")


@final
class SyntheticByteTokenizer:
    """Exact zero-state tokenizer used by the synthetic fixture."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticByteTokenizer is final")

    def encode(self, payload: bytes) -> tuple[int, ...]:
        return tuple(_exact_bytes(payload, "tokenizer payload"))


@final
class ControllerEnvironmentIPC:
    """The controller-owned ends of one request/response pipe pair."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("ControllerEnvironmentIPC is final")

    def __init__(
        self,
        *,
        request_read_fd: int,
        response_write_fd: int,
        request_writer: BinaryIO,
        response_reader: BinaryIO,
    ) -> None:
        self._request_read_fd: int | None = request_read_fd
        self._response_write_fd: int | None = response_write_fd
        self._request_writer = request_writer
        self._response_reader = response_reader

    @classmethod
    def create(cls) -> ControllerEnvironmentIPC:
        raw_fds: list[int] = []
        streams: list[BinaryIO] = []
        try:
            request_read, request_write = os.pipe()
            raw_fds.extend((request_read, request_write))
            response_read, response_write = os.pipe()
            raw_fds.extend((response_read, response_write))
            request_stream_fd = os.dup(request_write)
            raw_fds.append(request_stream_fd)
            os.set_blocking(request_stream_fd, False)
            request_writer = cast(
                BinaryIO,
                os.fdopen(request_stream_fd, "wb", buffering=0),
            )
            raw_fds.remove(request_stream_fd)
            streams.append(request_writer)
            response_stream_fd = os.dup(response_read)
            raw_fds.append(response_stream_fd)
            os.set_blocking(response_stream_fd, False)
            response_reader = cast(
                BinaryIO,
                os.fdopen(response_stream_fd, "rb", buffering=0),
            )
            raw_fds.remove(response_stream_fd)
            streams.append(response_reader)
            raw_fds.remove(request_write)
            os.close(request_write)
            raw_fds.remove(response_read)
            os.close(response_read)
            return cls(
                request_read_fd=request_read,
                response_write_fd=response_write,
                request_writer=request_writer,
                response_reader=response_reader,
            )
        except BaseException as primary:
            errors: list[BaseException] = [primary]
            for stream in streams:
                try:
                    stream.close()
                except BaseException as exc:
                    errors.append(exc)
            while raw_fds:
                descriptor = raw_fds.pop()
                try:
                    os.close(descriptor)
                except BaseException as exc:
                    errors.append(exc)
            raise BaseExceptionGroup("environment IPC creation failed", errors)

    @property
    def child_fds(self) -> tuple[int, int]:
        if self._request_read_fd is None or self._response_write_fd is None:
            raise RuntimeError("child IPC endpoints were released")
        return self._request_read_fd, self._response_write_fd

    def release_child_ends(self) -> None:
        errors: list[BaseException] = []
        for name in ("_request_read_fd", "_response_write_fd"):
            descriptor = getattr(self, name)
            setattr(self, name, None)
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except BaseException as exc:
                    errors.append(exc)
        if errors:
            raise BaseExceptionGroup("child IPC release failed", errors)

    def exchange(self, operation: str, **values: object) -> object:
        if self._request_writer.closed or self._response_reader.closed:
            raise RuntimeError("environment IPC is closed")
        message = {"operation": operation, **values}
        payload = canonical_json_bytes(message, indent=None)
        if payload.endswith(b"\n"):
            payload = payload[:-1]
        try:
            _write_frame_fd(
                self._request_writer.fileno(),
                payload,
                timeout_seconds=_IPC_TIMEOUT_SECONDS,
            )
            frame = _read_frame_fd(
                self._response_reader.fileno(),
                timeout_seconds=_IPC_TIMEOUT_SECONDS,
            )
            if frame is None:
                raise EOFError("synthetic environment response ended")
            response = _strict_compact_json(frame)
        except (EOFError, OSError, TimeoutError, ValueError) as exc:
            raise RecordValidationError(
                "synthetic environment IPC frame is invalid"
            ) from exc
        if (
            type(response) is not dict
            or type(response.get("ok")) is not bool
            or set(response) not in ({"ok", "value"}, {"error", "ok"})
        ):
            raise RecordValidationError("synthetic environment returned open IPC")
        if response["ok"] is not True:
            raise RecordValidationError(
                f"synthetic environment rejected operation: {response['error']}"
            )
        return response["value"]

    def close(self) -> None:
        errors: list[BaseException] = []
        for stream in (self._request_writer, self._response_reader):
            try:
                stream.close()
            except BaseException as exc:
                errors.append(exc)
        for name in (
            "_request_read_fd",
            "_response_write_fd",
        ):
            descriptor = getattr(self, name)
            setattr(self, name, None)
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except BaseException as exc:
                    errors.append(exc)
        if errors:
            raise BaseExceptionGroup("environment IPC cleanup failed", errors)


@final
@dataclass(frozen=True, slots=True, init=False)
class SyntheticEnvironmentFactory:
    """Exact registered command and handle binder for the sealed worker."""

    _task_input_bytes: bytes
    _program_bytes: bytes
    _program_sha256: str
    _implementation_source_sha256: str
    _seal: tuple[str, str, str]

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticEnvironmentFactory is final")

    def __init__(
        self,
        *,
        task_input_bytes: bytes,
        program_bytes: bytes,
        implementation_source_sha256: str,
    ) -> None:
        task_bytes = _exact_bytes(task_input_bytes, "task_input_bytes")
        sealed_program_bytes = _exact_bytes(program_bytes, "program_bytes")
        if (
            type(implementation_source_sha256) is not str
            or len(implementation_source_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in implementation_source_sha256
            )
        ):
            raise ValueError("implementation source digest is not canonical")
        task_sha256 = hashlib.sha256(task_bytes).hexdigest()
        program_sha256 = hashlib.sha256(sealed_program_bytes).hexdigest()
        object.__setattr__(self, "_task_input_bytes", task_bytes)
        object.__setattr__(self, "_program_bytes", sealed_program_bytes)
        object.__setattr__(self, "_program_sha256", program_sha256)
        object.__setattr__(
            self,
            "_implementation_source_sha256",
            implementation_source_sha256,
        )
        object.__setattr__(
            self,
            "_seal",
            (task_sha256, program_sha256, implementation_source_sha256),
        )

    def _verify_seal(self) -> None:
        observed = (
            hashlib.sha256(self._task_input_bytes).hexdigest(),
            hashlib.sha256(self._program_bytes).hexdigest(),
            self._implementation_source_sha256,
        )
        if observed != self._seal or self._program_sha256 != self._seal[1]:
            raise RecordValidationError("factory state differs from sealed bytes")

    def command(
        self,
        *,
        task_input_bytes: bytes,
        program_bytes: bytes,
    ) -> tuple[str, ...]:
        self._verify_seal()
        if (
            _exact_bytes(task_input_bytes, "task_input_bytes") != self._task_input_bytes
            or _exact_bytes(program_bytes, "program_bytes") != self._program_bytes
        ):
            raise RecordValidationError(
                "factory command bytes differ from sealed bytes"
            )
        return (
            sys.executable,
            "-I",
            str(Path(__file__)),
            "--synthetic-worker",
            "--task-sha256",
            hashlib.sha256(task_input_bytes).hexdigest(),
            "--program-sha256",
            self._program_sha256,
            "--source-sha256",
            self._implementation_source_sha256,
        )

    def bind(
        self,
        *,
        process: subprocess.Popen[bytes],
        ipc: ControllerEnvironmentIPC,
        writable_root_fd: int,
        instance_ordinal: int,
    ) -> SyntheticEnvironmentHandle:
        self._verify_seal()
        if type(process) is not subprocess.Popen:
            raise TypeError("process must be the controller's exact Popen")
        if type(ipc) is not ControllerEnvironmentIPC:
            raise TypeError("ipc must be exact ControllerEnvironmentIPC")
        if type(writable_root_fd) is not int:
            raise TypeError("writable_root_fd must be exact int")
        metadata = os.fstat(writable_root_fd)
        if not stat.S_ISDIR(metadata.st_mode):
            raise RecordValidationError("writable root fd is not a directory")
        if type(instance_ordinal) is not int or instance_ordinal < 0:
            raise ValueError("instance_ordinal must be a nonnegative exact int")
        return SyntheticEnvironmentHandle(
            process=process,
            ipc=ipc,
            task_input_bytes=self._task_input_bytes,
            program_bytes=self._program_bytes,
        )


@final
class SyntheticEnvironmentHandle:
    """Closed controller-facing operations for one exact worker."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticEnvironmentHandle is final")

    def __init__(
        self,
        *,
        process: subprocess.Popen[bytes],
        ipc: ControllerEnvironmentIPC,
        task_input_bytes: bytes,
        program_bytes: bytes,
    ) -> None:
        self._process = process
        self._ipc = ipc
        self._task_input_bytes = task_input_bytes
        self._program_bytes = program_bytes
        self._closed = False
        self._started = False

    def start(self) -> None:
        self._ipc.exchange(
            "start",
            task_input_bytes=base64.b64encode(self._task_input_bytes).decode("ascii"),
            program_bytes=base64.b64encode(self._program_bytes).decode("ascii"),
        )
        self._started = True

    def snapshot(self) -> bytes:
        value = self._ipc.exchange("snapshot")
        if type(value) is not str:
            raise RecordValidationError("snapshot response must be encoded text")
        try:
            return base64.b64decode(value, validate=True)
        except ValueError as exc:
            raise RecordValidationError("snapshot response is not base64") from exc

    def restore(self, snapshot_bytes: bytes) -> None:
        self._ipc.exchange(
            "restore",
            snapshot_bytes=base64.b64encode(
                _exact_bytes(snapshot_bytes, "snapshot_bytes")
            ).decode("ascii"),
        )

    def visible_context(self) -> bytes:
        value = self._ipc.exchange("visible_context")
        if type(value) is not str:
            raise RecordValidationError("visible context must be encoded text")
        return base64.b64decode(value, validate=True)

    def simulator_context(self) -> bytes | None:
        value = self._ipc.exchange("simulator_context")
        if value is None:
            return None
        if type(value) is not str:
            raise RecordValidationError(
                "simulator context must be encoded text or null"
            )
        return base64.b64decode(value, validate=True)

    def mutation_committed(self) -> bool:
        return self._boolean_query("mutation_committed")

    def verifier_eligible(self) -> bool:
        return self._boolean_query("verifier_eligible")

    def episode_terminal(self) -> bool:
        return self._boolean_query("episode_terminal")

    def failure_kind(self) -> FailureKind:
        value = self._ipc.exchange("failure_kind")
        try:
            return FailureKind(value)
        except (TypeError, ValueError) as exc:
            raise RecordValidationError("worker returned unknown failure kind") from exc

    def _boolean_query(self, operation: str) -> bool:
        value = self._ipc.exchange(operation)
        if type(value) is not bool:
            raise RecordValidationError(f"{operation} must return exact bool")
        return value

    def close(self) -> None:
        if self._closed:
            raise RuntimeError("synthetic environment handle closed more than once")
        self._closed = True
        if self._started:
            self._ipc.exchange("close")


@dataclass(frozen=True, slots=True)
class _SnapshotState:
    program_sha256: str
    visible_context: bytes
    simulator_context: bytes | None
    turns: tuple[object, ...]
    branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    episode_terminal: bool
    failure_kind: FailureKind


@dataclass(frozen=True, slots=True)
class _InitialObservation:
    snapshot_bytes: bytes
    resnapshot_bytes: bytes
    visible_context: bytes
    restored_visible_context: bytes
    simulator_context: bytes | None
    restored_simulator_context: bytes | None
    token_ids: tuple[int, ...]
    restored_token_ids: tuple[int, ...]
    branch_pending_calls: tuple[ToolCall, ...]
    restored_branch_pending_calls: tuple[ToolCall, ...]
    terminal_unexecuted_remainder: tuple[ToolCall, ...]
    restored_terminal_unexecuted_remainder: tuple[ToolCall, ...]
    episode_terminal: bool
    restored_episode_terminal: bool
    failure_kind: FailureKind
    restored_failure_kind: FailureKind
    mutation_committed: bool
    restored_mutation_committed: bool
    verifier_eligible: bool
    restored_verifier_eligible: bool


def _decode_calls(value: object, field: str) -> tuple[ToolCall, ...]:
    if type(value) is not list:
        raise RecordValidationError(f"{field} must be an array")
    calls: list[ToolCall] = []
    for item in value:
        if type(item) is not dict or set(item) != {
            "call_id",
            "canonical_arguments_json",
            "name",
        }:
            raise RecordValidationError(f"{field} contains an open tool call")
        calls.append(
            ToolCall(
                call_id=item["call_id"],
                name=item["name"],
                canonical_arguments_json=item["canonical_arguments_json"],
            )
        )
    return tuple(calls)


def _decode_snapshot_state(payload: bytes) -> _SnapshotState:
    try:
        compact_payload = payload[:-1] if payload.endswith(b"\n") else payload
        value = _strict_compact_json(compact_payload)
    except ValueError as exc:
        raise RecordValidationError("environment snapshot is not strict JSON") from exc
    expected = {
        "branch_pending_calls",
        "episode_terminal",
        "failure_kind",
        "program_sha256",
        "simulator_context",
        "terminal_unexecuted_remainder",
        "turns",
        "visible_context",
    }
    if type(value) is not dict or set(value) != expected:
        raise RecordValidationError("environment snapshot has an open shape")
    if canonical_json_bytes(value, indent=None) != payload:
        raise RecordValidationError("environment snapshot is not canonical")
    program_sha256 = value["program_sha256"]
    if (
        type(program_sha256) is not str
        or len(program_sha256) != 64
        or any(character not in "0123456789abcdef" for character in program_sha256)
    ):
        raise RecordValidationError("snapshot program digest is not canonical")
    try:
        visible_context = _worker_decoded(value["visible_context"])
        simulator_value = value["simulator_context"]
        simulator_context = (
            None if simulator_value is None else _worker_decoded(simulator_value)
        )
    except (TypeError, ValueError) as exc:
        raise RecordValidationError("snapshot context encoding is invalid") from exc
    turns_value = value["turns"]
    if type(turns_value) is not list:
        raise RecordValidationError("snapshot turns must be one exact array")
    if type(value["episode_terminal"]) is not bool:
        raise RecordValidationError("snapshot terminal state must be exact bool")
    try:
        failure_kind = FailureKind(value["failure_kind"])
    except (TypeError, ValueError) as exc:
        raise RecordValidationError("snapshot failure kind is unknown") from exc
    return _SnapshotState(
        program_sha256=program_sha256,
        visible_context=visible_context,
        simulator_context=simulator_context,
        turns=tuple(turns_value),
        branch_pending_calls=_decode_calls(
            value["branch_pending_calls"],
            "branch_pending_calls",
        ),
        terminal_unexecuted_remainder=_decode_calls(
            value["terminal_unexecuted_remainder"],
            "terminal_unexecuted_remainder",
        ),
        episode_terminal=value["episode_terminal"],
        failure_kind=failure_kind,
    )


def _validate_initial_observation(observation: _InitialObservation) -> None:
    if type(observation) is not _InitialObservation:
        raise TypeError("observation must be exact _InitialObservation")
    comparisons = (
        ("snapshot bytes", observation.snapshot_bytes, observation.resnapshot_bytes),
        (
            "visible context",
            observation.visible_context,
            observation.restored_visible_context,
        ),
        (
            "simulator context",
            observation.simulator_context,
            observation.restored_simulator_context,
        ),
        ("token IDs", observation.token_ids, observation.restored_token_ids),
        (
            "branch queue",
            observation.branch_pending_calls,
            observation.restored_branch_pending_calls,
        ),
        (
            "terminal remainder",
            observation.terminal_unexecuted_remainder,
            observation.restored_terminal_unexecuted_remainder,
        ),
        (
            "terminal state",
            observation.episode_terminal,
            observation.restored_episode_terminal,
        ),
        (
            "failure state",
            observation.failure_kind,
            observation.restored_failure_kind,
        ),
    )
    for label, initial, restored in comparisons:
        if initial != restored:
            raise ValueError(f"initial restore {label} mismatch")
    if observation.failure_kind is not FailureKind.NONE:
        raise ValueError("initial restore qualification requires no failure")
    if (
        observation.mutation_committed
        or observation.restored_mutation_committed
        or observation.verifier_eligible
        or observation.restored_verifier_eligible
    ):
        raise ValueError("initial restore must start without mutation or eligibility")


@dataclass(frozen=True, slots=True)
class _OwnedEnvironment:
    handle: SyntheticEnvironmentHandle
    process: subprocess.Popen[bytes]
    ipc: ControllerEnvironmentIPC
    root_fd: int
    workspace_fd: int
    root_name: str
    identity: EnvironmentProcessIdentity


def _assert_pairwise_isolated(instances: tuple[_OwnedEnvironment, ...]) -> None:
    objects: set[int] = set()
    pids: set[int] = set()
    roots: set[tuple[int, int]] = set()
    for instance in instances:
        object_identity = id(instance.handle)
        if object_identity in objects:
            raise ValueError("environment object identity is aliased")
        objects.add(object_identity)
        if instance.process.poll() is not None:
            raise ValueError("environment process is not live")
        if instance.process.pid != instance.identity.child_pid:
            raise ValueError("environment PID differs from controller Popen")
        if instance.identity.child_pid in pids:
            raise ValueError("environment PID is aliased")
        pids.add(instance.identity.child_pid)
        metadata = os.fstat(instance.root_fd)
        root_identity = (metadata.st_dev, metadata.st_ino)
        expected_root = (
            instance.identity.writable_root_st_dev,
            instance.identity.writable_root_st_ino,
        )
        if root_identity != expected_root:
            raise ValueError("environment root identity changed")
        named = os.stat(
            instance.root_name,
            dir_fd=instance.workspace_fd,
            follow_symlinks=False,
        )
        if (
            not stat.S_ISDIR(named.st_mode)
            or (
                named.st_dev,
                named.st_ino,
            )
            != root_identity
        ):
            raise ValueError("environment root name no longer binds held root")
        if root_identity in roots:
            raise ValueError("environment root identity is aliased")
        roots.add(root_identity)


def _open_root(run_root: Path) -> tuple[Path, int]:
    root = Path(run_root)
    absolute_root = root.absolute()
    metadata = os.stat(root, follow_symlinks=False)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RecordValidationError("run root must be a non-symlink directory")
    descriptor = os.open(root, _DIRECTORY_FLAGS)
    try:
        bound = os.fstat(descriptor)
        if (bound.st_dev, bound.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise RecordValidationError("run root identity changed during binding")
    except BaseException as primary:
        try:
            os.close(descriptor)
        except BaseException as cleanup:
            raise BaseExceptionGroup(
                "run root binding and cleanup failed",
                [primary, cleanup],
            ) from None
        raise
    return absolute_root, descriptor


def _open_workspace(root_fd: int) -> int:
    try:
        os.mkdir(_WORKSPACE_NAME, mode=0o700, dir_fd=root_fd)
        os.fsync(root_fd)
    except FileExistsError:
        pass
    try:
        workspace_fd = os.open(_WORKSPACE_NAME, _DIRECTORY_FLAGS, dir_fd=root_fd)
    except OSError as exc:
        raise RecordValidationError("environment workspace is unsafe") from exc
    try:
        if not stat.S_ISDIR(os.fstat(workspace_fd).st_mode):
            raise RecordValidationError("environment workspace is not a directory")
    except BaseException as primary:
        try:
            os.close(workspace_fd)
        except BaseException as cleanup:
            raise BaseExceptionGroup(
                "environment workspace binding and cleanup failed",
                [primary, cleanup],
            ) from None
        raise
    return workspace_fd


def _directory_identity(metadata: os.stat_result) -> tuple[int, int]:
    if not stat.S_ISDIR(metadata.st_mode):
        raise RecordValidationError("environment root is not a directory")
    return metadata.st_dev, metadata.st_ino


def _cleanup_owned_root(
    *,
    workspace_fd: int,
    root_name: str,
    expected_identity: tuple[int, int] | None,
    root_fd: int | None,
    allow_removal: bool = True,
) -> list[BaseException]:
    errors: list[BaseException] = []
    named_is_owned = False
    if expected_identity is None:
        errors.append(
            RecordValidationError(
                "residual uncertainty: created root identity was not observed"
            )
        )
    else:
        try:
            named_is_owned = (
                _directory_identity(
                    os.stat(
                        root_name,
                        dir_fd=workspace_fd,
                        follow_symlinks=False,
                    )
                )
                == expected_identity
            )
            if not named_is_owned:
                errors.append(
                    RecordValidationError(
                        "residual uncertainty: root name no longer binds owned inode"
                    )
                )
        except BaseException as exc:
            errors.append(exc)
    held_is_owned = False
    if root_fd is not None:
        try:
            held_is_owned = _directory_identity(os.fstat(root_fd)) == expected_identity
            if not held_is_owned:
                errors.append(
                    RecordValidationError(
                        "residual uncertainty: held root identity changed"
                    )
                )
        except BaseException as exc:
            errors.append(exc)
        if held_is_owned and allow_removal:
            try:
                _clear_directory(root_fd)
            except BaseException as exc:
                errors.append(exc)
    if not allow_removal:
        errors.append(
            RecordValidationError(
                "writable root preserved because process reap is uncertain"
            )
        )
    if allow_removal and named_is_owned and (root_fd is None or held_is_owned):
        try:
            os.rmdir(root_name, dir_fd=workspace_fd)
        except BaseException as exc:
            errors.append(exc)
    if root_fd is not None:
        try:
            os.close(root_fd)
        except BaseException as exc:
            errors.append(exc)
    try:
        os.fsync(workspace_fd)
    except BaseException as exc:
        errors.append(exc)
    return errors


def _allocate_root(
    *,
    workspace_fd: int,
    ordinal: int,
) -> tuple[str, int, tuple[int, int]]:
    for suffix in range(_ROOT_SUFFIX_ATTEMPTS):
        root_name = f"instance-{ordinal:04d}-{suffix:02d}"
        try:
            os.mkdir(root_name, mode=0o700, dir_fd=workspace_fd)
        except FileExistsError:
            continue
        expected_identity: tuple[int, int] | None = None
        root_fd: int | None = None
        try:
            expected_identity = _directory_identity(
                os.stat(
                    root_name,
                    dir_fd=workspace_fd,
                    follow_symlinks=False,
                )
            )
            os.fsync(workspace_fd)
            root_fd = os.open(root_name, _DIRECTORY_FLAGS, dir_fd=workspace_fd)
            if _directory_identity(os.fstat(root_fd)) != expected_identity:
                raise RecordValidationError(
                    "new environment root identity changed during open"
                )
            if (
                _directory_identity(
                    os.stat(
                        root_name,
                        dir_fd=workspace_fd,
                        follow_symlinks=False,
                    )
                )
                != expected_identity
            ):
                raise RecordValidationError(
                    "new environment root name changed during open"
                )
            return root_name, root_fd, expected_identity
        except BaseException as primary:
            cleanup_errors = _cleanup_owned_root(
                workspace_fd=workspace_fd,
                root_name=root_name,
                expected_identity=expected_identity,
                root_fd=root_fd,
            )
            message = (
                "environment root allocation failed with residual uncertainty"
                if cleanup_errors
                else "environment root allocation failed"
            )
            raise BaseExceptionGroup(message, [primary, *cleanup_errors])
    raise RecordValidationError("environment root suffix search exhausted")


@dataclass(frozen=True, slots=True)
class _ProcessCleanupResult:
    errors: tuple[BaseException, ...]
    reaped: bool


def _cleanup_process(
    process: subprocess.Popen[bytes],
) -> _ProcessCleanupResult:
    errors: list[BaseException] = []
    try:
        observed_returncode = process.poll()
        if observed_returncode is not None:
            if observed_returncode != 0:
                errors.append(
                    RecordValidationError(
                        "environment process exited nonzero before cleanup"
                    )
                )
            return _ProcessCleanupResult(tuple(errors), True)
    except BaseException as exc:
        errors.append(exc)
    try:
        process.terminate()
    except BaseException as exc:
        errors.append(exc)
    try:
        process.wait(timeout=1)
        return _ProcessCleanupResult(tuple(errors), True)
    except subprocess.TimeoutExpired:
        pass
    except BaseException as exc:
        errors.append(exc)
        try:
            observed_returncode = process.poll()
        except BaseException as poll_error:
            errors.append(poll_error)
            errors.append(
                RecordValidationError(
                    "environment process reap state remains uncertain"
                )
            )
            return _ProcessCleanupResult(tuple(errors), False)
        if observed_returncode is not None:
            return _ProcessCleanupResult(tuple(errors), True)
    try:
        process.kill()
    except BaseException as exc:
        errors.append(exc)
    try:
        process.wait(timeout=1)
    except BaseException as exc:
        errors.append(exc)
        errors.append(
            RecordValidationError(
                "environment process was not confirmed reaped"
            )
        )
        return _ProcessCleanupResult(tuple(errors), False)
    return _ProcessCleanupResult(tuple(errors), True)


class _EnvironmentFleet:
    def __init__(
        self,
        *,
        run_root: Path,
        factory: SyntheticEnvironmentFactory,
        task_input_bytes: bytes,
        program_bytes: bytes,
    ) -> None:
        self._root, self._root_fd = _open_root(run_root)
        try:
            self._workspace_fd = _open_workspace(self._root_fd)
        except BaseException as primary:
            try:
                os.close(self._root_fd)
            except BaseException as cleanup:
                raise BaseExceptionGroup(
                    "environment workspace setup and root cleanup failed",
                    [primary, cleanup],
                ) from None
            raise
        self._factory = factory
        self._task_input_bytes = _exact_bytes(task_input_bytes, "task_input_bytes")
        self._program_bytes = _exact_bytes(program_bytes, "program_bytes")
        self.instances: list[_OwnedEnvironment] = []
        self._closed = False

    def spawn(self, ordinal: int) -> _OwnedEnvironment:
        root_name, root_fd, root_identity = _allocate_root(
            workspace_fd=self._workspace_fd,
            ordinal=ordinal,
        )
        ipc: ControllerEnvironmentIPC | None = None
        process: subprocess.Popen[bytes] | None = None
        try:
            ipc = ControllerEnvironmentIPC.create()
            request_read, response_write = ipc.child_fds
            command = (
                *self._factory.command(
                    task_input_bytes=self._task_input_bytes,
                    program_bytes=self._program_bytes,
                ),
                "--request-fd",
                str(request_read),
                "--response-fd",
                str(response_write),
            )
            process = subprocess.Popen(
                command,
                close_fds=True,
                pass_fds=(request_read, response_write),
                cwd=f"/proc/self/fd/{root_fd}",
                env={},
            )
            ipc.release_child_ends()
            identity = EnvironmentProcessIdentity(
                instance_ordinal=ordinal,
                writable_root_relative_path=(f"{_WORKSPACE_NAME}/{root_name}"),
                writable_root_st_dev=root_identity[0],
                writable_root_st_ino=root_identity[1],
                child_pid=process.pid,
            )
            handle = self._factory.bind(
                process=process,
                ipc=ipc,
                writable_root_fd=root_fd,
                instance_ordinal=ordinal,
            )
            instance = _OwnedEnvironment(
                handle=handle,
                process=process,
                ipc=ipc,
                root_fd=root_fd,
                workspace_fd=self._workspace_fd,
                root_name=root_name,
                identity=identity,
            )
            self.instances.append(instance)
            return instance
        except BaseException as primary:
            errors: list[BaseException] = [primary]
            if ipc is not None:
                try:
                    ipc.close()
                except BaseException as exc:
                    errors.append(exc)
            if process is not None:
                process_cleanup = _cleanup_process(process)
                errors.extend(process_cleanup.errors)
            else:
                process_cleanup = None
            errors.extend(
                _cleanup_owned_root(
                    workspace_fd=self._workspace_fd,
                    root_name=root_name,
                    expected_identity=root_identity,
                    root_fd=root_fd,
                    allow_removal=(
                        process_cleanup is None or process_cleanup.reaped
                    ),
                )
            )
            raise BaseExceptionGroup("environment spawn failed", errors)

    def close(self, primary: BaseException | None = None) -> None:
        if self._closed:
            if primary is not None:
                raise primary
            return
        self._closed = True
        errors: list[BaseException] = []
        if primary is not None:
            errors.append(primary)
        for instance in self.instances:
            try:
                instance.handle.close()
            except BaseException as exc:
                errors.append(exc)
            try:
                instance.ipc.close()
            except BaseException as exc:
                errors.append(exc)
            process_cleanup = _cleanup_process(instance.process)
            errors.extend(process_cleanup.errors)
            errors.extend(
                _cleanup_owned_root(
                    workspace_fd=self._workspace_fd,
                    root_name=instance.root_name,
                    expected_identity=(
                        instance.identity.writable_root_st_dev,
                        instance.identity.writable_root_st_ino,
                    ),
                    root_fd=instance.root_fd,
                    allow_removal=process_cleanup.reaped,
                )
            )
        try:
            os.close(self._workspace_fd)
        except BaseException as exc:
            errors.append(exc)
        try:
            os.close(self._root_fd)
        except BaseException as exc:
            errors.append(exc)
        if errors:
            raise BaseExceptionGroup("environment qualification failed", errors)


def _clear_directory(directory_fd: int) -> None:
    for name in os.listdir(directory_fd):
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if stat.S_ISDIR(metadata.st_mode):
            child = os.open(name, _DIRECTORY_FLAGS, dir_fd=directory_fd)
            try:
                _clear_directory(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=directory_fd)
        else:
            os.unlink(name, dir_fd=directory_fd)
    os.fsync(directory_fd)


@dataclass(slots=True)
class _InitialQualificationResult:
    receipt: InitialRestoreQualificationReceipt
    receipt_ref: ArtifactRef
    _resources: tuple[_OwnedEnvironment, ...]
    _fleet: _EnvironmentFleet | None
    _provenances: tuple[StableSourceProvenance, ...]

    def close(self) -> None:
        fleet = self._fleet
        self._fleet = None
        provenances = self._provenances
        self._provenances = ()
        _close_qualification_lifecycle(
            fleet=fleet,
            provenances=provenances,
        )


def _close_qualification_lifecycle(
    *,
    fleet: _EnvironmentFleet | None,
    provenances: tuple[StableSourceProvenance, ...],
    primary: BaseException | None = None,
) -> None:
    errors: list[BaseException] = []
    if primary is not None:
        errors.append(primary)
    if fleet is not None:
        try:
            fleet.close()
        except BaseException as exc:
            errors.append(exc)
    for provenance in provenances:
        try:
            provenance.verify_again()
        except BaseException as exc:
            errors.append(exc)
    for provenance in provenances:
        try:
            provenance.close()
        except BaseException as exc:
            errors.append(exc)
    if errors:
        raise BaseExceptionGroup(
            "initial qualification lifecycle failed",
            errors,
        )


def _observe_initial(
    live: _OwnedEnvironment,
    restored: _OwnedEnvironment,
    tokenizer: SyntheticByteTokenizer,
    program_sha256: str,
) -> _InitialObservation:
    live.handle.start()
    snapshot = live.handle.snapshot()
    visible = live.handle.visible_context()
    simulator_context = live.handle.simulator_context()
    live_state = _decode_snapshot_state(snapshot)
    if (
        live_state.program_sha256 != program_sha256
        or live_state.visible_context != visible
        or live_state.simulator_context != simulator_context
        or live_state.turns
    ):
        raise ValueError("initial restore live embedded snapshot state mismatch")
    if (
        live.handle.episode_terminal() != live_state.episode_terminal
        or live.handle.failure_kind() is not live_state.failure_kind
    ):
        raise ValueError("initial restore live state query mismatch")
    restored.handle.start()
    restored.handle.restore(snapshot)
    resnapshot = restored.handle.snapshot()
    restored_visible = restored.handle.visible_context()
    restored_simulator_context = restored.handle.simulator_context()
    restored_state = _decode_snapshot_state(resnapshot)
    if (
        restored_state.program_sha256 != program_sha256
        or restored_state.visible_context != restored_visible
        or restored_state.simulator_context != restored_simulator_context
        or restored_state.turns
    ):
        raise ValueError("initial restore fresh embedded snapshot state mismatch")
    if (
        restored.handle.episode_terminal() != restored_state.episode_terminal
        or restored.handle.failure_kind() is not restored_state.failure_kind
    ):
        raise ValueError("initial restore fresh state query mismatch")
    return _InitialObservation(
        snapshot_bytes=snapshot,
        resnapshot_bytes=resnapshot,
        visible_context=visible,
        restored_visible_context=restored_visible,
        simulator_context=simulator_context,
        restored_simulator_context=restored_simulator_context,
        token_ids=tokenizer.encode(visible),
        restored_token_ids=tokenizer.encode(restored_visible),
        branch_pending_calls=live_state.branch_pending_calls,
        restored_branch_pending_calls=restored_state.branch_pending_calls,
        terminal_unexecuted_remainder=live_state.terminal_unexecuted_remainder,
        restored_terminal_unexecuted_remainder=(
            restored_state.terminal_unexecuted_remainder
        ),
        episode_terminal=live_state.episode_terminal,
        restored_episode_terminal=restored_state.episode_terminal,
        failure_kind=live_state.failure_kind,
        restored_failure_kind=restored_state.failure_kind,
        mutation_committed=live.handle.mutation_committed(),
        restored_mutation_committed=restored.handle.mutation_committed(),
        verifier_eligible=live.handle.verifier_eligible(),
        restored_verifier_eligible=restored.handle.verifier_eligible(),
    )


def _qualify_initial_restore(
    *,
    run_root: Path,
    authority: InitialQualificationAuthority,
) -> _InitialQualificationResult:
    """Execute the private S02C-b qualification transaction."""

    result = _open_qualified_initial_restore(
        run_root=run_root,
        authority=authority,
    )
    result.close()
    result._resources = ()
    return result


def _open_qualified_initial_restore(
    *,
    run_root: Path,
    authority: InitialQualificationAuthority,
) -> _InitialQualificationResult:
    """Open a qualified live/restored pair for the internal prefix controller."""

    if type(authority) is not InitialQualificationAuthority:
        raise TypeError("authority must be exact InitialQualificationAuthority")
    authority.verify_seal()
    provenances: list[StableSourceProvenance] = []
    try:
        for descriptor in (
            authority.environment_descriptor,
            authority.tokenizer_descriptor,
        ):
            provenances.append(
                StableSourceProvenance(
                    _SOURCE_ROOT,
                    _SOURCE_PATH,
                    descriptor.implementation_source_ref,
                )
            )
    except BaseException as primary:
        _close_qualification_lifecycle(
            fleet=None,
            provenances=tuple(provenances),
            primary=primary,
        )
        raise AssertionError("unreachable")
    return _qualify_with_provenance(
        run_root=run_root,
        authority=authority,
        provenances=tuple(provenances),
    )


def _qualify_with_provenance(
    *,
    run_root: Path,
    authority: InitialQualificationAuthority,
    provenances: tuple[StableSourceProvenance, ...],
) -> _InitialQualificationResult:
    fleet: _EnvironmentFleet | None = None
    try:
        factory = SyntheticEnvironmentFactory(
            task_input_bytes=authority.task_input_bytes,
            program_bytes=authority.program_bytes,
            implementation_source_sha256=(
                authority.environment_descriptor.implementation_source_ref.sha256
            ),
        )
        tokenizer = SyntheticByteTokenizer()
        fleet = _EnvironmentFleet(
            run_root=run_root,
            factory=factory,
            task_input_bytes=authority.task_input_bytes,
            program_bytes=authority.program_bytes,
        )
        live = fleet.spawn(0)
        restored = fleet.spawn(1)
        observation = _observe_initial(
            live,
            restored,
            tokenizer,
            hashlib.sha256(authority.program_bytes).hexdigest(),
        )
        _validate_initial_observation(observation)
        _assert_pairwise_isolated((live, restored))
        token_bytes = canonical_json_bytes(
            {"token_ids": list(observation.token_ids)},
            indent=None,
        )
        authority.verify_seal()
        with ControllerArtifactStore(run_root) as store:
            snapshot_ref = store.write(
                role="environment_snapshot",
                payload=observation.snapshot_bytes,
                media_type="application/octet-stream",
            )
            visible_ref = store.write(
                role="visible_context",
                payload=observation.visible_context,
                media_type="application/json",
            )
            token_ref = store.write(
                role="token_ids",
                payload=token_bytes,
                media_type="application/json",
            )
            receipt = InitialRestoreQualificationReceipt(
                schedule_ref=authority.schedule_ref,
                task_ref=authority.task_ref,
                task_input_ref=authority.task_input_ref,
                environment_contract_ref=authority.environment_contract_ref,
                isolation_contract_ref=authority.isolation_contract_ref,
                initial_environment_snapshot_ref=snapshot_ref,
                observed_resnapshot_sha256=hashlib.sha256(
                    observation.resnapshot_bytes
                ).hexdigest(),
                observed_resnapshot_byte_count=len(observation.resnapshot_bytes),
                visible_context_ref=visible_ref,
                visible_sha256=hashlib.sha256(
                    observation.restored_visible_context
                ).hexdigest(),
                token_ids_ref=token_ref,
                token_ids_sha256=hashlib.sha256(token_bytes).hexdigest(),
                branch_pending_calls=observation.branch_pending_calls,
                terminal_unexecuted_remainder=(
                    observation.terminal_unexecuted_remainder
                ),
                episode_terminal=observation.episode_terminal,
                failure_kind=observation.failure_kind,
                live_identity=live.identity,
                fresh_restore_identity=restored.identity,
                verified=True,
            )
            receipt_ref = store.write(
                role="initial_restore_qualification",
                payload=initial_restore_qualification_receipt_bytes(receipt),
                media_type="application/json",
            )
        _assert_pairwise_isolated((live, restored))
        authority.verify_seal()
        result = _InitialQualificationResult(
            receipt=receipt,
            receipt_ref=receipt_ref,
            _resources=(live, restored),
            _fleet=fleet,
            _provenances=provenances,
        )
    except BaseException as primary:
        _close_qualification_lifecycle(
            fleet=fleet,
            provenances=provenances,
            primary=primary,
        )
        raise AssertionError("unreachable")
    return result


__all__ = [
    "ControllerEnvironmentIPC",
    "InitialQualificationAuthority",
    "SyntheticEnvironmentFactory",
    "SyntheticEnvironmentHandle",
    "SyntheticByteTokenizer",
]
