"""Enforce the intentionally small default pytest surface without importing tests."""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path


SMOKE_DIRECTORY = Path("tests/smoke")
RESAMPLING_DIRECTORY = Path("tests/resampling_null")
PREFIX_INDEX_FILE = RESAMPLING_DIRECTORY / "test_s02d_prefix_index.py"
SMOKE_BUDGET = 8
RESAMPLING_BUDGET = 65


def _iter_python_files(root: Path, relative_directory: Path) -> Iterable[Path]:
    directory = root / relative_directory
    if not directory.is_dir():
        return ()
    return sorted(directory.rglob("*.py"), key=lambda path: path.relative_to(root).as_posix())


def _dotted_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else None
    return None


def _count_class_test_defs(node: ast.ClassDef) -> int:
    count = 0
    for member in node.body:
        if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count += member.name.startswith("test_")
        elif isinstance(member, ast.ClassDef):
            count += _count_class_test_defs(member)
    return count


def _count_test_defs(tree: ast.Module) -> int:
    count = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count += node.name.startswith("test_")
        elif isinstance(node, ast.ClassDef):
            count += _count_class_test_defs(node)
    return count


def _smoke_runtime_diagnostics(tree: ast.Module, relative_path: str) -> list[str]:
    diagnostics: list[str] = []
    forbidden_calls = {
        "pytest.skip",
        "pytest.xfail",
        "unittest.skip",
        "unittest.skipIf",
        "unittest.skipUnless",
        "pytest.mark.xfail",
        "pytest.mark.parametrize",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _dotted_name(node.func) in forbidden_calls:
            name = _dotted_name(node.func)
            diagnostics.append(f"{relative_path}: forbidden {name}")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for decorator in node.decorator_list:
                if (
                    not isinstance(decorator, ast.Call)
                    and _dotted_name(decorator) in forbidden_calls
                ):
                    name = _dotted_name(decorator)
                    diagnostics.append(
                        f"{relative_path}: forbidden {name}"
                    )

    return diagnostics


def _parse_file(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def inspect_test_budget(root: Path) -> tuple[str, ...]:
    """Return stable diagnostics for default-suite count and collection violations."""
    root = root.resolve()
    smoke_files = tuple(_iter_python_files(root, SMOKE_DIRECTORY))
    resampling_files = tuple(_iter_python_files(root, RESAMPLING_DIRECTORY))

    smoke_count = 0
    resampling_count = 0
    diagnostics: list[str] = []

    for path in smoke_files:
        tree = _parse_file(path)
        smoke_count += _count_test_defs(tree)
        diagnostics.extend(_smoke_runtime_diagnostics(tree, path.relative_to(root).as_posix()))

    for path in resampling_files:
        tree = _parse_file(path)
        resampling_count += _count_test_defs(tree)

    if smoke_count > SMOKE_BUDGET:
        diagnostics.append(
            "tests/smoke: expected at most "
            f"{SMOKE_BUDGET} test functions, found {smoke_count}"
        )
    if resampling_count > RESAMPLING_BUDGET:
        diagnostics.append(
            "tests/resampling_null: expected at most "
            f"{RESAMPLING_BUDGET} test functions, found {resampling_count}"
        )

    prefix_index_path = root / PREFIX_INDEX_FILE
    prefix_index_count = _count_test_defs(_parse_file(prefix_index_path)) if prefix_index_path.is_file() else 0
    if prefix_index_count > 4:
        diagnostics.append(
            "tests/resampling_null/test_s02d_prefix_index.py: expected at most 4 test functions, "
            f"found {prefix_index_count}"
        )

    return tuple(sorted(diagnostics))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check default pytest test-count budgets.")
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args(argv)
    diagnostics = inspect_test_budget(arguments.root)
    if not diagnostics:
        return 0

    for diagnostic in diagnostics:
        print(diagnostic, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
