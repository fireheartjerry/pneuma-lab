import pytest

from pneuma_lab.cloud.binding import verify_binding
from pneuma_lab.cloud.errors import CloudManifestError


def test_image_or_lease_swap_fails_closed() -> None:
    binding = {"code_sha256": "a" * 64, "image_sha256": "b" * 64, "manifest_sha256": "c" * 64, "lease_id": "lease"}
    verify_binding(binding, code="a" * 64, image="b" * 64, manifest="c" * 64, lease_id="lease")
    with pytest.raises(CloudManifestError): verify_binding(binding, code="a" * 64, image="d" * 64, manifest="c" * 64, lease_id="lease")
