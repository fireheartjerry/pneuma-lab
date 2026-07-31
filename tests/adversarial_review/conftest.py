"""Shared fixture loading for the adversarial-review tests.

The synthetic campaign is copied into a temporary directory for every test so
that a test which mutates an input to prove a fail-closed path cannot corrupt
the committed fixture.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Sequence

from pneuma_lab.adversarial_review.inputs import (
    CampaignInputs,
    EnvironmentPin,
    InputObject,
)
from pneuma_lab.adversarial_review.matrix import Claim, load_claims
from pneuma_lab.adversarial_review.subprocess_adapter import ReplaySource

FIXTURE_ROLE_IDS = (
    "R02-identification",
    "R03-statistics",
    "R09-manuscript",
    "R10-compliance",
)

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "adversarial_review"
    / "synthetic_campaign"
)


def load_fixture_campaign(
    tmp_path: Path,
) -> tuple[CampaignInputs, Sequence[Claim], ReplaySource]:
    """Copy the synthetic fixture into ``tmp_path`` and return its campaign parts."""

    shutil.copytree(FIXTURE / "root", tmp_path / "root")
    shutil.copytree(FIXTURE / "transcripts", tmp_path / "transcripts")
    spec = json.loads((FIXTURE / "campaign-spec.json").read_text(encoding="utf-8"))

    environment = spec["environment"]
    inputs = CampaignInputs(
        campaign_id=str(spec["campaign_id"]),
        stage=str(spec["stage"]),
        root=(tmp_path / "root").resolve(),
        environment=EnvironmentPin(
            repo_commit=str(environment["repo_commit"]),
            repo_dirty=bool(environment["repo_dirty"]),
            python_version=str(environment["python_version"]),
            platform=str(environment["platform"]),
            dependency_digest=str(environment["dependency_digest"]),
        ),
        objects=tuple(
            InputObject(
                slot=str(item["slot"]),
                path=str(item["path"]),
                declared_digest=str(item["declared_digest"]),
                description=str(item.get("description", "")),
                optional=bool(item.get("optional", False)),
            )
            for item in spec["objects"]
        ),
        receipt_index=dict(spec.get("receipt_index", {})),
        external_sources=tuple(spec.get("external_sources", ())),
    )
    claims = load_claims(spec.get("claims", ()))
    source = ReplaySource(transcript_dir=(tmp_path / "transcripts").resolve())
    return inputs, claims, source
