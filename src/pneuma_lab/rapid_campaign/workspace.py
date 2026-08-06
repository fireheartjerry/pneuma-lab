"""Private on-disk workspace and exact r2 bootstrap for God Mode."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .records import CampaignManifest, ExperimentVersion, canonical_bytes, digest_record
from .spend import SpendLedger
from .store import CampaignStateStore


class WorkspaceError(ValueError):
    """A campaign workspace binding is missing or differs."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_once(path: Path, value: object) -> None:
    payload = canonical_bytes(value)
    if path.exists():
        if path.read_bytes() != payload:
            raise WorkspaceError(f"refusing to replace different campaign file {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(payload)
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    os.replace(temporary, path)


def initialize_r2(
    root: Path,
    *,
    final_review_path: Path,
    package_path: Path,
    image_set_path: Path,
    power_root: Path | None,
    mode: str,
    projected_microusd: int,
) -> tuple[CampaignManifest, ExperimentVersion]:
    if mode not in {"simulate", "official"}:
        raise WorkspaceError("campaign mode must be simulate or official")
    review = json.loads(final_review_path.read_text(encoding="utf-8"))
    if review.get("record_kind") != "cloud_official_study_final_launch_review":
        raise WorkspaceError("final review kind differs")
    if review.get("verdict") != "READY_TO_SUBMIT":
        raise WorkspaceError("final review is not READY_TO_SUBMIT")
    if review.get("experiment_submitted") is not False or review.get("scientific_workload_started") is not False:
        raise WorkspaceError("r2 final review is not at the unlaunched boundary")
    bindings = review.get("bindings")
    surface = review.get("registered_surface")
    if not isinstance(bindings, dict) or not isinstance(surface, dict):
        raise WorkspaceError("final review bindings/surface are invalid")
    package_sha = _sha256(package_path)
    if package_sha != bindings.get("package_sha256"):
        raise WorkspaceError("package bytes differ from final review")
    image_sha = _sha256(image_set_path)
    image_set = json.loads(image_set_path.read_text(encoding="utf-8"))
    reviewed_images = review.get("images")
    roles = image_set.get("roles") if isinstance(image_set, dict) else None
    if not isinstance(reviewed_images, dict) or not isinstance(roles, list):
        raise WorkspaceError("image-set/final-review image bindings are invalid")
    observed_images = {
        row.get("role"): row.get("image_digest")
        for row in roles
        if isinstance(row, dict)
    }
    if observed_images != reviewed_images:
        raise WorkspaceError("image-set digests differ from final review")
    dependencies = {
        "runtime_code": bindings["runtime_source_commit"].ljust(64, "0"),
        "launch_surface": bindings["launch_surface_commit"].ljust(64, "0"),
        "eligible_roster": bindings["prelaunch_root_sha256"],
        "power_rng": bindings["c120_power_final_sha256"],
    }
    version = ExperimentVersion(
        version_id="r2",
        parent_version_id=None,
        hypothesis_status="confirmatory",
        action_id=review["action_id"],
        run_spec_sha256=bindings["run_spec_sha256"],
        package_sha256=package_sha,
        authorization_sha256=bindings["authorization_sha256"],
        image_set_sha256=image_sha,
        power_sha256=bindings["c120_power_final_sha256"],
        declared_criteria_sha256=bindings["launch_plan_sha256"],
        version_ceiling_microusd=round(float(surface["max_usd"]) * 1_000_000),
        dependencies=dependencies,
    )
    manifest = CampaignManifest(
        campaign_id="placebo-official-campaign-20260806",
        aws_account_id="892077329800",
        region="us-east-1",
        ceiling_microusd=7_500_000_000,
        root_version_id="r2",
        allowed_resource_classes=("batch", "ec2", "ecr", "iam", "s3", "network"),
        tag_namespace="pneuma-rapid-campaign",
    )
    if projected_microusd > version.version_ceiling_microusd:
        raise WorkspaceError("projection exceeds the immutable r2 ceiling")
    config = {
        "record_kind": "rapid_campaign_private_config",
        "schema_version": "0.1.0",
        "mode": mode,
        "final_review_path": str(final_review_path.resolve()),
        "final_review_sha256": _sha256(final_review_path),
        "package_path": str(package_path.resolve()),
        "image_set_path": str(image_set_path.resolve()),
        "power_root": str(power_root.resolve()) if power_root is not None else None,
        "projected_microusd": projected_microusd,
        "repo_root": str(Path.cwd().resolve()),
    }
    _write_once(root / "manifest.json", manifest.to_mapping())
    _write_once(root / "versions" / "r2.json", version.to_mapping())
    _write_once(root / "private-config.json", config)
    _write_once(root / "spend.json", SpendLedger(ceiling_microusd=manifest.ceiling_microusd).to_mapping())
    CampaignStateStore(root / "versions" / "r2" / "state.json", campaign_id=manifest.campaign_id, version_id="r2")
    return manifest, version


def load_workspace(root: Path) -> tuple[CampaignManifest, ExperimentVersion, dict[str, Any], SpendLedger, CampaignStateStore]:
    try:
        manifest = CampaignManifest.from_mapping(json.loads((root / "manifest.json").read_text(encoding="utf-8")))
        version = ExperimentVersion.from_mapping(json.loads((root / "versions" / "r2.json").read_text(encoding="utf-8")))
        config = json.loads((root / "private-config.json").read_text(encoding="utf-8"))
        ledger = SpendLedger.from_mapping(json.loads((root / "spend.json").read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise WorkspaceError("campaign workspace is unreadable or invalid") from exc
    if not isinstance(config, dict) or config.get("record_kind") != "rapid_campaign_private_config":
        raise WorkspaceError("private campaign configuration differs")
    store = CampaignStateStore(
        root / "versions" / "r2" / "state.json",
        campaign_id=manifest.campaign_id,
        version_id=version.version_id,
    )
    return manifest, version, config, ledger, store


def save_spend(root: Path, ledger: SpendLedger) -> None:
    path = root / "spend.json"
    temporary = path.with_name(".spend.json.tmp")
    temporary.write_bytes(canonical_bytes(ledger.to_mapping()))
    os.replace(temporary, path)


def verify_workspace_bindings(root: Path) -> dict[str, object]:
    manifest, version, config, ledger, store = load_workspace(root)
    package_path = Path(config["package_path"])
    image_path = Path(config["image_set_path"])
    review_path = Path(config["final_review_path"])
    if _sha256(package_path) != version.package_sha256:
        raise WorkspaceError("current package bytes differ")
    if _sha256(image_path) != version.image_set_sha256:
        raise WorkspaceError("current image-set bytes differ")
    if _sha256(review_path) != config["final_review_sha256"]:
        raise WorkspaceError("current final-review bytes differ")
    if config["mode"] == "official":
        if not config.get("power_root"):
            raise WorkspaceError("official campaign lacks the frozen power root")
        power_final = Path(config["power_root"]) / "c120-final.json"
        if _sha256(power_final) != version.power_sha256:
            raise WorkspaceError("frozen power-final bytes differ")
    return {
        "campaign_id": manifest.campaign_id,
        "version_id": version.version_id,
        "action_id": version.action_id,
        "phase": store.snapshot().phase,
        "campaign_ceiling_microusd": manifest.ceiling_microusd,
        "version_ceiling_microusd": version.version_ceiling_microusd,
        "projected_microusd": config["projected_microusd"],
        "remaining_microusd": ledger.remaining_microusd,
        "impact": "ROOT",
        "regenerate": [],
        "rerun_power": False,
        "rebuild_images": False,
        "bindings_sha256": digest_record({"manifest": manifest.to_mapping(), "version": version.to_mapping()}),
    }
