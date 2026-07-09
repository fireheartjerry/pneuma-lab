from __future__ import annotations

import copy
import json

import pytest

from pneuma_lab.dataset_readiness import (
    AUTHORIZED_FIELDS,
    REGISTRY_PATH,
    DatasetReadinessError,
    load_registry,
    validate_registry,
)


def test_canonical_registry_is_valid_and_deterministic() -> None:
    registry = load_registry()
    assert validate_registry(registry) == ()
    assert validate_registry(json.loads(json.dumps(registry))) == ()


def test_every_lane_has_stage_and_training_readiness() -> None:
    registry = load_registry()
    assert registry["lanes"]
    for lane in registry["lanes"]:
        assert lane["current_stage"]
        assert lane["training_readiness"]
        assert lane["authorization"]["training_authorized"] is False


def test_referenced_nonplanned_paths_exist() -> None:
    registry = load_registry()
    for lane in registry["lanes"]:
        for refs in lane["references"].values():
            for ref in refs:
                if not ref.get("planned"):
                    assert (REGISTRY_PATH.parents[3] / ref["path"]).is_file(), ref


def test_authorization_requires_all_governance_bindings() -> None:
    registry = copy.deepcopy(load_registry())
    lane = registry["lanes"][0]
    lane["current_stage"] = "training-authorized"
    lane["training_readiness"] = "ready-for-controlled-training"
    lane["authorization"]["training_authorized"] = True
    findings = validate_registry(registry)
    assert any("authorization_manifest" in item for item in findings)
    assert AUTHORIZED_FIELDS


def test_dialogue_license_blocks_training_authorization() -> None:
    registry = copy.deepcopy(load_registry())
    lane = next(item for item in registry["lanes"] if item["lane_id"] == "dialogue-swe-bench")
    lane["current_stage"] = "training-authorized"
    lane["training_readiness"] = "ready-for-controlled-training"
    lane["authorization"] = {field: "bound" for field in AUTHORIZED_FIELDS}
    lane["authorization"]["training_authorized"] = True
    assert any("undeclared artifact license" in item for item in validate_registry(registry))


def test_verifier_joins_and_labels_block_training_authorization() -> None:
    registry = copy.deepcopy(load_registry())
    lane = next(item for item in registry["lanes"] if item["lane_id"] == "swe-gym-openhands-verifier")
    lane["current_stage"] = "training-authorized"
    lane["training_readiness"] = "ready-for-controlled-training"
    lane["authorization"] = {field: "bound" for field in AUTHORIZED_FIELDS}
    lane["authorization"]["training_authorized"] = True
    findings = validate_registry(registry)
    assert any("verifier joins and labels" in item for item in findings)


def test_check_registry_raises_only_on_invalid_registry(tmp_path) -> None:
    bad = tmp_path / "registry.json"
    bad.write_text(json.dumps({"registry_schema_version": "bad", "lanes": []}), encoding="utf-8")
    with pytest.raises(DatasetReadinessError):
        from pneuma_lab.dataset_readiness import check_registry

        check_registry(bad)
