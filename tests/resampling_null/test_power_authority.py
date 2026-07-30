"""Focused contracts for the non-executing Task-8A power authority surface."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.resampling_null.errors import RecordValidationError
from pneuma_lab.resampling_null.power import (
    RNG_CONTRACT_SHA256,
    load_power_authority,
    load_power_config,
    seal_roster_bound_power_authority,
    seal_synthetic_power_authority,
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


def _manifest(root: Path, *, roster_kind: str, eligibility: bool = False) -> ArtifactRef:
    roster = _write(
        root,
        "inputs/roster.json",
        {
            "record_kind": "resampling_roster_v1",
            "schema_version": "1",
            "roster_kind": roster_kind,
            "supported_tiers": [120, 160],
            "tasks": [
                {
                    "task_id": "swe-001",
                    "benchmark": "SWE",
                    "stratum": "python",
                    "lineage": "repo-1",
                    "groups": [{"kind": "language", "value": "Python"}],
                    "tiers": [120, 160],
                }
            ],
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
    eligibility_ref = (
        _write(root, "inputs/eligibility.json", {"eligible": ["swe-001"]})
        if eligibility
        else None
    )
    return _write(
        root,
        "study.json",
        {
            "record_kind": "resampling_study_manifest",
            "schema_version": "0.1.0",
            "study_id": "p0-test",
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
                "roster_local_nonce_commitment_sha256": "c" * 64,
                "schedule_seed_commitment_sha256": "d" * 64,
                "assignment_master_key_commitment_sha256": "e" * 64,
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


def test_roster_bound_authority_requires_manifest_bound_eligibility(tmp_path: Path) -> None:
    manifest_ref = _manifest(tmp_path, roster_kind="eligible_confirmation", eligibility=True)

    authority_ref = seal_roster_bound_power_authority(manifest_ref, run_root=tmp_path, out=tmp_path / "authority.json")

    assert load_power_authority(authority_ref, run_root=tmp_path).authority_kind == "roster_bound_selection"
