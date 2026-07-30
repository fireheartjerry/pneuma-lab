"""Shared provider-authority graph fixtures."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.artifacts import validate_record
from pneuma_lab.resampling_null.types import ArtifactRef
from tests.resampling_null.provider_study_fixture import (
    ProviderStudySealFixture,
    build_provider_study_fixture,
)


@dataclass(frozen=True, slots=True)
class ProviderAuthorityFixture:
    schedule_ref: ArtifactRef
    refs: dict[str, ArtifactRef]

    @staticmethod
    def build(
        root: Path,
        **kwargs: Any,
    ) -> ProviderAuthorityFixture:
        return _build_provider_authority_fixture(root, **kwargs)

    @staticmethod
    def build_study(
        tmp_path: Path,
        *,
        failure_mode: str | None,
    ) -> ProviderStudySealFixture:
        return build_provider_study_fixture(
            tmp_path,
            failure_mode=failure_mode,
        )

    def __iter__(
        self,
    ) -> Iterator[ArtifactRef | dict[str, ArtifactRef]]:
        yield self.schedule_ref
        yield self.refs


def _build_provider_authority_fixture(
    root: Path,
    *,
    plan_kind: str = "provider_lane_plan_v2",
    subject_extra: bool = False,
    environment_benchmark: str = "swe",
    scheduled_lane: str = "lane-0",
    requires_simulator: bool = True,
    foreign_requires_simulator: bool | None = None,
    foreign_task_input_extra: bool = False,
    foreign_environment_extra: bool = False,
    foreign_grade_partial_reward: float | None = None,
    simulator_present: bool = True,
    simulator_aggregate_generated_tokens: int = 40,
    lane_simulator_aggregate_generated_tokens: int | None = None,
    subject_aggregate_generated_tokens: int = 40,
    subject_aggregate_model_calls: int = 4,
    parser_response_grammar: str = "fixture-response-v1",
    parser_tool_schema_drift: bool = False,
    meter_zero_cost: bool = True,
    schedule_authority: str = "synthetic_validation",
    program_expected_trigger: str = "no_intervention_opportunity",
    program_failure_injection: dict[str, object] | None = None,
    tool_names: tuple[str, ...] = ("read",),
    role_overrides: dict[str, str] | None = None,
    media_type_overrides: dict[str, str] | None = None,
    executable_sources: bool = False,
) -> ProviderAuthorityFixture:
    root.mkdir()
    effective_role_overrides = role_overrides or {}
    effective_media_type_overrides = media_type_overrides or {}

    def blob(
        relative_path: str,
        value: object,
        *,
        role: str,
        media_type: str | None = None,
    ) -> ArtifactRef:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            value
            if isinstance(value, bytes)
            else canonical_json_bytes(value, indent=None)
        )
        path.write_bytes(payload)
        return ArtifactRef(
            role=effective_role_overrides.get(relative_path, role),
            relative_path=relative_path,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
            media_type=effective_media_type_overrides.get(relative_path)
            or media_type
            or ("application/json" if not isinstance(value, bytes) else "text/plain"),
        )

    def ref_value(ref: ArtifactRef) -> dict[str, object]:
        return {
            "role": ref.role,
            "relative_path": ref.relative_path,
            "sha256": ref.sha256,
            "byte_count": ref.byte_count,
            "media_type": ref.media_type,
        }

    deep_leaf_ref = blob(
        "sources/deep-leaf.json",
        {
            "record_kind": "synthetic_deep_authority_leaf_v1",
            "schema_version": "1",
            "value_id": "authority",
        },
        role="deep_authority_asset",
    )
    deep_ref = blob(
        "sources/deep.json",
        {
            "record_kind": "synthetic_deep_authority_link_v1",
            "schema_version": "1",
            "nested_ref": ref_value(deep_leaf_ref),
        },
        role="deep_authority_asset",
    )
    revision_ref = blob(
        "sources/revision.json",
        b"fixture reviewed source\n",
        role="source_revision",
        media_type="application/octet-stream",
    )
    if executable_sources:
        source_root = Path(__file__).parents[2]
        environment_revision_ref = blob(
            "sources/synthetic-environment.py",
            (
                source_root / "src/pneuma_lab/resampling_null/synthetic_environment.py"
            ).read_bytes(),
            role="source_revision",
            media_type="application/octet-stream",
        )
        loop_revision_ref = blob(
            "sources/synthetic-prefix-loop.py",
            (
                source_root / "src/pneuma_lab/resampling_null/synthetic_prefix_loop.py"
            ).read_bytes(),
            role="source_revision",
            media_type="application/octet-stream",
        )
    else:
        environment_revision_ref = revision_ref
        loop_revision_ref = revision_ref
    tokenizer_ref = blob(
        "sources/tokenizer.json",
        {
            "record_kind": "synthetic_tokenizer_asset_v1",
            "schema_version": "1",
            "tokenizer_id": "fixture-v1",
        },
        role="tokenizer",
    )
    prompt_ref = blob(
        "sources/prompt.json",
        {
            "record_kind": "synthetic_prompt_template_asset_v1",
            "schema_version": "1",
            "template_id": "fixture-v1",
        },
        role="prompt_template",
    )
    tool_schema_ref = blob(
        "sources/tools.json",
        {
            "record_kind": "synthetic_tool_schema_asset_v1",
            "schema_version": "1",
            "tools": [{"name": name} for name in tool_names],
        },
        role="tool_schema",
    )
    alternate_tool_schema_ref = blob(
        "sources/tools-alternate.json",
        {
            "record_kind": "synthetic_tool_schema_asset_v1",
            "schema_version": "1",
            "tools": [{"name": "drift"}],
        },
        role="tool_schema",
    )
    clock_ref = blob(
        "sources/clock.txt",
        {
            "record_kind": "synthetic_clock_asset_v1",
            "schema_version": "1",
            "clock_id": "fixture-v1",
        },
        role="clock_source",
    )
    watchdog_ref = blob(
        "sources/watchdog.txt",
        {
            "record_kind": "synthetic_watchdog_asset_v1",
            "schema_version": "1",
            "watchdog_id": "fixture-v1",
        },
        role="watchdog_source",
    )
    qualification_ref = blob(
        "sources/qualification.json",
        {
            "record_kind": "synthetic_isolation_qualification_asset_v1",
            "schema_version": "1",
            "qualification_id": "fixture-v1",
        },
        role="isolation_qualification",
    )
    synthetic_grade_ref = blob(
        "sources/synthetic-grade.json",
        {"success": 0, "partial_reward": 0.0, "infrastructure_failure": False},
        role="synthetic_grade_result",
    )
    synthetic_verifier_ref = blob(
        "sources/synthetic-verifier.json",
        {"finding_count": 0},
        role="synthetic_verifier_result",
    )

    refs = {
        "revision": revision_ref,
        "tokenizer": tokenizer_ref,
        "prompt": prompt_ref,
        "tool_schema": tool_schema_ref,
        "clock": clock_ref,
        "watchdog": watchdog_ref,
        "qualification": qualification_ref,
        "deep": deep_ref,
        "deep_leaf": deep_leaf_ref,
        "synthetic_grade": synthetic_grade_ref,
        "synthetic_verifier": synthetic_verifier_ref,
    }
    source_revisions = [
        ref_value(ref)
        for ref in (
            (
                environment_revision_ref,
                loop_revision_ref,
            )
            if executable_sources
            else (revision_ref,)
        )
    ]
    call_caps = (
        {
            "aggregate_generated_tokens": (
                simulator_aggregate_generated_tokens
                if lane_simulator_aggregate_generated_tokens is None
                else lane_simulator_aggregate_generated_tokens
            ),
            "aggregate_model_calls": 4,
            "aggregate_turns": 4,
            "per_call_generated_tokens": 12,
            "per_call_turns": 1,
        }
        if simulator_present
        else {
            "aggregate_generated_tokens": 0,
            "aggregate_model_calls": 0,
            "aggregate_turns": 0,
            "per_call_generated_tokens": 0,
            "per_call_turns": 0,
        }
    )
    subject: dict[str, object] = {
        "record_kind": "prefix_subject_contract_v1",
        "schema_version": "1",
        "model_id": "fixture-subject",
        "tokenizer_ref": ref_value(tokenizer_ref),
        "prompt_template_ref": ref_value(prompt_ref),
        "tool_schema_ref": ref_value(tool_schema_ref),
        "request_grammar": (
            "synthetic-request-v1" if executable_sources else "fixture-request-v1"
        ),
        "response_grammar": (
            "synthetic-response-v1" if executable_sources else "fixture-response-v1"
        ),
        "seeded_call_grammar": "call-seed-v1",
        "stateless_client_attestation": "fixture-stateless-v1",
        "aggregate_caps": {
            "generated_tokens": subject_aggregate_generated_tokens,
            "model_calls": subject_aggregate_model_calls,
            "turns": 4,
        },
        "per_call_caps": {
            "generated_tokens": 12,
            "turns": 1,
        },
        "nominal_type": (
            "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticProviderActor"
            if executable_sources
            else "FixtureSubject"
        ),
        "build_id": ("synthetic-subject-v1" if executable_sources else "fixture-build"),
        "source_revision_refs": [ref_value(loop_revision_ref)],
    }
    if subject_extra:
        subject["open"] = True
    subject_ref = blob(
        "sources/subject.json",
        subject,
        role="subject_contract",
    )
    simulator_ref = blob(
        "sources/simulator.json",
        {
            **subject,
            "record_kind": "prefix_simulator_contract_v1",
            "model_id": "fixture-simulator",
            "nominal_type": (
                "pneuma_lab.resampling_null.synthetic_prefix_loop."
                "SyntheticProviderActor"
                if executable_sources
                else "FixtureSimulator"
            ),
            "build_id": (
                "synthetic-simulator-v1" if executable_sources else "fixture-build"
            ),
            "aggregate_caps": {
                "generated_tokens": simulator_aggregate_generated_tokens,
                "model_calls": 4,
                "turns": 4,
            },
        },
        role="simulator_contract",
    )
    parser_ref = blob(
        "sources/parser.json",
        {
            "record_kind": "prefix_tool_parser_contract_v1",
            "schema_version": "1",
            "nominal_type": (
                "pneuma_lab.resampling_null.synthetic_prefix_loop."
                "SyntheticResponseParser"
                if executable_sources
                else "FixtureParser"
            ),
            "build_id": (
                "synthetic-response-parser-v1"
                if executable_sources
                else "fixture-build"
            ),
            "response_grammar": (
                "synthetic-response-v1"
                if executable_sources
                else parser_response_grammar
            ),
            "tool_schema_ref": ref_value(
                (
                    alternate_tool_schema_ref
                    if parser_tool_schema_drift
                    else tool_schema_ref
                )
            ),
            "source_revision_refs": [ref_value(loop_revision_ref)],
        },
        role="tool_parser_contract",
    )
    meter_ref = blob(
        "sources/meter.json",
        {
            "record_kind": "prefix_meter_contract_v1",
            "schema_version": "1",
            "nominal_type": (
                "pneuma_lab.resampling_null.synthetic_prefix_loop.SyntheticTraceMeter"
                if executable_sources
                else "FixtureMeter"
            ),
            "build_id": (
                "synthetic-meter-v1" if executable_sources else "fixture-build"
            ),
            "clock_source_ref": ref_value(clock_ref),
            "watchdog_source_ref": ref_value(watchdog_ref),
            "cost_units": {
                "currency": "usd_micros",
                "generated_tokens": "tokens",
                "model_calls": "calls",
                "wall_clock": "milliseconds",
            },
            "provider_event_grammar": (
                "synthetic-provider-event-v1"
                if executable_sources
                else "fixture-provider-event-v1"
            ),
            "settlement_grammar": (
                "synthetic-provider-settlement-v1"
                if executable_sources
                else "fixture-settlement-v1"
            ),
            "zero_cost_synthetic_closure": meter_zero_cost,
            "source_revision_refs": [ref_value(loop_revision_ref)],
        },
        role="meter_contract",
    )
    refs.update(
        {
            "subject": subject_ref,
            "simulator": simulator_ref,
            "parser": parser_ref,
            "meter": meter_ref,
        }
    )

    task_rows: list[dict[str, object]] = []
    registry_tasks: list[dict[str, object]] = []
    for task_id, task_requires_simulator in (
        ("task-1", requires_simulator),
        (
            "task-foreign",
            (
                requires_simulator
                if foreign_requires_simulator is None
                else foreign_requires_simulator
            ),
        ),
    ):
        program_partial_reward = (
            foreign_grade_partial_reward
            if task_id == "task-foreign"
            and foreign_grade_partial_reward is not None
            else 0.0
        )
        program_ref = blob(
            f"sources/{task_id}-program.json",
            {
                "record_kind": "synthetic_prefix_program_v1",
                "schema_version": "1",
                "task_id": task_id,
                "expected_trigger_reason": program_expected_trigger,
                "tool_schema_ref": ref_value(tool_schema_ref),
                "provider_transcript": [],
                "tool_observations": [],
                "grade_result": {
                    "evidence_ref": ref_value(synthetic_grade_ref),
                    "success": 0,
                    "partial_reward": program_partial_reward,
                    "infrastructure_failure": False,
                },
                "verifier_result": {
                    "evidence_ref": ref_value(synthetic_verifier_ref),
                    "finding_count": 0,
                },
                "failure_injection": (
                    program_failure_injection
                    if program_failure_injection is not None
                    else {
                        "stage": "none",
                        "subject_role": None,
                        "call_index": None,
                        "tool_call_id": None,
                    }
                ),
                "clock_trace": [{"label": "prefix_epoch", "uint64_ms": 1}],
            },
            role="synthetic_execution_program",
        )
        task_input: dict[str, object] = {
            "record_kind": "prefix_task_input_v1",
            "schema_version": "1",
            "task_id": task_id,
            "benchmark": "swe",
            "requires_user_simulator": task_requires_simulator,
            "synthetic_execution_program_ref": ref_value(program_ref),
            "canonical_task_payload": {
                "instruction": task_id,
                "deep_ref": ref_value(deep_ref),
            },
        }
        if task_id == "task-foreign" and foreign_task_input_extra:
            task_input["open"] = True
        task_input_ref = blob(
            f"sources/{task_id}-input.json",
            task_input,
            role="task_input",
        )
        contract_refs: dict[str, ArtifactRef] = {}
        for kind, record_kind in (
            ("environment", "prefix_environment_contract_v1"),
            ("grader", "prefix_grader_contract_v1"),
            ("verifier", "prefix_verifier_contract_v1"),
            ("isolation", "prefix_isolation_contract_v1"),
        ):
            common: dict[str, object] = {
                "record_kind": record_kind,
                "schema_version": "1",
                "task_id": task_id,
                "benchmark": (
                    environment_benchmark
                    if kind == "environment" and task_id == "task-1"
                    else "swe"
                ),
                "build_id": (
                    {
                        "environment": "synthetic-environment-v1",
                        "grader": "synthetic-grader-v1",
                        "verifier": "synthetic-verifier-v1",
                        "isolation": "fixture-build",
                    }[kind]
                    if executable_sources
                    else "fixture-build"
                ),
                "source_revision_refs": [
                    ref_value(
                        environment_revision_ref
                        if kind == "environment"
                        else loop_revision_ref
                    )
                ],
            }
            if kind == "environment":
                common.update(
                    {
                        "nominal_factory_type": (
                            "pneuma_lab.resampling_null.synthetic_environment."
                            "SyntheticEnvironmentFactory"
                            if executable_sources
                            else "FixtureEnvironmentFactory"
                        ),
                        "snapshot_grammar": (
                            "synthetic-environment-snapshot-v1"
                            if executable_sources
                            else "fixture-snapshot-v1"
                        ),
                        "restore_grammar": (
                            "synthetic-environment-snapshot-v1"
                            if executable_sources
                            else "fixture-restore-v1"
                        ),
                        "raw_evidence_grammar": (
                            "synthetic-environment-evidence-v1"
                            if executable_sources
                            else "fixture-environment-evidence-v1"
                        ),
                        "runtime_id": (
                            "cpython-3.12-local"
                            if executable_sources
                            else "cpython-fixture"
                        ),
                        "container_digest": (
                            "sha256:" + "0" * 64
                            if executable_sources
                            else "sha256:" + "a" * 64
                        ),
                    }
                )
            elif kind in ("grader", "verifier"):
                common.update(
                    {
                        "nominal_type": (
                            "pneuma_lab.resampling_null.synthetic_prefix_loop."
                            + (
                                "SyntheticGradeCodec"
                                if kind == "grader"
                                else "SyntheticVerifierCodec"
                            )
                            if executable_sources
                            else f"Fixture{kind.title()}"
                        ),
                        "raw_evidence_grammar": (
                            {
                                "grader": "synthetic-grade-v1",
                                "verifier": "synthetic-verifier-v1",
                            }[kind]
                            if executable_sources
                            else f"fixture-{kind}-evidence-v1"
                        ),
                        "runtime_id": (
                            "cpython-3.12-local"
                            if executable_sources
                            else "cpython-fixture"
                        ),
                        "container_digest": (
                            "sha256:" + "0" * 64
                            if executable_sources
                            else "sha256:" + "a" * 64
                        ),
                    }
                )
            else:
                common.update(
                    {
                        "distinct_environment_instances": True,
                        "distinct_processes": True,
                        "distinct_roots": True,
                        "no_shared_writable_state": True,
                        "qualification_ref": ref_value(qualification_ref),
                    }
                )
            if (
                task_id == "task-foreign"
                and kind == "environment"
                and foreign_environment_extra
            ):
                common["open"] = True
            contract_refs[kind] = blob(
                f"sources/{task_id}-{kind}.json",
                common,
                role=f"{kind}_contract",
            )
        refs[f"{task_id}_input"] = task_input_ref
        refs[f"{task_id}_program"] = program_ref
        refs.update({f"{task_id}_{kind}": ref for kind, ref in contract_refs.items()})
        task_rows.append(
            {
                "task_id": task_id,
                "prefix_lane_ordinal": 0,
                "lane_ordinals_by_execution_rank": [0, 0, 0, 0],
                "task_input_ref": ref_value(task_input_ref),
                "environment_contract_ref": ref_value(contract_refs["environment"]),
                "grader_contract_ref": ref_value(contract_refs["grader"]),
                "verifier_contract_ref": ref_value(contract_refs["verifier"]),
                "isolation_contract_ref": ref_value(contract_refs["isolation"]),
            }
        )
        registry_tasks.append(
            {
                "task_id": task_id,
                "benchmark": "swe",
                "stratum": "python",
                "lineage": f"repo-{task_id}",
                "groups": [
                    {"kind": "language", "value": "python"},
                    {"kind": "domain", "value": "software"},
                    {"kind": "issue_family", "value": "bug"},
                ],
            }
        )

    plan_ref = blob(
        "sources/provider-plan.json",
        {
            "record_kind": plan_kind,
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
                    "simulator_caps": call_caps,
                    "subject_contract_ref": ref_value(subject_ref),
                    "simulator_contract_ref": (
                        ref_value(simulator_ref) if simulator_present else None
                    ),
                    "tool_parser_contract_ref": ref_value(parser_ref),
                    "meter_contract_ref": ref_value(meter_ref),
                }
            ],
            "task_lanes": task_rows,
        },
        role="provider_lane_plan",
    )
    registry_ref = blob(
        "sources/tasks.json",
        {
            "record_kind": "resampling_task_registry_v1",
            "schema_version": "1",
            "tasks": registry_tasks,
        },
        role="task_registry",
    )
    branch_program_registry_ref = blob(
        "sources/branch-program-registry.json",
        {
            "record_kind": "resampling_branch_program_registry_v1",
            "schema_version": "0.1.0",
            "tasks": [
                {
                    "task_id": task_id,
                    "programs": [
                        {
                            "branch_ordinal": ordinal,
                            "program_ref": ref_value(refs[f"{task_id}_program"]),
                        }
                        for ordinal in range(4)
                    ],
                }
                for task_id in ("task-1", "task-foreign")
            ],
        },
        role="branch_program_registry",
    )

    def scientific(
        relative_path: str,
        record_kind: str,
        payload: dict[str, object],
        *,
        role: str,
    ) -> ArtifactRef:
        record = validate_record(
            {
                "record_kind": record_kind,
                "schema_version": "0.1.0",
                "study_id": "study-1",
                "frozen_created_at": "2026-07-29T12:00:00Z",
                "provenance": {
                    "design_sha256": "a" * 64,
                    "code_sha256": "b" * 64,
                },
                "payload": payload,
            }
        )
        return blob(relative_path, record, role=role)

    arbitrary_ref = ref_value(tokenizer_ref)
    manifest_ref = scientific(
        "study-manifest.json",
        "resampling_study_manifest",
        {
            "task_registry_ref": ref_value(registry_ref),
            "roster_ref": arbitrary_ref,
            "eligibility_manifest_ref": None,
            "roster_ceremony_policy_ref": None,
            "assignment_program_ref": arbitrary_ref,
            "provider_lane_plan_ref": ref_value(plan_ref),
            "branch_program_registry_ref": ref_value(
                branch_program_registry_ref
            ),
            "storage_policy_contract_ref": arbitrary_ref,
            "power_grid_ref": arbitrary_ref,
            "power_screen_topology_ref": arbitrary_ref,
            "tokenizer_ref": ref_value(tokenizer_ref),
            "packet_template_ref": arbitrary_ref,
            "packet_policy_ref": arbitrary_ref,
            "pad_unit_set_ref": arbitrary_ref,
            "source_revision_refs": source_revisions,
            "commitment_scheme": "resampling-null-key-ceremony-v1",
            "roster_local_nonce_commitment_sha256": "a" * 64,
            "schedule_seed_commitment_sha256": "b" * 64,
            "assignment_master_key_commitment_sha256": "c" * 64,
            "required_document_kinds_ref": arbitrary_ref,
        },
        role="study_manifest",
    )
    scheduled_task = registry_tasks[0]
    schedule_ref = scientific(
        "prefix-schedule.json",
        "resampling_prefix_schedule",
        {
            "manifest_ref": ref_value(manifest_ref),
            "power_final_ref": arbitrary_ref,
            "schedule_authority": schedule_authority,
            "selected_tier": (
                None if schedule_authority == "synthetic_validation" else 120
            ),
            "selected_membership_sha256": "d" * 64,
            "schedule_seed": 7,
            "tasks": [
                {
                    "task": {
                        "task_id": scheduled_task["task_id"],
                        "benchmark": scheduled_task["benchmark"],
                        "stratum": scheduled_task["stratum"],
                        "lineage": scheduled_task["lineage"],
                        "sensitivity_groups": scheduled_task["groups"],
                    },
                    "prefix_seed": 11,
                    "slots": [
                        {
                            "slot_id": f"slot-{index}",
                            "seed": 20 + index,
                            "execution_order": index,
                            "hardware_lane": 0,
                        }
                        for index in range(4)
                    ],
                    "provider_lane": scheduled_lane,
                }
            ],
        },
        role="resampling_prefix_schedule",
    )
    refs["plan"] = plan_ref
    return ProviderAuthorityFixture(schedule_ref, refs)
