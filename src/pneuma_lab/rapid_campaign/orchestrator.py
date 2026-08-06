"""Restartable autonomous loop for one immutable experiment version."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .decision import CampaignDecision, Evaluation, decide_result
from .records import ExperimentVersion
from .spend import SpendLedger
from .store import CampaignSnapshot, CampaignStateStore, SubmissionIdentity


@dataclass(frozen=True, slots=True)
class Submission:
    parent_job_id: str
    child_job_ids: tuple[str, ...]
    receipt_sha256: str


@dataclass(frozen=True, slots=True)
class Observation:
    terminal: bool
    successful: bool
    evidence_sha256: str


@dataclass(frozen=True, slots=True)
class OutputArtifact:
    sha256: str
    locator: str


@dataclass(frozen=True, slots=True)
class AnalysisArtifact:
    sha256: str
    locator: str


class ExecutionAdapter(Protocol):
    def submit(self, *, client_token: str) -> Submission: ...
    def observe(self, submission: Submission) -> Observation: ...
    def seal_outputs(self, submission: Submission) -> OutputArtifact: ...
    def teardown(self, submission: Submission | None) -> int: ...


class AnalysisAdapter(Protocol):
    def analyse(self, output: OutputArtifact) -> AnalysisArtifact: ...


class ReviewAdapter(Protocol):
    def review(self, analysis: AnalysisArtifact) -> Evaluation: ...


@dataclass(frozen=True, slots=True)
class CampaignRunResult:
    phase: str
    decision_code: str | None
    state_sha256: str


class CampaignOrchestrator:
    def __init__(
        self,
        *,
        store: CampaignStateStore,
        ledger: SpendLedger,
        version: ExperimentVersion,
        projected_microusd: int,
        execution: ExecutionAdapter,
        analysis: AnalysisAdapter,
        review: ReviewAdapter,
    ) -> None:
        if store.version_id != version.version_id:
            raise ValueError("store/version identity differs")
        self.store = store
        self.ledger = ledger
        self.version = version
        self.projected_microusd = projected_microusd
        self.execution = execution
        self.analysis = analysis
        self.review = review
        self.reservation_id = f"{version.version_id}-run"
        self.client_token = f"pneuma-rapid-{version.run_spec_sha256[:48]}"

    def run(self, *, max_steps: int = 1000) -> CampaignRunResult:
        for _ in range(max_steps):
            snapshot = self.store.snapshot()
            if snapshot.phase == "teardown_complete":
                return self._result(snapshot)
            self._advance(snapshot)
        raise RuntimeError("campaign exceeded maximum local transition count")

    def _advance(self, snapshot: CampaignSnapshot) -> None:
        phase = snapshot.phase
        if phase == "draft":
            self.store.append("classified", {"impact": "ROOT", "rerun_power": False})
        elif phase == "classified":
            self.store.append("prepared", {"version_sha256": self.version.run_spec_sha256})
        elif phase == "prepared":
            self.ledger.reserve(
                self.reservation_id,
                version_id=self.version.version_id,
                amount_microusd=self.projected_microusd,
                version_ceiling_microusd=self.version.version_ceiling_microusd,
            )
            self.store.append(
                "reserved",
                {"reservation_id": self.reservation_id, "projected_microusd": self.projected_microusd},
            )
        elif phase == "reserved":
            self.store.append("submitting", {"client_token": self.client_token})
        elif phase == "submitting":
            submission = self.execution.submit(client_token=self.client_token)
            self.store.record_submission(
                parent_job_id=submission.parent_job_id,
                child_job_ids=submission.child_job_ids,
                receipt_sha256=submission.receipt_sha256,
            )
        elif phase in {"submitted", "observing", "observation_error"}:
            submission = self._submission(snapshot)
            try:
                observation = self.execution.observe(submission)
            except Exception:
                self.store.append("observation_error", {"submission": submission.parent_job_id})
                raise
            if not observation.terminal:
                self.store.append("observing", {"evidence_sha256": observation.evidence_sha256})
            elif observation.successful:
                self.store.append("workload_terminal", {"evidence_sha256": observation.evidence_sha256})
            else:
                self.store.append("workload_failed", {"evidence_sha256": observation.evidence_sha256})
        elif phase == "workload_terminal":
            output = self.execution.seal_outputs(self._submission(snapshot))
            observed = self.execution.teardown(self._submission(snapshot))
            self.ledger.observe(self.reservation_id, observed_microusd=observed)
            self.store.append(
                "outputs_sealed",
                {
                    "sha256": output.sha256,
                    "locator": output.locator,
                    "provider_teardown_complete": True,
                    "observed_microusd": observed,
                },
            )
        elif phase == "outputs_sealed":
            payload = snapshot.events[-1]["payload"]
            output = OutputArtifact(payload["sha256"], payload["locator"])
            analysis = self.analysis.analyse(output)
            self.store.append("analysed", {"sha256": analysis.sha256, "locator": analysis.locator})
        elif phase == "analysed":
            payload = snapshot.events[-1]["payload"]
            analysis = AnalysisArtifact(payload["sha256"], payload["locator"])
            evaluation = self.review.review(analysis)
            self.store.append("reviewed", {"evaluation": evaluation.to_mapping()})
        elif phase == "workload_failed":
            evaluation = Evaluation(
                validity="invalid",
                informative=False,
                favorable=None,
                operational_failure=True,
                correctable_findings=("workload-failure",),
            )
            self.store.append("reviewed", {"evaluation": evaluation.to_mapping()})
        elif phase == "reviewed":
            evaluation = Evaluation.from_mapping(snapshot.events[-1]["payload"]["evaluation"])
            decision = decide_result(evaluation)
            self._record_decision(decision)
        elif phase == "decided":
            self.store.append("teardown_started", {})
        elif phase in {"teardown_started", "teardown_failed"}:
            submission = self._submission(snapshot) if snapshot.submission is not None else None
            try:
                observed = self.execution.teardown(submission)
                self.ledger.observe(self.reservation_id, observed_microusd=observed)
                self.store.append("teardown_complete", {"observed_microusd": observed})
            except Exception:
                self.store.append("teardown_failed", {})
                raise
        else:
            raise RuntimeError(f"unsupported campaign phase {phase!r}")

    def _record_decision(self, decision: CampaignDecision) -> None:
        self.store.append(
            "decided",
            {
                "decision_code": decision.code,
                "rationale": decision.rationale,
                "successor_status": decision.successor_status,
            },
        )

    @staticmethod
    def _submission(snapshot: CampaignSnapshot) -> Submission:
        value: SubmissionIdentity | None = snapshot.submission
        if value is None:
            raise RuntimeError("campaign has no durable submission identity")
        return Submission(value.parent_job_id, value.child_job_ids, value.receipt_sha256)

    @staticmethod
    def _result(snapshot: CampaignSnapshot) -> CampaignRunResult:
        return CampaignRunResult(snapshot.phase, snapshot.decision_code, snapshot.state_sha256)
