"""Complete foundation CLI with strict command separation.

Every command dispatches through an injectable :class:`CommandHandlers`
boundary, so orchestration is testable without touching torch, the network,
or the protected corpus. ``default_handlers()`` imports every heavy module
lazily inside its handler, which keeps ``doctor``, ``duration``,
``setup-plan``, and ``--help`` usable on a torch-less interpreter.

Command separation invariants:

- ``prepare`` and ``dry-run`` never share a call path with ``train`` or
  ``resume``; a preparation or rehearsal command can never fall through into
  gradient work.
- ``preflight`` calls only ``preflight_foundation_run()`` and allocates
  nothing.
- Handler failures exit with status 2 and a ``BLOCKED:`` line on stderr.
  ``main`` catches ``ValueError``, ``RuntimeError``, ``OSError``, and
  ``ModelCacheError`` — the last is a bare ``Exception`` that can surface
  from any code path that consults the pinned cache, including deep inside
  ``run_no_gradient_dry_run`` and the runner preflight, so it is caught
  centrally rather than translated per call site. ``DryRunError`` is
  translated to ``RuntimeError`` inside its handler because importing
  ``dry_run`` requires the torch extra. Unexpected exception types
  propagate. A missing optional foundation dependency surfaces as
  ``BLOCKED`` through ``_lazy_import``, not as a traceback.

Documented CLI contracts:

- ``download-model --dry-run`` performs an offline verification of the
  already-cached pinned snapshot (``verify_pinned_snapshot``); it never
  touches the network and fails closed when the cache is absent.
- ``dry-run --dry-run`` verifies the pinned snapshot offline and reports the
  planned request without allocating a model.
- ``evaluate --run`` consumes ``<run>/manifest.json`` plus
  ``<run>/validation_batches.json`` (a JSON array of per-batch mappings with
  ``token_count`` and ``validation_loss``). The runner manifest records only
  aggregate best/last validation losses, so evaluation fails closed until the
  per-batch artifact exists; it never fabricates batch weights.
- The cloud handlers import ``pneuma_lab.foundation.cloud_bundle`` lazily
  (Task 14). Until that module lands, both commands fail closed with
  ``BLOCKED``. The CLI boundary passes primitives:
  ``build_cloud_reproduction_candidate(local_authorization_path, *,
  local_gate_report_path, quoted_hourly_usd, quoted_tax_inclusive_usd,
  output_path, repo_root)`` and ``build_cloud_bundle_for_cli(*, stage,
  authorization_path, quoted_hourly_usd, quoted_tax_inclusive_usd,
  output_path, repo_root, dry_run)``.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import json
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pneuma_lab.foundation.doctor import doctor_report, duration_hours, live_probe

# model_cache and its whole import chain (artifacts, snapshot_receipt, specs)
# are stdlib-only, so this import keeps the torch-less `--help` path intact.
from pneuma_lab.foundation.model_cache import ModelCacheError


STAGES = ("100k", "500k", "2m", "8m", "16m", "32m")
LEARNING_RATES = (5e-5, 1e-4, 2e-4)
DEFAULT_SEED = 20260713
_REGISTRY_RELATIVE = Path("docs/data/training-readiness/dataset-registry.json")
_SUITE_RELATIVE = Path("docs/data/training-readiness/pneuma-foundation-v0-suite.json")
_CLOUD_ONLY_ARGUMENTS = (
    ("local_authorization", "--local-authorization"),
    ("local_gate_report", "--local-gate-report"),
    ("quoted_hourly_usd", "--quoted-hourly-usd"),
    ("quoted_tax_inclusive_usd", "--quoted-tax-inclusive-usd"),
)


@dataclass(frozen=True)
class CommandHandlers:
    """Injectable one-handler-per-command dispatch boundary."""

    doctor: Callable
    setup_plan: Callable
    prepare: Callable
    preflight: Callable
    download_model: Callable
    dry_run: Callable
    authorization_candidate: Callable
    authorization_finalize: Callable
    train: Callable
    resume: Callable
    evaluate: Callable
    report: Callable
    cloud_bundle: Callable


def _add_json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", dest="as_json")


def _add_profile(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", choices=("local", "cloud"), default="local")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pneuma_lab.foundation",
        description="Local-first foundation training operations.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="check WSL2 local readiness")
    _add_json_flag(doctor)
    _add_profile(doctor)

    duration = subparsers.add_parser(
        "duration", help="estimate hours from measured tps"
    )
    duration.add_argument("--tokens", type=int, required=True)
    duration.add_argument("--tps", type=float, required=True)

    setup_plan = subparsers.add_parser(
        "setup-plan", help="print the inert WSL2 bootstrap sequence"
    )
    _add_json_flag(setup_plan)

    prepare = subparsers.add_parser(
        "prepare", help="deterministic zero-weight stage preparation"
    )
    prepare.add_argument("--stage", choices=STAGES, required=True)
    prepare.add_argument("--data-root", required=True)
    prepare.add_argument("--cache-root")
    prepare.add_argument("--dry-run", action="store_true")
    _add_json_flag(prepare)

    preflight = subparsers.add_parser(
        "preflight", help="run every fail-closed gate without allocating"
    )
    preflight.add_argument("--stage", choices=STAGES, required=True)
    preflight.add_argument("--authorization", required=True)
    preflight.add_argument("--lr", type=float, choices=LEARNING_RATES, required=True)
    _add_profile(preflight)
    _add_json_flag(preflight)

    download_model = subparsers.add_parser(
        "download-model", help="materialize and receipt the pinned snapshot"
    )
    download_model.add_argument("--model", choices=("2b",), required=True)
    download_model.add_argument("--cache-root")
    download_model.add_argument("--dry-run", action="store_true")
    _add_json_flag(download_model)

    dry_run = subparsers.add_parser("dry-run", help="no-gradient launch-gate rehearsal")
    dry_run.add_argument("--stage", choices=("100k",), required=True)
    dry_run.add_argument("--cache-root")
    dry_run.add_argument("--dry-run", action="store_true")
    _add_json_flag(dry_run)

    candidate = subparsers.add_parser(
        "authorization-candidate",
        help="print or build a nonauthorizing candidate scope",
    )
    candidate.add_argument("--stage", choices=STAGES, required=True)
    _add_profile(candidate)
    candidate.add_argument("--local-authorization")
    candidate.add_argument("--local-gate-report")
    candidate.add_argument("--quoted-hourly-usd", type=float)
    candidate.add_argument("--quoted-tax-inclusive-usd", type=float)
    _add_json_flag(candidate)

    finalize = subparsers.add_parser(
        "authorization-finalize",
        help="convert an unchanged candidate into a final authorization",
    )
    finalize.add_argument("--candidate", required=True)
    finalize.add_argument("--scope-digest", required=True)
    finalize.add_argument("--approval-phrase", required=True)
    finalize.add_argument("--operator-id", required=True)

    train = subparsers.add_parser("train", help="run one authorized training stage")
    train.add_argument("--stage", choices=STAGES, required=True)
    train.add_argument("--authorization", required=True)
    train.add_argument("--lr", type=float, choices=LEARNING_RATES, required=True)
    _add_profile(train)

    resume = subparsers.add_parser(
        "resume", help="resume exactly from a safe-boundary checkpoint"
    )
    resume.add_argument("--authorization", required=True)
    resume.add_argument("--checkpoint", required=True)
    _add_profile(resume)

    evaluate = subparsers.add_parser(
        "evaluate", help="evaluate one completed run into a claim-bounded report"
    )
    evaluate.add_argument("--run", required=True)
    evaluate.add_argument("--variant-results", action="append")

    report = subparsers.add_parser(
        "report", help="materialize the fixed-section reports for one run"
    )
    report.add_argument("--run", required=True)

    cloud_bundle = subparsers.add_parser(
        "cloud-bundle", help="authorized-only portable reproduction bundle"
    )
    cloud_bundle.add_argument("--stage", choices=("2m", "8m"), required=True)
    cloud_bundle.add_argument("--authorization", required=True)
    cloud_bundle.add_argument("--quoted-hourly-usd", type=float, required=True)
    cloud_bundle.add_argument("--quoted-tax-inclusive-usd", type=float, required=True)
    cloud_bundle.add_argument("--dry-run", action="store_true")

    return parser


# Public alias for external consumers (for example the operator-guide drift
# checker); the private name stays for the existing test surface.
build_parser = _parser


def _json_safe(value):
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def render_command_result(
    result,
    *,
    as_json: bool = False,
    command: str | None = None,
) -> None:
    """Print one command result; ``None`` renders nothing.

    The READY/BLOCKED human rendering is keyed on the ``doctor`` command,
    never duck-typed from result keys, so other commands whose payloads
    happen to carry ``ready``/``blockers`` members still render as JSON.
    """

    if result is None:
        return
    payload = _json_safe(result)
    if as_json:
        print(json.dumps(payload, default=str, indent=4, sort_keys=True))
        return
    if command == "doctor" and isinstance(payload, Mapping):
        print("READY" if payload.get("ready") else "BLOCKED")
        for blocker in payload.get("blockers") or ():
            print(f"- {blocker}")
        return
    if isinstance(payload, Mapping):
        print(json.dumps(payload, default=str, indent=4, sort_keys=True))
        return
    print(payload)


def _validate_arguments(args: argparse.Namespace) -> None:
    if getattr(args, "command", None) != "authorization-candidate":
        return
    missing = [
        flag for name, flag in _CLOUD_ONLY_ARGUMENTS if getattr(args, name) is None
    ]
    if args.profile == "cloud" and missing:
        raise ValueError(
            "authorization-candidate --profile cloud requires " + " ".join(missing)
        )
    if args.profile == "local" and len(missing) != len(_CLOUD_ONLY_ARGUMENTS):
        raise ValueError(
            "cloud-only arguments require --profile cloud: "
            + " ".join(
                flag
                for name, flag in _CLOUD_ONLY_ARGUMENTS
                if getattr(args, name) is not None
            )
        )


def main(
    argv: Sequence[str] | None = None,
    *,
    handlers: CommandHandlers | None = None,
) -> int:
    args = _parser().parse_args(argv)
    handlers = handlers or default_handlers()
    if args.command == "duration":
        hours = duration_hours(args.tokens, args.tps)
        print(f"{args.tokens} tokens at {args.tps:g} tokens/s: {hours:.2f} hours")
        return 0
    handler = getattr(handlers, args.command.replace("-", "_"))
    try:
        _validate_arguments(args)
        result = handler(args)
    except (ValueError, RuntimeError, OSError, ModelCacheError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    render_command_result(
        result,
        as_json=getattr(args, "as_json", False),
        command=args.command,
    )
    if args.command == "doctor":
        return 0 if isinstance(result, Mapping) and result.get("ready") is True else 1
    return 0


def derive_final_authorization_path(candidate_path: Path) -> Path:
    """Derive ``final/<name>`` from ``candidates/<name>`` without overwrite.

    Local candidates (``<stage>.json``) finalize to ``final/<stage>.json``;
    cloud candidates (``<stage>-cloud.json``) finalize to
    ``final/<stage>-cloud.json``. The result is always a different path from
    the input candidate, so finalization can never overwrite it.
    """

    candidate = Path(candidate_path)
    if candidate.suffix != ".json":
        raise ValueError("authorization candidate must be a JSON file")
    if candidate.parent.name != "candidates":
        raise ValueError("authorization candidate must live in a candidates directory")
    output = candidate.parent.parent / "final" / candidate.name
    if output == candidate:
        raise ValueError("final authorization path must differ from the candidate")
    return output


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _cache_root(args: argparse.Namespace, repo_root: Path) -> Path:
    raw = getattr(args, "cache_root", None)
    if raw:
        return Path(raw)
    return repo_root / "build" / "foundation" / "cache"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lazy_import(name: str):
    """Import one foundation module at handler time, failing closed.

    A module whose import chain requires the optional foundation extras
    surfaces as a ``BLOCKED`` exit instead of an ImportError traceback.
    """

    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise RuntimeError(
            f"{name} requires the foundation environment: {exc}"
        ) from exc


def _finalize_authorization(
    candidate_path: Path,
    supplied_scope_digest: str,
    supplied_approval_phrase: str,
    operator_id: str,
    approved_at: str,
    output_path: Path,
) -> Path:
    """Patchable seam over ``authorization.finalize_authorization``."""

    authorization = _lazy_import("pneuma_lab.foundation.authorization")
    return authorization.finalize_authorization(
        candidate_path,
        supplied_scope_digest,
        supplied_approval_phrase,
        operator_id,
        approved_at,
        output_path,
    )


def _load_json_value(path: Path, *, label: str, hint: str | None = None):
    suffix = f" ({hint})" if hint else ""
    try:
        payload = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"{label} cannot be read: {path}{suffix}") from exc
    try:
        return json.loads(payload)
    except ValueError as exc:
        raise ValueError(f"{label} is not valid JSON: {path}") from exc


def _load_json_object(path: Path, *, label: str, hint: str | None = None) -> dict:
    value = _load_json_value(path, label=label, hint=hint)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def _run_doctor(args: argparse.Namespace) -> dict:
    return doctor_report(live_probe(), profile=args.profile)


def _run_setup_plan(args: argparse.Namespace) -> dict:
    environment = _lazy_import("pneuma_lab.foundation.environment")
    return environment.setup_plan(_repo_root())


def _run_prepare(args: argparse.Namespace) -> dict:
    model_cache = _lazy_import("pneuma_lab.foundation.model_cache")
    preparation = _lazy_import("pneuma_lab.foundation.preparation")

    repo_root = _repo_root()
    tokenizer_snapshot = model_cache.pinned_snapshot_path(
        "2b", cache_root=_cache_root(args, repo_root)
    )
    request = preparation.PreparationRequest(
        stage=args.stage,
        repo_root=repo_root,
        data_root=Path(args.data_root),
        tokenizer_snapshot=tokenizer_snapshot,
        output_root=repo_root / "build" / "foundation" / "preparation" / args.stage,
        seed=DEFAULT_SEED,
        dry_run=bool(args.dry_run),
    )
    result = preparation.prepare_stage(request)
    payload = _json_safe(result)
    payload["stage"] = args.stage
    payload["dry_run"] = bool(args.dry_run)
    return payload


def _foundation_run_request(
    args: argparse.Namespace,
    *,
    stage: str,
    learning_rate: float,
    checkpoint_path: Path | None = None,
):
    runner = _lazy_import("pneuma_lab.foundation.runner")
    repo_root = _repo_root()
    return runner.FoundationRunRequest(
        repo_root=repo_root,
        authorization_path=Path(args.authorization),
        registry_path=repo_root / _REGISTRY_RELATIVE,
        suite_path=repo_root / _SUITE_RELATIVE,
        cache_root=repo_root / "build" / "foundation" / "cache",
        run_root=repo_root / "build" / "foundation" / "runs",
        stage=stage,
        learning_rate=learning_rate,
        execution_profile=args.profile,
        seed=DEFAULT_SEED,
        checkpoint_path=checkpoint_path,
    )


def _run_preflight(args: argparse.Namespace) -> dict:
    runner = _lazy_import("pneuma_lab.foundation.runner")
    preflight = runner.preflight_foundation_run(
        _foundation_run_request(args, stage=args.stage, learning_rate=args.lr)
    )
    return {
        "ready": bool(preflight.ready),
        "stage": args.stage,
        "learning_rate": args.lr,
        "execution_profile": args.profile,
        "model_key": preflight.authorization.model_key,
        "token_ceiling": preflight.authorization.token_ceiling,
        "scope_digest": preflight.authorization.scope_digest,
        "snapshot_path": str(preflight.cache.snapshot_path),
        "environment_ready": bool(preflight.environment["ready"]),
    }


def _run_download_model(args: argparse.Namespace) -> dict:
    model_cache = _lazy_import("pneuma_lab.foundation.model_cache")
    cache_root = _cache_root(args, _repo_root())
    if args.dry_run:
        cached = model_cache.verify_pinned_snapshot(args.model, cache_root=cache_root)
    else:
        cached = model_cache.prepare_pinned_snapshot(args.model, cache_root=cache_root)
    return {
        "model_key": cached.model_key,
        "revision": cached.revision,
        "snapshot_path": str(cached.snapshot_path),
        "receipt_path": str(cached.receipt_path),
        "verified_only": bool(args.dry_run),
    }


def _run_dry_run(args: argparse.Namespace) -> dict:
    repo_root = _repo_root()
    cache_root = _cache_root(args, repo_root)
    output_root = repo_root / "build" / "foundation" / "dry-run" / args.stage
    if args.dry_run:
        model_cache = _lazy_import("pneuma_lab.foundation.model_cache")
        cached = model_cache.verify_pinned_snapshot("2b", cache_root=cache_root)
        return {
            "planned_only": True,
            "model_key": "2b",
            "stage": args.stage,
            "snapshot_path": str(cached.snapshot_path),
            # Pairs with dry_run._REPORT_NAME; duplicated deliberately so the
            # planned path stays reportable on a torch-less interpreter.
            "report_path": str(output_root / "dry-run-report.json"),
        }
    dry_run = _lazy_import("pneuma_lab.foundation.dry_run")
    request = dry_run.DryRunRequest(
        model_key="2b",
        cache_root=cache_root,
        output_root=output_root,
        stage=args.stage,
    )
    try:
        return dry_run.run_no_gradient_dry_run(request)
    except dry_run.DryRunError as exc:
        raise RuntimeError(str(exc)) from exc


def _import_cloud_bundle():
    try:
        from pneuma_lab.foundation import cloud_bundle
    except ImportError as exc:
        raise RuntimeError(
            "cloud bundle support is unavailable: "
            "pneuma_lab.foundation.cloud_bundle is not implemented yet"
        ) from exc
    return cloud_bundle


def _cloud_entry_point(module, name: str) -> Callable:
    entry_point = getattr(module, name, None)
    if not callable(entry_point):
        raise RuntimeError(
            f"cloud bundle module does not expose the CLI entry point {name!r}"
        )
    return entry_point


def _run_authorization_candidate(args: argparse.Namespace) -> dict:
    repo_root = _repo_root()
    candidates_root = (
        repo_root / "build" / "foundation" / "authorizations" / "candidates"
    )
    if args.profile == "cloud":
        module = _import_cloud_bundle()
        build_candidate = _cloud_entry_point(
            module, "build_cloud_reproduction_candidate"
        )
        output_path = candidates_root / f"{args.stage}-cloud.json"
        candidate = build_candidate(
            Path(args.local_authorization),
            local_gate_report_path=Path(args.local_gate_report),
            quoted_hourly_usd=float(args.quoted_hourly_usd),
            quoted_tax_inclusive_usd=float(args.quoted_tax_inclusive_usd),
            output_path=output_path,
            repo_root=repo_root,
        )
        return {
            "candidate_path": str(output_path),
            "stage": args.stage,
            "execution_profile": "cloud",
            "scope_digest": candidate.get("scope_digest")
            if isinstance(candidate, Mapping)
            else None,
        }
    authorization = _lazy_import("pneuma_lab.foundation.authorization")
    candidate_path = candidates_root / f"{args.stage}.json"
    candidate = _load_json_object(
        candidate_path,
        label="authorization candidate",
        hint="run `prepare` for this stage first",
    )
    return {
        "candidate_path": str(candidate_path),
        "stage": args.stage,
        "execution_profile": "local",
        "scope_digest": candidate.get("scope_digest"),
        "required_approval_phrase": authorization.required_approval_phrase(candidate),
    }


def _run_authorization_finalize(args: argparse.Namespace) -> dict:
    candidate_path = Path(args.candidate)
    output_path = derive_final_authorization_path(candidate_path)
    approved_at = _utc_now()
    final_path = _finalize_authorization(
        candidate_path,
        args.scope_digest,
        args.approval_phrase,
        args.operator_id,
        approved_at,
        output_path,
    )
    return {
        "candidate_path": str(candidate_path),
        "final_authorization_path": str(final_path),
        "operator_id": args.operator_id,
        "approved_at": approved_at,
    }


def _run_result_payload(result, *, mode: str) -> dict:
    return {
        "mode": mode,
        "run_id": result.run_id,
        "status": result.status,
        "tokens_seen": result.progress.tokens_seen,
        "optimizer_steps": result.progress.optimizer_step,
        "last_checkpoint": (
            str(result.last_checkpoint) if result.last_checkpoint else None
        ),
        "run_manifest_path": str(result.run_manifest_path),
    }


def _run_train(args: argparse.Namespace) -> dict:
    runner = _lazy_import("pneuma_lab.foundation.runner")
    result = runner.run_foundation_training(
        _foundation_run_request(args, stage=args.stage, learning_rate=args.lr)
    )
    return _run_result_payload(result, mode="train")


def _stage_from_authorization(path: Path) -> str:
    manifest = _load_json_object(path, label="authorization manifest")
    scope = manifest.get("scope")
    stage = scope.get("stage") if isinstance(scope, Mapping) else None
    if not isinstance(stage, str) or not stage:
        raise ValueError("authorization manifest does not record a scope stage")
    return stage


def _checkpoint_learning_rate(checkpoint_path: Path) -> float:
    """Recover the exact checkpointed learning rate for the resume request.

    ``resume`` deliberately takes no ``--lr``: the learning rate is bound to
    the checkpoint, and the runner re-verifies the request value against the
    restored progress, so this recovery cannot widen the authorized scope.
    """

    import pickle

    try:
        import torch
    except ImportError as exc:
        raise RuntimeError("resume requires the foundation torch extra") from exc
    try:
        payload = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    except (
        OSError,
        RuntimeError,
        ValueError,
        EOFError,
        pickle.UnpicklingError,
    ) as exc:
        raise RuntimeError(f"checkpoint cannot be read: {exc}") from exc
    progress = payload.get("progress") if isinstance(payload, Mapping) else None
    rate = (
        progress.get("selected_learning_rate")
        if isinstance(progress, Mapping)
        else None
    )
    if not isinstance(rate, float) or not rate > 0:
        raise ValueError("checkpoint does not record a positive selected learning rate")
    return rate


def _run_resume(args: argparse.Namespace) -> dict:
    runner = _lazy_import("pneuma_lab.foundation.runner")
    checkpoint_path = Path(args.checkpoint)
    result = runner.resume_foundation_training(
        _foundation_run_request(
            args,
            stage=_stage_from_authorization(Path(args.authorization)),
            learning_rate=_checkpoint_learning_rate(checkpoint_path),
            checkpoint_path=checkpoint_path,
        )
    )
    return _run_result_payload(result, mode="resume")


def _run_evaluate(args: argparse.Namespace) -> dict:
    artifacts = _lazy_import("pneuma_lab.foundation.artifacts")
    evaluation = _lazy_import("pneuma_lab.foundation.evaluation")
    run_root = Path(args.run)
    manifest = _load_json_object(run_root / "manifest.json", label="run manifest")
    batches_path = run_root / "validation_batches.json"
    if not batches_path.is_file():
        raise ValueError(
            "run has no validation_batches.json; the runner manifest records "
            "only aggregate best/last validation losses, so per-batch metrics "
            f"must be exported to {batches_path} (a JSON array of mappings "
            "with token_count and validation_loss) before evaluation"
        )
    batches = _load_json_value(batches_path, label="validation batches artifact")
    if not isinstance(batches, list):
        raise ValueError(
            f"validation batches artifact must be a JSON array: {batches_path}"
        )
    report = evaluation.evaluate_run(
        manifest,
        validation_batches=batches,
        variant_results=(list(args.variant_results) if args.variant_results else None),
    )
    report_path = run_root / "evaluation_report.json"
    artifacts.write_atomic_json(report_path, report)
    return dict(report, evaluation_report_path=str(report_path))


def _run_report(args: argparse.Namespace) -> dict:
    reports = _lazy_import("pneuma_lab.foundation.reports")
    run_root = Path(args.run)
    if run_root.parent.name != "runs" or run_root.parent.parent.name != "foundation":
        raise ValueError("run directory must be <output-root>/foundation/runs/<run-id>")
    manifest = _load_json_object(run_root / "manifest.json", label="run manifest")
    evaluation = _load_json_object(
        run_root / "evaluation_report.json",
        label="evaluation report",
        hint="run `evaluate` for this run first",
    )
    paths = reports.materialize_reports(
        manifest, evaluation, output_root=run_root.parents[2]
    )
    return {name: str(path) for name, path in paths.items()}


def _run_cloud_bundle(args: argparse.Namespace) -> dict:
    module = _import_cloud_bundle()
    build_bundle = _cloud_entry_point(module, "build_cloud_bundle_for_cli")
    repo_root = _repo_root()
    output_path = (
        repo_root / "build" / "foundation" / "cloud" / f"{args.stage}-bundle.tar"
    )
    manifest = build_bundle(
        stage=args.stage,
        authorization_path=Path(args.authorization),
        quoted_hourly_usd=float(args.quoted_hourly_usd),
        quoted_tax_inclusive_usd=float(args.quoted_tax_inclusive_usd),
        output_path=output_path,
        repo_root=repo_root,
        dry_run=bool(args.dry_run),
    )
    payload = _json_safe(manifest) if isinstance(manifest, Mapping) else {}
    payload["bundle_path"] = str(output_path)
    payload["dry_run"] = bool(args.dry_run)
    return payload


def default_handlers() -> CommandHandlers:
    """Real command wiring; every heavy import happens inside its handler."""

    return CommandHandlers(
        doctor=_run_doctor,
        setup_plan=_run_setup_plan,
        prepare=_run_prepare,
        preflight=_run_preflight,
        download_model=_run_download_model,
        dry_run=_run_dry_run,
        authorization_candidate=_run_authorization_candidate,
        authorization_finalize=_run_authorization_finalize,
        train=_run_train,
        resume=_run_resume,
        evaluate=_run_evaluate,
        report=_run_report,
        cloud_bundle=_run_cloud_bundle,
    )


__all__ = [
    "CommandHandlers",
    "DEFAULT_SEED",
    "LEARNING_RATES",
    "STAGES",
    "build_parser",
    "default_handlers",
    "derive_final_authorization_path",
    "main",
    "render_command_result",
]
