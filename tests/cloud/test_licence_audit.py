from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.licence_audit import (
    ADMITTING_REASON,
    DERIVATION_COMMAND,
    Observation,
    derive_audit,
    language_counts,
    main,
    qualification_digest,
    roster_digest,
    validate_licence_audit,
    verify_licence_evidence,
)


PINNED = {
    # The DL-128 frozen SWE-bench-Live identities.
    "benchmark_repository": "microsoft/SWE-bench-Live",
    "benchmark_revision": "70ec57e852e3f2d195790fe71f553e272c691833",
    "dataset_revision": "608f7ae9ab8ea1f9f0d030fe04562cf6bd1a0c8b",
    "task_manifest_sha256": hashlib.sha256(b"task-manifest").hexdigest(),
}

ROSTER = [
    {"root_lineage": "acme/alpha", "language": "C", "base_commit": "a1" * 20},
    {"root_lineage": "acme/beta", "language": "C", "base_commit": "b2" * 20},
    {"root_lineage": "acme/gamma", "language": "C++", "base_commit": "c3" * 20},
    {"root_lineage": "acme/delta", "language": "C++", "base_commit": "d4" * 20},
]

_VERDICTS = {
    "acme/alpha": ("MIT", True, ADMITTING_REASON),
    "acme/beta": (None, False, "no_licence_at_base_commit"),
    "acme/gamma": ("Apache-2.0", True, ADMITTING_REASON),
    "acme/delta": ("GPL-3.0-only", False, "non_permissive_licence_at_base_commit"),
}


def _observer(payloads: dict[str, bytes] | None = None):
    def observe(candidate):
        name = candidate["root_lineage"]
        licence, admitted, reason = _VERDICTS[name]
        payload = (payloads or {}).get(name, f"LICENCE bytes for {name}".encode())
        return Observation(
            licence=licence,
            payload=payload,
            relative_path=f"licences/{name.replace('/', '_')}.txt",
            admitted=admitted,
            reason=reason,
        )
    return observe


def _audit(**kwargs):
    params = {
        "frozen_timestamp": "2026-07-31T00:00:00Z",
        "pinned_inputs": PINNED,
        "roster": ROSTER,
        "observe": _observer(),
        "evidence_root": "build/licence-evidence",
    }
    params.update(kwargs)
    return derive_audit(**params)


# ---------------------------------------------------------------------------
# The derivation is reproducible and self-consistent.
# ---------------------------------------------------------------------------


def test_derivation_is_deterministic_and_revalidates() -> None:
    first, second = _audit(), _audit()
    assert first == second
    assert validate_licence_audit(first) == first
    assert first["derivation"]["command"] == list(DERIVATION_COMMAND)


def test_record_carries_every_reproducibility_element() -> None:
    audit = _audit()
    # Deterministic derivation command and the code that produced the record.
    assert audit["derivation"]["command"] and audit["derivation"]["code_sha256"]
    # Pinned dataset and task-manifest digests.
    assert audit["pinned_inputs"]["dataset_revision"] == PINNED["dataset_revision"]
    assert audit["pinned_inputs"]["task_manifest_sha256"] == PINNED["task_manifest_sha256"]
    # Ordered roster with base commits, reasons, and evidence hashes.
    assert [item["root_lineage"] for item in audit["lineages"]] == [item["root_lineage"] for item in ROSTER]
    assert all(item["base_commit"] and item["reason"] for item in audit["lineages"])
    assert all(item["licence_evidence"]["sha256"] for item in audit["lineages"])
    # Per-language counts and a receipt bound to code and inputs.
    assert audit["language_counts"] == {"C": 1, "C++": 1}
    assert audit["receipt"]["qualification_sha256"] == qualification_digest(
        code_sha256=audit["derivation"]["code_sha256"],
        roster_sha256=audit["receipt"]["roster_sha256"],
        inputs_sha256=audit["receipt"]["inputs_sha256"],
    )


def test_every_lineage_carries_an_explicit_inclusion_or_exclusion_reason() -> None:
    audit = _audit()
    reasons = {item["root_lineage"]: item["reason"] for item in audit["lineages"]}
    assert reasons == {name: verdict[2] for name, verdict in _VERDICTS.items()}
    # Exclusions are recorded, not dropped: the roster keeps all four.
    assert len(audit["lineages"]) == len(ROSTER)


