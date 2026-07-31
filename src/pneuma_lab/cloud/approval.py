"""Exact manifest-bound local approval checks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from .errors import CloudManifestError


def approval_digest(authorization: Mapping[str, object]) -> str:
    return hashlib.sha256(json.dumps(dict(authorization), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_receipt(authorization: Mapping[str, object], receipt: Mapping[str, object], manifest_sha256: str) -> None:
    if receipt.get("authorization_sha256") != approval_digest(authorization) or receipt.get("manifest_sha256") != manifest_sha256 or authorization.get("manifest_sha256") != manifest_sha256:
        raise CloudManifestError("approval receipt is not bound to exact authorization and manifest")
