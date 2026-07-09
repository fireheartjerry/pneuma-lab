from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pneuma_lab.training import governance


ROOT = Path(__file__).resolve().parents[1]
INFRA_MANIFEST = (
    ROOT
    / "docs"
    / "data"
    / "training-readiness"
    / "openhands-sampled-dataset1-infrastructure.json"
)


def test_dataset1_allowlist_accepts_observable_features() -> None:
    feature_paths = [
        "input.observable_summary.tool_call_count",
        "input.observable_summary.tool_counts.Bash",
        "input.observable_summary.retry_count_max",
        "input.observable_summary.error_density",
        "input.trajectory.num_agent_steps",
        "input.objective.present",
        "input.feature_refs.0",
    ]

    assert governance.check_feature_allowlist(feature_paths) == []


def test_dataset1_allowlist_blocks_targets_oracles_and_raw_fields() -> None:
    feature_paths = [
        "target.resolved",
        "outcome.report.resolved",
        "oracle.fail_to_pass",
        "reference_supervision.gold_patch_sha256",
        "input.objective.text",
        "input.patch",
    ]

    findings = governance.check_feature_allowlist(feature_paths)
    assert {item["path"] for item in findings} == {
        "target.resolved",
        "outcome.report.resolved",
        "oracle.fail_to_pass",
        "reference_supervision.gold_patch_sha256",
        "input.objective.text",
        "input.patch",
    }
    assert {item["code"] for item in findings} == {"blocked_field"}


def test_source_metadata_requires_explicit_manifest_approval() -> None:
    feature_paths = ["input.repo", "input.task_id", "input.objective.text_sha256"]

    findings = governance.check_feature_allowlist(feature_paths)
    assert {item["code"] for item in findings} == {
        "source_metadata_requires_approval"
    }
    assert (
        governance.check_feature_allowlist(
            feature_paths,
            allow_source_metadata=True,
        )
        == []
    )


def test_example_input_leakage_scan_reports_exact_nested_paths() -> None:
    example = {
        "input": {
            "trace_id": "ptrace:synthetic",
            "repo": "synthetic/repo",
            "observable_summary": {"tool_call_count": 3},
            "outcome": {"resolved": True},
            "objective": {"text": "raw task prose"},
        }
    }

    findings = governance.check_example_input_leakage(example)

    assert {item["path"] for item in findings} == {
        "input.objective.text",
        "input.outcome.resolved",
    }
    assert all(item["code"] == "blocked_field" for item in findings)


def test_assert_feature_allowlist_raises_compact_error() -> None:
    with pytest.raises(ValueError, match="target.resolved:blocked_field"):
        governance.assert_feature_allowlist(["target.resolved"])


def test_pre_run_manifest_template_is_valid_but_not_fit_ready() -> None:
    manifest = governance.build_pre_run_manifest_template()

    assert governance.validate_pre_run_manifest(manifest) == []
    materialized_findings = governance.validate_pre_run_manifest(
        manifest,
        require_materialized_hashes=True,
    )
    assert {item["path"] for item in materialized_findings} == {
        "input_examples_sha256",
        "split_manifest_sha256",
    }
    assert {item["code"] for item in materialized_findings} == {
        "missing_materialized_hash"
    }


def test_pre_run_manifest_rejects_runtime_training_and_off_repo_paths() -> None:
    manifest = governance.build_pre_run_manifest_template()
    manifest["training_authorization"] = "authorized"
    manifest["training_weight"] = 1.0
    manifest["runtime_integration"] = "nightclaw"
    manifest["artifact_root"] = "C:/pneuma-data/training-runs/openhands-sampled/"
    manifest["approved_feature_paths"] = ["target.resolved"]

    findings = governance.validate_pre_run_manifest(manifest)

    assert "training_authorization_not_allowed" in {
        item["code"] for item in findings
    }
    assert "training_weight_must_remain_zero" in {item["code"] for item in findings}
    assert "runtime_integration_not_allowed" in {item["code"] for item in findings}
    assert "off_repo_artifact_root" in {item["code"] for item in findings}
    assert "blocked_field" in {item["code"] for item in findings}


def test_pre_run_manifest_accepts_materialized_hashes() -> None:
    manifest = governance.build_pre_run_manifest_template()
    digest = "a" * 64
    manifest["input_examples_sha256"] = f"sha256:{digest}"
    manifest["split_manifest_sha256"] = digest

    assert (
        governance.validate_pre_run_manifest(
            manifest,
            require_materialized_hashes=True,
        )
        == []
    )


def test_infrastructure_manifest_matches_governance_module() -> None:
    manifest = json.loads(INFRA_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["dataset_id"] == governance.DATASET_1_ID
    assert manifest["task_type"] == governance.DATASET_1_TASK_TYPE
    assert manifest["training_authorization"] == "not_authorized"
    assert manifest["governance_module"] == "pneuma_lab.training.governance"
    assert manifest["feature_allowlist"]["version"] == (
        governance.FEATURE_ALLOWLIST_SCHEMA_VERSION
    )
    assert manifest["feature_allowlist"]["default_allowed_feature_paths"] == list(
        governance.DEFAULT_ALLOWED_FEATURE_PATHS
    )
    assert manifest["feature_allowlist"][
        "source_metadata_feature_paths_requiring_manifest_approval"
    ] == list(governance.SOURCE_METADATA_FEATURE_PATHS)
    assert manifest["run_manifest_convention"]["template"] == (
        governance.build_pre_run_manifest_template()
    )
    assert governance.validate_pre_run_manifest(
        manifest["run_manifest_convention"]["template"]
    ) == []


def test_infrastructure_manifest_template_is_independent_copy() -> None:
    template = governance.build_pre_run_manifest_template()
    mutated = copy.deepcopy(template)
    mutated["approved_feature_paths"].append("target.resolved")

    assert governance.validate_pre_run_manifest(template) == []
    assert any(
        item["code"] == "blocked_field"
        for item in governance.validate_pre_run_manifest(mutated)
    )
