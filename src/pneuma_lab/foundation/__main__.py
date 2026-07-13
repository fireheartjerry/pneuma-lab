"""Read-only local foundation diagnostics and duration calculations."""

from __future__ import annotations

import argparse
import json

from pneuma_lab.foundation.doctor import doctor_report, duration_hours, live_probe


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m pneuma_lab.foundation")
    subparsers = parser.add_subparsers(dest="command", required=True)
    doctor = subparsers.add_parser("doctor", help="check WSL2 local readiness")
    doctor.add_argument("--json", action="store_true", dest="as_json")
    duration = subparsers.add_parser(
        "duration", help="estimate hours from measured tps"
    )
    duration.add_argument("--tokens", type=int, required=True)
    duration.add_argument("--tps", type=float, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "duration":
        hours = duration_hours(args.tokens, args.tps)
        print(f"{args.tokens} tokens at {args.tps:g} tokens/s: {hours:.2f} hours")
        return 0
    report = doctor_report(live_probe())
    if args.as_json:
        print(json.dumps(report, indent=4, sort_keys=True))
    else:
        print("READY" if report["ready"] else "BLOCKED")
        for blocker in report["blockers"]:
            print(f"- {blocker}")
    return 0 if report["ready"] else 1


if __name__ == "__main__":  # pragma: no cover - module execution boundary
    raise SystemExit(main())
