"""Hash-verified shard reading, deterministic sampling, and one-document batches.

This module is the fail-closed input seam for the local foundation trainer.
Shard bytes must match their manifest digest before a single record is
exposed, every microbatch carries exactly one authorization-sealed document,
and sampling is a pure function of ``(seed, epoch, cursor)`` so a checkpointed
run resumes bit-for-bit. Torch is imported lazily so hash verification and
sampling stay usable on import-light paths.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from pneuma_lab.foundation.records import EffectiveTrainingRecord

if TYPE_CHECKING:  # pragma: no cover - typing-only import
    from torch import Tensor


class FoundationDatasetError(ValueError):
    """Raised before training when shard bytes or batch boundaries are unsafe."""


@dataclass(frozen=True)
class FoundationBatch:
    """One collated single-document microbatch with its authorized weight."""

    input_ids: Tensor
    attention_mask: Tensor
    labels: Tensor
    forecast_targets: Mapping[str, Tensor]
    forecast_masks: Mapping[str, Tensor]
    effective_weight: Tensor
    token_count: int
    prompt_length: int
    document_count: int = 1


class FoundationShardDataset:
    """Read one immutable JSONL shard only after its manifest digest verifies.

    The shard bytes are read exactly once; the digest is computed over those
    same bytes so the parsed records are provably the hashed records. The
    whole shard stays resident in memory by design (single-read verification
    plus random access under a permutation require it) — roughly 1 GiB of
    parsed records at the largest 32m stage.
    """

    def __init__(self, shard_path: Path, manifest_path: Path) -> None:
        self.shard_path = Path(shard_path)
        self.manifest_path = Path(manifest_path)
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise FoundationDatasetError(
                f"shard manifest cannot be read: {exc}"
            ) from exc
        if not isinstance(manifest, Mapping):
            raise FoundationDatasetError("shard manifest must be a JSON object")
        expected_digest = manifest.get("sha256")
        if not isinstance(expected_digest, str) or not expected_digest:
            raise FoundationDatasetError("shard manifest sha256 digest is missing")
        try:
            payload = self.shard_path.read_bytes()
        except OSError as exc:
            raise FoundationDatasetError(f"shard cannot be read: {exc}") from exc
        if hashlib.sha256(payload).hexdigest() != expected_digest:
            raise FoundationDatasetError("shard hash does not match manifest")
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise FoundationDatasetError(
                f"shard bytes are not valid UTF-8: {exc}"
            ) from exc
        records = []
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise FoundationDatasetError(
                    f"shard line is not valid JSON: {exc}"
                ) from exc
            if not isinstance(record, dict):
                raise FoundationDatasetError("shard records must be JSON objects")
            records.append(record)
        example_count = manifest.get("example_count")
        if type(example_count) is not int or example_count != len(records):
            raise FoundationDatasetError(
                "shard manifest example_count does not match its records"
            )
        self.records: tuple[dict, ...] = tuple(records)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict:
        return self.records[index]

    def token_counts(self) -> tuple[int, ...]:
        """Return each record's pinned-tokenizer total token count."""

        counts = []
        for record in self.records:
            tokenization = record.get("tokenization")
            total = (
                tokenization.get("total_tokens")
                if isinstance(tokenization, Mapping)
                else None
            )
            if type(total) is not int or total <= 0:
                raise FoundationDatasetError(
                    "shard records require positive integer total_tokens"
                )
            counts.append(total)
        return tuple(counts)


def _validated_nonnegative_int(value, *, name: str) -> int:
    if type(value) is not int or value < 0:
        raise FoundationDatasetError(f"sampler {name} must be a nonnegative int")
    return value


