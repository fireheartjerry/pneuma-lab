"""Local and command adapters for the rapid campaign controller."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Sequence

from .decision import Evaluation
from .orchestrator import AnalysisArtifact, Observation, OutputArtifact, Submission
from .records import canonical_bytes


@dataclass
class SimulationExecution:
    root: Path
    submit_calls: int = 0

    def submit(self, *, client_token: str) -> Submission:
        self.submit_calls += 1
        receipt = {"client_token": client_token, "parent": "sim-parent", "children": ["sim-0", "sim-1"]}
        return Submission("sim-parent", ("sim-0", "sim-1"), hashlib.sha256(canonical_bytes(receipt)).hexdigest())

    def observe(self, submission: Submission) -> Observation:
        return Observation(True, True, hashlib.sha256(submission.parent_job_id.encode()).hexdigest())

    def seal_outputs(self, submission: Submission) -> OutputArtifact:
        destination = self.root / "versions" / "r2" / "outputs" / "index.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_bytes({"simulation": True, "submission": submission.parent_job_id})
        destination.write_bytes(payload)
        return OutputArtifact(hashlib.sha256(payload).hexdigest(), str(destination))

    def teardown(self, submission: Submission | None) -> int:
        return 0


@dataclass
class SimulationAnalysis:
    root: Path

    def analyse(self, output: OutputArtifact) -> AnalysisArtifact:
        destination = self.root / "versions" / "r2" / "analysis" / "result.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = canonical_bytes({"simulation": True, "output_sha256": output.sha256})
        destination.write_bytes(payload)
        return AnalysisArtifact(hashlib.sha256(payload).hexdigest(), str(destination))


@dataclass
class SimulationReview:
    favorable: bool = False

    def review(self, analysis: AnalysisArtifact) -> Evaluation:
        return Evaluation(validity="valid", informative=True, favorable=self.favorable)


@dataclass
class CommandAnalysis:
    argv: Sequence[str]
    output_path: Path

    def analyse(self, output: OutputArtifact) -> AnalysisArtifact:
        environment = {**os.environ, "PNEUMA_SEALED_OUTPUT_INDEX": output.locator}
        subprocess.run(self.argv, check=True, env=environment)
        payload = self.output_path.read_bytes()
        return AnalysisArtifact(hashlib.sha256(payload).hexdigest(), str(self.output_path))


@dataclass
class JsonReview:
    path: Path

    def review(self, analysis: AnalysisArtifact) -> Evaluation:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("analysis_sha256") != analysis.sha256:
            raise ValueError("review does not bind the analysis")
        return Evaluation.from_mapping(value["evaluation"])
