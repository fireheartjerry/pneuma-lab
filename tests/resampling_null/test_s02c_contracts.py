from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.prefix_contracts import (
    AUTHORITY_ASSET_ROLE_MEDIA,
    CONTROLLER_ROLE_MEDIA,
    REF_LOAD_CLASS_BY_ROLE,
    EnvironmentProcessIdentity,
    InitialRestoreQualificationReceipt,
    ImplementationDescriptor,
    RawProviderCompletionKind,
    RawProviderObservation,
    SnapshotRestoreReceipt,
    StableSourceProvenance,
    SyntheticClockRead,
    SyntheticFailureInjection,
    SyntheticGradeResult,
    SyntheticPrefixProgram,
    SyntheticProviderTranscriptRow,
    SyntheticToolObservation,
    SyntheticVerifierResult,
    load_prefix_candidate_receipt,
    load_initial_restore_qualification_receipt,
    load_snapshot_restore_receipt,
    load_synthetic_prefix_program,
    prefix_candidate_receipt_bytes,
    synthetic_prefix_program_bytes,
    initial_restore_qualification_receipt_bytes,
    snapshot_restore_receipt_bytes,
    validate_prefix_candidate_ref,
)
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    FrozenVerifierReceipt,
    GradeReceipt,
    FailureKind,
    PrefixCaps,
    ResourceCounters,
    SubjectTurn,
    ToolCall,
    TriggerReason,
)


SHA = "a" * 64


def _ref(role: str, *, media_type: str = "application/json") -> ArtifactRef:
    return ArtifactRef(
        role,
        f"sources/{role}.json",
        SHA,
        1,
        media_type,
    )


def _descriptor() -> ImplementationDescriptor:
    return ImplementationDescriptor(
        purpose="subject",
        nominal_type="pneuma_lab.synthetic.Subject",
        build_id="synthetic-v1",
        request_grammar="synthetic-request-v1",
        response_grammar="synthetic-response-v1",
        snapshot_grammar=None,
        restore_grammar=None,
        evidence_grammar=None,
        runtime_id=None,
        container_digest=None,
        implementation_source_ref=_ref(
            "source_revision",
            media_type="application/octet-stream",
        ),
    )


def _program() -> SyntheticPrefixProgram:
    turn = SubjectTurn(
        text="done",
        tool_calls=(ToolCall("call-1", "read", "{}\n"),),
        generated_tokens=1,
        finish_reason="stop",
    )
    row = SyntheticProviderTranscriptRow(
        subject_role="primary_subject",
        call_index=0,
        seed=7,
        model_contract_sha256=SHA,
        expected_request_ref=_ref("synthetic_request"),
        expected_request_sha256=SHA,
        expected_input_token_ids=(1, 2),
        response_ref=_ref("synthetic_response"),
        typed_turn=turn,
        reported_output_token_ids=(3,),
        reported_generated_tokens=1,
        provider_event_ref=_ref("synthetic_provider_event"),
        completion_kind=RawProviderCompletionKind.COMPLETED,
    )
    return SyntheticPrefixProgram(
        record_kind="synthetic_prefix_program_v1",
        schema_version="1",
        task_id="task-1",
        expected_trigger_reason=TriggerReason.FIRST_ELIGIBLE_MUTATION,
        tool_schema_ref=_ref("tool_schema"),
        provider_transcript=(row,),
        tool_observations=(
            SyntheticToolObservation(
                call_id="call-1",
                result_ref=_ref("synthetic_tool_result"),
                mutation_committed=True,
                verifier_eligible=True,
                episode_terminal=False,
                failure_kind=FailureKind.NONE,
            ),
        ),
        grade_result=SyntheticGradeResult(
            evidence_ref=_ref("synthetic_grade_result"),
            success=1,
            partial_reward=1.0,
            infrastructure_failure=False,
        ),
        verifier_result=SyntheticVerifierResult(
            evidence_ref=_ref("synthetic_verifier_result"),
            finding_count=0,
        ),
        failure_injection=SyntheticFailureInjection(
            stage="none",
            subject_role=None,
            call_index=None,
            tool_call_id=None,
        ),
        clock_trace=(
            SyntheticClockRead("prefix_epoch", 1),
            SyntheticClockRead("provider_0_complete", 2),
        ),
    )


def test_s02c_contracts_are_exact_frozen_and_canonical() -> None:
    descriptor = _descriptor()
    with pytest.raises(FrozenInstanceError):
        descriptor.build_id = "changed"  # type: ignore[misc]
    with pytest.raises((TypeError, ValueError)):
        replace(descriptor, implementation_source_ref=_ref("wrong"))

    identity = EnvironmentProcessIdentity(0, "instance-0", 1, 2, 3)
    with pytest.raises((TypeError, ValueError)):
        replace(identity, writable_root_relative_path="../escape")

    program = _program()
    payload = synthetic_prefix_program_bytes(program)
    assert load_synthetic_prefix_program(payload) == program
    for malformed in (
        b"\xef\xbb\xbf" + payload,
        payload[:-1] + b', "open": true}',
        b'{"record_kind":"synthetic_prefix_program_v1","record_kind":"x"}',
        b'{"value":NaN}',
    ):
        with pytest.raises((TypeError, ValueError)):
            load_synthetic_prefix_program(malformed)
    with pytest.raises(TypeError):
        replace(program, provider_transcript=list(program.provider_transcript))


