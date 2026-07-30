"""Linux forked sacrificial workers; parent keeps only testd metadata resident."""

from __future__ import annotations

import gc
import multiprocessing
from multiprocessing.connection import Connection

from .manifest import TestManifest
from .protocol import RunRequest, RunResult, receive_message, send_message


def _child(connection: Connection, manifest: TestManifest) -> None:
    try:
        request = receive_message(connection)
        if not isinstance(request, RunRequest):
            raise ValueError("child received a non-request message")
        from .worker import OneShotWorker

        send_message(connection, OneShotWorker(manifest).execute(request))
    finally:
        connection.close()


class LinuxPool:
    """Fork one clean child for each request and fail closed on every anomaly."""

    def __init__(self, manifest: TestManifest, *, timeout_seconds: float = 5.0) -> None:
        if type(timeout_seconds) not in (int, float) or timeout_seconds < 0:
            raise ValueError("timeout_seconds must be nonnegative")
        self._manifest = manifest
        self._timeout_seconds = float(timeout_seconds)
        self._context = multiprocessing.get_context("fork")
        gc.collect()
        gc.freeze()

    def run(self, request: RunRequest) -> RunResult:
        parent, child = self._context.Pipe(duplex=True)
        process = self._context.Process(target=_child, args=(child, self._manifest))
        try:
            process.start()
            child.close()
            send_message(parent, request)
            if not parent.poll(self._timeout_seconds):
                process.terminate()
                process.join(timeout=1)
                raise TimeoutError("sacrificial worker did not respond before deadline")
            result = receive_message(parent)
            process.join(timeout=1)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
                raise RuntimeError("sacrificial worker did not exit")
            if process.exitcode != 0 or not isinstance(result, RunResult):
                raise RuntimeError("sacrificial worker returned an invalid result")
            return result
        finally:
            parent.close()
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
