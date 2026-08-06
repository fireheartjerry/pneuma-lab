"""God Mode command line for rapid PLACEBO experiment campaigns."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .adapters import SimulationAnalysis, SimulationExecution, SimulationReview
from .orchestrator import CampaignOrchestrator
from .workspace import initialize_r2, load_workspace, save_spend, verify_workspace_bindings


def _emit(value: object) -> None:
    print(json.dumps(value, sort_keys=True))


def _init(args: argparse.Namespace) -> int:
    manifest, version = initialize_r2(
        Path(args.root),
        final_review_path=Path(args.final_review),
        package_path=Path(args.package),
        image_set_path=Path(args.image_set),
        mode=args.mode,
        projected_microusd=round(args.projected_usd * 1_000_000),
    )
    _emit({"status": "INITIALIZED", "campaign_id": manifest.campaign_id, "version_id": version.version_id})
    return 0


def _status(args: argparse.Namespace) -> int:
    manifest, version, _, ledger, store = load_workspace(Path(args.root))
    snapshot = store.snapshot()
    _emit(
        {
            "campaign_id": manifest.campaign_id,
            "version_id": version.version_id,
            "phase": snapshot.phase,
            "decision": snapshot.decision_code,
            "controlled_usd": ledger.controlled_total_microusd / 1_000_000,
            "remaining_usd": ledger.remaining_microusd / 1_000_000,
        }
    )
    return 0


def _dry_run(args: argparse.Namespace) -> int:
    value = verify_workspace_bindings(Path(args.root))
    value["mutation"] = False
    value["status"] = "READY"
    _emit(value)
    return 0


def _inspect(args: argparse.Namespace) -> int:
    manifest, version, config, _, store = load_workspace(Path(args.root))
    _emit(
        {
            "manifest": manifest.to_mapping(),
            "version": version.to_mapping(),
            "mode": config["mode"],
            "state_sha256": store.snapshot().state_sha256,
        }
    )
    return 0


def _run(args: argparse.Namespace) -> int:
    root = Path(args.root)
    _, version, config, ledger, store = load_workspace(root)
    verify_workspace_bindings(root)
    if config["mode"] != "simulate":
        raise RuntimeError("official adapter is not installed yet; no mutation occurred")
    orchestrator = CampaignOrchestrator(
        store=store,
        ledger=ledger,
        version=version,
        projected_microusd=config["projected_microusd"],
        execution=SimulationExecution(root),
        analysis=SimulationAnalysis(root),
        review=SimulationReview(),
    )
    result = orchestrator.run()
    save_spend(root, ledger)
    _emit({"phase": result.phase, "decision": result.decision_code, "state_sha256": result.state_sha256})
    return 0


def _stop(args: argparse.Namespace) -> int:
    _, _, _, _, store = load_workspace(Path(args.root))
    snapshot = store.snapshot()
    if snapshot.phase != "teardown_complete":
        _emit({"status": "STOP_RECORDED", "phase": snapshot.phase, "mutation": False})
    else:
        _emit({"status": "ALREADY_TERMINAL", "phase": snapshot.phase, "mutation": False})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="godmode")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--root", required=True)
    init.add_argument("--final-review", required=True)
    init.add_argument("--package", required=True)
    init.add_argument("--image-set", required=True)
    init.add_argument("--mode", choices=("simulate", "official"), default="official")
    init.add_argument("--projected-usd", type=float, default=1_000.0)
    init.set_defaults(handler=_init)
    for name, handler in (("status", _status), ("dry-run", _dry_run), ("inspect", _inspect), ("run", _run), ("stop", _stop)):
        command = sub.add_parser(name)
        command.add_argument("--root", required=True)
        command.set_defaults(handler=handler)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))
