"""The published schemas must accept what the system actually emits.

A schema that drifts from the emitter is worse than no schema: it tells an
external consumer the record has a shape it does not have.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

from pneuma_lab.adversarial_review import run_campaign  # noqa: E402
from pneuma_lab.adversarial_review.campaign import STAGE_PRE_LAUNCH  # noqa: E402

from .conftest import FIXTURE_ROLE_IDS, load_fixture_campaign  # noqa: E402

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas" / "adversarial-review"

SCHEMA_FILES = (
    "campaign-inputs.schema.json",
    "campaign-result.schema.json",
    "editor-synthesis.schema.json",
    "falsification-item.schema.json",
    "finding.schema.json",
    "readiness-disposition.schema.json",
    "reviewer-report.schema.json",
)


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", SCHEMA_FILES)
def test_schema_is_valid_draft_2020_12(name: str) -> None:
    schema = _schema(name)
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["x-pneuma-schema-kind"] == "adversarial_review_record"
    for field in ("$id", "title", "description", "type"):
        assert field in schema, f"{name} must declare {field}"


@pytest.mark.parametrize("name", SCHEMA_FILES)
def test_schema_files_have_no_bom(name: str) -> None:
    raw = (SCHEMA_DIR / name).read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")


def test_emitted_records_validate(tmp_path: Path) -> None:
    inputs, claims, source = load_fixture_campaign(tmp_path)
    result = run_campaign(
        campaign_id=inputs.campaign_id,
        stage=STAGE_PRE_LAUNCH,
        inputs=inputs,
        claims=claims,
        source=source,
        role_ids=FIXTURE_ROLE_IDS,
    )
    payload = result.to_canonical()

    jsonschema.validate(payload, _schema("campaign-result.schema.json"))
    jsonschema.validate(inputs.to_canonical(), _schema("campaign-inputs.schema.json"))
    jsonschema.validate(payload["synthesis"], _schema("editor-synthesis.schema.json"))
    jsonschema.validate(
        payload["disposition"], _schema("readiness-disposition.schema.json")
    )
    for report in payload["reports"]:
        jsonschema.validate(report, _schema("reviewer-report.schema.json"))
        for finding in report["findings"]:
            jsonschema.validate(finding, _schema("finding.schema.json"))
    for item in payload["falsification"]:
        jsonschema.validate(item, _schema("falsification-item.schema.json"))
