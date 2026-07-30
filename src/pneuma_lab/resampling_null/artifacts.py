"""Canonical, fail-closed artifact IO for the resampling-null study."""

from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import mimetypes
from pathlib import Path, PurePosixPath
import tempfile
from typing import TYPE_CHECKING, Any, Literal, cast

from jsonschema import Draft202012Validator

from pneuma_lab import schemas as pneuma_schemas
from pneuma_lab.foundation.artifacts import (
    canonical_json_bytes,
    write_atomic_bytes,
    write_atomic_json,
    write_atomic_jsonl,
)

from .authority_refs import (
    AuthorityRefReader,
    exact_text,
    walk_artifact_refs as _walk_artifact_refs,
)
from .errors import RecordValidationError
from .json_io import (
    load_json_bytes as _load_json_bytes,
    plain_json as _plain_json,
    resolve_inside as _resolve_inside,
    run_root as _run_root,
)
from .preflight import (
    ASSIGNMENT_PROGRAM_GRAMMAR,
    validate_assignment_program,
    validate_task_registry,
)
from .prefix_contracts import AUTHORITY_ASSET_ROLE_MEDIA
from .provider_contracts import validate_provider_lane_plan
from .types import ArtifactRef

if TYPE_CHECKING:
    from .evidence import FrozenPrefixReceipt


SCHEMA_BY_KIND = {
    "resampling_study_manifest": "resampling-study-manifest.schema.json",
    "resampling_prefix_schedule": "resampling-prefix-schedule.schema.json",
    "resampling_prefix_receipt": "resampling-prefix-receipt.schema.json",
    "resampling_assignment_ledger": "resampling-assignment-ledger.schema.json",
    "resampling_packet_index": "resampling-packet-index.schema.json",
    "resampling_task_block": "resampling-task-block.schema.json",
    "resampling_blinded_projection": "resampling-blinded-projection.schema.json",
    "resampling_analysis_freeze": "resampling-analysis-freeze.schema.json",
    "resampling_analysis": "resampling-analysis.schema.json",
    "resampling_power_report": "resampling-power-report.schema.json",
    "resampling_unblind_receipt": "resampling-unblind-receipt.schema.json",
    "resampling_artifact_root": "resampling-artifact-root.schema.json",
}

_SCIENTIFIC_REF_KEYS = frozenset(
    {"role", "relative_path", "sha256", "byte_count", "media_type"}
)
_SINGLETON_KINDS = frozenset(
    {
        "resampling_study_manifest",
        "resampling_prefix_schedule",
        "resampling_prefix_receipt",
        "resampling_assignment_ledger",
        "resampling_blinded_projection",
        "resampling_analysis_freeze",
        "resampling_analysis",
        "resampling_unblind_receipt",
    }
)
_OPERATIONAL_TOP_LEVEL = frozenset({"operational"})
_RECEIPT_NAME = "p0-core-receipt.json"
_FROZEN_UPSTREAM_KINDS = tuple(
    sorted(kind for kind in SCHEMA_BY_KIND if kind != "resampling_artifact_root")
)


def canonical_digest(value: Mapping[str, object]) -> str:
    """Return the stable compact-JSON SHA-256 for one mapping."""

    return hashlib.sha256(canonical_json_bytes(dict(value), indent=None)).hexdigest()


def _validation_error_key(error: Any) -> tuple[tuple[str, ...], str]:
    return tuple(str(part) for part in error.absolute_path), error.message


def _semantic_unique(
    values: object,
    field: str,
    *,
    key: str,
) -> None:
    if not isinstance(values, list):
        return
    observed: list[object] = []
    for item in values:
        if isinstance(item, Mapping):
            observed.append(item.get(key))
    if len(observed) != len(set(observed)):
        raise RecordValidationError(f"{field} must have unique {key} values")


def _decode_prefix_receipt_record(
    receipt: Mapping[str, object],
    *,
    field: str,
) -> FrozenPrefixReceipt:
    """Decode the schema mapping through the exact runtime value contracts."""

    from .authority_refs import decode_artifact_ref
    from .evidence import FrozenPrefixReceipt
    from .types import (
        CallSeedReceipt,
        FailureKind,
        FrozenVerifierReceipt,
        GradeReceipt,
        PrefixCaps,
        ResourceCounters,
        ToolCall,
        TriggerReason,
    )

    def mapping(name: str, value: object) -> Mapping[str, object]:
        if not isinstance(value, Mapping):
            raise RecordValidationError(f"{field}.{name} must be a mapping")
        return value

    def ref(name: str, value: object, role: str) -> ArtifactRef:
        return decode_artifact_ref(
            value,
            field=f"{field}.{name}",
            expected_role=role,
        )

    def counters(name: str, value: object) -> ResourceCounters:
        item = mapping(name, value)
        return ResourceCounters(
            generated_tokens=cast(int, item["generated_tokens"]),
            model_calls=cast(int, item["model_calls"]),
            tool_calls=cast(int, item["tool_calls"]),
            wall_clock_ms=cast(int, item["wall_clock_ms"]),
        )

    def calls(name: str, value: object) -> tuple[ToolCall, ...]:
        return tuple(
            ToolCall(
                call_id=cast(str, mapping(f"{name}[{index}]", item)["call_id"]),
                name=cast(str, mapping(f"{name}[{index}]", item)["name"]),
                canonical_arguments_json=cast(
                    str,
                    mapping(f"{name}[{index}]", item)["canonical_arguments_json"],
                ),
            )
            for index, item in enumerate(cast(list[object], value))
        )

    try:
        caps = mapping("prefix_caps", receipt["prefix_caps"])
        grade = mapping("y0_grade", receipt["y0_grade"])
        verifier = mapping("verifier_receipt", receipt["verifier_receipt"])
        return FrozenPrefixReceipt(
            task_id=cast(str, receipt["task_id"]),
            schedule_sha256=cast(str, receipt["schedule_sha256"]),
            prefix_caps=PrefixCaps(
                generated_tokens=cast(int, caps["generated_tokens"]),
                model_calls=cast(int, caps["model_calls"]),
                tool_calls=cast(int, caps["tool_calls"]),
                wall_clock_ms=cast(int, caps["wall_clock_ms"]),
            ),
            snapshot_ref=ref(
                "snapshot_ref",
                receipt["snapshot_ref"],
                "composite_snapshot",
            ),
            visible_context_ref=ref(
                "visible_context_ref",
                receipt["visible_context_ref"],
                "visible_context",
            ),
            visible_sha256=cast(str, receipt["visible_sha256"]),
            token_ids_ref=ref(
                "token_ids_ref",
                receipt["token_ids_ref"],
                "token_ids",
            ),
            token_ids_sha256=cast(str, receipt["token_ids_sha256"]),
            branch_pending_calls=calls(
                "branch_pending_calls",
                receipt["branch_pending_calls"],
            ),
            terminal_unexecuted_remainder=calls(
                "terminal_unexecuted_remainder",
                receipt["terminal_unexecuted_remainder"],
            ),
            trigger_reason=TriggerReason(cast(str, receipt["trigger_reason"])),
            terminal_failure_kind=FailureKind(
                cast(str, receipt["terminal_failure_kind"])
            ),
            y0_grade=GradeReceipt(
                success=cast(int, grade["success"]),
                partial_reward=cast(float, grade["partial_reward"]),
                infrastructure_failure=cast(
                    bool,
                    grade["infrastructure_failure"],
                ),
                artifact_ref=ref(
                    "y0_grade.artifact_ref",
                    grade["artifact_ref"],
                    "grade_evidence",
                ),
            ),
            grade_execution_receipt_ref=ref(
                "grade_execution_receipt_ref",
                receipt["grade_execution_receipt_ref"],
                "grade_evidence_receipt",
            ),
            verifier_receipt=FrozenVerifierReceipt(
                task_id=cast(str, verifier["task_id"]),
                schedule_sha256=cast(str, verifier["schedule_sha256"]),
                snapshot_ref=ref(
                    "verifier_receipt.snapshot_ref",
                    verifier["snapshot_ref"],
                    "composite_snapshot",
                ),
                verifier_artifact_ref=ref(
                    "verifier_receipt.verifier_artifact_ref",
                    verifier["verifier_artifact_ref"],
                    "verifier_evidence",
                ),
                finding_count=cast(int, verifier["finding_count"]),
            ),
            verifier_execution_receipt_ref=ref(
                "verifier_execution_receipt_ref",
                receipt["verifier_execution_receipt_ref"],
                "verifier_evidence_receipt",
            ),
            counters=counters("counters", receipt["counters"]),
            simulator_counters=counters(
                "simulator_counters",
                receipt["simulator_counters"],
            ),
            call_seeds=tuple(
                CallSeedReceipt(
                    subject_role=cast(
                        Literal["primary_subject", "user_simulator"],
                        mapping(f"call_seeds[{index}]", seed)["subject_role"],
                    ),
                    call_index=cast(
                        int,
                        mapping(f"call_seeds[{index}]", seed)["call_index"],
                    ),
                    seed=cast(
                        int,
                        mapping(f"call_seeds[{index}]", seed)["seed"],
                    ),
                )
                for index, seed in enumerate(cast(list[object], receipt["call_seeds"]))
            ),
            provider_attempts_ref=ref(
                "provider_attempts_ref",
                receipt["provider_attempts_ref"],
                "provider_attempt_ledger",
            ),
            boundary_ledger_ref=ref(
                "boundary_ledger_ref",
                receipt["boundary_ledger_ref"],
                "tool_boundary_ledger",
            ),
            provider_cost_ref=ref(
                "provider_cost_ref",
                receipt["provider_cost_ref"],
                "provider_cost_closure",
            ),
        )
    except RecordValidationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordValidationError(
            f"{field} runtime record is invalid: {exc}"
        ) from exc


def _validate_prefix_receipt_semantics(
    receipt: Mapping[str, object],
    *,
    field: str,
    schedule_sha256: str,
) -> None:
    runtime = _decode_prefix_receipt_record(receipt, field=field)
    if runtime.schedule_sha256 != schedule_sha256:
        raise RecordValidationError(
            f"{field}.schedule_sha256 differs from payload.schedule_ref"
        )
    if runtime.verifier_receipt.schedule_sha256 != schedule_sha256:
        raise RecordValidationError(
            f"{field}.verifier_receipt.schedule_sha256 differs from "
            "payload.schedule_ref"
        )


