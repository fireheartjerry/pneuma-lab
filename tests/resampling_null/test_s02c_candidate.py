from dataclasses import asdict, fields, replace
import hashlib
import inspect
import json
import os
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
import pneuma_lab.resampling_null.authority_refs as authority_refs
import pneuma_lab.resampling_null.controller_artifacts as controller_artifacts
from pneuma_lab.resampling_null.authority_refs import AuthorityRefReader
from pneuma_lab.resampling_null.controller_artifacts import (
    ControllerArtifactResolver,
    ControllerArtifactStore,
)
from pneuma_lab.resampling_null.evidence import (
    FrozenPrefixReceipt,
    GradeEvidence,
    SyntheticZeroAttemptCostClosure,
    ToolBoundaryLedger,
    load_controller_provider_cost_closure,
    load_controller_provider_event,
    load_controller_provider_settlement,
    load_composite_snapshot,
    load_grade_execution_receipt,
    load_provider_attempt,
    load_provider_attempt_ledger,
    load_provider_dispatch_intent,
    load_container_attestation,
    load_runtime_attestation,
    load_stateless_attestation,
    load_tool_boundary_ledger,
    load_verifier_execution_receipt,
)
from pneuma_lab.resampling_null.execution_authority import (
    load_prefix_execution_authority,
)
from pneuma_lab.resampling_null.prefix_contracts import (
    AUTHORITY_ASSET_ROLE_MEDIA,
    CONTROLLER_ROLE_MEDIA,
    load_initial_restore_qualification_receipt,
    load_prefix_candidate_receipt,
    load_snapshot_restore_receipt,
    load_synthetic_prefix_program,
)
import pneuma_lab.resampling_null.synthetic_prefix_loop as prefix_loop
import pneuma_lab.resampling_null.prefix_contracts as prefix_contracts
import pneuma_lab.resampling_null.scientific_records as scientific_records
from pneuma_lab.resampling_null.scientific_records import ScientificRefReader
from pneuma_lab.resampling_null.synthetic_prefix_loop import (
    _controller_nested_refs,
    _fresh_reload_candidate_graph,
    _scientific_y0_grade,
    run_prefix,
)
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    FailureKind,
    ToolCall,
    TriggerReason,
)
from tests.resampling_null.provider_authority_fixture import (
    ProviderAuthorityFixture,
)
from tests.resampling_null.test_s02c_prefix_loop import _loop_authority


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


def _zero_attempt_reload_kwargs(
    root: Path,
    *,
    authority,
    candidate_ref: ArtifactRef,
) -> dict[str, object]:
    receipt = load_prefix_candidate_receipt(_resolve(root, candidate_ref))
    assert type(receipt) is FrozenPrefixReceipt
    program_bytes = (root / authority.program_ref.relative_path).read_bytes()
    return {
        "program": load_synthetic_prefix_program(program_bytes),
        "program_bytes": program_bytes,
        "expected_cost_closure": SyntheticZeroAttemptCostClosure(),
        "expected_boundaries": (),
        "expected_provider_attempts_ref": receipt.provider_attempts_ref,
        "expected_boundary_ledger_ref": receipt.boundary_ledger_ref,
        "expected_provider_cost_ref": receipt.provider_cost_ref,
    }


def test_t5_s02cd_closes_one_transferred_store_before_fresh_reload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    schedule_ref = _candidate_schedule(root)
    events: list[str] = []
    close_count_after_loop = [0]
    original_close = ControllerArtifactStore.close
    original_resolve = ControllerArtifactResolver.resolve_bound
    original_open = prefix_loop._open_prefix_loop

    def close(self: ControllerArtifactStore) -> None:
        events.append("store-close")
        original_close(self)

    def resolve_bound(
        self: ControllerArtifactResolver,
        ref: ArtifactRef,
        *,
        expected_role: str,
        expected_media_type: str,
    ):
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
    monkeypatch.setattr(
        ControllerArtifactResolver,
        "resolve_bound",
        resolve_bound,
    )
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


