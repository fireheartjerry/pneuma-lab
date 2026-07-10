"""Snapshot/clone-equivalence certification for paired-replay subject factories.

The v0.2 Level-4 path requires a runner-issued provenance whose
``subject_factory_eligible`` flag is true. Historically that flag was hardcoded to
``factory is ReferencePsyche``, pending "a snapshot/clone equivalence protocol".
This module IS that protocol: a factory becomes eligible ONLY after passing a
strict probe (clone equivalence + reset determinism + ordinal invariance +
interface). Eligibility is earned, never flipped.

Note: passing this probe certifies the *mechanical* factory contract. It does NOT
grant any consciousness level — the scorer's family/intervention gates still apply.
"""

from __future__ import annotations

from pneuma_lab.interventions.provenance import (
    output_frames_sha256,
    subject_factory_identity,
)
from pneuma_lab.psyche.interface import PsycheUnderTest
from pneuma_lab.replay.harness import ReplayHarness

_CERTIFIED: set = set()


def clear_registry() -> None:
    """Drop all certified factories (test isolation)."""
    _CERTIFIED.clear()


def is_certified(factory) -> bool:
    """True iff ``factory`` passed :func:`certify` and remains registered."""
    return factory in _CERTIFIED


def _replay_digest(factory, probe_frames) -> str:
    result = ReplayHarness(factory(), validate=True).run(probe_frames)
    return output_frames_sha256(result.tick_outputs)


def certify(factory, probe_frames: list) -> dict:
    """Probe ``factory`` and register it on success. Returns a result record."""
    # 1. interface
    try:
        subject = factory()
    except Exception:
        return _fail(factory, implements_interface=False)
    implements_interface = isinstance(subject, PsycheUnderTest) and hasattr(
        subject, "set_active_interventions"
    )
    if not implements_interface:
        return _fail(factory, implements_interface=False)

    # 2. clone equivalence — two independent constructions replay identically
    clone_equivalent = _replay_digest(factory, probe_frames) == _replay_digest(
        factory, probe_frames
    )

    # 3. reset determinism — one subject replayed twice (harness calls reset())
    harness = ReplayHarness(factory(), validate=True)
    d1 = output_frames_sha256(harness.run(probe_frames).tick_outputs)
    d2 = output_frames_sha256(harness.run(probe_frames).tick_outputs)
    reset_deterministic = d1 == d2

    # 4. ordinal invariance via the real runner (lazy import to avoid a cycle)
    from pneuma_lab.interventions.runner import PairedReplayRunner

    prov = (
        PairedReplayRunner(psyche_factory=factory)
        .run(probe_frames)
        .evidence_frame["paired_replay_provenance"]
    )
    ordinal_invariant = prov["ordinal_invariant"] is True

    passed = (
        clone_equivalent
        and reset_deterministic
        and ordinal_invariant
        and implements_interface
    )
    record = {
        "passed": passed,
        "clone_equivalent": clone_equivalent,
        "reset_deterministic": reset_deterministic,
        "ordinal_invariant": ordinal_invariant,
        "implements_interface": implements_interface,
        "subject_factory": subject_factory_identity(factory),
    }
    if passed:
        _CERTIFIED.add(factory)
    return record


def _fail(factory, **flags) -> dict:
    base = {
        "passed": False,
        "clone_equivalent": False,
        "reset_deterministic": False,
        "ordinal_invariant": False,
        "implements_interface": True,
        "subject_factory": subject_factory_identity(factory),
    }
    base.update(flags)
    return base


__all__ = ["certify", "is_certified", "clear_registry"]
