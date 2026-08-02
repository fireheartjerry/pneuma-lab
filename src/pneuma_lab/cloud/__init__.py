"""Fail-closed local contracts for unexecuted cloud experiment preparation."""

from .authorization_keys import (
    resolve_trusted_key,
    validate_key_registry,
    verify_ledger_binding,
    verify_signature,
)
from .batch_array import require_batch_array_qualification
from .aws_account import build_account_verification
from .admission_measurement import (
    OUTPUT_PARITY_FIXTURE_IDS,
    TOOL_CALL_FIXTURES,
    USABLE_GPU_MEMORY_BYTES,
    canonical_tool_call,
    require_l40s_runtime,
    summarize_rung,
)
from .iac import require_terraform_for_l1, terraform_status
from .input_lock import (
    build_candidate_input_lock,
    classify_input_lock,
    real_candidate_findings,
    require_real_candidate_lock,
)
from .inputs import build_retrieval_plan, verify_input_lock, verify_input_receipts
from .licence_audit import (
    derive_audit,
    validate_licence_audit,
    verify_licence_evidence,
)
from .lease_contention import require_lease_contention_cleanup, require_lease_contention_qualification
from .manifests import (
    validate_experiment_manifest,
    validate_input_lock,
    validate_lease_contention_cleanup_receipt,
    validate_lease_contention_qualification_receipt,
    validate_pilot_admission_receipt,
    validate_worker_admission_measurement,
)
from .qualification import (
    evaluate_roster_gate,
    require_roster_gate_satisfied,
    validate_qualification_audit,
)
from .preparation_admission import (
    envelope_digest,
    require_preparation_admission,
    validate_preparation_admission,
    validate_preparation_envelope,
)
from .portability import build_portability_bundle, roster_digest, verify_portability_bundle
from .retrieval import (
    authorization_body_digest,
    build_audit_plan,
    build_receipt_verification_plan,
    missing_scopes,
    require_authorized,
    require_complete_scopes,
    retrieve_and_verify,
    validate_retrieval_authorization,
    verify_local_bytes,
    verify_mirrored_file,
)
from .unattended_policy import (
    admit_unattended_job,
    policy_digest,
    readable_policy_summary,
    validate_unattended_policy,
)
from .worker_admission import (
    compile_dual_worker_admissions,
    compile_worker_admission,
    measurement_evidence_digest,
)

__all__ = [
    "admit_unattended_job",
    "authorization_body_digest",
    "canonical_tool_call",
    "build_account_verification",
    "require_batch_array_qualification",
    "build_audit_plan",
    "build_candidate_input_lock",
    "build_receipt_verification_plan",
    "build_retrieval_plan",
    "build_portability_bundle",
    "classify_input_lock",
    "compile_dual_worker_admissions",
    "compile_worker_admission",
    "derive_audit",
    "evaluate_roster_gate",
    "envelope_digest",
    "missing_scopes",
    "measurement_evidence_digest",
    "OUTPUT_PARITY_FIXTURE_IDS",
    "policy_digest",
    "readable_policy_summary",
    "real_candidate_findings",
    "require_authorized",
    "require_complete_scopes",
    "require_lease_contention_cleanup",
    "require_lease_contention_qualification",
    "require_l40s_runtime",
    "require_preparation_admission",
    "require_real_candidate_lock",
    "require_roster_gate_satisfied",
    "require_terraform_for_l1",
    "resolve_trusted_key",
    "roster_digest",
    "summarize_rung",
    "retrieve_and_verify",
    "terraform_status",
    "TOOL_CALL_FIXTURES",
    "USABLE_GPU_MEMORY_BYTES",
    "validate_experiment_manifest",
    "validate_input_lock",
    "validate_lease_contention_cleanup_receipt",
    "validate_lease_contention_qualification_receipt",
    "validate_batch_array_qualification_receipt",
    "validate_key_registry",
    "validate_licence_audit",
    "validate_pilot_admission_receipt",
    "validate_worker_admission_measurement",
    "validate_preparation_admission",
    "validate_preparation_envelope",
    "validate_qualification_audit",
    "validate_retrieval_authorization",
    "validate_unattended_policy",
    "verify_input_lock",
    "verify_input_receipts",
    "verify_ledger_binding",
    "verify_licence_evidence",
    "verify_local_bytes",
    "verify_portability_bundle",
    "verify_mirrored_file",
    "verify_signature",
]
