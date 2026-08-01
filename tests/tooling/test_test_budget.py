from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

from scripts.check_test_budget import inspect_test_budget


def _write_tests(root: Path, relative_path: str, count: int) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"def test_case_{index}():\n    pass" for index in range(count)),
        encoding="utf-8",
    )


def _write_class_test(root: Path, relative_path: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "class TestContainer:\n    def test_method(self):\n        pass\n",
        encoding="utf-8",
    )


def test_accepts_counts_at_the_smoke_and_resampling_ceilings(tmp_path: Path) -> None:
    _write_tests(tmp_path, "tests/smoke/test_smoke.py", 7)
    _write_class_test(tmp_path, "tests/smoke/test_smoke_class.py")
    _write_tests(tmp_path, "tests/resampling_null/test_resampling.py", 60)
    _write_class_test(tmp_path, "tests/resampling_null/test_resampling_class.py")
    _write_tests(tmp_path, "tests/resampling_null/test_s02d_prefix_index.py", 4)

    assert inspect_test_budget(tmp_path) == ()


def test_rejects_more_than_eight_smoke_tests(tmp_path: Path) -> None:
    _write_tests(tmp_path, "tests/smoke/test_smoke.py", 9)

    assert inspect_test_budget(tmp_path) == (
        "tests/smoke: expected at most 8 test functions, found 9",
    )


def test_rejects_a_sixty_sixth_total_resampling_test(tmp_path: Path) -> None:
    _write_tests(tmp_path, "tests/resampling_null/test_resampling.py", 62)
    _write_tests(tmp_path, "tests/resampling_null/test_s02d_prefix_index.py", 4)

    assert inspect_test_budget(tmp_path) == (
        "tests/resampling_null: expected at most 65 test functions, found 66",
    )


def test_rejects_more_than_four_prefix_index_tests(tmp_path: Path) -> None:
    _write_tests(tmp_path, "tests/resampling_null/test_resampling.py", 60)
    _write_tests(tmp_path, "tests/resampling_null/test_s02d_prefix_index.py", 5)

    assert inspect_test_budget(tmp_path) == (
        "tests/resampling_null/test_s02d_prefix_index.py: expected at most 4 test functions, found 5",
    )


def test_rejects_forbidden_smoke_collection_constructs_anywhere(tmp_path: Path) -> None:
    smoke = tmp_path / "tests/smoke/test_runtime_features.py"
    smoke.parent.mkdir(parents=True)
    smoke.write_text(
        "\n".join(
            (
                "import pytest",
                "import unittest",
                "",
                "def subject_calls():",
                "    pytest.skip('forbidden')",
                "    pytest.xfail('forbidden')",
                "    unittest.skip('forbidden')",
                "    unittest.skipIf(True, 'forbidden')",
                "    unittest.skipUnless(False, 'forbidden')",
                "",
                "@pytest.skip('forbidden')",
                "def subject_pytest_skip_decorator():",
                "    pass",
                "",
                "@pytest.xfail('forbidden')",
                "def subject_pytest_xfail_decorator():",
                "    pass",
                "",
                "@unittest.skip('forbidden')",
                "def subject_unittest_skip_decorator():",
                "    pass",
                "",
                "@unittest.skipIf(True, 'forbidden')",
                "def subject_unittest_skip_if_decorator():",
                "    pass",
                "",
                "@unittest.skipUnless(False, 'forbidden')",
                "def subject_unittest_skip_unless_decorator():",
                "    pass",
                "",
                "@pytest.mark.xfail",
                "def subject_marked_xfail():",
                "    pass",
                "",
                "@pytest.mark.parametrize('value', [1, 2])",
                "def subject_parameterized(value):",
                "    pass",
            )
        ),
        encoding="utf-8",
    )

    diagnostics = inspect_test_budget(tmp_path)

    assert diagnostics == tuple(sorted(diagnostics))
    assert tuple(item.rsplit(": forbidden ", 1)[1] for item in diagnostics) == (
        "pytest.mark.parametrize",
        "pytest.mark.xfail",
        "pytest.skip",
        "pytest.skip",
        "pytest.xfail",
        "pytest.xfail",
        "unittest.skip",
        "unittest.skip",
        "unittest.skipIf",
        "unittest.skipIf",
        "unittest.skipUnless",
        "unittest.skipUnless",
    )


