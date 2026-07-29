"""Key-independent verification of published synthetic assignment graphs."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import asdict
import hashlib
from pathlib import Path
from typing import cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import (
    RecordValidationError,
    _load_direct_scientific_parent,
    _load_json_bytes,
    _read_ref,
    verify_artifact_root,
)
from .assignment import _ALLOCATION_TABLE
from .assignment import (
    BytesField,
    _AssignmentKeyBuffers,
    _allocate_task,
    _derive_assignment_subkeys_into,
    _read_exact_master_into,
    _solve_synthetic_stratum,
    _wipe_bytearray,
    assignment_prefix_view_sha256,
    commitment_sha256,
    load_assignment_authority,
)
from .branch_assignment import (
    _candidate_receipts,
    _load_object_ref,
    _prefix_task_view,
    _require_prefix_publication,
    _stratum_component,
    _task_schedule,
)
from .preflight import _validate_assignment_program
from .secrets import AssignmentSecretHandle, _require_handle_binding
from .storage import _load_operational_object
from .types import Arm, ArtifactRef, Treatment
from .types import (
    AllocationReceipt,
    AssignmentLedger,
    AssignmentMode,
    AssignmentPrefixTaskView,
    AssignmentPrefixView,
    DonorCandidateReceipt,
    DonorMatchReceipt,
    MatchedDonorReceipt,
    MatchingAlgorithm,
    NoTriggerDonorReceipt,
    TaskAssignment,
    TriggerReason,
)


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


def require_assignment_reconstruction(
    ledger_ref: ArtifactRef,
    *,
    assignment_secret_handle: AssignmentSecretHandle,
    matching_backend_session: object | None,
    run_root: Path,
) -> AssignmentLedger:
    """Reconstruct every secret-dependent synthetic assignment decision."""

    if matching_backend_session is not None:
        raise RecordValidationError(
            "synthetic reconstruction forbids a matching backend session"
        )
    root = Path(run_root).resolve(strict=True)
    public_ledger = verify_synthetic_assignment_graph(
        ledger_ref,
        run_root=root,
    )
    payload = cast(dict[str, object], public_ledger["payload"])
    manifest_ref = _artifact_ref(payload["manifest_ref"], field="manifest_ref")
    schedule_ref = _artifact_ref(payload["schedule_ref"], field="schedule_ref")
    prefix_ref = _artifact_ref(
        payload["prefix_index_ref"],
        field="prefix_index_ref",
    )
    program_ref = _artifact_ref(
        payload["matching_program_ref"],
        field="matching_program_ref",
    )
    authority = load_assignment_authority(
        schedule_ref,
        prefix_ref,
        run_root=root,
    )
    if authority.manifest_ref != manifest_ref:
        raise RecordValidationError("ledger manifest ancestry differs")
    _require_prefix_publication(
        manifest_ref=manifest_ref,
        schedule_ref=schedule_ref,
        run_root=root,
    )
    _require_handle_binding(
        assignment_secret_handle,
        manifest_ref,
        schedule_ref,
        run_root=root,
        purpose="assignment",
    )
    manifest = _load_direct_scientific_parent(
        _ref_mapping(manifest_ref),
        run_root=root,
        field="manifest_ref",
        expected_kind="resampling_study_manifest",
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
    manifest_payload = cast(dict[str, object], manifest.value["payload"])
    schedule_payload = cast(dict[str, object], schedule.value["payload"])
    prefix_payload = cast(dict[str, object], prefix.value["payload"])
    if _artifact_ref(
        manifest_payload.get("assignment_program_ref"),
        field="manifest assignment_program_ref",
    ) != program_ref:
        raise RecordValidationError("ledger matching program differs from manifest")
    program_path, program_raw = _read_ref(program_ref, run_root=root)
    program = _load_json_bytes(program_raw, source=program_path)
    if not isinstance(program, dict) or (
        program.get("assignment_mode") != "synthetic_derangement"
        or program.get("matching_algorithm") != "synthetic_cyclic_offset_v1"
        or program.get("backend_receipt_ref") is not None
    ):
        raise RecordValidationError("reconstruction program is not synthetic")
    _validate_assignment_program(program)
    normalizer = program.get("verifier_normalizer_contract")
    if not isinstance(normalizer, Mapping):
        raise RecordValidationError(
            "reconstruction normalizer contract is not an object"
        )
    normalizer_ref = _artifact_ref(
        normalizer.get("normalizer_source_ref"),
        field="reconstruction normalizer source",
    )
    tokenizer_ref = _artifact_ref(
        manifest_payload.get("tokenizer_ref"),
        field="reconstruction tokenizer",
    )
    normalizer_source = _load_object_ref(
        normalizer_ref,
        run_root=root,
        field="reconstruction normalizer source",
    )
    tokenizer_source = _load_object_ref(
        tokenizer_ref,
        run_root=root,
        field="reconstruction tokenizer",
    )
    revision_values = manifest_payload.get("source_revision_refs")
    if not isinstance(revision_values, list):
        raise RecordValidationError(
            "manifest source revisions must be an array"
        )
    revision_refs = {
        _artifact_ref(value, field="manifest source revision")
        for value in revision_values
    }
    if (
        normalizer.get("normalizer_source_sha256") != normalizer_ref.sha256
        or normalizer.get("report_tokenizer_sha256") != tokenizer_ref.sha256
        or normalizer_ref not in revision_refs
        or normalizer_source
        != {
            "record_kind": "synthetic_assignment_normalizer_v1",
            "schema_version": "1",
            "algorithm": "closed_fixture_components_v1",
        }
        or tokenizer_source
        != {
            "record_kind": "synthetic_report_tokenizer_v1",
            "schema_version": "1",
            "algorithm": "unicode_whitespace_v1",
        }
    ):
        raise RecordValidationError(
            "reconstruction normalizer/tokenizer authority differs"
        )
    stratum_fields = program.get("stratum_keys")
    if not isinstance(stratum_fields, list) or not stratum_fields or not all(
        type(field) is str and field for field in stratum_fields
    ):
        raise RecordValidationError("reconstruction stratum keys are malformed")

    schedule_values = schedule_payload.get("tasks")
    receipt_values = prefix_payload.get("task_receipts")
    if (
        not isinstance(schedule_values, list)
        or not isinstance(receipt_values, list)
        or len(schedule_values) != len(receipt_values)
        or not schedule_values
    ):
        raise RecordValidationError("reconstruction coverage is incomplete")
    schedules = tuple(
        _task_schedule(value, field=f"schedule tasks[{index}]")
        for index, value in enumerate(schedule_values)
    )
    receipts_by_id = {
        cast(str, cast(dict[str, object], receipt)["task_id"]): receipt
        for receipt in receipt_values
        if isinstance(receipt, dict)
    }
    schedule_ids = tuple(schedule.task.task_id for schedule in schedules)
    if tuple(receipts_by_id) != schedule_ids:
        raise RecordValidationError("reconstruction prefix order differs")
    task_views = tuple(
        _prefix_task_view(
            schedule_row,
            receipts_by_id[schedule_row.task.task_id],
            schedule_sha256=schedule_ref.sha256,
            run_root=root,
        )
        for schedule_row in schedules
    )
    view = AssignmentPrefixView(
        study_id=authority.study_id,
        schedule_sha256=schedule_ref.sha256,
        tasks=task_views,
    )
    view_sha256 = assignment_prefix_view_sha256(view)
    if payload.get("assignment_prefix_view_sha256") != view_sha256:
        raise RecordValidationError("reconstructed prefix view digest differs")

    master = bytearray(32)
    keys = _AssignmentKeyBuffers()
    try:
        _read_exact_master_into(assignment_secret_handle, master)
        if (
            commitment_sha256(
                "assignment-master-key",
                authority.study_id,
                BytesField(bytes(master)),
            )
            != manifest_payload.get(
                "assignment_master_key_commitment_sha256"
            )
        ):
            raise RecordValidationError(
                "reconstruction key does not match manifest commitment"
            )
        _derive_assignment_subkeys_into(
            memoryview(master),
            authority.study_id,
            manifest_ref,
            schedule_ref,
            keys,
        )
        strata: dict[
            tuple[str, ...],
            list[AssignmentPrefixTaskView],
        ] = {}
        stratum_by_task: dict[str, tuple[str, ...]] = {}
        for task in task_views:
            if task.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY:
                continue
            stratum_key = tuple(
                _stratum_component(task, cast(str, field))
                for field in stratum_fields
            )
            strata.setdefault(stratum_key, []).append(task)
            stratum_by_task[task.task_id] = stratum_key

        expected_proof_refs: list[ArtifactRef] = []
        expected_donors: dict[str, AssignmentPrefixTaskView] = {}
        expected_proof_by_task: dict[str, ArtifactRef] = {}
        published_refs = [
            _artifact_ref(value, field="matching_proof_refs item")
            for value in cast(list[object], payload["matching_proof_refs"])
        ]
        if len(published_refs) != len(strata):
            raise RecordValidationError("reconstruction proof count differs")
        for position, stratum_key in enumerate(
            sorted(
                strata,
                key=lambda key: tuple(
                    component.encode("utf-8") for component in key
                ),
            )
        ):
            stratum_tasks = tuple(strata[stratum_key])
            proof, selected = _solve_synthetic_stratum(
                tasks=stratum_tasks,
                stratum_key=stratum_key,
                assignment_prefix_view_sha256=view_sha256,
                assignment_program_sha256=program_ref.sha256,
                donor_key=keys.donor,
            )
            proof_ref = published_refs[position]
            proof_path, proof_raw = _read_ref(proof_ref, run_root=root)
            persisted = _load_json_bytes(proof_raw, source=proof_path)
            if (
                persisted != proof
                or canonical_json_bytes(proof, indent=None) != proof_raw
            ):
                raise RecordValidationError(
                    "keyed synthetic proof reconstruction differs"
                )
            expected_proof_refs.append(proof_ref)
            expected_donors.update(selected)
            for task in stratum_tasks:
                expected_proof_by_task[task.task_id] = proof_ref

        expected_assignments: list[dict[str, object]] = []
        expected_allocations: list[dict[str, object]] = []
        expected_receipts: list[dict[str, object]] = []
        task_by_id = {task.task_id: task for task in task_views}
        for schedule_row, task in zip(schedules, task_views, strict=True):
            donor = expected_donors.get(task.task_id)
            assignment, allocation = _allocate_task(
                study_id=authority.study_id,
                manifest_sha256=manifest_ref.sha256,
                schedule_sha256=schedule_ref.sha256,
                prefix_index_sha256=prefix_ref.sha256,
                task_schedule=schedule_row,
                donor_task=donor,
                allocation_key=keys.allocation,
                orientation_key=keys.orientation,
                capability_key=keys.capability,
            )
            expected_assignments.append(
                {
                    **asdict(assignment),
                    "slot_arms": [
                        [slot_id, arm.value]
                        for slot_id, arm in assignment.slot_arms
                    ],
                }
            )
            expected_allocations.append(
                {
                    "task_id": allocation.task_id,
                    "slot_ids_by_ordinal": list(
                        allocation.slot_ids_by_ordinal
                    ),
                    "treatment_allocation_index": (
                        allocation.treatment_allocation_index
                    ),
                    "allocation_rejection_counter": (
                        allocation.allocation_rejection_counter
                    ),
                    "no_packet_orientation_bit": (
                        allocation.no_packet_orientation_bit
                    ),
                    "orientation_rejection_counter": (
                        allocation.orientation_rejection_counter
                    ),
                    "slot_capabilities": [
                        list(row) for row in allocation.slot_capabilities
                    ],
                }
            )
            if donor is None:
                expected_receipts.append(
                    {
                        "kind": "not_applicable_no_trigger",
                        "task_id": task.task_id,
                        "trigger_reason": (
                            TriggerReason.NO_INTERVENTION_OPPORTUNITY.value
                        ),
                        "assignment_prefix_view_sha256": view_sha256,
                    }
                )
            else:
                typed_donor = task_by_id[donor.task_id]
                candidates = _candidate_receipts(
                    task,
                    tuple(
                        candidate
                        for candidate in task_views
                        if stratum_by_task.get(candidate.task_id)
                        == stratum_by_task[task.task_id]
                    ),
                    donor_key=keys.donor,
                )
                chosen = next(
                    candidate
                    for candidate in candidates
                    if candidate["donor_task_id"] == typed_donor.task_id
                )
                expected_receipts.append(
                    {
                        "kind": "matched",
                        "task_id": task.task_id,
                        "donor_task_id": typed_donor.task_id,
                        "task_lineage": task.lineage,
                        "donor_lineage": typed_donor.lineage,
                        "assignment_mode": "synthetic_derangement",
                        "matching_algorithm": "synthetic_cyclic_offset_v1",
                        "stratum_key": list(stratum_by_task[task.task_id]),
                        "assignment_prefix_view_sha256": view_sha256,
                        "candidates": candidates,
                        "chosen_primary_cost": chosen["primary_cost"],
                        "matching_proof_ref": _ref_mapping(
                            expected_proof_by_task[task.task_id]
                        ),
                    }
                )
        if (
            payload.get("matching_proof_refs")
            != [_ref_mapping(ref) for ref in expected_proof_refs]
            or payload.get("assignments") != expected_assignments
            or payload.get("allocation_receipts") != expected_allocations
            or payload.get("donor_match_receipts") != expected_receipts
        ):
            raise RecordValidationError(
                "keyed assignment reconstruction differs from ledger"
            )
    finally:
        keys.wipe()
        _wipe_bytearray(master)
    return _typed_assignment_ledger(public_ledger)


def require_confirmation_assignment(
    ledger_ref: ArtifactRef,
    *,
    assignment_secret_handle: AssignmentSecretHandle,
    matching_backend_session: object | None,
    run_root: Path,
) -> AssignmentLedger:
    """Fail closed until the nominal confirmation runner adapter exists."""

    del assignment_secret_handle, matching_backend_session
    root = Path(run_root).resolve(strict=True)
    ledger = _load_direct_scientific_parent(
        _ref_mapping(ledger_ref),
        run_root=root,
        field="ledger_ref",
        expected_kind="resampling_assignment_ledger",
    )
    payload = cast(dict[str, object], ledger.value["payload"])
    if payload.get("assignment_mode") != "confirmation_lineage_matching":
        raise RecordValidationError(
            "confirmation wrapper requires a confirmation ledger"
        )
    raise RecordValidationError(
        "confirmation matching backend reconstruction adapter is unavailable"
    )


def _require_assignment_publication(
    ledger_ref: ArtifactRef,
    *,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    run_root: Path,
) -> None:
    receipt_path = (
        run_root / "operational" / "storage-policy" / "assignment.json"
    )
    receipt, _receipt_raw = _load_operational_object(receipt_path)
    if set(receipt) != {
        "record_kind",
        "schema_version",
        "transaction",
        "intent",
        "transaction_intent_sha256",
        "publication_commit",
        "fresh_at_publication_commit",
        "publication_commit_recorded",
        "publication_commit_consumes_lease",
        "fixed_receipt_is_acceptance_marker",
    }:
        raise RecordValidationError(
            "assignment storage receipt shape is not closed"
        )
    intent = receipt.get("intent")
    proof = receipt.get("publication_commit")
    if not isinstance(intent, dict) or not isinstance(proof, dict):
        raise RecordValidationError(
            "assignment storage receipt parents must be objects"
        )
    intent_raw = canonical_json_bytes(intent, indent=None)
    intent_digest = hashlib.sha256(intent_raw).hexdigest()
    commit_id = hashlib.sha256(
        b"local-test-storage-commit-v1\x00" + bytes.fromhex(intent_digest)
    ).hexdigest()
    normalized_root_sha256 = hashlib.sha256(
        run_root.as_posix().encode("utf-8")
    ).hexdigest()
    begin = intent.get("begin")
    end = intent.get("end")
    if not isinstance(begin, dict) or not isinstance(end, dict):
        raise RecordValidationError(
            "assignment storage intent lacks begin/end observations"
        )
    if (
        receipt.get("record_kind") != "storage_policy_receipt_v1"
        or receipt.get("schema_version") != "1"
        or receipt.get("transaction") != "assignment"
        or receipt.get("transaction_intent_sha256") != intent_digest
        or receipt.get("fresh_at_publication_commit") is not True
        or receipt.get("publication_commit_recorded") is not True
        or receipt.get("publication_commit_consumes_lease") is not True
        or receipt.get("fixed_receipt_is_acceptance_marker") is not True
        or intent.get("transaction") != "assignment"
        or intent.get("prepared_scientific_relative_path")
        != ledger_ref.relative_path
        or intent.get("prepared_scientific_sha256") != ledger_ref.sha256
        or intent.get("lease_id") != begin.get("lease_id")
        or intent.get("lease_id") != end.get("lease_id")
        or begin.get("observation") != "begin"
        or end.get("observation") != "end"
        or begin.get("manifest_sha256") != manifest_ref.sha256
        or end.get("manifest_sha256") != manifest_ref.sha256
        or begin.get("schedule_sha256") != schedule_ref.sha256
        or end.get("schedule_sha256") != schedule_ref.sha256
        or begin.get("normalized_run_root_sha256")
        != normalized_root_sha256
        or end.get("normalized_run_root_sha256")
        != normalized_root_sha256
        or begin.get("mode") != "local_test"
        or end.get("mode") != "local_test"
        or begin.get("test_only") is not True
        or end.get("test_only") is not True
        or intent.get("final_lease_generation")
        != end.get("lease_generation")
        or intent.get("final_lease_expires_at_utc")
        != end.get("lease_expires_at_utc")
        or intent.get("continuous_lease_held") is not True
        or intent.get("fresh_at_end") is not True
        or intent.get("end_releases_lease") is not False
        or proof.get("record_kind") != "storage_publication_commit_v1"
        or proof.get("schema_version") != "1"
        or proof.get("transaction") != "assignment"
        or proof.get("manifest_sha256") != manifest_ref.sha256
        or proof.get("schedule_sha256") != schedule_ref.sha256
        or proof.get("normalized_run_root_sha256")
        != normalized_root_sha256
        or proof.get("mode") != "local_test"
        or proof.get("test_only") is not True
        or proof.get("lease_id") != intent.get("lease_id")
        or proof.get("lease_generation")
        != intent.get("final_lease_generation")
        or proof.get("lease_expires_at_utc")
        != intent.get("final_lease_expires_at_utc")
        or proof.get("authority_ref") != begin.get("authority_ref")
        or proof.get("mount_identity_sha256")
        != end.get("mount_identity_sha256")
        or proof.get("transaction_intent_sha256") != intent_digest
        or proof.get("scientific_relative_path") != ledger_ref.relative_path
        or proof.get("scientific_sha256") != ledger_ref.sha256
        or proof.get("registry_commit_id") != commit_id
        or proof.get("commit_recorded") is not True
        or proof.get("lease_consumed") is not True
        or proof.get("release_required") is not True
    ):
        raise RecordValidationError(
            "assignment storage receipt does not bind the accepted ledger"
        )
    proof_path = (
        run_root
        / "operational"
        / "storage-policy"
        / "registry"
        / "commits"
        / f"{commit_id}.json"
    )
    stored_proof, stored_raw = _load_operational_object(proof_path)
    if (
        stored_proof != proof
        or stored_raw != canonical_json_bytes(proof, indent=None)
    ):
        raise RecordValidationError(
            "assignment registry proof differs from fixed receipt"
        )


def require_assignment_publication(
    ledger_ref: ArtifactRef,
    *,
    run_root: Path,
) -> None:
    """Require the durable fixed receipt that makes one ledger authoritative."""

    ledger = _load_direct_scientific_parent(
        _ref_mapping(ledger_ref),
        run_root=run_root,
        field="ledger_ref",
        expected_kind="resampling_assignment_ledger",
    )
    payload = cast(dict[str, object], ledger.value["payload"])
    _require_assignment_publication(
        ledger_ref,
        manifest_ref=_artifact_ref(
            payload.get("manifest_ref"),
            field="manifest_ref",
        ),
        schedule_ref=_artifact_ref(
            payload.get("schedule_ref"),
            field="schedule_ref",
        ),
        run_root=Path(run_root).resolve(strict=True),
    )


def verify_result_bundle(
    receipt_path: Path,
    ledger_ref: ArtifactRef,
    *,
    assignment_secret_handle: AssignmentSecretHandle,
    matching_backend_session: object | None,
    required_document_kinds: Collection[str],
    run_root: Path,
) -> None:
    """Compose keyed reconstruction, storage acceptance, and root closure."""

    root = Path(run_root).resolve(strict=True)
    ledger = require_assignment_reconstruction(
        ledger_ref,
        assignment_secret_handle=assignment_secret_handle,
        matching_backend_session=matching_backend_session,
        run_root=root,
    )
    _require_assignment_publication(
        ledger_ref,
        manifest_ref=ledger.manifest_ref,
        schedule_ref=ledger.schedule_ref,
        run_root=root,
    )
    verify_artifact_root(
        receipt_path,
        root,
        required_document_kinds=required_document_kinds,
    )


def _typed_assignment_ledger(document: dict[str, object]) -> AssignmentLedger:
    payload = cast(dict[str, object], document["payload"])
    assignments = tuple(
        TaskAssignment(
            task_id=cast(str, row["task_id"]),
            task_lineage=cast(str, row["task_lineage"]),
            donor_match_kind=cast(object, row["donor_match_kind"]),  # type: ignore[arg-type]
            donor_task_id=cast(str | None, row["donor_task_id"]),
            donor_lineage=cast(str | None, row["donor_lineage"]),
            slot_arms=tuple(
                (cast(str, pair[0]), Arm(cast(str, pair[1])))
                for pair in cast(list[list[object]], row["slot_arms"])
            ),
            schedule_sha256=cast(str, row["schedule_sha256"]),
            prefix_index_sha256=cast(str, row["prefix_index_sha256"]),
        )
        for row in cast(list[dict[str, object]], payload["assignments"])
    )
    allocations = tuple(
        AllocationReceipt(
            task_id=cast(str, row["task_id"]),
            slot_ids_by_ordinal=cast(
                tuple[str, str, str, str],
                tuple(cast(list[str], row["slot_ids_by_ordinal"])),
            ),
            treatment_allocation_index=cast(
                int,
                row["treatment_allocation_index"],
            ),
            allocation_rejection_counter=cast(
                int,
                row["allocation_rejection_counter"],
            ),
            no_packet_orientation_bit=cast(
                int,
                row["no_packet_orientation_bit"],
            ),
            orientation_rejection_counter=cast(
                int,
                row["orientation_rejection_counter"],
            ),
            slot_capabilities=tuple(
                (cast(str, pair[0]), cast(str, pair[1]))
                for pair in cast(list[list[object]], row["slot_capabilities"])
            ),
        )
        for row in cast(
            list[dict[str, object]],
            payload["allocation_receipts"],
        )
    )
    donor_receipts: list[DonorMatchReceipt] = []
    for row in cast(
        list[dict[str, object]],
        payload["donor_match_receipts"],
    ):
        if row["kind"] == "not_applicable_no_trigger":
            donor_receipts.append(
                NoTriggerDonorReceipt(
                    kind="not_applicable_no_trigger",
                    task_id=cast(str, row["task_id"]),
                    trigger_reason="no_intervention_opportunity",
                    assignment_prefix_view_sha256=cast(
                        str,
                        row["assignment_prefix_view_sha256"],
                    ),
                )
            )
            continue
        candidates = tuple(
            DonorCandidateReceipt(
                donor_task_id=cast(str, candidate["donor_task_id"]),
                donor_lineage=cast(str, candidate["donor_lineage"]),
                primary_cost=cast(
                    tuple[int, int, int],
                    tuple(cast(list[int], candidate["primary_cost"])),
                ),
                fallback_code=cast(object, candidate["fallback_code"]),  # type: ignore[arg-type]
                tie_hmac_sha256=cast(str, candidate["tie_hmac_sha256"]),
            )
            for candidate in cast(
                list[dict[str, object]],
                row["candidates"],
            )
        )
        donor_receipts.append(
            MatchedDonorReceipt(
                kind="matched",
                task_id=cast(str, row["task_id"]),
                donor_task_id=cast(str, row["donor_task_id"]),
                task_lineage=cast(str, row["task_lineage"]),
                donor_lineage=cast(str, row["donor_lineage"]),
                assignment_mode=AssignmentMode(
                    cast(str, row["assignment_mode"])
                ),
                matching_algorithm=MatchingAlgorithm(
                    cast(str, row["matching_algorithm"])
                ),
                stratum_key=tuple(cast(list[str], row["stratum_key"])),
                assignment_prefix_view_sha256=cast(
                    str,
                    row["assignment_prefix_view_sha256"],
                ),
                candidates=candidates,
                chosen_primary_cost=cast(
                    tuple[int, int, int],
                    tuple(cast(list[int], row["chosen_primary_cost"])),
                ),
                matching_proof_ref=_artifact_ref(
                    row["matching_proof_ref"],
                    field="typed matching_proof_ref",
                ),
            )
        )
    return AssignmentLedger(
        study_id=cast(str, document["study_id"]),
        frozen_created_at=cast(str, document["frozen_created_at"]),
        manifest_ref=_artifact_ref(payload["manifest_ref"], field="manifest_ref"),
        schedule_ref=_artifact_ref(payload["schedule_ref"], field="schedule_ref"),
        prefix_index_ref=_artifact_ref(
            payload["prefix_index_ref"],
            field="prefix_index_ref",
        ),
        matching_program_ref=_artifact_ref(
            payload["matching_program_ref"],
            field="matching_program_ref",
        ),
        assignment_master_key_commitment_sha256=cast(
            str,
            payload["assignment_master_key_commitment_sha256"],
        ),
        assignment_prefix_view_sha256=cast(
            str,
            payload["assignment_prefix_view_sha256"],
        ),
        assignment_mode=AssignmentMode(
            cast(str, payload["assignment_mode"])
        ),
        matching_proof_refs=tuple(
            _artifact_ref(value, field="matching_proof_refs item")
            for value in cast(list[object], payload["matching_proof_refs"])
        ),
        assignments=assignments,
        allocation_receipts=allocations,
        donor_match_receipts=tuple(donor_receipts),
    )
