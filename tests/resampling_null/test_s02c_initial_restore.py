from __future__ import annotations

from dataclasses import replace
import inspect
import os
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
import pneuma_lab.resampling_null.synthetic_environment as synthetic_environment
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.prefix_contracts import (
    ImplementationDescriptor,
    InitialRestoreQualificationReceipt,
    load_initial_restore_qualification_receipt,
)
from pneuma_lab.resampling_null.synthetic_environment import (
    InitialQualificationAuthority,
    SyntheticEnvironmentFactory,
    SyntheticEnvironmentHandle,
    SyntheticByteTokenizer,
    _InitialObservation,
    _assert_pairwise_isolated,
    _open_qualified_initial_restore,
    _qualify_initial_restore,
    _validate_initial_observation,
)
from pneuma_lab.resampling_null.types import ArtifactRef, FailureKind


def _ref(role: str, name: str, *, media_type: str = "application/json") -> ArtifactRef:
    payload = name.encode()
    digest = __import__("hashlib").sha256(payload).hexdigest()
    relative_path = (
        f"controller-artifacts/{role}/{digest}"
        if role == "selected_task"
        else f"sources/{name}"
    )
    return ArtifactRef(
        role=role,
        relative_path=relative_path,
        sha256=digest,
        byte_count=len(payload),
        media_type=media_type,
    )


def _authority() -> InitialQualificationAuthority:
    task_input_bytes = canonical_json_bytes(
        {"messages": [{"content": "restore me", "role": "user"}]},
        indent=None,
    )
    program_bytes = canonical_json_bytes(
        {
            "record_kind": "synthetic_prefix_program_v1",
            "schema_version": "1",
            "task_id": "task-0",
        },
        indent=None,
    )
    source_bytes = (
        Path(__file__).parents[2]
        / "src/pneuma_lab/resampling_null/synthetic_environment.py"
    ).read_bytes()
    source_ref = ArtifactRef(
        "source_revision",
        "sources/synthetic_environment.py",
        __import__("hashlib").sha256(source_bytes).hexdigest(),
        len(source_bytes),
        "application/octet-stream",
    )
    return InitialQualificationAuthority(
        schedule_ref=_ref("resampling_prefix_schedule", "schedule"),
        task_ref=_ref("selected_task", "task"),
        task_input_ref=ArtifactRef(
            "task_input",
            "sources/task-input.json",
            __import__("hashlib").sha256(task_input_bytes).hexdigest(),
            len(task_input_bytes),
            "application/json",
        ),
        environment_contract_ref=_ref(
            "environment_contract",
            "environment-contract",
        ),
        isolation_contract_ref=_ref("isolation_contract", "isolation-contract"),
        program_ref=ArtifactRef(
            "synthetic_execution_program",
            "sources/program.json",
            __import__("hashlib").sha256(program_bytes).hexdigest(),
            len(program_bytes),
            "application/json",
        ),
        environment_descriptor=ImplementationDescriptor(
            purpose="environment",
            nominal_type=(
                "pneuma_lab.resampling_null.synthetic_environment."
                "SyntheticEnvironmentFactory"
            ),
            build_id="synthetic-environment-v1",
            request_grammar=None,
            response_grammar=None,
            snapshot_grammar="synthetic-environment-snapshot-v1",
            restore_grammar="synthetic-environment-snapshot-v1",
            evidence_grammar="synthetic-environment-evidence-v1",
            runtime_id="cpython-3.12-local",
            container_digest="sha256:" + "0" * 64,
            implementation_source_ref=source_ref,
        ),
        tokenizer_descriptor=ImplementationDescriptor(
            purpose="tokenizer",
            nominal_type=(
                "pneuma_lab.resampling_null.synthetic_environment."
                "SyntheticByteTokenizer"
            ),
            build_id="synthetic-byte-tokenizer-v1",
            request_grammar=None,
            response_grammar=None,
            snapshot_grammar=None,
            restore_grammar=None,
            evidence_grammar=None,
            runtime_id=None,
            container_digest=None,
            implementation_source_ref=source_ref,
        ),
        task_input_bytes=task_input_bytes,
        program_bytes=program_bytes,
    )


