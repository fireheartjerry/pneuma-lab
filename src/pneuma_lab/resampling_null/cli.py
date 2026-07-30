"""Fail-closed, zero-spend command line for the resampling-null controller.

This is intentionally a thin adapter: scientific choices stay in sealed records,
and every path accepted after study sealing is a run-root-relative POSIX path.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile

from .artifacts import (_scientific_documents, seal_artifact_root,
                        seal_study_manifest, verify_artifact_root,
                        validate_record, write_record)
from .analysis import analysis_result_payload, analyze as analyze_rows
from .blinding import (issue_unblind_permit, seal_blinded_projection,
                        unblind_and_publish_analysis)
from .freeze import CurrentAnalysisInputs, freeze_analysis
from .assignment import (load_assignment_authority,
                         require_schedulable_power_final)
from .branch_assignment import seal_branch_assignment
from .branch_controller import (load_frozen_prefix_view, prepare_no_intervention_slots,
                                prepare_opaque_work_orders, seal_no_intervention_block)
from .errors import RecordValidationError
from .execution_authority import load_prefix_execution_authority
from .json_io import load_json_bytes, resolve_inside, run_root
from .power import (finalize_synthetic_full_multiplier_report, finalize_synthetic_power_report, finalize_synthetic_validation_failed,
                    load_power_config, seal_roster_bound_power_authority,
                    seal_synthetic_power_authority, screen_power_grid,
                    select_validation_cells, simulate_power_shard,
                    validate_gaussian_approximation, validate_full_multiplier_fallback,
                    POWER_AUTHORITY_MEDIA_TYPE)
from .packets import (IdentifierAtom, NoInterventionPacketMarker,
                      SyntheticPacketArtifactStore, audit_and_seal_packet_index,
                      build_packet_pair, derive_packet_rewrite_artifacts,
                      normalize_synthetic_packet_findings,
                      write_packet_candidate)
from .prefix_index import seal_prefix_index
from .schedule import seal_prefix_schedule
from .secrets import AssignmentSecretStore
from .selftest_fixture import seal_synthetic_selftest_study
from .storage import claim_local_test_storage
from .synthetic_prefix_loop import run_prefix
from .types import (AnalysisConfig, AnalysisRow, ArtifactRef, GroupKind, GroupLabel,
                    TriggerReason)


class _ArgumentError(ValueError):
    """Redacted parser failure that never lets argparse print usage."""


# ArtifactRef identity includes media type.  Most controller records are JSON,
# but power authority is deliberately a closed capability format.  Keep this
# role mapping adjacent to the argv-to-ref boundary so a CLI replay cannot
# silently downgrade a sealed authority to generic JSON.
_REF_MEDIA_BY_ROLE = {
    "power_authority": POWER_AUTHORITY_MEDIA_TYPE,
    "power_grid": "application/json",
    "power_screen_topology": "application/json",
    "power_report": "application/json",
}


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise _ArgumentError("invalid command arguments")


def _relative_name(value: str, *, field: str) -> str:
    """Accept exactly one normalized relative POSIX filename, never a host path."""
    if type(value) is not str or not value or value == "." or "\\" in value or "//" in value:
        raise RecordValidationError(f"{field} must be a normalized root-relative POSIX path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts) or pure.as_posix() != value:
        raise RecordValidationError(f"{field} must be a normalized root-relative POSIX path")
    return value


def _ref(root: Path, name: str, role: str) -> ArtifactRef:
    name = _relative_name(name, field="scientific input")
    path, relative = resolve_inside(Path(name), root, require_exists=True)
    payload = path.read_bytes()
    return ArtifactRef(role=role, relative_path=relative,
                       sha256=hashlib.sha256(payload).hexdigest(), byte_count=len(payload),
                       media_type=_REF_MEDIA_BY_ROLE.get(role, "application/json"))


def _out(root: Path, value: str) -> Path:
    path, _ = resolve_inside(Path(_relative_name(value, field="scientific output")), root, require_exists=False)
    if path.exists():
        raise FileExistsError("scientific output already exists")
    return path


def _shards(root: Path, prefix: str) -> tuple[ArtifactRef, ...]:
    prefix = _relative_name(prefix, field="shard prefix")
    matches = sorted(
        p for p in root.rglob("*.json")
        if (relative := p.relative_to(root).as_posix()).startswith(prefix)
        and len(relative) > len(prefix)
        and relative[len(prefix):].split("/", 1)[0].split(".", 1)[0].isdigit()
    )
    return tuple(_ref(root, p.relative_to(root).as_posix(), "power_report") for p in matches)


def _external_file(value: str, *, root: Path, field: str) -> Path:
    """Resolve a required external file while forbidding controller-root custody."""
    try:
        path = Path(value).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RecordValidationError(f"{field} cannot be resolved") from exc
    if not path.is_file():
        raise RecordValidationError(f"{field} must identify a regular file")
    try:
        path.relative_to(root)
    except ValueError:
        return path
    raise RecordValidationError(f"{field} must remain outside run_root")


def _external_sources(source_root: str, sources: list[str], *, root: Path) -> dict[str, Path]:
    """Resolve named analysis sources only beneath their explicit external root."""
    try:
        base = Path(source_root).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise RecordValidationError("analysis source root cannot be resolved") from exc
    if not base.is_dir():
        raise RecordValidationError("analysis source root must be a directory")
    try:
        base.relative_to(root)
    except ValueError:
        pass
    else:
        raise RecordValidationError("analysis source root must remain outside run_root")
    result: dict[str, Path] = {}
    for source in sources:
        name = _relative_name(source, field="analysis source")
        if name in result:
            raise RecordValidationError("analysis sources must be unique")
        try:
            path = (base / Path(name)).resolve(strict=True)
            path.relative_to(base)
        except (OSError, RuntimeError, ValueError) as exc:
            raise RecordValidationError("analysis source escapes source root") from exc
        if not path.is_file():
            raise RecordValidationError("analysis source must identify a regular file")
        result[name] = path
    return result


def _mapping_ref(ref: ArtifactRef) -> dict[str, object]:
    return {"role": ref.role, "relative_path": ref.relative_path, "sha256": ref.sha256,
            "byte_count": ref.byte_count, "media_type": ref.media_type}


def _payload(record: dict[str, object], *, field: str) -> dict[str, object]:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        raise RecordValidationError(f"{field} payload is malformed")
    return payload


def _task_block_refs(root: Path, prefix: str) -> tuple[ArtifactRef, ...]:
    prefix = _relative_name(prefix, field="task block prefix").rstrip("/")
    prefix_with_slash = prefix + "/"
    refs: list[ArtifactRef] = []
    for path in sorted(root.rglob("*.json")):
        relative = path.relative_to(root).as_posix()
        if not relative.startswith(prefix_with_slash):
            continue
        try:
            record = validate_record(load_json_bytes(path.read_bytes(), source=path))
        except RecordValidationError:
            continue
        if record.get("record_kind") == "resampling_task_block":
            refs.append(_ref(root, relative, "task_block"))
    if not refs:
        raise RecordValidationError("task block prefix contains no sealed task blocks")
    return tuple(refs)


def _candidate_subprocess(frozen_schedule: list[dict[str, object]], closed_outcomes: dict[str, object]) -> object:
    """Run the pure candidate builder with no controller path or ledger argument."""
    request = json.dumps({"frozen_schedule": frozen_schedule, "closed_outcomes": closed_outcomes},
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="pneuma-projection-") as working:
        completed = subprocess.run(
            [sys.executable, "-I", "-m", "pneuma_lab.resampling_null.projection_candidate"],
            input=request, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=working,
            env={"PATH": "/usr/bin:/bin", "PYTHONUTF8": "1"}, check=False,
        )
    if completed.returncode != 0:
        raise RecordValidationError("isolated projection candidate builder failed")
    try:
        rows = json.loads(completed.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecordValidationError("isolated projection candidate is not canonical JSON") from exc
    from .projection_candidate import ProjectionCandidate
    if not isinstance(rows, list):
        raise RecordValidationError("isolated projection candidate has wrong shape")
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if canonical != completed.stdout:
        raise RecordValidationError("isolated projection candidate is not canonical")
    return ProjectionCandidate(tuple(rows), canonical, hashlib.sha256(canonical).hexdigest())


def _analysis_config(path: Path) -> AnalysisConfig:
    """Read the closed frozen decision region; randomness is manifest-derived."""
    value = load_json_bytes(path.read_bytes(), source=path)
    if not isinstance(value, dict) or set(value) != {
        "alpha", "delta_star", "sharp_draws", "multiplier_draws", "max_differential_failure_gap",
    }:
        raise RecordValidationError("analysis config has an unregistered shape")
    try:
        return AnalysisConfig(**value)
    except (TypeError, ValueError) as exc:
        raise RecordValidationError("analysis config is invalid") from exc


def _analysis_rows(clear_rows: tuple[dict[str, object], ...]) -> tuple[AnalysisRow, ...]:
    rows: list[AnalysisRow] = []
    for raw in clear_rows:
        slots = raw.get("slots")
        groups = raw.get("sensitivity_groups")
        if not isinstance(slots, list) or not isinstance(groups, list):
            raise RecordValidationError("unblinded projection row is malformed")
        outcomes: dict[str, dict[str, object]] = {}
        failures: dict[str, bool] = {}
        for slot in slots:
            if not isinstance(slot, dict) or not isinstance(slot.get("arm"), str) or not isinstance(slot.get("outcome"), dict):
                raise RecordValidationError("unblinded projection slot is malformed")
            arm = slot["arm"]
            if arm in outcomes:
                raise RecordValidationError("unblinded projection duplicates an arm")
            outcomes[arm] = slot["outcome"]
            failures[arm] = slot["outcome"].get("infrastructure_failure") is True
        if set(outcomes) != {"REAL", "SHAM", "NONE", "RESAMPLE"}:
            raise RecordValidationError("unblinded projection lacks a four-arm allocation")
        try:
            labels = tuple(GroupLabel(GroupKind(item["kind"]), item["value"]) for item in groups if isinstance(item, dict))
            if len(labels) != len(groups):
                raise ValueError
            rows.append(AnalysisRow(
                task_id=raw["task_id"], benchmark=raw["benchmark"], stratum=raw["stratum"], lineage=raw["lineage"],
                sensitivity_groups=labels, triggered=raw["triggered"], prefix=raw["prefix_success"],
                real=outcomes["REAL"]["success"], sham=outcomes["SHAM"]["success"],
                none=outcomes["NONE"]["success"], resample=outcomes["RESAMPLE"]["success"],
                real_infrastructure_failure=failures["REAL"], sham_infrastructure_failure=failures["SHAM"],
                none_infrastructure_failure=failures["NONE"], resample_infrastructure_failure=failures["RESAMPLE"],
                pipeline_valid=raw["pipeline_valid"], invalid_codes=tuple(raw["validity_codes"]),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            raise RecordValidationError("unblinded projection row is invalid") from exc
    return tuple(rows)


def _schedule_seed(path: Path) -> int:
    try:
        text = path.read_bytes().decode("ascii").strip()
    except UnicodeDecodeError as exc:
        raise RecordValidationError("schedule seed file must be ASCII U64") from exc
    if not text or not text.isdecimal():
        raise RecordValidationError("schedule seed file must contain one decimal U64")
    value = int(text)
    if value >= 2**64:
        raise RecordValidationError("schedule seed file must contain one decimal U64")
    return value


def _schedule_task_ids(schedule_ref: ArtifactRef, study_ref: ArtifactRef, *, root: Path) -> tuple[str, ...]:
    """Check the supplied study is the schedule's exact direct authority."""
    path, _ = resolve_inside(Path(schedule_ref.relative_path), root, require_exists=True)
    record = validate_record(load_json_bytes(path.read_bytes(), source=path))
    if record["record_kind"] != "resampling_prefix_schedule":
        raise RecordValidationError("schedule ref has wrong record kind")
    payload = record["payload"]
    if not isinstance(payload, dict) or payload.get("manifest_ref") != {
        "role": study_ref.role, "relative_path": study_ref.relative_path,
        "sha256": study_ref.sha256, "byte_count": study_ref.byte_count,
        "media_type": study_ref.media_type,
    }:
        raise RecordValidationError("schedule does not descend from supplied study")
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise RecordValidationError("schedule has no selected tasks")
    ids: list[str] = []
    for task in tasks:
        if not isinstance(task, dict) or not isinstance(task.get("task"), dict):
            raise RecordValidationError("schedule task is malformed")
        task_id = task["task"].get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise RecordValidationError("schedule task id is malformed")
        ids.append(task_id)
    if len(ids) != len(set(ids)):
        raise RecordValidationError("schedule task ids must be unique")
    return tuple(ids)