def test_t5_s02cd_attestations_reconcile_exact_program_and_authority(
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
    receipt = load_prefix_candidate_receipt(_resolve(root, candidate_ref))
    assert type(receipt) is FrozenPrefixReceipt
    snapshot = load_composite_snapshot(_resolve(root, receipt.snapshot_ref))
    program_bytes = (root / authority.program_ref.relative_path).read_bytes()
    program = load_synthetic_prefix_program(program_bytes)
    subject = load_stateless_attestation(
        _resolve(root, snapshot.subject_stateless_attestation_ref),
        expected_role="primary_subject",
    )
    runtime = load_runtime_attestation(_resolve(root, snapshot.runtime_ref))
    container = load_container_attestation(_resolve(root, snapshot.container_ref))

    prefix_loop._reconcile_reloaded_attestations(
        authority=authority,
        program=program,
        program_bytes=program_bytes,
        subject=subject,
        simulator=None,
        runtime=runtime,
        container=container,
    )
    with pytest.raises(ValueError, match="subject attestation"):
        prefix_loop._reconcile_reloaded_attestations(
            authority=authority,
            program=program,
            program_bytes=program_bytes,
            subject=replace(subject, program_sha256="f" * 64),
            simulator=None,
            runtime=runtime,
            container=container,
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


@pytest.mark.parametrize(
    ("role", "value"),
    [
        (
            "provider_attempt_ledger",
            {
                "attempt_refs": [False],
                "attempts": [],
                "intent_refs": [],
                "intents": [],
            },
        ),
        (
            "provider_attempt_ledger",
            {
                "attempt_refs": [],
                "attempts": [],
                "intent_refs": ["not-a-ref"],
                "intents": [],
            },
        ),
        (
            "provider_event",
            {
                "call_index": 0,
                "completion_kind": "completed",
                "cost_microunits": 9,
                "dispatch_intent_sha256": "a" * 64,
                "model_contract_sha256": "b" * 64,
                "observed_at_ms": 1,
                "response_sha256": False,
                "schema_version": "1",
                "seed": 1,
                "subject_role": "primary_subject",
            },
        ),
        (
            "provider_settlement",
            {
                "attempt_sha256": False,
                "call_index": 0,
                "cost_microunits": 0,
                "currency": "synthetic_microunit",
                "dispatch_intent_sha256": 7,
                "final": True,
                "provider_event_sha256": [],
                "schema_version": "1",
                "seed": 1,
                "subject_role": "primary_subject",
            },
        ),
        (
            "subject_stateless_attestation",
            {
                "authority_ref": {
                    "byte_count": 1,
                    "media_type": "application/json",
                    "relative_path": "sources/subject.json",
                    "role": "subject_contract",
                    "sha256": "c" * 64,
                },
                "program_sha256": False,
                "record_kind": 3,
                "schema_version": "1",
                "stateless": False,
            },
        ),
    ],
)
def test_t5_s02cd_controller_decoders_reject_wrong_typed_semantics(
    role: str,
    value: object,
) -> None:
    with pytest.raises((TypeError, ValueError)):
        _controller_nested_refs(
            role,
            canonical_json_bytes(value, indent=None),
        )


def test_t5_s02cd_authority_leaf_decoders_reject_opaque_json_shapes() -> None:
    with pytest.raises((TypeError, ValueError)):
        prefix_contracts.load_synthetic_request_payload(
            b'{"context_base64":"not-base64!","subject_role":"primary_subject"}\n'
        )
    with pytest.raises((TypeError, ValueError)):
        prefix_contracts.load_synthetic_request_payload(
            b'{"context_base64":"","subject_role":false}\n'
        )
    with pytest.raises((TypeError, ValueError)):
        prefix_contracts.load_synthetic_tool_result_payload(b'{"call_id":false}\n')


@pytest.mark.parametrize(
    ("role", "record_kind", "payload_field", "payload_value"),
    [
        ("tokenizer", "synthetic_tokenizer_asset_v1", "tokenizer_id", "byte-v1"),
        (
            "prompt_template",
            "synthetic_prompt_template_asset_v1",
            "template_id",
            "prompt-v1",
        ),
        (
            "tool_schema",
            "synthetic_tool_schema_asset_v1",
            "tools",
            [{"name": "read"}],
        ),
        ("clock_source", "synthetic_clock_asset_v1", "clock_id", "clock-v1"),
        (
            "watchdog_source",
            "synthetic_watchdog_asset_v1",
            "watchdog_id",
            "watchdog-v1",
        ),
        (
            "isolation_qualification",
            "synthetic_isolation_qualification_asset_v1",
            "qualification_id",
            "isolation-v1",
        ),
        (
            "deep_authority_asset",
            "synthetic_deep_authority_leaf_v1",
            "value_id",
            "leaf-v1",
        ),
    ],
)
def test_t5_s02cd_promoted_authority_decoders_are_closed_and_typed(
    role: str,
    record_kind: str,
    payload_field: str,
    payload_value: object,
) -> None:
    valid = {
        "record_kind": record_kind,
        "schema_version": "1",
        payload_field: payload_value,
    }
    decoded = prefix_contracts.load_promoted_authority_asset(
        role=role,
        payload=canonical_json_bytes(valid, indent=None),
    )
    assert decoded.role == role
    for bad in (
        {**valid, "extra": True},
        {**valid, "record_kind": "wrong"},
        {**valid, payload_field: False},
    ):
        with pytest.raises((TypeError, ValueError)):
            prefix_contracts.load_promoted_authority_asset(
                role=role,
                payload=canonical_json_bytes(bad, indent=None),
            )


def test_t5_s02cd_authority_decoder_registry_has_no_fallback() -> None:
    assert set(prefix_loop.AUTHORITY_ASSET_DECODER_BY_ROLE) == set(
        AUTHORITY_ASSET_ROLE_MEDIA
    )
    assert len(AUTHORITY_ASSET_ROLE_MEDIA) == 26


def test_t5_s02cd_deep_authority_link_is_closed_and_same_role() -> None:
    nested = ArtifactRef(
        "deep_authority_asset",
        "sources/deep-leaf.json",
        "a" * 64,
        1,
        "application/json",
    )
    link = {
        "record_kind": "synthetic_deep_authority_link_v1",
        "schema_version": "1",
        "nested_ref": asdict(nested),
    }
    decoded = prefix_contracts.load_promoted_authority_asset(
        role="deep_authority_asset",
        payload=canonical_json_bytes(link, indent=None),
    )
    assert decoded.nested_refs == (nested,)
    with pytest.raises(ValueError, match="deep_authority_asset"):
        prefix_contracts.load_promoted_authority_asset(
            role="deep_authority_asset",
            payload=canonical_json_bytes(
                {
                    **link,
                    "nested_ref": {
                        **asdict(nested),
                        "role": "tool_schema",
                    },
                },
                indent=None,
            ),
        )


def test_t5_s02cd_authority_read_binds_bytes_and_inode_on_same_fd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    source = root / "sources" / "asset.json"
    source.parent.mkdir(parents=True)
    payload = b'{"record_kind":"x"}\n'
    source.write_bytes(payload)
    ref = ArtifactRef(
        "deep_authority_asset",
        "sources/asset.json",
        hashlib.sha256(payload).hexdigest(),
        len(payload),
        "application/json",
    )
    replacement = root / "replacement.json"
    replacement.write_bytes(payload)
    original_stat = authority_refs.os.stat
    swapped = [False]

    def stat(path, *args, **kwargs):
        if path == "asset.json" and kwargs.get("dir_fd") is not None and not swapped[0]:
            swapped[0] = True
            os.replace(replacement, source)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(authority_refs.os, "stat", stat)
    with AuthorityRefReader(root) as reader:
        with pytest.raises(ValueError, match="identity changed"):
            reader.read_bound(ref)


def test_t5_s02cd_authority_reader_aggregates_traversal_and_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    (root / "sources").mkdir(parents=True)
    reader = AuthorityRefReader(root)
    original_close = authority_refs.os.close

    with pytest.raises(BaseExceptionGroup) as captured:
        with reader:
            root_descriptor = reader._root_descriptor

            def close(descriptor: int) -> None:
                if descriptor == root_descriptor:
                    original_close(descriptor)
                    raise OSError("injected reader close failure")
                original_close(descriptor)

            monkeypatch.setattr(authority_refs.os, "close", close)
            raise ValueError("injected traversal failure")

    assert [type(item) for item in captured.value.exceptions] == [
        ValueError,
        OSError,
    ]
    assert reader._root_descriptor is None


def test_t5_s02cd_authority_acquisition_preserves_fstat_and_close_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    reader = AuthorityRefReader(root)
    original_close = authority_refs.os.close

    def fstat(_descriptor: int):
        raise OSError("injected authority fstat failure")

    def close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("injected authority acquisition close failure")

    monkeypatch.setattr(authority_refs.os, "fstat", fstat)
    monkeypatch.setattr(authority_refs.os, "close", close)
    with pytest.raises(BaseExceptionGroup) as captured:
        reader.__enter__()

    assert [
        str(error) for error in captured.value.exceptions
    ] == [
        "injected authority fstat failure",
        "injected authority acquisition close failure",
    ]
    assert reader._root_descriptor is None


def test_t5_s02cd_scientific_acquisition_preserves_identity_and_close_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    reader = ScientificRefReader(root)
    original_stat = scientific_records.os.stat
    original_close = scientific_records.os.close

    def stat(path, *args, **kwargs):
        metadata = original_stat(path, *args, **kwargs)
        if Path(path) == root and kwargs.get("follow_symlinks") is False:
            values = list(metadata)
            values[1] += 1
            return os.stat_result(values)
        return metadata

    def close(descriptor: int) -> None:
        original_close(descriptor)
        raise OSError("injected scientific acquisition close failure")

    monkeypatch.setattr(scientific_records.os, "stat", stat)
    monkeypatch.setattr(scientific_records.os, "close", close)
    with pytest.raises(BaseExceptionGroup) as captured:
        reader.__enter__()

    assert isinstance(captured.value.exceptions[0], ValueError)
    assert "identity changed" in str(captured.value.exceptions[0])
    assert str(captured.value.exceptions[1]) == (
        "injected scientific acquisition close failure"
    )
    assert reader._root_descriptor is None


def test_t5_s02cd_controller_reader_aggregates_traversal_and_close_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    with ControllerArtifactStore(root):
        pass
    resolver = ControllerArtifactResolver(root)
    original_close = controller_artifacts.os.close

    with pytest.raises(BaseExceptionGroup) as captured:
        with resolver:
            owned = {
                resolver._root_descriptor,
                resolver._artifact_descriptor,
            }

            def close(descriptor: int) -> None:
                original_close(descriptor)
                if descriptor in owned:
                    raise OSError(f"injected close failure {descriptor}")

            monkeypatch.setattr(controller_artifacts.os, "close", close)
            raise ValueError("injected traversal failure")

    assert [type(item) for item in captured.value.exceptions] == [
        ValueError,
        OSError,
        OSError,
    ]
    assert resolver._root_descriptor is None
    assert resolver._artifact_descriptor is None


def test_t5_s02cd_scientific_reader_aggregates_traversal_and_close_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    reader = ScientificRefReader(root)
    original_close = scientific_records.os.close

    with pytest.raises(BaseExceptionGroup) as captured:
        with reader:
            root_descriptor = reader._root_descriptor

            def close(descriptor: int) -> None:
                original_close(descriptor)
                if descriptor == root_descriptor:
                    raise OSError("injected scientific close failure")

            monkeypatch.setattr(scientific_records.os, "close", close)
            raise ValueError("injected traversal failure")

    assert [type(item) for item in captured.value.exceptions] == [
        ValueError,
        OSError,
    ]
    assert reader._root_descriptor is None


def test_t5_s02cd_controller_read_binds_bytes_and_inode_on_same_fd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    root.mkdir()
    payload = b"controller bytes"
    with ControllerArtifactStore(root) as store:
        ref = store.write(
            role="provider_response",
            payload=payload,
            media_type="application/octet-stream",
        )
    replacement = root / "replacement.bin"
    replacement.write_bytes(payload)
    target = root / ref.relative_path
    original_stat = controller_artifacts.os.stat
    swapped = [False]

    def stat(path, *args, **kwargs):
        if path == ref.sha256 and kwargs.get("dir_fd") is not None and not swapped[0]:
            swapped[0] = True
            os.replace(replacement, target)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(controller_artifacts.os, "stat", stat)
    with ControllerArtifactResolver(root) as resolver:
        with pytest.raises(ValueError, match="identity changed"):
            resolver.resolve_bound(
                ref,
                expected_role=ref.role,
                expected_media_type=ref.media_type,
            )


def test_t5_s02cd_scientific_read_binds_bytes_and_inode_on_same_fd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "run"
    fixture = ProviderAuthorityFixture.build(root)
    ref = fixture.schedule_ref
    target = root / ref.relative_path
    replacement = root / "replacement.json"
    replacement.write_bytes(target.read_bytes())
    original_stat = scientific_records.os.stat
    swapped = [False]

    def stat(path, *args, **kwargs):
        if (
            path == ref.relative_path
            and kwargs.get("dir_fd") is not None
            and not swapped[0]
        ):
            swapped[0] = True
            os.replace(replacement, target)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(scientific_records.os, "stat", stat)
    with ScientificRefReader(root) as reader:
        with pytest.raises(ValueError, match="identity changed"):
            reader.read_bound(ref)


@pytest.mark.parametrize(
    "fixture_kwargs",
    [
        {"foreign_task_input_extra": True},
        {"foreign_environment_extra": True},
    ],
)
def test_t5_s02cd_open_foreign_task_or_contract_is_rejected(
    tmp_path: Path,
    fixture_kwargs: dict[str, object],
) -> None:
    fixture = ProviderAuthorityFixture.build(
        tmp_path / "run",
        **fixture_kwargs,
    )
    with pytest.raises(ValueError, match="open or incomplete shape"):
        load_prefix_execution_authority(
            run_root=tmp_path / "run",
            schedule_ref=fixture.schedule_ref,
            task_id="task-1",
        )


def test_t5_s02cd_shared_grade_ref_is_checked_per_program_occurrence(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    fixture = ProviderAuthorityFixture.build(
        root,
        executable_sources=True,
        requires_simulator=False,
        simulator_present=False,
        foreign_grade_partial_reward=0.5,
    )
    with pytest.raises(BaseExceptionGroup) as captured:
        run_prefix(
            run_root=root,
            schedule_ref=fixture.schedule_ref,
            task_id="task-1",
        )
    assert captured.value.subgroup(
        lambda error: isinstance(error, ValueError)
        and "grade evidence fields differ" in str(error)
    ) is not None


@pytest.mark.parametrize(
    "grade_value",
    [
        {
            "success": False,
            "partial_reward": 0.0,
            "infrastructure_failure": False,
        },
        {"success": 0, "infrastructure_failure": False},
        {
            "success": 0,
            "partial_reward": 0.0,
            "infrastructure_failure": False,
            "extra": 0,
        },
        {
            "success": 0,
            "partial_reward": 0,
            "infrastructure_failure": False,
        },
    ],
)
def test_t5_s02cd_grade_decodes_direct_exact_values(
    tmp_path: Path,
    grade_value: object,
) -> None:
    authority = _loop_authority(tmp_path)
    opened = prefix_loop._open_prefix_loop(run_root=tmp_path, authority=authority)
    try:
        grade_bytes = canonical_json_bytes(grade_value, indent=None)
        with pytest.raises((TypeError, ValueError)):
            prefix_loop.SyntheticGradeCodec().decode(
                payload=grade_bytes,
                program=opened._program,
                expected_payload=grade_bytes,
            )
    finally:
        opened.close()


@pytest.mark.parametrize(
    "verifier_value",
    [
        {"finding_count": False},
        {},
        {"finding_count": 0, "extra": 0},
    ],
)
def test_t5_s02cd_verifier_decodes_direct_exact_values(
    tmp_path: Path,
    verifier_value: object,
) -> None:
    authority = _loop_authority(tmp_path)
    opened = prefix_loop._open_prefix_loop(run_root=tmp_path, authority=authority)
    try:
        verifier_bytes = canonical_json_bytes(verifier_value, indent=None)
        with pytest.raises((TypeError, ValueError)):
            prefix_loop.SyntheticVerifierCodec().decode(
                payload=verifier_bytes,
                program=opened._program,
                expected_payload=verifier_bytes,
            )
    finally:
        opened.close()


def test_t5_s02cd_reloaded_provider_and_tool_records_reject_cross_wiring(
    tmp_path: Path,
) -> None:
    authority = _loop_authority(tmp_path)
    opened = prefix_loop._open_prefix_loop(
        run_root=tmp_path,
        authority=authority,
    )
    try:
        assert opened._store is not None
        payloads = opened._store.snapshot_writes()
        ledger = load_provider_attempt_ledger(payloads[opened.provider_attempts_ref])
        intents_by_ref = {
            ref: load_provider_dispatch_intent(payloads[ref])
            for ref in opened.intent_refs
        }
        attempts_by_ref = {
            ref: load_provider_attempt(payloads[ref]) for ref in opened.attempt_refs
        }
        events_by_ref = {
            attempt.provider_event_ref: load_controller_provider_event(
                payloads[attempt.provider_event_ref]
            )
            for attempt in opened.attempts
        }
        settlements_by_ref = {
            settlement.settlement_ref: load_controller_provider_settlement(
                payloads[settlement.settlement_ref]
            )
            for settlement in opened.settlements
        }
        cost_record = load_controller_provider_cost_closure(
            payloads[opened.provider_cost_ref]
        )
        tool_ledger = load_tool_boundary_ledger(payloads[opened.boundary_ledger_ref])
        tool_calls_by_ref = {
            boundary.tool_call_ref: ToolCall(
                **json.loads(payloads[boundary.tool_call_ref])
            )
            for boundary in opened.boundaries
        }
        first_intent_ref = opened.intent_refs[0]
        first_attempt = opened.attempts[0]
        first_event_ref = first_attempt.provider_event_ref
        first_settlement_ref = opened.settlements[0].settlement_ref

        prefix_loop._reconcile_reloaded_execution_records(
            authority=authority,
            program=opened._program,
            expected_cost_closure=opened.cost_closure,
            expected_boundaries=opened.boundaries,
            ledger=ledger,
            intents_by_ref=intents_by_ref,
            attempts_by_ref=attempts_by_ref,
            events_by_ref=events_by_ref,
            settlements_by_ref=settlements_by_ref,
            cost_record=cost_record,
            tool_ledger=tool_ledger,
            tool_calls_by_ref=tool_calls_by_ref,
        )
        with pytest.raises(ValueError, match="intent"):
            prefix_loop._reconcile_reloaded_execution_records(
                authority=authority,
                program=opened._program,
                expected_cost_closure=opened.cost_closure,
                expected_boundaries=opened.boundaries,
                ledger=ledger,
                intents_by_ref={
                    **intents_by_ref,
                    first_intent_ref: replace(
                        intents_by_ref[first_intent_ref],
                        absolute_deadline_ms=(
                            intents_by_ref[first_intent_ref].absolute_deadline_ms + 1
                        ),
                    ),
                },
                attempts_by_ref=attempts_by_ref,
                events_by_ref=events_by_ref,
                settlements_by_ref=settlements_by_ref,
                cost_record=cost_record,
                tool_ledger=tool_ledger,
                tool_calls_by_ref=tool_calls_by_ref,
            )
        with pytest.raises(ValueError, match="event"):
            prefix_loop._reconcile_reloaded_execution_records(
                authority=authority,
                program=opened._program,
                expected_cost_closure=opened.cost_closure,
                expected_boundaries=opened.boundaries,
                ledger=ledger,
                intents_by_ref=intents_by_ref,
                attempts_by_ref=attempts_by_ref,
                events_by_ref={
                    **events_by_ref,
                    first_event_ref: replace(
                        events_by_ref[first_event_ref],
                        dispatch_intent_sha256="f" * 64,
                    ),
                },
                settlements_by_ref=settlements_by_ref,
                cost_record=cost_record,
                tool_ledger=tool_ledger,
                tool_calls_by_ref=tool_calls_by_ref,
            )
        with pytest.raises(ValueError, match="settlement"):
            prefix_loop._reconcile_reloaded_execution_records(
                authority=authority,
                program=opened._program,
                expected_cost_closure=opened.cost_closure,
                expected_boundaries=opened.boundaries,
                ledger=ledger,
                intents_by_ref=intents_by_ref,
                attempts_by_ref=attempts_by_ref,
                events_by_ref=events_by_ref,
                settlements_by_ref={
                    **settlements_by_ref,
                    first_settlement_ref: replace(
                        settlements_by_ref[first_settlement_ref],
                        provider_event_sha256="e" * 64,
                    ),
                },
                cost_record=cost_record,
                tool_ledger=tool_ledger,
                tool_calls_by_ref=tool_calls_by_ref,
            )
        with pytest.raises(ValueError, match="tool"):
            prefix_loop._reconcile_reloaded_execution_records(
                authority=authority,
                program=opened._program,
                expected_cost_closure=opened.cost_closure,
                expected_boundaries=opened.boundaries,
                ledger=ledger,
                intents_by_ref=intents_by_ref,
                attempts_by_ref=attempts_by_ref,
                events_by_ref=events_by_ref,
                settlements_by_ref=settlements_by_ref,
                cost_record=cost_record,
                tool_ledger=ToolBoundaryLedger(
                    (
                        replace(
                            tool_ledger.boundaries[0],
                            elapsed_ms=tool_ledger.boundaries[0].elapsed_ms + 1,
                        ),
                        *tool_ledger.boundaries[1:],
                    )
                ),
                tool_calls_by_ref=tool_calls_by_ref,
            )
    finally:
        opened.close()


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
            **_zero_attempt_reload_kwargs(
                root,
                authority=authority,
                candidate_ref=candidate_ref,
            ),
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
            **_zero_attempt_reload_kwargs(
                root,
                authority=authority,
                candidate_ref=candidate_ref,
            ),
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
            **_zero_attempt_reload_kwargs(
                root,
                authority=authority,
                candidate_ref=candidate_ref,
            ),
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
