"""Isolated deterministic worker for the sealed synthetic environment fixture."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _encoded(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decoded(value: object) -> bytes:
    if type(value) is not str:
        raise ValueError("encoded bytes must be exact text")
    return base64.b64decode(value, validate=True)


def _snapshot(state: dict[str, object]) -> bytes:
    return _canonical(state) + b"\n"


def _main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--request-fd", type=int, required=True)
    parser.add_argument("--response-fd", type=int, required=True)
    parser.add_argument("--task-sha256", required=True)
    parser.add_argument("--program-sha256", required=True)
    arguments = parser.parse_args()
    request = os.fdopen(arguments.request_fd, "rb", buffering=0)
    response = os.fdopen(arguments.response_fd, "wb", buffering=0)
    state: dict[str, object] | None = None

    def reply(value: object) -> None:
        response.write(_canonical({"ok": True, "value": value}) + b"\n")

    while line := request.readline():
        try:
            message = json.loads(line)
            operation = message["operation"]
            if operation == "start":
                task_bytes = _decoded(message["task_input_bytes"])
                program_bytes = _decoded(message["program_bytes"])
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
                    "visible_context": _encoded(task_bytes),
                }
                reply(None)
            elif state is None:
                raise ValueError("environment has not started")
            elif operation == "snapshot":
                reply(_encoded(_snapshot(state)))
            elif operation == "restore":
                candidate = _decoded(message["snapshot_bytes"])
                decoded = json.loads(candidate)
                if (
                    type(decoded) is not dict
                    or _canonical(decoded) + b"\n" != candidate
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
            response.write(
                _canonical(
                    {
                        "error": f"{type(exc).__name__}: {exc}",
                        "ok": False,
                    }
                )
                + b"\n"
            )
    request.close()
    response.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
