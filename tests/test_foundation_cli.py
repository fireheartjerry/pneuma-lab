"""Strict command separation for the complete foundation CLI."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import fields
from pathlib import Path

import pytest

from pneuma_lab.foundation import cli
from pneuma_lab.foundation.cli import (
    CommandHandlers,
    _parser,
    derive_final_authorization_path,
    main,
    render_command_result,
)


REQUIRED_COMMANDS = {
    "doctor",
    "duration",
    "setup-plan",
    "prepare",
    "preflight",
    "download-model",
    "dry-run",
    "authorization-candidate",
    "authorization-finalize",
    "train",
    "resume",
    "evaluate",
    "report",
    "cloud-bundle",
}

_COMMAND_LINES = {
    "doctor": ["doctor"],
    "setup_plan": ["setup-plan"],
    "prepare": ["prepare", "--stage", "100k", "--data-root", "data"],
    "preflight": [
        "preflight",
        "--stage",
        "100k",
        "--authorization",
        "auth.json",
        "--lr",
        "1e-4",
    ],
    "download_model": ["download-model", "--model", "2b"],
    "dry_run": ["dry-run", "--stage", "100k"],
    "authorization_candidate": ["authorization-candidate", "--stage", "100k"],
    "authorization_finalize": [
        "authorization-finalize",
        "--candidate",
        "candidate.json",
        "--scope-digest",
        "d" * 64,
        "--approval-phrase",
        "PHRASE",
        "--operator-id",
        "operator",
    ],
    "train": [
        "train",
        "--stage",
        "100k",
        "--authorization",
        "auth.json",
        "--lr",
        "5e-5",
    ],
    "resume": [
        "resume",
        "--authorization",
        "auth.json",
        "--checkpoint",
        "checkpoint.pt",
    ],
    "evaluate": ["evaluate", "--run", "run-dir"],
    "report": ["report", "--run", "run-dir"],
    "cloud_bundle": [
        "cloud-bundle",
        "--stage",
        "2m",
        "--authorization",
        "auth.json",
        "--quoted-hourly-usd",
        "0.44",
        "--quoted-tax-inclusive-usd",
        "44.10",
    ],
}


def _subcommand_names(parser: argparse.ArgumentParser) -> set[str]:
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return set(action.choices)
    return set()


def _handlers(calls: list, results: dict | None = None) -> CommandHandlers:
    results = dict(results or {})
    results.setdefault("doctor", {"ready": True, "blockers": []})

    def recorder(name: str):
        def handler(args: argparse.Namespace):
            calls.append(name)
            return results.get(name)

        return handler

    return CommandHandlers(
        **{field.name: recorder(field.name) for field in fields(CommandHandlers)}
    )


def _capturing_handlers(calls: list, seen: dict) -> CommandHandlers:
    def recorder(name: str):
        def handler(args: argparse.Namespace):
            calls.append(name)
            seen[name] = args
            return None

        return handler

    return CommandHandlers(
        **{field.name: recorder(field.name) for field in fields(CommandHandlers)}
    )


def test_cli_exposes_every_documented_command() -> None:
    help_text = _parser().format_help()
    assert REQUIRED_COMMANDS.issubset(set(_subcommand_names(_parser())))
    assert "397b" not in help_text.casefold()


def test_prepare_and_dry_run_cannot_fall_through_to_train(tmp_path: Path) -> None:
    calls = []
    handlers = _handlers(calls)
    assert (
        main(
            ["prepare", "--stage", "100k", "--data-root", str(tmp_path)],
            handlers=handlers,
        )
        == 0
    )
    assert main(["dry-run", "--stage", "100k"], handlers=handlers) == 0
    assert calls == ["prepare", "dry_run"]


@pytest.mark.parametrize("handler_name", sorted(_COMMAND_LINES))
def test_every_command_dispatches_only_its_own_handler(handler_name: str) -> None:
    calls = []
    assert main(_COMMAND_LINES[handler_name], handlers=_handlers(calls)) == 0
    assert calls == [handler_name]


def test_duration_prints_hours_without_touching_handlers(capsys) -> None:
    calls = []
    assert (
        main(
            ["duration", "--tokens", "8000000", "--tps", "20"],
            handlers=_handlers(calls),
        )
        == 0
    )
    assert "111.11 hours" in capsys.readouterr().out
    assert calls == []


def test_doctor_preserves_ready_and_blocked_exit_codes(capsys) -> None:
    ready = _handlers([], {"doctor": {"ready": True, "blockers": []}})
    assert main(["doctor"], handlers=ready) == 0
    assert "READY" in capsys.readouterr().out
    blocked = _handlers(
        [],
        {"doctor": {"ready": False, "blockers": ["cuda_required"]}},
    )
    assert main(["doctor"], handlers=blocked) == 1
    output = capsys.readouterr().out
    assert "BLOCKED" in output
    assert "- cuda_required" in output


def test_doctor_json_rendering_matches_previous_module_cli(capsys) -> None:
    handlers = _handlers(
        [],
        {"doctor": {"ready": True, "blockers": [], "profile": "cloud"}},
    )
    assert main(["doctor", "--profile", "cloud", "--json"], handlers=handlers) == 0
    assert '"profile": "cloud"' in capsys.readouterr().out


@pytest.mark.parametrize(
    "error", (ValueError("nope"), RuntimeError("nope"), OSError("nope"))
)
def test_handler_failures_are_blocked_with_exit_2(error, capsys) -> None:
    handlers = _handlers([])
    handlers = CommandHandlers(
        **{
            field.name: (
                (lambda args, error=error: (_ for _ in ()).throw(error))
                if field.name == "prepare"
                else getattr(handlers, field.name)
            )
            for field in fields(CommandHandlers)
        }
    )
    assert (
        main(
            ["prepare", "--stage", "100k", "--data-root", "data"],
            handlers=handlers,
        )
        == 2
    )
    assert "BLOCKED: nope" in capsys.readouterr().err


def test_unexpected_handler_exceptions_propagate() -> None:
    handlers = _handlers([])
    handlers = CommandHandlers(
        **{
            field.name: (
                (lambda args: (_ for _ in ()).throw(TypeError("bug")))
                if field.name == "prepare"
                else getattr(handlers, field.name)
            )
            for field in fields(CommandHandlers)
        }
    )
    with pytest.raises(TypeError):
        main(["prepare", "--stage", "100k", "--data-root", "data"], handlers=handlers)


def test_cloud_candidate_requires_all_four_cloud_arguments(capsys) -> None:
    calls = []
    assert (
        main(
            ["authorization-candidate", "--stage", "2m", "--profile", "cloud"],
            handlers=_handlers(calls),
        )
        == 2
    )
    assert calls == []
    assert "BLOCKED" in capsys.readouterr().err


def test_local_candidate_rejects_cloud_only_arguments(capsys) -> None:
    calls = []
    assert (
        main(
            [
                "authorization-candidate",
                "--stage",
                "2m",
                "--quoted-hourly-usd",
                "0.44",
            ],
            handlers=_handlers(calls),
        )
        == 2
    )
    assert calls == []
    assert "BLOCKED" in capsys.readouterr().err


def test_learning_rate_choices_parse_scientific_notation() -> None:
    calls = []
    seen = {}
    handlers = _capturing_handlers(calls, seen)
    line = [
        "preflight",
        "--stage",
        "100k",
        "--authorization",
        "auth.json",
        "--lr",
        "5e-5",
    ]
    assert main(line, handlers=handlers) == 0
    assert seen["preflight"].lr == pytest.approx(5e-5)
    with pytest.raises(SystemExit):
        main(
            [
                "preflight",
                "--stage",
                "100k",
                "--authorization",
                "auth.json",
                "--lr",
                "3e-4",
            ],
            handlers=handlers,
        )


def test_stage_choices_reject_unlisted_stages() -> None:
    with pytest.raises(SystemExit):
        main(
            ["prepare", "--stage", "1m", "--data-root", "data"],
            handlers=_handlers([]),
        )
    with pytest.raises(SystemExit):
        main(
            ["dry-run", "--stage", "500k"],
            handlers=_handlers([]),
        )


def test_final_authorization_path_derivation(tmp_path: Path) -> None:
    candidates = tmp_path / "build" / "foundation" / "authorizations" / "candidates"
    local = candidates / "2m.json"
    cloud = candidates / "2m-cloud.json"
    final_root = candidates.parent / "final"
    assert derive_final_authorization_path(local) == final_root / "2m.json"
    assert derive_final_authorization_path(cloud) == final_root / "2m-cloud.json"
    assert derive_final_authorization_path(local) != local
    assert derive_final_authorization_path(cloud) != cloud


def test_final_authorization_path_rejects_non_candidate_inputs(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="candidates"):
        derive_final_authorization_path(tmp_path / "final" / "2m.json")
    with pytest.raises(ValueError, match="JSON"):
        derive_final_authorization_path(tmp_path / "candidates" / "2m.txt")


def test_finalize_derives_output_and_never_overwrites_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate = (
        tmp_path
        / "build"
        / "foundation"
        / "authorizations"
        / "candidates"
        / "2m-cloud.json"
    )
    captured = {}

    def fake_finalize(
        candidate_path,
        supplied_scope_digest,
        supplied_approval_phrase,
        operator_id,
        approved_at,
        output_path,
    ):
        captured["candidate_path"] = Path(candidate_path)
        captured["scope_digest"] = supplied_scope_digest
        captured["approval_phrase"] = supplied_approval_phrase
        captured["operator_id"] = operator_id
        captured["approved_at"] = approved_at
        captured["output_path"] = Path(output_path)
        return Path(output_path)

    monkeypatch.setattr(
        "pneuma_lab.foundation.cli._finalize_authorization",
        fake_finalize,
    )
    assert (
        main(
            [
                "authorization-finalize",
                "--candidate",
                str(candidate),
                "--scope-digest",
                "a" * 64,
                "--approval-phrase",
                "I APPROVE THIS EXACT PNEUMA FOUNDATION SCOPE " + "a" * 64,
                "--operator-id",
                "operator",
            ]
        )
        == 0
    )
    assert captured["candidate_path"] == candidate
    assert captured["output_path"] == (
        candidate.parent.parent / "final" / "2m-cloud.json"
    )
    assert captured["output_path"] != captured["candidate_path"]
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
        captured["approved_at"],
    )


def test_evaluate_default_handler_reads_persisted_validation_batches(
    tmp_path: Path,
) -> None:
    run_root = tmp_path / "build" / "foundation" / "runs" / "foundation-100k-a"
    run_root.mkdir(parents=True)
    manifest = {
        "run_id": "foundation-100k-a",
        "curriculum": {"stage": "100k"},
        "latency": {},
    }
    (run_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run_root / "validation_batches.json").write_text(
        json.dumps([{"token_count": 128, "validation_loss": 2.5}]),
        encoding="utf-8",
    )
    assert main(["evaluate", "--run", str(run_root)]) == 0
    report = json.loads(
        (run_root / "evaluation_report.json").read_text(encoding="utf-8")
    )
    assert report["run_id"] == "foundation-100k-a"
    assert report["metrics"]["validation_loss"] == pytest.approx(2.5)
    assert report["claim_boundary"]["no_consciousness_claim"] is True


def test_evaluate_fails_closed_without_validation_batches(
    tmp_path: Path,
    capsys,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "manifest.json").write_text(
        json.dumps({"run_id": "foundation-100k-a", "curriculum": {"stage": "100k"}}),
        encoding="utf-8",
    )
    assert main(["evaluate", "--run", str(run_root)]) == 2
    assert "validation_batches.json" in capsys.readouterr().err


def test_download_model_dry_run_verifies_offline_and_fails_closed(
    tmp_path: Path,
    capsys,
) -> None:
    assert (
        main(
            [
                "download-model",
                "--model",
                "2b",
                "--dry-run",
                "--cache-root",
                str(tmp_path / "cache"),
            ]
        )
        == 2
    )
    assert "BLOCKED" in capsys.readouterr().err


def test_cloud_bundle_default_handler_fails_closed(capsys) -> None:
    assert (
        main(
            [
                "cloud-bundle",
                "--stage",
                "2m",
                "--authorization",
                "missing.json",
                "--quoted-hourly-usd",
                "0.44",
                "--quoted-tax-inclusive-usd",
                "44.10",
            ]
        )
        == 2
    )
    assert "BLOCKED" in capsys.readouterr().err


def test_render_command_result_serializes_paths(capsys) -> None:
    render_command_result({"shard": Path("build") / "shard.jsonl"}, as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert payload["shard"].replace("\\", "/") == "build/shard.jsonl"


def test_module_entrypoint_reexports_cli_main() -> None:
    from pneuma_lab.foundation.__main__ import main as module_main

    assert module_main is main


def test_cli_help_never_imports_the_model_stack() -> None:
    source_root = Path(cli.__file__).resolve().parents[2]
    code = (
        "import sys\n"
        "for name in ('torch', 'transformers', 'huggingface_hub',"
        " 'bitsandbytes', 'peft', 'accelerate'):\n"
        "    sys.modules[name] = None\n"
        "from pneuma_lab.foundation.cli import _parser\n"
        "help_text = _parser().format_help()\n"
        "assert 'train' in help_text and 'cloud-bundle' in help_text\n"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = (
        str(source_root) + os.pathsep + environment.get("PYTHONPATH", "")
    )
    completed = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=environment,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