def _emit(ref: ArtifactRef | None = None, *, status: str = "ok", **extra: object) -> None:
    payload: dict[str, object] = {"status": status, **extra}
    if ref is not None:
        payload.update({"digest": ref.sha256, "output": ref.relative_path})
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(prog="pneuma_lab.resampling_null", add_help=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--debug", action="store_true")
    top = parser.add_subparsers(dest="command", required=True)
    selftest = top.add_parser("selftest")
    selftest.add_argument("--defer-artifact-root", action="store_true")
    selftest_stage = selftest.add_mutually_exclusive_group()
    selftest_stage.add_argument("--stop-after-study", action="store_true")
    selftest_stage.add_argument("--resume-after-power")
    study = top.add_parser("study").add_subparsers(dest="study_command", required=True)
    seal = study.add_parser("seal", aliases=["create"])
    for name in ("study", "tasks", "roster", "assignment_program", "provider_lane_plan", "storage_policy_contract", "power_grid", "power_screen_topology", "tokenizer", "packet_template", "packet_policy", "pad_unit_set", "required_kinds"):
        seal.add_argument("--" + name.replace("_", "-") + "-source", required=True)
    seal.add_argument("--revision-source", action="append", required=True)
    seal.add_argument("--eligibility-manifest-source")
    seal.add_argument("--roster-ceremony-policy-source")
    seal.add_argument("--out", required=True)
    check = study.add_parser("validate")
    check.add_argument("--study", required=True)
    power = top.add_parser("power").add_subparsers(dest="power_command", required=True)
    authority = power.add_parser("authority").add_subparsers(dest="authority_kind", required=True)
    for kind in ("synthetic", "roster-bound"):
        p = authority.add_parser(kind); p.add_argument("--study", required=True); p.add_argument("--out", required=True)
    for name in ("screen", "simulate", "select-validation", "validate", "validate-fallback", "finalize"):
        p = power.add_parser(name)
        p.add_argument("--authority", required=True); p.add_argument("--grid-ref", required=True); p.add_argument("--screen-topology-ref", required=True)
        p.add_argument("--out", required=True)
        if name != "finalize": p.add_argument("--screen")
        if name == "screen":
            p.add_argument("--phase", choices=("gaussian_approximation", "full_multiplier_fallback"), required=True); p.add_argument("--generation", type=int, required=True); p.add_argument("--shard-count", type=int, required=True); p.add_argument("--fallback-trigger")
        elif name == "simulate": p.add_argument("--shard-index", type=int, required=True)
        elif name == "select-validation": p.add_argument("--shard-prefix", required=True)
        elif name in ("validate", "validate-fallback"):
            p.add_argument("--shard-prefix", required=True)
            if name == "validate": p.add_argument("--selection", required=True)
        else:
            p.add_argument("--selected-screen"); p.add_argument("--selected-shard-prefix"); p.add_argument("--selected-selection"); p.add_argument("--selected-validation"); p.add_argument("--fallback-validation"); p.add_argument("--completed-gaussian", action="store_true"); p.add_argument("--completed-full-multiplier", action="store_true"); p.add_argument("--synthetic-validation-failed", action="store_true"); p.add_argument("--terminal-attempt"); p.add_argument("--terminal-stage", choices=("screen", "shard", "selection", "validation")); p.add_argument("--reason", choices=("gaussian_screen_exhausted", "full_multiplier_screen_exhausted", "numeric_fixture_failed", "runtime_bound_exceeded", "attempt_incomplete", "synthetic_validation_gate_failed"))
    schedule = top.add_parser("schedule").add_subparsers(dest="schedule_command", required=True)
    schedule_seal = schedule.add_parser("seal")
    schedule_seal.add_argument("--study", required=True); schedule_seal.add_argument("--power-final", required=True)
    schedule_seal.add_argument("--schedule-seed-file", required=True); schedule_seal.add_argument("--out", required=True)
    synthetic = top.add_parser("synthetic").add_subparsers(dest="synthetic_command", required=True)
    prefixes = synthetic.add_parser("prefixes")
    prefixes.add_argument("--study", required=True); prefixes.add_argument("--schedule", required=True); prefixes.add_argument("--out", required=True)
    branches = synthetic.add_parser("branches")
    for name in ("study", "schedule", "assignment", "prefix_index", "packet_index", "analysis_freeze"):
        branches.add_argument("--" + name.replace("_", "-"), required=True)
    branches.add_argument("--out-prefix", required=True)
    assignment = top.add_parser("assignment").add_subparsers(dest="assignment_command", required=True)
    assignment_seal = assignment.add_parser("seal")
    assignment_seal.add_argument("--schedule", required=True); assignment_seal.add_argument("--prefix-index", required=True)
    assignment_seal.add_argument("--assignment-key-file", required=True); assignment_seal.add_argument("--out", required=True)
    packets = top.add_parser("packets").add_subparsers(dest="packets_command", required=True)
    packet_build = packets.add_parser("build")
    packet_build.add_argument("--study", required=True); packet_build.add_argument("--assignment", required=True)
    packet_build.add_argument("--prefix-index", required=True); packet_build.add_argument("--out-candidate", required=True)
    packet_audit = packets.add_parser("audit")
    packet_audit.add_argument("--study", required=True); packet_audit.add_argument("--candidate", required=True)
    packet_audit.add_argument("--schedule", required=True); packet_audit.add_argument("--assignment", required=True)
    packet_audit.add_argument("--prefix-index", required=True); packet_audit.add_argument("--out-index", required=True)
    analysis = top.add_parser("analysis").add_subparsers(dest="analysis_command", required=True)
    analysis_freeze = analysis.add_parser("freeze")
    analysis_freeze.add_argument("--source-root", required=True); analysis_freeze.add_argument("--source", action="append", required=True)
    analysis_freeze.add_argument("--config", required=True); analysis_freeze.add_argument("--projection-schema", required=True)
    analysis_freeze.add_argument("--packet-index", required=True); analysis_freeze.add_argument("--out", required=True)
    project = top.add_parser("project").add_subparsers(dest="project_command", required=True)
    project_seal = project.add_parser("seal")
    project_seal.add_argument("--schedule", required=True); project_seal.add_argument("--analysis-freeze", required=True)
    project_seal.add_argument("--task-block-prefix", required=True); project_seal.add_argument("--out", required=True)
    analyze = top.add_parser("analyze")
    for name in ("study", "projection", "assignment", "analysis_freeze", "packet_index", "unblind_receipt", "out"):
        analyze.add_argument("--" + name.replace("_", "-"), required=True)
    analyze.add_argument("--source-root", required=True); analyze.add_argument("--source", action="append", required=True)
    analyze.add_argument("--config", required=True); analyze.add_argument("--projection-schema", required=True)
    analyze.add_argument("--assignment-key-file", required=True)
    artifacts = top.add_parser("artifacts").add_subparsers(dest="artifact_command", required=True)
    for name in ("seal", "verify"):
        p = artifacts.add_parser(name); p.add_argument("--required-kinds", required=True); p.add_argument("--out" if name == "seal" else "--receipt", required=True)
    status = top.add_parser("status"); status.add_argument("--study")
    return parser


def _config(args: argparse.Namespace, root: Path):
    return load_power_config(_ref(root, args.authority, "power_authority"), _ref(root, args.grid_ref, "power_grid"), _ref(root, args.screen_topology_ref, "power_screen_topology"), run_root=root)


def _artifact_ref(value: object, *, field: str) -> ArtifactRef:
    if not isinstance(value, dict):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    try:
        return ArtifactRef(**value)
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} must be an ArtifactRef") from exc


