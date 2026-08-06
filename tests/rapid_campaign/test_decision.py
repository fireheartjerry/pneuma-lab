from __future__ import annotations

from pneuma_lab.rapid_campaign.decision import Evaluation, decide_result


def test_valid_unfavorable_result_is_accepted_not_rerun() -> None:
    decision = decide_result(Evaluation(validity="valid", informative=True, favorable=False))
    assert decision.code == "ACCEPT_VALID_RESULT"
    assert decision.successor_status is None


def test_invalid_favorable_result_is_not_accepted() -> None:
    decision = decide_result(
        Evaluation(
            validity="invalid",
            informative=True,
            favorable=True,
            correctable_findings=("leakage",),
        )
    )
    assert decision.code == "REDESIGN_SCIENTIFIC"
    assert decision.successor_status == "operational_repair"


def test_uninformative_valid_result_can_redesign_only_with_grounded_reason() -> None:
    no_reason = decide_result(Evaluation(validity="valid", informative=False, favorable=None))
    assert no_reason.code == "TERMINAL_SCIENTIFIC_NO_GO"
    grounded = decide_result(
        Evaluation(
            validity="valid",
            informative=False,
            favorable=None,
            correctable_findings=("resolution-floor",),
        )
    )
    assert grounded.code == "REDESIGN_SCIENTIFIC"
    assert grounded.successor_status == "exploratory"


def test_operational_failure_has_a_separate_repair_route() -> None:
    decision = decide_result(
        Evaluation(
            validity="invalid",
            informative=False,
            favorable=None,
            operational_failure=True,
            correctable_findings=("worker-oom",),
        )
    )
    assert decision.code == "REDESIGN_OPERATIONAL"
    assert decision.successor_status == "operational_repair"

