"""Fail-closed, zero-spend command line for the resampling-null controller.

This is intentionally a thin adapter: scientific choices stay in sealed records,
and every path accepted after study sealing is a run-root-relative POSIX path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

from .artifacts import seal_artifact_root, seal_study_manifest, verify_artifact_root, validate_record
from .errors import RecordValidationError
from .json_io import load_json_bytes, resolve_inside, run_root
from .power import (finalize_synthetic_full_multiplier_report, finalize_synthetic_power_report, finalize_synthetic_validation_failed,
                    load_power_config, seal_roster_bound_power_authority,
                    seal_synthetic_power_authority, screen_power_grid,
                    select_validation_cells, simulate_power_shard,
                    validate_gaussian_approximation, validate_full_multiplier_fallback)
from .types import ArtifactRef


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
                       media_type="application/json")


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


def _emit(ref: ArtifactRef | None = None, *, status: str = "ok", **extra: object) -> None:
    payload: dict[str, object] = {"status": status, **extra}
    if ref is not None:
        payload.update({"digest": ref.sha256, "output": ref.relative_path})
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pneuma_lab.resampling_null", add_help=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--debug", action="store_true")
    top = parser.add_subparsers(dest="command", required=True)
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
    artifacts = top.add_parser("artifacts").add_subparsers(dest="artifact_command", required=True)
    for name in ("seal", "verify"):
        p = artifacts.add_parser(name); p.add_argument("--required-kinds", required=True); p.add_argument("--out" if name == "seal" else "--receipt", required=True)
    status = top.add_parser("status"); status.add_argument("--study")
    return parser


def _config(args: argparse.Namespace, root: Path):
    return load_power_config(_ref(root, args.authority, "power_authority"), _ref(root, args.grid_ref, "power_grid"), _ref(root, args.screen_topology_ref, "power_screen_topology"), run_root=root)


def _dispatch(args: argparse.Namespace, root: Path) -> ArtifactRef | None:
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
    try:
        args = parser.parse_args(argv)
        root = run_root(Path(args.run_root))
        result = _dispatch(args, root)
        if result is not None: _emit(result)
        elif args.command != "status": _emit(status="validated")
        return 0
    except SystemExit as exc:
        if exc.code == 0: raise
        _emit(status="error", error="invalid command arguments")
        return 2
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecordValidationError) as exc:
        _emit(status="error", error=str(exc).replace("\n", " "))
        return 2
