"""Public fail-closed command surface for the conditional P0 controller."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


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


def test_cli_selftest_uses_exact_frozen_roster_and_is_byte_deterministic(
    tmp_path: Path, capsys,
) -> None:
    from pneuma_lab.resampling_null.cli import main

    roots = (tmp_path / "one", tmp_path / "two")
    for root in roots:
        root.mkdir()
        assert main(["--run-root", str(root), "selftest", "--stop-after-study"]) == 0
        capsys.readouterr()
    expected = Path(__file__).parents[2] / "fixtures/resampling_null/p0-roster-synthetic.json"
    manifests = [json.loads((root / "study-manifest.json").read_text()) for root in roots]
    roster_refs = [manifest["payload"]["roster_ref"] for manifest in manifests]
    expected_digest = __import__("hashlib").sha256(expected.read_bytes()).hexdigest()
    assert [ref["sha256"] for ref in roster_refs] == [expected_digest, expected_digest]
    for root, ref in zip(roots, roster_refs, strict=True):
        roster = json.loads((root / ref["relative_path"]).read_text())
        assert len(roster["tasks"]) == 40
        assert {task["benchmark"] for task in roster["tasks"]} == {"SWE", "TAU"}
    assert (roots[0] / "study-manifest.json").read_bytes() == (roots[1] / "study-manifest.json").read_bytes()


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


def test_cli_descendant_commands_reject_missing_power_or_external_secret_before_write(
    tmp_path: Path, capsys,
) -> None:
    """No descendant may create an output until its authority inputs resolve."""
    from pneuma_lab.resampling_null.cli import main

    root = tmp_path / "root"
    root.mkdir()
    seed = tmp_path / "schedule-seed"
    seed.write_text("7\n", encoding="ascii")
    assert main([
        "--run-root", str(root), "schedule", "seal", "--study", "study.json",
        "--power-final", "power-final.json", "--schedule-seed-file", str(seed),
        "--out", "prefix-schedule.json",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    assert not (root / "prefix-schedule.json").exists()
    assert main([
        "--run-root", str(root), "assignment", "seal", "--schedule", "schedule.json",
        "--prefix-index", "prefix-index.json", "--assignment-key-file", str(root / "key"),
        "--out", "assignment.json",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    assert not (root / "assignment.json").exists()


def test_cli_descendant_commands_are_present_and_require_ref_only_inputs(
    tmp_path: Path, capsys,
) -> None:
    from pneuma_lab.resampling_null.cli import main

    root = tmp_path / "root"
    root.mkdir()
    assert main([
        "--run-root", str(root), "synthetic", "prefixes", "--study", "study.json",
        "--schedule", "schedule.json", "--out", "prefix-index.json",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_cli_parses_only_the_registered_schedule_prefix_and_assignment_surface() -> None:
    from pneuma_lab.resampling_null.cli import _parser

    parser = _parser()
    schedule = parser.parse_args([
        "--run-root", "/tmp/root", "schedule", "seal", "--study", "study.json",
        "--power-final", "power-final.json", "--schedule-seed-file", "/tmp/seed",
        "--out", "prefix-schedule.json",
    ])
    prefixes = parser.parse_args([
        "--run-root", "/tmp/root", "synthetic", "prefixes", "--study", "study.json",
        "--schedule", "prefix-schedule.json", "--out", "prefix-index.json",
    ])
    assignment = parser.parse_args([
        "--run-root", "/tmp/root", "assignment", "seal", "--schedule", "prefix-schedule.json",
        "--prefix-index", "prefix-index.json", "--assignment-key-file", "/tmp/key",
        "--out", "assignment-ledger.json",
    ])
    assert (schedule.command, prefixes.command, assignment.command) == (
        "schedule", "synthetic", "assignment",
    )


def test_cli_packets_surface_accepts_only_sealed_root_references() -> None:
    from pneuma_lab.resampling_null.cli import _parser

    parser = _parser()
    build = parser.parse_args([
        "--run-root", "/tmp/root", "packets", "build", "--study", "study.json",
        "--assignment", "assignment.json", "--prefix-index", "prefix.json",
        "--out-candidate", "packet-candidate.json",
    ])
    audit = parser.parse_args([
        "--run-root", "/tmp/root", "packets", "audit", "--study", "study.json",
        "--candidate", "packet-candidate.json", "--schedule", "schedule.json",
        "--assignment", "assignment.json", "--prefix-index", "prefix.json",
        "--out-index", "packet-index.json",
    ])
    assert (build.command, build.packets_command) == ("packets", "build")
    assert (audit.command, audit.packets_command) == ("packets", "audit")


def test_cli_analysis_surface_exposes_only_registered_external_inputs() -> None:
    """The clear-ledger/project controls are controller-owned, never argv knobs."""
    from pneuma_lab.resampling_null.cli import _parser

    parser = _parser()
    freeze = parser.parse_args([
        "--run-root", "/tmp/root", "analysis", "freeze", "--source-root", "/tmp/src",
        "--source", "analysis.py", "--config", "/tmp/config.json",
        "--projection-schema", "/tmp/projection.json", "--packet-index", "packet.json",
        "--out", "freeze.json",
    ])
    branches = parser.parse_args([
        "--run-root", "/tmp/root", "synthetic", "branches", "--study", "study.json",
        "--schedule", "schedule.json", "--assignment", "assignment.json",
        "--prefix-index", "prefix.json", "--packet-index", "packet.json",
        "--analysis-freeze", "freeze.json", "--out-prefix", "task-blocks",
    ])
    project = parser.parse_args([
        "--run-root", "/tmp/root", "project", "seal", "--schedule", "schedule.json",
        "--analysis-freeze", "freeze.json", "--task-block-prefix", "task-blocks",
        "--out", "projection.json",
    ])
    analyze = parser.parse_args([
        "--run-root", "/tmp/root", "analyze", "--study", "study.json",
        "--projection", "projection.json", "--assignment", "assignment.json",
        "--analysis-freeze", "freeze.json", "--source-root", "/tmp/src",
        "--source", "analysis.py", "--config", "/tmp/config.json",
        "--projection-schema", "/tmp/projection.json", "--packet-index", "packet.json",
        "--assignment-key-file", "/tmp/assignment-key", "--unblind-receipt", "unblind.json",
        "--out", "analysis.json",
    ])
    assert (freeze.command, freeze.analysis_command) == ("analysis", "freeze")
    assert (branches.command, branches.synthetic_command) == ("synthetic", "branches")
    assert (project.command, project.project_command) == ("project", "seal")
    assert analyze.command == "analyze"
    for parsed in (project, analyze):
        assert "assignment_key" not in vars(parsed) or parsed is analyze
    assert "assignment_key_file" not in vars(project)


def test_cli_synthetic_branches_is_fail_closed_without_branch_executor(
    tmp_path: Path, capsys, monkeypatch,
) -> None:
    """A parser surface must not pretend the absent Task-5 executor ran."""
    import pneuma_lab.resampling_null.cli as cli
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "root"
    root.mkdir()
    ref = ArtifactRef("test", "x.json", "a" * 64, 1, "application/json")
    monkeypatch.setattr(cli, "_ref", lambda *_args: ref)
    assert cli.main([
        "--run-root", str(root), "synthetic", "branches", "--study", "study.json",
        "--schedule", "schedule.json", "--assignment", "assignment.json",
        "--prefix-index", "prefix.json", "--packet-index", "packet.json",
        "--analysis-freeze", "freeze.json", "--out-prefix", "task-blocks",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["error"] == "synthetic branch executor is not installed"


def test_cli_analyze_does_not_decode_ledger_before_guard(
    tmp_path: Path, monkeypatch,
) -> None:
    """The CLI may bind the opaque ledger ref, but cannot parse it itself."""
    import stat
    from dataclasses import dataclass
    from types import SimpleNamespace
    import pneuma_lab.resampling_null.cli as cli
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "root"
    root.mkdir()
    key = tmp_path / "key"
    key.write_bytes(b"k" * 32)
    key.chmod(stat.S_IRUSR | stat.S_IWUSR)
    refs = {
        name: ArtifactRef(role, name, char * 64, 1, "application/json")
        for name, role, char in (
            ("study.json", "study_manifest", "a"), ("projection.json", "blinded_projection", "b"),
            ("assignment.json", "resampling_assignment_ledger", "c"), ("freeze.json", "analysis_freeze", "d"),
            ("packet.json", "packet_index_sealed", "e"), ("schedule.json", "resampling_prefix_schedule", "f"),
            ("prefix.json", "prefix_index", "1"), ("power.json", "power_report", "2"),
            ("config.json", "analysis_source", "3"), ("receipt.json", "unblind_receipt", "4"),
        )
    }
    def record(ref, *, root, kind):
        if kind == "resampling_assignment_ledger":
            pytest.fail("CLI decoded clear assignment ledger")
        if kind == "resampling_blinded_projection":
            return {"payload": {"analysis_freeze_ref": vars_ref(refs["freeze.json"]), "schedule_ref": vars_ref(refs["schedule.json"]), "expected_task_count": 1}}
        if kind == "resampling_prefix_schedule":
            return {"payload": {"manifest_ref": vars_ref(refs["study.json"]), "power_final_ref": vars_ref(refs["power.json"])}}
        if kind == "resampling_packet_index":
            return {"payload": {"stage": "sealed", "assignment_ref": vars_ref(refs["assignment.json"]), "prefix_index_ref": vars_ref(refs["prefix.json"])}}
        if kind == "resampling_analysis_freeze":
            return {"payload": {"config_ref": vars_ref(refs["config.json"])}}
        if kind == "resampling_study_manifest":
            return {"study_id": "s", "frozen_created_at": "2026-01-01T00:00:00Z", "provenance": {"code_sha256": "0" * 64, "design_sha256": "1" * 64}, "payload": {}}
        raise AssertionError(kind)
    def vars_ref(ref):
        return {"role": ref.role, "relative_path": ref.relative_path, "sha256": ref.sha256, "byte_count": ref.byte_count, "media_type": ref.media_type}
    monkeypatch.setattr(cli, "_ref", lambda _root, name, _role: refs[name])
    monkeypatch.setattr(cli, "_record_for_ref", record)
    monkeypatch.setattr(cli, "_external_sources", lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, "_external_file", lambda value, **kwargs: key)
    monkeypatch.setattr(cli, "_analysis_config", lambda _path: (object(), 0))
    monkeypatch.setattr(cli, "issue_unblind_permit", lambda *args, **kwargs: "permit")
    monkeypatch.setattr(cli, "unblind_projection", lambda *args, **kwargs: SimpleNamespace(receipt_ref=refs["receipt.json"], rows=()))
    @dataclass
    class _Result:
        marker: int = 1
    monkeypatch.setattr(cli, "analyze_rows", lambda *args, **kwargs: _Result())
    monkeypatch.setattr(cli, "write_record", lambda *args, **kwargs: refs["config.json"])
    args = SimpleNamespace(command="analyze", study="study.json", projection="projection.json",
        assignment="assignment.json", analysis_freeze="freeze.json", packet_index="packet.json",
        source_root="ignored", source=["ignored"], config="ignored", projection_schema="ignored",
        assignment_key_file=str(key), unblind_receipt="receipt.json", out="analysis.json")
    assert cli._dispatch(args, root) == refs["config.json"]


def test_cli_packets_rejects_noncanonical_root_names_before_writing(
    tmp_path: Path, capsys,
) -> None:
    from pneuma_lab.resampling_null.cli import main

    root = tmp_path / "root"
    root.mkdir()
    assert main([
        "--run-root", str(root), "packets", "build", "--study", "../study.json",
        "--assignment", "assignment.json", "--prefix-index", "prefix.json",
        "--out-candidate", "packet-candidate.json",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    assert not (root / "packet-candidate.json").exists()


def test_cli_packets_build_reserves_existing_candidate_before_packet_work(
    tmp_path: Path, capsys, monkeypatch,
) -> None:
    """An occupied final name cannot leave build sidecars behind."""
    import pneuma_lab.resampling_null.cli as cli
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "root"
    root.mkdir()
    for name in ("study.json", "assignment.json", "prefix.json", "candidate.json"):
        (root / name).write_text("{}", encoding="utf-8")
    refs = {
        name: ArtifactRef("test", name, "a" * 64, 2, "application/json")
        for name in ("study.json", "assignment.json", "prefix.json")
    }
    called = False
    monkeypatch.setattr(cli, "_ref", lambda _root, name, _role: refs[name])
    monkeypatch.setattr(
        cli, "_packet_manifest_parents",
        lambda *_args, **_kwargs: tuple(
            ArtifactRef(role, f"{role}.json", digest * 64, 1, "application/json")
            for role, digest in (("tokenizer", "b"), ("template", "c"), ("policy", "d"), ("pad", "e"))
        ),
    )
    def build(**_kwargs: object) -> ArtifactRef:
        nonlocal called
        called = True
        (root / "packet-work").mkdir()
        raise AssertionError("build must not run")
    monkeypatch.setattr(cli, "_build_packet_candidate", build)

    before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
    assert cli.main([
        "--run-root", str(root), "packets", "build", "--study", "study.json",
        "--assignment", "assignment.json", "--prefix-index", "prefix.json",
        "--out-candidate", "candidate.json",
    ]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "error"
    assert not called
    assert sorted(path.relative_to(root).as_posix() for path in root.rglob("*")) == before


def test_cli_packets_build_and_audit_route_exact_manifest_parents(
    tmp_path: Path, capsys, monkeypatch,
) -> None:
    """CLI derives packet authority only from the supplied sealed root refs."""
    import pneuma_lab.resampling_null.cli as cli
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "root"
    root.mkdir()
    for name in ("study.json", "assignment.json", "prefix.json", "schedule.json", "candidate.json"):
        (root / name).write_text("{}", encoding="utf-8")
    refs = {
        name: ArtifactRef("test", name, "a" * 64, 2, "application/json")
        for name in ("study.json", "assignment.json", "prefix.json", "schedule.json", "candidate.json")
    }
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli, "_ref", lambda _root, name, _role: refs[name])
    monkeypatch.setattr(
        cli, "_packet_manifest_parents",
        lambda study, assignment, prefix, *, root: (
            seen.setdefault("parents", (study, assignment, prefix)),
            (ArtifactRef("tokenizer", "tokenizer.json", "b" * 64, 1, "application/json"),
             ArtifactRef("template", "template.json", "c" * 64, 1, "application/json"),
             ArtifactRef("policy", "policy.json", "d" * 64, 1, "application/json"),
             ArtifactRef("pad", "pad.json", "e" * 64, 1, "application/json")),
        )[1],
    )
    candidate = ArtifactRef("packet_index_candidate", "packet-candidate.json", "f" * 64, 1, "application/json")
    sealed = ArtifactRef("packet_index_sealed", "packet-index.json", "1" * 64, 1, "application/json")
    monkeypatch.setattr(cli, "_build_packet_candidate", lambda **kwargs: (seen.setdefault("build", kwargs), candidate)[1])
    monkeypatch.setattr(cli, "audit_and_seal_packet_index", lambda candidate_ref, **kwargs: (seen.setdefault("audit", (candidate_ref, kwargs)), sealed)[1])
    monkeypatch.setattr(cli, "_schedule_task_ids", lambda schedule, study, *, root: ("t1",))

    assert cli.main([
        "--run-root", str(root), "packets", "build", "--study", "study.json",
        "--assignment", "assignment.json", "--prefix-index", "prefix.json",
        "--out-candidate", "packet-candidate.json",
    ]) == 0
    assert json.loads(capsys.readouterr().out)["output"] == "packet-candidate.json"
    assert seen["parents"] == (refs["study.json"], refs["assignment.json"], refs["prefix.json"])
    assert seen["build"]["assignment_ref"] == refs["assignment.json"]

    assert cli.main([
        "--run-root", str(root), "packets", "audit", "--study", "study.json",
        "--candidate", "candidate.json", "--schedule", "schedule.json",
        "--assignment", "assignment.json", "--prefix-index", "prefix.json",
        "--out-index", "packet-index.json",
    ]) == 0
    assert json.loads(capsys.readouterr().out)["output"] == "packet-index.json"
    assert seen["audit"][0] == refs["candidate.json"]
    assert seen["audit"][1]["expected_task_ids"] == ("t1",)


def test_cli_schedule_success_routes_only_bound_refs_and_external_seed(
    tmp_path: Path, capsys, monkeypatch,
) -> None:
    """The CLI can only hand the sealed API opaque root refs and a revealed seed."""
    import pneuma_lab.resampling_null.cli as cli
    from pneuma_lab.resampling_null.types import ArtifactRef

    root = tmp_path / "root"
    root.mkdir()
    (root / "study.json").write_text("{}", encoding="utf-8")
    (root / "power-final.json").write_text("{}", encoding="utf-8")
    seed = tmp_path / "schedule-seed"
    seed.write_text("7\n", encoding="ascii")
    seen: dict[str, object] = {}
    monkeypatch.setattr(cli, "require_schedulable_power_final", lambda *args, **kwargs: seen.setdefault("authority", args))
    monkeypatch.setattr(cli, "claim_local_test_storage", lambda **kwargs: seen.setdefault("lease", kwargs))

    def seal(manifest, final, *, schedule_seed_reveal, storage_policy_lease, run_root, out):
        seen.update(manifest=manifest, final=final, seed=schedule_seed_reveal, out=out)
        return ArtifactRef("resampling_prefix_schedule", "prefix-schedule.json", "a" * 64, 1, "application/json")

    monkeypatch.setattr(cli, "seal_prefix_schedule", seal)
    assert cli.main([
        "--run-root", str(root), "schedule", "seal", "--study", "study.json",
        "--power-final", "power-final.json", "--schedule-seed-file", str(seed),
        "--out", "prefix-schedule.json",
    ]) == 0
    assert json.loads(capsys.readouterr().out)["output"] == "prefix-schedule.json"
    assert seen["seed"] == 7
    assert seen["out"] == root / "prefix-schedule.json"


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
