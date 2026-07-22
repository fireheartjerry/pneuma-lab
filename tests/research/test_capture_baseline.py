from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import replace
from types import MappingProxyType

import pytest

from scripts.research import capture_baseline
from scripts.research.capture_baseline import (
    BaselineReceiptError,
    audit_persisted_baseline_pair,
    build_baseline_receipt,
    canonical_receipt_bytes,
    hash_project_config_bundle,
    launch_official_baseline,
    main,
    run_diagnostic_baseline_pair,
    run_trusted_baseline_pair,
    validate_baseline_pair,
)


COMMIT = "a" * 40
LOCK_SHA256 = "b" * 64
CONFIG_SHA256 = "c" * 64
FIXED_CONFIG_NAMES = (
    ".gitattributes",
    "pyproject.toml",
    "uv.lock",
    "scripts/__init__.py",
    "scripts/research/__init__.py",
    "scripts/research/capture_baseline.py",
)


def _baseline_dir(repo: Path) -> Path:
    path = repo / "build" / "research" / "baseline"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_junit(
    path: Path,
    *,
    timestamp: str = "2026-07-22T12:00:00-04:00",
    suite_name: str = "manual-nonofficial-suite",
    names: tuple[str, ...] = ("test_one", "test_two"),
    failures: int = 0,
    errors: int = 0,
    skipped: int = 0,
    duration: str = "1.25",
) -> None:
    cases: list[str] = []
    for index, name in enumerate(names):
        outcome = ""
        if index < failures:
            outcome = "<failure message='failed'/>"
        elif index < failures + errors:
            outcome = "<error message='errored'/>"
        elif index < failures + errors + skipped:
            outcome = "<skipped/>"
        cases.append(
            f"<testcase classname='tests.test_sample' name='{name}' time='0.1'>"
            f"{outcome}</testcase>"
        )
    path.write_text(
        "<?xml version='1.0' encoding='utf-8'?>"
        f"<testsuites name='{suite_name}'>"
        f"<testsuite name='{suite_name}' tests='{len(names)}' failures='{failures}' "
        f"errors='{errors}' skipped='{skipped}' time='{duration}' "
        f"timestamp='{timestamp}'>{''.join(cases)}</testsuite>"
        "</testsuites>",
        encoding="utf-8",
    )


def _build(path: Path, repo: Path, **overrides: str) -> dict:
    arguments = {
        "commit": COMMIT,
        "python_version": platform.python_version(),
        "dependency_lock_sha256": LOCK_SHA256,
        "project_config_sha256": CONFIG_SHA256,
        "repo_root": repo,
    }
    arguments.update(overrides)
    return build_baseline_receipt(path, **arguments)