def test_raw_provider_observation_is_closed_and_role_bound() -> None:
    observation = RawProviderObservation(
        subject_role="primary_subject",
        call_index=0,
        seed=1,
        model_contract_sha256=SHA,
        response_bytes=b"{}",
        typed_turn=SubjectTurn("ok", (), 1, "stop"),
        reported_output_token_ids=(3,),
        reported_generated_tokens=1,
        provider_event_bytes=b"{}",
        completion_kind=RawProviderCompletionKind.COMPLETED,
    )
    with pytest.raises((TypeError, ValueError)):
        replace(observation, reported_output_token_ids=None)
    with pytest.raises(TypeError):
        replace(observation, reported_output_token_ids=[3])


def test_role_load_registries_are_closed_disjoint_and_cover_s02c() -> None:
    classes = {
        role: load_class
        for role, (load_class, _authority) in REF_LOAD_CLASS_BY_ROLE.items()
    }
    assert classes["prefix_candidate_receipt"] == "controller_artifact"
    assert classes["synthetic_execution_program"] == "authority_asset"
    assert classes["resampling_prefix_schedule"] == "scientific_parent"
    assert not (set(CONTROLLER_ROLE_MEDIA) & set(AUTHORITY_ASSET_ROLE_MEDIA))
    assert set(classes) == (
        set(CONTROLLER_ROLE_MEDIA)
        | set(AUTHORITY_ASSET_ROLE_MEDIA)
        | {"resampling_prefix_schedule", "study_manifest"}
    )
    for registry in (
        CONTROLLER_ROLE_MEDIA,
        AUTHORITY_ASSET_ROLE_MEDIA,
        REF_LOAD_CLASS_BY_ROLE,
    ):
        with pytest.raises(TypeError):
            registry["forged"] = "application/json"  # type: ignore[index]


def test_stable_source_provenance_rechecks_held_nofollow_regular_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.py"
    payload = b"VALUE = 1\n"
    source.write_bytes(payload)
    ref = ArtifactRef(
        "source_revision",
        "source.py",
        hashlib.sha256(payload).hexdigest(),
        len(payload),
        "application/octet-stream",
    )
    with StableSourceProvenance(tmp_path, Path("source.py"), ref) as provenance:
        assert provenance.payload == payload
        assert provenance.verify_again() == payload
        source.write_bytes(b"VALUE = 2\n")
        with pytest.raises(ValueError):
            provenance.verify_again()

    source.unlink()
    target = tmp_path / "target.py"
    target.write_bytes(payload)
    source.symlink_to(target)
    with pytest.raises(ValueError):
        StableSourceProvenance(tmp_path, Path("source.py"), ref)


def test_candidate_wrapper_uses_exact_role_media_and_runtime_decoder() -> None:
    from pneuma_lab.resampling_null.evidence import (
        FrozenPrefixReceipt,
        composite_snapshot_bytes,
    )
    from tests.resampling_null.test_evidence_primitives import _ref as controller_ref
    from tests.resampling_null.test_evidence_primitives import _snapshot

    snapshot = _snapshot()
    snapshot_payload = composite_snapshot_bytes(snapshot)
    snapshot_ref = ArtifactRef(
        "composite_snapshot",
        "controller-artifacts/composite_snapshot/"
        + hashlib.sha256(snapshot_payload).hexdigest(),
        hashlib.sha256(snapshot_payload).hexdigest(),
        len(snapshot_payload),
        "application/json",
    )
    receipt = FrozenPrefixReceipt(
        task_id="task-1",
        schedule_sha256=snapshot.schedule_ref.sha256,
        prefix_caps=PrefixCaps(10, 3, 4, 100),
        snapshot_ref=snapshot_ref,
        visible_context_ref=snapshot.visible_context_ref,
        visible_sha256=snapshot.visible_sha256,
        token_ids_ref=snapshot.token_ids_ref,
        token_ids_sha256=snapshot.token_ids_sha256,
        branch_pending_calls=snapshot.branch_pending_calls,
        terminal_unexecuted_remainder=(),
        trigger_reason=TriggerReason.FIRST_ELIGIBLE_MUTATION,
        terminal_failure_kind=FailureKind.NONE,
        y0_grade=GradeReceipt(0, 0.0, False, controller_ref("grade_evidence")),
        grade_execution_receipt_ref=controller_ref("grade_evidence_receipt"),
        verifier_receipt=FrozenVerifierReceipt(
            "task-1",
            snapshot.schedule_ref.sha256,
            snapshot_ref,
            controller_ref("verifier_evidence"),
            0,
        ),
        verifier_execution_receipt_ref=controller_ref("verifier_evidence_receipt"),
        counters=ResourceCounters(3, 1, 1, 20),
        simulator_counters=ResourceCounters(1, 1, 0, 20),
        call_seeds=(),
        provider_attempts_ref=snapshot.provider_attempts_ref,
        boundary_ledger_ref=snapshot.boundary_ledger_ref,
        provider_cost_ref=controller_ref("provider_cost_closure"),
    )
    payload = prefix_candidate_receipt_bytes(receipt)
    assert load_prefix_candidate_receipt(payload) == receipt
    digest = hashlib.sha256(payload).hexdigest()
    ref = ArtifactRef(
        "prefix_candidate_receipt",
        f"controller-artifacts/prefix_candidate_receipt/{digest}",
        digest,
        len(payload),
        "application/json",
    )
    assert validate_prefix_candidate_ref(ref) == ref
    with pytest.raises(ValueError):
        validate_prefix_candidate_ref(
            replace(ref, media_type="application/octet-stream")
        )


