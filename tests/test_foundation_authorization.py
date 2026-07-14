"""Exact, hash-bound foundation authorization handshake tests."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

import pytest

from pneuma_lab.foundation.authorization import (
    APPROVAL_PHRASE_PREFIX,
    FoundationAuthorizationError,
    VerifiedFoundationAuthorization,
    apply_verified_authorization,
    artifact_binding,
    authorization_scope_digest,
    build_authorization_candidate,
    finalize_authorization,
    required_approval_phrase,
    verify_foundation_authorization,
)
from pneuma_lab.foundation.preparation import PreparationResult


ROOT = Path(__file__).resolve().parents[1]
APPROVED_AT = "2026-07-14T12:00:00Z"


def _git(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _strict_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=4, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _authorization_fixture(tmp_path: Path) -> tuple[Path, PreparationResult, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text("/build/\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("clean\n", encoding="utf-8")
    _git(repo, "init")
    _git(repo, "config", "user.email", "tests@pneuma.invalid")
    _git(repo, "config", "user.name", "Pneuma Tests")
    _git(repo, "add", ".gitignore", "tracked.txt")
    _git(repo, "commit", "-m", "fixture")
    commit = _git(repo, "rev-parse", "HEAD")

    output = repo / "build/foundation/preparation/100k"
    shard = output / "shards/records.jsonl"
    shard.parent.mkdir(parents=True)
    shard.write_text('{"record_id":"ftr:' + "a" * 64 + '"}\n', encoding="utf-8")
    shard_manifest = output / "shards/records.manifest.json"
    _write_json(
        shard_manifest,
        {
            "inventory": {
                "token_count": 1,
                "repository_count": 1,
                "issue_count": 1,
                "languages": {"python": 1},
                "tools": {"pytest": 1},
                "trajectory_length": {"min": 1, "max": 1, "mean": 1},
                "labels": {"resolved": 1},
            }
        },
    )
    names = (
        "suite_report.json",
        "license_receipt.json",
        "source_presence_receipt.json",
        "source_integrity_receipt.json",
        "split_receipt.json",
        "contamination_receipt.json",
        "diversity_receipt.json",
        "selection_receipt.json",
    )
    for name in names:
        value = {"fixture": name}
        if name == "selection_receipt.json":
            value.update(stage="100k", token_ceiling=100_000)
        _write_json(output / name, value)
    _write_json(
        output / "preparation_manifest.json",
        {
            "manifest_kind": "pneuma_foundation_preparation_manifest",
            "manifest_schema_version": "0.1.0",
            "stage": "100k",
            "token_ceiling": 100_000,
            "dry_run": False,
            "training_authorized": False,
            "persisted_training_weight": 0.0,
            "shard": {
                "artifact": shard.name,
                "manifest_artifact": shard_manifest.name,
            },
        },
    )
    candidate = repo / "build/foundation/authorizations/candidates/100k.json"
    preparation = PreparationResult(
        preparation_manifest_path=output / "preparation_manifest.json",
        suite_report_path=output / "suite_report.json",
        license_receipt_path=output / "license_receipt.json",
        source_presence_receipt_path=output / "source_presence_receipt.json",
        source_integrity_receipt_path=output / "source_integrity_receipt.json",
        shard_path=shard,
        shard_manifest_path=shard_manifest,
        split_receipt_path=output / "split_receipt.json",
        contamination_receipt_path=output / "contamination_receipt.json",
        diversity_receipt_path=output / "diversity_receipt.json",
        selection_receipt_path=output / "selection_receipt.json",
        authorization_candidate_path=candidate,
    )
    return repo, preparation, commit


def _build_and_finalize(
    tmp_path: Path,
) -> tuple[Path, PreparationResult, str, Path]:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    candidate = build_authorization_candidate(
        preparation,
        repo_root=repo,
        code_commit=commit,
    )
    value = _strict_json(candidate)
    digest = value["scope_digest"]
    final_path = repo / "build/foundation/authorizations/final/100k.json"
    finalized = finalize_authorization(
        candidate,
        supplied_scope_digest=digest,
        supplied_approval_phrase=required_approval_phrase(value),
        operator_id="student-operator",
        approved_at=APPROVED_AT,
        output_path=final_path,
    )
    assert finalized == final_path
    return repo, preparation, commit, final_path


def _valid_record() -> dict:
    forecasts = {
        name: {"applicable": False, "value": None, "provenance": None}
        for name in (
            "action_success",
            "expected_error",
            "verifier_outcome",
            "tool_cost",
            "token_cost",
            "latency_cost",
            "retrieval_usefulness",
            "intervention_response",
        )
    }
    forecasts["action_success"] = {
        "applicable": True,
        "value": 1.0,
        "provenance": "observed_outcome",
    }
    return {
        "record_kind": "pneuma_foundation_training_record",
        "record_schema_version": "0.1.0",
        "record_id": "ftr:" + "a" * 64,
        "source": {
            "dataset_family": "swe-gym",
            "lane_id": "swe-gym-openhands-sampled",
            "source_record_id": "source-1",
            "source_revision": None,
            "receipt_hashes": ["b" * 64],
        },
        "disposition": {
            "terminal_role": "train",
            "gradient_eligibility": "first_stage",
            "license_disposition": "local_research_candidate_no_redistribution",
            "privacy_disposition": "redaction_verified",
            "dual_use_disposition": "not_flagged",
            "oracle_disposition": "target_only",
        },
        "identity": {
            "repo": "org/repo",
            "issue_or_pr": "1",
            "task_id": "task-1",
            "base_commit": "c" * 40,
            "patch_sha256": "d" * 64,
            "test_patch_sha256": "e" * 64,
            "fuzzy_text_sha256": "f" * 64,
        },
        "split": {"split_id": "train", "quarantine_id": None},
        "rendered": {"prompt_text": "prompt", "target_text": "target"},
        "tokenization": {
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": "1" * 40,
            "prompt_tokens": 1,
            "target_tokens": 1,
            "total_tokens": 2,
        },
        "training_weight": 0.0,
        "forecast_targets": forecasts,
        "observations": {
            "language": "python",
            "tools": ["pytest"],
            "trajectory_length": 1,
            "labels": {"resolved": True},
        },
    }


def test_exact_authorization_public_contract_exists() -> None:
    assert APPROVAL_PHRASE_PREFIX == "I APPROVE THIS EXACT PNEUMA FOUNDATION SCOPE"
    assert set(VerifiedFoundationAuthorization.__dataclass_fields__) == {
        "model_key",
        "token_ceiling",
        "shard_path",
        "shard_manifest_path",
        "output_root",
        "authorized_lane_weights",
        "scope_digest",
        "manifest",
    }


def test_scope_digest_is_strict_deterministic_json() -> None:
    left = {"b": [2, 1], "a": {"value": 3}}
    right = {"a": {"value": 3}, "b": [2, 1]}
    assert authorization_scope_digest(left) == authorization_scope_digest(right)
    unicode_scope = {"operator": "Pneuma-\u03c0"}
    expected_payload = json.dumps(
        unicode_scope,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert authorization_scope_digest(unicode_scope) == hashlib.sha256(
        expected_payload
    ).hexdigest()
    for invalid in (
        {1: "non-string-key"},
        {"name": object()},
        {"value": math.nan},
        {"value": math.inf},
        {"Name": 1, "name": 2},
    ):
        with pytest.raises(FoundationAuthorizationError, match="JSON|alias|finite|key"):
            authorization_scope_digest(invalid)


def test_candidate_is_exact_non_authorizing_and_cannot_verify(tmp_path: Path) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    path = build_authorization_candidate(
        preparation,
        repo_root=repo,
        code_commit=commit,
    )
    candidate = _strict_json(path)

    assert path == preparation.authorization_candidate_path
    assert candidate["manifest_schema_version"] == "0.2.0"
    assert candidate["authorization_status"] == "candidate"
    assert candidate["operator_approval"] is None
    assert candidate["scope_digest"] == authorization_scope_digest(candidate["scope"])
    assert candidate["scope"]["stage"] == "100k"
    assert candidate["scope"]["token_ceiling"] == 100_000
    assert candidate["scope"]["authorized_lane_weights"] == {
        "swe-gym-openhands-sampled": 1.0
    }
    assert candidate["scope"]["source_data_policy"] == {
        "root": "C:\\pneuma-data",
        "write_allowed": False,
        "private_cloud_transfer": False,
    }
    assert candidate["scope"]["budget"] == {
        "paid_compute_usd": 0,
        "paid_compute_ceiling_usd": 0,
        "cloud_jobs_used": 0,
        "cloud_jobs_ceiling": 0,
        "cloud_lifetime_cap_usd": 45,
    }
    with pytest.raises(FoundationAuthorizationError, match="candidate|not authorized"):
        verify_foundation_authorization(path, repo_root=repo)


def test_artifact_binding_uses_canonical_repo_relative_path(tmp_path: Path) -> None:
    repo, preparation, _commit = _authorization_fixture(tmp_path)
    binding = artifact_binding(preparation.shard_path, repo_root=repo)
    assert binding == {
        "path": preparation.shard_path.relative_to(repo).as_posix(),
        "sha256": hashlib.sha256(preparation.shard_path.read_bytes()).hexdigest(),
        "size": preparation.shard_path.stat().st_size,
    }
    alias = preparation.shard_path.with_name("alias.jsonl")
    try:
        os.link(preparation.shard_path, alias)
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")
    with pytest.raises(FoundationAuthorizationError, match="hard.link|alias"):
        artifact_binding(alias, repo_root=repo)


def test_candidate_build_rejects_dirty_or_different_code_commit(tmp_path: Path) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    with pytest.raises(FoundationAuthorizationError, match="differs|commit"):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit="0" * 40,
        )
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(FoundationAuthorizationError, match="clean"):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


def test_candidate_requires_exact_distinct_preparation_artifact_paths(
    tmp_path: Path,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    aliased = copy.copy(preparation)
    object.__setattr__(
        aliased,
        "license_receipt_path",
        preparation.suite_report_path,
    )
    with pytest.raises(FoundationAuthorizationError, match="exact|distinct|receipt"):
        build_authorization_candidate(
            aliased,
            repo_root=repo,
            code_commit=commit,
        )


def test_exact_final_handshake_verifies_and_applies_one_lane(tmp_path: Path) -> None:
    repo, _preparation, _commit, final_path = _build_and_finalize(tmp_path)
    verified = verify_foundation_authorization(final_path, repo_root=repo)
    assert verified.model_key == "2b"
    assert verified.token_ceiling == 100_000
    assert dict(verified.authorized_lane_weights) == {
        "swe-gym-openhands-sampled": 1.0
    }
    record = _valid_record()
    before = copy.deepcopy(record)
    effective = apply_verified_authorization(record, verified)
    assert effective.record is record
    assert effective.effective_weight == 1.0
    assert record == before


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("supplied_scope_digest", "0" * 64, "digest"),
        ("supplied_approval_phrase", "wrong phrase", "phrase"),
        ("operator_id", " ", "operator"),
        ("approved_at", "2026-07-14T12:00:00+00:00", "UTC|timestamp"),
    ),
)
def test_finalize_rejects_wrong_handshake_inputs(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    candidate_path = build_authorization_candidate(
        preparation,
        repo_root=repo,
        code_commit=commit,
    )
    candidate = _strict_json(candidate_path)
    arguments = {
        "supplied_scope_digest": candidate["scope_digest"],
        "supplied_approval_phrase": required_approval_phrase(candidate),
        "operator_id": "student-operator",
        "approved_at": APPROVED_AT,
    }
    arguments[field] = value
    final_path = repo / "build/foundation/authorizations/final/100k.json"
    with pytest.raises(FoundationAuthorizationError, match=message):
        finalize_authorization(candidate_path, output_path=final_path, **arguments)
    assert not final_path.exists()


def test_finalize_rejects_duplicate_and_nonfinite_candidate_json(tmp_path: Path) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    candidate_path = build_authorization_candidate(
        preparation,
        repo_root=repo,
        code_commit=commit,
    )
    payload = candidate_path.read_text(encoding="utf-8")
    candidate_path.write_text(
        payload.replace(
            '"authorization_status": "candidate",',
            '"authorization_status": "candidate",\n'
            '    "authorization_status": "candidate",',
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(FoundationAuthorizationError, match="duplicate"):
        finalize_authorization(
            candidate_path,
            supplied_scope_digest="0" * 64,
            supplied_approval_phrase="wrong",
            operator_id="operator",
            approved_at=APPROVED_AT,
            output_path=repo / "build/foundation/authorizations/final/100k.json",
        )
    candidate_path.write_text(payload.replace("100000", "NaN", 1), encoding="utf-8")
    with pytest.raises(FoundationAuthorizationError, match="finite|constant|JSON"):
        finalize_authorization(
            candidate_path,
            supplied_scope_digest="0" * 64,
            supplied_approval_phrase="wrong",
            operator_id="operator",
            approved_at=APPROVED_AT,
            output_path=repo / "build/foundation/authorizations/final/100k.json",
        )


def test_candidate_publication_rolls_back_when_a_bound_source_mutates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import artifacts

    repo, preparation, commit = _authorization_fixture(tmp_path)
    candidate_path = build_authorization_candidate(
        preparation,
        repo_root=repo,
        code_commit=commit,
    )
    original_candidate = candidate_path.read_bytes()
    original_revalidate = artifacts.BoundArtifactReadHandle.revalidate
    mutated = False

    def mutate_then_revalidate(handle, expected):
        nonlocal mutated
        if not mutated and handle._publication.directory == preparation.shard_path.parent:
            mutated = True
            metadata = preparation.shard_path.stat()
            with preparation.shard_path.open("r+b") as stream:
                stream.write(b"X" * metadata.st_size)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.utime(
                    preparation.shard_path,
                    ns=(metadata.st_atime_ns, metadata.st_mtime_ns),
                )
            except OSError:
                pass
        return original_revalidate(handle, expected)

    monkeypatch.setattr(
        artifacts.BoundArtifactReadHandle,
        "revalidate",
        mutate_then_revalidate,
    )
    with pytest.raises(FoundationAuthorizationError, match="changed|metadata|digest|publication"):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )
    assert mutated is True
    assert candidate_path.read_bytes() == original_candidate


def test_final_publication_rolls_back_when_candidate_mutates_in_place(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import artifacts

    repo, preparation, commit = _authorization_fixture(tmp_path)
    candidate_path = build_authorization_candidate(
        preparation,
        repo_root=repo,
        code_commit=commit,
    )
    candidate = _strict_json(candidate_path)
    final_path = repo / "build/foundation/authorizations/final/100k.json"
    final_path.parent.mkdir(parents=True)
    final_path.write_bytes(b"previous-final")
    original_revalidate = artifacts.BoundArtifactReadHandle.revalidate
    mutated = False

    def mutate_then_revalidate(handle, expected):
        nonlocal mutated
        if not mutated and handle._publication.directory == candidate_path.parent:
            mutated = True
            metadata = candidate_path.stat()
            with candidate_path.open("r+b") as stream:
                stream.write(b"X" * metadata.st_size)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.utime(candidate_path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            except OSError:
                pass
        return original_revalidate(handle, expected)

    monkeypatch.setattr(
        artifacts.BoundArtifactReadHandle,
        "revalidate",
        mutate_then_revalidate,
    )
    with pytest.raises(FoundationAuthorizationError, match="changed|metadata|digest|publication"):
        finalize_authorization(
            candidate_path,
            supplied_scope_digest=candidate["scope_digest"],
            supplied_approval_phrase=required_approval_phrase(candidate),
            operator_id="operator",
            approved_at=APPROVED_AT,
            output_path=final_path,
        )
    assert mutated is True
    assert final_path.read_bytes() == b"previous-final"


def test_verify_rejects_artifact_tamper_and_dirty_or_different_commit(
    tmp_path: Path,
) -> None:
    repo, _preparation, _commit, final_path = _build_and_finalize(tmp_path)
    manifest = _strict_json(final_path)
    for binding in manifest["scope"]["artifacts"].values():
        path = repo / binding["path"]
        original = path.read_bytes()
        path.write_bytes(b"X" * len(original))
        with pytest.raises(
            FoundationAuthorizationError,
            match="artifact|digest|changed|JSON|binding",
        ):
            verify_foundation_authorization(final_path, repo_root=repo)
        path.write_bytes(original)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(FoundationAuthorizationError, match="clean|commit"):
        verify_foundation_authorization(final_path, repo_root=repo)


def test_verify_rejects_bound_artifact_hardlink_alias(tmp_path: Path) -> None:
    repo, preparation, _commit, final_path = _build_and_finalize(tmp_path)
    alias = preparation.shard_path.with_name("shard-alias.jsonl")
    try:
        os.link(preparation.shard_path, alias)
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")
    with pytest.raises(FoundationAuthorizationError, match="hard.link|alias|binding"):
        verify_foundation_authorization(final_path, repo_root=repo)


def test_verify_rejects_in_place_final_manifest_mutation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import artifacts

    repo, _preparation, _commit, final_path = _build_and_finalize(tmp_path)
    original_revalidate = artifacts.BoundArtifactReadHandle.revalidate
    mutated = False

    def mutate_then_revalidate(handle, expected):
        nonlocal mutated
        if not mutated and handle._publication.directory == final_path.parent:
            mutated = True
            metadata = final_path.stat()
            with final_path.open("r+b") as stream:
                stream.write(b"X" * metadata.st_size)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.utime(final_path, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
            except OSError:
                pass
        return original_revalidate(handle, expected)

    monkeypatch.setattr(
        artifacts.BoundArtifactReadHandle,
        "revalidate",
        mutate_then_revalidate,
    )
    with pytest.raises(FoundationAuthorizationError, match="changed|metadata|digest|binding"):
        verify_foundation_authorization(final_path, repo_root=repo)
    assert mutated is True


@pytest.mark.parametrize(
    "mutation",
    (
        lambda scope: scope["model"].update(revision="0" * 40),
        lambda scope: scope.update(stage="500k"),
        lambda scope: scope.update(token_ceiling=500_000),
        lambda scope: scope.update(local_profile="cloud"),
        lambda scope: scope["authorized_lane_weights"].update(
            {"swe-gym-openhands-verifier": 1.0}
        ),
        lambda scope: scope["source_data_policy"].update(write_allowed=True),
        lambda scope: scope["source_data_policy"].update(private_cloud_transfer=True),
        lambda scope: scope["budget"].update(paid_compute_usd=1),
        lambda scope: scope["budget"].update(cloud_jobs_used=1),
        lambda scope: scope.update(output_root="build/other/"),
    ),
)
def test_verify_rejects_semantically_invalid_authorized_scope(
    tmp_path: Path,
    mutation,
) -> None:
    repo, _preparation, _commit, final_path = _build_and_finalize(tmp_path)
    manifest = _strict_json(final_path)
    mutation(manifest["scope"])
    manifest["scope_digest"] = authorization_scope_digest(manifest["scope"])
    manifest["operator_approval"]["scope_digest"] = manifest["scope_digest"]
    phrase = APPROVAL_PHRASE_PREFIX + " " + manifest["scope_digest"]
    manifest["operator_approval"]["approval_phrase_sha256"] = hashlib.sha256(
        phrase.encode("utf-8")
    ).hexdigest()
    _write_json(final_path, manifest)
    with pytest.raises(FoundationAuthorizationError):
        verify_foundation_authorization(final_path, repo_root=repo)


@pytest.mark.parametrize("weight", (1.0, -1.0, -0.0, math.nan))
def test_apply_rejects_noncanonical_persisted_weights(
    tmp_path: Path,
    weight: float,
) -> None:
    repo, _preparation, _commit, final_path = _build_and_finalize(tmp_path)
    verified = verify_foundation_authorization(final_path, repo_root=repo)
    record = _valid_record()
    record["training_weight"] = weight
    with pytest.raises(FoundationAuthorizationError, match="weight"):
        apply_verified_authorization(record, verified)


def test_apply_permission_cannot_leak_to_sibling_or_targetless_record(
    tmp_path: Path,
) -> None:
    repo, _preparation, _commit, final_path = _build_and_finalize(tmp_path)
    verified = verify_foundation_authorization(final_path, repo_root=repo)
    sibling = _valid_record()
    sibling["source"]["lane_id"] = "swe-gym-openhands-verifier"
    with pytest.raises(FoundationAuthorizationError, match="lane"):
        apply_verified_authorization(sibling, verified)
    targetless = _valid_record()
    targetless["rendered"]["target_text"] = ""
    with pytest.raises(FoundationAuthorizationError, match="target"):
        apply_verified_authorization(targetless, verified)
    forecastless = _valid_record()
    for target in forecastless["forecast_targets"].values():
        target.update(applicable=False, value=None, provenance=None)
    with pytest.raises(FoundationAuthorizationError, match="forecast"):
        apply_verified_authorization(forecastless, verified)


def test_candidate_and_final_outputs_cannot_escape_expected_build_paths(
    tmp_path: Path,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    escaped = copy.copy(preparation)
    object.__setattr__(escaped, "authorization_candidate_path", tmp_path / "candidate.json")
    with pytest.raises(FoundationAuthorizationError, match="candidate|build|path"):
        build_authorization_candidate(escaped, repo_root=repo, code_commit=commit)
    candidate_path = build_authorization_candidate(
        preparation,
        repo_root=repo,
        code_commit=commit,
    )
    candidate = _strict_json(candidate_path)
    with pytest.raises(FoundationAuthorizationError, match="final|build|path"):
        finalize_authorization(
            candidate_path,
            supplied_scope_digest=candidate["scope_digest"],
            supplied_approval_phrase=required_approval_phrase(candidate),
            operator_id="operator",
            approved_at=APPROVED_AT,
            output_path=tmp_path / "final.json",
        )


def test_committed_pending_authorization_refuses_training() -> None:
    with pytest.raises(FoundationAuthorizationError, match="not authorized"):
        verify_foundation_authorization(
            ROOT / "docs/data/training-authorizations/pneuma-foundation-v0.pending.json",
            repo_root=ROOT,
        )


def test_authorization_module_does_not_import_preparation_or_legacy_scorer() -> None:
    source = (ROOT / "src/pneuma_lab/foundation/authorization.py").read_text(
        encoding="utf-8"
    )
    assert "foundation.preparation" not in source
    assert "legacy" not in source.casefold()
    assert "evals" not in source
    assert source.count("hmac.compare_digest") >= 6
