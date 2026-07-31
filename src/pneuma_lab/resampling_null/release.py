"""Task-10 release inspection and external package manifests.

This module deliberately has no authority to create a scientific result.  It
can only independently re-verify an already sealed artifact root and describe
the authority carried by its terminal power report.  In particular,
implementation-verification and synthetic roots remain non-results.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
import hashlib
from pathlib import Path

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import verify_artifact_root
from .errors import RecordValidationError
from .json_io import load_json_bytes, run_root


_NON_RESULT_AUTHORITIES = {
    "implementation_verification": "IMPLEMENTATION_VERIFICATION_ONLY",
    "synthetic_validation": "CONDITIONAL_ONLY",
}


def verify_release_bytes_independently(
    run_root_path: Path,
    receipt_path: Path,
) -> None:
    """Independently rehash the receipt's declared immutable byte closure.

    This intentionally does not call the scientific-graph verifier: it is the
    second, small verifier used by Task 10 to catch receipt/byte mismatch even
    if the primary graph reader shares an implementation defect.
    """
    root = run_root(run_root_path)
    receipt = Path(receipt_path).resolve(strict=True)
    try:
        receipt.relative_to(root)
    except ValueError as exc:
        raise RecordValidationError("release receipt must remain inside run_root") from exc
    record = load_json_bytes(receipt.read_bytes(), source=receipt)
    if not isinstance(record, Mapping) or record.get("record_kind") != "resampling_artifact_root":
        raise RecordValidationError("receipt is not an artifact-root record")
    payload = record.get("payload")
    if not isinstance(payload, Mapping) or not isinstance(payload.get("entries"), list):
        raise RecordValidationError("artifact-root receipt entries are malformed")
    entries = payload["entries"]
    normalized: list[dict[str, object]] = []
    paths: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise RecordValidationError("artifact-root entry is malformed")
        value = dict(entry)
        relative = value.get("relative_path")
        digest = value.get("sha256")
        count = value.get("byte_count")
        if not isinstance(relative, str) or not relative or not isinstance(digest, str) or len(digest) != 64:
            raise RecordValidationError("artifact-root entry identity is malformed")
        if type(count) is not int or count < 0:
            raise RecordValidationError("artifact-root entry byte count is malformed")
        candidate = (root / relative).resolve(strict=True)
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise RecordValidationError("artifact-root entry escapes run_root") from exc
        content = candidate.read_bytes()
        if len(content) != count or hashlib.sha256(content).hexdigest() != digest:
            raise RecordValidationError("artifact-root entry bytes differ from receipt")
        normalized.append(value)
        paths.append(relative)
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise RecordValidationError("artifact-root entries are not uniquely sorted")
    actual_root = hashlib.sha256(canonical_json_bytes(normalized, indent=None)).hexdigest()
    if payload.get("root_sha256") != actual_root:
        raise RecordValidationError("artifact-root digest mismatch")


def inspect_sealed_release(
    run_root_path: Path,
    receipt_path: Path,
    *,
    required_document_kinds: Collection[str],
) -> dict[str, object]:
    """Re-verify a sealed root and return a claim-bound release descriptor.

    The descriptor is intentionally derived after ``verify_artifact_root``;
    it is not a second, weaker graph reader.  A roster-bound final is merely
    labelled ``canonical_lineage_candidate``: scientific promotion still
    requires the separately authorized Step 4B release decision.
    """
    root = run_root(run_root_path)
    receipt = Path(receipt_path).resolve(strict=True)
    try:
        receipt.relative_to(root)
    except ValueError as exc:
        raise RecordValidationError("release receipt must remain inside run_root") from exc
    verify_artifact_root(receipt, root, required_document_kinds=required_document_kinds)
    verify_release_bytes_independently(root, receipt)
    record = load_json_bytes(receipt.read_bytes(), source=receipt)
    if not isinstance(record, Mapping) or not isinstance(record.get("payload"), Mapping):
        raise RecordValidationError("artifact-root receipt is malformed")
    entries = record["payload"].get("entries")
    if not isinstance(entries, list):
        raise RecordValidationError("artifact-root receipt entries are malformed")
    finals: list[Mapping[str, object]] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("document_kind") != "resampling_power_report":
            continue
        relative = entry.get("relative_path")
        if not isinstance(relative, str):
            raise RecordValidationError("artifact-root entry path is malformed")
        path = root / relative
        payload = load_json_bytes(path.read_bytes(), source=path)
        if not isinstance(payload, Mapping) or not isinstance(payload.get("payload"), Mapping):
            raise RecordValidationError("power report is malformed")
        value = payload["payload"]
        if value.get("stage") == "final":
            finals.append(value)
    if len(finals) != 1:
        raise RecordValidationError("sealed release requires exactly one terminal power final")
    final = finals[0]
    authority = final.get("decision_authority")
    finalization = final.get("finalization")
    decision = finalization.get("decision") if isinstance(finalization, Mapping) else None
    if not isinstance(authority, str) or not isinstance(decision, str):
        raise RecordValidationError("terminal power final lacks authority or decision")
    finalization_kind = finalization.get("kind") if isinstance(finalization, Mapping) else None
    if finalization_kind == "feasibility_no_go":
        if authority != "roster_bound_selection" or decision != "NO_GO":
            raise RecordValidationError("feasibility no-go has an invalid authority or decision")
        classification = "registered_no_go"
        claim_boundary = "requires_step4b_release_authorization"
        failure_classification = finalization.get("reason")
    elif finalization_kind == "synthetic_validation_failed":
        if authority != "synthetic_validation" or decision != "CONDITIONAL_ONLY":
            raise RecordValidationError("synthetic terminal failure has an invalid authority or decision")
        classification = "synthetic_fixture_failure"
        claim_boundary = "not_a_scientific_result"
        failure_classification = finalization.get("reason")
    elif finalization_kind != "completed_chain":
        raise RecordValidationError("terminal power finalization kind is not recognized")
    else:
        expected = _NON_RESULT_AUTHORITIES.get(authority)
        if expected is not None:
            if decision != expected:
                raise RecordValidationError("non-result authority carries an invalid terminal decision")
            classification = "implementation_fixture" if authority == "implementation_verification" else "synthetic_fixture"
            claim_boundary = "not_a_scientific_result"
            failure_classification = None
        elif authority == "roster_bound_selection":
            if decision != "GO":
                raise RecordValidationError("canonical power authority lacks its registered GO decision")
            classification = "canonical_lineage_candidate"
            claim_boundary = "requires_step4b_release_authorization"
            failure_classification = None
        else:
            raise RecordValidationError("terminal power authority is not recognized for release inspection")
    return {
        "contract_id": "resampling-null-task10-release-v1",
        "receipt_sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        "root_sha256": record["payload"].get("root_sha256"),
        "study_id": record.get("study_id"),
        "decision_authority": authority,
        "terminal_decision": decision,
        "classification": classification,
        "claim_boundary": claim_boundary,
        "failure_classification": failure_classification,
    }


def write_external_release_package(
    descriptor: Mapping[str, object],
    *,
    output: Path,
) -> str:
    """Write a content-addressed package manifest outside the sealed root."""
    required = {
        "contract_id", "receipt_sha256", "root_sha256", "study_id",
        "decision_authority", "terminal_decision", "classification", "claim_boundary",
        "failure_classification",
    }
    if set(descriptor) != required:
        raise RecordValidationError("release descriptor has an unregistered shape")
    path = Path(output)
    if path.exists():
        raise FileExistsError("release package output already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(dict(descriptor), indent=None)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


__all__ = (
    "inspect_sealed_release", "verify_release_bytes_independently",
    "write_external_release_package",
)
