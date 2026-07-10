from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pneuma_lab.brain import preflight

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "brain"
    / "authorization_authorized.json"
)


def _sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_authorized_artifact_passes_when_manifest_hash_matches(tmp_path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"corpus_id":"pneuma-brain-v0"}', encoding="utf-8")
    auth = json.loads(FIXTURE.read_text(encoding="utf-8"))
    auth["corpus_manifest_sha256"] = _sha256_file(manifest)
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    out = tmp_path / "run"
    verified = preflight.verify_corpus_run(
        auth_path, manifest, out, require_clean_code=False
    )
    assert verified["decision"] == "authorized"


def test_not_authorized_decision_is_rejected(tmp_path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text("{}", encoding="utf-8")
    auth = json.loads(FIXTURE.read_text(encoding="utf-8"))
    auth["decision"] = "not_authorized"
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    with pytest.raises(preflight.BrainPreflightError):
        preflight.verify_corpus_run(
            auth_path, manifest, tmp_path / "run", require_clean_code=False
        )


def test_manifest_hash_mismatch_is_rejected(tmp_path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text("{}", encoding="utf-8")
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(
        FIXTURE.read_text(encoding="utf-8"), encoding="utf-8"
    )  # placeholder hash
    with pytest.raises(preflight.BrainPreflightError):
        preflight.verify_corpus_run(
            auth_path, manifest, tmp_path / "run", require_clean_code=False
        )


def test_nonempty_output_root_is_rejected(tmp_path) -> None:
    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"corpus_id":"pneuma-brain-v0"}', encoding="utf-8")
    auth = json.loads(FIXTURE.read_text(encoding="utf-8"))
    auth["corpus_manifest_sha256"] = _sha256_file(manifest)
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    out = tmp_path / "run"
    out.mkdir()
    (out / "stale.txt").write_text("x", encoding="utf-8")
    with pytest.raises(preflight.BrainPreflightError):
        preflight.verify_corpus_run(auth_path, manifest, out, require_clean_code=False)
