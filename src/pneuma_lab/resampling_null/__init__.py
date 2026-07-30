"""Zero-spend resampling-null experimental core."""

from __future__ import annotations

from types import MappingProxyType


__all__ = (
    "AttemptBoundZeroCostClosure",
    "AUTHORITY_ASSET_ROLE_MEDIA",
    "Arm",
    "AnalysisRow",
    "AnalysisConfig",
    "AnalysisResult",
    "ArtifactRef",
    "BinarySufficientStatistics",
    "BinarySufficientStatisticsBatch",
    "ContrastResult",
    "GateBatchResult",
    "GateResult",
    "AssignmentLedger",
    "AssignmentSecretHandle",
    "AssignmentSecretStore",
    "AssignmentMode",
    "BranchOutcome",
    "BranchCaps",
    "BranchSlot",
    "BranchSlotSet",
    "audit_and_seal_packet_index",
    "build_packet_pair",
    "CallSeedReceipt",
    "CompletedToolBoundaryReceipt",
    "CompositeSnapshotEnvelope",
    "ContextMessage",
    "ControllerArtifactResolver",
    "ControllerArtifactStore",
    "CONTROLLER_ROLE_MEDIA",
    "CostClosure",
    "derive_call_seed",
    "derive_packet_rewrite_artifacts",
    "derive_seed",
    "FrozenVerifierReceipt",
    "FrozenPrefixReceipt",
    "FailureKind",
    "EnvironmentProcessIdentity",
    "GroupKind",
    "GroupLabel",
    "GradeReceipt",
    "GradeEvidence",
    "GradeExecutionReceipt",
    "grade_execution_receipt_bytes",
    "IdentifierAtom",
    "IdentifierKind",
    "ImplementationDescriptor",
    "InitialRestoreQualificationReceipt",
    "initial_restore_qualification_receipt_bytes",
    "LiteralAtom",
    "MatchingAlgorithm",
    "NoInterventionPacketMarker",
    "normalize_synthetic_packet_findings",
    "load_synthetic_packet_authority",
    "PacketAuthority",
    "PacketInvalid",
    "PacketPairReceipt",
    "PacketPolicy",
    "PacketRewriteArtifacts",
    "OpaqueSlotIdentity",
    "OpaqueSlotWorkOrder",
    "PrefixCaps",
    "PrefixExecutionAuthority",
    "ProviderAttemptLedger",
    "ProviderAttemptStatus",
    "ProviderCallAttemptReceipt",
    "ProviderDispatchIntent",
    "ProviderSettlement",
    "RawProviderCompletionKind",
    "RawProviderObservation",
    "REF_LOAD_CLASS_BY_ROLE",
    "SyntheticPacketArtifactStore",
    "SyntheticZeroAttemptCostClosure",
    "SyntheticPrefixProgram",
    "SnapshotRestoreReceipt",
    "StableSourceProvenance",
    "ResourceCounters",
    "RandomizationResult",
    "ResolutionResult",
    "SecondaryFamilyResult",
    "SimultaneousBounds",
    "run_prefix",
    "CallContractCaps",
    "load_prefix_execution_authority",
    "load_initial_restore_qualification_receipt",
    "load_grade_execution_receipt",
    "load_prefix_candidate_receipt",
    "seal_prefix_index",
    "load_snapshot_restore_receipt",
    "load_verifier_execution_receipt",
    "load_synthetic_prefix_program",
    "prefix_candidate_receipt_bytes",
    "require_assignment_reconstruction",
    "require_assignment_publication",
    "require_confirmation_assignment",
    "seal_branch_assignment",
    "snapshot_restore_receipt_bytes",
    "SubjectContext",
    "SubjectTurn",
    "TaskAssignment",
    "TaskSchedule",
    "TaskSpec",
    "ToolBoundary",
    "ToolBoundaryLedger",
    "ToolCall",
    "Treatment",
    "TriggerReason",
    "UnblindSecretHandle",
    "Verdict",
    "VerifierFinding",
    "VerifierEvidence",
    "VerifierExecutionReceipt",
    "verifier_execution_receipt_bytes",
    "verify_result_bundle",
    "verify_synthetic_assignment_graph",
    "synthetic_prefix_program_bytes",
    "validate_prefix_candidate_ref",
    "write_packet_candidate",
    "analyze",
    "classify_verdict",
    "evaluate_binary_gate_batch",
    "evaluate_binary_gate_kernel",
    "rows_to_binary_sufficient_statistics",
)


