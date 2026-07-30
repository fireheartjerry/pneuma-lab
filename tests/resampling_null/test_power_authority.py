"""Focused contracts for the non-executing Task-8A power authority surface."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.artifacts import (_scientific_documents,
                                                   _validate_power_identities,
                                                   write_record)
from pneuma_lab.resampling_null.assignment import BytesField, U64Field, commitment_sha256, kdf_frame
from pneuma_lab.resampling_null.power import (
    RNG_CONTRACT_SHA256,
    grid_content_sha256,
    load_power_authority,
    load_power_config,
    screen_power_grid,
    seal_roster_bound_power_authority,
    seal_synthetic_power_authority,
    select_validation_cells,
    simulate_power_shard,
)
from pneuma_lab.resampling_null.types import ArtifactRef


def _ref(root: Path, path: str, role: str) -> ArtifactRef:
    payload = (root / path).read_bytes()
    return ArtifactRef(
        role=role,
        relative_path=path,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_count=len(payload),
        media_type="application/json",
    )


def _write(root: Path, path: str, value: object) -> ArtifactRef:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(canonical_json_bytes(value, indent=None))
    return _ref(root, path, path.rsplit("/", 1)[-1].removesuffix(".json"))


def _fast_timing_probe() -> dict[str, object]:
    """Non-timing tests use a contract-shaped probe; timing behavior is separate."""
    from pneuma_lab.resampling_null.power import frozen_power_cells
    ids = hashlib.sha256(canonical_json_bytes(
        [cell.cell_id for cell in frozen_power_cells()], indent=None,
    )).hexdigest()
    return {
        "contract_id": "p0-production-timing-probe-v1", "dataset_count": 200,
        "cell_count": 2916, "cell_ids_sha256": ids,
        "replay_receipts_sha256": "b" * 64, "measured_wall_seconds": 0.01,
    }


def _manifest(root: Path, *, roster_kind: str, eligibility: bool = False, eligibility_tier_mismatch: bool = False) -> ArtifactRef:
    study_id = "p0-test"
    nonce = b"n" * 32
    roster_commitment = commitment_sha256("roster-local-nonce", study_id, BytesField(nonce))
    schedule_commitment = "d" * 64
    assignment_commitment = "e" * 64
    tasks = [
        {
            "task_id": f"{prefix}-{index:03d}",
            "benchmark": benchmark,
            "stratum": stratum,
            "lineage": f"{prefix}-lineage-{index:03d}",
            "groups": groups,
            "tiers": [120, 160],
        }
        for benchmark, prefix, stratum, groups in (
            ("SWE", "swe", "python", [{"kind": "language", "value": "Python"}, {"kind": "domain", "value": "systems"}]),
            ("TAU", "tau", "retail", [{"kind": "domain", "value": "retail"}, {"kind": "issue_family", "value": "refund"}]),
        )
        for index in range(1, 21)
    ]
    task_ids = [task["task_id"] for task in tasks]
    roster = _write(
        root,
        "inputs/roster.json",
        {
            "record_kind": "resampling_roster_v1",
            "schema_version": "1",
            "roster_kind": roster_kind,
            "supported_tiers": [120, 160],
            "tasks": tasks,
        },
    )
    grid = _write(
        root,
        "inputs/grid.json",
        {
            "schema_version": "1",
            "benchmark_tiers": [120, 160],
            "p0_values": [0.1, 0.4, 0.7],
            "trigger_rates": [0.6, 0.75, 0.9],
            "latent_rhos": [0.0, 0.4, 0.8],
            "datasets_per_cell": 20000,
            "screen_datasets_per_cell": 200,
            "max_projected_wall_seconds": 43200,
            "validation_cell_count": 5,
            "validation_datasets_per_cell": 2000,
            "multiplier_draws": 99999,
            "target_effect": 0.15,
            "target_power": 0.8,
            "familywise_alpha": 0.05,
            "gauss_hermite_order": 96,
            "gauss_legendre_order": 128,
            "probability_tolerance": 1e-10,
            "gaussian_root_tolerance": 1e-10,
            "gaussian_root_max_iterations": 200,
            "clopper_pearson_tolerance": 1e-12,
            "clopper_pearson_max_iterations": 200,
            "rng": {
                "bit_generator": "numpy.random.Philox",
                "contract_id": "power-philox-v1",
                "counter_fields": ["draw_domain", "phase", "cell_id", "replicate_index", "draw_kind", "draw_index"],
                "counter_frame": "power-rng-counter-v1",
                "draw_domains": ["screen", "grid", "validation"],
                "draw_kinds": ["screen_trigger_partition", "screen_triggered_pattern", "screen_no_trigger_success", "grid_trigger_partition", "grid_triggered_pattern", "grid_no_trigger_success", "gaussian_validation_trigger_partition", "gaussian_validation_triggered_pattern", "gaussian_validation_no_trigger_success", "multiplier_rademacher"],
                "integer_encoding": "unsigned-big-endian",
                "key_fields": ["root_u64", "authority_kind", "tier_membership_sha256_raw32", "grid_content_sha256_raw32"],
                "key_frame": "power-rng-key-v1",
                "numpy_version": "2.3.5",
                "root_u64": 7640891576956012809,
            },
        },
    )
    topology = _write(root, "inputs/topology.json", {"topology": "local"})
    precommit = {
        "study_id": study_id,
        "qualification_universe_sha256": "1" * 64,
        "roster_local_nonce_commitment_sha256": roster_commitment,
        "schedule_seed_commitment_sha256": schedule_commitment,
        "assignment_master_key_commitment_sha256": assignment_commitment,
    }
    precommit_sha256 = hashlib.sha256(canonical_json_bytes(precommit, indent=None)).hexdigest()
    beacon = {"chain_hash": "8990e7a9aaed2ffed73dbd7092123d6f289930540d7651336225dc172e51b2ce", "round": 7, "randomness_hex": ("b" * 64)}
    roster_seed = hashlib.sha256(kdf_frame("roster-seed-v1", [BytesField(bytes.fromhex(precommit_sha256)), BytesField(nonce), BytesField(bytes.fromhex(beacon["chain_hash"])), U64Field(7), BytesField(bytes.fromhex(beacon["randomness_hex"]))])).hexdigest()
    eligibility_ref = (
        _write(
            root,
            "inputs/eligibility.json",
            {
                "record_kind": "resampling_eligibility_manifest_v1",
                "schema_version": "1",
                "study_id": study_id,
                "precommit": precommit,
                "precommit_sha256": precommit_sha256,
                "timestamp_receipt": {"precommit_sha256": precommit_sha256, "timestamp": "2026-07-30T00:00:00Z"},
                "beacon_receipt": beacon,
                "roster_local_nonce_hex": nonce.hex(),
                "roster_seed_sha256": roster_seed,
                "accepted_task_ids": task_ids,
                "rejected_task_ids": [],
                "tier_membership": {"120": task_ids, "160": [] if eligibility_tier_mismatch else task_ids},
                "group_labels": {task["task_id"]: task["groups"] for task in tasks},
                "reserves": [],
            },
        ) if eligibility else None
    )
    return _write(
        root,
        "study.json",
        {
            "record_kind": "resampling_study_manifest",
            "schema_version": "0.1.0",
            "study_id": study_id,
            "frozen_created_at": "2026-07-30T00:00:00Z",
            "provenance": {"design_sha256": "a" * 64, "code_sha256": "b" * 64},
            "payload": {
                "task_registry_ref": {"role": "task_registry", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "roster_ref": {"role": "roster", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "eligibility_manifest_ref": None if eligibility_ref is None else {"role": "eligibility_manifest", "relative_path": eligibility_ref.relative_path, "sha256": eligibility_ref.sha256, "byte_count": eligibility_ref.byte_count, "media_type": eligibility_ref.media_type},
                "roster_ceremony_policy_ref": None if eligibility_ref is None else {"role": "roster_ceremony_policy", "relative_path": eligibility_ref.relative_path, "sha256": eligibility_ref.sha256, "byte_count": eligibility_ref.byte_count, "media_type": eligibility_ref.media_type},
                "assignment_program_ref": {"role": "assignment_program", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "provider_lane_plan_ref": {"role": "provider_lane_plan", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "storage_policy_contract_ref": {"role": "storage_policy_contract", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "power_grid_ref": {"role": "power_grid", "relative_path": grid.relative_path, "sha256": grid.sha256, "byte_count": grid.byte_count, "media_type": grid.media_type},
                "power_screen_topology_ref": {"role": "power_screen_topology", "relative_path": topology.relative_path, "sha256": topology.sha256, "byte_count": topology.byte_count, "media_type": topology.media_type},
                "tokenizer_ref": {"role": "tokenizer", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "packet_template_ref": {"role": "packet_template", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "packet_policy_ref": {"role": "packet_policy", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "pad_unit_set_ref": {"role": "pad_unit_set", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
                "source_revision_refs": [{"role": "source_revision", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type}],
                "commitment_scheme": "resampling-null-key-ceremony-v1",
                "roster_local_nonce_commitment_sha256": roster_commitment,
                "schedule_seed_commitment_sha256": schedule_commitment,
                "assignment_master_key_commitment_sha256": assignment_commitment,
                "required_document_kinds_ref": {"role": "required_document_kinds", "relative_path": roster.relative_path, "sha256": roster.sha256, "byte_count": roster.byte_count, "media_type": roster.media_type},
            },
        },
    )


def test_synthetic_authority_is_manifest_derived_and_config_is_grid_bound(tmp_path: Path) -> None:
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json")

    authority = load_power_authority(authority_ref, run_root=tmp_path)
    config = load_power_config(authority_ref, _ref(tmp_path, "inputs/grid.json", "power_grid"), _ref(tmp_path, "inputs/topology.json", "power_screen_topology"), run_root=tmp_path)

    assert authority.authority_kind == "synthetic_validation"
    assert config.rng_contract_sha256 == RNG_CONTRACT_SHA256


def test_authority_rejects_wrong_roster_arm_and_tampered_grid_contract(tmp_path: Path) -> None:
    synthetic_manifest = _manifest(tmp_path, roster_kind="synthetic_fixture")
    with pytest.raises(RecordValidationError, match="eligible_confirmation"):
        seal_roster_bound_power_authority(synthetic_manifest, run_root=tmp_path, out=tmp_path / "bad.json")

    authority_ref = seal_synthetic_power_authority(synthetic_manifest, run_root=tmp_path, out=tmp_path / "authority.json")
    grid_path = tmp_path / "inputs/grid.json"
    grid = __import__("json").loads(grid_path.read_text())
    grid["rng"]["root_u64"] = 1
    grid_path.write_bytes(canonical_json_bytes(grid, indent=None))
    with pytest.raises(RecordValidationError, match="must exactly equal manifest-bound refs"):
        load_power_config(authority_ref, _ref(tmp_path, "inputs/grid.json", "power_grid"), _ref(tmp_path, "inputs/topology.json", "power_screen_topology"), run_root=tmp_path)


def test_roster_bound_authority_fails_closed_without_reviewed_ceremony_adapter(tmp_path: Path) -> None:
    manifest_ref = _manifest(tmp_path, roster_kind="eligible_confirmation", eligibility=True)

    with pytest.raises(RecordValidationError, match="no reviewed verified ceremony adapter"):
        seal_roster_bound_power_authority(manifest_ref, run_root=tmp_path, out=tmp_path / "authority.json")


def test_roster_bound_authority_rejects_arbitrary_beacon_and_timestamp_bytes(tmp_path: Path) -> None:
    manifest_ref = _manifest(tmp_path, roster_kind="eligible_confirmation", eligibility=True)
    path = tmp_path / "inputs/eligibility.json"
    eligibility = __import__("json").loads(path.read_text())
    eligibility["timestamp_receipt"] = {"precommit_sha256": "0" * 64, "timestamp": "forged"}
    eligibility["beacon_receipt"] = {"chain_hash": "0" * 64, "round": 0, "randomness_hex": "0" * 64}
    path.write_bytes(canonical_json_bytes(eligibility, indent=None))

    with pytest.raises(RecordValidationError, match="no reviewed verified ceremony adapter"):
        seal_roster_bound_power_authority(manifest_ref, run_root=tmp_path, out=tmp_path / "authority.json")


def _staged_screen(tmp_path: Path, *, decision_authority: str = "synthetic_validation", topology_path: str = "inputs/topology.json") -> None:
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json")
    grid_ref = _ref(tmp_path, "inputs/grid.json", "power_grid")
    topology_ref = _ref(tmp_path, topology_path, "power_screen_topology")
    config_ref = _write(tmp_path, "inputs/config.json", {"fixture": "config"})
    numeric_ref = _write(tmp_path, "inputs/numeric.json", {"fixture": "numeric"})
    roster_ref = _ref(tmp_path, "inputs/roster.json", "roster")
    write_record(
        tmp_path / "power/screen.json",
        {
            "record_kind": "resampling_power_report",
            "schema_version": "0.1.0",
            "study_id": "p0-test",
            "frozen_created_at": "2026-07-30T00:00:00Z",
            "provenance": {"design_sha256": "a" * 64, "code_sha256": "b" * 64},
            "payload": {
                "stage": "screen", "authority_ref": {"role": authority_ref.role, "relative_path": authority_ref.relative_path, "sha256": authority_ref.sha256, "byte_count": authority_ref.byte_count, "media_type": authority_ref.media_type},
                "decision_authority": decision_authority, "phase": "gaussian_approximation", "generation": 0,
                "roster_ref": {"role": roster_ref.role, "relative_path": roster_ref.relative_path, "sha256": roster_ref.sha256, "byte_count": roster_ref.byte_count, "media_type": roster_ref.media_type},
                "tier_membership_sha256": load_power_authority(authority_ref, run_root=tmp_path).tier_membership_sha256,
                "grid_ref": {"role": grid_ref.role, "relative_path": grid_ref.relative_path, "sha256": grid_ref.sha256, "byte_count": grid_ref.byte_count, "media_type": grid_ref.media_type},
                "screen_topology_ref": {"role": topology_ref.role, "relative_path": topology_ref.relative_path, "sha256": topology_ref.sha256, "byte_count": topology_ref.byte_count, "media_type": topology_ref.media_type},
                "rng_contract_sha256": RNG_CONTRACT_SHA256, "grid_content_sha256": grid_content_sha256(grid_ref, run_root=tmp_path),
                "kernel_id": "power-screen-gaussian-v1", "shard_count": 1, "parent_refs": [],
                "config_ref": {"role": config_ref.role, "relative_path": config_ref.relative_path, "sha256": config_ref.sha256, "byte_count": config_ref.byte_count, "media_type": config_ref.media_type},
                "numeric_fixture_ref": {"role": numeric_ref.role, "relative_path": numeric_ref.relative_path, "sha256": numeric_ref.sha256, "byte_count": numeric_ref.byte_count, "media_type": numeric_ref.media_type},
                "numeric_contract": {"numpy_version": "2.3.5", "gauss_hermite_order": 96, "gauss_legendre_order": 128, "probability_tolerance": 1e-10, "gaussian_root_tolerance": 1e-10, "gaussian_root_max_iterations": 200, "clopper_pearson_tolerance": 1e-12, "clopper_pearson_max_iterations": 200},
                "projected_wall_seconds": 1, "cell_count": 2916, "dataset_count": 200,
                "timing_probe": {
                    "contract_id": "p0-production-timing-probe-v1",
                    "dataset_count": 200, "cell_count": 2916,
                    "cell_ids_sha256": "c" * 64,
                    "replay_receipts_sha256": "d" * 64,
                    "authority_ref_sha256": authority_ref.sha256,
                    "measured_wall_seconds": 1.0,
                },
            },
        }, run_root=tmp_path, role="power_report",
    )


def test_staged_report_rejects_nonderived_authority_mirror_before_topology_walk(tmp_path: Path) -> None:
    _staged_screen(tmp_path, decision_authority="roster_bound_selection")
    documents = _scientific_documents(tmp_path, excluded=(tmp_path / "inputs/roster.json",))
    screen = documents["power/screen.json"]

    with pytest.raises(RecordValidationError, match="decision_authority is not derived"):
        _validate_power_identities([screen], run_root=tmp_path)


def test_staged_report_rejects_swapped_manifest_topology_ref(tmp_path: Path) -> None:
    _write(tmp_path, "inputs/other-topology.json", {"topology": "other"})
    _staged_screen(tmp_path, topology_path="inputs/other-topology.json")
    documents = _scientific_documents(tmp_path, excluded=(tmp_path / "inputs/roster.json",))
    screen = documents["power/screen.json"]

    with pytest.raises(RecordValidationError, match="grid/topology refs must exactly equal"):
        _validate_power_identities([screen], run_root=tmp_path)


def test_tiny_synthetic_shards_cannot_enter_the_authority_merge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bounded fixture work is evidence plumbing, never a shortcut to authority."""
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(
        manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json"
    )
    config = load_power_config(
        authority_ref,
        _ref(tmp_path, "inputs/grid.json", "power_grid"),
        _ref(tmp_path, "inputs/topology.json", "power_screen_topology"),
        run_root=tmp_path,
    )
    import pneuma_lab.resampling_null.power as power
    ticks = iter((0.0, 0.01, 1.0, 1.01))
    monkeypatch.setattr(power, "perf_counter", lambda: next(ticks))
    monkeypatch.setattr(power, "_production_timing_probe", lambda **_: _fast_timing_probe())
    monkeypatch.setattr(power, "_validate_screen_timing_admission", lambda *_, **__: None)
    first_screen = screen_power_grid(
        config, phase="gaussian_approximation", generation=0, shard_count=2,
        fallback_trigger_ref=None, run_root=tmp_path, out=tmp_path / "power/first-screen.json",
    )
    screen = screen_power_grid(
        config, phase="gaussian_approximation", generation=1, shard_count=2,
        fallback_trigger_ref=None, run_root=tmp_path, out=tmp_path / "power/screen.json",
    )
    shards = tuple(
        simulate_power_shard(screen, config, shard_index=index, run_root=tmp_path,
                             out=tmp_path / f"power/shard-{index}.json", max_datasets=2,
                             max_cells=1)
        for index in range(2)
    )
    with pytest.raises(RecordValidationError, match="incomplete synthetic shard"):
        select_validation_cells(
            screen, shards, config, run_root=tmp_path, out=tmp_path / "power/selection.json"
        )
    assert first_screen.relative_path != screen.relative_path


