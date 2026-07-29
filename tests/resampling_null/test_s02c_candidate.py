from dataclasses import asdict, fields
import inspect
import json
import os
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.controller_artifacts import (
    ControllerArtifactResolver,
    ControllerArtifactStore,
)
from pneuma_lab.resampling_null.evidence import (
    FrozenPrefixReceipt,
    GradeEvidence,
    load_composite_snapshot,
    load_grade_execution_receipt,
    load_verifier_execution_receipt,
)
from pneuma_lab.resampling_null.execution_authority import (
    load_prefix_execution_authority,
)
from pneuma_lab.resampling_null.prefix_contracts import (
    CONTROLLER_ROLE_MEDIA,
    load_initial_restore_qualification_receipt,
    load_prefix_candidate_receipt,
    load_snapshot_restore_receipt,
)
import pneuma_lab.resampling_null.synthetic_prefix_loop as prefix_loop
from pneuma_lab.resampling_null.synthetic_prefix_loop import (
    _controller_nested_refs,
    _fresh_reload_candidate_graph,
    _scientific_y0_grade,
    run_prefix,
)
from pneuma_lab.resampling_null.types import ArtifactRef, FailureKind, TriggerReason
from tests.resampling_null.provider_authority_fixture import (
    ProviderAuthorityFixture,
)


def _resolve(root: Path, ref: ArtifactRef) -> bytes:
    with ControllerArtifactResolver(root) as resolver:
        return resolver.resolve(
            ref,
            expected_role=ref.role,
            expected_media_type=CONTROLLER_ROLE_MEDIA[ref.role],
        )


def _candidate_schedule(root: Path) -> ArtifactRef:
    fixture = ProviderAuthorityFixture.build(
        root,
        executable_sources=True,
        requires_simulator=False,
        simulator_present=False,
    )
    return fixture.schedule_ref


def _all_controller_payloads(root: Path) -> dict[ArtifactRef, bytes]:
    payloads: dict[ArtifactRef, bytes] = {}
    artifact_root = root / "controller-artifacts"
    for role_path in artifact_root.iterdir():
        if not role_path.is_dir():
            continue
        for path in role_path.iterdir():
            payload = path.read_bytes()
            ref = ArtifactRef(
                role_path.name,
                path.relative_to(root).as_posix(),
                path.name,
                len(payload),
                CONTROLLER_ROLE_MEDIA[role_path.name],
            )
            payloads[ref] = payload
    return payloads


def test_t5_s02cd_closes_one_transferred_store_before_fresh_reload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    schedule_ref = _candidate_schedule(root)
    events: list[str] = []
    close_count_after_loop = [0]
    original_close = ControllerArtifactStore.close
    original_resolve = ControllerArtifactResolver.resolve
    original_open = prefix_loop._open_prefix_loop

    def close(self: ControllerArtifactStore) -> None:
        events.append("store-close")
        original_close(self)

    def resolve(
        self: ControllerArtifactResolver,
        ref: ArtifactRef,
        *,
        expected_role: str,
        expected_media_type: str,
    ) -> bytes:
        events.append(f"resolve:{ref.role}")
        assert events.count("store-close") == close_count_after_loop[0] + 1
        return original_resolve(
            self,
            ref,
            expected_role=expected_role,
            expected_media_type=expected_media_type,
        )

    def open_loop(*, run_root: Path, authority):
        opened = original_open(run_root=run_root, authority=authority)
        close_count_after_loop[0] = events.count("store-close")
        return opened

    monkeypatch.setattr(ControllerArtifactStore, "close", close)
    monkeypatch.setattr(ControllerArtifactResolver, "resolve", resolve)
    monkeypatch.setattr(prefix_loop, "_open_prefix_loop", open_loop)

    candidate_ref = run_prefix(
        run_root=root,
        schedule_ref=schedule_ref,
        task_id="task-1",
    )

    assert events.count("store-close") == close_count_after_loop[0] + 1
    final_close = events.index("store-close", close_count_after_loop[0])
    assert all(not event.startswith("resolve:") for event in events[:final_close])
    assert events[final_close + 1].startswith("resolve:")
    assert candidate_ref.role == "prefix_candidate_receipt"


