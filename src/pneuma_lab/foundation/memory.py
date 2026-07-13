"""SQLite/FTS5 persistent memory with provenance and genuine hard erasure."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


class MemoryIntegrityError(ValueError):
    """Raised when consolidation or erasure provenance is inconsistent."""


@dataclass(frozen=True)
class ErasureReceipt:
    receipt_id: str
    revoked_adapters: tuple[str, ...]
    rebuild_from_checkpoint: str | None
    removed: dict[str, int]
    deleted_at: str

    def to_dict(self) -> dict:
        return {
            "receipt_kind": "pneuma_memory_hard_erasure",
            "receipt_schema_version": "0.1.0",
            "receipt_id": self.receipt_id,
            "deleted_at": self.deleted_at,
            "payload_retained": False,
            "removed": dict(self.removed),
            "revoked_adapters": list(self.revoked_adapters),
            "rebuild_from_checkpoint": self.rebuild_from_checkpoint,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class LocalMemoryStore:
    """Four local stores: recurrent state, events, knowledge, and lineage."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.content_root = self.root / "content"
        self.content_root.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.root / "memory.sqlite3")
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def __enter__(self) -> "LocalMemoryStore":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS lineage (
                era TEXT PRIMARY KEY,
                parent_era TEXT,
                checkpoint TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                receipt_id TEXT PRIMARY KEY,
                payload_hash TEXT NOT NULL,
                payload_path TEXT NOT NULL,
                era TEXT NOT NULL REFERENCES lineage(era),
                provenance_json TEXT NOT NULL,
                uncertainty REAL NOT NULL CHECK(uncertainty >= 0 AND uncertainty <= 1),
                suppressed INTEGER NOT NULL DEFAULT 0,
                suppression_reason TEXT,
                created_at TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS event_search
                USING fts5(receipt_id UNINDEXED, text);
            CREATE TABLE IF NOT EXISTS active_recurrent_state (
                state_key TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS embeddings (
                receipt_id TEXT NOT NULL REFERENCES events(receipt_id) ON DELETE CASCADE,
                content_path TEXT NOT NULL,
                sha256 TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS summaries (
                receipt_id TEXT NOT NULL REFERENCES events(receipt_id) ON DELETE CASCADE,
                summary TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_links (
                source_receipt TEXT NOT NULL REFERENCES events(receipt_id) ON DELETE CASCADE,
                target_receipt TEXT NOT NULL REFERENCES events(receipt_id) ON DELETE CASCADE,
                relation TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS encryption_keys (
                receipt_id TEXT PRIMARY KEY REFERENCES events(receipt_id) ON DELETE CASCADE,
                key_material BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS semantic_knowledge (
                knowledge_id TEXT PRIMARY KEY,
                knowledge_kind TEXT NOT NULL,
                claim TEXT NOT NULL,
                source_receipts_json TEXT NOT NULL,
                contradictions_json TEXT NOT NULL,
                uncertainty REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS adapters (
                adapter_id TEXT PRIMARY KEY,
                era TEXT NOT NULL REFERENCES lineage(era),
                source_receipts_json TEXT NOT NULL,
                status TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS erasures (
                receipt_id TEXT PRIMARY KEY,
                payload_hash TEXT NOT NULL,
                deleted_at TEXT NOT NULL,
                payload_retained INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        columns = {
            row["name"]
            for row in self.connection.execute("PRAGMA table_info(semantic_knowledge)")
        }
        if "knowledge_kind" not in columns:
            self.connection.execute(
                "ALTER TABLE semantic_knowledge "
                "ADD COLUMN knowledge_kind TEXT NOT NULL DEFAULT 'semantic'"
            )
        self.connection.commit()

    def record_lineage(
        self,
        era: str,
        *,
        parent_era: str | None,
        checkpoint: str,
    ) -> None:
        if parent_era is not None:
            parent = self.connection.execute(
                "SELECT era FROM lineage WHERE era = ?", (parent_era,)
            ).fetchone()
            if parent is None:
                raise MemoryIntegrityError(f"unknown parent era: {parent_era}")
        with self.connection:
            self.connection.execute(
                "INSERT INTO lineage(era, parent_era, checkpoint, created_at) "
                "VALUES (?, ?, ?, ?)",
                (era, parent_era, checkpoint, _now()),
            )

    def _write_content(self, payload: bytes, suffix: str) -> Path:
        digest = _sha256(payload)
        path = self.content_root / f"{digest}.{suffix}"
        if not path.exists():
            path.write_bytes(payload)
        return path

    def append_event(
        self,
        payload: str,
        *,
        era: str,
        provenance: dict | None = None,
        uncertainty: float = 0.0,
    ) -> str:
        if not 0.0 <= uncertainty <= 1.0:
            raise MemoryIntegrityError("uncertainty must be between zero and one")
        encoded = payload.encode("utf-8")
        path = self._write_content(encoded, "event")
        receipt_id = f"mem-{uuid.uuid4().hex}"
        with self.connection:
            self.connection.execute(
                "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, 0, NULL, ?)",
                (
                    receipt_id,
                    _sha256(encoded),
                    str(path),
                    era,
                    json.dumps(provenance or {}, sort_keys=True),
                    uncertainty,
                    _now(),
                ),
            )
            self.connection.execute(
                "INSERT INTO event_search(receipt_id, text) VALUES (?, ?)",
                (receipt_id, payload),
            )
        return receipt_id

    def set_active_state(self, state_key: str, value: dict) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO active_recurrent_state VALUES (?, ?, ?) "
                "ON CONFLICT(state_key) DO UPDATE SET "
                "state_json = excluded.state_json, updated_at = excluded.updated_at",
                (state_key, json.dumps(value, sort_keys=True), _now()),
            )

    def get_active_state(self, state_key: str) -> dict | None:
        row = self.connection.execute(
            "SELECT state_json FROM active_recurrent_state WHERE state_key = ?",
            (state_key,),
        ).fetchone()
        return None if row is None else json.loads(row["state_json"])

    def _event_row(self, receipt_id: str):
        return self.connection.execute(
            "SELECT * FROM events WHERE receipt_id = ?", (receipt_id,)
        ).fetchone()

    def read_event(
        self,
        receipt_id: str,
        *,
        include_suppressed: bool = False,
    ) -> dict | None:
        row = self._event_row(receipt_id)
        if row is None or (row["suppressed"] and not include_suppressed):
            return None
        return {
            "receipt_id": receipt_id,
            "payload": Path(row["payload_path"]).read_text(encoding="utf-8"),
            "era": row["era"],
            "provenance": json.loads(row["provenance_json"]),
            "uncertainty": row["uncertainty"],
            "suppressed": bool(row["suppressed"]),
        }

    def search(self, query: str) -> list[dict]:
        rows = self.connection.execute(
            "SELECT receipt_id FROM event_search WHERE event_search MATCH ? "
            "ORDER BY rank",
            (query,),
        ).fetchall()
        return [
            event
            for row in rows
            if (event := self.read_event(row["receipt_id"])) is not None
        ]

    def suppress(self, receipt_id: str, *, reason: str) -> None:
        if self._event_row(receipt_id) is None:
            raise MemoryIntegrityError(f"unknown receipt: {receipt_id}")
        with self.connection:
            self.connection.execute(
                "UPDATE events SET suppressed = 1, suppression_reason = ? "
                "WHERE receipt_id = ?",
                (reason, receipt_id),
            )
            self.connection.execute(
                "DELETE FROM event_search WHERE receipt_id = ?", (receipt_id,)
            )

    def unsuppress(self, receipt_id: str) -> None:
        event = self.read_event(receipt_id, include_suppressed=True)
        if event is None:
            raise MemoryIntegrityError(f"unknown receipt: {receipt_id}")
        with self.connection:
            self.connection.execute(
                "UPDATE events SET suppressed = 0, suppression_reason = NULL "
                "WHERE receipt_id = ?",
                (receipt_id,),
            )
            self.connection.execute(
                "DELETE FROM event_search WHERE receipt_id = ?", (receipt_id,)
            )
            self.connection.execute(
                "INSERT INTO event_search(receipt_id, text) VALUES (?, ?)",
                (receipt_id, event["payload"]),
            )

    def meta_memory(self, receipt_id: str) -> dict:
        row = self._event_row(receipt_id)
        if row is None:
            raise MemoryIntegrityError(f"unknown receipt: {receipt_id}")
        return {
            "receipt_id": receipt_id,
            "provenance": json.loads(row["provenance_json"]),
            "uncertainty": row["uncertainty"],
            "suppressed": bool(row["suppressed"]),
            "suppression_reason": row["suppression_reason"],
        }

    def autobiographical_view(self, *, era: str | None = None) -> list[dict]:
        """Derive autobiography from episodic events and lineage; store no copy."""

        if era is None:
            rows = self.connection.execute(
                "SELECT receipt_id FROM events WHERE suppressed = 0 "
                "ORDER BY created_at, receipt_id"
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT receipt_id FROM events WHERE suppressed = 0 AND era = ? "
                "ORDER BY created_at, receipt_id",
                (era,),
            ).fetchall()
        events = []
        for row in rows:
            event = self.read_event(row["receipt_id"])
            if event is not None:
                events.append(
                    {
                        "receipt_id": event["receipt_id"],
                        "era": event["era"],
                        "payload": event["payload"],
                        "provenance": event["provenance"],
                        "uncertainty": event["uncertainty"],
                    }
                )
        return events

    def add_derived_artifacts(
        self,
        receipt_id: str,
        *,
        embedding: bytes,
        summary: str,
        encryption_key: bytes,
    ) -> tuple[Path, ...]:
        if self._event_row(receipt_id) is None:
            raise MemoryIntegrityError(f"unknown receipt: {receipt_id}")
        embedding_path = self._write_content(embedding, "embedding")
        with self.connection:
            self.connection.execute(
                "INSERT INTO embeddings VALUES (?, ?, ?)",
                (receipt_id, str(embedding_path), _sha256(embedding)),
            )
            self.connection.execute(
                "INSERT INTO summaries VALUES (?, ?)", (receipt_id, summary)
            )
            self.connection.execute(
                "INSERT OR REPLACE INTO encryption_keys VALUES (?, ?)",
                (receipt_id, encryption_key),
            )
        event_path = Path(self._event_row(receipt_id)["payload_path"])
        return event_path, embedding_path

    def link(self, source: str, target: str, *, relation: str) -> None:
        if self._event_row(source) is None or self._event_row(target) is None:
            raise MemoryIntegrityError("memory links require two valid receipts")
        with self.connection:
            self.connection.execute(
                "INSERT INTO memory_links VALUES (?, ?, ?)",
                (source, target, relation),
            )

    def _valid_source_receipts(self, receipts: Iterable[str]) -> list[str]:
        values = sorted(set(receipts))
        if not values:
            raise MemoryIntegrityError("at least one source receipt is required")
        for receipt in values:
            row = self._event_row(receipt)
            if row is None or row["suppressed"]:
                raise MemoryIntegrityError(f"invalid source receipt: {receipt}")
        return values

    def consolidate(
        self,
        *,
        claim: str,
        source_receipts: Iterable[str],
        contradictions: Iterable[str],
        uncertainty: float,
        knowledge_kind: str = "semantic",
    ) -> dict:
        sources = self._valid_source_receipts(source_receipts)
        contradiction_values = sorted(set(contradictions))
        if not set(contradiction_values).issubset(set(sources)):
            raise MemoryIntegrityError("contradictions must reference source receipts")
        if not 0.0 <= uncertainty <= 1.0:
            raise MemoryIntegrityError("uncertainty must be between zero and one")
        if knowledge_kind not in {"semantic", "procedural"}:
            raise MemoryIntegrityError("knowledge_kind must be semantic or procedural")
        knowledge_id = f"knowledge-{uuid.uuid4().hex}"
        with self.connection:
            self.connection.execute(
                "INSERT INTO semantic_knowledge(knowledge_id, knowledge_kind, claim, "
                "source_receipts_json, contradictions_json, uncertainty, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    knowledge_id,
                    knowledge_kind,
                    claim,
                    json.dumps(sources),
                    json.dumps(contradiction_values),
                    uncertainty,
                    _now(),
                ),
            )
        return {
            "knowledge_id": knowledge_id,
            "knowledge_kind": knowledge_kind,
            "claim": claim,
            "source_receipts": sources,
            "contradictions": contradiction_values,
            "uncertainty": uncertainty,
        }

    def register_adapter(
        self,
        adapter_id: str,
        *,
        era: str,
        source_receipts: Iterable[str],
    ) -> None:
        sources = self._valid_source_receipts(source_receipts)
        with self.connection:
            self.connection.execute(
                "INSERT INTO adapters VALUES (?, ?, ?, 'active')",
                (adapter_id, era, json.dumps(sources)),
            )

    def adapter_status(self, adapter_id: str) -> str | None:
        row = self.connection.execute(
            "SELECT status FROM adapters WHERE adapter_id = ?", (adapter_id,)
        ).fetchone()
        return None if row is None else str(row["status"])

    def _safe_unlink_unreferenced(self, path: Path) -> None:
        event_count = self.connection.execute(
            "SELECT COUNT(*) FROM events WHERE payload_path = ?", (str(path),)
        ).fetchone()[0]
        embedding_count = self.connection.execute(
            "SELECT COUNT(*) FROM embeddings WHERE content_path = ?", (str(path),)
        ).fetchone()[0]
        if event_count == 0 and embedding_count == 0 and path.exists():
            path.unlink()

    def hard_delete(self, receipt_id: str) -> ErasureReceipt:
        row = self._event_row(receipt_id)
        if row is None:
            raise MemoryIntegrityError(f"unknown receipt: {receipt_id}")
        content_paths = [Path(row["payload_path"])]
        content_paths.extend(
            Path(item["content_path"])
            for item in self.connection.execute(
                "SELECT content_path FROM embeddings WHERE receipt_id = ?",
                (receipt_id,),
            )
        )
        adapter_rows = self.connection.execute(
            "SELECT adapter_id, era, source_receipts_json FROM adapters "
            "WHERE status = 'active'"
        ).fetchall()
        affected = [
            item
            for item in adapter_rows
            if receipt_id in json.loads(item["source_receipts_json"])
        ]
        semantic_rows = self.connection.execute(
            "SELECT knowledge_id, source_receipts_json FROM semantic_knowledge"
        ).fetchall()
        semantic_ids = [
            item["knowledge_id"]
            for item in semantic_rows
            if receipt_id in json.loads(item["source_receipts_json"])
        ]
        rebuild_checkpoints: list[str] = []
        removed = {
            "payloads": 1,
            "embeddings": self.connection.execute(
                "SELECT COUNT(*) FROM embeddings WHERE receipt_id = ?", (receipt_id,)
            ).fetchone()[0],
            "summaries": self.connection.execute(
                "SELECT COUNT(*) FROM summaries WHERE receipt_id = ?", (receipt_id,)
            ).fetchone()[0],
            "links": self.connection.execute(
                "SELECT COUNT(*) FROM memory_links "
                "WHERE source_receipt = ? OR target_receipt = ?",
                (receipt_id, receipt_id),
            ).fetchone()[0],
            "encryption_keys": self.connection.execute(
                "SELECT COUNT(*) FROM encryption_keys WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()[0],
        }
        for adapter in affected:
            lineage = self.connection.execute(
                "SELECT parent_era FROM lineage WHERE era = ?", (adapter["era"],)
            ).fetchone()
            if lineage and lineage["parent_era"]:
                parent = self.connection.execute(
                    "SELECT checkpoint FROM lineage WHERE era = ?",
                    (lineage["parent_era"],),
                ).fetchone()
                if parent:
                    rebuild_checkpoints.append(parent["checkpoint"])

        deleted_at = _now()
        with self.connection:
            for knowledge_id in semantic_ids:
                self.connection.execute(
                    "DELETE FROM semantic_knowledge WHERE knowledge_id = ?",
                    (knowledge_id,),
                )
            for adapter in affected:
                self.connection.execute(
                    "UPDATE adapters SET status = 'revoked_hard_delete' "
                    "WHERE adapter_id = ?",
                    (adapter["adapter_id"],),
                )
            self.connection.execute(
                "DELETE FROM event_search WHERE receipt_id = ?", (receipt_id,)
            )
            self.connection.execute(
                "DELETE FROM memory_links WHERE source_receipt = ? OR target_receipt = ?",
                (receipt_id, receipt_id),
            )
            self.connection.execute(
                "DELETE FROM encryption_keys WHERE receipt_id = ?", (receipt_id,)
            )
            self.connection.execute(
                "DELETE FROM summaries WHERE receipt_id = ?", (receipt_id,)
            )
            self.connection.execute(
                "DELETE FROM embeddings WHERE receipt_id = ?", (receipt_id,)
            )
            self.connection.execute(
                "DELETE FROM events WHERE receipt_id = ?", (receipt_id,)
            )
            self.connection.execute(
                "INSERT INTO erasures VALUES (?, ?, ?, 0)",
                (receipt_id, row["payload_hash"], deleted_at),
            )
        for path in content_paths:
            self._safe_unlink_unreferenced(path)
        return ErasureReceipt(
            receipt_id=receipt_id,
            revoked_adapters=tuple(sorted(item["adapter_id"] for item in affected)),
            rebuild_from_checkpoint=(
                sorted(set(rebuild_checkpoints))[0] if rebuild_checkpoints else None
            ),
            removed=removed,
            deleted_at=deleted_at,
        )

    def count_derivatives(self, receipt_id: str) -> dict[str, int]:
        semantic_count = sum(
            receipt_id in json.loads(row["source_receipts_json"])
            for row in self.connection.execute(
                "SELECT source_receipts_json FROM semantic_knowledge"
            )
        )
        return {
            "embeddings": self.connection.execute(
                "SELECT COUNT(*) FROM embeddings WHERE receipt_id = ?", (receipt_id,)
            ).fetchone()[0],
            "summaries": self.connection.execute(
                "SELECT COUNT(*) FROM summaries WHERE receipt_id = ?", (receipt_id,)
            ).fetchone()[0],
            "links": self.connection.execute(
                "SELECT COUNT(*) FROM memory_links "
                "WHERE source_receipt = ? OR target_receipt = ?",
                (receipt_id, receipt_id),
            ).fetchone()[0],
            "encryption_keys": self.connection.execute(
                "SELECT COUNT(*) FROM encryption_keys WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()[0],
            "semantic_records": semantic_count,
        }

    def erasure_receipt(self, receipt_id: str) -> dict | None:
        row = self.connection.execute(
            "SELECT * FROM erasures WHERE receipt_id = ?", (receipt_id,)
        ).fetchone()
        if row is None:
            return None
        return {
            "receipt_id": receipt_id,
            "deleted_at": row["deleted_at"],
            "payload_retained": bool(row["payload_retained"]),
        }
