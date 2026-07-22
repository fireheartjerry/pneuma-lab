"""Mint fail-closed G0 receipts from two launcher-owned full pytest runs."""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
from pathlib import PurePosixPath
import platform as platform_module
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from types import MappingProxyType
from typing import Any
import xml.etree.ElementTree as ElementTree


_FIXED_CONFIG_PATHS = (
    ".gitattributes",
    "pyproject.toml",
    "uv.lock",
    "scripts/__init__.py",
    "scripts/research/__init__.py",
    "scripts/research/capture_baseline.py",
)
_BASELINE_PARTS = ("build", "research", "baseline")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_NONCE_RE = re.compile(r"[0-9a-f]{32}")
_COUNT_RE = re.compile(r"(?:0|[1-9][0-9]*)")
_WINDOWS_PATH_RE = re.compile(r"([A-Za-z]):[\\/](.*)")
_ENV_ALLOWLIST = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "SYSTEMROOT",
    "WINDIR",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TZ",
    "WSL_DISTRO_NAME",
    "WSL_INTEROP",
    "WSLENV",
)
_ALLOWED_IGNORED_TREES = (
    ("build", "research", "baseline"),
    ("build", "research", "env"),
)
_ALLOWED_UV_ENVIRONMENT_FILE_LINKS = (
    "bin/python",
    "bin/python3",
    "bin/python3.12",
)
_ALLOWED_UV_ENVIRONMENT_DIRECTORY_LINKS = ("lib64",)
_RUNTIME_GUARDED_FUNCTION_NAMES = (
    "canonical_receipt_bytes",
    "_sha256_bytes",
    "_sha256_file",
    "_read_file",
    "_resolve_repo_root",
    "_is_linklike",
    "_safe_directory_chain",
    "_baseline_directory",
    "_require_output_dir",
    "_restricted_artifact",
    "_write_artifact",
    "_parse_gitfile_bytes",
    "_translate_windows_gitdir",
    "_resolve_linked_git_dir",
    "_sanitized_environment",
    "_git_binding",
    "_run_bound_git",
    "_verify_tracked_worktree",
    "_git_snapshot",
    "hash_project_config_bundle",
    "_fixed_config_context",
    "_source_tree_digest",
    "_runtime_module_path",
    "_launcher_hook_identity",
    "_run_process",
    "_resolve_uv_tool",
    "_validate_uv_tool",
    "_uv_project_environment",
    "_uv_python_prefix",
    "_probe_uv_runtime",
    "_validate_uv_runtime",
    "_register_case_path",
    "_environment_link_entry",
    "_environment_tree_digest",
    "_capture_context",
    "_local_name",
    "_parse_count",
    "_read_junit",
    "_require_sha256",
    "_require_commit",
    "_read_collection",
    "_context_uv_tool",
    "_pytest_pythonpath_override",
    "_full_suite_argv",
    "_context_receipt_fields",
    "_run_one",
    "_root_from_receipt",
    "_validate_receipt_id",
    "_aware_utc_timestamp",
    "_validate_process_artifacts",
    "_validate_official_receipt",
    "_collect_only_argv",
    "_independent_collection",
    "_validate_pair_receipts",
    "validate_baseline_pair",
    "require_live_g0_capability",
    "_clear_launcher_artifacts",
    "_runtime_implementation_objects",
    "_require_unmodified_runtime_implementation",
    "_run_baseline_pair_impl",
    "run_trusted_baseline_pair",
)
_RUNTIME_GUARDED_TYPE_NAMES = (
    "BaselineReceiptError",
    "_JunitSummary",
    "_CollectionEvidence",
    "_UvTool",
    "_UvRuntime",
    "_WslPathEvidence",
    "_GitBinding",
    "_CapturedProcess",
    "_LaunchSession",
    "_TrustedRun",
    "_LiveG0Capability",
    "_OfficialSessionRecord",
    "_ProjectContext",
)
_RUNTIME_GUARDED_CONSTANT_NAMES = (
    "_FIXED_CONFIG_PATHS",
    "_BASELINE_PARTS",
    "_SHA256_RE",
    "_COMMIT_RE",
    "_NONCE_RE",
    "_COUNT_RE",
    "_WINDOWS_PATH_RE",
    "_ENV_ALLOWLIST",
    "_ALLOWED_IGNORED_TREES",
    "_ALLOWED_UV_ENVIRONMENT_FILE_LINKS",
    "_ALLOWED_UV_ENVIRONMENT_DIRECTORY_LINKS",
    "_RUNTIME_GUARDED_FUNCTION_NAMES",
    "_RUNTIME_GUARDED_TYPE_NAMES",
    "_RUNTIME_GUARDED_CONSTANT_NAMES",
    "_ACTIVE_OFFICIAL_SESSIONS",
    "_UV_PROBE_CODE",
    "_PROCESS_JOURNAL_FIELDS",
    "_IMPORTED_LAUNCHER_PATH",
    "_IMPORTED_LAUNCHER_SHA256",
)


class BaselineReceiptError(ValueError):
    """Raised when baseline evidence is absent, ambiguous, or unauthorized."""


@dataclass(frozen=True)
class _JunitSummary:
    path: Path
    sha256: str
    timestamp: str
    suite_name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    duration_seconds: float
    testcase_count: int
    testcase_sha256: str


@dataclass(frozen=True)
class _CollectionEvidence:
    path: Path
    artifact_sha256: str
    nonce: str
    count: int
    collection_sha256: str
    runtime_module_relative_path: str
    hook_module_relative_path: str
    hook_module_sha256: str


@dataclass(frozen=True)
class _UvTool:
    executable: str
    version: str
    sha256: str


@dataclass(frozen=True)
class _UvRuntime:
    python_executable: str
    python_executable_sha256: str
    python_version: str
    python_runtime: str
    python_implementation: str
    python_platform: str
    installed_distributions_sha256: str
    installed_distribution_count: int
    runtime_module_relative_path: str
    runtime_module_sha256: str
    runtime_search_relative_paths: tuple[str, ...]


@dataclass(frozen=True)
class _WslPathEvidence:
    executable: str
    executable_sha256: str
    argv_sha256: str
    translated_path: str


@dataclass(frozen=True)
class _GitBinding:
    prefix: tuple[str, ...]
    executable: str
    executable_sha256: str
    admin_path: str
    marker_kind: str
    marker_sha256: str
    wslpath: _WslPathEvidence | None


@dataclass(frozen=True)
class _CapturedProcess:
    process_id: int
    returncode: int
    stdout: bytes
    stderr: bytes
    started_at_utc: str
    finished_at_utc: str
    elapsed_ns: int


@dataclass
class _LaunchSession:
    root: Path
    token: object
    official_runtime: bool
    active: bool = True


@dataclass(frozen=True)
class _TrustedRun:
    receipt: Mapping[str, Any]
    receipt_bytes: bytes
    process: _CapturedProcess
    session: _LaunchSession


@dataclass(frozen=True)
class _LiveG0Capability:
    audit_record: Mapping[str, Any]
    session: _LaunchSession

    def __reduce__(self):
        raise TypeError("live G0 capabilities are not serializable")


@dataclass
class _OfficialSessionRecord:
    session: _LaunchSession
    runs: list[_TrustedRun]
    capability: _LiveG0Capability | None = None


_ACTIVE_OFFICIAL_SESSIONS: dict[object, _OfficialSessionRecord] = {}


@dataclass(frozen=True)
class _ProjectContext:
    root: Path
    commit: str
    git_status_sha256: str
    project_config_sha256: str
    project_config_files: tuple[str, ...]
    dependency_lock_sha256: str
    git_executable: str
    git_executable_sha256: str
    git_admin_path: str
    git_marker_kind: str
    git_marker_sha256: str
    git_prefix_sha256: str
    wslpath_executable: str
    wslpath_executable_sha256: str
    wslpath_argv_sha256: str
    wslpath_translated_path: str
    tracked_tree_sha256: str
    source_root: str
    source_tree_sha256: str
    uv_executable: str
    uv_version: str
    uv_sha256: str
    uv_project_environment: str
    runtime_module_relative_path: str
    runtime_module_sha256: str
    runtime_search_relative_paths: tuple[str, ...]
    python_version: str
    python_runtime: str
    python_implementation: str
    python_executable: str
    python_executable_sha256: str
    python_platform: str
    platform: str
    installed_distributions_sha256: str
    installed_distribution_count: int
    environment_tree_sha256: str
    sanitized_environment_sha256: str
    environment_sha256: str


