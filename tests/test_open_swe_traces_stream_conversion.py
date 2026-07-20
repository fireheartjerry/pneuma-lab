"""Verified-stream conversion tests for the Open-SWE-Traces converter."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab.converters import open_swe_traces_training as converter
from pneuma_lab.schemas import load_schema

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "fixtures" / "adapters" / "open_swe_traces" / "golden"
TRACES_FIXTURE = GOLDEN / "pneuma_traces.jsonl"
ADAPTER_REPORT_FIXTURE = GOLDEN / "adapter_report.json"


def _golden_traces() -> tuple[dict, ...]:
    return converter.parse_verified_trace_stream(
        io.BytesIO(TRACES_FIXTURE.read_bytes())
    )


def _golden_adapter_report() -> dict:
    return converter.parse_verified_adapter_report_stream(
        io.BytesIO(ADAPTER_REPORT_FIXTURE.read_bytes())
    )


def test_parse_verified_trace_stream_accepts_golden_fixture() -> None:
    traces = _golden_traces()

    assert isinstance(traces, tuple)
    assert len(traces) == 2
    for trace in traces:
        assert isinstance(trace, dict)
        assert trace["trace_id"].startswith("ptrace:")
        assert trace["labels"]["repo_digest"].startswith("sha256:")
        assert type(trace["outcome"]["resolved"]) is bool


def test_parse_verified_trace_stream_rejects_blank_lines() -> None:
    first_line = TRACES_FIXTURE.read_bytes().splitlines()[0]
    with pytest.raises(ValueError, match="blank"):
        converter.parse_verified_trace_stream(
            io.BytesIO(first_line + b"\n\n" + first_line + b"\n")
        )


def test_parse_verified_trace_stream_rejects_non_object_lines() -> None:
    with pytest.raises(ValueError, match="object"):
        converter.parse_verified_trace_stream(io.BytesIO(b"[1,2,3]\n"))


def test_parse_verified_trace_stream_rejects_duplicate_member_json() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        converter.parse_verified_trace_stream(
            io.BytesIO(b'{"trace_id":"a","trace_id":"b"}\n')
        )


def test_parse_verified_trace_stream_rejects_nonfinite_constants() -> None:
    with pytest.raises(ValueError, match="constant|finite|JSON"):
        converter.parse_verified_trace_stream(
            io.BytesIO(b'{"trace_id":"x","score":NaN}\n')
        )


def test_parse_verified_trace_stream_requires_at_least_one_trace() -> None:
    with pytest.raises(ValueError, match="at least one"):
        converter.parse_verified_trace_stream(io.BytesIO(b""))


def test_parse_verified_trace_stream_rejects_schema_invalid_trace() -> None:
    trace = json.loads(TRACES_FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    trace.pop("trace_id")
    payload = json.dumps(trace, sort_keys=True).encode("utf-8") + b"\n"
    with pytest.raises(ValueError, match="trace_id|schema"):
        converter.parse_verified_trace_stream(io.BytesIO(payload))


def test_parse_verified_adapter_report_stream_accepts_golden_fixture() -> None:
    report = _golden_adapter_report()

    assert report["adapter"]["name"] == "open-swe-traces"
    assert report["dataset"] == converter.DATASET_ID
    assert report["counts"]["valid"] == 2
    assert report["trajectory"]["total_agent_steps"] == 5


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("drop_counts", "counts"),
        ("string_valid", "counts.valid"),
        ("wrong_schema_version", "adapter_report_schema_version"),
        ("wrong_dataset", "dataset"),
        ("raw_text_embedded", "privacy"),
        ("negative_agent_steps", "trajectory"),
    ],
)
def test_parse_verified_adapter_report_stream_rejects_tampered_shape(
    mutation: str,
    message: str,
) -> None:
    report = json.loads(ADAPTER_REPORT_FIXTURE.read_text(encoding="utf-8"))
    if mutation == "drop_counts":
        report.pop("counts")
    elif mutation == "string_valid":
        report["counts"]["valid"] = "2"
    elif mutation == "wrong_schema_version":
        report["adapter_report_schema_version"] = "9.9.9"
    elif mutation == "wrong_dataset":
        report["dataset"] = "swe-gym"
    elif mutation == "raw_text_embedded":
        report["privacy"]["raw_trajectory_text_embedded"] = True
    else:
        report["trajectory"]["total_agent_steps"] = -1
    payload = json.dumps(report, sort_keys=True).encode("utf-8")

    with pytest.raises(ValueError, match=message):
        converter.parse_verified_adapter_report_stream(io.BytesIO(payload))


def test_parse_verified_adapter_report_stream_rejects_duplicate_members() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        converter.parse_verified_adapter_report_stream(
            io.BytesIO(b'{"counts":{},"counts":{}}')
        )


def _run_stream_conversion(tmp_root: Path) -> dict:
    repo_root = tmp_root / "repo"
    data_root = tmp_root / "pneuma-data"
    data_root.mkdir(parents=True, exist_ok=True)
    output_root = repo_root / "build" / "training_examples" / "open-swe-traces" / "full"
    return converter.run_verified_stream_conversion(
        _golden_traces(),
        _golden_adapter_report(),
        repo_root=repo_root,
        data_root=data_root,
        output_root=output_root,
    )


def test_stream_conversion_publishes_without_reopening_sources(
    tmp_path,
    monkeypatch,
) -> None:
    def forbidden_legacy(*args, **kwargs):
        raise AssertionError("legacy path-opening conversion must not run")

    monkeypatch.setattr(converter, "run_full_conversion", forbidden_legacy)
    result = _run_stream_conversion(tmp_path)

    assert len(result["examples"]) == 2
    assert result["invalid_records"] == []
    assert Path(result["paths"]["examples"]).is_file()
    assert Path(result["paths"]["report"]).is_file()
    assert Path(result["paths"]["hash_manifest"]).is_file()
    assert Path(result["paths"]["invalid_examples"]).read_bytes() == b""


def test_stream_conversion_is_byte_deterministic_and_reconciles(tmp_path) -> None:
    result_1 = _run_stream_conversion(tmp_path / "run1")
    result_2 = _run_stream_conversion(tmp_path / "run2")

    for name in ("examples", "invalid_examples", "report", "hash_manifest"):
        bytes_1 = Path(result_1["paths"][name]).read_bytes()
        bytes_2 = Path(result_2["paths"][name]).read_bytes()
        assert (
            hashlib.sha256(bytes_1).hexdigest() == hashlib.sha256(bytes_2).hexdigest()
        )
        assert bytes_1 == bytes_2

    report = result_1["report"]
    assert report["input"]["trace_jsonl"] == "verified-stream:pneuma_traces.jsonl"
    assert report["input"]["adapter_report"] == "verified-stream:adapter_report.json"
    reconciliation = report["count_reconciliation"]
    assert reconciliation["reconciled"] is True
    assert reconciliation["observed"]["traces_read"] == 2
    assert reconciliation["observed"]["agent_steps"] == 5
    assert reconciliation["observed"]["resolved"] == 1
    assert reconciliation["observed"]["unresolved"] == 1
    assert reconciliation["expected"]["valid_traces"] == 2


def test_stream_conversion_rejects_unreconcilable_adapter_report(tmp_path) -> None:
    report = json.loads(ADAPTER_REPORT_FIXTURE.read_text(encoding="utf-8"))
    report["trajectory"]["total_agent_steps"] = 99
    output_root = (
        tmp_path / "repo" / "build" / "training_examples" / "open-swe-traces" / "full"
    )

    with pytest.raises(ValueError, match="reconcile"):
        converter.run_verified_stream_conversion(
            _golden_traces(),
            report,
            repo_root=tmp_path / "repo",
            data_root=tmp_path / "pneuma-data",
            output_root=output_root,
        )
    assert not output_root.exists()


def test_stream_conversion_examples_validate_against_training_contract(
    tmp_path,
) -> None:
    result = _run_stream_conversion(tmp_path)
    schema = load_schema(converter.TRAINING_EXAMPLE_SCHEMA)
    validator = Draft202012Validator(schema)

    written = [
        json.loads(line)
        for line in Path(result["paths"]["examples"])
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert written == result["examples"]
    for example in written:
        validator.validate(example)
        assert example["label_provenance"]["kind"] == "constructed_label"
        assert example["dataset_id"] == converter.DATASET_ID
    converter.validate_training_examples(written)
