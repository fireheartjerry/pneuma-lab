from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/verify_dataset_onboarding.py")
DATASET_ID = "swe-gym-openhands-sampled"


def _report():
    return {
        "adapter": {"name": "openhands-sampled", "version": "0.1.0"},
        "adapter_report_schema_version": "0.1.0",
        "counts": {
            "invalid": 0,
            "skipped": 0,
            "source_rows": 2,
            "traces_emitted": 2,
            "valid": 2,
        },
        "dataset": "swe-gym",
        "hf_repo": "SWE-Gym/OpenHands-Sampled-Trajectories",
        "hf_revision": "rev",
        "invalid_traces_file_sha256": "empty",
        "privacy": {"redaction_totals": [{"count": 1, "kind": "email"}]},
        "task_join_hf_repo": "SWE-Gym/SWE-Gym",
        "trace_index_file_sha256": "index",
        "traces_file_sha256": "traces",
        "trajectory": {
            "resolved_false": 1,
            "resolved_true": 1,
            "total_agent_steps": 3,
            "traces_missing_task_join": 0,
            "traces_with_task_join": 2,
        },
    }


def _manifest():
    return {
        "manifest_schema_version": "0.1.0",
        "dataset_id": DATASET_ID,
        "dataset_status": "onboarded",
        "registry_status": "single_dataset_pilot",
        "human_name": "Synthetic OpenHands sampled",
        "data_root_variable": "PNEUMA_DATA_ROOT",
        "default_observed_data_root": "C:/pneuma-data",
        "raw_path_relative": "raw/swe-gym/OpenHands-Sampled-Trajectories",
        "processed_path_relative": "processed/swe-gym/openhands-sampled",
        "source_of_truth_report_relative": (
            "processed/swe-gym/openhands-sampled/adapter_report.json"
        ),
        "adapter": {
            "name": "openhands-sampled",
            "module": "pneuma_lab.adapters.openhands_sampled",
            "version": "0.1.0",
        },
        "schema": {"artifact": "PneumaTrace", "envelope_version": "0.2.0"},
        "source": {
            "dataset": "swe-gym",
            "hf_repo": "SWE-Gym/OpenHands-Sampled-Trajectories",
            "hf_revision": "rev",
            "task_join_hf_repo": "SWE-Gym/SWE-Gym",
        },
        "expected_from_adapter_report": {
            "adapter_report_schema_version": "0.1.0",
            "counts": {
                "source_rows": 2,
                "traces_emitted": 2,
                "valid": 2,
                "invalid": 0,
                "skipped": 0,
            },
            "trajectory": {
                "traces_with_task_join": 2,
                "traces_missing_task_join": 0,
                "total_agent_steps": 3,
                "resolved_true": 1,
                "resolved_false": 1,
            },
            "privacy": {"redaction_totals": [{"count": 1, "kind": "email"}]},
            "hashes": {
                "traces_file_sha256": "traces",
                "trace_index_file_sha256": "index",
                "invalid_traces_file_sha256": "empty",
            },
        },
        "privacy_status": "redaction-verified processed outputs available",
        "allowed_uses": ["dataset onboarding validation"],
        "blocked_uses": ["ML training in this pass"],
    }


def _write_tree(tmp_path: Path, manifest=None, report=None):
    registry = tmp_path / "registry"
    registry.mkdir()
    data_root = tmp_path / "data"
    raw = data_root / "raw/swe-gym/OpenHands-Sampled-Trajectories"
    processed = data_root / "processed/swe-gym/openhands-sampled"
    raw.mkdir(parents=True)
    processed.mkdir(parents=True)
    for name in (
        "pneuma_traces.jsonl",
        "pneuma_traces.invalid.jsonl",
        "trace_index.jsonl",
    ):
        (processed / name).write_text("", encoding="utf-8")
    (processed / "adapter_report.json").write_text(
        json.dumps(report or _report(), sort_keys=True),
        encoding="utf-8",
    )
    (registry / "openhands-sampled.json").write_text(
        json.dumps(manifest or _manifest(), sort_keys=True),
        encoding="utf-8",
    )
    return data_root, registry


def _run(data_root: Path | None, registry: Path, env=None):
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--dataset",
        DATASET_ID,
        "--registry-root",
        str(registry),
    ]
    if data_root is not None:
        cmd += ["--data-root", str(data_root)]
    return subprocess.run(cmd, text=True, capture_output=True, env=env)


def test_passes_against_synthetic_manifest_and_report(tmp_path):
    data_root, registry = _write_tree(tmp_path)
    result = _run(data_root, registry)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: dataset onboarding manifest matches adapter report" in result.stdout
    assert "valid_traces=2" in result.stdout


def test_fails_on_mismatched_source_rows(tmp_path):
    manifest = _manifest()
    manifest["expected_from_adapter_report"]["counts"]["source_rows"] = 99
    data_root, registry = _write_tree(tmp_path, manifest=manifest)
    result = _run(data_root, registry)
    assert result.returncode == 1
    assert "counts.source_rows" in result.stdout


def test_fails_on_mismatched_valid_trace_count(tmp_path):
    manifest = _manifest()
    manifest["expected_from_adapter_report"]["counts"]["valid"] = 99
    data_root, registry = _write_tree(tmp_path, manifest=manifest)
    result = _run(data_root, registry)
    assert result.returncode == 1
    assert "counts.valid" in result.stdout


def test_fails_on_mismatched_trace_hash(tmp_path):
    manifest = _manifest()
    manifest["expected_from_adapter_report"]["hashes"]["traces_file_sha256"] = "bad"
    data_root, registry = _write_tree(tmp_path, manifest=manifest)
    result = _run(data_root, registry)
    assert result.returncode == 1
    assert "traces_file_sha256" in result.stdout


def test_fails_on_missing_required_manifest_field(tmp_path):
    manifest = _manifest()
    del manifest["privacy_status"]
    data_root, registry = _write_tree(tmp_path, manifest=manifest)
    result = _run(data_root, registry)
    assert result.returncode == 1
    assert "manifest missing required fields" in result.stdout
    assert "privacy_status" in result.stdout


def test_data_root_argument_overrides_environment(tmp_path):
    data_root, registry = _write_tree(tmp_path)
    bad_env_root = tmp_path / "missing"
    env = os.environ.copy()
    env["PNEUMA_DATA_ROOT"] = str(bad_env_root)
    result = _run(data_root, registry, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"data_root={data_root}" in result.stdout


def test_environment_data_root_used_when_argument_absent(tmp_path):
    data_root, registry = _write_tree(tmp_path)
    env = os.environ.copy()
    env["PNEUMA_DATA_ROOT"] = str(data_root)
    result = _run(None, registry, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"data_root={data_root}" in result.stdout
