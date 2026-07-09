from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = (
    ROOT
    / "docs"
    / "data"
    / "training-readiness"
    / "openhands-sampled-baseline-training-plan.json"
)


def test_openhands_baseline_training_plan_manifest_loads() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["dataset_id"] == "swe-gym-openhands-sampled"
    assert manifest["task_type"] == "RISK_PREDICTION"
    assert manifest["target_field"] == "target.resolved"
    assert manifest["training_authorization"] == "not_authorized"
    assert manifest["current_training_weight"] == 0.0
    assert manifest["split_manifest_status"] == "generated_reviewed"
    assert manifest["future_artifact_root"].startswith("build/training_runs/")
    assert "C:/pneuma-data" not in manifest["future_artifact_root"]
    assert "C:\\pneuma-data" not in manifest["future_artifact_root"]


def test_openhands_baseline_training_plan_declares_metrics_and_blocks_leakage() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for metric in ["AUROC", "AUPRC", "Brier score", "ECE"]:
        assert metric in manifest["required_metrics"]
    assert "per_repo_breakdown" in manifest["required_metrics"]
    assert "baseline_lift_over_constant_predictor" in manifest["required_metrics"]

    for blocked_key in ["target", "resolved", "outcome", "labels", "gold", "oracle", "patch"]:
        assert blocked_key in manifest["blocked_feature_keys"]
    assert "constant_base_rate" in manifest["baseline_ladder"]
    assert "logistic_regression_approved_structured_features" in manifest["baseline_ladder"]
    assert "no_sft_dpo_lora" in manifest["baseline_ladder"]
    assert "leakage_checker_implemented" in manifest["approval_gates"]
    assert "test_split_used_for_tuning" in manifest["invalidation_conditions"]


def test_openhands_baseline_training_plan_references_committed_docs_only_for_docs() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    doc_refs = [ref for ref in manifest["evidence_refs"] if ref.startswith(("docs/", "schemas/"))]

    assert doc_refs
    for ref in doc_refs:
        assert (ROOT / ref).is_file()

    build_refs = [ref for ref in manifest["evidence_refs"] if ref.startswith("build/")]
    assert build_refs
    for ref in build_refs:
        assert ref.startswith("build/training_examples/openhands-sampled/")
