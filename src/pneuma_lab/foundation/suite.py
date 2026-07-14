"""All-family foundation suite policy and payload-access guards."""

from __future__ import annotations

import json
import os
import re
import stat as stat_module
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, BinaryIO

from pneuma_lab.foundation.data import (
    ACTIVE_DATASET_GROUPS,
    DataAuthorizationError,
    governed_dataset_groups,
)
from pneuma_lab.foundation.source_presence import (
    SourcePresenceError,
    _is_link_or_reparse,
    _is_within,
    probe_family_presence,
)


class SuitePolicyError(ValueError):
    """Raised when suite policy cannot safely authorize the requested access."""


@dataclass(frozen=True)
class _TrustedPayload:
    path: Path
    resolved_path: Path
    device: int
    inode: int


_EXPECTED_FAMILY_MATRIX = (
    ("multi-swe-bench", "train", "later", "metadata_only", None),
    ("open-swe-traces", "train", "later", "metadata_only", None),
    ("sec-bench-pro", "governance", "never", "metadata_only", None),
    (
        "swe-bench",
        "eval",
        "never",
        "identity_metadata_only",
        "processed/swe-bench/normalized_metadata.jsonl",
    ),
    ("swe-bench-pro", "eval", "never", "metadata_only", None),
    ("swe-chat", "governance", "never", "metadata_only", None),
    ("swe-evo", "train", "later", "metadata_only", None),
    (
        "swe-gym",
        "train",
        "first_stage",
        "approved_processed_lane_only",
        None,
    ),
    (
        "swe-mera",
        "eval",
        "never",
        "identity_metadata_only",
        "processed/swe-mera/normalized_metadata.jsonl",
    ),
    (
        "swe-polybench",
        "eval",
        "later",
        "identity_metadata_only",
        "processed/swe-polybench/normalized_metadata.jsonl",
    ),
)
_EXPECTED_POLICY_KEYS = {
    "manifest_kind",
    "manifest_schema_version",
    "first_stage",
    "evaluation_identity",
    "families",
}
_EXPECTED_POLICY_ORDER = (
    "manifest_kind",
    "manifest_schema_version",
    "first_stage",
    "evaluation_identity",
    "families",
)
_EXPECTED_EVALUATION_IDENTITY = {
    "required_families": ["swe-bench", "swe-mera", "swe-polybench"],
    "blocked_unavailable_families": ["swe-bench-pro"],
}
_CANDIDATE_LANE_ID = "swe-gym-openhands-sampled"