def test_screen_rejects_a_slow_production_representative_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The registered cap applies before a slow real shard can fan out."""
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(
        manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json",
    )
    config = load_power_config(
        authority_ref, _ref(tmp_path, "inputs/grid.json", "power_grid"),
        _ref(tmp_path, "inputs/topology.json", "power_screen_topology"), run_root=tmp_path,
    )
    import pneuma_lab.resampling_null.power as power
    cell_ids_sha256 = hashlib.sha256(canonical_json_bytes(
        [cell.cell_id for cell in power.frozen_power_cells()], indent=None,
    )).hexdigest()
    monkeypatch.setattr(
        "pneuma_lab.resampling_null.power._production_timing_probe",
        lambda **_: {
            "contract_id": "p0-production-timing-probe-v1", "dataset_count": 200,
            "cell_count": 2916, "cell_ids_sha256": cell_ids_sha256,
            "replay_receipts_sha256": "b" * 64, "measured_wall_seconds": 500.0,
        },
    )

    with pytest.raises(RecordValidationError, match="projection exceeds frozen 12-hour"):
        screen_power_grid(
            config, phase="gaussian_approximation", generation=0, shard_count=64,
            fallback_trigger_ref=None, run_root=tmp_path, out=tmp_path / "power/screen.json",
        )
    assert not (tmp_path / "power/screen.json").exists()


def test_simulate_rejects_a_tampered_screen_timing_probe_before_prewrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A screen timing hash is an admission capability, not decorative metadata."""
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(
        manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json",
    )
    config = load_power_config(
        authority_ref, _ref(tmp_path, "inputs/grid.json", "power_grid"),
        _ref(tmp_path, "inputs/topology.json", "power_screen_topology"), run_root=tmp_path,
    )
    import pneuma_lab.resampling_null.power as power
    cell_ids_sha256 = hashlib.sha256(canonical_json_bytes(
        [cell.cell_id for cell in power.frozen_power_cells()], indent=None,
    )).hexdigest()
    monkeypatch.setattr(
        "pneuma_lab.resampling_null.power._production_timing_probe",
        lambda **_: {
            "contract_id": "p0-production-timing-probe-v1", "dataset_count": 200,
            "cell_count": 2916, "cell_ids_sha256": cell_ids_sha256,
            "replay_receipts_sha256": "b" * 64, "measured_wall_seconds": 1.0,
        },
    )
    screen = screen_power_grid(
        config, phase="gaussian_approximation", generation=0, shard_count=1,
        fallback_trigger_ref=None, run_root=tmp_path, out=tmp_path / "power/screen.json",
    )
    path = tmp_path / screen.relative_path
    record = __import__("json").loads(path.read_text(encoding="utf-8"))
    record["payload"]["timing_probe"]["replay_receipts_sha256"] = "0" * 64
    path.write_bytes(canonical_json_bytes(record, indent=None))
    tampered = _ref(tmp_path, screen.relative_path, "power_report")
    with pytest.raises(RecordValidationError, match="verification receipt is absent"):
        simulate_power_shard(
            tampered, config, shard_index=0, run_root=tmp_path,
            out=tmp_path / "power/shard.json", max_datasets=1, max_cells=1,
        )
    assert not (tmp_path / "power/shard.json").exists()