def _validate_semantics(value: dict[str, object]) -> None:
    kind = cast(str, value["record_kind"])
    payload = cast(dict[str, object], value["payload"])
    if kind == "resampling_prefix_schedule":
        tasks = cast(list[object], payload["tasks"])
        task_ids: list[object] = []
        for index, item in enumerate(tasks):
            if not isinstance(item, Mapping):
                continue
            task = item.get("task")
            if isinstance(task, Mapping):
                task_ids.append(task.get("task_id"))
                groups = task.get("sensitivity_groups")
                _semantic_unique(
                    groups,
                    f"payload.tasks[{index}].task.sensitivity_groups",
                    key="kind",
                )
            slots = item.get("slots")
            for slot_key in ("slot_id", "seed", "execution_order"):
                _semantic_unique(
                    slots,
                    f"payload.tasks[{index}].slots",
                    key=slot_key,
                )
        if len(task_ids) != len(set(task_ids)):
            raise RecordValidationError("payload.tasks must have unique task_id values")
    elif kind == "resampling_prefix_receipt":
        schedule_ref = cast(Mapping[str, object], payload["schedule_ref"])
        schedule_sha256 = cast(str, schedule_ref["sha256"])
        _semantic_unique(
            payload["task_receipts"],
            "payload.task_receipts",
            key="task_id",
        )
        for index, receipt in enumerate(
            cast(list[Mapping[str, object]], payload["task_receipts"])
        ):
            _validate_prefix_receipt_semantics(
                receipt,
                field=f"payload.task_receipts[{index}]",
                schedule_sha256=schedule_sha256,
            )
    elif kind == "resampling_assignment_ledger":
        assignments = cast(list[Mapping[str, object]], payload["assignments"])
        allocation_receipts = cast(
            list[Mapping[str, object]],
            payload["allocation_receipts"],
        )
        donor_match_receipts = cast(
            list[Mapping[str, object]],
            payload["donor_match_receipts"],
        )
        _semantic_unique(assignments, "payload.assignments", key="task_id")
        _semantic_unique(
            allocation_receipts,
            "payload.allocation_receipts",
            key="task_id",
        )
        _semantic_unique(
            donor_match_receipts,
            "payload.donor_match_receipts",
            key="task_id",
        )
        assignment_task_ids = [
            cast(str, assignment["task_id"]) for assignment in assignments
        ]
        allocation_task_ids = [
            cast(str, receipt["task_id"]) for receipt in allocation_receipts
        ]
        donor_receipt_task_ids = [
            cast(str, receipt["task_id"]) for receipt in donor_match_receipts
        ]
        if not (assignment_task_ids == allocation_task_ids == donor_receipt_task_ids):
            raise RecordValidationError(
                "assignment, allocation, and donor receipt task order must match"
            )
        allocation_by_task = {
            cast(str, receipt["task_id"]): receipt for receipt in allocation_receipts
        }
        donor_receipt_by_task = {
            cast(str, receipt["task_id"]): receipt for receipt in donor_match_receipts
        }

        for assignment in assignments:
            donor_match_kind = assignment["donor_match_kind"]
            if (
                donor_match_kind == "matched"
                and assignment["task_id"] == assignment["donor_task_id"]
            ):
                raise RecordValidationError(
                    "assignment task_id and donor_task_id must differ"
                )
            if (
                donor_match_kind == "matched"
                and assignment["task_lineage"] == assignment["donor_lineage"]
            ):
                raise RecordValidationError(
                    "assignment task and donor lineages must differ"
                )
            slot_arms = assignment.get("slot_arms")
            if isinstance(slot_arms, list):
                slot_ids = [
                    item[0]
                    for item in slot_arms
                    if isinstance(item, list) and len(item) == 2
                ]
                arms = [
                    item[1]
                    for item in slot_arms
                    if isinstance(item, list) and len(item) == 2
                ]
                if len(slot_ids) != len(set(slot_ids)):
                    raise RecordValidationError(
                        "assignment slot_arms must have unique slot IDs"
                    )
                if sorted(arms) != ["NONE", "REAL", "RESAMPLE", "SHAM"]:
                    raise RecordValidationError(
                        "assignment slot_arms must contain every arm exactly once"
                    )

            allocation = allocation_by_task[cast(str, assignment["task_id"])]
            allocation_slot_ids = cast(
                list[str],
                allocation["slot_ids_by_ordinal"],
            )
            capability_slot_ids = [
                cast(list[str], capability)[0]
                for capability in cast(
                    list[list[str]],
                    allocation["slot_capabilities"],
                )
            ]
            assignment_slot_ids = [
                cast(list[str], slot_arm)[0]
                for slot_arm in cast(list[list[str]], assignment["slot_arms"])
            ]
            if allocation_slot_ids != assignment_slot_ids:
                raise RecordValidationError(
                    "allocation slot_ids_by_ordinal must equal assignment slot order"
                )
            if capability_slot_ids != allocation_slot_ids:
                raise RecordValidationError(
                    "allocation slot capabilities must follow slot_ids_by_ordinal"
                )

            donor_receipt = donor_receipt_by_task[cast(str, assignment["task_id"])]
            if donor_receipt["kind"] != donor_match_kind:
                raise RecordValidationError(
                    "task assignment and donor receipt matching kinds differ"
                )
            if (
                donor_receipt["assignment_prefix_view_sha256"]
                != payload["assignment_prefix_view_sha256"]
            ):
                raise RecordValidationError(
                    "donor receipt assignment prefix view digest differs from ledger"
                )
            if donor_match_kind == "matched":
                for field in (
                    "task_id",
                    "task_lineage",
                    "donor_task_id",
                    "donor_lineage",
                ):
                    if donor_receipt[field] != assignment[field]:
                        raise RecordValidationError(
                            f"matched donor receipt {field} differs from assignment"
                        )
                if donor_receipt["assignment_mode"] != payload["assignment_mode"]:
                    raise RecordValidationError(
                        "matched donor receipt assignment mode differs from ledger"
                    )
                candidates = cast(
                    list[Mapping[str, object]],
                    donor_receipt["candidates"],
                )
                _semantic_unique(
                    candidates,
                    "payload.donor_match_receipts.candidates",
                    key="donor_task_id",
                )
                chosen = [
                    candidate
                    for candidate in candidates
                    if candidate["donor_task_id"] == donor_receipt["donor_task_id"]
                    and candidate["donor_lineage"] == donor_receipt["donor_lineage"]
                    and candidate["primary_cost"]
                    == donor_receipt["chosen_primary_cost"]
                ]
                if len(chosen) != 1:
                    raise RecordValidationError(
                        "matched donor and chosen cost must identify one candidate"
                    )

        matching_proof_refs = cast(
            list[Mapping[str, object]],
            payload["matching_proof_refs"],
        )
        matched_receipts = [
            receipt for receipt in donor_match_receipts if receipt["kind"] == "matched"
        ]
        if not matched_receipts and matching_proof_refs:
            raise RecordValidationError(
                "matching_proof_refs must be empty when every donor receipt is N/A"
            )
        if matched_receipts:
            triggered_strata = {
                tuple(cast(list[str], receipt["stratum_key"]))
                for receipt in matched_receipts
            }
            if len(matching_proof_refs) != len(triggered_strata):
                raise RecordValidationError(
                    "matching_proof_refs must contain exactly one ref per "
                    "triggered matching stratum"
                )
            for receipt in matched_receipts:
                if receipt["matching_proof_ref"] not in matching_proof_refs:
                    raise RecordValidationError(
                        "matched donor receipt points outside matching_proof_refs"
                    )
    elif kind == "resampling_packet_index":
        entries = payload.get("entries")
        _semantic_unique(entries, "payload.entries", key="task_id")
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, Mapping) or "real_ref" not in entry:
                    continue
                if entry.get("task_id") == entry.get("donor_task_id"):
                    raise RecordValidationError(
                        "packet pair task_id and donor_task_id must differ"
                    )
                if entry.get("real_token_count") != entry.get("sham_token_count"):
                    raise RecordValidationError(
                        "packet pair real/sham token counts must match"
                    )
                if entry.get("rewrite_expected") != entry.get("rewrite_completed"):
                    raise RecordValidationError(
                        "packet pair identifier rewrites must be complete"
                    )
    elif kind == "resampling_task_block":
        _semantic_unique(
            payload["sensitivity_groups"],
            "payload.sensitivity_groups",
            key="kind",
        )
        _semantic_unique(
            payload["slot_outcomes"],
            "payload.slot_outcomes",
            key="opaque_arm_id",
        )
        outcomes = cast(list[Mapping[str, object]], payload["slot_outcomes"])
        for outcome in outcomes:
            if (
                outcome.get("task_id") != payload["task_id"]
                or outcome.get("benchmark") != payload["benchmark"]
            ):
                raise RecordValidationError(
                    "slot outcome task/benchmark must match its task block"
                )
            if (
                outcome.get("infrastructure_failure") is True
                and outcome.get("success") != 0
            ):
                raise RecordValidationError(
                    "infrastructure-failure outcomes must have success == 0"
                )
            if outcome.get("prefix_success") != payload["prefix_success"]:
                raise RecordValidationError(
                    "slot outcome prefix_success must equal the task block's "
                    "frozen prefix_success"
                )
        attempts = payload.get("attempts")
        if isinstance(attempts, list):
            indices = [
                attempt.get("attempt_index")
                for attempt in attempts
                if isinstance(attempt, Mapping)
            ]
            if indices != list(range(len(indices))):
                raise RecordValidationError(
                    "payload.attempts must be chronological from attempt 0"
                )
            selected = payload.get("selected_attempt_index")
            if selected not in indices:
                raise RecordValidationError(
                    "selected_attempt_index must identify an embedded attempt"
                )
            selected_attempt = attempts[cast(int, selected)]
            if not isinstance(selected_attempt, Mapping):
                raise RecordValidationError(
                    "selected attempt must be an embedded attempt receipt"
                )
            failed_second = (
                selected == 1
                and len(attempts) == 2
                and selected_attempt.get("complete") is False
            )
            if not failed_second and selected_attempt.get("complete") is not True:
                raise RecordValidationError(
                    "successful selected attempt must be complete"
                )
            terminal_receipts = cast(
                list[Mapping[str, object]],
                payload["terminal_slot_receipts"],
            )
            selected_receipts = selected_attempt.get("terminal_receipts")
            if failed_second:
                if any(
                    not isinstance(attempt, Mapping)
                    or attempt.get("complete") is not False
                    for attempt in attempts
                ):
                    raise RecordValidationError(
                        "failed second-attempt finalization must preserve two "
                        "incomplete attempts"
                    )
                if any(
                    "failed_attempt_ref" not in terminal
                    for terminal in terminal_receipts
                ):
                    raise RecordValidationError(
                        "failed second-attempt finalization requires four "
                        "FailedSlotReceipt terminals"
                    )
            else:
                if selected_receipts != terminal_receipts:
                    raise RecordValidationError(
                        "successful terminal receipts must descend from the "
                        "selected complete attempt"
                    )
                if any(
                    "final_snapshot_ref" not in terminal
                    for terminal in terminal_receipts
                ):
                    raise RecordValidationError(
                        "successful finalization requires four unscored terminals"
                    )
            slot_ids = [receipt.get("slot_id") for receipt in terminal_receipts]
            capability_ids = [
                receipt.get("opaque_capability_id") for receipt in terminal_receipts
            ]
            if len(slot_ids) != len(set(slot_ids)) or len(capability_ids) != len(
                set(capability_ids)
            ):
                raise RecordValidationError(
                    "terminal receipts must identify four unique opaque slots"
                )
            selected_work_orders = selected_attempt.get("work_order_sha256s")
            selected_slot_identities = list(zip(slot_ids, capability_ids, strict=True))
            attempt_ref_signatures: list[str] = []
            for attempt_index, attempt in enumerate(attempts):
                if not isinstance(attempt, Mapping):
                    continue
                attempt_ref_signatures.append(
                    json.dumps(
                        attempt.get("attempt_ref"),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                if attempt.get("work_order_sha256s") != selected_work_orders:
                    raise RecordValidationError(
                        "every attempt must use the selected attempt's four "
                        "work-order positions"
                    )
                attempt_receipts = cast(
                    list[Mapping[str, object]],
                    attempt.get("terminal_receipts", []),
                )
                attempt_identities = [
                    (
                        receipt.get("slot_id"),
                        receipt.get("opaque_capability_id"),
                    )
                    for receipt in attempt_receipts
                ]
                canonical_positions = {
                    identity: index
                    for index, identity in enumerate(selected_slot_identities)
                }
                attempt_positions = [
                    canonical_positions.get(identity) for identity in attempt_identities
                ]
                if (
                    len(attempt_identities) != len(set(attempt_identities))
                    or any(position is None for position in attempt_positions)
                    or attempt_positions != sorted(cast(list[int], attempt_positions))
                ):
                    raise RecordValidationError(
                        "attempt terminal receipts must be a unique canonical-"
                        f"order subset of slot identities at attempt {attempt_index}"
                    )
            if len(attempt_ref_signatures) != len(set(attempt_ref_signatures)):
                raise RecordValidationError(
                    "attempt receipts must have unique attempt_ref identities"
                )
            execution_receipts = cast(
                list[Mapping[str, object]],
                payload["execution_receipts"],
            )
            if len(execution_receipts) != len(terminal_receipts):
                raise RecordValidationError(
                    "execution receipts must cover every terminal slot receipt"
                )
            for index, (terminal, execution, outcome) in enumerate(
                zip(terminal_receipts, execution_receipts, outcomes, strict=True)
            ):
                if execution.get("source_receipt_sha256") != canonical_digest(terminal):
                    raise RecordValidationError(
                        "execution receipt source digest does not bind its "
                        f"terminal receipt at slot {index}"
                    )
                if execution.get("outcome") != outcome:
                    raise RecordValidationError(
                        "execution receipt outcome differs from its top-level "
                        f"slot outcome at slot {index}"
                    )
                if outcome.get("opaque_arm_id") != terminal.get("opaque_capability_id"):
                    raise RecordValidationError(
                        f"opaque slot identity differs at slot {index}"
                    )
                expected_source_kind = (
                    "failed_second_attempt" if failed_second else "graded_unscored"
                )
                if execution.get("source_kind") != expected_source_kind:
                    raise RecordValidationError(
                        f"execution receipt source kind differs at slot {index}"
                    )
                if failed_second:
                    if terminal.get("failed_attempt_ref") != selected_attempt.get(
                        "attempt_ref"
                    ):
                        raise RecordValidationError(
                            "FailedSlotReceipt does not bind the incomplete "
                            "second attempt"
                        )
                    zero_counters = {
                        "generated_tokens": 0,
                        "model_calls": 0,
                        "tool_calls": 0,
                        "wall_clock_ms": 0,
                    }
                    if (
                        execution.get("grade_receipt") is not None
                        or outcome.get("success") != 0
                        or outcome.get("prefix_success") != payload["prefix_success"]
                        or outcome.get("partial_reward") != 0.0
                        or outcome.get("infrastructure_failure") is not True
                        or outcome.get("counters") != zero_counters
                        or outcome.get("artifact_ref")
                        != terminal.get("adverse_event_ref")
                    ):
                        raise RecordValidationError(
                            f"failed second-attempt slot {index} is not an "
                            "exact adverse-zero execution/outcome"
                        )
                else:
                    grade = execution.get("grade_receipt")
                    if not isinstance(grade, Mapping):
                        raise RecordValidationError(
                            "successful execution requires an exact grade receipt"
                        )
                    if (
                        outcome.get("success") != grade.get("success")
                        or outcome.get("partial_reward") != grade.get("partial_reward")
                        or outcome.get("infrastructure_failure")
                        != grade.get("infrastructure_failure")
                        or outcome.get("artifact_ref") != grade.get("artifact_ref")
                        or outcome.get("counters") != terminal.get("counters")
                    ):
                        raise RecordValidationError(
                            f"successful execution/grade/terminal receipts differ "
                            f"at slot {index}"
                        )
            outage = payload.get("outage_receipt")
            if len(attempts) == 1:
                if selected != 0 or outage is not None:
                    raise RecordValidationError(
                        "one-attempt success must select attempt 0 without outage"
                    )
            else:
                if selected != 1 or not isinstance(outage, Mapping):
                    raise RecordValidationError(
                        "a two-attempt task requires a selected rerun and outage receipt"
                    )
                first_attempt = cast(Mapping[str, object], attempts[0])
                if (
                    first_attempt.get("complete") is not False
                    or outage.get("task_id") != payload["task_id"]
                    or outage.get("first_attempt") != first_attempt
                    or outage.get("work_order_sha256s")
                    != first_attempt.get("work_order_sha256s")
                ):
                    raise RecordValidationError(
                        "outage receipt is not bound to the actual first attempt"
                    )
        if payload.get("triggered") is False:
            no_trigger_outcomes = cast(
                list[dict[str, object]],
                payload["slot_outcomes"],
            )
            if any(
                outcome.get("success") != payload["prefix_success"]
                for outcome in no_trigger_outcomes
            ):
                raise RecordValidationError(
                    "no-trigger slot outcomes must copy frozen Y_0 success "
                    "from task-block prefix_success"
                )
            copied_fields = (
                "success",
                "prefix_success",
                "partial_reward",
                "infrastructure_failure",
                "counters",
                "artifact_ref",
            )
            signatures = [
                tuple(
                    json.dumps(outcome.get(field), sort_keys=True)
                    for field in copied_fields
                )
                for outcome in no_trigger_outcomes
            ]
            if len(set(signatures)) != 1:
                raise RecordValidationError(
                    "no-trigger slot_outcomes must be four copied Y_0 outcomes"
                )
    elif kind == "resampling_blinded_projection":
        _semantic_unique(
            payload["task_block_refs"], "task_block_refs", key="relative_path"
        )
        _semantic_unique(payload["rows"], "rows", key="task_id")
        rows = cast(list[object], payload["rows"])
        if len(rows) != cast(int, payload["expected_task_count"]):
            raise RecordValidationError(
                "expected_task_count must equal the number of rows"
            )
        if len(cast(list[object], payload["task_block_refs"])) != len(rows):
            raise RecordValidationError(
                "task_block_refs and rows must have equal coverage"
            )
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            slots = row.get("slots")
            if isinstance(slots, list):
                labels = [
                    slot.get("label") for slot in slots if isinstance(slot, Mapping)
                ]
                if labels != ["A", "B", "C", "D"]:
                    raise RecordValidationError(
                        "blinded slots must be ordered A, B, C, D"
                    )
                for slot in slots:
                    if isinstance(slot, Mapping) and isinstance(slot.get("outcome"), Mapping):
                        if "artifact_ref" in cast(Mapping[str, object], slot["outcome"]):
                            raise RecordValidationError(
                                "blinded outcomes must not expose artifact references"
                            )
    elif kind == "resampling_artifact_root":
        entries = cast(list[dict[str, object]], payload["entries"])
        paths = [cast(str, entry["relative_path"]) for entry in entries]
        if paths != sorted(paths) or len(paths) != len(set(paths)):
            raise RecordValidationError(
                "artifact-root entries must have unique sorted relative paths"
            )
        if _RECEIPT_NAME in paths:
            raise RecordValidationError("artifact root must exclude its own receipt")
        required = cast(list[str], payload["required_document_kinds"])
        if required != sorted(required):
            raise RecordValidationError("required_document_kinds must be sorted")
    elif kind == "resampling_power_report":
        stage = payload["stage"]
        if stage == "shard":
            dataset_count = payload["dataset_count"]
            if type(dataset_count) is not int:
                raise RecordValidationError(
                    "power shard dataset_count must be an exact integer"
                )
            if type(payload.get("execution_complete")) is not bool:
                raise RecordValidationError("power shard execution_complete must be a strict boolean")
            for index, result in enumerate(
                cast(list[Mapping[str, object]], payload["cell_results"])
            ):
                totals = result.get("gate_totals")
                if not isinstance(totals, Mapping) or any(type(totals.get(field)) is not int for field in ("dataset_count", "causal_pass_count")):
                    raise RecordValidationError(f"power shard cell_results[{index}] must contain exact family gate totals")
                trials, passed = cast(int, totals["dataset_count"]), cast(int, totals["causal_pass_count"])
                if trials != dataset_count or not 0 <= passed <= trials:
                    raise RecordValidationError(f"power shard cell_results[{index}] is not bounded by shard dataset_count")
                receipt = result.get("replay_receipt")
                if not isinstance(receipt, Mapping) or receipt.get("dataset_count") != dataset_count:
                    raise RecordValidationError("power shard receipt does not bind aggregate dataset count")
                chunks = receipt.get("chunks")
                if not isinstance(chunks, list) or receipt.get("chunk_count") != len(chunks):
                    raise RecordValidationError("power shard receipt does not commit every chunk")
                if sum(cast(int, chunk.get("dataset_count", -1)) for chunk in chunks if isinstance(chunk, Mapping)) != dataset_count:
                    raise RecordValidationError("power shard receipt chunks do not cover aggregate datasets")
                aggregate = receipt.get("aggregate_gate_totals")
                if aggregate != totals or sum(cast(int, chunk.get("causal_pass_count", -1)) for chunk in chunks if isinstance(chunk, Mapping)) != passed:
                    raise RecordValidationError("power shard chunk totals do not bind aggregate gate totals")
        elif stage == "selection":
            selected = cast(list[object], payload["selected_cells"])
            if payload["selection_count"] != len(selected) or cast(
                int, payload["candidate_count"]
            ) < len(selected):
                raise RecordValidationError(
                    "power selection counts do not match selected_cells"
                )
        elif stage == "validation" and payload["phase"] == "gaussian_approximation":
            receipt = cast(
                Mapping[str, object],
                payload["approximation_receipt"],
            )
            unchanged = (
                receipt["gaussian_tier_decision"]
                == receipt["full_multiplier_tier_decision"]
            )
            within_tolerance = (
                cast(float, receipt["max_absolute_gate_pass_rate_difference"]) <= 0.01
            )
            if receipt["tier_decision_unchanged"] is not unchanged:
                raise RecordValidationError(
                    "Gaussian approximation receipt tier-decision flag is inconsistent"
                )
            if receipt["passed"] is not (within_tolerance and unchanged):
                raise RecordValidationError(
                    "Gaussian approximation receipt does not enforce the "
                    "0.01 difference and unchanged-tier gate"
                )
        elif stage == "validation" and payload["phase"] == "full_multiplier_fallback":
            cells = cast(list[object], payload["complete_cell_ids"])
            if payload["expected_cell_count"] != len(cells) or payload[
                "observed_cell_count"
            ] != len(cells):
                raise RecordValidationError(
                    "full-multiplier validation must cover every declared cell"
                )


def validate_record(value: Mapping[str, object]) -> dict[str, object]:
    """Validate and return a detached plain-JSON scientific record."""

    if not isinstance(value, Mapping):
        raise RecordValidationError("record must be a mapping")
    plain = _plain_json(value)
    if not isinstance(plain, dict):
        raise RecordValidationError("record must be a JSON object")
    record_kind = plain.get("record_kind")
    if not isinstance(record_kind, str) or record_kind not in SCHEMA_BY_KIND:
        raise RecordValidationError(f"unknown record_kind: {record_kind!r}")
    schema = pneuma_schemas.load_schema(SCHEMA_BY_KIND[record_kind])
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(plain), key=_validation_error_key)
    if errors:
        rendered: list[str] = []
        for error in errors:
            location = "$"
            if error.absolute_path:
                location += "".join(f"[{part!r}]" for part in error.absolute_path)
            rendered.append(f"{location}: {error.message}")
        raise RecordValidationError("; ".join(rendered))
    # The frozen value type applies path-normalization checks that are awkward
    # to express portably in ECMA-262 regular expressions.
    tuple(_walk_artifact_refs(plain))
    _validate_semantics(plain)
    return cast(dict[str, object], plain)


def load_record(path: Path) -> dict[str, object]:
    """Load strict UTF-8 JSON and validate it as one registered record."""

    source = Path(path)
    try:
        payload = source.read_bytes()
    except OSError as exc:
        raise RecordValidationError(f"cannot read record {source}: {exc}") from exc
    value = _load_json_bytes(payload, source=source)
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{source}: record must be a JSON object")
    return validate_record(cast(Mapping[str, object], value))


def _manifest_records(run_root: Path) -> list[tuple[Path, dict[str, object]]]:
    root = _run_root(run_root)
    found: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(root.rglob("*.json")):
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in (
            _OPERATIONAL_TOP_LEVEL | {"sources"}
        ):
            continue
        try:
            raw = _load_json_bytes(path.read_bytes(), source=path)
        except (OSError, RecordValidationError):
            continue
        if (
            isinstance(raw, Mapping)
            and raw.get("record_kind") == "resampling_study_manifest"
        ):
            found.append((path, validate_record(cast(Mapping[str, object], raw))))
    return found


def _require_manifest_ancestry(
    record: Mapping[str, object],
    *,
    run_root: Path,
) -> None:
    manifests = _manifest_records(run_root)
    if len(manifests) != 1:
        raise RecordValidationError(
            "exactly one study manifest must exist before scientific descendants"
        )
    manifest = manifests[0][1]
    for field in ("study_id", "frozen_created_at", "provenance"):
        if record.get(field) != manifest.get(field):
            raise RecordValidationError(
                f"scientific descendant {field} does not match study manifest"
            )


def _artifact_ref_for_path(
    path: Path, run_root: Path, role: str, media_type: str
) -> ArtifactRef:
    resolved, relative_path = _resolve_inside(path, run_root, require_exists=True)
    payload = resolved.read_bytes()
    return ArtifactRef(
        role=role,
        relative_path=relative_path,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type=media_type,
    )


def _prepare_destination(path: Path, run_root: Path) -> tuple[Path, str]:
    target, relative_path = _resolve_inside(path, run_root, require_exists=False)
    if target.exists():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    rebound, rebound_relative = _resolve_inside(
        target,
        run_root,
        require_exists=False,
    )
    if rebound != target or rebound_relative != relative_path:
        raise RecordValidationError("artifact destination ancestry changed")
    return target, relative_path


def write_record(
    path: Path,
    value: Mapping[str, object],
    *,
    run_root: Path,
    role: str,
) -> ArtifactRef:
    """Validate completely, publish atomically without overwrite, and reference."""

    validated = validate_record(value)
    # Task-6 protected records must never be created after an unblind read.
    # Import locally to keep the general artifact layer independent at import time.
    from .task6_state import require_preunblind_context
    require_preunblind_context(run_root, cast(str, validated["record_kind"]))
    if validated["record_kind"] != "resampling_study_manifest":
        _require_manifest_ancestry(validated, run_root=run_root)
    target, _relative = _resolve_inside(
        path,
        run_root,
        require_exists=False,
    )
    if target.exists():
        raise FileExistsError(target)
    if validated["record_kind"] == "resampling_task_block":
        _validate_task_write_ancestry(
            validated,
            run_root=run_root,
        )
    target, _relative = _prepare_destination(path, run_root)
    write_atomic_json(target, validated)
    return _artifact_ref_for_path(target, run_root, role, "application/json")


def validate_scientific_graph(run_root: Path) -> None:
    """Validate the complete currently-present scientific graph (no root needed)."""
    root = _run_root(run_root)
    documents = _scientific_documents(root, excluded=())
    if not documents:
        raise RecordValidationError("scientific graph is empty")
    _validate_kind_identities(
        documents,
        required_document_kinds={
            cast(str, document.value["record_kind"])
            for document in documents.values()
        },
        run_root=root,
    )


def validate_preunblind_graph(run_root: Path, ledger_ref: ArtifactRef) -> None:
    """Validate all non-clear-ledger graph edges before permit validation.

    The opaque ledger is excluded by its already-bound relative path: this
    deliberately avoids opening or decoding it before the permit routine has
    authenticated its public parents and handle.
    """
    root = _run_root(run_root)
    ledger_path, ledger_relative = _resolve_inside(
        Path(ledger_ref.relative_path), root, require_exists=False,
    )
    # Do not trust the supplied path as an exclusion capability.  Discover
    # every ledger-shaped JSON file first (including an alternate hardlink or
    # byte-identical alias) and permit exactly the one bound relative name.
    ledger_documents: list[Path] = []
    for path in root.rglob("*.json"):
        relative = path.relative_to(root)
        if _is_operational(relative) or (
            relative.parts and relative.parts[0] == "sources"
        ):
            continue
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise RecordValidationError(f"cannot inspect pre-unblind graph: {exc}") from exc
        # This intentionally decodes only top-level JSON keys and the scalar
        # record_kind value, never the ledger payload.  json string decoding
        # catches escaped spellings that a raw-byte discriminator would miss.
        if _top_level_record_kind(raw) == "resampling_assignment_ledger":
            ledger_documents.append(path.resolve(strict=True))
    expected_ledger = (root / ledger_relative).resolve(strict=False)
    if ledger_documents != [expected_ledger]:
        raise RecordValidationError(
            "pre-unblind graph must contain exactly the bound assignment ledger"
        )
    documents = _scientific_documents(root, excluded=tuple(ledger_documents))
    if not documents:
        raise RecordValidationError("scientific graph is empty")
    _validate_kind_identities(
        documents,
        required_document_kinds={
            cast(str, document.value["record_kind"])
            for document in documents.values()
        },
        run_root=root,
    )


def _top_level_record_kind(payload: bytes) -> str | None:
    """Safely discriminate the top-level kind without decoding nested values."""
    try:
        text = payload.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise RecordValidationError("pre-unblind graph JSON is not UTF-8") from exc
    decoder = json.JSONDecoder()
    index, length = 0, len(text)

    def whitespace(position: int) -> int:
        while position < length and text[position] in " \t\r\n":
            position += 1
        return position

    def string(position: int) -> tuple[str, int]:
        value, end = decoder.raw_decode(text, position)
        if not isinstance(value, str):
            raise RecordValidationError("pre-unblind graph object key is not string")
        return value, end

    def skip(position: int) -> int:
        position = whitespace(position)
        if position >= length:
            raise RecordValidationError("truncated pre-unblind graph JSON")
        if text[position] == '"':
            return string(position)[1]
        if text[position] not in "[{":
            end = position
            while end < length and text[end] not in ",]}":
                end += 1
            return end
        opening, closing, depth, quote = text[position], "}" if text[position] == "{" else "]", 0, False
        while position < length:
            character = text[position]
            if quote:
                if character == "\\":
                    position += 2
                    continue
                if character == '"':
                    quote = False
            elif character == '"':
                quote = True
            elif character == opening:
                depth += 1
            elif character == closing:
                depth -= 1
                if depth == 0:
                    return position + 1
            position += 1
        raise RecordValidationError("unterminated pre-unblind graph JSON")

    index = whitespace(index)
    if index >= length or text[index] != "{":
        return None
    index += 1
    while True:
        index = whitespace(index)
        if index < length and text[index] == "}":
            return None
        key, index = string(index)
        index = whitespace(index)
        if index >= length or text[index] != ":":
            raise RecordValidationError("malformed pre-unblind graph JSON")
        index = whitespace(index + 1)
        if key == "record_kind":
            value, index = string(index)
            return value
        index = whitespace(skip(index))
        if index >= length or text[index] not in ",}":
            raise RecordValidationError("malformed pre-unblind graph JSON")
        if text[index] == "}":
            return None
        index += 1


def write_jsonl_artifact(
    path: Path,
    rows: Iterable[Mapping[str, object]],
    *,
    run_root: Path,
    role: str,
) -> ArtifactRef:
    """Materialize, validate, and atomically publish one immutable JSONL blob."""

    materialized: list[dict[str, object]] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, Mapping):
            raise RecordValidationError(f"JSONL row {index} must be a mapping")
        plain = _plain_json(row, path=f"$[{index - 1}]")
        if not isinstance(plain, dict):
            raise RecordValidationError(f"JSONL row {index} must be a JSON object")
        materialized.append(cast(dict[str, object], plain))
    # Prove every row serializes before a destination is created.
    for row in materialized:
        canonical_json_bytes(row, indent=None)
    target, _relative = _prepare_destination(path, run_root)
    write_atomic_jsonl(target, materialized)
    return _artifact_ref_for_path(
        target,
        run_root,
        role,
        "application/x-ndjson",
    )


