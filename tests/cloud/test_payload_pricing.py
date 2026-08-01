from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.payload_pricing import build_payload_pricing_receipt, validate_payload_pricing_semantics


ROOT = Path(__file__).resolve().parents[2]
OFFER = ROOT / "docs/research/neurips-2026-workshop/evidence/aws-s3-us-east-1-price-list-20260728.json"
MANIFEST = ROOT / "docs/research/neurips-2026-workshop/evidence/step5b-payload-retrieval-manifest-20260801.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_official_offer_recomputes_worst_case_below_ceiling() -> None:
    receipt = build_payload_pricing_receipt(OFFER.read_bytes(), _manifest())
    assert receipt["rates_usd"]["standard_gb_month"] == "0.0230000000"
    assert receipt["request_ceilings"] == {"tier1_put": 5542, "tier1_list": 3410, "tier2_get": 13640}
    assert receipt["projected_cost_usd"] == "3.78"
    assert receipt["within_ceiling"] is True


def test_cost_and_binding_cannot_be_asserted() -> None:
    receipt = build_payload_pricing_receipt(OFFER.read_bytes(), _manifest())
    receipt["projected_cost_usd"] = "0.01"
    with pytest.raises(CloudManifestError, match="recomputed cost"):
        validate_payload_pricing_semantics(receipt, _manifest())
