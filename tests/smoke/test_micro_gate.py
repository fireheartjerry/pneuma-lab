from __future__ import annotations

from pneuma_lab.status import load_manifest, validate_manifest


def test_project_status_manifest_is_coherent() -> None:
    assert validate_manifest(load_manifest()) == []
