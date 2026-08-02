"""Compile raw dual-worker measurements without contacting AWS or a model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.cloud.authorization_keys import canonical_bytes
from pneuma_lab.cloud.worker_admission import (
    compile_dual_worker_admissions,
    measurement_evidence_digest,
)


def _measurement_argument(value: str) -> tuple[int, Path]:
    try:
        worker, raw_path = value.split("=", 1)
        index = int(worker)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("measurement must be INDEX=PATH") from exc
    if index not in {0, 1} or not raw_path:
        raise argparse.ArgumentTypeError("measurement must name worker index 0 or 1 and a path")
    return index, Path(raw_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--measurement", action="append", type=_measurement_argument, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if len(args.measurement) != 2 or len({index for index, _ in args.measurement}) != 2:
        parser.error("supply exactly one raw measurement for each worker index")
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    measurements = {}
    for index, path in args.measurement:
        raw_bytes = path.read_bytes()
        measurements[index] = (json.loads(raw_bytes), measurement_evidence_digest(raw_bytes))
    receipts = compile_dual_worker_admissions(measurements, protocol)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for index, receipt in receipts.items():
        destination = args.output_dir / f"worker-{index}-pilot-admission.json"
        destination.write_bytes(canonical_bytes(receipt) + b"\n")
    print(json.dumps({"worker_indexes": sorted(receipts), "status": "validated"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
