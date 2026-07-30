"""Single-use in-process worker primitive for a sacrificial child process."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from io import StringIO
import os

from .manifest import TestManifest
from .protocol import RunRequest, RunResult


_MAX_OUTPUT_CHARS = 16 * 1024


@dataclass(slots=True)
class OneShotWorker:
    """Validate one manifest-bound request, execute it once, then become unusable."""

    manifest: TestManifest
    _consumed: bool = field(default=False, init=False)

    def build_args(self, request: RunRequest) -> list[str]:
        if request.command not in {"run", "smoke"}:
            raise ValueError("worker accepts only run or smoke requests")
        selected = (
            self.manifest.micro_nodes
            if request.command == "smoke"
            else request.node_ids
        )
        if not selected or not set(selected) <= set(self.manifest.micro_nodes):
            raise ValueError("request node ids are outside the worker manifest")
        return ["-q", "-p", "no:cacheprovider", "--import-mode=importlib", *selected]

    def execute(self, request: RunRequest) -> RunResult:
        if self._consumed:
            raise RuntimeError("worker has already been consumed")
        self._consumed = True
        args = self.build_args(request)
        selected = tuple(
            request.node_ids if request.command == "run" else self.manifest.micro_nodes
        )
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        stdout = StringIO()
        stderr = StringIO()
        import pytest

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = int(pytest.main(args))
        return RunResult(
            exit_code=exit_code,
            node_ids=selected,
            worker_pid=os.getpid(),
            application_fingerprint="worker-unmeasured",
            dependency_fingerprint="worker-unmeasured",
            widening_reason="worker_exact_request",
        )
