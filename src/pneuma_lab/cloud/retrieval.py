"""Step 5B retrieval workflow: fail-closed authorization, offline plans, byte verification.

Nothing here reaches a network by itself. Retrieval is performed only by a
caller-injected fetcher, only under an `authorized` record bound to the exact
input lock and to a spend-ledger row. A `candidate` record is an authorization
request, not authority: it yields plans and nothing else.

Authorization is now authenticated rather than merely bound. An `authorized`
record must carry an Ed25519 signature over the complete canonical body, made
by a key enumerated in advance in the trusted registry, inside that key's
validity window, not revoked, not expired, and bound to a spend-ledger row whose
exact line bytes still match. See `authorization_keys` for what that ceremony
does and does not establish — in particular, a key is not a person.

Two independent things must both hold before a byte moves. The authorization
must authenticate, *and* the input lock must be a real candidate rather than the
Step 5A shape demonstration: a perfectly signed approval over a lock full of
placeholder identities would otherwise read as authority to retrieve nothing in
particular. See `input_lock`.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from .authorization_keys import Clock, trusted_now
from .errors import CloudManifestError
from .inputs import verify_input_lock
from .manifests import _validate, validate_input_lock


# The fetch boundary yields chunks rather than returning a whole object, so the
# byte ceiling can be enforced *during* transfer. A fetcher that buffers the
# whole object first defeats that, and is the caller's responsibility to avoid.
Fetcher = Callable[[Mapping[str, Any]], Iterable[bytes]]

_SCOPE_BY_KIND = {
    "model": "model",
    "tokenizer": "tokenizer",
    "benchmark": "benchmark",
    "benchmark_dataset": "benchmark",
    "container": "container_base",
    "verifier": "verifier",
}


_AUTHORIZED_FIELDS = ("ledger_row_id", "ledger_row_sha256", "human_authorization")


def authorization_body_digest(record: Mapping[str, Any]) -> str:
    """Return the digest of the canonical body an approver signs."""

    from .authorization_keys import authorization_body_digest as _digest

    return _digest(record)


def validate_retrieval_authorization(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the record and enforce the candidate/authorized invariants.

    Shape only. A record can pass this and still be unauthenticated: signature
    verification needs the trusted registry and an evaluation instant, which are
    supplied at the gate rather than carried by the record.
    """

    authorization = _validate(record, expected_kind="cloud_retrieval_authorization")
    present = sum(authorization[field] is not None for field in _AUTHORIZED_FIELDS)
    if authorization["status"] == "authorized":
        if present != len(_AUTHORIZED_FIELDS):
            raise CloudManifestError("an authorized record needs a ledger row, its content digest, and a signed human authorization")
    elif present != 0:
        raise CloudManifestError("a candidate must carry no ledger row, no ledger digest, and no signature")
    return authorization


def require_authorized(
    record: Mapping[str, Any],
    lock: Mapping[str, Any],
    *,
    key_registry: Mapping[str, Any],
    ledger_path: Path,
    clock: Clock = trusted_now,
) -> dict[str, Any]:
    """Return the authorization only when it is authenticated for this exact lock.

    Every one of these must hold, and none of them substitutes for another: the
    record is `authorized`; its Ed25519 signature verifies against an enumerated,
    unrevoked, in-window trusted key; the approval has not expired **at the
    instant the trusted clock reports**; the referenced ledger row exists with
    its approved content; the lock digest matches; and the lock is a real
    candidate rather than a shape demonstration.

    There is deliberately no `at` parameter. An earlier version took the
    evaluation instant from its caller, which made expiry advisory: replaying an
    expired authorization only required passing an earlier in-window timestamp.
    `clock` exists so tests can pin an instant and is not an execution option.
    """

    from .authorization_keys import verify_ledger_binding, verify_signature
    from .input_lock import require_real_candidate_lock

    authorization = validate_retrieval_authorization(record)
    if authorization["status"] != "authorized":
        raise CloudManifestError("retrieval requires a fresh authenticated authorization, not a candidate")
    verify_signature(authorization, key_registry, now=clock())
    verify_ledger_binding(authorization, ledger_path)
    require_real_candidate_lock(lock)
    if authorization["input_lock_sha256"] != verify_input_lock(lock):
        raise CloudManifestError("authorization is not bound to this input-lock digest")
    return authorization


