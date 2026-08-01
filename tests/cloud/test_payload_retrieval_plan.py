from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.payload_retrieval_plan import (
    build_payload_retrieval_plan,
    validate_payload_retrieval_plan_semantics,
)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-payload-retrieval-manifest-20260801.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_candidate_is_exact_bounded_and_authorizes_nothing() -> None:
    plan = build_payload_retrieval_plan(_manifest())
    assert plan["status"] == "candidate"
    assert plan["pricing_receipt_sha256"] is None
    assert plan["retrieval_object_count"] == 1705
    assert plan["retrieval_byte_ceiling_bytes"] == 67483211374
    assert plan["cost_ceiling_usd"] == 5.0
    assert plan["destination"]["prefix"].endswith(plan["payload_manifest_sha256"])


def test_ready_state_requires_a_pricing_receipt() -> None:
    plan = build_payload_retrieval_plan(_manifest(), pricing_receipt_sha256="a" * 64)
    assert plan["status"] == "ready_for_signature"
    plan["pricing_receipt_sha256"] = None
    with pytest.raises(CloudManifestError, match="price-receipted"):
        validate_payload_retrieval_plan_semantics(plan, _manifest())


@pytest.mark.parametrize("field", ["payload_manifest_sha256", "inventory_receipt_sha256", "retrieval_object_count", "retrieval_byte_ceiling_bytes"])
def test_manifest_bindings_are_recomputed(field: str) -> None:
    plan = build_payload_retrieval_plan(_manifest())
    plan[field] = plan[field] + 1 if isinstance(plan[field], int) else "0" * 64
    with pytest.raises(CloudManifestError, match=field):
        validate_payload_retrieval_plan_semantics(plan, _manifest())


def test_network_and_execution_boundaries_are_exact() -> None:
    plan = build_payload_retrieval_plan(_manifest())
    plan["allowed_hosts"].append("example.com")
    with pytest.raises(CloudManifestError, match="boundary"):
        validate_payload_retrieval_plan_semantics(plan, _manifest())
