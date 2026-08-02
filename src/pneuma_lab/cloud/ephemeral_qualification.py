"""Fail-closed bounds for the ephemeral two-worker qualification path.

This module is deliberately provider-free.  It validates the package consumed
by the ephemeral Terraform stack and its watchdog; it never submits a job or
authorizes scientific work.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from .errors import CloudManifestError

WORKER_COUNT = 2
WORKER_INSTANCE_TYPE = "g6e.2xlarge"
WORKER_VCPUS = 8
WORKER_GPU_COUNT = 1
TOTAL_SPOT_VCPUS = 16
MAX_WORKER_RUNTIME_MINUTES = 60
TOTAL_COST_CEILING_USD = 100.0
MAX_RETRIES = 0
SPOT_ALLOCATION_STRATEGY = "SPOT_PRICE_CAPACITY_OPTIMIZED"


def validate_plan(plan: Mapping[str, object]) -> None:
    """Reject any plan that can exceed the qualification envelope."""

    expected = {
        "worker_count": WORKER_COUNT,
        "instance_type": WORKER_INSTANCE_TYPE,
        "worker_vcpus": WORKER_VCPUS,
        "worker_gpu_count": WORKER_GPU_COUNT,
        "total_spot_vcpus": TOTAL_SPOT_VCPUS,
        "max_runtime_minutes": MAX_WORKER_RUNTIME_MINUTES,
        "max_retries": MAX_RETRIES,
        "spot_allocation_strategy": SPOT_ALLOCATION_STRATEGY,
    }
    for key, value in expected.items():
        if plan.get(key) != value:
            raise CloudManifestError(f"qualification plan must bind {key}={value!r}")
    ceiling = plan.get("total_cost_ceiling_usd")
    if not isinstance(ceiling, (int, float)) or isinstance(ceiling, bool):
        raise CloudManifestError("qualification plan must bind a numeric cost ceiling")
    if float(ceiling) != TOTAL_COST_CEILING_USD:
        raise CloudManifestError(
            "qualification plan cost ceiling must be exactly USD 100"
        )
    if plan.get("qualification_only") is not True:
        raise CloudManifestError("qualification plan must be marked qualification-only")


def require_two_workers(instance_ids: Iterable[str]) -> tuple[str, str]:
    """Require exactly two distinct provider identities, preserving order."""

    ids = tuple(instance_ids)
    if len(ids) != WORKER_COUNT or any(
        not isinstance(value, str) or not value for value in ids
    ):
        raise CloudManifestError("qualification requires exactly two worker identities")
    if len(set(ids)) != WORKER_COUNT:
        raise CloudManifestError("qualification workers must have distinct identities")
    return ids  # type: ignore[return-value]


def require_watchdog(
    *, started_at: int, now: int, runtime_limit_seconds: int = 3600
) -> None:
    """Enforce the hard per-worker wall clock before each bounded action."""

    if runtime_limit_seconds != MAX_WORKER_RUNTIME_MINUTES * 60:
        raise CloudManifestError("watchdog runtime must be exactly 3600 seconds")
    if now < started_at or now - started_at >= runtime_limit_seconds:
        raise CloudManifestError("qualification watchdog expired; stop without retry")


def require_cost_ceiling(
    *, projected_cost_usd: float, observed_cost_usd: float = 0.0
) -> None:
    """Enforce the qualification ceiling independently of AWS Budget alarms."""

    if projected_cost_usd < 0 or observed_cost_usd < 0:
        raise CloudManifestError("qualification cost values must be non-negative")
    if max(projected_cost_usd, observed_cost_usd) > TOTAL_COST_CEILING_USD:
        raise CloudManifestError(
            "qualification cost ceiling exceeded; stop without retry"
        )


def require_teardown_complete(receipt: Mapping[str, object]) -> None:
    """Require an explicit post-teardown absence proof for every owned object."""

    if receipt.get("resources_absent") is not True or receipt.get(
        "provider_errors"
    ) not in (None, [], {}):
        raise CloudManifestError("qualification teardown is not proven complete")
