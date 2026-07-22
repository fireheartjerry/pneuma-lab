"""Operator-guide drift checker and marked-guide tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from pneuma_lab.foundation.cli import build_parser
from pneuma_lab.foundation.operator_guide import (
    REQUIRED_GUIDE_COMMANDS,
    OperatorGuideError,
    check_operator_guide,
    guide_problems,
    main,
)

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "START-HERE-TRAINING.md"


def _parser():
    return build_parser()


def test_operator_guide_is_marked_and_last_action_is_train() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert text.startswith(
        "# LOCAL LADDER COMPLETE THROUGH 8M — DOUBLING GATE STOPPED THE LADDER"
    )
    assert "No Jupyter notebook is required." in text
    checklist = [line for line in text.splitlines() if line.startswith("- [")]
    assert checklist[-1].startswith("- [ ] `python -m pneuma_lab.foundation train")


def test_guide_commands_match_cli() -> None:
    report = check_operator_guide(GUIDE, parser=_parser())
    assert report == {"valid": True, "unknown_commands": [], "missing_commands": []}


def test_required_commands_cover_the_full_cli_surface() -> None:
    assert REQUIRED_GUIDE_COMMANDS == {
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


def _write_guide(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_checker_flags_unknown_commands(tmp_path: Path) -> None:
    broken = GUIDE.read_text(encoding="utf-8").replace(
        "python -m pneuma_lab.foundation doctor\n",
        "python -m pneuma_lab.foundation demolish --now\n",
        1,
    )
    report = check_operator_guide(
        _write_guide(tmp_path / "guide.md", broken), parser=_parser()
    )
    assert report["valid"] is False
    assert any("demolish" in value for value in report["unknown_commands"])


def test_checker_flags_missing_commands(tmp_path: Path) -> None:
    trimmed = GUIDE.read_text(encoding="utf-8").replace(
        "python -m pneuma_lab.foundation cloud-bundle", "echo skipped"
    )
    report = check_operator_guide(
        _write_guide(tmp_path / "guide.md", trimmed), parser=_parser()
    )
    assert report["valid"] is False
    assert report["missing_commands"] == ["cloud-bundle"]


def test_checker_confines_finalize_variables_to_the_finalize_section(
    tmp_path: Path,
) -> None:
    leaked = GUIDE.read_text(encoding="utf-8") + (
        '\n\n```bash\necho "$PNEUMA_SCOPE_DIGEST"\n```\n'
    )
    problems = guide_problems(
        _write_guide(tmp_path / "guide.md", leaked), parser=_parser()
    )
    assert any("finalization sequence" in value for value in problems)


def test_checker_requires_the_paste_paragraph(tmp_path: Path) -> None:
    silent = GUIDE.read_text(encoding="utf-8").replace(
        "Paste exactly the two values printed by `authorization-candidate`",
        "Provide the required values",
    )
    problems = guide_problems(
        _write_guide(tmp_path / "guide.md", silent), parser=_parser()
    )
    assert any("authorization-candidate" in value for value in problems)


def test_checker_requires_the_unchecked_train_tail(tmp_path: Path) -> None:
    checked = GUIDE.read_text(encoding="utf-8").replace(
        "- [ ] `python -m pneuma_lab.foundation train",
        "- [x] `python -m pneuma_lab.foundation train",
    )
    problems = guide_problems(
        _write_guide(tmp_path / "guide.md", checked), parser=_parser()
    )
    assert any("unchecked train" in value for value in problems)


def test_checker_requires_ordered_headings(tmp_path: Path) -> None:
    shuffled = GUIDE.read_text(encoding="utf-8").replace(
        "## 5. Close GPU-heavy Windows applications", "## 5. Renamed"
    )
    problems = guide_problems(
        _write_guide(tmp_path / "guide.md", shuffled), parser=_parser()
    )
    assert any("Close GPU-heavy" in value for value in problems)


def test_checker_rejects_unterminated_fences(tmp_path: Path) -> None:
    with pytest.raises(OperatorGuideError, match="fence"):
        check_operator_guide(
            _write_guide(tmp_path / "guide.md", "# TRAINING HAS NOT STARTED\n```\n"),
            parser=_parser(),
        )


def test_checker_rejects_missing_guides(tmp_path: Path) -> None:
    with pytest.raises(OperatorGuideError, match="read"):
        guide_problems(tmp_path / "absent.md", parser=_parser())


def test_module_main_exit_codes(tmp_path: Path, capsys) -> None:
    assert main([str(GUIDE)]) == 0
    assert '"valid": true' in capsys.readouterr().out
    broken = GUIDE.read_text(encoding="utf-8").replace(
        "# LOCAL LADDER COMPLETE THROUGH 8M", "# stage truth removed", 1
    )
    assert main([str(_write_guide(tmp_path / "guide.md", broken))]) == 1
    captured = capsys.readouterr()
    assert '"valid": false' in captured.out
    assert "PROBLEM:" in captured.err
