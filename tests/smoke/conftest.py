from __future__ import annotations

from collections.abc import Iterator
from hashlib import sha256
from pathlib import Path

import pytest

from pneuma_lab.resampling_null.types import ArtifactRef


@pytest.fixture(scope="session")
def canonical_refs() -> dict[str, ArtifactRef]:
    """Compact immutable references for the packet-only synthetic fixture."""

    def ref(role: str) -> ArtifactRef:
        payload = role.encode("ascii")
        return ArtifactRef(
            role=role,
            relative_path=f"fixtures/{role}",
            sha256=sha256(payload).hexdigest(),
            byte_count=len(payload),
            media_type="application/json",
        )

    return {
        role: ref(role)
        for role in (
            "focal_verifier",
            "donor_verifier",
            "assignment",
            "identifier_map",
            "tokenizer",
            "packet_template",
            "normalized_real",
            "normalized_donor",
            "normalized_sham",
            "packet_policy",
            "pad_unit_set",
        )
    }


@pytest.fixture
def synthetic_packet_root(tmp_path: Path) -> Iterator[Path]:
    root = tmp_path / "synthetic-packets"
    root.mkdir()
    yield root
