"""Fail-closed storage publication capabilities for resampling-null artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import fcntl
import hashlib
import os
from pathlib import Path
import tempfile
from typing import Literal, Never, cast
from collections.abc import Callable

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .artifacts import (
    RecordValidationError,
    _load_direct_scientific_parent,
    _load_json_bytes,
    _read_ref,
)
from .types import ArtifactRef


_LOCAL_LEASE_TOKEN = object()
_LOCAL_LEASE_SECONDS = 60
_MINIMUM_COMMIT_WINDOW_SECONDS = 5


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return {
        "role": ref.role,
        "relative_path": ref.relative_path,
        "sha256": ref.sha256,
        "byte_count": ref.byte_count,
        "media_type": ref.media_type,
    }


def _artifact_ref(value: object, *, field: str) -> ArtifactRef:
    if not isinstance(value, dict):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    try:
        return ArtifactRef(**value)
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is malformed: {exc}") from exc


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _utc_text(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _fsync_directory(path: Path) -> None:
    fd = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _exclusive_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(fd)
    _fsync_directory(path.parent)


def _prepare_same_directory(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(fd, 0o600)
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        temporary.unlink(missing_ok=True)
        raise
    os.close(fd)
    return temporary


def _install_no_replace(temporary: Path, destination: Path) -> None:
    source_fd = os.open(
        temporary.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    destination_fd = os.open(
        destination.parent,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        os.link(
            temporary.name,
            destination.name,
            src_dir_fd=source_fd,
            dst_dir_fd=destination_fd,
            follow_symlinks=False,
        )
    finally:
        os.close(source_fd)
        os.close(destination_fd)
    temporary.unlink()
    _fsync_directory(destination.parent)


@dataclass(frozen=True, slots=True)
class LocalTestStoragePolicyAttestation:
    record_kind: Literal["storage_policy_attestation_v1"]
    schema_version: Literal["1"]
    authority_ref: ArtifactRef
    transaction: Literal["prefix", "assignment"]
    manifest_sha256: str
    schedule_sha256: str | None
    observation: Literal["begin", "renewal", "end"]
    mode: Literal["local_test"]
    test_only: Literal[True]
    normalized_run_root_sha256: str
    lease_id: str
    lease_generation: int
    lease_expires_at_utc: str
    renewal_sequence: int
    storage_resource_id: None
    measurement_evidence_ref: None
    observed_at_utc: str
    resource_version: None
    mount_identity_sha256: str
    encryption_at_rest: Literal[False]
    encryption_algorithm: None
    kms_key_version: None
    acl_enforced: Literal[False]
    acl_policy_sha256: None
    measurement_sha256: None
    releases_lease: Literal[False]


@dataclass(frozen=True, slots=True)
class StorageTransactionIntent:
    record_kind: Literal["storage_transaction_intent_v1"]
    schema_version: Literal["1"]
    transaction: Literal["prefix", "assignment"]
    lease_id: str
    begin: LocalTestStoragePolicyAttestation
    renewals: tuple[LocalTestStoragePolicyAttestation, ...]
    end: LocalTestStoragePolicyAttestation
    continuous_lease_held: Literal[True]
    fresh_at_end: Literal[True]
    end_releases_lease: Literal[False]
    prepared_scientific_relative_path: str
    prepared_scientific_sha256: str
    final_lease_generation: int
    final_lease_expires_at_utc: str


@dataclass(frozen=True, slots=True)
class LocalTestStoragePublicationCommit:
    record_kind: Literal["storage_publication_commit_v1"]
    schema_version: Literal["1"]
    authority_ref: ArtifactRef
    transaction: Literal["prefix", "assignment"]
    manifest_sha256: str
    schedule_sha256: str | None
    mode: Literal["local_test"]
    test_only: Literal[True]
    normalized_run_root_sha256: str
    lease_id: str
    lease_generation: int
    lease_expires_at_utc: str
    renewal_sequence: int
    committed_at_utc: str
    transaction_intent_sha256: str
    scientific_relative_path: str
    scientific_sha256: str
    storage_resource_id: None
    measurement_evidence_ref: None
    resource_version: None
    mount_identity_sha256: str
    encryption_at_rest: Literal[False]
    encryption_algorithm: None
    kms_key_version: None
    acl_enforced: Literal[False]
    acl_policy_sha256: None
    measurement_sha256: None
    registry_commit_id: str
    commit_recorded: Literal[True]
    lease_consumed: Literal[True]
    release_required: Literal[True]


@dataclass(frozen=True, slots=True)
class StoragePolicyReceipt:
    record_kind: Literal["storage_policy_receipt_v1"]
    schema_version: Literal["1"]
    transaction: Literal["prefix", "assignment"]
    intent: StorageTransactionIntent
    transaction_intent_sha256: str
    publication_commit: LocalTestStoragePublicationCommit
    fresh_at_publication_commit: Literal[True]
    publication_commit_recorded: Literal[True]
    publication_commit_consumes_lease: Literal[True]
    fixed_receipt_is_acceptance_marker: Literal[True]


class ConfirmationStorageLease:
    """Unforgeable placeholder until the trusted provider registry exists."""

    __slots__ = ()

    def __new__(cls) -> ConfirmationStorageLease:
        raise TypeError("confirmation storage registry adapter is unavailable")

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("ConfirmationStorageLease cannot be subclassed")


class LocalTestStorageLease:
    """Exact one-use synthetic process-lock capability."""

    __slots__ = (
        "_authority_ref",
        "_expires_at",
        "_fd",
        "_lease_id",
        "_manifest_sha256",
        "_mount_identity_sha256",
        "_normalized_run_root_sha256",
        "_run_root",
        "_schedule_sha256",
        "_state",
        "_transaction",
    )

    def __new__(
        cls,
        token: object,
        **kwargs: object,
    ) -> LocalTestStorageLease:
        if cls is not LocalTestStorageLease or token is not _LOCAL_LEASE_TOKEN:
            raise TypeError("local-test storage leases are created only by core")
        return super().__new__(cls)

    def __init_subclass__(cls, **kwargs: object) -> None:
        raise TypeError("LocalTestStorageLease cannot be subclassed")

    def __copy__(self) -> LocalTestStorageLease:
        raise TypeError("local-test storage leases cannot be copied")

    def __deepcopy__(self, memo: object) -> LocalTestStorageLease:
        raise TypeError("local-test storage leases cannot be copied")

    def __reduce__(self) -> Never:
        raise TypeError("local-test storage leases cannot be serialized")

    def __init__(
        self,
        token: object,
        *,
        authority_ref: ArtifactRef,
        transaction: Literal["prefix", "assignment"],
        manifest_sha256: str,
        schedule_sha256: str | None,
        run_root: Path,
        fd: int,
        lease_id: str,
        normalized_run_root_sha256: str,
        mount_identity_sha256: str,
    ) -> None:
        if token is not _LOCAL_LEASE_TOKEN:
            raise TypeError("invalid local-test lease token")
        self._authority_ref = authority_ref
        self._transaction = transaction
        self._manifest_sha256 = manifest_sha256
        self._schedule_sha256 = schedule_sha256
        self._run_root = run_root
        self._fd = fd
        self._lease_id = lease_id
        self._normalized_run_root_sha256 = normalized_run_root_sha256
        self._mount_identity_sha256 = mount_identity_sha256
        self._state = "claimed"
        self._expires_at: datetime | None = None

    def _attestation(
        self,
        observation: Literal["begin", "end"],
        *,
        observed_at: datetime,
    ) -> LocalTestStoragePolicyAttestation:
        expires_at = self._expires_at
        if expires_at is None:
            raise RecordValidationError("local-test lease has no live expiry")
        return LocalTestStoragePolicyAttestation(
            record_kind="storage_policy_attestation_v1",
            schema_version="1",
            authority_ref=self._authority_ref,
            transaction=self._transaction,
            manifest_sha256=self._manifest_sha256,
            schedule_sha256=self._schedule_sha256,
            observation=observation,
            mode="local_test",
            test_only=True,
            normalized_run_root_sha256=self._normalized_run_root_sha256,
            lease_id=self._lease_id,
            lease_generation=0,
            lease_expires_at_utc=_utc_text(expires_at),
            renewal_sequence=0,
            storage_resource_id=None,
            measurement_evidence_ref=None,
            observed_at_utc=_utc_text(observed_at),
            resource_version=None,
            mount_identity_sha256=self._mount_identity_sha256,
            encryption_at_rest=False,
            encryption_algorithm=None,
            kms_key_version=None,
            acl_enforced=False,
            acl_policy_sha256=None,
            measurement_sha256=None,
            releases_lease=False,
        )

    def _begin(self) -> LocalTestStoragePolicyAttestation:
        if type(self) is not LocalTestStorageLease or self._state != "claimed":
            raise RecordValidationError("local-test lease cannot begin")
        now = _utc_now()
        self._expires_at = now + timedelta(seconds=_LOCAL_LEASE_SECONDS)
        self._state = "live"
        return self._attestation("begin", observed_at=now)

    def _end(self) -> LocalTestStoragePolicyAttestation:
        if type(self) is not LocalTestStorageLease or self._state != "live":
            raise RecordValidationError("local-test lease cannot end")
        now = _utc_now()
        if self._expires_at is None or now >= self._expires_at:
            raise RecordValidationError("local-test lease expired before end")
        self._state = "end_observed"
        return self._attestation("end", observed_at=now)

    def _commit(
        self,
        *,
        intent: StorageTransactionIntent,
        scientific_path: Path,
    ) -> LocalTestStoragePublicationCommit:
        if type(self) is not LocalTestStorageLease or self._state != "end_observed":
            raise RecordValidationError("local-test lease cannot commit")
        now = _utc_now()
        if self._expires_at is None or now >= self._expires_at:
            raise RecordValidationError("local-test lease expired before commit")
        resolved = scientific_path.resolve(strict=True)
        if not resolved.is_file() or resolved.parent == resolved:
            raise RecordValidationError("scientific path is not an installed file")
        relative_path = resolved.relative_to(self._run_root).as_posix()
        scientific_bytes = resolved.read_bytes()
        scientific_sha256 = hashlib.sha256(scientific_bytes).hexdigest()
        if (
            relative_path != intent.prepared_scientific_relative_path
            or scientific_sha256 != intent.prepared_scientific_sha256
            or intent.lease_id != self._lease_id
            or intent.end != self._attestation(
                "end",
                observed_at=datetime.fromisoformat(
                    intent.end.observed_at_utc.replace("Z", "+00:00")
                ),
            )
        ):
            raise RecordValidationError("storage intent does not bind installed science")
        intent_bytes = canonical_json_bytes(asdict(intent), indent=None)
        intent_digest = hashlib.sha256(intent_bytes).hexdigest()
        commit_id = hashlib.sha256(
            b"local-test-storage-commit-v1\x00" + bytes.fromhex(intent_digest)
        ).hexdigest()
        proof = LocalTestStoragePublicationCommit(
            record_kind="storage_publication_commit_v1",
            schema_version="1",
            authority_ref=self._authority_ref,
            transaction=self._transaction,
            manifest_sha256=self._manifest_sha256,
            schedule_sha256=self._schedule_sha256,
            mode="local_test",
            test_only=True,
            normalized_run_root_sha256=self._normalized_run_root_sha256,
            lease_id=self._lease_id,
            lease_generation=0,
            lease_expires_at_utc=_utc_text(self._expires_at),
            renewal_sequence=0,
            committed_at_utc=_utc_text(now),
            transaction_intent_sha256=intent_digest,
            scientific_relative_path=relative_path,
            scientific_sha256=scientific_sha256,
            storage_resource_id=None,
            measurement_evidence_ref=None,
            resource_version=None,
            mount_identity_sha256=self._mount_identity_sha256,
            encryption_at_rest=False,
            encryption_algorithm=None,
            kms_key_version=None,
            acl_enforced=False,
            acl_policy_sha256=None,
            measurement_sha256=None,
            registry_commit_id=commit_id,
            commit_recorded=True,
            lease_consumed=True,
            release_required=True,
        )
        proof_path = (
            self._run_root
            / "operational"
            / "storage-policy"
            / "registry"
            / "commits"
            / f"{commit_id}.json"
        )
        _exclusive_write(
            proof_path,
            canonical_json_bytes(asdict(proof), indent=None),
        )
        self._state = "committed_consumed"
        return proof

    def _release(self) -> None:
        fd = self._fd
        if fd < 0:
            return
        self._fd = -1
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def _abort(self) -> None:
        if self._state == "committed_consumed":
            raise RecordValidationError("committed local-test lease cannot abort")
        if self._state != "aborted_consumed":
            self._state = "aborted_consumed"
        self._release()


StoragePolicyLease = LocalTestStorageLease | ConfirmationStorageLease


def _load_operational_object(path: Path) -> tuple[dict[str, object], bytes]:
    raw = path.read_bytes()
    value = _load_json_bytes(raw, source=path)
    if not isinstance(value, dict):
        raise RecordValidationError(f"operational record is not an object: {path}")
    if canonical_json_bytes(value, indent=None) != raw:
        raise RecordValidationError(f"operational record is not compact canonical: {path}")
    return value, raw


def _matching_commit_proofs(
    root: Path,
    *,
    intent_digest: str,
) -> list[tuple[Path, dict[str, object]]]:
    commit_root = root / "operational" / "storage-policy" / "registry" / "commits"
    if not commit_root.exists():
        return []
    matches: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(commit_root.glob("*.json")):
        value, _raw = _load_operational_object(path)
        if value.get("transaction_intent_sha256") == intent_digest:
            matches.append((path, value))
    return matches


def _validate_local_intent(
    lease: LocalTestStorageLease,
    *,
    intent: dict[str, object],
    prepared_relative_path: str,
    prepared_sha256: str,
) -> dict[str, object]:
    expected_keys = {
        "record_kind",
        "schema_version",
        "transaction",
        "lease_id",
        "begin",
        "renewals",
        "end",
        "continuous_lease_held",
        "fresh_at_end",
        "end_releases_lease",
        "prepared_scientific_relative_path",
        "prepared_scientific_sha256",
        "final_lease_generation",
        "final_lease_expires_at_utc",
    }
    if set(intent) != expected_keys:
        raise RecordValidationError("storage intent has an open or incomplete shape")
    begin = intent["begin"]
    end = intent["end"]
    if not isinstance(begin, dict) or not isinstance(end, dict):
        raise RecordValidationError("storage intent attestations must be objects")
    attestation_keys = {
        "record_kind",
        "schema_version",
        "authority_ref",
        "transaction",
        "manifest_sha256",
        "schedule_sha256",
        "observation",
        "mode",
        "test_only",
        "normalized_run_root_sha256",
        "lease_id",
        "lease_generation",
        "lease_expires_at_utc",
        "renewal_sequence",
        "storage_resource_id",
        "measurement_evidence_ref",
        "observed_at_utc",
        "resource_version",
        "mount_identity_sha256",
        "encryption_at_rest",
        "encryption_algorithm",
        "kms_key_version",
        "acl_enforced",
        "acl_policy_sha256",
        "measurement_sha256",
        "releases_lease",
    }
    if set(begin) != attestation_keys or set(end) != attestation_keys:
        raise RecordValidationError("storage intent attestation shape is not closed")
    authority = _ref_mapping(lease._authority_ref)
    shared_checks = {
        "authority_ref": authority,
        "transaction": lease._transaction,
        "manifest_sha256": lease._manifest_sha256,
        "schedule_sha256": lease._schedule_sha256,
        "mode": "local_test",
        "test_only": True,
        "normalized_run_root_sha256": lease._normalized_run_root_sha256,
        "lease_id": lease._lease_id,
        "lease_generation": 0,
        "renewal_sequence": 0,
        "storage_resource_id": None,
        "measurement_evidence_ref": None,
        "resource_version": None,
        "mount_identity_sha256": lease._mount_identity_sha256,
        "encryption_at_rest": False,
        "encryption_algorithm": None,
        "kms_key_version": None,
        "acl_enforced": False,
        "acl_policy_sha256": None,
        "measurement_sha256": None,
        "releases_lease": False,
    }
    if any(begin.get(key) != value for key, value in shared_checks.items()) or any(
        end.get(key) != value for key, value in shared_checks.items()
    ):
        raise RecordValidationError("storage intent attestation binding differs")
    if (
        begin.get("record_kind") != "storage_policy_attestation_v1"
        or begin.get("schema_version") != "1"
        or begin.get("observation") != "begin"
        or end.get("record_kind") != "storage_policy_attestation_v1"
        or end.get("schema_version") != "1"
        or end.get("observation") != "end"
        or begin.get("lease_expires_at_utc") != end.get("lease_expires_at_utc")
        or intent["record_kind"] != "storage_transaction_intent_v1"
        or intent["schema_version"] != "1"
        or intent["transaction"] != lease._transaction
        or intent["lease_id"] != lease._lease_id
        or intent["renewals"] != []
        or intent["continuous_lease_held"] is not True
        or intent["fresh_at_end"] is not True
        or intent["end_releases_lease"] is not False
        or intent["prepared_scientific_relative_path"] != prepared_relative_path
        or intent["prepared_scientific_sha256"] != prepared_sha256
        or intent["final_lease_generation"] != end.get("lease_generation")
        or intent["final_lease_expires_at_utc"] != end.get("lease_expires_at_utc")
    ):
        raise RecordValidationError("storage intent lifecycle or science binding differs")
    observed_begin = datetime.fromisoformat(
        cast(str, begin["observed_at_utc"]).replace("Z", "+00:00")
    )
    observed_end = datetime.fromisoformat(
        cast(str, end["observed_at_utc"]).replace("Z", "+00:00")
    )
    expires_at = datetime.fromisoformat(
        cast(str, end["lease_expires_at_utc"]).replace("Z", "+00:00")
    )
    if not observed_begin <= observed_end < expires_at:
        raise RecordValidationError("storage intent timestamps are not fresh and ordered")
    return end


def _recover_committed_receipt(
    lease: LocalTestStorageLease,
    *,
    destination: Path,
    receipt_path: Path,
    role: str,
    media_type: str,
) -> ArtifactRef:
    root = lease._run_root
    intent_path = (
        root
        / "operational"
        / "storage-policy"
        / "intents"
        / f"{lease._transaction}.json"
    )
    if not intent_path.is_file():
        raise RecordValidationError(
            "installed science without intent is permanently quarantined"
        )
    intent, intent_bytes = _load_operational_object(intent_path)
    intent_digest = hashlib.sha256(intent_bytes).hexdigest()
    scientific_bytes = destination.read_bytes()
    scientific_sha256 = hashlib.sha256(scientific_bytes).hexdigest()
    relative_path = destination.relative_to(root).as_posix()
    if (
        intent.get("prepared_scientific_relative_path") != relative_path
        or intent.get("prepared_scientific_sha256") != scientific_sha256
    ):
        raise RecordValidationError("installed science does not match its storage intent")
    end = _validate_local_intent(
        lease,
        intent=intent,
        prepared_relative_path=relative_path,
        prepared_sha256=scientific_sha256,
    )
    proofs = _matching_commit_proofs(root, intent_digest=intent_digest)
    if len(proofs) != 1:
        raise RecordValidationError(
            "installed science lacks exactly one durable commit proof"
        )
    proof_path, proof = proofs[0]
    expected_commit_id = hashlib.sha256(
        b"local-test-storage-commit-v1\x00" + bytes.fromhex(intent_digest)
    ).hexdigest()
    if (
        set(proof) != set(LocalTestStoragePublicationCommit.__dataclass_fields__)
        or proof.get("record_kind") != "storage_publication_commit_v1"
        or proof.get("schema_version") != "1"
        or proof.get("transaction") != lease._transaction
        or proof.get("authority_ref") != _ref_mapping(lease._authority_ref)
        or proof.get("manifest_sha256") != lease._manifest_sha256
        or proof.get("schedule_sha256") != lease._schedule_sha256
        or proof.get("mode") != "local_test"
        or proof.get("test_only") is not True
        or proof.get("normalized_run_root_sha256")
        != lease._normalized_run_root_sha256
        or proof.get("lease_id") != intent.get("lease_id")
        or proof.get("lease_generation") != end.get("lease_generation")
        or proof.get("lease_expires_at_utc") != end.get("lease_expires_at_utc")
        or proof.get("renewal_sequence") != end.get("renewal_sequence")
        or proof.get("scientific_relative_path") != relative_path
        or proof.get("scientific_sha256") != scientific_sha256
        or proof.get("mount_identity_sha256") != lease._mount_identity_sha256
        or proof.get("storage_resource_id") is not None
        or proof.get("measurement_evidence_ref") is not None
        or proof.get("resource_version") is not None
        or proof.get("encryption_at_rest") is not False
        or proof.get("encryption_algorithm") is not None
        or proof.get("kms_key_version") is not None
        or proof.get("acl_enforced") is not False
        or proof.get("acl_policy_sha256") is not None
        or proof.get("measurement_sha256") is not None
        or proof.get("registry_commit_id") != expected_commit_id
        or proof_path.name != f"{expected_commit_id}.json"
        or proof.get("commit_recorded") is not True
        or proof.get("lease_consumed") is not True
        or proof.get("release_required") is not True
    ):
        raise RecordValidationError("durable commit proof has wrong binding")
    committed_at = datetime.fromisoformat(
        cast(str, proof["committed_at_utc"]).replace("Z", "+00:00")
    )
    expires_at = datetime.fromisoformat(
        cast(str, proof["lease_expires_at_utc"]).replace("Z", "+00:00")
    )
    if committed_at >= expires_at:
        raise RecordValidationError("durable commit proof is not fresh")
    receipt = {
        "record_kind": "storage_policy_receipt_v1",
        "schema_version": "1",
        "transaction": lease._transaction,
        "intent": intent,
        "transaction_intent_sha256": intent_digest,
        "publication_commit": proof,
        "fresh_at_publication_commit": True,
        "publication_commit_recorded": True,
        "publication_commit_consumes_lease": True,
        "fixed_receipt_is_acceptance_marker": True,
    }
    _exclusive_write(
        receipt_path,
        canonical_json_bytes(receipt, indent=None),
    )
    lease._abort()
    return ArtifactRef(
        role=role,
        relative_path=relative_path,
        sha256=scientific_sha256,
        byte_count=len(scientific_bytes),
        media_type=media_type,
    )


def _replace_uncommitted_intent(
    lease: LocalTestStorageLease,
    *,
    intent_path: Path,
    prepared_relative_path: str,
) -> None:
    if not intent_path.exists():
        return
    prepared_path = lease._run_root / prepared_relative_path
    if prepared_path.exists():
        raise RecordValidationError(
            "stale intent cannot abort after scientific installation"
        )
    old_intent, old_bytes = _load_operational_object(intent_path)
    old_digest = hashlib.sha256(old_bytes).hexdigest()
    old_sha256 = old_intent.get("prepared_scientific_sha256")
    if not isinstance(old_sha256, str):
        raise RecordValidationError("stale storage intent lacks science digest")
    _validate_local_intent(
        lease,
        intent=old_intent,
        prepared_relative_path=prepared_relative_path,
        prepared_sha256=old_sha256,
    )
    if _matching_commit_proofs(lease._run_root, intent_digest=old_digest):
        raise RecordValidationError(
            "committed intent cannot be replaced before science recovery"
        )
    abort = {
        "record_kind": "local_test_storage_abort_v1",
        "schema_version": "1",
        "transaction": lease._transaction,
        "lease_id": old_intent.get("lease_id"),
        "transaction_intent_sha256": old_digest,
        "prepared_scientific_relative_path": prepared_relative_path,
        "science_absent": True,
        "commit_absent": True,
        "state": "aborted_consumed",
    }
    abort_bytes = canonical_json_bytes(abort, indent=None)
    abort_id = hashlib.sha256(abort_bytes).hexdigest()
    abort_path = (
        lease._run_root
        / "operational"
        / "storage-policy"
        / "registry"
        / "aborts"
        / f"{abort_id}.json"
    )
    if abort_path.exists():
        if abort_path.read_bytes() != abort_bytes:
            raise RecordValidationError("stored abort proof bytes differ")
    else:
        _exclusive_write(abort_path, abort_bytes)
    intent_path.unlink()
    _fsync_directory(intent_path.parent)


def _publish_local_test_scientific(
    lease: LocalTestStorageLease,
    *,
    out: Path,
    role: str,
    media_type: str,
    prepare: Callable[[], bytes],
) -> ArtifactRef:
    """Publish one scientific file through the closed local-test transaction."""

    if type(lease) is not LocalTestStorageLease:
        raise TypeError("local publication requires the exact local lease")
    root = lease._run_root
    candidate = Path(out)
    if not candidate.is_absolute():
        candidate = root / candidate
    # Create the destination subtree only after a lexical containment check;
    # the strict resolve below still fails closed on any symlink escape.
    try:
        candidate.parent.relative_to(root)
    except ValueError as exc:
        raise RecordValidationError("scientific destination escapes run_root") from exc
    candidate.parent.mkdir(parents=True, exist_ok=True)
    parent = candidate.parent.resolve(strict=True)
    try:
        parent.relative_to(root)
    except ValueError as exc:
        raise RecordValidationError("scientific destination escapes run_root") from exc
    destination = parent / candidate.name
    receipt_path = (
        root
        / "operational"
        / "storage-policy"
        / f"{lease._transaction}.json"
    )
    if receipt_path.exists():
        raise FileExistsError(receipt_path)
    if destination.exists():
        try:
            return _recover_committed_receipt(
                lease,
                destination=destination,
                receipt_path=receipt_path,
                role=role,
                media_type=media_type,
            )
        except BaseException:
            lease._abort()
            raise

    temporary: Path | None = None
    installed = False
    committed = False
    try:
        begin = lease._begin()
        scientific_bytes = prepare()
        if type(scientific_bytes) is not bytes:
            raise TypeError("scientific preparer must return exact bytes")
        scientific_sha256 = hashlib.sha256(scientific_bytes).hexdigest()
        relative_path = destination.relative_to(root).as_posix()
        temporary = _prepare_same_directory(destination, scientific_bytes)
        end = lease._end()
        intent = StorageTransactionIntent(
            record_kind="storage_transaction_intent_v1",
            schema_version="1",
            transaction=lease._transaction,
            lease_id=lease._lease_id,
            begin=begin,
            renewals=(),
            end=end,
            continuous_lease_held=True,
            fresh_at_end=True,
            end_releases_lease=False,
            prepared_scientific_relative_path=relative_path,
            prepared_scientific_sha256=scientific_sha256,
            final_lease_generation=end.lease_generation,
            final_lease_expires_at_utc=end.lease_expires_at_utc,
        )
        expires_at = datetime.fromisoformat(
            end.lease_expires_at_utc.replace("Z", "+00:00")
        )
        if expires_at - _utc_now() < timedelta(
            seconds=_MINIMUM_COMMIT_WINDOW_SECONDS
        ):
            raise RecordValidationError(
                "local-test lease lacks bounded publication window"
            )
        intent_bytes = canonical_json_bytes(asdict(intent), indent=None)
        intent_digest = hashlib.sha256(intent_bytes).hexdigest()
        intent_path = (
            root
            / "operational"
            / "storage-policy"
            / "intents"
            / f"{lease._transaction}.json"
        )
        _replace_uncommitted_intent(
            lease,
            intent_path=intent_path,
            prepared_relative_path=relative_path,
        )
        _exclusive_write(intent_path, intent_bytes)
        _install_no_replace(temporary, destination)
        temporary = None
        installed = True
        publication_commit = lease._commit(
            intent=intent,
            scientific_path=destination,
        )
        committed = True
        if publication_commit.transaction_intent_sha256 != intent_digest:
            raise RecordValidationError(
                "publication commit does not bind transaction intent"
            )
        receipt = StoragePolicyReceipt(
            record_kind="storage_policy_receipt_v1",
            schema_version="1",
            transaction=lease._transaction,
            intent=intent,
            transaction_intent_sha256=intent_digest,
            publication_commit=publication_commit,
            fresh_at_publication_commit=True,
            publication_commit_recorded=True,
            publication_commit_consumes_lease=True,
            fixed_receipt_is_acceptance_marker=True,
        )
        _exclusive_write(
            receipt_path,
            canonical_json_bytes(asdict(receipt), indent=None),
        )
        return ArtifactRef(
            role=role,
            relative_path=relative_path,
            sha256=scientific_sha256,
            byte_count=len(scientific_bytes),
            media_type=media_type,
        )
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        if not installed:
            lease._abort()
        elif committed:
            lease._release()
        else:
            lease._release()
        raise
    finally:
        if committed:
            lease._release()


def claim_local_test_storage(
    *,
    transaction: Literal["prefix", "assignment"],
    run_root: Path,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef | None,
) -> LocalTestStorageLease:
    """Claim the closed local-test policy and an exclusive transaction lock."""

    if transaction not in ("prefix", "assignment"):
        raise ValueError("storage transaction must be prefix or assignment")
    if type(manifest_ref) is not ArtifactRef or (
        schedule_ref is not None and type(schedule_ref) is not ArtifactRef
    ):
        raise TypeError("storage binding requires exact ArtifactRef values")
    root = run_root.resolve(strict=True)
    if not root.is_dir():
        raise NotADirectoryError(root)
    manifest = _load_direct_scientific_parent(
        _ref_mapping(manifest_ref),
        run_root=root,
        field="manifest_ref",
        expected_kind="resampling_study_manifest",
    )
    payload = cast(dict[str, object], manifest.value["payload"])
    if (
        payload.get("eligibility_manifest_ref") is not None
        or payload.get("roster_ceremony_policy_ref") is not None
    ):
        raise RecordValidationError(
            "local-test storage requires a synthetic manifest"
        )
    roster_ref = _artifact_ref(
        payload.get("roster_ref"),
        field="manifest roster_ref",
    )
    roster_path, roster_bytes = _read_ref(roster_ref, run_root=root)
    roster = _load_json_bytes(roster_bytes, source=roster_path)
    if not isinstance(roster, dict) or roster.get("roster_kind") != "synthetic_fixture":
        raise RecordValidationError(
            "local-test storage requires a synthetic fixture roster"
        )
    authority_ref = _artifact_ref(
        payload.get("storage_policy_contract_ref"),
        field="manifest storage_policy_contract_ref",
    )
    authority_path, authority_bytes = _read_ref(authority_ref, run_root=root)
    authority = _load_json_bytes(authority_bytes, source=authority_path)
    expected_authority = {
        "record_kind": "storage_policy_contract_v1",
        "schema_version": "1",
        "mode": "local_test",
        "test_only": True,
        "storage_resource_id": None,
        "measurement_evidence_ref": None,
        "evidence_verifier_public_key_ed25519_hex": None,
        "registry_attestation_public_key_ed25519_hex": None,
        "max_measurement_age_seconds": None,
        "lease_kind": "local_test_process_lock_v1",
        "encryption_at_rest": False,
        "encryption_algorithm": None,
        "kms_key_version": None,
        "acl_enforced": False,
        "acl_policy_sha256": None,
        "measurement_sha256": None,
    }
    if authority != expected_authority:
        raise RecordValidationError("manifest storage policy is not closed local_test")
    if transaction == "prefix" and schedule_ref is not None:
        raise RecordValidationError("prefix storage lease requires null schedule")
    if transaction == "assignment" and schedule_ref is None:
        raise RecordValidationError("assignment storage lease requires schedule")
    normalized_root = root.as_posix().encode("utf-8")
    normalized_root_sha256 = hashlib.sha256(normalized_root).hexdigest()
    stat = root.stat()
    mount_identity_sha256 = hashlib.sha256(
        canonical_json_bytes(
            {"st_dev": stat.st_dev, "st_ino": stat.st_ino},
            indent=None,
        )
    ).hexdigest()
    schedule_sha256 = None if schedule_ref is None else schedule_ref.sha256
    binding = canonical_json_bytes(
        {
            "authority_sha256": authority_ref.sha256,
            "manifest_sha256": manifest_ref.sha256,
            "normalized_run_root_sha256": normalized_root_sha256,
            "schedule_sha256": schedule_sha256,
            "transaction": transaction,
        },
        indent=None,
    )
    lease_id = hashlib.sha256(b"local-test-storage-lease-v1\x00" + binding).hexdigest()
    lock_dir = root / "operational" / "storage-policy" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    resolved_lock_dir = lock_dir.resolve(strict=True)
    try:
        resolved_lock_dir.relative_to(root)
    except ValueError as exc:
        raise RecordValidationError("storage lock directory escapes run_root") from exc
    directory_fd = os.open(
        resolved_lock_dir,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
    )
    try:
        fd = os.open(
            f"{transaction}.lock",
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory_fd,
        )
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            raise RecordValidationError(
                f"{transaction} storage transaction lock is already held"
            ) from None
    finally:
        os.close(directory_fd)
    return LocalTestStorageLease(
        _LOCAL_LEASE_TOKEN,
        authority_ref=authority_ref,
        transaction=transaction,
        manifest_sha256=manifest_ref.sha256,
        schedule_sha256=schedule_sha256,
        run_root=root,
        fd=fd,
        lease_id=lease_id,
        normalized_run_root_sha256=normalized_root_sha256,
        mount_identity_sha256=mount_identity_sha256,
    )
