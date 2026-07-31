from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.inputs import verify_input_lock
from pneuma_lab.cloud.qualification import (
    FEASIBLE,
    NO_GO,
    UNSATISFIABLE,
    evaluate_roster_gate,
    require_roster_gate_satisfied,
    required_units,
    required_units_lower_bound,
    unfixed_requirement_terms,
    validate_qualification_audit,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures" / "cloud"
DECISION_LOG = REPO_ROOT / "docs/research/neurips-2026-workshop/15-decision-log.md"
_HEX = "a" * 64


def _lock() -> dict:
    return json.loads((FIXTURES / "input-lock-fixture.json").read_text())


def _lock_digest() -> str:
    return verify_input_lock(_lock())


def audit(tier: str, family: str = "swe") -> dict:
    stem = f"qualification-audit-{tier}-proxy" if family == "swe" else f"qualification-audit-tau2-{tier}-proxy"
    return json.loads((FIXTURES / f"{stem}.json").read_text())


def _mirror(tmp_path: Path) -> tuple[Path, dict]:
    """Write real evidence bytes and return the root plus a matching receipt."""

    payload = b"qualification-evidence"
    (tmp_path / "receipts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "receipts" / "audit.json").write_bytes(payload)
    return tmp_path, {"relative_path": "receipts/audit.json", "sha256": hashlib.sha256(payload).hexdigest()}


def _fully_audited(tier: str, receipt: dict, *, basis: str = "current_repository_metadata", family: str = "swe", fix_terms: bool = True) -> dict:
    """Return a maximally credited record; `fix_terms` supplies the authority values."""

    record = audit(tier, family)
    record["evidence_class"] = "audited_qualified"
    record["proxy_basis"] = basis
    record["input_lock_sha256"] = _lock_digest()
    for split in record["splits"]:
        split["isolation_evidence"] = dict(receipt)
        split["license_evidence"] = dict(receipt)
        split["three_pair_audit"] = {"pairs_attempted": 3, "pairs_independent_pass": 3}
        split["eligible_units"] = split["proxy_units"]
        if fix_terms:
            # Stands in for an authority that has fixed the terms; the
            # committed fixtures deliberately leave them unfixed.
            split["fixed_reserve"] = 0
            split["hamilton_allocation"] = 0
    return record


def _both_families(receipt: dict, tier: str = "c120") -> list[dict]:
    """A satisfied pair of audits, one per registered family."""

    records = []
    for family in ("swe", "tau2"):
        basis = "base_commit_admissible" if family == "swe" else "pinned_objective_pool"
        record = _fully_audited(tier, receipt, basis=basis, family=family)
        for split in record["splits"]:
            split["confirmation_quota"] = 1
        records.append(record)
    return records


def test_committed_proxy_fixtures_bind_their_design_and_code() -> None:
    design = hashlib.sha256((REPO_ROOT / "docs/research/neurips-2026-workshop/38-experiment-design-freeze.md").read_bytes()).hexdigest()
    code = hashlib.sha256((REPO_ROOT / "src/pneuma_lab/cloud/qualification.py").read_bytes()).hexdigest()
    for tier in ("c120", "c160"):
        provenance = validate_qualification_audit(audit(tier))["provenance"]
        assert provenance == {"design_sha256": design, "code_sha256": code}


def test_fixture_counts_are_transcribed_from_the_decision_log() -> None:
    """Guard against a silent transcription error in the roster evidence."""

    row = next(line for line in DECISION_LOG.read_text().splitlines() if line.startswith("| DL-128 "))
    assert "C120 keeps fixed confirmation quotas `9/14/16/17/16/16/16/16`" in row
    assert re.search(r"split C 9, C\+\+ 14, C# 26, Go 77, Java 44, JavaScript 35, Rust 28, TypeScript 45", row)
    assert "at least 11 C and 16 C++ lineages" in row
    assert "C needs at least 14 qualified lineages" in row

    expected_proxy = {"C": 9, "C++": 14, "C#": 26, "Go": 77, "Java": 44, "JavaScript": 35, "Rust": 28, "TypeScript": 45}
    expected_quota = dict(zip(expected_proxy, [9, 14, 16, 17, 16, 16, 16, 16]))
    for split in audit("c120")["splits"]:
        assert split["proxy_units"] == expected_proxy[split["split"]]
        assert split["confirmation_quota"] == expected_quota[split["split"]]

    # DL-128's stated minima fall out of the inequality's *lower bound*, since
    # the reserve and Hamilton terms are unfixed in the committed fixtures.
    by_name = {split["split"]: split for split in audit("c120")["splits"]}
    assert required_units_lower_bound(by_name["C"], "C120") == 11
    assert required_units_lower_bound(by_name["C++"], "C120") == 16
    assert required_units_lower_bound({s["split"]: s for s in audit("c160")["splits"]}["C"], "C160") == 14


def test_tau2_fixture_counts_are_transcribed_from_the_decision_log() -> None:
    row = next(line for line in DECISION_LOG.read_text().splitlines() if line.startswith("| DL-128 "))
    assert "airline 50 DB+COMMUNICATE" in row
    assert "telecom base 114" in row
    assert "banking 88 DB plus 9 ACTION-only" in row
    assert "C120 `17/13/10`" in row and "C160 `25/18/15`" in row

    pool = {"airline": 50, "telecom": 114, "banking": 88}
    quota = {"C120": {"airline": 17, "telecom": 13, "banking": 10}, "C160": {"airline": 25, "telecom": 18, "banking": 15}}
    for tier in ("c120", "c160"):
        record = validate_qualification_audit(audit(tier, "tau2"))
        assert record["benchmark_family"] == "tau2"
        for split in record["splits"]:
            assert split["proxy_units"] == pool[split["split"]]
            assert split["confirmation_quota"] == quota[record["tier"]][split["split"]]


# ---------------------------------------------------------------------------
# Requirement arithmetic: an unfixed term is not zero.
# ---------------------------------------------------------------------------


def test_inequality_matches_the_registered_contract() -> None:
    fixed = {"split": "C", "confirmation_quota": 9, "pilot_units": 1, "fixed_reserve": 3, "hamilton_allocation": 0}
    assert required_units(fixed, "C120") == 14
    # C160 adds the Hamilton allocation on top of quota, pilots, and reserves.
    assert required_units({**fixed, "hamilton_allocation": 5}, "C160") == 19
    # The Hamilton term is C160-only, so C120 ignores it.
    assert required_units({**fixed, "hamilton_allocation": 5}, "C120") == 14


def test_unfixed_reserve_fails_closed_rather_than_defaulting_to_zero() -> None:
    split = {"split": "C", "confirmation_quota": 9, "pilot_units": 1, "fixed_reserve": None, "hamilton_allocation": 0}
    assert unfixed_requirement_terms(split, "C120") == ("fixed_reserve",)
    with pytest.raises(CloudManifestError, match="an unfixed requirement term is not zero"):
        required_units(split, "C120")
    # The lower bound is still derivable, and understates rather than overstates.
    assert required_units_lower_bound(split, "C120") == 11


def test_c160_requires_a_fixed_hamilton_allocation() -> None:
    """DL-128 mandates the allocation for C160 but fixes no number."""

    split = {"split": "C", "confirmation_quota": 12, "pilot_units": 1, "fixed_reserve": 0, "hamilton_allocation": None}
    assert unfixed_requirement_terms(split, "C160") == ("hamilton_allocation",)
    with pytest.raises(CloudManifestError, match="hamilton_allocation"):
        required_units(split, "C160")
    # C120 carries no Hamilton term, so the same split is exactly determined.
    assert unfixed_requirement_terms(split, "C120") == ()
    assert required_units(split, "C120") == 14


def test_a_registered_floor_outranks_the_inequality() -> None:
    """DL-128 states tau2 C160 needs >= 47 qualified airline tasks outright.

    Found by hostile review: modelling only quota-plus-pilots put airline C160
    at 27 and silently understated the registered requirement by twenty tasks.
    """

    row = next(line for line in DECISION_LOG.read_text().splitlines() if line.startswith("| DL-128 "))
    assert "C160 requires at least 47 qualified airline tasks" in row

    airline = {s["split"]: s for s in audit("c160", "tau2")["splits"]}["airline"]
    assert airline["registered_minimum_units"] == 47
    # Quota 25 + two pilots would be 27; the registered floor wins.
    assert required_units_lower_bound(airline, "C160") == 47
    assert required_units({**airline, "fixed_reserve": 0, "hamilton_allocation": 0}, "C160") == 47

    # Where the arithmetic exceeds the floor, the arithmetic wins instead.
    assert required_units({**airline, "fixed_reserve": 0, "hamilton_allocation": 40}, "C160") == 67


def test_splits_without_a_registered_floor_use_the_inequality() -> None:
    """A null floor is a genuine state, not missing authority, so it fails open."""

    banking = {s["split"]: s for s in audit("c160", "tau2")["splits"]}["banking"]
    assert banking["registered_minimum_units"] is None
    assert unfixed_requirement_terms(banking, "C160") == ("fixed_reserve", "hamilton_allocation")
    assert required_units_lower_bound(banking, "C160") == 17


def test_committed_fixtures_leave_the_authority_terms_unfixed() -> None:
    """The registered authority fixes neither reserves nor Hamilton places."""

    for family in ("swe", "tau2"):
        for tier in ("c120", "c160"):
            record = validate_qualification_audit(audit(tier, family))
            for split in record["splits"]:
                assert split["fixed_reserve"] is None
                assert split["hamilton_allocation"] is None
            assert evaluate_roster_gate(record)["authority_complete"] is False


def test_unfixed_terms_can_never_reach_a_feasible_verdict(tmp_path: Path) -> None:
    """Even a fully evidenced, abundantly stocked split stays a no-go."""

    root, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt, basis="base_commit_admissible", fix_terms=False)
    for split in record["splits"]:
        split["confirmation_quota"] = 1
    evaluation = evaluate_roster_gate(record, evidence_root=root)
    assert evaluation["verdict"] == NO_GO
    assert evaluation["authority_complete"] is False
    assert all(split["credited_eligible"] == 0 for split in evaluation["splits"])
    assert all("fixed_reserve" in split["unfixed_requirement_terms"] for split in evaluation["splits"])

    # Supplying the authority values is what unlocks it — nothing else changes.
    for split in record["splits"]:
        split["fixed_reserve"] = 0
        split["hamilton_allocation"] = 0
    assert evaluate_roster_gate(record, evidence_root=root)["verdict"] == FEASIBLE


# ---------------------------------------------------------------------------
# Pool semantics.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("family,tier", [("swe", "c120"), ("swe", "c160"), ("tau2", "c120"), ("tau2", "c160")])
def test_proxy_metadata_is_never_qualification(family: str, tier: str, tmp_path: Path) -> None:
    root, _ = _mirror(tmp_path)
    evaluation = evaluate_roster_gate(audit(tier, family), evidence_root=root)
    assert evaluation["verdict"] == NO_GO
    assert all(split["credited_eligible"] == 0 for split in evaluation["splits"])
    with pytest.raises(CloudManifestError):
        require_roster_gate_satisfied([audit(tier, family)], evidence_root=root, lock=_lock())


@pytest.mark.parametrize("tier,starved", [("c120", {"C": 11, "C++": 16}), ("c160", {"C": 14})])
def test_metadata_proxy_shortfall_is_provisional_not_a_determination(tier: str, starved: dict, tmp_path: Path) -> None:
    """A current-metadata proxy cannot support an unsatisfiable-by-audit claim."""

    root, receipt = _mirror(tmp_path)
    evaluation = evaluate_roster_gate(_fully_audited(tier, receipt), evidence_root=root)
    assert evaluation["verdict"] == NO_GO
    assert not any(split["unsatisfiable_by_audit"] for split in evaluation["splits"])
    provisional = {s["split"]: s["required_lower_bound"] for s in evaluation["splits"] if s["provisional_unsatisfiable"]}
    assert provisional == starved


@pytest.mark.parametrize("tier,starved", [("c120", {"C": 11, "C++": 16}), ("c160", {"C": 14})])
def test_base_commit_pool_shortfall_is_unsatisfiable_by_audit(tier: str, starved: dict, tmp_path: Path) -> None:
    root, receipt = _mirror(tmp_path)
    evaluation = evaluate_roster_gate(_fully_audited(tier, receipt, basis="base_commit_admissible"), evidence_root=root)
    assert evaluation["verdict"] == UNSATISFIABLE
    assert {s["split"]: s["required_lower_bound"] for s in evaluation["splits"] if s["unsatisfiable_by_audit"]} == starved


def test_eligibility_may_exceed_a_metadata_proxy_but_not_the_admissible_pool(tmp_path: Path) -> None:
    """A base-commit-eligible lineage can sit outside the current-metadata proxy."""

    _, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt)
    record["splits"][0]["eligible_units"] = record["splits"][0]["proxy_units"] + 3
    assert validate_qualification_audit(record)["splits"][0]["eligible_units"] == 12

    record["proxy_basis"] = "base_commit_admissible"
    with pytest.raises(CloudManifestError):
        validate_qualification_audit(record)