def _normalized_source_name(path: Path) -> str:
    name = Path(path).name
    normalized = PurePosixPath(name).as_posix()
    if not normalized or normalized in {".", ".."} or "/" in normalized:
        raise ValueError(f"invalid source name: {path}")
    return normalized


def _media_type(path: Path) -> str:
    suffix = path.suffix.casefold()
    overrides = {
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
        ".md": "text/markdown",
        ".py": "text/x-python",
        ".txt": "text/plain",
    }
    if suffix in overrides:
        return overrides[suffix]
    guessed, _encoding = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def _required_kind_list(value: object) -> list[str]:
    candidate = value
    if isinstance(candidate, Mapping):
        candidate = candidate.get("required_document_kinds")
    if not isinstance(candidate, list):
        raise RecordValidationError(
            "required-document-kinds source must contain a JSON array"
        )
    if not all(isinstance(kind, str) for kind in candidate):
        raise RecordValidationError("required document kinds must be strings")
    kinds = cast(list[str], candidate)
    if tuple(kinds) != _FROZEN_UPSTREAM_KINDS:
        raise RecordValidationError(
            "required document kinds must exactly equal the frozen upstream kinds"
        )
    return kinds


@dataclass(frozen=True, slots=True)
class _SourceCopy:
    source: Path
    payload: bytes
    destination: Path
    ref: ArtifactRef


def _plan_source_copy(
    source: Path,
    *,
    run_root: Path,
    subtree: str,
    role: str,
) -> _SourceCopy:
    source_path = Path(source).resolve(strict=True)
    if not source_path.is_file():
        raise ValueError(f"source must be a file: {source}")
    payload = source_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    name = _normalized_source_name(source_path)
    relative = PurePosixPath("sources", subtree, f"{digest}-{name}").as_posix()
    destination, checked_relative = _resolve_inside(
        Path(run_root) / Path(relative),
        run_root,
        require_exists=False,
    )
    if checked_relative != relative:
        raise RecordValidationError("source destination path was not canonical")
    ref = ArtifactRef(
        role=role,
        relative_path=relative,
        sha256=digest,
        byte_count=len(payload),
        media_type=AUTHORITY_ASSET_ROLE_MEDIA.get(role, _media_type(source_path)),
    )
    return _SourceCopy(source_path, payload, destination, ref)


def _plan_provider_v2_closure(
    provider_copy: _SourceCopy,
    *,
    known_copies: Sequence[_SourceCopy],
    run_root: Path,
) -> list[_SourceCopy]:
    decoded = _load_json_bytes(
        provider_copy.payload,
        source=provider_copy.source,
    )
    if not isinstance(decoded, Mapping):
        return []
    if decoded.get("record_kind") != "provider_lane_plan_v2":
        return []
    if set(decoded) != {"record_kind", "schema_version", "lanes", "task_lanes"}:
        raise RecordValidationError(
            "provider lane plan has an open or incomplete shape"
        )
    source_root = provider_copy.source.parent.resolve(strict=True)
    known_by_ref = {copy.ref: copy for copy in known_copies}
    known_by_path = {copy.ref.relative_path: copy.ref for copy in known_copies}
    pending = list(_walk_artifact_refs(decoded))
    planned: list[_SourceCopy] = []
    observed: set[ArtifactRef] = set()
    while pending:
        ref = pending.pop(0)
        if ref in observed:
            continue
        observed.add(ref)
        known = known_by_ref.get(ref)
        if known is not None:
            if ref.media_type == "application/json":
                nested = _load_json_bytes(known.payload, source=known.source)
                pending.extend(_walk_artifact_refs(nested))
            continue
        conflicting = known_by_path.get(ref.relative_path)
        if conflicting is not None and conflicting != ref:
            raise RecordValidationError(
                "provider nested ref conflicts with an existing source path"
            )
        try:
            source, relative = _resolve_inside(
                provider_copy.source.parent / Path(ref.relative_path),
                source_root,
                require_exists=True,
            )
        except (FileNotFoundError, RecordValidationError) as exc:
            raise RecordValidationError(
                f"provider nested ref source is missing: {ref.relative_path!r}"
            ) from exc
        if relative != ref.relative_path or not source.is_file():
            raise RecordValidationError(
                f"provider nested ref source is not canonical: {ref.relative_path!r}"
            )
        payload = source.read_bytes()
        if (
            hashlib.sha256(payload).hexdigest() != ref.sha256
            or len(payload) != ref.byte_count
        ):
            raise RecordValidationError(
                f"provider nested ref bytes mismatch: {ref.relative_path!r}"
            )
        destination, destination_relative = _resolve_inside(
            Path(run_root) / Path(ref.relative_path),
            run_root,
            require_exists=False,
        )
        if destination_relative != ref.relative_path:
            raise RecordValidationError(
                "provider nested destination path is not canonical"
            )
        copy = _SourceCopy(source, payload, destination, ref)
        planned.append(copy)
        known_by_ref[ref] = copy
        known_by_path[ref.relative_path] = ref
        if ref.media_type == "application/json":
            nested = _load_json_bytes(payload, source=source)
            pending.extend(_walk_artifact_refs(nested))
    return planned


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return cast(dict[str, object], asdict(ref))


def _provider_execution_authority(
    roster_value: object,
    assignment_value: object,
) -> Literal["synthetic_validation", "confirmation"]:
    roster_fields = {
        "record_kind",
        "schema_version",
        "roster_kind",
        "supported_tiers",
        "tasks",
    }
    if not isinstance(roster_value, Mapping) or set(roster_value) != roster_fields:
        raise RecordValidationError("v2 provider plan requires a closed roster source")
    if (
        roster_value.get("record_kind") != "resampling_roster_v1"
        or roster_value.get("schema_version") != "1"
    ):
        raise RecordValidationError("v2 provider roster has wrong identity")

    if not isinstance(assignment_value, Mapping) or set(assignment_value) != set(
        ASSIGNMENT_PROGRAM_GRAMMAR.fields
    ):
        raise RecordValidationError(
            "v2 provider plan requires a closed assignment source"
        )
    assignment = dict(assignment_value)
    if assignment.get("record_kind") != ASSIGNMENT_PROGRAM_GRAMMAR.record_kind:
        raise RecordValidationError("v2 provider assignment has wrong identity")
    validate_assignment_program(assignment)

    authority_by_pair: dict[
        tuple[object, object],
        Literal[
            "synthetic_validation",
            "confirmation",
        ],
    ] = {
        (
            "synthetic_fixture",
            "synthetic_derangement",
        ): "synthetic_validation",
        (
            "eligible_confirmation",
            "confirmation_lineage_matching",
        ): "confirmation",
    }
    pair = (
        exact_text(
            roster_value.get("roster_kind"),
            field="v2 provider roster.roster_kind",
        ),
        exact_text(
            assignment.get("assignment_mode"),
            field="v2 provider assignment.assignment_mode",
        ),
    )
    try:
        return authority_by_pair[pair]
    except KeyError as exc:
        raise RecordValidationError(
            "v2 provider roster and assignment authority disagree or are unknown"
        ) from exc


