"""Fail-closed disposable micro-gate launcher checks."""

from __future__ import annotations

from pathlib import Path
import subprocess

from scripts.test_fast import build_cold_command, run_cold


def test_cold_command_is_limited_to_smoke_with_private_cache(tmp_path: Path) -> None:
    command, environment = build_cold_command(tmp_path, python="python-3.12")

    assert command == [
        "python-3.12",
        "-m",
        "pytest",
        "tests/smoke",
        "-q",
        "-p",
        "no:cacheprovider",
        "--import-mode=importlib",
    ]
    assert environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] == "1"
    assert environment["PYTHONPYCACHEPREFIX"] == str(tmp_path / "build/testd/pycache")


def test_cold_launcher_fails_closed_on_timeout(tmp_path: Path) -> None:
    def timeout(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(["pytest"], 5)

    assert run_cold(tmp_path, python="python-3.12", runner=timeout) == 1


def test_cold_launcher_rejects_malformed_child_result(tmp_path: Path) -> None:
    def malformed(*_args: object, **_kwargs: object) -> object:
        return object()

    assert run_cold(tmp_path, python="python-3.12", runner=malformed) == 1
