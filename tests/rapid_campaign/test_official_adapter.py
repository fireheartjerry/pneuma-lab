from __future__ import annotations

import json
from pathlib import Path

from pneuma_lab.rapid_campaign.official_adapter import OfficialBatchAdapter
from pneuma_lab.rapid_campaign.orchestrator import Observation, OutputArtifact
from pneuma_lab.rapid_campaign.records import ExperimentVersion


class FakeTransport:
    def __init__(self) -> None:
        self.parent = None
        self.resources = False

    def discover_parent(self, action_id: str):
        return self.parent

    def action_resources_exist(self, action_id: str) -> bool:
        return self.resources

    def observe(self, action_id: str, parent_job_id: str) -> Observation:
        return Observation(True, True, "8" * 64)

    def collect_outputs(self, action_id: str, destination: Path) -> OutputArtifact:
        return OutputArtifact("9" * 64, str(destination / "index.json"))

    def observed_cost_microusd(self, parent_job_id: str, fallback_microusd: int) -> int:
        return 123


def version() -> ExperimentVersion:
    return ExperimentVersion(
        version_id="r2",
        parent_version_id=None,
        hypothesis_status="confirmatory",
        action_id="official-p0-step4b-c120-20260806-r2",
        run_spec_sha256="1" * 64,
        package_sha256="2" * 64,
        authorization_sha256="3" * 64,
        image_set_sha256="4" * 64,
        power_sha256="5" * 64,
        declared_criteria_sha256="6" * 64,
        version_ceiling_microusd=5_100_000_000,
        dependencies={"runtime_code": "7" * 64},
    )


def test_submit_is_exact_and_idempotent(tmp_path) -> None:
    commands = []

    def runner(argv):
        commands.append(argv)
        receipt = Path(argv[argv.index("--receipt") + 1])
        receipt.write_text(
            json.dumps(
                {
                    "action_id": version().action_id,
                    "package_sha256": version().package_sha256,
                    "run_spec_sha256": version().run_spec_sha256,
                    "array_job_id": "parent",
                    "array_size": 2,
                    "status": "SUBMITTED",
                }
            ),
            encoding="utf-8",
        )

    adapter = OfficialBatchAdapter(
        repo_root=tmp_path,
        campaign_root=tmp_path,
        version=version(),
        package_path=tmp_path / "package.tgz",
        image_set_path=tmp_path / "images.json",
        projected_microusd=1_000,
        transport=FakeTransport(),
        runner=runner,
    )
    first = adapter.submit(client_token="token")
    second = adapter.submit(client_token="token")
    assert first == second
    assert first.parent_job_id == "parent"
    assert len(commands) == 1
    assert str(adapter.package_path) in commands[0]


def test_lost_response_recovers_one_discovered_parent_without_resubmit(
    tmp_path,
) -> None:
    transport = FakeTransport()
    transport.parent = "recovered"
    commands = []
    adapter = OfficialBatchAdapter(
        repo_root=tmp_path,
        campaign_root=tmp_path,
        version=version(),
        package_path=tmp_path / "package.tgz",
        image_set_path=tmp_path / "images.json",
        projected_microusd=1_000,
        transport=transport,
        runner=commands.append,
    )
    submission = adapter.submit(client_token="token")
    assert submission.parent_job_id == "recovered"
    assert commands == []
    assert adapter.observe(submission).successful is True
    assert adapter.teardown(submission) == 123
