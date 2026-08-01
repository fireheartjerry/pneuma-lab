from __future__ import annotations

import json

import pytest

from scripts.research.step5b_oci_audit import parse_manifest, select_linux_amd64


def test_selects_exact_linux_amd64_child() -> None:
    index = {
        "manifests": [
            {"digest": "sha256:arm", "platform": {"os": "linux", "architecture": "arm64"}},
            {"digest": "sha256:x86", "platform": {"os": "linux", "architecture": "amd64"}},
        ]
    }
    assert select_linux_amd64(index) == "sha256:x86"


def test_refuses_ambiguous_platform() -> None:
    index = {
        "manifests": [
            {"digest": "sha256:a", "platform": {"os": "linux", "architecture": "amd64"}},
            {"digest": "sha256:b", "platform": {"os": "linux", "architecture": "amd64"}},
        ]
    }
    with pytest.raises(ValueError, match="exactly one"):
        select_linux_amd64(index)


def test_parses_registry_object() -> None:
    assert parse_manifest(json.dumps({"schemaVersion": 2}).encode()) == {"schemaVersion": 2}
