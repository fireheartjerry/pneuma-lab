"""Capability boundary tests for the blinded projection candidate."""

from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

import pytest

from pneuma_lab.resampling_null.errors import RecordValidationError


pytestmark = pytest.mark.milestone


def test_candidate_module_is_capability_minimal_in_a_clean_subprocess() -> None:
    program = """
import ast
import inspect
import pneuma_lab.resampling_null.projection_candidate as candidate
source = inspect.getsource(candidate)
tree = ast.parse(source)
names = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
names |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
for forbidden in ('pathlib', 'artifacts', 'assignment', 'secrets', 'packets'):
    assert not any(forbidden in name for name in names), names
assert 'BranchOutcome' not in source
assert 'Arm' not in source
"""
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr


def test_candidate_protocol_runs_in_clean_subprocess_without_a_run_root(tmp_path) -> None:
    """The projector accepts only closed stdin data and emits only candidate bytes."""
    module = Path(__file__).parents[2] / "src/pneuma_lab/resampling_null/projection_candidate.py"
    outcomes = [{"success": 0, "prefix_success": 0, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}] * 4
    request = {"frozen_schedule": [{"task_id": "t", "prefix_success": 0, "slot_ids": ["0", "1", "2", "3"]}], "closed_outcomes": {"t": outcomes}}
    result = subprocess.run(
        [sys.executable, "-I", str(module)],
        cwd=tmp_path,
        env={}, input=json.dumps(request).encode("utf-8"), capture_output=True, text=False,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert b"artifact_ref" not in result.stdout
    assert json.loads(result.stdout) == json.loads(
        __import__("pneuma_lab.resampling_null.projection_candidate", fromlist=["build_candidate"]).build_candidate(
            request["frozen_schedule"], request["closed_outcomes"]
        ).canonical_bytes
    )


def test_candidate_sorts_schedule_and_strips_outcomes() -> None:
    from pneuma_lab.resampling_null.projection_candidate import build_candidate

    candidate = build_candidate(
        [
            {"task_id": "z", "prefix_success": 1, "slot_ids": ["z0", "z1", "z2", "z3"]},
            {"task_id": "a", "prefix_success": 0, "slot_ids": ["a0", "a1", "a2", "a3"]},
        ],
        {
            "a": [{"success": 0, "prefix_success": 0, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}] * 4,
            "z": [{"success": 1, "prefix_success": 1, "partial_reward": 1.0, "infrastructure_failure": False, "counters": {"generated_tokens": 1, "model_calls": 1, "tool_calls": 0, "wall_clock_ms": 1}}] * 4,
        },
    )

    assert [row["task_id"] for row in candidate.rows] == ["z", "a"]
    assert [slot["label"] for slot in candidate.rows[0]["slots"]] == ["A", "B", "C", "D"]
    assert "artifact_ref" not in repr(candidate.rows)


def test_candidate_rejects_prefix_mismatch_and_incomplete_coverage() -> None:
    from pneuma_lab.resampling_null.projection_candidate import build_candidate

    row = {"task_id": "a", "prefix_success": 0, "slot_ids": ["0", "1", "2", "3"]}
    outcome = {"success": 1, "prefix_success": 1, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}
    with pytest.raises(ValueError, match="coverage"):
        build_candidate([row], {})
    with pytest.raises(ValueError, match="prefix"):
        build_candidate([row], {"a": [outcome] * 4})


def test_trusted_sealer_is_not_exposed_by_the_candidate_module() -> None:
    import pneuma_lab.resampling_null.projection_candidate as candidate
    from pneuma_lab.resampling_null.blinding import seal_blinded_projection

    assert not hasattr(candidate, "seal_blinded_projection")
    assert callable(seal_blinded_projection)


def test_trusted_sealer_rejects_a_byte_different_caller_candidate(monkeypatch, tmp_path) -> None:
    """A digest match is insufficient: the supplied sealed bytes are checked."""
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.projection_candidate import ProjectionCandidate, build_candidate

    schedule = {
        "payload": {"tasks": [{"task": {"task_id": "t", "lineage": []}, "slots": [{"slot_id": str(i)} for i in range(4)]}]},
        "study_id": "s", "frozen_created_at": "2026-01-01T00:00:00Z", "provenance": {"code_sha256": "0" * 64, "design_sha256": "1" * 64},
    }
    block = {"payload": {"task_id": "t", "prefix_success": 0, "slot_outcomes": [{"success": 0, "prefix_success": 0, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}] * 4, "benchmark": "b", "stratum": "x", "sensitivity_groups": [], "triggered": False, "pipeline_valid": True, "validity_codes": []}}
    freeze = {"study_id": "s"}
    documents = iter([schedule, freeze, block])
    monkeypatch.setattr(blinding, "_load_direct_scientific_parent", lambda *args, **kwargs: type("D", (), {"value": next(documents)})())
    monkeypatch.setattr(blinding, "verify_frozen_analysis_inputs", lambda *args, **kwargs: None)
    monkeypatch.setattr(blinding, "write_record", lambda *args, **kwargs: pytest.fail("must not publish"))
    valid = build_candidate(
        [{"task_id": "t", "prefix_success": 0, "slot_ids": [str(i) for i in range(4)]}],
        {"t": block["payload"]["slot_outcomes"]},
    )
    mismatched = ProjectionCandidate(valid.rows, b"[]", valid.sha256)
    ref = __import__("pneuma_lab.resampling_null.types", fromlist=["ArtifactRef"]).ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    with pytest.raises(Exception, match="caller candidate bytes"):
        blinding._seal_blinded_projection_locked(run_root=tmp_path, destination=tmp_path / "out.json", schedule_ref=ref, analysis_freeze_ref=ref, task_block_refs=(ref,), candidate=mismatched)


def test_unblind_checks_graph_and_current_inputs_before_ledger_loader(monkeypatch, tmp_path) -> None:
    """The clear-ledger loader is structurally last in the pre-exposure path."""
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.freeze import CurrentAnalysisInputs
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "run"
    root.mkdir()
    ref = ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    inputs = CurrentAnalysisInputs({}, tmp_path / "config", tmp_path / "schema", ref)
    observed: list[str] = []
    monkeypatch.setattr(blinding, "validate_preunblind_graph", lambda *a: observed.append("pregraph"))
    monkeypatch.setattr(blinding, "verify_current_analysis_inputs", lambda *a, **k: observed.append("current"))
    monkeypatch.setattr(blinding, "_validated_permit", lambda *a, **k: observed.append("permit") or ("permit", {"rows": []}, {}))
    monkeypatch.setattr(blinding, "validate_scientific_graph", lambda *a: observed.append("graph"))
    monkeypatch.setattr(blinding, "_validate_ledger_ancestry", lambda *a, **k: observed.append("ledger") or {"payload": {"assignments": []}, "study_id": "s", "frozen_created_at": "2026-01-01T00:00:00Z", "provenance": {}})
    monkeypatch.setattr(blinding, "write_record", lambda *a, **k: ref)
    result = blinding.unblind_projection(
        object(), permit_hmac_sha256="permit", run_root=root,
        receipt_destination=root / "receipt.json", manifest_ref=ref,
        schedule_ref=ref, prefix_index_ref=ref, ledger_ref=ref,
        projection_ref=ref, freeze_ref=ref, expected_task_count=0,
        current_analysis_inputs=inputs,
    )
    assert result.receipt_ref == ref
    assert observed == ["pregraph", "current", "permit", "graph", "ledger"]


def test_valid_permit_taints_before_full_graph_failure(monkeypatch, tmp_path) -> None:
    """A graph parser interruption cannot leave a potentially exposed run clean."""
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.freeze import CurrentAnalysisInputs
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "run"
    root.mkdir()
    ref = ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    inputs = CurrentAnalysisInputs({}, tmp_path / "config", tmp_path / "schema", ref)
    monkeypatch.setattr(blinding, "validate_preunblind_graph", lambda *a: None)
    monkeypatch.setattr(blinding, "verify_current_analysis_inputs", lambda *a, **k: None)
    monkeypatch.setattr(blinding, "_validated_permit", lambda *a, **k: ("permit", {"rows": []}, {}))
    monkeypatch.setattr(blinding, "validate_scientific_graph", lambda *a: (_ for _ in ()).throw(RecordValidationError("graph failure")))
    with pytest.raises(RecordValidationError, match="graph failure"):
        blinding.unblind_projection(
            object(), permit_hmac_sha256="permit", run_root=root,
            receipt_destination=root / "receipt.json", manifest_ref=ref,
            schedule_ref=ref, prefix_index_ref=ref, ledger_ref=ref,
            projection_ref=ref, freeze_ref=ref, expected_task_count=0,
            current_analysis_inputs=inputs,
        )
    assert (root / "operational/task6/outcome-tainted.json").is_file()
