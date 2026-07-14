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
from pneuma_lab.foundation.data import (
    ACTIVE_DATASET_GROUPS,
    build_diversity_inventory,
)
from pneuma_lab.foundation.preparation import PreparationResult
from pneuma_lab.foundation.specs import MODEL_SPECS


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
    path.write_bytes(_pretty_json_bytes(value))


def _pretty_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=4, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


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
    spec = MODEL_SPECS["2b"]
    tokenizer_receipt_sha256 = "1" * 64
    tokenizer_snapshot_sha256 = "2" * 64
    generated_conversion = {
        "examples.jsonl": "3" * 64,
        "invalid_examples.jsonl": "4" * 64,
        "conversion_report.json": "5" * 64,
        "hash_manifest.json": "6" * 64,
    }
    license_receipt = {
        "receipt_kind": "dataset_license_posture",
        "receipt_schema_version": "0.1.0",
        "dataset_id": "swe-gym-openhands-sampled",
        "decision": "local_research_candidate_no_redistribution",
        "cloud_redistribution_allowed": False,
        "requires_exact_operator_authorization": True,
    }
    source_receipt_hashes = tuple(
        sorted(
            (
                hashlib.sha256(_pretty_json_bytes(license_receipt)).hexdigest(),
                tokenizer_receipt_sha256,
                tokenizer_snapshot_sha256,
                generated_conversion["conversion_report.json"],
                generated_conversion["hash_manifest.json"],
            )
        )
    )
    record = _valid_record()
    record["source"]["receipt_hashes"] = list(source_receipt_hashes)
    record["tokenization"]["tokenizer_revision"] = spec.revision
    shard_payload = (
        json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    shard_sha256 = hashlib.sha256(shard_payload).hexdigest()
    shard = output / f"shards/{shard_sha256}.jsonl"
    shard.parent.mkdir(parents=True)
    shard.write_bytes(shard_payload)
    inventory = build_diversity_inventory((record,))
    shard_manifest = output / f"shards/{shard_sha256}.manifest.json"
    _write_json(
        shard_manifest,
        {
            "manifest_kind": "pneuma_foundation_shard",
            "schema_version": "0.1.0",
            "sha256": shard_sha256,
            "example_count": 1,
            "duplicate_example_ids": [],
            "inventory": inventory,
            "source_policy": "read_only_external_corpus",
            "token_ceiling": 100_000,
        },
    )
    all_ten = {
        "complete": True,
        "families": list(ACTIVE_DATASET_GROUPS),
        "lanes": ["swe-gym-openhands-sampled"],
    }
    tokenizer_snapshot = {
        "model_id": spec.model_id,
        "revision": spec.revision,
        "receipt_sha256": tokenizer_receipt_sha256,
        "snapshot_sha256": tokenizer_snapshot_sha256,
    }
    receipts = {
        "suite_report.json": {
            "manifest_kind": "pneuma_foundation_suite_report",
            "manifest_schema_version": "0.1.0",
            "first_stage": {
                "stage": "100k",
                "authorized_lane_candidates": [
                    "swe-gym-openhands-sampled"
                ],
            },
            "families": [
                {"family": family, "exists": True}
                for family in ACTIVE_DATASET_GROUPS
            ],
        },
        "license_receipt.json": license_receipt,
        "source_presence_receipt.json": {
            "manifest_kind": "pneuma_foundation_source_presence_receipt",
            "manifest_schema_version": "0.1.0",
            "all_ten_present": True,
            "before": all_ten,
            "after": all_ten,
            "families": list(ACTIVE_DATASET_GROUPS),
            "lanes": ["swe-gym-openhands-sampled"],
        },
        "source_integrity_receipt.json": {
            "manifest_kind": "pneuma_foundation_source_integrity_receipt",
            "manifest_schema_version": "0.1.0",
            "before": [],
            "after": [],
            "all_ten_before": all_ten,
            "all_ten_after": all_ten,
            "tokenizer_snapshot": tokenizer_snapshot,
            "unchanged": True,
        },
        "split_receipt.json": {
            "manifest_kind": "pneuma_foundation_repo_grouped_split_receipt",
            "manifest_schema_version": "0.1.0",
            "assignments": [
                {
                    "record_id": record["record_id"],
                    "split_id": "train",
                    "canonical_repo": "org/repo",
                }
            ],
            "canonical_repository_sets": {
                "train": ["org/repo"],
                "validation": [],
                "held_out": [],
            },
            "repository_grouped": True,
        },
        "contamination_receipt.json": {
            "manifest_kind": "pneuma_foundation_contamination_receipt",
            "manifest_schema_version": "0.1.0",
            "training_identity_count": 1,
            "evaluation_identity_count": 3,
            "required_evaluation_families": [
                "swe-bench",
                "swe-mera",
                "swe-polybench",
            ],
            "evaluation_coverage_complete": True,
            "finding_count": 0,
            "findings": [],
            "repo_issue_disjoint": True,
        },
        "diversity_receipt.json": {
            "manifest_kind": "pneuma_foundation_diversity_receipt",
            "manifest_schema_version": "0.1.0",
            **inventory,
        },
        "selection_receipt.json": {
            "manifest_kind": "pneuma_foundation_selection_receipt",
            "manifest_schema_version": "0.1.0",
            "stage": "100k",
            "seed": 20260713,
            "token_ceiling": 100_000,
            "candidate_record_count": 1,
            "selected_record_count": 1,
            "selected_record_ids": [record["record_id"]],
            "selected_token_count": 2,
            "tokenizer_recount_total": 2,
            "resolved_count": 1,
            "unresolved_count": 0,
            "persisted_training_weight": 0.0,
        },
    }
    for name, value in receipts.items():
        _write_json(output / name, value)
    _write_json(
        output / "preparation_manifest.json",
        {
            "manifest_kind": "pneuma_foundation_preparation_manifest",
            "manifest_schema_version": "0.1.0",
            "stage": "100k",
            "token_ceiling": 100_000,
            "seed": 20260713,
            "dry_run": False,
            "dataset_suite": "all_ten_governed_groups",
            "gradient_lane": "swe-gym-openhands-sampled",
            "training_authorized": False,
            "persisted_training_weight": 0.0,
            "source_receipt_hashes": list(source_receipt_hashes),
            "tokenizer_snapshot": tokenizer_snapshot,
            "generated_artifact_sha256": {
                "conversion": generated_conversion,
                "eval_identities": {
                    "swe-bench": "7" * 64,
                    "swe-mera": "8" * 64,
                    "swe-polybench": "9" * 64,
                },
            },
            "receipt_sha256": {
                name: hashlib.sha256(_pretty_json_bytes(value)).hexdigest()
                for name, value in sorted(receipts.items())
            },
            "shard": {
                "artifact": shard.name,
                "sha256": shard_sha256,
                "example_count": 1,
                "manifest_artifact": shard_manifest.name,
            },
            "gates": {
                "all_ten_present": True,
                "eval_coverage_complete": True,
                "contamination_findings": 0,
                "source_unchanged": True,
                "tokenizer_recount_matches": True,
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


def _refresh_preparation_receipt_digest(
    preparation: PreparationResult,
    receipt_path: Path,
) -> None:
    manifest = _strict_json(preparation.preparation_manifest_path)
    manifest["receipt_sha256"][receipt_path.name] = hashlib.sha256(
        receipt_path.read_bytes()
    ).hexdigest()
    _write_json(preparation.preparation_manifest_path, manifest)


def _resign_final_scope(final_path: Path, repo: Path) -> None:
    manifest = _strict_json(final_path)
    for binding in manifest["scope"]["artifacts"].values():
        artifact = repo / binding["path"]
        binding["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        binding["size"] = artifact.stat().st_size
    manifest["scope_digest"] = authorization_scope_digest(manifest["scope"])
    manifest["operator_approval"]["scope_digest"] = manifest["scope_digest"]
    phrase = APPROVAL_PHRASE_PREFIX + " " + manifest["scope_digest"]
    manifest["operator_approval"]["approval_phrase_sha256"] = hashlib.sha256(
        phrase.encode("utf-8")
    ).hexdigest()
    _write_json(final_path, manifest)


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


def test_candidate_rejects_4b_scope_over_2b_preparation(tmp_path: Path) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    with pytest.raises(
        FoundationAuthorizationError,
        match="2b|4b|model|tokenizer|coher",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
            model_key="4b",
        )
    assert not preparation.authorization_candidate_path.exists()


@pytest.mark.parametrize(
    "contradiction",
    (
        "prep_ceiling",
        "prep_gradient_lane",
        "prep_training_authorized",
        "prep_negative_zero_weight",
        "prep_gate_false",
        "prep_shard_sha",
        "prep_receipt_sha",
        "shard_manifest_sha",
        "shard_manifest_count",
        "contamination_gate",
        "suite_presence",
        "source_presence",
        "source_unchanged",
        "selection_count",
        "diversity_inventory",
        "split_grouping",
        "license_cloud",
    ),
)
def test_candidate_rejects_cross_artifact_contradictions(
    tmp_path: Path,
    contradiction: str,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    prep = _strict_json(preparation.preparation_manifest_path)
    if contradiction == "prep_ceiling":
        prep["token_ceiling"] = 500_000
        _write_json(preparation.preparation_manifest_path, prep)
    elif contradiction == "prep_gradient_lane":
        prep["gradient_lane"] = "swe-gym-openhands-verifier"
        _write_json(preparation.preparation_manifest_path, prep)
    elif contradiction == "prep_training_authorized":
        prep["training_authorized"] = True
        _write_json(preparation.preparation_manifest_path, prep)
    elif contradiction == "prep_negative_zero_weight":
        prep["persisted_training_weight"] = -0.0
        _write_json(preparation.preparation_manifest_path, prep)
    elif contradiction == "prep_gate_false":
        prep["gates"]["contamination_findings"] = 1
        _write_json(preparation.preparation_manifest_path, prep)
    elif contradiction == "prep_shard_sha":
        prep["shard"]["sha256"] = "0" * 64
        _write_json(preparation.preparation_manifest_path, prep)
    elif contradiction == "prep_receipt_sha":
        prep["receipt_sha256"]["suite_report.json"] = "0" * 64
        _write_json(preparation.preparation_manifest_path, prep)
    elif contradiction in {"shard_manifest_sha", "shard_manifest_count"}:
        manifest = _strict_json(preparation.shard_manifest_path)
        if contradiction == "shard_manifest_sha":
            manifest["sha256"] = "0" * 64
        else:
            manifest["example_count"] = 2
        _write_json(preparation.shard_manifest_path, manifest)
    else:
        paths = {
            "contamination_gate": preparation.contamination_receipt_path,
            "suite_presence": preparation.suite_report_path,
            "source_presence": preparation.source_presence_receipt_path,
            "source_unchanged": preparation.source_integrity_receipt_path,
            "selection_count": preparation.selection_receipt_path,
            "diversity_inventory": preparation.diversity_receipt_path,
            "split_grouping": preparation.split_receipt_path,
            "license_cloud": preparation.license_receipt_path,
        }
        receipt_path = paths[contradiction]
        receipt = _strict_json(receipt_path)
        if contradiction == "contamination_gate":
            receipt.update(finding_count=1, repo_issue_disjoint=False)
            receipt["findings"] = [{"fixture": "contradiction"}]
        elif contradiction == "suite_presence":
            receipt["families"][0]["exists"] = False
        elif contradiction == "source_presence":
            receipt["all_ten_present"] = False
        elif contradiction == "source_unchanged":
            receipt["unchanged"] = False
        elif contradiction == "selection_count":
            receipt["selected_record_count"] = 2
        elif contradiction == "diversity_inventory":
            receipt["token_count"] += 1
        elif contradiction == "split_grouping":
            receipt["repository_grouped"] = False
        elif contradiction == "license_cloud":
            receipt["cloud_redistribution_allowed"] = True
        _write_json(receipt_path, receipt)
        _refresh_preparation_receipt_digest(preparation, receipt_path)
    with pytest.raises(
        FoundationAuthorizationError,
        match=(
            "coher|shard|receipt|gate|suite|source|selection|diversity|"
            "split|license|preparation|weight|token|lane|model"
        ),
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )
    assert not preparation.authorization_candidate_path.exists()


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


def test_verify_rejects_rehashed_but_incoherent_receipt_set(tmp_path: Path) -> None:
    repo, preparation, _commit, final_path = _build_and_finalize(tmp_path)
    contamination = _strict_json(preparation.contamination_receipt_path)
    contamination.update(finding_count=1, repo_issue_disjoint=False)
    contamination["findings"] = [{"fixture": "contradiction"}]
    _write_json(preparation.contamination_receipt_path, contamination)
    _refresh_preparation_receipt_digest(
        preparation,
        preparation.contamination_receipt_path,
    )
    _resign_final_scope(final_path, repo)

    with pytest.raises(FoundationAuthorizationError, match="coher|contamination|gate"):
        verify_foundation_authorization(final_path, repo_root=repo)


def test_verify_rejects_rehashed_4b_scope_over_2b_preparation(
    tmp_path: Path,
) -> None:
    repo, _preparation, _commit, final_path = _build_and_finalize(tmp_path)
    manifest = _strict_json(final_path)
    spec = MODEL_SPECS["4b"]
    manifest["scope"]["model"] = {
        "key": spec.key,
        "model_id": spec.model_id,
        "revision": spec.revision,
        "tokenizer_id": spec.model_id,
        "tokenizer_revision": spec.revision,
    }
    _write_json(final_path, manifest)
    _resign_final_scope(final_path, repo)

    with pytest.raises(FoundationAuthorizationError, match="2b|4b|model|tokenizer|coher"):
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
    assert "legacy" not in source.casefold()
    assert "evals" not in source
    assert source.count("hmac.compare_digest") >= 6
    assert "from typing import TYPE_CHECKING" in source
    assert "if TYPE_CHECKING:" in source
    assert "from pneuma_lab.foundation.preparation import PreparationResult" in source
    assert "preparation: PreparationResult" in source
