"""Capability boundary tests for the blinded projection candidate."""

from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

import pytest

from pneuma_lab.resampling_null.errors import RecordValidationError


pytestmark = pytest.mark.milestone


def test_candidate_module_is_capability_minimal_in_a_clean_subprocess() -> None:
    program = """
import ast
import inspect
import pneuma_lab.resampling_null.projection_candidate as candidate
source = inspect.getsource(candidate)
tree = ast.parse(source)
names = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
names |= {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
for forbidden in ('pathlib', 'artifacts', 'assignment', 'secrets', 'packets'):
    assert not any(forbidden in name for name in names), names
assert 'BranchOutcome' not in source
assert 'Arm' not in source
"""
    result = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr


def test_candidate_protocol_runs_in_clean_subprocess_without_a_run_root(tmp_path) -> None:
    """The projector accepts only closed stdin data and emits only candidate bytes."""
    module = Path(__file__).parents[2] / "src/pneuma_lab/resampling_null/projection_candidate.py"
    outcomes = [{"success": 0, "prefix_success": 0, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}] * 4
    request = {"frozen_schedule": [{"task_id": "t", "prefix_success": 0, "slot_ids": ["0", "1", "2", "3"]}], "closed_outcomes": {"t": outcomes}}
    result = subprocess.run(
        [sys.executable, "-I", str(module)],
        cwd=tmp_path,
        env={}, input=json.dumps(request).encode("utf-8"), capture_output=True, text=False,
        check=False,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert b"artifact_ref" not in result.stdout
    assert json.loads(result.stdout) == json.loads(
        __import__("pneuma_lab.resampling_null.projection_candidate", fromlist=["build_candidate"]).build_candidate(
            request["frozen_schedule"], request["closed_outcomes"]
        ).canonical_bytes
    )


def test_candidate_sorts_schedule_and_strips_outcomes() -> None:
    from pneuma_lab.resampling_null.projection_candidate import build_candidate

    candidate = build_candidate(
        [
            {"task_id": "z", "prefix_success": 1, "slot_ids": ["z0", "z1", "z2", "z3"]},
            {"task_id": "a", "prefix_success": 0, "slot_ids": ["a0", "a1", "a2", "a3"]},
        ],
        {
            "a": [{"success": 0, "prefix_success": 0, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}] * 4,
            "z": [{"success": 1, "prefix_success": 1, "partial_reward": 1.0, "infrastructure_failure": False, "counters": {"generated_tokens": 1, "model_calls": 1, "tool_calls": 0, "wall_clock_ms": 1}}] * 4,
        },
    )

    assert [row["task_id"] for row in candidate.rows] == ["z", "a"]
    assert [slot["label"] for slot in candidate.rows[0]["slots"]] == ["A", "B", "C", "D"]
    assert "artifact_ref" not in repr(candidate.rows)


def test_candidate_rejects_prefix_mismatch_and_incomplete_coverage() -> None:
    from pneuma_lab.resampling_null.projection_candidate import build_candidate

    row = {"task_id": "a", "prefix_success": 0, "slot_ids": ["0", "1", "2", "3"]}
    outcome = {"success": 1, "prefix_success": 1, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}
    with pytest.raises(ValueError, match="coverage"):
        build_candidate([row], {})
    with pytest.raises(ValueError, match="prefix"):
        build_candidate([row], {"a": [outcome] * 4})


def test_trusted_sealer_is_not_exposed_by_the_candidate_module() -> None:
    import pneuma_lab.resampling_null.projection_candidate as candidate
    from pneuma_lab.resampling_null.blinding import seal_blinded_projection

    assert not hasattr(candidate, "seal_blinded_projection")
    assert callable(seal_blinded_projection)


def test_trusted_sealer_rejects_a_byte_different_caller_candidate(monkeypatch, tmp_path) -> None:
    """A digest match is insufficient: the supplied sealed bytes are checked."""
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.projection_candidate import ProjectionCandidate, build_candidate

    schedule = {
        "payload": {"tasks": [{"task": {"task_id": "t", "lineage": []}, "slots": [{"slot_id": str(i)} for i in range(4)]}]},
        "study_id": "s", "frozen_created_at": "2026-01-01T00:00:00Z", "provenance": {"code_sha256": "0" * 64, "design_sha256": "1" * 64},
    }
    block = {"payload": {"task_id": "t", "prefix_success": 0, "slot_outcomes": [{"success": 0, "prefix_success": 0, "partial_reward": 0.0, "infrastructure_failure": False, "counters": {"generated_tokens": 0, "model_calls": 0, "tool_calls": 0, "wall_clock_ms": 0}}] * 4, "benchmark": "b", "stratum": "x", "sensitivity_groups": [], "triggered": False, "pipeline_valid": True, "validity_codes": []}}
    freeze = {"study_id": "s"}
    documents = iter([schedule, freeze, block])
    monkeypatch.setattr(blinding, "_load_direct_scientific_parent", lambda *args, **kwargs: type("D", (), {"value": next(documents)})())
    monkeypatch.setattr(blinding, "verify_frozen_analysis_inputs", lambda *args, **kwargs: None)
    valid = build_candidate(
        [{"task_id": "t", "prefix_success": 0, "slot_ids": [str(i) for i in range(4)]}],
        {"t": block["payload"]["slot_outcomes"]},
    )
    mismatched = ProjectionCandidate(valid.rows, b"[]", valid.sha256)
    ref = __import__("pneuma_lab.resampling_null.types", fromlist=["ArtifactRef"]).ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    with pytest.raises(Exception, match="caller candidate bytes"):
        blinding._seal_blinded_projection_locked(run_root=tmp_path, destination=tmp_path / "out.json", schedule_ref=ref, analysis_freeze_ref=ref, task_block_refs=(ref,), candidate=mismatched)


def test_unblind_checks_graph_and_current_inputs_before_ledger_loader(monkeypatch, tmp_path) -> None:
    """The clear-ledger loader is structurally last in the pre-exposure path."""
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.freeze import CurrentAnalysisInputs
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "run"
    root.mkdir()
    ref = ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    inputs = CurrentAnalysisInputs({}, tmp_path / "config", tmp_path / "schema", ref)
    observed: list[str] = []
    monkeypatch.setattr(blinding, "validate_preunblind_graph", lambda *a: observed.append("pregraph"))
    monkeypatch.setattr(blinding, "verify_current_analysis_inputs", lambda *a, **k: observed.append("current"))
    monkeypatch.setattr(blinding, "_validated_permit", lambda *a, **k: observed.append("permit") or ("permit", {"rows": []}, {}))
    monkeypatch.setattr(blinding, "validate_scientific_graph", lambda *a: observed.append("graph"))
    monkeypatch.setattr(blinding, "_validate_ledger_ancestry", lambda *a, **k: observed.append("ledger") or {"payload": {"assignments": []}, "study_id": "s", "frozen_created_at": "2026-01-01T00:00:00Z", "provenance": {}})
    result = blinding._stage_unblind_projection_locked(
        object(), permit_hmac_sha256="permit", root=root, manifest_ref=ref,
        schedule_ref=ref, prefix_index_ref=ref, ledger_ref=ref,
        projection_ref=ref, freeze_ref=ref, expected_task_count=0,
        current_analysis_inputs=inputs,
    )
    assert result.rows == ()
    assert observed == ["pregraph", "current", "permit", "graph", "ledger"]


def test_permit_issuance_never_decodes_the_clear_ledger(monkeypatch, tmp_path) -> None:
    """Only the private paired-unblind stage may cross to clear parsing."""
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.types import ArtifactRef

    ref = ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    monkeypatch.setattr(
        blinding, "_validated_permit",
        lambda *args, **kwargs: ("permit", {}, {}),
    )
    monkeypatch.setattr(
        blinding, "_validate_ledger_ancestry",
        lambda *args, **kwargs: pytest.fail("permit issuance decoded clear ledger"),
    )
    assert blinding.issue_unblind_permit(
        object(), run_root=tmp_path, manifest_ref=ref, schedule_ref=ref,
        prefix_index_ref=ref, ledger_ref=ref, projection_ref=ref, freeze_ref=ref,
        expected_task_count=1,
    ) == "permit"


def test_valid_permit_taints_before_full_graph_failure(monkeypatch, tmp_path) -> None:
    """A graph parser interruption cannot leave a potentially exposed run clean."""
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.freeze import CurrentAnalysisInputs
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "run"
    root.mkdir()
    ref = ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    inputs = CurrentAnalysisInputs({}, tmp_path / "config", tmp_path / "schema", ref)
    monkeypatch.setattr(blinding, "validate_preunblind_graph", lambda *a: None)
    monkeypatch.setattr(blinding, "verify_current_analysis_inputs", lambda *a, **k: None)
    monkeypatch.setattr(blinding, "_validated_permit", lambda *a, **k: ("permit", {"rows": []}, {}))
    monkeypatch.setattr(blinding, "validate_scientific_graph", lambda *a: (_ for _ in ()).throw(RecordValidationError("graph failure")))
    with pytest.raises(RecordValidationError, match="graph failure"):
        blinding._stage_unblind_projection_locked(
            object(), permit_hmac_sha256="permit", root=root, manifest_ref=ref,
            schedule_ref=ref, prefix_index_ref=ref, ledger_ref=ref,
            projection_ref=ref, freeze_ref=ref, expected_task_count=0,
            current_analysis_inputs=inputs,
        )
    assert (root / "operational/task6/outcome-tainted.json").is_file()


def test_paired_unblind_analysis_builder_failure_publishes_neither_record_but_taints(
    monkeypatch, tmp_path,
) -> None:
    """After clear parsing starts, a failed analysis cannot orphan a receipt."""
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.freeze import CurrentAnalysisInputs
    from pneuma_lab.resampling_null.task6_state import require_preunblind_context
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "run"
    root.mkdir()
    ref = ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    inputs = CurrentAnalysisInputs({}, tmp_path / "config", tmp_path / "schema", ref)
    monkeypatch.setattr(blinding, "validate_preunblind_graph", lambda *a: None)
    monkeypatch.setattr(blinding, "verify_current_analysis_inputs", lambda *a, **k: None)
    permit = "a" * 64
    monkeypatch.setattr(blinding, "_validated_permit", lambda *a, **k: (
        permit, {"rows": [{"task_id": "t", "slots": [{"slot_id": "0"}]}]}, {},
    ))
    monkeypatch.setattr(blinding, "validate_scientific_graph", lambda *a: None)
    monkeypatch.setattr(blinding, "_pair_transaction_key", lambda *a, **k: b"k" * 32)
    monkeypatch.setattr(blinding, "_require_manifest_ancestry", lambda *a, **k: None)
    monkeypatch.setattr(blinding, "_validate_ledger_ancestry", lambda *a, **k: {
        "payload": {"assignments": [{"task_id": "t", "slot_arms": {"0": "REAL"}}]},
        "study_id": "s", "frozen_created_at": "2026-01-01T00:00:00Z",
        "provenance": {"code_sha256": "0" * 64, "design_sha256": "1" * 64},
    })

    def fail_after_clear(_stage: object) -> dict[str, object]:
        raise RecordValidationError("injected analysis failure")

    with pytest.raises(RecordValidationError, match="injected analysis failure"):
        blinding.unblind_and_publish_analysis(
            object(), recovery_handle=object(), permit_hmac_sha256=permit, run_root=root,
            receipt_destination=root / "receipt.json", analysis_destination=root / "analysis.json",
            manifest_ref=ref, schedule_ref=ref, prefix_index_ref=ref, ledger_ref=ref,
            projection_ref=ref, freeze_ref=ref, expected_task_count=1,
            current_analysis_inputs=inputs, analysis_builder=fail_after_clear,
        )
    assert not (root / "receipt.json").exists()
    assert not (root / "analysis.json").exists()
    assert (root / "operational/task6/outcome-tainted.json").is_file()
    with pytest.raises(RecordValidationError, match="outcome-tainted"):
        require_preunblind_context(root, "resampling_blinded_projection")


def test_paired_unblind_second_publication_failure_rolls_back_receipt(
    monkeypatch, tmp_path,
) -> None:
    """A failing second write leaves no publicly discoverable half-pair."""
    import hashlib
    import pneuma_lab.resampling_null.blinding as blinding
    from pneuma_lab.resampling_null.freeze import CurrentAnalysisInputs
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "run"
    root.mkdir()
    ref = ArtifactRef("x", "x.json", "0" * 64, 0, "application/json")
    inputs = CurrentAnalysisInputs({}, tmp_path / "config", tmp_path / "schema", ref)
    permit = "a" * 64
    monkeypatch.setattr(blinding, "validate_preunblind_graph", lambda *a: None)
    monkeypatch.setattr(blinding, "verify_current_analysis_inputs", lambda *a, **k: None)
    monkeypatch.setattr(blinding, "_validated_permit", lambda *a, **k: (
        permit, {"rows": [{"task_id": "t", "slots": [{"slot_id": "0"}]}]}, {},
    ))
    monkeypatch.setattr(blinding, "validate_scientific_graph", lambda *a: None)
    monkeypatch.setattr(blinding, "_pair_transaction_key", lambda *a, **k: b"k" * 32)
    monkeypatch.setattr(blinding, "_validate_ledger_ancestry", lambda *a, **k: {
        "payload": {"assignments": [{"task_id": "t", "slot_arms": {"0": "REAL"}}]},
        "study_id": "s", "frozen_created_at": "2026-01-01T00:00:00Z",
        "provenance": {"code_sha256": "0" * 64, "design_sha256": "1" * 64},
    })
    prepared = 0
    receipt_ref = None
    def fake_prepared(_record, *, run_root, relative_path, role):
        nonlocal prepared, receipt_ref
        prepared += 1
        payload = f"{role}-{prepared}".encode("ascii")
        result_ref = ArtifactRef(role, relative_path, hashlib.sha256(payload).hexdigest(), len(payload), "application/json")
        if receipt_ref is None:
            receipt_ref = result_ref
            return _record, result_ref, payload
        assert receipt_ref is not None
        return {"payload": {"unblind_receipt_ref": blinding._mapping_ref(receipt_ref)}}, result_ref, payload
    monkeypatch.setattr(blinding, "_ref_for_prepared_record", fake_prepared)
    real_install = blinding.install_paired_publication_entry
    def fail_second(root, index, *, auth_key):
        if index == 1:
            raise OSError("injected publication failure")
        real_install(root, index, auth_key=auth_key)
    monkeypatch.setattr(blinding, "install_paired_publication_entry", fail_second)

    with pytest.raises(OSError, match="injected publication failure"):
        blinding.unblind_and_publish_analysis(
            object(), recovery_handle=object(), permit_hmac_sha256=permit, run_root=root,
            receipt_destination=root / "receipt.json", analysis_destination=root / "analysis.json",
            manifest_ref=ref, schedule_ref=ref, prefix_index_ref=ref, ledger_ref=ref,
            projection_ref=ref, freeze_ref=ref, expected_task_count=1,
            current_analysis_inputs=inputs, analysis_builder=lambda _stage: {},
        )
    assert not (root / "receipt.json").exists()
    assert not (root / "analysis.json").exists()
    assert not (root / "operational/task6/paired-publication.json").exists()
    assert (root / "operational/task6/outcome-tainted.json").is_file()


def test_next_task6_controller_entry_recovers_a_crashed_partial_pair(tmp_path) -> None:
    """The durable no-clear transaction makes a crash recoverable, not orphaning."""
    from pneuma_lab.resampling_null.task6_state import (
        begin_paired_publication,
        install_paired_publication_entry,
        prepare_paired_publication_entry,
        task6_controller_lock,
    )

    root = tmp_path / "run"
    root.mkdir()
    key = b"k" * 32
    receipt, analysis = root / "receipt.json", root / "analysis.json"
    begin_paired_publication(root, ((receipt, b"receipt"), (analysis, b"analysis")), auth_key=key)
    prepare_paired_publication_entry(root, 0, b"receipt", auth_key=key)
    install_paired_publication_entry(root, 0, auth_key=key)
    from pneuma_lab.resampling_null.task6_state import recover_paired_publication
    recover_paired_publication(root, auth_key=key)
    assert not receipt.exists()
    assert not analysis.exists()
    assert not (root / "operational/task6/paired-publication.json").exists()


def test_paired_recovery_never_deletes_same_bytes_replacement(tmp_path) -> None:
    """Digest equality alone is not ownership of a post-crash target."""
    from pneuma_lab.foundation.artifacts import write_atomic_bytes
    from pneuma_lab.resampling_null.errors import RecordValidationError
    from pneuma_lab.resampling_null.task6_state import (
        begin_paired_publication,
        install_paired_publication_entry,
        prepare_paired_publication_entry,
        recover_paired_publication,
    )

    root = tmp_path / "run"
    root.mkdir()
    key = b"k" * 32
    receipt, analysis = root / "receipt.json", root / "analysis.json"
    begin_paired_publication(root, ((receipt, b"receipt"), (analysis, b"analysis")), auth_key=key)
    prepare_paired_publication_entry(root, 0, b"receipt", auth_key=key)
    prepare_paired_publication_entry(root, 1, b"analysis", auth_key=key)
    install_paired_publication_entry(root, 0, auth_key=key)
    receipt.unlink()
    write_atomic_bytes(receipt, b"receipt")
    with pytest.raises(RecordValidationError, match="ownership"):
        recover_paired_publication(root, auth_key=key)
    assert receipt.read_bytes() == b"receipt"


def test_paired_install_never_overwrites_a_post_preflight_creator(tmp_path) -> None:
    """The public install uses no-replace creation, not a checked-then-replace race."""
    from pneuma_lab.foundation.artifacts import write_atomic_bytes
    from pneuma_lab.resampling_null.task6_state import (
        begin_paired_publication,
        install_paired_publication_entry,
        prepare_paired_publication_entry,
    )

    root = tmp_path / "run"
    root.mkdir()
    key = b"k" * 32
    receipt, analysis = root / "receipt.json", root / "analysis.json"
    begin_paired_publication(root, ((receipt, b"receipt"), (analysis, b"analysis")), auth_key=key)
    prepare_paired_publication_entry(root, 0, b"receipt", auth_key=key)
    write_atomic_bytes(receipt, b"post-preflight creator")
    with pytest.raises(FileExistsError, match="already exists"):
        install_paired_publication_entry(root, 0, auth_key=key)
    assert receipt.read_bytes() == b"post-preflight creator"


def test_preidentity_crash_window_recovers_only_the_keyed_private_temp(monkeypatch, tmp_path) -> None:
    """A crash after O_EXCL staging but before identity journaling is recoverable."""
    import json
    import pneuma_lab.resampling_null.task6_state as state

    root = tmp_path / "run"
    root.mkdir()
    key = b"k" * 32
    receipt, analysis = root / "receipt.json", root / "analysis.json"
    state.begin_paired_publication(root, ((receipt, b"receipt"), (analysis, b"analysis")), auth_key=key)
    original = state._write_transaction
    monkeypatch.setattr(state, "_write_transaction", lambda *_a, **_k: (_ for _ in ()).throw(OSError("injected journal crash")))
    with pytest.raises(OSError, match="injected journal crash"):
        state.prepare_paired_publication_entry(root, 0, b"receipt", auth_key=key)
    intent = json.loads((root / "operational/task6/paired-publication.json").read_text(encoding="utf-8"))
    staged = root / intent["entries"][0]["temporary_relative_path"]
    assert staged.is_file()
    monkeypatch.setattr(state, "_write_transaction", original)
    state.recover_paired_publication(root, auth_key=key)
    assert not staged.exists()
    assert not (root / "operational/task6/paired-publication.json").exists()


def test_forged_or_hardlinked_preidentity_intent_never_deletes_victim(tmp_path) -> None:
    """Authenticated intent rejects forgery; keyed-temp sweep unlinks only its alias."""
    import json
    import os
    from pneuma_lab.resampling_null.errors import RecordValidationError
    import pneuma_lab.resampling_null.task6_state as state

    root = tmp_path / "run"
    root.mkdir()
    key = b"k" * 32
    receipt, analysis, victim = root / "receipt.json", root / "analysis.json", root / "victim.json"
    victim.write_bytes(b"victim")
    state.begin_paired_publication(root, ((receipt, b"receipt"), (analysis, b"analysis")), auth_key=key)
    transaction = root / "operational/task6/paired-publication.json"
    intent = json.loads(transaction.read_text(encoding="utf-8"))
    staged = root / intent["entries"][0]["temporary_relative_path"]
    os.link(victim, staged)
    forged = json.loads(transaction.read_text(encoding="utf-8"))
    forged["entries"][1]["temporary_relative_path"] = "victim.json"
    # A readable receipt permit is not the recovery capability and cannot
    # authenticate a forged cleanup plan.
    public_permit = b"p" * 32
    forged["auth_hmac_sha256"] = state._transaction_mac(forged, public_permit)
    transaction.write_text(json.dumps(forged), encoding="utf-8")
    with pytest.raises(RecordValidationError, match="authentication"):
        state.recover_paired_publication(root, auth_key=key)
    assert victim.read_bytes() == b"victim"
    assert staged.exists()


def test_receipt_only_unblind_entrypoint_is_not_public() -> None:
    """No compatibility route may reintroduce the orphan-receipt defect."""
    import pneuma_lab.resampling_null.blinding as blinding

    assert not hasattr(blinding, "unblind_projection")