def load_suite_policy(path: Path) -> dict[str, Any]:
    """Load a suite policy as a JSON object with domain-specific failures."""

    def reject_duplicate_members(pairs):
        value = {}
        for name, member in pairs:
            if name in value:
                raise SuitePolicyError(
                    f"suite policy has duplicate JSON member: {name}"
                )
            value[name] = member
        return value

    def reject_constant(constant: str):
        raise ValueError(f"nonstandard JSON constant: {constant}")

    try:
        value = json.loads(
            Path(path).read_bytes().decode("utf-8"),
            object_pairs_hook=reject_duplicate_members,
            parse_constant=reject_constant,
        )
    except SuitePolicyError:
        raise
    except (
        OSError,
        TypeError,
        UnicodeError,
        json.JSONDecodeError,
        RecursionError,
        ValueError,
    ) as exc:
        raise SuitePolicyError(f"suite policy must be valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SuitePolicyError("suite policy must be a JSON object")
    return value


def evaluation_identity_scope(
    policy: Mapping,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return the exact required and blocked evaluation families."""

    _validated_family_map(policy)
    evaluation_identity = policy["evaluation_identity"]
    return (
        tuple(evaluation_identity["required_families"]),
        tuple(evaluation_identity["blocked_unavailable_families"]),
    )


def _policy_entries(policy: Mapping) -> tuple[Mapping, ...]:
    if not isinstance(policy, Mapping):
        raise SuitePolicyError("suite policy must be a mapping")
    entries = policy.get("families")
    if not isinstance(entries, list):
        raise SuitePolicyError("suite policy families must be a list")
    if not all(isinstance(item, Mapping) for item in entries):
        raise SuitePolicyError("suite policy family entries must be objects")
    return tuple(entries)


def _validated_family_map(policy: Mapping) -> dict[str, Mapping]:
    if not isinstance(policy, Mapping):
        raise SuitePolicyError("suite policy must be a mapping")
    if (
        set(policy) != _EXPECTED_POLICY_KEYS
        or tuple(policy) != _EXPECTED_POLICY_ORDER
    ):
        raise SuitePolicyError("suite policy manifest has missing or extra fields")
    if policy.get("manifest_kind") != "pneuma_foundation_dataset_suite":
        raise SuitePolicyError("suite policy manifest_kind is invalid")
    if policy.get("manifest_schema_version") != "0.1.0":
        raise SuitePolicyError("suite policy manifest_schema_version is invalid")
    evaluation_identity = policy.get("evaluation_identity")
    if (
        not isinstance(evaluation_identity, Mapping)
        or tuple(evaluation_identity) != tuple(_EXPECTED_EVALUATION_IDENTITY)
        or dict(evaluation_identity) != _EXPECTED_EVALUATION_IDENTITY
    ):
        raise SuitePolicyError(
            "suite policy evaluation identity must match the exact required and "
            "blocked/unavailable family lists"
        )
    entries = _policy_entries(policy)
    families: list[str] = []
    for item in entries:
        family = item.get("family")
        if not isinstance(family, str) or not family:
            raise SuitePolicyError("suite policy family names must be non-empty strings")
        families.append(family)
    if len(families) != 10 or set(families) != set(ACTIVE_DATASET_GROUPS):
        raise SuitePolicyError("suite policy must contain each active family exactly once")
    if tuple(families) != ACTIVE_DATASET_GROUPS:
        raise SuitePolicyError("suite policy families must use documented order")

    for item, expected in zip(entries, _EXPECTED_FAMILY_MATRIX, strict=True):
        family, role, gradient, access, identity_path = expected
        expected_item = {
            "family": family,
            "terminal_role": role,
            "gradient_eligibility": gradient,
            "payload_access_100k": access,
        }
        if identity_path is not None:
            expected_item["identity_metadata_relative_path"] = identity_path
        if dict(item) != expected_item or not all(
            isinstance(value, str) for value in item.values()
        ):
            raise SuitePolicyError(
                f"{family} must match the exact policy matrix"
            )

    first_stage = policy.get("first_stage")
    if not isinstance(first_stage, Mapping):
        raise SuitePolicyError("suite policy first stage must be an object")
    if set(first_stage) != {"stage", "authorized_lane_candidates"}:
        raise SuitePolicyError(
            "suite policy first-stage authorized lane candidates or stage are missing"
        )
    if not isinstance(first_stage.get("stage"), str) or (
        first_stage.get("stage") != "100k"
    ):
        raise SuitePolicyError("suite policy first stage must be 100k")
    candidates = first_stage.get("authorized_lane_candidates")
    if not isinstance(candidates, list) or not all(
        isinstance(candidate, str) for candidate in candidates
    ) or candidates != ["swe-gym-openhands-sampled"]:
        raise SuitePolicyError(
            "suite first-stage authorized lane candidates may nominate only "
            "the OpenHands Sampled lane"
        )
    return dict(zip(families, entries, strict=True))


def _lexical_data_relative_parts(path: object) -> tuple[str, ...] | None:
    try:
        raw_path = os.fspath(path)
    except TypeError:
        return None
    if not isinstance(raw_path, str) or not raw_path:
        return None
    raw_parts = tuple(
        part for part in re.split(r"[\\/]", raw_path) if part
    )
    if not raw_parts or any(part in {".", ".."} for part in raw_parts):
        return None
    if raw_parts.count("processed") != 1:
        return None
    processed_index = raw_parts.index("processed")
    try:
        is_absolute = Path(raw_path).is_absolute()
    except (OSError, TypeError, ValueError):
        return None
    if processed_index > 0 and not is_absolute:
        return None
    relative_parts = raw_parts[processed_index:]
    if any("\x00" in part or ":" in part for part in relative_parts):
        return None
    return relative_parts


def _validate_candidate_lane(registry: Mapping) -> None:
    lanes = registry.get("lanes")
    if not isinstance(lanes, list):
        raise SuitePolicyError("candidate lane requires a registry lanes list")
    matches = []
    for lane in lanes:
        if not isinstance(lane, Mapping):
            raise SuitePolicyError("candidate lane registry entries must be objects")
        lane_id = lane.get("lane_id")
        source_family = lane.get("source_family")
        if lane_id == _CANDIDATE_LANE_ID:
            matches.append(lane)
        elif not isinstance(lane_id, str) or not isinstance(source_family, str):
            raise SuitePolicyError("candidate lane registry structure is contradictory")
    if len(matches) != 1 or matches[0].get("source_family") != "swe-gym":
        raise SuitePolicyError(
            "candidate lane must appear exactly once under the swe-gym family"
        )


def _trusted_existing_file(
    *,
    data_root: object,
    path: object,
    allowed_relative_root: tuple[str, ...],
    exact: bool,
) -> _TrustedPayload:
    try:
        root = Path(os.fspath(data_root))
        candidate = Path(os.fspath(path))
    except (TypeError, ValueError) as exc:
        raise SuitePolicyError("trusted data root and payload path must be path-like") from exc
    if not root.is_absolute() or not candidate.is_absolute():
        raise SuitePolicyError("payload path must be absolute under the trusted data root")
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise SuitePolicyError("payload path is outside the trusted data root") from exc
    relative_parts = tuple(relative.parts)
    if exact:
        lexical_allowed = relative_parts == allowed_relative_root
    else:
        lexical_allowed = relative_parts[: len(allowed_relative_root)] == (
            allowed_relative_root
        )
    if not lexical_allowed:
        raise SuitePolicyError("payload path is outside the trusted data root lane")

    current = root
    components = [root]
    for part in relative_parts:
        current = current / part
        components.append(current)
    for index, component in enumerate(components):
        try:
            if _is_link_or_reparse(component):
                raise SuitePolicyError(
                    "trusted data root path contains a link or reparse point"
                )
            metadata = component.lstat()
        except FileNotFoundError as exc:
            raise SuitePolicyError(
                f"trusted data root payload path must exist: {component}"
            ) from exc
        except SourcePresenceError as exc:
            raise SuitePolicyError(f"trusted data root metadata failed: {exc}") from exc
        except OSError as exc:
            raise SuitePolicyError(f"trusted data root metadata failed: {exc}") from exc
        expected_directory = index < len(components) - 1
        if expected_directory and not stat_module.S_ISDIR(metadata.st_mode):
            raise SuitePolicyError(
                f"trusted data root ancestor must be a directory: {component}"
            )
        if not expected_directory and not stat_module.S_ISREG(metadata.st_mode):
            raise SuitePolicyError(
                f"trusted data root payload must be a regular file: {component}"
            )

    allowed_path = root.joinpath(*allowed_relative_root)
    try:
        resolved_root = root.resolve(strict=True)
        resolved_allowed = allowed_path.resolve(strict=True)
        resolved_candidate = candidate.resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SuitePolicyError(f"trusted data root resolution failed: {exc}") from exc
    if (
        not _is_within(resolved_allowed, resolved_root)
        or not _is_within(resolved_candidate, resolved_root)
        or (exact and resolved_candidate != resolved_allowed)
        or (not exact and not _is_within(resolved_candidate, resolved_allowed))
    ):
        raise SuitePolicyError("payload resolves outside the trusted data root lane")
    return _TrustedPayload(
        path=candidate,
        resolved_path=resolved_candidate,
        device=metadata.st_dev,
        inode=metadata.st_ino,
    )


def validate_suite_policy(policy: Mapping, registry: Mapping) -> tuple[str, ...]:
    """Require exact all-family coverage coherent with the readiness registry."""

    family_map = _validated_family_map(policy)
    if not isinstance(registry, Mapping):
        raise SuitePolicyError("dataset registry must be a mapping")
    _validate_candidate_lane(registry)
    try:
        governed = governed_dataset_groups(registry)
    except (DataAuthorizationError, AttributeError, TypeError, ValueError) as exc:
        raise SuitePolicyError(f"invalid dataset registry: {exc}") from exc
    if set(governed) != set(family_map):
        raise SuitePolicyError("suite and registry families differ")
    return ACTIVE_DATASET_GROUPS


def _validate_payload_request(
    policy: Mapping,
    *,
    stage: str,
    family: str,
    lane_id: str | None,
    data_root: Path,
    path: Path,
) -> _TrustedPayload:
    family_map = _validated_family_map(policy)
    if not isinstance(stage, str) or not stage:
        raise SuitePolicyError("stage must be a non-empty string")
    if not isinstance(family, str) or not family:
        raise SuitePolicyError("family must be a non-empty string")
    item = family_map.get(family)
    if item is None:
        raise SuitePolicyError(f"unknown suite family: {family!r}")
    access_key = f"payload_access_{stage}"
    access = item.get(access_key)
    if not isinstance(access, str):
        raise SuitePolicyError(f"unknown or unsupported suite stage: {stage!r}")
    relative_parts = _lexical_data_relative_parts(path)

    approved_root = ("processed", "swe-gym", "openhands-sampled")
    approved_lane = (
        access == "approved_processed_lane_only"
        and family == "swe-gym"
        and lane_id == "swe-gym-openhands-sampled"
        and relative_parts is not None
        and relative_parts[:3] == approved_root
    )
    identity_path = item.get("identity_metadata_relative_path")
    identity_metadata = (
        access == "identity_metadata_only"
        and isinstance(identity_path, str)
        and relative_parts is not None
        and relative_parts == tuple(identity_path.split("/"))
    )
    if not (approved_lane or identity_metadata):
        raise SuitePolicyError(f"{family} is metadata-only for stage {stage}")
    if approved_lane:
        return _trusted_existing_file(
            data_root=data_root,
            path=path,
            allowed_relative_root=(
                "processed",
                "swe-gym",
                "openhands-sampled",
            ),
            exact=False,
        )
    return _trusted_existing_file(
        data_root=data_root,
        path=path,
        allowed_relative_root=tuple(str(identity_path).split("/")),
        exact=True,
    )


def _windows_final_path_from_fd(fd: int) -> Path:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    handle = msvcrt.get_osfhandle(fd)
    if handle == -1:
        raise OSError("opened payload descriptor has no Windows handle")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_final_path = kernel32.GetFinalPathNameByHandleW
    get_final_path.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    get_final_path.restype = wintypes.DWORD

    buffer_size = 512
    while True:
        buffer = ctypes.create_unicode_buffer(buffer_size)
        length = get_final_path(handle, buffer, buffer_size, 0)
        if length == 0:
            raise ctypes.WinError(ctypes.get_last_error())
        if length < buffer_size:
            value = buffer.value
            break
        buffer_size = length + 1

    extended_prefix = "\\\\?\\"
    if value.startswith(f"{extended_prefix}UNC\\"):
        value = f"\\\\{value[len(extended_prefix) + 4:]}"
    elif value.startswith(extended_prefix):
        value = value[len(extended_prefix):]
        if not re.match(r"^[A-Za-z]:\\", value):
            raise OSError("opened payload returned an unsupported Windows namespace")
    final_path = Path(value)
    if not final_path.is_absolute():
        raise OSError("opened payload final Windows path is not absolute")
    return final_path


def _final_path_from_fd(fd: int) -> Path:
    if os.name == "nt":
        return _windows_final_path_from_fd(fd)
    if sys.platform.startswith("linux"):
        final_path = Path(os.readlink(f"/proc/self/fd/{fd}"))
        if not final_path.is_absolute():
            raise OSError("opened payload final Linux path is not absolute")
        return final_path
    raise SuitePolicyError(
        "opened payload final path cannot be proven on this platform"
    )


def _path_identity(path: Path) -> str:
    try:
        raw_path = os.fspath(path)
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise ValueError("path is not absolute")
        return os.path.normcase(os.path.normpath(raw_path))
    except (OSError, TypeError, ValueError) as exc:
        raise SuitePolicyError(
            f"opened payload final path cannot be normalized: {exc}"
        ) from exc


def _open_verified_stream(target: _TrustedPayload) -> BinaryIO:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    fd: int | None = None
    try:
        fd = os.open(target.path, flags)
        metadata = os.fstat(fd)
        if not stat_module.S_ISREG(metadata.st_mode):
            raise SuitePolicyError(
                "opened payload descriptor must identify a regular file"
            )
        if (metadata.st_dev, metadata.st_ino) != (target.device, target.inode):
            raise SuitePolicyError(
                "opened payload descriptor differs from the authorized file"
            )
        final_path = _final_path_from_fd(fd)
        if _path_identity(final_path) != _path_identity(target.resolved_path):
            raise SuitePolicyError(
                "opened payload final path differs from the authorized file"
            )
        stream = os.fdopen(fd, "rb", closefd=True)
        fd = None
        return stream
    except BaseException as exc:
        if fd is not None:
            try:
                os.close(fd)
            except OSError as close_exc:
                raise SuitePolicyError(
                    "opened payload descriptor could not be closed after failure"
                ) from close_exc
        if isinstance(exc, SuitePolicyError):
            raise
        if isinstance(exc, (OSError, RuntimeError, TypeError, ValueError)):
            raise SuitePolicyError(
                f"opened payload verification failed: {exc}"
            ) from exc
        raise


@contextmanager
def open_authorized_payload(
    policy: Mapping,
    *,
    stage: str,
    family: str,
    lane_id: str | None,
    data_root: Path,
    path: Path,
) -> Iterator[BinaryIO]:
    """Yield the same read-only binary stream whose open handle was authorized.

    Authorization inspects metadata only. Callers may read the yielded stream,
    but must never reopen ``path`` after this context manager has approved it.
    """

    target = _validate_payload_request(
        policy,
        stage=stage,
        family=family,
        lane_id=lane_id,
        data_root=data_root,
        path=path,
    )
    stream = _open_verified_stream(target)
    try:
        yield stream
    finally:
        try:
            stream.close()
        except OSError as exc:
            raise SuitePolicyError(
                f"opened payload stream could not be closed: {exc}"
            ) from exc


def build_suite_completeness_report(policy: Mapping, data_root: Path) -> dict:
    """Build a schema-ready report without reading any dataset payload."""

    _validated_family_map(policy)
    first_stage = policy["first_stage"]
    families = []
    for family, role, gradient, access, identity_path in _EXPECTED_FAMILY_MATRIX:
        report_item = {
            "family": family,
            "terminal_role": role,
            "gradient_eligibility": gradient,
            "payload_access_100k": access,
            **asdict(probe_family_presence(data_root, family)),
        }
        if identity_path is not None:
            report_item["identity_metadata_relative_path"] = identity_path
        families.append(report_item)
    return {
        "manifest_kind": "pneuma_foundation_suite_report",
        "manifest_schema_version": "0.1.0",
        "first_stage": {
            "stage": first_stage["stage"],
            "authorized_lane_candidates": list(
                first_stage["authorized_lane_candidates"]
            ),
        },
        "evaluation_identity": {
            "required_families": list(
                policy["evaluation_identity"]["required_families"]
            ),
            "blocked_unavailable_families": list(
                policy["evaluation_identity"]["blocked_unavailable_families"]
            ),
        },
        "families": families,
    }


__all__ = [
    "SuitePolicyError",
    "build_suite_completeness_report",
    "evaluation_identity_scope",
    "load_suite_policy",
    "open_authorized_payload",
    "validate_suite_policy",
]
