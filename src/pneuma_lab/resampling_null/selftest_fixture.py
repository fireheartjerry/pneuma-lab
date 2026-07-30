"""Committed zero-spend synthetic source materializer for CLI selftest staging."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path
import sys
import unicodedata

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.artifacts import (
    SCHEMA_BY_KIND,
    seal_study_manifest,
)
from pneuma_lab.resampling_null.types import ArtifactRef

SHA_A = "a" * 64
SHA_B = "b" * 64
FROZEN = "2026-07-28T12:00:00Z"
FROZEN_UPSTREAM_KINDS = tuple(
    sorted(
        kind
        for kind in SCHEMA_BY_KIND
        if kind != "resampling_artifact_root"
    )
)



def _fixture_ref(
    path: str,
    *,
    role: str,
    sha256: str,
    byte_count: int,
    media_type: str,
) -> dict[str, object]:
    return {
        "role": role,
        "relative_path": path,
        "sha256": sha256,
        "byte_count": byte_count,
        "media_type": media_type,
    }


def _fixture_record(
    kind: str,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "record_kind": kind,
        "schema_version": "0.1.0",
        "study_id": "study-1",
        "frozen_created_at": FROZEN,
        "provenance": {
            "design_sha256": SHA_A,
            "code_sha256": SHA_B,
        },
        "payload": payload,
    }


def seal_synthetic_selftest_study(run_root: Path) -> ArtifactRef:
    """Materialize fixed offline fixture inputs and seal only the study stage."""
    tmp_path = Path(run_root).resolve(strict=True)
    failure_mode: str | None = None
    external = tmp_path / "sources" / "selftest-fixture"
    external.mkdir(parents=True)

    def write_json(path: Path, value: object) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_json_bytes(value, indent=None))
        return path

    def external_ref(
        source: Path,
        *,
        relative_path: str,
        role: str,
        media_type: str = "application/json",
    ) -> dict[str, object]:
        payload = source.read_bytes()
        return _fixture_ref(
            relative_path,
            role=role,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
            media_type=media_type,
        )

    def planned_fixed_ref(
        source: Path,
        *,
        subtree: str,
        role: str,
    ) -> dict[str, object]:
        payload = source.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        return _fixture_ref(
            f"sources/{subtree}/{digest}-{source.name}",
            role=role,
            sha256=digest,
            byte_count=len(payload),
            media_type=(
                "application/octet-stream"
                if role == "source_revision"
                else "application/json"
            ),
        )

    task = {
        "task_id": "task-1",
        "benchmark": "swe",
        "stratum": "python",
        "lineage": "repo-1",
        "groups": [
            {"kind": "language", "value": "python"},
            {"kind": "domain", "value": "software"},
            {"kind": "issue_family", "value": "bug"},
        ],
    }
    revision_deep_source = write_json(
        external / "sources" / "provider-authority" / "revision-deep.json",
        {
            "record_kind": "synthetic_deep_authority_leaf_v1",
            "schema_version": "1",
            "value_id": "revision-authority",
        },
    )
    revision_deep_ref = external_ref(
        revision_deep_source,
        relative_path="sources/provider-authority/revision-deep.json",
        role="deep_authority_asset",
    )
    sources = {
        "tasks": write_json(
            external / "tasks.json",
            {
                "record_kind": "resampling_task_registry_v1",
                "schema_version": "1",
                "tasks": [task],
            },
        ),
        "tokenizer": write_json(
            external / "tokenizer.json",
            {
                "record_kind": "synthetic_tokenizer_asset_v1",
                "schema_version": "1",
                "tokenizer_id": "fixture-v1",
            },
        ),
        "revision": write_json(
            external / "revision.json",
            {"revision": "fixture-v1"},
        ),
    }
    for name in (
        "roster",
        "assignment",
        "storage-policy",
        "power-grid",
        "power-topology",
        "template",
        "policy",
        "pads",
    ):
        sources[name] = write_json(external / f"{name}.json", {"name": name})
    fixture_root = Path(__file__).resolve().parents[3] / "fixtures" / "resampling_null"
    sources["power-grid"] = fixture_root / "p0-power-grid.json"
    sources["power-topology"] = fixture_root / "p0-power-screen-topology.json"
    sources["required"] = write_json(
        external / "required.json",
        list(FROZEN_UPSTREAM_KINDS),
    )
    sources["eligibility"] = write_json(
        external / "eligibility.json",
        {"record_kind": "test_only_eligibility_fixture"},
    )
    sources["ceremony-policy"] = write_json(
        external / "ceremony-policy.json",
        {"record_kind": "test_only_ceremony_policy_fixture"},
    )
    tokenizer_ref = planned_fixed_ref(
        sources["tokenizer"],
        subtree="tokenizer",
        role="tokenizer",
    )
    revision_ref = planned_fixed_ref(
        sources["revision"],
        subtree="revisions",
        role="source_revision",
    )
    sources["roster"] = write_json(
        external / "roster.json",
        {
            "record_kind": "resampling_roster_v1",
            "schema_version": "1",
            "roster_kind": (
                "eligible_confirmation"
                if failure_mode
                in {"confirmation_missing", "confirmation_conditional"}
                else "synthetic_fixture"
            ),
            "supported_tiers": [120, 160],
            "tasks": [{**task, "tiers": [120, 160]}],
        },
    )
    sources["assignment"] = write_json(
        external / "assignment.json",
        {
            "record_kind": "resampling_assignment_program_v1",
            "schema_version": "1",
            "assignment_mode": (
                "confirmation_lineage_matching"
                if failure_mode
                in {
                    "authority_mismatch",
                    "confirmation_missing",
                    "confirmation_conditional",
                }
                else "synthetic_derangement"
            ),
            "matching_algorithm": (
                "exact_constrained_min_cost_v1"
                if failure_mode
                in {
                    "authority_mismatch",
                    "confirmation_missing",
                    "confirmation_conditional",
                }
                else "synthetic_cyclic_offset_v1"
            ),
            "finding_count_band_upper_bounds": [1, 3],
            "report_length_band_upper_bounds": [128, 512],
            "verifier_normalizer_contract": {
                "contract_id": "assignment-verifier-normalizer-v1",
                "normalizer_source_ref": revision_ref,
                "normalizer_source_sha256": revision_ref["sha256"],
                "report_tokenizer_sha256": tokenizer_ref["sha256"],
                "benchmark_component_kinds": {
                    "SWE": ["check_runner", "failure_class"],
                    "TAU": ["evaluator_component"],
                },
            },
            "assignment_runtime_contract": {
                "implementation": "CPython",
                "python_version": (
                    f"{sys.version_info.major}.{sys.version_info.minor}."
                    f"{sys.version_info.micro}"
                ),
                "unicodedata_unidata_version": unicodedata.unidata_version,
            },
            "backend_receipt_ref": (
                revision_ref
                if failure_mode
                in {
                    "authority_mismatch",
                    "confirmation_missing",
                    "confirmation_conditional",
                }
                else None
            ),
            "stratum_keys": ["benchmark", "language"],
        },
    )

    authority_dir = external / "sources" / "provider-authority"

    def authority_asset(name: str, value: object, *, role: str) -> dict[str, object]:
        source = write_json(authority_dir / name, value)
        return external_ref(
            source,
            relative_path=f"sources/provider-authority/{name}",
            role=role,
        )

    prompt_ref = authority_asset(
        "prompt.json",
        {
            "record_kind": "synthetic_prompt_template_asset_v1",
            "schema_version": "1",
            "template_id": "fixture-v1",
        },
        role="prompt_template",
    )
    tool_schema_ref = authority_asset(
        "tools.json",
        {
            "record_kind": "synthetic_tool_schema_asset_v1",
            "schema_version": "1",
            "tools": [],
        },
        role="tool_schema",
    )
    clock_ref = authority_asset(
        "clock.json",
        {
            "record_kind": "synthetic_clock_asset_v1",
            "schema_version": "1",
            "clock_id": "fixture-v1",
        },
        role="clock_source",
    )
    watchdog_ref = authority_asset(
        "watchdog.json",
        {
            "record_kind": "synthetic_watchdog_asset_v1",
            "schema_version": "1",
            "watchdog_id": "fixture-v1",
        },
        role="watchdog_source",
    )
    qualification_ref = authority_asset(
        "qualification.json",
        {
            "record_kind": "synthetic_isolation_qualification_asset_v1",
            "schema_version": "1",
            "qualification_id": "fixture-v1",
        },
        role="isolation_qualification",
    )
    common_call = {
        "schema_version": "1",
        "tokenizer_ref": tokenizer_ref,
        "prompt_template_ref": prompt_ref,
        "tool_schema_ref": tool_schema_ref,
        "request_grammar": "fixture-request-v1",
        "response_grammar": "fixture-response-v1",
        "seeded_call_grammar": "call-seed-v1",
        "stateless_client_attestation": "fixture-stateless-v1",
        "aggregate_caps": {
            "generated_tokens": 40,
            "model_calls": 4,
            "turns": 4,
        },
        "per_call_caps": {"generated_tokens": 12, "turns": 1},
        "build_id": "fixture-build",
        "source_revision_refs": [revision_ref],
    }
    subject_ref = authority_asset(
        "subject.json",
        {
            **common_call,
            "record_kind": "prefix_subject_contract_v1",
            "model_id": "fixture-subject",
            "nominal_type": "FixtureSubject",
        },
        role="subject_contract",
    )
    simulator_ref = authority_asset(
        "simulator.json",
        {
            **common_call,
            "record_kind": "prefix_simulator_contract_v1",
            "model_id": "fixture-simulator",
            "nominal_type": "FixtureSimulator",
        },
        role="simulator_contract",
    )
    parser_ref = authority_asset(
        "parser.json",
        {
            "record_kind": "prefix_tool_parser_contract_v1",
            "schema_version": "1",
            "nominal_type": "FixtureParser",
            "build_id": "fixture-build",
            "response_grammar": "fixture-response-v1",
            "tool_schema_ref": tool_schema_ref,
            "source_revision_refs": [revision_ref],
        },
        role="tool_parser_contract",
    )
    meter_ref = authority_asset(
        "meter.json",
        {
            "record_kind": "prefix_meter_contract_v1",
            "schema_version": "1",
            "nominal_type": "FixtureMeter",
            "build_id": "fixture-build",
            "clock_source_ref": clock_ref,
            "watchdog_source_ref": watchdog_ref,
            "cost_units": {
                "currency": "usd_micros",
                "generated_tokens": "tokens",
                "model_calls": "calls",
                "wall_clock": "milliseconds",
            },
            "provider_event_grammar": "fixture-provider-event-v1",
            "settlement_grammar": "fixture-settlement-v1",
            "zero_cost_synthetic_closure": failure_mode != "synthetic_meter",
            "source_revision_refs": [revision_ref],
        },
        role="meter_contract",
    )
    task_input_ref = authority_asset(
        "task-input.json",
        {
            "record_kind": "prefix_task_input_v1",
            "schema_version": "1",
            "task_id": "task-1",
            "benchmark": "swe",
            "requires_user_simulator": True,
            "canonical_task_payload": {
                "instruction": "fixture",
                "nested_ref": revision_deep_ref,
            },
        },
        role="task_input",
    )
    common_task = {
        "schema_version": "1",
        "task_id": "task-1",
        "benchmark": "swe",
        "build_id": "fixture-build",
        "source_revision_refs": [revision_ref],
    }
    environment_ref = authority_asset(
        "environment.json",
        {
            **common_task,
            "record_kind": "prefix_environment_contract_v1",
            "benchmark": "tau" if failure_mode == "binding" else "swe",
            "nominal_factory_type": "FixtureEnvironmentFactory",
            "snapshot_grammar": "fixture-snapshot-v1",
            "restore_grammar": "fixture-restore-v1",
            "raw_evidence_grammar": "fixture-environment-evidence-v1",
            "runtime_id": "cpython-fixture",
            "container_digest": "sha256:" + SHA_A,
        },
        role="environment_contract",
    )
    grader_ref = authority_asset(
        "grader.json",
        {
            **common_task,
            "record_kind": "prefix_grader_contract_v1",
            "nominal_type": "FixtureGrader",
            "raw_evidence_grammar": "fixture-grade-evidence-v1",
            "runtime_id": "cpython-fixture",
            "container_digest": "sha256:" + SHA_A,
        },
        role="grader_contract",
    )
    verifier_ref = authority_asset(
        "verifier.json",
        {
            **common_task,
            "record_kind": "prefix_verifier_contract_v1",
            "nominal_type": "FixtureVerifier",
            "raw_evidence_grammar": "fixture-verifier-evidence-v1",
            "runtime_id": "cpython-fixture",
            "container_digest": "sha256:" + SHA_A,
        },
        role="verifier_contract",
    )
    isolation_ref = authority_asset(
        "isolation.json",
        {
            **common_task,
            "record_kind": "prefix_isolation_contract_v1",
            "distinct_environment_instances": True,
            "distinct_processes": True,
            "distinct_roots": True,
            "no_shared_writable_state": True,
            "qualification_ref": qualification_ref,
        },
        role="isolation_contract",
    )
    sources["provider"] = write_json(
        external / "provider.json",
        {
            "record_kind": "provider_lane_plan_v2",
            "schema_version": "2",
            "lanes": [
                {
                    "ordinal": 0,
                    "lane_id": "lane-0",
                    "prefix_caps": {
                        "generated_tokens": 40,
                        "model_calls": 4,
                        "tool_calls": 4,
                        "wall_clock_ms": 1_000,
                    },
                    "branch_caps": {
                        "generated_tokens": 20,
                        "model_calls": 2,
                        "tool_calls": 4,
                        "wall_clock_ms": 500,
                        "pending_prefix_calls_count_against_tool_cap": True,
                    },
                    "simulator_caps": {
                        "aggregate_generated_tokens": 40,
                        "aggregate_model_calls": 4,
                        "aggregate_turns": 4,
                        "per_call_generated_tokens": 12,
                        "per_call_turns": 1,
                    },
                    "subject_contract_ref": subject_ref,
                    "simulator_contract_ref": simulator_ref,
                    "tool_parser_contract_ref": parser_ref,
                    "meter_contract_ref": meter_ref,
                }
            ],
            "task_lanes": [
                {
                    "task_id": "task-1",
                    "prefix_lane_ordinal": 0,
                    "lane_ordinals_by_execution_rank": [0, 0, 0, 0],
                    "task_input_ref": task_input_ref,
                    "environment_contract_ref": environment_ref,
                    "grader_contract_ref": grader_ref,
                    "verifier_contract_ref": verifier_ref,
                    "isolation_contract_ref": isolation_ref,
                }
            ],
        },
    )
    study = write_json(
        external / "study.json",
        _fixture_record(
            "resampling_study_manifest",
            {
                "commitment_scheme": "resampling-null-key-ceremony-v1",
                "roster_local_nonce_commitment_sha256": SHA_A,
                "schedule_seed_commitment_sha256": SHA_A,
                "assignment_master_key_commitment_sha256": SHA_A,
            },
        ),
    )
    def seal() -> ArtifactRef:
        return seal_study_manifest(
            study,
            sources["tasks"],
            sources["roster"],
            sources["assignment"],
            sources["provider"],
            sources["storage-policy"],
            sources["power-grid"],
            sources["power-topology"],
            sources["tokenizer"],
            sources["template"],
            sources["policy"],
            sources["pads"],
            [sources["revision"]],
            sources["required"],
            eligibility_manifest_source=(
                sources["eligibility"]
                if failure_mode
                in {"synthetic_conditional", "confirmation_conditional"}
                else None
            ),
            roster_ceremony_policy_source=(
                sources["ceremony-policy"]
                if failure_mode
                in {"synthetic_conditional", "confirmation_conditional"}
                else None
            ),
            run_root=run_root,
            out=run_root / "study-manifest.json",
        )
    return seal()


__all__ = ("seal_synthetic_selftest_study",)