def seal_study_manifest(
    study_source: Path,
    tasks_source: Path,
    roster_source: Path,
    assignment_program_source: Path,
    provider_lane_plan_source: Path,
    storage_policy_contract_source: Path,
    power_grid_source: Path,
    power_screen_topology_source: Path,
    tokenizer_source: Path,
    packet_template_source: Path,
    packet_policy_source: Path,
    pad_unit_set_source: Path,
    source_revision_sources: Sequence[Path],
    required_document_kinds_source: Path,
    *,
    eligibility_manifest_source: Path | None = None,
    roster_ceremony_policy_source: Path | None = None,
    run_root: Path,
    out: Path,
) -> ArtifactRef:
    """Copy every external input and seal the first scientific record."""

    root = _run_root(run_root)
    existing_scientific = _scientific_documents(
        root,
        excluded={Path(out)},
    )
    if existing_scientific:
        raise FileExistsError(
            "study manifest must be the first scientific record in run_root"
        )
    if not source_revision_sources:
        raise ValueError("source_revision_sources must be non-empty")
    revision_names = [_normalized_source_name(path) for path in source_revision_sources]
    if revision_names != sorted(revision_names):
        raise ValueError(
            "source_revision_sources must be sorted by normalized source name"
        )
    if len(revision_names) != len(set(revision_names)):
        raise ValueError("source_revision_sources must have unique normalized names")
    required_path = Path(required_document_kinds_source).resolve(strict=True)
    _required_kind_list(
        _load_json_bytes(required_path.read_bytes(), source=required_path)
    )

    source_path = Path(study_source).resolve(strict=True)
    template_raw = _load_json_bytes(source_path.read_bytes(), source=source_path)
    if not isinstance(template_raw, Mapping):
        raise RecordValidationError("study template must be a JSON object")
    template = cast(dict[str, object], _plain_json(template_raw))
    expected_top = {
        "record_kind",
        "schema_version",
        "study_id",
        "frozen_created_at",
        "provenance",
        "payload",
    }
    if set(template) != expected_top:
        raise RecordValidationError(
            "study template must contain exactly the scientific envelope fields"
        )
    if template.get("record_kind") != "resampling_study_manifest":
        raise RecordValidationError("study template has wrong record_kind")
    template_payload = template.get("payload")
    commitment_fields = {
        "commitment_scheme",
        "roster_local_nonce_commitment_sha256",
        "schedule_seed_commitment_sha256",
        "assignment_master_key_commitment_sha256",
    }
    if (
        not isinstance(template_payload, Mapping)
        or set(template_payload) != commitment_fields
    ):
        raise RecordValidationError(
            "study template payload must contain only the commitment scheme "
            "and three named commitment digests"
        )
    if template_payload["commitment_scheme"] != "resampling-null-key-ceremony-v1":
        raise RecordValidationError(
            "study template commitment_scheme must be resampling-null-key-ceremony-v1"
        )
    if (eligibility_manifest_source is None) != (roster_ceremony_policy_source is None):
        raise ValueError(
            "eligibility_manifest_source and roster_ceremony_policy_source "
            "must be supplied together"
        )

    fixed_inputs = (
        (tasks_source, "task-registry", "task_registry"),
        (roster_source, "roster", "roster"),
        (assignment_program_source, "assignment-program", "assignment_program"),
        (provider_lane_plan_source, "provider-lane-plan", "provider_lane_plan"),
        (
            storage_policy_contract_source,
            "storage-policy-contract",
            "storage_policy_contract",
        ),
        (power_grid_source, "power-grid", "power_grid"),
        (
            power_screen_topology_source,
            "power-screen-topology",
            "power_screen_topology",
        ),
        (tokenizer_source, "tokenizer", "tokenizer"),
        (packet_template_source, "packet-template", "packet_template"),
        (packet_policy_source, "packet-policy", "packet_policy"),
        (pad_unit_set_source, "pad-unit-set", "pad_unit_set"),
        (
            required_document_kinds_source,
            "required-document-kinds",
            "required_document_kinds",
        ),
    )
    copies = [
        _plan_source_copy(
            source,
            run_root=root,
            subtree=subtree,
            role=role,
        )
        for source, subtree, role in fixed_inputs
    ]
    revision_copies = [
        _plan_source_copy(
            revision,
            run_root=root,
            subtree="revisions",
            role="source_revision",
        )
        for revision in source_revision_sources
    ]
    conditional_copies: list[_SourceCopy] = []
    if (
        eligibility_manifest_source is not None
        and roster_ceremony_policy_source is not None
    ):
        conditional_copies = [
            _plan_source_copy(
                eligibility_manifest_source,
                run_root=root,
                subtree="eligibility-manifest",
                role="eligibility_manifest",
            ),
            _plan_source_copy(
                roster_ceremony_policy_source,
                run_root=root,
                subtree="roster-ceremony-policy",
                role="roster_ceremony_policy",
            ),
        ]
    provider_copy = next(
        copy for copy in copies if copy.ref.role == "provider_lane_plan"
    )
    provider_nested_copies = _plan_provider_v2_closure(
        provider_copy,
        known_copies=copies + revision_copies + conditional_copies,
        run_root=root,
    )
    all_copies = copies + revision_copies + conditional_copies + provider_nested_copies
    destinations = [copy.destination for copy in all_copies]
    if len(destinations) != len(set(destinations)):
        raise RecordValidationError("source copies have conflicting destinations")
    for destination in destinations:
        if destination.exists():
            raise FileExistsError(destination)

    by_role = {copy.ref.role: copy.ref for copy in copies + conditional_copies}
    final_payload: dict[str, object] = {
        "task_registry_ref": _ref_mapping(by_role["task_registry"]),
        "roster_ref": _ref_mapping(by_role["roster"]),
        "eligibility_manifest_ref": (
            _ref_mapping(by_role["eligibility_manifest"])
            if conditional_copies
            else None
        ),
        "roster_ceremony_policy_ref": (
            _ref_mapping(by_role["roster_ceremony_policy"])
            if conditional_copies
            else None
        ),
        "assignment_program_ref": _ref_mapping(by_role["assignment_program"]),
        "provider_lane_plan_ref": _ref_mapping(by_role["provider_lane_plan"]),
        "storage_policy_contract_ref": _ref_mapping(by_role["storage_policy_contract"]),
        "power_grid_ref": _ref_mapping(by_role["power_grid"]),
        "power_screen_topology_ref": _ref_mapping(by_role["power_screen_topology"]),
        "tokenizer_ref": _ref_mapping(by_role["tokenizer"]),
        "packet_template_ref": _ref_mapping(by_role["packet_template"]),
        "packet_policy_ref": _ref_mapping(by_role["packet_policy"]),
        "pad_unit_set_ref": _ref_mapping(by_role["pad_unit_set"]),
        "source_revision_refs": [_ref_mapping(copy.ref) for copy in revision_copies],
        "commitment_scheme": template_payload["commitment_scheme"],
        "roster_local_nonce_commitment_sha256": template_payload[
            "roster_local_nonce_commitment_sha256"
        ],
        "schedule_seed_commitment_sha256": template_payload[
            "schedule_seed_commitment_sha256"
        ],
        "assignment_master_key_commitment_sha256": template_payload[
            "assignment_master_key_commitment_sha256"
        ],
        "required_document_kinds_ref": _ref_mapping(by_role["required_document_kinds"]),
    }
    final = dict(template)
    final["payload"] = final_payload
    validated = validate_record(final)
    out_target, _relative = _resolve_inside(out, root, require_exists=False)
    if out_target.exists():
        raise FileExistsError(out_target)
    if out_target in destinations:
        raise RecordValidationError(
            "study manifest destination conflicts with a source destination"
        )

    provider_value = _load_json_bytes(
        provider_copy.payload,
        source=provider_copy.source,
    )
    if (
        isinstance(provider_value, Mapping)
        and provider_value.get("record_kind") == "provider_lane_plan_v2"
    ):
        task_copy = next(copy for copy in copies if copy.ref.role == "task_registry")
        task_value = _load_json_bytes(task_copy.payload, source=task_copy.source)
        if (
            not isinstance(task_value, Mapping)
            or set(task_value) != {"record_kind", "schema_version", "tasks"}
            or task_value.get("record_kind") != "resampling_task_registry_v1"
        ):
            raise RecordValidationError(
                "v2 provider plan requires a closed task registry"
            )
        registry = dict(task_value)
        validate_task_registry(registry)
        roster_copy = next(copy for copy in copies if copy.ref.role == "roster")
        assignment_copy = next(
            copy for copy in copies if copy.ref.role == "assignment_program"
        )
        execution_authority = _provider_execution_authority(
            _load_json_bytes(
                roster_copy.payload,
                source=roster_copy.source,
            ),
            _load_json_bytes(
                assignment_copy.payload,
                source=assignment_copy.source,
            ),
        )
        has_conditional_authority = bool(conditional_copies)
        if execution_authority == "synthetic_validation" and has_conditional_authority:
            raise RecordValidationError(
                "synthetic authority forbids eligibility and ceremony refs"
            )
        if execution_authority == "confirmation" and not has_conditional_authority:
            raise RecordValidationError(
                "confirmation authority requires eligibility and ceremony refs"
            )
        with tempfile.TemporaryDirectory(
            prefix=".pneuma-manifest-stage-",
            dir=root.parent,
        ) as staging_name:
            staging_root = Path(staging_name)
            for copy in all_copies:
                staging_path = staging_root / copy.ref.relative_path
                staging_path.parent.mkdir(parents=True, exist_ok=True)
                write_atomic_bytes(staging_path, copy.payload)
            with AuthorityRefReader(staging_root) as reader:
                validate_provider_lane_plan(
                    provider_value,
                    reader=reader,
                    registry=registry,
                    tokenizer_ref=by_role["tokenizer"],
                    manifest_revisions=tuple(copy.ref for copy in revision_copies),
                    schedule_authority=execution_authority,
                )
    from .publication import BoundPublication

    with BoundPublication(root) as publication:
        for copy in all_copies:
            publication.publish_bytes(
                copy.ref.relative_path,
                copy.payload,
                role=copy.ref.role,
                media_type=copy.ref.media_type,
            )
        manifest_payload = canonical_json_bytes(validated, indent=4)
        manifest_ref = publication.publish_bytes(
            _relative,
            manifest_payload,
            role="study_manifest",
            media_type="application/json",
        )
        publication.commit()
        return manifest_ref


def verify_digest_link(
    child: Mapping[str, object],
    field: str,
    parent: Mapping[str, object],
) -> None:
    """Verify a naked digest or ArtifactRef field against canonical parent bytes."""

    if field in child:
        link = child[field]
    else:
        payload = child.get("payload")
        if not isinstance(payload, Mapping) or field not in payload:
            raise RecordValidationError(f"missing digest link field {field!r}")
        link = payload[field]
    if isinstance(link, Mapping):
        claimed = link.get("sha256")
    else:
        claimed = link
    expected = canonical_digest(parent)
    if claimed != expected:
        raise RecordValidationError(
            f"{field} digest mismatch: expected {expected}, got {claimed!r}"
        )


@dataclass(frozen=True, slots=True)
class ArtifactEntry:
    relative_path: str
    sha256: str
    byte_count: int
    entry_kind: Literal["scientific_record", "referenced_blob"]
    document_kind: str | None
    role: str
    media_type: str


@dataclass(frozen=True, slots=True)
class _ScientificDocument:
    path: Path
    relative_path: str
    value: dict[str, object]
    sha256: str
    byte_count: int


def _is_operational(relative: Path) -> bool:
    return bool(relative.parts and relative.parts[0] in _OPERATIONAL_TOP_LEVEL)


def _scientific_documents(
    run_root: Path,
    *,
    excluded: Collection[Path],
) -> dict[str, _ScientificDocument]:
    root = _run_root(run_root)
    excluded_resolved = {Path(path).resolve(strict=False) for path in excluded}
    documents: dict[str, _ScientificDocument] = {}
    for path in sorted(root.rglob("*.json")):
        resolved = path.resolve(strict=True)
        if resolved in excluded_resolved:
            continue
        relative = resolved.relative_to(root)
        if _is_operational(relative) or (
            relative.parts and relative.parts[0] == "sources"
        ):
            continue
        payload = resolved.read_bytes()
        try:
            raw = _load_json_bytes(payload, source=resolved)
        except RecordValidationError:
            continue
        if not isinstance(raw, Mapping):
            continue
        kind = raw.get("record_kind")
        if not isinstance(kind, str):
            continue
        if kind == "resampling_artifact_root":
            raise RecordValidationError(
                f"nested or pre-existing artifact root: {relative.as_posix()}"
            )
        if kind not in SCHEMA_BY_KIND:
            if kind.startswith("resampling_"):
                raise RecordValidationError(
                    f"raw file presented as scientific record: {relative.as_posix()}"
                )
            continue
        validated = validate_record(cast(Mapping[str, object], raw))
        relative_path = PurePosixPath(*relative.parts).as_posix()
        documents[relative_path] = _ScientificDocument(
            path=resolved,
            relative_path=relative_path,
            value=validated,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
        )
    return documents


def _read_ref(
    ref: ArtifactRef,
    *,
    run_root: Path,
) -> tuple[Path, bytes]:
    parts = PurePosixPath(ref.relative_path).parts
    if parts and parts[0] in _OPERATIONAL_TOP_LEVEL:
        raise RecordValidationError(
            "operational artifacts cannot enter the scientific closure"
        )
    try:
        path, relative = _resolve_inside(
            Path(ref.relative_path),
            run_root,
            require_exists=True,
        )
    except (FileNotFoundError, RecordValidationError) as exc:
        raise RecordValidationError(
            f"dangling artifact_ref {ref.relative_path!r}"
        ) from exc
    if relative != ref.relative_path or not path.is_file():
        raise RecordValidationError(
            f"artifact_ref is not a canonical file: {ref.relative_path!r}"
        )
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != ref.sha256 or len(payload) != ref.byte_count:
        raise RecordValidationError(
            f"artifact_ref bytes mismatch: {ref.relative_path!r}"
        )
    return path, payload


def _load_direct_scientific_parent(
    value: object,
    *,
    run_root: Path,
    field: str,
    expected_kind: str,
    expected_stage: str | None = None,
) -> _ScientificDocument:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    try:
        ref = ArtifactRef(**cast(dict[str, Any], dict(value)))
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is malformed: {exc}") from exc
    if ref.media_type != "application/json":
        raise RecordValidationError(f"{field} must reference application/json")
    path, raw = _read_ref(ref, run_root=run_root)
    decoded = _load_json_bytes(raw, source=path)
    if not isinstance(decoded, Mapping):
        raise RecordValidationError(f"{field} must reference a JSON object")
    validated = validate_record(cast(Mapping[str, object], decoded))
    if validated["record_kind"] != expected_kind:
        raise RecordValidationError(
            f"{field} must reference {expected_kind}, got {validated['record_kind']}"
        )
    payload = cast(Mapping[str, object], validated["payload"])
    if expected_stage is not None and payload.get("stage") != expected_stage:
        raise RecordValidationError(
            f"{field} must reference {expected_kind} stage {expected_stage!r}"
        )
    return _ScientificDocument(
        path=path,
        relative_path=ref.relative_path,
        value=validated,
        sha256=ref.sha256,
        byte_count=ref.byte_count,
    )


def _validate_task_write_ancestry(
    record: Mapping[str, object],
    *,
    run_root: Path,
) -> None:
    task_payload = cast(Mapping[str, object], record["payload"])
    schedule = _load_direct_scientific_parent(
        task_payload["schedule_ref"],
        run_root=run_root,
        field="task block schedule_ref",
        expected_kind="resampling_prefix_schedule",
    )
    prefix = _load_direct_scientific_parent(
        task_payload["prefix_index_ref"],
        run_root=run_root,
        field="task block prefix_index_ref",
        expected_kind="resampling_prefix_receipt",
    )
    assignment = _load_direct_scientific_parent(
        task_payload["assignment_ref"],
        run_root=run_root,
        field="task block assignment_ref",
        expected_kind="resampling_assignment_ledger",
    )
    sealed_packet = _load_direct_scientific_parent(
        task_payload["packet_index_ref"],
        run_root=run_root,
        field="task block packet_index_ref",
        expected_kind="resampling_packet_index",
        expected_stage="sealed",
    )
    freeze = _load_direct_scientific_parent(
        task_payload["analysis_freeze_ref"],
        run_root=run_root,
        field="task block analysis_freeze_ref",
        expected_kind="resampling_analysis_freeze",
    )
    sealed_payload = cast(Mapping[str, object], sealed_packet.value["payload"])
    candidate = _load_direct_scientific_parent(
        sealed_payload["candidate_ref"],
        run_root=run_root,
        field="sealed packet candidate_ref",
        expected_kind="resampling_packet_index",
        expected_stage="candidate",
    )
    schedule_payload = cast(Mapping[str, object], schedule.value["payload"])
    manifest = _load_direct_scientific_parent(
        schedule_payload["manifest_ref"],
        run_root=run_root,
        field="schedule manifest_ref",
        expected_kind="resampling_study_manifest",
    )

    direct_parents = (
        manifest,
        schedule,
        prefix,
        assignment,
        candidate,
        sealed_packet,
        freeze,
    )
    for parent in direct_parents:
        for field in ("study_id", "frozen_created_at", "provenance"):
            if parent.value[field] != record[field]:
                raise RecordValidationError(
                    f"task block {field} differs from direct parent "
                    f"{parent.value['record_kind']}"
                )
    task_bytes = canonical_json_bytes(record, indent=2)
    pending_task = _ScientificDocument(
        path=_run_root(run_root) / "pending-task.json",
        relative_path="pending-task.json",
        value=cast(dict[str, object], dict(record)),
        sha256=hashlib.sha256(task_bytes).hexdigest(),
        byte_count=len(task_bytes),
    )
    _validate_scientific_ancestry(
        {
            "resampling_study_manifest": [manifest],
            "resampling_prefix_schedule": [schedule],
            "resampling_prefix_receipt": [prefix],
            "resampling_assignment_ledger": [assignment],
            "resampling_packet_index": [candidate, sealed_packet],
            "resampling_analysis_freeze": [freeze],
            "resampling_task_block": [pending_task],
        }
    )


def _extract_task_ids(value: object) -> set[str] | None:
    if isinstance(value, list):
        task_ids: list[str] = []
        for item in value:
            if isinstance(item, str) and item:
                task_ids.append(item)
            elif isinstance(item, Mapping):
                candidate = item.get("task_id")
                if not isinstance(candidate, str):
                    nested = item.get("task")
                    if isinstance(nested, Mapping):
                        candidate = nested.get("task_id")
                if isinstance(candidate, str) and candidate:
                    task_ids.append(candidate)
                else:
                    return None
            else:
                return None
        if len(task_ids) != len(set(task_ids)):
            raise RecordValidationError("roster contains duplicate task_id values")
        return set(task_ids)
    if isinstance(value, Mapping):
        for key in ("tasks", "task_ids", "roster"):
            if key in value:
                extracted = _extract_task_ids(value[key])
                if extracted is not None:
                    return extracted
        payload = value.get("payload")
        if isinstance(payload, (Mapping, list)):
            return _extract_task_ids(payload)
    return None


def _manifest_roster_task_ids(
    manifest: _ScientificDocument,
    *,
    run_root: Path,
) -> set[str]:
    payload = cast(Mapping[str, object], manifest.value["payload"])
    for key in ("roster_ref", "task_registry_ref"):
        ref_value = payload.get(key)
        if not isinstance(ref_value, Mapping):
            continue
        ref = ArtifactRef(**cast(dict[str, Any], dict(ref_value)))
        path, raw = _read_ref(ref, run_root=run_root)
        try:
            decoded = _load_json_bytes(raw, source=path)
        except RecordValidationError:
            continue
        extracted = _extract_task_ids(decoded)
        if extracted is not None:
            return extracted
    raise RecordValidationError("manifest roster does not expose a task roster")


