"""Tiny controller-contract tripwire; execution evidence stays mechanism-led."""

from dataclasses import dataclass, FrozenInstanceError
from enum import Enum
import hashlib
import inspect
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null import (
    ArtifactRef,
    BranchCaps,
    CallSeedReceipt,
    ContextMessage,
    FailureKind,
    GradeReceipt,
    OpaqueSlotIdentity,
    PrefixCaps,
    PrefixExecutionAuthority,
    SimulatorCaps,
    SubjectContext,
    SubjectTurn,
    TaskSchedule,
    ToolBoundary,
    ToolCall,
    derive_call_seed,
    load_prefix_execution_authority,
)
from pneuma_lab.resampling_null.artifacts import (
    RecordValidationError,
    validate_record,
)


def _authority_fixture(
    root: Path,
    *,
    plan_kind: str = "provider_lane_plan_v2",
    subject_extra: bool = False,
    environment_benchmark: str = "swe",
) -> tuple[ArtifactRef, dict[str, ArtifactRef]]:
    root.mkdir()

    def blob(relative_path: str, value: object, *, role: str) -> ArtifactRef:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            value
            if isinstance(value, bytes)
            else canonical_json_bytes(value, indent=None)
        )
        path.write_bytes(payload)
        return ArtifactRef(
            role=role,
            relative_path=relative_path,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
            media_type=(
                "application/json"
                if not isinstance(value, bytes)
                else "text/plain"
            ),
        )

    revision_ref = blob("sources/revision.txt", b"revision", role="source_revision")
    tokenizer_ref = blob(
        "sources/tokenizer.json",
        {"tokenizer": "fixture-v1"},
        role="tokenizer",
    )
    prompt_ref = blob(
        "sources/prompt.json",
        {"template": "fixture-v1"},
        role="prompt_template",
    )
    tool_schema_ref = blob(
        "sources/tools.json",
        {"tools": []},
        role="tool_schema",
    )
    clock_ref = blob("sources/clock.txt", b"clock", role="clock_source")
    watchdog_ref = blob(
        "sources/watchdog.txt",
        b"watchdog",
        role="watchdog_source",
    )
    qualification_ref = blob(
        "sources/qualification.json",
        {"qualification": "fixture-v1"},
        role="isolation_qualification",
    )

    refs = {
        "revision": revision_ref,
        "tokenizer": tokenizer_ref,
        "prompt": prompt_ref,
        "tool_schema": tool_schema_ref,
        "clock": clock_ref,
        "watchdog": watchdog_ref,
        "qualification": qualification_ref,
    }

    def ref_value(ref: ArtifactRef) -> dict[str, object]:
        return {
            "role": ref.role,
            "relative_path": ref.relative_path,
            "sha256": ref.sha256,
            "byte_count": ref.byte_count,
            "media_type": ref.media_type,
        }

    source_revisions = [ref_value(revision_ref)]
    call_caps = {
        "aggregate_generated_tokens": 40,
        "aggregate_model_calls": 4,
        "per_call_generated_tokens": 12,
        "per_call_turns": 1,
    }
    subject: dict[str, object] = {
        "record_kind": "prefix_subject_contract_v1",
        "schema_version": "1",
        "model_id": "fixture-subject",
        "tokenizer_ref": ref_value(tokenizer_ref),
        "prompt_template_ref": ref_value(prompt_ref),
        "tool_schema_ref": ref_value(tool_schema_ref),
        "request_grammar": "fixture-request-v1",
        "response_grammar": "fixture-response-v1",
        "seeded_call_grammar": "call-seed-v1",
        "stateless_client_attestation": "fixture-stateless-v1",
        "aggregate_caps": {
            "generated_tokens": 40,
            "model_calls": 4,
            "turns": 4,
        },
        "per_call_caps": {
            "generated_tokens": 12,
            "turns": 1,
        },
        "nominal_type": "FixtureSubject",
        "build_id": "fixture-build",
        "source_revision_refs": source_revisions,
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
            "nominal_type": "FixtureSimulator",
        },
        role="simulator_contract",
    )
    parser_ref = blob(
        "sources/parser.json",
        {
            "record_kind": "prefix_tool_parser_contract_v1",
            "schema_version": "1",
            "nominal_type": "FixtureParser",
            "build_id": "fixture-build",
            "response_grammar": "fixture-response-v1",
            "tool_schema_ref": ref_value(tool_schema_ref),
            "source_revision_refs": source_revisions,
        },
        role="tool_parser_contract",
    )
    meter_ref = blob(
        "sources/meter.json",
        {
            "record_kind": "prefix_meter_contract_v1",
            "schema_version": "1",
            "nominal_type": "FixtureMeter",
            "build_id": "fixture-build",
            "clock_source_ref": ref_value(clock_ref),
            "watchdog_source_ref": ref_value(watchdog_ref),
            "cost_units": {
                "currency": "usd_micros",
                "generated_tokens": "tokens",
                "model_calls": "calls",
                "wall_clock": "milliseconds",
            },
            "provider_event_grammar": "fixture-provider-event-v1",
            "settlement_grammar": "fixture-settlement-v1",
            "zero_cost_synthetic_closure": True,
            "source_revision_refs": source_revisions,
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
    for task_id, requires_simulator in (
        ("task-1", True),
        ("task-foreign", False),
    ):
        task_input_ref = blob(
            f"sources/{task_id}-input.json",
            {
                "record_kind": "prefix_task_input_v1",
                "schema_version": "1",
                "task_id": task_id,
                "benchmark": "swe",
                "requires_user_simulator": requires_simulator,
                "canonical_task_payload": {"instruction": task_id},
            },
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
                "build_id": "fixture-build",
                "source_revision_refs": source_revisions,
            }
            if kind == "environment":
                common.update(
                    {
                        "nominal_factory_type": "FixtureEnvironmentFactory",
                        "snapshot_grammar": "fixture-snapshot-v1",
                        "restore_grammar": "fixture-restore-v1",
                        "raw_evidence_grammar": "fixture-environment-evidence-v1",
                        "runtime_id": "cpython-fixture",
                        "container_digest": "sha256:" + "a" * 64,
                    }
                )
            elif kind in ("grader", "verifier"):
                common.update(
                    {
                        "nominal_type": f"Fixture{kind.title()}",
                        "raw_evidence_grammar": f"fixture-{kind}-evidence-v1",
                        "runtime_id": "cpython-fixture",
                        "container_digest": "sha256:" + "a" * 64,
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
            contract_refs[kind] = blob(
                f"sources/{task_id}-{kind}.json",
                common,
                role=f"{kind}_contract",
            )
        refs[f"{task_id}_input"] = task_input_ref
        refs.update(
            {
                f"{task_id}_{kind}": ref
                for kind, ref in contract_refs.items()
            }
        )
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
                    "simulator_contract_ref": ref_value(simulator_ref),
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
            "schedule_authority": "synthetic_validation",
            "selected_tier": None,
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
                    "provider_lane": "lane-0",
                }
            ],
        },
        role="resampling_prefix_schedule",
    )
    refs["plan"] = plan_ref
    return schedule_ref, refs


