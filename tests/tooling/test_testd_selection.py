from __future__ import annotations

from pneuma_lab.testd.manifest import TestManifest
from pneuma_lab.testd.selection import select


MANIFEST = TestManifest(
    micro_nodes=(
        "tests/smoke/test_micro_gate.py::test_one",
        "tests/smoke/test_micro_gate.py::test_two",
    ),
    milestone_nodes=("tests/resampling_null/test_packets.py::test_packet",),
    forensic_nodes=("tests/resampling_null/test_forensic.py::test_forensic",),
)


def test_known_dependencies_select_exact_and_transitive_nodes() -> None:
    selection = select(
        MANIFEST,
        dependencies={
            "src/a.py": {"tests/smoke/test_micro_gate.py::test_one"},
            "src/parent.py": {"tests/smoke/test_micro_gate.py::test_two"},
        },
        transitive_edges={"src/child.py": {"src/parent.py"}},
        changed_paths=("src/a.py", "src/child.py"),
    )

    assert selection.node_ids == (
        "tests/smoke/test_micro_gate.py::test_one",
        "tests/smoke/test_micro_gate.py::test_two",
    )
    assert selection.widening_reason == "known_dependencies"


def test_unknown_structural_and_prior_failure_widen_to_micro_gate() -> None:
    for changed_paths, failures in (
        (("unknown.txt",), ()),
        (("pyproject.toml",), ()),
        ((), ("tests/smoke/test_micro_gate.py::test_one",)),
    ):
        selection = select(
            MANIFEST,
            dependencies={},
            transitive_edges={},
            changed_paths=changed_paths,
            prior_failures=failures,
        )
        assert selection.node_ids == MANIFEST.micro_nodes
        assert selection.widening_reason != "known_dependencies"


def test_clean_known_graph_can_return_noop_but_forensic_requires_opt_in() -> None:
    clean = select(MANIFEST, dependencies={}, transitive_edges={}, changed_paths=())
    forensic = select(
        MANIFEST,
        dependencies={},
        transitive_edges={},
        changed_paths=(),
        include_forensic=True,
    )

    assert clean.node_ids == ()
    assert clean.widening_reason == "known_no_change"
    assert forensic.node_ids == MANIFEST.forensic_nodes