def test_roster_order_is_part_of_the_record() -> None:
    """A reordered roster is a different roster, so the receipt must change."""

    audit = _audit()
    reordered = list(reversed(audit["lineages"]))
    assert roster_digest(reordered) != audit["receipt"]["roster_sha256"]
    tampered = json.loads(json.dumps(audit))
    tampered["lineages"] = reordered
    with pytest.raises(CloudManifestError, match="roster digest does not match"):
        validate_licence_audit(tampered)


# ---------------------------------------------------------------------------
# Counts and receipts are recomputed, never believed.
# ---------------------------------------------------------------------------


def test_language_counts_are_derived_not_asserted() -> None:
    audit = _audit()
    tampered = json.loads(json.dumps(audit))
    tampered["language_counts"] = {"C": 9, "C++": 14}
    with pytest.raises(CloudManifestError, match="disagree with the roster"):
        validate_licence_audit(tampered)


def test_counts_follow_the_admissions_not_the_roster_size() -> None:
    assert language_counts([
        {"language": "C", "admitted": True},
        {"language": "C", "admitted": False},
        {"language": "Rust", "admitted": True},
    ]) == {"C": 1, "Rust": 1}


@pytest.mark.parametrize("field", ["roster_sha256", "inputs_sha256", "qualification_sha256"])
def test_a_tampered_receipt_digest_is_refused(field: str) -> None:
    audit = json.loads(json.dumps(_audit()))
    audit["receipt"][field] = "0" * 64
    with pytest.raises(CloudManifestError):
        validate_licence_audit(audit)


def test_receipt_is_bound_to_the_deriving_code() -> None:
    """Re-deriving with different code must not reuse the old receipt."""

    audit = json.loads(json.dumps(_audit()))
    audit["derivation"]["code_sha256"] = "f" * 64
    with pytest.raises(CloudManifestError, match="not bound to this code, roster, and inputs"):
        validate_licence_audit(audit)


def test_receipt_is_bound_to_the_pinned_inputs() -> None:
    audit = json.loads(json.dumps(_audit()))
    audit["pinned_inputs"]["dataset_revision"] = "e" * 40
    with pytest.raises(CloudManifestError, match="inputs digest does not match"):
        validate_licence_audit(audit)


def test_receipt_is_bound_to_every_evidence_byte() -> None:
    """Changing one licence file's digest invalidates the whole receipt."""

    baseline = _audit()
    altered = _audit(observe=_observer({"acme/alpha": b"different licence bytes"}))
    assert altered["receipt"]["inputs_sha256"] != baseline["receipt"]["inputs_sha256"]
    assert altered["receipt"]["qualification_sha256"] != baseline["receipt"]["qualification_sha256"]


# ---------------------------------------------------------------------------
# Internal coherence.
# ---------------------------------------------------------------------------


def test_an_admitted_lineage_must_name_its_licence_and_reason() -> None:
    audit = json.loads(json.dumps(_audit()))
    audit["lineages"][0]["licence"] = None
    with pytest.raises(CloudManifestError, match="must name the licence observed"):
        validate_licence_audit(audit)

    audit = json.loads(json.dumps(_audit()))
    audit["lineages"][0]["reason"] = "no_licence_at_base_commit"
    with pytest.raises(CloudManifestError, match="admitted but its reason is"):
        validate_licence_audit(audit)

    audit = json.loads(json.dumps(_audit()))
    audit["lineages"][1]["reason"] = ADMITTING_REASON
    with pytest.raises(CloudManifestError, match="carries the admitting reason but is excluded"):
        validate_licence_audit(audit)


def test_a_verdict_must_reference_the_bytes_it_rests_on() -> None:
    audit = json.loads(json.dumps(_audit()))
    audit["lineages"][1]["licence_evidence"] = None
    with pytest.raises(CloudManifestError, match="must reference the licence bytes"):
        validate_licence_audit(audit)


