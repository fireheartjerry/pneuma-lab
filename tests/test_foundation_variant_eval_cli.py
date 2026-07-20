"""Fail-closed argument validation for the ``variant-eval`` CLI verb."""

from __future__ import annotations

import argparse
import json
from dataclasses import fields
from pathlib import Path

import pytest

from pneuma_lab.foundation.cli import CommandHandlers, _parser, main


def _handlers(calls: list) -> CommandHandlers:
    def recorder(name: str):
        def handler(args: argparse.Namespace):
            calls.append(name)
            return None

        return handler

    return CommandHandlers(
        **{field.name: recorder(field.name) for field in fields(CommandHandlers)}
    )


def _line(run: str = "run-dir", output: str = "out-dir", **extra) -> list[str]:
    line = [
        "variant-eval",
        "--stage",
        "2m",
        "--authorization",
        "auth.json",
        "--run",
        run,
        "--output",
        output,
    ]
    for flag, value in extra.items():
        line.extend([f"--{flag.replace('_', '-')}", value])
    return line


def test_variant_eval_command_is_registered() -> None:
    help_text = _parser().format_help()
    assert "variant-eval" in help_text


def test_variant_eval_dispatches_only_its_own_handler() -> None:
    calls: list[str] = []
    assert main(_line(), handlers=_handlers(calls)) == 0
    assert calls == ["variant_eval"]


@pytest.mark.parametrize(
    "line",
    (
        ["variant-eval"],
        ["variant-eval", "--stage", "2m"],
        ["variant-eval", "--stage", "2m", "--authorization", "auth.json"],
        [
            "variant-eval",
            "--authorization",
            "auth.json",
            "--run",
            "run-dir",
            "--output",
            "out-dir",
        ],
    ),
)
def test_variant_eval_requires_every_argument(line: list[str]) -> None:
    with pytest.raises(SystemExit):
        main(line, handlers=_handlers([]))


@pytest.mark.parametrize("stage", ("100k", "500k", "1m"))
def test_variant_eval_rejects_pre_gate_stages(stage: str) -> None:
    line = _line()
    line[line.index("2m")] = stage
    with pytest.raises(SystemExit):
        main(line, handlers=_handlers([]))


def test_default_handler_requires_shard_flags_together(
    tmp_path: Path,
    capsys,
) -> None:
    assert (
        main(
            _line(
                run=str(tmp_path / "run"),
                output=str(tmp_path / "out"),
                shard=str(tmp_path / "shard.jsonl"),
            )
        )
        == 2
    )
    assert "together" in capsys.readouterr().err


def test_default_handler_blocks_on_missing_run_manifest(
    tmp_path: Path,
    capsys,
) -> None:
    assert main(_line(run=str(tmp_path / "run"), output=str(tmp_path / "out"))) == 2
    error = capsys.readouterr().err
    assert "BLOCKED" in error
    assert "run manifest" in error


def test_default_handler_blocks_on_stage_mismatch(
    tmp_path: Path,
    capsys,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "foundation-100k-a",
                "curriculum": {"stage": "100k"},
                "checkpoints": {"last_path": "checkpoint.pt"},
            }
        ),
        encoding="utf-8",
    )
    assert main(_line(run=str(run_root), output=str(tmp_path / "out"))) == 2
    assert "differs from --stage" in capsys.readouterr().err


def test_default_handler_blocks_without_a_recorded_checkpoint(
    tmp_path: Path,
    capsys,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "foundation-2m-a",
                "curriculum": {"stage": "2m"},
                "checkpoints": {"last_path": None},
            }
        ),
        encoding="utf-8",
    )
    assert main(_line(run=str(run_root), output=str(tmp_path / "out"))) == 2
    assert "no last checkpoint" in capsys.readouterr().err


def test_default_handler_blocks_on_a_missing_checkpoint_file(
    tmp_path: Path,
    capsys,
) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    (run_root / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "foundation-2m-a",
                "curriculum": {"stage": "2m"},
                "checkpoints": {
                    "last_path": str(run_root / "checkpoints" / "missing.pt")
                },
            }
        ),
        encoding="utf-8",
    )
    assert main(_line(run=str(run_root), output=str(tmp_path / "out"))) == 2
    assert "checkpoint is missing" in capsys.readouterr().err
