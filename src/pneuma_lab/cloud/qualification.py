"""G-ROSTER evaluation: the per-split eligibility inequality, derived not stored.

The registered gate is, for every split `s` of every benchmark family:

    eligible_s >= max(
        confirmation_quota_s + 2 * pilot_s + fixed_reserve_s
            + hamilton_allocation_s,             (C160 only)
        registered_minimum_units_s)              (where the design states a floor)

Three traps this module exists to avoid.

**1. Two pools are not the same set.** `proxy_basis` records which one a split's
`proxy_units` counts:

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
- `pinned_objective_pool` — the tau2 task pool frozen by DL-128. tau2 units are
  tasks drawn from that pool, so it bounds eligibility from above the same way.

Only a `base_commit_admissible` (swe) or `pinned_objective_pool` (tau2) record
can support the strong claim that a split is unsatisfiable by any audit outcome.
Against a current-metadata proxy the evaluator reports `FEASIBILITY_NO_GO` with
the shortfall marked `provisional_unsatisfiable`, because establishing or
refuting it requires the base-commit admissibility enumeration — which is Step
5B work, not a bookkeeping exercise.

**2a. A registered floor is not implied by the inequality.** DL-128 states some
requirements directly rather than through the quota arithmetic — tau2 C160 needs
"at least 47 qualified airline tasks", which is far above that split's
quota-plus-pilots. Modelling only the inequality would silently understate it,
so `registered_minimum_units` carries such a floor and the requirement is the
greater of the two. `None` means no floor is registered for that split, which —
unlike an unfixed reserve — is a genuine state rather than missing authority.

**2. An unfixed requirement term is not zero.** DL-128 requires C160 to carry
"12 per split plus the Hamilton allocation" and "plus reserves", but fixes no
number for either. Reading an absent value as 0 silently *understates* the
requirement and would let a marginal split look satisfied. So `fixed_reserve`
and (for C160) `hamilton_allocation` must be explicitly fixed by authority;
`None` fails closed. The evaluator still reports a `required_lower_bound` that
treats unfixed terms as 0, because both terms are non-negative and a shortfall
against the lower bound is a shortfall a fortiori — but such a split can never
reach a feasible verdict, only a sharper no-go.

**3. One family's qualification is not the other's.** A swe record qualifies
root lineages by base-commit licence evidence; a tau2 record qualifies
individual tasks from the pinned objective pool. `require_roster_gate_satisfied`
therefore demands a satisfied audit for *both* registered families and refuses a
single-family submission. The registered tiers remain exactly C120 and C160 —
there is no tau2-only tier and this module must not introduce one.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import CloudManifestError
from .manifests import _validate


REQUIRED_INDEPENDENT_PAIRS = 3

FEASIBLE = "CONDITIONALLY_FEASIBLE"
NO_GO = "FEASIBILITY_NO_GO"
UNSATISFIABLE = "FEASIBILITY_UNSATISFIABLE_BY_AUDIT"

METADATA_BASIS = "current_repository_metadata"
ADMISSIBLE_BASIS = "base_commit_admissible"
OBJECTIVE_POOL_BASIS = "pinned_objective_pool"

SWE = "swe"
TAU2 = "tau2"
REGISTERED_FAMILIES = (SWE, TAU2)

# Which bases may appear for which family, and which of them bound eligibility
# from above. A tau2 record claiming a base-commit basis, or a swe record
# claiming the objective pool, is a category error rather than weak evidence.
_ALLOWED_BASES = {
    SWE: frozenset({METADATA_BASIS, ADMISSIBLE_BASIS}),
    TAU2: frozenset({OBJECTIVE_POOL_BASIS}),
}
_BOUNDING_BASES = frozenset({ADMISSIBLE_BASIS, OBJECTIVE_POOL_BASIS})

# The unit each family counts, carried into the evaluation so a reader cannot
# silently compare a lineage count against a task count.
UNIT_KIND = {SWE: "root_lineage", TAU2: "task"}

# The Hamilton allocation is a C160-only term under DL-128.
_HAMILTON_TIERS = frozenset({"C160"})


def validate_qualification_audit(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the audit without assuming which pool or unit it counts."""

    audit = _validate(record, expected_kind="cloud_qualification_audit")
    family = audit["benchmark_family"]
    basis = audit["proxy_basis"]
    if basis not in _ALLOWED_BASES[family]:
        raise CloudManifestError(f"proxy basis {basis!r} is not a valid pool for the {family!r} family")
    if audit["evidence_class"] == "audited_qualified" and audit["input_lock_sha256"] is None:
        raise CloudManifestError("an audited qualification record must bind an input-lock digest")
    names = [split["split"] for split in audit["splits"]]
    if len(set(names)) != len(names):
        raise CloudManifestError("qualification splits must be unique")
    for split in audit["splits"]:
        # Only a bounding pool is a genuine superset of the eligible set.
        # Refusing this for a current-metadata proxy would make the one finding
        # that overturns a no-go verdict unrecordable.
        if basis in _BOUNDING_BASES and split["eligible_units"] > split["proxy_units"]:
            raise CloudManifestError(f"qualified units cannot exceed the bounding pool for split {split['split']!r}")
        if split["three_pair_audit"]["pairs_independent_pass"] > split["three_pair_audit"]["pairs_attempted"]:
            raise CloudManifestError(f"passing pairs cannot exceed attempted pairs for split {split['split']!r}")
    return audit


