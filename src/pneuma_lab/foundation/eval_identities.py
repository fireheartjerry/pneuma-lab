"""Strict identity extraction and generated evaluation-index handling."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat as stat_module
from typing import BinaryIO

from pneuma_lab.foundation.artifacts import (
    ArtifactPublicationError,
    bind_artifact_publication,
    write_atomic_jsonl,
)


IDENTITY_FIELDS = (
    "repo",
    "issue_or_pr",
    "task_id",
    "base_commit",
    "patch_sha256",
    "test_patch_sha256",
    "fuzzy_text_sha256",
)
EVAL_METADATA_FIELDS = ("source_id", "repo", "base_commit")


def open_authorized_payload(*args, **kwargs):
    """Defer the suite import to avoid a data-policy import cycle."""

    from pneuma_lab.foundation.suite import open_authorized_payload as opener

    return opener(*args, **kwargs)


def _evaluation_identity_scope(
    policy: Mapping,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Load the exact scope lazily to avoid the suite/data import cycle."""

    from pneuma_lab.foundation.suite import (
        SuitePolicyError,
        evaluation_identity_scope,
    )

    try:
        return evaluation_identity_scope(policy)
    except SuitePolicyError as exc:
        raise ContaminationIndexError(
            f"suite evaluation identity policy is invalid: {exc}"
        ) from exc


class IdentityRecordError(ValueError):
    """Raised when a canonical foundation identity cannot be established."""


class ContaminationIndexError(ValueError):
    """Raised when an evaluation identity index is incomplete or malformed."""