def _git_environment() -> dict[str, str]:
    allowed = {
        name: os.environ[name]
        for name in ("PATH", "HOME", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if name in os.environ
    }
    allowed.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return allowed


def _git(repo: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        cwd=repo,
        env=_git_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return result.stdout.decode("utf-8").strip()


def _make_repo(
    path: Path,
    *,
    test_source: str | None = None,
    conftest_source: str | None = None,
) -> Path:
    path.mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "src" / "pneuma_lab").mkdir(parents=True)
    (path / "src" / "pneuma_lab" / "__init__.py").write_text(
        "__version__ = 'test-fixture'\n", encoding="utf-8"
    )
    (path / ".gitattributes").write_text("* text=auto\n", encoding="utf-8")
    (path / ".gitignore").write_text(
        "/build/\n.venv/\n.pytest_cache/\n__pycache__/\n", encoding="utf-8"
    )
    (path / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\n"
        "testpaths = ['tests']\n"
        "pythonpath = ['src']\n",
        encoding="utf-8",
    )
    (path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (path / "scripts" / "research").mkdir(parents=True)
    (path / "scripts" / "__init__.py").write_text("", encoding="utf-8")
    (path / "scripts" / "research" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (path / "scripts" / "research" / "capture_baseline.py").write_bytes(
        Path(capture_baseline.__file__).read_bytes()
    )
    (path / "tests" / "test_sample.py").write_text(
        test_source
        or "def test_first():\n    assert True\n\ndef test_second():\n    assert True\n",
        encoding="utf-8",
    )
    if conftest_source is not None:
        (path / "conftest.py").write_text(conftest_source, encoding="utf-8")
    _git(path, "init", "--quiet")
    _git(path, "add", ".")
    _git(
        path,
        "-c",
        "user.name=Baseline Test",
        "-c",
        "user.email=baseline@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "fixture",
    )
    return path


@contextmanager
def _worktree_runtime(repo: Path):
    saved = {
        name: module
        for name, module in tuple(sys.modules.items())
        if name == "pneuma_lab" or name.startswith("pneuma_lab.")
    }
    for name in saved:
        sys.modules.pop(name, None)
    source = str(repo / "src")
    original_launcher_file = capture_baseline.__file__
    original_imported_path = capture_baseline._IMPORTED_LAUNCHER_PATH
    original_imported_sha256 = capture_baseline._IMPORTED_LAUNCHER_SHA256
    capture_baseline.__file__ = str(repo / "scripts" / "research" / "capture_baseline.py")
    capture_baseline._IMPORTED_LAUNCHER_PATH = Path(
        capture_baseline.__file__
    ).resolve(strict=True)
    capture_baseline._IMPORTED_LAUNCHER_SHA256 = hashlib.sha256(
        capture_baseline._IMPORTED_LAUNCHER_PATH.read_bytes()
    ).hexdigest()
    sys.path.insert(0, source)
    importlib.invalidate_caches()
    try:
        yield
    finally:
        for name in tuple(sys.modules):
            if name == "pneuma_lab" or name.startswith("pneuma_lab."):
                sys.modules.pop(name, None)
        sys.path.remove(source)
        capture_baseline.__file__ = original_launcher_file
        capture_baseline._IMPORTED_LAUNCHER_PATH = original_imported_path
        capture_baseline._IMPORTED_LAUNCHER_SHA256 = original_imported_sha256
        sys.modules.update(saved)
        importlib.invalidate_caches()


def _trusted_launch(repo: Path) -> dict:
    with _worktree_runtime(repo):
        return run_diagnostic_baseline_pair(repo, _baseline_dir(repo))


def _trusted_validate(repo: Path, first: dict, second: dict) -> dict:
    with _worktree_runtime(repo):
        return audit_persisted_baseline_pair(first, second)


def _load_run_receipts(repo: Path) -> tuple[dict, dict]:
    directory = _baseline_dir(repo)
    return tuple(
        json.loads((directory / f"baseline-receipt-run-{index}.json").read_text())
        for index in (1, 2)
    )


def _resign(receipt: dict) -> dict:
    changed = dict(receipt)
    changed.pop("receipt_id", None)
    changed["receipt_id"] = hashlib.sha256(
        canonical_receipt_bytes(changed)
    ).hexdigest()
    return changed


def _forge_collection(receipt: dict, nodeids: list[str]) -> tuple[dict, bytes]:
    path = Path(receipt["collection_path"])
    original = path.read_bytes()
    payload = json.loads(original)
    payload["nodeids"] = sorted(nodeids)
    forged_bytes = canonical_receipt_bytes(payload)
    path.write_bytes(forged_bytes)
    changed = dict(receipt)
    changed["collection_artifact_sha256"] = hashlib.sha256(forged_bytes).hexdigest()
    changed["collection_count"] = len(nodeids)
    changed["collection_sha256"] = hashlib.sha256(
        canonical_receipt_bytes({"nodeids": sorted(nodeids)})
    ).hexdigest()
    return _resign(changed), original


@pytest.fixture(scope="module", autouse=True)
def _fake_worktree_bound_uv(
    tmp_path_factory: pytest.TempPathFactory,
):
    directory = tmp_path_factory.mktemp("fake-uv")
    executable = directory / ("uv.exe" if os.name == "nt" else "uv")
    executable.write_bytes(b"test-only uv executable\n")
    executable.chmod(0o755)
    uv_tool = capture_baseline._UvTool(
        executable=str(executable.resolve(strict=True)),
        version="uv 99.0.0-test",
        sha256=hashlib.sha256(executable.read_bytes()).hexdigest(),
    )
    original_run_process = capture_baseline._run_process
    patcher = pytest.MonkeyPatch()

    def fake_probe(root: Path, tool, environment: dict[str, str]):
        selected_environment = Path(environment["UV_PROJECT_ENVIRONMENT"])
        selected_python = selected_environment / (
            "Scripts/python.exe" if os.name == "nt" else "bin/python"
        )
        selected_python.parent.mkdir(parents=True, exist_ok=True)
        selected_python.write_bytes(b"test-only selected python\n")
        module_file = root / "src" / "pneuma_lab" / "__init__.py"
        return capture_baseline._UvRuntime(
            python_executable=str(selected_python.resolve(strict=True)),
            python_executable_sha256=hashlib.sha256(
                selected_python.read_bytes()
            ).hexdigest(),
            python_version="3.12.13",
            python_runtime="3.12.13 (test-bound uv runtime)",
            python_implementation="CPython",
            python_platform=platform.platform(),
            installed_distributions_sha256="d" * 64,
            installed_distribution_count=3,
            runtime_module_relative_path="src/pneuma_lab/__init__.py",
            runtime_module_sha256=hashlib.sha256(module_file.read_bytes()).hexdigest(),
            runtime_search_relative_paths=("src/pneuma_lab",),
        )

    def fake_run_process(
        argv: list[str],
        *,
        cwd: Path,
        environment: dict[str, str],
    ):
        if argv and argv[0] == uv_tool.executable:
            assert argv[1:7] == [
                "run",
                "--project",
                str(cwd),
                "--frozen",
                "--extra",
                "dev",
            ]
            assert argv[7] == "python"
            assert environment["UV_PROJECT_ENVIRONMENT"] == str(
                cwd / "build" / "research" / "env"
            )
            return original_run_process(
                [sys.executable, *argv[8:]],
                cwd=cwd,
                environment=dict(environment),
            )
        return original_run_process(argv, cwd=cwd, environment=environment)

    patcher.setattr(capture_baseline, "_resolve_uv_tool", lambda _root: uv_tool)
    patcher.setattr(capture_baseline, "_probe_uv_runtime", fake_probe)
    patcher.setattr(capture_baseline, "_run_process", fake_run_process)
    yield
    patcher.undo()


@pytest.fixture(scope="module")
def official_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict, dict, dict]:
    repo = _make_repo(tmp_path_factory.mktemp("official-baseline") / "repo")
    pair = _trusted_launch(repo)
    first, second = _load_run_receipts(repo)
    return repo, first, second, pair


@pytest.mark.parametrize(("failures", "errors"), [(1, 0), (0, 1)])
def test_receipt_rejects_failing_suite(
    tmp_path: Path,
    failures: int,
    errors: int,
) -> None:
    repo = tmp_path / "repo"
    junit = _baseline_dir(repo) / "failed.xml"
    _write_junit(junit, failures=failures, errors=errors)

    with pytest.raises(BaselineReceiptError, match="not green"):
        _build(junit, repo)


def test_receipt_is_canonical(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    junit = _baseline_dir(repo) / "manual.xml"
    _write_junit(junit, skipped=1)

    receipt = _build(junit, repo)

    assert receipt["kind"] == "parsed_junit_nonofficial"
    assert receipt["official_g0"] is False
    assert receipt["tests"] == 2
    assert receipt["passed"] == 1
    assert receipt["failures"] == 0
    assert receipt["errors"] == 0
    assert receipt["skipped"] == 1
    assert receipt["duration_seconds"] == 1.25
    assert receipt["commit"] == COMMIT
    assert receipt["python_version"] == platform.python_version()
    assert receipt["dependency_lock_sha256"] == LOCK_SHA256
    assert receipt["project_config_sha256"] == CONFIG_SHA256
    assert receipt["junit_path"] == str(junit.resolve(strict=True))
    assert receipt["junit_suite_name"] == "manual-nonofficial-suite"
    assert receipt["collection_count"] == 2
    assert len(receipt["collection_sha256"]) == 64

    expected = (
        json.dumps(
            receipt,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    assert canonical_receipt_bytes(dict(reversed(tuple(receipt.items())))) == expected


def test_missing_junit_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    missing = _baseline_dir(repo) / "absent.xml"
    with pytest.raises(BaselineReceiptError, match="does not exist"):
        _build(missing, repo)


def test_malformed_junit_fails_closed(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    junit = _baseline_dir(repo) / "malformed.xml"
    junit.write_text("<testsuites><testsuite", encoding="utf-8")
    with pytest.raises(BaselineReceiptError, match="malformed"):
        _build(junit, repo)


def test_config_bundle_hash_is_order_independent_and_content_bound(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    paths = [repo / name for name in FIXED_CONFIG_NAMES]
    digest = hash_project_config_bundle(paths, root=repo)
    assert digest == hash_project_config_bundle(reversed(paths), root=repo)
    (repo / "uv.lock").write_text("version = 2\n", encoding="utf-8")
    assert digest != hash_project_config_bundle(paths, root=repo)


@pytest.mark.parametrize("ending", [b"", b"\n", b"\r\n"])
def test_gitfile_parser_accepts_one_exact_line(ending: bytes) -> None:
    assert capture_baseline._parse_gitfile_bytes(
        b"gitdir: ../admin/worktrees/wt" + ending
    ) == "../admin/worktrees/wt"


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"GITDIR: ../admin\n",
        b"gitdir:../admin\n",
        b"gitdir: \n",
        b"gitdir: one\ngitdir: two\n",
        b"gitdir: one\x00two\n",
        b"gitdir: \xff\n",
    ],
)
def test_gitfile_parser_rejects_malformed_lines(payload: bytes) -> None:
    with pytest.raises(BaselineReceiptError, match="git link|gitdir line|empty path"):
        capture_baseline._parse_gitfile_bytes(payload)


def test_relative_linked_gitdir_resolves_from_worktree(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    admin = tmp_path / "admin" / "worktrees" / "wt"
    worktree.mkdir()
    admin.mkdir(parents=True)

    assert capture_baseline.resolve_linked_git_dir(
        "../admin/worktrees/wt", worktree_root=worktree
    ) == admin.resolve(strict=True)


def test_standard_git_directory_binding_uses_explicit_scoped_paths(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo").resolve(strict=True)

    binding = capture_baseline._git_binding(
        repo,
        capture_baseline._sanitized_environment(),
    )

    assert binding.prefix == (
        binding.executable,
        f"--git-dir={repo / '.git'}",
        f"--work-tree={repo}",
    )
    assert "-C" not in binding.prefix


def test_missing_linked_gitdir_fails_closed(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    with pytest.raises(BaselineReceiptError, match="does not exist"):
        capture_baseline.resolve_linked_git_dir(
            "../missing/worktrees/wt", worktree_root=worktree
        )


@pytest.mark.parametrize(
    ("git_argument", "message"),
    [
        ("--absolute-git-dir", "administrative path"),
        ("--show-toplevel", "unexpected root"),
    ],
)
def test_git_binding_rejects_reported_path_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    git_argument: str,
    message: str,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    wrong = tmp_path / "wrong"
    wrong.mkdir()
    original = capture_baseline._run_bound_git

    def wrong_path(root, binding, *arguments):
        if arguments == ("rev-parse", git_argument):
            return (str(wrong) + "\n").encode()
        return original(root, binding, *arguments)

    monkeypatch.setattr(capture_baseline, "_run_bound_git", wrong_path)
    with pytest.raises(BaselineReceiptError, match=message):
        capture_baseline._git_binding(
            repo, capture_baseline._sanitized_environment()
        )


def test_wslpath_missing_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capture_baseline.shutil, "which", lambda *_args, **_kwargs: None)
    with pytest.raises(BaselineReceiptError, match="wslpath is unavailable"):
        capture_baseline._translate_windows_gitdir(
            r"C:\admin\worktrees\wt", environment={"PATH": ""}
        )


def test_wslpath_failure_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "wslpath"
    executable.write_text("fixture", encoding="utf-8")
    executable.chmod(0o755)
    monkeypatch.setattr(
        capture_baseline.shutil, "which", lambda *_args, **_kwargs: str(executable)
    )
    monkeypatch.setattr(
        capture_baseline.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=3, stdout=b"", stderr=b"failed"
        ),
    )
    with pytest.raises(BaselineReceiptError, match="wslpath failed"):
        capture_baseline._translate_windows_gitdir(
            r"C:\admin\worktrees\wt", environment={"PATH": str(tmp_path)}
        )


@pytest.mark.skipif(os.name == "nt", reason="WSL translation is a POSIX-only path")
def test_windows_linked_worktree_gitdir_uses_validated_wslpath_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = tmp_path / "wslpath"
    executable.write_text("fixture", encoding="utf-8")
    executable.chmod(0o755)
    git_directory = tmp_path / "custom-automount" / "git-admin"
    git_directory.mkdir(parents=True)
    monkeypatch.setattr(
        capture_baseline.shutil, "which", lambda *_args, **_kwargs: str(executable)
    )
    monkeypatch.setattr(
        capture_baseline.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=(git_directory.as_posix() + "\n").encode(),
            stderr=b"",
        ),
    )

    resolved, evidence = capture_baseline._translate_windows_gitdir(
        r"C:\admin\worktrees\wt", environment={"PATH": str(tmp_path)}
    )

    assert resolved == git_directory.resolve(strict=True)
    assert evidence.translated_path == str(resolved)


def test_current_git_binding_records_canonical_admin_and_marker() -> None:
    root = Path(__file__).resolve().parents[2]
    binding = capture_baseline._git_binding(
        root, capture_baseline._sanitized_environment()
    )

    assert Path(binding.admin_path).is_dir()
    assert len(binding.executable_sha256) == 64
    assert len(binding.marker_sha256) == 64
    if (root / ".git").is_file():
        assert binding.marker_kind == "file"
        raw = capture_baseline._parse_gitfile_bytes((root / ".git").read_bytes())
        if os.name != "nt" and capture_baseline._WINDOWS_PATH_RE.fullmatch(
            raw.replace("\\", "/")
        ):
            assert binding.wslpath is not None
            assert Path(binding.wslpath.executable).name == "wslpath"


def test_pair_accepts_two_independent_green_runs(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, launched_pair = official_run
    pair = _trusted_validate(repo, first, second)

    assert pair["kind"] == "local_g0_audit_record"
    assert pair["authority"] == "none"
    assert pair["authentication"] == "none"
    assert pair["live_g0_observed"] is False
    assert launched_pair["live_g0_observed"] is False
    assert pair["tests"] == 2
    assert pair["collection_sha256"] == first["collection_sha256"]
    assert pair["validation_collection_sha256"] == first["collection_sha256"]
    assert pair["validation_collection_count"] == first["collection_count"]
    assert len(pair["validation_command_sha256"]) == 64
    assert pair["run_receipt_ids"] == [first["receipt_id"], second["receipt_id"]]
    pair_path = _baseline_dir(repo) / "baseline-pair-receipt.json"
    assert pair_path.read_bytes() == canonical_receipt_bytes(launched_pair)
    with pytest.raises(BaselineReceiptError, match="live provenance"):
        validate_baseline_pair(first, second)


def test_launcher_records_fixed_command_nonce_and_process_evidence(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    for receipt in (first, second):
        argv = receipt["argv"]
        assert argv[:8] == [
            receipt["uv_executable"],
            "run",
            "--project",
            str(repo),
            "--frozen",
            "--extra",
            "dev",
            "python",
        ]
        assert argv[8:13] == [
            "-m",
            "pytest",
            "tests",
            "-q",
            f"--confcutdir={repo}",
        ]
        assert argv[13] == "-c"
        assert "-k" not in argv
        assert argv.count("-m") == 1
        assert receipt["uv_project_environment"] == str(
            repo / "build" / "research" / "env"
        )
        assert "/.venv/" not in receipt["python_executable"].replace("\\", "/")
        assert receipt["junit_suite_name"] == f"pneuma-baseline-{receipt['nonce']}"
        assert receipt["returncode"] == 0
        assert receipt["authority"] == "none"
        assert receipt["authentication"] == "none"
        assert receipt["process_id"] > 0
        assert len(receipt["command_sha256"]) == 64
        assert len(receipt["stdout_sha256"]) == 64
        assert len(receipt["stderr_sha256"]) == 64
        assert len(receipt["tracked_tree_sha256"]) == 64
        assert receipt["collection_hook_module_relative_path"] == (
            "scripts/research/capture_baseline.py"
        )
        assert receipt["collection_hook_module_sha256"] == hashlib.sha256(
            (repo / "scripts" / "research" / "capture_baseline.py").read_bytes()
        ).hexdigest()
        assert Path(receipt["stdout_path"]).is_file()
        assert Path(receipt["stderr_path"]).is_file()
        assert Path(receipt["process_journal_path"]).is_file()
        assert receipt["finished_at_utc"] >= receipt["started_at_utc"]


def test_launcher_hook_identity_rejects_shadow_module(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    shadow = tmp_path / "installed" / "scripts" / "research" / "capture_baseline.py"
    shadow.parent.mkdir(parents=True)
    shadow.write_text("# shadow package\n", encoding="utf-8")
    saved = capture_baseline.__file__
    try:
        capture_baseline.__file__ = str(shadow)
        with pytest.raises(BaselineReceiptError, match="hook module escapes"):
            capture_baseline._launcher_hook_identity(repo.resolve(strict=True))
    finally:
        capture_baseline.__file__ = saved


def test_worktree_regular_scripts_package_wins_over_shadow_package(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    shadow = repo / "src" / "scripts" / "research"
    shadow.mkdir(parents=True)
    (shadow.parent / "__init__.py").write_text("", encoding="utf-8")
    (shadow / "__init__.py").write_text("", encoding="utf-8")
    (shadow / "capture_baseline.py").write_text(
        "raise RuntimeError('shadow hook imported')\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(
        repo,
        "-c",
        "user.name=Baseline Test",
        "-c",
        "user.email=baseline@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "shadow fixture",
    )

    pair = _trusted_launch(repo)

    assert pair["validation_hook_module_relative_path"] == (
        "scripts/research/capture_baseline.py"
    )


def test_launcher_owned_pythonpath_supports_worktree_with_spaces(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo with spaces")

    pair = _trusted_launch(repo)

    assert pair["validation_collection_count"] == 2


def test_diagnostic_launcher_writes_non_authoritative_pair_receipt(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    with _worktree_runtime(repo):
        pair = run_diagnostic_baseline_pair(repo, _baseline_dir(repo))
    pair = json.loads(
        (_baseline_dir(repo) / "baseline-pair-receipt.json").read_text()
    )
    assert pair["kind"] == "local_g0_audit_record"
    assert pair["authority"] == "none"
    assert pair["live_g0_observed"] is False


def test_contract_entrypoint_refuses_noncanonical_output_dir(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    with pytest.raises(BaselineReceiptError, match="build/research/baseline"):
        run_trusted_baseline_pair(repo, tmp_path / "escaped-output")


def test_official_launcher_rejects_injected_runtime_transport(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    with _worktree_runtime(repo):
        with pytest.raises(BaselineReceiptError, match="runtime implementation"):
            launch_official_baseline(repo)


def test_direct_official_helper_rejects_injected_runtime_transport(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    with _worktree_runtime(repo):
        with pytest.raises(BaselineReceiptError, match="runtime implementation"):
            capture_baseline._run_baseline_pair_impl(
                repo,
                _baseline_dir(repo),
                official_runtime=True,
            )


def test_official_runtime_guard_pins_both_collection_argv_builders(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_full = capture_baseline._full_suite_argv
    original_collect = capture_baseline._collect_only_argv
    monkeypatch.setattr(
        capture_baseline,
        "_TRUSTED_RUNTIME_IMPLEMENTATION",
        capture_baseline._runtime_implementation_objects(),
    )

    def narrowed_full(*args, **kwargs):
        return [*original_full(*args, **kwargs), "-k", "test_one"]

    def narrowed_collect(*args, **kwargs):
        return [*original_collect(*args, **kwargs), "-k", "test_one"]

    monkeypatch.setattr(capture_baseline, "_full_suite_argv", narrowed_full)
    monkeypatch.setattr(capture_baseline, "_collect_only_argv", narrowed_collect)

    with pytest.raises(BaselineReceiptError, match="runtime implementation"):
        capture_baseline._require_unmodified_runtime_implementation()


@pytest.mark.parametrize("surface", ["sanitizer", "environment_allowlist"])
def test_official_runtime_guard_pins_transitive_selection_surfaces(
    monkeypatch: pytest.MonkeyPatch,
    surface: str,
) -> None:
    monkeypatch.setattr(
        capture_baseline,
        "_TRUSTED_RUNTIME_IMPLEMENTATION",
        capture_baseline._runtime_implementation_objects(),
    )
    if surface == "sanitizer":
        original = capture_baseline._sanitized_environment

        def poisoned(*args, **kwargs):
            result = original(*args, **kwargs)
            result["PYTEST_ADDOPTS"] = "-k test_one"
            return result

        monkeypatch.setattr(capture_baseline, "_sanitized_environment", poisoned)
    else:
        monkeypatch.setattr(
            capture_baseline,
            "_ENV_ALLOWLIST",
            (*capture_baseline._ENV_ALLOWLIST, "PYTEST_ADDOPTS"),
        )

    with pytest.raises(BaselineReceiptError, match="runtime implementation"):
        capture_baseline._require_unmodified_runtime_implementation()


def test_runtime_guard_covers_transitive_module_function_closure() -> None:
    module_functions = {
        name: value
        for name, value in vars(capture_baseline).items()
        if inspect.isfunction(value) and value.__module__ == capture_baseline.__name__
    }
    reachable: set[str] = set()
    pending = ["run_trusted_baseline_pair", "require_live_g0_capability"]
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        reachable.add(name)
        pending.extend(
            dependency
            for dependency in module_functions[name].__code__.co_names
            if dependency in module_functions and dependency not in reachable
        )

    assert reachable <= set(capture_baseline._RUNTIME_GUARDED_FUNCTION_NAMES)


def test_launcher_rejects_stale_imported_launcher_bytes(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    with _worktree_runtime(repo):
        saved = capture_baseline._IMPORTED_LAUNCHER_SHA256
        try:
            capture_baseline._IMPORTED_LAUNCHER_SHA256 = "0" * 64
            with pytest.raises(BaselineReceiptError, match="import-time committed source"):
                run_diagnostic_baseline_pair(repo, _baseline_dir(repo))
        finally:
            capture_baseline._IMPORTED_LAUNCHER_SHA256 = saved


def test_pair_rejects_a_timestamp_edited_copy(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    directory = _baseline_dir(repo)
    first_xml = directory / "manual-first.xml"
    second_xml = directory / "manual-second.xml"
    _write_junit(first_xml, timestamp="2026-07-22T12:00:00-04:00")
    second_xml.write_bytes(
        first_xml.read_bytes().replace(
            b"2026-07-22T12:00:00-04:00", b"2026-07-22T12:01:00-04:00"
        )
    )

    with pytest.raises(BaselineReceiptError, match="trusted full-suite launcher"):
        validate_baseline_pair(_build(first_xml, repo), _build(second_xml, repo))


def test_one_test_subset_xml_is_never_official_g0(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    directory = _baseline_dir(repo)
    first_xml = directory / "subset-first.xml"
    second_xml = directory / "subset-second.xml"
    _write_junit(first_xml, names=("test_only",), timestamp="2026-07-22T12:00:00Z")
    _write_junit(second_xml, names=("test_only",), timestamp="2026-07-22T12:01:00Z")

    with pytest.raises(BaselineReceiptError, match="trusted full-suite launcher"):
        validate_baseline_pair(_build(first_xml, repo), _build(second_xml, repo))


def test_pair_rejects_forged_commit(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    _repo, first, second, _pair = official_run
    forged = []
    for original in (first, second):
        changed = dict(original)
        changed["commit"] = "f" * 40
        forged.append(_resign(changed))

    with pytest.raises(BaselineReceiptError, match="current scoped Git HEAD"):
        _trusted_validate(_repo, *forged)


def test_pair_rejects_config_omission(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    _repo, first, second, _pair = official_run
    changed = dict(first)
    changed["project_config_files"] = changed["project_config_files"][:-1]
    changed = _resign(changed)

    with pytest.raises(BaselineReceiptError, match="fixed project config"):
        _trusted_validate(_repo, changed, second)


def test_pair_rejects_environment_drift(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    _repo, first, second, _pair = official_run
    changed = dict(first)
    changed["environment_sha256"] = "e" * 64
    changed = _resign(changed)

    with pytest.raises(BaselineReceiptError, match="environment"):
        _trusted_validate(_repo, changed, second)


def test_persisted_audit_rejects_resigned_false_context_field(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    changed = dict(first)
    changed["python_runtime"] = "forged runtime claim"
    changed = _resign(changed)
    receipt_path = Path(first["receipt_path"])
    original = receipt_path.read_bytes()
    try:
        receipt_path.write_bytes(canonical_receipt_bytes(changed))
        with pytest.raises(BaselineReceiptError, match="live context: python_runtime"):
            _trusted_validate(repo, changed, second)
    finally:
        receipt_path.write_bytes(original)


def test_pair_rejects_unbound_uv_project_environment(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    changed = dict(first)
    changed["uv_project_environment"] = str(repo / ".venv")
    changed = _resign(changed)

    with pytest.raises(BaselineReceiptError, match="UV_PROJECT_ENVIRONMENT"):
        _trusted_validate(repo, changed, second)


def test_pair_rejects_process_evidence_drift(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    _repo, first, second, _pair = official_run
    changed = dict(first)
    changed["returncode"] = 3
    changed = _resign(changed)

    with pytest.raises(BaselineReceiptError, match="zero return code"):
        _trusted_validate(_repo, changed, second)


def test_pair_rejects_forged_different_count_collection(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    first_changed, first_original = _forge_collection(
        first, ["tests/forged.py::test_only"]
    )
    second_changed, second_original = _forge_collection(
        second, ["tests/forged.py::test_only"]
    )
    try:
        with pytest.raises(
            BaselineReceiptError, match="independent collection|receipt file"
        ):
            _trusted_validate(repo, first_changed, second_changed)
    finally:
        Path(first["collection_path"]).write_bytes(first_original)
        Path(second["collection_path"]).write_bytes(second_original)


def test_pair_rejects_forged_same_count_nonexistent_nodeids(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    forged = [
        "tests/does_not_exist.py::test_forged_one",
        "tests/does_not_exist.py::test_forged_two",
    ]
    first_changed, first_original = _forge_collection(first, forged)
    second_changed, second_original = _forge_collection(second, forged)
    try:
        with pytest.raises(
            BaselineReceiptError, match="independent collection|receipt file"
        ):
            _trusted_validate(repo, first_changed, second_changed)
    finally:
        Path(first["collection_path"]).write_bytes(first_original)
        Path(second["collection_path"]).write_bytes(second_original)


def test_persisted_audit_rejects_copied_trusted_junit(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    second_path = Path(second["junit_path"])
    original = second_path.read_bytes()
    try:
        second_path.write_bytes(Path(first["junit_path"]).read_bytes())
        with pytest.raises(BaselineReceiptError, match="JUnit|receipt"):
            _trusted_validate(repo, first, second)
    finally:
        second_path.write_bytes(original)


def test_persisted_audit_rejects_missing_trusted_nonce(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    nonce_path = Path(first["nonce_path"])
    original = nonce_path.read_bytes()
    nonce_path.unlink()
    try:
        with pytest.raises(BaselineReceiptError, match="nonce|artifact"):
            _trusted_validate(repo, first, second)
    finally:
        nonce_path.write_bytes(original)


def test_persisted_audit_rejects_junit_nonce_mismatch(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    junit_path = Path(first["junit_path"])
    original = junit_path.read_bytes()
    wrong_suite = f"pneuma-baseline-{'f' * 32}".encode()
    assert wrong_suite != first["junit_suite_name"].encode()
    try:
        junit_path.write_bytes(
            original.replace(first["junit_suite_name"].encode(), wrong_suite)
        )
        with pytest.raises(BaselineReceiptError, match="JUnit|receipt"):
            _trusted_validate(repo, first, second)
    finally:
        junit_path.write_bytes(original)


def test_junit_read_outside_baseline_directory_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    junit = tmp_path / "escaped.xml"
    _write_junit(junit)

    with pytest.raises(BaselineReceiptError, match="build/research/baseline"):
        _build(junit, repo)


def _directory_symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlinks unavailable: {exc}")


def test_baseline_directory_rejects_parent_symlink_before_external_write(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    _directory_symlink_or_skip(repo / "build", outside)

    with pytest.raises(BaselineReceiptError, match="symlink|junction"):
        capture_baseline._baseline_directory(repo, create=True)

    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_text(encoding="utf-8") == "unchanged"


def test_uv_environment_rejects_research_symlink_before_external_write(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    (repo / "build").mkdir(parents=True)
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    sentinel.write_text("unchanged", encoding="utf-8")
    _directory_symlink_or_skip(repo / "build" / "research", outside)

    with pytest.raises(BaselineReceiptError, match="UV_PROJECT_ENVIRONMENT"):
        capture_baseline._uv_project_environment(repo)

    assert list(outside.iterdir()) == [sentinel]
    assert sentinel.read_text(encoding="utf-8") == "unchanged"


def test_launcher_rejects_unequal_collections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_nonce = "1" * 32
    second_nonce = "2" * 32
    repo = _make_repo(
        tmp_path / "repo",
        conftest_source=(
            "def pytest_collection_modifyitems(config, items):\n"
            "    if config.getini('junit_suite_name').endswith('" + second_nonce + "'):\n"
            "        items.pop()\n"
        ),
    )
    nonces = iter((first_nonce, second_nonce))
    monkeypatch.setattr(capture_baseline.secrets, "token_hex", lambda _size: next(nonces))

    with pytest.raises(BaselineReceiptError, match="equal canonical collection"):
        _trusted_launch(repo)


def test_launcher_requires_all_fixed_config_files(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    (repo / ".gitattributes").unlink()

    with pytest.raises(BaselineReceiptError, match="fixed project config"):
        _trusted_launch(repo)


def test_launcher_requires_clean_tree(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    (repo / "tests" / "test_sample.py").write_text(
        "def test_changed():\n    assert True\n", encoding="utf-8"
    )

    with pytest.raises(BaselineReceiptError, match="clean Git worktree"):
        _trusted_launch(repo)


@pytest.mark.parametrize(
    "index_flag",
    ["--assume-unchanged", "--skip-worktree"],
)
def test_launcher_rejects_hidden_index_flags_and_changed_tracked_bytes(
    tmp_path: Path,
    index_flag: str,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    _git(repo, "update-index", index_flag, "tests/test_sample.py")
    (repo / "tests" / "test_sample.py").write_text(
        "def test_hidden_failure():\n    assert False\n", encoding="utf-8"
    )

    assert not _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    with pytest.raises(BaselineReceiptError, match="Git index|committed HEAD"):
        _trusted_launch(repo)


@pytest.mark.skipif(os.name == "nt", reason="requires case-sensitive filesystem")
def test_launcher_rejects_case_colliding_tracked_directory_components(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    (repo / "Foo").mkdir()
    (repo / "foo").mkdir()
    (repo / "Foo" / "a.txt").write_text("a\n", encoding="utf-8")
    (repo / "foo" / "b.txt").write_text("b\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(
        repo,
        "-c",
        "user.name=Baseline Test",
        "-c",
        "user.email=baseline@example.invalid",
        "commit",
        "--quiet",
        "-m",
        "case collision",
    )

    with pytest.raises(BaselineReceiptError, match="case-colliding"):
        _trusted_launch(repo)


def test_launcher_rejects_ignored_root_conftest_collection_poison(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    (repo / ".git" / "info" / "exclude").write_text(
        "conftest.py\n", encoding="utf-8"
    )
    (repo / "conftest.py").write_text(
        "def pytest_collection_modifyitems(items):\n"
        "    items.pop()\n",
        encoding="utf-8",
    )

    assert not _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    with pytest.raises(BaselineReceiptError, match="ignored.*control surface"):
        _trusted_launch(repo)


def test_launcher_requires_fresh_uv_environment(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path / "repo")
    environment = repo / "build" / "research" / "env"
    environment.mkdir(parents=True)
    (environment / "sitecustomize.py").write_text(
        "raise RuntimeError('must never execute')\n", encoding="utf-8"
    )

    with pytest.raises(BaselineReceiptError, match="fresh absent"):
        _trusted_launch(repo)


def test_launcher_preserves_prior_evidence_when_environment_is_not_fresh(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    environment = repo / "build" / "research" / "env"
    environment.mkdir(parents=True)
    baseline = repo / "build" / "research" / "baseline"
    baseline.mkdir(parents=True)
    prior_receipt = baseline / "baseline-pair-receipt.json"
    prior_bytes = b'{"prior":"valid-audit-evidence"}\n'
    prior_receipt.write_bytes(prior_bytes)

    with pytest.raises(BaselineReceiptError, match="fresh absent"):
        _trusted_launch(repo)

    assert prior_receipt.read_bytes() == prior_bytes


def test_launcher_rejects_ignored_control_created_between_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_nonce = "3" * 32
    second_nonce = "4" * 32
    repo = _make_repo(
        tmp_path / "repo",
        conftest_source=(
            "from pathlib import Path\n\n"
            "def pytest_sessionfinish(session, exitstatus):\n"
            "    name = session.config.getini('junit_suite_name')\n"
            f"    if name.endswith('{first_nonce}'):\n"
            "        Path('poison.py').write_text('POISON = True\\n')\n"
        ),
    )
    (repo / ".git" / "info" / "exclude").write_text(
        "poison.py\n", encoding="utf-8"
    )
    nonces = iter((first_nonce, second_nonce))
    monkeypatch.setattr(capture_baseline.secrets, "token_hex", lambda _size: next(nonces))

    with pytest.raises(BaselineReceiptError, match="ignored.*control surface"):
        _trusted_launch(repo)


def test_launcher_rejects_environment_mutation_between_runs(
    tmp_path: Path,
) -> None:
    repo = _make_repo(
        tmp_path / "repo",
        conftest_source=(
            "from pathlib import Path\n\n"
            "def pytest_sessionfinish(session, exitstatus):\n"
            "    target = Path('build/research/env/tamper.py')\n"
            "    target.write_text('TAMPERED = True\\n')\n"
        ),
    )

    with pytest.raises(BaselineReceiptError, match="environment drifted between runs"):
        _trusted_launch(repo)


@pytest.mark.skipif(os.name == "nt", reason="POSIX uv environments use symlinks")
def test_posix_uv_environment_accepts_only_bound_interpreter_links(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    module = repo / "src" / "pneuma_lab" / "__init__.py"
    module.parent.mkdir(parents=True)
    module.write_text("__version__ = 'test'\n", encoding="utf-8")
    environment = repo / "build" / "research" / "env"
    binary = environment / "bin"
    binary.mkdir(parents=True)
    target = Path(sys.executable).resolve(strict=True)
    (environment / "lib").mkdir()
    os.symlink(str(target), binary / "python")
    os.symlink("python", binary / "python3")
    os.symlink("python", binary / "python3.12")
    os.symlink("lib", environment / "lib64", target_is_directory=True)
    (environment / "pyvenv.cfg").write_text("test = true\n", encoding="utf-8")
    runtime = capture_baseline._UvRuntime(
        python_executable=str(binary / "python"),
        python_executable_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        python_version="3.12.13",
        python_runtime="3.12.13 test",
        python_implementation="CPython",
        python_platform=platform.platform(),
        installed_distributions_sha256="d" * 64,
        installed_distribution_count=1,
        runtime_module_relative_path="src/pneuma_lab/__init__.py",
        runtime_module_sha256=hashlib.sha256(module.read_bytes()).hexdigest(),
        runtime_search_relative_paths=("src/pneuma_lab",),
    )

    capture_baseline._validate_uv_runtime(repo, environment, runtime)
    assert len(capture_baseline._environment_tree_digest(environment)) == 64


@pytest.mark.skipif(os.name == "nt", reason="requires POSIX symlinks")
def test_uv_environment_rejects_unapproved_file_link(tmp_path: Path) -> None:
    environment = tmp_path / "env"
    environment.mkdir()
    target = tmp_path / "outside.py"
    target.write_text("POISON = True\n", encoding="utf-8")
    os.symlink(str(target), environment / "sitecustomize.py")

    with pytest.raises(BaselineReceiptError, match="unapproved link"):
        capture_baseline._environment_tree_digest(environment)


@pytest.mark.skipif(os.name == "nt", reason="requires case-sensitive filesystem")
def test_uv_environment_rejects_case_colliding_directory_components(
    tmp_path: Path,
) -> None:
    environment = tmp_path / "env"
    (environment / "Foo").mkdir(parents=True)
    (environment / "foo").mkdir()
    (environment / "Foo" / "a.txt").write_text("a\n", encoding="utf-8")
    (environment / "foo" / "b.txt").write_text("b\n", encoding="utf-8")

    with pytest.raises(BaselineReceiptError, match="case-colliding"):
        capture_baseline._environment_tree_digest(environment)


def test_resigned_process_claims_cannot_mint_g0(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    changed = dict(first)
    changed.update(
        {
            "process_id": first["process_id"] + 10_000,
            "stdout_sha256": "9" * 64,
            "stdout_size_bytes": first["stdout_size_bytes"] + 17,
            "started_at_utc": "2026-01-01T00:00:00+00:00",
            "finished_at_utc": "2026-01-01T00:00:01+00:00",
        }
    )

    with pytest.raises(
        BaselineReceiptError,
        match="process|trusted full-suite launcher|receipt file",
    ):
        _trusted_validate(repo, _resign(changed), second)


def test_importable_dataclasses_cannot_rewrap_persisted_runs_as_live_g0(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, first, second, _pair = official_run
    session = capture_baseline._LaunchSession(
        root=repo,
        token=object(),
        official_runtime=True,
    )

    def wrap(receipt: dict) -> object:
        process = capture_baseline._CapturedProcess(
            process_id=receipt["process_id"],
            returncode=receipt["returncode"],
            stdout=Path(receipt["stdout_path"]).read_bytes(),
            stderr=Path(receipt["stderr_path"]).read_bytes(),
            started_at_utc=receipt["started_at_utc"],
            finished_at_utc=receipt["finished_at_utc"],
            elapsed_ns=receipt["elapsed_ns"],
        )
        return capture_baseline._TrustedRun(
            receipt=MappingProxyType(receipt),
            receipt_bytes=canonical_receipt_bytes(receipt),
            process=process,
            session=session,
        )

    with pytest.raises(BaselineReceiptError, match="launcher-registered"):
        validate_baseline_pair(wrap(first), wrap(second))


def test_directly_constructed_capability_cannot_recreate_live_g0(
    official_run: tuple[Path, dict, dict, dict],
) -> None:
    repo, _first, _second, pair = official_run
    fabricated = capture_baseline._LiveG0Capability(
        audit_record=MappingProxyType(pair),
        session=capture_baseline._LaunchSession(
            root=repo,
            token=object(),
            official_runtime=True,
        ),
    )

    with pytest.raises(BaselineReceiptError, match="active launcher registry"):
        capture_baseline.require_live_g0_capability(fabricated)


def test_malformed_capability_session_fails_closed() -> None:
    malformed = capture_baseline._LiveG0Capability(
        audit_record=MappingProxyType({}),
        session=object(),  # type: ignore[arg-type]
    )

    with pytest.raises(BaselineReceiptError, match="active launcher registry"):
        capture_baseline.require_live_g0_capability(malformed)


def test_launcher_detects_tree_change_between_runs(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path / "repo",
        conftest_source=(
            "from pathlib import Path\n\n"
            "def pytest_sessionfinish(session, exitstatus):\n"
            "    Path('pyproject.toml').write_text(\"[tool.pytest.ini_options]\\n\")\n"
        ),
    )

    with pytest.raises(BaselineReceiptError, match="clean Git worktree"):
        _trusted_launch(repo)


def test_launcher_detects_clean_head_change_between_runs(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path / "repo",
        conftest_source=(
            "import subprocess\n\n"
            "def pytest_sessionfinish(session, exitstatus):\n"
            "    subprocess.run([\n"
            "        'git', '-c', 'user.name=Baseline Drift',\n"
            "        '-c', 'user.email=drift@example.invalid',\n"
            "        'commit', '--allow-empty', '--quiet', '-m', 'drift'\n"
            "    ], check=True)\n"
        ),
    )

    with pytest.raises(BaselineReceiptError, match="drifted between runs"):
        _trusted_launch(repo)


def test_launcher_rejects_nonzero_pytest_result(tmp_path: Path) -> None:
    repo = _make_repo(
        tmp_path / "repo",
        conftest_source=(
            "def pytest_sessionfinish(session, exitstatus):\n"
            "    session.exitstatus = 3\n"
        ),
    )

    with pytest.raises(BaselineReceiptError, match="return code"):
        _trusted_launch(repo)


def test_launcher_sanitizes_subprocess_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RUNPOD_API_KEY", "not-a-real-secret")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k definitely_not_collected")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "forged-git-dir"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "forged-work-tree"))
    repo = _make_repo(
        tmp_path / "repo",
        test_source=(
            "import os\n\n"
            "def test_secret_is_absent():\n"
            "    assert 'RUNPOD_API_KEY' not in os.environ\n"
            "    assert os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] == '1'\n"
        ),
    )

    pair = _trusted_launch(repo)
    assert pair["tests"] == 1


def test_launcher_rejects_replayed_nonce(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    monkeypatch.setattr(capture_baseline.secrets, "token_hex", lambda _size: "1" * 32)

    with pytest.raises(BaselineReceiptError, match="distinct nonces"):
        _trusted_launch(repo)


def test_launcher_rejects_unapproved_python_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    original_probe = capture_baseline._probe_uv_runtime

    def unbound_probe(root, tool, environment):
        runtime = original_probe(root, tool, environment)
        parent_python = repo.parent / ".venv" / "bin" / "python"
        parent_python.parent.mkdir(parents=True, exist_ok=True)
        parent_python.write_bytes(b"unbound parent python\n")
        return replace(
            runtime,
            python_executable=str(parent_python.resolve(strict=True)),
            python_executable_sha256=hashlib.sha256(
                parent_python.read_bytes()
            ).hexdigest(),
        )

    monkeypatch.setattr(capture_baseline, "_probe_uv_runtime", unbound_probe)

    with pytest.raises(BaselineReceiptError, match="uv-selected Python"):
        _trusted_launch(repo)


def test_launcher_rejects_parent_worktree_runtime_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    outside_module = tmp_path / "parent-src" / "pneuma_lab" / "__init__.py"
    outside_module.parent.mkdir(parents=True)
    outside_module.write_text("__version__ = 'outside'\n", encoding="utf-8")
    original_probe = capture_baseline._probe_uv_runtime

    def parent_probe(root, tool, environment):
        runtime = original_probe(root, tool, environment)
        return replace(
            runtime,
            runtime_module_relative_path="../parent-src/pneuma_lab/__init__.py",
            runtime_module_sha256=hashlib.sha256(outside_module.read_bytes()).hexdigest(),
            runtime_search_relative_paths=("../parent-src/pneuma_lab",),
        )

    monkeypatch.setattr(capture_baseline, "_probe_uv_runtime", parent_probe)
    with pytest.raises(BaselineReceiptError, match="import escapes"):
        _trusted_launch(repo)


def test_launcher_rejects_uv_executable_from_default_venv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _make_repo(tmp_path / "repo")
    bad_uv = repo / ".venv" / "bin" / "uv"
    bad_uv.parent.mkdir(parents=True)
    bad_uv.write_bytes(b"not an approved uv\n")
    tool = capture_baseline._UvTool(
        executable=str(bad_uv.resolve(strict=True)),
        version="uv 0.0.0-forged",
        sha256=hashlib.sha256(bad_uv.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(capture_baseline, "_resolve_uv_tool", lambda _root: tool)

    with pytest.raises(BaselineReceiptError, match="uv executable|ignored executable"):
        _trusted_launch(repo)
