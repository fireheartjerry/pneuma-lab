"""Isolated per-slot branch execution for one opaque work order.

This module is the worker side of Task-5 branch execution.  It is deliberately
the *only* component that runs a branch subject, and it is deliberately unable
to grade one: ``run_opaque_slot`` returns an ``UnscoredSlotReceipt`` whose
``endpoint_readable`` field is structurally ``False``, so a worker cannot leak
an outcome back into arm allocation.  Grading is a separate, later, read-only
pass (``grade_opaque_slot``) that spawns a fresh disposable environment.

Trust boundary.  A worker never receives clear authority.  Everything it may
read is derived from its own ``OpaqueSlotWorkOrder`` through
``seal_slot_capability``, in three widening stages, each stage authorized only
by bytes the previous stage already verified:

1. the work order alone (plus the two execution assets the controller names) —
   enough to read the frozen composite prefix snapshot record;
2. the three artifact references *decoded out of that snapshot* — the
   environment snapshot, the visible context, and the token-id projection —
   enough to restore the environment and load the sealed program; and
3. the request references *decoded out of that program* — enough to prove each
   rendered model request byte-for-byte against its sealed expectation.

No stage takes a reference from a caller argument that the previous stage did
not already commit to, so a caller cannot widen a worker's read authority by
handing it a peer slot's snapshot or a donor's packet.

Order of operations is the scientific claim.  The environment is restored and
*then* verified — snapshot identity, visible-context digest, and token-id
digest — before the subject is allowed to emit a single turn.  Only after the
frozen pending prefix tool calls have drained does the branch record its
``pre_injection`` digests; those are the four-way equality the attempt sealer
later checks, and they would be meaningless if the subject had already acted.

Registered deviations from the abstract contract, all forced by the worker
read boundary:

- The final snapshot is written as a closed ``branch_final_snapshot_v1``
  object under the ``composite_snapshot`` role rather than a full
  ``CompositeSnapshotEnvelope``.  That envelope requires the study manifest,
  prefix schedule, isolation contract, and attestation references, none of
  which are in ``WORKER_READABLE_ROLES``; a worker that could name them would
  be a wider capability than the one it was issued.  The written record keeps
  exactly the fields a restore needs, so ``grade_opaque_slot`` can reopen it.
- Branch model requests use a local ``branch-request-v1`` grammar rather than
  the prefix loop's ``synthetic-request-v1``, because a branch request may
  carry the optional private packet and the prefix grammar has no field for
  one.  The grammar is still a pure function of (role, context, packet).
- A model-call cap that binds terminates with ``FailureKind.TOKEN_CAP``.
  ``FailureKind.MODEL_CALL_CAP`` is not in the registered unscored-receipt
  failure set, and both caps bound the same generation budget.
- ``wall_clock_ms`` is measured with a real monotonic clock, so that one
  counter field is genuinely observed rather than replayed.  Every other
  counter, digest, and seed in the receipt is a deterministic function of the
  frozen inputs.
"""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path
import time
from typing import Literal, cast

from pneuma_lab.foundation.artifacts import canonical_json_bytes

from .authority_refs import decode_artifact_ref, load_json_bytes
from .branch_records import SlotExecutionReceipt, UnscoredSlotReceipt, terminal_receipt_digest
from .controller import derive_call_seed
from .controller_artifacts import ControllerArtifactStore
from .errors import RecordValidationError
from .packet_capabilities import SlotArtifactLoader, seal_slot_capability
from .prefix_contracts import (
    SyntheticPrefixProgram,
    load_synthetic_prefix_program,
)
from .synthetic_environment import (
    SyntheticByteTokenizer,
    SyntheticEnvironmentFactory,
    SyntheticEnvironmentHandle,
    _decode_snapshot_state,
    _EnvironmentFleet,
)
from .types import (
    ArtifactRef,
    BranchOutcome,
    CallSeedReceipt,
    FailureKind,
    GradeReceipt,
    OpaqueSlotWorkOrder,
    ResourceCounters,
    SubjectTurn,
    ToolCall,
)


BRANCH_SNAPSHOT_RECORD_KIND = "branch_final_snapshot_v1"
BRANCH_REQUEST_GRAMMAR = "branch-request-v1"
_ZERO_COST_RECORD_KIND = "synthetic_zero_attempt_cost_closure_v1"
_SUBJECT_ROLE: Literal["primary_subject"] = "primary_subject"