def test_a_metadata_basis_record_can_never_reach_feasible(tmp_path: Path) -> None:
    """The weak basis cannot bound eligibility, so it cannot license a GO."""

    root, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt)
    for split in record["splits"]:
        split["confirmation_quota"] = 1
        split["eligible_units"] = split["proxy_units"] * 1000
    assert evaluate_roster_gate(record, evidence_root=root)["verdict"] == NO_GO
    with pytest.raises(CloudManifestError):
        require_roster_gate_satisfied([record], evidence_root=root, lock=_lock())


# ---------------------------------------------------------------------------
# Family separation.
# ---------------------------------------------------------------------------


def test_a_family_may_not_borrow_the_other_families_pool() -> None:
    """A basis belongs to a family; using the other one is a category error."""

    swe = audit("c120", "swe")
    swe["proxy_basis"] = "pinned_objective_pool"
    with pytest.raises(CloudManifestError, match="not a valid pool for the 'swe' family"):
        validate_qualification_audit(swe)

    tau2 = audit("c120", "tau2")
    tau2["proxy_basis"] = "base_commit_admissible"
    with pytest.raises(CloudManifestError, match="not a valid pool for the 'tau2' family"):
        validate_qualification_audit(tau2)


def test_evaluation_reports_the_unit_each_family_counts() -> None:
    assert evaluate_roster_gate(audit("c120", "swe"))["unit_kind"] == "root_lineage"
    assert evaluate_roster_gate(audit("c120", "tau2"))["unit_kind"] == "task"


