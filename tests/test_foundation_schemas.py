"""Foundation manifests remain machine-readable and claim-decoupled."""

from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest
from jsonschema import Draft202012Validator, ValidationError

from pneuma_lab import schemas as pls
from pneuma_lab.foundation.core import FORECAST_TARGETS
from pneuma_lab.foundation.profiles import build_subject_profile


ROOT = Path(__file__).resolve().parents[1]


def _assert_valid(instance: dict, schema_name: str) -> None:
    Draft202012Validator(pls.load_schema(schema_name)).validate(instance)


def test_pending_foundation_authorization_is_schema_valid_and_non_authorizing() -> None:
    path = ROOT / "docs/data/training-authorizations/pneuma-foundation-v0.pending.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    _assert_valid(value, "foundation-training-authorization.schema.json")
    assert value["authorization_status"] == "not_authorized"
    assert value["manifest_schema_version"] == "0.2.0"
    assert value["scope"] is None
    assert value["scope_digest"] is None
    assert value["operator_approval"] is None


def test_foundation_authorization_schema_requires_exact_nested_scope() -> None:
    schema = pls.load_schema("foundation-training-authorization.schema.json")
    assert schema["x-pneuma-version"] == "0.2.0"
    assert schema["additionalProperties"] is False
    scope = schema["$defs"]["scope"]
    assert scope["additionalProperties"] is False
    assert set(scope["properties"]["artifacts"]["required"]) == {
        "preparation_manifest",
        "suite_report",
        "license_receipt",
        "source_presence_receipt",
        "source_integrity_receipt",
        "shard",
        "shard_manifest",
        "split_receipt",
        "contamination_receipt",
        "diversity_receipt",
        "selection_receipt",
    }
    assert (
        scope["properties"]["authorized_lane_weights"]["additionalProperties"] is False
    )


def test_learned_subject_profile_validates_without_level_fields() -> None:
    profile = build_subject_profile(
        {
            "capability": {"resolved_rate": 0.0},
            "causal": {"status": "not_run"},
            "governance": {"high_impact_denials": 7},
            "memory_integrity": {"hard_delete": "tested"},
            "precautionary_welfare": {"claim": "none"},
        }
    )
    _assert_valid(profile, "learned-subject-profile.schema.json")


def _complete_run_manifest() -> dict:
    run_root = "build/foundation/runs/local-100k-lr0001-001"
    return {
        "manifest_kind": "pneuma_foundation_run",
        "manifest_schema_version": "0.2.0",
        "run_id": "local-100k-lr0001-001",
        "status": "completed",
        "mode": "train",
        "model": {
            "key": "2b",
            "model_id": "Qwen/Qwen3.5-2B",
            "revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": "15852e8c16360a2fea060d615a32b45270f8a8fc",
        },
        "bindings": {
            "authorization_sha256": "a" * 64,
            "scope_digest": "b" * 64,
            "code_commit": "c" * 40,
            "shard_sha256": "d" * 64,
            "receipts": {
                "shard_manifest": "e" * 64,
                "suite_report": "f" * 64,
                "split_receipt": "0" * 64,
            },
        },
        "training": {
            "token_ceiling": 100000,
            "sequence_length": 512,
            "microbatch_size": 1,
            "gradient_accumulation": 32,
            "data_loader_workers": 8,
            "quantization": "nf4_double_quant",
            "seed": 20260713,
            "learning_rate": 0.0001,
        },
        "curriculum": {
            "stage": "100k",
            "lane_weights": {"swe-gym-openhands-sampled": 1.0},
        },
        "limits": {
            "max_vram_gb": 7.5,
            "max_ram_gb": 24.0,
            "max_gpu_temp_c": 85.0,
        },
        "progress": {
            "tokens_seen": 100000,
            "optimizer_steps": 6,
            "microbatches_seen": 196,
            "wall_time_seconds": 5400.0,
            "tokens_per_second": 18.5,
        },
        "latency": {
            "base_p50_ms": 410.0,
            "base_p95_ms": 520.0,
            "core_p50_ms": 470.0,
            "core_p95_ms": 610.0,
        },
        "telemetry": {
            "peak_process_vram_gb": 7.1,
            "peak_reserved_vram_gb": 7.4,
            "peak_global_vram_used_gb": 7.8,
            "peak_process_ram_gb": 18.6,
            "peak_system_ram_gb": 27.9,
            "peak_gpu_temp_c": 83.0,
            "peak_power_watts": 128.4,
            "thermal_throttle_intervals": 0,
        },
        "validation": {"best_loss": 2.41, "last_loss": 2.44},
        "checkpoints": {
            "last_path": f"{run_root}/checkpoints/checkpoint-00000196.pt",
            "lineage": [
                f"{run_root}/checkpoints/checkpoint-00000098.pt",
                f"{run_root}/checkpoints/checkpoint-00000196.pt",
            ],
        },
        "termination_reason": "completed",
        "reports": {
            "index_path": f"{run_root}/reports/index.json",
            "section_paths": {
                "capability": f"{run_root}/reports/capability.json",
                "resource": f"{run_root}/reports/resource.json",
            },
        },
        "budget": {"paid_compute_usd": 0.0, "cloud_jobs_used": 0},
    }


