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


_FRAME_MAGIC = b"pneuma-resampling-null-frame-v1\x00"
_MAX_U32 = 2**32 - 1
_MAX_U64 = 2**64 - 1
_SUBKEY_LABELS = frozenset(
    {"donor", "allocation", "orientation", "capability", "unblind"}
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
