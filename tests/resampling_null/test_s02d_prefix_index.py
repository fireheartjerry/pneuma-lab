from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import pytest

import pneuma_lab.resampling_null.prefix_index as prefix_index_module
from pneuma_lab.resampling_null import run_prefix, seal_prefix_index
from pneuma_lab.resampling_null.artifacts import validate_record
from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.types import ArtifactRef
from tests.resampling_null.provider_authority_fixture import (
    ProviderAuthorityFixture,
)


def _completed_candidates(
    tmp_path: Path,
) -> tuple[Path, ProviderAuthorityFixture, tuple[ArtifactRef, ArtifactRef]]:
    run_root = tmp_path / "run"
    fixture = ProviderAuthorityFixture.build(
        run_root,
        executable_sources=True,
        requires_simulator=False,
        simulator_present=False,
    )
    schedule_path = run_root / "prefix-schedule.json"
    schedule = json.loads(schedule_path.read_bytes())
    registry = json.loads((run_root / "sources/tasks.json").read_bytes())
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
        run_prefix(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            task_id=task_id,
        )
        for task_id in ("task-1", "task-foreign")
    )
    return run_root, fixture, candidates


def test_s02d_seals_exact_schedule_order_after_fresh_graph_reload(
    tmp_path: Path,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    out = run_root / "prefix-index.json"

    ref = seal_prefix_index(
        run_root=run_root,
        schedule_ref=fixture.schedule_ref,
        candidate_refs=candidates,
        out=out,
    )

    assert ref.role == "resampling_prefix_receipt"
    assert ref.relative_path == "prefix-index.json"
    assert ref.media_type == "application/json"
    record = validate_record(json.loads(out.read_bytes()))
    assert record["payload"]["schedule_ref"] == asdict(fixture.schedule_ref)  # type: ignore[index]
    assert [
        receipt["task_id"]  # type: ignore[index]
        for receipt in record["payload"]["task_receipts"]  # type: ignore[index]
    ] == ["task-1", "task-foreign"]


@pytest.mark.parametrize("case", ["duplicate", "reverse"])
def test_s02d_rejects_nonexact_candidate_roster(
    tmp_path: Path,
    case: str,
) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    invalid = (
        (candidates[0], candidates[0])
        if case == "duplicate"
        else tuple(reversed(candidates))
    )

    with pytest.raises((TypeError, ValueError)):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=invalid,
            out=run_root / "prefix-index.json",
        )

    assert not (run_root / "prefix-index.json").exists()


def test_s02d_rejects_reserved_or_existing_destination(tmp_path: Path) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    existing = run_root / "prefix-index.json"
    existing.write_bytes(b"do not overwrite")

    for out in (
        existing,
        run_root / "controller-artifacts" / "prefix-index.json",
    ):
        with pytest.raises((FileExistsError, ValueError)):
            seal_prefix_index(
                run_root=run_root,
                schedule_ref=fixture.schedule_ref,
                candidate_refs=candidates,
                out=out,
            )

    assert existing.read_bytes() == b"do not overwrite"


def test_s02d_rejects_symlink_destination_component(tmp_path: Path) -> None:
    run_root, fixture, candidates = _completed_candidates(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (run_root / "publication-link").symlink_to(outside, target_is_directory=True)

    with pytest.raises((OSError, ValueError)):
        seal_prefix_index(
            run_root=run_root,
            schedule_ref=fixture.schedule_ref,
            candidate_refs=candidates,
            out=run_root / "publication-link" / "prefix-index.json",
        )

    assert not (outside / "prefix-index.json").exists()


@pytest.mark.parametrize("operation", ["write", "close"])
def test_s02d_publication_fault_removes_only_owned_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    target = run_root / "prefix-index.json"
    real_write = prefix_index_module.os.write
    real_close = prefix_index_module.os.close
    injected = False

    def is_target(descriptor: int) -> bool:
        try:
            return Path(f"/proc/self/fd/{descriptor}").resolve() == target
        except OSError:
            return False

    def failing_write(descriptor: int, payload: object) -> int:
        nonlocal injected
        if not injected and is_target(descriptor):
            injected = True
            raise OSError("injected write failure")
        return real_write(descriptor, payload)  # type: ignore[arg-type]

    def failing_close(descriptor: int) -> None:
        nonlocal injected
        if not injected and is_target(descriptor):
            injected = True
            real_close(descriptor)
            raise OSError("injected close failure")
        real_close(descriptor)

    monkeypatch.setattr(
        prefix_index_module.os,
        operation,
        failing_write if operation == "write" else failing_close,
    )
    root_descriptor = prefix_index_module.os.open(
        run_root,
        prefix_index_module._DIRECTORY_FLAGS,
    )
    try:
        with pytest.raises(BaseException):
            prefix_index_module._publish_once(
                root_descriptor=root_descriptor,
                relative_path="prefix-index.json",
                payload=b"payload",
            )
    finally:
        prefix_index_module.os.close(root_descriptor)

    assert injected
    assert not target.exists()