def _validate_kind_identities(
    documents: Mapping[str, _ScientificDocument],
    *,
    required_document_kinds: set[str],
    run_root: Path,
) -> None:
    by_kind: dict[str, list[_ScientificDocument]] = {}
    for document in documents.values():
        kind = cast(str, document.value["record_kind"])
        by_kind.setdefault(kind, []).append(document)
    observed_kinds = set(by_kind)
    missing = required_document_kinds - observed_kinds
    extra = observed_kinds - required_document_kinds
    if missing:
        raise RecordValidationError(
            f"missing required document kinds: {sorted(missing)}"
        )
    if extra:
        raise RecordValidationError(f"extra scientific document kinds: {sorted(extra)}")
    for kind in _SINGLETON_KINDS:
        if kind in by_kind and len(by_kind[kind]) != 1:
            raise RecordValidationError(f"{kind} must be singleton")

    packet_documents = by_kind.get("resampling_packet_index", [])
    if packet_documents:
        stages = [
            cast(Mapping[str, object], document.value["payload"])["stage"]
            for document in packet_documents
        ]
        if Counter(stages) != Counter({"candidate": 1, "sealed": 1}):
            raise RecordValidationError(
                "packet-index identities require one candidate and one sealed"
            )
        candidate = next(
            document
            for document in packet_documents
            if cast(Mapping[str, object], document.value["payload"])["stage"]
            == "candidate"
        )
        sealed = next(
            document
            for document in packet_documents
            if cast(Mapping[str, object], document.value["payload"])["stage"]
            == "sealed"
        )
        candidate_ref = cast(
            Mapping[str, object],
            cast(Mapping[str, object], sealed.value["payload"])["candidate_ref"],
        )
        if (
            candidate_ref.get("relative_path") != candidate.relative_path
            or candidate_ref.get("sha256") != candidate.sha256
        ):
            raise RecordValidationError(
                "sealed packet index does not parent the unique candidate"
            )

    manifest_documents = by_kind.get("resampling_study_manifest", [])
    schedule_documents = by_kind.get("resampling_prefix_schedule", [])
    roster_task_ids: set[str] | None = None
    if schedule_documents:
        if len(manifest_documents) != 1:
            raise RecordValidationError(
                "schedule coverage requires the singleton study manifest"
            )
        roster_task_ids = _manifest_roster_task_ids(
            manifest_documents[0],
            run_root=run_root,
        )
        schedule_task_ids = {
            cast(
                str,
                cast(Mapping[str, object], entry["task"])["task_id"],
            )
            for entry in cast(
                list[Mapping[str, object]],
                cast(
                    Mapping[str, object],
                    schedule_documents[0].value["payload"],
                )["tasks"],
            )
        }
        if schedule_task_ids != roster_task_ids:
            raise RecordValidationError(
                "schedule task identities must exactly cover the manifest roster"
            )

    task_documents = by_kind.get("resampling_task_block", [])
    if task_documents:
        task_ids = [
            cast(
                str,
                cast(Mapping[str, object], document.value["payload"])["task_id"],
            )
            for document in task_documents
        ]
        if len(task_ids) != len(set(task_ids)):
            raise RecordValidationError("duplicate task-block task_id identity")
        if roster_task_ids is None:
            raise RecordValidationError(
                "task-block coverage requires the singleton study manifest"
            )
        if set(task_ids) != roster_task_ids:
            raise RecordValidationError(
                "task-block task_id identities do not exactly cover the roster"
            )

    power_documents = by_kind.get("resampling_power_report", [])
    if power_documents:
        _validate_power_identities(power_documents, run_root=run_root)
    _validate_scientific_ancestry(by_kind)


def _require_ref_matches(
    value: object,
    expected: _ScientificDocument,
    *,
    field: str,
) -> None:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    if (
        value.get("relative_path") != expected.relative_path
        or value.get("sha256") != expected.sha256
        or value.get("byte_count") != expected.byte_count
        or value.get("media_type") != "application/json"
    ):
        raise RecordValidationError(
            f"{field} does not identify the exact {expected.value['record_kind']} parent"
        )


def _require_artifact_ref_equal(
    value: object,
    expected: object,
    *,
    field: str,
) -> None:
    if not isinstance(value, Mapping) or not isinstance(expected, Mapping):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    if dict(value) != dict(expected):
        raise RecordValidationError(
            f"{field} does not identify the exact frozen source ref"
        )


def _require_digest_equal(
    value: object,
    expected: _ScientificDocument,
    *,
    field: str,
) -> None:
    if value != expected.sha256:
        raise RecordValidationError(
            f"{field} hash does not bind the exact "
            f"{expected.value['record_kind']} parent"
        )


def _singleton_document(
    by_kind: Mapping[str, list[_ScientificDocument]],
    kind: str,
) -> _ScientificDocument | None:
    documents = by_kind.get(kind, [])
    if not documents:
        return None
    if len(documents) != 1:
        raise RecordValidationError(f"{kind} must be singleton")
    return documents[0]


def _validate_task_chain_semantics(
    task_payload: Mapping[str, object],
    *,
    schedule_entry: Mapping[str, object],
    prefix_receipt: Mapping[str, object],
    assignment_row: Mapping[str, object],
    allocation: Mapping[str, object],
) -> None:
    task_id = cast(str, task_payload["task_id"])
    task_spec = cast(Mapping[str, object], schedule_entry["task"])
    for field in (
        "task_id",
        "benchmark",
        "stratum",
        "sensitivity_groups",
    ):
        if task_payload[field] != task_spec[field]:
            raise RecordValidationError(
                f"task block {task_id!r} {field} differs from the frozen schedule"
            )

    prefix_verifier = cast(
        Mapping[str, object],
        prefix_receipt["verifier_receipt"],
    )
    if prefix_verifier["task_id"] != task_id:
        raise RecordValidationError(
            f"prefix verifier task_id differs for task {task_id!r}"
        )
    y0_grade = cast(
        Mapping[str, object],
        prefix_receipt["y0_grade"],
    )
    if task_payload["prefix_success"] != y0_grade["success"]:
        raise RecordValidationError(
            f"task block {task_id!r} prefix_success differs from the frozen "
            "prefix Y_0 grade"
        )
    expected_triggered = (
        prefix_receipt["trigger_reason"] != "no_intervention_opportunity"
    )
    if task_payload["triggered"] is not expected_triggered:
        raise RecordValidationError(
            f"task block {task_id!r} triggered state differs from the frozen "
            "prefix trigger"
        )

    outcomes = cast(
        list[Mapping[str, object]],
        task_payload["slot_outcomes"],
    )
    schedule_slot_ids = [
        cast(str, slot["slot_id"])
        for slot in cast(
            list[Mapping[str, object]],
            schedule_entry["slots"],
        )
    ]
    assignment_slot_ids = [
        cast(str, row[0])
        for row in cast(list[list[object]], assignment_row["slot_arms"])
    ]
    capability_rows = cast(
        list[list[object]],
        allocation["slot_capabilities"],
    )
    allocation_slot_ids = [cast(str, row[0]) for row in capability_rows]
    capability_ids = [cast(str, row[1]) for row in capability_rows]
    if (
        assignment_slot_ids != schedule_slot_ids
        or allocation_slot_ids != schedule_slot_ids
    ):
        raise RecordValidationError(
            f"task assignment/allocation slots differ from the frozen schedule "
            f"for task {task_id!r}"
        )
    expected_slot_identities = list(zip(schedule_slot_ids, capability_ids, strict=True))
    if [outcome["opaque_arm_id"] for outcome in outcomes] != capability_ids:
        raise RecordValidationError(
            f"task outcomes differ from allocated capabilities for task {task_id!r}"
        )

    terminal_receipts = task_payload["terminal_slot_receipts"]
    if isinstance(terminal_receipts, list):
        terminal_identities = [
            (
                cast(Mapping[str, object], receipt)["slot_id"],
                cast(Mapping[str, object], receipt)["opaque_capability_id"],
            )
            for receipt in terminal_receipts
        ]
        if terminal_identities != expected_slot_identities:
            raise RecordValidationError(
                f"task terminal slot identities differ from the "
                f"schedule/assignment for task {task_id!r}"
            )

    expected_positions = {
        identity: index for index, identity in enumerate(expected_slot_identities)
    }
    attempts = task_payload["attempts"]
    if isinstance(attempts, list):
        for attempt_index, attempt in enumerate(attempts):
            attempt_receipts = cast(
                list[Mapping[str, object]],
                cast(Mapping[str, object], attempt)["terminal_receipts"],
            )
            attempt_identities = [
                (
                    cast(str, receipt["slot_id"]),
                    cast(str, receipt["opaque_capability_id"]),
                )
                for receipt in attempt_receipts
            ]
            attempt_positions = [
                expected_positions.get(identity) for identity in attempt_identities
            ]
            if (
                len(attempt_identities) != len(set(attempt_identities))
                or any(position is None for position in attempt_positions)
                or attempt_positions != sorted(cast(list[int], attempt_positions))
            ):
                raise RecordValidationError(
                    f"task attempt {attempt_index} slot identities must be a "
                    f"unique canonical-order subset of the schedule/assignment "
                    f"for task {task_id!r}"
                )

    if not expected_triggered:
        expected_y0 = {
            "success": y0_grade["success"],
            "prefix_success": y0_grade["success"],
            "partial_reward": y0_grade["partial_reward"],
            "infrastructure_failure": y0_grade["infrastructure_failure"],
            "counters": prefix_receipt["counters"],
            "artifact_ref": y0_grade["artifact_ref"],
        }
        for outcome in outcomes:
            if {field: outcome[field] for field in expected_y0} != expected_y0:
                raise RecordValidationError(
                    f"no-trigger task {task_id!r} does not copy the complete "
                    "frozen prefix Y_0 outcome"
                )


def _validate_packet_entry_trigger_semantics(
    entry: Mapping[str, object],
    *,
    prefix_receipt: Mapping[str, object],
) -> None:
    task_id = cast(str, entry["task_id"])
    if prefix_receipt["task_id"] != task_id:
        raise RecordValidationError(
            f"packet entry {task_id!r} differs from its frozen prefix task"
        )
    expected_pair = prefix_receipt["trigger_reason"] != "no_intervention_opportunity"
    if ("real_ref" in entry) is not expected_pair:
        raise RecordValidationError(
            f"packet entry {task_id!r} must be a pair exactly when its "
            "frozen prefix triggers intervention"
        )


