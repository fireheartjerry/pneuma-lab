"""Registry tests: every contract and status schema is valid and discoverable."""

from __future__ import annotations

import json

import pytest

from pneuma_lab import INPUT_FRAMES, OUTPUT_FRAMES, __version__
from pneuma_lab import schemas as pls

EXPECTED_INPUT_COUNT = 5
EXPECTED_OUTPUT_COUNT = 9
EXPECTED_IO_BUNDLE_COUNT = 2
EXPECTED_EVIDENCE_CAMPAIGN_COUNT = 1
EXPECTED_TRAINING_COUNT = 4
EXPECTED_MANIFEST_COUNT = 1
SCHEMA_VERSION_OVERRIDES = {
    "consciousness-evidence-frame.schema.json": "0.2.0",
}


def test_schema_dir_exists() -> None:
    assert pls.SCHEMA_DIR.is_dir(), f"missing schema dir: {pls.SCHEMA_DIR}"


def test_expected_counts() -> None:
    assert len(pls.INPUT_SCHEMA_FILES) == EXPECTED_INPUT_COUNT
    assert len(pls.OUTPUT_SCHEMA_FILES) == EXPECTED_OUTPUT_COUNT
    assert len(pls.ENVELOPE_SCHEMA_FILES) == 1
    assert len(pls.IO_BUNDLE_SCHEMA_FILES) == EXPECTED_IO_BUNDLE_COUNT
    assert len(pls.EVIDENCE_CAMPAIGN_SCHEMA_FILES) == EXPECTED_EVIDENCE_CAMPAIGN_COUNT
    assert len(pls.TRAINING_SCHEMA_FILES) == EXPECTED_TRAINING_COUNT
    assert len(pls.MANIFEST_SCHEMA_FILES) == EXPECTED_MANIFEST_COUNT
    assert (
        len(pls.ALL_SCHEMA_FILES)
        == EXPECTED_INPUT_COUNT
        + EXPECTED_OUTPUT_COUNT
        + 1
        + EXPECTED_IO_BUNDLE_COUNT
        + EXPECTED_EVIDENCE_CAMPAIGN_COUNT
        + EXPECTED_TRAINING_COUNT
        + EXPECTED_MANIFEST_COUNT
    )


@pytest.mark.parametrize("filename", pls.ALL_SCHEMA_FILES)
def test_schema_file_exists(filename: str) -> None:
    assert pls.schema_path(filename).is_file(), f"missing schema file: {filename}"


@pytest.mark.parametrize("filename", pls.ALL_SCHEMA_FILES)
def test_schema_parses(filename: str) -> None:
    schema = pls.load_schema(filename)
    assert isinstance(schema, dict)


@pytest.mark.parametrize("filename", pls.ALL_SCHEMA_FILES)
def test_schema_has_core_metadata(filename: str) -> None:
    schema = pls.load_schema(filename)
    # Every contract declares its meta-schema, a stable $id, a title, and an object body.
    assert schema.get("$schema", "").endswith("schema"), filename
    assert schema.get("$id", "").endswith(".schema.json"), filename
    assert schema.get("title"), filename
    assert schema.get("type") == "object", filename
    assert schema.get("description"), filename


@pytest.mark.parametrize("filename", pls.INPUT_SCHEMA_FILES + pls.OUTPUT_SCHEMA_FILES)
def test_schema_declares_frame_kind_and_version(filename: str) -> None:
    schema = pls.load_schema(filename)
    kind = schema.get("x-pneuma-frame-kind")
    assert kind in {"input", "output"}, f"{filename}: bad frame kind {kind!r}"
    expected_version = SCHEMA_VERSION_OVERRIDES.get(filename, "0.1.0")
    assert schema.get("x-pneuma-version") == expected_version, filename


def test_input_output_partition_matches_files() -> None:
    for name in pls.INPUT_SCHEMA_FILES:
        assert pls.load_schema(name)["x-pneuma-frame-kind"] == "input", name
    for name in pls.OUTPUT_SCHEMA_FILES:
        assert pls.load_schema(name)["x-pneuma-frame-kind"] == "output", name


def test_ids_are_unique() -> None:
    ids = [pls.load_schema(n)["$id"] for n in pls.ALL_SCHEMA_FILES]
    assert len(ids) == len(set(ids)), "duplicate $id across schemas"


def test_load_all_schemas() -> None:
    loaded = pls.load_all_schemas()
    assert set(loaded) == set(pls.ALL_SCHEMA_FILES)


def test_package_metadata() -> None:
    assert __version__ == "0.1.0"
    assert len(INPUT_FRAMES) == EXPECTED_INPUT_COUNT
    assert len(OUTPUT_FRAMES) == EXPECTED_OUTPUT_COUNT


def test_public_subpackages_import() -> None:
    import pneuma_lab.adapters  # noqa: F401
    import pneuma_lab.evals  # noqa: F401
    import pneuma_lab.replay  # noqa: F401


@pytest.mark.parametrize("filename", pls.ALL_SCHEMA_FILES)
def test_schema_is_valid_jsonschema_if_available(filename: str) -> None:
    """If jsonschema is installed, every schema must itself be a valid schema."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = pls.load_schema(filename)
    # check_schema raises SchemaError on a malformed schema.
    jsonschema.Draft202012Validator.check_schema(schema)


def test_schemas_are_utf8_json_on_disk() -> None:
    # Guard against BOM / encoding drift from editors on Windows.
    for name in pls.ALL_SCHEMA_FILES:
        raw = pls.schema_path(name).read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{name} has a UTF-8 BOM"
        json.loads(raw.decode("utf-8"))


def test_envelope_bucket_registered() -> None:
    assert pls.ENVELOPE_SCHEMA_FILES == ("pneuma-trace.schema.json",)
    assert "pneuma-trace.schema.json" in pls.ALL_SCHEMA_FILES


def test_training_schema_bucket_registered() -> None:
    assert pls.TRAINING_SCHEMA_FILES == (
        "pneuma-training-example.schema.json",
        "estimator-run-manifest.schema.json",
        "estimator-training-authorization.schema.json",
        "pneuma-brain-corpus-authorization.schema.json",
    )
    assert "pneuma-training-example.schema.json" in pls.ALL_SCHEMA_FILES


def test_manifest_schema_bucket_registered() -> None:
    assert pls.MANIFEST_SCHEMA_FILES == ("project-status.schema.json",)
    schema = pls.load_schema("project-status.schema.json")
    assert schema["x-pneuma-schema-kind"] == "manifest"
    assert "project-status.schema.json" in pls.ALL_SCHEMA_FILES


def test_envelope_schema_shape() -> None:
    schema = pls.load_schema("pneuma-trace.schema.json")
    assert schema["x-pneuma-schema-kind"] == "envelope"
    assert schema["type"] == "object"
    for key in ("trace_id", "run_id", "provenance", "build", "frames"):
        assert key in schema["properties"], f"missing property {key}"
