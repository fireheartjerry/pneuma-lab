"""Keep canonical P0 grid work out of the software test surface.

A canonical all-cell screen probe or a full-workload grid shard is governed
scientific execution under the frozen timing-admission gate.  Running one as a
software or integration test both burns hours and blurs the line between
plumbing evidence and a result of record, so this guard fails closed on it.
Bounded machinery fixtures stay allowed: they are exactly the calls whose cell
and dataset counts are small.
"""

from __future__ import annotations

import pytest

_MAX_TEST_PROBE_CELLS = 8
_MAX_TEST_DATASETS_PER_CELL = 1024


@pytest.fixture(autouse=True)
def _forbid_canonical_grid_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    import pneuma_lab.resampling_null.power as power

    commitment = power._production_timing_probe_commitment
    gate_totals = power._gate_totals_for_cell

    def guarded_commitment(*, cells, **kwargs):
        if len(cells) > _MAX_TEST_PROBE_CELLS:
            raise AssertionError(
                f"a test attempted a {len(cells)}-cell screen timing probe; canonical "
                "full-grid work is scientific execution, not a software test"
            )
        return commitment(cells=cells, **kwargs)

    def guarded_gate_totals(cell, *, dataset_count, **kwargs):
        if dataset_count > _MAX_TEST_DATASETS_PER_CELL:
            raise AssertionError(
                f"a test attempted {dataset_count} datasets for cell {cell.cell_id}; "
                "canonical full-grid work is scientific execution, not a software test"
            )
        return gate_totals(cell, dataset_count=dataset_count, **kwargs)

    monkeypatch.setattr(power, "_production_timing_probe_commitment", guarded_commitment)
    monkeypatch.setattr(power, "_gate_totals_for_cell", guarded_gate_totals)