def _validate_scientific_ancestry(
    by_kind: Mapping[str, list[_ScientificDocument]],
) -> None:
    manifest = _singleton_document(by_kind, "resampling_study_manifest")
    schedule = _singleton_document(by_kind, "resampling_prefix_schedule")
    prefix = _singleton_document(by_kind, "resampling_prefix_receipt")
    assignment = _singleton_document(by_kind, "resampling_assignment_ledger")
    projection = _singleton_document(by_kind, "resampling_blinded_projection")
    freeze = _singleton_document(by_kind, "resampling_analysis_freeze")
    analysis = _singleton_document(by_kind, "resampling_analysis")
    unblind = _singleton_document(by_kind, "resampling_unblind_receipt")

    if schedule is not None and manifest is not None:
        schedule_payload = _power_payload(schedule)
        _require_ref_matches(
            schedule_payload["manifest_ref"],
            manifest,
            field="prefix schedule manifest_ref",
        )
    if assignment is not None:
        assignment_payload = _power_payload(assignment)
        if manifest is not None:
            manifest_payload = _power_payload(manifest)
            _require_ref_matches(
                assignment_payload["manifest_ref"],
                manifest,
                field="assignment manifest_ref",
            )
            _require_artifact_ref_equal(
                assignment_payload["matching_program_ref"],
                manifest_payload["assignment_program_ref"],
                field="assignment matching_program_ref",
            )
            if (
                assignment_payload["assignment_master_key_commitment_sha256"]
                != manifest_payload["assignment_master_key_commitment_sha256"]
            ):
                raise RecordValidationError(
                    "assignment master-key commitment differs from manifest"
                )
    if prefix is not None and schedule is not None:
        prefix_payload = _power_payload(prefix)
        _require_ref_matches(
            prefix_payload["schedule_ref"],
            schedule,
            field="prefix receipt schedule_ref",
        )
        for index, receipt in enumerate(
            cast(list[Mapping[str, object]], prefix_payload["task_receipts"])
        ):
            _require_digest_equal(
                receipt.get("schedule_sha256"),
                schedule,
                field=f"prefix receipt task_receipts[{index}].schedule_sha256",
            )
            verifier = receipt.get("verifier_receipt")
            if not isinstance(verifier, Mapping):
                raise RecordValidationError(
                    "prefix receipt verifier_receipt must be a mapping"
                )
            _require_digest_equal(
                verifier.get("schedule_sha256"),
                schedule,
                field=(
                    "prefix receipt "
                    f"task_receipts[{index}].verifier_receipt.schedule_sha256"
                ),
            )
    if assignment is not None:
        assignment_payload = _power_payload(assignment)
        if schedule is not None:
            _require_ref_matches(
                assignment_payload["schedule_ref"],
                schedule,
                field="assignment schedule_ref",
            )
        if prefix is not None:
            _require_ref_matches(
                assignment_payload["prefix_index_ref"],
                prefix,
                field="assignment prefix_index_ref",
            )
        for index, row in enumerate(
            cast(list[Mapping[str, object]], assignment_payload["assignments"])
        ):
            if schedule is not None:
                _require_digest_equal(
                    row.get("schedule_sha256"),
                    schedule,
                    field=f"assignment assignments[{index}].schedule_sha256",
                )
            if prefix is not None:
                _require_digest_equal(
                    row.get("prefix_index_sha256"),
                    prefix,
                    field=(f"assignment assignments[{index}].prefix_index_sha256"),
                )

    packet_documents = by_kind.get("resampling_packet_index", [])
    candidate = next(
        (
            document
            for document in packet_documents
            if _power_payload(document).get("stage") == "candidate"
        ),
        None,
    )
    sealed = next(
        (
            document
            for document in packet_documents
            if _power_payload(document).get("stage") == "sealed"
        ),
        None,
    )
    prefix_receipts_by_task: dict[str, Mapping[str, object]] = {}
    if prefix is not None:
        for receipt in cast(
            list[Mapping[str, object]],
            _power_payload(prefix)["task_receipts"],
        ):
            task_id = receipt.get("task_id")
            if not isinstance(task_id, str) or task_id in prefix_receipts_by_task:
                raise RecordValidationError(
                    "prefix receipt task coverage must be unique by task_id"
                )
            prefix_receipts_by_task[task_id] = receipt
    assignments_by_task: dict[str, Mapping[str, object]] = {}
    if assignment is not None:
        for row in cast(
            list[Mapping[str, object]],
            _power_payload(assignment)["assignments"],
        ):
            task_id = row.get("task_id")
            if not isinstance(task_id, str) or task_id in assignments_by_task:
                raise RecordValidationError(
                    "assignment packet coverage must be unique by task_id"
                )
            assignments_by_task[task_id] = row
    for packet in packet_documents:
        packet_payload = _power_payload(packet)
        if assignment is not None:
            _require_ref_matches(
                packet_payload["assignment_ref"],
                assignment,
                field="packet assignment_ref",
            )
        if prefix is not None:
            _require_ref_matches(
                packet_payload["prefix_index_ref"],
                prefix,
                field="packet prefix_index_ref",
            )
        if manifest is not None:
            manifest_payload = _power_payload(manifest)
            for field in (
                "tokenizer_ref",
                "packet_template_ref",
                "packet_policy_ref",
                "pad_unit_set_ref",
            ):
                _require_artifact_ref_equal(
                    packet_payload[field],
                    manifest_payload[field],
                    field=f"packet {field}",
                )
        if packet_payload["stage"] == "candidate":
            entries = cast(
                list[Mapping[str, object]],
                packet_payload["entries"],
            )
            entry_task_ids = {cast(str, entry["task_id"]) for entry in entries}
            if assignment is not None and entry_task_ids != set(assignments_by_task):
                raise RecordValidationError(
                    "candidate packet task coverage differs from the assignment ledger"
                )
            for index, entry in enumerate(entries):
                task_id = cast(str, entry["task_id"])
                if prefix is not None:
                    _require_digest_equal(
                        entry.get("prefix_index_sha256"),
                        prefix,
                        field=f"packet entries[{index}].prefix_index_sha256",
                    )
                    prefix_receipt = prefix_receipts_by_task.get(task_id)
                    if prefix_receipt is None:
                        raise RecordValidationError(
                            f"packet entry {task_id!r} lacks frozen prefix coverage"
                        )
                    _validate_packet_entry_trigger_semantics(
                        entry,
                        prefix_receipt=prefix_receipt,
                    )
                if "real_ref" in entry:
                    donor_task_id = cast(str, entry["donor_task_id"])
                    assignment_row = assignments_by_task.get(task_id)
                    if (
                        assignment_row is None
                        or assignment_row.get("donor_task_id") != donor_task_id
                    ):
                        raise RecordValidationError(
                            f"packet pair[{index}] task/donor IDs differ from "
                            "the assignment ledger"
                        )
                    focal_prefix = prefix_receipts_by_task.get(task_id)
                    donor_prefix = prefix_receipts_by_task.get(donor_task_id)
                    if focal_prefix is None or donor_prefix is None:
                        raise RecordValidationError(
                            f"packet pair[{index}] lacks focal/donor prefix coverage"
                        )
                    focal_verifier = focal_prefix.get("verifier_receipt")
                    donor_verifier = donor_prefix.get("verifier_receipt")
                    if not isinstance(
                        focal_verifier,
                        Mapping,
                    ) or not isinstance(donor_verifier, Mapping):
                        raise RecordValidationError(
                            f"packet pair[{index}] prefix verifier receipt is missing"
                        )
                    _require_artifact_ref_equal(
                        entry["focal_verifier_ref"],
                        focal_verifier.get("verifier_artifact_ref"),
                        field=f"packet pair[{index}] focal_verifier_ref",
                    )
                    _require_artifact_ref_equal(
                        entry["donor_verifier_ref"],
                        donor_verifier.get("verifier_artifact_ref"),
                        field=f"packet pair[{index}] donor_verifier_ref",
                    )
                    if assignment is not None:
                        _require_ref_matches(
                            entry["assignment_ref"],
                            assignment,
                            field=f"packet entries[{index}].assignment_ref",
                        )
                    if manifest is not None:
                        manifest_payload = _power_payload(manifest)
                        for field in (
                            "tokenizer_ref",
                            "packet_template_ref",
                            "packet_policy_ref",
                            "pad_unit_set_ref",
                        ):
                            _require_artifact_ref_equal(
                                entry[field],
                                manifest_payload[field],
                                field=f"packet entries[{index}].{field}",
                            )
    if sealed is not None and candidate is not None:
        candidate_payload = _power_payload(candidate)
        sealed_payload = _power_payload(sealed)
        _require_ref_matches(
            sealed_payload["candidate_ref"],
            candidate,
            field="sealed packet candidate_ref",
        )
        for field in (
            "assignment_ref",
            "prefix_index_ref",
            "tokenizer_ref",
            "packet_template_ref",
            "packet_policy_ref",
            "pad_unit_set_ref",
        ):
            _require_artifact_ref_equal(
                sealed_payload[field],
                candidate_payload[field],
                field=f"sealed/candidate packet {field}",
            )
    if freeze is not None and sealed is not None:
        _require_ref_matches(
            _power_payload(freeze)["packet_index_ref"],
            sealed,
            field="analysis freeze packet_index_ref",
        )

    task_documents = by_kind.get("resampling_task_block", [])
    for task in task_documents:
        task_payload = _power_payload(task)
        for field, parent in (
            ("schedule_ref", schedule),
            ("prefix_index_ref", prefix),
            ("assignment_ref", assignment),
            ("packet_index_ref", sealed),
            ("analysis_freeze_ref", freeze),
        ):
            if parent is not None:
                _require_ref_matches(
                    task_payload[field],
                    parent,
                    field=f"task block {field}",
                )

    schedule_entries: list[Mapping[str, object]] = []
    schedule_task_ids: list[str] = []
    schedule_by_task: dict[str, Mapping[str, object]] = {}
    allocation_by_task: dict[str, Mapping[str, object]] = {}
    if schedule is not None:
        schedule_entries = cast(
            list[Mapping[str, object]],
            _power_payload(schedule)["tasks"],
        )
        schedule_task_ids = [
            cast(str, cast(Mapping[str, object], entry["task"])["task_id"])
            for entry in schedule_entries
        ]
        schedule_by_task = dict(zip(schedule_task_ids, schedule_entries, strict=True))
        if prefix is not None:
            prefix_task_ids = [
                cast(str, receipt["task_id"])
                for receipt in cast(
                    list[Mapping[str, object]],
                    _power_payload(prefix)["task_receipts"],
                )
            ]
            if prefix_task_ids != schedule_task_ids:
                raise RecordValidationError(
                    "prefix receipts must exactly cover frozen schedule task "
                    "IDs in order"
                )
        if assignment is not None:
            assignment_payload = _power_payload(assignment)
            assignment_task_ids = [
                cast(str, row["task_id"])
                for row in cast(
                    list[Mapping[str, object]],
                    assignment_payload["assignments"],
                )
            ]
            allocation_receipts = cast(
                list[Mapping[str, object]],
                assignment_payload["allocation_receipts"],
            )
            allocation_task_ids = [
                cast(str, receipt["task_id"]) for receipt in allocation_receipts
            ]
            donor_match_receipts = cast(
                list[Mapping[str, object]],
                assignment_payload["donor_match_receipts"],
            )
            donor_receipt_task_ids = [
                cast(str, receipt["task_id"]) for receipt in donor_match_receipts
            ]
            if (
                assignment_task_ids != schedule_task_ids
                or allocation_task_ids != schedule_task_ids
                or donor_receipt_task_ids != schedule_task_ids
            ):
                raise RecordValidationError(
                    "assignment rows, allocations, and donor receipts must "
                    "exactly cover frozen schedule task IDs in order"
                )
            allocation_by_task = {
                cast(str, receipt["task_id"]): receipt
                for receipt in allocation_receipts
            }
            for task_id in schedule_task_ids:
                schedule_entry = schedule_by_task[task_id]
                task_spec = cast(
                    Mapping[str, object],
                    schedule_entry["task"],
                )
                assignment_row = assignments_by_task[task_id]
                if assignment_row["task_lineage"] != task_spec["lineage"]:
                    raise RecordValidationError(
                        f"assignment lineage differs for task {task_id!r}"
                    )
                prefix_receipt = prefix_receipts_by_task[task_id]
                expected_matched = (
                    prefix_receipt["trigger_reason"] != "no_intervention_opportunity"
                )
                donor_match_kind = assignment_row["donor_match_kind"]
                if (donor_match_kind == "matched") is not expected_matched:
                    raise RecordValidationError(
                        f"assignment matching kind differs from frozen trigger "
                        f"for task {task_id!r}"
                    )
                if donor_match_kind == "matched":
                    donor_id = cast(str, assignment_row["donor_task_id"])
                    donor_entry = schedule_by_task.get(donor_id)
                    if donor_entry is None:
                        raise RecordValidationError(
                            f"assignment donor {donor_id!r} is not scheduled"
                        )
                    donor_spec = cast(
                        Mapping[str, object],
                        donor_entry["task"],
                    )
                    if assignment_row["donor_lineage"] != donor_spec["lineage"]:
                        raise RecordValidationError(
                            f"assignment donor lineage differs for task {task_id!r}"
                        )
                schedule_slot_ids = [
                    cast(str, slot["slot_id"])
                    for slot in cast(
                        list[Mapping[str, object]],
                        schedule_entry["slots"],
                    )
                ]
                assignment_slot_ids = [
                    cast(str, row[0])
                    for row in cast(
                        list[list[object]],
                        assignment_row["slot_arms"],
                    )
                ]
                capability_rows = cast(
                    list[list[object]],
                    allocation_by_task[task_id]["slot_capabilities"],
                )
                capability_slot_ids = [cast(str, row[0]) for row in capability_rows]
                capability_ids = [cast(str, row[1]) for row in capability_rows]
                if (
                    assignment_slot_ids != schedule_slot_ids
                    or capability_slot_ids != schedule_slot_ids
                    or len(capability_ids) != len(set(capability_ids))
                ):
                    raise RecordValidationError(
                        f"assignment slot/capability order differs for task {task_id!r}"
                    )

    if schedule is not None and prefix is not None and assignment is not None:
        for task_document in task_documents:
            task_payload = _power_payload(task_document)
            task_id = cast(str, task_payload["task_id"])
            task_schedule_entry = schedule_by_task.get(task_id)
            task_prefix_receipt = prefix_receipts_by_task.get(task_id)
            task_allocation = allocation_by_task.get(task_id)
            if (
                task_schedule_entry is None
                or task_prefix_receipt is None
                or task_id not in assignments_by_task
                or task_allocation is None
            ):
                raise RecordValidationError(
                    f"task block {task_id!r} lacks exact schedule, prefix, "
                    "or assignment ancestry"
                )
            _validate_task_chain_semantics(
                task_payload,
                schedule_entry=task_schedule_entry,
                prefix_receipt=task_prefix_receipt,
                assignment_row=assignments_by_task[task_id],
                allocation=task_allocation,
            )

    if schedule is not None and projection is not None:
        from .projection_candidate import build_candidate

        projection_payload = _power_payload(projection)
        projection_rows = cast(
            list[Mapping[str, object]],
            projection_payload["rows"],
        )
        task_by_id = {
            cast(str, _power_payload(document)["task_id"]): document
            for document in task_documents
        }
        projection_task_ids = [cast(str, row["task_id"]) for row in projection_rows]
        if (
            set(task_by_id) != set(schedule_task_ids)
            or projection_task_ids != schedule_task_ids
        ):
            raise RecordValidationError(
                "projection rows and task blocks must exactly cover frozen "
                "schedule task IDs in order"
            )
        ordered_task_refs = cast(
            list[object],
            projection_payload["task_block_refs"],
        )
        if len(ordered_task_refs) != len(schedule_task_ids):
            raise RecordValidationError(
                "projection task_block_refs must follow frozen schedule order"
            )
        for index, task_id in enumerate(schedule_task_ids):
            _require_ref_matches(
                ordered_task_refs[index],
                task_by_id[task_id],
                field=f"projection task_block_refs[{index}]",
            )

        for index, task_id in enumerate(schedule_task_ids):
            schedule_entry = schedule_by_task[task_id]
            task_spec = cast(Mapping[str, object], schedule_entry["task"])
            task_document = task_by_id[task_id]
            task_payload = _power_payload(task_document)
            schedule_slots = cast(
                list[Mapping[str, object]],
                schedule_entry["slots"],
            )
            schedule_slot_ids = [cast(str, slot["slot_id"]) for slot in schedule_slots]
            outcomes = cast(
                list[Mapping[str, object]],
                task_payload["slot_outcomes"],
            )

            reconstructed = build_candidate(
                [{
                    "task_id": task_id,
                    "prefix_success": task_payload["prefix_success"],
                    "slot_ids": schedule_slot_ids,
                }],
                {task_id: outcomes},
            )
            reconstructed_slots = reconstructed.rows[0]["slots"]

            expected_row = {
                "task_id": task_id,
                "benchmark": task_payload["benchmark"],
                "stratum": task_payload["stratum"],
                "lineage": task_spec["lineage"],
                "sensitivity_groups": task_payload["sensitivity_groups"],
                "prefix_success": task_payload["prefix_success"],
                "triggered": task_payload["triggered"],
                "slots": [
                    slot for slot in cast(list[dict[str, object]], reconstructed_slots)
                ],
                "pipeline_valid": task_payload["pipeline_valid"],
                "validity_codes": task_payload["validity_codes"],
            }
            if projection_rows[index] != expected_row:
                raise RecordValidationError(
                    f"projection row {index} is not the exact frozen "
                    f"reconstruction of task block {task_id!r}"
                )

        candidate = build_candidate(
            [
                {
                    "task_id": task_id,
                    "prefix_success": _power_payload(task_by_id[task_id])["prefix_success"],
                    "slot_ids": [slot["slot_id"] for slot in cast(list[Mapping[str, object]], schedule_by_task[task_id]["slots"])],
                }
                for task_id in schedule_task_ids
            ],
            {
                task_id: cast(list[Mapping[str, object]], _power_payload(task_by_id[task_id])["slot_outcomes"])
                for task_id in schedule_task_ids
            },
        )
        if projection_payload["projection_candidate_sha256"] != candidate.sha256:
            raise RecordValidationError(
                "projection_candidate_sha256 does not match stripped reconstruction"
            )

    if projection is not None:
        projection_payload = _power_payload(projection)
        if schedule is not None:
            _require_ref_matches(
                projection_payload["schedule_ref"],
                schedule,
                field="projection schedule_ref",
            )
        if freeze is not None:
            _require_ref_matches(
                projection_payload["analysis_freeze_ref"],
                freeze,
                field="projection analysis_freeze_ref",
            )
        expected_task_paths = {document.relative_path for document in task_documents}
        projected_task_paths = {
            ref.relative_path
            for ref in _walk_artifact_refs(projection_payload["task_block_refs"])
        }
        if expected_task_paths != projected_task_paths:
            raise RecordValidationError(
                "projection task_block_refs do not exactly cover task blocks"
            )

    if unblind is not None:
        unblind_payload = _power_payload(unblind)
        for field, parent in (
            ("projection_ref", projection),
            ("assignment_ledger_ref", assignment),
            ("analysis_freeze_ref", freeze),
        ):
            if parent is not None:
                _require_ref_matches(
                    unblind_payload[field],
                    parent,
                    field=f"unblind {field}",
                )
        if (
            projection is not None
            and unblind_payload["expected_task_count"]
            != _power_payload(projection)["expected_task_count"]
        ):
            raise RecordValidationError(
                "unblind expected_task_count differs from the frozen projection"
            )
    if analysis is not None:
        analysis_payload = _power_payload(analysis)
        for field, parent in (
            ("analysis_freeze_ref", freeze),
            ("projection_ref", projection),
            ("unblind_receipt_ref", unblind),
        ):
            if parent is not None:
                _require_ref_matches(
                    analysis_payload[field],
                    parent,
                    field=f"analysis {field}",
                )
        if freeze is not None:
            _require_artifact_ref_equal(
                analysis_payload["config_ref"],
                _power_payload(freeze)["config_ref"],
                field="analysis config_ref",
            )
        if (
            projection is not None
            and analysis_payload["row_count"]
            != _power_payload(projection)["expected_task_count"]
        ):
            raise RecordValidationError(
                "analysis row_count differs from the frozen projection"
            )

    if manifest is not None:
        manifest_roster_ref = _power_payload(manifest)["roster_ref"]
        for index, power in enumerate(by_kind.get("resampling_power_report", [])):
            _require_artifact_ref_equal(
                _power_payload(power)["roster_ref"],
                manifest_roster_ref,
                field=f"power report[{index}] roster_ref",
            )


def _power_payload(document: _ScientificDocument) -> Mapping[str, object]:
    return cast(Mapping[str, object], document.value["payload"])


_POWER_KERNEL_IDS = {
    ("screen", "gaussian_approximation"): "power-screen-gaussian-v1",
    ("shard", "gaussian_approximation"): "power-grid-gaussian-v1",
    (
        "selection",
        "gaussian_approximation",
    ): "power-worst-five-selection-v1",
    (
        "validation",
        "gaussian_approximation",
    ): "power-gaussian-vs-multiplier-validation-v1",
    ("final", "gaussian_approximation"): "power-final-gaussian-v1",
    (
        "screen",
        "full_multiplier_fallback",
    ): "power-screen-full-multiplier-v1",
    (
        "shard",
        "full_multiplier_fallback",
    ): "power-grid-full-multiplier-v1",
    (
        "validation",
        "full_multiplier_fallback",
    ): "power-full-grid-validation-v1",
    (
        "final",
        "full_multiplier_fallback",
    ): "power-final-full-multiplier-v1",
}


def _artifact_paths(value: object) -> set[str]:
    return {ref.relative_path for ref in _walk_artifact_refs(value)}


def _ref_identity(
    value: object,
    *,
    field: str,
) -> tuple[str, str, int, str]:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    try:
        return (
            cast(str, value["relative_path"]),
            cast(str, value["sha256"]),
            cast(int, value["byte_count"]),
            cast(str, value["media_type"]),
        )
    except KeyError as exc:
        raise RecordValidationError(
            f"{field} is missing ArtifactRef field {exc.args[0]!r}"
        ) from exc


def _power_authority_sha256(payload: Mapping[str, object]) -> str:
    return _ref_identity(
        payload["authority_ref"],
        field="power authority_ref",
    )[1]


def _document_ref_identity(
    document: _ScientificDocument,
) -> tuple[str, str, int, str]:
    return (
        document.relative_path,
        document.sha256,
        document.byte_count,
        "application/json",
    )


def _require_parent_chain(
    value: object,
    expected: Sequence[_ScientificDocument | Mapping[str, object]],
    *,
    field: str,
) -> None:
    if not isinstance(value, list):
        raise RecordValidationError(f"{field} must be an ArtifactRef array")
    actual_identities = [
        _ref_identity(ref, field=f"{field}[{index}]") for index, ref in enumerate(value)
    ]
    expected_identities = [
        (
            _document_ref_identity(parent)
            if isinstance(parent, _ScientificDocument)
            else _ref_identity(parent, field=f"{field} expected[{index}]")
        )
        for index, parent in enumerate(expected)
    ]
    if actual_identities != expected_identities:
        raise RecordValidationError(
            f"{field} does not exactly parent the frozen power stage chain"
        )


def _extract_ordered_cell_ids(value: object) -> list[str] | None:
    candidate = value
    if isinstance(candidate, Mapping):
        for key in ("cells", "cell_ids", "grid"):
            if key in candidate:
                candidate = candidate[key]
                break
    if not isinstance(candidate, list):
        return None
    cell_ids: list[str] = []
    for item in candidate:
        if isinstance(item, str):
            cell_id = item
        elif isinstance(item, Mapping):
            candidate_cell_id = item.get("cell_id")
            if not isinstance(candidate_cell_id, str):
                return None
            cell_id = candidate_cell_id
        else:
            return None
        if not isinstance(cell_id, str) or not cell_id:
            return None
        cell_ids.append(cell_id)
    return cell_ids


def _power_grid_cell_ids(
    payload: Mapping[str, object],
    *,
    run_root: Path,
) -> list[str]:
    grid_value = payload["grid_ref"]
    if not isinstance(grid_value, Mapping):
        raise RecordValidationError("power grid_ref must be an ArtifactRef")
    grid_ref = ArtifactRef(**cast(dict[str, Any], dict(grid_value)))
    path, raw = _read_ref(grid_ref, run_root=run_root)
    decoded = _load_json_bytes(raw, source=path)
    cell_ids = _extract_ordered_cell_ids(decoded)
    if cell_ids is None:
        # Task 8A's compact frozen grid predates its explicit cell manifest.
        # The simulator derives that manifest exclusively from the closed grid
        # values; this preserves existing fixture bytes while keeping the
        # report topology deterministic.
        from .power import frozen_power_cells
        cell_ids = [cell.cell_id for cell in frozen_power_cells()]
    if not cell_ids or len(cell_ids) != len(set(cell_ids)):
        raise RecordValidationError(
            "power grid_ref must expose unique ordered cell IDs"
        )
    return cell_ids


