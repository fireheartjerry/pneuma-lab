"""A stable-identity certified factory for BaselinePsycheSubject-v0.

A real class (not a lambda) so its factory identity is meaningful and stable, and
so the certification registry keys on a durable object. Passing the certification
probe makes it ``subject_factory_eligible`` on the promotable runner path.
"""

from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.interventions import certified_subjects as cs
from pneuma_lab.nervous_system.subject import BaselinePsycheSubject

_FIXTURES = (
    Path(__file__).resolve().parents[3] / "fixtures" / "nervous_system" / "subject"
)
PROBE_FIXTURE = "ablate_scar.jsonl"


class CertifiedBaselineSubjectFactory:
    """Callable factory: each call returns a fresh, identically-seeded subject."""

    def __init__(self, *, seed_scars=None):
        self._seed = dict(seed_scars or {})

    def __call__(self) -> BaselinePsycheSubject:
        return BaselinePsycheSubject(scars=dict(self._seed))


def _probe_frames() -> list:
    return [
        json.loads(x)
        for x in (_FIXTURES / PROBE_FIXTURE).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def certify_baseline_subject(*, seed_scars=None):
    """Build + certify a CertifiedBaselineSubjectFactory. Returns (factory, result)."""
    factory = CertifiedBaselineSubjectFactory(seed_scars=seed_scars)
    result = cs.certify(factory, _probe_frames())
    return factory, result


__all__ = [
    "CertifiedBaselineSubjectFactory",
    "certify_baseline_subject",
    "PROBE_FIXTURE",
]
