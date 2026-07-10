from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pneuma_lab.brain import train

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "brain"
CORPUS = FIXTURES / "synthetic_corpus.jsonl"
AUTH = FIXTURES / "authorization_authorized.json"


def _prepare_auth(tmp_path) -> Path:
    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"corpus_id":"pneuma-brain-v0"}', encoding="utf-8")
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    auth["corpus_manifest_sha256"] = (
        "sha256:" + hashlib.sha256(manifest.read_bytes()).hexdigest()
    )
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    return auth_path, manifest


def test_run_training_writes_model_and_report(tmp_path) -> None:
    auth_path, manifest = _prepare_auth(tmp_path)
    out = tmp_path / "run"
    result = train.run_training(
        corpus_path=CORPUS,
        authorization_path=auth_path,
        corpus_manifest_path=manifest,
        output_root=out,
        require_clean_code=False,
    )
    assert (out / "model.json").is_file()
    assert (out / "metrics.json").is_file()
    assert (out / "report.md").is_file()
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert "RISK_PREDICTION" in metrics["tasks"]
    # The synthetic corpus is separable; dev AUROC should be strong.
    assert metrics["tasks"]["RISK_PREDICTION"]["dev"]["auroc"] >= 0.9


def test_run_training_is_byte_deterministic(tmp_path) -> None:
    auth_path, manifest = _prepare_auth(tmp_path)
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    train.run_training(
        corpus_path=CORPUS,
        authorization_path=auth_path,
        corpus_manifest_path=manifest,
        output_root=out_a,
        require_clean_code=False,
    )
    train.run_training(
        corpus_path=CORPUS,
        authorization_path=auth_path,
        corpus_manifest_path=manifest,
        output_root=out_b,
        require_clean_code=False,
    )
    assert (out_a / "model.json").read_bytes() == (out_b / "model.json").read_bytes()
