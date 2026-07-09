"""Commit provenance and fail-closed official evidence generation (G-12)."""

from __future__ import annotations

import subprocess

import pytest

from pneuma_lab import demo


_COMMIT = "a" * 40


def _provenance(*, dirty: bool = False, published: bool = True):
    refs = ("origin/main",) if published else ()
    return demo.RepositoryProvenance(
        commit=_COMMIT,
        dirty=dirty,
        remote_refs=refs,
    )


def test_live_repository_provenance_identifies_head() -> None:
    expected = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()

    provenance = demo.collect_repository_provenance()

    assert provenance.commit == expected
    assert len(provenance.commit) == 40


def test_regular_summary_records_non_official_source_provenance(tmp_path) -> None:
    summary = demo.run_canonical(
        tmp_path,
        provenance=_provenance(dirty=True, published=False),
    )

    assert summary["source_provenance"] == {
        "source_kind": "git",
        "git_commit": _COMMIT,
        "tree_state": "dirty",
        "remote_refs_containing_commit": [],
        "commit_published": False,
        "official": False,
    }
    markdown = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert _COMMIT in markdown
    assert "official: no" in markdown


@pytest.mark.parametrize(
    ("provenance", "reason"),
    [
        (_provenance(dirty=True), "working tree is dirty"),
        (_provenance(published=False), "not contained in any fetched remote ref"),
    ],
)
def test_official_summary_refuses_unverifiable_source(
    tmp_path,
    provenance,
    reason,
) -> None:
    with pytest.raises(demo.EvidenceProvenanceError, match=reason):
        demo.run_canonical(tmp_path, official=True, provenance=provenance)

    assert list(tmp_path.iterdir()) == []


def test_official_summary_marks_clean_published_source(tmp_path) -> None:
    summary = demo.run_canonical(
        tmp_path,
        official=True,
        provenance=_provenance(),
    )

    source = summary["source_provenance"]
    assert source["git_commit"] == _COMMIT
    assert source["tree_state"] == "clean"
    assert source["commit_published"] is True
    assert source["official"] is True


def test_official_cli_returns_nonzero_before_writing_on_dirty_tree(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        demo,
        "collect_repository_provenance",
        lambda: _provenance(dirty=True),
    )

    assert demo.main(["--official", "-o", str(tmp_path)]) == 2
    assert list(tmp_path.iterdir()) == []
