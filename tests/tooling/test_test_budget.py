from __future__ import annotations

from pathlib import Path

from scripts.check_test_budget import inspect_test_budget


def _write_tests(root: Path, relative_path: str, count: int, *, prefix: str = "test_case") -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"def {prefix}_{index}():\n    pass" for index in range(count)),
        encoding="utf-8",
    )


def _write_class_test(root: Path, relative_path: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "class TestContainer:\n    def test_method(self):\n        pass\n",
        encoding="utf-8",
    )


def test_accepts_exact_smoke_and_resampling_budgets(tmp_path: Path) -> None:
    _write_tests(tmp_path, "tests/smoke/test_smoke.py", 7)
    _write_class_test(tmp_path, "tests/smoke/test_smoke_class.py")
    _write_tests(tmp_path, "tests/resampling_null/test_resampling.py", 64)
    _write_class_test(tmp_path, "tests/resampling_null/test_resampling_class.py")

    assert inspect_test_budget(tmp_path) == ()


def test_rejects_nine_smoke_tests(tmp_path: Path) -> None:
    _write_tests(tmp_path, "tests/smoke/test_smoke.py", 9)
    _write_tests(tmp_path, "tests/resampling_null/test_resampling.py", 65)

    assert inspect_test_budget(tmp_path) == (
        "tests/smoke: expected 8 test functions, found 9",
    )


def test_rejects_sixty_six_resampling_tests(tmp_path: Path) -> None:
    _write_tests(tmp_path, "tests/smoke/test_smoke.py", 8)
    _write_tests(tmp_path, "tests/resampling_null/test_resampling.py", 66)

    assert inspect_test_budget(tmp_path) == (
        "tests/resampling_null: expected 65 test functions, found 66",
    )


def test_rejects_any_prefix_index_tests(tmp_path: Path) -> None:
    _write_tests(tmp_path, "tests/smoke/test_smoke.py", 8)
    _write_tests(tmp_path, "tests/resampling_null/test_resampling.py", 65)
    _write_tests(
        tmp_path,
        "tests/resampling_null/test_s02d_prefix_index.py",
        5,
    )

    assert inspect_test_budget(tmp_path) == (
        "tests/resampling_null/test_s02d_prefix_index.py: expected 0 test functions, found 5",
    )


def test_rejects_smoke_runtime_collection_features(tmp_path: Path) -> None:
    smoke = tmp_path / "tests/smoke/test_runtime_features.py"
    smoke.parent.mkdir(parents=True)
    smoke.write_text(
        "\n".join(
            (
                "import pytest",
                "import unittest",
                "",
                "def test_skip_call():",
                "    pytest.skip('forbidden')",
                "",
                "def test_xfail_call():",
                "    pytest.xfail('forbidden')",
                "",
                "@unittest.skip('forbidden')",
                "def test_unittest_skip():",
                "    pass",
                "",
                "@pytest.mark.xfail",
                "def test_marked_xfail():",
                "    pass",
                "",
                "@pytest.mark.parametrize('value', [1, 2])",
                "def test_parameterized(value):",
                "    pass",
            )
        ),
        encoding="utf-8",
    )
    _write_tests(tmp_path, "tests/smoke/test_smoke.py", 3)
    _write_tests(tmp_path, "tests/resampling_null/test_resampling.py", 65)

    assert inspect_test_budget(tmp_path) == (
        "tests/smoke/test_runtime_features.py: forbidden pytest.mark.parametrize decorator",
        "tests/smoke/test_runtime_features.py: forbidden pytest.mark.xfail decorator",
        "tests/smoke/test_runtime_features.py: forbidden pytest.skip call",
        "tests/smoke/test_runtime_features.py: forbidden pytest.xfail call",
        "tests/smoke/test_runtime_features.py: forbidden unittest.skip decorator",
    )


def test_missing_budget_directories_are_zero(tmp_path: Path) -> None:
    assert inspect_test_budget(tmp_path) == (
        "tests/resampling_null: expected 65 test functions, found 0",
        "tests/smoke: expected 8 test functions, found 0",
    )
