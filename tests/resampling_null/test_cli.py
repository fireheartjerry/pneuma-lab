"""Public fail-closed command surface for the conditional P0 controller."""

from __future__ import annotations

import json
from pathlib import Path


def test_cli_requires_a_root_and_emits_redacted_json_error(capsys) -> None:
    from pneuma_lab.resampling_null.cli import main

    assert main(["power", "screen"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert "traceback" not in payload


def test_cli_rejects_seed_and_outside_root_paths(tmp_path: Path, capsys) -> None:
    from pneuma_lab.resampling_null.cli import main

    root = tmp_path / "root"
    root.mkdir()
    assert main(["--run-root", str(root), "power", "screen", "--seed", "1"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_cli_status_is_a_successful_json_probe(tmp_path: Path, capsys) -> None:
    from pneuma_lab.resampling_null.cli import main

    assert main(["--run-root", str(tmp_path), "status"]) == 0
    assert json.loads(capsys.readouterr().out) == {"documents": 0, "status": "ok"}


def test_cli_rejects_noncanonical_paths_and_missing_final_refs(tmp_path: Path, capsys) -> None:
    from pneuma_lab.resampling_null.cli import _out, _shards, main
    from pneuma_lab.resampling_null.errors import RecordValidationError

    for value in ("", ".", "a//b", "a\\b", "../outside", "/absolute"):
        try:
            _out(tmp_path, value)
        except RecordValidationError:
            pass
        else:
            raise AssertionError(value)
    assert _shards(tmp_path, "bad") == ()
    (tmp_path / "already.json").write_text("{}", encoding="utf-8")
    try:
        _out(tmp_path, "already.json")
    except FileExistsError:
        pass
    else:
        raise AssertionError("existing output accepted")
    assert main([
        "--run-root", str(tmp_path), "power", "finalize", "--authority", "a.json",
        "--grid-ref", "g.json", "--screen-topology-ref", "t.json", "--out", "out.json",
        "--completed-full-multiplier",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_cli_selftest_surface_rejects_ambiguous_staging(tmp_path: Path, capsys) -> None:
    from pneuma_lab.resampling_null.cli import main

    assert main([
        "--run-root", str(tmp_path), "selftest", "--stop-after-study",
        "--defer-artifact-root",
    ]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"status": "error", "error": "invalid command arguments"}


def test_cli_selftest_stop_after_study_seals_only_manifest_and_inputs(
    tmp_path: Path, capsys,
) -> None:
    from pneuma_lab.resampling_null.cli import main

    assert main(["--run-root", str(tmp_path), "selftest", "--stop-after-study"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["output"] == "study-manifest.json"
    assert (tmp_path / "study-manifest.json").is_file()
    assert (tmp_path / "sources").is_dir()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["sources", "study-manifest.json"]


def test_cli_selftest_study_binds_frozen_p0_inputs_and_admits_power_config(
    tmp_path: Path, capsys,
) -> None:
    from pneuma_lab.resampling_null.cli import main
    from pneuma_lab.resampling_null.power import POWER_AUTHORITY_MEDIA_TYPE, load_power_config
    from pneuma_lab.resampling_null.types import ArtifactRef

    assert main(["--run-root", str(tmp_path), "selftest", "--stop-after-study"]) == 0
    capsys.readouterr()
    manifest = json.loads((tmp_path / "study-manifest.json").read_text(encoding="utf-8"))
    payload = manifest["payload"]
    grid = ArtifactRef(**payload["power_grid_ref"])
    topology = ArtifactRef(**payload["power_screen_topology_ref"])
    assert grid.sha256 == __import__("hashlib").sha256(
        (Path(__file__).parents[2] / "fixtures/resampling_null/p0-power-grid.json").read_bytes()
    ).hexdigest()
    assert topology.relative_path.endswith("p0-power-screen-topology.json")
    assert main([
        "--run-root", str(tmp_path), "power", "authority", "synthetic",
        "--study", "study-manifest.json", "--out", "power/authority.json",
    ]) == 0
    authority = ArtifactRef(**{
        "role": "power_authority", "relative_path": "power/authority.json",
        "sha256": json.loads(capsys.readouterr().out)["digest"],
        "byte_count": (tmp_path / "power/authority.json").stat().st_size,
        "media_type": POWER_AUTHORITY_MEDIA_TYPE,
    })
    assert load_power_config(authority, grid, topology, run_root=tmp_path)


def test_cli_selftest_stop_preflight_refuses_without_mutation(tmp_path: Path, capsys) -> None:
    from pneuma_lab.resampling_null.cli import main

    manifest = tmp_path / "study-manifest.json"
    manifest.write_bytes(b'{"prior":"bytes"}')
    before = manifest.read_bytes()
    assert main(["--run-root", str(tmp_path), "selftest", "--stop-after-study"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    assert manifest.read_bytes() == before
    assert sorted(path.name for path in tmp_path.iterdir()) == ["study-manifest.json"]


def test_cli_malformed_arguments_emit_only_one_redacted_json_object(capsys) -> None:
    from pneuma_lab.resampling_null.cli import main

    assert main(["--debug", "power", "screen"]) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "status": "error", "error": "invalid command arguments", "debug": "argument parsing failed",
    }


def test_cli_selftest_resume_requires_one_manifest_before_any_write(
    tmp_path: Path, capsys,
) -> None:
    from pneuma_lab.resampling_null.cli import main

    assert main([
        "--run-root", str(tmp_path), "selftest", "--resume-after-power",
        "power/p0-power-report.json", "--defer-artifact-root",
    ]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert "exactly one study manifest" in payload["error"]
    assert list(tmp_path.iterdir()) == []