def token_ids_bytes(visible_context: bytes) -> bytes:
    """Return the canonical token-id projection a prefix digest commits to.

    The projection is a separate digest from the visible context because the
    tokenizer is part of the frozen contract: two slots that see identical
    bytes but tokenize them differently have not received the same prefix.
    """

    if type(visible_context) is not bytes:
        raise RecordValidationError("visible_context must be exact bytes")
    return canonical_json_bytes(
        {"token_ids": list(SyntheticByteTokenizer().encode(visible_context))},
        indent=None,
    )


def render_branch_request(
    *,
    subject_role: Literal["primary_subject", "user_simulator"],
    context_bytes: bytes,
    guidance_bytes: bytes | None,
) -> bytes:
    """Render one branch model request as a pure function of its inputs.

    The packet occupies its own field rather than being spliced into the
    context, so a sealed expected-request artifact proves both *that* a packet
    was injected and *which* bytes were injected.
    """

    if subject_role not in ("primary_subject", "user_simulator"):
        raise RecordValidationError("request subject_role is not registered")
    if type(context_bytes) is not bytes:
        raise RecordValidationError("request context must be exact bytes")
    if guidance_bytes is not None and type(guidance_bytes) is not bytes:
        raise RecordValidationError("request guidance must be exact bytes or None")
    return canonical_json_bytes(
        {
            "context_base64": base64.b64encode(context_bytes).decode("ascii"),
            "grammar": BRANCH_REQUEST_GRAMMAR,
            "guidance_base64": (
                None
                if guidance_bytes is None
                else base64.b64encode(guidance_bytes).decode("ascii")
            ),
            "subject_role": subject_role,
        },
        indent=None,
    )


@dataclass(frozen=True, slots=True)
class RestoredPrefixView:
    """The restorable prefix facts decoded out of one composite snapshot.

    This is the worker's whole view of the prefix.  It carries no arm, donor,
    peer slot, grade, or provider transcript, and every reference in it is used
    to *widen the worker's own capability*, which is why it must come from the
    snapshot bytes and never from a caller argument.
    """

    environment_snapshot_ref: ArtifactRef
    visible_context_ref: ArtifactRef
    token_ids_ref: ArtifactRef
    visible_sha256: str
    token_ids_sha256: str
    branch_pending_calls: tuple[ToolCall, ...]

    def __post_init__(self) -> None:
        for name, role in (
            ("environment_snapshot_ref", "environment_snapshot"),
            ("visible_context_ref", "visible_context"),
            ("token_ids_ref", "token_ids"),
        ):
            ref = getattr(self, name)
            if type(ref) is not ArtifactRef:
                raise RecordValidationError(f"{name} must be exact ArtifactRef")
            if ref.role != role:
                raise RecordValidationError(f"{name} must use the {role} role")
        for name in ("visible_sha256", "token_ids_sha256"):
            digest = getattr(self, name)
            if type(digest) is not str or len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise RecordValidationError(f"{name} must be lowercase SHA-256 hex")
        if type(self.branch_pending_calls) is not tuple or any(
            type(call) is not ToolCall for call in self.branch_pending_calls
        ):
            raise RecordValidationError(
                "branch_pending_calls must be an exact ToolCall tuple"
            )


