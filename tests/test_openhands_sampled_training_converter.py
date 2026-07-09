from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pneuma_lab.converters import openhands_sampled_training as converter
from pneuma_lab.converters.openhands_sampled_training import convert_traces
from pneuma_lab.schemas import load_schema

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "adapters"
    / "openhands_sampled"
    / "golden"
    / "pneuma_traces.jsonl"
)
SCHEMA_NAME = "pneuma-training-example.schema.json"
FORBIDDEN_INPUT_KEYS = {
    "resolved",
    "outcome",
    "labels",
    "gold",
    "oracle",
    "fail_to_pass",
    "pass_to_pass",
    "patch",
    "verdict",
}


def _fixture_traces() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _fixture_jsonl_path(tmp_path: Path) -> Path:
    path = tmp_path / "pneuma_traces.jsonl"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    return path


def _adapter_report_path(tmp_path: Path) -> Path:
    report = {
        "adapter": {"name": "openhands-sampled", "version": "0.1.0"},
        "counts": {"valid": 3, "invalid": 0, "skipped": 0},
        "privacy": {"redaction_totals": []},
        "traces_file_sha256": "fixture-traces-sha",
        "trace_index_file_sha256": "fixture-index-sha",
        "invalid_traces_file_sha256": "fixture-invalid-sha",
    }
    path = tmp_path / "adapter_report.json"
    path.write_text(json.dumps(report, sort_keys=True), encoding="utf-8")
    return path


def _bounded_output_paths(tmp_path: Path, name: str = "run") -> tuple[Path, Path, Path]:
    root = tmp_path / "build" / name
    return (
        root / "examples.jsonl",
        root / "conversion_report.json",
        root / "hash_manifest.json",
    )