def test_swe_qualification_alone_does_not_satisfy_the_gate(tmp_path: Path) -> None:
    """The central family-separation property: SWE evidence is not tau2 evidence."""

    root, receipt = _mirror(tmp_path)
    swe, tau2 = _both_families(receipt)

    # Each alone is a satisfied audit for its own family...
    assert evaluate_roster_gate(swe, evidence_root=root)["verdict"] == FEASIBLE
    assert evaluate_roster_gate(tau2, evidence_root=root)["verdict"] == FEASIBLE

    # ...but neither alone opens the gate.
    for lone in (swe, tau2):
        with pytest.raises(CloudManifestError, match="missing a qualification audit"):
            require_roster_gate_satisfied([lone], evidence_root=root, lock=_lock())

    result = require_roster_gate_satisfied([swe, tau2], evidence_root=root, lock=_lock())
    assert set(result["families"]) == {"swe", "tau2"}
    assert result["tier"] == "C120"


def test_duplicate_family_submissions_are_refused(tmp_path: Path) -> None:
    root, receipt = _mirror(tmp_path)
    swe, _ = _both_families(receipt)
    with pytest.raises(CloudManifestError, match="duplicate qualification audit"):
        require_roster_gate_satisfied([swe, json.loads(json.dumps(swe))], evidence_root=root, lock=_lock())