def test_t5_s02a_loads_frozen_schedule_ancestry_authority(tmp_path: Path) -> None:
    schedule_ref, refs = _authority_fixture(tmp_path / "run")
    authority = load_prefix_execution_authority(
        run_root=tmp_path / "run",
        schedule_ref=schedule_ref,
        task_id="task-1",
    )

    assert type(authority) is PrefixExecutionAuthority
    assert type(authority.task_schedule) is TaskSchedule
    assert authority.task_schedule.prefix_seed == 11
    assert authority.task_schedule.provider_lane == "lane-0"
    assert authority.prefix_caps == PrefixCaps(40, 4, 4, 1_000)
    assert authority.branch_caps == BranchCaps(20, 2, 4, 500, True)
    assert authority.simulator_caps == SimulatorCaps(40, 4, 12, 1)
    assert authority.task_input_ref == refs["task-1_input"]
    assert authority.environment_contract_ref == refs["task-1_environment"]
    assert authority.grader_contract_ref == refs["task-1_grader"]
    assert authority.verifier_contract_ref == refs["task-1_verifier"]
    assert authority.isolation_contract_ref == refs["task-1_isolation"]
    assert authority.subject_contract_ref == refs["subject"]
    assert authority.simulator_contract_ref == refs["simulator"]
    assert authority.tool_parser_contract_ref == refs["parser"]
    assert authority.meter_contract_ref == refs["meter"]
    with pytest.raises(FrozenInstanceError):
        authority.prefix_caps = PrefixCaps(0, 0, 0, 0)  # type: ignore[misc]

    parameters = inspect.signature(load_prefix_execution_authority).parameters
    assert tuple(parameters) == ("run_root", "schedule_ref", "task_id")
    for forbidden in ("task", "caps", "factory", "task_input_ref"):
        assert forbidden not in parameters
    with pytest.raises(RecordValidationError, match="selected"):
        load_prefix_execution_authority(
            run_root=tmp_path / "run",
            schedule_ref=schedule_ref,
            task_id="task-foreign",
        )