def _validate_power_attempt_topology(
    documents: Sequence[_ScientificDocument],
    *,
    run_root: Path,
) -> None:
    by_authority: dict[str, list[_ScientificDocument]] = {}
    for document in documents:
        payload = _power_payload(document)
        by_authority.setdefault(
            _power_authority_sha256(payload),
            [],
        ).append(document)

    if len(by_authority) != 1:
        raise RecordValidationError(
            "power reports must share exactly one authority_ref SHA-256"
        )

    for authority_sha256, authority_documents in by_authority.items():
        baseline_payload = _power_payload(authority_documents[0])
        authority = cast(str, baseline_payload["decision_authority"])
        for document in authority_documents[1:]:
            payload = _power_payload(document)
            for field in (
                "authority_ref",
                "roster_ref",
                "grid_ref",
                "screen_topology_ref",
                "config_ref",
                "numeric_fixture_ref",
            ):
                _require_artifact_ref_equal(
                    payload[field],
                    baseline_payload[field],
                    field=(f"power authority {authority!r}/{authority_sha256} {field}"),
                )
            for field in (
                "decision_authority",
                "tier_membership_sha256",
                "rng_contract_sha256",
            ):
                if payload[field] != baseline_payload[field]:
                    raise RecordValidationError(
                        f"power authority {authority!r} {field} differs"
                    )
            if payload["numeric_contract"] != baseline_payload["numeric_contract"]:
                raise RecordValidationError(
                    f"power authority {authority!r} numeric source contract differs"
                )
        ordered_grid_cell_ids = _power_grid_cell_ids(
            baseline_payload,
            run_root=run_root,
        )

        nonfinal = [
            document
            for document in authority_documents
            if _power_payload(document)["stage"] != "final"
        ]
        by_attempt: dict[tuple[str, int], list[_ScientificDocument]] = {}
        for document in nonfinal:
            payload = _power_payload(document)
            key = (cast(str, payload["phase"]), cast(int, payload["generation"]))
            by_attempt.setdefault(key, []).append(document)

        gaussian_validations = [
            document
            for document in nonfinal
            if (
                _power_payload(document)["phase"] == "gaussian_approximation"
                and _power_payload(document)["stage"] == "validation"
            )
        ]
        terminal_gaussian_validation = (
            max(
                gaussian_validations,
                key=lambda document: cast(
                    int,
                    _power_payload(document)["generation"],
                ),
            )
            if gaussian_validations
            else None
        )

        for (phase, generation), attempt_documents in by_attempt.items():
            screens = [
                document
                for document in attempt_documents
                if _power_payload(document)["stage"] == "screen"
            ]
            if len(screens) != 1:
                raise RecordValidationError(
                    "each power phase/generation requires exactly one screen"
                )
            screen = screens[0]
            screen_payload = _power_payload(screen)
            if screen_payload["cell_count"] != len(ordered_grid_cell_ids):
                raise RecordValidationError(
                    "power screen cell_count differs from the ordered grid"
                )
            screen_shard_count = cast(int, screen_payload["shard_count"])
            for document in attempt_documents:
                payload = _power_payload(document)
                if payload["shard_count"] != screen_shard_count:
                    raise RecordValidationError(
                        "power shard_count differs from the screen-frozen count"
                    )
                stage = cast(str, payload["stage"])
                expected_kernel_id = _POWER_KERNEL_IDS.get((stage, phase))
                if (
                    expected_kernel_id is None
                    or payload["kernel_id"] != expected_kernel_id
                ):
                    raise RecordValidationError(
                        "power kernel_id is not derived from stage and phase"
                    )

            shards = sorted(
                (
                    document
                    for document in attempt_documents
                    if _power_payload(document)["stage"] == "shard"
                ),
                key=lambda document: cast(
                    int,
                    _power_payload(document)["shard_index"],
                ),
            )
            selections = [
                document
                for document in attempt_documents
                if _power_payload(document)["stage"] == "selection"
            ]
            validations = [
                document
                for document in attempt_documents
                if _power_payload(document)["stage"] == "validation"
            ]
            if len(selections) > 1 or len(validations) > 1:
                raise RecordValidationError(
                    "power attempt has duplicate downstream stage identities"
                )
            if phase == "gaussian_approximation":
                _require_parent_chain(
                    screen_payload["parent_refs"],
                    [],
                    field="Gaussian screen parent_refs",
                )
            else:
                screen_parents = cast(list[object], screen_payload["parent_refs"])
                if len(screen_parents) != 1:
                    raise RecordValidationError(
                        "full-multiplier screen must parent one Gaussian trigger"
                    )
                trigger_identity = _ref_identity(
                    screen_parents[0],
                    field="full-multiplier screen parent_refs[0]",
                )
                if (
                    _ref_identity(
                        screen_payload["fallback_trigger_ref"],
                        field="full-multiplier screen fallback_trigger_ref",
                    )
                    != trigger_identity
                ):
                    raise RecordValidationError(
                        "full-multiplier screen fallback_trigger_ref differs "
                        "from its explicit parent"
                    )
                if (
                    terminal_gaussian_validation is None
                    or trigger_identity
                    != _document_ref_identity(terminal_gaussian_validation)
                    or _power_payload(terminal_gaussian_validation)[
                        "approximation_receipt"
                    ]["passed"]  # type: ignore[index]
                    is not False
                ):
                    raise RecordValidationError(
                        "full-multiplier fallback must parent the terminal "
                        "failed Gaussian validation"
                    )

            if not shards:
                if selections or validations:
                    raise RecordValidationError(
                        "power downstream stages require a complete shard set"
                    )
                continue
            shard_counts = {
                cast(int, _power_payload(shard)["shard_count"]) for shard in shards
            }
            if len(shard_counts) != 1:
                raise RecordValidationError(
                    "power shard_count must be identical across the shard set"
                )
            dataset_counts = {
                cast(int, _power_payload(shard)["dataset_count"]) for shard in shards
            }
            if len(dataset_counts) != 1:
                raise RecordValidationError(
                    "power dataset_count must be identical across the shard set"
                )
            shard_count = next(iter(shard_counts))
            shard_indices = [
                cast(int, _power_payload(shard)["shard_index"]) for shard in shards
            ]
            if len(shards) > shard_count or shard_indices != list(range(len(shards))):
                raise RecordValidationError(
                    "power shards must be contiguous and zero-based without gaps"
                )
            merged_cell_ids: list[str] = []
            for shard in shards:
                shard_payload = _power_payload(shard)
                _require_parent_chain(
                    shard_payload["parent_refs"],
                    [screen],
                    field="power shard parent_refs",
                )
                cell_results = cast(
                    list[Mapping[str, object]],
                    shard_payload["cell_results"],
                )
                shard_cell_ids = [
                    cast(str, result["cell_id"]) for result in cell_results
                ]
                if len(shard_cell_ids) != len(set(shard_cell_ids)):
                    raise RecordValidationError(
                        "power shard contains duplicate cell IDs"
                    )
                merged_cell_ids.extend(shard_cell_ids)
            complete_shard_set = len(shards) == shard_count
            expected_cell_ids = (
                ordered_grid_cell_ids
                if complete_shard_set
                else ordered_grid_cell_ids[: len(merged_cell_ids)]
            )
            if merged_cell_ids != expected_cell_ids:
                raise RecordValidationError(
                    "power shard cell coverage has gaps, overlap, or wrong order"
                )

            if phase == "gaussian_approximation":
                if validations and not selections:
                    raise RecordValidationError(
                        "Gaussian validation requires a selection parent"
                    )
                if selections:
                    if not complete_shard_set:
                        raise RecordValidationError(
                            "Gaussian selection requires complete shard coverage"
                        )
                    selection = selections[0]
                    _require_parent_chain(
                        _power_payload(selection)["parent_refs"],
                        [screen, *shards],
                        field="power selection parent_refs",
                    )
                if validations:
                    selection = selections[0]
                    _require_parent_chain(
                        _power_payload(validations[0])["parent_refs"],
                        [screen, *shards, selection],
                        field="Gaussian validation parent_refs",
                    )
            else:
                if selections:
                    raise RecordValidationError(
                        "full-multiplier fallback forbids a selection stage"
                    )
                if validations:
                    if not complete_shard_set:
                        raise RecordValidationError(
                            "full-multiplier validation requires complete shards"
                        )
                    validation_payload = _power_payload(validations[0])
                    trigger = cast(
                        Mapping[str, object],
                        validation_payload["fallback_trigger_ref"],
                    )
                    _require_parent_chain(
                        validation_payload["parent_refs"],
                        [trigger, screen, *shards],
                        field="full-multiplier validation parent_refs",
                    )
                    if terminal_gaussian_validation is None or _ref_identity(
                        trigger,
                        field="full-multiplier fallback_trigger_ref",
                    ) != _document_ref_identity(terminal_gaussian_validation):
                        raise RecordValidationError(
                            "full-multiplier validation does not use the terminal "
                            "failed Gaussian validation"
                        )
                    if validation_payload["complete_cell_ids"] != ordered_grid_cell_ids:
                        raise RecordValidationError(
                            "full-multiplier validation lacks full ordered cell coverage"
                        )


def _validate_power_identities(
    documents: Sequence[_ScientificDocument],
    *,
    run_root: Path,
) -> None:
    # The authority blob is a referenced, closed contract rather than a
    # scientific record kind.  Validate it before trusting any report mirrors.
    # Importing here avoids a module-import cycle with the generic artifact IO.
    from .power import (_roster_group_sizes, _roster_joint_group_labels, grid_content_sha256, load_power_authority,
                        load_power_config, validate_power_execution_receipt)

    for document in documents:
        payload = _power_payload(document)
        authority_ref = ArtifactRef(**cast(dict[str, Any], dict(payload["authority_ref"])))
        authority = load_power_authority(authority_ref, run_root=run_root)
        grid_ref = ArtifactRef(**cast(dict[str, Any], dict(payload["grid_ref"])))
        topology_ref = ArtifactRef(**cast(dict[str, Any], dict(payload["screen_topology_ref"])))
        load_power_config(authority_ref, grid_ref, topology_ref, run_root=run_root)
        if payload["decision_authority"] != authority.authority_kind:
            raise RecordValidationError("power decision_authority is not derived from authority_ref")
        _require_artifact_ref_equal(
            payload["roster_ref"],
            _ref_mapping(authority.roster_ref),
            field="power roster_ref",
        )
        if payload["tier_membership_sha256"] != authority.tier_membership_sha256:
            raise RecordValidationError("power tier_membership_sha256 is not derived from authority_ref")
        if payload["rng_contract_sha256"] != load_power_config(
            authority_ref, grid_ref, topology_ref, run_root=run_root
        ).rng_contract_sha256:
            raise RecordValidationError("power rng_contract_sha256 differs from frozen grid contract")
        if payload["grid_content_sha256"] != grid_content_sha256(grid_ref, run_root=run_root):
            raise RecordValidationError("power grid_content_sha256 differs from closed grid bytes")
        if payload["stage"] == "shard":
            layout = _roster_group_sizes(authority, run_root=run_root)
            joint_group_labels = _roster_joint_group_labels(authority, run_root=run_root)
            for result in cast(list[Mapping[str, object]], payload["cell_results"]):
                validate_power_execution_receipt(result, authority=authority,
                    grid_digest=cast(str, payload["grid_content_sha256"]), roster_group_sizes=layout,
                    joint_group_labels=joint_group_labels)
    _validate_power_attempt_topology(documents, run_root=run_root)
    by_authority: dict[str, list[_ScientificDocument]] = {}
    for document in documents:
        payload = _power_payload(document)
        authority_sha256 = _power_authority_sha256(payload)
        by_authority.setdefault(authority_sha256, []).append(document)
    for authority_sha256, authority_documents in by_authority.items():
        authority = cast(
            str,
            _power_payload(authority_documents[0])["decision_authority"],
        )
        nonfinal: list[_ScientificDocument] = []
        finals: list[_ScientificDocument] = []
        identities: set[tuple[object, ...]] = set()
        for document in authority_documents:
            payload = _power_payload(document)
            stage = cast(str, payload["stage"])
            if stage == "final":
                finals.append(document)
                continue
            identity = (
                authority_sha256,
                payload["phase"],
                payload["generation"],
                stage,
                payload.get("shard_index") if stage == "shard" else None,
            )
            if identity in identities:
                raise RecordValidationError(
                    f"duplicate power attempt identity: {identity!r}"
                )
            identities.add(identity)
            nonfinal.append(document)
        if len(finals) != 1:
            raise RecordValidationError(
                f"power authority {authority!r} requires exactly one final"
            )
        final_payload = _power_payload(finals[0])
        attempted_paths = {document.relative_path for document in nonfinal}
        all_attempt_paths = {
            ref.relative_path
            for ref in _walk_artifact_refs(final_payload["all_attempt_refs"])
        }
        if attempted_paths != all_attempt_paths:
            raise RecordValidationError(
                "final all_attempt_refs must parent every immutable power attempt"
            )
        parent_paths = {
            ref.relative_path
            for ref in _walk_artifact_refs(final_payload["parent_refs"])
        }
        if parent_paths != attempted_paths:
            raise RecordValidationError(
                "final parent_refs must parent every immutable power attempt"
            )
        finalization = cast(Mapping[str, object], final_payload["finalization"])
        phase_order = {
            "gaussian_approximation": 0,
            "full_multiplier_fallback": 1,
        }

        def attempt_order(document: _ScientificDocument) -> tuple[int, int]:
            payload = _power_payload(document)
            return (
                phase_order[cast(str, payload["phase"])],
                cast(int, payload["generation"]),
            )

        def is_terminal_validation(document: _ScientificDocument) -> bool:
            payload = _power_payload(document)
            if payload["stage"] != "validation":
                return False
            if payload["phase"] == "full_multiplier_fallback":
                return True
            approximation = cast(
                Mapping[str, object],
                payload["approximation_receipt"],
            )
            return approximation["passed"] is True

        for validation in nonfinal:
            validation_payload = _power_payload(validation)
            if validation_payload["stage"] != "validation":
                continue
            validation_order = attempt_order(validation)
            later_documents = [
                document
                for document in nonfinal
                if attempt_order(document) > validation_order
            ]
            if not later_documents:
                continue
            if validation_payload[
                "phase"
            ] == "gaussian_approximation" and not is_terminal_validation(validation):
                if any(
                    _power_payload(document)["phase"] != "full_multiplier_fallback"
                    for document in later_documents
                ):
                    raise RecordValidationError(
                        "a failed Gaussian approximation validation may "
                        "transition only to full-multiplier fallback"
                    )
                continue
            raise RecordValidationError(
                "a persisted terminal power validation cannot be superseded "
                "by a later phase or generation"
            )

        if finalization["kind"] == "completed_chain":
            phase = finalization["selected_phase"]
            generation = finalization["selected_generation"]
            expected_final_kernel_id = _POWER_KERNEL_IDS[("final", cast(str, phase))]
            if finalization["selected_kernel_id"] != expected_final_kernel_id:
                raise RecordValidationError(
                    "completed power finalization selected_kernel_id is not "
                    "derived from selected_phase"
                )
            if (
                final_payload["phase"] != phase
                or final_payload["generation"] != generation
            ):
                raise RecordValidationError(
                    "final power report phase/generation differs from its "
                    "completed selection"
                )
            selected_attempt_order = (
                phase_order[cast(str, phase)],
                cast(int, generation),
            )
            if any(
                attempt_order(document) > selected_attempt_order
                for document in nonfinal
            ):
                raise RecordValidationError(
                    "completed power finalization must select the terminal "
                    "latest phase/generation attempt"
                )
            if any(
                attempt_order(document) < selected_attempt_order
                and is_terminal_validation(document)
                for document in nonfinal
            ):
                raise RecordValidationError(
                    "a terminal power validation cannot be superseded; only "
                    "an earlier incomplete attempt or failed Gaussian "
                    "approximation transition may precede finalization"
                )
            selected_tier = finalization["selected_tier"]
            decision = finalization["decision"]
            if authority == "roster_bound_selection":
                if selected_tier not in (120, 160) or decision != "GO":
                    raise RecordValidationError(
                        "roster-bound completed power chain requires a selected "
                        "passing C120/C160 tier and GO decision"
                    )
            elif selected_tier is not None or decision != "CONDITIONAL_ONLY":
                raise RecordValidationError(
                    "synthetic completed power chain must be CONDITIONAL_ONLY "
                    "without tier-selection authority"
                )
            document_by_path = {
                document.relative_path: document for document in nonfinal
            }

            def selected_document(
                ref_value: object,
                *,
                expected_stage: str,
                field: str,
            ) -> _ScientificDocument:
                refs = tuple(_walk_artifact_refs(ref_value))
                if len(refs) != 1:
                    raise RecordValidationError(
                        f"power finalization {field} must be one ArtifactRef"
                    )
                document = document_by_path.get(refs[0].relative_path)
                if document is None:
                    raise RecordValidationError(
                        f"power finalization {field} is not an attempted report"
                    )
                payload = _power_payload(document)
                if (
                    payload["stage"] != expected_stage
                    or payload["phase"] != phase
                    or payload["generation"] != generation
                ):
                    raise RecordValidationError(
                        f"power finalization {field} has wrong stage, phase, or generation"
                    )
                return document

            selected_screen_document = selected_document(
                finalization["selected_screen_ref"],
                expected_stage="screen",
                field="selected_screen_ref",
            )
            if (
                finalization["selected_shard_count"]
                != _power_payload(selected_screen_document)["shard_count"]
            ):
                raise RecordValidationError(
                    "power finalization selected_shard_count differs from "
                    "the selected screen"
                )
            shard_refs = tuple(_walk_artifact_refs(finalization["selected_shard_refs"]))
            if not shard_refs:
                raise RecordValidationError("selected power chain lacks a shard")
            selected_shard_documents: list[_ScientificDocument] = []
            for index, shard_ref in enumerate(shard_refs):
                selected_shard_documents.append(
                    selected_document(
                        _ref_mapping(shard_ref),
                        expected_stage="shard",
                        field=f"selected_shard_refs[{index}]",
                    )
                )
            complete_shard_documents = sorted(
                (
                    document
                    for document in nonfinal
                    if (
                        _power_payload(document)["stage"] == "shard"
                        and _power_payload(document)["phase"] == phase
                        and _power_payload(document)["generation"] == generation
                    )
                ),
                key=lambda document: cast(
                    int,
                    _power_payload(document)["shard_index"],
                ),
            )
            if [
                _document_ref_identity(document)
                for document in selected_shard_documents
            ] != [
                _document_ref_identity(document)
                for document in complete_shard_documents
            ]:
                raise RecordValidationError(
                    "power finalization selected_shard_refs do not exactly "
                    "cover the selected shard set"
                )
            if phase == "gaussian_approximation":
                selection_document = selected_document(
                    finalization["selected_selection_ref"],
                    expected_stage="selection",
                    field="selected_selection_ref",
                )
                validation_document = selected_document(
                    finalization["selected_validation_ref"],
                    expected_stage="validation",
                    field="selected_validation_ref",
                )
                selection_payload = _power_payload(selection_document)
                selected_cells = cast(
                    list[object],
                    selection_payload["selected_cells"],
                )
                if (
                    len(selected_cells) != 5
                    or selection_payload["selection_count"] != 5
                ):
                    raise RecordValidationError(
                        "Gaussian completed chain requires the frozen worst five cells"
                    )
                validation_payload = _power_payload(validation_document)
                approximation_receipt = cast(
                    Mapping[str, object],
                    validation_payload["approximation_receipt"],
                )
                if approximation_receipt["passed"] is not True:
                    raise RecordValidationError(
                        "Gaussian completed chain requires a passing "
                        "approximation validation receipt"
                    )
                expected_tier_decision = (
                    f"C{selected_tier}"
                    if authority == "roster_bound_selection"
                    else "CONDITIONAL_ONLY"
                )
                if (
                    approximation_receipt["gaussian_tier_decision"]
                    != expected_tier_decision
                    or approximation_receipt["full_multiplier_tier_decision"]
                    != expected_tier_decision
                ):
                    raise RecordValidationError(
                        "Gaussian completed verdict differs from its "
                        "authority-bound approximation receipt"
                    )
                if validation_payload["selected_cells"] != selected_cells:
                    raise RecordValidationError(
                        "Gaussian validation cells differ from the frozen selection"
                    )
                interval_cells = {
                    receipt.get("cell_id")
                    for receipt in cast(
                        list[Mapping[str, object]],
                        validation_payload["interval_receipts"],
                    )
                }
                if interval_cells != set(selected_cells):
                    raise RecordValidationError(
                        "Gaussian validation intervals do not cover the worst five"
                    )
            else:
                validation_document = selected_document(
                    finalization["full_grid_validation_ref"],
                    expected_stage="validation",
                    field="full_grid_validation_ref",
                )
                fallback_refs = tuple(
                    _walk_artifact_refs(finalization["fallback_trigger_ref"])
                )
                if len(fallback_refs) != 1:
                    raise RecordValidationError(
                        "fallback_trigger_ref must be one ArtifactRef"
                    )
                fallback = document_by_path.get(fallback_refs[0].relative_path)
                if (
                    fallback is None
                    or _power_payload(fallback)["phase"] != "gaussian_approximation"
                ):
                    raise RecordValidationError(
                        "full-multiplier chain must parent a failed Gaussian trigger"
                    )
                validation_payload = _power_payload(validation_document)
                if (
                    validation_payload["selected_tier"] != selected_tier
                    or validation_payload["decision"] != decision
                ):
                    raise RecordValidationError(
                        "full-multiplier completed verdict differs from its "
                        "full-grid validation receipt"
                    )
                validation_fallback = cast(
                    Mapping[str, object],
                    validation_payload["fallback_trigger_ref"],
                )
                if (
                    validation_fallback.get("relative_path") != fallback.relative_path
                    or validation_fallback.get("sha256") != fallback.sha256
                ):
                    raise RecordValidationError(
                        "full-grid validation uses a different fallback trigger"
                    )
        else:
            finalization_kind = cast(str, finalization["kind"])
            if (
                finalization_kind == "feasibility_no_go"
                and authority != "roster_bound_selection"
            ):
                raise RecordValidationError(
                    "synthetic power authority cannot finalize FEASIBILITY_NO_GO"
                )
            if (
                finalization_kind == "synthetic_validation_failed"
                and authority != "synthetic_validation"
            ):
                raise RecordValidationError(
                    "roster-bound power authority cannot finalize "
                    "synthetic_validation_failed"
                )
            terminal_ref = cast(
                Mapping[str, object],
                finalization["terminal_attempt_ref"],
            )
            terminal_path = cast(str, terminal_ref["relative_path"])
            terminal = next(
                (
                    document
                    for document in nonfinal
                    if document.relative_path == terminal_path
                ),
                None,
            )
            if terminal is None:
                raise RecordValidationError(
                    "feasibility no-go terminal attempt is not in all_attempt_refs"
                )
            terminal_payload = _power_payload(terminal)
            if terminal_payload["stage"] != finalization["terminal_stage"]:
                raise RecordValidationError(
                    "feasibility no-go terminal_stage does not match its attempt"
                )
            terminal_stage = cast(str, terminal_payload["stage"])
            terminal_phase = cast(str, terminal_payload["phase"])
            if finalization["terminal_phase"] != terminal_phase:
                raise RecordValidationError(
                    "power finalization terminal_phase does not match its attempt"
                )
            expected_terminal_kernel_id = _POWER_KERNEL_IDS[("final", terminal_phase)]
            if finalization["terminal_kernel_id"] != expected_terminal_kernel_id:
                raise RecordValidationError(
                    "power finalization terminal_kernel_id is not derived "
                    "from terminal_phase"
                )
            if finalization["terminal_shard_count"] != terminal_payload["shard_count"]:
                raise RecordValidationError(
                    "power finalization terminal_shard_count differs from "
                    "its terminal attempt"
                )
            if (
                final_payload["phase"] != terminal_phase
                or final_payload["generation"] != terminal_payload["generation"]
            ):
                raise RecordValidationError(
                    "final power report phase/generation differs from its "
                    "terminal attempt"
                )
            reason = finalization["reason"]
            if terminal_stage == "screen":
                phase_reason = (
                    "gaussian_screen_exhausted"
                    if terminal_phase == "gaussian_approximation"
                    else "full_multiplier_screen_exhausted"
                )
                allowed_reasons = {
                    phase_reason,
                    "numeric_fixture_failed",
                    "runtime_bound_exceeded",
                }
            elif terminal_stage == "validation":
                allowed_reasons = (
                    {"synthetic_validation_gate_failed"}
                    if finalization_kind == "synthetic_validation_failed"
                    else {"power_or_type_i_gate_failed"}
                )
            else:
                allowed_reasons = {"attempt_incomplete"}
            if reason not in allowed_reasons:
                raise RecordValidationError(
                    "power failure reason does not match its terminal phase/stage"
                )
            if reason == "power_or_type_i_gate_failed":
                if terminal_phase == "full_multiplier_fallback":
                    if (
                        terminal_payload["selected_tier"] is not None
                        or terminal_payload["decision"] != "NO_GO"
                    ):
                        raise RecordValidationError(
                            "full-multiplier gate-failure no-go differs from "
                            "its validation tier/decision receipt"
                        )
                else:
                    approximation = cast(
                        Mapping[str, object],
                        terminal_payload["approximation_receipt"],
                    )
                    if (
                        approximation["passed"] is not True
                        or approximation["gaussian_tier_decision"]
                        != "FEASIBILITY_NO_GO"
                        or approximation["full_multiplier_tier_decision"]
                        != "FEASIBILITY_NO_GO"
                    ):
                        raise RecordValidationError(
                            "Gaussian gate-failure no-go differs from its "
                            "validation tier-decision receipt"
                        )
            if _ref_identity(
                terminal_ref,
                field="feasibility no-go terminal_attempt_ref",
            ) != _document_ref_identity(terminal):
                raise RecordValidationError(
                    "feasibility no-go terminal_attempt_ref metadata differs "
                    "from the terminal attempt"
                )
            phase = terminal_payload["phase"]
            generation = terminal_payload["generation"]
            attempt_documents = [
                document
                for document in nonfinal
                if (
                    _power_payload(document)["phase"] == phase
                    and _power_payload(document)["generation"] == generation
                )
            ]
            downstream_stages = {
                cast(str, _power_payload(document)["stage"])
                for document in attempt_documents
            }
            if terminal_stage == "screen" and downstream_stages != {"screen"}:
                raise RecordValidationError(
                    "screen no-go has fictitious downstream attempt refs"
                )
            if terminal_stage == "shard":
                if downstream_stages - {"screen", "shard"}:
                    raise RecordValidationError(
                        "shard no-go has fictitious downstream attempt refs"
                    )
                shards = sorted(
                    (
                        document
                        for document in attempt_documents
                        if _power_payload(document)["stage"] == "shard"
                    ),
                    key=lambda document: cast(
                        int,
                        _power_payload(document)["shard_index"],
                    ),
                )
                if not shards or terminal is not shards[-1]:
                    raise RecordValidationError(
                        "shard no-go must name the last contiguous shard"
                    )
            if terminal_stage == "selection" and "validation" in downstream_stages:
                raise RecordValidationError(
                    "selection no-go has a fictitious validation attempt"
                )
            terminal_attempt_order = (
                phase_order[cast(str, phase)],
                cast(int, generation),
            )
            if any(
                (
                    phase_order[cast(str, _power_payload(document)["phase"])],
                    cast(int, _power_payload(document)["generation"]),
                )
                > terminal_attempt_order
                for document in nonfinal
            ):
                raise RecordValidationError(
                    "feasibility no-go does not name the terminal power attempt"
                )
            if any(
                attempt_order(document) < terminal_attempt_order
                and is_terminal_validation(document)
                for document in nonfinal
            ):
                raise RecordValidationError(
                    "feasibility no-go cannot supersede an earlier terminal "
                    "power validation"
                )
        if final_payload["phase"] != phase or final_payload["generation"] != generation:
            raise RecordValidationError(
                "final phase/generation must name its selected or terminal attempt"
            )