def _record_for_ref(ref: ArtifactRef, *, root: Path, kind: str) -> dict[str, object]:
    path, _ = resolve_inside(Path(ref.relative_path), root, require_exists=True)
    payload = path.read_bytes()
    if len(payload) != ref.byte_count or hashlib.sha256(payload).hexdigest() != ref.sha256:
        raise RecordValidationError("scientific parent bytes differ from its ref")
    record = validate_record(load_json_bytes(payload, source=path))
    if record.get("record_kind") != kind:
        raise RecordValidationError(f"scientific parent must be {kind}")
    return record


def _same_ref(left: object, right: ArtifactRef, *, field: str) -> None:
    if _artifact_ref(left, field=field) != right:
        raise RecordValidationError(f"{field} differs from supplied authority")


def _packet_manifest_parents(
    study_ref: ArtifactRef, assignment_ref: ArtifactRef, prefix_ref: ArtifactRef, *, root: Path,
) -> tuple[ArtifactRef, ArtifactRef, ArtifactRef, ArtifactRef]:
    """Load the four packet authorities exclusively from the sealed manifest."""
    study = _record_for_ref(study_ref, root=root, kind="resampling_study_manifest")
    assignment = _record_for_ref(assignment_ref, root=root, kind="resampling_assignment_ledger")
    prefix = _record_for_ref(prefix_ref, root=root, kind="resampling_prefix_receipt")
    study_payload = study["payload"]
    assignment_payload = assignment["payload"]
    prefix_payload = prefix["payload"]
    if not isinstance(study_payload, dict) or not isinstance(assignment_payload, dict) or not isinstance(prefix_payload, dict):
        raise RecordValidationError("packet authority payload is malformed")
    _same_ref(assignment_payload.get("manifest_ref"), study_ref, field="assignment manifest_ref")
    _same_ref(assignment_payload.get("prefix_index_ref"), prefix_ref, field="assignment prefix_index_ref")
    schedule_ref = _artifact_ref(assignment_payload.get("schedule_ref"), field="assignment schedule_ref")
    schedule = _record_for_ref(schedule_ref, root=root, kind="resampling_prefix_schedule")
    schedule_payload = schedule.get("payload")
    if not isinstance(schedule_payload, dict):
        raise RecordValidationError("packet schedule payload is malformed")
    _same_ref(schedule_payload.get("manifest_ref"), study_ref, field="schedule manifest_ref")
    _same_ref(prefix_payload.get("schedule_ref"), schedule_ref, field="prefix schedule_ref")
    tokenizer = _artifact_ref(study_payload.get("tokenizer_ref"), field="manifest tokenizer_ref")
    template = _artifact_ref(study_payload.get("packet_template_ref"), field="manifest packet_template_ref")
    policy = _artifact_ref(study_payload.get("packet_policy_ref"), field="manifest packet_policy_ref")
    pads = _artifact_ref(study_payload.get("pad_unit_set_ref"), field="manifest pad_unit_set_ref")
    return tokenizer, template, policy, pads


