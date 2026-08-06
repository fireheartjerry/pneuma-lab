from __future__ import annotations

import hashlib
import json

from pneuma_lab.rapid_campaign.cli import main


def test_cli_initializes_dry_runs_and_completes_simulated_loop(tmp_path, capsys) -> None:
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
                    "model-server": "sha256:" + "b" * 64,
                    "benchmark-worker": "sha256:" + "c" * 64,
                },
            }
        ),
        encoding="utf-8",
    )
    root = tmp_path / "campaign"
    common = ["--root", str(root)]
    assert main(["init", *common, "--final-review", str(review), "--package", str(package), "--image-set", str(images), "--mode", "simulate"]) == 0
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