def _mapping(value: object, *, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RecordValidationError(f"{field} must be a JSON object")
    return value


def _decode_pending_calls(value: object) -> tuple[ToolCall, ...]:
    if not isinstance(value, list):
        raise RecordValidationError("branch_pending_calls must be a JSON array")
    calls: list[ToolCall] = []
    for index, item in enumerate(cast(list[object], value)):
        row = _mapping(item, field=f"branch_pending_calls[{index}]")
        if set(row) != {"call_id", "canonical_arguments_json", "name"}:
            raise RecordValidationError(
                f"branch_pending_calls[{index}] has an open shape"
            )
        try:
            calls.append(
                ToolCall(
                    call_id=cast(str, row["call_id"]),
                    name=cast(str, row["name"]),
                    canonical_arguments_json=cast(
                        str, row["canonical_arguments_json"]
                    ),
                )
            )
        except (TypeError, ValueError) as exc:
            raise RecordValidationError(
                f"branch_pending_calls[{index}] is invalid"
            ) from exc
    return tuple(calls)


def decode_prefix_snapshot(payload: bytes) -> RestoredPrefixView:
    """Project the restorable prefix facts out of a composite snapshot record.

    Both the prefix loop's ``CompositeSnapshotEnvelope`` and this module's
    ``branch_final_snapshot_v1`` carry the same six load-bearing fields, so one
    decoder serves a first restore and a regrade alike.
    """

    if type(payload) is not bytes:
        raise RecordValidationError("composite snapshot payload must be exact bytes")
    record = _mapping(
        load_json_bytes(payload, source=Path("<composite-snapshot>")),
        field="composite snapshot",
    )
    missing = {
        "environment_snapshot_ref",
        "visible_context_ref",
        "token_ids_ref",
        "visible_sha256",
        "token_ids_sha256",
        "branch_pending_calls",
    } - set(record)
    if missing:
        raise RecordValidationError(
            "composite snapshot is missing a restorable field"
        )
    return RestoredPrefixView(
        environment_snapshot_ref=decode_artifact_ref(
            record["environment_snapshot_ref"], field="environment_snapshot_ref"
        ),
        visible_context_ref=decode_artifact_ref(
            record["visible_context_ref"], field="visible_context_ref"
        ),
        token_ids_ref=decode_artifact_ref(
            record["token_ids_ref"], field="token_ids_ref"
        ),
        visible_sha256=cast(str, record["visible_sha256"]),
        token_ids_sha256=cast(str, record["token_ids_sha256"]),
        branch_pending_calls=_decode_pending_calls(record["branch_pending_calls"]),
    )


def _require_work_order(work_order: object) -> OpaqueSlotWorkOrder:
    if type(work_order) is not OpaqueSlotWorkOrder:
        raise RecordValidationError("work_order must be exact OpaqueSlotWorkOrder")
    return work_order


def _read_prefix_view(
    work_order: OpaqueSlotWorkOrder,
    *,
    run_root: Path,
    task_input_ref: ArtifactRef,
    program_ref: ArtifactRef,
) -> RestoredPrefixView:
    capability = seal_slot_capability(
        work_order, additional_refs=(task_input_ref, program_ref)
    )
    with SlotArtifactLoader(capability, run_root=run_root) as loader:
        return decode_prefix_snapshot(loader.read_bytes(work_order.snapshot_ref))


def _program_request_refs(program: SyntheticPrefixProgram) -> tuple[ArtifactRef, ...]:
    seen: dict[str, ArtifactRef] = {}
    for row in program.provider_transcript:
        seen.setdefault(row.expected_request_ref.relative_path, row.expected_request_ref)
    return tuple(seen.values())


def _restore_and_verify(
    handle: SyntheticEnvironmentHandle,
    *,
    work_order: OpaqueSlotWorkOrder,
    prefix: RestoredPrefixView,
    environment_snapshot_bytes: bytes,
) -> bytes:
    """Restore, then prove the frozen prefix, before the subject may act."""

    handle.start()
    handle.restore(environment_snapshot_bytes)
    if handle.snapshot() != environment_snapshot_bytes:
        raise RecordValidationError(
            "restored environment does not reproduce its frozen snapshot"
        )
    visible = handle.visible_context()
    if hashlib.sha256(visible).hexdigest() != work_order.prefix_visible_sha256:
        raise RecordValidationError(
            "restored visible context differs from the frozen prefix digest"
        )
    if prefix.visible_sha256 != work_order.prefix_visible_sha256:
        raise RecordValidationError(
            "composite snapshot visible digest differs from the work order"
        )
    if hashlib.sha256(token_ids_bytes(visible)).hexdigest() != prefix.token_ids_sha256:
        raise RecordValidationError(
            "restored token-id projection differs from the frozen prefix digest"
        )
    if _decode_snapshot_state(
        environment_snapshot_bytes
    ).branch_pending_calls != prefix.branch_pending_calls:
        raise RecordValidationError(
            "composite snapshot pending calls differ from the restored environment"
        )
    return visible


@dataclass(frozen=True, slots=True)
class _SubjectLoopResult:
    generated_tokens: int
    model_calls: int
    tool_calls: int
    call_seeds: tuple[CallSeedReceipt, ...]
    failure_kind: FailureKind


def _run_subject_loop(
    handle: SyntheticEnvironmentHandle,
    *,
    work_order: OpaqueSlotWorkOrder,
    program: SyntheticPrefixProgram,
    loader: SlotArtifactLoader,
    guidance_bytes: bytes | None,
    executed_tool_calls: int,
    started_ns: int,
) -> _SubjectLoopResult:
    """Drive the branch subject under the frozen caps until a stop binds."""

    caps = work_order.branch_caps
    rows = {
        row.call_index: row
        for row in program.provider_transcript
        if row.subject_role == _SUBJECT_ROLE
    }
    call_seeds: list[CallSeedReceipt] = []
    generated_tokens = 0
    model_calls = 0
    tool_calls = executed_tool_calls
    failure = FailureKind.NONE

    def elapsed_ms() -> int:
        return (time.monotonic_ns() - started_ns) // 1_000_000

    def terminate(kind: FailureKind, pending: Sequence[ToolCall]) -> None:
        nonlocal failure
        handle.terminate(kind, tuple(pending))
        failure = kind

    call_index = 0
    while not handle.episode_terminal():
        if elapsed_ms() >= caps.wall_clock_ms:
            terminate(FailureKind.TIMEOUT, ())
            break
        if generated_tokens >= caps.generated_tokens:
            terminate(FailureKind.TOKEN_CAP, ())
            break
        if model_calls >= caps.model_calls:
            terminate(FailureKind.TOKEN_CAP, ())
            break
        seed = derive_call_seed(work_order.slot.seed, _SUBJECT_ROLE, call_index)
        row = rows.get(call_index)
        if row is None:
            raise RecordValidationError(
                "nonterminal branch outlived its sealed subject transcript"
            )
        if row.seed != seed:
            raise RecordValidationError(
                "sealed transcript seed differs from the derived call seed"
            )
        # The packet is visible exactly once, on the first post-pending call:
        # a packet that reappeared on later calls would be a second treatment.
        request = render_branch_request(
            subject_role=_SUBJECT_ROLE,
            context_bytes=handle.visible_context(),
            guidance_bytes=guidance_bytes if call_index == 0 else None,
        )
        if request != loader.read_bytes(row.expected_request_ref):
            raise RecordValidationError(
                "rendered branch request differs from its sealed expectation"
            )
        turn = row.typed_turn
        if type(turn) is not SubjectTurn:
            raise RecordValidationError(
                "sealed branch transcript row carries no typed turn"
            )
        model_calls += 1
        call_seeds.append(CallSeedReceipt(_SUBJECT_ROLE, call_index, seed))
        handle.append_assistant_turn(turn)
        generated_tokens += turn.generated_tokens
        capped = False
        for position, call in enumerate(turn.tool_calls):
            if tool_calls >= caps.tool_calls:
                terminate(FailureKind.TOOL_CAP, turn.tool_calls[position:])
                capped = True
                break
            tool_calls += 1
            handle.execute_tool(call)
            if handle.episode_terminal():
                break
        if capped:
            break
        call_index += 1

    if failure is FailureKind.NONE:
        failure = handle.failure_kind()
    return _SubjectLoopResult(
        generated_tokens=generated_tokens,
        model_calls=model_calls,
        tool_calls=tool_calls,
        call_seeds=tuple(call_seeds),
        failure_kind=failure,
    )


_LOCAL_SOURCE_ROOT = Path(__file__).parents[3]


def _verify_source_bytes(ref: ArtifactRef, *, run_root: Path) -> None:
    """Prove a source reference names local bytes that reproduce its digest.

    The reference is checked against the checked-out package source, not the
    run root, because that is the file the spawned worker re-hashes against
    ``--source-sha256`` before it will serve a single operation.  Verifying it
    here turns a caller-asserted implementation identity into a checked one.
    """

    del run_root  # the environment identity is a source claim, not an artifact
    root = _LOCAL_SOURCE_ROOT.resolve(strict=True)
    named = root / ref.relative_path
    if named.is_symlink():
        raise RecordValidationError(
            f"source reference must not be a symlink: {ref.relative_path!r}"
        )
    try:
        resolved = named.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise RecordValidationError(
            f"unreadable source reference {ref.relative_path!r}"
        ) from exc
    payload = resolved.read_bytes()
    if (
        len(payload) != ref.byte_count
        or hashlib.sha256(payload).hexdigest() != ref.sha256
    ):
        raise RecordValidationError(
            f"source reference bytes mismatch: {ref.relative_path!r}"
        )


def _spawn_isolated_handle(
    *,
    run_root: Path,
    task_input_bytes: bytes,
    program_bytes: bytes,
    environment_source_ref: ArtifactRef,
) -> tuple[_EnvironmentFleet, SyntheticEnvironmentHandle]:
    if type(environment_source_ref) is not ArtifactRef:
        raise RecordValidationError(
            "environment_source_ref must be exact ArtifactRef"
        )
    # The environment identity is a claim about which reviewed source the
    # worker subprocess re-hashes at startup.  Reading the referenced bytes
    # here makes the claim checkable instead of caller-asserted; a ref naming
    # an absent or altered source cannot mint an implementation identity.
    _verify_source_bytes(environment_source_ref, run_root=run_root)
    factory = SyntheticEnvironmentFactory(
        task_input_bytes=task_input_bytes,
        program_bytes=program_bytes,
        implementation_source_sha256=environment_source_ref.sha256,
    )
    fleet = _EnvironmentFleet(
        run_root=run_root,
        factory=factory,
        task_input_bytes=task_input_bytes,
        program_bytes=program_bytes,
    )
    try:
        return fleet, fleet.spawn(0).handle
    except BaseException:
        fleet.close()
        raise


def run_opaque_slot(
    work_order: OpaqueSlotWorkOrder,
    *,
    run_root: Path,
    task_input_ref: ArtifactRef,
    program_ref: ArtifactRef,
    environment_source_ref: ArtifactRef,
) -> UnscoredSlotReceipt:
    """Execute one opaque branch slot and close it without grading it.

    The returned receipt is terminal but unscored: it names the final snapshot
    and the resource cost, and it is structurally incapable of naming an
    outcome.  That is what lets an attempt be sealed before any endpoint is
    readable.
    """

    order = _require_work_order(work_order)
    root = Path(run_root)
    started_ns = time.monotonic_ns()
    prefix = _read_prefix_view(
        order, run_root=root, task_input_ref=task_input_ref, program_ref=program_ref
    )
    restore_capability = seal_slot_capability(
        order,
        additional_refs=(
            task_input_ref,
            program_ref,
            prefix.environment_snapshot_ref,
            prefix.visible_context_ref,
            prefix.token_ids_ref,
        ),
    )
    with SlotArtifactLoader(restore_capability, run_root=root) as loader:
        environment_snapshot_bytes = loader.read_bytes(prefix.environment_snapshot_ref)
        task_input_bytes = loader.read_bytes(task_input_ref)
        program_bytes = loader.read_bytes(program_ref)
    program = load_synthetic_prefix_program(program_bytes)
    if program.task_id != order.task_id:
        raise RecordValidationError("sealed program names a different task")
    execution_capability = seal_slot_capability(
        order,
        additional_refs=(
            task_input_ref,
            program_ref,
            prefix.environment_snapshot_ref,
            prefix.visible_context_ref,
            prefix.token_ids_ref,
            *_program_request_refs(program),
        ),
    )

    fleet, handle = _spawn_isolated_handle(
        run_root=root,
        task_input_bytes=task_input_bytes,
        program_bytes=program_bytes,
        environment_source_ref=environment_source_ref,
    )
    try:
        _restore_and_verify(
            handle,
            work_order=order,
            prefix=prefix,
            environment_snapshot_bytes=environment_snapshot_bytes,
        )
        executed = 0
        for call in prefix.branch_pending_calls:
            if executed >= order.branch_caps.tool_calls:
                raise RecordValidationError(
                    "frozen pending prefix calls exceed the branch tool cap"
                )
            executed += 1
            handle.execute_tool(call)
        pre_injection_visible = handle.visible_context()
        pre_injection_visible_sha256 = hashlib.sha256(
            pre_injection_visible
        ).hexdigest()
        pre_injection_token_ids_sha256 = hashlib.sha256(
            token_ids_bytes(pre_injection_visible)
        ).hexdigest()
        with SlotArtifactLoader(execution_capability, run_root=root) as loader:
            guidance_bytes = (
                None
                if order.private_guidance_ref is None
                else loader.read_bytes(order.private_guidance_ref)
            )
            result = _run_subject_loop(
                handle,
                work_order=order,
                program=program,
                loader=loader,
                guidance_bytes=guidance_bytes,
                executed_tool_calls=executed,
                started_ns=started_ns,
            )
        final_snapshot_bytes = handle.snapshot()
        final_state = _decode_snapshot_state(final_snapshot_bytes)
        final_visible = handle.visible_context()
    finally:
        fleet.close()

    wall_clock_ms = (time.monotonic_ns() - started_ns) // 1_000_000
    with ControllerArtifactStore(root) as store:
        environment_snapshot_ref = store.write(
            role="environment_snapshot",
            payload=final_snapshot_bytes,
            media_type="application/octet-stream",
        )
        visible_context_ref = store.write(
            role="visible_context",
            payload=final_visible,
            media_type="application/json",
        )
        token_ids_ref = store.write(
            role="token_ids",
            payload=token_ids_bytes(final_visible),
            media_type="application/json",
        )
        final_snapshot_ref = store.write(
            role="composite_snapshot",
            payload=canonical_json_bytes(
                {
                    "record_kind": BRANCH_SNAPSHOT_RECORD_KIND,
                    "opaque_capability_id": order.slot.opaque_capability_id,
                    "slot_id": order.slot.slot_id,
                    "environment_snapshot_ref": _ref_mapping(
                        environment_snapshot_ref
                    ),
                    "visible_context_ref": _ref_mapping(visible_context_ref),
                    "token_ids_ref": _ref_mapping(token_ids_ref),
                    "visible_sha256": hashlib.sha256(final_visible).hexdigest(),
                    "token_ids_sha256": hashlib.sha256(
                        token_ids_bytes(final_visible)
                    ).hexdigest(),
                    "branch_pending_calls": [
                        _call_mapping(call)
                        for call in final_state.branch_pending_calls
                    ],
                    "terminal_unexecuted_remainder": [
                        _call_mapping(call)
                        for call in final_state.terminal_unexecuted_remainder
                    ],
                    "episode_terminal": final_state.episode_terminal,
                    "terminal_failure_kind": result.failure_kind.value,
                    "pre_injection_visible_sha256": pre_injection_visible_sha256,
                    "pre_injection_token_ids_sha256": pre_injection_token_ids_sha256,
                },
                indent=None,
            ),
            media_type="application/json",
        )
        provider_cost_ref = store.write(
            role="provider_cost_closure",
            payload=canonical_json_bytes(
                {
                    "record_kind": _ZERO_COST_RECORD_KIND,
                    "total_cost_microunits": 0,
                },
                indent=None,
            ),
            media_type="application/json",
        )
    return UnscoredSlotReceipt(
        slot_id=order.slot.slot_id,
        opaque_capability_id=order.slot.opaque_capability_id,
        pre_injection_visible_sha256=pre_injection_visible_sha256,
        pre_injection_token_ids_sha256=pre_injection_token_ids_sha256,
        final_snapshot_ref=final_snapshot_ref,
        counters=ResourceCounters(
            result.generated_tokens,
            result.model_calls,
            result.tool_calls,
            wall_clock_ms,
        ),
        call_seeds=result.call_seeds,
        failure_kind=result.failure_kind,
        provider_cost_ref=provider_cost_ref,
        endpoint_readable=False,
    )


def _ref_mapping(ref: ArtifactRef) -> dict[str, object]:
    return {
        "byte_count": ref.byte_count,
        "media_type": ref.media_type,
        "relative_path": ref.relative_path,
        "role": ref.role,
        "sha256": ref.sha256,
    }


def _call_mapping(call: ToolCall) -> dict[str, object]:
    return {
        "call_id": call.call_id,
        "canonical_arguments_json": call.canonical_arguments_json,
        "name": call.name,
    }


def grade_opaque_slot(
    work_order: OpaqueSlotWorkOrder,
    unscored: UnscoredSlotReceipt,
    *,
    run_root: Path,
    task_input_ref: ArtifactRef,
    program_ref: ArtifactRef,
    environment_source_ref: ArtifactRef,
    prefix_success: int,
) -> SlotExecutionReceipt:
    """Grade one closed slot in a fresh, disposable, read-only environment.

    Grading runs after the fact and in a different process than the subject
    did, so a grader cannot influence the trajectory it scores.  The published
    receipt names the exact terminal receipt it descends from by digest, which
    is what prevents slot ``i``'s outcome from being paired with slot ``j``'s
    evidence.
    """

    order = _require_work_order(work_order)
    if type(unscored) is not UnscoredSlotReceipt:
        raise RecordValidationError("unscored must be exact UnscoredSlotReceipt")
    if unscored.opaque_capability_id != order.slot.opaque_capability_id or (
        unscored.slot_id != order.slot.slot_id
    ):
        raise RecordValidationError("terminal receipt does not belong to this order")
    if type(prefix_success) is not int or prefix_success not in (0, 1):
        raise RecordValidationError("prefix_success must be exact 0 or 1")
    root = Path(run_root)

    if (
        unscored.slot_id != order.slot.slot_id
        or unscored.opaque_capability_id != order.slot.opaque_capability_id
    ):
        raise RecordValidationError(
            "the unscored receipt does not belong to this work order's slot"
        )
    final_capability = seal_slot_capability(
        order,
        additional_refs=(task_input_ref, program_ref),
        terminal_snapshot_ref=unscored.final_snapshot_ref,
    )
    with SlotArtifactLoader(final_capability, run_root=root) as loader:
        final = decode_prefix_snapshot(loader.read_bytes(unscored.final_snapshot_ref))
        task_input_bytes = loader.read_bytes(task_input_ref)
        program_bytes = loader.read_bytes(program_ref)
    restore_capability = seal_slot_capability(
        order,
        additional_refs=(
            task_input_ref,
            program_ref,
            final.environment_snapshot_ref,
        ),
        terminal_snapshot_ref=unscored.final_snapshot_ref,
    )
    with SlotArtifactLoader(restore_capability, run_root=root) as loader:
        environment_snapshot_bytes = loader.read_bytes(final.environment_snapshot_ref)
    program = load_synthetic_prefix_program(program_bytes)
    if program.task_id != order.task_id:
        raise RecordValidationError("sealed program names a different task")

    fleet, handle = _spawn_isolated_handle(
        run_root=root,
        task_input_bytes=task_input_bytes,
        program_bytes=program_bytes,
        environment_source_ref=environment_source_ref,
    )
    try:
        handle.start()
        handle.restore(environment_snapshot_bytes)
        if handle.snapshot() != environment_snapshot_bytes:
            raise RecordValidationError(
                "regrade environment does not reproduce the final snapshot"
            )
        evidence = handle.grade()
        # Grading is an observation, not a step: if the act of grading moved
        # the environment, the graded state is not the state that was sealed.
        if handle.snapshot() != environment_snapshot_bytes:
            raise RecordValidationError("grading mutated the sealed final snapshot")
    finally:
        fleet.close()

    sealed = program.grade_result
    if (
        hashlib.sha256(evidence).hexdigest() != sealed.evidence_ref.sha256
        or len(evidence) != sealed.evidence_ref.byte_count
    ):
        raise RecordValidationError(
            "grade evidence differs from the sealed program result"
        )
    with ControllerArtifactStore(root) as store:
        grade_evidence_ref = store.write(
            role="grade_evidence",
            payload=evidence,
            media_type="application/octet-stream",
        )
    grade = GradeReceipt(
        success=sealed.success,
        partial_reward=sealed.partial_reward,
        infrastructure_failure=sealed.infrastructure_failure,
        artifact_ref=grade_evidence_ref,
    )
    return SlotExecutionReceipt(
        source_receipt_sha256=terminal_receipt_digest(unscored),
        source_kind="graded_unscored",
        grade_receipt=grade,
        outcome=BranchOutcome(
            task_id=order.task_id,
            benchmark=order.benchmark,
            opaque_arm_id=order.slot.opaque_capability_id,
            success=grade.success,
            prefix_success=prefix_success,
            partial_reward=grade.partial_reward,
            infrastructure_failure=grade.infrastructure_failure,
            counters=unscored.counters,
            artifact_ref=grade_evidence_ref,
        ),
    )


__all__ = [
    "BRANCH_REQUEST_GRAMMAR",
    "BRANCH_SNAPSHOT_RECORD_KIND",
    "RestoredPrefixView",
    "decode_prefix_snapshot",
    "grade_opaque_slot",
    "render_branch_request",
    "run_opaque_slot",
    "token_ids_bytes",
]
