"""Strict JSON and confined path helpers shared by authority modules."""

from __future__ import annotations

from collections.abc import Mapping
import json
import math
from numbers import Number
from pathlib import Path, PurePosixPath
from typing import Any, cast

from .errors import RecordValidationError


def plain_json(value: object, *, path: str = "$") -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise RecordValidationError(
                    f"{path}: JSON object keys must be strings"
                )
            result[key] = plain_json(nested, path=f"{path}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [
            plain_json(nested, path=f"{path}[{index}]")
            for index, nested in enumerate(value)
        ]
    if isinstance(value, bool):
        return value
    if isinstance(value, Number):
        try:
            finite = math.isfinite(cast(Any, value))
        except TypeError:
            finite = True
        if not finite:
            raise RecordValidationError(f"{path}: non-finite number")
        if type(value) not in (int, float):
            raise RecordValidationError(
                f"{path}: non-builtin numeric scalar is not a plain JSON number"
            )
    return value


def _reject_constant(value: str) -> object:
    raise RecordValidationError(f"non-finite JSON constant {value!r}")


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RecordValidationError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_json_bytes(payload: bytes, *, source: Path) -> object:
    if payload.startswith(b"\xef\xbb\xbf"):
        raise RecordValidationError(f"{source}: UTF-8 BOM is forbidden")
    try:
        text = payload.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except RecordValidationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RecordValidationError(
            f"{source}: invalid UTF-8 JSON: {exc}"
        ) from exc


def run_root(run_root: Path) -> Path:
    root = Path(run_root).resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    return root


def resolve_inside(
    path: Path,
    root: Path,
    *,
    require_exists: bool,
) -> tuple[Path, str]:
    run_root_path = run_root(root)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = run_root_path / candidate
    resolved = candidate.resolve(strict=require_exists)
    try:
        relative = resolved.relative_to(run_root_path)
    except ValueError as exc:
        raise RecordValidationError(
            f"artifact path escapes run_root: {path}"
        ) from exc
    if relative == Path("."):
        raise RecordValidationError(
            "artifact path must name a file below run_root"
        )
    return resolved, PurePosixPath(*relative.parts).as_posix()


__all__ = ("load_json_bytes", "plain_json", "resolve_inside", "run_root")
