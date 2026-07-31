from pathlib import Path

import pytest

from pneuma_lab.cloud.errors import CloudManifestError
from pneuma_lab.cloud.journal import JournalEvent, append


def test_resumable_journal_appends_once() -> None:
    events = append((), JournalEvent(1, "start", "a" * 64))
    with pytest.raises(CloudManifestError): append(events, JournalEvent(1, "retry", "a" * 64))


def test_phase_b_wording_preserves_peer_slot_scope() -> None:
    root = Path(__file__).resolve().parents[2]
    text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "docs/research/neurips-2026-workshop").glob("*.md")
        if not path.name.startswith("37-")
    )
    for forbidden in ("arm-blind worker", "workers cannot see their own arm", "full arm blindness"):
        assert forbidden not in text.lower()
    assert "peer-slot" in (root / "src/pneuma_lab/resampling_null/packet_capabilities.py").read_text(encoding="utf-8")
