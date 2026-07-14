"""Pinned, inert foundation environment bootstrap contracts."""

from __future__ import annotations

from pathlib import Path, PureWindowsPath
import shutil
import tempfile
import tomllib

import pytest

from pneuma_lab.foundation.environment import (
    PYTHON_SERIES,
    TRANSFORMERS_COMMIT,
    UV_VERSION,
    setup_plan,
    verify_lock,
)


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TRANSFORMERS_COMMIT = (
    "11ed2ff4df5fdfb3117f0e3365ef6ad94081ba69"
)
REGISTRY_PINS = {
    "accelerate": "1.14.0",
    "bitsandbytes": "0.49.2",
    "huggingface-hub": "1.23.0",
    "peft": "0.19.1",
    "pillow": "12.3.0",
    "psutil": "7.2.2",
    "safetensors": "0.8.0",
    "torch": "2.13.0",
    "torchvision": "0.28.0",
}


@pytest.fixture
def lock_directory() -> Path:
    parent = ROOT / "build"
    parent.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="task6-lock-", dir=parent))
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _valid_lock() -> str:
    lines = [
        "version = 1",
        "revision = 3",
        'requires-python = ">=3.12"',
        "",
        "[[package]]",
        'name = "pneuma-lab"',
        'version = "0.1.0"',
        'source = { editable = "." }',
        "[package.optional-dependencies]",
        "foundation = [",
        *(f'    {{ name = "{name}" }},' for name in sorted(REGISTRY_PINS)),
        '    { name = "transformers" },',
        "]",
        "[package.metadata]",
        "requires-dist = [",
        *(
            f'    {{ name = "{name}", marker = "extra == \'foundation\'", '
            f'specifier = "=={version}" }},'
            for name, version in sorted(REGISTRY_PINS.items())
        ),
        '    { name = "transformers", marker = "extra == \'foundation\'", '
        f'git = "https://github.com/huggingface/transformers.git?rev='
        f'{EXPECTED_TRANSFORMERS_COMMIT}" }},',
        "]",
        "",
    ]
    for name, version in sorted(REGISTRY_PINS.items()):
        lines.extend(
            (
                "[[package]]",
                f'name = "{name}"',
                f'version = "{version}"',
                'source = { registry = "https://pypi.org/simple" }',
                "",
            )
        )
    lines.extend(
        (
            "[[package]]",
            'name = "transformers"',
            'version = "5.4.0.dev0"',
            "source = { git = \"https://github.com/huggingface/transformers.git"
            f"?rev={EXPECTED_TRANSFORMERS_COMMIT}#{EXPECTED_TRANSFORMERS_COMMIT}\" }}",
            "",
        )
    )
    return "\n".join(lines)


def _write_lock(directory: Path, payload: str) -> Path:
    path = directory / "uv.lock"
    path.write_text(payload, encoding="utf-8", newline="\n")
    return path


def test_environment_constants_are_exact() -> None:
    assert UV_VERSION == "0.11.28"
    assert PYTHON_SERIES == (3, 12)
    assert TRANSFORMERS_COMMIT == EXPECTED_TRANSFORMERS_COMMIT
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["requires-python"] == ">=3.12,<3.13"


def test_setup_plan_maps_a_safe_windows_repository_without_side_effects() -> None:
    repo = PureWindowsPath("C:/pneuma-lab")
    plan = setup_plan(repo)

    assert plan == {
        "copy_wslconfig": (
            "Copy-Item .wslconfig.foundation.example $HOME\\.wslconfig"
        ),
        "restart_wsl": "wsl --shutdown",
        "enter_wsl": "wsl -d Ubuntu",
        "repo_path": "/mnt/c/pneuma-lab",
        "setup": "bash scripts/foundation/setup-wsl.sh",
        "training_started": False,
    }


