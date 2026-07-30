from __future__ import annotations

from pathlib import Path

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


def test_missing_budget_directories_are_zero_and_pass(tmp_path: Path) -> None:
    assert inspect_test_budget(tmp_path) == ()