@pytest.mark.parametrize(
    ("fixture_kwargs", "message"),
    [
        ({"plan_kind": "provider_lane_plan_v1"}, "identity"),
        ({"subject_extra": True}, "shape"),
        ({"environment_benchmark": "tau"}, "benchmark"),
    ],
)
def test_t5_s02a_rejects_v1_open_and_mismatched_authority(
    tmp_path: Path,
    fixture_kwargs: dict[str, object],
    message: str,
) -> None:
    schedule_ref, _refs = _authority_fixture(
        tmp_path / "run",
        **fixture_kwargs,  # type: ignore[arg-type]
    )
    with pytest.raises(RecordValidationError, match=message):
        load_prefix_execution_authority(
            run_root=tmp_path / "run",
            schedule_ref=schedule_ref,
            task_id="task-1",
        )


def test_t5_s02a_rejects_tampered_plan_or_nested_contract(tmp_path: Path) -> None:
    for target in ("plan", "subject"):
        root = tmp_path / target
        schedule_ref, refs = _authority_fixture(root)
        path = root / refs[target].relative_path
        path.write_bytes(path.read_bytes() + b" ")
        with pytest.raises(RecordValidationError, match="bytes mismatch"):
            load_prefix_execution_authority(
                run_root=root,
                schedule_ref=schedule_ref,
                task_id="task-1",
            )


def test_t5_s01_call_seed_and_frozen_boundary_contract() -> None:
    assert (
        derive_call_seed(42, "primary_subject", 0),
        derive_call_seed(42, "primary_subject", 1),
        derive_call_seed(42, "user_simulator", 0),
        derive_call_seed(42, "user_simulator", 1),
    ) == (
        5596737105796749176,
        5168650295223317663,
        12950473227392358843,
        174950558451330531,
    )
    receipt = CallSeedReceipt("primary_subject", 0, 5596737105796749176)
    with pytest.raises(FrozenInstanceError):
        receipt.seed = 0  # type: ignore[misc]
    with pytest.raises(ValueError, match="smaller than"):
        CallSeedReceipt("primary_subject", 2**64, 0)
    for invalid_integer in (True, -1, 2**64):
        with pytest.raises((TypeError, ValueError)):
            derive_call_seed(invalid_integer, "primary_subject", 0)
        with pytest.raises((TypeError, ValueError)):
            derive_call_seed(0, "primary_subject", invalid_integer)
    with pytest.raises(ValueError, match="registered"):
        derive_call_seed(0, "assistant", 0)  # type: ignore[arg-type]

    PrefixCaps(0, 0, 0, 0)
    with pytest.raises(TypeError, match="exact int"):
        PrefixCaps(True, 0, 0, 0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="pending prefix"):
        BranchCaps(1, 1, 1, 1, False)  # type: ignore[arg-type]

    assert {kind.name for kind in FailureKind} == {
        "NONE",
        "MODEL",
        "MALFORMED_ACTION",
        "TOKEN_CAP",
        "TOOL_CAP",
        "TIMEOUT",
        "INFRASTRUCTURE",
    }
    for mutated, verifier_eligible, failure_kind in (
        (True, False, FailureKind.INFRASTRUCTURE),
        (False, True, FailureKind.INFRASTRUCTURE),
        (False, False, FailureKind.NONE),
    ):
        with pytest.raises(ValueError, match="incomplete boundary"):
            ToolBoundary(
                1,
                False,
                mutated,
                verifier_eligible,
                failure_kind,
            )

    context = SubjectContext((ContextMessage("user", "visible"),), None)
    assert context.private_guidance is None
    with pytest.raises(TypeError, match="tuple"):
        SubjectContext([ContextMessage("user", "visible")], None)  # type: ignore[arg-type]
    assert ToolCall("call-1", "read", '{"path":"x"}\n').name == "read"
    for arguments in (
        '{ "path": "x" }',
        '{"duplicate":1,"duplicate":2}\n',
        '{"constant":NaN}\n',
        "[]\n",
        '{"path":"x"}',
    ):
        with pytest.raises(ValueError):
            ToolCall("call-2", "read", arguments)

    turn = SubjectTurn("", (ToolCall("call-3", "read", "{}\n"),), 0, None)
    assert turn.finish_reason is None
    with pytest.raises(TypeError, match="tuple"):
        SubjectTurn("", [], 0, None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-empty"):
        SubjectTurn("", (), 0, "")

    artifact_ref = ArtifactRef(
        "grade",
        "grades/task.json",
        "0" * 64,
        1,
        "application/json",
    )
    assert GradeReceipt(1, 0.5, False, artifact_ref).partial_reward == 0.5
    with pytest.raises(ValueError, match="requires success"):
        GradeReceipt(1, 0.0, True, artifact_ref)
    for partial_reward in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="finite"):
            GradeReceipt(0, partial_reward, False, artifact_ref)

    identity = OpaqueSlotIdentity("slot-1", "a" * 64, 2**64 - 1, 0, 0)
    assert identity.seed == 2**64 - 1
    with pytest.raises(ValueError, match="lowercase hexadecimal"):
        OpaqueSlotIdentity("slot-1", "A" * 64, 0, 0, 0)


