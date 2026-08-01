"""Fail-closed helpers for one-GPU throughput qualification receipts."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any

from .errors import CloudManifestError


THROUGHPUT_SAMPLES_PER_RUNG = 10
OUTPUT_TOKENS_PER_SAMPLE = 128
WARMUP_SAMPLES_PER_RUNG = 1
P10_METHOD = "nearest_rank"


def nearest_rank_p10(samples: Iterable[float]) -> float:
    """Return the preregistered nearest-rank tenth percentile.

    Exactly ten observations are required, making the registered p10 the
    minimum observed steady-state throughput.  Warmups never enter this set.
    """

    values = list(samples)
    if len(values) != THROUGHPUT_SAMPLES_PER_RUNG:
        raise CloudManifestError(
            f"p10 requires exactly {THROUGHPUT_SAMPLES_PER_RUNG} measured samples"
        )
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise CloudManifestError("throughput samples must be numeric")
    if any(not math.isfinite(float(value)) or float(value) <= 0 for value in values):
        raise CloudManifestError("throughput samples must be finite and positive")
    ordered = sorted(float(value) for value in values)
    rank = math.ceil(0.10 * len(ordered))
    return ordered[rank - 1]


def require_throughput_observation(record: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute a raw observation rather than trusting its summary fields."""

    result = dict(record)
    if result.get("p10_method") != P10_METHOD:
        raise CloudManifestError("throughput receipt uses an unregistered p10 method")
    if result.get("warmup_samples") != WARMUP_SAMPLES_PER_RUNG:
        raise CloudManifestError("throughput receipt has the wrong warmup count")
    if result.get("output_tokens_per_sample") != OUTPUT_TOKENS_PER_SAMPLE:
        raise CloudManifestError("throughput receipt has the wrong token count")
    samples = result.get("output_tokens_per_second")
    if not isinstance(samples, list):
        raise CloudManifestError("throughput receipt lacks raw samples")
    computed = nearest_rank_p10(samples)
    reported = result.get("p10_output_tokens_per_second")
    if isinstance(reported, bool) or not isinstance(reported, (int, float)):
        raise CloudManifestError("throughput receipt lacks a numeric p10")
    if float(reported) != computed:
        raise CloudManifestError("reported p10 contradicts raw throughput samples")
    return result