class DeterministicSampler:
    """Deterministic permutation and windowing over shard record indices.

    The permutation is ``random.Random(seed + epoch).shuffle(indices)`` and the
    ``cursor`` is a position in that permutation, checkpointed as
    ``dataset_cursor`` so a resumed run continues exactly. Microbatches are
    grouped into complete accumulation windows before a window starts; a window
    whose token sum would cross the authorized ceiling is skipped entirely, so
    the run never leaves pending gradients and never exceeds the cap.

    Keep at most one active window iterator per sampler — iteration mutates
    the shared ``cursor``. The cursor never resets; construct a fresh sampler
    for each new epoch.
    """

    def __init__(self, seed: int, epoch: int = 0, cursor: int = 0) -> None:
        if type(seed) is not int:
            raise FoundationDatasetError("sampler seed must be an int")
        self.seed = seed
        self.epoch = _validated_nonnegative_int(epoch, name="epoch")
        self.cursor = _validated_nonnegative_int(cursor, name="cursor")

    def permutation(self, length: int) -> tuple[int, ...]:
        """Return the epoch permutation of ``range(length)``."""

        length = _validated_nonnegative_int(length, name="length")
        indices = list(range(length))
        random.Random(self.seed + self.epoch).shuffle(indices)
        return tuple(indices)

    def iter_windows(
        self,
        token_counts: Sequence[int],
        *,
        gradient_accumulation: int,
        token_ceiling: int,
        tokens_seen: int = 0,
    ) -> Iterator[tuple[int, ...]]:
        """Yield complete accumulation windows that stay under the ceiling.

        Arguments are validated eagerly; the returned iterator advances
        ``self.cursor`` past each complete window it visits, whether the
        window is yielded or skipped for crossing the remaining ceiling.
        A trailing partial group is never started.
        """

        counts = tuple(token_counts)
        for count in counts:
            if type(count) is not int or count <= 0:
                raise FoundationDatasetError(
                    "sampler token counts must be positive ints"
                )
        if type(gradient_accumulation) is not int or gradient_accumulation < 1:
            raise FoundationDatasetError(
                "sampler gradient_accumulation must be a positive int"
            )
        if type(token_ceiling) is not int or token_ceiling <= 0:
            raise FoundationDatasetError("sampler token_ceiling must be a positive int")
        tokens_seen = _validated_nonnegative_int(tokens_seen, name="tokens_seen")
        order = self.permutation(len(counts))

        def windows() -> Iterator[tuple[int, ...]]:
            tokens_used = tokens_seen
            while self.cursor + gradient_accumulation <= len(order):
                window = order[self.cursor : self.cursor + gradient_accumulation]
                window_tokens = sum(counts[index] for index in window)
                self.cursor += gradient_accumulation
                if tokens_used + window_tokens > token_ceiling:
                    continue
                tokens_used += window_tokens
                yield window

        return windows()


class FoundationCollator:
    """Collate exactly one authorization-sealed document per microbatch."""

    def __init__(self, tokenizer, *, sequence_length: int = 512) -> None:
        if type(sequence_length) is not int or sequence_length < 2:
            raise FoundationDatasetError(
                "sequence_length must be an int of at least two"
            )
        self.tokenizer = tokenizer
        self.sequence_length = sequence_length

    def __call__(self, records: Sequence) -> FoundationBatch:
        if len(records) != 1 or not isinstance(records[0], EffectiveTrainingRecord):
            raise FoundationDatasetError(
                "each microbatch must contain one authorized document"
            )
        import torch

        from pneuma_lab.foundation.optimizer import forecast_tensors

        effective = records[0]
        eos_token_id = getattr(self.tokenizer, "eos_token_id", None)
        if type(eos_token_id) is not int or eos_token_id < 0:
            raise FoundationDatasetError(
                "tokenizer must expose a nonnegative integer eos_token_id"
            )
        rendered = effective.record.get("rendered")
        prompt_text = (
            rendered.get("prompt_text") if isinstance(rendered, Mapping) else None
        )
        target_text = (
            rendered.get("target_text") if isinstance(rendered, Mapping) else None
        )
        if not isinstance(prompt_text, str) or not isinstance(target_text, str):
            raise FoundationDatasetError("authorized record rendered text is malformed")
        prompt_ids = list(self.tokenizer.encode(prompt_text, add_special_tokens=True))
        target_ids = list(
            self.tokenizer.encode(target_text, add_special_tokens=False)
        ) + [eos_token_id]
        if len(target_ids) >= self.sequence_length:
            target_ids = target_ids[: self.sequence_length - 1] + [eos_token_id]
        prompt_ids = prompt_ids[: self.sequence_length - len(target_ids)]
        ids = prompt_ids + target_ids
        prompt_length = len(prompt_ids)
        labels = [-100] * prompt_length + ids[prompt_length:]
        targets, masks = forecast_tensors(effective.record)
        return FoundationBatch(
            input_ids=torch.tensor([ids]),
            attention_mask=torch.ones((1, len(ids)), dtype=torch.long),
            labels=torch.tensor([labels]),
            forecast_targets=targets,
            forecast_masks=masks,
            effective_weight=torch.tensor([effective.effective_weight]),
            token_count=len(ids),
            prompt_length=prompt_length,
        )


__all__ = [
    "DeterministicSampler",
    "FoundationBatch",
    "FoundationCollator",
    "FoundationDatasetError",
    "FoundationShardDataset",
]
