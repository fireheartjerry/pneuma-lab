"""Runner-issued provenance for counterbalanced paired replays.

Raw output dictionaries can be internally consistent yet caller-fabricated.  A
Level-4 artifact therefore needs more than recomputation: it needs a receipt from
the runner that produced every arm under counterbalanced factory order and bound
the exact input/output bytes into digests.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

_COUNTERBALANCED_ORDERS = (
    ("control", "treated", "null"),
    ("treated", "null", "control"),
    ("null", "control", "treated"),
)
_ISSUER = object()


def counterbalanced_orders() -> tuple[tuple[str, ...], ...]:
    """The three arm orders required for runner-issued provenance."""
    return _COUNTERBALANCED_ORDERS


def _sha256_json(value) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def input_frames_sha256(input_frames: list[dict]) -> str:
    return _sha256_json(input_frames)


def output_frames_sha256(tick_outputs: list) -> str:
    return _sha256_json(
        [frame for output in tick_outputs for frame in output.all_frames()]
    )


def subject_factory_identity(factory) -> str:
    module = getattr(factory, "__module__", None)
    qualname = getattr(factory, "__qualname__", None)
    if not module or not qualname:
        factory_type = type(factory)
        module = factory_type.__module__
        qualname = factory_type.__qualname__
    return f"{module}.{qualname}"


def unverified_provenance_record() -> dict:
    """Stable evidence-frame record for caller-supplied raw arm outputs."""
    return {
        "status": "unverified_raw_outputs",
        "runner": None,
        "subject_factory": None,
        "subject_factory_eligible": False,
        "input_frames_sha256": None,
        "arm_output_sha256": {
            "control": None,
            "treated": None,
            "null": None,
        },
        "arm_orders": [],
        "counterbalanced_passes": [],
        "ordinal_invariant": False,
    }


@dataclass(frozen=True)
class _PairedReplayProvenance:
    """Opaque capability and digest record issued only after runner replay."""

    input_digest: str
    arm_digests: tuple[tuple[str, str], ...]
    pass_digests: tuple[tuple[tuple[str, str], ...], ...]
    arm_orders: tuple[tuple[str, ...], ...]
    ordinal_invariant: bool
    subject_factory: str
    subject_factory_eligible: bool
    _issuer: object = field(repr=False, compare=False)

    @classmethod
    def issue(
        cls,
        input_frames: list[dict],
        replay_passes: list[dict[str, list]],
        factory,
        *,
        subject_factory_eligible: bool,
    ) -> "_PairedReplayProvenance":
        """Bind counterbalanced replay arms and record ordinal invariance."""
        if len(replay_passes) != len(_COUNTERBALANCED_ORDERS):
            raise ValueError("all counterbalanced replay orders are required")
        pass_digests = [
            {
                arm: output_frames_sha256(outputs)
                for arm, outputs in replay_pass.items()
            }
            for replay_pass in replay_passes
        ]
        expected_arms = set(_COUNTERBALANCED_ORDERS[0])
        if any(set(digests) != expected_arms for digests in pass_digests):
            raise ValueError("every replay pass must contain control, treated, and null")
        ordinal_invariant = all(
            len({digests[arm] for digests in pass_digests}) == 1
            for arm in expected_arms
        )
        first_digests = pass_digests[0]
        return cls(
            input_digest=input_frames_sha256(input_frames),
            arm_digests=tuple(
                (arm, first_digests[arm]) for arm in _COUNTERBALANCED_ORDERS[0]
            ),
            pass_digests=tuple(
                tuple((arm, digests[arm]) for arm in order)
                for order, digests in zip(_COUNTERBALANCED_ORDERS, pass_digests)
            ),
            arm_orders=_COUNTERBALANCED_ORDERS,
            ordinal_invariant=ordinal_invariant,
            subject_factory=subject_factory_identity(factory),
            subject_factory_eligible=subject_factory_eligible,
            _issuer=_ISSUER,
        )

    def integrity_errors(
        self,
        input_frames: list[dict],
        control_outputs: list,
        treated_outputs: list,
        null_outputs: list,
    ) -> list[str]:
        """Verify capability identity, digests, order coverage, and invariance."""
        errors: list[str] = []
        if self._issuer is not _ISSUER:
            errors.append("paired replay provenance was not issued by this runner")
        if self.arm_orders != _COUNTERBALANCED_ORDERS:
            errors.append("paired replay did not cover the required arm orders")
        if not self.subject_factory_eligible:
            errors.append(
                "subject factory is not certified for the v0.2 internal Level-4 path"
            )
        if self.input_digest != input_frames_sha256(input_frames):
            errors.append("paired replay input digest does not match the timeline")
        expected_digests = {
            "control": output_frames_sha256(control_outputs),
            "treated": output_frames_sha256(treated_outputs),
            "null": output_frames_sha256(null_outputs),
        }
        if dict(self.arm_digests) != expected_digests:
            errors.append("paired replay arm digests do not match supplied outputs")
        recorded_passes = [dict(pass_digest) for pass_digest in self.pass_digests]
        pass_shape_ok = (
            len(recorded_passes) == len(_COUNTERBALANCED_ORDERS)
            and all(set(digests) == set(expected_digests) for digests in recorded_passes)
        )
        derived_invariant = pass_shape_ok and all(
            len({digests[arm] for digests in recorded_passes}) == 1
            for arm in expected_digests
        )
        if self.ordinal_invariant != derived_invariant:
            errors.append("paired replay ordinal-invariance flag disagrees with pass digests")
        if not derived_invariant:
            errors.append("paired arm outputs changed with factory execution order")
        return errors

    def as_record(self) -> dict:
        return {
            "status": self._status(),
            "runner": "pneuma_lab.interventions.PairedReplayRunner/v1",
            "subject_factory": self.subject_factory,
            "subject_factory_eligible": self.subject_factory_eligible,
            "input_frames_sha256": self.input_digest,
            "arm_output_sha256": dict(self.arm_digests),
            "arm_orders": [list(order) for order in self.arm_orders],
            "counterbalanced_passes": [
                {
                    "order": list(order),
                    "arm_output_sha256": dict(pass_digest),
                }
                for order, pass_digest in zip(self.arm_orders, self.pass_digests)
            ],
            "ordinal_invariant": self.ordinal_invariant,
        }

    def _status(self) -> str:
        if not self.ordinal_invariant:
            return "order_confounded"
        if not self.subject_factory_eligible:
            return "uncertified_subject"
        return "runner_verified"


__all__ = ["counterbalanced_orders"]