def _opaque_guidance_paths(
    task_id: str,
    assignment: Mapping[str, object],
    allocation: Mapping[str, object],
) -> tuple[str, str]:
    """Name worker-visible packet payloads by opaque slot capability only."""
    if type(task_id) is not str or not task_id:
        raise RecordValidationError("packet task ID is malformed")
    if assignment.get("task_id") != task_id or allocation.get("task_id") != task_id:
        raise RecordValidationError("packet assignment/allocation task differs")
    slot_arms = assignment.get("slot_arms")
    slot_capabilities = allocation.get("slot_capabilities")
    if not isinstance(slot_arms, list) or not isinstance(slot_capabilities, list):
        raise RecordValidationError("packet slot authority is malformed")
    arm_slots: dict[str, str] = {}
    for index, item in enumerate(slot_arms):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
            or item[1] not in {"REAL", "SHAM", "NONE", "RESAMPLE"}
            or item[1] in arm_slots
        ):
            raise RecordValidationError(f"packet slot_arms[{index}] is malformed")
        arm_slots[item[1]] = item[0]
    capabilities: dict[str, str] = {}
    for index, item in enumerate(slot_capabilities):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or type(item[0]) is not str
            or type(item[1]) is not str
            or len(item[1]) != 64
            or any(char not in "0123456789abcdef" for char in item[1])
            or item[0] in capabilities
        ):
            raise RecordValidationError(
                f"packet slot_capabilities[{index}] is malformed"
            )
        capabilities[item[0]] = item[1]
    if (
        set(arm_slots) != {"REAL", "SHAM", "NONE", "RESAMPLE"}
        or set(capabilities) != set(arm_slots.values())
    ):
        raise RecordValidationError("packet slot authority must close exactly four arms")
    slug = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
    return (
        f"packet-work/{slug}/guidance-{capabilities[arm_slots['REAL']]}.txt",
        f"packet-work/{slug}/guidance-{capabilities[arm_slots['SHAM']]}.txt",
    )


def _build_packet_candidate(
    *, study_ref: ArtifactRef, assignment_ref: ArtifactRef, prefix_ref: ArtifactRef,
    tokenizer_ref: ArtifactRef, packet_template_ref: ArtifactRef, packet_policy_ref: ArtifactRef,
    pad_unit_set_ref: ArtifactRef, root: Path, out: Path,
) -> ArtifactRef:
    """Derive every candidate entry from frozen prefix and assignment receipts."""
    del study_ref  # ancestry was checked by _packet_manifest_parents before this call.
    prefix = _record_for_ref(prefix_ref, root=root, kind="resampling_prefix_receipt")
    assignment = _record_for_ref(assignment_ref, root=root, kind="resampling_assignment_ledger")
    prefix_rows = prefix["payload"].get("task_receipts") if isinstance(prefix["payload"], dict) else None
    assignment_rows = assignment["payload"].get("assignments") if isinstance(assignment["payload"], dict) else None
    allocation_rows = assignment["payload"].get("allocation_receipts") if isinstance(assignment["payload"], dict) else None
    if (
        not isinstance(prefix_rows, list)
        or not isinstance(assignment_rows, list)
        or not isinstance(allocation_rows, list)
    ):
        raise RecordValidationError("packet build parents are malformed")
    assignments = {row.get("task_id"): row for row in assignment_rows if isinstance(row, dict)}
    if len(assignments) != len(assignment_rows):
        raise RecordValidationError("assignment task coverage is malformed")
    allocations = {row.get("task_id"): row for row in allocation_rows if isinstance(row, dict)}
    if len(allocations) != len(allocation_rows) or set(allocations) != set(assignments):
        raise RecordValidationError("packet allocation task coverage is malformed")
    prefix_by_task = {row.get("task_id"): row for row in prefix_rows if isinstance(row, dict)}
    if len(prefix_by_task) != len(prefix_rows) or set(prefix_by_task) != set(assignments):
        raise RecordValidationError("prefix and assignment task coverage differs")
    entries = []
    store = SyntheticPacketArtifactStore(root)
    # The Task-5 APIs re-derive all artifact bytes during audit. This thin loop only
    # chooses deterministic, non-semantic locations for the temporary derivatives.
    from .packets import _load_normalized_findings
    for task_id, prefix_row in prefix_by_task.items():
        if type(task_id) is not str or not task_id:
            raise RecordValidationError("packet task ID is malformed")
        if prefix_row.get("trigger_reason") == "no_intervention_opportunity":
            entries.append(NoInterventionPacketMarker(task_id, prefix_ref.sha256, "no_intervention_opportunity"))
            continue
        assignment_row = assignments[task_id]
        allocation_row = allocations[task_id]
        donor_task_id = assignment_row.get("donor_task_id")
        donor_row = prefix_by_task.get(donor_task_id)
        if type(donor_task_id) is not str or not isinstance(donor_row, dict) or assignment_row.get("donor_match_kind") != "matched":
            raise RecordValidationError("triggered packet lacks a sealed matched donor")
        focal_verifier = _artifact_ref(prefix_row.get("verifier_receipt", {}).get("verifier_artifact_ref") if isinstance(prefix_row.get("verifier_receipt"), dict) else None, field="focal verifier ref")
        donor_verifier = _artifact_ref(donor_row.get("verifier_receipt", {}).get("verifier_artifact_ref") if isinstance(donor_row.get("verifier_receipt"), dict) else None, field="donor verifier ref")
        slug = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
        donor_slug = hashlib.sha256(donor_task_id.encode("utf-8")).hexdigest()
        real = normalize_synthetic_packet_findings(focal_verifier, task_id=task_id, run_root=root, out=root / f"packet-work/{slug}/real.json")
        donor = normalize_synthetic_packet_findings(donor_verifier, task_id=donor_task_id, run_root=root, out=root / f"packet-work/{slug}/donor-{donor_slug}.json")
        focal_ids = sorted({atom for finding in _load_normalized_findings(real, expected_task_id=task_id, run_root=root) for atom in finding.atoms if isinstance(atom, IdentifierAtom)}, key=lambda atom: (atom.kind.value, atom.entity_id))
        donor_ids = sorted({atom for finding in _load_normalized_findings(donor, expected_task_id=donor_task_id, run_root=root) for atom in finding.atoms if isinstance(atom, IdentifierAtom)}, key=lambda atom: (atom.kind.value, atom.entity_id))
        by_kind: dict[object, list[IdentifierAtom]] = {}
        for atom in focal_ids:
            by_kind.setdefault(atom.kind, []).append(atom)
        mapping: dict[IdentifierAtom, IdentifierAtom] = {}
        for atom in donor_ids:
            choices = by_kind.get(atom.kind, [])
            if not choices:
                raise RecordValidationError("packet donor identifiers lack focal-safe aliases")
            mapping[atom] = choices.pop(0)
        rewrites = derive_packet_rewrite_artifacts(mapping, focal_task_id=task_id, donor_task_id=donor_task_id, normalized_real_ref=real, normalized_donor_ref=donor, run_root=root, identifier_map_out=root / f"packet-work/{slug}/identifier-map.json", normalized_sham_out=root / f"packet-work/{slug}/sham.json")
        real_path, sham_path = _opaque_guidance_paths(
            task_id, assignment_row, allocation_row
        )
        entries.append(build_packet_pair(run_root=root, normalized_real_ref=real, normalized_donor_ref=donor, normalized_sham_ref=rewrites.normalized_sham_ref, artifact_store=store, real_relative_path=real_path, sham_relative_path=sham_path, task_id=task_id, donor_task_id=donor_task_id, prefix_index_sha256=prefix_ref.sha256, focal_verifier_ref=focal_verifier, donor_verifier_ref=donor_verifier, assignment_ref=assignment_ref, identifier_map_ref=rewrites.identifier_map_ref, tokenizer_ref=tokenizer_ref, packet_template_ref=packet_template_ref, packet_policy_ref=packet_policy_ref, pad_unit_set_ref=pad_unit_set_ref))
    return write_packet_candidate(entries, assignment_ref=assignment_ref, prefix_index_ref=prefix_ref, tokenizer_ref=tokenizer_ref, packet_template_ref=packet_template_ref, packet_policy_ref=packet_policy_ref, pad_unit_set_ref=pad_unit_set_ref, run_root=root, out=out)


