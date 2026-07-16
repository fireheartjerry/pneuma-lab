"""Exact, read-only environment and bootstrap contracts for foundation work."""

from __future__ import annotations

from collections.abc import Mapping
import math
from pathlib import Path, PureWindowsPath
import re
import tomllib
from urllib.parse import parse_qs, urlsplit

from pneuma_lab.foundation.artifacts import bind_artifact_publication


UV_VERSION = "0.11.28"
PYTHON_SERIES = (3, 12)
TRANSFORMERS_COMMIT = "11ed2ff4df5fdfb3117f0e3365ef6ad94081ba69"
MIN_USABLE_WSL_RAM_GB = 22.0
MAX_LOCK_BYTES = 16 * 1024 * 1024

FOUNDATION_VERSION_PINS: Mapping[str, str] = {
    "torch": "2.13.0",
    "torchvision": "0.28.0",
    "bitsandbytes": "0.49.2",
    "accelerate": "1.14.0",
    "peft": "0.19.1",
    "psutil": "7.2.2",
    "pillow": "12.3.0",
    "safetensors": "0.8.0",
    "huggingface-hub": "1.23.0",
}

_SAFE_WINDOWS_PART = re.compile(r"[A-Za-z0-9._ -]+\Z")
_TRANSFORMERS_REPOSITORY = "https://github.com/huggingface/transformers.git"
_REGISTRY = "https://pypi.org/simple"


def _windows_repo_path(repo_root: Path) -> tuple[PureWindowsPath, str]:
    raw = str(repo_root)
    if any(character in raw for character in "\r\n\0;&|$`'\""):
        raise ValueError("repository path contains unsafe shell characters")
    root = PureWindowsPath(raw)
    if not re.fullmatch(r"[A-Za-z]:", root.drive) or root.root != "\\":
        raise ValueError("repository root must be an absolute Windows drive path")
    relative_parts = root.parts[1:]
    if not relative_parts:
        raise ValueError("a drive root is not a safe repository root")
    if any(
        part in {"", ".", ".."} or _SAFE_WINDOWS_PART.fullmatch(part) is None
        for part in relative_parts
    ):
        raise ValueError("repository path contains an unsafe component")
    protected = tuple(part.casefold() for part in relative_parts)
    if root.drive.casefold() == "c:" and protected[:1] == ("pneuma-data",):
        raise ValueError("repository root cannot be inside the protected corpus")
    wsl_path = "/mnt/" + root.drive[0].casefold()
    wsl_path += "/" + "/".join(relative_parts)
    return root, wsl_path


def setup_plan(repo_root: Path) -> dict:
    """Describe the inert operator setup sequence without changing the host."""

    _root, wsl_path = _windows_repo_path(repo_root)
    return {
        "copy_wslconfig": (
            "Copy-Item .wslconfig.foundation.example $HOME\\.wslconfig"
        ),
        "restart_wsl": "wsl --shutdown",
        "enter_wsl": "wsl -d Ubuntu",
        "repo_path": wsl_path,
        "setup": "bash scripts/foundation/setup-wsl.sh",
        "training_started": False,
    }


