from __future__ import annotations

from pneuma_lab.brain import split


def test_split_is_deterministic_and_repo_grouped() -> None:
    a = split.split_of_repo("pandas-dev/pandas")
    b = split.split_of_repo("pandas-dev/pandas")
    assert a == b
    assert a in {"dev", "eval"}


def test_split_method_matches_estimator_convention() -> None:
    assert split.SPLIT_METHOD == "sha256_repo_mod10_lt3_eval_v1"


def test_assign_groups_examples_whole_repo_to_one_split() -> None:
    examples = [
        {"split_group": {"repo": "org/alpha"}},
        {"split_group": {"repo": "org/alpha"}},
        {"split_group": {"repo": "org/beta"}},
    ]
    assignment = split.assign(examples)
    assert assignment[0] == assignment[1]  # same repo -> same split
    assert set(assignment.values()) <= {"dev", "eval"}
