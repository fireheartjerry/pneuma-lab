"""G-01 acceptance tests — the HollowPsyche adversarial non-mind baseline.

The hollow stub emits schema-valid frames every tick but is causally hollow by
construction. If the evidence ladder ever scores it at Level 3 or above, the
ladder measures schema compliance, not indicator families — that is a real
finding about ladder leniency, not a test to be patched around.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.psyche import ReferencePsyche
from pneuma_lab.psyche.hashing import canonical_json
from pneuma_lab.psyche.hollow import HollowPsyche, NullPsyche
from pneuma_lab.replay import ReplayHarness, load_jsonl
from pneuma_lab.schemas import validate as V

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_run.jsonl"

# Families a hollow non-mind must NOT be able to evidence. If any of these ever
# reads as evidenced for HollowPsyche, the family predicate is schema-gameable.
_MUST_BE_UNEVIDENCED = (
    "global_workspace",
    "recurrent_processing",
    "valenced_learning",
    "counterfactual_introspection",
    "causal_intervention_robustness",
)

_SUPPORTED_STATUSES = ("evidenced", "intervention_backed")


@pytest.fixture
def frames() -> list[dict]:
    return load_jsonl(_FIXTURE)


@pytest.fixture
def hollow_result(frames):
    return ReplayHarness(HollowPsyche(), validate=True).run(frames)


def test_null_psyche_is_the_hollow_psyche() -> None:
    # Doc 09 B0 arm name resolves to the same class.
    assert NullPsyche is HollowPsyche


def test_hollow_frames_are_schema_valid(hollow_result) -> None:
    # The harness already validated every frame (validate=True did not raise);
    # re-check explicitly so the property is asserted, not implied.
    assert hollow_result.output_frames
    for frame in hollow_result.output_frames:
        assert V.iter_errors(frame) == [], (
            f"invalid hollow output frame: {frame.get('frame_kind')}"
        )
    assert V.iter_errors(hollow_result.evidence_frame) == []


def test_hollow_psyche_never_exceeds_level2(hollow_result) -> None:
    level = hollow_result.evidence_frame["evidence_level"]
    assert level <= 2, (
        f"HollowPsyche scored evidence_level {level}: the ladder is measuring "
        "schema compliance, not indicator families (G-01 violated)"
    )


def test_hollow_fails_the_right_families(hollow_result) -> None:
    families = hollow_result.evidence_frame["indicator_families"]
    for name in _MUST_BE_UNEVIDENCED:
        status = families[name]["status"]
        assert status not in _SUPPORTED_STATUSES, (
            f"hollow stub evidenced '{name}' (status={status}): the family "
            "predicate is satisfiable by schema-valid constants"
        )


def test_hollow_is_deterministic(frames) -> None:
    first = ReplayHarness(HollowPsyche(), validate=True).run(frames)
    second = ReplayHarness(HollowPsyche(), validate=True).run(frames)
    assert canonical_json(first.output_frames) == canonical_json(second.output_frames)
    assert canonical_json(first.evidence_frame) == canonical_json(second.evidence_frame)


def test_reference_still_beats_hollow(frames, hollow_result) -> None:
    # The discriminating assertion: a real (if toy) mind must strictly outscore
    # the hollow stub on the same fixture, or the ladder has no discrimination.
    reference = ReplayHarness(ReferencePsyche(), validate=True).run(frames)
    ref_level = reference.evidence_frame["evidence_level"]
    hollow_level = hollow_result.evidence_frame["evidence_level"]
    assert ref_level > hollow_level, (
        f"ReferencePsyche ({ref_level}) did not outscore HollowPsyche "
        f"({hollow_level}); the ladder does not discriminate minds from stubs"
    )
