"""Fail-closed storage publication capabilities for resampling-null artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import fcntl
import hashlib
import os
from pathlib import Path
from typing import Literal, Never, cast

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
        self._state = "committed_consumed"
        return LocalTestStoragePublicationCommit(
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
