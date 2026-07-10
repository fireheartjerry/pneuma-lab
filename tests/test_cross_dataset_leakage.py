from __future__ import annotations

from pneuma_lab.training import leakage_registry as lr


def test_digest_matches_adapter_scheme() -> None:
    from pneuma_lab.adapters import open_swe_traces as a

    assert lr.repo_digest("demo/alpha") == a._digest("demo/alpha")


def test_canonicalize_passes_digests_through_and_digests_raw() -> None:
    raw = "octo/repo"
    digest = lr.repo_digest(raw)
    assert lr.canonicalize_repo(raw) == digest
    assert lr.canonicalize_repo(digest) == digest


def test_mixed_raw_and_digest_lanes_detect_overlap() -> None:
    # Dataset #1 stores raw repo names; Dataset #2 stores digests.
    dataset_a_raw = ["octo/shared", "octo/only_a"]
    dataset_b_digests = [lr.repo_digest("octo/shared"), lr.repo_digest("octo/only_b")]
    report = lr.check_overlap(dataset_a_raw, dataset_b_digests)
    assert report["overlap_count"] == 1
    assert report["overlapping_repo_digests"] == [lr.repo_digest("octo/shared")]
    assert report["disjoint"] is False
    assert report["joint_training_safe"] is False


def test_disjoint_sets_report_safe_but_note_other_blockers() -> None:
    report = lr.check_overlap(["a/x"], [lr.repo_digest("b/y")])
    assert report["disjoint"] is True
    assert report["joint_training_safe"] is True
    assert "NOT sufficient" in report["note"]


def test_check_overlap_is_order_independent() -> None:
    a = ["a/x", "b/y", "c/z"]
    b = [lr.repo_digest("b/y"), lr.repo_digest("d/w")]
    assert lr.check_overlap(a, b) == lr.check_overlap(
        list(reversed(a)), list(reversed(b))
    )


def test_collect_split_group_repos_from_examples() -> None:
    examples = [
        {"split_group": {"repo": "sha256:deadbeef"}},
        {"split_group": {"repo": "octo/raw"}},
        {"split_group": {"repo": None}},
        {"split_group": {}},
    ]
    digests = lr.collect_split_group_repos(examples)
    assert "sha256:deadbeef" in digests
    assert lr.repo_digest("octo/raw") in digests
    assert len(digests) == 2


def test_foundation_manifest_is_unpopulated_and_blocked() -> None:
    manifest = lr.build_registry_manifest(
        dataset_a_id="swe-gym-openhands-sampled",
        dataset_b_id="open-swe-traces",
    )
    assert manifest["status"] == "foundation_unpopulated"
    assert manifest["overlap"]["joint_training_safe"] is False
    assert manifest["joint_training_authorization"]["status"] == "not_authorized"


def test_populated_manifest_runs_the_check() -> None:
    manifest = lr.build_registry_manifest(
        dataset_a_id="swe-gym-openhands-sampled",
        dataset_b_id="open-swe-traces",
        dataset_a_repos=["octo/shared"],
        dataset_b_repos=[lr.repo_digest("octo/shared")],
        populated=True,
    )
    assert manifest["status"] == "populated"
    assert manifest["overlap"]["overlap_count"] == 1
