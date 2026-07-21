"""Deterministic, fail-closed 2m multi-lane preparation and authorization tests."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from pneuma_lab.foundation.authorization import (
    APPROVAL_PHRASE_PREFIX,
    FoundationAuthorizationError,
    authorization_scope_digest,
    build_authorization_candidate,
    finalize_authorization,
    required_approval_phrase,
    verify_foundation_authorization,
    apply_verified_authorization,
)
from pneuma_lab.foundation.budget import CloudQuote
from pneuma_lab.foundation.cloud_bundle import (
    CloudBundleRequest,
    build_cloud_bundle,
    build_cloud_reproduction_candidate,
)
from pneuma_lab.foundation.contamination import (
    CROSS_DATASET_LEAKAGE_QUARANTINE_ID,
    EVAL_REPO_QUARANTINE_ID,
)
from pneuma_lab.foundation.data import ACTIVE_DATASET_GROUPS
from pneuma_lab.foundation.specs import MODEL_SPECS
from pneuma_lab.training import leakage_registry


ROOT = Path(__file__).resolve().parents[1]
OPENHANDS_TRACES = (
    ROOT / "fixtures/adapters/openhands_sampled/golden/pneuma_traces.jsonl"
)
OST_TRACES = ROOT / "fixtures/adapters/open_swe_traces/golden/pneuma_traces.jsonl"
OPENHANDS_LICENSE = (
    ROOT / "docs/data/license-receipts/swe-gym-openhands-sampled.local-research.json"
)
OST_LICENSE = ROOT / "docs/data/license-receipts/open-swe-traces.local-research.json"
LEAKAGE_REGISTRY = (
    ROOT / "docs/data/training-readiness/cross-dataset-leakage-registry.json"
)
APPROVED_AT = "2026-07-20T12:00:00Z"


class ByteTokenizer:
    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        assert add_special_tokens is False
        return list(text.encode("utf-8"))


def _copy_committed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def _canonical_json_bytes(value) -> bytes:
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


def _pretty_json_bytes(value) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            indent=4,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(value, indent=4, sort_keys=True, allow_nan=False) + "\n").encode(
            "utf-8"
        )
    )


def _write_pinned_tokenizer_snapshot(snapshot: Path) -> None:
    spec = MODEL_SPECS["2b"]
    snapshot.mkdir(parents=True)
    files = {
        "config.json": json.dumps(
            {
                "hidden_size": spec.hidden_size,
                "layer_types": list(spec.expected_layer_types),
                "num_hidden_layers": spec.layer_count,
            },
            sort_keys=True,
        ).encode("utf-8"),
        "tokenizer.json": b'{"fixture":"byte-tokenizer"}\n',
    }
    for name, payload in files.items():
        (snapshot / name).write_bytes(payload)
    receipt = {
        "receipt_kind": "pneuma_pinned_model_snapshot",
        "receipt_schema_version": "0.1.0",
        "model_id": spec.model_id,
        "revision": spec.revision,
        "files": [
            {
                "path": name,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in sorted(files.items())
        ],
    }
    (snapshot / "pneuma-snapshot-receipt.json").write_text(
        json.dumps(receipt, indent=4, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _split_bucket(canonical_repo: str) -> int:
    return int(hashlib.sha256(canonical_repo.encode()).hexdigest()[:8], 16) % 100


def _train_lane_repo(seed: str) -> tuple[str, str]:
    """Deterministic raw repo whose sha256:<hex> digest buckets into train."""

    index = 0
    while True:
        raw = f"ost/{seed}-{index}"
        digest = leakage_registry.repo_digest(raw)
        if _split_bucket(digest) < 80:
            return raw, digest
        index += 1


def _write_ost_lane(data_root: Path, repo_digests: tuple[str, str]) -> None:
    lane_root = data_root / "processed/open-swe-traces/pneuma-trace"
    lane_root.mkdir(parents=True)
    traces = [
        json.loads(line) for line in OST_TRACES.read_text(encoding="utf-8").splitlines()
    ]
    assert len(traces) == len(repo_digests)
    for trace, repo_digest in zip(traces, repo_digests, strict=True):
        trace["labels"]["repo_digest"] = repo_digest
    payload = b"".join(
        (
            json.dumps(
                trace,
                allow_nan=False,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        for trace in traces
    )
    (lane_root / "pneuma_traces.jsonl").write_bytes(payload)
    adapter_report = json.loads(
        (OST_TRACES.parent / "adapter_report.json").read_text(encoding="utf-8")
    )
    adapter_report["traces_file_sha256"] = hashlib.sha256(payload).hexdigest()
    (lane_root / "adapter_report.json").write_bytes(
        _canonical_json_bytes(adapter_report)
    )


def _prepare_fixture_2m(
    tmp_path: Path,
    *,
    skip_ost_license: bool = False,
    leakage_digests: tuple[str, ...] | None = None,
    eval_extra_rows: dict[str, list[dict]] | None = None,
):
    from pneuma_lab.foundation.preparation import PreparationRequest

    repo_root = tmp_path / "repo"
    data_root = tmp_path / "pneuma-data"
    _copy_committed(
        ROOT / "docs/data/training-readiness/dataset-registry.json",
        repo_root / "docs/data/training-readiness/dataset-registry.json",
    )
    registry = json.loads(
        (ROOT / "docs/data/training-readiness/dataset-registry.json").read_text(
            encoding="utf-8"
        )
    )
    for lane in registry["lanes"]:
        for references in lane["references"].values():
            for reference in references:
                if reference.get("planned") is True:
                    continue
                _copy_committed(ROOT / reference["path"], repo_root / reference["path"])
    _copy_committed(
        ROOT / "docs/data/training-readiness/pneuma-foundation-v0-suite.json",
        repo_root / "docs/data/training-readiness/pneuma-foundation-v0-suite.json",
    )
    _copy_committed(
        OPENHANDS_LICENSE,
        repo_root
        / "docs/data/license-receipts/swe-gym-openhands-sampled.local-research.json",
    )
    if not skip_ost_license:
        _copy_committed(
            OST_LICENSE,
            repo_root
            / "docs/data/license-receipts/open-swe-traces.local-research.json",
        )
    if leakage_digests is not None:
        registry_path = (
            repo_root
            / "docs/data/training-readiness/cross-dataset-leakage-registry.json"
        )
        leakage = json.loads(registry_path.read_text(encoding="utf-8"))
        digests = sorted(set(leakage_digests))
        pair = leakage["pairs"][0]
        pair["overlapping_repo_digests"] = digests
        pair["overlap_count"] = len(digests)
        pair["disjoint"] = not digests
        pair.pop("overlapping_repos", None)
        registry_path.write_bytes(_pretty_json_bytes(leakage))
    for family in ACTIVE_DATASET_GROUPS:
        family_root = data_root / "processed" / family
        family_root.mkdir(parents=True)
        (family_root / "presence.marker").write_text(family, encoding="utf-8")
    lane_root = data_root / "processed/swe-gym/openhands-sampled"
    lane_root.mkdir()
    shutil.copyfile(OPENHANDS_TRACES, lane_root / "pneuma_traces.jsonl")
    shutil.copyfile(
        OPENHANDS_TRACES.parent / "adapter_report.json",
        lane_root / "adapter_report.json",
    )
    ost_repos = (
        _train_lane_repo("alpha"),
        _train_lane_repo("beta"),
    )
    _write_ost_lane(data_root, tuple(digest for _raw, digest in ost_repos))
    for family in ("swe-bench", "swe-mera", "swe-polybench"):
        rows = [
            {
                "source_id": f"{family}-999",
                "repo": f"evaluation/{family}",
                "base_commit": hashlib.sha256(family.encode()).hexdigest(),
                "ignored_rich_field": {"not": "retained"},
            }
        ]
        rows.extend((eval_extra_rows or {}).get(family, []))
        path = data_root / f"processed/{family}/normalized_metadata.jsonl"
        path.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
    tokenizer_snapshot = (
        repo_root / "build/model-cache/models/2b" / MODEL_SPECS["2b"].revision
    )
    _write_pinned_tokenizer_snapshot(tokenizer_snapshot)
    request = PreparationRequest(
        stage="2m",
        repo_root=repo_root,
        data_root=data_root,
        tokenizer_snapshot=tokenizer_snapshot,
        output_root=repo_root / "build/foundation/preparation/2m",
    )
    _copy_committed(ROOT / ".gitignore", repo_root / ".gitignore")
    (repo_root / "uv.lock").write_text("# pinned dependency lock\n", encoding="utf-8")
    setup_script = repo_root / "scripts/foundation/setup-linux.sh"
    setup_script.parent.mkdir(parents=True, exist_ok=True)
    setup_script.write_text("#!/bin/sh\necho inert\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tests@pneuma.invalid"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Pneuma Tests"],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo_root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "fixture"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return request, ost_repos


def _result_files(result) -> tuple[Path, ...]:
    paths = []
    for field in result.__dataclass_fields__:
        if field == "tokenizer_snapshot_path":
            continue
        value = getattr(result, field)
        if value is None:
            continue
        if field == "eval_identity_paths":
            paths.extend(Path(path) for path in value.values())
        elif field == "lane_conversion_paths":
            paths.extend(
                Path(path)
                for lane_paths in value.values()
                for path in lane_paths.values()
            )
        else:
            paths.append(Path(value))
    return tuple(sorted(set(paths)))


def _shard_records(result) -> list[dict]:
    return [
        json.loads(line)
        for line in result.shard_path.read_text(encoding="utf-8").splitlines()
    ]


def _fixture_commit(repo_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _resign_final_scope(final_path: Path, repo: Path) -> None:
    manifest = json.loads(final_path.read_text(encoding="utf-8"))
    bindings = [*manifest["scope"]["artifacts"].values()]
    conversion = manifest["scope"]["evidence_artifacts"]["conversion"]
    for group in conversion.values():
        bindings.extend(group.values())
    bindings.extend(manifest["scope"]["evidence_artifacts"]["eval_identities"].values())
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


def _prepare(monkeypatch, request):
    from pneuma_lab.foundation import preparation

    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())
    return preparation.prepare_stage(request)


def _finalize(repo_root: Path, result) -> Path:
    candidate = json.loads(
        result.authorization_candidate_path.read_text(encoding="utf-8")
    )
    final_path = repo_root / "build/foundation/authorizations/final/2m.json"
    return finalize_authorization(
        result.authorization_candidate_path,
        supplied_scope_digest=candidate["scope_digest"],
        supplied_approval_phrase=required_approval_phrase(candidate),
        operator_id="student-operator",
        approved_at=APPROVED_AT,
        output_path=final_path,
    )


def _safe_cloud_quote() -> CloudQuote:
    return CloudQuote(
        hourly_usd=0.44,
        tax_inclusive_usd=38.0,
        prepaid_credit_usd=38.0,
        auto_pay_enabled=False,
        termination_hours=72,
        measured_tokens_per_second=20.0,
        prior_lifetime_spend_usd=0.0,
    )


def _build_cloud_candidate(repo_root: Path, final_path: Path) -> dict:
    gate_path = repo_root / "build/foundation/gates/local-gate-report.json"
    _write_json(gate_path, {"local_gates_passed": True})
    return build_cloud_reproduction_candidate(
        final_path,
        local_gate_report_path=gate_path,
        quote=_safe_cloud_quote(),
        output_path=repo_root
        / "build/foundation/authorizations/candidates/2m-cloud.json",
        repo_root=repo_root,
        _tokenizer_loader=lambda _path: ByteTokenizer(),
    )


def _finalize_cloud(repo_root: Path, candidate: dict) -> Path:
    return finalize_authorization(
        repo_root / "build/foundation/authorizations/candidates/2m-cloud.json",
        supplied_scope_digest=candidate["scope_digest"],
        supplied_approval_phrase=required_approval_phrase(candidate),
        operator_id="student-operator",
        approved_at=APPROVED_AT,
        output_path=repo_root / "build/foundation/authorizations/final/2m-cloud.json",
    )


def test_prepare_stage_2m_multi_lane_happy_path_is_byte_deterministic(
    tmp_path,
    monkeypatch,
) -> None:
    request, ost_repos = _prepare_fixture_2m(tmp_path)
    first = _prepare(monkeypatch, request)
    first_bytes = {path: path.read_bytes() for path in _result_files(first)}
    second = _prepare(monkeypatch, request)

    assert first == second
    assert first_bytes == {path: path.read_bytes() for path in _result_files(second)}

    manifest = json.loads(first.preparation_manifest_path.read_text(encoding="utf-8"))
    assert manifest["gradient_lanes"] == [
        "swe-gym-openhands-sampled",
        "open-swe-traces",
    ]
    assert "gradient_lane" not in manifest
    assert manifest["token_ceiling"] == 2_000_000
    assert manifest["lane_counts"] == {
        "swe-gym-openhands-sampled": {
            "converted_examples": 3,
            "selected_records": 3,
        },
        "open-swe-traces": {
            "converted_examples": 2,
            "selected_records": 2,
        },
    }
    assert manifest["gates"]["cross_dataset_leakage_quarantine_applied"] is True
    assert set(manifest["generated_artifact_sha256"]["conversion"]) == {
        "swe-gym-openhands-sampled",
        "open-swe-traces",
    }
    assert set(manifest["receipt_sha256"]) == {
        "suite_report.json",
        "license_receipt.json",
        "ost_license_receipt.json",
        "leakage_receipt.json",
        "source_presence_receipt.json",
        "source_integrity_receipt.json",
        "split_receipt.json",
        "contamination_receipt.json",
        "diversity_receipt.json",
        "selection_receipt.json",
    }
    assert len(manifest["source_receipt_hashes"]) == 9

    for lane_id in ("swe-gym-openhands-sampled", "open-swe-traces"):
        lane_root = request.output_root / "conversion" / lane_id
        for name in (
            "examples.jsonl",
            "invalid_examples.jsonl",
            "conversion_report.json",
            "hash_manifest.json",
        ):
            assert (lane_root / name).is_file()

    records = _shard_records(first)
    by_lane = {}
    for record in records:
        by_lane.setdefault(record["source"]["lane_id"], []).append(record)
    assert set(by_lane) == {"swe-gym-openhands-sampled", "open-swe-traces"}
    assert all(
        record["disposition"]["gradient_eligibility"] == "first_stage"
        for record in by_lane["swe-gym-openhands-sampled"]
    )
    for record in by_lane["open-swe-traces"]:
        assert record["disposition"]["gradient_eligibility"] == "later"
        assert record["disposition"]["privacy_disposition"] == (
            "digest_only_by_construction"
        )
        assert record["identity"]["repo"].startswith("sha256:")
        assert record["source"]["dataset_family"] == "open-swe-traces"
    assert {record["observations"]["labels"]["resolved"] for record in records} == {
        False,
        True,
    }
    assert all(
        record["source"]["receipt_hashes"] == manifest["source_receipt_hashes"]
        for record in records
    )

    leakage_receipt = json.loads(first.leakage_receipt_path.read_text(encoding="utf-8"))
    committed_registry = (
        request.repo_root
        / "docs/data/training-readiness/cross-dataset-leakage-registry.json"
    ).read_bytes()
    assert (
        leakage_receipt["registry_sha256"]
        == hashlib.sha256(committed_registry).hexdigest()
    )
    assert leakage_receipt["quarantine_id"] == CROSS_DATASET_LEAKAGE_QUARANTINE_ID
    assert leakage_receipt["quarantined_example_counts"] == {
        "open-swe-traces": 0,
        "swe-gym-openhands-sampled": 0,
    }
    assert len(leakage_receipt["overlapping_repo_digests"]) == 7

    ost_license = json.loads(first.ost_license_receipt_path.read_text(encoding="utf-8"))
    assert ost_license["dataset_id"] == "open-swe-traces"
    assert ost_license["cloud_redistribution_allowed"] is False

    candidate = json.loads(
        first.authorization_candidate_path.read_text(encoding="utf-8")
    )
    assert candidate["scope"]["stage"] == "2m"
    assert candidate["scope"]["authorized_lane_weights"] == {
        "swe-gym-openhands-sampled": 1.0,
        "open-swe-traces": 1.0,
    }
    assert set(candidate["scope"]["artifacts"]) >= {
        "ost_license_receipt",
        "leakage_receipt",
    }
    assert set(candidate["scope"]["evidence_artifacts"]["conversion"]) == {
        "swe-gym-openhands-sampled",
        "open-swe-traces",
    }


def test_prepare_stage_2m_quarantines_cross_lane_registry_repos(
    tmp_path,
    monkeypatch,
) -> None:
    ost_alpha = _train_lane_repo("alpha")
    ost_beta = _train_lane_repo("beta")
    quarantined = (
        leakage_registry.repo_digest("demo/alpha"),
        ost_beta[1],
    )
    request, _ost_repos = _prepare_fixture_2m(
        tmp_path,
        leakage_digests=quarantined,
    )
    result = _prepare(monkeypatch, request)

    records = _shard_records(result)
    shard_repos = {record["identity"]["repo"] for record in records}
    assert "demo/alpha" not in shard_repos
    assert ost_beta[1] not in shard_repos
    assert "demo/beta" in shard_repos
    assert ost_alpha[1] in shard_repos

    split = json.loads(result.split_receipt_path.read_text(encoding="utf-8"))
    quarantine_by_repo = {
        item["repo"]: item["quarantine_id"] for item in split["assignments"]
    }
    assert quarantine_by_repo["demo/alpha"] == CROSS_DATASET_LEAKAGE_QUARANTINE_ID
    assert quarantine_by_repo[ost_beta[1]] == CROSS_DATASET_LEAKAGE_QUARANTINE_ID
    assert quarantine_by_repo["demo/beta"] is None
    assert quarantine_by_repo[ost_alpha[1]] is None

    leakage_receipt = json.loads(
        result.leakage_receipt_path.read_text(encoding="utf-8")
    )
    assert leakage_receipt["overlapping_repo_digests"] == sorted(quarantined)
    assert leakage_receipt["quarantined_example_counts"] == {
        "open-swe-traces": 1,
        "swe-gym-openhands-sampled": 2,
    }
    assert leakage_receipt["quarantined_example_total"] == 3

    manifest = json.loads(result.preparation_manifest_path.read_text(encoding="utf-8"))
    assert manifest["lane_counts"]["swe-gym-openhands-sampled"] == {
        "converted_examples": 3,
        "selected_records": 1,
    }
    assert manifest["lane_counts"]["open-swe-traces"] == {
        "converted_examples": 2,
        "selected_records": 1,
    }


def test_prepare_stage_2m_quarantines_ost_examples_matching_eval_repo_digests(
    tmp_path,
    monkeypatch,
) -> None:
    ost_alpha = _train_lane_repo("alpha")
    request, _ost_repos = _prepare_fixture_2m(
        tmp_path,
        eval_extra_rows={
            "swe-bench": [
                {
                    "source_id": "swe-bench-777",
                    "repo": ost_alpha[0],
                    "base_commit": "7" * 40,
                }
            ]
        },
    )
    result = _prepare(monkeypatch, request)

    records = _shard_records(result)
    shard_repos = {record["identity"]["repo"] for record in records}
    assert ost_alpha[1] not in shard_repos

    split = json.loads(result.split_receipt_path.read_text(encoding="utf-8"))
    quarantine_by_repo = {
        item["repo"]: item["quarantine_id"] for item in split["assignments"]
    }
    assert quarantine_by_repo[ost_alpha[1]] == EVAL_REPO_QUARANTINE_ID


def test_prepare_stage_2m_fails_closed_without_the_ost_license_receipt(
    tmp_path,
    monkeypatch,
) -> None:
    request, _ost_repos = _prepare_fixture_2m(tmp_path, skip_ost_license=True)
    from pneuma_lab.foundation import preparation

    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())
    with pytest.raises(ValueError, match="Open-SWE-Traces license receipt"):
        preparation.prepare_stage(request)
    assert not request.output_root.exists()


def test_2m_candidate_finalizes_verifies_and_applies_both_lanes(
    tmp_path,
    monkeypatch,
) -> None:
    request, _ost_repos = _prepare_fixture_2m(tmp_path)
    result = _prepare(monkeypatch, request)
    final_path = _finalize(request.repo_root, result)
    verified = verify_foundation_authorization(
        final_path,
        repo_root=request.repo_root,
        _tokenizer_loader=lambda _path: ByteTokenizer(),
    )
    assert verified.token_ceiling == 2_000_000
    assert dict(verified.authorized_lane_weights) == {
        "swe-gym-openhands-sampled": 1.0,
        "open-swe-traces": 1.0,
    }
    records = _shard_records(result)
    by_lane = {}
    for record in records:
        by_lane.setdefault(record["source"]["lane_id"], record)
    ost_effective = apply_verified_authorization(
        by_lane["open-swe-traces"],
        verified,
    )
    assert ost_effective.effective_weight == 1.0
    assert ost_effective.record["disposition"]["gradient_eligibility"] == "later"
    openhands_effective = apply_verified_authorization(
        by_lane["swe-gym-openhands-sampled"],
        verified,
    )
    assert openhands_effective.effective_weight == 1.0

    swapped = copy.deepcopy(by_lane["open-swe-traces"])
    swapped["disposition"]["gradient_eligibility"] = "first_stage"
    with pytest.raises(
        FoundationAuthorizationError,
        match="eligib|membership|record",
    ):
        apply_verified_authorization(swapped, verified)


def test_2m_verification_rejects_tampered_leakage_receipt(
    tmp_path,
    monkeypatch,
) -> None:
    request, _ost_repos = _prepare_fixture_2m(tmp_path)
    result = _prepare(monkeypatch, request)
    final_path = _finalize(request.repo_root, result)

    original = result.leakage_receipt_path.read_bytes()
    result.leakage_receipt_path.write_bytes(b"X" * len(original))
    with pytest.raises(
        FoundationAuthorizationError,
        match="digest|changed|JSON|binding",
    ):
        verify_foundation_authorization(
            final_path,
            repo_root=request.repo_root,
            _tokenizer_loader=lambda _path: ByteTokenizer(),
        )
    result.leakage_receipt_path.write_bytes(original)

    receipt = json.loads(original.decode("utf-8"))
    receipt["registry_sha256"] = "0" * 64
    result.leakage_receipt_path.write_bytes(_pretty_json_bytes(receipt))
    manifest = json.loads(result.preparation_manifest_path.read_text(encoding="utf-8"))
    manifest["receipt_sha256"]["leakage_receipt.json"] = hashlib.sha256(
        result.leakage_receipt_path.read_bytes()
    ).hexdigest()
    _write_json(result.preparation_manifest_path, manifest)
    _resign_final_scope(final_path, request.repo_root)
    with pytest.raises(
        FoundationAuthorizationError,
        match="leakage|registry|receipt|coher",
    ):
        verify_foundation_authorization(
            final_path,
            repo_root=request.repo_root,
            _tokenizer_loader=lambda _path: ByteTokenizer(),
        )


def test_2m_verification_rejects_wrong_lane_weights(tmp_path, monkeypatch) -> None:
    request, _ost_repos = _prepare_fixture_2m(tmp_path)
    result = _prepare(monkeypatch, request)
    final_path = _finalize(request.repo_root, result)
    manifest = json.loads(final_path.read_text(encoding="utf-8"))
    del manifest["scope"]["authorized_lane_weights"]["open-swe-traces"]
    manifest["scope_digest"] = authorization_scope_digest(manifest["scope"])
    manifest["operator_approval"]["scope_digest"] = manifest["scope_digest"]
    phrase = APPROVAL_PHRASE_PREFIX + " " + manifest["scope_digest"]
    manifest["operator_approval"]["approval_phrase_sha256"] = hashlib.sha256(
        phrase.encode("utf-8")
    ).hexdigest()
    _write_json(final_path, manifest)
    with pytest.raises(FoundationAuthorizationError, match="lane"):
        verify_foundation_authorization(
            final_path,
            repo_root=request.repo_root,
            _tokenizer_loader=lambda _path: ByteTokenizer(),
        )


def test_2m_candidate_rejects_tampered_ost_conversion_report(
    tmp_path,
    monkeypatch,
) -> None:
    request, _ost_repos = _prepare_fixture_2m(tmp_path)
    result = _prepare(monkeypatch, request)
    report_path = result.lane_conversion_paths["open-swe-traces"]["conversion_report"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["warnings"] = []
    report_path.write_bytes(_canonical_json_bytes(report))
    manifest = json.loads(result.preparation_manifest_path.read_text(encoding="utf-8"))
    binding = manifest["generated_artifact_sha256"]["conversion"]["open-swe-traces"][
        "conversion_report"
    ]
    binding["sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    binding["size"] = report_path.stat().st_size
    _write_json(result.preparation_manifest_path, manifest)

    with pytest.raises(
        FoundationAuthorizationError,
        match="conversion|report|receipt|coher|source",
    ):
        build_authorization_candidate(
            result,
            repo_root=request.repo_root,
            code_commit=_fixture_commit(request.repo_root),
            _tokenizer=ByteTokenizer(),
        )


def test_2m_cloud_candidate_finalizes_and_verifies_both_lanes(
    tmp_path,
    monkeypatch,
) -> None:
    request, _ost_repos = _prepare_fixture_2m(tmp_path)
    result = _prepare(monkeypatch, request)
    final_path = _finalize(request.repo_root, result)
    candidate = _build_cloud_candidate(request.repo_root, final_path)
    scope = candidate["scope"]
    local_manifest = json.loads(final_path.read_text(encoding="utf-8"))
    assert candidate["authorization_status"] == "candidate"
    assert scope["execution_profile"] == "cloud"
    assert scope["stage"] == "2m"
    assert scope["authorized_lane_weights"] == {
        "swe-gym-openhands-sampled": 1.0,
        "open-swe-traces": 1.0,
    }
    assert {"ost_license_receipt", "leakage_receipt"} <= set(scope["artifacts"])
    assert scope["artifacts"] == local_manifest["scope"]["artifacts"]
    assert scope["evidence_artifacts"] == local_manifest["scope"]["evidence_artifacts"]
    assert set(scope["evidence_artifacts"]["conversion"]) == {
        "swe-gym-openhands-sampled",
        "open-swe-traces",
    }
    assert scope["source_data_policy"] == {
        "root": "bundle://authorized-shard",
        "write_allowed": False,
        "private_cloud_transfer": False,
        "private_cloud_transfer_allowed": True,
    }
    assert scope["budget"] == {
        "paid_compute_usd": 0,
        "cloud_jobs_used": 0,
        "paid_compute_ceiling_usd": 38.0,
        "cloud_job_ceiling": 1,
        "cloud_lifetime_cap_usd": 45,
    }

    cloud_final = _finalize_cloud(request.repo_root, candidate)
    assert cloud_final == (
        request.repo_root / "build/foundation/authorizations/final/2m-cloud.json"
    )
    verified = verify_foundation_authorization(
        cloud_final,
        repo_root=request.repo_root,
        _tokenizer_loader=lambda _path: ByteTokenizer(),
    )
    assert verified.token_ceiling == 2_000_000
    assert dict(verified.authorized_lane_weights) == {
        "swe-gym-openhands-sampled": 1.0,
        "open-swe-traces": 1.0,
    }
    assert verified.manifest["scope"]["execution_profile"] == "cloud"
    assert len(verified.authorized_record_membership) == len(_shard_records(result))


def test_2m_cloud_candidate_rejects_a_tampered_leakage_receipt(
    tmp_path,
    monkeypatch,
) -> None:
    request, _ost_repos = _prepare_fixture_2m(tmp_path)
    result = _prepare(monkeypatch, request)
    final_path = _finalize(request.repo_root, result)
    original = result.leakage_receipt_path.read_bytes()
    result.leakage_receipt_path.write_bytes(b"X" * len(original))
    with pytest.raises(
        FoundationAuthorizationError,
        match="digest|changed|leakage",
    ):
        _build_cloud_candidate(request.repo_root, final_path)
    assert not (
        request.repo_root / "build/foundation/authorizations/candidates/2m-cloud.json"
    ).exists()


def test_2m_cloud_verification_rejects_a_tampered_gate_report(
    tmp_path,
    monkeypatch,
) -> None:
    request, _ost_repos = _prepare_fixture_2m(tmp_path)
    result = _prepare(monkeypatch, request)
    final_path = _finalize(request.repo_root, result)
    candidate = _build_cloud_candidate(request.repo_root, final_path)
    cloud_final = _finalize_cloud(request.repo_root, candidate)
    gate_path = request.repo_root / "build/foundation/gates/local-gate-report.json"
    _write_json(gate_path, {"local_gates_passed": False})
    with pytest.raises(FoundationAuthorizationError, match="gate report"):
        verify_foundation_authorization(
            cloud_final,
            repo_root=request.repo_root,
            _tokenizer_loader=lambda _path: ByteTokenizer(),
        )


def test_2m_cloud_bundle_lists_both_lane_receipts_and_no_raw_corpus(
    tmp_path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import cloud_bundle

    request, _ost_repos = _prepare_fixture_2m(tmp_path)
    result = _prepare(monkeypatch, request)
    final_path = _finalize(request.repo_root, result)
    candidate = _build_cloud_candidate(request.repo_root, final_path)
    cloud_final = _finalize_cloud(request.repo_root, candidate)

    def _verify_with_fixture_tokenizer(path, *, repo_root, registry_path=None):
        del registry_path
        return verify_foundation_authorization(
            path,
            repo_root=repo_root,
            _tokenizer_loader=lambda _path: ByteTokenizer(),
        )

    monkeypatch.setattr(
        cloud_bundle,
        "verify_foundation_authorization",
        _verify_with_fixture_tokenizer,
    )
    bundle_request = CloudBundleRequest(
        repo_root=request.repo_root,
        data_root=request.data_root,
        authorization_path=cloud_final,
        output_path=request.repo_root / "build/foundation/cloud/2m-bundle.tar",
        stage="2m",
        quote=_safe_cloud_quote(),
        dry_run=True,
    )
    manifest = build_cloud_bundle(bundle_request)
    arcnames = {entry["arcname"] for entry in manifest["files"]}
    scope = candidate["scope"]
    for name in (
        "shard",
        "shard_manifest",
        "license_receipt",
        "ost_license_receipt",
        "leakage_receipt",
    ):
        assert scope["artifacts"][name]["path"] in arcnames
    assert scope["local_gate_report"]["path"] in arcnames
    assert "build/foundation/authorizations/final/2m-cloud.json" in arcnames
    for arcname in arcnames:
        lowered = arcname.casefold()
        assert "pneuma-data" not in lowered
        assert "swe-chat" not in lowered
        assert "sec-bench-pro" not in lowered
        assert not lowered.endswith(".ipynb")
        assert not any(
            lowered.endswith(suffix)
            for suffix in (".pt", ".pth", ".ckpt", ".safetensors")
        )
    assert not bundle_request.output_path.exists()


def test_canonical_repo_key_accepts_digest_identities() -> None:
    from pneuma_lab.foundation import preparation

    digest = leakage_registry.repo_digest("demo/alpha")
    assert preparation._canonical_repo_key(digest) == digest
    assert (
        preparation._canonical_repo_key(digest.upper().replace("SHA256:", "sha256:"))
        == digest
    )
    assignments = preparation._split_assignments(
        (
            {"example_id": "leak-1", "split_group": {"repo": digest}},
            {"example_id": "keep-1", "split_group": {"repo": "safe/repo"}},
        ),
        leakage_quarantined_digests=frozenset({digest}),
    )
    by_id = {item["record_source_id"]: item for item in assignments}
    assert by_id["leak-1"]["canonical_repo"] == digest
    assert by_id["leak-1"]["quarantine_id"] == CROSS_DATASET_LEAKAGE_QUARANTINE_ID
    assert by_id["keep-1"]["quarantine_id"] is None


def test_eval_overlap_quarantine_adds_repo_digests_for_digest_lanes() -> None:
    from pneuma_lab.foundation import preparation
    from pneuma_lab.foundation.contamination import IdentityRecord

    identity = IdentityRecord(
        "swe-bench",
        "swe-bench",
        "Shared-Org/Shared-Repo",
        "1",
        "t-1",
        None,
        None,
        None,
        None,
    )
    keys = preparation._eval_overlap_quarantine(
        (identity,),
        include_repo_digests=True,
    )
    assert "shared-org/shared-repo" in keys
    assert leakage_registry.repo_digest("Shared-Org/Shared-Repo") in keys
    assert preparation._eval_overlap_quarantine((identity,)) == frozenset(
        {"shared-org/shared-repo"}
    )