def _hamilton_required(tier: str) -> bool:
    return tier in _HAMILTON_TIERS


def _registered_floor(split: Mapping[str, Any]) -> int:
    """Return the directly registered minimum for this split, or 0 when none."""

    floor = split.get("registered_minimum_units")
    return 0 if floor is None else int(floor)


def unfixed_requirement_terms(split: Mapping[str, Any], tier: str) -> tuple[str, ...]:
    """Return the requirement terms no authority has fixed for this split."""

    missing: list[str] = []
    if split["fixed_reserve"] is None:
        missing.append("fixed_reserve")
    if _hamilton_required(tier) and split["hamilton_allocation"] is None:
        missing.append("hamilton_allocation")
    return tuple(missing)


def required_units(split: Mapping[str, Any], tier: str) -> int:
    """Return the exact requirement, or fail closed on an unfixed term.

    Fails closed rather than defaulting an absent reserve or Hamilton
    allocation to zero, because zero is the one value that can never make the
    gate stricter and is therefore the one an unfixed term must not take.
    """

    missing = unfixed_requirement_terms(split, tier)
    if missing:
        raise CloudManifestError(
            f"split {split['split']!r} has no authority-fixed {', '.join(missing)}; "
            "an unfixed requirement term is not zero and the gate fails closed"
        )
    total = int(split["confirmation_quota"]) + 2 * int(split["pilot_units"]) + int(split["fixed_reserve"])
    if _hamilton_required(tier):
        total += int(split["hamilton_allocation"])
    return max(total, _registered_floor(split))


def required_units_lower_bound(split: Mapping[str, Any], tier: str) -> int:
    """Return the requirement with unfixed non-negative terms treated as zero.

    Only sound as a *lower* bound: a shortfall against it is a shortfall under
    any admissible completion of the unfixed terms. It can never justify a
    feasible verdict.
    """

    total = int(split["confirmation_quota"]) + 2 * int(split["pilot_units"]) + int(split["fixed_reserve"] or 0)
    if _hamilton_required(tier):
        total += int(split["hamilton_allocation"] or 0)
    return max(total, _registered_floor(split))


