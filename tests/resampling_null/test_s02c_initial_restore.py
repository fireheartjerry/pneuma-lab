from __future__ import annotations

from dataclasses import replace
import inspect
import os
from pathlib import Path
import subprocess

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
    _cleanup_process,
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


def _exception_leaves(group: BaseExceptionGroup) -> list[BaseException]:
    result: list[BaseException] = []
    for error in group.exceptions:
        if isinstance(error, BaseExceptionGroup):
            result.extend(_exception_leaves(error))
        else:
            result.append(error)
    return result


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


def test_factory_command_executes_the_single_reviewed_source() -> None:
    authority = _authority()
    factory = SyntheticEnvironmentFactory(
        task_input_bytes=authority.task_input_bytes,
        program_bytes=authority.program_bytes,
        implementation_source_sha256=(
            authority.environment_descriptor.implementation_source_ref.sha256
        ),
    )

    command = factory.command(
        task_input_bytes=authority.task_input_bytes,
        program_bytes=authority.program_bytes,
    )

    assert Path(command[2]).samefile(Path(synthetic_environment.__file__))
    assert "--synthetic-worker" in command
    source_index = command.index("--source-sha256")
    assert command[source_index + 1] == (
        authority.environment_descriptor.implementation_source_ref.sha256
    )
    assert "_synthetic_environment_worker.py" not in " ".join(command)
    assert (
        not Path(synthetic_environment.__file__)
        .with_name("_synthetic_environment_worker.py")
        .exists()
    )


def test_factory_state_is_frozen_and_object_level_drift_is_detected() -> None:
    authority = _authority()
    factory = SyntheticEnvironmentFactory(
        task_input_bytes=authority.task_input_bytes,
        program_bytes=authority.program_bytes,
        implementation_source_sha256=(
            authority.environment_descriptor.implementation_source_ref.sha256
        ),
    )
    with pytest.raises((AttributeError, TypeError)):
        factory.program_bytes = b"drift"  # type: ignore[attr-defined]

    object.__setattr__(factory, "_program_bytes", b"drift")
    with pytest.raises(RecordValidationError, match="sealed bytes"):
        factory.command(
            task_input_bytes=authority.task_input_bytes,
            program_bytes=authority.program_bytes,
        )


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


def test_root_open_failure_after_mkdir_cleans_exact_owned_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_open = synthetic_environment.os.open

    def fail_instance_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == "instance-0000-00":
            raise OSError("injected post-mkdir open failure")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(synthetic_environment.os, "open", fail_instance_open)
    with pytest.raises(BaseExceptionGroup):
        _qualify_initial_restore(run_root=tmp_path, authority=_authority())
    assert not (tmp_path / "prefix-environments" / "instance-0000-00").exists()


