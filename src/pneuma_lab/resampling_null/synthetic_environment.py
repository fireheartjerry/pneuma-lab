"""Controller-owned subprocess fixture and initial-restore qualification.

This module is local synthetic-validation machinery only. It performs no
provider, model, network, experiment, spend, branch, or publication action.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import final

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .controller_artifacts import ControllerArtifactStore
from .errors import RecordValidationError
from .prefix_contracts import (
    EnvironmentProcessIdentity,
    ImplementationDescriptor,
    InitialRestoreQualificationReceipt,
    StableSourceProvenance,
    initial_restore_qualification_receipt_bytes,
)
from .types import ArtifactRef, FailureKind, ToolCall


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_ROOT_SUFFIX_ATTEMPTS = 16
_WORKSPACE_NAME = "prefix-environments"
_WORKER = Path(__file__).with_name("_synthetic_environment_worker.py")
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

    def __post_init__(self) -> None:
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
        request_write_fd: int,
        response_read_fd: int,
        response_write_fd: int,
    ) -> None:
        self._request_read_fd: int | None = request_read_fd
        self._request_write_fd: int | None = request_write_fd
        self._response_read_fd: int | None = response_read_fd
        self._response_write_fd: int | None = response_write_fd
        self._request_writer = os.fdopen(
            os.dup(request_write_fd),
            "wb",
            buffering=0,
        )
        self._response_reader = os.fdopen(
            os.dup(response_read_fd),
            "rb",
            buffering=0,
        )

    @classmethod
    def create(cls) -> ControllerEnvironmentIPC:
        request_read, request_write = os.pipe()
        response_read, response_write = os.pipe()
        return cls(
            request_read_fd=request_read,
            request_write_fd=request_write,
            response_read_fd=response_read,
            response_write_fd=response_write,
        )

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
        self._request_writer.write(
            payload if payload.endswith(b"\n") else payload + b"\n"
        )
        line = self._response_reader.readline()
        if not line:
            raise RecordValidationError("synthetic environment IPC ended unexpectedly")
        try:
            response = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RecordValidationError(
                "synthetic environment returned malformed IPC"
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
            "_request_write_fd",
            "_response_read_fd",
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
class SyntheticEnvironmentFactory:
    """Exact registered command and handle binder for the sealed worker."""

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("SyntheticEnvironmentFactory is final")

    def __init__(self, *, task_input_bytes: bytes, program_bytes: bytes) -> None:
        self.task_input_bytes = _exact_bytes(task_input_bytes, "task_input_bytes")
        self.program_bytes = _exact_bytes(program_bytes, "program_bytes")
        self.program_sha256 = hashlib.sha256(self.program_bytes).hexdigest()

    def command(
        self,
        *,
        task_input_bytes: bytes,
        program_bytes: bytes,
    ) -> tuple[str, ...]:
        if (
            _exact_bytes(task_input_bytes, "task_input_bytes") != self.task_input_bytes
            or _exact_bytes(program_bytes, "program_bytes") != self.program_bytes
        ):
            raise RecordValidationError(
                "factory command bytes differ from sealed bytes"
            )
        return (
            sys.executable,
            "-I",
            str(_WORKER),
            "--task-sha256",
            hashlib.sha256(task_input_bytes).hexdigest(),
            "--program-sha256",
            self.program_sha256,
        )

    def bind(
        self,
        *,
        process: subprocess.Popen[bytes],
        ipc: ControllerEnvironmentIPC,
        writable_root_fd: int,
        instance_ordinal: int,
    ) -> SyntheticEnvironmentHandle:
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
            task_input_bytes=self.task_input_bytes,
            program_bytes=self.program_bytes,
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
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
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
    if type(value["episode_terminal"]) is not bool:
        raise RecordValidationError("snapshot terminal state must be exact bool")
    try:
        failure_kind = FailureKind(value["failure_kind"])
    except (TypeError, ValueError) as exc:
        raise RecordValidationError("snapshot failure kind is unknown") from exc
    return _SnapshotState(
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
    metadata = os.stat(root, follow_symlinks=False)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise RecordValidationError("run root must be a non-symlink directory")
    descriptor = os.open(root, _DIRECTORY_FLAGS)
    bound = os.fstat(descriptor)
    if (bound.st_dev, bound.st_ino) != (metadata.st_dev, metadata.st_ino):
        os.close(descriptor)
        raise RecordValidationError("run root identity changed during binding")
    return root.absolute(), descriptor


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
    if not stat.S_ISDIR(os.fstat(workspace_fd).st_mode):
        os.close(workspace_fd)
        raise RecordValidationError("environment workspace is not a directory")
    return workspace_fd


class _EnvironmentFleet:
    def __init__(
        self,
        *,
        run_root: Path,
        factory: SyntheticEnvironmentFactory,
    ) -> None:
        self._root, self._root_fd = _open_root(run_root)
        try:
            self._workspace_fd = _open_workspace(self._root_fd)
        except BaseException:
            os.close(self._root_fd)
            raise
        self._factory = factory
        self.instances: list[_OwnedEnvironment] = []
        self._closed = False

    def spawn(self, ordinal: int) -> _OwnedEnvironment:
        root_fd: int | None = None
        root_name: str | None = None
        for suffix in range(_ROOT_SUFFIX_ATTEMPTS):
            candidate = f"instance-{ordinal:04d}-{suffix:02d}"
            try:
                os.mkdir(candidate, mode=0o700, dir_fd=self._workspace_fd)
            except FileExistsError:
                continue
            root_name = candidate
            os.fsync(self._workspace_fd)
            root_fd = os.open(candidate, _DIRECTORY_FLAGS, dir_fd=self._workspace_fd)
            break
        if root_fd is None or root_name is None:
            raise RecordValidationError("environment root suffix search exhausted")
        ipc: ControllerEnvironmentIPC | None = None
        process: subprocess.Popen[bytes] | None = None
        try:
            ipc = ControllerEnvironmentIPC.create()
            request_read, response_write = ipc.child_fds
            command = (
                *self._factory.command(
                    task_input_bytes=self._factory.task_input_bytes,
                    program_bytes=self._factory.program_bytes,
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
            metadata = os.fstat(root_fd)
            identity = EnvironmentProcessIdentity(
                instance_ordinal=ordinal,
                writable_root_relative_path=(f"{_WORKSPACE_NAME}/{root_name}"),
                writable_root_st_dev=metadata.st_dev,
                writable_root_st_ino=metadata.st_ino,
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
            if process is not None and process.poll() is None:
                try:
                    process.kill()
                    process.wait(timeout=2)
                except BaseException as exc:
                    errors.append(exc)
            try:
                os.close(root_fd)
            except BaseException as exc:
                errors.append(exc)
            try:
                os.rmdir(root_name, dir_fd=self._workspace_fd)
            except BaseException as exc:
                errors.append(exc)
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
            if instance.process.poll() is None:
                try:
                    instance.process.terminate()
                except BaseException as exc:
                    errors.append(exc)
                try:
                    instance.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    try:
                        instance.process.kill()
                    except BaseException as exc:
                        errors.append(exc)
                    try:
                        instance.process.wait(timeout=1)
                    except BaseException as exc:
                        errors.append(exc)
                except BaseException as exc:
                    errors.append(exc)
            root_verified = False
            try:
                metadata = os.fstat(instance.root_fd)
                expected = (
                    instance.identity.writable_root_st_dev,
                    instance.identity.writable_root_st_ino,
                )
                if (metadata.st_dev, metadata.st_ino) != expected:
                    raise RecordValidationError(
                        "owned environment root changed before cleanup"
                    )
                named = os.stat(
                    instance.root_name,
                    dir_fd=self._workspace_fd,
                    follow_symlinks=False,
                )
                if (
                    not stat.S_ISDIR(named.st_mode)
                    or (
                        named.st_dev,
                        named.st_ino,
                    )
                    != expected
                ):
                    raise RecordValidationError(
                        "owned environment root name changed before cleanup"
                    )
                root_verified = True
            except BaseException as exc:
                errors.append(exc)
            if root_verified:
                try:
                    _clear_directory(instance.root_fd)
                except BaseException as exc:
                    errors.append(exc)
            try:
                os.close(instance.root_fd)
            except BaseException as exc:
                errors.append(exc)
            if root_verified:
                try:
                    os.rmdir(instance.root_name, dir_fd=self._workspace_fd)
                    os.fsync(self._workspace_fd)
                except BaseException as exc:
                    errors.append(exc)
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
        errors: list[BaseException] = []
        fleet = self._fleet
        self._fleet = None
        if fleet is not None:
            try:
                fleet.close()
            except BaseException as exc:
                errors.append(exc)
        provenances = self._provenances
        self._provenances = ()
        for provenance in provenances:
            try:
                provenance.close()
            except BaseException as exc:
                errors.append(exc)
        if errors:
            raise BaseExceptionGroup(
                "initial qualification resource cleanup failed",
                errors,
            )


def _observe_initial(
    live: _OwnedEnvironment,
    restored: _OwnedEnvironment,
    tokenizer: SyntheticByteTokenizer,
) -> _InitialObservation:
    live.handle.start()
    snapshot = live.handle.snapshot()
    visible = live.handle.visible_context()
    live_state = _decode_snapshot_state(snapshot)
    if (
        live.handle.episode_terminal() != live_state.episode_terminal
        or live.handle.failure_kind() is not live_state.failure_kind
    ):
        raise ValueError("initial restore live state query mismatch")
    restored.handle.start()
    restored.handle.restore(snapshot)
    resnapshot = restored.handle.snapshot()
    restored_visible = restored.handle.visible_context()
    restored_state = _decode_snapshot_state(resnapshot)
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
        errors: list[BaseException] = [primary]
        for provenance in reversed(provenances):
            try:
                provenance.close()
            except BaseException as exc:
                errors.append(exc)
        raise BaseExceptionGroup("fixture provenance setup failed", errors)
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
    factory = SyntheticEnvironmentFactory(
        task_input_bytes=authority.task_input_bytes,
        program_bytes=authority.program_bytes,
    )
    tokenizer = SyntheticByteTokenizer()
    try:
        fleet = _EnvironmentFleet(run_root=run_root, factory=factory)
    except BaseException as primary:
        cleanup_errors: list[BaseException] = []
        for provenance in provenances:
            try:
                provenance.close()
            except BaseException as exc:
                cleanup_errors.append(exc)
        if cleanup_errors:
            raise BaseExceptionGroup(
                "environment fleet setup and provenance cleanup failed",
                [primary, *cleanup_errors],
            )
        raise
    try:
        live = fleet.spawn(0)
        restored = fleet.spawn(1)
        observation = _observe_initial(live, restored, tokenizer)
        _validate_initial_observation(observation)
        _assert_pairwise_isolated((live, restored))
        token_bytes = canonical_json_bytes(
            {"token_ids": list(observation.token_ids)},
            indent=None,
        )
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
        for provenance in provenances:
            provenance.verify_again()
        _assert_pairwise_isolated((live, restored))
        result = _InitialQualificationResult(
            receipt=receipt,
            receipt_ref=receipt_ref,
            _resources=(live, restored),
            _fleet=fleet,
            _provenances=provenances,
        )
    except BaseException as primary:
        errors: list[BaseException] = [primary]
        try:
            fleet.close()
        except BaseException as exc:
            errors.append(exc)
        for provenance in provenances:
            try:
                provenance.close()
            except BaseException as exc:
                errors.append(exc)
        raise BaseExceptionGroup("initial restore qualification failed", errors)
    return result


__all__ = [
    "ControllerEnvironmentIPC",
    "InitialQualificationAuthority",
    "SyntheticEnvironmentFactory",
    "SyntheticEnvironmentHandle",
    "SyntheticByteTokenizer",
]
