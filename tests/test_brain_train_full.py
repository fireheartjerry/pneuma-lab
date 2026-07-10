from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pneuma_lab.brain import train_full

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "brain"
TRACES = FIXTURES / "synthetic_traces.jsonl"
AUTH = FIXTURES / "authorization_authorized.json"


def _prepare(tmp_path):
    manifest = tmp_path / "corpus.json"
    manifest.write_text('{"corpus_id":"pneuma-brain-v0"}', encoding="utf-8")
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    auth["corpus_manifest_sha256"] = (
        "sha256:" + hashlib.sha256(manifest.read_bytes()).hexdigest()
    )
    auth_path = tmp_path / "auth.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    return auth_path, manifest


def test_full_training_writes_all_artifacts_and_prefixes(tmp_path):
    auth_path, manifest = _prepare(tmp_path)
    out = tmp_path / "run"
    metrics = train_full.run_full_training(
        traces_path=TRACES,
        authorization_path=auth_path,
        corpus_manifest_path=manifest,
        output_root=out,
        n_resamples=200,
        require_clean_code=False,
    )
    assert (out / "model.json").is_file()
    assert (out / "metrics.json").is_file()
    assert (out / "report.md").is_file()
    assert set(metrics["prefixes"]) == {"prefix_25", "prefix_50", "full"}
    for prefix in ("prefix_25", "prefix_50", "full"):
        entry = metrics["prefixes"][prefix]
        assert entry["oof_auroc"] is not None
        assert (
            entry["bootstrap"]["lo"] <= entry["oof_auroc"] <= entry["bootstrap"]["hi"]
        )


def test_full_training_is_byte_deterministic(tmp_path):
    auth_path, manifest = _prepare(tmp_path)
    a, b = tmp_path / "a", tmp_path / "b"
    train_full.run_full_training(
        traces_path=TRACES,
        authorization_path=auth_path,
        corpus_manifest_path=manifest,
        output_root=a,
        n_resamples=200,
        require_clean_code=False,
    )
    train_full.run_full_training(
        traces_path=TRACES,
        authorization_path=auth_path,
        corpus_manifest_path=manifest,
        output_root=b,
        n_resamples=200,
        require_clean_code=False,
    )
    assert (a / "model.json").read_bytes() == (b / "model.json").read_bytes()
    assert (a / "metrics.json").read_bytes() == (b / "metrics.json").read_bytes()
