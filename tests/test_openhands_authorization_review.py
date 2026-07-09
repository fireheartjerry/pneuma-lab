from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = (
    ROOT
    / "docs"
    / "data"
    / "training-readiness"
    / "openhands-sampled-authorization-review.json"
)
REGISTRY_PATH = ROOT / "docs" / "data" / "registry" / "openhands-sampled.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_hash(package: dict) -> str:
    value = copy.deepcopy(package)
    value["package_integrity"]["sha256"] = None
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def test_review_package_is_deterministic_and_hash_bound() -> None:
    package = _load(PACKAGE_PATH)
    assert _load(PACKAGE_PATH) == package
    assert package["package_status"] == "review_only"
    assert package["package_integrity"]["sha256"] == _canonical_hash(package)

    registry = _load(REGISTRY_PATH)
    source = registry["source"]
    assert package["dataset"]["dataset_id"] == registry["dataset_id"]
    assert package["dataset"]["hf_repo"] == source["hf_repo"]
    assert package["dataset"]["hf_revision"] == source["hf_revision"]
    assert package["dataset"]["source_hashes"] == {
        f"{key}": f"sha256:{value}"
        for key, value in registry["expected_from_adapter_report"]["hashes"].items()
    }
    hashes = list(package["dataset"]["source_hashes"].values()) + [
        package["converted_corpus"]["examples_jsonl_sha256"],
        package["split"]["manifest_sha256"],
        package["split"]["report_sha256"],
        package["split"]["hash_manifest_sha256"],
    ]
    for value in hashes:
        assert re.fullmatch(r"sha256:[0-9a-f]{64}", value)


def test_review_package_binds_scope_code_and_contained_output() -> None:
    package = _load(PACKAGE_PATH)
    code_state = package["code_state"]
    assert re.fullmatch(r"[0-9a-f]{40}", code_state["authorized_code_commit"])
    assert code_state["protected_paths"] == ["src/", "schemas/", "pyproject.toml"]
    assert package["split"]["counts"] == {
        "train": 3803,
        "validation": 1208,
        "test": 1044,
        "repo_groups": 11,
        "same_repo_in_multiple_splits": False,
    }
    assert package["controlled_training_scope"]["task_type"] == "RISK_PREDICTION"
    assert package["controlled_training_scope"]["source_examples"] == 6055
    assert package["output_policy"]["allowed_root"].startswith(
        "build/training_runs/openhands-sampled/"
    )
    assert package["output_policy"]["root_must_be_repo_local"] is True
    assert package["output_policy"]["forbidden_roots"] == [
        "C:/pneuma-data",
        "C:\\pneuma-data",
    ]
    assert package["training_constants"] == {
        "algorithm": "full-batch-logistic-regression-l2-v1",
        "learning_rate": 0.3,
        "learning_rate_decay": 0.005,
        "iterations": 800,
        "l2_lambda": 0.001,
        "randomness": "none",
        "class_imbalance_handling": "unweighted_baseline_reproduction_only",
        "model_use": "offline_advisory_only",
        "training_weight": 0.0,
        "required_metrics": [
            "AUROC",
            "AUPRC",
            "Brier score",
            "ECE",
            "per_repo_breakdown",
            "baseline_lift_over_constant_predictor",
        ],
    }


def test_review_package_is_explicitly_not_training_authorized() -> None:
    package = _load(PACKAGE_PATH)
    authorization = package["authorization"]
    assert authorization == {
        "training_authorized": False,
        "decision": "pending_human_review",
        "reviewer": None,
        "reviewed_at": None,
        "approval_record_ref": None,
        "required_human_decision": authorization["required_human_decision"],
    }
    assert package["training_constants"]["training_weight"] == 0.0
    assert package["output_policy"]["runtime_integration"] == "none"
    assert not any(
        ref.startswith("docs/data/training-authorizations/")
        for ref in package["references"]
    )
