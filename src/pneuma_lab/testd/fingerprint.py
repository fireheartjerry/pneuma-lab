"""Length-framed content identities for the fresh-process test runner."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import platform
import sys
from collections.abc import Iterable


def _frame(parts: Iterable[bytes]) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def _normalized_paths(
    root: Path, paths: Iterable[Path]
) -> tuple[tuple[str, bytes], ...]:
    base = Path(root).resolve(strict=True)
    result: list[tuple[str, bytes]] = []
    for candidate in paths:
        path = (
            (base / candidate).resolve(strict=True)
            if not Path(candidate).is_absolute()
            else Path(candidate).resolve(strict=True)
        )
        relative = path.relative_to(base).as_posix()
        if not path.is_file():
            raise ValueError(f"fingerprint input is not a file: {relative}")
        result.append((relative, path.read_bytes()))
    if len({path for path, _payload in result}) != len(result):
        raise ValueError("fingerprint inputs contain duplicate paths")
    return tuple(sorted(result))


@dataclass(frozen=True, slots=True)
class CheckoutFingerprint:
    digest: str
    paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StableRunnerFingerprint:
    digest: str
    paths: tuple[str, ...]
    cache_tag: str
    executable: str
    platform_tuple: tuple[str, str, str]


@dataclass(frozen=True, slots=True)
class ApplicationFingerprint:
    digest: str
    paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EnvironmentFingerprint:
    digest: str
    keys: tuple[str, ...]


def checkout_fingerprint(root: Path, *, paths: Iterable[Path]) -> CheckoutFingerprint:
    entries = _normalized_paths(root, paths)
    return CheckoutFingerprint(
        _frame(part for path, payload in entries for part in (path.encode(), payload)),
        tuple(path for path, _payload in entries),
    )


def application_fingerprint(
    root: Path, *, paths: Iterable[Path]
) -> ApplicationFingerprint:
    checkout = checkout_fingerprint(root, paths=paths)
    return ApplicationFingerprint(checkout.digest, checkout.paths)


def stable_runner_fingerprint(
    root: Path, *, paths: Iterable[Path]
) -> StableRunnerFingerprint:
    checkout = checkout_fingerprint(root, paths=paths)
    machine = (platform.system(), platform.machine(), platform.platform())
    return StableRunnerFingerprint(
        _frame(
            (
                checkout.digest.encode(),
                sys.implementation.cache_tag.encode(),
                str(Path(sys.executable).resolve()).encode(),
                *[item.encode() for item in machine],
            )
        ),
        checkout.paths,
        sys.implementation.cache_tag,
        str(Path(sys.executable).resolve()),
        machine,
    )


def environment_fingerprint(keys: Iterable[str]) -> EnvironmentFingerprint:
    ordered = tuple(sorted(set(keys)))
    if any(type(key) is not str or not key for key in ordered):
        raise ValueError("environment keys must be non-empty exact text")
    return EnvironmentFingerprint(
        _frame(
            part
            for key in ordered
            for part in (key.encode(), os.environ.get(key, "").encode())
        ),
        ordered,
    )
