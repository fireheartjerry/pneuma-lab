"""Scientific decision firewall for autonomous experiment iteration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class DecisionError(ValueError):
    """An evaluator result cannot support a campaign decision."""


@dataclass(frozen=True, slots=True)
class Evaluation:
    validity: str
    informative: bool
    favorable: bool | None
    operational_failure: bool = False
    evidence_complete: bool = True
    correctable_findings: tuple[str, ...] = ()
    new_exploratory_hypothesis: bool = False

    def __post_init__(self) -> None:
        if self.validity not in {"valid", "invalid", "inconclusive"}:
            raise DecisionError("evaluation validity is invalid")
        if type(self.informative) is not bool or self.favorable not in {
            True,
            False,
            None,
        }:
            raise DecisionError("evaluation booleans are invalid")
        if (
            type(self.operational_failure) is not bool
            or type(self.evidence_complete) is not bool
        ):
            raise DecisionError("evaluation flags are invalid")
        if not all(type(item) is str and item for item in self.correctable_findings):
            raise DecisionError("correctable findings must be non-empty strings")

    def to_mapping(self) -> dict[str, object]:
        return {
            "validity": self.validity,
            "informative": self.informative,
            "favorable": self.favorable,
            "operational_failure": self.operational_failure,
            "evidence_complete": self.evidence_complete,
            "correctable_findings": list(self.correctable_findings),
            "new_exploratory_hypothesis": self.new_exploratory_hypothesis,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Evaluation:
        expected = {
            "validity",
            "informative",
            "favorable",
            "operational_failure",
            "evidence_complete",
            "correctable_findings",
            "new_exploratory_hypothesis",
        }
        if set(value) != expected or not isinstance(
            value["correctable_findings"], list
        ):
            raise DecisionError("evaluation fields differ")
        return cls(
            validity=value["validity"],
            informative=value["informative"],
            favorable=value["favorable"],
            operational_failure=value["operational_failure"],
            evidence_complete=value["evidence_complete"],
            correctable_findings=tuple(value["correctable_findings"]),
            new_exploratory_hypothesis=value["new_exploratory_hypothesis"],
        )


@dataclass(frozen=True, slots=True)
class CampaignDecision:
    code: str
    rationale: str
    successor_status: str | None = None


def decide_result(evaluation: Evaluation) -> CampaignDecision:
    """Decide on validity/information without rewarding favorability."""

    findings = evaluation.correctable_findings
    if evaluation.operational_failure:
        if findings:
            return CampaignDecision(
                "REDESIGN_OPERATIONAL",
                "The workload failed operationally and has a grounded repair target.",
                "operational_repair",
            )
        return CampaignDecision(
            "TERMINAL_SCIENTIFIC_NO_GO",
            "The workload failed without a grounded autonomous repair.",
        )
    if not evaluation.evidence_complete or evaluation.validity == "invalid":
        if findings:
            return CampaignDecision(
                "REDESIGN_SCIENTIFIC",
                "The result is invalid or incomplete and has a grounded correction.",
                "operational_repair",
            )
        return CampaignDecision(
            "TERMINAL_SCIENTIFIC_NO_GO",
            "The result is invalid or incomplete without a grounded correction.",
        )
    if evaluation.validity == "valid" and evaluation.informative:
        return CampaignDecision(
            "ACCEPT_VALID_RESULT",
            "The result is valid and informative; favorability is not a decision input.",
        )
    if findings:
        return CampaignDecision(
            "REDESIGN_SCIENTIFIC",
            "The valid run is insufficiently informative and has a grounded design correction.",
            "exploratory",
        )
    if evaluation.new_exploratory_hypothesis:
        return CampaignDecision(
            "REDESIGN_SCIENTIFIC",
            "The result supports only a new explicitly exploratory successor.",
            "exploratory",
        )
    return CampaignDecision(
        "TERMINAL_SCIENTIFIC_NO_GO",
        "The run is not sufficiently informative and no grounded successor exists.",
    )
