"""Tiny packet-boundary tripwire; causal reconstruction lives in t3_s10."""

from pathlib import Path

import pytest

from pneuma_lab.resampling_null.packets import (
    IdentifierAtom,
    IdentifierKind,
    PacketInvalid,
    PacketPolicy,
    SyntheticPacketArtifactStore,
)


def test_packet_primitives_fail_closed(tmp_path: Path) -> None:
    store = SyntheticPacketArtifactStore(tmp_path)
    first = store.put_text(
        "private/packet.txt",
        "stable",
        role="private_guidance",
    )
    assert (
        store.put_text(
            "private/packet.txt",
            "stable",
            role="private_guidance",
        )
        == first
    )
    with pytest.raises(FileExistsError):
        store.put_text(
            "private/packet.txt",
            "changed",
            role="private_guidance",
        )
    with pytest.raises(PacketInvalid, match="escapes"):
        store.put_text(
            "../packet.txt",
            "escape",
            role="private_guidance",
        )
    with pytest.raises(ValueError, match="positive"):
        PacketPolicy(True, 1, "normalizer")
    with pytest.raises(ValueError, match="entity_id"):
        IdentifierAtom("", IdentifierKind.SYMBOL)
