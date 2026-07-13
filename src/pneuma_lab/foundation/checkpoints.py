"""Atomic PyTorch checkpoints with exact local resume and bounded retention."""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

try:
    import torch
except ImportError as exc:  # pragma: no cover - optional dependency boundary
    raise ImportError(
        "pneuma_lab.foundation.checkpoints requires the foundation torch extra"
    ) from exc


@dataclass(frozen=True)
class CheckpointSchedule:
    every_steps: int = 500
    every_seconds: int = 1_800

    def due(
        self,
        *,
        step: int,
        last_step: int,
        now: float,
        last_time: float,
    ) -> bool:
        return (
            step - last_step >= self.every_steps
            or now - last_time >= self.every_seconds
        )


class CheckpointManager:
    def __init__(self, root: Path, *, keep_last: int = 3) -> None:
        if keep_last < 1:
            raise ValueError("keep_last must be positive")
        self.root = Path(root)
        self.keep_last = keep_last
        self.index_path = self.root / "index.json"

    def _index(self) -> list[dict]:
        if not self.index_path.exists():
            return []
        value = json.loads(self.index_path.read_text(encoding="utf-8"))
        return list(value.get("checkpoints") or [])

    def _write_index(self, records: list[dict]) -> None:
        payload = (json.dumps({"checkpoints": records}, indent=4) + "\n").encode(
            "utf-8"
        )
        temporary = self.index_path.with_suffix(".json.tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, self.index_path)

    @staticmethod
    def _rng_state() -> dict:
        state = {
            "python": random.getstate(),
            "torch_cpu": torch.get_rng_state(),
        }
        if torch.cuda.is_available():
            state["torch_cuda"] = torch.cuda.get_rng_state_all()
        return state

    @staticmethod
    def _restore_rng(state: Mapping) -> None:
        random.setstate(state["python"])
        torch.set_rng_state(state["torch_cpu"])
        if "torch_cuda" in state and torch.cuda.is_available():
            torch.cuda.set_rng_state_all(state["torch_cuda"])

    def save(
        self,
        *,
        model,
        optimizer,
        progress: Mapping[str, int],
        validation_score: float,
    ) -> Path:
        step = int(progress["step"])
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"checkpoint-{step:08d}.pt"
        temporary = path.with_suffix(".pt.tmp")
        torch.save(
            {
                "format": "pneuma-foundation-checkpoint/0.1.0",
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "progress": dict(progress),
                "rng": self._rng_state(),
                "validation_score": float(validation_score),
            },
            temporary,
        )
        os.replace(temporary, path)

        records = [record for record in self._index() if record["step"] != step]
        records.append(
            {
                "step": step,
                "path": path.name,
                "validation_score": float(validation_score),
            }
        )
        records.sort(key=lambda item: item["step"])
        best = max(records, key=lambda item: (item["validation_score"], -item["step"]))
        keep_steps = {record["step"] for record in records[-self.keep_last :]}
        keep_steps.add(best["step"])
        retained = [record for record in records if record["step"] in keep_steps]
        for record in records:
            if record["step"] not in keep_steps:
                candidate = self.root / record["path"]
                if candidate.exists():
                    candidate.unlink()
        self._write_index(retained)
        return path

    def load(self, path: Path, *, model, optimizer) -> dict:
        payload = torch.load(Path(path), map_location="cpu", weights_only=False)
        if payload.get("format") != "pneuma-foundation-checkpoint/0.1.0":
            raise ValueError("unsupported checkpoint format")
        model.load_state_dict(payload["model"])
        optimizer.load_state_dict(payload["optimizer"])
        self._restore_rng(payload["rng"])
        return dict(payload["progress"])
