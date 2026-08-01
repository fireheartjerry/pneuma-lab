import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.preflight import require_quota, residuals, teardown_plan


def test_quota_preflight_refuses_zero_and_insufficient() -> None:
    with pytest.raises(CloudManifestError): require_quota(0)
    with pytest.raises(CloudManifestError): require_quota(7)
    require_quota(8)


def test_teardown_requires_owned_targets_and_is_byte_stable() -> None:
    ownership = {"jobs": ["job-1"], "buckets": ["bucket/prefix"]}
    first = teardown_plan(ownership, set(), {"job-1", "survivor"})
    assert first == teardown_plan(ownership, set(), {"job-1", "survivor"})
    assert residuals(ownership, {"job-1", "survivor"}) == ("survivor",)
    with pytest.raises(CloudManifestError): teardown_plan({}, set(), {"tag-only"})
    with pytest.raises(CloudManifestError): teardown_plan(ownership, {"job-1"}, set())
