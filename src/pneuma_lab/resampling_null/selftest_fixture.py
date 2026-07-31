"""Committed zero-spend synthetic source materializer for CLI selftest staging."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sys
import unicodedata
from collections.abc import Mapping

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.artifacts import (
    SCHEMA_BY_KIND,
    seal_study_manifest,
)
from pneuma_lab.resampling_null.assignment import BytesField, U64Field, commitment_sha256
from pneuma_lab.resampling_null.errors import RecordValidationError
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


def seal_synthetic_selftest_study(
    run_root: Path, *, profile: str = "canonical",
    schedule_seed: int | None = None, assignment_master_key: bytes | None = None,
) -> ArtifactRef:
    """Materialize fixed offline fixture inputs and seal only the study stage.

    ``profile`` selects which frozen power-grid contract the manifest binds.
    ``implementation_verification`` binds the separately governed miniature
    grid, whose records can never be admitted under a P0 power authority.
    """
    if profile not in {"canonical", "implementation_verification"}:
        raise RecordValidationError("unregistered selftest study profile")
    # A ceremony commits to the operator-custodied seed and master key before
    # any scientific record exists; the fixture keeps that ordering rather than
    # leaving unopenable placeholder commitments behind.
    schedule_commitment = SHA_A if schedule_seed is None else commitment_sha256(
        "schedule-seed", "study-1", U64Field(schedule_seed),
    )
    assignment_commitment = SHA_A if assignment_master_key is None else commitment_sha256(
        "assignment-master-key", "study-1", BytesField(assignment_master_key),
    )
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

    fixture_root = Path(__file__).resolve().parents[3] / "fixtures" / "resampling_null"
    roster_source = fixture_root / "p0-roster-synthetic.json"
    roster_value = __import__("json").loads(roster_source.read_text(encoding="utf-8"))
    tasks = [
        {key: value for key, value in task.items() if key != "tiers"}
        for task in roster_value["tasks"]
    ]
    task = tasks[0]
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
                "tasks": tasks,
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
        "power-grid",
        "power-topology",
        "template",
        "policy",
        "pads",
    ):
        sources[name] = write_json(external / f"{name}.json", {"name": name})
    sources["storage-policy"] = write_json(
        external / "storage-policy.json",
        {
            "record_kind": "storage_policy_contract_v1",
            "schema_version": "1",
            "mode": "local_test",
            "test_only": True,
            "storage_resource_id": None,
            "measurement_evidence_ref": None,
            "evidence_verifier_public_key_ed25519_hex": None,
            "registry_attestation_public_key_ed25519_hex": None,
            "max_measurement_age_seconds": None,
            "lease_kind": "local_test_process_lock_v1",
            "encryption_at_rest": False,
            "encryption_algorithm": None,
            "kms_key_version": None,
            "acl_enforced": False,
            "acl_policy_sha256": None,
            "measurement_sha256": None,
        },
    )
    sources["power-grid"] = fixture_root / (
        "p0-power-grid.json" if profile == "canonical"
        else "p0-power-grid-implementation-verification.json"
    )
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
    # The prefix loop verifies that every registered implementation descriptor
    # names a manifest source revision whose copied bytes equal this checkout's
    # real module source, so the fixture publishes those exact files.
    source_root = Path(__file__).resolve().parents[3]
    sources["loop-source"] = source_root / "src/pneuma_lab/resampling_null/synthetic_prefix_loop.py"
    sources["environment-source"] = source_root / "src/pneuma_lab/resampling_null/synthetic_environment.py"
    loop_source_ref = planned_fixed_ref(
        sources["loop-source"], subtree="revisions", role="source_revision",
    )
    environment_source_ref = planned_fixed_ref(
        sources["environment-source"], subtree="revisions", role="source_revision",
    )
    sources["roster"] = roster_source
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
                # The canonical profile pins a frozen runtime so a fixture
                # never leaks host identity into a study manifest.  The
                # implementation-verification profile deliberately binds the
                # executing runtime instead: its whole purpose is to prove the
                # production path runs here, and the schedule seal enforces an
                # exact runtime match.
                "python_version": (
                    "3.12.0" if profile == "canonical"
                    else f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                ),
                "unicodedata_unidata_version": (
                    "15.0.0" if profile == "canonical" else unicodedata.unidata_version
                ),
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
    synthetic_grade_ref = authority_asset(
        "branch-grade.json",
        {"record_kind": "synthetic_grade_result_v1", "schema_version": "1"},
        role="synthetic_grade_result",
    )
    synthetic_verifier_ref = authority_asset(
        "branch-verifier.json",
        {"record_kind": "synthetic_verifier_result_v1", "schema_version": "1"},
        role="synthetic_verifier_result",
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
        "request_grammar": "synthetic-request-v1",
        "response_grammar": "synthetic-response-v1",
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
            "record_kind": "prefix_subject_contract_v1", "build_id": "synthetic-subject-v1",
            "model_id": "fixture-subject",
            "nominal_type": "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticProviderActor",
        },
        role="subject_contract",
    )
    simulator_ref = authority_asset(
        "simulator.json",
        {
            **common_call,
            "record_kind": "prefix_simulator_contract_v1", "build_id": "synthetic-simulator-v1",
            "model_id": "fixture-simulator",
            "nominal_type": "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticProviderActor",
        },
        role="simulator_contract",
    )
    parser_ref = authority_asset(
        "parser.json",
        {
            "record_kind": "prefix_tool_parser_contract_v1", "build_id": "synthetic-response-parser-v1",
            "schema_version": "1",
            "nominal_type": "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticResponseParser",
            "response_grammar": "synthetic-response-v1",
            "tool_schema_ref": tool_schema_ref,
            "source_revision_refs": [loop_source_ref],
        },
        role="tool_parser_contract",
    )
    meter_ref = authority_asset(
        "meter.json",
        {
            "record_kind": "prefix_meter_contract_v1", "build_id": "synthetic-meter-v1",
            "schema_version": "1",
            "nominal_type": "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticTraceMeter",
            "clock_source_ref": clock_ref,
            "watchdog_source_ref": watchdog_ref,
            "cost_units": {
                "currency": "usd_micros",
                "generated_tokens": "tokens",
                "model_calls": "calls",
                "wall_clock": "milliseconds",
            },
            "provider_event_grammar": "synthetic-provider-event-v1",
            "settlement_grammar": "synthetic-provider-settlement-v1",
            "zero_cost_synthetic_closure": failure_mode != "synthetic_meter",
            "source_revision_refs": [loop_source_ref],
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
            "record_kind": "prefix_environment_contract_v1", "build_id": "synthetic-environment-v1", "source_revision_refs": [environment_source_ref],
            "benchmark": "tau" if failure_mode == "binding" else "swe",
            "nominal_factory_type": "pneuma_lab.resampling_null.synthetic_environment.SyntheticEnvironmentFactory",
            "snapshot_grammar": "synthetic-environment-snapshot-v1",
            "restore_grammar": "synthetic-environment-snapshot-v1",
            "raw_evidence_grammar": "synthetic-environment-evidence-v1",
            "runtime_id": "cpython-3.12-local",
            "container_digest": "sha256:" + "0" * 64,
        },
        role="environment_contract",
    )
    grader_ref = authority_asset(
        "grader.json",
        {
            **common_task,
            "record_kind": "prefix_grader_contract_v1", "build_id": "synthetic-grader-v1", "source_revision_refs": [loop_source_ref],
            "nominal_type": "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticGradeCodec",
            "raw_evidence_grammar": "synthetic-grade-v1",
            "runtime_id": "cpython-3.12-local",
            "container_digest": "sha256:" + "0" * 64,
        },
        role="grader_contract",
    )
    verifier_ref = authority_asset(
        "verifier.json",
        {
            **common_task,
            "record_kind": "prefix_verifier_contract_v1", "build_id": "synthetic-verifier-v1", "source_revision_refs": [loop_source_ref],
            "nominal_type": "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticVerifierCodec",
            "raw_evidence_grammar": "synthetic-verifier-v1",
            "runtime_id": "cpython-3.12-local",
            "container_digest": "sha256:" + "0" * 64,
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
    task_lanes = []
    branch_registry_tasks = []
    for fixture_task in tasks:
        task_id = fixture_task["task_id"]
        task_common = {
            "schema_version": "1",
            "task_id": task_id,
            "benchmark": fixture_task["benchmark"],
            "build_id": "fixture-build",
            "source_revision_refs": [loop_source_ref],
        }
        branch_program_ref = authority_asset(
            f"branch-program-{task_id}.json",
            {
                "record_kind": "synthetic_prefix_program_v1",
                "schema_version": "1",
                "task_id": task_id,
                "expected_trigger_reason": "no_intervention_opportunity",
                "tool_schema_ref": tool_schema_ref,
                "provider_transcript": [],
                "tool_observations": [],
                "grade_result": {
                    "evidence_ref": synthetic_grade_ref,
                    "success": 0,
                    "partial_reward": 0.0,
                    "infrastructure_failure": False,
                },
                "verifier_result": {
                    "evidence_ref": synthetic_verifier_ref,
                    "finding_count": 0,
                },
                "failure_injection": {
                    "stage": "none",
                    "subject_role": None,
                    "call_index": None,
                    "tool_call_id": None,
                },
                "clock_trace": [{"label": "prefix_epoch", "uint64_ms": 1}],
            },
            role="synthetic_execution_program",
        )
        fixture_input_ref = authority_asset(
            f"task-input-{task_id}.json",
            {
                "record_kind": "prefix_task_input_v1",
                "schema_version": "1",
                "task_id": task_id,
                "benchmark": fixture_task["benchmark"],
                "requires_user_simulator": True,
                "canonical_task_payload": {
                    "instruction": "fixture", "nested_ref": revision_deep_ref,
                },
                "synthetic_execution_program_ref": branch_program_ref,
            },
            role="task_input",
        )
        branch_registry_tasks.append(
            {
                "task_id": task_id,
                "programs": [
                    {
                        "branch_ordinal": ordinal,
                        "program_ref": branch_program_ref,
                    }
                    for ordinal in range(4)
                ],
            }
        )
        fixture_environment_ref = authority_asset(
            f"environment-{task_id}.json",
            {**task_common, "record_kind": "prefix_environment_contract_v1", "build_id": "synthetic-environment-v1", "source_revision_refs": [environment_source_ref],
             "nominal_factory_type": "pneuma_lab.resampling_null.synthetic_environment.SyntheticEnvironmentFactory",
             "snapshot_grammar": "synthetic-environment-snapshot-v1",
             "restore_grammar": "synthetic-environment-snapshot-v1",
             "raw_evidence_grammar": "synthetic-environment-evidence-v1",
             "runtime_id": "cpython-3.12-local", "container_digest": "sha256:" + "0" * 64},
            role="environment_contract",
        )
        fixture_grader_ref = authority_asset(
            f"grader-{task_id}.json",
            {**task_common, "record_kind": "prefix_grader_contract_v1", "build_id": "synthetic-grader-v1", "source_revision_refs": [loop_source_ref],
             "nominal_type": "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticGradeCodec", "raw_evidence_grammar": "synthetic-grade-v1",
             "runtime_id": "cpython-3.12-local", "container_digest": "sha256:" + "0" * 64},
            role="grader_contract",
        )
        fixture_verifier_ref = authority_asset(
            f"verifier-{task_id}.json",
            {**task_common, "record_kind": "prefix_verifier_contract_v1", "build_id": "synthetic-verifier-v1", "source_revision_refs": [loop_source_ref],
             "nominal_type": "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticVerifierCodec", "raw_evidence_grammar": "synthetic-verifier-v1",
             "runtime_id": "cpython-3.12-local", "container_digest": "sha256:" + "0" * 64},
            role="verifier_contract",
        )
        fixture_isolation_ref = authority_asset(
            f"isolation-{task_id}.json",
            {**task_common, "record_kind": "prefix_isolation_contract_v1",
             "distinct_environment_instances": True, "distinct_processes": True,
             "distinct_roots": True, "no_shared_writable_state": True,
             "qualification_ref": qualification_ref},
            role="isolation_contract",
        )
        task_lanes.append({
            "task_id": task_id, "prefix_lane_ordinal": 0,
            "lane_ordinals_by_execution_rank": [0, 0, 0, 0],
            "task_input_ref": fixture_input_ref,
            "environment_contract_ref": fixture_environment_ref,
            "grader_contract_ref": fixture_grader_ref,
            "verifier_contract_ref": fixture_verifier_ref,
            "isolation_contract_ref": fixture_isolation_ref,
        })
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
            "task_lanes": task_lanes,
        },
    )
    sources["branch-program-registry"] = write_json(
        external / "branch-program-registry.json",
        {
            "record_kind": "resampling_branch_program_registry_v1",
            "schema_version": "0.1.0",
            "tasks": branch_registry_tasks,
        },
    )
    study = write_json(
        external / "study.json",
        _fixture_record(
            "resampling_study_manifest",
            {
                "commitment_scheme": "resampling-null-key-ceremony-v1",
                "roster_local_nonce_commitment_sha256": SHA_A,
                "schedule_seed_commitment_sha256": schedule_commitment,
                "assignment_master_key_commitment_sha256": assignment_commitment,
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
            sources["branch-program-registry"],
            sources["storage-policy"],
            sources["power-grid"],
            sources["power-topology"],
            sources["tokenizer"],
            sources["template"],
            sources["policy"],
            sources["pads"],
            sorted(
                (sources["revision"], sources["loop-source"], sources["environment-source"]),
                key=lambda path: path.name,
            ),
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
