from __future__ import annotations

import os

import pytest

from pneuma_lab.testd.linux_pool import LinuxPool
from pneuma_lab.testd.manifest import TestManifest
from pneuma_lab.testd.protocol import RunRequest


pytestmark = pytest.mark.milestone


def test_linux_pool_consumes_a_distinct_child_for_each_request() -> None:
    node = "tests/smoke/test_micro_gate.py::test_project_status_manifest_is_coherent"
    pool = LinuxPool(TestManifest((node,), (), ()))

    first = pool.run(RunRequest("run", (node,), ()))
    second = pool.run(RunRequest("run", (node,), ()))

    assert first.exit_code == second.exit_code == 0
    assert first.worker_pid != second.worker_pid != os.getpid()


def test_linux_pool_fails_closed_for_child_timeout() -> None:
    node = "tests/smoke/test_micro_gate.py::test_project_status_manifest_is_coherent"
    pool = LinuxPool(TestManifest((node,), (), ()), timeout_seconds=0.0)

    with pytest.raises(TimeoutError):
        pool.run(RunRequest("run", (node,), ()))
