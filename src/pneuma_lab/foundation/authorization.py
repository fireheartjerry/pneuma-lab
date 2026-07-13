"""Hash-bound, registry-aware preflight for every foundation training stage."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from pneuma_lab.foundation.data import governed_dataset_groups
from pneuma_lab.foundation.specs import MODEL_SPECS
from pneuma_lab.schemas import load_schema


class FoundationAuthorizationError(ValueError):
    """Raised before model allocation when an authorization binding fails."""


@dataclass(frozen=True)
class VerifiedFoundationAuthorization:
    model_key: str
    token_ceiling: int
    shard_path: Path
    shard_manifest_path: Path
    output_root: Path
    positive_weight_groups: tuple[str, ...]
    manifest: dict


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def authorization_scope_digest(manifest: dict) -> str:
    """Digest every scoped field while excluding the approval that carries it."""

    value = copy.deepcopy(manifest)
    value["operator_approval"] = None
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _repo_path(repo_root: Path, relative: str) -> Path:
    candidate = (repo_root / relative).resolve()
    if not _inside(candidate, repo_root.resolve()):
        raise FoundationAuthorizationError(f"path escapes repository: {relative!r}")
    return candidate


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FoundationAuthorizationError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FoundationAuthorizationError(f"expected JSON object: {path}")
    return value


def verify_foundation_authorization(
    authorization_path: Path,
    *,
    repo_root: Path,
    registry_path: Path,
) -> VerifiedFoundationAuthorization:
    """Verify authorization, corpus, roles, gates, paths, and budget."""

    repo_root = Path(repo_root).resolve()
    manifest = _load_json(Path(authorization_path))
    validator = Draft202012Validator(
        load_schema("foundation-training-authorization.schema.json"),
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(manifest), key=lambda error: list(error.path))
    if errors:
        detail = "; ".join(
            f"{'.'.join(str(part) for part in error.path) or '<root>'}: {error.message}"
            for error in errors
        )
        raise FoundationAuthorizationError(f"authorization schema invalid: {detail}")
    if manifest["authorization_status"] != "authorized":
        raise FoundationAuthorizationError("foundation training is not authorized")

    model = manifest["model"]
    spec = MODEL_SPECS[model["key"]]
    if model["model_id"] != spec.model_id or model["revision"] != spec.revision:
        raise FoundationAuthorizationError("authorization does not match the model pin")
    token_ceiling = int(model["token_ceiling"])

    shard = manifest["shard"]
    if shard is None:
        raise FoundationAuthorizationError("authorized training requires a bound shard")
    shard_path = _repo_path(repo_root, shard["path"])
    shard_manifest_path = _repo_path(repo_root, shard["manifest_path"])
    build_root = (repo_root / "build").resolve()
    if not _inside(shard_path, build_root) or not _inside(
        shard_manifest_path, build_root
    ):
        raise FoundationAuthorizationError("authorized shards must remain under build/")
    for path, expected in (
        (shard_path, shard["sha256"]),
        (shard_manifest_path, shard["manifest_sha256"]),
    ):
        if not path.is_file():
            raise FoundationAuthorizationError(
                f"authorized artifact is missing: {path}"
            )
        if _sha256_file(path) != expected:
            raise FoundationAuthorizationError(
                f"authorized artifact hash changed: {path}"
            )

    shard_manifest = _load_json(shard_manifest_path)
    required_inventory = {
        "token_count",
        "repository_count",
        "issue_count",
        "languages",
        "tools",
        "trajectory_length",
        "labels",
    }
    inventory = shard_manifest.get("inventory")
    if not isinstance(inventory, dict) or not required_inventory.issubset(inventory):
        raise FoundationAuthorizationError("shard diversity inventory is incomplete")

    policy = manifest["dataset_policy"]
    if not policy["repo_issue_disjoint"]:
        raise FoundationAuthorizationError(
            "repository/issue evaluation disjointness failed"
        )
    if not policy["diversity_inventory_present"]:
        raise FoundationAuthorizationError("diversity inventory gate is false")
    roles = governed_dataset_groups(_load_json(Path(registry_path)))
    if set(policy["governed_groups"]) != set(roles):
        raise FoundationAuthorizationError("authorization must govern all ten groups")
    positive = tuple(sorted(policy["positive_weight_groups"]))
    if not positive:
        raise FoundationAuthorizationError(
            "authorized training needs a positive-weight group"
        )
    blocked = [
        group
        for group in positive
        if group not in roles or not roles[group].training_authorized
    ]
    if blocked:
        raise FoundationAuthorizationError(
            f"positive-weight groups are not registry-authorized: {blocked}"
        )

    gates = manifest["local_gates"]
    if token_ceiling > 100_000 and not gates["previous_stage_passed"]:
        raise FoundationAuthorizationError(
            "later stage requires previous-stage success"
        )
    if token_ceiling > 100_000 and not gates["resource_smoke_passed"]:
        raise FoundationAuthorizationError(
            "later stage requires the resource smoke gate"
        )
    if (token_ceiling > 2_000_000 or model["key"] == "4b") and not gates[
        "falsification_gate_passed"
    ]:
        raise FoundationAuthorizationError("promotion requires the falsification gate")

    output_root = _repo_path(repo_root, manifest["output_root"])
    if not _inside(output_root, build_root):
        raise FoundationAuthorizationError("output root must remain under build/")
    if manifest["source_data_policy"]["write_allowed"] is not False:
        raise FoundationAuthorizationError("the external corpus must remain read-only")
    approval = manifest["operator_approval"]
    if approval is None:
        raise FoundationAuthorizationError("operator approval is required")
    if approval["scope_digest"] != authorization_scope_digest(manifest):
        raise FoundationAuthorizationError("operator scope digest does not match")
    budget = manifest["budget"]
    if budget["paid_compute_usd"] != 0 or budget["cloud_jobs_used"] != 0:
        raise FoundationAuthorizationError("local training authorization must cost $0")

    return VerifiedFoundationAuthorization(
        model_key=model["key"],
        token_ceiling=token_ceiling,
        shard_path=shard_path,
        shard_manifest_path=shard_manifest_path,
        output_root=output_root,
        positive_weight_groups=positive,
        manifest=manifest,
    )
