"""Bounded canonical JSON protocol for the test supervisor."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Protocol, TypeAlias


PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 256 * 1024
_COMMANDS = frozenset({"run", "smoke", "status", "stop"})
_NODE_ID = re.compile(r"^tests/[A-Za-z0-9_./-]+\.py::test_[A-Za-z0-9_]+$")


class _ByteConnection(Protocol):
    def send_bytes(self, payload: bytes) -> None: ...

    def recv_bytes(self, maxlength: int) -> bytes: ...


def _text_tuple(
    value: object, *, field: str, node_ids: bool = False
) -> tuple[str, ...]:
    if type(value) is not list or any(
        type(item) is not str or not item for item in value
    ):
        raise ValueError(f"{field} must be an array of non-empty text")
    result = tuple(value)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} contains duplicates")
    if node_ids and any(_NODE_ID.fullmatch(item) is None for item in result):
        raise ValueError("node_ids are not manifest-shaped")
    return result


@dataclass(frozen=True, slots=True)
class RunRequest:
    command: str
    node_ids: tuple[str, ...]
    paths: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.command not in _COMMANDS:
            raise ValueError("unknown command")
        _text_tuple(list(self.node_ids), field="node_ids", node_ids=True)
        _text_tuple(list(self.paths), field="paths")

    def to_wire(self) -> dict[str, object]:
        return {
            "command": self.command,
            "kind": "request",
            "node_ids": list(self.node_ids),
            "paths": list(self.paths),
            "protocol_version": PROTOCOL_VERSION,
        }


@dataclass(frozen=True, slots=True)
class RunResult:
    exit_code: int
    node_ids: tuple[str, ...]
    worker_pid: int | None
    application_fingerprint: str
    dependency_fingerprint: str
    widening_reason: str

    def __post_init__(self) -> None:
        if type(self.exit_code) is not int or self.exit_code < 0:
            raise ValueError("exit_code must be a nonnegative exact integer")
        _text_tuple(list(self.node_ids), field="node_ids", node_ids=True)
        if self.worker_pid is not None and (
            type(self.worker_pid) is not int or self.worker_pid <= 0
        ):
            raise ValueError("worker_pid must be a positive exact integer or null")
        for field in (
            "application_fingerprint",
            "dependency_fingerprint",
            "widening_reason",
        ):
            if type(getattr(self, field)) is not str or not getattr(self, field):
                raise ValueError(f"{field} must be non-empty text")

    def to_wire(self) -> dict[str, object]:
        return {
            "application_fingerprint": self.application_fingerprint,
            "dependency_fingerprint": self.dependency_fingerprint,
            "exit_code": self.exit_code,
            "kind": "result",
            "node_ids": list(self.node_ids),
            "protocol_version": PROTOCOL_VERSION,
            "widening_reason": self.widening_reason,
            "worker_pid": self.worker_pid,
        }


WireMessage: TypeAlias = RunRequest | RunResult


def encode_message(message: WireMessage) -> bytes:
    if not isinstance(message, (RunRequest, RunResult)):
        raise TypeError("message must be a wire record")
    payload = json.dumps(
        message.to_wire(), allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ValueError("message exceeds maximum size")
    return payload


def decode_message(payload: bytes) -> WireMessage:
    if type(payload) is not bytes:
        raise TypeError("payload must be exact bytes")
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ValueError("message exceeds maximum size")

    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("nonfinite JSON")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid canonical JSON") from exc
    if type(value) is not dict:
        raise ValueError("message must be one object")
    if value.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("wrong protocol version")
    kind = value.get("kind")
    if kind == "request":
        expected = {"command", "kind", "node_ids", "paths", "protocol_version"}
        if set(value) != expected:
            raise ValueError("unknown fields")
        return RunRequest(
            str(value["command"]),
            _text_tuple(value["node_ids"], field="node_ids", node_ids=True),
            _text_tuple(value["paths"], field="paths"),
        )
    if kind == "result":
        expected = {
            "application_fingerprint",
            "dependency_fingerprint",
            "exit_code",
            "kind",
            "node_ids",
            "protocol_version",
            "widening_reason",
            "worker_pid",
        }
        if set(value) != expected:
            raise ValueError("unknown fields")
        return RunResult(
            value["exit_code"],
            _text_tuple(value["node_ids"], field="node_ids", node_ids=True),
            value["worker_pid"],
            value["application_fingerprint"],
            value["dependency_fingerprint"],
            value["widening_reason"],
        )
    raise ValueError("unknown message kind")


def send_message(connection: _ByteConnection, message: WireMessage) -> None:
    connection.send_bytes(encode_message(message))


def receive_message(connection: _ByteConnection) -> WireMessage:
    return decode_message(connection.recv_bytes(MAX_MESSAGE_BYTES))
