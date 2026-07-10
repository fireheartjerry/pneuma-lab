"""CLI: python -m pneuma_lab.nervous_system --trace <f> [--model <f>] --out <dir>.

Runs the shadow pipeline over one PneumaTrace-shaped fixture and writes the output
bundle(s) plus an append-only shadow log under ``--out``. Falls back to the
hermetic fixture model when no ``--model`` is given and the trained elite model is
absent (the trained artifact lives under the gitignored ``build/`` tree).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.nervous_system import ShadowNervousSystem

_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_MODEL = _REPO / "build" / "brain" / "v0-1" / "elite-final" / "model.json"
_FIXTURE_MODEL = _REPO / "fixtures" / "nervous_system" / "model.json"


def _resolve_model(arg):
    if arg:
        return Path(arg)
    return _DEFAULT_MODEL if _DEFAULT_MODEL.exists() else _FIXTURE_MODEL


def main(argv=None):
    parser = argparse.ArgumentParser(prog="pneuma_lab.nervous_system")
    parser.add_argument("--trace", required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--governance", default=None)
    parser.add_argument("--out", default=str(_REPO / "build" / "nervous_system"))
    parser.add_argument("--prefix", default="full")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8").strip())
    if args.governance:
        governance = json.loads(Path(args.governance).read_text(encoding="utf-8"))
    else:
        governance = {
            "kill_switch_state": "on",
            "authority_ceilings": {"global_max": "hold"},
        }

    system = ShadowNervousSystem.from_model_path(
        _resolve_model(args.model), shadow_log_path=out / "shadow_log.jsonl"
    )
    bundles = system.run_trace(trace, governance, prefixes=(args.prefix,))

    with open(out / "output_bundles.jsonl", "w", encoding="utf-8") as handle:
        for bundle in bundles:
            handle.write(json.dumps(bundle, sort_keys=True) + "\n")
    print(f"wrote {len(bundles)} bundle(s) to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
