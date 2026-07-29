"""Deterministic, closed imports for resampling-null authority assets."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import cast
import unicodedata

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import (
    RecordValidationError,
    _load_json_bytes,
    _plain_json,
    _resolve_inside,
)
from .types import ArtifactRef


@dataclass(frozen=True, slots=True)
class ClosedJsonImport:
    """One purpose-bound deterministic import grammar."""

    record_kind: str
    fields: frozenset[str]
    exact_integer_fields: frozenset[str] = frozenset()
    semantic_set_fields: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if type(self.record_kind) is not str or not self.record_kind:
            raise ValueError("record_kind must be one non-empty exact string")
        if "record_kind" not in self.fields:
            raise ValueError("closed import fields must include record_kind")
        if not self.exact_integer_fields <= self.fields:
            raise ValueError("exact integer fields must belong to the closed grammar")
        if not self.semantic_set_fields <= self.fields:
            raise ValueError("semantic-set fields must belong to the closed grammar")


class ConfirmationPreflightUnavailable(RecordValidationError):
    """Raised while no reviewed live ceremony adapter is installed."""


class ConfirmationRosterCeremonyCapability:
    """Opaque live-only ceremony capability; no core mint path exists."""

    __slots__ = ()

    def __new__(cls) -> ConfirmationRosterCeremonyCapability:
        raise TypeError(
            "ceremony capabilities have no public constructor; "
            "the reviewed live adapter is unavailable"
        )

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("ceremony capabilities cannot be subclassed")

    @property
    def source_sha256s(self) -> tuple[str, str, str, str, str, str, str]:
        raise ConfirmationPreflightUnavailable(
            "no registered live ceremony capability exists"
        )


class ConfirmationPreflightRegistry:
    """Fail-closed core placeholder for the separately reviewed live adapter."""

    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("the core preflight registry cannot be subclassed")

    def claim_roster_ceremony(
        self,
        *,
        qualification_universe_source: Path,
        selection_program_source: Path,
        precommit_source: Path,
        anchor_source: Path,
        reveal_source: Path,
        eligibility_source: Path,
        ceremony_policy_source: Path,
        study_id: str,
    ) -> ConfirmationRosterCeremonyCapability:
        del (
            qualification_universe_source,
            selection_program_source,
            precommit_source,
            anchor_source,
            reveal_source,
            eligibility_source,
            ceremony_policy_source,
            study_id,
        )
        raise ConfirmationPreflightUnavailable(
            "eligible confirmation is unavailable: no reviewed official "
            "Sigstore/drand/Node live adapter is installed"
        )


def _lower_hex(value: object, *, field: str, byte_count: int) -> bytes:
    if type(value) is not str:
        raise RecordValidationError(f"{field} must be exact lowercase hex text")
    text = cast(str, value)
    if len(text) != byte_count * 2 or any(
        character not in "0123456789abcdef" for character in text
    ):
        raise RecordValidationError(
            f"{field} must encode exactly {byte_count} bytes as lowercase hex"
        )
    return bytes.fromhex(text)


def verify_ed25519_canonical_json(
    value: Mapping[str, object],
    *,
    public_key_ed25519_hex: str,
    signature_ed25519_hex: str,
    signature_field: str | None = None,
) -> str:
    """Verify Ed25519 over exact compact canonical JSON and return its digest."""

    if not isinstance(value, Mapping):
        raise RecordValidationError("signed value must be a mapping")
    plain = _plain_json(value)
    if not isinstance(plain, dict):
        raise RecordValidationError("signed value must be a plain JSON object")
    if signature_field is not None:
        if type(signature_field) is not str or not signature_field:
            raise RecordValidationError("signature_field must be non-empty text")
        if plain.get(signature_field) != signature_ed25519_hex:
            raise RecordValidationError(
                "embedded signature differs from verification signature"
            )
        del plain[signature_field]
    _require_canonical_text(plain)
    payload = canonical_json_bytes(plain, indent=None)
    public_key = _lower_hex(
        public_key_ed25519_hex,
        field="public_key_ed25519_hex",
        byte_count=32,
    )
    signature = _lower_hex(
        signature_ed25519_hex,
        field="signature_ed25519_hex",
        byte_count=64,
    )
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, payload)
    except (InvalidSignature, ValueError) as exc:
        raise RecordValidationError("Ed25519 signature verification failed") from exc
    return hashlib.sha256(payload).hexdigest()


def _require_canonical_text(value: object, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _require_canonical_text(key, path=f"{path}.<key>")
            _require_canonical_text(nested, path=f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _require_canonical_text(nested, path=f"{path}[{index}]")
        return
    if not isinstance(value, str):
        return
    if unicodedata.normalize("NFC", value) != value:
        raise RecordValidationError(f"{path}: text must already be NFC-normalized")
    forbidden = next(
        (
            character
            for character in value
            if unicodedata.category(character).startswith("C")
        ),
        None,
    )
    if forbidden is not None:
        raise RecordValidationError(f"{path}: text contains a forbidden code point")


def _normalize_semantic_set(value: object, *, field: str) -> list[object]:
    if not isinstance(value, list):
        raise RecordValidationError(f"{field} must be an array")
    keyed: list[tuple[bytes, object]] = []
    observed: set[bytes] = set()
    for item in value:
        canonical = canonical_json_bytes(item, indent=None)
        if canonical in observed:
            raise RecordValidationError(f"{field} must not contain duplicates")
        observed.add(canonical)
        keyed.append((canonical, item))
    return [item for _canonical, item in sorted(keyed, key=lambda pair: pair[0])]


def _publish_cas(target: Path, payload: bytes) -> None:
    """Install once without replacing an existing pathname."""

    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    directory_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    directory_descriptor = os.open(target.parent, directory_flags)
    directory_metadata = os.fstat(directory_descriptor)
    try:
        rebound_directory = target.parent.stat()
    except BaseException:
        os.close(directory_descriptor)
        raise
    if (rebound_directory.st_dev, rebound_directory.st_ino) != (
        directory_metadata.st_dev,
        directory_metadata.st_ino,
    ):
        os.close(directory_descriptor)
        raise RecordValidationError("import destination directory changed")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(
            target.name,
            flags,
            0o644,
            dir_fd=directory_descriptor,
        )
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            os.close(directory_descriptor)
            raise
        read_flags = os.O_RDONLY
        read_flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        try:
            descriptor = os.open(
                target.name,
                read_flags,
                dir_fd=directory_descriptor,
            )
        except OSError as read_exc:
            os.close(directory_descriptor)
            raise RecordValidationError(
                "cannot bind existing digest-derived import"
            ) from read_exc
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or getattr(metadata, "st_nlink", 1) != 1
            ):
                raise RecordValidationError(
                    "existing digest-derived import is not one regular file"
                )
            observed = bytearray()
            while chunk := os.read(descriptor, 1024 * 1024):
                observed.extend(chunk)
            if bytes(observed) != payload:
                raise RecordValidationError(
                    "digest-derived import path contains other bytes"
                )
            rebound = os.stat(
                target.name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            if (rebound.st_dev, rebound.st_ino) != (
                metadata.st_dev,
                metadata.st_ino,
            ):
                raise RecordValidationError(
                    "digest-derived import pathname changed while reading"
                )
            rebound_directory = target.parent.stat()
            if (rebound_directory.st_dev, rebound_directory.st_ino) != (
                directory_metadata.st_dev,
                directory_metadata.st_ino,
            ):
                raise RecordValidationError("import destination directory changed")
        finally:
            os.close(descriptor)
            os.close(directory_descriptor)
        return

    try:
        view = memoryview(payload)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        rebound = os.stat(
            target.name,
            dir_fd=directory_descriptor,
            follow_symlinks=False,
        )
        if (rebound.st_dev, rebound.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise RecordValidationError(
                "digest-derived import pathname changed while publishing"
            )
        rebound_directory = target.parent.stat()
        if (rebound_directory.st_dev, rebound_directory.st_ino) != (
            directory_metadata.st_dev,
            directory_metadata.st_ino,
        ):
            raise RecordValidationError("import destination directory changed")
        os.fsync(directory_descriptor)
    except BaseException:
        try:
            rebound = os.stat(
                target.name,
                dir_fd=directory_descriptor,
                follow_symlinks=False,
            )
            metadata = os.fstat(descriptor)
            if (rebound.st_dev, rebound.st_ino) == (
                metadata.st_dev,
                metadata.st_ino,
            ):
                os.unlink(target.name, dir_fd=directory_descriptor)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)
        os.close(directory_descriptor)


def _publish_closed_value(
    decoded: object,
    *,
    grammar: ClosedJsonImport,
    run_root: Path,
    destination_template: str,
    role: str,
) -> ArtifactRef:
    if destination_template.count("{sha256}") > 1:
        raise ValueError("destination_template contains repeated {sha256}")
    if not isinstance(decoded, Mapping):
        raise RecordValidationError("closed import must be one JSON object")
    value = dict(cast(Mapping[str, object], decoded))
    observed_fields = frozenset(value)
    if observed_fields != grammar.fields:
        missing = sorted(grammar.fields - observed_fields)
        unknown = sorted(observed_fields - grammar.fields)
        raise RecordValidationError(
            f"closed import fields differ: missing={missing}, unknown={unknown}"
        )
    if value["record_kind"] != grammar.record_kind:
        raise RecordValidationError(
            f"record_kind must equal {grammar.record_kind!r}"
        )
    for field in grammar.exact_integer_fields:
        if type(value[field]) is not int:
            raise RecordValidationError(f"{field} must be an exact integer")
    _require_canonical_text(value)
    for field in grammar.semantic_set_fields:
        value[field] = _normalize_semantic_set(value[field], field=field)

    payload = canonical_json_bytes(value, indent=2)
    digest = hashlib.sha256(payload).hexdigest()
    try:
        relative_path = destination_template.format(sha256=digest)
    except (IndexError, KeyError, ValueError) as exc:
        raise ValueError("destination_template contains another format field") from exc
    if PurePosixPath(relative_path).as_posix() != relative_path:
        raise RecordValidationError("destination path must be canonical POSIX text")
    target, rebound = _resolve_inside(
        Path(relative_path),
        run_root,
        require_exists=False,
    )
    if rebound != relative_path:
        raise RecordValidationError("destination path changed during resolution")
    target.parent.mkdir(parents=True, exist_ok=True)
    rebound_target, rebound_relative = _resolve_inside(
        target,
        run_root,
        require_exists=False,
    )
    if rebound_target != target or rebound_relative != relative_path:
        raise RecordValidationError("destination ancestry changed before import")
    _publish_cas(target, payload)
    return ArtifactRef(
        role=role,
        relative_path=relative_path,
        sha256=digest,
        byte_count=len(payload),
        media_type="application/json",
    )


def import_closed_json(
    source: Path,
    *,
    grammar: ClosedJsonImport,
    run_root: Path,
    destination_template: str,
    role: str,
) -> ArtifactRef:
    """Validate and copy one closed JSON object to a deterministic path.

    ``destination_template`` may be fixed or contain one ``{sha256}`` token.
    A byte-identical existing object is accepted; every mismatch fails closed.
    """

    try:
        source_bytes = Path(source).read_bytes()
    except OSError as exc:
        raise RecordValidationError(f"cannot read import source {source}: {exc}") from exc
    decoded = _load_json_bytes(source_bytes, source=Path(source))
    return _publish_closed_value(
        decoded,
        grammar=grammar,
        run_root=run_root,
        destination_template=destination_template,
        role=role,
    )


def require_declared_fields(
    fields: Collection[str],
    *,
    required: Collection[str],
) -> None:
    """Reject programmatic grammars that silently omit required authority."""

    if frozenset(fields) != frozenset(required):
        raise ValueError("declared import grammar differs from required authority")


_GROUP_ORDER = {"language": 0, "domain": 1, "issue_family": 2}
TASK_REGISTRY_GRAMMAR = ClosedJsonImport(
    record_kind="resampling_task_registry_v1",
    fields=frozenset({"record_kind", "schema_version", "tasks"}),
)
ASSIGNMENT_PROGRAM_GRAMMAR = ClosedJsonImport(
    record_kind="resampling_assignment_program_v1",
    fields=frozenset(
        {
            "record_kind",
            "schema_version",
            "assignment_mode",
            "matching_algorithm",
            "finding_count_band_upper_bounds",
            "report_length_band_upper_bounds",
            "verifier_normalizer_contract",
            "assignment_runtime_contract",
            "backend_receipt_ref",
            "stratum_keys",
        }
    ),
)


def _closed_mapping(
    value: object,
    *,
    fields: Collection[str],
    path: str,
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{path} must be an object")
    result = dict(cast(Mapping[str, object], value))
    observed = frozenset(result)
    expected = frozenset(fields)
    if observed != expected:
        raise RecordValidationError(
            f"{path} fields differ: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return result


def _strict_text(value: object, *, path: str) -> str:
    if type(value) is not str or not value:
        raise RecordValidationError(f"{path} must be non-empty exact text")
    _require_canonical_text(value, path=path)
    return cast(str, value)


def _nonnegative_int(value: object, *, path: str) -> int:
    if type(value) is not int or cast(int, value) < 0:
        raise RecordValidationError(f"{path} must be an exact non-negative integer")
    return cast(int, value)


def _sha256(value: object, *, path: str) -> str:
    text = _strict_text(value, path=path)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise RecordValidationError(f"{path} must be lowercase SHA-256")
    return text


def _artifact_ref_value(value: object, *, path: str) -> ArtifactRef:
    mapping = _closed_mapping(
        value,
        fields={"role", "relative_path", "sha256", "byte_count", "media_type"},
        path=path,
    )
    try:
        return ArtifactRef(
            role=cast(str, mapping["role"]),
            relative_path=cast(str, mapping["relative_path"]),
            sha256=cast(str, mapping["sha256"]),
            byte_count=cast(int, mapping["byte_count"]),
            media_type=cast(str, mapping["media_type"]),
        )
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"{path} is malformed: {exc}") from exc


def _validate_task_registry(value: dict[str, object]) -> None:
    if value["schema_version"] != "1":
        raise RecordValidationError("task registry schema_version must equal '1'")
    tasks = value["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise RecordValidationError("task registry tasks must be a non-empty array")
    normalized_tasks: list[
        tuple[tuple[bytes, bytes, bytes, bytes], dict[str, object]]
    ] = []
    task_ids: set[str] = set()
    for index, item in enumerate(tasks):
        task = _closed_mapping(
            item,
            fields={"task_id", "benchmark", "stratum", "lineage", "groups"},
            path=f"tasks[{index}]",
        )
        texts = {
            field: _strict_text(task[field], path=f"tasks[{index}].{field}")
            for field in ("task_id", "benchmark", "stratum", "lineage")
        }
        if texts["task_id"] in task_ids:
            raise RecordValidationError("task registry task_id values must be unique")
        task_ids.add(texts["task_id"])
        groups = task["groups"]
        if not isinstance(groups, list) or not groups:
            raise RecordValidationError(f"tasks[{index}].groups must be non-empty")
        normalized_groups: list[tuple[tuple[int, bytes], dict[str, object]]] = []
        group_kinds: set[str] = set()
        for group_index, group_value in enumerate(groups):
            group = _closed_mapping(
                group_value,
                fields={"kind", "value"},
                path=f"tasks[{index}].groups[{group_index}]",
            )
            kind = _strict_text(
                group["kind"],
                path=f"tasks[{index}].groups[{group_index}].kind",
            )
            label = _strict_text(
                group["value"],
                path=f"tasks[{index}].groups[{group_index}].value",
            )
            if kind not in _GROUP_ORDER or kind in group_kinds:
                raise RecordValidationError(
                    f"tasks[{index}].groups has invalid or repeated kind"
                )
            group_kinds.add(kind)
            normalized_groups.append(
                ((_GROUP_ORDER[kind], label.encode("utf-8")), group)
            )
        task["groups"] = [
            group for _key, group in sorted(normalized_groups, key=lambda row: row[0])
        ]
        normalized_tasks.append(
            (
                (
                texts["benchmark"].encode("utf-8"),
                texts["stratum"].encode("utf-8"),
                texts["lineage"].encode("utf-8"),
                texts["task_id"].encode("utf-8"),
                ),
                task,
            )
        )
    value["tasks"] = [
        task for _key, task in sorted(normalized_tasks, key=lambda row: row[0])
    ]


def import_task_registry(
    source: Path,
    *,
    run_root: Path,
    destination: str = "inputs/task-registry.json",
) -> ArtifactRef:
    """Import the concrete closed task-registry authority."""

    try:
        source_bytes = Path(source).read_bytes()
    except OSError as exc:
        raise RecordValidationError(f"cannot read task registry {source}: {exc}") from exc
    decoded = _load_json_bytes(source_bytes, source=Path(source))
    value = _closed_mapping(
        decoded,
        fields=TASK_REGISTRY_GRAMMAR.fields,
        path="$",
    )
    if value.get("record_kind") != TASK_REGISTRY_GRAMMAR.record_kind:
        raise RecordValidationError("wrong task-registry record_kind")
    _require_canonical_text(value)
    _validate_task_registry(value)
    return _publish_closed_value(
        value,
        grammar=TASK_REGISTRY_GRAMMAR,
        run_root=run_root,
        destination_template=destination,
        role="task_registry",
    )


def _strict_cutpoints(value: object, *, path: str) -> None:
    if not isinstance(value, list):
        raise RecordValidationError(f"{path} must be an array")
    points = [
        _nonnegative_int(item, path=f"{path}[{index}]")
        for index, item in enumerate(value)
    ]
    if points != sorted(set(points)):
        raise RecordValidationError(f"{path} must be strictly increasing")


def _validate_assignment_program(value: dict[str, object]) -> None:
    if value["schema_version"] != "1":
        raise RecordValidationError("assignment program schema_version must equal '1'")
    mode = value["assignment_mode"]
    algorithm = value["matching_algorithm"]
    if (mode, algorithm) not in {
        ("synthetic_derangement", "synthetic_cyclic_offset_v1"),
        ("confirmation_lineage_matching", "exact_constrained_min_cost_v1"),
    }:
        raise RecordValidationError("assignment mode/algorithm pair is not closed")
    _strict_cutpoints(
        value["finding_count_band_upper_bounds"],
        path="finding_count_band_upper_bounds",
    )
    _strict_cutpoints(
        value["report_length_band_upper_bounds"],
        path="report_length_band_upper_bounds",
    )
    normalizer = _closed_mapping(
        value["verifier_normalizer_contract"],
        fields={
            "contract_id",
            "normalizer_source_ref",
            "normalizer_source_sha256",
            "report_tokenizer_sha256",
            "benchmark_component_kinds",
        },
        path="verifier_normalizer_contract",
    )
    if normalizer["contract_id"] != "assignment-verifier-normalizer-v1":
        raise RecordValidationError("wrong verifier normalizer contract_id")
    source_ref = _artifact_ref_value(
        normalizer["normalizer_source_ref"],
        path="verifier_normalizer_contract.normalizer_source_ref",
    )
    if _sha256(
        normalizer["normalizer_source_sha256"],
        path="verifier_normalizer_contract.normalizer_source_sha256",
    ) != source_ref.sha256:
        raise RecordValidationError("normalizer source digest is inconsistent")
    _sha256(
        normalizer["report_tokenizer_sha256"],
        path="verifier_normalizer_contract.report_tokenizer_sha256",
    )
    if normalizer["benchmark_component_kinds"] != {
        "SWE": ["check_runner", "failure_class"],
        "TAU": ["evaluator_component"],
    }:
        raise RecordValidationError("benchmark component kinds are incomplete")
    runtime = _closed_mapping(
        value["assignment_runtime_contract"],
        fields={"implementation", "python_version", "unicodedata_unidata_version"},
        path="assignment_runtime_contract",
    )
    if runtime["implementation"] != "CPython":
        raise RecordValidationError("assignment runtime must be CPython")
    _strict_text(runtime["python_version"], path="assignment_runtime_contract.python_version")
    _strict_text(
        runtime["unicodedata_unidata_version"],
        path="assignment_runtime_contract.unicodedata_unidata_version",
    )
    backend = value["backend_receipt_ref"]
    if mode == "synthetic_derangement":
        if backend is not None:
            raise RecordValidationError("synthetic assignment backend ref must be null")
    else:
        _artifact_ref_value(backend, path="backend_receipt_ref")
    stratum_keys = value["stratum_keys"]
    if not isinstance(stratum_keys, list) or not stratum_keys:
        raise RecordValidationError("stratum_keys must be a non-empty ordered array")
    for index, key in enumerate(stratum_keys):
        _strict_text(key, path=f"stratum_keys[{index}]")
    if len(stratum_keys) != len(set(cast(list[str], stratum_keys))):
        raise RecordValidationError("stratum_keys must be unique")


def import_assignment_program(
    source: Path,
    *,
    run_root: Path,
    destination: str = "inputs/assignment-program.json",
) -> ArtifactRef:
    """Import the concrete non-executable assignment-program authority."""

    if Path(source).suffix.lower() != ".json":
        raise RecordValidationError("assignment program source must be JSON")
    try:
        source_bytes = Path(source).read_bytes()
    except OSError as exc:
        raise RecordValidationError(
            f"cannot read assignment program {source}: {exc}"
        ) from exc
    decoded = _load_json_bytes(source_bytes, source=Path(source))
    value = _closed_mapping(
        decoded,
        fields=ASSIGNMENT_PROGRAM_GRAMMAR.fields,
        path="$",
    )
    if value.get("record_kind") != ASSIGNMENT_PROGRAM_GRAMMAR.record_kind:
        raise RecordValidationError("wrong assignment-program record_kind")
    _require_canonical_text(value)
    _validate_assignment_program(value)
    return _publish_closed_value(
        value,
        grammar=ASSIGNMENT_PROGRAM_GRAMMAR,
        run_root=run_root,
        destination_template=destination,
        role="assignment_program",
    )


__all__ = [
    "ClosedJsonImport",
    "ConfirmationPreflightRegistry",
    "ConfirmationPreflightUnavailable",
    "ConfirmationRosterCeremonyCapability",
    "import_assignment_program",
    "import_closed_json",
    "import_task_registry",
    "require_declared_fields",
    "verify_ed25519_canonical_json",
]
