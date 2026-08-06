"""Seal the prospective official-study roster and prelaunch authorities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pneuma_lab.cloud.official_prelaunch import file_digest, seal_prelaunch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--secret-root", type=Path, required=True)
    parser.add_argument("--power-report", type=Path, required=True)
    parser.add_argument("--protocol-amendment", type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    args = parser.parse_args()
    result = seal_prelaunch(
        package_root=args.package_root,
        secret_root=args.secret_root,
        power_report_path=args.power_report,
        protocol_amendment_path=args.protocol_amendment,
        code_commit=args.code_commit,
    )
    print(
        json.dumps(
            {"prelaunch_root": result.as_posix(), "sha256": file_digest(result)},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
