"""Strict validation of fixture-only cloud input and experiment manifests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from pneuma_lab import schemas

from .errors import CloudManifestError


_SCHEMA_BY_KIND = {
    "cloud_input_lock": "cloud-input-lock.schema.json",
    "cloud_experiment_manifest": "cloud-experiment-manifest.schema.json",
    "cloud_architecture_manifest": "cloud-architecture-manifest.schema.json",
    "cloud_image_manifest": "cloud-image-manifest.schema.json",
    "cloud_job_lease": "cloud-job-lease.schema.json",
    "cloud_spend_authorization": "cloud-spend-authorization.schema.json",
    "cloud_approval_receipt": "cloud-approval-receipt.schema.json",
    "cloud_result_binding": "cloud-result-binding.schema.json",
    "cloud_pilot_protocol": "cloud-pilot-protocol.schema.json",
    "cloud_interruption_qualification_receipt": "cloud-interruption-qualification-receipt.schema.json",
    "cloud_production_execution_surface": "cloud-production-execution-surface.schema.json",
    "cloud_retrieval_authorization": "cloud-retrieval-authorization.schema.json",
    "cloud_qualification_audit": "cloud-qualification-audit.schema.json",
    "cloud_worker_admission_measurement": "cloud-worker-admission-measurement.schema.json",
    "cloud_pilot_admission_receipt": "cloud-pilot-admission-receipt.schema.json",
    "cloud_image_build_receipt": "cloud-image-build-receipt.schema.json",
    "cloud_aws_account_verification": "cloud-aws-account-verification.schema.json",
    "cloud_approver_key_registry": "cloud-approver-key-registry.schema.json",
    "cloud_licence_audit": "cloud-licence-audit.schema.json",
    "cloud_unattended_spend_policy": "cloud-unattended-spend-policy.schema.json",
    "cloud_preparation_envelope": "cloud-preparation-envelope.schema.json",
    "cloud_preparation_admission": "cloud-preparation-admission.schema.json",
    "cloud_input_inventory_plan": "cloud-input-inventory-plan.schema.json",
    "cloud_payload_retrieval_manifest": "cloud-payload-retrieval-manifest.schema.json",
    "cloud_payload_retrieval_plan": "cloud-payload-retrieval-plan.schema.json",
    "cloud_payload_pricing_receipt": "cloud-payload-pricing-receipt.schema.json",
    "cloud_payload_mirror_receipt": "cloud-payload-mirror-receipt.schema.json",
    "cloud_step5b_lifecycle_receipt": "cloud-step5b-lifecycle-receipt.schema.json",
    "cloud_isolation_qualification_receipt": "cloud-isolation-qualification-receipt.schema.json",
    "cloud_production_role_receipt": "cloud-production-role-receipt.schema.json",
    "cloud_production_run_spec": "cloud-production-run-spec.schema.json",
    "cloud_production_worker_evidence": "cloud-production-worker-evidence.schema.json",
    "cloud_production_raw_worker_output": "cloud-production-raw-worker-output.schema.json",
    "cloud_production_controller_state": "cloud-production-controller-state.schema.json",
    "cloud_production_provider_binding": "cloud-production-provider-binding.schema.json",
    "cloud_production_image_receipt": "cloud-production-image-receipt.schema.json",
    "cloud_production_surface_e2e_receipt": "cloud-production-surface-e2e-receipt.schema.json",
    "cloud_registered_benchmark_adapter_manifest": "cloud-registered-benchmark-adapter-manifest.schema.json",
    "cloud_official_roster_candidate": "cloud-official-roster-candidate.schema.json",
    "cloud_official_assignment_pending": "cloud-official-assignment-pending.schema.json",
    "cloud_official_rng_commitment": "cloud-official-rng-commitment.schema.json",
    "cloud_official_analysis_graph": "cloud-official-analysis-graph.schema.json",
    "cloud_official_input_package": "cloud-official-input-package.schema.json",
    "cloud_official_study_authorization": "cloud-official-study-authorization.schema.json",
    "cloud_lease_contention_qualification_receipt": "cloud-lease-contention-qualification-receipt.schema.json",
    "cloud_lease_contention_cleanup_receipt": "cloud-lease-contention-cleanup-receipt.schema.json",
    "cloud_batch_array_qualification_receipt": "cloud-batch-array-qualification-receipt.schema.json",
    "cloud_ephemeral_dual_worker_qualification_receipt": "cloud-ephemeral-dual-worker-qualification-receipt.schema.json",
}


def _validate(record: Mapping[str, Any], *, expected_kind: str) -> dict[str, Any]:
    if not isinstance(record, Mapping) or record.get("record_kind") != expected_kind:
        raise CloudManifestError(f"record_kind must be {expected_kind!r}")
    schema = schemas.load_schema(_SCHEMA_BY_KIND[expected_kind])
    errors = sorted(Draft202012Validator(schema).iter_errors(dict(record)), key=str)
    if errors:
        raise CloudManifestError(errors[0].message)
    return dict(record)


def validate_input_lock(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a local fixture input lock without retrieving any input."""

    return _validate(record, expected_kind="cloud_input_lock")