def test_restore_receipt_contracts_are_exact_canonical_and_snapshot_bound() -> None:
    identity = EnvironmentProcessIdentity(0, "instance-0", 1, 2, 3)
    calls = (ToolCall("call-1", "read", "{}\n"),)
    initial = InitialRestoreQualificationReceipt(
        schedule_ref=_ref("resampling_prefix_schedule"),
        task_ref=ArtifactRef(
            "selected_task",
            "controller-artifacts/selected_task/" + SHA,
            SHA,
            1,
            "application/json",
        ),
        task_input_ref=_ref("task_input"),
        environment_contract_ref=_ref("environment_contract"),
        isolation_contract_ref=_ref("isolation_contract"),
        initial_environment_snapshot_ref=ArtifactRef(
            "environment_snapshot",
            "controller-artifacts/environment_snapshot/" + SHA,
            SHA,
            1,
            "application/octet-stream",
        ),
        observed_resnapshot_sha256=SHA,
        observed_resnapshot_byte_count=1,
        visible_context_ref=ArtifactRef(
            "visible_context",
            "controller-artifacts/visible_context/" + SHA,
            SHA,
            1,
            "application/json",
        ),
        visible_sha256=SHA,
        token_ids_ref=ArtifactRef(
            "token_ids",
            "controller-artifacts/token_ids/" + SHA,
            SHA,
            1,
            "application/json",
        ),
        token_ids_sha256=SHA,
        branch_pending_calls=calls,
        terminal_unexecuted_remainder=(),
        episode_terminal=False,
        failure_kind=FailureKind.NONE,
        live_identity=identity,
        fresh_restore_identity=EnvironmentProcessIdentity(
            1,
            "instance-1",
            1,
            3,
            4,
        ),
        verified=True,
    )
    assert load_initial_restore_qualification_receipt(
        initial_restore_qualification_receipt_bytes(initial)
    ) == initial
    restore = SnapshotRestoreReceipt(
        purpose="grade",
        schedule_ref=initial.schedule_ref,
        task_ref=initial.task_ref,
        task_input_ref=initial.task_input_ref,
        environment_contract_ref=initial.environment_contract_ref,
        isolation_contract_ref=initial.isolation_contract_ref,
        composite_snapshot_ref=ArtifactRef(
            "composite_snapshot",
            "controller-artifacts/composite_snapshot/" + SHA,
            SHA,
            1,
            "application/json",
        ),
        environment_snapshot_ref=initial.initial_environment_snapshot_ref,
        observed_resnapshot_sha256=SHA,
        observed_resnapshot_byte_count=1,
        branch_pending_calls=calls,
        terminal_unexecuted_remainder=(),
        visible_context_ref=initial.visible_context_ref,
        visible_sha256=SHA,
        token_ids_ref=initial.token_ids_ref,
        token_ids_sha256=SHA,
        episode_terminal=False,
        failure_kind=FailureKind.NONE,
        restored_identity=EnvironmentProcessIdentity(
            2,
            "instance-2",
            1,
            4,
            5,
        ),
        verified=True,
    )
    assert load_snapshot_restore_receipt(
        snapshot_restore_receipt_bytes(restore)
    ) == restore
    with pytest.raises((TypeError, ValueError)):
        replace(restore, purpose="other")


def test_failure_injection_is_exact_and_reachable_by_shape() -> None:
    with pytest.raises(ValueError):
        SyntheticFailureInjection(
            stage="provider_parser",
            subject_role=None,
            call_index=0,
            tool_call_id=None,
        )
    with pytest.raises(ValueError):
        SyntheticFailureInjection(
            stage="tool",
            subject_role="user_simulator",
            call_index=0,
            tool_call_id="call-1",
        )
    with pytest.raises(ValueError):
        load_prefix_candidate_receipt(
            canonical_json_bytes(
                {
                    "record_kind": "frozen_prefix_candidate_v1",
                    "schema_version": "1",
                    "receipt": {},
                    "open": True,
                },
                indent=None,
            )
        )
