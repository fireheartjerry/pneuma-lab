"""Storage-bound branch assignment publication for the resampling-null study."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
import hashlib
import hmac
from pathlib import Path
from typing import cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import (
    RecordValidationError,
    _load_direct_scientific_parent,
    _load_json_bytes,
    _read_ref,
    _scientific_documents,
    validate_record,
)
from .assignment import (
    BytesField,
    TextField,
    _AssignmentKeyBuffers,
    _allocate_task,
    _derive_assignment_subkeys_into,
    _read_exact_master_into,
    _solve_synthetic_stratum,
    _wipe_bytearray,
    assignment_prefix_view_sha256,
    commitment_sha256,
    kdf_frame,
    load_assignment_authority,
    require_schedulable_power_final,
)
from .secrets import (
    AssignmentSecretHandle,
    _require_handle_binding,
)
from .storage import (
    LocalTestStorageLease,
    StoragePolicyLease,
    _exclusive_write,
    _load_operational_object,
    _publish_local_test_scientific,
)
from .task_schedule_codec import decode_task_schedule
from .types import (
    ArtifactRef,
    AssignmentPrefixTaskView,
    AssignmentPrefixView,
    GroupKind,
    TaskSchedule,
    TriggerReason,
)


_PROOF_MEDIA_TYPE = "application/vnd.pneuma.assignment-matching-proof+json"
_LEDGER_MEDIA_TYPE = "application/json"


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return asdict(ref)


def _artifact_ref(value: object, *, field: str) -> ArtifactRef:
    if not isinstance(value, dict):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    try:
        return ArtifactRef(**value)
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is malformed: {exc}") from exc


def _load_object_ref(
    ref: ArtifactRef,
    *,
    run_root: Path,
    field: str,
) -> dict[str, object]:
    path, raw = _read_ref(ref, run_root=run_root)
    value = _load_json_bytes(raw, source=path)
    if not isinstance(value, dict):
        raise RecordValidationError(f"{field} must reference an object")
    return value


def _component_class(components: object, *, field: str) -> str:
    if not isinstance(components, list) or not components:
        raise RecordValidationError(f"{field} must be a non-empty component array")
    prior: tuple[bytes, bytes] | None = None
    normalized: list[list[object]] = []
    for index, component in enumerate(components):
        if not isinstance(component, Mapping) or set(component) != {
            "kind",
            "value",
            "count",
        }:
            raise RecordValidationError(f"{field}[{index}] has wrong shape")
        kind = component["kind"]
        value = component["value"]
        count = component["count"]
        if (
            type(kind) is not str
            or not kind
            or type(value) is not str
            or not value
            or type(count) is not int
            or count <= 0
        ):
            raise RecordValidationError(f"{field}[{index}] is malformed")
        order = (kind.encode("utf-8"), value.encode("utf-8"))
        if prior is not None and order <= prior:
            raise RecordValidationError(
                f"{field} must be strict UTF-8 (kind,value) sorted"
            )
        prior = order
        normalized.append([kind, value, count])
    digest = hashlib.sha256(
        canonical_json_bytes(normalized, indent=None)
    ).hexdigest()
    return f"sha256:{digest}"


def _prefix_task_view(
    schedule: TaskSchedule,
    receipt: object,
    *,
    schedule_sha256: str,
    run_root: Path,
) -> AssignmentPrefixTaskView:
    if not isinstance(receipt, Mapping):
        raise RecordValidationError("prefix task receipt must be an object")
    task_id = schedule.task.task_id
    if (
        receipt.get("task_id") != task_id
        or receipt.get("schedule_sha256") != schedule_sha256
    ):
        raise RecordValidationError("prefix task ancestry differs from schedule")
    for name in (
        "snapshot_ref",
        "visible_context_ref",
        "provider_cost_ref",
    ):
        _read_ref(
            _artifact_ref(
                receipt.get(name),
                field=f"prefix {name} {task_id}",
            ),
            run_root=run_root,
        )
    y0_grade = receipt.get("y0_grade")
    if not isinstance(y0_grade, Mapping):
        raise RecordValidationError("prefix y0_grade must be an object")
    _read_ref(
        _artifact_ref(
            y0_grade.get("artifact_ref"),
            field=f"prefix y0 grade artifact {task_id}",
        ),
        run_root=run_root,
    )
    verifier = receipt.get("verifier_receipt")
    if not isinstance(verifier, Mapping) or (
        verifier.get("task_id") != task_id
        or verifier.get("schedule_sha256") != schedule_sha256
    ):
        raise RecordValidationError("nested verifier ancestry differs from schedule")
    _read_ref(
        _artifact_ref(
            verifier.get("snapshot_ref"),
            field=f"prefix verifier snapshot {task_id}",
        ),
        run_root=run_root,
    )
    verifier_ref = _artifact_ref(
        verifier.get("verifier_artifact_ref"),
        field=f"prefix verifier {task_id}",
    )
    features = _load_object_ref(
        verifier_ref,
        run_root=run_root,
        field=f"prefix verifier features {task_id}",
    )
    expected_feature_fields = {
        "record_kind",
        "schema_version",
        "task_id",
        "benchmark",
        "source_verifier_ref",
        "source_report_ref",
        "components",
        "objective_finding_count",
        "normalized_report_token_count",
    }
    if (
        set(features) != expected_feature_fields
        or features.get("record_kind") != "assignment_verifier_features_v1"
        or features.get("schema_version") != "1"
        or features.get("task_id") != task_id
        or features.get("benchmark") != schedule.task.benchmark
        or features.get("objective_finding_count") != verifier.get("finding_count")
        or type(features.get("normalized_report_token_count")) is not int
        or cast(int, features["normalized_report_token_count"]) < 0
    ):
        raise RecordValidationError(
            f"prefix verifier features for {task_id!r} are not closed or bound"
        )
    source_verifier_ref = _artifact_ref(
        features["source_verifier_ref"],
        field=f"features source_verifier_ref {task_id}",
    )
    source_report_ref = _artifact_ref(
        features["source_report_ref"],
        field=f"features source_report_ref {task_id}",
    )
    source_verifier = _load_object_ref(
        source_verifier_ref,
        run_root=run_root,
        field=f"source verifier {task_id}",
    )
    source_report = _load_object_ref(
        source_report_ref,
        run_root=run_root,
        field=f"source report {task_id}",
    )
    if (
        set(source_verifier)
        != {
            "record_kind",
            "schema_version",
            "task_id",
            "benchmark",
            "components",
            "objective_findings",
        }
        or source_verifier.get("record_kind")
        != "synthetic_verifier_source_v1"
        or source_verifier.get("schema_version") != "1"
        or source_verifier.get("task_id") != task_id
        or source_verifier.get("benchmark") != schedule.task.benchmark
        or not isinstance(source_verifier.get("objective_findings"), list)
        or set(source_report)
        != {
            "record_kind",
            "schema_version",
            "task_id",
            "report_text",
        }
        or source_report.get("record_kind")
        != "synthetic_verifier_report_v1"
        or source_report.get("schema_version") != "1"
        or source_report.get("task_id") != task_id
        or type(source_report.get("report_text")) is not str
    ):
        raise RecordValidationError(
            f"synthetic verifier parents for {task_id!r} are not closed"
        )
    recomputed_finding_count = len(
        cast(list[object], source_verifier["objective_findings"])
    )
    recomputed_token_count = len(
        cast(str, source_report["report_text"]).split()
    )
    if (
        features["components"] != source_verifier["components"]
        or features["objective_finding_count"] != recomputed_finding_count
        or features["normalized_report_token_count"] != recomputed_token_count
        or verifier.get("finding_count") != recomputed_finding_count
    ):
        raise RecordValidationError(
            f"derived verifier features for {task_id!r} do not recompute"
        )
    try:
        trigger_reason = TriggerReason(cast(str, receipt.get("trigger_reason")))
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(
            f"prefix trigger reason for {task_id!r} is invalid"
        ) from exc
    issue_family = next(
        (
            group.value
            for group in schedule.task.sensitivity_groups
            if group.kind is GroupKind.ISSUE_FAMILY
        ),
        None,
    )
    return AssignmentPrefixTaskView(
        task_id=task_id,
        benchmark=schedule.task.benchmark,
        stratum=schedule.task.stratum,
        lineage=schedule.task.lineage,
        sensitivity_groups=schedule.task.sensitivity_groups,
        trigger_reason=trigger_reason,
        verifier_component_class=_component_class(
            features["components"],
            field=f"features components {task_id}",
        ),
        objective_finding_count=cast(int, features["objective_finding_count"]),
        normalized_report_token_count=cast(
            int,
            features["normalized_report_token_count"],
        ),
        telecom_issue_family=issue_family,
    )


def _stratum_component(task: AssignmentPrefixTaskView, field: str) -> str:
    direct = {
        "benchmark": task.benchmark,
        "stratum": task.stratum,
        "lineage": task.lineage,
        "verifier_component_class": task.verifier_component_class,
    }
    if field in direct:
        return direct[field]
    try:
        kind = GroupKind(field)
    except ValueError as exc:
        raise RecordValidationError(
            f"synthetic stratum field {field!r} is unsupported"
        ) from exc
    matches = [
        group.value for group in task.sensitivity_groups if group.kind is kind
    ]
    if len(matches) != 1:
        raise RecordValidationError(
            f"task {task.task_id!r} lacks one {field!r} stratum label"
        )
    return matches[0]


def _install_proof(
    proof: dict[str, object],
    *,
    run_root: Path,
) -> ArtifactRef:
    proof_bytes = canonical_json_bytes(proof, indent=None)
    digest = hashlib.sha256(proof_bytes).hexdigest()
    relative_path = f"blobs/matching/proof/{digest}.json"
    destination = run_root / relative_path
    if destination.exists():
        if destination.read_bytes() != proof_bytes:
            raise RecordValidationError("matching proof CAS bytes differ")
    else:
        _exclusive_write(destination, proof_bytes)
    return ArtifactRef(
        role="assignment_matching_proof",
        relative_path=relative_path,
        sha256=digest,
        byte_count=len(proof_bytes),
        media_type=_PROOF_MEDIA_TYPE,
    )


def _require_prefix_publication(
    *,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    run_root: Path,
) -> None:
    receipt_path = run_root / "operational" / "storage-policy" / "prefix.json"
    receipt, _receipt_bytes = _load_operational_object(receipt_path)
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
        raise RecordValidationError("prefix storage receipt shape is not closed")
    intent = receipt.get("intent")
    proof = receipt.get("publication_commit")
    if not isinstance(intent, dict) or not isinstance(proof, dict):
        raise RecordValidationError("prefix storage receipt parents must be objects")
    intent_bytes = canonical_json_bytes(intent, indent=None)
    intent_digest = hashlib.sha256(intent_bytes).hexdigest()
    expected_commit_id = hashlib.sha256(
        b"local-test-storage-commit-v1\x00" + bytes.fromhex(intent_digest)
    ).hexdigest()
    expected_relative_path = schedule_ref.relative_path
    normalized_root_sha256 = hashlib.sha256(
        run_root.as_posix().encode("utf-8")
    ).hexdigest()
    begin = intent.get("begin")
    end = intent.get("end")
    if not isinstance(begin, dict) or not isinstance(end, dict):
        raise RecordValidationError(
            "prefix storage intent lacks begin/end observations"
        )
    if (
        receipt.get("record_kind") != "storage_policy_receipt_v1"
        or receipt.get("schema_version") != "1"
        or receipt.get("transaction") != "prefix"
        or receipt.get("transaction_intent_sha256") != intent_digest
        or receipt.get("fresh_at_publication_commit") is not True
        or receipt.get("publication_commit_recorded") is not True
        or receipt.get("publication_commit_consumes_lease") is not True
        or receipt.get("fixed_receipt_is_acceptance_marker") is not True
        or intent.get("transaction") != "prefix"
        or intent.get("prepared_scientific_relative_path")
        != expected_relative_path
        or intent.get("prepared_scientific_sha256") != schedule_ref.sha256
        or intent.get("lease_id") != begin.get("lease_id")
        or intent.get("lease_id") != end.get("lease_id")
        or begin.get("observation") != "begin"
        or end.get("observation") != "end"
        or begin.get("manifest_sha256") != manifest_ref.sha256
        or end.get("manifest_sha256") != manifest_ref.sha256
        or begin.get("schedule_sha256") is not None
        or end.get("schedule_sha256") is not None
        or begin.get("normalized_run_root_sha256")
        != normalized_root_sha256
        or end.get("normalized_run_root_sha256")
        != normalized_root_sha256
        or begin.get("mode") != "local_test"
        or end.get("mode") != "local_test"
        or begin.get("test_only") is not True
        or end.get("test_only") is not True
        or proof.get("record_kind") != "storage_publication_commit_v1"
        or proof.get("schema_version") != "1"
        or proof.get("transaction") != "prefix"
        or proof.get("manifest_sha256") != manifest_ref.sha256
        or proof.get("schedule_sha256") is not None
        or proof.get("normalized_run_root_sha256")
        != normalized_root_sha256
        or proof.get("lease_id") != intent.get("lease_id")
        or proof.get("lease_generation")
        != intent.get("final_lease_generation")
        or proof.get("lease_expires_at_utc")
        != intent.get("final_lease_expires_at_utc")
        or proof.get("authority_ref") != begin.get("authority_ref")
        or proof.get("mount_identity_sha256")
        != end.get("mount_identity_sha256")
        or proof.get("mode") != "local_test"
        or proof.get("test_only") is not True
        or proof.get("transaction_intent_sha256") != intent_digest
        or proof.get("scientific_relative_path") != expected_relative_path
        or proof.get("scientific_sha256") != schedule_ref.sha256
        or proof.get("registry_commit_id") != expected_commit_id
        or proof.get("commit_recorded") is not True
        or proof.get("lease_consumed") is not True
        or proof.get("release_required") is not True
    ):
        raise RecordValidationError(
            "prefix storage receipt does not bind the accepted schedule"
        )
    proof_path = (
        run_root
        / "operational"
        / "storage-policy"
        / "registry"
        / "commits"
        / f"{expected_commit_id}.json"
    )
    stored_proof, stored_proof_bytes = _load_operational_object(proof_path)
    if (
        stored_proof != proof
        or stored_proof_bytes != canonical_json_bytes(proof, indent=None)
    ):
        raise RecordValidationError(
            "prefix registry proof differs from fixed receipt"
        )


def _candidate_receipts(
    focal: AssignmentPrefixTaskView,
    stratum_tasks: tuple[AssignmentPrefixTaskView, ...],
    *,
    donor_key: bytearray,
) -> list[dict[str, object]]:
    rows: list[tuple[bytes, bytes, dict[str, object]]] = []
    for donor in stratum_tasks:
        if donor.task_id == focal.task_id or donor.lineage == focal.lineage:
            continue
        tie = hmac.new(
            donor_key,
            kdf_frame(
                "donor-tie-v1",
                [TextField(focal.task_id), TextField(donor.task_id)],
            ),
            hashlib.sha256,
        ).digest()
        row: dict[str, object] = {
            "donor_task_id": donor.task_id,
            "donor_lineage": donor.lineage,
            "primary_cost": [
                0,
                abs(
                    focal.objective_finding_count
                    - donor.objective_finding_count
                ),
                abs(
                    focal.normalized_report_token_count
                    - donor.normalized_report_token_count
                ),
            ],
            "fallback_code": None,
            "tie_hmac_sha256": tie.hex(),
        }
        rows.append((tie, donor.task_id.encode("utf-8"), row))
    rows.sort(key=lambda item: (item[0], item[1]))
    if not rows:
        raise RecordValidationError(
            f"triggered task {focal.task_id!r} has no eligible donor"
        )
    return [row for _tie, _task_id, row in rows]


def seal_branch_assignment(
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    *,
    assignment_secret_handle: AssignmentSecretHandle,
    matching_backend_session: object | None,
    storage_policy_lease: StoragePolicyLease,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Seal one synthetic assignment ledger inside the assignment lease."""

    if matching_backend_session is not None:
        raise RecordValidationError(
            "synthetic assignment forbids a matching backend session"
        )
    if type(storage_policy_lease) is not LocalTestStorageLease:
        raise RecordValidationError(
            "confirmation assignment storage adapter is unavailable"
        )
    root = Path(run_root).resolve(strict=True)
    authority = load_assignment_authority(
        schedule_ref,
        prefix_index_ref,
        run_root=root,
    )
    if (
        storage_policy_lease._transaction != "assignment"
        or storage_policy_lease._manifest_sha256 != authority.manifest_ref.sha256
        or storage_policy_lease._schedule_sha256 != schedule_ref.sha256
        or storage_policy_lease._run_root != root
    ):
        raise RecordValidationError(
            "storage lease is not bound to this assignment authority"
        )
    _require_handle_binding(
        assignment_secret_handle,
        authority.manifest_ref,
        schedule_ref,
        run_root=root,
        purpose="assignment",
    )
    _require_prefix_publication(
        manifest_ref=authority.manifest_ref,
        schedule_ref=schedule_ref,
        run_root=root,
    )

    def prepare() -> bytes:
        schedule_document = _load_direct_scientific_parent(
            _ref_mapping(schedule_ref),
            run_root=root,
            field="schedule_ref",
            expected_kind="resampling_prefix_schedule",
        )
        manifest_document = _load_direct_scientific_parent(
            _ref_mapping(authority.manifest_ref),
            run_root=root,
            field="manifest_ref",
            expected_kind="resampling_study_manifest",
        )
        prefix_document = _load_direct_scientific_parent(
            _ref_mapping(prefix_index_ref),
            run_root=root,
            field="prefix_index_ref",
            expected_kind="resampling_prefix_receipt",
        )
        schedule_payload = cast(dict[str, object], schedule_document.value["payload"])
        manifest_payload = cast(dict[str, object], manifest_document.value["payload"])
        prefix_payload = cast(dict[str, object], prefix_document.value["payload"])
        forbidden_later_kinds = {
            "resampling_assignment_ledger",
            "resampling_packet_index",
            "resampling_task_block",
            "resampling_blinded_projection",
            "resampling_analysis_freeze",
            "resampling_analysis",
            "resampling_unblind_receipt",
            "resampling_artifact_root",
        }
        later = [
            document.relative_path
            for document in _scientific_documents(root, excluded=set()).values()
            if document.value["record_kind"] in forbidden_later_kinds
        ]
        if later:
            raise RecordValidationError(
                "assignment requires absence of ledger and later records: "
                + ", ".join(sorted(later))
            )
        if schedule_payload.get("schedule_authority") != "synthetic_validation":
            raise RecordValidationError(
                "confirmation assignment backend is unavailable"
            )
        matching_program_ref = _artifact_ref(
            manifest_payload.get("assignment_program_ref"),
            field="manifest assignment_program_ref",
        )
        matching_program = _load_object_ref(
            matching_program_ref,
            run_root=root,
            field="assignment program",
        )
        if (
            matching_program.get("assignment_mode") != "synthetic_derangement"
            or matching_program.get("matching_algorithm")
            != "synthetic_cyclic_offset_v1"
            or matching_program.get("backend_receipt_ref") is not None
        ):
            raise RecordValidationError(
                "assignment program is not closed synthetic mode"
            )
        normalizer = matching_program.get("verifier_normalizer_contract")
        if not isinstance(normalizer, Mapping):
            raise RecordValidationError(
                "assignment normalizer contract must be an object"
            )
        normalizer_ref = _artifact_ref(
            normalizer.get("normalizer_source_ref"),
            field="assignment normalizer source",
        )
        normalizer_source = _load_object_ref(
            normalizer_ref,
            run_root=root,
            field="assignment normalizer source",
        )
        tokenizer_ref = _artifact_ref(
            manifest_payload.get("tokenizer_ref"),
            field="manifest tokenizer_ref",
        )
        tokenizer_source = _load_object_ref(
            tokenizer_ref,
            run_root=root,
            field="manifest tokenizer",
        )
        if (
            normalizer.get("normalizer_source_sha256") != normalizer_ref.sha256
            or normalizer.get("report_tokenizer_sha256") != tokenizer_ref.sha256
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
                "synthetic normalizer/tokenizer implementation differs"
            )
        power_final_ref = _artifact_ref(
            schedule_payload.get("power_final_ref"),
            field="schedule power_final_ref",
        )
        selection = require_schedulable_power_final(
            authority.manifest_ref,
            power_final_ref,
            run_root=root,
        )
        if (
            selection.schedule_authority != "synthetic_validation"
            or schedule_payload.get("selected_tier") is not None
        ):
            raise RecordValidationError(
                "schedule no longer matches completed power authority"
            )
        stratum_fields = matching_program.get("stratum_keys")
        if not isinstance(stratum_fields, list) or not stratum_fields or not all(
            type(field) is str and field for field in stratum_fields
        ):
            raise RecordValidationError(
                "synthetic assignment stratum keys are malformed"
            )
        schedule_values = schedule_payload.get("tasks")
        receipt_values = prefix_payload.get("task_receipts")
        if (
            not isinstance(schedule_values, list)
            or not schedule_values
            or not isinstance(receipt_values, list)
            or len(receipt_values) != len(schedule_values)
        ):
            raise RecordValidationError(
                "schedule and prefix coverage are not exact and non-empty"
            )
        schedules = tuple(
            decode_task_schedule(value, field=f"schedule tasks[{index}]")
            for index, value in enumerate(schedule_values)
        )
        receipts_by_id: dict[str, object] = {}
        for receipt in receipt_values:
            if not isinstance(receipt, Mapping) or not isinstance(
                receipt.get("task_id"),
                str,
            ):
                raise RecordValidationError("prefix task receipt lacks task ID")
            task_id = cast(str, receipt["task_id"])
            if task_id in receipts_by_id:
                raise RecordValidationError("prefix task receipt IDs repeat")
            receipts_by_id[task_id] = receipt
        schedule_ids = tuple(schedule.task.task_id for schedule in schedules)
        if schedule_ids != selection.selected_task_ids:
            raise RecordValidationError(
                "schedule membership differs from completed power selection"
            )
        if tuple(receipts_by_id) != schedule_ids:
            raise RecordValidationError(
                "prefix task order/coverage differs from schedule"
            )
        task_views = tuple(
            _prefix_task_view(
                schedule,
                receipts_by_id[schedule.task.task_id],
                schedule_sha256=schedule_ref.sha256,
                run_root=root,
            )
            for schedule in schedules
        )
        view = AssignmentPrefixView(
            study_id=authority.study_id,
            schedule_sha256=schedule_ref.sha256,
            tasks=task_views,
        )
        view_sha256 = assignment_prefix_view_sha256(view)

        master = bytearray(32)
        keys = _AssignmentKeyBuffers()
        proof_refs: list[ArtifactRef] = []
        donors: dict[str, AssignmentPrefixTaskView] = {}
        proof_by_task: dict[str, ArtifactRef] = {}
        stratum_by_task: dict[str, tuple[str, ...]] = {}
        try:
            _read_exact_master_into(assignment_secret_handle, master)
            expected_commitment = commitment_sha256(
                "assignment-master-key",
                authority.study_id,
                BytesField(bytes(master)),
            )
            if (
                manifest_payload.get("assignment_master_key_commitment_sha256")
                != expected_commitment
            ):
                raise RecordValidationError(
                    "assignment master key does not match commitment"
                )
            _derive_assignment_subkeys_into(
                memoryview(master),
                authority.study_id,
                authority.manifest_ref,
                schedule_ref,
                keys,
            )
            strata: dict[tuple[str, ...], list[AssignmentPrefixTaskView]] = {}
            for task in task_views:
                if (
                    task.trigger_reason
                    is TriggerReason.NO_INTERVENTION_OPPORTUNITY
                ):
                    continue
                key = tuple(
                    _stratum_component(task, cast(str, field))
                    for field in stratum_fields
                )
                strata.setdefault(key, []).append(task)
                stratum_by_task[task.task_id] = key
            for stratum_key in sorted(
                strata,
                key=lambda key: tuple(component.encode("utf-8") for component in key),
            ):
                stratum_tasks = tuple(strata[stratum_key])
                proof, selected = _solve_synthetic_stratum(
                    tasks=stratum_tasks,
                    stratum_key=stratum_key,
                    assignment_prefix_view_sha256=view_sha256,
                    assignment_program_sha256=matching_program_ref.sha256,
                    donor_key=keys.donor,
                )
                proof_ref = _install_proof(proof, run_root=root)
                proof_refs.append(proof_ref)
                donors.update(selected)
                for task in stratum_tasks:
                    proof_by_task[task.task_id] = proof_ref

            assignments: list[dict[str, object]] = []
            allocations: list[dict[str, object]] = []
            donor_receipts: list[dict[str, object]] = []
            capabilities: set[str] = set()
            task_view_by_id = {task.task_id: task for task in task_views}
            for schedule, task in zip(schedules, task_views, strict=True):
                donor = donors.get(task.task_id)
                if (
                    task.trigger_reason
                    is TriggerReason.NO_INTERVENTION_OPPORTUNITY
                ) != (donor is None):
                    raise RecordValidationError(
                        "trigger state and donor assignment differ"
                    )
                assignment, allocation = _allocate_task(
                    study_id=authority.study_id,
                    manifest_sha256=authority.manifest_ref.sha256,
                    schedule_sha256=schedule_ref.sha256,
                    prefix_index_sha256=prefix_index_ref.sha256,
                    task_schedule=schedule,
                    donor_task=donor,
                    allocation_key=keys.allocation,
                    orientation_key=keys.orientation,
                    capability_key=keys.capability,
                )
                task_capabilities = {
                    capability for _slot_id, capability in allocation.slot_capabilities
                }
                if capabilities & task_capabilities:
                    raise RecordValidationError(
                        "slot capabilities are not globally unique"
                    )
                capabilities.update(task_capabilities)
                assignments.append(
                    {
                        **asdict(assignment),
                        "slot_arms": [
                            [slot_id, arm.value]
                            for slot_id, arm in assignment.slot_arms
                        ],
                    }
                )
                allocations.append(
                    {
                        **asdict(allocation),
                        "slot_ids_by_ordinal": list(
                            allocation.slot_ids_by_ordinal
                        ),
                        "slot_capabilities": [
                            list(row) for row in allocation.slot_capabilities
                        ],
                    }
                )
                if donor is None:
                    donor_receipts.append(
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
                    candidates = _candidate_receipts(
                        task,
                        tuple(
                            task_view_by_id[task_id]
                            for task_id, key in stratum_by_task.items()
                            if key == stratum_by_task[task.task_id]
                        ),
                        donor_key=keys.donor,
                    )
                    chosen = next(
                        candidate
                        for candidate in candidates
                        if candidate["donor_task_id"] == donor.task_id
                    )
                    proof_ref = proof_by_task[task.task_id]
                    donor_receipts.append(
                        {
                            "kind": "matched",
                            "task_id": task.task_id,
                            "donor_task_id": donor.task_id,
                            "task_lineage": task.lineage,
                            "donor_lineage": donor.lineage,
                            "assignment_mode": "synthetic_derangement",
                            "matching_algorithm": "synthetic_cyclic_offset_v1",
                            "stratum_key": list(stratum_by_task[task.task_id]),
                            "assignment_prefix_view_sha256": view_sha256,
                            "candidates": candidates,
                            "chosen_primary_cost": chosen["primary_cost"],
                            "matching_proof_ref": _ref_mapping(proof_ref),
                        }
                    )
        finally:
            keys.wipe()
            _wipe_bytearray(master)

        record: dict[str, object] = {
            "record_kind": "resampling_assignment_ledger",
            "schema_version": "0.1.0",
            "study_id": manifest_document.value["study_id"],
            "frozen_created_at": manifest_document.value["frozen_created_at"],
            "provenance": manifest_document.value["provenance"],
            "payload": {
                "manifest_ref": _ref_mapping(authority.manifest_ref),
                "schedule_ref": _ref_mapping(schedule_ref),
                "prefix_index_ref": _ref_mapping(prefix_index_ref),
                "matching_program_ref": _ref_mapping(matching_program_ref),
                "assignment_master_key_commitment_sha256": (
                    manifest_payload["assignment_master_key_commitment_sha256"]
                ),
                "assignment_prefix_view_sha256": view_sha256,
                "assignment_mode": "synthetic_derangement",
                "matching_proof_refs": [
                    _ref_mapping(ref) for ref in proof_refs
                ],
                "assignments": assignments,
                "allocation_receipts": allocations,
                "donor_match_receipts": donor_receipts,
            },
        }
        return canonical_json_bytes(validate_record(record), indent=2)

    return _publish_local_test_scientific(
        storage_policy_lease,
        out=out,
        role="resampling_assignment_ledger",
        media_type=_LEDGER_MEDIA_TYPE,
        prepare=prepare,
    )
