from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "data" / "training-readiness" / "openhands-sampled.json"


def test_openhands_training_readiness_manifest_loads_and_points_to_docs() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["dataset_id"] == "swe-gym-openhands-sampled"
    assert manifest["dataset_family"] == "swe-gym"
    assert manifest["counts"] == {
        "examples": 6055,
        "invalid_examples": 0,
        "quarantined_examples": 0,
        "agent_steps": 114461,
    }
    assert manifest["class_balance"]["resolved"] == 491
    assert manifest["class_balance"]["unresolved"] == 5564
    assert manifest["current_model_use_tier"] == "train_after_adapter"
    assert manifest["current_training_weight"] == 0.0
    assert manifest["training_authorization"] == "not_authorized"
    assert manifest["split_manifest_status"] == "generated_reviewed"
    assert manifest["recommended_split_policy"]["primary"] == "repo_grouped"
    assert manifest["recommended_split_policy"]["same_repo_in_multiple_splits"] is False
    assert manifest["recommended_split_policy"]["split_counts"]["train"]["examples"] == 3803
    assert manifest["recommended_split_policy"]["split_counts"]["validation"]["examples"] == 1208
    assert manifest["recommended_split_policy"]["split_counts"]["test"]["examples"] == 1044
    assert manifest["approved_task_types"] == ["RISK_PREDICTION"]
    assert "OPERATOR_PUSHBACK" in manifest["blocked_task_types"]
    assert "SELF_REPORT_FAITHFULNESS" in manifest["blocked_task_types"]
    assert "WORKSPACE_SALIENCE_LATER" in manifest["blocked_task_types"]

    for ref in manifest["generated_artifact_refs"].values():
        assert ref.startswith("build/training_examples/openhands-sampled/")
        assert "C:/pneuma-data" not in ref
        assert "C:\\pneuma-data" not in ref

    committed_doc_refs = [
        ref for ref in manifest["evidence_refs"] if ref.startswith("docs/")
    ]
    assert committed_doc_refs
    for ref in committed_doc_refs:
        assert (ROOT / ref).is_file()

    assert "full_conversion_artifacts_reproducible" in manifest[
        "required_gates_before_training"
    ]
    assert "no_runtime_integration" in manifest["required_gates_before_training"]
    assert "benchmark_contamination" in manifest["leakage_risks"]
