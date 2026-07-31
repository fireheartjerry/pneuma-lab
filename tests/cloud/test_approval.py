import pytest

from pneuma_lab.cloud.approval import approval_digest, verify_receipt
from pneuma_lab.cloud.errors import CloudManifestError


def test_receipt_binds_exact_manifest_bytes() -> None:
    auth = {"manifest_sha256": "a" * 64, "approval_id": "fixture"}
    receipt = {"authorization_sha256": approval_digest(auth), "manifest_sha256": "a" * 64}
    verify_receipt(auth, receipt, "a" * 64)
    with pytest.raises(CloudManifestError): verify_receipt(auth, receipt, "b" * 64)