def test_initial_restore_uses_real_distinct_processes_and_skips_stale_roots(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "prefix-environments"
    workspace.mkdir()
    stale = workspace / "instance-0000-00"
    stale.mkdir()
    (stale / "do-not-touch").write_bytes(b"stale")
    external = tmp_path / "external"
    external.mkdir()
    (workspace / "instance-0000-01").symlink_to(external, target_is_directory=True)

    result = _qualify_initial_restore(
        run_root=tmp_path,
        authority=_authority(),
    )

    assert result.receipt_ref.role == "initial_restore_qualification"
    stored = (tmp_path / result.receipt_ref.relative_path).read_bytes()
    receipt = load_initial_restore_qualification_receipt(stored)
    assert type(receipt) is InitialRestoreQualificationReceipt
    assert receipt.live_identity.child_pid > 0
    assert receipt.fresh_restore_identity.child_pid > 0
    assert receipt.live_identity.child_pid != receipt.fresh_restore_identity.child_pid
    assert (
        receipt.live_identity.writable_root_st_dev,
        receipt.live_identity.writable_root_st_ino,
    ) != (
        receipt.fresh_restore_identity.writable_root_st_dev,
        receipt.fresh_restore_identity.writable_root_st_ino,
    )
    assert receipt.live_identity.writable_root_relative_path.endswith(
        "instance-0000-02"
    )
    assert (stale / "do-not-touch").read_bytes() == b"stale"
    assert external.exists()
    assert not (workspace / "instance-0000-02").exists()
    assert not (workspace / "instance-0001-00").exists()


def test_factory_boundary_cannot_supply_pid_or_root_identity() -> None:
    command = inspect.signature(SyntheticEnvironmentFactory.command)
    bind = inspect.signature(SyntheticEnvironmentFactory.bind)

    assert tuple(command.parameters) == ("self", "task_input_bytes", "program_bytes")
    assert tuple(bind.parameters) == (
        "self",
        "process",
        "ipc",
        "writable_root_fd",
        "instance_ordinal",
    )
    assert "pid" not in bind.parameters
    assert "identity" not in bind.parameters
    assert "root_path" not in bind.parameters


def test_workspace_symlink_and_exhausted_stale_names_fail_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external = tmp_path / "external"
    external.mkdir()
    symlink_root = tmp_path / "symlink-root"
    symlink_root.mkdir()
    (symlink_root / "prefix-environments").symlink_to(
        external,
        target_is_directory=True,
    )
    with pytest.raises(RecordValidationError, match="workspace is unsafe"):
        _qualify_initial_restore(
            run_root=symlink_root,
            authority=_authority(),
        )
    assert not any(external.iterdir())

    collision_root = tmp_path / "collision-root"
    workspace = collision_root / "prefix-environments"
    workspace.mkdir(parents=True)
    monkeypatch.setattr(synthetic_environment, "_ROOT_SUFFIX_ATTEMPTS", 2)
    for suffix in range(2):
        stale = workspace / f"instance-0000-{suffix:02d}"
        stale.mkdir()
        (stale / "sentinel").write_text(str(suffix))
    with pytest.raises(BaseExceptionGroup) as raised:
        _qualify_initial_restore(
            run_root=collision_root,
            authority=_authority(),
        )
    assert any(
        "suffix search exhausted" in str(error) for error in raised.value.exceptions
    )
    assert [
        (workspace / f"instance-0000-{suffix:02d}" / "sentinel").read_text()
        for suffix in range(2)
    ] == ["0", "1"]


def test_qualification_rejects_unsealed_bytes_and_environment_descriptor() -> None:
    authority = _authority()
    with pytest.raises(ValueError, match="task_input_bytes"):
        replace(authority, task_input_bytes=b"drift")
    with pytest.raises(ValueError, match="program_bytes"):
        replace(authority, program_bytes=b"drift")
    with pytest.raises(ValueError, match="registered environment descriptor"):
        replace(
            authority,
            environment_descriptor=replace(
                authority.environment_descriptor,
                build_id="spoof",
            ),
        )
    with pytest.raises(ValueError, match="registered tokenizer descriptor"):
        replace(
            authority,
            tokenizer_descriptor=replace(
                authority.tokenizer_descriptor,
                nominal_type="SpoofTokenizer",
            ),
        )
    assert SyntheticByteTokenizer().encode(b"\x00\xff") == (0, 255)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("resnapshot_bytes", b"different"),
        ("visible_context", b"different"),
        ("token_ids", (1, 2, 999)),
        ("branch_pending_calls", (object(),)),
        ("terminal_unexecuted_remainder", (object(),)),
        ("episode_terminal", True),
        ("failure_kind", FailureKind.INFRASTRUCTURE),
    ],
)
def test_initial_restore_rejects_every_byte_and_state_mismatch(
    field: str,
    value: object,
) -> None:
    snapshot = b'{"state":"initial"}'
    observation = _InitialObservation(
        snapshot_bytes=snapshot,
        resnapshot_bytes=snapshot,
        visible_context=b"visible",
        restored_visible_context=b"visible",
        token_ids=(1, 2, 3),
        restored_token_ids=(1, 2, 3),
        branch_pending_calls=(),
        restored_branch_pending_calls=(),
        terminal_unexecuted_remainder=(),
        restored_terminal_unexecuted_remainder=(),
        episode_terminal=False,
        restored_episode_terminal=False,
        failure_kind=FailureKind.NONE,
        restored_failure_kind=FailureKind.NONE,
    )

    if field in ("visible_context", "token_ids"):
        changed = replace(observation, **{f"restored_{field}": value})
    elif field in (
        "branch_pending_calls",
        "terminal_unexecuted_remainder",
        "episode_terminal",
        "failure_kind",
    ):
        changed = replace(observation, **{f"restored_{field}": value})
    else:
        changed = replace(observation, **{field: value})

    with pytest.raises(ValueError, match="initial restore"):
        _validate_initial_observation(changed)


