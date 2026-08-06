"""Network-isolated parser entrypoint for pinned SWE log-parser source."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 3:
        return 2
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    parser_source = request.get("parser_source")
    log = request.get("log")
    if not isinstance(parser_source, str) or not isinstance(log, str):
        return 3
    namespace: dict[str, object] = {}
    exec(compile(parser_source, "<pinned-swe-log-parser>", "exec"), namespace)
    parser = namespace.get("parser")
    if not callable(parser):
        return 4
    value = parser(log)
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not isinstance(status, str)
        for key, status in value.items()
    ):
        return 5
    Path(sys.argv[2]).write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
