"""Mockable, fail-closed runner for the ephemeral Batch qualification.

The provider client is an injected seam.  This module contains the ordering
and invariants, but performs no provider calls when imported or tested.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from .ephemeral_qualification import (
    MAX_RETRIES,
    MAX_WORKER_RUNTIME_MINUTES,
    TOTAL_COST_CEILING_USD,
    require_cost_ceiling,
    require_two_workers,
)
from .errors import CloudManifestError
from .preparation_admission import require_preparation_admission

QUALIFICATION_TAGS = {
    "QualificationPurpose": "dual-l40s-admission-only",
    "QualificationTopology": "two-g6e-2xlarge-l40s",
    "QualificationManagedBy": "pneuma-ephemeral-runner-v1",
}
EXPECTED_RESOURCE_ADDRESSES = frozenset(
    {
        "aws_batch_compute_environment.qualification",
        "aws_batch_job_queue.qualification",
        "aws_batch_job_definition.worker",
    }
)


class QualificationProvider(Protocol):
    def preflight(self, tags: Mapping[str, str]) -> Mapping[str, Any]: ...

    def submit_array(
        self, *, size: int, timeout_seconds: int, attempts: int, tags: Mapping[str, str]
    ) -> str: ...

    def collect_admission(self, parent_job_id: str) -> Mapping[str, Any]: ...

    def run_partition_recovery(self, parent_job_id: str) -> Mapping[str, Any]: ...

    def disable_and_drain(self, tags: Mapping[str, str]) -> None: ...

    def verify_absence(self, tags: Mapping[str, str]) -> Mapping[str, bool]: ...


class TerraformQualification(Protocol):
    def apply(self, *, lock_timeout: str, tags: Mapping[str, str]) -> None: ...

    def destroy(self, *, lock_timeout: str, tags: Mapping[str, str]) -> None: ...


@dataclass(frozen=True)
class RunnerConfig:
    action_id: str
    region: str
    expected_projected_cost_usd: float
    expected_max_retries: int = MAX_RETRIES
    lock_timeout: str = "60s"


def require_account_plan(plan: Mapping[str, Any]) -> None:
    """Accept only the three ephemeral resources and approved existing inputs."""

    changes = plan.get("resource_changes")
    if not isinstance(changes, Sequence) or isinstance(changes, (str, bytes)):
        raise CloudManifestError("account plan must expose resource_changes")
    observed = set()
    for change in changes:
        if (
            not isinstance(change, Mapping)
            or change.get("address") not in EXPECTED_RESOURCE_ADDRESSES
        ):
            raise CloudManifestError(
                "account plan creates a non-qualification resource"
            )
        actions = tuple(change.get("actions", ()))
        if actions != ("create",):
            raise CloudManifestError(
                "qualification account plan must contain only creates"
            )
        observed.add(change["address"])
    if observed != EXPECTED_RESOURCE_ADDRESSES or len(changes) != len(
        EXPECTED_RESOURCE_ADDRESSES
    ):
        raise CloudManifestError(
            "account plan must contain exactly three ephemeral Batch resources"
        )
    if plan.get("approved_existing_inputs") != {
        "roles": True,
        "subnets": True,
        "security_groups": True,
    }:
        raise CloudManifestError(
            "account plan must reference pre-existing approved role/subnet/security-group inputs"
        )


def terraform_mutation_commands(
    *, directory: str = "infra/terraform/qualification"
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return locked future mutation commands; lock disabling is forbidden."""

    prefix = ("terraform", f"-chdir={directory}")
    return (
        prefix + ("apply", "-input=false", "-auto-approve", "-lock-timeout=60s"),
        prefix + ("destroy", "-input=false", "-auto-approve", "-lock-timeout=60s"),
    )


def _require_evidence(receipt: Mapping[str, Any]) -> None:
    ids = require_two_workers(receipt.get("instance_ids", ()))
    evidence = receipt.get("raw_evidence")
    if not isinstance(evidence, Mapping) or set(evidence) != {0, 1}:
        raise CloudManifestError(
            "admission receipt must contain raw evidence for both workers"
        )
    if any(
        not isinstance(evidence[index], (bytes, bytearray)) or not evidence[index]
        for index in (0, 1)
    ):
        raise CloudManifestError("each worker must retain nonempty raw admission bytes")
    if len(set(ids)) != 2:
        raise CloudManifestError("worker identities must remain distinct")


def execute(
    config: RunnerConfig,
    *,
    envelope: Mapping[str, Any],
    admission: Mapping[str, Any],
    key_registry: Mapping[str, Any],
    ledger_path: Any,
    account_plan: Mapping[str, Any],
    provider: QualificationProvider,
    terraform: TerraformQualification,
    verify_authority: Callable[..., Any] = require_preparation_admission,
) -> Mapping[str, Any]:
    """Run the ordered qualification lifecycle through injected seams."""

    require_account_plan(account_plan)
    if config.expected_max_retries != MAX_RETRIES:
        raise CloudManifestError("qualification runner permits zero retries only")
    if config.expected_projected_cost_usd >= TOTAL_COST_CEILING_USD:
        raise CloudManifestError(
            "qualification projection must be strictly below USD 100"
        )
    require_cost_ceiling(projected_cost_usd=config.expected_projected_cost_usd)
    verify_authority(
        envelope,
        admission,
        key_registry=key_registry,
        ledger_path=ledger_path,
        expected_action_id=config.action_id,
        expected_action_class="qualification_audit",
        expected_provider="aws",
        expected_region=config.region,
        expected_manifest_sha256=account_plan["plan_sha256"],
        expected_input_lock_sha256=account_plan.get("input_lock_sha256"),
        expected_projected_cost_usd=config.expected_projected_cost_usd,
        expected_max_retries=MAX_RETRIES,
        spend_history_sha256=account_plan["spend_history_sha256"],
    )

    tags = dict(QUALIFICATION_TAGS)
    tags["QualificationAction"] = config.action_id
    provider.preflight(tags)
    parent_job_id: str | None = None
    failure: Exception | None = None
    cleanup_failure: Exception | None = None
    try:
        terraform.apply(lock_timeout=config.lock_timeout, tags=tags)
        parent_job_id = provider.submit_array(
            size=2,
            timeout_seconds=MAX_WORKER_RUNTIME_MINUTES * 60,
            attempts=1,
            tags=tags,
        )
        evidence = provider.collect_admission(parent_job_id)
        _require_evidence(evidence)
        recovery = provider.run_partition_recovery(parent_job_id)
        if recovery.get("restored_completed_boundary") is not True:
            raise CloudManifestError(
                "partition/interruption recovery boundary was not restored exactly"
            )
    except Exception as exc:
        failure = exc
    finally:
        try:
            provider.disable_and_drain(tags)
        except Exception as exc:
            cleanup_failure = exc
        try:
            terraform.destroy(lock_timeout=config.lock_timeout, tags=tags)
        except Exception as exc:
            cleanup_failure = cleanup_failure or exc
    absence = provider.verify_absence(tags)
    required_absence = {
        "jobs",
        "instances",
        "volumes",
        "job_definition",
        "queue",
        "compute_environment",
    }
    if set(absence) != required_absence or not all(absence.values()):
        raise CloudManifestError(
            "provider-side qualification teardown absence is incomplete"
        )
    if cleanup_failure is not None:
        raise CloudManifestError(
            "qualification teardown failed closed"
        ) from cleanup_failure
    if failure is not None:
        raise CloudManifestError("qualification failed closed") from failure
    return {"parent_job_id": parent_job_id, "tags": tags, "qualification_only": True}
