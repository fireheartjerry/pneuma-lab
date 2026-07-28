"""The response cube: the single data structure every gauge statistic reads.

One `Response` is one elicitation: one (item, model, wording, scale, provenance,
arm, temperature, replicate) cell. The cube is deliberately raw — the model's
verbatim text is retained next to the parsed value, so a parse rule can be
re-litigated after the fact without re-running anything.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

#: Facets that identify a measurement *condition* (the metrology "operator").
CONDITION_FACETS = (
    "model",
    "wording_id",
    "scale_id",
    "arm",
    "provenance",
    "temperature",
)

_SORT_KEY = (
    "item_id",
    "model",
    "scale_id",
    "wording_id",
    "arm",
    "provenance",
    "temperature",
    "replicate",
)


@dataclass(frozen=True)
class Response:
    """One elicitation."""

    item_id: str
    model: str
    wording_id: str
    scale_id: str
    provenance: str
    arm: str
    temperature: float
    replicate: int
    raw_text: str
    value: float | None
    parse_ok: bool

    def asDict(self) -> dict:
        return {
            "item_id": self.item_id,
            "model": self.model,
            "wording_id": self.wording_id,
            "scale_id": self.scale_id,
            "provenance": self.provenance,
            "arm": self.arm,
            "temperature": self.temperature,
            "replicate": self.replicate,
            "raw_text": self.raw_text,
            "value": self.value,
            "parse_ok": self.parse_ok,
        }

    @staticmethod
    def fromDict(payload: dict) -> Response:
        return Response(
            item_id=str(payload["item_id"]),
            model=str(payload["model"]),
            wording_id=str(payload["wording_id"]),
            scale_id=str(payload["scale_id"]),
            provenance=str(payload["provenance"]),
            arm=str(payload["arm"]),
            temperature=float(payload["temperature"]),
            replicate=int(payload["replicate"]),
            raw_text=str(payload["raw_text"]),
            value=None if payload.get("value") is None else float(payload["value"]),
            parse_ok=bool(payload["parse_ok"]),
        )


@dataclass(frozen=True)
class BalancedMatrix:
    """A balanced item x condition x replicate design, ready for ANOVA."""

    cells: dict[tuple[str, tuple], list[float]]
    items: tuple[str, ...]
    conditions: tuple[tuple, ...]
    n_reps: int
    dropped_items: tuple[str, ...]
    dropped_conditions: tuple[tuple, ...]
    parse_failure_rate: float

    @property
    def n_items(self) -> int:
        return len(self.items)

    @property
    def n_conditions(self) -> int:
        return len(self.conditions)

    def usable(self) -> bool:
        return self.n_items >= 2 and self.n_conditions >= 2 and self.n_reps >= 2

    def itemRows(self) -> dict[str, dict[tuple, list[float]]]:
        """Regroup as item -> condition -> replicates (the bootstrap resamples items)."""
        rows: dict[str, dict[tuple, list[float]]] = {i: {} for i in self.items}
        for (item, cond), values in self.cells.items():
            rows[item][cond] = list(values)
        return rows


class ResponseCube:
    """An immutable, sorted collection of `Response` rows."""

    def __init__(self, responses: Iterable[Response]):
        self._rows: tuple[Response, ...] = tuple(
            sorted(
                responses,
                key=lambda r: tuple(_coerce(getattr(r, k)) for k in _SORT_KEY),
            )
        )

    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows)

    @property
    def rows(self) -> tuple[Response, ...]:
        return self._rows

    def values(self, facet: str) -> tuple:
        return tuple(sorted({getattr(r, facet) for r in self._rows}, key=_coerce))

    def filter(self, **facets) -> ResponseCube:
        """Keep rows matching every facet. A tuple/list value matches any member."""

        def keep(r: Response) -> bool:
            for key, want in facets.items():
                got = getattr(r, key)
                if isinstance(want, (tuple, list, set, frozenset)):
                    if got not in want:
                        return False
                elif got != want:
                    return False
            return True

        return ResponseCube(r for r in self._rows if keep(r))

    def mapValues(self, fn) -> ResponseCube:
        """Apply `fn` to every parsed value (used by the calibration remedy)."""
        return ResponseCube(
            replace(r, value=(None if r.value is None else float(fn(r.value))))
            for r in self._rows
        )

    def parseFailureRate(self) -> float:
        if not self._rows:
            return 0.0
        return sum(1 for r in self._rows if not r.parse_ok) / len(self._rows)

    def balancedMatrix(
        self, condition_facets: Sequence[str] = CONDITION_FACETS
    ) -> BalancedMatrix:
        """Collapse to a balanced item x condition x replicate design.

        Replicate counts are truncated to the minimum common count (dropping the
        *last* replicates, which is deterministic). Items or conditions with any
        empty cell are dropped and reported rather than silently imputed.
        """
        raw: dict[tuple[str, tuple], list[float]] = {}
        for r in self._rows:
            if not r.parse_ok or r.value is None:
                continue
            key = (r.item_id, tuple(getattr(r, f) for f in condition_facets))
            raw.setdefault(key, []).append((r.replicate, float(r.value)))
        cells_sorted = {k: [v for _, v in sorted(vs)] for k, vs in raw.items()}

        items = sorted({k[0] for k in cells_sorted})
        conditions = sorted(
            {k[1] for k in cells_sorted}, key=lambda c: tuple(map(_coerce, c))
        )

        # Drop items/conditions that are not fully crossed, iterating to a fixed point.
        while True:
            missing_items = {
                i for i in items if any((i, c) not in cells_sorted for c in conditions)
            }
            missing_conds = {
                c for c in conditions if any((i, c) not in cells_sorted for i in items)
            }
            if not missing_items and not missing_conds:
                break
            # Drop whichever side loses fewer observations, breaking ties toward conditions.
            if missing_items and (
                not missing_conds
                or len(missing_items) * len(conditions)
                <= len(missing_conds) * len(items)
            ):
                items = [i for i in items if i not in missing_items]
            else:
                conditions = [c for c in conditions if c not in missing_conds]
            if len(items) < 2 or len(conditions) < 2:
                break

        dropped_items = tuple(sorted({k[0] for k in cells_sorted} - set(items)))
        dropped_conditions = tuple(
            sorted(
                {k[1] for k in cells_sorted} - set(conditions),
                key=lambda c: tuple(map(_coerce, c)),
            )
        )

        # Choose the replicate depth that retains the most observations rather than
        # letting one short cell truncate the whole design. A handful of unparseable
        # replies would otherwise cost every item 25% of its data.
        depths = [
            min(len(cells_sorted[(i, c)]) for c in conditions)
            for i in items
            if all((i, c) in cells_sorted for c in conditions)
        ]
        n_reps = 0
        kept = list(items)
        if depths:
            best_score = -1
            for candidate in range(max(depths), 1, -1):
                keep = [
                    i
                    for i in items
                    if all((i, c) in cells_sorted for c in conditions)
                    and min(len(cells_sorted[(i, c)]) for c in conditions) >= candidate
                ]
                if len(keep) < 2:
                    continue
                score = len(keep) * candidate
                if score > best_score:
                    best_score, n_reps, kept = score, candidate, keep
        shallow = tuple(sorted(set(items) - set(kept)))
        items = kept
        dropped_items = tuple(sorted(set(dropped_items) | set(shallow)))
        cells = {
            (i, c): cells_sorted[(i, c)][:n_reps]
            for i in items
            for c in conditions
            if (i, c) in cells_sorted
        }
        return BalancedMatrix(
            cells=cells,
            items=tuple(items),
            conditions=tuple(conditions),
            n_reps=n_reps,
            dropped_items=dropped_items,
            dropped_conditions=dropped_conditions,
            parse_failure_rate=self.parseFailureRate(),
        )

    def toJsonl(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for r in self._rows:
                handle.write(
                    json.dumps(r.asDict(), sort_keys=True, ensure_ascii=False) + "\n"
                )
        return path

    @staticmethod
    def fromJsonl(path: str | Path) -> ResponseCube:
        rows = []
        with Path(path).open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(Response.fromDict(json.loads(line)))
        return ResponseCube(rows)

    def merge(self, other: ResponseCube) -> ResponseCube:
        return ResponseCube(list(self._rows) + list(other.rows))


def _coerce(value):
    """Sort key that keeps mixed float/str facets orderable and deterministic."""
    if isinstance(value, bool):
        return (0, float(value), "")
    if isinstance(value, (int, float)):
        return (0, float(value), "")
    return (1, 0.0, str(value))


__all__ = ["BalancedMatrix", "CONDITION_FACETS", "Response", "ResponseCube"]