def _walk_keys(value) -> list[str]:
    if isinstance(value, dict):
        keys = list(value)
        for child in value.values():
            keys.extend(_walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: list[str] = []
        for child in value:
            keys.extend(_walk_keys(child))
        return keys
    return []


def test_fixture_traces_convert_to_valid_training_examples() -> None:
    validator = Draft202012Validator(load_schema(SCHEMA_NAME))
    examples = convert_traces(
        _fixture_traces(),
        synthetic_fixture_ref="fixtures/adapters/openhands_sampled/golden/pneuma_traces.jsonl",
    )

    assert len(examples) == len(_fixture_traces()) == 3
    for example in examples:
        assert list(validator.iter_errors(example)) == []
        assert example["dataset_id"] == "swe-gym-openhands-sampled"
        assert example["dataset_family"] == "swe-gym"
        assert example["example_type"] == "TrajectoryExample"
        assert example["input_modality"] == "structured_features"
        assert example["task_type"] == "RISK_PREDICTION"
        assert example["task_mask"] == ["RISK_PREDICTION"]
        assert example["label_provenance"]["kind"] == "harness_outcome"
        assert example["privacy_status"] == "redaction_verified"
        assert example["model_use_tier"] == "train_after_adapter"
        assert example["training_weight"] == 0.0
        assert example["split_policy"] == "repo_grouped"
        assert example["target"].keys() == {"resolved"}
        assert example["evidence_refs"]
        assert example["canonical_feature_refs"]


def test_conversion_is_deterministic() -> None:
    traces = _fixture_traces()
    assert convert_traces(traces) == convert_traces(copy.deepcopy(traces))


def test_one_trace_produces_one_full_trace_example() -> None:
    traces = _fixture_traces()
    examples = convert_traces(traces)

    assert len(examples) == len(traces)
    assert {example["input"]["prefix"] for example in examples} == {"full"}
    assert all(
        example["input"]["trajectory"]["num_agent_steps"]
        == trace["trajectory"]["num_agent_steps"]
        for example, trace in zip(examples, traces)
    )


def test_target_resolved_comes_from_harness_outcome() -> None:
    traces = _fixture_traces()
    examples = convert_traces(traces)

    assert [example["target"]["resolved"] for example in examples] == [
        trace["labels"]["resolved"] for trace in traces
    ]
    assert [example["target"]["resolved"] for example in examples] == [
        trace["outcome"]["resolved"] for trace in traces
    ]


def test_input_has_no_forbidden_leakage_keys() -> None:
    examples = convert_traces(_fixture_traces())

    for example in examples:
        input_keys = {key.lower() for key in _walk_keys(example["input"])}
        assert FORBIDDEN_INPUT_KEYS.isdisjoint(input_keys)
        input_blob = json.dumps(example["input"], sort_keys=True)
        assert "C:/pneuma-data" not in input_blob
        assert "C:\\pneuma-data" not in input_blob
        assert "fail_to_pass" not in input_blob
        assert "pass_to_pass" not in input_blob


def test_outcome_oracle_and_label_resolved_do_not_affect_input() -> None:
    trace = _fixture_traces()[0]
    mutated = copy.deepcopy(trace)
    mutated["labels"]["resolved"] = trace["labels"]["resolved"]
    mutated["outcome"]["resolved"] = trace["outcome"]["resolved"]
    mutated["oracle"]["fail_to_pass"] = ["leaky-test"]
    mutated["oracle"]["pass_to_pass"] = ["leaky-test"]
    mutated["reference_supervision"] = {"gold_patch_sha256": "leaky"}
    mutated["outcome"]["git_patch_sha256"] = "leaky"

    assert convert_traces([trace])[0]["input"] == convert_traces([mutated])[0]["input"]


def test_converter_tests_use_committed_fixture_only() -> None:
    assert "fixtures" in str(FIXTURE)
    assert "C:\\pneuma-data" not in str(FIXTURE)
    assert "C:/pneuma-data" not in str(FIXTURE)


def test_limit_is_required(tmp_path) -> None:
    trace_path = _fixture_jsonl_path(tmp_path)
    report_path = _adapter_report_path(tmp_path)

    with pytest.raises(SystemExit):
        converter.main(
            [
                "--mode",
                "bounded-sample",
                "--input",
                str(trace_path),
                "--adapter-report",
                str(report_path),
            ]
        )


def test_limit_above_hard_cap_fails_closed(tmp_path) -> None:
    trace_path = _fixture_jsonl_path(tmp_path)
    report_path = _adapter_report_path(tmp_path)
    examples, report, manifest = _bounded_output_paths(tmp_path)

    rc = converter.main(
        [
            "--mode",
            "bounded-sample",
            "--input",
            str(trace_path),
            "--adapter-report",
            str(report_path),
            "--output",
            str(examples),
            "--report",
            str(report),
            "--hash-manifest",
            str(manifest),
            "--limit",
            "26",
        ]
    )

    assert rc == 2
    assert not examples.exists()
    assert not report.exists()
    assert not manifest.exists()


def test_missing_or_wrong_mode_fails(tmp_path) -> None:
    trace_path = _fixture_jsonl_path(tmp_path)
    report_path = _adapter_report_path(tmp_path)

    with pytest.raises(SystemExit):
        converter.main(
            [
                "--input",
                str(trace_path),
                "--adapter-report",
                str(report_path),
                "--limit",
                "1",
            ]
        )
    with pytest.raises(SystemExit):
        converter.main(
            [
                "--mode",
                "full",
                "--input",
                str(trace_path),
                "--adapter-report",
                str(report_path),
                "--limit",
                "1",
            ]
        )


def test_bounded_reader_reads_only_requested_records() -> None:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines(keepends=True)

    class TrackingLines:
        def __init__(self, values: list[str]) -> None:
            self.values = values
            self.reads = 0

        def __iter__(self):
            for value in self.values:
                self.reads += 1
                yield value

    tracking = TrackingLines(lines)
    traces = converter.read_bounded_trace_lines(tracking, 2)

    assert len(traces) == 2
    assert tracking.reads == 2


def test_bounded_conversion_outputs_are_deterministic_and_valid(tmp_path) -> None:
    trace_path = _fixture_jsonl_path(tmp_path)
    report_path = _adapter_report_path(tmp_path)
    out1 = _bounded_output_paths(tmp_path, "run1")
    out2 = _bounded_output_paths(tmp_path, "run2")

    result1 = converter.run_bounded_sample_conversion(
        input_path=trace_path,
        adapter_report_path=report_path,
        examples_path=out1[0],
        report_path=out1[1],
        hash_manifest_path=out1[2],
        limit=2,
    )
    result2 = converter.run_bounded_sample_conversion(
        input_path=trace_path,
        adapter_report_path=report_path,
        examples_path=out2[0],
        report_path=out2[1],
        hash_manifest_path=out2[2],
        limit=2,
    )

    assert out1[0].read_text(encoding="utf-8") == out2[0].read_text(encoding="utf-8")
    assert out1[1].read_text(encoding="utf-8") == out2[1].read_text(encoding="utf-8")
    assert out1[2].read_text(encoding="utf-8") == out2[2].read_text(encoding="utf-8")
    assert result1["report"] == result2["report"]
    assert result1["hash_manifest"] == result2["hash_manifest"]

    validator = Draft202012Validator(load_schema(SCHEMA_NAME))
    examples = [
        json.loads(line)
        for line in out1[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(examples) == 2
    assert result1["report"]["input"]["loaded_traces"] == 2
    assert result1["report"]["output"]["examples_emitted"] == 2

    for example in examples:
        assert list(validator.iter_errors(example)) == []
        assert example["example_type"] == "TrajectoryExample"
        assert example["task_type"] == "RISK_PREDICTION"
        assert example["task_mask"] == ["RISK_PREDICTION"]
        assert example["model_use_tier"] == "train_after_adapter"
        assert example["training_weight"] == 0.0
        assert example["evidence_refs"]
        input_keys = {key.lower() for key in _walk_keys(example["input"])}
        assert FORBIDDEN_INPUT_KEYS.isdisjoint(input_keys)


def test_cli_defaults_outputs_under_build(tmp_path, monkeypatch) -> None:
    trace_path = _fixture_jsonl_path(tmp_path)
    report_path = _adapter_report_path(tmp_path)
    monkeypatch.chdir(tmp_path)

    rc = converter.main(
        [
            "--mode",
            "bounded-sample",
            "--input",
            str(trace_path),
            "--adapter-report",
            str(report_path),
            "--limit",
            "1",
        ]
    )

    assert rc == 0
    assert (tmp_path / "build" / "training_examples").is_dir()
    assert (
        tmp_path
        / "build"
        / "training_examples"
        / "openhands-sampled"
        / "bounded-sample"
        / "examples.jsonl"
    ).is_file()


def test_forbidden_paths_fail_before_access(tmp_path) -> None:
    report_path = _adapter_report_path(tmp_path)
    examples, report, manifest = _bounded_output_paths(tmp_path)

    with pytest.raises(ValueError):
        converter.read_bounded_traces(
            "C:/pneuma-data/raw/swe-gym/OpenHands-Sampled-Trajectories/x.jsonl",
            1,
        )
    with pytest.raises(ValueError):
        converter.read_bounded_traces("C:/pneuma-data/processed/swe-chat/x.jsonl", 1)
    with pytest.raises(ValueError):
        converter.run_bounded_sample_conversion(
            input_path=FIXTURE,
            adapter_report_path=report_path,
            examples_path="C:/pneuma-data/processed/swe-gym/openhands-sampled/examples.jsonl",
            report_path=report,
            hash_manifest_path=manifest,
            limit=1,
        )
