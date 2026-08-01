"""Verify the live lifecycle precondition bound into payload authority."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError
from .manifests import validate_step5b_lifecycle_receipt


EXPECTED_RULES = [
    {"id": "expire-experiment-artifacts", "status": "Enabled", "prefix": "runs/", "expiration_days": 365, "noncurrent_days": 30, "abort_days": 7},
    {"id": "expire-step5b-payloads", "status": "Enabled", "prefix": "runs/step5b/payloads/", "expiration_days": 35, "noncurrent_days": 30, "abort_days": 7},
]


def validate_step5b_lifecycle_semantics(record: Mapping[str, Any], payload_plan: Mapping[str, Any]) -> dict[str, Any]:
    receipt = validate_step5b_lifecycle_receipt(record)
    if receipt["terraform_plan_sha256"] != payload_plan["lifecycle_terraform_plan_sha256"]:
        raise CloudManifestError("lifecycle receipt is not bound to the approved Terraform plan")
    if receipt["rules"] != EXPECTED_RULES:
        raise CloudManifestError("lifecycle receipt does not prove the exact 365/30/7 and 35/30/7 rules")
    return receipt


def step5b_lifecycle_receipt_digest(record: Mapping[str, Any], payload_plan: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(validate_step5b_lifecycle_semantics(record, payload_plan)) + b"\n").hexdigest()