def test_a_repeated_root_lineage_needs_a_duplicate_verdict() -> None:
    audit = json.loads(json.dumps(_audit()))
    audit["lineages"][1]["root_lineage"] = audit["lineages"][0]["root_lineage"]
    with pytest.raises(CloudManifestError, match="appears more than once"):
        validate_licence_audit(audit)


# ---------------------------------------------------------------------------
# Evidence bytes are re-hashed against the mirrored files.
# ---------------------------------------------------------------------------


def test_evidence_files_are_rehashed(tmp_path: Path) -> None:
    audit = _audit()
    root = tmp_path / "build" / "licence-evidence" / "licences"
    root.mkdir(parents=True)
    for lineage in audit["lineages"]:
        name = lineage["root_lineage"]
        (root / f"{name.replace('/', '_')}.txt").write_bytes(f"LICENCE bytes for {name}".encode())
    assert len(verify_licence_evidence(audit, tmp_path)) == len(ROSTER)

    # A single altered byte fails the whole audit.
    (root / "acme_alpha.txt").write_bytes(b"tampered")
    with pytest.raises(CloudManifestError, match="digest mismatch"):
        verify_licence_evidence(audit, tmp_path)


def test_missing_evidence_bytes_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(CloudManifestError, match="must be a regular non-symlink file"):
        verify_licence_evidence(_audit(), tmp_path)


def test_evidence_may_not_escape_the_evidence_root(tmp_path: Path) -> None:
    audit = json.loads(json.dumps(_audit()))
    # The schema blocks traversal, so an escape attempt is refused at validation.
    audit["lineages"][0]["licence_evidence"]["relative_path"] = "../outside.txt"
    with pytest.raises(CloudManifestError):
        verify_licence_evidence(audit, tmp_path)


# ---------------------------------------------------------------------------
# The audit cannot be manufactured, and proxy prose is not qualification.
# ---------------------------------------------------------------------------


def test_an_unobserved_lineage_fails_the_derivation() -> None:
    """"We did not look" must never be recorded as "we looked and found nothing"."""

    def observe(candidate):
        return None if candidate["root_lineage"] == "acme/beta" else _observer()(candidate)

    with pytest.raises(CloudManifestError, match="an unobserved lineage fails the derivation"):
        _audit(observe=observe)


def test_an_empty_derivation_is_not_an_audit() -> None:
    with pytest.raises(CloudManifestError, match="empty derivation is not an audit"):
        _audit(roster=[])


def test_an_unknown_verdict_is_refused() -> None:
    def observe(candidate):
        return Observation(licence="MIT", payload=b"x", relative_path="licences/x.txt", admitted=True, reason="looks_fine_to_me")

    with pytest.raises(CloudManifestError, match="unknown licence verdict"):
        _audit(observe=observe)


def test_the_derivation_command_refuses_to_synthesise(tmp_path: Path, capsys) -> None:
    """Running the command without real observations fails closed and writes nothing."""

    absent = tmp_path / "observations.json"
    assert main(["derive", "--observations", str(absent)]) == 2
    assert "CL-009/DL-128 proxy prose is not qualification" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())

    # Even with a file present there is no file-driven synthesis path.
    absent.write_text("{}", encoding="utf-8")
    assert main(["derive", "--observations", str(absent)]) == 2
    assert "No file-driven synthesis path exists" in capsys.readouterr().err


def test_the_verify_command_revalidates_a_committed_audit(tmp_path: Path, capsys) -> None:
    audit = _audit()
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    root = tmp_path / "build" / "licence-evidence" / "licences"
    root.mkdir(parents=True)
    for lineage in audit["lineages"]:
        name = lineage["root_lineage"]
        (root / f"{name.replace('/', '_')}.txt").write_bytes(f"LICENCE bytes for {name}".encode())
    assert main(["verify", "--audit", str(path), "--repo-root", str(tmp_path)]) == 0
    assert "licence audit verified" in capsys.readouterr().out


def test_no_committed_licence_audit_exists_yet() -> None:
    """The honest state: the real audit has not been run.

    If this ever fails, a licence audit fixture has appeared and someone must
    confirm it came from real retrieved bytes rather than from proxy prose.
    """

    fixtures = Path(__file__).resolve().parents[2] / "fixtures" / "cloud"
    assert not list(fixtures.glob("licence-audit*.json"))
