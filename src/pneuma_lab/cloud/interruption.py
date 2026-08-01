"""Independent verification for the AWS lease-expiry interruption drill."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .errors import CloudManifestError
from .manifests import validate_interruption_qualification_receipt


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def require_interruption_qualification(record: Mapping[str, Any]) -> dict[str, Any]:
    receipt = validate_interruption_qualification_receipt(record)
    gates = receipt["gates"]
    independent = receipt["controller_identity_arn"] != receipt["watcher_identity_arn"]
    if gates["independent_watcher"] != independent or not independent:
        raise CloudManifestError("watcher must be independent from the controller")
    lease = receipt["lease"]
    expired = _instant(lease["watcher_observed_timestamp"]) >= _instant(
        lease["expires_timestamp"]
    ) > _instant(lease["issued_timestamp"])
    if gates["lease_expired"] != expired or not expired:
        raise CloudManifestError("watcher termination was not observed after lease expiry")
    no_renewal = lease["controller_renewal_count"] == 0
    if gates["controller_could_not_renew"] != no_renewal or not no_renewal:
        raise CloudManifestError("controller renewed its own lease")
    boundary = receipt["boundary"]
    exact = (
        boundary["pre_interrupt_sha256"] == boundary["restored_sha256"]
        and boundary["all_arm_visible_bytes_match"]
    )
    if gates["boundary_exact"] != exact or not exact:
        raise CloudManifestError("completed-boundary restoration is not byte exact")
    resource_ids = [item["resource_id"] for item in receipt["resources"]]
    if len(resource_ids) != len(set(resource_ids)):
        raise CloudManifestError("interruption receipt repeats a resource id")
    absent = not receipt["residual_resource_ids"] and all(
        item["state_after"] == "absent" for item in receipt["resources"]
    )
    if gates["all_tagged_resources_absent"] != absent or not absent:
        raise CloudManifestError("tagged resources remain after the watcher drill")
    if not all(gates.values()):
        raise CloudManifestError("interruption qualification has a failing gate")
    return receipt
