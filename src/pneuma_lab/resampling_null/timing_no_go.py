"""Fail-closed Task-8 timing lower-bound no-go representation.

This module is deliberately outside the power-report graph.  It never returns
an ArtifactRef, never emits a power stage, and cannot authorize descendants.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import asdict, dataclass
import fcntl
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
from typing import cast

from jsonschema import Draft202012Validator

from pneuma_lab.foundation.artifacts import canonical_json_bytes
from pneuma_lab.schemas import load_schema

from .authority_refs import decode_artifact_ref, load_json_bytes
from .errors import RecordValidationError
from .types import ArtifactRef


_RECORD_PATH = PurePosixPath("timing-admission/task8-timing-no-go.json")
_FORMULA = (
    "ceil(elapsed_lower_bound_seconds * production_datasets_per_cell / "
    "screen_datasets_per_cell)"
)
_CELL_COUNT = 2916
_SHARD_COUNT = 64
_SCREEN_DATASETS_PER_CELL = 200
_PRODUCTION_DATASETS_PER_CELL = 20000
_MULTIPLIER = 100
_MAX_PROJECTED_WALL_SECONDS = 43200
_ADMISSIBLE_PROBE_THRESHOLD_SECONDS = 432
_HASH_CHUNK_BYTES = 1024 * 1024
_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_WRITE_FLAGS = (
    os.O_WRONLY
    | os.O_CREAT
    | os.O_EXCL
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_REF_ROLES = {
    "study_manifest_ref": "study_manifest",
    "power_authority_ref": "power_authority",
    "power_grid_ref": "power_grid",
    "power_screen_topology_ref": "power_screen_topology",
    "termination_evidence_ref": "timing_termination_evidence",
}
_REF_MEDIA_TYPES = {
    "study_manifest_ref": "application/json",
    "power_authority_ref": "application/vnd.pneuma.power-authority+json",
    "power_grid_ref": "application/json",
    "power_screen_topology_ref": "application/json",
    "termination_evidence_ref": "application/json",
}
_CLAIM_FIELDS = (
    "completed_screen",
    "p0_attempt",
    "p0_final",
    "scientific_result",
    "task_8_scientifically_complete",
    "task_10_complete",
)
@dataclass(frozen=True, slots=True)
class TimingNoGoBindings:
    """Exact immutable inputs to one Task-8 timing no-go representation."""

    study_manifest_ref: ArtifactRef
    power_authority_ref: ArtifactRef
    power_grid_ref: ArtifactRef
    power_screen_topology_ref: ArtifactRef
    termination_evidence_ref: ArtifactRef
    run_root_identity_sha256: str
    host_identity_sha256: str

    def __post_init__(self) -> None:
        for field, role in _REF_ROLES.items():
            ref = getattr(self, field)
            if type(ref) is not ArtifactRef:
                raise TypeError(f"{field} must be an exact ArtifactRef")
            if ref.role != role:
                raise ValueError(f"{field} role must equal {role!r}")
            if ref.media_type != _REF_MEDIA_TYPES[field]:
                raise RecordValidationError(
                    f"{field} media type must equal {_REF_MEDIA_TYPES[field]!r}"
                )
        _require_sha256(
            self.run_root_identity_sha256, field="run_root_identity_sha256"
        )
        _require_sha256(self.host_identity_sha256, field="host_identity_sha256")


def _require_sha256(value: object, *, field: str) -> str:
    if (
        type(value) is not str
        or len(cast(str, value)) != 64
        or any(character not in "0123456789abcdef" for character in cast(str, value))
    ):
        raise RecordValidationError(f"{field} must be a lowercase SHA-256")
    return cast(str, value)


def _root(run_root: Path) -> Path:
    root = Path(run_root).resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    return root


def _run_root_identity(root: Path) -> str:
    metadata = os.stat(root, follow_symlinks=False)
    identity = {
        "contract_id": "local-run-root-identity-v1",
        "normalized_path": str(root),
        "st_dev": metadata.st_dev,
        "st_ino": metadata.st_ino,
    }
    return hashlib.sha256(canonical_json_bytes(identity, indent=None)).hexdigest()


def _current_host_identity_sha256() -> str:
    """Bind the record to the machine that can read its stable local identity."""

    try:
        machine_id = Path("/etc/machine-id").read_text(encoding="ascii").strip()
    except OSError as exc:
        raise RecordValidationError("current host identity is unavailable") from exc
    if not machine_id:
        raise RecordValidationError("current host identity is empty")
    identity = {
        "contract_id": "local-host-identity-v1",
        "machine_id_sha256": hashlib.sha256(machine_id.encode("ascii")).hexdigest(),
        "machine_architecture": os.uname().machine,
    }
    return hashlib.sha256(canonical_json_bytes(identity, indent=None)).hexdigest()


def _read_confined(root: Path, relative_path: str) -> bytes:
    path = PurePosixPath(relative_path)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in ("", ".", "..") for part in path.parts)
        or path.as_posix() != relative_path
    ):
        raise RecordValidationError("binding path is not normalized below run_root")
    descriptors: list[int] = []
    file_descriptor: int | None = None
    root_descriptor = os.open(root, _DIRECTORY_FLAGS)
    descriptors.append(root_descriptor)
    parent = root_descriptor
    try:
        for component in path.parts[:-1]:
            child = os.open(component, _DIRECTORY_FLAGS, dir_fd=parent)
            descriptors.append(child)
            parent = child
        file_descriptor = os.open(path.parts[-1], _READ_FLAGS, dir_fd=parent)
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise RecordValidationError("binding must identify a regular file")
        chunks: list[bytes] = []
        while chunk := os.read(file_descriptor, _HASH_CHUNK_BYTES):
            chunks.append(chunk)
        after = os.fstat(file_descriptor)
        named = os.stat(path.parts[-1], dir_fd=parent, follow_symlinks=False)
        identity = (before.st_dev, before.st_ino)
        if (
            identity != (after.st_dev, after.st_ino)
            or identity != (named.st_dev, named.st_ino)
            or not stat.S_ISREG(after.st_mode)
            or not stat.S_ISREG(named.st_mode)
        ):
            raise RecordValidationError("binding identity changed during read")
        return b"".join(chunks)
    except OSError as exc:
        raise RecordValidationError("binding is missing or cannot be read safely") from exc
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        while descriptors:
            os.close(descriptors.pop())


def _read_ref(root: Path, ref: ArtifactRef, *, field: str) -> tuple[bytes, object]:
    payload = _read_confined(root, ref.relative_path)
    if (
        len(payload) != ref.byte_count
        or hashlib.sha256(payload).hexdigest() != ref.sha256
    ):
        raise RecordValidationError(f"{field} digest binding differs")
    value = load_json_bytes(payload, source=root / ref.relative_path)
    return payload, value


def _mapping(value: object, *, field: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must be an object")
    return dict(value)


def _decode_bindings(value: object) -> TimingNoGoBindings:
    mapping = _mapping(value, field="bindings")
    if set(mapping) != set(_REF_ROLES) | {
        "run_root_identity_sha256",
        "host_identity_sha256",
    }:
        raise RecordValidationError("bindings has an open or incomplete shape")
    refs = {
        field: decode_artifact_ref(mapping[field], field=field, expected_role=role)
        for field, role in _REF_ROLES.items()
    }
    try:
        return TimingNoGoBindings(
            **refs,
            run_root_identity_sha256=cast(str, mapping["run_root_identity_sha256"]),
            host_identity_sha256=cast(str, mapping["host_identity_sha256"]),
        )
    except (TypeError, ValueError) as exc:
        raise RecordValidationError(f"binding is malformed: {exc}") from exc


def _validate_artifact_graph(
    bindings: TimingNoGoBindings, *, root: Path
) -> dict[str, object]:
    if bindings.run_root_identity_sha256 != _run_root_identity(root):
        raise RecordValidationError("run-root identity binding differs")
    _, grid_value = _read_ref(root, bindings.power_grid_ref, field="power grid")
    grid = _mapping(grid_value, field="power grid")
    expected_grid = {
        "screen_datasets_per_cell": _SCREEN_DATASETS_PER_CELL,
        "datasets_per_cell": _PRODUCTION_DATASETS_PER_CELL,
        "max_projected_wall_seconds": _MAX_PROJECTED_WALL_SECONDS,
        "p0_values": [0.1, 0.4, 0.7],
        "trigger_rates": [0.6, 0.75, 0.9],
        "latent_rhos": [0.0, 0.4, 0.8],
    }
    if any(grid.get(field) != expected for field, expected in expected_grid.items()):
        raise RecordValidationError("power grid differs from frozen timing constants")
    nuisance_count = (
        len(cast(list[object], grid["p0_values"]))
        * len(cast(list[object], grid["trigger_rates"]))
        * len(cast(list[object], grid["latent_rhos"]))
    )
    if 4 * nuisance_count * nuisance_count != _CELL_COUNT:
        raise RecordValidationError("power grid does not derive the frozen 2916 cells")

    _, topology_value = _read_ref(
        root, bindings.power_screen_topology_ref, field="power topology"
    )
    topology = _mapping(topology_value, field="power topology")
    if topology != {
        "contract_id": "p0-power-screen-topology-v1",
        "schema_version": "1",
        "shard_partitioning": "contiguous-frozen-cell-range-v1",
    }:
        raise RecordValidationError("power topology differs from frozen topology")

    _, manifest_value = _read_ref(
        root, bindings.study_manifest_ref, field="study manifest"
    )
    manifest = _mapping(manifest_value, field="study manifest")
    manifest_payload = _mapping(manifest.get("payload"), field="study manifest payload")
    if manifest.get("record_kind") != "resampling_study_manifest":
        raise RecordValidationError("study manifest kind differs")
    for field, expected in (
        ("power_grid_ref", bindings.power_grid_ref),
        ("power_screen_topology_ref", bindings.power_screen_topology_ref),
    ):
        actual = decode_artifact_ref(
            manifest_payload.get(field),
            field=f"study manifest {field}",
            expected_role=expected.role,
        )
        if actual != expected:
            raise RecordValidationError(f"study manifest {field} binding differs")

    _, authority_value = _read_ref(
        root, bindings.power_authority_ref, field="power authority"
    )
    authority = _mapping(authority_value, field="power authority")
    if authority.get("authority_kind") != "synthetic_validation":
        raise RecordValidationError("timing no-go requires exact synthetic authority")
    authority_manifest = decode_artifact_ref(
        authority.get("manifest_ref"),
        field="power authority manifest_ref",
        expected_role="study_manifest",
    )
    if authority_manifest != bindings.study_manifest_ref:
        raise RecordValidationError("power authority manifest binding differs")

    _, evidence_value = _read_ref(
        root, bindings.termination_evidence_ref, field="termination evidence"
    )
    return _mapping(evidence_value, field="termination evidence")


def _validate_evidence(
    evidence: Mapping[str, object], bindings: TimingNoGoBindings
) -> tuple[dict[str, object], dict[str, object], int]:
    if set(evidence) != {
        "contract_id",
        "execution_owner",
        "machinery_owner",
        "run_root_identity_sha256",
        "host_identity_sha256",
        "clock",
        "termination",
    }:
        raise RecordValidationError("termination evidence has an open or incomplete shape")
    expected = {
        "contract_id": "task10-p0-timing-termination-evidence-v1",
        "execution_owner": "task_10_canonical_timing_rerun",
        "machinery_owner": "task_8_timing_admission",
        "run_root_identity_sha256": bindings.run_root_identity_sha256,
        "host_identity_sha256": bindings.host_identity_sha256,
    }
    if any(evidence.get(field) != value for field, value in expected.items()):
        raise RecordValidationError("termination evidence identity binding differs")
    if bindings.host_identity_sha256 != _current_host_identity_sha256():
        raise RecordValidationError("termination evidence does not bind the current host")
    clock = _mapping(evidence.get("clock"), field="monotonic clock evidence")
    if set(clock) != {
        "source",
        "started_monotonic_ns",
        "observed_monotonic_ns",
        "elapsed_lower_bound_seconds",
        "semantics",
    }:
        raise RecordValidationError("monotonic clock evidence has an open shape")
    if (
        clock.get("source") != "time.monotonic_ns"
        or clock.get("semantics") != "conservative_lower_bound"
    ):
        raise RecordValidationError("elapsed evidence is not a monotonic lower bound")
    started = clock.get("started_monotonic_ns")
    observed = clock.get("observed_monotonic_ns")
    elapsed = clock.get("elapsed_lower_bound_seconds")
    if (
        type(started) is not int
        or type(observed) is not int
        or type(elapsed) is not int
        or cast(int, started) < 0
        or cast(int, observed) <= cast(int, started)
        or cast(int, elapsed) < 0
        or cast(int, elapsed)
        > (cast(int, observed) - cast(int, started)) // 1_000_000_000
    ):
        raise RecordValidationError("monotonic elapsed lower bound is inconsistent")
    if cast(int, elapsed) <= _ADMISSIBLE_PROBE_THRESHOLD_SECONDS:
        raise RecordValidationError(
            "elapsed lower bound must strictly exceed the 432-second threshold"
        )
    termination = _mapping(evidence.get("termination"), field="termination evidence")
    if termination != {
        "authorization": "user_explicit",
        "event_id": "EJ-20260730-0217",
        "signal": "SIGTERM",
        "exit_status": "clean",
        "probe_status": "terminated_incomplete",
    }:
        raise RecordValidationError("authorized termination evidence differs")
    return clock, termination, cast(int, elapsed)


def _forbidden_descendants(
    root: Path, *, bindings: TimingNoGoBindings
) -> tuple[str, ...]:
    forbidden: list[str] = []
    allowed_files = {
        ".pneuma-power-screen.lock",
        _RECORD_PATH.as_posix(),
        *(ref.relative_path for ref in (
            bindings.study_manifest_ref,
            bindings.power_authority_ref,
            bindings.power_grid_ref,
            bindings.power_screen_topology_ref,
            bindings.termination_evidence_ref,
        )),
    }
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        current = Path(directory)
        for name in tuple(directory_names):
            candidate = current / name
            if candidate.is_symlink():
                forbidden.append(candidate.relative_to(root).as_posix())
                directory_names.remove(name)
        for name in file_names:
            path = current / name
            relative = path.relative_to(root).as_posix()
            if relative in allowed_files or relative.startswith("sources/"):
                continue
            if path.is_symlink():
                forbidden.append(relative)
                continue
            # Every file outside the immutable source namespace and the exact
            # bound inputs is a descendant. Content parsing is diagnostic only;
            # malformed bytes and non-JSON extensions cannot hide existence.
            forbidden.append(relative)
    return tuple(sorted(set(forbidden)))


def _assert_no_forbidden_descendants(
    root: Path, *, bindings: TimingNoGoBindings
) -> None:
    descendants = _forbidden_descendants(root, bindings=bindings)
    if descendants:
        raise RecordValidationError(
            "forbidden descendant exists after timing termination: "
            + ", ".join(descendants)
        )


@contextmanager
def _timing_publication_lock(root: Path):
    """Share the production screen lock across absence check and publication."""

    root_descriptor = os.open(root, _DIRECTORY_FLAGS)
    descriptor: int | None = None
    try:
        try:
            descriptor = os.open(
                ".pneuma-power-screen.lock",
                os.O_RDWR
                | os.O_CREAT
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=root_descriptor,
            )
        except OSError as exc:
            raise RecordValidationError("timing publication lock is unsafe") from exc
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        if descriptor is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
        os.close(root_descriptor)


def _record(
    bindings: TimingNoGoBindings,
    *,
    clock: Mapping[str, object],
    termination: Mapping[str, object],
    elapsed: int,
) -> dict[str, object]:
    projected = elapsed * _MULTIPLIER
    if projected <= _MAX_PROJECTED_WALL_SECONDS:
        raise RecordValidationError("projected lower bound is not timing-infeasible")
    return {
        "schema_version": "0.1.0",
        "record_kind": "resampling_timing_no_go",
        "payload": {
            "outcome": "timing_infeasible_lower_bound",
            "bindings": asdict(bindings),
            "projection": {
                "formula": _FORMULA,
                "cell_count": _CELL_COUNT,
                "shard_count": _SHARD_COUNT,
                "screen_datasets_per_cell": _SCREEN_DATASETS_PER_CELL,
                "production_datasets_per_cell": _PRODUCTION_DATASETS_PER_CELL,
                "multiplier": _MULTIPLIER,
                "max_projected_wall_seconds": _MAX_PROJECTED_WALL_SECONDS,
                "admissible_probe_threshold_seconds": (
                    _ADMISSIBLE_PROBE_THRESHOLD_SECONDS
                ),
                "elapsed_lower_bound_seconds": elapsed,
                "projected_wall_seconds_lower_bound": projected,
            },
            "monotonic_evidence": dict(clock),
            "termination_evidence": dict(termination),
            "execution_provenance": {
                "execution_owner": "task_10_canonical_timing_rerun",
                "machinery_owner": "task_8_timing_admission",
                "promotes_task_10_completion": False,
                "promotes_task_8_scientific_completion": False,
            },
            "artifact_absence": {
                "screen_record": False,
                "timing_verifier": False,
                "power_shard": False,
                "power_final": False,
                "downstream_artifact": False,
            },
            "claims": {field: False for field in _CLAIM_FIELDS},
        },
    }


def _validate_schema(record: Mapping[str, object]) -> None:
    validator = Draft202012Validator(load_schema("resampling-timing-no-go.schema.json"))
    errors = sorted(validator.iter_errors(record), key=lambda error: list(error.path))
    if errors:
        message = "; ".join(
            f"{'/'.join(str(item) for item in error.path) or '<root>'}: "
            f"{error.message}"
            for error in errors
        )
        raise RecordValidationError(f"timing no-go schema/claim validation failed: {message}")


def _exclusive_write(root: Path, payload: bytes) -> None:
    root_descriptor = os.open(root, _DIRECTORY_FLAGS)
    directory_descriptor: int | None = None
    descriptor: int | None = None
    created_directory = False
    try:
        try:
            os.mkdir("timing-admission", mode=0o700, dir_fd=root_descriptor)
            created_directory = True
        except FileExistsError:
            pass
        directory_descriptor = os.open(
            "timing-admission", _DIRECTORY_FLAGS, dir_fd=root_descriptor
        )
        if created_directory:
            os.fsync(root_descriptor)
        descriptor = os.open(
            "task8-timing-no-go.json",
            _WRITE_FLAGS,
            0o600,
            dir_fd=directory_descriptor,
        )
        opened_identity = os.fstat(descriptor)
        try:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short write")
                view = view[written:]
            os.fsync(descriptor)
        except BaseException:
            try:
                named = os.stat(
                    "task8-timing-no-go.json",
                    dir_fd=directory_descriptor,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                named = None
            if (
                named is not None
                and (named.st_dev, named.st_ino)
                == (opened_identity.st_dev, opened_identity.st_ino)
            ):
                os.unlink(
                    "task8-timing-no-go.json", dir_fd=directory_descriptor
                )
            raise
        os.fsync(directory_descriptor)
    except FileExistsError:
        raise
    except OSError as exc:
        raise RecordValidationError(
            "canonical directory or record cannot be published safely"
        ) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)
        os.close(root_descriptor)


def create_timing_no_go(
    bindings: TimingNoGoBindings, *, run_root: Path
) -> Path:
    """Create the one canonical non-power timing no-go record exclusively."""

    if type(bindings) is not TimingNoGoBindings:
        raise TypeError("bindings must be exact TimingNoGoBindings")
    root = _root(run_root)
    with _timing_publication_lock(root):
        evidence = _validate_artifact_graph(bindings, root=root)
        clock, termination, elapsed = _validate_evidence(evidence, bindings)
        _assert_no_forbidden_descendants(root, bindings=bindings)
        record = _record(
            bindings, clock=clock, termination=termination, elapsed=elapsed
        )
        _validate_schema(record)
        destination = root / _RECORD_PATH
        _exclusive_write(root, canonical_json_bytes(record, indent=None))
        _assert_no_forbidden_descendants(root, bindings=bindings)
    return destination


def verify_timing_no_go(path: Path, *, run_root: Path) -> dict[str, object]:
    """Verify canonical bytes, all bindings, arithmetic, and continued no-descendants."""

    root = _root(run_root)
    expected = root / _RECORD_PATH
    try:
        actual = Path(path).resolve(strict=True)
    except OSError as exc:
        raise RecordValidationError("timing no-go record is missing") from exc
    if actual != expected.resolve(strict=True):
        raise RecordValidationError("timing no-go record is not at its canonical path")
    with _timing_publication_lock(root):
        raw = _read_confined(root, _RECORD_PATH.as_posix())
        value = load_json_bytes(raw, source=expected)
        if not isinstance(value, Mapping):
            raise RecordValidationError("timing no-go record must be an object")
        record = dict(value)
        if canonical_json_bytes(record, indent=None) != raw:
            raise RecordValidationError("timing no-go record bytes are not canonical")
        _validate_schema(record)
        payload = _mapping(record.get("payload"), field="timing no-go payload")
        bindings = _decode_bindings(payload.get("bindings"))
        evidence = _validate_artifact_graph(bindings, root=root)
        clock, termination, elapsed = _validate_evidence(evidence, bindings)
        expected_record = _record(
            bindings, clock=clock, termination=termination, elapsed=elapsed
        )
        if record != expected_record:
            raise RecordValidationError(
                "timing no-go record differs from bound evidence"
            )
        _assert_no_forbidden_descendants(root, bindings=bindings)
    return record


__all__ = (
    "TimingNoGoBindings",
    "create_timing_no_go",
    "verify_timing_no_go",
)
