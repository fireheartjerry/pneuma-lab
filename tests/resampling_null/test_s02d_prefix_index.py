"""Linux milestone claims: replay, tamper rejection, retry, and contention stop."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import pneuma_lab.resampling_null.prefix_index as prefix_index
from pneuma_lab.resampling_null import run_prefix, seal_prefix_index
from pneuma_lab.resampling_null.artifacts import validate_record
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.types import ArtifactRef
from pneuma_lab.foundation.artifacts import canonical_json_bytes
from tests.resampling_null.provider_authority_fixture import ProviderAuthorityFixture


pytestmark = pytest.mark.milestone


def _candidate(tmp_path: Path):
    root = tmp_path / "run"
    fixture = ProviderAuthorityFixture.build(
        root,
        executable_sources=True,
        requires_simulator=False,
        simulator_present=False,
    )
    schedule_path = root / "prefix-schedule.json"
    schedule = json.loads(schedule_path.read_bytes())
    registry = json.loads((root / "sources/tasks.json").read_bytes())
    second = json.loads(json.dumps(schedule["payload"]["tasks"][0]))
    second["task"] = {
        "task_id": registry["tasks"][1]["task_id"],
        "benchmark": registry["tasks"][1]["benchmark"],
        "stratum": registry["tasks"][1]["stratum"],
        "lineage": registry["tasks"][1]["lineage"],
        "sensitivity_groups": registry["tasks"][1]["groups"],
    }
    second["prefix_seed"] = 12
    schedule["payload"]["tasks"].append(second)
    validate_record(schedule)
    schedule_bytes = canonical_json_bytes(schedule, indent=None)
    schedule_path.write_bytes(schedule_bytes)
    fixture = ProviderAuthorityFixture(
        schedule_ref=ArtifactRef(
            role="resampling_prefix_schedule",
            relative_path="prefix-schedule.json",
            sha256=hashlib.sha256(schedule_bytes).hexdigest(),
            byte_count=len(schedule_bytes),
            media_type="application/json",
        ),
        refs=fixture.refs,
    )
    candidates = tuple(
        run_prefix(run_root=root, schedule_ref=fixture.schedule_ref, task_id=task_id)
        for task_id in ("task-1", "task-foreign")
    )
    return root, fixture, candidates


def test_clean_replay_publishes_prefix_index(tmp_path: Path) -> None:
    root, fixture, candidates = _candidate(tmp_path)

    ref = seal_prefix_index(
        run_root=root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=root / "prefix-index.json",
    )

    assert ref.relative_path == "prefix-index.json"
    assert (root / ref.relative_path).is_file()


def test_semantic_candidate_tamper_is_rejected(tmp_path: Path) -> None:
    root, fixture, candidates = _candidate(tmp_path)
    path = root / candidates[0].relative_path
    path.write_bytes(path.read_bytes().replace(b'"task-1"', b'"forged"'))

    with pytest.raises(RecordValidationError):
        seal_prefix_index(
            run_root=root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=root / "prefix-index.json",
        )


def test_failed_candidate_seal_leaves_a_clean_retry_path(tmp_path: Path) -> None:
    root, fixture, candidates = _candidate(tmp_path)
    with pytest.raises(ValueError):
        seal_prefix_index(
            run_root=root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=root / "../escape.json",
        )

    ref = seal_prefix_index(
        run_root=root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=root / "prefix-index.json",
    )
    assert (root / ref.relative_path).exists()


def test_concurrent_reservation_fails_stop(tmp_path: Path) -> None:
    root, fixture, candidates = _candidate(tmp_path)
    assert prefix_index._S02D_PROCESS_RESERVATION.acquire(blocking=False)
    try:
        with pytest.raises(RecordValidationError, match="reservation"):
            seal_prefix_index(
                run_root=root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=root / "prefix-index.json",
            )
    finally:
        prefix_index._S02D_PROCESS_RESERVATION.release()
