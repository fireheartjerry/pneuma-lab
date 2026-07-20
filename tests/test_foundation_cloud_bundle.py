"""Authorized-only cloud reproduction bundle and quote-gated candidates.

The real ``verify_foundation_authorization`` requires the complete
preparation pipeline plus the pinned tokenizer snapshot; those handshakes
are exercised end to end in ``tests/test_foundation_authorization.py``.
Here the verifier is stubbed at the module seam so the downstream bundle
policy (transfer posture, raw-corpus and blocked-name guards, quote gate,
deterministic tar output) is tested hermetically.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import tarfile
from pathlib import Path

import pytest

from pneuma_lab.foundation import cloud_bundle
from pneuma_lab.foundation.authorization import (
    FoundationAuthorizationError,
    VerifiedFoundationAuthorization,
    authorization_scope_digest,
)
from pneuma_lab.foundation.budget import BudgetViolation, CloudQuote
from pneuma_lab.foundation.cloud_bundle import (
    CloudBundleError,
    CloudBundleRequest,
    build_cloud_bundle,
    build_cloud_bundle_for_cli,
    build_cloud_reproduction_candidate,
)
from pneuma_lab.foundation.specs import MODEL_SPECS


APPROVED_AT = "2026-07-15T12:00:00Z"
_REVISION = MODEL_SPECS["2b"].revision
_ARTIFACT_NAMES = (
    "preparation_manifest",
    "suite_report",
    "license_receipt",
    "source_presence_receipt",
    "source_integrity_receipt",
    "shard",
    "shard_manifest",
    "split_receipt",
    "contamination_receipt",
    "diversity_receipt",
    "selection_receipt",
)
_LOCAL_PROFILE = {
    "profile": "wsl2_local_nf4",
    "quantization": "nf4_double_quant",
    "core_dtype": "bf16",
    "projection_dtype": "bf16",
    "gradient_checkpointing": True,
    "sequence_length": 512,
    "microbatch_size": 1,
    "gradient_accumulation": 32,
    "data_loader_workers": 8,
    "max_ram_gb": 24.0,
    "max_vram_gb": 7.5,
}


@pytest.fixture(autouse=True)
def _stub_verifier(monkeypatch):
    """Replace the heavyweight verifier with a manifest-reading stub."""

    def fake_verify(path, *, repo_root, registry_path=None, _tokenizer_loader=None):
        del registry_path, _tokenizer_loader
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        if manifest.get("authorization_status") != "authorized":
            raise FoundationAuthorizationError("foundation training is not authorized")
        scope = manifest["scope"]
        root = Path(repo_root)
        return VerifiedFoundationAuthorization(
            model_key=scope["model"]["key"],
            token_ceiling=scope["token_ceiling"],
            shard_path=root / scope["artifacts"]["shard"]["path"],
            shard_manifest_path=root / scope["artifacts"]["shard_manifest"]["path"],
            output_root=root / "build/foundation/runs",
            authorized_lane_weights=scope["authorized_lane_weights"],
            authorized_record_membership={},
            scope_digest=manifest["scope_digest"],
            manifest=manifest,
        )

    monkeypatch.setattr(cloud_bundle, "verify_foundation_authorization", fake_verify)


def _git(repo: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _init_repo(root: Path) -> None:
    (root / ".gitignore").write_text("/build/\n/pneuma-data/\n", encoding="utf-8")
    (root / "uv.lock").write_text("# pinned dependency lock\n", encoding="utf-8")
    setup = root / "scripts" / "foundation" / "setup-linux.sh"
    setup.parent.mkdir(parents=True, exist_ok=True)
    setup.write_text("#!/bin/sh\necho inert\n", encoding="utf-8")
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "demo.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "notebook.ipynb").write_text("{}\n", encoding="utf-8")
    (root / ".env").write_text("SECRET=never\n", encoding="utf-8")
    _git(root, "init")
    _git(root, "config", "user.email", "tests@pneuma.invalid")
    _git(root, "config", "user.name", "Pneuma Tests")
    _git(root, "add", "-f", ".")
    _git(root, "commit", "-m", "fixture")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=4, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_artifact(root: Path, relative: str, payload: bytes) -> dict:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "path": relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }


def _local_scope(root: Path, *, stage: str = "2m") -> dict:
    artifacts = {
        name: _write_artifact(
            root,
            f"build/foundation/preparation/{stage}/{name}.json",
            f'{{"artifact": "{name}"}}\n'.encode("utf-8"),
        )
        for name in _ARTIFACT_NAMES
    }
    conversion = {
        name: _write_artifact(
            root,
            f"build/foundation/preparation/{stage}/conversion/{name}.jsonl",
            f'{{"conversion": "{name}"}}\n'.encode("utf-8"),
        )
        for name in (
            "examples",
            "invalid_examples",
            "conversion_report",
            "hash_manifest",
        )
    }
    eval_identities = {
        "swe-bench": _write_artifact(
            root,
            f"build/foundation/preparation/{stage}/eval-identities/swe-bench.jsonl",
            b'{"family": "swe-bench"}\n',
        )
    }
    return {
        "model": {
            "key": "2b",
            "model_id": "Qwen/Qwen3.5-2B",
            "revision": _REVISION,
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": _REVISION,
        },
        "tokenizer_snapshot": {
            "path": f"build/cache/models/2b/{_REVISION}",
            "model_id": "Qwen/Qwen3.5-2B",
            "revision": _REVISION,
            "receipt_sha256": hashlib.sha256(b"receipt").hexdigest(),
            "snapshot_sha256": hashlib.sha256(b"snapshot").hexdigest(),
        },
        "stage": stage,
        "token_ceiling": 2_000_000 if stage == "2m" else 8_000_000,
        "local_profile": dict(_LOCAL_PROFILE),
        "learning_rates": [0.00005, 0.0001, 0.0002],
        "code_commit": "a" * 40,
        "artifacts": artifacts,
        "evidence_artifacts": {
            "conversion": conversion,
            "eval_identities": eval_identities,
        },
        "authorized_lane_weights": {"swe-gym-openhands-sampled": 1.0},
        "source_data_policy": {
            "root": "C:\\pneuma-data",
            "write_allowed": False,
            "private_cloud_transfer": False,
        },
        "output_root": "build/foundation/runs/",
        "budget": {
            "paid_compute_usd": 0,
            "paid_compute_ceiling_usd": 0,
            "cloud_jobs_used": 0,
            "cloud_jobs_ceiling": 0,
            "cloud_lifetime_cap_usd": 45,
        },
    }


def _authorized_manifest(scope: dict) -> dict:
    digest = authorization_scope_digest(scope)
    phrase = f"I APPROVE THIS EXACT PNEUMA FOUNDATION SCOPE {digest}"
    return {
        "manifest_kind": "pneuma_foundation_training_authorization",
        "manifest_schema_version": "0.2.0",
        "authorization_status": "authorized",
        "scope": scope,
        "scope_digest": digest,
        "operator_approval": {
            "operator_id": "student-operator",
            "approved_at": APPROVED_AT,
            "scope_digest": digest,
            "approval_phrase_sha256": hashlib.sha256(
                phrase.encode("utf-8")
            ).hexdigest(),
        },
    }


def _local_authorization(root: Path) -> Path:
    manifest = _authorized_manifest(_local_scope(root))
    path = root / "build/foundation/authorizations/final/2m.json"
    _write_json(path, manifest)
    return path


def _local_gate_report(root: Path, *, passed: bool) -> Path:
    path = root / "build/foundation/gates/local-gate-report.json"
    _write_json(path, {"local_gates_passed": passed})
    return path


def _safe_quote(**overrides) -> CloudQuote:
    values = {
        "hourly_usd": 0.44,
        "tax_inclusive_usd": 38.0,
        "prepaid_credit_usd": 38.0,
        "auto_pay_enabled": False,
        "termination_hours": 72,
        "measured_tokens_per_second": 20.0,
        "prior_lifetime_spend_usd": 0.0,
    }
    values.update(overrides)
    return CloudQuote(**values)


def _cloud_authorization(
    root: Path,
    *,
    stage: str = "2m",
    cloud_transfer_allowed: bool = True,
    shard_override: Path | None = None,
) -> Path:
    scope = _local_scope(root, stage=stage)
    scope["execution_profile"] = "cloud"
    if cloud_transfer_allowed:
        scope["source_data_policy"]["root"] = "bundle://authorized-shard"
        scope["source_data_policy"]["private_cloud_transfer_allowed"] = True
    scope["local_gate_report"] = _write_artifact(
        root,
        "build/foundation/gates/local-gate-report.json",
        b'{"local_gates_passed": true}\n',
    )
    scope["budget"] = {
        "paid_compute_usd": 0,
        "cloud_jobs_used": 0,
        "paid_compute_ceiling_usd": 38.0,
        "cloud_job_ceiling": 1,
        "cloud_lifetime_cap_usd": 45,
    }
    if shard_override is not None:
        scope["artifacts"]["shard"] = {
            "path": str(shard_override),
            "sha256": hashlib.sha256(b"raw").hexdigest(),
            "size": 3,
        }
    manifest = _authorized_manifest(scope)
    path = root / f"build/foundation/authorizations/final/{stage}-cloud.json"
    _write_json(path, manifest)
    return path


def _bundle_request(
    root: Path,
    *,
    source_paths: list[Path] | None = None,
    cloud_transfer_allowed: bool = True,
    stage: str = "2m",
    dry_run: bool = True,
    quote: CloudQuote | None = None,
) -> CloudBundleRequest:
    _init_repo(root)
    _write_artifact(
        root,
        f"build/cache/models/2b/{_REVISION}/pneuma-snapshot-receipt.json",
        b'{"receipt_kind": "pneuma_pinned_model_snapshot"}\n',
    )
    authorization_path = _cloud_authorization(
        root,
        stage=stage,
        cloud_transfer_allowed=cloud_transfer_allowed,
        shard_override=source_paths[0] if source_paths else None,
    )
    return CloudBundleRequest(
        repo_root=root,
        data_root=root / "pneuma-data",
        authorization_path=authorization_path,
        output_path=root / f"build/foundation/cloud/{stage}-bundle.tar",
        stage=stage,
        quote=quote or _safe_quote(),
        dry_run=dry_run,
    )


def test_cloud_bundle_rejects_raw_corpus_and_unapproved_transfer(
    tmp_path: Path,
) -> None:
    request = _bundle_request(tmp_path, source_paths=[tmp_path / "pneuma-data/raw/x"])
    with pytest.raises(CloudBundleError, match="raw corpus"):
        build_cloud_bundle(request)
    request = _bundle_request(tmp_path, cloud_transfer_allowed=False)
    with pytest.raises(CloudBundleError, match="transfer posture"):
        build_cloud_bundle(request)


def test_cloud_bundle_rejects_blocked_dataset_names(tmp_path: Path) -> None:
    request = _bundle_request(
        tmp_path, source_paths=[tmp_path / "exports/swe-chat/rows.jsonl"]
    )
    with pytest.raises(CloudBundleError, match="blocked dataset"):
        build_cloud_bundle(request)
    request = _bundle_request(
        tmp_path, source_paths=[tmp_path / "exports/sec-bench-pro/rows.jsonl"]
    )
    with pytest.raises(CloudBundleError, match="blocked dataset"):
        build_cloud_bundle(request)


def test_cloud_bundle_rejects_a_stage_mismatch(tmp_path: Path) -> None:
    request = _bundle_request(tmp_path)
    mismatched = CloudBundleRequest(
        repo_root=request.repo_root,
        data_root=request.data_root,
        authorization_path=request.authorization_path,
        output_path=request.output_path,
        stage="8m",
        quote=request.quote,
        dry_run=True,
    )
    with pytest.raises(CloudBundleError, match="stage"):
        build_cloud_bundle(mismatched)


def test_dry_run_lists_only_permitted_files_and_writes_nothing(
    tmp_path: Path,
) -> None:
    request = _bundle_request(tmp_path)
    manifest = build_cloud_bundle(request)
    assert not request.output_path.exists()
    arcnames = [entry["arcname"] for entry in manifest["files"]]
    assert arcnames == sorted(arcnames)
    assert "uv.lock" in arcnames
    assert "scripts/foundation/setup-linux.sh" in arcnames
    assert "src/demo.py" in arcnames
    assert "build/foundation/authorizations/final/2m-cloud.json" in arcnames
    assert "build/foundation/preparation/2m/shard.json" in arcnames
    assert f"build/cache/models/2b/{_REVISION}/pneuma-snapshot-receipt.json" in arcnames
    assert manifest["network_access"] == "none"
    assert manifest["quote"]["allowed"] is True
    for arcname in arcnames:
        assert "pneuma-data" not in arcname
        assert not arcname.endswith(".ipynb")
        assert ".env" not in arcname


def test_bundle_tar_is_byte_deterministic(tmp_path: Path) -> None:
    request = _bundle_request(tmp_path, dry_run=False)
    build_cloud_bundle(request)
    first = hashlib.sha256(request.output_path.read_bytes()).hexdigest()
    build_cloud_bundle(request)
    second = hashlib.sha256(request.output_path.read_bytes()).hexdigest()
    assert first == second
    with tarfile.open(request.output_path) as archive:
        members = archive.getmembers()
        assert members[0].name == "PNEUMA_CLOUD_BUNDLE_MANIFEST.json"
        for member in members:
            assert member.mtime == 0
            assert member.uid == 0 and member.gid == 0
            assert member.uname == "" and member.gname == ""


def test_cli_adapter_builds_a_conservative_quote(tmp_path: Path) -> None:
    request = _bundle_request(tmp_path)
    manifest = build_cloud_bundle_for_cli(
        stage="2m",
        authorization_path=request.authorization_path,
        quoted_hourly_usd=0.44,
        quoted_tax_inclusive_usd=38.0,
        output_path=request.output_path,
        repo_root=tmp_path,
        dry_run=True,
    )
    assert manifest["quote"]["allowed"] is True
    assert not request.output_path.exists()


def test_cli_adapter_fails_closed_for_8m_without_measured_speed(
    tmp_path: Path,
) -> None:
    request = _bundle_request(tmp_path, stage="8m")
    with pytest.raises(BudgetViolation, match="30.9"):
        build_cloud_bundle_for_cli(
            stage="8m",
            authorization_path=request.authorization_path,
            quoted_hourly_usd=0.44,
            quoted_tax_inclusive_usd=38.0,
            output_path=request.output_path,
            repo_root=tmp_path,
            dry_run=True,
        )


def test_cloud_candidate_is_separate_and_binds_local_gates(tmp_path: Path) -> None:
    candidate = build_cloud_reproduction_candidate(
        _local_authorization(tmp_path),
        local_gate_report_path=_local_gate_report(tmp_path, passed=True),
        quote=_safe_quote(),
        output_path=tmp_path
        / "build/foundation/authorizations/candidates/2m-cloud.json",
        repo_root=tmp_path,
    )
    assert candidate["authorization_status"] == "candidate"
    assert candidate["scope"]["execution_profile"] == "cloud"
    assert (
        candidate["scope"]["source_data_policy"]["private_cloud_transfer_allowed"]
        is True
    )
    assert candidate["scope"]["local_gate_report"]["sha256"]
    assert candidate["operator_approval"] is None
    assert candidate["scope_digest"] == authorization_scope_digest(candidate["scope"])
    written = json.loads(
        (
            tmp_path / "build/foundation/authorizations/candidates/2m-cloud.json"
        ).read_text(encoding="utf-8")
    )
    assert written == candidate


def test_cloud_candidate_requires_passing_local_gates(tmp_path: Path) -> None:
    with pytest.raises(CloudBundleError, match="local gates"):
        build_cloud_reproduction_candidate(
            _local_authorization(tmp_path),
            local_gate_report_path=_local_gate_report(tmp_path, passed=False),
            quote=_safe_quote(),
            output_path=tmp_path
            / "build/foundation/authorizations/candidates/2m-cloud.json",
            repo_root=tmp_path,
        )


def test_cloud_candidate_rejects_an_inexact_output_path(tmp_path: Path) -> None:
    with pytest.raises(CloudBundleError, match="cloud.json"):
        build_cloud_reproduction_candidate(
            _local_authorization(tmp_path),
            local_gate_report_path=_local_gate_report(tmp_path, passed=True),
            quote=_safe_quote(),
            output_path=tmp_path / "build/foundation/authorizations/candidates/2m.json",
            repo_root=tmp_path,
        )


def test_cloud_candidate_rejects_a_cloud_source_authorization(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    cloud_path = _cloud_authorization(tmp_path)
    with pytest.raises(CloudBundleError, match="local authorization"):
        build_cloud_reproduction_candidate(
            cloud_path,
            local_gate_report_path=_local_gate_report(tmp_path, passed=True),
            quote=_safe_quote(),
            output_path=tmp_path
            / "build/foundation/authorizations/candidates/2m-cloud.json",
            repo_root=tmp_path,
        )


def test_cloud_candidate_enforces_quote_caps(tmp_path: Path) -> None:
    with pytest.raises(BudgetViolation, match="45"):
        build_cloud_reproduction_candidate(
            _local_authorization(tmp_path),
            local_gate_report_path=_local_gate_report(tmp_path, passed=True),
            quote=_safe_quote(tax_inclusive_usd=45.01),
            output_path=tmp_path
            / "build/foundation/authorizations/candidates/2m-cloud.json",
            repo_root=tmp_path,
        )
    with pytest.raises(BudgetViolation, match="auto-pay"):
        build_cloud_reproduction_candidate(
            _local_authorization(tmp_path),
            local_gate_report_path=_local_gate_report(tmp_path, passed=True),
            quote=_safe_quote(auto_pay_enabled=True),
            output_path=tmp_path
            / "build/foundation/authorizations/candidates/2m-cloud.json",
            repo_root=tmp_path,
        )


def test_cloud_candidate_accepts_cli_primitives(tmp_path: Path) -> None:
    candidate = build_cloud_reproduction_candidate(
        _local_authorization(tmp_path),
        local_gate_report_path=_local_gate_report(tmp_path, passed=True),
        quoted_hourly_usd=0.44,
        quoted_tax_inclusive_usd=38.0,
        output_path=tmp_path
        / "build/foundation/authorizations/candidates/2m-cloud.json",
        repo_root=tmp_path,
    )
    assert candidate["scope"]["budget"]["paid_compute_ceiling_usd"] == 38.0
    assert candidate["scope"]["budget"]["cloud_job_ceiling"] == 1
    with pytest.raises(CloudBundleError, match="not both"):
        build_cloud_reproduction_candidate(
            _local_authorization(tmp_path),
            local_gate_report_path=_local_gate_report(tmp_path, passed=True),
            quote=_safe_quote(),
            quoted_hourly_usd=0.44,
            output_path=tmp_path
            / "build/foundation/authorizations/candidates/2m-cloud.json",
            repo_root=tmp_path,
        )
