"""Sealed opaque packet capabilities for isolated branch workers.

The trusted preparer is the only component that may hold a clear
``TaskAssignment`` together with a ``PacketPairReceipt``.  This module turns
that clear pair into per-slot *opaque capabilities*: a preregistered-order
four-tuple in which each slot is named only by its allocation capability digest
and carries at most a generic private-guidance reference.

Two independent gates protect the worker boundary:

- every worker-visible guidance path must be the canonical name derived from
  ``(task_id, opaque_capability_id)`` alone, so a REAL packet cannot be handed
  to the slot that was allocated SHAM without detection; and
- every worker-visible guidance path must be arm-opaque, so the filename itself
  cannot spell ``real``/``sham``/``none``/``resample``.

Nothing here reads outcomes, grades, or the analysis freeze.  The resolution is
in-memory only: no new scientific record is published, because the sealed
packet index already is the published execution authority and a second sealed
mapping would create a competing authority for the same fact.

**What this layer does and does not hide.**  The registered property is
peer-slot and donor opacity, not self-arm opacity.  A packet-bearing worker
reads its own packet text — that text *is* the intervention — so it
necessarily observes whether it received applicable or structure-only
evidence, exactly as a real subject would.  What a worker must never obtain is
another slot's arm, the donor task, the clear assignment ledger, the packet
candidate index, or a peer slot's snapshot.  This module enforces that by
naming every worker-visible packet from its own capability digest alone and by
closing the worker's read authority to a role-restricted reference set.

The REAL/SHAM contrast is protected downstream instead: the packet builder
enforces exact token parity, schema/field/severity parity, and donor-identifier
rewriting, so arm membership cannot be read off a worker's resource counters.
Byte counts and digests of the two packets still differ, which is why they are
never published in an arm-labelled position and never reach the blinded
projection.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat

from .authority_refs import decode_artifact_ref, load_json_bytes
from .errors import RecordValidationError
from .types import ArtifactRef


GUIDANCE_ROLE = "private_guidance"
GUIDANCE_MEDIA_TYPE = "text/plain"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ARMS = ("REAL", "SHAM", "NONE", "RESAMPLE")
_ARM_WORDS = ("real", "sham", "none", "resample")
CANONICAL_GUIDANCE_PATH = re.compile(
    r"^packet-work/[0-9a-f]{64}/guidance-[0-9a-f]{64}\.txt$"
)
_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_CLOEXEC", 0)
)

# Every closed role a slot worker may ever be authorized to read.  Scientific
# record roles are absent by construction, so no capability can widen into the
# assignment ledger, either packet index, or the analysis freeze.
WORKER_READABLE_ROLES = frozenset(
    {
        "composite_snapshot",
        "environment_snapshot",
        "private_guidance",
        "synthetic_execution_program",
        "synthetic_grade_result",
        "synthetic_provider_event",
        "synthetic_request",
        "synthetic_response",
        "synthetic_tool_result",
        "synthetic_verifier_result",
        "task_input",
        "token_ids",
        "tool_schema",
        "visible_context",
    }
)


def require_arm_opaque_relative_path(relative_path: str, *, field: str) -> str:
    """Reject a worker-visible path that spells an arm anywhere.

    A plain substring test is safe here and strictly stronger than a
    delimiter-bounded one: every arm word contains at least one character
    outside ``[0-9a-f]``, so no capability digest, task slug, or lowercase hex
    component can ever contain one by accident.
    """

    if type(relative_path) is not str or not relative_path:
        raise RecordValidationError(f"{field} must be non-empty exact text")
    lowered = relative_path.lower()
    if any(word in lowered for word in _ARM_WORDS):
        raise RecordValidationError(f"{field} must be arm-opaque")
    return relative_path


def require_canonical_guidance_path(relative_path: str, *, field: str) -> str:
    """Require the single closed shape a worker-visible packet name may take."""

    require_arm_opaque_relative_path(relative_path, field=field)
    if CANONICAL_GUIDANCE_PATH.fullmatch(relative_path) is None:
        raise RecordValidationError(f"{field} is not a canonical guidance name")
    return relative_path


def opaque_guidance_relative_path(task_id: str, opaque_capability_id: str) -> str:
    """Return the only worker-visible packet name a capability may occupy.

    The name is a pure function of the task identity and the allocation
    capability digest, so the preparer cannot silently redirect one slot's
    capability at another slot's packet bytes.
    """

    if type(task_id) is not str or not task_id:
        raise RecordValidationError("task_id must be non-empty exact text")
    if type(opaque_capability_id) is not str or not _SHA256.fullmatch(
        opaque_capability_id
    ):
        raise RecordValidationError(
            "opaque_capability_id must be lowercase SHA-256 hexadecimal"
        )
    slug = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
    return f"packet-work/{slug}/guidance-{opaque_capability_id}.txt"


@dataclass(frozen=True, slots=True)
class OpaqueSlotGrant:
    """One preregistered slot position with no arm, donor, or peer identity."""

    slot_id: str
    opaque_capability_id: str
    guidance_ref: ArtifactRef | None

    def __post_init__(self) -> None:
        if type(self.slot_id) is not str or not self.slot_id:
            raise RecordValidationError("slot_id must be non-empty exact text")
        if type(self.opaque_capability_id) is not str or not _SHA256.fullmatch(
            self.opaque_capability_id
        ):
            raise RecordValidationError(
                "opaque_capability_id must be lowercase SHA-256 hexadecimal"
            )
        if self.guidance_ref is None:
            return
        if type(self.guidance_ref) is not ArtifactRef:
            raise RecordValidationError("guidance_ref must be ArtifactRef or None")
        if self.guidance_ref.role != GUIDANCE_ROLE:
            raise RecordValidationError("guidance_ref must use the private_guidance role")
        if self.guidance_ref.media_type != GUIDANCE_MEDIA_TYPE:
            raise RecordValidationError("guidance_ref media type is not registered")
        require_canonical_guidance_path(
            self.guidance_ref.relative_path,
            field="guidance_ref relative_path",
        )
        # The canonical name commits to a hashed task id and to the capability
        # digest.  A grant can check the capability half locally; the full
        # ``(task_id, capability)`` comparison happens in resolution, which is
        # the only place the clear task id is available.
        if not self.guidance_ref.relative_path.endswith(
            f"/guidance-{self.opaque_capability_id}.txt"
        ):
            raise RecordValidationError(
                "guidance_ref is not bound to this slot's capability digest"
            )


@dataclass(frozen=True, slots=True)
class TaskPacketCapabilities:
    """The four opaque slot grants for one scheduled task."""

    task_id: str
    triggered: bool
    grants: tuple[OpaqueSlotGrant, OpaqueSlotGrant, OpaqueSlotGrant, OpaqueSlotGrant]

    def __post_init__(self) -> None:
        if type(self.task_id) is not str or not self.task_id:
            raise RecordValidationError("task_id must be non-empty exact text")
        if type(self.triggered) is not bool:
            raise RecordValidationError("triggered must be exact bool")
        if type(self.grants) is not tuple or len(self.grants) != 4:
            raise RecordValidationError("grants must be an exact four-tuple")
        if any(type(grant) is not OpaqueSlotGrant for grant in self.grants):
            raise RecordValidationError("grants must contain exact OpaqueSlotGrant records")
        slot_ids = [grant.slot_id for grant in self.grants]
        capabilities = [grant.opaque_capability_id for grant in self.grants]
        if len(set(slot_ids)) != 4 or len(set(capabilities)) != 4:
            raise RecordValidationError("grants must name four distinct opaque slots")
        granted = sum(grant.guidance_ref is not None for grant in self.grants)
        if self.triggered and granted != 2:
            raise RecordValidationError(
                "a triggered task must grant exactly two packet-bearing slots"
            )
        if not self.triggered and granted:
            raise RecordValidationError(
                "an untriggered task must grant no packet-bearing slot"
            )
        paths = [
            grant.guidance_ref.relative_path
            for grant in self.grants
            if grant.guidance_ref is not None
        ]
        if len(set(paths)) != len(paths):
            raise RecordValidationError("granted slots must not share one packet path")

    def grant_for(self, opaque_capability_id: str) -> OpaqueSlotGrant:
        """Return the single grant a capability owns, or fail closed."""

        matches = [
            grant
            for grant in self.grants
            if grant.opaque_capability_id == opaque_capability_id
        ]
        if len(matches) != 1:
            raise RecordValidationError("capability does not own exactly one slot")
        return matches[0]


class _RootBoundReader:
    """Read run-root artifacts by reference with mandatory byte verification.

    ``AuthorityRefReader`` is deliberately confined to the copied ``sources/``
    authority namespace, so it cannot read packet or controller artifacts.  This
    reader keeps the guarantees that matter here:

    - the run root is pinned to one directory *descriptor* at construction, so
      renaming or replacing the root pathname afterwards cannot redirect a read;
    - every path component is opened with ``O_NOFOLLOW`` relative to the
      previous component's descriptor, so no symlink — planted before or during
      the walk — can leave the root; and
    - bytes must reproduce the reference digest and length.

    A hardlink inside the root to an outside inode is still readable.  That is
    accepted: the reference pins the exact bytes, so an attacker who can plant
    such a link already knows the content it would disclose.  Defeating an
    adversary who can rewrite the whole local root is out of the documented
    trusted-run-root threat model and needs signing custody, not a path check.
    """

    __slots__ = ("_root_fd", "_run_root")

    def __init__(self, run_root: Path) -> None:
        self._run_root = Path(run_root)
        try:
            self._root_fd: int | None = os.open(
                self._run_root, _DIRECTORY_FLAGS
            )
        except OSError as exc:
            raise RecordValidationError(f"run_root is not readable: {exc}") from exc
        try:
            if not stat.S_ISDIR(os.fstat(self._root_fd).st_mode):
                raise RecordValidationError("run_root must be a directory")
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        descriptor = self._root_fd
        self._root_fd = None
        if descriptor is not None:
            os.close(descriptor)

    def __enter__(self) -> _RootBoundReader:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def read_bytes(self, ref: ArtifactRef) -> bytes:
        if type(ref) is not ArtifactRef:
            raise RecordValidationError("read requires an exact ArtifactRef")
        if self._root_fd is None:
            raise RecordValidationError("root-bound reader is closed")
        parts = PurePosixPath(ref.relative_path).parts
        if not parts or any(part in ("", ".", "..") for part in parts):
            raise RecordValidationError(
                f"artifact_ref is not a normalized relative path: "
                f"{ref.relative_path!r}"
            )
        opened: list[int] = []
        try:
            parent = self._root_fd
            for part in parts[:-1]:
                descriptor = os.open(part, _DIRECTORY_FLAGS, dir_fd=parent)
                opened.append(descriptor)
                parent = descriptor
            file_descriptor = os.open(
                parts[-1],
                os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | os.O_CLOEXEC,
                dir_fd=parent,
            )
            opened.append(file_descriptor)
            with os.fdopen(file_descriptor, "rb", closefd=False) as handle:
                payload = handle.read()
        except OSError as exc:
            raise RecordValidationError(
                f"unreadable artifact_ref {ref.relative_path!r}: {exc}"
            ) from exc
        finally:
            for descriptor in reversed(opened):
                os.close(descriptor)
        if (
            len(payload) != ref.byte_count
            or hashlib.sha256(payload).hexdigest() != ref.sha256
        ):
            raise RecordValidationError(
                f"artifact_ref bytes mismatch: {ref.relative_path!r}"
            )
        return payload


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must be a JSON object")
    return value


def _sequence(value: object, *, field: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise RecordValidationError(f"{field} must be a JSON array")
    return value


_ENVELOPE_FIELDS = frozenset(
    {
        "record_kind",
        "schema_version",
        "study_id",
        "frozen_created_at",
        "provenance",
        "payload",
    }
)


def _record(
    reader: _RootBoundReader,
    ref: ArtifactRef,
    *,
    kind: str,
    role: str,
    field: str,
    stage: str | None = None,
) -> Mapping[str, object]:
    if ref.role != role:
        raise RecordValidationError(f"{field} must use the {role} role")
    if ref.media_type != "application/json":
        raise RecordValidationError(f"{field} must be canonical JSON")
    payload = reader.read_bytes(ref)
    value = load_json_bytes(payload, source=Path(ref.relative_path))
    record = _mapping(value, field=field)
    if set(record) != _ENVELOPE_FIELDS:
        raise RecordValidationError(f"{field} envelope has an unregistered shape")
    if record.get("record_kind") != kind:
        raise RecordValidationError(f"{field} is not a {kind} record")
    if record.get("schema_version") != "0.1.0":
        raise RecordValidationError(f"{field} schema_version is not registered")
    for name in ("study_id", "frozen_created_at"):
        item = record.get(name)
        if type(item) is not str or not item:
            raise RecordValidationError(f"{field} {name} is malformed")
    _mapping(record.get("provenance"), field=f"{field} provenance")
    body = _mapping(record.get("payload"), field=f"{field} payload")
    if stage is not None and body.get("stage") != stage:
        raise RecordValidationError(f"{field} is not at stage {stage}")
    return record


def _require_same_identity(
    left: Mapping[str, object],
    right: Mapping[str, object],
    *,
    left_name: str,
    right_name: str,
) -> None:
    for field in ("study_id", "frozen_created_at", "provenance"):
        if left.get(field) != right.get(field):
            raise RecordValidationError(
                f"{left_name} {field} differs from {right_name}"
            )


def _slot_order(allocation: Mapping[str, object], *, task_id: str) -> tuple[
    tuple[str, str], tuple[str, str], tuple[str, str], tuple[str, str],
]:
    """Return preregistered ``(slot_id, capability)`` pairs in ordinal order."""

    if allocation.get("task_id") != task_id:
        raise RecordValidationError("allocation receipt names a different task")
    ordinals = _sequence(
        allocation.get("slot_ids_by_ordinal"), field="slot_ids_by_ordinal"
    )
    capabilities = _sequence(
        allocation.get("slot_capabilities"), field="slot_capabilities"
    )
    if len(ordinals) != 4 or len(capabilities) != 4:
        raise RecordValidationError("allocation receipt must close exactly four slots")
    pairs: list[tuple[str, str]] = []
    for index, (slot_id, entry) in enumerate(zip(ordinals, capabilities, strict=True)):
        if type(slot_id) is not str or not slot_id:
            raise RecordValidationError(f"slot_ids_by_ordinal[{index}] is malformed")
        if (
            not isinstance(entry, list)
            or len(entry) != 2
            or entry[0] != slot_id
            or type(entry[1]) is not str
            or not _SHA256.fullmatch(entry[1])
        ):
            raise RecordValidationError(f"slot_capabilities[{index}] is malformed")
        pairs.append((slot_id, entry[1]))
    if len({pair[0] for pair in pairs}) != 4 or len({pair[1] for pair in pairs}) != 4:
        raise RecordValidationError("allocation receipt slots must be distinct")
    return (pairs[0], pairs[1], pairs[2], pairs[3])


def _arm_slots(assignment: Mapping[str, object], *, task_id: str) -> dict[str, str]:
    if assignment.get("task_id") != task_id:
        raise RecordValidationError("assignment row names a different task")
    rows = _sequence(assignment.get("slot_arms"), field="slot_arms")
    if len(rows) != 4:
        raise RecordValidationError("slot_arms must close exactly four arms")
    arms: dict[str, str] = {}
    for index, entry in enumerate(rows):
        if (
            not isinstance(entry, list)
            or len(entry) != 2
            or type(entry[0]) is not str
            or not entry[0]
            or entry[1] not in _ARMS
            or entry[1] in arms
        ):
            raise RecordValidationError(f"slot_arms[{index}] is malformed")
        arms[entry[1]] = entry[0]
    if set(arms) != set(_ARMS):
        raise RecordValidationError("slot_arms must assign every arm exactly once")
    return arms


_MARKER_ENTRY_FIELDS = frozenset({"task_id", "prefix_index_sha256", "trigger_reason"})
_REQUIRED_PAIR_ENTRY_FIELDS = frozenset(
    {"task_id", "donor_task_id", "prefix_index_sha256", "real_ref", "sham_ref"}
)


def _guidance_ref(
    entry: Mapping[str, object],
    *,
    field: str,
    task_id: str,
    opaque_capability_id: str,
    reader: _RootBoundReader,
) -> ArtifactRef:
    ref = decode_artifact_ref(entry.get(field), field=f"packet entry {field}")
    if ref.role != GUIDANCE_ROLE or ref.media_type != GUIDANCE_MEDIA_TYPE:
        raise RecordValidationError(f"packet entry {field} is not private guidance")
    require_canonical_guidance_path(
        ref.relative_path, field=f"packet entry {field} relative_path"
    )
    expected = opaque_guidance_relative_path(task_id, opaque_capability_id)
    if ref.relative_path != expected:
        raise RecordValidationError(
            f"packet entry {field} is not bound to its allocated slot capability"
        )
    # A grant must not name bytes that are absent or already substituted; the
    # read verifies existence, length, and digest before the slot is issued.
    reader.read_bytes(ref)
    return ref


def resolve_packet_capabilities(
    *,
    packet_index_ref: ArtifactRef,
    run_root: Path,
) -> tuple[TaskPacketCapabilities, ...]:
    """Resolve every task's four opaque slot grants from sealed authority.

    Only the trusted preparer may call this: it reads the clear assignment
    ledger.  The returned records contain no arm, donor, treatment, packet
    token count, or peer-slot identity, and are never written to the run root.
    """

    with _RootBoundReader(run_root) as reader:
        return _resolve(reader, packet_index_ref)


def _resolve(
    reader: _RootBoundReader,
    packet_index_ref: ArtifactRef,
) -> tuple[TaskPacketCapabilities, ...]:
    sealed = _record(
        reader,
        packet_index_ref,
        kind="resampling_packet_index",
        role="packet_index_sealed",
        field="sealed packet index",
        stage="sealed",
    )
    sealed_payload = _mapping(sealed["payload"], field="sealed packet payload")
    candidate_ref = decode_artifact_ref(
        sealed_payload.get("candidate_ref"), field="sealed candidate_ref"
    )
    assignment_ref = decode_artifact_ref(
        sealed_payload.get("assignment_ref"), field="sealed assignment_ref"
    )
    prefix_index_ref = decode_artifact_ref(
        sealed_payload.get("prefix_index_ref"), field="sealed prefix_index_ref"
    )
    candidate = _record(
        reader,
        candidate_ref,
        kind="resampling_packet_index",
        role="packet_index_candidate",
        field="packet candidate index",
        stage="candidate",
    )
    candidate_payload = _mapping(candidate["payload"], field="packet candidate payload")
    for field in ("assignment_ref", "prefix_index_ref"):
        expected = assignment_ref if field == "assignment_ref" else prefix_index_ref
        if decode_artifact_ref(
            candidate_payload.get(field), field=f"candidate {field}"
        ) != expected:
            raise RecordValidationError(
                f"sealed and candidate packet indexes disagree on {field}"
            )
    assignment = _record(
        reader,
        assignment_ref,
        kind="resampling_assignment_ledger",
        role="resampling_assignment_ledger",
        field="assignment ledger",
    )
    assignment_payload = _mapping(
        assignment["payload"], field="assignment ledger payload"
    )
    _require_same_identity(
        sealed,
        assignment,
        left_name="sealed packet index",
        right_name="its assignment ledger",
    )
    _require_same_identity(
        candidate,
        sealed,
        left_name="packet candidate index",
        right_name="its sealed packet index",
    )
    if decode_artifact_ref(
        assignment_payload.get("prefix_index_ref"), field="ledger prefix_index_ref"
    ) != prefix_index_ref:
        raise RecordValidationError(
            "assignment ledger names a different prefix index than the packet index"
        )

    entries = _sequence(candidate_payload.get("entries"), field="candidate entries")
    assignments = _sequence(
        assignment_payload.get("assignments"), field="ledger assignments"
    )
    allocations = _sequence(
        assignment_payload.get("allocation_receipts"), field="ledger allocations"
    )
    if len(assignments) != len(allocations):
        raise RecordValidationError("ledger assignment and allocation arrays differ")
    order = [_mapping(row, field="assignment row").get("task_id") for row in assignments]
    by_task = {}
    for entry in entries:
        row = _mapping(entry, field="packet entry")
        task_id = row.get("task_id")
        if type(task_id) is not str or not task_id or task_id in by_task:
            raise RecordValidationError("packet entries must have unique task IDs")
        by_task[task_id] = row
    if list(by_task) != order:
        raise RecordValidationError(
            "packet entries must follow the frozen assignment task order"
        )

    resolved: list[TaskPacketCapabilities] = []
    for assignment_row, allocation_row in zip(assignments, allocations, strict=True):
        row = _mapping(assignment_row, field="assignment row")
        allocation = _mapping(allocation_row, field="allocation receipt")
        task_id = row["task_id"]
        if type(task_id) is not str or not task_id:
            raise RecordValidationError("assignment row task_id is malformed")
        entry = by_task[task_id]
        ordered = _slot_order(allocation, task_id=task_id)
        arm_slots = _arm_slots(row, task_id=task_id)
        capability_by_slot = {slot_id: capability for slot_id, capability in ordered}
        if set(capability_by_slot) != set(arm_slots.values()):
            raise RecordValidationError(
                "assignment and allocation receipts name different slots"
            )
        if entry.get("prefix_index_sha256") != prefix_index_ref.sha256:
            raise RecordValidationError(
                "packet entry names a different prefix index than its sealed parent"
            )
        marker = "trigger_reason" in entry
        if marker:
            # A marker must be exactly a marker: a no-trigger entry that also
            # carried packet references would silently discard a real packet.
            if set(entry) != _MARKER_ENTRY_FIELDS:
                raise RecordValidationError(
                    "no-intervention packet marker has an unregistered shape"
                )
            if entry.get("trigger_reason") != "no_intervention_opportunity":
                raise RecordValidationError(
                    "packet entry trigger_reason is not registered"
                )
            if row.get("donor_match_kind") != "not_applicable_no_trigger":
                raise RecordValidationError(
                    "no-intervention packet marker contradicts its assignment donor"
                )
            grants = tuple(
                OpaqueSlotGrant(slot_id, capability, None)
                for slot_id, capability in ordered
            )
            resolved.append(TaskPacketCapabilities(task_id, False, grants))
            continue
        if not _REQUIRED_PAIR_ENTRY_FIELDS <= set(entry):
            raise RecordValidationError("packet pair entry is missing a required field")
        if row.get("donor_match_kind") != "matched":
            raise RecordValidationError(
                "a packet pair requires a matched donor assignment"
            )
        if entry.get("donor_task_id") != row.get("donor_task_id"):
            raise RecordValidationError(
                "packet entry donor differs from its sealed assignment donor"
            )
        real_slot = arm_slots["REAL"]
        sham_slot = arm_slots["SHAM"]
        granted = {
            real_slot: _guidance_ref(
                entry,
                field="real_ref",
                task_id=task_id,
                opaque_capability_id=capability_by_slot[real_slot],
                reader=reader,
            ),
            sham_slot: _guidance_ref(
                entry,
                field="sham_ref",
                task_id=task_id,
                opaque_capability_id=capability_by_slot[sham_slot],
                reader=reader,
            ),
        }
        grants = tuple(
            OpaqueSlotGrant(slot_id, capability, granted.get(slot_id))
            for slot_id, capability in ordered
        )
        resolved.append(TaskPacketCapabilities(task_id, True, grants))
    return tuple(resolved)


@dataclass(frozen=True, slots=True)
class SealedSlotCapability:
    """The complete closed read authority one isolated slot worker receives.

    The role allowlist is the structural guard: no capability — issued by
    mistake, by a future caller, or by a compromised preparer path — can name a
    scientific record, because no scientific role is in
    ``WORKER_READABLE_ROLES``.  At most one guidance artifact may appear, and it
    must carry this capability's own digest in its canonical name.
    """

    opaque_capability_id: str
    readable_refs: tuple[ArtifactRef, ...]

    def __post_init__(self) -> None:
        if type(self.opaque_capability_id) is not str or not _SHA256.fullmatch(
            self.opaque_capability_id
        ):
            raise RecordValidationError(
                "opaque_capability_id must be lowercase SHA-256 hexadecimal"
            )
        if type(self.readable_refs) is not tuple or not self.readable_refs:
            raise RecordValidationError("readable_refs must be a non-empty tuple")
        if any(type(ref) is not ArtifactRef for ref in self.readable_refs):
            raise RecordValidationError("readable_refs must contain ArtifactRef records")
        paths = [ref.relative_path for ref in self.readable_refs]
        if len(set(paths)) != len(paths):
            raise RecordValidationError("readable_refs must name distinct artifacts")
        guidance = 0
        for ref in self.readable_refs:
            if ref.role not in WORKER_READABLE_ROLES:
                raise RecordValidationError(
                    f"role {ref.role!r} may never be readable by a slot worker"
                )
            if ref.role != GUIDANCE_ROLE:
                continue
            guidance += 1
            require_canonical_guidance_path(
                ref.relative_path, field="readable guidance relative_path"
            )
            if not ref.relative_path.endswith(
                f"/guidance-{self.opaque_capability_id}.txt"
            ):
                raise RecordValidationError(
                    "readable guidance must carry this capability's own digest"
                )
        if guidance > 1:
            raise RecordValidationError("a slot may read at most one guidance artifact")


def seal_slot_capability(
    work_order: object,
    *,
    additional_refs: Sequence[ArtifactRef] = (),
) -> SealedSlotCapability:
    """Derive a worker's read authority from its own work order.

    The capability is not an independent input: everything it authorizes is
    either named by the order itself or an explicitly supplied execution asset
    that must still pass the role allowlist.  This is the only sanctioned way
    to build a ``SealedSlotCapability``; the dataclass constructor stays
    validated so a hand-built one cannot widen past the same gates.
    """

    from .types import OpaqueSlotWorkOrder

    if type(work_order) is not OpaqueSlotWorkOrder:
        raise RecordValidationError("work_order must be exact OpaqueSlotWorkOrder")
    refs: list[ArtifactRef] = [work_order.snapshot_ref]
    if work_order.private_guidance_ref is not None:
        refs.append(work_order.private_guidance_ref)
    for ref in additional_refs:
        if type(ref) is not ArtifactRef:
            raise RecordValidationError("additional_refs must contain ArtifactRef records")
        if ref.role == GUIDANCE_ROLE:
            raise RecordValidationError(
                "guidance authority comes only from the work order"
            )
        refs.append(ref)
    return SealedSlotCapability(
        work_order.slot.opaque_capability_id,
        tuple(refs),
    )


class SlotArtifactLoader:
    """Read capability closed to exactly one worker's sealed reference set.

    The loader is the only artifact door a slot worker has.  It refuses any
    reference outside its sealed capability, so a worker cannot reach the clear
    assignment ledger, the packet candidate index, a donor map, or a peer
    slot's snapshot even if it learns their names.
    """

    __slots__ = ("_capability", "_reader", "_permitted", "_run_root")

    def __init__(self, capability: SealedSlotCapability, *, run_root: Path) -> None:
        if type(capability) is not SealedSlotCapability:
            raise RecordValidationError("capability must be exact SealedSlotCapability")
        self._capability = capability
        self._permitted = frozenset(capability.readable_refs)
        self._run_root = Path(run_root)
        self._reader: _RootBoundReader | None = None

    def __enter__(self) -> SlotArtifactLoader:
        self._reader = _RootBoundReader(self._run_root)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._reader = None

    @property
    def opaque_capability_id(self) -> str:
        return self._capability.opaque_capability_id

    def read_bytes(self, ref: ArtifactRef) -> bytes:
        """Return verified bytes for a sealed reference; refuse everything else."""

        if type(ref) is not ArtifactRef:
            raise RecordValidationError("slot read requires an exact ArtifactRef")
        if ref not in self._permitted:
            raise RecordValidationError(
                "slot capability does not authorize this artifact"
            )
        reader = self._reader
        if reader is None:
            raise RecordValidationError("slot loader is not open")
        return reader.read_bytes(ref)


__all__ = [
    "GUIDANCE_MEDIA_TYPE",
    "GUIDANCE_ROLE",
    "OpaqueSlotGrant",
    "SealedSlotCapability",
    "SlotArtifactLoader",
    "TaskPacketCapabilities",
    "WORKER_READABLE_ROLES",
    "opaque_guidance_relative_path",
    "require_arm_opaque_relative_path",
    "require_canonical_guidance_path",
    "resolve_packet_capabilities",
    "seal_slot_capability",
]
