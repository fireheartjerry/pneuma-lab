"""Narrow tests for the fail-closed result-to-paper pipeline.

Every package fixture here is synthetic. The tests verify that the pipeline
refuses the packages it must refuse, that the manuscript checks fire on the
real manuscript, and that no generated asset can carry a number the pipeline
did not emit.

    python -m pytest tests/placebo_paper -q
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pneuma_lab.placebo_paper import admit, checks, run, write_assets
from pneuma_lab.placebo_paper.cli import main as cli_main
from pneuma_lab.placebo_paper.errors import (
    MissingReceipt,
    PackageRejected,
    UnsealedPackage,
    WrongAuthority,
    WrongLineage,
)
from pneuma_lab.placebo_paper.render import UNFILLED, figure_data, primary_table

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures" / "placebo_paper"
PAPER = REPO_ROOT / "paper"
MANUSCRIPT = PAPER / "placebo_protocol.tex"


# --------------------------------------------------------------------------
# Package admission: the refusals that matter
# --------------------------------------------------------------------------


def test_admissible_package_is_admitted() -> None:
    package = admit(FIXTURES / "admissible")
    assert package.lineage == "canonical_confirmation"
    assert package.verdict == "UNRESOLVED_RESAMPLING"
    assert package.number("resolution.r95") == pytest.approx(0.042)


def test_step_4a_is_refused_by_name() -> None:
    with pytest.raises(WrongLineage, match="Step 4A"):
        admit(FIXTURES / "step4a")


def test_incomplete_p0_root_is_refused() -> None:
    with pytest.raises(WrongLineage, match="incomplete non-result"):
        admit(FIXTURES / "p0_incomplete")


def test_unsealed_package_is_refused() -> None:
    with pytest.raises(UnsealedPackage, match="not sealed"):
        admit(FIXTURES / "unsealed")


def test_unverified_artifact_root_is_refused() -> None:
    with pytest.raises(UnsealedPackage, match="recursive verification"):
        admit(FIXTURES / "unverified_root")


def test_package_without_a_completed_unblind_is_refused() -> None:
    with pytest.raises(UnsealedPackage, match="unblind ceremony"):
        admit(FIXTURES / "no_unblind")


def test_wrong_authority_is_refused() -> None:
    with pytest.raises(WrongAuthority, match="does not license"):
        admit(FIXTURES / "wrong_authority")


def test_missing_receipt_is_refused() -> None:
    with pytest.raises(MissingReceipt, match="unblind_receipt"):
        admit(FIXTURES / "missing_receipt")


def test_verdict_outside_the_taxonomy_is_refused() -> None:
    with pytest.raises(PackageRejected, match="not in the preregistered taxonomy"):
        admit(FIXTURES / "bad_verdict")


def test_a_directory_is_not_a_package(tmp_path: Path) -> None:
    with pytest.raises(PackageRejected, match="not a package"):
        admit(tmp_path)


def test_a_number_the_package_did_not_emit_cannot_be_supplied() -> None:
    package = admit(FIXTURES / "admissible")
    with pytest.raises(PackageRejected, match="may not supply one by hand"):
        package.number("content.estimate_but_nicer")


def test_the_admissible_fixture_labels_itself_synthetic() -> None:
    payload = json.loads(
        (FIXTURES / "admissible" / "package.json").read_text(encoding="utf-8")
    )
    assert "SYNTHETIC" in payload["synthetic_fixture_notice"]
    assert "never be cited" in payload["synthetic_fixture_notice"]


# --------------------------------------------------------------------------
# Generated assets
# --------------------------------------------------------------------------


def test_scaffold_without_a_package_is_entirely_unfilled(tmp_path: Path) -> None:
    written = write_assets(tmp_path, None, [])
    assert set(written) == {
        "table-primary.tex",
        "table-resolution.tex",
        "table-environments.tex",
        "table-claim-evidence.tex",
        "appendix-artifacts.tex",
        "figure-data.json",
    }
    table = (tmp_path / "table-primary.tex").read_text(encoding="utf-8")
    assert UNFILLED in table
    assert "0." not in table.replace("0.45", ""), "no value may appear without a package"
    data = json.loads((tmp_path / "figure-data.json").read_text(encoding="utf-8"))
    assert data["source"] == "unfilled_scaffold"
    assert all(value is None for value in data["series"].values())


def test_scaffold_and_filled_table_have_the_same_row_set(tmp_path: Path) -> None:
    package = admit(FIXTURES / "admissible")
    empty = primary_table(None).splitlines()
    filled = primary_table(package).splitlines()
    assert len(empty) == len(filled), "the row set is frozen; only values change"
    assert UNFILLED not in "\n".join(filled)


def test_figure_data_binds_the_artifact_root() -> None:
    package = admit(FIXTURES / "admissible")
    data = figure_data(package)
    assert data["artifact_root_digest"] == package.artifact_root_digest
    assert data["verdict"] == package.verdict


def test_claim_matrix_marks_a_receipt_the_package_lacks(tmp_path: Path) -> None:
    package = admit(FIXTURES / "admissible")
    write_assets(
        tmp_path,
        package,
        [{"claim_id": "X1", "text": "unsupported", "receipt": "not_a_receipt"}],
    )
    text = (tmp_path / "table-claim-evidence.tex").read_text(encoding="utf-8")
    assert "MISSING" in text


def test_artifact_appendix_lists_every_receipt(tmp_path: Path) -> None:
    package = admit(FIXTURES / "admissible")
    write_assets(tmp_path, package, [])
    text = (tmp_path / "appendix-artifacts.tex").read_text(encoding="utf-8")
    for name in package.receipts:
        assert name in text


# --------------------------------------------------------------------------
# Manuscript checks
# --------------------------------------------------------------------------


def test_placeholder_check_fires_on_the_pre_results_manuscript() -> None:
    result = checks.check_placeholders(MANUSCRIPT.read_text(encoding="utf-8"))
    assert result.status == "fail"
    assert any("result slot" in item for item in result.findings)


def test_manuscript_is_currently_anonymous() -> None:
    result = checks.check_anonymity(MANUSCRIPT.read_text(encoding="utf-8"))
    assert result.status == "pass", result.findings


def test_anonymity_check_catches_an_identifying_string() -> None:
    result = checks.check_anonymity("Our repo is at github.com/someone/somerepo.\n")
    assert result.status == "fail"


def test_novelty_discipline_catches_a_prohibited_phrasing() -> None:
    result = checks.check_forbidden_novelty_claims(
        "We present the first placebo-controlled evaluation of agent feedback.\n"
    )
    assert result.status == "fail"


def test_manuscript_makes_no_prohibited_novelty_claim() -> None:
    result = checks.check_forbidden_novelty_claims(
        MANUSCRIPT.read_text(encoding="utf-8")
    )
    assert result.status == "pass", result.findings


def test_number_provenance_catches_a_hand_entered_measured_value() -> None:
    result = checks.check_number_provenance(
        "We find a gain of 4.2 percentage points over the control.\n", ()
    )
    assert result.status == "fail"


def test_bibliography_check_blocks_on_the_unresolved_citation_queue() -> None:
    queue = {
        "entries": [
            {"key": "synthetic_unresolved_source", "state": "unresolved"}
        ]
    }
    result = checks.check_bibliography("", [], queue)
    assert result.status == "fail"
    assert any("synthetic_unresolved_source" in item for item in result.findings)


def test_live_citation_queue_is_fully_verified() -> None:
    queue = json.loads(
        (PAPER / "placebo" / "citation-queue.json").read_text(encoding="utf-8")
    )
    result = checks.check_bibliography("", [], queue)
    assert result.status == "pass", result.findings


def test_every_manuscript_citation_resolves_to_a_bib_entry() -> None:
    bibs = [
        (PAPER / "refs.bib").read_text(encoding="utf-8"),
        (PAPER / "placebo" / "refs-placebo.bib").read_text(encoding="utf-8"),
    ]
    result = checks.check_bibliography(
        MANUSCRIPT.read_text(encoding="utf-8"), bibs, None
    )
    assert result.status == "pass", result.findings


def test_page_budget_is_reported_as_an_estimate() -> None:
    result = checks.check_page_budget(MANUSCRIPT.read_text(encoding="utf-8"))
    assert result.status in ("pending", "fail")
    assert "SOURCE estimate" in result.detail


def test_pdf_checks_are_pending_not_passing(tmp_path: Path) -> None:
    results = checks.check_pdf_dependent(tmp_path / "nothing.pdf")
    assert results
    assert all(item.status == "pending" for item in results)


# --------------------------------------------------------------------------
# Preflight
# --------------------------------------------------------------------------


def test_preflight_blocks_the_pre_results_manuscript() -> None:
    report = run(
        MANUSCRIPT,
        bib_paths=(PAPER / "refs.bib", PAPER / "placebo" / "refs-placebo.bib"),
        citation_queue_path=PAPER / "placebo" / "citation-queue.json",
        package_path=None,
    )
    assert not report.submission_ready
    names = {item.name for item in report.failures}
    assert {"placeholders", "evidence_package"} <= names
    assert "bibliography" not in names


def test_preflight_reports_a_rejected_package_by_reason() -> None:
    report = run(MANUSCRIPT, package_path=FIXTURES / "step4a")
    assert report.package_state == "rejected"
    assert "Step 4A" in report.package_detail


def test_preflight_never_passes_a_pdf_check_without_a_pdf() -> None:
    report = run(MANUSCRIPT, pdf_path=REPO_ROOT / "does-not-exist.pdf")
    pdf_results = [item for item in report.results if item.name.startswith("pdf_")]
    assert pdf_results
    assert all(item.status == "pending" for item in pdf_results)


def test_preflight_render_is_deterministic() -> None:
    first = run(MANUSCRIPT).render()
    second = run(MANUSCRIPT).render()
    assert first == second


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def test_cli_preflight_exits_nonzero_while_blocked(capsys) -> None:
    assert cli_main(["preflight"]) == 1
    assert "preflight BLOCKED" in capsys.readouterr().out


def test_cli_admit_refuses_step_4a(capsys) -> None:
    assert cli_main(["admit", "--package", str(FIXTURES / "step4a")]) == 2
    assert "REFUSED: WrongLineage" in capsys.readouterr().err


def test_cli_render_writes_the_scaffold(tmp_path: Path, capsys) -> None:
    assert cli_main(["render", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "table-primary.tex").is_file()
    assert "table-primary.tex" in capsys.readouterr().out


# --------------------------------------------------------------------------
# Guardrails on the manuscript itself
# --------------------------------------------------------------------------


def test_canonical_entrypoint_and_archived_sources() -> None:
    """main.tex selects the trial; the retired draft and style stay untouched."""

    import subprocess

    changed = subprocess.run(
        ["git", "diff", "--name-only", "934ff2c", "--", "paper/"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split()
    for protected in ("paper/placebo.tex", "paper/neurips_2026.sty"):
        assert protected not in changed, f"{protected} must not be modified"

    entrypoint = (PAPER / "main.tex").read_text(encoding="utf-8")
    assert "\\input{placebo_protocol.tex}" in entrypoint
    assert "Ten Conversations, Two Thousand Questions" not in entrypoint


def test_placebo_acronym_is_the_manuscript_contract() -> None:
    source = MANUSCRIPT.read_text(encoding="utf-8")
    assert "\\title{The PLACEBO Trial: Isolating the Causal Effect of" in source
    assert "\\newcommand{\\placeboexpanded}" in source
    assert "The name is the contract." in source
    assert source.count("\\placeboexpanded") >= 3
    for component in (
        "Preregistered",
        "L}abel-Blind",
        "A}rm-Controlled",
        "C}ausal",
        "E}valuation",
        "B}ehavioral",
        "O}utcomes",
    ):
        assert component in source