def _repository_root(path: Path) -> Path:
    for candidate in (path.parent, *path.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise ValueError("lock file is not inside a Python repository")


def _read_lock(path: Path) -> bytes:
    candidate = Path(path)
    if candidate.name != "uv.lock" or not candidate.is_absolute():
        raise ValueError("lock path must be an absolute uv.lock path")
    try:
        lexical = Path(candidate.absolute())
        root = _repository_root(lexical)
        resolved_root = root.resolve(strict=True)
        resolved_path = lexical.resolve(strict=True)
        resolved_path.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("lock path is not safely contained by its repository") from exc
    try:
        with bind_artifact_publication(
            resolved_path.parent,
            anchor_root=resolved_root,
            allowed_root=resolved_root,
        ) as publication:
            with publication.hold_read(resolved_path) as held:
                if held.size > MAX_LOCK_BYTES:
                    raise ValueError("lock file exceeds the bounded read limit")
                read = held.read_bytes()
                held.revalidate(read)
    except ValueError:
        raise
    except (OSError, RuntimeError, TypeError) as exc:
        raise ValueError("lock file could not be read through a bound handle") from exc
    return read.payload


def _reject_nonfinite(value) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("lock document contains a non-finite number")
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError("lock document contains a non-string key")
            _reject_nonfinite(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_nonfinite(nested)


def _require_registry_source(package: Mapping, name: str) -> None:
    source = package.get("source")
    if not isinstance(source, Mapping) or set(source) != {"registry"}:
        raise ValueError(f"{name} must come from the pinned package registry")
    if source["registry"] != _REGISTRY:
        raise ValueError(f"{name} has the wrong package registry")


def _require_transformers_source(package: Mapping) -> None:
    source = package.get("source")
    if not isinstance(source, Mapping) or set(source) != {"git"}:
        raise ValueError("transformers must come from the pinned git source")
    value = source["git"]
    if not isinstance(value, str):
        raise ValueError("transformers git source must be a string")
    parsed = urlsplit(value)
    repository = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    query = parse_qs(parsed.query, strict_parsing=True)
    if (
        repository != _TRANSFORMERS_REPOSITORY
        or query != {"rev": [TRANSFORMERS_COMMIT]}
        or parsed.fragment != TRANSFORMERS_COMMIT
    ):
        raise ValueError("transformers git source is not the exact pinned commit")


def _edge_names(edges, *, label: str) -> set[str]:
    if not isinstance(edges, list):
        raise ValueError(f"{label} must be a lock dependency list")
    names: set[str] = set()
    for edge in edges:
        if not isinstance(edge, Mapping) or set(edge) != {"name"}:
            raise ValueError(f"{label} contains a malformed dependency edge")
        name = edge.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{label} contains an invalid dependency name")
        canonical = name.casefold().replace("_", "-")
        if canonical in names:
            raise ValueError(f"{label} contains duplicate dependency {canonical}")
        names.add(canonical)
    return names


def _require_root_edges(indexed: Mapping[str, Mapping]) -> None:
    root = indexed.get("pneuma-lab")
    if root is None or root.get("source") != {"editable": "."}:
        raise ValueError("lock must contain the local pneuma-lab project root")
    optional = root.get("optional-dependencies")
    if not isinstance(optional, Mapping):
        raise ValueError("lock root is missing optional dependency edges")
    expected_names = set(FOUNDATION_VERSION_PINS) | {"transformers"}
    if _edge_names(optional.get("foundation"), label="foundation extra") != expected_names:
        raise ValueError("lock root foundation edges do not match the exact pins")

    metadata = root.get("metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("lock root is missing dependency metadata")
    requirements = metadata.get("requires-dist")
    if not isinstance(requirements, list):
        raise ValueError("lock root dependency metadata is malformed")
    foundation_requirements: dict[str, Mapping] = {}
    for requirement in requirements:
        if not isinstance(requirement, Mapping):
            raise ValueError("lock root contains malformed dependency metadata")
        if requirement.get("marker") != "extra == 'foundation'":
            continue
        name = requirement.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("foundation dependency metadata has an invalid name")
        canonical = name.casefold().replace("_", "-")
        if canonical in foundation_requirements:
            raise ValueError(f"duplicate foundation requirement: {canonical}")
        foundation_requirements[canonical] = requirement
    if set(foundation_requirements) != expected_names:
        raise ValueError("foundation dependency metadata is incomplete")
    for name, version in FOUNDATION_VERSION_PINS.items():
        requirement = foundation_requirements[name]
        if requirement.get("specifier") != f"=={version}":
            raise ValueError(f"foundation requirement {name} is not exact")
    transformers = foundation_requirements["transformers"]
    git = transformers.get("git")
    if not isinstance(git, str):
        raise ValueError("foundation transformers requirement is not a git pin")
    parsed = urlsplit(git)
    repository = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if (
        repository != _TRANSFORMERS_REPOSITORY
        or parse_qs(parsed.query, strict_parsing=True)
        != {"rev": [TRANSFORMERS_COMMIT]}
        or parsed.fragment
    ):
        raise ValueError("foundation transformers requirement has the wrong commit")


def verify_lock(lock_path: Path) -> None:
    """Verify required packages structurally in one strictly bound lock read."""

    payload = _read_lock(Path(lock_path))
    try:
        document = tomllib.loads(payload.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError("lock file is not strict UTF-8 TOML") from exc
    _reject_nonfinite(document)
    if type(document.get("version")) is not int or document["version"] != 1:
        raise ValueError("lock version must be the exact integer 1")
    if type(document.get("revision")) is not int or document["revision"] != 3:
        raise ValueError("lock revision must be the exact integer 3")
    if document.get("requires-python") != "==3.12.*":
        raise ValueError("lock Python requirement must be exactly ==3.12.*")
    packages = document.get("package")
    if not isinstance(packages, list):
        raise ValueError("lock file does not contain package entries")
    indexed: dict[str, Mapping] = {}
    for package in packages:
        if not isinstance(package, Mapping):
            raise ValueError("lock package entry must be a table")
        name = package.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("lock package name must be a non-empty string")
        canonical = name.casefold().replace("_", "-")
        if canonical in indexed:
            raise ValueError(f"duplicate lock package: {canonical}")
        indexed[canonical] = package
    for name, version in FOUNDATION_VERSION_PINS.items():
        package = indexed.get(name)
        if package is None:
            raise ValueError(f"lock is missing exact package {name}")
        if package.get("version") != version:
            raise ValueError(f"{name} is not pinned to {version}")
        _require_registry_source(package, name)
    transformers = indexed.get("transformers")
    if transformers is None:
        raise ValueError("lock is missing transformers")
    transformers_version = transformers.get("version")
    if (
        not isinstance(transformers_version, str)
        or not transformers_version
        or transformers_version != transformers_version.strip()
    ):
        raise ValueError("transformers must expose a resolved version")
    _require_transformers_source(transformers)
    _require_root_edges(indexed)


__all__ = [
    "FOUNDATION_VERSION_PINS",
    "MIN_USABLE_WSL_RAM_GB",
    "PYTHON_SERIES",
    "TRANSFORMERS_COMMIT",
    "UV_VERSION",
    "setup_plan",
    "verify_lock",
]
