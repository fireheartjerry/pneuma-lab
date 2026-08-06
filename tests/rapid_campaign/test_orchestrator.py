from __future__ import annotations

from dataclasses import dataclass

import pytest

from pneuma_lab.rapid_campaign.decision import Evaluation
from pneuma_lab.rapid_campaign.orchestrator import (
    AnalysisArtifact,
    CampaignOrchestrator,
    Observation,
    OutputArtifact,
    Submission,
)
from pneuma_lab.rapid_campaign.records import ExperimentVersion
from pneuma_lab.rapid_campaign.spend import SpendLedger
from pneuma_lab.rapid_campaign.store import CampaignStateStore


SHA = "a" * 64


def version() -> ExperimentVersion:
    return ExperimentVersion(
        version_id="r2",
        parent_version_id=None,
        hypothesis_status="confirmatory",
        action_id="official-p0-step4b-c120-20260806-r2",
        run_spec_sha256=SHA,
        package_sha256="b" * 64,
        authorization_sha256="c" * 64,
        image_set_sha256="d" * 64,
        power_sha256="e" * 64,
        declared_criteria_sha256="f" * 64,
        version_ceiling_microusd=5_100_000_000,
        dependencies={"eligible_roster": "1" * 64},
    )


@dataclass
class FakeExecution:
    submit_calls: int = 0
    observe_calls: int = 0
    fail_observation_once: bool = False

    def submit(self, *, client_token: str) -> Submission:
        self.submit_calls += 1
        return Submission("parent", ("a", "b"), "2" * 64)

    def observe(self, submission: Submission) -> Observation:
        self.observe_calls += 1
        if self.fail_observation_once and self.observe_calls == 1:
            raise RuntimeError("transient")
        return Observation(terminal=True, successful=True, evidence_sha256="3" * 64)

    def seal_outputs(self, submission: Submission) -> OutputArtifact:
        return OutputArtifact("4" * 64, "outputs/index.json")

    def teardown(self, submission: Submission | None) -> int:
        return 100


class FakeAnalysis:
    def analyse(self, output: OutputArtifact) -> AnalysisArtifact:
        return AnalysisArtifact("5" * 64, "analysis/result.json")


class FakeReview:
    def review(self, analysis: AnalysisArtifact) -> Evaluation:
        return Evaluation(validity="valid", informative=True, favorable=False)


def make(tmp_path, execution: FakeExecution) -> CampaignOrchestrator:
    return CampaignOrchestrator(
        store=CampaignStateStore(tmp_path / "state.json", campaign_id="campaign", version_id="r2"),
        ledger=SpendLedger(ceiling_microusd=7_500_000_000),
        version=version(),
        projected_microusd=5_100_000_000,
        execution=execution,
        analysis=FakeAnalysis(),
        review=FakeReview(),
    )


def test_full_version_reaches_teardown_and_accepts_negative_result(tmp_path) -> None:
    execution = FakeExecution()
    orchestrator = make(tmp_path, execution)
    result = orchestrator.run()
    assert result.phase == "teardown_complete"
    assert result.decision_code == "ACCEPT_VALID_RESULT"
    assert execution.submit_calls == 1
    assert orchestrator.ledger.observed_microusd == 100


def test_observation_error_resumes_without_second_submission(tmp_path) -> None:
    execution = FakeExecution(fail_observation_once=True)
    orchestrator = make(tmp_path, execution)
    with pytest.raises(RuntimeError, match="transient"):
        orchestrator.run()
    assert orchestrator.store.snapshot().phase == "observation_error"
    result = orchestrator.run()
    assert result.phase == "teardown_complete"
    assert execution.submit_calls == 1
    assert execution.observe_calls == 2
