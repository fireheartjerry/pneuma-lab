"""Milestone claims: sealed opaque packet capabilities never expose an arm."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.packet_capabilities import (
    OpaqueSlotGrant,
    SealedSlotCapability,
    SlotArtifactLoader,
    TaskPacketCapabilities,
    opaque_guidance_relative_path,
    require_arm_opaque_relative_path,
    require_canonical_guidance_path,
    resolve_packet_capabilities,
    seal_slot_capability,
)
from pneuma_lab.resampling_null.types import (
    ArtifactRef,
    BranchCaps,
    OpaqueSlotIdentity,
    OpaqueSlotWorkOrder,
)


pytestmark = pytest.mark.milestone


_STUDY = "study-synthetic"
_FROZEN = "2026-07-30T00:00:00Z"
_PROVENANCE = {"design_sha256": "1" * 64, "code_sha256": "2" * 64}
_CAPS = ("a" * 64, "b" * 64, "c" * 64, "d" * 64)
_SLOTS = ("slot-0", "slot-1", "slot-2", "slot-3")


def _write(root: Path, name: str, payload: bytes, *, role: str, media: str) -> ArtifactRef:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return ArtifactRef(
        role=role,
        relative_path=name,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type=media,
    )


def _write_json(root: Path, name: str, value: object, *, role: str) -> ArtifactRef:
    payload = json.dumps(value, sort_keys=True, indent=2).encode("utf-8")
    return _write(root, name, payload, role=role, media="application/json")


def _envelope(payload: dict[str, object]) -> dict[str, object]:
    return {
        "record_kind": "resampling_packet_index",
        "schema_version": "0.1.0",
        "study_id": _STUDY,
        "frozen_created_at": _FROZEN,
        "provenance": dict(_PROVENANCE),
        "payload": payload,
    }


def _build_root(
    root: Path,
    *,
    arms: tuple[str, str, str, str] = ("REAL", "SHAM", "NONE", "RESAMPLE"),
    real_path: str | None = None,
    sham_path: str | None = None,
    triggered: bool = True,
    entry_overrides: dict[str, object] | None = None,
    candidate_study_id: str | None = None,
) -> ArtifactRef:
    """Write one minimal sealed/candidate/ledger triple for a single task."""

    task_id = "task-1"
    arm_slots = list(zip(_SLOTS, arms, strict=True))
    capability_by_slot = dict(zip(_SLOTS, _CAPS, strict=True))
    real_slot = next(slot for slot, arm in arm_slots if arm == "REAL")
    sham_slot = next(slot for slot, arm in arm_slots if arm == "SHAM")
    real_relative = real_path or opaque_guidance_relative_path(
        task_id, capability_by_slot[real_slot]
    )
    sham_relative = sham_path or opaque_guidance_relative_path(
        task_id, capability_by_slot[sham_slot]
    )
    prefix_ref = _write_json(
        root, "prefix-index.json", {"stub": "prefix"}, role="resampling_prefix_receipt"
    )
    ledger = {
        "record_kind": "resampling_assignment_ledger",
        "schema_version": "0.1.0",
        "study_id": _STUDY,
        "frozen_created_at": _FROZEN,
        "provenance": dict(_PROVENANCE),
        "payload": {
            "prefix_index_ref": _ref_value(prefix_ref),
            "assignments": [
                {
                    "task_id": task_id,
                    "donor_match_kind": (
                        "matched" if triggered else "not_applicable_no_trigger"
                    ),
                    "donor_task_id": "task-2" if triggered else None,
                    "slot_arms": [list(pair) for pair in arm_slots],
                }
            ],
            "allocation_receipts": [
                {
                    "task_id": task_id,
                    "slot_ids_by_ordinal": list(_SLOTS),
                    "slot_capabilities": [
                        [slot, capability_by_slot[slot]] for slot in _SLOTS
                    ],
                }
            ],
        },
    }
    ledger_ref = _write_json(
        root, "assignment.json", ledger, role="resampling_assignment_ledger"
    )
    if triggered:
        real_guidance = _write(
            root, real_relative, b"real-packet", role="private_guidance", media="text/plain"
        )
        sham_guidance = _write(
            root, sham_relative, b"sham-packet", role="private_guidance", media="text/plain"
        )
        entry: dict[str, object] = {
            "task_id": task_id,
            "donor_task_id": "task-2",
            "prefix_index_sha256": prefix_ref.sha256,
            "real_ref": _ref_value(real_guidance),
            "sham_ref": _ref_value(sham_guidance),
        }
    else:
        entry = {
            "task_id": task_id,
            "prefix_index_sha256": prefix_ref.sha256,
            "trigger_reason": "no_intervention_opportunity",
        }
    if entry_overrides is not None:
        entry.update(entry_overrides)
    candidate_envelope = _envelope(
        {
            "stage": "candidate",
            "assignment_ref": _ref_value(ledger_ref),
            "prefix_index_ref": _ref_value(prefix_ref),
            "entries": [entry],
        }
    )
    if candidate_study_id is not None:
        candidate_envelope["study_id"] = candidate_study_id
    candidate_ref = _write_json(
        root, "packet-candidate.json", candidate_envelope, role="packet_index_candidate"
    )
    return _write_json(
        root,
        "packet-sealed.json",
        _envelope(
            {
                "stage": "sealed",
                "candidate_ref": _ref_value(candidate_ref),
                "assignment_ref": _ref_value(ledger_ref),
                "prefix_index_ref": _ref_value(prefix_ref),
            }
        ),
        role="packet_index_sealed",
    )


def _ref_value(ref: ArtifactRef) -> dict[str, object]:
    return {
        "role": ref.role,
        "relative_path": ref.relative_path,
        "sha256": ref.sha256,
        "byte_count": ref.byte_count,
        "media_type": ref.media_type,
    }


def test_canonical_guidance_name_is_a_pure_capability_function() -> None:
    first = opaque_guidance_relative_path("task-1", "b" * 64)
    assert first == opaque_guidance_relative_path("task-1", "b" * 64)
    assert first != opaque_guidance_relative_path("task-2", "b" * 64)
    assert first != opaque_guidance_relative_path("task-1", "c" * 64)
    assert "real" not in first and "sham" not in first
    with pytest.raises(RecordValidationError, match="SHA-256"):
        opaque_guidance_relative_path("task-1", "not-a-digest")


def test_arm_opaque_gate_rejects_every_arm_word_regardless_of_delimiter() -> None:
    revealing = (
        "packet-work/private-real.txt",
        "packet-work/private_sham.txt",
        "packet-work/private REAL.txt",
        "packet-work/guidance(SHAM).txt",
        "packet-work/arm=NONE.txt",
        "packet-work/type@RESAMPLE.txt",
        "packet-work/realPacket.txt",
        "packet-work/shamish/guidance.txt",
    )
    for path in revealing:
        with pytest.raises(RecordValidationError, match="arm-opaque"):
            require_arm_opaque_relative_path(path, field="path")
    # Every arm word contains a non-hex character, so no lowercase-hex
    # component and neither literal component of the canonical name can trip it.
    assert require_arm_opaque_relative_path(
        opaque_guidance_relative_path("task-1", "a" * 64), field="path"
    )


def test_canonical_guidance_gate_is_a_whitelist_not_a_blacklist() -> None:
    assert require_canonical_guidance_path(
        opaque_guidance_relative_path("task-1", "a" * 64), field="path"
    )
    for path in (
        "packet-work/abc/guidance-" + "a" * 64 + ".txt",
        "packet-work/" + "a" * 64 + "/guidance-" + "a" * 63 + ".txt",
        "other/" + "a" * 64 + "/guidance-" + "a" * 64 + ".txt",
        "packet-work/" + "a" * 64 + "/guidance-" + "a" * 64 + ".json",
    ):
        with pytest.raises(RecordValidationError, match="canonical guidance name"):
            require_canonical_guidance_path(path, field="path")


def test_task_capabilities_close_the_packet_bearing_slot_count() -> None:
    grants = tuple(
        OpaqueSlotGrant(slot, capability, None)
        for slot, capability in zip(_SLOTS, _CAPS, strict=True)
    )
    assert TaskPacketCapabilities("task-1", False, grants).triggered is False
    with pytest.raises(RecordValidationError, match="exactly two"):
        TaskPacketCapabilities("task-1", True, grants)
    ref = ArtifactRef(
        "private_guidance",
        opaque_guidance_relative_path("task-1", _CAPS[0]),
        "e" * 64,
        4,
        "text/plain",
    )
    granted = (OpaqueSlotGrant(_SLOTS[0], _CAPS[0], ref), *grants[1:])
    with pytest.raises(RecordValidationError, match="no packet-bearing slot"):
        TaskPacketCapabilities("task-1", False, granted)
    with pytest.raises(RecordValidationError, match="arm-opaque"):
        OpaqueSlotGrant(
            _SLOTS[0],
            _CAPS[0],
            ArtifactRef(
                "private_guidance", "packet-work/private-real.txt", "e" * 64, 4, "text/plain"
            ),
        )


def test_resolution_maps_arms_onto_preregistered_slot_order(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(root, arms=("NONE", "REAL", "SHAM", "RESAMPLE"))
    resolved = resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)
    assert len(resolved) == 1
    task = resolved[0]
    assert task.task_id == "task-1" and task.triggered is True
    assert [grant.slot_id for grant in task.grants] == list(_SLOTS)
    assert [grant.guidance_ref is not None for grant in task.grants] == [
        False,
        True,
        True,
        False,
    ]
    for grant in task.grants:
        if grant.guidance_ref is None:
            continue
        assert grant.guidance_ref.relative_path == opaque_guidance_relative_path(
            "task-1", grant.opaque_capability_id
        )
    # Serialize the complete returned record, including every guidance ref
    # field, so the assertion cannot pass by omitting the leak surface.
    serialized = json.dumps(
        [
            [
                grant.slot_id,
                grant.opaque_capability_id,
                None if grant.guidance_ref is None else _ref_value(grant.guidance_ref),
            ]
            for grant in task.grants
        ]
    )
    for token in ("REAL", "SHAM", "RESAMPLE", "NONE", "task-2", "donor"):
        assert token not in serialized
    assert "real" not in serialized.lower() and "sham" not in serialized.lower()


def test_resolution_rejects_a_packet_bound_to_the_wrong_capability(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    # Hand the REAL packet the SHAM slot's canonical capability name.
    sealed = _build_root(
        root,
        real_path=opaque_guidance_relative_path("task-1", _CAPS[1]),
        sham_path=opaque_guidance_relative_path("task-1", _CAPS[2]),
    )
    with pytest.raises(RecordValidationError, match="allocated slot capability"):
        resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)


def test_resolution_rejects_the_legacy_arm_labelled_guidance_path(
    tmp_path: Path,
) -> None:
    """The old `private-real` writer output cannot enter a slot grant."""
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(root, real_path="packet-work/private-real.txt")
    with pytest.raises(RecordValidationError, match="arm-opaque"):
        resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)


def test_resolution_covers_a_no_intervention_task_without_any_packet(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(root, triggered=False)
    resolved = resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)
    assert resolved[0].triggered is False
    assert all(grant.guidance_ref is None for grant in resolved[0].grants)


def test_slot_loader_reads_only_its_sealed_reference_set(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    permitted = _write(
        root,
        opaque_guidance_relative_path("task-1", _CAPS[0]),
        b"guidance",
        role="private_guidance",
        media="text/plain",
    )
    forbidden = _write(
        root, "assignment.json", b"{}", role="resampling_assignment_ledger", media="application/json"
    )
    capability = SealedSlotCapability(_CAPS[0], (permitted,))
    with SlotArtifactLoader(capability, run_root=root) as loader:
        assert loader.read_bytes(permitted) == b"guidance"
        with pytest.raises(RecordValidationError, match="does not authorize"):
            loader.read_bytes(forbidden)
        tampered = ArtifactRef(
            permitted.role,
            permitted.relative_path,
            "f" * 64,
            permitted.byte_count,
            permitted.media_type,
        )
        with pytest.raises(RecordValidationError, match="does not authorize"):
            loader.read_bytes(tampered)
    with pytest.raises(RecordValidationError, match="not open"):
        SlotArtifactLoader(capability, run_root=root).read_bytes(permitted)


def test_sealed_capability_refuses_an_arm_labelled_readable_reference() -> None:
    with pytest.raises(RecordValidationError, match="arm-opaque"):
        SealedSlotCapability(
            _CAPS[0],
            (
                ArtifactRef(
                    "private_guidance",
                    "packet-work/guidance-sham.txt",
                    "e" * 64,
                    4,
                    "text/plain",
                ),
            ),
        )


def _guidance_ref_for(capability: str) -> ArtifactRef:
    return ArtifactRef(
        "private_guidance",
        opaque_guidance_relative_path("task-1", capability),
        "e" * 64,
        4,
        "text/plain",
    )


def test_sealed_capability_role_allowlist_excludes_every_scientific_record() -> None:
    snapshot = ArtifactRef(
        "composite_snapshot", "controller-artifacts/x", "e" * 64, 4, "application/json"
    )
    assert SealedSlotCapability(_CAPS[0], (snapshot,)).readable_refs == (snapshot,)
    for role in (
        "resampling_assignment_ledger",
        "packet_index_candidate",
        "packet_index_sealed",
        "analysis_freeze",
        "resampling_prefix_receipt",
    ):
        with pytest.raises(RecordValidationError, match="never be readable"):
            SealedSlotCapability(
                _CAPS[0],
                (ArtifactRef(role, "ledger.json", "e" * 64, 4, "application/json"),),
            )
    with pytest.raises(RecordValidationError, match="capability's own digest"):
        SealedSlotCapability(_CAPS[0], (snapshot, _guidance_ref_for(_CAPS[1])))
    with pytest.raises(RecordValidationError, match="at most one guidance"):
        SealedSlotCapability(
            _CAPS[0],
            (
                _guidance_ref_for(_CAPS[0]),
                ArtifactRef(
                    "private_guidance",
                    opaque_guidance_relative_path("task-2", _CAPS[0]),
                    "f" * 64,
                    4,
                    "text/plain",
                ),
            ),
        )


def _work_order(guidance: ArtifactRef | None) -> OpaqueSlotWorkOrder:
    return OpaqueSlotWorkOrder(
        study_id=_STUDY,
        task_id="task-1",
        benchmark="SWE",
        slot=OpaqueSlotIdentity("slot-0", _CAPS[0], 7, 0, 0),
        snapshot_ref=ArtifactRef(
            "composite_snapshot",
            "controller-artifacts/composite_snapshot/" + "a" * 64,
            "a" * 64,
            1,
            "application/json",
        ),
        private_guidance_ref=guidance,
        prefix_visible_sha256="c" * 64,
        packet_index_sha256="d" * 64,
        analysis_freeze_sha256="e" * 64,
        branch_caps=BranchCaps(1, 1, 1, 1, True),
    )


def test_capability_sealing_derives_authority_only_from_its_work_order() -> None:
    guidance = _guidance_ref_for(_CAPS[0])
    order = _work_order(guidance)
    sealed = seal_slot_capability(order)
    assert sealed.opaque_capability_id == _CAPS[0]
    assert sealed.readable_refs == (order.snapshot_ref, guidance)
    program = ArtifactRef(
        "synthetic_execution_program",
        "sources/program.json",
        "b" * 64,
        2,
        "application/json",
    )
    assert program in seal_slot_capability(order, additional_refs=(program,)).readable_refs
    # The two slot-identifying roles may never arrive through the generic list:
    # a packet and a composite snapshot both name a specific slot, so both come
    # only from the work order (or, for grading, its own named parameter).
    for smuggled in (
        _guidance_ref_for(_CAPS[1]),
        _guidance_ref_for(_CAPS[0]),
        ArtifactRef(
            "composite_snapshot",
            "controller-artifacts/composite_snapshot/" + "9" * 64,
            "9" * 64,
            1,
            "application/json",
        ),
        ArtifactRef(
            "resampling_assignment_ledger",
            "assignment.json",
            "c" * 64,
            3,
            "application/json",
        ),
    ):
        with pytest.raises(RecordValidationError, match="may not be added"):
            seal_slot_capability(order, additional_refs=(smuggled,))
    terminal = ArtifactRef(
        "composite_snapshot",
        "controller-artifacts/composite_snapshot/" + "8" * 64,
        "8" * 64,
        1,
        "application/json",
    )
    assert terminal in seal_slot_capability(
        order, terminal_snapshot_ref=terminal
    ).readable_refs
    with pytest.raises(RecordValidationError, match="composite_snapshot role"):
        seal_slot_capability(order, terminal_snapshot_ref=program)
    assert seal_slot_capability(_work_order(None)).readable_refs == (
        order.snapshot_ref,
    )


def test_resolution_rejects_a_candidate_from_a_different_study(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(root, candidate_study_id="study-other")
    with pytest.raises(RecordValidationError, match="study_id differs"):
        resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)


def test_resolution_rejects_a_foreign_prefix_digest(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(root, entry_overrides={"prefix_index_sha256": "f" * 64})
    with pytest.raises(RecordValidationError, match="different prefix index"):
        resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)


def test_resolution_rejects_a_donor_the_ledger_did_not_match(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(root, entry_overrides={"donor_task_id": "task-999"})
    with pytest.raises(RecordValidationError, match="donor differs"):
        resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)


def test_resolution_rejects_a_marker_that_also_carries_packets(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(
        root,
        triggered=False,
        entry_overrides={
            "real_ref": _ref_value(
                ArtifactRef(
                    "private_guidance",
                    opaque_guidance_relative_path("task-1", _CAPS[0]),
                    "e" * 64,
                    4,
                    "text/plain",
                )
            )
        },
    )
    with pytest.raises(RecordValidationError, match="marker has an unregistered shape"):
        resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)


def test_resolution_rejects_a_grant_whose_packet_bytes_are_absent(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(root)
    (root / opaque_guidance_relative_path("task-1", _CAPS[0])).unlink()
    with pytest.raises(RecordValidationError, match="unreadable artifact_ref"):
        resolve_packet_capabilities(packet_index_ref=sealed, run_root=root)


def test_resolution_rejects_a_mislabelled_sealed_index_role(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    sealed = _build_root(root)
    relabelled = ArtifactRef(
        "packet_index_candidate",
        sealed.relative_path,
        sealed.sha256,
        sealed.byte_count,
        sealed.media_type,
    )
    with pytest.raises(RecordValidationError, match="packet_index_sealed role"):
        resolve_packet_capabilities(packet_index_ref=relabelled, run_root=root)


def test_slot_loader_refuses_a_symlinked_artifact(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"guidance")
    link = root / "packet-work" / ("0" * 64) / ("guidance-" + _CAPS[0] + ".txt")
    link.parent.mkdir(parents=True)
    link.symlink_to(outside)
    ref = ArtifactRef(
        "private_guidance",
        link.relative_to(root).as_posix(),
        hashlib.sha256(b"guidance").hexdigest(),
        8,
        "text/plain",
    )
    with SlotArtifactLoader(SealedSlotCapability(_CAPS[0], (ref,)), run_root=root) as loader:
        with pytest.raises(RecordValidationError, match="unreadable artifact_ref"):
            loader.read_bytes(ref)
