"""Local persistent-memory provenance, suppression, consolidation, and erasure."""

from __future__ import annotations

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab import schemas as pls
from pneuma_lab.foundation.memory import LocalMemoryStore, MemoryIntegrityError


def test_event_memory_is_searchable_and_suppression_is_reversible(
    tmp_path: Path,
) -> None:
    with LocalMemoryStore(tmp_path) as store:
        store.record_lineage("era-0", parent_era=None, checkpoint="base.pt")
        receipt = store.append_event(
            "pytest found the failing assertion",
            era="era-0",
            provenance={"trace_id": "trace-1"},
            uncertainty=0.1,
        )
        assert store.search("failing assertion")[0]["receipt_id"] == receipt
        assert store.read_event(receipt)["payload"] == (
            "pytest found the failing assertion"
        )
        store.suppress(receipt, reason="temporarily irrelevant")
        assert store.read_event(receipt) is None
        assert store.search("failing assertion") == []
        assert store.meta_memory(receipt)["suppressed"] is True
        store.unsuppress(receipt)
        assert store.read_event(receipt)["payload"].startswith("pytest")


def test_active_state_and_autobiographical_memory_are_local_views(
    tmp_path: Path,
) -> None:
    with LocalMemoryStore(tmp_path) as store:
        store.record_lineage("era-0", parent_era=None, checkpoint="base.pt")
        store.set_active_state("decision", {"candidate": 1, "confidence": 0.6})
        assert store.get_active_state("decision") == {
            "candidate": 1,
            "confidence": 0.6,
        }
        receipt = store.append_event("first local event", era="era-0")
        view = store.autobiographical_view(era="era-0")
        assert view == [
            {
                "receipt_id": receipt,
                "era": "era-0",
                "payload": "first local event",
                "provenance": {},
                "uncertainty": 0.0,
            }
        ]


def test_consolidation_retains_receipts_contradictions_and_is_order_stable(
    tmp_path: Path,
) -> None:
    with LocalMemoryStore(tmp_path) as store:
        store.record_lineage("era-0", parent_era=None, checkpoint="base.pt")
        first = store.append_event("tests pass", era="era-0")
        second = store.append_event("one flaky test appeared", era="era-0")
        record = store.consolidate(
            claim="The suite is usually healthy",
            source_receipts=(second, first),
            contradictions=(second,),
            uncertainty=0.25,
        )
        assert record["source_receipts"] == sorted((first, second))
        assert record["contradictions"] == [second]
        assert record["uncertainty"] == pytest.approx(0.25)

        procedure = store.consolidate(
            claim="Run pytest before promotion",
            source_receipts=(first,),
            contradictions=(),
            uncertainty=0.1,
            knowledge_kind="procedural",
        )
        assert procedure["knowledge_kind"] == "procedural"


def test_consolidation_rejects_false_memory_without_valid_receipts(
    tmp_path: Path,
) -> None:
    with LocalMemoryStore(tmp_path) as store:
        with pytest.raises(MemoryIntegrityError, match="source receipt"):
            store.consolidate(
                claim="invented claim",
                source_receipts=("missing",),
                contradictions=(),
                uncertainty=0.0,
            )


def test_hard_delete_removes_payload_and_all_derivatives_and_revokes_adapter(
    tmp_path: Path,
) -> None:
    with LocalMemoryStore(tmp_path) as store:
        store.record_lineage("era-0", parent_era=None, checkpoint="base.pt")
        store.record_lineage(
            "era-1",
            parent_era="era-0",
            checkpoint="era-1-before-training.pt",
        )
        receipt = store.append_event("private user fact", era="era-1")
        paths = store.add_derived_artifacts(
            receipt,
            embedding=b"local-vector-bytes",
            summary="private summary",
            encryption_key=b"local-key",
        )
        other = store.append_event("linked event", era="era-1")
        store.link(receipt, other, relation="supports")
        store.consolidate(
            claim="derived private knowledge",
            source_receipts=(receipt,),
            contradictions=(),
            uncertainty=0.2,
        )
        store.register_adapter(
            "adapter-era-1",
            era="era-1",
            source_receipts=(receipt,),
        )
        erasure = store.hard_delete(receipt)

        assert store.read_event(receipt, include_suppressed=True) is None
        assert store.search("private") == []
        assert all(not path.exists() for path in paths)
        assert store.count_derivatives(receipt) == {
            "embeddings": 0,
            "summaries": 0,
            "links": 0,
            "encryption_keys": 0,
            "semantic_records": 0,
        }
        assert erasure.revoked_adapters == ("adapter-era-1",)
        assert erasure.rebuild_from_checkpoint == "base.pt"
        assert store.adapter_status("adapter-era-1") == "revoked_hard_delete"
        assert store.erasure_receipt(receipt)["payload_retained"] is False
        serialized = erasure.to_dict()
        Draft202012Validator(
            pls.load_schema("memory-erasure-receipt.schema.json")
        ).validate(serialized)
        assert serialized["removed"] == {
            "payloads": 1,
            "embeddings": 1,
            "summaries": 1,
            "links": 1,
            "encryption_keys": 1,
        }
