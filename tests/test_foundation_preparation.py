"""Deterministic, fail-closed foundation shard preparation tests."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from pneuma_lab.converters.openhands_sampled_training import convert_traces
from pneuma_lab.foundation.records import (
    GradientEligibility,
    LaneDisposition,
    TerminalRole,
    render_foundation_record,
)
from pneuma_lab.foundation.data import ACTIVE_DATASET_GROUPS


ROOT = Path(__file__).resolve().parents[1]
TRACE_FIXTURE = (
    ROOT / "fixtures/adapters/openhands_sampled/golden/pneuma_traces.jsonl"
)
LICENSE_RECEIPT = (
    ROOT / "docs/data/license-receipts/swe-gym-openhands-sampled.local-research.json"
)


class ByteTokenizer:
    def encode(self, text: str, *, add_special_tokens: bool) -> list[int]:
        assert add_special_tokens is False
        return list(text.encode("utf-8"))


def _foundation_records() -> list[dict]:
    traces = [
        json.loads(line)
        for line in TRACE_FIXTURE.read_text(encoding="utf-8").splitlines()
    ]
    examples = convert_traces(traces)
    disposition = LaneDisposition(
        terminal_role=TerminalRole.TRAIN,
        gradient_eligibility=GradientEligibility.FIRST_STAGE,
        license_disposition="local_research_candidate_no_redistribution",
        privacy_disposition="redaction_verified",
        dual_use_disposition="not_flagged",
        oracle_disposition="target_only",
    )
    return [
        render_foundation_record(
            example,
            lane_disposition=disposition,
            split_assignment={"split_id": "train", "quarantine_id": None},
            tokenizer=ByteTokenizer(),
            tokenizer_revision="1" * 40,
            source_receipt_hashes=("a" * 64,),
        )
        for example in examples
    ]

def test_preparation_public_contract_exists() -> None:
    from pneuma_lab.foundation.preparation import (
        STAGE_TOKEN_CEILINGS,
        PreparationRequest,
        PreparationResult,
        deterministic_split,
        prepare_stage,
        select_complete_records,
    )

    assert STAGE_TOKEN_CEILINGS == {
        "100k": 100_000,
        "500k": 500_000,
        "1m": 1_000_000,
        "2m": 2_000_000,
        "8m": 8_000_000,
        "16m": 16_000_000,
        "32m": 32_000_000,
    }
    request = PreparationRequest(
        stage="100k",
        repo_root=Path("repo"),
        data_root=Path("data"),
        tokenizer_snapshot=Path("tokenizer"),
        output_root=Path("out"),
    )
    assert request.seed == 20260713
    assert request.dry_run is False
    assert set(PreparationResult.__dataclass_fields__) == {
        "preparation_manifest_path",
        "suite_report_path",
        "license_receipt_path",
        "source_presence_receipt_path",
        "source_integrity_receipt_path",
        "shard_path",
        "shard_manifest_path",
        "split_receipt_path",
        "contamination_receipt_path",
        "diversity_receipt_path",
        "selection_receipt_path",
    }
    assert callable(deterministic_split)
    assert callable(select_complete_records)
    assert callable(prepare_stage)


def test_deterministic_split_uses_casefolded_repository_hash() -> None:
    from pneuma_lab.foundation.preparation import deterministic_split

    for repo in ("demo/alpha", "demo/beta", "Org/Mixed-Case"):
        bucket = int(hashlib.sha256(repo.casefold().encode()).hexdigest()[:8], 16) % 100
        expected = "train" if bucket < 80 else "validation" if bucket < 90 else "held_out"
        assert deterministic_split(repo) == expected
        assert deterministic_split(repo.swapcase()) == expected
    with pytest.raises(ValueError, match="repository"):
        deterministic_split("  ")


def test_selection_is_stable_train_only_bounded_and_label_anchored() -> None:
    from pneuma_lab.foundation.preparation import select_complete_records

    records = _foundation_records()
    validation = copy.deepcopy(records[0])
    validation["record_id"] = "ftr:" + "f" * 64
    validation["split"]["split_id"] = "validation"
    selected = select_complete_records(
        reversed(records + [validation]),
        token_ceiling=sum(record["tokenization"]["total_tokens"] for record in records),
    )

    assert [record["record_id"] for record in selected] == sorted(
        record["record_id"] for record in records
    )
    assert {record["observations"]["labels"]["resolved"] for record in selected} == {
        False,
        True,
    }
    assert all(record["split"]["split_id"] == "train" for record in selected)
    assert sum(record["tokenization"]["total_tokens"] for record in selected) <= sum(
        record["tokenization"]["total_tokens"] for record in records
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (lambda record: record["observations"].pop("labels"), "labels"),
        (lambda record: record["tokenization"].update(total_tokens=0), "token"),
        (lambda record: record["tokenization"].update(total_tokens=float("nan")), "token|JSON"),
        (lambda record: record.update(record_id="duplicate"), "record_id|schema"),
    ),
)
def test_selection_rejects_malformed_nested_records(mutation, message) -> None:
    from pneuma_lab.foundation.preparation import select_complete_records

    records = _foundation_records()
    mutation(records[0])
    with pytest.raises(ValueError, match=message):
        select_complete_records(records, token_ceiling=100_000)


def test_selection_rejects_duplicate_record_ids() -> None:
    from pneuma_lab.foundation.preparation import select_complete_records

    records = _foundation_records()
    records[1]["record_id"] = records[0]["record_id"]
    with pytest.raises(ValueError, match="duplicate"):
        select_complete_records(records, token_ceiling=100_000)


def test_selection_excludes_nontraining_terminal_roles() -> None:
    from pneuma_lab.foundation.preparation import select_complete_records

    records = _foundation_records()
    eval_record = copy.deepcopy(records[0])
    eval_record["record_id"] = "ftr:" + "e" * 64
    eval_record["disposition"]["terminal_role"] = "eval"
    selected = select_complete_records(
        records + [eval_record],
        token_ceiling=100_000,
    )

    assert eval_record["record_id"] not in {
        record["record_id"] for record in selected
    }


def test_committed_license_receipt_is_exact_and_conservative() -> None:
    assert json.loads(LICENSE_RECEIPT.read_text(encoding="utf-8")) == {
        "receipt_kind": "dataset_license_posture",
        "receipt_schema_version": "0.1.0",
        "dataset_id": "swe-gym-openhands-sampled",
        "artifact_card_license_declared": False,
        "upstream_code_license": "Apache-2.0",
        "mirror_directory_license_observed": "MIT",
        "decision": "local_research_candidate_no_redistribution",
        "cloud_redistribution_allowed": False,
        "requires_exact_operator_authorization": True,
        "sources": [
            "https://huggingface.co/datasets/SWE-Gym/OpenHands-Sampled-Trajectories",
            "https://github.com/SWE-Gym/SWE-Gym",
            "https://huggingface.co/datasets/neulab/agent-data-collection/blob/main/swe-gym_openhands_sampled_trajectories/LICENSE",
        ],
    }


def _copy_committed(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def _prepare_fixture(tmp_path: Path):
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
                source = ROOT / reference["path"]
                _copy_committed(source, repo_root / reference["path"])
    _copy_committed(
        ROOT / "docs/data/training-readiness/pneuma-foundation-v0-suite.json",
        repo_root / "docs/data/training-readiness/pneuma-foundation-v0-suite.json",
    )
    _copy_committed(
        LICENSE_RECEIPT,
        repo_root
        / "docs/data/license-receipts/swe-gym-openhands-sampled.local-research.json",
    )
    for family in ACTIVE_DATASET_GROUPS:
        family_root = data_root / "processed" / family
        family_root.mkdir(parents=True)
        (family_root / "presence.marker").write_text(family, encoding="utf-8")
    lane_root = data_root / "processed/swe-gym/openhands-sampled"
    lane_root.mkdir()
    shutil.copyfile(TRACE_FIXTURE, lane_root / "pneuma_traces.jsonl")
    shutil.copyfile(
        TRACE_FIXTURE.parent / "adapter_report.json",
        lane_root / "adapter_report.json",
    )
    for family in ("swe-bench", "swe-mera", "swe-polybench"):
        path = data_root / f"processed/{family}/normalized_metadata.jsonl"
        path.write_text(
            json.dumps(
                {
                    "source_id": f"{family}-999",
                    "repo": f"evaluation/{family}",
                    "base_commit": hashlib.sha256(family.encode()).hexdigest(),
                    "ignored_rich_field": {"not": "retained"},
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    tokenizer_snapshot = repo_root / "build/model-cache/2b/snapshot"
    tokenizer_snapshot.mkdir(parents=True)
    (tokenizer_snapshot / "tokenizer.fixture").write_text("byte", encoding="utf-8")
    request = PreparationRequest(
        stage="100k",
        repo_root=repo_root,
        data_root=data_root,
        tokenizer_snapshot=tokenizer_snapshot,
        output_root=repo_root / "build/foundation/preparation/100k",
    )
    return request


def _result_files(result) -> tuple[Path, ...]:
    return tuple(Path(getattr(result, field)) for field in result.__dataclass_fields__)


def _make_directory_alias(link: Path, target: Path) -> None:
    if os.name == "nt":
        result = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            pytest.skip(f"directory junctions unavailable: {result.stderr.strip()}")
        return
    try:
        link.symlink_to(target, target_is_directory=True)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def test_prepare_stage_is_repeatable_zero_weight_and_fully_receipted(
    tmp_path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import preparation

    request = _prepare_fixture(tmp_path)
    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())
    first = preparation.prepare_stage(request)
    first_bytes = {path: path.read_bytes() for path in _result_files(first)}

    def reject_reconversion(*args, **kwargs):
        raise AssertionError("complete byte-identical conversion should be reused")

    monkeypatch.setattr(
        preparation.openhands_converter,
        "run_verified_stream_conversion",
        reject_reconversion,
    )
    second = preparation.prepare_stage(request)

    assert first == second
    assert first_bytes == {path: path.read_bytes() for path in _result_files(second)}
    records = [
        json.loads(line)
        for line in first.shard_path.read_text(encoding="utf-8").splitlines()
    ]
    assert records
    assert all(record["training_weight"] == 0.0 for record in records)
    assert {record["observations"]["labels"]["resolved"] for record in records} == {
        False,
        True,
    }
    assert sum(record["tokenization"]["total_tokens"] for record in records) <= 100_000

    selection = json.loads(first.selection_receipt_path.read_text(encoding="utf-8"))
    recounted = sum(
        len(record["rendered"]["prompt_text"].encode("utf-8"))
        + len(record["rendered"]["target_text"].encode("utf-8"))
        for record in records
    )
    assert selection["selected_token_count"] == recounted
    assert selection["tokenizer_recount_total"] == recounted

    suite = json.loads(first.suite_report_path.read_text(encoding="utf-8"))
    assert [item["family"] for item in suite["families"]] == list(
        ACTIVE_DATASET_GROUPS
    )
    assert all(item["exists"] for item in suite["families"])
    contamination = json.loads(
        first.contamination_receipt_path.read_text(encoding="utf-8")
    )
    assert contamination["evaluation_coverage_complete"] is True
    assert contamination["finding_count"] == 0
    assert contamination["repo_issue_disjoint"] is True

    conversion_root = request.repo_root / "build/training_examples/openhands-sampled/full"
    expected_receipts = sorted(
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (
            conversion_root / "conversion_report.json",
            conversion_root / "hash_manifest.json",
            request.repo_root
            / "docs/data/license-receipts/swe-gym-openhands-sampled.local-research.json",
        )
    )
    assert all(record["source"]["receipt_hashes"] == expected_receipts for record in records)
    source_integrity = json.loads(
        first.source_integrity_receipt_path.read_text(encoding="utf-8")
    )
    assert source_integrity["unchanged"] is True
    assert source_integrity["before"] == source_integrity["after"]


def test_prepare_stage_uses_verified_streams_and_recovers_partial_outputs(
    tmp_path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import preparation

    request = _prepare_fixture(tmp_path)
    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())
    protected = request.data_root.resolve()
    real_open = Path.open

    def reject_protected_path_open(path: Path, *args, **kwargs):
        resolved = path.resolve(strict=False)
        if resolved == protected or protected in resolved.parents:
            raise AssertionError("protected payload was reopened by path")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", reject_protected_path_open)
    result = preparation.prepare_stage(request)
    conversion_root = request.repo_root / "build/training_examples/openhands-sampled/full"
    (conversion_root / "conversion_report.json").write_bytes(b"partial")
    (conversion_root / "orphan.tmp").write_bytes(b"partial")

    repaired = preparation.prepare_stage(request)
    report = json.loads((conversion_root / "conversion_report.json").read_text())
    assert repaired.shard_path.read_bytes() == result.shard_path.read_bytes()
    assert report["count_reconciliation"]["reconciled"] is True


def test_prepare_stage_dry_run_validates_without_writing(tmp_path, monkeypatch) -> None:
    from pneuma_lab.foundation import preparation

    request = _prepare_fixture(tmp_path)
    request = preparation.PreparationRequest(
        **{**request.__dict__, "dry_run": True}
    )
    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())
    result = preparation.prepare_stage(request)

    assert not request.output_root.exists()
    assert not (request.repo_root / "build/training_examples").exists()
    assert all(not path.exists() for path in _result_files(result))


def test_prepare_stage_denies_invalid_suite_before_any_output(tmp_path, monkeypatch) -> None:
    from pneuma_lab.foundation import preparation

    request = _prepare_fixture(tmp_path)
    suite_path = (
        request.repo_root
        / "docs/data/training-readiness/pneuma-foundation-v0-suite.json"
    )
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    suite["families"][0]["payload_access_100k"] = "approved_processed_lane_only"
    suite_path.write_text(json.dumps(suite), encoding="utf-8")
    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())

    with pytest.raises(ValueError, match="suite|policy"):
        preparation.prepare_stage(request)
    assert not request.output_root.exists()
    assert not (request.repo_root / "build/training_examples").exists()


def test_prepare_stage_rejects_missing_eval_coverage_before_writes(
    tmp_path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import preparation

    request = _prepare_fixture(tmp_path)
    (request.data_root / "processed/swe-mera/normalized_metadata.jsonl").write_bytes(
        b""
    )
    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())

    with pytest.raises(ValueError, match="at least one|empty|identity"):
        preparation.prepare_stage(request)
    assert not request.output_root.exists()
    assert not (request.repo_root / "build/training_examples").exists()


def test_prepare_stage_rejects_output_alias_before_source_reads(
    tmp_path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import preparation

    request = _prepare_fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    request.output_root.parent.mkdir(parents=True)
    _make_directory_alias(request.output_root, outside)
    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())

    with pytest.raises(ValueError, match="link|junction|reparse|output"):
        preparation.prepare_stage(request)
    assert tuple(outside.iterdir()) == ()
    assert not (request.repo_root / "build/training_examples").exists()


def test_prepare_stage_rejects_duplicate_registry_json_before_writes(
    tmp_path,
    monkeypatch,
) -> None:
    from pneuma_lab.foundation import preparation

    request = _prepare_fixture(tmp_path)
    registry_path = (
        request.repo_root / "docs/data/training-readiness/dataset-registry.json"
    )
    payload = registry_path.read_text(encoding="utf-8")
    registry_path.write_text(
        payload.replace(
            '"registry_schema_version": "0.1.0",',
            '"registry_schema_version": "0.1.0",'
            '"registry_schema_version": "0.1.0",',
            1,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(preparation, "_load_tokenizer", lambda path: ByteTokenizer())

    with pytest.raises(ValueError, match="duplicate"):
        preparation.prepare_stage(request)
    assert not request.output_root.exists()


def test_preparation_module_has_no_training_execution_dependencies() -> None:
    source = (
        ROOT / "src/pneuma_lab/foundation/preparation.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "foundation.optimizer",
        "foundation.runner",
        "load_local_qwen",
    ):
        assert forbidden not in source