_LAZY_EXPORTS = MappingProxyType({
    "AttemptBoundZeroCostClosure": ("evidence", "AttemptBoundZeroCostClosure"),
    "AUTHORITY_ASSET_ROLE_MEDIA": ("prefix_contracts", "AUTHORITY_ASSET_ROLE_MEDIA"),
    "Arm": ("types", "Arm"),
    "AnalysisRow": ("types", "AnalysisRow"),
    "AnalysisConfig": ("types", "AnalysisConfig"),
    "AnalysisResult": ("types", "AnalysisResult"),
    "ArtifactRef": ("types", "ArtifactRef"),
    "BinarySufficientStatistics": ("types", "BinarySufficientStatistics"),
    "BinarySufficientStatisticsBatch": ("types", "BinarySufficientStatisticsBatch"),
    "ContrastResult": ("types", "ContrastResult"),
    "GateBatchResult": ("types", "GateBatchResult"),
    "GateResult": ("types", "GateResult"),
    "AssignmentLedger": ("types", "AssignmentLedger"),
    "AssignmentSecretHandle": ("secrets", "AssignmentSecretHandle"),
    "AssignmentSecretStore": ("secrets", "AssignmentSecretStore"),
    "AssignmentMode": ("types", "AssignmentMode"),
    "BranchOutcome": ("types", "BranchOutcome"),
    "BranchCaps": ("types", "BranchCaps"),
    "BranchSlot": ("types", "BranchSlot"),
    "BranchSlotSet": ("types", "BranchSlotSet"),
    "audit_and_seal_packet_index": ("packets", "audit_and_seal_packet_index"),
    "build_packet_pair": ("packets", "build_packet_pair"),
    "CallSeedReceipt": ("types", "CallSeedReceipt"),
    "CompletedToolBoundaryReceipt": ("evidence", "CompletedToolBoundaryReceipt"),
    "CompositeSnapshotEnvelope": ("evidence", "CompositeSnapshotEnvelope"),
    "ContextMessage": ("types", "ContextMessage"),
    "ControllerArtifactResolver": ("controller_artifacts", "ControllerArtifactResolver"),
    "ControllerArtifactStore": ("controller_artifacts", "ControllerArtifactStore"),
    "CONTROLLER_ROLE_MEDIA": ("prefix_contracts", "CONTROLLER_ROLE_MEDIA"),
    "CostClosure": ("evidence", "CostClosure"),
    "derive_call_seed": ("controller", "derive_call_seed"),
    "derive_packet_rewrite_artifacts": ("packets", "derive_packet_rewrite_artifacts"),
    "FrozenVerifierReceipt": ("types", "FrozenVerifierReceipt"),
    "FrozenPrefixReceipt": ("evidence", "FrozenPrefixReceipt"),
    "FailureKind": ("types", "FailureKind"),
    "EnvironmentProcessIdentity": ("prefix_contracts", "EnvironmentProcessIdentity"),
    "GroupKind": ("types", "GroupKind"),
    "GroupLabel": ("types", "GroupLabel"),
    "GradeReceipt": ("types", "GradeReceipt"),
    "GradeEvidence": ("evidence", "GradeEvidence"),
    "GradeExecutionReceipt": ("evidence", "GradeExecutionReceipt"),
    "grade_execution_receipt_bytes": ("evidence", "grade_execution_receipt_bytes"),
    "IdentifierAtom": ("packets", "IdentifierAtom"),
    "IdentifierKind": ("packets", "IdentifierKind"),
    "ImplementationDescriptor": ("prefix_contracts", "ImplementationDescriptor"),
    "InitialRestoreQualificationReceipt": (
        "prefix_contracts",
        "InitialRestoreQualificationReceipt",
    ),
    "initial_restore_qualification_receipt_bytes": (
        "prefix_contracts",
        "initial_restore_qualification_receipt_bytes",
    ),
    "LiteralAtom": ("packets", "LiteralAtom"),
    "MatchingAlgorithm": ("types", "MatchingAlgorithm"),
    "NoInterventionPacketMarker": ("packets", "NoInterventionPacketMarker"),
    "normalize_synthetic_packet_findings": (
        "packets",
        "normalize_synthetic_packet_findings",
    ),
    "load_synthetic_packet_authority": ("packets", "load_synthetic_packet_authority"),
    "PacketAuthority": ("packets", "PacketAuthority"),
    "PacketInvalid": ("packets", "PacketInvalid"),
    "PacketPairReceipt": ("packets", "PacketPairReceipt"),
    "PacketPolicy": ("packets", "PacketPolicy"),
    "PacketRewriteArtifacts": ("packets", "PacketRewriteArtifacts"),
    "OpaqueSlotIdentity": ("types", "OpaqueSlotIdentity"),
    "OpaqueSlotWorkOrder": ("types", "OpaqueSlotWorkOrder"),
    "PrefixCaps": ("types", "PrefixCaps"),
    "PrefixExecutionAuthority": ("execution_authority", "PrefixExecutionAuthority"),
    "ProviderAttemptLedger": ("evidence", "ProviderAttemptLedger"),
    "ProviderAttemptStatus": ("evidence", "ProviderAttemptStatus"),
    "ProviderCallAttemptReceipt": ("evidence", "ProviderCallAttemptReceipt"),
    "ProviderDispatchIntent": ("evidence", "ProviderDispatchIntent"),
    "ProviderSettlement": ("evidence", "ProviderSettlement"),
    "RawProviderCompletionKind": ("prefix_contracts", "RawProviderCompletionKind"),
    "RawProviderObservation": ("prefix_contracts", "RawProviderObservation"),
    "REF_LOAD_CLASS_BY_ROLE": ("prefix_contracts", "REF_LOAD_CLASS_BY_ROLE"),
    "SyntheticPacketArtifactStore": ("packets", "SyntheticPacketArtifactStore"),
    "SyntheticZeroAttemptCostClosure": ("evidence", "SyntheticZeroAttemptCostClosure"),
    "SyntheticPrefixProgram": ("prefix_contracts", "SyntheticPrefixProgram"),
    "SnapshotRestoreReceipt": ("prefix_contracts", "SnapshotRestoreReceipt"),
    "StableSourceProvenance": ("prefix_contracts", "StableSourceProvenance"),
    "ResourceCounters": ("types", "ResourceCounters"),
    "RandomizationResult": ("types", "RandomizationResult"),
    "ResolutionResult": ("types", "ResolutionResult"),
    "SecondaryFamilyResult": ("types", "SecondaryFamilyResult"),
    "SimultaneousBounds": ("types", "SimultaneousBounds"),
    "run_prefix": ("synthetic_prefix_loop", "run_prefix"),
    "CallContractCaps": ("types", "CallContractCaps"),
    "load_prefix_execution_authority": (
        "execution_authority",
        "load_prefix_execution_authority",
    ),
    "load_initial_restore_qualification_receipt": (
        "prefix_contracts",
        "load_initial_restore_qualification_receipt",
    ),
    "load_grade_execution_receipt": ("evidence", "load_grade_execution_receipt"),
    "load_prefix_candidate_receipt": ("prefix_contracts", "load_prefix_candidate_receipt"),
    "seal_prefix_index": ("prefix_index", "seal_prefix_index"),
    "load_snapshot_restore_receipt": ("prefix_contracts", "load_snapshot_restore_receipt"),
    "load_verifier_execution_receipt": ("evidence", "load_verifier_execution_receipt"),
    "load_synthetic_prefix_program": ("prefix_contracts", "load_synthetic_prefix_program"),
    "prefix_candidate_receipt_bytes": ("prefix_contracts", "prefix_candidate_receipt_bytes"),
    "require_assignment_reconstruction": (
        "assignment_verification",
        "require_assignment_reconstruction",
    ),
    "require_assignment_publication": (
        "assignment_verification",
        "require_assignment_publication",
    ),
    "require_confirmation_assignment": (
        "assignment_verification",
        "require_confirmation_assignment",
    ),
    "seal_branch_assignment": ("branch_assignment", "seal_branch_assignment"),
    "snapshot_restore_receipt_bytes": ("prefix_contracts", "snapshot_restore_receipt_bytes"),
    "SubjectContext": ("types", "SubjectContext"),
    "SubjectTurn": ("types", "SubjectTurn"),
    "TaskAssignment": ("types", "TaskAssignment"),
    "TaskSchedule": ("types", "TaskSchedule"),
    "TaskSpec": ("types", "TaskSpec"),
    "ToolBoundary": ("types", "ToolBoundary"),
    "ToolBoundaryLedger": ("evidence", "ToolBoundaryLedger"),
    "ToolCall": ("types", "ToolCall"),
    "Treatment": ("types", "Treatment"),
    "TriggerReason": ("types", "TriggerReason"),
    "UnblindSecretHandle": ("secrets", "UnblindSecretHandle"),
    "Verdict": ("types", "Verdict"),
    "VerifierFinding": ("packets", "VerifierFinding"),
    "VerifierEvidence": ("evidence", "VerifierEvidence"),
    "VerifierExecutionReceipt": ("evidence", "VerifierExecutionReceipt"),
    "verifier_execution_receipt_bytes": ("evidence", "verifier_execution_receipt_bytes"),
    "verify_result_bundle": ("assignment_verification", "verify_result_bundle"),
    "verify_synthetic_assignment_graph": (
        "assignment_verification",
        "verify_synthetic_assignment_graph",
    ),
    "synthetic_prefix_program_bytes": ("prefix_contracts", "synthetic_prefix_program_bytes"),
    "validate_prefix_candidate_ref": ("prefix_contracts", "validate_prefix_candidate_ref"),
    "write_packet_candidate": ("packets", "write_packet_candidate"),
    "analyze": ("analysis", "analyze"),
    "classify_verdict": ("analysis", "classify_verdict"),
    "evaluate_binary_gate_batch": ("analysis", "evaluate_binary_gate_batch"),
    "evaluate_binary_gate_kernel": ("analysis", "evaluate_binary_gate_kernel"),
    "rows_to_binary_sufficient_statistics": ("analysis", "rows_to_binary_sufficient_statistics"),
})