def validate_payload_retrieval_manifest(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a metadata-derived payload manifest without authorizing it."""

    return _validate(record, expected_kind="cloud_payload_retrieval_manifest")


def validate_payload_retrieval_plan(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one unsigned or price-qualified payload action plan."""

    return _validate(record, expected_kind="cloud_payload_retrieval_plan")


def validate_payload_pricing_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_payload_pricing_receipt")


def validate_payload_mirror_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_payload_mirror_receipt")


def validate_step5b_lifecycle_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_step5b_lifecycle_receipt")


def validate_interruption_qualification_receipt(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_interruption_qualification_receipt")


def validate_production_execution_surface(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_production_execution_surface")


def validate_lease_contention_qualification_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a real DynamoDB contention receipt without promoting science."""

    return _validate(record, expected_kind="cloud_lease_contention_qualification_receipt")


def validate_lease_contention_cleanup_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate exact cleanup evidence without promoting a scientific result."""

    return _validate(record, expected_kind="cloud_lease_contention_cleanup_receipt")


def validate_batch_array_qualification_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate real Batch array evidence without promoting it to science."""

    return _validate(record, expected_kind="cloud_batch_array_qualification_receipt")


def validate_ephemeral_dual_worker_qualification_receipt(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the terminal receipt for the fixed two-worker fixture lane."""

    return _validate(
        record,
        expected_kind="cloud_ephemeral_dual_worker_qualification_receipt",
    )


def validate_production_role_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one role hand-off receipt without promoting it to science."""

    return _validate(record, expected_kind="cloud_production_role_receipt")


def validate_production_run_spec(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a production run binding without authorizing its execution."""

    return _validate(record, expected_kind="cloud_production_run_spec")


def validate_production_worker_evidence(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate raw worker evidence before any separate scientific admission."""

    return _validate(record, expected_kind="cloud_production_worker_evidence")


def validate_production_raw_worker_output(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate raw worker payload shape without interpreting scientific outcomes."""

    return _validate(record, expected_kind="cloud_production_raw_worker_output")


def validate_production_controller_state(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate durable production state without treating it as execution proof."""

    return _validate(record, expected_kind="cloud_production_controller_state")


def validate_production_provider_binding(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the concrete provider binding without authorizing a launch."""

    return _validate(record, expected_kind="cloud_production_provider_binding")


def validate_production_image_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_production_image_receipt")


def validate_production_surface_e2e_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_production_surface_e2e_receipt")


def validate_registered_benchmark_adapter_manifest(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_registered_benchmark_adapter_manifest")


def validate_official_roster_candidate(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_official_roster_candidate")


def validate_official_assignment_pending(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_official_assignment_pending")


def validate_official_rng_commitment(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_official_rng_commitment")


def validate_official_analysis_graph(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_official_analysis_graph")


def validate_official_input_package(record: Mapping[str, Any]) -> dict[str, Any]:
    return _validate(record, expected_kind="cloud_official_input_package")


def validate_official_study_authorization(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the separate official-study authority shape."""

    return _validate(record, expected_kind="cloud_official_study_authorization")


def validate_experiment_manifest(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an unpromoted experiment manifest bound to an input-lock digest."""

    return _validate(record, expected_kind="cloud_experiment_manifest")


def validate_worker_admission_measurement(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one raw worker measurement before it is compiled to a receipt."""

    return _validate(record, expected_kind="cloud_worker_admission_measurement")


def validate_pilot_admission_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a recorded per-worker admission measurement without promotion.

    A gate verdict is stored beside the counts it rests on, so the two can
    disagree. They must not: a receipt claiming `tool_call: true` while its own
    measurements record 3 of 4 cases passing is not a weaker pass, it is an
    incoherent record, and admitting one would let a failed gate be reported as
    a clean one. The p10-throughput gate is checked the same way against the
    frozen protocol threshold in `pilot.require_p10_gate_consistency`.

    Only the count-bearing gates are recomputed here. `oom` rests on
    `peak_gpu_memory_gib` against a device capacity the schema already bounds,
    and is checked where that capacity is known rather than asserted twice.
    """

    receipt = _validate(record, expected_kind="cloud_pilot_admission_receipt")
    gates = receipt["gates"]
    measurements = receipt["measurements"]
    for gate, label in (("tool_call", "tool-call gate"), ("output_parity", "output-parity gate")):
        cases = int(measurements[f"{gate}_cases"])
        passes = int(measurements[f"{gate}_passes"])
        if passes > cases:
            raise CloudManifestError(f"{label} records more passes than cases")
        if gates[gate] != (passes == cases):
            raise CloudManifestError(f"{label} contradicts its own measurements ({passes}/{cases})")
    return receipt
