"""Canonical binary framing and keyed derivations for resampling-null assignment."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import hmac
from pathlib import Path
from typing import Literal, cast
import unicodedata

from .artifacts import (
    RecordValidationError,
    _load_json_bytes,
    _load_direct_scientific_parent,
    _power_payload,
    _read_ref,
    _scientific_documents,
    _validate_power_identities,
    _walk_artifact_refs,
)
from .preflight import verify_ed25519_canonical_json
from .secrets import (
    AssignmentSecretHandle,
    UnblindSecretHandle,
    _consume_assignment_handle_into,
)
from .types import ArtifactRef, ScheduleSelection
from .types import (
    AllocationReceipt,
    Arm,
    AssignmentPrefixTaskView,
    AssignmentPrefixView,
    TaskAssignment,
    TaskSchedule,
    Treatment,
    TriggerReason,
)


_FRAME_MAGIC = b"pneuma-resampling-null-frame-v1\x00"
_MAX_U32 = 2**32 - 1
_MAX_U64 = 2**64 - 1
_SUBKEY_LABELS = frozenset(
    {"donor", "allocation", "orientation", "capability", "unblind", "pair_recovery"}
)
_ALLOCATION_TABLE: tuple[tuple[Treatment, Treatment, Treatment, Treatment], ...] = (
    (Treatment.NO_PACKET, Treatment.NO_PACKET, Treatment.REAL, Treatment.SHAM),
    (Treatment.NO_PACKET, Treatment.NO_PACKET, Treatment.SHAM, Treatment.REAL),
    (Treatment.NO_PACKET, Treatment.REAL, Treatment.NO_PACKET, Treatment.SHAM),
    (Treatment.NO_PACKET, Treatment.REAL, Treatment.SHAM, Treatment.NO_PACKET),
    (Treatment.NO_PACKET, Treatment.SHAM, Treatment.NO_PACKET, Treatment.REAL),
    (Treatment.NO_PACKET, Treatment.SHAM, Treatment.REAL, Treatment.NO_PACKET),
    (Treatment.REAL, Treatment.NO_PACKET, Treatment.NO_PACKET, Treatment.SHAM),
    (Treatment.REAL, Treatment.NO_PACKET, Treatment.SHAM, Treatment.NO_PACKET),
    (Treatment.REAL, Treatment.SHAM, Treatment.NO_PACKET, Treatment.NO_PACKET),
    (Treatment.SHAM, Treatment.NO_PACKET, Treatment.NO_PACKET, Treatment.REAL),
    (Treatment.SHAM, Treatment.NO_PACKET, Treatment.REAL, Treatment.NO_PACKET),
    (Treatment.SHAM, Treatment.REAL, Treatment.NO_PACKET, Treatment.NO_PACKET),
)


@dataclass(frozen=True, slots=True)
class U64Field:
    value: int


@dataclass(frozen=True, slots=True)
class TextField:
    value: str


@dataclass(frozen=True, slots=True)
class BytesField:
    value: bytes


FrameField = U64Field | TextField | BytesField


@dataclass(frozen=True, slots=True)
class UniformDraw:
    value: int
    counter: int


@dataclass(frozen=True, slots=True)
class AssignmentAuthority:
    """Immutable identities loaded exclusively through scientific refs."""

    study_id: str
    frozen_created_at: str
    manifest_ref: ArtifactRef
    schedule_ref: ArtifactRef
    prefix_index_ref: ArtifactRef


def _artifact_ref(value: object, *, field: str) -> ArtifactRef:
    if not isinstance(value, dict):
        raise RecordValidationError(f"{field} must be an ArtifactRef")
    try:
        return ArtifactRef(**value)
    except (KeyError, TypeError, ValueError) as exc:
        raise RecordValidationError(f"{field} is malformed: {exc}") from exc


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return {
        "role": ref.role,
        "relative_path": ref.relative_path,
        "sha256": ref.sha256,
        "byte_count": ref.byte_count,
        "media_type": ref.media_type,
    }


def load_assignment_authority(
    schedule_ref: ArtifactRef,
    prefix_index_ref: ArtifactRef,
    *,
    run_root: Path,
) -> AssignmentAuthority:
    """Load schedule, its manifest, and prefix solely through bound refs."""

    if type(schedule_ref) is not ArtifactRef or type(prefix_index_ref) is not ArtifactRef:
        raise TypeError("assignment authority requires exact ArtifactRef values")
    schedule = _load_direct_scientific_parent(
        _ref_mapping(schedule_ref),
        run_root=run_root,
        field="schedule_ref",
        expected_kind="resampling_prefix_schedule",
    )
    schedule_payload = schedule.value["payload"]
    if not isinstance(schedule_payload, dict):
        raise RecordValidationError("schedule payload must be an object")
    manifest_ref = _artifact_ref(
        schedule_payload.get("manifest_ref"),
        field="schedule manifest_ref",
    )
    manifest = _load_direct_scientific_parent(
        _ref_mapping(manifest_ref),
        run_root=run_root,
        field="schedule manifest_ref",
        expected_kind="resampling_study_manifest",
    )
    prefix = _load_direct_scientific_parent(
        _ref_mapping(prefix_index_ref),
        run_root=run_root,
        field="prefix_index_ref",
        expected_kind="resampling_prefix_receipt",
    )
    prefix_payload = prefix.value["payload"]
    if not isinstance(prefix_payload, dict):
        raise RecordValidationError("prefix payload must be an object")
    if _artifact_ref(
        prefix_payload.get("schedule_ref"),
        field="prefix schedule_ref",
    ) != schedule_ref:
        raise RecordValidationError("prefix index does not descend from schedule_ref")
    identities = (manifest.value, schedule.value, prefix.value)
    for field in ("study_id", "frozen_created_at", "provenance"):
        expected = identities[0][field]
        if any(record[field] != expected for record in identities[1:]):
            raise RecordValidationError(
                f"assignment authority has inconsistent {field}"
            )
    return AssignmentAuthority(
        study_id=str(schedule.value["study_id"]),
        frozen_created_at=str(schedule.value["frozen_created_at"]),
        manifest_ref=manifest_ref,
        schedule_ref=schedule_ref,
        prefix_index_ref=prefix_index_ref,
    )


def require_schedulable_power_final(
    manifest_ref: ArtifactRef,
    power_final_ref: ArtifactRef,
    *,
    run_root: Path,
) -> ScheduleSelection:
    """Return only membership authority from one complete validated power chain."""

    if type(manifest_ref) is not ArtifactRef or type(power_final_ref) is not ArtifactRef:
        raise TypeError("power-final authority requires exact ArtifactRef values")
    manifest = _load_direct_scientific_parent(
        _ref_mapping(manifest_ref),
        run_root=run_root,
        field="manifest_ref",
        expected_kind="resampling_study_manifest",
    )
    final = _load_direct_scientific_parent(
        _ref_mapping(power_final_ref),
        run_root=run_root,
        field="power_final_ref",
        expected_kind="resampling_power_report",
        expected_stage="final",
    )
    for field in ("study_id", "frozen_created_at", "provenance"):
        if final.value[field] != manifest.value[field]:
            raise RecordValidationError(
                f"power final {field} does not match manifest"
            )

    documents = _scientific_documents(run_root, excluded=set())
    power_documents = [
        document
        for document in documents.values()
        if document.value["record_kind"] == "resampling_power_report"
    ]
    final_payload = _power_payload(final)
    declared_attempt_paths = {
        ref.relative_path
        for ref in _walk_artifact_refs(final_payload["all_attempt_refs"])
    }
    expected_power_paths = declared_attempt_paths | {power_final_ref.relative_path}
    observed_power_paths = {document.relative_path for document in power_documents}
    if observed_power_paths != expected_power_paths:
        raise RecordValidationError(
            "run root power reports are not exactly the final-declared chain"
        )
    _validate_power_identities(power_documents, run_root=run_root)

    finalization = final_payload["finalization"]
    if not isinstance(finalization, Mapping):
        raise RecordValidationError("power finalization must be an object")
    if finalization.get("kind") != "completed_chain":
        raise RecordValidationError("power final is not a completed schedulable chain")
    authority = final_payload["decision_authority"]
    selected_tier = finalization.get("selected_tier")

    manifest_payload = manifest.value["payload"]
    if not isinstance(manifest_payload, Mapping):
        raise RecordValidationError("manifest payload must be an object")
    roster_ref = _artifact_ref(
        manifest_payload.get("roster_ref"),
        field="manifest roster_ref",
    )
    roster_path, roster_bytes = _read_ref(roster_ref, run_root=run_root)
    roster = _load_json_bytes(roster_bytes, source=roster_path)
    if not isinstance(roster, Mapping):
        raise RecordValidationError("manifest roster must be an object")
    if set(roster) != {
        "record_kind",
        "schema_version",
        "roster_kind",
        "supported_tiers",
        "tasks",
    }:
        raise RecordValidationError("manifest roster has an open or incomplete shape")
    if (
        roster["record_kind"] != "resampling_roster_v1"
        or roster["schema_version"] != "1"
    ):
        raise RecordValidationError("manifest roster has wrong identity")
    tasks = roster["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise RecordValidationError("manifest roster tasks must be non-empty")
    supported_tiers = roster["supported_tiers"]
    if supported_tiers not in ([120], [120, 160]):
        raise RecordValidationError(
            "manifest roster supported_tiers must be [120] or [120, 160]"
        )

    selected_task_ids: list[str] = []
    seen_task_ids: set[str] = set()
    previous_order_key: tuple[bytes, bytes, bytes, bytes] | None = None
    tier_counts: dict[tuple[str, int], int] = {}
    for index, task in enumerate(tasks):
        if not isinstance(task, Mapping):
            raise RecordValidationError(f"manifest roster task {index} must be an object")
        if set(task) != {
            "task_id",
            "benchmark",
            "stratum",
            "lineage",
            "groups",
            "tiers",
        }:
            raise RecordValidationError(
                f"manifest roster task {index} has an open or incomplete shape"
            )
        task_id = task["task_id"]
        if not isinstance(task_id, str) or not task_id or task_id in seen_task_ids:
            raise RecordValidationError(
                "manifest roster task_id values must be unique non-empty strings"
            )
        seen_task_ids.add(task_id)
        text_fields = {
            field: task[field]
            for field in ("benchmark", "stratum", "lineage")
        }
        if any(not isinstance(value, str) or not value for value in text_fields.values()):
            raise RecordValidationError(
                f"manifest roster task {task_id!r} has invalid text metadata"
            )
        order_key = tuple(
            cast(str, value).encode("utf-8")
            for value in (
                text_fields["benchmark"],
                text_fields["stratum"],
                text_fields["lineage"],
                task_id,
            )
        )
        if previous_order_key is not None and order_key <= previous_order_key:
            raise RecordValidationError(
                "manifest roster tasks are not in strict registry order"
            )
        previous_order_key = cast(tuple[bytes, bytes, bytes, bytes], order_key)
        groups = task["groups"]
        if not isinstance(groups, list) or len(groups) != 3:
            raise RecordValidationError(
                f"manifest roster task {task_id!r} lacks complete groups"
            )
        expected_group_kinds = ("language", "domain", "issue_family")
        for group_index, (group, expected_kind) in enumerate(
            zip(groups, expected_group_kinds, strict=True)
        ):
            if (
                not isinstance(group, Mapping)
                or set(group) != {"kind", "value"}
                or group.get("kind") != expected_kind
                or not isinstance(group.get("value"), str)
                or not group.get("value")
            ):
                raise RecordValidationError(
                    f"manifest roster task {task_id!r} group {group_index} is invalid"
                )
        tiers = task["tiers"]
        if (
            not isinstance(tiers, list)
            or not tiers
            or any(type(tier) is not int or tier not in (120, 160) for tier in tiers)
            or tiers != sorted(set(tiers))
            or any(tier not in supported_tiers for tier in tiers)
        ):
            raise RecordValidationError(
                f"manifest roster task {task_id!r} has invalid tiers"
            )
        benchmark = cast(str, text_fields["benchmark"])
        for tier in tiers:
            key = (benchmark, cast(int, tier))
            tier_counts[key] = tier_counts.get(key, 0) + 1
        if authority == "synthetic_validation" or selected_tier in tiers:
            selected_task_ids.append(task_id)

    eligibility_ref = manifest_payload.get("eligibility_manifest_ref")
    if authority == "synthetic_validation":
        if (
            roster["roster_kind"] != "synthetic_fixture"
            or eligibility_ref is not None
            or selected_tier is not None
            or finalization.get("decision") != "CONDITIONAL_ONLY"
        ):
            raise RecordValidationError(
                "synthetic completed chain does not match manifest roster authority"
            )
    elif authority == "roster_bound_selection":
        if (
            roster["roster_kind"] != "eligible_confirmation"
            or not isinstance(eligibility_ref, Mapping)
            or selected_tier not in (120, 160)
            or finalization.get("decision") != "GO"
        ):
            raise RecordValidationError(
                "roster-bound completed chain does not match manifest eligibility"
            )
        benchmarks = {
            cast(str, cast(Mapping[str, object], task)["benchmark"])
            for task in tasks
        }
        if any(
            tier_counts.get((benchmark, tier)) != tier
            for benchmark in benchmarks
            for tier in cast(list[int], supported_tiers)
        ):
            raise RecordValidationError(
                "confirmation roster tier counts do not equal their declared sizes"
            )
        eligibility = _artifact_ref(
            eligibility_ref,
            field="manifest eligibility_manifest_ref",
        )
        _read_ref(eligibility, run_root=run_root)
    else:
        raise RecordValidationError("power final has unknown decision authority")
    if not selected_task_ids:
        raise RecordValidationError("completed power final selects no roster tasks")
    return ScheduleSelection(
        schedule_authority=authority,
        selected_tier=selected_tier,
        selected_task_ids=tuple(selected_task_ids),
    )


def verify_matching_invocation_signature(
    receipt: Mapping[str, object],
    *,
    runner_public_key_ed25519_hex: str,
) -> str:
    """Verify one runner attestation over its canonical unsigned receipt."""

    signature = receipt.get("runner_signature_ed25519_hex")
    if type(signature) is not str:
        raise RecordValidationError(
            "runner_signature_ed25519_hex must be exact text"
        )
    return verify_ed25519_canonical_json(
        receipt,
        public_key_ed25519_hex=runner_public_key_ed25519_hex,
        signature_ed25519_hex=signature,
        signature_field="runner_signature_ed25519_hex",
    )


class _AssignmentKeyBuffers:
    """Private mutable application-owned buffers; never returned or serialized."""

    __slots__ = ("donor", "allocation", "orientation", "capability")

    def __init__(self) -> None:
        self.donor = bytearray(32)
        self.allocation = bytearray(32)
        self.orientation = bytearray(32)
        self.capability = bytearray(32)

    def _buffers(self) -> tuple[object, ...]:
        return (
            self.donor,
            self.allocation,
            self.orientation,
            self.capability,
        )

    def _validate(self) -> None:
        if any(
            type(buffer) is not bytearray or len(buffer) != 32
            for buffer in self._buffers()
        ):
            self.wipe()
            raise ValueError("assignment destinations must be mutable 32-byte buffers")

    def wipe(self) -> None:
        for buffer in self._buffers():
            if type(buffer) is bytearray:
                _wipe_bytearray(buffer)


def _u32(value: int, *, field: str) -> bytes:
    if type(value) is not int or not 0 <= value <= _MAX_U32:
        raise ValueError(f"{field} must fit one unsigned 32-bit integer")
    return value.to_bytes(4, "big")


def _text_payload(value: object, *, field: str) -> bytes:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value:
        raise ValueError(f"{field} must be non-empty")
    if unicodedata.normalize("NFC", value) != value:
        raise ValueError(f"{field} must already be NFC-normalized")
    if any(unicodedata.category(character).startswith("C") for character in value):
        raise ValueError(f"{field} contains a forbidden Unicode category")
    try:
        payload = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must be strict UTF-8 text") from exc
    if len(payload) > _MAX_U32:
        raise ValueError(f"{field} UTF-8 payload exceeds unsigned 32-bit length")
    return payload


def _field_payload(field: object) -> tuple[int, bytes]:
    if type(field) is U64Field:
        value = field.value
        if type(value) is not int:
            raise TypeError("U64 field value must be an integer")
        if not 0 <= value <= _MAX_U64:
            raise ValueError("U64 field value is outside the unsigned 64-bit range")
        return 0x01, value.to_bytes(8, "big")
    if type(field) is TextField:
        return 0x02, _text_payload(field.value, field="TEXT field value")
    if type(field) is BytesField:
        if type(field.value) is not bytes:
            raise TypeError("BYTES field value must be exact bytes")
        if len(field.value) > _MAX_U32:
            raise ValueError("BYTES field payload exceeds unsigned 32-bit length")
        return 0x03, field.value
    raise TypeError("frame field must be U64Field, TextField, or BytesField")


def kdf_frame(tag: str, fields: Sequence[FrameField]) -> bytes:
    """Encode one exact typed, length-prefixed derivation frame."""

    tag_payload = _text_payload(tag, field="frame tag")
    if not isinstance(fields, Sequence) or isinstance(
        fields,
        (str, bytes, bytearray),
    ):
        raise TypeError("frame fields must be a sequence of typed fields")
    field_count = len(fields)
    if field_count > _MAX_U32:
        raise ValueError("frame field count exceeds unsigned 32-bit range")
    frozen_fields = tuple(fields)
    if len(frozen_fields) != field_count:
        raise ValueError("frame field sequence differs from its declared count")

    encoded = bytearray(_FRAME_MAGIC)
    encoded.extend(_u32(len(tag_payload), field="frame tag length"))
    encoded.extend(tag_payload)
    encoded.extend(_u32(field_count, field="frame field count"))
    for field in frozen_fields:
        field_type, payload = _field_payload(field)
        encoded.append(field_type)
        encoded.extend(_u32(len(payload), field="frame field payload length"))
        encoded.extend(payload)
    return bytes(encoded)


def commitment_sha256(
    label: Literal[
        "roster-local-nonce",
        "schedule-seed",
        "assignment-master-key",
    ],
    study_id: str,
    value: U64Field | BytesField,
) -> str:
    """Return one representation- and purpose-bound commitment digest."""

    if type(label) is not str or label not in {
        "roster-local-nonce",
        "schedule-seed",
        "assignment-master-key",
    }:
        raise ValueError("commitment label is not recognized")
    if label == "schedule-seed":
        if type(value) is not U64Field:
            raise TypeError("schedule-seed commitment requires one U64 field")
    else:
        if type(value) is not BytesField:
            raise TypeError("roster/master commitment requires one BYTES field")
        if type(value.value) is not bytes or len(value.value) != 32:
            raise ValueError("roster/master commitment requires exactly 32 bytes")
    frame = kdf_frame(
        "commitment-v1",
        [TextField(label), TextField(study_id), value],
    )
    return hashlib.sha256(frame).hexdigest()


def derive_seed(schedule_seed: int, task_id: str, role: str) -> int:
    """Derive one deterministic unsigned 64-bit schedule seed."""

    return int.from_bytes(
        hashlib.sha256(
            kdf_frame(
                "derive-seed-v1",
                [
                    U64Field(schedule_seed),
                    TextField(task_id),
                    TextField(role),
                ],
            )
        ).digest()[:8],
        "big",
    )


def uniform_below(
    key: bytearray,
    message_frame: bytes,
    upper: int,
) -> UniformDraw:
    """Draw without modulo bias from one purpose-bound HMAC stream."""

    if type(upper) is not int or not 1 <= upper <= 2**64:
        raise ValueError("upper must be an integer in [1, 2**64]")
    if type(key) is not bytearray or len(key) != 32:
        raise ValueError("key must be one private mutable 32-byte buffer")
    if type(message_frame) is not bytes:
        raise TypeError("message frame must be exact bytes")
    limit = (1 << 64) - ((1 << 64) % upper)
    for counter in range(1 << 64):
        digest = hmac.new(
            key,
            kdf_frame(
                "uniform-below-v1",
                [BytesField(message_frame), U64Field(counter)],
            ),
            hashlib.sha256,
        ).digest()
        value = int.from_bytes(digest[:8], "big")
        if value < limit:
            return UniformDraw(value=value % upper, counter=counter)
    raise RuntimeError("64-bit rejection counter exhausted")


def _wipe_bytearray(buffer: bytearray) -> None:
    if type(buffer) is not bytearray:
        raise TypeError("wipe target must be a bytearray")
    for index in range(len(buffer)):
        buffer[index] = 0


def _read_exact_master_into(
    assignment_secret_handle: AssignmentSecretHandle | UnblindSecretHandle,
    destination: bytearray,
) -> None:
    """Read one assignment secret into an application-owned buffer."""

    if type(destination) is not bytearray:
        raise ValueError("master destination must be one mutable 32-byte buffer")
    if len(destination) != 32:
        _wipe_bytearray(destination)
        raise ValueError("master destination must be one mutable 32-byte buffer")
    try:
        _consume_assignment_handle_into(assignment_secret_handle, destination)
    except BaseException:
        _wipe_bytearray(destination)
        raise


def _require_master_view(assignment_master_key: memoryview) -> None:
    if (
        type(assignment_master_key) is not memoryview
        or assignment_master_key.readonly
        or assignment_master_key.nbytes != 32
        or assignment_master_key.itemsize != 1
        or not assignment_master_key.contiguous
        or type(assignment_master_key.obj) is not bytearray
        or len(assignment_master_key.obj) != 32
    ):
        raise ValueError("assignment master key must be one mutable 32-byte view")


def _assignment_context(
    study_id: str,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
) -> bytes:
    if type(manifest_ref) is not ArtifactRef or type(schedule_ref) is not ArtifactRef:
        raise TypeError("assignment context requires exact ArtifactRef values")
    return kdf_frame(
        "assignment-context-v1",
        [
            TextField(study_id),
            BytesField(bytes.fromhex(manifest_ref.sha256)),
            BytesField(bytes.fromhex(schedule_ref.sha256)),
        ],
    )


def _extract_assignment_prk_into(
    assignment_master_key: memoryview,
    study_id: str,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    destination: bytearray,
) -> None:
    _require_master_view(assignment_master_key)
    if type(destination) is not bytearray or len(destination) != 32:
        raise ValueError("PRK destination must be one mutable 32-byte buffer")
    context = _assignment_context(study_id, manifest_ref, schedule_ref)
    salt = hashlib.sha256(context).digest()
    destination[:] = hmac.new(
        salt,
        assignment_master_key,
        hashlib.sha256,
    ).digest()


def _expand_assignment_subkey_into(
    prk: bytearray,
    label: str,
    destination: bytearray,
) -> None:
    if type(prk) is not bytearray or len(prk) != 32:
        raise ValueError("PRK must be one private mutable 32-byte buffer")
    if type(label) is not str or label not in _SUBKEY_LABELS:
        raise ValueError("assignment subkey label is not recognized")
    if type(destination) is not bytearray or len(destination) != 32:
        raise ValueError("subkey destination must be one mutable 32-byte buffer")
    info = kdf_frame("assignment-subkey-v1", [TextField(label)])
    destination[:] = hmac.new(prk, info + b"\x01", hashlib.sha256).digest()


def _derive_assignment_subkeys_into(
    assignment_master_key: memoryview,
    study_id: str,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    destination: _AssignmentKeyBuffers,
) -> None:
    """Derive only the four assignment-purpose keys into mutable buffers."""

    if type(destination) is not _AssignmentKeyBuffers:
        raise TypeError("assignment destination must be private key buffers")
    destination._validate()
    prk = bytearray(32)
    try:
        _extract_assignment_prk_into(
            assignment_master_key,
            study_id,
            manifest_ref,
            schedule_ref,
            prk,
        )
        for label in ("donor", "allocation", "orientation", "capability"):
            _expand_assignment_subkey_into(
                prk,
                label,
                getattr(destination, label),
            )
    except BaseException:
        destination.wipe()
        raise
    finally:
        _wipe_bytearray(prk)


def _derive_unblind_subkey_into(
    assignment_master_key: memoryview,
    study_id: str,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    destination: bytearray,
) -> None:
    """Derive only the unblind-purpose key into one mutable buffer."""

    if type(destination) is not bytearray:
        raise ValueError("unblind destination must be one mutable 32-byte buffer")
    if len(destination) != 32:
        _wipe_bytearray(destination)
        raise ValueError("unblind destination must be one mutable 32-byte buffer")
    prk = bytearray(32)
    try:
        _extract_assignment_prk_into(
            assignment_master_key,
            study_id,
            manifest_ref,
            schedule_ref,
            prk,
        )
        _expand_assignment_subkey_into(prk, "unblind", destination)
    except BaseException:
        _wipe_bytearray(destination)
        raise
    finally:
        _wipe_bytearray(prk)


def _derive_pair_recovery_subkey_into(
    assignment_master_key: memoryview,
    study_id: str,
    manifest_ref: ArtifactRef,
    schedule_ref: ArtifactRef,
    destination: bytearray,
) -> None:
    """Derive the non-persisted Task-6 recovery authenticator."""
    if type(destination) is not bytearray or len(destination) != 32:
        raise ValueError("pair recovery destination must be one mutable 32-byte buffer")
    prk = bytearray(32)
    try:
        _extract_assignment_prk_into(assignment_master_key, study_id, manifest_ref, schedule_ref, prk)
        _expand_assignment_subkey_into(prk, "pair_recovery", destination)
    except BaseException:
        _wipe_bytearray(destination)
        raise
    finally:
        _wipe_bytearray(prk)


def _assignment_prefix_view_payload(view: AssignmentPrefixView) -> dict[str, object]:
    """Serialize only the authority-approved pre-treatment allowlist."""

    if type(view) is not AssignmentPrefixView:
        raise TypeError("prefix view must be an exact AssignmentPrefixView")
    return {
        "study_id": view.study_id,
        "schedule_sha256": view.schedule_sha256,
        "tasks": [
            {
                "task_id": task.task_id,
                "benchmark": task.benchmark,
                "stratum": task.stratum,
                "lineage": task.lineage,
                "sensitivity_groups": [
                    {"kind": group.kind.value, "value": group.value}
                    for group in task.sensitivity_groups
                ],
                "trigger_reason": task.trigger_reason.value,
                "verifier_component_class": task.verifier_component_class,
                "objective_finding_count": task.objective_finding_count,
                "normalized_report_token_count": (
                    task.normalized_report_token_count
                ),
                "telecom_issue_family": task.telecom_issue_family,
            }
            for task in view.tasks
        ],
    }


def assignment_prefix_view_sha256(view: AssignmentPrefixView) -> str:
    """Digest the closed allowlist without accepting outcome or branch fields."""

    from pneuma_lab.foundation.artifacts import canonical_json_bytes

    return hashlib.sha256(
        canonical_json_bytes(_assignment_prefix_view_payload(view), indent=None)
    ).hexdigest()


def _slot_capability(
    *,
    key: bytearray,
    study_id: str,
    manifest_sha256: str,
    schedule_sha256: str,
    prefix_index_sha256: str,
    task_id: str,
    slot_id: str,
    arm: Arm,
) -> str:
    if type(key) is not bytearray or len(key) != 32:
        raise ValueError("capability key must be one mutable 32-byte key")
    if not isinstance(arm, Arm):
        raise TypeError("capability arm must be an Arm")
    return hmac.new(
        key,
        kdf_frame(
            "slot-capability-v1",
            [
                TextField(study_id),
                BytesField(bytes.fromhex(manifest_sha256)),
                BytesField(bytes.fromhex(schedule_sha256)),
                BytesField(bytes.fromhex(prefix_index_sha256)),
                TextField(task_id),
                TextField(slot_id),
                TextField(arm.value),
            ],
        ),
        hashlib.sha256,
    ).hexdigest()


def _allocate_task(
    *,
    study_id: str,
    manifest_sha256: str,
    schedule_sha256: str,
    prefix_index_sha256: str,
    task_schedule: TaskSchedule,
    donor_task: AssignmentPrefixTaskView | None,
    allocation_key: bytearray,
    orientation_key: bytearray,
    capability_key: bytearray,
) -> tuple[TaskAssignment, AllocationReceipt]:
    """Apply the frozen 12-way table and independently oriented null pair."""

    for name, digest in (
        ("manifest_sha256", manifest_sha256),
        ("schedule_sha256", schedule_sha256),
        ("prefix_index_sha256", prefix_index_sha256),
    ):
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    for name, key in (
        ("allocation_key", allocation_key),
        ("orientation_key", orientation_key),
        ("capability_key", capability_key),
    ):
        if type(key) is not bytearray or len(key) != 32:
            raise ValueError(f"{name} must be one mutable 32-byte key")
    if type(task_schedule) is not TaskSchedule:
        raise TypeError("task_schedule must be an exact TaskSchedule")

    task = task_schedule.task
    slots = task_schedule.slots.slots
    slot_ids = cast(
        tuple[str, str, str, str],
        tuple(slot.slot_id for slot in slots),
    )
    allocation = uniform_below(
        allocation_key,
        kdf_frame("allocation-v1", [TextField(task.task_id)]),
        len(_ALLOCATION_TABLE),
    )
    treatments = _ALLOCATION_TABLE[allocation.value]
    no_packet_ordinals = [
        index
        for index, treatment in enumerate(treatments)
        if treatment is Treatment.NO_PACKET
    ]
    if len(no_packet_ordinals) != 2:
        raise AssertionError("frozen allocation table row lacks two null slots")
    orientation = uniform_below(
        orientation_key,
        kdf_frame("orientation-v1", [TextField(task.task_id)]),
        2,
    )
    null_arms = (
        (Arm.NONE, Arm.RESAMPLE)
        if orientation.value == 0
        else (Arm.RESAMPLE, Arm.NONE)
    )
    arms: list[Arm] = []
    for ordinal, treatment in enumerate(treatments):
        if treatment is Treatment.REAL:
            arms.append(Arm.REAL)
        elif treatment is Treatment.SHAM:
            arms.append(Arm.SHAM)
        else:
            arms.append(
                null_arms[no_packet_ordinals.index(ordinal)]
            )

    capabilities: list[tuple[str, str]] = []
    for slot_id, arm in zip(slot_ids, arms, strict=True):
        capability = _slot_capability(
            key=capability_key,
            study_id=study_id,
            manifest_sha256=manifest_sha256,
            schedule_sha256=schedule_sha256,
            prefix_index_sha256=prefix_index_sha256,
            task_id=task.task_id,
            slot_id=slot_id,
            arm=arm,
        )
        capabilities.append((slot_id, capability))

    assignment = TaskAssignment(
        task_id=task.task_id,
        task_lineage=task.lineage,
        donor_match_kind=(
            "not_applicable_no_trigger" if donor_task is None else "matched"
        ),
        donor_task_id=None if donor_task is None else donor_task.task_id,
        donor_lineage=None if donor_task is None else donor_task.lineage,
        slot_arms=tuple(zip(slot_ids, arms, strict=True)),
        schedule_sha256=schedule_sha256,
        prefix_index_sha256=prefix_index_sha256,
    )
    receipt = AllocationReceipt(
        task_id=task.task_id,
        slot_ids_by_ordinal=slot_ids,
        treatment_allocation_index=allocation.value,
        allocation_rejection_counter=allocation.counter,
        no_packet_orientation_bit=orientation.value,
        orientation_rejection_counter=orientation.counter,
        slot_capabilities=tuple(capabilities),
    )
    return assignment, receipt


def _solve_synthetic_stratum(
    *,
    tasks: tuple[AssignmentPrefixTaskView, ...],
    stratum_key: tuple[str, ...],
    assignment_prefix_view_sha256: str,
    assignment_program_sha256: str,
    donor_key: bytearray,
) -> tuple[dict[str, object], dict[str, AssignmentPrefixTaskView]]:
    """Return the first valid frozen cyclic offset and its complete audit proof."""

    if type(donor_key) is not bytearray or len(donor_key) != 32:
        raise ValueError("donor_key must be one mutable 32-byte key")
    if not isinstance(tasks, tuple) or not all(
        type(task) is AssignmentPrefixTaskView for task in tasks
    ):
        raise TypeError("tasks must be a tuple of exact prefix-task views")
    if (
        not isinstance(stratum_key, tuple)
        or not stratum_key
        or not all(type(component) is str and component for component in stratum_key)
    ):
        raise ValueError("stratum_key must be a non-empty strict-text tuple")
    for name, digest in (
        ("assignment_prefix_view_sha256", assignment_prefix_view_sha256),
        ("assignment_program_sha256", assignment_program_sha256),
    ):
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    triggered = tuple(
        task
        for task in tasks
        if task.trigger_reason is not TriggerReason.NO_INTERVENTION_OPPORTUNITY
    )
    if len({task.lineage for task in triggered}) < 3:
        raise RecordValidationError(
            "synthetic triggered stratum requires at least three lineages"
        )
    canonical = tuple(sorted(triggered, key=lambda task: task.task_id.encode("utf-8")))
    ordered = tuple(
        sorted(
            canonical,
            key=lambda task: (
                hmac.new(
                    donor_key,
                    kdf_frame(
                        "synthetic-order-v1",
                        [
                            BytesField(
                                bytes.fromhex(assignment_prefix_view_sha256)
                            ),
                            *(TextField(component) for component in stratum_key),
                            TextField(task.task_id),
                        ],
                    ),
                    hashlib.sha256,
                ).digest(),
                task.task_id.encode("utf-8"),
            ),
        )
    )
    cycle_rows = [
        {
            "order_hmac_sha256": hmac.new(
                donor_key,
                kdf_frame(
                    "synthetic-order-v1",
                    [
                        BytesField(bytes.fromhex(assignment_prefix_view_sha256)),
                        *(TextField(component) for component in stratum_key),
                        TextField(task.task_id),
                    ],
                ),
                hashlib.sha256,
            ).hexdigest(),
            "task_id": task.task_id,
        }
        for task in ordered
    ]
    trials: list[dict[str, object]] = []
    selected: dict[str, AssignmentPrefixTaskView] | None = None
    selected_offset: int | None = None
    for offset in range(1, len(ordered)):
        candidate = {
            focal.task_id: ordered[(index + offset) % len(ordered)]
            for index, focal in enumerate(ordered)
        }
        failure: str | None = None
        for focal in canonical:
            donor = candidate[focal.task_id]
            if focal.lineage == donor.lineage:
                failure = "same_lineage"
                break
            if candidate[donor.task_id].task_id == focal.task_id:
                failure = "reciprocal_two_cycle"
                break
        valid = failure is None
        trials.append(
            {"failure_code": failure, "offset": offset, "valid": valid}
        )
        if valid:
            selected = candidate
            selected_offset = offset
            break
    if selected is None or selected_offset is None:
        raise RecordValidationError("synthetic stratum has no valid cyclic offset")
    proof: dict[str, object] = {
        "assignment_prefix_view_sha256": assignment_prefix_view_sha256,
        "assignment_program_sha256": assignment_program_sha256,
        "canonical_focal_task_ids": [task.task_id for task in canonical],
        "cycle_order": cycle_rows,
        "donor_by_task": [
            [task.task_id, selected[task.task_id].task_id] for task in canonical
        ],
        "invocation_receipt_refs": [],
        "offset_trials": trials,
        "proof_kind": "synthetic_cyclic_offset_v1",
        "schema_version": "1",
        "selected_offset": selected_offset,
        "stratum_key": list(stratum_key),
    }
    return proof, selected