def test_t5_s01_review_rejects_foreign_role_values_at_public_boundary() -> None:
    class ForeignRole(str, Enum):
        PRIMARY_SUBJECT = "primary_subject"

    class EqualityOverloadedRole:
        def __eq__(self, other: object) -> bool:
            return other == "primary_subject"

    for foreign_role in (ForeignRole.PRIMARY_SUBJECT, EqualityOverloadedRole()):
        with pytest.raises(TypeError, match="subject_role must be exact str"):
            derive_call_seed(0, foreign_role, 0)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="subject_role must be exact str"):
            CallSeedReceipt(foreign_role, 0, 0)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="registered"):
        CallSeedReceipt("assistant", 0, 0)  # type: ignore[arg-type]


def test_t5_s01_review_requires_exact_tuple_and_record_types() -> None:
    class ForeignTuple(tuple[object, ...]):
        pass

    @dataclass(frozen=True, slots=True)
    class ExtendedContextMessage(ContextMessage):
        hidden_state: str

    @dataclass(frozen=True, slots=True)
    class ExtendedToolCall(ToolCall):
        hidden_state: str

    with pytest.raises(TypeError, match="exact tuple"):
        SubjectContext(ForeignTuple((ContextMessage("user", "visible"),)), None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact ContextMessage"):
        SubjectContext(
            (ExtendedContextMessage("user", "visible", "hidden"),),
            None,
        )
    with pytest.raises(TypeError, match="exact tuple"):
        SubjectTurn("", ForeignTuple(()), 0, None)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="exact ToolCall"):
        SubjectTurn(
            "",
            (ExtendedToolCall("call-4", "read", "{}\n", "hidden"),),
            0,
            None,
        )


def test_t5_s01_review_preserves_scalar_error_taxonomy() -> None:
    for field, invocation in (
        ("slot_seed", lambda: derive_call_seed(True, "primary_subject", 0)),
        ("call_index", lambda: derive_call_seed(0, "primary_subject", True)),
    ):
        with pytest.raises(TypeError, match=field):
            invocation()
    for invocation in (
        lambda: derive_call_seed(-1, "primary_subject", 0),
        lambda: derive_call_seed(0, "primary_subject", 2**64),
    ):
        with pytest.raises(ValueError):
            invocation()
    with pytest.raises(TypeError, match="pending_prefix"):
        BranchCaps(0, 0, 0, 0, 1)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="success"):
        GradeReceipt(
            True,  # type: ignore[arg-type]
            0.0,
            False,
            ArtifactRef(
                "grade",
                "grades/task.json",
                "0" * 64,
                1,
                "application/json",
            ),
        )
