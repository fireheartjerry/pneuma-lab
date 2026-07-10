from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.training import dialogue_governance as gov


ROOT = Path(__file__).resolve().parents[1]
READINESS = (
    ROOT
    / "docs"
    / "data"
    / "archive"
    / "dialogue-swe-bench"
    / "training-readiness.json"
)


def test_license_gate_blocks_current_local_provenance() -> None:
    gate = gov.license_gate_status(
        local_license=None,
        normalized_metadata_license="paper=CC BY 4.0; hf_dataset=not declared; github=none",
        hf_license_declared=False,
        github_license_declared=False,
    )

    assert gate["status"] == gov.LICENSE_STATUS_BLOCKED
    assert gate["real_row_conversion_allowed"] is False
    assert gate["bounded_real_conversion_allowed"] is False
    assert gate["training_authorization"] == "not_authorized"
    assert any("local provenance license is null" in note for note in gate["notes"])


def test_license_gate_requires_all_sources_to_resolve() -> None:
    blocked = gov.license_gate_status(
        local_license="MIT",
        hf_license_declared=True,
        github_license_declared=False,
    )
    allowed = gov.license_gate_status(
        local_license="MIT",
        hf_license_declared=True,
        github_license_declared=True,
    )

    assert blocked["status"] == gov.LICENSE_STATUS_BLOCKED
    assert allowed["status"] == gov.LICENSE_STATUS_ALLOWED
    assert allowed["bounded_real_conversion_allowed"] is True


def test_dialogue_allowlist_blocks_raw_text_oracle_and_target_fields() -> None:
    paths = [
        "input.dataset.source_row",
        "input.dialogue_summary.turn_count",
        "input.problem_statement",
        "input.patch",
        "input.FAIL_TO_PASS",
        "input.task.difficulty",
    ]

    findings = gov.check_input_allowlist(paths, task_type="TASK_DIFFICULTY")

    assert {item["path"] for item in findings} == {
        "input.problem_statement",
        "input.patch",
        "input.fail_to_pass",
        "input.task.difficulty",
    }
    assert {item["code"] for item in findings} == {"blocked_field"}


def test_operator_pushback_blocks_simulated_correction_count_as_input() -> None:
    findings = gov.check_input_allowlist(
        [
            "input.dialogue_summary.turn_count",
            "input.dialogue_summary.simulated_correction_count",
        ],
        task_type="OPERATOR_PUSHBACK",
    )

    assert findings == [
        {
            "path": "input.dialogue_summary.simulated_correction_count",
            "code": "blocked_field",
            "message": "input path touches raw, oracle, target, or task-label material",
            "blocked_tokens": ["simulated_correction_count"],
        }
    ]


def test_example_leakage_scan_reports_blocked_fields_only() -> None:
    example = {
        "task_type": "TASK_DIFFICULTY",
        "input": {
            "dataset": {"dataset_id": "dialogue-swe-bench"},
            "task": {"difficulty": "medium"},
            "problem_statement": "raw issue text",
        },
    }

    findings = gov.check_example_input_leakage(example)

    assert {item["path"] for item in findings} == {
        "input.problem_statement",
        "input.task.difficulty",
    }


def test_bounded_conversion_request_is_blocked_by_license_gate() -> None:
    gate = gov.license_gate_status(
        local_license=None,
        hf_license_declared=False,
        github_license_declared=False,
    )

    findings = gov.validate_bounded_conversion_request(
        limit=5,
        output_root="build/training_examples/dialogue-swe-bench/bounded/run/",
        license_gate=gate,
    )

    assert findings == [
        {
            "path": "license_gate",
            "code": "license_gate_blocked",
            "message": "bounded real-row conversion is blocked until license review resolves",
        }
    ]


def test_bounded_conversion_request_rejects_off_repo_or_oversized_outputs() -> None:
    gate = gov.license_gate_status(
        local_license="MIT",
        hf_license_declared=True,
        github_license_declared=True,
    )

    findings = gov.validate_bounded_conversion_request(
        limit=11,
        output_root="C:/pneuma-data/processed/dialogue-swe-bench/bounded/",
        license_gate=gate,
    )

    assert "invalid_bounded_limit" in {item["code"] for item in findings}
    assert "off_repo_output_forbidden" in {item["code"] for item in findings}
    assert "unapproved_output_root" in {item["code"] for item in findings}


def test_readiness_manifest_matches_governance_template() -> None:
    manifest = json.loads(READINESS.read_text(encoding="utf-8"))
    template = gov.build_readiness_manifest_template()

    for key in [
        "manifest_schema_version",
        "dataset_id",
        "status",
        "training_authorization",
        "bounded_real_conversion",
        "license_gate",
        "governance_module",
        "governance_version",
        "allowed_input_paths",
        "blocked_field_tokens",
        "task_target_field_blocks",
        "next_recommended_dataset",
    ]:
        assert manifest[key] == template[key]
    assert gov.validate_readiness_manifest(manifest) == []


def test_readiness_manifest_stays_blocked() -> None:
    manifest = json.loads(READINESS.read_text(encoding="utf-8"))
    manifest["license_gate"]["status"] = gov.LICENSE_STATUS_ALLOWED

    findings = gov.validate_readiness_manifest(manifest)

    assert any(item["code"] == "license_gate_not_blocked" for item in findings)