def test_gate_refuses_audits_describing_different_tiers(tmp_path: Path) -> None:
    root, receipt = _mirror(tmp_path)
    swe, _ = _both_families(receipt, "c120")
    _, tau2_c160 = _both_families(receipt, "c160")
    with pytest.raises(CloudManifestError, match="must all describe one tier"):
        require_roster_gate_satisfied([swe, tau2_c160], evidence_root=root, lock=_lock())


def test_only_registered_tiers_are_accepted() -> None:
    """No tau2-only tier may be introduced through this record."""

    record = audit("c120", "tau2")
    record["tier"] = "TAU2-ONLY"
    with pytest.raises(CloudManifestError):
        validate_qualification_audit(record)


# ---------------------------------------------------------------------------
# Evidence resolution.
# ---------------------------------------------------------------------------


def test_gate_is_a_consistency_check_not_an_authenticity_check(tmp_path: Path) -> None:
    """State the guard's real strength: it catches incoherence, not forgery.

    A party who can write both the audit record and the evidence files can
    satisfy it, because the receipt digests live in the record they attest.
    That limit is disclosed in `require_roster_gate_satisfied` and doc 51; this
    test pins the actual behaviour so nobody mistakes it for authentication.
    """

    root, receipt = _mirror(tmp_path)
    records = _both_families(receipt)
    for record in records:
        for split in record["splits"]:
            split["proxy_units"] = 999
            split["eligible_units"] = 999
    assert require_roster_gate_satisfied(records, evidence_root=root, lock=_lock())["tier"] == "C120"

    # Same records, but the receipts do not resolve to real bytes.
    forged = json.loads(json.dumps(records))
    for record in forged:
        for split in record["splits"]:
            split["isolation_evidence"] = {"relative_path": "receipts/audit.json", "sha256": _HEX}
    assert evaluate_roster_gate(forged[0], evidence_root=root)["verdict"] == NO_GO
    # And with no evidence root at all, nothing is credited.
    assert evaluate_roster_gate(records[0])["verdict"] == NO_GO
    with pytest.raises(CloudManifestError):
        require_roster_gate_satisfied(records, evidence_root=tmp_path / "absent", lock=_lock())