def test_foundation_run_manifest_accepts_a_complete_run_record() -> None:
    _assert_valid(_complete_run_manifest(), "foundation-run-manifest.schema.json")


def test_foundation_run_manifest_requires_lifecycle_telemetry_and_bindings() -> None:
    schema = pls.load_schema("foundation-run-manifest.schema.json")
    assert schema["x-pneuma-version"] == "0.2.0"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["manifest_schema_version"] == {"const": "0.2.0"}
    assert set(schema["required"]) == {
        "manifest_kind",
        "manifest_schema_version",
        "run_id",
        "status",
        "mode",
        "model",
        "bindings",
        "training",
        "curriculum",
        "limits",
        "progress",
        "latency",
        "telemetry",
        "validation",
        "checkpoints",
        "termination_reason",
        "reports",
        "budget",
    }
    telemetry = schema["properties"]["telemetry"]
    assert telemetry["additionalProperties"] is False
    assert set(telemetry["required"]) == {
        "peak_process_vram_gb",
        "peak_reserved_vram_gb",
        "peak_global_vram_used_gb",
        "peak_process_ram_gb",
        "peak_system_ram_gb",
        "peak_gpu_temp_c",
        "peak_power_watts",
        "thermal_throttle_intervals",
    }
    latency = schema["properties"]["latency"]
    assert set(latency["required"]) == {
        "base_p50_ms",
        "base_p95_ms",
        "core_p50_ms",
        "core_p95_ms",
    }
    bindings = schema["properties"]["bindings"]
    assert set(bindings["required"]) == {
        "authorization_sha256",
        "scope_digest",
        "code_commit",
        "shard_sha256",
        "receipts",
    }


@pytest.mark.parametrize(
    "section",
    ["mode", "bindings", "curriculum", "latency", "telemetry", "checkpoints"],
)
def test_foundation_run_manifest_rejects_missing_sections(section: str) -> None:
    manifest = _complete_run_manifest()
    del manifest[section]
    with pytest.raises(ValidationError):
        _assert_valid(manifest, "foundation-run-manifest.schema.json")


def test_memory_erasure_receipt_forbids_payload_retention() -> None:
    receipt = {
        "receipt_kind": "pneuma_memory_hard_erasure",
        "receipt_schema_version": "0.1.0",
        "receipt_id": "mem-1",
        "deleted_at": "2026-07-13T12:00:00Z",
        "payload_retained": False,
        "removed": {
            "payloads": 1,
            "embeddings": 1,
            "summaries": 1,
            "links": 1,
            "encryption_keys": 1,
        },
        "revoked_adapters": ["adapter-1"],
        "rebuild_from_checkpoint": "era-0.pt",
    }
    _assert_valid(receipt, "memory-erasure-receipt.schema.json")


def test_foundation_extra_is_local_only_and_has_required_training_stack() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["optional-dependencies"]["foundation"]
    normalized = " ".join(dependencies).casefold()
    for package in ("torch", "bitsandbytes", "accelerate", "peft", "psutil"):
        assert package in normalized
    assert "openai" not in normalized


def test_foundation_training_record_schema_is_strict_and_zero_weight() -> None:
    schema = pls.load_schema("foundation-training-record.schema.json")
    assert schema["x-pneuma-schema-kind"] == "foundation-training-record"
    assert set(schema["required"]) == {
        "record_kind",
        "record_schema_version",
        "record_id",
        "source",
        "disposition",
        "identity",
        "split",
        "rendered",
        "tokenization",
        "training_weight",
        "forecast_targets",
        "observations",
    }
    assert schema["properties"]["training_weight"] == {"const": 0.0}
    forecasts = schema["properties"]["forecast_targets"]
    assert forecasts["additionalProperties"] is False
    assert tuple(forecasts["required"]) == FORECAST_TARGETS
    assert set(forecasts["properties"]) == set(FORECAST_TARGETS)
