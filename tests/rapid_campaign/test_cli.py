from __future__ import annotations

import hashlib
import json

from pneuma_lab.rapid_campaign.cli import main
from pneuma_lab.rapid_campaign.cli import _reconcile_spend_reservation
from pneuma_lab.rapid_campaign.records import ExperimentVersion
from pneuma_lab.rapid_campaign.spend import SpendLedger
from pneuma_lab.rapid_campaign.store import CampaignStateStore


def test_cli_initializes_dry_runs_and_completes_simulated_loop(
    tmp_path, capsys
) -> None:
    package = tmp_path / "package.tar.gz"
    package.write_bytes(b"package")
    package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
    images = tmp_path / "images.json"
    images.write_text(
        json.dumps(
            {
                "roles": [
                    {"role": "controller", "image_digest": "sha256:" + "a" * 64},
                    {"role": "model-server", "image_digest": "sha256:" + "b" * 64},
                    {"role": "benchmark-worker", "image_digest": "sha256:" + "c" * 64},
                ]
            }
        ),
        encoding="utf-8",
    )
    review = tmp_path / "review.json"
    review.write_text(
        json.dumps(
            {
                "record_kind": "cloud_official_study_final_launch_review",
                "verdict": "READY_TO_SUBMIT",
                "action_id": "official-p0-step4b-c120-20260806-r2",
                "experiment_submitted": False,
                "scientific_workload_started": False,
                "bindings": {
                    "runtime_source_commit": "1" * 40,
                    "launch_surface_commit": "2" * 40,
                    "c120_power_final_sha256": "3" * 64,
                    "prelaunch_root_sha256": "4" * 64,
                    "run_spec_sha256": "5" * 64,
                    "authorization_sha256": "6" * 64,
                    "launch_plan_sha256": "7" * 64,
                    "package_sha256": package_sha,
                },
                "registered_surface": {"max_usd": 5100.0},
                "images": {
                    "controller": "sha256:" + "a" * 64,
                    "model_server": "sha256:" + "b" * 64,
                    "benchmark_worker": "sha256:" + "c" * 64,
                },
            }
        ),
        encoding="utf-8",
    )
    root = tmp_path / "campaign"
    common = ["--root", str(root)]
    assert (
        main(
            [
                "init",
                *common,
                "--final-review",
                str(review),
                "--package",
                str(package),
                "--image-set",
                str(images),
                "--mode",
                "simulate",
            ]
        )
        == 0
    )
    assert main(["dry-run", *common]) == 0
    dry = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert dry["rerun_power"] is False
    assert dry["rebuild_images"] is False
    assert dry["mutation"] is False
    assert main(["run", *common]) == 0
    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result["phase"] == "teardown_complete"
    assert result["decision"] == "ACCEPT_VALID_RESULT"
    assert main(["status", *common]) == 0


def test_crash_reconciles_spend_from_durable_reserved_event(tmp_path) -> None:
    store = CampaignStateStore(
        tmp_path / "state.json", campaign_id="campaign", version_id="r2"
    )
    store.append("classified", {"impact": "ROOT", "rerun_power": False})
    store.append("prepared", {"version_sha256": "1" * 64})
    store.append(
        "reserved",
        {"reservation_id": "r2-run", "projected_microusd": 1_000_000},
    )
    version = ExperimentVersion(
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
    ledger = SpendLedger(ceiling_microusd=7_500_000_000)
    _reconcile_spend_reservation(
        ledger=ledger,
        store=store,
        version=version,
        projected_microusd=1_000_000,
    )
    assert ledger.outstanding_microusd == 1_000_000