def derive_seed(schedule_seed: int, task_id: str, role: str) -> int:
    """Derive one deterministic unsigned 64-bit schedule seed portably."""

    import hashlib
    import unicodedata

    if type(schedule_seed) is not int or not 0 <= schedule_seed < 2**64:
        raise ValueError("U64 field value is outside the unsigned 64-bit range")
    fields = (task_id, role)
    payloads: list[bytes] = []
    for value in fields:
        if type(value) is not str:
            raise TypeError("TEXT field value must be a string")
        if not value:
            raise ValueError("TEXT field value must be non-empty")
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("TEXT field value must already be NFC-normalized")
        if any(unicodedata.category(character).startswith("C") for character in value):
            raise ValueError("TEXT field value contains a forbidden Unicode category")
        payloads.append(value.encode("utf-8", errors="strict"))
    frame = bytearray(b"pneuma-resampling-null-frame-v1\x00")
    tag = b"derive-seed-v1"
    frame.extend(len(tag).to_bytes(4, "big"))
    frame.extend(tag)
    frame.extend((3).to_bytes(4, "big"))
    frame.extend(b"\x01")
    frame.extend((8).to_bytes(4, "big"))
    frame.extend(schedule_seed.to_bytes(8, "big"))
    for payload in payloads:
        frame.extend(b"\x02")
        frame.extend(len(payload).to_bytes(4, "big"))
        frame.extend(payload)
    return int.from_bytes(hashlib.sha256(frame).digest()[:8], "big")


def __getattr__(name: str) -> object:
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    from importlib import import_module

    module = import_module(f".{module_name}", __name__)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
