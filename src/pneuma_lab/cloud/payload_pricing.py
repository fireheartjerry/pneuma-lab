"""Extract and recompute the bounded Step 5B S3 price receipt."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from decimal import ROUND_CEILING, Decimal
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_payload_pricing_receipt
from .payload_inventory import payload_manifest_digest, validate_payload_manifest_semantics


PRICE_URL = "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonS3/current/us-east-1/index.json"
PART_SIZE = 64 * 1024 * 1024


def _rate(offer: Mapping[str, Any], usage_type: str, description: str) -> str:
    matches = []
    for sku, product in offer["products"].items():
        if product.get("attributes", {}).get("usagetype") != usage_type:
            continue
        for term in offer["terms"]["OnDemand"].get(sku, {}).values():
            for dimension in term["priceDimensions"].values():
                if description in dimension["description"]:
                    matches.append(dimension["pricePerUnit"]["USD"])
    if len(matches) != 1:
        raise CloudManifestError(f"official offer has {len(matches)} matching {usage_type} rates")
    return matches[0]


def build_payload_pricing_receipt(offer_bytes: bytes, manifest_record: Mapping[str, Any]) -> dict[str, Any]:
    try:
        offer = json.loads(offer_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CloudManifestError("AWS price-list source is not UTF-8 JSON") from exc
    manifest = validate_payload_manifest_semantics(manifest_record)
    rates = {
        "standard_gb_month": _rate(offer, "TimedStorage-ByteHrs", "first 50 TB"),
        "tier1_request": _rate(offer, "Requests-Tier1", "PUT, COPY, POST, or LIST"),
        "tier2_request": _rate(offer, "Requests-Tier2", "GET and all other requests"),
    }
    retrievable = [item for item in manifest["objects"] if item["retrieval_required"]]
    put_once = sum(math.ceil(item["size_bytes"] / PART_SIZE) + 2 if item["size_bytes"] > PART_SIZE else 1 for item in retrievable)
    # Two complete action attempts plus one final receipt PUT per attempt.
    requests = {"tier1_put": (put_once + 1) * 2, "tier1_list": len(retrievable) * 2, "tier2_get": len(retrievable) * 8}
    days = {"current": 35, "noncurrent_retry": 30, "abandoned_multipart": 7}
    gb = Decimal(manifest["retrieval_byte_ceiling_bytes"]) / Decimal(1_000_000_000)
    storage = gb * Decimal(sum(days.values())) / Decimal(30) * Decimal(rates["standard_gb_month"])
    request_cost = Decimal(requests["tier1_put"] + requests["tier1_list"]) * Decimal(rates["tier1_request"])
    request_cost += Decimal(requests["tier2_get"]) * Decimal(rates["tier2_request"])
    projected = (storage + request_cost).quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    record = {
        "record_kind": "cloud_payload_pricing_receipt", "schema_version": "0.1.0",
        "source": {"url": PRICE_URL, "sha256": hashlib.sha256(offer_bytes).hexdigest(), "size_bytes": len(offer_bytes), "publication_timestamp": offer["publicationDate"], "offer_version": offer["version"]},
        "region": "us-east-1", "payload_manifest_sha256": payload_manifest_digest(manifest),
        "payload_bytes": manifest["retrieval_byte_ceiling_bytes"], "multipart_part_size_bytes": PART_SIZE,
        "request_ceilings": requests, "billable_storage_days": days, "rates_usd": rates,
        "projected_cost_usd": f"{projected:.2f}", "cost_ceiling_usd": "5.00", "within_ceiling": projected <= Decimal("5.00"),
    }
    return validate_payload_pricing_semantics(record, manifest)


def validate_payload_pricing_semantics(record: Mapping[str, Any], manifest_record: Mapping[str, Any]) -> dict[str, Any]:
    receipt = validate_payload_pricing_receipt(record)
    manifest = validate_payload_manifest_semantics(manifest_record)
    if receipt["payload_manifest_sha256"] != payload_manifest_digest(manifest) or receipt["payload_bytes"] != manifest["retrieval_byte_ceiling_bytes"]:
        raise CloudManifestError("pricing receipt is not bound to the payload manifest")
    days = sum(receipt["billable_storage_days"].values())
    gb = Decimal(receipt["payload_bytes"]) / Decimal(1_000_000_000)
    cost = gb * Decimal(days) / Decimal(30) * Decimal(receipt["rates_usd"]["standard_gb_month"])
    ceilings = receipt["request_ceilings"]
    cost += Decimal(ceilings["tier1_put"] + ceilings["tier1_list"]) * Decimal(receipt["rates_usd"]["tier1_request"])
    cost += Decimal(ceilings["tier2_get"]) * Decimal(receipt["rates_usd"]["tier2_request"])
    projected = cost.quantize(Decimal("0.01"), rounding=ROUND_CEILING)
    if receipt["projected_cost_usd"] != f"{projected:.2f}" or receipt["within_ceiling"] != (projected <= Decimal(receipt["cost_ceiling_usd"])):
        raise CloudManifestError("pricing verdict contradicts the recomputed cost")
    return receipt
