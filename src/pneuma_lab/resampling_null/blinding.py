"""Trusted projection sealing and unblind-permit framing."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, cast

from .artifacts import (
    _load_direct_scientific_parent,
    _prepare_destination,
    _require_manifest_ancestry,
    _read_ref,
    validate_record,
    validate_preunblind_graph,
    validate_scientific_graph,
    write_record,
)
from .assignment import (BytesField, TextField, _derive_pair_recovery_subkey_into,
                         _derive_unblind_subkey_into, _read_exact_master_into,
                         commitment_sha256, kdf_frame)
from .errors import RecordValidationError
from .projection_candidate import ProjectionCandidate, build_candidate
from .secrets import UnblindSecretHandle, _require_handle_binding
from .freeze import CurrentAnalysisInputs, verify_current_analysis_inputs, verify_frozen_analysis_inputs
from .task6_state import (
    abort_paired_publication,
    begin_paired_publication,
    install_paired_publication_entry,
    mark_outcome_tainted,
    prepare_paired_publication_entry,
    recover_paired_publication,
    require_singleton_absent,
    task6_controller_lock,
)
from .types import ArtifactRef
from pneuma_lab.foundation.artifacts import canonical_json_bytes


def _mapping_ref(ref: ArtifactRef) -> dict[str, object]:
    return {"role": ref.role, "relative_path": ref.relative_path, "sha256": ref.sha256, "byte_count": ref.byte_count, "media_type": ref.media_type}


def seal_blinded_projection(
    *, run_root: Path, destination: Path, schedule_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef, task_block_refs: tuple[ArtifactRef, ...],
    candidate: ProjectionCandidate,
) -> ArtifactRef:
    """Reload authoritative parents and publish one reconstructed projection."""
    # The lock covers discovery and install, so an alternate destination cannot
    # manufacture a second singleton between check and write.
    with task6_controller_lock(run_root) as root:
        require_singleton_absent(root, "resampling_blinded_projection")
        validate_scientific_graph(root)
        return _seal_blinded_projection_locked(
            run_root=root, destination=destination, schedule_ref=schedule_ref,
            analysis_freeze_ref=analysis_freeze_ref, task_block_refs=task_block_refs,
            candidate=candidate,
        )


def _seal_blinded_projection_locked(
    *, run_root: Path, destination: Path, schedule_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef, task_block_refs: tuple[ArtifactRef, ...],
    candidate: ProjectionCandidate,
) -> ArtifactRef:
    schedule = _load_direct_scientific_parent(_mapping_ref(schedule_ref), run_root=run_root, field="schedule_ref", expected_kind="resampling_prefix_schedule")
    freeze = _load_direct_scientific_parent(_mapping_ref(analysis_freeze_ref), run_root=run_root, field="analysis_freeze_ref", expected_kind="resampling_analysis_freeze")
    verify_frozen_analysis_inputs(analysis_freeze_ref, run_root=run_root)
    blocks = [_load_direct_scientific_parent(_mapping_ref(ref), run_root=run_root, field="task_block_ref", expected_kind="resampling_task_block") for ref in task_block_refs]
    by_task = {cast(str, cast(Mapping[str, object], block.value["payload"])["task_id"]): block for block in blocks}
    schedule_rows = cast(list[Mapping[str, object]], cast(Mapping[str, object], schedule.value["payload"])["tasks"])
    frozen = []
    outcomes = {}
    rows = []
    for entry in schedule_rows:
        task = cast(Mapping[str, object], entry["task"])
        task_id = cast(str, task["task_id"])
        block = by_task.get(task_id)
        if block is None:
            raise RecordValidationError("task blocks must exactly cover the schedule")
        payload = cast(Mapping[str, object], block.value["payload"])
        slots = cast(list[Mapping[str, object]], entry["slots"])
        frozen.append({"task_id": task_id, "prefix_success": payload["prefix_success"], "slot_ids": [slot["slot_id"] for slot in slots]})
        raw_outcomes = payload["slot_outcomes"]
        if not isinstance(raw_outcomes, list) or len(raw_outcomes) != 4:
            raise RecordValidationError("task block slot outcomes are malformed")
        outcomes[task_id] = [
            {
                "success": outcome.get("success"),
                "prefix_success": outcome.get("prefix_success"),
                "partial_reward": outcome.get("partial_reward"),
                "infrastructure_failure": outcome.get("infrastructure_failure"),
                "counters": outcome.get("counters"),
            }
            for outcome in raw_outcomes
            if isinstance(outcome, Mapping)
        ]
        if len(outcomes[task_id]) != 4:
            raise RecordValidationError("task block slot outcomes are malformed")
    rebuilt_candidate = build_candidate(frozen, outcomes)
    if (
        type(candidate) is not ProjectionCandidate
        or candidate.canonical_bytes != rebuilt_candidate.canonical_bytes
    ):
        raise RecordValidationError(
            "caller candidate bytes differ from trusted reconstruction"
        )
    candidate = rebuilt_candidate
    for index, base in enumerate(candidate.rows):
        task_id = cast(str, base["task_id"])
        schedule_entry = schedule_rows[index]
        task = cast(Mapping[str, object], schedule_entry["task"])
        payload = cast(Mapping[str, object], by_task[task_id].value["payload"])
        rows.append({
            "task_id": task_id, "benchmark": payload["benchmark"], "stratum": payload["stratum"],
            "lineage": task["lineage"], "sensitivity_groups": payload["sensitivity_groups"],
            "prefix_success": base["prefix_success"], "triggered": payload["triggered"],
            "slots": base["slots"], "pipeline_valid": payload["pipeline_valid"],
            "validity_codes": payload["validity_codes"],
        })
    if set(by_task) != {cast(str, cast(Mapping[str, object], row["task"])["task_id"]) for row in schedule_rows}:
        raise RecordValidationError("task blocks must exactly cover the schedule")
    record = {
        "record_kind": "resampling_blinded_projection", "schema_version": "0.1.0",
        "study_id": schedule.value["study_id"], "frozen_created_at": schedule.value["frozen_created_at"], "provenance": schedule.value["provenance"],
        "payload": {"schedule_ref": _mapping_ref(schedule_ref), "analysis_freeze_ref": _mapping_ref(analysis_freeze_ref), "task_block_refs": [_mapping_ref(ref) for ref in task_block_refs], "rows": rows, "projection_candidate_sha256": candidate.sha256, "expected_task_count": len(rows), "complete": True},
    }
    if freeze.value["study_id"] != schedule.value["study_id"]:
        raise RecordValidationError("freeze and schedule have different study identities")
    return write_record(destination, record, run_root=run_root, role="blinded_projection")


@dataclass(frozen=True, slots=True)
class UnblindResult:
    receipt_ref: ArtifactRef
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class PairedUnblindResult:
    """The sole public result of a completed unblind-and-analysis transaction."""

    receipt_ref: ArtifactRef
    analysis_ref: ArtifactRef


@dataclass(frozen=True, slots=True)
class _UnblindStage:
    receipt_record: Mapping[str, object]
    rows: tuple[dict[str, object], ...]


def _validated_permit(
    handle: UnblindSecretHandle, *, run_root: Path, manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef, prefix_index_ref: ArtifactRef, ledger_ref: ArtifactRef,
    projection_ref: ArtifactRef, freeze_ref: ArtifactRef, expected_task_count: int,
) -> tuple[str, Mapping[str, object], Mapping[str, object]]:
    """Validate every non-clear parent before the clear-ledger parser runs."""
    manifest = _load_direct_scientific_parent(_mapping_ref(manifest_ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest")
    schedule = _load_direct_scientific_parent(_mapping_ref(schedule_ref), run_root=run_root, field="schedule_ref", expected_kind="resampling_prefix_schedule")
    prefix = _load_direct_scientific_parent(_mapping_ref(prefix_index_ref), run_root=run_root, field="prefix_index_ref", expected_kind="resampling_prefix_receipt")
    freeze = _load_direct_scientific_parent(_mapping_ref(freeze_ref), run_root=run_root, field="freeze_ref", expected_kind="resampling_analysis_freeze")
    projection = _load_direct_scientific_parent(_mapping_ref(projection_ref), run_root=run_root, field="projection_ref", expected_kind="resampling_blinded_projection")
    # This checks the exact ledger bytes and digest before any JSON decode of it.
    _read_ref(ledger_ref, run_root=run_root)
    verify_frozen_analysis_inputs(freeze_ref, run_root=run_root)
    schedule_payload = cast(Mapping[str, object], schedule.value["payload"])
    projection_payload = cast(Mapping[str, object], projection.value["payload"])
    if schedule_payload.get("manifest_ref") != _mapping_ref(manifest_ref) or cast(Mapping[str, object], prefix.value["payload"]).get("schedule_ref") != _mapping_ref(schedule_ref) or projection_payload.get("schedule_ref") != _mapping_ref(schedule_ref) or projection_payload.get("analysis_freeze_ref") != _mapping_ref(freeze_ref) or projection_payload.get("expected_task_count") != expected_task_count or projection_payload.get("complete") is not True:
        raise RecordValidationError("unblind context ancestry is incomplete")
    _require_handle_binding(handle, manifest_ref, schedule_ref, run_root=run_root, purpose="unblind")
    master, key = bytearray(32), bytearray(32)
    try:
        _read_exact_master_into(handle, master)
        if commitment_sha256("assignment-master-key", str(manifest.value["study_id"]), BytesField(bytes(master))) != cast(Mapping[str, object], manifest.value["payload"])["assignment_master_key_commitment_sha256"]:
            raise RecordValidationError("master commitment does not match manifest")
        _derive_unblind_subkey_into(memoryview(master), str(manifest.value["study_id"]), manifest_ref, schedule_ref, key)
        frame = kdf_frame("unblind-permit-v1", [TextField(str(manifest.value["study_id"])), BytesField(bytes.fromhex(manifest_ref.sha256)), BytesField(bytes.fromhex(schedule_ref.sha256)), BytesField(bytes.fromhex(prefix_index_ref.sha256)), BytesField(bytes.fromhex(ledger_ref.sha256)), BytesField(bytes.fromhex(projection_ref.sha256)), BytesField(bytes.fromhex(freeze_ref.sha256)), TextField(str(expected_task_count))])
        return hmac.new(key, frame, hashlib.sha256).hexdigest(), projection_payload, manifest.value
    finally:
        master[:] = b"\x00" * len(master)
        key[:] = b"\x00" * len(key)


def issue_unblind_permit(
    handle: UnblindSecretHandle, *, run_root: Path, manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef, prefix_index_ref: ArtifactRef, ledger_ref: ArtifactRef,
    projection_ref: ArtifactRef, freeze_ref: ArtifactRef, expected_task_count: int,
) -> str:
    """Issue a one-use permit after independently validating public ancestry."""
    permit, _projection, _manifest = _validated_permit(handle, run_root=run_root, manifest_ref=manifest_ref, schedule_ref=schedule_ref, prefix_index_ref=prefix_index_ref, ledger_ref=ledger_ref, projection_ref=projection_ref, freeze_ref=freeze_ref, expected_task_count=expected_task_count)
    return permit


def _validate_ledger_ancestry(
    ledger_ref: ArtifactRef, *, run_root: Path, manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef, prefix_index_ref: ArtifactRef,
) -> Mapping[str, object]:
    """Parse clear ledger only after its raw ref and public context are verified."""
    ledger = _load_direct_scientific_parent(
        _mapping_ref(ledger_ref), run_root=run_root, field="ledger_ref",
        expected_kind="resampling_assignment_ledger",
    )
    payload = cast(Mapping[str, object], ledger.value["payload"])
    if (
        payload.get("manifest_ref") != _mapping_ref(manifest_ref)
        or payload.get("schedule_ref") != _mapping_ref(schedule_ref)
        or payload.get("prefix_index_ref") != _mapping_ref(prefix_index_ref)
    ):
        raise RecordValidationError("ledger does not descend from complete unblind context")
    return ledger.value


def _stage_unblind_projection_locked(
    handle: UnblindSecretHandle, *, permit_hmac_sha256: str, root: Path,
    manifest_ref: ArtifactRef, schedule_ref: ArtifactRef, prefix_index_ref: ArtifactRef,
    ledger_ref: ArtifactRef, projection_ref: ArtifactRef, freeze_ref: ArtifactRef,
    expected_task_count: int, current_analysis_inputs: CurrentAnalysisInputs,
) -> _UnblindStage:
    """Cross the clear-ledger boundary, retaining all clear rows only in RAM."""
    # This intentionally excludes the opaque ledger: graph validation must
    # precede every ledger open/decode, while the permit validates its raw
    # digest and binding before the full graph is allowed to inspect it.
    validate_preunblind_graph(root, ledger_ref)
    verify_current_analysis_inputs(
        freeze_ref, run_root=root, inputs=current_analysis_inputs,
    )
    actual, projection_payload, _manifest = _validated_permit(
        handle, run_root=root, manifest_ref=manifest_ref,
        schedule_ref=schedule_ref, prefix_index_ref=prefix_index_ref,
        ledger_ref=ledger_ref, projection_ref=projection_ref,
        freeze_ref=freeze_ref, expected_task_count=expected_task_count,
    )
    if not hmac.compare_digest(actual, permit_hmac_sha256):
        raise RecordValidationError("unblind permit MAC does not match")
    # Taint is intentionally before the first ledger decode.  A crash or
    # later full-graph validation failure therefore cannot reset a context
    # that began to expose assignment/outcome information.
    mark_outcome_tainted(root)
    validate_scientific_graph(root)
    ledger_value = _validate_ledger_ancestry(
        ledger_ref, run_root=root, manifest_ref=manifest_ref,
        schedule_ref=schedule_ref, prefix_index_ref=prefix_index_ref,
    )
    arms = {row["task_id"]: dict(row["slot_arms"]) for row in cast(list[Mapping[str, object]], cast(Mapping[str, object], ledger_value["payload"])["assignments"])}
    clear_rows = []
    for row in cast(list[Mapping[str, object]], projection_payload["rows"]):
        slot_arms = arms.get(cast(str, row["task_id"]))
        if slot_arms is None:
            raise RecordValidationError("ledger does not cover blinded projection")
        clear_rows.append({**dict(row), "slots": [{**dict(slot), "arm": slot_arms[slot["slot_id"]]} for slot in cast(list[Mapping[str, object]], row["slots"])]})
    receipt_record = {
        "record_kind": "resampling_unblind_receipt", "schema_version": "0.1.0",
        "study_id": ledger_value["study_id"], "frozen_created_at": ledger_value["frozen_created_at"],
        "provenance": ledger_value["provenance"],
        "payload": {
            "projection_ref": _mapping_ref(projection_ref),
            "assignment_ledger_ref": _mapping_ref(ledger_ref),
            "analysis_freeze_ref": _mapping_ref(freeze_ref),
            "expected_task_count": expected_task_count, "permit_hmac_sha256": actual,
        },
    }
    return _UnblindStage(receipt_record=receipt_record, rows=tuple(clear_rows))


def _ref_for_prepared_record(
    record: Mapping[str, object], *, run_root: Path, relative_path: str, role: str,
) -> tuple[Mapping[str, object], ArtifactRef, bytes]:
    """Validate a not-yet-published record and bind the reference to its bytes."""
    validated = validate_record(record)
    _require_manifest_ancestry(validated, run_root=run_root)
    payload = canonical_json_bytes(validated, indent=4)
    return validated, ArtifactRef(
        role=role, relative_path=relative_path,
        sha256=hashlib.sha256(payload).hexdigest(), byte_count=len(payload),
        media_type="application/json",
    ), payload


def _pair_transaction_key(
    handle: UnblindSecretHandle, *, run_root: Path, manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
) -> bytes:
    """Derive a capability-only recovery key; permits are deliberately public receipts."""
    manifest = _load_direct_scientific_parent(
        _mapping_ref(manifest_ref), run_root=run_root, field="manifest_ref",
        expected_kind="resampling_study_manifest",
    )
    _require_handle_binding(handle, manifest_ref, schedule_ref, run_root=run_root, purpose="unblind")
    master, pair_key = bytearray(32), bytearray(32)
    try:
        _read_exact_master_into(handle, master)
        if commitment_sha256("assignment-master-key", str(manifest.value["study_id"]), BytesField(bytes(master))) != cast(Mapping[str, object], manifest.value["payload"])["assignment_master_key_commitment_sha256"]:
            raise RecordValidationError("master commitment does not match manifest")
        _derive_pair_recovery_subkey_into(memoryview(master), str(manifest.value["study_id"]), manifest_ref, schedule_ref, pair_key)
        return bytes(pair_key)
    finally:
        master[:] = b"\x00" * len(master)
        pair_key[:] = b"\x00" * len(pair_key)


def unblind_and_publish_analysis(
    handle: UnblindSecretHandle, *, recovery_handle: UnblindSecretHandle,
    permit_hmac_sha256: str, run_root: Path,
    receipt_destination: Path, analysis_destination: Path, manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef, prefix_index_ref: ArtifactRef, ledger_ref: ArtifactRef,
    projection_ref: ArtifactRef, freeze_ref: ArtifactRef, expected_task_count: int,
    current_analysis_inputs: CurrentAnalysisInputs,
    analysis_builder: Callable[[UnblindResult], Mapping[str, object]],
) -> PairedUnblindResult:
    """Publish receipt and analysis together only after in-memory analysis succeeds.

    This is a recoverable all-or-none controller transaction: destinations are
    preflighted before taint, no clear rows leave memory before the builder has
    completed, and publication failure removes every target written in this
    call.  The controller lock prevents a second Task-6 writer from observing
    a partial pair.
    """
    with task6_controller_lock(run_root) as root:
        transaction_key = _pair_transaction_key(
            recovery_handle, run_root=root, manifest_ref=manifest_ref,
            schedule_ref=schedule_ref,
        )
        recover_paired_publication(root, auth_key=transaction_key)
        require_singleton_absent(root, "resampling_unblind_receipt")
        receipt_target, receipt_relative = _prepare_destination(receipt_destination, root)
        analysis_target, analysis_relative = _prepare_destination(analysis_destination, root)
        if receipt_target == analysis_target:
            raise RecordValidationError("unblind receipt and analysis destinations must differ")
        stage = _stage_unblind_projection_locked(
            handle, permit_hmac_sha256=permit_hmac_sha256, root=root,
            manifest_ref=manifest_ref, schedule_ref=schedule_ref,
            prefix_index_ref=prefix_index_ref, ledger_ref=ledger_ref,
            projection_ref=projection_ref, freeze_ref=freeze_ref,
            expected_task_count=expected_task_count,
            current_analysis_inputs=current_analysis_inputs,
        )
        receipt_record, receipt_ref, receipt_bytes = _ref_for_prepared_record(
            stage.receipt_record, run_root=root,
            relative_path=receipt_relative, role="unblind_receipt",
        )
        analysis_record = analysis_builder(UnblindResult(receipt_ref, stage.rows))
        _analysis_record, analysis_ref, analysis_bytes = _ref_for_prepared_record(
            analysis_record, run_root=root, relative_path=analysis_relative,
            role="analysis",
        )
        analysis_payload = cast(Mapping[str, object], _analysis_record["payload"])
        if analysis_payload.get("unblind_receipt_ref") != _mapping_ref(receipt_ref):
            raise RecordValidationError("analysis does not bind the paired unblind receipt")
        begin_paired_publication(
            root, ((receipt_target, receipt_bytes), (analysis_target, analysis_bytes)),
            auth_key=transaction_key,
        )
        try:
            prepare_paired_publication_entry(root, 0, receipt_bytes, auth_key=transaction_key)
            prepare_paired_publication_entry(root, 1, analysis_bytes, auth_key=transaction_key)
            install_paired_publication_entry(root, 0, auth_key=transaction_key)
            install_paired_publication_entry(root, 1, auth_key=transaction_key)
        except BaseException:
            abort_paired_publication(root, auth_key=transaction_key)
            raise
        recover_paired_publication(root, auth_key=transaction_key)
        return PairedUnblindResult(receipt_ref=receipt_ref, analysis_ref=analysis_ref)