def _branch_program_refs(task_id: str) -> None:
    """Fail closed: no study manifest authorizes per-slot branch programs yet.

    ``run_opaque_slot`` needs one manifest-authorized branch execution program
    per slot, in the same way ``run_prefix`` needs its prefix program.  The
    committed study-manifest contract has no field that names them, so there is
    nothing to resolve and nothing a caller may substitute.  Inventing a
    program here would let the CLI script four slot trajectories outside frozen
    authority, which is exactly the fabrication this gate exists to prevent.
    """

    raise RecordValidationError(
        "no manifest-authorized branch execution program covers task "
        f"{task_id!r}; branch slot execution is not authorized"
    )


def _synthetic_branches(args: argparse.Namespace, root: Path) -> ArtifactRef | None:
    """Admit branch authority and materialize every task block it permits.

    Admission is real work, not a formality: each task's ancestry, sealed
    packet capabilities, frozen prefix snapshot, and preregistered slot order
    are resolved before anything is written.  An untriggered task closes
    completely here by copying ``Y_0`` to its four opaque slots.  A triggered
    task prepares its four opaque work orders and then stops at the one
    remaining authority gate, because no study manifest yet names the per-slot
    branch execution programs the isolated worker would replay.
    """

    study_ref = _ref(root, args.study, "study_manifest")
    schedule_ref = _ref(root, args.schedule, "resampling_prefix_schedule")
    assignment_ref = _ref(root, args.assignment, "resampling_assignment_ledger")
    prefix_index_ref = _ref(root, args.prefix_index, "resampling_prefix_receipt")
    packet_index_ref = _ref(root, args.packet_index, "packet_index_sealed")
    freeze_ref = _ref(root, args.analysis_freeze, "analysis_freeze")
    prefix_name = _relative_name(args.out_prefix, field="task block prefix")
    task_ids = _schedule_task_ids(schedule_ref, study_ref, root=root)
    study_id = _study_id(study_ref, root=root)
    # Admission is a whole-run barrier.  A partially materialized branch stage
    # is worse than none: it would leave a root whose task blocks silently
    # cover only the tasks that happened to be admissible.
    admitted: list[tuple[str, object, object, Path]] = []
    for task_id in task_ids:
        authority = load_prefix_execution_authority(
            run_root=root, schedule_ref=schedule_ref, task_id=task_id,
        )
        prefix = load_frozen_prefix_view(
            prefix_index_ref=prefix_index_ref, task_id=task_id, run_root=root,
        )
        slots = authority.task_schedule.slots.slots
        out = _out(root, f"{prefix_name}/{hashlib.sha256(task_id.encode('utf-8')).hexdigest()}.json")
        if prefix.trigger_reason is TriggerReason.NO_INTERVENTION_OPPORTUNITY:
            prepare_no_intervention_slots(
                prefix=prefix, slots=slots,
                packet_index_ref=packet_index_ref, run_root=root,
            )
        else:
            prepare_opaque_work_orders(
                study_id=study_id,
                benchmark=authority.task_schedule.task.benchmark,
                prefix=prefix, slots=slots, branch_caps=authority.branch_caps,
                packet_index_ref=packet_index_ref, analysis_freeze_ref=freeze_ref,
                run_root=root,
            )
            _branch_program_refs(task_id)
        admitted.append((task_id, authority, prefix, out))
    sealed: ArtifactRef | None = None
    for _task_id, authority, prefix, out in admitted:
        identities = prepare_no_intervention_slots(
            prefix=prefix, slots=authority.task_schedule.slots.slots,
            packet_index_ref=packet_index_ref, run_root=root,
        )
        sealed = seal_no_intervention_block(
            prefix=prefix, task_spec=authority.task_schedule.task,
            slots=identities, y0_grade=prefix.y0_grade,
            schedule_ref=schedule_ref, prefix_index_ref=prefix_index_ref,
            assignment_ref=assignment_ref, packet_index_ref=packet_index_ref,
            analysis_freeze_ref=freeze_ref, run_root=root, out=out,
        )
    return sealed


def _study_id(study_ref: ArtifactRef, *, root: Path) -> str:
    record = _record_for_ref(study_ref, root=root, kind="resampling_study_manifest")
    study_id = record.get("study_id")
    if type(study_id) is not str or not study_id:
        raise RecordValidationError("study manifest study_id is malformed")
    return study_id


