from __future__ import annotations

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.throughput import nearest_rank_p10, require_throughput_observation


def observation() -> dict:
    samples = [8.9, 8.1, 8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2, 9.0]
    return {
        "p10_method": "nearest_rank",
        "warmup_samples": 1,
        "output_tokens_per_sample": 128,
        "output_tokens_per_second": samples,
        "p10_output_tokens_per_second": 8.1,
    }


def test_p10_is_the_minimum_of_exactly_ten_registered_samples() -> None:
    assert nearest_rank_p10(observation()["output_tokens_per_second"]) == 8.1


@pytest.mark.parametrize("count", [9, 11])
def test_p10_rejects_any_other_sample_count(count: int) -> None:
    with pytest.raises(CloudManifestError, match="exactly 10"):
        nearest_rank_p10([8.1] * count)


def test_observation_recomputes_reported_p10() -> None:
    record = observation()
    record["p10_output_tokens_per_second"] = 8.2
    with pytest.raises(CloudManifestError, match="contradicts"):
        require_throughput_observation(record)


def test_observation_rejects_warmup_or_token_count_drift() -> None:
    for field, value in (("warmup_samples", 0), ("output_tokens_per_sample", 127)):
        record = observation()
        record[field] = value
        with pytest.raises(CloudManifestError):
            require_throughput_observation(record)
