"""G-ROSTER evaluation: the per-split eligibility inequality, derived not stored.

The registered gate is, for every split `s`:

    eligible_s >= confirmation_quota_s + 2 * pilot_s + fixed_reserve_s

Two pools are NOT the same set, and conflating them is the trap this module
exists to avoid. `proxy_basis` records which one a split's `proxy_lineages`
counts:

- `current_repository_metadata` — the DL-128 nonarchived/permissive proxy,
  filtered on *present-day* repository metadata. This is **not** an upper bound
  on eligibility: the registered eligibility criterion is base-commit license
  evidence, and a repository that is archived today, or whose current metadata
  license is absent or unrecognized, may still carry a permissive licence at its
  pinned base commit. Such a lineage is outside the proxy yet inside the
  admissible pool.
- `base_commit_admissible` — the pool enumerated at the pinned base commits.
  Qualification (OCI mirroring, isolation, three independent pairs) filters this
  pool, so here `eligible_s <= proxy_s` genuinely holds and is enforced.

Only a `base_commit_admissible` record can support the strong claim that a split
is unsatisfiable by any audit outcome. Against a current-metadata proxy the
evaluator reports `FEASIBILITY_NO_GO` with the shortfall marked
`provisional_unsatisfiable`, because establishing or refuting it requires the
base-commit admissibility enumeration — which is Step 5B work, not a
bookkeeping exercise.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import CloudManifestError
from .manifests import _validate


REQUIRED_INDEPENDENT_PAIRS = 3

FEASIBLE = "CONDITIONALLY_FEASIBLE"
NO_GO = "FEASIBILITY_NO_GO"
UNSATISFIABLE = "FEASIBILITY_UNSATISFIABLE_BY_AUDIT"

ADMISSIBLE_BASIS = "base_commit_admissible"
METADATA_BASIS = "current_repository_metadata"


def validate_qualification_audit(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the audit record without assuming which pool the proxy counts."""

    audit = _validate(record, expected_kind="cloud_qualification_audit")
    if audit["evidence_class"] == "audited_qualified" and audit["input_lock_sha256"] is None:
        raise CloudManifestError("an audited qualification record must bind an input-lock digest")
    names = [split["split"] for split in audit["splits"]]
    if len(set(names)) != len(names):
        raise CloudManifestError("qualification splits must be unique")
    for split in audit["splits"]:
        # Only the base-commit pool is a genuine superset of the eligible set.
        # Refusing this for a current-metadata proxy would make the one finding
        # that overturns a no-go verdict unrecordable.
        if audit["proxy_basis"] == ADMISSIBLE_BASIS and split["eligible_lineages"] > split["proxy_lineages"]:
            raise CloudManifestError(f"qualified lineages cannot exceed the admissible pool for split {split['split']!r}")
        if split["three_pair_audit"]["pairs_independent_pass"] > split["three_pair_audit"]["pairs_attempted"]:
            raise CloudManifestError(f"passing pairs cannot exceed attempted pairs for split {split['split']!r}")
    return audit


def required_lineages(split: Mapping[str, Any]) -> int:
    """Return `confirmation_quota + 2 * pilot + fixed_reserve` for one split."""

    return int(split["confirmation_quota"]) + 2 * int(split["pilot_lineages"]) + int(split["fixed_reserve"])


def _resolve_receipt(receipt: Mapping[str, Any] | None, evidence_root: Path | None) -> bool:
    """Return whether the receipt resolves to bytes with the recorded digest."""

    if receipt is None:
        return False
    if evidence_root is None:
        return False
    from .retrieval import verify_mirrored_file

    try:
        verify_mirrored_file(evidence_root / receipt["relative_path"], receipt["sha256"])
    except CloudManifestError:
        return False
    return True


def _split_evidence_is_complete(split: Mapping[str, Any], evidence_root: Path | None) -> bool:
    if split["three_pair_audit"]["pairs_independent_pass"] < REQUIRED_INDEPENDENT_PAIRS:
        return False
    return _resolve_receipt(split["isolation_evidence"], evidence_root) and _resolve_receipt(split["license_evidence"], evidence_root)


def evaluate_roster_gate(record: Mapping[str, Any], *, evidence_root: Path | None = None) -> dict[str, Any]:
    """Evaluate G-ROSTER for one tier and return the derived verdict.

    A split is credited only when its isolation and licence receipts resolve to
    real bytes under `evidence_root`. Without an evidence root nothing is
    credited, so a hand-written record cannot reach a feasible verdict.
    """

    audit = validate_qualification_audit(record)
    audited = audit["evidence_class"] == "audited_qualified"
    admissible = audit["proxy_basis"] == ADMISSIBLE_BASIS
    splits: list[dict[str, Any]] = []
    for split in audit["splits"]:
        required = required_lineages(split)
        complete = audited and _split_evidence_is_complete(split, evidence_root)
        credited = int(split["eligible_lineages"]) if complete else 0
        over_pool = required > int(split["proxy_lineages"])
        splits.append({
            "split": split["split"],
            "required": required,
            "proxy_lineages": int(split["proxy_lineages"]),
            "credited_eligible": credited,
            "evidence_complete": complete,
            # Only meaningful against the base-commit pool. Against a current
            # metadata proxy this is a provisional signal, not a determination.
            "unsatisfiable_by_audit": over_pool and admissible,
            "provisional_unsatisfiable": over_pool and not admissible,
            "shortfall": max(0, required - credited),
        })
    if any(split["unsatisfiable_by_audit"] for split in splits):
        verdict = UNSATISFIABLE
    elif audited and admissible and all(split["evidence_complete"] and split["shortfall"] == 0 for split in splits):
        verdict = FEASIBLE
    else:
        verdict = NO_GO
    return {
        "tier": audit["tier"],
        "evidence_class": audit["evidence_class"],
        "proxy_basis": audit["proxy_basis"],
        "verdict": verdict,
        "splits": tuple(splits),
    }


def require_roster_gate_satisfied(record: Mapping[str, Any], *, evidence_root: Path, lock: Mapping[str, Any]) -> dict[str, Any]:
    """Guard the promotion path: refuse unless G-ROSTER is genuinely satisfied.

    Requires a `base_commit_admissible` basis, resolvable evidence bytes, and an
    input-lock digest recomputed from `lock` rather than asserted.

    Honest limit, stated because the guard is easy to overrate: this is a
    **consistency** check, not an **authenticity** check. Receipt digests live in
    the same record as the counts they attest, so a party who can write both the
    audit record and the evidence files can satisfy it. It catches a stale,
    mismatched, or internally incoherent audit; it does not prove an audit
    happened. Authenticity needs the approver key ceremony this package
    deliberately does not implement.
    """

    from .inputs import verify_input_lock

    audit = validate_qualification_audit(record)
    if audit["input_lock_sha256"] != verify_input_lock(lock):
        raise CloudManifestError("qualification audit is not bound to this input-lock digest")
    evaluation = evaluate_roster_gate(audit, evidence_root=evidence_root)
    if evaluation["verdict"] != FEASIBLE:
        raise CloudManifestError(f"G-ROSTER is open ({evaluation['verdict']}); no manifest promotion, pilot authorization, or launch-readiness claim is permitted")
    return evaluation
