"""Analysis-freeze boundary tests."""

from __future__ import annotations

import pytest

from pneuma_lab.resampling_null.errors import RecordValidationError


pytestmark = pytest.mark.milestone


def test_freeze_module_exposes_the_public_constructor() -> None:
    from pneuma_lab.resampling_null.freeze import freeze_analysis

    assert callable(freeze_analysis)


def test_snapshot_rejects_duplicate_and_escape_destinations(tmp_path) -> None:
    from pneuma_lab.resampling_null.freeze import snapshot_sources

    source = tmp_path / "input.json"
    source.write_text("{}", encoding="utf-8")
    run_root = tmp_path / "run"
    run_root.mkdir()
    with pytest.raises((ValueError, RecordValidationError), match="duplicate"):
        snapshot_sources(
            run_root,
            {"one": source, "two": source},
            relative_paths={
                "one": "sources/analysis-freeze/a",
                "two": "sources/analysis-freeze/a",
            },
        )
    with pytest.raises((ValueError, RecordValidationError), match="escapes"):
        snapshot_sources(
            run_root,
            {"one": source},
            relative_paths={"one": "../escape"},
        )


def test_freeze_verification_binds_each_named_input(tmp_path, monkeypatch) -> None:
    """Swapping bytes between named sources must invalidate the freeze."""
    import pneuma_lab.resampling_null.freeze as freeze
    from pneuma_lab.resampling_null.types import ArtifactRef

    run_root = tmp_path / "run"
    snapshot_root = run_root / "sources" / "analysis-freeze"
    snapshot_root.mkdir(parents=True)
    current_root = tmp_path / "current"
    current_root.mkdir()

    frozen_paths = {
        "estimands": snapshot_root / "estimands",
        "multiplicity": snapshot_root / "multiplicity",
        "config": snapshot_root / "config",
        "schema": snapshot_root / "schema",
    }
    frozen_paths["estimands"].write_bytes(b"estimands")
    frozen_paths["multiplicity"].write_bytes(b"multiplicity")
    frozen_paths["config"].write_bytes(b"config")
    frozen_paths["schema"].write_bytes(b"schema")

    current_paths = {
        "estimands": current_root / "estimands",
        "multiplicity": current_root / "multiplicity",
    }
    current_paths["estimands"].write_bytes(b"multiplicity")
    current_paths["multiplicity"].write_bytes(b"estimands")
    current_config = current_root / "config"
    current_schema = current_root / "schema"
    current_config.write_bytes(b"config")
    current_schema.write_bytes(b"schema")

    def ref_for(name: str) -> dict[str, object]:
        payload = frozen_paths[name].read_bytes()
        import hashlib

        return {
            "role": "analysis_source",
            "relative_path": f"sources/analysis-freeze/{name}",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "byte_count": len(payload),
            "media_type": "application/octet-stream",
        }

    packet_ref = ArtifactRef(
        "packet_index", "packet-index.json", "0" * 64, 0, "application/json"
    )
    packet_mapping = {
        "role": packet_ref.role,
        "relative_path": packet_ref.relative_path,
        "sha256": packet_ref.sha256,
        "byte_count": packet_ref.byte_count,
        "media_type": packet_ref.media_type,
    }
    freeze_value = {
        "payload": {
            "source_refs": [
                {"name": "estimands", "ref": ref_for("estimands")},
                {"name": "multiplicity", "ref": ref_for("multiplicity")},
            ],
            "config_ref": ref_for("config"),
            "projection_schema_ref": ref_for("schema"),
            "packet_index_ref": packet_mapping,
        }
    }
    documents = iter([freeze_value, {"study_id": "study"}])
    monkeypatch.setattr(
        freeze,
        "_load_direct_scientific_parent",
        lambda *args, **kwargs: type("Document", (), {"value": next(documents)})(),
    )

    with pytest.raises(RecordValidationError, match="named input"):
        freeze.verify_analysis_freeze(
            ArtifactRef("analysis_freeze", "freeze.json", "1" * 64, 0, "application/json"),
            run_root=run_root,
            source_paths=current_paths,
            config_path=current_config,
            projection_schema_path=current_schema,
            packet_index_ref=packet_ref,
        )


def test_freeze_writer_emits_schema_valid_named_bindings(tmp_path, monkeypatch) -> None:
    """The production writer and public schema must agree on the v0.2 contract."""
    import pneuma_lab.resampling_null.freeze as freeze
    from pneuma_lab.resampling_null.artifacts import validate_record
    from pneuma_lab.resampling_null.types import ArtifactRef

    run_root = tmp_path / "run"
    run_root.mkdir()
    source = tmp_path / "estimands.json"
    config = tmp_path / "config.json"
    projection_schema = tmp_path / "projection.schema.json"
    for path in (source, config, projection_schema):
        path.write_bytes(path.name.encode("utf-8"))

    packet_ref = ArtifactRef(
        "packet_index", "packet-index.json", "0" * 64, 0, "application/json"
    )
    monkeypatch.setattr(
        freeze,
        "_load_direct_scientific_parent",
        lambda *args, **kwargs: type(
            "Document", (), {"value": {"study_id": "study"}}
        )(),
    )

    def snapshot(_root, sources):
        return {
            name: ArtifactRef(
                "analysis_source",
                f"sources/analysis-freeze/{name}",
                str(index) * 64,
                index,
                "application/octet-stream",
            )
            for index, name in enumerate(sources, start=1)
        }

    captured: dict[str, object] = {}

    def write(_destination, record, **_kwargs):
        captured.update(record)
        validate_record(record)
        return ArtifactRef(
            "analysis_freeze", "freeze.json", "f" * 64, 1, "application/json"
        )

    monkeypatch.setattr(freeze, "snapshot_sources", snapshot)
    monkeypatch.setattr(freeze, "write_record", write)

    freeze.freeze_analysis(
        run_root=run_root,
        destination=run_root / "freeze.json",
        study_id="study",
        frozen_created_at="2026-07-30T00:00:00Z",
        provenance={"design_sha256": "d" * 64, "code_sha256": "c" * 64},
        source_paths={"estimands": source},
        config_path=config,
        projection_schema_path=projection_schema,
        packet_index_ref=packet_ref,
    )

    assert captured["schema_version"] == "0.2.0"
    assert captured["payload"]["source_refs"] == [
        {
            "name": "estimands",
            "ref": {
                "role": "analysis_source",
                "relative_path": "sources/analysis-freeze/estimands",
                "sha256": "1" * 64,
                "byte_count": 1,
                "media_type": "application/octet-stream",
            },
        }
    ]
