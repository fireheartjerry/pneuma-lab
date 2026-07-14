"""Exact, hash-bound foundation authorization handshake tests."""

from __future__ import annotations

from collections.abc import Mapping
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from types import MappingProxyType

import pytest

from pneuma_lab.converters import openhands_sampled_training as openhands_converter
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
from pneuma_lab.foundation.records import (
    GradientEligibility,
    LaneDisposition,
    TerminalRole,
    render_foundation_record,
)
from pneuma_lab.foundation.specs import MODEL_SPECS


ROOT = Path(__file__).resolve().parents[1]
APPROVED_AT = "2026-07-14T12:00:00Z"


class ByteTokenizer:
    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        assert add_special_tokens is False
        return list(text.encode("utf-8"))


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


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
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
    conversion_root = output / "conversion"
    conversion_root.mkdir(parents=True)
    trace_path = (
        ROOT / "fixtures/adapters/openhands_sampled/golden/pneuma_traces.jsonl"
    )
    adapter_report_path = trace_path.parent / "adapter_report.json"
    traces = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
    ]
    adapter_report = json.loads(adapter_report_path.read_text(encoding="utf-8"))
    conversion_examples = openhands_converter.convert_traces(
        traces,
        adapter_report_ref="verified-stream:adapter_report.json",
        manifest_ref="full/hash_manifest.json",
    )
    openhands_converter.validate_training_examples(conversion_examples)
    examples_payload = b"".join(
        _canonical_json_bytes(example) for example in conversion_examples
    )
    invalid_payload = b""
    conversion_report = openhands_converter.build_conversion_report(
        mode=openhands_converter.FULL_MODE,
        input_path="verified-stream:pneuma_traces.jsonl",
        adapter_report_path="verified-stream:adapter_report.json",
        adapter_report=adapter_report,
        limit=None,
        traces_read=len(traces),
        agent_steps=sum(
            int(trace["trajectory"]["num_agent_steps"]) for trace in traces
        ),
        examples=conversion_examples,
        invalid_records=[],
        output_hashes={
            "examples_jsonl_sha256": hashlib.sha256(examples_payload).hexdigest(),
            "invalid_examples_jsonl_sha256": hashlib.sha256(
                invalid_payload
            ).hexdigest(),
        },
    )
    conversion_report["converter"]["git_sha"] = commit
    assert conversion_report["count_reconciliation"]["reconciled"] is True
    conversion_report_payload = _canonical_json_bytes(conversion_report)
    hash_manifest = openhands_converter.build_hash_manifest(
        mode=openhands_converter.FULL_MODE,
        examples_text=examples_payload.decode("utf-8"),
        invalid_text="",
        report_text=conversion_report_payload.decode("utf-8"),
        limit=None,
        input_path="verified-stream:pneuma_traces.jsonl",
        adapter_report_path="verified-stream:adapter_report.json",
    )
    hash_manifest["hashes"]["hash_manifest_json_sha256"] = hashlib.sha256(
        _canonical_json_bytes(hash_manifest)
    ).hexdigest()
    conversion_files = {
        "examples": (conversion_root / "examples.jsonl", examples_payload),
        "invalid_examples": (
            conversion_root / "invalid_examples.jsonl",
            invalid_payload,
        ),
        "conversion_report": (
            conversion_root / "conversion_report.json",
            conversion_report_payload,
        ),
        "hash_manifest": (
            conversion_root / "hash_manifest.json",
            _canonical_json_bytes(hash_manifest),
        ),
    }
    for path, payload in conversion_files.values():
        path.write_bytes(payload)
    generated_conversion = {
        name: {
            "path": path.relative_to(repo).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        }
        for name, (path, payload) in conversion_files.items()
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
                generated_conversion["conversion_report"]["sha256"],
                generated_conversion["hash_manifest"]["sha256"],
            )
        )
    )
    lane_disposition = LaneDisposition(
        terminal_role=TerminalRole.TRAIN,
        gradient_eligibility=GradientEligibility.FIRST_STAGE,
        license_disposition="local_research_candidate_no_redistribution",
        privacy_disposition="redaction_verified",
        dual_use_disposition="not_flagged",
        oracle_disposition="target_only",
    )
    selected_example = conversion_examples[0]
    record = render_foundation_record(
        selected_example,
        lane_disposition=lane_disposition,
        split_assignment={"split_id": "train", "quarantine_id": None},
        tokenizer=ByteTokenizer(),
        tokenizer_revision=spec.revision,
        source_receipt_hashes=source_receipt_hashes,
    )
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
    suite_policy = json.loads(
        (
            ROOT
            / "docs/data/training-readiness/"
            "pneuma-foundation-v0-suite.json"
        ).read_text(encoding="utf-8")
    )
    eval_root = output / "eval-identities"
    eval_root.mkdir(parents=True)
    eval_rows = {
        "swe-bench": {
            "source_id": "eval-bench-101",
            "repo": "eval/bench",
            "base_commit": "1" * 40,
        },
        "swe-mera": {
            "source_id": "eval-mera-102",
            "repo": "eval/mera",
            "base_commit": "2" * 40,
        },
        "swe-polybench": {
            "source_id": "eval-poly-103",
            "repo": "eval/poly",
            "base_commit": "3" * 40,
        },
    }
    eval_files = {}
    for family, row in eval_rows.items():
        path = eval_root / f"{family}.jsonl"
        payload = _canonical_json_bytes(row)
        path.write_bytes(payload)
        eval_files[family] = (path, payload)
    generated_eval = {
        family: {
            "path": path.relative_to(repo).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size": len(payload),
        }
        for family, (path, payload) in eval_files.items()
    }
    source_payloads = {
        "processed/swe-gym/openhands-sampled/pneuma_traces.jsonl": (
            trace_path.read_bytes()
        ),
        "processed/swe-gym/openhands-sampled/adapter_report.json": (
            adapter_report_path.read_bytes()
        ),
        **{
            f"processed/{family}/normalized_metadata.jsonl": payload
            for family, (_path, payload) in eval_files.items()
        },
    }
    source_snapshots = [
        {
            "relative_path": relative_path,
            "size": len(payload),
            "mtime_ns": index,
            "device": 1,
            "inode": index,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        for index, (relative_path, payload) in enumerate(
            sorted(source_payloads.items()),
            start=1,
        )
    ]
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
            "evaluation_identity": copy.deepcopy(
                suite_policy["evaluation_identity"]
            ),
            "families": [
                {
                    **copy.deepcopy(item),
                    "exists": True,
                }
                for item in suite_policy["families"]
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
            "before": source_snapshots,
            "after": copy.deepcopy(source_snapshots),
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
                    "record_source_id": example["example_id"],
                    "repo": example["split_group"]["repo"],
                    "split_id": "train",
                    "canonical_repo": example["split_group"]["repo"].casefold(),
                    "quarantine_id": None,
                }
                for example in conversion_examples
            ],
            "canonical_repository_sets": {
                "train": ["demo/alpha", "demo/beta"],
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
            "evaluation_family_counts": {
                "swe-bench": 1,
                "swe-mera": 1,
                "swe-polybench": 1,
            },
            "blocked_evaluation_family_status": {
                "swe-bench-pro": "blocked_unavailable",
            },
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
            "candidate_record_count": len(conversion_examples),
            "selected_record_count": 1,
            "selected_record_ids": [record["record_id"]],
            "selected_token_count": record["tokenization"]["total_tokens"],
            "tokenizer_recount_total": record["tokenization"]["total_tokens"],
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
                "eval_identities": generated_eval,
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
        conversion_examples_path=conversion_files["examples"][0],
        conversion_invalid_examples_path=conversion_files[
            "invalid_examples"
        ][0],
        conversion_report_path=conversion_files["conversion_report"][0],
        conversion_hash_manifest_path=conversion_files["hash_manifest"][0],
        eval_identity_paths={
            family: value[0] for family, value in eval_files.items()
        },
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


def _refresh_derived_preparation(
    preparation: PreparationResult,
    *,
    repair_hash_manifest: bool = True,
    recompute_record_ids: bool = True,
) -> None:
    if repair_hash_manifest:
        hash_manifest = _strict_json(preparation.conversion_hash_manifest_path)
        hash_manifest["hashes"].update(
            examples_jsonl_sha256=hashlib.sha256(
                preparation.conversion_examples_path.read_bytes()
            ).hexdigest(),
            invalid_examples_jsonl_sha256=hashlib.sha256(
                preparation.conversion_invalid_examples_path.read_bytes()
            ).hexdigest(),
            conversion_report_json_sha256=hashlib.sha256(
                preparation.conversion_report_path.read_bytes()
            ).hexdigest(),
            hash_manifest_json_sha256=None,
        )
        hash_manifest["hashes"]["hash_manifest_json_sha256"] = hashlib.sha256(
            _canonical_json_bytes(hash_manifest)
        ).hexdigest()
        preparation.conversion_hash_manifest_path.write_bytes(
            _canonical_json_bytes(hash_manifest)
        )

    manifest = _strict_json(preparation.preparation_manifest_path)
    source_receipt_hashes = sorted(
        {
            hashlib.sha256(preparation.license_receipt_path.read_bytes()).hexdigest(),
            manifest["tokenizer_snapshot"]["receipt_sha256"],
            manifest["tokenizer_snapshot"]["snapshot_sha256"],
            hashlib.sha256(preparation.conversion_report_path.read_bytes()).hexdigest(),
            hashlib.sha256(
                preparation.conversion_hash_manifest_path.read_bytes()
            ).hexdigest(),
        }
    )
    records = [
        json.loads(line)
        for line in preparation.shard_path.read_text(encoding="utf-8").splitlines()
    ]
    for record in records:
        record["source"]["receipt_hashes"] = source_receipt_hashes
        if recompute_record_ids:
            record["record_id"] = "ftr:" + hashlib.sha256(
                json.dumps(record["source"], sort_keys=True).encode("utf-8")
            ).hexdigest()
    shard_payload = b"".join(_canonical_json_bytes(record) for record in records)
    shard_sha256 = hashlib.sha256(shard_payload).hexdigest()
    shard_root = preparation.preparation_manifest_path.parent / "shards"
    new_shard = shard_root / f"{shard_sha256}.jsonl"
    new_shard.write_bytes(shard_payload)
    old_shard_manifest = _strict_json(preparation.shard_manifest_path)
    old_shard_manifest.update(
        sha256=shard_sha256,
        example_count=len(records),
        inventory=build_diversity_inventory(records),
    )
    new_shard_manifest = shard_root / f"{shard_sha256}.manifest.json"
    _write_json(new_shard_manifest, old_shard_manifest)
    object.__setattr__(preparation, "shard_path", new_shard)
    object.__setattr__(
        preparation,
        "shard_manifest_path",
        new_shard_manifest,
    )

    selection = _strict_json(preparation.selection_receipt_path)
    selection.update(
        selected_record_count=len(records),
        selected_record_ids=[record["record_id"] for record in records],
        selected_token_count=sum(
            record["tokenization"]["total_tokens"] for record in records
        ),
        tokenizer_recount_total=sum(
            record["tokenization"]["total_tokens"] for record in records
        ),
        resolved_count=sum(
            record["observations"]["labels"]["resolved"] is True
            for record in records
        ),
        unresolved_count=sum(
            record["observations"]["labels"]["resolved"] is False
            for record in records
        ),
    )
    _write_json(preparation.selection_receipt_path, selection)
    diversity = {
        "manifest_kind": "pneuma_foundation_diversity_receipt",
        "manifest_schema_version": "0.1.0",
        **build_diversity_inventory(records),
    }
    _write_json(preparation.diversity_receipt_path, diversity)

    conversion_paths = {
        "examples": preparation.conversion_examples_path,
        "invalid_examples": preparation.conversion_invalid_examples_path,
        "conversion_report": preparation.conversion_report_path,
        "hash_manifest": preparation.conversion_hash_manifest_path,
    }
    manifest["source_receipt_hashes"] = source_receipt_hashes
    manifest["generated_artifact_sha256"]["conversion"] = {
        name: {
            "path": path.relative_to(
                preparation.preparation_manifest_path.parents[4]
            ).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": path.stat().st_size,
        }
        for name, path in conversion_paths.items()
    }
    manifest["shard"].update(
        artifact=new_shard.name,
        sha256=shard_sha256,
        example_count=len(records),
        manifest_artifact=new_shard_manifest.name,
    )
    receipt_paths = {
        "suite_report.json": preparation.suite_report_path,
        "license_receipt.json": preparation.license_receipt_path,
        "source_presence_receipt.json": preparation.source_presence_receipt_path,
        "source_integrity_receipt.json": preparation.source_integrity_receipt_path,
        "split_receipt.json": preparation.split_receipt_path,
        "contamination_receipt.json": preparation.contamination_receipt_path,
        "diversity_receipt.json": preparation.diversity_receipt_path,
        "selection_receipt.json": preparation.selection_receipt_path,
    }
    manifest["receipt_sha256"] = {
        name: hashlib.sha256(path.read_bytes()).hexdigest()
        for name, path in receipt_paths.items()
    }
    _write_json(preparation.preparation_manifest_path, manifest)


def _resign_final_scope(final_path: Path, repo: Path) -> None:
    manifest = _strict_json(final_path)
    bindings = [*manifest["scope"]["artifacts"].values()]
    for group in manifest["scope"]["evidence_artifacts"].values():
        bindings.extend(group.values())
    for binding in bindings:
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
        "authorized_record_membership",
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
    assert set(candidate["scope"]["evidence_artifacts"]["conversion"]) == {
        "examples",
        "invalid_examples",
        "conversion_report",
        "hash_manifest",
    }
    assert set(candidate["scope"]["evidence_artifacts"]["eval_identities"]) == {
        "swe-bench",
        "swe-mera",
        "swe-polybench",
    }
    assert all(
        binding["path"].startswith("build/foundation/preparation/100k/")
        for group in candidate["scope"]["evidence_artifacts"].values()
        for binding in group.values()
    )
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


def test_candidate_rejects_internally_coherent_sibling_preparation_root(
    tmp_path: Path,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    original_root = preparation.preparation_manifest_path.parent
    sibling_root = repo / "build/foundation/sibling-preparation/100k"
    shutil.copytree(original_root, sibling_root)
    sibling = copy.copy(preparation)
    for field in preparation.__dataclass_fields__:
        if field == "authorization_candidate_path":
            continue
        value = getattr(preparation, field)
        if isinstance(value, Mapping):
            replaced = {
                family: sibling_root / path.relative_to(original_root)
                for family, path in value.items()
            }
        else:
            replaced = sibling_root / Path(value).relative_to(original_root)
        object.__setattr__(sibling, field, replaced)
    with pytest.raises(FoundationAuthorizationError, match="exact|stage root"):
        build_authorization_candidate(
            sibling,
            repo_root=repo,
            code_commit=commit,
        )


def test_candidate_recomputes_contamination_from_bound_eval_bytes(
    tmp_path: Path,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    eval_path = preparation.eval_identity_paths["swe-bench"]
    row = json.loads(eval_path.read_text(encoding="utf-8"))
    selected = json.loads(
        preparation.shard_path.read_text(encoding="utf-8").splitlines()[0]
    )
    row["repo"] = selected["identity"]["repo"]
    eval_path.write_bytes(_canonical_json_bytes(row))
    manifest = _strict_json(preparation.preparation_manifest_path)
    binding = manifest["generated_artifact_sha256"]["eval_identities"][
        "swe-bench"
    ]
    binding["sha256"] = hashlib.sha256(eval_path.read_bytes()).hexdigest()
    binding["size"] = eval_path.stat().st_size
    _write_json(preparation.preparation_manifest_path, manifest)

    with pytest.raises(
        FoundationAuthorizationError,
        match="coher|contamination|disjoint|finding",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


def test_candidate_rejects_rehashed_empty_report_source_hashes(
    tmp_path: Path,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    report = _strict_json(preparation.conversion_report_path)
    report["source_hashes"] = {}
    preparation.conversion_report_path.write_bytes(
        _canonical_json_bytes(report)
    )
    _refresh_derived_preparation(preparation)

    with pytest.raises(
        FoundationAuthorizationError,
        match="source|conversion|coher|report",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


@pytest.mark.parametrize("missing", ("input", "target", "dataset_family", "dataset_id"))
def test_candidate_rejects_rehashed_incomplete_conversion_example(
    tmp_path: Path,
    missing: str,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    examples = [
        json.loads(line)
        for line in preparation.conversion_examples_path.read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    examples[0].pop(missing)
    preparation.conversion_examples_path.write_bytes(
        b"".join(_canonical_json_bytes(example) for example in examples)
    )
    report = _strict_json(preparation.conversion_report_path)
    report["output"]["hashes"]["examples_jsonl_sha256"] = hashlib.sha256(
        preparation.conversion_examples_path.read_bytes()
    ).hexdigest()
    preparation.conversion_report_path.write_bytes(_canonical_json_bytes(report))
    _refresh_derived_preparation(preparation)

    with pytest.raises(
        FoundationAuthorizationError,
        match="schema|conversion|example|coher|join",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


@pytest.mark.parametrize(
    "case",
    ("source_hash", "reconciliation", "output_count", "output_hash"),
)
def test_candidate_rejects_rehashed_conversion_report_contradictions(
    tmp_path: Path,
    case: str,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    report = _strict_json(preparation.conversion_report_path)
    if case == "source_hash":
        report["source_hashes"]["traces_file_sha256"] = "0" * 64
    elif case == "reconciliation":
        report["count_reconciliation"]["reconciled"] = False
    elif case == "output_count":
        report["output"]["examples_emitted"] += 1
    else:
        report["output"]["hashes"]["examples_jsonl_sha256"] = "0" * 64
    preparation.conversion_report_path.write_bytes(_canonical_json_bytes(report))
    _refresh_derived_preparation(preparation)

    with pytest.raises(
        FoundationAuthorizationError,
        match="source|conversion|report|hash|reconcil|coher",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


def test_candidate_rejects_rehashed_hash_manifest_contradiction(
    tmp_path: Path,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    hash_manifest = _strict_json(preparation.conversion_hash_manifest_path)
    hash_manifest["hashes"]["examples_jsonl_sha256"] = "0" * 64
    hash_manifest["hashes"]["hash_manifest_json_sha256"] = None
    hash_manifest["hashes"]["hash_manifest_json_sha256"] = hashlib.sha256(
        _canonical_json_bytes(hash_manifest)
    ).hexdigest()
    preparation.conversion_hash_manifest_path.write_bytes(
        _canonical_json_bytes(hash_manifest)
    )
    _refresh_derived_preparation(
        preparation,
        repair_hash_manifest=False,
    )

    with pytest.raises(
        FoundationAuthorizationError,
        match="manifest|hash|conversion|coher",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


@pytest.mark.parametrize(
    "payload",
    (
        b'{"error":"quarantined"}\n',
        b'{"error":}\n',
    ),
)
def test_candidate_strictly_rejects_nonempty_invalid_examples(
    tmp_path: Path,
    payload: bytes,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    preparation.conversion_invalid_examples_path.write_bytes(payload)
    manifest = _strict_json(preparation.preparation_manifest_path)
    binding = manifest["generated_artifact_sha256"]["conversion"][
        "invalid_examples"
    ]
    binding["sha256"] = hashlib.sha256(payload).hexdigest()
    binding["size"] = len(payload)
    _write_json(preparation.preparation_manifest_path, manifest)

    with pytest.raises(
        FoundationAuthorizationError,
        match="invalid|JSON|empty|coher",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


@pytest.mark.parametrize("case", ("missing_eval", "empty", "trace_digest"))
def test_candidate_rejects_rehashed_incomplete_source_integrity(
    tmp_path: Path,
    case: str,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    receipt = _strict_json(preparation.source_integrity_receipt_path)
    if case == "missing_eval":
        receipt["before"] = receipt["before"][:-1]
    elif case == "empty":
        receipt["before"] = []
    else:
        for snapshot in receipt["before"]:
            if snapshot["relative_path"].endswith("pneuma_traces.jsonl"):
                snapshot["sha256"] = "0" * 64
    receipt["after"] = copy.deepcopy(receipt["before"])
    _write_json(preparation.source_integrity_receipt_path, receipt)
    _refresh_preparation_receipt_digest(
        preparation,
        preparation.source_integrity_receipt_path,
    )

    with pytest.raises(
        FoundationAuthorizationError,
        match="source|integrity|input|coher|digest",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


@pytest.mark.parametrize(
    ("case", "recompute_record_ids"),
    (
        ("prompt", True),
        ("target", True),
        ("labels", True),
        ("forecast", True),
        ("identity", True),
        ("record_id", False),
    ),
)
def test_candidate_rejects_rehashed_underived_rendered_record(
    tmp_path: Path,
    case: str,
    recompute_record_ids: bool,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    record = json.loads(
        preparation.shard_path.read_text(encoding="utf-8").splitlines()[0]
    )
    if case == "prompt":
        record["rendered"]["prompt_text"] += " changed"
    elif case == "target":
        record["rendered"]["target_text"] += " changed"
    elif case == "labels":
        record["observations"]["labels"]["resolved"] = False
    elif case == "forecast":
        record["forecast_targets"]["action_success"]["value"] = 0.0
    elif case == "identity":
        record["identity"]["task_id"] = "changed-task"
    else:
        record["record_id"] = "ftr:" + "0" * 64
    preparation.shard_path.write_bytes(_canonical_json_bytes(record))
    _refresh_derived_preparation(
        preparation,
        recompute_record_ids=recompute_record_ids,
    )

    with pytest.raises(
        FoundationAuthorizationError,
        match="deriv|record|render|coher",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


def test_exact_final_handshake_verifies_and_applies_one_lane(tmp_path: Path) -> None:
    repo, preparation, _commit, final_path = _build_and_finalize(tmp_path)
    verified = verify_foundation_authorization(final_path, repo_root=repo)
    assert verified.model_key == "2b"
    assert verified.token_ceiling == 100_000
    assert dict(verified.authorized_lane_weights) == {
        "swe-gym-openhands-sampled": 1.0
    }
    assert isinstance(verified.authorized_lane_weights, MappingProxyType)
    assert isinstance(verified.authorized_record_membership, MappingProxyType)
    record = json.loads(
        preparation.shard_path.read_text(encoding="utf-8").splitlines()[0]
    )
    before = copy.deepcopy(record)
    effective = apply_verified_authorization(record, verified)
    assert effective.record is not record
    assert effective.effective_weight == 1.0
    assert record == before
    bound_target = effective.record["rendered"]["target_text"]
    bound_membership = dict(verified.authorized_record_membership)
    record["rendered"]["target_text"] = "caller changed target"
    record["source"]["lane_id"] = "caller-changed-lane"
    record["forecast_targets"]["action_success"]["value"] = 0.0
    record["observations"]["tools"].append("caller-tool")
    assert effective.record["rendered"]["target_text"] == bound_target
    assert effective.record["source"]["lane_id"] == "swe-gym-openhands-sampled"
    assert effective.record["forecast_targets"]["action_success"]["value"] == 1.0
    assert isinstance(effective.record["observations"]["tools"], tuple)
    assert dict(verified.authorized_record_membership) == bound_membership
    assert effective.effective_weight == 1.0
    with pytest.raises(TypeError):
        effective.record["rendered"]["target_text"] = "direct change"
    with pytest.raises(TypeError):
        effective.record["source"]["lane_id"] = "direct change"
    with pytest.raises(TypeError):
        effective.record["forecast_targets"]["action_success"]["value"] = 0.0
    with pytest.raises(AttributeError):
        effective.record["observations"]["tools"].append("direct change")


def test_apply_requires_exact_verified_shard_membership(tmp_path: Path) -> None:
    repo, preparation, _commit, final_path = _build_and_finalize(tmp_path)
    verified = verify_foundation_authorization(final_path, repo_root=repo)
    authorized = json.loads(
        preparation.shard_path.read_text(encoding="utf-8").splitlines()[0]
    )
    assert set(verified.authorized_record_membership) == {
        authorized["record_id"]
    }
    assert apply_verified_authorization(authorized, verified).effective_weight == 1.0

    never_in_shard = copy.deepcopy(authorized)
    never_in_shard["record_id"] = "ftr:" + "9" * 64
    never_in_shard["source"]["source_record_id"] = "unrelated-source"
    with pytest.raises(FoundationAuthorizationError, match="membership|shard|record"):
        apply_verified_authorization(never_in_shard, verified)

    modified = copy.deepcopy(authorized)
    modified["rendered"]["target_text"] += " one-byte-mutation"
    with pytest.raises(FoundationAuthorizationError, match="membership|shard|record|digest"):
        apply_verified_authorization(modified, verified)


def test_apply_rejects_record_from_post_verify_swapped_shard(tmp_path: Path) -> None:
    repo, preparation, _commit, final_path = _build_and_finalize(tmp_path)
    verified = verify_foundation_authorization(final_path, repo_root=repo)
    swapped = json.loads(
        preparation.shard_path.read_text(encoding="utf-8").splitlines()[0]
    )
    swapped["record_id"] = "ftr:" + "8" * 64
    swapped["source"]["source_record_id"] = "post-verify-swap"
    preparation.shard_path.write_text(
        json.dumps(swapped, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FoundationAuthorizationError, match="membership|shard|record"):
        apply_verified_authorization(swapped, verified)


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
    bindings = [*manifest["scope"]["artifacts"].values()]
    for group in manifest["scope"]["evidence_artifacts"].values():
        bindings.extend(group.values())
    for binding in bindings:
        path = repo / binding["path"]
        original = path.read_bytes()
        path.write_bytes(b"X" * max(1, len(original)))
        with pytest.raises(
            FoundationAuthorizationError,
            match="artifact|digest|changed|JSON|binding",
        ):
            verify_foundation_authorization(final_path, repo_root=repo)
        path.write_bytes(original)
    (repo / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(FoundationAuthorizationError, match="clean|commit"):
        verify_foundation_authorization(final_path, repo_root=repo)


def test_verify_rejects_oversized_declared_evidence_before_read(
    tmp_path: Path,
) -> None:
    repo, _preparation, _commit, final_path = _build_and_finalize(tmp_path)
    manifest = _strict_json(final_path)
    manifest["scope"]["evidence_artifacts"]["eval_identities"]["swe-bench"][
        "size"
    ] = 10_000_000
    manifest["scope_digest"] = authorization_scope_digest(manifest["scope"])
    manifest["operator_approval"]["scope_digest"] = manifest["scope_digest"]
    phrase = APPROVAL_PHRASE_PREFIX + " " + manifest["scope_digest"]
    manifest["operator_approval"]["approval_phrase_sha256"] = hashlib.sha256(
        phrase.encode("utf-8")
    ).hexdigest()
    _write_json(final_path, manifest)

    with pytest.raises(
        FoundationAuthorizationError,
        match="ceiling|oversized|size limit",
    ):
        verify_foundation_authorization(final_path, repo_root=repo)


def test_candidate_rejects_oversized_actual_evidence_before_full_read(
    tmp_path: Path,
) -> None:
    repo, preparation, commit = _authorization_fixture(tmp_path)
    oversized = preparation.eval_identity_paths["swe-bench"]
    with oversized.open("r+b") as stream:
        stream.truncate(10_000_000)

    with pytest.raises(
        FoundationAuthorizationError,
        match="ceiling|oversized|size limit",
    ):
        build_authorization_candidate(
            preparation,
            repo_root=repo,
            code_commit=commit,
        )


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