def canonical_receipt_bytes(value: Mapping[str, Any]) -> bytes:
    """Return compact, sorted, newline-terminated canonical JSON bytes."""

    try:
        text = json.dumps(
            dict(value),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise BaselineReceiptError("value is not canonical-JSON serializable") from exc
    return (text + "\n").encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise BaselineReceiptError(f"required file cannot be hashed: {path}") from exc
    return digest.hexdigest()


def _read_file(path: Path, *, label: str) -> tuple[Path, bytes]:
    candidate = Path(path)
    try:
        resolved = candidate.resolve(strict=True)
        if not resolved.is_file():
            raise BaselineReceiptError(f"{label} is not a regular file: {candidate}")
        return resolved, resolved.read_bytes()
    except FileNotFoundError as exc:
        raise BaselineReceiptError(f"{label} does not exist: {candidate}") from exc
    except BaselineReceiptError:
        raise
    except OSError as exc:
        raise BaselineReceiptError(f"{label} cannot be read: {candidate}") from exc


def _resolve_repo_root(repo_root: Path) -> Path:
    try:
        root = Path(repo_root).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError(f"repository root does not exist: {repo_root}") from exc
    if not root.is_dir():
        raise BaselineReceiptError("repository root must be a directory")
    return root


def _is_linklike(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _safe_directory_chain(
    root: Path,
    parts: Sequence[str],
    *,
    create: bool,
) -> Path:
    current = root
    for part in parts:
        if not part or part in {".", ".."} or "/" in part or "\\" in part:
            raise BaselineReceiptError("managed directory component is malformed")
        candidate = current / part
        if os.path.lexists(candidate):
            if _is_linklike(candidate):
                raise BaselineReceiptError(
                    "managed directory chain contains a symlink or junction"
                )
            try:
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                raise BaselineReceiptError("managed directory cannot be resolved") from exc
            if resolved != candidate or not resolved.is_dir():
                raise BaselineReceiptError("managed path is not an in-tree directory")
        elif create:
            try:
                candidate.mkdir()
                resolved = candidate.resolve(strict=True)
            except OSError as exc:
                raise BaselineReceiptError("managed directory cannot be created") from exc
            if resolved != candidate or _is_linklike(candidate) or not resolved.is_dir():
                raise BaselineReceiptError("managed directory escaped during creation")
        else:
            raise BaselineReceiptError("managed directory does not exist")
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise BaselineReceiptError("managed directory escapes the worktree") from exc
        current = candidate
    return current


def _baseline_directory(root: Path, *, create: bool) -> Path:
    try:
        return _safe_directory_chain(root, _BASELINE_PARTS, create=create)
    except BaselineReceiptError as exc:
        raise BaselineReceiptError(
            f"build/research/baseline must be a safe in-tree directory: {exc}"
        ) from exc


def _require_output_dir(root: Path, output_dir: Path) -> Path:
    supplied = Path(output_dir)
    if not supplied.is_absolute():
        supplied = root / supplied
    expected = root.joinpath(*_BASELINE_PARTS)
    if Path(os.path.abspath(supplied)) != expected:
        raise BaselineReceiptError(
            "trusted output must be exactly build/research/baseline"
        )
    return _baseline_directory(root, create=True)


def _restricted_artifact(
    path: Path,
    *,
    root: Path,
    must_exist: bool,
) -> Path:
    baseline = _baseline_directory(root, create=not must_exist)
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = baseline / candidate
    if must_exist:
        resolved, _ = _read_file(candidate, label="baseline artifact")
        if resolved.parent != baseline:
            raise BaselineReceiptError(
                "JUnit and evidence reads must stay below build/research/baseline"
            )
        return resolved
    try:
        parent = candidate.parent.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError("baseline artifact parent does not exist") from exc
    if parent != baseline or candidate.name in {"", ".", ".."}:
        raise BaselineReceiptError(
            "all writes must stay directly below build/research/baseline"
        )
    return parent / candidate.name


def _write_artifact(root: Path, path: Path, payload: bytes) -> None:
    target = _restricted_artifact(path, root=root, must_exist=False)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = ""
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                Path(temporary).unlink()
            except FileNotFoundError:
                pass


def _parse_gitfile_bytes(payload: bytes) -> str:
    if not payload or b"\x00" in payload:
        raise BaselineReceiptError("worktree .git link is malformed")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BaselineReceiptError("worktree .git link is not UTF-8") from exc
    if text.endswith("\n"):
        text = text[:-1]
        if text.endswith("\r"):
            text = text[:-1]
    elif text.endswith("\r"):
        text = text[:-1]
    if "\n" in text or "\r" in text or not text.startswith("gitdir: "):
        raise BaselineReceiptError("worktree .git link must contain exactly one gitdir line")
    raw_path = text[len("gitdir: ") :]
    if not raw_path:
        raise BaselineReceiptError("worktree .git link has an empty path")
    return raw_path


def _translate_windows_gitdir(
    raw_path: str,
    *,
    environment: Mapping[str, str],
) -> tuple[Path, _WslPathEvidence]:
    candidate = shutil.which("wslpath", path=environment.get("PATH"))
    if not candidate:
        raise BaselineReceiptError("wslpath is unavailable for a Windows gitdir")
    try:
        executable = Path(os.path.abspath(candidate))
        executable.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError("wslpath executable cannot be resolved") from exc
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise BaselineReceiptError("wslpath executable is not executable")
    argv = [str(executable), "-u", "--", raw_path]
    result = subprocess.run(
        argv,
        env=dict(environment),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise BaselineReceiptError(
            "wslpath failed: "
            f"returncode={result.returncode} "
            f"stdout_sha256={_sha256_bytes(result.stdout)} "
            f"stderr_sha256={_sha256_bytes(result.stderr)}"
        )
    try:
        output = result.stdout.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise BaselineReceiptError("wslpath output is not UTF-8") from exc
    if output.endswith("\n"):
        output = output[:-1]
        if output.endswith("\r"):
            output = output[:-1]
    if not output or "\n" in output or "\r" in output or not PurePosixPath(output).is_absolute():
        raise BaselineReceiptError("wslpath output must be one absolute POSIX path")
    try:
        translated = Path(output).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError("wslpath target does not exist") from exc
    if not translated.is_dir():
        raise BaselineReceiptError("wslpath target is not a directory")
    evidence = _WslPathEvidence(
        executable=str(executable),
        executable_sha256=_sha256_file(executable),
        argv_sha256=_sha256_bytes(canonical_receipt_bytes({"argv": argv})),
        translated_path=str(translated),
    )
    return translated, evidence


def _resolve_linked_git_dir(
    raw_path: str,
    *,
    worktree_root: Path,
    environment: Mapping[str, str],
) -> tuple[Path, _WslPathEvidence | None]:
    if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path:
        raise BaselineReceiptError("linked worktree gitdir is malformed")
    normalized = raw_path.replace("\\", "/")
    windows_path = _WINDOWS_PATH_RE.fullmatch(normalized)
    evidence = None
    if windows_path and os.name != "nt":
        candidate, evidence = _translate_windows_gitdir(
            raw_path, environment=environment
        )
    else:
        candidate = Path(normalized)
        if not candidate.is_absolute():
            candidate = worktree_root / candidate
        try:
            candidate = candidate.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise BaselineReceiptError(
                f"linked worktree gitdir does not exist: {raw_path}"
            ) from exc
    if not candidate.is_dir():
        raise BaselineReceiptError("linked worktree gitdir is not a directory")
    return candidate, evidence


def resolve_linked_git_dir(raw_path: str, *, worktree_root: Path) -> Path:
    """Resolve one exact linked-worktree gitdir under the current platform."""

    path, _ = _resolve_linked_git_dir(
        raw_path,
        worktree_root=worktree_root,
        environment=_sanitized_environment(),
    )
    return path


def _sanitized_environment(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in _ENV_ALLOWLIST
        if name in os.environ
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "PYTHONHASHSEED": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        }
    )
    if extra:
        environment.update({str(key): str(value) for key, value in extra.items()})
    return environment


def _git_binding(root: Path, environment: Mapping[str, str]) -> _GitBinding:
    candidate = shutil.which("git", path=environment.get("PATH"))
    if not candidate:
        raise BaselineReceiptError("scoped Git executable is unavailable")
    try:
        executable = Path(candidate).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError("scoped Git executable cannot be resolved") from exc
    if not executable.is_file():
        raise BaselineReceiptError("scoped Git executable is not a regular file")
    try:
        executable.relative_to(root)
    except ValueError:
        pass
    else:
        raise BaselineReceiptError("scoped Git executable may not come from the worktree")

    marker = root / ".git"
    if not os.path.lexists(marker) or _is_linklike(marker):
        raise BaselineReceiptError("repository root has no canonical .git marker")
    wslpath = None
    if marker.is_dir():
        admin = marker.resolve(strict=True)
        marker_kind = "directory"
        marker_sha256 = _sha256_bytes(
            canonical_receipt_bytes(
                {"kind": marker_kind, "canonical_path": str(admin)}
            )
        )
        prefix = (
            str(executable),
            f"--git-dir={admin}",
            f"--work-tree={root}",
        )
    elif marker.is_file():
        payload = marker.read_bytes()
        raw_path = _parse_gitfile_bytes(payload)
        admin, wslpath = _resolve_linked_git_dir(
            raw_path,
            worktree_root=root,
            environment=environment,
        )
        marker_kind = "file"
        marker_sha256 = _sha256_bytes(payload)
        prefix = (
            str(executable),
            f"--git-dir={admin}",
            f"--work-tree={root}",
        )
    else:
        raise BaselineReceiptError("repository .git marker is neither a file nor directory")

    binding = _GitBinding(
        prefix=prefix,
        executable=str(executable),
        executable_sha256=_sha256_file(executable),
        admin_path=str(admin),
        marker_kind=marker_kind,
        marker_sha256=marker_sha256,
        wslpath=wslpath,
    )
    inside = _run_bound_git(root, binding, "rev-parse", "--is-inside-work-tree")
    if inside.decode("ascii", errors="strict").strip() != "true":
        raise BaselineReceiptError("scoped Git is not inside the requested worktree")
    admin_raw = _run_bound_git(root, binding, "rev-parse", "--absolute-git-dir")
    top_raw = _run_bound_git(root, binding, "rev-parse", "--show-toplevel")
    try:
        observed_admin = Path(
            admin_raw.decode("utf-8", errors="strict").strip()
        ).resolve(strict=True)
        observed_top = Path(
            top_raw.decode("utf-8", errors="strict").strip()
        ).resolve(strict=True)
    except (FileNotFoundError, OSError, UnicodeDecodeError) as exc:
        raise BaselineReceiptError("scoped Git reported malformed canonical paths") from exc
    if observed_admin != admin:
        raise BaselineReceiptError("scoped Git reported an unexpected administrative path")
    if observed_top != root:
        raise BaselineReceiptError("scoped Git reported an unexpected root")
    return binding


def _run_bound_git(root: Path, binding: _GitBinding, *arguments: str) -> bytes:
    environment = _sanitized_environment()
    command = [*binding.prefix, *arguments]
    result = subprocess.run(
        command,
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise BaselineReceiptError(
            "scoped Git command failed: "
            f"returncode={result.returncode} "
            f"stdout_sha256={_sha256_bytes(result.stdout)} "
            f"stderr_sha256={_sha256_bytes(result.stderr)}"
        )
    return result.stdout


def _run_git(root: Path, *arguments: str) -> bytes:
    environment = _sanitized_environment()
    return _run_bound_git(root, _git_binding(root, environment), *arguments)


def _verify_tracked_worktree(
    root: Path,
    binding: _GitBinding,
    commit: str,
) -> str:
    flags_raw = _run_bound_git(root, binding, "ls-files", "-v", "-z")
    flags = [entry for entry in flags_raw.split(b"\x00") if entry]
    abnormal = []
    for entry in flags:
        try:
            text = entry.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise BaselineReceiptError("Git index path is not UTF-8") from exc
        if len(text) < 3 or text[1] != " " or text[0] != "H":
            abnormal.append(text[:80])
    if abnormal:
        raise BaselineReceiptError(
            "Git index contains assume-unchanged, skip-worktree, or non-normal flags"
        )

    object_format = _run_bound_git(
        root, binding, "rev-parse", "--show-object-format"
    ).decode("ascii", errors="strict").strip()
    if object_format not in {"sha1", "sha256"}:
        raise BaselineReceiptError("Git object format is unsupported")
    tree_raw = _run_bound_git(
        root,
        binding,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        commit,
    )
    manifest: list[dict[str, object]] = []
    expected_object_ids: list[str] = []
    hash_paths: list[str] = []
    casefolded: dict[str, str] = {}
    for record in (item for item in tree_raw.split(b"\x00") if item):
        try:
            metadata, path_bytes = record.split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii", errors="strict").split(" ")
            name = path_bytes.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise BaselineReceiptError("Git tree entry is malformed") from exc
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not relative.parts
            or "\n" in name
            or "\r" in name
        ):
            raise BaselineReceiptError("Git tree path is malformed")
        if kind != "blob" or mode not in {"100644", "100755", "120000"}:
            raise BaselineReceiptError("Git tree contains an unsupported entry")
        try:
            _register_case_path(relative, casefolded)
        except BaselineReceiptError as exc:
            raise BaselineReceiptError(
                "Git tree contains case-colliding path components"
            ) from exc
        path = root.joinpath(*relative.parts)
        parent = path.parent
        while parent != root:
            if _is_linklike(parent):
                raise BaselineReceiptError("tracked path has a linked parent")
            parent = parent.parent
        if mode == "120000":
            if path.is_symlink():
                payload = os.readlink(path).encode("utf-8")
            elif path.is_file():
                payload = path.read_bytes()
            else:
                raise BaselineReceiptError("tracked symbolic link is not materialized")
        else:
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(root)
            except (FileNotFoundError, OSError, ValueError) as exc:
                raise BaselineReceiptError("tracked file escapes or is missing") from exc
            if _is_linklike(path) or not resolved.is_file():
                raise BaselineReceiptError("tracked path is not an exact regular file")
            payload = resolved.read_bytes()
        expected_object_ids.append(object_id)
        hash_paths.append(relative.as_posix())
        manifest.append(
            {
                "mode": mode,
                "object_id": object_id,
                "path": relative.as_posix(),
                "raw_sha256": _sha256_bytes(payload),
                "size_bytes": len(payload),
            }
        )
    if not manifest or len(manifest) != len(flags):
        raise BaselineReceiptError("Git index and committed tree inventories differ")
    result = subprocess.run(
        [*binding.prefix, "hash-object", "--stdin-paths"],
        cwd=root,
        env=_sanitized_environment(),
        input=("\n".join(hash_paths) + "\n").encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise BaselineReceiptError(
            "Git clean-filter verification failed: "
            f"returncode={result.returncode} "
            f"stdout_sha256={_sha256_bytes(result.stdout)} "
            f"stderr_sha256={_sha256_bytes(result.stderr)}"
        )
    try:
        observed_object_ids = result.stdout.decode("ascii", errors="strict").splitlines()
    except UnicodeDecodeError as exc:
        raise BaselineReceiptError("Git hash-object output is malformed") from exc
    expected_length = 40 if object_format == "sha1" else 64
    if (
        observed_object_ids != expected_object_ids
        or any(len(value) != expected_length for value in observed_object_ids)
    ):
        raise BaselineReceiptError(
            "tracked working-tree bytes differ from committed HEAD after clean filters"
        )
    return _sha256_bytes(canonical_receipt_bytes({"entries": manifest}))


def _git_snapshot(
    root: Path, binding: _GitBinding | None = None
) -> tuple[str, str, str, _GitBinding]:
    active = binding or _git_binding(root, _sanitized_environment())
    commit = _run_bound_git(root, active, "rev-parse", "--verify", "HEAD").decode(
        "ascii", errors="strict"
    ).strip()
    if _COMMIT_RE.fullmatch(commit) is None:
        raise BaselineReceiptError("scoped Git HEAD is malformed")
    status = _run_bound_git(
        root, active, "status", "--porcelain=v1", "--untracked-files=all"
    )
    if status:
        raise BaselineReceiptError("trusted baseline requires a clean Git worktree")
    tracked_tree_digest = _verify_tracked_worktree(root, active, commit)
    ignored = _run_bound_git(
        root,
        active,
        "ls-files",
        "-z",
        "--others",
        "--ignored",
        "--exclude-standard",
    )
    ignored_paths = [
        PurePosixPath(name)
        for name in ignored.decode("utf-8", errors="strict").split("\x00")
        if name
    ]
    poisoned = []
    for path in ignored_paths:
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise BaselineReceiptError("Git reported a malformed ignored path")
        if not any(
            tuple(path.parts[: len(prefix)]) == prefix
            for prefix in _ALLOWED_IGNORED_TREES
        ):
            poisoned.append(path.as_posix())
    if poisoned:
        sample = ", ".join(sorted(poisoned)[:3])
        raise BaselineReceiptError(
            f"ignored executable or control surface is present: {sample}"
        )
    marker = root / ".git"
    if active.marker_kind == "file":
        if not marker.is_file() or _sha256_file(marker) != active.marker_sha256:
            raise BaselineReceiptError("worktree .git marker drifted during snapshot")
    elif not marker.is_dir():
        raise BaselineReceiptError("repository .git directory drifted during snapshot")
    return commit, _sha256_bytes(status), tracked_tree_digest, active


def hash_project_config_bundle(
    paths: Iterable[Path],
    *,
    root: Path,
) -> str:
    """Hash a caller-specified root-relative canonical configuration bundle."""

    resolved_root = _resolve_repo_root(root)
    entries: dict[str, dict[str, object]] = {}
    for supplied in paths:
        candidate = Path(supplied)
        if not candidate.is_absolute():
            candidate = resolved_root / candidate
        resolved, payload = _read_file(candidate, label="project configuration file")
        try:
            relative = resolved.relative_to(resolved_root).as_posix()
        except ValueError as exc:
            raise BaselineReceiptError(
                "project configuration file escapes repository root"
            ) from exc
        if relative in entries:
            raise BaselineReceiptError(f"project config is duplicated: {relative}")
        entries[relative] = {
            "sha256": _sha256_bytes(payload),
            "size_bytes": len(payload),
        }
    if not entries:
        raise BaselineReceiptError("project configuration bundle cannot be empty")
    manifest = {
        "files": [
            {"path": name, **entries[name]}
            for name in sorted(entries)
        ]
    }
    return _sha256_bytes(canonical_receipt_bytes(manifest))


def _fixed_config_context(root: Path) -> tuple[str, str]:
    for name in _FIXED_CONFIG_PATHS:
        lexical = root / name
        try:
            resolved = lexical.resolve(strict=True)
        except (FileNotFoundError, OSError) as exc:
            raise BaselineReceiptError(
                f"fixed project config is missing: {name}"
            ) from exc
        if resolved != lexical or not resolved.is_file():
            raise BaselineReceiptError(
                f"fixed project config is not a regular in-tree file: {name}"
            )
    launcher = (root / "scripts" / "research" / "capture_baseline.py").resolve()
    try:
        active_launcher = Path(__file__).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError("active launcher source is unavailable") from exc
    launcher_sha256 = _sha256_file(launcher)
    if (
        launcher != active_launcher
        or launcher != _IMPORTED_LAUNCHER_PATH
        or launcher_sha256 != _IMPORTED_LAUNCHER_SHA256
        or launcher_sha256 != _sha256_file(active_launcher)
    ):
        raise BaselineReceiptError(
            "active launcher differs from its import-time committed source"
        )
    digest = hash_project_config_bundle(
        [root / name for name in _FIXED_CONFIG_PATHS], root=root
    )
    lock_digest = _sha256_file(root / "uv.lock")
    return digest, lock_digest


def _source_tree_digest(root: Path, binding: _GitBinding | None = None) -> str:
    active = binding or _git_binding(root, _sanitized_environment())
    raw = _run_bound_git(
        root, active, "ls-files", "-z", "--", "src/pneuma_lab"
    )
    names = [name for name in raw.decode("utf-8", errors="strict").split("\x00") if name]
    if not names:
        raise BaselineReceiptError("tracked pneuma_lab source tree is empty")
    entries: list[dict[str, object]] = []
    source_root = (root / "src" / "pneuma_lab").resolve(strict=True)
    for name in sorted(names):
        path = (root / name).resolve(strict=True)
        try:
            path.relative_to(source_root)
        except ValueError as exc:
            raise BaselineReceiptError("tracked source path escapes src/pneuma_lab") from exc
        if not path.is_file():
            raise BaselineReceiptError("tracked source path is not a regular file")
        entries.append(
            {
                "path": Path(name).as_posix(),
                "sha256": _sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return _sha256_bytes(canonical_receipt_bytes({"files": entries}))


def _runtime_module_path(root: Path) -> str:
    importlib.invalidate_caches()
    module = importlib.import_module("pneuma_lab")
    module_file = getattr(module, "__file__", None)
    if not module_file:
        raise BaselineReceiptError("pneuma_lab runtime module has no source file")
    try:
        resolved = Path(module_file).resolve(strict=True)
        relative = resolved.relative_to(root)
        resolved.relative_to((root / "src" / "pneuma_lab").resolve(strict=True))
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise BaselineReceiptError(
            "pneuma_lab runtime import escapes the resolved worktree"
        ) from exc
    return relative.as_posix()


def _launcher_hook_identity(root: Path) -> tuple[str, str]:
    expected = root / "scripts" / "research" / "capture_baseline.py"
    package_markers = (
        root / "scripts" / "__init__.py",
        root / "scripts" / "research" / "__init__.py",
    )
    try:
        resolved = Path(__file__).resolve(strict=True)
        expected_resolved = expected.resolve(strict=True)
        relative = resolved.relative_to(root).as_posix()
        if resolved != expected_resolved:
            raise ValueError("unexpected hook module")
        for marker in package_markers:
            if _is_linklike(marker) or not marker.is_file():
                raise ValueError("namespace or linked hook package")
            marker.resolve(strict=True).relative_to(root)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise BaselineReceiptError(
            "pytest collection hook module escapes the regular worktree package"
        ) from exc
    return relative, _sha256_file(resolved)


def _run_process(
    argv: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
) -> _CapturedProcess:
    started = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    monotonic_start = time.monotonic_ns()
    try:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
    except OSError as exc:
        raise BaselineReceiptError("bound subprocess could not be launched") from exc
    return _CapturedProcess(
        process_id=process.pid,
        returncode=process.returncode,
        stdout=stdout,
        stderr=stderr,
        started_at_utc=started,
        finished_at_utc=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
        elapsed_ns=time.monotonic_ns() - monotonic_start,
    )


def _resolve_uv_tool(root: Path) -> _UvTool:
    environment = _sanitized_environment()
    candidate = shutil.which("uv", path=environment.get("PATH"))
    if not candidate:
        raise BaselineReceiptError("approved uv executable is unavailable")
    try:
        executable = Path(candidate).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError("approved uv executable cannot be resolved") from exc
    result = subprocess.run(
        [str(executable), "--version"],
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    version = result.stdout.decode("utf-8", errors="strict").strip()
    if result.returncode != 0 or not version.startswith("uv "):
        raise BaselineReceiptError("approved uv executable version probe failed")
    return _UvTool(
        executable=str(executable),
        version=version,
        sha256=_sha256_file(executable),
    )


def _validate_uv_tool(root: Path, tool: _UvTool) -> None:
    try:
        executable = Path(tool.executable).resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError("uv executable is missing") from exc
    if not executable.is_file() or _sha256_file(executable) != tool.sha256:
        raise BaselineReceiptError("uv executable digest is invalid")
    if any(part.lower() == ".venv" for part in executable.parts):
        raise BaselineReceiptError("uv executable may not come from a default .venv")
    if not isinstance(tool.version, str) or not tool.version.startswith("uv "):
        raise BaselineReceiptError("uv executable version is invalid")
    try:
        executable.relative_to(root / "build" / "research" / "env")
    except ValueError:
        return
    raise BaselineReceiptError("uv executable may not come from its project environment")


def _uv_project_environment(root: Path) -> Path:
    try:
        return _safe_directory_chain(
            root,
            ("build", "research", "env"),
            create=True,
        )
    except BaselineReceiptError as exc:
        raise BaselineReceiptError(
            "UV_PROJECT_ENVIRONMENT must be an in-tree directory"
        ) from exc


def _uv_python_prefix(root: Path, tool: _UvTool) -> list[str]:
    return [
        tool.executable,
        "run",
        "--project",
        str(root),
        "--frozen",
        "--extra",
        "dev",
        "python",
    ]


_UV_PROBE_CODE = """
import importlib
import importlib.metadata
import importlib.util
import json
import platform
import sys

module = importlib.import_module("pneuma_lab")
spec = importlib.util.find_spec("pneuma_lab")
distributions = sorted(
    {
        (str(dist.metadata.get("Name") or "<unnamed>"), str(dist.version))
        for dist in importlib.metadata.distributions()
    }
)
print(json.dumps({
    "distributions": [{"name": name, "version": version} for name, version in distributions],
    "implementation": platform.python_implementation(),
    "module_file": module.__file__,
    "module_search_locations": list(spec.submodule_search_locations or []),
    "platform": platform.platform(),
    "python_executable": sys.executable,
    "python_runtime": sys.version,
    "python_version": platform.python_version(),
}, sort_keys=True, separators=(",", ":")))
""".strip()


def _probe_uv_runtime(
    root: Path,
    tool: _UvTool,
    environment: dict[str, str],
) -> _UvRuntime:
    result = _run_process(
        [*_uv_python_prefix(root, tool), "-c", _UV_PROBE_CODE],
        cwd=root,
        environment=environment,
    )
    if result.returncode != 0:
        raise BaselineReceiptError(
            "uv-selected Python probe failed: "
            f"returncode={result.returncode} "
            f"stdout_sha256={_sha256_bytes(result.stdout)} "
            f"stderr_sha256={_sha256_bytes(result.stderr)}"
        )
    try:
        value = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineReceiptError("uv-selected Python probe output is malformed") from exc
    if not isinstance(value, dict):
        raise BaselineReceiptError("uv-selected Python probe output is malformed")
    try:
        module_path = Path(value["module_file"]).resolve(strict=True)
        relative_module = module_path.relative_to(root).as_posix()
        search_paths = tuple(
            sorted(
                Path(path).resolve(strict=True).relative_to(root).as_posix()
                for path in value["module_search_locations"]
            )
        )
        python_path = Path(value["python_executable"])
        distributions = value["distributions"]
        if not isinstance(distributions, list):
            raise TypeError("distribution inventory")
        distributions_digest = _sha256_bytes(
            canonical_receipt_bytes({"distributions": distributions})
        )
        return _UvRuntime(
            python_executable=str(python_path),
            python_executable_sha256=_sha256_file(python_path),
            python_version=str(value["python_version"]),
            python_runtime=str(value["python_runtime"]),
            python_implementation=str(value["implementation"]),
            python_platform=str(value["platform"]),
            installed_distributions_sha256=distributions_digest,
            installed_distribution_count=len(distributions),
            runtime_module_relative_path=relative_module,
            runtime_module_sha256=_sha256_file(module_path),
            runtime_search_relative_paths=search_paths,
        )
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise BaselineReceiptError("uv-selected Python probe paths are invalid") from exc


def _validate_uv_runtime(
    root: Path,
    environment_path: Path,
    runtime: _UvRuntime,
) -> None:
    try:
        environment_absolute = environment_path.resolve(strict=True)
        if environment_absolute != environment_path or _is_linklike(environment_path):
            raise ValueError("linked environment")
        python_lexical = Path(os.path.abspath(runtime.python_executable))
        python_relative = python_lexical.relative_to(environment_absolute).as_posix()
        if _is_linklike(python_lexical) and (
            python_relative not in _ALLOWED_UV_ENVIRONMENT_FILE_LINKS
        ):
            raise ValueError("unapproved linked interpreter")
        python_path = python_lexical.resolve(strict=True)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise BaselineReceiptError(
            "uv-selected Python must be rooted in UV_PROJECT_ENVIRONMENT"
        ) from exc
    if not python_path.is_file() or _sha256_file(python_path) != runtime.python_executable_sha256:
        raise BaselineReceiptError("uv-selected Python executable digest is invalid")
    if not runtime.python_version.startswith("3.12."):
        raise BaselineReceiptError("uv-selected Python must satisfy Python 3.12")
    source_root = (root / "src" / "pneuma_lab").resolve(strict=True)
    try:
        module_path = (root / runtime.runtime_module_relative_path).resolve(strict=True)
        module_path.relative_to(source_root)
        search_paths = [
            (root / relative).resolve(strict=True)
            for relative in runtime.runtime_search_relative_paths
        ]
        if not search_paths:
            raise ValueError("empty package search locations")
        for path in search_paths:
            path.relative_to(source_root)
    except (OSError, ValueError) as exc:
        raise BaselineReceiptError(
            "uv-selected pneuma_lab import escapes the resolved worktree"
        ) from exc
    if _sha256_file(module_path) != runtime.runtime_module_sha256:
        raise BaselineReceiptError("uv-selected pneuma_lab module digest is invalid")
    _require_sha256(
        "installed_distributions_sha256", runtime.installed_distributions_sha256
    )


def _register_case_path(
    relative: Path | PurePosixPath,
    observed: dict[str, str],
) -> None:
    parts = relative.parts
    for depth in range(1, len(parts) + 1):
        exact = PurePosixPath(*parts[:depth]).as_posix()
        folded = exact.casefold()
        prior = observed.get(folded)
        if prior is not None and prior != exact:
            raise BaselineReceiptError(
                "managed uv environment contains a case-colliding path component"
            )
        observed[folded] = exact


def _environment_link_entry(root: Path, path: Path) -> dict[str, object]:
    relative = path.relative_to(root).as_posix()
    try:
        target = os.readlink(path)
        resolved = path.resolve(strict=True)
    except (OSError, ValueError) as exc:
        raise BaselineReceiptError(
            "managed uv environment contains an unreadable link"
        ) from exc
    if relative in _ALLOWED_UV_ENVIRONMENT_FILE_LINKS:
        try:
            metadata = resolved.stat()
            if not stat.S_ISREG(metadata.st_mode):
                raise ValueError("interpreter target is not regular")
            primary = (root / "bin" / "python").resolve(strict=True)
            if relative != "bin/python" and resolved != primary:
                raise ValueError("interpreter aliases disagree")
        except (OSError, ValueError) as exc:
            raise BaselineReceiptError(
                "managed uv environment interpreter link is invalid"
            ) from exc
        return {
            "kind": "interpreter-symlink",
            "path": relative,
            "target": target,
            "resolved_target": str(resolved),
            "target_sha256": _sha256_file(resolved),
            "target_size_bytes": metadata.st_size,
        }
    if relative in _ALLOWED_UV_ENVIRONMENT_DIRECTORY_LINKS:
        try:
            expected = (root / "lib").resolve(strict=True)
        except OSError as exc:
            raise BaselineReceiptError(
                "managed uv environment library link is invalid"
            ) from exc
        if target != "lib" or resolved != expected or not resolved.is_dir():
            raise BaselineReceiptError(
                "managed uv environment library link is invalid"
            )
        return {
            "kind": "directory-symlink",
            "path": relative,
            "target": target,
            "resolved_target": "lib",
        }
    raise BaselineReceiptError("managed uv environment contains an unapproved link")


def _environment_tree_digest(environment: Path) -> str:
    try:
        root = environment.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise BaselineReceiptError("managed uv environment is unavailable") from exc
    if root != environment or _is_linklike(environment):
        raise BaselineReceiptError("managed uv environment is linked or escaped")
    entries: list[dict[str, object]] = []
    casefolded: dict[str, str] = {}
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for name in sorted(directories):
            path = current_path / name
            relative_path = path.relative_to(root)
            _register_case_path(relative_path, casefolded)
            if _is_linklike(path):
                entries.append(_environment_link_entry(root, path))
                continue
            try:
                metadata = path.stat()
            except OSError as exc:
                raise BaselineReceiptError(
                    "managed uv environment cannot be read"
                ) from exc
            if not path.is_dir():
                raise BaselineReceiptError(
                    "managed uv environment contains a non-directory entry"
                )
            entries.append(
                {
                    "kind": "directory",
                    "path": relative_path.as_posix(),
                    "mode": stat.S_IMODE(metadata.st_mode),
                }
            )
        for name in sorted(files):
            path = current_path / name
            relative_path = path.relative_to(root)
            _register_case_path(relative_path, casefolded)
            if _is_linklike(path):
                entries.append(_environment_link_entry(root, path))
                continue
            try:
                metadata = path.stat()
            except OSError as exc:
                raise BaselineReceiptError("managed uv environment cannot be read") from exc
            if not stat.S_ISREG(metadata.st_mode):
                raise BaselineReceiptError(
                    "managed uv environment contains a non-regular file"
                )
            entries.append(
                {
                    "kind": "file",
                    "path": relative_path.as_posix(),
                    "sha256": _sha256_file(path),
                    "size_bytes": metadata.st_size,
                    "mode": stat.S_IMODE(metadata.st_mode),
                }
            )
    if not entries:
        raise BaselineReceiptError("managed uv environment is empty")
    entries.sort(key=lambda entry: (str(entry["path"]), str(entry["kind"])))
    return _sha256_bytes(canonical_receipt_bytes({"entries": entries}))


def _capture_context(root: Path) -> _ProjectContext:
    config_digest, lock_digest = _fixed_config_context(root)
    commit, status_digest, tracked_tree_digest, git_binding = _git_snapshot(root)
    source_digest = _source_tree_digest(root, git_binding)
    tool = _resolve_uv_tool(root)
    _validate_uv_tool(root, tool)
    uv_environment = _uv_project_environment(root)
    subprocess_environment = _sanitized_environment(
        {"UV_PROJECT_ENVIRONMENT": str(uv_environment)}
    )
    runtime = _probe_uv_runtime(root, tool, subprocess_environment)
    _validate_uv_runtime(root, uv_environment, runtime)
    environment_tree_digest = _environment_tree_digest(uv_environment)
    platform_value = platform_module.platform()
    sanitized_digest = _sha256_bytes(
        canonical_receipt_bytes(subprocess_environment)
    )
    git_prefix_digest = _sha256_bytes(
        canonical_receipt_bytes({"argv": list(git_binding.prefix)})
    )
    environment_fields = {
        "dependency_lock_sha256": lock_digest,
        "git_executable_sha256": git_binding.executable_sha256,
        "git_admin_path": git_binding.admin_path,
        "git_marker_kind": git_binding.marker_kind,
        "git_marker_sha256": git_binding.marker_sha256,
        "git_prefix_sha256": git_prefix_digest,
        "installed_distributions_sha256": runtime.installed_distributions_sha256,
        "environment_tree_sha256": environment_tree_digest,
        "platform": platform_value,
        "project_config_sha256": config_digest,
        "python_executable_sha256": runtime.python_executable_sha256,
        "python_implementation": runtime.python_implementation,
        "python_platform": runtime.python_platform,
        "python_runtime": runtime.python_runtime,
        "python_version": runtime.python_version,
        "runtime_module_relative_path": runtime.runtime_module_relative_path,
        "runtime_module_sha256": runtime.runtime_module_sha256,
        "runtime_search_relative_paths": list(runtime.runtime_search_relative_paths),
        "sanitized_environment_sha256": sanitized_digest,
        "source_tree_sha256": source_digest,
        "tracked_tree_sha256": tracked_tree_digest,
        "uv_executable_sha256": tool.sha256,
        "uv_project_environment": str(uv_environment),
        "uv_version": tool.version,
        "wslpath_executable_sha256": (
            git_binding.wslpath.executable_sha256 if git_binding.wslpath else ""
        ),
        "wslpath_argv_sha256": (
            git_binding.wslpath.argv_sha256 if git_binding.wslpath else ""
        ),
        "wslpath_translated_path": (
            git_binding.wslpath.translated_path if git_binding.wslpath else ""
        ),
    }
    return _ProjectContext(
        root=root,
        commit=commit,
        git_status_sha256=status_digest,
        project_config_sha256=config_digest,
        project_config_files=_FIXED_CONFIG_PATHS,
        dependency_lock_sha256=lock_digest,
        git_executable=git_binding.executable,
        git_executable_sha256=git_binding.executable_sha256,
        git_admin_path=git_binding.admin_path,
        git_marker_kind=git_binding.marker_kind,
        git_marker_sha256=git_binding.marker_sha256,
        git_prefix_sha256=git_prefix_digest,
        wslpath_executable=(
            git_binding.wslpath.executable if git_binding.wslpath else ""
        ),
        wslpath_executable_sha256=(
            git_binding.wslpath.executable_sha256 if git_binding.wslpath else ""
        ),
        wslpath_argv_sha256=(
            git_binding.wslpath.argv_sha256 if git_binding.wslpath else ""
        ),
        wslpath_translated_path=(
            git_binding.wslpath.translated_path if git_binding.wslpath else ""
        ),
        tracked_tree_sha256=tracked_tree_digest,
        source_root="src/pneuma_lab",
        source_tree_sha256=source_digest,
        uv_executable=tool.executable,
        uv_version=tool.version,
        uv_sha256=tool.sha256,
        uv_project_environment=str(uv_environment),
        runtime_module_relative_path=runtime.runtime_module_relative_path,
        runtime_module_sha256=runtime.runtime_module_sha256,
        runtime_search_relative_paths=runtime.runtime_search_relative_paths,
        python_version=runtime.python_version,
        python_runtime=runtime.python_runtime,
        python_implementation=runtime.python_implementation,
        python_executable=runtime.python_executable,
        python_executable_sha256=runtime.python_executable_sha256,
        python_platform=runtime.python_platform,
        platform=platform_value,
        installed_distributions_sha256=runtime.installed_distributions_sha256,
        installed_distribution_count=runtime.installed_distribution_count,
        environment_tree_sha256=environment_tree_digest,
        sanitized_environment_sha256=sanitized_digest,
        environment_sha256=_sha256_bytes(canonical_receipt_bytes(environment_fields)),
    )


def _local_name(tag: object) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _parse_count(suite: ElementTree.Element, name: str) -> int:
    raw = suite.attrib.get(name)
    if raw is None or _COUNT_RE.fullmatch(raw) is None:
        raise BaselineReceiptError(f"JUnit XML has an invalid {name!r} count")
    return int(raw)


def _read_junit(pytest_xml: Path, *, root: Path) -> _JunitSummary:
    path = _restricted_artifact(pytest_xml, root=root, must_exist=True)
    payload = path.read_bytes()
    if not payload.strip() or b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise BaselineReceiptError("JUnit XML is malformed")
    try:
        document = ElementTree.fromstring(payload)
    except ElementTree.ParseError as exc:
        raise BaselineReceiptError("JUnit XML is malformed") from exc
    if _local_name(document.tag) not in {"testsuite", "testsuites"}:
        raise BaselineReceiptError("JUnit XML root is invalid")
    suites = [node for node in document.iter() if _local_name(node.tag) == "testsuite"]
    leaves = [
        suite
        for suite in suites
        if not any(
            child is not suite and _local_name(child.tag) == "testsuite"
            for child in suite.iter()
        )
    ]
    if not leaves:
        raise BaselineReceiptError("JUnit XML contains no suites")
    totals = {name: 0 for name in ("tests", "failures", "errors", "skipped")}
    duration = Decimal(0)
    timestamps: set[str] = set()
    suite_names: set[str] = set()
    for suite in leaves:
        counts = {name: _parse_count(suite, name) for name in totals}
        if counts["tests"] < sum(counts[name] for name in ("failures", "errors", "skipped")):
            raise BaselineReceiptError("JUnit outcome counts exceed test count")
        for name, value in counts.items():
            totals[name] += value
        try:
            suite_duration = Decimal(suite.attrib["time"])
        except (KeyError, InvalidOperation) as exc:
            raise BaselineReceiptError("JUnit duration is malformed") from exc
        if not suite_duration.is_finite() or suite_duration < 0:
            raise BaselineReceiptError("JUnit duration is malformed")
        duration += suite_duration
        timestamp = suite.attrib.get("timestamp", "")
        try:
            datetime.fromisoformat(timestamp[:-1] + "+00:00" if timestamp.endswith("Z") else timestamp)
        except ValueError as exc:
            raise BaselineReceiptError("JUnit timestamp is malformed") from exc
        if not timestamp:
            raise BaselineReceiptError("JUnit timestamp is missing")
        timestamps.add(timestamp)
        name = suite.attrib.get("name", "")
        if not name:
            raise BaselineReceiptError("JUnit suite name is missing")
        suite_names.add(name)
    if totals["tests"] <= 0 or len(timestamps) != 1 or len(suite_names) != 1:
        raise BaselineReceiptError("JUnit suite summary is ambiguous")
    testcases = []
    for case in document.iter():
        if _local_name(case.tag) != "testcase":
            continue
        testcases.append(
            {
                "classname": case.attrib.get("classname", ""),
                "file": case.attrib.get("file", ""),
                "line": case.attrib.get("line", ""),
                "name": case.attrib.get("name", ""),
            }
        )
    if len(testcases) != totals["tests"]:
        raise BaselineReceiptError("JUnit testcase collection does not match its count")
    duration_seconds = float(duration)
    if not math.isfinite(duration_seconds):
        raise BaselineReceiptError("JUnit duration exceeds finite range")
    return _JunitSummary(
        path=path,
        sha256=_sha256_bytes(payload),
        timestamp=next(iter(timestamps)),
        suite_name=next(iter(suite_names)),
        tests=totals["tests"],
        failures=totals["failures"],
        errors=totals["errors"],
        skipped=totals["skipped"],
        duration_seconds=duration_seconds,
        testcase_count=len(testcases),
        testcase_sha256=_sha256_bytes(
            canonical_receipt_bytes({"testcases": sorted(testcases, key=lambda item: tuple(item.values()))})
        ),
    )


def _require_sha256(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise BaselineReceiptError(f"{name} is not a SHA-256 digest")
    return value


def _require_commit(value: object) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise BaselineReceiptError("commit is not an exact Git object ID")
    return value


def _diagnostic_environment_digest(
    python_version: str,
    platform_value: str,
    lock_digest: str,
    config_digest: str,
) -> str:
    return _sha256_bytes(
        canonical_receipt_bytes(
            {
                "dependency_lock_sha256": lock_digest,
                "platform": platform_value,
                "project_config_sha256": config_digest,
                "python_version": python_version,
            }
        )
    )


def build_baseline_receipt(
    pytest_xml: Path,
    *,
    commit: str,
    python_version: str,
    dependency_lock_sha256: str,
    project_config_sha256: str,
    repo_root: Path,
) -> dict:
    """Parse one JUnit file into a diagnostic receipt with no G0 authority."""

    root = _resolve_repo_root(repo_root)
    summary = _read_junit(pytest_xml, root=root)
    if summary.failures or summary.errors:
        raise BaselineReceiptError(
            f"JUnit suite is not green: failures={summary.failures} errors={summary.errors}"
        )
    commit = _require_commit(commit)
    if not isinstance(python_version, str) or not python_version:
        raise BaselineReceiptError("python_version is required")
    lock_digest = _require_sha256("dependency_lock_sha256", dependency_lock_sha256)
    config_digest = _require_sha256("project_config_sha256", project_config_sha256)
    platform_value = platform_module.platform()
    receipt = {
        "schema_version": 2,
        "kind": "parsed_junit_nonofficial",
        "authority": "none",
        "official_g0": False,
        "tests": summary.tests,
        "passed": summary.tests - summary.failures - summary.errors - summary.skipped,
        "failures": summary.failures,
        "errors": summary.errors,
        "skipped": summary.skipped,
        "duration_seconds": summary.duration_seconds,
        "commit": commit,
        "python_version": python_version,
        "platform": platform_value,
        "dependency_lock_sha256": lock_digest,
        "project_config_sha256": config_digest,
        "environment_sha256": _diagnostic_environment_digest(
            python_version, platform_value, lock_digest, config_digest
        ),
        "junit_path": str(summary.path),
        "junit_timestamp": summary.timestamp,
        "junit_sha256": summary.sha256,
        "junit_suite_name": summary.suite_name,
        "collection_count": summary.testcase_count,
        "collection_sha256": summary.testcase_sha256,
    }
    return {**receipt, "receipt_id": _sha256_bytes(canonical_receipt_bytes(receipt))}


def pytest_collection_finish(session) -> None:
    """Launcher-owned pytest hook: persist canonical node IDs before execution."""

    nonce = os.environ.get("PNEUMA_BASELINE_NONCE")
    output = os.environ.get("PNEUMA_BASELINE_COLLECTION_PATH")
    repo = os.environ.get("PNEUMA_BASELINE_REPO_ROOT")
    if not nonce and not output and not repo:
        return
    if not nonce or not output or not repo or _NONCE_RE.fullmatch(nonce) is None:
        raise BaselineReceiptError("launcher collection hook environment is malformed")
    root = _resolve_repo_root(Path(repo))
    module_path = _runtime_module_path(root)
    hook_path, hook_sha256 = _launcher_hook_identity(root)
    nodeids = sorted(item.nodeid for item in session.items)
    if not nodeids or len(nodeids) != len(set(nodeids)):
        raise BaselineReceiptError("launcher collection is empty or ambiguous")
    payload = {
        "nonce": nonce,
        "nodeids": nodeids,
        "runtime_module_relative_path": module_path,
        "hook_module_relative_path": hook_path,
        "hook_module_sha256": hook_sha256,
    }
    _write_artifact(root, Path(output), canonical_receipt_bytes(payload))


def _read_collection(path: Path, *, root: Path, nonce: str) -> _CollectionEvidence:
    resolved = _restricted_artifact(path, root=root, must_exist=True)
    payload = resolved.read_bytes()
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineReceiptError("collection evidence is malformed") from exc
    if not isinstance(value, dict) or set(value) != {
        "nonce",
        "nodeids",
        "runtime_module_relative_path",
        "hook_module_relative_path",
        "hook_module_sha256",
    }:
        raise BaselineReceiptError("collection evidence fields are malformed")
    if value["nonce"] != nonce:
        raise BaselineReceiptError("collection evidence nonce mismatch")
    nodeids = value["nodeids"]
    if (
        not isinstance(nodeids, list)
        or not nodeids
        or any(not isinstance(item, str) or not item for item in nodeids)
        or nodeids != sorted(nodeids)
        or len(nodeids) != len(set(nodeids))
    ):
        raise BaselineReceiptError("collection evidence node IDs are malformed")
    runtime_path = value["runtime_module_relative_path"]
    if not isinstance(runtime_path, str) or not runtime_path.startswith("src/pneuma_lab/"):
        raise BaselineReceiptError("collection runtime module escapes the worktree")
    hook_path = value["hook_module_relative_path"]
    hook_sha256 = value["hook_module_sha256"]
    expected_hook_path, expected_hook_sha256 = _launcher_hook_identity(root)
    if hook_path != expected_hook_path or hook_sha256 != expected_hook_sha256:
        raise BaselineReceiptError("collection hook module identity drifted")
    return _CollectionEvidence(
        path=resolved,
        artifact_sha256=_sha256_bytes(payload),
        nonce=nonce,
        count=len(nodeids),
        collection_sha256=_sha256_bytes(
            canonical_receipt_bytes({"nodeids": nodeids})
        ),
        runtime_module_relative_path=runtime_path,
        hook_module_relative_path=hook_path,
        hook_module_sha256=hook_sha256,
    )


def _context_uv_tool(context: _ProjectContext) -> _UvTool:
    return _UvTool(
        executable=context.uv_executable,
        version=context.uv_version,
        sha256=context.uv_sha256,
    )


def _pytest_pythonpath_override(root: Path) -> str:
    paths = (root.as_posix(), (root / "src").as_posix())
    if any(any(character in path for character in ('"', "\r", "\n")) for path in paths):
        raise BaselineReceiptError("worktree path cannot be represented in pytest pythonpath")
    return "pythonpath=" + " ".join(f'"{path}"' for path in paths)


def _full_suite_argv(
    context: _ProjectContext,
    junit: Path,
    nonce: str,
) -> list[str]:
    root = context.root
    return [
        *_uv_python_prefix(root, _context_uv_tool(context)),
        "-m",
        "pytest",
        "tests",
        "-q",
        f"--confcutdir={root}",
        "-c",
        str(root / "pyproject.toml"),
        "-o",
        _pytest_pythonpath_override(root),
        f"--junitxml={junit}",
        "-o",
        f"junit_suite_name=pneuma-baseline-{nonce}",
        "-p",
        "no:cacheprovider",
        "-p",
        "scripts.research.capture_baseline",
    ]


def _context_receipt_fields(context: _ProjectContext) -> dict[str, Any]:
    values = asdict(context)
    values.pop("root")
    values["project_config_files"] = list(context.project_config_files)
    values["runtime_search_relative_paths"] = list(
        context.runtime_search_relative_paths
    )
    return values


def _run_one(
    context: _ProjectContext,
    *,
    run_index: int,
    nonce: str,
    session: _LaunchSession,
) -> _TrustedRun:
    root = context.root
    baseline = _baseline_directory(root, create=True)
    nonce_path = baseline / f"run-{run_index}-nonce.txt"
    collection_path = baseline / f"run-{run_index}-collection.json"
    junit_path = baseline / f"pytest-run-{run_index}.xml"
    stdout_path = baseline / f"run-{run_index}-stdout.bin"
    stderr_path = baseline / f"run-{run_index}-stderr.bin"
    journal_path = baseline / f"run-{run_index}-process.json"
    receipt_path = baseline / f"baseline-receipt-run-{run_index}.json"
    _write_artifact(root, nonce_path, (nonce + "\n").encode("ascii"))
    argv = _full_suite_argv(context, junit_path, nonce)
    process_environment = _sanitized_environment(
        {
            "PNEUMA_BASELINE_COLLECTION_PATH": str(collection_path),
            "PNEUMA_BASELINE_NONCE": nonce,
            "PNEUMA_BASELINE_REPO_ROOT": str(root),
            "UV_PROJECT_ENVIRONMENT": context.uv_project_environment,
        }
    )
    process = _run_process(
        argv,
        cwd=root,
        environment=process_environment,
    )
    _write_artifact(root, stdout_path, process.stdout)
    _write_artifact(root, stderr_path, process.stderr)
    if process.returncode != 0:
        raise BaselineReceiptError(
            "full-suite pytest returned a nonzero return code: "
            f"returncode={process.returncode} "
            f"stdout_sha256={_sha256_bytes(process.stdout)} "
            f"stderr_sha256={_sha256_bytes(process.stderr)}"
        )
    junit = _read_junit(junit_path, root=root)
    expected_suite = f"pneuma-baseline-{nonce}"
    if junit.suite_name != expected_suite:
        raise BaselineReceiptError("JUnit nonce suite-name mismatch")
    collection = _read_collection(collection_path, root=root, nonce=nonce)
    if collection.count != junit.tests:
        raise BaselineReceiptError("JUnit count differs from launcher collection count")
    if collection.runtime_module_relative_path != context.runtime_module_relative_path:
        raise BaselineReceiptError("subprocess pneuma_lab runtime source drifted")
    if junit.failures or junit.errors:
        raise BaselineReceiptError("full-suite JUnit is not green")
    receipt: dict[str, Any] = {
        "schema_version": 2,
        "kind": "trusted_run_audit_evidence",
        "authority": "none",
        "official_g0": False,
        "authentication": "none",
        "threat_model": "honest_local_operator",
        "run_index": run_index,
        **_context_receipt_fields(context),
        "nonce": nonce,
        "nonce_path": str(nonce_path),
        "nonce_sha256": _sha256_file(nonce_path),
        "argv": argv,
        "command_sha256": _sha256_bytes(canonical_receipt_bytes({"argv": argv})),
        "process_environment_sha256": _sha256_bytes(
            canonical_receipt_bytes(process_environment)
        ),
        "process_id": process.process_id,
        "started_at_utc": process.started_at_utc,
        "finished_at_utc": process.finished_at_utc,
        "elapsed_ns": process.elapsed_ns,
        "returncode": process.returncode,
        "stdout_sha256": _sha256_bytes(process.stdout),
        "stdout_size_bytes": len(process.stdout),
        "stdout_path": str(stdout_path),
        "stderr_sha256": _sha256_bytes(process.stderr),
        "stderr_size_bytes": len(process.stderr),
        "stderr_path": str(stderr_path),
        "junit_path": str(junit.path),
        "junit_timestamp": junit.timestamp,
        "junit_sha256": junit.sha256,
        "junit_suite_name": junit.suite_name,
        "junit_testcase_sha256": junit.testcase_sha256,
        "tests": junit.tests,
        "passed": junit.tests - junit.failures - junit.errors - junit.skipped,
        "failures": junit.failures,
        "errors": junit.errors,
        "skipped": junit.skipped,
        "duration_seconds": junit.duration_seconds,
        "collection_path": str(collection.path),
        "collection_artifact_sha256": collection.artifact_sha256,
        "collection_count": collection.count,
        "collection_sha256": collection.collection_sha256,
        "collection_hook_module_relative_path": (
            collection.hook_module_relative_path
        ),
        "collection_hook_module_sha256": collection.hook_module_sha256,
        "receipt_path": str(receipt_path),
    }
    journal = {
        "schema_version": 1,
        "kind": "baseline_process_journal",
        "run_index": run_index,
        "commit": context.commit,
        "nonce": nonce,
        "argv": argv,
        "command_sha256": receipt["command_sha256"],
        "process_environment_sha256": receipt["process_environment_sha256"],
        "process_id": process.process_id,
        "started_at_utc": process.started_at_utc,
        "finished_at_utc": process.finished_at_utc,
        "elapsed_ns": process.elapsed_ns,
        "returncode": process.returncode,
        "stdout_path": str(stdout_path),
        "stdout_sha256": receipt["stdout_sha256"],
        "stdout_size_bytes": receipt["stdout_size_bytes"],
        "stderr_path": str(stderr_path),
        "stderr_sha256": receipt["stderr_sha256"],
        "stderr_size_bytes": receipt["stderr_size_bytes"],
        "nonce_path": str(nonce_path),
        "nonce_sha256": receipt["nonce_sha256"],
        "junit_path": str(junit.path),
        "junit_sha256": junit.sha256,
        "junit_suite_name": junit.suite_name,
        "junit_testcase_sha256": junit.testcase_sha256,
        "collection_path": str(collection.path),
        "collection_artifact_sha256": collection.artifact_sha256,
        "collection_sha256": collection.collection_sha256,
        "collection_count": collection.count,
        "collection_hook_module_relative_path": (
            collection.hook_module_relative_path
        ),
        "collection_hook_module_sha256": collection.hook_module_sha256,
        "tests": junit.tests,
        "failures": junit.failures,
        "errors": junit.errors,
        "skipped": junit.skipped,
    }
    journal_bytes = canonical_receipt_bytes(journal)
    _write_artifact(root, journal_path, journal_bytes)
    receipt["process_journal_path"] = str(journal_path)
    receipt["process_journal_sha256"] = _sha256_bytes(journal_bytes)
    receipt["receipt_id"] = _sha256_bytes(canonical_receipt_bytes(receipt))
    receipt_bytes = canonical_receipt_bytes(receipt)
    _write_artifact(root, receipt_path, receipt_bytes)
    trusted_run = _TrustedRun(
        receipt=MappingProxyType(receipt),
        receipt_bytes=receipt_bytes,
        process=process,
        session=session,
    )
    if session.official_runtime:
        record = _ACTIVE_OFFICIAL_SESSIONS.get(session.token)
        if record is None or record.session is not session or len(record.runs) >= 2:
            raise BaselineReceiptError("official launcher session registry is invalid")
        record.runs.append(trusted_run)
    return trusted_run


def _root_from_receipt(receipt: Mapping[str, Any]) -> Path:
    path_value = receipt.get("junit_path")
    if not isinstance(path_value, str):
        raise BaselineReceiptError("official receipt has no exact JUnit path")
    path = Path(path_value)
    try:
        if tuple(path.parent.parts[-3:]) != _BASELINE_PARTS:
            raise BaselineReceiptError("official JUnit path is outside build/research/baseline")
        return path.parents[3].resolve(strict=True)
    except (FileNotFoundError, IndexError, OSError) as exc:
        raise BaselineReceiptError("official JUnit path cannot identify its worktree") from exc


def _validate_receipt_id(receipt: Mapping[str, Any]) -> None:
    receipt_id = _require_sha256("receipt_id", receipt.get("receipt_id"))
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_id"}
    if receipt_id != _sha256_bytes(canonical_receipt_bytes(unsigned)):
        raise BaselineReceiptError("official receipt ID is invalid")


_PROCESS_JOURNAL_FIELDS = (
    "commit",
    "nonce",
    "argv",
    "command_sha256",
    "process_environment_sha256",
    "process_id",
    "started_at_utc",
    "finished_at_utc",
    "elapsed_ns",
    "returncode",
    "stdout_path",
    "stdout_sha256",
    "stdout_size_bytes",
    "stderr_path",
    "stderr_sha256",
    "stderr_size_bytes",
    "nonce_path",
    "nonce_sha256",
    "junit_path",
    "junit_sha256",
    "junit_suite_name",
    "junit_testcase_sha256",
    "collection_path",
    "collection_artifact_sha256",
    "collection_sha256",
    "collection_count",
    "collection_hook_module_relative_path",
    "collection_hook_module_sha256",
    "tests",
    "failures",
    "errors",
    "skipped",
)


def _aware_utc_timestamp(value: object, *, label: str) -> datetime:
    if not isinstance(value, str):
        raise BaselineReceiptError(f"{label} timestamp is malformed")
    try:
        parsed = datetime.fromisoformat(
            value[:-1] + "+00:00" if value.endswith("Z") else value
        )
    except ValueError as exc:
        raise BaselineReceiptError(f"{label} timestamp is malformed") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BaselineReceiptError(f"{label} timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _validate_process_artifacts(
    receipt: Mapping[str, Any],
    *,
    root: Path,
    trusted: _TrustedRun | None,
) -> None:
    receipt_path = _restricted_artifact(
        Path(receipt.get("receipt_path", "")), root=root, must_exist=True
    )
    canonical = canonical_receipt_bytes(receipt)
    if receipt_path.read_bytes() != canonical:
        raise BaselineReceiptError("official receipt file differs from its claims")

    output_payloads: dict[str, bytes] = {}
    for stream in ("stdout", "stderr"):
        path = _restricted_artifact(
            Path(receipt.get(f"{stream}_path", "")), root=root, must_exist=True
        )
        payload = path.read_bytes()
        output_payloads[stream] = payload
        if (
            receipt.get(f"{stream}_sha256") != _sha256_bytes(payload)
            or receipt.get(f"{stream}_size_bytes") != len(payload)
        ):
            raise BaselineReceiptError(
                f"official {stream} artifact differs from process evidence"
            )

    journal_path = _restricted_artifact(
        Path(receipt.get("process_journal_path", "")), root=root, must_exist=True
    )
    journal_bytes = journal_path.read_bytes()
    if receipt.get("process_journal_sha256") != _sha256_bytes(journal_bytes):
        raise BaselineReceiptError("official process journal digest is invalid")
    try:
        journal = json.loads(journal_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BaselineReceiptError("official process journal is malformed") from exc
    if not isinstance(journal, dict) or journal_bytes != canonical_receipt_bytes(journal):
        raise BaselineReceiptError("official process journal is not canonical")
    expected_journal = {
        "schema_version": 1,
        "kind": "baseline_process_journal",
        "run_index": receipt.get("run_index"),
        **{name: receipt.get(name) for name in _PROCESS_JOURNAL_FIELDS},
    }
    if journal != expected_journal:
        raise BaselineReceiptError("official process journal differs from receipt claims")

    started = _aware_utc_timestamp(
        receipt.get("started_at_utc"), label="process start"
    )
    finished = _aware_utc_timestamp(
        receipt.get("finished_at_utc"), label="process finish"
    )
    junit_timestamp = _aware_utc_timestamp(
        receipt.get("junit_timestamp"), label="JUnit"
    )
    if started > finished or not started <= junit_timestamp <= finished:
        raise BaselineReceiptError("JUnit timestamp falls outside the process interval")
    if not isinstance(receipt.get("elapsed_ns"), int) or receipt["elapsed_ns"] <= 0:
        raise BaselineReceiptError("official process duration is malformed")

    if trusted is not None:
        if trusted.receipt_bytes != canonical or dict(trusted.receipt) != dict(receipt):
            raise BaselineReceiptError("trusted launch receipt was mutated or replaced")
        process = trusted.process
        expected_process = {
            "process_id": process.process_id,
            "returncode": process.returncode,
            "started_at_utc": process.started_at_utc,
            "finished_at_utc": process.finished_at_utc,
            "elapsed_ns": process.elapsed_ns,
            "stdout_sha256": _sha256_bytes(process.stdout),
            "stdout_size_bytes": len(process.stdout),
            "stderr_sha256": _sha256_bytes(process.stderr),
            "stderr_size_bytes": len(process.stderr),
        }
        if any(receipt.get(name) != value for name, value in expected_process.items()):
            raise BaselineReceiptError("receipt differs from the live trusted process")
        if output_payloads != {"stdout": process.stdout, "stderr": process.stderr}:
            raise BaselineReceiptError("persisted output differs from the live process")


def _validate_official_receipt(
    receipt: Mapping[str, Any],
    *,
    root: Path,
    context: _ProjectContext,
    trusted: _TrustedRun | None = None,
) -> None:
    if (
        receipt.get("kind") != "trusted_run_audit_evidence"
        or receipt.get("authority") != "none"
        or receipt.get("official_g0") is not False
        or receipt.get("authentication") != "none"
        or receipt.get("threat_model") != "honest_local_operator"
    ):
        raise BaselineReceiptError("trusted run evidence metadata is invalid")
    _validate_receipt_id(receipt)
    if receipt.get("commit") != context.commit:
        raise BaselineReceiptError("receipt commit differs from current scoped Git HEAD")
    if receipt.get("project_config_files") != list(_FIXED_CONFIG_PATHS):
        raise BaselineReceiptError("receipt omits or changes the fixed project config")
    if receipt.get("project_config_sha256") != context.project_config_sha256:
        raise BaselineReceiptError("receipt fixed project config digest drifted")
    if receipt.get("environment_sha256") != context.environment_sha256:
        raise BaselineReceiptError("receipt environment digest drifted")
    if receipt.get("uv_project_environment") != context.uv_project_environment:
        raise BaselineReceiptError("receipt UV_PROJECT_ENVIRONMENT is not worktree-bound")
    for field in (
        "dependency_lock_sha256",
        "environment_tree_sha256",
        "git_executable",
        "git_executable_sha256",
        "git_admin_path",
        "git_marker_kind",
        "git_marker_sha256",
        "git_prefix_sha256",
        "wslpath_executable",
        "wslpath_executable_sha256",
        "wslpath_argv_sha256",
        "wslpath_translated_path",
        "tracked_tree_sha256",
        "source_tree_sha256",
        "runtime_module_relative_path",
        "runtime_module_sha256",
        "python_executable_sha256",
        "sanitized_environment_sha256",
        "uv_executable",
        "uv_version",
        "uv_sha256",
    ):
        if receipt.get(field) != getattr(context, field):
            raise BaselineReceiptError(f"receipt environment/source field drifted: {field}")
    if receipt.get("runtime_search_relative_paths") != list(
        context.runtime_search_relative_paths
    ):
        raise BaselineReceiptError("receipt runtime package search paths drifted")
    expected_context = _context_receipt_fields(context)
    for field, expected in expected_context.items():
        if receipt.get(field) != expected:
            raise BaselineReceiptError(
                f"persisted receipt context differs from live context: {field}"
            )
    if receipt.get("returncode") != 0:
        raise BaselineReceiptError("official G0 requires zero return code")
    if receipt.get("failures") != 0 or receipt.get("errors") != 0:
        raise BaselineReceiptError("official G0 requires a green JUnit suite")
    nonce = receipt.get("nonce")
    if not isinstance(nonce, str) or _NONCE_RE.fullmatch(nonce) is None:
        raise BaselineReceiptError("official receipt nonce is malformed")
    junit_path = _restricted_artifact(Path(receipt["junit_path"]), root=root, must_exist=True)
    expected_argv = _full_suite_argv(context, junit_path, nonce)
    if receipt.get("argv") != expected_argv:
        raise BaselineReceiptError("official receipt does not bind the fixed full-suite argv")
    if receipt.get("command_sha256") != _sha256_bytes(
        canonical_receipt_bytes({"argv": expected_argv})
    ):
        raise BaselineReceiptError("official command digest is invalid")
    expected_process_environment = _sanitized_environment(
        {
            "PNEUMA_BASELINE_COLLECTION_PATH": str(
                _baseline_directory(root, create=False)
                / Path(receipt["collection_path"]).name
            ),
            "PNEUMA_BASELINE_NONCE": nonce,
            "PNEUMA_BASELINE_REPO_ROOT": str(root),
            "UV_PROJECT_ENVIRONMENT": context.uv_project_environment,
        }
    )
    if receipt.get("process_environment_sha256") != _sha256_bytes(
        canonical_receipt_bytes(expected_process_environment)
    ):
        raise BaselineReceiptError("official process environment digest is invalid")
    if not isinstance(receipt.get("process_id"), int) or receipt["process_id"] <= 0:
        raise BaselineReceiptError("official process evidence is malformed")
    if not isinstance(receipt.get("elapsed_ns"), int) or receipt["elapsed_ns"] < 0:
        raise BaselineReceiptError("official process duration is malformed")
    for name in ("started_at_utc", "finished_at_utc"):
        try:
            datetime.fromisoformat(receipt[name])
        except (KeyError, TypeError, ValueError) as exc:
            raise BaselineReceiptError("official process timestamps are malformed") from exc
    for name in (
        "stdout_sha256",
        "stderr_sha256",
        "process_environment_sha256",
        "nonce_sha256",
        "collection_artifact_sha256",
        "collection_sha256",
        "collection_hook_module_sha256",
        "junit_sha256",
        "junit_testcase_sha256",
    ):
        _require_sha256(name, receipt.get(name))
    nonce_path = _restricted_artifact(Path(receipt["nonce_path"]), root=root, must_exist=True)
    nonce_payload = nonce_path.read_bytes()
    if nonce_payload != (nonce + "\n").encode("ascii") or _sha256_bytes(nonce_payload) != receipt["nonce_sha256"]:
        raise BaselineReceiptError("official nonce evidence is missing or replayed")
    junit = _read_junit(junit_path, root=root)
    observed_junit = {
        "junit_timestamp": junit.timestamp,
        "junit_sha256": junit.sha256,
        "junit_suite_name": junit.suite_name,
        "junit_testcase_sha256": junit.testcase_sha256,
        "tests": junit.tests,
        "failures": junit.failures,
        "errors": junit.errors,
        "skipped": junit.skipped,
        "duration_seconds": junit.duration_seconds,
    }
    if any(receipt.get(name) != value for name, value in observed_junit.items()):
        raise BaselineReceiptError("official receipt no longer matches its JUnit file")
    if junit.suite_name != f"pneuma-baseline-{nonce}":
        raise BaselineReceiptError("official JUnit nonce binding is invalid")
    collection = _read_collection(Path(receipt["collection_path"]), root=root, nonce=nonce)
    if (
        receipt.get("collection_artifact_sha256") != collection.artifact_sha256
        or receipt.get("collection_count") != collection.count
        or receipt.get("collection_sha256") != collection.collection_sha256
        or receipt.get("collection_hook_module_relative_path")
        != collection.hook_module_relative_path
        or receipt.get("collection_hook_module_sha256")
        != collection.hook_module_sha256
    ):
        raise BaselineReceiptError("official collection evidence drifted")
    if collection.count != junit.tests or receipt.get("tests") != collection.count:
        raise BaselineReceiptError(
            "receipt collection/JUnit count violates the independent collection contract"
        )
    if collection.runtime_module_relative_path != context.runtime_module_relative_path:
        raise BaselineReceiptError("collection runtime path differs from bound environment")
    _validate_process_artifacts(receipt, root=root, trusted=trusted)


def _collect_only_argv(context: _ProjectContext) -> list[str]:
    root = context.root
    return [
        *_uv_python_prefix(root, _context_uv_tool(context)),
        "-m",
        "pytest",
        "tests",
        "-q",
        "--collect-only",
        f"--confcutdir={root}",
        "-c",
        str(root / "pyproject.toml"),
        "-o",
        _pytest_pythonpath_override(root),
        "-p",
        "no:cacheprovider",
        "-p",
        "scripts.research.capture_baseline",
    ]


def _independent_collection(
    context: _ProjectContext,
    first_receipt_id: str,
    second_receipt_id: str,
) -> dict[str, Any]:
    root = context.root
    baseline = _baseline_directory(root, create=True)
    collection_path = baseline / "validation-collection.json"
    try:
        collection_path.unlink()
    except FileNotFoundError:
        pass
    nonce = _sha256_bytes(
        canonical_receipt_bytes(
            {
                "commit": context.commit,
                "run_receipt_ids": [first_receipt_id, second_receipt_id],
            }
        )
    )[:32]
    argv = _collect_only_argv(context)
    environment = _sanitized_environment(
        {
            "PNEUMA_BASELINE_COLLECTION_PATH": str(collection_path),
            "PNEUMA_BASELINE_NONCE": nonce,
            "PNEUMA_BASELINE_REPO_ROOT": str(root),
            "UV_PROJECT_ENVIRONMENT": context.uv_project_environment,
        }
    )
    process = _run_process(argv, cwd=root, environment=environment)
    if process.returncode != 0:
        raise BaselineReceiptError(
            "independent collection command failed: "
            f"returncode={process.returncode} "
            f"stdout_sha256={_sha256_bytes(process.stdout)} "
            f"stderr_sha256={_sha256_bytes(process.stderr)}"
        )
    collection = _read_collection(collection_path, root=root, nonce=nonce)
    if collection.runtime_module_relative_path != context.runtime_module_relative_path:
        raise BaselineReceiptError(
            "independent collection used an unbound pneuma_lab runtime"
        )
    return {
        "validation_collection_artifact_sha256": collection.artifact_sha256,
        "validation_collection_count": collection.count,
        "validation_collection_sha256": collection.collection_sha256,
        "validation_hook_module_relative_path": collection.hook_module_relative_path,
        "validation_hook_module_sha256": collection.hook_module_sha256,
        "validation_command_sha256": _sha256_bytes(
            canonical_receipt_bytes({"argv": argv})
        ),
        "validation_environment_sha256": _sha256_bytes(
            canonical_receipt_bytes(environment)
        ),
        "validation_nonce": nonce,
        "validation_returncode": process.returncode,
        "validation_runtime_module_relative_path": (
            collection.runtime_module_relative_path
        ),
    }


def _validate_pair_receipts(
    first: Mapping[str, Any],
    second: Mapping[str, Any],
    *,
    trusted_first: _TrustedRun | None,
    trusted_second: _TrustedRun | None,
) -> dict:
    first_root = _root_from_receipt(first)
    second_root = _root_from_receipt(second)
    if first_root != second_root:
        raise BaselineReceiptError("baseline runs identify different worktrees")
    context = _capture_context(first_root)
    _validate_official_receipt(
        first, root=first_root, context=context, trusted=trusted_first
    )
    _validate_official_receipt(
        second, root=first_root, context=context, trusted=trusted_second
    )
    shared = (
        "commit",
        "project_config_sha256",
        "dependency_lock_sha256",
        "environment_sha256",
        "source_tree_sha256",
        "python_executable_sha256",
        "collection_hook_module_relative_path",
        "collection_hook_module_sha256",
        "collection_sha256",
        "collection_count",
        "tests",
    )
    if any(first.get(name) != second.get(name) for name in shared[:-3]):
        raise BaselineReceiptError("baseline pair commit, config, or environment differs")
    if (
        first.get("collection_sha256") != second.get("collection_sha256")
        or first.get("collection_count") != second.get("collection_count")
        or first.get("tests") != second.get("tests")
    ):
        raise BaselineReceiptError("baseline pair requires equal canonical collection and counts")
    validation = _independent_collection(
        context,
        first["receipt_id"],
        second["receipt_id"],
    )
    if (
        validation["validation_collection_sha256"]
        != first.get("collection_sha256")
        or validation["validation_collection_count"]
        != first.get("collection_count")
        or validation["validation_collection_count"] != first.get("tests")
        or validation["validation_hook_module_relative_path"]
        != first.get("collection_hook_module_relative_path")
        or validation["validation_hook_module_sha256"]
        != first.get("collection_hook_module_sha256")
    ):
        raise BaselineReceiptError(
            "independent collection does not match both full-suite runs"
        )
    after_collection = _capture_context(first_root)
    if after_collection != context:
        raise BaselineReceiptError(
            "commit, config, source, or uv environment drifted during independent collection"
        )
    distinct_fields = (
        ("nonce", "distinct nonces"),
        ("process_id", "distinct processes"),
        ("junit_path", "distinct JUnit paths"),
        ("junit_timestamp", "distinct JUnit timestamps"),
        ("junit_sha256", "distinct JUnit hashes"),
        ("receipt_id", "distinct receipt IDs"),
    )
    for field, label in distinct_fields:
        if first.get(field) == second.get(field):
            raise BaselineReceiptError(f"baseline pair requires {label}")
    pair: dict[str, Any] = {
        "schema_version": 2,
        "kind": "local_g0_audit_record",
        "authority": "none",
        "official_g0": False,
        "authentication": "none",
        "threat_model": "honest_local_operator",
        "live_g0_observed": bool(
            trusted_first is not None
            and trusted_second is not None
            and trusted_first.session.official_runtime
            and trusted_second.session.official_runtime
        ),
        "commit": first["commit"],
        "project_config_sha256": first["project_config_sha256"],
        "dependency_lock_sha256": first["dependency_lock_sha256"],
        "environment_sha256": first["environment_sha256"],
        "environment_tree_sha256": first["environment_tree_sha256"],
        "uv_executable": first["uv_executable"],
        "uv_version": first["uv_version"],
        "uv_sha256": first["uv_sha256"],
        "uv_project_environment": first["uv_project_environment"],
        "python_executable": first["python_executable"],
        "python_executable_sha256": first["python_executable_sha256"],
        "git_executable": first["git_executable"],
        "git_executable_sha256": first["git_executable_sha256"],
        "git_admin_path": first["git_admin_path"],
        "git_marker_kind": first["git_marker_kind"],
        "git_marker_sha256": first["git_marker_sha256"],
        "git_prefix_sha256": first["git_prefix_sha256"],
        "wslpath_executable": first["wslpath_executable"],
        "wslpath_executable_sha256": first["wslpath_executable_sha256"],
        "wslpath_argv_sha256": first["wslpath_argv_sha256"],
        "wslpath_translated_path": first["wslpath_translated_path"],
        "tracked_tree_sha256": first["tracked_tree_sha256"],
        "source_tree_sha256": first["source_tree_sha256"],
        "collection_hook_module_relative_path": first[
            "collection_hook_module_relative_path"
        ],
        "collection_hook_module_sha256": first[
            "collection_hook_module_sha256"
        ],
        "collection_sha256": first["collection_sha256"],
        "collection_count": first["collection_count"],
        "tests": first["tests"],
        "run_receipt_ids": [first["receipt_id"], second["receipt_id"]],
        "nonces": [first["nonce"], second["nonce"]],
        "process_ids": [first["process_id"], second["process_id"]],
        "junit_sha256s": [first["junit_sha256"], second["junit_sha256"]],
        "run_receipt_sha256s": [
            _sha256_file(Path(first["receipt_path"])),
            _sha256_file(Path(second["receipt_path"])),
        ],
        "process_journal_sha256s": [
            first["process_journal_sha256"],
            second["process_journal_sha256"],
        ],
        **validation,
    }
    pair["pair_id"] = _sha256_bytes(canonical_receipt_bytes(pair))
    return pair


def validate_baseline_pair(first: object, second: object) -> _LiveG0Capability:
    """Mint G0 only from two live runs owned by one active launcher session."""

    if type(first) is not _TrustedRun or type(second) is not _TrustedRun:
        raise BaselineReceiptError(
            "G0 requires live provenance from the trusted full-suite launcher"
        )
    if (
        first.session is not second.session
        or not first.session.active
        or not first.session.official_runtime
        or first.session.root != _root_from_receipt(first.receipt)
    ):
        raise BaselineReceiptError("trusted full-suite launcher capability is invalid")
    record = _ACTIVE_OFFICIAL_SESSIONS.get(first.session.token)
    if (
        record is None
        or record.session is not first.session
        or len(record.runs) != 2
        or record.runs[0] is not first
        or record.runs[1] is not second
        or record.capability is not None
    ):
        raise BaselineReceiptError("live run provenance is not launcher-registered")
    audit_record = _validate_pair_receipts(
        first.receipt,
        second.receipt,
        trusted_first=first,
        trusted_second=second,
    )
    capability = _LiveG0Capability(
        audit_record=MappingProxyType(audit_record),
        session=first.session,
    )
    record.capability = capability
    return capability


def require_live_g0_capability(value: object) -> _LiveG0Capability:
    """Accept G0 only by exact identity from its still-active launcher session."""

    if type(value) is not _LiveG0Capability:
        raise BaselineReceiptError(
            "G0 requires the exact live capability from the active launcher registry"
        )
    session = value.session
    if type(session) is not _LaunchSession:
        raise BaselineReceiptError(
            "G0 capability is not owned by the active launcher registry"
        )
    record = _ACTIVE_OFFICIAL_SESSIONS.get(session.token)
    if (
        not session.active
        or not session.official_runtime
        or record is None
        or record.session is not session
        or record.capability is not value
        or len(record.runs) != 2
        or any(run.session is not session for run in record.runs)
        or any(session.root != _root_from_receipt(run.receipt) for run in record.runs)
    ):
        raise BaselineReceiptError(
            "G0 capability is not owned by the active launcher registry"
        )
    return value


def audit_persisted_baseline_pair(first: dict, second: dict) -> dict:
    """Audit persisted evidence without granting a serialized object G0 authority."""

    audited = _validate_pair_receipts(
        first,
        second,
        trusted_first=None,
        trusted_second=None,
    )
    audited["live_g0_observed"] = False
    audited.pop("pair_id", None)
    audited["pair_id"] = _sha256_bytes(canonical_receipt_bytes(audited))
    return audited


def _clear_launcher_artifacts(root: Path) -> None:
    baseline = _baseline_directory(root, create=True)
    names = [
        "pytest-run-1.xml",
        "pytest-run-2.xml",
        "run-1-nonce.txt",
        "run-2-nonce.txt",
        "run-1-collection.json",
        "run-2-collection.json",
        "run-1-stdout.bin",
        "run-2-stdout.bin",
        "run-1-stderr.bin",
        "run-2-stderr.bin",
        "run-1-process.json",
        "run-2-process.json",
        "validation-collection.json",
        "baseline-receipt-run-1.json",
        "baseline-receipt-run-2.json",
        "baseline-pair-receipt.json",
    ]
    for name in names:
        path = baseline / name
        try:
            if path.is_dir():
                raise BaselineReceiptError(f"launcher artifact target is a directory: {name}")
            path.unlink()
        except FileNotFoundError:
            continue


def _runtime_implementation_objects() -> tuple[object, ...]:
    namespace = globals()
    guarded_functions = tuple(
        namespace[name] for name in _RUNTIME_GUARDED_FUNCTION_NAMES
    )
    guarded_types = tuple(namespace[name] for name in _RUNTIME_GUARDED_TYPE_NAMES)
    guarded_constant_identities = tuple(
        (name, id(namespace[name])) for name in _RUNTIME_GUARDED_CONSTANT_NAMES
    )
    return (
        _RUNTIME_GUARDED_FUNCTION_NAMES,
        _RUNTIME_GUARDED_TYPE_NAMES,
        _RUNTIME_GUARDED_CONSTANT_NAMES,
        guarded_functions,
        guarded_types,
        guarded_constant_identities,
        subprocess.Popen,
        subprocess.run,
        subprocess.DEVNULL,
        subprocess.PIPE,
        shutil.which,
        secrets.token_hex,
        hashlib.sha256,
        json.dumps,
        json.loads,
        ElementTree.fromstring,
        datetime,
        platform_module.platform,
        tempfile.mkstemp,
        time.monotonic_ns,
        os.environ,
        os.name,
        os.access,
        os.walk,
        os.readlink,
        os.replace,
        os.fdopen,
        os.fsync,
        os.close,
        os.path.abspath,
        os.path.lexists,
        stat.S_ISREG,
        math.isfinite,
        Path,
        PurePosixPath,
        MappingProxyType,
        asdict,
        Decimal,
    )


def _require_unmodified_runtime_implementation() -> None:
    if _runtime_implementation_objects() != _TRUSTED_RUNTIME_IMPLEMENTATION:
        raise BaselineReceiptError(
            "official G0 requires the unmodified committed runtime implementation"
        )


def _run_baseline_pair_impl(
    repo_root: Path,
    output_dir: Path,
    *,
    official_runtime: bool,
) -> _LiveG0Capability | dict:
    if official_runtime:
        _require_unmodified_runtime_implementation()
    root = _resolve_repo_root(repo_root)
    _require_output_dir(root, output_dir)
    environment_path = root / "build" / "research" / "env"
    if os.path.lexists(environment_path):
        raise BaselineReceiptError(
            "trusted baseline requires a fresh absent UV_PROJECT_ENVIRONMENT"
        )
    _clear_launcher_artifacts(root)
    initial = _capture_context(root)
    session = _LaunchSession(
        root=root,
        token=object(),
        official_runtime=official_runtime,
    )
    if official_runtime:
        if session.token in _ACTIVE_OFFICIAL_SESSIONS:
            raise BaselineReceiptError("official launcher token collision")
        _ACTIVE_OFFICIAL_SESSIONS[session.token] = _OfficialSessionRecord(
            session=session,
            runs=[],
        )
    nonces = (secrets.token_hex(16), secrets.token_hex(16))
    if nonces[0] == nonces[1]:
        raise BaselineReceiptError("trusted launcher requires distinct nonces")
    first = _run_one(
        initial, run_index=1, nonce=nonces[0], session=session
    )
    between = _capture_context(root)
    if between != initial:
        raise BaselineReceiptError("commit, config, or environment drifted between runs")
    second = _run_one(
        initial, run_index=2, nonce=nonces[1], session=session
    )
    final = _capture_context(root)
    if final != initial:
        raise BaselineReceiptError("commit, config, or environment drifted after runs")
    if official_runtime:
        result: _LiveG0Capability | dict = validate_baseline_pair(first, second)
        pair = dict(result.audit_record)
    else:
        pair = _validate_pair_receipts(
            first.receipt,
            second.receipt,
            trusted_first=first,
            trusted_second=second,
        )
        result = pair
    _write_artifact(
        root,
        _baseline_directory(root, create=True) / "baseline-pair-receipt.json",
        canonical_receipt_bytes(pair),
    )
    return result


def run_trusted_baseline_pair(
    repo_root: Path, output_dir: Path
) -> _LiveG0Capability:
    """Run two full suites only through the unmodified official implementation."""

    root = _resolve_repo_root(repo_root)
    _require_output_dir(root, output_dir)
    _require_unmodified_runtime_implementation()
    result = _run_baseline_pair_impl(root, output_dir, official_runtime=True)
    if type(result) is not _LiveG0Capability:
        raise BaselineReceiptError("official G0 capability was not produced")
    return require_live_g0_capability(result)


def run_diagnostic_baseline_pair(repo_root: Path, output_dir: Path) -> dict:
    """Exercise injected test transports without ever minting live G0 authority."""

    result = _run_baseline_pair_impl(
        repo_root,
        output_dir,
        official_runtime=False,
    )
    if not isinstance(result, dict):
        raise BaselineReceiptError("diagnostic baseline unexpectedly produced authority")
    return result


def launch_official_baseline(repo_root: Path) -> _LiveG0Capability:
    """Convenience entrypoint with the sole permitted output directory."""

    root = _resolve_repo_root(repo_root)
    return run_trusted_baseline_pair(root, root.joinpath(*_BASELINE_PARTS))


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _argument_parser().parse_args(argv)
    launch_official_baseline(arguments.repo_root)
    return 0


_IMPORTED_LAUNCHER_PATH = Path(__file__).resolve(strict=True)
_IMPORTED_LAUNCHER_SHA256 = _sha256_file(_IMPORTED_LAUNCHER_PATH)
_TRUSTED_RUNTIME_IMPLEMENTATION = _runtime_implementation_objects()


if __name__ == "__main__":
    raise SystemExit(main())
