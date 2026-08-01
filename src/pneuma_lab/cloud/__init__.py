"""Fail-closed local contracts for unexecuted cloud experiment preparation."""

from .inputs import build_retrieval_plan, verify_input_lock
from .manifests import validate_experiment_manifest, validate_input_lock
from .qualification import (
    evaluate_roster_gate,
    require_roster_gate_satisfied,
    validate_qualification_audit,
)
from .retrieval import (
    authorization_binding_digest,
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

__all__ = [
    "authorization_binding_digest",
    "admit_unattended_job",
    "build_audit_plan",
    "build_receipt_verification_plan",
    "build_retrieval_plan",
    "evaluate_roster_gate",
    "missing_scopes",
    "policy_digest",
    "readable_policy_summary",
    "require_authorized",
    "require_complete_scopes",
    "require_roster_gate_satisfied",
    "retrieve_and_verify",
    "validate_experiment_manifest",
    "validate_input_lock",
    "validate_qualification_audit",
    "validate_retrieval_authorization",
    "validate_unattended_policy",
    "verify_input_lock",
    "verify_local_bytes",
    "verify_mirrored_file",
]