def test_t5_s02cd_public_run_freezes_restores_and_reloads_candidate_graph(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    schedule_ref = _candidate_schedule(root)
    candidate_ref = run_prefix(
        run_root=root,
        schedule_ref=schedule_ref,
        task_id="task-1",
    )

    candidate_payload = _resolve(root, candidate_ref)
    assert set(json.loads(candidate_payload)) == {
        "record_kind",
        "schema_version",
        "receipt",
    }
    receipt = load_prefix_candidate_receipt(candidate_payload)
    assert type(receipt) is FrozenPrefixReceipt
    assert receipt.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY

    snapshot = load_composite_snapshot(_resolve(root, receipt.snapshot_ref))
    initial = load_initial_restore_qualification_receipt(
        _resolve(root, snapshot.initial_restore_qualification_ref)
    )
    assert snapshot.environment_snapshot_ref.role == "environment_snapshot"
    assert snapshot.branch_pending_calls == ()
    assert snapshot.terminal_unexecuted_remainder == ()
    assert snapshot.episode_terminal is True
    assert snapshot.cumulative_mutation is False
    assert snapshot.primary_counters == receipt.counters
    assert snapshot.simulator_counters == receipt.simulator_counters

    grade_execution = load_grade_execution_receipt(
        _resolve(root, receipt.grade_execution_receipt_ref)
    )
    verifier_execution = load_verifier_execution_receipt(
        _resolve(root, receipt.verifier_execution_receipt_ref)
    )
    grade_restore = load_snapshot_restore_receipt(
        _resolve(root, grade_execution.restore_receipt_ref)
    )
    verifier_restore = load_snapshot_restore_receipt(
        _resolve(root, verifier_execution.restore_receipt_ref)
    )
    identities = (
        initial.live_identity,
        initial.fresh_restore_identity,
        grade_restore.restored_identity,
        verifier_restore.restored_identity,
    )
    assert len({identity.child_pid for identity in identities}) == 4
    assert (
        len(
            {
                (
                    identity.writable_root_st_dev,
                    identity.writable_root_st_ino,
                )
                for identity in identities
            }
        )
        == 4
    )
    assert grade_restore.purpose == "grade"
    assert verifier_restore.purpose == "verify"
    assert grade_restore.composite_snapshot_ref == receipt.snapshot_ref
    assert verifier_restore.composite_snapshot_ref == receipt.snapshot_ref
    assert grade_restore.environment_snapshot_ref == snapshot.environment_snapshot_ref
    assert (
        verifier_restore.environment_snapshot_ref == snapshot.environment_snapshot_ref
    )
    assert receipt.y0_grade.artifact_ref == grade_execution.grade_evidence_ref
    assert (
        receipt.verifier_receipt.verifier_artifact_ref
        == verifier_execution.verifier_evidence_ref
    )
    assert not any(
        path.name.startswith("instance-")
        for path in (root / "prefix-environments").iterdir()
    )


def test_t5_s02cd_controller_json_grammar_rejects_open_and_malformed_refs() -> None:
    with pytest.raises(ValueError, match="open or incomplete"):
        _controller_nested_refs(
            "provider_request",
            b'{"context_base64":"","extra":0,"subject_role":"primary_subject"}\n',
        )
    with pytest.raises((TypeError, ValueError), match="provider_request"):
        _controller_nested_refs(
            "provider_request",
            b'{"context_base64":7,"subject_role":false}\n',
        )
    wrong = ArtifactRef(
        "task_input",
        "sources/task.json",
        "a" * 64,
        1,
        "application/json",
    )
    input_ref = ArtifactRef(
        "input_token_ids",
        "controller-artifacts/input_token_ids/" + "b" * 64,
        "b" * 64,
        1,
        "application/json",
    )
    model_ref = ArtifactRef(
        "subject_contract",
        "sources/subject.json",
        "c" * 64,
        1,
        "application/json",
    )
    with pytest.raises((TypeError, ValueError), match="request_ref"):
        _controller_nested_refs(
            "provider_dispatch_intent",
            canonical_json_bytes(
                {
                    "absolute_deadline_ms": 2,
                    "call_index": 0,
                    "input_token_ids_ref": asdict(input_ref),
                    "model_contract_ref": asdict(model_ref),
                    "request_ref": asdict(wrong),
                    "seed": 1,
                    "subject_role": "primary_subject",
                },
                indent=None,
            ),
        )
    with pytest.raises(ValueError, match="open ArtifactRef"):
        _controller_nested_refs(
            "visible_context",
            (
                b'{"hidden":{"byte_count":1,"media_type":"application/json",'
                b'"relative_path":"sources/x","role":"task_input"}}\n'
            ),
        )


def test_t5_s02cd_fresh_reload_rejects_cross_class_hardlink_alias(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    schedule_ref = _candidate_schedule(root)
    candidate_ref = run_prefix(
        run_root=root,
        schedule_ref=schedule_ref,
        task_id="task-1",
    )
    receipt = load_prefix_candidate_receipt(_resolve(root, candidate_ref))
    assert type(receipt) is FrozenPrefixReceipt
    authority = load_prefix_execution_authority(
        run_root=root,
        schedule_ref=schedule_ref,
        task_id="task-1",
    )
    visible_path = root / receipt.visible_context_ref.relative_path
    visible_path.unlink()
    os.link(root / authority.task_input_ref.relative_path, visible_path)

    with pytest.raises(ValueError, match="physical file"):
        _fresh_reload_candidate_graph(
            run_root=root,
            candidate_ref=candidate_ref,
            authority=authority,
            expected_controller_payloads=_all_controller_payloads(root),
            allowed_prior_controller_refs=frozenset(),
        )


def test_t5_s02cd_fresh_reload_requires_retained_bytes_and_reachable_writes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    schedule_ref = _candidate_schedule(root)
    candidate_ref = run_prefix(
        run_root=root,
        schedule_ref=schedule_ref,
        task_id="task-1",
    )
    authority = load_prefix_execution_authority(
        run_root=root,
        schedule_ref=schedule_ref,
        task_id="task-1",
    )
    with pytest.raises(ValueError, match="retained input bytes"):
        expected_payloads = _all_controller_payloads(root)
        expected_payloads[candidate_ref] = b"alternate\n"
        _fresh_reload_candidate_graph(
            run_root=root,
            candidate_ref=candidate_ref,
            authority=authority,
            expected_controller_payloads=expected_payloads,
            allowed_prior_controller_refs=frozenset(),
        )
    orphan_payload = b'{"token_ids":[]}\n'
    orphan_ref = ArtifactRef(
        "token_ids",
        "controller-artifacts/token_ids/" + "f" * 64,
        "f" * 64,
        len(orphan_payload),
        "application/json",
    )
    with pytest.raises(ValueError, match="unreachable writes"):
        expected_payloads = _all_controller_payloads(root)
        expected_payloads[orphan_ref] = orphan_payload
        _fresh_reload_candidate_graph(
            run_root=root,
            candidate_ref=candidate_ref,
            authority=authority,
            expected_controller_payloads=expected_payloads,
            allowed_prior_controller_refs=frozenset(),
        )


def test_t5_s02cd_forces_only_adverse_no_trigger_scientific_y0_to_zero() -> None:
    raw_ref = ArtifactRef(
        "grade_evidence",
        "controller-artifacts/grade_evidence/" + "a" * 64,
        "a" * 64,
        1,
        "application/octet-stream",
    )
    evidence = GradeEvidence(1, 0.75, False, b"x")

    natural = _scientific_y0_grade(
        trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        failure_kind=FailureKind.NONE,
        evidence=evidence,
        evidence_ref=raw_ref,
    )
    adverse = _scientific_y0_grade(
        trigger_reason=TriggerReason.NO_INTERVENTION_OPPORTUNITY,
        failure_kind=FailureKind.TIMEOUT,
        evidence=evidence,
        evidence_ref=raw_ref,
    )

    assert (natural.success, natural.partial_reward) == (1, 0.75)
    assert (adverse.success, adverse.partial_reward) == (0, 0.0)
    assert natural.artifact_ref == adverse.artifact_ref == raw_ref


def test_t5_s02cd_public_entry_has_no_injection_or_publication_seam() -> None:
    signature = inspect.signature(run_prefix)
    assert tuple(signature.parameters) == ("run_root", "schedule_ref", "task_id")
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert signature.return_annotation in (ArtifactRef, "ArtifactRef")
    assert not {
        "out",
        "store",
        "factory",
        "resolver",
        "fixtures",
        "codecs",
        "provider",
        "model",
    } & set(signature.parameters)
    assert tuple(field.name for field in fields(FrozenPrefixReceipt))[-3:] == (
        "provider_attempts_ref",
        "boundary_ledger_ref",
        "provider_cost_ref",
    )
