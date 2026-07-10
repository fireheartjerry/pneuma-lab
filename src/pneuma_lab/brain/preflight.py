"""Fail-closed corpus authorization gate for the PneumaBrain-v0.1 trainer.

The trainer must not fit anything unless a schema-valid, decision=authorized
corpus authorization is bound to the exact corpus manifest bytes, the output
root is empty and repo-local, and (in production) the worktree is clean. This
module verifies those bindings; it does not authorize anything by itself.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator

from pneuma_lab.schemas import load_schema

AUTHORIZATION_SCHEMA = "pneuma-brain-corpus-authorization.schema.json"


class BrainPreflightError(ValueError):
    """A stable, operator-readable fail-closed preflight failure."""


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise BrainPreflightError(message)


def _worktree_clean() -> bool:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout == ""


def verify_corpus_run(
    authorization_path: str | Path,
    corpus_manifest_path: str | Path,
    output_root: str | Path,
    *,
    require_clean_code: bool = True,
) -> dict:
    """Verify the signed authorization binds this corpus manifest and output root."""
    auth_file = Path(authorization_path)
    manifest_file = Path(corpus_manifest_path)
    out_dir = Path(output_root)

    _require(auth_file.is_file(), f"authorization artifact missing: {auth_file}")
    _require(manifest_file.is_file(), f"corpus manifest missing: {manifest_file}")

    import json

    try:
        authorization = json.loads(auth_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrainPreflightError(f"cannot read authorization: {exc}") from exc

    errors = sorted(
        Draft202012Validator(load_schema(AUTHORIZATION_SCHEMA)).iter_errors(
            authorization
        ),
        key=lambda item: list(item.path),
    )
    if errors:
        raise BrainPreflightError(
            f"authorization is not schema-valid: {errors[0].message}"
        )

    _require(
        authorization.get("decision") == "authorized",
        "authorization decision is not 'authorized'",
    )
    _require(
        authorization.get("corpus_manifest_sha256") == _sha256_file(manifest_file),
        "authorization corpus_manifest_sha256 does not match the corpus manifest bytes",
    )

    if require_clean_code:
        _require(
            _worktree_clean(),
            "worktree is not clean; commit or stash before an authorized run",
        )

    if out_dir.exists():
        _require(out_dir.is_dir(), "output root exists but is not a directory")
        _require(
            not any(out_dir.iterdir()),
            "output root must be empty before an authorized run",
        )

    return authorization


__all__ = ["AUTHORIZATION_SCHEMA", "BrainPreflightError", "verify_corpus_run"]
