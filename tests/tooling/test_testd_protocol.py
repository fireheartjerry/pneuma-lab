from __future__ import annotations

import json

import pytest

from pneuma_lab.testd.protocol import (
    MAX_MESSAGE_BYTES,
    RunRequest,
    RunResult,
    decode_message,
    encode_message,
    receive_message,
    send_message,
)


def test_protocol_round_trip_is_canonical_and_byte_only() -> None:
    request = RunRequest(
        "run",
        ("tests/smoke/test_micro_gate.py::test_project_status_manifest_is_coherent",),
        ("src/pneuma_lab/status.py",),
    )

    payload = encode_message(request)

    assert (
        payload
        == json.dumps(request.to_wire(), sort_keys=True, separators=(",", ":")).encode()
    )
    assert decode_message(payload) == request


def test_protocol_rejects_open_or_noncanonical_requests() -> None:
    with pytest.raises(ValueError, match="unknown command"):
        RunRequest("eval", (), ())
    with pytest.raises(ValueError, match="duplicate"):
        decode_message(b'{"kind":"request","kind":"request"}')
    with pytest.raises(ValueError, match="unknown fields"):
        decode_message(
            b'{"command":"run","kind":"request","paths":[],"protocol_version":1,"node_ids":[],"extra":true}'
        )


def test_protocol_rejects_oversize_and_uses_byte_connection_methods() -> None:
    class Connection:
        def __init__(self) -> None:
            self.payload = b""

        def send_bytes(self, payload: bytes) -> None:
            self.payload = payload

        def recv_bytes(self, maxlength: int) -> bytes:
            assert maxlength == MAX_MESSAGE_BYTES
            return self.payload

        def send(self, _value: object) -> None:
            raise AssertionError("pickle send must not be used")

        def recv(self) -> object:
            raise AssertionError("pickle recv must not be used")

    connection = Connection()
    result = RunResult(
        0,
        ("tests/smoke/test_micro_gate.py::test_project_status_manifest_is_coherent",),
        7,
        "source",
        "dependency",
        "full",
    )
    send_message(connection, result)

    assert receive_message(connection) == result
    with pytest.raises(ValueError, match="maximum"):
        decode_message(b"x" * (MAX_MESSAGE_BYTES + 1))