def test_simulate_rejects_tampered_screen_elapsed_before_prewrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The projection must still match the measured total-work receipt."""
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(
        manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json",
    )
    config = load_power_config(
        authority_ref, _ref(tmp_path, "inputs/grid.json", "power_grid"),
        _ref(tmp_path, "inputs/topology.json", "power_screen_topology"), run_root=tmp_path,
    )
    import pneuma_lab.resampling_null.power as power
    ids = hashlib.sha256(canonical_json_bytes(
        [cell.cell_id for cell in power.frozen_power_cells()], indent=None,
    )).hexdigest()
    monkeypatch.setattr(
        power, "_production_timing_probe", lambda **_: {
            "contract_id": "p0-production-timing-probe-v1", "dataset_count": 200,
            "cell_count": 2916, "cell_ids_sha256": ids,
            "replay_receipts_sha256": "b" * 64, "measured_wall_seconds": 1.0,
        },
    )
    screen = screen_power_grid(
        config, phase="gaussian_approximation", generation=0, shard_count=1,
        fallback_trigger_ref=None, run_root=tmp_path, out=tmp_path / "power/screen.json",
    )
    path = tmp_path / screen.relative_path
    record = __import__("json").loads(path.read_text(encoding="utf-8"))
    record["payload"]["timing_probe"]["measured_wall_seconds"] = 2.0
    path.write_bytes(canonical_json_bytes(record, indent=None))

    with pytest.raises(RecordValidationError, match="projection does not match"):
        simulate_power_shard(
            _ref(tmp_path, screen.relative_path, "power_report"), config, shard_index=0,
            run_root=tmp_path, out=tmp_path / "power/shard.json", max_datasets=1,
            max_cells=1,
        )
    assert not (tmp_path / "power/shard.json").exists()


def test_simulate_rejects_a_forged_timing_verification_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Later shards require the locked verifier marker, not bare probe fields."""
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(
        manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json",
    )
    config = load_power_config(
        authority_ref, _ref(tmp_path, "inputs/grid.json", "power_grid"),
        _ref(tmp_path, "inputs/topology.json", "power_screen_topology"), run_root=tmp_path,
    )
    import pneuma_lab.resampling_null.power as power
    ids = hashlib.sha256(canonical_json_bytes(
        [cell.cell_id for cell in power.frozen_power_cells()], indent=None,
    )).hexdigest()
    monkeypatch.setattr(power, "_production_timing_probe", lambda **_: {
        "contract_id": "p0-production-timing-probe-v1", "dataset_count": 200,
        "cell_count": 2916, "cell_ids_sha256": ids,
        "replay_receipts_sha256": "b" * 64, "measured_wall_seconds": 1.0,
    })
    screen = screen_power_grid(
        config, phase="gaussian_approximation", generation=0, shard_count=1,
        fallback_trigger_ref=None, run_root=tmp_path, out=tmp_path / "power/screen.json",
    )
    marker = power._timing_verification_path(screen, run_root=tmp_path)
    receipt = __import__("json").loads(marker.read_text(encoding="utf-8"))
    receipt["authority_ref"]["sha256"] = "0" * 64
    marker.write_bytes(canonical_json_bytes(receipt, indent=None))

    with pytest.raises(RecordValidationError, match="does not bind this immutable screen"):
        simulate_power_shard(
            screen, config, shard_index=0, run_root=tmp_path,
            out=tmp_path / "power/shard.json", max_datasets=1, max_cells=1,
        )
    assert not (tmp_path / "power/shard.json").exists()