def _entry_mapping(entry: ArtifactEntry) -> dict[str, object]:
    return cast(dict[str, object], asdict(entry))


def _artifact_entries(
    run_root: Path,
    required_document_kinds: Collection[str],
    *,
    excluded: Collection[Path],
) -> list[ArtifactEntry]:
    required = list(required_document_kinds)
    if (
        len(required) != len(set(required))
        or "resampling_artifact_root" in required
        or any(kind not in SCHEMA_BY_KIND for kind in required)
    ):
        raise RecordValidationError("required_document_kinds is invalid")
    documents = _scientific_documents(run_root, excluded=excluded)
    _validate_kind_identities(
        documents,
        required_document_kinds=set(required),
        run_root=run_root,
    )
    if not documents:
        raise RecordValidationError("scientific artifact closure is empty")
    manifests = [
        document
        for document in documents.values()
        if document.value["record_kind"] == "resampling_study_manifest"
    ]
    if len(manifests) != 1:
        raise RecordValidationError("artifact closure requires one study manifest")
    manifest_value = manifests[0].value
    for document in documents.values():
        for field in ("study_id", "frozen_created_at", "provenance"):
            if document.value[field] != manifest_value[field]:
                raise RecordValidationError(
                    f"{document.relative_path}: {field} differs from manifest"
                )
    manifest_payload = cast(Mapping[str, object], manifest_value["payload"])
    required_ref = ArtifactRef(
        **cast(
            dict[str, Any],
            dict(
                cast(
                    Mapping[str, object],
                    manifest_payload["required_document_kinds_ref"],
                )
            ),
        )
    )
    required_path, required_bytes = _read_ref(required_ref, run_root=run_root)
    frozen_required = _required_kind_list(
        _load_json_bytes(required_bytes, source=required_path)
    )
    if frozen_required != sorted(required):
        raise RecordValidationError(
            "required_document_kinds differ from the manifest-bound source"
        )

    refs_by_path: dict[str, ArtifactRef] = {}
    for document in documents.values():
        for ref in _walk_artifact_refs(document.value):
            previous = refs_by_path.get(ref.relative_path)
            if previous is not None and previous != ref:
                raise RecordValidationError(
                    f"conflicting artifact_ref metadata for {ref.relative_path!r}"
                )
            refs_by_path[ref.relative_path] = ref
            _read_ref(ref, run_root=run_root)

    entries_by_path: dict[str, ArtifactEntry] = {}
    for relative_path, document in documents.items():
        incoming = refs_by_path.get(relative_path)
        if incoming is not None:
            if (
                incoming.sha256 != document.sha256
                or incoming.byte_count != document.byte_count
                or incoming.media_type != "application/json"
            ):
                raise RecordValidationError(
                    f"scientific record ref mismatch: {relative_path!r}"
                )
            role = incoming.role
        else:
            role = cast(str, document.value["record_kind"])
        entries_by_path[relative_path] = ArtifactEntry(
            relative_path=relative_path,
            sha256=document.sha256,
            byte_count=document.byte_count,
            entry_kind="scientific_record",
            document_kind=cast(str, document.value["record_kind"]),
            role=role,
            media_type="application/json",
        )

    for relative_path, ref in refs_by_path.items():
        if relative_path in documents:
            continue
        _path, payload = _read_ref(ref, run_root=run_root)
        entries_by_path[relative_path] = ArtifactEntry(
            relative_path=relative_path,
            sha256=hashlib.sha256(payload).hexdigest(),
            byte_count=len(payload),
            entry_kind="referenced_blob",
            document_kind=None,
            role=ref.role,
            media_type=ref.media_type,
        )
    return [entries_by_path[path] for path in sorted(entries_by_path)]


def _normalize_required_kinds(
    required_document_kinds: Collection[str],
) -> list[str]:
    required = list(required_document_kinds)
    if tuple(sorted(required)) != _FROZEN_UPSTREAM_KINDS or len(required) != len(
        set(required)
    ):
        raise RecordValidationError(
            "required_document_kinds must exactly equal the frozen upstream kinds"
        )
    return list(_FROZEN_UPSTREAM_KINDS)


def _entries_digest(entries: Sequence[ArtifactEntry]) -> str:
    payload = [_entry_mapping(entry) for entry in entries]
    return hashlib.sha256(canonical_json_bytes(payload, indent=None)).hexdigest()


def seal_artifact_root(
    run_root: Path,
    required_document_kinds: Collection[str],
    out: Path,
    *,
    study_id: str,
    frozen_created_at: str,
    provenance: Mapping[str, str],
) -> ArtifactRef:
    """Seal the complete sorted recursive scientific artifact closure."""

    root = _run_root(run_root)
    expected_out = root / _RECEIPT_NAME
    resolved_out, _relative = _resolve_inside(out, root, require_exists=False)
    if resolved_out != expected_out:
        raise RecordValidationError(
            f"artifact-root output must be exactly {expected_out}"
        )
    if expected_out.exists():
        raise FileExistsError(expected_out)
    required = _normalize_required_kinds(required_document_kinds)
    entries = _artifact_entries(
        root,
        required,
        excluded={expected_out},
    )
    provenance_copy = cast(dict[str, object], _plain_json(provenance))
    record: dict[str, object] = {
        "record_kind": "resampling_artifact_root",
        "schema_version": "0.1.0",
        "study_id": study_id,
        "frozen_created_at": frozen_created_at,
        "provenance": provenance_copy,
        "payload": {
            "code_sha256": provenance_copy.get("code_sha256"),
            "design_sha256": provenance_copy.get("design_sha256"),
            "entries": [_entry_mapping(entry) for entry in entries],
            "root_sha256": _entries_digest(entries),
            "required_document_kinds": required,
        },
    }
    return write_record(
        expected_out,
        record,
        run_root=root,
        role="artifact_root",
    )


def verify_artifact_root(
    receipt_path: Path,
    run_root: Path,
    *,
    required_document_kinds: Collection[str],
) -> None:
    """Recompute and verify an immutable artifact-root receipt."""

    root = _run_root(run_root)
    receipt, _relative = _resolve_inside(
        receipt_path,
        root,
        require_exists=True,
    )
    if receipt != root / _RECEIPT_NAME:
        raise RecordValidationError(
            f"artifact-root receipt must be exactly {root / _RECEIPT_NAME}"
        )
    record = load_record(receipt)
    if record["record_kind"] != "resampling_artifact_root":
        raise RecordValidationError("receipt is not a resampling artifact root")
    payload = cast(Mapping[str, object], record["payload"])
    required = _normalize_required_kinds(required_document_kinds)
    if payload["required_document_kinds"] != required:
        raise RecordValidationError("required_document_kinds differ from receipt")
    provenance = cast(Mapping[str, object], record["provenance"])
    if (
        payload["code_sha256"] != provenance["code_sha256"]
        or payload["design_sha256"] != provenance["design_sha256"]
    ):
        raise RecordValidationError("artifact-root provenance is inconsistent")
    actual_entries = _artifact_entries(
        root,
        required,
        excluded={receipt},
    )
    manifest_entries = [
        entry
        for entry in actual_entries
        if entry.document_kind == "resampling_study_manifest"
    ]
    if len(manifest_entries) != 1:
        raise RecordValidationError("artifact root lacks its singleton manifest")
    manifest = load_record(root / Path(manifest_entries[0].relative_path))
    for field in ("study_id", "frozen_created_at", "provenance"):
        if record[field] != manifest[field]:
            raise RecordValidationError(
                f"artifact-root {field} differs from study manifest"
            )
    actual_payload = [_entry_mapping(entry) for entry in actual_entries]
    if payload["entries"] != actual_payload:
        raise RecordValidationError(
            "artifact-root entries do not match current closure"
        )
    if payload["root_sha256"] != _entries_digest(actual_entries):
        raise RecordValidationError("artifact-root digest mismatch")


__all__ = [
    "SCHEMA_BY_KIND",
    "RecordValidationError",
    "ArtifactEntry",
    "canonical_digest",
    "validate_record",
    "load_record",
    "write_record",
    "write_jsonl_artifact",
    "seal_study_manifest",
    "verify_digest_link",
    "seal_artifact_root",
    "verify_artifact_root",
    "validate_scientific_graph",
    "validate_preunblind_graph",
]