def test_rejects_simple_import_aliases_in_smoke_constructs(tmp_path: Path) -> None:
    smoke = tmp_path / "tests/smoke/test_aliases.py"
    smoke.parent.mkdir(parents=True)
    smoke.write_text(
        "\n".join(
            (
                "import pytest as pt",
                "import unittest as ut",
                "from pytest import mark",
                "from pytest import skip as ps",
                "from pytest import xfail as xf",
                "from unittest import skip as us",
                "from unittest import skipIf as skip_if",
                "from unittest import skipUnless as skip_unless",
                "",
                "def subject_calls():",
                "    pt.skip('forbidden')",
                "    pt.xfail('forbidden')",
                "    us('forbidden')",
                "    skip_if(True, 'forbidden')",
                "    skip_unless(False, 'forbidden')",
                "",
                "@ps('forbidden')",
                "def subject_skip_decorator():",
                "    pass",
                "",
                "@xf('forbidden')",
                "def subject_xfail_decorator():",
                "    pass",
                "",
                "@ut.skip('forbidden')",
                "def subject_unittest_skip_decorator():",
                "    pass",
                "",
                "@ut.skipIf(True, 'forbidden')",
                "def subject_unittest_skip_if_decorator():",
                "    pass",
                "",
                "@ut.skipUnless(False, 'forbidden')",
                "def subject_unittest_skip_unless_decorator():",
                "    pass",
                "",
                "@mark.xfail",
                "def subject_marked_xfail():",
                "    pass",
                "",
                "@mark.parametrize('value', [1, 2])",
                "def subject_parameterized(value):",
                "    pass",
            )
        ),
        encoding="utf-8",
    )

    diagnostics = inspect_test_budget(tmp_path)

    assert tuple(item.rsplit(": forbidden ", 1)[1] for item in diagnostics) == (
        "pytest.mark.parametrize",
        "pytest.mark.xfail",
        "pytest.skip",
        "pytest.skip",
        "pytest.xfail",
        "pytest.xfail",
        "unittest.skip",
        "unittest.skip",
        "unittest.skipIf",
        "unittest.skipIf",
        "unittest.skipUnless",
        "unittest.skipUnless",
    )


def test_default_pytest_collection_is_only_the_micro_gate() -> None:
    environment = os.environ.copy()
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    collected_files = tuple(
        line for line in result.stdout.splitlines() if line.startswith("tests/")
    )
    # The contract is that default collection reaches the micro gate and
    # nothing else. Pinning the case count as well made the gate's own growth
    # look like a budget violation: commit 79e9df7 deliberately took it to
    # seven cases and this assertion still demanded one.
    assert len(collected_files) == 1, collected_files
    assert collected_files[0].startswith("tests/smoke/test_micro_gate.py:"), collected_files
    assert "resampling_null" not in result.stdout


def test_pytest_config_keeps_opt_in_markers_out_of_default_collection() -> None:
    root = Path(__file__).resolve().parents[2]
    configuration = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = configuration["tool"]["pytest"]["ini_options"]["addopts"]
    environment = os.environ.copy()
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    default_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_foundation_qwen_smoke.py",
            "--collect-only",
            "-q",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    bare_marker_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-m",
            "qwen_smoke",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    selected_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_foundation_qwen_smoke.py",
            "--collect-only",
            "-q",
            "-m",
            "qwen_smoke",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )

    assert '-m "not qwen_smoke and not foundation"' in addopts
    assert default_result.returncode == 5, default_result.stderr
    assert "tests/test_foundation_qwen_smoke.py:" not in default_result.stdout
    assert bare_marker_result.returncode == 5, bare_marker_result.stderr
    assert "tests/test_foundation_qwen_smoke.py:" not in bare_marker_result.stdout
    # The opt-in selection can only collect where the optional dependency it
    # exercises is installed. Without torch the module is skipped at collection
    # and pytest exits 5, which is an environment condition rather than a broken
    # contract -- and the repository guide explicitly says not to install
    # optional dependencies just to manufacture a pass. The marker-exclusion
    # assertions above hold everywhere, so only this half is conditional.
    if importlib.util.find_spec("torch") is None:
        pytest.skip("torch unavailable: the qwen_smoke opt-in cannot collect in this environment")
    assert selected_result.returncode == 0, selected_result.stderr
    assert "tests/test_foundation_qwen_smoke.py: 1" in selected_result.stdout


def test_documented_pytest_commands_state_current_opt_in_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    required_commands = (
        "python -m pytest -q",
        "python -m pytest tests/test_foundation_qwen_smoke.py -m qwen_smoke -q",
        "python -m pytest $foundationTests -m foundation --import-mode=prepend -q",
    )

    for guide_name in ("AGENTS.md", "CLAUDE.md"):
        guide = (root / guide_name).read_text(encoding="utf-8")
        for command in required_commands:
            assert command in guide, f"{guide_name} must document: {command}"
        assert "$env:PYTHONPATH" in guide
        # The compact milestone suite was restored and is documented again, so
        # the guides must name it. This assertion previously required the
        # opposite -- that the command be absent and declared unavailable --
        # which stopped being true once the suite was marked and retained.
        assert "python -m pytest tests/resampling_null -m milestone -q" in guide
        # Bare-marker forms remain wrong: default discovery is restricted to
        # tests/smoke, so they silently collect nothing.
        assert "python -m pytest tests/ -m foundation -q" not in guide


def test_missing_budget_directories_are_zero_and_pass(tmp_path: Path) -> None:
    assert inspect_test_budget(tmp_path) == ()
