from __future__ import annotations

from dataclasses import replace

import pytest

from pneuma_lab.rapid_campaign.records import (
    CampaignManifest,
    ExperimentVersion,
    RecordError,
    digest_record,
)


SHA = "a" * 64


def test_manifest_and_version_round_trip_with_verified_digest() -> None:
    manifest = CampaignManifest(
        campaign_id="placebo-official-20260806",
        aws_account_id="892077329800",
        region="us-east-1",
        ceiling_microusd=7_500_000_000,
        root_version_id="r2",
        allowed_resource_classes=("batch", "ec2", "ecr", "iam", "s3", "network"),
        tag_namespace="pneuma-rapid-campaign",
    )
    decoded = CampaignManifest.from_mapping(manifest.to_mapping())
    assert decoded == manifest
    assert digest_record(decoded) == digest_record(manifest)

    version = ExperimentVersion(
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
        dependencies={"eligible_roster": "1" * 64, "runtime_code": "2" * 64},
    )
    assert ExperimentVersion.from_mapping(version.to_mapping()) == version


def test_version_rejects_invalid_parent_and_open_or_bad_digest_data() -> None:
    version = ExperimentVersion(
        version_id="r3",
        parent_version_id="r2",
        hypothesis_status="exploratory",
        action_id="official-p0-step4b-c120-20260806-r3",
        run_spec_sha256=SHA,
        package_sha256="b" * 64,
        authorization_sha256="c" * 64,
        image_set_sha256="d" * 64,
        power_sha256="e" * 64,
        declared_criteria_sha256="f" * 64,
        version_ceiling_microusd=500_000_000,
        dependencies={"model": "1" * 64},
    )
    payload = version.to_mapping()
    payload["unexpected"] = True
    with pytest.raises(RecordError, match="unexpected"):
        ExperimentVersion.from_mapping(payload)
    with pytest.raises(RecordError, match="sha256"):
        ExperimentVersion.from_mapping(
            {**version.to_mapping(), "run_spec_sha256": "bad"}
        )
    with pytest.raises(RecordError, match="itself"):
        replace(version, parent_version_id="r3")
