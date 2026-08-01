"""Fail-closed verification for C120 Linux sandbox-isolation evidence."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .authorization_keys import canonical_bytes
from .errors import CloudManifestError
from .manifests import _validate


REGISTERED_SPLITS = {
    "swe": ("c", "cpp", "cs", "go", "java", "js", "rust", "ts"),
    "tau2": ("airline", "telecom", "banking"),
}
REQUIRED_PAIRS = 3
REQUIRED_ASSERTIONS = (
    "immutable_image_digest",
    "linux_amd64",
    "network_none",
    "capabilities_dropped",
    "no_new_privileges",
    "fresh_pair_clean",
    "a_marker_absent_from_b",
    "b_marker_absent_from_a",
    "recreated_a_clean",
)


def isolation_receipt_digest(record: Mapping[str, Any]) -> str:
    """Return the canonical digest of one validated receipt."""

    return hashlib.sha256(canonical_bytes(validate_isolation_receipt(record))).hexdigest()


def validate_isolation_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate coverage and every independently observed isolation invariant."""

    receipt = _validate(record, expected_kind="cloud_isolation_qualification_receipt")
    if receipt["tier"] != "C120":
        raise CloudManifestError("the registered isolation action qualifies C120 only")
    if receipt["host"]["os"] != "linux" or receipt["host"]["architecture"] != "x86_64":
        raise CloudManifestError("G-ROSTER isolation must run on Linux x86_64")
    if receipt["input_lock_sha256"] != receipt["case_manifest"]["input_lock_sha256"]:
        raise CloudManifestError("isolation receipt and case manifest bind different input locks")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for pair in receipt["pairs"]:
        family, split = pair["family"], pair["split"]
        if split not in REGISTERED_SPLITS.get(family, ()):
            raise CloudManifestError(f"unregistered isolation split: {family}/{split}")
        grouped[(family, split)].append(pair)
        failed = [name for name in REQUIRED_ASSERTIONS if pair["assertions"].get(name) is not True]
        if failed:
            raise CloudManifestError(
                f"isolation pair {pair['pair_id']!r} failed: {', '.join(failed)}"
            )

    expected = {(family, split) for family, splits in REGISTERED_SPLITS.items() for split in splits}
    if set(grouped) != expected:
        missing = sorted(expected - set(grouped))
        extra = sorted(set(grouped) - expected)
        raise CloudManifestError(f"isolation split coverage mismatch; missing={missing}, extra={extra}")
    pair_ids = [pair["pair_id"] for pair in receipt["pairs"]]
    if any(count != 1 for count in Counter(pair_ids).values()):
        raise CloudManifestError("isolation pair IDs must be globally unique")
    for key, pairs in grouped.items():
        if len(pairs) != REQUIRED_PAIRS:
            raise CloudManifestError(f"{key[0]}/{key[1]} requires exactly three isolation pairs")
        if len({pair["unit_id"] for pair in pairs}) != REQUIRED_PAIRS:
            raise CloudManifestError(f"{key[0]}/{key[1]} isolation pairs must use distinct units")
    return receipt


def require_isolation_receipt(
    record: Mapping[str, Any], *, expected_case_manifest_sha256: str, expected_input_lock_sha256: str
) -> dict[str, Any]:
    """Require exact precommitted ancestry, not merely an internally valid receipt."""

    receipt = validate_isolation_receipt(record)
    if receipt["case_manifest"]["sha256"] != expected_case_manifest_sha256:
        raise CloudManifestError("isolation receipt does not bind the frozen case manifest")
    if receipt["input_lock_sha256"] != expected_input_lock_sha256:
        raise CloudManifestError("isolation receipt does not bind the real input lock")
    return receipt


def case_manifest_digest(cases: Sequence[Mapping[str, Any]], input_lock_sha256: str) -> str:
    """Bind ordered cases and the real input lock before provider execution."""

    return hashlib.sha256(canonical_bytes({"input_lock_sha256": input_lock_sha256, "cases": list(cases)})).hexdigest()
