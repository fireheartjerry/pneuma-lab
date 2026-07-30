from __future__ import annotations

from pathlib import Path

from pneuma_lab.testd.fingerprint import (
    application_fingerprint,
    checkout_fingerprint,
    environment_fingerprint,
    stable_runner_fingerprint,
)


def test_checkout_fingerprint_is_content_and_order_sensitive_not_separator_sensitive(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    source = tmp_path / "src" / "module.py"
    source.write_text("value = 1\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'x'\n", encoding="utf-8"
    )

    first = checkout_fingerprint(
        tmp_path, paths=(Path("src/module.py"), Path("pyproject.toml"))
    )
    second = checkout_fingerprint(
        tmp_path, paths=(Path("pyproject.toml"), Path("src") / "module.py")
    )
    source.write_text("value = 2\n", encoding="utf-8")

    assert first == second
    assert first != checkout_fingerprint(
        tmp_path, paths=(Path("src/module.py"), Path("pyproject.toml"))
    )


def test_application_and_runner_fingerprints_bind_distinct_inputs(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("a", encoding="utf-8")
    (tmp_path / "uv.lock").write_text("b", encoding="utf-8")

    application = application_fingerprint(tmp_path, paths=(Path("src/app.py"),))
    runner = stable_runner_fingerprint(
        tmp_path, paths=(Path("pyproject.toml"), Path("uv.lock"))
    )

    assert application.digest != runner.digest
    assert application.paths == ("src/app.py",)


def test_environment_fingerprint_changes_for_relevant_values(monkeypatch) -> None:
    monkeypatch.setenv("TESTD_SAMPLE", "one")
    first = environment_fingerprint(("TESTD_SAMPLE",))
    monkeypatch.setenv("TESTD_SAMPLE", "two")

    assert first != environment_fingerprint(("TESTD_SAMPLE",))
