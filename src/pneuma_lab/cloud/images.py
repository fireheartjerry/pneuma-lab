"""Static image-recipe inspection; never pulls or builds an image."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .errors import CloudManifestError


_QUALIFICATION_IMAGE_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_GIT_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def recipe_digest(paths: Sequence[Path]) -> str:
    """Hash named recipe files in a fixed path-and-byte order."""

    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix()):
        digest.update(path.as_posix().encode("utf-8") + b"\0" + path.read_bytes())
    return digest.hexdigest()


def validate_image_manifest(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reject swapped images, duplicate roles, or fixture promotion."""

    from .manifests import _validate

    manifest = _validate(record, expected_kind="cloud_image_manifest")
    images = manifest["images"]
    names = {image["name"] for image in images}
    if names != {"controller", "model-server", "benchmark-worker"}:
        raise CloudManifestError("image manifest must bind exactly three roles")
    if any(image["image_digest"] is not None or image["sbom_sha256"] is not None for image in images):
        raise CloudManifestError("Step 7A manifest cannot claim a built image or SBOM")
    return manifest


def validate_image_build_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate Step 7B double-build evidence without performing a build."""

    from .manifests import _validate

    receipt = _validate(record, expected_kind="cloud_image_build_receipt")
    digests = receipt["build_image_digests"]
    observed_reproducible = digests[0] == digests[1]
    if receipt["reproducible"] != observed_reproducible:
        raise CloudManifestError("reproducible must equal the two-digest comparison")
    return receipt


def validate_image_build_set(records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    """Require a complete, single-recipe, reproducible three-role build set."""

    receipts = tuple(validate_image_build_receipt(record) for record in records)
    if {record["role"] for record in receipts} != {"controller", "model-server", "benchmark-worker"}:
        raise CloudManifestError("Step 7B requires exactly one receipt for each image role")
    if len(receipts) != 3 or len({record["recipe_sha256"] for record in receipts}) != 1:
        raise CloudManifestError("Step 7B build receipts must bind one recipe exactly once per role")
    if len({record["input_lock_sha256"] for record in receipts}) != 1:
        raise CloudManifestError("Step 7B build receipts must bind one exact Step 5B input lock")
    if not all(record["reproducible"] for record in receipts):
        raise CloudManifestError("Step 7B remains blocked by a non-reproducible image")
    return receipts


def require_qualification_image_binding(
    evidence_root: Path,
    *,
    image_digest: str,
    source_commit: str,
) -> dict[str, Any]:
    """Require one complete fixture-image receipt bound to this checkout.

    The image is immutable, but its digest can still point at an older source
    revision.  The concrete qualification runner must reject that stale
    source/image pair before any provider mutation.
    """

    if not _QUALIFICATION_IMAGE_DIGEST_RE.fullmatch(image_digest):
        raise CloudManifestError(
            "qualification image binding is not an immutable digest"
        )
    if not _GIT_COMMIT_RE.fullmatch(source_commit):
        raise CloudManifestError(
            "qualification source revision is not a full commit"
        )
    if not evidence_root.is_dir():
        raise CloudManifestError("qualification image evidence root is missing")

    matches: list[dict[str, Any]] = []
    for path in sorted(evidence_root.glob("qualification-image-build-*-receipt-*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, Mapping):
            continue
        target = record.get("target")
        if (
            isinstance(target, Mapping)
            and target.get("ecr_image_digest") == image_digest
        ):
            matches.append(dict(record))
    if len(matches) != 1:
        raise CloudManifestError(
            "qualification image digest must match exactly one retained build receipt"
        )
    record = matches[0]
    if record.get("status") != "COMPLETE" or record.get("provider") != "aws":
        raise CloudManifestError("qualification image build receipt is not complete")
    target = record.get("target")
    if (
        not isinstance(target, Mapping)
        or target.get("fresh_read_digest_match") is not True
        or target.get("repository_tag_mutability") != "IMMUTABLE"
        or target.get("ecr_image_digest") != image_digest
    ):
        raise CloudManifestError("qualification image ECR immutability evidence is incomplete")
    source = record.get("source")
    checks = record.get("local_checks")
    fixture = checks.get("fixture_runtime") if isinstance(checks, Mapping) else None
    package = checks.get("package_import") if isinstance(checks, Mapping) else None
    aws_cli = checks.get("aws_cli") if isinstance(checks, Mapping) else None
    if not isinstance(source, Mapping) or source.get("commit") != source_commit:
        raise CloudManifestError(
            "qualification image was built from a different source revision"
        )
    if not isinstance(checks, Mapping) or not isinstance(fixture, Mapping):
        raise CloudManifestError(
            "qualification image receipt lacks fixture runtime evidence"
        )
    if checks.get("source_revision_label") != source_commit:
        raise CloudManifestError("qualification image source labels disagree")
    if (
        checks.get("image_entrypoint") != "/opt/pneuma/fixed_admission_entrypoint.sh"
        or checks.get("image_entrypoint_check") != "pass"
        or checks.get("image_cmd_override") != "absent"
        or checks.get("fresh_ecr_read") != "pass"
    ):
        raise CloudManifestError(
            "qualification image fixed ENTRYPOINT evidence is incomplete"
        )
    if (
        not isinstance(aws_cli, Mapping)
        or aws_cli.get("check") != "pass"
        or not isinstance(package, Mapping)
        or package.get("pneuma_lab") != "pass"
        or not isinstance(checks.get("runtime_schema"), str)
    ):
        raise CloudManifestError(
            "qualification image runtime dependency evidence is incomplete"
        )
    if (
        fixture.get("network") != "none"
        or fixture.get("gpu") is not False
        or fixture.get("model_download") is not False
        or fixture.get("model_loaded") is not False
        or fixture.get("immutable_worker_indexed_artifact") != "worker-0"
        or fixture.get("all_five_inputs_materialized_as_readable_local_files") is not True
        or fixture.get("retrieved_bytes_match") is not True
    ):
        raise CloudManifestError(
            "qualification image fixture-only runtime evidence is incomplete"
        )
    return record


def inspect_dockerfile(path: Path) -> None:
    """Enforce immutable base syntax and no unpinned pip install."""

    lines = path.read_text(encoding="utf-8").splitlines()
    if not any(line.startswith("FROM ") and "@sha256:" in line for line in lines):
        raise CloudManifestError("Dockerfile requires a digest-pinned FROM")
    for line in lines:
        if "pip install" in line and "==" not in line and "--require-hashes -r" not in line:
            raise CloudManifestError("Dockerfile has an unpinned pip install")
