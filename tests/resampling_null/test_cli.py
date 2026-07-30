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
