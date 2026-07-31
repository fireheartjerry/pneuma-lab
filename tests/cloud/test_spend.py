import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.spend import SpendState, reserve, settle


def state() -> SpendState:
    return SpendState("aws", 100.0, 10.0, 20.0, 10.0, 20.0, 50.0)


def test_reservation_must_clear_both_invariants() -> None:
    assert reserve(state(), 20.0).provider_reserved == 40.0
    with pytest.raises(CloudManifestError): reserve(state(), 21.0)
    with pytest.raises(CloudManifestError): reserve(state(), 71.0)


def test_unreserved_settlement_is_rejected() -> None:
    with pytest.raises(CloudManifestError): settle(state(), 21.0)
