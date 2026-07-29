"""Key-independent verification of published synthetic assignment graphs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import (
    RecordValidationError,
    _load_direct_scientific_parent,
    _load_json_bytes,
    _read_ref,
)
from .assignment import _ALLOCATION_TABLE
from .types import Arm, ArtifactRef, Treatment


def _artifact_ref(value: object, *, field: str) -> ArtifactRef:
    if not isinstance(value, dict):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    try:
        return ArtifactRef(**value)
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is malformed: {exc}") from exc


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return {
        "role": ref.role,
        "relative_path": ref.relative_path,
        "sha256": ref.sha256,
        "byte_count": ref.byte_count,
        "media_type": ref.media_type,
    }


def _proof(
    ref: ArtifactRef,
    *,
    run_root: Path,
) -> dict[str, object]:
    expected_path = f"blobs/matching/proof/{ref.sha256}.json"
    if (
        ref.role != "assignment_matching_proof"
        or ref.relative_path != expected_path
        or ref.media_type
        != "application/vnd.pneuma.assignment-matching-proof+json"
        or ref.byte_count <= 0
    ):
        raise RecordValidationError("matching proof ref has wrong identity")
    path, raw = _read_ref(ref, run_root=run_root)
    value = _load_json_bytes(raw, source=path)
    if not isinstance(value, dict) or canonical_json_bytes(value, indent=None) != raw:
        raise RecordValidationError("matching proof is not compact canonical JSON")
    expected_fields = {
        "assignment_prefix_view_sha256",
        "assignment_program_sha256",
        "canonical_focal_task_ids",
        "cycle_order",
        "donor_by_task",
        "invocation_receipt_refs",
        "offset_trials",
        "proof_kind",
        "schema_version",
        "selected_offset",
        "stratum_key",
    }
    if (
        set(value) != expected_fields
        or value.get("proof_kind") != "synthetic_cyclic_offset_v1"
        or value.get("schema_version") != "1"
        or value.get("invocation_receipt_refs") != []
    ):
        raise RecordValidationError("synthetic matching proof shape is not closed")
    return value


def _reconstruct_arms(
    allocation: Mapping[str, object],
) -> list[str]:
    index = allocation.get("treatment_allocation_index")
    orientation = allocation.get("no_packet_orientation_bit")
    if type(index) is not int or not 0 <= index < len(_ALLOCATION_TABLE):
        raise RecordValidationError("allocation index is outside the frozen table")
    if type(orientation) is not int or orientation not in (0, 1):
        raise RecordValidationError("null orientation bit is not exact")
    treatments = _ALLOCATION_TABLE[index]
    null_ordinals = [
        ordinal
        for ordinal, treatment in enumerate(treatments)
        if treatment is Treatment.NO_PACKET
    ]
    null_arms = (
        (Arm.NONE.value, Arm.RESAMPLE.value)
        if orientation == 0
        else (Arm.RESAMPLE.value, Arm.NONE.value)
    )
    result: list[str] = []
    for ordinal, treatment in enumerate(treatments):
        if treatment is Treatment.REAL:
            result.append(Arm.REAL.value)
        elif treatment is Treatment.SHAM:
            result.append(Arm.SHAM.value)
        else:
            result.append(null_arms[null_ordinals.index(ordinal)])
    return result


def verify_synthetic_assignment_graph(
    ledger_ref: ArtifactRef,
    *,
    run_root: Path,
) -> dict[str, object]:
    """Verify public ancestry, proof reachability, feasibility, and allocation."""

    root = Path(run_root).resolve(strict=True)
    ledger = _load_direct_scientific_parent(
        _ref_mapping(ledger_ref),
        run_root=root,
        field="ledger_ref",
        expected_kind="resampling_assignment_ledger",
    )
    payload = cast(dict[str, object], ledger.value["payload"])
    if payload.get("assignment_mode") != "synthetic_derangement":
        raise RecordValidationError("unkeyed synthetic verifier rejects other modes")
    schedule_ref = _artifact_ref(payload.get("schedule_ref"), field="schedule_ref")
    prefix_ref = _artifact_ref(
        payload.get("prefix_index_ref"),
        field="prefix_index_ref",
    )
    program_ref = _artifact_ref(
        payload.get("matching_program_ref"),
        field="matching_program_ref",
    )
    schedule = _load_direct_scientific_parent(
        _ref_mapping(schedule_ref),
        run_root=root,
        field="schedule_ref",
        expected_kind="resampling_prefix_schedule",
    )
    prefix = _load_direct_scientific_parent(
        _ref_mapping(prefix_ref),
        run_root=root,
        field="prefix_index_ref",
        expected_kind="resampling_prefix_receipt",
    )
    schedule_payload = cast(dict[str, object], schedule.value["payload"])
    prefix_payload = cast(dict[str, object], prefix.value["payload"])
    if prefix_payload.get("schedule_ref") != _ref_mapping(schedule_ref):
        raise RecordValidationError("prefix receipt does not descend from schedule")

    schedule_rows = cast(list[dict[str, object]], schedule_payload["tasks"])
    task_ids = [
        cast(str, cast(dict[str, object], row["task"])["task_id"])
        for row in schedule_rows
    ]
    lineages = {
        cast(str, cast(dict[str, object], row["task"])["task_id"]): cast(
            str,
            cast(dict[str, object], row["task"])["lineage"],
        )
        for row in schedule_rows
    }
    prefix_rows = cast(list[dict[str, object]], prefix_payload["task_receipts"])
    triggers = {
        cast(str, row["task_id"]): cast(str, row["trigger_reason"])
        for row in prefix_rows
    }
    assignments = cast(list[dict[str, object]], payload["assignments"])
    allocations = cast(list[dict[str, object]], payload["allocation_receipts"])
    donor_receipts = cast(
        list[dict[str, object]],
        payload["donor_match_receipts"],
    )
    if any(
        [cast(str, row["task_id"]) for row in rows] != task_ids
        for rows in (prefix_rows, assignments, allocations, donor_receipts)
    ):
        raise RecordValidationError(
            "assignment graph arrays do not share exact schedule order"
        )

    proof_refs = [
        _artifact_ref(value, field="matching_proof_refs item")
        for value in cast(list[object], payload["matching_proof_refs"])
    ]
    if len(proof_refs) != len(set(proof_refs)):
        raise RecordValidationError("matching proof refs repeat")
    proofs = {
        ref: _proof(ref, run_root=root)
        for ref in proof_refs
    }
    triggered_ids = [
        task_id
        for task_id in task_ids
        if triggers[task_id] != "no_intervention_opportunity"
    ]
    reachable_refs: set[ArtifactRef] = set()
    mapping: dict[str, str] = {}
    proof_ref_by_task: dict[str, ArtifactRef] = {}
    proof_focal_ids: dict[ArtifactRef, list[str]] = {}
    for ref, proof in proofs.items():
        if (
            proof.get("assignment_prefix_view_sha256")
            != payload.get("assignment_prefix_view_sha256")
            or proof.get("assignment_program_sha256") != program_ref.sha256
        ):
            raise RecordValidationError("matching proof ancestry differs")
        focal_ids = proof.get("canonical_focal_task_ids")
        donor_rows = proof.get("donor_by_task")
        cycle_rows = proof.get("cycle_order")
        trials = proof.get("offset_trials")
        selected_offset = proof.get("selected_offset")
        if (
            not isinstance(focal_ids, list)
            or not focal_ids
            or not all(type(task_id) is str and task_id for task_id in focal_ids)
            or len(focal_ids) != len(set(focal_ids))
            or focal_ids
            != sorted(
                focal_ids,
                key=lambda task_id: cast(str, task_id).encode("utf-8"),
            )
            or not isinstance(donor_rows, list)
            or len(donor_rows) != len(focal_ids)
            or not isinstance(cycle_rows, list)
            or not isinstance(trials, list)
            or type(selected_offset) is not int
            or selected_offset < 1
            or len(trials) != selected_offset
            or not isinstance(proof.get("stratum_key"), list)
            or not cast(list[object], proof["stratum_key"])
            or not all(
                type(component) is str and component
                for component in cast(list[object], proof["stratum_key"])
            )
        ):
            raise RecordValidationError("synthetic proof order/trial grammar differs")
        local_mapping: dict[str, str] = {}
        for index, row in enumerate(donor_rows):
            if (
                not isinstance(row, list)
                or len(row) != 2
                or row[0] != focal_ids[index]
                or not all(isinstance(value, str) for value in row)
            ):
                raise RecordValidationError("proof donor mapping order differs")
            local_mapping[cast(str, row[0])] = cast(str, row[1])
        if (
            set(local_mapping) != set(focal_ids)
            or set(local_mapping.values()) != set(focal_ids)
            or any(focal == donor for focal, donor in local_mapping.items())
            or any(
                lineages[focal] == lineages[donor]
                for focal, donor in local_mapping.items()
            )
            or any(
                local_mapping.get(donor) == focal
                for focal, donor in local_mapping.items()
            )
        ):
            raise RecordValidationError("synthetic proof mapping is infeasible")
        cycle_task_ids: list[str] = []
        if (
            len(cycle_rows) != len(focal_ids)
            or {
                row.get("task_id")
                for row in cycle_rows
                if isinstance(row, Mapping)
            }
            != set(focal_ids)
        ):
            raise RecordValidationError("synthetic proof cycle order is incomplete")
        for row in cycle_rows:
            if (
                not isinstance(row, Mapping)
                or type(row.get("task_id")) is not str
                or type(row.get("order_hmac_sha256")) is not str
                or len(cast(str, row["order_hmac_sha256"])) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in cast(str, row["order_hmac_sha256"])
                )
            ):
                raise RecordValidationError("synthetic cycle row is malformed")
            cycle_task_ids.append(cast(str, row["task_id"]))
        expected_selected_mapping = {
            focal: cycle_task_ids[
                (index + selected_offset) % len(cycle_task_ids)
            ]
            for index, focal in enumerate(cycle_task_ids)
        }
        if local_mapping != expected_selected_mapping:
            raise RecordValidationError(
                "synthetic mapping does not follow selected cyclic offset"
            )
        for index, trial in enumerate(trials, start=1):
            trial_mapping = {
                focal: cycle_task_ids[(position + index) % len(cycle_task_ids)]
                for position, focal in enumerate(cycle_task_ids)
            }
            expected_failure: str | None = None
            for focal in focal_ids:
                donor = trial_mapping[focal]
                if lineages[focal] == lineages[donor]:
                    expected_failure = "same_lineage"
                    break
                if trial_mapping[donor] == focal:
                    expected_failure = "reciprocal_two_cycle"
                    break
            if (
                not isinstance(trial, Mapping)
                or trial.get("offset") != index
                or trial.get("valid") is not (expected_failure is None)
                or trial.get("failure_code") != expected_failure
            ):
                raise RecordValidationError("synthetic proof trial prefix differs")
        overlap = set(mapping) & set(local_mapping)
        if overlap:
            raise RecordValidationError("matching proofs overlap focal tasks")
        mapping.update(local_mapping)
        proof_focal_ids[ref] = cast(list[str], focal_ids)
        for focal in focal_ids:
            proof_ref_by_task[focal] = ref
        reachable_refs.add(ref)
    if set(mapping) != set(triggered_ids):
        raise RecordValidationError(
            "matching proofs do not exactly cover triggered tasks"
        )

    capabilities: set[str] = set()
    for task_id, assignment, allocation, donor_receipt in zip(
        task_ids,
        assignments,
        allocations,
        donor_receipts,
        strict=True,
    ):
        slot_ids = allocation.get("slot_ids_by_ordinal")
        slot_arms = assignment.get("slot_arms")
        schedule_row = schedule_rows[task_ids.index(task_id)]
        expected_slot_ids = [
            cast(str, slot["slot_id"])
            for slot in cast(list[dict[str, object]], schedule_row["slots"])
        ]
        if not isinstance(slot_ids, list) or not isinstance(slot_arms, list):
            raise RecordValidationError("allocation slot arrays are malformed")
        if (
            slot_ids != expected_slot_ids
            or assignment.get("task_lineage") != lineages[task_id]
            or assignment.get("schedule_sha256") != schedule_ref.sha256
            or assignment.get("prefix_index_sha256") != prefix_ref.sha256
        ):
            raise RecordValidationError("assignment schedule ancestry differs")
        reconstructed = _reconstruct_arms(allocation)
        if slot_arms != [
            [slot_id, arm]
            for slot_id, arm in zip(slot_ids, reconstructed, strict=True)
        ]:
            raise RecordValidationError("assignment arms differ from public draws")
        capability_rows = allocation.get("slot_capabilities")
        if not isinstance(capability_rows, list) or len(capability_rows) != 4:
            raise RecordValidationError("slot capability rows are incomplete")
        for index, row in enumerate(capability_rows):
            if (
                not isinstance(row, list)
                or len(row) != 2
                or row[0] != slot_ids[index]
                or not isinstance(row[1], str)
                or len(row[1]) != 64
                or any(character not in "0123456789abcdef" for character in row[1])
                or row[1] in capabilities
            ):
                raise RecordValidationError("slot capability identity is invalid")
            capabilities.add(row[1])
        if task_id in mapping:
            proof_ref = _artifact_ref(
                donor_receipt.get("matching_proof_ref"),
                field=f"donor receipt proof {task_id}",
            )
            if (
                donor_receipt.get("kind") != "matched"
                or donor_receipt.get("donor_task_id") != mapping[task_id]
                or donor_receipt.get("task_lineage") != lineages[task_id]
                or donor_receipt.get("donor_lineage")
                != lineages[mapping[task_id]]
                or donor_receipt.get("assignment_mode")
                != "synthetic_derangement"
                or donor_receipt.get("matching_algorithm")
                != "synthetic_cyclic_offset_v1"
                or donor_receipt.get("assignment_prefix_view_sha256")
                != payload.get("assignment_prefix_view_sha256")
                or donor_receipt.get("stratum_key")
                != proofs[proof_ref].get("stratum_key")
                or assignment.get("donor_match_kind") != "matched"
                or assignment.get("donor_task_id") != mapping[task_id]
                or assignment.get("donor_lineage")
                != lineages[mapping[task_id]]
                or proof_ref != proof_ref_by_task[task_id]
            ):
                raise RecordValidationError(
                    "matched donor receipt/assignment/proof disagree"
                )
            reachable_refs.add(proof_ref)
            candidates = donor_receipt.get("candidates")
            focal_ids = proof_focal_ids[proof_ref]
            if not isinstance(candidates, list):
                raise RecordValidationError("matched candidates must be an array")
            expected_donors = {
                candidate
                for candidate in focal_ids
                if candidate != task_id
                and lineages[candidate] != lineages[task_id]
            }
            observed_donors: set[str] = set()
            chosen_cost: object | None = None
            for candidate in candidates:
                if not isinstance(candidate, Mapping):
                    raise RecordValidationError("matched candidate is not an object")
                donor_id = candidate.get("donor_task_id")
                primary_cost = candidate.get("primary_cost")
                if (
                    type(donor_id) is not str
                    or donor_id not in expected_donors
                    or candidate.get("donor_lineage") != lineages[donor_id]
                    or candidate.get("fallback_code") is not None
                    or type(candidate.get("tie_hmac_sha256")) is not str
                    or len(cast(str, candidate["tie_hmac_sha256"])) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in cast(str, candidate["tie_hmac_sha256"])
                    )
                    or not isinstance(primary_cost, list)
                    or len(primary_cost) != 3
                    or any(type(value) is not int or value < 0 for value in primary_cost)
                    or primary_cost[0] != 0
                ):
                    raise RecordValidationError("matched candidate ancestry is invalid")
                observed_donors.add(donor_id)
                if donor_id == mapping[task_id]:
                    chosen_cost = candidate.get("primary_cost")
            if (
                len(candidates) != len(expected_donors)
                or observed_donors != expected_donors
                or (
                donor_receipt.get("chosen_primary_cost") != chosen_cost
                )
            ):
                raise RecordValidationError(
                    "matched candidates are incomplete or chosen cost differs"
                )
        elif (
            donor_receipt
            != {
                "kind": "not_applicable_no_trigger",
                "task_id": task_id,
                "trigger_reason": "no_intervention_opportunity",
                "assignment_prefix_view_sha256": payload[
                    "assignment_prefix_view_sha256"
                ],
            }
            or assignment.get("donor_match_kind")
            != "not_applicable_no_trigger"
            or assignment.get("donor_task_id") is not None
            or assignment.get("donor_lineage") is not None
        ):
            raise RecordValidationError("no-trigger donor ancestry is not closed")
    if reachable_refs != set(proof_refs):
        raise RecordValidationError("matching proof graph has unreachable refs")
    return ledger.value
