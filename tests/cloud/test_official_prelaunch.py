from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.official_prelaunch import (
    canonical_bytes,
    seal_prelaunch,
    verify_prelaunch,
)


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    package = tmp_path / "package"
    secrets = tmp_path / "secrets"
    amendment = tmp_path / "amendment.md"
    # The production function intentionally pins the reviewed amendment bytes;
    # tests copy the actual repository amendment rather than weakening that pin.
    source = Path(
        "docs/research/neurips-2026-workshop/67-minimal-prelaunch-protocol-amendment-20260805.md"
    )
    amendment.write_bytes(source.read_bytes())
    tasks = []
    for benchmark in ("SWE", "TAU"):
        for index in range(120):
            tasks.append(
                {"task_id": f"{benchmark.lower()}:{index:03d}", "benchmark": benchmark}
            )
    _write(package / "inputs/task-registry.json", {"tasks": tasks})
    _write(package / "inputs/input-lock.json", {"record_kind": "cloud_input_lock"})
    _write(package / "inputs/analysis-graph.json", {"record_kind": "analysis_graph"})
    _write(
        package / "power/sources/c120-roster.json",
        {"tasks": [{**task, "tiers": [120]} for task in tasks]},
    )
    commitment_values = {}
    secrets.mkdir(parents=True)
    for label in (
        "roster",
        "schedule",
        "assignment",
        "packet",
        "model",
        "benchmark",
        "unblind",
    ):
        raw = hashlib.sha256(label.encode()).digest()
        (secrets / f"{label}-seed.bin").write_bytes(raw)
        commitment_values[label] = hashlib.sha256(
            b"official-study-commitment-v1\0" + label.encode() + b"\0" + raw
        ).hexdigest()
    _write(
        package / "power/sources/deterministic-seed-commitments.json",
        {"commitments": commitment_values},
    )
    power = package / "power/final.json"
    _write(
        power,
        {
            "record_kind": "resampling_power_report",
            "payload": {
                "stage": "final",
                "finalization": {"decision": "GO", "selected_tier": 120},
            },
        },
    )
    return package, secrets, power, amendment


def test_seals_exact_prelaunch_authorities(tmp_path: Path) -> None:
    package, secrets, power, amendment = _fixture(tmp_path)
    result = seal_prelaunch(
        package_root=package,
        secret_root=secrets,
        power_report_path=power,
        protocol_amendment_path=amendment,
        code_commit="a" * 40,
    )
    root = verify_prelaunch(result, package_root=package)
    assert root["selected_tier"] == 120
    plan = json.loads((package / "sealed/task-block-plan.json").read_text())
    assert plan["task_count"] == 240
    assert plan["worker_counts"] == {"worker-0": 180, "worker-1": 60}
    assignment = json.loads(
        (package / "sealed/assignment.controller-only.json").read_text()
    )
    assert len(assignment["rows"]) == 240
    assert {slot["arm"] for row in assignment["rows"] for slot in row["slots"]} == {
        "REAL",
        "SHAM",
        "NONE",
        "RESAMPLE",
    }
    openings = json.loads(
        (package / "sealed/execution-seeds.controller-only.json").read_text()
    )
    assert len(openings["rows"]) == 240
    assert all(len(row["slots"]) == 4 for row in openings["rows"])
    assert {
        row["worker_id"]
        for row in openings["rows"]
        if row["task_id"].startswith("tau:")
    } == {"worker-0"}


def test_rejects_nonopening_seed(tmp_path: Path) -> None:
    package, secrets, power, amendment = _fixture(tmp_path)
    (secrets / "packet-seed.bin").write_bytes(b"x" * 32)
    with pytest.raises(CloudManifestError, match="packet seed"):
        seal_prelaunch(
            package_root=package,
            secret_root=secrets,
            power_report_path=power,
            protocol_amendment_path=amendment,
            code_commit="a" * 40,
        )


def test_rejects_tampered_bound_artifact(tmp_path: Path) -> None:
    package, secrets, power, amendment = _fixture(tmp_path)
    result = seal_prelaunch(
        package_root=package,
        secret_root=secrets,
        power_report_path=power,
        protocol_amendment_path=amendment,
        code_commit="a" * 40,
    )
    (package / "sealed/task-block-plan.json").write_bytes(b"{}\n")
    with pytest.raises(CloudManifestError, match="bytes differ"):
        verify_prelaunch(result, package_root=package)