def _resolve_receipt(receipt: Mapping[str, Any] | None, evidence_root: Path | None) -> bool:
    """Return whether the receipt resolves to bytes with the recorded digest."""

    if receipt is None or evidence_root is None:
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
    """Evaluate G-ROSTER for one family and tier and return the derived verdict.

    A split is credited only when its isolation and licence receipts resolve to
    real bytes under `evidence_root`. Without an evidence root nothing is
    credited, so a hand-written record cannot reach a feasible verdict. A split
    whose requirement terms are not all authority-fixed can never be credited as
    satisfied either, however large its eligible count.
    """

    audit = validate_qualification_audit(record)
    tier = audit["tier"]
    family = audit["benchmark_family"]
    audited = audit["evidence_class"] == "audited_qualified"
    bounding = audit["proxy_basis"] in _BOUNDING_BASES
    splits: list[dict[str, Any]] = []
    for split in audit["splits"]:
        missing = unfixed_requirement_terms(split, tier)
        exact = not missing
        lower_bound = required_units_lower_bound(split, tier)
        complete = audited and exact and _split_evidence_is_complete(split, evidence_root)
        credited = int(split["eligible_units"]) if complete else 0
        # Compared against the lower bound: if even the understated requirement
        # exceeds the bounding pool, no completion of the unfixed terms helps.
        over_pool = lower_bound > int(split["proxy_units"])
        splits.append({
            "split": split["split"],
            "unit_kind": UNIT_KIND[family],
            "required_lower_bound": lower_bound,
            "required_exact": required_units(split, tier) if exact else None,
            "requirement_exact": exact,
            "registered_minimum_units": split.get("registered_minimum_units"),
            "unfixed_requirement_terms": missing,
            "proxy_units": int(split["proxy_units"]),
            "credited_eligible": credited,
            "evidence_complete": complete,
            # Only meaningful against a bounding pool. Against a current
            # metadata proxy this is a provisional signal, not a determination.
            "unsatisfiable_by_audit": over_pool and bounding,
            "provisional_unsatisfiable": over_pool and not bounding,
            "shortfall": max(0, lower_bound - credited),
        })
    if any(split["unsatisfiable_by_audit"] for split in splits):
        verdict = UNSATISFIABLE
    elif (
        audited
        and bounding
        and all(split["requirement_exact"] and split["evidence_complete"] and split["shortfall"] == 0 for split in splits)
    ):
        verdict = FEASIBLE
    else:
        verdict = NO_GO
    return {
        "benchmark_family": family,
        "unit_kind": UNIT_KIND[family],
        "tier": tier,
        "evidence_class": audit["evidence_class"],
        "proxy_basis": audit["proxy_basis"],
        "verdict": verdict,
        "authority_complete": all(split["requirement_exact"] for split in splits),
        "splits": tuple(splits),
    }


def require_roster_gate_satisfied(records: Sequence[Mapping[str, Any]], *, evidence_root: Path, lock: Mapping[str, Any]) -> dict[str, Any]:
    """Guard the promotion path: refuse unless G-ROSTER holds for both families.

    Takes the full set of audits for one tier. SWE qualification is not tau2
    qualification, so a submission covering only one family is refused rather
    than partially credited. Every record must bind an input-lock digest
    recomputed from `lock` rather than asserted, must use a bounding pool, and
    must have every requirement term authority-fixed.

    Honest limit, stated because the guard is easy to overrate: this is a
    **consistency** check, not an **authenticity** check. Receipt digests live
    in the same record as the counts they attest, so a party who can write both
    the audit record and the evidence files can satisfy it. It catches a stale,
    mismatched, or internally incoherent audit; it does not prove an audit
    happened. Authenticity of the *authorization* is handled by the Ed25519
    ceremony in `authorization_keys`; no equivalent ceremony yet covers the
    audit evidence itself, which remains a stated residual limitation.
    """

    from .inputs import verify_input_lock

    expected_lock = verify_input_lock(lock)
    audits = [validate_qualification_audit(record) for record in records]
    if not audits:
        raise CloudManifestError("G-ROSTER requires a qualification audit for every registered benchmark family")

    tiers = {audit["tier"] for audit in audits}
    if len(tiers) != 1:
        raise CloudManifestError("G-ROSTER audits must all describe one tier")

    by_family: dict[str, dict[str, Any]] = {}
    for audit in audits:
        family = audit["benchmark_family"]
        if family in by_family:
            raise CloudManifestError(f"duplicate qualification audit for the {family!r} family")
        by_family[family] = audit

    absent = [family for family in REGISTERED_FAMILIES if family not in by_family]
    if absent:
        raise CloudManifestError(
            f"G-ROSTER is missing a qualification audit for: {', '.join(absent)}; "
            "one family's qualification is never evidence for another's"
        )

    evaluations: dict[str, Any] = {}
    for family, audit in sorted(by_family.items()):
        if audit["input_lock_sha256"] != expected_lock:
            raise CloudManifestError(f"the {family!r} qualification audit is not bound to this input-lock digest")
        evaluation = evaluate_roster_gate(audit, evidence_root=evidence_root)
        if evaluation["verdict"] != FEASIBLE:
            raise CloudManifestError(
                f"G-ROSTER is open for {family!r} ({evaluation['verdict']}); "
                "no manifest promotion, pilot authorization, or launch-readiness claim is permitted"
            )
        evaluations[family] = evaluation
    return {"tier": tiers.pop(), "families": evaluations}
