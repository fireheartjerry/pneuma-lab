"""Image-bound adapter for the fixed two-rung GPU admission probe."""

from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


def main() -> int:
    raw_index = os.environ.get("AWS_BATCH_JOB_ARRAY_INDEX")
    if raw_index not in {"0", "1"}:
        raise SystemExit("AWS_BATCH_JOB_ARRAY_INDEX must be exactly 0 or 1")
    required = {
        "QUALIFICATION_MODEL": "--model",
        "QUALIFICATION_MODEL_REVISION": "--revision",
        "QUALIFICATION_PROTOCOL": "--protocol",
        "QUALIFICATION_ARCHITECTURE": "--architecture",
        "QUALIFICATION_AUTHORIZATION": "--authorization",
        "QUALIFICATION_IMAGE": "--image",
        "QUALIFICATION_INPUT_LOCK": "--input-lock",
        "QUALIFICATION_OUTPUT_ROOT": "--output-root",
    }
    argv = ["dual_worker_admission_probe.py"]
    for variable, flag in required.items():
        value = os.environ.get(variable)
        if not value:
            raise SystemExit(f"missing image-bound qualification variable: {variable}")
        if flag == "--output-root":
            value = str(Path(value) / f"worker-{raw_index}" / "measurement.json")
            flag = "--output"
        argv.extend((flag, value))
    argv.extend(("--worker-index", raw_index))
    argv.extend(("--rung", "l40s-tp1-32768", "--rung", "l40s-tp1-65536"))
    sys.argv = argv
    runpy.run_module(
        "pneuma_lab.cloud.dual_worker_admission_probe", run_name="__main__"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
