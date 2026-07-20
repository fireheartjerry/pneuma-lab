"""Validate START-HERE-TRAINING.md against the real foundation CLI.

The operator guide is an executable contract: every fenced
``python -m pneuma_lab.foundation`` command must parse against the real
argument parser, every CLI command must appear in an operational section,
and the final checklist must end with the deliberately unchecked ``train``
action. Documented shell variables are substituted with syntactically valid
fixture values (paths, digests, phrases, hosts, ports, floats) before
parsing; the checker never executes any command.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
import shlex
import sys
from pathlib import Path


class OperatorGuideError(ValueError):
    """The operator guide file cannot be checked."""


GUIDE_TITLE = "# TRAINING HAS NOT STARTED"

REQUIRED_GUIDE_COMMANDS = frozenset(
    {
        "doctor",
        "duration",
        "setup-plan",
        "prepare",
        "preflight",
        "download-model",
        "dry-run",
        "authorization-candidate",
        "authorization-finalize",
        "train",
        "resume",
        "evaluate",
        "report",
        "cloud-bundle",
    }
)

REQUIRED_HEADINGS = (
    "## 1. What “all ten datasets” means",
    "## 2. Current readiness and hard safety boundaries",
    "## 3. Windows WSL2 memory setup",
    "## 4. WSL Python 3.12 environment",
    "## 5. Close GPU-heavy Windows applications",
    "## 6. Download and verify only Qwen3.5-2B",
    "## 7. Prepare the deterministic 100K shard",
    "## 8. Review the exact authorization candidate",
    "## 9. Finalize only the displayed digest",
    "## 10. Run non-training preflight and no-gradient dry run",
    "## 11. Start, monitor, interrupt, and resume training",
    "## 12. Evaluate and report",
    "## 13. Optional one-time RunPod reproduction",
    "## 14. Common failures and exact recovery",
    "## 15. Final operator checklist",
)

_MODULE_TOKEN = "python -m pneuma_lab.foundation"
_FINALIZE_VARIABLES = ("PNEUMA_SCOPE_DIGEST", "PNEUMA_APPROVAL_PHRASE")
_VARIABLE_TOKEN = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")


def _fixture_for_variable(name: str) -> str:
    upper = name.upper()
    if upper.endswith("_USD"):
        return "12.34"
    if "PHRASE" in upper:
        return "I APPROVE THIS EXACT PNEUMA FOUNDATION SCOPE " + "a" * 64
    if "DIGEST" in upper:
        return "a" * 64
    if "PORT" in upper:
        return "22"
    if "HOST" in upper:
        return "203.0.113.5"
    return "build/foundation/fixture.json"


def _fenced_lines(text: str) -> list[str]:
    lines: list[str] = []
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            inside = not inside
            continue
        if inside:
            lines.append(stripped)
    if inside:
        raise OperatorGuideError("operator guide has an unterminated code fence")
    return lines


def _guide_command_lines(text: str) -> list[str]:
    commands: list[str] = []
    for line in _fenced_lines(text):
        if _MODULE_TOKEN not in line:
            continue
        if "pneuma_lab.foundation.operator_guide" in line:
            continue
        _, _, arguments = line.partition(_MODULE_TOKEN)
        commands.append(arguments.strip())
    return commands


def _substituted_argv(arguments: str) -> list[str]:
    tokens = shlex.split(arguments)
    argv: list[str] = []
    for token in tokens:
        match = _VARIABLE_TOKEN.fullmatch(token)
        argv.append(_fixture_for_variable(match.group(1)) if match else token)
    return argv


def _parse_silently(parser: argparse.ArgumentParser, argv: list[str]) -> bool:
    sink = io.StringIO()
    try:
        with (
            contextlib.redirect_stderr(sink),
            contextlib.redirect_stdout(sink),
        ):
            parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code in (0, None)
    return True


def _section_region(text: str, heading: str, next_heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    end = text.find(next_heading, start)
    return text[start:end] if end >= 0 else text[start:]


def _checklist_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("- [")]


def guide_problems(guide_path: Path, *, parser: argparse.ArgumentParser) -> list[str]:
    """Return every structural problem in the guide; empty means clean."""

    try:
        text = Path(guide_path).read_text(encoding="utf-8")
    except OSError as exc:
        raise OperatorGuideError(f"operator guide cannot be read: {exc}") from exc
    problems: list[str] = []
    if not text.startswith(GUIDE_TITLE):
        problems.append("guide must start with the TRAINING HAS NOT STARTED marker")
    if "No Jupyter notebook is required." not in text:
        problems.append("guide must state that no Jupyter notebook is required")
    cursor = 0
    for heading in REQUIRED_HEADINGS:
        position = text.find(heading, cursor)
        if position < 0:
            problems.append(f"missing or out-of-order heading: {heading}")
        else:
            cursor = position
    checklist = _checklist_lines(text)
    if not checklist:
        problems.append("guide must end with an operator checklist")
    elif not checklist[-1].startswith("- [ ] `python -m pneuma_lab.foundation train"):
        problems.append("the last checklist item must be the unchecked train command")
    finalize_region = _section_region(text, REQUIRED_HEADINGS[8], REQUIRED_HEADINGS[9])
    for name in _FINALIZE_VARIABLES:
        for line in text.splitlines():
            if name in line and line not in finalize_region:
                problems.append(f"{name} may appear only in the finalization sequence")
                break
    fence_start = finalize_region.find("```")
    preamble = finalize_region[:fence_start] if fence_start >= 0 else ""
    if not ("authorization-candidate" in preamble and "paste" in preamble.casefold()):
        problems.append(
            "the finalization paragraph must tell the operator to paste the"
            " values printed by authorization-candidate"
        )
    return problems


def check_operator_guide(
    guide_path: Path,
    *,
    parser: argparse.ArgumentParser,
) -> dict:
    """Check the guide's commands and structure against the real parser."""

    text = Path(guide_path).read_text(encoding="utf-8")
    unknown_commands: list[str] = []
    seen_commands: set[str] = set()
    for arguments in _guide_command_lines(text):
        try:
            argv = _substituted_argv(arguments)
        except ValueError:
            unknown_commands.append(arguments)
            continue
        if not argv:
            unknown_commands.append(arguments)
            continue
        if _parse_silently(parser, argv):
            seen_commands.add(argv[0])
        else:
            unknown_commands.append(arguments)
    missing_commands = sorted(REQUIRED_GUIDE_COMMANDS - seen_commands)
    structural = guide_problems(guide_path, parser=parser)
    return {
        "valid": not (unknown_commands or missing_commands or structural),
        "unknown_commands": unknown_commands,
        "missing_commands": missing_commands,
    }


def main(argv: list[str] | None = None) -> int:
    entry = argparse.ArgumentParser(
        prog="python -m pneuma_lab.foundation.operator_guide"
    )
    entry.add_argument("guide", type=Path)
    args = entry.parse_args(argv)
    from pneuma_lab.foundation.cli import build_parser

    parser = build_parser()
    report = check_operator_guide(args.guide, parser=parser)
    print(json.dumps(report, indent=4, sort_keys=True))
    for problem in guide_problems(args.guide, parser=parser):
        print(f"PROBLEM: {problem}", file=sys.stderr)
    return 0 if report["valid"] else 1


if __name__ == "__main__":  # pragma: no cover - module execution boundary
    raise SystemExit(main())
