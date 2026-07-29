"""Deterministic prefix-schedule sealing for the resampling-null study."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
from pathlib import Path
import sys
from typing import cast
import unicodedata

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import (
    RecordValidationError,
    _load_direct_scientific_parent,
    _load_json_bytes,
    _read_ref,
    validate_record,
)
from .assignment import (
    TextField,
    U64Field,
    commitment_sha256,
    derive_seed,
    kdf_frame,
    require_schedulable_power_final,
)
from .execution_authority import _validate_provider_lane_plan
from .preflight import _validate_assignment_program, _validate_task_registry
from .storage import (
    LocalTestStorageLease,
    StoragePolicyLease,
    _publish_local_test_scientific,
)
from .types import ArtifactRef


_GROUP_ORDER = {
    "language": 0,
    "domain": 1,
    "issue_family": 2,
}


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return {
        "role": ref.role,
        "relative_path": ref.relative_path,
        "sha256": ref.sha256,
        "byte_count": ref.byte_count,
        "media_type": ref.media_type,
    }


def _artifact_ref(value: object, *, field: str) -> ArtifactRef:
    if not isinstance(value, dict):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    try:
        return ArtifactRef(**value)
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is malformed: {exc}") from exc


def _load_manifest_asset(
    manifest_payload: Mapping[str, object],
    *,
    field: str,
    run_root: Path,
) -> tuple[ArtifactRef, dict[str, object]]:
    ref = _artifact_ref(manifest_payload.get(field), field=f"manifest {field}")
    path, raw = _read_ref(ref, run_root=run_root)
    value = _load_json_bytes(raw, source=path)
    if not isinstance(value, dict):
        raise RecordValidationError(f"manifest {field} must reference an object")
    return ref, value


def _task_order_key(task: Mapping[str, object]) -> tuple[bytes, bytes, bytes, bytes]:
    return cast(
        tuple[bytes, bytes, bytes, bytes],
        tuple(
            cast(str, task[field]).encode("utf-8")
            for field in ("benchmark", "stratum", "lineage", "task_id")
        ),
    )


def _membership_digest(
    selected_tasks: list[dict[str, object]],
    *,
    authority: str,
    selected_tier: int | None,
) -> str:
    rows = [
        {
            "benchmark": task["benchmark"],
            "groups": task["groups"],
            "task_id": task["task_id"],
        }
        for task in sorted(
            selected_tasks,
            key=lambda task: (
                cast(str, task["benchmark"]).encode("utf-8"),
                cast(str, task["task_id"]).encode("utf-8"),
            ),
        )
    ]
    preimage = {
        "rows": rows,
        "schedule_authority": authority,
        "schema_version": "1",
        "selected_tier": selected_tier,
    }
    return hashlib.sha256(canonical_json_bytes(preimage, indent=None)).hexdigest()


def _slot_frame_digest(schedule_seed: int, task_id: str, role: str) -> bytes:
    return hashlib.sha256(
        kdf_frame(
            "derive-seed-v1",
            [
                U64Field(schedule_seed),
                TextField(task_id),
                TextField(role),
            ],
        )
    ).digest()


def seal_prefix_schedule(
    manifest_ref: ArtifactRef,
    power_final_ref: ArtifactRef,
    *,
    schedule_seed_reveal: int,
    storage_policy_lease: StoragePolicyLease,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Derive and publish the immutable prefix schedule under a live lease."""

    if type(storage_policy_lease) is not LocalTestStorageLease:
        raise RecordValidationError(
            "confirmation schedule publication adapter is unavailable"
        )
    root = Path(run_root).resolve(strict=True)
    if (
        storage_policy_lease._transaction != "prefix"
        or storage_policy_lease._manifest_sha256 != manifest_ref.sha256
        or storage_policy_lease._schedule_sha256 is not None
        or storage_policy_lease._run_root != root
    ):
        raise RecordValidationError(
            "storage lease is not bound to this prefix authority"
        )

    def prepare() -> bytes:
        manifest = _load_direct_scientific_parent(
            _ref_mapping(manifest_ref),
            run_root=root,
            field="manifest_ref",
            expected_kind="resampling_study_manifest",
        )
        manifest_payload = cast(dict[str, object], manifest.value["payload"])
        selection = require_schedulable_power_final(
            manifest_ref,
            power_final_ref,
            run_root=root,
        )
        if (
            type(schedule_seed_reveal) is not int
            or schedule_seed_reveal < 0
            or schedule_seed_reveal >= 2**64
        ):
            raise RecordValidationError("schedule seed reveal must be exact U64")
        expected_commitment = commitment_sha256(
            "schedule-seed",
            cast(str, manifest.value["study_id"]),
            U64Field(schedule_seed_reveal),
        )
        if manifest_payload["schedule_seed_commitment_sha256"] != expected_commitment:
            raise RecordValidationError("schedule seed reveal does not match commitment")

        _task_registry_ref, task_registry = _load_manifest_asset(
            manifest_payload,
            field="task_registry_ref",
            run_root=root,
        )
        _validate_task_registry(task_registry)
        _assignment_ref, assignment_program = _load_manifest_asset(
            manifest_payload,
            field="assignment_program_ref",
            run_root=root,
        )
        if set(assignment_program) != {
            "record_kind",
            "schema_version",
            "assignment_mode",
            "matching_algorithm",
            "finding_count_band_upper_bounds",
            "report_length_band_upper_bounds",
            "verifier_normalizer_contract",
            "assignment_runtime_contract",
            "backend_receipt_ref",
            "stratum_keys",
        }:
            raise RecordValidationError(
                "assignment program has an open or incomplete shape"
            )
        if assignment_program["record_kind"] != "resampling_assignment_program_v1":
            raise RecordValidationError("assignment program has wrong identity")
        _validate_assignment_program(assignment_program)
        normalizer = cast(
            dict[str, object],
            assignment_program["verifier_normalizer_contract"],
        )
        normalizer_ref = _artifact_ref(
            normalizer.get("normalizer_source_ref"),
            field="assignment normalizer_source_ref",
        )
        _read_ref(normalizer_ref, run_root=root)
        if normalizer["normalizer_source_sha256"] != normalizer_ref.sha256:
            raise RecordValidationError("assignment normalizer digest differs from ref")
        revision_values = manifest_payload["source_revision_refs"]
        if not isinstance(revision_values, list):
            raise RecordValidationError("manifest source_revision_refs must be an array")
        revision_refs = [
            _artifact_ref(value, field="manifest source_revision_refs item")
            for value in revision_values
        ]
        if normalizer_ref not in revision_refs:
            raise RecordValidationError(
                "assignment normalizer is not a manifest source revision"
            )
        tokenizer_ref = _artifact_ref(
            manifest_payload.get("tokenizer_ref"),
            field="manifest tokenizer_ref",
        )
        _read_ref(tokenizer_ref, run_root=root)
        if normalizer["report_tokenizer_sha256"] != tokenizer_ref.sha256:
            raise RecordValidationError(
                "assignment report tokenizer differs from manifest tokenizer"
            )
        runtime = cast(
            dict[str, object],
            assignment_program["assignment_runtime_contract"],
        )
        expected_python = (
            f"{sys.version_info.major}.{sys.version_info.minor}."
            f"{sys.version_info.micro}"
        )
        if (
            runtime["implementation"] != "CPython"
            or runtime["python_version"] != expected_python
            or runtime["unicodedata_unidata_version"]
            != unicodedata.unidata_version
        ):
            raise RecordValidationError(
                "assignment runtime differs from the executing controller"
            )
        expected_assignment_mode = (
            "synthetic_derangement"
            if selection.schedule_authority == "synthetic_validation"
            else "confirmation_lineage_matching"
        )
        if assignment_program["assignment_mode"] != expected_assignment_mode:
            raise RecordValidationError(
                "assignment program mode does not match schedule authority"
            )
        _provider_ref, provider_plan = _load_manifest_asset(
            manifest_payload,
            field="provider_lane_plan_ref",
            run_root=root,
        )
        registry_tasks = cast(list[dict[str, object]], task_registry["tasks"])
        registry_by_id = {
            cast(str, task["task_id"]): task for task in registry_tasks
        }
        selected_ids = set(selection.selected_task_ids)
        if not selected_ids <= set(registry_by_id):
            raise RecordValidationError(
                "power-selected membership is not in the task registry"
            )
        selected_tasks = [registry_by_id[task_id] for task_id in selected_ids]
        selected_tasks.sort(key=_task_order_key)
        validated_plan = _validate_provider_lane_plan(
            provider_plan,
            run_root=root,
            registry=task_registry,
            tokenizer_ref=tokenizer_ref,
            manifest_revisions=tuple(revision_refs),
            schedule_authority=selection.schedule_authority,
        )
        lanes = tuple(lane.lane_id for lane in validated_plan.lanes)
        lane_bindings = {
            row.task_id: (
                row.prefix_lane_ordinal,
                row.lane_ordinals_by_execution_rank,
            )
            for row in validated_plan.task_lanes
        }
        schedule_tasks: list[dict[str, object]] = []
        for task in selected_tasks:
            task_id = cast(str, task["task_id"])
            prefix_lane_ordinal, lanes_by_rank = lane_bindings[task_id]
            order_digests = [
                _slot_frame_digest(
                    schedule_seed_reveal,
                    task_id,
                    f"execution-order-{ordinal}",
                )
                for ordinal in range(4)
            ]
            ranked_ordinals = sorted(
                range(4),
                key=lambda ordinal: (order_digests[ordinal], ordinal),
            )
            execution_rank = {
                ordinal: rank for rank, ordinal in enumerate(ranked_ordinals)
            }
            slots = []
            for ordinal in range(4):
                slot_digest = _slot_frame_digest(
                    schedule_seed_reveal,
                    task_id,
                    f"slot-{ordinal}",
                )
                rank = execution_rank[ordinal]
                slots.append(
                    {
                        "slot_id": slot_digest.hex(),
                        "seed": derive_seed(
                            schedule_seed_reveal,
                            task_id,
                            f"slot-{ordinal}",
                        ),
                        "execution_order": rank,
                        "hardware_lane": lanes_by_rank[rank],
                    }
                )
            groups = sorted(
                cast(list[dict[str, object]], task["groups"]),
                key=lambda group: (
                    _GROUP_ORDER[cast(str, group["kind"])],
                    cast(str, group["value"]).encode("utf-8"),
                ),
            )
            schedule_tasks.append(
                {
                    "task": {
                        "task_id": task_id,
                        "benchmark": task["benchmark"],
                        "stratum": task["stratum"],
                        "lineage": task["lineage"],
                        "sensitivity_groups": groups,
                    },
                    "prefix_seed": derive_seed(
                        schedule_seed_reveal,
                        task_id,
                        "prefix",
                    ),
                    "slots": slots,
                    "provider_lane": lanes[prefix_lane_ordinal],
                }
            )
        record: dict[str, object] = {
            "record_kind": "resampling_prefix_schedule",
            "schema_version": "0.1.0",
            "study_id": manifest.value["study_id"],
            "frozen_created_at": manifest.value["frozen_created_at"],
            "provenance": manifest.value["provenance"],
            "payload": {
                "manifest_ref": _ref_mapping(manifest_ref),
                "power_final_ref": _ref_mapping(power_final_ref),
                "schedule_authority": selection.schedule_authority,
                "selected_tier": selection.selected_tier,
                "selected_membership_sha256": _membership_digest(
                    selected_tasks,
                    authority=selection.schedule_authority,
                    selected_tier=selection.selected_tier,
                ),
                "schedule_seed": schedule_seed_reveal,
                "tasks": schedule_tasks,
            },
        }
        return canonical_json_bytes(validate_record(record), indent=2)

    return _publish_local_test_scientific(
        storage_policy_lease,
        out=out,
        role="resampling_prefix_schedule",
        media_type="application/json",
        prepare=prepare,
    )