@pytest.mark.parametrize(
    "unsafe",
    (
        PureWindowsPath("C:/"),
        PureWindowsPath("C:/pneuma-data"),
        PureWindowsPath("C:/pneuma-data/alias"),
        PureWindowsPath("//server/share/pneuma-lab"),
        PureWindowsPath("relative/pneuma-lab"),
        PureWindowsPath("C:/safe;touch owned"),
        PureWindowsPath("C:/safe$(touch owned)"),
        PureWindowsPath("C:/safe\nowned"),
    ),
)
def test_setup_plan_rejects_non_drive_protected_or_shell_unsafe_roots(
    unsafe: PureWindowsPath,
) -> None:
    with pytest.raises(ValueError):
        setup_plan(unsafe)


def test_verify_lock_accepts_structural_exact_pins(lock_directory: Path) -> None:
    verify_lock(_write_lock(lock_directory, _valid_lock()))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value.replace('    { name = "torch" },\n', "", 1),
        lambda value: value.replace(
            'specifier = "==2.13.0"', 'specifier = ">=2.13"', 1
        ),
        lambda value: value.replace(
            'source = { editable = "." }', 'source = { editable = "../other" }'
        ),
    ),
)
def test_verify_lock_requires_exact_root_foundation_edges(
    lock_directory: Path,
    mutate,
) -> None:
    with pytest.raises(ValueError):
        verify_lock(_write_lock(lock_directory, mutate(_valid_lock())))


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: value.replace('version = "2.13.0"', 'version = "2.13.1"'),
        lambda value: value.replace(
            'source = { registry = "https://pypi.org/simple" }',
            'source = { path = "../wheelhouse" }',
            1,
        ),
        lambda value: value.replace(EXPECTED_TRANSFORMERS_COMMIT, "0" * 40),
        lambda value: value.replace(
            'version = "5.4.0.dev0"', 'version = ""'
        ),
        lambda value: value.replace(
            'name = "torch"',
            'name = "torch"\nversion = "2.13.0"\n'
            'source = { registry = "https://pypi.org/simple" }\n\n'
            '[[package]]\nname = "torch"',
        ),
        lambda value: value + '\n[[package]]\nname = "torch"\n'
        'version = "nan"\nsource = { registry = "https://pypi.org/simple" }\n',
    ),
)
def test_verify_lock_rejects_wrong_sources_commits_versions_and_duplicates(
    lock_directory: Path,
    mutate,
) -> None:
    path = _write_lock(lock_directory, mutate(_valid_lock()))
    with pytest.raises(ValueError):
        verify_lock(path)


def test_verify_lock_rejects_substring_only_and_malformed_documents(
    lock_directory: Path,
) -> None:
    substring_only = "\n".join(
        f'# {name}=={version}' for name, version in REGISTRY_PINS.items()
    ) + f"\n# transformers {EXPECTED_TRANSFORMERS_COMMIT}\n"
    for payload in (substring_only, "[[package]\n", "version = nan"):
        with pytest.raises(ValueError):
            verify_lock(_write_lock(lock_directory, payload))


def test_setup_artifacts_are_exact_and_cannot_start_privileged_work() -> None:
    assert (ROOT / ".wslconfig.foundation.example").read_text(
        encoding="utf-8"
    ) == (
        "[wsl2]\n"
        "memory=24GB\n"
        "swap=8GB\n"
        "processors=20\n"
        "localhostForwarding=true\n"
    )
    linux = (ROOT / "scripts/foundation/setup-linux.sh").read_text(
        encoding="utf-8"
    )
    wsl = (ROOT / "scripts/foundation/setup-wsl.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in linux
    assert "https://astral.sh/uv/0.11.28/install.sh" in linux
    assert "uv sync --python 3.12 --extra dev --extra foundation --locked" in linux
    assert 'doctor --profile "$profile"' in linux
    assert "SETUP COMPLETE" in linux
    assert "TRAINING HAS NOT STARTED" in linux
    assert "microsoft" in wsl.casefold()
    assert 'exec "$repo_root/scripts/foundation/setup-linux.sh" local' in wsl
    forbidden = (
        "authorization-finalize",
        "foundation train",
        "foundation resume",
        "huggingface-cli download",
        "snapshot_download",
        "c:/pneuma-data",
    )
    combined = f"{linux}\n{wsl}".casefold()
    assert all(value not in combined for value in forbidden)