def test_identity_checks_reject_object_pid_root_alias_and_dead_process(
    tmp_path: Path,
) -> None:
    (tmp_path / "one").mkdir()
    one = _open_qualified_initial_restore(
        run_root=tmp_path / "one",
        authority=_authority(),
    )
    killed = False
    try:
        live, restored = one._resources
        _assert_pairwise_isolated((live, restored))
        with pytest.raises(ValueError, match="object"):
            _assert_pairwise_isolated((live, live))
        alias_pid = replace(restored.identity, child_pid=live.identity.child_pid)
        with pytest.raises(ValueError, match="PID"):
            _assert_pairwise_isolated((live, replace(restored, identity=alias_pid)))
        alias_root = replace(
            restored.identity,
            writable_root_st_dev=live.identity.writable_root_st_dev,
            writable_root_st_ino=live.identity.writable_root_st_ino,
        )
        with pytest.raises(ValueError, match="root"):
            _assert_pairwise_isolated((live, replace(restored, identity=alias_root)))
        live.process.terminate()
        live.process.wait(timeout=2)
        killed = True
        with pytest.raises(ValueError, match="not live"):
            _assert_pairwise_isolated((live, restored))
    finally:
        if killed:
            with pytest.raises(BaseExceptionGroup):
                one.close()
        else:
            one.close()


def test_cleanup_aggregates_baseexception_and_removes_only_owned_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_close = SyntheticEnvironmentHandle.close
    calls = 0

    def explosive_close(self: SyntheticEnvironmentHandle) -> None:
        nonlocal calls
        calls += 1
        original_close(self)
        if calls == 1:
            raise KeyboardInterrupt("synthetic close fault")

    monkeypatch.setattr(SyntheticEnvironmentHandle, "close", explosive_close)

    with pytest.raises(BaseExceptionGroup) as raised:
        _qualify_initial_restore(
            run_root=tmp_path,
            authority=_authority(),
        )

    def leaves(group: BaseExceptionGroup) -> list[BaseException]:
        result: list[BaseException] = []
        for error in group.exceptions:
            if isinstance(error, BaseExceptionGroup):
                result.extend(leaves(error))
            else:
                result.append(error)
        return result

    assert any(isinstance(error, KeyboardInterrupt) for error in leaves(raised.value))
    workspace = tmp_path / "prefix-environments"
    assert not any(workspace.iterdir())
    assert not [
        child
        for child in os.listdir("/proc/self/fd")
        if child == "definitely-not-a-real-fd"
    ]
