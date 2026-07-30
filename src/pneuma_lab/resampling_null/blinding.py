"""Trusted projection sealing and unblind-permit framing."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, cast

from .artifacts import _load_direct_scientific_parent, write_record
from .assignment import BytesField, TextField, _derive_unblind_subkey_into, _read_exact_master_into, commitment_sha256, kdf_frame
from .errors import RecordValidationError
from .projection_candidate import ProjectionCandidate, build_candidate
from .secrets import UnblindSecretHandle, _require_handle_binding
from .types import ArtifactRef


def _mapping_ref(ref: ArtifactRef) -> dict[str, object]:
    return {"role": ref.role, "relative_path": ref.relative_path, "sha256": ref.sha256, "byte_count": ref.byte_count, "media_type": ref.media_type}


def seal_blinded_projection(
    *, run_root: Path, destination: Path, schedule_ref: ArtifactRef,
    analysis_freeze_ref: ArtifactRef, task_block_refs: tuple[ArtifactRef, ...],
    candidate: ProjectionCandidate,
) -> ArtifactRef:
    """Reload authoritative parents and publish one reconstructed projection."""
    schedule = _load_direct_scientific_parent(_mapping_ref(schedule_ref), run_root=run_root, field="schedule_ref", expected_kind="resampling_prefix_schedule")
    freeze = _load_direct_scientific_parent(_mapping_ref(analysis_freeze_ref), run_root=run_root, field="analysis_freeze_ref", expected_kind="resampling_analysis_freeze")
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
        outcomes[task_id] = cast(list[Mapping[str, object]], payload["slot_outcomes"])
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


def _framed_unblind_permit(
    handle: UnblindSecretHandle, *, study_id: str, manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef, prefix_index_ref: ArtifactRef, ledger_ref: ArtifactRef,
    projection_ref: ArtifactRef, freeze_ref: ArtifactRef, expected_task_count: int,
) -> str:
    """Consume a fresh unblind handle and return its context-bound permit MAC."""
    if type(handle) is not UnblindSecretHandle or type(expected_task_count) is not int or expected_task_count < 0:
        raise ValueError("unblind permit requires fresh exact context")
    master = bytearray(32)
    key = bytearray(32)
    try:
        _read_exact_master_into(handle, master)
        _derive_unblind_subkey_into(memoryview(master), study_id, manifest_ref, schedule_ref, key)
        frame = kdf_frame("unblind-permit-v1", [TextField(study_id), BytesField(bytes.fromhex(manifest_ref.sha256)), BytesField(bytes.fromhex(schedule_ref.sha256)), BytesField(bytes.fromhex(prefix_index_ref.sha256)), BytesField(bytes.fromhex(ledger_ref.sha256)), BytesField(bytes.fromhex(projection_ref.sha256)), BytesField(bytes.fromhex(freeze_ref.sha256)), TextField(str(expected_task_count))])
        return hmac.new(key, frame, hashlib.sha256).hexdigest()
    finally:
        master[:] = b"\x00" * len(master)
        key[:] = b"\x00" * len(key)


@dataclass(frozen=True, slots=True)
class UnblindResult:
    receipt_ref: ArtifactRef
    rows: tuple[dict[str, object], ...]


def _validated_permit(
    handle: UnblindSecretHandle, *, run_root: Path, manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef, prefix_index_ref: ArtifactRef, ledger_ref: ArtifactRef,
    projection_ref: ArtifactRef, freeze_ref: ArtifactRef, expected_task_count: int,
) -> tuple[str, Mapping[str, object], Mapping[str, object]]:
    """Validate all non-clear parents and consume exactly one unblind handle."""
    manifest = _load_direct_scientific_parent(_mapping_ref(manifest_ref), run_root=run_root, field="manifest_ref", expected_kind="resampling_study_manifest")
    schedule = _load_direct_scientific_parent(_mapping_ref(schedule_ref), run_root=run_root, field="schedule_ref", expected_kind="resampling_prefix_schedule")
    prefix = _load_direct_scientific_parent(_mapping_ref(prefix_index_ref), run_root=run_root, field="prefix_index_ref", expected_kind="resampling_prefix_receipt")
    freeze = _load_direct_scientific_parent(_mapping_ref(freeze_ref), run_root=run_root, field="freeze_ref", expected_kind="resampling_analysis_freeze")
    projection = _load_direct_scientific_parent(_mapping_ref(projection_ref), run_root=run_root, field="projection_ref", expected_kind="resampling_blinded_projection")
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
    ledger = _load_direct_scientific_parent(_mapping_ref(ledger_ref), run_root=run_root, field="ledger_ref", expected_kind="resampling_assignment_ledger")
    if cast(Mapping[str, object], ledger.value["payload"]).get("manifest_ref") != _mapping_ref(manifest_ref) or cast(Mapping[str, object], ledger.value["payload"]).get("schedule_ref") != _mapping_ref(schedule_ref):
        raise RecordValidationError("ledger does not descend from permit context")
    return permit


def unblind_projection(
    handle: UnblindSecretHandle, *, permit_hmac_sha256: str, run_root: Path,
    receipt_destination: Path, manifest_ref: ArtifactRef, schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef, ledger_ref: ArtifactRef, projection_ref: ArtifactRef,
    freeze_ref: ArtifactRef, expected_task_count: int,
) -> UnblindResult:
    """Verify a permit before loading the clear ledger and publish first receipt."""
    # This consumes the independently minted handle before any clear-ledger read.
    actual, projection_payload, manifest = _validated_permit(handle, run_root=run_root, manifest_ref=manifest_ref, schedule_ref=schedule_ref, prefix_index_ref=prefix_index_ref, ledger_ref=ledger_ref, projection_ref=projection_ref, freeze_ref=freeze_ref, expected_task_count=expected_task_count)
    if not hmac.compare_digest(actual, permit_hmac_sha256):
        raise RecordValidationError("unblind permit MAC does not match")
    ledger = _load_direct_scientific_parent(_mapping_ref(ledger_ref), run_root=run_root, field="ledger_ref", expected_kind="resampling_assignment_ledger")
    arms = {row["task_id"]: dict(row["slot_arms"]) for row in cast(list[Mapping[str, object]], cast(Mapping[str, object], ledger.value["payload"])["assignments"])}
    clear_rows = []
    for row in cast(list[Mapping[str, object]], projection_payload["rows"]):
        slot_arms = arms.get(cast(str, row["task_id"]))
        if slot_arms is None:
            raise RecordValidationError("ledger does not cover blinded projection")
        clear_rows.append({**dict(row), "slots": [{**dict(slot), "arm": slot_arms[slot["slot_id"]]} for slot in cast(list[Mapping[str, object]], row["slots"])]})
    record = {"record_kind": "resampling_unblind_receipt", "schema_version": "0.1.0", "study_id": ledger.value["study_id"], "frozen_created_at": ledger.value["frozen_created_at"], "provenance": ledger.value["provenance"], "payload": {"projection_ref": _mapping_ref(projection_ref), "assignment_ledger_ref": _mapping_ref(ledger_ref), "analysis_freeze_ref": _mapping_ref(freeze_ref), "expected_task_count": expected_task_count, "permit_hmac_sha256": actual}}
    receipt = write_record(receipt_destination, record, run_root=run_root, role="unblind_receipt")
    return UnblindResult(receipt_ref=receipt, rows=tuple(clear_rows))
