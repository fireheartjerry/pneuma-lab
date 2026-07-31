import pytest

from pneuma_lab.cloud.emulation import exercise_t1_fault_matrix
from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.fakes import LocalControlPlane


def test_t1_fault_matrix_is_labelled_local_only() -> None:
    assert exercise_t1_fault_matrix() == ("t1_local_only", "duplicate_delivery_blocked", "expired_lease_blocked", "teardown_ordered")


def test_corrupt_output_and_post_teardown_work_fail_closed() -> None:
    plane = LocalControlPlane(); plane.submit("one")
    with pytest.raises(CloudManifestError): plane.publish("one", b"bad", b"ok")
    plane.teardown()
    with pytest.raises(CloudManifestError): plane.submit("two")