def test_timing_verification_receipt_is_a_singleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A concurrent second verifier cannot replace the first locked marker."""
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(
        manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json",
    )
    config = load_power_config(
        authority_ref, _ref(tmp_path, "inputs/grid.json", "power_grid"),
        _ref(tmp_path, "inputs/topology.json", "power_screen_topology"), run_root=tmp_path,
    )
    import pneuma_lab.resampling_null.power as power
    ids = hashlib.sha256(canonical_json_bytes([cell.cell_id for cell in power.frozen_power_cells()], indent=None)).hexdigest()
    monkeypatch.setattr(power, "_production_timing_probe", lambda **_: {
        "contract_id": "p0-production-timing-probe-v1", "dataset_count": 200,
        "cell_count": 2916, "cell_ids_sha256": ids,
        "replay_receipts_sha256": "b" * 64, "measured_wall_seconds": 1.0,
    })
    screen = screen_power_grid(config, phase="gaussian_approximation", generation=0,
                               shard_count=1, fallback_trigger_ref=None, run_root=tmp_path,
                               out=tmp_path / "power/screen.json")
    probe = __import__("json").loads((tmp_path / screen.relative_path).read_text())["payload"]["timing_probe"]

    with pytest.raises(RecordValidationError, match="verification receipt already exists"):
        power._write_timing_verification(screen, config, probe, run_root=tmp_path)


def test_shard_records_replay_receipts_and_task7_gate_totals_not_static_binomials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_ref = _manifest(tmp_path, roster_kind="synthetic_fixture")
    authority_ref = seal_synthetic_power_authority(
        manifest_ref, run_root=tmp_path, out=tmp_path / "power/authority.json"
    )
    config = load_power_config(
        authority_ref, _ref(tmp_path, "inputs/grid.json", "power_grid"),
        _ref(tmp_path, "inputs/topology.json", "power_screen_topology"), run_root=tmp_path,
    )
    import pneuma_lab.resampling_null.power as power
    ticks = iter((0.0, 0.01))
    monkeypatch.setattr(power, "perf_counter", lambda: next(ticks))
    monkeypatch.setattr(power, "_production_timing_probe", lambda **_: _fast_timing_probe())
    monkeypatch.setattr(power, "_validate_screen_timing_admission", lambda *_, **__: None)
    screen = screen_power_grid(
        config, phase="gaussian_approximation", generation=0, shard_count=1,
        fallback_trigger_ref=None, run_root=tmp_path, out=tmp_path / "power/screen.json",
    )
    shard = simulate_power_shard(
        screen, config, shard_index=0, run_root=tmp_path, out=tmp_path / "power/shard.json",
        max_datasets=2, max_cells=1,
    )
    payload = __import__("json").loads((tmp_path / shard.relative_path).read_text())["payload"]
    cell = payload["cell_results"][0]

    assert "replay_receipt" in cell
    assert cell["family"] == "alternative"
    assert cell["gate_totals"]["dataset_count"] == 2
    assert cell["replay_receipt"]["aggregate_gate_totals"] == cell["gate_totals"]
    assert "alternative_pass_count" not in cell
