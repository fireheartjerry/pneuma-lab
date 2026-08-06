"""Exact, recoverable adapter around the unchanged official Batch scripts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Protocol

from .orchestrator import Observation, OutputArtifact, Submission
from .records import ExperimentVersion, canonical_bytes


BUCKET = "pneuma-phase-b-892077329800"
REGION = "us-east-1"
JOB_STATES = ("SUBMITTED", "PENDING", "RUNNABLE", "STARTING", "RUNNING", "SUCCEEDED", "FAILED")


class OfficialTransport(Protocol):
    def discover_parent(self, action_id: str) -> str | None: ...
    def action_resources_exist(self, action_id: str) -> bool: ...
    def observe(self, action_id: str, parent_job_id: str) -> Observation: ...
    def collect_outputs(self, action_id: str, destination: Path) -> OutputArtifact: ...
    def observed_cost_microusd(self, parent_job_id: str, fallback_microusd: int) -> int: ...


def _default_runner(argv: list[str]) -> None:
    subprocess.run(argv, check=True)


@dataclass
class OfficialBatchAdapter:
    repo_root: Path
    campaign_root: Path
    version: ExperimentVersion
    package_path: Path
    image_set_path: Path
    projected_microusd: int
    transport: OfficialTransport
    runner: Callable[[list[str]], None] = _default_runner

    @property
    def version_root(self) -> Path:
        return self.campaign_root / "versions" / self.version.version_id

    @property
    def submission_receipt(self) -> Path:
        return self.version_root / "provider" / "submission.json"

    def submit(self, *, client_token: str) -> Submission:
        del client_token  # the immutable action/run-spec pair is the provider token.
        if self.submission_receipt.exists():
            return self._submission_from_receipt()
        parent = self.transport.discover_parent(self.version.action_id)
        if parent is not None:
            self._write_recovery_receipt(parent)
            return self._submission_from_receipt()
        if self.transport.action_resources_exist(self.version.action_id):
            self._cleanup("partial-pre-submit-cleanup.json")
        self.submission_receipt.parent.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(self.repo_root / "scripts" / "research" / "submit_official_batch.py"),
            "--action-id",
            self.version.action_id,
            "--package",
            str(self.package_path),
            "--package-sha256",
            self.version.package_sha256,
            "--run-spec-sha256",
            self.version.run_spec_sha256,
            "--image-set",
            str(self.image_set_path),
            "--receipt",
            str(self.submission_receipt),
        ]
        try:
            self.runner(command)
        except Exception:
            parent = self.transport.discover_parent(self.version.action_id)
            if parent is None:
                raise
            self._write_recovery_receipt(parent)
        return self._submission_from_receipt()

    def observe(self, submission: Submission) -> Observation:
        return self.transport.observe(self.version.action_id, submission.parent_job_id)

    def seal_outputs(self, submission: Submission) -> OutputArtifact:
        del submission
        return self.transport.collect_outputs(self.version.action_id, self.version_root / "outputs")

    def teardown(self, submission: Submission | None) -> int:
        self._cleanup("teardown.json")
        if submission is None:
            return 0
        return self.transport.observed_cost_microusd(submission.parent_job_id, self.projected_microusd)

    def _cleanup(self, receipt_name: str) -> None:
        receipt = self.version_root / "provider" / receipt_name
        receipt.parent.mkdir(parents=True, exist_ok=True)
        self.runner(
            [
                sys.executable,
                str(self.repo_root / "scripts" / "research" / "cleanup_official_batch.py"),
                "--action-id",
                self.version.action_id,
                "--receipt",
                str(receipt),
            ]
        )

    def _write_recovery_receipt(self, parent: str) -> None:
        payload = {
            "record_kind": "rapid_campaign_recovered_official_submission",
            "schema_version": "0.1.0",
            "action_id": self.version.action_id,
            "package_sha256": self.version.package_sha256,
            "run_spec_sha256": self.version.run_spec_sha256,
            "array_job_id": parent,
            "array_size": 2,
            "status": "RECOVERED",
        }
        self.submission_receipt.parent.mkdir(parents=True, exist_ok=True)
        self.submission_receipt.write_bytes(canonical_bytes(payload))

    def _submission_from_receipt(self) -> Submission:
        payload = json.loads(self.submission_receipt.read_text(encoding="utf-8"))
        expected = {
            "action_id": self.version.action_id,
            "package_sha256": self.version.package_sha256,
            "run_spec_sha256": self.version.run_spec_sha256,
            "array_size": 2,
        }
        for key, value in expected.items():
            if payload.get(key) != value:
                raise RuntimeError(f"official submission receipt {key} differs")
        parent = payload.get("array_job_id")
        if type(parent) is not str or not parent:
            raise RuntimeError("official submission receipt lacks array job identity")
        receipt_sha = hashlib.sha256(canonical_bytes(payload)).hexdigest()
        return Submission(parent, (f"{parent}:0", f"{parent}:1"), receipt_sha)


class Boto3OfficialTransport:
    """Read/collect transport; all infrastructure mutation stays in reviewed scripts."""

    def __init__(self, *, poll_seconds: float = 30.0, max_hourly_usd: float = 2.2421) -> None:
        import boto3

        self.batch = boto3.client("batch", region_name=REGION)
        self.s3 = boto3.client("s3", region_name=REGION)
        self.poll_seconds = poll_seconds
        self.max_hourly_usd = max_hourly_usd

    def discover_parent(self, action_id: str) -> str | None:
        queue = f"{action_id}-queue"
        if not self.batch.describe_job_queues(jobQueues=[queue]).get("jobQueues", []):
            return None
        found: set[str] = set()
        for status in JOB_STATES:
            token = None
            while True:
                kwargs: dict[str, Any] = {"jobQueue": queue, "jobStatus": status, "maxResults": 100}
                if token:
                    kwargs["nextToken"] = token
                response = self.batch.list_jobs(**kwargs)
                for row in response.get("jobSummaryList", []):
                    if row.get("jobName") == action_id and "index" not in row.get("arrayProperties", {}):
                        found.add(str(row["jobId"]))
                token = response.get("nextToken")
                if not token:
                    break
        if len(found) > 1:
            raise RuntimeError("multiple official parent submissions exist")
        return next(iter(found), None)

    def action_resources_exist(self, action_id: str) -> bool:
        return bool(
            self.batch.describe_job_queues(jobQueues=[f"{action_id}-queue"]).get("jobQueues", [])
            or self.batch.describe_compute_environments(computeEnvironments=[f"{action_id}-ce"]).get("computeEnvironments", [])
            or self.batch.describe_job_definitions(jobDefinitionName=f"{action_id}-job", status="ACTIVE").get("jobDefinitions", [])
        )

    def observe(self, action_id: str, parent_job_id: str) -> Observation:
        last_status = None
        while True:
            rows = self.batch.describe_jobs(jobs=[parent_job_id]).get("jobs", [])
            if len(rows) != 1 or rows[0].get("jobName") != action_id:
                raise RuntimeError("official parent job identity differs")
            status = str(rows[0].get("status"))
            if status != last_status:
                print(json.dumps({"event": "AWS_BATCH_STATUS", "action_id": action_id, "status": status}), flush=True)
                last_status = status
            evidence = hashlib.sha256(canonical_bytes(rows[0])).hexdigest()
            if status in {"SUCCEEDED", "FAILED"}:
                return Observation(True, status == "SUCCEEDED", evidence)
            time.sleep(self.poll_seconds)

    def collect_outputs(self, action_id: str, destination: Path) -> OutputArtifact:
        prefix = f"runs/official/{action_id}/outputs/"
        objects: list[dict[str, object]] = []
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            for row in page.get("Contents", []):
                key = str(row["Key"])
                relative = key.removeprefix(prefix)
                if not relative or relative.startswith("/") or ".." in Path(relative).parts:
                    raise RuntimeError("unsafe official output key")
                target = destination / "raw" / Path(relative)
                target.parent.mkdir(parents=True, exist_ok=True)
                self.s3.download_file(BUCKET, key, str(target))
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                objects.append({"key": key, "relative_path": str(Path("raw") / relative), "byte_count": target.stat().st_size, "sha256": digest})
        if not objects:
            raise RuntimeError("official output prefix is empty")
        index = {
            "record_kind": "rapid_campaign_sealed_output_index",
            "schema_version": "0.1.0",
            "action_id": action_id,
            "objects": sorted(objects, key=lambda item: str(item["key"])),
        }
        payload = canonical_bytes(index)
        destination.mkdir(parents=True, exist_ok=True)
        index_path = destination / "index.json"
        index_path.write_bytes(payload)
        return OutputArtifact(hashlib.sha256(payload).hexdigest(), str(index_path))

    def observed_cost_microusd(self, parent_job_id: str, fallback_microusd: int) -> int:
        durations_ms = 0
        found = 0
        for status in JOB_STATES:
            token = None
            while True:
                kwargs: dict[str, Any] = {"arrayJobId": parent_job_id, "jobStatus": status, "maxResults": 100}
                if token:
                    kwargs["nextToken"] = token
                response = self.batch.list_jobs(**kwargs)
                ids = [str(row["jobId"]) for row in response.get("jobSummaryList", [])]
                for start in range(0, len(ids), 100):
                    for job in self.batch.describe_jobs(jobs=ids[start : start + 100]).get("jobs", []):
                        started = int(job.get("startedAt", 0))
                        stopped = int(job.get("stoppedAt", 0))
                        if started > 0 and stopped >= started:
                            durations_ms += stopped - started
                            found += 1
                token = response.get("nextToken")
                if not token:
                    break
        if found < 2:
            return fallback_microusd
        return min(fallback_microusd, math.ceil((durations_ms / 3_600_000) * self.max_hourly_usd * 1_000_000))
