from __future__ import annotations

import pytest

from pneuma_lab.testd.manifest import TestManifest
from pneuma_lab.testd.protocol import RunRequest
from pneuma_lab.testd.worker import OneShotWorker


def test_worker_rejects_nodes_outside_its_manifest() -> None:
    worker = OneShotWorker(
        TestManifest(
            (
                "tests/smoke/test_micro_gate.py::test_project_status_manifest_is_coherent",
            ),
            (),
            (),
        )
    )

    with pytest.raises(ValueError, match="manifest"):
        worker.build_args(
            RunRequest("run", ("tests/smoke/test_micro_gate.py::test_missing",), ())
        )


def test_worker_executes_once_and_reports_bounded_result() -> None:
    node = "tests/smoke/test_micro_gate.py::test_project_status_manifest_is_coherent"
    worker = OneShotWorker(TestManifest((node,), (), ()))

    result = worker.execute(RunRequest("run", (node,), ()))

    assert result.exit_code == 0
    assert result.node_ids == (node,)
    assert result.worker_pid > 0
    with pytest.raises(RuntimeError, match="consumed"):
        worker.execute(RunRequest("run", (node,), ()))