@dataclass(frozen=True)
class IdentityRecord:
    family: str
    lane_id: str
    repo: str | None
    issue_or_pr: str | None
    task_id: str | None
    base_commit: str | None
    patch_sha256: str | None
    test_patch_sha256: str | None
    fuzzy_text_sha256: str | None

    def __post_init__(self) -> None:
        for field in ("family", "lane_id"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value:
                raise IdentityRecordError(f"{field} must be a nonempty string")
        for field in IDENTITY_FIELDS:
            value = getattr(self, field)
            if value is not None and not isinstance(value, str):
                raise IdentityRecordError(f"{field} must be a string or null")


def identity_from_foundation_record(record: Mapping) -> IdentityRecord:
    """Extract the nested source and identity containers without coercion."""

    if not isinstance(record, Mapping):
        raise IdentityRecordError("foundation record must be a mapping")
    source = record.get("source")
    identity = record.get("identity")
    if not isinstance(source, Mapping):
        raise IdentityRecordError("foundation record source must be a mapping")
    if not isinstance(identity, Mapping):
        raise IdentityRecordError("foundation record identity must be a mapping")
    if set(identity) != set(IDENTITY_FIELDS):
        raise IdentityRecordError(
            "foundation record identity has missing or unknown fields"
        )
    family = source.get("dataset_family")
    lane_id = source.get("lane_id")
    if not isinstance(family, str) or not family:
        raise IdentityRecordError("source.dataset_family must be a nonempty string")
    if not isinstance(lane_id, str) or not lane_id:
        raise IdentityRecordError("source.lane_id must be a nonempty string")
    values = {}
    for field in IDENTITY_FIELDS:
        value = identity[field]
        if value is not None and not isinstance(value, str):
            raise IdentityRecordError(f"identity.{field} must be a string or null")
        values[field] = value
    return IdentityRecord(family=family, lane_id=lane_id, **values)


def _validated_allowed_fields(allowed_fields: Iterable[str]) -> tuple[str, ...]:
    if isinstance(allowed_fields, (str, bytes)):
        raise ContaminationIndexError("allowed metadata fields must be an iterable")
    try:
        values = tuple(allowed_fields)
    except TypeError as exc:
        raise ContaminationIndexError(
            "allowed metadata fields must be an iterable"
        ) from exc
    if (
        len(values) != len(EVAL_METADATA_FIELDS)
        or not all(isinstance(value, str) for value in values)
        or set(values) != set(EVAL_METADATA_FIELDS)
    ):
        raise ContaminationIndexError(
            "allowed metadata fields must be exactly source_id, repo, base_commit"
        )
    return values


def _metadata_row(
    raw_line: bytes,
    *,
    line_number: int,
    allow_unretained_fields: bool = False,
) -> dict:
    if not raw_line.strip():
        raise ContaminationIndexError(
            f"evaluation identity index line {line_number} must not be blank"
        )

    def reject_duplicate_members(pairs):
        value = {}
        for name, member in pairs:
            if name in value:
                raise ContaminationIndexError(
                    "evaluation identity index line "
                    f"{line_number} has duplicate field: {name}"
                )
            value[name] = member
        return value

    def reject_constant(constant: str):
        raise ValueError(f"nonstandard JSON constant: {constant}")

    try:
        value = json.loads(
            raw_line,
            object_pairs_hook=reject_duplicate_members,
            parse_constant=reject_constant,
        )
    except ContaminationIndexError:
        raise
    except (
        json.JSONDecodeError,
        RecursionError,
        UnicodeError,
        ValueError,
    ) as exc:
        raise ContaminationIndexError(
            f"evaluation identity index line {line_number} must be valid JSON"
        ) from exc
    if not isinstance(value, dict):
        raise ContaminationIndexError(
            f"evaluation identity index line {line_number} must be an object"
        )
    fields = set(value)
    required_fields = set(EVAL_METADATA_FIELDS)
    if not required_fields.issubset(fields) or (
        not allow_unretained_fields and fields != required_fields
    ):
        raise ContaminationIndexError(
            f"evaluation identity index line {line_number} has missing or unknown fields"
        )
    source_id = value.get("source_id")
    if not isinstance(source_id, str) or not source_id.split():
        raise ContaminationIndexError(
            f"evaluation identity index line {line_number} source_id is invalid"
        )
    for field in ("repo", "base_commit"):
        field_value = value.get(field)
        if field_value is not None and not isinstance(field_value, str):
            raise ContaminationIndexError(
                f"evaluation identity index line {line_number} {field} is invalid"
            )
        if isinstance(field_value, str) and not field_value.split():
            raise ContaminationIndexError(
                f"evaluation identity index line {line_number} {field} is blank"
            )
    return {field: value[field] for field in EVAL_METADATA_FIELDS}


def _metadata_rows(
    stream: BinaryIO,
    *,
    allow_unretained_fields: bool = False,
) -> tuple[dict, ...]:
    rows = []
    source_ids: set[str] = set()
    for line_number, raw_line in enumerate(stream, start=1):
        if not isinstance(raw_line, bytes):
            raise ContaminationIndexError(
                "evaluation identity index must be read as binary JSONL"
            )
        row = _metadata_row(
            raw_line,
            line_number=line_number,
            allow_unretained_fields=allow_unretained_fields,
        )
        source_id = row["source_id"]
        if source_id in source_ids:
            raise ContaminationIndexError(
                f"duplicate evaluation source_id: {source_id}"
            )
        source_ids.add(source_id)
        rows.append(row)
    if not rows:
        raise ContaminationIndexError(
            "evaluation identity index must contain at least one record"
        )
    return tuple(rows)


def _issue_suffix(source_id: str) -> str | None:
    match = re.search(r"(?:^|[-_#/])([0-9]+)$", source_id)
    return match.group(1) if match is not None else None


def iter_eval_metadata_identities(
    path: Path,
    family: str,
    allowed_fields: Iterable[str],
) -> Iterator[IdentityRecord]:
    """Parse one generated/local identity index; never use for corpus paths."""

    _validated_allowed_fields(allowed_fields)
    if not isinstance(family, str) or not family:
        raise ContaminationIndexError("evaluation family must be a nonempty string")
    try:
        with Path(path).open("rb") as stream:
            rows = _metadata_rows(stream)
    except ContaminationIndexError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise ContaminationIndexError(
            f"evaluation identity index for {family} cannot be read: {exc}"
        ) from exc
    for row in rows:
        identity = IdentityRecord(
            family=family,
            lane_id=family,
            repo=row["repo"],
            issue_or_pr=_issue_suffix(row["source_id"]),
            task_id=row["source_id"],
            base_commit=row["base_commit"],
            patch_sha256=None,
            test_patch_sha256=None,
            fuzzy_text_sha256=None,
        )
        if not any(
            isinstance(getattr(identity, field), str)
            and bool(getattr(identity, field).split())
            for field in IDENTITY_FIELDS
        ):
            raise ContaminationIndexError(
                f"evaluation identity index for {family} has no usable identity"
            )
        yield identity


def load_required_eval_identities(
    indexes: Mapping[str, Path],
    *,
    suite_policy: Mapping,
) -> tuple[IdentityRecord, ...]:
    """Load every policy-required evaluation index in policy order."""

    if not isinstance(indexes, Mapping):
        raise ContaminationIndexError("evaluation identity indexes must be a mapping")
    required, _blocked = _evaluation_identity_scope(suite_policy)
    provided = set(indexes)
    missing = [family for family in required if family not in provided]
    extra = sorted(provided - set(required), key=str)
    if missing:
        raise ContaminationIndexError(
            "missing required evaluation identity index: " + ", ".join(missing)
        )
    if extra:
        raise ContaminationIndexError(
            "unexpected evaluation identity index: " + ", ".join(map(str, extra))
        )
    paths: set[str] = set()
    file_identities: set[tuple[int, int]] = set()
    result = []
    for family in required:
        try:
            path = Path(indexes[family])
            resolved = path.resolve(strict=True)
            identity = os.path.normcase(os.path.normpath(os.fspath(resolved)))
            metadata = resolved.stat()
        except (TypeError, ValueError, OSError) as exc:
            raise ContaminationIndexError(
                f"evaluation identity index path for {family} cannot be inspected"
            ) from exc
        file_identity = (metadata.st_dev, metadata.st_ino)
        if identity in paths or file_identity in file_identities:
            raise ContaminationIndexError("evaluation identity index paths are duplicated")
        paths.add(identity)
        file_identities.add(file_identity)
        result.extend(
            iter_eval_metadata_identities(path, family, EVAL_METADATA_FIELDS)
        )
    return tuple(result)


def _policy_source_path(policy: Mapping, family: str) -> str:
    if not isinstance(policy, Mapping):
        raise ContaminationIndexError("suite policy must be a mapping")
    entries = policy.get("families")
    if not isinstance(entries, list):
        raise ContaminationIndexError("suite policy families must be a list")
    matches = [
        item
        for item in entries
        if isinstance(item, Mapping) and item.get("family") == family
    ]
    if len(matches) != 1:
        raise ContaminationIndexError(
            f"suite policy must define {family} exactly once"
        )
    relative = matches[0].get("identity_metadata_relative_path")
    if not isinstance(relative, str) or not relative:
        raise ContaminationIndexError(
            f"suite policy has no identity metadata path for {family}"
        )
    return relative


def _absolute_path(value: Path, *, label: str) -> Path:
    try:
        raw_path = os.fspath(value)
        if not isinstance(raw_path, str) or not raw_path:
            raise ValueError("path must be a nonempty string")
        return Path(os.path.abspath(raw_path))
    except (OSError, TypeError, ValueError) as exc:
        raise ContaminationIndexError(
            f"evaluation identity index {label} path is invalid"
        ) from exc


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_generated_output_path(
    repo_root: Path,
    data_root: Path,
    output_path: Path,
) -> Path:
    repo = _absolute_path(repo_root, label="repository root")
    data = _absolute_path(data_root, label="protected data root")
    output = _absolute_path(output_path, label="output")
    build = repo / "build"
    try:
        resolved_repo = repo.resolve(strict=False)
        resolved_data = data.resolve(strict=False)
        resolved_build = build.resolve(strict=False)
        resolved_output = output.resolve(strict=False)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ContaminationIndexError(
            "evaluation identity index output path cannot be resolved"
        ) from exc
    if _is_within(resolved_output, resolved_data):
        raise ContaminationIndexError(
            "evaluation identity index output must remain outside the protected data root"
        )
    try:
        relative_output = output.relative_to(build)
    except ValueError as exc:
        raise ContaminationIndexError(
            "evaluation identity index output must remain under repository build storage"
        ) from exc
    if not relative_output.parts:
        raise ContaminationIndexError(
            "evaluation identity index output must be strictly below the repository build root"
        )

    components = [repo, build]
    current = build
    for part in relative_output.parts:
        current /= part
        components.append(current)
    for component in components:
        try:
            metadata = component.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise ContaminationIndexError(
                "evaluation identity index output metadata cannot be inspected"
            ) from exc
        is_junction = getattr(component, "is_junction", None)
        try:
            junction = bool(callable(is_junction) and is_junction())
        except OSError as exc:
            raise ContaminationIndexError(
                "evaluation identity index output junction cannot be inspected"
            ) from exc
        reparse_flag = getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        if (
            stat_module.S_ISLNK(metadata.st_mode)
            or junction
            or bool(getattr(metadata, "st_file_attributes", 0) & reparse_flag)
        ):
            raise ContaminationIndexError(
                "evaluation identity index output path contains a link or reparse point"
            )
        if component != output and not stat_module.S_ISDIR(metadata.st_mode):
            raise ContaminationIndexError(
                "evaluation identity index output ancestor must be a directory"
            )
        if component == output and not stat_module.S_ISREG(metadata.st_mode):
            raise ContaminationIndexError(
                "evaluation identity index output must be a regular file path"
            )

    if (
        not _is_within(resolved_build, resolved_repo)
        or not _is_within(resolved_output, resolved_build)
        or resolved_output == resolved_build
    ):
        raise ContaminationIndexError(
            "evaluation identity index output resolves outside repository build storage"
        )
    return output


def build_eval_identity_index(
    policy: Mapping,
    *,
    stage: str = "100k",
    family: str,
    repo_root: Path,
    data_root: Path,
    source_path: Path,
    output_path: Path,
    allowed_fields: Iterable[str],
) -> dict:
    """Build a minimized index exclusively from one authorized verified stream."""

    _validated_allowed_fields(allowed_fields)
    if not isinstance(family, str) or not family:
        raise ContaminationIndexError("evaluation family must be a nonempty string")
    relative_source = _policy_source_path(policy, family)
    output_path = _validate_generated_output_path(
        repo_root,
        data_root,
        output_path,
    )
    try:
        with open_authorized_payload(
            policy,
            stage=stage,
            family=family,
            lane_id=None,
            data_root=data_root,
            path=source_path,
        ) as stream:
            rows = _metadata_rows(stream, allow_unretained_fields=True)
    except ContaminationIndexError:
        raise
    rows = tuple(
        sorted(
            rows,
            key=lambda row: (
                row["source_id"],
                row["repo"] or "",
                row["base_commit"] or "",
            ),
        )
    )
    try:
        with bind_artifact_publication(
            output_path.parent,
            anchor_root=Path(repo_root),
            allowed_root=Path(repo_root) / "build",
            forbidden_roots=(Path(data_root),),
        ) as publication:
            write_atomic_jsonl(
                output_path,
                rows,
                publication=publication,
            )
            output_sha256 = publication.sha256(output_path)
    except ArtifactPublicationError as exc:
        raise ContaminationIndexError(
            f"evaluation identity index output publication failed: {exc}"
        ) from exc
    return {
        "manifest_kind": "pneuma_eval_identity_index_receipt",
        "manifest_schema_version": "0.1.0",
        "family": family,
        "source_relative_path": relative_source,
        "output_artifact": Path(output_path).name,
        "output_sha256": output_sha256,
        "identity_count": len(rows),
        "retained_fields": list(EVAL_METADATA_FIELDS),
    }


__all__ = [
    "EVAL_METADATA_FIELDS",
    "IDENTITY_FIELDS",
    "ContaminationIndexError",
    "IdentityRecord",
    "IdentityRecordError",
    "build_eval_identity_index",
    "identity_from_foundation_record",
    "iter_eval_metadata_identities",
    "load_required_eval_identities",
]
