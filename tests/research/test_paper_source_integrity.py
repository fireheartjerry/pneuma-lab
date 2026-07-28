"""Tests for the injected-control-character check.

This check replaced two grep checks that had run green on every invocation while
missing a live defect -- one of them could never fire at all. So the tests that
matter are the ones proving it FAILS on the real damage, in both the forms that
damage actually took in this repository:

    mid-line   "Section~" + CR + "ef{sec:population}"
               the carriage return sits inside the line

    terminator "Section~" + CRLF + "ef{sec:floors}"
               the carriage return lands in line-terminator position, so it is
               indistinguishable from an ordinary Windows line ending, and the
               remnant becomes the start of the NEXT line

The second form is why the first version of this check, which only scanned for
stray control characters, was insufficient.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).resolve().parents[2] / "paper" / "check_source_integrity.py"
)
_spec = importlib.util.spec_from_file_location("check_source_integrity", _MODULE_PATH)
assert _spec and _spec.loader
integrity = importlib.util.module_from_spec(_spec)
sys.modules["check_source_integrity"] = integrity
_spec.loader.exec_module(integrity)

PAPER = _MODULE_PATH.parent


def run(job: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_MODULE_PATH), job],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def stage(tmp_path: Path, body: bytes) -> Path:
    """Write a throwaway job file next to the real checker."""
    target = PAPER / "_integrity_fixture.tex"
    target.write_bytes(body)
    return target


def test_the_real_papers_are_clean() -> None:
    for job in ("placebo", "main"):
        result = run(job, PAPER)
        assert result.returncode == 0, f"{job}: {result.stdout}"


def test_mid_line_carriage_return_is_caught(tmp_path: Path) -> None:
    """The form that reached the PDF as 'Section efsec:population.'"""
    target = stage(tmp_path, b"Text before Section~\r>ef{sec:x} and after.\r\n")
    try:
        result = run("_integrity_fixture", PAPER)
        assert result.returncode == 1
        assert "\\r" in result.stdout or "0D" in result.stdout
    finally:
        target.unlink(missing_ok=True)


def test_terminator_position_carriage_return_is_caught(tmp_path: Path) -> None:
    """The form that hid inside a legitimate CRLF and broke a live reference."""
    target = stage(
        tmp_path, b"the larger replication of Section~\r\nef{sec:floors} x\r\n"
    )
    try:
        result = run("_integrity_fixture", PAPER)
        assert result.returncode == 1, result.stdout
        assert "macro remnant" in result.stdout
    finally:
        target.unlink(missing_ok=True)


def test_ordinary_crlf_file_is_not_flagged(tmp_path: Path) -> None:
    """898 legitimate terminators must not look like damage."""
    body = b"\r\n".join(b"A normal line with \\ref{sec:x} in it." for _ in range(50))
    target = stage(tmp_path, body + b"\r\n")
    try:
        assert run("_integrity_fixture", PAPER).returncode == 0
    finally:
        target.unlink(missing_ok=True)


def test_literal_tab_is_caught(tmp_path: Path) -> None:
    """\\textbf losing a backslash becomes TAB + 'extbf'."""
    target = stage(tmp_path, b"A line with \textbf{bold} in it.\r\n")
    try:
        result = run("_integrity_fixture", PAPER)
        assert result.returncode == 1
        assert "09" in result.stdout or "\\t" in result.stdout
    finally:
        target.unlink(missing_ok=True)


@pytest.mark.parametrize("remnant", ["ef{", "extbf{", "egin{", "abel{", "itep{"])
def test_line_starting_with_a_macro_remnant_is_caught(
    remnant: str, tmp_path: Path
) -> None:
    target = stage(tmp_path, b"Fine line.\r\n" + remnant.encode() + b"sec:x} tail\r\n")
    try:
        assert run("_integrity_fixture", PAPER).returncode == 1
    finally:
        target.unlink(missing_ok=True)


def test_every_remnant_is_a_real_macro_minus_one_character() -> None:
    """A remnant that is not a macro tail would be a false-positive generator."""
    macros = {
        "ref",
        "textbf",
        "textit",
        "texttt",
        "emph",
        "begin",
        "end",
        "cite",
        "citep",
        "label",
        "section",
        "subsection",
        "newcommand",
        "frac",
        "footnote",
    }
    for remnant in integrity.REMNANTS:
        stem = remnant.rstrip("{")
        assert any(macro.endswith(stem) for macro in macros), remnant


def test_missing_job_file_is_not_an_error() -> None:
    assert run("no_such_job", PAPER).returncode == 0
