import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.pilot import RUNG_NAMES, require_within_protocol, select_rung


def protocol() -> dict:
    return {"rungs": list(RUNG_NAMES), "max_cost_usd": 1.0, "max_runtime_minutes": 10, "max_retries": 1, "max_samples": 2}


def test_protocol_rejects_expansion_and_efficacy_selection() -> None:
    with pytest.raises(CloudManifestError): require_within_protocol(protocol(), cost=1.1, runtime=1, retries=0, samples=1)
    with pytest.raises(CloudManifestError): select_rung(protocol(), {RUNG_NAMES[0]: {"efficacy": True}})


def test_largest_passing_registered_rung_is_selected() -> None:
    gates = {"oom": True, "tool_call": True, "output_parity": True, "p10_throughput": True}
    assert select_rung(protocol(), {RUNG_NAMES[0]: gates, RUNG_NAMES[1]: gates}) == RUNG_NAMES[1]
