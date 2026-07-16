"""Hash-verified shards, deterministic sampling, and one-document collation."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

from pneuma_lab.foundation.core import FORECAST_TARGETS  # noqa: E402
from pneuma_lab.foundation.dataset import (  # noqa: E402
    DeterministicSampler,
    FoundationCollator,
    FoundationDatasetError,
    FoundationShardDataset,
)
from pneuma_lab.foundation.records import (  # noqa: E402
    _make_effective_training_record,
)


class CountingTokenizer:
    """Byte-level tokenizer double with an inspectable encode-call count."""

    eos_token_id = 1

    def __init__(self) -> None:
        self.encode_calls = 0

    def encode(self, text: str, add_special_tokens: bool) -> list[int]:
        self.encode_calls += 1
        ids = [byte + 2 for byte in text.encode("utf-8")]
        if add_special_tokens:
            return [0, *ids]
        return ids


@pytest.fixture
def tokenizer() -> CountingTokenizer:
    return CountingTokenizer()


def _record(
    example_id: str = "ex-1",
    *,
    prompt_text: str = "prompt",
    target_text: str = "target",
) -> dict:
    return {
        "record_kind": "pneuma_foundation_training_record",
        "record_schema_version": "0.1.0",
        "record_id": "ftr:" + hashlib.sha256(example_id.encode("utf-8")).hexdigest(),
        "source": {
            "dataset_family": "swe-gym",
            "lane_id": "swe-gym-openhands-sampled",
            "source_record_id": example_id,
            "source_revision": None,
            "receipt_hashes": [],
        },
        "disposition": {
            "terminal_role": "train",
            "gradient_eligibility": "first_stage",
            "license_disposition": "reviewed",
            "privacy_disposition": "reviewed",
            "dual_use_disposition": "not_flagged",
            "oracle_disposition": "target_only",
        },
        "identity": {
            "repo": "org/repo",
            "issue_or_pr": "123",
            "task_id": "task-123",
            "base_commit": "abc",
            "patch_sha256": "sha256:" + "a" * 64,
            "test_patch_sha256": "b" * 64,
            "fuzzy_text_sha256": "c" * 64,
        },
        "split": {"split_id": "train", "quarantine_id": None},
        "rendered": {"prompt_text": prompt_text, "target_text": target_text},
        "tokenization": {
            "tokenizer_id": "Qwen/Qwen3.5-2B",
            "tokenizer_revision": "d" * 40,
            "prompt_tokens": 4,
            "target_tokens": 2,
            "total_tokens": 6,
        },
        "training_weight": 0.0,
        "forecast_targets": {
            "action_success": {
                "applicable": True,
                "value": 1.0,
                "provenance": "observed_outcome",
            },
            "expected_error": {
                "applicable": True,
                "value": 0.0,
                "provenance": "observed_outcome",
            },
            **{
                name: {"applicable": False, "value": None, "provenance": None}
                for name in FORECAST_TARGETS
                if name not in ("action_success", "expected_error")
            },
        },
        "observations": {
            "language": "python",
            "tools": ["shell", "pytest"],
            "trajectory_length": 8,
            "labels": {"resolved": True},
        },
    }


def _effective_record(weight: float = 1.0, **overrides):
    return _make_effective_training_record(
        _record(**overrides),
        effective_weight=weight,
    )


def _write_zero_weight_shard(tmp_path: Path) -> tuple[Path, Path]:
    records = [_record("ex-1"), _record("ex-2")]
    lines = [
        json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        for record in records
    ]
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    shard = tmp_path / f"{digest}.jsonl"
    shard.write_bytes(payload)
    manifest = tmp_path / f"{digest}.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_kind": "pneuma_foundation_shard",
                "schema_version": "0.1.0",
                "sha256": digest,
                "example_count": len(records),
                "duplicate_example_ids": [],
                "source_policy": "read_only_external_corpus",
            },
            indent=4,
        )
        + "\n",
        encoding="utf-8",
    )
    return shard, manifest


def test_collator_masks_prompt_and_preserves_one_document(tokenizer) -> None:
    batch = FoundationCollator(tokenizer, sequence_length=512)([_effective_record()])
    assert batch.document_count == 1
    assert batch.input_ids.shape[0] == 1
    assert (batch.labels[0, : batch.prompt_length] == -100).all()
    assert batch.forecast_masks["action_success"].item() is True


def test_collator_supervises_target_and_appends_eos(tokenizer) -> None:
    batch = FoundationCollator(tokenizer, sequence_length=512)([_effective_record()])
    target_ids = tokenizer.encode("target", add_special_tokens=False) + [
        tokenizer.eos_token_id
    ]
    prompt_ids = tokenizer.encode("prompt", add_special_tokens=True)
    assert batch.prompt_length == len(prompt_ids)
    assert batch.token_count == len(prompt_ids) + len(target_ids)
    assert batch.input_ids.shape == (1, batch.token_count)
    assert batch.attention_mask.shape == (1, batch.token_count)
    assert batch.input_ids[0, batch.prompt_length :].tolist() == target_ids
    assert batch.labels[0, batch.prompt_length :].tolist() == target_ids
    assert batch.effective_weight.item() == 1.0


def test_collator_truncates_target_to_sequence_length_and_keeps_eos(
    tokenizer,
) -> None:
    effective = _effective_record(target_text="x" * 64)
    batch = FoundationCollator(tokenizer, sequence_length=16)([effective])
    assert batch.token_count == 16
    assert batch.prompt_length == 0
    assert batch.input_ids.shape == (1, 16)
    assert batch.input_ids[0, -1].item() == tokenizer.eos_token_id


def test_collator_truncates_prompt_but_never_target(tokenizer) -> None:
    effective = _effective_record(prompt_text="p" * 100, target_text="ok")
    batch = FoundationCollator(tokenizer, sequence_length=16)([effective])
    target_ids = tokenizer.encode("ok", add_special_tokens=False) + [
        tokenizer.eos_token_id
    ]
    assert batch.token_count == 16
    assert batch.prompt_length == 16 - len(target_ids)
    assert batch.labels[0, : batch.prompt_length].eq(-100).all()
    assert batch.input_ids[0, batch.prompt_length :].tolist() == target_ids
    assert batch.labels[0, batch.prompt_length :].tolist() == target_ids


def test_collator_rejects_multi_document_batches_before_tokenizing(
    tokenizer,
) -> None:
    collator = FoundationCollator(tokenizer, sequence_length=32)
    with pytest.raises(FoundationDatasetError, match="one authorized document"):
        collator([_effective_record(), _effective_record()])
    assert tokenizer.encode_calls == 0


def test_collator_rejects_unauthorized_plain_records(tokenizer) -> None:
    collator = FoundationCollator(tokenizer, sequence_length=32)
    with pytest.raises(FoundationDatasetError, match="one authorized document"):
        collator([_record()])
    assert tokenizer.encode_calls == 0


def test_collator_rejects_empty_batches(tokenizer) -> None:
    collator = FoundationCollator(tokenizer, sequence_length=32)
    with pytest.raises(FoundationDatasetError, match="one authorized document"):
        collator([])
    assert tokenizer.encode_calls == 0


@pytest.mark.parametrize("sequence_length", (0, 1, -8, 2.0, True, None))
def test_collator_rejects_invalid_sequence_lengths(tokenizer, sequence_length) -> None:
    with pytest.raises(FoundationDatasetError, match="sequence_length"):
        FoundationCollator(tokenizer, sequence_length=sequence_length)


def test_collator_requires_integer_eos_token(tokenizer) -> None:
    tokenizer.eos_token_id = None
    collator = FoundationCollator(tokenizer, sequence_length=32)
    with pytest.raises(FoundationDatasetError, match="eos_token_id"):
        collator([_effective_record()])


def test_dataset_reads_records_in_shard_order(tmp_path: Path) -> None:
    shard, manifest = _write_zero_weight_shard(tmp_path)
    dataset = FoundationShardDataset(shard, manifest)
    assert len(dataset) == 2
    assert dataset[0]["source"]["source_record_id"] == "ex-1"
    assert dataset[1]["source"]["source_record_id"] == "ex-2"
    assert dataset.token_counts() == (6, 6)


def test_dataset_rejects_shard_hash_change(tmp_path: Path) -> None:
    shard, manifest = _write_zero_weight_shard(tmp_path)
    shard.write_text(shard.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    with pytest.raises(FoundationDatasetError, match="hash"):
        FoundationShardDataset(shard, manifest)


def test_dataset_rejects_manifest_without_digest(tmp_path: Path) -> None:
    shard, manifest = _write_zero_weight_shard(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    del payload["sha256"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FoundationDatasetError, match="sha256"):
        FoundationShardDataset(shard, manifest)


def test_dataset_rejects_example_count_mismatch(tmp_path: Path) -> None:
    shard, manifest = _write_zero_weight_shard(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["example_count"] = 3
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(FoundationDatasetError, match="example_count"):
        FoundationShardDataset(shard, manifest)


def test_dataset_rejects_unparseable_manifest(tmp_path: Path) -> None:
    shard, manifest = _write_zero_weight_shard(tmp_path)
    manifest.write_text("not json", encoding="utf-8")
    with pytest.raises(FoundationDatasetError, match="manifest"):
        FoundationShardDataset(shard, manifest)


def test_dataset_rejects_non_object_records(tmp_path: Path) -> None:
    payload = b"[1,2]\n"
    digest = hashlib.sha256(payload).hexdigest()
    shard = tmp_path / f"{digest}.jsonl"
    shard.write_bytes(payload)
    manifest = tmp_path / f"{digest}.manifest.json"
    manifest.write_text(
        json.dumps({"sha256": digest, "example_count": 1}),
        encoding="utf-8",
    )
    with pytest.raises(FoundationDatasetError, match="JSON object"):
        FoundationShardDataset(shard, manifest)


def test_sampler_permutation_matches_seeded_shuffle_per_epoch() -> None:
    expected = list(range(10))
    random.Random(7 + 2).shuffle(expected)
    assert DeterministicSampler(7, epoch=2).permutation(10) == tuple(expected)
    assert DeterministicSampler(7, epoch=2).permutation(10) == tuple(expected)
    assert DeterministicSampler(7, epoch=3).permutation(10) != tuple(expected)


def test_sampler_yields_complete_windows_and_skips_over_ceiling() -> None:
    sampler = DeterministicSampler(0, epoch=0)
    order = sampler.permutation(5)
    token_counts = [10, 10, 10, 10, 10]
    token_counts[order[2]] = 1000
    windows = list(
        sampler.iter_windows(
            token_counts,
            gradient_accumulation=2,
            token_ceiling=100,
        )
    )
    assert windows == [order[0:2]]
    assert sampler.cursor == 4


def test_sampler_never_starts_a_partial_window() -> None:
    sampler = DeterministicSampler(5, epoch=0)
    windows = list(
        sampler.iter_windows(
            [4, 4, 4],
            gradient_accumulation=2,
            token_ceiling=1_000,
        )
    )
    assert len(windows) == 1
    assert len(windows[0]) == 2
    assert sampler.cursor == 2


def test_sampler_cursor_resume_matches_uninterrupted_run() -> None:
    counts = [3, 4, 5, 6, 7, 8, 9, 10]
    full = DeterministicSampler(11, epoch=1)
    all_windows = list(
        full.iter_windows(counts, gradient_accumulation=2, token_ceiling=10_000)
    )
    assert len(all_windows) == 4

    first = DeterministicSampler(11, epoch=1)
    stream = first.iter_windows(counts, gradient_accumulation=2, token_ceiling=10_000)
    head = [next(stream)]
    tokens_seen = sum(counts[index] for index in head[0])
    resumed = DeterministicSampler(11, epoch=1, cursor=first.cursor)
    tail = list(
        resumed.iter_windows(
            counts,
            gradient_accumulation=2,
            token_ceiling=10_000,
            tokens_seen=tokens_seen,
        )
    )
    assert head + tail == all_windows
    assert resumed.cursor == full.cursor


@pytest.mark.parametrize(
    ("seed", "epoch", "cursor"),
    (
        (True, 0, 0),
        (0.5, 0, 0),
        (0, -1, 0),
        (0, 0.5, 0),
        (0, 0, -1),
        (0, 0, None),
    ),
)
def test_sampler_rejects_invalid_construction(seed, epoch, cursor) -> None:
    with pytest.raises(FoundationDatasetError):
        DeterministicSampler(seed, epoch=epoch, cursor=cursor)


@pytest.mark.parametrize(
    "kwargs",
    (
        {"gradient_accumulation": 0},
        {"gradient_accumulation": True},
        {"token_ceiling": 0},
        {"token_ceiling": None},
        {"tokens_seen": -1},
    ),
)
def test_sampler_rejects_invalid_window_arguments(kwargs) -> None:
    sampler = DeterministicSampler(3)
    arguments = {
        "gradient_accumulation": 2,
        "token_ceiling": 100,
        "tokens_seen": 0,
        **kwargs,
    }
    with pytest.raises(FoundationDatasetError):
        sampler.iter_windows([5, 5, 5, 5], **arguments)


@pytest.mark.parametrize("count", (0, -3, 2.5, True, None))
def test_sampler_rejects_invalid_token_counts(count) -> None:
    sampler = DeterministicSampler(3)
    with pytest.raises(FoundationDatasetError, match="token count"):
        sampler.iter_windows(
            [5, count],
            gradient_accumulation=1,
            token_ceiling=100,
        )