def _require_resumable_selftest(root: Path, final_name: str) -> None:
    """Prove a staged root is power-complete before any descendant write."""
    documents = _scientific_documents(root, excluded=set())
    manifests = [
        path for path, document in documents.items()
        if document.value["record_kind"] == "resampling_study_manifest"
    ]
    if len(manifests) != 1:
        raise RecordValidationError("resume requires exactly one study manifest")
    manifest_name = manifests[0]
    final_ref = _ref(root, final_name, "power_report")
    manifest_ref = _ref(root, manifest_name, "study_manifest")
    require_schedulable_power_final(manifest_ref, final_ref, run_root=root)
    unexpected = [
        path for path, document in documents.items()
        if document.value["record_kind"] not in {
            "resampling_study_manifest", "resampling_power_report",
        }
    ]
    if unexpected:
        raise RecordValidationError(
            "resume requires no schedule or later scientific artifacts"
        )


def _selftest(args: argparse.Namespace, root: Path) -> ArtifactRef | None:
    if args.stop_after_study:
        if (root / "study-manifest.json").exists() or any(
            root.rglob("p0-core-receipt.json")
        ):
            raise RecordValidationError(
                "study-only selftest requires an empty scientific root"
            )
        documents = _scientific_documents(root, excluded=set())
        if documents:
            raise RecordValidationError(
                "study-only selftest requires an empty scientific root"
            )
        return seal_synthetic_selftest_study(root)
    if args.resume_after_power:
        _require_resumable_selftest(root, args.resume_after_power)
        raise RecordValidationError(
            "selftest descendants are not implemented in this CLI checkpoint"
        )
    raise RecordValidationError("selftest fixture bundle is not installed")


