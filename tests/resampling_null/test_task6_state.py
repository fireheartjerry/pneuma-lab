"""Adversarial tests for the one-way Task-6 controller boundary."""

from __future__ import annotations

import threading

import pytest

from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.task6_state import (
    mark_outcome_tainted,
    require_preunblind_context,
    require_singleton_absent,
    task6_controller_lock,
)


pytestmark = pytest.mark.milestone


def test_outcome_taint_is_durable_and_has_no_reset_path(tmp_path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    with task6_controller_lock(root) as locked:
        mark_outcome_tainted(locked)
    for action in (
        "resampling_analysis_freeze",
        "resampling_task_block",
        "resampling_blinded_projection",
    ):
        with pytest.raises(RecordValidationError, match="outcome-tainted"):
            require_preunblind_context(root, action)
    with task6_controller_lock(root) as locked:
        with pytest.raises(RecordValidationError, match="already outcome-tainted"):
            mark_outcome_tainted(locked)


def test_singleton_check_covers_alternate_destinations_and_concurrent_controllers(tmp_path) -> None:
    root = tmp_path / "run"
    root.mkdir()
    entered = threading.Event()
    release = threading.Event()
    observed: list[str] = []

    def first() -> None:
        with task6_controller_lock(root) as locked:
            require_singleton_absent(locked, "resampling_blinded_projection")
            (locked / "one").mkdir()
            (locked / "one" / "projection.json").write_text(
                '{"record_kind":"resampling_blinded_projection"}', encoding="utf-8"
            )
            entered.set()
            release.wait(timeout=2)

    def second() -> None:
        entered.wait(timeout=2)
        with task6_controller_lock(root) as locked:
            with pytest.raises(RecordValidationError, match="singleton"):
                require_singleton_absent(locked, "resampling_blinded_projection")
            observed.append("rejected")

    first_thread = threading.Thread(target=first)
    second_thread = threading.Thread(target=second)
    first_thread.start()
    second_thread.start()
    entered.wait(timeout=2)
    release.set()
    first_thread.join(timeout=2)
    second_thread.join(timeout=2)
    assert observed == ["rejected"]


def test_preunblind_graph_rejects_an_alternate_ledger_alias_before_loading(tmp_path) -> None:
    from pneuma_lab.resampling_null.artifacts import validate_preunblind_graph
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "run"
    root.mkdir()
    ledger = root / "ledger.json"
    ledger.write_text('{"record_kind":"resampling_assignment_ledger"}', encoding="utf-8")
    alias = root / "alternate.json"
    alias.hardlink_to(ledger)
    ref = ArtifactRef("ledger", "ledger.json", "0" * 64, 0, "application/json")
    with pytest.raises(RecordValidationError, match="exactly the bound assignment ledger"):
        validate_preunblind_graph(root, ref)
