"""Numerical parity runner for fresh, cached, reset, packed, and continued cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

try:
    import torch
    from torch import Tensor
except ImportError as exc:  # pragma: no cover - optional dependency boundary
    raise ImportError(
        "pneuma_lab.foundation.parity requires the foundation torch extra"
    ) from exc


@dataclass(frozen=True)
class ParityCase:
    name: str
    args: tuple
    kwargs: Mapping


@dataclass(frozen=True)
class ParityReport:
    case_names: tuple[str, ...]
    max_absolute_error: float


def _compare(left, right, *, atol: float, rtol: float) -> float:
    if isinstance(left, Tensor) and isinstance(right, Tensor):
        torch.testing.assert_close(left, right, atol=atol, rtol=rtol)
        return float((left - right).abs().max().item()) if left.numel() else 0.0
    if isinstance(left, (tuple, list)) and isinstance(right, type(left)):
        if len(left) != len(right):
            raise AssertionError("output container lengths differ")
        return max(
            (_compare(a, b, atol=atol, rtol=rtol) for a, b in zip(left, right)),
            default=0.0,
        )
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            raise AssertionError("output mapping keys differ")
        return max(
            (
                _compare(left[key], right[key], atol=atol, rtol=rtol)
                for key in sorted(left)
            ),
            default=0.0,
        )
    if left is not right and left != right:
        raise AssertionError(f"non-tensor outputs differ: {left!r} != {right!r}")
    return 0.0


def assert_numerical_parity(
    reference,
    modified,
    cases: tuple[ParityCase, ...],
    *,
    atol: float,
    rtol: float,
) -> ParityReport:
    if not cases:
        raise ValueError("at least one parity case is required")
    errors = []
    names = []
    for case in cases:
        names.append(case.name)
        with torch.no_grad():
            expected = reference(*case.args, **dict(case.kwargs))
            actual = modified(*case.args, **dict(case.kwargs))
        errors.append(_compare(expected, actual, atol=atol, rtol=rtol))
    return ParityReport(
        case_names=tuple(names),
        max_absolute_error=max(errors, default=0.0),
    )
