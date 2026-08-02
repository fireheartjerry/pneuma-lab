from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.research.prepare_step7b_builder_successor import canonical_bytes, prepare


ROOT = Path(__file__).resolve().parents[2]
PREDECESSOR = ROOT / "docs/research/neurips-2026-workshop/evidence/step7b-aws-builder-successor-007-plan-20260801.json"


def test_successor_rebinds_action_archive_source_and_live_surface(tmp_path: Path) -> None:
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"fresh archive")
    plan = prepare(
        json.loads(PREDECESSOR.read_text(encoding="utf-8")),
        root=ROOT,
        archive=archive,
        action_id="step7b-aws-builder-008",
        frozen_timestamp="2026-08-02T01:00:00Z",
        expires_timestamp="2026-08-03T01:00:00Z",
        source_commit="a" * 40,
    )

    assert plan["action_id"] == "step7b-aws-builder-008"
    assert plan["source_commit"] == "a" * 40
    assert plan["archive"]["sha256"] == hashlib.sha256(b"fresh archive").hexdigest()
    assert plan["archive"]["size_bytes"] == len(b"fresh archive")
    assert "step7b-aws-builder-008" in plan["archive"]["s3_uri"]
    assert "step7b-aws-builder-008" in plan["bootstrap"]["output_s3_uri"]
    assert "step7b-aws-builder-008" in plan["bootstrap"]["plan_s3_uri"]
    for role in ("controller", "model-server", "benchmark-worker"):
        dockerfile = ROOT / plan["roles"][role]["dockerfile"]["path"]
        assert plan["roles"][role]["dockerfile"]["sha256"] == hashlib.sha256(dockerfile.read_bytes()).hexdigest()
    body = dict(plan)
    digest = body.pop("plan_sha256")
    assert digest == hashlib.sha256(canonical_bytes(body)).hexdigest()


def test_successor_can_bind_the_production_surface_harness(tmp_path: Path) -> None:
    archive = tmp_path / "source.tar"
    archive.write_bytes(b"fresh archive")
    plan = prepare(
        json.loads(PREDECESSOR.read_text(encoding="utf-8")),
        root=ROOT,
        archive=archive,
        action_id="step7b-aws-builder-010",
        frozen_timestamp="2026-08-02T02:00:00Z",
        expires_timestamp="2026-08-03T02:00:00Z",
        source_commit="b" * 40,
        production_surface=True,
    )
    surface = plan["production_surface"]
    assert surface["controller_privileged"] is True
    assert surface["request"]["max_tokens"] == 4
    harness = {
        "record_kind": surface["record_kind"],
        "schema_version": surface["schema_version"],
        "action_id": plan["action_id"],
        "input_lock_sha256": plan["input_lock_sha256"],
        "request": surface["request"],
    }
    assert surface["harness_sha256"] == hashlib.sha256(canonical_bytes(harness) + b"\n").hexdigest()
