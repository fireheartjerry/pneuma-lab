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
    required_lineages,
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


def audit(tier: str) -> dict:
    return json.loads((FIXTURES / f"qualification-audit-{tier}-proxy.json").read_text())


def _mirror(tmp_path: Path) -> tuple[Path, dict]:
    """Write real evidence bytes and return the root plus a matching receipt."""

    payload = b"qualification-evidence"
    (tmp_path / "receipts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "receipts" / "audit.json").write_bytes(payload)
    return tmp_path, {"relative_path": "receipts/audit.json", "sha256": hashlib.sha256(payload).hexdigest()}


def _fully_audited(tier: str, receipt: dict, *, basis: str = "current_repository_metadata") -> dict:
    record = audit(tier)
    record["evidence_class"] = "audited_qualified"
    record["proxy_basis"] = basis
    record["input_lock_sha256"] = _lock_digest()
    for split in record["splits"]:
        split["isolation_evidence"] = dict(receipt)
        split["license_evidence"] = dict(receipt)
        split["three_pair_audit"] = {"pairs_attempted": 3, "pairs_independent_pass": 3}
        split["eligible_lineages"] = split["proxy_lineages"]
    return record


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
        assert split["proxy_lineages"] == expected_proxy[split["split"]]
        assert split["confirmation_quota"] == expected_quota[split["split"]]
    # DL-128's stated C120 minima fall straight out of the inequality.
    by_name = {split["split"]: split for split in audit("c120")["splits"]}
    assert required_lineages(by_name["C"]) == 11
    assert required_lineages(by_name["C++"]) == 16
    assert required_lineages({s["split"]: s for s in audit("c160")["splits"]}["C"]) == 14


def test_inequality_matches_the_registered_contract() -> None:
    assert required_lineages({"confirmation_quota": 9, "pilot_lineages": 1, "fixed_reserve": 3}) == 14


@pytest.mark.parametrize("tier", ["c120", "c160"])
def test_proxy_metadata_is_never_qualification(tier: str, tmp_path: Path) -> None:
    root, _ = _mirror(tmp_path)
    evaluation = evaluate_roster_gate(audit(tier), evidence_root=root)
    assert evaluation["verdict"] == NO_GO
    assert all(split["credited_eligible"] == 0 for split in evaluation["splits"])
    with pytest.raises(CloudManifestError):
        require_roster_gate_satisfied(audit(tier), evidence_root=root, lock=_lock())


@pytest.mark.parametrize("tier,starved", [("c120", {"C": 11, "C++": 16}), ("c160", {"C": 14})])
def test_metadata_proxy_shortfall_is_provisional_not_a_determination(tier: str, starved: dict, tmp_path: Path) -> None:
    """A current-metadata proxy cannot support an unsatisfiable-by-audit claim."""

    root, receipt = _mirror(tmp_path)
    evaluation = evaluate_roster_gate(_fully_audited(tier, receipt), evidence_root=root)
    assert evaluation["verdict"] == NO_GO
    assert not any(split["unsatisfiable_by_audit"] for split in evaluation["splits"])
    provisional = {s["split"]: s["required"] for s in evaluation["splits"] if s["provisional_unsatisfiable"]}
    assert provisional == starved


@pytest.mark.parametrize("tier,starved", [("c120", {"C": 11, "C++": 16}), ("c160", {"C": 14})])
def test_base_commit_pool_shortfall_is_unsatisfiable_by_audit(tier: str, starved: dict, tmp_path: Path) -> None:
    root, receipt = _mirror(tmp_path)
    evaluation = evaluate_roster_gate(_fully_audited(tier, receipt, basis="base_commit_admissible"), evidence_root=root)
    assert evaluation["verdict"] == UNSATISFIABLE
    assert {s["split"]: s["required"] for s in evaluation["splits"] if s["unsatisfiable_by_audit"]} == starved


def test_eligibility_may_exceed_a_metadata_proxy_but_not_the_admissible_pool(tmp_path: Path) -> None:
    """A base-commit-eligible lineage can sit outside the current-metadata proxy."""

    _, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt)
    record["splits"][0]["eligible_lineages"] = record["splits"][0]["proxy_lineages"] + 3
    assert validate_qualification_audit(record)["splits"][0]["eligible_lineages"] == 12

    record["proxy_basis"] = "base_commit_admissible"
    with pytest.raises(CloudManifestError):
        validate_qualification_audit(record)


def test_gate_is_a_consistency_check_not_an_authenticity_check(tmp_path: Path) -> None:
    """State the guard's real strength: it catches incoherence, not forgery.

    A party who can write both the audit record and the evidence files can
    satisfy it, because the receipt digests live in the record they attest.
    That limit is disclosed in `require_roster_gate_satisfied` and doc 49; this
    test pins the actual behaviour so nobody mistakes it for authentication.
    """

    root, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt, basis="base_commit_admissible")
    for split in record["splits"]:
        split["proxy_lineages"] = 999
        split["eligible_lineages"] = 999
        split["confirmation_quota"] = 1
    assert evaluate_roster_gate(record, evidence_root=root)["verdict"] == FEASIBLE

    # Same record, but the receipts do not resolve to real bytes.
    forged = json.loads(json.dumps(record))
    for split in forged["splits"]:
        split["isolation_evidence"] = {"relative_path": "receipts/audit.json", "sha256": _HEX}
    assert evaluate_roster_gate(forged, evidence_root=root)["verdict"] == NO_GO
    # And with no evidence root at all, nothing is credited.
    assert evaluate_roster_gate(record)["verdict"] == NO_GO
    with pytest.raises(CloudManifestError):
        require_roster_gate_satisfied(record, evidence_root=tmp_path / "absent", lock=_lock())


def test_gate_requires_the_bound_input_lock(tmp_path: Path) -> None:
    root, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt, basis="base_commit_admissible")
    for split in record["splits"]:
        split["confirmation_quota"] = 1
    assert require_roster_gate_satisfied(record, evidence_root=root, lock=_lock())["verdict"] == FEASIBLE
    other = _lock()
    other["model_pins"][0]["repository"] = "org/other-model"
    with pytest.raises(CloudManifestError):
        require_roster_gate_satisfied(record, evidence_root=root, lock=other)


def test_incomplete_split_evidence_credits_nothing(tmp_path: Path) -> None:
    root, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt, basis="base_commit_admissible")
    for split in record["splits"]:
        split["confirmation_quota"] = 1
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


def test_a_metadata_basis_record_can_never_reach_feasible(tmp_path: Path) -> None:
    """The weak basis cannot bound eligibility, so it cannot license a GO."""

    root, receipt = _mirror(tmp_path)
    record = _fully_audited("c120", receipt)
    for split in record["splits"]:
        split["confirmation_quota"] = 1
        split["eligible_lineages"] = split["proxy_lineages"] * 1000
    evaluation = evaluate_roster_gate(record, evidence_root=root)
    assert evaluation["verdict"] == NO_GO
    with pytest.raises(CloudManifestError):
        require_roster_gate_satisfied(record, evidence_root=root, lock=_lock())