def test_root_open_replacement_race_never_deletes_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_open = synthetic_environment.os.open
    workspace = tmp_path / "prefix-environments"

    def replace_before_open(
        path: object,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == "instance-0000-00":
            (workspace / "instance-0000-00").rename(workspace / "moved-owned")
            (workspace / "instance-0000-00").mkdir()
            (workspace / "instance-0000-00" / "replacement").write_text("keep")
            raise OSError("injected replacement race")
        return real_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(synthetic_environment.os, "open", replace_before_open)
    with pytest.raises(BaseExceptionGroup) as raised:
        _qualify_initial_restore(run_root=tmp_path, authority=_authority())
    assert any(
        "uncertain" in str(error).lower() for error in _exception_leaves(raised.value)
    )
    assert (workspace / "instance-0000-00" / "replacement").read_text() == "keep"
    assert (workspace / "moved-owned").is_dir()


def test_bind_failure_cleans_nested_child_contents_through_held_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_bind(
        self: SyntheticEnvironmentFactory,
        *,
        process: subprocess.Popen[bytes],
        ipc: object,
        writable_root_fd: int,
        instance_ordinal: int,
    ) -> object:
        os.mkdir("nested", dir_fd=writable_root_fd)
        nested_fd = os.open(
            "nested",
            os.O_RDONLY | os.O_DIRECTORY,
            dir_fd=writable_root_fd,
        )
        try:
            file_fd = os.open(
                "payload",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=nested_fd,
            )
            os.close(file_fd)
        finally:
            os.close(nested_fd)
        raise RuntimeError("injected bind failure")

    monkeypatch.setattr(SyntheticEnvironmentFactory, "bind", fail_bind)
    with pytest.raises(BaseExceptionGroup):
        _qualify_initial_restore(run_root=tmp_path, authority=_authority())
    assert not (tmp_path / "prefix-environments" / "instance-0000-00").exists()


@pytest.mark.parametrize(
    "phase",
    ["second_pipe", "first_dup", "first_fdopen", "second_dup", "second_fdopen"],
)
def test_ipc_creation_is_transactional_for_every_acquisition(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    before = len(os.listdir("/proc/self/fd"))
    real_pipe = synthetic_environment.os.pipe
    real_dup = synthetic_environment.os.dup
    real_fdopen = synthetic_environment.os.fdopen
    counts = {"pipe": 0, "dup": 0, "fdopen": 0}

    def injected_pipe() -> tuple[int, int]:
        counts["pipe"] += 1
        if phase == "second_pipe" and counts["pipe"] == 2:
            raise OSError("injected second pipe failure")
        return real_pipe()

    def injected_dup(descriptor: int) -> int:
        counts["dup"] += 1
        if phase == "first_dup" and counts["dup"] == 1:
            raise OSError("injected first dup failure")
        if phase == "second_dup" and counts["dup"] == 2:
            raise OSError("injected second dup failure")
        return real_dup(descriptor)

    def injected_fdopen(
        descriptor: int,
        mode: str,
        buffering: int = -1,
    ) -> object:
        counts["fdopen"] += 1
        if phase == "first_fdopen" and counts["fdopen"] == 1:
            raise OSError("injected first fdopen failure")
        if phase == "second_fdopen" and counts["fdopen"] == 2:
            raise OSError("injected second fdopen failure")
        return real_fdopen(descriptor, mode, buffering=buffering)

    monkeypatch.setattr(synthetic_environment.os, "pipe", injected_pipe)
    monkeypatch.setattr(synthetic_environment.os, "dup", injected_dup)
    monkeypatch.setattr(synthetic_environment.os, "fdopen", injected_fdopen)
    with pytest.raises(BaseException):
        synthetic_environment.ControllerEnvironmentIPC.create()
    assert len(os.listdir("/proc/self/fd")) == before


def test_process_cleanup_waits_after_terminate_and_kill_failures() -> None:
    class CleanupProcess:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self.waits = 0

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            self.calls.append("terminate")
            raise OSError("terminate failed")

        def wait(self, *, timeout: int) -> int:
            self.calls.append(f"wait:{timeout}")
            self.waits += 1
            if self.waits == 1:
                raise subprocess.TimeoutExpired("fixture", timeout)
            return 0

        def kill(self) -> None:
            self.calls.append("kill")
            raise OSError("kill failed")

    process = CleanupProcess()
    errors = _cleanup_process(process)  # type: ignore[arg-type]

    assert process.calls == ["terminate", "wait:1", "kill", "wait:1"]
    assert [str(error) for error in errors] == ["terminate failed", "kill failed"]


def test_process_cleanup_preserves_poll_failure_and_still_attempts_policy() -> None:
    class PollFailureProcess:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def poll(self) -> None:
            self.calls.append("poll")
            raise OSError("poll failed")

        def terminate(self) -> None:
            self.calls.append("terminate")

        def wait(self, *, timeout: int) -> int:
            self.calls.append(f"wait:{timeout}")
            return 0

        def kill(self) -> None:
            self.calls.append("kill")

    process = PollFailureProcess()
    errors = _cleanup_process(process)  # type: ignore[arg-type]

    assert process.calls == ["poll", "terminate", "wait:1"]
    assert [str(error) for error in errors] == ["poll failed"]


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


def test_cleanup_replacement_race_preserves_new_name_target(tmp_path: Path) -> None:
    result = _open_qualified_initial_restore(
        run_root=tmp_path,
        authority=_authority(),
    )
    first = result._resources[0]
    workspace = tmp_path / "prefix-environments"
    owned = workspace / first.root_name
    moved = workspace / "moved-after-qualification"
    owned.rename(moved)
    owned.mkdir()
    (owned / "replacement").write_text("keep")

    with pytest.raises(BaseExceptionGroup) as raised:
        result.close()

    assert any(
        "uncertain" in str(error).lower() for error in _exception_leaves(raised.value)
    )
    assert (owned / "replacement").read_text() == "keep"
    assert moved.is_dir()


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

    assert any(
        isinstance(error, KeyboardInterrupt)
        for error in _exception_leaves(raised.value)
    )
    workspace = tmp_path / "prefix-environments"
    assert not any(workspace.iterdir())
    assert not [
        child
        for child in os.listdir("/proc/self/fd")
        if child == "definitely-not-a-real-fd"
    ]