def test_gate_requires_the_bound_input_lock(tmp_path: Path) -> None:
    root, receipt = _mirror(tmp_path)
    records = _both_families(receipt)
    assert require_roster_gate_satisfied(records, evidence_root=root, lock=_lock())["tier"] == "C120"
    other = _lock()
    other["model_pins"][0]["repository"] = "org/other-model"
    with pytest.raises(CloudManifestError, match="not bound to this input-lock digest"):
        require_roster_gate_satisfied(records, evidence_root=root, lock=other)


def test_incomplete_split_evidence_credits_nothing(tmp_path: Path) -> None:
    root, receipt = _mirror(tmp_path)
    record, _ = _both_families(receipt)
    assert evaluate_roster_gate(record, evidence_root=root)["verdict"] == FEASIBLE

    for field in ("isolation_evidence", "license_evidence"):
        broken = json.loads(json.dumps(record))
        broken["splits"][0][field] = None
        evaluation = evaluate_roster_gate(broken, evidence_root=root)
        assert evaluation["verdict"] == NO_GO
        assert evaluation["splits"][0]["credited_eligible"] == 0

    broken = json.loads(json.dumps(record))
    broken["splits"][0]["three_pair_audit"] = {"pairs_attempted": 3, "pairs_independent_pass": 2}
    assert evaluate_roster_gate(broken, evidence_root=root)["verdict"] == NO_GO


def test_passing_pairs_cannot_exceed_attempted_pairs(tmp_path: Path) -> None:
    _, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt)
    record["splits"][0]["three_pair_audit"] = {"pairs_attempted": 2, "pairs_independent_pass": 3}
    with pytest.raises(CloudManifestError):
        validate_qualification_audit(record)


def test_audited_record_must_bind_an_input_lock(tmp_path: Path) -> None:
    _, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt)
    record["input_lock_sha256"] = None
    with pytest.raises(CloudManifestError):
        validate_qualification_audit(record)
