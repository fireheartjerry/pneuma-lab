from __future__ import annotations

from pneuma_lab.governance import open_swe_traces as gov


def test_allowed_paths_pass_the_allowlist() -> None:
    paths = [
        "input.dataset.dataset_id",
        "input.dataset.source_group",
        "input.language",
        "input.source.instance_id_digest",
        "input.source.license",
        "input.trajectory_summary.num_messages",
        "input.tool_summary.tool_counts.read_file",
        "input.feature_refs.0",
    ]

    findings = gov.check_input_allowlist(paths, task_type="RISK_PREDICTION")

    assert findings == []


def test_raw_trajectory_tool_and_patch_fields_are_blocked() -> None:
    paths = [
        "input.trajectory",
        "input.tool_calls",
        "input.tools",
        "input.metadata.reference_patch.patch",
        "input.metadata.model_patch.patch",
        "input.metadata.category",
    ]

    findings = gov.check_input_allowlist(paths, task_type="RISK_PREDICTION")

    assert {item["path"] for item in findings} == {
        "input.trajectory",
        "input.tool_calls",
        "input.tools",
        "input.metadata.reference_patch.patch",
        "input.metadata.model_patch.patch",
        "input.metadata.category",
    }
    assert {item["code"] for item in findings} == {"blocked_field"}


def test_resolved_target_is_blocked_from_risk_prediction_input() -> None:
    findings = gov.check_input_allowlist(
        ["input.resolved"], task_type="RISK_PREDICTION"
    )

    assert findings == [
        {
            "path": "input.resolved",
            "code": "blocked_field",
            "message": "input path touches raw, oracle, target, or metadata content",
            "blocked_tokens": ["resolved"],
        }
    ]


def test_raw_identifiers_are_blocked_not_just_digests() -> None:
    findings = gov.check_input_allowlist(
        ["input.source.instance_id", "input.source.repo", "input.source.trajectory_id"],
        task_type="RISK_PREDICTION",
    )

    assert {item["path"] for item in findings} == {
        "input.source.instance_id",
        "input.source.repo",
        "input.source.trajectory_id",
    }


def test_example_leakage_scan_reports_blocked_fields_only() -> None:
    example = {
        "task_type": "RISK_PREDICTION",
        "input": {
            "dataset": {"dataset_id": "open-swe-traces"},
            "trajectory": [{"role": "assistant", "content": "raw text"}],
            "resolved": True,
        },
    }

    findings = gov.check_example_input_leakage(example)

    assert {item["path"] for item in findings} == {
        "input.trajectory.*.content",
        "input.trajectory.*.role",
        "input.resolved",
    }


def test_label_provenance_forbids_harness_outcome() -> None:
    findings = gov.validate_label_provenance(
        {"kind": "harness_outcome", "confidence": "medium"}
    )

    assert findings == [
        {
            "path": "label_provenance.kind",
            "code": "harness_outcome_forbidden",
            "message": (
                "Open-SWE-Traces resolved outcomes are synthetic/automated; "
                "label_provenance.kind must never be harness_outcome"
            ),
        }
    ]


def test_label_provenance_rejects_unknown_kind() -> None:
    findings = gov.validate_label_provenance(
        {"kind": "human_label", "confidence": "low"}
    )

    assert {item["code"] for item in findings} == {"kind_not_allowed"}


def test_label_provenance_rejects_high_confidence() -> None:
    findings = gov.validate_label_provenance(
        {"kind": "constructed_label", "confidence": "high"}
    )

    assert findings == [
        {
            "path": "label_provenance.confidence",
            "code": "confidence_too_high",
            "message": (
                "resolved-derived confidence must stay at medium or lower "
                "pending independent review of the verifier methodology"
            ),
        }
    ]


def test_label_provenance_accepts_constructed_or_simulated_at_or_below_medium() -> None:
    assert (
        gov.validate_label_provenance(
            {"kind": "constructed_label", "confidence": "medium"}
        )
        == []
    )
    assert (
        gov.validate_label_provenance({"kind": "simulated_label", "confidence": "low"})
        == []
    )


def test_training_authorization_defaults_stay_non_training() -> None:
    defaults = gov.TRAINING_AUTHORIZATION_DEFAULTS

    assert defaults["training_authorization"] == "not_authorized"
    assert defaults["training_weight"] == 0.0
    assert defaults["model_use_tier"] == "train_after_adapter"


def test_blocked_training_uses_includes_minimax_qwen_tos_caveat() -> None:
    uses = gov.blocked_training_uses()

    assert gov.MINIMAX_QWEN_TOS_CAVEAT in uses
    assert any("minimax" in use.lower() or "qwen" in use.lower() for use in uses)
