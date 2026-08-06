"""Materialize the frozen controller-only SWE execution payload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.cloud.official_execution_assets import write_swe_execution_assets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.package_root.resolve()
    output = args.output or root / "inputs/execution/swe-tasks.controller-only.json"
    receipt = write_swe_execution_assets(
        task_registry_path=root / "inputs/task-registry.json",
        selection_path=root / "inputs/roster-sources/swe-selection.json",
        output_path=output,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
