import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.pilot import (
    MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND,
    RUNG_NAMES,
    require_within_protocol,
    select_rung,
)


def protocol() -> dict:
    return {"rungs": list(RUNG_NAMES), "max_cost_usd": 1.0, "max_runtime_minutes": 10, "max_retries": 1, "max_samples": 20, "minimum_p10_output_tokens_per_second": MINIMUM_P10_OUTPUT_TOKENS_PER_SECOND, "throughput_samples_per_rung": 10, "output_tokens_per_sample": 128, "warmup_samples_per_rung": 1, "p10_method": "nearest_rank"}


def test_protocol_rejects_expansion_and_efficacy_selection() -> None:
    with pytest.raises(CloudManifestError):
        require_within_protocol(protocol(), cost=1.1, runtime=1, retries=0, samples=1)
    with pytest.raises(CloudManifestError):
        select_rung(protocol(), {RUNG_NAMES[0]: {"efficacy": True}})


def test_largest_passing_registered_rung_is_selected() -> None:
    gates = {"oom": True, "tool_call": True, "output_parity": True, "p10_throughput": True}
    assert select_rung(protocol(), {RUNG_NAMES[0]: gates, RUNG_NAMES[1]: gates}) == RUNG_NAMES[1]


def test_protocol_without_a_preregistered_throughput_floor_fails_closed() -> None:
    incomplete = protocol()
    incomplete.pop("minimum_p10_output_tokens_per_second")
    with pytest.raises(CloudManifestError, match="p10-throughput threshold"):
        require_within_protocol(incomplete, cost=1.0, runtime=1, retries=0, samples=1)


def test_protocol_cannot_substitute_a_different_p10_floor() -> None:
    altered = protocol()
    altered["minimum_p10_output_tokens_per_second"] = 7.99
    with pytest.raises(CloudManifestError, match="DL-165"):
        require_within_protocol(altered, cost=1.0, runtime=1, retries=0, samples=1)