def _bound_lock(record: Mapping[str, Any], lock: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    authorization = validate_retrieval_authorization(record)
    verified = validate_input_lock(lock)
    if authorization["input_lock_sha256"] != verify_input_lock(verified):
        raise CloudManifestError("authorization is not bound to this input-lock digest")
    return authorization, verified


def build_audit_plan(lock: Mapping[str, Any], record: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Derive the ordered, executable Step 5B retrieval-and-verification plan.

    Buildable from a candidate; executable only through `retrieve_and_verify`.
    """

    authorization, verified = _bound_lock(record, lock)
    scopes = set(authorization["scopes"])
    mirror = authorization["mirror_root"]
    steps: list[dict[str, str]] = []

    def add(kind: str, target: Mapping[str, Any], receipt: Mapping[str, Any]) -> None:
        if _SCOPE_BY_KIND[kind] not in scopes:
            return
        reference = str(target["digest"] if kind == "container" else target["revision"])
        size = receipt["size_bytes"]
        # Mirror paths are scoped by kind, repository, and reference so two
        # artifacts can never be written to one destination and clobber it.
        slug = f"{kind}/{str(target['repository']).replace('/', '_')}/{reference.replace('/', '_').replace(':', '_')}"
        steps.append({
            "kind": kind,
            "repository": str(target["repository"]),
            "reference": reference,
            "expected_sha256": receipt["sha256"],
            "expected_size_bytes": size,
            "mirror_path": f"{mirror}/{slug}/{receipt['relative_path']}",
        })

    for pin in verified["model_pins"]:
        add("model", pin, pin["snapshot_receipt"])
    add("tokenizer", verified["tokenizer_pin"], verified["tokenizer_pin"]["snapshot_receipt"])
    for pin in verified["benchmark_pins"]:
        add("benchmark", pin, pin["snapshot_receipt"])
        # The dataset revision and its task manifest are the bytes the roster
        # counts are derived from; retrieving the repo alone would leave the
        # single most load-bearing input unverified.
        add("benchmark_dataset", {"repository": pin["repository"], "revision": pin["dataset_revision"]}, {"sha256": pin["task_manifest_sha256"], "relative_path": "task-manifest.json", "size_bytes": pin["task_manifest_size_bytes"]})
    for source in verified["verifier_sources"]:
        add("verifier", source, source["snapshot_receipt"])
    for base in verified["container_bases"]:
        digest = base["digest"].split(":")[-1]
        add("container", base, {"sha256": digest, "relative_path": "manifest.json", "size_bytes": base["manifest_size_bytes"]})
    if len({step["mirror_path"] for step in steps}) != len(steps):
        raise CloudManifestError("retrieval plan mirror paths must be unique")
    if not steps:
        raise CloudManifestError("retrieval plan is empty for the authorized scopes")
    return tuple(steps)


def missing_scopes(lock: Mapping[str, Any], record: Mapping[str, Any]) -> tuple[str, ...]:
    """Return lock-populated scopes the authorization does not cover."""

    authorization, verified = _bound_lock(record, lock)
    populated = {"model", "tokenizer", "benchmark", "verifier", "container_base", "license", "contamination"}
    if not verified["license_receipts"]:
        populated.discard("license")
    if not verified["contamination_receipts"]:
        populated.discard("contamination")
    return tuple(sorted(populated - set(authorization["scopes"])))


def require_complete_scopes(lock: Mapping[str, Any], record: Mapping[str, Any]) -> dict[str, Any]:
    """Refuse an authorization that would leave a pinned input unretrieved."""

    absent = missing_scopes(lock, record)
    if absent:
        raise CloudManifestError(f"authorization omits pinned input scopes: {', '.join(absent)}")
    return validate_retrieval_authorization(record)


def build_receipt_verification_plan(lock: Mapping[str, Any], record: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    """Derive local verification steps for license and contamination receipts.

    These are audit outputs mirrored provider-locally, so they are verified as
    files, never fetched from a registry.
    """

    authorization, verified = _bound_lock(record, lock)
    scopes = set(authorization["scopes"])
    mirror = authorization["mirror_root"]
    steps: list[dict[str, str]] = []
    for kind, key in (("license", "license_receipts"), ("contamination", "contamination_receipts")):
        if kind not in scopes:
            continue
        for receipt in verified[key]:
            steps.append({"kind": kind, "expected_sha256": receipt["sha256"], "expected_size_bytes": receipt["size_bytes"], "mirror_path": f"{mirror}/{kind}/{receipt['relative_path']}"})
    if len({step["mirror_path"] for step in steps}) != len(steps):
        raise CloudManifestError("receipt verification mirror paths must be unique")
    return tuple(steps)


def verify_local_bytes(payload: bytes, expected_sha256: str) -> str:
    """Hash bytes already present locally and fail closed on any mismatch."""

    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise CloudManifestError("retrieved bytes do not match the pinned digest")
    return digest


def verify_mirrored_file(path: Path, expected_sha256: str) -> str:
    """Verify an already-mirrored file without consulting a registry or tag."""

    if not path.is_file():
        raise CloudManifestError(f"mirrored artifact is missing: {path.as_posix()}")
    return verify_local_bytes(path.read_bytes(), expected_sha256)


def _publish(staged: Path, destination: Path) -> None:
    """Durably install a staged file at its destination.

    The staged file is fsynced before the rename and the destination directory
    after it, so a receipt cannot outlive the bytes it attests to across a
    crash. The rename is atomic within the mirror root, so no reader ever
    observes a partially written artifact at the published path.
    """

    with staged.open("rb") as handle:
        os.fsync(handle.fileno())
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged, destination)
    try:
        directory = os.open(destination.parent, os.O_RDONLY)
    except OSError:
        # Directory fsync is unavailable on some platforms (notably Windows).
        # The atomic rename still holds, so this is a durability degradation
        # rather than a correctness one.
        return
    try:
        os.fsync(directory)
    except OSError:
        pass
    finally:
        os.close(directory)


def _resolve_within(root: Path, relative: str) -> Path:
    """Resolve a mirror-relative path, refusing anything that escapes the root."""

    candidate = root / relative
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise CloudManifestError(f"mirror path escapes the mirror root: {relative}") from exc
    return candidate


def retrieve_and_verify(
    lock: Mapping[str, Any],
    record: Mapping[str, Any],
    fetcher: Fetcher,
    *,
    key_registry: Mapping[str, Any],
    ledger_path: Path,
    mirror_root: Path,
    clock: Clock = trusted_now,
) -> tuple[dict[str, Any], ...]:
    """Retrieve, durably publish, and independently re-verify every planned step.

    Three properties this function is responsible for, each of which was a real
    defect in an earlier version:

    **Time is not caller-supplied.** Validity is resolved through `clock`, which
    defaults to the trusted system clock. Overriding it is a test seam. An
    earlier signature took an `at` string from the caller, which meant an
    expired authorization could be replayed simply by passing an earlier
    in-window instant.

    **The ceiling is enforced before and during transfer, never after.** Every
    step's size is authenticated: it is pinned in the input lock, whose digest
    sits inside the signed authorization body, so it is approved rather than
    declared by the fetcher at transfer time. The whole plan is checked against
    the ceiling before the first byte moves, and each chunk is counted as it
    arrives, so an oversized object is abandoned mid-transfer rather than
    absorbed and then rejected.

    **A receipt attests to a file that exists.** Bytes are streamed to a staged
    file, durably installed at the mirror path, then *reopened and rehashed
    independently* before a receipt is emitted. An earlier version returned a
    `mirror_path` it never wrote or reread, so the receipt named a file that did
    not exist.
    """

    authorization = require_authorized(record, lock, key_registry=key_registry, ledger_path=ledger_path, clock=clock)
    plan = build_audit_plan(lock, authorization)
    ceiling = authorization["byte_ceiling_bytes"]

    # Pre-flight: the authorized plan as a whole must fit, so an over-budget
    # retrieval is refused outright instead of part-way through.
    planned = sum(int(step["expected_size_bytes"]) for step in plan)
    if planned > ceiling:
        raise CloudManifestError(
            f"authenticated plan size {planned} exceeds the authorized byte ceiling {ceiling}"
        )

    root = Path(mirror_root)
    root.mkdir(parents=True, exist_ok=True)
    staging = root / ".staging"
    staging.mkdir(parents=True, exist_ok=True)

    receipts: list[dict[str, Any]] = []
    spent = 0
    for index, step in enumerate(plan):
        expected_size = int(step["expected_size_bytes"])
        destination = _resolve_within(root, step["mirror_path"])
        if destination.exists():
            raise CloudManifestError(f"mirror destination is already occupied: {step['mirror_path']}")

        staged = staging / f"{index:04d}.part"
        received = 0
        digest = hashlib.sha256()
        try:
            with staged.open("wb") as handle:
                for chunk in fetcher(step):
                    received += len(chunk)
                    # Counted as it arrives: the transfer is abandoned at the
                    # first chunk that crosses either bound.
                    if received > expected_size:
                        raise CloudManifestError(
                            f"transfer for {step['kind']} exceeded its authenticated size {expected_size}"
                        )
                    if spent + received > ceiling:
                        raise CloudManifestError("transfer exceeded the authorized byte ceiling")
                    digest.update(chunk)
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
            if received != expected_size:
                raise CloudManifestError(
                    f"transfer for {step['kind']} ended at {received} bytes, not its authenticated size {expected_size}"
                )
            if digest.hexdigest() != step["expected_sha256"]:
                raise CloudManifestError("retrieved bytes do not match the pinned digest")
            _publish(staged, destination)
        finally:
            staged.unlink(missing_ok=True)

        # Independent re-verification of the installed file: rehashed from disk
        # rather than reusing the streaming digest, so a publication fault
        # cannot pass as a verified artifact.
        installed_digest = verify_mirrored_file(destination, step["expected_sha256"])
        installed_size = destination.stat().st_size
        if installed_size != expected_size:
            raise CloudManifestError(f"installed artifact size {installed_size} does not match {expected_size}")

        spent += received
        receipts.append({
            "kind": step["kind"],
            "reference": step["reference"],
            "sha256": installed_digest,
            "size_bytes": installed_size,
            "mirror_path": step["mirror_path"],
            "installed_path": destination.as_posix(),
        })

    with contextlib.suppress(OSError):
        staging.rmdir()
    return tuple(receipts)