def _dispatch(args: argparse.Namespace, root: Path) -> ArtifactRef | None:
    if args.command == "selftest":
        return _selftest(args, root)
    if args.command == "study":
        if args.study_command == "validate":
            path, _ = resolve_inside(Path(args.study), root, require_exists=True)
            validate_record(load_json_bytes(path.read_bytes(), source=path)); return None
        values = vars(args)
        ref = seal_study_manifest(*[Path(values[n]) for n in ("study_source", "tasks_source", "roster_source", "assignment_program_source", "provider_lane_plan_source", "storage_policy_contract_source", "power_grid_source", "power_screen_topology_source", "tokenizer_source", "packet_template_source", "packet_policy_source", "pad_unit_set_source")], [Path(x) for x in args.revision_source], Path(args.required_kinds_source), eligibility_manifest_source=Path(args.eligibility_manifest_source) if args.eligibility_manifest_source else None, roster_ceremony_policy_source=Path(args.roster_ceremony_policy_source) if args.roster_ceremony_policy_source else None, run_root=root, out=_out(root, args.out)); return ref
    if args.command == "power":
        if args.power_command == "authority":
            manifest = _ref(root, args.study, "study_manifest")
            fn = seal_synthetic_power_authority if args.authority_kind == "synthetic" else seal_roster_bound_power_authority
            return fn(manifest, run_root=root, out=_out(root, args.out))
        config = _config(args, root)
        if args.power_command == "screen":
            trigger = _ref(root, args.fallback_trigger, "power_report") if args.fallback_trigger else None
            return screen_power_grid(config, phase=args.phase, generation=args.generation, shard_count=args.shard_count, fallback_trigger_ref=trigger, run_root=root, out=_out(root, args.out))
        if args.power_command == "simulate": return simulate_power_shard(_ref(root, args.screen, "power_report"), config, shard_index=args.shard_index, run_root=root, out=_out(root, args.out))
        if args.power_command == "select-validation": return select_validation_cells(_ref(root, args.screen, "power_report"), _shards(root, args.shard_prefix), config, run_root=root, out=_out(root, args.out))
        if args.power_command == "validate": return validate_gaussian_approximation(_ref(root, args.screen, "power_report"), _shards(root, args.shard_prefix), _ref(root, args.selection, "power_report"), config, run_root=root, out=_out(root, args.out))
        if args.power_command == "validate-fallback": return validate_full_multiplier_fallback(_ref(root, args.screen, "power_report"), _shards(root, args.shard_prefix), config, run_root=root, out=_out(root, args.out))
        selected = sum(bool(x) for x in (args.completed_gaussian, args.completed_full_multiplier, args.synthetic_validation_failed))
        if selected != 1: raise RecordValidationError("finalize requires exactly one closed finalization arm")
        if args.completed_gaussian:
            if not all((args.selected_screen, args.selected_shard_prefix, args.selected_selection, args.selected_validation)):
                raise RecordValidationError("Gaussian final requires all selected screen, shard, selection, and validation refs")
            return finalize_synthetic_power_report(_ref(root,args.selected_screen,"power_report"), _shards(root,args.selected_shard_prefix), _ref(root,args.selected_selection,"power_report"), _ref(root,args.selected_validation,"power_report"), config, run_root=root,out=_out(root,args.out))
        if args.completed_full_multiplier:
            if not all((args.selected_screen, args.selected_shard_prefix, args.fallback_validation)):
                raise RecordValidationError("full-multiplier final requires selected screen, shard, and fallback validation refs")
            return finalize_synthetic_full_multiplier_report(_ref(root,args.selected_screen,"power_report"), _shards(root,args.selected_shard_prefix), _ref(root,args.fallback_validation,"power_report"), config, run_root=root,out=_out(root,args.out))
        if args.synthetic_validation_failed:
            if not all((args.terminal_attempt, args.terminal_stage, args.reason)):
                raise RecordValidationError("synthetic failed final requires terminal attempt, stage, and closed reason")
            authority = _ref(root, args.authority, "power_authority")
            attempts = []
            for path in sorted(root.rglob("*.json")):
                try:
                    record = load_json_bytes(path.read_bytes(), source=path)
                    payload = record.get("payload") if isinstance(record, dict) else None
                    if isinstance(payload, dict) and record.get("record_kind") == "resampling_power_report" and payload.get("authority_ref") == {"role": authority.role, "relative_path": authority.relative_path, "sha256": authority.sha256, "byte_count": authority.byte_count, "media_type": authority.media_type}:
                        attempts.append(_ref(root, path.relative_to(root).as_posix(), "power_report"))
                except RecordValidationError:
                    continue
            return finalize_synthetic_validation_failed(tuple(attempts), _ref(root,args.terminal_attempt,"power_report"), terminal_stage=args.terminal_stage, reason=args.reason, config=config, run_root=root,out=_out(root,args.out))
        raise RecordValidationError("synthetic CLI cannot finalize a roster-bound multiplier selection")
    if args.command == "schedule":
        manifest_ref = _ref(root, args.study, "study_manifest")
        final_ref = _ref(root, args.power_final, "power_report")
        # Validate the entire final chain before allocating an output or a lease.
        require_schedulable_power_final(manifest_ref, final_ref, run_root=root)
        seed_path = _external_file(args.schedule_seed_file, root=root, field="schedule seed file")
        seed = _schedule_seed(seed_path)
        out = _out(root, args.out)
        lease = claim_local_test_storage(transaction="prefix", run_root=root, manifest_ref=manifest_ref, schedule_ref=None)
        return seal_prefix_schedule(manifest_ref, final_ref, schedule_seed_reveal=seed,
                                    storage_policy_lease=lease, run_root=root, out=out)
    if args.command == "synthetic":
        if args.synthetic_command == "branches":
            return _synthetic_branches(args, root)
        study_ref = _ref(root, args.study, "study_manifest")
        schedule_ref = _ref(root, args.schedule, "resampling_prefix_schedule")
        task_ids = _schedule_task_ids(schedule_ref, study_ref, root=root)
        out = _out(root, args.out)
        candidates = tuple(run_prefix(run_root=root, schedule_ref=schedule_ref, task_id=task_id) for task_id in task_ids)
        return seal_prefix_index(run_root=root, schedule_ref=schedule_ref, candidate_refs=candidates,
                                 out=out)
    if args.command == "assignment":
        schedule_ref = _ref(root, args.schedule, "resampling_prefix_schedule")
        prefix_ref = _ref(root, args.prefix_index, "resampling_prefix_receipt")
        authority = load_assignment_authority(schedule_ref, prefix_ref, run_root=root)
        secret_path = _external_file(args.assignment_key_file, root=root, field="assignment key file")
        out = _out(root, args.out)
        store = AssignmentSecretStore(secret_path)
        try:
            handle = store.claim_assignment(authority.manifest_ref, schedule_ref, run_root=root)
            lease = claim_local_test_storage(transaction="assignment", run_root=root,
                                             manifest_ref=authority.manifest_ref, schedule_ref=schedule_ref)
            return seal_branch_assignment(schedule_ref, prefix_ref, assignment_secret_handle=handle,
                                          matching_backend_session=None, storage_policy_lease=lease,
                                          run_root=root, out=out)
        finally:
            store.close()
    if args.command == "packets":
        study_ref = _ref(root, args.study, "study_manifest")
        assignment_ref = _ref(root, args.assignment, "resampling_assignment_ledger")
        prefix_ref = _ref(root, args.prefix_index, "resampling_prefix_receipt")
        tokenizer_ref, template_ref, policy_ref, pads_ref = _packet_manifest_parents(
            study_ref, assignment_ref, prefix_ref, root=root,
        )
        if args.packets_command == "build":
            # Reserve the candidate name before Task-5 can write packet-work
            # derivatives.  Keep this separate from the call for reviewable
            # no-side-effect ordering.
            candidate_out = _out(root, args.out_candidate)
            return _build_packet_candidate(
                study_ref=study_ref, assignment_ref=assignment_ref, prefix_ref=prefix_ref,
                tokenizer_ref=tokenizer_ref, packet_template_ref=template_ref,
                packet_policy_ref=policy_ref, pad_unit_set_ref=pads_ref, root=root,
                out=candidate_out,
            )
        candidate_ref = _ref(root, args.candidate, "packet_index_candidate")
        schedule_ref = _ref(root, args.schedule, "resampling_prefix_schedule")
        task_ids = _schedule_task_ids(schedule_ref, study_ref, root=root)
        return audit_and_seal_packet_index(
            candidate_ref, expected_task_ids=task_ids, assignment_ref=assignment_ref,
            schedule_ref=schedule_ref, prefix_index_ref=prefix_ref,
            tokenizer_ref=tokenizer_ref, packet_template_ref=template_ref,
            packet_policy_ref=policy_ref, pad_unit_set_ref=pads_ref, run_root=root,
            out=_out(root, args.out_index),
        )
    if args.command == "analysis":
        sources = _external_sources(args.source_root, args.source, root=root)
        config = _external_file(args.config, root=root, field="analysis config")
        schema = _external_file(args.projection_schema, root=root, field="projection schema")
        packet_ref = _ref(root, args.packet_index, "packet_index_sealed")
        packet = _record_for_ref(packet_ref, root=root, kind="resampling_packet_index")
        if _payload(packet, field="packet index").get("stage") != "sealed":
            raise RecordValidationError("analysis freeze requires a sealed packet index")
        # Read manifest identity only through sealed packet ancestry.
        packet_payload = _payload(packet, field="packet index")
        assignment_ref = _artifact_ref(packet_payload.get("assignment_ref"), field="packet assignment_ref")
        assignment = _record_for_ref(assignment_ref, root=root, kind="resampling_assignment_ledger")
        manifest_ref = _artifact_ref(_payload(assignment, field="assignment").get("manifest_ref"), field="assignment manifest_ref")
        manifest = _record_for_ref(manifest_ref, root=root, kind="resampling_study_manifest")
        provenance = manifest.get("provenance")
        if not isinstance(provenance, dict):
            raise RecordValidationError("manifest provenance is malformed")
        return freeze_analysis(run_root=root, destination=_out(root, args.out), study_id=str(manifest["study_id"]),
                               frozen_created_at=str(manifest["frozen_created_at"]), provenance=provenance,
                               source_paths=sources, config_path=config, projection_schema_path=schema,
                               packet_index_ref=packet_ref)
    if args.command == "project":
        schedule_ref = _ref(root, args.schedule, "resampling_prefix_schedule")
        freeze_ref = _ref(root, args.analysis_freeze, "analysis_freeze")
        # Reserve before candidate work: an existing destination must not run a
        # controller subprocess or touch an opaque outcome view.
        out = _out(root, args.out)
        schedule = _record_for_ref(schedule_ref, root=root, kind="resampling_prefix_schedule")
        blocks = _task_block_refs(root, args.task_block_prefix)
        frozen: list[dict[str, object]] = []
        outcomes: dict[str, object] = {}
        refs_by_task: dict[str, ArtifactRef] = {}
        for entry in _payload(schedule, field="schedule").get("tasks", []):
            if not isinstance(entry, dict) or not isinstance(entry.get("task"), dict) or not isinstance(entry.get("slots"), list):
                raise RecordValidationError("schedule task is malformed")
            task_id = entry["task"].get("task_id")
            if not isinstance(task_id, str):
                raise RecordValidationError("schedule task id is malformed")
            frozen.append({"task_id": task_id, "prefix_success": None,
                           "slot_ids": [slot.get("slot_id") for slot in entry["slots"] if isinstance(slot, dict)]})
        for ref in blocks:
            block = _record_for_ref(ref, root=root, kind="resampling_task_block")
            payload = _payload(block, field="task block")
            task_id = payload.get("task_id")
            if not isinstance(task_id, str) or task_id in outcomes:
                raise RecordValidationError("task blocks have duplicate task coverage")
            outcomes[task_id] = payload.get("slot_outcomes")
            refs_by_task[task_id] = ref
            for row in frozen:
                if row["task_id"] == task_id:
                    row["prefix_success"] = payload.get("prefix_success")
                    break
        if any(row["prefix_success"] not in (0, 1) for row in frozen):
            raise RecordValidationError("task blocks must exactly cover the schedule")
        ordered_blocks = tuple(refs_by_task[row["task_id"]] for row in frozen)
        candidate = _candidate_subprocess(frozen, outcomes)
        return seal_blinded_projection(run_root=root, destination=out, schedule_ref=schedule_ref,
                                       analysis_freeze_ref=freeze_ref, task_block_refs=ordered_blocks, candidate=candidate)
    if args.command == "analyze":
        study_ref = _ref(root, args.study, "study_manifest")
        projection_ref = _ref(root, args.projection, "blinded_projection")
        ledger_ref = _ref(root, args.assignment, "resampling_assignment_ledger")
        freeze_ref = _ref(root, args.analysis_freeze, "analysis_freeze")
        packet_ref = _ref(root, args.packet_index, "packet_index_sealed")
        projection = _record_for_ref(projection_ref, root=root, kind="resampling_blinded_projection")
        projection_payload = _payload(projection, field="projection")
        if projection_payload.get("analysis_freeze_ref") != _mapping_ref(freeze_ref):
            raise RecordValidationError("projection differs from supplied analysis freeze")
        schedule_ref = _artifact_ref(projection_payload.get("schedule_ref"), field="projection schedule_ref")
        schedule = _record_for_ref(schedule_ref, root=root, kind="resampling_prefix_schedule")
        schedule_payload = _payload(schedule, field="schedule")
        if schedule_payload.get("manifest_ref") != _mapping_ref(study_ref):
            raise RecordValidationError("projection schedule differs from supplied study")
        # The packet index is public and sealed before the freeze.  It binds
        # the opaque ledger bytes to the public prefix without parsing the
        # clear slot map; that parse is exclusive to the paired unblind stage.
        packet = _record_for_ref(packet_ref, root=root, kind="resampling_packet_index")
        packet_payload = _payload(packet, field="packet index")
        if packet_payload.get("stage") != "sealed":
            raise RecordValidationError("analysis requires a sealed packet index")
        if packet_payload.get("assignment_ref") != _mapping_ref(ledger_ref):
            raise RecordValidationError("packet index differs from supplied assignment ledger")
        prefix_ref = _artifact_ref(packet_payload.get("prefix_index_ref"), field="packet prefix_index_ref")
        power_final_ref = _artifact_ref(schedule_payload.get("power_final_ref"), field="schedule power_final_ref")
        sources = _external_sources(args.source_root, args.source, root=root)
        config_path = _external_file(args.config, root=root, field="analysis config")
        schema_path = _external_file(args.projection_schema, root=root, field="projection schema")
        config = _analysis_config(config_path)
        current = CurrentAnalysisInputs(sources, config_path, schema_path, packet_ref)
        receipt_out = _out(root, args.unblind_receipt)
        analysis_out = _out(root, args.out)
        secret_path = _external_file(args.assignment_key_file, root=root, field="assignment key file")
        expected = projection_payload.get("expected_task_count")
        if type(expected) is not int or expected < 1:
            raise RecordValidationError("projection expected task count is malformed")
        freeze = _record_for_ref(freeze_ref, root=root, kind="resampling_analysis_freeze")
        config_ref = _artifact_ref(_payload(freeze, field="analysis freeze").get("config_ref"), field="analysis freeze config_ref")
        manifest = _record_for_ref(study_ref, root=root, kind="resampling_study_manifest")

        def build_analysis(unblinded: object) -> dict[str, object]:
            # The staged unblind result carries only in-memory rows and the
            # deterministic future receipt ref; no artifact has been written.
            rows = _analysis_rows(unblinded.rows)  # type: ignore[union-attr]
            result = analyze_rows(rows, config, manifest_ref=study_ref,
                                  power_final_ref=power_final_ref, run_root=root)
            return {
                "record_kind": "resampling_analysis", "schema_version": "0.2.0",
                "study_id": manifest["study_id"], "frozen_created_at": manifest["frozen_created_at"],
                "provenance": manifest["provenance"],
                "payload": {
                    "analysis_freeze_ref": _mapping_ref(freeze_ref),
                    "projection_ref": _mapping_ref(projection_ref),
                    "unblind_receipt_ref": _mapping_ref(unblinded.receipt_ref),  # type: ignore[union-attr]
                    "config_ref": _mapping_ref(config_ref), "row_count": len(rows),
                    "result": analysis_result_payload(result),
                    "numeric_receipt": {"finite": True},
                },
            }

        store = AssignmentSecretStore(secret_path)
        try:
            permit = issue_unblind_permit(
                store.claim_unblind(study_ref, schedule_ref, run_root=root), run_root=root,
                manifest_ref=study_ref, schedule_ref=schedule_ref, prefix_index_ref=prefix_ref,
                ledger_ref=ledger_ref, projection_ref=projection_ref, freeze_ref=freeze_ref,
                expected_task_count=expected,
            )
            paired = unblind_and_publish_analysis(
                store.claim_unblind(study_ref, schedule_ref, run_root=root),
                recovery_handle=store.claim_unblind(study_ref, schedule_ref, run_root=root),
                permit_hmac_sha256=permit,
                run_root=root, receipt_destination=receipt_out, manifest_ref=study_ref,
                schedule_ref=schedule_ref, prefix_index_ref=prefix_ref, ledger_ref=ledger_ref,
                projection_ref=projection_ref, freeze_ref=freeze_ref, expected_task_count=expected,
                current_analysis_inputs=current,
                analysis_destination=analysis_out, analysis_builder=build_analysis,
            )
        finally:
            store.close()
        return paired.analysis_ref
    if args.command == "artifacts":
        required_path = Path(args.required_kinds).resolve(strict=True)
        required = load_json_bytes(required_path.read_bytes(), source=required_path)
        if not isinstance(required, list):
            raise RecordValidationError("required-kinds source must be a JSON array")
        if args.artifact_command == "seal":
            manifests = [p for p in root.rglob("*.json") if p.name == "study-manifest.json"]
            if len(manifests) != 1:
                raise RecordValidationError("artifact sealing requires exactly one study manifest")
            manifest = load_json_bytes(manifests[0].read_bytes(), source=manifests[0])
            if not isinstance(manifest, dict):
                raise RecordValidationError("study manifest is not a JSON object")
            return seal_artifact_root(root, required, _out(root,args.out), study_id=manifest["study_id"], frozen_created_at=manifest["frozen_created_at"], provenance=manifest["provenance"])
        receipt, _ = resolve_inside(Path(_relative_name(args.receipt, field="receipt")), root, require_exists=True)
        verify_artifact_root(receipt, root, required_document_kinds=required); return None
    documents = list(root.rglob("*.json")); _emit(status="ok", documents=len(documents)); return None


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    debug = "--debug" in (argv if argv is not None else __import__("sys").argv[1:])
    try:
        args = parser.parse_args(argv)
        if (
            args.command == "selftest"
            and args.stop_after_study
            and args.defer_artifact_root
        ):
            parser.error("--stop-after-study cannot defer an absent artifact root")
        root = run_root(Path(args.run_root))
        result = _dispatch(args, root)
        if result is not None: _emit(result)
        elif args.command != "status": _emit(status="validated")
        return 0
    except SystemExit as exc:
        if exc.code == 0: raise
        _emit(status="error", error="invalid command arguments",
              **({"debug": "argument parsing failed"} if debug else {}))
        return 2
    except _ArgumentError:
        _emit(status="error", error="invalid command arguments",
              **({"debug": "argument parsing failed"} if debug else {}))
        return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecordValidationError) as exc:
        _emit(status="error", error=str(exc).replace("\n", " "))
        return 2
